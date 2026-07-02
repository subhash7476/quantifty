# ARCHITECTURE_DECISIONS.md

Architecture Decision Records (ADRs) for `F:\Nifty`. Each ADR is a durable record of a binding decision. ADRs are append-only; supersede rather than edit. All initial ADRs derive from `docs/PLATFORM_CONSTITUTION.md` v1.0.

**Status legend:** Proposed · **Accepted** · Superseded · Deprecated.

---

## ADR-001 — Ledger Is Truth

**Status:** Accepted (2026-06-04)

### Context
A trading platform receives position/PnL signals from multiple authorities — the exchange, the broker API, the execution engine, internal trackers, and the dashboard. These can disagree (broker API lag, partial fills, UI staleness). Without a single declared source of truth, components silently diverge and a position can become ambiguous or untraceable.

### Decision
The platform's **internal ledger is the primary source of truth**. The authority order is fixed:

`Exchange → Broker → Execution Engine → Ledger → Risk Engine → Dashboard`

No dashboard, strategy, or broker API response may override ledger truth. Position/PnL truth lives in the execution trackers (`position_tracker`, `pnl_tracker`) and the persistence repositories; the dashboard and facades are **read-only** consumers.

### Alternatives Considered
- **Broker API as source of truth** — rejected: broker responses lag, are rate-limited, and lack internal intent (idempotency, grouping); trusting them blindly causes double-counting and reconciliation loops.
- **Dashboard/derived state as truth** — rejected: presentation layer must never feed back into trading state (hidden side effects, Principle 3).
- **No declared authority (eventual consistency)** — rejected: produces untraceable positions, violating §7.

### Consequences
- A durable, reconstructable ledger (persistence repos) is mandatory; recovery restores from it.
- Reconciliation exists to *detect and correct* divergence against the broker, not to let the broker overwrite the ledger.
- The dashboard/facades must stay read-only; any write path through the UI is a violation.

---

## ADR-002 — Platform / Strategy Separation

**Status:** Accepted (2026-06-04)

### Context
The repository was salvaged from a monolith that mixed execution infrastructure with many strategies, indicators, ML pipelines, and research. That coupling made the platform unstable: strategy churn destabilized infrastructure, and infrastructure changes broke strategies.

### Decision
The platform is **strategy-agnostic**. The only permitted dependency direction is `Strategy → Platform`; `Platform → Strategy` is **forbidden**. The platform must remain usable when **no strategies exist**. Strategies, alpha/market-regime research, ML training, backtesting, and scanners live **outside** this repository (§4–§5).

### Alternatives Considered
- **Keep strategies in-repo behind interfaces** — rejected: proximity invites coupling; the monolith proved this fails in practice.
- **One repo, enforced only by convention** — rejected: convention without a hard rule erodes; a binary import rule is checkable.
- **Strategy plugins loaded by the platform** — rejected for now: a plugin registry owned by the platform risks `Platform → Strategy` coupling; deferred unless a strict consumer-only seam is proven.

### Consequences
- Enforced by a checkable invariant: **no `core.strategies|runner|backtest|state|models|ftmo` import anywhere in the platform** (verified empty at adoption).
- Surviving strategy-coupled code (`CaptureEngine`/`metrics_service` inputs, `legacy_adapter.save_signal`, strategy DDL in the shared schema) is **soft residue** to be refactored out, not new violations.
- The platform is testable and deployable headless (Flask + options dashboard boot with zero strategies).

**MM11 resolution note (2026-07-01):** the three "soft residue" items listed above are now resolved: `CaptureEngine`/`metrics_service` removed (MM11.1), `legacy_adapter.save_signal` removed (MM11.1), strategy-specific DDL pruned (MM11.4). See `docs/reports/MM11_REMOVAL_LEDGER.md`.

---

## ADR-003 — Deterministic Event Processing

**Status:** Accepted (2026-06-04)

### Context
Live/backtest divergence is the dominant source of trading-system bugs: code that behaves one way in research and another in production. Hidden side effects and multiple execution paths make trades unexplainable and irreproducible.

### Decision
The platform maintains **deterministic operation**: a **single execution path**, a **single position truth**, **deterministic event processing**, and **auditable state transitions**. Time is data-driven (a `Clock` advanced by bar timestamps) so live and backtest traverse the *same* code path. Hidden side effects are prohibited.

### Alternatives Considered
- **Separate live and backtest engines** — rejected: guarantees divergence; doubles maintenance and trust cost.
- **Multi-threaded/event-driven concurrency in the core loop** — rejected: nondeterministic ordering breaks reproducibility and auditability; the orchestrator is single-threaded by design.
- **Wall-clock-driven processing** — rejected for the trade path: makes backtests non-reproducible. (Wall-clock is used only for operational concerns like heartbeat/staleness, never the trade decision path.)

### Consequences
- The deterministic loop (single orchestrator) is a required platform pillar; it is currently **absent** in `F:\Nifty` (the scaffold is to be extracted from `core/runner.py`).
- Every trading action must be explainable from recorded state (supports §7 audit trail).
- Operational wall-clock logic (staleness, heartbeat) is kept clearly separate from the deterministic trade clock.

---

## ADR-004 — No Trading On Stale Data

**Status:** Accepted (2026-06-04)

### Context
A silent market-data feed failure is among the most dangerous live-trading conditions: the process appears healthy while acting on stale prices, or stops trading without anyone noticing. Silent failure is unacceptable (§6).

### Decision
Data integrity is mandatory. The platform **monitors feed freshness, detects stale data, alerts operators, and activates protective controls** (trips the kill switch) when data goes stale during market hours. Trading on stale market data is prohibited.

### Alternatives Considered
- **Trust the feed; rely on broker rejects** — rejected: broker won't reject an order priced on stale-but-valid data; the hazard is undetected.
- **Alert only, no automatic control** — rejected: an alert without a protective control still permits stale-data trades in the gap before a human reacts.
- **Halt on any single missed tick** — rejected: too brittle; a threshold (5 minutes without a new bar, during market hours) balances safety and false-trips.

