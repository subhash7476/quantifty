# MM10.2 — Contract-Level SPAN Risk: Implementation Specification

**Date:** 2026-06-30  
**Milestone:** MM10.2 — Contract-Level SPAN Risk Implementation  
**Status:** APPROVED — ChatGPT Technical Lead sign-off 2026-06-30  
**Baseline:** tag `mm10.1-complete`, commit `bfc9854`, clean working tree  
**Author role:** System Architect  
**Workflow:** Claude (spec) → ChatGPT TL (review) → DeepSeek V4 (implementation) → Review → Commit → Documentation

---

## Technical Lead Sign-Off Record

**Review date:** 2026-06-30  
**Reviewer role:** ChatGPT Technical Lead

The TL raised one objection during review: *"Replace the duplicated `_SCENARIO_WEIGHTS` and `_derive_contract_scan_risk()` with a shared internal SPAN math module, or explain why that is not appropriate."*

Three options were evaluated (§4.3). The TL accepted the analysis and issued the following explicit verdicts:

- ✅ Keep the duplicated `_SCENARIO_WEIGHTS` in `span_calculator.py` (Option C)
- ✅ Keep the duplicated pure helper `_derive_contract_scan_risk`
- ✅ Protect equivalence permanently with regression test R10
- ✅ Document the duplication as intentional in §4.3

No other objections raised. Spec approved for implementation by DeepSeek V4.

---

## Codebase Analysis — Required Pre-Spec Questions

Before specifying changes, five questions were answered from direct codebase inspection.

### Q1 — What contract-level information already exists in `SpanSnapshot`?

Three collections are populated by the parser and available on every `SpanSnapshot` instance:

| Field | Type | Keyed by | Contains |
|-------|------|----------|----------|
| `futures` | `Dict[str, Tuple[SpanFutureContract, ...]]` | underlying symbol | Per-expiry contract with 16-element `ra` tuple, `expiry`, `price`, `delta`, `time_to_expiry` |
| `option_series` | `Dict[str, Tuple[SpanOptionSeries, ...]]` | underlying symbol | Per-expiry series with vol/scan rates (no `ra` tuple) |
| `option_contracts` | `Dict[str, Tuple[SpanOptionContract, ...]]` | underlying symbol | Per-strike/expiry contract with 16-element `ra` tuple, `strike`, `option_type`, `delta`, `implied_vol` |

`SpanFutureContract.ra` and `SpanOptionContract.ra` are complete 16-element risk-array tuples. SPAN scan risk is derived from these tuples by the same formula used to produce `risk_arrays[symbol].scan_risk`.

Verified against `nsccl.20260625.i01.spn`:
- `snapshot.futures['NIFTY']` → 3 contracts, expiries: 2026-06-30, 2026-07-28, 2026-08-25
- `snapshot.option_contracts['NIFTY']` → 4064 contracts across all strikes and expiries
- `snapshot.option_contracts['BANKNIFTY']` → 2564 contracts

### Q2 — What information is currently ignored by `SpanMarginCalculator`?

All three contract collections (`futures`, `option_series`, `option_contracts`) are entirely ignored.

`_scan_margin_per_unit(symbol)` reads only `self._snapshot.risk_arrays[symbol].risk_metrics["scan_risk"]`. This value was derived in `parser_v400` from the **nearest eligible expiry future's RA tuple only**. Every position in that underlying — regardless of expiry, strike, or instrument type — receives this single value.

Additionally ignored: per-contract `delta`, `implied_vol`, `time_to_expiry`. These remain out of scope for MM10.2.

### Q3 — Which data structures already support contract-level lookup?

| Lookup needed | Data structure | Accessor |
|---------------|---------------|----------|
| Futures by underlying + expiry | `SpanFutureContract.expiry` in `snapshot.futures[underlying]` | Linear scan of sorted tuple |
| Options by underlying + expiry + strike + type | `SpanOptionContract.{expiry,strike,option_type}` in `snapshot.option_contracts[underlying]` | Linear scan of tuple |
| Instrument type routing | `pos.instrument.type: InstrumentType` | Direct enum comparison |
| Futures underlying + expiry | `Future.underlying: str`, `Future.expiry: date` | Direct attribute access |
| Options underlying + expiry + strike + type | `Option.{underlying,expiry,strike,option_type}` | Direct attribute access |

`snapshot.futures[underlying]` is a sorted tuple (sorted by expiry, as populated by `_extract_future_contracts()` in `parser_v400`). No new indexing structures are required.

### Q4 — Which assumptions in the current calculator are still simplified?

1. **Nearest-expiry for all positions**: `risk_arrays[symbol].scan_risk` is derived from the nearest eligible future's RA. Far-month futures and options at any expiry receive this same value regardless of their actual expiry.
2. **Instrument type ignored**: `Future`, `Option`, and `Equity` instruments follow the identical code path in `_scan_margin_per_unit`.
3. **No strike differentiation**: An ATM call and a deep-OTM put at the same expiry receive the same scan risk.
4. **SOM applied unconditionally**: `max(scan_risk, SOM)` is applied to all instruments, including futures, despite SOM being an options-specific concept.

