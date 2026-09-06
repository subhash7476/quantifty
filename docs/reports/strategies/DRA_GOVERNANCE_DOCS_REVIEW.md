# DRA Governance Documents & docs/ Organization Review

**Date:** 2026-07-04
**Scope:** `DRA_IMPLEMENTATION_PLAN.md`, `TECHNICAL_REVIEW_TEMPLATE.md`, `IMPLEMENTATION_LEDGER.md`, and the arrangement of the `docs/` tree
**Reviewer:** Claude (session review)

---

## Verdict Summary

| Item | Verdict |
|------|---------|
| DRA Implementation Plan | Sound architecture translation; **5 internal inconsistencies** to fix before M2 |
| Technical Review Template | Strong (verification-honesty discipline is excellent); **2 governance gaps** |
| Implementation Ledger | **Structurally contradicts its own append-only invariant; already out of sync with reality** |
| docs/ arrangement | Good top-level structure; `docs/reports/` (116 flat files) and `docs/Migrated Docs/` need attention; DRA README stale |

---

## 1. DRA Implementation Plan (`docs/implementation/dra/DRA_IMPLEMENTATION_PLAN.md`)

The plan is a faithful, traceable translation of MSI-009 into engineering deliverables. Every component carries an MSI trace, the DTOs match the frozen specs, milestone decomposition is sensible, and the risk register is honest. The findings below are all internal-consistency defects, not architectural ones.

### P1 — Two different implementation file-naming schemes (Medium)

§2 Package Structure names concrete implementations by strategy:
`duckdb_observation_reader.py`, `default_evidence_builder.py`, `filesystem_artifact_loader.py`, `default_artifact_evaluator.py`, `default_knowledge_builder.py`, `duckdb_knowledge_publisher.py`

But the milestone deliverables (M2–M6, §18) name the same modules plainly:
`artifact_loader.py`, `observation_reader.py`, `evidence_builder.py`, `knowledge_builder.py`, `knowledge_publisher.py`

An implementer following M2 verbatim will create files that contradict §2. Pick one scheme (the §2 strategy-named scheme is better — it matches the interface/implementation split rationale) and correct the milestone deliverables.

### P2 — Three different test locations (Medium)

- §2 places tests at `core/msi/tests/`
- Milestone deliverables reference `tests/test_artifact_loader.py` (repo-root tests/)
- Actual M0 code landed in `tests/msi/` (correct — matches platform convention)

Update §2 and the milestone deliverable paths to `tests/msi/`.

### P3 — M0 scope drift never reconciled (Medium)

The plan's M0 deliverables list contracts only (8 files, "Contracts + DTOs"). M0 as implemented also delivered all 6 interface ABCs (`core/msi/interfaces/`) and is titled "Contracts & Runtime Interfaces" in the ledger and implementation report. The interfaces were always in §2's package layout, so the work is legitimate — but it is a deviation from the plan's M0 deliverable list, and the ledger's M0 entry says "Deviations: None." Either amend the plan's M0 deliverables (v1.1 note) or record the deviation in the ledger. The M0 review's claim that "package structure exactly matches Plan §2" also glossed over this.

### P4 — `KnowledgeBuildError` referenced but not in the error hierarchy (Low)

`core/msi/interfaces/knowledge_builder.py:30` raises `KnowledgeBuildError`, which does not appear in the plan §16 error hierarchy (`errors.py` defines `KnowledgePublishError` but no `KnowledgeBuildError`). The M0 review's Finding 1 listed this docstring among the forward references but did not notice the type is absent from the plan entirely. Add it to §16 or change the docstring.

### P5 — Milestone acceptance has a forward dependency (Low)

M1's acceptance criteria include "Artifact loads via ArtifactLoader (M2)" — M1 cannot be *accepted* until M2 exists, yet the dependency order is M1 → M2. In practice this means M1 certification is provisional until M2. Either state that explicitly, or move that criterion to M2's acceptance.

### P6 — Minor editorial

