# MM10 — Architecture Roadmap
## Institutional-Grade SPAN Margin Engine

**Date:** 2026-06-29  
**Author role:** System Architect  
**Predecessor milestone:** MM9.5-complete (tag: `mm9.5-complete`, commit: `1bb6b60`)  
**Status:** Pre-implementation — for Technical Lead review and approval  
**2026-07-01 update:** MM10.1–MM10.4 implemented as specified. MM10.5 (Exposure Margin, §ELM+EM
composition) was subsequently **retired, not implemented** — resolved as the same regulatory
charge as ELM under legacy naming. See `docs/architecture_decisions.md` ADR-012 and
`docs/reports/MM10_5_MARGIN_COMPONENT_VERIFICATION.md`.  

**Evidence base:**  
- As-built source: `core/risk/span/` (all modules, post-MM9.5)  
- `docs/reports/MM9_5_ARCHITECTURE_RECONCILIATION.md`  
- `docs/reports/MM9_FINAL_ARCHITECTURE_CERTIFICATION.md`  
- `docs/reports/MM9_5_S0_5_EXTERNAL_MARGIN_RECONCILIATION.md`  
- `docs/reports/SPAN_XML_SCHEMA_AND_MM9_MAPPING.md`  
- Real NSE SPAN file: `reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn`  
- ADR-001 through ADR-010 (`docs/architecture_decisions.md`)  
- 957 tests passing at baseline (196 in the SPAN suite)

**Governing constraints:**  
ADR-001 (Ledger Is Truth) · ADR-003 (Deterministic Processing) · ADR-006 (Sole Orchestrator) · ADR-007 (MarginCalculator Seam) · ADR-008 (scan_risk Units) · ADR-009 (Parser Input Contract) · ADR-010 (Version Key Policy)

---

## 1. Current SPAN Capability

### 1.1 What the platform can do today

The platform has a production-grade SPAN infrastructure built during MM9.0–9.5. The following is a precise inventory of what is implemented, tested, and certified.

**Data acquisition and parsing**

- `SpanPipeline` downloads the NSE SPAN ZIP from the exchange, extracts the `.spn` XML, calls the registry, and archives the snapshot.
- `ParserRegistry` dispatches on `<fileFormat>` verbatim (ADR-009, ADR-010). `"4.00"` is the only registered version.
- `ParserV400` (`parser_v400.py`) performs a complete transformation of raw bytes to `SpanSnapshot`:
  - Reads all 239 `<ccDef>` underlying definitions
  - Derives `scan_risk` as max weighted loss across 16 scenarios from nearest-expiry `<futPf/fut/ra>`
  - Reads `short_option_minimum` per underlying from `<somTiers/tier/rate/val>`
  - Reads `intra_spread_charge_rs` per underlying from `<dSpread>` (minimum charge tier)
  - Reads `price_scan_range`, `vol_scan_range`, `cvf`, `risk_free_rate` and stores them in `risk_metrics`
  - Extracts per-expiry `SpanFutureContract` tuples (symbol, expiry, price, delta, TTE, priceScan, volScan, RA[16])
  - Extracts per-expiry `SpanOptionSeries` tuples (vol, priceScan, volScan, TTE)
  - Extracts per-strike `SpanOptionContract` tuples (strike, type, price, delta, IV, RA[16])
  - Stores 16 scan scenario definitions in `metadata["scan_scenarios"]`

**Data model**

- `SpanSnapshot` — frozen DTO, SHA-256 provenance, `is_settlement` flag, full contracts
- `SpanRiskArray` — per-underlying risk metrics dict
- `SpanFutureContract`, `SpanOptionSeries`, `SpanOptionContract` — frozen per-contract value types

**Repository and readiness**

- `SpanRepository` — pickle-based archive, SHA-256 integrity verification
- `SpanReadiness` — FRESH/BLOCK verdict at session startup
- `SpanFreshness` — staleness check against expected trading date
- Driver startup gate integration (`_check_span_readiness`)

**Margin computation**

`SpanMarginCalculator` implements the `MarginCalculator` protocol (ADR-007):

```
margin = abs(qty) x lot_size x max(scan_risk, short_option_min) x margin_rate
```

where `scan_risk` is absolute Rs per lot-unit (ADR-008). Price does not appear in the scan margin formula. The formula is validated against NSCCL-published values: NIFTY Rs 168,327 per lot (+0.19% vs published range).

