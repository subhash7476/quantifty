# MM9.5 Architecture Reconciliation Report
## Real NSE SPAN Integration — System Architect Review

**Date:** 2026-06-29  
**Author role:** System Architect  
**Scope:** Reconcile MM9.4 architecture with the real NSE SPAN XML schema (PC-SPAN fileFormat 4.00)  
**Evidence base:**  
- `reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn` — real NSE file, reverse-engineered  
- `docs/reports/SPAN_XML_SCHEMA_AND_MM9_MAPPING.md` — complete XML schema and gap analysis  
- All MM9.4 slice specifications (S1–S4)  
- As-built source: `core/risk/span/` (all modules)

**Governing constraints:**  
ADR-001 (Ledger Is Truth) · ADR-003 (Deterministic Processing) · ADR-006 (Sole Orchestrator) · ADR-007 (MarginCalculator Seam)

---

## Executive Summary

MM9.4's architecture is fundamentally correct. The layered design — registry → snapshot → calculator — maps precisely to how NSE SPAN data is structured. However, MM9.4 was built without access to a real NSE file. Three consequential mismatches must be corrected before the parser can be implemented:

1. **Unit mismatch (G-1):** `scan_risk` was assumed to be a dimensionless fraction of notional. The real NSE file stores pre-computed worst-case losses in rupees per lot-unit. This affects the calculator formula.

2. **Input contract mismatch (G-2):** `ParserRegistry` expects a pre-parsed `dict`. The real NSE file is XML — 57 MB, PC-SPAN fileFormat 4.00. The registry must accept raw bytes.

3. **SOM assumption (G-5):** The calculator requires `short_option_minimum` as a mandatory key. NSE's index SOM rate is zero — but the key must be explicitly emitted by the parser.

Everything else in MM9.4 is architecturally sound and requires no redesign.

---

## 1. Architecture Validation

### 1.1 ParserRegistry — ⚠ Requires Modification

**What is correct:**  
The registry concept — dispatching on `schema_version` to a parser function — is the right design. The `UnsupportedSpanSchema` exception is correctly placed. The default global registry pattern is appropriate.

**What requires modification:**

*Input contract:* The current signature is `Callable[[dict], SpanSnapshot]`. This assumed a pre-parsed dict — that is, some upstream step would already have extracted a Python dict from the raw file. No such step exists or should exist. The parser function must receive raw bytes and own the complete transformation from bytes to `SpanSnapshot`. The signature must become `Callable[[bytes], SpanSnapshot]`.

*Version key:* The current code uses `"v1"` as the schema_version key. The real NSE file contains `<fileFormat>4.00</fileFormat>`. The version key should be the `<fileFormat>` value verbatim — `"4.00"`. Any mapping layer between `<fileFormat>` and a private key adds indirection without benefit and creates a maintenance surface when NSE releases format 4.01 or 5.00.

*Function name:* `parse_span_csv` is a misnomer. The real format is XML. The function must be renamed or aliased to `parse_span_xml`. The versioned parser registered under `"4.00"` should be a private function named to reflect its specificity.

**What does NOT change:** The registry's dispatch logic, the `UnsupportedSpanSchema` exception, and the global default registry are correct and remain unchanged.

---

### 1.2 SpanSnapshot — ⚠ Requires Modification (minimal)

**What is correct:**  
All six existing fields are correct and correctly typed:
- `snapshot_date: date` — maps precisely to `<pointInTime/date>` parsed as YYYYMMDD
- `schema_version: str` — maps to `<fileFormat>` value
- `exchange: str` — maps to `<exchange/exch>` = "NSE"
- `segment: str` — correctly hardcoded "FO" (not present in XML; inferred from file naming)
- `file_hash: str` — correctly the SHA-256 of the companion ZIP, not derivable from XML itself
- `risk_arrays: Dict[str, SpanRiskArray]` — correctly keyed by underlying symbol, one per `<ccDef/cc>`
- `metadata: Dict[str, Any]` — correctly a free-form dict for auxiliary provenance data

**What requires modification:**  
One field must be added to the struct itself (not to metadata):

`is_settlement: bool` — derived from `<pointInTime/isSetl>`. The value is 0 for intraday files (i01, i02…) and 1 for end-of-day settlement files. This is a first-class field because:
1. The startup gate must prefer the EOD settlement file for next-day sessions — intraday and EOD files can have materially different `priceScan` values.
2. This is a binary property of the snapshot that a gate reads with a direct attribute check. Burying it in `metadata` requires a dict access and type cast, and it could be silently omitted by a future parser.

