# Nifty-BankNifty Index Pair Trading — Deep Research

**Generated:** 2026-08-01
**Data:** 1d EOD (2016-01-01 to 2026-07-31, 2,620 obs) + 1m intraday (2023-01-02 to 2026-07-03, 315,023 obs)
**Cost model:** 3 bps round-trip per pair leg (futures STT + brokerage + exchange)
**Execution:** Futures — Nifty lot=25, BankNifty lot=15

---

## Executive Summary

**Verdict: NO ACTIONABLE OPPORTUNITY.** The Nifty-BankNifty price ratio does not mean-revert reliably enough for systematic pair trading. Every test that controls for in-sample overfitting weakens the case, and intraday strategies are uniformly negative. The apparent EOD profitability is driven by a single year (COVID 2020) and unstable parameters.

---

## 1. Statistical Foundation

### 1.1 Correlation & Beta
| Metric | Value |
|--------|-------|
| Return correlation | 0.8892 |
| Rolling 60d corr (mean/min/max) | 0.86 / 0.62 / 0.98 |
| Rolling 60d beta (mean/std) | 1.13 / 0.18 |

High but not perfect — the spread contains independent variation. This is necessary but not sufficient for pair trading.

### 1.2 Ratio History (BNF / N50)
| Period | Mean | Std | Min | Max | N |
|--------|------|-----|-----|-----|---|
| Full (2016-2026) | 2.28 | 0.16 | 1.89 | 2.66 | 2,620 |
| 2016-2019 | 2.39 | 0.16 | 1.94 | 2.66 | 985 |
| 2020-2022 | 2.20 | 0.15 | 1.89 | 2.64 | 748 |
| 2023-now | 2.24 | 0.10 | 2.03 | 2.42 | 887 |

The ratio has a **declining trend** (from 2.39 to 2.24) and **declining volatility** (std from 0.16 to 0.10). The narrowing range in 2023+ reduces profit potential per trade.

### 1.3 Cointegration (Johansen Test)
| Statistic | Value | 95% Critical |
|-----------|-------|--------------|
| Trace r=0 | 14.42 | 15.49 |
| Trace r=1 | 0.74 | 3.84 |

**NOT cointegrated at 5%.** The two indices share a common trend but their log-price spread is a random walk with drift — it can diverge for extended periods.

### 1.4 Half-Life of Mean Reversion
| Method | Half-Life | Beta | R-squared |
|--------|-----------|------|-----------|
| Full-sample OLS | **166.5 days** | -0.0042 | 0.0021 |
| Rolling 252d (median) | **41.7 days** | — | — |

The R-squared of 0.0021 means the autoregressive model explains 0.2% of the variance — mean reversion is extremely weak. The rolling estimate suggests faster reversion in some windows, but this is inconsistent.

### 1.5 Overnight Reversal
| Metric | Value |
|--------|-------|
| Lag-1 autocorrelation | +0.086 (slight continuation, not reversal) |
| Reversal rate (all days) | 48.9% |
| Reversal after big up move | 48.1% (n=318) |
| Reversal after big down move | 48.1% (n=291) |

**Essentially a coin flip.** There is no statistically meaningful overnight reversal in the ratio.

---

## 2. Intraday Analysis (1m Data, 2023-2026)

### 2.1 Intraday Spread Behavior
| Metric | Value |
|--------|-------|
| Days analyzed | 844 |
| Daily ratio range (mean) | 61.7 bps |
| Daily ratio std (mean) | 13.6 bps |
| Ratio change autocorr (1m) | -0.025 |
| Ratio change autocorr (5m) | +0.005 |
| Ratio change autocorr (60m) | +0.006 |

### 2.2 Mean Reversion Test
| Direction | Slope | R | Mean-Reverting? |
|-----------|-------|---|-----------------|
| Up moves (ratio rises) | **+1.10** | 0.79 | **No — trends** |
| Down moves (ratio falls) | **+1.17** | 0.76 | **No — trends** |

**Critical finding:** The ratio does NOT mean-revert intraday. When it moves away from the open, it tends to keep moving in the same direction. A pair trader fading intraday moves would be consistently wrong.

### 2.3 Intraday Z-Score Strategies
All 27 parameter combinations tested (entry_z=2.0-3.0, exit_z=0.5-1.0, window=60-240 min) produced **negative** net PnL. The best combination lost 3,295 bps. The worst lost 16,499 bps.

**Intraday pair trading is a non-starter.**

---

