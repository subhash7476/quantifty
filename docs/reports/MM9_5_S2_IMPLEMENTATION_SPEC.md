# MM9.5-S2 — Parser Completeness
## Implementation Specification

**Date:** 2026-06-29
**Milestone:** MM9.5-S2
**Status:** SPECIFICATION — no production code written
**Evidence base:**
- `docs/reports/SPAN_XML_SCHEMA_AND_MM9_MAPPING.md` — XML schema + gap analysis G-1 through G-8
- `docs/reports/MM9_5_S1_IMPLEMENTATION_SPEC.md` — S1 completed scope
- `core/risk/span/parser_v400.py` — S1 production parser (current state)
- `core/risk/span/span_snapshot.py` — current DTOs
- `tests/risk/span/test_parser_v400.py` — S1 test suite (Blocks A–G, all passing)
- `reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn` — real NSE SPAN file (57.2 MB)
**Governing ADRs:** ADR-007 · ADR-008 · ADR-009 · ADR-010

---

## 1. Objective

Make `parser_v400` a **complete** transformation of the PC-SPAN 4.00 XML into `SpanSnapshot`. After S2, a consumer holding only a `SpanSnapshot` has everything required to:

- compute per-contract SPAN margin for any futures or option position (MM10+ scope)
- validate scan scenario parameters against the file that produced them
- credit inter-month spread charges (MM10+ scope)
- assert that all NSE contracts carry `cvf = 1.0`

The parser remains a pure `bytes → SpanSnapshot` transformation. Zero calculator logic, zero business rules, zero runtime dependencies enter the parser.

### What S1 already provides (do not repeat or replace)

| Data | Source in XML | How stored in S1 |
|------|--------------|------------------|
| snapshot_date, is_settlement, exchange, schema_version, file_hash | `<pointInTime>` | `SpanSnapshot` fields |
| scan_risk per underlying | Nearest-expiry `<futPf/fut/ra/a>` × 16 | `risk_metrics["scan_risk"]` |
| short_option_minimum | `<ccDef/somTiers/rate/val>` | `risk_metrics["short_option_minimum"]` |
| Raw 16-scenario values per underlying | Same `<fut/ra>` | `metadata["scenario_values"]` |
| created, clearing_org, counts | `<created>`, `<ec>`, element counts | `metadata` keys |

---

## 2. Current Architecture (S1 End-State)

```
raw bytes (latin-1 XML)
  ↓  parse_span_xml(raw: bytes)          ADR-009
  ├── decode latin-1
  ├── ElementTree.fromstring
  ├── extract preamble                   → SpanSnapshot.{snapshot_date, is_settlement, exchange, …}
  ├── build fut_pfs index (by pfCode)
  ├── count option_count from oopPf
  └── for each <ccDef>:
        ├── extract symbol, SOM
        ├── look up fut_pf by pfCode
        ├── select nearest-expiry <fut> by <pe>
        ├── extract 16 <ra/a>            → scan_risk + scenario_values
        └── emit SpanRiskArray(symbol, {scan_risk, short_option_minimum})
  → SpanSnapshot(
        risk_arrays: Dict[str, SpanRiskArray],   # keyed by cc, 239 entries
        metadata: {created, clearing_org, underlying_count,
                   futures_contract_count, option_count, scenario_values}
    )
```

**Layering after S1:**

```
ParserRegistry
  ↓
ParserV400 (parse_span_xml)
  ↓
SpanSnapshot (immutable)        ← S2 extends this; all S1 fields preserved
  ↓
SpanMarginCalculator            ← must NOT change in S2
  ↓
Execution
```

---

## 3. Gap Analysis (S2-Specific)

All gaps below are additive. Nothing in S1 is wrong or removed.

| ID | Description | Severity | XML source | S2 resolution |
|----|-------------|----------|------------|---------------|
| S2-G1 | Price scan range absent from `risk_metrics` | HIGH | `<futPf/fut/scanRate/priceScan>` (nearest expiry) | Add `"price_scan_range"` to `risk_metrics` |
| S2-G2 | Vol scan range absent from `risk_metrics` | HIGH | `<futPf/fut/scanRate/volScan>` (nearest expiry) | Add `"vol_scan_range"` to `risk_metrics` |
| S2-G3 | CVF not captured (SPAN gap G-4) | MEDIUM | `<phyPf/cvf>` | Add `"cvf"` to `risk_metrics`; default 1.0 if absent |
| S2-G4 | Spread charges not captured (SPAN gap G-3) | MEDIUM | `<ccDef/dSpread/rate/val>` | Add `"intra_spread_charge_rs"` to `risk_metrics`; minimum charge across tiers; 0.0 if absent |
| S2-G5 | Risk-free rate not captured | MEDIUM | `<futPf/fut/intrRate/val>` (nearest expiry) | Add `"risk_free_rate"` to `risk_metrics`; 0.0 if absent |
| S2-G6 | Scenario grid definitions absent from `metadata` (SPAN gap G-8) | LOW | `<pointDef/scanPointDef>` | Add `metadata["scan_scenarios"]` as list of 16 dicts |
| S2-G7 | Per-contract futures data not extracted | HIGH | `<futPf/fut>` (all fields) | New `SpanFutureContract` DTO; `SpanSnapshot.futures` field |
| S2-G8 | Per-expiry option series not extracted | HIGH | `<oopPf/series>` | New `SpanOptionSeries` DTO; `SpanSnapshot.option_series` field |
| S2-G9 | Per-strike option data not extracted (SPAN gap G-7) | HIGH | `<oopPf/series/opt>` with RA[16] | New `SpanOptionContract` DTO; `SpanSnapshot.option_contracts` field |

