# Research Mechanism Coverage & Blind-Spot Map — v1

**Date:** 2026-09-28
**Question:** given everything in the Vault and everything we have actually tested, which economic
mechanisms are covered, which are covered with defects, which are only adjacent, and which are untested?

**Inputs (only):**
- `RESEARCH_STRATEGY_SPECIFICATION_AUDIT_2026-09-28.md` (**SPEC**): authoritative for what was tested and how
- `VAULT_GAP_MAP_COVERAGE_AUDIT_2026-09-28.md` (**COV**)
- `docs/research/Vault_STRATEGY_CENSUS.md` (**CENSUS**) and `Vault_STRATEGY_INVENTORY.csv` (**INV**)
- the internal reports these cite

**Vault counts:**
- "family n" = CENSUS §4 family counts.
- "name hits" = case-insensitive regex over INV `strategy_name`, run 2026-09-28. Name hits are
  **keyword counts, not classifications**: they overlap, and a keyword in a title does not prove the
  mechanism is coded. They show only that the idea exists in the Vault.

**Governance:** inventory only. No strategy is recommended, ranked, scored or predicted. No data read,
no backtest, no parameter touched. Contradictions between documents are carried, not repaired.

**Status definitions (one per mechanism):**
- **A**: a materially equivalent mechanism was tested on real data. A failed test is still A.
- **B**: tested on real data, but a documented specification gap or defect prevents full coverage.
- **C**: related research exists; this mechanism itself was not tested.
- **D**: no materially equivalent experiment identified.

Priced-infeasible, RFA-abandoned and catalogued items are **never** treated as tests.

---

## 1. Executive conclusion

- **How much of the Vault is covered.** Measured by files, very little. About 93% of Vault files
  (CENSUS §6) are **single-instrument time-series timing rules**:
  - trend-following entries
  - oscillator fades
  - band and breakout rules
  - volatility stops
  - their combinations
  
  None of those mechanisms has been tested here in single-instrument, multi-day form. Our tested research is
  overwhelmingly **cross-sectional** (ranking many names on one date). The Vault is almost entirely
  **time-series** (timing one instrument), with only 4 rotation/ranking name hits in 5,807 files.
- **Broad areas genuinely covered (A):**
  - cross-sectional short-horizon reversal (raw and residual)
  - cross-sectional overnight-gap reversal
  - cross-sectional intermediate momentum and vol-scaled TSMOM ranking
  - opening-session continuation (index time-series and equity cross-section)
  - delivery-based informed accumulation
  - Gann time-geometry
  
  The first three and delivery accumulation are cross-sectional. **The Vault barely contains them.**
- **Covered with defects (B):**
  - basis/carry as a predictor
  - short-premium harvesting (unconditional stock and forecast-gated index)
  - relative-value spread reversion (Nifty/BankNifty)
  - regime-gated directional trading (legacy DRA)
  - volatility-scaled exit brackets
- **Adjacent but not covered (C).** These are the Vault's core mechanisms, each close to something we
  tested but not tested itself:
  - single-instrument time-series reversion
  - single-instrument multi-day trend-following
  - range breakout
  - volatility compression → expansion
  - volume-confirmed price moves
  - hedged carry capture
  - indicator-timed premium selling
  - trend-strength gating
  - price-level geometry
- **Genuinely untested (D):**
  - calendar-timed flow
  - intraday time-of-day effects
  - failed-breakout / liquidity-sweep rejection
  - VWAP anchoring
  - signed order-flow imbalance
  - venue-segmentation arbitrage
  - serial-dependence regime switching
- **Not yet to be called gaps:**
  - the 389 unclassified Vault files
  - mechanisms touching internal programs this chain never audited (low-vol C5, IVOL, TS Basis, Skew, LAG, GEX/Options-Wall, NiftyShield, DayType, JEV, N200 HMM)
  - OI-positioning (RFA-abandoned, absent from the Vault)
  
  See §9.

---

## 2. Authoritative tested-mechanism inventory (from SPEC)

