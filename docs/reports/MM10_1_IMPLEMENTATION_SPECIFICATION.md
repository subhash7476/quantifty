# MM10.1 — Implementation Specification
## Safety Hardening & MarginCalculator Protocol v2

**Date:** 2026-06-30  
**Author role:** System Architect  
**Milestone predecessor:** `mm9.5-complete` (tag, commit `1bb6b60`)  
**Approved architecture:** `docs/reports/MM10_ARCHITECTURE_ROADMAP.md` + `docs/reports/MM10_ARCHITECTURE_REVISION.md`  
**Status:** For Technical Lead review

---

## 1. Objective

Close the one known production safety gap before any MM10 capability work begins, and formalise the `MarginCalculator` protocol so all subsequent milestones build against a stable interface.

**S1 — Absent/Corrupt SPAN Hard Refusal**  
LIVE F&O must refuse startup when the SPAN snapshot is absent, corrupt, or unreadable. The current try/except swallow that falls back to `MarginTracker` with a logged warning is not acceptable for production.

**S2 — MarginCalculator Protocol v2**  
Promote `get_incremental_margin(...)` from an off-protocol extension on `SpanMarginCalculator` to a formal method on the `MarginCalculator` protocol. Retire the `hasattr` duck-typing in `ExecutionHandler`. Add a flat-rate implementation to `MarginTracker` so it satisfies v2. No formula changes anywhere.

---

## 2. Current Behaviour

### 2.1 S1 — Current startup flow

**`scripts/fno_runner.py:138-170` (condensed):**

```
if derivatives:
    span_repo = SpanRepository()
    expected = expected_span_date()
    try:
        span_snapshot = span_repo.load(expected)
        span_readiness = build_span_readiness(span_repo)
        logger.info(...)
    except Exception:
        logger.warning("SPAN snapshot absent ... proceeding with flat-rate MarginTracker")
        # span_snapshot stays None
        # span_readiness stays None
```

When the `except` branch is taken:
- `span_snapshot` is `None` → `ExecutionHandler` receives no `span_snapshot` → constructs `MarginTracker` (flat 20%)
- `span_readiness` is `None` → `LoopDriver` receives `span_readiness=None`

**`core/runtime/driver.py:444-483` — `_check_span_readiness()`:**

```python
if not (self._config.is_live
        and has_derivatives(self._config.symbols)
        and self._span_readiness is not None):  # ← third condition is False
    return True  # vacuous pass
```

Because `self._span_readiness is None`, the gate is a no-op. The session runs on flat-rate `MarginTracker` without any readiness enforcement.

**Net result:** A LIVE F&O session with absent or corrupt SPAN data does not refuse. It logs one warning and runs — with no capital protection from SPAN parameters.

---

### 2.2 S2 — Current `MarginCalculator` protocol (v1)

**`core/risk/margin_calculator.py`:**

```python
class MarginCalculator(Protocol):
    margin_rate: float
    def get_exposure(self, current_prices, symbol=None) -> float: ...
    def get_used_margin(self, current_prices) -> float: ...
```

`get_incremental_margin` is **not in the protocol**.

**`core/risk/span/span_calculator.py:119-142`:**  
`SpanMarginCalculator` defines `get_incremental_margin(symbol, quantity, price, lot_size=1.0) -> float` as an extension method, outside the protocol.

**`core/execution/margin_tracker.py`:**  
`MarginTracker` has no `get_incremental_margin` method.

**`core/execution/handler.py:1172-1185`:**

```python
used_current = self.margin_tracker.get_used_margin(prices)
if hasattr(self.margin_tracker, 'get_incremental_margin'):
    incremental_est = self.margin_tracker.get_incremental_margin(
        order.symbol, order.quantity, current_price,
        lot_size=effective_multiplier,
    )
else:
    incremental_est = (
        self._estimate_required_margin(order.quantity * effective_multiplier, current_price)
        * self.margin_tracker.margin_rate
    )
```

`_estimate_required_margin(quantity, price) -> float` at `handler.py:1105-1108` returns `quantity * price`.

**The `else` branch equivalent:** `quantity * effective_multiplier * price * margin_rate`  
Which in protocol terms equals: `abs(quantity) * lot_size * price * margin_rate`

**Stale test at `tests/risk/span/test_span_composition.py:55`:**

```python
assert not hasattr(mt, "get_incremental_margin")
```

This assertion will break when `MarginTracker` gains the method. It must be replaced.

---

## 3. Gap Analysis

### S1 gap

