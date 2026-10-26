# M4a — Compression → Expansion: Non-Confirmatory Characterization Report

**Protocol:** `M4A_COMPRESSION_EXPANSION_PROTOCOL.md` v1.0 (frozen before any outcome; one logged amendment, A1, to the
verifier only). **Log:** `M4A_COMPRESSION_EXPANSION_RESEARCH_LOG.md`. **Branch:** `research/m4a-compression-expansion`
(worktree `F:\Nifty_m4a`). **Status:** GR-1.4 non-confirmatory characterization — TRAIN 2012-01-02 → 2017-12-29 and
VAL 2018-01-01 → 2022-12-30 are signal-spent windows (GR-1.3); **nothing below is a confirmation, no HOLDOUT was read (none
exists in this package), no strategy was built, the Vault mechanism map and closure ledger were not modified.**
Every table is script-generated from `data/research/m4a_compress/results/` (copied to `docs/reports/research/m4a_compress/`).

---

## 1. Answer

**On the pre-registered contrast, M4a shows no support — and every cell, stage, horizon and year points the other way.**
A low trailing ATR10/ATR60 state (bottom 20 % of its own 252-session history, onset only) is followed by a *smaller*
normalised forward range than the normal-state complement and than the high-dispersion state. All four primary cells are
wrong-signed in VAL (one-sided p ≈ 1, Holm p = 1), all four are wrong-signed in TRAIN, all 44 year-by-cell values in TRAIN and
VAL are negative, and the block-bootstrap 95 % interval excludes zero on the negative side in every cell. The minimum
detectable effect in VAL is 0.036–0.059 (units of the name's own baseline), so a positive effect of that size is excluded.

**Characterization outcome: C5, construct-scoped, NON-CONFIRMATORY** — the pre-declared criterion was tested on data and
failed; **M4a stays open** (it is not closed as a mechanism), and this run gives **no reason to spend a fresh confirmatory
window on this contrast.**

**What this does not say.** The negative sign is what volatility persistence predicts: the compression cohort is *selected
on a low recent range* (ATR10), and forward range tracks recent range (protocol §11(iv), stated before the run; the same
sign appears on random regime-switching synthetic data in the pre-freeze scale test). The contrast is against the
*unconditional* complement, not against names with the same current range level, so it cannot show whether compression carries
information *beyond the level of recent range*. That level-controlled question is untested and would be a new
pre-registration (§10).

## 2. What was run

Frozen specification (protocol §5–§7): D2 = ATR10/ATR60 of `(H−L)/C[s−1]`, trailing-252 percentile ending at t (t included,
`#(window ≤ x_t)/252`, complete windows only), compression = percentile ≤ 0.20, onset = no compression state on the prior 20
sessions; PIT top-200 daily panel (the certified BKV-1 dev snapshot, panel hash `46de7d4d…` asserted at load; nothing after
2022-12-30 loadable). Primary outcome `E_range = mean_{t+1..t+h}((H−L)/C[s−1]) / median_{t−251..t}(same)`, h ∈ {5, 20}. Estimand:
cohort-by-date `d(t) = mean_C(E) − mean_X(E)`, one-sided Newey–West with lag = h, **four primary cells** (h × {normal, persistence}),
Holm at α = 0.05 on VAL. Operator-confirmed pins (protocol §10): normal cohort = the literal complement (not in compression at t,
≥ 100 names/date); persistence comparator = the high-state cohort (percentile ≥ 0.80, onset-mirrored). D1 (RV10/RV60, same
percentile) is declared robustness only.

## 3. Primary result

**VAL 2018-01-01 → 2022-12-30 (the decision stage):**

{{TABLE:primary_VAL}}

**TRAIN 2012-01-02 → 2017-12-29 (descriptive, takes no decision):**

{{TABLE:primary_TRAIN}}

`d-bar` and `MDE80` are in units of the name's own trailing-median range; `mean E` columns are date-cohort means. "Holm p" is over the
four VAL cells (TRAIN Holm is shown for information only). "bound d-bar / Holm bound p" is the pre-specified worst-case
attrition bound (dropped C events set to the smallest retained C value, dropped comparator events to the largest retained X
value): it barely moves anything because attrition is tiny (§4). **No cell is VAL-consistent** (each has d̄ ≤ 0).

## 4. Event counts, formation dates, attrition

**VAL:**

{{TABLE:counts_VAL}}

**TRAIN:**

{{TABLE:counts_TRAIN}}

"pair dates" are the formation dates on which the contrast exists (≥ 1 compression event and the comparator floor met);
"dates < floor" is the number of dates with compression events and a normal cohort under 100 names that were excluded. The dropped events
(no forward window) are at most 0.1 % of any cohort. Accounting identities hold exactly (`formed = resolved + dropped + value missing
+ contained-out`; VP4):

{{TABLE:accounting_VAL}}

## 5. The persistence comparison and cohort levels

The vs-persistence cells compare compression with the high-dispersion state (`pct ≥ 0.80`). Cohort levels (mean and median E,
D2), so the sign is visible rather than inferred:

**VAL:**

{{TABLE:levels_VAL}}

**TRAIN:**

{{TABLE:levels_TRAIN}}

Compression names (C) go on to a forward range about equal to their own trailing median, the complement (N) to a range
clearly above it, and the high-state names (P) to the highest — the ordering persistence implies. (A mean-over-median E above 1
is the ordinary skew of a daily range and is common to all three cohorts.)

## 6. Stability

**By year (d-bar per formation year, VAL then TRAIN):**

{{TABLE:byyear_VAL}}

{{TABLE:byyear_TRAIN}}

Every value is negative: the result is not a single regime. **Concentration by date** (VAL, then TRAIN; top-10 dates are the ten
largest d(t)):

{{TABLE:conc_VAL}}

{{TABLE:conc_TRAIN}}

Removing the ten most favourable dates makes d̄ *more* negative; only 26–39 % of VAL dates have d(t) > 0. (The "share of sum in
top-10" column has no meaning when the sum is negative and is shown only for completeness.)

## 7. D1 robustness (RV10/RV60, same percentile construction; disclosure only)

**VAL:**

{{TABLE:d1_VAL}}

**TRAIN:**

{{TABLE:d1_TRAIN}}

The estimator makes no difference to the sign: D1 is wrong-signed in all four cells in both stages (the two definitions of
compression select overlapping but not identical names; D1 has more compression dates that pass the floor).

## 8. Secondary outcomes (report-only, unadjusted, non-classifying) and signed move (descriptive)

**Realized-volatility expansion and absolute forward move, D2, VAL:**

{{TABLE:secondary_VAL}}

**TRAIN:**

{{TABLE:secondary_TRAIN}}

The realized-volatility contrast is negative like the range. The *absolute move* contrast is smaller than the range contrast and mixed in sign: negative in most cells (the 5/persistence cell is
negative in both stages, t ≈ −2.2 VAL and −2.4 TRAIN, unadjusted), slightly positive only in VAL 20/normal (+0.023, p = 0.12); no cell is
positive-significant and none is promoted. That is a descriptive observation among 8 unadjusted secondary cells per stage and is **not** a finding.

**Signed forward move — descriptive means only, no test of any kind (VAL, then TRAIN):**

{{TABLE:signed_VAL}}

{{TABLE:signed_TRAIN}}

## 9. Report-only tests (unadjusted)

**VAL:**

{{TABLE:reportonly_VAL}}

**TRAIN:**

{{TABLE:reportonly_TRAIN}}

Event-weighted contrast, block-bootstrap 95 % CI, two-way (entity, date) clustered event contrast and within-date permutation p all
agree with the Newey–West result. (`cluster p` and `perm p` are one-sided for d̄ > 0, hence ≈ 1.)

## 10. What a successor would have to be

* This characterization gives no evidence in favour of spending an unread window on the *same* contrast.
* The untested question is level-controlled: does compression predict expansion **among names with the same current short-run
  range** (e.g. matched on ATR10 percentile or on trailing range level), i.e. does the ATR10/ATR60 *ratio* carry information beyond
  the *level* of recent range? That is a different estimand, needs its own pre-registration (with the persistence control declared
  before any read), its own power-feasibility check (RFA) and a genuinely unread surface (inventory §9.4: India VIX 1m/EOD, the
  101 unread vendor-N100 1m names, or a future window). It is **not** authorised or started by this report.
* Nothing here is a trading result; there is no cost model and no strategy.

## 11. Independent verification

{{TABLE:verification}}

VP1 compares 3.1–3.7 million ledger values per stage with a pure-SQL re-derivation (own calendar, membership, ranges, means, `list_filter`
percentile, onset rule, windows) with **zero** missing or extra rows, **zero** flag or status mismatches, percentile and E
agreeing to ~1e-13. **Amendment A1:** on the first TRAIN verification VP1 stopped on the D1 robustness variant: one row of 229,373
(MARKSANS, session 1596, normal cohort) differed by exactly 1/252 in percentile because the window holds an exact mathematical
tie between two ratios that the numpy and SQL float paths break differently (confirmed by direct recomputation). It was
investigated before anything was changed; the verifier tolerance was amended (a percentile difference passes only if it is an integer
number of 1/252 steps no larger than the count of tied window values), tested, and the freeze re-recorded with history. No engine,
cohort, outcome, analysis or classification code changed and no result changed. That row is the only percentile difference in the
whole verification.

{{TABLE:classification}}

## 12. Vault taxonomy mapping (the ledger is not modified)

| Item | Mapping |
|---|---|
| This run | **C5, construct-scoped, non-confirmatory** (criterion tested on data, failed; the D2 ATR-ratio compression state, onset, PIT top-200 daily, range-expansion outcome, complement and high-state comparators) |
| M4a as a mechanism | unchanged: **C — open** (construct-scoped negative; the level-controlled question is untested) |
| Sealed / unread windows | untouched: no HOLDOUT read; the 2023-01-02 → present equity window was never loaded; TRAIN/VAL were already signal-spent |
| C6 / C7 / C8 | not reached (no VAL-consistent cell; no HOLDOUT; no economic gate) |
| Register | owed to the operator (not done here): an exposure-register row for this 2012–2022 equity-EOD read |

## 13. Pre-run predictions (protocol §11), checked

(i) Accounting identities and C∩N = C∩P = ∅: **hold exactly** (VP4). (ii) The diagnostics counts reproduce: D2 compression events TRAIN 3,790 / VAL 3,071 in
the diagnostics vs 3,774 / 3,069 resolved at h = 5 here (the difference is the events whose window is not available or leaves the stage).
(iii) VP1 agrees row-for-row with zero exceptions: **yes** (after the tie-tolerance amendment for one D1 row). (iv) Sign: **d̄ < 0 in all
four cells and stages** — predicted for the persistence cells and "probably" for the normal cells; the modal outcome C5 occurred.

## 14. Reproducibility and limits

TRAIN and VAL were re-run from the hashed snapshot into a scratch directory under the final freeze; every result file is
byte-identical (parquet ledgers frame-identical) — `repro_check.json`. Limits: TRAIN/VAL are spent, so this is a characterization;
~3–4 compression names per formation date make the per-date contrast noisy (the MDE is reported and is small relative to the
observed effects); dropped-window attrition is negligible; the persistence cells are a demanding comparator by construction; only one
universe, one estimator family and two horizons were examined, as pre-registered.

## 15. Files

`scripts/m4a_compress/{common,panel,state,cohorts,outcome,analyze,classify,stats,diagnostics,freeze,run_stage,verify_independent,build_report}.py`,
`tests/m4a_compress/` (55 tests: state, cohorts, outcome, analysis, panel, governance, synthetic end-to-end), protocol `.md` + `.json`,
freeze record `m4a_compress_FREEZE.json`, research log, result bundle `docs/reports/research/m4a_compress/`.
