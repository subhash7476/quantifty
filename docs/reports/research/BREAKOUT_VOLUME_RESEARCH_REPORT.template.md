# M3a × M5b — Range Breakout + Abnormal-Volume Confirmation — Research Report (BKV-1)

**Question.** When an individual stock breaks out of a multi-day closing range, does unusually high same-day volume distinguish breakouts that continue from breakouts that fail?
**Protocol:** `BREAKOUT_VOLUME_PROTOCOL.md` v1.0, frozen at commit `84fcd99` (record `breakout_volume_FREEZE.json`); **no forward return existed before that commit.** Two logged verifier/output amendments followed (A1, A2 — §7.4); neither touched the engine, the analysis, the classification rule or any result.
**Branch / worktree:** `research/breakout-volume`, `F:\Nifty_bkv`. **Every number below is rendered by `scripts/breakout_vol/build_report.py` from the files in `docs/reports/research/breakout_volume/`;** none is typed by hand.

---

## 1. Executive summary

* **Final classification: C5 — construct-scoped** (the pre-registered criterion was tested on data and failed). `classification.json` = {{CLASSIFICATION}}. No defect trigger fired. **The HOLDOUT (2023-01 → 2026-09) was never read** — the protocol stops at a failed VAL — so no window was spent and the operator question about spending it never arose.
* **Primary test.** 8 pre-declared cells (N ∈ {20, 63} × H ∈ {5, 20} × up/down). The statistic is the paired within-date difference in direction-signed, market-excess forward return between breakouts **with** abnormal volume (B) and **without** (C). **0 of 8 cells is confirmed in VAL** (Holm-8 adjusted p = 1.000 in every cell; smallest unadjusted one-sided p = 0.159, down-side N=20 H=5, d̄ = +39 bp, 95 % CI [−36, +125] bp).
* **The up-side sign is opposite to the hypothesis in every cell and both windows.** Volume-confirmed *upside* breakouts continued *less* than unconfirmed ones (VAL d̄ = −52, −104, −6, −24 bp; TRAIN −10, −87, −39, −80 bp). The pre-registered test is one-sided in the continuation direction, so this is a **distinct finding, never counted as support**, and no test of it was pre-registered (the two-sided p for the N=20 H=5 cell would be ≈ 0.05 unadjusted).
* **Power is the binding constraint, and it is disclosed as such.** The minimum detectable effect (80 % power, one-sided) is 67–253 bp per cell in VAL (§5). A null here means *this design cannot demonstrate a volume premium smaller than that*; it does **not** show that volume is irrelevant.
* **Auditability.** All six independent checks pass in both stages (§6): a pure-SQL re-derivation matches the engine on **19,761 (TRAIN) and 17,067 (VAL) events with zero exceptions** (max |Δf| ≈ 2e-12 bp); a raw as-traded rebuild, a hand Newey–West + `statsmodels` kernel, accounting identities and fee arithmetic agree. Nothing is marked NOT AUDITABLE.
* **Economics (descriptive).** Round-trip statutory + DP cost ≈ 22 bp of notional before slippage. The B arm on the up-side is negative net of cost in all four cells; the down-side B arm shows positive short-proxy nets in VAL but is not distinguishable from C and flips sign across windows (§8).

## 2. Frozen research question and protocol

See `BREAKOUT_VOLUME_PROTOCOL.md`. Pinned before any result: closing-range breakout `C_t > max(C_{t−N..t−1})` (N = 20, 63; mirror for downside), **onset only** (no same-side breakout flag in the prior 20 sessions), abnormal volume `V_t ≥ 2 × median(V_{t−20..t−1})`, arms A = B ⊔ C and the control D, entry at the adjusted open of t+1, exit at the close of t+H (H = 5, 20), estimand `f = sign·(R − R_m)` in bp with `R_m` the equal-weight mean over the PIT top-200 members with a resolved window, paired-by-date contrast, calendar-aware Newey–West with lag H, Holm over 8 cells. Vault vocabulary mapping (C4–C9) fixed in protocol §10.

## 3. Exact signal / event definitions

For entity *e*, regular-calendar session *t*, adjusted OHLCV:

| Object | Formula (units) |
|---|---|
| Range level | `Mx_N(t) = max(C_{t−N}…C_{t−1})`, `Mn_N(t) = min(C_{t−N}…C_{t−1})` (price) |
| Breakout | `UP = [C_t > Mx_N]`, `DN = [C_t < Mn_N]` |
| Onset | `UP ∧ (UP_s = 0 ∀ s∈[t−20, t−1])` (same for DN) — uses breakout flags only, never volume |
| Abnormal volume | `AV = V_t / median(V_{t−20}…V_{t−1})`, `ABN = [AV ≥ 2.0]` (shares ratio) |
| Arms | B = onset ∧ ABN; C = onset ∧ ¬ABN; A = B ⊔ C; D = ABN ∧ ¬UP ∧ ¬DN ∧ (no ABN in t−20…t−1), signed by sign(C_t − C_{t−1}) |
| Return | `R = C_{t+H}/O_{t+1} − 1`; `R_m` = mean R over members at t with a resolved window (≥ 100 names) |
| Estimand | `f = sign·(R − R_m)·10⁴` bp, sign = +1 up/D_up, −1 down/D_dn; continuation > 0 |
| Test | `d(t) = m_B(t) − m_C(t)` on dates with both arms; d̄; SE from calendar-aware NW, lag = H; one-sided Student-t, n−1 df; Holm-8 |

## 4. Data provenance and sample construction

* **Store and snapshot.** `equity_bhavcopy_adjusted` (CA-adjusted OHLC, volume divided by the cumulative bonus/split factor). One hashed snapshot of 1,341,582 rows ≤ 2022-12-30 (the store runs to 2026-09-29; fence non-vacuous): panel `46de7d4d…`, calendar `73addee2…`, membership `db87add8…` (`manifest_dev.json`, in the freeze record).
* **Universe.** PSB/CSMP point-in-time top-200 by trailing-6-month median turnover, monthly rebalance; membership at *t* = the **last rebalance strictly before t**; entity by `universe_eligibility`; delisted names stay while listed.
* **Calendar.** 26 snapshot-span dates removed by rule (weekends, Muhurat/short sessions by turnover < 0.40 × neighbourhood, n_symbols < 200 — incl. 2016-04-19 which the store lists as `unresolved`, and 2017-07-10 whose cause is unverified); list in `breakout_volume_diagnostics_outcome_free.json`. The rule was checked outcome-free against a trailing median: identical dates.
* **Sessions.** TRAIN 2012-01-02 → 2017-12-29 = 1,474; VAL 2018-01-01 → 2022-12-30 = 1,233.
* **Eligibility.** Valid rows on all 84 sessions t−83…t and PIT member. Eligible name-days: TRAIN 290,347; VAL 246,287 (of 290,600 / 246,600 member-days — 99.9 %).
* **Funnel (reconciliation).** Breakout flags before the onset rule vs events after it (counts only, from the outcome-free diagnostics): TRAIN N20 up 36,408 → 4,533; VAL N20 up 30,248 → 3,775. Cell-level funnel below; every row satisfies *formed = resolved + dropped + window-beyond-stage + no-benchmark* and *A = B + C* (asserted in code and re-checked by VP4).

**VAL funnel**

{{FUNNEL_VAL}}

**TRAIN funnel**

{{FUNNEL_TRAIN}}

## 5. Primary results

Units: bp of entry-open notional, direction-signed so that continuation is positive, net of the same-window equal-weight universe return. m_B and m_C are the means of the per-date cohort means over each arm's own dates, so m_B − m_C differs slightly from d̄, which is the mean of the per-date differences over the paired dates only (the *n_B*, *n_C* columns count events). MDE80 = (z₀.₉₅ + z₀.₈₀)·SE = 2.486·SE.

### 5.1 VAL — confirmatory (Holm over the 8 cells)

{{PRIMARY_VAL}}

**Reading.** No cell has Holm-adjusted p below 0.05; none is confirmed (classifier: `val_confirmed = []`). Every up-side cell has d̄ < 0. The down-side sign is positive at N=20 and mixed at N=63. Every 95 % CI contains zero except the N=20 H=5 up cell, whose CI lies entirely below zero (the wrong-signed direction). MDEs (67–253 bp) exceed the point estimates in all cells: the design has power only against sizeable effects.

