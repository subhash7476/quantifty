# MSI-007 — Architecture Review

**Document under review:** MSI-007 Published MSI Artifact Specification (Draft v0.1)
**Reviewed against:** MSI-002 (ontology), MSI-005 (State Inference v0.2), MSI-006 (Validation v0.2), MSI Roadmap v1.2, ADR-023
**Verdict:** Architecturally the most important MSI document — it formalizes the Research→Platform handshake — and it is close. **Not ready to freeze.** One headline decision (lifecycle ownership), one cross-reference regression, one mandated reconciliation, and two smaller items.

**Status update (2026-07-03):** v0.2 applies the headline decision + F1/F2/F4 — lifecycle removed from §12 and ceded to MSI-008 (§3 scope updated; MSI-008 roadmap deliverables gain Published Artifact Lifecycle); §4 diagram term fixed to State Inference; MSI-005 §9 reconciled to the MSI-007 metadata contract (Approval Status dropped, metadata list deferred to MSI-007); MSI-006 ownership of the Validation Identifier acknowledged in §7. F3 (compatibility model) and F5 remain open; re-review recommended.

---

## 0. Headline — the lifecycle challenge (answered decisively)

**Question:** should the artifact lifecycle (Candidate → Validated → Published → Consumed → Retired) live in MSI-007, or be owned entirely by MSI-008, leaving MSI-007 to define only identity, metadata, and the runtime contract?

**Answer: move it to MSI-008. Remove the lifecycle from MSI-007.** The draft's compromise (§12: "MSI-007 defines the states, MSI-008 defines governance") is not enough — it is a half-ownership that invites exactly the drift the program is trying to eliminate. Three independent reasons, any one sufficient:

1. **Lifecycle state is mutable; the artifact is immutable.** §10 says a Published MSI Artifact is never modified. But an artifact *moves* Candidate → … → Retired over time. A time-varying annotation cannot be a property the immutable-artifact spec owns. It necessarily lives *outside* the artifact, maintained by governance. Putting a mutable state machine inside the immutability spec is self-contradictory.

2. **The five states span three domains, not one.** Only *one* of them is intrinsic to MSI-007:
   - **Candidate / Validated** — a *research + validation* object that has **not yet crossed the boundary**. It is not yet a Published MSI Artifact at all. "Validated" also duplicates MSI-006's *Approved verdict* (MSI-006 §9).
   - **Published** — the one transition MSI-007 legitimately owns: the act of *becoming* a Published MSI Artifact.
   - **Consumed** — a **runtime usage fact** (MSI-005), not a lifecycle stage. An artifact is consumed many times, concurrently; it is not a monotonic state the artifact "enters and rests in." This one shouldn't be a lifecycle state anywhere.
   - **Retired** — **governance** deprecation (MSI-008 Deprecation Policy).
   So four of five states belong to Research/Validation, Runtime, or Governance — not to the artifact-identity spec.

3. **Single-owner consistency.** MSI-006 §9 (just reworked) already cedes deployment lifecycle to MSI-008 ("MSI-006 states fitness; MSI-008 decides promotion"). If MSI-007 co-defines the state list, the lifecycle is now split across **three** documents. Owning the nouns (states) in one doc and the verbs (transitions) in another is precisely the MSI-OP-002 duplication the whole review discipline exists to prevent. Whoever owns the state machine owns both.

**What MSI-007 keeps:** exactly one lifecycle-adjacent thing — the **publication event**: the instant an approved candidate becomes a Published MSI Artifact (identity minted, metadata sealed, provenance frozen). That is what this document *is about*. Everything before (candidacy, validation) and after (consumption, retirement) is owned elsewhere. MSI-007 may *reference* that an artifact's lifecycle state is governed by MSI-008 — it must not enumerate the state machine. Delete §12's ladder; drop "Consumed" entirely.

This also removes the standing tension in §3, which already excludes "deployment governance" from scope while §12 defines a governance lifecycle.

---

## Findings

