# Research Mechanism Coverage & Blind-Spot Map — v1.1 (FROZEN)

**Date:** 2026-09-29
**Supersedes:** `RESEARCH_MECHANISM_COVERAGE_MAP_v1_2026-09-28.md` (**v1**)
**Question:** given everything in the Vault and everything we have actually tested, which economic
mechanisms are covered, which are covered with defects, which are only adjacent, and which are untested?

**Inputs, in order of authority:**
1. `RESEARCH_STRATEGY_SPECIFICATION_AUDIT_2026-09-28.md` (**SPEC**): authoritative for what was tested and how.
2. **v1**: the base document and its structure.
3. `RESEARCH_MECHANISM_COVERAGE_CLOSURE_AUDIT_2026-09-29.md` (**CLOSE**): authoritative for the corrections found in closure.

Vault counts come from `docs/research/Vault_STRATEGY_CENSUS.md` (**CENSUS**) and
`Vault_STRATEGY_INVENTORY.csv` (**INV**), as in v1.

**What changed from v1.** This is a consolidation pass, not a new audit.
- Four statuses change: **M3b D→B, M2c C→B, M3a C→B, M9c D→C** (CLOSE §3).
- Omitted tested mechanisms are added to §2 (CLOSE §2.3).
- Two false v1 statements are retracted (§1).
- Every other status is carried from v1 unchanged.
- No search was run, no data read, no experiment run, and no holdout or sealed data consumed.
- Contradictions between documents are carried, not repaired.

**Vault counts:**
- "family n" = CENSUS §4 family counts.
- "name hits" = case-insensitive regex over INV `strategy_name`. These are **keyword counts, not
  classifications**: they overlap, and they show only that an idea exists in the Vault.

**Governance:** inventory only. No strategy is recommended, ranked, scored or predicted.

**Status definitions (one per mechanism):**
- **A**: a materially equivalent mechanism was tested on real data. A failed test is still A.
- **B**: tested on real data, but a documented specification gap, defect or scope limit prevents full coverage.
- **C**: related research exists; this mechanism itself was not tested.
- **D**: no materially equivalent experiment identified.
- **E**: the internal record is insufficient to decide.

Priced-infeasible, RFA-abandoned, catalogued items and live paper operation are **never** treated as tests.

---

## 1. Executive conclusion

- **How much of the Vault is covered.** About 93% of Vault files (CENSUS §6) are
  **single-instrument time-series timing rules**: trend entries, oscillator fades, band and breakout
  rules, volatility stops, and combinations of these.
  - Our tested research is still predominantly **cross-sectional**, and the Vault has only 4
    rotation/ranking name hits in 5,807 files.
  - **Correction to v1:** single-instrument time-series rules *have* been tested, though narrowly.
    - **RELIANCE daily study:** trend (TSMOM, SMA) and Donchian breakout rules, long/flat on one large-cap name.
    - **MRLC:** a sweep-and-reclaim construct run across 2023–26 1m, 2012–22 daily (2,300 PIT
      symbols) and a 2015–22 Nifty-100 1m archive.
  - Both are **B**: the tested forms are narrow and carry documented defects.
- **Retracted v1 statements:**
  1. ~~"No single-instrument multi-day trend rule was ever run."~~ The RELIANCE study ran
     `ts_mom_{63,126,252}` and `sma_{50,100,200}` long/flat, with causal P&L, over three panels
     2010–2026 (CLOSE §3).
  2. ~~"F-RANGE/MRLC were catalogue and analysis only."~~ MRLC was backtested on 2026-08-30/31
     (`MRLC_TEST_2026-08-30.md`, `MRLC_ARCHIVE_TEST_2026-08-31.md`). v1 had seen only the earlier
     analysis-only `MRLC_CONSTRUCT_ASSESSMENT.md`. F-RANGE itself remains catalogued only.
- **Covered (A):**
  - cross-sectional short-horizon reversal (raw and residual)
  - cross-sectional overnight-gap reversal
  - cross-sectional intermediate momentum and vol-scaled TSMOM ranking
  - opening-session continuation (index time-series and equity cross-section)
  - delivery-based informed accumulation
  - Gann time geometry
- **Covered with defects or narrow scope (B):**
  - basis/carry as a predictor
  - short-premium harvesting (unconditional stock and forecast-gated index)
  - relative-value spread reversion (Nifty/BankNifty)
  - regime-gated directional trading
  - volatility-scaled exit brackets
  - **new in v1.1:** single-instrument multi-day trend (M2c), range breakout (M3a), liquidity-sweep rejection (M3b)
- **Adjacent but not covered (C):**
  - single-instrument extreme reversion (M1c; C/B borderline)
  - volatility compression → expansion
  - volume-confirmed moves
  - hedged carry capture
  - indicator-timed premium selling
  - trend-strength gating
  - price-level geometry
  - **new in v1.1:** serial-dependence regime (M9c)
- **Genuinely untested (D):**
  - calendar-timed flow
  - intraday time-of-day effects
  - VWAP anchoring
  - signed order-flow imbalance (data-blocked)
  - venue/product arbitrage (data-blocked)
- **Open uncertainties (§9):**
  - M1c (C/B)
  - the untested M3b sub-variants
  - the RELIANCE IC defect R1
  - the DayType contradictions
  - Trade Intelligence (E)
  - the 389 unclassified Vault files
  - the residual risk that an operator-local or poorly named study was not found

---

## 2. Authoritative tested-mechanism inventory

### 2.1 Mapped mechanisms (from SPEC, plus the closure additions)

**Cross-sectional**