| Construct | Economic mechanism | Key evidence | Status | Limitations |
|---|---|---|---|---|
| PSB-1 C1 | Cross-sectional 1-week reversal | NIFTY-200 PIT, weekly, `s = −r(t−5,t)`, dev 2012–22, n 569, IC +0.0232, t 3.76; net −16.8% (SPEC §3.1) | A | Single in-sample dev window; cost-killed |
| PSB-1 C2 | Cross-sectional idiosyncratic (market-residual) 1-week reversal | 52-week beta residual / σ(ε), n 529, IC +0.0352, t 6.63 (SPEC §3.2) | A | Single in-sample window; cost-killed |
| CB-N50 reversal & momentum features | Cross-sectional 1–20-day reversal, next-day horizon | Nifty 50 PIT, daily, open t+1 → open t+2. TRAIN reversal L1 IC +0.0459 (t 8.42); momentum L5/10/20 IC −0.041/−0.028/−0.021 (i.e. reversal); combined HOLDOUT +0.0294, NW t 4.35 (SPEC §3.6) | A | HOLDOUT figure is reversal + basis combined; basis contract UNKNOWN; m = 9 family partly printed |
| CB-N50 basis feature | Cross-sectional basis → next-day stock return | TRAIN IC +0.0557, NW t 12.13 (SPEC §3.6) | B | Basis contract and day-count UNKNOWN |
| ISD F4 | Cross-sectional overnight-gap reversal (gap at 09:15, hold 09:16 → 15:29) | F&O PIT, TRAIN 2023-01 → 2024-11, IC −0.0289, NW t −6.09 (SPEC §3.7) | A | Cost-killed; per-cell ICs only in a secondary memo |
| ISD F1 | Cross-sectional intraday opening-drive continuation | Windows 30/45 min, hold → 15:29; sign wrong (IC −0.0166, t −2.81, secondary) (SPEC §3.7) | A | Failed on sign |
| A | Index time-series intraday opening-window continuation | Nifty 50 1m proxy, sign of bars 0..30/45, exit 15:14 (frozen), TRAIN 2012–18 pass, HOLDOUT 2019–22 net −0.22 bp FAIL (SPEC §3.8) | A | Construct doc grid says 15:29 (stale); gross HOLDOUT significance not reported |
| PSB-2 C4 | Cross-sectional 12-1 momentum, long-only, 6-month staggered | Monthly, dev 2012–22, n 131, IC +0.0466, t 2.55, power 0.41 (SPEC §3.5) | A | Single dev window |
| F1 screen | 12-1 cross-sectional momentum, ≤ 10 names, + ATR(21) bracket | TRAIN 2012–18 n 83, HOLDOUT n 47 (SPEC §3.15) | A (momentum, via C4); B (bracket) | Exploratory screen; grid interior UNKNOWN; report/code conflict |
| Trend | Cross-sectional ranking of vol-scaled multi-horizon (63/126/252) TSMOM, beta/sector neutral | SSF, monthly, TRAIN 2017-02 → 2021-12, n 59, IC +0.0219, t 1.13 FAIL (SPEC §3.9) | A | HOLDOUT never read |
| PSB-1 C3, PSB-2 C2 | Abnormal delivery share → informed accumulation (cross-sectional) | C3 weekly IC +0.0248, t 2.93; C2 fortnightly IC +0.0349, power 0.92 → Phase 0.5 TRAIN 2011–18 power ≤ 0.66 (SPEC §3.3, §3.4) | A | Retired on power |
| Carry v1/v2 | Residual futures basis as a cross-sectional predictor of 1-month **spot** return | SSF, monthly; v1 sign fail; v2 HOLDOUT IC +0.0544 (t 3.31); SEALED +0.0610, net +20.52% (spot) (SPEC §3.10) | B | Dividend sign inverted in code; dividend PIT uncertifiable; gates on EW quintile not the pre-registered z-weighted book; futures spread gross t ≈ −0.8 (secondary) |
| Late-cycle stock straddle | Unconditional short-premium harvest, final ~9 sessions of the monthly cycle | ~160–190 F&O stocks; discovery 2016–22 t 6.05; confirmation 2023–26 t 3.78 (SPEC §3.11) | B | Exploratory; liquidity filter ambiguous; spread-charge method UNKNOWN |
| MSRP D1 | Forecast-gated index straddle (E[RV]/implied quantile gates) + unconditional short/long arms | Nifty weeklies, open → close, 2023–25 in-sample, ρ(signal, return) −0.027 (SPEC §3.12) | B | Strike rule UNKNOWN; in-sample coefficients |
| Nifty/BankNifty z-score | Relative-value spread reversion, EOD and intraday | Johansen not cointegrated; bootstrap p 0.354; 27 intraday combos negative (SPEC §3.13) | B | Z-score formula, hedge ratio, exit semantics UNKNOWN |
| Gann GF-1 / GF-4T/R8 / GF-10 | Time-geometry of swings (calendar counts, printed windows, duration overbalance) → minor trend change within 5 sessions | PIT N100, weekly stock-week, 2011-03 → 2022-12, p_sur 0.953/0.980/0.214 (SPEC §3.14) | A | Non-confirmatory screen |
| DRA HMM-gated EMA | Regime-gated intraday trend entry (P(Expansion) > 0.70 + EMA 9 > 21 on 15m; ATR SL/TP; 5 h time stop) | Nifty 50 cash, walk-forward 2023–26, 200 trades, −₹1,647, no significance test (SPEC §4) | B | LEGACY; primary report absent; ATR period UNKNOWN |

---

## 3. Mechanism taxonomy — Vault family → economic mechanism → variants

