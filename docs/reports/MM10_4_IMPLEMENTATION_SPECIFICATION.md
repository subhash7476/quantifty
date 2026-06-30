# MM10.4 — NseMarginEngine (Phase 2): Extreme Loss Margin (ELM)
## Implementation Specification

**Date:** 2026-06-30
**Author role:** System Architect
**Status:** For ChatGPT Technical Lead review
**Milestone tag:** `mm10.4-complete` (target)
**Predecessor:** `mm10.3-complete`

---

## 0. Reference Data

### 0a. SPAN XML Verification (Reference file: `nsccl.20260625.i1/nsccl.20260625.i01.spn`)

A full-file grep for all conceivable ELM-related element names was executed against the reference
SPAN file:

```
Pattern: (elm|extreme|extremeLoss|xtrm|eloss) (case-insensitive)
Result:  0 matches across all 3,819 lines of the 218 KB file
```

A complete structural enumeration of the NIFTY `<ccDef>` block confirmed every XML element
present. The full element list is:

```
<cc>, <name>, <group>, <currency>, <riskExponent>, <capAnov>, <procMeth>, <wfprMeth>,
<spotMeth>, <somMeth>, <cmbMeth>, <pfLink> (x3: PHY/FUT/OOP), <adjRate> (x10),
<scanTiers>, <intraTiers>, <interTiers>, <somTiers>, <dSpread> (x153)
```

**Verdict: The NSE PC-SPAN v4.00 XML contains no ELM element.** ELM is not part of the
SPAN risk parameter file.

### 0b. SpanSnapshot `extreme_loss` Key — Null Finding

`span_snapshot.py` line 37 mentions `extreme_loss` in the `risk_metrics` docstring as an
*example* of a possible free-form key. `parser_v400.py` never populates this key; it is never
set in the reference SPAN file. No existing code reads `risk_metrics["extreme_loss"]`.
No reader should conclude that ELM is "already partially in SpanSnapshot."

### 0c. ELM Rate Data — Authoritative Source and Phase 1 Scope

**Authoritative source:** NSE Clearing Corporation Ltd (NSCCL) is the regulatory authority
for F&O margin requirements. The definitive reference for ELM rates is the NSE Clearing
equity derivatives margins page:

```
https://www.nseclearing.com/Risk_Management/Equity_Derivatives/Margins/
```

Rates are also published in NSCCL circulars (downloadable PDFs). The circular number must be
recorded in `elm_rates.py` once verified. NSE Clearing servers were unreachable via direct
HTTP during spec research; the 3% figure below is a best-available candidate from indirect
sources and is **unverified until the implementer confirms from the authoritative page above.**

**ELM rate schedule (Phase 1 scope — index derivatives only):**

| Product category | ELM Rate | Applies to | Status |
|-----------------|----------|-----------|--------|
| Index derivatives (NIFTY, BANKNIFTY) | **3%** of notional | Futures: long + short. Options: short only. | Pending NSCCL verification |
| Stock derivatives | `max(5%, 1.5 × σ × √N)` | Futures: long + short. Options: short only. | Out of scope — Future Extension 1 |
| Expiry-day additional (index short options) | **+2%** | Short index options on expiry day | Out of scope — Future Extension 2 |
| Deep OTM option ELM | TBD from NSCCL | Short positions | Out of scope — Future Extension 3 |
| Long-dated option ELM | TBD from NSCCL | Short positions | Out of scope — Future Extension 4 |

**Phase 1 scope for MM10.4:**
- Index derivatives only: NIFTY, BANKNIFTY
- Single static rate per product category (no volatility computation)
- All out-of-scope rules documented in Section 11 (Future Extensions)

**Implementer action required before coding:** Access the NSE Clearing margins page above,
locate the current ELM schedule for equity derivatives, and record the exact NSCCL circular
number and date as a comment in `elm_rates.py`. Do not write any rate value without this
verification. See **Risk 1**.

**Notional value definition (confirmed from multiple sources):**
```
ELM_notional = underlying_price x lot_size x |qty|
```
For futures, `underlying_price` is the futures contract price (approximates spot with
cost-of-carry). For options, `underlying_price` is the price of the **underlying index**, not
the option premium.

**Calendar spread special ELM rule (NSE, out of scope for Phase 1):**
NSE applies reduced ELM on the far-month leg of a calendar spread (1/3 of notional). Phase 1
charges full ELM on all futures positions. This is conservative: it overestimates margin
requirement but is never unsafe. See **Risk 5**.

---

## 1. Current Architecture