### Consequences
- `RuntimeWatchdog` (`core/execution/watchdog.py`) implements detection + heartbeat and trips `ExecutionHandler.activate_kill_switch` on staleness. It exists and is tested.
- It is **passive**: a loop driver must call `record_bar` / `check_data_staleness` / `write_heartbeat`. Until ADR-003's loop exists, this obligation is **operationally unmet**.
- Staleness checks are gated to market hours and use wall-clock time (consistent with ADR-003's separation).

---

## ADR-005 — Execution Before Alpha

**Status:** Accepted (2026-06-04)

### Context
It is tempting to prioritize signal quality (indicators, models, predictions). But poor execution — wrong fills, lost orders, inaccurate positions, unenforced risk — destroys more capital than mediocre signals, and does so unrecoverably. The platform's value is reliability, not prediction.

### Decision
**Execution quality outranks signal quality.** The platform prioritizes order correctness, fill tracking, position accuracy, risk enforcement, and reconciliation **over** indicators, models, predictions, and research outputs. The platform is explicitly **not responsible for generating alpha**.

### Alternatives Considered
- **Alpha-first platform with execution as a thin wrapper** — rejected: makes execution an afterthought; the monolith's instability came from exactly this.
- **Equal priority** — rejected: under conflict (e.g., a signal wants to trade but risk/reconciliation is uncertain), the platform must default to execution safety, so the ordering must be explicit.

### Consequences
- Investment goes to execution/ledger/risk/reconciliation/observability first; indicators and models are out of scope (reinforces ADR-002).
- Risk-before-trading (Principle 4: size, risk, stop, margin, clearance) is enforced in `ExecutionHandler` regardless of signal conviction.
- "Margin-aware execution" depth (SPAN) and the F&O product model are prioritized execution work, ahead of any predictive capability.

---

## ADR-006 — Deterministic Loop Driver Is The Sole Runtime Orchestrator

**Status:** Accepted (2026-06-04)

### Context
ADR-003 mandates a **single execution path** and deterministic event processing, but it does not name *what* owns that path at runtime. The platform now has all the components a trade touches — `SignalSource` (the strategy-agnostic seam), `LoopDriver` (specified in `docs/DRIVER_SPECIFICATION.md`), `ExecutionHandler`, and the ledger — but `ExecutionHandler.process_signal(...)` is a public method any caller could invoke. Without a binding rule, a strategy, a dashboard action, a one-off script, a broker-adapter callback, or a utility could submit trading intent **directly** to `ExecutionHandler`, bypassing the driver. That is precisely the "multiple execution paths" pathology that destabilised the monolith (ADR-002 Context, ADR-003 Context): trades that skip the loop are nondeterministic, unobservable (no heartbeat/telemetry/journal wiring), and unprotected (no staleness gate, no startup reconciliation gate). The single execution path needs a single, named owner.

### Decision
All trading activity inside `F:\Nifty` must enter the platform through one path only:

`SignalSource → LoopDriver → ExecutionHandler → Ledger`

No strategy, dashboard, broker adapter, script, or utility may bypass the `LoopDriver` and submit trading intent directly to `ExecutionHandler`. The `LoopDriver` is the **sole runtime orchestrator**: it is the only component that calls `ExecutionHandler.process_signal(...)` in a running process. Any new way to introduce trading intent must be expressed as a `SignalSource` implementation driven by the `LoopDriver` — never as a new caller of the handler.

**Future contributors must not create alternative runtime orchestration paths.** A second loop, a "fast path", a direct script-to-handler call, or a dashboard write-through is a constitutional violation, reviewable on the same footing as a `Platform → Strategy` import (ADR-002).

This decision is grounded in four principles:
- **Deterministic Processing (Principle 3, ADR-003):** one orchestrator ⇒ one ordering ⇒ live == replay; multiple callers reintroduce nondeterminism.
- **Single Execution Path (Principle 3):** the driver *is* that path; naming a sole owner makes the principle checkable, not aspirational.
- **Platform / Strategy Separation (Principle 5, ADR-002):** strategies inject intent only through the abstract `SignalSource` seam; they never hold or call the handler.
- **Execution Before Alpha (Principle 2, ADR-005):** every trade is forced through the handler's risk/idempotency/kill-switch gates because there is no path that skips them.

### Alternatives Considered
- **Allow direct `process_signal` calls from "trusted" scripts** — rejected: trust is not a control. Multiple entry points are multiple execution paths; each bypasses the observability and safety wiring the driver guarantees, and reproducibility is lost the moment a second caller exists (violates ADR-003).
- **Multiple specialised orchestrators (one per book — futures, options)** — rejected: divergent loops produce divergent ordering, recovery, and observability, and break single position truth. One neutral driver hosts all books behind the seam (DRIVER_SPECIFICATION.md §5.3).
- **A push model where sources call into the handler when they choose** — rejected for the same reason DRIVER_SPECIFICATION.md §5.2 rejects it: push destroys deterministic ordering and the single-thread guarantee.
- **Convention only, no ADR** — rejected: convention without a binding, reviewable rule erodes (the lesson of ADR-002). This ADR makes "bypassing the driver" an explicit violation.

### Consequences
- `ExecutionHandler.process_signal(...)` has **exactly one runtime caller**: the `LoopDriver`. (Unit tests and mock-broker flows may call it directly — that is test scope, already present in `handler.py`, and is not a runtime path.)
- Every new runtime entry point (a new strategy, a discretionary console, a replay tool) must implement `SignalSource` and be driven by the `LoopDriver` — not wired to the handler.
- Heartbeat, telemetry, the runtime event journal, staleness protection, and the startup reconciliation gate are **guaranteed for all trades**, because the one path that wires them is the only path that exists.
- Code review gains a checkable invariant: any new call site of `ExecutionHandler.process_signal` outside the `LoopDriver` (and tests) is a violation to be rejected, analogous to the `Platform → Strategy` import scan (ADR-002).
- The dashboard/facades remain read-only (ADR-001); this ADR closes the remaining write-path loophole by forbidding a UI action from reaching the handler directly.

---

# Implementation Notes (non-ADR)

These are durable engineering notes that record a *decision in flight* — not new ADRs, and not amendments to the accepted ADRs above (which remain append-only). They exist so a known, deliberate interim implementation is not later rediscovered as a bug.

## IN-001 — Kill-switch event ownership consolidation (relates to ADR-004, ADR-006)

**Status:** **Resolved** (LoopDriver Phase G closed, 2026-06-07). `KILL_SWITCH_ACTIVATED` is now emitted from a **single observation of the handler's kill-switch edge** (`_kill_switched` False→True) in `LoopDriver._check_kill_switch`, run each tick after routing and the watchdog drive — so every cause (stale data via the watchdog, drawdown, broker fault, daily-trade-limit) is journaled **exactly once**, regardless of cause, and in replay/paper as well as live. The data-health **proxy emission was removed** from `_drive_watchdog`; `WATCHDOG_STALE_DATA` continues to be emitted there. Edge-triggered via a `_kill_switch_was_active` latch. TDD: `tests/runtime/test_driver_kill_switch.py` (handler-caused trip now journaled — the former gap) + the rewired stale-data tests (watchdog trips the shared handler, as production). The narrative below is retained as the decision record.

**Context.** The `KILL_SWITCH_ACTIVATED` runtime-journal event records that trading was halted. The kill switch itself is owned by `ExecutionHandler` (`_kill_switched`, set by `activate_kill_switch`). It can be tripped by several causes — stale data (the `RuntimeWatchdog`, ADR-004), and, once execution routing lands, drawdown / broker failure / daily-trade-limit inside the handler.

**Current source (interim, watchdog phase / Phase E).** While the loop is execution-free, the *only* kill-switch cause the driver can observe is the watchdog's staleness trip. The `LoopDriver` therefore emits `KILL_SWITCH_ACTIVATED` from a **data-health proxy**: the `watchdog.data_healthy` True→False edge (the watchdog flips health and calls `activate_kill_switch` synchronously). This keeps the driver free of any `ExecutionHandler` reference (preserving ADR-006 for the watchdog phase) and is edge-triggered (no per-tick duplication).

**Future source (target, Phase G).** When execution routing introduces other kill-switch causes, emission must move to a **single source of truth**: one observation of the handler's kill-switch edge (`_kill_switched`, the private-attr coupling acknowledged in DRIVER_SPECIFICATION.md §10.7). The data-health **proxy emission for the kill-switch line must then be removed** from the watchdog path, so a single stale-data trip is not journaled as `KILL_SWITCH_ACTIVATED` twice (once by the proxy, once by the handler-edge observer). `WATCHDOG_STALE_DATA` continues to be emitted from the watchdog path — only the kill-switch line consolidates.

**Goal.** Exactly one `KILL_SWITCH_ACTIVATED` per kill-switch activation, sourced from the handler's kill-switch edge, regardless of cause.

*Ref: docs/DRIVER_SPECIFICATION.md §9, §10.7; docs/PROJECT_STATE.md (Planned #1 implementation note); ADR-004, ADR-006.*

---

## IN-002 — Dual PortfolioView Instances (MM9.3-S2/S3)

**Status:** **Resolved** (MM9.3-S3 closed, 2026-06-28).

### Context

`PortfolioView` (`core/execution/portfolio_view.py`) is a read-only projection over the three financial trackers (`position_tracker`, `pnl_tracker`, `margin_tracker`). It computes `mtm_equity`, `gross_exposure`, `used_margin`, and portfolio Greeks from a supplied price snapshot. Two independent callers need portfolio state at different lifecycle points: the LoopDriver needs it for telemetry publishing (per cadence), and the `ExecutionHandler` needs it for the per-signal drawdown risk gate. Both are read-only (ADR-001: Ledger Is Truth — a projection is not a source of truth) and both consume the same underlying trackers.

Reusing the same `PortfolioView` instance across both callers would require threading it from the composition root (`fno_runner.py`) into the handler's constructor — a coupling that crosses the driver-handler boundary and adds lifecycle ordering constraints. Creating two instances that wrap the same trackers incurs zero state duplication (the view is stateless; it holds only references).

### Decision

Two `PortfolioView` instances exist, each bound to its caller's scope:

1. **Driver's `portfolio_view`** (S2 — `core/runtime/driver.py`): constructed in `fno_runner.py` and injected into `LoopDriver.__init__`. Used in `_build_positions()` on each telemetry cadence to produce the enriched positions payload. Serves observability.

2. **Handler's `_handler_portfolio_view`** (S3 — `core/execution/handler.py`): constructed in `ExecutionHandler.__init__`. Used in the drawdown gate (`process_signal` step 4) to compute `mtm_equity` across the full `_price_cache`. Serves risk evaluation.

Both wrap the same three tracker instances (`self.position_tracker`, `self.pnl_tracker`, `self.margin_tracker`) and share the same `PortfolioGreeks` aggregator (`self.portfolio_greeks`). Neither mutates state. No locking is required (ADR-003: deterministic single-threaded runtime).

### Consequences

- The driver and handler each own their projection — no cross-boundary dependency.
- Adding a third consumer in a later slice (e.g., a watchdog equity check) follows the same pattern: construct locally.
- The `PortfolioView` constructor remains lightweight (four reference assignments); the cost of a second instance is negligible.
- The `portfolio_greeks` parameter is injected in both instances but consumed only in the driver's telemetry path today — the handler's drawdown gate reads only `mtm_equity`.

*Ref: core/execution/portfolio_view.py; core/runtime/driver.py; core/execution/handler.py; docs/reports/MM9_3_S2_IMPLEMENTATION_SPEC.md §2.4; ADR-001, ADR-003.*

---

## IN-003 — IV/TTE Fallback Strategy in Portfolio Greek Computation (MM9.3-S1B/S2)

**Status:** **Resolved** (MM9.3-S2 closed, 2026-06-28).

### Context

`PortfolioGreeks.calculate_portfolio_greeks()` (`core/risk/greeks/portfolio_greeks.py`) computes portfolio-level Greeks for both the risk gate (`_check_greek_limits`, S1B) and the telemetry projection (`PortfolioView.snapshot()`, S2). Its signature requires `volatilities` and `time_to_expiry_map` per symbol. In the current S1B/S2 implementation, both callers pass **empty dicts** for these parameters:

```python
greeks = self._portfolio_greeks.calculate_portfolio_greeks(
    market_prices=current_prices,
    volatilities={},
    time_to_expiry_map={},
)
```

`PortfolioGreeks` applies safe defaults inside its per-position loop:
- **IV:** `volatilities.get(symbol, 0.20)` — 20% volatility default.
- **TTE:** `time_to_expiry_map.get(symbol, 0.0)` — zero time to expiry.

### Decision

The empty-dict fallback strategy is accepted as a documented limitation for MM9.3. The rationale:

1. **TTE=0.0 is intrinsically safe.** `Black76Engine.calculate()` at T=0 returns delta as `+1` (ITM call), `-1` (ITM put), or `0` (OTM) — intrinsic value only. Gamma and vega are zero (no curvature or vol sensitivity at zero time). There is no divide-by-zero or NaN path (`black76_engine.py:32-39`).

2. **Conservative delta limits.** The intrinsic-only delta reported at TTE=0 is *more conservative* for OTM positions (delta=0, underestimating exposure) and correct for ITM positions (delta=±1). The limit check (`delta > max_portfolio_delta`) treats an underestimated delta as safer — the gate may pass when it should block, but will never block when it should pass.

3. **Telemetry Greeks are observational.** The S2 telemetry payload carries the same TTE=0 Greek values. Consumers (dashboards, operators) see the same conservative snapshot the risk gate evaluates against. There is no consumer-side expectation of IV smile or theta accuracy.

4. **MM9.5 is the planned resolution.** A future MM9.5 slice will source per-position IV from the options feed and TTE from the canonical instrument's expiry field, passing real values through the callers. The empty-dict fallback ensures the API surface is correct (callers already pass the right parameter names) while requiring zero plumbing work today.

### Consequences

- All Greek values computed for option positions in S1B/S2 are TTE=0 intrinsic: delta is sound, vega and gamma are zero, theta is zero, rho is zero.
- Equity and futures Greeks are unaffected (they dispatch through `GreeksCalculator`'s equity/future branches, which read neither IV nor TTE).
- Operators must not rely on the telemetry `portfolio_greeks.vega` or `portfolio_greeks.theta` values for trading decisions until MM9.5.
- The flag `TODO(MM10)` on `InstrumentParser.parse()` in the S1B code marks the future canonical-resolver migration path for per-position IV/TTE sourcing.

*Ref: core/risk/greeks/portfolio_greeks.py; core/risk/greeks/greeks_model.py; core/risk/greeks/greeks_calculator.py; core/risk/greeks/black76_engine.py; docs/reports/MM9_3_S2_IMPLEMENTATION_SPEC.md §2.3; docs/reports/MM9_3_IMPLEMENTATION_SPEC.md §2.4.*

---

## ADR-007 — MarginCalculator Protocol Is The SPAN Substitution Seam

**Status:** **Accepted** (2026-06-28) · MM9.4-S1.

### Context

The platform's margin model is currently a flat-rate calculator (`MarginTracker`, `core/execution/margin_tracker.py`) that multiplies gross notional exposure by `margin_rate` (default 0.20). This is insufficient for real option-selling margin, which requires SPAN-based scenario analysis. Replacing `MarginTracker` in-place would require changing every consumer's import and type annotation — a mechanical burden that discourages the replacement. Furthermore, the current implementation couples the margin model to the `core/execution/` package, where the flat-rate calculator lives beside the trackers it reads.

### Decision

A **`MarginCalculator` Protocol** (`core/risk/margin_calculator.py`) defines the abstract margin-computation seam. The protocol specifies the surface that any margin implementation must satisfy:

* `margin_rate: float` — the margin requirement fraction.
* `get_exposure(current_prices, symbol=None) -> float` — gross notional exposure.
* `get_used_margin(current_prices) -> float` — estimated margin consumed.

The protocol is a `typing.Protocol` — it is satisfied **structurally**, not by inheritance. `MarginTracker` satisfies it without subclassing, import change, or any code modification. The protocol lives in `core/risk/` (alongside Greeks), not in `core/execution/` (where the trackers live), reinforcing that margin computation is a risk-domain concern, not an execution concern.

**Consumers are typed to the abstraction.** Both `PortfolioView.__init__` and `ExecutionHandler.__init__` declare their `margin_tracker` parameter/attribute as `MarginCalculator`, not `MarginTracker`. This means a future `SpanMarginCalculator` (MM9.4-S3/S4) can be dropped in place with zero consumer changes.

**Protocol boundaries (hard rules):**

1. **Statelessness.** Implementations must never cache positions, margin, or equity. Immutable configuration (e.g., SPAN parameters loaded at construction) is permitted — portfolio state is not.
2. **Responsibility boundary.** `MarginCalculator` computes margin. `ExecutionHandler` decides admission. The calculator must never expose business-policy methods such as `can_trade(...)`, `approve(...)`, or `reject(...)`.
3. **Determinism.** Future `SpanMarginCalculator` implementations must remain deterministic. SPAN parameters sourced from exchange data are immutable once loaded. No runtime I/O, no runtime downloads, no runtime broker queries.
4. **No broker API at execution time.** Broker APIs must never be consulted during margin calculation. Broker APIs are permitted only for offline reconciliation, diagnostics, and research — never for execution-time margin computation.

### Alternatives Considered

- **`MarginTracker` as abstract base class** — rejected: requires inheritance and a subclass for every margin model; the flat-rate implementation would need to become a subclass, coupling it to the seam.
- **Duck typing only (no Protocol)** — rejected: consumers would have no enforceable contract; a future implementor could omit required methods without static detection.
- **Functional interface (single `calculate_margin(current_prices) -> float` function)** — rejected: discards `margin_rate` metadata that telemetry and reporting consume, and cannot be type-checked structurally across implementations.
- **Protocol in `core/execution/`** — rejected: margin is a risk-domain concern; placing the seam in `core/risk/` keeps the abstraction co-located with the SPAN/Greeks family and avoids creating a cross-domain dependency from the risk model to the execution package.

### Consequences

- `MarginTracker` is unchanged — no subclass, no import change, no code modification. It satisfies `MarginCalculator` structurally.
- Consumers are typed to `MarginCalculator`, making the `SpanMarginCalculator` swap purely a composition-root change.
- The protocol enforces the SPAN-refactoring preconditions (statelessness, determinism, no broker API) by contract, preventing future implementations from accidentally introducing runtime I/O or caching.
- The four boundary rules are documented and reviewable.
- `MarginCalculator Protocol v1` is the versioned contract; future versions may extend the surface.
- **MM9.4-S3 (2026-06-28):** `SpanMarginCalculator` (`core/risk/span/span_calculator.py`) is the first concrete implementation. It satisfies the protocol structurally (no inheritance), consumes immutable `SpanSnapshot` risk arrays, and exposes a calculator-only `get_incremental_margin()` method not on the protocol.
- **MM9.4-S4 (2026-06-28):** Composition swap complete. `fno_runner.py` conditionally constructs `SpanMarginCalculator` (with snapshot) or `MarginTracker` (fallback). `driver.py` includes a SPAN readiness gate (LIVE + derivatives + snapshot present). The margin gate uses `get_incremental_margin()` via capability detection. `MarginTracker` is unchanged; `MarginCalculator` protocol is unchanged. **The SPAN integration program is complete.**

*Ref: core/risk/margin_calculator.py; core/execution/margin_tracker.py; core/execution/portfolio_view.py; core/execution/handler.py; docs/reports/MM9_4_S1_IMPLEMENTATION_SPEC.md; ADR-003 (determinism), ADR-005 (execution before alpha).*

---

## ADR-G1-W2 — Future Resolution Through Canonical Instrument

**Status:** **Accepted** (2026-06-09) · Gate G1 Wave 2, Migration Target #1.

### Context
`InstrumentParser.parse` (`core/instruments/instrument_parser.py`) recognizes only an Option regex and an Equity fallback — it has **no Future branch**, despite `core/instruments/future.py` existing. The `ExecutionHandler.process_signal` non-option order-build branch (`handler.py:513`) called `parse` directly, so every futures-style symbol (e.g. `NIFTY26JUNFUT`) was constructed as an **`Equity`** and the order was mistyped `EQUITY` (**F-PARSE-1**, pinned by the Wave 2A characterization suite). The canonical instrument architecture (4C.1–4C.6) already owns the authoritative identity (`InstrumentResolver` → `CanonicalInstrument`), but the live order-build path did not consume it for futures.

### Decision
The `ExecutionHandler` order-build path now attempts **canonical future resolution before** legacy `InstrumentParser` parsing. A new `core/execution/futures.resolve_future(symbol, timestamp, resolver=None)` regex-detects a future symbol, resolves a `CanonicalInstrument` via `InstrumentResolver.resolve_future`, and **derives a legacy `Future` from it** (the `Future` is what flows into `NormalizedOrder`). Non-future symbols return `None` and fall through to the unchanged `parse` (equity/option behavior is identical).

**`CanonicalInstrument` is the identity source but remains internal.** Only its economic facts (underlying, expiry, lot_size) are read to build the legacy `Future`; the canonical object **may not cross**:
- broker boundaries
- persistence boundaries
- restore boundaries
- reconciliation boundaries

This is the load-bearing **G1 / 4C.7 boundary**: G1 makes canonical the *source* and keeps the broker payload byte-for-byte unchanged; the moment a payload reads `ci.instrument_key` / `ci.product`, that is 4C.7 (a behavior change) and stays blocked.

**Determinism (ADR-003):** the FUTURE *type* is decided by the symbol shape, not by master presence — a master-absent resolve still derives a `Future` (from symbol-parsed fields), so the order type never flips on DB presence.

### Consequences
- A futures-style symbol now types **`FUTURE`** with `symbol`/`side`/`quantity`/`order_type` byte-identical (broker payload preserved). Equity/option paths unchanged.
- **Scope is site #1 only** (`process_signal` non-option branch). `process_group_signal` (#2), the option-via-selector path (#4), the restore path, `InstrumentParser`, `UpstoxAdapter`, `PaperBroker`, reconciliation, and persistence schemas are untouched.
- The `orders` table has no `instrument_type` column, so the type correction has **zero persistence footprint** — a value correction, not a format change.
- **Gate G1 remains OPEN**: this closes one migration site; the remaining sites (restore, option, position) and the Section-6 closure proof remain.

*Ref: docs/reports/G1_WAVE2_IMPLEMENTATION_REPORT.md; docs/reports/SOLE_IDENTITY_PATH_REVIEW.md; docs/reports/G1_WAVE2A_BROKER_PAYLOAD_REVIEW.md; core/execution/futures.py; core/execution/handler.py; ADR-003, ADR-006.*

---

## ADR-MM7E-1 — The Production Composition Root Injects `SignalSource`, It Does Not Construct It

**Status:** **Accepted** (2026-06-12) · Phase MM7E.1 composition-root scope challenge.

### Context
ADR-006 binds all trading intent to one path — `SignalSource → LoopDriver → ExecutionHandler → Ledger` — and names the `LoopDriver` the sole runtime orchestrator, but it does not say *who constructs the object graph* in production. The first production **composition root** — the F&O entry script that constructs a live `LoopDriver` (`scripts/fno_runner.py`, the Planned #4 live-enablement track) — does not yet exist; today `LoopDriver(...)` is constructed only under `tests/`. The MM7E review (`docs/reports/MM7E_ENTRY_SCRIPT_REVIEW.md`) maps the five objects that root must wire (`ExecutionHandler` `load_db_state=True` → `PaperBroker` → `RealTimeClock` → live `MarketDataProvider` → `build_master_readiness`) and identifies the one collaborator that carries judgment — the production `SignalSource` (W1) — as the sole gateway to alpha, the MM7C C4 chain-parity obligation, and F4 live-lot sizing. The open question (MM7E.1): **does the entry script construct a production `SignalSource` (Design A), or accept one by dependency injection (Design B)?**

### Decision
The production composition root **constructs the four mechanical collaborators** (`LoopDriver`, `ExecutionHandler`, `PaperBroker`, provider) and **accepts `SignalSource` via dependency injection** — a typed parameter with a not-None refusal before the driver is built. **MM7E does not own `SignalSource` construction.** It depends only on the C1–C6 *consumer protocol* (`core/runtime/signal_source.py`), never on any concrete strategy/source module. The first concrete source — minimal-deterministic or real-strategy — is deferred to a later slice that wires the terminal root.

This is the production-shaped continuation of the seam ADR-006 already mandates and MM7D.1 already proved: `source` is an existing `LoopDriver.__init__` parameter, MM7D.1 *injected* a synthetic source rather than constructing one, and Design B promotes that exact injection from test-local to the runner's signature. **MM7E requires the seam for a source, not a production source.**

The refusal contract is preserved at the composition root, not relocated into `run()`: the script asserts `source is not None` before constructing the driver (the T1 acceptance predicate), keeping `source` optional on the driver for the legitimate inert replay path while making "a live run needs a source" a hard refusal at the root.

### Alternatives Considered
- **Design A — root constructs a "minimal deterministic" production source** — rejected. Even a no-alpha source is new production code MM7E must author and own, with its own correctness burden and a standing temptation to grow toward the real strategy; it drags the slice's risk profile from "mechanical plumbing, fully netted by MM7C+MM7D.1" toward alpha + chain-parity + F4, collapsing two roadmap slices into one under-netted slice. It also couples MM7E by import to a concrete source module.
- **Make `run()` raise when `source is None`** — rejected: that breaks the legitimate inert replay/Phase-C path. The refusal belongs at the composition root (the script), not inside the driver.
- **Defer the entire entry script until a real strategy source exists** — rejected: the composition root is independently testable and independently valuable (it proves recovery → readiness → canonicalization → reconciliation → watchdog end-to-end at `ExecutionMode.PAPER` with no capital at risk). Injection lets the root land and run its full gate against a test-double/minimal source now.

### Consequences
- The entry script is **pure plumbing**: zero source-risk surface (no alpha, no MM7C C4 chain provider, no F4 enters MM7E), zero import edge to any strategy module, smallest production root (four constructed objects, not five).
- **W1 ("no production `SignalSource` exists") leaves MM7E's critical path entirely** and becomes solely the later strategy slice's concern. MM7E's acceptance tests inject doubles (as the MM7A `_fno_live_contract` predicate already asserts only `source is not None`).
- Honest boundary: Design B makes MM7E a **partial** composition root, not the terminal one — terminal source construction (and the single file that can run live unaided) relocates to the strategy slice. This is correct: the slice that owns alpha owns wiring the real source.
- Consistent with **ADR-006** (intent enters only via the `SignalSource` seam driven by the `LoopDriver`), **ADR-002** (no `Platform → Strategy` coupling — the root names no concrete source), and **ADR-005** (execution-before-alpha — the de-risked execution root ships first, the alpha-bearing source later).
- This sharpens the review body's §7-1/§8.1 mitigation from "ship a minimal source" to "inject the source"; it does not alter the runtime target (`Mode.LIVE`/`ExecutionMode.PAPER`, §3), the refusal contract (§4), the G1-protected activation sequence (§5), or the characterization net (§6).

*Ref: docs/reports/MM7E_ENTRY_SCRIPT_REVIEW.md (§10 scope challenge; §0–§9 entry-script map); docs/reports/MM7C_SIGNALSOURCE_CHARACTERIZATION.md (C1–C6); docs/reports/MM7D1_SYNTHETIC_WIRING_PROOF.md; docs/PROJECT_STATE.md (Completed — Phase MM7E); docs/CHANGELOG_PLATFORM.md (2026-06-12); core/runtime/signal_source.py; core/runtime/driver.py; ADR-002, ADR-005, ADR-006.*

---

## ADR-MM7F-1 — A Faulting Broker-Positions Source Is A Startup Refusal

**Status:** **Accepted** (2026-06-12) · Phase MM7F #6a (hazard W3 resolution).

### Context
The startup gate (Phase F, guaranteed by ADR-006) reconciles the restored ledger against broker truth before the driver reaches RUNNING. The broker book is supplied by an injected `broker_positions: Callable[[], List[Dict]]`, and that callable can fault — broker auth/transport failure (`upstox_adapter.py:60-62` raises `RuntimeError` on HTTP 401/403). Hazard **W3** (`MM7_LIVE_WIRING_REVIEW.md` §3.2): `self._broker_positions()` is invoked inside `_reconcile_ledger`, which runs **before** `run()`'s `try/finally` (`driver.py:524`), so a raise propagated **uncaught out of `run()`**, stranding the driver in `RECOVERY` with no `STOPPED`, no journal record, and no alert. That is the most dangerous failure mode for a trading runtime: a process that looks alive but silently never started — indistinguishable from health. MM7F §F4 established that W3 is a **driver-gate property, independent of the (#6b) broker-positions shape adapter** — it can and should be fixed on its own.

### Decision
**A broker-positions source that raises is a refuse-to-start — never a fallback, retry, or swallow.** `_reconcile_ledger` wraps the single broker-book read in `try/except` and routes any exception into the **existing reconciliation refusal contract**: `RECONCILIATION_FAIL` (durable journal) → `alerter.critical` → `abort_startup()` → `STOPPED`; the gate returns `False`, so the deterministic loop never runs (`bars_processed == 0`). An **unverifiable** broker book is thereby treated exactly like an **inconsistent** one (a real position divergence) and a master-readiness **BLOCK** — the same `RECONCILIATION_FAIL`/`abort_startup` shape. `except Exception` (not a bare `except`) is used so `KeyboardInterrupt`/`SystemExit` still propagate.

**The refusal lives inside the gate** — not in `run()`'s `try/finally`, and not in the composition root (`scripts/fno_runner.py`). There is one owner for the contract: consistent with ADR-MM7E-1, the entry script must **not** wrap the callable in its own `try/except`.

### Alternatives Considered
- **Catch in `run()`'s `try/finally`** — rejected: that block covers only the loop *after* the gate; it would produce an `ERROR` finalize rather than the `STOPPED` refuse-to-start lifecycle, and it would separate the broker-source failure from its `RECONCILIATION_FAIL` sibling.
- **Swallow / treat as an empty book (fall back to a vacuous reconcile)** — rejected: starting live while unable to read the broker book is precisely the unvalidated-ledger trade that ADR-001/ADR-004 prohibit. Fallback is never appropriate for a trading runtime: **refuse > warn > fallback**.
- **Retry inside the gate** — rejected (YAGNI for #6a): startup is not the place to mask a persistent auth/transport fault. A transient-retry policy, if ever wanted, belongs to the broker adapter (#6b), not the gate.
- **Wrap the callable in the composition root** — rejected: it would duplicate the contract and hide it from the driver's own gate; the refusal is the gate's responsibility (MM7 §3.2).

### Consequences
- A live F&O run **cannot silently start blind** to the broker book; the failure is loud (critical alert) and durable (`RECONCILIATION_FAIL` + `STOPPED` journaled).
- The MM7A **T3** characterization net flipped from defect-pin to refusal-pin (`tests/runtime/test_driver_broker_positions_failure.py`) — behavior is now pinned: no escape, `STOPPED`, `RECONCILIATION_FAIL` + `STOPPED` journaled, critical alert, `bars_processed == 0`.
- **Scope: gate hardening only** — no adapter, no reconciliation-logic change, no broker change, `ExecutionMode.LIVE` untouched. The `broker_positions` **shape adapter** (W2) and the broker-`trading_symbol`↔internal-key mapping that give LIVE reconciliation *teeth* remain **#6b** (behind F4). At `ExecutionMode.PAPER` `broker_positions=None`, so this path does not execute (PaperBroker's book is permanently empty — MM7F §F2).
- Consistent with **ADR-001** (reconciliation detects and refuses divergence; a broker fault never passes silently and never overwrites the ledger), **ADR-004** (no trading on data you cannot trust — extends "stale" to "unreadable"), **ADR-006** (the single gate that guarantees reconciliation now guarantees it even when the broker source faults), and **ADR-MM7E-1** (the refusal stays in the gate, not the composition root).

*Ref: docs/reports/MM7F_6A_W3_GATE_HARDENING_REPORT.md; docs/reports/MM7F_BROKER_POSITIONS_ADAPTER_REVIEW.md (§F4); docs/reports/MM7_LIVE_WIRING_REVIEW.md §3.2 (W3); core/runtime/driver.py (`_reconcile_ledger`); tests/runtime/test_driver_broker_positions_failure.py; docs/PROJECT_STATE.md (Planned #6a — DONE); docs/CHANGELOG_PLATFORM.md (2026-06-12); commit d3a4390; ADR-001, ADR-004, ADR-006, ADR-MM7E-1.*

---

## ADR-MM7J3 — `instrument_token` Is The Sole Reliable Reconciliation Key; `trading_symbol` Is Unreliable

**Status:** **Accepted** (2026-06-15) · Phase MM7J.3 #6b.3 (R1 implementation; route frozen at MM7I).

### Context
`reconcile()` matches internal ledger keys against broker position keys by raw string. The internal ledger is keyed on the order's `instrument_token` (e.g. `NSE_FO|53001` — `place_order` sends `"instrument_token": order.symbol` at `upstox_adapter.py:86`; the fill keys `PositionTracker._positions` on that same value). The broker's `/portfolio/short-term-positions` response uses `trading_symbol` as its human display key — the compact form (`NIFTY26JAN2623500CE`) confirmed by MM7J.0/MM7J.1 to yield 0 rows in the spaced master (`NIFTY 20350 CE 30 JUN 26`). A shape-only adapter passing `trading_symbol` as the reconcile `symbol` would orphan every live derivative position — a false divergence → startup refusal on every run. MM7I froze the namespace-resolution route as R1 (composition-root re-key on `instrument_token`). MM7J.2 preserved `instrument_token` on `BrokerPosition`. This ADR records the #6b.3 R1 implementation.

### Decision
**`instrument_token` is the sole reliable reconciliation key for positions the platform opened.** `trading_symbol` is not used for reconciliation identity.

At the composition root, the broker book is re-keyed by `instrument_token` before the shape adapter:

```
broker.get_positions()           → Dict[str, BrokerPosition]  (keyed on trading_symbol)
rekey_broker_positions_by_token  → Dict[str, BrokerPosition]  (keyed on instrument_token)
to_reconcile_positions           → List[Dict]                  (symbol = instrument_token)
reconcile()                      → alerts                       (both sides match)
```

Implemented in `core/brokers/token_rekey.py`. G1-clean: uses `pos.instrument_token` (the `BrokerPosition` attribute), never the literal string `instrument_key`.

Positions with `instrument_token is None` are **excluded from the reconcile input** and returned as **`UNRECONCILABLE_UNMAPPED_POSITION`** pre-alerts — distinct from `ORPHANED_BROKER_POSITION` (`ORPHANED` = present at broker, absent internally; `UNRECONCILABLE` = cannot be mapped into the key space). Cause metadata in `internal_value`: `"missing_token"` for `None`; `"unknown_token"` reserved. Tolerates `None` per MM7J.2 design.

### Alternatives Considered
- **`trading_symbol` → master lookup (R2 / 4C.8)** — rejected (MM7I): blocked on the paused 4C chain; compact form has 0 master coverage; R1 is deterministic and sufficient.
- **Forward `trading_symbol` as `UNRECONCILABLE` to reconcile** — rejected: produces `ORPHANED_BROKER_POSITION` for every position the platform opened — a false-divergence → startup refusal.
- **`CanonicalInstrument` lookup** — rejected: `CanonicalInstrument` must not cross the broker-payload boundary (G1 / 4C.7); `instrument_token` already equals the ledger key by construction.

### Consequences
- `trading_symbol` is not a reconciliation identity — must not be used as a reconcile key by any future work.
- `UNRECONCILABLE_UNMAPPED_POSITION` is the correct alert for a None-token position; `ORPHANED_BROKER_POSITION` is not.
- Live-wiring at the LIVE rung remains deferred: bind `broker_positions=lambda: to_reconcile_positions(rekey_broker_positions_by_token(broker.get_positions())[0])` at `fno_runner` LIVE rung, gated on a first-hand authenticated non-empty position capture.
- Full suite **522 passing, 0 failing**.

*Ref: core/brokers/token_rekey.py; tests/runtime/test_reconcile_symbol_namespace.py; docs/reports/MM7I_NAMESPACE_ROUTE_DECISION.md; docs/reports/MM7J0_R1_PRECONDITIONS.md; docs/CHANGELOG_PLATFORM.md (2026-06-15); ADR-001, ADR-MM7F-1.*

---

## ADR-008 — SpanRiskArray `scan_risk` Unit Convention

**Status:** Accepted (2026-06-29) · MM9.5 Architecture Reconciliation.

### Context

ADR-007 introduced the `MarginCalculator` protocol and the `SpanMarginCalculator` (MM9.4-S3) as the first concrete implementation. ADR-007's protocol boundaries explicitly deferred the canonical unit of `scan_risk` to be confirmed against a real NSE SPAN file ("to be confirmed" — a placeholder the reconciliation now closes).

The MM9.4-S3 implementation (`core/risk/span/span_calculator.py`) assumed **Strategy A**: `scan_risk` is a dimensionless fraction of notional, and computed margin as `notional × max(scan_risk, short_option_min) × margin_rate`. The method was named `_risk_percentage`, encoding the fraction assumption in its name.

Reverse-engineering the actual NSE NSCCL SPAN file (`reference/span/nsccl.20260625.i01.spn`, PC-SPAN format 4.00, 57.2 MB) revealed that risk array (`<ra><a>`) values are in **absolute Rs per lot-unit** — verified empirically: NIFTY worst-case RA value = 2244.36 Rs/lot-unit × 75 lot-units = Rs 168,327 per lot, consistent with published NSCCL margin requirements. Strategy A would produce an absurd result (notional × 2244 → notional × a price).

### Decision

`scan_risk` in `SpanRiskArray.risk_metrics["scan_risk"]` stores **absolute Rs per lot-unit**. It is never a fraction of notional, and the current underlying price plays no role in the scan margin calculation.

**Canonical formula:**

```
units  = abs(qty) × lot_size
margin = units × scan_risk
```

`short_option_minimum` is also in Rs per lot-unit (0.0 for index options — NSE does not impose SOM on NIFTY/BANKNIFTY index options; `<somTiers/tier/rate/val>` = 0 in the real file). The effective per-position scan margin is:

```
margin = units × max(scan_risk, short_option_minimum)
```

**Derivation of `scan_risk` from RA values:** the `<ra>` element contains 16 `<a>` scenario values. The sign convention in the PC-SPAN 4.00 file is: **positive RA = loss to position holder, negative RA = gain**. The worst-case loss is:

```
scan_risk = max(0, max( weight[i] × RA[i]  for i in 0..15 ))
```

where scenarios 15 and 16 (1-indexed) carry weight=0.3 (extreme up/down move); all other scenarios carry weight=1.0. The parser must perform this reduction before populating `risk_metrics["scan_risk"]`. The `max(0, ...)` clamp ensures that an all-gain RA (all values negative) produces a zero margin.

**The `MarginCalculator.margin_rate` multiplier is retained** — it represents a regulatory or house additional buffer applied on top of the scan range, not a substitute for the scan risk itself.

### Alternatives Considered

- **Strategy A — scan_risk as fraction of notional** — rejected: empirically falsified by the real NSE SPAN file. RA values for NIFTY are in the 2000–2244 Rs range; a "fraction" of 2244 applied to any position notional is nonsensical. Verified: 2244.36 × 75 lots = Rs 168,327 ≈ published NSCCL margin (~9.3% of notional at NIFTY 24,000).
- **Parse RA weighted-average (all 16 scenarios)** — rejected: SPAN defines initial margin as the **worst-case** (maximum loss) across scenarios, not an average; the averaging interpretation understates required margin.

### Consequences

- `SpanMarginCalculator._single_span_margin` (MM9.4-S3) contains the wrong formula and must be corrected in MM9.5-S2: replace `notional * risk_pct * margin_rate` with `units * scan_risk * margin_rate`, remove the price dependency from the scan margin path, rename `_risk_percentage` to reflect the Rs/lot semantics.
- The parser (MM9.5-S1) must emit `scan_risk` as the worst-case Rs/lot-unit value derived from the 16-scenario RA reduction; it must also explicitly emit `short_option_minimum = 0.0` (not omit the key — the current calculator raises `MissingRiskMetric` on absence).
- No consumer outside `core/risk/span/` is affected by the unit choice: `MarginCalculator.get_used_margin` returns Rs, and the upstream callers (`_check_margin_budget`, `PortfolioView`) consume only the Rs result.
- This decision supersedes the "to be confirmed" placeholder in ADR-007 and closes gap G-1 from `docs/reports/SPAN_XML_SCHEMA_AND_MM9_MAPPING.md`.

*Ref: core/risk/span/span_calculator.py; docs/reports/SPAN_XML_SCHEMA_AND_MM9_MAPPING.md (G-1); docs/reports/MM9_5_ARCHITECTURE_RECONCILIATION.md (D1, D2); reference/span/nsccl.20260625.i01.spn; ADR-007.*

---

## ADR-009 — ParserRegistry Input Contract: Raw Bytes

**Status:** Accepted (2026-06-29) · MM9.5 Architecture Reconciliation.

### Context

`ParserRegistry` (`core/risk/span/span_parser.py`) was written with the type annotation `Dict[str, Callable[[dict], SpanSnapshot]]` — parser functions were expected to receive a pre-parsed `dict`. The function intended to be registered is named `parse_span_csv`, suggesting a CSV format.

The real NSE SPAN file is a binary XML document (PC-SPAN format 4.00, CRLF line endings, latin-1 character encoding, 57.2 MB). It is not CSV. It is not a Python dict. When delivered as a ZIP archive (the standard NSE distribution format), it requires decompression before parsing. No concrete parser is registered in the current codebase; only the registry infrastructure exists.

Without a binding decision on what the registry accepts, a future implementor could introduce a pre-parsing layer in the registry (coupling it to ZIP/XML), write the parser to receive a parsed `dict` or `ElementTree` (coupling to a specific intermediate), or receive raw `bytes` and own all stages. Only one of these respects the registry's stated role as a format-agnostic dispatch table.

### Decision

Parser functions registered in `ParserRegistry` accept **raw `bytes`** — the verbatim binary content of the `.spn` file (or the content of the primary XML file after ZIP extraction at the caller's discretion). The registry's type annotation is `Callable[[bytes], SpanSnapshot]`.

**Responsibility allocation:**

| Stage | Owner |
|---|---|
| File location on disk | `SpanRepository` |
| ZIP decompression (if applicable) | Parser function |
| Character encoding detection/decode | Parser function |
| XML parsing | Parser function |
| Field extraction (priceScan, volScan, RA values) | Parser function |
| RA 16-scenario worst-case reduction | Parser function |
| `SpanSnapshot` construction | Parser function |

The registry is format-agnostic: it stores a version string → callable mapping and dispatches. It performs no format detection, no ZIP handling, no XML parsing, no dict construction. A bytes-in, `SpanSnapshot`-out contract is the minimum-assumption interface that keeps the registry reusable across future format changes.

### Alternatives Considered

- **Registry accepts a pre-parsed `dict`** — rejected: a dict is an intermediate representation whose schema is chosen by whoever builds the dict, not by the parser; coupling the registry to that schema forces all parser implementations to agree on a dict format that is version-specific and undocumented. The bytes contract avoids this layer.
- **Registry accepts a parsed `xml.etree.ElementTree.Element` (the root element)** — rejected: the registry would need to parse the XML, selecting an encoding and parser library before dispatch; this couples the registry to one XML parsing approach and breaks the format-agnostic invariant.
- **Registry handles ZIP extraction and passes decompressed bytes to the parser** — rejected for the same reason: adds responsibility to the registry, requires it to understand the ZIP-vs-raw-file distinction, and cannot be format-agnostic.

### Consequences

- `parse_span_csv` in `span_parser.py` must be renamed `parse_span_xml` (or `parse_nsccl_span_v4`) in MM9.5-S1 to reflect the real format.
- The function signature changes from `parse_span_csv(schema_version: str, raw_data: dict)` to `parse_span_xml(raw: bytes) -> SpanSnapshot`.
- The registry key used in `span_parser.py` ("v1") must be updated to "4.00" per ADR-010.
- All tests that register parsers using a `dict` call signature or the "v1" key must be updated in MM9.5-S1 alongside the production change.
- `SpanRepository` passes the raw file bytes to `ParserRegistry.parse(version, raw_bytes)` — no pre-parsing before dispatch.
- Future parser authors own the full format-specific stack: a `parse_span_v5_xml(raw: bytes)` function registered under "5.00" owns its own ZIP/XML handling independently.

*Ref: core/risk/span/span_parser.py; docs/reports/MM9_5_ARCHITECTURE_RECONCILIATION.md (D3, G-2, G-3); ADR-007.*

---

## ADR-010 — SPAN Version Key Policy: `<fileFormat>` Verbatim

**Status:** Accepted (2026-06-29) · MM9.5 Architecture Reconciliation.

### Context

`ParserRegistry` dispatches by `schema_version` string. The current implementation registers parsers under the key `"v1"` — an internal label with no relationship to any NSE-defined version identifier.

The real NSE SPAN file header is `<fileFormat val="4.00">`. NSE NSCCL is the authoritative source for format versioning; their numbering scheme (major.minor, "4.00") is the only version label that appears in the file itself and in NSE documentation. The "v1" internal key provides no traceability to the NSE format and offers no upgrade policy: if NSE releases format 4.01 or 5.00, there is no defined behavior.

Before any concrete parser is registered (none exists today — only the registry infrastructure), the version key convention must be locked so that the registry contract is coherent between the key chosen at registration time and the key derived from the file at parse time.

### Decision

**Registry keys match `<fileFormat val="...">` verbatim.** The version key for the current NSE SPAN format is `"4.00"`, not `"v1"`. At parse time, the pipeline reads the `<fileFormat>` attribute from the incoming file and passes it as the `schema_version` argument to `ParserRegistry.parse(schema_version, raw)`.

**Policy for format changes:**

| NSE format change | Action |
|---|---|
| Minor, backward-compatible (e.g., 4.01) | Alias: register the `"4.00"` parser under `"4.01"` as well. No new parser function. |
| Breaking minor change (new required elements / changed semantics) | New parser function registered under the new key (e.g., `"4.01"`). `"4.00"` parser remains for archive replay. |
| Major version (e.g., 5.00) | New parser function registered under `"5.00"`. Old parsers remain for archive replay. |
| Unknown version string | `ParserRegistry.parse` raises `UnsupportedSpanSchema`. Startup readiness converts this to **BLOCK**. |

Archive replay correctness is preserved: a historical `.spn` file from format "4.00" will always dispatch to the "4.00" parser even after newer parsers are registered, because the key comes verbatim from the file's own `<fileFormat>` attribute.

### Alternatives Considered

- **Internal versioning ("v1", "v2", …)** — rejected: no traceability from an internal key to the NSE format version that file belongs to; an operator cannot inspect a SPAN file and know which registry key to use without a separate mapping table; introduces a hidden translation layer with no authoritative source.
- **Integer major-only versioning (4, 5)** — rejected: discards the NSE minor version, which may carry breaking changes; the "4.00" → "4.01" alias rule above handles minor-compatible updates without losing the distinction between major and minor.
- **Semantic version parsing (extract major.minor, dispatch on major only)** — rejected: NSE's format versioning semantics are not published; assuming minor versions are always backward-compatible is an unverified claim; verbatim matching is the safest default and the alias rule handles the common case.

### Consequences

- The key `"v1"` in `span_parser.py` must be replaced with `"4.00"` in MM9.5-S1 alongside the ADR-009 parser rename.
- The pipeline (parser function or `SpanRepository.load`) must extract `<fileFormat val="...">` from the raw file before dispatching; the version key in the registry must equal the NSE `<fileFormat>` value.
- All tests that use the "v1" key must be updated in MM9.5-S1 (the version key is not a public contract today; no external callers exist).
- `UnsupportedSpanSchema` is the correct exception for unknown formats; the startup readiness check must treat it as BLOCK — not WARN — because trading on margin computed from an unrecognised format is undefined.
- The alias policy means registering `"4.01"` pointing to the same `parse_span_xml` function requires one line; a future `parse_span_xml_v5` is registered under `"5.00"` independently.

*Ref: core/risk/span/span_parser.py; docs/reports/MM9_5_ARCHITECTURE_RECONCILIATION.md (D5, D6, G-4, G-5); ADR-007, ADR-009.*

---

## ADR-011 — NseMarginEngine Is The MarginCalculator For LIVE F&O

**Date:** 2026-06-30

**Status:** ACCEPTED

### Context

MM10.3 introduced `NseMarginEngine` as a composition layer wrapping `SpanMarginCalculator` with calendar spread credits. MM10.4 added ELM. This changed the production margin architecture from a single calculator to a layered engine.

Without an explicit ADR, two interpretations are possible:
- `SpanMarginCalculator` is the production `MarginCalculator` and `NseMarginEngine` is an optional enhancement
- `NseMarginEngine` is the production `MarginCalculator` and `SpanMarginCalculator` is its internal SPAN component

### Decision

`NseMarginEngine` is the production `MarginCalculator` for LIVE F&O from MM10.3 onwards.

`SpanMarginCalculator` is its internal SPAN component — not the production calculator once spread credits and ELM are live.

`SpanMarginCalculator` remains independently testable and is a valid conservative fallback (scan-only, no credits, no ELM).

`MarginTracker` remains the flat-rate fallback for non-F&O and non-SPAN portfolios.

### Consequences

- `ExecutionHandler` receives `NseMarginEngine` (not `SpanMarginCalculator`) when `span_snapshot` is provided.
- All future margin components (exposure margin, delivery margin) are added to `NseMarginEngine`, not to `SpanMarginCalculator`.
- `SpanMarginCalculator` is feature-frozen after MM10.2 — no new methods, no new data sources.
- ELM data source (`elm_rates.py`, NSE Clearing circulars) is independent of the SPAN XML data source — these sources never merge.

*Ref: core/risk/nse_margin_engine.py; core/risk/elm_rates.py; core/execution/handler.py; docs/reports/MM10_ARCHITECTURE_REVISION.md; docs/reports/MM10_3_IMPLEMENTATION_SPECIFICATION.md; docs/reports/MM10_4_IMPLEMENTATION_SPECIFICATION.md.*

**2026-07-01 update — MM10.5 Spec Section 8, Risk 1 CLOSED:**

Primary-source research (`docs/reports/MM10_5_MARGIN_COMPONENT_VERIFICATION.md`) resolves the
Risk 1 discriminator (`docs/reports/MM10_5_IMPLEMENTATION_SPECIFICATION.md` §8;
`docs/reports/MM10_5_ARCHITECTURE_REASSESSMENT.md`) as **Hypothesis B (H-same)**: "Exposure
Margin" is not a component distinct from ELM for NSE Equity Derivatives — it is the retired
name for it. SEBI's own risk-management history page states ELM "replaces the terms 'exposure
margin' and 'second line of defence'"; NSE's current MG-12/MG-13 clearing report schema
itemizes only SPAN Margin, Extreme Loss Margin, Delivery Margin, and Margin on Consolidated
Crystallized Obligation — no separate Exposure Margin field exists in any current F&O clearing
report.

**Correction to Consequences above:** the bullet "All future margin components (exposure
margin, delivery margin) are added to `NseMarginEngine`" is stale. There is no separate
exposure margin component to add — `elm_rates.py` / `_elm_margin` already is it. Delivery
Margin remains the one genuinely outstanding future component for `NseMarginEngine`.

**Binding consequence:** do not write `exposure_margin_rates.py` or an `_em_margin` method on
`NseMarginEngine`. MM10.4's `_elm_margin` is the complete implementation of this regulatory
charge; adding a second component would double-count it. MM10.5 may proceed on this basis.

**Successor:** ADR-012 formally retires MM10.5 on this basis.

---

## ADR-012 — MM10.5 Retired: Exposure Margin Is ELM Under Legacy Naming; MM10 Complete

**Date:** 2026-07-01

**Status:** ACCEPTED

### Context

MM10.5 was scoped (`docs/reports/MM10_5_IMPLEMENTATION_SPECIFICATION.md`) to add a third,
additive margin component — `exposure_margin_rates.py` + an `_em_margin` method on
`NseMarginEngine` — on top of SPAN and ELM (MM10.4). The spec's own Section 8, Risk 1, flagged
this as unverified: is "Exposure Margin" a genuine third NSCCL component, or a legacy name for
ELM under a different label? Upstox `/charges/margin` API evidence
(`docs/reports/MM10_5_ARCHITECTURE_REASSESSMENT.md`) sharpened the question (all sampled
responses reconcile exactly to `span_margin + exposure_margin` with zero residual; Upstox's own
field docs tie `exposure_margin` to "ELM percentage values") but a pre-trade blocked-margin
endpoint cannot rule out a separate end-of-day ELM charge, so it did not close Risk 1 on its own.

Primary-source research (`docs/reports/MM10_5_MARGIN_COMPONENT_VERIFICATION.md`) resolved it:
SEBI's risk-management history page states ELM "replaces the terms 'exposure margin' and
'second line of defence' that have been used hitherto"; NSE's current MG-12 (Detail Margin File)
and MG-13 (Client Level Margin File) clearing report schemas itemize SPAN Margin, Extreme Loss
Margin, Delivery Margin, and Margin on Consolidated Crystallized Obligation only — no separate
Exposure Margin field exists in any current F&O clearing report. This is Hypothesis B (H-same)
per the Reassessment doc's discriminator (§3): two non-SPAN percentage line items were found
(ELM + none), not three, so H-same is confirmed and H-separate is rejected.

Two independent public NSE artifacts were checked this session as candidate corroborating
sources and both came back uninformative, not contradictory: (1) today's live SPAN Risk
Parameter file (`reference/span/.../nsccl.20260701.i01.spn`, PC-SPAN v4.00) contains zero
occurrences of `exposure`/`extreme`/`elm`/`loss`/`buffer`/`defence` — expected and orthogonal,
since a PC-SPAN file only ever encodes the SPAN-component risk arrays and would omit these terms
under either hypothesis; (2) a live-browser open of the NSE page describing the MG-12/MG-13
field list (`nseindia.com/static/products-services/equity-derivatives-data-reports-margin`,
`nseindia.com/all-reports-derivatives`) was attempted — the browser extension is connected, but
`nseindia.com` is blocked by the extension's own safety restrictions for both target URLs, so
the check could not be completed and is not completable through this channel. The Technical
Lead's requested final sanity check therefore remains formally unperformed. Retirement proceeds
without it, on the user's explicit instruction, on the strength of the primary-source research
already gathered in `MM10_5_MARGIN_COMPONENT_VERIFICATION.md` (SEBI risk-management history page,
NSE Clearing FAQ PDF, and the MG-12/13/14/15 report-schema field-list text, all independently
corroborating).

### Decision

**MM10.5 is retired**, not deferred and not superseded by a renamed future milestone. "Exposure
Margin," as used in broker docs/APIs (Upstox `exposure_margin`) and pre-2009 SEBI circulars, is
the legacy name for Extreme Loss Margin (ELM) for NSE Equity Derivatives — not a distinct,
additive regulatory charge. `NseMarginEngine` will not gain an `exposure_margin_rates.py` module
or an `_em_margin` method; MM10.4's `_elm_margin` already is the complete implementation.

**MM10 (Complete SPAN portfolio margin) is complete** for its SPAN scan-risk (MM9.5) +
contract-level RA routing (MM10.2) + calendar spread credits (MM10.3) + ELM/exposure-margin
resolution (MM10.4–MM10.5) scope.

**Delivery Margin is descoped from MM10.** It was listed in `docs/PROJECT_STATE.md` as remaining
MM10 scope but has no spec, no implementation, and no successor milestone number. Per explicit
user instruction, it is not folded into a renamed future milestone at this time — it is simply
removed from MM10's scope, unimplemented, and not to be touched without a fresh scoping decision.

### Consequences

- ADR-011 stands; its 2026-07-01 update already anticipated this closure. This ADR is the
  formal retirement act that update deferred.
- `docs/PROJECT_STATE.md` Planned item 5 moves from "MM10.1–MM10.4 COMPLETE" to "MM10.1–MM10.5
  COMPLETE," with Delivery Margin recorded as descoped, not remaining, scope.
- `docs/PROJECT_STATE.md`'s Blocked-section MM10.5 entry (2026-07-01) is closed and moved to
  Completed.
- No code changes result from this ADR — it is a scope/documentation closure only.
- The Margin Authority Model review's separate recommendation (a new ADR distinguishing
  `NseMarginEngine` sizing authority from broker order-acceptance authority,
  `docs/reports/MARGIN_AUTHORITY_ARCHITECTURE_REVIEW.md` §3 Q6) is unaffected by this ADR and
  remains open, not yet written.

*Ref: docs/reports/MM10_5_IMPLEMENTATION_SPECIFICATION.md §8 Risk 1;
docs/reports/MM10_5_ARCHITECTURE_REASSESSMENT.md;
docs/reports/MM10_5_MARGIN_COMPONENT_VERIFICATION.md; ADR-011.*

---

## ADR-013 — Two Margin Authorities: `NseMarginEngine` Sizes, Broker RMS Accepts

**Date:** 2026-07-01

**Status:** ACCEPTED

### Context

Upstox `/charges/margin` order-margin API evidence prompted a platform-level question the MM10.5
Risk 1 discriminator never addressed: now that a broker margin API is visibly available, should
the broker replace or supplement `NseMarginEngine` as the margin authority for LIVE trading?
`docs/reports/MARGIN_AUTHORITY_ARCHITECTURE_REVIEW.md` answered this in full; ADR-012's
Consequences left the resulting new-ADR recommendation (its §3 Q6) explicitly open and
"not yet written." This ADR is that formal decision.

Without an explicit split, "the broker becomes authoritative for LIVE" is ambiguous between two
readings: (a) the broker becomes authoritative for order acceptance only, or (b) the broker
replaces `NseMarginEngine` as the sizing calculator in LIVE mode. Reading (b) would collapse two
platform principles that already forbid it independent of this evidence: **Runner Is Neutral**
(CLAUDE.md Principle 4 — the LoopDriver treats live and backtest data identically; a backtest has
no broker session, so sizing cannot depend on a broker call without live and backtest running on
structurally different margin logic) and **Audit-First** (Principle 5 — every trade must be
explainable by exact analytical facts; a broker's returned total is an opaque number, while
`NseMarginEngine`'s `span - credit + elm` is a decomposable, auditable formula).

### Decision

The platform recognizes **two distinct margin authorities**, never merged:

| Authority | Owns | Component |
|---|---|---|
| **Computation / sizing authority** | "What margin will this position consume, as a decomposable formula?" | `NseMarginEngine` — used for research, backtesting, paper trading, and LIVE pre-trade sizing/gating |
| **Order-acceptance authority** | "Will the exchange/broker actually accept this order at this margin?" | The broker RMS, at the gateway |

`NseMarginEngine` remains the sole sizing/computation authority in every mode, including LIVE,
unchanged from ADR-011. The broker's authority is scoped **only** to accepting or rejecting the
order it receives — it is never consulted for sizing and never overrides `NseMarginEngine`'s
computed margin.

**Revised product objective.** `NseMarginEngine`'s purpose is a **deterministic implementation of
publicly available NSE Clearing margin rules** — for research, backtesting, paper trading,
deterministic sizing, auditability, and broker-independent execution. It is **not**, and was
never achievably, an exact clone of any broker's proprietary RMS: retail has no access to broker
RMS internals or a historical broker-side SPAN archive, so byte-for-byte parity with a broker's
number was never a claim the local engine could honestly make. Restating the objective this way
makes the existing design *more* correct relative to its actual, achievable goal — it requires no
redesign of any frozen component.

**Broker margin reconciliation is deferred.** Obtaining a broker margin estimate, comparing it to
`NseMarginEngine`'s output, logging differences, and surfacing them for an operational decision
before order submission is a **LIVE execution capability**, not a margin calculation capability.
It is explicitly deferred until LIVE trading is an active milestone: there is currently no
production strategy, no funded LIVE account, and no operational need for it. It must never
influence backtesting, research, or paper trading. No implementation work — including a
configurable validation-policy enum or a multi-broker provider abstraction — is undertaken now,
ahead of a concrete consumer.

### Alternatives Considered

- **Broker `/charges/margin` replaces `NseMarginEngine` for LIVE sizing** — rejected: violates
  Runner Is Neutral and Audit-First (Context above); also reintroduces the exact ambiguity
  ADR-011 already closed ("which component is the production calculator").
- **A `MarginProvider` abstraction anticipating future brokers (Zerodha, Dhan, ...)** — rejected
  as premature: exactly one broker is integrated today; a provider hierarchy would guess its
  interface shape from zero second implementations, and would create a second, differently-named
  seam alongside the existing `MarginCalculator` Protocol (ADR-007) for no present consumer —
  inviting the same kind of ambiguity ADR-011 was written to prevent.
- **A configurable OFF / WARN / STRICT margin-validation policy, built now** — rejected as
  premature: there is no broker margin fetch, no comparison logic, and no reconciliation
  scaffolding in the repository to configure. `OFF` is also not a real per-environment policy
  choice — it is the only physically possible state in backtest/research (no broker session
  exists to query), so it should be structurally forced by source absence, not selectable,
  whenever this is eventually built (mirroring how `require_reconciliation_on_start` already
  branches by source presence rather than by mode).
- **Merge the broker's total into `NseMarginEngine.get_used_margin`** — rejected: destroys
  determinism (ADR-003) and auditability (ADR-005), and reintroduces live/backtest divergence.

### Consequences

- No change to `ExecutionHandler` construction or `MarginCalculator` injection. ADR-007 and
  ADR-011 stand unmodified.
- Closes the open item left by ADR-012's Consequences (Margin Authority Model review, §3 Q6).
- A future LIVE-only margin reconciliation layer, if and when built, is strictly additive: it
  consumes `NseMarginEngine` output and a broker margin fetch as two independent inputs, never
  replaces either with the other, and a validation-policy config belongs to that future milestone
  — not to this ADR.
- The revised product objective ("deterministic implementation of public NSE rules," not "exact
  broker clone") is the durable framing for `NseMarginEngine` going forward and should inform any
  future margin-related documentation or design discussion.
- Margin subsystem (`core/risk/span/`, `core/risk/elm_rates.py`, `core/risk/nse_margin_engine.py`)
  is feature-frozen; this ADR adds no new margin computation and requests none.

*Ref: docs/reports/MARGIN_AUTHORITY_ARCHITECTURE_REVIEW.md §§1-4 (Q1/Q3, Q4, Q5, Q6);
ADR-003, ADR-005, ADR-007, ADR-011, ADR-012; CLAUDE.md Architecture Principles 3, 4, 5.*

---

## ADR-014 — MM11 Sequencing: Platform Consolidation Precedes External Strategy Integration

**Date:** 2026-07-01

**Status:** ACCEPTED

### Context

`docs/reports/MM11_ARCHITECTURE_REVIEW_AND_PROPOSAL.md` (Part 2) initially recommended an
External Strategy Integration Contract (a `SignalSource` conformance harness, a non-alpha
reference implementation, and a promotion-path document) as MM11, with Platform Consolidation
(Planned items #2/#3/#7 — strategy-analytics residue, dead `core/data/*` twins, unified
market-data layer) named as a legitimate but secondary alternative. The Technical Lead challenged
this recommendation directly and asked for an objective reassessment, not a defense of the
original call, specifically probing whether publishing an integration contract before
consolidating and freezing the infrastructure was the correct sequence.

Two facts were checked before re-deciding (`MM11_ARCHITECTURE_REVIEW_AND_PROPOSAL.md` §3.1):
`core/runtime/signal_source.py` (the `SignalSource` ABC) has exactly one commit in its history —
it has never been modified since introduction — and the three consolidation candidates share no
file surface with the integration-contract deliverables (`core/runtime/driver.py`,
`scripts/fno_runner.py`, `core/runtime/signal_source.py`).

### Decision

**MM11 is Platform Consolidation / Infrastructure Freeze.** External Strategy Integration
(the Part 2 proposal, unchanged in content) is resequenced to **MM12**.

This is a **prioritization decision, not a dependency decision** — the reassessment explicitly
rejects the premise that consolidation is a technical prerequisite for the integration contract:
the contract has never changed and the planned consolidation work does not touch it. The
resequencing is chosen because:

1. Consolidation's consumer (the codebase and its own documentation) is real and present today;
   the integration contract's consumer (a future external strategy) is not.
2. The consolidation items have sat in `docs/PROJECT_STATE.md` "Planned" since MM7–MM8, repeatedly
   deprioritized in favor of forward-looking milestones — a pattern this decision declines to
   repeat a third time.
3. Publishing an external-facing contract on top of stale top-level docs is a genuine problem:
   `README.md` currently describes this repository as a "Market Data Repository," not the trading
   platform CLAUDE.md describes, and `PROJECT_REVIEW_SUMMARY.md` (dated 2026-03-04) describes a
   prior, different multi-strategy monolith. A documentation-audit pass should precede anything
   external-facing.
4. The integration contract loses nothing by waiting one milestone: the `SignalSource` ABC stays
   frozen regardless, and PAPER validation of a reference implementation is exactly as achievable
   at MM12 as it would have been at MM11.

**Named cost, accepted knowingly:** this sequencing defers the first end-to-end proof that the
MM7–MM10 execution stack actually drives a `SignalSource` through the real composition root
(`fno_runner.py`) in a running process, rather than only through test doubles. This is the one
genuinely strong argument for doing External Strategy Integration first, and it is not addressed
by the prioritization reasoning above — it is accepted as a known, bounded tradeoff (the stack is
already heavily unit/integration tested; a thin non-alpha reference source in PAPER is marginal
incremental de-risking, not a large unknown).

### Alternatives Considered

- **External Strategy Integration Contract as MM11** (the original Part 2 recommendation) —
  not rejected on its merits, only resequenced: it remains a fully valid MM12. Rejected as MM11
  specifically because its consumer does not exist yet, while a same-cost, present-consumer
  alternative (consolidation) was available and had been repeatedly deferred.
- **"Consolidate first to avoid future breaking changes to the integration contract"** — rejected
  as the stated justification: this ADR's own verification (`git log` on `signal_source.py`; file
  surface disjointness) disproves it. Anyone re-litigating this decision on churn-avoidance grounds
  should be pointed to §3.1 of the reassessment document, not re-argued with from scratch.
- **Do both in parallel** — not adopted as the formal sequencing, though nothing in this ADR
  forbids incidental parallel progress; the decision names MM11/MM12 as the priority order for
  planning and reporting purposes, not a hard technical gate preventing overlap.

### Consequences

- `docs/PROJECT_STATE.md` Planned items #2, #3, #7 are promoted to the active MM11 scope; the
  stale top-level docs rewrite (`README.md`, `PROJECT_REVIEW_SUMMARY.md`) is added to MM11 scope
  as the external-facing-docs sub-item identified in this reassessment.
  `MM11_ARCHITECTURE_REVIEW_AND_PROPOSAL.md` Part 2's content becomes the MM12 proposal, unchanged.
- No code, ADR, or contract change results from this ADR itself — it is a sequencing/roadmap
  decision. `SignalSource`, `LoopDriver`, `ExecutionHandler`, and the margin subsystem are
  unaffected and remain as specified in ADR-002, ADR-006, ADR-MM7E-1, ADR-011/012/013.
- A future MM12 kickoff should re-verify (not assume) that `signal_source.py` is still unmodified
  before treating this ADR's stability claim as still current.

*Ref: docs/reports/MM11_ARCHITECTURE_REVIEW_AND_PROPOSAL.md Part 3 (§3.1–§3.4);
ADR-002, ADR-006, ADR-MM7E-1, ADR-013; docs/PROJECT_STATE.md Planned #2, #3, #7.*

---

## ADR-015 — CaptureEngine / TLP Pipeline: REFACTOR Downgraded to REMOVE

**Date:** 2026-07-02

**Status:** ACCEPTED

### Context

ADR-014 scoped `docs/PROJECT_STATE.md` Planned #2 as "decouple `CaptureEngine`/`metrics_service`
inputs from strategy-analytics tables" — the verb "decouple" implies a **refactor** in which the
component survives, reshaped. When the MM11 implementation specification
(`MM11_IMPLEMENTATION_SPECIFICATION.md` §0b) verified this scope against the live tree rather than
inheriting the 2026-06-04 inventory's assumption, the "component stays" premise did not hold:

- `scripts/fno_runner.py` — the **only** live composition root — contains zero references to
  `CaptureEngine`, `capture_engine`, or `StructuralMetricsService`. The
  `ExecutionHandler.capture_engine` constructor parameter is never supplied a real instance, so the
  guard `if self.capture_engine and signal.signal_type != SignalType.EXIT` is **always false in
  production** — dead code behind an unreachable branch, not optional infrastructure.
- `TLPLogger` (`core/analytics/capture.py`) is never instantiated anywhere outside its own
  definition (`init_tlp_logger`/`get_tlp_logger`/`TLPLogger(` — zero call sites).
- The two tables `CaptureEngine.capture_context` reads (`regime_insights`,
  `daily_structural_metrics`) have zero live writers; both reads fall through `except: pass` to
  hardcoded defaults on every real invocation, and `_calculate_breadth`/`_get_index_trend` are
  literal stub returns (`0.5` / `"NEUTRAL"`) that were never implemented.

Net effect: even if `capture_engine` *were* wired at the composition root, `capture_context()`
would return a `TradeStructuralContext` assembled entirely from stubs and fallbacks. The component
has never produced a real structural snapshot in this repository's lifetime — it is fully dead
code with no live path to becoming otherwise, not "strategy-coupled infrastructure worth
decoupling."

### Decision

**MM11.1 removes `CaptureEngine`, `StructuralMetricsService`, `TLPLogger`, and the `capture_engine`
seam from `ExecutionHandler` outright, rather than decoupling them.** This is a deliberate,
signed-off deviation from ADR-014's literal "decouple" wording for Planned #2, recorded here per
`MM11_IMPLEMENTATION_SPECIFICATION.md` §6 (deviation #1) and §2 (MM11.1 acceptance criterion 5,
which conditions MM11.1 completion on this ADR existing).

Decoupling code that is already unreachable in production adds no value over removing it, and
leaving a "decoupled" but unwired component in place would itself violate CLAUDE.md's Development
Convention "No backwards-compatibility shims — delete unused code completely." REMOVE is the
disposition consistent with both the verified evidence and the platform's own conventions.

### Alternatives Considered

- **REFACTOR as literally scoped by ADR-014 (decouple, keep the component)** — rejected: it
  preserves provably-dead code, produces no runtime behavior it did not already have (none), and
  contradicts the "delete unused code completely" convention. Its only merit would be honoring the
  ADR-014 wording verbatim, which §6 explicitly surfaces and overrides on evidence.
- **Defer to a later milestone** — rejected: the code is unambiguously dead now; deferral would
  carry a known-dead component across the Platform v1.0 line, which the v1.0 definition
  ("free of verified-dead code") forbids.

### Consequences

- MM11.1 deleted `core/analytics/capture.py` and `core/analytics/metrics_service.py`, removed the
  `capture_engine` constructor parameter/assignment/branch and the import from
  `core/execution/handler.py`, and removed the unused analytics-persistence helpers from
  `core/database/legacy_adapter.py`, `writers.py`, and `__init__.py`. Each removal is filed as a
  Removal Ledger entry with the §1.5 four-part proof; behavior preservation is demonstrated by the
  before/after full-suite diff (1055 passed, 4 skipped — identical).
- The behavior-neutrality claim was **demonstrated, not asserted** (removing an always-false branch)
  — this was the milestone's hardest §1.5 proof-#2 case and is discharged in the ledger.
- ADR-014's sequencing decision is unaffected; this ADR corrects only *what specific work item*
  Planned #2 resolves to (REMOVE, not REFACTOR), inside the boundary ADR-014 already drew.
- The `docs/PROJECT_STATE.md` "Deferred — `CaptureEngine` full structural capture" item is now
  obsolete (the component no longer exists) and is retired in the same MM11.7 close-out.

*Ref: docs/reports/MM11_IMPLEMENTATION_SPECIFICATION.md §0b, §2 (MM11.1), §6 (deviation #1);
docs/reports/MM11_REMOVAL_LEDGER.md (MM11.1 entries); ADR-002, ADR-014;
CLAUDE.md (Development Conventions).*

---

## ADR-016 — `SignalSource` Is The Strategy Interface; External Packaging Via Factory

**Date:** 2026-07-02

**Status:** ACCEPTED

### Context

MM12 (External Strategy Integration Contract, ADR-014) must name the interface an external
strategy implements. The candidate answers ranged from "reuse the existing `SignalSource` ABC
as-is" to "introduce a richer `Strategy` ABC with lifecycle/feedback hooks (`on_fill`,
`on_reject`, `on_pause`)". Relevant verified facts: `core/runtime/signal_source.py` has exactly
one commit (`c1d833a`, re-verified 2026-07-02 per ADR-014's standing instruction) and survived
MM7–MM11 unmodified while the entire execution stack was built against it; the driver's pull
model is the deterministic backbone (ADR-003/ADR-006); Platform v1.0 is certified and its
components frozen.

### Decision

**The `SignalSource` ABC is the complete strategy interface.** No new ABC, no additional hooks,
no feedback channels from platform to strategy. An external strategy is a separate
repository/package that imports only the sanctioned surface (`core.runtime.signal_source`,
`core.events`) and exports a single factory:

```
build_signal_source(config: dict) -> SignalSource
```

The composition root (`scripts/fno_runner.py`) injects — never constructs — the source
(ADR-MM7E-1), wrapping it in the platform-owned `GuardedSignalSource` (ADR-018) before handing it
to the driver. One strategy process = one strategy; multi-strategy composition is deferred until a
second real strategy exists.

### Alternatives Considered

- **Richer `Strategy` ABC with `on_fill`/`on_reject` callbacks** — rejected: every feedback
  channel makes strategy output a function of execution outcomes, which differ PAPER vs LIVE by
  construction, destroying replay-equivalence (the property that makes external backtests valid
  promotion evidence) and requiring frozen-driver changes.
- **In-repo strategy directory (`core/strategies/`)** — rejected: violates ADR-002 / Constitution
  §5 (platform must not grow strategy logic inward); the strategy layer is intentionally
  greenfield and external.
- **Plugin registry / multi-strategy loader** — rejected as premature abstraction with no second
  consumer (the same reasoning that rejected `MarginProvider`, ADR-013).

### Consequences

- Strategies cannot observe their own fills; the shadow-state model (ADR-017) is the mandated
  state discipline.
- The conformance suite (MM12.2, `core/runtime/conformance.py`) certifies implementations of this
  interface; its import-surface check enforces the sanctioned-surface rule mechanically.
- Contract evolution is additive-only within a major version, anchored on the frozen ABC and
  `SignalEvent` dataclass; the seam's single-commit status is re-verified at each dependent
  milestone (ADR-014 practice, adopted as standing).

*Ref: docs/reports/MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §3, §13; ADR-002, ADR-003,
ADR-006, ADR-013, ADR-014, ADR-MM7E-1; core/runtime/signal_source.py (c1d833a).*

---

## ADR-017 — Strategy State Is Shadow State; Divergence Is Fail-Safe

**Date:** 2026-07-02

**Status:** ACCEPTED

### Context

A stateful strategy needs position awareness (am I long?) to emit exits, but the seam forbids any
ledger/broker/handler handle (DRIVER_SPECIFICATION §5.4) and the platform gives no fill/reject
feedback (ADR-016). Six handler gates (kill switch, daily limit, drawdown, stacking, risk, Greek,
margin/priceability) can silently drop an entry signal (`process_signal` returns `None`), so any
strategy-side belief about its positions can be wrong.

### Decision

**Strategy state is shadow state: `state = f(bar_history, own_signal_history, config)`.** The
strategy tracks the positions it *believes* it opened from its own emitted signals and never reads
platform truth. This is accepted because divergence is provably **one-directional and fail-safe**:
the strategy can only believe in a position that does not exist (rejected entry), never the
reverse (the platform opens no position unsignalled). Every consequence is absorbed by existing
frozen guards: EXIT on FLAT is a no-op (`handler.py:699-701`); duplicate entries hit the stacking
guard (`handler.py:633-636`); replayed ids hit the idempotency lock (`handler.py:550-554`). The
strategy may waste signals; it cannot bypass a guard or double a position.

**Named extension point, deliberately not built:** a read-only position projection passed via the
existing `on_start(context=...)` parameter — the one injection point the frozen contract already
permits. It is deferred until the first real strategy demonstrates a concrete need (e.g.,
shadow-state recovery after process restart with open positions). Until then, building it would be
an abstraction ahead of need (CLAUDE.md convention).

### Alternatives Considered

- **Fill/reject feedback hooks** — rejected (ADR-016; determinism).
- **Read-only ledger projection now** — rejected: no consumer exists; the extension point is
  reserved and requires no ABC change when needed.
- **Platform-managed strategy state** — rejected: moves strategy state across the boundary,
  inverting ADR-002's dependency direction.

### Consequences

- The conformance suite need not (and cannot) verify shadow-state *correctness* — only that the
  source holds no forbidden platform handles; shadow-state divergence review is a named
  PAPER-validation gate item in the promotion path (MM12.5).
- MM13's PAPER validation must include a journal audit comparing emitted intent vs. executed
  reality to quantify real-world divergence rates.

*Ref: docs/reports/MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §3.3–§3.4, §16.2; ADR-016;
DRIVER_SPECIFICATION.md §5.4; core/execution/handler.py:550-554, 633-636, 699-701.*

---

## ADR-018 — Boundary Validation Is Reject-And-Journal, Enforced By A Platform-Owned Guard

**Date:** 2026-07-02

**Status:** ACCEPTED

### Context

`ExecutionHandler.process_signal` tolerates missing mandatory risk metadata
(`sl_distance`/`risk_r`) by logging a WARNING and default-filling conservative values
(`handler.py:575-581`) — a legacy tolerance from when every caller was in-repo. For an external
contract this is the wrong posture: a certified strategy missing its risk definition has a defect,
and trading it on synthetic values makes the trade unexplainable by the strategy's facts
(Audit-First). The handler is frozen (v1.0), so hardening cannot go there.

### Decision

**A platform-owned `GuardedSignalSource` wrapper — itself a conforming `SignalSource` — is
composed around every external source at the composition root.** Per bar it: (1) short-circuits
`[]` if quarantined (ADR-019); (2) invokes the inner source inside a fault boundary; (3) validates
the returned value's shape and each signal against the contract (mandatory entry metadata,
bar-equal timestamp, universe membership); (4) **drops violators and journals
`SIGNAL_CONTRACT_REJECTED`** — never default-fills — passing only contract-clean signals to the
driver. Validation is per-signal: one bad signal does not suppress clean siblings (mirrors the
driver's §8.4 per-signal isolation). The handler's legacy default path remains untouched but
becomes unreachable for guarded external sources.

### Alternatives Considered

- **Harden `process_signal` itself** — rejected: modifies a frozen v1.0 component, and boundary
  concerns belong at the boundary layer, not inside execution.
- **Default-fill at the guard (preserve legacy semantics)** — rejected: violates Audit-First; a
  synthetic `sl_distance` is not the strategy's fact.
- **Validate only in the conformance suite (offline)** — rejected: certification proves the
  strategy *can* behave; the guard proves it *is* behaving, on every bar, in production.

### Consequences

- New journal `EventType` members: `SIGNAL_CONTRACT_REJECTED` (WARNING), plus ADR-019's
  `STRATEGY_ERROR`/`STRATEGY_QUARANTINED`; matching `RuntimeMetric` counters keep the
  "observable without broker login" surface complete (Constitution §6). Additive, non-breaking.
- Zero diffs in `core/runtime/driver.py` and `core/execution/handler.py` — the MM12.3 slice's
  acceptance criterion.
- The guard must itself pass the conformance suite (it is a `SignalSource`).

*Ref: docs/reports/MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §4.3, §7.3, §8; ADR-016, ADR-019;
core/execution/handler.py:556-581; PLATFORM_CONSTITUTION.md §6.*

---

## ADR-019 — Strategy Fault Policy: Quarantine-And-Continue

**Date:** 2026-07-02

**Status:** ACCEPTED

### Context

Today an uncaught exception in `SignalSource.on_bar` propagates out of `LoopDriver._tick()` and
terminates the run through the `finally` shutdown — a strategy bug stops the whole process. Live,
that is the worst failure mode: the process dies with positions open, taking telemetry, watchdog,
heartbeat, and the operator's observability down exactly when they are most needed (Constitution
§6: failures must be observable without broker login; silent failure is unacceptable).

### Decision

**On the first uncaught `on_bar` fault (or malformed return value), the `GuardedSignalSource`
quarantines the strategy and the loop continues.** Concretely: journal `STRATEGY_ERROR` (durable,
traceback digest, `strategy_id`) → `alerter.critical(...)` → latch QUARANTINED and journal
`STRATEGY_QUARANTINED` (edge-triggered, once) → return `[]` for this and every subsequent bar; the
inner source is never invoked again. Loop, watchdog, telemetry, heartbeat, and journal all
survive; the account freezes (no signals to route) and the operator intervenes with full
observability — the platform's existing *kill-switched-but-running* idiom applied to the strategy
seam. **No automatic retry** (a deterministic strategy that threw on bar N throws on bar N again;
success on retry would prove nondeterminism). **No auto-flatten** (closing positions is a trading
decision; taking it inside an error handler would put alpha-adjacent authority in the platform).
`on_start` faults are a startup refusal; `on_stop` faults are logged and swallowed so shutdown
completes. Root-level wiring of quarantine to `activate_kill_switch` is an optional belt-and-braces
MM12.3 implementation choice, not required — `[]`-forever already stops all strategy-driven trading.

**Non-blocking note (Technical Lead, 2026-07-02, recorded at MM12.1 approval):** the quarantine
mechanism deliberately combines **validation** (per-signal contract enforcement, ADR-018) and
**operational policy** (fault response, this ADR) in one component, by design. With exactly one
fault policy in existence, extracting a separate policy object would be speculative abstraction.
Extraction is deferred until there is evidence of a **second policy** (e.g., a PAPER-only
"log-and-keep-invoking" diagnostic mode, or per-strategy policy selection under multi-strategy
composition).

### Alternatives Considered

- **Fail-fast process stop (status quo)** — rejected: destroys observability with positions open;
  contradicts Constitution §6.
- **Retry / N-strike escalation** — rejected: incompatible with the determinism contract
  (MM12.1 architecture §6); adds policy surface with no evidence it is needed.
- **Auto-flatten open positions on quarantine** — rejected: a trading decision inside an error
  handler; the alert-and-operator loop is the correct authority. The unmanaged-positions residual
  equals the existing kill-switch posture (`handler.py:606` blocks everything including EXITs and
  does not auto-flatten), so no new risk class is introduced.

### Consequences

- Strategy program defects (exceptions, malformed returns) and strategy data defects (individual
  contract-violating signals, ADR-018) are treated at different severities: quarantine vs.
  per-signal drop. Escalating repeated data defects to quarantine is an open question deferred to
  MM13 PAPER evidence.
- MM12.3's fault-injection tests must exercise validation and quarantine as one surface (a
  contract-violating signal and an `on_bar` raise in the same bar), since they are one component
  by decision.
- Operator recovery from quarantine is process restart after a fix — deliberately not automated.

*Ref: docs/reports/MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §8, §12, §16.3–§16.4; ADR-018;
PLATFORM_CONSTITUTION.md §6; DRIVER_SPECIFICATION.md §3.2 (kill-switched-but-running), §8.4.*

---

## ADR-020 — Reference Strategy Is A Permanently PAPER-Confined, Non-Alpha Canary; Guard Behavior Is Proven Live Via Throwaway Fixtures

**Status:** Accepted (2026-07-02)

### Context

MM12.4 requires the first concrete `SignalSource` implementation to validate the full platform pipeline end-to-end. This reference strategy must never be mistaken for a real trading strategy, must never be promoted to LIVE, and must prove the platform's guard infrastructure (ADR-018/ADR-019) works through the real composition root.

### Decision

1. **Reference strategy is permanently PAPER-confined and non-alpha.** The chosen design is `reference_strategies/heartbeat/` — a fixed-cadence, single-equity-symbol heartbeat (`HeartbeatSignalSource`) that trades on a deterministic bar-count schedule with no market awareness. It is permanently confined to `ExecutionMode.PAPER` and must never be promoted through the CONFORMANT → PAPER-VALIDATED → LIVE-APPROVED ladder (MM12.1 §14.1). This is enforced by convention (no code ever constructs it with `execution_mode=ExecutionMode.LIVE`), not by a new runtime policy object.

2. **Alternative designs were explicitly rejected.** Inert source, queue-backed discretionary source, indicator-based strategy, and seeded-random signal generator were each evaluated and rejected (MM12.4 §2.1).

3. **Guard behavior is proven live via separate throwaway fixtures.** `reference_strategies/fault_fixtures/` contains `AlwaysRaisesSource` (proves quarantine-and-continue) and `BadMetadataSource` (proves reject-and-journal). These are separate from the heartbeat strategy so the two proofs remain visibly distinct.

4. **`fno_runner.build_runner` unconditionally wraps every injected `source` in `GuardedSignalSource`.** This is execution of ADR-018, explicitly deferred by MM12.3 to this milestone — not a new decision.

5. **ADR-002's checkable invariant is extended** to forbid any `core/` module from importing `reference_strategies` (mirroring the existing `core.strategies|runner|backtest|state|models|ftmo` carve-out).

### Alternatives Considered

- **Trading an F&O instrument to exercise SPAN/NseMarginEngine** — rejected: pulls in instrument-master/contract-selection complexity with no incremental proof value for this milestone's primary goal (proving the external-strategy hosting pipeline).
- **Wrapping the guard only for a strategy-specific code path** — rejected: contradicts ADR-018's "every external source" wording and would silently leave a future strategy unguarded.

### Consequences

- The reference strategy's `strategy_id` (`reference_heartbeat_v1`) never appears in any LIVE-mode journal record, by construction.
- Guard behavior is proven through the real composition root using throwaway fixtures, establishing the standing pattern for any future strategy's guard proof.
- `reference_strategies/` is excluded from `core/` module import scanning (ADR-002 extension).
- A named limitation exists: shadow-state recovery across a process restart while a position is open is out of scope for this strategy — `on_start(context)` position projection remains reserved (ADR-017).

*Ref: docs/reports/MM12_4_REFERENCE_STRATEGY_ARCHITECTURE.md; ADR-002; ADR-016; ADR-017; ADR-018; ADR-019.*

---

## ADR-021 — Strategy Promotion Is Evidence-Gated, Ledgered, and Revocable

**Date:** 2026-07-02

**Status:** ACCEPTED

### Context

MM12 (External Strategy Integration Contract, ADR-014) establishes the `SignalSource` seam, the
conformance suite, the runtime guard, and the reference strategy through MM12.1–MM12.4. What does
not yet exist is the permanent governance process that every future strategy must follow from
creation through live deployment — the promotion pipeline. Without this, the seam, conformance,
guard, and reference are individually complete but have no binding lifecycle, no evidence
standards, no grant authority, and no revocation mechanism — and the Platform v1.0 freeze means
this governance must be purely documentary, consuming certified components without modifying them.

`docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` designs the pipeline and was
reviewed and approved by the Technical Lead. This ADR records MM12.5's core architectural
decisions as binding records, carrying MM12.1 §14.1's two fixed rules (no PAPER without
CONFORMANT; contract-relevant change restarts at CONFORMANT) into permanent governance.

### Decision

The platform adopts a five-stage promotion ladder, two non-ladder states, a fixed certification
identity triple, a dual-role authority model, and a permanent record scheme — all as documented:

1. **Five-stage ladder:** DEVELOPMENT → CONFORMANT → PAPER VALIDATED → LIVE CANDIDATE →
   LIVE APPROVED. No stage may be skipped (MM12.1 §14.1 fixed rule preserved). Each stage has
   defined purpose, entry criteria, required evidence, exit criteria, failure criteria, and
   rollback criteria exactly as specified in `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §4.

2. **Two non-ladder states:** SUSPENDED (trading halted, license in abeyance, re-entry via the
   strategy-attributable vs. external fork) and RETIRED (terminal, `strategy_id` never reused).

3. **Certification identity triple:** `(strategy_id, code_ref, config_hash) @ STRATEGY_CONTRACT_VERSION`.
   Any change to the triple creates a new identity entering at Stage 0 (§2). A major contract
   version bump voids all standing certifications (§3.1).

4. **Authority model:** Technical Lead grants on evidence (P1–P4); Account Owner commits capital
   (the capital half of P4, cap raises, retirement of live strategy). Demotion is permissionless
   by any party or automatic trigger (§8).

5. **Permanent records:** The append-only `docs/STRATEGY_PROMOTION_LEDGER.md` records every
   transition; per-strategy dossiers at `docs/strategies/<strategy_id>/` hold the permanent
   evidence corpus (§9).

6. **The pipeline consumes certified systems and never modifies them** (§0.1). All evidence is
   mechanical output of existing platform instruments. A promotion requirement that would need a
   change to a frozen component is, by definition, mis-specified.

### Alternatives Considered

- **Additional stages (BACKTESTED before CONFORMANT, LIVE RAMP between 3 and 4, RE-CERTIFICATION)** —
  rejected: each was evaluated in the architecture (§3.2) and found to add no new kind of evidence
  or to create pressure for a shortcut path. The existing five stages cover all distinct evidence
  gates.
- **Three-gate ladder (MM12.1 §14.1's original sketch)** — superseded: MM12.1 §15's exit criterion
  required the Stage 3/4 split (architectural completion vs. funded-account operational
  prerequisite) which the five-stage ladder executes.
- **Platform code enforcement (runtime `PromotionState` object)** — rejected as premature and
  architecture-violating: the pipeline lives in governance documents and the ledger, not in
  platform code. A runtime enforcement object would modify frozen components without a concrete
  need from a strategy in the pipeline.

### Consequences

- Every future strategy (including ports of historical designs) must follow the full ladder.
- Promotion without a ledger entry does not exist (§1.6).
- All evidence is pointer-chained: ledger → dossier → corpus/code ref, fully reconstructable
  offline (§9.3). A grant is audited by re-running its evidence.
- The two-authority model (ADR-013) is unaffected: the pipeline consumes sizing/admission
  outputs; it does not review the authority split.
- ADR-016 (strategy seam), ADR-017 (shadow state), ADR-018 (boundary validation), ADR-019
  (quarantine), and ADR-020 (reference strategy) are unaffected.
- `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` is the governing reference
  for all stage definitions, cross-cutting requirements, and promotion procedures.

*Ref: docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md §§0–§4, §8, §9;
docs/reports/MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §14.1, §14.2, §15;
ADR-002, ADR-005, ADR-013, ADR-016, ADR-017, ADR-018, ADR-019, ADR-020.*

---

## ADR-022 — Automatic Revocation Triggers and the Suspension Fork

**Date:** 2026-07-02

**Status:** ACCEPTED

### Context

ADR-021 establishes the promotion ladder and the principle that promotion is a revocable license,
not a diploma. It does not enumerate *what* triggers revocation — leaving each stage's failure
criteria implicit and creating two risks: (1) a guard event in LIVE may be treated differently
across strategies or stages; (2) the suspension fork (strategy-attributable vs. external cause)
has no binding rule, so every suspension requires a discretionary decision before re-entry —
defeating the "demotion is permissionless" principle.

`docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §7.6 defines a fixed trigger
table that resolves these risks. This ADR records that table and the suspension forks as binding,
and records the resolution of MM12.1 open question #3 (escalating contract-violation counts to
quarantine) for promotion purposes without any guard code change.

### Decision

1. **Fixed revocation trigger table.** The following events are binary failures at the stated
   stages — one occurrence voids the stage's evidence (PAPER) or triggers automatic suspension
   (LIVE):

| Event | In PAPER window | In LIVE |
|---|---|---|
| `STRATEGY_ERROR` / `STRATEGY_QUARANTINED` | Stage 2 failure | automatic suspension |
| `SIGNAL_CONTRACT_REJECTED` (even one) | Stage 2 failure | automatic suspension |
| Kill switch, strategy-attributable cause | Stage 2 failure | automatic suspension |
| Declared-max-DD breach (drawdown gate trip) | Stage 2 failure | automatic suspension |
| Reconciliation divergence, strategy-attributable | n/a (PAPER book is empty) | automatic suspension |
| Live trade not replay-explainable | n/a | automatic suspension |

2. **Zero-tolerance for post-certification guard events.** A CONFORMANT strategy has mechanically
   proven it never emits contract-violating signals on the certification corpus. Therefore the
   *first* post-certification guard event (any type) voids the certification. This resolves MM12.1
   open question #3 (escalation to quarantine) for promotion purposes: the guard's runtime policy
   (drop-and-journal, no escalation) is unchanged; the *pipeline* treats the first journaled
   rejection as certification-voiding. No guard code change — the journal already records the
   evidence (§7.6 note).

3. **The suspension fork.** Any suspension receives a ledger entry with trigger, timestamp, and
   open-position disposition. Within 5 trading days, an investigation report classifies the root
   cause as *strategy-attributable* or *external*. That classification governs re-entry (§3.1):
   - **External cause** (broker outage, platform defect, ops error) → grantor sign-off → resume
     at the prior stage (Stage 4 or Stage 2/3).
   - **Strategy-attributable cause** → the strategy has a defect → fix produces a new identity →
     re-enter at Stage 0.
   - **Unclassified within 5 days** → default to strategy-attributable (the default is the safe
     fork: the strategy does not resume until the operator proves the cause was external).

4. **Operator discretion is always preserved.** The fixed trigger list is the *minimum* suspension
   set. An operator may suspend at any time for any reason, with a justification recorded in the
   suspension ledger entry within 5 trading days.

5. **Kill-switch-and-journal is the mechanism.** The platform already has `activate_kill_switch`,
   journal events, and the *kill-switched-but-running* idiom (ADR-019). Suspension uses these
   existing instruments — no new runtime code.

### Alternatives Considered

- **Escalating violations (N-strike then quarantine in the guard)** — rejected for promotion
  purposes: a certified strategy has zero excuses for a contract violation, and the guard's v1.0
  runtime policy is frozen. The pipeline's zero-tolerance stance uses the existing journal as the
  evidence source, not a new guard code path.
- **Grace periods / warnings before suspension** — rejected: a certified deterministic strategy
  emitting a contract-violating signal has a defect; a grace period risks a second defective trade
  before the operator acts.
- **Auto-flatten on suspension** — rejected (consistent with ADR-019's decision): the platform
  never auto-flattens; the operator manages open positions manually via the broker.
- **Suspension as a promotion-rung (downgradable, upgradable without restart)** — rejected: the
  only re-entry path without ladder restart is the external-cause fork (§3.1). Any strategy-caused
  suspension exits through Stage 0.

### Consequences

- The trigger table is the **only** automatic revocation policy in the pipeline. It is not
  extensible by adding new triggers without a ledgered amendment to the architecture document.
- The MM12.1 open question #3 resolution means the pipeline treats a single `SIGNAL_CONTRACT_REJECTED`
  identically to a quarantine — both are certification-voiding. No guard code was changed to
  achieve this.
- Every LIVE session's `strategy_id` must map to a then-current LIVE APPROVED entry in the ledger
  at all times (§9.3). A mechanical scan of journal records against the ledger is the audit
  procedure.
- Demotion velocity is unconstrained: any party can suspend without waiting for a ledger entry.
  The investigation report requirement (within 5 trading days) is the backstop that prevents
  indefinite suspension without record.
- ADR-004 (no trading on stale data), ADR-019 (quarantine-and-continue), and the existing
  kill-switch mechanism are unchanged — this ADR only declares *what the pipeline does* when these
  events occur.
- `docs/STRATEGY_PROMOTION_LEDGER.md` gains suspension entry format requirements.

*Ref: docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md §§3.1, §5.1, §7.4.3, §7.6;
docs/reports/MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §8.5 (open question #3);
ADR-019, ADR-021; PLATFORM_CONSTITUTION.md §6; core/execution/handler.py (kill-switch).*
