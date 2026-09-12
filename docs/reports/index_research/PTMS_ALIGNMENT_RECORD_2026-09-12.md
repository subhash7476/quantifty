# PTMS — Price × Time × Market-Structure Research: Alignment Record

**Date:** 2026-09-12
**Artifact class:** alignment record. **This memo authorizes nothing** — no construct
code, no RFA declaration, no data read, no window spend. It states my understanding
of the charter, corrects two facts in it, and proposes an architecture for the
operator to accept, amend, or reject.
**Inputs:** operator charter (this session) · `docs/DATA_STORE_MAP.md` §9 ·
`A_INDEX_INTRADAY_PRIOR_EXPOSURE_AUDIT.md` · `A_HOLDOUT_CLOSURE.md` ·
`ISD_BATTERY_TRAIN_REPORT.md` · `ISD_PROGRAM_REASSESSMENT.md` ·
`CB_N50_HOLDOUT_REPORT.md` · `RS_MOM_RFA.md` · `CLAUDE.md` RFA section.
**Verified this session:** per-file distinct-symbol scan of the 1m store;
`data/isd/pit_universe.duckdb` row/range check.

---

## 0. Two corrections to the charter, stated first

### C1 — Broad equity 1m breadth starts **2023-01-02**, not 2024-10-17

The charter's §4 and this repo's own `DATA_STORE_MAP.md` §9 both say the 1m store
holds only `NSE_INDEX|Nifty 50` and `NSE_INDEX|Nifty Bank` until 2024-10-16, with
breadth beginning 2024-10-17. **Both are wrong.** Method: open every 1m file in
2022-12 → 2023-09 and report `count(distinct symbol)` where it changes.

```
CHANGE at 2023-01-02.duckdb    2 -> 190      # 188 NSE_EQ + 2 NSE_INDEX
CHANGE at 2023-05-09.duckdb  190 -> 191
CHANGE at 2023-09-26.duckdb  192 -> 193
2024-06-14: 195 syms (193 EQ) · 2025-06-16: 198 syms (196 EQ)
```

First-file-of-year scan confirms the step is exactly at the year boundary: every
first file 2012→2022 has 2 symbols; 2023-01-02 has 190. Corroborated independently
by `data/isd/pit_universe.duckdb:pit_membership` — 173,900 rows, **898 sessions,
2023-01-02 → 2026-08-24** — and by the ISD battery's own 474-session TRAIN starting
2023-01-02.

**Consequence:** the cross-sectional intraday panel is ~900 sessions, not ~230. A
TRAIN/HOLDOUT/SEALED split on it is arithmetically possible. That is a materially
more generous picture than the charter assumes — which is precisely why C2 matters.

### C2 — That window, and the index 1m window, are already heavily spent

The charter's §13 treats prior research as a *source of candidate signals*. It never
treats it as *consumed statistical budget*. That is the largest gap in the charter,
because Research Family 1 as proposed starts exactly where this repo has already spent.

| Surface | Span | Consumed by | Exposure class |
|---|---|---|---|
| Index 1m (Nifty 50 + Bank) | 2012-01-04 → 2025-12-31 | `scripts/build_intraday_features.py` (daytype) — 53 features incl. partial returns, TWAP, range, CLV, linreg slope, realized vol, Bank intermarket block | **Feature-level, whole span, both indices** |
| Index 1m | 2023-01 → ~2026-05 (844 sessions) | Nifty/Bank pair research — ratio z-scores, 27 intraday mean-reversion parameter combos, all net-negative; byproduct: intraday ratio **trends** (+1.10/+1.17) | **Signal-level (trading-rule evaluation)** |
| Nifty futures intraday, opening-drive continuation | TRAIN 2012–2018 / HOLDOUT 2019–2022 | **A-INDEX-INTRADAY** — RFA PROCEED (0.8720) → TRAIN PASS (+1.27 bp net) → **HOLDOUT FAIL** (−0.22 bp). Closed 2026-08-27, no successor authorized | **Signal-level, gated, terminal** |
| Equity breadth 1m (~190 names) | 2023-01-02 → 2024-11-30 (474 sessions) | **ISD battery** — F1 opening-drive (TRAIN sign negative → family closed); F4 overnight gap (IC −0.0289, NW t −6.09, p 0.0000, **net −3196 bp**) | **Signal-level, gated, terminal** |
| Nifty 50 daily cross-section (50 names) | TRAIN 2016–2019, HOLDOUT 2020–2022 | **CB-N50** — TRAIN IC +0.059, HOLDOUT IC +0.029; momentum dropped (daily momentum *is* reversal) | **Signal-level, gated** |

