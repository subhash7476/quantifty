# PTMS — Gann Faithful Construct Definitions (GF-1 to GF-7)

**Date:** 2026-09-14 · **Branch:** `research/ptms-price-time-market-structure`

**Status:** CANDIDATE DEFINITIONS. **Not a pre-registration. Nothing selected or frozen.** No
parameter was chosen, no market data or outcome read, and no RFA, TRAIN/HOLDOUT or backtest run. See
§6.

**Addendum (§12, after register delta Δ2 — *45 Years in Wall Street*):** proposes GF-8, GF-9 and
GF-10 and adds 1949 primary bases to GF-4T to GF-7. §§0–11 are unedited. GF-10 contradicts operator
ruling 7 and is **pending operator acceptance**. Design choices are in
`PTMS_GANN_PREREG_DESIGN_DECISIONS_2026-09-14.md`.

**Operator rulings (2026-09-15):** GF-10 **accepted as GANN-FAITHFUL (R-5); ruling 7 superseded.**
Stage-1 primaries: GF-1, GF-4T/R8, GF-10 (m = 3). GF-8 and GF-9 excluded from Stage 1, retained as
Arm-1 claims (R-6). GF-7 excluded from Stage 1 (R-7). GF-5 and GF-6 deferred, not retired (R-8). §12.1's
K3 "declared departure" is admitted as an explicitly labelled approximation (R-1). Record:
`PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md`. Nothing frozen.

**Inputs:**
- `PTMS_GANN_PRIMARY_SOURCE_CLAIM_REGISTER_2026-09-14.md` — F0 §§0–25 and delta Δ1 §26. Claim IDs
  cited as `TIM-03`, `Δ-07` etc. are from there.
- `PTMS_GANN_CONSTRUCT_CATALOGUE_2026-09-14.md` §21 (status after Δ1); §§4, 5, 12–15 for design
  machinery.
- `PTMS_N100_EOD_FEASIBILITY_AUDIT_2026-09-14.md` (substrate facts only).
- Operator handoff, 2026-09-14.

**Source keys:**
- **[MMPTC]** — *Master Mathematical Price Time and Trend Calculator*, 1953.
- **[WSSS]** — *Wall Street Stock Selector*, 1930.
- **[NSTD]** — *New Stock Trend Detector*, 1936.
- **[TST]** — *Truth of the Stock Tape*, 1923.

Quotations are kept short; everything else is paraphrase with locators.

**Purpose:** turn the primary-sourced Gann constructs into mechanizable candidate definitions that
separate **what Gann specified** from **what a modern implementation must assume**. The research
question is:

> Does Gann's documented price-time framework contain a reproducible statistical edge?

The faithful version is defined first. Modern reinterpretations are out of scope here (catalogue §21,
Arm 2).

---

## 0. Summary

| ID | Construct | Faithfully mechanizable? | Needs translation ruling? | Unit of construction | CA exposure |
|---|---|---|---|---|---|
| **GF-1** | Master Square time points (fractions of 144 from highs/lows) | **Yes, with declared assumptions** | No (time counts only) | Per stock; index-compatible | Anchor identification only |
| **GF-2** | 45° / geometric angles on the chart-space grid | **Framework yes; trading rules only partly** — Gann defers them to a course not supplied | **Yes** | Per stock; index scale unstated | **Level; severe** |
| **GF-3** | Square of high / low / range in time | **Yes, with declared assumptions** | **Yes** | Per stock; index-compatible (Gann says so) | **Level; severe** |
| **GF-4T** | 360° circle divisions as time counts | **Yes, with declared assumptions** | No | Per stock; index-compatible | Anchor identification only |
| **GF-4P** | 360° circle divisions as price levels | Yes, with declared assumptions | **Yes** | Per stock | **Level; severe** |
| **GF-5** | Pivot anniversary (month / year resolution) | Yes, with declared assumptions | No | Per stock; index-compatible | Anchor identification only |
| **GF-6** | Absolute reaction-duration rules | Yes, with declared assumptions | No | Per stock; index-compatible | Anchor identification only |
| **GF-7** | Third-month / 3rd–4th move / 6–7 week culmination | Yes, with declared assumptions (segmentation) | No | Per stock; index-compatible | Anchor identification only |

**Excluded here:**
- GA-3 / GS-5, ATR- or σ-scaled angles, relative time overbalance, GT-2 — all Arm 2.
- The Square-of-Nine spiral — not in primary sources.
- The 360-day annual cycle — unresolved.
- TIM-10 — held pending the translation ruling.

---

## 1. Cross-cutting definitions (apply to every GF construct)

These are **assumption slots**. Gann either leaves them open or offers several options. Each must be
pinned by the operator **before any read, without reference to outcomes**, and disclosed as a
departure where it departs.

### 1.1 Unit convention (price ↔ chart space)

- **Gann:** stocks, **1 point per space on the daily chart**; grains 1¢ per space on
  daily/weekly/monthly; other instruments by Special Instructions, not supplied ([MMPTC] pp. 1, 5).
- **Candidate U-LIT (literal quotation unit):** one space = ₹1 on the daily chart. This is the
  faithful default *if* the operator admits the translation (register §26.5). Price numbers are
  as-traded rupees.
- **Not Gann, so Arm 2 if used:** percentage scaling, price-band rescaling, decimal shifting, ₹0.05
  tick units, σ/ATR scaling.
- **Weekly / monthly stock charts:** scale unstated. Options:
  - (a) daily construction only;
  - (b) the grain precedent (same scale on all timeframes), declared as an assumption.
