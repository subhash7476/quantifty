# M4a — Compression → Expansion — Research Design Inventory

**Date:** 2026-09-30 · **Branch:** `research/m4a-compression-expansion` (cut from `main` `d79a278`)
**Status:** inventory / design only. **No strategy built, no experiment coded, no parameter optimised,
no holdout read, no RFA filed, no Vault taxonomy modified.**
**Governing inputs (authority order):**
1. `RESEARCH_MECHANISM_COVERAGE_MAP_v1.1_2026-09-29.md` (**MAP**) — M4a status **C**.
2. `RESEARCH_MECHANISM_COVERAGE_CLOSURE_AUDIT_2026-09-29.md` (**CLOSE**) — M4a unchanged, C.
3. `RESEARCH_CLOSURE_LEDGER_2026-09-29.md` (**LEDGER**) — M4a: "C4 forecast-only … no directional test
   exists … fully open".
4. `BREAKOUT_VOLUME_PROTOCOL.md` / `BREAKOUT_VOLUME_RESEARCH_REPORT.md` (**BKV-1**) — the most recent
   protocol and closure template (hash-gated freeze, onset events, cohort-by-date, calendar-aware
   Newey–West, Holm, independent SQL re-derivation, C4–C9 mapping).
5. `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` (**REGISTER**) + **GR-1** spent-window rules.
6. `VAULT_MECHANISM_GAP_MAP_2026-09-28.md` + `Vault_STRATEGY_CENSUS.md` (**CENSUS**) — Vault is a
   hypothesis menu only; E2-at-best screenshots, ~78% crypto perps, no OOS.

**Level of every measurement in this document.** All counts below are **outcome-free** (meta/feature):
compression state is computed from information at or before *t*, and **no forward return, forward
range, or forward volatility is computed anywhere in this branch**. This mirrors BKV-1's pre-freeze
`diagnostics.py`. No reading outcome was produced, so no window is spent at signal level.

---

## 1. Executive Finding

**M4a is cleanly specifiable and empirically testable on already-present data. It is neither
infeasible nor arbitrary. It is genuinely untested (MAP/LEDGER status C), and the Vault does not
close it.** Recommendation: **PROCEED** to a smallest-defensible experiment, subject to one real
constraint below (window freshness).

What is established:

- **The mechanism is real and mechanically measurable at time *t*.** `compression` can be defined as
  a scale-free low state of a trailing realized-dispersion statistic (range, ATR, realized vol, or
  band width), using only data ≤ *t*. `expansion` can be defined as a forward increase in range,
  forward realized volatility, and/or absolute directional movement. Nothing must be invented: every
  ingredient already exists in the certified equity store (`equity_bhavcopy_adjusted`) and the index
  stores.
- **The Vault does not test it.** MAP maps M4a to "Squeeze 15 name hits; BB/Keltner squeeze subset";
  CLOSE finds the closest work is N200-HMM Variant B and GEX Stage A — both **forecast the level or
  the event of volatility**, neither conditions a directional or range expansion in the underlying on
  a prior compression state. LEDGER §8 states plainly: "M4a … C4 forecast-only; **No directional test
  exists … Fully open**".
- **The prior repo codebase had a compression→expansion strategy** (PixityAI `core/strategies/expansion_v3/`
  — `daily_compression_scanner.py`, `daily_breakout_trigger.py`, `hourly_breakout_trigger.py`, and
  `run_v3/v4/v8_backtest.py`). It was **not ported** in the SALVAGE migration and no reproducible
  result survives in this repo. It is **not** closure under the Vault's rules (§3).
- **Data is ample; events are abundant.** An outcome-free count on the already-hashed BKV dev panel
  (PIT top-200 turnover, entity-grain, CA-adjusted, ≤ 2022-12-30) finds ≈ **1,400–1,600 compression
  onsets per year** across ~200 names (≈ 7 per name-year), ~506 entities, over 13 years. Event count
  is **not** the binding constraint — the opposite of C5/C4/F1-style demonstrability failures.
- **The binding constraint is window freshness.** The primary surfaces (equity EOD 2010–2026,
  index 1m 2012–2026, equity 1m 2023–2026, futures EOD 2016–2026) are **signal-spent** under
  GR-1.3 — operator ruling **R-11** marks equity EOD 2023-01-02 → 2026-09-11 signal-spent, and
  2012–2022 was spent by PSB/Gann/MRLC/BKV. A fresh confirmatory read must therefore use a
  genuinely unread surface (REGISTER §5/§6: **India VIX 1m 2022→2026**, **India VIX EOD 2010→2025**,
  or the **unread 101 names of the vendor N100 1m store 2015–2022**), or a future window.

What remains unknown: whether a prior low-dispersion state carries information about **subsequent
expansion beyond the mechanical persistence of volatility** (the correct null), at which horizon, and
whether the family of compression definitions is one mechanism or several collinear proxies.

---

## 2. Existing Vault Coverage

### 2.1 The Vault's own verdict (MAP v1.1 §4, M4a row; CLOSE §4; LEDGER §8)