| Vault family (family n) | Economic mechanism(s) it expresses | Variants folded in (not separate mechanisms) |
|---|---|---|
| MA trend-transition (1,245), MACD/momentum (235), Ichimoku (36), SAR (5), vol-stop trend (220, as entry) | **M2c** single-instrument time-series trend persistence | MA cross / stack / slope, HMA/VWMA/VIDYA/Kalman smoothers, MACD line/zero cross, Tenkan/Kijun, SAR flips, Supertrend flips; lengths, thresholds, MTF agreement filters |
| Vol-stop trend (as exit), stop/TP machinery (83% of files mention SL) | **M13** volatility-scaled exit / bracket rules | ATR trail, Chandelier, fixed-multiple SL/TP |
| Oscillator reversion (682), Band/channel (148, reversion use), Z-score switching (7 name hits), regression/quadratic bands (44 name hits, regex also catches LSMA) | **M1c** single-instrument short-horizon overshoot reversion | RSI/Stoch/KDJ/CCI/Williams/MFI extremes; BB/Keltner re-entry; z-bands; regression envelopes. Divergence (61 name hits) folded in as a conditioning variant (borderline, §3.1) |
| Grid/martingale/DCA (71) | Grid: **M1c** reversion at grid spacing, with path-dependent inventory. Martingale/DCA: **sizing rule, not a mechanism** | Grid spacing, ladder depth, averaging rules |
| Breakout/range (189), Band/channel (break use), squeeze (15 name hits) | **M3a** range-escape continuation; **M4a** volatility compression → expansion | Donchian, 52-week, box, opening-range break, BB/Keltner squeeze release, σ-scaled ("Black-Scholes") breakout |
| Breakout/range (FVG subset: 24 "gap" name hits, mostly fair-value gap), Pattern/price-action (121; candlestick 189 name hits) | **M3b** rejection of an extreme / liquidity-sweep reversal / liquidity-zone revisit | Failed breakout, sweep-and-reclaim, hammer/engulfing, FVG fills |
| Pattern/price-action (Fib/harmonic 91 name hits, pivots, S/R) | **M10b** price-level geometry (retracement ratios, pivots) | Fib levels, ABCD/harmonic, pivot points, round numbers |
| Pattern/price-action (swing time), census "Hurst" (2) | **M10a** time geometry (covered via Gann); **M9c** serial-dependence regime | Swing-duration counts; Hurst gate |
| Volume/flow (43; "volume/vwap/obv" 198 name hits, mostly as filters) | **M5b** volume-confirmed moves; **M5c** VWAP anchoring; **M5d** signed order-flow imbalance | OBV, MFI, FVE, volume breakouts; VWAP cross/reversion; CVD/volume delta |
| ADX/DMI (19) | **M9b** trend-strength regime gating | ADX thresholds, DMI crosses |
| Seasonal/calendar (10; 26 name hits incl. seasonality filters) | **M11a** calendar-timed flow; **M11b** intraday time-of-day | Day-of-week holds, month-end, sell-in-May, session-clock trades |
| Hedge/arbitrage (42; ~10–15 genuine per CENSUS §10.7) | **M6a** relative-value spread reversion (different assets); **M6b** same-asset venue/product spread capture | Pair z-bands, cross-exchange spot/perp |
| Carry/funding/basis (2 + monitors) | **M7a** basis as predictor; **M7b** hedged carry capture | Funding-rate monitors, spread executors |
| Options-vol selling (2; 22 option name hits) | **M8c** indicator-timed short premium (relative to M8a/M8b) | RSI/BB/EMA-gated ATM selling |
| Combo (2,306) | Not a mechanism: AND-conjunctions of the above (CENSUS §10.5) | — |
| ML/"AI"/Kalman (16 name hits) | Not a mechanism: model classes over the above; CENSUS §10.8 finds static rules under ML labels | — |
| UNCLEAR (389), NON-STRATEGY (44+) | Unclassified / none | — |

Cross-sectional mechanisms present in our research but essentially absent from the Vault (4 rotation
name hits): M1a, M1b, M1d, M2a, M2b, M2e, M5a, M7a. They are listed in §4 for completeness.

### 3.1 Borderline deduplication decisions

1. **Time-series vs cross-sectional reversal kept separate (M1a vs M1c).** Cross-sectional reversal
   ranks relative returns on a date; the market component is ranked away (M1a) or regressed away (M1b).
   Single-instrument reversion bets on the absolute price path, including the market-level component.
   Different information set, different payoff.
2. **Divergence folded into M1c, not separated.** Divergence is "an extreme not confirmed by momentum
   → reversal": a conditioning filter on overshoot reversion. If a future hypothesis is specifically
   *momentum-decay predicts trend end independent of an extreme*, it would need its own row. Flagged
   in §9.
3. **Breakout (M3a) kept separate from trend (M2c).** Both bet on continuation. Breakout conditions on
   a **level event** (price crossing a defined range boundary), under a stop/order-clustering
   rationale. Generic trend rules condition on a smoothed slope. Borderline: a Donchian rule and a
   long-MA rule overlap heavily in practice.
