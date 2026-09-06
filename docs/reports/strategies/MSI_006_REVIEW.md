# MSI-006 — Architecture Review

**Document under review:** MSI-006 Validation Framework (Draft v0.1)
**Reviewed against:** MSI-001 (principles), MSI-002 (ontology), MSI-005 (State Inference, reworked v0.2), MSI Roadmap v1.2, ADR-023
**Verdict:** Sound foundation; **not ready to freeze**. Four substantive findings and four smaller ones below. No architectural reversal required — all findings are additive or boundary-clarifying.

**Status update (2026-07-03):** MSI-006 v0.2 applies F1–F4 — Validation Identifier ownership (§7.1 + MSI-6D-05); §9 reframed as verdicts with deployment lifecycle ceded to MSI-008 (+ MSI-6D-06); Calibration Validation (Domain 7); out-of-sample and walk-forward named (Domains 2–3). F5–F8 remain open; re-review recommended.

---

## Summary judgment

The six-domain structure is clean, the conjunctive-not-compensatory acceptance rule (§10) is exactly right, and the dependency numbering is correct for the post-ADR-023 roadmap (Depends on 001–005; Required by 007). The document correctly excludes artifact structure (MSI-007) and strategy promotion from scope.

The gaps are of two kinds: (a) **deliverables the roadmap assigns to MSI-006 that the draft omits** (Calibration, Drift Detection, and — via MSI-001 — out-of-sample/walk-forward), and (b) **two ownership boundaries that must be drawn now** to avoid the exact cross-document duplication ADR-023 was written to prevent (the Validation Identifier, and the validation-outcome vs promotion-lifecycle line with MSI-008).

---

## Findings (severity-ranked)

### F1 — HIGH — The Validation Identifier is not explicitly owned or defined
ADR-023 decision #3 makes MSI-006 the **sole owner** of the `ValidationIdentifier`: MSI-007 references it, MSI-005 treats it as opaque. In the draft it appears only as one bullet in §7 (Validation Evidence) and §11 (Provenance) — never *defined* and never *claimed*. This is the single most important cross-document contract MSI-006 carries.

**Recommend:** a first-class definition (a dedicated short section or a decision, e.g. MSI-6D-05: *"MSI-006 owns the Validation Identifier. It is the canonical, immutable reference to a validation record that MSI-005 and MSI-007 cite. No other specification mints it."*). State its properties: unique, immutable, resolvable to a full validation record.

### F2 — HIGH — Validation-outcome ladder overlaps MSI-008 (promotion pipeline)
§9 defines a four-state ladder — Rejected → Experimental → Provisionally Approved → Approved — and §1 frames the document as "governing the **promotion** of MSI research." But the roadmap assigns **Promotion Pipeline, Model Lifecycle, Versioning, Deprecation** to **MSI-008 Research Governance**. "Experimental" and "Provisionally Approved" read as *lifecycle/deployment* stages, not *validation verdicts* — this risks two documents owning one ladder (violates MSI-OP-002).

**Recommend:** draw the line explicitly. Validation produces a **verdict + evidence** at a point in time (naturally Approved / Rejected, optionally a conditional Provisional *with named conditions*). The multi-rung lifecycle an artifact travels over time is governance (MSI-008). Reword §1 from "governing the promotion of" to "**validating candidates for** promotion" — validation *gates* promotion; governance *executes* it. If the ladder stays here, scope it explicitly as validation status only, with MSI-008 owning how those states map to deployment.

### F3 — HIGH — Uncertainty calibration is absent
MSI-002 (MSI-OD-005) and MSI-005 §12 make **quantified uncertainty a first-class property of every Estimate**. The validation that this uncertainty is *calibrated* (e.g., stated 70% intervals contain truth ~70% of the time) is the check most tightly coupled to that ontological decision — and without it the entire "quantified uncertainty" edifice is unfalsifiable. The roadmap lists **Calibration** as an MSI-006 deliverable; the draft never mentions it.

**Recommend:** add Calibration as a named objective/domain (natural fit: a Scientific Validation sub-requirement, or a seventh domain). This is arguably *the* MSI-specific validation requirement and its absence is the most consequential gap.

### F4 — MEDIUM-HIGH — Out-of-sample / walk-forward not named, though MSI-001 delegates them here
MSI-001 §(line 219) states validation "shall include out-of-sample and walk-forward evaluation" and that the methods are "defined in a later MSI specification (**MSI-006**)." MSI-006 is the promised home, yet Domains 2–4 speak only of "repeatability" and "robustness" without naming out-of-sample or walk-forward. This is a broken traceability promise from a higher governing document.

**Recommend:** name out-of-sample and walk-forward explicitly as mandatory in Scientific (Domain 2) and/or Temporal (Domain 3) validation. Also aligns with the platform's Known Pitfalls ("single-period validation is misleading — always run full walk-forward").

---

## Smaller findings

### F5 — MEDIUM — Drift Detection missing; scope ambiguous
The roadmap lists **Drift Detection** as an MSI-006 deliverable; the draft omits it. Note a genuine scoping question: pre-publication you can only test *robustness* (Domain 4), whereas drift *detection* is inherently ongoing/post-publication. Decide whether MSI-006 defines drift as an **acceptance criterion** (artifact must ship with declared drift bounds / a detection method) versus ongoing **monitoring** (which may belong to MSI-008 governance or runtime). At minimum the deliverable must be addressed, even if to delegate part of it.

### F6 — LOW-MEDIUM — "Dataset" is a non-ontology term
§7 ("validation dataset") and Domain 2 lean on "dataset." The ontology's entities are **Observation** (MSI-003) and **Evidence** (MSI-004). For consistency, validation operates over Observations/Evidence; "dataset" introduces a parallel vocabulary. Recommend aligning terminology, or defining "validation dataset" explicitly in terms of the ontology entities.

### F7 — LOW-MEDIUM — Human reviewer vs deterministic validation tension
§8 requires validation be deterministic and repeatable, yet §7/§11 include a human "reviewer" and an "approval status." Clarify the split: deterministic *computation* of validation results vs human *attestation/approval*. Who produces the "Approved" outcome — an automated pass, or a human sign-off? This bears directly on what the Validation Identifier (F1) certifies.

### F8 — LOW — "Trust" framing is soft for a governing spec
§1/§4 lean on "trusted"/"trustworthy." Acceptable as philosophy framing, but consider grounding it in the concrete, testable properties already listed (sound, reproducible, deterministic, conformant) rather than the subjective term.

---

## What is right (keep)

- **Conjunctive, not compensatory acceptance (§10)** — excellent and load-bearing; no domain can be bought with another's excess.
- **Six-domain decomposition** — clean and mostly non-overlapping.
- **Determinism/reproducibility (Domain 5)** correctly mirrors MSI-005 §13 — identical Evidence + Artifact + config → identical Knowledge.
- **Dependency numbering** correct for roadmap v1.2 (Required by MSI-007).
- **Scope exclusions** correctly disclaim artifact structure and strategy promotion.
- **Immutable validation evidence (§7, MSI-6D-02/04)** — consistent with the platform's audit-first principle.

---

## Recommendation

Return to author for a v0.2 addressing F1–F4 (the freeze-blockers) and a decision on F5. F6–F8 are polish. Do not freeze until F1 (Validation Identifier ownership) and F2 (the MSI-006/MSI-008 boundary) are settled — these are precisely the single-owner cross-reference guarantees the MSI-005 review established as the program's freeze discipline.

**End of Review**