| Field | Value |
|---|---|
| MAP ID | **M4a** — Volatility compression → expansion |
| Economic hypothesis | Low realized range is followed by expansion, with direction resolved by the break |
| Vault evidence | Squeeze **15 name hits**; BB/Keltner squeeze subset of Band/channel (148 files) and Breakout/range (189 files) |
| Existing research (closest) | MSRP D1 (**B**, forecast-gated options); Gate-0 **F-VOL** (priced only, zero reads); DRA HMM (legacy); N200 HMM Variant B (vol-state → forward-vol event, **FAIL vs persistence**); GEX Stage A (positioning → next-day RV/IV) |
| Status | **C** — related research exists; the mechanism itself was not tested |
| Material gap (verbatim) | "All forecast the level or events of volatility, or price options. **None conditions a directional expansion trade in the underlying on compression.**" |
| Data available? | Yes |
| Eligible only if… (MAP §8) | "Compression-conditioned expansion in the underlying, not implied-vs-forecast vol or vol-level forecasting" |

LEDGER §7 (mechanism vs construct): M4a row — exact construct evidence **none**; closes construct —
**No**; closes mechanism — **No**. LEDGER §8: "M4a | C | C4 forecast-only (N200/GEX) | No directional
test exists | Partly (Gate 0 priced) | **Fully open**".

### 2.2 Why the Vault entry does not establish M4a

- The **Vault is a hypothesis menu, not evidence.** CENSUS: 91% PineScript on crypto perps, 96.7%
  evidence level **E2** (reproducible rule, screenshot-only result), **0** files with walk-forward /
  OOS (E3), **0** with forward records (E4). The "15 squeeze name hits" are indicator *vocabulary*
  inside MA/oscillator/band conjunction wrappers — the same keywords counted twice when a file
  matches ≥2 families (CENSUS §4). No Vault file measures compression-conditioned expansion.
- The mechanism is folded into MAP under Breakout/range + Band/channel, but the *mechanism itself* is
  "compression-conditioned expansion", which no mapped experiment runs.

### 2.3 What the Vault **did** establish (adjacent only)

The Band/channel family (Bollinger/Keltner) and the Breakout/range family are real coding patterns in
the Vault, but they are single-name intraday tactics with no cost model or OOS. Under CENSUS §8 they
are `RELATED`, not tested. **They do not close M4a.**

---

## 3. Existing Compression Constructs

Every construct the repo or Vault contains that touches compression / low-vol state, with the fields
requested. **None is a test of M4a.** The table distinguishes M4a-relevant from adjacent.

| # | Construct | Compression definition | Timeframe / universe / period | Sample | Outcome defined | TRAIN/VAL/HOLDOUT | Result | Closure | Genuine M4a? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **N200 HMM Variant B** (`N200_REGIME_CLOSURE.md`; design §10.1–10.2) | HMM on vol & vol-ratio features (GK, KER, drift), P(S₂) | Daily, N200 PIT, 2012–2023 | folds | Forward 5-day Garman–Klass RV in own trailing top tercile | folds; persistence baseline | **FAIL**: gate FAIL, skill vs persistence **−0.1835**, 0–3/10 folds positive | C5 (family closed) | **No** — forecasts the *volatility level/event*, no expansion conditioned on compression, no direction |
| 2 | **GEX Stage A** (`GEX_REGIME_STAGE_A_*`) | Dealer gamma exposure state | Daily index, TRAIN/HOLDOUT | regression | Next-day RV / IV (regression), `ln_rv5`/`ln_rv20` as controls | TRAIN t −3.20, HOLDOUT t −2.65 PASS | State variable confirmed | C4/C6 (state-only) | **No** — positioning → vol level; explicitly "controls, not an M4a test" (CLOSE §4) |
| 3 | **DRA HMM-gated EMA** (`DRA_TECHNICAL_DOSSIER.md`; SPEC §4) | HMM vol states incl. Expansion/Contraction labels | Intraday 15m, Nifty cash, walk-forward 2023–26 | 200 trades | Directional P&L | walk-forward (legacy) | −₹1,647, no significance test | C3 legacy | **No** — vol state is a *gate inside a trend rule*; compression is not the hypothesis, and the primary report is absent |
| 4 | **MSRP D1** (forecast-gated index straddle) | Forecast RV vs implied | Nifty weeklies, 2023–25 | in-sample | Options P&L | in-sample | ρ(signal, ret) −0.027; STOP | C4 in-sample STOP | **No** — prices an options payoff on an implied-vs-forecast gap |
| 5 | **Gate-0 F-VOL** (`STAGE_A_GATE0_REPORT.md`) | "volatility family" | — | **0 reads** | — | none | Priced infeasible only | C0 → **priced, not tested** (LEDGER §9.14) | **No** — arithmetic only |
| 6 | **PixityAI `expansion_v3`** (`docs/archive/CODEBASE_OVERVIEW.md` §1; `CLEANUP_AUDIT_REPORT_2026-03-13.md`) | Daily compression scanner + daily/hourly breakout triggers; `run_v3` (compression + 1H breakout), `run_v4` (compression + daily breakout), `run_v8` (15m OR compression) | Daily/1H/15m, prior repo universe | **none surviving** | Breakout P&L | none | **No reproducible result in this repo; code not ported** | Not in the Vault taxonomy; **not closure** | **Partly** — the closest thing to an M4a *implementation*, but unported and uncertified |
| 7 | **DayType / intraday compression cluster** (`INDEX_MICROSTRUCTURE_PROFILING.md` §125, §442–456) | Low day_range, high TWAP-cross count, low linreg R² → "Compression" cluster | Intraday Nifty, feature/cluster | KMeans clusters | Cluster membership; PM range p50 | feature | "Choppy signal = range compression", PM range 25% smaller | feature, not a test | **No** — a regime *classification feature*, no forward expansion outcome |
| 8 | **BKV-1** (M3a×M5b) | *(breakout, not compression)* prior-N closing range crossed with abnormal volume | Daily, PIT top-200, 2012–2022 | 36,828 events | Direction-signed market-excess continuation | TRAIN/VAL; HOLDOUT unread | VAL **0/8** confirmed | C5 construct-scoped | **No** — breakout continuation; compression is not an input. (Its **harness** is the reusable asset, §9.) |
| 9 | **RELIANCE Donchian** (`M2c/M3a`) | *(breakout, not compression)* close > prior N-day high | Daily, one name, long/flat | thin | net return | DEV/VAL/RECENT | +0.8 / +4.2 / −3.2 %; R1 voids IC | C4 single-name | **No** |
| 10 | **PSB-1 C5 / IVOL** | Cross-sectional **level** of low vol (σ(252d); 60-day idio vol) | Monthly SSF / N200, 2012–2022 | 131 / 59 | Forward cross-sectional return rank | TRAIN/HOLDOUT/SEALED | Power-drop / SEALED sign-flip | C4 / C5 | **No** — a cross-sectional *low-vol level* premium; not a compression→expansion transition, and not single-instrument |
| 11 | **Vault BB/Keltner squeeze files** (15 name hits) | Bandwidth squeeze indicated in prose/code | Crypto perps, ≤3-month windows | screenshots | unverifiable | none | none reproducible | E2, hypothesis only | **No** — not evidence |