## 3. EOD Strategy Analysis

### 3.1 Full-Sample Grid Search (Top 5 of 45)
| # | Entry Z | Exit Z | Window | N Trades | Net (bps) | Annual (bps) | WR | PF | MaxDD |
|---|---------|--------|--------|----------|-----------|-------------|-----|----|-------|
| 1 | 1.5 | 0.0 | 20 | 115 | +3,274 | +312 | 41.7% | 1.45 | -1,092 |
| 2 | 1.5 | 0.5 | 20 | 99 | +2,792 | +266 | 44.4% | 1.37 | -1,091 |
| 3 | 1.5 | 1.0 | 20 | 87 | +1,260 | +120 | 46.0% | 1.17 | -1,288 |
| 4 | 2.0 | 0.0 | 20 | 85 | +870 | +83 | 44.7% | 1.14 | -1,247 |
| 5 | 2.0 | 0.5 | 20 | 77 | +248 | +24 | 42.9% | 1.03 | -1,853 |

The top strategy nominally earns +312 bps/yr, but **this is the full-sample (in-sample) result** — the same data used to select parameters. The following tests control for this bias.

### 3.2 Bootstrap Significance Test
| Metric | Value |
|--------|-------|
| Actual net (no costs) | +709.5 bps |
| Null mean (shuffled) | -217.7 bps |
| Null std | 2,607.9 bps |
| **p-value** | **0.354** |

**NOT statistically significant at 5%.** A strategy that buys and sells random ratio dislocations would produce similar or better results in 35% of simulations. The null distribution is wide because the ratio has large swings — random entries will occasionally catch big moves.

---

## 4. Out-of-Sample Validation

### 4.1 Fixed-Parameter Walk-Forward (trained 2016-2019, tested forward)

**Best training params:** entry_z=1.0, exit_z=1.5, window=10d (net +1,748 bps on train)

| Year | Net (bps) | Trades | WR | Annualized |
|------|-----------|--------|-----|------------|
| 2016 | +658 | 8 | 50% | +684 |
| 2017 | +126 | 10 | 30% | +131 |
| 2018 | +900 | 9 | 56% | +932 |
| 2019 | +243 | 12 | 50% | +253 |
| **2020** | **+1,546** | **14** | **43%** | **+1,604** |
| 2021 | +627 | 11 | 54% | +653 |
| **2022** | **-1,128** | **16** | **25%** | **-1,177** |
| **2023** | **-1,323** | **17** | **24%** | **-1,381** |
| 2024 | +128 | 10 | 30% | +132 |
| 2025 | +542 | 11 | 36% | +564 |
| 2026 | +556 | 6 | 67% | +1,027 |

| Aggregate | Value |
|-----------|-------|
| Total (all years) | +2,875 bps |
| Positive years | 9/11 |
| **Without COVID 2020** | **+1,329 bps (133 bps/yr)** |
| 2022-2023 combined | **-2,451 bps** |

**Key observations:**
1. **2020 is 54% of total profit** — the COVID crash created an extreme ratio dislocation. Remove it and the annualized return drops to ~133 bps, barely above noise.
2. **2022-2023 lost almost everything** — the rate-hiking regime was hostile to this strategy.
3. **Late-sample parameters differ** — the strategy that worked 2016-2019 stopped working in 2022-2023.

### 4.2 Alternative Fixed Parameters (ez=1.5, xz=0.0, w=20 — top full-sample pick)

| Year | Net (bps) | Year | Net (bps) |
|------|-----------|------|-----------|
| 2016 | -59 | 2022 | -193 |
| 2017 | +95 | 2023 | -593 |
| 2018 | -16 | 2024 | -233 |
| 2019 | +412 | 2025 | +536 |
| 2020 | +1,875 | 2026 | +60 |
| 2021 | +803 | | |

This parameter set — the one a naive researcher would pick from the full sample — **fails in 2016-2018** and again in **2022-2024**. It only looks good because 2020-2021 inflation pulls the full-sample average up.

### 4.3 Parameter Stability by Rolling 4-Year Window

| Window | Best ez | Best xz | Best w | Train Net (bps) |
|--------|---------|---------|--------|-----------------|
| 2016-2019 | 1.0 | 1.5 | 10 | +1,748 |
| 2017-2020 | 1.0 | 0.0 | 10 | +3,321 |
| 2018-2021 | 1.0 | 0.0 | 10 | +3,872 |
| 2019-2022 | 1.5 | 0.0 | 20 | +2,878 |
| 2020-2023 | 1.5 | 0.0 | 20 | +1,661 |
| 2021-2024 | 1.5 | 1.0 | 20 | +612 |
| **2022-2025** | **1.0** | **1.0** | **40** | +1,586 |
| **2023-2026** | **1.0** | **1.0** | **40** | +1,430 |

