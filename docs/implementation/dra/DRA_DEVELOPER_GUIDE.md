# DRA Developer Guide

**Version:** 1.0  
**Date:** 2026-07-04  
**Architecture Reference:** MSI-001 through MSI-009 (Frozen v1.0)

---

## 1. Overview

The Daily Regime Analyzer (DRA) is the reference implementation of the MSI Runtime Pipeline. At daily cadence, it consumes Platform Observations, evaluates a Published MSI Artifact, and produces deterministic Market Knowledge for trading strategies.

### Architecture

```
DuckDB → Observation → Evidence → Artifact Evaluation → Knowledge → Strategy
```

### Certified Pipeline Components

| Component | Module | Role |
|-----------|--------|------|
| DuckDBObservationReader | `core.msi.dra` | Read Observations from DuckDB |
| FilesystemArtifactLoader | `core.msi.dra` | Load and validate PublishedArtifacts |
| DefaultEvidenceBuilder | `core.msi.dra` | Convert Observations to Evidence |
| DefaultArtifactEvaluator | `core.msi.dra` | Evaluate artifact → MarketState |
| DefaultKnowledgeBuilder | `core.msi.dra` | Build KnowledgeObject |
| DefaultKnowledgePublisher | `core.msi.dra` | Publish Knowledge |
| KnowledgeRepository | `core.msi.dra` | Store/retrieve KnowledgeObjects |
| ProvenanceChain | `core.msi.dra` | Immutable provenance tracking |
| DRAOrchestrator | `core.msi.dra` | Pipeline coordinator |

---

## 2. Setup

### Python Environment

- Python 3.10+
- Dependencies: `duckdb` (for DuckDBObservationReader)

### Import

```python
from core.msi import DRAOrchestrator
from core.msi.dra import (
    DuckDBObservationReader,
    FilesystemArtifactLoader,
    DefaultEvidenceBuilder,
    DefaultArtifactEvaluator,
    DefaultKnowledgeBuilder,
    DefaultKnowledgePublisher,
    KnowledgeRepository,
)
```

---

## 3. Artifact Creation

Published MSI Artifacts are the Research-to-Platform interface (MSI-007). Every artifact must contain:

```
{artifact_directory}/
  metadata.json         # MSI-007 §7 metadata
  evidence_rules.json   # MSI-004 §2 evidence rules
  model.py              # PublishedArtifact implementation
  provenance.json       # MSI-007 §9 provenance
  checksum.sha256        # Content integrity hashes
```

### metadata.json

```json
{
  "artifact_id": "my-artifact",
  "artifact_version": "v1.0.0",
  "schema_version": "1.0",
  "validation_id": "val-my-artifact-v1",
  "publication_timestamp": "2026-07-04T12:00:00",
  "compatibility_version": "1.0",
  "runtime_compatibility": "msi-v1.0",
  "provenance_reference": "prov-my-artifact",
  "supported_runtime_versions": ["msi-v1.0"],
  "supported_ontology_versions": ["1.0"],
  "supported_contract_versions": ["1.0"]
}
```

All three `supported_*_versions` fields are mandatory — the ArtifactLoader uses fail-closed compatibility validation.

### model.py

```python
from core.msi.contracts import ArtifactMetadata, PublishedArtifact, MarketState, Estimate

class MyArtifact(PublishedArtifact):
    metadata = ArtifactMetadata(
        artifact_id="my-artifact",
        artifact_version="v1.0.0",
        schema_version="1.0",
        validation_id="val-my-artifact-v1",
        publication_timestamp=datetime(2026, 7, 4, 12, 0, 0),
        compatibility_version="1.0",
        runtime_compatibility="msi-v1.0",
        provenance_reference="prov-my-artifact",
    )

    def get_evidence_rules(self):
        return {
            "features": [
                {"name": "vix_close", "source": "NSE_INDEX|India VIX",
                 "field": "close", "transform": "identity"},
            ],
            "lookback_days": 90,
            "required_symbols": ["NSE_INDEX|India VIX"],
            "rule_format_version": "1.0",
        }

    def evaluate(self, evidence: Tuple[Evidence, ...]) -> MarketState:
        # implementation-defined — must be deterministic
        return MarketState(
            evaluation_timestamp=evidence[0].construction_timestamp,
            estimates=(Estimate("volatility", 1.0, 0.15, "magnitude"),),
        )
```

### checksum.sha256

Generate with:
```python
import hashlib, json

files = ["metadata.json", "evidence_rules.json", "model.py", "provenance.json"]
per_file = {f: hashlib.sha256(open(f"{dir}/{f}", "rb").read()).hexdigest() for f in files}
combined = hashlib.sha256("".join(per_file[f] for f in files).encode()).hexdigest()
checksum = {"algorithm": "sha256", "files": per_file, "combined_hash": combined}
json.dump(checksum, open(f"{dir}/checksum.sha256", "w"), indent=2)
```

---

## 4. Running the DRA

### Pipeline Execution