- **Consequence of fidelity, not a defect:** under U-LIT a 45° line is nearly flat for a ₹3,000
  stock and steep for a ₹100 stock, and a price number of 3,000 maps to 3,000 days. Price level
  therefore changes which events can exist at all.
  - Report this as a **diagnostic** (stratify by price level).
  - Do not normalize it away, or the construct stops being Gann's.

### 1.2 Time unit

- **Gann:** days (calendar **or** market), weeks, months — each admissible ([MMPTC] pp. 1, 2, 6;
  register Δ-10). Leap days are counted.
- **Slot T** ∈ {calendar days, market (NSE session) days, calendar weeks, calendar months}.
  - Each value is a separate cell, **or** one T is pre-selected per construct on a written textual
    rationale.
  - Example rationale: the WSSS/NSTD duration rules are stated in weeks and months.
- **NSE sessions:** 5-day weeks today, matching Gann's 1953 note that exchanges were open 5 days
  ([MMPTC] p. 5). No 6-day mapping is needed for the 1953 constructs; the WSSS-era rules still carry
  the register ANN-09 caveat.

### 1.3 Anchors

- **Gann's options:**
  - 0;
  - extreme low;
  - extreme high;
  - halfway point of the range or of the highest price;
  - "important" and "minor" highs and lows;
  - second or third higher bottom;
  - January, for yearly periods

  ([MMPTC] pp. 4, 6–7). **Significance is undefined** (register SWG-05).
- **Slot A** (anchor class) plus **slot K** (pivot detector: swing order, confirmation rule) for
  important/minor highs and lows.
- **"Extreme ever sold" is left-censored.** The PIT N100 panel starts 2011-03-25 (EOD feasibility
  audit), and many N100 names listed earlier. **Candidate:** "running extreme over the stock's
  available history in the store, as of *t*", with listing date and data start disclosed per stock.
  This is an assumption, not Gann.
- **Anchor 0** (chart bottom at zero price) is a price-axis origin, not a date. It only applies to
  price-level constructs (GF-2, GF-4P).

### 1.4 Price basis and corporate actions

- **Level constructs** (GF-2, GF-3, GF-4P, and GF-1 where a price point is used) need **as-traded**
  prices.
  - The adjusted view is back-adjusted, so its levels carry look-ahead (EOD audit).
  - The equity 1m store is also back-adjusted (CLAUDE.md) and is **not** admissible for level
    constructs.
- **Anchor identification** for time-only constructs (GF-1, GF-4T, GF-5, GF-6, GF-7) may use an
  as-of-*t* adjusted series, so extrema are not distorted by bonus/split ratios. Ratio adjustment
  preserves where relative extrema fall *within* a consistently adjusted window.
- **Gann's split practice is mixed** (register CA-01 to CA-03), and **[MMPTC] is silent**.
  Candidate slot **CA-POL**:
  - (a) reset level anchors at any bonus/split ex-date;
  - (b) express pre-event levels in post-event units from the ex-date forward (causal);
  - (c) exclude constructs whose anchor-to-event window spans a ratio corporate action.
- **Non-ratio events** (spin-offs, rights, special dividends — unadjusted in the store per the EOD
  audit): exclude windows that span them, under every policy.

### 1.5 Causality / point-in-time

- An anchor exists only from its **confirmation date** (running extreme, or pivot confirmed by rule
  K). Time counts run from the **anchor date**; an event at *t* is usable only if confirmation ≤ *t*.
- "Extreme high/low" means **to date**. If an extreme is exceeded before its square or division date,
  the pending events from it are **invalidated at that moment**. The alternative — keeping the old
  anchor — must be declared; neither is stated by Gann.
- No centred windows. The repository's causal swing convention applies (`result.iloc[i + period]`).
- Outcome windows start strictly after *t*.

### 1.6 Outcome — "change in trend"

Gann's watch statements say to watch for a change in trend. **[MMPTC] does not define it**, so it is
slot **O**:

- **O1 — Gann-sourced:** the close relative to the halfway point of the period range flips side
  ([MMPTC] p. 3, register Δ-14), on the bar of the construct's time unit.