The calculator is wired as the active margin engine for LIVE F&O via composition swap at `scripts/fno_runner.py`. Equity / paper / backtest use the unchanged `MarginTracker` (flat 20%).

**Test coverage**

957 tests total; 196 in `tests/risk/span/`. All passing at the `mm9.5-complete` tag.

---

### 1.2 What is parsed but not consumed

The following data is extracted by `ParserV400` and stored in the `SpanSnapshot`, but the calculator does not yet use it:

| Parsed data | Stored in | What it enables |
|-------------|-----------|-----------------|
| `intra_spread_charge_rs` per underlying | `risk_metrics["intra_spread_charge_rs"]` | Calendar spread credits (MM10.3) |
| `SpanFutureContract.ra` (per-expiry RA[16]) | `snapshot.futures[symbol]` | Per-expiry futures margin (MM10.2) |
| `SpanOptionContract.ra` (per-strike RA[16]) | `snapshot.option_contracts[symbol]` | Per-strike option margin (MM10.2) |
| `SpanOptionContract.delta`, `.implied_vol` | `snapshot.option_contracts[symbol]` | Greek accuracy (post-MM10) |
| `metadata["scan_scenarios"]` (16 definitions) | `snapshot.metadata` | Scenario re-derivation audit |

This data is already in the snapshot. MM10 consumes it; it does not require re-parsing.

---

### 1.3 Known safety gap (blocking)

The MM9 certification (§7, §8) identified one unresolved safety issue that must be closed before any MM10 capability work begins:

> `fno_runner.py:155-170` wraps `span_repo.load()` in `try/except Exception`. On any snapshot load failure it logs a WARNING and proceeds with `MarginTracker` (flat 20%). The driver's `_check_span_readiness` guard is a no-op because no readiness checker was injected.
>
> **Result:** A LIVE F&O session with absent or corrupt SPAN data does not refuse — it trades on flat-rate margin with only a warning.

This is a hard requirement for production. MM10.1 closes it.

---

## 2. Remaining SPAN Components

This section evaluates every significant SPAN feature not yet implemented and assigns a disposition.

### 2.1 Calendar / Inter-Month Spread Credits — MM10 (MM10.3)

**What it is:** When a portfolio holds opposite-side positions on the same underlying across different expiries (a calendar spread), NSCCL charges a reduced margin. Instead of two full single-leg margins, the matched lot-pairs pay a flat spread charge. For NIFTY: Rs 425 per lot-pair; for BANKNIFTY: Rs 1,029 per lot-pair.

**Current state:** `intra_spread_charge_rs` is stored in `risk_metrics` for every underlying. The calculator does not apply it.

**Why include in MM10:** This is the most capital-significant missing component for any F&O strategy using calendar spreads or multi-expiry positions. Currently the calculator overcharges such positions by approximately `2 x scan_risk x lots - spread_charge` per lot-pair — for NIFTY, roughly Rs 336,000 per lot-pair. This overcharge reduces deployable capital and may incorrectly gate valid trades.

**Safety direction:** Conservative when not applied (overestimates margin). Never unsafe.

---

### 2.2 Per-Strike Option Margin — MM10 (MM10.2)

**What it is:** Options positions are currently margined using the underlying futures `scan_risk` — the worst-case loss from the nearest-expiry futures RA. The true option margin is derived from the per-strike `SpanOptionContract.ra` for the specific expiry/strike/type held.

**Current state:** `SpanOptionContract.ra` is parsed and stored. The calculator uses the underlying-level `scan_risk` for all positions regardless of instrument type.

**Why include in MM10:** For deep in-the-money options, the per-strike RA is close to the futures RA and the overcharge is small. For far out-of-the-money options (low delta), the per-strike RA is much smaller than the futures RA, and the overcharge is large. Using futures RA for all options is conservative but capital-inefficient for short-dated OTM positions.

**Architectural concern:** The calculator must determine whether a position is on a futures or options contract and, for options, look up the correct `SpanOptionContract` by (symbol, expiry, strike, option_type). This requires the position instrument to carry these attributes. Whether the current instrument model exposes them must be verified at implementation time.

**Safety direction:** Conservative when not applied. Never unsafe.

---

### 2.3 Per-Expiry Futures RA Differentiation — MM10 (MM10.2)

**What it is:** When a portfolio holds futures on the same underlying but different expiries, all positions currently use the same `scan_risk` derived from the nearest-expiry futures RA. Far-expiry contracts may have higher or lower risk arrays depending on carry and vol term structure.

