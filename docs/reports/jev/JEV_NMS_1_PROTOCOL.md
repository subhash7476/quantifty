# JEV-NMS-1 — First Jev Nifty Market-State Experiment: Protocol (FROZEN at F₁)

**Status:** FROZEN at F₁. Nothing in this document may change. Any change voids the run
and requires a new pre-registration with its own prospective window.
**Branch:** `research/jev-nifty-market-state` (dedicated worktree from `main`; no PTMS/GF-10 content).
**Governance:** estimation-only construct, documented under the N200 precedent (U1). No RFA
declaration is filed; the §23 sample-size rule is the feasibility gate.
**Sealed artifacts:** `governance/jev_nms_1/` — templates (`templates/*.json`), pinned
environment (`environment.json`, `requirements-jev.txt`), canonical configuration
(`config.json`). Hashes and F₁ are recorded in `JEV_NMS_1_F1_FREEZE_RECORD.md`.
**Lineage:** feasibility report → proposed protocol → audit 1 → audit 2 → Amendment 1 →
closure R-1..R-5 → closure B-1..B-7 → final approval (all 2026-09-18).

Tags: **[R]** repository convention · **[A]** approved decision · **[D]** disclosure.

---

## 1. Research question [A]
Can Jev probabilistically nowcast the mechanically defined Nifty 50 state over the next
15 minutes `[t, t+15)`, using only information available at timestamp t, in a way that adds
information beyond a deterministic model given exactly the same input? This is a forward
nowcast, not a classification of the current state.

## 2. Hypothesis and disclosures [A]
- **H0:** adding Jev's probabilities to a recalibrated B3 does not reduce multiclass
  log-loss on prospective sessions (ΔLL ≤ 0).
- **H1:** ΔLL > 0, one-sided. A null result is valid.

Disclosures [D]:
1. The experiment tests whether Jev adds information from **nine numerical summaries**. It
   does not establish general market-judgment capability. TypeSafe's Jev 1.13 documentation
   lists weak numerical reasoning ("not a calculator"); a NULL means only that Jev reading
   these summaries adds nothing.
2. Jev's training cutoff is **unknown**. The experiment is not conditioned on obtaining it.
3. Prior repository exposure of 2023+ index 1m data: pair-ratio research; DayType
   structural features and facts; A-track and Analog Path SEALED designation (A retired;
   Analog Path concluded NO at HOLDOUT); NiftyShield and Options-Wall operations. Jev
   pretraining may cover D-fit, D-eval and H-exposed. **Only the prospective set P can
   produce POSITIVE.**
4. Prior evidence leans toward null (Analog Path: path adds nothing beyond return; A-track
   continuation decayed at HOLDOUT).
5. CAS discontinuity: C_prev is the previous session's 15:29 close — the last 1m close
   before 2026-08-03 and the closing-auction print from 2026-08-03. The definition of f2
   shifts at that date.
6. Jev is not told the instrument. Its information channel is the nine fields plus the
   fixed template text.
7. The template does not tell Jev that labels are time-of-day-volatility normalized (§9).
   Any resulting magnitude mismatch is only partly absorbed by the pool recalibration (§16).

## 3. Universe [R]
`NSE_INDEX|Nifty 50` only, from `data/market_data/nse/candles/1m/{date}.duckdb`. The index
slice is certified FAIL-with-register and PTMS certification covers `NSE_EQ` only [D];
known defects are handled by §4 and never repaired or imputed.

## 4. Eligibility [R][A]
A session is eligible only if all hold (the rule is the universe; no hand exclusions, no
imputation):
1. the file exists and the date is a trading day in `core/market/nse_holidays.py`;
2. the first bar's date equals the session date;
3. the first bar is stamped 09:15 (native, start-labelled, per `bar_labeling.labeling_of`);
   any other first stamp is excluded, not converted;
4. the date is not in `SPECIAL_SESSIONS`;
5. exactly one bar for every minute 09:15..14:59 (345 bars), strictly monotonic, no duplicates;
6. every bar through 14:59 has consistent OHLC, all prices > 0, and `is_synthetic = FALSE`;
7. **feed freeze:** no run of ≥ 10 consecutive bars before 15:00 with O=H=L=C and an
   unchanged close;
