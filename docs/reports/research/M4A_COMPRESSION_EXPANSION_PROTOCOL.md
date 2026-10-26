# M4a-CE — Compression → Expansion: Non-Confirmatory Characterization — Protocol v1.0 (FROZEN)

**Status:** FROZEN at the freeze record `m4a_compress_FREEZE.json`. **No outcome existed before the freeze.** The only
pre-freeze reads were the hashed BKV-1 dev snapshot (prices ≤ 2022-12-30, no later price in it), the outcome-free
diagnostics (`diagnostics.py`; cohort membership and row availability only) and a synthetic-data dry run of the whole
pipeline (`tests/m4a_compress/test_pipeline_dryrun.py`).
**Branch / worktree:** `research/m4a-compression-expansion` in `F:\Nifty_m4a` (cut from `main` `d79a278`; the live
orchestrator checkout `F:\Nifty` stays on `main`).
**Design authority:** `docs/reports/external/M4A_COMPRESSION_EXPANSION_DESIGN_INVENTORY.md` (§9 specification, §10 freeze list).
**Harness:** BKV-1 (`scripts/breakout_vol/`, imported and hashed, never edited). **Governing vocabulary:** closure ledger
C0–C9, GR-1 spent-window rules. **No RFA is created**; the study reports the minimum detectable effect (MDE) per cell.
**The Vault mechanism map and closure ledger are not modified.**

> **This is a GR-1.4 non-confirmatory characterization, not a test that can confirm anything.** TRAIN and VAL are
> signal-spent windows (§3): no result here is a confirmation, no gate is fed, no strategy exists, and no HOLDOUT is read
> (none exists in this package). The run answers one question: *does the mechanism show enough evidence to justify a
> future fresh confirmatory experiment on an unread surface?*

---

## 1. Question and hypothesis

**Question.** Does a low trailing realized-dispersion state contain information about subsequent range expansion,
beyond ordinary volatility persistence?

**Primary hypothesis (per cell c = (h, comparator)).** d̄_c = E over dates[ mean_C(E) − mean_X(E) ] > 0, where C is the
compression cohort (§5), X the comparator cohort (*normal* or *persistence*) formed on the same date, and E the
normalised forward range expansion (§6). **H0: d̄_c ≤ 0.**

*Expected sign under pure persistence is NEGATIVE* (§11): the compression state is defined by a low short-run range
(ATR10) relative to ATR60, and forward range tracks recent range. A wrong-signed cell is therefore the persistence
signature, not evidence about the mechanism; it is reported and never counted as support.

## 2. What the Vault says (unchanged by this study)

MAP v1.1 / CLOSE / LEDGER all hold M4a at **C — fully open**: nothing in the repo or Vault conditions a range expansion
on a prior compression state (inventory §2–§3). N200-HMM Variant B and GEX Stage A forecast the level of volatility and
are not M4a tests. This study does not change any taxonomy entry.

## 3. Prior exposure and window status (disclosed before any read)

* **Equity EOD 2012 → 2022-12-30 is already signal-spent** (register rows Q-1…Q-3, G-S1, MRLC E-3, N200 HMM Q-4, and
  BKV-1 Q-7). Under GR-1.3 a spent window can never be confirmatory. TRAIN and VAL here are therefore *not naive*; a VAL
  pass is a consistency check only. **The HOLDOUT (2023-01-02 → present) is not read and cannot be read by this package.**
* The same panel was used by BKV-1 for a different mechanism (breakout × volume); only its price/volume/membership
  columns are re-used. No BKV-1 outcome is used here. Compression thresholds, windows and horizons were chosen from the
  inventory and standard practice (10/60-session ATR, 252-session percentile, one week / one month), not from any look at
  a forward range on this panel.

## 4. Data and substrate