**Current state:** `SpanFutureContract` tuples are stored per symbol per expiry, each with a full RA[16]. The calculator ignores expiry and uses the single underlying-level `scan_risk`.

**Why include in MM10:** Accuracy and consistency. The per-expiry data is already present. The lookup is straightforward (match by symbol + expiry). This milestone is naturally bundled with per-strike option RA (both are contract-level RA lookups).

**Safety direction:** Could be either direction (far-expiry RA may be higher or lower than near-expiry). Implement with fallback to underlying-level RA if the contract is not found.

---

### 2.4 MarginCalculator Protocol v2 — MM10 (MM10.1)

**What it is:** `get_incremental_margin` is defined on `SpanMarginCalculator` but not on the `MarginCalculator` protocol. The execution handler reaches it via `hasattr` duck-typing (`handler.py:1172-1176`). This is acknowledged debt from MM9.4 (protocol frozen to avoid `MarginTracker` breakage at the time of the composition swap).

**Why include in MM10:** The `hasattr` detection is brittle. A future `MarginCalculator` implementation that accidentally defines `get_incremental_margin` with a different signature would be silently invoked. Formalizing v2 eliminates this risk. Small, contained change.

---

### 2.5 ELM (Extreme Loss Margin) — MM10 (MM10.4)

**What it is:** NSE requires ELM on top of SPAN scan margin. ELM is a flat percentage of notional, published by NSCCL separately from the SPAN file:
- Index futures / index options: 1.5% of contract value
- Single-stock derivatives: varies per underlying (typically 3.5-5.0%)

**Current state:** `margin_rate` (currently `1.0`) serves as a safety multiplier on scan margin. This is not equivalent to ELM. ELM is `elm_rate x notional`; scan margin is `scan_risk x lots`. The two components are structurally different.

**Why include in MM10:** Without ELM, the computed margin understates the true NSE required margin. For a NIFTY futures lot: SPAN scan = Rs 168,327; ELM at 1.5% of Rs 18,03,885 notional = Rs 27,058. Total exchange margin ~Rs 195,000. The platform currently underestimates by approximately 16%.

**Data source risk:** ELM rates are published in NSCCL circulars, not in the SPAN XML. A new data source (or hardcoded constants for index underlyings) is required.

---

### 2.6 Exposure Margin — MM10 (MM10.5)

**What it is:** NSE's third margin layer, on top of SPAN + ELM:
- Index futures: 2.0% of contract value
- Equity futures: 5.0% of contract value
- Options (sold): 2.0% or 5.0% depending on underlying classification

**Current state:** Not implemented.

**Why include in MM10:** Required for the complete NSE margin picture. For NIFTY futures: exposure margin = 2% x Rs 18,03,885 = Rs 36,078. Total margin per lot = Rs 231,000 vs computed Rs 168,327 — a 37% shortfall if excluded.

**Data source:** Rates are stable NSE rules, published in the NSE margin framework. Can be sourced as named constants.

---

### 2.7 Hard Refusal for Absent/Corrupt SPAN — MM10 (MM10.1)

Covered in §1.3. Safety prerequisite. Smallest slice.

---

### 2.8 Items Evaluated and Deferred Beyond MM10

| Item | Disposition | Reasoning |
|------|-------------|-----------|
| Net Option Value (NOV) credit | Post-MM10 | Requires tracking long option premium paid across the book as a credit against margin. Complex portfolio accounting orthogonal to margin computation. Deferred indefinitely. |
| Delivery margin | Post-MM10 | Near-expiry margin surcharge published per NSE circular. Not in the SPAN file. Deferred until near-expiry position management is in scope. |
| Inter-commodity spreads | N/A | `<clearingOrg/interSpreads>` is empty in the NSE file. NSE does not publish inter-commodity spread credits between NIFTY and BANKNIFTY through SPAN. Not applicable. |
| `<adjRate>` scenario-specific adjustments | N/A | Pre-computed RA already incorporates these. Applying them separately would double-count. |
| `<pbRateDef>` performance bond tiers | N/A | Clearing-member account type distinctions. Single-account platform. |
| `<curConv>` INR/USD conversion | N/A | INR-denominated platform. |
| Broker margin reconciliation | Post-MM10 | Diagnostic only. ADR-007 prohibits broker I/O at margin time. |

---

## 3. Proposed MM10 Breakdown

### MM10.1 — Safety Hardening and Protocol v2

