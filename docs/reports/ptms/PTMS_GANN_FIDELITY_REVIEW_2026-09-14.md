# PTMS — Gann Fidelity Review of the Construct Catalogue Shortlist

**Date:** 2026-09-14 · **Branch:** `research/ptms-price-time-market-structure`
**Reviews:** `PTMS_GANN_CONSTRUCT_CATALOGUE_2026-09-14.md` (commits `561d524`, `bb5d3aa`).
**The catalogue is not modified by this review.** Corrections it will need are listed in §9, not applied.
**Type:** governance review. No data store was queried, no outcome read, no RFA / test / backtest
run, no TRAIN/HOLDOUT created, nothing frozen, no family definition touched.

The question this review serves is **"does Gann theory contain anything real?"**, not "can something
Gann-like be made into a testable signal?". Where those diverge, this review sides with the first.

---

## 1. Executive answer

| Construct | Gann fidelity | Statistical cleanliness | Gann-specific content | Strongest generic-market explanation | Recommended status |
|---|---|---|---|---|---|
| **GO-2** Time overbalance | **HIGH** | **MEDIUM** | **MEDIUM** — the "largest prior reaction" reference and the claim that *time* outranks *price* | Swing mechanics: under any volatile path and a fixed swing rule, a correction that has lasted unusually long is mechanically more likely to become a trend break | **A. FAITHFUL GANN TEST**, valid only against a surrogate-swing null and the time-vs-price contrast |
| **GT-1** Pivot anniversary | **MEDIUM** (HIGH for the 360-day form) | **MEDIUM** | **LOW** at 365.25 days; **MEDIUM** only through the 360-vs-365.25 contrast and activity-matched anchors | Annual corporate / event calendar: major pivots cluster on results and event days, and those recur yearly | **A. FAITHFUL GANN TEST**, with a pre-declared attribution ladder (§5.5). The most likely positive result is **C** |
| **GA-3 / GS-5** Self-scaled 1×1 | **LOW** | **MEDIUM** | **LOW** | Momentum deceleration: the event is literally "the current leg's average speed fell below the prior leg's" | **B. GANN-INSPIRED MODERN REINTERPRETATION** (mean-of-swings form) · **C. GENERIC MARKET PROPERTY** (prior-leg and σ-rate forms) |
| **GT-2** Time symmetry | **LOW** | **MEDIUM** | **LOW** | Duration persistence from volatility clustering and swing-rule mechanics | **C. GENERIC MARKET PROPERTY** — remove from the Gann battery; usable as a control covariate for GO-2 |

**Two findings against the catalogue I produced:**
1. **I overstated GA-3's fidelity.** The catalogue called the rate equality "the only dimensionally
   valid 'square' with a privileged 1". That is true only under requirements *I imposed* — scale-free
   across stocks, no exogenous constant — and those requirements remove the very thing that made
   Gann's 1 privileged (§6).
2. **I mislabelled the faithful angle and square forms (GA-1, GS-2) as "dimensionally invalid".**
   A fixed price-per-time constant is dimensionally legitimate. Their real defect is that the theory
   supplies no constant for NSE equities.

**Recommended programme path: PATH B**, split into GANN-FAITHFUL TESTS and GANN-INSPIRED MODERN
REINTERPRETATIONS, with separate multiplicity families and a rule that only the faithful arm may be
cited as evidence about Gann (§11).

---

## 2. Evidence base and its limits

- Fidelity is judged against the claims **as transmitted** in catalogue §2. **No primary Gann text was
  read for this review or for the catalogue.** Every fidelity grade is therefore provisional, relative
  to the commonly transmitted corpus, and should be re-graded against a primary-source claim register
  before any faithful-arm pre-registration (§11, prerequisite F0).
- The practitioner corpus is internally inconsistent (360 vs 365.25-day year; calendar vs market
  days; fixed vs adaptive scales). Where it is, the review names which reading is more characteristic
  of Gann and which is shared with generic technical analysis. It does not pick the convenient one.

---

## 3. Framework

**Three properties, graded independently:**

