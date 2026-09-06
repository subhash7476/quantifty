# MM10.5 — NseMarginEngine (Phase 3): Exposure Margin (EM)
## Implementation Specification

**Date:** 2026-06-30
**Author role:** System Architect
**Status:** RETIRED (2026-07-01, ADR-012) — Risk 1 resolved as Hypothesis B (H-same); this spec's
`exposure_margin_rates.py` / `_em_margin` design is not implemented. See
`docs/architecture_decisions.md` ADR-012 and `docs/reports/MM10_5_MARGIN_COMPONENT_VERIFICATION.md`.
**Milestone tag:** none — retired, not tagged
**Predecessor:** `mm10.4-complete`

---

## 0. Reference Data

### 0a. SPAN XML Verification

Exposure Margin (EM) was deliberately not searched in the SPAN XML because the architectural
conclusion from MM10.4 is already load-bearing: NSE PC-SPAN v4.00 XML carries only SPAN scan
risk parameters. The MM10.4 Section 0a grep confirmed zero matches for any additional-margin
keywords across all 3,819 lines of the reference file `nsccl.20260625.i01.spn`.

EM is a regulatory margin component defined by NSE Clearing circulars, not by the SPAN risk
parameter file. The SPAN data source and the regulatory-rates data source are independent.
No parser change is required or permitted.

**Verdict: EM does not exist in the NSE PC-SPAN v4.00 XML. No SPAN subsystem change is needed
or allowed.**

### 0b. Clarification of MM10.4 Risk 5 — Mislabeling Corrected

MM10.4 Section 8, Risk 5 stated: *"NSE reduces ELM on the far-month futures leg of a calendar
spread to 1/3 of notional."* The language "ELM" was imprecise; the regulatory source of the
1/3 far-month concession is the **Exposure Margin** circular, not the ELM circular. Confirmed
from NSE Clearing documentation:

> "In case of calendar spread positions in futures contract, exposure margins are levied on
> one third of the value of open position of the far month futures contract."
> — NSE Clearing, equity derivatives margin schedule

This means:
- **ELM (MM10.4)** has NO calendar spread concession. ELM is applied at full rate to both
  legs of a calendar spread. MM10.4 implementation is correct and complete as-is.
- **Exposure Margin (MM10.5)** carries the 1/3 far-month rule. It must be implemented in
  `_em_margin()`, reusing the spread-pair matching logic from `_spread_credit`.

MM10.5 therefore resolves MM10.4 Risk 5, but the fix belongs in EM logic — not in ELM logic.

### 0c. EM Rate Data — Authoritative Source and Phase 1 Scope

**Regulatory authority:** NSE Clearing Corporation Ltd (NSCCL).

**Rate schedule — sourced from NSE Clearing equity derivatives margin schedule, confirmed
from official NSE documentation:**

```
URL: https://www.nseclearing.in/risk-management/equity-derivatives/margins
```

**EM rate schedule:**

| Product category | EM Rate | Applies to | Status |
|-----------------|---------|-----------|--------|
| Index derivatives (NIFTY, BANKNIFTY) | **3%** of notional | Futures: long + short. Options: short only. | REQUIRES VERIFICATION — see Risk 1 |
| Index calendar spread far-month | **1%** (= 1/3 × 3%) | Far-month futures leg only (matched-lot basis) | REQUIRES VERIFICATION — see Risk 1 |
| Stock derivatives | **5% or 1.5σ** of notional (whichever is higher) | Futures: long + short. Options: short only. | Phase 2 — dynamic component out of scope |
| Expiry-day calendar spread removal | No concession on expiry day | Index calendar spreads expiring that day | Phase 2 — effective 2025-02-10 SEBI circular |

**Note on EM vs ELM distinction:** These are two distinct regulatory components, both additive
to SPAN. The NSE Clearing framework defines:

```
Initial Margin (F&O segment) = SPAN Margin + Exposure Margin
Extreme Loss Margin           = separate additional component on top of Initial Margin
```

Combined total upfront margin = SPAN + Exposure Margin + ELM.

After MM10.5, `get_used_margin` correctly implements this full stack:
```
max(0.0, span_margin - spread_credit) + elm + em
```

**Phase 1 scope for MM10.5:**
- Index derivatives only: NIFTY, BANKNIFTY at 3%
- Static far-month calendar spread concession (1/3 of notional, non-expiry days only)
- Expiry-day concession removal deferred to Phase 2

**Notional value definition (consistent with ELM):**
```
EM_notional = price × lot_size × |qty|
```
For futures: `price` is the futures contract price from `current_prices`. For options:
`price` is the underlying index proxy derived from futures positions in Pass 1 (same pattern
as `_elm_margin`).

**REQUIRES VERIFICATION NOTE:** The 3% index rate is confirmed from NSE Clearing sources
accessed via web search during spec research. The NSE Clearing website was unreachable during
this session (timeout). The implementer (DeepSeek V4) must verify the current rate against
the live NSE Clearing page before writing `exposure_margin_rates.py`. If the page remains
unreachable, request the rate from the Technical Lead with a specific circular reference.
Do not write `0.03` into the module without direct confirmation from an official NSE artifact.

### 0d. Data Source Independence

| Data source | Frequency | Serves | Reader |
|------------|-----------|--------|--------|
| NSE PC-SPAN v4.00 XML (daily download) | Daily | SPAN scan risk, intra-spread charges, SOM | `parser_v400.py` → `SpanSnapshot` → `SpanMarginCalculator` |
| NSE Clearing circular (ELM) | Occasional | ELM rates | `elm_rates.py` → `NseMarginEngine._elm_rates` — **FROZEN MM10.4** |
| NSE Clearing circular (EM) | Occasional | EM rates | `exposure_margin_rates.py` → `NseMarginEngine._em_rates` — **NEW** |

These three sources never merge. `SpanSnapshot` never carries EM or ELM data. Neither rates
module imports from the SPAN subsystem. Neither imports from the other.

---

## 1. Current Architecture

