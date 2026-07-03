# MSI-001
# Market State Intelligence Architecture
## Philosophy & Governing Principles

**Document ID:** MSI-001

**Version:** v1.0

**Status:** Frozen

**Classification:** Governing Architecture Specification

**Architecture Program:** Market State Intelligence (MSI)

---

# 1. Purpose

This document establishes the governing principles for the Market State Intelligence (MSI) Architecture. It defines the durable architectural rules that all present and future MSI components shall follow, while intentionally avoiding implementation details, algorithms, statistical methods, and machine learning techniques — those concerns belong to later specifications.

These principles are subordinate to the Platform Constitution. They govern MSI only, introduce no parallel authority or review body, and are change-controlled through the platform's existing ADR process (`docs/ARCHITECTURE_DECISIONS.md`).

---

# 2. Scope

This specification governs:

- architectural philosophy
- constitutional principles
- architectural boundaries
- responsibilities
- runtime constraints
- conformance requirements

This specification does not define:

- market ontology
- observation architecture
- evidence generation
- inference algorithms
- machine learning
- trading strategies
- implementation details

---

# 3. Relationship to the Platform

The Platform Constitution remains the governing authority for the repository.

MSI extends the Platform Architecture.

MSI shall not supersede or contradict any Platform constitutional principle.

In particular, MSI shall remain consistent with:

- Ledger is Truth
- Execution Before Alpha
- Deterministic Operation
- Risk Before Trading
- No Trading On Stale Data

MSI exists to provide market-state knowledge.

Trading decisions remain the responsibility of strategies.

---

# 4. Architectural Boundary

MSI consists of two independent domains.

## 4.1 Research Domain

Classification:

**Research**

Responsibilities include:

- hypothesis development
- market-state research
- feature engineering
- model development
- scientific validation
- publication of MSI Artifacts

The Research Domain exists outside the Platform repository.

---

## 4.2 Runtime Domain

Classification:

**Platform**

Responsibilities include:

- loading approved MSI Artifacts
- deterministic runtime evaluation
- exposing market-state knowledge
- replay support
- auditability

Runtime MSI performs no:

- research
- model training
- feature engineering
- parameter optimisation
- adaptive learning

---

# 5. Foundational Assumptions

The MSI Architecture adopts the following assumptions.

## MSI-FA-001

Financial markets possess structural properties that cannot be directly observed.

---

## MSI-FA-002

Observable market data provide evidence regarding those structural properties.

---

## MSI-FA-003

Market-state estimates are derived from evidence rather than directly measured.

---

## MSI-FA-004

Every market-state estimate contains uncertainty.

Absolute certainty shall never be assumed.

---

## MSI-FA-005

Inference technologies evolve.

Architecture shall remain stable.

---

# 6. Governing Principles

## MSI-CP-001

### Platform First

MSI shall conform to the Platform Constitution.

No MSI specification may weaken or replace Platform constitutional principles.

---

## MSI-CP-002

### Research Separation

Research activities shall remain outside the Platform repository.

Only approved MSI Artifacts may cross into Platform runtime.

---

## MSI-CP-003

### Runtime Determinism

Runtime MSI shall remain deterministic.

Given identical:

- platform facts
- MSI Artifact
- runtime configuration

identical outputs shall always be produced.

---

## MSI-CP-004

### Point-in-Time Correctness

Every runtime inference shall use only information available at the evaluation timestamp.

Future information shall never influence historical inference.

---

## MSI-CP-005

### No Look-Ahead

Look-ahead bias is prohibited.

Historical replay shall produce exactly the same market-state outputs that would have been available at that historical instant.

---

## MSI-CP-006

### Scientific Validation

Every MSI Artifact shall undergo scientific validation before publication.

Validation shall include out-of-sample and walk-forward evaluation. In-sample performance is not sufficient evidence of validity. Validation methods and acceptance thresholds are defined in a later MSI specification (MSI-006).

Runtime shall consume only validated artifacts.

---

## MSI-CP-007

### Auditability

Every market-state output shall be traceable to:

- Platform facts
- MSI Artifact version
- runtime configuration

Complete replay shall be supported.

---

## MSI-CP-008

### Strategy Independence

MSI provides market-state knowledge.

Strategies remain solely responsible for:

- signal generation
- trading decisions
- position management

MSI shall never generate trading signals.

---

## MSI-CP-009

### Implementation Independence

The governing architecture shall remain independent of:

- statistical models
- machine learning algorithms
- optimisation methods
- inference engines

Implementations may evolve without requiring constitutional change.

---

# 7. Governing Decisions

## MSI-CD-001

### Decision

MSI shall be implemented as a deterministic runtime consumer of validated research outputs.

### Rationale

Separating research from runtime preserves Platform determinism while allowing unrestricted scientific experimentation.

---

## MSI-CD-002

### Decision

The Published MSI Artifact is the only architectural interface between Research and Platform.

### Rationale

A single governed interface enables reproducibility, version control, validation, and auditability.

---

## MSI-CD-003

### Decision

Strategies shall consume market-state knowledge through existing Platform interfaces.

### Rationale

MSI shall integrate with the existing Platform Architecture without introducing privileged execution paths.

---

## MSI-CD-004

### Decision

Runtime MSI implementation shall be demand-driven.

### Rationale

Runtime components shall be introduced only when required by a production strategy, preventing speculative platform abstractions.

---

# 8. Non-Goals

MSI does not:

- discover trading strategies
- optimise profitability
- train models
- engineer features at runtime
- execute trades
- manage positions
- calculate risk
- allocate capital
- interact with brokers

These responsibilities belong elsewhere within the overall system architecture.

---

# 9. Conformance Requirements

Every MSI specification shall demonstrate conformance with this document.

Specifically, every subsequent specification shall:

- preserve deterministic operation;
- preserve Platform constitutional principles;
- respect the Research/Platform boundary;
- preserve point-in-time correctness;
- prohibit look-ahead bias;
- support deterministic replay;
- avoid implementation-specific architectural dependencies.

Specifications that violate these requirements shall not be approved.

---

# 10. Dependencies

This specification is the constitutional foundation of the MSI Architecture.

All subsequent MSI specifications depend upon this document.

No later specification may contradict its principles.

---

# 11. Status

Current Status:

v1.0

Frozen

---

**End of Document**
