# Research Strategy Specification Audit

**Date:** 2026-09-28
**Scope:** every construct that `VAULT_GAP_MAP_COVERAGE_AUDIT_2026-09-28.md` classed as genuinely tested
or partially/relatedly tested. The question is what mechanically was run.
**Method:** values copied from frozen protocols, pre-registrations and script-generated reports only.
Nothing is inferred, and no default indicator setting is assumed. A value not found in an internal
record is **UNKNOWN**. A value found only in a secondary record (a review, a closure memo, a dossier)
is marked *(secondary)*. No data was read and no computation was run.
**Costs:** where a gate was net-of-cost, the gross/statistical figure is reported next to it. Nothing
is re-adjudicated on cost.

Path prefixes: `psb/`, `index_research/`, `strategies/`, `sleeves/`, `carry/`, `sfb_f1/`, `ptms/`
are under `docs/reports/`.

---

## 1. Executive summary

- **15 constructs were genuinely run on data.** For 12 of them the frozen protocol pins the signal
  formula, universe, cadence, windows and test statistic exactly, so the mechanical rule is
  recoverable from the record alone: PSB-1 C1/C2/C3, PSB-2 C2/C4, CB-N50, ISD F1/F4, A, Trend,
  Carry, Gann GF-1/GF-4T/GF-10.
- **Three tested constructs are under-specified in the record:**
  - the **Nifty/BankNifty pair** z-score study: z-score formula, hedge ratio and exit semantics are undocumented
  - **MSRP D1**: strike-selection rule is not in the triage report
  - the **F1 screen**: the bracket grid is only partly documented, and the report text contradicts the code on the open-gap rule
- **Two tested constructs carry documented divergences between specification and implementation:**
  - **Carry**: the dividend adjustment sign is inverted in the frozen code; dividend PIT-ness is uncertifiable; the gates were computed on an equal-weight quintile book, not the pre-registered z-weighted book; returns are spot, not futures
  - **A**: the construct document's grid table states a 15:29 exit, while the frozen pre-registration pins 15:14
- **One tested construct is LEGACY:** the DRA HMM-gated EMA strategy. Its primary report is not in the
  repo, so its rules come only from a secondary dossier, and some parameters (ATR period) are UNKNOWN.
- **Almost none of the tested constructs uses a classical single-instrument technical indicator.**
  Indicators appear only as:
  - an ATR bracket (F1: ATR period 21, TRAIN-selected multiples)
  - an EMA(9)/EMA(21) filter inside the legacy DRA
  - K3 swing detection (Gann)
  
  No RSI, Stochastic, MACD, Bollinger, Donchian, Supertrend or ADX rule appears in any tested
  construct's specification.

## 2. Coverage audited

| # | Construct | Coverage-audit class | Research status | Spec completeness |
|---|---|---|---|---|
| 1 | PSB-1 C1 short-term reversal | Genuinely tested | STAT-EDGE (in-sample dev) / COST-KILLED | Complete |
| 2 | PSB-1 C2 residual reversal | Genuinely tested | STAT-EDGE (in-sample dev) / COST-KILLED | Complete |
| 3 | PSB-1 C3 delivery z | Genuinely tested | STAT-EDGE (in-sample dev) / COST-KILLED | Complete |
| 4 | PSB-2 C2 delivery z, fortnightly (+ Phase 0.5) | Genuinely tested | Dev: eligible, recommended → Phase 0.5 TESTED-FAIL (power) → retired | Complete |
| 5 | PSB-2 C4 12-1 momentum, staggered | Genuinely tested | TESTED (IC > 0, net > 0), dropped on power | Complete |
| 6 | CB-N50 breadth features | Genuinely tested | TRAIN-PASS, HOLDOUT-PASS (IC); P&L gate G4 never evaluated | Mostly complete (see §6) |
| 7 | ISD F1 opening drive (equities) | Genuinely tested | TESTED-FAIL (wrong sign) | Complete |
| 8 | ISD F4 overnight gap | Genuinely tested | STAT-EDGE / COST-KILLED (TRAIN) | Complete; per-cell ICs not in script report |
| 9 | A index opening drive | Genuinely tested | TRAIN-PASS → HOLDOUT-FAIL (net gate) | Complete; doc inconsistency (§10) |
| 10 | Trend sleeve | Genuinely tested | TESTED-FAIL (TRAIN) | Complete |
| 11 | Carry v1 / v2 | Genuinely tested | v1 TESTED-FAIL (wrong sign); v2 HOLDOUT-PASS, SEALED-PASS (spot) | Complete, with documented defects |
| 12 | Late-cycle stock straddle selling | Genuinely tested | EXPLORATORY (discovery + unchanged-code confirmation) | Partly (§6) |
| 13 | MSRP D1 vol-gated index straddle | Genuinely tested | TESTED-FAIL (in-sample triage) | Partly (§6) |
| 14 | Nifty/BankNifty ratio z-score | Genuinely tested | EXPLORATORY, TESTED-FAIL | Under-specified |
| 15 | Gann GF-1 / GF-4T/R8 / GF-10 | Genuinely tested | TESTED-FAIL (non-confirmatory screen) | Complete |
| 16 | F1 12-1 momentum + ATR bracket | Genuinely tested (screen) | EXPLORATORY screen; GO printed, superseded NO-GO | Partly (§6) |
| 17 | DRA HMM-gated EMA strategy | Related | LEGACY | Partly (§6) |
| 18 | Stage-A Gate 0 families | Related | PRICED-INFEASIBLE / CATALOGUED-ONLY | Not a construct test |
| 19 | MRLC | Related | CATALOGUED-ONLY (analysis) | Not a construct test |
| 20 | Flow, RS-MOM | Related | RFA-ABANDON | No data read |
| 21 | OSC | Related | Probe on burned data → RFA-ABANDON | Probe only |
| 22 | STOCK-STRADDLE-M10 | Related | Pre-registered, not yet run | No result exists |

---

## 3. Detailed mechanical specification — genuinely tested constructs

### 3.1 PSB-1 C1 — short-term reversal

