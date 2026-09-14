# PTMS — Gann Pre-Registration Design Decisions (A–E)

**Date:** 2026-09-14 · **Branch:** `research/ptms-price-time-market-structure`

**Status:** DESIGN RECOMMENDATIONS. **Not a pre-registration. Nothing frozen.** Answers the operator's
priority list A–E from textual Gann evidence and outcome-independent reasoning only.
- No market data or outcome was read.
- No RFA declaration was written or run; §E is arithmetic from `scripts/rfa/power.py` only.
- No TRAIN/HOLDOUT read, backtest or parameter fit.

**Follow-up (added after `1247b8c`):** `PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md` completes the
*45 Years* reading and recommends changes to §D.4 (GF-7, GF-8 and GF-9 excluded from Stage 1), §E.4
item 1 (2023–2026 freshness unresolved, not indicated spent), §E.5 option 1 (screen window ends
2022-12-30) and §E.5 option 2 ("deferred, not retired"). The text below is unedited; those
recommendations await operator ruling.

**Inputs:**
- `PTMS_GANN_PRIMARY_SOURCE_CLAIM_REGISTER_2026-09-14.md` — F0, Δ1 (§26), **Δ2 (§27, *45 Years in
  Wall Street*)**.
- `PTMS_GANN_FAITHFUL_CONSTRUCT_DEFINITION_2026-09-14.md` — §§0–11 and **addendum §12**.
- `PTMS_GANN_CONSTRUCT_CATALOGUE_2026-09-14.md` §§21–22.
- `scripts/research/ptms_gann/gf_power_sketch.py` — pure arithmetic.
- `scripts/research/ptms_gann/phi_null_check.py` — synthetic random numbers only (null sd and
  attenuation of a binary-on-binary IC).
- Operator acceptance message of 2026-09-14 (rulings 1–12).

**The research question:** does Gann's documented price-time framework contain a reproducible
statistical edge? The target is the most faithful, pre-specified, statistically viable test — not a
convenient modern proxy.

---

## 0. Summary

| # | Question | Answer |
|---|---|---|
| **A** | Are *45 Years* and *How to Make Profits in Commodities* necessary before freeze? | ***45 Years*: yes — and reading it changed the design.** It supplies Gann's swing detector, outcome rule, relative time overbalance, percentage rules and day windows. About 45 printed pages remain unread and should be read before any freeze. ***Commodities*: not before a stock freeze.** The supplied copy is an Italian translation and is inadmissible for wording |
| **B** | Keep GF-2 partial or exclude it? | **Exclude GF-2 from the first faithful experiment.** Gann defers the angle rules to a course not supplied, and GF-2 needs the translation ruling. A partial test would be misread as "Gann angles fail" |
| **C** | Price / chart-space translation for GF-2 / GF-3 / GF-4P | **The text cannot resolve it.** Gann never converts his point rules across price levels or currencies, though he notes they depend on price level. **Design resolution: two stages.** Stage 1 is translation-free. Stage 2 (GF-3, GF-4P, TIM-10, the 1949 point rules) needs the U-LIT ruling. Recommendation: admit U-LIT as a declared literal assumption for stage 2 only |
| **D** | Primary cell per surviving construct | **Seven stage-1 primaries:** GF-1, GF-4T/R8, GF-5, GF-6, GF-7, GF-8, GF-10. GF-9 is secondary. Shared pins: 3-Day Chart detector, calendar days, Rule 10 outcome, Rule 9 market state, weekly formations with a 5-session horizon, and a **surrogate-differenced IC as the pass statistic** (§D.3). m = 7 |
| **E** | Enough power to justify an RFA before any outcome read? | **No.** Every stage-1 score and Gann's Rule 10 outcome are binary, which attenuates any borrowed effect size by 0.26–0.61 (§E.2). At the central band no primary reaches 0.80 inside 10 forward years: the best (GF-4T/R8, GF-1) need 14–16 years; GF-7 and GF-10 33–38; GF-5, GF-6 and GF-8 88–350. **At the optimistic corner, GF-5, GF-6 and GF-8 fail on any forward window of 10 years or less** (10.0, 13.3 and 39.0 years). **Recommendation:** no RFA declaration now. The development span can test only whether effects of the optimistic size exist — the size a forward test would need — for GF-1, GF-4T/R8, GF-7 and GF-10 (§E.5) |