```
CLI / fno_runner.py
        |
        |  span_snapshot: SpanSnapshot
        v
ExecutionHandler.__init__
        |
        |  if span_snapshot is not None:
        v
SpanMarginCalculator(position_tracker, span_snapshot)   <- frozen MM10.2
        |
        |  wrapped by:
        v
NseMarginEngine(span_calc, span_snapshot)               <- MM10.3
        |
        |  implements MarginCalculator Protocol v2
        v
   margin_tracker
        |
        +-- get_exposure(prices, symbol?)  -> notional
        +-- get_used_margin(prices)        -> max(0, SPAN - spread_credit)
        +-- get_incremental_margin(...)    -> per-symbol SPAN estimate
```

**Current margin formula (MM10.3):**
```
get_used_margin = max(0.0, span_margin - spread_credit)
```
where:
- `span_margin = span_calc.get_used_margin(prices)`
- `spread_credit = sum(calendar spread pair credits)` from MM10.3

---

## 2. Objective

Add Extreme Loss Margin (ELM) to `NseMarginEngine`. ELM is a regulatory margin component
mandated by SEBI/NSE, applied as a fixed percentage of the notional value of each F&O position.
It is **additive** to SPAN margin and is **never reduced** by calendar spread credits.

**Primary constraint:** The SPAN subsystem (SpanMarginCalculator, SpanSnapshot, ParserV400,
ParserRegistry, SpanRepository, SpanReadiness) must not change. ELM logic must live
exclusively in `NseMarginEngine`.

**Primary goal:** Integrate ELM without weakening the architectural separation established in
MM10.3. The data-source boundary (SPAN XML vs. NSE circular rates) must be preserved.

---

## 3. Target Architecture

```
CLI / fno_runner.py
        |
        |  span_snapshot: SpanSnapshot
        |  elm_rates: Dict[str, float]      <- NEW: injected from elm_rates.py
        v
ExecutionHandler.__init__
        |
        |  if span_snapshot is not None:
        |
        +-- SpanMarginCalculator(position_tracker, span_snapshot)   <- frozen
        |
        +-- NseMarginEngine(                                         <- MM10.4
                span_calc,
                span_snapshot,
                elm_rates,          <- NEW constructor parameter
            )
                |
                |  implements MarginCalculator Protocol v2
                |
                +-- _span_calc: SpanMarginCalculator    <- SPAN scan risk (unchanged)
                +-- _snapshot: SpanSnapshot              <- spread credit lookup (unchanged)
                +-- _elm_rates: Dict[str, float]         <- NEW: regulatory rate table
                |
                +-- get_used_margin(prices)
                |     = max(0, SPAN - spread_credit) + ELM    <- MM10.4 formula
                |
                +-- _spread_credit(prices) -> float       <- MM10.3 unchanged
                +-- _elm_margin(prices) -> float          <- NEW in MM10.4
```

**Two independent data sources, two independent code paths:**

| Data source | Serves | Who reads it |
|------------|--------|-------------|
| NSE PC-SPAN v4.00 XML (daily download) | SPAN scan risk, spread charges, SOM | `parser_v400.py` -> `SpanSnapshot` -> `SpanMarginCalculator` |
| NSE Clearing circulars (occasional issuance) | ELM rates | `elm_rates.py` -> `NseMarginEngine._elm_rates` |

These sources never merge. `SpanSnapshot` never carries ELM data. `elm_rates.py` never reads
SPAN XML.

---

## 4. Component Responsibilities

### 4a. Frozen — Zero changes permitted

| Component | File | Frozen since |
|-----------|------|-------------|
| ParserRegistry | `core/risk/span/span_parser.py` | MM9.5 |
| ParserV400 | `core/risk/span/parser_v400.py` | MM9.5 |
| SpanSnapshot | `core/risk/span/span_snapshot.py` | MM9.5 |
| SpanRepository | `core/risk/span/span_repository.py` | MM9.5 |
| SpanReadiness | `core/risk/span/span_readiness.py` | MM9.5 |
| SpanMarginCalculator | `core/risk/span/span_calculator.py` | MM10.2 |
| MarginCalculator Protocol v2 | `core/risk/margin_calculator.py` | MM10.1 |

### 4b. New file: `core/risk/elm_rates.py`

Owns the ELM rate table for known underlyings. This is the single location for regulatory
constants derived from NSE Clearing circulars. It must not import from the SPAN subsystem.