```
CLI / fno_runner.py
        |
        |  span_snapshot: SpanSnapshot
        |  elm_rates: Dict[str, float]   <- from elm_rates.py (MM10.4)
        v
ExecutionHandler.__init__
        |
        |  if span_snapshot is not None:
        |
        +-- SpanMarginCalculator(position_tracker, span_snapshot)   <- frozen MM10.2
        |
        +-- NseMarginEngine(                                         <- MM10.4
                span_calc,
                span_snapshot,
                elm_rates,
            )
                |
                |  implements MarginCalculator Protocol v2
                |
                +-- _span_calc: SpanMarginCalculator
                +-- _snapshot: SpanSnapshot
                +-- _elm_rates: Dict[str, float]
                |
                +-- get_used_margin(prices)
                |     = max(0, SPAN - spread_credit) + ELM
                |
                +-- _spread_credit(prices) -> float
                +-- _elm_margin(prices) -> float
                +-- _resolve_elm_rate(symbol) -> float
```

**Current margin formula (MM10.4):**
```
get_used_margin = max(0.0, span_margin - spread_credit) + elm
```
where:
- `span_margin   = span_calc.get_used_margin(prices)`
- `spread_credit = sum(calendar spread pair credits)` — MM10.3
- `elm           = _elm_margin(prices)` — MM10.4

---

## 2. Objective

Add Exposure Margin (EM) to `NseMarginEngine` as the fourth and final standard NSE initial
margin component for index F&O. EM is a regulatory margin component defined by NSE Clearing,
applied as a fixed percentage of the notional value of each F&O position. It is **additive**
to the existing `max(0.0, span_margin - credit) + elm` formula and is **never reduced** by
calendar spread SPAN credits. EM has its own concession mechanism: the far-month futures leg
of a matched calendar spread pair pays 1/3 of the standard rate.

This milestone also **resolves MM10.4 Risk 5** by correctly attributing the 1/3 far-month
concession to EM rather than ELM (see Section 0b).

**Primary constraint:** The SPAN subsystem and all frozen files must not change. EM logic
lives exclusively in `NseMarginEngine` and `exposure_margin_rates.py`.

**After MM10.5, the NSE F&O initial margin engine is complete for index derivatives:**

| Component | Milestone | Formula contribution |
|-----------|-----------|---------------------|
| SPAN Margin | MM10.2 | `span_calc.get_used_margin(prices)` |
| Calendar Spread Credits | MM10.3 | `- spread_credit` (inside clamp) |
| Extreme Loss Margin (ELM) | MM10.4 | `+ elm` (additive, outside clamp) |
| **Exposure Margin (EM)** | **MM10.5** | **`+ em` (additive, outside clamp)** |

---

## 3. Target Architecture

```
CLI / fno_runner.py
        |
        |  span_snapshot: SpanSnapshot
        |  elm_rates: Dict[str, float]    <- from elm_rates.py (unchanged)
        |  em_rates: Dict[str, float]     <- NEW: from exposure_margin_rates.py
        v
ExecutionHandler.__init__
        |
        |  if span_snapshot is not None:
        |
        +-- SpanMarginCalculator(position_tracker, span_snapshot)   <- frozen
        |
        +-- NseMarginEngine(                                         <- MM10.5
                span_calc,
                span_snapshot,
                elm_rates,
                em_rates,              <- NEW constructor parameter
            )
                |
                |  implements MarginCalculator Protocol v2 (unchanged)
                |
                +-- _span_calc: SpanMarginCalculator
                +-- _snapshot: SpanSnapshot
                +-- _elm_rates: Dict[str, float]          <- unchanged
                +-- _em_rates: Dict[str, float]           <- NEW
                |
                +-- get_used_margin(prices)
                |     = max(0, SPAN - spread_credit) + ELM + EM   <- MM10.5
                |
                +-- _spread_credit(prices) -> float       <- unchanged MM10.3
                +-- _elm_margin(prices) -> float           <- unchanged MM10.4
                +-- _resolve_elm_rate(symbol) -> float     <- unchanged MM10.4
                +-- _em_margin(prices) -> float            <- NEW
                +-- _resolve_em_rate(symbol) -> float      <- NEW
```

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
| ELM rates | `core/risk/elm_rates.py` | MM10.4 |

### 4b. New file: `core/risk/exposure_margin_rates.py`

Owns the Exposure Margin rate table for known underlyings. Separate from the frozen
`elm_rates.py`. Must not import from the SPAN subsystem or from `elm_rates.py`.

**Why a new file, not an extension of `elm_rates.py`:**
`elm_rates.py` is frozen as of MM10.4 and cannot be modified. More importantly, ELM and EM
are governed by separate NSCCL circulars with independent update cycles. A rate change in one
does not imply a change in the other. Separate files → separate update points → separate audit
trails. Merging them would couple two independent regulatory sources and obscure which circular
governs which rate.

**Module structure (implementation sketch — rate subject to Section 0c verification):**

```python
"""Exposure Margin rate table for known underlyings.

Source: NSE Clearing equity derivatives margins schedule
    https://www.nseclearing.in/risk-management/equity-derivatives/margins

Category-level rates (single source of truth):
  INDEX: 3% — REQUIRES VERIFICATION against live NSE Clearing page before commit
  STOCK: dynamic max(5%, 1.5σ√N) — Phase 2; only floor recorded here

Calendar spread far-month concession: 1/3 of standard rate (NSE Clearing circular).
Applied by NseMarginEngine._em_margin. This module is data only.
"""

from typing import Dict, FrozenSet

EM_RATES_BY_CATEGORY: Dict[str, float] = {
    "INDEX": 0.03,    # 3% — verify against NSE Clearing page before commit
    "STOCK": 0.05,    # 5% floor — Phase 2; dynamic component out of scope
}

EM_CALENDAR_SPREAD_FRACTION: float = 1.0 / 3.0   # far-month leg pays 1/3 of standard rate

_INDEX_UNDERLYINGS: FrozenSet[str] = frozenset({"NIFTY", "BANKNIFTY"})

INDEX_EM_RATES: Dict[str, float] = {
    u: EM_RATES_BY_CATEGORY["INDEX"] for u in _INDEX_UNDERLYINGS
}
```

No computation logic. No SPAN imports. `INDEX_EM_RATES` is the public export consumed by
`handler.py`. `EM_CALENDAR_SPREAD_FRACTION` documents the NSE concession rule and is
imported by `_em_margin` to avoid hardcoding `1/3` in the engine.

