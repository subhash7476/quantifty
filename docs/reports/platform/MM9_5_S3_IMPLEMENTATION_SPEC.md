# MM9.5-S3 — SpanMarginCalculator Migration
## Implementation Specification

**Date:** 2026-06-29
**Milestone:** MM9.5-S3
**Status:** SPECIFICATION — no production code written
**Evidence base:**
- `core/risk/span/span_calculator.py` — current calculator (MM9.4-S3)
- `core/risk/span/span_snapshot.py` — immutable DTOs (MM9.5-S2)
- `core/risk/span/parser_v400.py` — v400 parser producing SpanSnapshot (MM9.5-S2)
- `tests/risk/span/test_span_calculator.py` — Groups A–G, all passing
- `tests/risk/span/test_span_composition.py` — Groups H–L, all passing
- `tests/risk/span/test_parser_v400_regression.py` — regression values from `nsccl.20260625.i01.spn`
- `docs/reports/MM9_5_S2_IMPLEMENTATION_SPEC.md` — S2 scope boundary

**Governing ADRs:** ADR-007 · ADR-008 · ADR-009 · ADR-010

---

## 1. Objective

Migrate `SpanMarginCalculator` from engineering placeholder inputs to
authoritative NSE Clearing SPAN values produced by `parser_v400`. After S3:

- The calculator reads all seven official risk metrics that the v400 parser
  populates inside `SpanRiskArray.risk_metrics`.
- The margin formula uses absolute-rupee RA values exactly as the parser
  produces them, not a percentage fraction assumed in MM9.4-S3.
- A full set of regression tests verifies that calculator output is derived
  from parser-produced values and not from synthetic test data.
- The parser and snapshot remain completely untouched.

This milestone is a **consumer migration**, not a parser enhancement. The
smallest possible change to `span_calculator.py` that achieves correct
arithmetic with real v400 data is the target.

---

## 2. Current Architecture

```
ParserRegistry
  ↓
parser_v400.parse_span_xml(raw: bytes) → SpanSnapshot
  ↓
SpanSnapshot (frozen dataclass)
  ↓
SpanMarginCalculator.__init__(position_tracker, span_snapshot, margin_rate)
  ↓
get_used_margin / get_exposure / get_incremental_margin
  ↓
Execution layer (margin gate in handler)
```

The calculator is the first and only current consumer of `SpanSnapshot`. The
parser has no knowledge of calculator logic. No circular dependencies exist.

---

## 3. Current Calculator Behaviour

### 3.1 Data path

```python
# _risk_percentage(symbol)
risk_array = self._snapshot.risk_arrays.get(symbol)
scan_risk  = risk_array.risk_metrics["scan_risk"]
som        = risk_array.risk_metrics["short_option_minimum"]
return max(scan_risk, som)              # treated as a decimal fraction
```

### 3.2 Margin formula

```python
# _single_span_margin(symbol, current_price)
lot_size = getattr(pos.instrument, "lot_size", None) or pos.instrument.multiplier
notional = pos.quantity * current_price * lot_size  # rupees
risk_pct = self._risk_percentage(symbol)            # assumed fraction, e.g. 0.15
return notional * risk_pct                          # rupees × fraction = rupees ✓
```

### 3.3 Defined constants (MM9.4-S3)

```python
SPAN_METRIC_SCAN_RISK        = "scan_risk"
SPAN_METRIC_SHORT_OPTION_MIN = "short_option_minimum"
```

### 3.4 Existing test assumptions

All existing tests supply `scan_risk` and `short_option_minimum` as
**decimal fractions** (e.g., `0.15`, `0.08`). The formula is correct for
that input shape.

---

## 4. Gap Analysis

### 4.1 CRITICAL — Unit incompatibility between parser output and calculator formula

The v400 parser derives `scan_risk` from the 16-scenario Risk Array (RA):

```python
# parser_v400._derive_scan_risk
SCENARIO_WEIGHTS = [1.0] * 14 + [0.3, 0.3]
return max(0.0, max(v * w for v, w in zip(ra, SCENARIO_WEIGHTS)))
```

The RA values represent **profit/loss in rupees per one underlying unit**
under each scenario. From the regression reference file
(`nsccl.20260625.i01.spn`):