8. the previous trading session's file has a bar stamped 15:29 with close > 0;
9. the date is not in the defect register (currently 2026-02-25, 2026-03-02).

**R-1 (item 7 materiality).** "Otherwise-eligible" = passing every item except 7. The
100-session development sample is drawn (seed 42) from the otherwise-eligible D-eval set.
Before any scored Jev call, **stop and return to the operator** if (a) item 7 alone excludes
> 2% of otherwise-eligible sessions in D-fit or in D-eval (each separately), or (b) any
item-7-excluded session falls in the drawn 100-session sample. Always report, per set:
otherwise-eligible count, item-7 excluded count and percentage, excluded dates with the
longest frozen run's start and length, and any overlap with the drawn sample — written to
the ledger before any scored call.

## 5. Timestamp grid [A]
t ∈ {10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30}. The earliest
input bar is t−31 ≥ 09:15; the latest label window ends by 15:00, so neither features nor
labels touch the post-CAS flat bars (15:15–15:28) or the 15:29 auction print. Every eligible
session contributes 10 states.

## 6. Input features — the only Jev input [A]
Natural-log returns in basis points.

| # | Field | Definition |
|---|---|---|
| f1 | `minutes_since_open` | t − 09:15 in minutes (integer) |
| f2 | `gap_bp` | ln(O / C_prev) |
| f3 | `ret_open_bp` | ln(P(t) / O) |
| f4 | `ret_15_bp` | ln(P(t) / P(t−15)) |
| f5 | `ret_30_bp` | ln(P(t) / P(t−30)) |
| f6 | `rv_30_bp` | √Σ r_i² over the 30 one-minute returns ending at t |
| f7 | `range_30_bp` | ln(max H / min L) over the bars stamped t−30 … t−1 |
| f8 | `er_30` | \|f5\| / Σ\|r_i\| over the same 30 returns; 0 if the denominator is 0 |
| f9 | `twap_dist_bp` | ln(P(t) / TWAP_t); TWAP_t = mean close of bars stamped 09:15 … t−1 |

Rounding: bp fields to 1 decimal, `er_30` to 3 decimals, f1 integer. The rounded values are
exactly what Jev receives **and** what B2/B3 use. If this definition disagrees with
`compute_checkpoint_features`, this protocol governs.

## 7. Point-in-time construction [A][R]
- A bar stamped m covers [m, m+1). O = open of the 09:15 bar. P(τ) = close of the bar
  stamped τ−1. r_i = ln(C_i / C_{i−1}). C_prev = close of the previous session's 15:29 bar.
- Information set I_t = the bars stamped ≤ t−1 in session D, plus C_prev. Nothing else.
- Historical sets (D-fit, D-eval, H-exposed): states from the canonical store — file D, and
  file D−1 for C_prev only.
- Prospective set P: features come from the **live** payload built from ingestor bars stamped
  ≤ t−1; this payload is **authoritative for both J and B3**. Labels (including their P(t))
  come from the canonical store after the close. A live-vs-canonical P(t) difference
  > 0.5 bp flags the observation; flagged observations stay in the primary analysis and a
  secondary analysis excludes them.
- Required tests: input/label disjointness; isolation (a directory containing only D and D−1
  reproduces the state exactly); request audit (every payload checked field by field
  against I_t and against the sealed template hash).

## 8. Forward label definition [A]
For h ∈ {5, 15, 30} the label window is the bars stamped t … t+h−1 (h returns; the first
from P(t)). R = ln(P(t+h)/P(t)); ER_f = |R| / Σ|r_j| (0 if the denominator is 0);
RV_f = √Σ r_j²; z = R / S_h(t); v = RV_f / S_h(t).

Precedence:
1. `disorderly`: v ≥ V*_h and ER_f < E*_h;
2. `trending_up` / `trending_down`: |z| ≥ Z*_h and ER_f ≥ E*_h, sign of R;
3. `range_bound`: otherwise.

Constants on D-fit only, per horizon, pooled across slots: E*_h = median(ER_f);
Z*_h = 70th percentile of |z|; V*_h = 75th percentile of v. **Base-rate gate:** before any
Jev call, if any class has a D-fit base rate < 5% at h = 15, stop and return to the
operator. [D] `range_bound` is a heterogeneous residual; ER_f is coarse at h = 5.

