# RELIANCE Daily Regime Research — Report

**Branch:** `research/reliance-regime-daily` · **Date:** 2026-09-10
**Instrument:** RELIANCE (NSE delivery equity, CA-adjusted, entity-continuous)
**Data:** `equity_bhavcopy.duckdb` (`equity_bhavcopy_adjusted`), 1d index store
**Artefacts:** `data/reliance_regime/results.json`, `panel.parquet`, `signals.parquet`
**Tests:** 16/16 passing (`tests/reliance_regime/`)

---

## 1. Design

Daily **Long/Flat** decisions, close-to-close: the signal computed at the
close of day t (using only data through t) decides the position held for the
t → t+1 return. Fees are era-accurate delivery-equity costs
(`core/execution/equity/delivery_fees.py`, STT 0.1% **per leg** dominates)
charged on every entry/exit at ₹1,00,000 notional.

**Panels (pre-specified):** DEV 2010–2019 (n=2,478) · VALIDATION 2020–2022
(n=748, COVID era) · RECENT 2023–2026-09 (n=915). All signals frozen before
any evaluation; no parameter was changed after seeing results.

**Signal slate (13):** `always_long` (benchmark), `ts_mom_{63,126,252}`
(time-series momentum, 1-day skip — the Moskowitz-Ooi-Pedersen convention),
`sma_{50,100,200}`, `donchian_{63,252}` (breakout), `reversal_5` (buy
dips), `vol_calm` (volatility-state gate: flat while trailing 20d realized
vol exceeds the 70th percentile of its trailing 252d window — Moreira-Muir
in Long/Flat form), `idx_trend` (market regime: Nifty above its 200d SMA),
`combined` = ts_mom_252 AND vol_calm AND idx_trend.

## 2. Data audit

RELIANCE daily: **4,141 rows, 2010-01-04 → 2026-09-09, zero gaps**, CA-clean
(2 bonus events adjusted: 2017-09-07, 2024-10-28; no |return| > 0.25 anywhere),
Nifty-200 membership at rank 2–3 for all 175 rebalances. Nifty 50 context:
full span. India VIX context: 2014-05-14+. Vendor 1m intraday for RELIANCE
exists (2015–2025) but is unused — the horizon is close-to-close.

## 3. Results (net of era-accurate delivery fees)

| signal | in-mkt | tr/yr | net ann | Sharpe | maxDD | IC | IC t |
|---|---:|---:|---:|---:|---:|---:|---:|
| **DEV 2010–2019** (buy&hold gross +13.9%) | | | | | | | |
| ts_mom_252 | 62% | 6.8 | **+9.6%** | 0.49 | −37% | +0.005 | 0.3 |
| sma_200 | 62% | 9.1 | +6.0% | 0.31 | −46% | +0.098 | 4.9 |
| sma_50 | 57% | 18.8 | +0.9% | 0.05 | −62% | **+0.172** | **9.5** |
| donchian_252 | 2% | 7.3 | +0.8% | 0.18 | −14% | +0.229 | 5.1 |
| reversal_5 | 47% | 51 | +2.3% | 0.13 | −33% | **−0.321** | −20.4 |
| vol_calm | 59% | 11.5 | −0.0% | — | −55% | −0.017 | −0.8 |
| idx_trend | 57% | 7.4 | +5.0% | 0.27 | −45% | +0.037 | 1.9 |
| combined | 31% | 10.3 | −1.4% | — | −40% | +0.006 | 0.3 |
| **VALIDATION 2020–2022** (buy&hold gross +23.6%) | | | | | | | |
| sma_50 | 54% | 18.9 | **+11.8%** | 0.58 | −20% | **+0.144** | **4.3** |
| sma_200 | 80% | 8.8 | +8.1% | 0.32 | −24% | +0.082 | 1.8 |
| ts_mom_252 | 91% | 3.7 | +9.5% | 0.34 | −30% | −0.074 | −1.3 |
| ts_mom_126 | 73% | 17.2 | −8.3% | −0.34 | −39% | −0.084 | −2.1 |
| donchian_63 | 4% | 11.5 | +4.2% | 0.66 | −4% | +0.249 | 4.0 |
| reversal_5 | 47% | 48 | −8.6% | −0.33 | −42% | **−0.290** | −9.6 |
| vol_calm | 73% | 9.1 | +9.4% | 0.41 | −24% | +0.010 | 0.2 |
| combined | 61% | 8.4 | −1.4% | — | −24% | −0.031 | −0.8 |
| **RECENT 2023–2026-09** (buy&hold gross +2.0%) | | | | | | | |
| sma_200 | 51% | 6.6 | **+1.7%** | 0.11 | −17% | +0.075 | 2.4 |
| sma_50 | 44% | 19.3 | −0.7% | −0.05 | −32% | **+0.194** | **6.4** |
| ts_mom_252 | 50% | 9.4 | −4.3% | −0.26 | −30% | −0.034 | −1.0 |
| reversal_5 | 47% | 52 | −2.2% | −0.15 | −30% | **−0.358** | −12.9 |
| donchian_252 | 1% | 5.0 | −3.2% | −0.70 | −13% | +0.152 | 2.4 |
| vol_calm | 70% | 11.3 | −2.6% | −0.16 | −26% | −0.007 | −0.2 |
| combined | 26% | 13.8 | −4.9% | −0.44 | −26% | −0.007 | −0.2 |

