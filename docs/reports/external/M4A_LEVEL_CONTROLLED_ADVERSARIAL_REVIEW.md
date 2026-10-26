# M4a — Level-Controlled Follow-Up: Adversarial Research Review

**Date:** 2026-09-30 · **Branch:** `research/m4a-compression-expansion` (worktree `F:\Nifty_m4a`)
**Role:** adversarial reviewer. **No code written, no protocol created, no parameter optimised, no holdout read,
no Vault/ledger edit, no strategy proposed.**
**Reviewed in full:** `M4A_COMPRESSION_EXPANSION_DESIGN_INVENTORY.md`; `M4A_COMPRESSION_EXPANSION_PROTOCOL.md` v1.0;
`M4A_COMPRESSION_EXPANSION_CHARACTERIZATION_REPORT.md`; `M4A_COMPRESSION_EXPANSION_RESEARCH_LOG.md`; and the frozen
implementation (`scripts/m4a_compress/state.py`, `cohorts.py`, `outcome.py`, `analyze.py`).

**One new measurement, outcome-free.** §3 uses a diagnostic computed from the hashed BKV dev panel that touches **no
forward outcome** (state definition only, equivalent to the study's own `diagnostics.py`). It is the empirical basis for
the central finding. No window is spent at signal level.

---

## 1. Executive Finding

**The first experiment is predominantly a test of the current range level, not of compression.** The report diagnoses this
qualitatively ("the compression cohort is selected on a low recent range"); the diagnosis is correct but understated. An
outcome-free measurement shows the compression indicator is **~76 % collinear with the current short-run range level** and
**almost independent of the long-run term**:

| Quantity (BKV dev panel, D2 state, no outcome) | Value |
|---|---|
| `corr( pct(ATR10/ATR60) , pct(ATR10) )` — signal vs own-history level | **0.757** |
| `corr( pct(ATR10/ATR60) , pct(ATR60) )` — signal vs own-history long-run term | **−0.028** |
| mean own-history ATR10 percentile — compression / complement | **0.194 / 0.562** |
| P(compressed \| bottom-quintile ATR10 level) | 0.567 |
| P(compressed \| top-quintile ATR10 level) | **0.012** |
| share of compressed name-days also in bottom-quintile ATR10 level | 0.64 |

The ratio's **slow term contributes essentially nothing** to the signal's variation; the signal is the fast term. A name in
a high current range state is essentially *never* "compressed". So the four negative VAL cells are, to first order, the
persistence signature the protocol predicted — and the estimand never conditioned on the level.

**Is a level-controlled formulation the correct next experiment? The question is right; the formulation proposed in the
report (match on ATR10 level; keep the high-state persistence comparator) is not, and would likely fail or mislead.**
It over-controls a variable the signal is 76 % made of, conditions on a component/collider of the treatment, re-introduces
regression-to-the-mean by matching on a noisy level, and — crucially — keeps a **level-contaminated outcome** (forward range
÷ trailing 252-session median), which re-imports the level through the denominator.

**Decision (§11): B — the identification problem is better solved another way.** Keep the level-controlled *question* if
the mechanism is continued, but answer it with a **level-neutral forward-change outcome and a joint incremental-predictive
model with date fixed effects and a flexible level control**, benchmarked against a **fitted persistence null** — not by
cohort matching. A confirmatory read would additionally require a genuinely fresh surface; none of the primary equity-EOD
windows are fresh.

---

## 2. What the First Experiment Actually Established

Frozen construct (protocol §5–§7; `state.py:56–70`, `cohorts.py:27–31`):

- `ratio_t = ATR10_t / ATR60_t`, `ATR_n = mean((H−L)/C[s−1], n)`;
- `pct_t` = `#{s ∈ [t−251,t] : ratio_s ≤ ratio_t}/252`; compression `C = [pct ≤ 0.20]`, onset (no compression in prior 20);
- comparators `N` = the literal complement, `P` = high state `[pct ≥ 0.80]`, onset-mirrored;
- outcome `E_range = mean_{t+1..t+h}(range) / median_{t−251..t}(range)`, `h ∈ {5,20}`;
- estimand `d(t) = mean_C(E) − mean_X(E)`, cohort-by-date, Newey–West lag `h`, 4 primary cells, Holm on VAL.

**Established:**

1. The level-uncontrolled contrast is **strongly and pervasively negative**: all four VAL cells (d̄ = −0.059 … −0.232), all
   four TRAIN cells, all 44 year-by-cell values; the block-bootstrap CI excludes zero on the negative side in every cell.
2. The **MDE is small (0.036–0.059)** relative to the observed effects, so the design *does* exclude a positive effect of
   ~4–6 % (in units of the name's trailing-median range) at the level-uncontrolled granularity. That is a real, if narrow,
   exclusion.
3. The sign is exactly what **volatility persistence** predicts, and the same sign appears on random regime-switching
   synthetic data (log L13). So the run functions as a **strong persistence diagnostic**, not an M4a measurement.
4. Robustness and verification are clean (VP1–VP5 pass; A1 touched the verifier only).

**Not established:** anything about a compression effect *beyond the current level*. The report says this (§1, §10); this
review quantifies why the proposed successor does not fix it.

---

## 3. Identification Problem

### 3.1 Formal decomposition

Let `Y` be the forward expansion outcome, `C` the compression event, `L` the current short-run range level, and `M` the
longer-run range level, with `ratio = L/M`. The first experiment estimates

```
E[Y | C] − E[Y | ¬C]  =  { level/persistence effect }  +  { incremental compression effect } .
```

Because `C` is selected on `ratio` and `ratio` is 76 % collinear with `L`, the first term is large and negative (forward
range tracks recent range), while the second term — the only M4a-relevant part — is **unidentified** by this contrast. A
negative total therefore says nothing about the sign of the incremental term.

### 3.2 The two hypotheses the experiment cannot separate

- **A — mechanical level:** `L` low today ⇒ forward range low (persistence). No "compression" mechanism; just
  autocorrelation of volatility.
- **B — compression:** *unusually* low `L` relative to the name's own longer-run `M` ⇒ forward range **rises** from the low
  level (a rebound) more than for names with the same `L` but no relative compression.

The observed negative d̄ is fully consistent with A and carries no information about B. The contrast never holds `L` fixed.

### 3.3 Why "compression" has collapsed onto the level

`ratio = exp(a − b)` with `a = log ATR10`, `b = log ATR60`. `b` is a 60-session mean and moves slowly; its own-history
percentile is nearly uncorrelated with the ratio's (corr = −0.028). So the ratio's cross-time variation is dominated by `a`.
Empirically (above): `corr(pct ratio, pct ATR10) = 0.757`, and `P(compressed | top-quintile ATR10 level) = 0.012`. **The
construct as specified is, in operation, "the current short-run range is low".** Any successor that ignores this is testing
the level again under a new name.

### 3.4 The outcome is not level-neutral either

`E_range = mean_{t+1..t+h}(range) / median_{t−251..t}(range)`. The numerator is essentially the forward **level**; the
denominator is a slow trailing **level**. In a level-persistent world this ratio is another level statistic. Indeed the
cohort means reported (§5 of the report) are `E(C) ≈ 1.03`, `E(N) ≈ 1.18`, `E(P) ≈ 1.26` — i.e. they order exactly by
level. The report's own numbers show forward range for compressed names landing near their trailing median: relative to the
*low current* level that is incipient expansion, but the estimand measures the forward level, not the expansion from `L`.
**A level-controlled question needs a level-neutral outcome, or it just re-measures `L`.**

### 3.5 The treatment shares structure with any level control

Any control built on `ATR10` is built on the **numerator of the treatment**. Fixing `a` leaves `ratio = a − b` varying only
through `b`. So "does the ratio predict expansion beyond the level" is, algebraically, **"does the older part of the range
history (`b`, or more precisely days t−59..t−10) predict forward expansion beyond the recent 10-day level (`a`)?"** That is a
legitimate but different question — a *term-structure-of-realized-range* question — and it should be named as such, with its
own prior. It is not obviously the colloquial "coiled spring → expansion".

---

## 4. Candidate Control Designs

Assessed against three pathologies: **over-control** (removing the mechanism), **collider/Berkson bias**
(conditioning on a common consequence), and **mechanical regression-to-the-mean** (selecting/matching on a noisy variable).

| Control | What it does | Verdict | Why |
|---|---|---|---|
| **Match on ATR10 percentile** (own-history) | Pairs compressed names with names at the same own-history level | **Reject as primary** | Conditions on a variable that is 76 % the treatment (over-control); matching on a *noisy* percentile induces regression-to-the-mean; `ratio = L/M` makes `L` a common parent, so selecting on `ratio` while conditioning on `L` is a collider/Berkson design |
| **Match on absolute normalized ATR10/range** (cross-sectional, within date) | Same-dollar-volatility pairing | **Weak** | Controls the market vol regime (good) but volatility levels are persistently name-specific, so matches are sparse and cross-regime; does not fix the noisy-level regression problem and still conditions on the treatment numerator |
| **Stratify by current range level** (bins) | Nonparametric level control | **Acceptable as a design-based check, not primary** | Transparent, no functional form; but with ~3–4 compression names per date, date×level-bin cells are near-empty → attrition. Use pooled within-level bins, not date-by-bin cells |
| **Residualize `ATR10/ATR60` against ATR10 level** | Orthogonalizes the ratio to the level | **Reject** | Regressing a ratio on its own numerator is mechanically contorted (`corr(a,b) ≠ 0`); a linear residual of `a − b` on `a` is dominated by `−b` and mis-specified; can create spurious dependence |
| **Regression / ANCOVA** (joint model, date FE, flexible level control) | Uses all events, no matching attrition | **Accept as primary, with conditions** | Conditions are: (1) work in **logs**; (2) include **both** `a` and the compression term (so `b` is not collinear with `a`); (3) use a **level-neutral outcome**; (4) benchmark against a **fitted persistence null**, not a raw comparator |
| **Alternative formulation — level-invariant shape measure** (e.g. efficiency ratio / variance ratio / range-to-path) | A compression proxy that is level-neutral by construction | **Defer** | Genuinely different and avoids the shared-numerator trap, but weak repo/Vault precedent and the task forbids proliferating indicators. Keep as a fallback only |

**Cross-cutting:** matching is not automatically correct here. Every design that *holds `L` fixed* and *tests `ratio`* is
holding fixed a variable that is a component of the treatment. That is inherent to using a ratio of two levels as the signal.
The only clean escapes are (i) a **joint model** that separates the fast and slow levels rather than "matching" them, and
(ii) a **level-neutral outcome**.

---

## 5. Recommended Identification Strategy

If M4a is continued, the identification should be an **incremental-predictive (Granger-style) test**, not a cohort match:

1. **Level-neutral outcome.** Measure expansion relative to the *current* short-run level, not a trailing median:
   `y^h_{it} = log( mean_{t+1..t+h}(range) / ATR10_{it} )`. Under pure persistence `y ≈ 0`; under M4a a compressed name
   should have `y > 0` relative to an equally-level name. Symmetric by construction; no direction.
2. **Joint model with date fixed effects and a flexible level control.**
   `y^h_{it} = α_t + f(a_{it}) + β · x_{it} + ε`, with `a = log ATR10`, `x = a − b = log(ATR10/ATR60)` (compression; low =
   compressed), `f` a spline or decile function of `a`, `α_t` date fixed effects absorbing the market vol regime.
   `β = 0` under pure persistence; **H1: β > 0** (relative compression predicts expansion beyond the current level).
3. **Design-based check (nonparametric).** Within date and within deciles of `a`, compare `y` between names in the bottom
   quintile of `x` and the rest. This is the "level-matched contrast" done correctly: pooling within level bins, with a
   level-neutral outcome, no hard matching.
4. **Fitted persistence null.** Fit a small autoregression of log-range on its own recent lags (or a stochastic-vol model)
   *without* `x`, and test whether adding `x` improves out-of-sample forecast skill for `y` (incremental R² / nested model).
   This is the correct "beyond persistence" statement; the raw high-state cohort is not.

**Why this is identifiable where matching is not:** the design matrix `[1, a, x]` (`x = a − b`) is full rank because `b`
varies; the coefficient on `x` equals the (negated) coefficient on `b` in `y ~ a + b`. It isolates the incremental
information in the **longer-run range level** (older history) beyond the recent level — the defensible content of
"compression".

---

## 6. Exact Estimand

For entity `i`, session `t`, horizon `h`:

- `a_{it} = log ATR10_{it}`, `b_{it} = log ATR60_{it}`, `x_{it} = a_{it} − b_{it}` (log compression ratio; low = compressed);
- outcome `y^h_{it} = log( mean_{s∈(t, t+h]}(range_s) / ATR10_{it} )` — forward expansion **from the current level**;
- level control `f(·)` fixed before the read (pre-registered basis/df), date effect `α_t`.

**Primary estimand (one-sided, symmetric, no direction):**

```
β_h  =  coefficient on x_{it} in   y^h_{it} = α_t + f(a_{it}) + β_h · x_{it} + ε_{it}

H0: β_h ≤ 0      H1: β_h > 0      (relative compression ⇒ forward range expands beyond the current level)
```

Secondary, same estimand on the design-based (within-level-quintile) contrast and on the persistence-residual outcome.

**What it explicitly is not:** no signed return, no entry/exit, no cost, no strategy. A positive `β_h` answers
*"does compression contain information about subsequent expansion beyond the current level of range?"* It says nothing
about direction or profitability.

---

## 7. Persistence Benchmark

**The old comparator is invalid after level control.** The high-state cohort `P` (`pct ≥ 0.80`) is *higher in level by
construction* (its mean ATR10 percentile ≈ 0.8 vs compression's ≈ 0.19). Using `P` while also controlling for level would
condition away the treatment and mix two controls. It must be dropped.

**The correct benchmark after level control is one of:**

1. **Level-matched non-compressed names** — the same `a`-decile, `x` not in its bottom quintile. This is the design-based
   persistence benchmark and is exactly what `β` in §6 uses as its implicit counterfactual.
2. **A fitted persistence forecast** — the model's own prediction of `y^h` from `a` (and its history) with `β` fixed at 0.
   The M4a claim is that the compression term adds skill beyond it.

Both are legitimate; the first is design-based, the second is model-based. The original "vs high-state" comparator should be
retired for the successor. (Note this is the same lesson as N200-HMM, which failed *against a persistence baseline*, not
against zero.)

---

## 8. Sample / Power Implications

Using the first experiment's realized sample and the outcome-free collinearity:

| Quantity | Value | Source |
|---|---|---|
| Compression events (D2) | TRAIN ~3,790 / VAL ~3,071 | report / diagnostics |
| Formation dates with ≥1 compression | TRAIN ~1,012 / VAL ~817 | report §4 |
| Compression names per formation date | ~3–4 | report §14 |
| Signal variance removed by a level control | `R² ≈ 0.757² = 0.573` | §1 diagnostic |
| Residual treatment variance | ~43 % | derived |
| Observed VAL MDE (level-uncontrolled) | 0.036–0.059 | report §3 |

**Attrition.** Hard matching on level bins would leave <1 compression name per date-bin and collapse the cohort-by-date
design. The joint model avoids this: it uses all ~3,000 compression events and the full comparator pool, with the level
entering as a flexible covariate. **Do not use hard matching; use regression plus a pooled within-level check.**

**MDE.** With ~43 % of the signal variance remaining after a level control, the residual-dimension MDE inflates by roughly
`1/√0.43 ≈ 1.5×`, i.e. to the order of **0.05–0.09** in the level-neutral outcome — still able to see a large rebound, blind
to a small one. This is a **limitation to report, not a reason to kill the mechanism** (the RFA lesson: do not abandon on an
assumed effect size). State the MDE per cell and let the data speak.

**Effective n.** ~800–1,000 independent formation dates per stage (as before); Newey–West lag `h`; date fixed effects absorb
the market-vol regime, which is the dominant common factor.

---

## 9. Spent-vs-Fresh Window Treatment

- **2012–2022 equity EOD is signal-spent** (register Q-1…Q-3, G-S1, MRLC E-3, N200 Q-4, BKV-1 Q-7; GR-1.3). It is usable only
  for **design/development carried as GR-1.4 non-confirmatory** — the first experiment's own status. A successor built and
  checked here confirms nothing.
- **Do not read the existing 2023-01-02 → present equity EOD window merely because it exists.** Under operator ruling R-11 it
  is signal-spent, and Q-6 reserves part of it for the CSMP momentum lineage. It is not a HOLDOUT for M4a.
- **Genuine confirmation requires an unread surface** (REGISTER §5–§6): `NSE_INDEX|India VIX` 1m 2022→2026 (V-0b, unread,
  value-verified), India VIX EOD 2010→2025 (V-0c, unread), or the **101 unread names** of the vendor N100 1m store 2015–2022
  (V-1 covers only Reliance). Each needs an operator register row **before** the read; the vendor store also needs provenance
  certification.
- **Consequence for design choice.** The broad daily-equity panel is exactly the surface that is spent; the fresh surfaces are
  index-level (VIX/Nifty) or intraday (vendor 1m, different cadence). A confirmatory M4a may therefore have to change
  substrate, which is a real cost to weigh before committing.

---

## 10. Failure Modes

1. **Over-control** — conditioning on ATR10 deletes ~57 % of the signal and the part that *is* "recent range is low". If the
   mechanism is literally the level, the control deletes M4a and the residual is a different (term-structure) effect.
2. **Collider / Berkson** — `ratio = L/M` is a common child of `L` and `M`; selecting on `ratio` and conditioning on `L`
   induces a spurious `L–M` relation and can bias `β` in either direction.
3. **Regression-to-the-mean** — matching or binning on a noisy level estimate makes "same-level" compressed names
   differentially noise-selected; forward change then partly reflects noise, not dynamics.
4. **Level-contaminated outcome** — keeping the trailing-median denominator re-imports the level; the test is then partly the
   first experiment again.
5. **Persistence masquerading as signal** — any positive `β` must beat a *fitted* persistence forecast, or it is just
   autocorrelation.
6. **Mechanical shared-term bias** — `a` and `x` share `a`; a naive regression without care (or residualizing a ratio on its
   numerator) manufactures spurious coefficients.
7. **Multiple testing / threshold drift** — the family must stay tiny (one treatment, two horizons, two comparators max);
   no percentile or window search (the task's own constraint).
8. **Definitional overreach** — concluding "compression works" from an effect that is really the longer-run range term, or
   "compression fails" from a level test. Name the mechanism precisely.
9. **Window double-spend** — reading the spent equity EOD (or the reserved 2023+ window) and calling a result confirmatory.

---

## 11. Decision: **B — the identification problem is better solved another way**

**Ruling.** The level-controlled *question* is the right one; the **matching formulation proposed in the report is not**,
and the honest next step — if any — is a **joint incremental-predictive test with a level-neutral outcome and a fitted
persistence null** (§5–§7), not a matched cohort contrast with the old high-state comparator.

Why B and not the others:

- **Not C (too confounded to justify another experiment).** The confound is severe (0.757 collinearity, shared numerator) but
  **not absolute**: in logs, `a` and `b` are separately identified (`[1, a, a−b]` is full rank), so the incremental content
  of the longer-run term is estimable. The confound rules out the *matching* design, not every design.
- **Not D (another formulation first).** A level-invariant shape measure (efficiency/variance ratio) is the only genuinely
  different formulation and is deferred, not prioritised — the task forbids proliferating indicators, and the incremental
  term-structure test directly targets the stated question.
- **Close to A, with a methodological correction.** If the operator insists on a design-based (nonparametric) test, it must
  be a **within-level pooled contrast on a level-neutral outcome** — which is A done correctly. But the report's specific
  proposal (match on ATR10 percentile, keep `P`) would not be defensible, which is why the label is B.

**Caveat that rides with B.** Because the signal is 76 % the level and the fresh confirmatory surfaces are index/intraday,
the operator should decide **whether the plausible residual effect (the longer-run range term) is of interest at all** before
committing a fresh window. If the answer is no, M4a should be left as a documented C (open, non-confirmatory) and the
program should move on — that is a legitimate and perhaps the best outcome. This review does not manufacture a reason to
spend a window.

---

## 12. Proposed Next-Step Specification (concept only — **not a protocol, not frozen**)

If the operator elects to proceed, the smallest defensible design is:

| Element | Proposed value |
|---|---|
| **Question** | Does a low `ATR10/ATR60` state predict forward range expansion **beyond the current short-run range level**? |
| **Signal (continuous, no threshold)** | `x = log(ATR10) − log(ATR60)` (equivalently `log(ATR10/ATR60)`); the effect is tested as a coefficient, not a percentile cut |
| **Level control** | `a = log(ATR10)`, entered through a pre-registered spline/decile basis `f(a)`; plus date fixed effects |
| **Outcome (level-neutral, symmetric)** | `y^h = log( mean_{t+1..t+h}(range) / ATR10_t )`, `h ∈ {5, 20}`, `range = (H−L)/C[s−1]` |
| **Estimand** | `β_h` in `y^h = α_t + f(a) + β_h x + ε`; **H1: β_h > 0** one-sided |
| **Persistence benchmark** | (i) level-matched within-decile contrast; (ii) fitted no-`x` persistence forecast, `β=0` null |
| **Inference** | Newey–West (lag = h) or cluster-robust by date; ≤ 2 horizons; report MDE per cell |
| **Universe / substrate** | PIT top-200 daily equity for **design/development only** (spent); a fresh surface chosen by the operator for any **confirmation** |
| **Windows** | Stage labels are the operator's; the spent panel may be used GR-1.4 non-confirmatory only |
| **Stopping rule** | If the level-controlled `β` is not positive, M4a is left open-but-unpromising; no threshold search, no second estimator, no comparator rescue; no spent-window read may be labelled confirmatory |
| **Refused** | re-specifying ATR windows, percentiles, horizons, or comparators after seeing a result; hard matching on level as the primary design; any holdout read; any directional/trading arm |

**Not done here:** no code, no protocol, no freeze, no window read. This section exists so that a future agent starts from a
clean, level-controlled, symmetric specification rather than another level test.

---

## Appendix — evidence pointers

- Construct: `scripts/m4a_compress/state.py:56–70`, `cohorts.py:27–31`; outcome `outcome.py:43–63`; estimand `analyze.py:55–89`.
- Results: `M4A_COMPRESSION_EXPANSION_CHARACTERIZATION_REPORT.md` §3–§7 (VAL d̄ −0.059…−0.232; MDE 0.036–0.059; all years negative).
- Persistence prediction and limits: protocol §11(iv), §12; report §1, §10.
- Outcome-free collinearity diagnostic (this review): `corr(pct ratio, pct ATR10) = 0.757`; `P(compressed | top-quintile ATR10) = 0.012`; state vs onset caveat — the diagnostic is on the state (`pct ≤ 0.20`), and the onset cohort is a subset, so the collinearity conclusion carries over a fortiori.
- Spent/fresh windows: `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` §3–§6, §11; GR-1.3; ruling R-11; Q-6.