| Field | Value | Source |
|---|---|---|
| Mechanism | Last week's cross-sectional losers outperform winners next week | `psb/PSB1_PROTOCOL.md` §5 C1 |
| Universe | Gate-(c) point-in-time NIFTY-200; membership = most recent `rebalance_date ≤ t` | §2 |
| Data | `equity_bhavcopy_adjusted` (CA-adjusted daily bhavcopy), `close` | §2 |
| Signal | `s_i(t) = − r_i(t−5, t)`, r = adjusted-close return, t−k counts trading days | §5 C1, §4.4 |
| Formation | Weekly grid: last full-session day of each ISO week (`n_symbols ≥ 200`) | §3 |
| Holding | One week: `adj_close(t → t′)`, t′ = next grid day | §3 |
| Execution timing | Formed **at the close of t**; no execution lag (net spread labelled an upper bound) | §3, §6 |
| Ranking | Fractional percentile ranks in [0,1], average ties, scored names only | §4.4 |
| Portfolio (secondary metric) | Equal-weight top quintile minus equal-weight universe baseline; baseline also charged fees | §6 |
| Long/short | IC: cross-sectional. Secondary: long top quintile vs baseline | §6 |
| Sizing / stops / filters | None / none / none (formation-complete rule only) | §4, §5 |
| Costs (not adjudicated here) | Gate-(d) delivery fees + κ = 5 bp/side | §2 |
| Window | Dev 2012-01-01 → 2022-12-31 (single in-sample window; no TRAIN/HOLDOUT split) | §3 |
| n | 569 formation dates (first 2012-02-03, last 2022-12-23) | `psb/PSB1_C1_REPORT.md` header, "Formation dates" |
| Test | Spearman IC per date; one-sided t on mean IC | Protocol §6 |
| Result | Mean IC +0.02319, SD 0.14701, t 3.7628, p 9.27e-05, AC₁ 0.0966 | Report §6 Metrics |
| Gross | Top−base −4.01%/yr; Q1−Q5 +1.05%/yr | Report §6 Quintile spread |
| Net | −16.80%/yr (upper bound); drag 1,293 bp/yr; turnover 0.7717 | same |
| Power | 0.6848 at n* 183 | Report §7 |
| Verdict | Not eligible (net < 0, power < 0.80) | CLAUDE.md PSB-1 table *(secondary)* |

### 3.2 PSB-1 C2 — residual reversal
The universe, data, grid, timing, ranking, portfolio and costs are the same as C1 (`PSB1_PROTOCOL.md` §2–§6).

| Field | Value | Source |
|---|---|---|
| Market return | EW mean of `r_i(w−5, w)` over members with both prices | §5 C2 |
| Beta model | OLS `r_i = α + β·r_mkt + ε` on the 52 weekly grid returns ending at the grid date before t; ≥ 40 of 52 required; formation week excluded | §5 C2 |
| Signal | `s = − (r_i(t−5,t) − α − β·r_mkt(t−5,t)) / σ_i(ε)` | §5 C2 |
| Window / n | Dev 2012–2022; 529 dates | `psb/PSB1_C2_REPORT.md` |
| Result | Mean IC +0.03515, SD 0.12194, t 6.6306, p 4.14e-11 | Report §6 |
| Gross / net | Top−base +5.48%; Q1−Q5 +14.95%; net −8.60%; drag 1,421.6 bp; turnover 0.7872 | Report §6 Quintile |
| Power | 0.9875 | Report §7 |

### 3.3 PSB-1 C3 — delivery-percentage anomaly (weekly)
The universe, grid and costs are the same as C1.

| Field | Value | Source |
|---|---|---|
| Signal | `dp` = mean `deliv_pct` over the 5 days ending t (≥ 3 non-NULL); `μ, σ` over the 60 days ending t−5 (≥ 40, σ > 0); `s = (dp − μ)/σ` | `PSB1_PROTOCOL.md` §5 C3 |
| Direction | High abnormal delivery → positive relative return | §5 C3 |
| Window / n | Dev 2020-04-01 → 2022-12-31; 143 | `psb/PSB1_C3_REPORT.md` |
| Result | Mean IC +0.02481, SD 0.10134, t 2.9275, p 1.99e-03 | Report §6 |
| Gross / net | Top−base +11.12%; Q1−Q5 +17.45%; net −2.45%; drag 1,383.7 bp; turnover 0.5872 | Report §6 Quintile |
| Power | 0.9510 | Report §7 |

### 3.4 PSB-2 C2 — delivery z, fortnightly (and C2 Phase 0.5)

| Field | Value | Source |
|---|---|---|
| Signal | `dp` = mean `deliv_pct` over the fortnight's trading days ending t (≥ 8); `μ, σ` over the 252 days ending t−21 (≥ 150, σ > 0); `s = (dp − μ)/σ` | `psb/PSB2_PROTOCOL.md` §5 C2 |
| Grid | Fortnightly: last full session on/before the 15th + last full session of the month | §3 |
| Holding | To next grid day (~15 days); formed at close of t | §3 |
| Portfolio | Top quintile, enter in Q1, **exit only when outside the top two quintiles** (0.40 band); IC unbanded | §5 C2 |
| Universe / data | As PSB-1 (NIFTY-200 PIT; certified adjusted view) | §2 |
| Window / n | Dev 2020-09-04 → 2022-12-31; 56 grid, 55 scored | `psb/PSB2_C2_REPORT.md` |
| Result | Mean IC +0.03489, SD 0.10403, t 2.4874, p 7.99e-03, AC₁ −0.1818 | Report §6 |
| Gross / net | Top−base +7.03%; net +4.57%; drag 270.3 bp; turnover 0.2701 | Report §6 |
| Power | 0.9198 at n* 84 | Report §7 |
| Phase 0.5 (extended TRAIN 2011–2018) | Variants V1 monthly/0.4, V2 fortnightly/0.6, V3 fortnightly/0.4 staggered 3; mean IC 0.0234 / 0.0226 / 0.0226; SD ≈ 0.10; power 0.42 / 0.66 / 0.66; **no variant ≥ 0.80**; HOLDOUT not run | `psb/C2_PHASE0_5_MINIBATTERY.md` Phase A table, Selection |

### 3.5 PSB-2 C4 — 12-1 momentum, long-only, staggered

| Field | Value | Source |
|---|---|---|
| Signal | `s = (1 + r_12)/(1 + r_1) − 1`, r_12 over grid g−12 → g, r_1 over g−1 → g (monthly grid) | `PSB2_PROTOCOL.md` §5 C4 |
| Portfolio | Long-only top quintile; 6 equal tranches, 1/6 rebalanced monthly; no band | §5 C4 |
| Window / n | Dev 2012–2022; 132 grid, 131 scored | `psb/PSB2_C4_REPORT.md` |
| Result | Mean IC +0.04655, SD 0.20895, t 2.5499, p 5.97e-03 | Report §6 |
| Gross / net | Top−base +3.08%; net +2.87%; drag 35.2 bp; turnover 0.0776 | Report §6 |
| Power | 0.4110 at n* 42 → dropped by rule | Report §7, §8 |

### 3.6 CB-N50 — constituent breadth features

