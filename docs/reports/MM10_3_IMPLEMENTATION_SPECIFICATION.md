# MM10.3 — NseMarginEngine (Phase 1): Calendar Spread Credits
## Implementation Specification

**Date:** 2026-06-30  
**Author role:** System Architect  
**Status:** For ChatGPT Technical Lead review  
**Milestone tag:** `mm10.3-complete` (target)  
**Predecessor:** `mm10.2-complete`
**2026-07-01 update:** this doc's references to a future "Exposure Margin (MM10.5)" component are
now stale — MM10.5 was **retired, not implemented**; "Exposure Margin" was resolved to be the
same regulatory charge as ELM under legacy naming, not a separate additive term
(`docs/architecture_decisions.md` ADR-012).

---

## 0. Reference Data (Verified)

Before any specification, the relevant `dSpread` data was extracted from the reference SPAN file
(`nsccl.20260625.i1/nsccl.20260625.i01.spn`) to resolve all unit questions.

| Symbol    | dSpread count | All rate/val | `intra_spread_charge_rs` (parser min) |
|-----------|---------------|--------------|----------------------------------------|
| NIFTY     | 153           | 425.0        | 425.0                                  |
| BANKNIFTY | 15            | 1029.0       | 1029.0                                 |

**dSpread element structure (from real file):**
```xml
<dSpread>
  <spread>1</spread>
  <chargeMeth>F</chargeMeth>          <!-- F = Flat rate -->
  <rate>
    <r>1</r>
    <val>425.000000</val>
  </rate>
  <pLeg><cc>NIFTY</cc><pe>20260630</pe><rs>A</rs><i>1.000000</i></pLeg>
  <pLeg><cc>NIFTY</cc><pe>20260707</pe><rs>B</rs><i>1.000000</i></pLeg>
</dSpread>
```

**Unit determination:** Each dSpread defines a specific expiry-pair. The `val=425.0` is in the same
unit as `scan_risk`: **Rs per underlying unit** (not per lot). Confirmation:
- NIFTY scan_risk = 2244.36 Rs/unit → per-lot = 2244.36 × 65 = 145,883 Rs
- NIFTY spread charge per lot = 425.0 × 65 = 27,625 Rs
- Net matched-pair margin = 27,625 Rs (vs 291,766 Rs without credit)
- This matches known NSE calendar spread margins of Rs 25,000–30,000 per NIFTY pair ✓

**Parser limitation (frozen):** The parser currently extracts `min(rate/val)` across all dSpreads,
discarding the per-pair expiry information (`pLeg/pe`). For the reference file, all rates are
identical so no information is lost. Phase 1 uses this flat rate. Full tier fidelity (different
rates by month-gap) is a future parser extension. The parser is not touched in MM10.3.

---

## 1. Current Architecture

```
CLI / fno_runner.py
        │
        │  span_snapshot: SpanSnapshot
        ▼
ExecutionHandler.__init__
        │
        │  if span_snapshot is not None:
        ▼
SpanMarginCalculator(position_tracker, span_snapshot)
        │
        │  implements MarginCalculator Protocol v2
        ▼
   margin_tracker
        │
        ├── get_exposure(prices, symbol?)  → notional
        ├── get_used_margin(prices)        → scan only (no credits)
        └── get_incremental_margin(...)    → per-symbol scan
```

**Single production instantiation site:** `core/execution/handler.py:204`

**Current margin formula (`get_used_margin`):**
```
for each position:
    margin += abs(qty) × lot_size × max(scan_risk_per_contract, SOM) × margin_rate
```
Calendar spread credits are not applied. Both legs of a matched spread pair pay full standalone
scan risk. This is conservative (overestimates required margin) but never unsafe.

---

## 2. Proposed Architecture

```
CLI / fno_runner.py
        │
        │  span_snapshot: SpanSnapshot
        ▼
ExecutionHandler.__init__
        │
        │  if span_snapshot is not None:
        ▼
NseMarginEngine                              ← NEW in MM10.3
  │   implements MarginCalculator Protocol v2
  │   data sources: SpanMarginCalculator + PositionTracker
  │
  ├── _span_calc: SpanMarginCalculator       ← existing, UNCHANGED
  │     └── SpanSnapshot (read-only)
  │
  ├── _spread_credit(prices) → float         ← NEW: CalendarSpreadCredit logic
  │     └── reads self._snapshot (injected explicitly — see §10)
  │
  └── get_used_margin(prices)
        = span_calc.get_used_margin(prices)
          - _spread_credit(prices)
          (clamped to ≥ 0)
```

