# MM9.5-S1 — ParserV400 & SpanSnapshot Integration
## Implementation Specification

**Date:** 2026-06-29
**Milestone:** MM9.5-S1
**Status:** SPECIFICATION — no production code written
**Evidence base:** `docs/reports/SPAN_XML_SCHEMA_AND_MM9_MAPPING.md` · `docs/reports/MM9_5_ARCHITECTURE_RECONCILIATION.md` · ADR-008/009/010
**Governing ADRs:** ADR-007 (MarginCalculator Seam) · ADR-008 (scan_risk unit) · ADR-009 (bytes contract) · ADR-010 (version key policy)

---

## 1. Architecture Summary

### 1.1 Change surface

S1 is intentionally narrow. Every production change listed below is required; nothing beyond it is permitted.

| File | Change type | Description |
|------|-------------|-------------|
| `core/risk/span/span_snapshot.py` | Additive | Add `is_settlement: bool` field to `SpanSnapshot` |
| `core/risk/span/span_parser.py` | Corrective | Fix registry type; delete `parse_span_csv`; change key "v1"→"4.00" |
| `core/risk/span/parser_v400.py` | New file | `parse_span_xml(raw: bytes) → SpanSnapshot` + internal helpers |
| `core/risk/span/__init__.py` | Additive | Export `parse_span_xml` |
| `tests/risk/span/test_parser_v400.py` | New file | Full TDD test suite (Blocks A–F) |
| `tests/risk/span/test_span_parser.py` | Corrective | Update version key "v1"→"4.00" in existing tests |

### 1.2 Nothing else changes

Forbidden in S1: `span_calculator.py`, `span_repository.py`, `span_readiness.py`, `span_freshness.py`, `span_pipeline.py`, `core/execution/`, `core/runtime/`, `fno_runner.py`, any test outside `tests/risk/span/`. The calculator formula correction is MM9.5-S2. No runtime wiring. No new ADRs.

### 1.3 Data flow

```
raw bytes
  ↓
parse_span_xml(raw: bytes)          ← ADR-009: bytes-in, SpanSnapshot-out
  ↓
  ├── decode(latin-1)
  ├── ElementTree.fromstring(text)
  ├── extract metadata             → SpanSnapshot.metadata
  ├── extract snapshot_date        → SpanSnapshot.snapshot_date
  ├── extract is_settlement        → SpanSnapshot.is_settlement
  ├── for each <ccDef>:
  │     ├── extract symbol (cc)
  │     ├── extract SOM (somTiers/rate/val)
  │     ├── find matching <futPf> by pfCode
  │     ├── select nearest-expiry <fut> by <pe>
  │     ├── extract 16 <ra/a> values
  │     └── reduce → scan_risk (Rs/lot-unit)
  └── build SpanSnapshot
        └── risk_arrays: Dict[str, SpanRiskArray]    ← keyed by <ccDef/cc>
```

---

## 2. Production Edits

### 2.1 `core/risk/span/span_snapshot.py` — Add `is_settlement`

**Change:** Insert `is_settlement: bool` as a field of the `SpanSnapshot` frozen dataclass.

**Complete `SpanSnapshot` field specification after the change:**

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `snapshot_date` | `date` | `<pointInTime/date>` text, YYYYMMDD | Parse with `datetime.strptime(s, "%Y%m%d").date()` |
| `schema_version` | `str` | `<fileFormat>` text content | "4.00" verbatim — ADR-010 |
| `exchange` | `str` | `<clearingOrg/exchange/exch>` text | "NSE" |
| `segment` | `str` | Not in XML | Hardcode `"FO"` |
| `file_hash` | `str` | `hashlib.sha256(raw).hexdigest()` | Computed from raw bytes before decode |
| `is_settlement` | `bool` | `<pointInTime/isSetl>` text | `"0"` → False (intraday), `"1"` → True (EOD settlement) |
| `risk_arrays` | `Dict[str, SpanRiskArray]` | One entry per `<ccDef>` | Keyed by `<ccDef/cc>` verbatim |
| `metadata` | `Dict[str, Any]` | See §2.1.1 | Auxiliary provenance |