| Field | Value | Source |
|---|---|---|
| Mechanism | Stock-level cross-sectional next-day prediction on Nifty 50 constituents | `index_research/CB_N50_PRE_REGISTRATION.md` §1.1 |
| Universe | PIT Nifty 50, verified against NSE changes; days with N < 30 excluded | §1.5, §3.1 |
| Features | Relative momentum `(close_t/close_{t−L} − 1) − median`, L ∈ {5, 10, 20}; futures basis `(F_close/S_close − 1)` annualised, winsorised ±3σ, minus median; reversal `−(close_t/close_{t−1} − 1) − median` | §1.2, §3.3 |
| Normalisation | Daily cross-sectional z-score, clipped ±3.0; combined = equal-weight mean of available z-scores | §3.3 |
| Basis contract / annualisation day-count | **UNKNOWN** (not specified in the pre-registration) | — |
| Target | Stock open(t+1) → open(t+2); signal from the close of t | §3.2, §3.6 |
| Test | Daily Spearman IC; Newey–West SE, Andrews automatic lag; TRAIN Bonferroni m = 9 | §3.4, §5.1 |
| Breadth rule (execution vehicle) | Free-float-weighted fraction with S > 0; LONG if > 0.65, SHORT if < 0.35, else FLAT; Nifty futures 1 unit; enter open t+1, exit open t+2 | §3.5, §3.6 |
| TRAIN | 2016-01-01 → 2019-12-31; 983 IC obs | `CB_N50_TRAIN_REPORT.md` header |
| TRAIN per-feature | mom L5 −0.0407 (t −7.15); L10 −0.0281 (−4.77); L20 −0.0207 (−3.48); reversal L1 +0.0459 (8.42); basis +0.0557 (12.13) | TRAIN report, Lookback table |
| Selection | "Best momentum lookback L = 20" → dropped for wrong sign; active = reversal + basis | TRAIN report, Sign check |
| TRAIN combined | Mean IC +0.05867, SD 0.1679, AC₁ −0.063, NW t 11.36 | TRAIN report, Combined |
| Breadth check | LONG 48 days (−2.4 bp), SHORT 2 days (+49.4 bp), FLAT 935: directional FAIL | TRAIN report, Breadth |
| HOLDOUT | 2020-01-01 → 2022-12-31; 746 obs; mean IC +0.02936, SD 0.1826, AC₁ −0.006, NW t 4.35, p 1.5e-05 | `CB_N50_HOLDOUT_REPORT.md` |
| Verdict | G1, G2, G3 PASS; **G4 (futures P&L) not evaluated**; SEALED unread | HOLDOUT report, Disposition |

### 3.7 ISD F1 and F4 — intraday equity battery

| Field | F1 opening drive | F4 overnight gap | Source |
|---|---|---|---|
| Universe | PIT F&O membership (~200 names/session), intraday-present | same | `strategies/ISD_PHASE0_PRE_REGISTRATION.md` §2 |
| Data | Certified native 1m equity store | same | §2 |
| Feature | (window-end bar close − 09:15 auction open)/09:15 open | (09:15 auction open − prev_close)/prev_close; CA ex-dates excluded | §4 |
| Cells | window {09:15–09:45, 09:15–10:00} × band {20%, 40%} | entry {09:16 open, 09:16 close} × band {20%, 40%} | §5 |
| Entry | Bar open after window end (09:46 / 10:01) | 09:16 bar open or close | §4 |
| Exit | 15:29 bar close; EOD flat | same | §4 |
| Book | Long top band / short bottom band; dollar-neutral; ADV cap 10% of trailing 20-session ADV as of T−1 | same | §4 |
| Sign | +1 pinned (continuation) | Discovered once on TRAIN, registered −1 | §4; `ISD_BATTERY_TRAIN_REPORT.md` |
| Test | Per-cell BH α 0.0125 vs random-entry (1,000) and circular-shift (1,000) nulls; family NW t at α 0.05 | §5–§7 |
| TRAIN | 2023-01-02 → 2024-11-30; 474 sessions | TRAIN report |
| Result | 0/4 cells qualify; w0945 IC −0.0166, t −2.81 *(secondary)* | 4/4 qualify; family IC −0.0289, NW t −6.09, shift-null p 0.0000 | TRAIN report; `ISD_PROGRAM_REASSESSMENT.md` §1 |
| Gross per session (F4) | — | +6.02 / +4.41 / +4.43 / +3.18 bp; implied cost 10.59–12.07 bp *(secondary)* | Reassessment §3 table |
| Verdict | FAIL (sign) | FAIL (net-spread gate only) | TRAIN report; Reassessment §1 |

### 3.8 A — index intraday opening drive

| Field | Value | Source |
|---|---|---|
| Instrument | `NSE_INDEX|Nifty 50` 1m as the price proxy; vehicle near-month Nifty futures (no intraday futures data) | `index_research/A_CONSTRUCT_DEFINITION.md` §1, §5 |
| Feature | (window-end bar close − opening print)/opening print; opening print = first bar open | §1 |
| Cells | Bars 0..30 (entry bar 31) and 0..45 (entry bar 46) | §1 |
| Entry | Open of bar 31 / 46 | §2 |
| Exit | **15:14 bar close**, EOD flat (D6) | `A_PHASE0_PRE_REGISTRATION.md` line 101; construct def §3 |
| Position | Long if feature > 0, short if < 0; every valid session; no filters or thresholds | construct def §4 |
| Sizing | Constant ₹2 Cr notional; returns in bp | §4, §6 |
| Return | `r_t = sign·(exit − entry)/entry − costs` | §6 |
| Test | Per-cell BH α 0.025; sign-permutation and block-shift nulls; family NW t; net-spread > 0 | §9 |
| TRAIN | 2012-01-02 → 2018-12-31; 1,699 tradeable | `A_TRAIN_REPORT.md` |
| TRAIN result | w30: net −0.58 bp, NW t −0.36, sign p 0.042 (not qualifying); w45: net +1.27 bp, NW t 0.86, sign p 0.0030 (qualifies); block-shift p 0.0000 | TRAIN report table |
| HOLDOUT | 2019-01-01 → 2022-12-31; n 988; net −0.22 bp, NW t −0.09, AC₁ −0.104, p 0.133 / 0.150 → FAIL | `A_HOLDOUT_REPORT.md` |
| Gross | +4.41 bp (TRAIN) → +3.13 bp (HOLDOUT); **gross significance not reported** | `A_HOLDOUT_CLOSURE.md` decomposition *(secondary)* |
| Verdict | Retired at HOLDOUT; SEALED untouched | Closure |

### 3.9 Trend sleeve

