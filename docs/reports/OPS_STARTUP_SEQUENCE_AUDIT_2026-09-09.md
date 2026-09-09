# Startup-sequence audit — 2026-09-09 PAPER window

Companion to `OPS_INGESTOR_RESPAWN_LOOP_2026-09-09.md` (that report covers the supervisor
respawn defect and its breaker; this one covers everything else the 09:20 start did).

Orchestrator started 09:20:44. Audited at ~09:55, market open.

## Verdict at a glance

| Startup step | Outcome |
|---|---|
| Live-buffer EOD purge | **OK** |
| `download_all_data.py` catch-up | **OK — ran to completion** |
| Bhavcopy / 1d / 1m ingest | **OK** (all at 2026-09-08) |
| Derived builds + strategy refresh | **OK** (one monthly step skipped by design, one suspect) |
| **CAS synthetic marking** | **BROKEN — never runs, and the ingest actively erases it** |
| Instrument-master refresh | **NOT AUTOMATED — manual-only, 1.0 d stale** |
| Child supervision | **OK since the breaker** |

---

## 1. Live-buffer purge — OK

`market_ingestor.log` 09:20:49: *"EOD purge: live buffer cleared of rows before
2026-09-09."* Verified against the store rather than the log:

```
ticks_today.ticks: rows=15,290  distinct_days=1  min=2026-09-09 09:20:51  max=09:50:34
```

Exactly one session present, first row one second after the purge. `candles_today.duckdb`
could not be read — held by the live single writer, which is the correct state, not a
fault.

## 2. `download_all_data.py` catch-up — ran, completed, released its lock

Dispatched 09:20:56 (`data/ops/last_catchup.json` stamps `2026-09-09T09:20:56`). Its
`RUN_LOCK` (`data/ops/download_all_data.pid`) is **gone**, which only happens in
`main()`'s `finally` — so the pipeline exited normally rather than being killed.

Landed output, in pipeline order:

| Step | Evidence | Written |
|---|---|---|
| 1 equity bhavcopy | `max(trade_date)=2026-09-08`, 7,149,789 rows | — |
| 2 futures bhavcopy | `max(trade_date)=2026-09-08`, 1,494,048 rows | — |
| 3 index 1d | `1d/2026-09-08.duckdb` | 09:25 |
| 5 stock options | `max(trade_date)=2026-09-08`, 99,401,764 rows | — |
| 6 1m candles | `1m/2026-09-08.duckdb` | 09:31 |
| 7 build nifty50 | `carry/nifty50.duckdb` | 09:31 |
| 8 build continuous | `trend/continuous.duckdb` | 09:31 |
| 9 refresh carry | `carry/weekly_signals.duckdb`, `carry/facts.duckdb` | 09:32–09:33 |
| 9 refresh ts-basis-daily | `ts_basis_daily/ts_facts.duckdb`, `ts_signals.duckdb` | 09:34 |

2026-09-08 is the correct head: today's bhavcopy does not publish until after the close.
Formation dates confirm the refresh is real, not just a touched file —
`carry/weekly_signals` and `ts_basis_daily/ts_signals` both report
`MAX(formation_date) = 2026-09-08`.

### 2a. Two refresh steps did not rebuild

- **`carry-monthly` — correctly skipped.** Output head 2026-07-31 vs source 2026-09-08 is
  a 39-day gap, inside the `monthly=True` 40-day tolerance. It will rebuild on its own in
  a couple of days. Not a defect.
- **`ts-basis` — suspect.** `_needs_rebuild(TS_SIG_DB, "ts-basis")` is called **without**
  `monthly=True`, while the equally-monthly `carry-monthly` passes it. Tolerance is
  therefore 0, so a monthly construct is judged "Stale" on every run and rebuilt daily.
  Output head is still 2026-07-24 and the store's mtime is 2026-08-10, so either the
  rebuild is a daily no-op or it fails silently — **the two are not separable from mtime
  alone**, and the pipeline's stdout was inherited by a console that is not captured.
  Low priority: TS Basis monthly is SEALED-de-authorized and not on a promotion path.

---

## 3. CAS synthetic marking is broken — the primary finding

### 3a. `scripts/cas/mark_synthetic_bars.py` has no callers

A repo-wide grep for `mark_synthetic_bars` outside the script itself returns **nothing**.
It is a hand-run repair tool. Nothing in the orchestrator, `download_all_data.py`, or the
EOD chain invokes it.

### 3b. The ingest does not merely fail to mark — it erases marks

`scripts/fetch_upstox_historical.py:258`:

```sql
ON CONFLICT (symbol, timeframe, timestamp) DO UPDATE SET
    open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
    close = EXCLUDED.close, volume = EXCLUDED.volume,
    is_synthetic = FALSE
```

`is_synthetic = FALSE` is **hardcoded into the upsert**. And
`download_all_data._download_1m_candles` re-walks
`start_date = latest_1m_date − LOOKBACK_DAYS(7)` through today on every run. So any
session inside that trailing 7-day window has its marks actively reset each day. This is
the pitfall register's *"a historical backfill re-introduces every defect the backfill
script was written to fix"* — here the re-introduction is written into the SQL.

### 3c. Measured state of the 1m store

`is_synthetic = TRUE` counts vs. bars carrying the CAS carry-forward signature
(`NSE_EQ`, 15:15–15:29, `volume=0`, `open=high=low=close`):