| Construct | Economic mechanism | Key evidence | Status | Limitations |
|---|---|---|---|---|
| PSB-1 C1 | Cross-sectional 1-week reversal (M1a) | NIFTY-200 PIT, weekly, `s = −r(t−5,t)`, dev 2012–22, n 569, IC +0.0232, t 3.76; net −16.8% (SPEC §3.1) | A | Single in-sample dev window; cost-killed |
| PSB-1 C2 | Idiosyncratic (market-residual) 1-week reversal (M1b) | 52-week beta residual / σ(ε), n 529, IC +0.0352, t 6.63 (SPEC §3.2) | A | Single in-sample window; cost-killed |
| CB-N50 reversal & momentum features | Cross-sectional 1–20-day reversal, next-day horizon (M1a) | Nifty 50 PIT, daily, open t+1 → open t+2. TRAIN reversal L1 IC +0.0459 (t 8.42); momentum L5/10/20 IC −0.041/−0.028/−0.021, i.e. reversal. Combined HOLDOUT +0.0294, NW t 4.35 (SPEC §3.6) | A | HOLDOUT figure is reversal + basis combined; basis contract UNKNOWN |
| CB-N50 basis feature | Cross-sectional basis → next-day stock return (M7a) | TRAIN IC +0.0557, NW t 12.13 (SPEC §3.6) | B | Basis contract and day-count UNKNOWN |
| ISD F4 | Cross-sectional overnight-gap reversal (M1d) | F&O PIT, TRAIN 2023-01 → 2024-11, IC −0.0289, NW t −6.09 (SPEC §3.7) | A | Cost-killed; per-cell ICs only in a secondary memo |
| ISD F1 | Cross-sectional intraday opening-drive continuation (M2e) | Windows 30/45 min; sign wrong (IC −0.0166, t −2.81, secondary) (SPEC §3.7) | A | Failed on sign |
| PSB-2 C4 | Cross-sectional 12-1 momentum, long-only (M2a) | Monthly, dev 2012–22, n 131, IC +0.0466, t 2.55, power 0.41 (SPEC §3.5) | A | Single dev window |
| F1 screen | 12-1 momentum, ≤ 10 names, + ATR(21) bracket (M2a, M13) | TRAIN 2012–18 n 83, HOLDOUT n 47 (SPEC §3.15) | A (momentum); B (bracket) | Exploratory; grid interior UNKNOWN; report/code conflict |
| Trend sleeve | Cross-sectional rank of vol-scaled 63/126/252 TSMOM (M2b) | SSF, monthly, TRAIN n 59, IC +0.0219, t 1.13 FAIL (SPEC §3.9) | A | HOLDOUT never read |
| PSB-1 C3, PSB-2 C2 | Abnormal delivery share → informed accumulation (M5a) | C3 weekly IC +0.0248, t 2.93; C2 fortnightly IC +0.0349, power 0.92, then Phase 0.5 TRAIN power ≤ 0.66 (SPEC §3.3–3.4) | A | Retired on power |
| Carry v1/v2 | Residual futures basis → 1-month **spot** return (M7a) | v1 sign fail; v2 HOLDOUT IC +0.0544 (t 3.31); SEALED +0.0610, net +20.52% spot (SPEC §3.10) | B | Dividend sign inverted in code; PIT uncertifiable; EW-quintile gate; futures spread gross t ≈ −0.8 |

**Time-series, single instrument or index**

| Construct | Economic mechanism | Key evidence | Status | Limitations |
|---|---|---|---|---|
| A (index intraday) | Opening-window continuation (M2d) | Nifty 50 1m proxy, sign of bars 0..30/45, exit 15:14; TRAIN pass, HOLDOUT net −0.22 bp FAIL (SPEC §3.8) | A | Construct-doc grid says 15:29 (stale) |
| **RELIANCE daily study** *(v1.1)* | Single-instrument multi-day trend (M2c); level-crossing breakout (M3a); regime gates (M9a) | Scope and results in the **RELIANCE detail** below | **B** (M2c, M3a) | One large-cap name; long/flat; daily; binary rules; **IC defect R1**; RECENT panel is sealed-era data |
| **MRLC test** *(v1.1)* | Liquidity-sweep rejection (M3b), conjoined with a stretch and a volume condition | Rule and results in the **MRLC detail** below | **B** (M3b) | Conjunctive; selection over 24 cells; ideal fills; survivorship; R unit undefined in the test report; not a fresh pre-registered holdout |
| Late-cycle stock straddle | Unconditional short-premium harvest (M8a) | ~160–190 F&O stocks; discovery 2016–22 t 6.05; confirmation 2023–26 t 3.78 (SPEC §3.11) | B | Exploratory; liquidity filter ambiguous; spread-charge method UNKNOWN |
| MSRP D1 | Forecast-gated index straddle (M8b) | Nifty weeklies, 2023–25 in-sample, ρ(signal, return) −0.027 (SPEC §3.12) | B | Strike rule UNKNOWN; in-sample coefficients |
| Nifty/BankNifty z-score | Relative-value spread reversion (M6a) | Johansen not cointegrated; bootstrap p 0.354; 27 intraday combos negative (SPEC §3.13) | B | Z formula, hedge ratio and exit semantics UNKNOWN |
| Gann GF-1 / GF-4T/R8 / GF-10 | Time geometry of swings (M10a) | PIT N100, weekly, 2011-03 → 2022-12, p_sur 0.953/0.980/0.214 (SPEC §3.14) | A | Non-confirmatory screen |
| DRA HMM-gated EMA | Regime-gated intraday trend entry (M9a) | Nifty 50 cash, walk-forward 2023–26, 200 trades, −₹1,647, no significance test (SPEC §4) | B | LEGACY; primary report absent; ATR period UNKNOWN |
| **DayType directional prior** *(v1.1, evidence for M9a)* | 13:00 session-archetype label as a directional prior on the afternoon | Separation figures and caveats in the **DayType detail** below | B (as M9a evidence) | Out of sample for the classifier only; label fit over 2012–2025; no cost-inclusive gated P&L; count and training-span contradictions (§9) |
| **W2 afternoon variance** *(v1.1, evidence for M9c)* | Afternoon serial dependence (VR) by 13:00 DayType label | Pre-registered 2026-09-27; Nifty 1m 2023-01-02 → 2026-09-25, 899 sessions; pooled pre-CAS VR 1.046 [0.917, 1.204]; by label (2024+), CIs overlap → "no detectable path difference by label" (CLOSE §3) | C (for M9c) | Tests a label as a predictor of dependence, not a past-data dependence estimator as the regime signal |

**RELIANCE detail** (CLOSE §3)
- **Scope:** RELIANCE delivery equity, long/flat, close-to-close, era-accurate delivery fees.
  Panels: DEV 2010–19, VAL 2020–22, RECENT 2023–26-09.
- **M2c rules:**
  - `ts_mom_{63,126,252}` = sign of the trailing return, with a 1-day skip.
  - `sma_{50,100,200}` = close > SMA.
- **M2c results:**
  - `sma_200` net +6.0 / +8.1 / +1.7%.
  - Full-span bootstrap CI of the `sma_200` daily mean [−0.01%, +0.06%] includes zero; excess vs buy-and-hold −7.7%/yr.