Assumption 4 is only observable when SOM > 0. In `nsccl.20260625.i01.spn`, `short_option_minimum = 0.0` for both NIFTY and BANKNIFTY.

### Q5 — Can MM10.2 be implemented without modifying the parser?

**Yes.** `parser_v400` already extracts and populates `futures`, `option_series`, and `option_contracts` on every parse. Zero parser changes are needed. The parser is feature-frozen and will not be touched.

---

## 1. Objective

Upgrade `SpanMarginCalculator` to derive SPAN scan margin from per-contract RA tuples stored in `SpanSnapshot`, replacing the current nearest-expiry symbol-level approximation.

After MM10.2:
- A `Future` position with July expiry receives the scan risk derived from the July futures RA
- An `Option` position at a specific strike/expiry receives the scan risk derived from that contract's RA, subject to the SOM floor
- An `Equity` position is unaffected; it continues to use the symbol-level path

This is the **final milestone that modifies `SpanMarginCalculator`**. The calculator becomes feature-frozen immediately after acceptance.

---

## 2. Current Behaviour

```
get_used_margin(prices)
  └─ _single_span_margin(symbol, price)
       ├─ pos = position_tracker.get_position(symbol)
       ├─ lot_size = pos.instrument.lot_size or pos.instrument.multiplier
       ├─ risk = _scan_margin_per_unit(symbol)        ← symbol-level only
       └─ return pos.quantity * lot_size * risk * margin_rate

_scan_margin_per_unit(symbol)
  ├─ risk_array = snapshot.risk_arrays.get(symbol)   ← keyed by underlying
  ├─ scan_risk = risk_array.risk_metrics["scan_risk"] ← nearest-expiry RA value
  ├─ som = risk_array.risk_metrics["short_option_minimum"]
  └─ return max(scan_risk, som)
```

`snapshot.futures`, `snapshot.option_series`, `snapshot.option_contracts` are never consulted.

**Regression baseline (from `test_span_calculator_regression.py`):**

| Test | Position | Expected margin |
|------|----------|----------------|
| R2 | NIFTY, 10 lots (qty=10, lot=65), nearest-expiry | Rs 1,458,834 |
| R3 | BANKNIFTY, 5 lots (qty=5, lot=30), nearest-expiry | Rs 827,010 |

These use `scan_risk = 2244.36` (NIFTY) and `5513.40` (BANKNIFTY), both derived from the nearest Jun-2026 futures RA.

---

## 3. Current Limitations

1. **Far-month futures accuracy**: NIFTY Jul-2026 future has `scan_risk = 2255.78` from its own RA; Aug-2026 has `2267.27`. All three expiries currently receive `2244.36` (Jun nearest). The calculator systematically underestimates far-month risk.

2. **Option accuracy**: NIFTY Jul-2026 C-23750 has `scan_risk = 608.20` from its own RA; P-23750 has `220.60`. Both currently receive `2244.36` — the nearest futures scan risk — which is approximately 4× the call's true risk.

3. **Instrument type not routed**: `Future` and `Option` instruments are never branched to their respective contract data. The routing decision is deferred to MM10.2.

4. **Dead data**: Three snapshot collections — `futures`, `option_series`, `option_contracts` — are populated by a production parser on every SPAN load and never consumed.

---

## 4. Gap Analysis

### 4.1 Data completeness

All data needed for MM10.2 exists in the snapshot on every parse. No new parser logic, no new snapshot fields, no new repository operations.

| Required | Source | Status |
|----------|--------|--------|
| Per-expiry futures RA tuple | `snapshot.futures[underlying][i].ra` | Available, unused |
| Per-strike/expiry option RA tuple | `snapshot.option_contracts[underlying][i].ra` | Available, unused |
| Futures expiry for lookup | `Future.expiry: date` | Available |
| Option expiry + strike + type for lookup | `Option.{expiry, strike, option_type}` | Available |
| Instrument type discriminant | `pos.instrument.type: InstrumentType` | Available |

### 4.2 Critical encoding mismatch — VERIFIED

**This is the highest-severity implementation risk. Verify before writing a single line.**

`SpanOptionContract.option_type` stores the raw XML `<o>` element text, which is `'C'` or `'P'` in NSE SPAN files (verified directly against `nsccl.20260625.i01.spn`).

`OptionType.CALL.value = "CE"`, `OptionType.PUT.value = "PE"` (from `core/instruments/option.py`).

A naïve comparison `oc.option_type == instrument.option_type.value` will **always be False** — every option lookup will silently miss and fall back to symbol-level. This defect produces no exception, no warning, and wrong results that look plausible.

**Resolution**: The lookup method must normalize before comparing:

```
normalize: "C" or "CE" → "C"
           "P" or "PE" → "P"
```

Apply normalization to the instrument's value before comparing against the snapshot's stored value. Both sides may need normalization if future SPAN file versions use "CE"/"PE" encoding.

### 4.3 SCENARIO_WEIGHTS duplication — three options evaluated

`_SCENARIO_WEIGHTS` and `_derive_scan_risk` currently live only in `parser_v400.py`. The calculator needs the same values. Three options exist.