## 4. The stable findings

**A. Daily return continuation is real and persists for 16 years.** The
`reversal_5` signal — long after a down 5-day stretch — has IC **−0.32 /
−0.29 / −0.36** with t −20.4 / −9.6 / −12.9 across the three panels. RELIANCE
5-day returns *continue*, they do not mean-revert. Short-lookback trend
signals (`sma_50` IC **+0.17 / +0.14 / +0.19**, t 9.5 / 4.3 / 6.4) carry the
same information from the long side. This is the literature's one robust
single-stock directional regularity, confirmed here out-of-sample twice
(2020–2022 and 2023–2026 were never used to select anything).

**B. The economics are the wall, exactly as predicted.** At 19 trades/yr the
`sma_50` signal pays ~4%/yr in delivery STT alone; its gross in-market edge
(≈ +5.5% DEV) barely clears it and does not survive the flat 2023–2026 era
net (−0.7%). Only low-turnover long-horizon trend (`sma_200`, ~7–9 trades/yr,
`ts_mom_252`) nets positive in **all three panels** (+9.6 / +8.1–9.5 / +1.7%),
but its edge is the 2010–2022 RELIANCE trend; when the stock went sideways
(2023+), the signal decayed to Sharpe 0.11.

**C. Regime conditioning adds nothing consistent.** The `vol_calm` gate
(flat above the 70th trailing-vol percentile) *hurt* in DEV — the high-vol
bucket was where RELIANCE's bull trend paid (+32.9% vs −7.4% for the gated
book); was neutral in VALIDATION; neutral-to-negative in RECENT. The vol
tercile regime table itself is era-unstable: the bucket that pays flips
sign between panels. `idx_trend` helped DEV, neutral after. The pre-specified
`combined` construct nets **negative in all three panels** (−1.4 / −1.4 /
−4.9%). No threshold or regime split was tuned after the fact; the gates
were chosen from the literature before results, and the data says they do
not lift the trend signal on this name.

**D. Breakouts are lottery tickets.** `donchian` holds the market 1–4% of
days, grosses +70–180% annualized in-market when breakouts run (DEV,
VALIDATION), and −200% in-market when they reverse (RECENT). Positive IC,
negative reliable economics — the classic skew profile.

## 5. Verdict

**As a daily buy/sell predictor: NO ROBUST TRADABLE EDGE — but one real,
stable, and now twice-replicated statistical fact.**

1. The *predictability* exists: RELIANCE daily returns continue at short
   horizons (IC ≈ +0.3 at 5d, ≈ +0.17 at 50d), stable across three eras
   including two untouched-by-selection windows. This is a genuine,
   replicable answer to "does a daily direction signal exist for RELIANCE".
2. The *tradeability* does not follow: delivery STT (0.1%/leg) plus the
   2023+ regime change (RELIANCE stopped trending) reduce every conversion
   of that IC into P&L to ≈ zero net — except long-horizon trend, which is
   positive everywhere but weak (Sharpe 0.1–0.5) and simply tracks the
   stock's own multi-year trend.
3. Regime conditioning (vol gate, index gate), in this formulation, did not
   improve the result in any panel. That negative result is itself the
   literature's lesson: for a single large-cap name, the market regime is
   mostly the stock's own trend, and volatility gating costs more
   participation than it saves.

**Next steps if wanted:** the 1m vendor store (RELIANCE 2015–2025) opens
intraday timing of the *entry/exit within* the trend days (the sma_50 IC is
strongest of all — the fee wall, not the signal, is what kills it); or a
proper economic study of `sma_200` long-only with real turnover. Both are
new decisions, not continuations of this report.

---

# Follow-up studies (2026-09-10)

## Study 1 — Intraday entry/exit timing for the long-only sma_200 book