**Design: product-category-based representation.**
NSE Clearing groups instruments by product category (INDEX, STOCK), not by individual
underlying. The category is the stable unit: adding a new index underlying (e.g. MIDCPNIFTY)
requires only one line in `_INDEX_UNDERLYINGS`; the rate is inherited from the category.
`INDEX_ELM_RATES` is a derived flat dict for the `NseMarginEngine` constructor — no interface
change to the engine is required.

```python
from typing import Dict, FrozenSet

# Source: NSE Clearing Corporation equity derivatives margins page
#   https://www.nseclearing.com/Risk_Management/Equity_Derivatives/Margins/
#
# ** Rates pending implementer verification — see MM10.4 spec Risk 1. **
# ** Record the NSCCL circular number and date as a comment here once verified. **
# ** Example: NSCCL/CMPT/43028/2019 dated 2019-06-14 — TO BE REPLACED with actual. **

# Category-level rates (single source of truth).
# Stock derivatives ELM (max(5%, 1.5σ√N)) requires a runtime volatility feed
# and is not a static constant — see Future Extension 1.
ELM_RATES_BY_CATEGORY: Dict[str, float] = {
    "INDEX": 0.03,    # Phase 1 scope — TO BE VERIFIED from NSCCL circular
}

# Underlyings covered by Phase 1 (index derivatives only).
# Adding a new index underlying requires only a single entry here.
_INDEX_UNDERLYINGS: FrozenSet[str] = frozenset({"NIFTY", "BANKNIFTY"})

# Flat underlying→rate dict for NseMarginEngine constructor.
# Derived from category rates — do NOT hard-code individual rates here.
INDEX_ELM_RATES: Dict[str, float] = {
    u: ELM_RATES_BY_CATEGORY["INDEX"] for u in _INDEX_UNDERLYINGS
}
```

No computation logic. No SPAN imports. Category rates drive per-underlying rates;
`INDEX_ELM_RATES` is the public export consumed by `handler.py`.

### 4c. Modified: `core/risk/nse_margin_engine.py`

**Constructor change (signature):**
```python
def __init__(
    self,
    span_calc: SpanMarginCalculator,
    span_snapshot: SpanSnapshot,
    elm_rates: Dict[str, float],    # required — no default
):
    self._span_calc = span_calc
    self._snapshot = span_snapshot
    self._elm_rates = dict(elm_rates)   # independent copy, no mutation
```

`elm_rates` is required with no default. Callers must supply it explicitly.
An empty dict `{}` produces ELM = 0 for all positions (valid for tests that predate MM10.4).

**Updated `get_used_margin`:**
```python
def get_used_margin(self, current_prices: Dict[str, float]) -> float:
    span_margin = self._span_calc.get_used_margin(current_prices)
    credit = self._spread_credit(current_prices)
    elm = self._elm_margin(current_prices)
    return max(0.0, span_margin - credit) + elm
```

The `max(0.0, ...)` clamp applies to `(span_margin - credit)` only. ELM is always additive
and never inside the clamp.

**`current_prices` keying convention (critical):**

`current_prices` is keyed by **contract symbol** (e.g., `"NIFTY25JUN25FUT"`, `"NIFTY25JUN2425000CE"`),
not by underlying name. This is confirmed by tracing `handler._check_margin_budget` which builds:
```python
prices = {sym: snap.price for sym, snap in self._price_cache.items()}
```
where `_price_cache` is populated via `update_market_price(signal.symbol, price)` using the
signal's contract symbol. `current_prices.get("NIFTY")` therefore returns `None` for every
real portfolio.

**ELM notional price resolution:**
- **Futures**: use `current_prices.get(sym)` directly — the futures price is the notional
  basis, and `futures_price ≈ underlying_spot` (cost-of-carry basis, negligible for ELM).
- **Options (short)**: the option premium in `current_prices.get(sym)` is wrong (e.g., 150
  vs. NIFTY at 24000). The correct basis is the underlying spot. Derived from the nearest
  futures position on the same underlying already in the portfolio.