**Not in S2 scope (deferred, per §12):** per-strike RA validation against recomputed Greeks, spread netting logic, interest-rate compounding, delta scenarios.

---

## 4. Exact Production Changes

### 4.1 `core/risk/span/span_snapshot.py` — Three new DTOs + three new SpanSnapshot fields

#### 4.1.1 New frozen dataclasses

Add in this order, below `SpanRiskArray`, above `SpanSnapshot`:

```python
@dataclass(frozen=True)
class SpanFutureContract:
    """Per-expiry futures contract extracted from <futPf/fut>."""
    symbol: str
    expiry: date                   # <pe> YYYYMMDD
    price: float                   # <p>
    delta: float                   # <d> — always 1.0 for futures
    time_to_expiry: float          # <t> in years
    risk_free_rate: float          # <intrRate/val> annualised; 0.0 if absent
    price_scan_range: float        # <scanRate/priceScan>; 0.0 if absent
    vol_scan_range: float          # <scanRate/volScan>; 0.0 if absent
    ra: Tuple[float, ...]          # 16 scenario P&L values in Rs per lot-unit


@dataclass(frozen=True)
class SpanOptionSeries:
    """Per-expiry option series extracted from <oopPf/series>."""
    symbol: str
    expiry: date                   # <pe> YYYYMMDD
    vol: float                     # <v> at-the-money vol for this series
    price_scan_range: float        # <scanRate/priceScan>; 0.0 if absent
    vol_scan_range: float          # <scanRate/volScan>; 0.0 if absent
    time_to_expiry: float          # <t> in years; 0.0 if absent
    risk_free_rate: float          # <intrRate/val>; 0.0 if absent


@dataclass(frozen=True)
class SpanOptionContract:
    """Per-strike option contract extracted from <oopPf/series/opt>."""
    symbol: str
    expiry: date                   # inherited from parent <series/pe>
    strike: float                  # <k>
    option_type: str               # "C" or "P"   (from <o> element)
    price: float                   # <p>
    delta: float                   # <d>
    implied_vol: float             # <v>; 0.0 if absent
    ra: Tuple[float, ...]          # 16 scenario P&L values in Rs per lot-unit
```

**Required import addition:** `from typing import Tuple` must be present at the top of `span_snapshot.py`.

#### 4.1.2 New fields on `SpanSnapshot`

Append three new fields with `field(default_factory=dict)` at the **end** of the `SpanSnapshot` dataclass. This preserves backwards compatibility: all existing callers using keyword arguments continue to work; the new fields default to `{}`.

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class SpanSnapshot:
    # --- Existing S1 fields (unchanged) ---
    snapshot_date: date
    schema_version: str
    exchange: str
    segment: str
    file_hash: str
    is_settlement: bool
    risk_arrays: Dict[str, SpanRiskArray]
    metadata: Dict[str, Any]
    # --- New S2 fields ---
    futures: Dict[str, Tuple[SpanFutureContract, ...]] = field(default_factory=dict)
    option_series: Dict[str, Tuple[SpanOptionSeries, ...]] = field(default_factory=dict)
    option_contracts: Dict[str, Tuple[SpanOptionContract, ...]] = field(default_factory=dict)
```

All three dicts are keyed by the underlying symbol (same key space as `risk_arrays`). Values are immutable tuples (not lists) to honour the frozen semantics of the snapshot. The `field(default_factory=dict)` form is required because `frozen=True` dataclasses cannot use mutable defaults directly.

**Backwards-compatibility guarantee:** Any existing code that constructs `SpanSnapshot` with the 8 S1 keyword arguments will continue to work. Any existing equality assertion (`snap1 == snap2`) will still work because both snapshots will have `futures={}`, `option_series={}`, `option_contracts={}` by default.

---

### 4.2 `core/risk/span/parser_v400.py` — Extended extraction

#### 4.2.1 New constant

```python
SPAN_CVF_EXPECTED = 1.0   # NSE publishes cvf=1.0 for all F&O; stored for caller assertion
```

#### 4.2.2 New shared helper: `_safe_float`

```python
def _safe_float(s: Optional[str], default: float = 0.0) -> float:
    if s is None or s == "":
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default
```

This replaces ad-hoc `float(…or "0")` patterns throughout the module. Existing uses of `float(som_raw)` inside `try/except` in S1 may be simplified to `_safe_float(som_raw)`.

#### 4.2.3 Refactor `_derive_scan_risk` → `_extract_ra_tuple` + `_derive_scan_risk`

The S1 `_derive_scan_risk(fut)` does two things: extracts RA values and derives `scan_risk`. Split it into two:

```python
def _extract_ra_tuple(elem: Element) -> Tuple[float, ...]:
    """Extract and validate exactly 16 RA values from any <ra> block."""
    a_elements = elem.findall("ra/a")
    if len(a_elements) != 16:
        raise UnsupportedSpanSchema(
            f"Expected 16 RA scenarios, got {len(a_elements)}"
        )
    vals = []
    for a in a_elements:
        try:
            vals.append(float(a.text))
        except (ValueError, TypeError) as e:
            raise UnsupportedSpanSchema(
                f"Invalid RA value '{a.text or ''}' in <ra/a>: {e}"
            )
    return tuple(vals)


def _derive_scan_risk(ra: Tuple[float, ...]) -> float:
    """Derive scan_risk from a pre-extracted 16-tuple of RA values."""
    weighted_losses = [-v * w for v, w in zip(ra, SCENARIO_WEIGHTS)]
    return max(0.0, max(weighted_losses))