| Symbol     | `scan_risk` (Rs/unit) | `price_scan_range` (Rs/unit) |
|------------|----------------------|------------------------------|
| NIFTY      | 2244.36              | 2234.01                      |
| BANKNIFTY  | 5513.40              | 5488.30                      |

These are **absolute rupee values per one underlying unit**, not percentage
fractions.

**Proof — current formula applied to real v400 data produces wrong output:**
```
# 10 NIFTY lots, price=24000, lot_size=75
notional  = 10 × 24,000 × 75 = 18,000,000 Rs
risk_pct  = max(2244.36, 0.0)  ← treated as fraction by current formula
margin    = 18,000,000 × 2244.36 ≈ 40 billion Rs   (WRONG — ~22,000× overstated)
```

**Correct SPAN formula (absolute-Rs model):**
```
margin_per_unit = max(scan_risk_rs, som_rs)         # Rs per underlying unit
margin          = qty_lots × lot_size × margin_per_unit × margin_rate
# 10 × 75 × 2244.36 × 1.0 = 1,683,270 Rs          (correct)
```

**IMPORTANT — SOM unit must be verified before implementation:**
`short_option_minimum` is sourced from `somTiers/tier/rate/val` in the XML.
Two plausible interpretations exist:

- **Rs per underlying unit** (consistent with scan_risk): `max()` is valid as-is
- **Percentage value** (e.g., 3.0 = 3% of underlying price): requires normalisation
  `som_rs = (som_pct / 100) × price` before the `max()`

For NSE index contracts NIFTY and BANKNIFTY, the reference file shows
`short_option_minimum = 0.0` — so the two interpretations are numerically
equivalent for these underlyings. The unit matters most for equity option
underlyings where SOM > 0.

The implementer must:
1. Read the SOM value for at least one equity underlying (non-zero SOM)
   from `nsccl.20260625.i01.spn`.
2. Compare it to the contract's notional to determine units.
3. Add a regression assertion for that SOM value before writing the formula.
4. Document the confirmed unit in an inline comment inside `_risk_per_unit()`.

### 4.2 Missing metric key constants

Five metric keys populated by the v400 parser have no corresponding constant
in `span_calculator.py`:

| Key in `risk_metrics`      | Parser source                           | Defined in calculator? |
|----------------------------|-----------------------------------------|------------------------|
| `scan_risk`                | `_derive_scan_risk(nearest_fut_ra)`     | ✅                     |
| `short_option_minimum`     | `somTiers/tier/rate/val`                | ✅                     |
| `price_scan_range`         | `scanRate/priceScan` of nearest future  | ❌                     |
| `vol_scan_range`           | `scanRate/volScan` of nearest future    | ❌                     |
| `cvf`                      | `phyPf/cvf` (always 1.0 for NSE)       | ❌                     |
| `intra_spread_charge_rs`   | `min(dSpread/rate/val)`                 | ❌                     |
| `risk_free_rate`           | `intrRate/val` of nearest future        | ❌                     |

### 4.3 No param accessor on the calculator

Callers cannot query price_scan_range, cvf, risk_free_rate, or spread charge
from the calculator's snapshot without bypassing the calculator entirely.
The public surface area needs one generic accessor.

### 4.4 No calculator regression tests against v400 data

All existing calculator tests use hand-crafted `SpanSnapshot` objects with
synthetic fractional values (schema_version="v1"). No test proves the
calculator handles a v400-parsed snapshot correctly. The unit error described
in §4.1 would only surface at runtime.

---

## 5. Exact Production Changes

### 5.1 `core/risk/span/span_calculator.py`

**Change 1 — Add five metric key constants (after the two existing ones):**

```python
SPAN_METRIC_PRICE_SCAN_RANGE     = "price_scan_range"
SPAN_METRIC_VOL_SCAN_RANGE       = "vol_scan_range"
SPAN_METRIC_CVF                  = "cvf"
SPAN_METRIC_INTRA_SPREAD_CHARGE  = "intra_spread_charge_rs"
SPAN_METRIC_RISK_FREE_RATE       = "risk_free_rate"
```

**Change 2 — Replace `_risk_percentage` with `_risk_per_unit`:**

Rename the helper and change the return semantics from "fraction" to
"absolute Rs per underlying unit":

