# Intraday Analog Path — Phase 1B TRAIN Report

**Branch:** `research/intraday-analog-path` · **Date:** 2026-09-09
**Fences:** TRAIN 2012–2018 only (1,687 eligible sessions; HOLDOUT and SEALED untouched)
**Config seal:** `cd3d5149244c9ed6c5684153f30bedf4a160184375bdc4bb18d6c73dedc8a81d`
**Artefacts:** `data/analog_path/phase1b_train_grid.json`, `analogue_records_train_{A,B,C}_K{K}.parquet`, `plots/examples.json`

---

## A. Analogue methodology (exact)

- **States (frozen):** A = 14-dim normalized path `P(t)/P(09:15)−1` (first element 0);
  B = 13-dim simple interval returns; C = 14-dim linear detrend of A,
  `C(t) = A(t) − (t/13)·A(12:30)` (endpoints exactly 0; endpoint magnitude removed —
  **diagnostic only**). Both A and B contain endpoint magnitude (§4 disclosure).
- **Distance:** Euclidean on each state, separately.
- **Walk-forward pool:** for query day D at position i, pool = eligible days
  strictly before D. Selection = ascending Euclidean distance; K ∈ {5,10,20,50}
  nearest (pool ≥ K required; ~0–50 early days flagged pool-too-small).
- **Outcome access:** strictly after selection — `select_analogues` receives the
  state matrix only; outcomes are gathered by the caller afterwards (structural
  causal ordering; mutation-invariance tested).
- **Forecasts (all causal, expanding):** baseline = expanding mean of pool
  outcomes; return-only = expanding OLS of outcome on open→12:30 return evaluated
  at D's R; analogue = mean (and median) of the K selected analogues' outcomes.
- **Inference:** Newey-West t (lag 5), moving-block bootstrap CI (blocks of 5),
  empirical nulls (1,000 iterations, seed 42), two-sided empirical p.
- **Grid:** 3 representations × 4 K × 5 horizons = 60 cells; all reported; no
  cell dropped, no threshold added.

## B. Similarity diagnostics

| Representation | ref-percentile median | frac > 50th pct | frac > 90th pct |
|---|---:|---:|---:|
| A (path) | 0.003 | 0.5% | 0.1% |
| B (intervals) | 0.003 | 2.4% | 0.3% |
| C (shape) | 0.003 | 0.8% | 0.1% |

The nearest analogue typically sits at the **0.3rd percentile** of the
distribution of distances between historical days — i.e., "nearest neighbour"
genuinely means *similar* for ~97–99.5% of query days; weakly-matched days
(percentile > 50%) are rare (0.5–2.4%). The system can therefore identify weak
matches; none were forced into predictions. *(Implementation note: the first
run's pool-rank percentile was degenerate by construction — the nearest is
always the pool minimum — and was replaced by this pair-distribution reference
percentile before any interpretation; disclosed, not a protocol change.)*

## C. Analogue forecasts (full grid in `phase1b_train_grid.json`)

Across all 60 cells the forecast–realized correlation ranges **−0.043 to
+0.047**; directional accuracy 0.48–0.52; MAE ≈ RMSE ≈ the unconditional sd at
every horizon. No cell is individually notable. Anchors: at K=50 the observed
correlation (+0.028, rep A close) equals the randomized-matching null mean
(+0.025) — a K=50 forecast *is* essentially the expanding mean, as it should be.

## D. Comparison with baselines (walk-forward, close horizon unless noted)

| Forecast | corr | dir acc | MAE |
|---|---:|---:|---:|
| Unconditional (expanding mean) | +0.028 | 0.477 | 39.9 bp |
| Return-only (expanding OLS on R) | **+0.059** | **0.552** | 39.6 bp |
| Analogue, best cell of 12 (close) | +0.039 (A_K5) | 0.520 (A_K50) | ~40 bp |

