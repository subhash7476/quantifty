# Opus Review B — audit of the VWAP-XREV-1 primary results (TRAIN / VAL / one-shot HOLDOUT)

Reviewer: Claude Opus (independent subagent). Read-only w.r.t. both repos; it ran its own labelled
**[post-primary]** read-only cuts on the saved events tables. Report reproduced verbatim (formatting
normalised only). Prompt: "Audit whether these results actually support the stated empirical conclusion.
Look specifically for multiple-testing, selection effects, dependence, regime concentration, data
artefacts, and economic interpretation errors." The reviewer was forbidden to redefine the primary
experiment.

---

**Scope.** Read the protocol, PRIMARY_RESULTS.md, the research log and the code (engine, analyze, stats,
classify). The code is causal: thresholds are built from `pool[t-60:t]`, σ_prior comes from prior sessions
only, entry is the next open, outcomes are strict-NaN. The fee arithmetic checks out. Every cut marked
**[post-primary]** is the reviewer's own read-only analysis of the saved events tables. None changes the label.

## 1. Is C6 an accurate description?

The frozen tree applies C6 correctly (C6 needs HOLDOUT point estimates above zero in at least one
VAL-confirmed cell; down/h10 +1.7 bp and down/h30 +4.1 bp meet that). The problem is the English gloss
"positive but incomplete". It is **too generous**.

- The C6-versus-C5 margin carries almost no information. It rests on the sign of two HOLDOUT point estimates
  that share the same events. Both are market-level: HOLDOUT market-excess R_ex is +0.36 bp (p .44) and
  +0.82 bp (p .41).
- HOLDOUT was well powered. Its minimum detectable effects are 5.7 and 8.5 bp. Its 95% CI upper bounds
  (6.9 and 11.5 bp) sit below the TRAIN estimates (7.5 and 12.5 bp). The h30 miss is narrow. (Anchored on
  TRAIN, not VAL: the VAL estimates were selected for significance, so comparing against them would
  overstate the miss.)
- The third confirmed cell reversed. For up/h5 the HOLDOUT CI is [−4.6, +0.4], which excludes the VAL
  estimate of +4.6.

What the data establish: in TRAIN, reversion after down-displacement relative to the market is real.
Event-level R_ex is +3.9 to +5.8 bp with two-way-cluster p ≈ .001; robust to 1/99 winsorising and to
date-ordered two-sided trimming (t 3.0–4.2). VAL shows the same, more weakly. HOLDOUT shows none of it.
What the data do not establish: any out-of-sample reversion effect beyond what the market does in the same
window.

## 2. Multiple testing, selection, market beta

- **FWER is controlled.** The q selection was outcome-free, VAL Holm over 10 cells bounds family-wise error at
  ≤5%, and HOLDOUT is tested only on VAL survivors. "The confirmations are chance" is not the main risk; the
  main risk is that the confirmations depend on the estimator:
  - [post-primary] VAL R_ex, same test: smallest p is .007, which becomes .07 under Holm-10. Zero cells confirm.
  - [post-primary] VAL raw event-level two-way-cluster p (a pre-registered secondary statistic): smallest is
    .042. Zero cells pass Holm-10; up/h5 has cluster p .108.
  - So the VAL confirmation exists only under raw returns with session weighting.
- **up/h5 is most plausibly noise or an artefact of the weighting.** TRAIN +1.0 bp p .22; HOLDOUT −2.0 bp
  reversed. [post-primary] Removing the 27 VAL sessions that had a single up-event drops it to +2.1 bp (t 1.14);
  those singleton sessions average +17.2 bp and are 17% of sessions but ~2.6% of events.
- **Market-beta artefact.** R is raw; R_ex = R − equal-weight universe return over the same window; B = R − R_ex.
  [post-primary] On TRAIN days with ≥30 down-events (9 sessions, 575 events): raw R30 −28 bp, R_ex30 +5 bp —
  market-wide selloffs that kept falling. That is why the TRAIN event mean is negative while the session mean
  is positive. In VAL the same heavy days rebounded (raw +20 bp, B30 +13 bp), which is why VAL event means turn
  positive (2024-07-23, Budget day, alone produced several +360 to +450 bp events). At the session level B is
  positive on the down side in every stage (+1.3 to +8.0 bp): part of every raw session-mean "reversion" is the
  market's own intraday reversal. For VAL down/h30, ~8 of the 18.7 bp is benchmark.
