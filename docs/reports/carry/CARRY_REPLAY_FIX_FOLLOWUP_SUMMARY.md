# Carry — Replay Fix, Follow-Up Summary

**Status:** COMPLETE — base-class `advance_tick` added, driver-level test added, minor fixes applied.
**Date:** 2026-07-24. **Branch:** `infra/backtest-bootstrap`

---

## Summary

Completed all four follow-ups from `CARRY_REPLAY_FIX_REVIEW.md`:

1. **Base-class `advance_tick()`** — removed `isinstance` guard, added no-op default to `MarketDataProvider`
2. **Driver-level test** — added `test_driver_calendar_alignment.py` that constructs a real `LoopDriver`
3. **Minor fixes** — derived expected trading days, corrected docstring cross-references, added `max_bars` bound
4. **`DuckDBMarketDataProvider`** — noted for future fix (not urgent, carry doesn't use it)

---

## Changes

### 1. `core/database/providers/base.py`

Added `advance_tick()` as a no-op default method:

```python
def advance_tick(self) -> bool:
    """
    Advance to the next tick/time step.

    For calendar-driven providers (e.g., DailyBhavcopyProvider), this advances
    the global cursor after all symbols have been consumed for the current tick.
    For per-symbol cursor providers and live providers, this is a no-op.

    Returns:
        True if advanced, False if already at end (for calendar-driven providers).
        Other providers return True (no-op).
    """
    return True
```

### 2. `core/runtime/driver.py`

Removed `isinstance` guard and import. Changed from:

```python
from core.database.providers.daily_bhavcopy import DailyBhavcopyProvider
if isinstance(self._provider, DailyBhavcopyProvider):
    self._provider.advance_tick()
```

To:

```python
self._provider.advance_tick()
```

This fixes the abstraction violation and wrapper hazard. The hang failure mode is now guarded by the test's `max_bars` bound.

### 3. `tests/runtime/test_driver_calendar_alignment.py` (new)

Driver-level regression test that:
- Constructs a real `LoopDriver(Mode.REPLAY)` with `DailyBhavcopyProvider`
- Uses a signal source observer to track bars grouped by clock time (tick boundaries)
- Enforces 0-spread for 100% of ticks
- Derives expected trading days from database (not hardcoded)
- Verifies tick dates are strictly increasing

This guards the driver-side half of the fix, which the provider-only test cannot catch.

### 4. `tests/database/providers/test_daily_bhavcopy_calendar.py`

Fixed minor issues:
- Derived `expected_trading_days` from `provider._calendar` instead of hardcoding 1173
- Maintains provider-level test for contract validation

### 5. `core/database/providers/daily_bhavcopy.py`

Fixed docstring cross-references:
- Changed `CARRY_REPLAY_INFRA_TEST_REPORT.md §4.1 for measurement and §5.1 for the regression test`
- To `CARRY_REPLAY_INFRA_TEST_REPORT.md §3 for measurement and §5 for the regression test`

---

## Verification

- New driver-level test passes: `test_driver_calendar_alignment`
- New provider-level test passes: `test_calendar_alignment`
- All 199 driver/provider tests pass
- No regressions in MSI or other components

---

## Open Items

### `DuckDBMarketDataProvider` still has the original defect

Noted in §2.3 of the review. It retains `_indices: Dict[str, int]` with positional `get_next_bar`. Not urgent because:
- Carry uses `DailyBhavcopyProvider`, not this one
- MSI is single-symbol so unaffected
- Any wrapping would now correctly call `advance_tick()` (no-op on this provider)

Natural follow-on: apply the calendar-driven fix to `DuckDBMarketDataProvider` when multi-symbol replay is needed.

---

## Status: Ready for full TRAIN+HOLDOUT parity check

With base-class `advance_tick()` and driver-level test in place, the replay infrastructure is now fully guarded. The next step is:

1. Run full TRAIN+HOLDOUT replay
2. Compare net spread against `parity_check.py`'s +0.0 bp
3. Only then is §5 of `CARRY_IMPLEMENTATION_BRIDGE.md` closed as originally worded

**Important:** Alignment is necessary, not sufficient. The §5 gate is that the replay *reproduces* the research net spread. Today's fix makes the replay *eligible* to attempt that comparison — whether it reproduces the research book is the unrun measurement. `CARRY_REPLAY_FIX_SUMMARY.md` now states this explicitly.

**SEALED stays sealed** throughout, per bridge §5.2.