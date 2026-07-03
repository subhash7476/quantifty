# MSI-009
# Market State Intelligence Architecture
## Daily Regime Analyzer (DRA) Architecture

**Document ID:** MSI-009

**Version:** v1.0

**Status:** Frozen

**Classification:** Reference Implementation Architecture

---

# 1. Purpose

This specification defines the architecture of the Daily Regime Analyzer (DRA), the first production Market State Engine implemented within the Market State Intelligence (MSI) Architecture.

The DRA serves two purposes:

- provide deterministic daily Market State Knowledge for trading strategies;
- demonstrate the implementability of the MSI constitutional architecture through a concrete reference implementation.

This specification defines architecture only. It does not define implementation algorithms.

---

# 2. Relationship to Previous Specifications

The DRA implements and shall conform to MSI-001 through MSI-008.
No architectural concept introduced by the DRA may contradict or redefine those specifications.

---

# 3. Scope

This specification defines:

- runtime responsibilities
- runtime architecture
- observation consumption
- evidence construction
- artifact evaluation
- knowledge production
- runtime integration
- validation requirements

It does **not** define:

- statistical models
- machine learning
- feature engineering
- optimisation
- research workflow
- trading strategy logic

The DRA operates at **daily cadence**. This is a reference implementation decision. The MSI architecture itself remains cadence-agnostic.

---

# 4. Architectural Role

The Daily Regime Analyzer is a Runtime Market State Engine implementing the complete MSI Runtime Pipeline.

It:

- consumes Platform Observations (MSI-003);
- constructs deterministic Evidence (MSI-004);
- evaluates an Active Published MSI Artifact (MSI-005, MSI-007, MSI-008);
- produces deterministic Daily Market Knowledge.

The DRA never generates trading signals.

---

# 5. Runtime Architecture

```text
                   Published MSI Artifact
                             │
                             │
Platform Observations ───────┼──────────────┐
                             │              │
                             ▼              │
                  Evidence Construction     │
                             │              │
                             ▼              │
                    Artifact Evaluation ◄───┘
                             │
                             ▼
                 Daily Market Knowledge
                             │
                             ▼
                         Strategy Layer
                             │
                             ▼
                        SignalSource
```

The Published MSI Artifact is a runtime input, not a runtime transformation stage.

---

# 6. Responsibilities

The DRA shall:

- consume Platform Observations;
- construct deterministic Evidence;
- evaluate Active Published MSI Artifacts;
- produce deterministic Daily Market Knowledge;
- expose Knowledge through Platform-defined interfaces;
- preserve provenance;
- support deterministic replay.

The DRA shall not:

- train models;
- optimise parameters;
- perform research;
- modify artifacts;
- generate trading signals.

---

# 7. Observation Requirements

The DRA consumes observations conforming to MSI-003.

As a complete Runtime Pipeline, it constructs Evidence from those observations before artifact evaluation.

Observation sources shall remain deterministic, immutable, replayable and point-in-time correct.

---

# 8. Evidence Requirements

Evidence construction shall conform to MSI-004.

Construction rules originate from the Published MSI Artifact.

Evidence shall remain deterministic and preserve provenance.

---

# 9. Artifact Evaluation

The DRA implements the MSI-005 Runtime Artifact Evaluation Engine and satisfies the State Inference Contract defined by MSI-005.

Inference methodology remains implementation-defined.

Runtime behaviour shall remain deterministic.

---

# 10. Knowledge Outputs

The DRA produces Daily Market Knowledge.

Knowledge Objects shall conform to the Knowledge Object defined by MSI-005.

This specification does not redefine the Knowledge schema.

---

# 11. Runtime Integration

The DRA integrates exclusively through Platform interfaces defined by the Platform Architecture.

Strategies consume Knowledge.

Strategies alone generate trading signals.

---

# 12. Validation

The DRA shall satisfy MSI-006 before any artifact becomes eligible for runtime use.

---

# 13. Artifact Usage

The DRA executes only **Active Published MSI Artifacts** governed by MSI-007 and MSI-008.

---

# 14. Governance

Artifact lifecycle is governed exclusively by MSI-008.

The DRA performs no governance operations.

---

# 15. Architectural Principles

- MSI-DRA-001 The DRA shall remain deterministic.
- MSI-DRA-002 The DRA shall remain replayable.
- MSI-DRA-003 The DRA shall remain strategy-independent.
- MSI-DRA-004 The DRA shall preserve complete provenance.
- MSI-DRA-005 The DRA shall conform to MSI-001 through MSI-008.

---

# 16. Architectural Decisions

- MSI-9D-01 The DRA is the reference implementation of the MSI Architecture.
- MSI-9D-02 The DRA introduces no new constitutional concepts.
- MSI-9D-03 Future Market State Engines shall conform to the same architectural contracts.
- MSI-9D-04 The DRA demonstrates the implementability of the MSI Architecture.

---

# 17. Consequences

Successful implementation demonstrates that:

- the constitutional architecture is implementable;
- Research and Platform remain separated;
- deterministic Market State Intelligence integrates without Platform redesign;
- future Market State Engines can reuse the same contracts.

---

# 18. Dependencies

Depends upon MSI-001 through MSI-008.

---

# 19. Status

Current Status:

v1.0

Frozen

---

**End of Document**
