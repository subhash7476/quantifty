# DayType live 13:00 fact — stale prior-session bar truncates the session frame

**Session affected:** 2026-09-10 (entry missed)
**Status:** root cause found, fixed at both sites, regression tests green.
**A missed `short_straddle`, not a no-trade day.** Fresh process required to pick up the fix.

---

## 1. Symptom

Every retry in the 13:00–13:30 window journaled the same line (31 consecutive
`FACT_PUBLISH_SKIPPED` events, 13:01 → 13:31):

```
live 13:00 fact not ready: no source covers 09:15..13:00
  [per_day_store: absent; live_buffer: 1 bars, last 16:00 -- only 1 bars < 100, rejected]
```

The window latched at 13:31 and the session produced no entry.

## 2. Root cause

`data/live_buffer/candles_today.duckdb` held **all 226 session bars** for
NF/BN/VIX the whole time. It also held **three leftover rows from the previous
session** — `2026-09-09 16:00`, one per index symbol, `O=H=L=C`, `volume=0`:

| symbol | rows on 2026-09-09 | rows on 2026-09-10 |
|---|--:|--:|
| `NSE_INDEX|Nifty 50` | 1 (16:00) | 261 (09:00 → 13:20) |
| `NSE_INDEX|Nifty Bank` | 1 (16:00) | 261 |
| `NSE_INDEX|India VIX` | 1 (16:00) | 261 |

`_session_frame()` in `scripts/daytype/publish_live_fact.py` filtered on
**minute-of-day only** — never on the session date. The read is
`ORDER BY timestamp`, so the stale 16:00 row sorts **first**, and its
minute-of-day (960) already satisfies `>= CHECKPOINT_MIN (780)`. The
"first bar at/after 13:00" slice therefore cut the frame at index 0:

```
reached = sess.index[sess_min >= CHECKPOINT_MIN]   # -> [0, ...]
return sess.iloc[: reached[0] + 1]                 # -> 1 row, the stale 16:00 bar
```

One bar < `MIN_BARS` (100) → rejected → "no source covers 09:15..13:00", on
every retry, deterministically. The publisher was reading yesterday's closing
tick and reporting that today's session had no data.

`candles_today.duckdb` is a **rolling** buffer, not a today-only one — its own
rotation semantics say so. The publisher, which is handed an explicit `today`,
was the component making the wrong assumption.

## 3. Fix

`scripts/daytype/publish_live_fact.py` — scope the frame to the session date
**before** the checkpoint slice:

```python
def _session_frame(df: pd.DataFrame, session: date) -> Optional[pd.DataFrame]:
    ...
    df = df[df["timestamp"].dt.date == session]
    minute = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
```

Call site passes the `today` the publisher already carries. Nothing else changed
— the checkpoint slice, `MIN_BARS`, the source ladder, and the interior-gap
tolerance are untouched.

### Verification

- **RED/GREEN proven.** With the one added line removed, the new regression test
  fails and reproduces the production string verbatim
  (`live_buffer only 1 bars < 100 ... (1 bars, last 16:00)`); with it, it passes.
- `tests/daytype/test_daytype_facts.py` — **21 passed** (20 pre-existing + 1 new,
  `test_prior_session_bar_in_live_buffer_does_not_truncate_frame`).
- Run against the **real live buffer** at 13:35:
  `LIVE FACT 2026-09-10: Choppy conf=0.660 vix_at_checkpoint=11.77 (live@0bf5d6e)`
  — 226 bars found where the publisher had reported one.

## 3b. Same defect, second site — the evidence recorder

`scripts/nifty_shield_paper/recorder.py::_extract_session_bars(session, ...)`
took a `session` argument and **never filtered on it**, so the full-session
NF/BN/VIX bars copied into the evidence package came from the whole rolling
buffer. The three 16:00 rows would have entered the package and sorted **ahead
of every real bar** on `ORDER BY symbol, timestamp` — a replay whose clock
starts on the prior session and then jumps backwards. Fixed the same way
(`WHERE ... CAST(timestamp AS DATE) = ?`); the predicate is a no-op on the
per-day store, which is single-date by construction.

RED/GREEN proven; `tests/nifty_shield_paper` — **53 passed** (52 pre-existing +
1 new, `test_session_bars_exclude_prior_session_rows_in_rolling_buffer`).

