# PTMS — Gann Pre-Registration Design Decisions (A–E)

**Date:** 2026-09-14 · **Branch:** `research/ptms-price-time-market-structure`

**Status:** DESIGN RECOMMENDATIONS. **Not a pre-registration. Nothing frozen.** Answers the operator's
priority list A–E from textual Gann evidence and outcome-independent reasoning only.
- No market data or outcome was read.
- No RFA declaration was written or run; §E is arithmetic from `scripts/rfa/power.py` only.
- No TRAIN/HOLDOUT read, backtest or parameter fit.

**Inputs:**
- `PTMS_GANN_PRIMARY_SOURCE_CLAIM_REGISTER_2026-09-14.md` — F0, Δ1 (§26), **Δ2 (§27, *45 Years in
  Wall Street*)**.
- `PTMS_GANN_FAITHFUL_CONSTRUCT_DEFINITION_2026-09-14.md` — §§0–11 and **addendum §12**.
- `PTMS_GANN_CONSTRUCT_CATALOGUE_2026-09-14.md` §§21–22.
- `scripts/research/ptms_gann/gf_power_sketch.py` (this commit) — pure arithmetic.
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
| **E** | Enough power to justify an RFA before any outcome read? | **No — not for a confirmatory test on any forward window the programme can realistically wait for.** At the CB-N50-anchored central band, no primary reaches 0.80 inside 3 forward years. The dense constructs need ~5.3 years; the state constructs 11–13; GF-5 23. Only the undefended optimistic corner clears within 1–3 years. The gate would print PROCEED, but that means only "not provably infeasible". **Recommendation:** do not declare an RFA now. The operator should choose between a declared non-confirmatory kill-screen on the development span, a ≥5-year forward design, or stopping (§E.5) |

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
| Statistic | Per-date cross-sectional Spearman IC of construct score vs O-R10, **minus the same IC computed on per-stock surrogate price paths through identical K3 machinery** (§D.3) | Swing mechanics produce duration and timing regularities in noise |
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
| **GF-8** percentage | Close within 45–50% below the to-date extreme high while S9 is bull; score = inside the band | Rule 3's band; "most important resistance levels are 50%"; 50% of the highest selling price ranked highest in ch. IV | Halfway of extreme range; 100% advance from low; other bands | Placebo bands (38–43%, 53–58%); surrogates |
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

### E.2 Bands (arithmetic assumptions, not estimates)

| Input | Optimistic | Central | Pessimistic | Defence |
|---|---|---|---|---|
| δ (mean surrogate-differenced IC) | 0.06 | **0.03** | 0.01 | Central anchored on CB-N50 HOLDOUT IC +0.029 — the repo's best out-of-sample cross-sectional association, **on a different hypothesis**. It is borrowed; **there is no independent Gann-specific effect-size evidence** |
| sd of per-date IC | 1/√(k−1) | ×1.5 | ×2 | The optimistic value is the independence floor. **Date clustering and surrogate differencing both raise sd**, so the "optimistic" corner assumes away known dependence |
| k eligible names | 100 for flag constructs; 40–50 for state constructs (names in a qualifying swing) | | | Design estimates, not measured |
| n | Formation dates per year × years | | | Weekly (52) except GF-5 (12) |

### E.3 Results (script output, `scripts/research/ptms_gann/gf_power_sketch.py`)

Power at forward horizons (optimistic / central):

| Construct | role | k | fwd 1y | fwd 2y | fwd 3y | fwd 5y | dev 15.5y (info only) |
|---|---|---|---|---|---|---|---|
| GF-1 | primary | 100 | 0.96 / 0.15 | 1.00 / 0.33 | 1.00 / 0.50 | 1.00 / 0.77 | 1.00 / 1.00 |
| GF-4T/R8 | primary | 100 | 0.96 / 0.15 | 1.00 / 0.33 | 1.00 / 0.50 | 1.00 / 0.77 | 1.00 / 1.00 |
| GF-5 | primary | 100 | 0.26 / 0.03 | 0.61 / 0.06 | 0.84 / 0.10 | 0.98 / 0.17 | 1.00 / 0.60 |
| GF-6 | primary | 40 | 0.57 / 0.06 | 0.91 / 0.12 | 0.99 / 0.18 | 1.00 / 0.33 | 1.00 / 0.86 |
| GF-7 | primary | 50 | 0.69 / 0.07 | 0.96 / 0.15 | 1.00 / 0.24 | 1.00 / 0.42 | 1.00 / 0.94 |
| GF-8 | primary | 100 | 0.96 / 0.15 | 1.00 / 0.33 | 1.00 / 0.50 | 1.00 / 0.77 | 1.00 / 1.00 |
| GF-10 | primary | 45 | 0.63 / 0.06 | 0.94 / 0.13 | 0.99 / 0.21 | 1.00 / 0.37 | 1.00 / 0.90 |
| GF-9 | secondary | 100 | 0.96 / 0.15 | 1.00 / 0.33 | 1.00 / 0.50 | 1.00 / 0.77 | 1.00 / 1.00 |
| GF-6m (month-end cadence) | rejected | 40 | 0.09 / 0.02 | 0.23 / 0.03 | 0.38 / 0.04 | 0.65 / 0.07 | 1.00 / 0.22 |
| GF-7m (4-week cadence) | rejected | 50 | 0.13 / 0.02 | 0.33 / 0.04 | 0.53 / 0.05 | 0.80 / 0.09 | 1.00 / 0.32 |