| Field | Value | Source |
|---|---|---|
| Universe | NSE SSF names, PIT F&O-listed and liquid; ≥ 12 months history | `sleeves/TREND_PHASE0_PRE_REGISTRATION.md` §2 |
| Price | Continuous back-adjusted near-month futures; roll at ≤ 3 trading days to expiry (ratio back-adjust) | §3, §3.2 |
| Signal | Log returns h ∈ {63, 126, 252}; vol = std of 60-day daily log returns × √252; z_h = ret_h/vol; tsmom = mean_h z_h; winsorise ±3 SD, cross-sectional z | §3 |
| Neutralisation | Cross-sectional OLS on 252-day beta to Nifty 50 + NSE sector dummies; residual is the signal | §4 |
| Target | Forward one-month **spot** adjusted return | §5 |
| Portfolio (pre-reg) | z-weighted, beta/sector/dollar neutral, ADV cap 10% of 20-day futures ADV, 0.25σ no-trade band, monthly | §6 |
| Reported spread | Quintile L/S, net | `TREND_TRAIN_REPORT.md` Quintile section |
| TRAIN | 2017-02-28 → 2021-12-31; 59 formations; mean 153 names | TRAIN report, Substrate |
| Result | Mean IC +0.02194, SD 0.1486, t 1.134, p 0.131, AC₁ 0.022; halves +0.0546 / −0.0097 | TRAIN report, Rank-IC |
| Gross / net | L−S gross −3.47%; net −4.06%; drag 59.4 bp; turnover 0.6948 | TRAIN report, Quintile |
| Verdict | Gate 2 FAIL; HOLDOUT (2022–2023) never read | TRAIN report, Predictions; pre-reg §9 |

### 3.10 Carry v1 / v2

| Field | Value | Source |
|---|---|---|
| Universe | PIT F&O single stocks; drop if trailing 20-day median futures turnover < ₹5 Cr | `carry/CARRY_PHASE0_PRE_REGISTRATION.md` §2 |
| Signal | `raw = ((F − S)/S)·(365/DTE)` on near-month; minus expected annualised dividend yield (announced dividends); cross-sectional demean; winsorise ±3 SD; z-score | §3 |
| Roll | Near-month until T−3 trading days, then next month | §3.4 |
| Neutralisation | 252-day beta to Nifty + NSE sector dummies, cross-sectional OLS residual | §4 |
| Target | Forward one-month return. **Implemented as spot adjusted return** (`fwd_ret_1m`) | §5; `FUNNEL_CARRY_CONDITIONING_AUDIT_2026-09-24.md` table, line 50 *(secondary)* |
| Portfolio (pre-reg) | z-weighted, beta/sector/dollar neutral, ADV cap 10% of 20-day ADV, 0.25σ band, monthly | §6 |
| Portfolio used in gates | **Quintile, equal-weight** L/S; slippage 5 bp/side fixed; gross ₹1 Cr | `carry/CARRY_NET_SPREAD_REPORT.md` §1–§2 |
| Sign | v1 −1 (short high residual basis); v2 +1 | v1 §1; `CARRY_V2_PRE_REGISTRATION.md` §1 |
| v1 TRAIN | 2016-03 → 2020-12; IC +0.041, p 1.8e-4 (wrong sign → v1 FAIL) | v2 §0 |
| v2 HOLDOUT | 2021-01-31 → 2022-12-31; n 23; mean IC +0.05443, SD 0.0790, t 3.306, p 1.6e-03 (α 0.025) | `CARRY_HOLDOUT_IC_REPORT.md` §1 |
| Net spread | TRAIN gross +14.37% / net +12.84% (58 formations); HOLDOUT gross +8.42% / net +6.96% (24) | Net-spread report §2 |
| SEALED | 2023-01-01 → 2026-07-20; n 42; IC +0.06104, t 4.49, NW t 4.10; gross +22.23%, net +20.52% | `CARRY_SEALED_REPORT.md` §1–§2 |
| Post-hoc findings | Futures spread gross t −0.83 (TRAIN) / −0.79 (HOLDOUT); convergence cost t −16.7 / −10.6; v2 sign is anti-KMPV carry; dividend adjustment sign inverted in `build_carry.py:251-252` | `carry/CARRY_FUTURES_TRANSLATION_REVIEW.md` Verdict, §1 *(secondary)* |

### 3.11 Late-cycle single-stock straddle selling (exploratory)

| Field | Value | Source |
|---|---|---|
| Universe | Every F&O stock per monthly expiry (~160–190 names) | `strategies/OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` §2, §5 |
| Data | `stock_options_bhavcopy.duckdb` (+ futures bhavcopy for ATM) | §0 |
| Entry | Sell the ATM straddle at the close k sessions before expiry, k ∈ {cycle start, 15, 10, 7, 5, 3}; ATM = strike nearest the same-expiry future; both legs traded | §2 Construct |
| Liquidity filter | §2: "both legs traded". §9.1 verdict sentence: "ATM legs each traded ≥ 100 contracts". **Which filter produced the §2/§5 tables is not stated** | §2, §9.1 |
| Exit | Buy back at the T−1 close (close if traded, else `settle`) | §0, §2 |
| Exclusions | Front-future daily move > 25% (CA jump); missing exit rows | §2 |
| Return | (entry premium − exit premium)/entry premium; averaged within expiry, t across expiries | §2 |
| Discovery | 2016-02 → 2022-12; 80–81 expiries; 10-before gross +13.8%, t 6.05; net @2% +11.5%, t 4.98 | §2.1 table |
| Confirmation | Entries 2023-01-01 → 2026-08-24; 43 expiries; 10-before gross +10.6%, t 3.78; net @2% +8.2%, t 2.90; P5 vrp60 IC +0.014, t 1.24 FAIL | §4, §5.1, §5.2 |
| Selection | 6 offsets; 10-before is the in-sample best | §2.3 "Multiple testing" |
| Status | EXPLORATORY; not pre-registered; not a gated read | Status line |

### 3.12 MSRP D1 — forecast-gated Nifty straddle (in-sample triage)

| Field | Value | Source |
|---|---|---|
| Signal | Ratio `E[RV]/implied_vix`, with `E[RV]` = certified `expected_next_day_realized_vol` artifact | `strategies/MSRP_PHASE7_FEE_TRIAGE.md` rank-correlation list; `MSRP_PHASE7_RESEARCH_RESET.md` predecessor note |
| Gates | Short if ratio ≤ q10/q20/q30; long if ≥ q70/q80/q90 (dev-window quantiles); D1 = short ≤ q20 + long ≥ q80 | Triage arms table |
| Instrument | Nifty weekly options; DTE median 6 (p10 2, p90 8); 1 lot | Triage header |
| Strike selection | **UNKNOWN** in this report ("valid straddle" only) | — |
| Entry / exit | Bhavcopy open → close ("open->close return") | Caveats; rank-correlation item 2 |
| Window | 2023-01-02 → 2025-12-31; 695 tradable days; coefficients fit on the same window (in-sample) | Header, Caveats |
| Result | Transmission ρ(RV_{t+1}, long-straddle return) 0.093; ρ(signal, return) −0.027; unconditional short gross +₹197,110 (Sharpe 0.74 net); D1 combined net −₹120,182 | Arms table; D1 block; correlations |
| Verdict | STOP; "do not pre-register D1" | Triage conclusion |