- **O2 — Gann-sourced:** three-consecutive-closes rule ([WSSS] pp. 66–73, register TOB-10).
- **O3:** a confirmed opposite pivot (rule K) within horizon *h*.
- **O4 — non-directional:** |ln(*P*_{t+h}/*P_t*)| / σ_ℓ(*t*).

**For fidelity, prefer O1 or O2 as primary**, with others off the pass path. Horizon *h* is a slot.

### 1.7 Point density and coverage

Gann's point sets are dense: fractions of 144, squares 1–19, master numbers, and 64ths of the circle
(every 5⅝ units). With any tolerance, **most of the time axis is "near a Gann point"**. Every GF test
must therefore:

1. restrict itself to the **named point set** of that construct, as written in §§2–8, not the union;
2. compute its **coverage fraction** *c* — the share of eligible sessions inside any window — per
   stock and in aggregate;
3. test hit incidence against a **coverage-matched null**, placebo points with the same *c*, never
   against a flat base rate.

### 1.8 Individual-stock construction and aggregation

- **Construction is per stock:** own anchors, own price numbers, no fitted common parameter. This
  follows Gann's individual-study principle (register XS-01 to XS-03; [NSTD] p. 17).
- **Pooling across N100** (event study GX-1, or date-clustered model) is a **statistical device for
  power**, not a Gann claim. Label it so in any report.
- **Per-stock heterogeneity** (catalogue GX-4) is a required diagnostic, not an optional one.
- **Index application:** Gann applies GF-1, GF-3, GF-4 and the duration rules to "stock averages"
  ([MMPTC] p. 4; [NSTD] passim), so an index version is faithful in kind. The **index price scale is
  not stated** (1953 averages were in the hundreds; Nifty 50 is in the tens of thousands).
  - Index versions of level constructs (GF-2, GF-3, GF-4P) share the translation problem, in more
    acute form.
  - Index placement is Family C (single-index `per_trade_pnl`) or D, never a veneer over N100
    (catalogue §11.1).

### 1.9 Evidence label

- Historical N100 EOD may be used, and results **may not be presented as pristine confirmation**
  (operator exposure ruling; catalogue §19.1(b)).
- Any read is **development / non-confirmatory** unless a pre-registration defines otherwise.

---

## 2. GF-1 — Master Square time points

| # | Field | Definition |
|---|---|---|
| 1 | Primary basis | [MMPTC] p. 1 (square of 144 works for time and price); p. 3 (strongest points 1/4, 1/3, 3/8, 1/2, 5/8, 2/3, 3/4, 7/8, 1); p. 4 (most changes in trend at time periods of 1/2, the end, 1/3, 2/3, 1/4, 3/4 of 144); p. 6 (new square every 144 periods); p. 7 (keep time periods from important highs and lows). Register Δ-01, Δ-05, Δ-06 |
| 2 | Source claim | Most changes in trend occur when time periods measured from highs and lows reach one-half of 144, the end of a square, or its 1/3, 2/3, 1/4 and 3/4 points |
| 3 | Specified by Gann | Point set **P4** = {36, 48, 72, 96, 108, 144} and its repetition every 144 (p. 4). A wider "strongest points" set **P8** adds {54, 90, 126} (p. 3). Units: days, weeks or months. Counted from highs and lows |
| 4 | Unspecified | Which highs/lows (significance); calendar vs market days; tolerance; P4 vs P8; the meaning of "change in trend"; how far to repeat squares |
| 5 | Implementation assumptions | A (anchor class) + K (detector); T; tolerance *w* (in units of T); P4 vs P8; number of squares *S*; outcome O; *h* |
| 6 | Faithfully mechanizable? | **Yes, with the §1 assumptions.** Time-only, so no price unit and no translation ruling needed |
| 7 | Stock / index | Per stock (primary). Index-compatible ([MMPTC] p. 4 applies the method to averages) |
| 8 | Corporate actions | Time axis immune. Anchor identification on an as-of-*t* adjusted series; exclude windows spanning non-ratio events |
| 9 | Dimensional / scale | Pure time counts. No scale. **The time unit T is the only "scale" and must be pinned** |
| 10 | Causal / PIT | Event at *t* = anchor date + *n* units, usable if the anchor is confirmed by *t*. Running extremes per §1.5 |
| 11 | Null / controls | (i) **Placebo fractions** of 144 with matched coverage, avoiding Gann fractions (e.g. 0.29, 0.41, 0.59, 0.71, 0.83); (ii) **random anchors**: same stock, same calendar month, non-pivot dates; (iii) **time-only hazard** of trend change versus elapsed time since the anchor; (iv) calendar controls (month, F&O expiry week, results season); (v) coverage-matched null (§1.7); (vi) date-clustered errors |
| 12 | Multiplicity | Illustrative: A {extreme high, extreme low, important high, important low} = 4 × T = 4 × {P4, P8} = 2 → **32 cells** before *w*, *S*, O and *h*. Pin one primary cell; the rest are robustness, off the pass path |

---

## 3. GF-2 — 45° and geometric angles on the chart-space grid

| # | Field | Definition |
|---|---|---|
| 1 | Primary basis | [MMPTC] p. 1 (nine spaces = 9 days / 9 points on stocks, daily chart); p. 3 (pitch or trend is the geometric angle; price 72 at time 72 = balanced at 45°); p. 5 (green 2×1 = two spaces per period; 1×2 = one space per two periods; red angles on squares of 9; inner square from 72; break below 45° on the inner square shows weakness in proportion to time from the high or low); p. 6 ("Follow all rules on angles as given in the Master Forecasting course"; place the chart at 0, the low, or the square of high/low/range). Register Δ-02 to Δ-04, Δ-08 |
| 2 | Source claim | The trend's pitch is a geometric angle on a price-time grid of equal spaces. On stocks' daily charts one space is one point per day. Price and time balance at 45°. A break below the 45° angle on the inner square signals weakness |
| 3 | Specified by Gann | Slopes in spaces per period: 1 (45°), 2 (2×1), ½ (1×2). Stock unit on the daily chart: 1 point per space. Candidate origins: 0, low, high, square of high/low/range, halfway point (72 = centre). Inner square from 72. **One rule:** a break below 45° on the inner square = weakness, proportional to elapsed time |
| 4 | Unspecified | **The angle trading rules** (deferred to a course not supplied); rupee translation; weekly/monthly stock scales; which origin governs; what counts as a "break" (close, low, duration); the outcome of a hold vs a break; the meaning of "in proportion to the time" |
| 5 | Implementation assumptions | U-LIT (§1.1); origin class A; break rule (e.g. first close below the line); T = market days (the daily chart counts sessions, one space per bar; declared); angle set {1×1, 2×1, 1×2}; outcome O; *h* |
| 6 | Faithfully mechanizable? | **Verified construct; only partly mechanizable faithfully.** The stated inner-square 45° break rule is mechanizable under U-LIT + origin + break assumptions. **General angle support/resistance or hold/break rules are NOT faithfully mechanizable** until the Master Forecasting course is read. Any rule filled in beyond p. 5 is Arm 2 |
| 7 | Stock / index | Per stock, daily chart. Index: the angle unit for averages is unstated, so it is not faithful under U-LIT |
| 8 | Corporate actions | **Severe.** A line in ₹ per day from an as-traded origin is broken by any split or bonus. CA-POL (a) or (c) required. Policy (b) — rescaling the line by the ratio — is an assumption Gann never gave |
| 9 | Dimensional / scale | ₹ ≡ days by Gann's convention. Catalogue §4's objection is **not removed**; it becomes the core control (row 11) |
| 10 | Causal / PIT | Origin = confirmed anchor. The line is defined only from the anchor date. Break evaluated at close *t* |
| 11 | Null / controls | (i) **Scale placebos**: lines at ₹0.8 and ₹1.25 per day. They must not be 2 or ½, which are Gann's own angles. **If placebo slopes predict as well, there is no Gann-specific content**; (ii) **price-only**: a horizontal level at the same distance below price; (iii) **time-only**: same elapsed time without a line; (iv) random origins; (v) momentum since the anchor, and σ; (vi) price-level strata (§1.1 diagnostic) |
| 12 | Multiplicity | Illustrative: origin {low, high, halfway} = 3 × angle {1×1, 2×1, 1×2} = 3 × break rule 1 → **9 cells** for the inner-square rule, before O and *h*. Unbounded if non-Gann rules are added — they belong in Arm 2 |

---

## 4. GF-3 — Square of high, low and range in time

| # | Field | Definition |
|---|---|---|
| 1 | Primary basis | [MMPTC] p. 4 (watch the square in time of the highest price, minor highs and lows, lowest price, second or third higher bottom, and range; wheat example; the same method for individual stocks); pp. 6–7 (place the chart on the square of the high, low or range; never overlook the extreme high and low, ½ of high-to-low, and ½ of the highest price). Register Δ-04, Δ-07, Δ-09 |
| 2 | Source claim | A time count equal to the price number of an extreme high, extreme low or range — and its multiples — marks where to watch for a change in trend. Nearness of that count to squares of 144 adds weight |
| 3 | Specified by Gann | Price quantity *Q* ∈ {extreme high, extreme low, range, minor highs/lows, second/third higher bottom}. Time count = *Q* in days, weeks **or** months. Multiples (the wheat low of 28 squares every 28 months). Comparison with multiples of 144 (281 vs 288) |
| 4 | Unspecified | Origin date for each count — for the range: the high's date, the low's date, or the later of the two; the wheat example leaves this implicit. Rupee translation; rounding of fractional prices; number of multiples; tolerance; history start for "ever sold" |
| 5 | Implementation assumptions | U-LIT with *Q* in as-traded rupees rounded to an integer (declared); T; origin date (candidate: the date of the extreme whose price is squared; for the range, the later extreme's date); multiples *k* ≤ *K*; tolerance *w*; running-extreme invalidation (§1.5); outcome O; *h* |
| 6 | Faithfully mechanizable? | **Yes, with declared assumptions.** It is Gann's most explicit price-time construct, with a worked example |
| 7 | Stock / index | Per stock (primary; p. 4 names individual stocks). Index is named too (averages), but its scale is unstated |
| 8 | Corporate actions | **Severe.** *Q* is a level. A bonus or split changes *Q* by the ratio. CA-POL required; Gann's old-stock-equivalent practice (register CA-03) is one candidate, declared as an assumption |
| 9 | Dimensional / scale | ₹ ≡ days/weeks/months by convention. **Structural consequence:** for most N100 stocks (₹ hundreds to thousands) *Q* in months or weeks exceeds the ~15.5-year span, and *Q* in days runs from months to decades. **Event availability depends on price level**, so the testable subset is selected by price. Disclose it and stratify; do not rescale |
| 10 | Causal / PIT | *Q* uses extremes to date. The event at origin + *k*·*Q* units is invalid if a new extreme replaces *Q* first (declared rule). The range needs both extremes confirmed |
| 11 | Null / controls | (i) **Scale placebos**: counts of 0.8·*Q* and 1.25·*Q*; (ii) **shuffled *Q***: the price number of another stock at a similar date; (iii) random anchors; (iv) coverage-matched null; (v) time-only hazard; (vi) price-level strata |
| 12 | Multiplicity | Illustrative: *Q* {high, low, range} = 3 × T = 4 × {count, count + near-144-multiple} = 2 → **24 cells** before *K*, *w*, O and *h* |

---

## 5. GF-4 — 360° circle divisions (GF-4T time; GF-4P price)

| # | Field | Definition |
|---|---|---|
| 1 | Primary basis | [MMPTC] p. 2 (the circle's parts agree with the parts of 144; important for time and price changes and resistance levels; watched when time periods in days, weeks or months reach these points — original typeface); p. 5 (1/16 of the circle ≈ 22½ months); p. 8 (divisions by 2, 3, 4, 8, 16, 32, 64, 6, 12 give points for time or price in days, weeks or months; halves, thirds and quarters "most important"); p. 9 (divisions by 24 ≈ 15 days; 180 months = half a circle; halfway points of highs/lows near degrees) — pp. 8–9 are the re-set pages (register §26.1). Register Δ-11, Δ-12 |
| 2 | Source claim | **GF-4T:** time counts from highs and lows reaching circle divisions (in days, weeks or months) mark changes in trend. **GF-4P:** price levels — especially halfway points — near circle degrees act as resistance |
| 3 | Specified by Gann | A tiered division set, ranked by Gann: **D1** = {180, 360} (halves), then {120, 240} (thirds) and {90, 270} (quarters) as most important; **D2** adds eighths {45, 135, 225, 315}; **D3** adds 16ths, 32nds, 64ths, and the 6th and 12th divisions {60, 300, 30, 150, 210, 330}; 24ths {15, 75, …}. Units: days, weeks, months. Price read in its quotation units as degrees |
| 4 | Unspecified | Which tier is primary; anchor; T; tolerance; "approximately" 15 days; for GF-4P, the translation and whether degrees above 360 wrap |
| 5 | Implementation assumptions | Tier (candidate primary **D1 ∪ quarters**, justified by Gann's "most important" wording — a textual, not outcome-based, choice, still the operator's to ratify); A + K; T; *w*; O; *h*. GF-4P adds U-LIT, the halfway-point anchor, and a wrap rule |
| 6 | Faithfully mechanizable? | **GF-4T: yes, with assumptions. GF-4P: yes, with assumptions, but level-based.** **D3 is effectively unfalsifiable** — 64ths every 5⅝ units cover almost everything — and is recommended off the pass path |
| 7 | Stock / index | Both. GF-4T is index-compatible; GF-4P index scale is unstated |
| 8 | Corporate actions | GF-4T: anchor identification only. GF-4P: severe (levels) — CA-POL |
| 9 | Dimensional / scale | GF-4T: pure counts. GF-4P: ₹ ≡ degrees by convention |
| 10 | Causal / PIT | As GF-1 |
| 11 | Null / controls | (i) **Placebo divisions** with matched coverage, non-Gann (1/7, 1/11 of 360); (ii) random anchors; (iii) coverage-matched null; (iv) calendar controls. (v) **Separability from GF-5**: a 360-day count and a one-year anniversary fall 5–6 calendar days apart, so windows of ±*w* ≥ 3 days overlap. Report GF-4T 360 and GF-5 year-1 on **disjoint** windows, or treat them as one event with the attribution unresolved. **GF-4T 360 is a circle count, not evidence of a 360-day year** (register §26.3). (vi) GF-4P: random price levels at equal density |
| 12 | Multiplicity | Illustrative GF-4T: tier {D1+quarters, D2} = 2 × A = 4 × T = 4 → **32 cells**. GF-4P: tier 2 × anchor {halfway of range, ½ of high} = 2 → **4 cells**, before *w*, O and *h* |

---

## 6. GF-5 — Pivot anniversary (month / year resolution)

| # | Field | Definition |
|---|---|---|
| 1 | Primary basis | [WSSS] p. 55 (the most important time is one year from the stock's own bottom or top, "not the calendar year", at month resolution; also every 3rd/6th/9th/12th month); [NSTD] p. 14 (watch for a change in trend one year, two years, etc. from any important top and bottom). Register ANN-01, ANN-02, Δ-17 |
| 2 | Source claim | One year, two years, etc. after an important top or bottom, watch for at least a change in the minor trend |
| 3 | Specified by Gann | Anchor = important top or bottom; lags = integer years; resolution = calendar month in [WSSS]; checkpoints at 3-month multiples |
| 4 | Unspecified | Significance; window within the anniversary month; outcome ("at least a change in the minor trend"); maximum number of years |
| 5 | Implementation assumptions | K + significance rule; window = the anniversary calendar month (faithful resolution) or ±*w* days (finer than Gann, declared); *n* ∈ {1, 2, …, *N*}; O; *h* |
| 6 | Faithfully mechanizable? | **Yes, with assumptions** |
| 7 | Stock / index | Per stock; index-compatible ([NSTD] uses averages) |
| 8 | Corporate actions | Anchor identification only |
| 9 | Dimensional / scale | Calendar time; no scale |
| 10 | Causal / PIT | Anchor confirmed before the window opens |
| 11 | Null / controls | (i) **Random-anchor anniversaries** (same stock, same calendar month, non-pivot dates) — absorbs results and dividend seasonality; (ii) **placebo lags** (e.g. 10 and 14 months); (iii) calendar month × expiry week; (iv) date-clustered errors (market-wide pivots synchronize anniversaries). A pass against placebo lags but not random anchors = **annual seasonality, not Gann** (catalogue Candidate 2, retained) |
| 12 | Multiplicity | Illustrative: resolution {month, ±*w* days} = 2 × *N* {1, 1–3} = 2 × anchor {tops, bottoms, both} = 3 → **12 cells** |

---

## 7. GF-6 — Absolute reaction-duration rules

| # | Field | Definition |
|---|---|---|
| 1 | Primary basis | [WSSS] p. 50 (weekly rule: active stocks seldom react more than 3–4 weeks before the main trend resumes; watch the 3rd week); pp. 50–51 (monthly rule: strong stocks seldom react into the 2nd month; next watch the 3rd or 4th month); [NSTD] p. 38 (in a bull market a stock going higher reacts no more than two to three months and resumes in the third month; a bear-market rally of only six to seven weeks, not over two months, is weakness). Register TIM-03, TIM-04, Δ-16 |
| 2 | Source claim | Reactions within a sound trend have absolute maximum durations. Exceeding them — or failing to resume by the third month — indicates the trend has weakened or changed |
| 3 | Specified by Gann | Separate statements, kept separate, not merged: **R-W** weekly, 3–4 weeks (active stocks); **R-M** monthly, not into the 2nd month (strong stocks); **R-N** reaction ≤ 2–3 months, resume in the 3rd month (bull market). Mirror for rallies in bear markets |
| 4 | Unspecified | Reaction start (confirmed top?) and end; "active" and "strong position"; how calendar months are counted ("into the 2nd month"); bull/bear market state; outcome |
| 5 | Implementation assumptions | K (reaction start at a confirmed high); calendar-week or calendar-month counting; activity or strength filter (declared, not tuned); market-state rule; O (candidate: main-trend resumption = close above the reaction's starting high by the stated deadline, vs not); *h* |
| 6 | Faithfully mechanizable? | **Yes, with assumptions.** The thresholds are Gann's, so they are not parameters to choose |
| 7 | Stock / index | Per stock; index-compatible ([NSTD] cites the Railroad Averages) |
| 8 | Corporate actions | Anchor identification only |
| 9 | Dimensional / scale | Absolute calendar time; no scale |
| 10 | Causal / PIT | The duration is known in real time once the reaction start is confirmed. The event at *t* = first session past the threshold with no resumption |
| 11 | Null / controls | (i) **Time-only hazard** of resumption versus elapsed time; (ii) **placebo thresholds** at non-Gann durations (e.g. 5 and 9 weeks) — the Gann thresholds are fixed and placebos show whether they are special; (iii) shuffled reaction histories; (iv) σ regime and momentum |
| 12 | Multiplicity | Illustrative: {R-W, R-M, R-N} = 3 × filter {on, off} = 2 × direction {reactions, rallies} = 2 → **12 cells** |

---

## 8. GF-7 — Culmination: third month, 3rd–4th move, 6–7 weeks

| # | Field | Definition |
|---|---|---|
| 1 | Primary basis | [WSSS] pp. 48–49 (the 3rd or 4th move is the culminating period; declines make 2, 3 or 4 moves); pp. 50, 83–84 (fast moves culminate in 6–7 weeks); [NSTD] p. 14 (failure to go higher in the third month indicated lower prices); p. 38. Register TIM-01, TIM-09, Δ-16. **TIM-10 (85–100 points) excluded** pending the translation ruling |
| 2 | Source claim | Trends culminate on the 3rd or 4th move. Fast moves culminate in the 6th–7th week. A move that cannot make new ground in its third month is failing |
| 3 | Specified by Gann | Ordinal counts {3, 4}; durations {6–7 weeks}; the third-month test |
| 4 | Unspecified | What counts as a move or hesitation; what "fast" means; when the move starts |
| 5 | Implementation assumptions | Segmentation rule (K on the construct's bar unit); "fast" threshold (declared, not tuned); move start; O; *h* |
| 6 | Faithfully mechanizable? | **Yes, with assumptions** — segmentation carries most of the weight |
| 7 | Stock / index | Per stock; index-compatible |
| 8 | Corporate actions | Segmentation on an as-of-*t* adjusted series; anchor identification only |
| 9 | Dimensional / scale | Counts and calendar time; no scale |
| 10 | Causal / PIT | Moves counted at confirmation only |
| 11 | Null / controls | (i) **Placebo counts** (2nd, 5th move); (ii) **placebo durations** (4 and 10 weeks); (iii) segmentation-matched random sequences (surrogate swings); (iv) momentum and σ |
| 12 | Multiplicity | Illustrative: {3rd–4th move, 6–7 weeks, third month} = 3 × segmentation 2 → **6 cells** |

---

## 9. Cross-construct structure

### 9.1 Overlaps (count once or attribute explicitly)

- **GF-1 ∩ GF-4T:** 90 is in both sets; 144's fractions and the circle's divisions coincide at
  2½-scaled points. Report overlapping counts once.
- **GF-3 uses GF-1:** nearness of *Q* to multiples of 144.
- **GF-4T 360 vs GF-5 one year:** separability required (§5 row 11).
- **GF-6, GF-7 share reaction and segmentation machinery:** a common detector K; events may coincide.
- **GF-2, GF-3, GF-4P are the translation-dependent level family:** one ruling, one CA-POL.

### 9.2 Multiplicity (illustrative, not a selection)

| Construct | Illustrative cells (before tolerance, outcome, horizon) |
|---|---|
| GF-1 | 32 |
| GF-2 | 9 |
| GF-3 | 24 |
| GF-4T / GF-4P | 32 / 4 |
| GF-5 | 12 |
| GF-6 | 12 |
| GF-7 | 6 |
| **Total** | **≈ 131** |

With 2–3 tolerance values, 2 outcomes and 2 horizons, the grid passes **1,000**.

**Recommendation:** one **primary cell per construct** (≈ 7–8 primary tests), pinned before any
read, with every other cell a declared robustness check off the pass path. Pin *m* in the PTMS
multiplicity register (catalogue §19 step 2). **Power is not computed here.** The demonstrability
arithmetic that closed C5, C4 and F1 applies to whatever *m* is pinned.

### 9.3 What a positive result would and would not mean

- **Would support Gann-specific content:** the construct beats its **scale / placebo-point** controls
  **and** the coverage-matched null **and** calendar and momentum controls, on the primary cell.
- **Would not:**
  - beating only a flat base rate;
  - equal performance under non-Gann scales, fractions or lags — evidence of a generic effect, not
    Gann;
  - a pooled result driven by a few stocks (per-stock heterogeneity diagnostic);
  - any Arm 2 reinterpretation's result.

---

## 10. Operator decisions required before any pre-registration

1. **Translation ruling:** is U-LIT (1 quoted point = ₹1 per space, daily chart) admissible? This
   decides GF-2, GF-3, GF-4P and TIM-10 together.
2. **Unread supplied sources:** read *45 Years in Wall Street* and *How to Make Profits in
   Commodities* before any freeze? They may add or alter time rules (GF-5 to GF-7), relative
   overbalance, and the 360-day question.
3. **Missing referenced material:** the Master Forecasting course (angle rules — GF-2 stays partial
   without it) and the Special Instructions (scales).
4. **Per-construct slots:** A/K, T, *w*, O, *h*, CA-POL, point tier — pinned from text and design
   reasoning only.
5. **Left-censoring policy** for "extreme ever sold" (§1.3).
6. **Family placement:** stock-level GF on N100 (Family F-type, own definition and RFA) versus index
   GF (Family C/D). Unchanged from catalogue §19.1(a).
7. **Primary cell per construct and the pinned *m*.**
8. **Provenance of [MMPTC]** — origin; pp. 8–9 re-set.

---

## 11. Governance status

- **CANDIDATE DEFINITIONS ONLY.** No construct selected, frozen or approved.
- **No market data read. No outcome read.** No RFA, TRAIN/HOLDOUT, backtest, performance
  calculation, parameter search or threshold fit.
- Thresholds quoted (3–4 weeks, 6–7 weeks, fractions of 144, circle divisions) are **Gann's text**,
  not fitted values.
- **No family definition modified.** Nothing here states or implies that Gann's framework has
  predictive power.
- Arm 2 reinterpretations (GA-3 / GS-5 and scaled angles) are **not** faithful tests of Gann's
  documented method and must be labelled so if ever run.

---

## 12. Addendum — Δ2 candidates and 1949 updates

**Source key:** **[45Y]** — *45 Years in Wall Street*, 1949 (reprint scan; register §27.1). Claim IDs
`Δ2-nn` are register §27.2.

### 12.1 Cross-cutting slots now given a Gann basis

| Slot | §1 status | 1949 basis | Candidate pin (recommendation, not frozen) |
|---|---|---|---|
| **K** — swing detector | Open (SWG-05/06) | 3-Day Chart rule, [45Y] p. 63 (Δ2-10) | **K3**: strict 3-Day Chart. The 2-day exception near extremes is discretionary, so it is **not** applied (declared departure) |
| **T** — time unit | Calendar or market days | "All of these moves are based on calendar days", p. 61; ch. VI tables in calendar days | **Calendar days** for every 1949 rule. GF-1 (1953, both admissible) is pinned to calendar days for one convention across the battery |
| **O** — change in trend | O1–O4 | Rule 10, p. 13 (Δ2-11) | **O-R10**: on K3, a break of the last swing low (trend was up) or a cross of the last swing top (trend was down) |
| **Market state** | Unspecified | Rule 9, p. 12: higher tops and bottoms = main trend up | **S9**: the last two K3 tops and bottoms both rising = bull state; both falling = bear state; otherwise no state |
| **Tolerance *w*** | Free | Rule 8 day windows carry widths (Δ2-06) | Gann's widths for GF-4T/R8; exact date (next session if a holiday) where Gann gives none |
| **Price basis** | CA-POL | Averages carry split-ups; a true average uses actual prices, p. 60 (Δ2-16) | Stage 1 (ratios and durations): an as-of-*t* ratio-adjusted series. Stage 2 (levels): as-traded, CA-POL |

### 12.2 GF-8 — Percentage of the stock's own high and low

| # | Field | Definition |
|---|---|---|
| 1 | Primary basis | [45Y] p. 8 (Rule 3); pp. 30–38 (ch. IV); pp. 94–95. Register Δ2-09; supersedes RET-01 |
| 2 | Source claim | A 50% decline from any high, or a 50% advance from any low, with the main trend, is a buying or selling point; the listed percentage bands and 100% act as resistance; 50% of the highest selling price and the halfway point of extreme high and low matter most |
| 3 | Specified by Gann | Bands {3–5, 10–12, 20–25, 33–37, 45–50, 62–67, 72–78, 85–87}%; 50% and 100% most important; with the main trend; importance ranking in ch. IV |
| 4 | Unspecified | Which high or low ("any"); the time dependence ch. IV mentions but does not quantify; what "resistance" does (hold vs reverse); horizon |
| 5 | Implementation assumptions | Anchor = a confirmed K3 top formed in S9 bull state (decline leg) / K3 bottom in bear state (advance leg) — Rule 3's "any high level" governs; the to-date extreme high (ch. IV "of greater importance") is robustness; band 45–50% as Gann gives it; O-R10 or a K3 turn inside the band; *h* |
| 6 | Faithfully mechanizable? | **Yes, with declared assumptions.** Scale-free: no translation ruling |
| 7 | Stock / index | Per stock (Rule 3 names individual stocks); index-compatible |
| 8 | Corporate actions | Ratio-invariant on an as-of-*t* adjusted series. Exclude windows spanning non-ratio events |
| 9 | Dimensional / scale | Dimensionless |
| 10 | Causal / PIT | Anchor to date; band entry at close *t* |
| 11 | Null / controls | (i) **Placebo bands** at non-Gann percentages with equal width (e.g. 38–43%, 53–58%); (ii) surrogate price paths per stock; (iii) momentum and σ; (iv) price-level strata (diagnostic). **Also the price-only control for GF-10** |
| 12 | Multiplicity | Illustrative: band {50% of high, halfway of range} 2 × leg {decline, advance} 2 × outcome 2 → **8 cells** |

### 12.3 GF-9 — Modal swing duration

| # | Field | Definition |
|---|---|---|
| 1 | Primary basis | [45Y] p. 57 (ch. VI); swing tables in calendar days. Register Δ2-14 |
| 2 | Source claim | Record the time of each important swing; watch for a change in trend at the end of the time cycle that has repeated most often |
| 3 | Specified by Gann | Per-market history of swing durations; the mode; calendar days |
| 4 | Unspecified | "Important" swings; binning of durations; minimum history; tolerance |
| 5 | Implementation assumptions | K3 swings; bins (declared, e.g. Rule 8 window bands reused as bins — a textual, not fitted, choice); expanding history to date; *w* = bin width |
| 6 | Faithfully mechanizable? | Yes, with assumptions. **Literal on an index** (chapter title: swings on the averages). **Per-stock = declared extension** |
| 7 | Stock / index | Index literal; stock extension |
| 8 | Corporate actions | Anchor identification only |
| 9 | Dimensional / scale | Calendar time |
| 10 | Causal / PIT | Mode from swings completed before *t* |
| 11 | Null / controls | (i) surrogate swings; (ii) placebo quantile (median, 75th percentile); (iii) time-only hazard |
| 12 | Multiplicity | Illustrative: binning 2 × direction 2 → **4 cells** |

### 12.4 GF-10 — Rule 8 time overbalance (PENDING operator acceptance; ruling 7) — ACCEPTED 2026-09-15 (R-5), ruling 7 superseded

| # | Field | Definition |
|---|---|---|
| 1 | Primary basis | [45Y] pp. 11–12 (Rule 8, *Market Over-Balanced*); p. 39 (greatest time period); p. 62. Register Δ2-01, Δ2-02, Δ2-04, Δ2-15 |
| 2 | Source claim | In an advancing market, when the time of a decline exceeds the time of the previous decline, a change in trend is indicated; in a long decline, the first rally exceeding the previous rally in time signals a change, at least temporarily. Price overbalance is the parallel rule, and the time change is the more important |
| 3 | Specified by Gann | Current vs previous counter-move **duration**; bull and bear mirrors; "first time"; time ranked above price |
| 4 | Unspecified | Swing detector (K3 now available); "previous" = immediately preceding vs greatest prior (p. 39); market state; outcome and horizon |
| 5 | Implementation assumptions | K3; S9 state; primary comparison = **immediately preceding** counter-move (Rule 8's paired price clause says "the previous decline"); greatest-prior as robustness; event = first session the current counter-move's calendar-day duration exceeds the previous one's; O-R10; *h* |
| 6 | Faithfully mechanizable? | **Yes, with declared assumptions** |
| 7 | Stock / index | Per stock ("Averages or individual stocks", p. 11); index-compatible |
| 8 | Corporate actions | Durations immune. Price leg ratio-invariant on an as-of-*t* series |
| 9 | Dimensional / scale | Time : time. Price leg points : points within one stock — no translation |
| 10 | Causal / PIT | Durations from confirmed K3 turning points; the current counter-move's start is confirmed before *t* |
| 11 | Null / controls | (i) **Surrogate price paths** through identical K3 machinery. **This is the pass criterion, not zero**: a longer decline is mechanically more likely to break the last low; (ii) **price overbalance** (Δ2-02) as Gann's own contrast — time should outrank it; (iii) GF-8 price-only; (iv) time-only hazard; (v) momentum and σ |
| 12 | Multiplicity | Illustrative: comparison {previous, greatest} 2 × leg {time, price} 2 × direction 2 → **8 cells** |

### 12.5 Updates to GF-4T to GF-7 (additional primary bases)

| Construct | 1949 addition | Effect on the definition |
|---|---|---|
| GF-4T | **R8 windows**: 7–12, 18–21, 28–31, 42–49, 57–65, 85–92, 112–120, 150–157, 175–185 days from any high or low; importance weighting ([45Y] p. 11) | Candidate primary basis **GF-4T/R8**: Gann gives the unit and the widths. Counted with the [MMPTC] circle divisions as one family (register §27.4 item 5) |
| GF-5 | Ch. IX anniversary **months** of extreme highs and lows, each year (pp. 92–93); Rule 10 exactly 1–5 years and 15, 22, 34, 42, 48, 49 months (p. 13) | Resolution = month (the rule sentence); exact-date and month-count forms are robustness |
| GF-6 | Rule 4: 3-week reaction; after 30+ days next window about 6–7 weeks; after 45–49+ days about 60–65 days, the greatest average bull reaction (pp. 8–9) | Adds an R-49 cell (reaction beyond 65 calendar days). WSSS, NSTD and 45Y agree on about two months |
| GF-7 | Rule 5: 3–4 sections (p. 9). Rule 8: at the 3rd–4th section, a smaller price gain **and** a shorter time than the previous section = change due (p. 12) | Adds **R8S**: section = a K3 upswing; section count ≥ 3; both gain and duration below the previous section's |
| TIM-10 and point rules | Rule 2 (2–3 points), Rule 6, Rule 12 (1 point per day), 9-Point Chart, 5-point rule | Join GF-3 / GF-4P in the translation-dependent stage 2 |

### 12.6 Not for an N100 cross-section

- Rule 8 seasonal dates, Rule 10 holiday dates, ch. VIII months of extreme highs: identical for every
  stock. Index design only (Family C/D).
- GF-2 (angles): excluded from the first faithful experiment (decision B).

### 12.7 Governance

- **CANDIDATE DEFINITIONS ONLY.** Nothing selected, frozen or approved. GF-10 pending operator
  acceptance.
- 2026-09-15: GF-10 accepted as GANN-FAITHFUL (R-5). Stage-1 membership ruled (R-6 to R-8). Still
  nothing frozen.
- No market data or outcome read; no RFA, TRAIN/HOLDOUT, backtest or parameter fit. Thresholds are
  Gann's text.