## 9. Volatility normalization [A]
S_h(t) = median over eligible D-fit sessions of RV_f(t, h), per slot and horizon.
S^trail_h(t) = median over eligible D-fit sessions of realized volatility over [t−h, t)
(used by B1). 60 constants (10 slots × 3 horizons × 2 windows), sealed before any Jev call.
Because the §8 thresholds are D-fit quantiles, labels are invariant to a common rescaling of
all constants; only the relative time-of-day scale matters. The constants are never
re-estimated on D-eval, H-exposed or P. [D] If P's volatility regime differs from D-fit,
base rates shift for all models; the B2/B3 hyperparameter CV inside D-fit uses labels
normalized with the full-D-fit scale (affects model selection only, never evaluation).

## 10. Sets and boundaries [A]
F₁ (protocol freeze) and F₂ (prospective-analysis freeze) are calendar dates.

| Set | Span (by session date) | Role | Jev calls |
|---|---|---|---|
| D-fit | 2023-03-01 → 2024-12-31 | fits §9 scales, §8 constants, B0–B3 | S0 smoke only, never scored; L2 draws |
| D-eval | 2025-01-01 → 2025-12-31 | development evaluation; cross-fitted pool | development (§23); L2 draws |
| H-exposed | 2026-01-01 → the last session dated ≤ F₁ | **EXPOSED / NON-CONFIRMATORY**, deterministic models only | none |
| Buffer | date > F₁ and date ≤ F₂ | excluded from every analysis, fit, evaluation, probe and confirmation set | **none** |
| P | first eligible trading session with date > F₂, for N_P sessions | the only confirmatory set | live |

The sets are disjoint. Single native clock throughout (2023-03-01 is the first native
session after the Feb-2023 hole); strictly temporal order.

## 11. Jev model and request [A]
- Model identifier `jev-1.13.0`, a literal in every request body, never an alias. The
  response `model` field echoes the request; drift is detected by the L5 canaries.
- One four-option Choice question per request, returning a probability per option. No
  abstention request. S_15(t) or any other volatility scale is not sent (U3).
- **Live timing for P:** t = the wall-clock minute boundary at which bar t−1 completes.
  Target send ≤ t+15 s; **hard maximum t+60 s**. A request sent after t+60 s, or whose bar
  t−1 had not arrived by t+60 s, is timing-invalid for that observation. Recorded per call:
  `state_as_of` (last included bar stamp and payload build time), `request_sent_at` (the
  attempt that produced the used response), `response_received_at`, latency, status.
  Target compliance is reported.
- After-close calls for P are prohibited unless TypeSafe confirms in writing that Jev has no
  retrieval or external-information capability. Historical calls (S0, L2, L3, development,
  L5 canaries) are after-the-fact by design and are not P observations.
- A second judgment request is never issued to obtain a different answer.

## 11A. Prompt neutrality [A]
1. One fixed template per horizon; the h = 5/15/30 templates are character-for-character
   identical except for the horizon value.
2. Four classes in the fixed order `trending_up`, `trending_down`, `range_bound`,
   `disorderly`, with neutral descriptions mirroring §8. No numeric thresholds, base rates,
   examples, priors, or time-of-day / "typical" reference.
3. No instrument name, clock time, date, year, month, weekday, session count, index level
   or event identifier in any template or payload.
4. No future information: the payload is f1–f9 from I_t only.
5. No suggestion of an expected class; no leading phrasing; no reference to other states.
6. No adaptive prompting: nothing depends on the state, prior responses or results; no
   rephrased retries.
7. SHA-256 of every template (including L2) sealed before any scored call; the request audit
   checks every request against it.
8. Identical structure for every state: field order, names, units and rounding. Fixed option
   order makes any position bias constant; the pool intercepts c_k absorb it (§16).
9. The S0 smoke test checks parsing only; outputs are not examined for accuracy. Templates
   cannot change after the first Jev call.

Final template text is in §29.

## 12. Caching [A]
- Ordinary cache key = SHA-256 of the canonical request bytes (§12a). Ordinary scored
  requests **never** bypass the cache; a cached key is never re-sent.
- Deliberate L3/L5 bypass records use the record identifier
  `canonical_request_hash + run_id + replicate_index`, are marked **non-authoritative**, and
  replicate 0 is authoritative.
- Transport retries (§25) resend the identical canonical bytes under the same key; only the
  first valid response is stored.