**Rollback path (unchanged from MM10 Architecture Revision §3):**
```python
# Conservative: scan-only, no credits
margin_tracker = SpanMarginCalculator(position_tracker, span_snapshot)

# Full MM10.3+:
span_calc = SpanMarginCalculator(position_tracker, span_snapshot)
margin_tracker = NseMarginEngine(span_calc)
```

---

## 3. Responsibility Boundaries

### SpanMarginCalculator (feature-frozen after MM10.2)

**Owns exclusively:**
- Per-position SPAN scan risk: `abs(qty) × lot_size × max(scan_risk_per_contract, SOM)`
- Short Option Minimum (SOM) floor application
- Contract-level RA routing for futures (per-expiry) and options (per-strike)
- Fallback to symbol-level scan risk on miss
- `get_exposure` (notional only)
- `get_incremental_margin` (symbol-level scan, pre-trade)

**Does NOT own:**
- Calendar spread credits (cross-position reduction)
- ELM (deferred to MM10.4)
- Exposure margin (deferred to MM10.5)
- Broker haircuts (out of scope)
- Any portfolio-level netting

**Invariant for MM10.3:** `span_calculator.py` must remain unchanged. A guard test verifies
that `span_calculator.py` contains no references to `elm`, `exposure_margin`, `broker`,
`spread_credit`, or `NseMarginEngine`.

### NseMarginEngine (new in MM10.3)

**Owns:**
- Protocol v2 surface for production F&O margin
- Calendar spread credit computation (Phase 1)
- Composition of `SpanMarginCalculator` output with spread credits
- Future composition of ELM (MM10.4) and Exposure Margin (MM10.5)

**Does NOT own:**
- SPAN scan risk calculation (delegated to SpanMarginCalculator)
- PositionTracker (shared reference via calculator, read-only)
- SpanSnapshot directly (accessed via `_span_calc._snapshot` — only for spread matching)

**Protocol delegation:**
```
get_exposure(prices, symbol?)  → delegate to _span_calc (no credit adjustment to notional)
get_incremental_margin(...)    → delegate to _span_calc (cannot see offsetting leg pre-trade)
get_used_margin(prices)        → apply spread credit reduction
margin_rate                    → proxy from _span_calc.margin_rate
```

`get_exposure` and `get_incremental_margin` are explicitly **not** credit-aware in Phase 1.
The reason for `get_incremental_margin`: a pre-trade call cannot know whether the proposed
order will form a spread with an existing position until after the fill. Delegating to the
scan-only path is the conservative pre-trade policy.

---

## 4. Calendar Spread Credit Algorithm

### 4.1 Inputs

```python
position_tracker: PositionTracker    # via _span_calc.position_tracker (public attribute)
span_snapshot: SpanSnapshot          # self._snapshot — injected at construction (see §10)
current_prices: Dict[str, float]     # available for future use; not needed for scan credit
```

### 4.2 Outputs

```python
total_spread_credit: float   # Rs reduction to apply to get_used_margin; always ≥ 0
```

### 4.3 Eligibility

Only **Future** instruments are eligible for Phase 1 spread credit.

- `InstrumentType.FUTURE` only
- Options and equity positions are ignored in the spread-matching pass
- Rationale: NSE delta-based spreads in the reference file pair futures expiries; option
  spread credit (volatility spreads) is a separate mechanism deferred to a future milestone

### 4.4 Matching Algorithm