### 3.13 Nifty/BankNifty ratio z-score (exploratory)

| Field | Value | Source |
|---|---|---|
| Series | Price ratio BNF/N50 | `index_research/NIFTY_BANKNIFTY_PAIR_RESEARCH.md` §1.2 |
| Z-score formula, hedge ratio, leg sizing | **UNKNOWN** (not defined in the report) | — |
| EOD grid | 45 combos over entry_z, exit_z, window (days); top-5 shown; exact grid values **UNKNOWN** beyond those rows | §3.1 |
| Intraday grid | 27 combos: entry_z 2.0–3.0, exit_z 0.5–1.0, window 60–240 min | §2.3 |
| Walk-forward | Params chosen on 2016–2019: entry_z 1.0, **exit_z 1.5**, window 10d; exit semantics with exit_z > entry_z **not explained** | §4.1 |
| Costs | 3 bp round trip per leg; lot rounding, margins and roll not modelled | Header; §6 table |
| Data | EOD 2016-01-01 → 2026-07-31 (2,620 obs); 1m 2023-01-02 → 2026-07-03 | Header |
| Results | Johansen trace 14.42 < 15.49; half-life 166 days; bootstrap p 0.354 (no costs); walk-forward +2,875 bp total, 2022–23 −2,451 bp; all 27 intraday combos negative | §1.3, §1.4, §3.2, §4.1, §2.3 |
| Status | Exploratory; not pre-registered; the last month was read | §6 governance row |

### 3.14 Gann GF-1, GF-4T/R8, GF-10 (non-confirmatory screen)

| Field | Value | Source |
|---|---|---|
| Universe / unit | PIT N100; stock-week, formation at close of D_L (last session of the ISO week) | `ptms/PTMS_GANN_STAGE1_FREEZE_DOCUMENT_DRAFT_2026-09-19.md` rows RR-4, RR-7, 27 |
| Swing detector | K3: up-switch after 3 sessions of higher highs **and** higher lows; down-switch after 3 sessions of lower lows; strict inequality; swing usable from close of confirming session | R-1 |
| Outcome (O-R10) | Binary: any penetration strictly beyond the reference swing within the next 5 sessions; intraday high/low basis | R-2, RR-5 |
| GF-1 score | Calendar-day counts P4 = {36, 48, 72, 96, 108, 144} + 144k from running highest high / lowest low; look-ahead = calendar dates D_L+1 … D_L+7 | R-3, R-9, RR-7 |
| GF-4T/R8 score | 1 if any date in the next 7 days falls in {7–12, 18–21, 28–31, 42–49, 57–65, 85–92, 112–120, 150–157, 175–185} calendar days from the last confirmed K3 swing | Freeze line 443; `PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md` line 467 |
| GF-10 score | In S9 bull state and a K3 decline: 1 once the decline's calendar duration exceeds the preceding completed decline's, before any up-switch; outcome = break of last K3 swing low within 5 sessions; bear mirror pooled | R-5 |
| Direction for GF-1 / GF-4T/R8 | Defined in freeze §2.2–§2.3 (G-2); **not extracted in this audit** | R-2 note |
| Statistic | T_c = mean over formation weeks of per-date Spearman IC of score vs O-R10 | Freeze line 1163 |
| Null | Block-bootstrap surrogates, B = 1999, mean block 20, seed 42; α 0.05/3 one-sided | Freeze row RR-8, line 299; `PTMS_GANN_STAGE1_SCREEN_REPORT.md` §1 |
| Window | 2011-03-25 → 2022-12-30 | Freeze document line 283 (ruling text on the non-confirmatory screen) |
| n (dates) | 609 / 606 / 320 | Screen report §3 |
| Result | T_c −0.0101 / +0.0334 / +0.0473; p_sur 0.953 / 0.980 / 0.214 | Screen report §4 |
| Verdict | Retired from forward testing under this protocol; explicitly **not** "Gann's rule is false" | Screen report §4 |

### 3.15 F1 — 12-1 momentum with ATR bracket (feasibility screen)

| Field | Value | Source |
|---|---|---|
| Signal | 12-1 cross-sectional momentum, skip most recent month | `sfb_f1/F1_FEASIBILITY_SCREEN_REPORT.md` Configuration |
| Portfolio | ≤ 10 names, equal-weight, long-only, monthly formation; notional ₹10 L | Configuration; spec §3 |
| Universe | Cash liquidity proxy: trailing-63-day median traded value ≥ ₹5 Cr | Configuration |
| Price path | Cash price as the futures proxy; basis ignored | Spec §3; report caveat 3 |
| ATR period | 21 days | Best Bracket Params |
| Bracket grid | 4×4×4 over (n, k_sl, k_tp). Documented endpoints: n min 5; k_sl 1.0 … 2.5; k_tp 2.0 … 5.0. **Interior grid values UNKNOWN** | Report; `F1_FEASIBILITY_SCREEN_CODE_REVIEW.md` line 18; `_REPORT_REVIEW.md` line 45 |
| Selected | n = 5 (max hold within bracket), k_sl 2.5, k_tp 5.0 (three grid boundaries) | Report; verdict review line 30 |
| Exit logic | SL before TP; open-gap step uses the **open** in code, "daily low" in the report text; past 5 bars → month-end fallback | Verdict review line 30, line 66 *(secondary)* |
| Windows | TRAIN 2012–2018 (n 83); HOLDOUT 2019–2022 (n 47) | Report tables |
| Result | TRAIN gross +1.81%/formation; net (opt/mid/pess) +1.54 / +1.32 / +0.87%, all CI lows ≤ 0; HOLDOUT gross +3.32%, net +3.12 / +2.97 / +2.67%, CIs > 0; DaysH 18.8 / 18.5; MaxDD −42 to −46% (TRAIN) | Report tables |
| Test | Block-bootstrap CI on expectancy (block length **UNKNOWN**) | Spec §5 |
| Verdict | Printed GO; superseded NO-GO | Verdict review; CLAUDE.md F1 banner *(secondary)* |

---

## 4. Partially / relatedly tested constructs

