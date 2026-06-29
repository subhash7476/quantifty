# MM9.5-S4 — Integration Certification

**Status**: APPROVED WITH MAJOR SCOPE REDUCTION — revised after ChatGPT Lead review
**Target**: DeepSeek V4 / GLM implementation
**Milestone**: MM9.5 closing — scan-risk subsystem integration certification

---

## 1. Objective

Certify the finished `SpanMarginCalculator` and `ParserV400` as production-ready by fixing one genuine runtime robustness defect and proving end-to-end system behaviour through tests alone.

**This milestone adds tests. It fixes one bug. It adds no new capability.**

---

## 2. Philosophy

S4 is **Integration Certification**, not Integration Development.

The parser and calculator are already correct and well-tested at the unit level (S1–S3). S4 proves that the **system** — composition root, runtime gate, startup sequence, fallback paths — behaves correctly when those components are wired together.

The highest value at this stage comes from **proving** the subsystem rather than **extending** it.

---

## 3. Current Architecture (Unchanged)

```
┌──── OFFLINE ──────────────────────────────────────────────────────────────────┐
│ scripts/fetch_span_params.py                                                  │
│   → download_span_data()  (NSE URL)                                           │
│   → parse_span_xml()      (ParserRegistry → ParserV400)                       │
│   → promote_snapshot()    (→ data/span/*.parquet + .zip)                      │
└────────────────────────────────────────────────────────────────────────────────┘

┌──── RUNTIME COMPOSITION (scripts/fno_runner.py) ──────────────────────────────┐
│                                                                               │
│  SpanRepository.load(expected) ─► SpanSnapshot (immutable)                    │
│     ├──► SpanMarginCalculator(pt, snapshot) ──► ExecutionHandler (injected)   │
│     └──► build_span_readiness(repo) ──────────► LoopDriver (startup gate)     │
│                                                                               │
│  On failure → span_snapshot=None, span_readiness=None                         │
│             → MarginTracker (flat 20% fallback)                               │
└────────────────────────────────────────────────────────────────────────────────┘

┌──── RUNTIME EXECUTION (core/runtime/driver.py + core/execution/handler.py) ───┐
│                                                                               │
│  Startup gate: _check_master_readiness() → _check_span_readiness()            │
│                          (BLOCK = refuse to start)                            │
│                                                                               │
│  Per-signal gate chain (handler.py):                                          │
│    ...                                                                        │
│   10. *** MARGIN BUDGET GATE ***  ← SpanMarginCalculator integration point    │
│         └─ get_used_margin(prices) + get_incremental_margin(sym, qty, px, ls) │
│    ...                                                                        │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Integration Points (All Already Implemented)

| # | Integration Point | File | Status |
|---|---|---|---|
| IP-1 | Snapshot load + readiness build | `scripts/fno_runner.py:150–170` | Implemented |
| IP-2 | Conditional calculator injection | `core/execution/handler.py:199–207` | Implemented |
| IP-3 | Startup SPAN readiness gate | `core/runtime/driver.py:444–483` | Implemented |
| IP-4 | Margin budget gate — SPAN path | `core/execution/handler.py:1175–1179` | Implemented |
| IP-5 | Margin budget gate — fallback path | `core/execution/handler.py:1180–1184` | Implemented |
| IP-6 | PortfolioView telemetry | `core/execution/handler.py:216–220` | Implemented |

---

## 4. Gap Analysis

### GAP-1: Unhandled `SpanMarginError` in Margin Gate (HIGH — only production fix)

**File**: `core/execution/handler.py:1147–1186`

`_check_margin_budget()` calls `get_used_margin()` and `get_incremental_margin()` without try/except. If either raises `MissingRiskArray` or `MissingRiskMetric`, the exception propagates to `process_signal()` and crashes the tick loop.

```text
SpanMarginCalculator
  → get_used_margin() / get_incremental_margin()
    → MissingRiskArray / MissingRiskMetric
      → UNHANDLED → tick loop crash
