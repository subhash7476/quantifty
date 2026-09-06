# MSI-009 — Architecture Review

**Document under review:** `docs/architecture/market_state_intelligence/MSI_009_DAILY_REGIME_ANALYZER_ARCHITECTURE.md` (Draft v0.1)  
**Reviewer:** Architecture Review Board (Claude, platform-grounded)  
**Date:** 2026-07-03  
**Verdict:** Not ready for freeze. Three Critical findings (pipeline diagram, Knowledge Object redefinition, engine input contract). Three High findings (dual-purpose charter, undefined entity, evidence-ordering). The document is otherwise laser-aligned with MSI principles; the defects are scope/placement, not philosophy.

Graded against: MSI-001 (v0.4), MSI-002 (v0.3), MSI-003 (v0.3), MSI-004 (v0.3), MSI-005 (v0.3), MSI-006 (v0.2), MSI-007 (v0.2), MSI-008 (v0.2), `docs/PLATFORM_CONSTITUTION.md`, `docs/reports/MSI_GROUNDING_BRIEF.md`, ADR-023, the MSI Roadmap v1.2, the MSI Program Charter, and the DRA Technical Dossier (`docs/reports/DRA_TECHNICAL_DOSSIER.md`). Prior review findings from MSI-001 through MSI-008 are cross-referenced where relevant.

---

## 0. Roadmap Gate — Freeze ordering

The roadmap states: *"A later specification shall not be frozen if any prerequisite specification remains unfrozen."* MSI-009 depends on MSI-001 through MSI-008 per §18. The roadmap status table confirms **all eight predecessors are Not Frozen**:

| Doc | Roadmap Status |
|-----|----------------|
| MSI-001 | Reviewed — Ready for Freeze |
| MSI-002 | Reviewed — Ready for Freeze |
| MSI-003 | Reviewed — Ready for Freeze |
| MSI-004 | Reviewed — Ready for Freeze |
| MSI-005 | Reworked; Architecture Review Required |
| MSI-006 | F1–F4 applied; Re-review Recommended |
| MSI-007 | lifecycle→MSI-008 + F1/F2 applied; Re-review Recommended |
| MSI-008 | Reviewed; Changes Required |

MSI-009 does not itself claim to be frozen (it correctly declares "Draft v0.1, Not Frozen"), so this is not a self-contradiction. It is a **structural reminder**: every normative assertion MSI-009 makes — that DRA "shall conform to" MSI-005, that Knowledge Objects "conform to MSI-005" (§10), that DRA "executes only Published MSI Artifacts defined by MSI-007" (§13) — rests on specifications whose own open review items could alter those contracts. The document is correct to acknowledge this via its draft status.

---

## Findings

### C1 — CRITICAL — §5 runtime pipeline diagram contradicts the two-pipeline architecture (MSI-005 §4, ADR-023 §5.4)

MSI-009 §5:

```
Platform Observations → Evidence Construction → Published MSI Artifact → State Inference → Daily Market Knowledge → Strategy → SignalSource → Platform Runtime
```

ADR-023 §5.4 and MSI-005 §4 define two **distinct** pipelines:

```
Research:  Observation → Evidence → Inference → Validation → Artifact
Runtime:   Observation → Evidence → Artifact Evaluation → Knowledge → Strategy → SignalSource
```

Three contradictions:

1. **"Published MSI Artifact" positioned as a sequential stage.** In both pipelines, the artifact is an **object consumed as input**, not a data-transforming pipeline stage. In the Runtime pipeline, "Artifact Evaluation" is the stage — the artifact itself is a side-input. Placing the artifact as a stage implies it transforms data, which it does not.

2. **"State Inference" replaces "Artifact Evaluation."** MSI-005 distinguishes two faces: the research-facing Inference Contract and the runtime-facing Artifact Evaluation engine. The runtime pipeline uses "Artifact Evaluation" to avoid conflating with research-stage "Inference." MSI-009's diagram collapses both into a single "State Inference" stage without acknowledging the distinction.