| Condition | Expected | Actual |
|-----------|----------|--------|
| LIVE F&O, SPAN absent | Startup refused (BLOCK) | WARNING logged, flat-rate proceeds |
| LIVE F&O, SPAN corrupt | Startup refused (BLOCK) | WARNING logged, flat-rate proceeds |
| PAPER F&O, SPAN absent | WARNING, flat-rate proceeds | WARNING, flat-rate proceeds ✓ |
| Equity only | No SPAN check | No SPAN check ✓ |
| Backtest | No SPAN check | No SPAN check ✓ |

Root cause: When `span_repo.load()` raises, the exception is swallowed with a warning and `span_readiness` is left as `None`. The driver's `_check_span_readiness` gate has a `self._span_readiness is not None` guard, so it passes vacuously.

### S2 gap

| Item | Status |
|------|--------|
| `get_incremental_margin` on `SpanMarginCalculator` | Implemented — off-protocol |
| `get_incremental_margin` on `MarginCalculator` protocol | **Absent** |
| `get_incremental_margin` on `MarginTracker` | **Absent** |
| Detection in `handler.py` | `hasattr` duck-typing |

Risk: Any future `MarginCalculator` implementation that coincidentally defines `get_incremental_margin` with a different signature would be silently invoked by the handler with no type or protocol check.

---

## 4. Exact Production Changes

### S1 — `scripts/fno_runner.py`

**Verify imports** (near top, with existing SPAN imports):

```python
from core.risk.span.span_readiness import (
    SpanReadinessVerdict,
    build_span_readiness,
)
from core.instruments.master_readiness import ReadinessState
```

`build_span_readiness` and `ReadinessState` are already present. Add `SpanReadinessVerdict` if missing.

**Narrow the exception clause** and **replace the inline closure** with a named module-level helper.

**Step 1 — Add a named helper** near the top of `fno_runner.py` (after the existing `_make_live_broker_positions` function, before `build_runner`):

```python
def _make_span_block_checker(expected_date: date) -> Callable[[], SpanReadinessVerdict]:
    """Return an always-BLOCK SPAN readiness checker for the given date.

    Used when SpanRepository.load() fails on a LIVE F&O startup — the checker
    is injected into LoopDriver so _check_span_readiness() fires and refuses.
    """
    def _check() -> SpanReadinessVerdict:
        return SpanReadinessVerdict(
            state=ReadinessState.BLOCK,
            snapshot_date=None,
            expected_date=expected_date,
            reason=f"SPAN snapshot absent or corrupt for {expected_date} — LIVE F&O refused",
        )
    return _check
```

**Step 2 — Replace the `except Exception` block** at `fno_runner.py:165-170`.

`SpanRepository.load()` documents `FileNotFoundError` (absent file) and `ValueError` (checksum mismatch). `pickle.load()` raises `OSError` on I/O failure and `pickle.UnpicklingError` on corrupt data. These four cover all realistic failure modes; unexpected programming errors propagate.

Current:
```python
    except Exception:
        logger.warning(
            "fno_runner: SPAN snapshot absent for %s — "
            "proceeding with flat-rate MarginTracker",
            expected,
        )
```

Replace with:
```python
    except (FileNotFoundError, ValueError, OSError, pickle.UnpicklingError):
        if execution_mode is ExecutionMode.LIVE:
            span_readiness = _make_span_block_checker(expected)
            logger.error(
                "fno_runner: SPAN snapshot absent or corrupt for %s — "
                "LIVE F&O startup refused (BLOCK injected)",
                expected,
            )
        else:
            logger.warning(
                "fno_runner: SPAN snapshot absent for %s — "
                "proceeding with flat-rate MarginTracker (PAPER/non-LIVE mode)",
                expected,
            )
```

**Add `import pickle`** to `fno_runner.py` if not already present (verify with grep).

**Mechanism:** The always-BLOCK callable satisfies the `Callable[[], SpanReadinessVerdict]` type expected by `LoopDriver`. When `_check_span_readiness()` fires, it calls the checker, receives `ReadinessState.BLOCK`, logs `SPAN_READINESS_BLOCK`, calls `abort_startup()`, and returns `False`. The driver transitions to `STOPPED`. The startup gate code in `driver.py` is not modified.

---

### S2a — `core/risk/margin_calculator.py`

Add `get_incremental_margin` to the protocol and update the docstring to v2:

```python
class MarginCalculator(Protocol):
    """Protocol v2: adds get_incremental_margin for pre-trade margin estimation."""

    margin_rate: float

    def get_exposure(self, current_prices: Dict[str, float],
                     symbol: Optional[str] = None) -> float:
        """Gross notional exposure across the portfolio, or for one symbol."""

    def get_used_margin(self, current_prices: Dict[str, float]) -> float:
        """Estimated margin consumed given current prices."""

    def get_incremental_margin(
        self,
        symbol: str,
        quantity: float,
        price: float,
        lot_size: float = 1.0,
    ) -> float:
        """Margin estimate for a proposed order (pre-trade check)."""
```

---

### S2b — `core/execution/margin_tracker.py`

Add `get_incremental_margin` to `MarginTracker`:

```python
def get_incremental_margin(
    self,
    symbol: str,
    quantity: float,
    price: float,
    lot_size: float = 1.0,
) -> float:
    return abs(quantity) * lot_size * price * self.margin_rate
```

This is numerically identical to the existing `else` branch in handler.py (`quantity * effective_multiplier * price * margin_rate`). No behaviour change for any caller.

---

### S2c — `core/execution/handler.py`

Replace `hasattr` detection block at lines 1176-1185:

Current:
```python
if hasattr(self.margin_tracker, 'get_incremental_margin'):
    incremental_est = self.margin_tracker.get_incremental_margin(
        order.symbol, order.quantity, current_price,
        lot_size=effective_multiplier,
    )
else:
    incremental_est = (
        self._estimate_required_margin(order.quantity * effective_multiplier, current_price)
        * self.margin_tracker.margin_rate
    )
```

Replace with:
```python
incremental_est = self.margin_tracker.get_incremental_margin(
    order.symbol, order.quantity, current_price,
    lot_size=effective_multiplier,
)
```

Do not delete `_estimate_required_margin`. Grep for other call sites first; if none exist, leave it as dead code. Removal is out of scope for MM10.1.

---

## 5. RED → GREEN Implementation Plan

### S1

**RED:** Write tests in `tests/risk/span/test_mm10_1_s1_span_hard_refusal.py`:
- Mock `SpanRepository.load()` to always raise.
- Call `fno_runner.build_runner()` with `ExecutionMode.LIVE` and a derivative symbol.
- Assert `driver._span_readiness is not None`.
- Call `driver._check_span_readiness()` directly.
- Assert it returns `False` and driver reaches `STOPPED`.
- In a separate test, call with `ExecutionMode.PAPER` and assert `driver._span_readiness is None`.

All tests fail (red) before the change.

**GREEN:** Apply the `fno_runner.py` change described in §4 S1.

**Regression:** Full suite. PAPER tests that exercise the no-snapshot path must still see `span_readiness=None` and proceed.

---

### S2

**RED order:**

1. `test_margin_tracker_satisfies_protocol_v2` — `isinstance(MarginTracker(pt), MarginCalculator)` or `hasattr(mt, 'get_incremental_margin')`. Fails.
2. `test_margin_tracker_incremental_margin_flat_rate` — numerically assert `mt.get_incremental_margin("X", 2, 100.0, 75.0) == 3000.0` (with `margin_rate=0.2`). Fails.
3. `test_span_calculator_satisfies_protocol_v2` — assert `SpanMarginCalculator` has the method. Passes immediately (regression guard).
4. `test_handler_calls_incremental_margin_via_protocol` — handler with `MarginTracker`, order at margin limit; confirm gate fires via the protocol path.

**GREEN order:**

1. Add `get_incremental_margin` to `MarginCalculator` protocol.
2. Add `get_incremental_margin` to `MarginTracker`.
3. Remove `hasattr` block from `handler.py`.

**Test to update:**

`tests/risk/span/test_span_composition.py:55` — replace:
```python
assert not hasattr(mt, "get_incremental_margin")
```
with:
```python
assert hasattr(mt, "get_incremental_margin")
```

---

## 6. Test Plan

### S1 Tests — new file `tests/risk/span/test_mm10_1_s1_span_hard_refusal.py`

| Test | Description | Pass criterion |
|------|-------------|----------------|
| `test_live_fno_missing_snapshot_injects_block_checker` | `build_runner()` with `ExecutionMode.LIVE`, derivative symbol, repo raises on `load()` | `driver._span_readiness is not None` |
| `test_live_fno_block_checker_returns_block_verdict` | Call the injected checker directly | `verdict.state == ReadinessState.BLOCK` and `verdict.reason` contains "absent or corrupt" |
| `test_live_fno_startup_gate_fires_and_aborts` | Call `driver._check_span_readiness()` with block checker injected | Returns `False` |
| `test_paper_fno_missing_snapshot_proceeds` | `build_runner()` with `ExecutionMode.PAPER`, repo raises | `driver._span_readiness is None`; `handler.margin_tracker` is `MarginTracker` |
| `test_equity_only_no_snapshot_no_effect` | Non-derivative symbol, repo raises | No exception; `span_readiness is None` |

