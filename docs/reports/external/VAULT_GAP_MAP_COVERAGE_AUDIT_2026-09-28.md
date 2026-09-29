# Vault Gap Map — Coverage Audit of the AR/RD Claims

**Date:** 2026-09-28
**Audits:** `docs/reports/external/VAULT_MECHANISM_GAP_MAP_2026-09-28.md` (commit `2230023`)
**Method:** each AR/RD claim traced to the primary internal report. The only secondary sources used are
two, both flagged: the DRA dossier (its primary report was not migrated) and `CLAUDE.md`'s gate table.
The latter is used only for the Carry HOLDOUT/SEALED figures (A8, A10) and the RS-MOM power figure (A1),
none of which changes a verdict. No external source, no market data, no new computation. **Costs are not
used to adjudicate.** Where a gate was net-of-cost, the gross/statistical result is reported separately.

**Status vocabulary (kept distinct):** TESTED-PASS · TESTED-FAIL (statistics) · HOLDOUT-FAIL ·
STAT-EDGE / COST-KILLED · PRICED-INFEASIBLE (zero data read) · RFA-ABANDON (zero data read) ·
CATALOGUED-ONLY · EXPLORATORY (not pre-registered) · LEGACY (primary report not in repo) · NEVER RESEARCHED.

**Verdicts:** VERIFIED AR · VERIFIED RD · NOT ACTUALLY TESTED · INSUFFICIENT EVIDENCE.

---

## A. Coverage audit table

### A1. MA trend-transition — claimed **AR**

| Evidence cited | Construct actually tested | Mechanism actually tested | Instrument / universe | Timeframe · hold | Entry / exit | Period | n | Result | Status | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| Trend sleeve | Vol-scaled multi-horizon (63/126/252d) TSMOM, **ranked cross-sectionally**, beta/sector-neutralised | Cross-sectional ranking by own-trend strength | ~153 NSE SSF names, PIT | Daily signal · monthly rebalance | Quintile L/S by rank | TRAIN 2017-02-28 → 2021-12-31 | 59 formations | Mean IC +0.0219, t 1.13, p 0.131; 2nd-half IC −0.0097 | TESTED-FAIL (not significant) | `sleeves/TREND_TRAIN_REPORT.md` "Rank-IC Results"; construct `TREND_PHASE0_PRE_REGISTRATION.md` §3 |
| A (index intraday) | Sign of return from opening print to bar 30/45 → hold same direction | Intraday time-series continuation, single instrument | Nifty 50 (1m), futures vehicle | 1m · entry bar 31/46 → exit 15:14 close, EOD-flat | Long if window return > 0, short if < 0; every session | TRAIN 2012–2018; HOLDOUT 2019–2022 | 1,699 / 988 | TRAIN w45 p 0.0030 (net); HOLDOUT net −0.22 bp, p 0.133 / 0.150. Gross +4.41 → +3.13 bp; **gross HOLDOUT significance not reported** | TRAIN-PASS → HOLDOUT-FAIL (net gate) | `index_research/A_HOLDOUT_CLOSURE.md` gate table + decomposition; `A_CONSTRUCT_DEFINITION.md` §1–§4; `A_TRAIN_REPORT.md` |
| DRA HMM | HMM-regime-gated EMA(9)>EMA(21) alignment entries, ATR SL 1.5 / TP 2.0 | MA alignment filtered by regime | Nifty 50 cash, 15m | Intraday 15m | EMA alignment + HMM expansion state; ATR bracket | Walk-forward 9 windows, tests 2024-02 → 2026-02 | 200 trades | −Rs 1,647, 44.7% win; **no significance test**; "fresh EMA crossover yielded 1 trade in 9 windows" | LEGACY — source `docs/HMM_REGIME_STRATEGY_REPORT.md` **not migrated** | `strategies/DRA_TECHNICAL_DOSSIER.md` §8.1, §9 |
| RS-MOM | — | — | — | — | — | — | — | Max power 0.337 | RFA-ABANDON, no data read | CLAUDE.md RFA section (`index_research/RS_MOM_RFA.md`) |
| F1 / PSB-2 C4 | 12-1 cross-sectional momentum | Cross-sectional 12-month momentum | Cash-liquid names / NIFTY-200 | Monthly | Rank-based | see A5 | — | — | Different mechanism (cross-sectional) | `sfb_f1/F1_FEASIBILITY_SCREEN_REPORT.md`; `psb/PSB2_C4_REPORT.md` |

