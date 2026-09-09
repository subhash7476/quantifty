# INTRADAY_ANALOG_PATH_PROTOCOL — Phase 1A (DRAFT, pre-analogue-engine)

**Status:** Phase 1A — data layer, baselines, and state construction only.
The analogue engine (KNN), null tests, and the TRAIN gate report are Phase 1B;
this document's §1–§6 are frozen now; §7–§9 are frozen by Phase 1B's
pre-registration before any HOLDOUT read.
**Branch:** `research/intraday-analog-path`
**Machine-readable config:** `scripts/analog_path/config.json` (SHA-256 recorded in §11)
**Date:** 2026-09-09

---

## 1. Hypothesis

> The path taken by the NIFTY 50 index from market open to 12:30 contains
> information about the distribution of returns after 12:30 that is not fully
> captured by the simple return from open to 12:30.

Formally, with t0 = open, T = 12:30, X_T = the 15-minute-grid state at T:

- H0 (null): P(return after T | X_T) = P(return after T | R_open→T)
- H1: the full path adds incremental information beyond R_open→T.

The central comparison is Model A (return-only conditioning) vs Model B
(historical path-analogue conditioning). A clean negative result is a valid
outcome.

## 2. Definitions (frozen)

- **Instrument:** `NSE_INDEX|Nifty 50` only. No BANKNIFTY, no stocks in Phase 1.
- **Data source:** the certified 1-minute store,
  `data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb`, read through the
  normalized contract (mirrors `scripts/isd/read_1m.py`; schema drift handled
  in one place).
- **Grid:** 14 fixed stamps — 09:15, 09:30, …, 12:15, 12:30 (15-minute
  spacing). *Operator decision 2026-09-09:* the enumerated timestamp list
  (14 stamps → 13 intervals) is authoritative; the prompt's summary numbers
  ("13 observations", "12-dimensional") are recorded as off-by-one slips and
  overridden by the enumeration.
- **Timestamp eras (certified):**
  - *end-labelled sessions:* first bar 09:16 covers 09:15–09:16; a bar
    stamped t closes AT t;
  - *start-labelled sessions:* first bar 09:15; a bar stamped t opens AT t;
  - *cas* ≥ 2026-08-03 — start-labelled; the index 15:29 bar carries the
    closing-auction print.
- **Operational era rule (AP-D4 resolution, 2026-09-09):** the price rule
  follows the **observed first-bar stamp** (09:16 → vendor rule, 09:15 →
  native rule), not the calendar date; date-based provenance is retained as
  a separate recorded field. This admits the 20 Jan-2023 sessions.
- **Price at grid time t (frozen):** the last close of a bar whose stamp is
  ≤ t — **except 09:15**, which is the first bar's open (the A-track D3
  opening-print convention, reused verbatim). Consequently P(12:30) is the
  close of the 12:30-stamped bar in the vendor era and the close of the
  12:29-stamped bar in the native/cas eras. The 12:30-labelled native-era bar
  must NOT be used.
- **Open (frozen):** first valid session bar's open in all eras. *Disclosed
  discrepancy:* the vendor-era first-bar open deviates from the official
  daily open (median 3.2 bp / p99 25 bp / max 74 bp; A_INDEX_SLICE_
  CERTIFICATION C5) because the 1m series carries the opening print, not the
  auction print. Accepted; never silently substituted by the daily candle.