**Clarification on Group G**: The import-isolation tests (`test_does_not_import_parser`, `test_does_not_import_pipeline`, `test_does_not_import_readiness`) scan for `"span_parser"`, `"ParserRegistry"`, `"span_pipeline"`, and `"span_readiness"`. They do **not** scan for `"parser_v400"`. Options B and C are therefore both Group-G-compliant.

---

**Option A — New `core/risk/span/span_math.py` shared module**

Create a thin module containing `SCENARIO_WEIGHTS` and `derive_scan_risk`. Both `parser_v400.py` and `span_calculator.py` import from it.

*Blocker*: Eliminates duplication only if `parser_v400.py` also imports from it. `parser_v400.py` is **feature-frozen** — modifying its imports to point at a new module is a change to a frozen file and is out of scope for MM10.2.

A calculator-only `span_math.py` that the parser ignores does not solve the problem: the parser retains its private copy and two divergeable sources still exist. R10 would still be required. The result is an extra file containing one constant and one function, with only one caller and no reduction in drift risk — pure overhead. CLAUDE.md: *"don't add abstractions for one-time use."*

*Verdict*: Option A is blocked. Requires modifying a frozen file. The calculator-only variant solves nothing.

---

**Option B — Calculator imports directly from `parser_v400.py`**

`span_calculator.py` adds `from core.risk.span.parser_v400 import _SCENARIO_WEIGHTS`. No frozen files are modified. Group G tests pass (they do not block `parser_v400` imports).

Three problems:

1. `_SCENARIO_WEIGHTS` is a private symbol in `parser_v400.py` (underscore-prefixed). Importing a private implementation detail creates an undeclared dependency on internal structure, not a public API.

2. The architectural intent of Group G is that the calculator's runtime dependency is `SpanSnapshot` only — the frozen data structure it receives at construction. A direct import from the parser module couples the calculator to the parser's internal organisation. If a future defect fix restructures `parser_v400.py`, the calculator breaks silently.

3. Adding `"parser_v400"` to the Group G blocklist is a plausible future test improvement. A pre-existing import would block that hardening.

*Verdict*: Option B is technically possible but architecturally incorrect. It imports a private symbol from a module the calculator should not depend on.

---

**Option C — Duplicate the constant locally in `span_calculator.py` (chosen)**

Define `_SCENARIO_WEIGHTS = (1.0,) * 14 + (0.3, 0.3)` at module level in `span_calculator.py`. The calculator is self-contained. No frozen files touched. Group G passes. R10 guards against drift.

The duplication is exactly 1 line: a 16-element tuple of weights that originate from the PC-SPAN 4.00 specification, not from NSCCL or any mutable business source. They will not change unless the exchange changes the SPAN scenario model — an event that would require a coordinated update of both the parser and the calculator regardless. R10 catches any accidental divergence automatically.

*Verdict*: Option C is the correct pragmatic choice. CLAUDE.md prohibits speculative abstraction and prohibits modifying frozen files. The cost of the duplication is one tuple literal, covered by one regression test.

---

**If Option A is desired in a future milestone**: add a non-frozen `core/risk/span/span_math.py`, update `parser_v400.py` to import from it as part of a deliberate un-freeze/re-certification cycle, and update the calculator at the same time. That is a clean refactor but belongs after MM10.2 when the parser's frozen status is reassessed.

Constant value (verified from `parser_v400.py`):
```
_SCENARIO_WEIGHTS = (1.0,) * 14 + (0.3, 0.3)   # 16 elements; from PC-SPAN 4.00 scenario model
```

### 4.4 SOM floor scope

`short_option_minimum` is 0.0 for NIFTY and BANKNIFTY in `nsccl.20260625.i01.spn`. The SOM floor must still be applied in code — other underlyings and other dates may carry non-zero SOM values. Unit test J4 must use a synthetic snapshot with SOM > 0 to prove the floor is enforced.

The current calculator applies `max(scan_risk, SOM)` to all instruments. After MM10.2, SOM is applied only on the option path (it is meaningless for futures and equity). This is a correctness improvement: futures currently receive a spurious SOM check that has no effect only because SOM = 0.0.

### 4.5 `get_incremental_margin` — known limitation, TL decision required

The `MarginCalculator` Protocol v2 signature is:

```python
def get_incremental_margin(self, symbol: str, quantity: float, price: float, lot_size: float = 1.0) -> float
```

No instrument, expiry, strike, or option type is passed. This method cannot perform contract-level lookup without an instrument reference, and modifying the protocol is out of scope (feature-frozen).

**Consequence**: After MM10.2, `get_used_margin()` is contract-level accurate; `get_incremental_margin()` remains at symbol-level nearest-expiry. For LIVE F&O, this means the pre-trade margin gate will overestimate option margin — it will use the underlying's futures scan risk rather than the option's contract scan risk.

**Decision required from Technical Lead**: Accept this asymmetry in MM10.2 (safe — overestimates, never underestimates), or define a separate pre-trade check mechanism for options as a follow-on task.

