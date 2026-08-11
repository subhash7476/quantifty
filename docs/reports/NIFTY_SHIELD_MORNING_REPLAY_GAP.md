# NiftyShield — Morning-Replay Gap (mid-day starts miss DayType facts)

**Status:** OPEN. Distinct from, and downstream of, the live-buffer data-root fix
(commit `c098a09`). That fix was necessary to make the driver read *any* live bars;
this gap is why a bar-reading driver still misses the day's DayType checkpoint facts
when the session starts mid-session.

**Date:** 2026-08-11

---

## Summary

`LiveDuckDBMarketDataProvider` seeds its per-symbol cursor to the **latest** bar in
the live buffer at startup and thereafter delivers only bars **newer** than that
cursor. It never replays the bars already in today's buffer. So a session that
starts after 09:15 sees only the bars that arrive *after it started* — it does not
reconstruct the morning. The DayType engine's checkpoints (10am / 11am / 13pm) each
require a minimum number of in-order 1m bars accumulated from the 09:15 open, so a
mid-day start cannot reach them, and the corresponding facts never fire.

This is a **restart-resilience** gap. A session started **before the open** and left
running accumulates bars forward from 09:15 naturally and hits every checkpoint — no
replay needed. The gap bites only when the session (or the whole ops stack) is
(re)started during the trading day, which is exactly what happened today.

---

## Symptom (2026-08-11)

- Ops stack recovered from the stale-lock cascade; the session (`session.py`, pid
  3240) reached `RUNNING` at **12:44** with healthy feeds.
- Once the data-root bug was fixed, the provider *can* read the live buffer — but a
  session that first runs at 12:44 seeds its cursor to the 12:44 bar and only sees
  bars from 12:44 forward: ~16 bars by 13:00.
- The 13pm checkpoint needs **≥100** bars (see thresholds below). 16 < 100 → no
  13:00 fact. The 10am/11am checkpoints were already past before the session existed.
- Net: all three of today's DayType facts are unrecoverable regardless of the
  data-root fix.

---

## Mechanism

### Provider seeds to "now", delivers only forward bars

`core/database/providers/live_market.py`:

- `_initialize_symbols()` loads recent bars and sets
  `self._last_timestamps[symbol] = df.iloc[-1]["timestamp"]` — the **most recent**
  bar at startup.
- `_poll_for_new_bars()` then queries `start_time = last_ts + 1s` — strictly bars
  **after** the seed. The morning's bars (already in the buffer) are on the wrong
  side of the cursor and are never emitted.
- If `_initialize_symbols` found nothing, the first poll takes the `else` branch
  (`limit=1`, most-recent bar only) — still no backfill.

### DayType checkpoints need bars from the open

`core/state/daytype_engine.py` (`on_bar` accumulates 1m Nifty bars; a checkpoint
fires when wall-clock ≥ its time **and** at least the min-bar floor has arrived —
`triggered = bar_time >= CHECKPOINT_WALL_TIMES[cp] and n_bars >= MIN_BARS_REQUIRED[cp]`):

| Checkpoint | Wall time (`CHECKPOINT_WALL_TIMES`) | Reference bars (`CHECKPOINT_BARS`, not used to trigger) | Min bars floor (`MIN_BARS_REQUIRED`) |
|---|---|---|---|
| 10am | 10:00 | 45 | 20 |
| 11am | 11:00 | 105 | 50 |
| 13pm | 13:00 | 225 | **100** |

`CHECKPOINT_BARS` are reference only; the **primary trigger is wall-clock time**,
with `MIN_BARS_REQUIRED` as a floor (lowered to tolerate ~50% WebSocket coverage).
Both assume continuous 1m bars from the 09:15 open. A mid-day start starves the
`n_bars` counter.

So even with the data-root fix delivering live bars, `n_bars` climbs only from the
session's start time. For a 12:44 start, ~16 bars exist by 13:00 — below the 100
floor — so no 13pm fact fires *at* 13:00.