```

**Impact**: A signal for a symbol whose risk array is absent from the SPAN snapshot bypasses the entire gate chain and terminates the runtime.

**Fix**: `_check_margin_budget` catches `SpanMarginError`, logs a warning, and returns `(False, 1.0)` — a safe refusal that keeps the tick loop running.

---

### GAP-3: Silent Partial Margin from `get_used_margin` (DOCUMENT ONLY)

`SpanMarginCalculator.get_used_margin()` at line 110–113 silently skips symbols absent from `current_prices`. This is the intentional cold-start gap from MM9.2-S1.

**No code change.** The behaviour is correct. A position that has a price cache entry but no risk array will crash (fail-fast), which is correct after GAP-1 is fixed — the exception is caught by the gate. A position without a price cache entry is cold-start and is excluded from margin until its first tick.

---

### GAP-4: No End-to-End Integration Tests (TEST GAP)

No existing test exercises the full pipeline: snapshot → calculator → position entry → margin gate → SPAN margin response.

---

### GAP-5: No Negative-Path Integration Tests (TEST GAP)

No tests for `MissingRiskArray`/`MissingRiskMetric` in the margin gate context, or for edge cases like empty risk arrays and zero cash balance with SPAN.

---

### GAP-6: No Determinism Test for Full Integration (TEST GAP)

Individual components are tested for determinism, but the full `_check_margin_budget` with SPAN calculator has no repeated-execution test.

---

### GAP-7: Margin Gate Tests Only Cover Flat-Rate Path (TEST GAP)

All tests in `test_mm9_1_margin_gate.py` use `MarginTracker`. None test the SPAN path.

---

### GAP-2 and GAP-8 — NOT IN SCOPE

| Gap | What | Why removed |
|---|---|---|
| GAP-2 | Startup symbol validation | Duplicates GAP-1 protection. The handler already rejects at runtime. Adding a second validator adds code without adding safety. |
| GAP-8 | Drawdown integration test | Drawdown isn't changing. Margin calculation is. Not needed for certification. |

---

## 5. Exact Production Change

### ONLY Change: Exception Handling in `_check_margin_budget`

**File**: `core/execution/handler.py`
**Rationale**: GAP-1 — the single genuine robustness defect

```python
# BEFORE (line 1170–1186):
prices = {sym: snap.price for sym, snap in self._price_cache.items()}
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
utilisation = (used_current + incremental_est) / self.metrics.cash_balance
return utilisation <= self.config.max_capital_utilisation, utilisation

# AFTER:
prices = {sym: snap.price for sym, snap in self._price_cache.items()}
try:
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
except SpanMarginError as e:
    self.logger.warning("MARGIN_BUDGET_REJECTED span_margin_error=%s", e)
    return False, 1.0
