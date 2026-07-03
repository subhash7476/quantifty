# MSI-004
# Market State Intelligence Architecture
## Evidence Architecture

**Document ID:** MSI-004

**Version:** v1.0

**Status:** Frozen

**Classification:** Governing Architecture Specification

---

# 1. Purpose

This specification defines the Evidence Architecture of the Market State Intelligence (MSI) framework.

Evidence transforms immutable Observations into standardized Evidence suitable for market-state inference.

The *design* of evidence transforms is offline Research. The *runtime* deterministically evaluates validated, versioned evidence-construction rules carried by a Published MSI Artifact. Evidence Architecture performs interpretation only in this constrained sense — it performs no inference and no market-state estimation.

---

# 2. Offline / Runtime Separation

Evidence construction spans the Research/Platform boundary and shall be split accordingly, mirroring MSI-001 §4.1/§4.2 and the MSI-003 reframe.

**Offline (Research, outside the Platform repository):**

- designing evidence transforms — what constitutes evidence and how it is constructed;
- feature engineering and experimentation;
- validation of evidence-construction rules.

These are Research activities. They cross into the Platform only as validated, versioned evidence-construction rules inside a **Published MSI Artifact** (MSI-001 `MSI-CD-002`, MSI-002 §4.10).

**Runtime (Platform, read-only):**

- deterministically evaluates the artifact's validated evidence-construction rules against point-in-time Observations;
- performs no discovery, fitting, feature engineering, or rule authoring.

This keeps runtime Evidence within *Analytics Produce Facts — runtime read-only* and MSI-001 `MSI-CD-004` (demand-driven; no speculative platform abstractions).

---

# 3. Scope

This specification defines:

- Evidence
- Evidence Construction (offline design; runtime evaluation)
- Evidence Objects
- Evidence Contracts
- Evidence Provenance
- Evidence Quality
- Evidence Lifecycle

This specification does not define:

- inference algorithms
- probability estimation
- market-state estimation
- confidence estimation
- strategy behaviour
- trading signals

---

# 4. Architectural Position

```
Observation Architecture

↓

Evidence Architecture

↓

State Inference Architecture
```

Evidence Architecture is the bridge between observed market facts and market-state inference.

---

# 5. Responsibilities

Evidence Architecture shall:

- evaluate validated evidence-construction rules over Observations;
- construct Evidence Objects deterministically;
- preserve provenance;
- standardize evidence representation;
- evaluate evidence quality;
- expose deterministic Evidence Objects.

Evidence Architecture shall not:

- author or discover evidence-construction rules at runtime;
- engineer features at runtime;
- estimate market state;
- classify markets;
- determine trading regimes;
- generate trading signals.

---

# 6. Definition of Evidence

Evidence is information derived from one or more Observations that supports or contradicts one or more hypotheses regarding latent market properties.

Evidence is neither:

- an Observation;
- an Estimate;
- a Market State;
- a trading signal.

Evidence exists solely to support inference.

---

# 7. Evidence Object

Every Evidence Object shall contain:

- Evidence Identifier
- Source Observation(s)
- Construction Timestamp
- Evidence Type
- Evidence Value
- Artifact Version (the construction rules applied)
- Provenance Metadata
- Quality Metadata
- Version

Evidence Objects are immutable.

---

# 8. Evidence Construction

Evidence shall be produced only from Observations that satisfy MSI-003.

Runtime evidence construction applies only validated, versioned construction rules carried by a Published MSI Artifact; it authors no rules.

Evidence construction shall:

- preserve causality;
- preserve provenance;
- preserve determinism;
- preserve reproducibility.

Given identical Observations and identical artifact-carried construction rules, identical Evidence shall always be produced.

---

# 9. Evidence Provenance

Every Evidence Object shall retain complete lineage.

The following chain shall always be reconstructable:

```
Observation

↓

Evidence

↓

Estimate

↓

Market State

↓

Knowledge
```

Replay shall reconstruct identical Evidence Objects.

---

# 10. Evidence Quality

Evidence Quality describes the reliability of the constructed evidence.

Evidence Quality is distinct from Observation Quality (MSI-003 §8).

Quality dimensions include:

- consistency;
- stability;
- completeness;
- reproducibility;
- traceability.

Evidence quality shall accompany every Evidence Object.

---

# 11. Evidence Lifecycle

Evidence-construction rules follow the lifecycle:

```
Constructed

↓

Validated

↓

Published (as Artifact)

↓

Consumed (runtime evaluation)

↓

Archived
```

Rule authoring, validation, and publication are offline Research; consumption is runtime evaluation. Evidence Objects are immutable once constructed.

---

# 12. Architectural Principles

## MSI-EA-001

Evidence shall always be derived from Observations.

---

## MSI-EA-002

Evidence shall remain deterministic.

---

## MSI-EA-003

Evidence shall preserve complete provenance.

---

## MSI-EA-004

Evidence shall remain independent of inference methodology.

---

## MSI-EA-005

Evidence shall never contain trading intent.

---

# 13. Architectural Decisions

## MSI-4D-01

Evidence-construction rules are designed and validated offline (Research).

Runtime only evaluates validated, artifact-carried rules; it engineers no features and authors no rules.

---

## MSI-4D-02

Evidence Architecture shall remain independent of State Inference.

---

## MSI-4D-03

Evidence Objects shall be immutable and shall support complete replay.

---

## MSI-4D-04

Evidence shall represent interpreted Observations, not inferred Market State.

---

# 14. Consequences

This specification guarantees:

- deterministic evidence generation;
- complete evidence provenance;
- causal correctness;
- replay reproducibility;
- inference independence;
- no runtime feature engineering.

Inference engines may evolve without modifying the Evidence Architecture.

---

# 15. Dependencies

Depends upon:

- MSI-001
- MSI-002
- MSI-003

Required by:

- MSI-005

---

# 16. Status

Current Status:

v1.0

Frozen

---

**End of Document**