All other auxiliary data (`created` timestamp, clearing org name, INR/USD rate, scan scenario grid definitions) belongs in `metadata`. The dict absorbs these without a struct change.

**What does NOT change:** The frozen dataclass design, the six existing fields, and the `risk_arrays` dict structure.

---

### 1.3 SpanRiskArray — ⚠ Requires Modification (one semantic clarification)

**What is correct:**  
The two-field design is correct: `symbol: str` and `risk_metrics: Dict[str, float]`. The flexible dict allows the parser to emit additional fields (`price_scan_range`, `vol_scan_range`, `cvf`, `intra_spread_charge_rs`) without touching the DTO schema. This is exactly the right abstraction level.

**What requires modification:**

*D1 — scan_risk unit (see §2 D1 for the full decision):* The `risk_metrics["scan_risk"]` value was left as "flagged for confirmation" in S3. Confirmation has arrived: the real NSE RA values are in **rupees per lot-unit**, not as fractions of notional. This is not a DTO change — it is a semantic clarification of what the parser must emit and what the calculator must consume. The metric key string is unchanged; the unit is now confirmed and must be written into ADR-008.

*G-5 — short_option_minimum must be explicitly emitted:* The calculator raises `MissingRiskMetric` if this key is absent. NSE's SOM rate for NIFTY and BANKNIFTY is zero (`<somTiers/tier/rate/val>` = 0). The parser must emit `"short_option_minimum": 0.0` explicitly for every underlying. For single-stock underlyings, the parser must read the actual `<somTiers>` rate per ccDef, which may be non-zero.

**What does NOT change:** The two-field DTO shape, the `frozen=True` constraint, and the `risk_metrics` dict design.

---

### 1.4 SpanRepository — ✔ Correct

**Reasoning:**  
The repository is a pure read path that deserializes an archived snapshot, verifies its SHA-256 against the companion ZIP, and returns an immutable value. Its design is correct in every dimension:

- Pickle-based storage is appropriate: SPAN data is hundreds of floats per snapshot, read once at session start. DuckDB is unjustified overhead.
- The append-only archive (`promote_snapshot`) is correct — snapshots are immutable once published.
- `FileNotFoundError` / `ValueError` exception boundary is correctly placed: these are startup-time failures, never compute-time failures.
- Date-keyed versioning (`nse_fo_span_YYYY-MM-DD`) is correct.
- `latest_version()` convenience method is appropriate.

**One operational note (not an architectural issue):** The repository expects files named `nse_fo_span_YYYY-MM-DD.zip`. NSE publishes `nsccl.YYYYMMDD.iNN.spn` inside a ZIP container. The pipeline (`fetch_span_params.py`) must handle the rename — a pipeline implementation concern, not a repository design issue.

---

### 1.5 SpanMarginCalculator — ⚠ Requires Modification (formula correction)

**What is correct:**  
The object design is correct: injected `SpanSnapshot` as frozen config, live `PositionTracker` by reference, stateless computation. Protocol conformance (`get_exposure`, `get_used_margin`, `margin_rate`) is correct. Exception family (`MissingRiskArray`, `MissingRiskMetric`, `UnsupportedInstrument`) is correct. `get_incremental_margin` is correctly off-protocol.

**What requires modification:**

*Formula — unit mismatch (G-1, D1):* The current `_single_span_margin` computes:
```
notional = qty × price × lot
return notional × risk_pct       # treats scan_risk as a fraction
```
This is wrong for two independent reasons: (a) SPAN margin is in rupees, not a fraction of notional; (b) SPAN parameters are pre-published and must not change tick-by-tick with current price. The correct formula under Strategy B:
```
units = abs(qty) × lot
return units × scan_risk          # scan_risk in Rs/lot-unit; no price dependency
```

*Method naming:* `_risk_percentage()` is a misnomer under Strategy B. The returned value is not a percentage. Rename to `_scan_risk_per_unit()`.

*`get_incremental_margin` signature:* Currently accepts `price` and uses it in the scan margin formula. Under Strategy B, `price` is not needed for the scan component. The `price` parameter should be removed from the scan margin path.

**What does NOT change:** Protocol conformance, exception family, DI pattern, statelessness invariant, `margin_rate` as a safety multiplier. ADR-007 is fully preserved.

---

### 1.6 MarginCalculator Protocol — ✔ Correct

**Reasoning:**  
The protocol surface (`margin_rate: float`, `get_exposure`, `get_used_margin`) is correctly minimal. `MarginTracker` still conforms structurally. The protocol has not been grown and must not be grown in MM9.5. Nothing in the real NSE schema requires a protocol change. The protocol invariant holds exactly.

