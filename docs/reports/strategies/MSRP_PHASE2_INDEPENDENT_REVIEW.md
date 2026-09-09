# MSRP Phase 2 — Independent Model Review

**Document type:** Institutional-style independent critique (Phase 2 of the Market
State Research Program), as defined in `MSRP_PHASE0_CHARTER.md` §6.

**Subject under review:** `docs/reports/MSRP_PHASE1_RESEARCH_DOSSIER.md` (the
forward-volatility-regime pre-registration) and, through it, the reference fixture
it proposes to beat.

**Reviewer stance:** adversarial / review-board. The objective is to find flaws in
the pre-registration **before** it is frozen, not to ratify it. A pre-registration
is the one artifact whose defects are cheapest to fix now and most expensive after
the immutable freeze.

**Date:** 2026-07-06

**Charter lenses applied:** hidden assumptions · leaking features · unstable labels ·
causal vs. merely-predictive variables · unmodelled uncertainty.

---

## Verdict

**PASS WITH REQUIRED REVISIONS.**

The pre-registration is scientifically sound in structure and exemplary in
discipline (sealed held-out, decision table fixed in advance, scientific-claim /
engineering-deliverable separation). It is **not yet safe to freeze**: one finding
(**M2 — bootstrap method**) is an outright methodological error that would bake an
anti-conservative test into an immutable document, and three others (**M1, M3,
Mo2**) require pre-registered additions to make the stated Scientific Claim
actually testable and honest.

