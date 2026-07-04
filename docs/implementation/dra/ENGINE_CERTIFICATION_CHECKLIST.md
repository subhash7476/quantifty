# MSI Engine Certification Checklist

**Target Platform:** MSI v1.0 (certified, tag `msi-v1.0-certified`)

Every new MSI engine must satisfy every item on this checklist before certification.

---

## Architecture Compliance

- [ ] Engine targets MSI v1.0 architecture (MSI-001 through MSI-009)
- [ ] Engine uses certified M0 frozen DTOs (`Observation`, `Evidence`, `Estimate`, `MarketState`, `KnowledgeObject`, `PublishedArtifact`)
- [ ] Engine uses certified M0 ABCs (`ObservationReader`, `EvidenceBuilder`, `ArtifactLoader`, `ArtifactEvaluator`, `KnowledgeBuilder`, `KnowledgePublisher`)
- [ ] Engine uses certified M2 error hierarchy (`DRAError` and all subclasses)
- [ ] No architectural concepts introduced beyond MSI-001 through MSI-009

---

## Component Certification

### M0 — Contracts & Interfaces
- [ ] All DTOs are `@dataclass(frozen=True)` and immutable
- [ ] All interfaces are ABCs with abstract methods only
- [ ] Contract tests pass (immutability, MSI compliance, ABC conformance)

### M1 — Test Artifact
- [ ] `metadata.json` has all 8 MSI-007 §7 fields
- [ ] `evidence_rules.json` is valid and deterministic
- [ ] `model.py` implements `PublishedArtifact` with `get_evidence_rules()` and `evaluate()`
- [ ] `provenance.json` covers all MSI-007 §9 dimensions
- [ ] `checksum.sha256` is valid (per-file + combined hash)
- [ ] Artifact evaluate() returns valid MarketState
- [ ] Artifact is deterministic (same input → same output)

### M2 — Artifact Loader
- [ ] Loads valid artifact → returns PublishedArtifact handle
- [ ] Validates metadata structure (8 MSI-007 §7 fields)
- [ ] Fail-closed compatibility (absent `supported_*_versions` → reject)
- [ ] Checksum integrity verified (per-file + combined)
- [ ] Lifecycle state check (if present, must be Active)
- [ ] Validation status check (if present, must be Approved)
- [ ] All rejections raise typed errors
- [ ] Deterministic loading (same path → same instance)

### M3 — Observation Reader
- [ ] Reads from platform-persisted data
- [ ] Produces point-in-time correct Observations
- [ ] Deterministic observation IDs (SHA-256)
- [ ] Chronological ordering within symbols
- [ ] Symbol-existence pre-check
- [ ] Empty-result handling for no-data dates

### M4 — Evidence Builder
- [ ] Rules obtained exclusively through `artifact.get_evidence_rules()`
- [ ] Point-in-time correctness enforced
- [ ] No look-ahead (future observations excluded)
- [ ] Deterministic evidence IDs (SHA-256)
- [ ] All Evidence DTO fields populated
- [ ] Missing symbols raise `EvidenceConstructionError`

### M5 — Evaluator + Knowledge Builder
- [ ] Calls `artifact.evaluate(evidence)` only
- [ ] Validates MarketState contract (every Estimate has all 4 fields)
- [ ] Uncertainty >= 0 enforced
- [ ] No scalar confidence/uncertainty on KnowledgeObject (MSI-5D-03)
- [ ] Deterministic knowledge_id (SHA-256)
- [ ] Provenance chain preserved

### M6 — Knowledge Publisher
- [ ] Publish → store operation succeeds
- [ ] Roundtrip: publish → load → bit-identical
- [ ] Duplicate knowledge_id rejected
- [ ] `get_knowledge(date)` returns correct KnowledgeObject
- [ ] `get_latest()` returns most recent
- [ ] Empty repository returns None

### M7 — Orchestrator
- [ ] Full pipeline executes: Observation → Evidence → Evaluate → Knowledge → Publish
- [ ] Returns KnowledgeObject
- [ ] Deterministic (same inputs → identical output)
- [ ] Errors propagate naturally (no swallowing)
- [ ] No partial state on failure
- [ ] Pipeline order matches MSI-009 §5

### M8 — Replay Verification
- [ ] 3 consecutive runs → identical knowledge_id
- [ ] Roundtrip consistency across instances
- [ ] Different inputs → different output
- [ ] Point-in-time: T data unavailable at T+1 evaluation, and vice versa
- [ ] Subset data produces equivalent MarketState

### M9 — Documentation
- [ ] Public API exports complete
- [ ] MSI-traceable docstrings on all modules
- [ ] No `import *` or `type: ignore`
- [ ] Engine developer guide written

---

## Determinism

- [ ] No uuid4() in any ID generation
- [ ] No random() in any ID generation
- [ ] No wall-clock timestamps in any ID generation
- [ ] No object identity in any ID generation
- [ ] All IDs are SHA-256 content hashes
- [ ] Identical inputs → bit-identical outputs at every pipeline stage

---

## Governance

- [ ] Implementation plan exists (10 milestones, M0–M9)
- [ ] Implementation ledger created (append-only event log)
- [ ] Independent technical review for each milestone
- [ ] Fix verification addenda where required
- [ ] Certification events recorded
- [ ] All commits tagged (`{engine}-m0` through `{engine}-m9`)

---

## Regression

- [ ] All engine tests pass
- [ ] All existing DRA tests pass (no regression)
- [ ] No architectural violations
- [ ] No scope creep beyond milestone boundaries

---

## Version

**Checklist Version:** 1.0

**Target Platform Version:** MSI v1.0 (`msi-v1.0-certified`)

---

**End of Checklist**