---

### 1.7 Startup Readiness — ✔ Correct

**Reasoning:**  
`SpanReadinessVerdict` with `ReadinessState.FRESH` / `ReadinessState.BLOCK` and no WARN grace period is the correct design. The strict binary is appropriate: a stale or absent SPAN snapshot means margin parameters are unknown, and the session must not start. The `build_span_readiness()` callable pattern mirrors the instrument master readiness gate and integrates cleanly.

**One clarification for implementation:** The startup gate should add a preference for `is_settlement=True` snapshots over intraday snapshots for the same date. Intraday files (i01) are valid for startup but EOD files represent finalized parameters. This is a policy detail surfaced by the `is_settlement` field addition — not a design flaw.

---

### 1.8 Repository Layout — ✔ Correct

**Reasoning:**  
`data/span/nse_fo_span_YYYY-MM-DD.{zip,parquet}` pairs in a flat directory is correct. The data volume (one ZIP + one pickle per trading day) does not require indexing, partitioning, or a database. The layout mirrors the instrument master archive and is appropriate for the same reasons.

---

## 2. Design Decisions

### D1 — scan_risk unit: percentage vs absolute Rs/lot

**Decision: B — absolute Rs/lot-unit**

**Reasoning:**

SPAN margin is defined by NSCCL as a pre-computed worst-case loss in rupees for one lot-unit of the underlying, across 16 price and volatility stress scenarios. The NSE SPAN file stores these losses in the `<ra/a>` elements — they are in rupees, pre-computed using Black-Scholes at each scenario's price/vol shift. They are not fractions of notional.

Strategy A (percentage) would require dividing by the price at parse time:
```
scan_risk_fraction = worst_loss_rs / (parse_time_price × cvf)
```
At runtime, the calculator computes:
```
margin = qty × lot × current_price × scan_risk_fraction
       = qty × lot × current_price × worst_loss_rs / parse_time_price
```
This is incorrect. SPAN margin does not scale with current price — it scales with the pre-defined `priceScan` range. If NIFTY is at 24,000 at parse time and moves to 24,500 at margin-check time, the margin on one NIFTY futures lot is still `lot × 2244.36 Rs`, not `lot × 2244.36 × (24500/24000)`. The clearing house publishes parameters for the day; they do not float tick-by-tick.

Strategy B stores the worst-case loss directly:
```
scan_risk = 2244.36   # Rs per lot-unit (NIFTY)
```
At runtime:
```
margin = abs(qty) × lot × scan_risk    # Rs; no price dependency; no parse-time price
```
This is correct, simpler, and deterministic across all prices observed during the session. It matches the SPAN design intent and is consistent with ADR-003.

**Downstream consequences:**

| Component | Change required |
|-----------|-----------------|
| `_single_span_margin` | Remove `price` from scan margin; use `units × scan_risk` |
| `_risk_percentage()` | Rename to `_scan_risk_per_unit()` |
| `get_incremental_margin` | Remove `price` from scan margin path; price available for exposure if needed |
| `get_used_margin` | SPAN scan component no longer needs `current_prices`; exposure component still does |
| Parser | Emit `scan_risk` as float Rs (e.g. 2244.36 for NIFTY, 5513.40 for BANKNIFTY) |
| Constants | Update `METRIC_SCAN_RISK` docstring to document unit |
| Tests | Revise expected values; confirm NIFTY margin per lot = 2244.36 × lot_size |

`margin_rate` (currently `1.0`) continues to serve as a safety multiplier on top of the SPAN scan amount, representing the ELM overlay. This is correct and requires no change.

---

### D2 — Where does XML parsing occur?

**Decision: Option A — ParserRegistry receives raw bytes; parser builds XML tree**

**Reasoning:**

The ParserRegistry's single responsibility is dispatch: given a version string, invoke the correct parser. It must not own format-specific transformation. If the registry builds an XML tree before dispatching, it becomes coupled to XML as a file format. Future format version 5.00 might be JSON, CSV, or binary — the registry must remain format-agnostic.

Under Option A, the complete transformation for one parser version is a total function:
```
raw_bytes → _parse_nsccl_v400(raw_bytes: bytes) → SpanSnapshot
```
The parser owns everything: ZIP extraction (if needed), XML parsing, XPath traversal, field extraction, RA worst-case reduction, and DTO construction. This is a clean, independently testable unit with one input type and one output type.

