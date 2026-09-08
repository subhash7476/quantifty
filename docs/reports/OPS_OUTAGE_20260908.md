# Ops Outage — 2026-09-08 morning window

**Status:** RESOLVED (stack restarted 09:40, reached `started`). One open defect (D1) and
one design gap (D2) remain.

## Operator symptoms
1. `orchestrator.py` started this morning, but the stack was not trading.
2. EOD purge was not done.
3. `download_all_data.py` was not run.
4. Options-Wall page shows an iron-fly premium farm, but no trade is entered.

Symptoms 1–3 share a single root cause (R1). Symptom 4 is unrelated and is **correct
behaviour** (see F4).

---

## R1 — Root cause: PID reuse defeated the ingestor adoption check

`scripts/ops/orchestrator.py::child_alive()` decides "already running" from
`pidfile.pid_alive(pid)` alone. `pid_alive()` is careful about *zombies*
(`GetExitCodeProcess == STILL_ACTIVE`) but never verifies process **identity**.

`data/ops/market_ingestor.pid` held **19336**, written 2026-09-07 14:42. That PID had been
recycled by a live `conhost.exe`. So:

```
child_alive("ingestor") -> True   (conhost is genuinely alive)
_ensure(deps, "ingestor")         -> adopts a process that does not exist
```

### Failure chain (each link observed, not inferred)

| # | Step | Evidence |
|---|---|---|
| 1 | Ingestor never spawned | no `market_ingestor.py` in the 09:26 process list |
| 2 | VIX feed never warmed | preflight: `live_vix ... ingestor_alive=False bar_age=63593s` (17.6 h) |
| 3 | `marks_warm` was fine | poller heartbeat cadence 9–13 s vs `MARKS_HEARTBEAT_MAX_S=60` — **only VIX was cold** |
| 4 | Warm-up loop (5b) exhausted | `start_sequence` returns `timeout:warmup` |
| 5 | `_cmd_start` tore the stack down | `if outcome != "started": sup.shutdown()` |
| 6 | Flask + chain_poller killed | PIDs 15812 / 22292 / 7892 all dead by 09:36; poller log stops 09:33:17 |

Steps 8/9/10 (`session`, `eod`, `wall_poller`) are **after** the warm-up gate and never ran.

### Timing note (not a fault)
Teardown landed at 09:33:17, not the nominal 09:27+120 s. `warmup_timeout_s=120` counts
`waited += poll_s` (2.0 s/iteration), but each iteration calls `marks_warm()`, `vix_warm()`
and `gate_status()` — three separate `preflight.build_context()` calls, each a bounded-retry
DuckDB read against `chain_cache.duckdb` while the poller holds append locks. 60 counted
iterations ≈ 6 min wall. The code's own `"after ~%ss counted"` wording acknowledges this.

### Fix applied
Deleted the stale locks (`market_ingestor.pid` was the only harmful one — the rest pointed at
genuinely dead PIDs). Operator restarted; sequence reached `started` in ~35 s with the
ingestor live:

```
09:40:55  WebSocket ingestor started successfully.
09:40:56  [Ingestor] EOD purge: live buffer cleared of rows before 2026-09-08.
```

---

## R2 — EOD purge and download: killed before the fire window

Not a gate failure. `scripts/schedule_worker.py` fires **20:00–23:30** (`FIRE_HOUR = 20`).
The orchestrator and its EOD child were shut down at **2026-09-07 15:56:49** — over four
hours before the worker could fire.

Consequences, in order:
- EOD chain never ran on 09-07 → no purge, no download.
- `futures_bhavcopy` / `stock_options_bhavcopy` max = **2026-09-04**; Monday 09-07 missing.
- Preflight reports this as `WARN eod_feeds behind expected session: futures, stock_options`.

Note this is *not* the `eod_decision.decide()` futures-gate pathology recorded in CLAUDE.md —
`decide()` was never reached at all. Both are now catching up: `download_all_data.py`
(09:41:12) and `ingest_equity_bhavcopy.py --start 2026-08-31 --end 2026-09-08` (09:41:22).

### D2 — Design gap (open)
The EOD fire window (20:00) is ~4.5 h after the session ends (~15:40), but the orchestrator is
a **foreground** supervisor the operator Ctrl+C's when the session ends. The EOD chain can
therefore only ever run if the operator leaves the terminal open all evening. Any evening the
operator closes up shop, EOD is silently skipped and the next morning's feeds are one session
stale. This is structural, not a one-off.

---

## F4 — Iron fly shows but no trade: correct behaviour, invisible reason

**The executor is right; the page is misleading.**