```

The S1 call site changes from `scan_risk, fut_ra = _derive_scan_risk(nearest)` to:

```python
fut_ra = _extract_ra_tuple(nearest)
scan_risk = _derive_scan_risk(fut_ra)
```

This refactor is non-breaking: the `scan_risk` value is identical; `fut_ra` is now a clean `Tuple[float, ...]` reused for `SpanFutureContract`.

#### 4.2.4 New structural indices (built once before the ccDef loop)

S1 already builds `fut_pfs: Dict[str, Element]`. S2 adds:

```python
# Physical portfolio index (for cvf extraction)
phy_pfs: Dict[str, Element] = {
    pp.findtext("pfCode", ""): pp
    for pp in root.findall("pointInTime/clearingOrg/exchange/phyPf")
    if pp.findtext("pfCode", "") != ""
}

# Options portfolio index (for series/opt extraction)
oop_pf_index: Dict[str, Element] = {
    op.findtext("pfCode", ""): op
    for op in root.findall("pointInTime/clearingOrg/exchange/oopPf")
    if op.findtext("pfCode", "") != ""
}
```

#### 4.2.5 Scenario grid extraction (called once before the ccDef loop)

```python
def _extract_scan_scenarios(root: Element) -> List[Dict]:
    scenarios = []
    for sp in root.findall("pointInTime/clearingOrg/pointDef/scanPointDef"):
        try:
            num = _safe_float(sp.findtext("priceScanDef/numerator", "0"))
            den = _safe_float(sp.findtext("priceScanDef/denominator", "1"), default=1.0)
            vnum = _safe_float(sp.findtext("volScanDef/numerator", "0"))
            vden = _safe_float(sp.findtext("volScanDef/denominator", "1"), default=1.0)
            scenarios.append({
                "point": int(sp.findtext("point", "0")),
                "paired_point": int(sp.findtext("pairedPoint", "0")),
                "price_mult": num / den if den != 0.0 else 0.0,
                "vol_mult": vnum / vden if vden != 0.0 else 0.0,
                "weight": _safe_float(sp.findtext("weight", "1.0"), default=1.0),
            })
        except (ValueError, TypeError):
            continue  # malformed entry: skip, never raise
    return scenarios
```

If `<pointDef>` is absent, `findall` returns `[]` and `scenarios` is `[]`. This is not an error.

#### 4.2.6 New metric extraction per underlying (in the ccDef loop)

After selecting `nearest` (the nearest-expiry futures element), extract the additional metrics:

```python
# From nearest-expiry futures element
price_scan_range = _safe_float(nearest.findtext("scanRate/priceScan")) if nearest is not None else 0.0
vol_scan_range   = _safe_float(nearest.findtext("scanRate/volScan"))   if nearest is not None else 0.0
risk_free_rate   = _safe_float(nearest.findtext("intrRate/val"))        if nearest is not None else 0.0

# CVF from physical portfolio
phy_pf = phy_pfs.get(symbol)
cvf = _safe_float(phy_pf.findtext("cvf") if phy_pf is not None else None, default=SPAN_CVF_EXPECTED)

# Intra-spread charge from ccDef/dSpread tiers
spread_vals = [
    _safe_float(d.findtext("rate/val"))
    for d in cc.findall("dSpread")
]
intra_spread_charge_rs = min(spread_vals) if spread_vals else 0.0
```

The `SpanRiskArray` construction becomes:

```python
risk_arrays[symbol] = SpanRiskArray(
    symbol=symbol,
    risk_metrics={
        "scan_risk": scan_risk,                        # S1 — unchanged
        "short_option_minimum": short_option_minimum,  # S1 — unchanged
        "price_scan_range": price_scan_range,          # S2
        "vol_scan_range": vol_scan_range,              # S2
        "cvf": cvf,                                    # S2
        "intra_spread_charge_rs": intra_spread_charge_rs,  # S2
        "risk_free_rate": risk_free_rate,              # S2
    },
)
```

**Invariant:** All 7 keys are always emitted. No key is ever absent. The S1 calculator reads only `scan_risk` and `short_option_minimum`; the new keys are invisible to it.

#### 4.2.7 `SpanFutureContract` extraction

For each symbol in the ccDef loop, after existing futures processing:

```python
def _extract_future_contracts(
    symbol: str,
    fut_pf: Optional[Element],
) -> Tuple[SpanFutureContract, ...]:
    if fut_pf is None:
        return ()
    result = []
    for fut in fut_pf.findall("fut"):
        pe_s = fut.findtext("pe", "")
        if not pe_s or pe_s == "00000000":
            continue
        try:
            expiry = datetime.strptime(pe_s, "%Y%m%d").date()
        except ValueError:
            continue  # unparseable expiry: skip this contract
        ra = _extract_ra_tuple(fut)  # raises UnsupportedSpanSchema if != 16
        result.append(SpanFutureContract(
            symbol=symbol,
            expiry=expiry,
            price=_safe_float(fut.findtext("p")),
            delta=_safe_float(fut.findtext("d"), default=1.0),
            time_to_expiry=_safe_float(fut.findtext("t")),
            risk_free_rate=_safe_float(fut.findtext("intrRate/val")),
            price_scan_range=_safe_float(fut.findtext("scanRate/priceScan")),
            vol_scan_range=_safe_float(fut.findtext("scanRate/volScan")),
            ra=ra,
        ))
    result.sort(key=lambda c: c.expiry)  # nearest expiry first
    return tuple(result)