Under Option B, the registry builds an `ElementTree` before dispatch. This creates an implicit constraint: every registered parser must speak XML, because the registry has already committed to an XML tree for all versions. That is incorrect — "4.00" implies XML today, but "5.00" should not be constrained by format decisions made for "4.00".

Testing under Option A is also cleaner: a test injects exact bytes from the real NSE file and asserts on the returned snapshot. No XML tree mocking required.

**Revised signature:**
```python
# Before
_parsers: Dict[str, Callable[[dict], SpanSnapshot]]
# After
_parsers: Dict[str, Callable[[bytes], SpanSnapshot]]
```
This is a breaking change to the type, but no concrete parser function has been registered yet. Zero downstream impact on production code.

---

### D3 — Should ParserRegistry remain version-based?

**Decision: Yes. Adjust the version key to match the file's own declaration.**

**Version key policy:**

The current code uses internal key `"v1"`. The real file declares `<fileFormat>4.00</fileFormat>`. The key must be the `<fileFormat>` value verbatim: `"4.00"`.

Version detection sequence for any NSE SPAN file:
1. Extract the ZIP (if the raw source is a ZIP container).
2. Parse just enough XML to read `<fileFormat>` — a cheap header read, not a full parse.
3. Dispatch to the registered parser for that key.
4. The parser reads the full file and returns the snapshot.

**Policy for future versions:**

| Version pattern | Policy |
|----------------|--------|
| `4.01` (backward-compatible) | New optional elements: the `"4.00"` parser handles them via `findtext(..., default=None)`. Register the same function under `"4.01"` as an alias. |
| `4.01` (breaking) | Register a new parser function. The `"4.00"` parser remains registered for `"4.00"`. |
| `5.00` (major) | Register a new parser function. Both coexist in the registry. |
| Unknown version | `UnsupportedSpanSchema` raised (existing behavior — correct). Startup gate refuses with an actionable error. |

This policy requires no code change to the registry itself — only the discipline that implementers register under the exact `<fileFormat>` string, not an internal alias.

---

### D4 — Should SpanSnapshot evolve?

**Decision: One field addition. No other structural changes.**

Add `is_settlement: bool` to `SpanSnapshot`, derived from `<pointInTime/isSetl>`.

**Rationale for struct placement vs metadata:** The startup gate reads this value to decide whether the snapshot is suitable for the next session. A boolean at the top level of the frozen struct enables a one-line guard. Putting it in `metadata` requires dict access, a type cast, and risks silent omission by a future parser. First-class concern → first-class field.

**Everything else goes in metadata:**

| Field | XML source | Metadata key |
|-------|-----------|--------------|
| File creation timestamp | `<created>` | `"created"` |
| Clearing org code | `<ec>` | `"clearing_org"` |
| INR/USD rate | `<curConv/factor>` | `"inr_usd_rate"` |
| 16 scan scenario definitions | `<pointDef/scanPointDef>` | `"scan_scenarios"` |

The `scan_scenarios` entry makes the snapshot self-documenting — enabling future RA recomputation without a second parse of the original file.

**What does NOT change:** The frozen dataclass design, the six existing fields, and their types.

---

### D5 — Should the 16 scenario arrays be stored?

**Decision: A — keep the simplified model for MM9.5**

**Reasoning:**

The single `scan_risk` value (worst-case weighted loss across 16 scenarios) is the output of the scenario reduction. It is the sufficient statistic for every computation the current calculator performs: `margin = units × scan_risk`. The 16 raw values are an intermediate representation that the calculator never needs.

Storing the full array would require either: (a) a `scenario_array: Tuple[float, ...]` field in `SpanRiskArray` — complicating the DTO with data no current consumer uses; or (b) 16 entries in `risk_metrics` — an awkward encoding for a structured type.

Neither is justified without a concrete consumer. The only future use case requiring the full array is inter-month spread credit computation (delta matching across expiries). That is explicitly deferred to MM10 (see D6). When that slice arrives, the architecture can introduce a separate `SpanContractRiskTable` DTO for per-contract RA data, rather than retrofitting `SpanRiskArray`.

**Concession for observability:** The scan scenario *definitions* (price/vol multipliers and weights for each of the 16 points) are stored in `metadata["scan_scenarios"]`. This costs 16 × 5 floats — negligible — and makes the snapshot self-documenting.

---

### D6 — Calendar spreads, SOM, NOV: which milestone?

**Short option minimum (SOM) — MM9.5**