**Verdict: NOT VERIFIED AS AR → VERIFIED RD (partial).** No experiment tests an MA crossover/transition as a
standalone time-series rule. The Trend sleeve ranks names cross-sectionally, and A uses a single intraday
window sign, not moving averages. The only MA-alignment test (DRA) is LEGACY: second-hand, regime-gated,
with no significance test, so INSUFFICIENT EVIDENCE on its own.

### A2. MACD / momentum — claimed **AR**
No experiment uses MACD, EMA differences, or a momentum-rate trigger on a single instrument. The coverage
claim rested on "same mechanism as A1".
**Verdict: NOT ACTUALLY TESTED** (RD at most, by the same partial evidence as A1).

### A3. Oscillator reversion — claimed **RD**

| Evidence | Construct | Mechanism tested | Universe | Timeframe · hold | Entry / exit | Period | n | Result | Status | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| PSB-1 C1 | s = −r(t−5, t) | Cross-sectional 5-day reversal | NIFTY-200 PIT | Weekly formation · 1 week | Quintile rank | Dev 2012–2022 (single in-sample window) | 569 | Mean IC +0.0232, one-sided t 3.76, p 9.3e-5; net −16.8% | STAT-EDGE (in-sample) / COST-KILLED | `psb/PSB1_C1_REPORT.md` §6; `PSB1_PROTOCOL.md` §5 C1 |
| PSB-1 C2 | Market-residual 5-day reversal | Idiosyncratic reversal | NIFTY-200 PIT | Weekly | Quintile rank | Dev 2012–2022 | 529 | Mean IC +0.035, t 6.63 | STAT-EDGE (in-sample) / COST-KILLED | `psb/PSB1_C2_REPORT.md` |
| CB-N50 | 1-day reversal feature (and L=5/10/20 "momentum", which came out negative, i.e. reversal) | Cross-sectional 1–20-day reversal | Nifty 50 PIT | Daily · next-day open-to-open | Rank IC only | TRAIN 2016–2019; HOLDOUT 2020–2022 | 983 / 746 | TRAIN reversal L1 IC +0.0459, NW t 8.42. HOLDOUT (reversal+basis **combined**) IC +0.0294, NW t 4.35 | TESTED-PASS (IC), HOLDOUT-PASS (combined) | `index_research/CB_N50_TRAIN_REPORT.md` lookback table; `CB_N50_HOLDOUT_REPORT.md` |
| ISD F4 | Fade of overnight gap | Cross-sectional overnight-gap reversal | PIT F&O stocks, 1m | Entry 09:16 → exit 15:29 | Rank bands 20/40% | TRAIN 2023-01-02 → 2024-11-30 | 474 sessions | Family IC −0.0289, NW t −6.09, p 0.0000 | STAT-EDGE / COST-KILLED | `strategies/ISD_BATTERY_TRAIN_REPORT.md`; `ISD_PROGRAM_REASSESSMENT.md` §1–§3 |
| Nifty/BankNifty pair | Z-score fade of price ratio (EOD + 27 intraday combos) | Spread mean reversion | Nifty / BankNifty ratio | 1d and 1m | entry_z / exit_z / window grid | EOD 2016–2026; 1m 2023–2026 | varies | Not cointegrated; bootstrap p 0.354; all 27 intraday combos negative | EXPLORATORY (not pre-registered), TESTED-FAIL | `index_research/NIFTY_BANKNIFTY_PAIR_RESEARCH.md` §1.3, §2.3, §3.2 |

**Verdict: VERIFIED RD.** Cross-sectional short-horizon reversal is genuinely tested. Several statistical edges
exist, and PSB C1 and ISD F4 were killed on cost, not statistics. Spread z-score reversion is tested
(exploratory). **A single instrument faded on an oscillator threshold (RSI/Stoch/CCI extremes) is not tested
anywhere.**

### A4. Volatility-stop trend — claimed **RD**

| Evidence | Construct | Mechanism tested | Result | Status | Source |
|---|---|---|---|---|---|
| F1 brackets | ATR-21 SL/TP **exit bracket** on 12-1 momentum entries (TRAIN-selected k_sl 2.5, k_tp 5.0, at grid boundary) | Fixed ATR exit on a cross-sectional momentum book. The verdict review found the bracket was mostly inactive | Screen printed GO; superseded NO-GO | Not a signal test | `sfb_f1/F1_FEASIBILITY_SCREEN_REPORT.md` "Best Bracket Params"; `F1_FEASIBILITY_SCREEN_VERDICT_REVIEW.md` |
| DRA | ATR SL/TP on EMA entries | As A1 | As A1 | LEGACY | DRA dossier §3.3 |