- §13 "Testing Strategy" subsections are numbered 12.1–12.4.
- Storage roots are inconsistent: knowledge at `data/market_data/msi/knowledge/`, artifacts at `data/msi/artifacts/`. Both are new roots; consider unifying under one MSI data root.
- Per-date knowledge DB files (`{YYYY-MM-DD}.duckdb`) make `get_latest()`/`get_range()` multi-file scans; a single `knowledge.duckdb` with `evaluation_date` indexed would be simpler at daily cadence. Worth a one-line decision note in §6 either way.
- `KnowledgePublisher` ABC carries read methods (`get_knowledge`, `get_latest`) while §11 also defines a separate `KnowledgeReader` facade with the same reads plus `get_range` — overlapping read paths, and `KnowledgeReader` appears in M6 deliverables but not in §2's package layout and has no ABC in `interfaces/`. Decide: reader methods live on the publisher, or on the reader, not both.

---

## 2. Technical Review Template (`TECHNICAL_REVIEW_TEMPLATE.md`)

The Verified / Inspected / Reviewed / Observed vocabulary and the mandatory three-part Verification Performed section are genuinely good governance — they directly fix the "reviewer claims tests pass without running them" failure mode, and M0_REVIEW.md already uses them correctly.

### T1 — "PASS WITH MINOR FIXES" has no downstream definition (Medium)

The template's recommendation values are PASS / PASS WITH MINOR FIXES / FAIL, but the ledger's certification criteria define only PASS and FAIL. This is not hypothetical: M0 already received "PASS WITH MINOR FIXES" and the ledger has no state for it. Define the middle verdict in both documents: who applies the fixes, who verifies them, whether a re-review or a fix-verification addendum is required, and what ledger status it maps to.

### T2 — No traceability fields (Low)

The template has no field for the commit hash under review, the implementation report it reviews, or the ledger entry it feeds. The ledger's invariants promise "each entry references review and certification reports" — the template should carry the reciprocal references (Commit, Implementation Report path, Ledger entry).

### T3 — Guidelines embedded inside the template (Low)

Everything after "End of Review Report" (the ~80-line "Review Template Guidelines" section) will be copied into every instantiated review unless the reviewer knows to delete it. Move the guidelines to a companion doc (e.g. `TECHNICAL_REVIEW_GUIDELINES.md`) or mark the boundary "— delete below this line when instantiating —".

---

## 3. Implementation Ledger (`IMPLEMENTATION_LEDGER.md`)

### L1 — Append-only invariant contradicts the document's own structure (High)

Governance declares: "This ledger is append-only. No entry shall be modified once written." But the ledger is a fixed status table whose rows must be edited in place every time a milestone advances (the Review Process step 6 is literally "Ledger Updated"). Every legitimate status change violates the stated invariant. Two coherent options:

1. **Event-log form (recommended):** an append-only chronological table — `Date | Milestone | Event | Reference` — where "M0 implementation complete", "M0 review filed (PASS WITH MINOR FIXES)", "M0 certified" are separate appended rows. Current status is derived from the latest event per milestone.
2. Keep the status table and drop the append-only claim, keeping only "corrections by appending."

### L2 — Ledger already out of sync (Medium)

`reports/M0_REVIEW.md` exists with a PASS WITH MINOR FIXES recommendation, yet the ledger shows M0 as "Pending Review" with Review Report "—". The single-source-of-truth claim fails on day one. Update M0's entry (review filed, verdict, report path) as part of resolving L1.

### L3 — Certification states incomplete (Medium)

Same as T1 from the ledger side: certification criteria define PASS/FAIL only; the review process that feeds it produces three verdicts.

### L4 — Minor

- M0 is titled "Contracts & Runtime Interfaces" here vs. the plan's "Contracts + DTOs" (see P3).
- M9's "**Disposition**: Not Started" formatting differs from every other entry.
- "Chronological: entries ordered by certification date" — the table is ordered by milestone number; the event-log form (L1) resolves this too.

---

## 4. docs/ Folder Arrangement

### What's good