* **Store / snapshot:** the BKV-1 dev snapshot `data/research/breakout_volume/{panel,calendar,membership}_dev.parquet`
  (adjusted OHLCV from `equity_bhavcopy_adjusted`, entity grain, PIT top-200 by trailing-6-month median turnover, monthly
  rebalance, membership on session t = the last rebalance **strictly before t**, regular-session calendar rule as in BKV-1
  §4). SHA-256 panel `46de7d4d…`, calendar `73addee2…`, membership `db87add8…` — the freeze record re-hashes all three and
  **`panel.load_panel` refuses to load anything whose panel hash is not the BKV-1 one** and anything holding a price after
  2022-12-30. 508 entities, 3,203 regular sessions, 537,200 member name-days.
* **Valid row:** open, high, low, close and volume present and > 0 (the BKV-1 rule, inherited unchanged); every other
  (entity, session) is *missing* — never imputed, never forward-filled.

## 5. Definitions (all information through the close of t; the outcome uses t+1.. only)

Per entity and regular-session index s: H, L, C = adjusted high, low, close; C[s−1] = the close of the **previous session
in the calendar** (if that session has no valid row, every quantity that needs it is missing).

1. **Daily range** `rng_s = (H_s − L_s) / C[s−1]`. **Log return** `r_s = ln(C_s / C[s−1])`.
2. **Compression ratio (primary, D2):** `ATR_10(s) / ATR_60(s)`, `ATR_n(s) = mean(rng_{s−n+1..s})`. Declared robustness (D1):
   `std(r, 10) / std(r, 60)` (sample std, ddof = 1, over the same windows). A ratio whose slow term is 0 is missing.
3. **Trailing percentile.** `pct(t) = #{ s ∈ [t−251, t] : ratio_s ≤ ratio_t } / 252` — the window **ends at t and includes t**;
   ties count as ≤; **every one of the 252 ratios must exist** (no partial windows). Compression: `pct ≤ 0.20`.
   High state: `pct ≥ 0.80`. (Comparisons carry a 1e-12 tolerance so 50/252 is in, 51/252 is out.)
4. **Cohorts on date t** (each requires: PIT member at t **and** `pct(t)` defined):
   * **C — compression onset:** `pct(t) ≤ 0.20` **and** on each of the prior 20 sessions `pct` is defined and `> 0.20`
     (quiet period = max(h, 20) = 20 for both horizons). An unevaluable prior session is *unknown*, never "no compression".
   * **N — normal state:** `pct(t) > 0.20` (the literal complement of the compression state; includes names that left
     compression recently and names in the high state).
   * **P — persistence comparator:** `pct(t) ≥ 0.80` **and** on each of the prior 20 sessions `pct` defined and `< 0.80`
     (the mirror of the onset rule on the high tail).
   C is disjoint from N and from P; P ⊂ N.
