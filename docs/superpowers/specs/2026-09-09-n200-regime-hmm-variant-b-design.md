# N200 Per-Stock Regime Classifier — Variant B (volatility-only) Design Spec

**Date:** 2026-09-09
**Branch:** `feat/n200-regime-hmm`
**Status:** pre-registered. Frozen before any Variant B fold is fitted.
**Parent:** `2026-09-09-n200-regime-hmm-design.md` (Variant A). **Everything in the parent holds unchanged except §5 (features) and §9 (artifact paths).** This document states only the deltas and the disclosures; it does not restate the parent, so the difference between the two constructs is auditable as a diff rather than a re-read.

---

## 1. Why Variant B exists

Variant A's primary gate failed decisively: Brier skill **−0.6304** against the trailing base rate and **−0.4119** against persistence, negative in **10 of 10** folds, ECE **0.3526** against a 0.05 threshold (`N200_REGIME_EVALUATION.md`).

The diagnosis is structural, not numerical. Variant A's fitted emissions separated on **direction**:

| separation | magnitude |
|---|---|
| drift, S1 vs S2 | **2.4 sigma** |
| volatility, S0 vs S2 | **0.26 sigma** |

`P(S_2)` was a down-trend probability being scored against an unoriented forward-volatility target. The canonical ordering sorted on the weakest available axis. Sanity A passed 10/10 and sanity C passed, so the latent structure is real and the transition dynamics earn their parameters — the states simply describe something other than what the gate asks about.

**Variant B removes every axis on which EM could prefer direction or trend shape, leaving volatility as the only structure available to separate on.**

## 2. The delta — §5 features

Variant A used four features: `gk_vol_z`, `gk_ratio_st`, `ker_20`, `drift_t`. Variant B uses three, all volatility:

| Feature | Definition | Purpose |
|---|---|---|
| `gk_vol_z` | `log(GK²_t / median(GK²) over trailing 252 sessions)` | volatility level, unchanged from A |
| `gk_ratio_st` | `log(mean(GK²) over 5d / mean(GK²) over 60d)` | short-horizon expansion, unchanged from A |
| `gk_ratio_med` | `log(mean(GK²) over 20d / mean(GK²) over 252d)` | **new** — medium-horizon expansion, replacing the two dropped features |

**Dropped, and why each:**

- **`drift_t`** — the only signed feature, and the one that produced the 2.4-sigma directional split. Removing it is the explicit instruction and the core of the variant.
- **`ker_20`** — dropped although it is *unsigned*, and this is the judgement call in this spec. Kaufman's efficiency ratio measures trend **shape**, not volatility. It was Variant A's second-strongest separator (−0.83 chop vs +0.76/+0.67 trending). Retaining it while dropping drift would most likely collapse up-trend and down-trend into a single "trending" state and let EM separate on efficiency instead — leaving volatility once again the weakest axis and the canonical ordering once again sorting on a thin margin. That is Variant A's failure mode with direction removed, and it is worth avoiding by construction rather than discovering a second time.
- **`gk_ratio_med` added** to keep three features supporting three states. Two features would leave K=3 thinly identified; the medium-horizon term is the natural third volatility axis and is not a new *kind* of quantity.

Everything else about §5 is unchanged: trailing-only windows, the same GK definition, the same per-entity GK floor at the 1st percentile of its own non-zero GK from the fit window, winsorization at ±3 sigma and standardization with fit-window moments only.

## 3. The delta — §9 artifact paths

Variant B writes to separate paths so Variant A's artifacts are never overwritten and the two remain comparable:

```
data/features/n200_regime/regime_panel_b.duckdb
data/features/n200_regime/params_b/fold_{year}.json
docs/reports/index_research/N200_REGIME_VARIANT_B_EVALUATION.md
```

`data/features/n200_regime/panel.duckdb` is **reused unchanged**. It carries OHLC, GK, membership and sequence ids but deliberately no features, so it is variant-independent — the reason the parent stopped at GK.

