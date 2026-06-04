# PLATFORM_CONSTITUTION.md

Version: 1.0
Repository: F:\Nifty
Status: Foundational Document

---

# 1. Mission

F:\Nifty exists to provide a professional-grade execution, risk, ledger, and operations platform for Indian derivatives trading.

The platform's purpose is to safely execute, monitor, reconcile, and risk-manage trading activity.

The platform is not responsible for generating alpha.

Supported trading books:

1. Equity Futures (directional)

   * Typical holding period: 3–15 trading days
   * Typical concentration: 3–10 positions

2. Index Option Selling

   * NIFTY options
   * BANKNIFTY options

The platform must remain strategy-agnostic.

---

# 2. Core Principles

## Principle 1 — Ledger is Truth

The platform's internal ledger is the primary source of truth.

Priority order:

Exchange
→ Broker
→ Execution Engine
→ Ledger
→ Risk Engine
→ Dashboard

No dashboard, strategy, or broker API response may override ledger truth.

---

## Principle 2 — Execution Before Alpha

Execution quality is more important than signal quality.

The platform prioritizes:

* Order correctness
* Fill tracking
* Position accuracy
* Risk enforcement
* Reconciliation

over:

* Indicators
* Models
* Predictions
* Research outputs

---

## Principle 3 — Deterministic Operation

Every trading action must be explainable and reproducible.

The platform shall maintain:

* Single execution path
* Single position truth
* Deterministic event processing
* Auditable state transitions

Hidden side effects are prohibited.

---

## Principle 4 — Risk Before Trading

No trade may exist without defined risk.

Required before order submission:

* Position size
* Risk amount
* Stop definition
* Margin validation
* Risk clearance

The platform may refuse trades that violate risk constraints.

---

## Principle 5 — No Trading On Stale Data

Data integrity is mandatory.

The platform shall:

* Monitor feed freshness
* Detect stale data
* Alert operators
* Activate protective controls when necessary

Trading on stale market data is prohibited.

---

# 3. Platform Responsibilities

The platform is responsible for:

## Market Data

* Live data ingestion
* Historical data access
* Instrument metadata
* Market session handling
* Options chain retrieval

## Execution

* Order creation
* Order submission
* Order modification
* Order cancellation
* Fill processing
* Execution recovery

## Ledger

* Orders
* Fills
* Positions
* PnL
* Trade history

## Risk

* Position limits
* Margin checks
* Exposure monitoring
* Greeks monitoring
* Kill-switch enforcement

## Reconciliation

* Broker reconciliation
* Position reconciliation
* State recovery
* Startup consistency checks

## Observability

* Telemetry
* Heartbeat monitoring
* Health checks
* Alerting

## Operations Dashboard

* System health
* Positions
* Orders
* PnL
* Margin
* Greeks

---

# 4. Explicit Non-Responsibilities

The platform shall not contain:

## Research

* Research notebooks
* Experimental studies
* Optimization experiments
* Parameter sweeps

## Machine Learning

* Model training
* Feature engineering
* Label generation
* Training pipelines

## Strategy Research

* Signal discovery
* Alpha research
* Market regime research

## Backtesting

* Backtest engines
* Walk-forward frameworks
* Research simulations

## Scanning Systems

* Equity scanners
* Opportunity scanners
* Screening engines

These belong outside the platform repository.

---

# 5. Strategy Boundary

Strategies consume platform services.

Strategies do not own platform infrastructure.

Allowed dependency:

Strategy
→ Platform

Forbidden dependency:

Platform
→ Strategy

The platform must remain usable even when no strategies exist.

---

# 6. Observability Requirements

Every live trading process must expose:

* Heartbeat
* Health status
* Telemetry
* Error reporting

Failures must be observable without broker login.

Silent failure is unacceptable.

---

# 7. Operational Safety Requirements

The platform shall support:

* Kill switch
* Recovery after restart
* Reconciliation checks
* Audit trail generation

A position must never become untraceable.

---

# 8. Option Selling Requirements

The platform must support:

* Margin-aware execution
* Greeks monitoring
* Portfolio Greeks aggregation
* Option position tracking

The platform does not assume any specific option-selling strategy.

---

# 9. Equity Futures Requirements

The platform must support:

* Multi-position futures portfolios
* Position sizing
* Portfolio exposure tracking
* Futures carry positions

The platform does not assume any specific futures entry methodology.

---

# 10. Repository Standard

Every new module must answer:

1. Does this belong to the platform?
2. Does it belong to a strategy?
3. Does it belong to research?

If uncertain:

Platform code shall be kept smaller.

Research and strategy code shall remain separate.

---

# 11. Long-Term Goal

F:\Nifty shall evolve into a professional Indian derivatives execution and risk platform whose infrastructure remains stable regardless of changes in trading strategies.

Strategies may change.

The platform should not.
