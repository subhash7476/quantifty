# Market State Intelligence (MSI)

**Status:** Frozen — v1.0

---

# Overview

Market State Intelligence (MSI) defines the architectural framework through which scientifically validated market-state knowledge is made available to trading strategies in a deterministic, auditable, and reproducible manner.

MSI is **not** a trading strategy.

MSI is **not** a machine learning framework.

MSI is **not** a market research environment.

MSI defines the architectural boundary between **offline market-state research** and **deterministic runtime consumption**.

---

# Platform Classification

The Platform Constitution classifies all functionality as one of:

- Platform
- Strategy
- Research

MSI spans two domains with a strictly controlled boundary.

---

## Offline MSI Research

**Classification:** Research

Responsibilities include:

- market-state research
- hypothesis development
- feature engineering
- model development
- parameter optimisation
- scientific experimentation
- validation
- publication of approved MSI Artifacts

These activities are performed **outside the Platform repository**.

Research outputs become eligible for Platform use only after satisfying the scientific and governance requirements defined by the MSI Architecture.

---

## Runtime MSI

**Classification:** Platform

Responsibilities include:

- loading approved MSI Artifacts
- deterministic runtime evaluation
- exposing market-state information to strategies
- deterministic replay
- auditability
- artifact version tracking

Runtime MSI performs **no**:

- model training
- feature engineering
- parameter optimisation
- research
- model adaptation

Runtime MSI is a deterministic runtime consumer of previously approved research outputs.

---

# Architectural Position

```
Research Repository
────────────────────────────────────────────

Market State Research

↓

Training

↓

Validation

↓

Published MSI Artifact


====================================================

Platform Repository

Published MSI Artifact

↓

Runtime MSI

↓

Strategy
(read-only MSI consumer)

↓

SignalSource

↓

Platform Infrastructure

↓

Execution
```

The strategy remains the sole producer of trading signals through the existing `SignalSource` interface.

Runtime MSI provides market-state information only.

Runtime MSI never generates trading signals.

---

# Mission

The mission of MSI is to provide deterministic, reproducible, and auditable market-state knowledge derived from scientifically validated offline research while remaining independent of any specific statistical, mathematical, or machine learning methodology.

---

# Guiding Principles

MSI adopts the following architectural principles.

- Architecture before implementation.
- Research remains outside the Platform repository.
- Runtime remains deterministic.
- Runtime is read-only.
- Point-in-time correctness is mandatory.
- Look-ahead bias is prohibited.
- Scientific validation precedes deployment.
- Complete auditability.
- Strategy independence.
- Broker independence.

---

# Relationship to the Platform

The Platform Constitution remains the governing authority.

MSI shall conform to all existing Platform principles, including:

- Ledger is Truth
- Execution Before Alpha
- Deterministic Operation
- Risk Before Trading
- No Trading On Stale Data

MSI shall never supersede these principles.

MSI exists solely to provide market-state knowledge that strategies may choose to consume.

Trading decisions remain the sole responsibility of strategies.

---

# Published MSI Artifact

The **Published MSI Artifact** is the controlled interface between Research and Platform.

Only Published MSI Artifacts may cross the Research → Platform boundary.

Each artifact shall be:

- uniquely identifiable
- versioned
- reproducible
- scientifically validated
- traceable to its originating research
- approved through the Platform governance process

Runtime replay shall identify the exact MSI Artifact version used to produce every market-state output.

The formal MSI Artifact specification is defined in MSI-007 (Published Artifact Specification).

---

# Runtime Determinism

Runtime MSI shall evaluate only deterministic, point-in-time platform facts.

Runtime MSI shall not perform:

- online feature engineering
- online model training
- parameter optimisation
- historical reinterpretation
- adaptive learning

Given identical:

- Platform facts
- MSI Artifact version
- runtime configuration

Runtime MSI shall always produce identical outputs.

---

# Architecture Documents

| ID | Document |
|----|----------|
| MSI-001 | Philosophy & Governing Principles |
| MSI-002 | Market Ontology |
| MSI-003 | Observation Architecture |
| MSI-004 | Evidence Architecture |
| MSI-005 | State Inference Architecture |
| MSI-006 | Validation Framework |
| MSI-007 | Published MSI Artifact Specification |
| MSI-008 | Artifact Governance Architecture |
| MSI-009 | Daily Regime Analyzer (DRA) Architecture |

---

# Reading Order

Architecture specifications shall be read in numerical order.

Each specification defines constraints for subsequent specifications.

No later specification may contradict an earlier governing specification.

---

# Governance

MSI adopts the existing Platform governance.

Architecture changes shall follow:

- Platform Constitution
- Existing ADR process
- PROJECT_STATE
- Strategy Promotion governance

MSI introduces no parallel governance model.

---

# Implementation Status

The current Platform contains no production strategies.

Accordingly, Runtime MSI remains an architectural specification.

Implementation shall be initiated only when required by the first production strategy (MM13), ensuring compliance with the Platform principle of avoiding speculative abstractions.

---

# Current Status

MSI Architecture — **Frozen (v1.0)**

Reference Runtime Engine: **Daily Regime Analyzer (DRA)** — Ready for Implementation

Runtime implementation shall be initiated only when required by the first production strategy (MM13), ensuring compliance with the Platform principle of avoiding speculative abstractions.

---

**End of Document**
