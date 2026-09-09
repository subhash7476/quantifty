# N200 Per-Stock Regime Classifier — Design Spec

**Date:** 2026-09-09
**Branch:** `feat/n200-regime-hmm`
**Status:** pre-registered design, approved section by section. Every parameter below was fixed **before** any estimation code was written or any fold was fitted.

---

## 1. What this is

A pooled panel hidden Markov model over the point-in-time N200 cross-section that emits, for every stock on every date, a filtered probability distribution over three latent regimes, a canonical state label, and an entropy measure of state uncertainty.

**It is a statistical estimation build, not a strategy.** No trading rule, no expression in futures or options, no factor sleeve, no P&L. Those decisions come later, if at all, and are out of scope here.

## 2. What this is not, and why that matters for governance

This build **never reads a forward return**. Its features are volatility, trend-efficiency and normalized-drift descriptors; its acceptance target is forward realized *volatility*. Nothing in it estimates or evaluates return predictability.

Three consequences, pinned so nobody re-reads this artifact later as something it isn't:

- **It does not consume the sealed return window.** The 2023–2026 out-of-sample return budget stays intact.
- **It does not require an RFA declaration.** The RFA gate governs constructs claiming an effect against forward returns; this one makes no such claim. *If* a successor turns these probabilities into a return-predicting construct, that successor needs its own RFA and must disclose this build as prior exposure.
- **The moment anyone regresses these states on forward returns, that is a different study** under different rules. Doing so inside this repo would burn window.

This mirrors the platform's "Analytics Produce Facts" principle: the regime panel is a fact table, computed offline, read-only at runtime.

## 3. Substrate

Verified by `scripts/n200_regime/preflight_substrate.py` → `docs/reports/index_research/N200_REGIME_SUBSTRATE_PREFLIGHT.md` (commit `e0d67cf`).

| Item | Finding |
|---|---|
| Prices | `equity_bhavcopy_adjusted`, 7,146,210 CA-adjusted OHLC rows, 2010-01-04 → 2026-09-08 |
| Membership | `universe_membership`, 175 monthly rebalances, exactly 200 names each, 2012-01-31 → 2026-07-09 |
| Member → price coverage | 2 misses in 35,000 member-months (0.006%) |
| Warmup at fold boundaries | 192–198 of 200 names carry ≥252 prior sessions at every fold 2017–2026 |
| OHLC integrity | 0 nulls, 0 non-positive, 0 `high < low`, 0 open/close outside `[low, high]` |
| Panel size | ~487,000 filtered observations across ten folds |

**Two substrate facts this design absorbs rather than hides:**

1. **Membership is `method = turnover_top200`** — a constructed top-200-by-turnover, **not official NSE Nifty 200 index membership**. It is point-in-time and survivorship-free, which is what the estimation needs, but every downstream statement must say "top-200 by turnover", never "Nifty 200".
2. **187,651 rows (2.63%) are zero-range.** With no row carrying open or close outside `[low, high]`, zero range forces O = C = H = L, so Garman-Klass is **exactly zero** there (0 negative rows). `log(GK / baseline)` is undefined at zero. These are circuit-locked or untraded sessions.
   **Pinned treatment:** floor each stock's GK variance at the 1st percentile of its own non-zero GK, computed on the fit window only.

## 4. Panel construction

- **Universe:** `universe_membership`, monthly rebalances. A name is in the panel for the month following each rebalance at which it appears.
- **Entity grain:** resolved through `symbol_entity_intervals`. NSE recycles vacated tickers and re-issues ISINs on face-value change; symbol-grain joins silently splice two companies together. This is the PSB-1 lesson and it applies unchanged.
- **Series:** `EQ` and `BE` only (the store holds nothing else). `BE` is retained deliberately — a move to trade-for-trade surveillance is itself part of a stock's volatility state, and excluding it would delete exactly the stressed observations State 2 exists to describe.
- **Sequences:** one per (entity × contiguous membership interval). A name leaving and re-entering the universe yields two sequences, never one with a hole — an HMM run across a gap would propagate state through time that does not exist.
- **Warmup:** 252 sessions of prior history required before a name contributes an observation.
- **Minimum sequence length:** 60 sessions; shorter sequences are dropped.

## 5. Features

Four per stock per day. All trailing-only — no centred windows, no forward information.