- Stored: request bytes, raw response, parsed probabilities, model identifier, transport
  configuration identifier, the §11 timing fields. The cache is append-only; all analysis
  reads only from it; cache loss makes the run INVALID. The API key is never stored.

### 12a. Canonical request serialization [A]
UTF-8 JSON without insignificant whitespace (`,` `:` separators). Top-level key order
`model`, `state`, `questions`. `state` keys in §6 order. Each question object's keys in order
`type`, `instructions`, `criteria`; criteria keys in their fixed order. Question IDs:
`market_state` (Templates 1–3), `snapshot_year` (Template 4); question IDs are not sent to the
model as content. Numbers are fixed-decimal literals: bp fields 1 decimal, `er_30` 3
decimals, `minutes_since_open` integer; negative zero written as 0 (`0.0` / `0.000`).
Headers are excluded from the canonical bytes.

## 13. Probes [A]
Run only after the §28 pre-Jev sequence is complete.
- **L1 structural [R]:** disjointness, isolation and request-audit tests; a fence guard
  refusing any date outside the active set (and every buffer date); a guard against dates
  beyond those present in the store.
- **L2 memorization:** 90 states (30 per year 2023/2024/2025, §23 draw) with Template 4.
  Fail if a one-sided binomial test against chance 1/3 gives p < 0.01. On failure,
  development results are **CONTAMINATED**, no development conclusion is drawn, and P
  requires explicit operator approval before F₂.
- **L3 repeatability:** 50 states each sent twice (bypass). Report argmax agreement and
  maximum absolute probability difference. Replicate 0 is authoritative. L3 agreement is the
  canary baseline.
- **L4 schema:** invalid or unparseable responses ≤ 2%.
- **L5 drift canary:** the first 20 L3 states in seed order, replayed (bypass) at the start of
  P and after every 60 prospective sessions; agreement = argmax agreement with their L3
  replicate-0 responses. **Halt (INVALID)** if agreement falls more than 10 percentage points
  below the L3 baseline.

## 14. Baselines — fitted on D-fit, then frozen [A]
- **Folds (shared by B2 and B3):** D-fit sessions sorted by date, 5 contiguous
  session-grouped blocks, block sizes differing by at most one session.
- **B0 climatology:** P(label | slot), +1 Laplace smoothing.
- **B1 probabilistic persistence:** P(forward label | trailing label, slot), +1 smoothing;
  trailing label = §8 rule on [t−h, t) with S^trail_h(t) and the same constants.
- **B2:** `sklearn.linear_model.LogisticRegression`, `solver="lbfgs"`, `max_iter=1000`,
  `tol=1e-6`, `OMP_NUM_THREADS=1`; features f1–f9 standardized with D-fit mean/SD; L2 penalty
  and multinomial behaviour are the library defaults for lbfgs with > 2 classes (only `C`,
  `solver`, `max_iter`, `tol` are passed). C ∈ [0.01, 0.1, 1, 10] by mean out-of-fold
  log-loss (ln); ties within 1e-12 → first in list order. Convergence/deprecation warnings
  are written to the ledger.
- **B3 (R-2):** `sklearn.ensemble.HistGradientBoostingClassifier`, `loss="log_loss"`,
  `random_state=42`, `early_stopping=False`, `max_depth=None`, `max_bins=255`,
  `class_weight=None`, `categorical_features=None`, `OMP_NUM_THREADS=1`, on the nine rounded
  features. Grid (lexicographic, first key outermost): `learning_rate` [0.03, 0.10];
  `max_iter` [100, 300]; `max_leaf_nodes` [7, 15]; `min_samples_leaf` [50, 200];
  `l2_regularization` [0.0, 1.0] — 32 combinations. Selected per horizon by mean out-of-fold
  log-loss (ln) on the shared folds; ties within 1e-12 → first in grid order; refit on all
  D-fit. Probabilities mapped by class name, never column position; clipped at ≥ 1e-4 and
  renormalized. The grid is never expanded or altered.

## 15. Jev model J [A]
J = Jev's four-class probability vector, clipped at ≥ 1e-4 and renormalized.