- **M3a rule:** `donchian_{63,252}` = close > prior N-day high, excluding today.
- **M3a results:**
  - DEV `donchian_252` +0.8% (in market 2%).
  - VAL `donchian_63` +4.2%.
  - RECENT `donchian_252` −3.2%.
- **M9a gates:** `vol_calm`, `idx_trend`, and `combined`, whose net is −1.4 / −1.4 / −4.9%.

**MRLC detail** (CLOSE §3)
- **Rule:**
  - Entry conditions:
    - stretch ≥ threshold below the 25-day average;
    - a sweep: close below the 10-session low on ≥ 2× usual volume, then a close back above it within 3 bars;
    - a news guard: skip 3 sessions after a ≥ 8% crash.
  - Entry is the next open.
  - Stop: sweep low − 2× ATR.
  - Exits: 50% at the 25-day average, the rest via breakeven then a 2× ATR trail; 20-session time stop.
  - Delivery fees.
- **Results:**
  - Dev 1h ≤ 15%: 40 trades, +0.72 R, t 2.12.
  - 2012–22 daily, 2,300 PIT symbols, ≤ 15%: 1,017 trades, +0.24 R, t 8.62.
  - Archive, Nifty-100 1m, 2015–22, 4h ≤ 10%: 109 trades, +0.19 R, t 1.90.

**DayType detail** (CLOSE §3)
- **Result:** BullTrend minus BearTrend forward return +0.2546 pp [+0.197, +0.312], n 805/801, sessions ≤ 2022.
- **Traded window, 13:00→15:15:** +0.2305 pp [+0.165, +0.299], class counts 614 / 561.

**R1: RELIANCE IC defect** (CLOSE §3; established by reading code, not re-run, not repaired)
- The P&L is causal: `pos = sig.shift(1)`, against `ret = close.pct_change()` (`data.py:66`).
- The IC is not: `np.corrcoef(sig[valid], ret)` pairs the **unshifted** signal with the **same-day** return.
- **What stands and what doesn't:**
  - The **net-return and bootstrap figures stand.**
  - **The reported ICs are contemporaneous**, so the study's "daily return continuation is real … twice replicated" claim is not established.
- **No RELIANCE IC is used anywhere in this map as evidence of direction.**

### 2.2 Tested mechanisms added from CLOSE §2.3 (not re-audited in SPEC; no C/D effect)

These were tested but omitted from v1 §2. They are recorded with their documented outcome and are
**not given a status letter here**, because SPEC did not audit their specifications. No new mechanism
IDs are created.

**Cross-sectional** (all essentially absent from the Vault)

| Construct | Mechanism | Documented outcome (CLOSE §2) |
|---|---|---|
| PSB-1 C5 | Cross-sectional low volatility: s = −σ(252d), monthly, banded | Tested; closest PSB-1 candidate, missed power (CLAUDE.md PSB-1 table) |
| IVOL | Cross-sectional idiosyncratic volatility (SSF) | TRAIN/HOLDOUT PASS; SEALED FAIL (sign flip) |
| Skew | Cross-sectional 25Δ risk-reversal | TRAIN FAIL |
| LAG | Cross-sectional sector lead-lag diffusion | TRAIN FAIL (IC −0.0307, t −1.43) |
| TS Basis / TS Basis Daily | Own-history basis z, ranked cross-sectionally: a variant of M7a | M7a stays **B**; the basis-family spot-vs-futures issue applies (`BASIS_FAMILY_POST_MORTEM_2026-09-24.md`) |

**Out-of-taxonomy** (no Vault family maps to these)

| Construct | Mechanism | Documented outcome |
|---|---|---|
| GEX Stage A / B1 | Dealer gamma exposure → next-day realised/implied vol; GEX-gated iron fly | Stage A PASS (TRAIN t −3.20, HOLDOUT t −2.65); B1 STOP (gated fly net Sharpe −0.75) |
| Intraday Analog Path | Nifty 09:15→12:30 path shape beyond endpoint return | HOLDOUT: NO (path adds nothing beyond R). Its return-only baseline is further M2d-type evidence |
| DayType | Intraday session-archetype nowcast used as a directional prior | Counted as M9a evidence (§2.1) |
| N200 HMM | Per-stock volatility-regime forecastability (forward-vol target) | Variants A and B FAIL |

**Non-mechanism programs examined** (CLOSE §2), for completeness:
- PSB-1 C4 and PSB-2 C3 (cross-sectional, already inside M1a/M5a)
- OSC (option cross-section, RFA ABANDON)
- N50-LS (RFA ABANDON)
- MSI (architecture)
- the options survey
- the options direction read (one session)
- PTMS Family G (not frozen)
- **Trade Intelligence M0.5/M2: E.** The reports do not name the trade book they analyse.

---

## 3. Mechanism taxonomy — Vault family → economic mechanism → variants

Unchanged from v1. The closure pass required no taxonomy correction.

