# GEX Regime Stage A — TRAIN review (hand-written interpretation)

**Date:** 2026-09-23 · **Branch:** `research/options-hedging-scenarios`
**Reads:** `GEX_REGIME_STAGE_A_TRAIN.md` (script-generated, commit `0222caa`), `GEX_REGIME_STAGE_A_TRAIN_CHECKS.md`,
`GEX_REGIME_STAGE_A_HOLDOUT_CHECKS.md`. Spec: `docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md`.
The numbers below are quoted from those reports; nothing is recomputed here.

## 1. Result

TRAIN 2016-02-11 → 2019-12-31, n = 953: **b(N) = −1.19, NW t = −3.20 → PASS** under the pre-written rule
(b < 0, t ≤ −2.0). Moving N from its p10 to p90 lowers next-day Parkinson RV relative to VIX-implied variance by
~20 %. The descriptive variants agree in sign: sign-only S (t −2.84), flip distance D (t −3.68), close-to-close
outcome (t −3.77).

corr(N, ln VIX) = +0.11, so N is **not** a proxy for the vol level — it carries information that VIX, trailing RV5
and RV20 do not.

## 2. What the PASS is built on — set before HOLDOUT is read

- **2016–2018 (monthly-only chains) carries it:** b = −1.46, SE ≈ 0.44, n = 711.
- **2019 (first weeklies year) is underpowered, not contradictory:** b = −0.23, SE ≈ 0.94, n = 242. The gap to
  2016–18 is ~1.2 SE; 2019 cannot reject the earlier effect, nor confirm it.
- **The chain changed shape in 2019:** median kept strikes 44 → 103, expiries per day 1–2 → 4. HOLDOUT 2020–22 is
  entirely the weekly structure (127–285 strikes, 4–6 expiries per day), which is the structure that exists today.
  **HOLDOUT is therefore the real test of the current market**, not a formality.

## 3. What was validated — and what was not

Under the assumed sign convention (calls +, puts −), N is a gamma-weighted share of near-spot call OI minus put OI.
TRAIN shows **that predictor** carries information about realized-vs-implied variance beyond vol level.

It does **not** show that dealer hedging is the mechanism. Call-heavy near-spot OI after rallies (and put-heavy OI
after sell-offs) would give the same sign through a positioning/sentiment channel with no dealer story at all. Stage
B's proposed adjustments ("reposition on dealer flows") assume the dealer mechanism; if HOLDOUT passes, Stage B
should be designed on the predictor, not on the narrative.

## 4. HOLDOUT readiness

- Pre-run checks clean: 744 / 748 days computed; forward/close median 1.0006–1.0016; flip censored 4 % in 2020
  (COVID), 0 % after. N's median sits higher in 2021–22 (+0.08) than in TRAIN (~+0.01); the model is on the
  coefficient, not the level.
- **Code is frozen at `c1ccd45`** for the HOLDOUT fit. Any change to `core/analytics/gex_history.py` or
  `scripts/gex_regime/run_stage_a.py` after TRAIN is a re-specification (spec §7).
- HOLDOUT is one-shot and operator-triggered: `python scripts/gex_regime/run_stage_a.py --window holdout`
  (it refuses unless the TRAIN report records PASS). 2023+ stays unread.