**Dependency pattern note:** `em_rates` (the per-underlying rate map) is constructor-injected
for testability — it varies per deployment and must be mockable. `EM_CALENDAR_SPREAD_FRACTION`
is a *fixed regulatory constant* (NSE circular mandates exactly 1/3, not a configurable
fraction) and is imported at the call site instead. This is intentionally asymmetric:
injectable = per-deployment config; imported constant = regulatory invariant. Architecture
guard `test_ll1` verifies that `exposure_margin_rates` is never imported from `core.risk.span.*`
or `core.risk.elm_rates`.

### 4c. Modified: `core/risk/nse_margin_engine.py`

**Constructor change (signature):**
```python
def __init__(
    self,
    span_calc: SpanMarginCalculator,
    span_snapshot: SpanSnapshot,
    elm_rates: Dict[str, float],    # required — unchanged from MM10.4
    em_rates: Dict[str, float],     # required — NEW, no default
):
    self._span_calc = span_calc
    self._snapshot = span_snapshot
    self._elm_rates = dict(elm_rates)
    self._em_rates = dict(em_rates)    # NEW — independent copy
```

Both parameters required, no defaults. An empty dict `{}` produces zero ELM or EM (valid for
tests that predate their respective milestones).

**Updated `get_used_margin`:**
```python
def get_used_margin(self, current_prices: Dict[str, float]) -> float:
    span_margin = self._span_calc.get_used_margin(current_prices)
    credit = self._spread_credit(current_prices)
    elm = self._elm_margin(current_prices)
    em = self._em_margin(current_prices)
    return max(0.0, span_margin - credit) + elm + em
```

The `max(0.0, ...)` clamp applies to `(span_margin - credit)` only. Both ELM and EM are
always additive and never inside the clamp.

**`current_prices` keying convention (unchanged from MM10.4):**

`current_prices` is keyed by contract symbol (e.g., `"NIFTY25JUN25FUT"`), not by underlying
name. `current_prices.get("NIFTY")` returns `None` for every real portfolio. `_em_margin`
must derive the underlying-spot proxy from futures positions in Pass 1, exactly as `_elm_margin`
does.

**New private method `_em_margin` — three-pass algorithm:**

Pass 1: derive underlying-spot proxy from futures (identical to `_elm_margin`).
Pass 2: compute full EM for all qualifying positions at the standard rate.
Pass 3: apply 1/3 far-month calendar spread concession using the same pair-matching
algorithm as `_spread_credit`.

```python
def _em_margin(self, current_prices: Dict[str, float]) -> float:
    from core.risk.exposure_margin_rates import EM_CALENDAR_SPREAD_FRACTION
    pt = self._span_calc.position_tracker

    # Pass 1: derive underlying-spot proxy from futures.
    underlying_prices: Dict[str, float] = {}
    for sym, pos in pt._positions.items():
        if pos.instrument.type == InstrumentType.FUTURE:
            price = current_prices.get(sym, 0.0)
            if price > 0.0:
                underlying = pos.instrument.underlying
                underlying_prices.setdefault(underlying, price)

    # Pass 2: full EM for all qualifying positions.
    total = 0.0
    for sym, pos in pt._positions.items():
        inst = pos.instrument
        itype = inst.type
        if itype not in (InstrumentType.FUTURE, InstrumentType.OPTION):
            continue
        underlying = inst.underlying
        em_rate = self._em_rates.get(underlying, 0.0)
        if em_rate == 0.0:
            continue
        is_option = itype == InstrumentType.OPTION
        is_short = pos.side.name == "SHORT"
        if is_option and not is_short:
            continue   # long options: EM exempt

        price = (current_prices.get(sym, 0.0)
                 if itype == InstrumentType.FUTURE
                 else underlying_prices.get(underlying, 0.0))
        if price == 0.0:
            continue   # emit WARNING log (same Risk 3 pattern as _elm_margin)

        lot_size = getattr(inst, "lot_size", None) or inst.multiplier
        total += em_rate * lot_size * pos.quantity * price

    # Pass 3: subtract 2/3 excess EM for matched far-month calendar spread futures legs.
    # Pass 2 charged full rate for every futures leg. Far-month matched legs pay only
    # 1/3 rate (EM_CALENDAR_SPREAD_FRACTION). Reduction = 2/3 × rate × lot × lots × price.
    futures_by_underlying: Dict[str, Dict[date, float]] = defaultdict(
        lambda: defaultdict(float))
    future_prices_by_expiry: Dict[str, Dict[date, float]] = defaultdict(dict)
    lot_sizes: Dict[str, float] = {}

    for sym, pos in pt._positions.items():
        inst = pos.instrument
        if inst.type != InstrumentType.FUTURE:
            continue
        underlying = inst.underlying
        if self._em_rates.get(underlying, 0.0) == 0.0:
            continue
        expiry = inst.expiry
        signed_qty = pos.quantity if pos.side.name == "LONG" else -pos.quantity
        futures_by_underlying[underlying][expiry] += signed_qty
        price = current_prices.get(sym, 0.0)
        if price > 0.0:
            future_prices_by_expiry[underlying][expiry] = price
        if underlying not in lot_sizes:
            lot_sizes[underlying] = getattr(inst, "lot_size", None) or inst.multiplier

    em_reduction = 0.0
    for underlying, expiry_map in futures_by_underlying.items():
        expiries = sorted(expiry_map.keys())
        if len(expiries) < 2:
            continue
        em_rate = self._em_rates.get(underlying, 0.0)
        if em_rate == 0.0:
            continue
        lot_size = lot_sizes.get(underlying, 1.0)
        remaining = {e: expiry_map[e] for e in expiries}

        for i in range(len(expiries)):
            e_i = expiries[i]
            q_i = remaining[e_i]
            if q_i == 0.0:
                continue
            for j in range(i + 1, len(expiries)):
                e_j = expiries[j]
                q_j = remaining[e_j]
                if q_j == 0.0:
                    continue
                if (q_i > 0 and q_j > 0) or (q_i < 0 and q_j < 0):
                    continue   # same-side: not a spread

                n_matched = min(abs(q_i), abs(q_j))
                if n_matched == 0.0:
                    continue

                # e_j is always the far-month (j > i, expiries sorted ascending).
                far_price = future_prices_by_expiry[underlying].get(e_j, 0.0)
                if far_price > 0.0:
                    excess = (1.0 - EM_CALENDAR_SPREAD_FRACTION) * em_rate * lot_size * n_matched * far_price
                    em_reduction += excess

                sign_i = 1 if q_i > 0 else -1
                sign_j = 1 if q_j > 0 else -1
                remaining[e_i] -= n_matched * sign_i
                remaining[e_j] -= n_matched * sign_j
                q_i = remaining[e_i]
                if q_i == 0.0:
                    break

    return max(0.0, total - em_reduction)
```

