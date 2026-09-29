# Research Mechanism Coverage — Closure Audit

**Date:** 2026-09-29
**Audits:** `RESEARCH_MECHANISM_COVERAGE_MAP_v1_2026-09-28.md` (**v1**). Only its C and D rows, plus the §9 uncertainty register.
**Question:** does internal research outside the SPEC audit chain already test any mechanism v1 calls C (adjacent) or D (untested)?

**Method:**
- Read existing internal reports and, where a report's claim depended on it, the generating script.
- No market data read, no backtest, no re-run, no parameter touched, no holdout or sealed data consumed, no external source.
- Contradictions and defects are **carried, not repaired**.
- Every document cited below was opened in this pass.

**Closure statuses (per task):**
- **A**: covered.
- **B**: covered with a documented defect or specification gap.
- **C**: still adjacent, not covered.
- **D**: still untested.
- **E**: insufficient evidence.

A failed experiment still counts as coverage. Discussion, proposals, catalogues, pricing, RFA-only work and live paper operation do not.

---

## 1. Executive conclusion

**Yes, v1's C/D classifications materially change.** Four of v1's statuses were wrong, and in every case v1 overstated novelty:

| Mechanism | v1 | Closure | Why |
|---|---|---|---|
| **M3b** failed-breakout / liquidity sweep | D | **B** | MRLC was **backtested**, not "analysis only": 2023–26 1m store, a 2012–22 daily extension over 2,300 PIT symbols, and a 2015–22 Nifty-100 1m archive read |
| **M2c** single-instrument multi-day trend | C | **B** | The RELIANCE daily study ran TSMOM 63/126/252 and SMA 50/100/200 long/flat rules, causal, net of fees, over three panels 2010–2026 |
| **M3a** range-breakout continuation | C | **B** | Same study: Donchian 63/252 level-crossing breakouts |
| **M9c** serial-dependence regime | D | **C** | A pre-registered variance-ratio test (W2) checked whether a regime label forecasts afternoon serial dependence (null). A DayType label-persistence diagnostic was INCONCLUSIVE |

**Two v1 statements are now false and are retracted:**
- v1 §1 (and §5 row 1) say no single-instrument multi-day trend rule was ever run. RELIANCE ran several.
- v1 §4 row M3b says F-RANGE/MRLC were "catalogue and analysis only". MRLC was run on data on 2026-08-30/31.

**Why v1 missed them.** v1's inputs (SPEC, COV) cite `MRLC_CONSTRUCT_ASSESSMENT.md` (2026-08-29). That assessment is analysis-only and predates the test reports. The RELIANCE study, W2, Analog Path and the MRLC test were never in the SPEC chain.

**No v1 A or B status is weakened.** M9a stays B with more evidence. All other C/D rows keep their status, but several gain named adjacent evidence that narrows what "untested" may be claimed to mean (§4).

**One code-level defect found, not repaired.** The RELIANCE report's headline "daily return continuation is real" rests on an IC that correlates each signal with the **same day's** return, not the next day's (§3, note R1). Its causal P&L results are unaffected. Its IC-based direction claims are not established by the code as written.

---

## 2. Research programs examined

### 2.1 The 13 programs named in v1 §9