**`is_settlement` semantics:** The NSE file naming convention uses `i01`, `i02`, … for intraday snapshots and a distinct name for the EOD settlement file. The `<isSetl>` element encodes this. The startup gate (ADR-007/MM9.4-S4) may later prefer `is_settlement=True` snapshots for next-day session — having it as a first-class field enables that check without a metadata dict access.

**`SpanRiskArray` — unchanged:** `symbol: str`, `risk_metrics: Dict[str, float]`. The two mandatory keys in `risk_metrics` remain `"scan_risk"` and `"short_option_minimum"`.

**§2.1.1 Required metadata keys:**

```python
metadata = {
    "created": str,           # raw <created> text, e.g. "202606242149" (YYYYMMDDHHmm IST)
    "clearing_org": str,      # <clearingOrg/ec> text, e.g. "NSCCL"
    "underlying_count": int,  # count of <ccDef> elements parsed
    "futures_contract_count": int,  # total <fut> elements across all futPf
    "option_count": int,      # total <opt> elements across all oopPf
}
```

No other metadata keys are required for S1. Additional keys may be added but must not be consumed by any production code in S1.

---

### 2.2 `core/risk/span/span_parser.py` — Three targeted fixes

**Fix 1 — Registry type annotation:**

Change the type stored in `ParserRegistry._parsers` from:
```
Dict[str, Callable[[dict], SpanSnapshot]]
```
to:
```
Dict[str, Callable[[bytes], SpanSnapshot]]
```

The `parse` method signature must accept `raw: bytes` (not `raw_data: dict`). All internal type annotations must be updated consistently.

**Fix 2 — Delete `parse_span_csv`:**

The function `parse_span_csv(schema_version: str, raw_data: dict)` is deleted entirely. It was never registered for production. No alias, no deprecation comment, no backward-compat shim.

**Fix 3 — Change the registered version key:**

Any location in `span_parser.py` that registers a parser or uses the string `"v1"` as a version key must change to `"4.00"`. Per ADR-010, the key must match `<fileFormat>` verbatim. All tests in `test_span_parser.py` that reference the key `"v1"` must be updated in the same commit.

The `UnsupportedSpanSchema` exception behaviour and the default global registry instance are correct and unchanged.

---

### 2.3 `core/risk/span/parser_v400.py` — New file

**Module purpose:** Owns the complete transformation from raw PC-SPAN 4.00 XML bytes to a populated `SpanSnapshot`. No caller performs any pre-processing; no caller inspects the XML.

**Public API (one exported name):**

```python
def parse_span_xml(raw: bytes) -> SpanSnapshot:
    ...
```

- **Input:** `raw` — verbatim binary content of the `.spn` file (latin-1 encoded XML, possibly with CRLF line endings). May be the direct contents of the `.spn` file or the primary entry after ZIP extraction at the caller's discretion.
- **Output:** a fully-populated, frozen `SpanSnapshot`.
- **Side effects:** none. No I/O, no logging, no global state mutation.

**Internal structure:** All helpers are module-private (underscore-prefixed). No public classes. The function may delegate to an internal `_ParserV400` class or module-level functions — implementation choice — but only `parse_span_xml` is exported.

**Required imports:** `hashlib`, `datetime.date`, `datetime.datetime`, `xml.etree.ElementTree`, `typing`, `SpanSnapshot`, `SpanRiskArray`, `UnsupportedSpanSchema`.

**Forbidden imports:** `SpanRepository`, `SpanMarginCalculator`, `SpanReadinessVerdict`, `ExecutionHandler`, `LoopDriver`, any `core/execution` or `core/runtime` module.

---

### 2.4 XML Extraction Specification

All XPath expressions use Python `xml.etree.ElementTree` findtext/findall conventions.

#### 2.4.1 Document root and preamble

```
root = ET.fromstring(decoded_text)     # root tag: <spanFile>

schema_version  = root.findtext("fileFormat")                       # "4.00"
created_ts      = root.findtext("created")                          # "202606242149"
snapshot_date_s = root.findtext("pointInTime/date")                 # "20260625"
is_setl_s       = root.findtext("pointInTime/isSetl")               # "0" or "1"
clearing_org    = root.findtext("pointInTime/clearingOrg/ec")       # "NSCCL"
exchange_code   = root.findtext("pointInTime/clearingOrg/exchange/exch")  # "NSE"
```