**Why `_em_margin` is not a clone of `_elm_margin`:**

The two methods share structural shape but are not equivalent:
- `_elm_margin`: two passes; no calendar spread adjustment; full rate on all futures
- `_em_margin`: three passes; Pass 3 applies the 1/3 far-month reduction to matched pairs

A parameterised helper `_pct_margin(rates, apply_spread_concession)` would need a conditional
branch to toggle Pass 3, papering over a real regulatory difference. Separate named methods
with clear regulatory purpose are simpler and more auditable. An architecture guard in
Phase LL catches any attempt to merge them.

**New private method `_resolve_em_rate`:**
```python
def _resolve_em_rate(self, symbol: str) -> float:
    for underlying, rate in self._em_rates.items():
        if symbol.startswith(underlying):
            return rate
    return 0.0
```
Same prefix-matching pattern as `_resolve_elm_rate`. Used only by `get_incremental_margin`.

**Updated `get_incremental_margin`:**
```python
def get_incremental_margin(
    self,
    symbol: str,
    quantity: float,
    price: float,
    lot_size: float = 1.0,
) -> float:
    span_incr = self._span_calc.get_incremental_margin(
        symbol, quantity, price, lot_size=lot_size,
    )
    elm_rate = self._resolve_elm_rate(symbol)
    elm_incr = elm_rate * lot_size * abs(quantity) * price
    em_rate = self._resolve_em_rate(symbol)
    em_incr = em_rate * lot_size * abs(quantity) * price
    return span_incr + elm_incr + em_incr
```

**Phase 1 known limitation (carried forward from MM10.4 Risk 2):**
`get_incremental_margin` still cannot distinguish long options from short options. For
long-option pre-trade checks, both ELM and EM are overestimated (conservative). See
Section 11, Extension 1 for the Protocol v3 resolution path.

### 4d. Modified: `core/execution/handler.py`

Import and wire `em_rates`:

```python
from core.risk.elm_rates import INDEX_ELM_RATES
from core.risk.exposure_margin_rates import INDEX_EM_RATES    # NEW

# Where NseMarginEngine is constructed:
engine = NseMarginEngine(
    span_calc,
    span_snapshot,
    elm_rates=INDEX_ELM_RATES,
    em_rates=INDEX_EM_RATES,     # NEW
)
```

No other handler changes.

### 4e. Modified: `tests/risk/test_nse_margin_engine.py`

Add test groups BB through LL. All existing groups (A through AA) pass unchanged.
Existing tests that construct `NseMarginEngine(calc, snap, elm_rates={})` must be updated to
`NseMarginEngine(calc, snap, elm_rates={}, em_rates={})` to satisfy the now-required fourth
argument. The empty dict preserves all existing test semantics: EM = 0.

---

## 5. Production Changes — Complete File List

| File | Change | Frozen? |
|------|--------|---------|
| `core/risk/exposure_margin_rates.py` | **NEW** — EM rate table and calendar spread fraction constant | No |
| `core/risk/nse_margin_engine.py` | Add `em_rates` param, `_em_margin`, `_resolve_em_rate`; update `get_used_margin` and `get_incremental_margin` | No |
| `core/execution/handler.py` | Import `INDEX_EM_RATES`; pass to `NseMarginEngine` constructor | No |
| `tests/risk/test_nse_margin_engine.py` | Add groups BB-LL; update existing test constructors to pass `em_rates={}` | No |
| `core/risk/elm_rates.py` | **ZERO changes** | Frozen MM10.4 |
| `core/risk/span/span_calculator.py` | **ZERO changes** | Frozen MM10.2 |
| `core/risk/span/span_snapshot.py` | **ZERO changes** | Frozen MM9.5 |
| `core/risk/span/parser_v400.py` | **ZERO changes** | Frozen MM9.5 |
| `core/risk/margin_calculator.py` | **ZERO changes** | Frozen MM10.1 |

**Why no parser changes?** EM originates from NSE Clearing circulars, not the SPAN XML.
Adding EM to the parser would incorrectly couple the two sources and violate the frozen-parser
constraint.

**Why no `elm_rates.py` changes?** It is frozen. ELM and EM are independently regulated at
different rates with different concession structures. They must remain separate files.

---

## 6. RED to GREEN TDD Plan

All tests in groups BB-LL must be written and confirmed RED before implementation begins.
Groups A-AA must remain GREEN throughout.

### Phase BB — EM rate module

```
test_bb1_em_rates_module_exists           # core.risk.exposure_margin_rates is importable
test_bb2_em_rates_has_nifty               # INDEX_EM_RATES["NIFTY"] > 0
test_bb3_em_rates_has_banknifty           # INDEX_EM_RATES["BANKNIFTY"] > 0
test_bb4_em_rates_are_positive_fractions  # all values in (0, 1)
test_bb5_em_rate_differs_from_elm_rate    # INDEX_EM_RATES["NIFTY"] != INDEX_ELM_RATES["NIFTY"]
                                          #   (3% vs 2% — distinct components)
test_bb6_em_rates_no_span_import          # no import from core.risk.span.*
test_bb7_em_rates_no_elm_import           # no import from core.risk.elm_rates
test_bb8_calendar_spread_fraction         # EM_CALENDAR_SPREAD_FRACTION == pytest.approx(1/3)
```

### Phase CC — Constructor wiring