**Sweep result — these two were the only sites.** Every other minute-of-day
filter (`publish_facts.py`, `build_eod_features.py`, `parity_check_13pm.py`,
`sealed_harness.py`) reads the per-day store, which holds one date per file.
`scripts/ops/preflight.py` reads the buffer with `MAX(timestamp)`, which a
stale older row cannot flatter. The bar provider is exonerated by the journal
itself — it ticked 13:01 → 13:31 at correct times, so it was never serving the
16:00 row.

## 4. Today's session — outcome

The fact row is now in `day_type_facts.duckdb`, but **it landed at 13:35, after
the 13:30 window closed**. Both latches had already fired:

- the driver latched `_published_sessions` at the 13:31 bar (retry window expired);
- `NiftyShieldSignalSource` latched `_entered_today = True` at the same bar
  (`entry_window_minutes = 30`).

**A real entry was missed — this was not a session the strategy would have sat
out anyway.** Resolving the published fact through the live selection path:

| input | value |
|---|---|
| regime | `Choppy` |
| regime_confidence | 0.6605 |
| `vix_at_checkpoint` | 11.77 — under `vix_skip_above` 20.0, so **no VIX skip** |
| `vix_pctile` | 23.81 — under `vix_iron_fly_pctile` 36.8 |
| → `select_structure` | **`short_straddle`** |
| `regime_sizing["Choppy"]` | 1.0 (full size, `max_lots` 2) |

`on_bar` applies no confidence gate, so the fact would have reached
`_build_legs` and emitted the straddle legs.

**No entry was taken on 2026-09-10, and none can be now** without widening a
pre-registered strategy parameter to chase a missed fill — an operator decision,
not a bug fix.

## 5. Required action before the next session

**The running session process still holds the pre-fix module.** Python imported
`publish_live_fact` at startup; an edit on disk does not reach a live process.
Left as-is, 2026-09-11 fails identically.

Confirmed running now: `orchestrator.py` (PID 26288) supervising
`nifty_shield_paper/session.py` (PID 20012), plus `market_ingestor.py` (24152)
and `chain_poller.py` (4748).

**Normal path — no special action.** The orchestrator is a foreground supervisor
started fresh each trading day (`python scripts/ops/orchestrator.py`, Ctrl+C to
stop). Today's stack shuts down at EOD as usual; tomorrow's start imports the
fixed module. **Verify** after tomorrow's start that no `FACT_PUBLISH_SKIPPED`
line appears after 13:00 in `data/nifty_shield/journal.jsonl`.

**Only if this orchestrator instance is left running past today**, restart the
session child alone — the supervisor respawns it with fresh code. Windows note
(repo-standing): `taskkill` via Git Bash silently fails; use PowerShell and
**confirm the process is dead before the supervisor respawns a single-writer**:

```powershell
Stop-Process -Id 20012 -Force; Start-Sleep -Seconds 3; Get-Process -Id 20012 -ErrorAction SilentlyContinue
```

An empty result from the last command means it is gone. There are no open
positions today, so a session restart risks nothing beyond the journal seam.

## 6. Follow-up (not fixed here)

1. **The three stale rows should not be in the buffer at all.** The rotation was
   submitted at 08:45:46 today (`EOD purge: live buffer cleared of rows before
   2026-09-10`) — one second after the WebSocket connected at 08:45:46.
   *Hypothesis, unverified:* the WS connect delivers a last-known-LTP snapshot
   per subscribed symbol carrying the previous session's exchange timestamp, and
   the aggregator writes those **after** the rotation completes. Consistent with
   the evidence — exactly the 3 index symbols, `O=H=L=C`, `volume=0`,
   `is_synthetic=False` (so not the `RecoverBars` path, which stamps TRUE).
   Fixing the ordering is a `market_ingestor` / writer-worker change, tracked
   with the F3/F4/F1 redesign.
2. **`_purge_stale_live_buffer` logs success on `submit()`, not on completion.**
   `"EOD purge: live buffer cleared"` is printed the moment the command is queued.
   The rotation's own result line (`live buffer rotated at ...: candles=N kept`)
   comes from `core.database.ingestors.live_buffer_writer`, whose logger has no
   handler and does not reach `logs/market_ingestor.log` — so **the rotation's
   actual outcome is invisible in the logs.** This is the repo's own
   "a value that is printed but never asserted is documentation, not a control"
   pitfall. The purge log line should move to the completion callback.