- **The R_ex caveat runs both ways.** The equal-weight benchmark includes the event names and assumes β=1, so on
  many-event days it absorbs part of the effect (R_ex is conservative there). That does not rescue HOLDOUT:
  [post-primary] HOLDOUT R_ex is also ≈0 in the 1–3-event sessions.

## 3. Dependence, regime, artefacts

- **Session vs event weighting.** Low-count sessions carry a disproportionate share of the inference weight.
  [post-primary] Singleton sessions are 20% of down-side sessions in TRAIN and VAL, with R10 of +20.8 and +30.8
  bp; they supply ~4 of the 7.5 bp (TRAIN) and ~6 of the 11.1 bp (VAL) in down/h10. Excluding them, VAL
  down/h10 is +6.2 bp (t 1.73) and R_ex +2.7 bp (t 0.85); VAL down/h30 holds up better (+13.3 bp, t 2.59). In
  HOLDOUT the singleton sessions do not revert (−2.4 bp at h10). The pre-registered leave-top-k drops only the
  most favourable sessions, so it always pushes toward fragility; date-ordered two-sided trimming leaves VAL
  significant (t 3–5). The fair fragility claim is the singleton dependence, not "top-5 sessions".
- **Regime and timing.** [post-primary, quarterly, split exactly at stage boundaries] Down-side R_ex quarters
  2023Q2–2025Q2 are mostly +2 to +17 bp; HOLDOUT's first quarter, 2025Q2, is strongly positive (h10 +14.7, h30
  +16.4). From **2025Q3 onward, five consecutive quarters are ~0 or negative** (h30 R_ex −5.3 to +1.5); up/h5
  turns negative in the same quarters. So the decay does not coincide with the HOLDOUT boundary; it starts
  roughly mid-2025 and HOLDOUT is dominated by the post-break period. Any external explanation (F&O regulatory
  changes, participant mix) is post-hoc narrative and must be labelled so.
- **Universe composition does not explain the decay.** [post-primary] Restricted to names that appear in TRAIN,
  HOLDOUT down/h10 is +1.9 bp and h30 +4.1 bp, the same as the full universe. No liquidity tercile in HOLDOUT
  reproduces VAL. The CAS era (from 2026-08-03) is ~40 HOLDOUT sessions and does not drive the result.
- **Artefact checks came back clean:** entry gap (next open vs decision close) median 0 and |gap| < 50 bp for
  every event; exact-zero returns 0.4–2.2% of events (no stale-bar clusters); NaN share ≤0.1%. Events at the
  first window bar (k=59) are 11–17% of events; in HOLDOUT they supply part of the down-side positive estimate
  (h10: +6.8 bp at k=59 vs +1.1 bp later). The largest VAL event (KPIT 2025-01-29, +947 bp in 10 minutes) is
  genuine results-day trading, confirmed against the raw 1m bars.

## 4. Economics

- **Costs are right.** Net at κ=0 minus gross is −4.58 bp, matching ~4.5 bp round trip at Rs 5 lakh (STT 2.5,
  exchange ~0.6, brokerage 0.8, stamp 0.3, GST/SEBI). Adding 2×2.75 bp slippage gives ~10 bp. κ=2.75 bp is
  borrowed from a different construct; at extreme-displacement moments spreads are plausibly wider, so the 5 bp
  scenario is the honest one.
- **"Not economically meaningful" is correct but trivially so.** The frozen economic gate is never reached
  because nothing is HOLDOUT-confirmed. All 10 HOLDOUT net cells at κ=2.75 are negative.