```

#### 4.2.8 `SpanOptionSeries` and `SpanOptionContract` extraction

```python
def _extract_option_data(
    symbol: str,
    oop_pf: Optional[Element],
) -> Tuple[Tuple[SpanOptionSeries, ...], Tuple[SpanOptionContract, ...]]:
    if oop_pf is None:
        return (), ()
    series_list: List[SpanOptionSeries] = []
    contracts_list: List[SpanOptionContract] = []
    for series in oop_pf.findall("series"):
        pe_s = series.findtext("pe", "")
        if not pe_s or pe_s == "00000000":
            continue
        try:
            expiry = datetime.strptime(pe_s, "%Y%m%d").date()
        except ValueError:
            continue
        series_list.append(SpanOptionSeries(
            symbol=symbol,
            expiry=expiry,
            vol=_safe_float(series.findtext("v")),
            price_scan_range=_safe_float(series.findtext("scanRate/priceScan")),
            vol_scan_range=_safe_float(series.findtext("scanRate/volScan")),
            time_to_expiry=_safe_float(series.findtext("t")),
            risk_free_rate=_safe_float(series.findtext("intrRate/val")),
        ))
        for opt in series.findall("opt"):
            ra = _extract_ra_tuple(opt)  # raises UnsupportedSpanSchema if != 16
            contracts_list.append(SpanOptionContract(
                symbol=symbol,
                expiry=expiry,
                strike=_safe_float(opt.findtext("k")),
                option_type=opt.findtext("o", ""),
                price=_safe_float(opt.findtext("p")),
                delta=_safe_float(opt.findtext("d")),
                implied_vol=_safe_float(opt.findtext("v")),
                ra=ra,
            ))
    return tuple(series_list), tuple(contracts_list)