**Conclusion for Phase 1.** No construct in the repo or Vault tests M4a. The nearest neighbours
(N200 HMM, GEX) test **volatility-level forecasting**; the nearest implementation (PixityAI
`expansion_v3`) is unported and uncertified; the Vault contributes only keyword counts. M4a is
correctly **C / fully open**, exactly as MAP and LEDGER state.

---

## 4. Data Availability

All figures read in this branch are **meta-level** (schema, counts, extents). No outcome was computed.

### 4.1 Daily

| Surface | Store | Span | Universe over time | Fields | CA / session handling |
|---|---|---|---|---|---|
| **Equity EOD** | `data/market_data/equity_bhavcopy.duckdb` → `equity_bhavcopy_adjusted` (+ `equity_bhavcopy` raw) | **2010-01-04 → 2026-09-29** (7,190,162 adj rows; 4,157 calendar sessions) | 1,520 (2010) → 2,969 (2026) symbols/yr | OHLC, prev_close, volume, turnover, deliv_qty, deliv_pct | entity-grain CA adjustment; `trading_calendar.n_symbols`; PIT `universe_membership` (`turnover_top200`, 177 monthly rebalances, 2012-01-31 → 2026-09-11); `symbol_entity_intervals` for ticker recycling |
| **Index EOD** | `data/market_data/nse/candles/1d/{date}.duckdb` | **2010-01-04 → 2026-09-29** (4,146 files) | **index-only** (Nifty 50, Nifty Bank, India VIX + ~140 other indices; 1 → 146 symbols) | OHLC, volume (index volume = 0) | start-labelled; `is_synthetic` flag; CAS-aware session module |
| **Futures EOD** | `data/market_data/futures_bhavcopy.duckdb` | **2016-02-11 → 2026-09-29** | 380 underlyings (363 stock + 13 index) | OHLC, settle, contracts, val, OI, chg_OI | per-contract; `fo_eligible_intervals`; `stock_futures_continuous` exists but only **2022-08-08 → 2025-07-17** (270 underlyings, 49,711 rows) — thin |
| **PIT index membership** | `data/isd/n200_membership.duckdb` (587), `n100_membership.duckdb` (263) | interval tables | official NSE MCWB PIT | symbol, valid_from/to | certified in CB-N50 substrate |

### 4.2 Intraday