```python
def _risk_per_unit(self, symbol: str) -> float:
    """Return SPAN margin in rupees per one underlying unit.

    Both scan_risk and short_option_minimum are sourced from the v400 parser
    as absolute rupees per underlying unit.  [Document confirmed SOM unit here
    after verification — see §4.1 of S3 spec.]
    """
    risk_array = self._snapshot.risk_arrays.get(symbol)
    if risk_array is None:
        raise MissingRiskArray(f"No SPAN risk array for symbol {symbol!r}")
    scan_risk = risk_array.risk_metrics.get(SPAN_METRIC_SCAN_RISK)
    if scan_risk is None:
        raise MissingRiskMetric(f"Missing '{SPAN_METRIC_SCAN_RISK}' for {symbol!r}")
    som = risk_array.risk_metrics.get(SPAN_METRIC_SHORT_OPTION_MIN, 0.0)
    # [If SOM is a percentage in the snapshot, apply:
    #  som_rs = (som / 100) × current_price before max()]
    return max(scan_risk, som)
```

**Change 3 — Update `_single_span_margin` to use absolute-Rs formula:**

```python
def _single_span_margin(self, symbol: str, current_price: float) -> float:
    pos      = self.position_tracker.get_position(symbol)
    lot_size = getattr(pos.instrument, "lot_size", None) or pos.instrument.multiplier
    risk     = self._risk_per_unit(symbol)           # Rs per underlying unit
    return pos.quantity * lot_size * risk             # qty_lots × units/lot × Rs/unit = Rs
```

Note: `get_exposure` is NOT changed — gross notional exposure is correctly
computed as `qty × price × lot_size` and does not use risk metrics.

**Change 4 — Update `get_incremental_margin`:**

```python
def get_incremental_margin(
    self, symbol: str, quantity: float, price: float, lot_size: float = 1.0
) -> float:
    risk = self._risk_per_unit(symbol)               # Rs per underlying unit
    return quantity * lot_size * risk * self.margin_rate
```

**Change 5 — Add `get_snapshot_param` accessor:**

```python
def get_snapshot_param(self, symbol: str, metric: str) -> float:
    """Return any risk_metrics value from the snapshot for a given symbol.

    Raises MissingRiskArray  if symbol not in snapshot.
    Raises MissingRiskMetric if metric absent.
    """
    risk_array = self._snapshot.risk_arrays.get(symbol)
    if risk_array is None:
        raise MissingRiskArray(f"No SPAN risk array for symbol {symbol!r}")
    value = risk_array.risk_metrics.get(metric)
    if value is None:
        raise MissingRiskMetric(f"Missing metric {metric!r} for symbol {symbol!r}")
    return value
```

### 5.2 `core/risk/span/__init__.py`

Add the five new constants to the import block and to `__all__`:

```python
from core.risk.span.span_calculator import (
    SpanMarginCalculator,
    SpanMarginError,
    UnsupportedInstrument,
    MissingRiskArray,
    MissingRiskMetric,
    SPAN_METRIC_SCAN_RISK,
    SPAN_METRIC_SHORT_OPTION_MIN,
    SPAN_METRIC_PRICE_SCAN_RANGE,
    SPAN_METRIC_VOL_SCAN_RANGE,
    SPAN_METRIC_CVF,
    SPAN_METRIC_INTRA_SPREAD_CHARGE,
    SPAN_METRIC_RISK_FREE_RATE,
)
```

### 5.3 `tests/risk/span/test_span_calculator.py`

**Update all existing test fixtures** in Groups A–G to supply `scan_risk` and
`short_option_minimum` as **absolute Rs per underlying unit** rather than
decimal fractions. Choose values so that expected margins remain identical
through the formula transformation:

```python
# Before (MM9.4-S3 — percentage-based, synthetic)
# qty=10, price=200, lot_size=1
snap = _snapshot({"NIFTY": {
    SPAN_METRIC_SCAN_RISK: 0.15,        # fraction
    SPAN_METRIC_SHORT_OPTION_MIN: 0.08,
}})
# margin = 10 × 200 × 1 × max(0.15, 0.08) = 300.0

# After (MM9.5-S3 — absolute-Rs, still synthetic but correct units)
# qty=10, lot_size=1, scan_risk in Rs/unit
snap = _snapshot({"NIFTY": {
    SPAN_METRIC_SCAN_RISK: 30.0,        # Rs per unit (chosen so 10×1×30=300)
    SPAN_METRIC_SHORT_OPTION_MIN: 16.0,
}})
# margin = 10 × 1 × max(30.0, 16.0) = 300.0  ← same expected value
```