3. **The diagram is a single linear pipeline when the architecture mandates two.** ADR-023's two-pipeline model is the structural guarantee against train/serve skew. A single pipeline that interleaves Evidence Construction → Artifact → State Inference erases the boundary and suggests the DRA participates in Research activities at runtime.

**Fix:** Replace with a diagram showing the DRA's position within the **runtime pipeline only**, with the artifact as a side-input to the evaluation stage:

```
Platform Observations → Evidence Construction (artifact-carried rules) ──┐
                                                                        ▼
                                               Artifact Evaluation ← Published MSI Artifact
                                                        │
                                                        ▼
                                                   Knowledge → Strategy → SignalSource
```

### C2 — CRITICAL — §10 Knowledge Object fields contradict the governing definition (MSI-005 §11, MSI-OP-004)

MSI-005 §11 is the **owner** of the Knowledge Object schema. MSI-009 §10 redefines it:

| MSI-005 §11 (governing) | MSI-009 §10 (this doc) | Delta |
|---|---|---|
| Knowledge Identifier | *(absent)* | Missing |
| Evaluation Timestamp | Runtime Timestamp | Renamed |
| Artifact Version | Artifact Identifier | Different concept — Version is point-in-time, Identifier is permanent |
| Runtime Version | *(absent)* | Missing |
| Market State | Market State | Match |
| Provenance Reference | Provenance Reference | Match |
| *(absent)* | Estimate Set | **New field — undefined in ontology** |

MSI-OP-004: *"Later specifications may extend entities. They shall not redefine them."* Dropping two fields, renaming two, and adding an undefined field is redefinition, not extension.

The "Estimate Set" addition is separately problematic: MSI-002 §4.8 defines Market State as "the collection of Estimates." Adding "Estimate Set" alongside "Market State" either duplicates the same collection (violating MSI-OP-002: entities shall not overlap) or introduces an undefined entity not licensed by MSI-002 (violating MSI-OP-004). See H2 below.

**Fix:** Drop the Knowledge field enumeration from §10. Replace with: *"Knowledge Objects conform to MSI-005 §11. The DRA produces Daily Market Knowledge as the Knowledge Object containing Market State."* Let the governing spec own the schema.

### C3 — CRITICAL — §4/§7 DRA input contract contradicts MSI-005 §7

MSI-009 §4: *"Its responsibility is to transform **Platform observations** into deterministic daily market-state knowledge."*  
MSI-009 §7: *"The DRA consumes only **observations** conforming to MSI-003."*

MSI-005 §7: *"The runtime artifact-evaluation engine shall consume only: **Evidence Objects**; Published MSI Artifact; deterministic runtime configuration."*

The Runtime pipeline includes Observation → Evidence, yes — but the **evaluation engine proper** (the MSI-005-defined artifact-evaluation stage) consumes Evidence, not raw Observations. By positioning the DRA as the full runtime pipeline (consuming Observations, constructing Evidence, evaluating the artifact), MSI-009 is broader than MSI-005's engine contract — but it never states this explicitly.

If the DRA IS the full runtime pipeline, it should say so clearly and acknowledge that it subsumes MSI-003 (read), MSI-004 (construction), and MSI-005 (evaluation). If it is only the artifact-evaluation engine, it should consume Evidence per MSI-005 §7.

**Fix:** Add a scoping statement: *"The DRA implements the full MSI Runtime pipeline — it reads Observations (MSI-003), constructs Evidence (MSI-004), and evaluates the Published MSI Artifact (MSI-005) to produce Knowledge. Where MSI-005 §7 defines the engine's input contract as Evidence, the DRA's broader pipeline encompasses that contract."*

---

### H1 — HIGH — Dual-purpose charter: DRA as both production engine and MSI architecture validator (§1, §17, MSI-9D-04)

MSI-009 §1 assigns the DRA two purposes:
1. Provide deterministic daily market-state knowledge for strategies
2. **Validate the completeness of the MSI constitutional architecture through a concrete implementation**