**Do NOT add an `instrument=None` optional parameter** to `get_incremental_margin`. No caller in the current scope will use it. CLAUDE.md explicitly prohibits speculative abstractions, and the protocol is feature-frozen. A dead parameter ships as technical debt.

### 4.6 Long/short treatment

`Position.quantity` is an absolute value in the current data model. The calculator cannot distinguish long from short options. SOM is applied to all option positions conservatively. This overestimates long-option margin (long options cannot lose more than the premium paid). Consistent with the architecture's "overestimates, never underestimates" principle and explicitly out of scope.

### 4.7 Lot-size ownership

`pos.instrument.lot_size` (Option) and `pos.instrument.multiplier` (Future) provide the lot/multiplier. The calculator trusts that instruments are constructed correctly. Lot-size accuracy is a concern for the composition root, not the calculator.

### 4.8 Fallback key for FUTURE and OPTION

The current code uses `symbol` (the position tracker key, which is also `pos.symbol = pos.instrument.symbol`) to look up `risk_arrays`. For a `Future("NIFTY25JUL", underlying="NIFTY", ...)`, the position key may be `"NIFTY25JUL"` while `risk_arrays` is keyed by `"NIFTY"`. This discrepancy currently does not surface because the test suite uses only `Equity` instruments where `symbol == underlying`.

After MM10.2, the fallback path for FUTURE and OPTION must use `instrument.underlying`, not `pos.symbol`. The `Equity` path continues to use `pos.symbol` (which equals the underlying for equities).

---

## 5. Exact Production Changes

**Only `core/risk/span/span_calculator.py` is modified in production code.**

### 5.1 New module-level constant

```
_SCENARIO_WEIGHTS = (1.0,) * 14 + (0.3, 0.3)
```

16-element tuple, identical semantics to `parser_v400.SCENARIO_WEIGHTS`. Placement: top of file, near existing `SPAN_METRIC_*` constants.

### 5.2 New import

```python
from core.instruments.instrument_base import InstrumentType
```

This is the only new import. Routing by `InstrumentType` enum comparison requires no `isinstance` check and no import of `Future` or `Option` — the enum is sufficient and avoids cross-module coupling to specific instrument implementations.

### 5.3 New private method: `_derive_contract_scan_risk(ra: tuple) -> float`

```
max(0.0, max(v * w for v, w in zip(ra, _SCENARIO_WEIGHTS)))
```

Pure function. No snapshot access. Identical semantics to `parser_v400._derive_scan_risk`. Named differently to emphasize it operates on a contract-level RA, not a symbol-level one.

### 5.4 New private method: `_lookup_future_scan_risk(underlying: str, expiry: date) -> Optional[float]`

Logic:
1. `contracts = self._snapshot.futures.get(underlying)` — returns `None` if underlying absent
2. If `contracts is None`: return `None`
3. Find first `f` in `contracts` where `f.expiry == expiry`
4. If found: return `_derive_contract_scan_risk(f.ra)`
5. If not found: return `None`

Returning `None` signals the caller to apply the symbol-level fallback. No exception raised on miss.

### 5.5 New private method: `_lookup_option_scan_risk(underlying: str, expiry: date, strike: float, option_type_str: str) -> Optional[float]`

`option_type_str` is `instrument.option_type.value` — the instrument enum value, which is `"CE"` or `"PE"`.

Logic:
1. Normalize: `norm = "C" if option_type_str in ("CE", "C") else "P"`
2. `contracts = self._snapshot.option_contracts.get(underlying)` — returns `None` if underlying absent
3. If `contracts is None`: return `None`
4. Find first `oc` where `oc.expiry == expiry and oc.strike == strike and oc.option_type == norm`
   (also tolerate `oc.option_type == option_type_str` in case a future SPAN file uses `"CE"`/`"PE"`)
5. If not found: return `None`
6. `contract_scan_risk = _derive_contract_scan_risk(oc.ra)`
7. Retrieve SOM: `ra = self._snapshot.risk_arrays.get(underlying)`; `som_floor = ra.risk_metrics.get("short_option_minimum", 0.0)` if `ra` is not None else `0.0`
8. Return `max(contract_scan_risk, som_floor)`

### 5.6 New private method: `_resolve_scan_risk(pos: Position) -> float`

Routing dispatcher. Called from `_single_span_margin` in place of `_scan_margin_per_unit(symbol)`.

```
instrument_type = pos.instrument.type

if instrument_type is InstrumentType.FUTURE:
    underlying = pos.instrument.underlying
    expiry = pos.instrument.expiry
    result = _lookup_future_scan_risk(underlying, expiry)
    if result is not None:
        return result
    return _scan_margin_per_unit(underlying)   ← fallback uses underlying, not pos.symbol

elif instrument_type is InstrumentType.OPTION:
    underlying = pos.instrument.underlying
    expiry = pos.instrument.expiry
    strike = pos.instrument.strike
    ot_str = pos.instrument.option_type.value
    result = _lookup_option_scan_risk(underlying, expiry, strike, ot_str)
    if result is not None:
        return result
    return _scan_margin_per_unit(underlying)   ← fallback uses underlying, not pos.symbol

else:   # EQUITY and any future instrument types
    return _scan_margin_per_unit(pos.symbol)   ← existing path unchanged
```