5. **Lookback implied.** `pct(t)` needs 252 ratios, each needing 60 ranges, each needing a prior close ⇒ valid rows on
   t−311 … t; the onset conditions add 20 more ⇒ **332 consecutive valid rows** for C and P. (The inventory's
   "t − max(slow, 252) − 1 … t" cannot support a complete 252-window of a 60-session ratio; it is read as "every declared
   window complete" — §10.)

## 6. Outcomes (forward window t+1..t+h; baselines end at t; strict windows)

For h ∈ {5, 20}, all normalised by the name's own trailing baseline (window 252 ending at t):

| Outcome | Definition | Role |
|---|---|---|
| **E_range** | `mean_{t+1..t+h}(rng) / median_{t−251..t}(rng)` | **Primary** |
| E_vol | `sqrt(mean r² over t+1..t+h) / sqrt(mean r² over t−251..t)` | Secondary (report-only) |
| E_abs | `\|Σ r over t+1..t+h\| / (√h · sqrt(mean r² over t−251..t))` | Secondary (report-only) |
| E_sgn | `(Σ r over t+1..t+h) / (√h · same baseline)` | **Descriptive only — no test, no p-value, never classifying** |

**Forward availability (mechanical, exhaustive).** Every session t..t+h has a valid row ⇒ *normal*. Otherwise, if t+h is
past the last panel session ⇒ *beyond*; anything else (a hole, or the series ends inside the window) ⇒ *dropped*. A
dropped event is never imputed and never truncated (unlike BKV-1 there is no "terminal" accrual); it enters only the
attrition bound (§7.5). **Stage containment:** an event belongs to a stage iff its formation t **and** t+h lie inside the
stage; lookback may cross a stage boundary.

## 7. Estimand, inference, multiplicity

1. **Cohort series.** For each cell and cohort the observation at formation date t is the equal-weighted mean of E over
   that cohort's resolved events formed at t. Cross-sectional dependence on a date is removed by construction; a date
   contributes once whatever its event count.
2. **Primary statistic.** `d(t) = m_C(t) − m_X(t)` on dates with ≥ 1 C event **and** the comparator floor met — for
   *normal*, ≥ **100** N events (the inventory's pinned "min benchmark names = 100", read as the size floor of the
   normal-state benchmark; excluded dates are counted); for *persistence*, ≥ 1 P event. `d̄ = mean d(t)`.
3. **Test.** One-sided (H1: d̄ > 0) t = d̄ / SE, SE from the **calendar-aware Newey–West (Bartlett) estimator with lag L = h**
   (BKV-1 `nw_gap_test`, unchanged: gaps in the date index contribute no cross-products; Student-t, n − 1 df).
4. **Family.** **4 primary cells = h ∈ {5, 20} × comparator ∈ {normal, persistence}, D2, E_range.** **VAL** carries the
   decision: Holm over the 4 cells, α = 0.05 one-sided; a cell is **VAL-consistent** iff Holm-adjusted p < 0.05, d̄ > 0 and
   it is not attrition-fragile. **TRAIN is descriptive and takes no decision.** No pooling of TRAIN and VAL. D1, the
   secondary outcomes, the event-weighted contrast, the two-way-clustered event contrast, the within-date permutation p
   and the block-bootstrap CI are **report-only** (unadjusted; not gates).
5. **Attrition bound (pre-specified, no discretion; BKV-1 rule).** Recompute d̄ and its p with dropped C events replaced by
   the smallest retained C value of the cell and dropped comparator events by the largest retained X value, each on its
   own formation date (comparator floor applied to the augmented counts). A cell is **attrition-fragile** if the bound's
   d̄ ≤ 0 or its Holm-adjusted bound-p ≥ 0.05.
6. **MDE.** `(z₀.₉₅ + z₀.₈₀) · SE` (one-sided, 80 % power) per cell and stage, in units of E.

## 8. Characterization outcome and Vault mapping (fixed here, before any result)

| Label | Condition (first match) |
|---|---|
| **C4** | a defect trigger fired: frozen-file hash mismatch; any independent-verification disagreement beyond tolerance (`stop=True`); accounting-identity failure |
| **C5** | no VAL-consistent cell: the pre-declared criterion was tested on data and failed — always **"construct-scoped, non-confirmatory"**; M4a stays open |
| **C6** | ≥ 1 VAL-consistent cell: positive but incomplete — evidence sufficient to justify a **fresh pre-registered confirmatory experiment on an unread surface**; **not a confirmation** |
| C7–C9 | unreachable: no HOLDOUT exists and no economic gate applies (no tradeable expression) |

The word "confirmed" is not used for TRAIN or VAL. A significant *negative* d̄ is reported as the persistence signature
(§1) and never as support. Results that cannot be reproduced by the independent paths are **NOT AUDITABLE** and unused.

## 9. Independent verification (pre-declared; `verify_independent.py`, frozen; a disagreement STOPs the run)

| # | Check | Two methods | Tolerance |
|---|---|---|---|
| VP1 | every ledger row: existence, cohort flags, percentile, forward status, E_range / E_vol / E_abs / E_sgn, both variants | numpy engine vs **pure-SQL** window-function re-derivation from the same snapshot (own calendar, membership, ranges, means, `list_filter` percentile, onset rule, windows) | rows equal; flags equal; pct 1e-12; E 1e-9 |
| VP2 | seeded sample (4 per cohort); events with any adjustment factor of any symbol of the entity in the span are skipped and counted | engine vs **plain-Python loops over the RAW as-traded table** (own ratios, percentile, cohort rule, E_range, E_vol). All compared quantities are scale-free | 1e-9 |
| VP3 | every cell: cohort d(t), d̄, SE, t, p | table vs dict arithmetic from the ledger + a pure-Python NW + statsmodels `S_hac_simple`; Holm by hand | 1e-6 |
| VP4 | accounting: formed = resolved + dropped + value-missing + contained-out; unique (entity, t); C∩N = C∩P = ∅; pct ∈ (0,1] | identity | exact |
| VP5 | price basis: (a) adjusted OHLC = raw on entities with no factor of any symbol (gate); (b) for entities with one, adjusted rebuilt from `adjustment_factors` (entity level) — agreement rate reported | arithmetic | (a) 1e-9 |

The pipeline was validated on a synthetic snapshot with regime-switching volatility, delistings, holes, splits and a
rename chain: the two engines agree exactly there and the verifier fails on a deliberately tampered ledger. A causality
test perturbs everything after t and shows state and cohorts up to t unchanged, and a second test shows the window does
include t.

## 10. Pre-freeze interpretations (each fixed before any outcome; the two starred were confirmed by the operator 2026-09-30)

1. **Percentile convention:** `#(window ≤ x_t) / 252`, t included (§5.3). SQL verifier uses the same rule.
2. **Eligibility:** every declared window complete, no `min_periods` — 332 consecutive valid rows (§5.5). This is stricter
   than, and replaces, the inventory's "t − max(slow,252) − 1 … t", which cannot hold the percentile window.
3. **★ Normal cohort = the literal complement** (`pct > 0.20`, member, evaluable) — not a 21-session clean-of-compression
   variant. The clean variant would have left only 328 / 348 (TRAIN / VAL) compression dates above the 100-name floor
   against 901 / 704 for the complement (outcome-free counts, D2).
4. **★ "vs persistence" = the high-state cohort P** (`pct ≥ 0.80`, onset-mirrored): inventory §9.1(i) "forward expansion
   after high state". d(t) = mean_C(E) − mean_P(E). Not run: a level-matched control or the name's unconditional
   expansion (§6 alternatives) — those would be design additions.
5. **Normal-cohort floor:** the inventory's "min benchmark names = 100" is read as the floor on the normal cohort (M4a has
   no market benchmark); a date with fewer than 100 N events is excluded from the *normal* cells and counted.