| Construct | What is documented | Status | Source |
|---|---|---|---|
| DRA HMM-gated EMA | Daily 3-state GaussianHMM (features incl. VIX level, VIX 90d percentile, ratio, slope, RV); rank-based state map; overrides VIX ROC5 > 0.20 or pctl90 > 0.85 → SHOCK. Long entry: P(Expansion) > 0.70 for ≥ 1 day, EMA(9) > EMA(21) on 15m, vol_z > 1 and close > VWAP (both bypassed on index), no open position. Exit: P(Shock) or P(Contraction) > 0.65; SL entry − 1.5·ATR; TP entry + 2.0·ATR; time stop 20 × 15m. **ATR period UNKNOWN.** Walk-forward 9 × (9-month train / 3-month test / 3-month step), May 2023 → Feb 2026. 200 trades, −₹1,647, win 44.7%; **no significance test** | LEGACY | `strategies/DRA_TECHNICAL_DOSSIER.md` §3.2–§3.3, data section, §8.1 |
| Stage-A Gate 0 families | Priced from fees + power module only. F-RANGE breakout (60m) required gross S 2.49 → implausible; failed breakout 2.02 → plausible, unmeasured; F-VOL, F-TOD, F-REL implausible. **No entry/exit rule was ever specified to a testable level** | PRICED-INFEASIBLE / CATALOGUED | `strategies/STAGE_A_GATE0_REPORT.md` §2; `STAGE_A_DISCOVERY_LAB_DESIGN.md` D-A7 |
| MRLC | Four-layer conjunction (25-day SMA divergence, VPVR POC, sweep, reclaim); "every price in the case study is invented" | CATALOGUED-ONLY | `strategies/MRLC_CONSTRUCT_ASSESSMENT.md` status line, §5.5 |
| Flow | OI-positioning crowding, negative IC declared; δ [0.015, 0.03], SD [0.10, 0.18]; max power 0.6053 | RFA-ABANDON | `rfa_gate/FLOW_RFA.md` |
| RS-MOM | Nifty/BankNifty relative-strength momentum, weekly; max power 0.337 | RFA-ABANDON | CLAUDE.md *(secondary)*; `index_research/RS_MOM_RFA.md` |
| OSC | IV-surface richness, probe on burned 2023–25; within-moneyness IC +0.0167, t 2.06 | Probe → RFA-ABANDON | `OSC_RFA_ABANDON.md` |
| STOCK-STRADDLE-M10 | Forward pre-registration of 3.11; cycle 1 entry 2026-10-12 | Pre-registered, no result | `strategies/STOCK_STRADDLE_M10_PRE_REGISTRATION.md` |

---

## 5. Parameter inventory

| Construct | Lookbacks / lengths | Thresholds / bands | Cadence · hold | Stops / targets | Filters |
|---|---|---|---|---|---|
| PSB-1 C1 | 5-day return | Quintiles | Weekly · 1 wk | None | Formation-complete |
| PSB-1 C2 | 5-day return; 52-week beta (≥ 40) | Quintiles | Weekly · 1 wk | None | ≥ 40/52 weeks |
| PSB-1 C3 | 5-day delivery mean (≥ 3); 60-day baseline to t−5 (≥ 40) | Quintiles | Weekly · 1 wk | None | σ > 0 |
| PSB-2 C2 | Fortnight mean (≥ 8); 252-day baseline to t−21 (≥ 150) | Enter Q1, exit outside top 2 quintiles | Fortnightly · ~15 d | None | σ > 0 |
| PSB-2 C4 | 12-month, skip 1 month | Top quintile | Monthly · 6-month staggered | None | 12 prior grid dates |
| CB-N50 | Momentum L ∈ {5, 10, 20}; reversal 1 day; basis spot | z clip ±3; breadth 0.35 / 0.65 | Daily · open t+1 → open t+2 | None | N ≥ 30 |
| ISD F1 | Window 30 / 45 min from 09:15 | Bands 20% / 40% | Intraday · entry → 15:29 | None | ADV cap 10% of 20-session ADV |
| ISD F4 | Overnight gap | Bands 20% / 40% | Intraday · 09:16 → 15:29 | None | CA ex-dates excluded; ADV cap |
| A | Window 30 / 45 bars | Sign of feature | Daily · bar 31/46 → 15:14 | None | Session-validity rule only |
| Trend | 63 / 126 / 252-day returns; 60-day vol; 252-day beta | Winsorise ±3; 0.25σ band | Monthly · 1 month | None | ADV cap 10% |
| Carry | Near-month basis × 365/DTE; 252-day beta; 20-day ADV | Winsorise ±3; 0.25σ band; ₹5 Cr floor | Monthly · 1 month | None | Roll T−3 |
| Straddle study | Offsets {start, 15, 10, 7, 5, 3} sessions | ATM nearest future | Monthly expiry · to T−1 | None | Both legs traded (see §6); > 25% CA-jump drop |
| MSRP D1 | E[RV] artifact (fixed coefficients) | Quantiles q10–q90 | Daily · open → close | None | None stated |
| Pair z | EOD window grid; intraday 60–240 min | entry_z / exit_z grids | EOD / intraday | UNKNOWN | UNKNOWN |
| Gann | K3 = 3 sessions; P4 counts; R8 windows; 5-session outcome; 7-day look-ahead | Binary score | Weekly | None | PIT N100 |
| F1 | 12-1; ATR 21 | k_sl 2.5, k_tp 5.0 (selected) | Monthly · ≤ 5-bar bracket, else month-end | ATR SL / TP | ₹5 Cr liquidity |
| DRA (legacy) | EMA 9 / 21 (15m); HMM 3 states | P > 0.70 / 0.65 | 15m intraday · ≤ 5 h | SL 1.5·ATR, TP 2.0·ATR, **ATR period UNKNOWN** | HMM regime; overrides |

**Classical indicators actually used in any tested construct:**
- ATR(21) bracket (F1)
- EMA 9/21 alignment (DRA, legacy)
- K3 swing detector (Gann)

Nothing else. RSI, Stochastic, CCI, Williams %R, MFI, MACD, Bollinger, Keltner, Donchian, Supertrend,
Parabolic SAR, Ichimoku, ADX, OBV and VWAP appear in **no tested construct**.

---

## 6. Parameters that are UNKNOWN or insufficiently documented

