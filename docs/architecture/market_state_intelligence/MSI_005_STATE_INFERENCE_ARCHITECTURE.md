# MSI-005
# Market State Intelligence Architecture
## State Inference Architecture

**Document ID:** MSI-005

**Version:** v1.0

**Status:** Frozen

**Classification:** Governing Architecture Specification

---

# 1. Purpose

This specification defines the architecture responsible for inferring latent Market State from standardized Evidence and exposing it as Knowledge to Platform strategies.

State Inference is the architectural stage that transforms Evidence into Estimates of Latent Variables (Market State), while preserving determinism, causality, provenance, and complete replay.

MSI-005 owns two faces of a single contract:

- the research-facing **Inference Contract** that a Published MSI Artifact must satisfy;
- the platform-facing **runtime artifact-evaluation engine** that evaluates a conforming artifact to produce Knowledge.

Knowledge is the output object of the inference architecture. It is not a separate architectural layer.

This specification governs how latent Market State is inferred.

It intentionally remains independent of any particular inference methodology.

---

# 2. Relationship to Previous Specifications

MSI-001 defines the governing principles.

MSI-002 defines the ontology.

MSI-003 defines Observations.

MSI-004 defines Evidence.

MSI-005 defines how latent Market State is inferred from Evidence and exposed as Knowledge.

MSI-006 defines validation of inference.

MSI-007 defines the internal structure of the Published MSI Artifact.

---

# 3. Scope

This specification defines:

- Inference Interfaces
- Inference Contract
- Confidence Estimation
- Uncertainty Representation
- Knowledge Construction
- Runtime Artifact Evaluation
- Runtime Provenance
- Runtime Determinism
- Model Independence

This specification does not define:

- model training
- optimisation
- feature engineering
- statistical methods
- machine learning
- the internal structure of the Published MSI Artifact (MSI-007)
- validation methodology (MSI-006)
- trading decisions
- execution

---

# 4. Architectural Position

The MSI Architecture describes two pipelines that share the Observation and Evidence spine.

```
Research:  Observation → Evidence → Inference → Validation → Artifact

Runtime:   Observation → Evidence → Artifact Evaluation → Knowledge → Strategy → SignalSource
```

State Inference is the stage at which Evidence becomes Estimates of Market State.

In the Research pipeline, inference produces a candidate that Validation gates and that is sealed into a Published MSI Artifact.

In the Runtime pipeline, the artifact-evaluation engine evaluates a conforming artifact against Evidence to produce Knowledge.

Strategies remain solely responsible for producing trading signals.

---

# 5. The Two Faces of State Inference

MSI-005 defines one Inference Contract honoured from both sides.

- **Research produces** artifacts that conform to the Inference Contract.
- **Runtime evaluates** artifacts that conform to the Inference Contract.

The Inference Contract is the pivot between Research and Platform. The Published MSI Artifact is the only object that crosses the boundary (MSI-002 MSI-OD-003).

The two faces shall remain distinct within this specification. The research-facing contract defines what an artifact must express. The runtime engine defines how a conforming artifact is deterministically evaluated. Neither face may absorb the responsibilities of the other.

---

# 6. Responsibilities

State Inference shall:

- define the Inference Contract that Published MSI Artifacts satisfy;
- evaluate Published MSI Artifacts at runtime;
- consume Evidence Objects;
- produce Estimates of Latent Variables composing Market State;
- construct Knowledge Objects from Market State;
- represent uncertainty on every Estimate;
- preserve provenance;
- preserve replay;
- expose Knowledge through Platform interfaces.

State Inference shall not:

- train models;
- optimise parameters;
- engineer features;
- define the internal structure of the artifact (MSI-007);
- define validation methodology (MSI-006);
- modify Published MSI Artifacts;
- generate trading signals.

---

# 7. Runtime Inputs

The runtime artifact-evaluation engine shall consume only:

- Evidence Objects;
- Published MSI Artifact;
- deterministic runtime configuration.

It shall never consume:

- research notebooks;
- experimental models;
- training datasets;
- optimisation results.

Runtime shall evaluate only approved artifacts.

---

# 8. Inference Contract

The Inference Contract defines the interface between Evidence and Market State that every Published MSI Artifact shall satisfy.

The Inference Contract specifies:

- the Evidence a conforming artifact consumes;
- the Estimates a conforming artifact produces;
- that every Estimate carries a value and its own quantified uncertainty (MSI-002 MSI-OD-005);
- that Market State is the multidimensional collection of those Estimates (MSI-002 MSI-OD-001);
- point-in-time and causal evaluation semantics.

The Inference Contract is methodology independent. Any inference method whose output conforms to the contract is admissible. The contract constrains the shape of inference, never its technique.

---

# 9. Published MSI Artifact

A Published MSI Artifact is the only Research object permitted to execute within Platform runtime.

The artifact's metadata contract is defined and owned by MSI-007. This specification does not re-enumerate it.

At runtime the evaluation engine binds on:

- Artifact Identifier
- Artifact Version
- Validation Identifier
- Runtime Compatibility