| Vault family (family n) | Economic mechanism(s) it expresses | Variants folded in (not separate mechanisms) |
|---|---|---|
| MA trend-transition (1,245), MACD/momentum (235), Ichimoku (36), SAR (5), vol-stop trend (220, as entry) | **M2c** single-instrument time-series trend persistence | MA cross / stack / slope, HMA/VWMA/VIDYA/Kalman smoothers, MACD line/zero cross, Tenkan/Kijun, SAR flips, Supertrend flips; lengths, thresholds, MTF agreement filters |
| Vol-stop trend (as exit), stop/TP machinery (83% of files mention SL) | **M13** volatility-scaled exit / bracket rules | ATR trail, Chandelier, fixed-multiple SL/TP |
| Oscillator reversion (682), Band/channel (148, reversion use), Z-score switching (7 name hits), regression/quadratic bands (44 name hits) | **M1c** single-instrument short-horizon overshoot reversion | RSI/Stoch/KDJ/CCI/Williams/MFI extremes; BB/Keltner re-entry; z-bands; regression envelopes. Divergence (61 name hits) folded in as a conditioning variant |
| Grid/martingale/DCA (71) | Grid: **M1c** at grid spacing. Martingale/DCA: **sizing rule, not a mechanism** | Grid spacing, ladder depth, averaging rules |
| Breakout/range (189), Band/channel (break use), squeeze (15 name hits) | **M3a** range-escape continuation; **M4a** volatility compression → expansion | Donchian, 52-week, box, opening-range break, BB/Keltner squeeze release, σ-scaled breakout |
| Breakout/range (FVG subset: 24 "gap" name hits), Pattern/price-action (121; candlestick 189 name hits) | **M3b** rejection of an extreme / liquidity sweep / liquidity-zone revisit | Failed breakout, sweep-and-reclaim, hammer/engulfing, FVG fills |
| Pattern/price-action (Fib/harmonic 91 name hits, pivots, S/R) | **M10b** price-level geometry | Fib levels, ABCD/harmonic, pivot points, round numbers |
| Pattern/price-action (swing time), census "Hurst" (2) | **M10a** time geometry; **M9c** serial-dependence regime | Swing-duration counts; Hurst gate |
| Volume/flow (43; 198 volume/vwap/obv name hits) | **M5b** volume-confirmed moves; **M5c** VWAP anchoring; **M5d** signed order-flow imbalance | OBV, MFI, FVE, volume breakouts; VWAP cross/reversion; CVD/volume delta |
| ADX/DMI (19) | **M9b** trend-strength regime gating | ADX thresholds, DMI crosses |
| Seasonal/calendar (10; ~26 name hits) | **M11a** calendar-timed flow; **M11b** intraday time-of-day | Day-of-week holds, month-end, sell-in-May, session-clock trades |
| Hedge/arbitrage (42; ~10–15 genuine) | **M6a** relative-value spread reversion; **M6b** same-asset venue/product spread capture | Pair z-bands, cross-exchange spot/perp |
| Carry/funding/basis (2 + monitors) | **M7a** basis as predictor; **M7b** hedged carry capture | Funding-rate monitors, spread executors |
| Options-vol selling (2; 22 option name hits) | **M8c** indicator-timed short premium | RSI/BB/EMA-gated ATM selling |
| Combo (2,306) | Not a mechanism: AND-conjunctions of the above | — |
| ML/"AI"/Kalman (16 name hits) | Not a mechanism: model classes over the above | — |
| UNCLEAR (389), NON-STRATEGY (44+) | Unclassified / none | — |

Cross-sectional mechanisms that are essentially absent from the Vault: M1a, M1b, M1d, M2a, M2b, M2e,
M5a, M7a. The §2.2 cross-sectional additions also belong in this group.

### 3.1 Borderline deduplication decisions (v1, with v1.1 notes)

1. **M1a vs M1c kept separate.** Cross-sectional reversal ranks relative returns; single-instrument
   reversion bets on the absolute path.
2. **Divergence folded into M1c.** A momentum-decay-without-extreme hypothesis would need its own row.
3. **M3a kept separate from M2c.** Breakout conditions on a level event; trend conditions on a
   smoothed slope. v1.1 note: RELIANCE tested both, with separate rules (`donchian_*` vs `sma_*`/`ts_mom_*`).
4. **Candlestick and FVG folded into M3b.** v1.1 note: B-coverage applies to the MRLC sweep-and-reclaim form only. **Candlestick and FVG remain untested.**
5. **Grid folded into M1c.**
6. **Vol-stop as entry (M2c) vs as exit (M13).**
7. **Opening-range breakout (M3a) vs A's opening-window direction (M2d):** adjacent, not equivalent.
8. **(v1.1) MRLC conjunction assigned to M3b, not M1c or M5b.**
   - The construct's design document names the sweep as the edge ("That premise is the entire
     edge", `MRLC_CONSTRUCT_ASSESSMENT.md` §1.1).
   - Its §1.2 table calls the 25-day SMA divergence a positioning filter (CLOSE §3, §5).
   - The stretch and volume conjuncts therefore give M1c and M5b adjacent evidence only.

---

## 4. Coverage map (master table)