| Surface | Store | Span | Universe | Notes |
|---|---|---|---|---|
| **Index 1m** | `data/market_data/nse/candles/1m/{date}.duckdb` | **2012-01-02 → 2026-09-29** (3,623 files) | Nifty 50, Nifty Bank (2012→); India VIX (2022→) | 375 bars/session; `is_synthetic` flag; only ~2–3 index symbols before 2023 |
| **Equity 1m** | same store | **2023-01-02 → present** | ~202 (2023) → 226 (2026) `NSE_EQ` names | ~375 bars/session; post-CAS carry-forward bars flagged `is_synthetic`; **must filter `is_synthetic = FALSE`** |
| **Vendor N100 1m** | `data/market_data/nse/candles/1m_vendor/{name}.duckdb` | **2015-02-02 → 2025-08-06** | **102 names** (Nifty-100); cols `ts, o,h,l,c, volume`; ~972k rows/file | Only `reliance.duckdb` is a recorded reader (REGISTER V-1). **The other 101 names are unenumerated / unread.** Provenance/uncertified — a substrate blocker, not a budget one |
| **India VIX 1m** | canonical store (Upstox backfill) | **2022-01-03 → 2026-09-11** (1,165 sessions) | India VIX | REGISTER **V-0b: NONE — unread**; value-verified 99.98%; defect V2 (90 sessions with bars past 15:30) |
| **India VIX EOD (vendor CSV)** | `data/market_data/India VIX Historical Data 101.csv` | **2010-01-04 → 2025-06-05** | India VIX | REGISTER **V-0c: NONE — unread**; overlap check not run |

### 4.3 Determinations asked for

- **Earliest reliable date.** Equity EOD **2012-01-02** for the certified PIT top-200 panel (BKV
  chose 2012, not 2010, because the 84-session eligibility lookback must clear the panel start).
  Index 1m 2012-01-02. Equity 1m 2023-01-02. Vendor 1m 2015-02-02.
- **Latest reliable date.** Equity EOD / index 1d / index 1m **2026-09-29** (store max). Vendor 1m
  **2025-08-06**. Post-CAS sessions (≥ 2026-08-03) require `is_synthetic = FALSE`.
- **Universe size over time.** Top-200 PIT is fixed by construction (monthly rebalance); raw equity
  universe grows 1,520 → 2,969. Index-1m is fixed at 2–3 names.
- **Fields without look-ahead.** OHLC/volume all known at the close of *t*; compression state uses
  ≤ *t* only; forward windows use *t+1..t+H*. No look-ahead is required.
- **Corporate-action adequacy.** `equity_bhavcopy_adjusted` is certified by the PSB-1 four-arm
  contract suite (entity-grain, time-aware, ISIN-prefix linkage). **Do not join 1m to bhavcopy
  across a CA** (different bases).
- **Session/calendar adequacy.** `core/market/session_schedule.py` (era + `SPECIAL_SESSIONS`),
  `core/market/nse_holidays.py`, `core/market/bar_labeling.py`, `trading_calendar`. BKV's rule-based
  regular-session filter (n_symbols ≥ 200 ∧ turnover ≥ 0.40 × centred 21-session median) is reusable.

### 4.4 Outcome-free event inventory (this branch)

Computed on `data/research/breakout_volume/panel_dev.parquet` (already hashed by BKV-1; 1,341,582
rows, 508 entities, 2010-01-04 → 2022-12-30). State = trailing-percentile of `RV10/RV60`; **no
forward quantity computed**.

| Compression rule | Name-days in state | Onset events | Events/yr (approx) | Entities with ≥1 | Mean run length |
|---|---|---|---|---|---|
| RV10/RV60 trailing-pctile ≤ q15 | 14.3% of rows | 18,109 | ~1,300–1,650 | 506 | 5.5 sessions |
| RV10/RV60 trailing-pctile ≤ q20 | 19.0% | 18,264 | ~1,500 | 506 | 5.5 |
| RV10/RV60 trailing-pctile ≤ q25 | 23.8% | 17,531 | ~1,500 | 506 | 5.5 |
| ATR14/ATR60 trailing-pctile ≤ q20 | 18.9% | (not onset-filtered) | — | — | — |

Cross-sectional clustering: **median 80 names in compression on a given day** (p90 = 144, max = 268);
essentially every session carries ≥1 name in compression. This is why the estimand must be
**cohort-by-date**, exactly as BKV-1 (else cross-sectional dependence is counted as n).

---

## 5. Candidate Mechanism Definitions

Keep the family **small and collinear-aware**. All four candidates are functions of the same
underlying quantity — *past realized dispersion* — so they will be highly correlated. Treat them as
one mechanism with one **primary** definition and at most one or two declared robustness variants;
**do not fish across them.**

Let *Cₜ* = close, *Hₜ* / *Lₜ* = high/low, *rₜ* = ln(Cₜ/Cₜ₋₁), at session *t*.

