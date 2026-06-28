# MM9.4-S1 Implementation Specification
## MarginCalculator Protocol & SPAN Architecture

**Status:** PENDING IMPLEMENTATION
**Preceded by:** MM9.3-S3 — Drawdown Gate I.M.2 Full Fix (COMPLETE, 719 tests passing)
**Followed by:** MM9.4-S2 — SPAN Parameter Sourcing
**Date drafted:** 2026-06-28
**Type:** Architecture + specification only. **No production code. No patches. No commits.**

---

## 0. Reading Guide — S1 Code Scope vs S1 Document Scope

This specification has two distinct scopes, and conflating them is the single largest risk to
implementation quality.

| Scope | Content |
|---|---|
| **S1 CODE scope** (what an engineer ships) | One new protocol file (`core/risk/margin_calculator.py`), two type annotations (`ExecutionHandler.margin_tracker`, `PortfolioView.__init__`), one ADR, doc syncs. **Zero behaviour change. 719 tests stay green.** |
| **S1 DOCUMENT scope** (what this spec designs) | The complete target SPAN architecture: data lifecycle (§5), buying-power model (§6), failure modes (§7), migration path (§8). These are **designed here and implemented in S2–S4.** S1 ships only the protocol seam that makes them possible. |

Every section below states explicitly which scope it belongs to. When a section describes SPAN
data flow, buying power, or failure handling, it is describing the **future** architecture the
protocol enables — **not** code S1 writes. The non-goals (§ "Explicit Non-Goals") are the binding
boundary on S1 code.

**The S1 deliverable, in one sentence:** introduce the `MarginCalculator` abstraction that
`MarginTracker` already satisfies structurally, so that a future `SpanMarginCalculator` can be
substituted at the composition root with no change to any consumer — and document the SPAN
architecture that substitution will eventually carry.

---

## 1. Architectural Objectives

S1 has a single architectural purpose: **introduce the substitution seam between the execution
engine and the margin calculation, before any SPAN logic exists**, so that the eventual
`MarginTracker → SpanMarginCalculator` replacement is a one-line composition-root change rather
than a cross-cutting refactor of every consumer.

Concretely, S1 delivers:

1. **`MarginCalculator` protocol** — a `typing.Protocol` in `core/risk/margin_calculator.py`
   declaring exactly the surface that `MarginTracker`'s consumers call today (§2.3): `margin_rate`,
   `get_exposure`, `get_used_margin`. No more, no less.
2. **`MarginTracker` satisfies it structurally** — by *structural* conformance (no base class, no
   inheritance edge). `MarginTracker` is **not modified**. It already has every member the protocol
   declares.
3. **Consumers are typed to the protocol, not the concrete class** — `ExecutionHandler.margin_tracker`
   and `PortfolioView.__init__`'s `margin_tracker` parameter are annotated `MarginCalculator`. This
   is the line that makes the swap legal: a consumer typed to the protocol accepts any conforming
   implementation.
4. **ADR for the seam** — a new ADR records that `MarginCalculator` is the SPAN substitution point
   and that the abstraction is introduced *before* SPAN to avoid a big-bang migration.

This slice introduces **no new behaviour, no new gate, no new calculation, no SPAN logic, and no
runtime change**. After S1, the platform computes margin identically to before (flat 20% via
`MarginTracker`); the only change is that the *type* of the margin collaborator is now an
abstraction.

### 1.1 What S1 explicitly does NOT do

S1 does **not** implement SPAN, source SPAN data, change the gate formula, add buying-power
calculation, add methods for incremental margin, or touch the runtime. Those are S2–S4 (§8, and the
roadmap in `MM9_IMPLEMENTATION_PLAN.md` §4). S1 declares **only today's consumed surface** so that
`MarginTracker` conforms with zero code change. The protocol grows in later slices.

---

## 2. The MarginCalculator Protocol

### 2.1 Why this abstraction is required *before* SPAN