This fixture update preserves all existing expected assertion values while
correcting the input unit. Every test in Groups A–G passes without changing
a single `assert` line.

**Add Group H — Snapshot param accessor tests** (new tests at the end of the
existing file, following Group G):

```
test_h1_get_snapshot_param_scan_risk
test_h2_get_snapshot_param_price_scan_range
test_h3_get_snapshot_param_cvf
test_h4_get_snapshot_param_missing_symbol_raises
test_h5_get_snapshot_param_missing_metric_raises
```

### 5.4 New file — `tests/risk/span/test_span_calculator_regression.py`

New test module containing Group R — calculator regression tests using
v400-realistic snapshot values pinned to the reference file.

Minimum assertions required (see §6 for the complete RED → GREEN sequence):
```
test_r1_v400_parsed_scan_risk_is_consumed_not_as_fraction
test_r2_nifty_margin_from_reference_snapshot          (skipped if reference absent)
test_r3_banknifty_margin_from_reference_snapshot      (skipped if reference absent)
test_r4_get_snapshot_param_price_scan_range_from_v400
test_r5_get_snapshot_param_risk_free_rate_from_v400
test_r6_determinism_with_v400_snapshot
test_r7_margin_is_independent_of_price_when_scan_risk_is_absolute
```

---

## 6. Test Plan — RED → GREEN

All tests are written before any production code change (TDD enforced).

### Phase 1 — RED: new constants missing (ImportError)

```python
# In test_span_calculator.py

def test_metric_constants_complete():
    from core.risk.span.span_calculator import (
        SPAN_METRIC_PRICE_SCAN_RANGE,
        SPAN_METRIC_VOL_SCAN_RANGE,
        SPAN_METRIC_CVF,
        SPAN_METRIC_INTRA_SPREAD_CHARGE,
        SPAN_METRIC_RISK_FREE_RATE,
    )
    assert SPAN_METRIC_PRICE_SCAN_RANGE    == "price_scan_range"
    assert SPAN_METRIC_VOL_SCAN_RANGE      == "vol_scan_range"
    assert SPAN_METRIC_CVF                 == "cvf"
    assert SPAN_METRIC_INTRA_SPREAD_CHARGE == "intra_spread_charge_rs"
    assert SPAN_METRIC_RISK_FREE_RATE      == "risk_free_rate"
```

Write five constants → GREEN.

### Phase 2 — RED: `get_snapshot_param` absent (AttributeError)

```python
def test_h2_get_snapshot_param_price_scan_range():
    snap = _snapshot({"NIFTY": {
        SPAN_METRIC_SCAN_RISK: 30.0,
        SPAN_METRIC_SHORT_OPTION_MIN: 0.0,
        SPAN_METRIC_PRICE_SCAN_RANGE: 29.0,
        SPAN_METRIC_CVF: 1.0,
    }})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    assert calc.get_snapshot_param("NIFTY", SPAN_METRIC_PRICE_SCAN_RANGE) == 29.0
```

Implement `get_snapshot_param` → GREEN.

### Phase 3 — RED: accessor exception tests

```python
def test_h4_get_snapshot_param_missing_symbol_raises():
    calc = SpanMarginCalculator(PositionTracker(), _snapshot({}))
    with pytest.raises(MissingRiskArray):
        calc.get_snapshot_param("UNKNOWN", SPAN_METRIC_SCAN_RISK)

def test_h5_get_snapshot_param_missing_metric_raises():
    snap = _snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0}})
    calc = SpanMarginCalculator(PositionTracker(), snap)
    with pytest.raises(MissingRiskMetric):
        calc.get_snapshot_param("NIFTY", SPAN_METRIC_CVF)
```

Add raises inside accessor → GREEN.

### Phase 4 — RED: price-independence test (unit incompatibility proof)