4. **Candlestick and FVG folded into M3b.** A hammer is an intrabar failed breakdown; an FVG fill is a
   revisit of an unfilled imbalance zone. Both are "price rejected at or returning to a liquidity
   location". Kept apart from M10b (fixed geometric ratios, no liquidity rationale).
5. **Grid folded into M1c.** Its return source is reversion at the grid spacing. The inventory ladder
   changes the risk profile, not the economic hypothesis.
6. **Vol-stop as entry (M2c) vs as exit (M13).** A Supertrend flip used as the entry signal is trend
   persistence. The same ATR machinery used only to exit is an exit-rule mechanism.
7. **Opening-range breakout (M3a) vs A's opening-window direction (M2d).** A trades the *sign* of the
   first 30/45 minutes at a fixed time. ORB trades a *level break* at an unknown later time. Adjacent,
   not equivalent.

---

## 4. Coverage map (master table)

| ID | Mechanism family | Economic hypothesis | Vault evidence | Existing research | Status | Exact coverage evidence | Material difference / gap | Data available? | Candidate for new research? |
|---|---|---|---|---|---|---|---|---|---|
| M1a | Short-horizon reversal, cross-sectional | Recent relative losers outperform over 1 day – 1 week (overreaction / liquidity provision) | ~none (4 rotation name hits) | PSB-1 C1; CB-N50 reversal + momentum L5–20 | **A** | SPEC §3.1 (weekly, NIFTY-200, dev 2012–22, t 3.76); SPEC §3.6 (daily, N50, TRAIN t 8.42, HOLDOUT combined t 4.35) | — | Yes | No (covered) |
| M1b | Idiosyncratic (residual) reversal | The market-stripped part of last week's move reverts | none | PSB-1 C2 | **A** | SPEC §3.2 (t 6.63, in-sample dev) | — | Yes | No |
| M1c | Short-horizon overshoot reversion, **single instrument, time-series** | An extreme move in one instrument relative to its own recent distribution reverts in absolute terms | Oscillator 682; band-reversion subset of 148; z-score 7; grid 71; divergence 61 name hits | Closest: M1a/M1b (cross-sectional); pair z-score (spread, B); legacy FTMO null (prior only, not in repo) | **C** | — | Our reversal tests rank names relative to each other or trade a two-asset spread; none bets on one instrument's absolute reversion from its own extremes | Index 1m 2012+, equity 1m 2023+, daily bhavcopy 2010+ | Yes, if the hypothesis is absolute single-instrument reversion |
| M1d | Overnight-gap reversal, cross-sectional | Stocks with large overnight gaps revert intraday relative to peers | ~0 (24 "gap" name hits, mostly FVG; crypto has no session gap) | ISD F4 | **A** | SPEC §3.7 (IC −0.0289, NW t −6.09, TRAIN) | — | Yes | No |
| M2a | Intermediate momentum, cross-sectional | 12-1 month relative winners keep outperforming | 4 rotation name hits | PSB-2 C4; F1 (with bracket) | **A** | SPEC §3.5 (IC +0.0466, t 2.55, power 0.41); SPEC §3.15 | — | Yes | No |
| M2b | Vol-scaled TSMOM, ranked cross-sectionally | Names with stronger own-trend (vol-scaled, 3/6/12 m) outperform peers | none | Trend sleeve | **A** | SPEC §3.9 (IC +0.0219, t 1.13, FAIL) | — | Yes | No |
| M2c | Trend persistence, **single instrument, multi-day, time-series** | An instrument trending (by smoothed slope, crossover or trailing level) keeps moving in the same absolute direction | MA 1,245; MACD 235; vol-stop 220; Ichimoku 36; SAR 5; plus most of Combo 2,306 | Closest: M2b (ranking), A (intraday index, fixed window), DRA (legacy, regime-gated 15m EMA, B) | **C** | — | M2b ranks names; it never trades one instrument's absolute trend. A is a single-session, fixed-time rule. DRA is legacy with no significance test. No multi-day single-instrument trend rule was tested | Index daily 2012+ and 1m 2012+; SSF daily 2016+; equity daily | Yes |
| M2d | Opening-session continuation, index time-series | The first 30/45 minutes' direction persists to the close | 4 opening-range keyword hits across INV name/detail fields (level breaks, not window sign) | A | **A** | SPEC §3.8 (TRAIN pass, HOLDOUT net −0.22 bp FAIL) | Doc caveat: construct grid says 15:29, frozen pre-reg 15:14 (carried) | Yes | No |
| M2e | Opening-drive continuation, cross-sectional equity | Stocks with the strongest first 30/45 min outperform to the close | none | ISD F1 | **A** | SPEC §3.7 (wrong sign; secondary IC −0.0166) | — | Yes | No |
| M3a | Range-escape continuation | Crossing a defined range boundary (N-day high, box, opening range) triggers continuation via clustered orders/stops | Breakout 189; ~1,252 "breakout/channel/donchian" name hits (heavily overlapping) | Closest: M2b, A; Gate 0 F-RANGE breakout (**priced only**) | **C** | — | No level-crossing rule tested; A uses window sign, not a boundary; Gate 0 read no data | Index 1m/1d; equity 1m (2023+) / daily | Yes |
| M3b | Rejection of an extreme / liquidity sweep / liquidity-zone revisit | Price that breaches a visible level and reclaims it (or revisits an unfilled imbalance) reverses, because the breach was stop-liquidity harvesting, not information | Pattern 121; candlestick 189, FVG ~24 name hits | F-RANGE failed breakout (**catalogued**); MRLC (**analysis only**) | **D** | — | Never run on data; catalogue and analysis are not tests (COV §C) | Index 1m (no volume); equity 1m 2023+ | Yes |
| M4a | Volatility compression → expansion | Periods of unusually low realised range are followed by expansion, with direction resolved by the break | Squeeze 15 name hits; BB/Keltner squeeze subset | Closest: MSRP D1 (forecast RV vs implied → straddle P&L, B); Gate 0 F-VOL (**priced only**); DRA HMM vol states (legacy) | **C** | — | MSRP tests implied-vs-forecast mispricing with an options payoff; it does not test compression-conditioned directional expansion in the underlying | Index 1m/1d, VIX 1d 2012+ | Yes |
| M5a | Informed accumulation via delivery share | Abnormally high delivery % signals informed buying | none (NSE-specific field) | PSB-1 C3; PSB-2 C2 (+ Phase 0.5) | **A** | SPEC §3.3, §3.4 | — | Yes (delivery 2020+; backfill used in Phase 0.5) | No |
| M5b | Volume-confirmed price moves | Price moves on abnormal total volume carry information and persist; moves on thin volume revert | OBV/MFI/FVE/volume breakouts (volume family 43; ~198 volume/VWAP/OBV name hits, mostly filters) | Closest: M5a (delivery composition), Flow (OI, **RFA only**) | **C** | — | Delivery % measures position-taking share, not total-volume shocks conditioning price moves | Equity daily volume 2010+; equity 1m 2023+; **index volume = 0** | Yes |
| M5c | VWAP anchoring | Institutional execution benchmarked to VWAP creates predictable pull or support around session VWAP | 49 VWAP-titled files (CENSUS §9.9) | Gate 0 excluded VWAP families (index volume 0); DRA's VWAP filter was bypassed on index | **D** | — | Never tested on any instrument with volume | Equity 1m 2023+ only; not index | Yes (equity only) |
| M5d | Signed order-flow imbalance | Net aggressor volume predicts short-horizon drift or reversal | CVD/volume-delta files (volume family) | None | **D** | — | No test | **Insufficient**: no signed trades; only bar-direction approximations | Data-blocked |
| M6a | Relative-value spread reversion (different assets) | A two-asset price ratio reverts to its mean | Pair / hedge subset (12 pair name hits) | Nifty/BankNifty z-score | **B** | SPEC §3.13 (EOD and intraday, failed; exploratory) | Z-score formula, hedge ratio, exit semantics UNKNOWN; only one pair | Index 1d/1m | Only as a specification-complete re-test of the same mechanism, or other pairs (§9) |
| M6b | Same-asset venue / product spread capture | Segmented liquidity lets one asset trade at different prices across venues; the spread pays the provider of cross-venue inventory | ~10–15 genuine hedge/arb files | None | **D** | — | No test | **Insufficient**: single venue (NSE); no BSE or second-venue store identified | Out of current data scope |
| M7a | Basis as a cross-sectional return predictor | Residual futures basis predicts forward (spot) returns | ~0 (funding monitors only) | Carry v1/v2; CB-N50 basis feature | **B** | SPEC §3.10 (HOLDOUT t 3.31, SEALED t 4.49 on spot); SPEC §3.6 | Dividend sign defect; PIT uncertifiable; portfolio divergence; spot-not-futures | Yes | No new mechanism; open defects are documentation/implementation items |
| M7b | Hedged carry capture | Holding the hedged spot/futures (or perp) pair earns the basis/funding as it converges | Funding monitors, spread executors (~5) | Closest: Carry futures-translation review measured the futures L/S spread of the carry *signal* (secondary) | **C** | — | That review asks whether the signal survives in futures returns; it does not test convergence capture from a hedged position | SSF + equity daily 2016+ | Yes |
| M8a | Unconditional short-premium harvest (stock, late cycle) | Late-cycle single-stock option premium exceeds realised payoff (VRP concentrated in final sessions) | Options 2–22 name hits (index/crypto) | Seller-edge study | **B** | SPEC §3.11 (discovery t 6.05, confirmation t 3.78) | Exploratory; liquidity filter ambiguous; spread charge UNKNOWN; forward M10 pre-registered, not yet run | Stock options 2016+ | Covered as a mechanism; open items are specification |
| M8b | Forecast-gated premium timing (index) | Selling (or buying) premium only when forecast RV is low (or high) vs implied improves returns | Options files (indicator-gated, see M8c) | MSRP D1; straddle study P5 (vrp60 tilt, failed) | **B** | SPEC §3.12; SPEC §3.11 (P5) | Strike rule UNKNOWN; in-sample coefficients | Nifty options to 2026-07 | No new mechanism |
| M8c | Indicator-timed premium selling | Technical price-state signals (RSI/BB/EMA) time short-premium entries | 2 census options files; "ATM-Option-Selling … EMA … RSI" name hit | Closest: M8a, M8b | **C** | — | Our conditioning used vol-forecast and VRP state, never price-state indicators | Stock options 2016+, Nifty options to 2026-07 | Yes (only if the price-state→premium link is the hypothesis) |
| M9a | Regime-gated directional trading | A latent-state model identifies periods when a directional rule works | Regime filters in 68% of files (CENSUS §2) | DRA HMM-gated EMA | **B** | SPEC §4 (200 trades, no significance test) | LEGACY; primary report missing; ATR period UNKNOWN | VIX, index 1d/1m | See §9 |
| M9b | Trend-strength gating | Trend rules work only when directional strength (ADX/DMI) is high | ADX 19 (mostly filters) | Closest: DRA rule-based detector (code only, no result); DRA HMM | **C** | — | No ADX-gated test; HMM gating used VIX/vol/slope features | Index/equity OHLC | Yes, but only as a conditioning layer on an M2c/M3a base (which is itself C) |
| M9c | Serial-dependence regime | Sign of autocorrelation (persistent vs anti-persistent) is forecastable, selecting trend vs reversion | Hurst 2 name hits | Closest: DRA HMM (vol/drift states) | **D** | — | No dependence-structure regime test | Index 1d/1m, equity | Yes |
| M10a | Time geometry of swings | Elapsed-time counts or duration overbalance predict a minor trend change | Pattern subset | Gann GF-1, GF-4T/R8, GF-10 | **A** | SPEC §3.14 (p_sur 0.953/0.980/0.214, non-confirmatory) | — | Yes | No |
| M10b | Price-level geometry | Fixed ratio levels (Fib, harmonic) or pivot levels attract or reject price | Fib/harmonic 91 name hits; pivots | Gann GO-1 retracement (**catalogued**), GO-3 (**descriptive**) | **C** | — | Gann tested time, not price-ratio levels; GO-1 never screened | Daily / 1m OHLC | Yes |
| M11a | Calendar-timed flow | Schedule-driven flows (salary/SIP inflows, month-end rebalancing, weekend risk) shift returns by calendar position | Seasonal 10; ~26 calendar name hits | Gann GT-4 (**descriptive**); no DoW/ToM test in `docs/reports` (grep 2026-09-28) | **D** | — | Never tested | Index 1d 2012+, equity daily 2010+ | Yes |
| M11b | Intraday time-of-day | Expected return or reversal differs by time of session (auction cycle, lunch thinness) | Session-clock files (8 session name hits) | Gate 0 F-TOD (**priced only**); A and ISD are time-anchored but test direction, not time-of-day | **D** | — | Pricing read no data; no time-of-day return test exists | Index 1m 2012+, equity 1m 2023+ | Yes |
| M13 | Volatility-scaled exit / bracket | Vol-normalised stops/targets change the payoff of a given entry | Vol-stop 220; SL mentions 83% | F1 ATR(21) bracket; DRA ATR SL/TP (legacy) | **B** | SPEC §3.15 (bracket selected to near-inactivity); SPEC §4 | Grid interior UNKNOWN; report/code conflict; DRA ATR period UNKNOWN | Daily OHLC; 1m | Exit rules are a payoff modifier, not a return mechanism |

