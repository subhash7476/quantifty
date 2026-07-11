# MSRP Phase 5A — Independent Technical Review

**Document type:** Independent technical review of the Phase-5A implementation
(`ForwardVolatilityArtifact`, `PublishedArtifact v2`).

**Subject:** `docs/implementation/msrp/reports/MSRP_PHASE5A_IMPLEMENTATION_REPORT.md`
and the code it describes.

**Method:** source verification — the implementation was read directly and checked
against the frozen Phase-1 dossier (`d9233b1`) and the certified MSI contracts. Claims
in the implementation report were **not** taken on trust; each verdict below cites what
was read.

**Date:** 2026-07-06

---

## Verdict

**PASS WITH REQUIRED FIXES.**

The core research realization is faithful: the HAR-RV+VIX authoring math, the dev-only
fit, the held-out seal, and the log-normal point-estimate/uncertainty all conform to the
frozen dossier, and no research decisions were smuggled in. Two defects and one
architectural risk must be resolved before Phase 6:

- **F1 (Major, architectural):** the artifact's `evidence_rules` declare transforms the
  **certified evidence builder cannot execute** — the artifact is loadable and
  evaluatable on pre-built evidence, but **not evidence-buildable through the certified
  DRA pipeline**. The report's "certified-runtime compatibility" claim is overstated.
- **F2 (Moderate):** `evaluate()` mis-stamps `evaluation_timestamp` for all historical
  evaluations.
- **F3 (Minor):** the two above slipped because no test covers either surface.

None of these touch the frozen coefficients or the Phase-6 AUC score.

---

## Findings

### F1 — Evidence rules declare transforms the certified builder rejects *(Major; architectural; resolve before Phase 6)*

**Verified:** `core/msi/dra/default_evidence_builder.py:167-171` —
`transform = feature.get("transform", "identity"); if transform != "identity": raise …
"Unsupported transform"`. The certified `DefaultEvidenceBuilder` executes **identity
only**.

The artifact (`core/msi/artifacts/forward_vol_v2/model.py:53-87` and
`evidence_rules.json`) declares three **non-identity** transforms — `rv_intraday`,
`har_weekly_5d`, `har_monthly_22d` — plus `lookback_days: 22`. Consequences:

- The artifact **loads** (via `FilesystemArtifactLoader`) and `evaluate()` **works on
  hand-constructed `Evidence`** (which is all the 42 tests exercise).
- But the certified `ObservationReader → EvidenceBuilder` path **cannot build** this
  artifact's evidence: `DefaultEvidenceBuilder.build()` would raise on the first
  non-identity transform. The single-date reader also cannot supply a 22-day trailing
  aggregate or an intraday-aggregated RV.
- Therefore the report's §9 "Certified-runtime compatibility" and §10 "MSI runtime
  compatibility preserved" are **overstated**: *loadable* ✔, *end-to-end
  evidence-buildable* ✘.

**Scope note (fair to the implementer):** Phase 5A's brief was to *author* the artifact,
and the declared transforms are the *honest* description of what the dossier features
require. This is not a "5A did it wrong" coefficient defect. It is a **surfaced forward
risk the report should have flagged and did not**, and Phase 6 inherits it directly:
building evidence for these features **must not** be solved by extending
`DefaultEvidenceBuilder` or the reader — that is a runtime/engine change the charter
scope fence forbids ("MSI, the DRA, and the execution stack are frozen"). The defensible
path is a **Phase-6/A2 offline evidence-construction step as research tooling** (the same
category as `core/msi/msrp/forward_vol.py`), feeding pre-built `Evidence` to
`evaluate()` — exactly how the tests already operate. This tension also exposes that the
frozen dossier's §5.2 "point-in-time clean, no spanning-read engineering" was optimistic:
the hypothesis is point-in-time but still needs intraday + multi-day aggregation the
certified reader/builder do not provide. That cannot be edited now (dossier is frozen);
it must be handled by Phase-6 research tooling and recorded.

**Required action:** before Phase 6, document the evidence-construction strategy (offline
research tooling, not a platform change) and correct the implementation report's
runtime-compatibility claim to "loadable + evaluatable on pre-built evidence; evidence
construction is Phase-6 research tooling."

### F2 — `evaluate()` mis-stamps `evaluation_timestamp` *(Moderate; fix before Phase 6)*

**Verified:** `core/msi/artifacts/forward_vol_v2/model.py:104-109,137`:

```python
latest_ts = _SENTINEL_TS            # datetime(2026, 7, 3, 15, 30)
for e in evidence:
    ...
    if e.construction_timestamp > latest_ts:
        latest_ts = e.construction_timestamp
...
return MarketState(evaluation_timestamp=latest_ts, estimates=(estimate,))
```