The current state (`MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §1, §9): `MarginTracker` is the
sole concrete margin type, named directly in three consumers. SPAN will replace the *calculation*
entirely (worst-case scenario loss instead of flat gross-notional × rate) but must preserve the
*consumer contract* — the gate, PortfolioView, and telemetry must keep calling the same methods.

Without the protocol, introducing `SpanMarginCalculator` in MM9.4-S3 forces a simultaneous edit of
every consumer in one slice — exactly the big-bang, high-consequence change the audit warns against
(`MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §7: "Any change to `process_signal`'s gating logic is
high-consequence — it is the sole execution path, ADR-006"). Introducing the seam first **decouples
the abstraction change (S1, zero behaviour) from the implementation change (S3, all behaviour)**.
S1 is the safe, reviewable, behaviour-preserving half of that split.

This mirrors the architecture-before-implementation pattern the plan already commits to
(`MM9_IMPLEMENTATION_PLAN.md` §3.3 D6): *"The correct SPAN seam is a `MarginCalculator` protocol
replacing `MarginTracker` itself (introduced in MM9.4)."* S1 is that introduction.

### 2.2 Interface

```python
# core/risk/margin_calculator.py
from typing import Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class MarginCalculator(Protocol):
    """
    The margin-calculation seam consumed by ExecutionHandler and PortfolioView.

    MarginTracker (core/execution/margin_tracker.py) satisfies this structurally
    today (flat-rate model). MM9.4-S3 introduces SpanMarginCalculator, a second
    implementation, substituted at the composition root with no consumer change.

    This protocol declares ONLY the surface consumed as of MM9.4-S1. SPAN-specific
    methods (incremental margin, scenario margin) are added in later slices when a
    consumer actually calls them — never speculatively (YAGNI; narrow scope).
    """

    margin_rate: float

    def get_exposure(
        self, current_prices: Dict[str, float], symbol: Optional[str] = None
    ) -> float:
        """Gross notional of open positions (all, or one symbol)."""
        ...

    def get_used_margin(self, current_prices: Dict[str, float]) -> float:
        """Estimated margin currently locked by open positions."""
        ...
```

The three members are **exactly** the surface grepped across `core/` (§2.3). Signatures are matched
byte-for-byte to `MarginTracker` so structural conformance holds without any change to the concrete
class.

### 2.3 Surface derivation (evidence)

The protocol surface is not a guess — it is the exact set of `MarginTracker` members reached by any
consumer. Verified by `grep -rn "margin_tracker\.\|margin_rate" core/`:

| Member | Consumer call sites | Evidence |
|---|---|---|
| `margin_rate: float` | gate incremental estimate | `handler.py:1162` (`* self.margin_tracker.margin_rate`) |
| `get_used_margin(prices)` | gate, telemetry, view | `handler.py:1159`, `handler.py:1198`, `portfolio_view.py:80` |
| `get_exposure(prices, symbol=None)` | view | `portfolio_view.py:79` |

**`get_exposure` is load-bearing and must not be omitted.** The MM9.4-S1 sketch in
`MM9_IMPLEMENTATION_PLAN.md` §4 lists only `margin_rate` + `get_used_margin` because it was written
from the gate's point of view. But `PortfolioView.snapshot()` calls `get_exposure` directly
(`portfolio_view.py:79`). If the protocol omits `get_exposure`, `PortfolioView` cannot be typed to
`MarginCalculator`, and the S3 substitution silently breaks PortfolioView's `gross_exposure` field.
The grep is the authority; the plan sketch is superseded by it.

### 2.4 `margin_rate` is a transitional member

`margin_rate` is included because the gate reads it today (`handler.py:1162`:
`_estimate_required_margin(...) * self.margin_tracker.margin_rate`) and S1 must not change
behaviour. It is, however, **a flat-rate artefact with no SPAN analogue** — SPAN has no single
portfolio-wide rate; margin is a non-linear function of strike distance, volatility, and Greeks
(`MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §7). The `_estimate_required_margin × margin_rate`
formula in the gate is exactly what MM9.4-S4 replaces with the buying-power model (§6, §8).

The protocol therefore carries `margin_rate` as a **transitional** member: required for S1
conformance, slated for removal when the gate migrates off the flat formula in S4.
`SpanMarginCalculator` will either expose a vestigial `margin_rate` (e.g. `0.0`, never read once S4
lands) or the member is dropped from the protocol in the S4 slice once no consumer reads it. S1 does
not decide S4's disposition; it only records the member as transitional.

### 2.5 No speculative SPAN methods on the S1 protocol

The protocol does **not** declare `get_incremental_margin`, `get_scenario_margin`,
`get_initial_margin`, `get_exposure_margin`, or any SPAN-specific method. Reasons:

1. **YAGNI / narrow scope** — no consumer calls them yet; S1 declares only the consumed surface.
2. **Backward compatibility** — declaring an unconsumed method would force `MarginTracker` to grow a
   stub to keep conforming, violating "no behaviour change" and the project convention against
   abstractions for one-time/future use (`CLAUDE.md` Development Conventions).
3. **Protocol growth is incremental** — when MM9.4-S4's gate calls `get_incremental_margin`, that
   slice adds the method to the protocol *and* the concrete `SpanMarginCalculator` together. The
   protocol surface always equals the consumed surface.

### 2.6 Responsibilities, ownership, lifecycle, invariants

| Property | Specification |
|---|---|
| **Responsibility** | Declare the margin-calculation contract consumed by execution + portfolio layers. It is a *type*, not a calculator — it computes nothing. |
| **Ownership** | Lives in `core/risk/` (alongside `core/risk/greeks/`). Owned by the risk domain because margin is a risk-engine concern (`PLATFORM_CONSTITUTION.md` §3); the execution layer *consumes* it. |
| **Lifecycle** | The protocol is a static type. It is never instantiated. Concrete implementations (`MarginTracker` today, `SpanMarginCalculator` future) have their own lifecycles, constructed at the composition root and injected. |
| **Invariant — statelessness** | A `MarginCalculator` is a pure read-projection over `PositionTracker`. It holds no position truth (ADR-001: Ledger Is Truth). It reads trackers + prices; it never mutates them. `MarginTracker` already honours this (`margin_tracker.py` — reads `position_tracker._positions`, writes nothing). |
| **Invariant — determinism** | Same tracker state + same `current_prices` → same result, every call, in live and replay (ADR-003). No wall-clock, no external I/O, no network call in any method. This forbids a `SpanMarginCalculator` that polls a broker margin API in the hot path (§5.7, §7; `MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §8). |
| **Invariant — one-directional dependency** | `risk → (reads) → execution trackers`. Never the reverse. Margin is downstream of the ledger. |

### 2.7 Deterministic guarantees

The protocol does not by itself enforce determinism — it is a type. But it **declares the contract
under which determinism is required**, and the ADR (§10) binds every implementation to it. The S1
GREEN bar (§9) includes a regression proof that the existing deterministic behaviour is unchanged.
Future implementations are bound by the ADR: any `MarginCalculator` that introduces non-determinism
(external API in a method body, wall-clock dependence) is a constitutional violation reviewable on
the same footing as a `Platform → Strategy` import (ADR-002), and is caught by the determinism
constraint in `MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §8.

---

## 3. Component Responsibilities

One responsibility per component; no overlapping ownership. The table is the authority for the S3/S4
slices that follow.

| Component | Single responsibility | What it does NOT do |
|---|---|---|
| **`MarginCalculator`** (protocol, NEW, `core/risk/margin_calculator.py`) | Declare the margin-calculation contract (the type). | Compute anything; hold state; know about SPAN. |
| **`MarginTracker`** (`core/execution/margin_tracker.py`, UNCHANGED) | The **current** concrete implementation: flat-rate margin from gross exposure. Satisfies `MarginCalculator` structurally. | Gate; reserve margin; know cash balance; persist; call brokers. |
| **`SpanMarginCalculator`** (FUTURE, MM9.4-S3, `core/risk/span/span_calculator.py`) | The **future** concrete implementation: scenario-based worst-case margin from SPAN parameters + `CanonicalInstrument` + Greeks. Will satisfy the (then-grown) `MarginCalculator`. | Exist in S1. Gate. Decide admission. Own cash. |
| **`ExecutionHandler`** (`core/execution/handler.py`, annotation only in S1) | Own the execution path and the margin **gate** (`_check_margin_budget`). Owns the admission *decision*; delegates the *calculation* to its `MarginCalculator`. | Compute margin itself; know SPAN internals. The gate calls protocol methods only. |
| **`PortfolioView`** (`core/execution/portfolio_view.py`, annotation only in S1) | Read-only projection: surface `gross_exposure` + `used_margin` in `PortfolioSnapshot` by delegating to its `MarginCalculator`. | Gate; mutate; compute margin itself. |
| **`CanonicalInstrument`** (`core/instruments/canonical.py`, UNCHANGED) | The economic-fact source SPAN will consume: `lot_size`/`multiplier`, `asset_class`, `underlying`, `strike`, `expiry`, `option_type`. | Compute margin. Cross broker/persistence/reconciliation boundaries (G1 / 4C.7 guard). |

**Ownership boundary that S1 establishes and S3/S4 must preserve:**
*Calculation* lives behind the `MarginCalculator` seam (S3 swaps the implementation). *Decision*
(admit/reject) lives in `ExecutionHandler._check_margin_budget` (S4 changes the formula). *Truth*
(positions, cash) lives in the trackers (ADR-001; never in the calculator). These three never merge.

---

## 4. Data Flow

The flow below is the **target** end-to-end margin path (Signal → Admission). S1 changes **none** of
the runtime arrows — it only changes the *static type* of the `MarginCalculator` node so the
implementation behind it is swappable. The arrows annotated **[S1]** are the only thing S1 touches
(a type annotation, not a runtime edge); all others are existing, unchanged behaviour.

```
SignalEvent
   │  (ADR-006: enters only via SignalSource → LoopDriver)
   ▼
LoopDriver._tick()  ──►  ExecutionHandler.process_signal(signal)
   │
   ▼
[PHASE 0]   Authority + idempotency guard                         (unchanged)
[0..4]      STOP/kill-switch/daily-limit/drawdown gates           (unchanged; drawdown via PortfolioView, MM9.3-S3)
[4b]        Position stacking guard                               (unchanged; load-bearing for margin non-double-count, §6.4)
[5]         _check_risk_limits → RiskManager.evaluate(order)      (unchanged; stays margin-free)
[9C]        _check_greek_limits → portfolio Greek gate            (unchanged; MM9.3-S1B)
   │
   ▼
[PHASE 1]   Instrument Resolution
   │  InstrumentResolver → CanonicalInstrument (lot_size, asset_class, strike, expiry)
   │  order.canonical_instrument is populated (handler.py:1153-1157)
   ▼
[PHASE 2]   RiskManager.evaluate(order)  → RiskDecision           (unchanged)
   │
   ▼
[PRICEABLE] _check_book_priceable()  → fresh-book preflight       (unchanged; MM9.2-S3)
   │
   ▼
[MARGIN]    _check_margin_budget(order, current_price)            ◄── the gate
   │
   │   reads Portfolio State:
   │     • prices  = {sym: snap.price for self._price_cache}      (handler.py:1158)
   │     • cash    = self.metrics.cash_balance                    (handler.py:1149,1164)
   │     • mult    = order.canonical_instrument.multiplier        (handler.py:1153)
   │
   │   delegates Margin Calculation to its MarginCalculator: ─────────────[S1: type is now the protocol]
   │     • used_current = margin_calculator.get_used_margin(prices)        (handler.py:1159)
   │     • incremental  = _estimate_required_margin(qty*mult, price)
   │                       * margin_calculator.margin_rate                  (handler.py:1160-1162)
   │
   │   computes Buying Power / admission test:
   │     • TODAY (S1):  utilisation = (used_current + incremental) / cash   (handler.py:1164)
   │     • FUTURE (S4): free_capital = cash - span_used; admit iff
   │                     span_incremental(order) ≤ free_capital            (§6, §8)
   ▼
Admission Decision:  (approved: bool, utilisation: float)         (handler.py:1165)
   │     • approved → continue to [PHASE 5] order_tracker.add_order → [PHASE 7] broker.place_order
   │     • rejected → MARGIN_BUDGET_EXCEEDED, order not built (C2: gate precedes add_order)
   ▼
[PHASE 5/7]  Order persisted + routed to broker                   (unchanged)
```

**Interactions documented:**

1. **Signal → Resolution.** `process_signal` resolves the order's `CanonicalInstrument` (Future via
   `core/execution/futures.resolve_future`, ADR-G1-W2; option via selector). The canonical object
   supplies `multiplier` (= lot_size) to the gate. SPAN (S3) will additionally read `asset_class`,
   `strike`, `expiry`, `option_type` from the same object — already populated, no new resolution.
2. **Resolution → Portfolio State.** The gate reads three portfolio facts at call time: the full
   `_price_cache` (all held symbols, MM9.2-S1), `cash_balance` (MM9.2-S4, now updates per session),
   and the order's multiplier. These are the inputs the calculator needs.
3. **Portfolio State → Margin Calculation.** The gate **delegates** to the `MarginCalculator`. This
   is the swap point. Today the methods run flat-rate arithmetic; after S3 the same method names run
   SPAN scenario arithmetic. The gate code is identical across the swap — **this is the property S1
   exists to guarantee.**
4. **Margin Calculation → Buying Power → Admission.** The gate combines the calculator's output with
   `cash_balance` into an admission test. Today: a utilisation ratio. After S4: a free-capital /
   buying-power test (§6). The *call site* (`process_signal` step [MARGIN]) is unchanged across all
   of MM9.4 — only the formula inside `_check_margin_budget` changes in S4.

**The boundary S1 protects:** between "Portfolio State" and "Margin Calculation" sits the
`MarginCalculator` seam. S1 makes that seam a typed abstraction so steps 3–4 can be re-implemented
(S3/S4) without re-touching steps 1–2 or the consumers.

---

## 5. SPAN Data Architecture

**DOCUMENT scope — designed here, implemented in MM9.4-S2/S3. S1 writes none of this.** This
section specifies the architecture the `MarginCalculator` seam will eventually carry, so that S2/S3
have no architectural decisions left to make. It is anchored on the determinism constraint already
fixed by the audit (`MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §8).