| Sessions | Marked | Signature bars | State |
|---|--:|--:|---|
| 2026-08-03 → 08-20 | 2,406–2,618 | 2,576–2,618 | largely marked |
| 2026-08-21 → 08-28 | 262–294 | 2,856–2,870 | ~90% erased (20–21 of 228 symbols retain any mark) |
| **2026-08-31 → 09-08** | **0** | **2,576–2,577** | **entirely unmarked, 7 sessions** |

Direct evidence, 2026-09-08, most-traded equity (`NSE_EQ|INE669E01016`):

```
15:14  15.41 15.43 15.40 15.42  vol 1,539,044  is_synthetic=False   <- last real bar
15:15  15.42 15.42 15.42 15.42  vol 0          is_synthetic=False   <- carry-forward
 ...   (14 identical flat zero-volume bars)
15:28  15.42 15.42 15.42 15.42  vol 0          is_synthetic=False
15:29  15.42 15.42 15.42 15.42  vol 3,672,124  is_synthetic=False   <- the auction print
```

Fourteen bars with no trades behind them, all flagged as genuine.

The 08-21 → 08-28 band also carries a different universe (228 `NSE_EQ` symbols vs 200
before and after, 86,625 rows vs 76,125). Whether the universe change and the near-total
mark loss share a cause is **unexplained** — do not assume it is the same mechanism as the
September zeros.

### 3d. Why this matters, and what it does *not* affect

**Today's live session is unaffected.** NiftyShield reads the live buffer and the chain
poller, not the 1m per-date stores. This is a **research-substrate** defect: those files
feed backtests and `core/analytics/day_features.py`.

The cost is precisely the one the pitfall register already names — *a contiguity gate that
counts one bar per slot passes on fabricated data*. Every file reports exactly 76,125 rows
(200 equities + 3 indices, × 375 minutes). That perfect count is the tell, not the
reassurance: ~2,576 of those bars per session are aggregator carry-forward from a stale
LTP, and every completeness check will keep passing on them.

---

## 4. Instrument master is refreshed only by hand

`data/instruments/nse_fo_instruments.duckdb` is dated 2026-09-08 09:27 — 1.0 d old, which
is the `WARN instrument_master` in preflight.

`scripts/fetch_instrument_master.py` is invoked from exactly two non-test places:
`flask_app/blueprints/ops/routes.py:184` and `app_facade/data_facade.py:222` — both
operator-triggered dashboard actions. **No automated caller exists** in the orchestrator,
`download_all_data.py`, or the EOD chain. Yesterday's 09:27 refresh was a human clicking
the button; today nobody did.

Not a current fault — today's chain poller resolved expiries 2026-09-15 / 2026-09-22
correctly. It is a latent risk on an expiry-roll or new-listing day, since expiry
resolution and order-placement instrument mapping both read this store.

---

## 5. The ingestor has no singleton guard at all

`scripts/market_ingestor.py:225`:

```python
    def run(self, mock: bool = False):
        # Only acquire file lock if we are NOT running unified (PID check)
        # But for simplicity, we let the unified runner manage it.
        # self._acquire_lock()
```

`_acquire_lock()` is **commented out**. The only thing that stopped ~25 duplicate
ingestors from running concurrently this morning was the ZMQ bind failing on port 5555.

This corrects §7 item 2 of the companion report, which proposed *reordering* the call.
The fix is not a reorder and not a one-liner: re-enabling the guard introduces a **second
lock namespace** for the same daemon — `_acquire_lock` writes `data/market_ingestor.pid`,
while the orchestrator supervises `data/ops/market_ingestor.pid`. The operator has to
decide which file is authoritative before this is enabled; two independent locks for one
single-writer is how the original defect class started.

---

## 6. Respawn re-check — holding

~11 minutes after the breaker, all six supervised children report alive:

```
flask       alive=True  flask.pid            pid=20692
ingestor    alive=True  market_ingestor.pid  pid=12140
poller      alive=True  chain_poller.pid     pid=17952
session     alive=True  session.pid          pid=21000
eod         alive=True  _eod_worker.lock     pid=24008
wall_poller alive=True  wall_poller.pid      pid=21368
```

Exactly one `market_ingestor.py` process (12140, from 09:20:47). No new spawns. Session
heartbeat 09:51:01, `data_healthy=true`, 31 bars processed, 0 trades. Chain poller
09:48:18 (344 rows). Wall poller 09:48:25, all steps `ok`.

---

## 7. Disk hygiene (not a startup finding)

`data/live_buffer/` holds ~14 GB of compaction baselines from 2026-09-04:
`ticks_today.pre_compact_20260904_214842.duckdb` (10.1 GB) and
`candles_today.pre_compact_20260904_214846.duckdb` (4.3 GB). These are deliberate
copy-first snapshots; whether they are still needed is the operator's call.

---

**Follow-up task note:** `OPS_POST_CLOSE_FIX_TASK_2026-09-09.md` holds the execution plan for §3 (CAS) and §4 (instrument master), to be run after the close. It **corrects §4 above**: the master refresh is not manual — it is fired by the OAuth callback, so it silently skips on any day the token survives from the previous day. It also records two prerequisites found afterwards: the Cat-I table resolves 0 symbols for September (the marker would raise mid-run), and the marker overwrites its own copy-first baseline.