### 5.7 Modify `_single_span_margin`

Replace the single call to `_scan_margin_per_unit(symbol)`:

```
# Before:
risk = self._scan_margin_per_unit(symbol)

# After:
risk = self._resolve_scan_risk(pos)
```

`pos` is already retrieved earlier in `_single_span_margin`. The `symbol` parameter remains for the Equity fallback. No other changes to `_single_span_margin`.

### 5.8 No new exceptions

Contract miss → graceful fallback to `_scan_margin_per_unit`. The existing `MissingRiskArray` is raised if the fallback also fails (underlying absent from `risk_arrays`). No new exception class is required.

---

## 6. RED → GREEN Implementation Plan

**TDD discipline is required. Implementation proceeds in two sub-milestones matching the architecture revision.**

### MM10.2-S1: Per-Expiry Futures RA

**Step 1 — Write Group I tests (all RED)**  
Write I1 through I6 in `test_span_calculator.py`. All must fail before any production code changes. Confirm RED with `pytest tests/risk/span/test_span_calculator.py -k "test_I"`.

**Step 2 — Implement S1 production code**
- Add `_SCENARIO_WEIGHTS` constant
- Add import `from core.instruments.instrument_base import InstrumentType`
- Add `_derive_contract_scan_risk`
- Add `_lookup_future_scan_risk`
- Add `_resolve_scan_risk` with FUTURE branch and EQUITY fallback (OPTION branch falls through to EQUITY path at this stage)
- Modify `_single_span_margin` to call `_resolve_scan_risk(pos)`

**Step 3 — Verify S1 GREEN**  
`pytest tests/risk/span/` → Groups A–H unchanged, Group I green.  
If any of A–H regress, the EQUITY fallback path is broken — fix before proceeding.

### MM10.2-S2: Per-Strike Option RA

**Step 4 — Write Group J and K tests (all RED)**  
Write J1 through J6 and K1 through K3 in `test_span_calculator.py`.

**Step 5 — Implement S2 production code**
- Add `_lookup_option_scan_risk` with type normalization and SOM floor
- Complete `_resolve_scan_risk` OPTION branch

**Step 6 — Verify S2 GREEN**  
`pytest tests/risk/span/` → Groups A–K all green.

### Regression additions

**Step 7 — Write R8, R9, R10 (confirm RED without reference file)**  
Add to `test_span_calculator_regression.py`. Confirm all three are skipped (not erroring) when reference file is absent.

**Step 8 — Verify R8–R10 GREEN**  
`pytest tests/risk/span/test_span_calculator_regression.py` with reference file present → R1–R10 all green.

**Step 9 — Full test run**  
`pytest tests/risk/span/` → zero failures, zero errors.

---

## 7. Test Plan

### 7.1 Existing tests — must remain GREEN throughout

All tests in `test_span_calculator.py` Groups A–H and all R1–R7 in `test_span_calculator_regression.py`. Any regression in these groups indicates a broken Equity path or broken symbol-level fallback.

### 7.2 Group I — Future contract RA routing (new, in `test_span_calculator.py`)

Fixtures use `SpanFutureContract` constructed directly; no parser involvement.

**I1 — `_lookup_future_scan_risk` returns correct value for exact expiry match**

Setup: `SpanSnapshot.futures["NIFTY"] = (SpanFutureContract(expiry=date(2026,7,28), ra=(2255.78,0,...,0,0), ...),)`.  
Call `calc._lookup_future_scan_risk("NIFTY", date(2026,7,28))`.  
Assert returns `2255.78` (first scenario weight=1.0 dominates when other elements are 0).

**I2 — `_lookup_future_scan_risk` returns `None` for expiry miss**

Setup: snapshot has Jul-2026 future only.  
Call with `expiry=date(2026,8,25)`.  
Assert returns `None`.

**I3 — Per-expiry scan risk differs between expiries**

Setup: snapshot with two `SpanFutureContract` entries with distinct first RA elements (e.g., 2244.36 and 2255.78).  
Assert `_lookup_future_scan_risk("NIFTY", jun_expiry) != _lookup_future_scan_risk("NIFTY", jul_expiry)`.

**I4 — `get_used_margin` uses contract-level RA for `Future` instrument**

Setup: `PositionTracker` with a `Future("NIFTY25JUL", underlying="NIFTY", expiry=date(2026,7,28), multiplier=65)` position (qty=10).  
Snapshot: `risk_arrays["NIFTY"].scan_risk = 2244.36` (nearest), `futures["NIFTY"]` with Jul-2026 RA producing scan_risk `2255.78`.  
Assert `get_used_margin({...}) == 10 * 65 * 2255.78 * 1.0`.  
Assert result `!= 10 * 65 * 2244.36 * 1.0` (contract-level ≠ symbol-level).

**I5 — Future contract miss falls back to symbol-level**

