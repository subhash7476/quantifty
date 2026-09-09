# Writer-Worker Redesign — Implementation Review (F1/F3/F4)

**Reviewer:** Claude (Opus 4.8)
**Date:** 2026-08-10
**Branch:** `feat/ops-orchestrator`
**Scope:** the 7-commit writer-worker range `372945f..52b3d28` against
`docs/superpowers/specs/2026-08-10-writer-worker-redesign-design.md`.

## Verdict

**Architecture sound; one merge-blocker, now root-caused and fixed in this review.** The
branch faithfully implements the design (single-writer worker, event-loop offload,
connect-then-async backfill, two-queue command model). But as delivered it was **not green** —
the committed "F4 proof" test failed consistently — and the diagnosis reordered once the cause
was isolated by experiment. Two further findings remain (one HIGH, one latent MEDIUM).

## The failing test, and its real cause (FIXED)

`tests/database/ingestors/test_reader_no_contention.py::test_cross_process_reader_lands_during_active_writing`
requires the retrying cross-process reader to land ≥ 48 / 50 opens. As delivered it failed
three times running (ok = 42, 41, 42 ≈ 82–84%).

**Cause — `Aggregate` pile-up starving the writer window, not a writer-side bug.** The test's
load thread submits `Aggregate(["X"])` every 0.1 s, and because every tick timestamp is 2020
against a 2026 `current_minute`, **every pass finds a completed bar and opens
`live_candles_writer` RW.** `LiveBufferWriter._run` drained *all* pending control commands
before each tick batch, so piled Aggregates ran back-to-back — RW occupancy on
`candles_today` went far above the isolated-open rate the bounded-retry reader was validated
against (design §1.1 fact 4: 37/40 @ 13 writes/0.6 s), starving the child reader.

Note this is also the production risk: the main loop posts one `Aggregate(~200 symbols)` every
1.5 s (`market_ingestor.py:299`); at the team's own measured ~27 ms/RW-open, a minute-boundary
pass writing 200 symbols is ~5.4 s — 3.6× the cadence — so passes fall behind, the unbounded
control queue grows, and drain-all-first then runs several full aggregations back-to-back
while the tick queue backs toward its 50k bound.

**Fix applied in this review** (`live_buffer_writer.py`, uncommitted): coalesce redundant
`Aggregate`s in the control drain — an `Aggregate` re-reads current state, so N piled ones are
identical to the newest; `RecoverBars`/`Purge` are never coalesced. One edit, no other change.
Result: the F4 proof passes **3/3**, full ingestor suite **15/15**. This confirms the red was
reader-starvation, and that the writer-retry gap below is orthogonal (it does *not* explain the
failing test — a retrying writer would contend *more*, if anything lowering the reader rate).

## HIGH-1 — Tick-flush batch is dropped permanently on a writer RW-open failure

Independent of the test above, the worker's tick path can silently lose data. In `_run`,
`_coalesce_ticks` dequeues up to 500 frames and calls `_flush_ticks`; if `live_ticks_writer`'s
RW open raises, the exception propagates to `_run`'s `except` and **the already-dequeued batch
is gone** — ticks are not re-derivable. Cross-process readers using `live_buffer_reader()` do
open `ticks_today` RO (`manager.py:308-312`), so the collision is reachable, and per design
§1.1 fact 2 RO and RW cannot coexist on one file.

Contributing root cause — a retry-string mismatch:

- The **reader** retry (`manager.py:320-322`) matches the actual Windows errors:
  `"being used by another process"`, `"Conflicting lock"`, `"Cannot open file"`.
- The worker's `live_ticks_writer` / `live_candles_writer` have no retry of their own and lean
  on `_duckdb_connect`'s generic retry (`manager.py:92`), which only fires on `"could not
  open"` — **a string DuckDB never emits for this contention** (the real message is
  `Cannot open file … used by another process`). So the writer never retries and raises.

For **candles** this self-heals — aggregation is idempotent and re-runs from the last real bar
next cycle — so the impact is delayed writes plus ERROR-level noise for an expected-transient
event (the `Aggregation failed for X …` lines in the logs). For **ticks** it is permanent
loss.

**Fix:** wrap `live_ticks_writer` / `live_candles_writer` opens in the same bounded retry the
reader uses, matching the real error strings, raising only after the bound. Apply with care and
re-run the F4 proof — a writer that retries holds contention longer, so confirm it does not
depress the reader landing rate. Do **not** pre-set a new test threshold; pick it after the
retry lands and the clean rate is known.