### 5.1 Source of SPAN data

**Decision: NSE-published daily SPAN parameter files are the primary source; the Upstox margin API
is rejected for the hot path.** NSE publishes daily SPAN risk parameter files (scanning ranges,
price-scan ranges, volatility-scan ranges, inter-month/inter-commodity spread charges) per
underlying. These are *static, reproducible files*, which is the decisive property: a replay must
compute the same margin as the live run it reproduces (ADR-003). An online broker API returns
time-varying, rate-limited, non-reproducible values and cannot be called in a deterministic gate
(`MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §8: *"This precludes any non-deterministic external
margin API call inside `process_signal`"*).

The Upstox margin API may be used **out-of-band** (offline reconciliation of our SPAN estimate vs
broker truth, a research/audit tool) but never inside `_check_margin_budget`.

### 5.2 Versioning

Each SPAN parameter set is a **versioned, immutable snapshot** keyed by the NSE publication date
(the trading day the parameters apply to). The version is recorded in the runtime event journal at
load time so every margin decision is attributable to an exact parameter version (Audit-First,
`CLAUDE.md`). A replay pins the same version the live session used.

### 5.3 Update cadence

NSE publishes SPAN files **daily** (and intra-day revisions on volatile days). The platform's update
cadence is therefore **daily, at startup**, parallel to the existing daily instrument-master refresh
(`scripts/fetch_instrument_master.py`, `MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §5). Intra-day
revisions are **not** consumed mid-session (would break determinism within a session); they are
picked up at the next startup.