```python
# In test_span_calculator_regression.py

def _v400_snapshot():
    """Synthetic snapshot using v400-parser output format: absolute Rs/unit."""
    return SpanSnapshot(
        snapshot_date=date(2026, 6, 25),
        schema_version="4.00",
        exchange="NSE",
        segment="FO",
        file_hash="s3_regression_fixture",
        is_settlement=False,
        risk_arrays={
            "NIFTY": SpanRiskArray("NIFTY", {
                "scan_risk":              2244.36,
                "short_option_minimum":   0.0,
                "price_scan_range":       2234.01,
                "vol_scan_range":         6.0,
                "cvf":                    1.0,
                "intra_spread_charge_rs": 425.0,
                "risk_free_rate":         0.07,
            }),
        },
        metadata={},
    )


def test_r7_margin_is_independent_of_price_when_scan_risk_is_absolute():
    """Absolute-Rs formula: margin must NOT scale with price changes.

    If this test fails, the formula is still percentage-based (wrong).
    """
    pt = _tracker_with_lots("NIFTY", qty=10, lot_size=75)
    calc = SpanMarginCalculator(pt, _v400_snapshot())
    m_at_24000 = calc.get_used_margin({"NIFTY": 24000.0})
    m_at_25000 = calc.get_used_margin({"NIFTY": 25000.0})
    assert m_at_24000 == m_at_25000, (
        "Margin must not change with price in the absolute-Rs model"
    )
    # 10 lots × 75 units/lot × 2244.36 Rs/unit = 1,683,270 Rs
    assert m_at_24000 == pytest.approx(1_683_270.0, rel=1e-6)
```

This test is RED with the current formula (produces ~40B Rs, and varies with
price). Updating the formula → GREEN.

### Phase 5 — RED: existing Groups A–G fail after fixture update

Update Groups A–G fixtures from fraction to Rs-unit values (§5.3). With the
old formula still in place they fail. Applying the formula update from §5.1
resolves all of them simultaneously. → GREEN.

### Phase 6 — RED: reference-file regression tests

```python
# In test_span_calculator_regression.py

SPAN_FILE = (
    pathlib.Path(__file__).resolve().parents[3]
    / "reference" / "span" / "nsccl.20260625.i1" / "nsccl.20260625.i01.spn"
)
pytestmark = pytest.mark.skipif(
    not SPAN_FILE.exists(), reason="Reference SPAN file absent"
)

@pytest.fixture(scope="module")
def real_snapshot():
    from core.risk.span.parser_v400 import parse_span_xml
    return parse_span_xml(SPAN_FILE.read_bytes())


def test_r2_nifty_margin_from_reference_snapshot(real_snapshot):
    pt = _tracker_with_lots("NIFTY", qty=10, lot_size=75)
    calc = SpanMarginCalculator(pt, real_snapshot)
    # 10 × 75 × 2244.36 = 1,683,270 Rs
    assert calc.get_used_margin({"NIFTY": 24000.0}) == pytest.approx(1_683_270.0, abs=1.0)

def test_r3_banknifty_margin_from_reference_snapshot(real_snapshot):
    pt = _tracker_with_lots("BANKNIFTY", qty=5, lot_size=35)
    calc = SpanMarginCalculator(pt, real_snapshot)
    # 5 × 35 × 5513.40 = 964,845 Rs
    assert calc.get_used_margin({"BANKNIFTY": 52000.0}) == pytest.approx(964_845.0, abs=1.0)
```

These tests skip (not fail) if the reference file is absent. They are the
definitive margin oracle when the reference file is present.

### Phase 7 — VERIFY: import isolation still holds (Groups F1–F4)

Groups F1–F4 (does not import parser, repository, pipeline, readiness, or
runner) must pass unchanged. The calculator must import NO new modules.
Verify with `python -m pytest tests/risk/span/test_span_calculator.py -k "f1 or f2 or f3 or f4"`.

### Phase 8 — VERIFY: composition tests still pass (Groups H–L)

`test_span_composition.py` Groups H–L must pass after updating the
composition test's `_make_snapshot` helper to use Rs-unit values consistent
with the new formula. The public API signatures of all calculator methods
are unchanged, so only fixture values need updating.

---

## 7. Definition of Done

- [ ] `SPAN_METRIC_PRICE_SCAN_RANGE`, `SPAN_METRIC_VOL_SCAN_RANGE`,
      `SPAN_METRIC_CVF`, `SPAN_METRIC_INTRA_SPREAD_CHARGE`,
      `SPAN_METRIC_RISK_FREE_RATE` constants exist in `span_calculator.py`
      and are exported from `core/risk/span/__init__.py`.