The SOM rate is directly in the SPAN file per underlying (`<ccDef/somTiers/tier/rate/val>`). For NIFTY and BANKNIFTY it is zero; for single-stock underlyings it may be non-zero. The parser must read this value per ccDef and emit `"short_option_minimum"` in every `SpanRiskArray`. No calculator change is required — `max(scan_risk, 0.0) == scan_risk` for index options; for non-zero SOM underlyings the existing `max()` logic in the calculator applies correctly. SOM belongs in MM9.5 because it is required for the parser to produce a snapshot the calculator can consume without raising `MissingRiskMetric`.

**Calendar spread charges — MM10**

The `<dSpread>` data is present: NIFTY at Rs 425/lot-pair, BANKNIFTY at Rs 1,029/lot-pair. Consuming spread credits requires portfolio-level leg matching — identifying opposite-side positions across expiries on the same underlying and netting their margin. This is a book-level operation, not a calculator-level concern. The calculator is stateless and processes one position at a time; adding leg grouping would violate that invariant. Defer to MM10.

The conservative overestimate (two full single-leg margins on a calendar spread, no credit) is safe: the gate may reject tradeable orders at the margin, but will never admit unmargined ones.

**Net option value (NOV) credit — Future (post MM10)**

NOV requires tracking the long option premium paid across the book and crediting it against margin. This is a portfolio accounting concern distinct from margin computation. It requires multi-leg position management that is out of scope for the current platform. Defer indefinitely.

**ELM (Extreme Loss Margin) as a formal separate component — Future**

The current design uses `margin_rate` as a safety multiplier on scan margin. The NSE ELM rate (published by NSCCL alongside SPAN parameters, but not in the SPAN file itself) should eventually be sourced and applied as a distinct additive component. For MM9.5, `margin_rate = 1.0` as a buffer multiplier on scan margin is acceptable. Defer formal ELM sourcing to a slice when the platform connects to NSCCL's ELM publication.

---

## 3. Deferred Items

The following XML elements are intentionally unsupported in MM9.5. All deferrals result in margin at or above the true NSCCL-computed value — overestimate, never underestimate.

| XML element | Semantic | Why deferred | Safety direction |
|-------------|----------|--------------|-----------------|
| `<ccDef/dSpread>` | Calendar spread charges | Requires portfolio-level leg matching; new architectural concern outside calculator scope | Overestimates margin on hedged positions — safe |
| `<oopPf/series/opt>` (per-strike RA) | Per-strike option scenario losses | Requires `SpanOptionRiskTable` DTO; underlying-level RA is a valid conservative substitute | Overestimates margin on low-delta options — safe |
| `<ccDef/adjRate>` | Scenario-specific rate adjustments | Pre-computed RA already incorporates these; applying them again would double-count | Not applicable when using pre-computed RA directly |
| `<pointDef/deltaPointDef>` | Delta scenarios for inter-month spread credit | Spread credit computation deferred to MM10 | Not applicable until spread credits are implemented |
| `<clearingOrg/pbRateDef>` | Performance bond rate tiers by account type | Clearing-member-level distinctions not applicable to single-account trading | Not applicable |
| `<definitions/acctTypeDef>` | Account type definitions | Single-account platform; member/hedge/customer distinctions not needed | Not applicable |
| `<curConv>` | INR/USD conversion rate | INR-denominated platform; USD conversion not needed | Not applicable |
| `<clearingOrg/interSpreads>` | Inter-commodity spreads | Empty for NSE in this file; NIFTY/BANKNIFTY netting requires commodity-level pairing | Not applicable currently |

---

## 4. Risk Assessment

### 4.1 Technical Risk — HIGH (G-1, pre-correction)

The unit mismatch is the highest-severity technical risk in the current codebase. If `scan_risk` is emitted in Rs/lot-unit by the parser but the calculator multiplies it against notional (`qty × price × lot × scan_risk`), the result is approximately `24,000 × 75 × 2244 ≈ Rs 4 billion per NIFTY lot` — absurdly large, immediately visible. Alternatively, if an implementer independently discovers Strategy A (dividing by price at parse time) and the calculator uses the current formula, the result is arithmetically plausible (~Rs 168,000 per lot) but contractually undefined — the formula only produces the correct number when current price equals parse-time price.

The risk is eliminated by ADR-008, which locks the unit before any implementation begins.

All other technical risks are LOW: the XML parse is a one-time startup cost; the ZIP container is a known, solved problem; the file format is well-documented by reverse engineering.

### 4.2 Architectural Risk — LOW

The interface change (`dict → bytes`) is localized to the parser layer and has no downstream production impact — no concrete parser function has been registered. The calculator formula change modifies one private method body with no protocol surface impact. No ADR is invalidated. The composition swap (S4) is unaffected.