MSI-9D-04: *"The DRA validates the completeness of the MSI Architecture."*  
§17: *"Successful implementation of the DRA demonstrates that the MSI constitutional architecture is complete."*

This is a single-responsibility violation and a logical circularity:

- **Validation is MSI-006's responsibility** — it owns the Validation Identifier, the validation domains, and the acceptance criteria. MSI-006 validates implementations; the DRA is an implementation being validated. Having the implementation also be the validator conflates roles.
- **Circular logic** — the DRA depends on MSI-001 through MSI-008 being correct (it "shall conform to all preceding MSI specifications," MSI-DRA-005). If a gap exists in those specifications, a conformant DRA would faithfully reproduce the gap — and could not detect it. The only way the DRA can "validate completeness" is if the architecture is already complete, in which case the validation is redundant.
- **Per the Program Charter §13**, the MSI program is complete when "all governing MSI specifications are approved; all governing MSI specifications are frozen; the first Runtime Market State Engine is integrated." The DRA is the result of completeness, not the test for it.

The DRA's role as a **concrete test that the architecture CAN be implemented** is reasonable and useful — it proves implementability, not completeness. Conflating "implementable" with "complete" overclaims.

**Fix:** Rephrase MSI-009's second purpose: *"demonstrate the implementability of the MSI constitutional architecture through a concrete reference implementation"* — and drop the "validate completeness" language from §17 and MSI-9D-04.

### H2 — HIGH — "Estimate Set" (§10) is an undefined ontological entity

MSI-009 §10 introduces "Estimate Set" as a Knowledge component alongside Market State. Per MSI-002 §4.8, Market State IS the collection of Estimates. There is no "Estimate Set" entity in MSI-002's ontology, and no definition of how it differs from Market State.

If "Estimate Set" is meant to be the same thing as Market State, it duplicates (MSI-OP-002). If it is meant to be a subset or a different abstraction, it introduces an entity not defined by the governing ontology (MSI-OP-004: later specs may extend entities, not introduce undefined new ones without ontological grounding).

**Fix:** Remove "Estimate Set." Market State is the collection of Estimates carrying value + uncertainty. No secondary collection is architecturally justified.

### H3 — HIGH — Evidence Construction placed before artifact availability (§5 diagram, §8)

MSI-009 §5 places "Evidence Construction" as a pipeline stage feeding INTO "Published MSI Artifact." But MSI-004 §2 states that runtime Evidence construction *evaluates artifact-carried rules* — the construction rules are carried BY the artifact, so Evidence Construction cannot logically precede the artifact.

The correct ordering: the artifact provides the construction rules; those rules are applied to Observations to produce Evidence; the artifact-evaluation engine then consumes that Evidence. Evidence Construction and Artifact Evaluation both depend on the artifact, and neither precedes it.

As diagrammed, the implication is that the DRA constructs Evidence independently of (or before accessing) the artifact, which contradicts MSI-004's offline/runtime split.

**Fix:** Align with C1's recommended diagram, where Evidence Construction receives artifact-carried rules as a side-input, and the artifact is available to all runtime stages.

---

### M1 — MEDIUM — "Daily" cadence assumed without acknowledging it as orthogonal to the MSI architecture

MSI-002 §4.8 defines Market State at "a particular instant" — cadence-agnostic. MSI-005 never prescribes a temporal frequency. MSI-009 repeatedly bakes "daily" into its identity (name, title, §1, §5, §10). This is legitimate scoping for a reference implementation, but should be explicitly noted as a narrowing choice not derived from the governing architecture — otherwise a reader may assume the MSI architecture prescribes daily evaluation.

**Fix:** Add a scoping statement: *"The DRA operates at daily cadence — a scoping choice for the reference implementation. The MSI architecture is cadence-agnostic; future Market State Engines may operate at intraday or multi-day frequencies under the same contracts."*

### M2 — MEDIUM — §13 "executes only Published MSI Artifacts" omits the activation gate (MSI-008 §9)

MSI-009 §13: *"The DRA executes only Published MSI Artifacts defined by MSI-007."*

