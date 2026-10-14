# Orchestrator run check — 2026-10-14

Trigger: the 09:10 orchestrator console window did not close after the 15:50 stop and was closed by hand (~19:16).

## Run

| Item | Result |
|---|---|
| Scheduled start | 09:10:02, token via phone approval 09:12 |
| Session | 09:15:12 → 15:50:08, 260 driver bars, `telemetry_clean` true |
| Execution hash | `101bae72…4791` — matches the 2026-10-13 re-pin, so the day counts toward the E008 window |
| 13:00 entry | short strangle `NIFTY19OCT2622700CE` / `NIFTY19OCT2622600PE` (holiday-shifted weekly, fix from 2026-10-13 confirmed live) |
| Exit | `stop_loss` at 13:11:16 |
| 13:40 | `WATCHDOG_STALE_DATA` → kill switch latched, no position open, no `KILL_SWITCH_RELEASED` before 15:50. Cause not established: the ingestor log has no lines for 13:30–13:45 |
| `END orchestrator` | 15:50:09 exit 0 (`scheduled_runs.log`) |
| Per-run log | `data/ops/logs/orchestrator_2026-10-14.log` written (first scheduled day with the tee) |

## Why the window stayed open

The supervisor did stop itself: `trading day over — stopping the stack` 15:50:05, exit 0 at 15:50:09. The window stayed because
`options_wall_poller` (and, by the same mechanism, the `eod` schedule worker) was **still running**. Its log shows
`shutdown signal received (2)` at 19:16:08 and `stopped cleanly` 19:16:30, i.e. the signal came from closing the window,
not from the supervisor. A console window cannot close while a process attached to it lives.

Mechanism (`scripts/ops/orchestrator.py`):

1. `eod` and `wall_poller` are natively locked: the child writes its own lock seconds after launch, and `child_alive`
   reads that lock.
2. `_ensure()` spawns them as the last two steps of the start sequence. Only `Supervisor.tick` stamped a spawn time, so
   the grace window (`spawn_grace_s`) did not cover a spawn made by `_ensure`.
3. The first tick, milliseconds later, read both as dead and spawned a second copy — logged at 09:15:10.733/.737 as
   `child eod / wall_poller is not alive — restart #1`.
4. The copy refused the single-instance lock and exited. `_started[name]` now held the dead copy's handle.
5. At 15:50 `shutdown()` terminated the dead handles; the original instances had no handle and ran on.

Consequence beyond the window: a surviving child holds its lock into the next morning, so the next 09:10 start would
adopt a day-old wall poller / eod worker (expired token) — the same class as the 2026-10-06 stale-stack incident.
`flask`, `ingestor`, `poller`, `session` and `ts_combo` were unaffected: their pid file or lock existed before the
first tick.

Evidence is indirect for `eod` (idle, writes nothing) and direct for `wall_poller`; the restart lines, the code path
and the 19:16 signal all agree. The 09:15 start lines of `options_wall_poller.log` had already rotated out, so the
duplicate's own "another WallPoller is already running" message was not available.

## Fix

`Supervisor.note_spawn(name)` stamps the grace window; `_wire_supervisor(deps, sup)` wraps `deps.spawn` so every spawn
the start sequence makes starts it. `tests/ops/test_orchestrator.py::test_first_tick_does_not_respawn_children_the_start_sequence_just_spawned`
failed with duplicate spawns before the change and passes after; `tests/ops` 132 passed.

`scripts/ops/orchestrator.py` is outside `EXECUTION_GLOBS`, so no E008 window reset or re-pin.

## Open

- 13:40 stale-data trip: cause unknown; the kill switch stayed latched to 15:50 (`releasable` stale trips release on the
  first bar back — none was journaled). No impact today (flat since 13:11) but it would have blocked a re-entry.
- 15:28–15:40 `api.upstox.com` name-resolution failures in the wall poller (network, transient; wall poller is
  observe-only).
- 10-07 iron-condor wing-leg exclusion from window metrics: still undecided.