```

#### 4.2.9 Updated `SpanSnapshot` construction

```python
return SpanSnapshot(
    snapshot_date=snapshot_date,
    schema_version=schema_version,
    exchange=exchange_code,
    segment=SEGMENT_FO,
    file_hash=file_hash,
    is_settlement=(is_setl_s == "1"),
    risk_arrays=risk_arrays,
    metadata={
        "created": created_ts,
        "clearing_org": clearing_org,
        "underlying_count": len(risk_arrays),
        "futures_contract_count": futures_count,
        "option_count": option_count,
        "scenario_values": scenario_values,      # S1 — unchanged
        "scan_scenarios": scan_scenarios,         # S2 — new
    },
    futures=futures_by_symbol,                   # S2 — new
    option_series=option_series_by_symbol,        # S2 — new
    option_contracts=option_contracts_by_symbol,  # S2 — new
)
```

All three new dicts are `Dict[str, Tuple[…]]` keyed by symbol, built by calling `_extract_future_contracts` and `_extract_option_data` in the ccDef loop.

---

### 4.3 `core/risk/span/__init__.py` — New exports

Add to the import line and `__all__`:

```python
from core.risk.span.span_snapshot import (
    SpanSnapshot,
    SpanRiskArray,
    UnsupportedSpanSchema,
    SpanFutureContract,    # new S2
    SpanOptionSeries,      # new S2
    SpanOptionContract,    # new S2
)
```

Add `"SpanFutureContract"`, `"SpanOptionSeries"`, `"SpanOptionContract"` to `__all__`.

---

### 4.4 Size characteristic note (informational, not a constraint)

The real NSE SPAN file contains 158,713 option contracts each with a 16-value RA tuple. As in-memory Python `Tuple[float, ...]` objects, each contract is approximately 256–320 bytes. The full `option_contracts` collection for this file is estimated at 40–50 MB in memory. This is the correct and expected size for a complete SPAN snapshot. No optimisation is permitted in S2. Future slices may introduce lazy loading through `SpanRepository` if needed.

---

## 5. Test Plan (RED → GREEN)

### 5.1 Test file inventory

| File | Status | Purpose |
|------|--------|---------|
| `tests/risk/span/test_parser_v400.py` | **EXISTING — must not be modified** | S1 Blocks A–G; must remain passing |
| `tests/risk/span/test_parser_v400_s2.py` | **NEW** | S2 Blocks H–L (unit tests with synthetic fixture) |
| `tests/risk/span/test_parser_v400_regression.py` | **NEW** | Block M (integration tests against real SPAN archive) |

### 5.2 S2 synthetic fixture

The S2 synthetic fixture (`S2_FIXTURE_XML`) extends the S1 fixture by adding:
- `<pointDef><scanPointDef>` block: 16 scenario entries with `<point>`, `<pairedPoint>`, `<priceScanDef/numerator>`, `<priceScanDef/denominator>`, `<volScanDef/numerator>`, `<volScanDef/denominator>`, `<weight>`
- `<cvf>1.00</cvf>` on each `<phyPf>` portfolio element
- `<dSpread>` on NIFTY `<ccDef>` with `<spread>1</spread><rate><val>425.0</val></rate>`
- `<scanRate><priceScan>2234.01</priceScan><volScan>0.04</volScan></scanRate>` on each NIFTY `<fut>`
- `<intrRate><val>0.07</val></intrRate>` on each NIFTY `<fut>`
- `<scanRate><priceScan>1100.0</priceScan><volScan>0.02</volScan></scanRate>` on WIDGET `<fut>`
- NIFTY `<oopPf/series>` with one `<series pe="20260130">` containing `<v>0.40</v>`, `<scanRate>`, `<t>0.016438</t>`, `<intrRate>`, and 3 `<opt>` children each with `<k>`, `<o>`, `<p>`, `<d>`, `<v>`, and exactly 16 `<ra/a>` values
- WIDGET has no `<oopPf>` (same as S1)

The S2 fixture must also pass all S1 Block A–G assertions from `test_parser_v400.py` when `parse_span_xml(S2_FIXTURE_BYTES)` is called.

---

### Block H — New risk_metrics keys

**H-1 — `price_scan_range` present and correct**
- RED: key absent from risk_metrics (S1 does not emit it)
- GREEN: `snapshot.risk_arrays["NIFTY"].risk_metrics["price_scan_range"] == 2234.01`

**H-2 — `vol_scan_range` present and correct**
- GREEN: `snapshot.risk_arrays["NIFTY"].risk_metrics["vol_scan_range"] == 0.04`

**H-3 — `cvf` = 1.0 for all underlyings**
- GREEN: `snapshot.risk_arrays["NIFTY"].risk_metrics["cvf"] == 1.0`
- GREEN: `snapshot.risk_arrays["WIDGET"].risk_metrics["cvf"] == 1.0`

**H-4 — `cvf` defaults to 1.0 when `<phyPf/cvf>` absent**
- Fixture variant: phyPf with no `<cvf>` child
- GREEN: `risk_metrics["cvf"] == 1.0`

**H-5 — `intra_spread_charge_rs` correct for underlying with dSpread**
- Fixture: NIFTY `<dSpread><spread>1</spread><rate><val>425.0</val></rate></dSpread>`
- GREEN: `snapshot.risk_arrays["NIFTY"].risk_metrics["intra_spread_charge_rs"] == 425.0`

**H-6 — `intra_spread_charge_rs` = 0.0 when no dSpread**
- Fixture: WIDGET has no `<dSpread>`
- GREEN: `snapshot.risk_arrays["WIDGET"].risk_metrics["intra_spread_charge_rs"] == 0.0`

**H-7 — `intra_spread_charge_rs` selects minimum when multiple dSpread tiers**
- Fixture variant: NIFTY dSpread tiers with vals 425.0, 500.0, 600.0
- GREEN: `risk_metrics["intra_spread_charge_rs"] == 425.0`

**H-8 — `risk_free_rate` present and correct**
- Fixture: `<intrRate><val>0.07</val></intrRate>` on nearest-expiry NIFTY fut
- GREEN: `snapshot.risk_arrays["NIFTY"].risk_metrics["risk_free_rate"] == 0.07`

**H-9 — `risk_free_rate` defaults to 0.0 when absent**
- Fixture variant: nearest-expiry fut with no `<intrRate>`
- GREEN: `risk_metrics["risk_free_rate"] == 0.0`

**H-10 — All 7 metric keys always present**
- GREEN: for every entry in `snapshot.risk_arrays.values()`:
  `{"scan_risk", "short_option_minimum", "price_scan_range", "vol_scan_range", "cvf", "intra_spread_charge_rs", "risk_free_rate"} == set(ra.risk_metrics.keys())`

**H-11 — S1 keys unchanged in value**
- GREEN: `scan_risk` and `short_option_minimum` equal the S1-expected values for the same fixture
- Acceptance: S2 changes must not alter values already verified in S1 Blocks C and D

---

### Block I — Scenario grid in metadata

**I-1 — `scan_scenarios` key present in metadata**
- GREEN: `"scan_scenarios" in snapshot.metadata`

**I-2 — 16 scenario entries extracted**
- GREEN: `len(snapshot.metadata["scan_scenarios"]) == 16`

**I-3 — Scenario dict has required keys**
- GREEN: each entry has exactly the keys `point`, `paired_point`, `price_mult`, `vol_mult`, `weight`

**I-4 — Extreme scenario weights are 0.3**
- Fixture: `<scanPointDef>` entries 15 and 16 have `<weight>0.3</weight>`
- GREEN: `metadata["scan_scenarios"][14]["weight"] == 0.3`
- GREEN: `metadata["scan_scenarios"][15]["weight"] == 0.3`

**I-5 — Normal scenario weights are 1.0**
- GREEN: `metadata["scan_scenarios"][0]["weight"] == 1.0`

**I-6 — `scan_scenarios` is empty list when `<pointDef>` absent**
- Fixture variant: remove `<pointDef>` block entirely
- GREEN: `snapshot.metadata["scan_scenarios"] == []`; no exception raised

---

### Block J — SpanFutureContract

**J-1 — `futures` field present on SpanSnapshot**
- GREEN: `hasattr(snapshot, "futures")`

**J-2 — `futures` keyed by symbol**
- GREEN: `"NIFTY" in snapshot.futures`

**J-3 — Correct number of futures contracts per symbol**
- Fixture: NIFTY has 2 futures (20260130, 20260227); WIDGET has 1
- GREEN: `len(snapshot.futures["NIFTY"]) == 2`
- GREEN: `len(snapshot.futures["WIDGET"]) == 1`

**J-4 — Futures sorted nearest expiry first**
- GREEN: `snapshot.futures["NIFTY"][0].expiry < snapshot.futures["NIFTY"][1].expiry`
- GREEN: `snapshot.futures["NIFTY"][0].expiry == date(2026, 1, 30)`

**J-5 — SpanFutureContract fields populated correctly**
- GREEN: `.symbol == "NIFTY"`
- GREEN: `.expiry == date(2026, 1, 30)`
- GREEN: `.price_scan_range == 2234.01`
- GREEN: `.vol_scan_range == 0.04`
- GREEN: `.risk_free_rate == 0.07`

**J-6 — SpanFutureContract RA tuple has 16 values**
- GREEN: `len(snapshot.futures["NIFTY"][0].ra) == 16`

**J-7 — RA values match fixture**
- Fixture: NIFTY nearest fut RA[0] = -1000.0
- GREEN: `snapshot.futures["NIFTY"][0].ra[0] == -1000.0`

**J-8 — SpanFutureContract is frozen**
- GREEN: `snapshot.futures["NIFTY"][0].expiry = date(2026, 1, 1)` raises `FrozenInstanceError`

**J-9 — Symbol with no futPf has empty futures tuple**
- Fixture: ORPHAN ccDef with no matching futPf
- GREEN: `snapshot.futures.get("ORPHAN", ()) == ()`

**J-10 — Futures contract with pe="00000000" is excluded**
- Fixture variant: add `<fut><pe>00000000</pe>…</fut>` to NIFTY futPf
- GREEN: excluded; `len(snapshot.futures["NIFTY"]) == 2` (unchanged)

---

### Block K — SpanOptionSeries

**K-1 — `option_series` field present on SpanSnapshot**
- GREEN: `hasattr(snapshot, "option_series")`

**K-2 — NIFTY has the expected number of series**
- Fixture: NIFTY oopPf has one `<series pe="20260130">`
- GREEN: `len(snapshot.option_series["NIFTY"]) == 1`

**K-3 — SpanOptionSeries fields correct**
- GREEN: `snapshot.option_series["NIFTY"][0].symbol == "NIFTY"`
- GREEN: `snapshot.option_series["NIFTY"][0].expiry == date(2026, 1, 30)`
- GREEN: `snapshot.option_series["NIFTY"][0].price_scan_range == 2234.01`
- GREEN: `snapshot.option_series["NIFTY"][0].vol == pytest.approx(0.40, abs=0.001)`

**K-4 — Symbol with no oopPf has empty option_series tuple**
- Fixture: WIDGET has no `<oopPf>`
- GREEN: `snapshot.option_series.get("WIDGET", ()) == ()`

**K-5 — SpanOptionSeries is frozen**
- GREEN: `snapshot.option_series["NIFTY"][0].vol = 0.99` raises `FrozenInstanceError`

---

### Block L — SpanOptionContract

**L-1 — `option_contracts` field present on SpanSnapshot**
- GREEN: `hasattr(snapshot, "option_contracts")`

**L-2 — NIFTY option contract count matches fixture opt elements**
- Fixture: NIFTY oopPf/series has 3 `<opt>` children
- GREEN: `len(snapshot.option_contracts["NIFTY"]) == 3`

**L-3 — SpanOptionContract fields populated correctly**
- Fixture: first opt `<k>24000.00</k><o>C</o><p>260.05</p><d>0.8453</d><v>0.4029</v>` + 16 RA
- GREEN: `.symbol == "NIFTY"`
- GREEN: `.expiry == date(2026, 1, 30)`
- GREEN: `.strike == 24000.00`
- GREEN: `.option_type == "C"`
- GREEN: `.price == 260.05`
- GREEN: `.delta == pytest.approx(0.8453, abs=0.0001)`
- GREEN: `.implied_vol == pytest.approx(0.4029, abs=0.0001)`

**L-4 — SpanOptionContract RA tuple has 16 values**
- GREEN: `len(snapshot.option_contracts["NIFTY"][0].ra) == 16`

**L-5 — RA values correct for option contract**
- Fixture: known RA values; validate first and last
- GREEN: values match fixture

**L-6 — Option contract with invalid RA count raises UnsupportedSpanSchema**
- Fixture variant: one `<opt>` with 15 `<a>` elements
- GREEN: raises `UnsupportedSpanSchema`; message contains "Expected 16 RA scenarios"

**L-7 — SpanOptionContract is frozen**
- GREEN: `snapshot.option_contracts["NIFTY"][0].strike = 0.0` raises `FrozenInstanceError`

**L-8 — Implied vol absent → 0.0**
- Fixture variant: `<opt>` with no `<v>` element
- GREEN: `.implied_vol == 0.0`

**L-9 — Sum of option_contracts counts matches metadata["option_count"]**
- GREEN: `sum(len(v) for v in snapshot.option_contracts.values()) == snapshot.metadata["option_count"]`

---

### Block M — Regression against real SPAN archive

File: `tests/risk/span/test_parser_v400_regression.py`

All tests are conditionally skipped when the reference file is absent:

```python
import pathlib, pytest
SPAN_FILE = pathlib.Path(__file__).resolve().parents[3] / \
            "reference" / "span" / "nsccl.20260625.i1" / "nsccl.20260625.i01.spn"