**Worse than "never" — a late start can fire mis-windowed.** Because the trigger is
`bar_time >= 13:00 AND n_bars >= 100`, a 12:44 start reaches 100 forward bars around
**14:24**, where `bar_time (14:24) >= 13:00` also holds → the 13pm checkpoint can
fire *late*, computing "13pm" features from bars **12:44–14:24** instead of
**09:15–13:00**. That is a fact against the wrong window fed to the model — arguably
worse than a clean miss. Either outcome (silent miss if <100 bars by the 15:30
close, or a mis-windowed late fire) means a mid-day start cannot produce a **valid**
DayType checkpoint fact.

---

## Why the data-root fix does not cover this

The data-root fix (`c098a09`) repaired *where* the provider reads (the ingestor's
live buffer instead of the nonexistent `data/nifty_shield/live_buffer/`). It changed
0 bars → forward bars. It did **not** change *which* bars the provider chooses to
emit — that is still "everything after startup". The two are independent:

- Data-root bug: provider read the wrong file → **0** bars.
- Replay gap: provider reads the right file but **skips the morning** → forward-only.

Both must be closed for a mid-day (re)start to produce the day's facts.

---

## Design considerations (not yet decided)

The naive fix — "seed the cursor to start-of-day and replay the buffer" — is not
free, because in LIVE PAPER mode **bars drive the entire loop**, not just the DayType
fact path. Replaying four hours of bars at startup would also run the strategy,
execution handler, and marks over stale timestamps, potentially manufacturing
retroactive paper trades at prices that were never actionable. Any fix has to
separate "reconstruct read-only day state (DayType features/facts)" from "act on
live prices".

Options to weigh (each has a different blast radius; none is endorsed here):

1. **Read-only morning backfill into the DayType engine only.** On startup, load the
   day's buffered 1m Nifty (and BankNifty, Block H) bars directly into the engine's
   accumulators via `on_bar`/`on_bn_bar`, *outside* the trade loop, then let the live
   provider continue forward for execution. Keeps trades on live bars; reconstructs
   only the fact path. Most surgical for the stated goal (facts), but adds a
   startup seam the engine must expose.
2. **Provider replay window with an execution guard.** Seed the provider cursor to
   start-of-day and emit the backlog, but gate the execution/marks path to skip
   fills on bars older than session start (facts still compute from the full stream).
   Broader change to the driver's live semantics; higher risk.
3. **Operational-only: mandate start-before-open.** Treat mid-day starts as
   fact-lossy by policy; the orchestrator already parks until market open, so a
   before-open start is the intended path. Cheapest (no code), but leaves the stack
   fragile to any intraday restart — the exact failure mode seen today.

The read-only backfill (option 1) matches the platform's "analytics produce facts,
runtime is read-only" principle most closely: the DayType fact is a read-only
computation over the day's bars and has no reason to depend on trade-loop timing.

## Interaction with start-before-open

Even option 1 is only needed for restarts. The **first, clean** run of the day —
orchestrator parks until 09:15, session starts before open — reaches every
checkpoint without any replay. So the practical priority order is:

1. Confirm the data-root fix end-to-end on a **start-before-open** run
   (`bars_processed` climbing, 10:00 fact firing). This is the real verification of
   `c098a09` and needs no new code.
2. Then decide whether intraday restart-resilience (this gap) is worth option 1/2,
   or whether the start-before-open policy (option 3) is acceptable.

---

## Verification plan for the data-root fix (prerequisite)

- Start the ops stack **before 09:15** tomorrow.
- Assert `data/nifty_shield/heartbeat.json` `bars_processed` climbs after open.
- Assert the 10:00 fact appears in `data/nifty_shield/facts.duckdb` (file created,
  a DayType row for the 10am checkpoint).
- If all three hold, `c098a09` is verified and this gap is the sole remaining blocker
  for intraday-restart fact recovery.

---

## Key references

| Item | Location |
|---|---|
| Provider seed-to-latest | `core/database/providers/live_market.py` (`_initialize_symbols`, `_poll_for_new_bars`) |
| DayType checkpoint gating | `core/state/daytype_engine.py` (`on_bar`, `MIN_BARS_REQUIRED`, `CHECKPOINT_BARS`, `CHECKPOINT_WALL_TIMES`) |
| Data-root fix (prerequisite) | commit `c098a09`; `core/database/manager.py` (`live_buffer_root`), `scripts/nifty_shield_paper/session.py` |
| Session fact store | `data/nifty_shield/facts.duckdb` (per `session.py` docstring) |