**Rulings affected.** §A's reading contradicts accepted ruling 7 ("Keep relative time-overbalance
unresolved / Arm 2") on primary evidence (register §27.5). GF-10 is carried here **pending operator
acceptance**. If the operator does not accept it, drop GF-10: m becomes 6 and nothing else in §D changes.

---

## A. Are *45 Years in Wall Street* and *How to Make Profits in Commodities* necessary before freeze?

### A.1 *45 Years in Wall Street* (1949) — necessary

Reading chapters II and IV to IX (register §27.1) showed that the pre-*45 Years* design was built on
assumption slots Gann had already filled. Every item below was read on the page:

| Design slot | Before Δ2 | Gann's 1949 text |
|---|---|---|
| Swing detector K | Undefined; any detector a modern choice (SWG-05/06) | **3-Day Chart construction rule**, calendar days (pp. 61, 63) |
| Outcome "change in trend" | O1/O2 from 1930/1953; otherwise open | **Rule 10**: break of the last 3-Day-Chart low, or cross of the last upswing top (p. 13) |
| Relative time overbalance | NOT FOUND → Arm 2 | **Rule 8**, verbatim; time ranked above price (pp. 11–12) |
| Percentage / retracement | NOT FOUND | **Rule 3** and **ch. IV** percentage bands (pp. 8, 30–38) |
| Time windows, tolerance | Free *w* | **Rule 8 day windows with widths** (p. 11) |
| Anniversary | Month / year (1930, 1936) | **Ch. IX anniversary dates**; Rule 10 exact years and months (pp. 13, 92–93) |
| Duration norms | Weeks and months (1930, 1936) | **Rule 4** day norms (pp. 8–9) |
| Culmination | 3rd/4th move (1930) | **Rule 8 diminishing sections** (p. 12) |
| Price basis | Gann silent | Prefers actual selling prices over split-adjusted averages (p. 60) |

**Why "necessary", not "useful":** freezing without it would have frozen modern substitutes for rules
Gann published — a modern pivot detector, a modern outcome, Arm-2 overbalance. The brief forbids
exactly that ("Do not invent a modern fractal/pivot detector and claim that it is Gann's definition").

**Still unread** (printed pages): 46–55 (rest of ch. V), 64–73 (ch. VII), 76–81 (ch. VII), 84–89
(ch. VIII), 96–99 (ch. IX), 102 to end (chs. X–XVI except 100–101). Pages 46–55 and 64–73 sit inside
chapters that supply stage-1 rules (greatest time period; the 3-Day Chart).
**Recommendation:** read them before any freeze.
- This is cheap and involves no outcome.
- The failure mode of register §20 item 8 (freezing before reading a supplied text) should not be
  repeated a third time.

### A.2 *How to Make Profits in Commodities* — not necessary before a stock freeze

- **The supplied copy is an Italian translation** (register §27.1). A translation cannot verify
  wording, so it cannot settle any claim this programme needs.
- The claim it was expected to settle — time overbalancing price and volume (F0-TOB-03) — is now
  verified in *45 Years* p. 10.
- Its remaining content is commodity-specific. The stock arm does not depend on it.
- **If commodities are ever tested, an English original is required first.**

### A.3 *How to Make Profits Trading in Puts and Calls* — not inspected

Not requested under A. Its relevance to stock price-time rules is **assumed low from the title only**;
that assumption is unverified. A contents-page check before freeze would close it.

---

## B. Must GF-2 remain partial, or be excluded from the first faithful experiment?

**Recommendation: exclude GF-2 from the first faithful experiment.**

1. **Gann withholds the rules.** [MMPTC] p. 6 defers all angle rules to the *Master Forecasting
   course*, which was not supplied. The only stated rule is a break below 45° on the inner square
   (p. 5). A test of that single rule is not a test of Gann's angle method. A null result would be
   reported — and remembered — as "Gann angles do not work", which the evidence could not support.
2. **Translation dependence.** GF-2 needs U-LIT, and so do the 1949 point rules. Its result would be
   conditional on a ruling that stage 1 avoids.
3. **Placement is ambiguous.** Several origins are admissible (0, low, high, squares of high/low/range,
   halfway) with no selection rule. The inner square from 72 multiplies them.
4. **No loss of framework coverage.** Stage 1 still tests Gann's time rules, his overbalance rule
   (which carries a price leg) and his percentage rules.

