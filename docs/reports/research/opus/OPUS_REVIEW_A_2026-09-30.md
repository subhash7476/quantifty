# Opus Review A — pre-freeze attack on VWAP-XREV-1 (1.0-RC1)

Reviewer: Claude Opus (independent subagent, read-only, no forward return computed). Report reproduced
verbatim below (formatting normalised only).
Prompt: "Attack this experiment for hidden look-ahead, survivorship bias, threshold leakage, incorrect VWAP
construction, invalid normalization, sample-selection bias, and statistical-design flaws. Do not redesign it
unless a material flaw exists."

---

**OPUS REVIEW A: VWAP-XREV-1 (1.0-RC1)**

Scope: read the protocol JSON, engine/stats/analyze/universe/common/freeze/run_primary/diagnostics/prep/regime,
the tests and the log; ran outcome-free checks on the session cache, fno_membership.json and futures_bhavcopy.
Computed no forward return.

**A. Look-ahead and causality: sound, and verified in code**
- VWAP: cumulative sum of (H+L+C)/3·V over valid bars, through bar k inclusive (engine.py:76-79). With
  start-labelled bars, bar k closes at 09:15+(k+1), so D=k+1 is correct. Labelling is consistent across the
  store: 0 of 920 cached sessions have <90% of names with slot 0 populated. Tests cover brute force and
  future-bar invariance. NON-ISSUE.
- Decision inputs are close_k, VWAP_k, the prior scale, and the valid-bar fraction via cum_ok through k.
  "First qualifying bar" via argmax is causal. Entry is O[k+1]. NON-ISSUE.
- sigma_prior uses rows with index in [t-20, t); hist is appended only after detection. NON-ISSUE.
- Threshold pool: today's |z| is appended at t, thresholds() slices pool[t-60:t], so today and future are
  excluded; a test covers it. NON-ISSUE. q selection was outcome-free. NON-ISSUE. Membership = same-day FUTSTK
  rows; contract listing is known ex ante, so not look-ahead. NON-ISSUE.
- CAS era moves sigma by <1% (median ratio 0.99-1.006 either side of 2026-08-03); all exits <= 15:10.
  NON-ISSUE.