Non-mechanisms (excluded from status): martingale/DCA sizing; Combo conjunctions; ML/Kalman model
classes; MTF agreement filters (conditioning on M2c); non-strategy files.

---

## 5. False coverage audit

Earlier labels (Gap Map `2230023` and parts of COV) that must **not** be read as "already researched":

| Earlier claim | Correct reading | Why |
|---|---|---|
| "MA trend-transition = AR" | M2c is **C** | The Trend sleeve ranks names cross-sectionally (SPEC §3.9); A is a fixed-time intraday rule (SPEC §3.8); DRA is legacy (SPEC §4). No single-instrument multi-day trend rule was ever run |
| "MACD = AR" | Part of M2c, **C** | No EMA-difference or momentum-rate trigger in any tested spec (SPEC §5) |
| "Breakout = AR / cost-dead" | M3a is **C** | Gate 0 priced it with no data read (SPEC §4); A is not a level break |
| "Oscillator reversion covered via cross-sectional reversal" | M1a/M1b are **A**; M1c is **C** | The cross-sectional tests do not cover single-instrument absolute reversion |
| "Volatility stops covered via F1" | M13 is **B** as an exit; as an entry it is part of M2c, **C** | F1's bracket is an exit on a momentum book, selected to near-inactivity (SPEC §3.15) |
| "Grid = repackaged short-vol" / "repackaged reversion" | Grid sits under M1c, **C** | A conceptual reduction is not a test; M1c itself is untested |
| "Pattern/price-action = RD via Gann" | M10a is **A** (time geometry only); M10b is **C**; M3b is **D** | Gann tested time counts, not price levels, candles or sweeps |
| "Volume/flow = RD" | M5a is **A**; M5b is **C**; M5c/M5d are **D** | Only delivery composition was tested |
| "Carry = AR" | M7a is **B**; M7b is **C** | Documented defects; capture never tested |
| "Options selling = AR" | M8a/M8b are **B**; M8c is **C** | Exploratory, specification gaps; indicator timing never tested |
| "ADX = RD" | M9b is **C** | No ADX-conditioned result exists |
| "Hedge/arb = RD" | M6a is **B**; M6b is **D** | The pair study is under-specified; venue arbitrage never tested |
| "Intraday breakout / TOD / vol-state are cost-dead" | Priced infeasible, **not tested** | Gate 0 read no data (SPEC §4) |

