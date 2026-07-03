# MSI-002
# Market State Intelligence Architecture
## Market Ontology

**Document ID:** MSI-002

**Version:** v1.0

**Status:** Frozen

**Classification:** Governing Architecture Specification

---

# 1. Purpose

This specification defines the canonical ontology of the Market State Intelligence (MSI) Architecture.

Its purpose is to establish the entities, relationships, and terminology used throughout the MSI Architecture.

This ontology is normative.

All subsequent MSI specifications shall use the definitions established herein.

---

# 2. Scope

This specification defines:

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

This specification intentionally does not define:

- inference algorithms
- statistical methods
- machine learning
- implementation details
- trading behaviour

---

# 3. Ontological Principles

## MSI-OP-001

Every architectural entity shall possess a single, well-defined meaning.

---

## MSI-OP-002

Architectural entities shall not overlap in responsibility.

---

## MSI-OP-003

Architectural entities shall remain implementation independent.

---

## MSI-OP-004

Later specifications may extend entities.

They shall not redefine them.

---

# 4. Canonical Entities

## 4.1 Market

A Market is the external system being observed.

MSI neither owns nor controls the Market.

---

## 4.2 Market Reality

Market Reality represents the complete state of the Market at a particular instant.

Market Reality exists independently of observation.

Market Reality cannot be directly accessed.

---

## 4.3 Observable

An Observable is a measurable property of Market Reality.

Examples include:

- traded price
- traded volume
- bid price
- ask price
- implied volatility
- open interest

Observables exist independently of MSI.

---

## 4.4 Observation

An Observation is a point-in-time measurement of one or more Observables.

Observations are immutable.

Observations contain no interpretation.

---

## 4.5 Evidence

Evidence is information derived from one or more Observations.

Evidence supports subsequent inference.

Evidence is neither Observation nor Knowledge.

---

## 4.6 Latent Variable

A Latent Variable is a property of Market Reality that cannot be directly observed.

Latent Variables exist conceptually whether or not they can currently be estimated.

A Latent Variable is a fact of Market Reality. It is never produced by observation; it is only ever estimated through Evidence.

---

## 4.7 Estimate

An Estimate is an inferred approximation of a Latent Variable, derived from Evidence.

Every Estimate carries both a value and a quantified uncertainty.

An Estimate is never certain; absolute certainty shall never be assumed.

An Estimate is not the Latent Variable itself. It is the best available inference of that Latent Variable at a particular instant.

---

## 4.8 Market State

Market State is the collection of Estimates of Latent Variables describing the Market at a particular instant.

Market State is multidimensional.

Market State is never represented by a single categorical label.

Every dimension of Market State carries its own uncertainty.

---

## 4.9 Knowledge

Knowledge is the runtime-exposed representation of Market State provided to trading strategies.

Knowledge is the only MSI output consumed by strategies.

---

## 4.10 Published MSI Artifact

A Published MSI Artifact is a governed research output approved for Platform runtime use.

It represents the only architectural interface between the Research domain and the Platform domain.

The internal structure of the artifact is defined in a later specification.

---

# 5. Ontological Relationships

The canonical relationships are:

```
Market Reality
  ├─ exposes ──> Observable ─> Observation ─> Evidence ─┐
  └─ contains ─> Latent Variable                        │
                       ▲                                │
                       └──── estimated by ─── Estimate <┘
                                                 │  (value + uncertainty)
                                                 ▼
                                            Market State
                                                 ▼
                                             Knowledge
```

A Latent Variable is a property of Market Reality. It is estimated through Evidence, never produced by it.

An Estimate carries a value and its uncertainty. Market State is the collection of Estimates. Knowledge is the runtime-exposed representation of Market State.

Published MSI Artifacts define how Estimates and Market State are produced.

Strategies consume Knowledge.

Strategies never consume Estimates, Evidence, or Observations.

---

# 6. Ontological Decisions

## MSI-OD-001

Market State is a multidimensional construct.

It shall never be reduced to a single architectural entity.

---

## MSI-OD-002

Knowledge is the only MSI representation exposed to strategies.

Strategies consume Knowledge through existing Platform interfaces, not through any MSI-owned channel (MSI-001 MSI-CD-003).

---

## MSI-OD-003

Published MSI Artifacts constitute the only interface between Research and Platform.

---

## MSI-OD-004

Ontology shall remain independent of inference methodology.

---

## MSI-OD-005

Every Estimate shall carry quantified uncertainty.

Market State shall never be represented as certain (MSI-001 MSI-FA-004).

---

# 7. Consequences

This ontology establishes a strict separation between:

- Market Reality
- Observation
- Evidence
- Estimate
- Market State
- Knowledge

Later specifications define how transitions occur between these entities.

This specification defines only that the entities exist.

---

# 8. Dependencies

Depends upon:

- MSI-001

Required by:

- MSI-003
- MSI-004
- MSI-005
- MSI-006
- MSI-007
- MSI-008
- MSI-009

---

# 9. Status

Current Status:

v1.0

Frozen

---

**End of Document**
