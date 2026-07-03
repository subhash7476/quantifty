# MSI-005 — Architecture Challenge

**Subject:** Three architectural decisions to settle before freezing MSI-005
**Documents examined:** MSI-005 (draft v0.1), MSI-002 Ontology (reviewed v0.3), MSI Roadmap (v1.1 draft)
**Mode:** Deliberate challenge of the architecture — not the wording
**Status:** Analysis + recommendations. No edits made to MSI-005; these are to be settled *before* freeze.

---

## 0. The one decision underneath all three

The three questions are not independent. They are three symptoms of a single unsettled decision:

> **What is MSI-005''s responsibility?**
>
> **(A) The inference-contract layer** — Evidence → Estimates → Market State. Inference interfaces, confidence/uncertainty representation, inference contracts, model independence. *This is what the roadmap promised.*
>
> **(B) The runtime evaluation engine** — deterministic execution of a governed Published Artifact against Evidence to produce Knowledge, with replay and provenance. *This is what the draft actually delivered.*

Settle (A) vs (B) and all three answers fall out of it. Answering the three in isolation is the wrong altitude for what you asked.

The draft has silently chosen (B) and, in doing so, left the roadmap''s inference deliverables — **Inference Interfaces, Confidence Estimation, Uncertainty Representation, Inference Contracts** — **homeless**. That is the load-bearing finding, and it does not depend on deciding which document is "more correct."

---

## 1. "Knowledge Production" vs "State Inference" — a scope fork, not a rename

**Recommendation: do not treat this as a naming choice. Decide the scope fork first (section 0); the title follows.**

### Steelman for the draft''s framing (credit it)
The draft''s model — a *dumb, deterministic evaluator* with all the intelligence baked into the Published Artifact upstream in Research — is **deeply consonant with the platform''s own governing principles**:

- CLAUDE.md: *"Analytics Produce Facts — all indicators pre-computed offline; runtime is read-only."*
- CLAUDE.md: *"Execution Owns Reality"* / *"Runner is Neutral."*

Under that lens, "Knowledge Production" as a deterministic runtime stage is not a mistake — it is the platform''s core philosophy applied to MSI. This framing deserves credit, not dismissal.

### Why "the roadmap says State Inference" does not automatically win
The roadmap is **v1.1 Draft** and lists MSI-005 as **Planned**. The draft is **v0.1** and newer. It is entirely plausible the author''s thinking *evolved*: split the inference-contract concern from the runtime-execution concern, and MSI-005 became the execution half. If so, **the roadmap is the stale artifact**, not the draft. Do not resolve this by seniority.

### The finding that holds regardless of which doc is newer
The roadmap''s MSI-005 inference deliverables (Inference Interfaces, Confidence Estimation, Uncertainty Representation, Inference Contracts) are **absent from the draft and currently belong to no document.** So the real decision is:

> **Does MSI-005 own the inference contract, or does that content move to a new/renamed specification?**

- If **MSI-005 owns both** inference-contract and runtime-execution → title should be **State Inference Architecture** (roadmap term; also standard ML usage for runtime prediction/serving), and the draft must *add* the missing inference-contract, confidence, and uncertainty-representation deliverables.
- If **the concerns are split** → the draft stays as the runtime-execution half (a defensible title like "Knowledge Production" / "Runtime Evaluation" is fine), **and** a companion inference-contract spec must be created to house the homeless deliverables, **and the roadmap must be corrected** to reflect the split.

### Supporting evidence (internal inconsistency)
The draft calls the runtime an **"inference engine"** in section 14 ("Future inference engines may replace one another...") while titling itself "Knowledge Production." Whichever fork you pick, reconcile this: the runtime *is* an inference engine in the ML-serving sense, so the title''s avoidance of "inference" is not currently principled.

**Required follow-up either way:** the roadmap must be reconciled with the chosen scope. Silent drift between a normative roadmap and a governing spec is itself an architectural defect.

---

## 2. Published MSI Artifact contract — defer to a dedicated artifact specification

**Recommendation: defer the full contract. MSI-005 keeps only the runtime *binding* metadata; the internal structure and schema go to a dedicated artifact specification.**

