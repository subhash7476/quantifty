# MSRP Phase 5A — Implementation Addendum (Review-Fixes)

**Document type:** Addendum to the Phase-5A implementation report. Records the fixes
applied in the Review-Fixes governed phase.

**Companion documents:**
- `MSRP_PHASE5A_IMPLEMENTATION_REPORT.md` — the implementation record (as-delivered for
  review; unchanged by this addendum).
- `MSRP_PHASE5A_TECHNICAL_REVIEW.md` — the independent technical review (verdict: PASS
  WITH REQUIRED FIXES).

**Status:** Review-fixes applied; ready for the next governed act (certification).

**Date:** 2026-07-06

---

## 1. Scope of this Addendum

The independent technical review cleared the artifact math as faithful to the frozen
Phase-1 dossier (commit `d9233b1`) and identified three required fixes — F1 (architectural),
F2 (moderate correctness), F3 (test gaps). This addendum records those fixes. It does
**not** edit the implementation report; that document remains the frozen record of what
was delivered for review. Where the review corrected an overstatement in the report, the
correction lives here, with an explicit pointer.

No frozen coefficients were changed by any fix (verified: n_obs=700, σ=0.272552,
b0=−3.762284, b1=0.312252, b2=0.129720, b3=0.082761, b4=0.475815 — bit-identical before
and after).

---

## 2. Fixes Applied

| Finding | Severity | Fix | Code/doc touched |
|---|---|---|---|
| **F1** — evidence rules declare transforms the certified `DefaultEvidenceBuilder` rejects (identity-only) | Major (architectural) | **No transform change** — they honestly describe the features. Corrected the implementation report's overstated compatibility claim (see §3 below) and documented the Phase-6 evidence-construction strategy (see §4). Added a boundary test pinning the constraint. | tests + this addendum |
| **F2** — `evaluate()` mis-stamped `evaluation_timestamp` via a future sentinel floor (`_SENTINEL_TS = 2026-07-03`), corrupting point-in-time provenance for every historical evaluation | Moderate | Removed the `_SENTINEL_TS` floor; `evaluation_timestamp = max(e.construction_timestamp for e in evidence)` — matches the certified reference-fixture pattern. Regenerated `model.py`; checksums recomputed. | build template → `model.py` |
| **F3** — no test covered the F1/F2 surfaces, so both passed silently | Minor | Added `test_evaluation_timestamp_is_max_evidence_timestamp` (uses a 2025 date so a sentinel floor would fail) and `TestEvidenceConstructionBoundary::test_certified_builder_rejects_non_identity_transforms`. | tests |

### F2 detail

The original `evaluate()` initialized `latest_ts = _SENTINEL_TS` (a 2026-07-03 future
constant) and only advanced it when evidence was *later*. For any held-out day before
2026-07-03 — i.e. all but the last — the resulting `MarketState.evaluation_timestamp`
was wrongly reported as 2026-07-03, and the `knowledge_id` (derived partly from the
timestamp) no longer encoded the true evaluation date. This did **not** affect the frozen
coefficients or the Phase-6 AUC score (AUC uses `Estimate.value`, not the timestamp), and
determinism was preserved — which is exactly why the replay tests missed it. The fix adapts
the non-empty path of the certified fixture at `tests/msi/fixtures/test_artifact/model.py`
(`if evidence: eval_ts = max(e.construction_timestamp for e in evidence)`) and drops the
fixture's `_SENTINEL_TS` empty-evidence fallback entirely: `evaluate()` validates all four
features are present-and-positive and raises `ValueError` first, so empty evidence is
unreachable and a bare `max(...)` is both correct and free of the sentinel branch.

---

## 3. Corrected Compatibility Claim

The implementation report's §1, §9 ("Certified-runtime compatibility"), and §10 ("MSI
runtime compatibility preserved") state the artifact is compatible with the certified MSI
runtime. **That wording is overstated** and is corrected here:

- **Loadable** via `FilesystemArtifactLoader` — ✅ true.
- **KnowledgeObject buildable** via `DefaultKnowledgeBuilder` (on pre-built Evidence) — ✅ true.
- **End-to-end evidence-buildable** via the certified `DuckDBObservationReader →
  DefaultEvidenceBuilder` path — ❌ **not supported**.