- [ ] `SpanMarginCalculator.get_snapshot_param(symbol, metric)` is
      implemented, raises `MissingRiskArray` / `MissingRiskMetric` correctly.
- [ ] Margin formula uses absolute-Rs-per-unit arithmetic. Confirmed by
      `test_r7_margin_is_independent_of_price_when_scan_risk_is_absolute`
      passing GREEN.
- [ ] `test_span_calculator.py` Groups A–G pass with updated Rs-unit fixtures.
- [ ] `test_span_calculator.py` Group H (accessor tests) all GREEN.
- [ ] `test_span_calculator_regression.py` Group R: all tests GREEN or SKIP.
      No FAIL permitted, not even for reference-absent tests.
- [ ] SOM unit confirmed and documented in inline comment within
      `_risk_per_unit()`.
- [ ] All previously passing tests in `tests/risk/span/` remain GREEN.
- [ ] `span_parser.py`, `parser_v400.py`, `span_snapshot.py`,
      `span_pipeline.py`, `span_repository.py`, `span_readiness.py`,
      `span_freshness.py` have zero diff.

---

## 8. Files to Modify

| File | Nature of change |
|------|-----------------|
| `core/risk/span/span_calculator.py` | Add 5 constants; rename `_risk_percentage` → `_risk_per_unit`; update formula in `_single_span_margin` and `get_incremental_margin`; add `get_snapshot_param` |
| `core/risk/span/__init__.py` | Export 5 new constants |
| `tests/risk/span/test_span_calculator.py` | Update Groups A–G fixtures from fractions to Rs-unit values; add Group H |
| `tests/risk/span/test_span_calculator_regression.py` | **New file** — Group R regression tests |

---

## 9. Files That Must NOT Change

| File | Reason |
|------|--------|
| `core/risk/span/span_parser.py` | Parser registry; complete as of MM9.5-S1 |
| `core/risk/span/parser_v400.py` | v400 parser; complete as of MM9.5-S2 |
| `core/risk/span/span_snapshot.py` | Immutable DTOs; complete as of MM9.5-S2 |
| `core/risk/span/span_pipeline.py` | Pipeline primitives; out of scope |
| `core/risk/span/span_repository.py` | On-disk read path; out of scope |
| `core/risk/span/span_readiness.py` | Startup gate; out of scope |
| `core/risk/span/span_freshness.py` | Date logic; out of scope |
| `core/execution/handler.py` | Execution layer; out of scope |
| `tests/risk/span/test_parser_v400.py` | Parser tests; parser is locked |
| `tests/risk/span/test_parser_v400_s2.py` | Parser completeness tests; locked |
| `tests/risk/span/test_parser_v400_regression.py` | Parser regression oracle; locked |
| `tests/risk/span/test_span_snapshot.py` | DTO immutability tests; out of scope |

`test_span_composition.py` may require fixture value updates to match the
new Rs-unit formula (see §6 Phase 8), but its test logic and public API
assertions must remain structurally identical.

---

## 10. Risks

### R1 — SOM unit ambiguity (HIGH probability, MEDIUM impact)

`short_option_minimum` from `somTiers/tier/rate/val` may be a percentage
value (e.g., 3.0 = 3%) rather than absolute Rs per unit. If so,
`max(scan_risk_rs, som_raw)` is dimensionally invalid. Impact is limited
because NIFTY and BANKNIFTY have SOM = 0.0, making the formula correct for
these underlyings regardless of unit interpretation.

**Mitigation**: Read SOM for a non-zero equity underlying from the reference
file before writing the formula. Add a dedicated regression assertion.
Document confirmed unit in `_risk_per_unit()` comment.

### R2 — `test_span_composition.py` fixture values break silently

If the composition tests construct a snapshot with fraction-based values and
the formula changes to absolute-Rs, the margin assertion values will be wrong
by 1000×. Tests remain GREEN only if fixture values are updated alongside
the formula.

**Mitigation**: Phase 8 explicitly lists composition fixture updates as a
required verification step. Run composition tests before and after formula
change.

### R3 — Reference-file margin assertions use wrong lot size

`test_r2` and `test_r3` hardcode lot_size=75 (NIFTY) and lot_size=35
(BANKNIFTY). If the actual NSE lot sizes differ from the reference SPAN
file's contract specifications, the assertions will fail.