| # | Construct | Item | State |
|---|---|---|---|
| 1 | CB-N50 | Which futures contract feeds the basis feature; its annualisation day-count | UNKNOWN |
| 2 | CB-N50 | The Bonferroni m = 9 family: only 5 of 9 lookback tests are printed; the criterion that made L = 20 "best" is not stated | Insufficient |
| 3 | ISD F4 | Per-cell IC values are absent from the script-generated report (p only); "Net bp −3196.2" has no stated unit or aggregation | Insufficient |
| 4 | ISD F1 | Cell IC (−0.0166, t −2.81) exists only in the secondary reassessment memo | Secondary only |
| 5 | A | Gross-return significance on HOLDOUT not reported; the gross figures appear only in the closure memo | Insufficient |
| 6 | Carry | Dividend PIT-ness not certifiable (no announcement date in store); 2.56% of basis cells exposed | Documented limitation |
| 7 | Carry | κ in the pre-reg reads "e.g. 5 bp"; the fixed 5 bp appears only in the net-spread report | Pinned post-hoc in the report |
| 8 | Straddle study | Liquidity filter behind the §2/§5 tables: "both legs traded" vs "≥ 100 contracts" | Ambiguous |
| 9 | Straddle study | How the "2% spread" is charged (per leg, per side, or on premium) | UNKNOWN |
| 10 | MSRP D1 | Strike-selection rule; artifact coefficients | UNKNOWN in the triage report |
| 11 | Pair z | Z-score definition (ratio vs log ratio, rolling mean/SD), hedge ratio, leg sizing, full 45-combo EOD grid, stop rules, exit semantics when exit_z > entry_z | UNKNOWN |
| 12 | F1 | Interior bracket-grid values; bootstrap block length | UNKNOWN |
| 13 | Gann | GF-1 / GF-4T/R8 direction rules | Documented (freeze §2.2–§2.3), not extracted here |
| 14 | DRA | ATR period in the executor; exact HMM feature list beyond those named; primary report not in repo | UNKNOWN / LEGACY |
| 15 | Trend | NSE sector-dummy source and its PIT-ness | Not stated in pre-reg |

---

## 7. Research-result inventory

| Construct | Window | n | Effect | Statistic | Gross | Net (reported) |
|---|---|--:|---|---|---|---|
| PSB-1 C1 | Dev 2012–22 | 569 | IC +0.0232 | t 3.76, p 9.3e-05 | Q1−Q5 +1.05% | −16.80% |
| PSB-1 C2 | Dev 2012–22 | 529 | IC +0.0352 | t 6.63, p 4.1e-11 | Q1−Q5 +14.95% | −8.60% |
| PSB-1 C3 | Dev 2020–22 | 143 | IC +0.0248 | t 2.93, p 2.0e-03 | Q1−Q5 +17.45% | −2.45% |
| PSB-2 C2 | Dev 2020-09–22 | 55 | IC +0.0349 | t 2.49, p 8.0e-03; power 0.92 | +7.03% | +4.57% |
| C2 Phase 0.5 | TRAIN 2011–18 | 95 / 215 | IC 0.022–0.023 | power 0.42–0.66 | −1.54 to +1.88% | −2.95 to −0.14% |
| PSB-2 C4 | Dev 2012–22 | 131 | IC +0.0466 | t 2.55, p 6.0e-03; power 0.41 | +3.08% | +2.87% |
| CB-N50 TRAIN | 2016–19 | 983 | IC +0.0587 (combined) | NW t 11.36 | — | Not evaluated |
| CB-N50 HOLDOUT | 2020–22 | 746 | IC +0.0294 | NW t 4.35, p 1.5e-05 | — | Not evaluated |
| ISD F1 | TRAIN 2023-01 → 2024-11 | 474 | IC −0.0166 (w0945) *(secondary)* | t −2.81 | — | — |
| ISD F4 | TRAIN 2023-01 → 2024-11 | 474 | IC −0.0289 | NW t −6.09, p 0.0000 | +3.18 to +6.02 bp/session *(secondary)* | Negative |
| A TRAIN | 2012–18 | 1,699 | w45 net +1.27 bp | sign p 0.0030 | +4.41 bp | +1.27 bp |
| A HOLDOUT | 2019–22 | 988 | Net −0.22 bp | NW t −0.09, p 0.133 | +3.13 bp *(secondary)* | −0.22 bp |
| Trend TRAIN | 2017-02 → 2021-12 | 59 | IC +0.0219 | t 1.13, p 0.131 | −3.47% | −4.06% |
| Carry v1 TRAIN | 2016-03 → 2020-12 | 58 | IC +0.041 (wrong sign) | p 1.8e-4 | +14.37% (v2 sign) | +12.84% (v2 sign) |
| Carry v2 HOLDOUT | 2021–22 | 23 | IC +0.0544 | t 3.31, p 1.6e-03 | +8.42% | +6.96% |
| Carry v2 SEALED | 2023-01 → 2026-07 | 42 | IC +0.0610 | t 4.49, NW t 4.10 | +22.23% | +20.52% |
| Straddle discovery | 2016-02 → 2022-12 | 80–81 exp | +13.8%/cycle (10-before) | t 6.05 | +13.8% | +11.5% @2% |
| Straddle confirmation | 2023-01 → 2026-08 | 43 exp | +10.6%/cycle | t 3.78 | +10.6% | +8.2% @2% (t 2.90) |
| MSRP D1 | 2023–25 (in-sample) | 695 days | ρ(signal, return) −0.027 | — | Short arm +₹197k | D1 −₹120k |
| Pair EOD | 2016–26 | — | Walk-forward +2,875 bp | Bootstrap p 0.354 | +709.5 bp (bootstrap) | Walk-forward net |
| Pair intraday | 2023–26 | 27 combos | All negative | — | — | −3,295 to −16,499 bp |
| Gann GF-1 / 4T / 10 | 2011-03 → 2022-12 | 609 / 606 / 320 | T_c −0.010 / +0.033 / +0.047 | p_sur 0.953 / 0.980 / 0.214 | — | — |
| F1 TRAIN | 2012–18 | 83 | +1.81%/formation gross | CI low ≤ 0 | +1.81% | +0.87 to +1.54% |
| F1 HOLDOUT | 2019–22 | 47 | +3.32%/formation gross | CI > 0 | +3.32% | +2.67 to +3.12% |
| DRA (legacy) | 2024-02 → 2026-02 tests | 200 trades | −₹1,647 | None | — | — |

## 8. Research-status / verdict inventory