**What would re-admit GF-2:** the Master Forecasting course (primary text) **and** the translation
ruling. Until then it stays Arm 1 *framework* with no experiment. If the inner-square rule is ever run
alone, label it "GF-2 inner-square 45° break rule only — not a test of Gann's angle method".

---

## C. Price / chart-space translation for GF-2, GF-3 and GF-4P

### C.1 What the text says

- **1953:** stocks are 1 point per space on the daily chart. Scales are per instrument and per chart,
  with other scales in Special Instructions not supplied (register Δ-02).
- **1949:** point rules are everywhere — Rules 2, 6 and 12, the 9-Point Chart, the 5-point rule
  (register Δ2-17). Gann signals price-level dependence without converting it:
  - stops "depending upon how high stocks are selling" (p. 8);
  - pyramiding works best in active high-priced stocks (pp. 21–22);
  - 6¼% matters at very high levels (ch. IV).
- **1949 also gives scale-free rules:** percentages of the stock's own prices (Rule 3, ch. IV), and
  comparisons of one move with the previous move in the same stock (Rule 8).

**Conclusion: no textual resolution exists.** Gann states nominal-point rules for 1920s–1950s US
prices, recognises that price level matters, and gives no conversion. Any conversion — percentage
rescaling, price bands, σ or ATR — is a modern addition. Ruling 6 already keeps those in Arm 2.

### C.2 Design resolution — two stages

| Stage | Constructs | Needs U-LIT? | Price basis |
|---|---|---|---|
| **1 — translation-free** | GF-1, GF-4T/R8, GF-5, GF-6, GF-7, GF-8, GF-10 (primaries); GF-9 (secondary) | **No.** Durations; percentages of the stock's own prices; point comparisons within one stock | As-of-*t* ratio-adjusted series (ratios and durations are invariant to bonus and split ratios). Exclude windows spanning non-ratio events |
| **2 — conditional** | GF-3, GF-4P, TIM-10, Rule 2/6/12 point rules, 9-Point Chart; GF-2 only if the course is obtained | **Yes** | As-traded (Gann p. 60 preference); CA-POL from definition §1.4 |