**B. Findings**
- **F1 MATERIAL — classification rules ambiguous/gameable.** C5 and C6 overlap ("HOLDOUT positive-signed but not
  significant" is also "HOLDOUT null"). C6's "single stage/sub-period" conflicts with C5's "no cell
  VAL-confirmed"; a significant TRAIN result (descriptive-only) or a significant robustness split could lift a
  label to C6, contradicting "none is ever promoted". C4 ("defect voids the read") has no pre-listed triggers.
  Fix: a precedence-ordered mutually exclusive tree using only VAL and HOLDOUT primary cells. C4 iff a
  pre-listed trigger fires (freeze/code hash mismatch; membership agreement failure; per-cell NaN-outcome share
  above a stated cap, e.g. 2%). C8 = C7 + economic gate. C7 = VAL-confirmed and HOLDOUT-confirmed. C6 =
  VAL-confirmed, not HOLDOUT-confirmed, HOLDOUT point estimate > 0 in >=1 VAL-confirmed cell. C5 otherwise.
  Delete "single stage/sub-period". TRAIN and robustness never enter classification.
- **F2 MATERIAL — code does not implement the stated confirmation rule; no classifier exists.**
  analyze.stage_table applies Holm over all 10 cells in every stage including HOLDOUT, while the protocol says
  HOLDOUT Holm is over VAL-confirmed cells only (code is more conservative but it is a mismatch at the one-shot
  read). Nothing maps tables to a C-label. Fix: one pure function classify(val_tab, holdout_tab, holdout_cost)
  -> label + cells with unit tests; write before the freeze and hash it.
- **F3 MATERIAL (cheap) — "HOLDOUT evaluated exactly once" is not enforced.** run_primary HOLDOUT can be re-run
  and overwrites outputs; nothing requires VAL results first. Fix: assert VAL cells CSV exists before HOLDOUT;
  write a HOLDOUT-read marker and refuse a second run (as run_sealed.py does).
- **F4 MATERIAL (cheap) — freeze hashes only the protocol JSON.** engine/analyze/stats/universe/common and the
  membership JSON are not covered; numeric Params defaults live in code not JSON; run_primary cites a
  non-existent robustness.py. Fix: record SHA-256 of those files, membership JSON and classifier in the freeze
  record and assert; implement robustness overrides before freeze or state robustness code is post-freeze and
  non-classifying.
- **F5 MINOR — economic gate multiplicity.** "CI lower bound > 0 in at least one HOLDOUT-confirmed cell" uses an
  unadjusted 95% CI across up to 10 cells. Fix: 1-0.05/m percentile bound (m = number of HOLDOUT-confirmed
  cells); disclose kappa=2.75 is borrowed from ISD G6b (a different construct); extreme-displacement spreads
  are plausibly wider (hence the 5 bp scenario).
- **F6 MINOR — residual bid-ask bounce.** O[k+1] removes the close->open bounce; what remains is trade-sign
  persistence (sub-bp to ~1 bp), comparable to the session-mean SE at H=5/10. Fix: pre-register entry_delay=2 as
  a qualifier: a cell confirmed at H=5 or 10 whose delay-2 HOLDOUT mean <= 0 is "microstructure-contaminated"
  and cannot support C7/C8.
- **F7 MINOR — missing entry/exit bar -> NaN conditions on the future.** Given an extreme move the likeliest
  cause is a price-band lock (a continuation case), so dropping biases toward reversion. Baseline missingness in
  10:15-15:10 is 0.01-0.5% per session; the conditional rate is unmeasured. "same_event_set_for_all_horizons"
  holds for detection, not for evaluated outcomes. Fix: report n_NaN per cell and side; pre-registered
  sensitivity exiting at the last valid close at or before k+H (a causal as-traded price, not imputation); tie
  the NaN share to the C4 cap; correct the wording.
- **F8 MINOR — coverage/survivorship disclosure factually wrong.** Store members / FUTSTK underlyings: 2023-06
  140/187 (75%); 2024-10 136/179 (76%); 2024-12 172/223 (77%); 2025-02 177/227 (78%); 2025-06 191/220 (87%);
  2025-10 199/209 (95%); 2026-04 201/213 (94%); 2026-09-29 210/210 (100%). The Dec-2024 jump is NSE's F&O
  expansion (179 -> 223), not a rise in store coverage; so "~100% from mid-2025" is wrong and the survivorship
  shaping (names retained into the late-2026 F&O list) reaches into HOLDOUT. Coverage converging to exactly 100%
  on the last session suggests the store's name list was chosen on a later universe, i.e. sample selection on a
  future variable; its link to 5-60-minute reversion is plausibly weak and probably conservative (dropped names
  are the less liquid). Fix: correct protocol text and log L14; add a labelled robustness read on a
  constant-name subset (names present from the TRAIN start), per stage.
- **F9 MINOR — market-direction component in side cells.** Raw R_H includes the market's return over the same
  window; events cluster on one side on trend days. Valid for the hypothesis but an interpretation hazard. Fix:
  for every confirmed cell report R_ex with identical session-level NW inference; a confirmed raw cell with
  non-positive R_ex is a market-level finding.
- **F10 MINOR — disclose.** dmov is mechanically biased toward "reversion" (VWAP drifts toward price) -> mark
  non-evidential. Events pile up at the first window bar (13.5% at k=59; 13.0% with |z_prev| >= c: inherited
  states) -> pre-register a descriptive split k=59 vs later. sigma_prior "min 15 sessions" counts store rows,
  not finite sigma values (engine.py:135) -> count finite sigma.

**C. Estimand and statistics are sound.** Session-level equal weighting removes within-session cross-sectional
dependence from the SE and down-weights many-event market-shock days; NW Bartlett is HAC; lag 5 at n~285; block
of 6 reasonable; the event-level two-way cluster is a proper secondary. Holm is valid (conservative) under
strong positive dependence across nested horizons and sides. VAL-then-HOLDOUT gatekeeping controls FWER once F2
aligns the code. The z definition does not leak; sqrt(D) matters only within a bucket and the bucket quantile
absorbs level and time-of-day effects; events concentrate on today-vol-shock names and days (inherent; the range
and raw_bp robustness reads cover it). Overnight returns never enter. Float32 caching is negligible.

**D. Verdict: FREEZE-AFTER-FIXES.** Gating fixes: F1 (mutually exclusive classification tree with pre-listed C4
triggers); F2 (coded classifier, HOLDOUT Holm over VAL-confirmed only); F3 (HOLDOUT one-shot guard +
VAL-before-HOLDOUT); F4 (freeze hash covering code, membership file, classifier); F8 (corrected coverage
disclosure).

---

## What changed as a result (recorded before the freeze)

| Finding | Adopted? | Change |
|---|---|---|
| F1 | Yes | Classification rewritten as a precedence-ordered, mutually exclusive tree over VAL/HOLDOUT primary cells only; C4 triggers pre-listed (hash mismatch, membership-agreement failure, NaN share > 2% in a primary cell); "single stage/sub-period" deleted; TRAIN and robustness never classify |
| F2 | Yes | `scripts/vwap_rev/classify.py` + unit tests; HOLDOUT Holm over VAL-confirmed cells only; `stage_table`'s all-10 Holm column renamed `p_holm_all10` (descriptive) |
| F3 | Yes | HOLDOUT run requires the VAL cells CSV and writes a one-shot marker; a second run is refused |
| F4 | Yes | Freeze record hashes protocol + engine/analyze/stats/universe/common/classify/freeze/run_primary + membership JSON; numeric Params mirrored into the protocol JSON with a test that defaults equal the JSON; robustness code declared post-freeze and non-classifying |
| F5 | Yes | Economic gate uses a one-sided bootstrap lower bound at level 0.05/m (m = HOLDOUT-confirmed cells); κ provenance disclosed |
| F6 | Yes | Delay-2 qualifier pre-registered and computed inside the single HOLDOUT read; H∈{5,10} cells with delay-2 mean ≤ 0 are "microstructure-contaminated" and cannot support C7/C8 |
| F7 | Yes | n_NaN reported per cell/side; last-valid-exit sensitivity added (post-primary, non-classifying); NaN cap wired to C4; wording corrected |
| F8 | Yes | Protocol coverage text and log L14 corrected with Opus's numbers; constant-name ("core") universe added as labelled robustness, defined from the warm-up sessions only |
| F9 | Yes | R_ex reported with identical inference for every cell; a HOLDOUT-confirmed cell with non-positive R_ex is annotated a market-level finding (annotation, not a label change) |
| F10 | Yes | dmov marked non-evidential; k=59-vs-later split reported descriptively; σ_prior minimum counts finite σ values (engine fix; outcome-free diagnostics rerun) |