**Verdict: NOT ACTUALLY TESTED.** No ATR-trailing, Supertrend, Chandelier or stop-and-reverse rule was
tested as an entry signal. F1 used fixed ATR brackets as exit tooling only.

### A5. Breakout / range — claimed **AR**

| Evidence | What it is | Status | Source |
|---|---|---|---|
| Trend sleeve | Cross-sectional ranking (A1), not a range breakout | TESTED-FAIL, different mechanism | as A1 |
| A | Opening-window **direction** (sign of return), not a break of an opening-range high/low | HOLDOUT-FAIL (net) | as A1 |
| Stage A Gate 0, F-RANGE breakout (60m) | Required gross S_ann 2.49 vs 2.15 ceiling | **PRICED-INFEASIBLE, zero data read** | `strategies/STAGE_A_GATE0_REPORT.md` §2 table |
| F-RANGE failed breakout | PLAUSIBLE, scoped to the first map (D-A7) | **CATALOGUED, never measured** | `STAGE_A_DISCOVERY_LAB_DESIGN.md` D-A7; `STAGE_A_GATE0_REPORT.md` |
| F1 / PSB-2 C4 | 12-1 cross-sectional momentum, monthly, dev 2012–2022, 131 formations, IC +0.0466, power 0.411 | TESTED (IC positive, power fail); different mechanism | `psb/PSB2_C4_REPORT.md` §6–§8 |

**Verdict: NOT VERIFIED AS AR → partial RD via A only.** Donchian, 52-week-high and range-breakout rules
were never tested. Opening-range *breakout* was never tested; A tested opening-window direction. The
intraday breakout cell was only priced, not measured.

### A6. Pattern / price-action — claimed **RD**

| Evidence | Construct | Mechanism tested | Universe | Period | n | Result | Status | Source |
|---|---|---|---|---|---|---|---|---|
| PTMS Gann Stage-1 | GF-1 (calendar-day counts from running extremes → change-in-trend within 5 sessions); GF-4T/R8 (printed time windows from last K3 swing); GF-10 (time overbalance of a decline → break of last K3 swing low within 5 sessions) | Swing-pivot **time** geometry predicting a swing break | N100 PIT, daily | Screen 2011-03-25 → 2022-12-30 | 609 / 606 / 320 dates | p_sur 0.953 / 0.980 / 0.214 at α 0.05/3 | TESTED-FAIL; explicitly **NON-CONFIRMATORY**, "never 'Gann's rule is false'" | `ptms/PTMS_GANN_STAGE1_SCREEN_REPORT.md` §4; freeze doc R-2, R-5, R-9 |
| MRLC | Sweep/reclaim conjunction | Analysis only. "Every price in the case study is invented" | — | — | — | Not testable as specified | CATALOGUED / analysis | `strategies/MRLC_CONSTRUCT_ASSESSMENT.md` status line, §5.5 |
| Gann GO-1 retracement | Range-division retracement | — | — | — | — | Status S (secondary) | CATALOGUED-ONLY | `ptms/PTMS_GANN_CONSTRUCT_CATALOGUE_2026-09-14.md` status table |

**Verdict: VERIFIED RD (narrow).** Only swing-pivot time constructs were tested, as a non-confirmatory
screen. Candlestick patterns, Fibonacci/harmonic retracement, ABCD, 123-reversal and ZigZag structures are
**not tested**.

### A7. Volume / flow — claimed **RD**

| Evidence | Construct | Mechanism tested | Universe | Timeframe | Period | n | Result | Status | Source |
|---|---|---|---|---|---|---|---|---|---|
| PSB-1 C3 | Delivery-% z-score | Abnormal delivery share → return | NIFTY-200 | Weekly | Dev (delivery from 2020) | 143 | IC +0.025, t 2.93 | STAT-EDGE (in-sample) / COST-KILLED | `psb/PSB1_C3_REPORT.md` |
| PSB-2 C2 | Fortnightly delivery-% vs 252d baseline, banded | As above | NIFTY-200 | Fortnightly | Dev 2020-09-04 → 2022-12-31 | 55 | IC +0.0349, net +4.57%, power 0.92; **retired** in Phase 0.5 (no variant reached power 0.80 on 2011–2018 TRAIN) | TESTED → RETIRED | `psb/PSB2_C2_REPORT.md`; `C2_PHASE0_5_MINIBATTERY.md` |
| Flow | Futures-OI positioning crowding | — | SSF | Monthly | — | — | Max power 0.6053 | RFA-ABANDON, no data read | `rfa_gate/FLOW_RFA.md` |
| Gate 0 | VWAP / volume-intensity families | — | Index | — | — | — | Excluded (index volume = 0) | NOT RESEARCHED | `STAGE_A_DISCOVERY_LAB_DESIGN.md` line ~672 |