The artifact's `evidence_rules` honestly declare non-identity transforms (`rv_intraday`,
`har_weekly_5d`, `har_monthly_22d`) because its features are intraday + multi-day
aggregates, not raw observations. The certified `DefaultEvidenceBuilder` executes
identity-only (`core/msi/dra/default_evidence_builder.py:167-171`), so it raises on this
artifact's rules. This is **not** a Phase-5A coefficient defect; it is an evidence-supply
gap that Phase 6 inherits and must resolve as research tooling (§4).

---

## 4. Evidence-Construction Strategy (Phase-6 forward risk)

**Why the transforms are non-identity (and must stay so).** The four dossier features are
not raw observations: `RV^{(d)}` aggregates ~375 intraday 1m log-returns into a daily
realized volatility; `RV^{(w)}` and `RV^{(m)}` are trailing 5- and 22-day means of that
daily series; only `VIX_t` is a single close. Mislabeling them `identity` to satisfy the
builder would be dishonest about what the evidence represents. The declared transforms are
the faithful description; the gap is in evidence *supply*, not evidence *declaration*.

**Why this is not a Phase-5A defect.** Phase 5A's brief was to *author the artifact*
(frozen coefficients + deterministic `evaluate()` + MSI-007 shape). That is complete and
the math is cleared by review. Evidence supply for a research artifact has always lived in
research tooling (the same category as `core/msi/msrp/forward_vol.py`), not in the
platform runtime.

**Resolution path for Phase 6 (must NOT breach the charter scope fence).** The charter
(`MSRP_PHASE0_CHARTER.md` §7) forbids runtime/engine changes: *"MSI, the DRA, and the
execution stack are frozen and sufficient. MSRP changes the artifact, not the platform."*
Therefore Phase 6 / A2 **must not** extend `DefaultEvidenceBuilder`, the
`DuckDBObservationReader`, or add a spanning-read path. Instead, evidence for the held-out
window is constructed by **offline research tooling** (extending
`core/msi/msrp/forward_vol.py` — RV series → HAR aggregates → `Evidence` DTOs) and fed to
`ForwardVolatilityArtifact.evaluate()` exactly as the tests already do. This keeps the
platform frozen while still producing real `KnowledgeObject`s for the head-to-head.

**Dossier §5.2 optimism, recorded (not edited).** The frozen dossier asserts "single-date
`DuckDBObservationReader` reads suffice … no spanning-read engineering." The hypothesis is
point-in-time *correct*, but its features still require intraday + multi-day aggregation
the certified single-date reader/builder do not provide. The dossier is frozen and cannot
be edited; this mismatch is handled by the Phase-6 offline evidence-construction step
above and recorded here so it is not mistaken for an oversight.

**Boundary test.** `TestEvidenceConstructionBoundary::test_certified_builder_rejects_non_identity_transforms`
pins this constraint in the test suite so it is not rediscovered in Phase 6.

---

## 5. Post-Fix Verification

- **Phase-5A tests:** 44/44 pass (42 original + F2 timestamp test + F1 boundary test).
- **Full MSI suite:** 328 passed, 0 failed (284 existing untouched + 44 Phase-5A).
- **Coefficients:** unchanged by all fixes (verified bit-identical).
- **No existing production files modified** by the fixes other than the regenerated
  `core/msi/artifacts/forward_vol_v2/model.py` (F2 timestamp logic only) and its
  recomputed `checksum.sha256`.

```
$ python -m pytest tests/msi/
============================= 328 passed in 7.48s =============================
```

---

## 6. Files Touched by the Review-Fixes Phase

| Path | Change |
|---|---|
| `scripts/msrp/build_forward_vol_artifact.py` | F2: removed `_SENTINEL_TS` floor in the `evaluate()` template; `evaluation_timestamp = max(e.construction_timestamp for e in evidence)`. |
| `core/msi/artifacts/forward_vol_v2/model.py` | Regenerated from the corrected template (coefficients unchanged). |
| `core/msi/artifacts/forward_vol_v2/checksum.sha256` | Recomputed (model.py content changed by the F2 fix). |
| `tests/msi/msrp/test_forward_vol_artifact.py` | F3: added the timestamp-correctness test and the evidence-builder boundary test. |
| `docs/implementation/msrp/reports/MSRP_Phase5A_implementation_addendum.md` | This addendum (new). |

---

*End of addendum. Review-fixes only — certification and governance remain separate
governed acts.*