Setup: `Future` with `expiry=date(2027,1,1)` (absent from snapshot futures).  
Snapshot: `futures["NIFTY"]` contains Jul-2026 only. `risk_arrays["NIFTY"].scan_risk = 2244.36`.  
Assert `get_used_margin({...}) == 10 * 65 * 2244.36 * 1.0`.

**I6 — Equity path unchanged after Future routing introduced**

Repeat any single existing Group B assertion verbatim with no changes to setup. Assert identical result.

### 7.3 Group J — Option contract RA routing (new, in `test_span_calculator.py`)

**J1 — `_lookup_option_scan_risk` returns correct value for exact match**

Setup: `SpanSnapshot.option_contracts["NIFTY"] = (SpanOptionContract(expiry=date(2026,7,28), strike=23750.0, option_type="C", ra=(608.20,0,...,0,0), ...),)`.  
`risk_arrays["NIFTY"].short_option_minimum = 0.0`.  
Assert `calc._lookup_option_scan_risk("NIFTY", date(2026,7,28), 23750.0, "CE") == 608.20`.

**J2 — `_lookup_option_scan_risk` returns `None` for expiry/strike/type miss**

Assert returns `None` when strike=24000.0 (absent), wrong expiry, or wrong type passed.

**J3 — Type normalization: `'CE'` matches `'C'` in snapshot**

Setup: `SpanOptionContract.option_type = "C"` (as produced by real SPAN file parser).  
Call with `option_type_str = "CE"` (as produced by `OptionType.CALL.value`).  
Assert returns a float (not `None`). This is the encoding mismatch guard — the most important correctness test in MM10.2.

Variant B: `option_type = "CE"` in snapshot, call with `"CE"`. Assert match found (future-proofing for SPAN files that may encode `"CE"`/`"PE"`).

**J4 — SOM floor applied when SOM exceeds contract scan risk**

Setup: `SpanOptionContract` with RA producing scan_risk `10.0`.  
`risk_arrays["NIFTY"].short_option_minimum = 50.0`.  
Assert `_lookup_option_scan_risk(...)` returns `50.0`, not `10.0`.

**J5 — `get_used_margin` uses contract-level RA for `Option` instrument**

Setup: `PositionTracker` with `Option("NIFTY25JUL23750CE", underlying="NIFTY", expiry=date(2026,7,28), strike=23750.0, option_type=OptionType.CALL, lot_size=65)` (qty=10).  
Snapshot: `risk_arrays["NIFTY"].scan_risk = 2244.36`, `option_contracts["NIFTY"]` with C-23750 Jul RA producing scan_risk `608.20`.  
Assert `get_used_margin({...}) == 10 * 65 * 608.20 * 1.0`.  
Assert result `!= 10 * 65 * 2244.36 * 1.0`.

**J6 — Option contract miss falls back to symbol-level**

Setup: `Option` with strike=99999.0 (absent from snapshot). Assert fallback produces `qty * lot_size * risk_arrays["NIFTY"].scan_risk`.

### 7.4 Group K — Backward compatibility (new, in `test_span_calculator.py`)

**K1 — Equity portfolio unchanged**

Re-run three Group B scenarios (multi-position, different symbols) and assert identical values to pre-MM10.2 expectation. No changes to fixtures or assertions from the Group B originals.

**K2 — `get_incremental_margin` remains symbol-level (documented asymmetry)**

Call `calc.get_incremental_margin("NIFTY", 10, 200.0, lot_size=65)` with `risk_arrays["NIFTY"].scan_risk = 30.0`.  
Assert returns `10 * 65 * 30.0 = 19500.0`.  
This confirms the pre-trade gate uses the symbol-level path and does not receive contract parameters — consistent with §4.5.

**K3 — Mixed portfolio: Equity + Future + Option in same `get_used_margin` call**

Setup: three positions — `Equity("RELIANCE")`, `Future(underlying="NIFTY", expiry=jul)`, `Option(underlying="NIFTY", expiry=jul, strike=23750, type=CALL)`.  
Snapshot: all three have both `risk_arrays` and contract-level data with intentionally distinct values.  
Assert total margin equals the sum of three independent expectations (one per routing path).

### 7.5 Regression additions (new, in `test_span_calculator_regression.py`)

All three tests are skipped (not errored) if `reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn` is absent — consistent with existing R1–R7 skip guard.

**R8 — Futures far-month RA, per-contract routing**

Position: `Future` with `underlying="NIFTY"`, `expiry=date(2026,7,28)`, `multiplier=65`, qty=10.  
Expected: `10 * 65 * 2255.78 = 1,466,257.00` Rs.  
Assert result `== 1466257.00`.  
Assert result `!= 1458834.00` (confirms per-expiry routing, not nearest-expiry).

**R9 — Option contract RA, per-strike routing**

Position A: `Option(underlying="NIFTY", expiry=date(2026,7,28), strike=23750.0, option_type=OptionType.CALL, lot_size=65)`, qty=10.  
Expected A: `10 * 65 * max(608.20, 0.0) = 395,330.00` Rs.

Position B: same but `option_type=OptionType.PUT`.  
Expected B: `10 * 65 * max(220.60, 0.0) = 143,390.00` Rs.

