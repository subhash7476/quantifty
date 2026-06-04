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