The only `premium_farm` rows today are `NSE_INDEX|Nifty 50`, `expiry = 2026-09-08` — **today**.
Nifty's weekly expiry is Tuesday and today is Tuesday, so **dte = 0**.

`core/options_wall/paper_executor.py::step()`:

```python
dte = (date.fromisoformat(structural.expiry) - now.date()).days
if dte < self.cfg.min_dte:      # min_dte = 1
    return None                 # silent
```

0 < 1 → the executor refuses, correctly and silently. The 0-DTE exclusion is deliberate.

The other two indices pass the dte gate but have **no farm signal**, so they are correctly idle:

| Index | Expiry | DTE | dte gate | premium_farm rows today |
|---|---|---|---|---|
| Nifty 50 | 2026-09-08 | **0** | **BLOCKS** | 2 |
| Nifty Bank | 2026-09-29 | 21 | passes | 0 (imperfection only) |
| SENSEX | 2026-09-10 | 2 | passes | 0 (imperfection / laggard) |

So **zero trades today is the correct outcome** — consistent with the pilot's own expectation
that farm trades are rare.

### D1 — Defect (open): scanner/executor divergence
`_run_scan()` in `core/options_wall/engine.py` applies **no dte filter** — it persists
`premium_farm` for the expiring contract, and the wall renders it as a live iron-fly
candidate. The executor then refuses on dte and returns `None` without recording a reason.
The page shows a tradeable-looking setup that the executor is structurally forbidden to take,
with nothing on screen explaining why.

Worth noting: on expiry day `get_weekly_expiry()` returns *today's* expiry, so the wall spends
the whole session scanning a contract the executor can never trade. From tomorrow (09-09) the
Nifty near-weekly rolls to 09-15 (dte 6) and the same signal would trade normally.

### D1 — RESOLVED 2026-09-08 (operator-directed)
The floor is now enforced **once**, in the scanner, and set to 0 so expiry-day flies trade.

- `ScanConfig.min_dte: int = 0` — the single declared default.
- `PaperConfig.min_dte = ScanConfig.min_dte` — one literal, so the two cannot drift.
- `_farm_screen` rejects `dte < cfg.min_dte` as its first (cheapest) guard, so the wall can no
  longer render a farm candidate the executor would refuse.
- The duplicate gate in `PaperExecutor.step()` is deleted; `step()` passes its `now` into
  `scan_chain`, and `_dte` takes an explicit day so the gate is testable at a pinned date.

Two tests added (`tests/options_wall/test_paper_executor.py`): DTE 0 opens at floor 0; DTE 0 at
floor 1 yields **no farm row and no trade** — the assertion that would have caught D1.

Six farm tests in `tests/analytics/test_chain_scanner.py` were pinned to `_NOW`. Four of them
had been asserting an empty farm list while silently passing on the real-calendar DTE rather
than on the gate they name. Suite: **145 passed**.

**Risk accepted, stated plainly.** `min_dte=0` is a new trading regime, not a display fix. The
codebase's existing position is that near-expiry is hazardous — `charm_dte_max = 2` exists to
flag charm cascades. Short gamma now opens into exactly that window. The `_manage` time stop is
`dte <= 1 and now >= 15:15`, but post-CAS index derivatives trade to **15:40**, so a 0-DTE fly
has ~25 minutes of settlement drift the time stop does not reach, and `sl_frac` is measured
against `max_loss`, which a pinned expiry can traverse in minutes. The pilot's TP/SL thresholds
(`tp_frac=0.25`, `sl_frac=0.5`) were not chosen with 0-DTE in mind.

---

## Health banner — worked, but under-weighted
The banner shipped yesterday (`fix/options-wall-tp-sl-thresholds`) did fire: the wall heartbeat
was `2026-09-07T15:40:06` (~18 h stale) and `/options/wall/api/health` returns `stale: true`,
rendering *"Poller heartbeat is stale — step health unknown."* It is styled `.unknown`
(grey `#F2F2F0`) and sits above a confident, fully-rendered gate strip and iron-fly card, which
carry no staleness marking of their own. The banner was correct and still did not stop the
operator reading an 18-hour-old scan as live.

---

## Unrelated observation
`autotrader.py` (PID 316, since 2026-09-07 18:02) is running under this Python install but
**no such file exists in `F:\Nifty`** — it belongs to another working directory. It is not an
orchestrator child. Flagged as an unaccounted process and a candidate DuckDB lock holder;
not touched.

## Current state (09:45)
All ten expected processes live: orchestrator, flask, market_ingestor, chain_poller, session,
schedule_worker, options_wall_poller, plus the two catch-up ingests. Wall heartbeat
`status: OK`, all six steps `ok: true` for NIFTY / BANKNIFTY / SENSEX.