**Parameters are unstable.** The window length shifts from 10d to 40d over the sample. Exit thresholds change. A researcher who selects the "best" parameters from any training period will apply wrong parameters to the next regime.

### 4.4 Regime Analysis (200-day MA trend)

| Regime | Days | Net (bps) | Annual | WR | MaxDD |
|--------|------|-----------|--------|-----|-------|
| Bull (>5% above MA) | 1,144 | +2,080 | +235 | 30.8% | -2,280 |
| Bear (<5% below MA) | 184 | -84 | -14 | 71.4% | -583 |
| Sideways | 1,093 | +1,836 | +190 | 47.6% | -1,132 |

The strategy is profitable in bull and sideways but slightly negative in bear markets. This is consistent with the ratio having an upward drift in bull markets — the "mean reversion" captures the upward trend, not actual reversion.

---

## 5. Why This Doesn't Work

### 5.1 Structural Reasons

| Problem | Evidence |
|---------|----------|
| **Not cointegrated** | Trace stat 14.42 < 15.49 critical |
| **Half-life too long** | 166 days — positions would be held for months |
| **No intraday reversion** | Ratio *trends* intraday (positive slope) |
| **Parameters unstable** | Window shifts 10d → 40d, thresholds change |
| **COVID-dependent** | 2020 = 54% of all profits |
| **Bootstrap fails** | p=0.354, cannot reject random null |
| **Rate-hiking hostile** | 2022-2023: -2,451 bps |

### 5.2 What This Means for Trading

A systematic Nifty-BankNifty pair trade would need to:
1. Hold positions for **months** (half-life of 166 days)
2. Survive **prolonged drawdowns** (2022-2023 lost -2,451 bps over 2 years)
3. Bet that the **next dislocation** is as large as COVID 2020
4. Somehow pick the **right parameters** for the next regime

This is not a strategy — it's a bet on a specific dislocating event that already happened.

### 5.3 What Might Work Instead

The data suggests the ratio **trends**, not mean-reverts. Potential alternatives:

1. **Ratio momentum** — go with the trend, not against it
2. **Sector rotation timing** — trade BankNifty/Nifty relative strength (this is already partially captured by the existing TS Basis / Carry strategy framework)
3. **Event-driven** — trade around RBI policy, budget, earnings season when the correlation temporarily breaks
4. **Options-based dispersion** — trade index options to capture the spread (Nifty straddle vs BankNifty straddle)

These are different constructs entirely and would require separate pre-registration and RFA clearance.

---

## 6. Data & Methodology Notes

| Item | Detail |
|------|--------|
| 1d data source | NSE index close from per-day DuckDB files (2016-01-01 to 2026-07-31) |
| 1m data source | Upstox V3 historical candles (2023-01-02 to 2026-07-03) |
| Index volume | Always 0 — no VWAP or execution realism possible |
| Cost model | 3 bps round-trip per pair leg (futures STT + brokerage + exchange + SEBI + GST + stamp) |
| Execution assumptions | Futures only (Nifty lot=25, BankNifty lot=15). Lot rounding, margins, and roll costs are not modeled |
| Research governance | This is an exploratory screen, NOT a pre-registered construct. No SEALED window was spent. Data from 2026-07-03 to 2026-07-31 (1d only) is the most recent unread window, but it was used in this analysis |

---

## 7. Conclusion

**No systematic pair trading opportunity exists between Nifty 50 and Bank Nifty using price ratio mean reversion.** The data is exhaustive (10.5 years EOD + 3.5 years 1m) and the conclusion is robust across multiple validation frameworks: bootstrap, fixed-parameter walk-forward, train/test splits, and regime decomposition.

The pair is simply not mean-reverting enough — the half-life is too long, intraday behavior is trending, parameters are unstable, and the apparent profitability is concentrated in a single extreme event. Any live deployment would be exposed to large, sustained drawdowns in the regime most likely to repeat (rate-hiking cycles).

**No successor research is authorized by this report.** The conclusion is negative, not conditional. If a new construct is proposed (ratio momentum, options dispersion, event-driven), it must start its own RFA pre-check and pre-registration from scratch.
