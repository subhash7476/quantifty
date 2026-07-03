# MSI Program Charter

**Program:** Market State Intelligence (MSI)

**Version:** v1.0

**Status:** Complete — MSI Architecture Frozen

The constitutional MSI Architecture is complete and frozen. All nine governing specifications (MSI-001 through MSI-009) are at v1.0 Frozen. Current phase: Implementation.

---

# 1. Purpose

This charter establishes the objectives, scope, governance, and operating principles of the Market State Intelligence (MSI) Architecture Program.

MSI extends the Platform Infrastructure by defining a deterministic, auditable mechanism through which validated market-state information may be consumed by trading strategies.

This charter governs the architecture program.

It does not define implementation.

---

# 2. Relationship to the Platform

The Platform Constitution remains the governing authority.

MSI shall conform to all existing Platform principles, including:

- Ledger is Truth
- Execution Before Alpha
- Deterministic Operation
- Risk Before Trading
- No Trading On Stale Data

Nothing within MSI supersedes the Platform Constitution.

---

# 3. Program Classification

MSI consists of two independent domains.

## Domain A — Research

Classification: **Research**

Responsibilities include:

- market-state research
- hypothesis development
- feature engineering
- model development
- parameter optimisation
- scientific experimentation
- validation
- publication of approved MSI artifacts

Research activities occur outside the Platform repository.

---

## Domain B — Runtime

Classification: **Platform**

Responsibilities include:

- loading published MSI artifacts
- deterministic runtime evaluation
- exposing market-state information
- deterministic replay
- auditability

Runtime MSI performs no research.

Runtime MSI performs no model training.

Runtime MSI performs no parameter optimisation.

---

# 4. Mission

The mission of MSI is to provide deterministic market-state information derived from scientifically validated offline research while preserving the architectural principles of the Platform Infrastructure.

---

# 5. Objectives

The objectives of the MSI program are:

- establish a formal Market State Intelligence Architecture;
- define a canonical Market Ontology;
- standardise market observations;
- standardise evidence generation;
- define deterministic runtime interfaces;
- establish scientific validation requirements;
- provide a reusable foundation for future Market State Engines.

---

# 6. Scope

The MSI Architecture governs:

- Market Ontology
- Observation Architecture
- Evidence Architecture
- State Inference Architecture
- Validation Framework
- Published Artifact Specification
- Runtime Market State Interfaces

The MSI Architecture does not govern:

- trade execution
- order management
- portfolio management
- broker integration
- position sizing
- execution risk
- margin calculation

These remain Platform responsibilities.

---

# 7. Architectural Principles

The MSI program adopts the following principles.

## Principle 1

Architecture precedes implementation.

---

## Principle 2

Research is separated from runtime.

---

## Principle 3

Runtime remains deterministic.

---

## Principle 4

Inference shall be point-in-time correct.

---

## Principle 5

Future information shall never influence historical inference.

---

## Principle 6

Scientific validation precedes runtime deployment.

---

## Principle 7

Runtime consumes published MSI artifacts.

Runtime does not create them.

---

# 8. Deliverables

The MSI program consists of the following governing specifications.

| Document | Purpose |
|-----------|---------|
| MSI-001 | Philosophy & First Principles |
| MSI-002 | Market Ontology |
| MSI-003 | Observation Architecture |
| MSI-004 | Evidence Architecture |
| MSI-005 | State Inference Architecture |
| MSI-006 | Validation Framework |
| MSI-007 | Published Artifact Specification |
| MSI-008 | Artifact Governance |
| MSI-009 | Daily Regime Analyzer (DRA) Architecture |

Implementation specifications may follow after the governing architecture has been approved.

---

# 9. Governance

MSI adopts the existing Platform governance.

Changes to MSI shall use:

- Platform Constitution
- Existing ADR process
- PROJECT_STATE
- Strategy Promotion governance

MSI introduces no parallel governance process.

---

# 10. Scientific Requirements

Every published MSI artifact shall satisfy, at minimum:

- deterministic reproduction;
- point-in-time correctness;
- no look-ahead bias;
- complete auditability;
- documented provenance;
- out-of-sample validation.

Artifacts failing these requirements shall not enter the Platform runtime.

---

# 11. Runtime Boundary

The runtime boundary is fixed.

```
Offline Research

↓

Published MSI Artifact

=========================

Platform Runtime

↓

Runtime MSI

↓

Strategy

↓

SignalSource

↓

Platform Infrastructure
```

No runtime component shall:

- train models;
- engineer features;
- optimise parameters;
- modify published artifacts.

---

# 12. Success Criteria

The MSI program is successful when:

- research remains outside the Platform repository;
- runtime remains deterministic;
- market-state information is reproducible;
- strategies consume MSI through existing platform interfaces;
- future Market State Engines can be introduced without architectural changes.

---

# 13. Definition of Done

The MSI Architecture Program is complete when:

- all governing MSI specifications are approved;
- all governing MSI specifications are frozen;
- the first Runtime Market State Engine is integrated through the existing Strategy interface;
- no Platform constitutional principle is violated.

---

# 14. Governing Statement

MSI extends the Platform Infrastructure by providing deterministic market-state information.

MSI does not replace research.

MSI does not replace trading strategies.

MSI does not replace Platform Infrastructure.

MSI provides the architectural bridge between validated research and deterministic strategy execution.

---

**End of Document**
