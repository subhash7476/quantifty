# Ops + NiftyShield E008 fix plan — 2026-10-07

Branch `fix/orchestrator-eod-stop` (worktree `F:\Nifty_opsfix`), cut from main `09af31d`.

## 1. Incidents and root causes (evidence in session transcript)

| # | Symptom | Root cause | In hash scope? |
|---|---|---|---|
| I1 | 2026-10-07 09:10 orchestrator never started; pollers looped on "token absent or expired"; day-old session ran kill-switched | `_cmd_start` supervised with `while True` until Ctrl+C. 10-06 nobody pressed it; Task `\Nifty\Orchestrator` is `MultipleInstances=IgnoreNew` → `0x800710E0`, token gate never ran | No (`scripts/ops/orchestrator.py`) |
| I2 | 2026-10-06 11:54 NiftyShield stopped trading for the day | Upstox API unreachable 11:49→11:55 (all pollers `ConnectionError`) → watchdog stale trip → `activate_kill_switch` has **no release**; latched after DATA RECOVERED (11:56). 13:01 entry: "every leg rejected by a gate". Same pattern 09-30 14:35 | **Yes** (`core/execution/handler.py`) |
| I3 | Every exit logs `Exit diagnostics failed: no such column: intended_entry` | `handler._compute_exit_diagnostics` selects `intended_entry`/`entry_timestamp` from `trade_context`, which has no such columns; also reads equity 1m candles for option legs. Swallowed → `mae_mfe=None` | **Yes** (`handler.py:532`) |

## 2. E008 window (what a hash change costs)

E008 = the forward PAPER-validation window for `nifty_shield_v1` (ledger grant). Gates (runbook §8): ≥20 counted sessions
AND ≥30 round-trips, drawdown never breached, journal audit clean, margin gate on every entry, kill-switch drill, ≥1
byte-identical replay, regression green.

It runs on ONE frozen execution identity: `FROZEN_EXECUTION_HASH d66838c9…` over 5 file globs
(`scripts/nifty_shield_paper/identity.py`: `strategies/nifty_shield_v1/*.py`, `core/execution/options/nifty_shield_*.py`,
`core/execution/options/fees.py`, `core/execution/handler.py`, `scripts/nifty_shield_paper_runner.py`), with
`WINDOW_START 2026-09-28`. Each session's recorder stamps the hash; `assemble_report` counts a session only if it is on/after
`WINDOW_START` with a matching stamp. Any change to those files = new identity: re-pin hash + `WINDOW_START` together,
declared BEFORE the next session's first run, ledger note under E008. A strategy-attributable restart resets the count.

Banked under `d66838c9` today: 6 sessions (09-28, 09-29, 09-30, 10-01, 10-05, 10-06) + 10-07 in progress. A re-pin discards
them as window evidence (they remain on disk). Sessions without an entry (no-entry / VIX-skip / kill-switch day, e.g. 10-06)
do not count toward ≥20 even today.

## 3. Fix list

- **F1 (done, outside hash)** — orchestrator stops itself at 15:50 on its start date (date rollover also). 4 tests + runbook line. 120 ops tests green.
- **F2 (done, hash)** — stale-data kill-switch trip is releasable (`activate_kill_switch(releasable=True)` / `release_kill_switch`); every other trip stays latched. Journals `KILL_SWITCH_RELEASED`.
- **F3 (done, hash)** — dead `_compute_exit_diagnostics` MAE/MFE path removed.
- **F4 (done, hash re-pin)** — `FROZEN_EXECUTION_HASH b33f5c3f…` (watchdog.py added to EXECUTION_GLOBS; entry marks-freshness check added — operator-approved after review), `WINDOW_START 2026-10-08`, ledger E008 note. Recompute if any hash-scope file changes again.
- **F5 (dropped)** — `alerter.critical` already pushes a Telegram when the kill switch latches, and `release_kill_switch` pushes a WARNING on release; a clean day-end exit is exit 0 and needs no alert.
- **F6 (added in review, outside hash)** — a non-releasable trip landing while a stale trip is latched raises no False→True driver edge; the driver now journals it as its own `KILL_SWITCH_ACTIVATED` so gate-4 evidence is not masked.

## 4. Decisions (operator, 2026-10-07: D1 = A, D2 = re-pin now once, D3 = remove the dead path)

- **D1 kill switch**: A) release only a stale-data trip on DATA RECOVERED, journal `KILL_SWITCH_RELEASED`, never release drawdown/broker/daily-limit trips; B) keep latch, alert only; C) leave as is.
- **D2 timing of the re-pin**: re-pin now (reset the 6 banked sessions) vs defer hash-scope fixes until E008 closes (keep the count, accept latch risk) vs batch with anything the debugging sessions find.
- **D3 diagnostics**: remove the dead path (options structures have no 1m candles) vs fix the schema.

## 5. Sequence and constraints

1. Approve D1–D3. 2. Implement F2–F5 with failing tests first, in this worktree. 3. Code-debugging session over the diff and the five hash-scope areas (run before the re-pin so all hash-scope defects land in ONE re-pin). 4. Full regression (known reds only: analog_path×2, g1_closure_guard×2, ptms repo guard). 5. Push, PR, merge. 6. Repo debugging session.

**Merge timing.** Today's orchestrator was started at 13:00 from old code and will NOT auto-stop: press Ctrl+C after ~15:45 or tomorrow repeats I1 (IgnoreNew). Merge only after today's session has finalized and before 09:10 on 10-08 (the task runs whatever F:\Nifty has checked out; a supervisor revive mid-day would load new code under an old window).
