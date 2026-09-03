# DayType 13:00 Coverage Gate — Match the Engine, Not a Row Count

**Date:** 2026-09-03 · **Branch:** MRLC-testing · **Component:** `scripts/daytype/publish_live_fact.py`

## 1. Problem

On 2026-09-03 the 13:00 DayType fact did not publish. All five orchestrator children
were alive and the live buffer held the morning: `NSE_INDEX|Nifty 50` had **225** of 226
session bars, 09:15 → 13:00, missing only the single interior minute **12:53** (a bar
dropped during live WebSocket ingest; `RecoveryManager` never backfilled it).

The Sep-2 fix (`6140b59`) added a source-acceptance gate in `_today_bars` requiring
`len(frame) >= REQUIRED_BARS` (**226**, exactly 09:15..13:00 inclusive). A single dropped
minute anywhere in the window leaves ≤225 rows, so the frame was rejected, the VIX lookup
(same ladder) returned `None`, and `publish_live` returned not-ready. The retry window
(13:00→13:10) could not help: every retry saw the same 225-bar frame.

This is a **new** failure mode, distinct from the three the Sep-2 RCA fixed. The morning
open (09:15) is present; the per-day store is absent (Cause B already handled). It is a
lone mid-session dropped bar, and today was the first day one occurred.

## 2. Root cause: the gate is stricter than the engine that consumes the frame

`core/state/daytype_engine.py` triggers the `13pm` checkpoint on **wall-clock time**, not
bar count. Its own comment (lines 66–69):

> Bar count thresholds assume continuous 1m bars from 9:15 open. These are kept as
> reference but **NOT used for triggering — wall-clock time is the primary trigger
> (robust to WebSocket gaps / late starts).**

The trigger (`on_bar`, lines 284–289):

```python
triggered = bar_time >= wall_time and n_bars >= MIN_BARS_REQUIRED[cp]   # 13pm: 100
```

So the engine emits `13pm` on the **first bar whose timestamp ≥ 13:00**, provided ≥100
bars have accumulated. `CHECKPOINT_BARS['13pm'] = 225` is used only in the
timezone-naive backtest fallback, never in live publishing (frames carry timestamps).

The engine was **designed to tolerate exactly this gap.** The Sep-2 `REQUIRED_BARS = 226`
gate defeated that robustness. The RCA's premise — "the engine emits `13pm` only at bar
index 225" — is true only of the fallback path, not the wall-clock path live publishing
uses.

### Empirical confirmation (2026-09-03)

Feeding today's 225-bar gapped frame (missing 12:53, last bar 13:00) directly into
`compute_13pm_state`, bypassing the gate, produced a valid fact:

```
checkpoint='13pm', predicted_state='BearTrend', confidence=0.6973, p_choppy=0.6973
```

The engine handled the gap. The gate was the sole blocker.

## 3. Fix: coverage = "reaches 13:00", not "has 226 rows"

Replace the single acceptance test in `_today_bars`. A source is accepted iff:

1. its session bars **reach the checkpoint** — the feed has at least one bar at
   minute ≥ `CHECKPOINT_MIN` (13:00); **and**
2. it holds ≥ `MIN_BARS` (100) session bars.

Interior gaps are tolerated. This mirrors the engine's trigger exactly
(`bar_time >= 13:00 and n_bars >= 100`), so any frame the gate accepts, the engine can
process — no silent rejection three frames downstream.

### Frame construction

`_session_frame` keeps its 09:15 lower bound. The accepted frame is session bars from
09:15 up to **and including the first bar at minute ≥ 13:00**. Formally:

- From the raw df, take session bars (minute ≥ `SESSION_OPEN_MIN` = 555).
- `reaches = max(session bar minute) >= CHECKPOINT_MIN` (780).
- The frame is bars up to and including the first bar with minute ≥ 780.
- Accept iff `reaches and len(frame) >= MIN_BARS`.