| Program | Examined (documents opened) | Relevant C/D evidence? | Mechanisms potentially affected |
|---|---|---|---|
| **C5 low-vol** | `psb/PSB1_C5_REPORT.md` | No. Cross-sectional: s = −σ(252d), monthly, banded | None (cross-sectional low-vol; absent from v1 §2, see §2.3) |
| **IVOL** | `sleeves/IVOL_PHASE0_PRE_REGISTRATION.md` §1 | No. Cross-sectional idiosyncratic-vol rank on SSF | None |
| **TS Basis / TS Basis Daily** | `ts_basis/TS_BASIS_PHASE0_PRE_REGISTRATION.md` §2–3; `TS_BASIS_DAILY_COMBO_SPEC.md` §1; `TS_BASIS_DAILY_ML_FILTER_REPORT.md`; `BASIS_FAMILY_POST_MORTEM_2026-09-24.md` | Adjacent only | M7b (see §4) |
| **Skew** | `sleeves/SKEW_PHASE0_PRE_REGISTRATION.md` §1–3 | No. Cross-sectional 25Δ risk-reversal rank | None |
| **LAG** | `sleeves/LAG_TRAIN_REPORT.md` | No. Cross-sectional sector lead-lag diffusion, TRAIN FAIL (IC −0.0307, t −1.43) | None (cross-sectional; absent from v1 §2) |
| **GEX / Options-Wall / HedgeWall** | `HEDGEWALL_BRIEF_2026-09-23.md`; `GEX_REGIME_STAGE_A_{TRAIN,HOLDOUT}.md`; `GEX_FLY_B1_DEV.md`; `OPTIONS_WALL_FEASIBILITY_REPORT.md`; `OPTIONS_WALL_EVIDENCE.md`; `OPTIONS_WALL_OVERLAY_STUDY_2026-09-07.md`; `OPTIONS_WALL_COUNTERFACTUAL_BATTERY.md`; `DW1_DEALER_WALL_PRE_REGISTRATION.md` | Adjacent only | M4a, M8c, M10b, M11b (see §4) |
| **NiftyShield** | `NIFTY_SHIELD_ADOPTION_ASSESSMENT.md` §0–3; `NIFTY_SHIELD_REGIME_AND_STRUCTURE_AUDIT.md` §0–2; `NIFTY_SHIELD_REGIME_HORIZON_DIAGNOSTIC.md`; `NIFTY_SHIELD_AFTERNOON_VARIANCE{_PREREG,}_2026-09-27.md` (W2) | **Yes** (W2) | M9c (changed), M9a, M8c, M11b |
| **DayType** | `DAYTYPE_HORIZON_DISCLOSURE.md`; `DAYTYPE_HORIZON_CEILING.md`; `DAYTYPE_LABEL_REPRODUCIBILITY.md`; `REGIME_DETECTION_SPEC_AUDIT_2026-09-09.md` §0–1; `REGIME_TRANSITION_DIAGNOSTIC.md` | **Yes** | M9c (changed), M9a |
| **JEV-NMS-1** | `jev/JEV_NMS_1_PROTOCOL.md` §1–4, §8, §15–16; `jev/JEV_NMS_1_DEVELOPMENT_REPORT.md` §4–6 | Adjacent only | M9c, M11b |
| **N200 HMM** | `N200_REGIME_CLOSURE.md` | Adjacent only | M4a, M9a |
| **PSB-1 C4** | `psb/PSB1_C4_REPORT.md` | No. Cross-sectional: C1 reversal × delivery percentile | None |
| **PSB-2 C3** | `psb/PSB2_C3_REPORT.md` header; CLAUDE.md PSB-2 section | No. Cross-sectional delivery-conditioned reversal | None |
| **OSC probe** | CLAUDE.md OSC section (`OSC_RFA_ABANDON.md` not opened) | No. Cross-section of option strike-expiry cells | None |

### 2.2 Programs found by this pass that were in **neither** v1 §9 nor the SPEC chain

The named list in v1 §9 was itself incomplete. That is a finding in its own right (§6).

| Program | Document(s) opened | Relevant C/D evidence? | Mechanisms affected |
|---|---|---|---|
| **MRLC test** | `strategies/MRLC_TEST_2026-08-30.md`, `strategies/MRLC_ARCHIVE_TEST_2026-08-31.md`, `strategies/MRLC_CONSTRUCT_ASSESSMENT.md` (header, §5.5); scripts present at `scripts/mrlc_test/` | **Yes** | M3b (changed), M1c, M5b |
| **RELIANCE daily regime** | `index_research/RELIANCE_REGIME_RESEARCH_REPORT.md`; `scripts/reliance_regime/signals.py`, `evaluate.py`, `data.py:66` | **Yes** | M2c, M3a (changed); M1c, M9a, M5c |
| **Intraday Analog Path** | `index_research/INTRADAY_ANALOG_PATH_{PROTOCOL,TRAIN_REPORT,HOLDOUT_REPORT}.md` | Reinforces A-status M2d; no C/D change | M3b (no), M2d |
| **W2 afternoon variance** | as in the NiftyShield row | **Yes** | M9c |
| **Options-Wall counterfactual battery** | `OPTIONS_WALL_COUNTERFACTUAL_BATTERY.md` | Descriptive, 9 sessions | M11b, M8c (no change) |
| **Basis-family post-mortem** | `BASIS_FAMILY_POST_MORTEM_2026-09-24.md` | Adjacent | M7b |
| **Structural alpha dossier** | `STRUCTURAL_ALPHA_DOSSIER.md` §B | Confirms "untested" | M11a |
| N50-LS | `N50-LS_RFA.md`, `N50_LS_PRE_REGISTRATION.md` (headers) | No. RFA ABANDON, no data read | None |
| MSI | `strategies/MSI_GROUNDING_BRIEF.md` | No. Architecture documents | None |
| Options strategy survey | `strategies/OPTIONS_STRATEGY_RESEARCH.md` (header) | No. Survey, no candidate authorized | None |
| Options direction read | `options_monitor/OPTIONS_DIRECTION_READ_2026-09-24.md` (header) | No. One-session descriptive read | None |
| PTMS Family G | `ptms/PTMS_FAMILY_G_P3_HYPOTHESIS_DEFINITION.md` (header) | No. CANDIDATE, NOT FROZEN | None |
| Trade Intelligence M0.5 / M2 | `strategies/TRADE_INTELLIGENCE_{M0_5,M2}_ANALYTICS.md` (headers) | **E**: the reports do not name the trade book they analyse | Undetermined |