```
Step 1 — Build futures_by_underlying: Dict[str, Dict[date, float]]
  For each position in PositionTracker._positions.values():
    - Skip if position.instrument.type != InstrumentType.FUTURE
    - underlying = position.instrument.underlying
    - expiry     = position.instrument.expiry
    - signed_qty = +position.quantity if LONG else -position.quantity
    - futures_by_underlying[underlying][expiry] += signed_qty

Step 2 — For each underlying U with at least 2 distinct expiry entries:
  a. Look up intra_spread_charge_rs for U:
       charge_per_unit = snapshot.risk_arrays[U].risk_metrics.get(
           "intra_spread_charge_rs", 0.0)
       If charge_per_unit == 0.0: skip U (conservative — no credit data)
       If U not in snapshot.risk_arrays: skip U

  b. Sort expiries ascending: sorted_expiries = sorted(futures_by_underlying[U].keys())
     Build: signed_qty_by_expiry = {e: futures_by_underlying[U][e] for e in sorted_expiries}

  c. Resolve lot_size for U:
       Take lot_size from the first FUTURE position for this underlying.
       lot_size = instrument.lot_size if hasattr(instrument, 'lot_size')
                  else instrument.multiplier

  d. Greedy matching (ascending expiry order):
       For each i, j in combinations of sorted_expiries where i < j (ascending):
         q_i = remaining[e_i]   # signed
         q_j = remaining[e_j]   # signed
         If sign(q_i) == sign(q_j): continue  # same direction, no spread
         n_matched = min(|q_i|, |q_j|)        # lots to match

         scan_near = _get_scan_risk(U, min(e_i, e_j), snapshot)
         scan_far  = _get_scan_risk(U, max(e_i, e_j), snapshot)
         credit    = max(0.0, (scan_near + scan_far - charge_per_unit) * lot_size * n_matched)
         total_spread_credit += credit

         remaining[e_i] -= n_matched * sign(q_i)
         remaining[e_j] -= n_matched * sign(q_j)
         # Continue to next pair with updated remaining quantities

Step 3 — Return total_spread_credit
```

### 4.5 Scan Risk Lookup (`_get_scan_risk`)

```
def _get_scan_risk(underlying: str, expiry: date, snapshot: SpanSnapshot) -> float:
    1. Try contract-level RA lookup:
         contracts = snapshot.futures.get(underlying, ())
         for c in contracts:
           if c.expiry == expiry:
             return _derive_contract_scan_risk(c.ra)

    2. Fallback: symbol-level scan risk:
         ra = snapshot.risk_arrays.get(underlying)
         if ra is not None:
           return ra.risk_metrics.get("scan_risk", 0.0)

    3. Not found: return 0.0 (no credit possible for this leg)
```

`_derive_contract_scan_risk` uses the same 16-scenario-weight formula as `SpanMarginCalculator`.
The formula is **duplicated** (not imported from the frozen calculator) for the same reason as
in `span_calculator.py` itself: the parser is frozen and the guard test enforces mathematical
equivalence independently.

### 4.6 Lot Size Resolution

Lot size for a matched pair is taken from the first resolved FUTURE position for that
underlying. Since NSE lot sizes are standardised per underlying and NSE revisions apply to
all expiries simultaneously, any position in the matched group carries the correct lot size.

Resolution order (mirrors `SpanMarginCalculator._single_exposure`):
```python
lot_size = getattr(instrument, "lot_size", None) or instrument.multiplier
```

### 4.7 Invariants

1. **Credit is non-negative per pair:** `max(0.0, ...)` applied to each matched pair.
2. **Total margin is non-negative:** `max(0.0, span_margin - credit)` in `get_used_margin`.
3. **Deterministic:** Positions sorted by expiry (ascending) before matching. Result is
   invariant to `dict` insertion order in `PositionTracker._positions`.
4. **Conservative on missing data:** Missing risk array, missing `intra_spread_charge_rs`,
   or zero charge → credit = 0 for that underlying.
5. **Calculator unchanged:** `NseMarginEngine.get_used_margin` calls
   `_span_calc.get_used_margin(prices)` as a black box; no calculator private methods called.
6. **No I/O:** `_spread_credit` performs zero filesystem, network, or broker calls.

### 4.8 Failure Behaviour

| Condition | Behaviour |
|-----------|-----------|
| Underlying not in `risk_arrays` | Skip underlying; credit = 0 |
| `intra_spread_charge_rs` = 0 for underlying | Skip underlying; credit = 0 |
| `intra_spread_charge_rs` absent from risk_metrics | Skip underlying; credit = 0 |
| Future expiry not in `snapshot.futures` | Fall back to symbol-level scan risk |
| Symbol not in `snapshot.futures` at all | Fall back to symbol-level scan risk |
| Only one expiry present for underlying | No spread possible; credit = 0 |
| All positions same direction for underlying | No matching; credit = 0 |
| Spread charge > combined scan risk | Credit clamped to 0 (invariant 1) |
| Total credit > total scan margin | Result clamped to 0 (invariant 2) |

No exceptions are raised by the spread credit computation. It degrades silently to zero
credit in all missing-data cases. `SpanMarginCalculator` exceptions (`MissingRiskArray`,
`MissingRiskMetric`) propagate unchanged from the delegated `get_used_margin` call.