### S2 Tests — new file `tests/risk/span/test_mm10_1_s2_protocol_v2.py`

| Test | Description | Pass criterion |
|------|-------------|----------------|
| `test_margin_tracker_satisfies_protocol_v2` | Structural protocol conformance | `hasattr(mt, 'get_incremental_margin')` is True |
| `test_span_calculator_satisfies_protocol_v2` | Structural protocol conformance | `hasattr(smc, 'get_incremental_margin')` is True |
| `test_margin_tracker_incremental_qty2_lot75_price100` | `margin_rate=0.2`, qty=2, lot=75, price=100 | `== 3000.0` |
| `test_margin_tracker_incremental_default_lot_size` | `margin_rate=0.2`, qty=1, price=200, no lot_size | `== 40.0` |
| `test_margin_tracker_incremental_matches_prior_else_branch` | Numeric equivalence with old formula | Equal to `qty * lot * price * rate` |
| `test_handler_uses_protocol_not_hasattr` | Handler with `MarginTracker` at utilisation limit; order is rejected | Gate fires; no `hasattr` in path |

### Regression

- Full 957-test suite green after each of S1 and S2 independently.
- No change to handler margin gate admit/reject outcomes.
- `tests/risk/span/test_span_composition.py` passes with updated assertion.

---

## 7. Files to Modify

### S1
| File | Change |
|------|--------|
| `scripts/fno_runner.py` | Replace `except Exception` block (lines 165-170) with LIVE/PAPER branch + always-BLOCK checker injection. Verify `SpanReadinessVerdict` is imported. |

### S2
| File | Change |
|------|--------|
| `core/risk/margin_calculator.py` | Add `get_incremental_margin` to `MarginCalculator` Protocol; update module docstring to v2 |
| `core/execution/margin_tracker.py` | Add `get_incremental_margin` method |
| `core/execution/handler.py` | Remove `hasattr` block at lines 1176-1185; replace with direct protocol call |
| `tests/risk/span/test_span_composition.py` | Update stale `not hasattr` assertion at line 55 |

---

## 8. Files That Must NOT Change

| File | Reason |
|------|--------|
| `core/risk/span/span_readiness.py` | Feature-frozen (MM9.5) |
| `core/risk/span/span_repository.py` | Feature-frozen (MM9.5) |
| `core/risk/span/span_snapshot.py` | Feature-frozen (MM9.5) |
| `core/risk/span/span_calculator.py` | Feature-frozen (MM9.5) |
| `core/risk/span/span_parser.py` | Feature-frozen (MM9.5) |
| `core/risk/span/parser_v400.py` | Feature-frozen (MM9.5) |
| `core/runtime/driver.py` | Startup gate architecture unchanged in MM10.1 |
| `core/execution/position_tracker.py` | Out of scope |
| `core/execution/portfolio_view.py` | Out of scope |

---

## 9. Risks

### R1 — Missing imports in `fno_runner.py` — LOW

Two imports may be absent: `SpanReadinessVerdict` (from `span_readiness`) and `pickle` (stdlib). Verify with grep before touching the file. `build_span_readiness` and `ReadinessState` are already present. **Resolution:** Add missing imports; at most two one-line additions.

---

### R2 — Stale test at `test_span_composition.py:55` — LOW

`assert not hasattr(mt, "get_incremental_margin")` will fail when `MarginTracker` gains the method. **Resolution:** Explicitly identified in §5 and §7; must be updated before S2 RED-to-GREEN.

---

### R3 — `_estimate_required_margin` becomes dead code — LOW / INTENTIONAL

After removing the `else` branch, `_estimate_required_margin` in `handler.py:1105-1108` has no callers. Do not delete it in MM10.1 — verify no other call sites exist first. Leave as dead code; cleanup is out of scope. **Resolution:** Grep for call sites; note finding in commit message.

---

### R4 — PAPER log message changes wording — LOW / ACCEPTABLE

The PAPER exception branch now includes "(PAPER/non-LIVE mode)" in the warning text. Log text is not a contract. No test assertions on log text expected. **Resolution:** Acceptable.

---

### R5 — `@runtime_checkable` on `MarginCalculator` — LOW