---

## 6. Genuine blind spots (D, after deduplication)

| ID | Economic hypothesis | Why it is genuinely new | Existing data required | Store sufficient? | Major specification questions | Why a separate mechanism |
|---|---|---|---|---|---|---|
| M3b | Breach-and-reclaim of a visible level (or revisit of an unfilled imbalance) signals stop-liquidity harvesting and reverses | No test ever run; F-RANGE and MRLC exist only as catalogue/analysis | Intraday OHLC; for a volume-profile version, volume | Index 1m has no volume → volume-free version only; equity 1m 2023+ has volume | How to define "failure" causally (known only after the fact, per Stage-A design); which level (prior-day extreme, session range, swing); reclaim window; horizon | Its information set (a failed level event) differs from both reversion-from-extremes (M1c) and continuation (M3a) |
| M5c | VWAP-benchmarked execution creates a predictable pull or support around session VWAP | No test anywhere; excluded only for lack of index volume | Equity 1m with volume | Equity 1m 2023+ (post-CAS bars need `is_synthetic` filtering); **not index** | Anchor definition (session vs rolling); reversion vs continuation sign; cross-sectional vs single-name | Uses an execution-flow rationale no tested construct uses |
| M5d | Signed aggressor imbalance predicts short-horizon drift or reversal | No test | Signed trades or quotes | **Insufficient** (bar-level only) | Whether bar-direction proxies are an acceptable substitute; the record does not say | Different information (who initiated) from delivery or OI |
| M6b | Same-asset price differences across venues or products converge; the spread pays inventory/transfer risk | No test | Synchronous multi-venue prices | **Insufficient** (NSE only; second-venue store UNKNOWN) | Venue scope; latency assumptions | Location arbitrage, not time (carry) or relative value (pairs) |
| M9c | The autocorrelation sign is persistent enough to choose trend vs reversion rules ex ante | No dependence-structure regime tested; DRA used vol/drift states | Price series | Yes (index/equity) | Estimator and window (Hurst, variance ratio); what the gated base rule is. Its base rules (M1c, M2c) are themselves untested | A regime defined by serial dependence, not volatility |
| M11a | Schedule-driven flows shift returns by calendar position (DoW, turn-of-month, month-of-year) | Never tested; Gann GT-4 is descriptive only | Daily index/equity returns | Yes (index 1d 2012+, equity 2010+) | Which calendar effect; index vs cross-section; NSE holiday handling (`nse_holidays.py`) | Information set is the calendar itself, independent of price history |
| M11b | Intraday expected return or reversal differs by time of session | Gate 0 only priced it | Index/equity 1m | Index 1m 2012+ (vendor/native era label offset, SPEC §3.8); equity 1m 2023+ | Whether it is a standalone mechanism or a conditioning axis (Stage-A design treats it as the latter); CAS-era session change | Time-of-session as the signal, not a fixed anchor for another signal |