**New private method `_elm_margin`:**
```python
def _elm_margin(self, current_prices: Dict[str, float]) -> float:
    pt = self._span_calc.position_tracker

    # Pass 1: derive underlying-spot proxy from futures positions.
    # current_prices is contract-symbol keyed ("NIFTY25JUN25FUT" -> 24005.0),
    # so futures price is the best available proxy for underlying spot.
    underlying_prices: Dict[str, float] = {}
    for sym, pos in pt._positions.items():
        if pos.instrument.type == InstrumentType.FUTURE:
            price = current_prices.get(sym, 0.0)
            if price > 0.0:
                underlying = pos.instrument.underlying
                underlying_prices.setdefault(underlying, price)

    # Pass 2: compute ELM per position.
    total = 0.0
    for sym, pos in pt._positions.items():
        inst = pos.instrument
        underlying = inst.underlying
        elm_rate = self._elm_rates.get(underlying, 0.0)
        if elm_rate == 0.0:
            continue
        is_option = inst.type == InstrumentType.OPTION
        is_short = pos.side.name == "SHORT"
        if is_option and not is_short:
            continue                         # long options: ELM exempt

        if inst.type == InstrumentType.FUTURE:
            price = current_prices.get(sym, 0.0)
        else:
            # Options: use underlying proxy derived in Pass 1.
            price = underlying_prices.get(underlying, 0.0)

        if price == 0.0:
            # Log warning — see Risk 3.
            continue

        lot_size = getattr(inst, "lot_size", None) or inst.multiplier
        qty = pos.quantity                   # always positive magnitude
        total += elm_rate * lot_size * qty * price
    return total
```

Key invariants enforced:
- Long options: skipped (ELM exempt per NSE rules)
- Short options: ELM applied using underlying proxy from futures map
- Futures (long or short): ELM applied using contract's own price from `current_prices`
- Options with no futures in portfolio: price = 0.0, ELM skipped with warning (see Risk 3)
- Unknown underlying (not in `_elm_rates`): ELM = 0

**`get_incremental_margin` — Phase 1 simplification:**

The existing signature `(symbol, quantity, price, lot_size)` does not carry instrument type,
and `symbol` is a contract symbol (e.g., `"NIFTY25JUN25FUT"`), not an underlying name.
`self._elm_rates.get(symbol, 0.0)` would always return 0.0 for contract symbols. Fix: a
private helper that extracts the underlying from the contract symbol by prefix-matching against
the known rate-table keys. This is sufficient for Phase 1 (NIFTY and BANKNIFTY only).

```python
def _resolve_elm_rate(self, symbol: str) -> float:
    """Match contract symbol to elm_rates by prefix (e.g. 'NIFTY25...' -> 'NIFTY')."""
    for underlying, rate in self._elm_rates.items():
        if symbol.startswith(underlying):
            return rate
    return 0.0

def get_incremental_margin(
    self,
    symbol: str,
    quantity: float,
    price: float,
    lot_size: float = 1.0,
) -> float:
    span_incr = self._span_calc.get_incremental_margin(symbol, quantity, price, lot_size=lot_size)
    elm_rate = self._resolve_elm_rate(symbol)
    elm_incr = elm_rate * lot_size * abs(quantity) * price
    return span_incr + elm_incr
```

**Phase 1 known limitation:** `get_incremental_margin` does not carry instrument type so it
cannot distinguish long options (ELM-exempt) from short options. The pre-trade ELM estimate
therefore overestimates for long-option entries. This is conservative (safe) but may cause
pre-trade rejections near the margin limit for long-option strategies. Full resolution is
MM10.5 when instrument-type routing is available in the incremental API.

### 4d. Modified: `core/execution/handler.py`

Import and wire `elm_rates`:

```python
from core.risk.elm_rates import INDEX_ELM_RATES

# Where NseMarginEngine is constructed (handler.py ~line 204):
engine = NseMarginEngine(span_calc, span_snapshot, elm_rates=INDEX_ELM_RATES)
```

No other handler changes.

### 4e. Modified: `tests/risk/test_nse_margin_engine.py`

Add test groups S through AA. All existing groups (A through R) pass unchanged.
Existing tests that construct `NseMarginEngine(calc, snap)` must be updated to
`NseMarginEngine(calc, snap, elm_rates={})` to satisfy the now-required third argument.
The empty dict preserves test semantics: ELM = 0 for all existing tests.

---

## 5. Production Changes — Complete File List

| File | Change | Frozen? |
|------|--------|---------|
| `core/risk/elm_rates.py` | **NEW** — ELM rate table | No |
| `core/risk/nse_margin_engine.py` | Add `elm_rates` param, `_elm_margin`, update `get_used_margin`, update `get_incremental_margin` | No |
| `core/execution/handler.py` | Import `INDEX_ELM_RATES`, pass to `NseMarginEngine` constructor | No |
| `tests/risk/test_nse_margin_engine.py` | Add groups S-AA; update existing test constructors to pass `elm_rates={}` | No |
| `core/risk/span/span_calculator.py` | **ZERO changes** | Frozen MM10.2 |
| `core/risk/span/span_snapshot.py` | **ZERO changes** | Frozen MM9.5 |
| `core/risk/span/parser_v400.py` | **ZERO changes** | Frozen MM9.5 |
| `core/risk/margin_calculator.py` | **ZERO changes** | Frozen MM10.1 |