| ID | Mechanism family | Economic hypothesis | Vault evidence | Existing research | Status | Exact coverage evidence | Material difference / gap | Data available? | Candidate for new research? |
|---|---|---|---|---|---|---|---|---|---|
| M1a | Short-horizon reversal, cross-sectional | Recent relative losers outperform over 1 day – 1 week | ~none (4 rotation name hits) | PSB-1 C1; CB-N50 reversal + momentum L5–20 | **A** | SPEC §3.1; SPEC §3.6 | — | Yes | No (covered) |
| M1b | Idiosyncratic (residual) reversal | The market-stripped part of last week's move reverts | none | PSB-1 C2 | **A** | SPEC §3.2 | — | Yes | No |
| M1c | Short-horizon overshoot reversion, **single instrument, time-series** | An extreme move relative to its own recent distribution reverts in absolute terms | Oscillator 682; band-reversion subset of 148; z-score 7; grid 71; divergence 61 name hits | Closest: M1a/M1b (cross-sectional); pair z-score (B); **RELIANCE `reversal_5`** (sign rule: long iff 5-day return < 0; net +2.3 / −8.6 / −2.2%); **MRLC stretch** (≥ 10–20% below the 25-day average, reversion to the average) **only jointly with a sweep** (CLOSE §4) | **C** (C/B borderline, §9) | — | `reversal_5` is a sign rule, not reversion from an extreme. MRLC tests a conjunction. "Never tested" is false for a sign rule and for the sweep-conditioned form | Index 1m 2012+, equity 1m 2023+, daily bhavcopy 2010+ | Yes, only for **extreme reversion not conditional on a sweep** |
| M1d | Overnight-gap reversal, cross-sectional | Large overnight gaps revert intraday relative to peers | ~0 | ISD F4 | **A** | SPEC §3.7 | — | Yes | No |
| M2a | Intermediate momentum, cross-sectional | 12-1 month relative winners keep outperforming | 4 rotation name hits | PSB-2 C4; F1 | **A** | SPEC §3.5; SPEC §3.15 | — | Yes | No |
| M2b | Vol-scaled TSMOM, ranked cross-sectionally | Names with stronger own-trend outperform peers | none | Trend sleeve | **A** | SPEC §3.9 (FAIL) | — | Yes | No |
| M2c | Trend persistence, **single instrument, multi-day, time-series** | An instrument trending (by slope, crossover or trailing return) keeps moving the same way in absolute terms | MA 1,245; MACD 235; vol-stop 220; Ichimoku 36; SAR 5; plus most of Combo 2,306 | **RELIANCE daily study** (v1.1); also M2b (ranking), A (intraday), DRA (legacy) | **B** *(v1: C)* | CLOSE §3: `ts_mom_{63,126,252}`, `sma_{50,100,200}` long/flat, causal P&L (`pos = sig.shift(1)`), delivery fees, DEV 2010–19 / VAL 2020–22 / RECENT 2023–26. `sma_200` net +6.0 / +8.1 / +1.7%; full-span bootstrap CI includes zero; excess vs buy-and-hold −7.7%/yr | One large-cap name; long/flat; daily; binary rules. **R1:** ICs are contemporaneous and not evidence of direction. No index/futures/other-name/long-short form. RECENT panel is sealed-era data. MACD, Ichimoku, SAR and Supertrend implementations not tested | Index daily 2012+ and 1m 2012+; SSF daily 2016+; equity daily | Yes, only for forms **beyond one large-cap, long/flat daily name** (e.g. index, futures, other names, long/short, broader universe) |
| M2d | Opening-session continuation, index time-series | The first 30/45 minutes' direction persists to the close | 4 opening-range keyword hits (level breaks, not window sign) | A; Analog Path return-only baseline (§2.2) | **A** | SPEC §3.8 (HOLDOUT FAIL) | Doc caveat: 15:29 vs frozen 15:14 (carried) | Yes | No |
| M2e | Opening-drive continuation, cross-sectional equity | Strongest first 30/45-min stocks outperform to the close | none | ISD F1 | **A** | SPEC §3.7 (wrong sign) | — | Yes | No |
| M3a | Range-escape continuation | Crossing a defined range boundary triggers continuation via clustered orders/stops | Breakout 189; ~1,252 heavily overlapping breakout/channel/donchian name hits | **RELIANCE `donchian_{63,252}`** (v1.1); Gate 0 F-RANGE breakout (**priced only**) | **B** *(v1: C)* | CLOSE §3: close > prior N-day high excluding today; causal P&L; DEV `donchian_252` +0.8% (in market 2%); VAL `donchian_63` +4.2%; RECENT `donchian_252` −3.2% | One name, long/flat, daily. In market only 1–4% of days, so the evidence is thin by construction. The R1 caveat applies to the study's IC claims. **No intraday, opening-range, index or other-instrument form.** Not all breakout variants are covered | Index 1m/1d; equity 1m (2023+) / daily | Yes, only for forms **beyond the RELIANCE daily Donchian construct**: broader instruments, intraday, opening-range breakout |
| M3b | Rejection of an extreme / liquidity sweep / liquidity-zone revisit | A breach of a visible level that is then reclaimed reverses, because the breach harvested stop liquidity rather than carrying information | Pattern 121; candlestick 189, FVG ~24 name hits | **MRLC test** (v1.1); F-RANGE failed breakout (**catalogued only**) | **B** *(v1: D)* | CLOSE §3: close below the 10-session low on ≥ 2× volume, reclaimed within 3 bars, conjoined with stretch ≥ threshold below the 25-day average and a news guard. Dev 1h ≤15% +0.72 R (t 2.12); 2012–22 daily 2,300 PIT symbols ≤15% +0.24 R (t 8.62); archive OOS 4h ≤10% +0.19 R (t 1.90) | Sweep not isolated from the stretch and volume conditions. Selection over 24 cells; extension and archive are "consistency checks, not fresh pre-registered holdouts". Ideal fills; survivorship (2023–26, archive); R unit not defined in the test report; 2023–26 cells are sealed-era. **FVG and candlestick sub-variants untested.** Does not establish every failed-breakout implementation | Index 1m (no volume); equity 1m 2023+; equity daily 2010+ | Yes, only for the **untested remainder**: sweep without the stretch filter, index forms, FVG, candlestick. The MRLC sweep-and-reclaim form is already B |
| M4a | Volatility compression → expansion | Low realised range is followed by expansion, with direction resolved by the break | Squeeze 15 name hits; BB/Keltner squeeze subset | Closest: MSRP D1 (B); Gate 0 F-VOL (**priced only**); DRA HMM (legacy); **N200 HMM** (vol-state → forward-vol event, FAIL); **GEX Stage A** (positioning → next-day RV/IV) (CLOSE §4) | **C** | — | All forecast the level or events of volatility, or price options. None conditions a directional expansion trade in the underlying on compression. The GEX `ln_rv` coefficients are controls | Index 1m/1d, VIX 1d 2012+ | Yes |
| M5a | Informed accumulation via delivery share | Abnormally high delivery % signals informed buying | none | PSB-1 C3; PSB-2 C2 (+ Phase 0.5) | **A** | SPEC §3.3, §3.4 | — | Yes | No |
| M5b | Volume-confirmed price moves | Moves on abnormal volume persist; moves on thin volume revert | Volume family 43; ~198 name hits, mostly filters | Closest: M5a; Flow (**RFA only**); **MRLC ≥ 2× volume sweep conjunct** (CLOSE §4) | **C** | — | Volume appears only as one conjunct of MRLC, with no ablation. Delivery % is position-taking share, not total-volume shocks | Equity daily volume 2010+; equity 1m 2023+; **index volume = 0** | Yes |
| M5c | VWAP anchoring | VWAP-benchmarked execution creates pull or support around session VWAP | 49 VWAP-titled files | Gate 0 excluded VWAP (index volume 0); DRA VWAP filter bypassed on index; RELIANCE `vwap_E1` is an **execution variant**; DayType/JEV TWAP-distance **features** (CLOSE §4) | **D** | — | Never tested as a pull or support mechanism | Equity 1m 2023+ only | Yes (equity only) |
| M5d | Signed order-flow imbalance | Net aggressor volume predicts short-horizon drift or reversal | CVD/volume-delta files | None | **D** | — | No test | **Insufficient** (no signed trades) | Data-blocked |
| M6a | Relative-value spread reversion | A two-asset ratio reverts to its mean | 12 pair name hits | Nifty/BankNifty z-score | **B** | SPEC §3.13 | Rule UNKNOWN; one pair | Index 1d/1m | Only as a specification-complete re-test, or other pairs |
| M6b | Same-asset venue / product spread capture | Segmented liquidity lets one asset trade at different prices | ~10–15 genuine files | None | **D** | — | No test | **Insufficient** (NSE only) | Out of current data scope |
| M7a | Basis as a cross-sectional return predictor | Residual futures basis predicts forward (spot) returns | ~0 | Carry v1/v2; CB-N50 basis; TS Basis (§2.2) | **B** | SPEC §3.10; SPEC §3.6 | Dividend sign defect; PIT uncertifiable; portfolio divergence; spot-not-futures | Yes | No new mechanism |
| M7b | Hedged carry capture | Holding the hedged spot/futures pair earns the basis as it converges | ~5 files | Closest: Carry futures-translation review; **basis-family post-mortem** (convergence −137 / −101 bp/month on the Q5−Q1 book) (CLOSE §4) | **C** | — | Convergence measured as a component of a signal-ranked L/S futures book, not as a hedged position with its own financing and costs | SSF + equity daily 2016+ | Yes |
| M8a | Unconditional short-premium harvest (stock, late cycle) | Late-cycle single-stock option premium exceeds realised payoff | 2–22 name hits | Seller-edge study (+ W6 CA-filter split) | **B** | SPEC §3.11 | Exploratory; forward M10 pre-registered, not yet run | Stock options 2016+ | Covered as a mechanism |
| M8b | Forecast-gated premium timing (index) | Selling premium only when forecast RV is low vs implied improves returns | Indicator-gated options files | MSRP D1; straddle P5 | **B** | SPEC §3.12; §3.11 | Strike rule UNKNOWN; in-sample | Nifty options to 2026-07 | No new mechanism |
| M8c | Indicator-timed premium selling | Price-state signals (RSI/BB/EMA) time short-premium entries | 2 census files; 1 name hit | Closest: M8a, M8b; **NiftyShield** (DayType + VIX selection; forward PAPER only, no completed experiment); **GEX-gated fly** (positioning, B1 STOP); counterfactual battery (9 sessions, descriptive) (CLOSE §4) | **C** | — | A paper book in progress is not a result. The GEX gate is positioning, not a price-state signal | Stock options 2016+, Nifty options to 2026-07 | Yes (only if the price-state → premium link is the hypothesis) |
| M9a | Regime-gated directional trading | A state model identifies when a directional rule works | Regime filters in 68% of files | DRA HMM-gated EMA; **RELIANCE `vol_calm` / `idx_trend` / `combined`**; **DayType directional prior** (v1.1 evidence) | **B** | SPEC §4; CLOSE §3 (RELIANCE combined net −1.4 / −1.4 / −4.9%; DayType +0.2546 pp [+0.197, +0.312]) | One stock (net P&L, unaffected by R1); DayType label fit over 2012–2025 (out of sample for the classifier only); DRA legacy; no cost-inclusive DayType-gated P&L | VIX, index 1d/1m | No new mechanism; open items are specification |
| M9b | Trend-strength gating | Trend rules work only when ADX/DMI strength is high | ADX 19 | Closest: DRA rule-based detector (code only); DRA HMM | **C** | — | No ADX-conditioned result | Index/equity OHLC | Yes, as a conditioning layer on a base rule |
| M9c | Serial-dependence regime | The autocorrelation sign is forecastable, selecting trend vs reversion | Hurst 2 name hits | **W2** (pre-registered: afternoon VR by DayType label, null); **DayType transition diagnostic** (archetype persistence, INCONCLUSIVE); **JEV** B1 persistence baseline (CLOSE §3) | **C** *(v1: D)* | — | Serial-dependence questions *were* investigated, but not the v1 mechanism: **a past-data dependence estimator (Hurst/VR) used as an ex-ante regime signal to choose between trend and reversion rules, in multi-day form**. W2 is null; transition labels come from a whole-sample fit | Index 1d/1m, equity | Yes, only for the dependence-estimator-as-regime form |
| M10a | Time geometry of swings | Elapsed-time counts predict a minor trend change | Pattern subset | Gann GF-1, GF-4T/R8, GF-10 | **A** | SPEC §3.14 | — | Yes | No |
| M10b | Price-level geometry | Fixed ratio or pivot levels attract or reject price | Fib/harmonic 91 name hits; pivots | Gann GO-1 (**catalogued**), GO-3 (**descriptive**); Options-Wall OI/gamma walls (no historical test; DW-1 DRAFT) (CLOSE §4) | **C** | — | Gann tested time only. OI-derived walls are neither geometry nor tested | Daily / 1m OHLC | Yes |
| M11a | Calendar-timed flow | Schedule-driven flows shift returns by calendar position | Seasonal 10; ~26 name hits | Gann GT-4 (**descriptive**); `STRUCTURAL_ALPHA_DOSSIER.md` §B lists expiry-day, month-end and RBI-event as **Untested**; `day_of_week` only as a discarded ML-filter feature (CLOSE §4) | **D** | — | Never tested | Index 1d 2012+, equity daily 2010+ | Yes |
| M11b | Intraday time-of-day | Expected return or reversal differs by time of session | 8 session name hits | Gate 0 F-TOD (**priced only**); W2 variance share; JEV B0 slot climatology; counterfactual battery slot cut (9 sessions) (CLOSE §4) | **D** | — | Variance shares and state-class frequencies are not expected return by time; the 9-session cut is descriptive | Index 1m 2012+, equity 1m 2023+ | Yes |
| M13 | Volatility-scaled exit / bracket | Vol-normalised stops/targets change the payoff of a given entry | Vol-stop 220; SL mentions 83% | F1 ATR(21) bracket; DRA ATR SL/TP; MRLC ATR stop/trail (inside a conjunction) | **B** | SPEC §3.15; SPEC §4 | Grid interior UNKNOWN; report/code conflict; DRA ATR period UNKNOWN | Daily OHLC; 1m | Payoff modifier, not a return mechanism |