#### 2.4.2 Structural indices built once before the ccDef loop

```python
# Index futPf elements by their <pfCode> (equals the <cc> value of the matching ccDef)
fut_pfs: Dict[str, Element] = {
    fp.findtext("pfCode"): fp
    for fp in root.findall("pointInTime/clearingOrg/exchange/futPf")
}

# Index oopPf elements for option counting only
oop_pfs: List[Element] = root.findall("pointInTime/clearingOrg/exchange/oopPf")
```

#### 2.4.3 ccDef loop

For each `<ccDef>` element in `root.findall("pointInTime/clearingOrg/ccDef")`:

```
symbol  = ccDef.findtext("cc")                      # e.g. "NIFTY"
som_val = ccDef.findtext("somTiers/rate/val", "0")  # "0" for index underlyings
short_option_minimum = float(som_val)
```

If `som_val` is missing or empty, default to `0.0` (do not raise).

#### 2.4.4 Nearest-expiry futures selection

```python
fut_pf = fut_pfs.get(symbol)
if fut_pf is None:
    # No futures portfolio for this underlying (e.g. a currency or commodity ccDef)
    # Emit scan_risk=0.0 for completeness; do not raise
    scan_risk = 0.0
else:
    futs = fut_pf.findall("fut")
    # Select nearest expiry: minimum <pe> value (YYYYMMDD string sort = date sort)
    # Exclude pe="00000000" (physical/no-expiry placeholder, never in futPf but guard anyway)
    eligible = [f for f in futs if f.findtext("pe", "00000000") != "00000000"]
    if not eligible:
        scan_risk = 0.0
    else:
        nearest = min(eligible, key=lambda f: f.findtext("pe"))
        scan_risk = _derive_scan_risk(nearest)
```

**Rationale for `0.0` fallback:** Some `<ccDef>` entries in the file may represent underlyings with no F&O contracts on the NSE segment. Emitting `scan_risk=0.0` for these is correct — no F&O position can exist on them in this platform. Do not raise.

#### 2.4.5 Scan risk derivation — `_derive_scan_risk(fut_element)`

```python
SCENARIO_WEIGHTS = [1.0] * 14 + [0.3, 0.3]   # 16 weights; pts 15,16 at 0.3

def _derive_scan_risk(fut: Element) -> float:
    a_elements = fut.findall("ra/a")
    if len(a_elements) != 16:
        raise UnsupportedSpanSchema(
            f"Expected 16 RA scenarios, got {len(a_elements)}"
        )
    ra_values = [float(a.text) for a in a_elements]

    # RA sign convention (PC-SPAN 4.00):
    #   positive RA value = profit for a unit long position
    #   negative RA value = loss for a unit long position
    # scan_risk = worst-case weighted loss across all 16 scenarios.
    weighted_losses = [-ra * w for ra, w in zip(ra_values, SCENARIO_WEIGHTS)]
    return max(weighted_losses)
```

**Verified result:** NIFTY Jun-26 nearest-expiry futures → `scan_risk = 2244.36` Rs/lot-unit (scenario 13, price −priceScan). BANKNIFTY Jun-26 → `scan_risk = 5513.40` Rs/lot-unit.

**Sign convention note:** Raw `<a>` text values use the convention positive = gain for long, negative = loss. Negating converts to loss perspective; `max` selects the worst case.

#### 2.4.6 SpanRiskArray construction

```python
SpanRiskArray(
    symbol=symbol,
    risk_metrics={
        "scan_risk": scan_risk,                       # ADR-008: Rs per lot-unit
        "short_option_minimum": short_option_minimum, # Rs per lot-unit; 0.0 for index
    },
)
```

Both keys are always emitted — never omitted.

#### 2.4.7 SpanSnapshot construction

```python
SpanSnapshot(
    snapshot_date=datetime.strptime(snapshot_date_s, "%Y%m%d").date(),
    schema_version=schema_version,          # "4.00"  — ADR-010
    exchange=exchange_code,                  # "NSE"
    segment="FO",                            # hardcoded; not present in XML
    file_hash=hashlib.sha256(raw).hexdigest(),  # of raw bytes before decode
    is_settlement=(is_setl_s == "1"),
    risk_arrays=risk_arrays,                 # Dict[str, SpanRiskArray]
    metadata={
        "created": created_ts,
        "clearing_org": clearing_org,
        "underlying_count": len(risk_arrays),
        "futures_contract_count": futures_count,
        "option_count": option_count,
    },
)
```