## MEDIUM-1 (latent) — Second live-buffer RW path breaches the single-writer invariant

The design's load-bearing invariant is "exactly one thread ever opens the live buffer RW." The
batch `DatabaseManager.live_buffer_writer()` (long-hold, both files — the original F4 culprit)
still exists and is still reachable:

- `core/database/writers.py:78` — `MarketDataWriter.insert_candles_batch`, today branch.
- `scripts/fetch_upstox_historical.py:162`.

Neither is wired into the live loop today (`MarketDataWriter` candle inserts are now test-only;
the fetch script is a manual offline tool), so this is **latent, not active** — but nothing
enforces the invariant, and this path takes a `WriterLock` file lock the worker's narrow
writers do not, so the two would not be mutually excluded. A manual `fetch_upstox_historical.py`
run for *today* during market hours would reopen exactly the long-hold RW the redesign removed.
Per the repo's "delete unused code / no backwards-compat shims" convention, remove the batch
`live_buffer_writer()` and the `writers.py` today-branch, or route both through the worker.

## What's right (keep)

- **F3 fully closed:** `_handle_message` does only `enqueue_frame(raw bytes)`; all parse +
  tz-conversion + DB moved to the worker; `IST` hoisted to module level; explicit
  `ping_interval=10.0 / ping_timeout=30.0`.
- **Two-queue design is correct:** the unbounded control queue means `Aggregate/RecoverBars/
  Purge` can never raise `Full` or be dropped; drop-oldest applies only to the bounded tick
  queue — commands are structurally un-droppable.
- **Shutdown drain** (`_final_drain`) is correct and tested (50/50 persisted); daemon `stop`
  orders WS-stop before writer-stop.
- **Synthetic/real precedence** is order-safe both ways (recovery `INSERT OR IGNORE
  is_synthetic=TRUE`; aggregator `ON CONFLICT DO UPDATE is_synthetic=FALSE`; last-real-bar
  query filters `is_synthetic=FALSE`) — no sequencing guard needed, per design §6.
- DDL-once bootstrap; per-symbol short-lived candle writes verified by test; tick path proven
  never to open candles; no dangling `TickBuffer` references.

## Recommended order of work

1. **Merge-blocker — DONE in this review:** `Aggregate` coalescing. F4 proof green 3/3, suite
   15/15. Needs the operator's decision to commit (currently uncommitted working-tree change).
2. **HIGH-1:** bounded retry on the worker write paths, matching the real error strings; re-run
   the F4 proof to confirm the reader rate holds.
3. **MEDIUM-1:** remove or re-route the batch `live_buffer_writer()` path.

---

## Resolution status (implementer, after review)

All three items above are now done by DeepSeek (implementer) on `feat/ops-orchestrator`:

1. **Merge-blocker — committed `3767b27`.** The `Aggregate` coalescing fix was verified on the
   implementer's machine first (F4 proof 5/5, suite 15/15) and committed as-is. No further edit.
2. **HIGH-1 — committed `5fb89fc`.** `manager.py` now has one `_live_connect_with_retry`
   helper that matches the real Windows error strings (`being used by another process` /
   `Conflicting lock` / `Cannot open file`) and is used by `live_ticks_writer`,
   `live_candles_writer`, **and** the reader's candles open (unifying the transient-string list
   that was the retry-mismatch root cause). New regression test
   `test_tick_flush_survives_transient_rw_collision` proves a 20-frame batch survives a 3×
   transient RW-open collision (verified it FAILS — n=0, batch dropped — with the retry
   reverted). F4 reader landing rate re-measured at **50/50 across 5 runs** — the retrying
   writer does not depress the reader rate. No threshold change; the existing `ok >= 48`
   assertion holds.
3. **MEDIUM-1 — committed `143f042`.** Both latent callers re-routed to the narrow short-lived
   `live_candles_writer()` (`writers.py` today-branch, `fetch_upstox_historical.py` live-buffer
   write); the batch `DatabaseManager.live_buffer_writer()` — the original F4 long-hold — is
   deleted (zero remaining callers). `MarketDataWriter.insert_candles_batch` today-path smoke-
   tested green. The single-writer invariant is now structurally un-breachable: no code path in
   the repo opens the live buffer RW except the worker's narrow writers.

Regression at close: ingestor suite **16/16**, `tests/database/` **19/19**,
`tests/nifty_shield_paper/` + `test_nifty_shield_paper_execution.py` + `tests/ops/` **86/86**.