Non-mechanisms (excluded from status): martingale/DCA sizing; Combo conjunctions; ML/Kalman model
classes; MTF agreement filters; non-strategy files.

---

## 5. False coverage audit

Earlier labels (Gap Map `2230023`, parts of COV, and v1 itself) that must **not** be read as stated:

| Earlier claim | Correct reading (v1.1) | Why |
|---|---|---|
| "MA trend-transition = AR" | M2c is **B**, but **via the RELIANCE study only**, not via the constructs the gap map cited | The Trend sleeve ranks cross-sectionally (SPEC §3.9), A is fixed-time intraday (SPEC §3.8), DRA is legacy. The actual single-instrument test is one long/flat large-cap name, with IC defect R1 (CLOSE §3) |
| v1: "No single-instrument multi-day trend rule was ever run" | **Retracted** | RELIANCE ran TSMOM and SMA rules with causal P&L (CLOSE §1, §3) |
| "MACD = AR" | Part of M2c (**B**), but MACD itself is not tested | Only TSMOM/SMA binary rules were run; no EMA-difference trigger in any tested spec |
| "Breakout = AR / cost-dead" | M3a is **B** via RELIANCE Donchian only; **not** cost-dead | Gate 0 priced breakouts with no data read. The only data test is daily Donchian on one name, thin in-market exposure |
| "Oscillator reversion covered via cross-sectional reversal" | M1a/M1b are **A**; M1c is **C** (C/B borderline) | Cross-sectional tests do not cover absolute reversion. `reversal_5` is a sign rule; MRLC's stretch is tested only jointly with a sweep |
| "Volatility stops covered via F1" | M13 is **B** as an exit; as an entry it sits inside M2c (**B**, via SMA/TSMOM only, not Supertrend) | F1's bracket was selected to near-inactivity |
| "Grid = repackaged short-vol / reversion" | Grid sits under M1c, **C** | A conceptual reduction is not a test |
| "Pattern/price-action = RD via Gann" | M10a is **A** (time only); M10b is **C**; M3b is **B via MRLC**, not via Gann | Gann tested time counts. The sweep evidence comes from MRLC; candles and FVG remain untested |
| v1 / COV: "F-RANGE/MRLC catalogue and analysis only" | **Retracted for MRLC**; F-RANGE remains catalogue only | MRLC was backtested 2026-08-30/31. v1 had seen only the 2026-08-29 analysis document (CLOSE §1) |
| "Volume/flow = RD" | M5a **A**; M5b **C**; M5c/M5d **D** | Only delivery composition was tested; MRLC volume is a conjunct |
| "Carry = AR" | M7a **B**; M7b **C** | Documented defects; capture never tested |
| "Options selling = AR" | M8a/M8b **B**; M8c **C** | Indicator timing never tested; NiftyShield is paper-only |
| "ADX = RD" | M9b **C** | No ADX-conditioned result |
| "Hedge/arb = RD" | M6a **B**; M6b **D** | Pair study under-specified; venue arbitrage untested |
| "Intraday breakout / TOD / vol-state are cost-dead" | Priced infeasible, **not tested** | Gate 0 read no data |
| v1: "M9c — no dependence-structure regime test" | Too strong: M9c is **C** | W2 and the transition diagnostic investigated dependence-related questions; the estimator-as-regime form is untested |