```
test_cc1_constructor_accepts_em_rates          # NseMarginEngine(calc, snap, {}, {}) succeeds
test_cc2_constructor_requires_em_rates         # NseMarginEngine(calc, snap, elm_rates={})
                                               #   raises TypeError (missing em_rates)
test_cc3_em_rates_stored_as_copy               # mutating external dict after construction
                                               #   does not affect engine
test_cc4_elm_behavior_unchanged_by_em          # engine with elm_rates={"NIFTY": 0.02},
                                               #   em_rates={} -> EM = 0; ELM formula unchanged
```

### Phase DD — Zero EM baseline

```
test_dd1_empty_portfolio_em_is_zero            # no positions -> EM = 0
test_dd2_unknown_underlying_em_is_zero         # underlying not in em_rates -> EM = 0
test_dd3_empty_em_rates_em_is_zero             # em_rates={} -> EM = 0 for all positions
test_dd4_long_option_em_is_zero                # long call or long put -> EM = 0
                                               #   regardless of em_rates value
```

### Phase EE — Index futures EM

```
test_ee1_long_future_em_applied                # long future -> EM > 0
test_ee2_short_future_em_applied               # short future -> EM > 0
test_ee3_future_em_formula                     # EM = rate × lot × qty × price (exact)
test_ee4_two_futures_em_additive               # 2 independent futures -> sum of EMs
test_ee5_opposite_futures_em_additive          # long + short same underlying -> EM on both
                                               #   (no netting; both sides pay full EM)
```

Concrete formula for `test_ee3_future_em_formula`:
```python
# NIFTY long future: price=24000, lot=75, qty=1, em_rate=0.03
expected_em = 0.03 * 75 * 1 * 24000   # = 54_000.0
assert abs(engine._em_margin(prices) - expected_em) < 0.01
```

### Phase FF — Index options EM

```
test_ff1_short_call_em_applied                 # short CALL -> EM > 0 (underlying proxy)
test_ff2_short_put_em_applied                  # short PUT -> EM > 0
test_ff3_long_call_em_zero                     # long CALL -> EM = 0 (exempt)
test_ff4_long_put_em_zero                      # long PUT -> EM = 0 (exempt)
test_ff5_short_option_em_formula               # EM = rate × lot × qty × underlying_price
                                               #   where underlying_price from Pass 1 proxy
test_ff6_options_only_portfolio_em_zero        # short options, no futures in portfolio
                                               #   -> underlying_prices map is empty
                                               #   -> price = 0.0 -> EM = 0 (warning logged)
```

### Phase GG — Mixed portfolio

```
test_gg1_future_plus_short_option              # EM = future_EM + short_option_EM
test_gg2_future_plus_long_option               # EM = future_EM only (long option exempt)
test_gg3_multi_underlying                      # NIFTY + BANKNIFTY -> independent EMs summed
```

### Phase HH — Calendar spread 1/3 far-month EM concession

This phase directly resolves MM10.4 Risk 5.

```
test_hh1_single_leg_no_concession              # 1 futures position, no opposing leg -> full EM
test_hh2_calendar_spread_near_pays_full        # near-month leg -> full EM (3%)
test_hh3_calendar_spread_far_pays_one_third    # far-month opposing leg -> 1/3 EM (1%)
test_hh4_calendar_spread_total_formula         # near_EM + far_EM verified exactly:
                                               #   rate*lot*1*near_price + (1/3)*rate*lot*1*far_price
test_hh5_partial_match_reduces_only_matched    # 3 near lots + 1 far lot (opposite side):
                                               #   1 far lot at 1/3 EM, 2 remaining near at full
test_hh6_same_side_no_concession               # long near + long far (same direction) -> no spread
                                               #   -> both legs pay full EM
test_hh7_options_ineligible_for_concession     # spread-pair futures + short options:
                                               #   futures get 1/3 concession on far month;
                                               #   options pay full EM via underlying proxy
```

Concrete formula for `test_hh4_calendar_spread_total_formula`:
```python
# NIFTY calendar spread: 1 lot long near, 1 lot short far
# near_price=24000, far_price=24200, lot=75, em_rate=0.03
near_em  = 0.03 * 75 * 1 * 24000              # = 54_000.0  (full rate)
far_em   = (1.0/3.0) * 0.03 * 75 * 1 * 24200  # = 18_150.0  (1/3 rate)
expected = near_em + far_em                    # = 72_150.0
assert abs(engine._em_margin(prices) - expected) < 0.01
```

### Phase II — Component independence

```
test_ii1_em_additive_to_spread_reduced_span    # get_used_margin = max(0,SPAN-credit)+ELM+EM
test_ii2_span_credit_does_not_reduce_em        # SPAN credit affects SPAN only; EM unchanged
test_ii3_span_fully_offset_em_still_applied    # when span <= credit, EM is still fully added
test_ii4_elm_and_em_are_independent            # changing em_rates does not alter ELM;
                                               #   changing elm_rates does not alter EM
test_ii5_em_spread_concession_independent_of_span_credit
                                               # EM 1/3 concession and SPAN spread credit are
                                               #   computed independently for same spread pair
```

Concrete target for `test_ii1`:
```python
# NIFTY calendar spread: near-long + far-short at price=24000/24200, lot=75
elm  = 0.02 * 75 * 1 * 24000 * 2           # ELM: both legs, no concession
em   = (0.03*75*1*24000                     # near leg: full EM
      + (1.0/3.0)*0.03*75*1*24200)          # far leg: 1/3 EM
expected = max(0.0, span_margin - credit) + elm + em
assert abs(result - expected) < 0.01
```

### Phase JJ — `get_incremental_margin` includes EM

```
test_jj1_incremental_includes_em_estimate      # NIFTY25JUN25FUT -> result > SPAN + ELM alone
test_jj2_incremental_em_formula                # em_incr = rate × lot × abs(qty) × price
test_jj3_incremental_em_zero_for_unknown       # "RELIANCE25JUN25FUT" -> only SPAN + ELM
test_jj4_incremental_total_formula             # total = SPAN_incr + ELM_incr + EM_incr (exact)
```

### Phase KK — Determinism

```
test_kk1_em_deterministic_same_inputs          # _em_margin called twice on same args -> identical
test_kk2_em_deterministic_with_spread_pair     # calendar spread portfolio -> same EM both calls
test_kk3_full_margin_deterministic             # get_used_margin called twice -> identical total
```

