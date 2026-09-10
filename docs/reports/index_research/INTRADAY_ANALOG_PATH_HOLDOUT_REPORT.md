# Intraday Analog Path — HOLDOUT Report (terminal)

**Branch:** `research/intraday-analog-path` · **Date:** 2026-09-09
**Fence:** HOLDOUT 2019–2022, 981 eligible sessions, run **once** at the frozen
methodology (config seal `cd3d5149…` unchanged since the TRAIN run; no
parameter, representation, distance, K, tolerance, or horizon was altered).
**SEALED:** locked, unread, unspent.
**Artefacts:** `data/analog_path/phase1b_holdout_grid.json`,
`analogue_records_holdout_{A,B,C}_K{K}.parquet`.

---

## 1. Frozen-methodology confirmation

The runner was made fence-parameterizable (`--fence train|holdout`) — the
frozen validation step, not a methodology change. Re-running TRAIN through
the same code path reproduces the TRAIN grid; HOLDOUT was executed exactly
once.

## 2. Baselines (walk-forward, HOLDOUT)

| Horizon | return-only corr | return-only dir acc |
|---|---:|---:|
| 13:00 | +0.108 | 0.503 |
| 13:30 | +0.124 | 0.497 |
| 14:00 | +0.097 | 0.518 |
| 15:00 | +0.159 | 0.533 |
| close | +0.125 | 0.528 |

The return-only conditioning **strengthened out-of-sample** (TRAIN close corr
+0.059 → HOLDOUT +0.125; the COVID-era window carries more drift for R to
capture). This confirms Q1 from the protocol: the open→12:30 return does
carry post-12:30 information.

## 3. Analogue forecasts (full 60-cell grid in the artefact)

- Raw forecast–realized correlations: mostly |corr| < 0.10 across cells; the
  best block is representation A at close (+0.041…+0.071), which exceeds the
  randomized-matching null (p = 0.048/0.020/0.035 at K=5/20/50) and the
  block-shift null (A_K20 +0.071 vs p95 +0.059).
- **However**, the frozen central test absorbs exactly this: in
  `realized ~ [1, analogue_f, R]`, β_analogue is insignificant in **all 60
  cells** (A-close t ≤ +0.72; the largest t anywhere is ≈ +2.3 in two
  scattered C cells — far below the multiplicity-corrected bar for a
  60-cell grid). The A-close correlation is carried by the path's **endpoint
  (R)**, not by path shape: once R is controlled, nothing remains.

## 4. The central question — path beyond return?

**NO.** On HOLDOUT, exactly as on TRAIN, the path adds no detectable
incremental information beyond the open→12:30 return. ΔR² ≤ 0.38 pp in every
cell; no β_analogue survives Newey-West inference; the scattered C-cell
positives (h14/h15, t≈2.1–2.3) are inconsistent across K and horizon and
consistent with chance under the 60-cell multiplicity.

## 5. Same-return/different-path control (±10 bp, frozen)

882 matched groups (COVID-era return dispersion → mean group 57, median 50):

| Horizon | TRAIN diff (NW t) | HOLDOUT diff (NW t) | Permutation status (HOLDOUT) |
|---|---:|---:|---|
| 13:00 | −0.96 bp (−5.07) | −1.15 bp (−4.88) | ≈ −1.6σ, inside [p5, p95] band |
| 13:30 | −1.20 bp (−4.79) | −1.35 bp (−4.29) | ≈ −1.9σ, inside band |
| 14:00 | −0.19 bp | −0.37 bp | null |
| 15:00 | +0.64 bp | −0.50 bp | null |
| **close** | **+2.37 bp (+3.47)** | **−0.04 bp (−0.54)** | null |

**The TRAIN close-horizon +2.37 bp shape premium did not survive.** The
30–60 min shape reversal is directionally consistent across both windows
(~1 bp, near-shape slightly underperforming) but sits at the edge of its
within-group permutation band and is economically negligible. As instructed,
the intriguing secondary result was not pursued.

## 6. Null tests (HOLDOUT, 1,000 iterations, seed 42)

- Randomized matching: A-close cells p = 0.020–0.048 (the only sub-0.05
  cells of 20), fully absorbed by R in the controlled regression.
- Block-shift (close): A cells exceed the band raw, again subsumed by R.
- Sign-permutation (dir acc): all cells within the null band.

## 7. Leakage and discipline

Every HOLDOUT date was fence-asserted; pool construction uses only dates
strictly before D (positions < i — within the HOLDOUT list the pool is the
expanding HOLDOUT history itself plus nothing else, per the frozen
walk-forward rule); selection is state-only, outcomes gathered
post-selection; SEALED forward outcomes were never read; the ledger records
the HOLDOUT rows with `used_for_methodology_decision=false`.

## 8. Verdict

**NO EVIDENCE — the historical-analog hypothesis is substantially falsified
in this formulation.**

- Q1 (does R predict post-12:30?) — **YES** (weak, and stronger OOS).
- Q2 (does the 09:15→12:30 path add information beyond R?) — **NO**, in both
  TRAIN and HOLDOUT, across 2 primary + 1 diagnostic representation, 4 K
  values, 5 horizons (120 cells total), under Newey-West inference and three
  null families.
- Q3 (do analogues beat return-only conditioning?) — **NO**.
- Q4 (does anything survive chronological validation?) — **NO**: the only
  TRAIN-side candidate (the +2.4 bp close shape premium) vanished; the
  30–60 min reversal is marginal and economically nil.
- Q5 (SEALED) — **NOT EVALUATED.** Per the frozen termination mapping
  (HOLDOUT fail → construct retired, SEALED untouched), the 2023-01-01 →
  present window (885 eligible sessions) remains **locked and unspent**.

## 9. What this means

The 09:15→12:30 path shape of the NIFTY 50 does not contain predictive
information about post-12:30 returns beyond the open→12:30 return, in this
formulation (15-min grid, Euclidean analogue matching, K∈{5,10,20,50},
2012–2022 walk-forward evidence, 2023+ preserved). The market's "journey to
12:30" reduces, for forecasting purposes, to where it arrived. The
return-only baseline is the genuine (if weak) signal this investigation
confirms — consistent with the A-track's opening-drive finding and the
Phase 1A OLS result. Recommendation: close the construct; do not re-open
with new distances/features; any successor starts its own pre-registration.