**Why no parser changes?** ELM originates from NSE Clearing circulars, not from the SPAN XML.
The parser processes SPAN XML. These are two independent data sources. Adding ELM to the parser
would incorrectly couple the sources and violate the frozen-parser constraint.

---

## 6. RED to GREEN TDD Plan

All tests in groups S-AA must be written and confirmed RED before implementation begins.
Groups A-R must remain GREEN throughout.

### Phase S — ELM rate module

```
test_s1_elm_rates_module_exists          # core.risk.elm_rates is importable
test_s2_elm_rates_has_nifty              # INDEX_ELM_RATES["NIFTY"] > 0
test_s3_elm_rates_has_banknifty          # INDEX_ELM_RATES["BANKNIFTY"] > 0
test_s4_elm_rates_are_positive_fractions # all values in (0, 1)
test_s5_elm_rates_does_not_import_span   # no import from core.risk.span.*
```

### Phase T — Constructor wiring

```
test_t1_constructor_accepts_elm_rates           # NseMarginEngine(calc, snap, {}) succeeds
test_t2_constructor_requires_elm_rates          # NseMarginEngine(calc, snap) raises TypeError
test_t3_elm_rates_stored_as_copy                # mutating external dict does not affect engine
```

### Phase U — Zero ELM baseline

```
test_u1_empty_portfolio_elm_is_zero             # no positions -> ELM = 0
test_u2_unknown_underlying_elm_is_zero          # underlying not in elm_rates -> ELM = 0
test_u3_zero_rate_elm_is_zero                   # rate=0.0 in table -> ELM = 0
test_u4_options_no_futures_elm_is_zero          # short options, no futures in portfolio
                                                #   -> underlying_prices map empty
                                                #   -> price = 0.0 -> ELM = 0 (with warning log)
```

### Phase V — Futures ELM

```
test_v1_long_future_elm_applied                 # long future -> ELM > 0
test_v2_short_future_elm_applied                # short future -> ELM > 0
test_v3_future_elm_formula                      # ELM = rate x lot x qty x price (exact)
test_v4_two_futures_elm_additive                # 2 independent positions -> sum of ELMs
test_v5_opposite_futures_elm_additive           # long + short same underlying -> ELM on both
```

### Phase W — Options ELM

```
test_w1_short_call_elm_applied                  # short CALL -> ELM > 0
test_w2_short_put_elm_applied                   # short PUT -> ELM > 0
test_w3_long_call_elm_zero                      # long CALL -> ELM = 0
test_w4_long_put_elm_zero                       # long PUT -> ELM = 0
test_w5_short_option_elm_formula                # ELM = rate x lot x qty x underlying_price
test_w6_mixed_options_only_short_pays           # portfolio: long + short options; only short in ELM
```

### Phase X — Mixed portfolio

```
test_x1_future_plus_short_option_sum            # ELM = future_ELM + short_option_ELM
test_x2_future_plus_long_option                 # ELM = future_ELM only
test_x3_multi_underlying                        # NIFTY + BANKNIFTY -> independent ELMs summed
```

### Phase Y — Spread interaction

```
test_y1_elm_additive_to_spread_reduced_span     # get_used_margin = max(0, SPAN-credit) + ELM
test_y2_spread_credit_does_not_reduce_elm       # credit reduces SPAN only; ELM unchanged
test_y3_span_fully_offset_elm_still_applied     # when span <= credit, ELM still added
```

Concrete target for `test_y1_elm_additive_to_spread_reduced_span` (using NIFTY, rate=0.03,
price=24000, lot=65, 1 lot each leg of a calendar spread):

```python
# Spread credit reduces SPAN margin (existing MM10.3 logic).
# ELM applies to BOTH futures legs (long and short both pay ELM):
expected_elm = 0.03 * 65 * 1 * 24000 * 2   # two legs, each pays full ELM
# Total: max(0, span_after_credit) + expected_elm
assert abs(result - (span_after_credit + expected_elm)) < 0.01
```

### Phase Z — get_incremental_margin includes ELM

```
test_z1_incremental_includes_elm_estimate       # NIFTY25JUN25FUT -> result > SPAN-alone
test_z2_incremental_elm_formula                 # elm_incr = rate x lot x abs(qty) x price
                                                #   (_resolve_elm_rate extracts 'NIFTY' prefix)
test_z3_incremental_elm_zero_for_unknown        # 'RELIANCE25JUN25FUT' -> only SPAN component
                                                #   (no matching prefix in elm_rates)
```