---

## 7. "Do not test yet": new at the indicator level, covered economically

| Looks new | Already-covered mechanism | Evidence |
|---|---|---|
| Cross-sectional RSI/Stochastic rank, 1–5-day reversal rotation | M1a | SPEC §3.1, §3.6 |
| Beta- or factor-residual weekly reversal variants | M1b | SPEC §3.2 |
| Momentum rotation (the Vault's 4 rotation files), 6-/12-month rank rotation | M2a | SPEC §3.5 |
| Vol-scaled multi-horizon momentum rank | M2b | SPEC §3.9 |
| First-30/45-minute index direction rules, re-parameterised windows | M2d | SPEC §3.8 (frozen; any change is a new construct but the same mechanism) |
| Equity opening-drive rank variants | M2e | SPEC §3.7 |
| Cross-sectional overnight-gap fade variants | M1d | SPEC §3.7 |
| Delivery-% z variants (other windows/cadences) | M5a | SPEC §3.3–§3.4 |
| Gann time-count variants (other day counts, window widths) | M10a | SPEC §3.14 |
| Basis-rank variants (other annualisation, windows) | M7a (B) | SPEC §3.10 |
| VRP-bucket tilts on stock straddles | M8b | SPEC §3.11 P5 |
| Martingale/DCA sizing overlays; Combo conjunctions; ML-labelled versions of the above | Not mechanisms | CENSUS §10.5, §10.8 |

---

## 8. Research-queue candidate list (unranked, neutral)

**Group D (no materially equivalent experiment):** M3b, M5c, M9c, M11a, M11b; data-blocked: M5d, M6b.

**Group C (untested, adjacent to tested work).** Each is eligible only if the hypothesis is the stated
distinction:

| ID | Eligible only if the hypothesis is… |
|---|---|
| M1c | Absolute single-instrument reversion from its own extremes, not cross-sectional ranking |
| M2c | Multi-day absolute trend persistence in a single instrument, not ranking and not a single intraday window |
| M3a | Continuation triggered by crossing a defined level, as distinct from smoothed-slope trend |
| M4a | Compression-conditioned expansion in the underlying, not implied-vs-forecast vol mispricing |
| M5b | Total-volume shocks conditioning price persistence, not delivery composition |
| M7b | Convergence earned by holding the hedged position, not basis as a ranking signal |
| M8c | Price-state indicators timing premium sales, not vol-forecast or VRP conditioning |
| M9b | Trend-strength conditioning of a base trend rule (requires M2c or M3a to be specified first) |
| M10b | Price-ratio or pivot levels, not time counts |

**Group B (tested; open items are specification or implementation, not new mechanisms):** M6a, M7a,
M8a, M8b, M9a, M13.

---

## 9. Uncertainty register

| Item | Why the classification is uncertain |
|---|---|
| 389 Vault UNCLEAR files | Filename carries no mechanism (CENSUS §10.6); not classified here |
| Internal programs outside this audit chain | C5 low-vol, IVOL, TS Basis / TS Basis Daily, Skew, LAG, GEX regime, Options-Wall/HedgeWall, NiftyShield, DayType, JEV-NMS-1, N200 HMM, PSB-1 C4, PSB-2 C3, OSC probe were **not** re-audited in SPEC. Any Vault mechanism touching volatility level, skew, sector lead-lag, dealer positioning or regime estimation may be more covered (or less) than shown. In particular, M4a (vol regimes) and M9a (regime gating) could be affected by DayType/N200 HMM work not read here |
| M9a (DRA) | Only secondary evidence (dossier); primary report not in repo. Assigned B, but could equally be argued INSUFFICIENT EVIDENCE |
| M6a | The pair study's rule cannot be reconstructed; B asserts that *a* spread-reversion test happened, not *which* |
| M1c vs divergence | Divergence folded into M1c; a momentum-decay-without-extreme hypothesis would need its own row |
| M3a vs M2c | Donchian/long-MA overlap; the boundary between level-break and slope-trend is a judgment call |
| M3b candlestick fold | A single-bar rejection may be argued as its own mechanism; kept inside M3b |
| M11b | Stage-A design treats time-of-day as a conditioning axis rather than a family; standalone status is uncertain |
| OI positioning (Flow) | RFA-abandoned (no data read) and absent from the Vault; not mapped |
| Carry economic identity | Futures-translation review reads Carry as a spot effect with anti-KMPV sign (secondary). M7a's *mechanism label* ("carry") is itself contested |
| Vault name-hit counts | Title regex; overlapping and noisy. Evidence of existence, not of prevalence |
| Straddle study M8a | Exploratory with a replicated confirmation; whether it counts as "covered" beyond B depends on the forward M10 pre-registration, which has no result yet |

---

## Final quality check

1. Every A/B cites SPEC evidence: yes (§2, §4).
2. Failed experiments count as tested: yes (Trend, ISD F1, A, Gann are A).
3. No indicator is treated as a mechanism: yes; indicators appear only as variants (§3).
4. No parameter variation is counted as a new mechanism: yes (§7).
5. No missing parameter inferred: yes; UNKNOWNs carried from SPEC.
6. No catalogued or priced item promoted to tested: yes (F-RANGE, MRLC, Gate 0, GO-1, GT-4).
7. No market data read: yes (INV is the worker's inventory, not market data).
8. No backtest run: yes.
9. No holdout or sealed data consumed: yes.
10. Every D explains why it is uncovered: yes (§6).
11. Uncertain cases registered: yes (§9).
12. Traceable reasoning per mechanism: yes (§4, §5).
