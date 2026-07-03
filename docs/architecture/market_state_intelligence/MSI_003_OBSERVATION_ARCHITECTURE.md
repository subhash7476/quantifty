# MSI-003
# Market State Intelligence Architecture
## Observation Architecture

**Document ID:** MSI-003

**Version:** v1.0

**Status:** Frozen

**Classification:** Governing Architecture Specification

---

# 1. Purpose

This specification defines how Market State Intelligence obtains Observations: as a read-only view over the Platform's already-persisted, point-in-time market-data facts.

MSI does not acquire, source, or store market data. The Platform owns data acquisition and storage. MSI-003 defines the Observation contract and canonical standardisation through which downstream MSI architecture reads those facts.

The Observation layer is the entry point of runtime Market State Intelligence. It performs no interpretation, no evidence generation, and no inference.

---

# 2. Relationship to Platform Data Infrastructure

Data acquisition and persistence are existing Platform responsibilities. The Platform already acquires and stores market-data facts through:

- market-data and broker adapters (`core/data/`, `core/brokers/`);
- the canonical instrument master (`core/instruments/`);
- immutable DuckDB market-data stores (1m candles, daily intermarket, option chains).

MSI-003 introduces no parallel acquisition, ingestion, or storage subsystem. In MSI terms, the Platform's persisted point-in-time market-data facts **are** the Observations. This specification defines only the read-contract and canonical standardisation over them.

This is consistent with MSI-001 `MSI-CD-004` (Runtime MSI is demand-driven; no speculative platform abstractions) and the Platform principle *Analytics Produce Facts — runtime is read-only.*

---

# 3. Scope

This specification defines:

- the Observation read-contract;
- Observation standardisation;
- Observation metadata and provenance references;
- Observation integrity guarantees.

This specification does not define:

- data acquisition (Platform-owned);
- data storage (Platform-owned);
- Evidence, Features, Indicators;
- Inference or Market State;
- Strategies.

---

# 4. Responsibilities

The Observation layer shall:

- read persisted market-data facts from the Platform;
- present them as canonical, immutable Observations;
- preserve point-in-time correctness;
- carry through Platform provenance;
- expose Observations to downstream MSI architecture.

The Observation layer shall not:

- acquire or source market data;
- store or persist market data independently;
- interpret observations;
- engineer features;
- infer latent variables or estimate Market State;
- produce trading signals.

---

# 5. Observation Contract

Every Observation exposed to MSI shall carry:

- Observation Identifier;
- Timestamp (point-in-time);
- Instrument Identifier (canonical);
- Source Reference (Platform-recorded);
- Observable Type;
- Measured Value;
- Measurement Units;
- Provenance Reference (to Platform-recorded provenance);
- Quality Metadata.

Instrument and source identity resolve through the existing canonical instrument master. Observation provenance **references** the Platform's recorded provenance rather than duplicating it.

Observation objects are immutable.

---

# 6. Point-in-Time Principle

Every Observation shall represent only information available at its recorded timestamp.

The Observation layer shall never introduce future information.

Because Observations are read from the Platform's immutable stored facts, historical replay reproduces identical Observation streams by construction.

---

# 7. Provenance

Every Observation shall retain complete provenance, referencing the Platform's recorded provenance for:

- acquisition source;
- acquisition timestamp;
- original timestamp;
- collection mechanism;
- schema version.

Provenance shall remain attached throughout the MSI pipeline.

---

# 8. Quality

Observation quality describes measurement-process quality — the fidelity of the recorded measurement.

It is distinct from Estimate uncertainty (MSI-002 §4.7) and from evidence quality (defined in MSI-004). Observation quality is not evidence and shall remain separate from evidence quality.

Quality dimensions include:

- completeness;
- validity;
- consistency;
- timeliness;
- precision.

---

# 9. Observation Integrity

Observations are immutable once read into MSI.

Corrections to underlying data are represented as new Observations, never mutations of existing ones — mirroring the Platform's immutable market-data store.

---

# 10. Architectural Principles

## MSI-OA-001

The Observation layer performs no interpretation.

---

## MSI-OA-002

The Observation layer is deterministic.

Determinism derives from reading the Platform's immutable stored facts, not from re-acquiring live data.

---

## MSI-OA-003

The Observation layer preserves Platform provenance.

---

## MSI-OA-004

The Observation layer preserves point-in-time correctness.

---

## MSI-OA-005

The Observation layer preserves immutability.

---

# 11. Architectural Decisions

## MSI-3D-01

The Observation layer reads Platform-persisted market-data facts.

It introduces no acquisition, ingestion, or storage subsystem.

---

## MSI-3D-02

Determinism and complete replay derive from the Platform's immutable stored facts.

---

## MSI-3D-03

The Observation layer remains provider-independent, inheriting provider independence from the Platform data layer.

---

# 12. Consequences

This specification guarantees:

- deterministic replay (via the Platform's immutable store);
- reproducible Observation streams;
- provider independence;
- complete provenance;
- causal correctness;
- no duplication of Platform data infrastructure.

All downstream MSI specifications shall consume Observations defined by this specification.

---

# 13. Dependencies

Depends upon:

- MSI-001
- MSI-002

Required by:

- MSI-004

---

# 14. Status

Current Status:

v1.0

Frozen

---

**End of Document**