### Phase LL — Architecture guards

```
test_ll1_em_rates_no_span_import               # exposure_margin_rates.py: no core.risk.span import
test_ll2_em_rates_no_elm_import                # exposure_margin_rates.py: no elm_rates import
test_ll3_em_not_in_span_calculator             # span_calculator.py: no 'em' or 'exposure' token
test_ll4_em_not_in_span_snapshot               # span_snapshot.py: no runtime EM key assignment
test_ll5_elm_rates_unchanged_from_mm10_4       # git diff mm10.4-complete HEAD -- core/risk/elm_rates.py
                                               #   returns empty
test_ll6_parser_unchanged_from_mm10_2          # git diff mm10.2-complete HEAD -- parser_v400.py
                                               #   returns empty
```

Implementation skeleton:

```python
import pathlib, re, subprocess

def test_ll1_em_rates_no_span_import():
    src = pathlib.Path("core/risk/exposure_margin_rates.py").read_text()
    assert "core.risk.span" not in src
    assert "SpanSnapshot" not in src

def test_ll2_em_rates_no_elm_import():
    src = pathlib.Path("core/risk/exposure_margin_rates.py").read_text()
    assert "elm_rates" not in src

def test_ll3_em_not_in_span_calculator():
    src = pathlib.Path("core/risk/span/span_calculator.py").read_text()
    assert not re.search(r'\bem\b', src, re.IGNORECASE)
    assert not re.search(r'\bexposure\b', src, re.IGNORECASE)

def test_ll5_elm_rates_unchanged_from_mm10_4():
    result = subprocess.run(
        ["git", "diff", "mm10.4-complete", "HEAD", "--",
         "core/risk/elm_rates.py"],
        capture_output=True, text=True,
    )
    assert result.stdout.strip() == "", "elm_rates.py was modified after MM10.4 freeze"
```

---

## 7. Test Strategy

### 7a. Isolation

Each group tests one invariant in isolation. No group depends on another group's implementation.
Groups BB-LL reuse the `_snapshot()` and `_future_calc()` fixtures from existing tests.
Phase HH requires a two-expiry futures fixture; a new helper
`_two_expiry_calc(pt, snap, near_exp, far_exp, near_price, far_price)` may be introduced
locally in the test file (does not count as modifying existing test logic).

### 7b. Regression

Groups A-AA must remain GREEN with zero logic modification. Updating existing constructor
calls from `NseMarginEngine(calc, snap, elm_rates={})` to
`NseMarginEngine(calc, snap, elm_rates={}, em_rates={})` does not count as logic modification.

### 7c. Architecture enforcement

Groups LL1-LL6 enforce data-source boundaries at the code level. They are not optional.
A GREEN LL guard is a contract: EM logic has not leaked into frozen files; `elm_rates.py`
has not been modified post-MM10.4.

### 7d. Reference regression (post-verification)

Once the EM rate is verified against the live NSE Clearing page, add:
```
test_r3_nifty_em_matches_nsccl_reference
```
Values must be hand-computed from the verified rate and real SPAN data, not derived from the
implementation itself. Record the circular number and date in the test comment. Separately
hand-compute the calendar spread concession and verify it with a Phase HH reference test.

### 7e. Determinism

EM is a deterministic function. Phase KK enforces this. A calendar spread portfolio (KK2) is
included because the three-pass algorithm in `_em_margin` is more complex than `_elm_margin`
and must produce identical results on repeated calls.

### 7f. ELM and EM independence

`test_ii4_elm_and_em_are_independent` verifies that modifying `em_rates` at construction
does not change the ELM component, and vice versa. This guards against accidental coupling
of the two rate dictionaries inside `get_used_margin`.

---

## 8. Risks

### Risk 1 — EM rate and component count are UNVERIFIED — conflicting evidence found (HIGH)

During spec research the NSE Clearing website timed out on every fetch attempt. Rates were
assembled from web-search summaries (lowest-confidence source class). Two secondary sources
found during research contradict the three-component stacking model this spec assumes:

| Source | Reported structure | Index EM rate |
|--------|-------------------|---------------|
| Fyers margin explainer | SPAN + Exposure Margin (two components, no ELM line) | **2%** |
| markettrade.in | Total Margin = SPAN + Exposure Margin (two components) | not stated |
| NSE search summaries | Three components: SPAN + EM + ELM separately | **3%** |

These are genuinely conflicting. Two outcomes are possible:
- **Hypothesis A (spec assumes):** ELM and EM are independent components stacked additively.
  Index EM = 3%. Total = SPAN + EM(3%) + ELM(2%).
- **Hypothesis B:** "Exposure Margin" is the umbrella label for what this codebase calls ELM + EM
  combined. Index EM = 2% and no separate ELM on F&O. MM10.4's `_elm_margin` and this spec's
  `_em_margin` would double-count.

**The discriminating check** (one authoritative source resolves both unknowns):
> Fetch an *itemized* margin breakup for one NIFTY futures lot from Zerodha SPAN or Samco
> margin calculator. If the breakup shows three line-items (SPAN / Exposure Margin / ELM)
> with EM ≈ 3% → Hypothesis A confirmed. If it shows only two line-items with EM ≈ 2% →
> Hypothesis B; MM10.4 must be revisited before MM10.5 proceeds.

Alternatively, the NSCCL circular list at
`https://www.nseclearing.in/risk-management/equity-derivatives/circulars` contains the
explicit ELM and EM circular texts — the Technical Lead should download both and confirm they
specify separate additive components.

**Mitigation:** Section 10, Constraint 9 mandates implementer verification before writing
`exposure_margin_rates.py`. Do not proceed with MM10.5 implementation until the discriminating
check is resolved. If Hypothesis B holds, escalate to the System Architect before any code
is written — this changes the MM10.4 formula, not just MM10.5.

**2026-07-01 update:** Upstox `/charges/margin` API evidence sharpens this risk but does not
close it — see `docs/reports/MM10_5_ARCHITECTURE_REASSESSMENT.md`. Upstox's own field docs
describe `exposure_margin` as "based on ELM percentage values provided by exchange," and all
sampled responses reconcile exactly to `span_margin + exposure_margin` with no residual —
consistent with Hypothesis B (H-same) but not conclusive, since the endpoint returns pre-trade
blocked margin only and could simply be omitting an end-of-day ELM component. MM10.5 remains
BLOCKED pending the primary-source discriminator described in that report (itemized NIFTY
futures breakdown: two non-SPAN components → collapse MM10.4/MM10.5; three → proceed).

