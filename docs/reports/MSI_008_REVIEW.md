# MSI-008 — Architecture Review

**Document under review:** MSI-008 Artifact Governance Architecture (Draft v0.1)
**Reviewed against:** MSI-001, MSI-002, MSI-005 (v0.3), MSI-006 (v0.2), MSI-007 (v0.2), README, Program Charter, MSI Roadmap v1.2, ADR-023
**Verdict:** The most internally coherent document in the series — the lifecycle-ownership partition and the mutable-state/immutable-identity split are exactly right. **Not ready to freeze:** one headline title/scope fork and one governance-authority tension, plus three reconciliations.

---

## 0. Headline — the title/scope fork: "Artifact Governance" vs "Research Governance"

The roadmap, README, Charter, and MSI-007 (§16) all call MSI-008 **Research Governance**. The draft retitles it **Artifact Governance** and narrows scope to the artifact lifecycle (Promotion, Publication Approval, Supersession, Retirement, Revalidation, Drift Response) — dropping the roadmap's Research Workflow, Feature Lifecycle, Model Lifecycle, Versioning, and Architecture Governance.

**Recommendation: accept the narrowing — "Artifact Governance" is the better scope — but reconcile it deliberately.** Reasoning:

- **The narrowing aligns with the program's own boundary.** The README explicitly places research-process activities — feature engineering, model development, research workflow, optimisation — *outside the Platform repository*. So governing the research *process* is not MSI's remit; governing the *artifact* (the boundary object and its Platform-side lifecycle) is exactly its remit. "Research Governance" would have pulled MSI into defining external research workflow — contradicting "research is external" and "MSI introduces no parallel governance."
- The dropped items are not real Platform-side gaps: Versioning is covered (immutability + new-version + supersession), Promotion Pipeline is covered (§8), and Architecture Governance is already the existing ADR/PROJECT_STATE process. Feature/Model lifecycle genuinely belong to the external research repo.

**But this is the MSI-005 pattern and must not be a silent drift.** Required:
1. Rename MSI-008 to Artifact Governance in the **roadmap, README, and Charter**, and either remove the research-process deliverables or explicitly relocate them (external research repo).
2. MSI-008 §3 "does not define" must **explicitly exclude research-process governance** (feature/model lifecycle, research workflow) as external to Platform MSI, pointing at the README boundary — so the exclusion is deliberate and documented, not forgotten.

---

## Findings

### F1 — MED-HIGH — "Governance authority" framing risks a parallel governance body
§4 declares MSI-008 "the authority responsible for controlling the lifecycle," and §5/§14 give it its own decisions and records. But the Charter, README, and roadmap governance rule are emphatic: *MSI adopts the existing Platform governance (ADR process, PROJECT_STATE, Strategy Promotion governance) and introduces no parallel governance model.* The platform already has a **Strategy Promotion Pipeline** (ADR-021/022) that MSI artifact promotion is the analog of.

**Recommend:** state that MSI-008 governance operates *through* the existing Platform governance instruments (ADR/PROJECT_STATE, and the promotion-governance model), not as a new authority. §8 Promotion in particular should reference the existing promotion governance rather than read as self-contained.

### F2 — MED — Roadmap lifecycle states now disagree with the draft
The roadmap's MSI-008 deliverable (added last cycle) reads "Candidate → Validated → Published → Consumed → Retired." MSI-008 §6 uses a better 7-state ladder — **Candidate → Validated → Publication Approved → Published → Active → Superseded → Retired** — and correctly **drops "Consumed"** (a runtime usage fact, not a lifecycle state, per the MSI-007 review). Reconcile the roadmap to the draft's states. *(This roadmap line was introduced in the MSI-007 fix pass; the draft's version is the correct one.)*

### F3 — MED — §6 framing implies the artifact exists before publication
§6 says "Every Published MSI Artifact follows the lifecycle: Candidate → …". But per MSI-007 §12, an object is a **Published MSI Artifact only from Publication onward**; Candidate/Validated are pre-artifact research/validation objects. §7's ownership split already encodes this correctly (Research owns Candidate, Validation owns Validated). Tighten §6 to "an artifact progresses through" / "the lifecycle spans candidacy through retirement," so it doesn't assert the artifact exists as such during pre-publication states.

### F4 — MED — Drift: pair §13 (response) with MSI-006's open F5 (detection)
§13 Drift Response is the *response* side (performance degradation, calibration failure, ontology/runtime incompatibility, scientific invalidation). MSI-006 review F5 (drift **detection**/acceptance) is still open. Design them as a pair: **detection criteria = MSI-006** (does the artifact ship with drift bounds?), **response = MSI-008 §13**. Note the coupling so neither owns both nor leaves a gap.

### F5 — LOW — Terminology
"Publication Approved" (governance state) sits close to MSI-006's "Approved" (validation verdict) — ensure the two are unambiguously distinct. "Deployment context" (§9) is used but undefined.

---

## What is right (keep — this is strong)

- **§7 Lifecycle Ownership partition** — Research owns Candidate; Validation (MSI-006) owns Validated; Governance owns the rest. This is the single-owner discipline made explicit and it cleanly honors the MSI-006 boundary. Best section in the document.
- **MSI-AG-002** (governance state mutable, artifact identity immutable) — exactly the distinction the MSI-007 review argued for; it is why lifecycle correctly lives here and not in MSI-007.
- **MSI-AG-005 + §10/§11** — point-in-time governance replay, plus superseded/retired artifacts remaining permanently reproducible, **completes the deterministic-replay story across MSI-005/007/008**: which artifact was Active at time T is now itself replayable. This closes a real loop.
- **Revalidation §12** — new Validation Identifier, never overwrites — consistent with MSI-006 owning the identifier and with immutability.
- **Monotonic transitions (§6)** and immutable governance records (§14) — correct.
- **Dependency numbering** correct (Depends 001–007; Required by 009).

---

## Recommendation

Return for v0.2. Freeze-blockers: **§0 (settle the title/scope and reconcile roadmap/README/Charter)** and **F1 (governance-through-existing-instruments, not a parallel authority)**. F2–F4 are reconciliations that should land before freeze; F5 is polish. Architecturally the document is sound and largely freeze-ready once the "Artifact Governance" scope is made official and the governance-authority framing is aligned with the Platform Constitution.

**End of Review**