| Feature | Definition | Purpose |
|---|---|---|
| `gk_vol_z` | `log(GK²_t / median(GK²) over trailing 252 sessions)` | level-free volatility state |
| `gk_ratio_st` | `log(mean(GK²) over 5d / mean(GK²) over 60d)` | volatility *expansion* — separates onset-of-stress from steady high vol |
| `ker_20` | `abs(P_t − P_{t−20}) / Σ abs(ΔP)` over the same 20 sessions | Kaufman Efficiency Ratio: trend vs chop |
| `drift_t` | `r_{20d} / (σ_daily × √20)` | signed, scale-free drift |

**Garman-Klass:** `GK² = 0.5·ln(H/L)² − (2·ln2 − 1)·ln(C/O)²`, floored per §3.2.

**Winsorization:** each feature at ±3 standard deviations. **Bounds computed on the fit window only** and applied unchanged to the filter year — recomputing bounds on the filtered year would leak.

**Standardization:** zero mean, unit variance, using **fit-window moments only**, frozen with the model parameters.

## 6. Model

Pooled panel Gaussian HMM, `K = 3`, fitted by Baum-Welch in log space.

- **Shared across all names:** one transition matrix `A` and one set of emissions. This is what makes State 2 mean the same thing for every stock, and it is defensible only because the features are normalized to be cross-sectionally comparable. *Stated limitation:* a defensive largecap and a high-beta midcap are assumed to switch at the same rate. Per-stock `A` is a pre-registered robustness variant, not the base case.
- **Emissions:** Gaussian with **diagonal covariance**. Chosen for numerical stability in the M-step; feature correlation is absorbed into state definitions rather than modelled within-state.
- **E-step:** forward-backward per sequence, log-sum-exp throughout. Sufficient statistics accumulated across all sequences before any M-step update.
- **M-step:** closed-form updates for `A`, `μ`, `σ²` from pooled statistics.
- **Initialization:** k-means on the fit window with a fixed seed. Deterministic — same input, same parameters, same hash.
- **Convergence:** relative log-likelihood change < 1e-6, maximum 200 iterations. Both recorded in the fold artifact.
- **Canonical ordering:** after each fit, states are sorted ascending by `gk_vol_z` emission mean, so State 0 = Quiet, State 1 = Intermediate/Chop, State 2 = Stress. The permutation is applied to `A`, `μ`, `σ²` together and stored as `order_map`. **This is what eliminates label switching across refits** — not a constraint during EM, a deterministic sort after it.

## 7. Causal inference

**Filtered marginals only.** For each sequence, forward recursion:

```
α_t(j) ∝ f(y_t | S_t = j) · Σ_i A_ij · α_{t-1}(i)
P(S_t = j | F_t) = α_t(j) / Σ_k α_t(k)
```

No backward pass, no smoothing, no Viterbi. The backward pass exists in the E-step **during fitting only**, inside the fit window, and never touches a filtered output.

**Entropy:** `H_t = −Σ_j p_j · log₃(p_j)`, normalized to [0, 1] — 0 is certainty, 1 is a uniform posterior.

## 8. Folds and the lookahead barrier

Expanding window, annual boundaries.

| Fit window | Filter (evaluation) year |
|---|---|
| 2012–2016 | 2017 |
| 2012–2017 | 2018 |
| … | … |
| 2012–2025 | 2026 (partial — store ends 2026-09-08, 170 sessions) |

The fit window opens at 2012 because that is when membership begins; the 252-session feature warmup for those early names is drawn from **price** history back to 2010, which membership does not gate. So 2012 features exist and the first fit window is a genuine five years.

**Barrier:** parameters used to filter any date in year *T* are estimated only on data ending 31 December *T−1*. This covers the model parameters, the winsorization bounds, the standardization moments, and the GK floor. Lookahead through parameters is the failure mode this design most needs to avoid, and it is not visible in the output — only in the fold construction.

Canonical ordering is re-applied at every refit, before parameters are frozen and handed to the filter.

## 9. Artifacts and provenance

**Panel:** `data/features/n200_regime/regime_panel.duckdb`, one row per (entity, trade_date):

```
entity, symbol, trade_date, fold_year,
p_s0, p_s1, p_s2, state, entropy,
model_hash
```

**Parameters:** one JSON per fold, `data/features/n200_regime/params/fold_{year}.json`:

```
A (3×3), mu (3×4), var (3×4), order_map,
feature_names, winsor_bounds, standardize_moments, gk_floor_pct,
trained_on (window), n_sequences, n_observations,
iterations, final_loglik, converged,
git_commit, fitted_at, model_hash (SHA-256 over the numeric payload)
```