### F1 — HIGH — Stale term in the §4 diagram: "Knowledge Production"
§4 line ~91 routes `Published MSI Artifact → Knowledge Production → Strategy`. "Knowledge Production" no longer exists — MSI-005 was renamed **State Inference** and Knowledge folded in as its output (ADR-023). This is the exact cross-reference drift the program is policing. Replace with **State Inference** (or "Runtime MSI / Artifact Evaluation").

### F2 — MEDIUM-HIGH — Metadata not reconciled with MSI-005 §9 (ADR-023 mandate)
ADR-023 required MSI-005's runtime binding metadata to be reconciled against the MSI-007 contract. They currently disagree:

| MSI-005 §9 | MSI-007 §7 |
|---|---|
| Provenance **Metadata** | Provenance **Reference** |
| Approval Status | *(absent)* |
| *(Compatibility Version only)* | Compatibility Version **+ Runtime Compatibility** |

MSI-007 is now the **owner** of the artifact contract, so MSI-005 must be aligned to MSI-007, not vice versa. Two specific calls:
- **Naming:** settle "Provenance Metadata" vs "Provenance Reference" — one term.
- **Drop "Approval Status" from both.** Approval/lifecycle status is a mutable governance annotation (see §0) — it does not belong in immutable binding metadata. MSI-007 correctly omits it; MSI-005 §9 should too. (Consistent with the lifecycle decision above.)

### F3 — MEDIUM — Compatibility / version vocabulary sprawls
Across §7, §8, §13 the artifact carries: Schema Version, Compatibility Version, Runtime Compatibility, and "supported runtime / ontology / inference-contract version(s)." It is unclear how "Compatibility Version" (§7) relates to the three "supported X version(s)" (§8), or how runtime binding (§13) uses them. Define one coherent compatibility model: what the artifact **pins** (ontology version = MSI-002, inference-contract version = MSI-005, runtime version, schema version) and how §8's compatibility rejection evaluates each. Right now a reader cannot tell which field gates binding.

### F4 — LOW — Acknowledge MSI-006 as owner of the Validation Identifier
MSI-007 correctly *references* the Validation Identifier (§7/§9/§13) — good, and consistent with MSI-6D-05. Add one line stating it is owned by MSI-006 and treated here as an opaque reference, to make the single-owner rule explicit at the point of use.

### F5 — LOW — Principle ID scheme
Principles use `MSI-AP-70x`; decisions use `MSI-7D-0x`. The `70x` block prefix is redundant (AP already scopes to doc 7) and diverges from the `MSI-SI-00x` / `MSI-VF-00x` pattern in 005/006. Cosmetic; align if you care about series uniformity.

---

## What is right (keep)

- **Opaque-executable runtime contract (§11, MSI-7D-02)** — excellent and exactly correct: runtime depends only on metadata + inference contract + compatibility and never inspects internals. This is the concrete enforcement of MSI-005 model independence and the "internals implementation-defined" boundary. It is the heart of the handshake and it is right.
- **Identity: unique, constant, never reused (§6)** — correct.
- **Immutability + new-version-on-change + permanent reproducibility (§10, MSI-7D-04)** — correct and load-bearing.
- **Compatibility rejection (§8, "runtime shall reject incompatible artifacts")** — correct gate (needs the F3 tightening, but the principle is right).
- **Provenance links to originating research + Validation Identifier + contract/ontology versions (§9)** — correct lineage.
- **Dependency numbering** correct for roadmap v1.2 (Depends 001–006; Required by 008).

---

## Recommendation

Return for v0.2. The freeze-blockers are **§0 (remove lifecycle → MSI-008)**, **F1 (stale "Knowledge Production")**, and **F2 (reconcile metadata with MSI-005, drop Approval Status)**. F3 should be settled for a clean contract. F4/F5 are polish. Once lifecycle is removed, MSI-007 becomes exactly what you described: a pure Research→Platform handshake — identity, metadata, compatibility, provenance, immutability, and the runtime binding contract — with the publication event as its single lifecycle touchpoint.

Note the coupling: F2 and §0 both create edits to **MSI-005 §9**, and §0 hands the lifecycle to **MSI-008** — so this review is best actioned together with the MSI-005 metadata alignment and before MSI-008 is drafted.

**End of Review**