In the common case (13:00 bar present, today's case) the last frame bar is exactly 13:00.
In the rare case where the **13:00 bar itself** is missing but 13:01 has arrived, the frame
includes the 13:01 bar and the engine triggers on it — the fact fires without any fill.
This one bar of "lookahead" (13:01 vs 13:00) is exactly what the engine's own `>= 13:00`
trigger already does; it occurs only when 13:00-exact is absent.

### Why this is safer than the 226 gate

The "silently wrong fact" the Sep-2 RCA feared (a window truncated at 11:29 stamped
`13pm`) is impossible: a frame whose bars stop before 13:00 has no ≥13:00 bar → `reaches`
is false → rejected. The time-based test is a strictly stronger coverage guard than a row
count, which could in principle be met by 226 dense/duplicate rows that never reach 13:00.

### VIX repaired for free

`vix_at_checkpoint` → `_today_bars(VIX_SYMBOL)` → same gate. Fixing `_today_bars` fixes
VIX. Its value becomes the close of the first VIX bar ≥ 13:00 — identical to today's
semantics whenever the 13:00 bar exists, and a sensible fallback (13:01 close) when it is
the missing minute. Docstring updated from "at or before 13:00" to reflect the ≥13:00
first-bar semantics.

## 4. What does NOT change

The Sep-2 fix's genuine repairs stay intact:

- **The ordered ladder** per-day-store → live-buffer. A partial per-day store is still
  rejected — now because it does not reach 13:00 — and the ladder falls through to the
  live buffer (Cause B).
- **The one-line skip diagnostic** naming every source and its coverage. The reject line
  changes wording from "short of 13:00, rejected" (still accurate) to also cover the
  below-`MIN_BARS` case; not-ready still names each source.
- **`fetch_upstox_historical`'s `_session_closed` gate** — untouched.
- **No backfill / network fetch is added.** The retry window (13:00→13:10, gated on *bar*
  time) already lets the feed catch up on its own; the fix needs no new data source.

`REQUIRED_BARS` (226) is removed from the acceptance path. `MIN_BARS` (already
`MIN_BARS_REQUIRED['13pm']` = 100 in `publish_facts.py`) is re-imported into
`publish_live_fact.py`.

## 5. Tests (`tests/daytype/test_daytype_facts.py`)

1. **New, pinned to 2026-09-03** — frame 09:15→13:00 with one interior minute (12:53)
   dropped (225 bars, reaches 13:00) → **accepted**, publishes `13pm`. Reproduces today's
   exact miss; fails before the fix.
2. **New** — frame reaching 13:00 but with only ~90 bars → **rejected** on `MIN_BARS`.
3. **New** — exact-13:00 bar missing, 13:01 present → **accepted** (engine fires on 13:01).
4. **Regression preserved** — 43-bar 09:15→09:57 per-day store → rejected (doesn't reach
   13:00) → falls through to live buffer.
5. **Regression preserved** — source truncated before 13:00 (late 11:39 start) → rejected,
   skip line names it (the 2026-08-31 case; the existing regression test).

All existing `tests/daytype/`, `test_publish_hook_live_dry_run.py`, and
`tests/nifty_shield_paper/` tests must stay green.

## 6. Acceptance

- The three new tests pass; the two named regression tests still pass; the full
  `tests/daytype` + `test_publish_hook_live_dry_run` + `tests/nifty_shield_paper` suite is
  green.
- End-to-end: `python scripts/daytype/publish_live_fact.py --date 2026-09-03 --db <scratch>`
  publishes a `13pm` fact from the live buffer (rather than NOT READY), matching the
  §2 empirical result.

## 7. Flagged, not fixed (out of scope)

`DayTypeEngine` has a pre-existing label quirk: `cluster_id` maps through `CLUSTER_NAMES`
(`2 → BearTrend`) while `confidence` tracks `proba.max()` and `p_choppy = proba[2]`. Today's
output read `BearTrend` with `p_choppy=0.6973` as the max class. This predates and is
unrelated to the coverage gate; noted here, not touched.