Python structural `Protocol` matching via `isinstance()` requires `@runtime_checkable`. If S2 tests use `isinstance(mt, MarginCalculator)`, the decorator must be present. If absent, add it to `margin_calculator.py` (zero behaviour change). If tests use `hasattr()` instead, the decorator is not needed. **Resolution:** Implementer chooses test form and adds decorator only if using `isinstance`.

---

## 10. Acceptance Criteria

### S1

1. LIVE F&O with no SPAN snapshot → `_check_span_readiness()` returns `False` → `abort_startup()` called → driver does not reach `RUNNING`.
2. The refusal logs at ERROR level (not WARNING).
3. PAPER F&O with no SPAN snapshot → WARNING logged → `span_readiness is None` → startup proceeds exactly as at mm9.5-complete.
4. `core/runtime/driver.py` and `core/risk/span/span_readiness.py` are not modified.

### S2

1. `MarginTracker` has `get_incremental_margin` — satisfies `MarginCalculator` v2 structurally.
2. `SpanMarginCalculator` has `get_incremental_margin` — satisfies `MarginCalculator` v2 structurally.
3. `MarginTracker.get_incremental_margin(sym, qty, price, lot_size)` returns `abs(qty) * lot_size * price * margin_rate`.
4. `handler.py` contains no `hasattr` reference to `get_incremental_margin`.
5. Handler margin gate behaviour (approve/reject verdicts) is numerically identical before and after the change for all existing tests.
6. `tests/risk/span/test_span_composition.py:55` is updated and passes.
7. `SpanMarginCalculator.get_incremental_margin` formula is unchanged.

---

## 11. Definition of Done

- All tests in `test_mm10_1_s1_span_hard_refusal.py` pass (RED → GREEN confirmed).
- All tests in `test_mm10_1_s2_protocol_v2.py` pass (RED → GREEN confirmed).
- `tests/risk/span/test_span_composition.py` passes with updated assertion.
- Full 957-test suite green with no regressions.
- `handler.py` contains no `hasattr(self.margin_tracker, 'get_incremental_margin')`.
- `fno_runner.py` LIVE exception branch logs ERROR and injects an always-BLOCK checker.
- `fno_runner.py` PAPER exception branch is behaviourally unchanged from mm9.5-complete.
- Commit tagged and `docs/reports/` updated per KB discipline.

---

## 12. Rollback Strategy

Both slices are independently deployable and independently rollbackable.

**S1 rollback:** Revert `scripts/fno_runner.py` to the pre-S1 state. The `except Exception` block returns to swallow-and-warn. No other files were changed. Driver, readiness module, and handler are unaffected.

**S2 rollback:** Revert `core/risk/margin_calculator.py`, `core/execution/margin_tracker.py`, and `core/execution/handler.py` to pre-S2 state. The `hasattr` detection path is restored. `SpanMarginCalculator` is unaffected — its `get_incremental_margin` always existed. The stale test at `test_span_composition.py:55` must be reverted simultaneously.

**Combined rollback:** `git revert` the MM10.1 commit(s). All changed files return to mm9.5 state. Zero impact on SPAN parser, snapshot, repository, or runtime infrastructure.

---

## Appendix A — Confirmed File Inventory

Verified by reading source at mm9.5-complete baseline:

| Symbol | Confirmed location |
|--------|--------------------|
| `MarginCalculator` protocol | `core/risk/margin_calculator.py` |
| `MarginTracker` | `core/execution/margin_tracker.py` |
| `SpanMarginCalculator` | `core/risk/span/span_calculator.py` |
| `SpanReadinessVerdict` | `core/risk/span/span_readiness.py` |
| `build_span_readiness` | `core/risk/span/span_readiness.py` |
| `ReadinessState` | `core/instruments/master_readiness.py` |
| `hasattr` detection | `core/execution/handler.py:1176` |
| `_estimate_required_margin` | `core/execution/handler.py:1105-1108` |
| `except (FileNotFoundError, ValueError, OSError, pickle.UnpicklingError)` block | `scripts/fno_runner.py:165-170` |
| `_make_span_block_checker(expected_date)` helper | new function in `scripts/fno_runner.py`, after `_make_live_broker_positions` |
| Stale test | `tests/risk/span/test_span_composition.py:55` |

---

## Appendix B — Dependency Confirmation

MM10.1 has no prerequisites. It is the entry point of the MM10 programme.

MM10.2 (per-expiry and per-strike RA) depends on MM10.1-S2 having locked the v2 protocol, so that all subsequent `MarginCalculator` implementations build against the stable interface.

No changes to SPAN data, parser, snapshot, or repository are required or permitted in MM10.1.