---

### 2.5 Failure Behaviour

All failures raise `UnsupportedSpanSchema`. No other exception type is permitted to escape `parse_span_xml`.

| Condition | Raise message |
|-----------|--------------|
| Bytes cannot be decoded as latin-1 | `"Cannot decode SPAN file as latin-1: {e}"` |
| `ET.fromstring` raises `ParseError` | `"Malformed SPAN XML: {e}"` |
| `root.findtext("fileFormat")` is None or empty | `"Missing <fileFormat> in SPAN file"` |
| `fileFormat` ≠ `"4.00"` | `"Parser v4.00 received fileFormat '{version}'"` |
| `snapshot_date_s` is None or cannot be parsed | `"Missing or invalid <pointInTime/date>: '{val}'"` |
| `<ra/a>` count ≠ 16 for a selected futures contract | `"Expected 16 RA scenarios, got {n}"` |
| `float(a.text)` raises ValueError on any RA value | `"Invalid RA value '{val}' in <ra/a>: {e}"` |

**Not an error:** zero `<ccDef>` elements found. The snapshot is valid with an empty `risk_arrays` dict.

---

### 2.6 ParserRegistry Wiring

In `span_parser.py`, after the `ParserRegistry` class definition, register the production parser:

```python
from core.risk.span.parser_v400 import parse_span_xml

registry = ParserRegistry()
registry.register("4.00", parse_span_xml)   # ADR-010: key = <fileFormat> verbatim
```

The `ParserRegistry.parse(schema_version, raw)` method signature becomes:

```python
def parse(self, schema_version: str, raw: bytes) -> SpanSnapshot: ...
```

---

### 2.7 `core/risk/span/__init__.py` — Export addition

Add `parse_span_xml` to `__all__` and to the module-level imports:

```python
from core.risk.span.parser_v400 import parse_span_xml
```

---

## 3. Options Extraction — S1 Scope

Options (`<oopPf>`) are parsed for **counting only** in S1. No per-strike RA reduction is performed. No `scan_risk` is computed for individual options. The option count is placed in `SpanSnapshot.metadata["option_count"]`.

**Counting algorithm:**
```python
option_count = sum(
    len(oop.findall("series/opt"))
    for oop in oop_pfs
)
```

Per-strike option RA values are NOT stored in S1. A position in a NIFTY option will use `risk_arrays["NIFTY"].risk_metrics["scan_risk"]` as a conservative proxy. This is a known limitation, documented in ADR-008 and this specification. No TODOs, no stubs, no scaffolding for the deferred path.

---

## 4. Test Plan

All tests live in `tests/risk/span/test_parser_v400.py`. Tests use a synthetic XML fixture — a minimal but structurally correct PC-SPAN 4.00 XML string, embedded as a module-level constant and encoded to bytes.

**Fixture design:** Two `<ccDef>` entries — "NIFTY" (index, SOM=0, two futures contracts with different expiries) and "WIDGET" (synthetic stock with SOM=15.0, one futures contract). NIFTY nearest-expiry RA values are chosen so that the expected `scan_risk` is a known integer (e.g., 1000.0) for easy assertion.

**Fixture file_hash** is computed in tests as `hashlib.sha256(FIXTURE_BYTES).hexdigest()` and asserted against `snapshot.file_hash`.

---

### Block A — Registry and dispatch

**A-1 — `parse_span_xml` is registered under "4.00"**
- RED: `registry._parsers.get("4.00")` is None (before the fix)
- GREEN: `registry._parsers["4.00"]` is `parse_span_xml`
- Acceptance: the callable stored under "4.00" is exactly the `parse_span_xml` function

**A-2 — `"v1"` key is absent from the registry**
- RED: `"v1"` is present (old behaviour)
- GREEN: `registry._parsers.get("v1")` is None
- Acceptance: no "v1" key in the registry after the fix