**Verdict: VERIFIED RD (narrow).** Only the delivery-composition construct is tested. OBV, MFI, VWAP
cross/anchor, volume delta/CVD, FVE and volume-confirmation rules are **not tested**. OI-flow was only
gated at RFA.

### A8. Hedge / arbitrage — claimed **RD**

| Evidence | What was tested | Status | Source |
|---|---|---|---|
| Carry / TS Basis | Basis used as a **cross-sectional predictor** of spot returns (monthly) | TESTED-PASS (Carry SEALED), de-authorised (TS Basis) | CLAUDE.md CARRY section; `FUNNEL_CARRY_CONDITIONING_AUDIT_2026-09-24.md` ("Carry's return is spot, not futures") |
| Nifty/BankNifty pair | Stat-arb on two **different** assets | EXPLORATORY, TESTED-FAIL | as A3 |

**Verdict: NOT ACTUALLY TESTED** for the Vault's mechanism: same-asset spread capture across venues or
products (long spot / short perp, convergence plus inventory rebalance). Related stat-arb only.

### A9. ADX / DMI — claimed **RD**

| Evidence | What it is | Status | Source |
|---|---|---|---|
| DRA rule-based `RegimeDetector` (EMA/ADX/ATR) | Existed as code; only a CDSL paper backfill (19 signals, 11 trades), provenance undocumented | LEGACY, no test result | DRA dossier §1 table, §8.5 |
| DRA HMM | Gated on VIX / ratio / slope / RV features, **not ADX** | LEGACY | DRA dossier §3, §8.1 |
| Gate 0 F-VOL | Vol-state conditional family | PRICED-INFEASIBLE, zero data read | `STAGE_A_GATE0_REPORT.md` §2 |

**Verdict: NOT ACTUALLY TESTED** (ADX trend-strength gating). Regime gating in general: INSUFFICIENT
EVIDENCE (legacy, second-hand).

### A10. Carry / funding / basis — claimed **AR**
Carry is fully gated (TRAIN burned for sign, HOLDOUT IC +0.046 t 2.60, SEALED PASS). That mechanism is the
basis level/residual as a **cross-sectional return predictor**. The Vault files are funding-rate monitors
and one-shot spread executors: carry *capture* by holding the hedged pair.
**Verdict: VERIFIED RD, not AR.** The basis-as-signal is genuinely tested. Funding/basis capture as a
hedged position is not.

### A11. Options-vol selling — claimed **AR**

| Evidence | Construct | Mechanism tested | Universe | Hold | Period | n | Result | Status | Source |
|---|---|---|---|---|---|---|---|---|---|
| Seller-edge study | Sell ATM straddle ~10 sessions before monthly expiry; buy back the session before expiry | Unconditional late-cycle premium (VRP) harvest | ~150–190 liquid F&O stocks | ~9 sessions | Discovery 2016–22; confirmation 2023-01 → 2026-08, same code | 43 confirmation expiries | Confirmation gross +10.6%/cycle t 3.78; P5 (VRP-conditional IC) **FAIL**, t 1.24 | EXPLORATORY, not pre-registered; replicated | `strategies/OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` §5.1, §5.2, §9.1 |
| STOCK-STRADDLE-M10 | Frozen forward pre-registration of the above | — | — | — | Forward from 2026-10-12 | 0 | No result yet | PRE-REGISTERED, untested | `STOCK_STRADDLE_M10_PRE_REGISTRATION.md` |
| MSRP D1 | Vol-forecast-gated (E[RV]/VIX quantile) ATM Nifty straddle, long/short | Forecast-conditional straddle timing | Nifty index | Open → close, 1 day | 2023-01-02 → 2025-12-31 (in-sample) | 695 days | Transmission ρ 0.093; signal vs return ρ −0.027; unconditional short gross positive | TESTED-FAIL (in-sample) | `strategies/MSRP_PHASE7_FEE_TRIAGE.md` arms table, rank correlations |
| OSC | IV-surface richness cross-section | Relative-value within the surface | Nifty options | Daily | Probe on burned 2023–25 | 1,701 unread | Within-moneyness IC +0.0167 | RFA-ABANDON (demonstrability) | `OSC_RFA_ABANDON.md` |

