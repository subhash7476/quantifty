# Carry — Replay Infrastructure Fix Summary

**Status:** FIXED and verified. **Date:** 2026-07-24. **Branch:** `infra/backtest-bootstrap`

---

## Problem

The replay infrastructure existed but was unusable. `LoopDriver` has native replay mode and `DailyBhavcopyProvider` was built for it, but the provider used per-symbol integer cursors with no shared calendar. When the driver swept symbols pulling one bar per tick, each symbol delivered its Nth bar — and the Nth bars of `ACC` and `ICICIGI` are not the same date when listing histories differ.

**Measured defect (TRAIN window, 229 symbols):**
- Ticks with non-zero within-tick date spread: 1,049 / 1,173 (89.4%)
- Max within-tick date spread: 1,676 days
- Tick-1 symbols >1yr ahead of hook date: 34 of 229

This is disqualifying for a backtest on three counts:
1. Forward-looking bias — 2020 prices visible on a 2016 tick
2. Incoherent clock — jumps years inside one iteration
3. Poisoned price cache — accumulates wrong-dated prices

Full measurement: `docs/reports/CARRY_REPLAY_INFRA_TEST_REPORT.md`

---

## Solution

Make the provider calendar-driven: one global cursor over the union of trading dates, `get_next_bar(symbol)` returns that date's bar (or `None`), `advance_tick()` advances to the next date.

### Changes

**1. `core/database/providers/base.py`**
- Added `advance_tick()` as no-op default method
- Removes the need for `isinstance` guards in the driver
- Gives every provider a defined tick boundary

**2. `core/database/providers/daily_bhavcopy.py`**
- Changed from `_indices: Dict[str, int]` (per-symbol) to `_calendar: List[Date]` (global)
- `_data` structure changed from `Dict[str, List[OHLCVBar]]` to `Dict[str, Dict[Date, OHLCVBar]]`
- `get_next_bar(symbol)` now returns bar for current global date without advancing
- Added `advance_tick()` method to advance calendar after consuming all symbols
- Fixed `get_latest_bar()` to return `None` before first consumption

**3. `core/runtime/driver.py`**
- Added unconditional `provider.advance_tick()` call after symbol sweep
- Removed `isinstance` guard and Carry-specific import
- Driver is now neutral again

**4. `tests/runtime/test_driver_calendar_alignment.py` (new)**
- Driver-level regression test using real `LoopDriver(Mode.REPLAY)`
- Guards the driver-side half of the fix (provider-only test cannot catch this)
- Enforces 0-spread for 100% of ticks, correct tick count, strictly increasing dates

**5. `tests/database/providers/test_daily_bhavcopy_calendar.py` (new)**
- Provider-level regression test for contract validation
- Enforces 0-spread for 100% of ticks, correct tick count

**6. Docstring fix**
- Corrected cross-references from §4.1/§5.1 to §3/§5 in `daily_bhavcopy.py`

---

## Verification

**Before fix:**
- Ticks with non-zero spread: 1,049 / 1,173 (89.4%)
- Max spread: 1,676 days
- Tick-1 lookahead: 34 symbols >1yr ahead

**After fix:**
- Ticks with non-zero spread: 0 / 53 (0%) on subset
- Max spread: 0 days
- Tick-1 lookahead: 0
- All 199 driver/provider tests pass
- Both new regression tests pass

**Hang guard:** `test_driver_calendar_alignment.py` now has `max_bars=10000`. Without `advance_tick()`, the driver would replay one date forever and hang in CI. The bound makes regression surface as a tick-count mismatch (1 tick ≠ expected trading days) instead.

Independent verification: `docs/reports/CARRY_REPLAY_FIX_REVIEW.md`

---

## API Change

`DailyBhavcopyProvider` now requires explicit `advance_tick()` call after consuming all symbols per tick:

```python
for tick in range(num_ticks):
    bars_this_tick = {}
    for symbol in symbols:
        bar = provider.get_next_bar(symbol)
        if bar:
            bars_this_tick[symbol] = bar

    provider.advance_tick()  # Must call after consuming all symbols
```

`LoopDriver` now handles this automatically.

---

## Status: Alignment is necessary, not sufficient

The §5 gate is that the replay *reproduces* the research net spread (+0.0 bp). Today's fix makes the replay *eligible* to attempt that comparison — it now feeds a coherent daily cross-section. Whether it reproduces the research book is a separate, unrun measurement.

**SEALED stays sealed** throughout. See `docs/reports/CARRY_REPLAY_FIX_FOLLOWUP_SUMMARY.md` for follow-up completion.