### 5.4 Lifecycle

```
fetch (offline job)  →  versioned snapshot on disk  →  load-once at startup  →
frozen for the session  →  read-only in the gate  →  discarded at shutdown  →
next day: new version fetched
```

The snapshot is **loaded once at startup and frozen for the entire session.** No method reloads it
mid-session. This is the same load-once-freeze discipline that makes the gate deterministic.

### 5.5 Cache ownership

The loaded SPAN parameter set is owned by the `SpanMarginCalculator` instance (constructed at the
composition root, `scripts/fno_runner.py`, and injected as the handler's `MarginCalculator`). It is
**not** a global, not a singleton, not a module-level cache — ownership follows the same injection
pattern as every other collaborator (ADR-MM7E-1: the composition root constructs and injects). The
calculator holds the frozen parameter set as immutable instance state; its *methods* remain
stateless with respect to position/price inputs (the determinism invariant, §2.6).

### 5.6 Refresh strategy

Refresh is **at startup only**, via the offline fetch job feeding the load-once step. There is no
runtime refresh path into the calculator. The fetch job's cadence is operational (a scheduled OS
task, like the master refresh); the *load* is a startup-gate step (§5.8).

### 5.7 Stale-data policy

A SPAN snapshot is **stale** if its version date is older than the current trading day at startup.
Policy (binding, derived from ADR-004 + ADR-MM7F-1):

- **Stale at startup** → refuse to start (§7 F2). Trading on stale risk parameters is trading on
  data the platform cannot trust — the ADR-004 prohibition extended from prices to risk parameters
  (`MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §8, ADR-004 clause).
- **No mid-session staleness check** — the snapshot is frozen for the session by design (§5.4), so
  there is no "goes stale mid-session" condition for SPAN parameters (unlike market-data prices,
  which the watchdog already guards under ADR-004).

### 5.8 Startup behaviour

The SPAN load is a **startup-gate step**, slotted at the ordering the audit already fixed
(`MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §8): **after** `_check_master_readiness()` and
**after** `_canonicalize_restored_ledger()` (canonical identity must be verified before margin
references `ci.multiplier`/`ci.asset_class`/`ci.strike`), and **before** the tick loop runs. A
faulting or missing load at this step is a refuse-to-start (§7), consistent with the
`broker_positions` faulting-source contract (ADR-MM7F-1).

### 5.9 Runtime behaviour

At runtime the calculator's methods read the frozen snapshot, the position tracker, and the supplied
prices — and nothing else. No I/O, no network, no wall-clock. Same inputs → same margin, live and
replay (ADR-003).

### 5.10 Failure behaviour