### 2.3 Tested mechanisms outside v1's taxonomy (omissions from v1 §2; no C/D effect)

These were tested but appear nowhere in v1 §2. None is a C/D mechanism, and no new rows are added here:
- **Cross-sectional low-volatility** (PSB-1 C5)
- **Cross-sectional idiosyncratic volatility** (IVOL: TRAIN/HOLDOUT PASS, SEALED FAIL per CLAUDE.md)
- **Cross-sectional option skew** (Skew: TRAIN FAIL)
- **Cross-sectional sector lead-lag** (LAG: TRAIN FAIL)
- **Basis-level own-history z, ranked** (TS Basis, a M7a variant)
- **Dealer gamma exposure → next-day realised/implied vol** (GEX Stage A: TRAIN t −3.20, HOLDOUT t −2.65, PASS). The GEX-gated fly failed B1 at net Sharpe −0.75.
- **Intraday path shape beyond endpoint return** (Analog Path: HOLDOUT NO). Its return-only baseline, open→12:30 predicting post-12:30, is further M2d-type evidence.
- **Intraday session-archetype nowcast as a directional prior** (DayType; see M9a in §3)
- **Per-stock volatility-regime forecastability** (N200 HMM: Variants A and B FAIL)

---

## 3. Classification changes

Only mechanisms where this pass found meaningful evidence are listed.