---

## 5. Production Changes

### 5.1 New Files

| File | Purpose |
|------|---------|
| `core/risk/nse_margin_engine.py` | `NseMarginEngine` class |
| `tests/risk/test_nse_margin_engine.py` | Full test suite (Groups A–N, R) |

### 5.2 Modified Files

| File | Change | Site |
|------|--------|------|
| `core/execution/handler.py` | Swap injection: `NseMarginEngine(SpanMarginCalculator(...))` | Line ~204 |

The change at `handler.py:204` replaces:
```python
self.margin_tracker: MarginCalculator = SpanMarginCalculator(
    self.position_tracker, span_snapshot)
```
with:
```python
_span_calc = SpanMarginCalculator(self.position_tracker, span_snapshot)
self.margin_tracker: MarginCalculator = NseMarginEngine(_span_calc, span_snapshot)
```

### 5.3 Unchanged Files (Explicit)

All MM9.5 / MM10.1 / MM10.2 certified components are not touched:

| File | Status |
|------|--------|
| `core/risk/span/span_calculator.py` | Feature-frozen — zero changes |
| `core/risk/span/span_snapshot.py` | Feature-frozen — zero changes |
| `core/risk/span/span_parser.py` | Feature-frozen — zero changes |
| `core/risk/span/parser_v400.py` | Feature-frozen — zero changes |
| `core/risk/span/span_repository.py` | Feature-frozen — zero changes |
| `core/risk/span/span_readiness.py` | Feature-frozen — zero changes |
| `core/risk/margin_calculator.py` | Protocol v2 — zero changes |
| `tests/risk/span/test_span_calculator.py` | Regression — zero changes |
| `tests/risk/span/test_span_calculator_regression.py` | Regression — zero changes |

---

## 6. RED → GREEN Plan (TDD Phases)

All test groups are written **before** any implementation code. Each phase must reach GREEN
before the next phase begins. DeepSeek V4 writes only enough implementation to pass each phase.

### Phase 1 — Protocol Conformance (Group A)

Tests verify:
- `NseMarginEngine` has `margin_rate: float`
- Callable for `get_exposure`, `get_used_margin`, `get_incremental_margin`
- Does not inherit from `MarginCalculator` (structural protocol, not nominal)
- Does not inherit from `SpanMarginCalculator`
- `margin_rate` proxies to `_span_calc.margin_rate`

Expected: All RED (class does not exist).

### Phase 2 — Delegation (Group B)

Tests verify:
- `get_exposure` returns identical value to `_span_calc.get_exposure`
- `get_incremental_margin` returns identical value to `_span_calc.get_incremental_margin`
- `get_used_margin` with equity-only portfolio returns identical value to `_span_calc` (no spread)
- `get_used_margin` with futures all same expiry returns identical value (no matching)
- `get_used_margin` with futures all same direction returns identical value (no matching)

Expected: GREEN after implementing class scaffold + pure delegation in all three methods.
The `_spread_credit` stub returning 0.0 passes all Phase 2 tests.

### Phase 3 — Spread Credit Basics (Group C)

Tests verify:
- Two futures, different expiries, opposite directions, same underlying → credit > 0
- Credit = `(scan_near + scan_far − spread_charge) × lot_size × n_matched`
- `get_used_margin` returns `span_margin − credit`
- Credit cannot make margin negative
- Credit cannot be negative itself (when spread_charge > combined scan risk)

Expected: RED (no `_spread_credit` logic yet). GREEN after `_spread_credit` implemented.

### Phase 4 — Matching Rules (Group D)

Tests verify:
- Partial match: 3 long lots + 2 short lots → credit on 2 pairs; 1 outright unaffected
- Three expiries: long-near + long-mid + short-far → greedy match resolves correctly
- Same-direction spread (long + long) → no credit
- Mixed underlying: NIFTY spread credit isolated from BANKNIFTY outright (no cross-underlying credit)
- Option instruments in same portfolio are NOT matched
- Equity instruments are NOT matched

Expected: RED if matching is incomplete. GREEN after full matching pass.

### Phase 5 — Scan Risk Lookup (Group E)

Tests verify:
- Contract-level RA used when futures expiry found in snapshot
- Symbol-level fallback used when expiry not found
- Credit with symbol-level fallback is correct
- Missing underlying in risk_arrays → credit = 0 (no exception)