**Unresolved tension the operator must rule on before any successor claims a fresh
window.** `A_HOLDOUT_CLOSURE.md` asserts index-1m SEALED (2023-01-01 → present, 873
sessions) is "untouched." `A_INDEX_INTRADAY_PRIOR_EXPOSURE_AUDIT.md` §3 classifies
the pair research's read of **that same window** as *signal-level*. Both are in the
repo; they cannot both be load-bearing. I do not inherit A's framing.

---

## 1. My understanding of the actual objective

We are building a **falsifiable measurement apparatus**, not a strategy. Its output
is a verdict — including, legitimately, "no information here" — about whether price,
time, price×time geometry, cross-market structure, and derivatives/market-state data
carry *genuine, out-of-sample, incremental, economically survivable* predictive
information about future market behavior.

Four words carry the weight:

- **Genuine** — survives a pre-registered specification frozen before the confirmatory
  read, with multiplicity accounted, against an explicit null.
- **Out-of-sample** — measured on a window that was unread when the specification froze.
  Per C2, that is the scarcest resource this project owns.
- **Incremental** — adds information *after* controlling for what is already known.
  `A` vs `A+B`, not `B` in isolation.
- **Economically survivable** — clears era-accurate costs at the executable horizon.
  This repo has now killed constructs on fees (PSB), on demonstrability (C5/C4/F1),
  and on **book-level economics despite a demonstrated effect** (ISD F4: the strongest
  |t| ever measured here, −3196 bp net). All three are live failure modes.

Gann is one hypothesis family inside this, on equal footing with the others and
entitled to no special treatment. The most likely single outcome — and a successful
one — is a documented null.

## 2. The three things that must not be conflated

| | **Gann strategy** | **Price-Time research** | **Multi-signal AI system** |
|---|---|---|---|
| Epistemic status | Asserted method; truth presumed | Hypothesis family under test | Combination *mechanism* |
| Primitive | A rule that trades | A measurable quantity + a null | A function over frozen inputs |
| Free parameters | Chosen to fit the chart | Enumerated and **counted as multiplicity** before the read | Selected under nested OOS |
| Origin / scale | Picked in hindsight, visually | Deterministic PIT function of prior data; the set of admissible rules counts toward *m* | N/A |
| Success | "It lined up" | Effect survives freeze → HOLDOUT → cost → robustness | HOLDOUT improvement over best single input |
| Failure | Not defined | Defined before the run | Defined before the run |
| Can create alpha? | Claims yes | Measures whether any exists | **No.** It can only recombine information already present |

The practical distinctions:

- **Gann strategy → Price-Time research** is the conversion of an unfalsifiable visual
  practice into a quantity with units, a null, and a stated failure criterion. The
  charter's §10C demand — *specify the price and time scale mathematically before
  evaluation* — is the whole conversion in one sentence. A "45° angle" is a statement
  about pixels unless the price-unit and time-unit are pinned; and **the set of
  admissible normalizations is itself the multiplicity surface** (see §7, L5).