**Scope:** Two targeted safety and hygiene fixes. No capability extension.

**S1 — Absent/Corrupt SPAN Hard Refusal**

Convert `fno_runner.py:155-170` from `try/except Exception` to a hard refusal for LIVE F&O. When `span_repo.load()` fails (any exception), inject an always-BLOCK readiness checker so `_check_span_readiness` refuses startup with a logged reason. The driver then reaches BLOCK -> abort_startup -> STOPPED. This preserves the existing startup gate architecture exactly.

**S2 — MarginCalculator Protocol v2**

Add `get_incremental_margin(symbol, quantity, price, lot_size) -> float` to the `MarginCalculator` protocol definition. Update `MarginTracker` to implement the method with a conservative flat-rate estimate. Retire the `hasattr` capability detection in `handler.py:1172-1176` and call the protocol method directly. No formula changes anywhere.

**TDD anchor:**
- LIVE F&O session with no snapshot in `data/span/` -> startup aborts with BLOCK and a logged reason, not a WARNING and a flat-rate proceed
- `MarginTracker` satisfies the v2 protocol (structural conformance test)
- `SpanMarginCalculator` satisfies the v2 protocol
- Existing handler integration tests remain green (behaviour unchanged; only the detection path changes)

---

### MM10.2 — Contract-Level RA Accuracy

**Scope:** Replace the underlying-level `scan_risk` fallback with per-contract RA for futures and options positions. The parser already extracts this data. This milestone wires it into the calculator.

**S1 — Per-Expiry Futures RA**

For a futures position, look up `snapshot.futures[symbol]` for the contract matching the position's expiry. Apply the existing RA reduction formula (`_derive_scan_risk`) to get `per_expiry_scan_risk`. Fall back to `risk_arrays[symbol]["scan_risk"]` if the contract is not found.

**S2 — Per-Strike Option RA**

For an options position, look up `snapshot.option_contracts[symbol]` for the contract matching (expiry, strike, option_type). Apply the RA reduction. Fall back to underlying-level `scan_risk` if not found.

**Prerequisite investigation:** The position's `instrument` object must expose expiry (for futures) and expiry + strike + option_type (for options). If these attributes are absent from the current instrument model, a targeted instrument model extension is required before S1/S2 can be implemented. This investigation is the first task of MM10.2.

**TDD anchor:**
- NIFTY near-month futures -> scan_risk from matching `SpanFutureContract.ra`, within 0.5% of the underlying-level `scan_risk` (near-month is the derivation basis)
- NIFTY far-month futures -> scan_risk from the far-month RA (may differ from near-month)
- NIFTY 24000 CE (low delta) -> scan_risk from matching `SpanOptionContract.ra`, materially less than underlying futures scan_risk
- NIFTY deep ITM call -> scan_risk close to underlying futures scan_risk
- Fallback: position with expiry absent from snapshot -> falls back to underlying scan_risk, no exception raised
- Fallback: option position with strike absent from snapshot -> falls back to underlying scan_risk, no exception raised
- Full regression suite green (existing tests use hand-built snapshots with no `futures` or `option_contracts` -> fallback always taken -> all expected values unchanged)

---

### MM10.3 — Calendar Spread Credits

**Scope:** Apply inter-month spread charge credits for portfolio positions holding opposite-side legs on the same underlying across different expiries. `intra_spread_charge_rs` per underlying is already in `risk_metrics`.

**Design:**

The credit algorithm is a portfolio-level operation separate from per-position scan margin:

1. For each underlying in the portfolio, enumerate all open positions.
2. Separate positions by expiry. Identify positions with opposite sides across different expiries.
3. Perform greedy leg-matching: pair long lots against short lots at different expiries, consuming matched lots from both. Sort by nearest expiry first (conservative: credits near-month pair first).
4. For each matched lot-pair the credit is: `per_expiry_scan_risk_near + per_expiry_scan_risk_far - intra_spread_charge_rs`. This replaces two full-leg margins with one spread charge.
5. The credit cannot reduce total portfolio margin below zero.

**Implementation path:** A new private method `_spread_credit(positions_by_symbol) -> float` on `SpanMarginCalculator`. `get_used_margin` computes the gross per-position sum first, then subtracts the total spread credit. No new class required.

**Architecture note:** Leg-matching requires each position's expiry, which MM10.2-S1 delivers. MM10.2 must precede or accompany MM10.3.