## 16. Combined model B3+J [A]
- B3+J: logit_k = a·ln p_B3,k + b·ln p_J,k + c_k, Σc_k = 0 (5 free parameters), maximum
  likelihood. B3*: the same with b = 0 (B3 recalibrated on the same data; 4 parameters).
  Nested; one extra parameter.
- Development: the 100 development sessions sorted by date into 5 contiguous time blocks
  for cross-fitting; all development ΔLL is out-of-fold. Stop, recorded NULL
  (anti-informative), if b̂ on the full permitted development sample is ≤ 0.
- Prospective: a, b, c_k refit once at F₂ on the full permitted D-eval Jev sample (every
  valid h = 15 observation of the 100 development sessions after paired exclusion), then
  frozen. Nothing is estimated on P.

## 17. Primary metric [A]
At h = 15 on P: ΔLL = session-weighted mean of the session means of (ℓ_B3* − ℓ_B3+J), where
ℓ = −ln p(true class) in nats; positive favours J. **Paired exclusion:** an observation with
an invalid Jev response or invalid timing is removed from both models and counted. Session
weight = number of valid observations.

## 18. Secondary metrics — descriptive, cannot rescue the primary [A]
Multiclass Brier, accuracy, confusion matrices; reliability and ECE (10 bins); J vs each of
B0, B1, B2, B3; per-slot ΔLL; ΔLL at h = 5 and h = 30; primary repeated without seam-flagged
observations; deterministic models on H-exposed (labelled EXPOSED); coverage and AURC (§21);
L3, canary and timing-compliance statistics; N1/N2 (§20).

## 19. Statistical inference [R][A]
Unit = session. Primary: paired moving-block bootstrap over sessions (blocks of 5 contiguous
sessions, 10,000 iterations, seed 42), one-sided 95% lower bound of ΔLL; Newey–West t
(lag 5) and AC₁ reported. Label windows do not overlap at h = 5/15 and only abut at h = 30;
within-session input overlap and volatility clustering are absorbed by session averaging and
block resampling.

## 20. Null procedure [A]
- **Primary empirical null — conditional randomization:** permute Jev probability vectors
  within strata of (timestamp slot × B3* top class × B3* max-probability tercile), pool
  frozen, 1,000 iterations, seed 42; empirical p = share of permuted ΔLL ≥ observed.
  Tercile cuts computed on the full permitted D-eval sample and frozen at F₂.
  **[D] This null is approximate** — residual Jev–B3 dependence remains within strata — so
  the §19 bootstrap carries the validity of the primary claim.
- **N1** (unconditional within-slot session permutation) and **N2** (5-session block
  shift) are descriptive secondary nulls ("J vs noise") only.

## 21. Abstention and coverage [A]
No separate abstention judgment. Confidence = max of J's four class probabilities.
Abstention is not a ground-truth class and does not enter the primary metric. Secondary:
at coverage 100/80/60/40/20% (quantile cuts within the evaluation set), log-loss and
accuracy of J and B3* on the retained subset; risk–coverage curves; **AURC under 0-1 loss and
log-loss**, B3* ranked by its own max probability; descriptive test of whether B3* loss is
higher where J is least confident.

## 22. Multiple testing [R][A]
One confirmatory decision (§27 POSITIVE). Secondary tests Holm-adjusted within family and
descriptive only. Every run (smoke, probes, canaries, development, P) is logged to
`data/jev_market_state/ledger.jsonl` before its results are visible; the full grid is
reported.

## 23. Draws, call budget and sample size [A]
Draws (all seed 42, frozen and recorded before execution):
- **S0:** 5 D-fit sessions; timestamps 10:00 and 14:30.
- **L2:** 30 eligible sessions per calendar year 2023, 2024, 2025; one grid timestamp per
  selected session.
- **Development:** 100 sessions from the otherwise-eligible D-eval set (R-1).
- **Secondary-horizon subset:** the first 30 of those 100 in seed order.
- **L3:** 50 states (drawn from D-fit ∪ D-eval eligible states).

| Stage | Design | Calls |
|---|---|---|
| S0 (unscored) | 5 × 2 | 10 |
| L2 | 90 | 90 |
| L3 (incl. canary baseline) | 50 × 2 | 100 |
| Development primary | 100 × 10, h = 15 | 1,000 |
| Development secondary | 30 × 10 × {5, 30} | 600 |
| **Initial total** | | **1,800** |
| P (separate approval) | 10 × N_P | 1,200–2,500 |
| L5 canaries during P | 20 × (1 + ⌊N_P/60⌋) | 60–100 |