**Recommendation on the ruling itself (operator's decision):**
- **Admit U-LIT as a declared literal assumption for stage 2 only.**
  - It is the only reading that adds nothing to Gann.
  - Its cost is known in advance: under U-LIT a ₹3,000 stock and a ₹100 stock produce structurally
    different event sets.
- **Mandatory for stage 2:**
  - price-level strata reported as a diagnostic;
  - scale placebos at ₹0.8 and ₹1.25 per space;
  - no rescaling.
- **If refused,** stage 2 is `NOT FAITHFULLY TESTABLE FROM PRIMARY SOURCES` (register §26.5).
  Stage 1 is unaffected.

**Stage 2 is not pre-registered until stage 1 has concluded.** Its constructs are sparse (under U-LIT
many N100 price numbers exceed the data span in weeks or months), so its power case is weaker still
(§E).

---

## D. Primary cell per surviving construct, without looking at outcomes

### D.1 Rules for choosing a primary cell

A cell is primary only on a written reason drawn from the text or from statistical design. The order
of preference:
1. Gann specifies it.
2. Gann ranks it ("most important").
3. Several independent Gann texts agree on it.
4. It avoids an invented slot.
5. It keeps the outcome windows independent (non-overlap).

No choice below uses, or could have used, a market outcome.

### D.2 Shared pins (all stage-1 primaries)

| Slot | Pin | Reason |
|---|---|---|
| Swing detector **K3** | Strict 3-Day Chart, [45Y] p. 63; the 2-day exception not applied | Gann's rule. The exception is discretionary ("except when…"), so applying it would be an invention. Declared departure |
| Time unit **T** | Calendar days | [45Y] p. 61; ch. VI tables. GF-1 (1953 admits both) pinned to the same convention |
| Outcome **O-R10** | K3 trend-change signal: break of the last swing low (trend was up) or cross of the last swing top (trend was down) | [45Y] p. 13 — Gann's own change-in-trend signal |
| Market state **S9** | Last two K3 tops and bottoms both rising = bull; both falling = bear | [45Y] p. 12 (Rule 9) |
| Anchors | "Any high or low" = confirmed K3 turning points; "extreme" = to-date extreme in the store, left-censored at 2011-03-25 with listing date disclosed | Rule 8, ch. IX; definition §1.3 |
| Formation | Last session of each calendar week; eligible names per construct | Weekly cadence with non-overlapping outcomes |
| Horizon *h* | **5 sessions** (the next week) | Statistical design, not Gann: *h* equal to the formation spacing keeps outcomes non-overlapping, which the power arithmetic assumes. Longer *h* (15 sessions ≈ Rule 4's 3 weeks) is robustness only |
| Statistic | Per-date cross-sectional Spearman IC of construct score vs O-R10, **minus the same IC computed on per-stock surrogate price paths through identical K3 machinery** (§D.3). Both sides are binary, so the IC is φ (§E.2) | Swing mechanics produce duration and timing regularities in noise |
| Pooling | N100 PIT, per-stock construction, date-clustered inference | Definition §1.8; ruling 9 |
| Multiplicity | **m = 7** primaries, Bonferroni α = 0.05/7 one-sided | One cell per construct |

### D.3 Why the pass statistic must be surrogate-differenced

This follows from construct mechanics, not from data.
- In a random walk, a decline that has already lasted longer than the previous decline is more likely
  to break the last swing low within a week, because it has had more time to do so.
- Turns on a 3-Day Chart cluster at the typical swing length, so windows at 7–12 or 18–21 days from
  a turn will catch turns in noise.

A zero-IC null would therefore "confirm" Gann on noise. The primary statistic must be the excess over
surrogate paths. Candidate surrogate: a per-stock stationary block bootstrap of daily returns,
preserving volatility clustering. The method is to be pinned in the pre-registration. Coverage-matched
placebo windows (definition §1.7) are an additional control, not a substitute.

### D.4 Primary cells

| Construct | Primary cell | Textual reason | Robustness (off the pass path) | Required controls |
|---|---|---|---|---|
| **GF-10** time overbalance *(pending ruling 7)* | Stock in S9 bull state, in a K3 decline. Score 1 from the first session its calendar-day duration exceeds the **immediately preceding** K3 decline's duration. Bear mirror pooled with sign | Rule 8 verbatim; "the previous decline" in the paired price clause | Greatest prior decline (p. 39); price overbalance leg; *h* = 15 | Surrogates; price overbalance (Gann ranks time above it); GF-8; momentum, σ |
| **GF-6** reaction duration | Bull-state K3 reaction exceeding **65 calendar days** without a new high | Three texts agree on about two months: WSSS monthly rule, NSTD p. 38, [45Y] Rule 4 "60 to 65 days … the greatest average time" | 3–4 weeks (WSSS weekly; needs the "active" filter); 6–7 weeks | Surrogates; placebo thresholds (40 / 90 days) |
| **GF-7** culmination | Rule 8 diminishing section: bull-state K3 upswing number ≥ 3 whose price gain **and** duration are both below the previous upswing's. Score at confirmation | [45Y] p. 12 states it with both legs; Rule 5 p. 9 gives the 3–4 count | 3rd/4th move alone (WSSS); 6–7 weeks fast move | Surrogates; placebo counts (2nd, 5th); one leg only |
| **GF-8** percentage | Close within 45–50% below a confirmed K3 top formed while S9 was bull (the reaction's own high); score = inside the band | **Anchor chosen on wording:** Rule 3 says "a 50% decline from **any** high level", so the rule sentence governs over ch. IV's importance ranking. The wider anchor does not rescue power — the flag stays sparse (§E) | To-date extreme high (ch. IV "of greater importance"); halfway of extreme range; 100% advance from low; other bands | Placebo bands (38–43%, 53–58%); surrogates |
| **GF-4T/R8** day windows | Score 1 if next week's sessions fall inside any Rule 8 window counted from the **last confirmed** K3 top or bottom | Gann supplies the unit and widths (p. 11) — no free tolerance | All K3 turns in the last 185 days; [MMPTC] circle tier D1 + quarters; importance weighting | Coverage-matched placebo windows; surrogates |
| **GF-1** Master Square | Score 1 if next week contains a date *n* ∈ P4 = {36, 48, 72, 96, 108, 144} calendar days (repeating every 144) from the to-date extreme high or low | [MMPTC] p. 4 names P4 as where "most changes in trend occur"; P8 is the broader "strongest points" list | P8; weeks and months as units; K3 turns as anchors | Placebo fractions of 144; coverage-matched null; surrogates |
| **GF-5** anniversary | Monthly: score 1 if the calendar month is the month of the stock's to-date extreme high or low, anchor ≥ 12 months old. **Outcome variant:** an "important" change — an O-R10 signal whose following K3 swing outlasts the preceding swing (Rule 8's own importance criterion) | Ch. IX rule sentence is at month resolution; WSSS p. 55 and NSTD p. 14 agree on yearly repetition | Rule 10 exact 1–5 years at day resolution; 15/22/34/42/48/49 months | Random-anchor anniversaries (seasonality); placebo lags (10 / 14 months) |
| GF-9 modal duration (secondary) | Score 1 if the current K3 swing's duration reaches the stock's modal bin of past swings | Ch. VI p. 57. Literal on averages, so a per-stock version is an extension, hence secondary | Median / 75th-percentile placebos | Surrogates |

### D.5 Overlaps and exclusions

- **GF-6 and GF-10** share K3 reactions, and one event can trigger both. Report their joint
  incidence and an attribution table. The multiplicity count stays at 7, because both are tested.
- **GF-4T/R8 and GF-1** coincide at 48 days (42–49 window). Report coincident flags once.
- **Excluded from N100** (identical for every stock, so a rank IC has nothing to rank): Rule 8 seasonal
  dates, Rule 10 holiday dates, ch. VIII months of extreme highs. Index design only (Family C/D).
- **Open items the pre-registration must still pin:**
  - surrogate method and draw count;
  - eligible-name floor per date;
  - handling of non-ratio corporate-action windows;
  - the GF-5 importance-outcome confirmation lag;
  - the reading of [45Y] pp. 46–55 and 64–73 (§A.1), which could qualify K3 or GF-10.

---

## E. Is there enough power to justify an RFA before any outcome read?

### E.1 Contract fit

- The stage-1 design fits the RFA `rank_ic` contract. The declared quantities are the mean per-date IC
  (delta) and its dispersion (sd).
- `per_trade_pnl` is unsuitable. There is no position rule, and a single-time-series Sharpe runs into
  the √T wall that killed RS-MOM.
- Noncentral t, ncp = δ·√n/sd (`scripts/rfa/power.py`), one-sided, α = 0.05/7 = 0.00714.

### E.2 Bands and the binary-statistic correction

| Input | Optimistic | Central | Pessimistic | Defence |
|---|---|---|---|---|
| Latent δ | 0.06 | **0.03** | 0.01 | Central anchored on CB-N50 HOLDOUT IC +0.029 — a continuous feature vs a continuous forward return, **on a different hypothesis**. Borrowed; **no independent Gann-specific effect-size evidence exists** |
| Attenuation to φ | × *a*(*p*, *q*) | same | same | Stage-1 scores are Gann's binary rules and O-R10 is binary. Under a bivariate-normal threshold model, φ ≈ ρ·φ(*z_p*)·φ(*z_q*)/√(*p*(1−*p*)*q*(1−*q*)). Checked on synthetic data (`phi_null_check.py`): simulated vs analytic means agree within 0.001 except at *p* = 0.02 |
| sd of per-date IC | 1/√(*k*−1) | ×1.5 | ×2 | The permutation-null sd of a correlation is 1/√(*k*−1) for **any** margins. Simulated 0.0995–0.1607 against 0.1005–0.1601; a margin-dependent formula was checked and rejected. The multipliers stand in for date clustering and surrogate differencing |
| Defined dates | × P(defined) | | | A date counts only if both score and outcome vary across the *k* names. Sparse flags lose dates (44% at *p* = 0.02, *k* = 40) |
| *k*, *p*, *q* | per construct | | | **Design assumptions, never measured.** *q* = 0.30 for all constructs (5-session Rule 10 base rate, assumed). *p* from construct geometry for GF-1, GF-4T/R8 and GF-5; from symmetry for GF-10; assumed for GF-6, GF-7, GF-8 and GF-9 |

**Correction record.** The first commit of this document (`cb7886e`) computed power as if the IC were
graded, with no attenuation and no undefined dates. It understated the required years by roughly 3× for
the dense constructs and far more for sparse ones. §E.3 supersedes it. The first version also gave
GF-8 *k* = 100, which was inconsistent with its sparse state definition.

### E.3 Results (script output, `scripts/research/ptms_gann/gf_power_sketch.py`; α = 0.05/7 one-sided; *q* = 0.30)

| Construct | role | *k* | *p* (basis) | attenuation | P(defined) | φ at central |
|---|---|---|---|---|---|---|
| GF-1 | primary | 100 | 0.29 (geometry) | 0.57 | 1.00 | 0.0172 |
| GF-4T/R8 | primary | 100 | 0.50 (geometry) | 0.61 | 1.00 | 0.0182 |
| GF-5 | primary | 100 | 0.17 (geometry) | 0.51 | 1.00 | 0.0153 |
| GF-6 | primary | 40 | 0.05 (assumed) | 0.36 | 0.87 | 0.0108 |
| GF-7 | primary | 50 | 0.20 (assumed) | 0.53 | 1.00 | 0.0159 |
| GF-8 | primary | 40 | 0.02 (assumed) | 0.26 | 0.55 | 0.0079 |
| GF-10 | primary | 45 | 0.40 (symmetry) | 0.60 | 1.00 | 0.0180 |
| GF-9 | secondary | 100 | 0.20 (assumed) | 0.53 | 1.00 | 0.0159 |

Power (optimistic / central):

| Construct | fwd 1y | fwd 3y | fwd 5y | fwd 10y | dev 15.5y (info only) |
|---|---|---|---|---|---|
| GF-1 | 0.47 / 0.05 | 0.96 / 0.15 | 1.00 / 0.27 | 1.00 / 0.55 | 1.00 / 0.78 |
| GF-4T/R8 | 0.52 / 0.05 | 0.98 / 0.17 | 1.00 / 0.30 | 1.00 / 0.61 | 1.00 / 0.83 |
| GF-5 | 0.06 / 0.02 | 0.23 / 0.03 | 0.43 / 0.05 | 0.80 / 0.09 | 0.95 / 0.14 |
| GF-6 | 0.06 / 0.02 | 0.18 / 0.03 | 0.33 / 0.04 | 0.66 / 0.07 | 0.87 / 0.10 |
| GF-7 | 0.18 / 0.03 | 0.62 / 0.06 | 0.87 / 0.10 | 1.00 / 0.22 | 1.00 / 0.37 |
| GF-8 | 0.03 / 0.01 | 0.06 / 0.02 | 0.10 / 0.02 | 0.21 / 0.03 | 0.35 / 0.04 |
| GF-10 | 0.21 / 0.03 | 0.69 / 0.07 | 0.91 / 0.12 | 1.00 / 0.26 | 1.00 / 0.42 |
| GF-9 | 0.40 / 0.04 | 0.93 / 0.13 | 1.00 / 0.22 | 1.00 / 0.48 | 1.00 / 0.71 |

Formations (defined dates) for power 0.80 and forward years:

| Construct | opt: n / years | **cen: n / years** | pes: n / years |
|---|---|---|---|
| GF-4T/R8 | 86 / 1.7 | **750 / 14.4** | 11,949 / 229.8 |
| GF-1 | 96 / 1.8 | **839 / 16.1** | 13,367 / 257.1 |
| GF-9 | 111 / 2.1 | **974 / 18.7** | 15,527 / 298.6 |
| GF-10 | 195 / 3.8 | **1,723 / 33.1** | 27,515 / 529.1 |
| GF-7 | 221 / 4.3 | **1,964 / 37.8** | 31,368 / 603.2 |
| GF-5 | 120 / 10.0 | **1,051 / 87.6** | 16,760 / 1,396.7 |
| GF-6 | 602 / 13.3 | **5,391 / 119.0** | 86,206 / 1,902.3 |
| GF-8 | 1,124 / 39.0 | **10,091 / 350.1** | 161,396 / 5,599.4 |

### E.4 Reading

1. **Which window counts.** Confirmatory evidence can only come after a freeze.
   - The exposure register records equity-EOD signal readers over 2011–2022 (Q-1 to Q-3, Q-5) and over
     2023-01 to present (`scripts/signal_engine/`, rows F-1 to F-5; `scripts/mrlc_test/`, E-3; ISD
     E-1/E-2).
   - Historical N100 EOD may be used, but not as pristine confirmation (operator exposure ruling).
   - The operator adjudicates; this document assumes forward-only confirmation.
2. **Central band: no primary reaches 0.80 inside 10 forward years.** The best are 14–16 years.
3. **Optimistic corner.**
   - The gate's verdict corner. **GF-5, GF-6 and GF-8 fail it on any forward window of 10 years or
     less.** The formal gate would return **ABANDON** for them on such a window.
   - GF-6's and GF-8's flag fractions are assumptions. At *k* = 40 and *q* = 0.30, the optimistic
     corner needs 13.3 years at *p* = 0.05 and 9.0 years at *p* = 0.08. A flag fraction of at least
     about 0.08 would bring either within 10 years (arithmetic from the same functions, not in the
     committed tables).
   - GF-1, GF-4T/R8, GF-7 and GF-10 would print **PROCEED** on a 2–5 year window. That means "not
     provably infeasible" only: the corner doubles a borrowed effect and puts the sd at the independence
     floor, and §D.3 says the true sd is higher.
4. **The figures are upper bounds.** They assume independent per-date ICs. Persistent state flags
   (GF-10, GF-6) and market-wide swing synchronisation make adjacent dates dependent; surrogate
   differencing adds variance.
5. **Why the binary statistic stays.** A graded score or a continuous forward-return outcome would
   escape the attenuation. Neither is Gann's: his rules are thresholds and his change-in-trend signal is
   an event. Swapping them in is the "convenient modern proxy" the brief rules out. If ever used, label
   it Arm 2.
6. **The demonstrability wall, fourth appearance** (C5, C4, F1, PTMS-Gann). It is arithmetic about δ,
   sd and calendar time. The binary nature of faithful Gann rules makes it steeper here than for a
   graded cross-sectional signal.
7. **What the development span can and cannot do.**
   - At the central corner, 15.5 years gives power of only 0.78–0.83 (GF-1, GF-4T/R8), 0.37–0.42
     (GF-7, GF-10) and ≤ 0.14 (GF-5, GF-6, GF-8). It **cannot** cleanly kill a central-sized effect.
   - At the optimistic corner it gives 1.00 for GF-1, GF-4T/R8, GF-7 and GF-10. Effects of that size
     are exactly what a feasible forward test would need.
   - So a development read can rule out the only effect size that would make forward confirmation
     practical. It cannot confirm anything.

### E.5 Answer and recommendation

**The constructs do not have enough power to justify a confirmatory RFA.** Do **not** write an RFA
declaration now. Operator options, in the order recommended:

1. **Declared non-confirmatory feasibility screen on 2011-03-25 → 2026-09-11** for GF-1, GF-4T/R8,
   GF-7 and GF-10 only. **Requires explicit operator authorization** (it reads outcomes).
   - Freeze the §D cells, the surrogate method and the decision rule first.
   - Pre-state the rule: a construct whose surrogate-differenced φ is not distinguishable from zero is
     retired from forward testing (the screen has power ≈ 1.00 against optimistic-size effects).
   - A pass earns only the right to pre-register a forward test.
   - **Two-stage selection:** the forward test's α must be pinned before the screen, over **all
     constructs entering the screen** (m = 4 here), not only the survivors.
   - Label every number non-confirmatory.
2. **Record GF-5, GF-6 and GF-8 as power-infeasible** under faithful binary scoring at the design
   assumptions in §E.2. The p values behind GF-6 and GF-8 are assumptions; revisiting them requires
   a written rationale that does not come from outcomes.
3. **Forward-only confirmatory design** without a screen: at least 15 years for the best constructs at
   the central band. Not recommended.
4. **Stop** the faithful Gann battery at the definition stage, recording the power finding as the
   reason.

Stage 2 (translation-dependent) has sparser events and should not be considered until stage 1 has
concluded.

---

## F. Governance

- **Nothing frozen, selected or approved.** Every pin above is a recommendation.
- No market data or outcome read; no RFA declaration, TRAIN/HOLDOUT, backtest or parameter fit.
- §E numbers are script output from pure arithmetic and synthetic random numbers
  (`gf_power_sketch.py`, `phi_null_check.py`). The sketch sets `power.ALPHA` in its own process and
  is not on any declaration path.
- SHA-256 values reported for these files are over the LF bytes as committed. Reproduce them with
  `git show HEAD:<path> | sha256sum`; a Windows checkout may convert to CRLF.
- Rulings 7 (GF-10) and 5 (GF-8, GF-9 additions) are affected and **pending operator acceptance**.
  Rulings 1–4, 6 and 8–12 are respected unchanged.
- The supplied PDFs are not committed. No family definition was modified. Nothing here states or
  implies that Gann's framework has predictive power.