**Verdict: VERIFIED RD, not AR.** Premium harvesting is genuinely tested: exploratory, replicated on an
unread window. Conditional timing was tested twice (VRP tilt, vol forecast) and failed. The Vault's
mechanism, **technical-indicator (RSI/BB/EMA) timing of short-option entries**, is **not tested**.

### A12. Items the gap map labelled "Repackaged" (implicit coverage claims)

| Vault item | Anything in the record testing it? | Verdict |
|---|---|---|
| Combo multi-indicator | Nothing tests any AND-confluence | NOT ACTUALLY TESTED (a conceptual reduction, not a test) |
| Band / channel (Bollinger, Keltner) | Only the pair-ratio z-score (A3, exploratory, spread) | NOT ACTUALLY TESTED on a single instrument |
| Grid / martingale / DCA | Nothing | NOT ACTUALLY TESTED; never researched |
| Ichimoku | Nothing | NOT ACTUALLY TESTED |
| Parabolic SAR | Nothing | NOT ACTUALLY TESTED |
| Z-score switching (single name) | Pair ratio only | NOT ACTUALLY TESTED as specified |
| Quadratic / regression bands | Nothing | NOT ACTUALLY TESTED |
| FVE | Nothing | NOT ACTUALLY TESTED |
| σ-scaled ("Black-Scholes") breakout | Nothing; Trend is vol-scaled but not a breakout | NOT ACTUALLY TESTED |
| Nifty ORB template | A (opening-window direction, not a range break) | RD, partial |
| Nifty Supertrend template | Nothing | NOT ACTUALLY TESTED |

---

## B. Corrections to the Vault Gap Map (`2230023`)

| # | Gap-map claim | Correction | Severity |
|---|---|---|---|
| 1 | MA trend-transition **AR** | → **RD (partial)**. No MA rule tested; the only MA-alignment test is LEGACY/unverifiable | Overstated |
| 2 | MACD/momentum **AR** | → **NOT ACTUALLY TESTED** | Unsupported |
| 3 | Breakout/range **AR** ("ORB answered by A"; "intraday breakout cost-dead") | → **RD via A only**. A tested opening-window direction, not a breakout. Intraday breakout was *priced*, never measured. Donchian/52-wk never tested | Overstated |
| 4 | Volatility-stop trend **RD** | → **NOT ACTUALLY TESTED** as a signal. F1 used fixed exit brackets | Overstated |
| 5 | Carry/funding/basis **AR** | → **RD**. Basis-as-predictor tested; carry capture not | Overstated |
| 6 | Options-vol selling **AR** | → **RD**. VRP harvest tested (exploratory); indicator-timed selling not | Overstated |
| 7 | Hedge/arbitrage **RD** | → **NOT ACTUALLY TESTED** (same-asset spread capture). Only different-asset stat-arb tested | Overstated |
| 8 | ADX/DMI **RD** | → **NOT ACTUALLY TESTED**; regime gating = INSUFFICIENT EVIDENCE (legacy) | Unsupported |
| 9 | Pattern/price-action **RD** | Holds, but **narrow**: swing-time constructs only, non-confirmatory. Candles, Fib and harmonics untested | Partially supported |
| 10 | Volume/flow **RD** | Holds, but **narrow**: delivery-% only. OBV/MFI/VWAP/CVD untested | Partially supported |
| 11 | Oscillator reversion **RD** | **Supported** (cross-sectional + spread). Single-instrument threshold fade untested | Supported |
| 12 | "Repackaged" rows (combo, band, grid, Ichimoku, SAR, z-score, regression bands, FVE, σ-breakout) | Economic reductions are **arguments, not tests**. Each is NOT ACTUALLY TESTED | Unsupported as coverage |
| 13 | Wording: "cost-dead", "answered", "retired" | Gate 0 verdicts are zero-data pricing. A's HOLDOUT fail was a **net-of-cost** gate with positive gross (+3.13 bp) and no reported gross test. Gann is a non-confirmatory screen | Mis-stated status |
| 14 | "No family is genuinely new at the family level" | **Withdrawn.** It rested on the overstated rows above | Conclusion unsupported |