- **Close (frozen):** the close of the session's final minute bar — stamp
  15:30 (vendor) / 15:29 (native and cas). This rule is robust to the flat
  feed-extension tails found on six 2025 sessions (15:30–15:59 prints at a
  different frozen value; defect-register entry AP-D1). In the cas era the
  15:29 close IS the closing-auction print (the index's official close).
  **Sealed-era note:** this convention governs the 2026-08-03+ sessions and
  is fixed now, before any sealed outcome read; operator sign-off is
  recorded at final freeze.
- **Outcomes (frozen horizons):** returns of P(t)/P(12:30) − 1 for
  t ∈ {13:00, 13:30, 14:00, 15:00, close}. Price at each t uses the frozen
  rule above.
- **Excursions (frozen):** over all bars strictly after the cutoff bar and
  through the close bar: MFE = max cumulative return (≥ 0), MAE = min
  cumulative return (≤ 0). Flat extension tails are outside the window by
  construction (capped at the close stamp).

## 3. State representations (frozen)

- **A — normalized price path (magnitude + shape):** 14-vector
  `P(t)/P(09:15) − 1`, first element exactly 0.
- **B — interval returns:** 13-vector of simple interval returns
  `P(t_{i+1})/P(t_i) − 1` over the grid.
- **Distance (frozen):** Euclidean, only. No DTW / cosine / correlation /
  clustering / ML in Phase 1.
- **K values (frozen):** {5, 10, 20, 50}. All four reported; none selected
  by performance.
- **No additional normalization** (no per-day z-scoring) is introduced in
  Phase 1. Any candidate normalization requires operator approval before use
  (protocol §35 of the research prompt).

## 4. Eligibility (frozen rule, mechanically applied)

A session is eligible iff ALL of the following hold:

1. the per-date 1m file exists;
2. the first bar's date equals the session date (no cross-day contamination);
3. the first bar stamp matches an observed-labelling standard (09:16 or
   09:15; anything else excluded);
4. ≥ 360 bars in the session;
5. ≥ 195 bars in the morning window 09:15–12:31;
6. all 14 grid prices constructible with positive prices;
7. the era close bar exists with positive close;
8. all four intraday horizon bars (13:00/13:30/14:00/15:00 per era stamps)
   exist with positive prices;
9. timestamps strictly monotonic, no duplicates;
10. OHLC consistency and positive prices on every bar.

Excluded by this rule (all verified): May 2018 hole (no files — permanent),
Feb 2023 hole (no files — vendor/native transition), the 2024 Saturday DR
sessions ending 12:29, Muhurat evening sessions, outage/halt days
(2013-10-14, 2017-07-10, 2021-02-24, 2021-07-23, 2022-03-07, circuit-breaker
days 2020-03-13/23), the two multi-day corrupt files (2026-02-25,
2026-03-02), nonstandard-first-bar days (e.g. 2018-07-09, 09:17), and the
60-bar special sessions. **The rule is the universe; no hand-picked
exclusions, no imputation of holes.** The eligible list is persisted
(`data/analog_path/eligible_days.csv`) and reproducible from committed code.

## 5. Fences (frozen; unchanged from the A-track)

| Window | Span | Role |
|---|---|---|
| TRAIN | 2012-01-01 → 2018-12-31 | discovery; baselines and methodology development |
| HOLDOUT | 2019-01-01 → 2022-12-31 | one-shot validation after TRAIN freeze |
| SEALED | 2023-01-01 → present | untouched until final freeze; one-shot final test |

**Prior-exposure disclosure:** the earlier A construct read TRAIN and
HOLDOUT on this same index 1m store for a *different* construct
(opening-drive continuation; retired at HOLDOUT 2026-08-27); the
pair-ratio analysis read 2023–2026 1m (ratio hypothesis only); the DayType
pipeline read index 1m structurally (2012–2025, regime labels). **The
present construct has no construct-level read in any window**, and the
SEALED window has never been read at construct level by any project.

## 6. Leakage controls (frozen, enforced programmatically)

- **Expanding walk-forward analogue pool:** for query day D, the analogue
  database contains only dates strictly earlier than D. Never D, never
  futures, never future outcomes. Enforced by the matcher API (Phase 1B),
  tested in `tests/analog_path/test_leakage.py`.
- Session state and outcomes for D are constructed from the single file D
  only — verified by an isolation test (loader pointed at a directory
  containing only D's file must reproduce the state identically).
- Fence guard: `config.require_fence` raises on any SEALED date; the sealed
  runner is hard-locked until the methodology freeze. Phase 1A runners
  accept only `train`/`holdout` and validate every loaded date.
- Data-integrity checks (§4 items 9–10) run on every loaded session; defects
  are recorded (append-only `defect_register.json`), never silently repaired.

## 7. Experiments (Phase 1A implemented; 1B pre-registered)

- **Exp 0 — unconditional baseline:** distribution of each frozen horizon +
  MFE/MAE over TRAIN: n, mean, median, sd, hit rate (frac > 0), skew,
  quantiles {1,5,10,25,50,75,90,95,99%}, Newey-West t (lag 5), AC1,
  moving-block bootstrap 95% CI of the mean (blocks of 5 sessions, 10,000
  iterations, seed 42).
- **Exp 1 — return-only baseline:** R = P(12:30)/P(open) − 1, binned at the
  frozen edges {−∞, −2, −1, −0.5, 0, 0.5, 1, 2, +∞}%. Same summary block per
  bin per horizon; continuous confirmation = OLS of outcome on R with
  Newey-West SE per horizon (pre-specified, not bin-optimized).
- **Exp 2/3 — state construction:** representations A and B (implemented and
  tested in Phase 1A; the analogue engine consuming them is Phase 1B).
- **Phase 1B (not yet authorized):** KNN analogue engine (Euclidean, K ∈
  {5,10,20,50}, expanding walk-forward pool), similarity-quality diagnostics
  (nearest-distance percentile vs the eligible historical distance
  distribution), analogue-conditioned outcome forecasts (mean, median, hit
  rate, forecast error, correlation, calibration buckets), the central
  path-vs-return comparison, the same-return/different-path control
  (**tolerance DEFERRED — pinned before that experiment runs**), and null
  tests (sign-permutation + block-shift random matching, 1,000 iterations,
  seed 42 — the repository's established machinery).

## 8. Statistical methodology (frozen conventions)

- Newey-West t with lag 5 for means of overlapping/serially-dependent
  series; AC1 reported wherever a mean is tested (A-track convention).
- Block bootstrap (moving blocks of 5 sessions) for 95% CIs of means.
- Empirical nulls (1,000 iterations, seed 42) required for any claimed
  effect; parametric p-values never stand alone.
- **Multiple-testing policy:** the search space is fully enumerated in the
  append-only ledger (`data/analog_path/experiment_ledger.jsonl`): 2
  representations × 1 distance × 4 K × 5 horizons (+ excursions). The ledger
  records every experiment with code version, data version, sample, fence,
  result, and whether the result drove a methodological decision. Failed
  experiments are retained; nothing is overwritten. Reporting is of the full
  grid, never the best cell alone.

## 9. Holdout / Sealed discipline (frozen)

1. Develop and debug on TRAIN only.
2. Freeze the full methodology (representations, distance, K set, horizons,
   bins, matching tolerance, exclusion rules, statistical tests).
3. Run HOLDOUT once. No methodology changes based on individual cells.
4. Final freeze; only then may the SEALED window be read — one shot, at the
   frozen methodology. Before that, SEALED access is limited to structural
   eligibility inspection (data integrity, date coverage) — which is what
   Phase 1A has done.
5. Any change after a SEALED read contaminates the window; a new untouched
   holdout must then be created (prompt §13).

## 10. Not a strategy

Phase 1 is statistical validation only. No entry/exit rules, sizing, stops,
leverage, or live signals. If a credible effect survives the gates, an
economic layer (costs, slippage, vehicle, turnover) is a separate authorized
step, and "statistically detectable but economically unusable" is a valid
final classification.

## 11. Configuration seal

`scripts/analog_path/config.json` canonical-form SHA-256 (JSON semantics,
line-ending-stable):
`cd3d5149244c9ed6c5684153f30bedf4a160184375bdc4bb18d6c73dedc8a81d`
(recorded 2026-09-09 — any semantic edit to the JSON breaks the seal and
must be treated as a freeze decision). Code: `scripts/analog_path/` (config,
data_layer, states, matcher, forecasts, control, nulls, eligibility, stats,
ledger, exp0/exp1, run_phase1b_train, plot_examples, verify_sample). Tests:
`tests/analog_path/` (69 passing at Phase 1B). Artifacts (git-ignored,
reproducible): `data/analog_path/` (eligible list, defect register,
experiment ledger, experiment results, analogue records, plots).

## 12. Known data defects absorbed by the frozen rules (register)

- **AP-D1 (new, this track):** six native-era sessions (2025-04-25, 04-30,
  05-08, 05-13, 05-21 + one further) carry 15:30–15:59 flat extension prints
  at a frozen value that differs from the 15:29 close; not flagged synthetic
  in the store. Absorbed by the frozen close rule (stamp-based) and the
  excursion-window cap. No outcome is affected.
- **AP-D2 (new, this track):** the 2026-02-25 and 2026-03-02 files each
  contain the previous session's bars (first-bar-date rule excludes both).
- **AP-D3:** CAS-era index bars 15:15–15:28 are flat carry-forward prints
  (not synthetic-flagged); the 15:29 bar carries the auction print. The
  frozen close = 15:29 bar close; flat bars inside the excursion window add
  no new extremes.
- **AP-D4 (RESOLVED 2026-09-09, operator decision):** the 20 Jan-2023
  sessions are **included**. Era classification follows the OBSERVED
  first-bar stamp (09:16 → end-labelled/vendor rule; 09:15 →
  start-labelled/native rule; anything else → excluded), not the calendar
  date. Tests demonstrate the convention across the transition period
  (2022-12-30, 2023-01-02, 2023-01-31, 2023-03-02). SEALED eligible count:
  865 → 885. TRAIN/HOLDOUT unaffected (1,687 / 981).
- Inherited (A-track certification): vendor-era opening-print discrepancy;
  May 2018 and Feb 2023 permanent holes; 2026-08-24..26 recent lag
  (re-ingestible only through the normal certified process — not a
  prerequisite for this research).

## 13. Phase 1B amendments (operator-authorized 2026-09-09)

1. **Same-return/different-path tolerance frozen at ±10 bp** on the
   open→12:30 return (config `return_matching_tolerance_pct = 0.10`).
2. **State C (diagnostic only):** `C(t) = A(t) − (t/13)·A(12:30)` — the
   linear detrend of State A; first and last elements exactly 0; endpoint
   magnitude removed. One construction only; Euclidean distance like the
   primaries. Reported separately, never used to select primary results.
3. **Both States A and B contain endpoint magnitude** — documented, not
   treated as pure shape.
4. **Walk-forward forecasts (frozen):** expanding mean (unconditional),
   expanding OLS on R (return-only), analogue mean/median. Pool-size rule:
   a query day requires pool ≥ K, else flagged `pool_too_small` (mechanical,
   no threshold tuning).
5. **Similarity quality:** primary measure = nearest distance's percentile
   in the pair-distance distribution of a deterministic pool sample
   (S = min(80, pool), seed NULL_SEED + i); the trivial pool-rank percentile
   is reported for completeness but carries no information (the nearest is
   always the pool minimum).
6. **Nulls (frozen):** randomized matching (K random pool days per query,
   causal sampling; statistic = forecast–realized correlation), block-shift
   (calendar-month blocks; close horizon), sign-permutation (directional
   accuracy; close horizon). 1,000 iterations, seed 42, two-sided empirical
   p-values.
7. **Return-controlled comparison:** `realized ~ [1, analogue_forecast, R]`
   with NW SEs + ΔR² vs the R-only model, all 60 cells.
8. **Control experiment:** ±10 bp matched sets; near/far split at the median
   State-C distance; min group size 5 (frozen); within-group permutation
   null.

Phase 1B TRAIN results: `INTRADAY_ANALOG_PATH_TRAIN_REPORT.md` (verdict:
WEAK; central forecast question NO EVIDENCE; control close-horizon effect
+2.4 bp, permutation p≈2e-5).