pytestmark = pytest.mark.skipif(
    not SPAN_FILE.exists(),
    reason="Real SPAN reference file not present"
)
```

All Block M tests use a single module-level fixture:
```python
@pytest.fixture(scope="module")
def real_snapshot():
    from core.risk.span.parser_v400 import parse_span_xml
    return parse_span_xml(SPAN_FILE.read_bytes())
```

**M-1 — Real file parses without exception**
- GREEN: fixture construction above completes without raising

**M-2 — NIFTY scan_risk (reference value 2244.36)**
- GREEN: `real_snapshot.risk_arrays["NIFTY"].risk_metrics["scan_risk"] == pytest.approx(2244.36, abs=0.01)`

**M-3 — BANKNIFTY scan_risk (reference value 5513.40)**
- GREEN: `real_snapshot.risk_arrays["BANKNIFTY"].risk_metrics["scan_risk"] == pytest.approx(5513.40, abs=0.01)`

**M-4 — Underlying count is 239**
- GREEN: `real_snapshot.metadata["underlying_count"] == 239`

**M-5 — Option count is 158,713**
- GREEN: `real_snapshot.metadata["option_count"] == 158713`

**M-6 — NIFTY price_scan_range (reference 2234.01)**
- GREEN: `real_snapshot.risk_arrays["NIFTY"].risk_metrics["price_scan_range"] == pytest.approx(2234.01, abs=0.01)`

**M-7 — BANKNIFTY price_scan_range (reference 5488.30)**
- GREEN: `real_snapshot.risk_arrays["BANKNIFTY"].risk_metrics["price_scan_range"] == pytest.approx(5488.30, abs=0.01)`

**M-8 — NIFTY intra_spread_charge_rs = 425.0**
- GREEN: `real_snapshot.risk_arrays["NIFTY"].risk_metrics["intra_spread_charge_rs"] == pytest.approx(425.0, abs=0.01)`

**M-9 — BANKNIFTY intra_spread_charge_rs = 1029.0**
- GREEN: `real_snapshot.risk_arrays["BANKNIFTY"].risk_metrics["intra_spread_charge_rs"] == pytest.approx(1029.0, abs=0.01)`

**M-10 — cvf = 1.0 for all underlyings**
- GREEN: `all(ra.risk_metrics["cvf"] == 1.0 for ra in real_snapshot.risk_arrays.values())`

**M-11 — risk_free_rate = 0.07 for NIFTY**
- GREEN: `real_snapshot.risk_arrays["NIFTY"].risk_metrics["risk_free_rate"] == pytest.approx(0.07, abs=0.001)`

**M-12 — Scenario grid has 16 entries**
- GREEN: `len(real_snapshot.metadata["scan_scenarios"]) == 16`

**M-13 — NIFTY has at least one futures contract**
- GREEN: `len(real_snapshot.futures.get("NIFTY", ())) >= 1`

**M-14 — NIFTY nearest futures RA[12] matches validated reference**
- RA index 12 = scenario 13 = price −priceScan; reference value 2244.36
- GREEN: `real_snapshot.futures["NIFTY"][0].ra[12] == pytest.approx(2244.36, abs=0.01)`

**M-15 — NIFTY has at least one option series**
- GREEN: `len(real_snapshot.option_series.get("NIFTY", ())) >= 1`

**M-16 — Total option_contracts count equals metadata["option_count"]**
- GREEN: `sum(len(v) for v in real_snapshot.option_contracts.values()) == real_snapshot.metadata["option_count"]`

**M-17 — Parser is deterministic on real file**
- GREEN: `parse_span_xml(raw) == parse_span_xml(raw)` (structural equality)

---

## 6. Definition of Done

```
✓ Three new frozen DTOs in span_snapshot.py: SpanFutureContract, SpanOptionSeries, SpanOptionContract
✓ SpanSnapshot has 3 new fields with default_factory=dict: futures, option_series, option_contracts
✓ SpanRiskArray.risk_metrics emits exactly 7 keys for every underlying:
    scan_risk, short_option_minimum, price_scan_range, vol_scan_range,
    cvf, intra_spread_charge_rs, risk_free_rate