MSI-008 §9: *"An **Active** Published MSI Artifact is eligible for runtime loading."* The lifecycle distinguishes "Published Artifact" (identity-exists state) from "Active" (eligible-for-runtime state). An artifact can be Published but not Active.

MSI-009 should reference both states: the DRA executes *Active* Published MSI Artifacts, as governed by MSI-007 (artifact identity) and MSI-008 §9 (activation).

**Fix:** *"The DRA executes only Active Published MSI Artifacts, as governed by MSI-007 (artifact identity) and MSI-008 §9 (activation)."*

### M3 — MEDIUM — DRA dossier confirms previous implementations violated the Constitution's boundary; MSI-009 doesn't acknowledge the precedent

The DRA dossier documents that both the rule-based `RegimeDetector` and the HMM classifier lived inside the platform repo (`D:\BOT\root`, then partially migrated to `F:\nifty` before being deliberately removed). The Constitution §4 lists "Market regime research" among activities that belong **outside** the platform repository. Previous DRA code (feature engineering, HMM training, rule-based classifier) was exactly the in-repo regime work the Constitution forbids.

MSI-009 is architecturally clean — it correctly scopes out model training, feature engineering, and optimization (§3). But it never acknowledges the precedent or explains how the DRA's runtime-only design prevents the same violation. This is not a defect in MSI-009's architecture, but omitting the lesson learned weakens the document's authority.

**Fix:** Optional — add a brief note that previous regime-code violated the Research/Platform boundary by colocating feature engineering and ML training; the DRA architecture enforces the boundary by consuming only validated, published artifacts.

---

### L1 — LOW — §11 "existing Platform interfaces" are aspirational, not existing

MSI-009 §11: *"The DRA integrates with Platform runtime exclusively through **existing** Platform interfaces."*