utilisation = (used_current + incremental_est) / self.metrics.cash_balance
return utilisation <= self.config.max_capital_utilisation, utilisation
```

**Import required**: `from core.risk.span.span_calculator import SpanMarginError` added to handler.py imports.

**That is the only production code change in S4.**

---

### No Changes To

| Component | Reason |
|---|---|
| `SpanMarginCalculator` | Feature complete (S3). No margin math changes. |
| `SpanSnapshot` / DTOs | Immutable — complete. |
| `ParserV400` / `ParserRegistry` | Complete (S1–S2). |
| `SpanRepository` / `SpanReadiness` / `SpanFreshness` / `SpanPipeline` | Complete (S0–S4 earlier). |
| `MarginCalculator` Protocol | Complete (MM9.4). |
| `MarginTracker` | Stable fallback — must remain. |
| `PositionTracker` / `PortfolioView` | No SPAN changes. |
| `LoopDriver` / `_check_span_readiness` | Gate logic correct. |
| `scripts/fno_runner.py` | Composition root — stable. Do not touch. |
| `scripts/fetch_span_params.py` | Offline — complete. |
| All broker, instrument, Flask, FTMO code | Not involved. |

---

## 6. RED → GREEN Test Plan

All tests follow TDD: write test (RED), implement GAP-1 fix (GREEN for Phase 2), verify all other phases pass (should be GREEN immediately — they test existing behaviour).

### Phase 1: SPAN Margin Gate End-to-End (GAP-7, GAP-4)

**New file**: `tests/execution/test_mm9_5_s4_span_margin_integration.py`

| ID | Test | Verifies |
|---|---|---|
| I1 | `test_span_gate_approves_under_limit` | Full gate with SPAN calculator, utilisation < 0.80 → `(True, u)` |
| I2 | `test_span_gate_rejects_over_limit` | Utilisation > 0.80 → `(False, u)` |
| I3 | `test_span_gate_boundary_equal` | Utilisation exactly 0.80 → `(True, 0.80)` |
| I4 | `test_span_gate_includes_used_current` | Existing position margin contributes to used_current |
| I5 | `test_span_gate_futures_multiplier` | F&O order uses lot_size as multiplier → `qty × ls × scan_risk` |
| I6 | `test_span_gate_margin_rate_haircut` | `margin_rate=1.5` increases margin proportionally |
| I7 | `test_span_gate_price_independence` | Same position, different price → same scan margin |
| I8 | `test_span_gate_single_execution_deterministic` | Same inputs twice → identical (approved, utilisation) |

### Phase 2: Negative-Path Integration (GAP-1, GAP-5)

**New file**: `tests/execution/test_mm9_5_s4_span_negative.py`

| ID | Test | Verifies |
|---|---|---|
| N1 | `test_missing_risk_array_rejected_not_crashed` | `_check_margin_budget` with symbol not in snapshot → `(False, 1.0)`, no exception |
| N2 | `test_missing_scan_risk_rejected_not_crashed` | scan_risk absent from risk array → `(False, 1.0)`, no exception |
| N3 | `test_missing_risk_array_warning_logged` | Warning log emitted containing "span_margin_error" |
| N4 | `test_zero_cash_balance_bypasses_gate` | `cash_balance ≤ 0` with SPAN → `(True, 0.0)` |
| N5 | `test_empty_risk_arrays_position_held` | Snapshot with no risk arrays, book has position → `(False, 1.0)` |
| N6 | `test_held_position_not_in_snapshot` | Held position's symbol not in risk_arrays → `(False, 1.0)` |

### Phase 3: Determinism (GAP-6)

**New file**: `tests/execution/test_mm9_5_s4_span_determinism.py`

| ID | Test | Verifies |
|---|---|---|
| D1 | `test_span_gate_repeated_identical` | Same handler, position, order, price → same output 3 times |
| D2 | `test_two_calculators_same_snapshot` | Two calculators from same snapshot → identical margin |
| D3 | `test_used_margin_deterministic` | `get_used_margin` same inputs → exact match |

### Phase 4: Composition + Startup Gate

**New file**: `tests/scripts/test_mm9_5_s4_fno_runner_span_wiring.py`

| ID | Test | Verifies |
|---|---|---|
| S1 | `test_snapshot_loaded_injects_span_calculator` | Valid snapshot → `SpanMarginCalculator` in handler |
| S2 | `test_no_snapshot_falls_back_to_margin_tracker` | No snapshot → `MarginTracker` in handler |
| S3 | `test_span_readiness_injected_for_derivatives` | Derivative universe → `driver._span_readiness is not None` |
| S4 | `test_span_readiness_none_for_equity` | Equity universe → `driver._span_readiness is None` |

**New file**: `tests/runtime/test_mm9_5_s4_driver_span_gate.py`

| ID | Test | Verifies |
|---|---|---|
| G1 | `test_span_readiness_fresh_proceeds` | Verdict FRESH → `_check_span_readiness` returns True |
| G2 | `test_span_readiness_block_aborts` | Verdict BLOCK → returns False, calls `abort_startup` |
| G3 | `test_absent_snapshot_blocks` | Snapshot missing → BLOCK, reason contains "absent" |
| G4 | `test_stale_snapshot_blocks` | Yesterday's snapshot → BLOCK, reason contains "stale" |
| G5 | `test_future_snapshot_blocks` | Tomorrow's snapshot → BLOCK, reason contains "future" |
| G6 | `test_equity_universe_skips_gate` | Equity → returns True without calling checker |
| G7 | `test_paper_mode_skips_gate` | Paper mode → returns True |

### Phase 5: Regression Compatibility

**New file**: `tests/execution/test_mm9_5_s4_span_regression.py`

| ID | Test | Verifies |
|---|---|---|
| R1 | `test_existing_margin_gate_tests_pass` | All `test_mm9_1_margin_gate.py` tests pass unchanged |
| R2 | `test_portfolio_view_works_with_span` | `PortfolioView.snapshot()` with SPAN → exposure/used_margin correct |
| R3 | `test_existing_span_calculator_tests_pass` | All `test_span_calculator.py` tests pass |
| R4 | `test_existing_span_parser_tests_pass` | All `test_parser_v400*.py` tests pass |
| R5 | `test_existing_span_composition_tests_pass` | All `test_span_composition.py` tests pass |

---

## 7. Definition of Done

1. **GAP-1 closed**: `_check_margin_budget` catches `SpanMarginError`, returns `(False, 1.0)`, logs warning.
2. **Phase 1** (I1–I8): SPAN margin gate end-to-end — all pass.
3. **Phase 2** (N1–N6): negative-path integration — all pass.
4. **Phase 3** (D1–D3): determinism — all pass.
5. **Phase 4** (S1–S4, G1–G7): composition wiring + startup gate — all pass.
6. **Phase 5** (R1–R5): regression compatibility — all pass.
7. **Existing test suites pass unchanged** (all 18 files from §9 "Files That Must NOT Change").
8. **No architectural drift**: parser read-only, calculator snapshot-only, runtime has no XML awareness, no circular dependencies.
9. **MM9.5 closed**: scan-risk subsystem certified production-ready. Platform ready for MM10.

---

## 8. Files to Modify

| File | Change | Lines |
|---|---|---|
| `core/execution/handler.py` | Add `try/except SpanMarginError` in `_check_margin_budget()` | ~8 |
| `core/execution/handler.py` | Add `from core.risk.span.span_calculator import SpanMarginError` to imports | 1 |

**New test files** (6 files, ~40 tests):

| File | Phase | Tests |
|---|---|---|
| `tests/execution/test_mm9_5_s4_span_margin_integration.py` | Phase 1 | I1–I8 |
| `tests/execution/test_mm9_5_s4_span_negative.py` | Phase 2 | N1–N6 |
| `tests/execution/test_mm9_5_s4_span_determinism.py` | Phase 3 | D1–D3 |
| `tests/scripts/test_mm9_5_s4_fno_runner_span_wiring.py` | Phase 4 | S1–S4 |
| `tests/runtime/test_mm9_5_s4_driver_span_gate.py` | Phase 4 | G1–G7 |
| `tests/execution/test_mm9_5_s4_span_regression.py` | Phase 5 | R1–R5 |

**Total production code changed**: ~9 lines in 1 file.
**Total new test code**: ~500 lines across 6 files (~33 tests).

---

## 9. Files That MUST NOT Change

| File | Reason |
|---|---|
| `core/risk/span/span_calculator.py` | Feature complete (S3) |
| `core/risk/span/span_snapshot.py` | Immutable DTO — complete |
| `core/risk/span/span_parser.py` | ParserRegistry — complete |
| `core/risk/span/parser_v400.py` | V4.00 parser — complete |
| `core/risk/span/span_repository.py` | Complete |
| `core/risk/span/span_readiness.py` | Complete |
| `core/risk/span/span_freshness.py` | Complete |
| `core/risk/span/span_pipeline.py` | Complete |
| `core/risk/margin_calculator.py` | Protocol — complete |
| `core/execution/margin_tracker.py` | Stable fallback — must remain |
| `core/execution/position_tracker.py` | No SPAN changes needed |
| `core/execution/portfolio_view.py` | No SPAN changes needed |
| `core/runtime/driver.py` | Gate logic unchanged |
| `scripts/fno_runner.py` | **Composition root — stable. Do not touch.** |
| `scripts/fetch_span_params.py` | Offline — complete |
| `core/brokers/` | No SPAN changes |
| `core/instruments/` | No SPAN changes |
| `flask_app/` | No UI changes |
| `ftmo/` | No FTMO changes |
| All files under `tests/risk/span/` | Existing regression suites — unchanged |

---

## 10. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `SpanMarginError` import in handler creates new dependency edge | LOW | Handler already imports `SpanMarginCalculator` from the same module. No circular dependency possible (calculator → position_tracker only; handler → calculator → snapshot; no reverse edges). |
| `(False, 1.0)` return on SPAN error masks misconfiguration | MEDIUM | Warning log captures the exception message verbatim. `1.0` utilisation unambiguously exceeds `0.80`. Operator must monitor logs for "span_margin_error" warnings. |
| New tests fail on CI due to missing `reference/span/` | NONE | All new tests use synthetic data. No dependency on the real NSE SPAN file. |

---

## 11. Acceptance Criteria

1. `_check_margin_budget` returns `(False, 1.0)` when `SpanMarginError` is raised — no crash.
2. All 33 new tests pass.
3. All 18 existing test files from the locked list pass unchanged.
4. No files from the locked list are modified.
5. No new abstractions, interfaces, DTOs, or runtime logic beyond the single `try/except`.
6. `pytest tests/risk/span/ -v` — all pass.
7. `pytest tests/execution/test_mm9_1_margin_gate.py -v` — all pass (regression).
8. MM9.5 can be declared closed.

---

## 12. Out of Scope

- Inter-month spread credits
- Calendar spread margin
- Delivery margin
- Exposure margin addition
- Option delta ladder calculations
- Portfolio offset algorithms
- Any new parser features
- Any new XML parsing
- Any new DTOs or schema changes
- Broker API integration for margin queries
- UI changes
- Strategy development
- Performance optimisation
- Intraday SPAN snapshot refresh
- Removing or refactoring `MarginTracker`
- Removing or refactoring `_estimate_required_margin`
- Startup symbol validation (GAP-2 — removed per review)
- Drawdown gate SPAN integration (GAP-8 — removed per review)
- `scripts/fno_runner.py` changes of any kind
- Complete SPAN portfolio margin (MM10 scope)

---

## 13. Rollback Strategy

The single production change is self-contained:

- **Remove the try/except block** — restore the original three lines (used_current, incremental_est, utilisation calculation). MarginTracker fallback is unaffected. SPAN snapshot removal from `data/span/` immediately and safely reverts to flat-rate margin behaviour.

---

## 14. Implementation Sequence

1. Write GAP-1 fix (the `try/except SpanMarginError`) in `handler.py`
2. Write Phase 2 tests (N1–N6) — verify the fix works (GREEN)
3. Write Phase 1 tests (I1–I8) — verify SPAN gate end-to-end (GREEN)
4. Write Phase 3 tests (D1–D3) — verify determinism (GREEN)
5. Write Phase 4 tests (S1–S4, G1–G7) — verify composition + startup (GREEN)
6. Write Phase 5 tests (R1–R5) — verify no regressions (GREEN)
7. Run full test suite: `pytest tests/ -x --tb=short`
8. Run SPAN suite specifically: `pytest tests/risk/span/ -v`

---

## 15. Documentation Updates Required (After Implementation)

Identify only — do NOT update during S4:

| Document | Update |
|---|---|
| `docs/CHANGELOG_PLATFORM.md` | Add MM9.5-S4 entry |
| `docs/PROJECT_STATE.md` | Mark MM9.5 complete |
| `docs/PLATFORM_INVENTORY.md` | Add 6 new test files |

---

*End of MM9.5-S4 Implementation Specification (Revised)*