### Phase AA — Architecture guards

```
test_aa1_elm_not_in_span_calculator             # span_calculator.py contains no 'elm' (case-insensitive)
test_aa2_elm_not_in_span_snapshot               # span_snapshot.py has no 'extreme_loss' key assignment
test_aa3_elm_rates_no_span_import               # elm_rates.py imports nothing from core.risk.span
test_aa4_parser_unchanged_since_mm10_2          # parser_v400.py unmodified (git diff check)
```

Implementation:

```python
import pathlib, re

def test_aa1_elm_not_in_span_calculator():
    src = pathlib.Path("core/risk/span/span_calculator.py").read_text()
    assert not re.search(r'\belm\b', src, re.IGNORECASE)

def test_aa2_elm_not_in_span_snapshot():
    src = pathlib.Path("core/risk/span/span_snapshot.py").read_text()
    # Section 0b confirms 'extreme_loss' already appears in a docstring — that is OK.
    # Guard: no runtime *assignment* to risk_metrics["extreme_loss"] exists.
    assert not re.search(r'risk_metrics\[[\'"]extreme_loss[\'"]\]\s*=', src)

def test_aa3_elm_rates_no_span_import():
    src = pathlib.Path("core/risk/elm_rates.py").read_text()
    assert "core.risk.span" not in src
    assert "SpanSnapshot" not in src
    assert "SpanRiskArray" not in src
```

---

## 7. Test Strategy

### 7a. Isolation

Each group tests one invariant in isolation. No group depends on another group's implementation.
Groups S-AA reuse the `_snapshot()` and `_future_calc()` fixtures from existing tests.

### 7b. Regression

Groups A-R must remain GREEN with no modification of existing test logic after MM10.4
implementation. The milestone is not complete if a single existing test changes color.
(Constructor call updates to pass `elm_rates={}` do not count as "modification of test logic.")

### 7c. Architecture enforcement

Groups AA1-AA4 enforce the data-source boundary at the code level. They are not optional.
A GREEN architecture guard is a contract: ELM logic has not leaked into frozen files.

### 7d. Reference regression (post-verification)

Once the ELM rate is officially verified against an NSE Clearing circular, add:

```
test_r2_nifty_elm_matches_nsccl_reference
```

Target values must be hand-computed from the verified rate and real SPAN data, not derived
from the implementation itself. Record the circular number and date in the test comment.

### 7e. Determinism

ELM is a deterministic function: same prices, same portfolio, same rates -> same output.
Extend Group G determinism test with a portfolio containing options to verify ELM determinism.

---

## 8. Risks

### Risk 1 — ELM rate unverified (HIGH)
NSE and NSCCL servers were unreachable during specification research. The 3% figure was
extracted from a search-engine summary of the NSE equity derivatives margins page, not from a
direct page fetch or downloaded circular. The advisor for this spec flagged this explicitly:
"I can't confirm 1.5% from here either — my own recollection leans toward 2% and I'm not
certain." Three different candidate rates appeared in research: 1.5%, 2%, and 3%.

**Mitigation:** Before writing any value into `elm_rates.py`, the implementer (DeepSeek V4)
must open `nseclearing.in/risk-management/equity-derivatives/margins` or download the
relevant NSE Clearing circular and record the exact circular number. This is a BLOCKING
precondition for Phase S-R2 tests. If NSE servers remain unreachable, request the URL from
the Technical Lead.

### Risk 2 — get_incremental_margin overestimates ELM for long options (LOW)
Phase 1 applies ELM to all positions in `get_incremental_margin`, including long options which
are ELM-exempt. Pre-trade margin checks may reject viable long-option trades if portfolio
margin is near the limit.

**Mitigation:** Document as known Phase 1 limitation. `get_used_margin` is correct; only the
pre-trade estimate is conservative. Resolve in MM10.5 when instrument-type routing is
available in the incremental API.

### Risk 3 — Options-only portfolio: ELM silently zero when no futures position present (MEDIUM)
`current_prices` is keyed by contract symbol (confirmed from `handler._check_margin_budget`).
`_elm_margin` derives the underlying-spot proxy for short options from futures positions already
in the portfolio (Pass 1). If the portfolio holds only short options with no futures hedge, the
`underlying_prices` map is empty and `price == 0.0` for every option position → ELM = 0,
underestimating total margin with no exception raised.

