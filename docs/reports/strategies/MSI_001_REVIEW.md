# MSI-001 Architecture Review

**Document under review:** `docs/architecture/market_state_intelligence/MSI_001_PHILOSOPHY_AND_FIRST_PRINCIPLES.md` (Draft v0.3)
**Reviewer:** Claude (platform-grounded)
**Date:** 2026-07-03
**Verdict:** Approve to freeze **after one blocking fix** (out-of-sample validation principle). Everything else is non-blocking polish.

This review *is* the "Architecture Review Required / Not Frozen" gate the document asks for. It is graded against the five requirements in `docs/reports/MSI_GROUNDING_BRIEF.md` and verified against `docs/PLATFORM_CONSTITUTION.md` and `docs/ARCHITECTURE_DECISIONS.md`.

---

## 1. Conformance verification (checked against the live repo)

| Claim in MS001 | Repo reality | Result |
|---|---|---|
| §3 cites 5 Platform principles (Ledger is Truth, Execution Before Alpha, Deterministic Operation, Risk Before Trading, No Trading On Stale Data) | Constitution Principles 1–5, exact names | ✅ Accurate |
| §4.1 Research is outside the platform repo | Constitution §4 lists ML / strategy research / backtesting / regime research as "belong outside the platform repository" | ✅ Consistent |
| §8 non-goals (no alpha discovery, no training, no risk calc, no broker) | Constitution §1 "not responsible for generating alpha", §5 strategy boundary | ✅ Consistent |
| No reference to `DayTypeEngine` or any code as prior art | `core/strategies/` is empty; no regime code exists | ✅ Clean — grounding req 5 met |
| Governance introduces no new board | 26 ADRs + strategy-promotion ledger already exist; README routes MSI through them | ✅ (but see §3.2 below) |

No factual/cross-reference errors found.

---

## 2. What v0.3 fixed (previously-open grounding gaps now closed)

The grounding brief was written against a *pre-v0.3* draft. Several of its headline complaints are now resolved — credit where due, and they should **not** be re-raised as open:

- **Point-in-time correctness** — now `MSI-CP-004`. ✅ (was missing)
- **No look-ahead** — now `MSI-CP-005`. ✅ (was missing — this was flagged as the top scientific-validity risk)
- **Alpha tension defused correctly.** v0.3 did not "reconcile" the maximalist *"canonical knowledge layer / every strategy reasons through MSI"* vision — it **dropped** it, in favor of "market-state knowledge that strategies **may** choose to consume" (§3, `MSI-CP-008`, matching README line 173). This is the stronger fix and is fully conformant with "the platform must remain strategy-agnostic / usable when no strategies exist."
- **Offline vs runtime split** — §4.1 (Research, outside repo) vs §4.2 (Runtime, Platform, read-only) is clean and explicit. ✅ grounding req 2 met.
- **Demand-driven sequencing** — `MSI-CD-004` gates runtime implementation to a real production-strategy requirement. ✅ matches grounding point 4.
- **Provenance-pinning** — `MSI-CP-007` (traceable to artifact version + replay) and `MSI-CD-002` (single governed interface) cover it at principle level.

This is a materially stronger document than the version the grounding brief critiqued.

---

## 3. Findings

### 3.1 BLOCKING — Out-of-sample / walk-forward validation is not committed at the principle level

`MSI-CP-006` requires "scientific validation" but never names **out-of-sample / walk-forward** validation. Neither does the README (line 152 says only "scientific validation precedes deployment"). Grounding brief req 3 is explicit: *any MSI claim of scientific defensibility must commit, at the principle level, to out-of-sample / walk-forward validation — not defer 100% of it to a later document.* The platform's own house rule is blunt: **"in-sample results are meaningless."**

This is the one item that should gate the **Not Frozen → Frozen** transition, because "scientific validation" without an anti-overfitting commitment is the exact hole a market-state system falls through.

**Fix (trivial):** add one clause to `MSI-CP-006` — e.g. *"Validation shall include out-of-sample / walk-forward evaluation; in-sample performance is not sufficient evidence."* Method and thresholds may be deferred to MSI-006. One line closes it.

### 3.2 NON-BLOCKING — "Constitutional" naming brushes the "no parallel governance" constraint

The doc titles its own rules **Constitutional Principles** and **Constitutional Decisions** ("architectural law"). Grounding brief §5 requires MSI to introduce **no parallel governance model / no parallel board** — and the README already commits to "MSI introduces no parallel governance model." Two "constitutions" invites exactly the confusion the constraint forbids. This is naming, not substance.

**Fix (closes two items at once):** either rename to **"Governing Principles / Governing Decisions,"** or add one sentence stating these principles are **subordinate to the Platform Constitution and change-controlled through the existing ADR process** (`docs/ARCHITECTURE_DECISIONS.md`). MS001 never uses the word "ADR"; that sentence also closes the otherwise-missing ADR-pointer (grounding req 4), which is presently only covered in the README, not in the governing philosophy doc.

### 3.3 NON-BLOCKING — One-sentence-per-line prose violates a house rule

The document is written almost entirely one sentence per line/paragraph. House rule: **prefer plain paragraphs over one-sentence-per-line prose.** Consolidate.

Note — this is *not* a complaint about the FA → CP → CD layering. Restating determinism/implementation-independence across FA-005 (assumption), CP-009 (principle), and CD-001 (decision) is intentional altitude-layering, not duplication. Only the *formatting* and any verbatim slogan repetition should be compressed.

### 3.4 OPTIONAL — CP-004 and CP-005 are two angles of one causality principle

`MSI-CP-004` (point-in-time) and `MSI-CP-005` (no look-ahead) are near-restatements. Keeping both is defensible for emphasis; merging into a single "Causality / Point-in-Time" principle would tighten the doc. Author's call.

---

## 4. Separate follow-up (out of scope for this review)

Commit `49825a2` just landed a **"DRA Technical Dossier"**, and the README lists **MSI-008 "Daily Regime Analyzer."** The Constitution (line 203) lists **"Market regime research"** among activities that *belong outside the platform repository.* MS001 itself is clean on this. But if DRA work begins landing regime-*research* artifacts (training, feature engineering, parameter sweeps) inside the repo, that is the line-203 boundary made real. Recommend a **separate review of the DRA dossier** against the Research/Platform boundary — do not couple it to the MS001 freeze decision.

---

## 5. Recommendation

- **Apply 3.1** (out-of-sample clause) → then MS001 can move Not Frozen → **Frozen**.
- **Apply 3.2** (subordinate-to-Constitution + ADR sentence, or rename) — strongly recommended; closes the last governing-consistency gap cheaply.
- 3.3 / 3.4 are polish; do at the author's discretion.
- Store MS001 in the repo after 3.1 is in. The document is otherwise sound, conformant, and a clear improvement over the drafted baseline.
