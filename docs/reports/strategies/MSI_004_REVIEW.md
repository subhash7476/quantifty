# MSI-004 Architecture Review

**Document under review:** `docs/architecture/market_state_intelligence/MSI_004_EVIDENCE_ARCHITECTURE.md` (Draft v0.2)
**Reviewer:** Claude (platform-grounded)
**Date:** 2026-07-03
**Verdict:** Changes required before freeze. One blocking issue: MSI-004 describes **feature engineering** (Evidence construction/interpretation) without declaring it **offline Research**, which the Platform Constitution forbids in-repo. The evidence *invariants* are sound.

Graded against `docs/reports/MSI_GROUNDING_BRIEF.md`, governing `MSI-001` (v0.4) / `MSI-002` (v0.3) / `MSI-003` (v0.3, reframed), and `docs/PLATFORM_CONSTITUTION.md`. Scope is upward-consistency only.

---

## 1. What is sound

- **Evidence definition** (§5) extends MSI-002 §4.5 cleanly and aligns with the new Estimate/Latent Variable model: "information derived from observations that supports or contradicts hypotheses regarding latent market properties." Evidence is explicitly not an Observation, Market State, or signal. Good.
- **Determinism + causality** (§7, `MSI-EA-002`): identical observations → identical evidence; preserves causality/provenance/reproducibility. Consistent with MSI-001 `CP-003`/`CP-004`.
- **Inference independence** (§4, `MSI-EA-004`, `MSI-AD-401`): evidence never estimates state, classifies markets, determines regimes, or generates signals. Correctly keeps MSI-004 upstream of inference and consistent with MSI-001 `CP-008`.
- **Evidence quality distinct from Observation quality** (§9) — respects the MSI-003 boundary.
- **No trading intent in evidence** (`MSI-EA-005`) — good guardrail.

---

## 2. Findings

### 2.1 BLOCKING — "Evidence construction" is feature engineering; MSI-004 never declares it offline Research

§1 says "Evidence Architecture **is responsible for interpretation**"; §4 says "**interpret** observations; **construct** evidence"; §7 defines "construction rules." Interpreting observations into derived, standardized information **is feature engineering**. The Constitution (§4, lines 192–203) lists among activities that *belong outside the platform repository*:

- **Machine Learning → Feature engineering**
- **Strategy Research → Signal discovery, Market regime research**

MSI-004 as written does not say *where* Evidence construction lives. That is the same defect MSI-003 had, and it must be resolved the same way — an explicit offline/runtime split mirroring MSI-001 §4.1/§4.2 and the MSI-003 reframe:

- **Offline (Research, outside the repo):** the *design* of evidence transforms — what counts as evidence, how it is constructed, feature engineering, validation. This is authored in the Research domain and carried into the Platform only inside a **Published MSI Artifact** (MSI-001 `CD-002`, MSI-002 §4.10).
- **Runtime (Platform, read-only):** deterministically *evaluates* the validated, versioned evidence-construction rules **from the artifact** against point-in-time Observations. No discovery, no fitting, no engineering at runtime — consistent with *Analytics Produce Facts — runtime read-only* and MSI-001 `CD-004`.

Without this split, "Evidence Architecture is responsible for interpretation" reads as feature engineering inside the platform runtime, which the Constitution prohibits. The `§10` lifecycle (Constructed → Validated → **Published** → Consumed) already implies the offline-authoring/artifact-publication flow — the doc just needs to *state* it.

**This also fixes a roadmap problem:** the MSI-004 roadmap entry lists "Feature Governance" and "Feature Promotion Framework" — feature-lifecycle governance belongs on the Research side (MSI-007 already owns "Feature Lifecycle / Promotion Pipeline"), not as an in-repo MSI-004 deliverable.

### 2.2 NON-BLOCKING — §3 uses the stale term "Observation Acquisition"

§3's position diagram reads "Observation Acquisition → Evidence Architecture → State Inference." MSI-003 was reframed away from an acquisition layer; the upstream is now the **Observation layer / Observation Architecture** (a read-contract over Platform facts). Update the term.

### 2.3 NON-BLOCKING — §8 provenance chain skips Estimate and Market State, and uses a non-entity ("Inference")

§8 shows `Observation → Evidence → Inference → Knowledge`. MSI-002's canonical chain (as revised) is `Observation → Evidence → Estimate → Market State → Knowledge`. "Inference" is a process, not an MSI-002 entity. Align the chain to the canonical entities so lineage is reconstructable in the ontology's own terms.

### 2.4 NON-BLOCKING — Decision IDs `MSI-AD-4xx` collide with the platform ADRs

Same issue fixed in MSI-003: `MSI-AD-401…404` reads as "ADR." Rename to a non-colliding per-doc scheme (`MSI-4D-01…04`) for consistency across the series (MSI-001 `CD`, MSI-002 `OD`, MSI-003 `3D`).

### 2.5 MINOR — §1 "responsible for interpretation" needs the offline qualifier

Once 2.1 is applied, reword §1 so "interpretation" is explicitly the *evaluation of validated, artifact-carried construction rules*, not open-ended runtime interpretation.

---

## 3. Recommendation

- **2.1 gates freeze.** Add the offline (Research, artifact-authored) vs runtime (read-only, evaluates validated rules) split to Evidence construction — the single change that keeps MSI-004 on the right side of the Constitution's feature-engineering prohibition. It parallels the MSI-003 reframe exactly.
- **2.2–2.5** are consistency polish (stale term, ontology-chain alignment, decision IDs).
- The evidence *invariants* (derived-from-observations, deterministic, provenance-complete, inference-independent, no trading intent) are all correct and should be preserved through the reframe. As with MSI-003, the problem is **placement** (where construction happens), not the principles.