### 4.3 Operational Risk — MEDIUM

*Intraday vs EOD file selection:* NSE publishes multiple intraday files per day (i01, i02…) and one EOD settlement file per trading day. Using an intraday file (i01) with a lower `priceScan` at session start slightly underestimates required margin versus what the clearing house will compute at EOD. The `is_settlement` field enables the startup gate to enforce a policy. **Recommended policy:** accept intraday files for MVP; enforce EOD-only for production.

*ZIP container:* NSE distributes the `.spn` XML file inside a ZIP. The pipeline must extract before parsing. This is a solved problem but must be tested end-to-end.

*SOM for single-stock underlyings:* The SOM rate is zero for NIFTY and BANKNIFTY. Single-stock underlyings may have non-zero SOM rates. The parser must read `<somTiers>` per ccDef rather than hardcoding zero. If a single-stock SOM is misread as zero, the gate may undercharge margin on short equity options. This is a parser correctness concern, not an architecture concern, but it must be tested.

### 4.4 Maintenance Risk — MEDIUM

NSE has historically changed SPAN file formats. The version registry mitigates this, but only if the key matches `<fileFormat>` verbatim and the policy (D3) is documented in an ADR. The risk materialises as a BLOCK verdict at startup with `UnsupportedSpanSchema` — a clear, actionable error. This is the correct behavior; the risk is operational (the platform stops) not silent (the platform continues with wrong parameters).

### 4.5 Future Compatibility — HIGH

Strategy B (absolute Rs/lot) is more robust to lot size changes than Strategy A. NSE periodically revises lot sizes. Under Strategy B, a lot size change requires only an instrument master update — the `scan_risk` value in the snapshot remains valid; `new_lots × scan_risk` is correct. Under Strategy A, the fraction embeds the old lot size at parse time and would produce incorrect margins after a lot size change without an explicit re-parse.

The `risk_metrics: Dict[str, float]` design of `SpanRiskArray` accommodates future fields (`intra_spread_charge_rs`, `price_scan_range`, `vol_scan_range`, `cvf`) without any DTO schema change. This is the correct abstraction level for a domain where the parameter set evolves.

---

## 5. ADR Recommendations

Three new ADRs are required. **Do not write them yet — identify and describe only.**

---

### ADR-008: SpanRiskArray scan_risk Unit Convention

**Title:** `scan_risk` stores absolute rupees per lot-unit, not a fraction of notional  
**Purpose:** Lock the canonical unit of `risk_metrics["scan_risk"]` so parser and calculator are unambiguously aligned before either is implemented.  
**Why required:** G-1 identified a unit mismatch between the assumed model (fraction of notional) and the real NSE file (Rs/lot-unit). ADR-007 established the metric-key contract but explicitly flagged the unit as "to be confirmed at implementation time." That confirmation has now arrived and must be recorded formally. Without this ADR, the next implementer may independently choose Strategy A and reintroduce the mismatch.  
**Scope:** Defines that `scan_risk ∈ risk_metrics` is in units of Rs per lot-unit; the calculator formula `margin = abs(qty) × lot × scan_risk`; that price does not appear in the scan margin formula; and that the parser derives this value as `max(weight[i] × max(0, −RA[i]) for i in 0..15)` from the NSE risk array.

---

### ADR-009: ParserRegistry Input Contract

**Title:** Parser functions receive raw bytes; the registry performs no format transformation  
**Purpose:** Define the contract between `ParserRegistry` and registered parser functions.  
**Why required:** The current implementation uses `Callable[[dict], SpanSnapshot]` — an interface that assumed upstream pre-processing that does not exist. The real file requires `Callable[[bytes], SpanSnapshot]`. This is a breaking change to the interface contract and must be recorded so future parser authors know exactly what they receive and must return.  
**Scope:** Defines the parser function signature; establishes that version detection reads `<fileFormat>` verbatim as the registry key; establishes that ZIP extraction, XML parsing, field extraction, and RA reduction are the parser's responsibility.

---

### ADR-010: SPAN Version Key Policy

**Title:** Registry keys match `<fileFormat>` verbatim; policy for minor/major version changes  
**Purpose:** Define how the platform handles new SPAN format versions released by NSE.  
**Why required:** The current internal key `"v1"` has no relationship to NSE's `<fileFormat>` value. Without a documented policy, each implementer facing a new version (4.01, 5.00) will make an independent decision, potentially creating mapping inconsistencies or silent failures.  
**Scope:** The registry key is the `<fileFormat>` string verbatim; minor-compatible versions may alias to the same parser; major versions require a new registered function; `UnsupportedSpanSchema` is the correct behavior for unknown versions.