Freeze should proceed **only after** the M2/M3/Mo1/Mo2/Mi1 revisions are applied
(they strengthen the pre-registration without touching the operator's D3 gate).
**M1** is flagged for an operator decision because it concerns the D3 baseline.

---

## Findings (ranked)

### M1 — The pre-registered comparison does not, by itself, test the Scientific Claim *(hidden assumptions; causal-vs-predictive)*

**Severity: Major (operator decision required).**

§2.1 claims HAR-RV+VIX beats "what the VIX level **alone** provides." But the
pre-registered gate (§3.2, per charter D3) scores the fixture by its **3-level
bucketed** `market_regime` ∈ {0,1,2} (VIX thresholds 15 / 25). Bucketing discards
almost all of VIX's information. Beating a 3-level VIX bucket by ≥0.03 AUC is a
materially weaker result than beating VIX itself — and VIX_t is already one of the
candidate's own regressors. A candidate could clear the gate while adding **nothing**
over continuous VIX, leaving the §2.1 claim unsupported.

**Required revision:** add a **secondary reference arm — raw continuous `VIX_t` as
a discriminant score** — and pre-register reporting of `ΔAUC` against *both* the
fixture (the D3 gate) and raw VIX. The fixture stays the pre-registered **gate**
(operator-decided, charter-recorded); raw-VIX ΔAUC becomes the evidence that
substantiates §2.1. Making raw VIX the *primary* gate would require an operator
amendment to charter D3 — **this review does not recommend that unilaterally; it
surfaces the choice.**

### M2 — Day-level bootstrap is invalid under autocorrelation *(unstable labels; unmodelled uncertainty)*

**Severity: Major (must fix before freeze).**

§8 specifies "resample **days** with replacement." Both the candidate score
(realized vol is highly persistent) and the label (`Y_t` depends on a trailing-20d
median → serially correlated) are strongly autocorrelated. An i.i.d. day-level
bootstrap **understates** CI width, producing false "CI excludes 0" approvals — the
exact failure the CI is meant to prevent. Freezing this would immortalize an
anti-conservative test.

**Required revision:** replace the day-level bootstrap with a **moving-block
bootstrap** (contiguous blocks; pre-register a block length on the order of the vol
autocorrelation scale, e.g. 10 trading days, chosen on the **dev** window, never the
held-out). Pin the block length and replicate count `B` alongside the seed (§1.1).

### M3 — Label base-rate drift makes AUC partly a persistence score, and warns on power *(unstable labels)*

**Severity: Major (must fix before freeze — reporting + power caveat).**

`Y_t = 1[RV_{t+1} > trailing-20d median]` has a **drifting base rate**: in rising-vol
stretches `Y≈1` persistently; in falling-vol stretches `Y≈0`. Consequences: (a) AUC
can be inflated by a model that merely tracks vol *persistence* rather than
forecasting regime *change*; (b) the effective sample size over ~120 held-out days
is **far below 120**, so the `ΔAUC ≥ 0.03` + block-bootstrap-CI-excludes-0 bar is
likely to land on "inconclusive" (§10 row 2) rather than approval.

**Required revision:** pre-register reporting of the held-out **base rate and its
run-structure**, and state the power limitation explicitly in Threats to Validity
(§11) so an "inconclusive" outcome is understood in advance as an expected,
non-failing result rather than a disappointment to be explained away.

### Mo1 — "Causal" overclaims *(causal vs. merely-predictive)*

**Severity: Moderate.**

§4 asserts the latent variable is "causal, not merely predictive." HAR RV-lags and
VIX are **structurally-motivated predictors** (volatility persistence; option-implied
expectations), not manipulable causes; the model is a reduced-form regression. The
economic mechanism (vol clustering) *motivates* the predictors but does not make the
regression causal.

**Required revision:** soften §4 to "structurally-motivated forecasting variable."
Keep the economic-mechanism argument as motivation for *why the predictor should
generalize* — that is its legitimate role.

### Mo2 — Uncertainty is unmodelled where it matters and untested by the gate *(unmodelled uncertainty)*

**Severity: Moderate (must fix scope before freeze).**

(a) Emitted `uncertainty` = **homoskedastic** dev residual std; RV is heteroskedastic
even in logs, so the uncertainty will be mis-scaled precisely in high-vol states —
where a volatility consumer cares most. The dossier marks the heteroskedastic
refinement **"optional,"** yet **Calibration is a mandatory MSI-006 domain** (§9);
optional-ness contradicts the validation plan. (b) The AUC gate never uses
`uncertainty`, but the MM13 consumer **does** (it gates signals on value +
uncertainty) — so a mis-calibrated uncertainty can pass the gate and still degrade
downstream decisions.

**Required revision:** move calibrated (state-dependent) uncertainty in-scope for the
Phase-5 artifact, and pre-register a **Calibration acceptance check** (e.g. held-out
prediction-interval coverage within a stated tolerance, reported once, not tuned) as
part of the §9 Calibration domain.

### Mo3 — Parameter-estimation uncertainty ignored *(unmodelled uncertainty)*

**Severity: Minor.** Emitted uncertainty reflects residual noise only, not
coefficient (`b0…b4`) estimation uncertainty. Acceptable for a frozen artifact;
**note it** in §12 as a known simplification.

### Mi1 — Bootstrap replicate count unspecified *(reproducibility)*

**Severity: Minor.** §8 pins the seed but not `B`. Pin `B` (e.g. 10,000) in §1.1 —
pre-registration requires the full procedure, not just its seed.

### Mi2 — Construct mismatch: overnight-excluded RV vs. overnight-inclusive VIX *(assumptions)*

**Severity: Minor / note.** `RV_t` excludes the overnight return (§5) while VIX prices
overnight-inclusive expectations. Defensible (intraday RV is the target construct),
but **note** the mismatch in §12 so it is not mistaken for an oversight.

---

## What passes (not merely absent problems)

- **Feature and label timing are genuinely leak-free.** Every feature and the
  threshold `M_t` use only data through the close of day `t`; the outcome `RV_{t+1}`
  is the only forward quantity. Verified against §3.1 / §5 / §6 — no leakage found.
- **Pre-registration discipline is exemplary** — sealed held-out, decision table
  fixed before results, explicit falsification conditions.
- **Scientific-claim / engineering-deliverable separation (§2.1 / §2.2)** correctly
  prevents "we built it" from being read as "it's true."
- **Parsimony (5 coefficients)** is appropriate to the ~750-observation dev sample
  and directly answers the prior art's non-stationarity lesson.
- **The prior-art cautionary lesson is carried, not ignored** (§11 external validity
  cites the DRA non-stationarity failure).

---

## Disposition

| Finding | Class | Action before freeze | Needs operator? |
|---|---|---|---|
| M1 | baseline / claim | Add secondary raw-VIX arm + reporting | **Yes** (touches D3 framing) |
| M2 | test invalid | Block bootstrap; pin block length + `B` | No |
| M3 | label drift / power | Report base rate; state power caveat | No |
| Mo1 | overclaim | Soften "causal" → "structurally-motivated predictive" | No |
| Mo2 | uncertainty scope | Calibrated uncertainty in-scope + acceptance check | No |
| Mo3 | uncertainty | Note parameter-uncertainty simplification | No |
| Mi1 | reproducibility | Pin `B` | No |
| Mi2 | construct | Note overnight/VIX mismatch | No |

**Recommendation:** apply M2/M3/Mo1/Mo2/Mo3/Mi1/Mi2 to the dossier (they strengthen
the pre-registration and do not alter the D3 gate), obtain an operator decision on
M1, then — and only then — freeze and commit the dossier as the immutable Phase-1
baseline. Freezing before M2 is fixed would immortalize an anti-conservative test.

---

*End of independent review. This document evaluates; it does not itself
pre-register. Any change it induces is applied to the Phase-1 dossier before that
dossier is frozen.*