✓ metadata["scan_scenarios"] always present (empty list if <pointDef> absent)
✓ All 3 new DTOs exported from core.risk.span.__init__
✓ Blocks H–L (test_parser_v400_s2.py): all RED before production changes, all GREEN after
✓ Block M (test_parser_v400_regression.py): all GREEN on real NSE SPAN file
✓ NIFTY scan_risk = 2244.36, BANKNIFTY scan_risk = 5513.40 confirmed from real file
✓ NIFTY intra_spread_charge_rs = 425.0, BANKNIFTY = 1029.0 confirmed from real file
✓ Zero regressions: full tests/risk/span/ suite passes; S1 test count unchanged
✓ SpanMarginCalculator and all its tests pass without modification
✓ No forbidden import in parser_v400.py (test F-6 continues to pass)
✓ SpanSnapshot constructed without new fields (S1 style) still works
✓ Parser deterministic: two calls with same bytes → equal SpanSnapshot (M-17)
```

---

## 7. Files to Modify

| File | Change type | Summary |
|------|-------------|---------|
| `core/risk/span/span_snapshot.py` | Additive | 3 new frozen DTOs; 3 new SpanSnapshot fields with `field(default_factory=dict)` |
| `core/risk/span/parser_v400.py` | Additive + refactor | New extractions; refactor `_derive_scan_risk` → `_extract_ra_tuple` + `_derive_scan_risk`; add `_safe_float`, `_extract_scan_scenarios`, `_extract_future_contracts`, `_extract_option_data` |
| `core/risk/span/__init__.py` | Additive | Export 3 new DTOs |

**New files:**

| File | Purpose |
|------|---------|
| `tests/risk/span/test_parser_v400_s2.py` | S2 Blocks H–L unit tests with S2 synthetic fixture |
| `tests/risk/span/test_parser_v400_regression.py` | Block M integration tests against real SPAN archive |

---

## 8. Files That Must NOT Change

| File | Reason |
|------|--------|
| `core/risk/span/span_parser.py` | Complete as of S1; no changes needed |
| `core/risk/span/span_calculator.py` | Calculator changes are MM9.5-S3 / MM10 scope |
| `core/risk/span/span_repository.py` | Storage layer not in S2 scope |
| `core/risk/span/span_readiness.py` | Not in scope |
| `core/risk/span/span_freshness.py` | Not in scope |
| `tests/risk/span/test_parser_v400.py` | S1 test suite must remain intact and passing |
| `tests/risk/span/test_span_parser.py` | Must remain intact and passing |
| `tests/risk/span/test_span_snapshot.py` | Must remain intact and passing |
| `tests/risk/span/test_span_calculator.py` | Must remain intact and passing |
| `tests/risk/span/test_span_composition.py` | Must remain intact and passing |
| `tests/risk/span/test_span_repository.py` | Must remain intact and passing |
| `tests/risk/span/test_span_readiness.py` | Must remain intact and passing |
| Any file outside `core/risk/span/` and `tests/risk/span/` | Full prohibition |

---

## 9. Risks

| ID | Risk | Likelihood | Mitigation |
|----|------|-----------|------------|
| R-1 | `SpanSnapshot.__eq__` breaks because two independently parsed snapshots are compared and one has empty new fields | LOW | Both will have `futures={}`, `option_series={}`, `option_contracts={}` by default → equal. Two fully parsed snapshots compare equal field-by-field if RA values are identical (deterministic test M-17). |
| R-2 | 158,713 option contracts × 16 RA values each ≈ 40–50 MB in memory per snapshot may exceed CI RAM limits | MEDIUM | Block M tests marked `pytest.mark.slow`; CI can exclude with `-m "not slow"`. Unit tests (H–L) use small fixtures only. |
| R-3 | `<pointDef>` XPath may differ between SPAN file variants | LOW | If `findall` returns empty, `scan_scenarios = []`. Not a fatal error. Regression test M-12 validates the path on the real file. |
| R-4 | Multiple `<dSpread>` tiers: minimum charge may not be the "adjacent-month" credit | MEDIUM | Minimum is always the most conservative credit value. Real NIFTY=425 and BANKNIFTY=1029 are known and validated in M-8/M-9. |
| R-5 | `_extract_ra_tuple` raises on a malformed option contract RA, aborting the entire parse | LOW | Any option contract with ≠16 RA values indicates a corrupt SPAN file; raising is correct. Real file verified clean in M-1. |
| R-6 | `field(default_factory=dict)` requires `from dataclasses import dataclass, field` — `field` may not be currently imported | LOW | Verify imports at the top of `span_snapshot.py` before modifying; add `field` to the import if absent. |

---

## 10. Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC-S2-1 | `SpanFutureContract`, `SpanOptionSeries`, `SpanOptionContract` importable from `core.risk.span` |
| AC-S2-2 | `SpanSnapshot.futures`, `.option_series`, `.option_contracts` exist with `default_factory=dict` |
| AC-S2-3 | `SpanRiskArray.risk_metrics` always emits exactly 7 keys; no key ever absent for any underlying |
| AC-S2-4 | `metadata["scan_scenarios"]` always present; `[]` if `<pointDef>` absent |
| AC-S2-5 | NIFTY `scan_risk == 2244.36` and BANKNIFTY `scan_risk == 5513.40` on real SPAN file (M-2, M-3) |
| AC-S2-6 | NIFTY `intra_spread_charge_rs == 425.0` and BANKNIFTY `== 1029.0` on real file (M-8, M-9) |
| AC-S2-7 | NIFTY `price_scan_range == 2234.01`, BANKNIFTY `== 5488.30` on real file (M-6, M-7) |
| AC-S2-8 | `sum(len(v) for v in snapshot.option_contracts.values()) == 158713` on real file (M-16) |
| AC-S2-9 | Blocks H–M: all RED before production changes; all GREEN after |
| AC-S2-10 | Zero regressions: all pre-existing `tests/risk/span/` tests pass; no test count decreases |
| AC-S2-11 | `SpanMarginCalculator` and all its tests pass unchanged |
| AC-S2-12 | No forbidden imports in `parser_v400.py` (test F-6 continues to pass) |
| AC-S2-13 | `SpanSnapshot(snapshot_date=…, schema_version=…, exchange=…, segment=…, file_hash=…, is_settlement=False, risk_arrays={}, metadata={})` still constructs without error |

---

## 11. Out-of-Scope — Explicit Prohibition

The following are **forbidden in S2**. Any introduction requires a full revert:

- `SpanMarginCalculator` — formula unchanged; per-contract margin is MM10+ scope
- Calculator adoption of new metric keys (`price_scan_range`, `cvf`, spread credits) — MM10+
- Delta scenarios (`<deltaPointDef>`) — used only for spread credits; deferred to MM10+
- Spread credit logic (applying `intra_spread_charge_rs` to net positions) — MM10+
- `SpanRepository` changes (storage of new DTOs) — separate slice
- `SpanReadinessVerdict` — not in scope
- Startup gate changes — not in scope
- Performance optimisation (lazy loading, streaming) — not in S2
- `fno_runner.py` or any file outside `core/risk/span/` and `tests/risk/span/`
- Any UI, Flask, broker, or instrument-master change
- Any new ADR — ADR-007/008/009/010 fully govern this change

---

## 12. Rollback Strategy

S2 is **purely additive** at the `SpanSnapshot` level. Safe rollback because:

1. All new `SpanSnapshot` fields have `default_factory=dict`; any caller that does not supply them gets `{}`.
2. `SpanRiskArray.risk_metrics` uses a free-form dict; removing the 5 new keys leaves `scan_risk` and `short_option_minimum` intact and the calculator unaffected.
3. `parser_v400.py` changes are isolated to new extraction helpers; the S1 computation path (`_derive_scan_risk` → `scan_risk`) is unchanged in semantics and result.
4. New test files can be deleted without touching any S1 test.

**Rollback procedure:** `git revert <S2-commit>`. The full S1 test suite must pass after revert. The `SpanMarginCalculator` tests must also pass after revert.

---

*Ref: `docs/reports/SPAN_XML_SCHEMA_AND_MM9_MAPPING.md` (XML schema, gap analysis G-1 through G-8); `docs/reports/MM9_5_S1_IMPLEMENTATION_SPEC.md` (S1 scope); `reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn` (57.2 MB real SPAN file); `core/risk/span/span_calculator.py` (MM9.4-S3; must not change); ADR-007/008/009/010.*
