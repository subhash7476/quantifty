# MSI Engine Development Guide

**Target Platform:** MSI v1.0 (certified, tag `msi-v1.0-certified`)

**Version:** 1.0

**Date:** 2026-07-04

---

## 1. Overview

This guide describes how to build a new Market State Intelligence (MSI) Engine targeting the MSI v1.0 Platform. An MSI Engine is a deterministic runtime pipeline that consumes Platform Observations, evaluates a Published MSI Artifact, and produces Market Knowledge for strategies.

The Daily Regime Analyzer (DRA) is the certified reference implementation. Every new engine follows the same architecture, contracts, and governance process.

---

## 2. Architecture

### Two-Pipeline Model

```
Research Pipeline            Runtime Pipeline
─────────────────            ────────────────
Observation                   Observation ←──── DuckDB
    │                              │
Evidence                        Evidence ←──── Artifact Rules
    │                              │
Inference                       Artifact.evaluate()
    │                              │
Validation                      MarketState
    │                              │
Published Artifact ──────────→ KnowledgeObject ──→ Strategy
```

**Shared spine:** Observation and Evidence are identical in both pipelines (MSI-003, MSI-004). This prevents train/serve skew.

**Research lives outside the platform repo.** The Published MSI Artifact is the sole Research→Platform interface (MSI-007).

### Runtime Architecture

Every MSI engine decomposes into six stateless components:

```
DRAOrchestrator (stateless coordinator)
  ├── ObservationReader   — Platform data → Observations
  ├── ArtifactLoader      — Artifact path → PublishedArtifact
  ├── EvidenceBuilder     — Observations + Rules → Evidence
  ├── ArtifactEvaluator   — Evidence + Artifact → MarketState
  ├── KnowledgeBuilder    — MarketState + Provenance → KnowledgeObject
  └── KnowledgePublisher  — KnowledgeObject → Storage
```

---

## 3. Prerequisites

### Required Contracts (from M0)

Every engine MUST use the certified frozen DTOs:

```python
from core.msi.contracts import (
    Observation,       # MSI-003 §5
    Evidence,          # MSI-004 §7
    Estimate,          # MSI-002 §4.7
    MarketState,       # MSI-002 §4.8
    KnowledgeObject,   # MSI-005 §11
    PublishedArtifact, # MSI-007 §11 (ArtifactMetadata + ABC)
)
```

### Required Interfaces (from M0)

Every engine MUST implement the certified ABCs:

```python
from core.msi.interfaces import (
    ObservationReader,     # read(date, symbols) -> tuple[Observation, ...]
    EvidenceBuilder,       # build(observations, artifact) -> tuple[Evidence, ...]
    ArtifactLoader,        # load(artifact_ref) -> PublishedArtifact
    ArtifactEvaluator,     # evaluate(evidence, artifact) -> MarketState
    KnowledgeBuilder,      # build(ms, artifact, chain) -> KnowledgeObject
    KnowledgePublisher,    # publish(knowledge), get_knowledge(date), get_latest()
)
```

### Required Error Hierarchy (from M2)

```python
from core.msi.dra.errors import (
    DRAError, ObservationReadError, ArtifactLoadError, ArtifactNotFoundError,
    ArtifactIncompatibleError, ArtifactNotActiveError, ArtifactNotValidatedError,
    ArtifactIntegrityError, EvidenceConstructionError, EvaluationError,
    KnowledgeBuildError, KnowledgePublishError, KnowledgeRepositoryError,
)
```

---

## 4. Development Process

### M0 — Contracts (required for all engines)

No engine-specific work. All engines share the certified contracts and interfaces.

### M1 — Test Artifact

Create a minimal Published MSI Artifact for pipeline testing:

```
tests/{engine}/fixtures/test_artifact/
  metadata.json, evidence_rules.json, model.py, provenance.json, checksum.sha256
```

Use the DRA M1 artifact as a template.

### M2 — Artifact Loader

Implement `ArtifactLoader`. Reference: `core/msi/dra/filesystem_artifact_loader.py`.

Requirements:
- Validate metadata (8 MSI-007 §7 fields)
- Fail-closed compatibility (supported_*_versions must be present)
- Verify checksum integrity (per-file SHA-256 + combined hash)
- Safe model import via `importlib.util`
- Return opaque PublishedArtifact handle

### M3 — Observation Reader

Implement `ObservationReader`. Reference: `core/msi/dra/duckdb_observation_reader.py`.

Requirements:
- Read from platform-persisted market data
- Produce point-in-time correct, chronologically ordered Observations
- Deterministic observation IDs (SHA-256 content hash)
- Symbol-existence pre-check

### M4 — Evidence Builder

Implement `EvidenceBuilder`. Reference: `core/msi/dra/default_evidence_builder.py`.

Requirements:
- Rules obtained exclusively through `artifact.get_evidence_rules()`
- Point-in-time: observations limited to evaluation boundary
- Deterministic evidence IDs (SHA-256)
- No artifact internal inspection

