# Regime Detection — Audit Against the Three-Layer Institutional Spec

**Date:** 2026-09-09
**Scope:** read-only audit. No code changed, no model retrained, no market data read.
**Question asked:** does the regime detection in this repo match the submitted three-layer specification (Feature Physics / Statistical Formulation / Online Filtering)?

---

## 0. The answer depends on a framing that has to come first

**The repo's regime detector and the submitted spec are not two versions of the same object.**

- The **spec** describes a *daily, multi-day-persistent* regime process: MS-AR with a transition matrix `P`, `W2(P_t, P_{t-k})` over 30-day vs 252-day empirical return distributions, monotonic `sigma_1 < sigma_2 < sigma_3` anchoring across refits, Hamilton-filtered `xi_{t|t}`.
- The **repo** has a *same-day intraday nowcast of a session archetype*: features built from that session's 09:15→13:00 bars, predicting which of three full-session shapes (`Choppy` / `BullTrend` / `BearTrend`) today will turn out to be. In production it is refit **never** — a frozen pickle is served.

So the correct reading of most "missing" spec items is *different object*, not *inferior implementation*. "Add a transition matrix" presumes day-types persist across days — a property nobody in this repo has measured, and the traded horizon points the other way (13:00→15:15, median absolute move **10.6 pts = 0.044%**, `NIFTY_SHIELD_REGIME_AND_STRUCTURE_AUDIT.md` §2.2).

What exists today, end to end:

```
core/analytics/day_features.py            Blocks A-G: per-session 1m/5m/15m features (Nifty 50)
  -> scripts/daytype/build_eod_features.py        full-session feature panel, 2012-2026 CSVs
  -> scripts/daytype/cluster_day_types.py         winsorize -> StandardScaler -> PCA(87%) -> KMeans   [defines the LABEL]
  -> scripts/daytype/train_daytype_classifier.py  logistic + LightGBM on partial-session features     [predicts the label]
  -> core/state/daytype_engine.py                 live serving: frozen scaler.pkl + model.pkl @ 10am/11am/13pm
  -> scripts/daytype/publish_live_fact.py         writes the 13:00 fact (+ intraday VIX, VIX percentile)
  -> strategies/nifty_shield_v1/                  consumes regime + regime_confidence + vix_pctile
```

**There is no Markov / HMM / state-space regime model in this repository.** A prior generation had one (`HMMRegimeClassifier` over `hmmlearn.hmm.GaussianHMM`, 3 states, Gaussian emissions — `docs/reports/strategies/DRA_TECHNICAL_DOSSIER.md` §3, §10.6), but it lived in the pre-SALVAGE monolith (`D:\BOT\root`) and was **dropped by explicit decision in the 2026-06-04 SALVAGE migration**. Verified absent: a whole-tree grep for `hmmlearn`, `GaussianHMM`, `MarkovAutoregression`, `wasserstein` returns exactly one hit — that dossier. Neither `requirements.txt` nor `pyproject.toml` declares `hmmlearn` or `statsmodels`.

---

## 1. Layer-by-layer verdict

### Layer 1 — Input space (market physics, not price)