- **Multi-signal AI → combination layer.** The reference claim ("price-only X%,
  +sentiment Y%") is not reproducible here and is not accepted. ML enters only after
  its inputs are individually frozen and validated; it is a combiner, never a source.
  Portfolio optimization likewise improves *implementation* of a real signal and
  cannot manufacture one.

## 3. The research hierarchy I propose we follow

The charter's §3 chain is right but has no power pre-check and no budget accounting.
Two insertions:

```
DATA  →  HYPOTHESIS  →  PRECISE DEFINITION
   →  [NEW] PRIOR-EXPOSURE / BUDGET DECLARATION
   →  [NEW] RFA POWER PRE-CHECK          ← free, reads no data, ABANDON is dispositive
   →  PRE-REGISTRATION FREEZE (SHA-256 over the spec)
   →  DISCOVERY / TRAIN
   →  HOLDOUT
   →  COSTS / EXECUTABILITY
   →  ROBUSTNESS
   →  INCREMENTAL INFORMATION
   →  (optional) SEALED one-shot
   →  ONLY THEN COMBINATION / PORTFOLIO / EXECUTION
```

**Why RFA before construct code.** `scripts/rfa/gate.py` asks one question: given the
formations actually available and an *independently defended* effect-size band, can
this construct reach power 0.80 even under assumptions more generous than anyone
believes? It reads no market data, so it is free. ABANDON is dispositive; **PROCEED
means only "not provably infeasible"** — never authorization, and never a statement
about fees or drawdown. It has one live kill to its name (FLOW, max power 0.6053) and
one structural result this project must inherit (§7, L5).

**Why budget declaration before RFA.** The RFA's `n_available` is a lie if the window
it counts has already been read. C2 is the evidence that this is not hypothetical.

**Standing correction carried forward** (`CLAUDE.md`, RFA section): the gate's verdict
is only as good as the declared SD/Sharpe band, which must be *independently defended*,
never inherited from a short in-sample read. C2 (the PSB-2 candidate) died precisely on
an SD that did not survive re-estimation; CB-N50's hand-off says to anchor on its
**HOLDOUT +0.029**, not its TRAIN +0.059.

## 4. Datasets available and relevant to the first phase

Canonical only. Paths are exact; ranges are as recorded in `DATA_STORE_MAP.md` plus
this session's checks.

### Price

| Store | Grain / span | Role in Phase 1 |
|---|---|---|
| `data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb` | `candles(symbol, timeframe, timestamp, OHLC, volume, is_synthetic)`; **2 index symbols 2012-01-02 → 2022-12-30; ~190→198 symbols (188→196 `NSE_EQ`) from 2023-01-02** | The only intraday substrate. Two distinct regimes — treat as two datasets, never one |
| `data/market_data/nse/candles/1d/{date}.duckdb` | per-date daily candles; **149 NSE index symbols** incl. sector/thematic, 2016→; Nifty 50 back to 2012-02-21 | Daily index / cross-index layer |
| `data/market_data/equity_bhavcopy.duckdb` | `equity_bhavcopy` 7.16M rows, 2010-01-04→; `equity_bhavcopy_adjusted` VIEW; `corporate_actions`, `adjustment_factors`, `trading_calendar`, `symbol_entity_intervals`, `symbol_isin`, `universe_*` | Daily equity panel + **all PIT machinery** |
| `data/market_data/futures_bhavcopy.duckdb` | `futures_bhavcopy` 1.496M, 2016-02-11→; `stock_futures_continuous` (**2022-08-08 → 2025-07-17 only**); `fo_eligible_intervals` | Basis / futures layer |

### Time

| Store | Content |
|---|---|
| `equity_bhavcopy.duckdb:trading_calendar` | 4,138 sessions, 2010→ — the session oracle |
| `core/market/session_schedule.py` | date-keyed, segment-named windows; `CAS_EFFECTIVE 2026-08-03` |
| `core/market/nse_holidays.py` | forward calendar — required to count past the last *stored* date |

1m `timestamp` = **bar open, IST-naive**. Verified 2020-01-02: 09:16 → 15:30, 375
bars/symbol. 1d `timestamp` = 00:00 naive.

### Cross-market

`1d/{date}.duckdb` (149 index symbols, daily, 2016→) · `futures_bhavcopy` FUTIDX
(`NIFTY`, `BANKNIFTY`) · `data/reference/mcwb_*.zip` (monthly PIT weights).
**Intraday cross-market is Nifty 50 ↔ Nifty Bank only** before 2023.

### Derivatives / market state

`options_bhavcopy.duckdb` (`option_bhavcopy` 5.49M, index, 2016-02-11 → **2026-07-17**) ·
`stock_options_bhavcopy.duckdb` (99.5M, 2016-02-11→) · EOD `open_int` / `chg_in_oi` ·
`NSE_INDEX|India VIX` (1d 2015→, 1m 2023-01-02→) · `equity_bhavcopy.deliv_qty/deliv_pct`.

### PIT / integrity

`symbol_entity_intervals` · `symbol_isin` · `adjustment_factors` (apply causally,
ex-date-gated) · `universe_membership` · `data/isd/pit_universe.duckdb:pit_membership`
(898 sessions, 2023-01-02 → 2026-08-24; `intraday_present` + `fno_member`) ·
`fo_eligible_intervals` · `data/cas/cas_category.duckdb`.

**Do not use** `nifty200_current.csv` or `config.db:fo_stocks` as historical universes —
the store map names both as time-travel sources.

## 5. The historical-data limitations that bind

1. **Two intraday regimes, not one.** 2012 → 2022-12-30 is a **two-symbol index pair**.
   2023-01-02 → present is a ~190-name cross-section. Any construct spanning the
   boundary changes its own universe mid-sample.
2. **The cross-section is ~3.7 years and one macro regime**, and a majority of it is
   already read (C2). It is split-capable in arithmetic and budget-poor in fact.
3. **No intraday option-chain history.** No historical intraday OI, IV, Greeks, bid/ask,
   PCR or GEX. `chain_cache.duckdb` is 360 rows; `wall_chain_snapshots/` is 6 days.
   Tick `bid`/`ask` columns exist and are **NULL**. An intraday derivatives battery
   cannot be built.
4. **No sentiment/text store.** Proxies (VIX, delivery %, EOD OI) are not news sentiment.
   The infographic's "price + sentiment → 80–90%" claim is not reproducible here.
5. **No FX, commodities, bonds, or global indices.** The MCX packet in
   `fetch_intermarket_data.py` is unused.
6. **BSE/SENSEX 1m begins 2026-08-24** — 15 files. Unusable for any split.
7. **Sector indices are 1d-only from 2016**, and **sector membership is not PIT-tabled**.
8. **Continuous futures exist only 2022-08-08 → 2025-07-17.** No rolled series before 2022.
9. **Index options stall 2026-07-17**; stock options run to present. Do not join them
   naively across that boundary.
10. **Known 1m gaps:** ~35 files missing against calendar; 2018 holds 223 vs ~246 expected;
    2026-08-01 missing; pre-2014 files lack `instrument_key`.
11. **Pre-2023 index 1m is vendor-sourced and never independently verified** against the
    certified 1d store (`A_INDEX_INTRADAY_PRIOR_EXPOSURE_AUDIT.md` §2). Pre-2023 index
    rows carry `volume = 0`; July-2016 dates are resampled sub-minute ticks.
12. **Futures history cannot predate 2016** — the calendar lever is exhausted there.

## 6. Leakage, survivorship, timestamp and budget risks

**Timestamp**
- 1m `timestamp` is the **bar open**. A signal computed from the 09:15 bar is not known
  until 09:16. Every label must begin strictly *after* the signal window's last bar closes
  (the ISD R2 pin).
- **Post-CAS (≥2026-08-03)**, F&O names carry carry-forward bars 15:15–15:27 with
  `O=H=L=C`, `volume=0`, and the auction in one print. Filter `is_synthetic = FALSE`.
  **A bar is not a trade** — a contiguity gate that counts one bar per slot passes on
  fabricated data.
- `volume = 0` as a synthetic predicate is **`NSE_EQ`-only**. Indices carry volume 0 on
  every bar; applying it to `NSE_INDEX` marks real index history as fabricated. Resolve
  the index era **by rule** (date), never by detection.
- Never VWAP or vol_z on `NSE_INDEX`.
- Roll/expiry counting must run past the last *stored* date via `nse_holidays.py`.

**Survivorship / entity**
- A per-day 1m file's symbol set is **whichever universe its writer used**, not a universe.
  ~190 constant names from day one is exactly the shape a backfilled fixed list would have.
  Use `pit_membership` (`intraday_present`, `fno_member`); do not upgrade ISD's
  certification to "survivorship-free" beyond what it states.
- An entity is not one symbol for all time (recycled tickers, DTIL) → `symbol_entity_intervals`.
- An ISIN is not one entity for all time (face-value re-issue, PHILIPCARB/PCBL) → issuer-prefix linkage.
- An index is not one name for all time (`S&P CNX Nifty` → `CNX Nifty` → `Nifty 50`) →
  match by containment, hard-fail unmapped.

**Lookahead**
- Adjustment factors must be applied causally, ex-date-gated.
- Dividends are not price-adjusted — do not confuse with total return.
- Day-type regime labels are **not PIT-safe on reuse** (KMeans trained 2012–2023);
  retrain per window or exclude.
- Never stitch `1m_vendor/` (different schema, ends 2025-08-06) into the canonical store.

**Multiplicity / specification**
- The admissible (price-unit, time-unit) normalization set **is** the multiplicity surface.
  {1×1, 2×1, 1×2, 3×1, 1×3} across *k* normalizations is m = 5k, pinned before the read.
- The **number of candidate origin rules** counts toward *m*.
- In-repo precedent: ISD's 4 cells at BH α = 0.0125.

**Budget exhaustion (the fourth class the charter omits)**
- Reading a window in any *signal-level* capacity spends it. C2 is the inventory.
- A declared `n_available` over a read window is a false power calculation.
- Every new declaration must carry a prior-exposure section naming what it inherits.

## 7. Proposed architecture of the research battery

Seven layers. Lower layers are shared and certified once; only L2 changes per hypothesis.

**L0 — Substrate access (PIT-enforcing, read-only).** One loader per canonical store. It
owns the calendar oracle, the `is_synthetic` filter, era resolution by rule, entity/ISIN
interval resolution, causal adjustment, and PIT universe membership. **No research code
touches DuckDB directly.** This is where every pitfall in §6 is enforced once instead of
re-litigated per construct. Certification report before first use (this repo's P2 gap is
still open).

**L1 — Clock & origin.** Time is a first-class coordinate: session phase, elapsed bars
from origin, time-to-event. An **origin rule** is a deterministic function of strictly
prior data, declared in the pre-registration; its candidate set is enumerated and counted.

**L2 — Construct (the only hypothesis-specific layer).** A pure function
`(panel, frozen_params) → signal values`. No labels visible. Geometry, cross-market
residual, and derivatives constructs all satisfy this signature — which is what makes the
incremental-information layer possible later.

**L3 — Labels.** Forward returns beginning strictly after the signal window closes.
Non-overlapping by construction, or the overlap is declared and handled (AC₁ / Newey–West).

**L4 — Evaluation.** Rank-IC or per-trade P&L; NW-corrected t; **empirical null via
circular shift** (ISD's machinery); era-accurate net-of-cost spread; block-bootstrap where
the unit is a trade. Cost anchors already measured: `A_COST_SUBSTRATE_MEASUREMENTS.md`
(~5.3 bp/session index intraday), `core/execution/equity/delivery_fees.py`.

**L5 — Governance.** Budget declaration → RFA declaration (frozen, SHA-256) → gate →
pre-registration freeze (SHA) → TRAIN → HOLDOUT → SEALED one-shot; trial ledger
(`data/isd/trial_ledger.jsonl` precedent); multiplicity register.

> **The steer this layer forces on the Gann family — to be tested by an RFA
> declaration, not assumed.** A geometry rule on Nifty is a `per_trade_pnl` claim on a
> *single index time series*. RS-MOM established that shape is structurally dead:
> `ncp = S·√T`, √T_sealed ≈ 1.89 → needs Sharpe ≥ 1.3. **Cadence cancels** — finer bars
> buy no power. The escape CB-N50 demonstrated is `rank_ic` over a **genuine
> cross-section** (√n = 29.8 from the same calendar). So the same geometry expressed as a
> daily cross-sectional rank-IC over the ~190-name panel is the only shape that can
> plausibly clear the gate. **But** CB-N50's third binding constraint applies with full
> force: using 190 stocks merely to manufacture a rank-IC statistic for an index-only
> price rule is **invalid** — if the hypothesis is cross-sectional, the primary hypothesis
> must be stock-level prediction.

**L6 — Incremental information.** Only for constructs that cleared L5 independently.
Nested comparison `A` vs `A+B` on a window unread by *both*; the new source must
improve HOLDOUT, not TRAIN. This is where §13's existing sleeves (Carry, TS Basis, the
ISD F4 finding, DayType, MRLC) enter — as **controls to beat**, never as free ingredients.

**L7 — ML combination.** Last, and only over frozen L5-cleared inputs, under nested OOS.

## 8. What should NOT be built yet

1. **No construct code before its RFA declaration is frozen and PROCEED.**
2. **No Gann/geometry implementation** before the price-unit, time-unit, origin rule, and
   full multiplicity count are written down and frozen.
3. **No ML / feature-store / XGBoost layer.** Nothing has cleared L5 in this family.
4. **No intraday option-chain battery** — the history does not exist (§5.3).
5. **No sentiment/news pipeline**, and no acquisition decision, until a price-side result
   exists that sentiment could plausibly add to.
6. **No cross-market module beyond Nifty↔Bank intraday and the 1d index family.**
   No FX/commodities/bonds/global — do not build an abstraction awaiting data.
7. **No portfolio optimizer, sizing layer, SL/TP logic, or options-selection layer.**
   Downstream of a signal that does not yet exist.
8. **No SEALED read of any window**, and no reliance on A's "SEALED untouched" claim
   until the C2 tension is adjudicated by the operator.
9. **No re-run of A or ISD with a widened grid** — both are terminal; neither authorizes a
   successor. A new construct starts its own pre-registration.
10. **No `MarginProvider` / broker-reconciliation abstraction** (ADR-011/012/013 standing).
11. **No new persistent store** until L0's certification says what it must guarantee.

## 9. The logical sequence of phases

| Phase | Deliverable | Spends a window? | Exit condition |
|---|---|---|---|
| **P0 — Budget adjudication** | Prior-exposure register across the 1m store (index + breadth), including the A-vs-pair-research reconciliation. Extends the existing audit to the breadth panel | No | Operator ruling on which windows are readable, and in what capacity |
| **P1 — Store-map correction** | Fix `DATA_STORE_MAP.md` §9 for C1 (breadth starts 2023-01-02); re-verify the other §9 claims by the same method | No | Map matches the store |
| **P2 — L0 substrate certification** | PIT access layer + certification report (entity/ISIN/CA/calendar/synthetic/universe arms, unfiltered, contract-shaped) | No | Zero structural defects; deterministic reproducibility |
| **P3 — Hypothesis catalogue** | Every price-time / cross-market / derivatives hypothesis written as a *quantity with units and a null*, with candidate origins and normalizations **enumerated**. Includes the honest Gann formalization | No | Operator selects the slate; *m* is pinned |
| **P4 — RFA pre-checks** | One frozen declaration per candidate; band independently defended (CB-N50 shrinkage lesson). Expect ABANDONs — that is the gate working | No | Survivors only |
| **P5 — Pre-registration freeze** | Per survivor: exact definition, eligibility, timestamp semantics, split, benchmark, cost model, robustness set, **failure criteria**, multiplicity correction. SHA-256 frozen | No | Operator sign-off |
| **P6 — TRAIN** | Discovery read on the declared TRAIN window | **Yes** | Gate verdicts per pre-registration |
| **P7 — HOLDOUT** | Confirmatory read at frozen parameters | **Yes** | Pass/fail, no re-tuning |
| **P8 — Costs & executability** | Era-accurate net-of-cost at the executable horizon | No new read | Net positive, or terminal (ISD F4's lesson) |
| **P9 — Robustness** | Sub-period, regime, parameter-neighbourhood, null-model checks | No new read | Stability documented |
| **P10 — Incremental information** | `A` vs `A+B` nested comparison against existing sleeves | **Yes** | HOLDOUT improvement, or "no incremental information" (a valid result) |
| **P11 — Combination / ML** | Only over frozen, cleared inputs, nested OOS | **Yes** | Beats best single input OOS |
| **P12 — Trading layer** | Sizing, risk, instrument selection, execution | — | Out of scope until P11 |

P0–P5 read no market data and spend no budget. If the programme dies at P4, it costs a
handful of declaration files — which is the gate's entire purpose.

---

## What I need from the operator to proceed

1. **Ruling on C2** — which windows are readable, and in what capacity? Specifically:
   is index 1m 2023→ fresh (A's framing) or spent (the audit's framing)?
2. **Confirm the phase sequence**, or say where to cut it.
3. **P3 slate** — how wide should the hypothesis catalogue be before RFA?
4. Whether the Gann family is formalized as **single-index `per_trade_pnl`** (very likely
   an RFA ABANDON, cheaply — which is itself a clean result) or as **cross-sectional
   `rank_ic` with a genuine stock-level primary hypothesis**.