**No pickles anywhere.** Every artifact is plain arrays in JSON or Parquet. This is deliberate: the DayType audit found the live path serving version-coupled sklearn pickles whose `model_hash` covers the pickle bytes but not the library that must unpickle them. Plain arrays have no such coupling and hash stably.

## 10. Acceptance gate

### 10.1 Primary gate — forward volatility calibration (binding, pass/fail)

**Target:** for each (stock, date *t*), the binary event that forward 5-day realized Garman-Klass volatility — `sqrt(Σ GK²_{t+1..t+5})` — lands in the **top tercile** of that stock's own trailing distribution. The mirror event (bottom tercile) is scored against State 0.

**Threshold construction — strictly backward-looking.** The tercile cut for date *t* is the empirical 33rd/67th percentile of that same forward-5-day quantity over the stock's trailing 252 sessions **ending at t−1**. No global quantile, no in-sample quantile, no quantile computed over a window containing *t*. This is the one place where an innocuous-looking `quantile()` call would silently leak the answer into the label.

**Metrics:**

- **Brier score** of `P(S_2 | F_t)` against the top-tercile realization, and of `P(S_0 | F_t)` against the bottom-tercile realization. Pooled across the panel, per fold and overall, strictly out-of-sample.
- **Brier skill score** against two baselines: (i) the unconditional trailing base rate, and (ii) a persistence baseline using the stock's current GK percentile as its predicted probability. The second is the honest one — beating "today was volatile, so tomorrow will be" is the real bar.
- **Reliability diagram**, 10 equal-width probability bins, bins with ≥100 observations. Report Expected Calibration Error.

**Pass conditions, pinned.** The binding pair is `P(S_2)` against the top-tercile event. The `P(S_0)` / bottom-tercile pair is computed and reported, and a sign disagreement between the two is a finding, but the gate is decided on the State 2 pair — one gate, not two, so there is no ambiguity about which result governs.

1. Brier skill score > 0 against **both** baselines, pooled across all folds; **and** positive in **≥ 7 of 10** folds.
2. Reliability curve **monotone non-decreasing** across populated bins.
3. **ECE < 0.05** on the State 2 pair (reported for State 0, not gated).

**Evaluation-overlap caveat, disclosed up front:** the 5-day forward target overlaps across consecutive dates, so pooled observations are autocorrelated and a naive standard error would be optimistic. Confidence intervals come from a **stationary block bootstrap** (block length 10 sessions) over dates, and the gate is additionally reported on a **non-overlapping every-5th-session subsample** as a robustness column. The pass conditions are evaluated on the full sample; the subsample is disclosure, not a second gate.

### 10.2 Sanity check A — predictive compression (mandatory)

Out-of-sample mean log-likelihood per observation must exceed **both** an i.i.d. Gaussian mixture (same K, same features, no transition structure) and a single-state Gaussian, in **≥ 8 of 10** folds. This is what establishes that the transition dynamics earn their parameters rather than the states merely partitioning the feature space.

### 10.3 Sanity check C — structural realism and anti-flicker (mandatory)

- **Dwell time:** median regime dwell **> 3 sessions**. A model that ping-pongs daily has found noise, not regimes. Reported alongside the implied durations `1/(1 − A_ii)`.
- **Cross-sectional coherence:** cross-sectional mean `P(S_2)` must spike systemically during known stress, not scatter idiosyncratically. Specific check: the March 2020 window ranks in the **top 1% of all days** by cross-sectional mean `P(S_2)`. Reported with the full time series so a reader can see 2018 IL&FS, 2020 COVID and 2022 separately rather than taking one number on faith.

## 11. Testing

| Test | What it proves |
|---|---|
| **Synthetic recovery** | Generate a panel from a known `A`, `μ`, `σ²`; EM recovers them within tolerance. If this fails, nothing downstream means anything. |
| **Causality / truncation** | Filtering a sequence truncated after date *t* yields `P(S_t)` **bit-identical** to filtering the full sequence. This is the only test that actually proves filtered-not-smoothed; a smoother fails it immediately. |
| **Determinism** | Same input → same parameters → same `model_hash`, across runs and processes. |
| **Canonical ordering** | Permuting the initialization must not permute the output labels. |
| **Log-space stability** | Long sequences do not underflow; log-likelihood is finite and monotone non-decreasing across EM iterations. |