---

## C. True research coverage (conservative)

**Genuinely tested (a documented experiment on this mechanism):**
- Cross-sectional short-horizon reversal: PSB-1 C1/C2 (in-sample stat edge), CB-N50 (TRAIN + HOLDOUT IC pass), ISD F4 (TRAIN stat edge)
- Index intraday opening-window continuation (A: TRAIN pass, HOLDOUT fail on a net gate)
- Cross-sectional TSMOM ranking (Trend: TRAIN fail) and 12-1 cross-sectional momentum (PSB-2 C4 / F1)
- Basis as a cross-sectional predictor (Carry: HOLDOUT + SEALED pass)
- Delivery-% volume composition (PSB C3 / C2: stat edge, retired on power)
- Late-cycle stock straddle premium harvest (exploratory, replicated)
- Vol-forecast-gated index straddle timing (in-sample fail)
- Spread z-score mean reversion, Nifty/BankNifty (exploratory, fail)
- Swing-pivot time geometry (Gann: non-confirmatory screen, retired)

**Partially / relatedly tested (the mechanism is adjacent; the Vault form is not tested):**
MA trend-transition, breakout (via A), oscillator reversion on a single instrument, pattern/price-action,
volume/flow, carry/funding capture, options-vol selling with indicator timing.

**Never actually tested:**
MACD triggers, volatility-stop/Supertrend/SAR signals, Donchian/52-week/range breakout, Bollinger/Keltner
band rules, Ichimoku, grid/martingale/DCA, confluence (combo) rules, candlestick, Fib and harmonic
patterns, OBV/MFI/VWAP/CVD/FVE, same-asset venue/product spread capture, ADX gating, calendar/seasonal,
regression bands, σ-scaled breakout.

**Only priced infeasible (zero data read):** intraday index breakout (60m), time-of-day standalone,
vol-state conditional, dense N/BN divergence (all Gate 0); OI flow and RS-MOM (RFA-ABANDON).

**Merely catalogued:** F-RANGE failed breakout (scoped, unmeasured); MRLC (analysis only); Gann GO-1
retracement, GT-4 seasonal dates and other secondary/descriptive Gann constructs.

**Insufficient evidence (legacy, second-hand):** DRA HMM-gated EMA strategy and rule-based ADX regime
detector (primary report not in repo).

---

## D. Revised mechanism gap map

| Vault family | Revised status |
|---|---|
| Oscillator reversion | RD: cross-sectional and spread forms tested; single-instrument threshold fade **open** |
| MA trend-transition | RD (partial): **open** as a rule |
| MACD / momentum | **Open** |
| Volatility-stop trend (+ SAR, Supertrend) | **Open** |
| Breakout / range | RD via A only; range/Donchian/ORB-break **open**; intraday form priced only |
| Band / channel | **Open** (single instrument) |
| Pattern / price-action | RD (swing-time only); candles/Fib/harmonics **open** |
| Grid / martingale / DCA | **Open**, never researched |
| Volume / flow | RD (delivery-%); OBV/MFI/VWAP/CVD **open** |
| Hedge / arbitrage (same-asset) | **Open** |
| Ichimoku | **Open** |
| ADX / DMI | **Open**; regime gating insufficient evidence |
| Seasonal / calendar | **Open**, never researched |
| Carry / funding / basis | RD: signal tested; capture **open** |
| Options-vol selling | RD: harvest tested; indicator timing **open** |
| Combo | Open by construction: no confluence rule tested |
| UNCLEAR (389 files) | Unclassified |

**Answer to the audit question.** Of the mechanisms represented by the 5,807 Vault strategies, we have
genuinely tested only these four:
- cross-sectional reversal
- cross-sectional / ranked momentum
- basis-as-predictor
- short-premium harvesting

We have also run narrow tests adjacent to five more:
- intraday opening-window direction
- swing-time geometry
- delivery-volume composition
- spread z-score reversion
- vol-forecast straddle timing

**The Vault's dominant form is single-instrument technical timing rules:** MA/MACD crossovers,
oscillator-threshold fades, band rules, volatility-stop trend, range breakouts, patterns, volume
indicators, and their confluences. We have assumed that form was covered, but it was never tested
here. The earlier gap map conflated "same broad economic family" with "tested".