## 4. Unchanged from Variant A

Stated explicitly so nothing is silently re-specified: the panel and universe (§4), the model (§6 — K=3, shared transition matrix, diagonal covariance, log-space Baum-Welch, canonical ordering ascending by `gk_vol_z` emission mean), causal inference (§7 — forward filter only), the fold structure and barrier (§8 — expanding annual folds 2017–2026, parameters from data ending 31 December T−1, covering the GK floor, winsorization bounds and standardization moments), the acceptance gate and every threshold (§10), the tests (§11), and the risk register (§14).

**The seed is unchanged (20260909) and the ordering feature is unchanged.** No knob moves except the feature set.

## 5. Prior exposure and multiplicity — disclosed

**The §10 gate has now been run once, on the same panel, against the same target.** Variant B is the second construct in this family: **m = 2**.

- Thresholds are **kept identical** to Variant A, deliberately, so the two results are directly comparable. Brier skill is not a p-value and there is no principled Bonferroni-style deflation for it; inventing one after seeing Variant A fail would itself be a post-hoc move.
- **Variant B's feature choice was motivated by Variant A's fitted emission parameters, not by its gate metric.** The distinction matters: the change responds to *what the states turned out to describe* (a 2.4-sigma directional split), not to a search over what might score better on Brier. No feature was selected by trying it against the gate.
- **A Variant C would compound this**, and the deflation problem gets real rather than notional at m = 3. If Variant B fails, the correct reading is that the volatility-regime construct family has a deeper problem than feature contamination — not that a third feature set deserves a turn.
- The gate target remains forward *volatility*, so Variant B still reads no forward return, still needs no RFA declaration, and still leaves the 2023–2026 sealed return window unspent.

## 6. Pinned prediction, stated before the run

Per repo convention, the falsifiable claim comes before the numbers.

**If the diagnosis in §1 is correct**, Variant B's fitted emissions should show volatility separation between S0 and S2 on `gk_vol_z` of **at least 1.0 sigma** — versus 0.26 in Variant A — and the canonical ordering should then be sorting on the strongest axis rather than the weakest. Reliability should improve materially from ECE 0.3526, and the extreme-bin pileup (94% of Variant A's observations sat in `[0.0,0.1)` or `[0.9,1.0)`) should thin out.

**Two failure modes are distinguishable in advance, and the report must say which occurred:**

1. **Separation improves but calibration still fails** — the states are genuinely volatility-flavoured and still do not predict the forward tercile. That indicts the *target's predictability*, and closes the family: a well-separated volatility HMM that cannot beat "this stock has been volatile lately" means the persistence baseline already contains the information.
2. **Separation does not improve** (S0-to-S2 `gk_vol_z` gap stays below 1.0 sigma) — three collinear volatility features failed to identify three distinct variance states, which is a specification problem with this feature construction rather than a finding about markets.

**What would falsify Variant B:** the same condition as Variant A — Brier skill at or below the persistence baseline. Beating the base rate is not sufficient and never was.

## 7. Known risk specific to this variant

`gk_vol_z`, `gk_ratio_st` and `gk_ratio_med` are all built from the same GK series and two of them share the 252-session baseline, so they are **more collinear than Variant A's feature set**. Under diagonal covariance, correlated features are effectively counted more than once, and the states may end up identified almost entirely by volatility *level* with the two ratio features contributing little independent information. The empirical correlation matrix of the three features on the fit window is to be reported in the evaluation, whatever the gate outcome — it is the diagnostic that distinguishes failure mode 2 from a genuine finding.

## 8. Deferred work — unchanged

The DayType repair (three defects, `REGIME_DETECTION_SPEC_AUDIT_2026-09-09.md`) remains queued behind this build, sequenced reproducibility-first. Variant B does not change that ordering, and no part of either variant should be reused to "fix" DayType by substitution.