| ID | Compression state (all ≤ t) | Expansion outcome (natural) | Why it is M4a | Principal confound | Measurable at t? |
|---|---|---|---|---|---|
| **D1 — Realized-vol contraction** *(primary candidate)* | trailing percentile of `RV_short/RV_long`, e.g. `std(r,10)/std(r,60)`; state = percentile ≤ q (trailing 252) | forward realized vol / range | Directly encodes "quiet → not quiet" | Volatility persistence; the *ratio* can fall because long-vol rose | Yes (past window) |
| **D2 — Range/ATR contraction** | trailing percentile of `ATR_short/ATR_long`, `ATR_n = mean((H−L)/Cₜ₋₁, n)` | forward mean/realized range | Range is the most robust, thin-tail statistic; Vault uses ATR (M13) | Same; range is positively skewed | Yes |
| **D3 — Band-width contraction** | trailing percentile of Bollinger bandwidth `BBW = 4·std(C,20)/mean(C,20)` | forward range / vol | The *named* Vault precedent ("BB/Keltner squeeze", 15 name hits) | Collinear with D1/D2; `mean(C,20)` level drift | Yes |
| **D4 — Narrow-range count (NR7 / inside-bar count)** | count of the last *N* sessions that are the narrowest of the last *k* (NR7), or inside-bar count | forward range / vol | Classic "narrow range" formulation (Vault pattern/price-action) | Weaker repo precedent; discrete and unstable near ties | Yes |

**Why not more.** D1–D3 differ only in the dispersion estimator; D4 is a discretization. The repo's
own precedent for *how* to normalize is **relative-to-own-history** (N200 HMM uses trailing
percentiles; PSB/IVOL use trailing vol) rather than a fixed ratio threshold. So the defensible primary
is a **trailing-percentile** state, and the experiment should pin **one** estimator (recommend **D2
range/ATR**, because range needs no mean-drift assumption and is the least fragile on thin names) with
**D1** as the single declared robustness variant.

**What compression is NOT.** It is not "low price level"; it is not "low volume" (M5b); it is not a
breakout (M3a); it is not the level of the VIX. Keeping these separate is required by the task.

---

## 6. Outcome Definitions

Keep the three outcomes **separate** (task §Phase 4). For each, the forward quantity is measured over
*t+1 … t+H* and compared to that name's own trailing baseline (strictly ≤ *t*).

| Outcome | Definition | What it answers |
|---|---|---|
| **A. Range expansion** | `E^range = mean_{t+1..t+H} (H−L)/Cₜ₋₁  /  trailing median of same (252d, ≤ t)` | does compression precede a wider range? |
| **B. Realized-vol expansion** | `E^vol = sqrt(mean_{t+1..t+H} r²) / trailing same (252d, ≤ t)` (or Garman–Klass) | does compression precede higher realized vol? |
| **C. Directional movement** | (i) **magnitude** `|Σ r|` (or `|C_{t+H}/C_{t+1}−1|`) — symmetric expansion; (ii) **signed** `Σ r` — direction | (i) is still M4a; (ii) is a **different** question |

**The distinction the task demands, made explicit:**

- **"Compression predicts expansion"** is the **M4a mechanism question**. Its estimand compares a
  forward *dispersion* outcome (A, B, or C-i) after a compression state against the correct benchmark.
  It is symmetric in direction by construction.
- **"Compression predicts profitable direction"** is a **strategy** question. A signed return (C-ii)
  is reported **descriptively only**; it is not the primary estimand and cannot carry the M4a label.
  Direction, if it matters, is "resolved by the break" — which is M3a, tested separately (BKV-1).

**The correct null for M4a.** Because volatility clusters, "compression today → higher vol tomorrow"
is partly mechanical. The benchmark is **not zero**; it is the **persistence baseline**: the same
forward-expansion statistic conditioned on the *complementary* state (normal/high dispersion), or the
name's unconditional forward expansion. N200 HMM used exactly this benchmark (skill vs persistence)
and it is what killed that variant. An M4a result that does not beat persistence is no result.

---

## 7. Statistical Feasibility

**The demonstrability wall that killed C5/C4/F1 does not bind here.** Those constructs had ~130
monthly (or ≤10-name) formations. Compression onsets are **abundant**: ~1,500/yr on a 200-name PIT
panel (≈ 7 per name-year), 18k+ events over 2010–2022, on essentially every trading session.

| Quantity | Estimate | Basis |
|---|---|---|
| Event count, TRAIN 2012–2017 | ≈ 8,000–9,000 onsets | 6 yr × ~1,500 |
| Event count, VAL 2018–2022 | ≈ 7,300–8,000 onsets | 5 yr × ~1,500 |
| Independent formation **dates** | ~250 sub-sampled / ~1,233 VAL sessions | cohort-by-date |
| Cross-sectional dependence | median 80 names/day in state | §4.4 — must use cohort-by-date |
| Event overlap (same name) | mean run 5.5 sessions | onset + 20-session quiet removes most overlap |
| Effective n for HAC | ≈ #formation dates (not #events) | NW lag = H |

**Plausible effect size.** The M4a literature/mechanism gives no defensible point estimate ex ante.
That is acceptable because the question is directional ("does compression contain *any* information"),
and the experiment is a **within-panel contrast**, not an RFA power problem. Using the repo's own
power machinery (`scripts/rfa/power.py`: `ncp = δ√n / sd`), for a cohort-by-date contrast with
n ≈ 1,200 VAL formation dates:
- if the per-date sd of the expansion contrast is ~0.5 (in units of the trailing baseline),
  the MDE at 80% power, one-sided α = 0.05 is `(z₀.₉₅+z₀.₈₀)·sd/√n ≈ 2.49·0.5/34.6 ≈ 0.036`
  — i.e. ~3.6% relative expansion. That is a small effect, detectable.