**TDD anchor:**
- Single NIFTY near-month long, no opposite leg -> credit = 0, margin unchanged
- NIFTY near-month long + NIFTY far-month short (equal lots) -> credit = `near_scan + far_scan - 425` per matched lot-pair
- NIFTY 2x long near + 1x short far -> credit on one matched lot-pair only; second near lot receives no credit
- Credit floor: total portfolio margin >= 0 always
- BANKNIFTY spread charge = Rs 1,029 per lot-pair (from `intra_spread_charge_rs`)
- Regression: all existing single-position tests -> credit = 0 (no opposite leg) -> all pass unchanged

---

### MM10.4 — ELM (Extreme Loss Margin)

**Scope:** Source NSE ELM rates and apply as an additive component to SPAN scan margin.

**ELM is structurally distinct from scan margin:**
```
scan_margin = abs(qty) x lot_size x scan_risk          # from SPAN RA (price-independent)
elm          = elm_rate x abs(qty) x lot_size x price  # percentage of notional
total        = scan_margin + elm
```

`margin_rate` is a multiplicative safety buffer on the combined total. It is not ELM. These must be kept separate.

**Data source:** ELM rates are published in NSCCL circulars and are not in the SPAN file. They are stable and change infrequently. Start with hardcoded constants for index underlyings in a new module `core/risk/span/elm_rates.py`. A rate of 0.0 for unknown underlyings degrades to scan-only margin (conservative, never unsafe).

**Implementation path:** A new private method `_elm_margin(symbol, qty, lot_size, price) -> float` on `SpanMarginCalculator`. ELM rate table injected at construction time or sourced from `elm_rates.py`. `get_used_margin` and `get_incremental_margin` sum scan + ELM before applying `margin_rate`.

**TDD anchor:**
- NIFTY futures: ELM = 1.5% x notional; total = scan + ELM ~Rs 195,000 per lot
- BANKNIFTY futures: ELM = 1.5% x notional
- Zero ELM rate -> ELM component = 0, all existing expected values unchanged
- `margin_rate` multiplier applies to the combined (scan + ELM) sum
- Unknown underlying with no ELM rate -> 0 contribution (no exception)

---

### MM10.5 — Exposure Margin

**Scope:** Apply NSE exposure margin as the third and final margin layer.

**Structure:**
```
exposure_margin = exposure_rate x abs(qty) x lot_size x price
total           = (scan_margin + elm + exposure_margin) x margin_rate
```

NSE rates: index futures 2.0%, equity futures 5.0%, sold options 2.0% / 5.0% depending on underlying type.

**Implementation path:** A new private method `_exposure_margin(symbol, qty, lot_size, price) -> float` on `SpanMarginCalculator`. Exposure rates in a new module `core/risk/span/exposure_rates.py`. The three components remain individually traceable within `get_used_margin`.

**TDD anchor:**
- NIFTY futures total: scan (~168,327) + ELM (~27,058) + exposure (~36,078) ~Rs 231,000 per lot
- Each component individually testable with zero rate -> contributes 0
- `get_used_margin` returns sum of all three components x `margin_rate`
- `get_incremental_margin` likewise includes all three components
- Full regression suite green with zero ELM and zero exposure rates

---

## 4. Dependency Graph

```
MM10.1 — Safety Hardening + Protocol v2
  S1: Hard refusal for absent SPAN (fno_runner.py)
  S2: MarginCalculator protocol v2 + retire hasattr
        |
        v
     MM10.2 — Contract-Level RA Accuracy
       prerequisite: instrument model expiry/strike/type audit
       S1: Per-expiry futures RA
       S2: Per-strike option RA
               |
               v
            MM10.3 — Calendar Spread Credits
              prerequisite: expiry visible on position (from MM10.2)
              Leg matching + intra_spread_charge_rs credit
                       |
                       v
                    MM10.4 — ELM
                      elm_rates module
                      Additive ELM component in calculator
                               |
                               v
                            MM10.5 — Exposure Margin
                              exposure_rates module
                              Additive exposure component in calculator
                                       |
                                       v
                                    Production-ready NSE SPAN
                                    (scan + ELM + exposure, spread-credited,
                                     per-contract RA, hard-refusal gate)
```

**Why this order minimises risk:**

**MM10.1 first:** Closes the only known production safety gap before adding any capability. Locking the protocol v2 contract means all subsequent milestones build against a stable interface. No formula change means zero regression risk.