The return-only baseline is the only forecast with real skill (consistent with
Phase 1A's OLS slope t=3.15 on R). The analogue forecast does not beat it in
any cell. Calibration quintiles (A_K5/close) show **no monotonicity**: mean
forecast −36 bp → realized −2 bp; +36 bp → realized 0 bp. The forecast buckets
carry no realized-return information.

## E. Path incremental value — the central test

Return-controlled regressions `realized ~ [1, analogue_forecast, R]` with NW
SEs, all 60 cells: β_analogue insignificant everywhere (|t| ≤ 1.26; the two
largest are A_K20 and B_K50 with *negative* signs). ΔR² over the R-only model
≤ 0.15 pp in every cell. **On TRAIN, the 09:15→12:30 path adds no detectable
incremental information beyond the open→12:30 return at the forecast level.**
This holds for both primary representations and the shape diagnostic.

## F. Same-return / different-path control (±10 bp, frozen)

1,584 matched groups (mean size 107, median 89; each group = pool days within
±10 bp of the query's open→12:30 return; near/far split at the median State-C
distance within the group):

| Horizon | mean(near−far) | NW t | block-bootstrap 95% CI | permutation z (1,000) |
|---|---:|---:|---:|---:|
| 13:00 | −0.96 bp | −5.07 | [−1.3, −0.6] bp | ≈ −1.8 (p≈0.08) |
| 13:30 | −1.20 bp | −4.79 | [−1.7, −0.7] bp | ≈ −2.2 (p≈0.03) |
| 14:00 | −0.19 bp | −0.51 | [−0.9, +0.6] bp | ≈ −0.3 |
| 15:00 | +0.64 bp | +1.09 | [−0.5, +1.8] bp | ≈ +1.2 |
| close | **+2.37 bp** | +3.47 | [+1.1, +3.7] bp | ≈ +4.3 (p≈2e-5) |

Within endpoint-matched groups, shape-near days slightly **underperform** at
30–60 min and **outperform by ~2.4 bp to the close**. The close-horizon effect
survives the within-group permutation null comfortably; the 30–60 min reversal
hints are marginal (z≈2). Note the variance caveat: distance-sorting contracts
the observed per-group variance (7.5 bp/session vs 22 bp under the permutation
null) — itself consistent with shape–outcome association — so the permutation
null, not the parametric t, is the benchmark; it is passed at close and 13:30.

## G. Null tests (1,000 iterations, seed 42)

- **Randomized matching (all 20 (K, horizon) cells):** no observed correlation
  exceeds the null by more than ~1.7 null-sd; two-sided empirical p ≥ 0.094,
  most in 0.2–0.9.
- **Block-shift (close horizon, 12 cells):** every observed correlation lies
  within the null band [p5, p95]; the best (A_K5, +0.039) sits exactly at p95.
- **Sign-permutation (directional accuracy, close, 12 cells):** all observed
  within [0.478, 0.521] — indistinguishable from chance.
- **Excursion diagnostics (MFE/MAE analogue-forecast correlations +0.07 to
  +0.16) are reported WITHOUT nulls and are not interpretable as path
  information** — the K50 value partly reflects volatility clustering in
  overlapping expanding windows. Flagged, not claimed.

## H. Leakage verification (explicit)

- Selection is computed from the morning-state matrix only; outcomes are
  gathered post-selection (structural). Test: mutating the outcome matrix does
  not change selections.
- Query day and all future dates are excluded from the pool by construction
  (`idx < i`); tested for K ∈ {5,10,20,50} at multiple positions.
- Mutating future states does not change the query's similarity diagnostics
  (tested).
- Session state uses only the query day's own file (directory-isolation test).
- Fence guard: every loaded date asserted `train`; SEALED raises `FenceError`;
  artefacts contain TRAIN rows only; SEALED forward outcomes were never read.

## I. Visual examples

`data/analog_path/plots/` — three examples chosen **by similarity strata only**
(never by outcome): high (2012-01-10, ref pct 0.0), moderate (2012-10-15,
0.0025), weak (2014-05-16, 0.933). Each shows the query path (normalized,
black), its top-5 analogue morning paths, the 12:30 marker, and the analogues'
afternoon continuations. Note: I could not visually inspect the PNGs myself
(model limitation) — selection was rule-based; the files are there for the
operator's review.

## J. Research verdict

**WEAK — with the central forecast question answered NO EVIDENCE.**

1. The headline hypothesis — *does path-analogue conditioning improve
   post-12:30 forecasts beyond the open→12:30 return?* — is **negative on
   TRAIN**: no cell beats the return-only baseline; the return-controlled
   regression shows no incremental coefficient anywhere; forecast calibration
   is flat; all three null families fail to separate any observed statistic.
2. The one live finding is the same-return/different-path control: within
   ±10 bp endpoint-matched groups, shape proximity predicts a **+2.4 bp**
   close-return premium (permutation p≈2e-5) and a ~1 bp short-horizon
   reversal. This is a conditional *distributional* fact about historical
   days, at an economically negligible size (a 3.8 bp futures round-trip
   would consume it ~1.6× over), and it does not translate into forecast
   skill for the query day in the frozen grid.
3. This is TRAIN — the discovery surface. Nothing here was tuned to it. The
   frozen methodology is unchanged and can be validated one-shot on HOLDOUT
   exactly as-is if the operator wishes; the SEALED window remains locked.

**Answer to the five protocol questions (Phase 1A prompt) at the TRAIN stage:**
Q1 (does R predict?) — YES (weak, close horizon only). Q2 (does the path add
beyond R?) — NO EVIDENCE. Q3 (analogues better than return-only?) — NO.
Q4/Q5 — not yet asked (HOLDOUT/SEALED untouched).