**Mitigation:** `_elm_margin` emits a WARNING-level log when `price == 0.0` and `elm_rate > 0`
and skips rather than computing 0.0 silently. For portfolios with both futures and options
(the common case for NIFTY/BANKNIFTY strategies), Pass 1 provides the underlying proxy.
For naked short-option portfolios, the runner must also track the near-month futures price
in `_price_cache`. Enforce in `test_u4`: zero price → ELM = 0, log emitted.

### Risk 4 — Expiry-day additional ELM omitted (LOW for normal operation)
SEBI's November 2024 circular added 2% ELM on short index options on their expiry day.
Phase 1 does not implement this. On expiry days the system understates required margin by
2% of notional for short index options.

**Mitigation:** Acceptable for Phase 1. See Section 11, Extension 2 for the full design.
Positions are typically reduced before expiry in normal operation.

### Risk 5 — Calendar spread 1/3 far-month ELM rule omitted (LOW)
NSE reduces ELM on the far-month futures leg of a calendar spread to 1/3 of notional. Phase 1
applies full ELM to all futures legs, overestimating margin by approximately 2/3 of one leg's
ELM for each matched spread pair.

**Mitigation:** Conservative (overestimates), not unsafe. Resolve in MM10.5 by reusing the
spread-pair matching logic already in `_spread_credit`.

### Risk 6 — Stock derivatives ELM not implemented (MEDIUM for future scope)
Stock derivatives ELM is `max(5%, 1.5σ√N)` — not a static constant. Phase 1 applies 0% ELM
to any underlying not in `_elm_rates`. `ELM_RATES_BY_CATEGORY` reserves the `"STOCK"` key
as the extension point.

**Mitigation:** Explicit scope exclusion. See Section 11, Extension 1 for the full design.

---

## 9. Definition of Done

| Criterion | How to verify |
|-----------|--------------|
| ELM rate officially verified and documented | `elm_rates.py` contains NSE circular number as comment |
| All Phase S-AA tests written RED before implementation | `pytest -k "s or t or u or v or w or x or y or z or aa"` all FAILED |
| All Phase S-AA tests GREEN after implementation | Same invocation — all PASSED |
| All existing groups A-R still GREEN | `pytest tests/risk/test_nse_margin_engine.py` — all PASSED |
| Architecture guards pass | `pytest -k "aa"` — all PASSED |
| `span_calculator.py` unchanged | `git diff mm10.2-complete HEAD -- core/risk/span/span_calculator.py` empty |
| `span_snapshot.py` unchanged | Same — empty diff |
| `parser_v400.py` unchanged | Same — empty diff |
| `margin_calculator.py` unchanged | Same — empty diff |
| `get_used_margin` formula verified | `test_y1` passes with hand-computed expected value |
| Reference regression written | `test_r2_nifty_elm_matches_nsccl_reference` exists with circular number |
| `handler.py` wires `INDEX_ELM_RATES` | Code review: `elm_rates=INDEX_ELM_RATES` at NseMarginEngine construction |

---

## 10. Engineering Constraints for DeepSeek V4

These are structural requirements, not preferences. Any violation causes review rejection.

1. **ELM in NseMarginEngine only.** No ELM logic may appear in `span_calculator.py`,
   `span_snapshot.py`, `parser_v400.py`, `margin_calculator.py`, or any file in
   `core/risk/span/`.

2. **No default for `elm_rates`.** The constructor parameter must be required. Do not write
   `elm_rates: Dict[str, float] = {}` or `elm_rates: Optional[...] = None`. Silent zero-ELM
   is a production safety risk.

3. **ELM is additive, never inside the clamp.** `get_used_margin` must implement exactly:
   `max(0.0, span_margin - credit) + elm` — the `max(0)` applies to `(span - credit)` only.
   ELM can never be negative; do not include it inside the clamp.

4. **Long options excluded.** `_elm_margin` must skip positions where
   `inst.type == InstrumentType.OPTION` and `pos.side.name == "LONG"`.

5. **No mutation of `elm_rates`.** Store a copy: `self._elm_rates = dict(elm_rates)`.

6. **`elm_rates.py` must not import from `core.risk.span.*`.** The data-source boundary is
   enforced by `test_aa3`.

7. **All existing tests must remain GREEN with zero logic modification.** Updating existing
   `NseMarginEngine(calc, snap)` calls to `NseMarginEngine(calc, snap, elm_rates={})` is
   required; this is not a logic modification.