Formations required for power 0.80:

| Construct | opt: n / years | **cen: n / years** | pes: n / years |
|---|---|---|---|
| GF-1, GF-4T/R8, GF-8, GF-9 | 34 / 0.7 | **277 / 5.3** | 4,381 / 84.2 |
| GF-5 | 34 / 2.8 | **277 / 23.1** | 4,381 / 365.1 |
| GF-6 | 81 / 1.6 | **698 / 13.4** | 11,116 / 213.8 |
| GF-7 | 65 / 1.2 | **556 / 10.7** | 8,848 / 170.2 |
| GF-10 | 72 / 1.4 | **619 / 11.9** | 9,853 / 189.5 |

### E.4 Reading

1. **Which window counts.** Confirmatory evidence can only come after a freeze.
   - The exposure register records equity-EOD signal readers over 2011–2022 (Q-1 to Q-3, Q-5) and over
     2023-01 to present (`scripts/signal_engine/`, rows F-1 to F-5; `scripts/mrlc_test/`, E-3; ISD
     E-1/E-2).
   - Historical N100 EOD may be used, but not as pristine confirmation (operator exposure ruling).
   - The operator adjudicates; this document assumes forward-only confirmation.
2. **At the central band, no primary reaches 0.80 inside 3 forward years.**
   - The dense constructs need about 5.3 years.
   - The state constructs (GF-6, GF-7, GF-10) need 11–13 years; GF-5 needs 23.
   - Monthly cadence for GF-6 or GF-7 would need 43–58 years, which is why weekly is pinned. This is
     not a claim that cadence buys power — per-date IC dispersion is set by k, not by cadence. Weekly
     is simply the densest non-overlapping schedule available.
3. **The optimistic corner clears quickly** (0.7–2.8 years), so the formal gate would print
   **PROCEED**. That corner combines a doubled borrowed effect with the independence floor on sd, and
   the design itself (§D.3) says sd will be higher. PROCEED would mean "not provably infeasible" and
   nothing more — the O1 lesson.
4. **The figures are upper bounds.** They assume independent per-date ICs. Persistent state flags
   (GF-10, GF-6) and market-wide swing synchronisation make adjacent dates dependent, and surrogate
   differencing adds variance.
5. **The demonstrability wall again.** This is its fourth appearance (C5, C4, F1, now PTMS-Gann). It is
   arithmetic about δ, sd and calendar time. A better Gann construct cannot escape it, because the
   effect-size band is borrowed and the only lever is years.
6. **The development span is not confirmation, but it can kill.** At the central corner, 15.5 years of
   history gives power 0.86–1.00 for six of seven primaries (GF-5: 0.60).
   - A construct that shows no surrogate-differenced effect there, at that power, does not justify a
     multi-year forward wait.
   - A construct that does show one earns only the right to pre-register a forward test.
   - The read is asymmetric: it can refute and cannot confirm.

### E.5 Answer and recommendation

**The constructs do not have enough power to justify a confirmatory RFA on any realistic forward
window.** Do **not** write an RFA declaration now. The operator's options, in the order recommended:

1. **Declared non-confirmatory kill-screen on 2011-03-25 → 2026-09-11** (recommended next step,
   **requires explicit operator authorization** because it reads outcomes):
   - freeze the §D cells first;
   - pre-state that a pass is development evidence only and a fail retires the construct from forward
     testing;
   - label every number non-confirmatory.
2. **Forward-only confirmatory design of 5 years or more**, restricted to the dense constructs
   (GF-1, GF-4T/R8, GF-8). A smaller m would shorten it; that is not computed here, to avoid tuning
   the window.
3. **Stop** the faithful Gann battery at the definition stage, recording the power finding as the
   reason.

Stage 2 (translation-dependent) has sparser events and should not be considered until stage 1 has
concluded.

---

## F. Governance

- **Nothing frozen, selected or approved.** Every pin above is a recommendation.
- No market data or outcome read; no RFA declaration, TRAIN/HOLDOUT, backtest or parameter fit.
- §E numbers are script output from pure arithmetic. `gf_power_sketch.py` sets `power.ALPHA` in its
  own process and is not on any declaration path.
- Rulings 7 (GF-10) and 5 (GF-8, GF-9 additions) are affected and **pending operator acceptance**.
  Rulings 1–4, 6 and 8–12 are respected unchanged.
- The supplied PDFs are not committed. No family definition was modified. Nothing here states or
  implies that Gann's framework has predictive power.