6. **D1** uses sample std (ddof = 1) of log returns, fast 10 / slow 60, same percentile rule.
7. **Forward validity:** every session t..t+h valid; otherwise dropped and counted (§6). Stage containment as BKV-1.
8. **Quiet window:** max(h, 20) = 20 for both horizons.
9. **Prior close** in the outcome is each session's own prior close (`C[s−1]`), exactly as in the ATR definition.
10. **Decision stage:** VAL (Holm-4); TRAIN descriptive; no pooling (inventory §9.1, BKV-1 §15).
11. **Permutation draws:** 2,000 (report-only statistic, event sets of ~10⁵); bootstrap 10,000; seeds 20260930 / 20260931.

## 11. Pre-run mechanical predictions (falsifiable; checked in the report)

(i) `formed = resolved + dropped + value-missing + contained-out` in every block; C∩N = C∩P = ∅. (ii) The event counts in
`m4a_compress/diagnostics_outcome_free.json` reproduce (D2 compression events TRAIN 3,790 / VAL 3,071; D1 4,078 / 3,350).
(iii) VP1 agrees with the ledger row-for-row with zero exceptions. (iv) **Sign:** because the C cohort is selected on a low
*recent* range and forward range persists, mean E(C) < mean E(N) and mean E(C) < mean E(P) are expected, i.e. **d̄ < 0 in the
two persistence cells and probably in the two normal cells**; the modal outcome is **C5** (no VAL-consistent cell). This is
a statement about what the pre-specified contrast can show, not evidence that compression carries no information: the
estimand compares compression with the unconditional complement, not with a level-matched one (§12).