### The boundary
- **MSI-005 owns** only the *minimum metadata the runtime requires to execute an artifact deterministically* — the current section 7 list: Artifact Identifier, Version, Schema Version, Publication Timestamp, Validation Identifier, Compatibility Version, Provenance Metadata, Approval Status. This is the **execution/binding contract** and it is legitimately MSI-005''s concern (it needs these to pin, validate, and provenance-track).
- **A dedicated artifact spec owns** the *internal structure*, schema, and payload semantics.

### Why a dedicated spec — not MSI-007, not MSI-008
MSI-002 **MSI-OD-003** elevates the Published Artifact to *the only interface between Research and Platform*. An interface that load-bearing warrants **its own specification**, not:
- a subsection of MSI-007 (Research Governance owns *lifecycle* — promotion, versioning, deprecation — not the interface schema), nor
- an implementation doc (MSI-008 DRA and successors should *conform to* the artifact contract, not *define* it).

This also cleans up an existing ambiguity: both MSI-002 section 4.10 and MSI-005 section 7 defer artifact internals to an unnamed "later specification." Naming that owner (a dedicated artifact spec) removes the vagueness and respects **MSI-OP-002** (no overlapping responsibility).

---

## 3. Confidence & Uncertainty on the Knowledge Object — remove; this is a violation, not a choice

**Recommendation: remove standalone Confidence and Uncertainty from the Knowledge Object (section 8). Uncertainty already lives on the Estimate; Knowledge exposes it by *containing* Market State.**

This is the one question that the ontology has already settled — framing it as "Knowledge or Estimate?" reopens a decision that MSI-002 deliberately closed.

### The ontology already assigned uncertainty to the Estimate — deliberately
- MSI-002 section 4.7: *"Every Estimate carries both a value and a quantified uncertainty."*
- MSI-002 **MSI-OD-005**: *"Every Estimate shall carry quantified uncertainty."*
- MSI-002 section 4.8: Market State *"is the collection of Estimates"*; *"Every dimension of Market State carries its own uncertainty."*
- MSI-002 section 9 records this as a **reviewed, applied decision**: *"Estimate entity added ... uncertainty represented via Estimate and MSI-OD-005."*

So uncertainty is intrinsic to each Estimate, per-dimension, and this was a settled review outcome — not an open slot.

### Why the draft''s section 8 scalar fields are a violation
The Knowledge Object''s single top-level Confidence and Uncertainty:

1. **Flatten multidimensional uncertainty into a scalar** — contradicting **MSI-OD-001** (*"Market State ... shall never be reduced to a single architectural entity"*) and section 4.8 (*"Every dimension ... carries its own uncertainty"*).
2. **Duplicate a responsibility already assigned to Estimate** — violating **MSI-OP-002** (entities shall not overlap). Two authorities for the same fact can disagree; the ontology already named the canonical one.
3. **Silently undo the settled MSI-002 review decision** — barred by **MSI-OP-004** (later specs may extend entities, *not redefine them*).

### The correct shape
Knowledge *contains* Market State, which *is* the collection of Estimates, each already carrying value + uncertainty. Uncertainty reaches strategies **through** Market State at the granularity the ontology requires. No duplicate field is needed; a duplicate field is the anti-pattern.

### The "Confidence" nuance — resolve it explicitly
Confidence appears **nowhere** in MSI-002, yet the roadmap lists *"Confidence Estimation"* as an MSI-005 deliverable. Reconcile as follows:

- **"Confidence Estimation" is legitimate MSI-005 *scope*** — an inference activity (how uncertainty is quantified). It belongs in the document.
- It does **not** license a Confidence *field* on the Knowledge Object. Per **MSI-OP-004**, MSI-005 cannot mint a new canonical property.
- If a scalar aggregate confidence is ever genuinely wanted for ergonomics, it must be **defined in MSI-002 first** as an explicitly *derived projection* of per-Estimate uncertainties — never a co-equal primary field.

---

## 4. Summary of recommendations

| # | Question | Recommendation | Force |
|---|----------|----------------|-------|
| 0 | Underlying | Decide MSI-005''s responsibility: inference-contract layer vs runtime evaluation engine. All three follow from this. | Decide first |
| 1 | Term / scope | Not a rename — a scope fork. Decide whether MSI-005 owns the inference contract or it moves to a companion spec. Title follows. Reconcile the roadmap either way. The homeless inference deliverables are the real issue. | Reasoned recommendation; roadmap reconciliation **required** |
| 2 | Artifact contract | Defer full contract to a **dedicated artifact specification** (justified by MSI-OD-003). MSI-005 keeps only the 8-field runtime binding metadata. | Recommend dedicated spec |
| 3 | Confidence / Uncertainty | **Remove** from Knowledge Object. Uncertainty already belongs on the Estimate (MSI-OD-005), carried into Market State, which Knowledge contains. Confidence field is unlicensed (MSI-OP-004). | **Firm — current draft violates the ontology** |