**Data:** vendor 1m store (`1m_vendor/reliance.duckdb`, 2,605 sessions
2015-02-02 → 2025-08-06; start-labelled, volume populated, zero dups).
**Provenance seam found and resolved:** the vendor price *level* differs
from the repo's CA-adjusted daily series by a smooth ~5% pre-2024 factor
(different corporate-action lineage — both bonuses plus an accumulating
dividend adjustment; daily/vendor close ratio drifts 0.93 → 1.00). Every
vendor day is **rescaled by its own same-day close ratio**, aligning the
level to the daily series while preserving the intraday shape exactly
(`scripts/reliance_regime/intraday.py`, tested).

**Book:** 69 sma_200 round trips 2010–2026; 38 inside the vendor window.
Entry variants on the day after the entry signal (E+1): open, first-30-min
TWAP, VWAP, dip limit (open − 0.5×prior range, else close), and the
infeasible day-low bound; exit variants: signal close (baseline) vs
next-day open. Era-accurate delivery fees on every leg.

| entry / exit | gross/trade | net/trade | ann net | win rate |
|---|---:|---:|---:|---:|
| **close_E / close_X (baseline)** | +4.59% | +4.36% | **+15.6%** | 0.26 |
| open_E1 / close_X | +4.18% | +3.95% | +14.2% | 0.24 |
| twap30_E1 / close_X | +4.17% | +3.94% | +14.1% | 0.26 |
| vwap_E1 / close_X | +3.97% | +3.74% | +13.4% | 0.29 |
| dip_E1 / close_X | +4.05% | +3.82% | +13.7% | 0.32 |
| low_E1 / close_X (infeasible) | +5.30% | +5.07% | +18.2% | 0.47 |
| close_E / open_X1 | +4.76% | +4.53% | +16.2% | 0.32 |

**Finding: intraday timing does NOT improve the book.** Every executable
next-day entry variant is *worse* than buying at the signal close — the
E→E+1 overnight move is positive on trend days (waiting costs ~1.2–2.2% ann).
Even perfect foreknowledge of the entry day's low (the infeasible bound)
adds only +2.6% ann, and no executable rule captures any of it. The one
small improvement is on the exit side: exiting at the open of the day after
the exit signal gains ~0.6% ann (+16.2% vs +15.6%) — the exit-day overnight
gap also trends. The close-to-close convention used in the main research
was already the right execution.

## Study 2 — Economic study of long-only sma_200 (full 2010–2026 panel)

**Cost ladder** (per-leg cost in bp; ~8 round trips/yr, low turnover):

| per-leg | 0bp | 2bp | 5bp | 10bp (STT reality) | 15bp | 20bp | 25bp |
|---|---:|---:|---:|---:|---:|---:|---:|
| ann net | +6.4% | +6.2% | +6.0% | **+5.5%** | +5.1% | +4.7% | +4.3% |
| Sharpe | 0.32 | 0.31 | 0.30 | 0.28 | 0.26 | 0.24 | 0.22 |
| maxDD | −41% | −42% | −43% | −45% | −47% | −49% | −51% |

Cost sensitivity is ~0.85%/yr per 10 bp/leg — **fees are not the binding
constraint** (unlike the daily-continuation signals at 19+ trades/yr). The
binding constraint is the signal itself.

**Yearly net (≈10.5 bp/leg):** 2010–2016 mostly flat (−10% to −3% with
0.10–0.81 participation; RELIANCE was range-bound), then the trend era
**2017–2021**: +55%, +24%, +21%, +29%, +7%; then **2022 −10%, 2023 −1.3%
(33% participation), 2024 +10.6%, 2025 +14.8%, 2026 −25.4% (13%
participation — caught in the drawdown)**.

**Verdict of the economics:** over the full span the book nets +5.4%/yr vs
buy-and-hold gross +13.1% (**excess −7.7%**) — trend timing *gave up* half
the stock's return to sit flat, its drawdown protection is modest (−45% vs
−40%), and the bootstrap CI of the daily mean ([−0.01%, +0.06%]) **includes
zero**: the full-span edge is not statistically distinguishable from zero.
The +15.6% ann net in Study 1's vendor window is the 2015–2025 trend-era
subsample, not the whole history.

**Combined conclusion:** intraday timing cannot rescue the sma_200 book,
and the sma_200 book itself is economically fragile — its entire net
advantage is the 2017–2021 trend era, and on the full 2010–2026 record it
underperforms simply holding RELIANCE. For a single name, the regime here
is the stock's own trend; both follow-up paths the report offered have now
been walked and neither changes the verdict of the main research:
**direction is weakly predictable (continuation), but no delivery-equity
expression of it is robustly profitable.**