`latest_ts` is initialized to the **future** sentinel `2026-07-03` and only advances if
evidence is *later*. For any evidence dated before 2026-07-03 — i.e. **every held-out day
except the last** — `evaluation_timestamp` is reported as `2026-07-03`, not the evidence's
actual date. The certified reference fixture (`tests/msi/fixtures/test_artifact/model.py`)
uses the correct pattern: `max(e.construction_timestamp for e in evidence)` with the
sentinel used **only** when evidence is empty. (Here the empty-evidence branch is
unreachable anyway — missing features raise `ValueError` first — so the sentinel serves
*only* as an erroneous floor.)

**Impact:** does **not** affect the frozen coefficients or the Phase-6 candidate score
(the AUC uses `Estimate.value`, not the timestamp). But it corrupts point-in-time
provenance: every held-out `KnowledgeObject` would carry `evaluation_timestamp =
2026-07-03`, and the `knowledge_id` (derived partly from `eval_timestamp`) would no
longer encode the evaluation date. Determinism is preserved, so the replay tests pass —
which is exactly why the bug is invisible today.

**Required action:** replace the floor logic with
`max(e.construction_timestamp for e in evidence)` (sentinel only for empty evidence),
mirroring the certified fixture.

### F3 — Test gaps that let F1 and F2 pass silently *(Minor)*

Per the report's own §4 test inventory: `TestEvaluate` and `TestPointInTime` assert
determinism, formula match, and "different evidence → different output," but **no test
asserts `evaluation_timestamp` equals the max evidence timestamp** (F2), and **no test
attempts evidence construction through `DefaultEvidenceBuilder`** (F1). Add both — the
second as an explicit *expected-failure / documented-boundary* test so the identity-only
constraint is captured, not rediscovered in Phase 6.

---

## What passes (verified by reading, not assumed)

| Area | Verification |
|---|---|
| RV construction (dossier §5) | `forward_vol.py:27-50` — `sqrt(Σ (1m log-return)²)`, intraday-only (per-day closes, no cross-day term), no annualization, `<2`-print days dropped. ✔ |
| HAR features (§6) | `forward_vol.py:53-68` — `rv_daily`, 5d-mean (`min_periods=5`), 22d-mean (`min_periods=22`), `dropna` warmup; four rejected features absent. ✔ |
| Model form + dev-only OLS (§7/§8) | `forward_vol.py:71-134` — `log RV_{t+1}` on `[1, log RV_d, log RV_w, log RV_m, log VIX]`; `lstsq` closed form (no solver DoF); design filtered to `[dev_start, dev_end]`. ✔ |
| Held-out seal (§1/§8) | `forward_vol.py:104` — `rv.loc[rv.index <= dev_end].shift(-1)` clamps the target to the dev window; the last dev day contributes no row. ✔ |
| VIX join (§12.2) | `forward_vol.py:95-98` — `reindex` + `dropna` (holiday mismatch dropped, no ffill). ✔ |
| Point estimate + uncertainty (§7 / Mo2) | `model.py:121-129` — `value = exp(μ + σ²/2)`; `uncertainty = value·sqrt(exp(σ²)−1)` = the correct log-normal SD; level-scaled → widens in high-vol, conforming to the dossier's "scaled by predicted level." ✔ |
| Coefficients frozen + consistent | `model.py:28-34` — five positive coefficients (VIX largest, 0.476; economically consistent with Corsi 2009), `SIGMA`, `N_OBS=700`, as module literals. Report's fitted-not-tuned claim consistent with the closed-form fit. ✔ |
| Loader governance claim (report §8.6) | `filesystem_artifact_loader.py:180-192` — status checks raise only when the field is *present and wrong*; omitting `validation_status`/`lifecycle_state` loads as "not yet governed." `validation_id` is `…-pending` (correctly **not** Approved pre-certification). Claim is honest. ✔ |
| Phase-2 revisions | Mo2 (state-dependent uncertainty) implemented; Mo1 already in dossier; M1/M3 correctly deferred to Phase 6; Mo3 recorded in provenance. ✔ |
| No research decisions / additive only | The seven §8 items are genuinely implementation-level (solver, dimension label, feature names, location, derived uncertainty formula, target clamp, omitted governance fields); zero existing files modified. ✔ |

The regression claim (284 existing + 42 new green) is plausible and consistent with the
additive-only change set; it was not independently re-executed in this review.

---

## Disposition

| Finding | Severity | Action | Blocks Phase 6? |
|---|---|---|---|
| F1 | Major (architectural) | Document offline evidence-construction tooling; correct the report's compatibility claim; do **not** touch the frozen builder/reader | **Yes — must be planned** |
| F2 | Moderate | Fix `evaluation_timestamp` to `max(evidence ts)` | Yes — fix first |
| F3 | Minor | Add timestamp + evidence-builder-boundary tests | With F1/F2 |

**Recommendation:** the Phase-5A *artifact math* is sound and conformant and can stand;
F2 is a trivial correctness fix; F1 is the substantive one — it is not a coefficient
defect but it decides how Phase 6 builds evidence without breaching the charter scope
fence, and it must be resolved (as research tooling) before the A2 harness runs. This
review does **not** certify the artifact; it clears the math and flags the integration
gap.

---

*End of independent technical review. Evaluation only — certification and governance are
separate governed acts.*