The grounding brief §4: *"Greenfield strategy layer. `core/strategies/` does not exist; there is no production `SignalSource`, no alpha, no strategy."* The interface through which strategies consume MSI knowledge is the **read-side dependency** described in the README (settled decision #1) — but this interface doesn't exist yet. MSI-005 §6 says "expose Knowledge through Platform interfaces" without defining them.

The word "existing" is factually incorrect and invites a counter-argument. The principle is correct — the DRA should use the strategy interface, not create a privileged channel — but the interface is specified, not existing.

**Fix:** Replace "existing" with "defined": *"The DRA integrates with Platform runtime exclusively through the strategy interfaces defined by MSI-005 and the Platform Architecture."*

### L2 — LOW — §6/§8 responsibilities restate MSI-003/004/005 without adding DRA-specific scope

§6 (DRA shall consume observations, evaluate evidence, execute artifact, produce knowledge, preserve provenance, support replay) is a near-verbatim restatement of responsibilities already owned by MSI-003 §4, MSI-004 §5, and MSI-005 §6. §8 (Evidence shall conform to MSI-004, remain deterministic, preserve provenance) restates MSI-004 §8 and §9.

The restatements don't contradict — they're redundant. The reference implementation architecture should focus on what makes the DRA specific: daily cadence, the particular observations/evidence it consumes, and its runtime integration points.

### L3 — LOW — MSI-9D-01 through MSI-9D-03 are restatements, not new decisions

| Decision | Substance | Equivalent |
|---|---|---|
| MSI-9D-01 | DRA is reference implementation | MSI-009 scope statement, appropriate |
| MSI-9D-02 | DRA introduces no new constitutional concepts | MSI-CP-001, MSI-DRA-005 |
| MSI-9D-03 | Future engines conform to same contracts | MSI-005 §16, MSI-5D-01 |
| MSI-9D-04 | DRA validates MSI completeness | Novel, but see H1 |

Three of four decisions are not new architectural commitments — they affirm existing ones. MSI-9D-01 is a useful scoping statement. The rest could be folded into §15 (Architectural Principles).

### L4 — LOW — Terminology variance: "Runtime Timestamp" vs "Evaluation Timestamp"

§10 uses "Runtime Timestamp." MSI-005 §11 uses "Evaluation Timestamp." Consistent terminology across the specification chain matters for audit and cross-reference. Not a defect, but pick one and align.

---

## What is architecturally correct — and should remain unchanged

- **Strategy independence (§4, §6, §11).** DRA produces knowledge, never signals. Correctly places Strategy between Knowledge and SignalSource in the diagram. Consistent with MSI-001 MSI-CP-008, MSI-005 §6, and the README settled decision #1.

- **Research/Runtime separation (§3, §6).** DRA runtime scope explicitly excludes training, optimization, feature engineering, and model modification. Correctly mirrors MSI-001 §4.2 and the Constitution's prohibition on in-repo research.

- **Artifact governance delegation (§14).** DRA performs no governance operations; lifecycle owned by MSI-008. Correct single-owner discipline matching the MSI-008 review's central finding.

- **Validation delegation (§12).** No Published MSI Artifact until validation completed. Correctly references MSI-006 as the validation authority, consistent with MSI-6D-03.

- **MSI-DRA-001 through MSI-DRA-005** correctly mirror the core MSI guarantees: determinism, replayability, strategy independence, provenance, predecessor conformance. These are well-scoped to what a runtime engine must guarantee.

- **Dependency enumeration (§18).** Correctly lists all eight MSI prerequisites. Consistent with the roadmap dependency graph.

- **Classification as Reference Implementation Architecture.** Appropriate — this is the right classification for a document defining the first concrete engine's architecture without prescribing algorithms.

- **No reference to `DayTypeEngine` or any code as prior art.** Clean — consistent with the grounding brief's prohibition and with the platform's greenfield strategy layer.

---

## Freeze Candidate

**No.** MSI-009 is not a freeze candidate for three independent reasons:

1. **C1, C2, C3 are blocking.** The pipeline diagram, Knowledge Object redefinition, and engine input contract contradict MSI-005 — the governing inference specification. Reconcile these before freeze.
2. **Roadmap rule:** all eight predecessors remain Not Frozen. Even if MSI-009 were internally flawless, it cannot freeze before its prerequisites.
3. **H1 and H2** (dual-purpose validator, undefined Estimate Set entity) should be resolved before freeze to avoid downstream propagation.

MSI-009's draft quality is high — its philosophy, its boundary discipline, and its conformance posture are all correct. The issues are scope/placement, not direction. After C1–C3 are resolved and MSI-005 through MSI-008 stabilize, it should reach freeze quickly.

---

## Summary of findings by severity

| Severity | ID | Finding |
|---|---|---|
| **Critical** | C1 | §5 single-pipeline diagram contradicts two-pipeline architecture (MSI-005 §4, ADR-023) |
| **Critical** | C2 | §10 Knowledge Object fields redefine MSI-005 §11 schema (MSI-OP-004 violation) |
| **Critical** | C3 | §4/§7 DRA consumes "observations" but MSI-005 §7 says engine consumes Evidence |
| **High** | H1 | DRA positioned as both production engine and MSI architecture validator — circular |
| **High** | H2 | "Estimate Set" is undefined in MSI-002 ontology; duplicates or conflicts with Market State |
| **High** | H3 | Evidence Construction placed before artifact availability, contradicting MSI-004 §2 |
| **Medium** | M1 | "Daily" cadence assumed without acknowledging it is orthogonal to cadence-agnostic MSI architecture |
| **Medium** | M2 | §13 "executes Published MSI Artifacts" omits MSI-008's Active-gate |
| **Medium** | M3 | Document omits the precedent of prior in-repo regime code violating the Constitution boundary |
| **Low** | L1 | "Existing Platform interfaces" don't exist — greenfield strategy layer |
| **Low** | L2 | §6/§8 restate MSI-003/004/005 responsibilities without DRA-specific scope |
| **Low** | L3 | MSI-9D-02/03/04 are restatements or problematic, not new architectural decisions |
| **Low** | L4 | "Runtime Timestamp" vs MSI-005's "Evaluation Timestamp" — terminology drift |

---

**End of Review**