- **Misleading element to correct.** The TRAIN and VAL tables show positive session-mean net returns at h30/h60
  (up to +9.8 bp). Equal weight per session is not an implementable P&L, because it needs the day's final event
  count at the time capital is allocated. The tradeable figure is the event-weighted net (TRAIN down/h60 about
  −15.5 bp; VAL positive at κ=2.75 for down h10–h60 but that is VAL, and the positive part is market-level).
  Flag these rows as "session-weighted, not tradeable".

## 5. Post-primary analyses (non-classifying)

Worth running, highest value first: (1) put the quarterly R_ex series in the report — the most informative
single exhibit because it dates the break; (2) R_ex with a β-adjusted, leave-own-name-out benchmark per stage,
to close the β=1 caveat; (3) event-weighted versus session-weighted and singleton-excluded results side by side,
as disclosure; (4) tag earnings/results days from the corporate-announcement calendar and report descriptively;
(5) the pre-registered robustness grid (q, normalisation, VWAP type, delay-2, core universe) as disclosure only.

Refuse as forking-paths abuse: promoting HOLDOUT h60 (raw p .022/.003 but R_ex p .34/.15; not VAL-confirmed);
adopting a winsorised, trimmed or singleton-excluded estimator as the primary; regime- or side-conditional
"works in bull markets / in Q2-2025" claims; using the 20 and 45 minute horizons to find a confirming cell;
excluding earnings days as a rescue; redefining the stages around the mid-2025 break; any second HOLDOUT read.
Specifically: the date-ordered trimmed HOLDOUT raw down/h30 reaches t≈2 [post-primary], but its R_ex trimmed
t is 0.38; it must not be reported as partial support.

## 6. Verdict

Mechanically, the frozen label is **C6** and it stands. In substance, the evidence supports **"empirically
failed out-of-sample"**. A stock-specific reversion after extreme downside displacement from VWAP existed in
2023–mid-2025 (TRAIN R_ex +4 to +6 bp, robust). VAL confirmed it only under raw returns with session weighting;
it did not hold under the market-excess or event-clustered versions. The well-powered HOLDOUT shows no reversion
relative to the market (R_ex ≈ 0) and is inconsistent with the TRAIN effect size. The residual positive raw
points are market-level. up/h5 reversed. Nothing clears costs.

Wording the reviewer would allow:

> "Classification C6 under the frozen tree (VAL-confirmed cells; none HOLDOUT-confirmed; HOLDOUT point
> estimates positive in two of three). The substantive result is non-replication: HOLDOUT (2025-04 → 2026-09,
> well-powered, MDE 5.7–8.5 bp) shows no reversion net of the equal-weight market (R_ex +0.4/+0.8 bp, p > 0.4)
> and excludes the TRAIN effect sizes at 95%; the positive raw HOLDOUT points are market-level. A market-excess
> reversion after downside displacement is present in 2023–mid-2025 and absent from 2025Q3 onward
> (post-primary, descriptive). No cell is economically meaningful; every HOLDOUT net-of-cost estimate is
> negative. This does not support extreme VWAP displacement as a persistent source of intraday reversion."

Do **not** write "partially confirmed", "positive but incomplete" without the non-replication clause, or
anything implying the effect is present but under-powered.

---

## What changed as a result (recorded)

| Point | Change |
|---|---|
| Primary experiment / label | **None.** Frozen tree label C6 stands; the primary is never re-defined |
| C6 gloss | Adopt Opus's non-replication wording; the report's "exact empirical conclusion" carries it, and never says "positive but incomplete" alone |
| Session-weighted net rows | Flagged "session-weighted, not tradeable" wherever shown; event-weighted net reported alongside |
| Post-primary disclosure set | Run and labelled: full robustness grid; quarterly R_ex series; event- vs session-weighted and singleton-excluded views; subgroup splits. **Not run (stated):** β-adjusted leave-own-name-out benchmark and earnings-day tagging (no verified announcement calendar in the repo path used here) |
| Refused as forking-paths | HOLDOUT h60 promotion; any trimmed/winsorised/singleton-excluded primary; regime- or side-conditional claims; 20/45-min horizons as a rescue; stage redefinition; second HOLDOUT read |
