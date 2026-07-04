# MSI Engine Authoring Template

**Target Platform:** MSI v1.0 (certified, tag `msi-v1.0-certified`)

This template defines the directory structure and governance files for a new MSI Engine targeting the certified v1.0 platform.

---

## Directory Structure

```
core/msi/{engine}/
  __init__.py                           # {EngineName} public API
  {
    engine}_observation_reader.py        # Custom ObservationReader (M3)
  {
    engine}_artifact_loader.py           # Custom ArtifactLoader (M2) — optional
  {
    engine}_evidence_builder.py          # Custom EvidenceBuilder (M4) — optional
  {
    engine}_artifact_evaluator.py        # Custom ArtifactEvaluator (M5) — optional
  {
    engine}_knowledge_builder.py         # Custom KnowledgeBuilder (M5) — optional
  {
    engine}_knowledge_publisher.py       # Custom KnowledgePublisher (M6) — optional
  {
    engine}_orchestrator.py              # Custom Orchestrator (M7) — optional
  errors.py                              # Engine-specific errors (extend DRAError)
  provenance.py                          # Custom provenance — optional

tests/{engine}/
  __init__.py
  conftest.py                            # Engine-specific fixtures
  test_contracts.py                      # M0: DTO immutability
  test_interfaces.py                     # M0: ABC conformance
  test_artifact.py                       # M1: Test artifact validation
  test_artifact_loader.py               # M2: Loader tests
  test_observation_reader.py            # M3: Reader tests
  test_evidence_builder.py              # M4: Builder tests
  test_artifact_evaluator.py            # M5: Evaluator tests
  test_knowledge_builder.py             # M5: Knowledge builder tests
  test_knowledge_publisher.py           # M6: Publisher tests
  test_orchestrator.py                   # M7: Integration tests
  test_replay.py                         # M8: Replay tests
  fixtures/
    test_artifact/                       # M1: Engine test artifact

docs/implementation/{engine}/
  {ENGINE}_IMPLEMENTATION_PLAN.md        # 10-milestone plan (M0–M9)
  IMPLEMENTATION_LEDGER.md              # Append-only event log
  TECHNICAL_REVIEW_TEMPLATE.md          # Review template
  TECHNICAL_REVIEW_GUIDELINES.md        # Review guidelines
  {ENGINE}_DEVELOPER_GUIDE.md           # Engine developer guide
  reports/                              # Per-milestone reports
    M0_IMPLEMENTATION_REPORT.md
    M0_REVIEW.md
    M0_FIX_VERIFICATION_ADDENDUM.md    # If PASS WITH MINOR FIXES
    M0_CERTIFICATION.md
    ...                                 # Repeat for M1–M9
```

---

## Minimum Viable Engine

Most engines only need:

| Component | Reuse or Custom? |
|-----------|-----------------|
| ObservationReader | Custom (reads from different source/cadence) |
| ArtifactLoader | Reuse `FilesystemArtifactLoader` |
| EvidenceBuilder | Reuse `DefaultEvidenceBuilder` |
| ArtifactEvaluator | Reuse `DefaultArtifactEvaluator` |
| KnowledgeBuilder | Reuse `DefaultKnowledgeBuilder` |
| KnowledgePublisher | Reuse `DefaultKnowledgePublisher` |
| Orchestrator | Reuse `DRAOrchestrator` |
| PublishedArtifact | Custom (different model/logic) |

**Files needed for a minimum viable engine:**

1. `core/msi/{engine}/{engine}_observation_reader.py` — custom reader
2. `tests/{engine}/fixtures/test_artifact/` — engine test artifact
3. `tests/{engine}/test_observation_reader.py` — reader tests
4. `tests/{engine}/test_orchestrator.py` — integration tests
5. `docs/implementation/{engine}/{ENGINE}_IMPLEMENTATION_PLAN.md`

---

## Example: engine/\_\_init\_\_.py

```python
"""
{EngineName} — MSI Engine (MSI-009).

Targets MSI v1.0 platform (tag: msi-v1.0-certified).

Components:
  {Engine}ObservationReader — MSI-003 §4
  ... (reused from core.msi.dra for other components)
"""

from .{engine}_observation_reader import {Engine}ObservationReader

__all__ = ["{Engine}ObservationReader"]
```

---

## Example: Implementation Plan

```markdown
# {EngineName} Implementation Plan

**Architecture Reference:** MSI-001 through MSI-009 (Frozen v1.0)
**Platform Reference:** MSI v1.0 Platform Release (tag msi-v1.0-certified)
**Date:** {YYYY-MM-DD}
**Status:** Proposed

---

## Milestone Summary

| Milestone | Description | Reuse or Custom |
|-----------|-------------|-----------------|
| M0 | Contracts & Interfaces | Reuse from core.msi |
| M1 | Test Artifact | Custom |
| M2 | Artifact Loader | Reuse FilesystemArtifactLoader |
| M3 | Observation Reader | Custom |
| ... | ... | ... |

---
```

---

## Governance

New engines follow the same process as the DRA:

1. Author implementation plan
2. Implement M0 through M9 in dependency order
3. File implementation report per milestone
4. Independent technical review per milestone
5. Fix verification (if PASS WITH MINOR FIXES)
6. Certification + tag
7. Append events to implementation ledger
8. Final platform certification (tag: `msi-v1.0-{engine}`)

---

## Version

**Template Version:** 1.0

**Target Platform:** MSI v1.0 (`msi-v1.0-certified`)

---

**End of Template**