---

## 6. Implementation Roadmap

The minimum implementation set required to connect the real NSE SPAN file to the existing MM9.4 architecture. Each slice is independently reviewable and TDD-compatible.

---

### MM9.5-S1: Registry Interface and Snapshot Field Corrections

**Scope:** Two targeted changes to existing code — no new logic.

1. Change `ParserRegistry` type from `Callable[[dict], SpanSnapshot]` to `Callable[[bytes], SpanSnapshot]`. Rename `parse_span_csv` to `parse_span_xml` (or introduce `parse_span_xml` as the canonical entry point, keeping `parse_span_csv` as a deprecated alias). Update the dispatch method signature.

2. Add `is_settlement: bool` to `SpanSnapshot`. Update `span_snapshot.py` and all existing test fixtures that construct `SpanSnapshot` — add `is_settlement=False` as the new field with a default of `False` for backward compatibility with existing intraday-case tests.

**TDD anchor:**
- Test that a parser registered under `"4.00"` receives bytes and returns a `SpanSnapshot` with `is_settlement=True/False` correctly set.
- Test that `UnsupportedSpanSchema` is raised for an unknown version key.
- Test that the existing test suite remains fully green (no regressions).

**Does not touch:** Calculator, readiness gate, repository, pipeline.

**Why first:** Every subsequent slice depends on the interface being correct. Fixing it independently makes the type system correct before any parser is written.

---

### MM9.5-S2: NSE XML Parser (v4.00)

**Scope:** New parser function registered under `"4.00"`. The parser implements the complete transformation from raw bytes to `SpanSnapshot`.

Extracts:
- `snapshot_date` from `<pointInTime/date>` (YYYYMMDD format)
- `is_settlement` from `<pointInTime/isSetl>`
- `exchange` from `<exchange/exch>`
- For each `<ccDef/cc>`: one `SpanRiskArray` with:
  - `scan_risk`: worst-case weighted RA loss from the nearest-expiry `<futPf/fut/ra>` (Strategy B — Rs/lot-unit)
  - `short_option_minimum`: from `<ccDef/somTiers/tier/rate/val>` read per underlying (not hardcoded)
  - Additional metrics stored but not required by the calculator: `price_scan_range`, `vol_scan_range`, `cvf`, `intra_spread_charge_rs`
- `metadata` dict: `created`, `clearing_org`, `inr_usd_rate`, `scan_scenarios`

**TDD anchor:**  
Tests run against the real file `reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn`:
- `snapshot.snapshot_date == date(2026, 6, 25)`
- `snapshot.is_settlement == False`
- `snapshot.risk_arrays["NIFTY"].risk_metrics["scan_risk"]` ≈ 2244.36 (worst loss from nearest-expiry futures RA)
- `snapshot.risk_arrays["BANKNIFTY"].risk_metrics["scan_risk"]` ≈ 5513.40
- `snapshot.risk_arrays["NIFTY"].risk_metrics["short_option_minimum"] == 0.0`
- `snapshot.risk_arrays["NIFTY"].risk_metrics["price_scan_range"] == 2234.01`
- `len(snapshot.risk_arrays) == 239`
- Corrupt/truncated file raises a clear `ValueError`, not a silent empty snapshot
- `UnsupportedSpanSchema` raised for `<fileFormat>3.00</fileFormat>`

**Does not touch:** Calculator, repository, readiness, pipeline.

**Why second:** The parser is the central missing piece. Once it produces a validated snapshot from a real file, the corrected calculator can be tested against real data.

---

### MM9.5-S3: Calculator Formula Correction (Strategy B)

**Scope:** Targeted changes to `SpanMarginCalculator` only — no protocol changes, no handler changes.

1. Change `_single_span_margin` to `units × scan_risk` — remove `price` from the scan component.
2. Rename `_risk_percentage()` to `_scan_risk_per_unit()`.
3. Update `get_incremental_margin`: remove `price` from the scan margin formula; price is only needed for exposure.
4. Update `METRIC_SCAN_RISK` constant docstring to document the unit (Rs/lot-unit).
5. Zero changes to the protocol, `MarginTracker`, handler, or any consumer.

**TDD anchor:**
- NIFTY single-lot margin = `scan_risk × lot_size` (hand-built snapshot with `scan_risk=2244.36`, `lot_size=75` → `margin = Rs 168,327`).
- Doubling lot_size doubles margin — confirming no price dependency.
- `margin_rate=2.0` doubles the result — safety multiplier still applies.
- Revise expected values in existing R1–R6, I1–I3 test set; full suite remains green.
- Full test suite passes at `791 + new`.