- if sd ≈ 2.0 (highly noisy thin names), MDE ≈ 0.14 — still detectable, and the wide-CI case is
  reported as a limitation, not a kill.

**Multiple-testing burden is small.** A defensible primary family is **2 states (compression vs
baseline) × 2 horizons (H = 5, 20) = 4 cells**, Holm-adjusted — not the 8+ of BKV and nothing like a
threshold grid. One declared robustness variant (D1) is disclosure only. **No threshold search.**

**RFA.** Per the BKV precedent ("No RFA is created — the frozen process did not require one for this
construct; the study reports the MDE instead"), M4a does **not** require an RFA to proceed; the
existing RFA metrics (`per_trade_pnl`, `rank_ic`) do not cleanly express a within-panel
compression→expansion contrast, and forcing one would mis-specify the mechanism. Report the MDE per
cell instead. **Do not use the RFA to kill the mechanism because a guessed effect size is small.**

---

## 8. Confounds / Failure Modes

1. **Mechanical persistence (the dominant confound).** Forward vol is positively autocorrelated with
   current vol; a compression→expansion result vs a *zero* null is nearly tautological. **Mandatory
   control:** the persistence benchmark (§6), and reporting complement-state expansion alongside.
2. **Regression to the mean of the statistic itself.** Conditioning on a low trailing percentile of a
   dispersion estimator partly guarantees the forward value exceeds that low value. Comparing against
   the *name's own trailing median* (not against the compressed value) reduces, but does not
   eliminate, this. Prefer an **out-of-state comparison** (compression cohort vs normal cohort on the
   same date) as the primary estimand.
3. **Direction is not implied.** A symmetric expansion finding says nothing about sign. Any signed
   result is descriptive and belongs to the M3a/M2c family, not M4a.
4. **Overlapping windows.** H-day forward windows overlap across H−1 consecutive dates → HAC
   (Newey–West) with **lag = H**, pre-specified (BKV §7.3).
5. **Cross-sectional clustering.** 80 names in state per day → cohort-by-date observation, never
   event-pooled as independent (BKV §7.1).
6. **Look-ahead in the percentile.** The state percentile must use a **trailing** window ending at
   *t*; a centred or full-sample percentile leaks the answer.
7. **Corporate-action basis.** Use only `equity_bhavcopy_adjusted`; never join 1m to bhavcopy across
   a CA. The BKV panel already handles this.
8. **Short / special sessions.** Reuse BKV's rule-based regular-session filter; CAS-era synthetic
   bars (`is_synthetic = TRUE`) must be excluded; index carries volume = 0 (never use volume on
   index).
9. **Universe survivorship / membership look-ahead.** PIT membership on the last rebalance strictly
   before *t* (BKV §4).
10. **Threshold/definition selection.** The family must be pinned at freeze; post-primary variants are
    disclosure only (BKV §13).
11. **Era heterogeneity.** CAS (2026-08-03) changed the intraday session; any intraday M4a must be
    era-aware. Daily closes are unaffected (the auction print equals the bhavcopy close 92–95%,
    CLAUDE.md).
12. **Index-1m window is signal-spent** (REGISTER I-1…I-8); an index M4a test on 2012–2022 cannot be
    confirmatory.

---

## 9. Recommended First Experiment

**One experiment. Answer the mechanism question only.** Reuse BKV-1's harness wherever possible.

### 9.1 Specification

| Element | Value |
|---|---|
| **Question** | Does a low trailing realized-dispersion state contain information about subsequent range/volatility expansion, **beyond volatility persistence**? |
| **Primary compression definition** | **D2 (range/ATR contraction)**: `ATR_fast(t)/ATR_slow(t)`, `ATR_n(t)=mean((H−L)/Cₜ₋₁, n)`, trailing-percentile (`≤` q0.20 of the last 252 sessions, ending at *t*). Declared robustness variant: D1 (`RV10/RV60`, same percentile). |
| **Primary expansion outcome** | **A. Range expansion** over H: `E^range(t,H) = mean_{t+1..t+H}((H−L)/Cₜ₋₁) / trailing_median_252(≤t)`. Secondary (declared): B. realized vol; C-i. absolute return. |
| **Timeframe** | Daily (sessions). |
| **Universe** | PIT top-200 by trailing-6-month median turnover (reuse BKV `universe_membership`, entity-grain). Single universe, no alternatives. |
| **PIT treatment** | Membership on session *t* = members of the last rebalance **strictly before *t***; delisted names included while listed; recycled tickers via `symbol_entity_intervals` (all inherited from BKV §4). |
| **Stages** | TRAIN **2012-01-02 → 2017-12-29** (descriptive); VAL **2018-01-01 → 2022-12-30** (consistency); HOLDOUT **only if a genuinely fresh surface is authorised** (see 9.4). |
| **Event eligibility** | Valid rows on every session `t−max(slow,252)−1 … t` (one uniform requirement) **and** PIT member at *t*. |
| **Onset / non-overlap** | Event = compression state at *t* with **no compression state in the prior `max(H,20)` sessions** (declusters same-name overlap). Symmetric "normal-state" cohort = not-in-state, same eligibility, used as the primary benchmark. |
| **Look-ahead protections** | All statistics use ≤ *t*; entry convention irrelevant (no trade), outcome begins at *t+1*; trailing percentiles only; a causality unit test perturbs data after *t* and shows the state unchanged (BKV `test_signal_is_causal`). |
| **Primary estimand** | Cohort-by-date contrast `d(t) = mean_fast_cohort(E) − mean_normal_cohort(E)` on dates with both arms; `d̄ = mean d(t)`; **one-sided t (H1: d̄ > 0)** with calendar-aware Newey–West lag **L = H**. |
| **Secondary diagnostics** | (i) expansion after compression vs **persistence baseline** (forward expansion after high state); (ii) D1 variant; (iii) H ∈ {5, 20}; (iv) event-weighted contrast; (v) within-date permutation p and block-bootstrap CI (report-only); (vi) by-year stability; (vii) signed return (descriptive, non-classifying). |
| **Multiple testing** | **Holm over 4 primary cells** (D2 × {H=5,20} × {vs-normal, vs-persistence}); α = 0.05 one-sided. Variants are disclosure only. |
| **Cost treatment** | **None.** The mechanism question has no tradeable expression. If a directional arm is ever added, it is a **separate pre-registration** and uses BKV's delivery-fee + κ methodology. |
| **Stopping / closure rule** | If VAL confirms no cell → **STOP**: no HOLDOUT read, no re-specification, no second estimator/horizon. Category **C5, construct-scoped** (M4a stays open). If VAL confirms and a fresh HOLDOUT surface is authorised → one-shot HOLDOUT, Holm over confirmed cells; a failed HOLDOUT is **C5, never C6** (LEDGER precedent: IVOL, Analog, VWAP). |

### 9.2 What is reusable today (identify, do not rebuild)

| Need | Existing asset |
|---|---|
| Hashed PIT top-200 daily panel (entity-grain, CA-adjusted, calendar) | `scripts/breakout_vol/prep.py` + `data/research/breakout_volume/panel_dev.parquet` |
| Calendar-aware Newey–West, two-way cluster, within-date permutation, block bootstrap, Holm, MDE | `scripts/breakout_vol/stats.py` and `scripts/vwap_rev/stats.py` |
| Stage runner, freeze/hash gate, classification C4–C9, independent SQL verifier, leakage audit | `scripts/breakout_vol/{run_stage,freeze,classify,verify_independent}.py` |
| Realized-vol utility (1m → annualized RV) | `core/analytics/realized_vol.py` |
| Session/CAS/holiday handling | `core/market/{session_schedule,nse_holidays,bar_labeling,trading_calendar}.py` |
| Test scaffolding (synthetic end-to-end, governance, causal) | `tests/breakout_vol/` |

### 9.3 Smallest required additions (research only; not built here)

1. A **compression-state module** (`state.py`) — one pure function per D1/D2, trailing-percentile,
   with a causality unit test.
2. A **forward-expansion outcome module** (`outcome.py`) — `E^range`, `E^vol`, `|return|`, computed
   from `t+1..t+H`, using only the trailing baseline.
3. A **diagnostics/outcome-free** entry point (event counts, cluster sizes, run lengths) mirroring
   `breakout_vol/diagnostics.py`, run before freeze.
4. **A window decision** (9.4) — operator input, not code.

### 9.4 The window decision (the only real blocker)

Per **GR-1.3**, TRAIN and VAL above are **already signal-spent** and can be **consistency checks
only**; they cannot be confirmatory. Choose one:

- **(a) Non-confirmatory characterization (permitted now).** Run the design on TRAIN+VAL, label it
  **GR-1.4 non-confirmatory**, feed no gate. Buys a clean answer to "is there anything here?" without
  spending a fresh window. **Recommended first step.**
- **(b) Fresh confirmatory read on an unread surface.** The only genuinely unread candidates
  (REGISTER §5/§6) are **India VIX 1m 2022→2026** (V-0b), **India VIX EOD 2010→2025** (V-0c), and the
  **101 unread vendor-N100 1m names 2015–2022** (V-1 covers only Reliance). Each needs an operator
  register row **before** the read; the vendor store also needs provenance/certification.
- **(c) Wait for a future window** (e.g. equity EOD after the current spent span) — the cleanest
  confirmatory path but slowest.

This document authorizes none of (a)–(c); it states the options so the operator can pick.

---

## 10. Exact Freeze Specification

If the operator proceeds beyond design, the freeze must pin, before any outcome exists (mirroring
BKV-1 §1–§16):

1. **Construct + question** as in §9.1, verbatim.
2. **Hashes** of the input snapshot (TRAIN/VAL, ≤ 2022-12-30) and of the state/outcome/engine code;
   a `FREEZE.json` with SHA-256 over protocol + modules + snapshot (BKV pattern).
3. **Pinned parameters** — slow = 60, percentile window = 252, q = 0.20, H ∈ {5, 20}, quiet = 20,
   universe = PIT top-200, calendar rule, min benchmark names = 100, α = 0.05, NW lag = H, seeds.
   **No parameter is pinned or changed on TRAIN.**
4. **Primary family = 4 cells** (D2 × {H=5,20} × {vs-normal, vs-persistence}); Holm; everything else
   report-only.
5. **Outcome-free diagnostics** run and hashed before freeze (event counts, cluster sizes, run
   lengths) — reproduces §4.4.
6. **Independent verification** — pure-SQL re-derivation of every event, state, outcome and the NW
   statistic; accounting identities; a disagreement STOPs the run (BKV §11).
7. **Leakage/bias audit** — the §8 table, each row with a control and an evidence pointer.
8. **Classification mapping** — the LEDGER C4–C9 vocabulary, mapped before any result; a failed
   HOLDOUT after a VAL pass is C5, not C6; every category quoted **"construct-scoped"**.
9. **Refused rescues** — no post-hoc change of estimator, percentile, horizon, universe, weighting or
   event definition; no second HOLDOUT read; no promotion of a variant, subgroup or single year.
10. **Reproducibility** — deterministic from hashed snapshot; re-run reproduces byte-for-byte.

---

## 11. Open Questions

1. **Does compression predict expansion beyond persistence?** The single question the first
   experiment answers. N200 HMM already failed the analogous persistence test for vol-level, so this
   is a live risk, not a formality.
2. **Is the effect cross-sectional or concentrated?** Median 80 names/day in state → a pooled result
   could be driven by a few days (2020 COVID, 2022). Require by-year and concentration diagnostics.
3. **One mechanism or several?** D1–D3 are collinear; the experiment should show whether the choice of
   estimator changes the answer, without becoming a grid.
4. **Is direction resolved by the break (M3a) or symmetric?** Out of scope for M4a; only relevant if a
   later pre-registration combines M4a with M3a.
5. **Daily vs intraday?** Compression→expansion may be stronger intraday, but equity 1m starts 2023
   and index 1m is spent; intraday would need the vendor store or a forward window.
6. **Fresh window.** Which of VIX-1m, VIX-EOD, vendor-N100, or a future window is the confirmatory
   surface — and is the vendor store certifiable?
7. **Does the options surface corroborate?** If compression truly predicts realized expansion, forward
   IV/RV gaps should widen after compression. This is an **M8b-adjacent** cross-check, not M4a itself.
8. **Vault squeeze files.** Do the 15 Vault squeeze files contain any *specification* worth borrowing
   (e.g. a particular bandwidth normalization), without importing them as evidence? Likely no, but
   unexamined.

---

## 12. Explicit Recommendation

### **PROCEED** — as a smallest-defensible mechanism test, conditioned on the window decision.

Justification, in the Vault's own terms:

- **Not INFEASIBLE.** The mechanism is mechanically specifiable from information at *t*; the data
  exists; events are abundant; the harness is largely built and certified.
- **Not DEFER.** There is nothing arbitrary left to invent — the compression family is small, grounded
  in Vault vocabulary (squeeze/bandwidth) and repo precedent (trailing-vol percentiles), and the
  outcome definitions follow directly. Deferring would only re-litigate what this document settles.
- **PROCEED, with two honest qualifications:**
  1. **The confirmatory window is scarce.** Every primary surface is signal-spent (GR-1.3; R-11). The
     first experiment should therefore run as a **GR-1.4 non-confirmatory characterization** on
     TRAIN+VAL, with a confirmatory HOLDOUT only on a genuinely unread surface chosen by the operator
     before the read (§9.4). This is a budget constraint, not a mechanism defect.
  2. **The persistence benchmark is binding.** N200 HMM Variant B already failed to beat volatility
     persistence. An M4a result that does not beat persistence is a null, and must be reported as
     such.

**Explicitly not done and not sanctioned here:** no strategy, no parameter optimisation, no
threshold grid, no instrument cherry-picking, no holdout read, no BKV-1 revival, no Vault taxonomy
change, no architecture redesign, no RFA filed, no framework.

**One-line hand-off.** *M4a is fully open (MAP/LEDGER C), cleanly specifiable, data-rich, and
untested; the only real constraint is that the confirmatory window is spent, so run it as a
non-confirmatory characterization first and reserve a fresh surface for confirmation.*

---

## Provenance / reproducibility of this inventory

- **Branch:** `research/m4a-compression-expansion`, cut from `main` `d79a278`; no code committed.
- **Reads performed:** documents only, plus an **outcome-free** count on the already-hashed BKV dev
  panel (`data/research/breakout_volume/panel_dev.parquet`). No forward return, range or volatility
  was computed; no signal-level window was spent; no holdout touched.
- **Outcome-free probe:** `C:\Users\devou\AppData\Local\Temp\opencode\m4a_counts.py` (not committed;
  reproducible from the hashed panel).
- **Vault status:** M4a remains **C**; nothing in this document changes the MAP, CLOSE, or LEDGER.