Expected: Mostly GREEN from Phase 3/4. Add explicit tests to pin lookup paths.

### Phase 6 — Zero Spread Charge (Group F)

Tests verify:
- `intra_spread_charge_rs = 0.0` → credit = 0 regardless of matched lots
- `intra_spread_charge_rs` absent from risk_metrics → credit = 0
- No exception raised in either case

Expected: RED if zero-charge guard not implemented. GREEN after guard.

### Phase 7 — Determinism (Group G)

Tests verify:
- Same inputs produce same output on repeated calls
- Credit result is independent of position insertion order in PositionTracker
  (test by inserting same positions in permuted order)
- `nse_margin_engine.py` does not import `span_parser`, `span_repository`,
  `span_readiness`, or any SPAN private helpers (static import check)

### Phase 8 — Guard Tests (Group H)

Static analysis via file content inspection. Tests verify:
- `span_calculator.py` contains no references to:
  `elm`, `exposure_margin`, `broker`, `spread_credit`, `NseMarginEngine`
- `nse_margin_engine.py` contains no references to private calculator methods:
  `_scan_margin_per_unit`, `_single_span_margin`, `_resolve_scan_risk`
- `nse_margin_engine.py` contains no I/O: `open(`, `Path(`, `.read`, `.write`

### Phase 9 — Real-File Regression (Group R)

Skipped when reference SPAN file is absent (same `pytestmark` pattern as
`test_span_calculator_regression.py`).

Tests verify:
- **R1 NIFTY spread (1 near lot long + 1 far lot short):**
  - `NseMarginEngine.get_used_margin` < `SpanMarginCalculator.get_used_margin`
  - Credit = (2244.36 + 2255.78 − 425.0) × 65 × 1 ≈ 264,884 Rs
  - Net margin ≈ 27,625 Rs
- **R2 Outright only:** identical to SpanMarginCalculator (regression)
- **R3 Partial match:** credit on matched lots only; unmatched charged at full scan
- **R4 BANKNIFTY spread:** credit = (5513.40 + far_scan − 1029.0) × 30 × n_matched

### Phase 10 — Handler Integration (Group N)

Tests verify:
- `ExecutionHandler` constructed with `span_snapshot` provides an `NseMarginEngine`
  instance (not `SpanMarginCalculator`) as `margin_tracker`
- `type(handler.margin_tracker) is NseMarginEngine`
- `ExecutionHandler` with `span_snapshot=None` still provides `MarginTracker` (unchanged)
- Existing handler tests remain GREEN

---

## 7. Risks (Ranked)

### Risk 1 — Unit of `intra_spread_charge_rs` (RESOLVED)
Pre-spec this was the primary blocker. The reference file confirms: `val=425.0` is
Rs per underlying unit (same denomination as `scan_risk`). Per-lot spread charge = 425 × 65
= 27,625 Rs for NIFTY, matching known NSE spread margin levels.  
**Residual risk: zero.**

### Risk 2 — Parser Flat Rate vs. Tier Fidelity (ACCEPTED, DEFERRED)
The frozen parser collapses all dSpread tiers to `min(rate/val)`. For the reference file,
all 153 NIFTY tiers are identical (425.0) and all 15 BANKNIFTY tiers are identical (1029.0),
so no information is lost today. If NSE introduces varied rates by month-gap in a future file,
the flat rate will under-charge the wider spreads.  
**Mitigation:** Documented in `nse_margin_engine.py`. Parser extension is a future milestone.

### Risk 3 — Options Not Matched (DESIGN DECISION)
Phase 1 matches only Future instruments. Options held alongside futures in the same underlying
are charged at full scan risk.  
**Mitigation:** Conservative (overestimates margin). NSE option spread credits use a delta-based
mechanism architecturally distinct from calendar spread credits. Explicitly out-of-scope.

### Risk 4 — Greedy vs. Optimal Matching
Greedy nearest-pair matching may not produce minimum total margin in all configurations.  
**Mitigation:** For a flat spread charge rate (all tiers equal), greedy ascending-expiry is
equivalent to NSE's delta-based matching for the Phase 1 scope. Standard practice for
exchange SPAN implementations.

### Risk 5 — `handler.py` Regression
The wiring change at `handler.py:204` is load-bearing. An incorrect swap silently changes
what margin logic is used.  
**Mitigation:** Group N integration tests pin the constructed type. Rollback = revert one line.