**Does not touch:** Protocol, handler, readiness, pipeline, repository.

**Why third:** S2 must exist first so S3's tests can be validated against real `scan_risk` values from the actual parser. The formula correction is dependent on confirming what the parser produces.

---

### MM9.5-S4: Fetch Pipeline Integration

**Scope:** `scripts/fetch_span_params.py` — connect to the real NSE URL, handle ZIP extraction, call the registry-dispatched parser, archive the snapshot.

1. Implement ZIP extraction — the NSE file is `nsccl.YYYYMMDD.iNN.spn` inside a ZIP.
2. Fast-read `<fileFormat>` to determine the parser version key.
3. Call the registry with the correct version key and raw bytes.
4. Call `promote_snapshot(raw_bytes, parsed_snapshot, snapshot_date, archive_dir)` — no changes to this function.
5. Wire `SPAN_SOURCE_URL` and `SPAN_REFRESH_CUTOFF` as named constants confirmed against NSE's published schedule.

**TDD anchor:**
- Integration test: inject a local copy of the real `.spn` ZIP; assert full round-trip: parse → promote → load → margin calculation produces Rs 168,327 for one NIFTY futures lot.
- Running twice for the same date is idempotent (existing append-only behavior).
- Readiness gate returns READY after a successful fetch for today's expected date.
- Readiness gate returns BLOCK with `is_settlement=False` if policy requires EOD only.

**Does not touch:** Calculator, protocol, handler, execution path.

**Why last:** The only slice requiring network access (or a mocked URL). All earlier slices are filesystem-free. S4 closes the loop from NSE file publication to live margin gate.

---

## 7. Slice Dependency Graph

```
MM9.5-S1  (registry interface + SpanSnapshot.is_settlement)
    │
MM9.5-S2  (NSE XML parser — consumes corrected interface, produces real snapshots)
    │         \
    │          MM9.5-S3  (calculator formula — can be written against hand-built snapshots;
    │                      validate final expected values using S2 output)
    │
MM9.5-S4  (fetch pipeline — requires S2's parser to be registered)
```

S1 is the prerequisite for everything. S2 is the critical-path bottleneck. S3 can be written in parallel with S2 using hand-built snapshots (as per the original S3 approach), with final value validation deferred until S2 is complete. S4 closes the round-trip.

---

## 8. Success Criteria

**1. Is MM9.4 fundamentally correct?**

**Yes.** The layered design — `ParserRegistry → SpanSnapshot → SpanMarginCalculator → MarginCalculator protocol` — maps accurately to how NSE SPAN data is structured. The parser/calculator separation is correct. The immutable snapshot DTO is correct. The repository abstraction is correct. The readiness gate pattern is correct. The protocol is correct. The exception family is correctly placed.

MM9.4's gaps are implementation gaps, not architectural gaps. Every identified issue was a consequence of building against assumptions rather than a real file — a predictable and acceptable outcome for design-first architecture. The assumptions were structurally sound; only two (unit and input contract) require correction.

**2. Does MM9.4 require a redesign?**

**No.** Three targeted modifications correct the gaps:
- Registry input contract: `dict → bytes` (one type signature change in one file)
- `SpanSnapshot`: add `is_settlement: bool` (one field addition in one file)
- Calculator formula: `notional × fraction → units × Rs/lot` (one method body change in one file)

No component is replaced. No ADR is invalidated. No protocol grows. The MM9.4 architecture survives contact with the real NSE file intact.

**3. What is the critical path to a working SPAN margin gate?**

`MM9.5-S1 (interface)` → `MM9.5-S2 (parser)` → `MM9.5-S3 (formula)` → `MM9.5-S4 (pipeline)`. S1 is fast. S2 is the largest slice and the bottleneck. S3 can proceed partially in parallel with S2.

**4. Are ADR-001, ADR-003, ADR-006, ADR-007 preserved?**

**Yes, without exception.**  
- ADR-001 (Ledger Is Truth): the calculator reads the live position tracker on demand; no portfolio state is cached.  
- ADR-003 (Deterministic Processing): Strategy B removes price from the scan margin formula, making the result more deterministic — same inputs, same output, regardless of tick price.  
- ADR-006 (Sole Orchestrator): MM9.5-S1 through S4 introduce no new runtime paths and no new orchestration.  
- ADR-007 (MarginCalculator Seam): the protocol is not grown; `MarginTracker` continues to conform; the calculator remains the concrete implementation behind the seam; the seam's rules are unchanged.