**MM10.2 before MM10.3:** Spread credit matching requires each position's expiry. MM10.2-S1 delivers the per-expiry RA lookup, which necessarily also delivers expiry visibility on the position. MM10.3 depends on this. Combining the prerequisite into the expiry-RA milestone avoids discovering a missing precondition mid-implementation of spread credits.

**MM10.3 before MM10.4:** Not a hard dependency (they touch different calculator methods), but spread credits are the most architecturally novel change in MM10 (portfolio-level grouping). Completing them before introducing additive rate components keeps each review bounded to one conceptual change. An implementer should not be reviewing spread matching logic and ELM rate sourcing in the same diff.

**MM10.4 before MM10.5:** ELM and exposure margin are structurally parallel (`rate x notional`). Implementing ELM first establishes the additive component pattern (method, rate table, inclusion in `get_used_margin` and `get_incremental_margin` sums). MM10.5 follows the same pattern. Sequencing ensures the pattern is already reviewed before it is duplicated.

**The final state** after MM10.5 matches the NSE margin framework exactly: SPAN scan + ELM + exposure margin, with inter-month spread credits applied where applicable.

---

## 5. Architecture Review

### 5.1 ParserRegistry — No change required

Dispatches on `<fileFormat>` verbatim (ADR-010), accepts raw bytes (ADR-009). MM10 introduces no new file formats. All MM10 data is already extracted by `ParserV400`. Feature-frozen.

### 5.2 ParserV400 — No change required

All data needed by MM10.2 and MM10.3 is already extracted: `intra_spread_charge_rs` in `risk_metrics`, `SpanFutureContract` tuples in `snapshot.futures`, `SpanOptionContract` tuples in `snapshot.option_contracts`. The RA reduction formula is validated. Feature-frozen.

### 5.3 SpanSnapshot — No change required

All needed fields exist: `risk_arrays`, `futures`, `option_series`, `option_contracts`, `metadata`. No new DTO fields are needed for any MM10 milestone.

### 5.4 SpanMarginCalculator — Extension only, no redesign

The calculator is the locus of all MM10 capability changes. Each milestone adds one or two new private methods. The public protocol surface is unchanged through MM10.2-MM10.5.

| Milestone | New private method(s) | Public change |
|-----------|----------------------|---------------|
| MM10.1-S2 | None | `get_incremental_margin` promoted to protocol |
| MM10.2-S1 | `_per_expiry_scan_risk(symbol, expiry)` | None |
| MM10.2-S2 | `_per_strike_scan_risk(symbol, expiry, strike, option_type)` | None |
| MM10.3 | `_spread_credit(positions_by_symbol)` | None |
| MM10.4 | `_elm_margin(symbol, qty, lot_size, price)` | None |
| MM10.5 | `_exposure_margin(symbol, qty, lot_size, price)` | None |

The constructor may be extended to accept optional `elm_rates` and `exposure_rates` arguments. Constructor extension is backward-compatible: default to zero rates, preserving all existing tests exactly.

### 5.5 Instrument model — Investigation required before MM10.2

The per-contract RA lookup requires the position's instrument to expose `expiry: date` (for futures) and `expiry + strike + option_type` (for options). Whether the current `Instrument` subclasses expose these is the first task of MM10.2 — an investigation, not a design assumption. If absent, a targeted instrument model extension (add fields, no redesign) is the prerequisite. The fallback design (use underlying-level `scan_risk` when contract not found) means the calculator degrades gracefully if the attribute is unavailable during development.

### 5.6 ExecutionHandler — Minimal change in MM10.1-S2 only

MM10.1-S2 retires the `hasattr` detection at `handler.py:1172-1176` and replaces it with a direct protocol method call. One-line change. No further handler changes across the entire MM10 programme.

### 5.7 PositionTracker — No change required

The calculator already iterates `position_tracker._positions`. The spread credit grouping (MM10.3) groups these by underlying using the same iteration.

### 5.8 PortfolioView — No change required

`PortfolioView` consumes `margin_tracker.get_used_margin(prices)` and `get_exposure(prices)`. These return totals regardless of internal composition. Telemetry keys (`used_margin`, `exposure`) are unchanged.

---

## 6. Risk Assessment

**R1 — Instrument model attribute availability (MM10.2 prerequisite) — MEDIUM**

The position instrument may not expose expiry/strike/option_type in the form the calculator requires, causing a wider instrument model change than anticipated.