**End of Document**


---

## 5. Resolution / Decisions (2026-07-03)

The architecture-review board (owner) resolved the three questions and revised the program structure. These decisions supersede the open forks above and govern all downstream MSI documents.

### 5.1 MSI-005 scope — resolved to *owns-both*
MSI-005 is **State Inference Architecture**. It owns *both* the research-facing inference contract *and* the runtime artifact-evaluation engine. "Knowledge Production" does **not** become its own architectural layer — **Knowledge is the output object of the inference architecture**. The roadmap's inference deliverables (Inference Interfaces, Confidence Estimation, Uncertainty Representation, Inference Contracts) return home to MSI-005, and the **Knowledge Object schema** lives in MSI-005 as the inference output.

*Framing to carry into the rework:* MSI-005 defines the **inference contract**; Research produces artifacts conforming to it, Runtime evaluates artifacts conforming to it. The contract is the pivot — this is the concrete meaning of "MSI-005 is the hinge." The two faces (research-facing contract vs runtime evaluation) must be kept explicitly distinct within the document.

### 5.2 Published Artifact Specification — dedicated spec, placed *before* Governance
A dedicated **Published Artifact Specification** is introduced as **MSI-007**, *before* Research Governance — not deferred to after DRA. Rationale: the artifact is the terminal output of the Research pipeline and the input to the Runtime pipeline (the join point), so everything after inference depends on it. Progression: Validation → Artifact → Governance → Implementation.

Renumbering: Research Governance **007 → 008**; Daily Regime Analyzer **008 → 009**.

*Ownership caveat (same class as §3):* the `ValidationIdentifier` is owned by **MSI-006 (Validation)**; MSI-007 (Artifact) merely *references* it; MSI-005 treats it as an opaque binding field. One concept, one owner.

### 5.3 Confidence / Uncertainty — removed from the Knowledge Object
Confirmed per §3: the Knowledge Object carries **no** standalone scalar `Confidence`/`Uncertainty`. Uncertainty lives on the Estimate (MSI-OD-005) and reaches strategies *by containing* Market State. The Knowledge Object is `{ Market State (collection of Estimates, each with its own uncertainty) + provenance + versions }`.

### 5.4 Two pipelines made explicit
The architecture has **two distinct pipelines** sharing one upstream spine:

```
Research:  Observation → Evidence → Inference → Validation → Artifact
Runtime:   Observation → Evidence → Artifact Evaluation → Knowledge → Strategy
```

- **Observation + Evidence (MSI-003/004) are the shared spine** — identical in both pipelines. This is the structural guarantee against train/serve skew: research inference and runtime evaluation consume Evidence under the *same* MSI-004 contract, which is what makes MSI-005's determinism / point-in-time guarantees hold (cf. platform Known Pitfalls: "in-sample results are meaningless").
- **The Artifact is the join point** — terminal output of Research, input to Runtime. This *earns* MSI-OD-003 ("the only interface between Research and Platform") rather than merely asserting it.

Later documents shall make the two-pipeline structure explicit.

### 5.5 Freeze decision
- Freeze **MSI-001, MSI-002, MSI-003, MSI-004**.
- **Do not freeze MSI-005** — rework to the owns-both model first, then proceed down the renumbered chain.

### 5.6 Revised roadmap

| ID | Document |
|----|----------|
| MSI-001 | Philosophy & First Principles |
| MSI-002 | Market Ontology |
| MSI-003 | Observation Architecture |
| MSI-004 | Evidence Architecture |
| MSI-005 | State Inference Architecture |
| MSI-006 | Validation Framework |
| MSI-007 | Published Artifact Specification |
| MSI-008 | Research Governance |
| MSI-009 | Daily Regime Analyzer (DRA) Runtime Architecture |

*Recorded as ADR-023. Doc sync: MSI Roadmap, README, Program Charter, MSI-002 dependency list.*

**End of Resolution**