| Property | Meaning |
|---|---|
| **Gann fidelity** | How much of the transmitted claim survives formalization unchanged: its reference quantity, unit, anchor and implication |
| **Statistical cleanliness** | Causal, deterministic, low researcher DoF, a well-defined null, and no mechanical coupling between event and outcome |
| **Gann-specific content** | A **discriminating prediction**: something the Gann claim predicts that the strongest generic explanation does *not*. Without one, a positive result cannot favour Gann over the generic account, however faithful the formalization |

**What each final class licenses a positive result to say:**

| Class | A positive result licenses |
|---|---|
| **A. Faithful Gann test** | "This supports the mechanized Gann rule X" — and only if the discriminating contrast also comes out Gann's way |
| **B. Gann-inspired modern reinterpretation** | "This supports a modern statistical construct inspired by Gann." Never evidence for Gann |
| **C. Generic market property** | A known or generic property; Gann terminology should be dropped |
| **D. Not worth testing** | Nothing |

**The asymmetry of inference matters:**
- A **negative** result on an A-class test refutes the *mechanized* rule, not Gann in general,
  because the mechanization carries researcher choices.
- A negative result on a B-class construct says **nothing** about Gann at all.

---

## 4. GO-2 — Time overbalance

**A. Correspondence to the Gann claim — HIGH.** The transmitted rule is close to verbatim: when a
reaction runs longer in time than the largest previous reaction in the same trend, the trend has
changed. The catalogue keeps:
- the reference quantity — the **maximum** prior reaction, not the average or the last;
- the scope — reactions **within the current trend**;
- the implication — a trend change;
- Gann's own pivot machinery — 1/2/3-day swing charts.

**B. Transformation needed for dimensional validity — essentially none on the time leg.** It compares
time with time, so it is dimensionally valid as Gann states it. Mechanization still added:
- a deterministic trend rule (ascending confirmed highs and lows);
- confirmation-delay stamping of pivots;
- a minimum number of prior reactions;
- a choice of sessions or calendar days (Gann used both).

The price-overbalance leg is price : price and also valid as stated; the choice of log over
arithmetic depth is the only departure.

**C. What was lost or changed:**
- Gann applied the rule across time frames (daily, weekly, monthly trends) with discretion about
  which trend is "the" trend. A single mechanized swing order fixes one frame and discards that
  discretion.
- "Trend has changed" is qualitative. It becomes either a signed forward return or a mechanized trend
  flip, and neither is Gann's own measure.

**D. Gann-specific content — MEDIUM.** Two elements are not generic:
1. **The maximum-prior-reaction reference.** The generic claim is "long corrections end trends";
   Gann's is "longer than the *longest* previous correction *in this trend*". This is testable as
   increment over elapsed duration alone.
2. **The time-over-price asymmetry.** The transmitted corpus holds that time is the more important
   factor. **A Gann-specific prediction is that time overbalance carries more information than price
   overbalance** of the same trend. The generic swing account predicts no such ordering; if anything,
   depth predicts trend breaks more directly, because a deep correction mechanically approaches the
   prior swing low.

Without these two contrasts GO-2 collapses to "corrections sometimes last longer than previous
corrections", which is **not** Gann-specific.

**E. What a positive result would justify.**
- **"Supports a Gann price-time principle"** is justified only if all three hold:
  1. the overbalance indicator beats a **surrogate-swing null** (§4.F);
  2. it adds information over elapsed duration, depth and trend age;
  3. time overbalance is at least as informative as price overbalance.
- If (1)–(2) hold but (3) fails, the finding is **"a maximum-reference duration effect", not a Gann
  price-time principle**.
- If (1) fails, it is swing mechanics.

**F. Strongest simpler non-Gann explanation — swing-rule mechanics.** Apply a fixed *k*-day swing rule
to a pure random walk with realistic volatility. A correction that has lasted a long time has
typically drifted further and is closer to breaching the prior swing low, so trend flips follow long
corrections **mechanically**. Also, *D*\* is the maximum of the prior reactions, so it grows with
trend age: the event is rarer in old trends, which conditions implicitly on trend age.

The null for GO-2 is therefore **not "no effect"**. It is the effect a surrogate series (volatility-
and trend-age-matched random walk, or block-bootstrapped returns) produces under the same swing rule.
The catalogue's control list did not contain this, and it must be added (§9).