*Mitigation:* Explicit investigation task first. The fallback (use underlying-level `scan_risk` if contract not found) means the calculator remains correct regardless of whether the lookup succeeds.

*Rank:* Highest.

---

**R2 — ELM rate data source (MM10.4) — MEDIUM**

ELM rates are published in NSCCL circulars without a machine-readable format. If they change between code update and deployment, the ELM calculation uses a stale rate. Per-underlying equity ELM rates are not uniform.

*Mitigation:* Start with hardcoded constants for NIFTY and BANKNIFTY (1.5%, stable for years). Per-stock ELM is post-MM10 scope. An unknown underlying with no rate contributes 0 (never understates safety).

*Rank:* Second.

---

**R3 — Spread credit matching edge cases (MM10.3) — MEDIUM**

The greedy leg-matching algorithm may not reproduce NSCCL's exact methodology for portfolios with more than two expiries or unequal lot counts across many legs.

*Mitigation:* Implement the conservative version first: match only nearest + second-nearest expiry; credit only up to the minimum matched lot count. External reconciliation against a broker margin calculator (Zerodha/Upstox) before go-live. The fallback (no credit applied) is always safe.

*Rank:* Third.

---

**R4 — Per-strike option RA sign convention (MM10.2-S2) — LOW**

The sign convention for option RA values in `SpanOptionContract.ra` may have subtleties for deeply negative-delta positions that differ from the futures RA path.

*Mitigation:* Validate against a NIFTY ATM call and put from the reference file. Document in the external reconciliation report.

*Rank:* Fourth.

---

**R5 — SPAN schema change — LOW**

NSE releases a new `<fileFormat>` value. The registry raises `UnsupportedSpanSchema`, blocking startup.

*Mitigation:* Existing registry design handles this. `UnsupportedSpanSchema` produces a clear, actionable error. Register a new parser under the new key (ADR-010). Risk is operational (platform stops), never silent.

*Rank:* Fifth.

---

**R6 — Regression on existing margin tests — LOW BY DESIGN**

New calculator methods inadvertently alter existing margin computations.

*Mitigation:* All new methods are additive. Existing tests use hand-built snapshots with no `futures` or `option_contracts` data and zero ELM/exposure rates. Default rates of zero preserve all existing expected values exactly. Full 957-test suite run at every milestone boundary.

*Rank:* Sixth.

---

## 7. Testing Strategy

The MM9.5 philosophy is preserved:

```
Research -> Architecture -> Review -> Implementation -> Review -> Commit -> Documentation
```

---

### MM10.1 — Safety + Protocol v2

| Test type | Content |
|-----------|---------|
| Unit | S1: LIVE F&O with no snapshot -> BLOCK verdict injected -> startup aborts. S2: `MarginTracker` satisfies v2 protocol; `SpanMarginCalculator` satisfies v2 protocol. |
| Regression | Full 957-test suite green. Handler calls `get_incremental_margin` via protocol method directly, not via hasattr. |
| Integration | Composition root with intentionally missing snapshot -> startup abort, clear reason logged. |
| External reconciliation | Not required (no formula change). |

---

### MM10.2 — Contract-Level RA Accuracy

| Test type | Content |
|-----------|---------|
| Unit | Near-month NIFTY futures margin matches underlying-level scan_risk within 0.5%. Far-month NIFTY uses far-month RA (possibly different). NIFTY low-delta OTM call margin < NIFTY futures margin. NIFTY deep ITM call margin close to futures margin. Fallback: absent contract -> underlying-level scan_risk, no exception. |
| Regression | All existing calculator tests use hand-built snapshots with empty `futures`/`option_contracts` -> fallback always taken -> all pass unchanged. Full suite green. |
| Integration | Real June 2026 NSE snapshot -> per-expiry and per-strike margins computed and logged for spot verification. |
| External reconciliation | Compare per-strike option margins against NSCCL or broker reference. Report: `docs/reports/MM10_2_OPTION_RA_RECONCILIATION.md`. |

---

### MM10.3 — Calendar Spread Credits

| Test type | Content |
|-----------|---------|
| Unit | Single position -> credit = 0. Equal-lot calendar spread -> credit = `near_scan + far_scan - intra_spread_charge_rs`. Unequal lots -> credit on minimum matched count. Credit floor: total margin >= 0. NIFTY Rs 425 / BANKNIFTY Rs 1,029 per lot-pair. |
| Regression | All single-position tests -> credit = 0 (no opposite leg) -> all pass. Full suite green. |
| Integration | Portfolio: 1x NIFTY near long + 1x NIFTY far short -> total margin lower than sum of two individual margins by the expected spread credit. |
| External reconciliation | Compare spread-credited margin against a broker margin calculator. Report: `docs/reports/MM10_3_SPREAD_CREDIT_RECONCILIATION.md`. |

