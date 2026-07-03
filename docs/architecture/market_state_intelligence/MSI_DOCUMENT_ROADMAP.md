# MSI Architecture Roadmap

**Architecture Program:** Market State Intelligence (MSI)

**Status:** Complete — MSI v1.0 Frozen

**Version:** 1.3

---

# Purpose

This document defines the complete roadmap of the Market State Intelligence (MSI) Architecture Program.

It establishes the governing architecture specifications, their objectives, dependencies, implementation order, and completion status.

This document is administrative.

It does not define architecture.

---

# Architecture Philosophy

The MSI Architecture is intentionally layered.

Each specification introduces concepts that become prerequisites for subsequent specifications.

Later specifications shall not redefine concepts established by earlier governing documents.

## Two Pipelines

The MSI Architecture describes two distinct pipelines that share one upstream spine:

```
Research:  Observation → Evidence → Inference → Validation → Artifact
Runtime:   Observation → Evidence → Artifact Evaluation → Knowledge → Strategy
```

- **Observation and Evidence (MSI-003, MSI-004) are the shared spine** — identical in both pipelines. Consuming Evidence under a single MSI-004 contract in both research inference and runtime evaluation is the structural guarantee against train/serve skew, and is what allows MSI-005's determinism and point-in-time guarantees to hold.
- **The Published Artifact is the join point** — the terminal output of the Research pipeline and the input to the Runtime pipeline. This is why it is the only interface between Research and Platform (MSI-002 MSI-OD-003).

Every responsibility in the program shall have exactly one owning specification.

---

# Document Dependency Graph

```
MSI-001
Philosophy & First Principles
        │
        ▼
MSI-002
Market Ontology
        │
        ▼
MSI-003
Observation Architecture
        │
        ▼
MSI-004
Evidence Architecture
        │
        ▼
MSI-005
State Inference Architecture
        │
        ▼
MSI-006
Validation Framework
        │
        ▼
MSI-007
Published Artifact Specification
        │
        ▼
MSI-008
Artifact Governance
        │
        ▼
MSI-009
Daily Regime Analyzer Architecture
```

---

# Governing Specifications

---

## MSI-001

**Title**

Philosophy & First Principles

**Purpose**

Defines the governing principles of the Market State Intelligence Architecture.

**Primary Deliverables**

- Purpose
- Scope
- Philosophy
- First Principles
- Governing Principles
- Governing Decisions
- Non-Goals
- Foundational Separation

**Depends On**

None

---

## MSI-002

**Title**

Market Ontology

**Purpose**

Defines the canonical entities that exist within the MSI Architecture.

**Primary Deliverables**

- Market
- Market Reality
- Observable
- Observation
- Evidence
- Latent Variable
- Estimate
- Market State
- Knowledge
- Published MSI Artifact

**Depends On**

MSI-001

---

## MSI-003

**Title**

Observation Architecture

**Purpose**

Defines how market observations enter the architecture.

**Primary Deliverables**

- Observation Read-Contract
- Observation Standardisation
- Observation Quality
- Observation Provenance References
- Observation Integrity

**Depends On**

MSI-002

---

## MSI-004

**Title**

Evidence Architecture

**Purpose**

Defines how observations become evidence suitable for inference.

**Primary Deliverables**

- Evidence Model
- Evidence Construction
- Evidence Contract
- Evidence Provenance
- Evidence Quality
- Evidence Lifecycle

**Depends On**

MSI-003

---

## MSI-005

**Title**

State Inference Architecture

**Purpose**

Defines the architecture responsible for inferring latent market state from evidence. Owns both the research-facing inference contract and the runtime artifact-evaluation engine; Knowledge is the output object of the inference architecture, not a separate layer.

**Primary Deliverables**

- Inference Interfaces
- Confidence Estimation
- Uncertainty Representation
- Knowledge Construction (Knowledge Object as inference output)
- Runtime Artifact Evaluation (deterministic, replayable)
- Model Independence
- Inference Contracts

**Depends On**

MSI-004

---

## MSI-006

**Title**

Validation Framework

**Purpose**

Defines scientific validation requirements for MSI.

**Primary Deliverables**

- Validation Methodology
- Benchmarking
- Calibration
- Robustness Testing
- Drift Detection
- Acceptance Criteria
- Validation Identifier (owner)

**Depends On**

MSI-005

---

## MSI-007

**Title**

Published Artifact Specification

**Purpose**

Defines the internal structure, schema, and contract of the Published MSI Artifact — the only interface between the Research domain and the Platform domain (MSI-002 MSI-OD-003). Introduced before Research Governance because every subsequent specification depends on the artifact as the Research→Runtime join point.

**Primary Deliverables**

- Artifact Internal Structure
- Artifact Schema and Versioning Contract
- Runtime Binding Contract (reconciled with MSI-005's runtime binding metadata)
- Validation Identifier Reference (owned by MSI-006)
- Provenance and Reproducibility Requirements
- Compatibility and Schema-Version Rules

**Depends On**

MSI-006

---

## MSI-008

**Title**

Artifact Governance

**Purpose**

Defines lifecycle management of Published MSI Artifacts.

**Primary Deliverables**

- Artifact Lifecycle (Candidate → Validated → Publication Approved → Published → Active → Superseded → Retired)
- Publication Approval
- Deployment Governance
- Artifact Promotion
- Supersession
- Retirement
- Revalidation Governance
- Drift Response

**Depends On**

MSI-007

---

## MSI-009

**Title**

Daily Regime Analyzer Architecture

**Purpose**

Defines the first implementation of the Market State Intelligence Architecture.

**Primary Deliverables**

- DRA Scope
- Inputs
- Outputs
- Interfaces
- Runtime Behaviour
- Validation Requirements
- Integration with Platform Infrastructure

**Depends On**

MSI-008

---

# Future Specifications

The following specifications may be introduced after completion of the governing architecture.

Examples include:

- Intraday State Engine
- Liquidity State Engine
- Options State Engine
- Macro State Engine
- Portfolio State Engine
- Cross-Asset State Engine

These specifications shall conform to MSI-001 through MSI-008.

---

# Architecture Freeze Order

Specifications shall be frozen in numerical order.

```
MSI-001

↓

MSI-002

↓

MSI-003

↓

MSI-004

↓

MSI-005

↓

MSI-006

↓

MSI-007

↓

MSI-008

↓

MSI-009
```

A later specification shall not be frozen if any prerequisite specification remains unfrozen.

---

# Document Status

| Document | Status |
|-----------|--------|
| MSI-001 | Frozen — v1.0 |
| MSI-002 | Frozen — v1.0 |
| MSI-003 | Frozen — v1.0 |
| MSI-004 | Frozen — v1.0 |
| MSI-005 | Frozen — v1.0 |
| MSI-006 | Frozen — v1.0 |
| MSI-007 | Frozen — v1.0 |
| MSI-008 | Frozen — v1.0 |
| MSI-009 | Frozen — v1.0 |

---

# Governance Rule

This roadmap defines the canonical structure of the Market State Intelligence Architecture Program.

Changes to this roadmap follow the platform's existing governance — the ADR process (`docs/ARCHITECTURE_DECISIONS.md`) and PROJECT_STATE. MSI introduces no parallel governance body. The 1.2 revision (Published Artifact Specification introduced as MSI-007; Research Governance and DRA renumbered; MSI-005 resolved to owns-both) is recorded as ADR-023.

---

**End of Document**