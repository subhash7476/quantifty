# MM9.4-S3 Implementation Specification
## SpanMarginCalculator — First Concrete `MarginCalculator`

**Status:** PENDING IMPLEMENTATION
**Preceded by:** MM9.4-S1 — `MarginCalculator` Protocol & SPAN Substitution Seam (COMPLETE, ADR-007) · MM9.4-S2 — SPAN Parameter Sourcing (COMPLETE)
**Followed by:** MM9.4-S4 — Buying-Power Gate + Composition-Root Swap
**Test baseline:** 766 passing (must remain green)
**Date drafted:** 2026-06-28
**Type:** Architecture + specification only. **No production code. No patches. No commits.**

---

## 0. Reading Guide — What S3 Ships vs What S3 Defers

S3 is the **computation** slice. It introduces the first concrete `MarginCalculator`: a pure object that
turns an immutable `SpanSnapshot` (S2) plus the live position book into a SPAN-based margin number. It
**does not** replace `MarginTracker`, touch any consumer, change the protocol, or wire anything into the
runtime. That is S4.

| Scope | Content |
|---|---|
| **S3 CODE scope** (what an engineer ships) | One new module `core/risk/span/span_calculator.py` containing `SpanMarginCalculator` (+ its exceptions), and its test module. The calculator satisfies `MarginCalculator` **structurally** (protocol v1, unchanged). It computes per-position SPAN scan margin + short-option minimum + exposure margin from a `SpanSnapshot`, and exposes an additional `get_incremental_margin(...)` method (calculator-only, not on the protocol) that S4's gate will consume. |
| **S3 DOCUMENT scope** (what this spec designs) | The `risk_metrics` **metric-key contract** (§3) — the exact keys the calculator reads and what each contributes — and the explicit list of exchange-specific behaviour deferred behind that contract. This is designed here so S4 (and the offline parser that populates `risk_metrics`) have no architectural decisions left. |

**The S3 deliverable, in one sentence:** make `SpanMarginCalculator(position_tracker, span_snapshot, …)`
a deterministic, filesystem-free, stateless-w.r.t.-portfolio computation object that returns SPAN margin
through the existing `MarginCalculator` surface — so S4 can swap it in at the composition root with zero
consumer code changes.

---

## 0.1 As-Built vs S2-Design — READ BEFORE CODING (load-bearing)

The MM9.4-S2 **spec** (`MM9_4_S2_IMPLEMENTATION_SPEC.md` §1.2) sketched a *design-intent* DTO with fields
`version`, `source_url`, `fetch_timestamp_ist`, `risk_arrays: tuple[...]`, and an `array_for()` method.
**The code that actually shipped in S2 differs.** S3 targets the **as-built** code, not the S2 design
sketch. The authoritative shapes are:

```python
# core/risk/span/span_snapshot.py  (AS BUILT — this is what S3 consumes)
@dataclass(frozen=True)
class SpanRiskArray:
    symbol: str                          # contract/underlying symbol, e.g. "NIFTY"
    risk_metrics: Dict[str, float]       # free-form named risk values (§3 defines the keys S3 reads)

@dataclass(frozen=True)
class SpanSnapshot:
    snapshot_date: date
    schema_version: str
    exchange: str
    segment: str
    file_hash: str
    risk_arrays: Dict[str, SpanRiskArray]   # keyed by symbol — lookup via .get(symbol)
    metadata: Dict[str, Any]
```

Consequences for the implementer (do **not** rediscover these as bugs):

| S2-design sketch said | As-built reality (target this) |
|---|---|
| `snapshot.array_for(underlying) -> Optional[...]` | **No such method.** Use `snapshot.risk_arrays.get(underlying)`. |
| `risk_arrays: tuple[SpanRiskArray, ...]` | `Dict[str, SpanRiskArray]` keyed by `symbol`. |
| `SpanRiskArray(underlying, price_scan_range, volatility_scan_range, scan_points, …)` | `SpanRiskArray(symbol, risk_metrics: Dict[str, float])`. Named risk values live **inside** `risk_metrics` (§3). |
| `version: date` | `snapshot_date: date`. |
| `checksum_sha256` | `file_hash` (sha256 of the raw ZIP; verified by the repository on load, `span_repository.py:88-95`). |

The repository read path (`SpanRepository.load(version)`) raises **`FileNotFoundError`** (no archive
entry) or **`ValueError`** (checksum mismatch / corrupt). Those are the **repository's** exceptions; the
calculator never catches or re-raises them (§6, Design Q8) — the calculator never touches the filesystem.

---

## 1. Architectural Objectives

### 1.1 Responsibilities

`SpanMarginCalculator` has exactly one responsibility: **given an immutable `SpanSnapshot` (config) and the
live position book (read on demand), compute SPAN margin numbers.** Specifically it answers:

- `get_used_margin(current_prices) -> float` — total SPAN margin consumed by the **current** book.
- `get_exposure(current_prices, symbol=None) -> float` — gross notional exposure (margin-model-independent).
- `get_incremental_margin(instrument, quantity, side, current_prices) -> float` — the additional SPAN
  margin a **proposed** order would consume (calculator-only method; S4's gate consumes it).

It does **not**: decide admission, log, mutate any tracker, read the filesystem, hit the network, query a
broker, or hold portfolio state. (ADR-007 rule #2: the calculator computes; `ExecutionHandler` decides.)

### 1.2 Ownership

| Artifact | Owner |
|---|---|
| The frozen `SpanSnapshot` it was constructed with | The calculator holds it as **immutable construction-time configuration** (ADR-007 rule #1 permits config). |
| The `position_tracker` reference | **Not owned** — a live read-only reference to the ledger's tracker (ADR-001 truth). The calculator reads it on each call; it never copies/caches positions (§5.2). |
| Margin numbers it returns | Owned by the caller; the calculator retains nothing between calls. |

### 1.3 Lifecycle

```
(startup, once)   composition root [S4] loads SpanSnapshot via SpanRepository,
                  constructs SpanMarginCalculator(position_tracker, span_snapshot)
(session)         snapshot frozen for the whole session; every get_*() call is a
                  pure function of (frozen snapshot, live positions, passed prices)
(shutdown)        calculator discarded; next session constructs a fresh one
```

In **S3** there is no live construction — the calculator is exercised only by its own tests. The composition
swap (`MarginTracker` → `SpanMarginCalculator` in `fno_runner.py`) is **S4**.

### 1.4 Deterministic guarantees & invariants

- **Pure given inputs:** `(frozen snapshot, position-book state, prices) → margin` is a total function. Same
  inputs ⇒ byte-identical output (ADR-003).
- **No I/O:** zero filesystem, network, broker, or clock access at compute time (§5).
- **No mutation:** never writes any tracker, the snapshot, or its own attributes after construction.
- **Statelessness w.r.t. portfolio:** no positions/margin/equity cached across calls (ADR-007 rule #1; §5.2).
- **Structural protocol conformance:** satisfies `MarginCalculator` v1 without inheritance or protocol edits.

---

## 2. SpanMarginCalculator — Object Surface

Module: **`core/risk/span/span_calculator.py`** (new). Placement is in `core/risk/span/` beside the data
foundation it consumes (ADR-007: margin is a risk-domain concern, not an execution concern).

### 2.1 Constructor & injected dependencies

```python
class SpanMarginCalculator:
    def __init__(
        self,
        position_tracker: PositionTracker,
        span_snapshot: SpanSnapshot,
        *,
        margin_rate: float = DEFAULT_EXPOSURE_MARGIN_RATE,   # exposure-margin (ELM) fraction
    ) -> None:
        ...
```

| Dependency | Role | Notes |
|---|---|---|
| `position_tracker` | Live read-only source of the current book | Same parameter shape as `MarginTracker.__init__` → keeps the S4 swap a one-liner. Held by reference; never cached. |
| `span_snapshot` | Immutable SPAN parameters (config) | An **already-loaded, already-validated** `SpanSnapshot` DTO. The calculator depends **only** on this type — never on `SpanRepository`, the fetch job, the archive layout, or the parser (Design Q1, Q6). |
| `margin_rate` | The exposure-margin / ELM fraction | Satisfies the protocol's required `margin_rate: float` field. Semantics defined in §3.4. Keyword-only with a documented default. |

**The snapshot is injected as a constructed object, not loaded by the calculator** (Design Q1). The
composition root (S4) calls `SpanRepository.load(active_version)` and passes the result in. This is the exact
analogue of how `MarginCalculator` consumers depend on the protocol, not on `MarginTracker` (ADR-007), and
how `SpanSnapshot` is the single immutable DTO at the loader→calculator boundary (S2 §Design Q9).

### 2.2 Public API

```python
margin_rate: float                                              # protocol field (exposure-margin rate)

def get_exposure(self, current_prices: Dict[str, float],
                 symbol: Optional[str] = None) -> float:        # protocol — gross notional
def get_used_margin(self, current_prices: Dict[str, float]) -> float:   # protocol — total SPAN margin

def get_incremental_margin(self, instrument, quantity: int,
                           side: PositionSide,
                           current_prices: Dict[str, float]) -> float:  # S3-only (S4's gate consumes)
```

`get_exposure` and `get_used_margin` are the **protocol v1 surface** — identical signatures to
`MarginTracker`, so the object is a structural `MarginCalculator`. `get_incremental_margin` is an
**additional method**, present on `SpanMarginCalculator` only; it is **not** added to the protocol (§2.5).

### 2.3 Internal helpers (private)

```python
def _underlying_for(self, instrument) -> str          # canonical underlying lookup key (§3.1, Q2)
def _risk_array_for(self, underlying) -> SpanRiskArray # snapshot.risk_arrays.get(...) or raise (§6)
def _lot_size(self, instrument) -> float              # lot_size, falling back to multiplier (§3.2)
def _span_margin_for(self, instrument, quantity, side, price) -> float   # per-position SPAN (§3.2)
def _notional(self, symbol, quantity, price) -> float # qty * price * lot_size (exposure leg)
```

These are implementation detail and not part of any contract. `_span_margin_for` is the single point where
the §3 metric-key contract is applied, so changing the SPAN formula touches exactly one method.

### 2.4 Immutability & statelessness

- The calculator stores only: the `position_tracker` **reference**, the frozen `span_snapshot`, and the
  scalar `margin_rate`. No mutable portfolio state.
- The held `SpanSnapshot` is `frozen=True`; the calculator never attempts to mutate it.
- No method writes to `self` after `__init__`. No memoization of margin/exposure/positions (ADR-007 rule #1
  forbids caching portfolio-derived values; deterministic recomputation is cheap, §7).

### 2.5 Protocol stays v1 — do NOT grow it (load-bearing)

S2's Appendix C phrase *"satisfies the grown protocol"* is a trap. **Do not add `get_incremental_margin`
(or anything else) to the `MarginCalculator` protocol in S3.** Reason: `MarginTracker` satisfies the
protocol **structurally**; adding a method to the protocol that `MarginTracker` lacks would break its
conformance, and every `MarginCalculator`-typed slot — `ExecutionHandler.margin_tracker`
(`handler.py:196`), `PortfolioView.__init__` — would fail static checking. That drags execution-path edits
into S3, violating the non-goals. Implementations are free to **exceed** the protocol surface;
`get_incremental_margin` lives on `SpanMarginCalculator` alone. Whether to formalize an incremental method
into a `MarginCalculator` v2 is an **S4 decision**, made when both implementations and all consumers can be
updated together.

---

## 3. Margin Algorithm — The `risk_metrics` Metric-Key Contract

The calculator's input is **not** the NSE raw file — S2's parser already absorbed that. The calculator's
input is the `SpanRiskArray.risk_metrics: Dict[str, float]`. This section defines **exactly** which keys the
calculator reads and what each contributes, so the algorithm is fully specified while the NSE-file-to-metric
derivation remains (correctly) deferred to the offline parser.

### 3.1 Lookup key — which risk array applies to a position (Design Q2)

```
position.instrument  ──_underlying_for()──►  canonical underlying symbol  ──.get()──►  SpanRiskArray
```

- The lookup key is the **canonical underlying** (e.g. `"NIFTY"`, `"BANKNIFTY"`) — **one risk array serves
  every contract on that underlying** (all strikes, all expiries, the future). SPAN parameters are published
  per underlying, not per contract.
- Derivation (`_underlying_for`): read the instrument's underlying field. Options/futures built through the
  canonical path expose an `underlying`; equities expose their own symbol. Use the instrument's existing
  attribute (`getattr(instrument, "underlying", None) or instrument.symbol`) — **no new resolver, no master
  query** (the canonical identity was already settled by the startup gate's canonicalization step before any
  margin runs; §5).
- A position whose underlying has **no** entry in `snapshot.risk_arrays` is a **reject** (§6 F-MISS-ARRAY).

### 3.2 Per-position SPAN margin (`_span_margin_for`)

For one position (instrument, signed quantity `q`, side, current price `p`):

```
underlying  = _underlying_for(instrument)
array       = snapshot.risk_arrays[underlying].risk_metrics      # the metric dict
lot         = _lot_size(instrument)                              # lot_size or multiplier fallback (§3.2.1)
units       = abs(q) * lot                                       # contract units

scan        = array["scan_risk"] * units                        # worst-case scenario loss, per the array
short_min   = array.get("short_option_minimum", 0.0) * units    # only when the position is a SHORT OPTION
position_span = scan + (short_min if is_short_option(instrument, side) else 0.0)
```

**Metric keys read by S3 (the contract the parser must populate):**

| Key | Meaning | Applied to | Missing-key behaviour |
|---|---|---|---|
| `"scan_risk"` | Worst-case loss for the underlying across SPAN price/vol scenarios, **per contract unit** (the parser pre-reduces NSE's scenario array to this single number — §3.5). | Every position. | **Reject** (§6 F-MISS-METRIC) — `scan_risk` is mandatory. |
| `"short_option_minimum"` | Short-option minimum charge per contract unit. | Short option positions only. | Default `0.0` (treated as no minimum). |

> **Schema confirmation flag (do NOT fabricate):** the *exact* metric key strings the NSE parser emits
> (`"scan_risk"`, `"short_option_minimum"`, or NSE's own names) are an **implementation-time fact**, to be
> confirmed against what the S2 parser actually writes when the real NSE schema is wired. Define them as
> **named module constants** (`METRIC_SCAN_RISK`, `METRIC_SHORT_OPTION_MIN`) flagged for confirmation, exactly
> as S2 flagged `SPAN_SOURCE_URL`. The algorithm's correctness rests on the *contract shape*, not the spelling.

#### 3.2.1 Lot size — reuse the S2-proven rule

`_lot_size` mirrors `MarginTracker._calculate_single_exposure` (`margin_tracker.py:42`) exactly:
`getattr(instrument, "lot_size", None) or instrument.multiplier`. (Option carries `lot_size`; Future folds
lot_size into `multiplier`; Equity has neither → 1.0.) Do **not** invent a new sizing rule — the MM9.2-S2
fix is the canonical source.

### 3.3 Portfolio SPAN margin (`get_used_margin`)

```python
def get_used_margin(self, current_prices):
    total = 0.0
    for symbol, position in position_tracker._positions.items():
        price = current_prices.get(symbol)
        if price is None:           # MM9.2-S2 rule: a zero-priced leg stays in via 'is not None';
            continue                # an *absent* price contributes nothing this tick
        total += self._span_margin_for(position.instrument, position.quantity,
                                        position.side, price)
    total += self.get_exposure(current_prices) * self.margin_rate   # exposure (ELM) component
    return total
```

- **SPAN scan component:** sum of per-position `_span_margin_for` (§3.2).
- **Exposure component:** gross notional × `margin_rate` (the ELM overlay, §3.4).
- Total used margin = SPAN scan + short-option minimums + exposure margin.

### 3.4 `margin_rate` semantics

The protocol requires a `margin_rate: float` field (telemetry/reporting read it — ADR-007 Alternatives).
For SPAN there is no single flat rate, so `margin_rate` is defined as **the exposure-margin (ELM) fraction**
— the percentage-of-notional overlay added on top of scan risk in §3.3. It is a real, used number (it scales
the exposure component), not a sentinel. Documented default `DEFAULT_EXPOSURE_MARGIN_RATE` flagged for
confirmation against NSE's published ELM. **Note:** `margin_rate` is exercised only by S3's own tests and the
exposure component until S4 wires the calculator into the gate.

### 3.5 What is intentionally DEFERRED (stated exactly)

The following are **out of S3** and live **behind the metric-key contract** — i.e., in the offline parser
that pre-computes `risk_metrics`, or in S4/later slices. None require runtime computation; all are deferred
deliberately so the calculator stays a deterministic lookup-and-sum:

| Deferred behaviour | Where it belongs | Why deferred from S3 |
|---|---|---|
| Deriving `scan_risk` from NSE's 16-point scenario risk array (price/vol shifts, worst-case selection) | **Offline parser** (S2 schema, confirmed at impl time) — emits the reduced `scan_risk` metric. | Keeps runtime margin a pure lookup (ADR-003); scenario repricing is reproducible offline. |
| Inter-month spread credits (calendar offsets across expiries of one underlying) | Later slice (margin-netting) | Requires portfolio-grouping logic; S3 charges margin per position with no spread credit (conservative — overestimates, never under). |
| Inter-commodity spread credits (e.g. NIFTY↔BANKNIFTY offsets) | Later slice | Same — S3 is conservative (no offset). |
| Net option value (NOV) adjustment / long-option premium credit | Later slice | Requires premium accounting across the book. |
| Tiered/composite delta scenarios, delta-based repricing | **Offline parser** (folded into `scan_risk`) | See §3.6 — Greeks are **not** used at runtime. |
| Buying-power gate formula (`free_capital = cash − used_margin; reject if free < incremental`) | **S4** | Non-goal of S3 (gate/handler change). S3 provides `get_incremental_margin`; S4 wires it. |

**Conservatism note:** because S3 omits all spread/NOV credits, S3's SPAN margin is an **upper bound** on
true SPAN. This is the safe direction (a margin gate may reject a tradeable order; it will never admit an
unmargined one). State this in the module docstring so it is not later mistaken for a defect.

### 3.6 GreeksCalculator — NOT used (conscious divergence from the plan)

`MM9_IMPLEMENTATION_PLAN.md` §MM9.4-S3 says the calculator computes margin "using `CanonicalInstrument` and
`GreeksCalculator`." **That line predates the as-built S2 DTO and is superseded.** Under the metric-key
contract, any option repricing that produces `scan_risk` happens **offline in the parser**, not at runtime.
Pulling `GreeksCalculator` into the calculator would (a) add runtime computation that must itself be
deterministic and (b) duplicate work the parser already did. The calculator therefore uses **no Greeks** —
it is strictly lookup × scale × sum, which is *more* deterministic (ADR-003), not less. Record this as a
deliberate divergence in the S3 report and tick the plan accordingly.

---

## 4. Repository Usage

| Question | Answer |
|---|---|
| When is the repository called? | **At the composition root, at startup, once (S4).** Never by the calculator. |
| When is the snapshot loaded? | Before calculator construction: `snapshot = SpanRepository(...).load(active_version)`; then `SpanMarginCalculator(pt, snapshot)`. |
| Who owns the loaded snapshot? | The calculator (immutable config, §1.2). The repository retains nothing (S2 §4.2). |
| Caching strategy | **None in the calculator.** The snapshot is loaded once and frozen for the session; there is nothing to cache or refresh. No per-tick re-read. |
| Filesystem access by the calculator? | **Never.** The calculator imports the `SpanSnapshot` **type** only; it does not import or call `SpanRepository`. This is what makes §8's unit tests filesystem-free (Design Q7). |

The calculator's only dependency on `core/risk/span/` is `span_snapshot.SpanSnapshot` (the DTO). It must not
import `span_repository`, `span_parser`, `span_pipeline`, or `span_readiness` — enforced by an import-absence
test (§8.1 R6).

---

## 5. Determinism

### 5.1 Zero runtime I/O
- **No downloads:** all acquisition was the S2 offline job; the calculator performs none (ADR-007 rule #3).
- **No filesystem:** the calculator holds a constructed DTO; it never reads the archive (§4).
- **No broker:** no margin/positions query to any broker API at compute time (ADR-007 rule #4).
- **No clock:** margin is a function of (snapshot, positions, prices) — never of wall-clock time (ADR-003).

### 5.2 Statelessness vs the `position_tracker` reference (address head-on)
The protocol surface `get_used_margin(current_prices)` passes **no positions**, so the calculator **must**
hold a `position_tracker` reference to know the book — exactly as `MarginTracker` does. **This is a live read
of ledger truth (ADR-001), not cached portfolio state**, so it satisfies ADR-007 rule #1 ("positions, margin,
and equity must never be cached" — a live reference read each call is not a cache). Do **not** try to make the
calculator "stateless" by passing positions as a method argument: that would break the protocol surface and
the S4 drop-in swap. "Pure computation object, owns no mutable portfolio state" means **it stores no
position/margin/equity snapshot**, not that it holds no tracker reference.

### 5.3 Replay guarantees
The session journals the loaded `snapshot_date` + `file_hash` (S2 §7.3). Replay loads that exact archive
entry (hard version + checksum equality) and constructs an identical calculator; with identical position
state and prices, every `get_used_margin`/`get_incremental_margin` reproduces the live value bit-for-bit.

### 5.4 Frozen for the session
The snapshot is loaded once and never reloaded mid-session (S2 §7.2). Two ticks at the same book + prices
compute the same margin for the session's lifetime — the property S4's gate relies on.

---

## 6. Error Handling

The calculator owns a small, distinct exception family for **input/lookup** faults it can detect; the
**repository** owns load/integrity faults (the calculator never sees them — §0.1). Refuse > warn > fallback
(ADR-MM7F-1): the calculator **never** returns a flat-rate or guessed margin on any fault.

```python
class SpanMarginError(Exception):              # base for all calculator faults
class UnsupportedInstrument(SpanMarginError):  # asset class SPAN cannot margin
class MissingRiskArray(SpanMarginError):       # no risk array for the underlying
class MissingRiskMetric(SpanMarginError):      # mandatory metric key absent from the array
```

| # | Condition | Detected where | Result | Owner |
|---|---|---|---|---|
| F-UNKNOWN-INST | Unknown / unsupported **asset class** (cannot be SPAN-margined) | `_span_margin_for` | **raise `UnsupportedInstrument`** | Calculator |
| F-MISS-ARRAY | No `risk_arrays` entry for the position's underlying | `_risk_array_for` | **raise `MissingRiskArray`** | Calculator |
| F-MISS-METRIC | Mandatory metric (`scan_risk`) absent from the array | `_span_margin_for` | **raise `MissingRiskMetric`** | Calculator |
| F-MISSING-FILE | No archive entry for the date | `SpanRepository.load` | `FileNotFoundError` → startup REFUSE (S2 §6) | **Repository / startup gate** (never the calculator) |
| F-CORRUPT / F-CKSUM | Checksum mismatch / corrupt snapshot | `SpanRepository.load` | `ValueError` → startup REFUSE (S2 §6) | **Repository / startup gate** |
| F-SCHEMA | Unsupported parser schema | `span_parser` / load path | `UnsupportedSpanSchema` → startup REFUSE (S2 §6) | **Parser / startup gate** |
| F-INVALID-EXPIRY | Expired/invalid contract reaching the calculator | n/a in S3 | Not the calculator's concern — identity validity is settled by the startup canonicalization gate (§5) before margin runs; an invalid instrument surfaces as F-UNKNOWN-INST or F-MISS-ARRAY. | Startup gate |

**Disposition summary (Design Q4, Q5, Q8):**
- **Unknown instrument / missing array / missing metric → exception** (rejection at compute time), raised by
  the **calculator**. The caller (S4's gate / S3's tests) decides what to do; a raised `SpanMarginError`
  means "this order/book cannot be margined," which the gate translates into a reject.
- **Corrupt snapshot / unsupported schema / missing file → startup failure**, raised by the **repository or
  the readiness gate** (S2), long before the calculator is constructed. The calculator is only ever handed a
  validated snapshot, so it never owns these.
- The calculator's exceptions are **distinct from** the repository's `FileNotFoundError`/`ValueError`
  (Design Q8): different layer, different failure class, never conflated.

---

## 7. Performance

| Concern | Spec |
|---|---|
| Complexity | `get_used_margin`: **O(P)** in open positions P. `get_incremental_margin`: **O(1)** (one underlying lookup + arithmetic). `get_exposure`: O(P) (or O(1) for a single `symbol`). |
| Lookup strategy | `risk_arrays` is already a `Dict[str, SpanRiskArray]` keyed by symbol → **O(1)** per-position underlying lookup. No scan, no sort. |
| Snapshot indexing | None needed — the dict is the index. P is tens of positions and the underlying set is ~2 (NIFTY, BANKNIFTY); no further structure justified (CLAUDE.md "no over-engineering"). |
| Memory ownership | The calculator holds one frozen `SpanSnapshot` (hundreds of floats) + one tracker reference + one scalar. Negligible. No per-call allocation beyond the running sum. |
| Caching | **None** (ADR-007 rule #1). Deterministic recomputation each call is O(P) arithmetic — far cheaper than the correctness risk of cached portfolio state. |

Avoid premature optimization: do not add memoization, indices, or a DuckDB store (S2 §1.1 already settled
the in-memory-DTO decision).

---

## 8. Testing Strategy

All tests are deterministic and **filesystem-free**: every test constructs a `SpanSnapshot` **by hand** and
injects it — proving the DI boundary (Design Q7). No test loads from disk, hits the network, or queries a
broker.

### 8.1 RED (write first; all fail before `span_calculator.py` exists)

```
R1  test_conforms_to_margin_calculator_protocol
      SpanMarginCalculator instance satisfies MarginCalculator structurally
      (has margin_rate, get_exposure, get_used_margin); isinstance/typing check.
R2  test_used_margin_single_short_option
      One short NIFTY option, hand-built snapshot {scan_risk, short_option_minimum};
      used_margin == scan*units + short_min*units + exposure*margin_rate. Exact number.
R3  test_missing_risk_array_raises_MissingRiskArray
      Position on an underlying absent from risk_arrays → MissingRiskArray (not a fallback).
R4  test_missing_scan_risk_metric_raises_MissingRiskMetric
      Array present but no "scan_risk" key → MissingRiskMetric.
R5  test_incremental_margin_for_proposed_order
      get_incremental_margin(instrument, qty, side, prices) == the SPAN delta for that leg.
R6  test_calculator_does_not_import_repository_or_filesystem
      AST/import-absence: span_calculator.py imports SpanSnapshot type only, never
      span_repository / span_parser / span_pipeline / urllib / open().
```

### 8.2 GREEN (minimum to pass each RED)

```
G1  Class with margin_rate + the two protocol methods (R1).
G2  _span_margin_for applying the §3.2 contract; get_used_margin summing it + exposure (R2).
G3  _risk_array_for raising MissingRiskArray on .get() miss (R3).
G4  _span_margin_for raising MissingRiskMetric on absent mandatory key (R4).
G5  get_incremental_margin computing one leg's SPAN via _span_margin_for (R5).
G6  Imports limited to SpanSnapshot (R6).
```

### 8.3 Integration

```
I1  Multi-position book (short NIFTY option + long BANKNIFTY future + an equity),
    hand-built snapshot covering both underlyings → used_margin equals the summed,
    independently-computed expectation; equity leg dispatches correctly (lot fallback).
I2  Zero-price leg behaviour: a leg priced 0.0 stays in the sum (contributes scan on units);
    an *absent* price contributes nothing (mirrors MM9.2-S2 semantics).
I3  Determinism: two identical calls return byte-identical floats; reordering positions
    does not change the total.
```

### 8.4 Regression

```
X1  Full suite stays green at 766 → 766+new. No existing test changes.
X2  MarginTracker tests (tests/risk/test_margin_calculator.py) unchanged and passing —
    proves the protocol was not grown (§2.5): MarginTracker still conforms.
X3  Zero diff in handler.py / portfolio_view.py / margin_tracker.py / driver.py / fno_runner.py
    (verify by `git diff --stat`).
```

### 8.5 Acceptance Criteria

| # | Criterion |
|---|---|
| AC1 | `core/risk/span/span_calculator.py` exists with `SpanMarginCalculator` satisfying `MarginCalculator` v1 **structurally** (no inheritance, no protocol edit). |
| AC2 | Margin computed from the as-built `SpanSnapshot` (`risk_arrays: Dict`, `.get()` lookup) per the §3 metric-key contract — no `array_for()`, no `version`, no tuple API. |
| AC3 | `get_incremental_margin` exists on the calculator and is **absent** from the `MarginCalculator` protocol. |
| AC4 | Unknown instrument → `UnsupportedInstrument`; missing array → `MissingRiskArray`; missing `scan_risk` → `MissingRiskMetric`. **No fallback to flat-rate ever.** |
| AC5 | The calculator performs **zero** filesystem/network/broker/clock access; it imports only the `SpanSnapshot` type (R6 green). |
| AC6 | Calculator is unit-testable with a hand-built snapshot, no disk (Design Q7) — all §8.1/§8.3 tests filesystem-free. |
| AC7 | `MarginCalculator` protocol unchanged; `MarginTracker` still conforms (X2). |
| AC8 | **Zero edits** to `handler.py`, `portfolio_view.py`, `margin_tracker.py`, `driver.py`, `fno_runner.py` (X3). No gate/buying-power/composition-root change. |
| AC9 | All 766 prior tests pass; new S3 tests green; no test touches the network or disk. |
| AC10 | NSE metric-key strings + `DEFAULT_EXPOSURE_MARGIN_RATE` are **named constants flagged for confirmation**, not fabricated. |

### 8.6 Definition of Done

- [ ] `core/risk/span/span_calculator.py` — `SpanMarginCalculator` (+ `SpanMarginError`, `UnsupportedInstrument`, `MissingRiskArray`, `MissingRiskMetric`), metric-key constants flagged.
- [ ] `tests/risk/span/test_span_calculator.py` — R1–R6, I1–I3 green; filesystem-free.
- [ ] `MarginCalculator` protocol untouched; `MarginTracker` conformance preserved (X2).
- [ ] Zero diff in handler/portfolio_view/margin_tracker/driver/fno_runner (X3).
- [ ] All 766 prior tests pass; new tests green; no network/disk in any test.
- [ ] Docs synced (§9.3).

---

## 9. File-by-File Plan

### 9.1 Production files

| File | Change | Why |
|---|---|---|
| `core/risk/span/span_calculator.py` | **NEW.** `SpanMarginCalculator` + exception family + metric-key constants (§2, §3, §6). | The slice's sole production artifact: the first concrete `MarginCalculator`, consuming the S2 `SpanSnapshot`. |
| `core/risk/span/__init__.py` | **MODIFY (export only).** Add `SpanMarginCalculator` (+ exceptions) to the package exports. | Make the calculator importable from `core.risk.span` for the S4 composition root; mirrors the existing S2 export block. **No logic change.** |

**Not created/modified in S3 (and why):**

| File | Reason |
|---|---|
| `core/risk/margin_calculator.py` (protocol) | **Untouched** — protocol stays v1; growing it breaks `MarginTracker` conformance (§2.5). |
| `core/execution/handler.py`, `portfolio_view.py`, `margin_tracker.py` | No consumer/gate/buying-power change (non-goals; S4). |
| `core/runtime/driver.py` | No startup-gate wiring of SPAN readiness in S3 (S4). |
| `scripts/fno_runner.py` | No composition-root swap / snapshot injection in S3 (S4). |
| `core/risk/span/span_repository.py`, `span_parser.py`, `span_pipeline.py`, `span_readiness.py`, `span_freshness.py`, `span_snapshot.py` | S2 data foundation is stable; S3 consumes, does not modify. |

### 9.2 Test files

| File | Purpose |
|---|---|
| `tests/risk/span/test_span_calculator.py` | **NEW.** R1–R6 (protocol conformance, metric-contract margin, exception family, incremental, import-absence), I1–I3 (multi-position, zero-price, determinism). |

### 9.3 Documentation files

| File | Change | Why |
|---|---|---|
| `docs/reports/MM9_IMPLEMENTATION_PLAN.md` | Tick `MM9.4-S3`; note the two conscious divergences (no GreeksCalculator at runtime; metric-key contract over per-scenario runtime repricing). | Keep the roadmap accurate; record the plan-line supersession (§3.6). |
| `docs/PROJECT_STATE.md` | SPAN margin **computation** present (S3); buying-power gate still BLOCKED/Planned #5 (S4 pending). | KB sync discipline. |
| `docs/CHANGELOG_PLATFORM.md` | "MM9.4-S3 — `SpanMarginCalculator`: first concrete `MarginCalculator`; SPAN scan + short-option-minimum + exposure margin from immutable `SpanSnapshot`; metric-key contract; no protocol/consumer/gate changes." | Changelog discipline. |
| `docs/architecture_decisions.md` | **Optional IN-note** (not a new ADR): record (a) the metric-key contract as the calculator's deferral seam, and (b) the no-Greeks divergence. ADR-007 already covers the seam; no new architectural decision needs a full ADR. | Durable record of the two conscious deviations. |
| `docs/SESSION_BOOTSTRAP.md` | "Current Gaps §8": SPAN now has computation; only the buying-power gate (S4) remains. | Bootstrap accuracy. |

---

## 10. Additional Design Questions — Explicit Answers

1. **How is a `SpanSnapshot` injected into the calculator?**
   As a constructed, validated DTO via `__init__(span_snapshot=…)`. The composition root (S4) loads it with
   `SpanRepository.load(active_version)`; the calculator never loads it (§2.1, §4). The calculator depends
   only on the `SpanSnapshot` **type**, never on the repository/parser/job.

2. **What lookup key uniquely identifies a contract's risk array?**
   The **canonical underlying symbol** (e.g. `"NIFTY"`), derived by `_underlying_for(instrument)`; one array
   serves all contracts on that underlying. `snapshot.risk_arrays.get(underlying)` (§3.1).

3. **How are futures and options handled differently?**
   Both look up the same per-underlying array and pay `scan_risk × units`. The **only** difference: a
   **short option** additionally pays `short_option_minimum × units` (§3.2); futures and long options do not.
   `units = abs(qty) × lot_size`, with the lot rule of §3.2.1 (futures fold lot into multiplier).

4. **How are unsupported instruments reported?**
   By raising `UnsupportedInstrument` (an asset class SPAN cannot margin) at compute time — never a silent 0,
   never a flat-rate fallback (§6 F-UNKNOWN-INST).

5. **How are missing risk arrays handled?**
   `MissingRiskArray` is raised when `risk_arrays.get(underlying)` returns `None`; `MissingRiskMetric` when a
   mandatory metric (`scan_risk`) is absent. Both are rejections, not fallbacks (§6).

6. **How is deterministic replay preserved?**
   No I/O, no clock, frozen snapshot, no caching; margin is a pure function of (snapshot, positions, prices).
   Replay loads the journaled `snapshot_date`+`file_hash` and reconstructs identical numbers (§5).

7. **Can the calculator be unit-tested without filesystem access?**
   Yes — and it is mandated. Tests hand-build a `SpanSnapshot` and inject it; the calculator imports no
   repository and opens no file (§8, R6, AC6). This is the concrete proof the DI boundary holds.

8. **What exceptions belong to the calculator vs the repository?**
   Calculator: `SpanMarginError` family (`UnsupportedInstrument`, `MissingRiskArray`, `MissingRiskMetric`) —
   input/lookup faults at compute time. Repository: `FileNotFoundError` / `ValueError` (and the parser's
   `UnsupportedSpanSchema`) — load/integrity/schema faults at startup. The calculator never sees or re-raises
   the repository's exceptions (§6, §0.1).

9. **Which exchange-specific calculations are intentionally deferred to later slices?**
   Deriving `scan_risk` from NSE's scenario array (→ offline parser); inter-month spread credits;
   inter-commodity spread credits; net option value / long-premium credit; delta/Greek-based repricing
   (→ offline); the buying-power gate formula (→ S4). All enumerated in §3.5. S3's margin is a conservative
   **upper bound** (no spread/NOV credits).

---

## 11. Explicit Non-Goals (S3 must NOT include any of these)

- Replacement of `MarginTracker` · composition-root changes · handler wiring · driver changes
- Buying-power changes (the gate formula) · startup-gate changes · telemetry · `PortfolioView` changes
- Persistence · runtime downloads · broker integration · optimisation
- **Growing the `MarginCalculator` protocol** (§2.5)
- MM9.4-S4 work · MM10 work
- Fabricating NSE metric-key names / ELM rate (flag as constants for confirmation)

---

## 12. Architecture Principles Preserved

| Principle | How S3 preserves it |
|---|---|
| **ADR-001 — Ledger Is Truth** | The calculator reads the live `position_tracker` (truth) on demand and holds no portfolio snapshot; it is downstream reference computation, mutating nothing (§5.2). |
| **ADR-003 — Deterministic Processing** | No I/O, no clock, frozen snapshot, no caching ⇒ `(snapshot, positions, prices) → margin` is pure; replay == live (§5). |
| **ADR-006 — Sole Orchestrator** | S3 adds no runtime path and no new handler caller; the calculator is constructed (S4) and invoked only inside the existing gate path (S4). |
| **ADR-007 — MarginCalculator Seam** | The calculator satisfies the protocol **structurally**, holds the `SpanSnapshot` as permitted immutable config (rule #1), exposes no admission policy (rule #2), uses no broker API (rule #4), and stays deterministic (rule #3). The protocol is **not** grown (§2.5). |
| Immutable DTOs | Consumes the frozen `SpanSnapshot`; never mutates it; stores no mutable portfolio state. |
| Dependency injection | Snapshot + tracker injected at construction; the calculator loads nothing (§4). |
| Stateless calculator | No positions/margin/equity cached; recomputed each call (§5.2, §7). |
| Deterministic replay | Hard snapshot equality + pure compute reconstructs identical margin (§5.3). |
| No runtime network I/O | Zero network/filesystem/broker access at compute time (§5.1). |
| Single source of truth | One immutable `SpanSnapshot` at the loader→calculator boundary (Design Q1); the live ledger for positions. |

---

## Appendix A — Calculator Surface (Authoritative for S4)

```
core/risk/span/span_calculator.py
  SpanMarginCalculator(position_tracker, span_snapshot, *, margin_rate=DEFAULT_EXPOSURE_MARGIN_RATE)
      margin_rate: float                                            # protocol field (exposure/ELM rate)
      get_exposure(current_prices, symbol=None) -> float           # protocol — gross notional
      get_used_margin(current_prices) -> float                     # protocol — total SPAN margin
      get_incremental_margin(instrument, quantity, side, prices) -> float   # S3-only; S4's gate consumes
  exceptions: SpanMarginError ⊃ {UnsupportedInstrument, MissingRiskArray, MissingRiskMetric}
  constants (flagged for confirmation): METRIC_SCAN_RISK, METRIC_SHORT_OPTION_MIN, DEFAULT_EXPOSURE_MARGIN_RATE
```

## Appendix B — Metric-Key Contract (Authoritative for the offline parser)

```
SpanRiskArray.risk_metrics must contain, per underlying:
  "scan_risk"              (mandatory)  worst-case per-contract-unit scenario loss   → reject if absent
  "short_option_minimum"  (optional)   short-option minimum per contract unit       → default 0.0
The offline parser (S2 schema) is responsible for reducing NSE's raw scenario array to "scan_risk".
```

## Appendix C — Slice Dependencies

```
MM9.4-S1 (COMPLETE: MarginCalculator protocol v1, ADR-007)
        │
MM9.4-S2 (COMPLETE: SPAN data foundation — SpanSnapshot DTO, repository, readiness)
        │
MM9.4-S3 (THIS SLICE: SpanMarginCalculator — consumes SpanSnapshot via DI; satisfies protocol v1; no swap)
        │
MM9.4-S4 (buying-power gate formula + composition-root swap MarginTracker → SpanMarginCalculator)
```

S3 must be green before S4 begins: the calculator and its `get_incremental_margin` must be stable before the
gate types against them and the composition root swaps the implementation.