**A-3 — `registry.parse("4.00", fixture_bytes)` returns a `SpanSnapshot`**
- RED: `TypeError` — wrong signature (old `dict` contract)
- GREEN: returns a `SpanSnapshot` instance
- Acceptance: `isinstance(result, SpanSnapshot)` is True

**A-4 — Unknown version raises `UnsupportedSpanSchema`**
- RED: may raise `KeyError` (old behaviour)
- GREEN: `registry.parse("9.99", fixture_bytes)` raises `UnsupportedSpanSchema`
- Acceptance: message contains the unsupported version string

**A-5 — `parse_span_csv` is gone**
- RED: `from core.risk.span.span_parser import parse_span_csv` succeeds (old behaviour)
- GREEN: `ImportError` on that import
- Acceptance: the name does not exist in the module

---

### Block B — Metadata extraction

**B-1 — `snapshot_date` is correct**
- Fixture: `<pointInTime/date>` = "20260101"
- GREEN: `snapshot.snapshot_date == date(2026, 1, 1)`

**B-2 — `schema_version` is "4.00"**
- GREEN: `snapshot.schema_version == "4.00"`

**B-3 — `exchange` is "NSE"**
- GREEN: `snapshot.exchange == "NSE"`

**B-4 — `segment` is "FO"**
- GREEN: `snapshot.segment == "FO"`

**B-5 — `file_hash` is SHA-256 hex of raw bytes**
- GREEN: `snapshot.file_hash == hashlib.sha256(FIXTURE_BYTES).hexdigest()`

**B-6 — `is_settlement` = False for intraday (`<isSetl>` = "0")**
- Fixture: `<isSetl>0</isSetl>`
- GREEN: `snapshot.is_settlement is False`

**B-7 — `is_settlement` = True for settlement (`<isSetl>` = "1")**
- Fixture variant: `<isSetl>1</isSetl>`
- GREEN: `snapshot.is_settlement is True`

**B-8 — `metadata["clearing_org"]` is "NSCCL"**
- GREEN: `snapshot.metadata["clearing_org"] == "NSCCL"`

**B-9 — `metadata["created"]` is the raw created string**
- Fixture: `<created>202601010900</created>`
- GREEN: `snapshot.metadata["created"] == "202601010900"`

**B-10 — `metadata["underlying_count"]` equals number of ccDef entries**
- Fixture has 2 ccDef entries
- GREEN: `snapshot.metadata["underlying_count"] == 2`

**B-11 — `SpanSnapshot` is frozen (immutable)**
- GREEN: `snapshot.risk_arrays = {}` raises `FrozenInstanceError`

---

### Block C — Futures extraction

**C-1 — Both underlyings appear in `risk_arrays`**
- GREEN: `"NIFTY" in snapshot.risk_arrays and "WIDGET" in snapshot.risk_arrays`

**C-2 — `scan_risk` is derived from nearest-expiry futures RA**
- Fixture: NIFTY has two futures contracts — expiry "20260130" and "20260227"
  - "20260130" is nearest; its RA produces `max(-ra * w) = 1000.0`
  - "20260227" RA produces `max = 800.0`
- GREEN: `snapshot.risk_arrays["NIFTY"].risk_metrics["scan_risk"] == 1000.0`
- Acceptance: the nearer expiry is selected, not the farther

**C-3 — Single-contract underlying selects that contract**
- Fixture: WIDGET has one futures contract
- GREEN: `scan_risk` equals the expected value derived from WIDGET's single RA

**C-4 — RA weights 0.3 applied to scenarios 15 and 16**
- Fixture RA: scenario 15 raw = −900.0 (unweighted loss 900); scenario 16 raw = −2000.0 (weighted loss 0.3×2000=600); scenario 1 raw = −1100.0 (weighted loss 1100)
- GREEN: `scan_risk == 1100.0` (not 2000.0 and not 900.0)
- Acceptance: confirms weight application

**C-5 — SOM=0 for index underlying**
- GREEN: `snapshot.risk_arrays["NIFTY"].risk_metrics["short_option_minimum"] == 0.0`