```python
from datetime import date
from core.msi.dra import (
    DRAOrchestrator,
    DuckDBObservationReader,
    FilesystemArtifactLoader,
    DefaultEvidenceBuilder,
    DefaultArtifactEvaluator,
    DefaultKnowledgeBuilder,
    DefaultKnowledgePublisher,
    KnowledgeRepository,
)

orchestrator = DRAOrchestrator(
    observation_reader=DuckDBObservationReader(source="data/market_data/nse/candles/1d/"),
    evidence_builder=DefaultEvidenceBuilder(),
    artifact_loader=FilesystemArtifactLoader(),
    artifact_evaluator=DefaultArtifactEvaluator(),
    knowledge_builder=DefaultKnowledgeBuilder(),
    knowledge_publisher=DefaultKnowledgePublisher(KnowledgeRepository()),
)

knowledge = orchestrator.run(
    evaluation_date=date(2026, 7, 4),
    artifact_ref="data/msi/artifacts/my-artifact/v1.0.0/",
)
print(knowledge.knowledge_id)
```

### Pipeline Flow

1. ArtifactLoader loads and validates the artifact (checksums, compatibility, lifecycle)
2. Required symbols extracted from artifact evidence rules
3. ObservationReader reads observations for those symbols
4. EvidenceBuilder applies artifact rules to observations
5. ArtifactEvaluator calls `artifact.evaluate(evidence)` with contract validation
6. KnowledgeBuilder constructs KnowledgeObject with deterministic SHA-256 ID
7. KnowledgePublisher persists the KnowledgeObject
8. KnowledgeObject returned to caller

### Error Handling

All errors are typed DRA exceptions:
- `ArtifactLoadError` — artifact not found, incompatible, or invalid
- `ObservationReadError` — required data unavailable
- `EvidenceConstructionError` — rules cannot be applied
- `EvaluationError` — artifact evaluation failed
- `KnowledgePublishError` — publication failed

Errors propagate naturally through the orchestrator — no swallowing, no partial state.

---

## 5. Testing

### Test Suite

```bash
python -m pytest tests/msi/ -v          # Full MSI suite (283 tests)
python -m pytest tests/msi/ -q          # Compact output
```

### Test Architecture

Tests are organized by milestone:

| File | Milestone | Tests | Focus |
|------|-----------|-------|-------|
| `test_contracts.py` | M0 | 17 | DTO immutability, MSI compliance |
| `test_interfaces.py` | M0 | 25 | ABC inheritance, abstract methods |
| `test_m1_artifact.py` | M1 | 83 | Reference test artifact |
| `test_artifact_loader.py` | M2 | 37 | Artifact loading and validation |
| `test_observation_reader.py` | M3 | 21 | DuckDB observation reading |
| `test_evidence_builder.py` | M4 | 22 | Evidence construction |
| `test_artifact_evaluator.py` | M5 | 11 | Artifact evaluation |
| `test_knowledge_builder.py` | M5 | 14 | Knowledge construction |
| `test_provenance.py` | M5 | 12 | Provenance chain |
| `test_knowledge_repository.py` | M6 | 14 | Knowledge storage |
| `test_knowledge_publisher.py` | M6 | 12 | Knowledge publication |
| `test_orchestrator.py` | M7 | 10 | Pipeline integration |
| `test_replay.py` | M8 | 5 | Deterministic replay |

### Reuse Fixtures

`tests/msi/conftest.py` provides session-scoped fixtures:
- `test_artifact_path` — path to the M1 reference artifact
- `reference_test_artifact` — loaded M1 PublishedArtifact
- `sample_observations` — 2 sample Observation DTOs
- `sample_evidence` — 2 sample Evidence DTOs
- `sample_evidence_high_vix` / `sample_evidence_low_vix` / `sample_evidence_empty`

---

## 6. Replay Verification

The DRA pipeline is deterministic. Identical inputs produce identical outputs across processes:

```python
# Run twice — identical knowledge_id
o1 = DRAOrchestrator(...).run(date(2026, 7, 4), artifact_ref)
o2 = DRAOrchestrator(...).run(date(2026, 7, 4), artifact_ref)
assert o1.knowledge_id == o2.knowledge_id
```

Replay guarantees verified in `tests/msi/test_replay.py`:
- 3 consecutive runs → identical knowledge_id
- Cross-orchestrator-instance consistency
- Point-in-time isolation (T data ≠ T+1 data)
- Subset data equivalence

---

## 7. Provenance

Every KnowledgeObject carries a complete provenance chain (MSI-005 §14):

```
Observation IDs → Evidence IDs → Artifact ID/Version → Knowledge ID
```

The `ProvenanceChain` is immutable and supports:
- `reconstruct()` — returns a complete audit record
- `verify()` — checks internal consistency

---

## 8. Deterministic IDs

All pipeline IDs are deterministic SHA-256 hex digests:

| ID Type | Hash Components |
|---------|-----------------|
| Evidence ID | `artifact_version \| evidence_type \| source_ids \| value` |
| Knowledge ID | `artifact_version \| eval_timestamp \| estimate fields` |

No uuid, random, or object identity contributes to any ID.

---

## 9. Governance

All milestones follow the DRA Implementation Ledger process:
1. Implementation complete → report
2. Independent technical review → PASS / PASS WITH MINOR FIXES / FAIL
3. Fix verification addendum (if needed)
4. Certification → commit + tag (`dra-m0` through `dra-m9`)

Current status: **M0–M9 certified** (DRA v1.0 complete).

---

## References

- MSI Architecture: `docs/architecture/market_state_intelligence/MSI_001_*` through `MSI_009_*`
- DRA Implementation Plan: `docs/implementation/dra/DRA_IMPLEMENTATION_PLAN.md`
- Implementation Ledger: `docs/implementation/dra/IMPLEMENTATION_LEDGER.md`
- Project State: `docs/PROJECT_STATE.md`