**Mitigation**: Confirm lot sizes from the instrument DB or NSE official
circulars before pinning the expected values. Alternatively, derive lot_size
from the snapshot's futures contracts if available.

### R4 — Lot-size attribute naming on instrument (pre-existing, low)

The existing formula already handles:
```python
lot_size = getattr(pos.instrument, "lot_size", None) or pos.instrument.multiplier
```
If multiplier is 1.0 instead of the correct F&O lot size, the margin is
wrong by the lot size factor. This is a pre-existing issue, not introduced
by S3. Preserve the existing lookup logic unchanged.

---

## 11. Acceptance Criteria

1. `calc.get_used_margin(prices)` returns a result that is **independent of
   `prices`** when `scan_risk` is a constant absolute-Rs value. (Price enters
   `get_exposure` only; not the SPAN margin path.)

2. `calc.get_used_margin` for 10 NIFTY lots with reference-file scan_risk
   (2244.36) and lot_size=75 equals exactly **1,683,270 Rs** (within 1 Rs).

3. `calc.get_snapshot_param("NIFTY", "price_scan_range")` returns the parsed
   value without touching the underlying XML or opening any file.

4. `python -m pytest tests/risk/span/ -x` exits 0.

5. The following grep returns no output (import isolation preserved):
   ```
   grep -n "span_parser\|span_repository\|span_pipeline\|span_readiness\|ParserRegistry" \
        core/risk/span/span_calculator.py
   ```

6. The calculator does not open, read, or write any file on disk.
   Existing Group F test `test_no_filesystem_io` must still pass.

---

## 12. Out-of-Scope

The following are **explicitly excluded** from MM9.5-S3:

- Inter-month spread charge deductions (requires portfolio offset logic)
- Delivery margin and MTM margin
- Option delta-based margin (SPAN delta-ladder computation)
- CVF usage in the margin formula (CVF = 1.0 for all NSE contracts)
- `vol_scan_range` usage in the margin formula
- `risk_free_rate` usage in the margin formula
- `intra_spread_charge_rs` usage in the margin formula
- Parser modifications of any kind — no new XML parsing
- `SpanSnapshot` or `SpanRiskArray` DTO changes
- Execution handler changes
- Runner, startup, or readiness changes
- UI changes
- `SpanRepository` or `SpanPipeline` changes
- `SpanFreshness` changes
- Performance optimisations beyond what correctness requires
- Circular dependency of any kind between calculator and parser layers

---

## 13. Rollback Strategy

S3 touches only `span_calculator.py`, `__init__.py`, and tests. The rollback
procedure is:

1. `git revert <S3-commit-sha>` — single commit revert.
2. `python -m pytest tests/risk/span/` passes immediately (reverts to MM9.4-S3
   formula with fractional test fixtures).
3. The execution handler receives a `SpanMarginCalculator` with the old
   formula — margin gating resumes with pre-S3 behaviour.
4. No snapshot files, DuckDB files, or configuration files are touched by S3;
   no data-layer rollback is required.

---

## Appendix A — Regression Oracle Values

From `reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn`
(locked in `test_parser_v400_regression.py`, must not be re-derived):

| Symbol     | `scan_risk` | `price_scan_range` | `intra_spread_charge_rs` | `risk_free_rate` | `cvf` |
|------------|-------------|---------------------|--------------------------|------------------|-------|
| NIFTY      | 2244.36     | 2234.01             | 425.0                    | 0.07             | 1.0   |
| BANKNIFTY  | 5513.40     | 5488.30             | 1029.0                   | TBD              | 1.0   |

**The S3 implementer must add `short_option_minimum` values for NIFTY,
BANKNIFTY, and at least one equity underlying (non-zero SOM) to this table
before writing test assertions.**

## Appendix B — Derived Margin Oracle

For `test_r2` and `test_r3` (skipped if reference file absent):

| Symbol    | qty_lots | lot_size | scan_risk  | Expected margin (Rs) |
|-----------|----------|----------|------------|----------------------|
| NIFTY     | 10       | 75       | 2244.36    | 1,683,270.0          |
| BANKNIFTY | 5        | 35       | 5513.40    | 964,845.0            |

Formula: `expected = qty_lots × lot_size × scan_risk`
(These values hold regardless of the `current_price` argument passed to
`get_used_margin` — that is the defining property of the absolute-Rs model.)