| Spec item | Repo state | Evidence | Verdict |
|---|---|---|---|
| Garman-Klass volatility | Not implemented by formula | — | **ABSENT (formula)** |
| Parkinson volatility | Not implemented by formula | — | **ABSENT (formula)** |
| *Range-based, non-close-to-close vol* (the spec's intent) | `intraday_atr_5m` (true-range mean over 5m bars, open-normalized), `day_range_pct`, `largest_5m_candle`, `range_pct_before_11am` / `after_130pm`, `log_vol_expansion` (AM/PM vol ratio) | [day_features.py:250](core/analytics/day_features.py:250)-330, ATR at [:268](core/analytics/day_features.py:268) | **PARTIAL — intent met, formula differs** |
| Is it close-to-close only? | No. `realized_vol` (1m close-to-close sigma) exists but is **dropped before clustering** — corr 0.988 with the range-based ATR | [cluster_day_types.py:59](scripts/daytype/cluster_day_types.py:59) `DROP_COLS` | **The spec's criticism does not bite** |
| Volatility clustering | Explicit feature: lag-1 autocorrelation of \|1m returns\| | [day_features.py:308](core/analytics/day_features.py:308) | **MATCH** |
| Kaufman Efficiency Ratio | Not implemented | — | **ABSENT (formula)** |
| *Trend-vs-chop efficiency* (the spec's intent) | `linreg_r2` on the 1m close series, `hh_count_15m` / `ll_count_15m`, `flip_count_15m`, `twap_cross_count`, `max_twap_excursion`, `center_of_mass_return_time` | [day_features.py:210](core/analytics/day_features.py:210), Blocks C/E/F | **PARTIAL — intent met, formula differs** |
| Cross-asset (Bank Nifty) | Block H, computed live: `bn_nf_open_5m_spread`, `bn_nf_open_30m_spread`, `bn_nf_partial_return_spread`, `bn_nf_correlation_5m`, `bn_nf_range_ratio`, `bn_leads_nifty` | [daytype_engine.py:386](core/state/daytype_engine.py:386)-442 | **MATCH** |
| India VIX | `vix_at_checkpoint` (1m India VIX at/before 13:00) + 756-session trailing percentile gate | [publish_live_fact.py](scripts/daytype/publish_live_fact.py), [vix_percentile.py:76](scripts/daytype/vix_percentile.py:76) | **MATCH (level + percentile)** |
| India VIX **term** spread / 20d-vs-60d RV spread | Not implemented | — | **ABSENT** |
| USD/INR rate of change | Not implemented anywhere in the feature path | — | **ABSENT** |
| 10Y G-Sec yield change | Not implemented | — | **ABSENT** |

**Layer 1 summary.** The spec's *diagnosis* — that raw price / close-to-close returns make unstable inputs — does not apply here. This feature set is structural, range-based, and already carries volatility clustering, trend efficiency, and a cross-asset block. GK/Parkinson would be a **substitution** for `intraday_atr_5m`, not new information. The genuine gaps are **macro/rates/FX** (USD/INR, G-Sec) and **VIX term structure**.

### Layer 2 — Model architecture

| Spec item | Repo state | Evidence | Verdict |
|---|---|---|---|
| Not vanilla GMM / k-means | **It is exactly KMeans** — on PCA of z-scored structural features (not on raw price) | [cluster_day_types.py:150](scripts/daytype/cluster_day_types.py:150), [:156](scripts/daytype/cluster_day_types.py:156), [:199](scripts/daytype/cluster_day_types.py:199) | **DIFFERENT — the criticised architecture, on better inputs** |
| MS-AR / regime switching with transition matrix `P` | Not present. No transition matrix, no persistence term, no serial-correlation model | — | **ABSENT** |
| Latent memory / non-i.i.d. treatment | Absent at model level. Each session is scored independently by a multinomial logistic (or LightGBM) on that session's own partial features | [train_daytype_classifier.py:157](scripts/daytype/train_daytype_classifier.py:157)-196, [daytype_engine.py:339](core/state/daytype_engine.py:339)-360 | **ABSENT — the spec's flaw #3 is a true match** |
| *Within-session / prior-day* memory | Present in the **features** (rolling 20-session percentiles, Block A prev-day gap/range/CLV/slope, AM-vs-PM vol ratio) — as covariates, never as a latent state | [day_features.py:71](core/analytics/day_features.py:71)-127, `fill_block_d_rolling` | **PARTIAL** |
| Optimal transport / `W2` distribution-shift monitor | Not present | — | **ABSENT** |
| Jump models | Not present | — | **ABSENT** |

**Layer 2 summary.** This is where the spec's criticism lands squarely. The taxonomy is unconditional clustering; the live call is a per-session i.i.d. classifier. There is no latent state and no regime persistence anywhere in the model.

### Layer 3 — Online filtering & cold-start stability

| Spec item | Repo state | Evidence | Verdict |
|---|---|---|---|
| No full-sample smoothing / no Viterbi for live calls | Structurally impossible: the engine builds features from bars up to the checkpoint index and applies a **frozen** scaler + **frozen** model | [daytype_engine.py:180](core/state/daytype_engine.py:180)-195, [:339](core/state/daytype_engine.py:339)-360 | **MATCH — intent met, different mechanism** |
| Filtered (not smoothed) state estimate `xi_{t\|t}` | Equivalent in spirit: `predict_proba` on information available at the checkpoint; `regime_confidence` is that max probability | [daytype_engine.py:353](core/state/daytype_engine.py:353), [source.py:100](strategies/nifty_shield_v1/source.py:100)-114 | **MATCH (in spirit; not a Hamilton filter)** |
| No lookahead in the trailing gate | `vix_percentile.percentile()` excludes `asof` from its own window and returns `None` — not a default — on a short window | [vix_percentile.py:76](scripts/daytype/vix_percentile.py:76)-101 | **MATCH — stricter than the spec asks** |
| Label switching prevented on refit | **Not prevented by constraint — prevented by never refitting.** `CLUSTER_NAMES = {0: Choppy, 1: BullTrend, 2: BearTrend}` is a hardcoded post-hoc mapping; nothing enforces a monotone sigma ordering | [train_daytype_classifier.py:99](scripts/daytype/train_daytype_classifier.py:99)-103 | **DIFFERENT — freeze, not constraint** |
| Refit discipline | **No automated refit path exists.** `cluster_day_types.py` / `train_daytype_classifier.py` are referenced only by docs and by error messages — never invoked by the orchestrator, the EOD chain, or any scheduled job. Every published fact carries `(model_hash, regime_fact_version, trained_on, produced_by)` | [publish_facts.py:44](scripts/daytype/publish_facts.py:44)-71, [:163](scripts/daytype/publish_facts.py:163)-230 | **MATCH — arguably stronger than monotonicity** |

**Layer 3 summary.** The spec's flaws #1 (label switching) and #2 (lag) are **not live defects here**. Label switching is neutralised because the artifacts are frozen and provenance-stamped; lag does not bite because the inputs are intraday partials, not trailing moving averages. What the freeze cannot do is survive the day someone retrains — see Finding B.

---

## 2. Findings that outrank the spec's list

Repo-specific; none appear on the submitted checklist. Ranked by weight.

### Finding A — Horizon mismatch: trained on the full session, traded on the quiet tail (HIGH)

The label is a **full-session** KMeans archetype; the strategy opens at 13:00 and closes at 15:15. The model is trained on one horizon and consumed on another, and the traded horizon is the quietest part of the day — median |13:00→15:15| move 10.6 pts (0.044% of index), median range 47.9 pts (`NIFTY_SHIELD_REGIME_AND_STRUCTURE_AUDIT.md` §2.2).

Counterweight, cited at its own scope: `diagnose_regime_horizon.py` over **1,606 out-of-sample sessions** finds the 13:00 call *does* separate direction over its forward window — BullTrend minus BearTrend = **+0.255 pp**, bootstrap 95% CI [+0.197, +0.312], excluding zero. That is evidence of **directional separation over the forward window**, not general validation of the regime model, and it does not dissolve the mismatch: a label defined over 09:15–15:29 is still not the quantity a 13:00–15:15 structure is exposed to.

### Finding B — The label generator is not reproducible (HIGH)

`cluster_day_types.py` persists `cluster_labels.csv`, `cluster_centroids.csv`, `pca_variance.csv` and a text summary — but **never pickles the scaler, the PCA, or the KMeans object**. Consequences:

- The target definition cannot be re-derived. The live audit had to fall back to a 14-D z-scored nearest-centroid **proxy**, and disagreement between proxy and trained label cannot be split into model error and proxy error (`..._AUDIT.md` §2.1).
- Any monotonic-anchoring constraint the spec proposes is unenforceable on a fit that cannot be reproduced. **Reproducibility precedes anchoring.**

This is the label-stability finding that actually matters here — and it is a different one from the spec's.

### Finding C — The KMeans fit that defines the target spans the classifier's val and holdout years (MEDIUM, disclosure)

`load_features()` concatenates `range(2012, 2026)` → the panel is **2012–2025** ([cluster_day_types.py:97](scripts/daytype/cluster_day_types.py:97)-99), and `select_k` fits KMeans on the whole matrix ([:194](scripts/daytype/cluster_day_types.py:194)-209). `cluster_labels.csv` runs **2012-01-04 → 2025-12-31** (3,413 sessions). The shipped classifier is `train_thru=2023` → **val 2024, holdout 2025** ([train_daytype_classifier.py:119](scripts/daytype/train_daytype_classifier.py:119)-129; `models/daytype/logistic_13pm_prod/metadata.json`).

So holdout accuracy is measured against labels defined by an unsupervised fit that **saw the holdout year**. Tolerable for a taxonomy — the label is a description, not a forecast — but it is a real optimism channel and is currently undisclosed in the model metadata.

### Finding D — `subperiod_stability` reports a period it did not test (LOW, but it misstates evidence)

The masks are `year <= 2020` / `year >= 2021` ([cluster_day_types.py:255](scripts/daytype/cluster_day_types.py:255)-256), while the docstring says "early (2023-24) and late (2025-26)" and the console line prints **"Subperiod centroid similarity (2023-24 vs 2025-26)"** ([:400](scripts/daytype/cluster_day_types.py:400)). The number is a 2012–2020 vs 2021–2025 comparison labelled as a 2023–2026 one. It is not written to `cluster_summary.txt`, so the stability claim exists only in stdout — where it is wrong about its own window.

### Finding E — The live regime path depends on undeclared dependencies (MEDIUM)

`daytype_engine.py` unpickles `model.pkl` / `scaler.pkl`, which are **scikit-learn** objects (LightGBM boosters for the `lgbm_*` variants); the clustering script additionally needs `scipy`. Neither `requirements.txt` nor `pyproject.toml` declares `scikit-learn`, `scipy`, or `lightgbm` (this machine has sklearn 1.8.0, scipy 1.17.0). A pickle is version-coupled to the library that wrote it, and `model_hash` covers the **pickle bytes**, not the unpickling library version — so a clean environment rebuild can change or break the live 13:00 regime fact without moving any value the provenance triple tracks.

### Finding F — `vix_percentile.refresh()` is still not wired into the EOD chain (known-open)

The module docstring calls `refresh()` "an explicit maintenance step for the EOD chain", but nothing calls it: the only references outside the module are the read path at [publish_live_fact.py:39](scripts/daytype/publish_live_fact.py:39),257, and the open item already logged at `NIFTY_SHIELD_REMEDIATION_2026-09-08.md` §7. Until it is wired the percentile window ages, and the gate degrades to "unavailable" → calmest branch. Recorded for completeness, not as a new finding.

---

## 3. Scorecard

| Layer | Item | Verdict |
|---|---|---|
| L1 | Range-based / non-close-to-close vol | PARTIAL (ATR + range family, not GK/Parkinson) |
| L1 | Volatility clustering | MATCH |
| L1 | Trend efficiency | PARTIAL (linreg R², HH/LL, TWAP crossings — not Kaufman ER) |
| L1 | Cross-asset (BankNifty) | MATCH |
| L1 | India VIX level + trailing percentile | MATCH |
| L1 | VIX term spread / 20d-60d RV spread | ABSENT |
| L1 | USD/INR, 10Y G-Sec | ABSENT |
| L2 | Non-i.i.d. / latent memory | ABSENT |
| L2 | MS-AR / transition matrix | ABSENT |
| L2 | Wasserstein distribution-shift monitor | ABSENT |
| L2 | "Not vanilla clustering" | DIFFERENT — is KMeans, but over structural PCA features |
| L3 | Forward-only, no smoothing in live | MATCH |
| L3 | Filtered probability as confidence | MATCH (in spirit) |
| L3 | No-lookahead trailing gate | MATCH |
| L3 | Label-switching prevention | DIFFERENT — by freeze + provenance, not by constraint |

**Counts:** MATCH 6 · PARTIAL 2 · DIFFERENT 3 · ABSENT 5.

---

## 4. Recommendations, ranked

Nothing below is implemented. Ranked by expected value **given this repo's constraints**, not by the spec's ordering.

1. **Fix the reproducibility gap (Finding B) first.** Persist the scaler, PCA and KMeans objects from `cluster_day_types.py` with a hash. Cheap, no research budget, and it is a precondition for everything else here — including the spec's monotonic anchoring, which cannot be enforced on a fit that cannot be reproduced.
2. **Declare `scikit-learn` / `scipy` / `lightgbm` with pins, and fold the sklearn version into fact provenance (Finding E).** Also cheap; closes a silent-drift channel on a live production fact.
3. **Correct or delete the mislabelled subperiod-stability print (Finding D).** One line.
4. **Disclose the label-fit / holdout overlap in model metadata (Finding C).** Documentation, not a re-run.
5. **Resolve the horizon mismatch (Finding A) — the only item with real research weight.** Two honest options: (a) re-label on the traded horizon (13:00→15:15 archetypes) and retrain, or (b) keep the full-session label and state explicitly that the strategy consumes it as a *directional prior*, which is what the +0.255 pp diagnostic supports and no more. Option (a) is a new construct, not a tweak.
6. ~~**The spec's Layer-2 items are the lowest-value additions here — and the cheap first step is not to build one.**~~ **RUN 2026-09-09 — see `REGIME_TRANSITION_DIAGNOSTIC.md`.** The empirical transition matrix over all 3,409 usable session pairs shows **no persistence**: max diagonal excess **+0.014**, expected state durations indistinguishable from the independence baseline (1.86 / 1.33 / 1.37 vs 1.86 / 1.39 / 1.34), and only **15.2%** of the chi-square comes from diagonal cells. The dependence that exists is weak one-step **rotation**, not persistence (BearTrend→BullTrend and BullTrend→Choppy above chance), and it decays by lag 2 (Cramér's V 0.0698 → 0.0372). **A Markov-switching layer over these labels has essentially no persistence to model.** The pinned rule returns INCONCLUSIVE on the letter (V 0.0698 > the 0.05 kill threshold) because V picks up the off-diagonal rotation; on the question the recommendation actually asked — do day-types persist — the answer is no.
7. **`W2` (30d vs 252d) as a *monitor*, not a classifier**, is the one Layer-2 idea that could earn its place cheaply: it would flag when the frozen 2012–2023 model is being served into a data-generating process it was never fit on. That is a live risk created by the freeze-instead-of-refit design.
8. **USD/INR + G-Sec ingestion** (the real Layer-1 gap) is a substrate task with no current consumer. Do it only if item 5 or 7 creates one.

**Routing is an operator decision and this report does not make it.** Items 1–4 are hygiene on an existing production path. Item 5 under option (a) is a **new construct** — a re-labelled, retrained day-type model — and would face this repo's own demonstrability arithmetic before any window is spent. Whether that routes through the MM12.5 promotion pipeline (safety / forward-paper, as NiftyShield adoption did) or through research/RFA depends on whether it is treated as a change to a live strategy input or as a new research candidate.

---

## 5. Evidence index

| Claim | File |
|---|---|
| Feature blocks A–G; ATR, vol clustering, linreg R² | `core/analytics/day_features.py` |
| Winsorize → scale → PCA → KMeans; k-selection; stability tests | `scripts/daytype/cluster_day_types.py` |
| Logistic + LightGBM checkpoint classifiers; splits; `CLUSTER_NAMES` | `scripts/daytype/train_daytype_classifier.py` |
| Live serving, frozen pickles, Block H cross-asset | `core/state/daytype_engine.py` |
| Fact provenance (`model_hash`, `regime_fact_version`, `trained_on`) | `scripts/daytype/publish_facts.py` |
| Live 13:00 fact, intraday VIX, driver hook | `scripts/daytype/publish_live_fact.py` |
| Trailing VIX percentile, `asof`-excluded window | `scripts/daytype/vix_percentile.py` |
| Strategy consumption of regime + confidence + VIX percentile | `strategies/nifty_shield_v1/source.py`, `structures.py`, `config.py` |
| Shipped model metadata (`train_thru=2023`, 38 features, Block A excluded) | `models/daytype/logistic_13pm_prod/metadata.json` |
| Horizon mismatch, ledger, proxy-label caveat | `docs/reports/index_research/NIFTY_SHIELD_REGIME_AND_STRUCTURE_AUDIT.md` |
| +0.255 pp forward-window separation, n = 1,606 | `docs/reports/index_research/NIFTY_SHIELD_REGIME_HORIZON_DIAGNOSTIC.md` |
| Prior HMM generation, dropped at SALVAGE | `docs/reports/strategies/DRA_TECHNICAL_DOSSIER.md` |
| `vix_percentile.refresh()` EOD wiring open item | `docs/reports/index_research/NIFTY_SHIELD_REMEDIATION_2026-09-08.md` §7 |