**Classification: A. FAITHFUL GANN TEST** — conditional on the surrogate-swing null and the
time-vs-price contrast being declared as the pass conditions.

---

## 5. GT-1 — Pivot anniversary

**A. Correspondence — MEDIUM overall; HIGH for the 360-day form.** Gann is widely credited with
treating anniversaries of important tops and bottoms as timing points. Two readings are transmitted:
- the **calendar anniversary** (≈ 365.25 days), which is shared with ordinary seasonality thinking;
- the **360-day "circle"** with its divisions, which is distinctively Gann.

Mechanizing "important top/bottom" as a trailing-window extremum confirmed with delay is a reasonable
causal stand-in for "important", but it is the researcher's definition.

**B. Transformation — none on the time axis** (time vs a pinned calendar unit). The only
transformations are causal: the anchor becomes a *confirmed* major pivot, and "a turn" is replaced by
a mechanized turn-incidence or activity outcome.

**C. What was lost:**
- Gann's selection of *which* tops matter — often the few most important of a year or of history.
  Mechanized "major" pivots will include many that Gann would not have selected.
- The use of anniversaries of *historical* market dates beyond the instrument's own pivots.
- Discretionary tolerance: a "few days either side" becomes a fixed window *w*.

**D. Gann-specific content — LOW at 365.25 days; MEDIUM only through two discriminating contrasts:**
1. **360 vs 365.25 days.** A generic annual calendar effect predicts recurrence at the **calendar
   anniversary**. The Gann circle predicts **360 days**, about 5 calendar days (≈ 3–4 sessions)
   earlier. Separating them needs windows of *w* ≤ 1–2 sessions, so the windows do not overlap. The
   catalogue treated *Y* ∈ {360, 365.25} as a nuisance DoF; **it should instead be the principal
   Gann-vs-calendar contrast**.
2. **Pivot-specificity.** The anniversary must be of a *pivot*, not of any date of the same stock in
   the same calendar month (random-anchor control).

**E. What a positive result would justify** — the attribution ladder (§5.5). **"Supports a Gann
price-time principle" requires the top rung.** Anything lower is either an annual calendar effect or
a pivot-anchored annual recurrence that is *compatible with* Gann but not specific to it.

**F. Strongest simpler non-Gann explanation — pivots are event days, and events recur annually.**
Major turning points in individual stocks cluster around quarterly/annual results, AGM and dividend
dates, index reviews, and the Union Budget (1 February since 2017). Those recur at ≈ 365 days. The
anniversary of a pivot is therefore often the anniversary of a **results date**.

**This defeats the catalogue's random-anchor control.** A random date in the same calendar month is
not a results date, so a pivot anniversary can beat random anchors purely because pivots are
event-selected days. The repo has **no earnings calendar**, so the control must be approximated by
**activity-matched anchors**: non-pivot dates of the same stock, chosen for comparable abnormal
activity (|return|/σ or volume spikes) in the same calendar month.

A further non-Gann contributor: market-wide pivots (e.g. March 2020) make anniversaries synchronous
across stocks. Those are date-clustered, macro-calendar events.

### 5.5 Attribution ladder (to be pre-declared; operator's ruling recorded)

| A positive anniversary result that survives… | …but not… | Must be classified as |
|---|---|---|
| Ordinary calendar controls (month, expiry week, σ, momentum) | Random-anchor anniversaries | **"Annual calendar effect"** — not Gann (operator ruling) |
| Random-anchor anniversaries | Activity-matched anchors | **"Event-day annual recurrence"** — not Gann |
| Activity-matched anchors, at 365.25 days | The 360-day contrast (360 no stronger than 365.25) | **"Pivot-anchored annual recurrence, compatible with but not specific to Gann"** |
| Activity-matched anchors **and** 360 days ≥ 365.25 days with separable windows | — | **"Supports the mechanized Gann anniversary / circle rule"** |

**Classification: A. FAITHFUL GANN TEST, with the expectation recorded in advance that the most
likely positive outcome is class C (annual / event calendar).** It is worth testing because its
faithful form carries a sharp discriminating contrast (360 vs 365.25) that costs little to add.