### Risk 6 — Lot Size Mismatch
Lot size taken from first FUTURE position for underlying. If instruments in the same
underlying have inconsistent lot sizes (should not occur on NSE), the credit will be wrong.  
**Mitigation:** NSE lot sizes are standardised per underlying per revision. Same assumption
as existing `SpanMarginCalculator._single_span_margin`.

---

## 8. Definition of Done

MM10.3 is complete when ALL of the following hold:

1. `core/risk/nse_margin_engine.py` exists with `NseMarginEngine`
2. `NseMarginEngine` satisfies `MarginCalculator` Protocol v2 structurally
3. `get_used_margin` returns less than bare `SpanMarginCalculator` for any portfolio
   with matched futures calendar spreads
4. Credit formula verified against real NIFTY data (Group R, test R1)
5. `git diff mm10.2-complete -- core/risk/span/span_calculator.py` shows zero changes
6. All Groups A–K and R in existing `test_span_calculator.py` and
   `test_span_calculator_regression.py` pass unchanged
7. All Groups A–N and R in `test_nse_margin_engine.py` pass
8. Group H guard tests confirm:
   - `span_calculator.py` contains no `elm`/`exposure_margin`/`broker` references
   - `nse_margin_engine.py` does not intrude on calculator private methods
9. Group G determinism tests pass
10. Group N confirms `ExecutionHandler` receives `NseMarginEngine` when `span_snapshot`
    is provided

---

## 9. ADR Triggered

Per `MM10_ARCHITECTURE_REVISION.md §8`:

**ADR-011: NseMarginEngine is the MarginCalculator for LIVE F&O**

Must be drafted by DeepSeek V4 and approved by ChatGPT Technical Lead before any
implementation code for MM10.3 is written. The ADR records:
- `NseMarginEngine` is the production `MarginCalculator` for LIVE F&O from MM10.3 onwards
- `SpanMarginCalculator` is its internal SPAN component — not the production calculator
  once spread credits are live
- `SpanMarginCalculator` remains a valid conservative fallback (scan-only)
- `MarginTracker` remains the flat-rate fallback

---

## 10. Engineering Constraints for DeepSeek V4

These are hard constraints, not style suggestions:

### Constructor signature (Phase 1 only)
```python
class NseMarginEngine:
    def __init__(
        self,
        span_calc: SpanMarginCalculator,
        span_snapshot: SpanSnapshot,
    ):
        self._span_calc = span_calc
        self._snapshot  = span_snapshot
```
`span_snapshot` is injected explicitly to avoid accessing `span_calc._snapshot` (private
attribute). The same `SpanSnapshot` object already in scope at the handler wiring site is
passed to both `SpanMarginCalculator` and `NseMarginEngine` — one authoritative snapshot,
two explicit holders. `span_calc.position_tracker` is public and accessed directly without
needing a separate injection.

ELM and exposure rate tables are MM10.4/MM10.5 parameters. They must NOT appear in the
MM10.3 constructor, even as `None` defaults.

### `get_used_margin` contract
```python
def get_used_margin(self, current_prices: Dict[str, float]) -> float:
    span_margin = self._span_calc.get_used_margin(current_prices)
    credit      = self._spread_credit(current_prices)
    return max(0.0, span_margin - credit)
```
`margin_rate` is already applied inside `SpanMarginCalculator.get_used_margin`.
Do NOT re-apply it in `NseMarginEngine` (double application under-reports margin).

### `margin_rate` property
```python
@property
def margin_rate(self) -> float:
    return self._span_calc.margin_rate
```

### Scan risk duplication
`_derive_contract_scan_risk` is intentionally duplicated from `SpanMarginCalculator`
(same pattern as `_SCENARIO_WEIGHTS` duplication). Do not import private methods from
`span_calculator.py`. Group H guard tests will fail if you do.

### PositionTracker access
`position_tracker` is already a public attribute on `SpanMarginCalculator`
(`self.position_tracker = position_tracker` in its `__init__`). Access it via
`self._span_calc.position_tracker` — do not accept it as a separate constructor argument.
A third injection site would create a second drift surface; the calculator and engine
must always share the same tracker instance.

### Options hard exclusion
```python
if position.instrument.type != InstrumentType.FUTURE:
    continue
```
This is a hard constraint in `_spread_credit`, not a configuration option.