**2026-07-01 update — RESOLVED as Hypothesis B (H-same):**
`docs/reports/MM10_5_MARGIN_COMPONENT_VERIFICATION.md` closes this risk. SEBI's own
risk-management history page states ELM "replaces the terms 'exposure margin' and 'second line
of defence'," and NSE's current MG-12/MG-13 clearing report field lists itemize only SPAN
Margin, Extreme Loss Margin, Delivery Margin, and Margin on Consolidated Crystallized
Obligation — no separate Exposure Margin line exists in any current F&O clearing report.
Two-component discriminator outcome: **confirmed** (SPAN + ELM only; no independent EM). This
falsifies Hypothesis A and this spec's premise that Index EM (3%) stacks additively on top of
ELM (2%). `elm_rates.py` / `_elm_margin` (MM10.4) is already the complete implementation of
this regulatory charge; `exposure_margin_rates.py` and `_em_margin` as specified in this
document must not be written — doing so would double-count. ADR-011
(`docs/architecture_decisions.md`) has been updated with this closure.

Sourcing caveat: the above was recovered via a reader-proxy fetch of nseindia.com, not a direct
browser render (nseindia.com blocked WebFetch and the Chrome browser-automation extension was
unavailable at research time). The Technical Lead has requested a live-browser open of the
MG-12/MG-13 report page with a PDF/screenshot archived to `docs/reports/` as a final sanity
check before MM10.5 is formally retired via a dedicated ADR. That check and the formal
retirement ADR are outstanding — this spec should be treated as superseded/inactive in the
interim, not as a green light to implement Section 0c/6's EM rate table.

### Risk 2 — `get_incremental_margin` overestimates EM for long options (LOW)
Identical to MM10.4 Risk 2 for ELM. No instrument type available in the incremental API.

**Mitigation:** Document as Phase 1 known limitation. `get_used_margin` is correct. See
Section 11, Extension 1 for the Protocol v3 path.

### Risk 3 — Options-only portfolio: EM silently zero when no futures present (MEDIUM)
Identical to MM10.4 Risk 3. `_em_margin` builds the underlying-spot proxy from futures in
Pass 1. A naked short-option portfolio with no futures provides no proxy → EM = 0.

**Mitigation:** `_em_margin` emits WARNING-level log when price = 0.0 and em_rate > 0.
`test_ff6` enforces this: EM = 0 + log emitted. The runner must track near-month futures
prices in `_price_cache` for naked short-option portfolios.

### Risk 4 — Expiry-day calendar spread removal not implemented (LOW)
SEBI circular effective 2025-02-10: no calendar spread EM concession on expiry day for
expiring contracts. Phase 1 always grants the 1/3 concession, so on expiry day the system
underestimates required EM for calendar spreads where the near-month is expiring.

**Mitigation:** The error is bounded: maximum understatement = 2/3 × em_rate × notional of
the near-month expiring leg only. Positions are typically closed before expiry. See Section 11,
Extension 2 for the design.

### Risk 5 — Stock derivatives EM not implemented (MEDIUM for future scope)
Stock EM is `max(5%, 1.5σ√N)` — not a static constant. Phase 1 applies 0% EM to any
underlying not in `em_rates`. `EM_RATES_BY_CATEGORY["STOCK"]` is the reserved extension point.

**Mitigation:** Explicit scope exclusion. See Section 11, Extension 3.

### Risk 6 — Pass 3 two-step floating-point accumulation (LOW)
Pass 2 charges full EM; Pass 3 subtracts the excess. Two operations accumulate floating-point
error. For portfolios with up to 20 spread pairs at typical lot sizes, accumulated error is
sub-paisa and negligible. `max(0.0, total - em_reduction)` guards against negative output.

**Mitigation:** An alternative single-pass implementation that directly applies 1/3 rate to
far-month legs is equally valid and may be preferred by the implementer; the spec permits
either approach as long as Phase HH formula assertions pass.

---

## 9. Definition of Done

| Criterion | How to verify |
|-----------|--------------|
| EM rate verified against live NSE Clearing page | `exposure_margin_rates.py` contains URL and circular reference |
| All Phase BB-LL tests written RED before implementation | `pytest -k "bb or cc or dd or ee or ff or gg or hh or ii or jj or kk or ll"` — all FAILED |
| All Phase BB-LL tests GREEN after implementation | Same invocation — all PASSED |
| All existing groups A-AA still GREEN | `pytest tests/risk/test_nse_margin_engine.py` — all PASSED |
| Architecture guards pass | `pytest -k "ll"` — all PASSED |
| `span_calculator.py` unchanged | `git diff mm10.2-complete HEAD -- core/risk/span/span_calculator.py` empty |
| `span_snapshot.py` unchanged | Same — empty diff |
| `parser_v400.py` unchanged | Same — empty diff |
| `margin_calculator.py` unchanged | Same — empty diff |
| `elm_rates.py` unchanged | `git diff mm10.4-complete HEAD -- core/risk/elm_rates.py` empty |
| `get_used_margin` formula verified | `test_ii1` passes with hand-computed expected value |
| Calendar spread concession formula verified | `test_hh4` passes with hand-computed expected value |
| Reference regression written | `test_r3_nifty_em_matches_nsccl_reference` exists with circular number |
| `handler.py` wires `INDEX_EM_RATES` | Code review: `em_rates=INDEX_EM_RATES` at NseMarginEngine construction |
| MM10.4 Risk 5 resolved | `test_hh3_calendar_spread_far_pays_one_third` GREEN; ELM groups A-AA unchanged |

---

## 10. Engineering Constraints for DeepSeek V4

These are structural requirements, not preferences. Any violation causes review rejection.

1. **EM in NseMarginEngine only.** No EM logic in `span_calculator.py`, `span_snapshot.py`,
   `parser_v400.py`, `margin_calculator.py`, or any file in `core/risk/span/`.