8. **Write tests before implementation.** Confirm RED after each group. Implement. Confirm GREEN.
   Do not write implementation first.

9. **Verify the ELM rate before writing `elm_rates.py`.** If NSE servers remain unreachable,
   request the verified rate from the Technical Lead. Do not use 3% (or any rate) without
   direct confirmation from an official NSE Clearing artifact.

10. **`_elm_margin` must not call SpanMarginCalculator private methods.** Use only
    `span_calc.position_tracker._positions` (same access pattern as `_spread_credit`) and
    the public `InstrumentType` enum.

11. **`current_prices` is contract-symbol keyed — never underlying-keyed.** `_elm_margin`
    must build the underlying→spot map from futures positions in Pass 1 before applying ELM
    to options in Pass 2. Direct `current_prices.get("NIFTY")` returns None for all positions.

12. **`_resolve_elm_rate` must use startswith prefix matching.** `get_incremental_margin`
    receives a contract symbol; `_elm_rates` keys are underlying names. Direct dict lookup
    always returns 0.0 for contract symbols.

---

## 11. Future Extensions (Out of Scope for MM10.4)

The following ELM rules are deliberately excluded from Phase 1. They are documented here so
that future implementers understand what remains and can size the work correctly.

### Extension 1 — Stock Derivatives ELM

**Rule:** ELM for stock F&O is `max(5%, 1.5 × σ × √N)` where σ is the daily volatility of
the underlying and N is the look-back period, both published by NSE Clearing on a rolling
basis via a separate risk file.

**Prerequisite:** A new data pipeline to ingest the NSE Clearing stock-level volatility file.
`ELM_RATES_BY_CATEGORY` already reserves the `"STOCK"` key (commented out in Phase 1) as
the entry point for this work. The per-underlying `_elm_rates` dict in `NseMarginEngine`
stays the same; the loader populates it with dynamic rates at startup.

**Impact files:** `elm_rates.py` (add dynamic loader), `nse_margin_engine.py` (pass
refreshed rates on each computation cycle or accept a callable), new `nsccl_stock_vol.py`
data-feed module.

### Extension 2 — Expiry-Day Additional ELM

**Rule:** SEBI circular dated October 2024 (effective 2024-11-21) mandates an additional 2%
ELM on short index option positions on their weekly expiry day. Combined ELM on expiry day
becomes 5% (3% base + 2% additional) for short index options.

**Prerequisite:** Runtime expiry detection. `_elm_margin` must know the current date and
compare it to each position's `inst.expiry`. The `SpanReadiness` and `SpanSnapshot` layers
already carry expiry data; the engine's clock dependency must be introduced cleanly (inject
`as_of: date` into `get_used_margin` or a dedicated `set_date()` method).

**Impact files:** `nse_margin_engine.py`, `margin_calculator.py` Protocol v2 (if signature
changes — consider whether this breaks the frozen protocol), `test_nse_margin_engine.py`.

**Note:** This rule makes `get_used_margin` non-deterministic across calendar dates for
identical portfolios and prices. The spec for this extension must address how tests handle
date injection.

### Extension 3 — Deep OTM Option ELM

**Rule:** NSE may apply specific ELM treatment for deep out-of-the-money short option
positions where the option premium is negligible but tail risk remains. The exact rule
(minimum notional floor, strike-distance threshold) requires confirmation from a current
NSCCL circular.

**Prerequisite:** NSCCL circular research (this rule was not confirmed during MM10.4 spec
research). Until confirmed, the Phase 1 formula — ELM on full notional for all short options
regardless of moneyness — is conservative and correct as a floor.

**Impact files:** `nse_margin_engine.py` (`_elm_margin` gains a strike-distance condition),
`elm_rates.py` (possible deep-OTM rate table).

### Extension 4 — Long-Dated Option ELM

**Rule:** NSE may apply additional margin requirements for options with far expiries (e.g.,
monthly vs. weekly contracts) to account for higher gamma and vega risk over longer horizons.
The exact rule requires NSCCL circular confirmation.

**Prerequisite:** Same as Extension 3. Expiry-distance logic would be co-located with the
Extension 2 expiry-detection infrastructure.

**Impact files:** `nse_margin_engine.py`, possibly `elm_rates.py` (maturity-bucketed rates).

---

### Extension development order (recommended)

Extension 2 (expiry-day) is the highest regulatory priority given the SEBI effective date
(November 2024). Extensions 3 and 4 require rule confirmation before implementation begins.
Extension 1 (stock derivatives) requires a separate data pipeline and is scoped as a separate
milestone.