---

## 6. Genuine blind spots (D, after deduplication)

**Removed from D in v1.1:**
- **M3b → B** (MRLC)
- **M9c → C** (W2, transition diagnostic)

M2c and M3a were C in v1 and are now B.

| ID | Economic hypothesis | Why it is genuinely new | Existing data required | Store sufficient? | Major specification questions | Why a separate mechanism |
|---|---|---|---|---|---|---|
| M5c | VWAP-benchmarked execution creates pull or support around session VWAP | No test anywhere; RELIANCE's VWAP entry is an execution variant only | Equity 1m with volume | Equity 1m 2023+ (filter `is_synthetic` post-CAS); **not index** | Anchor definition; reversion vs continuation sign; cross-sectional vs single-name | Execution-flow rationale no tested construct uses |
| M5d | Signed aggressor imbalance predicts short-horizon drift or reversal | No test | Signed trades or quotes | **Insufficient** | Whether bar-direction proxies are acceptable; the record does not say | Different information (who initiated) |
| M6b | Same-asset price differences across venues/products converge | No test | Synchronous multi-venue prices | **Insufficient** (NSE only) | Venue scope; latency | Location arbitrage |
| M11a | Schedule-driven flows shift returns by calendar position | Never tested; the dossier lists calendar items as Untested | Daily index/equity returns | Yes | Which calendar effect; index vs cross-section; holiday handling | Information set is the calendar itself |
| M11b | Intraday expected return or reversal differs by time of session | Gate 0 only priced it; related items measure variance or state classes, not return | Index/equity 1m | Index 1m 2012+ (label-era offset); equity 1m 2023+ | Standalone vs conditioning axis; CAS-era session change | Time-of-session as the signal |

**Untested remainders of B/C mechanisms.** These are not new D rows; they are listed so they stay visible:

| Parent | Untested remainder |
|---|---|
| M3b (B) | Candlestick rejection; FVG revisit; sweep without the stretch filter; index forms |
| M9c (C) | Past-data dependence estimator (Hurst/VR) as an ex-ante regime signal choosing trend vs reversion, multi-day |
| M1c (C) | Extreme reversion not conditional on a sweep (oscillator, band, z-score extremes) |

---

## 7. "Do not test yet": new at the indicator level, covered economically

| Looks new | Already-covered mechanism | Evidence |
|---|---|---|
| Cross-sectional RSI/Stochastic rank, 1–5-day reversal rotation | M1a | SPEC §3.1, §3.6 |
| Beta- or factor-residual weekly reversal variants | M1b | SPEC §3.2 |
| Momentum rotation, 6-/12-month rank rotation | M2a | SPEC §3.5 |
| Vol-scaled multi-horizon momentum rank | M2b | SPEC §3.9 |
| Re-parameterised first-30/45-minute index direction rules | M2d | SPEC §3.8 |
| Equity opening-drive rank variants | M2e | SPEC §3.7 |
| Cross-sectional overnight-gap fade variants | M1d | SPEC §3.7 |
| Delivery-% z variants | M5a | SPEC §3.3–3.4 |
| Gann time-count variants | M10a | SPEC §3.14 |
| Basis-rank variants, incl. own-history z | M7a (B) | SPEC §3.10; §2.2 |
| VRP-bucket tilts on stock straddles | M8b | SPEC §3.11 P5 |
| **Re-parameterised long/flat daily SMA/TSMOM rules on RELIANCE** | M2c (B) | CLOSE §3. This covers **only** that name and form; MACD, Ichimoku, SAR, Supertrend and other instruments are **not** covered |
| **Re-parameterised daily Donchian lookbacks on RELIANCE** | M3a (B) | CLOSE §3. Other breakout implementations (box, 52-week on other names, squeeze release, opening-range, intraday) are **not** covered |
| **Re-thresholded MRLC cells (stretch %, stop multiple, timeframe)** | M3b (B) | CLOSE §3. Selection over 24 cells already occurred |
| Martingale/DCA sizing overlays; Combo conjunctions; ML-labelled versions | Not mechanisms | CENSUS §10.5, §10.8 |

---

## 8. Research-queue candidate list (unranked, neutral)

This is an inventory of eligible forms, **not** an instruction to test anything now.