**Sample size (E-9):** at F₂, from development data only, compute n_req for the one-sided
session-level test at α = 0.05, power 0.80, δ = 0.5 × out-of-fold development ΔLL, SD =
development session-level SD of ΔLL. If n_req > 250, F₂ is not established and P is not run
("not demonstrable within budget"). Otherwise N_P = max(120, n_req), frozen at F₂. [D] The
conjunction of bootstrap and conditional null lowers effective power below nominal.

## 24. Stopping rules [A]
1. Before any Jev call: class base rate < 5% at h = 15 → stop; return to operator.
2. Before any scored call: R-1 materiality breach → stop; return statistics.
3. L2 failure → development CONTAMINATED; P requires explicit approval before F₂.
4. Development futility: out-of-fold development ΔLL ≤ 0 → NULL; no F₂.
5. b̂ ≤ 0 → NULL (anti-informative); no F₂.
6. n_req > 250 → NULL (not demonstrable within budget); no F₂.
7. From F₂: fixed sample, no interim performance looks; only data quality, timing and
   canaries are monitored.
8. N_P not reached within **15 months of F₂** → INVALID.
9. Canary halt, or any change to model or transport semantics → halt; INVALID.

## 25. Reproducibility and pinned environment [R][A]
- Sealed at F₁ (`governance/jev_nms_1/config.json`): every §4–§24 constant and rule, the
  B2/B3 configuration, fold rule, draws, template hashes, protocol-document hash,
  environment-record hash, and transport configuration. Sealed at F₂: pool parameters,
  stratum cuts, N_P, and the F₂ environment record.
- **Pinned list** (must be identical at F₁, at F₂ and throughout P): Python, numpy,
  pandas, scikit-learn, scipy, duckdb, OpenSSL, HTTP client, endpoint and API version,
  §12a serialization, timeout and retry policy, model identifier. OS/runtime build details
  are recorded, not pinned; changes are logged and do not invalidate.
- No dependency upgrades during the experiment.
- **Raw-HTTP transport (B-6):** Python standard-library `http.client.HTTPSConnection`
  (persistent keep-alive; version = pinned Python); `POST https://api.typesafe.ai/v1/systemone`
  (API `v1`); headers `Content-Type: application/json`, `Connection: keep-alive`,
  `Authorization: Bearer <TYPESAFE_API_KEY>` (never logged, persisted or hashed). The
  TypeSafe SDK is not installed. Model `jev-1.13.0` in every body.
- **Timeout:** 20 s per attempt (connect + read).
- **Retry policy (transport only):** retry only on connection error, timeout, HTTP 429 or
  HTTP 5xx; never after HTTP 200 (including schema-invalid 200); never on other 4xx. P: at
  most one retry, and only if it starts ≤ t+60 s — a retry that cannot start by t+60 s makes
  the observation timing-invalid. Historical calls: at most three retries, back-off 2/4/8 s.
  Retries resend identical canonical bytes under the same key. A second judgment request is
  never issued to obtain a different answer.
- Seed 42 throughout. Persisted: eligible list, defect register, R-1 statistics, input
  file SHA-256 at read time, features and labels (authoritative), live P payloads, all D-fit
  artifacts with hashes (§28).

## 26. Failure conditions — run INVALID [A]
- Any change to the F₁ configuration seal or a template hash after F₁.
- A request with a model identifier other than `jev-1.13.0`, or request/response identifier
  mismatch.
- Canary halt (L5).
- Cache loss, or any figure not traceable to the cache.
- L1 failure, or a request-audit hit on post-t information.
- Invalid responses > 2%.
- > 10% of P observations timing-invalid (R-3; denominator = 10 × eligible P sessions).
- < 80% of P trading sessions eligible.
- N_P not reached within 15 months of F₂.
- Any evaluation of P before N_P is reached.
- Any after-close P call without TypeSafe's written confirmation.
- The recorded environment at F₂ or during P differs from the F₁ pins in any pinned item
  (B-5).
- Any D-fit fit, hyperparameter selection, template or protocol modification after the
  first Jev call.