### M5 — Evaluator + Knowledge Builder

Implement `ArtifactEvaluator`. Reference: `core/msi/dra/default_artifact_evaluator.py`.

Requirements:
- Call `artifact.evaluate(evidence)` only
- Validate MarketState contract (every Estimate has 4 fields, uncertainty >= 0)
- Raise `EvaluationError` on contract violation

Implement `KnowledgeBuilder`. Reference: `core/msi/dra/default_knowledge_builder.py`.

Requirements:
- Deterministic knowledge_id (SHA-256 of artifact_version + eval_timestamp + estimate fields)
- No scalar confidence/uncertainty (MSI-5D-03)
- Preserve provenance chain

### M6 — Knowledge Publisher

Implement `KnowledgePublisher`. Reference: `core/msi/dra/default_knowledge_publisher.py`.

Requirements:
- Store KnowledgeObjects with duplicate detection
- Support `get_knowledge(date)` and `get_latest()`
- Publish → load → bit-identical roundtrip

### M7 — Orchestrator

Implement the pipeline coordinator. Reference: `core/msi/dra/orchestrator.py`.

Requirements:
- Wire all 6 components in MSI-009 §5 order
- Natural error propagation (no swallowing)
- No partial state on failure
- Construct ProvenanceChain from pipeline outputs

### M8 — Replay Verification

Prove deterministic replay. Reference: `tests/msi/test_replay.py`.

Requirements:
- 3 consecutive runs → identical knowledge_id
- Roundtrip consistency across instances
- Point-in-time isolation
- Subset data equivalence

### M9 — Documentation

No engine-specific code. Update public API exports and write an engine developer guide.

---

## 5. Determinism Requirements

Every engine MUST satisfy:

| Contract | Requirement |
|----------|-------------|
| Evidence IDs | SHA-256 of `artifact_version|evidence_type|source_ids|value` |
| Knowledge IDs | SHA-256 of `artifact_version|eval_timestamp|estimate_fields` |
| Pipeline output | Identical inputs → identical KnowledgeObject |
| No random/uuid | All IDs are content-hash derived |
| No wall-clock time | All timestamps from observations or artifact metadata |

---

## 6. Testing

Every engine MUST pass:

- Contract tests (DTO immutability, MSI compliance)
- Interface tests (ABC conformance)
- Component unit tests (each M2–M6 component in isolation)
- Orchestrator integration tests (M7, full pipeline)
- Replay verification tests (M8, determinism proof)
- Existing DRA tests (regression safety)

Minimum test pattern:

```
tests/{engine}/
  conftest.py               # Engine-specific fixtures
  test_artifact_loader.py
  test_observation_reader.py
  test_evidence_builder.py
  test_artifact_evaluator.py
  test_knowledge_builder.py
  test_knowledge_publisher.py
  test_orchestrator.py
  test_replay.py
```

---

## 7. Governance

Every engine MUST:

1. Follow the DRA Implementation Plan structure (milestones M0–M9)
2. Register in the Implementation Ledger
3. Pass independent technical review
4. Obtain certification (PASS / PASS WITH MINOR FIXES / FAIL)
5. Tag certified commits (`{engine}-m0` through `{engine}-m9`)
6. Provide a developer guide and authoring template

---

## 8. Example: Minimum Viable Engine

The smallest possible engine:

```python
from core.msi.dra import FilesystemArtifactLoader, DefaultEvidenceBuilder
from core.msi.dra import DefaultArtifactEvaluator, DefaultKnowledgeBuilder
from core.msi.dra import DefaultKnowledgePublisher, KnowledgeRepository
from core.msi.dra import DRAOrchestrator, ProvenanceChain
from my_engine import MyObservationReader

orchestrator = DRAOrchestrator(
    observation_reader=MyObservationReader(),    # Engine-specific
    evidence_builder=DefaultEvidenceBuilder(),    # Reuse
    artifact_loader=FilesystemArtifactLoader(),   # Reuse
    artifact_evaluator=DefaultArtifactEvaluator(), # Reuse
    knowledge_builder=DefaultKnowledgeBuilder(),   # Reuse
    knowledge_publisher=DefaultKnowledgePublisher(KnowledgeRepository()),  # Reuse
)
```

Most engines only need a custom `ObservationReader` and a custom `PublishedArtifact`. All other components reuse the certified DRA implementations.

---

## References

- MSI Architecture: `docs/architecture/market_state_intelligence/MSI_001_*`
- DRA Implementation Plan: `docs/implementation/dra/DRA_IMPLEMENTATION_PLAN.md`
- DRA Developer Guide: `docs/implementation/dra/DRA_DEVELOPER_GUIDE.md`
- Engine Certification Checklist: `docs/implementation/dra/ENGINE_CERTIFICATION_CHECKLIST.md`
- Engine Authoring Template: `docs/implementation/dra/ENGINE_AUTHORING_TEMPLATE.md`
- Implementation Ledger: `docs/implementation/dra/IMPLEMENTATION_LEDGER.md`