See §7. The governing principle is **refuse > warn > fallback** (ADR-MM7F-1): a SPAN failure is
never silently replaced by a flat-rate fallback, because a wrong-but-confident margin number is more
dangerous than a loud refusal.

---

## 6. Buying Power Model

**DOCUMENT scope — defines relationships and ownership only. No formulas (explicit non-goal). The
admission *formula* is implemented in MM9.4-S4.** This section defines the three quantities and how
they relate, so S4 has the model fixed.

### 6.1 Definitions

| Term | Definition | Owner |
|---|---|---|
| **Required margin** | The margin a *proposed order* would additionally lock — the incremental SPAN initial margin + exposure margin for the new contract, given the current portfolio (SPAN nets correlated positions, so this is portfolio-dependent, not standalone). | `MarginCalculator` (S3 computes it; S1 protocol will gain the method in S4) |
| **Available margin** | Capital free to lock against new positions = portfolio equity − margin already used by open positions. | Derived in the gate from `cash_balance` (now session-updating, MM9.2-S4) and the calculator's `get_used_margin`. |
| **Buying power** | The admission capacity: how much *more* required margin the portfolio can absorb before exhausting available margin. Conceptually `buying_power = available_margin` measured against `required_margin(order)`. | The gate (`_check_margin_budget`), as the admission decision. |

### 6.2 How they relate

```
available_margin = equity − used_margin
admit(order)  ⇔  required_margin(order) ≤ available_margin
```

Stated as a rule, not a formula: **an order is admitted iff the margin it would require does not
exceed the margin currently available.** Buying power is the slack in that inequality.

### 6.3 Relationship to the current (S1) gate

S1's gate uses a **utilisation ratio**, not this buying-power model:

```
utilisation = (used_current + incremental_est) / cash_balance        # handler.py:1164
admit  ⇔  utilisation ≤ max_capital_utilisation                       # handler.py:1165
```

This is the *current* admission test and is unchanged by S1. MM9.4-S4 migrates it to the
free-capital / buying-power model above (§8). The two are not numerically identical — utilisation is
a ratio against gross cash; buying power is free capital against incremental requirement. S4 owns
that migration; S1 leaves the utilisation formula in place.

### 6.4 Non-double-counting invariant (carried forward)

The current gate's correctness depends on the **position stacking guard** (gate step [4b]):
`used_margin(all positions) + incremental(new order)` does not double-count only because
`process_signal` blocks a new entry on a symbol that already holds a position (`handler.py:1144-1148`
comment). This invariant is **inherited by the buying-power model**: if pyramiding is ever
introduced, both the utilisation gate and the future buying-power gate must exclude `order.symbol`
from the "already used" term. S1 changes nothing here but records the dependency so S4 preserves it.

---

## 7. Failure Modes