---

### MM10.4 — ELM

| Test type | Content |
|-----------|---------|
| Unit | NIFTY futures ELM = 1.5% x notional. Zero ELM rate -> contribution = 0, backward-compatible. ELM + scan sum correctly in `get_used_margin` and `get_incremental_margin`. Unknown underlying with no ELM rate -> 0 contribution. |
| Regression | All existing tests: ELM rate = 0 -> margin unchanged. Full suite green. |
| Integration | Real snapshot + 1.5% ELM -> total (scan + ELM) for NIFTY ~Rs 195,000. |
| External reconciliation | Compare (scan + ELM) against NSCCL published initial margin. Report: `docs/reports/MM10_4_ELM_RECONCILIATION.md`. |

---

### MM10.5 — Exposure Margin

| Test type | Content |
|-----------|---------|
| Unit | NIFTY futures exposure = 2% x notional. All three components sum correctly. Each component individually zero-testable. |
| Regression | All existing tests: exposure rate = 0 -> margin unchanged. Full suite green. |
| Integration | Real snapshot + full rates -> total (scan + ELM + exposure) for NIFTY ~Rs 231,000. |
| External reconciliation | Compare total computed margin against broker-reported initial margin via authenticated API session. This is the final production validation. Report: `docs/reports/MM10_5_TOTAL_MARGIN_RECONCILIATION.md`. |

---

## 8. Engineering Constraints

All MM9.5 invariants are preserved without exception:

| Constraint | MM10 status |
|------------|-------------|
| TDD only | Required. Every slice begins with a failing test. |
| Deterministic behaviour | Required. ADR-003. ELM and exposure rates are constants or archived — never fetched at margin-check time. |
| Immutable snapshots | Required. `SpanSnapshot` remains frozen throughout MM10. |
| Parser remains read-only | Required. `ParserV400` is feature-frozen. |
| No architectural drift | Required. No new top-level abstractions. Additive private methods only. |
| Smallest safe changes | Required. Each milestone modifies a bounded set of files. |
| Feature freeze on certified components | Required. `ParserRegistry`, `ParserV400`, `SpanSnapshot`, `SpanRepository`, `SpanReadiness` are not modified in MM10. |
| Backward compatibility | Required. Zero-rate defaults for ELM and exposure preserve every existing expected value exactly. |

---

## 9. Summary Gap Analysis

| SPAN Component | Status at mm9.5-complete | MM10 Disposition |
|----------------|--------------------------|------------------|
| Parser infrastructure (ParserRegistry, ParserV400) | Implemented | Feature-frozen |
| SpanSnapshot DTO | Implemented | Feature-frozen |
| Scan risk (worst-case RA, 16 scenarios, absolute Rs) | Implemented | Feature-frozen |
| Short option minimum (SOM) | Implemented (0 for NIFTY/BN; parseable for equity) | Feature-frozen |
| SpanFutureContract per-expiry RA (extracted) | Parsed, not consumed | MM10.2-S1 |
| SpanOptionContract per-strike RA (extracted) | Parsed, not consumed | MM10.2-S2 |
| Intra-commodity spread charges (extracted) | Parsed, not consumed | MM10.3 |
| MarginCalculator protocol v2 | Partially (off-protocol via hasattr) | MM10.1-S2 |
| Absent/corrupt SPAN hard refusal | Not implemented (safety gap) | MM10.1-S1 |
| Calendar / inter-month spread credits | Not implemented | MM10.3 |
| ELM (Extreme Loss Margin) | Not implemented | MM10.4 |
| Exposure margin | Not implemented | MM10.5 |
| NOV credit | Not implemented | Deferred post-MM10 |
| Delivery margin | Not implemented | Deferred post-MM10 |
| Inter-commodity spreads | N/A (empty in NSE file) | Not applicable |
| Broker margin reconciliation | Not implemented | Post-MM10 diagnostic |

**Production-ready NSE margin computation** is achieved when MM10.1 through MM10.5 are complete: the calculator computes scan margin + ELM + exposure margin, applies inter-month spread credits where applicable, uses per-contract RA for every position, and refuses to start when SPAN data is absent.
