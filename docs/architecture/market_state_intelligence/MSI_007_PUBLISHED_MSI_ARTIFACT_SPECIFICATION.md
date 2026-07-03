# MSI-007
# Market State Intelligence Architecture
## Published MSI Artifact Specification

**Document ID:** MSI-007

**Version:** v1.0

**Status:** Frozen

**Classification:** Governing Architecture Specification

---

# 1. Purpose

This specification defines the Published MSI Artifact.

The Published MSI Artifact is the sole architectural interface between the Research domain and the Platform runtime.

It represents the only research output permitted to execute within deterministic Platform runtime.

This specification defines the architectural contract of the Published MSI Artifact.

It does not prescribe its physical serialization.

---

# 2. Relationship to Previous Specifications

MSI-001 establishes the governing principles.

MSI-002 defines the Market Ontology.

MSI-003 defines Observations.

MSI-004 defines Evidence.

MSI-005 defines the State Inference Contract.

MSI-006 defines Validation.

MSI-007 defines the runtime artifact implementing the approved inference contract.

---

# 3. Scope

This specification defines:

- Published MSI Artifact
- Artifact Contract
- Artifact Identity
- Artifact Metadata
- Artifact Compatibility
- Artifact Provenance
- Artifact Immutability
- Publication Event

This specification does not define:

- research methodology
- inference algorithms
- validation methodology
- runtime execution
- deployment governance

---

# 4. Architectural Role

The Published MSI Artifact forms the constitutional boundary between Research and Platform.

```
Research

↓

Validation

↓

Published MSI Artifact

==========================

Platform Runtime

↓

State Inference

↓

Strategy
```

No research object may enter Platform runtime except through a Published MSI Artifact.

---

# 5. Artifact Principles

## MSI-AP-701

Every Published MSI Artifact is immutable.

---

## MSI-AP-702

Every Published MSI Artifact is versioned.

---

## MSI-AP-703

Every Published MSI Artifact is traceable.

---

## MSI-AP-704

Every Published MSI Artifact is reproducible.

---

## MSI-AP-705

Every Published MSI Artifact is deterministic.

---

# 6. Artifact Identity

Every Published MSI Artifact shall possess a unique identity.

Identity shall remain constant throughout the lifetime of the artifact.

Artifact identity shall never be reused.

---

# 7. Artifact Metadata

Every Published MSI Artifact shall expose runtime binding metadata including:

- Artifact Identifier
- Artifact Version
- Schema Version
- Validation Identifier
- Publication Timestamp
- Compatibility Version
- Runtime Compatibility
- Provenance Reference

The Validation Identifier is owned by MSI-006 and is carried here as an opaque reference (MSI-6D-05).

The internal representation of the artifact is implementation-defined.

---

# 8. Artifact Compatibility

Every artifact shall declare:

- supported runtime version(s);
- supported ontology version(s);
- supported inference contract version(s).

Runtime shall reject incompatible artifacts.

---

# 9. Artifact Provenance

Every Published MSI Artifact shall retain complete provenance linking:

- originating research;
- Validation Identifier;
- inference contract version;
- ontology version;
- publication event.

Artifact provenance shall be immutable.

---

# 10. Artifact Immutability

Published MSI Artifacts shall never be modified.

Changes require publication of a new artifact version.

Historical artifacts remain permanently reproducible.

---

# 11. Artifact Contract

Runtime shall treat every Published MSI Artifact as an opaque executable object.

Runtime depends only upon:

- artifact metadata;
- inference contract;
- runtime compatibility.

Runtime shall never inspect implementation-specific internals.

---

# 12. Publication and Lifecycle Ownership

Publication is the event at which an approved candidate becomes a Published MSI Artifact: its identity is minted, its metadata is sealed, and its provenance is frozen. This specification owns the publication event.

The artifact lifecycle — candidacy, validation, promotion, consumption, and retirement — is owned entirely by MSI-008 Artifact Governance. This specification defines no artifact lifecycle states or transitions.

An artifact's lifecycle state is a mutable governance annotation maintained outside the immutable artifact.

---

# 13. Runtime Binding

Runtime shall bind a Published MSI Artifact using:

- Artifact Identifier;
- Artifact Version;
- Validation Identifier;
- Runtime Compatibility.

Successful binding establishes deterministic execution.

---

# 14. Architectural Decisions

## MSI-7D-01

Published MSI Artifacts are the only executable research objects permitted within Platform runtime.

---

## MSI-7D-02

Runtime shall treat artifact internals as opaque.

---

## MSI-7D-03

Artifact metadata constitutes the runtime binding contract.

---

## MSI-7D-04

Artifact immutability is mandatory.

---

## MSI-7D-05

Every runtime execution shall identify the exact Published MSI Artifact used.

---

# 15. Consequences

This specification guarantees:

- deterministic runtime execution;
- complete provenance;
- artifact reproducibility;
- immutable deployment history;
- separation of Research and Platform.

---

# 16. Dependencies

Depends upon:

- MSI-001
- MSI-002
- MSI-003
- MSI-004
- MSI-005
- MSI-006

Required by:

- MSI-008

---

# 17. Status

Current Status:

v1.0

Frozen

---

**End of Document**