2. **`elm_rates.py` must not be modified.** It is frozen as of MM10.4. Any EM-related
   content belongs in `exposure_margin_rates.py`. Do not add EM rates or constants to
   `elm_rates.py`.

3. **No default for `em_rates`.** Constructor parameter must be required. Do not write
   `em_rates: Dict[str, float] = {}` or `Optional[...] = None`. Silent zero-EM is a
   production safety risk.

4. **EM and ELM are both additive, never inside the clamp.** `get_used_margin` must
   implement exactly: `max(0.0, span_margin - credit) + elm + em`. The `max(0)` applies
   to `(span - credit)` only.

5. **Long options excluded from EM.** `_em_margin` must skip positions where
   `inst.type == InstrumentType.OPTION` and `pos.side.name == "LONG"`.

6. **No mutation of `em_rates`.** Store a copy: `self._em_rates = dict(em_rates)`.

7. **`exposure_margin_rates.py` must not import from `core.risk.span.*` or
   `core.risk.elm_rates`.** Enforced by `test_ll1` and `test_ll2`.

8. **Calendar spread 1/3 concession applies to futures only.** Options positions are never
   part of the far-month EM reduction in Pass 3.

9. **Far-month identification uses expiry sort order.** After
   `expiries = sorted(expiry_map.keys())`, the outer index `j > i` always identifies the
   far-month. Do not invent an alternative identification strategy.

10. **All existing tests must remain GREEN with zero logic modification.** Updating
    `NseMarginEngine(calc, snap, elm_rates={})` to
    `NseMarginEngine(calc, snap, elm_rates={}, em_rates={})` is required; this is not a
    logic modification.

11. **Write tests before implementation.** Confirm RED after each group. Implement.
    Confirm GREEN. Do not write implementation first.

12. **Verify the EM rate before writing `exposure_margin_rates.py`.** If the NSE Clearing
    page is unreachable, request the confirmed rate from the Technical Lead. Do not commit
    `0.03` without a confirmed official source.

13. **`_em_margin` must not call SpanMarginCalculator private methods.** Use only
    `span_calc.position_tracker._positions` and the public `InstrumentType` enum (same
    access pattern as `_spread_credit` and `_elm_margin`).

14. **`current_prices` is contract-symbol keyed — never underlying-keyed.** `_em_margin`
    must build the underlying→spot map from futures positions in Pass 1. Direct
    `current_prices.get("NIFTY")` returns `None` for all real portfolios.

15. **`_resolve_em_rate` must use startswith prefix matching.** `get_incremental_margin`
    receives a contract symbol; `_em_rates` keys are underlying names. Direct dict lookup
    always returns 0.0 for contract symbols.

16. **`EM_CALENDAR_SPREAD_FRACTION` from `exposure_margin_rates.py` must be referenced in
    Pass 3.** Do not hardcode `1/3` or `0.3333` in `nse_margin_engine.py`. The constant
    belongs in the rates module as a documented regulatory rule.

---

## 11. Future Extensions (Out of Scope for MM10.5)

### Extension 1 — Protocol v3: instrument type in `get_incremental_margin`

**Rule:** The current `get_incremental_margin(symbol, quantity, price, lot_size)` interface
cannot distinguish long options from short options. Both ELM and EM overestimate margin for
long-option pre-trade checks.

**Design:** Protocol v3 would add `instrument_type: InstrumentType = FUTURE` as an optional
parameter, or restructure as `get_incremental_margin(order: ProposedOrder)`. Either path lets
`_resolve_elm_rate` and `_resolve_em_rate` skip long-option charges. MarginCalculator Protocol
v2 is frozen; v3 must be a new Protocol class with a migration plan.

**Impact files:** `core/risk/margin_calculator.py` (new protocol; v2 retained),
`core/risk/nse_margin_engine.py`, `core/execution/handler.py` (call site),
`tests/risk/test_nse_margin_engine.py` (groups Z and JJ extended).

### Extension 2 — Expiry-day calendar spread EM removal

**Rule:** SEBI circular effective 2025-02-10 removes the 1/3 far-month EM concession on the
expiry day for contracts expiring on that day. Both legs pay full EM on expiry day.

**Prerequisite:** `_em_margin` must know the current date. The cleanest injection is
`get_used_margin(current_prices, as_of: date)`, but this changes the frozen Protocol v2
signature. Alternative: a `set_date(d: date)` setter on `NseMarginEngine` called by the
handler before each margin check.

**Note:** This makes `get_used_margin` non-deterministic across calendar dates for identical
portfolios. The Phase KK determinism tests must be updated to inject a fixed date.

**Impact files:** `core/risk/nse_margin_engine.py`, `core/execution/handler.py`.

### Extension 3 — Stock derivatives EM

**Rule:** Stock F&O EM is `max(5%, 1.5σ√N)`. Phase 1 applies 0% EM to underlyings not in
`em_rates`. `EM_RATES_BY_CATEGORY["STOCK"]` (5% floor) is the reserved extension point.

**Prerequisite:** A data pipeline to ingest NSE Clearing stock-level volatility files and
populate `_em_rates` dynamically at startup.

**Impact files:** `exposure_margin_rates.py` (add dynamic loader), `nse_margin_engine.py`
(accept refreshed rates or a callable), new `nsccl_stock_vol.py` data-feed module.

### Extension 4 — ELM calendar spread rule clarification (advisory)

**Background:** MM10.5 Section 0b clarifies that the 1/3 far-month concession belongs to EM,
not ELM. ELM has no calendar spread concession per current NSE Clearing documentation.

**If a future NSE Clearing circular introduces an ELM calendar spread concession:** the design
mirrors the MM10.5 `_em_margin` Pass 3 logic applied inside `_elm_margin`. Until such a
circular is confirmed, ELM charges full rate to all futures legs and this extension remains
hypothetical. Do not implement without a confirmed circular.

---

### Extension development order (recommended)

Extension 2 (expiry-day) has the highest regulatory priority (SEBI effective 2025-02-10).
Extension 1 (Protocol v3) has the highest usability priority for pre-trade accuracy.
Extension 3 (stock derivatives) requires a separate data pipeline and is a separate milestone.
Extension 4 is hypothetical — do not implement without a confirmed NSCCL circular.