| Mechanism | v1 | Closure | Changed? | Evidence | Reason |
|---|---|---|---|---|---|
| **M3b** Failed breakout / liquidity sweep | D | **B** | **Yes** | See **M3b detail** below | Breach-and-reclaim of a recent low is the entry trigger: the mechanism itself, run on data with a result. **Why this conjunction counts as M3b coverage but not M1c or M5b coverage:** the construct's own design document names the sweep as the edge ("That premise is the entire edge", `MRLC_CONSTRUCT_ASSESSMENT.md` §1.1). Its §1.2 table calls the 25-day SMA divergence a *positioning filter*. **B, not A:** (1) the sweep is never isolated from the stretch and volume conditions; (2) selection over 24 cells, with the extension and archive reads described by the reports themselves as "consistency checks, not fresh pre-registered holdouts"; (3) ideal fills; survivorship in the 2023–26 and archive universes; (4) the R unit is not defined in the test report; (5) FVG and candlestick sub-variants (v1 folds) remain untested; (6) the 2023–26 cells sit in the repo's sealed-era calendar |
| **M2c** Single-instrument multi-day trend | C | **B** | **Yes** | See **M2c/M3a detail** below | The mechanism (one instrument's absolute trend, multi-day) was run with causal P&L. **B, not A:** a single large-cap name; long/flat only; binary rules; the study's IC and direction claims are defective (R1); no index or futures form; the RECENT panel is sealed-era data |
| **M3a** Range-breakout continuation | C | **B** | **Yes** | Same study: `donchian_{63,252}` = long iff close > prior N-day high excluding today. DEV `donchian_252` net +0.8%, in market 2%; VAL `donchian_63` +4.2%; RECENT `donchian_252` −3.2%. Report §4D: "Breakouts are lottery tickets" | A level-crossing rule was tested with causal P&L. **B:** same limits as M2c. In market only 1–4% of days, so the evidence is thin by construction. No intraday or opening-range form |
| **M9c** Serial-dependence regime | D | **C** | **Yes** | **W2** (`NIFTY_SHIELD_AFTERNOON_VARIANCE{_PREREG,}_2026-09-27.md`): pre-registered 2026-09-27. Nifty 50 1m, 2023-01-02 → 2026-09-25, 899 sessions. VR = Σ(ln S_end/S_13)² / ΣΣD² on 5-min returns; moving-block bootstrap (block 20, 10,000 reps). Pooled pre-CAS VR 1.046 [0.917, 1.204] = no afternoon autocorrelation. VR by 13:00 DayType label, 2024+: Bull 0.964, Bear 0.842, Choppy 1.242, CIs overlapping. Pinned conclusion: "no detectable path difference by label". **Transition diagnostic** (`REGIME_TRANSITION_DIAGNOSTIC.md`): day-type persistence 2012–2025, Cramér's V 0.0698, max diagonal excess +0.014, INCONCLUSIVE. **JEV** B1 persistence baseline, 15-min state classes | These test whether a regime **label** predicts serial dependence (null), and whether session archetypes persist (inconclusive). They do **not** test the v1 hypothesis: a dependence estimator (Hurst or VR from past data) used as the regime signal, choosing between trend and reversion rules, in multi-day form. So v1's "no dependence-structure regime test" is too strong, but the mechanism is not covered. Caveats carried: the transition labels come from a KMeans fit over all of 2012–2025 (that report's own caveat); the DayType training span is stated as 2023–24 in the horizon diagnostic but "train_thru2023" in W2 (contradiction carried) |
| **M9a** Regime-gated directional trading | B | **B** | No (evidence added) | **RELIANCE:** `vol_calm` (flat above the 70th percentile of 20d RV within a trailing 252d window), `idx_trend` (Nifty > 200d SMA), `combined` = ts_mom_252 ∧ vol_calm ∧ idx_trend. Combined net −1.4 / −1.4 / −4.9% across the three panels. **DayType directional prior** (`NIFTY_SHIELD_REGIME_HORIZON_DIAGNOSTIC.md`; `DAYTYPE_HORIZON_CEILING.md`): 13:00 label, BullTrend minus BearTrend forward return +0.2546 pp, 95% CI [+0.197, +0.312], n 805/801, sessions ≤ 2022. Traded window 13:00→15:15: +0.2305 pp [+0.165, +0.299], class counts 614 bull / 561 bear | Non-legacy tests now exist alongside DRA. **Still B:** RELIANCE is one stock (its gating results are net P&L, unaffected by R1); DRA remains legacy; DayType "out-of-sample" means out of sample **for the classifier only**. The label definition is a KMeans fit over 2012–2025 (`REGIME_TRANSITION_DIAGNOSTIC.md` header). No cost-inclusive gated P&L exists for DayType |

**M3b detail (MRLC).**
- **Rule:** stretch ≥ threshold below the 25-day average; sweep = close below the recent 10-session low on ≥ 2× usual volume, then close back above within 3 bars; skip 3 sessions after a ≥ 8% crash; buy at the next open. Stop = sweep low − 2× ATR (1.5× shown). Exit 50% at the 25-day average, the rest via breakeven then a 2× ATR trail; 20-session time stop. Delivery fees.
- **Dev read, 2023-01 → 2026-08, ~196 names:** 1h ≤15% 40 trades, +0.72 R, t 2.12.
- **2012–22 daily extension, 2,300 PIT symbols:** ≤15% 1,017 trades, +0.24 R, t 8.62. **Archive, Nifty-100 1m, 2015-02 → 2022-12:** 4h ≤10% 109 trades, +0.19 R, t 1.90.

**M2c/M3a detail (RELIANCE).**
- **Scope:** `RELIANCE_REGIME_RESEARCH_REPORT.md` §1–5 and follow-ups; `signals.py`. RELIANCE delivery equity, long/flat, close-to-close, era-accurate delivery fees.
- **Panels:** DEV 2010–19, VAL 2020–22, RECENT 2023–26-09.
- **Rules:** `ts_mom_{63,126,252}` (sign of trailing return, 1-day skip) and `sma_{50,100,200}` (close > SMA).
- **Results:**
  - `sma_200` net +6.0% / +8.1% / +1.7% across the panels.
  - Full-span `sma_200` bootstrap CI of the daily mean [−0.01%, +0.06%] includes zero. Excess over buy-and-hold is −7.7%/yr.

**R1 — RELIANCE IC defect (code read only; not re-run, not repaired).**
- **The code:**
  - `data.py:66` sets `ret = close.pct_change()`, which is the return from t−1 to t, indexed at t.
  - `evaluate.py` computes P&L causally: `pos = sig.shift(1)`.
  - But it computes `ic = np.corrcoef(sig[valid], ret)`, the **unshifted** signal against the same-day return, and the NW t is built from the same pairing.
- **Consequence:** the reported ICs are contemporaneous, not predictive. This does not match the docstring's `corr(signal_t, ret_{t+1})`.
  - That pairing would mechanically produce the reported pattern: `reversal_5` (which includes today's return) IC −0.32, `sma_50` +0.17.
  - So the report's §4A/§5 claim that "daily return continuation is real … twice replicated" **is not established by the code as written**.
- **What stands:** only the net-return and bootstrap figures, which use `pos = sig.shift(1)`.
- **How the map uses it:** no IC figure from this study is used here as evidence of direction.

---

## 4. Confirmed unchanged gaps

Each item below was checked against the programs in §2. The status is unchanged, and the listed evidence is the closest found. "Untested" or "not covered" may now be claimed only in the narrowed sense stated.

| Mechanism | Status | Closest evidence found | Why it does not establish coverage |
|---|---|---|---|
| **M1c** Single-instrument absolute reversion | **C** | RELIANCE `reversal_5`: long iff the 5-day return, including today, is negative. Net +2.3 / −8.6 / −2.2% across the three panels. MRLC's stretch condition (≥ 10–20% below the 25-day average) with reversion to the average as target, **only in conjunction with** a sweep and volume trigger | `reversal_5` is a sign rule, not reversion from an extreme relative to the instrument's own distribution. MRLC tests the conjunction, not unconditional overshoot reversion (v1 treats conjunctions as non-mechanisms). **Narrowing:** "never tested" is false for a sign rule and for the sweep-conditioned form. Borderline, see §5 |
| **M4a** Volatility compression → expansion | **C** | N200 HMM Variant B (vol and vol-ratio features → forward 5-day RV above own trailing 67th percentile; gate FAIL, skill vs persistence −0.1835). GEX Stage A (positioning → next-day RV/IV) | Both forecast volatility level or events. Neither conditions a directional expansion trade on compression. The `ln_rv5`/`ln_rv20` coefficients in the GEX fit are controls, not an M4a test |
| **M5b** Volume-confirmed price moves | **C** | MRLC requires ≥ 2× usual volume on the sweep bar | Volume is one conjunct of the MRLC trigger. No ablation isolating the volume condition was found in the reports |
| **M5c** VWAP anchoring | **D** | RELIANCE follow-up Study 1: `vwap_E1` next-day VWAP entry (+13.4% vs +15.6% close entry). DayType/JEV use TWAP-distance features | Execution-price variant and model features, not a test of VWAP as a pull or support level |
| **M5d** Signed order flow | **D** (data-blocked) | None | — |
| **M6b** Venue / product arbitrage | **D** (data-blocked) | None | — |
| **M7b** Hedged carry capture | **C** | `BASIS_FAMILY_POST_MORTEM_2026-09-24.md` §1.2; `CARRY_FUTURES_TRANSLATION_REVIEW.md` §2–3: convergence −137 / −101 bp/month on the Carry Q5−Q1 book (t −16.7 / −10.6), ≈ the ex-ante basis gap | Convergence is measured as a component of a signal-ranked L/S futures book. Holding a hedged spot/futures pair with its own financing and costs was not tested |
| **M8c** Indicator-timed premium selling | **C** | NiftyShield: DayType + VIX select the structure. It runs under forward PAPER only (MM12.5 routing; RFA "not run"; external backtest "filed, not graded"). Live audit n = 8, descriptive. GEX-gated fly (B1 STOP) | NiftyShield has no completed experiment: a paper book in progress is not a result. The GEX gate uses dealer positioning, not a price-state indicator. The counterfactual battery is 9 sessions and descriptive |
| **M9b** Trend-strength (ADX) gating | **C** | None beyond v1 (only an `adx.py` file in `REPO_AUDIT.md`) | No ADX-conditioned result |
| **M10b** Price-level geometry | **C** | Options-Wall call/put walls, pin, flip (OI/gamma-derived levels). No historical test: DW-1 pre-registration is DRAFT, with ABANDON expected | OI-derived levels are neither ratio/pivot geometry nor tested. Gann tested time only (v1) |
| **M11a** Calendar-timed flow | **D** | `STRUCTURAL_ALPHA_DOSSIER.md` §B lists "Expiry-day bias", "Month-end effect", "RBI policy event" as **Untested**. `day_of_week` appears only as an ML-filter feature (importance 0.0000; the model was discarded) | Confirms v1 |
| **M11b** Intraday time-of-day | **D** | W2 hold-window **variance** share (0.181 vs an assumed 0.40); JEV B0 per-slot **state-class** climatology; counterfactual battery entry-slot cut (9 sessions, short structures, net of fees) | Variance shares and state-class frequencies are not expected return or reversal by time of day. The 9-session slot cut is descriptive and on option structures |

---

## 5. Remaining uncertainty

| Item | Why it is unresolved |
|---|---|
| **M1c: C vs B** | MRLC's stretch-below-average + reversion-to-average is an envelope-style extreme reversion, but it is only ever tested jointly with a sweep. Whether that counts as testing M1c depends on accepting a conjunction as coverage, which v1's rules reject. M3b is treated differently only because the construct's design document names the sweep as the edge and the stretch as a positioning filter (`MRLC_CONSTRUCT_ASSESSMENT.md` §1.1–1.2). Held at C conservatively |
| **DayType session counts** | Same ≤ 2022 window, two figures: the horizon diagnostic's 13:00 rows total ~2,684 sessions (805 bull / 801 bear); the ceiling report gives n = 1,950 (614 / 561). Carried, not reconciled |
| **M3b sub-variants** | Candlestick rejection and FVG revisit (v1 §3.1 fold 4) have no test. B applies to the sweep-and-reclaim form only |
| **RELIANCE IC defect (R1)** | Established by reading code, not by a re-run. If a re-run were ever authorized, the direction claims could move in either direction. This audit does not attempt it |
| **DayType training span** | "2023–24 train" (`diagnose_regime_horizon.py` comment and report) vs "train_thru2023" (W2 prereg §2). Carried. It affects which sessions are in-sample for M9a and M9c evidence |
| **Trade Intelligence M0.5/M2 (E)** | 10–11k trades with rank 1–10, TP/SL and ~2-day holds. The reports opened do not name the source book, so mechanism relevance cannot be determined |
| **Sweep completeness** | This pass:<br>• swept `docs/reports/**` filenames;<br>• ran a keyword grep (calendar, seasonality, Hurst/VR, Donchian/ORB, Fib/pivot, ADX, squeeze, volume shock, order flow, arbitrage, time-of-day);<br>• matched every `scripts/*/` and `scripts/research/*/` directory to an examined report: `se1`, `se3` and `ts_basis_filter` hold only `__pycache__`, and every other directory maps to a program in §2;<br>• checked the research-library plan's outcome table (`docs/superpowers/plans/2026-09-27-research-library-implementation.md` §6). Only W2 (examined) and W6 (straddle CA-filter split, an M8a item already at B) have results.<br>`git branch -a` shows only `main` and `research/straddle-m10-prereg` locally, plus two `fix/*` remotes. Reports that exist only in an operator's local folder, or under non-descriptive names, may still be missing. MRLC and RELIANCE were found by filename and keyword, not by citation, so a similarly named but unlisted study could have been missed |
| **v1 §9 carry-overs** | The 389 unclassified Vault files and OI positioning (Flow, RFA-only) are not affected by this pass |

---

## 6. Final recommendation for map status

- **v1 cannot be frozen as written.** It states two things that are false (§1): a never-tested M2c and an analysis-only MRLC. It also misclassifies M3b (D → B), M2c (C → B), M3a (C → B) and M9c (D → C).
- **v1 does not need another full evidence pass.** The specific corrections are listed in §3. Apply them as **v1.1** and freeze that version. v1.1 should also:
  - update v1 §5 (false-coverage audit) and §6/§8 (the D list loses M3b; the C list loses M2c and M3a and gains M9c);
  - add the §2.3 omissions to v1 §2 as tested cross-sectional or out-of-taxonomy mechanisms, with no new C/D rows;
  - narrow the "eligible only if…" wording to the untested forms:
    - **M1c:** extreme reversion not conditional on a sweep.
    - **M2c:** any form beyond one large-cap, long/flat daily name (index, futures, other names, long/short).
    - **M3a:** the same as M2c, plus intraday and opening-range breakouts.
  - keep the M3b remainder in the v1.1 queue wording so that moving M3b to B does not silently drop it: the sweep without the stretch filter, index forms, FVG and candlestick variants.
- **Items that remain unresolved after v1.1 (§5):**
  - M1c (C/B borderline)
  - the M3b sub-variants
  - the Trade Intelligence book (E)
  - the stated residual risk of the filename and keyword sweep

This document recommends no mechanism for research and ranks nothing.