### 5.2 TRAIN — descriptive only (no decision, nothing pinned or changed on it)

{{PRIMARY_TRAIN}}

TRAIN and VAL agree on sign in 6 of 8 cells and on the up-side sign in all four; neither window shows a cell with a positive, significant B − C.

### 5.3 Secondary and control quantities (report-only, unadjusted, never gates)

Arm means are of per-date cohort means (bp, market-excess) with NW t against zero; the event-weighted contrast, the two-way (entity × date) clustered event contrast, and the within-date permutation p are second and third estimators of the same B − C statistic (§6 cross-checks). The attrition-bound column recomputes d̄ after replacing dropped/terminal events by the pre-specified worst values.

**VAL**

{{SECONDARY_VAL}}

**TRAIN**

{{SECONDARY_TRAIN}}

**Reading.** (i) The three estimators of B − C (cohort-paired, event-weighted, two-way-clustered) agree in sign in every VAL cell except the N=63 H=5 *up* cell (−6.1 vs −2.1 vs +8.2 bp — all ≈ 0). (ii) In VAL the permutation p and the NW p are both > 0.05 in all eight cells (no disagreement about the 0.05 line); the two-way-clustered event p is also > 0.05 everywhere (closest: 0.066 and 0.073 at down N=20). In TRAIN (descriptive) one cell differs: down N=20 H=5 has clustered-event p = 0.018 against NW p = 0.129 and permutation p = 0.119. (iii) The attrition bound moves nothing: dropped/terminal events number single digits per cell in VAL (funnel table). (iv) The control D (abnormal volume without a breakout, signed by the day's direction) shows no reliable continuation at any cell in VAL (|t| ≤ 1.96, and the only |t| near 2 is negative). (v) Breakouts as such (A) do not reliably continue in the market-excess sense; the one A cell with t > 2 (down-side N=20 H=5, +25.5 bp) is unadjusted and one of the 32 arm-cells tested (4 arms × 8 cells).

## 6. Independent verification (two methods per headline number; disagreement ⇒ STOP)

{{VERIFICATION}}

**How each headline number is reproduced.** (1) *Event-level:* VP1 re-derives every event's existence, arm, AV, entry/exit prices, R, R_m and f in **pure SQL window functions** from the same snapshot (own calendar, own membership, own flag/onset logic, own terminal rule, own benchmark) and matches the numpy engine with zero exceptions. (2) *Raw-data level:* VP2 rebuilds seeded events from the RAW as-traded table with plain Python loops (Mx, the 10th/11th sorted volumes, AV, entry, exit, R) — scale-free quantities only, because adjusted price *levels* legitimately differ from raw ones for any name with a later bonus/split. (3) *Statistic level:* VP3 recomputes d̄, SE, t, p for all 16 cells from the cohort ledger by (a) a dictionary-arithmetic pure-Python Newey–West and (b) `statsmodels.stats.sandwich_covariance.S_hac_simple` on the zero-filled demeaned series, and rebuilds the cohort means from the event ledger; all agree to ≤ 1e-12. (4) *Alternative inference:* a within-date permutation test (5,000 draws) and a two-way-clustered event contrast are reported beside the NW statistic; in VAL none disagrees on the 0.05 line (one TRAIN cell does, §5.3). (5) *Data level:* adjusted volume equals raw volume on all sampled rows of entities with no bonus/split; for 3,000 sampled rows of CA entities the adjusted close and volume are rebuilt from `adjustment_factors` (3,000/3,000); an independent turnover-based (CA-invariant) abnormal-volume flag agrees with the volume flag on ≈ 97 % of breakouts (the residue is the price-move term: turnover = price × volume). (6) *Fees:* hand arithmetic = library.

## 7. Failure / leakage / bias audit

### 7.1 Audit table (control → evidence)

| Risk | Control | Evidence |
|---|---|---|
| Look-ahead in signal | flags use t−N…t only; entry = open of t+1; test perturbs everything after t and shows events ≤ t unchanged | `test_signal_is_causal…`; VP1 |
| Volume alignment | median over t−20…t−1 (today excluded); one row per (entity, date) for OHLC and V; test: ×1000 today's volume leaves its baseline unchanged | `test_volume_baseline_excludes_today`; VP1/VP2 |
| Price/volume timestamp mismatch | both come from the same daily row on the same regular-calendar index | VP2 (raw rows) |
| Info from t used as if earlier | none: the signal is a close-of-t object; earliest trade is the t+1 open; the overnight gap is a disclosed part of R (decomposition in §9.4) | protocol §6 |
| Survivorship / universe changes | PIT monthly top-200 by trailing turnover; membership strictly before t; delisted names kept while listed; terminal-price rule; attrition bound | §4; dropped/terminal events: single digits per cell |
| Overlapping events | onset-only with a 20-session quiet period = longest H; non-declustered variant (R3) reported separately | §9 |
| Event clustering | per-date cohort observation; HAC lag H; permutation & clustered checks | §5.3 |
| Duplicated observations | unique (entity, t, N, kind) (0 duplicates); one listing per entity-date (0 duplicate listings in the snapshot) | VP4 |
| Weighting mistakes | cohort-weighted primary reported beside event-weighted contrast; A = B ⊔ C identity | §5.3, VP4 |
| Denominator / sample-count errors | every cell reconciles by identity; benchmark identity Σ(R − R_m) = 0 shown on the worked dates | §4, §10 |
| Corporate actions | certified adjusted view for prices and volume; {{CA_SHARE}} % of events have a CA factor in [t−83, exit+1] — results without them are in R4 | §9 |
| Special / short sessions | rule-based removal; non-causal-median sensitivity checked (identical dates) | §4 |
| Cost assumptions | existing delivery-fee model both legs; κ scenarios, break-even κ reported; short leg is a cost-scale proxy | §8 |
| Multiple testing / parameter selection | 8-cell Holm family; nothing tuned on TRAIN; post-primary variants labelled non-classifying | §5, §9 |

### 7.2 Things that could still bias the result (stated, not corrected)

* **Not beta-adjusted.** Excess is over an equal-weight universe return. Volume-flagged breakouts may carry different beta; B − C only partly nets it.
* **Entry at the open of t+1** can be unfillable when a name is locked at a circuit; not modelled. Entry is the auction-opening print, not a filled price.
* **Top-200 turnover universe only** (large/liquid). Nothing is said about small caps, where volume signals and breakouts behave differently.
* **B days are larger-move days** by construction (declared confound R9; §9.5).
* **Prior exposure (GR-1.3).** 2012–22 equity EOD is signal-spent by PSB/CSMP/Gann/MRLC; VAL is a consistency check, not naive.
* **Cohort weighting** gives each formation date equal weight regardless of how many events it has; the event-weighted contrast is reported beside it and reaches the same conclusions.

### 7.3 Pre-run predictions (protocol §14) — scorecard

| Prediction | Outcome |
|---|---|
| A = B ⊔ C exactly in every cell | ✓ (all 16 cell-rows, both stages) |
| Σ(R − R_m) = 0 to machine precision on every date | ✓ (worked example: 1.4e-15) |
| Outcome-free event counts reproduce | ✓ (e.g. TRAIN N20 up B/C formed 1,800/2,733 in diagnostics; funnel shows formed 1,800 / 2,733 before containment) |
| VP1 agrees with the ledger with zero exceptions | ✓ (19,761 and 17,067 events) |
| < 1 of 8 VAL cells confirms under H0; modal outcome C5 | ✓ (0 of 8; C5) |

### 7.4 Deviations and amendments (all logged)

* **A1** — VP5 "clean" names were defined by symbol, but adjustment is per entity; run on TRAIN it failed on 103/4,000 rows, all 11 offending entities carrying a corporate action under a *renamed* symbol (PHILIPCARB→PCBL etc.). The verifier population (VP5, and the VP2 skip rule) was corrected to entity level and tested on a synthetic rename chain. No engine/analysis code and no TRAIN number changed.
* **A2** — `classification.json` failed to serialise tuple keys; output-only fix, VAL cell table byte-identical.
* **Departure from the advisor's suggestion:** the HOLDOUT-spend question was not put to the operator up front; it is only relevant if VAL confirms, which it did not.

## 8. Economic / cost analysis (descriptive; the economic gate is conditional on a HOLDOUT confirmation and was not reached)

Round trip on ₹5,00,000: BUY at the entry-open date + SELL at the exit date, priced by the existing `delivery_fees.py` (STT 0.1 % per leg, exchange, SEBI, stamp on the buy leg, GST, DP on the sell) = ≈ 22 bp of notional (hand-checked in §10) plus slippage κ per side. Both directions are priced on the long-side delivery schedule as a conservative cost-scale proxy (a multi-day cash-delivery short is not implementable; no short fee schedule is invented — the down-side is mechanism evidence, not a strategy). "Gross raw B" is the un-netted direction-signed mean return (it includes market drift).

**VAL — B arm, event-weighted net (bp) by slippage scenario**

{{COSTS_VAL}}

**TRAIN — B arm**

{{COSTS_TRAIN}}

**Reading.** Up-side B is negative net of cost in every cell and every κ (even at κ = 0) — the gross raw mean is ≤ +7 bp against a 22 bp fee. Down-side B shows positive short-proxy nets in VAL (24–164 bp at κ = 5), but (i) it is not distinguishable from the C arm (§5.1), (ii) it is not stable — TRAIN B raw signed means at down/N=20 are +35 bp (H=5) and −37 bp (H=20) — and (iii) a multi-day cash short is not implementable, so this is not an economic finding. The break-even κ is large and positive only where the raw mean is large.

## 9. Post-primary disclosure analyses (declared in protocol §13; **cannot change the label or be promoted**)

### 9.1 Variants (VAL; one-sided p of B − C)

{{VARIANTS}}

Cell-level d̄ (VAL, bp):

{{VARIANT_CELLS}}

Two down-side cells reach unadjusted p < 0.05 **only** under the AV ≥ 3.0 variant (N=20 H=5 p = 0.043; N=63 H=5 p = 0.028). That is 2 of 56 variant cells (chance expectation ≈ 2.8 at α = 0.05), it appears in one of seven variants, it was not the primary threshold, and it is exactly the shape the protocol pre-declares non-promotable (threshold chosen after the result). **Not promoted; refused as forking paths.** The non-declustered variant (R3) is negative in 7 of 8 cells (+1 bp in the eighth), consistent with the look-ahead-weighting artefact noted in the protocol for persistence-defined events.

### 9.2 By calendar year (VAL, H = 5, B − C in bp)

{{BY_YEAR}}

Year-to-year sign changes are large; no cell is stable across years.

### 9.3 Breakout-depth terciles (R9; cuts fixed once per N × side from pooled TRAIN ∪ VAL events)

{{TERCILES}}

**Confound check.** B share rises steeply with depth (e.g. up N=20: 21 % → 30 % → 62 %), confirming that abnormal-volume breakouts are the deep ones. Within terciles, B − C is not significantly positive anywhere (largest positive t = 1.25, up N=63 H=5 deepest tercile); the largest |t| is negative (−1.96, up N=20 H=20 deepest tercile). So the wrong-signed pooled up-side result is not removed by conditioning on depth.

### 9.4 Overnight gap vs post-open drift (VAL, raw direction-signed means, bp)

{{GAP}}

The volume-confirmed up-side breakouts gap more (overnight-gap component B > C) and then drift *less* after the open (post-open drift B − C ≈ −81 bp at H = 5, N=20) — the continuation that exists is captured by the open, not after it.

## 10. Arithmetic / reconstruction ledger

Everything below is reproduced from raw rows and hand arithmetic; the files are in `docs/reports/research/breakout_volume/`:

| Ledger | File | Grain |
|---|---|---|
| Event ledger (every input to every f) | `events_{TRAIN,VAL}.csv.gz` | 1 row per (entity, session, N, kind) — signal quantities, entry/exit sessions, R, R_m, f, raw, status |
| Cohort ledger | `cohort_{TRAIN,VAL}.csv` | 1 row per (cell, formation date): n_B, n_C, m_B, m_C, d |
| Benchmark ledger | `bench_{TRAIN,VAL}.csv` | R_m and member count per (date, H) |
| Cell tables | `cells_*.csv` | every statistic in §5 |
| Cost tables | `costs_*.csv` | per arm, per κ |
| Reconciliation | `accounting_*.json` | sample funnel per cell |
| Verification | `verification_*.json`, `vp2_raw_sample_*.csv` | the six checks; sampled raw rebuilds |

**Path from the headline number to the raw observations** (VAL, N=20, H=5, up: d̄ = −52.4 bp): raw bhavcopy rows → adjusted OHLCV (certified view) → per-event `f` (event ledger) → per-date `m_B`, `m_C` (cohort ledger) → `d(t) = m_B − m_C` on 505 paired dates → d̄ → Newey–West SE → t → p. The last three steps and two example events are written out below with real numbers.

{{WORKED}}

## 11. Classification

**Ledger-consistent Vault category: C5 — construct-scoped.** The pre-registered criterion (8-cell paired B − C > 0, Holm-8 in VAL) was tested on data and failed (0 of 8; smallest unadjusted p 0.159). C5 needs a predefined criterion that predates the read — it did (frozen at `84fcd99`).

*Scope of the closure (must always accompany the label):* the construct as specified — closing-range onset breakouts (N = 20, 63) in the PIT top-200 turnover universe, abnormal volume = same-day volume ≥ 2× the prior-20-session median, entry at the next open, holds of 5 and 20 sessions, market-excess continuation returns, 2018–2022 confirmatory window. It does **not** close M3a (range-escape continuation) or M5b (volume-confirmed moves) as mechanisms, and says nothing about other range definitions, thresholds, horizons, universes, event definitions or eras. C6 does not apply (no VAL confirmation), C7–C9 do not apply; C9 is unreachable on this substrate. The HOLDOUT window remains unspent.

**What the data establish.** On 2018–22 top-200 stocks there is no detectable positive difference between the continuation of volume-confirmed and unconfirmed breakouts at the pre-declared specification; on the up-side the point estimates are negative in every cell in both windows.
**What they do not establish.** That volume is irrelevant: the MDE (67–253 bp) means effects of a size plausible for a volume premium (tens of bp) could not have been detected. Nor anything about the unspent 2023-01 → 2026-09 window.

## 12. Recommended next research action

None on this construct. Any change (threshold, range definition, universe, horizon, event definition, the AV ≥ 3.0 down-side pattern) is a **new pre-registration** on a window not already spent; the post-primary tables here are disclosure and cannot seed a rescue. If a successor is ever written, the first design question is demonstrability: the MDE table shows that H = 20 cells are unpowered for any plausible volume effect, which is the same wall the Vault found for monthly cross-sections. Housekeeping: add this experiment to the closure ledger as **M3a × M5b — C5, construct-scoped, EMPIRICALLY TESTED** (M3a and M5b stay open); register the 2012–22 equity-EOD signal read (row Q-7) and note that the 2023+ window was not read.

## 13. Reproducibility

```bash
git worktree add -b research/breakout-volume ../Nifty_bkv origin/main    # then check out the branch commits
python -m scripts.breakout_vol.prep && python -m scripts.breakout_vol.diagnostics
python -m pytest tests/breakout_vol -q                                     # 30 tests incl. synthetic end-to-end with splits/renames
python -m scripts.breakout_vol.freeze                                      # (done at 84fcd99; amends logged in the freeze record)
python -m scripts.breakout_vol.run_stage TRAIN ; python -m scripts.breakout_vol.run_stage VAL
python -m scripts.breakout_vol.verify_independent TRAIN ; python -m scripts.breakout_vol.verify_independent VAL
python -m scripts.breakout_vol.run_stage CLASSIFY
python -m scripts.breakout_vol.post_primary ; python -m scripts.breakout_vol.worked_examples ; python -m scripts.breakout_vol.build_report
```
Determinism: seeded bootstrap (20260930) and permutation (20260931); results reproduce byte-for-byte from the hashed snapshot. Data paths are absolute under `F:/Nifty/data` (the worktree carries no `data/`).