---

## 6. GA-3 / GS-5 — Self-scaled 1×1: critical examination

### 6.1 What Gann's 1×1 actually is (as transmitted)

The 1×1 is **one unit of price per one unit of time on a fixed scale chosen for the instrument**. The
same scale is held across swings, so angles drawn from different pivots are **parallel and
comparable**, and the market "moves from angle to angle" within one fixed geometry.

The privilege of "1" comes from that **exogenous, fixed unit**. Gann's squares ("square of the
range") likewise convert a price range into a time count through the same fixed unit.

### 6.2 The catalogue's claim

> "The only dimensionally valid 'square' with a privileged 1 is a rate equality" — current swing rate
> = prior swing rate.

**The statement is mathematically correct and scientifically misleading:**

1. **"Dimensionally valid" was misapplied.** *P* = *u*·*t* with a declared *u* in ₹/day is
   dimensionally valid. What the theory lacks for NSE equities is a **value** for *u*, not dimensional
   coherence. The catalogue's rejection of GA-1 and GS-2 as "dimensionally invalid" should read "no
   theory-given constant for this market; untestable unless a Gann-attested scale rule is pinned from
   primary sources".
2. **"Only" holds under imposed requirements.** Rate equality is the unique candidate only if one
   demands (a) scale-free comparability across 100 stocks, (b) no exogenous constant, and (c) a
   privileged value. **(a) and (b) are programme requirements, not Gann's.** Gann worked one
   instrument at a time with an exogenous scale.
3. **The "privileged 1" is trivial.** Every ratio of like quantities has a privileged value of 1:
   equality. Its privilege is a property of taking a ratio, not evidence that the ratio is Gann's.
4. **The reference changed.** Gann's 1×1 compares price progress with a **fixed structural unit**.
   GA-3 compares it with **the stock's own immediately preceding swing**, so the ray's slope changes
   every leg, angles from successive pivots are no longer parallel, and the "angle to angle"
   geometry disappears.

**Mechanically, the GA-3 break is**

  (*x_t* − *x_O*)/(*t* − *O*) < ρ = *A*_prev / *D*_prev,

that is, **the current leg's average log return per session has fallen below the previous leg's
average log return per session.** That is a leg-over-leg speed ratio: a momentum-deceleration
statistic. The only Gann residue is the ray drawn from a pivot and the reading of a break as
weakness, and both are common to generic trendline analysis.

### 6.3 Verdict on the three options