**C-6 — SOM > 0 for stock underlying**
- Fixture: WIDGET `<somTiers><rate><val>15.0</val></rate></somTiers>`
- GREEN: `snapshot.risk_arrays["WIDGET"].risk_metrics["short_option_minimum"] == 15.0`

**C-7 — Both `"scan_risk"` and `"short_option_minimum"` always present**
- GREEN: both keys present for every entry in `snapshot.risk_arrays`

**C-8 — `SpanRiskArray.symbol` matches `<ccDef/cc>`**
- GREEN: `snapshot.risk_arrays["NIFTY"].symbol == "NIFTY"`

**C-9 — All-gain RA produces scan_risk = 0.0**
- Fixture RA: all 16 values are positive floats (all profits for long)
- GREEN: `_derive_scan_risk(element)` returns 0.0

**C-10 — `futures_contract_count` in metadata**
- Fixture: NIFTY has 2 futures, WIDGET has 1
- GREEN: `snapshot.metadata["futures_contract_count"] == 3`

---

### Block D — Options extraction

**D-1 — `option_count` in metadata**
- Fixture: NIFTY oopPf has 10 opt elements; WIDGET oopPf absent
- GREEN: `snapshot.metadata["option_count"] == 10`

**D-2 — Options do NOT appear as separate entries in `risk_arrays`**
- GREEN: `len(snapshot.risk_arrays) == 2` (only NIFTY and WIDGET)

**D-3 — Absent oopPf does not raise**
- Fixture: WIDGET has no `<oopPf>`
- GREEN: parsing completes; WIDGET appears in `risk_arrays`

---

### Block E — Error handling

**E-1 — Non-latin-1 bytes raise `UnsupportedSpanSchema`**
- GREEN: raises with "Cannot decode" in message

**E-2 — Malformed XML raises `UnsupportedSpanSchema`**
- Input: `b"this is not xml"`
- GREEN: raises with "Malformed SPAN XML" in message

**E-3 — Missing `<fileFormat>` raises `UnsupportedSpanSchema`**
- GREEN: raises with "Missing <fileFormat>" in message

**E-4 — Wrong fileFormat value raises `UnsupportedSpanSchema`**
- Fixture variant: `<fileFormat>5.00</fileFormat>`
- GREEN: raises with the bad version in message

**E-5 — Missing `<pointInTime/date>` raises `UnsupportedSpanSchema`**
- GREEN: raises with "Missing or invalid" in message

**E-6 — RA with fewer than 16 `<a>` elements raises `UnsupportedSpanSchema`**
- Fixture variant: 15 `<a>` elements
- GREEN: raises with "Expected 16 RA scenarios, got 15"

**E-7 — Non-numeric RA value raises `UnsupportedSpanSchema`**
- Fixture variant: one `<a>` has text "N/A"
- GREEN: raises with "Invalid RA value"

**E-8 — ccDef with no matching futPf → scan_risk=0.0, no raise**
- Fixture: third ccDef "ORPHAN" with no futPf pfCode match
- GREEN: `snapshot.risk_arrays["ORPHAN"].risk_metrics["scan_risk"] == 0.0`

**E-9 — futPf with no `<fut>` children → scan_risk=0.0**
- Fixture: empty `<futPf>` for WIDGET
- GREEN: `snapshot.risk_arrays["WIDGET"].risk_metrics["scan_risk"] == 0.0`

---

### Block F — Regression

**F-1 — Six original `SpanSnapshot` fields are unchanged**
- GREEN: `snapshot_date`, `schema_version`, `exchange`, `segment`, `file_hash`, `risk_arrays`, `metadata` all accessible by existing names

**F-2 — `is_settlement` field is frozen**
- GREEN: `snapshot.is_settlement = True` raises `FrozenInstanceError`

**F-3 — `SpanRiskArray` is unchanged**
- GREEN: existing `SpanRiskArray` construction still works

**F-4 — `ParserRegistry.parse` passes bytes to registered callable**
- GREEN: a test-double parser registered under "4.00" receives the exact bytes passed in

**F-5 — Unknown version raises `UnsupportedSpanSchema` via registry**
- GREEN: `registry.parse("3.00", b"...")` raises `UnsupportedSpanSchema`