- Clean root: exactly 8 platform-level governance docs (Constitution, ADRs, changelog, project state, inventory, driver spec, bootstrap, promotion ledger). Nothing stray.
- `docs/architecture/market_state_intelligence/` — 13 MSI docs, consistently named `MSI_00N_*`, with README, roadmap, charter, and freeze report. Exemplary.
- `docs/implementation/dra/` with its own `reports/` subfolder — the right pattern: program-scoped docs with program-scoped reports.
- `docs/lessons_learned/` — topical, has README.
- `docs/strategies/` — four templates plus per-strategy subfolder (`reference_heartbeat_v1/`). Consistent with the promotion governance framework.
- `docs/releases/` — started correctly with MSI v1.0 notes.

### D1 — `docs/reports/` is a 116-file flat pile (Medium, chronic)

Plans, specs, reviews, characterizations, closeouts, and audits from G1, MM7–MM12, and platform-wide work all live in one flat directory. It is now the hardest part of docs/ to navigate. The DRA layout (`docs/implementation/<program>/reports/`) is the better pattern. Recommendation: don't do a disruptive mass move; instead (a) freeze flat `docs/reports/` for new program work — new programs get `docs/implementation/<program>/reports/`; (b) optionally add a `docs/reports/README.md` index grouping the existing files by program (G1, MM7, MM8, MM9, MM10–12, platform).

### D2 — `docs/Migrated Docs/` naming (Low)

Space in the directory name (breaks unquoted shell usage — the earlier directory scan literally failed on it), inconsistent with every other snake_case directory. Contents also include `STRATEGY LAYOUT.md` (space) and `Claudereasearch-12052026.md` (typo). Rename to `docs/migrated/` or `docs/archive/`. Note: `CLAUDE.md` references `docs/OPTIONS_ANALYSIS_DASHBOARD_PLAN.md`, but the file actually lives inside Migrated Docs — that pointer is broken today and should be fixed wherever the directory ends up.

### D3 — DRA README is stale (Medium)

`docs/implementation/dra/README.md`:
- The Documents table lists four TBD documents (`DRA_IMPLEMENTATION_SPECIFICATION.md`, `DRA_MILESTONE_M0.md`, `DRA_IMPLEMENTATION_LOG.md`, `DRA_VALIDATION_PLAN.md`) that were never created under those names, and omits the three governance documents that DO exist: `TECHNICAL_REVIEW_TEMPLATE.md`, `IMPLEMENTATION_LEDGER.md`, and `reports/`.
- The Milestones table shows M0 "Pending" while M0 is implemented, reported, and reviewed.
- The plan's header says "See `docs/implementation/dra/README.md`" for the review disposition — the README doesn't contain it.

### D4 — Stragglers (Low)

- `docs/superpowers/plans/` — one orphaned tool-generated plan file (`2026-05-12-options-portfolio.md`); move to the archive directory or delete if superseded.
- `docs/PROJECT_STATE.md` does mention DRA (KB sync OK on that axis); confirm CHANGELOG_PLATFORM has the DRA/MSI freeze entries when M0 is committed.
- `core/msi/`, `tests/msi/`, `docs/implementation/`, `docs/releases/` are all still untracked in git — the entire M0 milestone plus its governance docs exist only in the working tree. The ledger's review process step 5 is "Commit with milestone tag"; nothing can be certified while the work is uncommitted. (`.gitignore` does cover `__pycache__/`, so the stray `.pyc` files under `tests/msi/` won't be committed.)

---

## Recommended Action Order

1. **L1 + L2** — restructure the ledger as an append-only event log and record the M0 events (implementation complete, review filed).
2. **T1/L3** — define PASS WITH MINOR FIXES semantics in template + ledger (fix-verification addendum, no full re-review, maps to "Certified after fixes verified").
3. **P1/P2** — reconcile file naming and test paths in the plan (a v1.1 editorial amendment; the architecture is untouched).
4. **P3** — record the M0 interfaces deviation (or amend the plan's M0 deliverables) so "Deviations: None" is true.
5. **D3** — refresh the DRA README (documents table + milestone status).
6. **D2** — rename `docs/Migrated Docs/` → `docs/archive/` and fix the CLAUDE.md pointer.
7. **D1** — add `docs/reports/README.md` index; adopt per-program reports going forward.
8. Commit M0 + governance docs (they're untracked; certification is blocked on it).

---

**End of Review**