The **Validation Identifier** is owned by MSI-006. This specification treats it as an opaque reference to the validation record that approved the artifact.

The **internal structure** of the artifact is defined by MSI-007.

---

# 10. Market State and Estimates

Market State is the multidimensional collection of Estimates of Latent Variables (MSI-002 §4.8).

Every Estimate carries both a value and a quantified uncertainty (MSI-002 §4.7, MSI-OD-005).

Every dimension of Market State carries its own uncertainty.

Market State shall never be reduced to a single categorical label or a single scalar (MSI-002 MSI-OD-001).

---

# 11. Knowledge Object

Knowledge is the runtime-exposed representation of Market State (MSI-002 §4.9). The Knowledge Object is the output of State Inference.

Every Knowledge Object shall contain:

- Knowledge Identifier
- Evaluation Timestamp
- Artifact Version
- Runtime Version
- Market State
- Provenance Reference

Market State within the Knowledge Object is the collection of Estimates, each carrying its own value and uncertainty. Uncertainty reaches strategies by the Knowledge Object containing Market State, at the per-dimension granularity the ontology requires.

The Knowledge Object shall not carry a standalone scalar Confidence or Uncertainty. Such a field would flatten multidimensional uncertainty (MSI-OD-001) and duplicate a responsibility already assigned to the Estimate (MSI-OP-002).

Knowledge Objects are immutable.

Knowledge Objects represent the only MSI output exposed to strategies.

---

# 12. Confidence and Uncertainty Representation

Uncertainty is intrinsic to every Estimate and is represented per-dimension within Market State.

Confidence Estimation is an inference activity — the quantification of uncertainty during inference. It is legitimate scope of this specification.

Confidence Estimation does not license a standalone Confidence property on the Knowledge Object. If an aggregate confidence is ever required, it shall be defined in MSI-002 first, as an explicitly derived projection of per-Estimate uncertainties, and never as a co-equal primary field (MSI-OP-004).

---

# 13. Runtime Evaluation

Runtime evaluation shall satisfy:

- deterministic execution;
- point-in-time correctness;
- causal evaluation;
- reproducibility;
- replay compatibility.

Given identical:

- Evidence;
- Published MSI Artifact;
- runtime configuration;

State Inference shall produce identical Knowledge Objects.

---

# 14. Provenance

Every Knowledge Object shall retain complete lineage.

```
Observation

↓

Evidence

↓

Published MSI Artifact

↓

Knowledge
```

Replay shall reconstruct identical Knowledge Objects.

---

# 15. Runtime Constraints

Runtime artifact evaluation shall never perform:

- online learning;
- parameter optimisation;
- feature engineering;
- adaptive behaviour;
- runtime experimentation.

Runtime remains a deterministic evaluation engine.

---

# 16. Model Independence

The Inference Contract and the runtime evaluation engine are independent of any statistical, mathematical, or machine learning methodology.

Any artifact conforming to the Inference Contract is admissible.

Future inference methods may replace one another without architectural modification, provided their output conforms to the contract.

---

# 17. Architectural Principles

## MSI-SI-001

Market State shall be inferred, never observed.

---

## MSI-SI-002

Every Estimate shall carry quantified uncertainty; Knowledge exposes uncertainty through Market State.

---

## MSI-SI-003

Knowledge shall be deterministic and reproducible.

---

## MSI-SI-004

Knowledge shall preserve complete provenance.

---

## MSI-SI-005

The Inference Contract shall remain independent of inference methodology.

---

## MSI-SI-006

Strategies consume Knowledge.

Strategies never consume Estimates, Evidence, or Observations.

---

# 18. Architectural Decisions

## MSI-5D-01

MSI-005 owns both the research-facing Inference Contract and the runtime artifact-evaluation engine. Knowledge is the output object of the inference architecture, not a separate layer.

---

## MSI-5D-02

Published MSI Artifacts shall be the only executable Research objects permitted in Platform runtime.

---

## MSI-5D-03

Knowledge Objects shall remain immutable and shall carry no standalone scalar Confidence or Uncertainty; uncertainty is carried per-Estimate within Market State.

---

## MSI-5D-04

State Inference shall preserve deterministic replay.

---

## MSI-5D-05

The internal structure of the Published MSI Artifact is deferred to MSI-007. This specification defines only the runtime binding metadata and reconciles with MSI-007.

---

## MSI-5D-06

State Inference shall expose only Knowledge through Platform interfaces. Implementation details remain encapsulated.

---

# 19. Consequences

This architecture guarantees:

- deterministic runtime behaviour;
- artifact version pinning;
- complete replay;
- reproducible Knowledge;
- separation of Research from Platform runtime;
- independence from inference methodology;
- a single Inference Contract honoured by both the Research and Runtime pipelines.

Future inference engines may replace one another without requiring architectural modification.

---

# 20. Dependencies

Depends upon:

- MSI-001
- MSI-002
- MSI-003
- MSI-004

Required by:

- MSI-006

---

# 21. Status

Current Status:

v1.0

Frozen

---

**End of Document**