**F-6 — No import of execution or runtime modules in `parser_v400.py`**
- GREEN: AST inspection of `parser_v400.py` confirms no import of `core.execution`, `core.runtime`, `SpanMarginCalculator`, `SpanRepository`, `LoopDriver`, `ExecutionHandler`

**F-7 — `parse_span_xml` is deterministic**
- GREEN: two calls with identical bytes return structurally equal `SpanSnapshot` instances

**F-8 — Full existing `tests/risk/span/` suite passes at zero regressions**
- GREEN: `test_span_snapshot.py`, `test_span_repository.py`, `test_span_readiness.py`, `test_span_freshness.py`, `test_span_calculator.py`, `test_span_composition.py` all pass after the changes

---

## 5. Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC-1 | `parse_span_xml(raw: bytes)` exists in `core/risk/span/parser_v400.py` and is importable from `core.risk.span` |
| AC-2 | `ParserRegistry` is keyed on `"4.00"`; `"v1"` is absent; `parse_span_csv` is deleted |
| AC-3 | `SpanSnapshot.is_settlement: bool` exists and is a frozen dataclass field |
| AC-4 | Parsing the synthetic fixture produces a `SpanSnapshot` with the expected `scan_risk` values |
| AC-5 | Both `"scan_risk"` and `"short_option_minimum"` always present in every `SpanRiskArray.risk_metrics` |
| AC-6 | Nearest-expiry futures selection uses minimum `<pe>` date |
| AC-7 | RA reduction applies weights `[1.0]*14 + [0.3, 0.3]` and takes `max(-ra * w)` |
| AC-8 | All Block E error conditions raise `UnsupportedSpanSchema` and nothing else escapes |
| AC-9 | No import of any execution/runtime module in `parser_v400.py` |
| AC-10 | All new tests are RED before production changes, GREEN after |
| AC-11 | Zero regression: full `tests/risk/span/` suite passes; test count does not decrease |
| AC-12 | No changes outside `core/risk/span/` and `tests/risk/span/` |

---

## 6. Definition of Done

```
✓ ParserV400 parses the real NSE XML file to a SpanSnapshot
✓ SpanSnapshot.is_settlement is populated correctly (False for i01 intraday file)
✓ risk_arrays keyed by <ccDef/cc> for all 239 underlyings
✓ Nearest-expiry futures RA reduction produces 2244.36 for NIFTY, 5513.40 for BANKNIFTY
  (verified against reference/span/nsccl.20260625.i01.spn as manual smoke test)
✓ Unknown schema versions raise UnsupportedSpanSchema
✓ All Block A–F tests pass (≥ 30 new tests)
✓ Zero regressions in full test suite
✓ No runtime behaviour change (calculator, handler, driver untouched)
✓ ADR-009 contract enforced: parse_span_xml signature is (raw: bytes) -> SpanSnapshot
✓ ADR-010 contract enforced: registry key is "4.00"
```

---

## 7. Out of Scope — Explicit Prohibition

The following are **forbidden in S1**. Introducing any of these exceeds scope and requires a revert:

- `SpanMarginCalculator` — formula correction is S2
- `MarginCalculator` protocol — no changes
- `ExecutionHandler` — no changes
- `LoopDriver` — no changes
- `PortfolioView` — no changes
- `fno_runner.py` — no changes
- `SpanRepository` — no changes
- `SpanReadinessVerdict` — no changes
- Startup gate — no changes
- Telemetry — no changes
- ZMQ — no changes
- Buying-power logic — no changes
- Per-contract option scan_risk — MM10+
- Inter-month spread credits (`<dSpread>`) — MM10+
- Interest rate parameters (`<intrRate>`) — deferred
- Delta scenarios (`<deltaPointDef>`) — deferred
- Performance-optimising the XML parse — deferred
- Repository redesign of any kind
- Any file outside `core/risk/span/` and `tests/risk/span/`

---

*Ref: `docs/reports/SPAN_XML_SCHEMA_AND_MM9_MAPPING.md` (XML paths, RA table, gap analysis G-1/G-2/G-5); `docs/reports/MM9_5_ARCHITECTURE_RECONCILIATION.md` (§1.1/§1.2/§1.3/§2 D1); `reference/span/nsccl.20260625.i01.spn` (source file); ADR-007/008/009/010.*
