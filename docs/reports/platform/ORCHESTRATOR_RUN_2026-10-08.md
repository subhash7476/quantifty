# Orchestrator run check — 2026-10-08 (Thu)

Read-only check at 18:46. Nothing was started, stopped or modified.

## Verdict

The window itself worked (entry 13:00, hard exit 15:35, clean stop 15:50, no kill switch,
no open positions). The *run* did not go as scheduled, and two things need an operator decision
before tomorrow's 09:10 start.

## Timeline (all IST)

| Time | Event | Source |
|---|---|---|
| 09:10 | Scheduled `\Nifty\Orchestrator` starts (`run_if_session.py`) | `data/ops/scheduled_runs.log` |
| 09:43 | Catch-up dispatched; session runner starts (33 min after 09:10 — token gate) | `last_catchup.json`, journal |
| 09:43–11:58 | Session runs without a recorder (`prior_capture_merged: false`) | journal / `meta.json` |
| 11:58:40 – 11:59:08 | Session runner starts 3 times; flask, ingestor, ts_combo, wall_poller all (re)created 11:59:00–11:59:06 | journal, process list |
| 13:00 | `bear_call_spread` 22250/22450, 1 lot, entered (fills 13:01) | `execution.db` |
| 15:15 | `straddle_capture` OK, exit 0 | `scheduled_runs.log` |
| 15:35 | Hard exit; both structures closed | journal `STRUCTURE_CLOSE` |
| 15:50:05 | LoopDriver stops cleanly; `orchestrator.pid` removed | journal, `data/ops` mtime |

`scheduled_runs.log` has **no `END orchestrator 2026-10-08` line**. Task Scheduler `LastTaskResult = 1`.
The 09:10 wrapper process is gone and the orchestrator that ran the window (from 11:59) has
no `START` line, so it was not started by the wrapper.

## Findings

1. **Orphans after the 15:50 stop.** `orchestrator.py status` shows `ingestor`, `wall_poller`,
   `ts_combo` alive (PIDs 18388, 6428, 11568, parent 19244 dead); flask, poller, session, eod
   dead. `orchestrator.pid` is gone. Tomorrow's start will meet three stale children.
2. **Preflight is NO-GO** (`marks_warm`: chain poller not running) — expected after close, but the
   orphaned ingestor is the only thing keeping `live_vix` green.
3. **The 10-07 iron fly was left half-open overnight and its P&L landed on 10-08.**
   Group `55a1b863…`: three legs closed 10-07 at 15:37:03 / 15:37:33 / 15:43:21 (after the 15:35
   hard exit, ~30 s apart); the long 22500 PE wing was never closed, was held ~20 h, and was sold
   10-08 15:35:03 at 313.85 (bought 94.05, 130 qty → ≈ +₹28.6k gross). Journal shows
   `structure unmonitored for 74489s` / `NO exit bracket` (CRITICAL) at each restart, and the three
   `close_group leg failed … Idempotency violation` errors at 15:35 are the already-closed legs
   being re-submitted — benign, but they confirm the structure was never marked closed.
   `metrics.json` books it as `IRON_CONDOR`, session 2026-10-07, **+₹29,786 / r +1.527**, which
   dominates the window's `total_realized_pnl` (₹26,437). **That number is an unhedged long put
   catching a down day, not strategy edge.** Today's actual trade: SPREAD **+₹645** net (+₹774 gross).
4. **Why the 10-07 close stalled is not established.** Marks were intermittently stale/missing
   13:13–15:34 on 10-07 (chain poller gaps of 62–70 s, one 356 s), and no `STRUCTURE_CLOSE` was
   journaled for that group.
5. **No orchestrator log exists.** `run_if_session.py` inherits stdout/stderr and Task Scheduler
   does not redirect it, so the cause of the 09:10 instance's `exit 1` and of the 11:58–11:59
   restart is unrecoverable from disk. `logs/orchestrator_console*.log` are from 2026-08-21.

## Not determined

- Who/what ended the 09:10 instance, and who started the 11:59 one.
- Why the 09:43–11:58 session had no recorder capture.

## Decisions for the operator

- Stop the three orphans (PowerShell `Stop-Process`, verify death) before 09:10 tomorrow, or
  confirm the orchestrator adopts them cleanly.
- Decide whether 10-07's wing-leg P&L is excluded from the E008 window metrics (window starts 10-08).
- Give the scheduled orchestrator a log file (redirect in `run_if_session.py` / task action).