Assert A `== 395330.00`, B `== 143390.00`. Assert A `!= B` (call and put have different risk at same strike).

**R10 — Backward equivalence: nearest-expiry contract matches symbol-level**

Position: `Future` with `underlying="NIFTY"`, `expiry=date(2026,6,30)` (nearest expiry), `multiplier=65`, qty=10.  
Expected: `10 * 65 * 2244.36 = 1,458,834.00` Rs.  
Assert equals R2 value. This confirms `_SCENARIO_WEIGHTS` in the calculator is identical to the parser's weights, and the nearest-expiry contract path gives the same result as the current symbol-level path.

---

## 8. Files to Modify

| File | Changes |
|------|---------|
| `core/risk/span/span_calculator.py` | Add `_SCENARIO_WEIGHTS` constant; add import `InstrumentType`; add `_derive_contract_scan_risk`, `_lookup_future_scan_risk`, `_lookup_option_scan_risk`, `_resolve_scan_risk`; modify `_single_span_margin` to call `_resolve_scan_risk(pos)` |
| `tests/risk/span/test_span_calculator.py` | Add Group I (I1–I6), Group J (J1–J6), Group K (K1–K3) |
| `tests/risk/span/test_span_calculator_regression.py` | Add R8, R9, R10 with real SPAN file |

---

## 9. Files That Must NOT Change

| File | Reason |
|------|--------|
| `core/risk/span/span_snapshot.py` | Feature-frozen; contains the correct DTOs |
| `core/risk/span/parser_v400.py` | Feature-frozen; already extracts all needed data |
| `core/risk/span/span_parser.py` | Feature-frozen |
| `core/risk/span/span_repository.py` | Feature-frozen |
| `core/risk/span/span_readiness.py` | Feature-frozen |
| `core/risk/margin_calculator.py` | Feature-frozen; Protocol v2 signature unchanged |
| `core/execution/handler.py` | Out of scope |
| `core/execution/position_models.py` | Out of scope |
| `core/execution/position_tracker.py` | Out of scope |
| `scripts/fno_runner.py` | Out of scope |
| `core/instruments/` (all files) | Out of scope; read-only |

Verification command after implementation: `git diff --name-only mm10.1-complete HEAD` must show only the three files listed in §8.

---

## 10. Risks

| Risk | Severity | Detection | Mitigation |
|------|----------|-----------|------------|
| Option type encoding mismatch (`'C'`/`'P'` vs `'CE'`/`'PE'`) | **HIGH** | J3 fails if normalization absent; silent fallback to symbol-level otherwise | J3 specifically tests both encoding variants; encoding verified against real SPAN file. Normalization is mandatory, not optional. |
| `_SCENARIO_WEIGHTS` drift from parser constant | **MEDIUM** | R10 fails if values diverge | R10 backward-equivalence test: nearest-expiry contract via calculator must equal nearest-expiry symbol-level. Any weight difference causes a measurable mismatch. |
| Future/Option fallback uses `pos.symbol` instead of `instrument.underlying` | **MEDIUM** | I5 fails if fallback key is wrong | `_resolve_scan_risk` must explicitly use `instrument.underlying` for the FUTURE/OPTION fallback path, not `pos.symbol` |
| `get_incremental_margin` asymmetry (symbol-level pre-trade, contract-level post-trade) | **DOCUMENTED** | K2 asserts symbol-level behaviour explicitly | Documented in §4.5 and §10. TL must accept or escalate before implementation begins. |
| SOM=0.0 in reference file makes R9 SOM clause unexercised | **LOW** | J4 covers non-zero SOM via synthetic fixture | J4 uses synthetic snapshot with SOM=50.0 > contract scan_risk=10.0. R9 asserts contract scan_risk directly (SOM is 0.0 so `max(x, 0.0) == x`). |
| Strike float equality | **LOW** | Verified against reference file | NIFTY/BANKNIFTY strikes are always integers in SPAN files (23750.0, 62400.0, etc.). Python `float.__eq__` at integer values is exact. No fuzzy comparison needed. |

---

## 11. Acceptance Criteria

1. `pytest tests/risk/span/` exits with code 0; zero failures, zero errors.
2. Groups A–K all pass (unit tests).
3. R1–R10 all pass when reference SPAN file is present.
4. A `Future` with July expiry produces a `get_used_margin` result different from one with June expiry when the snapshot holds distinct RA tuples for those expiries (I4, R8).
5. An `Option` at strike 23750 CE produces a `get_used_margin` result different from the same underlying's nearest-futures scan risk (J5, R9).
6. An `Equity` position produces identical results before and after the change (K1, I6).
7. A contract miss (expiry/strike/type absent from snapshot) falls back gracefully to symbol-level without raising any exception (I5, J6).
8. `span_calculator` does not import `span_parser`, `ParserRegistry`, `span_pipeline`, or `span_readiness` (Group G tests pass). It also does not import from `parser_v400` — per the architectural decision in §4.3.
9. `git diff --name-only mm10.1-complete HEAD` shows exactly three files: `span_calculator.py`, `test_span_calculator.py`, `test_span_calculator_regression.py`.