**Group D (no materially equivalent experiment):** M5c, M11a, M11b. Data-blocked: M5d, M6b.

**Group C and B remainders.** Each is eligible only if the hypothesis is the stated distinction:

| ID | Status | Eligible only if the hypothesis is… |
|---|---|---|
| M1c | C (C/B borderline) | **Extreme reversion not conditional on a sweep**: absolute single-instrument reversion from its own extremes, not cross-sectional ranking, not a sign rule |
| M2c | B | A form **beyond one large-cap, long/flat daily name**, e.g. index, futures, other names, long/short, broader universe |
| M3a | B | A form **beyond the RELIANCE daily Donchian construct**, e.g. broader instruments, intraday, opening-range breakout |
| M3b | B | The **untested remainder**: sweep without the stretch filter, index forms, FVG, candlestick variants. The MRLC sweep-and-reclaim form is already B-covered |
| M4a | C | Compression-conditioned expansion in the underlying, not implied-vs-forecast vol or vol-level forecasting |
| M5b | C | Total-volume shocks conditioning price persistence, isolated from other conjuncts; not delivery composition |
| M7b | C | Convergence earned by holding the hedged position, not basis as a ranking signal |
| M8c | C | Price-state indicators timing premium sales, not vol-forecast, VRP or positioning conditioning |
| M9b | C | Trend-strength conditioning of a specified base trend or breakout rule |
| M9c | C | A past-data dependence estimator (Hurst/VR) as the ex-ante regime signal selecting trend vs reversion, multi-day; not a regime label predicting dependence |
| M10b | C | Price-ratio or pivot levels, not time counts or OI-derived walls |

**Group B (open items are specification or implementation, not new mechanisms):** M6a, M7a, M8a,
M8b, M9a, M13.

---

## 9. Uncertainty register

| Item | Why the classification is uncertain |
|---|---|
| **M1c: C vs B** | MRLC's stretch-below-average + reversion-to-average is an envelope-style extreme reversion, but it is tested only jointly with the sweep. Counting it depends on accepting a conjunction as coverage, which this map's rules reject. Held at C (CLOSE §5) |
| **M3b sub-variants** | Candlestick rejection and FVG revisit have no test. B applies to the MRLC sweep-and-reclaim form only |
| **RELIANCE IC defect (R1)** | Established by code reading, not a re-run. The study's direction (IC) claims are unestablished; only net-return and bootstrap figures stand. A re-run could move them either way; none is authorized here |
| **DayType training span** | "2023–24 train" (`diagnose_regime_horizon.py` and its report) vs "train_thru2023" (W2 prereg §2). Carried, not reconciled; it affects which sessions are in-sample for the M9a and M9c evidence |
| **DayType session counts** | Same ≤ 2022 window, two figures: the horizon diagnostic's 13:00 rows total ~2,684 sessions (805 bull / 801 bear); the ceiling report gives n = 1,950 (614 / 561). Carried, not reconciled |
| **DayType label definition** | The KMeans label was fit over 2012–2025, so "out-of-sample" results are out of sample for the classifier, not for the label |
| **Trade Intelligence M0.5/M2: E** | 10–11k trades, rank 1–10, TP/SL, ~2-day holds. The reports opened do not name the source book; mechanism relevance is undetermined |
| **Sweep completeness** | CLOSE swept `docs/reports/**` filenames and keywords, matched every `scripts/*/` and `scripts/research/*/` directory, checked the research-library outcomes, and ran `git branch -a`. An operator-local or poorly named study may still be missing |
| 389 Vault UNCLEAR files | The filename carries no mechanism (CENSUS §10.6); not classified |
| M9a (DRA) | Only secondary evidence (dossier) for the legacy component |
| M6a | The pair study's rule cannot be reconstructed; B asserts that *a* spread-reversion test happened, not *which* |
| M1c vs divergence | A momentum-decay-without-extreme hypothesis would need its own row |
| M3a vs M2c | The Donchian/long-MA overlap is a judgment call; RELIANCE tested them as separate rules |
| M11b | The Stage-A design treats time-of-day as a conditioning axis; standalone status uncertain |
| OI positioning (Flow) | RFA-abandoned, absent from the Vault; not mapped. GEX Stage A (§2.2) is a positioning → volatility test, not OI-flow → return |
| Carry economic identity | The futures-translation review reads Carry as a spot effect with anti-KMPV sign; M7a's "carry" label is contested |
| Vault name-hit counts | Title regex, overlapping and noisy; evidence of existence, not prevalence |
| M8a | Exploratory with a replicated confirmation; forward M10 pre-registration has no result yet |

---

## Quality check

1. M3b = **B**: yes (§4).
2. M2c = **B**: yes.
3. M3a = **B**: yes.
4. M9c = **C**: yes.
5. No A/B status weakened: yes. Every v1 A and B is carried, and M9a stays B with added evidence.
6. M1c remains C with the C/B borderline recorded: yes (§4, §9).
7. The untested M3b sub-variants remain visible: yes (§3.1, §4, §6, §8, §9).
8. RELIANCE IC defect R1 preserved: yes (§2.1, §4, §9).
9. The omitted tested mechanisms were added to the inventory: yes (§2.2; RELIANCE, MRLC, DayType, W2 in §2.1).
10. No new experiments run: yes.
11. No new data read: yes.
12. No holdout or sealed data consumed: yes.
13. No new mechanism invented: yes; no new IDs.
14. No mechanism ranked: yes.
15. Frozen status stated: yes (below).

---

## MAP STATUS: FROZEN v1.1

- The closure audit corrected four classifications: **M3b D→B, M2c C→B, M3a C→B, M9c D→C**.
- It retracted two false v1 statements and added the omitted tested mechanisms to the inventory.
- Every remaining uncertainty is recorded explicitly in §9: M1c C/B, the untested M3b sub-variants, RELIANCE R1, the DayType contradictions, and Trade Intelligence E.
- **No further broad archaeology is required before moving into research design.** Future research
  should treat this document as the **baseline coverage boundary**. A claim that a mechanism is
  "untested" should be checked against §4, §6 and §8 of this map, not against v1.
- **This is not a guarantee that every historical or internal artifact was found.** The closure sweep
  was by filename, keyword, script directory, research-library outcomes and branch listing. An
  operator-local or poorly named study may still exist. If one surfaces, it amends this map through a
  new, versioned correction layer; this frozen text is not edited in place.