## 12. Layout

```
core/analytics/regime/panel_hmm.py    EM + forward filter. Pure numerics, no I/O.
core/analytics/regime/features.py     GK, KER, drift, winsorize, standardize.
scripts/n200_regime/build_panel.py    Substrate → feature panel.
scripts/n200_regime/run_folds.py      Fit + filter per fold; writes params + panel.
scripts/n200_regime/evaluate.py       Gate §10 + sanity A/C → report.
scripts/n200_regime/preflight_substrate.py   (done, committed e0d67cf)
tests/regime/test_panel_hmm.py        §11 tests.
```

Engine stays free of DuckDB and file paths so the synthetic recovery test exercises the same code the folds do.

**Memory constraint (operational, learned during preflight):** the box has ~2.6 GB free of 7.9 GB, and `equity_bhavcopy_adjusted` is a view doing entity-grain CA joins recomputed on every query. The panel build materializes it **once** to an on-disk scratch database with `memory_limit` set below free RAM. A fold runner that streams repeatedly from that view will die with "Allocation failure".

## 13. Sequencing and deferred work

**This build first: implement → fit → evaluate against §10.** Nothing promotes to a nightly publisher until the gate passes.

### Deferred — DayType repair (queued, do after this build is validated)

The existing intraday DayType regime classifier has three confirmed defects from `docs/reports/index_research/REGIME_DETECTION_SPEC_AUDIT_2026-09-09.md`. They are **not fixed by this build** and remain open. Ordered as the audit ranked them:

1. **Horizon mismatch (HIGH).** The label is a full-session KMeans archetype; the strategy opens at 13:00 and closes at 15:15 (median move over that window 10.6 pts, 0.044%). Trained on one horizon, consumed on another. Resolution is either re-labelling on the traded horizon and retraining — a new construct — or explicitly documenting that NiftyShield consumes it as a directional prior, which is all the +0.255 pp forward-window diagnostic supports.
2. **Label generator not reproducible (HIGH).** `scripts/daytype/cluster_day_types.py` never persists its scaler, PCA or KMeans objects, so the target definition cannot be re-derived and the live nearest-centroid proxy is not commensurable with the trained label. Fix first — it is a precondition for the other two.
3. **Label fit spans the classifier's holdout (MEDIUM, disclosure).** The KMeans panel is 2012–2025 while the shipped classifier is train ≤2023 / val 2024 / hold 2025, so holdout accuracy is scored against labels defined by a fit that saw the holdout year. Tolerable for a taxonomy; currently undisclosed in model metadata.

Two smaller items from the same audit, also open: `scikit-learn` / `scipy` / `lightgbm` are undeclared in `requirements.txt` and `pyproject.toml` while the live path unpickles sklearn objects (Finding E), and `subperiod_stability` prints "2023-24 vs 2025-26" for masks that are `≤2020` / `≥2021` (Finding D).

**Explicit non-goal:** no part of this N200 build should be reused to "fix" DayType by substitution. They are different objects over different horizons — that framing is the whole first section of the audit.

## 14. Risks and what would falsify this

| Risk | Consequence | Disclosure |
|---|---|---|
| Shared `A` is misspecified across the size/beta spectrum | Dwell times are an average that fits nobody | Per-stock `A` is the pre-registered variant; dwell reported per size tercile as diagnostic |
| `K = 3` fixed rather than selected | A genuine 2- or 4-state structure is forced into 3 | Fixed by design requirement; log-likelihood at K = 2, 4 reported as disclosure, **not** used to reselect after seeing gate results |
| Turnover-proxy universe ≠ Nifty 200 | External claims about "Nifty 200" would be wrong | Named in every artifact |
| Zero-range flooring distorts the quiet state | State 0 partly captures illiquidity, not calm | Share of State 0 mass sitting on floored rows reported |
| 2026 fold is a partial year (170 sessions) | Last fold has less evidence | Reported per fold; gate counts folds, so a thin fold cannot dominate |
| Gate passes but states are useless for anything | A well-calibrated forecast of volatility terciles is not automatically actionable | Accepted — usefulness is explicitly out of scope, and testing it is a separate study under different governance |

**What would falsify the build:** a Brier skill score at or below the persistence baseline. If knowing the filtered regime adds nothing beyond "this stock has been volatile lately", the latent structure is decorative and the honest outcome is to say so and stop.