| Status | Constructs |
|---|---|
| TESTED-PASS | Carry v2 (HOLDOUT, SEALED on spot returns); CB-N50 IC (TRAIN, HOLDOUT) |
| TESTED-FAIL | Trend (TRAIN); ISD F1 (sign); Carry v1 (sign); Gann ×3 (non-confirmatory); MSRP D1 (in-sample); C2 Phase 0.5 (power) |
| HOLDOUT-FAIL | A (net-of-cost gate; gross positive, untested) |
| STAT-EDGE / COST-KILLED | PSB-1 C1, C2, C3 (dev in-sample); ISD F4 (TRAIN) |
| Passed statistics, dropped on power | PSB-2 C4 |
| EXPLORATORY | Straddle study (replicated); pair z-score (failed); F1 screen (GO superseded) |
| PRICED-INFEASIBLE | Gate 0: F-RANGE breakout, F-VOL, F-TOD, F-REL |
| RFA-ABANDON | Flow, RS-MOM, OSC |
| CATALOGUED-ONLY | F-RANGE failed breakout, MRLC, Gann secondary/descriptive constructs |
| LEGACY | DRA HMM-gated EMA |
| Pre-registered, not yet run | STOCK-STRADDLE-M10 |

## 9. Source / evidence map

| Construct | Specification source | Result source | Secondary sources used |
|---|---|---|---|
| PSB-1 C1–C3 | `psb/PSB1_PROTOCOL.md` §2–§9 | `psb/PSB1_C{1,2,3}_REPORT.md` | CLAUDE.md (verdict wording) |
| PSB-2 C2, C4 | `psb/PSB2_PROTOCOL.md` §2–§9 | `psb/PSB2_C{2,4}_REPORT.md`; `C2_PHASE0_5_MINIBATTERY.md` | — |
| CB-N50 | `index_research/CB_N50_PRE_REGISTRATION.md` §1, §3, §5 | `CB_N50_TRAIN_REPORT.md`, `CB_N50_HOLDOUT_REPORT.md` | — |
| ISD F1 / F4 | `strategies/ISD_PHASE0_PRE_REGISTRATION.md` §2–§10 | `ISD_BATTERY_TRAIN_REPORT.md` | `ISD_PROGRAM_REASSESSMENT.md` §1, §3 |
| A | `index_research/A_PHASE0_PRE_REGISTRATION.md`; `A_CONSTRUCT_DEFINITION.md` | `A_TRAIN_REPORT.md`, `A_HOLDOUT_REPORT.md` | `A_HOLDOUT_CLOSURE.md` |
| Trend | `sleeves/TREND_PHASE0_PRE_REGISTRATION.md` §2–§9 | `sleeves/TREND_TRAIN_REPORT.md` | — |
| Carry | `carry/CARRY_PHASE0_PRE_REGISTRATION.md` §2–§9; `CARRY_V2_PRE_REGISTRATION.md` | `CARRY_NET_SPREAD_REPORT.md`, `CARRY_HOLDOUT_IC_REPORT.md`, `CARRY_SEALED_REPORT.md` | `CARRY_FUTURES_TRANSLATION_REVIEW.md`; `FUNNEL_CARRY_CONDITIONING_AUDIT_2026-09-24.md`; `CARRY_SUBSTRATE_CERTIFICATION.md` |
| Straddle study | `strategies/OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` §2, §4 | same, §2.1, §5 | — |
| MSRP D1 | `strategies/MSRP_PHASE7_FEE_TRIAGE.md` | same | `MSRP_PHASE7_RESEARCH_RESET.md` |
| Pair z-score | `index_research/NIFTY_BANKNIFTY_PAIR_RESEARCH.md` | same | — |
| Gann | `ptms/PTMS_GANN_STAGE1_FREEZE_DOCUMENT_DRAFT_2026-09-19.md`; `PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md` | `ptms/PTMS_GANN_STAGE1_SCREEN_REPORT.md` | — |
| F1 | `sfb_f1/F1_FEASIBILITY_SCREEN_SPEC.md` §2–§6 | `F1_FEASIBILITY_SCREEN_REPORT.md` | `F1_FEASIBILITY_SCREEN_VERDICT_REVIEW.md`, `_CODE_REVIEW.md`, `_REPORT_REVIEW.md` |
| DRA | — (primary `docs/HMM_REGIME_STRATEGY_REPORT.md` not in repo) | — | `strategies/DRA_TECHNICAL_DOSSIER.md` |

## 10. Gaps in our own research documentation

1. **A: stale grid table.** `A_CONSTRUCT_DEFINITION.md` §9 still lists "Exit 15:29 close". The frozen
   pre-registration and §3 (D6) pin 15:14.
2. **Carry: specification vs implementation.**
   - The pre-registered portfolio is z-weighted with ADV caps, but the net-spread gates use an equal-weight quintile book.
   - The dividend adjustment is subtracted, not added (sign error), in the frozen code.
   - The v2 sign rationale misreads KMPV.
   - The target is spot, not futures.
   
   All of these are recorded post-hoc; none is repaired.
3. **F1: report text contradicts code.**
   - The open-gap step uses the open in code but is described as "daily low".
   - The bracket grid's interior values are recorded nowhere.
   - An earlier run's TRAIN window included pre-2012 formations; the final run shows n 83, but no document states the fix explicitly.
4. **ISD: key statistics only in secondary documents.** F1's IC and F4's per-cell gross are only in the reassessment memo, not in the script-generated report.
5. **CB-N50: selection family incomplete.** m = 9 is declared but only five tests are printed; the lookback-selection criterion is unstated; the basis feature's contract and day-count are unspecified.
6. **Pair study: rule not reconstructable.** The z-score, hedge ratio and exit semantics are not defined anywhere, so the exact rule cannot be reconstructed.
7. **Straddle study: two liquidity filters.** Two different filters are named, and the table they belong to is not identified.
8. **MSRP D1: strike selection undocumented** in the triage report.
9. **DRA: primary evidence not migrated.** Every DRA rule and result is second-hand.
10. **PSB-1 C1 "gross" ambiguity.** The CLAUDE.md summary "Q1-Q5 gross +1.1%" is the long-short spread. The protocol's
    gross spread (top quintile − baseline) is **−4.01%**. Both are in the report; the summary quotes only one.

---

## Answer

**Largely yes for the cross-sectional constructs; partially for the rest; and for the single-instrument
technical-indicator mechanisms that dominate the Vault, the question does not arise, because no such
rule was ever specified or tested.**

- **Exact rules and parameters are recoverable** from frozen, primary records for PSB-1 C1–C3, PSB-2 C2/C4,
  CB-N50, ISD F1/F4, A, Trend, Carry and the three Gann constructs. For Carry and A, the implementation
  diverges from the written specification in documented ways (§10.1, §10.2).
- **They are only partially known** for the straddle study (filter, spread charge), MSRP D1 (strike rule),
  the F1 screen (grid, open-gap rule) and the legacy DRA strategy (ATR period, primary report missing).
- **They are not known** for the Nifty/BankNifty z-score study: its defining formula, hedge ratio and
  exit semantics are absent from the record.