**DOCUMENT scope — deterministic handling designed here; implemented in MM9.4-S2/S3/S4. S1 ships no
failure-handling code** (S1's only failure surface is the protocol-conformance check, §9). Every
mode resolves to one of three platform idioms: **refuse-to-start** (ADR-MM7F-1), **trip kill switch**
(ADR-004), or **deterministic per-order rejection** — never a silent flat-rate fallback.

| # | Failure | When detected | Deterministic handling | Precedent |
|---|---|---|---|---|
| F1 | **SPAN data unavailable** (file absent at startup) | Startup gate load step (§5.8) | **Refuse to start.** Journal `MARGIN_PARAMS_UNAVAILABLE` → `alerter.critical` → `abort_startup()` → `STOPPED`. `bars_processed == 0`. | ADR-MM7F-1 (faulting source = startup refusal) |
| F2 | **Stale SPAN data** (snapshot older than trading day) | Startup gate load step | **Refuse to start.** Same shape as F1 (`MARGIN_PARAMS_STALE`). Trading on untrusted risk parameters is prohibited. | ADR-004 (no trading on stale data), §5.7 |
| F3 | **Corrupted SPAN data** (unparseable / schema-invalid file) | Startup gate load step | **Refuse to start.** `MARGIN_PARAMS_CORRUPT`. A partially-parsed parameter set is never used — all-or-nothing load. | ADR-MM7F-1; `refuse > warn > fallback` |
| F4 | **Missing instrument in SPAN set** (no parameters for an order's underlying) | Per-order, in the gate | **Reject the order deterministically.** `MARGIN_UNRESOLVABLE` rejection; order not built. Never fall back to flat-rate for the unmapped instrument (a silent regime change). The portfolio's other positions are unaffected. | `refuse > warn > fallback`; deterministic gate |
| F5 | **Missing expiry** (`CanonicalInstrument.expiry is None` for a derivative) | Per-order, in the gate (or earlier at resolution) | **Reject the order.** A derivative without an expiry cannot be SPAN-priced. Deterministic rejection, same shape as F4. `CanonicalInstrument._validate` already requires expiry for FUTURE/OPTION (`canonical.py:62-77`), so this is a defence-in-depth check, not the primary guard. | Canonical validation + deterministic gate |
| F6 | **Incomplete contract metadata** (missing strike/option_type/lot_size for a SPAN lookup) | Per-order, in the gate | **Reject the order.** SPAN cannot scenario-price a contract with incomplete economic facts. Deterministic rejection. (`CanonicalInstrument._validate` enforces OPTION completeness at construction — `canonical.py:64-74` — so this is also defence-in-depth.) | Canonical validation + deterministic gate |

**Cross-cutting rule:** startup-time failures (F1–F3) are **refuse-to-start** (the whole session is
unsafe). Per-order failures (F4–F6) are **single-order rejections** (the rest of the book is safe and
trading continues). Neither ever degrades to a flat-rate fallback — the flat-rate model is
`MarginTracker`, which is being *replaced*, not used as a SPAN safety net.

---

## 8. Migration Strategy

How the platform moves from flat-rate `MarginTracker` to SPAN `SpanMarginCalculator` without breaking
execution. The whole point of the S1 seam is that this migration is **incremental and
behaviour-gated at each step**, never a big bang.

```
            CURRENT                         S1 (THIS SLICE)                    S3/S4 (FUTURE)
   ┌────────────────────────┐     ┌────────────────────────────┐    ┌──────────────────────────┐
   │ ExecutionHandler        │     │ ExecutionHandler            │    │ ExecutionHandler          │
   │  .margin_tracker:        │     │  .margin_tracker:           │    │  .margin_tracker:         │
   │   MarginTracker  (concr.)│ ──► │   MarginCalculator (proto)  │──► │   MarginCalculator (proto)│
   │                          │     │   = MarginTracker (flat)    │    │   = SpanMarginCalculator  │
   └────────────────────────┘     └────────────────────────────┘    └──────────────────────────┘
        behaviour: flat 20%            behaviour: flat 20%               behaviour: SPAN
        (no abstraction)               (abstraction, SAME behaviour)     (NEW behaviour)
                                       ▲ ZERO behaviour change            ▲ behaviour change, gated
```

### 8.1 The four-step migration (plan §4 roadmap)

| Slice | Change | Behaviour change? | Risk |
|---|---|---|---|
| **MM9.4-S1** (this) | Introduce `MarginCalculator` protocol; type consumers to it. `MarginTracker` unchanged and still injected. | **None.** Flat-rate everywhere. | Minimal — type-only. 719 tests stay green. |
| **MM9.4-S2** | Source + version SPAN parameter files; design the scenario data model. No calculator yet. | None (data only). | Low — offline data plumbing. |
| **MM9.4-S3** | Implement `SpanMarginCalculator` satisfying the (grown) protocol. **Not yet injected** — constructed and unit-tested in isolation. | None in the running system (still `MarginTracker` injected). | Medium — new calculation, but not on the live path until S4. |
| **MM9.4-S4** | Composition root injects `SpanMarginCalculator`; gate formula migrates to buying-power (§6). | **Yes** — SPAN margin replaces flat-rate. Gated by full regression + characterization. | High — the behaviour switch. Isolated to one slice because S1–S3 prepared the seam. |

### 8.2 Why this preserves existing execution behaviour

- **S1 is provably behaviour-neutral**: `MarginTracker` is still the injected implementation; only
  the *type annotation* changes. Structural typing means `MarginTracker` conforms with no edit
  (§9). Every one of the 719 tests exercises the identical runtime object.
- **The swap is one line at the composition root** (S4: `MarginTracker(...)` →
  `SpanMarginCalculator(...)` in `scripts/fno_runner.py`). Because consumers are typed to the
  protocol (S1), no consumer changes when the implementation changes.
- **The gate call site never moves** across the whole migration. `_check_margin_budget` is called at
  the same point in `process_signal` (between PHASE 2 and PHASE 5) in S1, S3, and S4 — only its
  internal formula changes (S4). This is the property the plan commits to
  (`MM9_IMPLEMENTATION_PLAN.md` §3.10: *"MM9.4 replaces `MarginTracker` with `SpanMarginCalculator`
  … The gate method is unchanged"*).
- **Rollback is symmetric**: if S4's SPAN behaviour is wrong in production, reverting the one-line
  composition-root injection restores flat-rate behaviour instantly, because `MarginTracker` is never
  deleted until SPAN is proven.

### 8.3 Backward compatibility guarantees (S1)

- `MarginTracker` keeps its exact public surface and behaviour.
- All existing constructions `MarginTracker(position_tracker)` and
  `MarginTracker(position_tracker, margin_rate=...)` are unchanged.
- All existing `PortfolioView(pt, pnl, margin_tracker, ...)` constructions are unchanged (the
  parameter type widens from concrete to protocol — strictly more permissive).
- The handler's `_check_margin_budget`, `_estimate_required_margin`, and `get_stats` bodies are
  unchanged.

---

## 9. Testing Strategy

**S1 is a protocol introduction — there is no meaningful behavioural RED/GREEN cycle, and inventing
one would be theatre.** The honest verification of a type-only seam is conformance + regression. The
strategy below reflects that.

### 9.1 RED

A pure protocol intro has no failing-behaviour-then-passing-behaviour arc. The closest legitimate RED
is a **conformance assertion written before the protocol file exists**:

```
R1. test_margin_tracker_satisfies_margin_calculator_protocol
    from core.risk.margin_calculator import MarginCalculator   # ImportError until the file exists → RED
    assert isinstance(MarginTracker(position_tracker), MarginCalculator)
```

This is RED only because the module does not yet exist (ImportError). It is not a behavioural RED. It
is included for TDD discipline (write the test first) but the spec is explicit that the *real*
verification is §9.2–§9.4, not this synthetic failure.

### 9.2 GREEN — conformance (two layers, because `runtime_checkable` is not enough)

```
G1. Runtime structural check (attribute presence only):
    assert isinstance(MarginTracker(pt), MarginCalculator)  → True
    LIMIT (state explicitly): @runtime_checkable isinstance verifies ATTRIBUTE/METHOD
    PRESENCE, not signatures. It would pass even if get_exposure had the wrong
    parameters. It is necessary but not sufficient.

G2. Static type check (the actual signature-level GREEN):
    Run mypy (or pyright) over core/. The annotations
      ExecutionHandler.margin_tracker: MarginCalculator
      PortfolioView.__init__(..., margin_tracker: MarginCalculator, ...)
    type-check against MarginTracker's real signatures. A signature mismatch
    (e.g. protocol omits get_exposure, or wrong parameter types) is a static
    type error. THIS is the real conformance proof — not the runtime isinstance.
```

If the repository does not currently run mypy/pyright in CI, S1's GREEN bar is: (a) G1 passes, and
(b) a one-off `mypy core/risk/margin_calculator.py core/execution/handler.py
core/execution/portfolio_view.py` run is clean and its output recorded in the slice's DoD evidence.

### 9.3 Integration

```
I1. test_portfolio_view_accepts_margin_calculator_typed_collaborator
    Construct PortfolioView(pt, pnl, MarginTracker(pt), portfolio_greeks=None).
    snapshot() returns gross_exposure and used_margin identical to pre-S1 values
    (same flat-rate numbers). Proves the type widening did not change behaviour.

I2. test_handler_margin_gate_unchanged_under_protocol_annotation
    Existing _check_margin_budget tests run against the handler whose
    margin_tracker is annotated MarginCalculator. Same approve/reject decisions,
    same utilisation values, as pre-S1.
```

### 9.4 Regression

```
RG1. Full suite: all 719 existing tests pass, unmodified. Zero behaviour change is
     the headline acceptance signal. Any test that changes value is a defect in S1.
```

### 9.5 Acceptance criteria

| # | Criterion |
|---|---|
| AC1 | `core/risk/margin_calculator.py` exists, defining `@runtime_checkable` `MarginCalculator(Protocol)` with exactly `margin_rate: float`, `get_exposure(current_prices, symbol=None) -> float`, `get_used_margin(current_prices) -> float`. |
| AC2 | `MarginTracker` is **unmodified** and `isinstance(MarginTracker(pt), MarginCalculator)` is `True`. |
| AC3 | `ExecutionHandler.margin_tracker` is annotated `MarginCalculator`; the injected object is still `MarginTracker` (composition root unchanged in S1). |
| AC4 | `PortfolioView.__init__`'s `margin_tracker` parameter is annotated `MarginCalculator`; all existing constructions still type-check. |
| AC5 | Static type check (mypy/pyright) over the three touched files is clean. |
| AC6 | The protocol declares **no** SPAN-specific methods (no `get_incremental_margin`, etc.). |
| AC7 | All 719 existing tests pass with **zero value changes** (behaviour-neutral). |
| AC8 | New conformance tests (R1/G1/I1/I2) are green. |
| AC9 | A new ADR records the `MarginCalculator` seam decision (§10). |
| AC10 | `MarginTracker` is **not** made a subclass of the protocol (structural conformance only — no `class MarginTracker(MarginCalculator)`; no `execution → risk` import on the concrete class). |

### 9.6 Definition of Done

- [ ] `core/risk/margin_calculator.py` created — `MarginCalculator` protocol, three members, docstring noting `margin_rate` transitional + no speculative SPAN methods.
- [ ] `ExecutionHandler.margin_tracker` annotated `MarginCalculator` (import from `core.risk.margin_calculator`).
- [ ] `PortfolioView.__init__` `margin_tracker` parameter annotated `MarginCalculator`.
- [ ] `MarginTracker` untouched (verify `git diff core/execution/margin_tracker.py` is empty).
- [ ] Composition root (`scripts/fno_runner.py`) untouched — still injects `MarginTracker` (S1 does not swap).
- [ ] `tests/risk/test_margin_calculator.py` — conformance tests (R1/G1) green.
- [ ] `tests/execution/test_portfolio_view*.py` + margin-gate tests — I1/I2 green, no value changes.
- [ ] Static type check clean over the three files; output recorded.
- [ ] All 719 prior tests pass.
- [ ] New ADR added to `docs/ARCHITECTURE_DECISIONS.md`.
- [ ] Doc syncs (§10) committed.

---

## 10. File-by-File Implementation Plan

### 10.1 Production files

| File | Change | Why |
|---|---|---|
| `core/risk/margin_calculator.py` | **NEW.** Define `@runtime_checkable MarginCalculator(Protocol)` with `margin_rate`, `get_exposure`, `get_used_margin`. | The seam itself. Lives in `core/risk/` because margin is a risk-domain concern (`PLATFORM_CONSTITUTION.md` §3), alongside `core/risk/greeks/`. |
| `core/execution/handler.py` | **Annotation only.** `self.margin_tracker: MarginCalculator = MarginTracker(self.position_tracker)` (handler.py:195); import the protocol. `_check_margin_budget`/`_estimate_required_margin`/`get_stats` bodies unchanged. | Types the primary consumer to the abstraction so S4 can swap the implementation with no handler edit. `execution → risk` import is a clean direction; `risk` is not in the ADR-002 forbidden set, and `PortfolioGreeks` is already imported here (handler.py:204). |
| `core/execution/portfolio_view.py` | **Annotation only.** `margin_tracker: MarginCalculator` in `__init__` (portfolio_view.py:51) and the import. Body unchanged. | The second consumer (`get_exposure` at :79, `get_used_margin` at :80). Without this, PortfolioView still names the concrete class and the S3 swap breaks it (§2.3). |

**Not modified in S1 (and why):**

| File | Reason |
|---|---|
| `core/execution/margin_tracker.py` | Satisfies the protocol structurally with no change (the whole point). Modifying it would break "zero behaviour change". |
| `scripts/fno_runner.py` | Composition root still injects `MarginTracker`. The swap to `SpanMarginCalculator` is S4, not S1. |
| `core/instruments/canonical.py` | SPAN will *read* it (S3); S1 reads nothing new. |
| `core/runtime/driver.py` | No runtime change in S1 (explicit non-goal). |

### 10.2 Test files

| File | Change | Why |
|---|---|---|
| `tests/risk/test_margin_calculator.py` | **NEW.** R1 (import/conformance), G1 (`isinstance`), and a test asserting the protocol surface is exactly the three members (guards against speculative SPAN-method creep, AC6). | Verifies the seam exists and `MarginTracker` conforms. |
| `tests/execution/test_portfolio_view.py` (+ `_greeks` variant) | **Possibly touched** only if a test asserts the concrete type of the `margin_tracker` parameter. I1 added. Existing value assertions must stay green unchanged. | Proves the annotation widening is behaviour-neutral for the view. |
| `tests/execution/test_margin_gate*.py` (existing margin-gate tests) | **Not modified.** I2 reuses them as the regression that the gate decision is unchanged. | Behaviour-neutrality of the handler gate. |

### 10.3 Documentation files

| File | Change | Why |
|---|---|---|
| `docs/ARCHITECTURE_DECISIONS.md` | **NEW ADR** — "MarginCalculator Protocol Is the SPAN Substitution Seam." Records: the seam is introduced before SPAN to split the abstraction change (S1, zero behaviour) from the implementation change (S3/S4, all behaviour); structural conformance; `margin_rate` transitional; determinism + ADR-001/003/006 binding on all implementations. The §3.3 D6 rationale in the plan already exists; this ADR ratifies it. | The seam *decision* is made at S1, so the ADR belongs here — not deferred to MM9.4 completion. |
| `docs/reports/MM9_IMPLEMENTATION_PLAN.md` | Tick MM9.4-S1; note the protocol surface correction (`get_exposure` included, plan §4 sketch superseded by the grep, §2.3). | Keeps the plan's MM9.4-S1 entry accurate. |
| `docs/PROJECT_STATE.md` | Note: margin seam abstracted; SPAN still BLOCKED/Planned #5 (unchanged — S1 is preparation, not delivery). | KB sync discipline. |
| `docs/CHANGELOG_PLATFORM.md` | Entry: "MM9.4-S1 — `MarginCalculator` protocol introduced; consumers typed to the seam; zero behaviour change; SPAN substitution point established." | Changelog discipline. |
| `docs/SESSION_BOOTSTRAP.md` | "Current Gaps §8" updated: the SPAN gap now has a defined seam; SPAN implementation still pending (S2–S4). | Bootstrap accuracy. |

---

## Explicit Non-Goals (S1 code must NOT include any of these)

- SPAN formula implementation · exchange-specific calculations · broker-specific logic
- portfolio offsets · option-strategy recognition · spread credits
- optimization · performance tuning · caching implementation · persistence
- UI · telemetry changes · runtime changes (`driver.py` untouched)
- buying-power *formulas* (§6 defines relationships only; the formula is S4)
- speculative SPAN methods on the protocol (`get_incremental_margin`, scenario margin, etc.)
- swapping the injected implementation (composition root stays `MarginTracker`)
- modifying `MarginTracker`
- MM9.4-S2 work · MM10 work · any `InstrumentParser.parse()` [9C] change

---

## Architecture Principles Preserved

| Principle | How S1 preserves it |
|---|---|
| **ADR-001 — Ledger Is Truth** | The protocol declares a *read-projection* contract; every implementation reads trackers, never mutates. Margin is never a source of position truth. |
| **ADR-002 — Platform/Strategy Separation** | The protocol lives in `core/risk/`; consumers import from `risk` (a permitted direction — not in the forbidden set; `PortfolioGreeks` already crosses it). No strategy coupling. |
| **ADR-003 — Deterministic Processing** | The protocol's determinism invariant (§2.6) binds every implementation: no external I/O / wall-clock in any method; replay == live. SPAN data is load-once-frozen (§5). |
| **ADR-006 — Sole Orchestrator** | The margin gate stays inside `process_signal` on the single execution path. The seam adds no parallel path, no second caller. |
| Deterministic execution | Preserved — S1 changes types only; behaviour byte-identical. |
| Single source of truth | The calculator is downstream of the ledger; the seam does not create a second truth. |
| Stateless calculators | The protocol's statelessness invariant is explicit (§2.6); frozen SPAN params are immutable instance state, methods stay stateless w.r.t. inputs. |
| Immutable DTOs | `PortfolioSnapshot` unchanged (frozen). No new mutable state. |
| Dependency injection | The implementation is injected at the composition root (ADR-MM7E-1); S1 types the injection point to the abstraction. |
| Backward compatibility | Zero behaviour change; all existing constructions/tests pass unmodified (§8.3). |

---

## Appendix A — Protocol Surface (Authoritative)

Derived from `grep -rn "margin_tracker\.\|margin_rate" core/` (§2.3), **not** from the plan sketch:

```python
@runtime_checkable
class MarginCalculator(Protocol):
    margin_rate: float                                                      # handler.py:1162  (transitional, §2.4)
    def get_exposure(self, current_prices: Dict[str, float],
                     symbol: Optional[str] = None) -> float: ...            # portfolio_view.py:79
    def get_used_margin(self, current_prices: Dict[str, float]) -> float: ...  # handler.py:1159,1198 / portfolio_view.py:80
```

## Appendix B — Slice Dependencies

```
MM9.3-S3 (COMPLETE) ──► MM9.4-S1 (THIS SLICE: protocol seam, zero behaviour)
                              │
                              ▼
                        MM9.4-S2 (SPAN parameter sourcing)
                              │
                              ▼
                        MM9.4-S3 (SpanMarginCalculator implementation)
                              │
                              ▼
                        MM9.4-S4 (buying-power gate; composition-root swap)
```

S1 must be green before S2 begins: the protocol surface must be stable before SPAN work types
against it.
