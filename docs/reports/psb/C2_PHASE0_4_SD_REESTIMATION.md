# C2 Phase 0.4 — SD Re-Estimation on Extended Dev Window

**Generated:** 2026-07-18 07:41 UTC

## Fence Assertion

| Check | Value |
|---|---|
| Computed MAX (formation window) | 2022-12-30 |
| Store actual MAX | 2026-07-09 |
| Fence holds | YES (differs from store MAX) |
| Dev window | 2010-01-04 → 2022-12-31 |
| PSB-2 baseline dev window | 2020-09-04 → 2022-12-30 |

## Extended Window Results

| Metric | Value |
|---|---|
| Grid dates in window | 311 |
| Scored formations (n) | 260 |
| Mean IC | 0.024563 |
| SD_IC | 0.104209 |
| t-statistic | 3.8006 |
| One-sided p-value | 8.999668e-05 |
| AC₁ (lag-1 autocorrelation) | -0.041441 |
| Net spread (annualized) | 0.7809% |
| Gross spread (annualized) | 3.0025% |
| Fee+slippage drag (bp/yr) | 235.8 |
| Turnover | 0.2767 |
| Power projection (n*=84) | 0.6907 |

Structural note: 311 grid dates, but 51 early formations (≈2010) lack a 252-day delivery baseline and produce no scores — statistics are computed on the 260 scored formations. The true sample growth from PSB-2 is 55 → 260, not 311.

## Gate G0 — Tolerance Evaluation

| Criterion | PSB-2 baseline | Extended w/ tolerance | Verdict |
|---|---|---|---|
| Mean IC | 0.0349 | 0.024563 | |Δ| ≤ 0.0201 | **PASS** |
| SD_IC | 0.0994 | 0.104209 | [0.0497, 0.1988] | **PASS** |
| Net spread | 4.57% | 0.7809% | > 0 | **PASS** |
| AC₁ | -0.1818 | -0.041441 | < 0 | **PASS** |

**G0 overall verdict:** **ALL PASS**

**Note:** AC₁ (-0.0414) did not exceed the 0.10 trigger; no Newey-West adjustment needed.

## Comparison to PSB-2 Baseline (n=55)

The PSB-2 C2 report on 55 fortnightly formations (2020-09-04 → 2022-12-30) reported mean IC = +0.0349, SD_IC = 0.0994, net spread = 4.57%, AC₁ = -0.1818.

The extended window (2010-01-04 → 2022-12-31, 311 grid dates, n = 260 scored) produces mean IC = 0.024563, SD_IC = 0.104209, net spread = 0.7809%, AC₁ = -0.041441.

**G0 verdict: PASS.** Mean IC and SD_IC are within pinned tolerances — the construct survives falsification on the extended window. But the headline is more qualified than the PSB-2 sample suggested:
- Mean IC fell ~30% (0.0349 → 0.0246), entirely within tolerance, but SD_IC was never the risk — mean IC was.
- Power at 0.69 is below the 0.80 the successor pre-registration needs for an n*=84 sealed read; the construct clears IC and SD consistency but does not project to clear a power hurdle.
- Net spread at 0.78% clears the trivial `>0` bar but left 3.79 pp on the table vs the PSB-2 4.57% estimate.
- AC₁ −0.04 is benign — below the 0.10 trigger, below the PSB-2 −0.18 — the autocorrelation threat did not materialize with a larger sample.

These are the facts the C2-VAL pre-registration must own. C2 is not vindicated — it is bounded.

---
*All numbers script-generated. C2 parameters frozen from PSB-2 protocol. Sealed window (2023-01-01 → 2026-07-09) unread.*