---

## 12. Definition of Done

- [ ] `pytest tests/risk/span/` — zero failures (Groups A–K, R1–R10)
- [ ] `_SCENARIO_WEIGHTS = (1.0,) * 14 + (0.3, 0.3)` defined at module level in `span_calculator.py`
- [ ] No import of `span_parser`, `ParserRegistry`, `span_pipeline`, `span_readiness`, or `parser_v400` in `span_calculator.py` (Group G green; `parser_v400` excluded per §4.3 Option B analysis)
- [ ] All four new private methods present with exact names: `_derive_contract_scan_risk`, `_lookup_future_scan_risk`, `_lookup_option_scan_risk`, `_resolve_scan_risk`
- [ ] Type normalization in `_lookup_option_scan_risk` handles both `"CE"`/`"C"` and `"PE"`/`"P"` variants
- [ ] `_single_span_margin` calls `_resolve_scan_risk(pos)` for scan risk — not `_scan_margin_per_unit(symbol)`
- [ ] No changes to any feature-frozen file (verified by `git diff`)
- [ ] R10 backward-equivalence passes (confirms `_SCENARIO_WEIGHTS` parity with parser)
- [ ] J3 encoding normalization test passes (confirms option type mismatch handled)
- [ ] Commit message includes `mm10.2-complete`
- [ ] Tag `mm10.2-complete` applied after all tests pass
- [ ] `docs/reports/` updated with implementation summary (KB sync discipline)

---

## 13. Rollback Strategy

### Immediate rollback

`git revert <mm10.2-commit-sha>` returns to the MM10.1-complete state. Only `span_calculator.py` and the three test files are affected. No parser, snapshot, repository, readiness, runner, or protocol changes are reversed because none were made.

### S1-only rollback (revert S2 only)

If option RA routing is defective but futures routing is stable, remove the `InstrumentType.OPTION` branch in `_resolve_scan_risk` (fall through to the EQUITY path). This leaves futures on per-expiry RA and options on symbol-level nearest-expiry — identical to current option behaviour. No test regressions expected in Groups A–I; Groups J and K fail (acceptable for a partial rollback).

### Forward rollback via NseMarginEngine

`NseMarginEngine` (MM10.3+) wraps `SpanMarginCalculator`. If MM10.2 ships a latent defect, the aggregator can apply a correction factor, override the scan result, or fall back to `MarginTracker`. `SpanMarginCalculator` is never the sole guard — `ExecutionHandler`'s capital checks and position-size limits provide additional margin for error in production.

---

## Appendix A — Verified Regression Anchors (nsccl.20260625.i01.spn)

Extracted directly from the reference SPAN file using `parser_v400.parse_span_xml`. These values are authoritative inputs for R8, R9, R10 assertions.

| Instrument | Expiry | Strike | Type | RA-derived scan_risk (Rs/unit) | Lot size | 10-lot margin |
|-----------|--------|--------|------|-------------------------------|----------|---------------|
| NIFTY Future | 2026-06-30 | — | — | 2244.36 | 65 | 1,458,834 (= R2, = R10) |
| NIFTY Future | 2026-07-28 | — | — | 2255.78 | 65 | 1,466,257 (R8) |
| NIFTY Future | 2026-08-25 | — | — | 2267.27 | 65 | 1,473,725.50 |
| BANKNIFTY Future | 2026-06-30 | — | — | 5513.40 | 30 | 1,654,020 (= R3 basis) |
| BANKNIFTY Future | 2026-07-28 | — | — | 5541.47 | 30 | 1,662,441 |
| NIFTY Option | 2026-07-28 | 23750 | CE | 608.20 | 65 | 395,330 (R9-A) |
| NIFTY Option | 2026-07-28 | 23750 | PE | 220.60 | 65 | 143,390 (R9-B) |

SOM: NIFTY = 0.0, BANKNIFTY = 0.0 in this SPAN file. Non-zero SOM possible on other dates and for other underlyings — the SOM floor must remain in code.

Backward-equivalence: `derive(snapshot.futures['NIFTY'][0].ra) = 2244.36 = snapshot.risk_arrays['NIFTY'].scan_risk`. Confirmed equal. R10 tests this invariant at the calculator level via a real position lookup.

---

## Appendix B — Option Type Encoding Verification

Raw XML `<o>` element values observed in `nsccl.20260625.i01.spn`: `'C'` and `'P'` exclusively (15 samples inspected).

`OptionType.CALL.value = "CE"`, `OptionType.PUT.value = "PE"` (from `core/instruments/option.py`).

`parser_v400` stores raw XML value into `SpanOptionContract.option_type` verbatim:
```python
option_type=opt.findtext("o", "")
```

Therefore in all current NSE SPAN files, `SpanOptionContract.option_type` is `'C'` or `'P'`. The lookup method in `_lookup_option_scan_risk` must normalize `instrument.option_type.value` (`"CE"` or `"PE"`) before comparison. Future-proofing for SPAN files that may encode `"CE"`/`"PE"` is achieved by tolerating both forms on the instrument side.