## 27. Result classification [A]
- **POSITIVE:** a valid P run with the paired session-block bootstrap one-sided 95% lower
  bound of ΔLL > 0 **and** conditional-randomization p < 0.05. Meaning: Jev adds statistically
  detectable information at h = 15 from nine numerical summaries beyond an identical-input
  deterministic model. No claim about economic value, general market judgment or strategy.
- **NULL:** a valid P run that is not POSITIVE; §24 rules 4, 5 or 6.
- **INVALID:** any §26 condition; §24 rules 8 or 9; and **"INVALID — development
  contaminated / P not authorized"** when L2 fails and prospective approval is not granted
  (F₂ not established).
- §24 rules 1 and 2 are operator returns, not results.
- Nothing from D-fit, D-eval, H-exposed or the buffer can produce POSITIVE.

## 28. Lifecycle [A]
1. **Pre-F₁:** commit this protocol and the sealed artifacts; hash templates, environment
   record, protocol document and configuration; set F₁ (recorded in
   `JEV_NMS_1_F1_FREEZE_RECORD.md`).
2. **After F₁, before any Jev call, in order:** (1) construct and freeze eligibility;
   (2) make all §23 draws; (3) fit §9 scales and §8 thresholds on D-fit, run the base-rate
   gate and the R-1 report; (4) fit and freeze B0–B3 on D-fit; (5) persist and hash the
   artifacts; (6) verify the hashes.
3. **Then:** S0 → L1/L2/L3 → development Jev calls. After the first Jev call, no D-fit
   fitting, hyperparameter selection, template or protocol modification is permitted.
4. **After development:** out-of-fold ΔLL and futility rules; n_req; pool fit on the full
   permitted sample; freeze stratum cuts and N_P; record the environment and verify it
   against the F₁ pins; set **F₂** (administrative/statistical seal, not a performance look).
5. **Buffer:** unused.
6. **P:** from the first eligible session with date > F₂; live calls; canaries at start and
   every 60 sessions; 15-month cap from F₂; no parameter estimated on P.

## 29. Final templates (sealed as `governance/jev_nms_1/templates/*.json`)

Shared state (field order fixed; values per §6 and §12a):
`minutes_since_open`, `gap_bp`, `ret_open_bp`, `ret_15_bp`, `ret_30_bp`, `rv_30_bp`,
`range_30_bp`, `er_30`, `twap_dist_bp`.

**Template 1 (h = 5), instructions:**

> The state is a snapshot of a stock index taken during a regular trading session. It contains only information available at the moment the snapshot was taken. All returns are natural-log returns expressed in basis points (bp). Field meanings: `minutes_since_open` is the number of minutes elapsed since the session open. `gap_bp` is the return from the previous session's closing value to this session's opening value. `ret_open_bp` is the return from this session's opening value to the current value. `ret_15_bp` is the return over the most recent 15 minutes. `ret_30_bp` is the return over the most recent 30 minutes. `rv_30_bp` is the square root of the sum of squared one-minute returns over the most recent 30 minutes. `range_30_bp` is the log ratio of the highest to the lowest value over the most recent 30 minutes. `er_30` is the absolute 30-minute return divided by the sum of absolute one-minute returns over the same 30 minutes; it is 1 when every one-minute move was in the same direction and near 0 when the moves largely cancelled out. `twap_dist_bp` is the return from the average one-minute closing value since the session open to the current value. Based only on this snapshot, which description best fits the index's behavior over the next 5 minutes?

Criteria (fixed order):
- `trending_up`: A substantial net rise over the period that is mostly one-directional.
- `trending_down`: A substantial net fall over the period that is mostly one-directional.
- `range_bound`: No substantial one-directional move and no large back-and-forth turbulence over the period.
- `disorderly`: Large movement back and forth over the period without a consistent direction.

**Template 2 (h = 15)** and **Template 3 (h = 30):** identical to Template 1 except
"next 5 minutes" → "next 15 minutes" / "next 30 minutes".

**Template 4 (L2):** the Template 1 preamble and field definitions verbatim (through
"…to the current value."), then: "Based only on this snapshot, in which calendar year was it
most likely recorded?" Criteria (fixed order): `2023`: The snapshot was recorded in calendar
year 2023. · `2024`: The snapshot was recorded in calendar year 2024. · `2025`: The snapshot
was recorded in calendar year 2025.

The sealed JSON files are authoritative for exact bytes.