## 12. Limits of what this can say

* The two persistence cells are a demanding bar: compression must be followed by *more* normalised expansion than a
  high-dispersion state. A "no" there does not show the mechanism is absent.
* Even the vs-normal contrast is not level-controlled: the compressed cohort has a lower ATR10 by construction. A
  level-matched design is the natural successor if this run is not decisive; it is **not** part of this protocol.
* With ~1–4 compression names per formation date the per-date d(t) is noisy; the MDE is reported so that a null is read
  against it.

## 13. Refused in advance (rescues)

Any change of estimator, fast/slow window, percentile window, threshold, horizon, universe, weighting, cohort or event
definition after seeing a result; adding a level-matched or any other comparator; promoting D1, a secondary outcome, a
subgroup, a single year or a single side; describing TRAIN or VAL as confirmation; reading any HOLDOUT; pooling TRAIN and VAL.

## 14. Declared report-only analyses (disclosure only; cannot change any label)

R1 event-weighted contrast (weights n_C); R2 block-bootstrap CI (block h+1); R3 two-way-clustered (entity, date) event
contrast; R4 within-date permutation p; R5 by calendar year (mean d, share of positive dates); R6 date concentration
(share of Σd in the top 10 dates, d̄ without them, median d, share of positive dates, the top-10 dates listed);
R7 secondary outcomes E_vol and E_abs contrasts (unadjusted, non-classifying); R8 signed forward move, descriptive means
per cohort only; R9 D1 (4 cells, Holm within D1 for information); R10 cohort levels (mean and median E in C, N, P); R11 MDE.

## 15. Reproducibility

```bash
git worktree add ../Nifty_m4a research/m4a-compression-expansion
python -m scripts.m4a_compress.diagnostics            # outcome-free counts
python -m pytest tests/m4a_compress -q                # unit + governance + synthetic end-to-end
python -m scripts.m4a_compress.freeze                 # only after the protocol is final, before any outcome
python -m scripts.m4a_compress.run_stage TRAIN ; python -m scripts.m4a_compress.run_stage VAL
python -m scripts.m4a_compress.verify_independent TRAIN ; python -m scripts.m4a_compress.verify_independent VAL
python -m scripts.m4a_compress.run_stage CLASSIFY
```
Determinism: seeded bootstrap and permutation; every state is a function of prior sessions; results reproduce
byte-for-byte from the hashed snapshot.

---

## Amendments (append-only; each is logged in the freeze record `history` and the research log)

**A1 - 2026-09-30, verifier tolerance only (`verify_independent.py`, VP1 percentile).** VP1 as frozen required the
percentile to agree to 1e-12. Run on TRAIN it failed for the D1 robustness variant: 1 of 229,373 rows (MARKSANS, session
1596; cohort N, pct 0.2341 in the engine vs 0.2302 in SQL, both above the 0.20 threshold) differed by exactly 1/252. Diagnosis
(before any change): the 252-window holds an *exact mathematical tie* between two ratios (direct numpy: distance 0.0); the
numpy/pandas path and the SQL path differ at the 1e-16 level, which decides which side of `<=` the tie falls. Cohort flags,
statuses and every outcome value agree on every row of both variants and both stages; D2 agrees exactly on TRAIN and VAL.
Amended: a percentile difference passes only if it is an integer number k of 1/252 steps with 1 <= k <= the number of window
ratios within 1e-12 relative of the current one (counted by the SQL path); anything else is unexplained and fails VP1. Tested on
a synthetic tie table and on a tampered percentile. **No engine, cohort, outcome, analysis or classification code changed;
TRAIN and VAL results were computed before the amendment and are unchanged.**