| Option | Verdict |
|---|---|
| 1. Faithful translation of Gann's 1×1 | **No.** It removes the fixed unit, which is the defining feature |
| 2. Defensible modern reinterpretation | **Only in a form that preserves a stable, per-stock structural speed** — the mean rate over several prior swings, or a scale frozen causally and held fixed across later pivots. That keeps the idea of a *characteristic* unit per instrument, which is the nearest analogue to Gann's fixed scale, while making it data-derived. **Label: Gann-inspired modern reinterpretation** |
| 3. Generic trend-speed / momentum construct in Gann terminology | **Yes, for the immediately-preceding-swing form (the catalogue's primary cell) and for the volatility-normalized form.** These are momentum-deceleration and trend-intensity statistics |

### 6.4 Are the ρ variants implementation choices or different hypotheses?

**They are different hypotheses.** Each asserts a different reference against which trend "speed" is
judged, and each has a different generic twin.

| Variant | Hypothesis it states | Generic twin | Fidelity to Gann's fixed unit |
|---|---|---|---|
| Immediately preceding swing | "A leg is weak when slower than the last leg" — leg-to-leg memory | Momentum deceleration / short-horizon momentum ratio | LOW |
| Mean of previous *m* swings (or a causally frozen per-stock scale) | "A leg is weak when slower than the stock's characteristic speed" | Trend strength vs a trailing norm | **MEDIUM** — the closest to a fixed instrument unit |
| Volatility-normalized rate (*n*·σ per session) | "A leg is weak when its drift falls below a multiple of noise" | Trend-intensity / t-statistic threshold (GA-2 / GS-3) | LOW — the reference is not a swing or a unit at all |
| Log-price rate (vs arithmetic) | Constant *percentage* speed rather than constant *rupee* speed | — | Arithmetic is Gann's; **log is a departure**. For small legs they nearly coincide; for large legs they diverge, so they are distinct hypotheses where it matters |

Each variant is therefore a separate hypothesis in the multiplicity register, not a robustness cell
of one hypothesis. Only the mean-of-swings / frozen-scale arithmetic form can claim even modern-
reinterpretation status; the others are generic.

### 6.5 A-F summary for GA-3 / GS-5

| | |
|---|---|
| **A. Correspondence** | **LOW.** It keeps a ray from a pivot and "break = weakness"; it loses the fixed unit and the parallel-angle geometry |
| **B. Transformation** | The exogenous unit is replaced by an endogenous rate (prior-swing amplitude / duration) in log price |
| **C. Lost** | The fixed scale, parallel angles from different pivots, the angle hierarchy (1×2, 2×1… as structural levels), arithmetic geometry, and GS-2's price-range-to-time conversion (the actual "square of the range") |
| **D. Gann-specific** | **LOW.** No discriminating prediction against momentum deceleration was identified |
| **E. Positive result justifies** | **Only "supports a modern statistical construct inspired by Gann"** — never "supports a Gann price-time principle". GS-5 (the "ratio square") carries the same limit: Gann's square is range-to-time through a fixed unit, not a rate equality |
| **F. Strongest generic explanation** | Momentum deceleration / leg-speed mean reversion. After a fast prior leg (large ρ), a break is near-certain early in the new leg, because early-leg noise dominates a steep ray. The event rate is mechanically a function of the prior leg's speed |

**Classification: B. GANN-INSPIRED MODERN REINTERPRETATION** (mean-of-swings / frozen per-stock
scale) · **C. GENERIC MARKET PROPERTY** (prior-swing and σ-rate forms). **It should not appear in
any list headed "most faithful to Gann"** (catalogue §17.0 list A — see §9).

### 6.6 What a faithful angle test would require

A faithful 1×1 test needs a **fixed per-instrument scale** that is:
- held constant across pivots;
- arithmetic;
- rescaled only by corporate-action ratios, which preserves its economic meaning;
- **chosen by a rule attested in Gann's own writings**, not by the researcher.

If primary sources supply such a rule for equities (e.g. price-range-dependent unit conventions, as
some practitioner sources report — **unverified here**), the faithful angle test exists and belongs
in the faithful arm. If they do not, **faithful Gann angles are NOT TESTABLE**, and that is a finding
to record, not a gap to fill with GA-3.

---

## 7. GT-2 — Time symmetry

**A. Correspondence — LOW.** Gann is credited with "time balancing" and symmetric moves, but
equal-duration symmetry is also part of generic cycle, harmonic and Elliott-style folklore. The
transmitted corpus gives no Gann-specific reference (unlike GO-2's *largest* prior reaction or
GT-1's 360-day circle). "A move lasts as long as the prior move" is not distinctively his.

**B. Transformation — none** (time vs time). Mechanization adds the swing rule, the multiplier set and
the tolerance.

**C. Lost** — little, because little was specified. That is the problem: the claim is thin enough
that its formalization is almost entirely researcher-defined.

**D. Gann-specific content — LOW.** No discriminating prediction against generic duration persistence
was found.
- The {1/2, 1, 2} multipliers are shared with harmonic-ratio folklore.
- Unlike GO-2, there is no asymmetry claim (time vs price) and no maximum-reference rule.

**E. What a positive result would justify** — **neither framing.** A positive result would support
"consecutive swing durations are dependent", which is a property of the return process, not a Gann
principle.

**F. Strongest generic explanation — volatility clustering plus swing-rule mechanics.** Swing duration
under a fixed *k*-day rule is roughly inversely related to volatility. Volatility is persistent, so
consecutive swing durations are positively dependent in almost any financial series. The termination
hazard at τ ≈ *D*_prev is then elevated with no geometric content. Controlling for σ regime would
remove most of it, and whatever survived would still have no Gann-specific signature.

**Classification: C. GENERIC MARKET PROPERTY. Recommend removal from the Gann battery.** It remains
useful as a **control covariate** for GO-2: duration persistence must be absorbed before a
maximum-reference effect can be claimed.

---

## 8. Final classification

| Construct | Gann fidelity | Statistical cleanliness | Gann-specific content | Generic-market explanation | Class | Recommended status |
|---|---|---|---|---|---|---|
| GO-2 Time overbalance | HIGH | MEDIUM | MEDIUM | Swing-rule mechanics; trend exhaustion | **A** | Faithful arm. Pass conditions: beat a surrogate-swing null; increment over duration, depth and trend age; time ≥ price overbalance |
| GT-1 Pivot anniversary | MEDIUM (360-day form HIGH) | MEDIUM | LOW (365.25) / MEDIUM (with 360 contrast + activity-matched anchors) | Annual results / event calendar; event-selected pivots | **A** (the likely positive outcome is **C**) | Faithful arm, with the §5.5 attribution ladder pre-declared and *Y* as the principal contrast |
| GA-3 / GS-5 — mean-of-swings or frozen per-stock arithmetic scale | LOW-MEDIUM | MEDIUM | LOW | Trend strength vs trailing norm | **B** | Modern-reinterpretation arm only; never cited as Gann evidence |
| GA-3 / GS-5 — prior-swing (catalogue primary cell), σ-rate, log forms | LOW | MEDIUM | LOW | Momentum deceleration; trend intensity | **C** | Drop from the Gann programme (or keep in the modern arm, explicitly labelled generic) |
| GT-2 Time symmetry | LOW | MEDIUM | LOW | Volatility clustering; duration persistence | **C** | Remove from the battery; retain as a GO-2 control covariate |

No shortlisted construct is class **D**. The faithful angle test (§6.6) is **conditionally NOT
TESTABLE** pending primary sources.

---

## 9. Corrections the catalogue will need (listed, not applied)

| # | Catalogue location | Correction |
|---|---|---|
| K1 | §1 item 3, §8 conclusion, GS-5 status row | The rate equality is a **modern reinterpretation under programme-imposed requirements**, not "the only valid square". State the imposed requirements |
| K2 | §17.0 list A ("most faithful") | Remove GA-3/GS-5 and GT-2. List A becomes GO-2 and the GT-1 360-day form |
| K3 | GA-1, GS-2 status and §18 | "Dimensionally invalid" → "no theory-given constant for this market". Reclassify to **NOT TESTABLE unless a Gann-attested scale rule is pinned from primary sources** (faithful form in §6.6) |
| K4 | GA-3 fields 16–18, §15.1 | The ρ variants (prior swing / mean of swings / σ-rate / log vs arithmetic) are **distinct hypotheses**, not DoF within one |
| K5 | GO-2 controls, §17.1 Candidate 1 | Add the **surrogate-swing null** (random-walk / block-bootstrap series under the same swing rule), the **trend-age / number-of-prior-reactions** control, and the **time-vs-price-overbalance contrast** as a Gann-specific pass condition |
| K6 | GT-1 fields, §17.1 Candidate 2, §15 | Promote *Y* ∈ {360, 365.25} from nuisance DoF to **principal contrast** (non-overlapping windows); add **activity-matched anchors**; embed the §5.5 attribution ladder, including the operator's "annual calendar effect" classification |
| K7 | GT-2 status, §17.1 alternate | Reclassify to generic duration persistence; remove from the Gann shortlist; retain as a GO-2 control |
| K8 | §2 | State that claims are as-transmitted, not verified against primary texts; fidelity grades are provisional |

---

## 10. What results could and could not say (pre-committed reading)

| Outcome | Permissible statement |
|---|---|
| GO-2 passes all three conditions | "The mechanized Gann time-overbalance rule carries information beyond swing mechanics, duration and depth, and time outranks price as Gann claimed." Limited to this mechanization, universe and period; historical evidence is non-confirmatory (GR-1.3; operator exposure ruling 2026-09-14) |
| GO-2 beats surrogates but price ≥ time | "A maximum-reference duration effect exists; Gann's time-primacy claim is not supported" |
| GO-2 fails the surrogate null | "Consistent with swing-rule mechanics; no Gann-specific content detected" |
| GT-1 at any rung below the top of §5.5 | The rung's label; **not** Gann |
| GT-1 top rung | "Supports the mechanized Gann anniversary / circle rule" |
| GA-3 / GS-5 positive, any form | "Supports a modern statistical construct inspired by Gann" (mean form) or the generic label (other forms). **Never evidence for Gann** |
| GA-3 / GS-5 negative | **Says nothing about Gann** |
| GT-2 any result | Duration-dependence finding; not reported under Gann |
| Faithful arm negative | "The mechanized Gann rules tested show no information on PIT N100 EOD." It does not refute unmechanized or discretionary Gann practice — and discretionary practice is not a scientific claim |

---

## 11. Final recommendation — PATH B

**Split the programme into GANN-FAITHFUL TESTS and GANN-INSPIRED MODERN REINTERPRETATIONS.**

### Arm 1 — Gann-faithful tests

The only arm permitted to produce statements about Gann.

| Item | Content |
|---|---|
| Members | **GO-2** (with K5); **GT-1** (with K6: 360-vs-365.25 contrast, activity-matched anchors, attribution ladder); **faithful fixed-scale 1×1 (§6.6)** only if F0 yields a Gann-attested scale rule, otherwise recorded as NOT TESTABLE |
| Prerequisite **F0** | A **primary-source claim register**: each rule paraphrased with a citation to the work and location (no long reproduction), fixing the reference quantity, unit, anchor and implication *before* formalization. Fidelity grades in this review are re-graded against it |
| Multiplicity | Its own family, pinned before any read |
| Placement | **Family placement remains the operator's ruling.** One observation favours stock-level application for this arm specifically: Gann applied these rules **to individual instruments**, so per-stock application of a per-instrument rule is not an index rule in stock clothing. Pooling across 100 stocks remains a researcher inference choice and must pass the catalogue §11 veneer test |

### Arm 2 — Gann-inspired modern reinterpretations

| Item | Content |
|---|---|
| Members | GA-3 / GS-5 in the mean-of-swings / frozen-scale form, as one explicitly labelled hypothesis. Any other ρ variant is a separate hypothesis and, per §6.4, generic |
| Reporting rule | Results **may never be cited as evidence for or against Gann** |
| Multiplicity | A separate family, not pooled with Arm 1 |
| Governance priority | Lower than Arm 1. It competes for budget with every other modern price-time construct and receives no priority from the Gann label |

### Removed

GT-2 leaves the Gann programme (generic). It survives only as a GO-2 control covariate.

### Why not PATH A or PATH C

| Path | Why not |
|---|---|
| **A — faithful only** | Nearly right, and Arm 1 *is* Path A. Choosing A alone would leave the catalogue's reinterpretations unlabelled rather than excluded, which is exactly the blur this review found. B makes the separation, and the rule that Arm 2 is not Gann evidence, binding |
| **C — stop** | Not warranted. GO-2 and GT-1 have faithful formalizations whose discriminating contrasts (surrogate swing null + time-vs-price; 360 vs 365.25 + activity-matched anchors) are computable on PIT N100 EOD. Daily resolution matches Gann's daily/weekly swing charts, and 15.5 years supports annual anniversaries |
| **What C gets right** | Faithful Gann **angles and squares** may genuinely be untestable on this data, if F0 finds no attested scale rule. **That would be an honest partial Path-C result for that part of the corpus**, to be recorded rather than papered over with GA-3 |

**Not chosen on expected profitability:** no outcome informed any grade, and the recommendation
keeps the constructs most likely to produce a clean *null* about Gann.

---

## 12. Governance statements

- **No outcome values were read.** No data store was queried for this review.
- **No RFA, test or backtest was run. No TRAIN/HOLDOUT was created.**
- **No hypothesis was frozen or selected.** Classifications and the path recommendation await the
  operator's ruling.
- **The catalogue was not modified.** Corrections K1–K8 are listed for a later, separately authorized
  edit.
- **No family definition was modified** (Families B, C, D, F, G; PTMS-G-PTSQ untouched).
