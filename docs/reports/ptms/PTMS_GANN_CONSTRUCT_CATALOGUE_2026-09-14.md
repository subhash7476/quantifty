# PTMS — Gann Construct Catalogue / Hypothesis-Design Document

**Date:** 2026-09-14 · **Branch:** `research/ptms-price-time-market-structure`
**Status:** GANN CONSTRUCT CATALOGUE / HYPOTHESIS-DESIGN DOCUMENT. **Not a frozen hypothesis.**
No construct is selected, frozen or approved by appearing here. No TRAIN/HOLDOUT exists. No RFA was
run. No outcome value was read. See §20.

**Addendum (2026-09-14, post-F0):** §21 records status changes from the F0 primary-source register
and its delta Δ1 (register §26, 1953 *Master Mathematical Price Time and Trend Calculator*). The
status table, §17 shortlist and §18 rejections below are **preserved as originally written** and are
**superseded where §21 differs**. Faithful constructs GF-1 to GF-7 are defined in
`PTMS_GANN_FAITHFUL_CONSTRUCT_DEFINITION_2026-09-14.md`.

**Inputs:**
- Operator brief of 2026-09-14 (Gann construct catalogue).
- Substrate description: `PTMS_N100_EOD_FEASIBILITY_AUDIT_2026-09-14.md` (commits `a8c7e37`, `1aff3ae`).
- Governing definitions:
  - `PTMS_P3_FAMILY_CATALOGUE_2026-09-12.md` (Families B, C, D, F);
  - `PTMS_ALIGNMENT_RECORD_2026-09-12.md` (§2 "Gann strategy → Price-Time research");
  - `PTMS_P0_P1_PLAN_2026-09-12.md` (ruling §4);
  - `PTMS_N100_INTENDED_EXPERIMENT_AUDIT_2026-09-14.md` (§10, ruling #3 §4);
  - `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` (GR-1).

No store was queried for this document. Every data statement is carried from the feasibility audit.

---

## Construct status table (all candidates)

Status key: **P** = PRIMARY CANDIDATE · **S** = SECONDARY CANDIDATE · **D** = DESCRIPTIVE ONLY ·
**NT** = NOT TESTABLE · **R** = REJECTED BEFORE TESTING. "≡" marks a mathematical equivalence,
counted **once** in multiplicity (§15).

| ID | Construct | Dimensional resolution | Anchor causality | CA exposure | Status |
|---|---|---|---|---|---|
| GA-1 | Literal fixed-unit angle (₹ per day) | None — price ≡ time by fiat | Depends on pivot | Level; fatal | **R** |
| GA-2 | Normalized-scale angle ray (σ / ATR / fixed-% per session) | Data-derived scale; ratio set loses privilege | Delayed-causal pivot | Displacement | **S** |
| GA-3 | Self-scaled 1×1: break of the prior-swing rate ray | Rate : rate (like with like) | Delayed-causal pivot | Displacement | **P** |
| GA-4 | Angle fan touch-reversal (multi-ray support/resistance) | As GA-2 or GA-3 | Delayed-causal pivot | Displacement | **S** |
| GA-5 | Chart-drawn 45° visual angle | Pixels | Visual | — | **NT** |
| GS-1 | Price level = elapsed time count (incl. "square of a high/low") | None — rupees ≡ days | Varies | Level; fatal | **R** |
| GS-2 | Absolute price change = elapsed days ("square of the range") | None | Delayed-causal | Level/points; fatal | **R** |
| GS-3 | Diffusive square: \|Δx\|/σ = √ΔT | σ as random-walk conversion | Delayed-causal | Displacement | **S** |
| GS-4 | Linear normalized square: \|Δx\|/s = ΔT | Data-derived scale | Delayed-causal | Displacement | **S** (≡ GA-2 at n = 1) |
| GS-5 | Ratio square: A_cur/A_prev = D_cur/D_prev | Price:price vs time:time | Delayed-causal | Displacement | **P** (≡ GA-3 touch) |
| GT-1 | Pivot anniversary (integer years from a causal major pivot) | Time : calendar year (pinned) | Delayed-causal | None on time axis | **P** |
| GT-2 | Time symmetry: elapsed = prior swing duration | Time : time | Delayed-causal | None on time axis | **P** |
| GT-3 | Circle-division day counts from pivot (45, 90, 120 … 360) | Time : pinned day counts | Delayed-causal | None on time axis | **S** |
| GT-4 | Fixed seasonal calendar dates (equinox/solstice, midpoints) | Calendar | Causal (fixed) | None | **D** (index claim; fails veneer test on N100) |
| GT-5 | Long master cycles (7/10/20/30/60-year) | Calendar | Causal | None | **NT** (≤ 1 repetition in 15.5 y) |
| GT-6 | Listing-date anniversaries | Calendar | Causal | None | **D** |
| GT-7 | Swing-duration recurrence (distributional) | Time : time | Delayed-causal | None | **D** |
| GN-1 | Square-of-Nine price levels (√P steps from a pivot) | None — √ of a rupee level | Delayed-causal | **Level; intrinsically CA-vulnerable** | **S** (heavily constrained) |
| GN-2 | Square-of-Nine time counts (√ΔT steps) | Time only | Delayed-causal | None on time axis | **S** |
| GN-3 | Square-of-Nine price-time coincidence (same wheel angle) | None — rupees ≡ days | Delayed-causal | Level; fatal | **R** |
| GN-4 | Traditional wheel / overlay readings | Visual / interpretive | Visual | — | **NT** |
| GO-1 | Range-division retracement (eighths, 50%) | Price : price | Delayed-causal | Displacement | **S** (price-only; also a control) |
| GO-2 | Overbalance: time (and price) overbalance of the largest prior correction | Time : time, price : price | Delayed-causal | Displacement + time | **P** |
| GO-3 | Round-number / "natural" price levels | Level | Causal | Level; fatal | **D** (not Gann-specific) |
| GO-4 | Planetary / astrological time | Outside data | — | — | **R** |
| GO-5 | Gann swing-chart pivot rule | Auxiliary anchor generator | Delayed-causal | — | **D** (not a hypothesis) |
| GX-1 | Per-stock event study, pooled (unit: stock-event) | Inherits | Inherits | Inherits | **Architecture — P-compatible** |
| GX-2 | Formation-date cross-sectional rank of a per-stock state (unit: date × stock) | Inherits | Inherits | Inherits | **Architecture — P-compatible (Family F native)** |
| GX-3 | Synchronicity breadth → index move | Inherits | Inherits | Inherits | **R for Family F** (veneer; index claim) |
| GX-4 | Universality vs stock-specific scale (heterogeneity) | Inherits | Inherits | Inherits | **D** |

**Shortlist recommended for formal pre-registration (§17), not selected:** GO-2 (time overbalance),
GT-1 (pivot anniversary), GA-3 ≡ GS-5 (self-scaled 1×1 break), with GT-2 (time symmetry) as an
alternate.

---

## 1. Executive summary

1. **"Gann theory" is not a hypothesis.** It is a practitioner corpus of geometric, numerical and
   calendrical rules. Decomposed, it yields 26 distinct candidate constructs plus 4 cross-sectional
   architectures.
   - 5 are **rejected before testing** and 3 are **not testable**.
   - 5 are **descriptive only**, 8 are **secondary** and 5 are **primary** candidates.
   - Two pairs are mathematically equivalent (GS-5 ≡ GA-3; GS-4 ≡ GA-2 at n = 1), so there are
     4 independent primary and 7 independent secondary constructs.
   - These counts cover the 26 constructs only. The 4 cross-sectional architectures are tallied
     separately: GX-1 and GX-2 P-compatible, GX-3 rejected for Family F, GX-4 descriptive.
2. **The decisive filter is dimensional.** Price and time are different dimensions. A Gann
   statement is dimensionally valid only if it does one of two things:
   - compares **like with like** — price : price, time : time, or rate : rate;
   - compares a quantity with an **externally pinned unit** — the calendar year, or a fixed day count.
   Any statement equating a price quantity to a time quantity ("price = time", "1 point per day",
   "price 144 ↔ day 144") needs a conversion constant. Gann does not provide one for NSE equities, so
   those statements are **rejected before testing**.
3. **Under any data-derived price scale (σ, ATR), the canonical angle ratios lose their privileged
   status.** The "1" in 1×1 is meaningful only under an exogenous scale. Once *s* = k·σ, the ratio
   set {1/4, 1/2, 1, 2, 4…} is an arbitrary grid over a continuous parameter, and an angle family
   becomes the fishing machine the P3 catalogue's Family C row already warns about
   (*m* = 5·k·j). **The one formulation that restores a privileged 1 is self-scaling:** slope equal to
   the stock's own prior-swing rate (GA-3).
4. **Absolute-price-level constructs are intrinsically corporate-action-vulnerable, and no price
   basis rescues them.**
   - Raw prices break the geometry at 112 bonus/split ex-dates.
   - Backward-adjusted levels depend on future events.
   - Spin-offs, rights issues and special dividends are unadjusted in both.
   This decides the fate of the Square-of-Nine price wheel (GN-1), price-equals-time squares
   (GS-1, GS-2) and round numbers (GO-3). **Scale-free constructs survive**: displacement ratios,
   durations, calendar distances.
5. **Anchor causality is a classification axis, not a detail.**
   - Swing pivots are causal only with a declared detection delay (repo rule:
     `result.iloc[i + period]`, never a centered window).
   - Full-sample "major highs/lows" and "all-time highs" are look-ahead. On this panel an
     "all-time" high also means "since 2010-01-04".
6. **Governance collision, surfaced and not resolved.**
   - Ruling §4 / §7 pins **Gann = Family C, single-index `per_trade_pnl`, with "no cross-sectional
     rank-IC manufactured by applying an index rule to the equity universe"**. The operator's present
     direction places Gann on PIT N100 stocks.
   - Ruling #3 §4 requires a stock-level price-time hypothesis to have "its own definition,
     multiplicity accounting, RFA and pre-registration" and to be genuinely stock-level.
   - **This catalogue cannot reclassify C → F.** It applies an explicit **veneer test** (§11) to
     every cross-sectional construct. Constructs that are index rules in disguise (GT-4, GX-3) are
     excluded from the Family F reading. The family-placement ruling remains the operator's.
7. **The honest expectation** is the one the charter already stated: most of the corpus is
   descriptive or untestable, and the survivors are scale-free, causally anchored,
   calendar- or ratio-pinned constructs. That is a successful outcome for this document.

---

## 2. What "Gann theory" actually claims

The claims below are stated as commonly transmitted in practitioner literature. **No claim is
assumed true.** Where the corpus is internally inconsistent, the inconsistency is itself recorded as
a degree of freedom.

| # | Claim (as transmitted) | Kind |
|---|---|---|
| C1 | Price and time are interchangeable; when a move's price and time "square", a change in trend is due | Price × time equality |
| C2 | Angles from significant highs/lows (1×1 "45°", 2×1, 1×2, 4×1, 1×4, 8×1, 1×8 …) act as support/resistance; a trend holding above the 1×1 is strong, and breaking it signals the next angle | Price × time geometry |
| C3 | A move "balances" when its duration or extent matches a prior move; **when time overbalances (a correction lasts longer than the largest prior correction), the trend has changed** | Ratio / overbalance |
| C4 | Anniversaries of important highs/lows (one year, and divisions of the year / circle — 90, 180, 270, 360 days; also 45, 120, 135, 225, 240, 315) mark potential turning points | Calendar time |
| C5 | Seasonal dates (around equinoxes/solstices and their midpoints) are natural turning times | Fixed calendar |
| C6 | Long "master" cycles (e.g. 10, 20, 30, 60 years) govern major trends | Long calendar cycles |
| C7 | Price ranges divide naturally into eighths and thirds; 50% is the most important retracement | Price-only |
| C8 | The Square of Nine (a number spiral) locates support/resistance prices and turning dates at angular positions (45°, 90°, 180°, 360°); **the same wheel maps price and time** | Numerical geometry |
| C9 | The "square of the range" (a price range expressed as a count of days) and the "square of a high/low" (the price of an extreme as a count of days) time future turns | Price ↔ time conversion |
| C10 | Planetary / astrological cycles govern market timing | External |

**Internal ambiguities of the corpus itself** — theory-level, not researcher-level:
- 360-day vs 365.25-day year;
- calendar days vs market days;
- arithmetic vs logarithmic chart geometry;
- which price series (close, high/low);
- which swing counts as "significant".

Gann's own work was on individual instruments (commodities, the Dow and single stocks) with
instrument-specific price-per-day scales. None of the corpus is specified for a cross-section.

---

## 3. Why the claims are difficult to operationalize

| Obstacle | Where it bites | Consequence |
|---|---|---|
| **Dimensional incommensurability** (§4) | C1, C2, C8, C9 | Needs a conversion constant the theory does not supply for NSE equities |
| **Anchor selection** (§5) | C2, C3, C4, C8, C9 | "Significant high/low" is retrospective unless mechanized with delay |
| **Tolerance** | Every "touch", "square" or "anniversary" | Exact equality has probability ≈ 0 on discrete sessions; any band is a researcher choice |
| **Event vs outcome coupling** | Turning-point claims | The outcome "a turn happened" is itself a pivot-detection rule. It must use data strictly after the event and must not share the pivot that defined the event |
| **Direction** | C2, C3, C4 | Most claims say "change" or "turn" without a sign. Directional labels require a sign rule relative to the prior move |
| **Fan multiplicity** | C2, C4, C8 | Many rays / counts / angles → many chances to "hit" by construction |
| **Visual interpretation** | C2, C8 practice | Chart scale, choice of angle, redrawing after the fact |
| **Corporate actions** (§14) | Every level-based claim | Nominal price changes 1:k with no economic change |
| **Common confounders** (§12) | All | Momentum, reversal, volatility clustering, earnings/dividend seasonality, index reviews, expiry cycles |

---

## 4. The dimensional / unit problem

### 4.1 The core point

Let *x* be a price quantity and *t* a time quantity. "*x* = *t*" has meaning only via a constant
*c* with units price/time: *x* = *c*·*t*. Every Gann angle and square is a claim about *c*.

**Gann does not supply *c* for NSE equities.** His scales were instrument- and era-specific
conventions (e.g. one cent per day on a grain contract). The ₹ is not a natural unit for a ₹100 stock
and a ₹30,000 stock simultaneously, and a 1:10 split changes *c* by a factor of ten overnight.

### 4.2 Admissible price representations and what each does to the hypothesis

| Representation | Definition (at session *t*) | Scale-free across stocks? | CA-robust? | What the Gann claim becomes |
|---|---|---|---|---|
| Absolute price | *P_t* (₹) | No | No (level) | Literal Gann; meaningless across a ₹100 / ₹30,000 cross-section |
| Absolute change | *P_t − P_O* (₹) | No | No | "*k* rupees per day" — stock-dependent, split-dependent |
| Percentage change | (*P_t/P_O* − 1) | Yes | Yes (within event-free span) | Asymmetric up/down; "*k*% per day" rays are curves in log space |
| Log change | *x_t − x_O*, *x* = ln *P̃* | Yes | Yes (within event-free span / as-of-*t* adjusted) | Symmetric; rays are constant-growth paths |
| ATR-normalized | (*P_t − P_O*)/ATR_ℓ | Yes | Partly (ATR also jumps at raw ex-dates) | Price in "typical daily ranges"; *c* = *k*·ATR is data-derived |
| σ-normalized (log) | (*x_t − x_O*)/σ_ℓ | Yes | Yes | Price in "typical daily σ"; *c* = *k*·σ data-derived |
| Diffusion-consistent | (*x_t − x_O*)/(σ_ℓ·√(*t − O*)) | Yes | Yes | A random-walk z-score; "square" means z = 1. **This is σ's model, not Gann's** |
| Self-scaled (prior swing) | (*x_t − x_O*) / (A_prev/D_prev · (*t − O*)) | Yes | Yes | Current rate relative to the stock's own previous rate; "1" = equal rates |
| Cross-sectional rank | rank of a per-stock statistic among N100 at *t* | Yes | Yes | Removes the level entirely; the claim becomes relative |
| Market-residual | *x* minus β·(index log change) | Yes | Yes | Idiosyncratic geometry; β estimation adds DoF |
| Fixed Gann-style unit | e.g. 1 unit = 1% or ₹1 per day | 1%: yes; ₹1: no | 1%: yes; ₹1: no | Exogenous but **not given by the theory** for this market — an assertion, not a derivation |

Notation used below: *P̃_t* is the price on the declared price basis (§14), *x_t* = ln *P̃_t*;
σ_ℓ(t) is the trailing standard deviation of daily log changes over ℓ sessions ending at *t*−1.

### 4.3 The consequence for ratios

If *s* is data-derived (σ, ATR), a ray of slope *n*·*s* is one member of a continuous family
indexed by *n*. **Nothing in the theory privileges *n* = 1** — the canonical set {1/8 … 8} becomes an
arbitrary grid, and each element is an extra test.

The ratio set regains meaning only when the comparison is between like quantities:
- **rate : rate** (GA-3 / GS-5: *n* = 1 means "the same speed as the prior swing");
- **time : time** (GO-2, GT-2: "longer than the longest prior correction", "as long as the prior
  swing");
- **price : price** (GO-1: "half the range");
- **time : pinned calendar unit** (GT-1, GT-3: "one year").

### 4.4 Arithmetic vs logarithmic geometry

Gann drew on arithmetic charts. A straight arithmetic ray is a curve in log price. For an N100 stock
that moves 5–10× over the panel, arithmetic rays drawn from early pivots are dominated by level
rather than behaviour. This is a **theory-level ambiguity with two values**. Log geometry is the
modern-fidelity reading; it is not a correction of Gann, and choosing it is a disclosed departure.

### 4.5 Time representations

| Axis | Definition | Where the theory points |
|---|---|---|
| Trading sessions | Count of `trading_calendar` sessions | Natural for rays/rates on EOD data; ignores weekends/holidays |
| Calendar days | Date difference | **Gann's anniversaries and circle divisions are calendar-based** (C4, C5, C9) |
| Calendar years | 365.25 or 360 days | C4 — **a theory-internal ambiguity, two values** |

**Sessions vs calendar days is a theory-relevant degree of freedom, not an implementation detail:**
a 90-calendar-day count is ~62 sessions, and the two place events on different dates. The panel has
3,834 sessions spanning ~5,650 calendar days.

---

## 5. The anchor / origin problem

### 5.1 Anchor classes

| Class | Anchors | Usable as stated? |
|---|---|---|
| **Causal by construction** | Listing date; fixed calendar origin; prior-session close; running extremum over **strictly prior** data (e.g. max high over the previous *W* sessions); N100 membership start date (PIT) | Yes |
| **Causal only with declared detection delay** | Swing pivots: a *k*-session swing high at session *i* is **known at *i* + *k***. Gann swing-chart pivots (1-, 2-, 3-day charts) are known when the reversal condition completes | Yes, **if** every event and statistic is time-stamped at confirmation, never at *i* (repo rule: `result.iloc[i + period]` assignment, never a centered window) |
| **Look-ahead by construction** | All-time high/low over the full sample; "major" turning points labelled retrospectively; centered-window pivots; the "significant" swing chosen by eye; zig-zag filters that repaint | **NOT TESTABLE as stated**: restate with a causal anchor or reject |

### 5.2 Panel-specific anchor facts (from the feasibility audit)

- **Left censoring.** EOD history starts **2010-01-04**, so a running extremum is "highest since
  2010-01-04 (or since listing, if later)", not an all-time high. Any "all-time high/low" anchor
  silently changes meaning on this panel.
- **Membership vs history.** Price history before a stock's N100 entry is PIT-known and may feed
  anchors. **Eligibility of an event** is decided by membership at the event date. Whether
  pre-membership pivots may anchor post-entry events is a declared choice (§15).
- **Listing date.** `instrument_master.listing_date` exists as a VARCHAR field and is not audited.
  The first trade in `equity_bhavcopy` is left-censored at 2010-01-04 for older listings.

### 5.3 "Major" pivot — the unavoidable researcher choice

Every mechanized "significant" pivot needs at least:
- a confirmation delay *k*;
- a significance rule — e.g. extremum over a trailing window *W*, amplitude ≥ *q*·σ, or a Gann
  swing-chart order;
- a tie rule.

None is theory-pinned, except that Gann's swing charts supply a small attested set of orders
(1-, 2-, 3-day).

---

## 6. Full construct catalogue

Each construct lists fields 1–25 of the brief. In field 17, **[T]** means theory-defined,
**[T?]** a theory-internal ambiguity, and **[R]** a researcher choice. Rejected and untestable
constructs keep every field so that the reason for rejection is auditable.

### 6.1 Angles

#### GA-1 — Literal fixed-unit angle

| # | Field | Specification |
|---|---|---|
| 1 | ID | GA-1 |
| 2 | Name | Literal fixed-unit Gann angle |
| 3 | Gann claim | From a significant low, the 1×1 rises one price unit per time unit; price above it = strong trend |
| 4 | Math | Ray *R_n*(*t*) = *P_O* + *n*·*u*·(*t* − *O*), with *u* a fixed ₹ per day |
| 5 | Data | Daily close / high / low (raw) |
| 6 | Anchor | Significant high/low |
| 7 | Price transform | None (₹) |
| 8 | Time transform | Calendar days or sessions |
| 9 | Geometry | Straight arithmetic rays |
| 10 | Event | Close crosses or touches *R_n* |
| 11 | Outcome | Forward change |
| 12 | Direction | Directional |
| 13 | Scope | Single-series |
| 14 | N100 EOD? | Mechanically yes |
| 15 | Assumptions | ₹ is a natural unit for every stock; level is economically meaningful |
| 16 | Parameters | *u*, *n*, anchor rule, tolerance, horizon, time axis |
| 17 | Theory vs choice | *n* set [T]; *u* [R] (no NSE value in theory); everything else [R] |
| 18 | DoF | *u* is unbounded and stock-specific |
| 19 | Price-only control | Horizontal level at the same distance |
| 20 | Time-only control | Elapsed time since anchor |
| 21 | Confounders | Price level, splits, trend |
| 22 | Falsification | Not reachable: any result can be re-scaled by choosing *u* |
| 23 | Economic interpretation | None across a ₹100–₹30,000 cross-section |
| 24 | Realistic with our data? | No — 112 bonus/split ex-dates re-scale *u* |
| 25 | Status | **REJECTED BEFORE TESTING** (dimensionally invalid; CA-fatal) |

#### GA-2 — Normalized-scale angle ray

| # | Field | Specification |
|---|---|---|
| 1 | ID | GA-2 |
| 2 | Name | Normalized-scale angle ray from a causal pivot |
| 3 | Gann claim | As GA-1 (C2) |
| 4 | Math | *L_n*(*t*) = *x_O* + *n*·*s*(*O*)·Δ*T*, where *s* ∈ {*k*·σ_ℓ(*O*), *k*·ATR_ℓ(*O*)/*P_O*, fixed *q*% per session} is frozen at the confirmation of *O*; Δ*T* in sessions or calendar days |
| 5 | Data | Daily OHLC; trailing σ or ATR |
| 6 | Anchor | Causal swing pivot, time-stamped at confirmation *O* + *k* |
| 7 | Price transform | Log price, on the declared basis (§14) |
| 8 | Time transform | Sessions (default reading) or calendar days [T?] |
| 9 | Geometry | Rays in log space, slope *n*·*s* |
| 10 | Event | First confirmed close crossing *L_n* after *O* + *k* (break), or within tolerance τ of *L_n* (touch) |
| 11 | Outcome | Forward log change over *h*, signed by the ray's direction; or turn incidence within *h* |
| 12 | Direction | Directional (break = trend weakening) |
| 13 | Scope | Single-series per stock; pooled (GX-1) or ranked (GX-2) |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | The normalizing scale is the "natural" unit for Gann rays |
| 16 | Parameters | Scale family, *k*, ℓ, *n* set, pivot rule, τ, *h*, time axis, arithmetic vs log |
| 17 | Theory vs choice | *n* set [T] *but meaningless under a data-derived s* (§4.3); arithmetic vs log [T?]; time axis [T?]; everything else [R] |
| 18 | DoF | Scale family × *k* × ℓ × rays × τ × *h* — the Family C *m* = 5·*k*·*j* surface |
| 19 | Price-only control | Horizontal level at the same displacement from *x_O*, with no slope |
| 20 | Time-only control | Same Δ*T* since pivot with no price condition |
| 21 | Confounders | Momentum since pivot (a ray break ≈ trailing return below *n*·*s*·Δ*T*); volatility regime; reversal |
| 22 | Falsification | Break/touch indicator adds no information over price-only + time-only + momentum controls; placebo slopes (*n* ∉ Gann set) perform as well |
| 23 | Economic interpretation | Weak: a trend-intensity threshold with an arbitrary constant |
| 24 | Realistic with our data? | Yes mechanically; the multiplicity is the problem |
| 25 | Status | **SECONDARY CANDIDATE** (GS-4 ≡ GA-2 at *n* = 1) |

#### GA-3 — Self-scaled 1×1: break of the prior-swing rate ray

| # | Field | Specification |
|---|---|---|
| 1 | ID | GA-3 (≡ GS-5 at touch) |
| 2 | Name | Self-scaled 1×1 break |
| 3 | Gann claim | C2 + C3: a trend is sound while it advances at least at its "natural" rate; losing the 1×1 means the trend weakens |
| 4 | Math | Confirmed pivot *O* ends prior leg *j*−1 with amplitude *A* = \|*x_O* − *x*_{O'}\| and duration *D* = *O* − *O'* (*O'* = previous confirmed pivot). Rate ρ = *A*/*D*. Ray: *L*(*t*) = *x_O* + sgn·ρ·(*t* − *O*), where sgn is the new leg's direction |
| 5 | Data | Daily high/low (pivots), close (events) |
| 6 | Anchor | Two consecutive confirmed pivots *O'*, *O*; causal at *O* + *k* |
| 7 | Price transform | Log price (rate : rate is scale-free) |
| 8 | Time transform | Sessions (rate per session); calendar variant [T?] |
| 9 | Geometry | One ray whose slope equals the stock's own prior-leg rate |
| 10 | Event | First session *t* ≥ *O* + *k* at which the close crosses *L* against sgn (break). Touch variant: within τ |
| 11 | Outcome | Forward log change over *h*, signed by sgn (claim: sign opposite to the leg); or turn incidence within *h* |
| 12 | Direction | Directional relative to the leg |
| 13 | Scope | Per stock; pooled or ranked |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | The prior leg's rate is the relevant "1×1" unit; one prior leg is representative |
| 16 | Parameters | Pivot rule and *k*; leg definition (prior leg vs mean of prior *m* legs); break vs touch; τ (touch); *h*; outcome definition; time axis |
| 17 | Theory vs choice | *n* = 1 [T] — **privileged, because rate : rate**; which leg sets ρ [R]; *k* from Gann swing-chart orders [T set of 3]; everything else [R] |
| 18 | DoF | Moderate: *k* (3) × ρ source (≤ 2) × event type (2) × *h* × outcome |
| 19 | Price-only control | Close falls below a horizontal level at the same current distance from *x_O* (no slope) |
| 20 | Time-only control | Same elapsed Δ*T* since *O* without the ray condition |
| 21 | Confounders | Momentum deceleration; short-term reversal; volatility change between legs; mean-reverting leg rates |
| 22 | Falsification | The 1×1 break adds nothing over price-only, time-only, momentum and σ-change controls; **placebo rates** (ρ scaled by 0.8 / 1.25, or ρ drawn from another stock's leg) perform as well; or the sign is wrong |
| 23 | Economic interpretation | Yes: loss of trend speed relative to the stock's own recent behaviour |
| 24 | Realistic with our data? | Yes |
| 25 | Status | **PRIMARY CANDIDATE** |

#### GA-4 — Angle fan touch-reversal

| # | Field | Specification |
|---|---|---|
| 1 | ID | GA-4 |
| 2 | Name | Multi-ray support/resistance fan |
| 3 | Gann claim | C2: price moves from angle to angle; each ray is support/resistance |
| 4 | Math | Rays *L_n* for *n* ∈ {1/8, 1/4, 1/3, 1/2, 1, 2, 3, 4, 8} under the GA-2 or GA-3 scale; event = touch of any ray within τ followed by rejection |
| 5 | Data | Daily OHLC |
| 6 | Anchor | Causal pivot |
| 7 | Price transform | Log |
| 8 | Time transform | Sessions / calendar |
| 9 | Geometry | Fan of 9 rays |
| 10 | Event | Touch within τ of any ray |
| 11 | Outcome | Reversal away from the ray within *h* |
| 12 | Direction | Directional (away from ray) |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | Every ray is equally meaningful; touches are rare relative to chance |
| 16 | Parameters | Ray set, scale, τ, rejection rule, *h* |
| 17 | Theory vs choice | Ray set [T]; everything else [R] |
| 18 | DoF | **Severe**: with 9 rays and any τ, a touch is near-certain in a range-bound market |
| 19 | Price-only control | Touch of random horizontal levels with matched density |
| 20 | Time-only control | Random sessions matched on elapsed time |
| 21 | Confounders | Base rate of touching *something*; short-term reversal |
| 22 | Falsification | Reversal rate at Gann rays ≤ rate at placebo rays of the same density |
| 23 | Economic interpretation | Weak |
| 24 | Realistic with our data? | Mechanically yes; statistically fragile |
| 25 | Status | **SECONDARY CANDIDATE** (shortlist list F) |

#### GA-5 — Chart-drawn 45° angle

| # | Field | Specification |
|---|---|---|
| 1 | ID | GA-5 |
| 2 | Name | Visual 45° angle |
| 3 | Gann claim | Drawn 45° lines on a chart |
| 4 | Math | Slope in pixels; depends on chart aspect ratio |
| 5 | Data | A chart image |
| 6 | Anchor | Chosen by eye |
| 7 | Price transform | Axis scaling of the chart |
| 8 | Time transform | Axis scaling of the chart |
| 9 | Geometry | Pixel geometry |
| 10 | Event | Visual touch |
| 11 | Outcome | Visual |
| 12 | Direction | Interpretive |
| 13 | Scope | Single chart |
| 14 | N100 EOD? | No |
| 15 | Assumptions | Aspect ratio is meaningful |
| 16 | Parameters | Aspect ratio, anchor, drawing |
| 17 | Theory vs choice | All [R] |
| 18 | DoF | Unbounded |
| 19 | Price-only control | n/a |
| 20 | Time-only control | n/a |
| 21 | Confounders | Hindsight |
| 22 | Falsification | None possible |
| 23 | Economic interpretation | None |
| 24 | Realistic with our data? | No |
| 25 | Status | **NOT TESTABLE** |

### 6.2 Price-time squaring

#### GS-1 — Price level = elapsed time count

| # | Field | Specification |
|---|---|---|
| 1 | ID | GS-1 |
| 2 | Name | Price level equals time count (incl. "square of a high/low") |
| 3 | Gann claim | C1/C9: when the price value equals the days elapsed (or a high of 144 → watch day 144), a turn is due |
| 4 | Math | Event when \|*P_t* − *u*·(*t* − *O*)\| ≤ τ, or *t* − *O* = *P_ext*/*u* |
| 5 | Data | Raw daily close |
| 6 | Anchor | Origin date or an extreme |
| 7 | Price transform | None (₹) — sometimes "decimal shifting" of large prices |
| 8 | Time transform | Calendar days |
| 9 | Geometry | Equality of a number of rupees and a number of days |
| 10 | Event | Equality within τ |
| 11 | Outcome | Turn incidence |
| 12 | Direction | Non-directional |
| 13 | Scope | Single-series |
| 14 | N100 EOD? | Mechanically |
| 15 | Assumptions | ₹ ≡ day |
| 16 | Parameters | *u*, decimal-shift rule, τ, anchor |
| 17 | Theory vs choice | *u* = 1 [T] in its original commodity setting; decimal shifting [R] |
| 18 | DoF | Decimal shifting makes any price map to any day |
| 19 | Price-only control | n/a |
| 20 | Time-only control | Random day counts |
| 21 | Confounders | Price level |
| 22 | Falsification | Not reachable: re-scaling rescues any failure |
| 23 | Economic interpretation | None |
| 24 | Realistic with our data? | No — 1:k splits move the "square" by *k*× |
| 25 | Status | **REJECTED BEFORE TESTING** |

#### GS-2 — Absolute price change = elapsed days ("square of the range")

| # | Field | Specification |
|---|---|---|
| 1 | ID | GS-2 |
| 2 | Name | Square of the range |
| 3 | Gann claim | C9: a range of *R* points is "squared" *R* days later |
| 4 | Math | Event at *t* − *O* = \|*P_high* − *P_low*\|/*u* |
| 5 | Data | Raw daily high/low |
| 6 | Anchor | End of the range swing (delayed-causal) |
| 7 | Price transform | Points (₹) |
| 8 | Time transform | Calendar days |
| 9 | Geometry | Range ↔ day count |
| 10 | Event | Day count reached, within τ |
| 11 | Outcome | Turn incidence |
| 12 | Direction | Non-directional |
| 13 | Scope | Single-series |
| 14 | N100 EOD? | Mechanically |
| 15 | Assumptions | ₹ ≡ day |
| 16 | Parameters | *u*, τ, range definition |
| 17 | Theory vs choice | *u* [T] only in the original market; otherwise [R] |
| 18 | DoF | *u* |
| 19 | Price-only control | n/a |
| 20 | Time-only control | Random day counts from the same pivot |
| 21 | Confounders | Price level; splits |
| 22 | Falsification | Not reachable without an exogenous *u* |
| 23 | Economic interpretation | None across stocks |
| 24 | Realistic with our data? | No |
| 25 | Status | **REJECTED BEFORE TESTING**. Its scale-free residue ("the range's own duration") is GT-2 |

#### GS-3 — Diffusive price-time square

| # | Field | Specification |
|---|---|---|
| 1 | ID | GS-3 |
| 2 | Name | Diffusive square |
| 3 | Gann claim | C1, reinterpreted: price and time are "in equilibrium" when displacement matches what elapsed time warrants |
| 4 | Math | *z_t* = \|*x_t* − *x_O*\| / (σ_ℓ(*O*)·√(*t* − *O*)); event when *z* first crosses 1 (or leaves [1 − τ, 1 + τ]) |
| 5 | Data | Daily close; trailing σ |
| 6 | Anchor | Causal pivot (confirmation-stamped) |
| 7 | Price transform | σ-normalized log |
| 8 | Time transform | √sessions |
| 9 | Geometry | Parabolic envelope *x_O* ± σ√Δ*T* |
| 10 | Event | Envelope crossing |
| 11 | Outcome | Forward signed change or turn incidence within *h* |
| 12 | Direction | Directional (continuation vs exhaustion — **the sign is not given by Gann**) |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | A random-walk scale is the right conversion — **this is the null model's own geometry** |
| 16 | Parameters | ℓ, pivot rule, threshold, τ, *h*, sign |
| 17 | Theory vs choice | Threshold "1" is privileged only by the random-walk model, not by Gann [R]; sign [R] |
| 18 | DoF | Moderate; the sign ambiguity doubles it |
| 19 | Price-only control | \|*x_t* − *x_O*\|/σ threshold with no √*T* |
| 20 | Time-only control | Δ*T* alone |
| 21 | Confounders | Momentum t-statistic (GS-3 *is* a momentum-since-pivot z-score); volatility regime |
| 22 | Falsification | No increment over a momentum-z control; placebo thresholds equally good |
| 23 | Economic interpretation | Yes, but as momentum strength, not Gann |
| 24 | Realistic with our data? | Yes |
| 25 | Status | **SECONDARY CANDIDATE** (low fidelity; useful as the control geometry for GA/GS constructs) |

#### GS-4 — Linear normalized square

| # | Field | Specification |
|---|---|---|
| 1 | ID | GS-4 |
| 2 | Name | Linear normalized square |
| 3 | Gann claim | C1 with a modern scale |
| 4 | Math | \|*x_t* − *x_O*\|/*s* = Δ*T* — **identical to the GA-2 1×1 ray** |
| 5–24 | Fields | As GA-2 with *n* = 1 |
| 25 | Status | **SECONDARY CANDIDATE — ≡ GA-2 (n = 1); counted once** |

#### GS-5 — Ratio square

| # | Field | Specification |
|---|---|---|
| 1 | ID | GS-5 |
| 2 | Name | Ratio square (price ratio equals time ratio) |
| 3 | Gann claim | C1/C3: a move is "square" with its predecessor when it has gone as far, relative to it, as it has lasted |
| 4 | Math | (*A_cur*/*A_prev*) = (*D_cur*/*D_prev*) ⇔ *A_cur*/*D_cur* = *A_prev*/*D_prev* ⇔ current rate = prior rate — **identical to touching the GA-3 ray** |
| 5–24 | Fields | As GA-3, touch variant |
| 25 | Status | **PRIMARY CANDIDATE — ≡ GA-3 (touch); counted once.** The equivalence is itself a finding: the only dimensionally valid "square" with a privileged 1 is a rate equality |

### 6.3 Time cycles / anniversaries

#### GT-1 — Pivot anniversary

| # | Field | Specification |
|---|---|---|
| 1 | ID | GT-1 |
| 2 | Name | Anniversary of a causal major pivot |
| 3 | Gann claim | C4: important highs/lows recur as turning times one year (and integer years) later |
| 4 | Math | For a major pivot at date *d_O*, confirmed at *d_O* + *k*: event window *W_n* = sessions with calendar date within ±*w* sessions of *d_O* + *n*·*Y*, where *Y* ∈ {365.25, 360} days and *n* ∈ {1, 2, …} |
| 5 | Data | Daily OHLC; trading calendar |
| 6 | Anchor | Major pivot: extremum over a trailing window *W* and confirmed with delay *k* |
| 7 | Price transform | None for the event (time only); outcome uses a scale-free transform |
| 8 | Time transform | **Calendar days** [T] |
| 9 | Geometry | Calendar distance |
| 10 | Event | Session inside *W_n* |
| 11 | Outcome | Non-directional: turn incidence (a new confirmed pivot whose pivot session lies in [*t*, *t* + *h*]) or scale-free activity (\|forward log change\|/σ_ℓ). Directional variant: signed against the direction since *d_O* |
| 12 | Direction | Non-directional primary |
| 13 | Scope | Per stock; anchors differ by stock |
| 14 | N100 EOD? | Yes (anniversaries from ~2011 onward; *n* ≥ 3 needs pivots ≥ 3 y old) |
| 15 | Assumptions | The pivot's calendar date carries forward information |
| 16 | Parameters | *Y*, *n* set, *W*, *k*, *w*, outcome definition, *h* |
| 17 | Theory vs choice | Calendar axis [T]; integer years [T]; *Y* [T?, two values]; *W*, *k* (Gann order set), *w*, *h*, outcome [R] |
| 18 | DoF | Low-moderate |
| 19 | Price-only control | n/a — the event carries no price condition. Condition instead on price state at *t* (momentum, σ, distance from pivot price) |
| 20 | Time-only control | **Placebo lags** (e.g. 300, 330, 400, 430 days — non-Gann) from the same pivot; **random-anchor anniversaries** (anniversary of a random non-pivot date of the same stock in the same calendar month) |
| 21 | Confounders | **Annual corporate calendar** (results season, AGM, dividend ex-dates recur yearly — no earnings calendar in store); fiscal-year effects; index reviews (Mar/Sep); expiry cycle; volatility seasonality |
| 22 | Falsification | Anniversary-window incidence ≤ placebo-lag incidence **and** ≤ random-anchor-anniversary incidence (the latter absorbs the stock's own annual calendar) |
| 23 | Economic interpretation | Possible (memory of reference dates) but largely confounded by annual reporting cycles |
| 24 | Realistic with our data? | Yes |
| 25 | Status | **PRIMARY CANDIDATE** |

#### GT-2 — Time symmetry

| # | Field | Specification |
|---|---|---|
| 1 | ID | GT-2 |
| 2 | Name | Equal-duration symmetry |
| 3 | Gann claim | C3: a move tends to last as long as the prior move; time balances |
| 4 | Math | Legs between confirmed pivots have durations *D_j*. For the current leg starting at *O*: event window = sessions *t* with \|(*t* − *O*) − *m*·*D*_{j−1}\| ≤ *w*, *m* ∈ {1} (primary) or {1/2, 1, 2} |
| 5 | Data | Daily high/low |
| 6 | Anchor | Two consecutive confirmed pivots |
| 7 | Price transform | None for the event |
| 8 | Time transform | Sessions or calendar days [T?] |
| 9 | Geometry | Duration equality |
| 10 | Event | Elapsed time reaches *m*·*D*_{j−1} (observable at *t* only if the current leg is still unconfirmed-ended at *t*) |
| 11 | Outcome | Turn incidence within *h*; or signed forward change against the leg |
| 12 | Direction | Non-directional primary |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | Consecutive leg durations are dependent beyond the base hazard |
| 16 | Parameters | Pivot rule / *k*, *m* set, *w*, *h*, time axis, outcome |
| 17 | Theory vs choice | *m* = 1 [T]; {1/2, 2} [T?]; everything else [R] |
| 18 | DoF | Low-moderate |
| 19 | Price-only control | Condition on leg amplitude-to-date in σ units |
| 20 | Time-only control | **Base hazard of leg termination as a function of elapsed time alone** (no reference to *D*_{j−1}); placebo multipliers (0.8, 1.25); *D* drawn from another stock's leg |
| 21 | Confounders | Duration dependence of swings in any autocorrelated series; volatility clustering (similar regimes → similar durations) |
| 22 | Falsification | Termination hazard at *m*·*D*_{j−1} does not exceed the elapsed-time-only hazard or the placebo-multiplier hazard |
| 23 | Economic interpretation | Weak-moderate (regime persistence) |
| 24 | Realistic with our data? | Yes |
| 25 | Status | **PRIMARY CANDIDATE** (shortlist alternate — it shares machinery and confounders with GO-2) |

#### GT-3 — Circle-division day counts

| # | Field | Specification |
|---|---|---|
| 1 | ID | GT-3 |
| 2 | Name | Division-of-the-circle counts from a pivot |
| 3 | Gann claim | C4: 45, 90, 120, 135, 180, 225, 240, 270, 315, 360 days from a pivot are turning times |
| 4 | Math | Event windows at *d_O* + *c* (± *w*), *c* ∈ 𝒞 (set above), calendar days |
| 5 | Data | Daily OHLC |
| 6 | Anchor | Causal major pivot |
| 7 | Price transform | None for the event |
| 8 | Time transform | Calendar days [T] |
| 9 | Geometry | Fixed counts |
| 10 | Event | Session in any window |
| 11 | Outcome | Turn incidence / scale-free activity |
| 12 | Direction | Non-directional |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | All counts are meaningful |
| 16 | Parameters | 𝒞, *w*, pivot rule, *h* |
| 17 | Theory vs choice | 𝒞 [T] but variable across sources [T?]; everything else [R] |
| 18 | DoF | **High coverage**: 10 windows of ±*w* in 360 days cover a large fraction of all sessions, so hits are near-guaranteed |
| 19 | Price-only control | Condition on price state |
| 20 | Time-only control | Placebo count sets of equal size and spacing (e.g. offset by 17 days) |
| 21 | Confounders | Quarterly results (~91 days ≈ 90); monthly expiry (~30); coverage base rate |
| 22 | Falsification | Gann count set ≤ placebo count sets of equal coverage |
| 23 | Economic interpretation | Weak; the 90 ≈ quarter confound is severe |
| 24 | Realistic with our data? | Yes mechanically |
| 25 | Status | **SECONDARY CANDIDATE** (list F) |

#### GT-4 — Fixed seasonal calendar dates

| # | Field | Specification |
|---|---|---|
| 1 | ID | GT-4 |
| 2 | Name | Seasonal dates |
| 3 | Gann claim | C5: dates near Mar 21, Jun 21, Sep 23, Dec 21 and their midpoints are turning times |
| 4 | Math | Event windows at fixed calendar dates ± *w* |
| 5 | Data | Daily OHLC |
| 6 | Anchor | Fixed calendar (causal) |
| 7 | Price transform | None |
| 8 | Time transform | Calendar |
| 9 | Geometry | Calendar |
| 10 | Event | Session in window |
| 11 | Outcome | Turn incidence / activity |
| 12 | Direction | Non-directional |
| 13 | Scope | **Identical for every stock** |
| 14 | N100 EOD? | Mechanically yes |
| 15 | Assumptions | Market-wide timing |
| 16 | Parameters | Date set, *w* |
| 17 | Theory vs choice | Dates [T?]; *w* [R] |
| 18 | DoF | Low, but only ~15 repetitions per date |
| 19 | Price-only control | n/a |
| 20 | Time-only control | Placebo date sets |
| 21 | Confounders | Quarter ends, fiscal year end (Mar 31), index reviews (late Mar / Sep), quarterly results season |
| 22 | Falsification | Placebo dates perform as well |
| 23 | Economic interpretation | None beyond fiscal calendar |
| 24 | Realistic with our data? | As an **index** claim only |
| 25 | Status | **DESCRIPTIVE ONLY on N100.** Fails the veneer test (§11): a common date applied to 100 stocks is one index event, not 100 stock-level observations. Belongs to Family C/D on the index |

#### GT-5 — Long master cycles

| # | Field | Specification |
|---|---|---|
| 1 | ID | GT-5 |
| 2 | Name | Master cycles (7/10/20/30/60-year) |
| 3 | Gann claim | C6 |
| 4 | Math | Phase within period *T_c* ≥ 7 y |
| 5 | Data | ≥ several periods of history |
| 6 | Anchor | Historical major pivots (pre-panel) |
| 7 | Price transform | Log |
| 8 | Time transform | Calendar years |
| 9 | Geometry | Periodic |
| 10 | Event | Phase |
| 11 | Outcome | Trend change |
| 12 | Direction | Mixed |
| 13 | Scope | Single-series |
| 14 | N100 EOD? | **No** — 15.5 y holds ≤ 2 repetitions of a 7-y cycle and < 1 of a 20-y cycle |
| 15 | Assumptions | Stationary periodicity |
| 16 | Parameters | Periods, anchors |
| 17 | Theory vs choice | Periods [T?] |
| 18 | DoF | n/a |
| 19 | Price-only control | n/a |
| 20 | Time-only control | Phase-randomized surrogate |
| 21 | Confounders | Macro regimes |
| 22 | Falsification | Not achievable with the sample |
| 23 | Economic interpretation | Weak |
| 24 | Realistic with our data? | No |
| 25 | Status | **NOT TESTABLE** |

#### GT-6 — Listing-date anniversaries

| # | Field | Specification |
|---|---|---|
| 1 | ID | GT-6 |
| 2 | Name | IPO / listing anniversaries |
| 3 | Gann claim | Birth dates of a security as time origin (practitioner extension of C4) |
| 4 | Math | Windows at listing date + *n*·*Y* |
| 5 | Data | `instrument_master.listing_date` (VARCHAR, unaudited) |
| 6 | Anchor | Listing date (causal) |
| 7 | Price transform | None |
| 8 | Time transform | Calendar |
| 9 | Geometry | Calendar |
| 10 | Event | Session in window |
| 11 | Outcome | Turn incidence / activity |
| 12 | Direction | Non-directional |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Partly (field quality unknown) |
| 15 | Assumptions | Listing date is a meaningful reference |
| 16 | Parameters | *Y*, *n*, *w* |
| 17 | Theory vs choice | Weakly [T?] |
| 18 | DoF | Low |
| 19 | Price-only control | n/a |
| 20 | Time-only control | Random-date anniversaries |
| 21 | Confounders | Firm age / time-of-life effects; annual reporting cycle; lock-up history (mostly outside the panel) |
| 22 | Falsification | Random-date anniversaries perform as well |
| 23 | Economic interpretation | Minimal |
| 24 | Realistic with our data? | Uncertain (field unaudited) |
| 25 | Status | **DESCRIPTIVE ONLY** |

#### GT-7 — Swing-duration recurrence

| # | Field | Specification |
|---|---|---|
| 1 | ID | GT-7 |
| 2 | Name | Recurrence of swing durations |
| 3 | Gann claim | C3: durations repeat |
| 4 | Math | Distribution of \|*D_j* − *D*_{j−1}\| vs a surrogate |
| 5 | Data | Daily high/low |
| 6 | Anchor | Consecutive pivots |
| 7 | Price transform | None |
| 8 | Time transform | Sessions |
| 9 | Geometry | Duration differences |
| 10 | Event | n/a (distributional) |
| 11 | Outcome | None forward-looking |
| 12 | Direction | n/a |
| 13 | Scope | Per stock / pooled |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | — |
| 16 | Parameters | Pivot rule |
| 17 | Theory vs choice | [R] |
| 18 | DoF | Low |
| 19 | Price-only control | n/a |
| 20 | Time-only control | Block-shuffled / phase-randomized surrogate series |
| 21 | Confounders | Volatility clustering |
| 22 | Falsification | Duration similarity no greater than in surrogates |
| 23 | Economic interpretation | Descriptive |
| 24 | Realistic with our data? | Yes |
| 25 | Status | **DESCRIPTIVE ONLY** (no forward outcome; GT-2 is its predictive form) |

### 6.4 Square of Nine

#### GN-1 — Square-of-Nine price levels

| # | Field | Specification |
|---|---|---|
| 1 | ID | GN-1 |
| 2 | Name | Square-of-Nine price levels |
| 3 | Gann claim | C8: from a pivot price, support/resistance lies at prices one "angle" around the spiral |
| 4 | Math | Standard numeric reading: *S_m* = (√*P_O* ± *m*·δ)², δ = 1/4 per 45°, 1/2 per 90°, 1 per 180°, 2 per 360° |
| 5 | Data | **Raw** daily close/high/low |
| 6 | Anchor | Causal pivot price |
| 7 | Price transform | √ of the **rupee level** |
| 8 | Time transform | None |
| 9 | Geometry | Quadratic price ladder |
| 10 | Event | Price within τ of some *S_m* |
| 11 | Outcome | Reversal within *h* |
| 12 | Direction | Directional (away from level) |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Mechanically, only on raw prices and only on spans with no CA event |
| 15 | Assumptions | Rupee levels (after √) carry information; price unit (₹ vs paise) and decimal shifting are natural |
| 16 | Parameters | δ set, *m* range, decimal-shift rule, τ, pivot rule, *h* |
| 17 | Theory vs choice | Angle steps [T]; decimal-shift / unit [R]; everything else [R] |
| 18 | DoF | **High**: √(*k*·*P*) = √*k*·√*P*, so the ladder is not scale-invariant — the unit choice moves every level |
| 19 | Price-only control | **It is already price-only**: placebo ladders (δ = 0.2, 0.3) and random level sets of equal density |
| 20 | Time-only control | n/a |
| 21 | Confounders | Round-number clustering; short-term reversal; touch base rate |
| 22 | Falsification | Reversal at Sq9 levels ≤ placebo ladders of equal density |
| 23 | Economic interpretation | Only as a trader-behaviour / focal-price claim |
| 24 | Realistic with our data? | Poor: CA-fatal across 112 bonus/split events plus unadjusted spin-offs; every event resets the ladder |
| 25 | Status | **SECONDARY CANDIDATE, heavily constrained** (lists E, F) |

#### GN-2 — Square-of-Nine time counts

| # | Field | Specification |
|---|---|---|
| 1 | ID | GN-2 |
| 2 | Name | Square-of-Nine time counts |
| 3 | Gann claim | C8: elapsed days landing on cardinal/ordinal spiral positions are turning times |
| 4 | Math | Event when √(Δ*T* + *c₀*) is within τ of a multiple of δ (δ = 1/4 for 45° steps), where *c₀* is the spiral start value |
| 5 | Data | Daily OHLC, calendar |
| 6 | Anchor | Causal pivot |
| 7 | Price transform | None |
| 8 | Time transform | √(calendar days) |
| 9 | Geometry | Spiral positions of day counts |
| 10 | Event | Session in window |
| 11 | Outcome | Turn incidence / activity |
| 12 | Direction | Non-directional |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | The spiral mapping of days is natural |
| 16 | Parameters | *c₀*, δ, τ, time axis, pivot rule |
| 17 | Theory vs choice | δ [T]; *c₀* [T?]; everything else [R] |
| 18 | DoF | Moderate; window density falls with Δ*T* (spacing ∝ √Δ*T*), so the base rate varies over time |
| 19 | Price-only control | Condition on price state |
| 20 | Time-only control | Placebo δ; time-matched random windows with the same density profile |
| 21 | Confounders | Elapsed-time hazard; overlap with GT-3 counts (90, 180, 360 lie near cardinal positions) |
| 22 | Falsification | Incidence ≤ density-matched placebo |
| 23 | Economic interpretation | None |
| 24 | Realistic with our data? | Yes mechanically; CA-immune |
| 25 | Status | **SECONDARY CANDIDATE** (list F) |

#### GN-3 — Square-of-Nine price-time coincidence

| # | Field | Specification |
|---|---|---|
| 1 | ID | GN-3 |
| 2 | Name | Price and date on the same spiral angle |
| 3 | Gann claim | C8: when price and time sit on the same angle, a turn is due |
| 4 | Math | Angle(√*P_t*) ≡ Angle(√Δ*T*) within τ |
| 5 | Data | Raw price; calendar |
| 6 | Anchor | Pivot |
| 7 | Price transform | √ rupee level |
| 8 | Time transform | √ days |
| 9 | Geometry | Equates a rupee-derived angle to a day-derived angle |
| 10 | Event | Coincidence |
| 11 | Outcome | Turn incidence |
| 12 | Direction | Non-directional |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Mechanically |
| 15 | Assumptions | Rupees ≡ days |
| 16 | Parameters | Unit, τ, *c₀* |
| 17 | Theory vs choice | Equivalence [T]; unit [R] |
| 18 | DoF | Unit choice re-maps every coincidence |
| 19 | Price-only control | n/a |
| 20 | Time-only control | n/a |
| 21 | Confounders | — |
| 22 | Falsification | Not reachable |
| 23 | Economic interpretation | None |
| 24 | Realistic with our data? | No |
| 25 | Status | **REJECTED BEFORE TESTING** (dimensionally invalid; CA-fatal) |

#### GN-4 — Traditional wheel / overlay readings

| # | Field | Specification |
|---|---|---|
| 1 | ID | GN-4 |
| 2 | Name | Wheel, cardinal-cross and overlay readings |
| 3 | Gann claim | C8 as practised: reading the diagram, overlays, cross placements |
| 4 | Math | None supplied |
| 5 | Data | Diagram |
| 6 | Anchor | Discretionary |
| 7 | Price transform | Discretionary |
| 8 | Time transform | Discretionary |
| 9 | Geometry | Diagrammatic |
| 10 | Event | Interpretation |
| 11 | Outcome | Interpretation |
| 12 | Direction | Interpretive |
| 13 | Scope | — |
| 14 | N100 EOD? | No |
| 15 | Assumptions | — |
| 16 | Parameters | Unbounded |
| 17 | Theory vs choice | [R] |
| 18 | DoF | Unbounded |
| 19 | Price-only control | n/a |
| 20 | Time-only control | n/a |
| 21 | Confounders | Hindsight |
| 22 | Falsification | None |
| 23 | Economic interpretation | None |
| 24 | Realistic with our data? | No |
| 25 | Status | **NOT TESTABLE** |

### 6.5 Other Gann constructs

#### GO-1 — Range-division retracement

| # | Field | Specification |
|---|---|---|
| 1 | ID | GO-1 |
| 2 | Name | Eighths / 50% retracement |
| 3 | Gann claim | C7 |
| 4 | Math | For the completed leg (*x*_{O'} → *x_O*), retracement fraction *f_t* = (*x_O* − *x_t*)/(*x_O* − *x*_{O'}); event when *f_t* reaches *r* ∈ {1/8 … 7/8} (primary *r* = 1/2) within τ |
| 5 | Data | Daily OHLC |
| 6 | Anchor | Two confirmed pivots |
| 7 | Price transform | Log or arithmetic fraction [T?] (not identical) |
| 8 | Time transform | None |
| 9 | Geometry | Price : price |
| 10 | Event | Reach of *r* |
| 11 | Outcome | Reversal (resumption of the leg) within *h* |
| 12 | Direction | Directional |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | Fractions are focal |
| 16 | Parameters | *r* set, τ, log vs arithmetic, pivot rule, *h* |
| 17 | Theory vs choice | 1/2 [T]; eighths [T]; everything else [R] |
| 18 | DoF | Moderate |
| 19 | Price-only control | **It is price-only**: placebo fractions (0.3, 0.45, 0.55, 0.7) |
| 20 | Time-only control | n/a |
| 21 | Confounders | Short-term reversal; Fibonacci-level folklore competing for the same levels |
| 22 | Falsification | Resumption at *r* = 1/2 ≤ at placebo fractions |
| 23 | Economic interpretation | Weak-moderate (focal points) |
| 24 | Realistic with our data? | Yes |
| 25 | Status | **SECONDARY CANDIDATE**. Not price × time — it is the natural **price-only control** for GO-2's price leg |

#### GO-2 — Overbalance (time and price)

| # | Field | Specification |
|---|---|---|
| 1 | ID | GO-2 |
| 2 | Name | Time overbalance (with price overbalance as nested control) |
| 3 | Gann claim | C3: "when time overbalances — a reaction runs longer than the largest previous reaction in the trend — the trend has changed"; the price analogue for depth |
| 4 | Math | See §17.1 |
| 5 | Data | Daily high/low/close |
| 6 | Anchor | Confirmed pivots defining the trend and its completed corrections |
| 7 | Price transform | Log depth (price : price) |
| 8 | Time transform | Sessions or calendar days [T?] |
| 9 | Geometry | Ratio of the current correction's duration (depth) to the maximum prior correction's duration (depth) in the same trend |
| 10 | Event | First session at which the current correction's elapsed duration exceeds the maximum prior correction duration, while the trend is still unbroken |
| 11 | Outcome | Signed forward change against the trend over *h*; or trend-state flip incidence within *h* |
| 12 | Direction | Directional relative to the trend |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | A mechanized trend with ≥ 1 completed correction exists; corrections are comparable within a trend |
| 16 | Parameters | Pivot order *k*, trend rule, minimum prior corrections, time axis, *h*, outcome |
| 17 | Theory vs choice | "Exceeds the largest prior" [T]; *k* ∈ Gann swing-chart orders [T set]; trend rule, minimum count, *h*, outcome [R]; time axis [T?] |
| 18 | DoF | Low-moderate |
| 19 | Price-only control | **Price overbalance**: depth exceeds the largest prior correction depth (and GO-1 retracement level) |
| 20 | Time-only control | Elapsed correction duration alone (hazard curve), with no reference to the stock's own prior maximum; **shuffled-history control** (maximum prior duration drawn from another stock's trend) |
| 21 | Confounders | Trend exhaustion; momentum decay; volatility regime shifts; mechanical correlation between long corrections and trend breaks |
| 22 | Falsification | See §17.1 |
| 23 | Economic interpretation | Yes: loss of trend control measured against the stock's own precedent |
| 24 | Realistic with our data? | Yes; time leg is CA-immune |
| 25 | Status | **PRIMARY CANDIDATE** |

#### GO-3 — Round-number / natural price levels

| # | Field | Specification |
|---|---|---|
| 1 | ID | GO-3 |
| 2 | Name | Round numbers |
| 3 | Gann claim | Natural resistance at round prices (practitioner overlap) |
| 4 | Math | Levels at multiples of 10^*j* ₹ |
| 5 | Data | Raw price |
| 6 | Anchor | None |
| 7 | Price transform | ₹ level |
| 8 | Time transform | None |
| 9 | Geometry | Level grid |
| 10 | Event | Touch |
| 11 | Outcome | Reversal |
| 12 | Direction | Directional |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Mechanically (raw) |
| 15 | Assumptions | Focal-price behaviour |
| 16 | Parameters | Grid, τ |
| 17 | Theory vs choice | [R] |
| 18 | DoF | Moderate |
| 19 | Price-only control | Placebo grids |
| 20 | Time-only control | n/a |
| 21 | Confounders | Price clustering (a known microstructure effect, not Gann) |
| 22 | Falsification | Placebo grids equally good |
| 23 | Economic interpretation | Microstructure, not Gann |
| 24 | Realistic with our data? | CA-fatal |
| 25 | Status | **DESCRIPTIVE ONLY** (not Gann-specific; level-based) |

#### GO-4 — Planetary / astrological time

| # | Field | Specification |
|---|---|---|
| 1 | ID | GO-4 |
| 2 | Name | Astrological timing |
| 3 | Gann claim | C10 |
| 4 | Math | Ephemeris-derived dates |
| 5 | Data | External ephemeris (not in store) |
| 6 | Anchor | Astronomical |
| 7 | Price transform | — |
| 8 | Time transform | Astronomical |
| 9 | Geometry | Aspect angles |
| 10 | Event | Aspects |
| 11 | Outcome | Turns |
| 12 | Direction | Interpretive |
| 13 | Scope | Market-wide |
| 14 | N100 EOD? | No data; also fails the veneer test |
| 15 | Assumptions | No mechanism |
| 16 | Parameters | Body/aspect sets (vast) |
| 17 | Theory vs choice | [R] in practice |
| 18 | DoF | Unbounded |
| 19 | Price-only control | n/a |
| 20 | Time-only control | Placebo ephemerides |
| 21 | Confounders | Calendar |
| 22 | Falsification | Degenerate under the multiplicity |
| 23 | Economic interpretation | None |
| 24 | Realistic with our data? | No |
| 25 | Status | **REJECTED BEFORE TESTING** |

#### GO-5 — Gann swing-chart pivot rule (auxiliary)

| # | Field | Specification |
|---|---|---|
| 1 | ID | GO-5 |
| 2 | Name | Swing-chart pivot generator |
| 3 | Gann claim | Trend and pivots are defined by *k*-day swing charts (*k* ∈ {1, 2, 3}) |
| 4 | Math | Up-swing turns down when *k* consecutive sessions make lower highs (mirror for up); pivot = extreme of the finished swing, **stamped at the completing session** |
| 5 | Data | Daily high/low |
| 6 | Anchor | Generates anchors |
| 7 | Price transform | Highs/lows (scale-free ordering; CA-safe if no ex-date inside the comparison) |
| 8 | Time transform | Sessions |
| 9 | Geometry | Order statistics |
| 10 | Event | n/a |
| 11 | Outcome | n/a |
| 12 | Direction | n/a |
| 13 | Scope | Per stock |
| 14 | N100 EOD? | Yes |
| 15 | Assumptions | Inside/outside-day handling declared |
| 16 | Parameters | *k*; inside/outside-day rule |
| 17 | Theory vs choice | *k* set [T]; inside/outside rule [R] |
| 18 | DoF | Small |
| 19–22 | Controls / falsification | n/a (not a hypothesis) |
| 23 | Economic interpretation | n/a |
| 24 | Realistic with our data? | Yes |
| 25 | Status | **DESCRIPTIVE ONLY — auxiliary definition** used by GA-3, GS-5, GT-1/2/3, GN-2, GO-1, GO-2. Its *k* multiplies every consumer's *m* |

---

## 7. Gann angles — testable meaning for modern equity data

| Ratio | Slope (per session) | Price unit | Time unit | Origin | Meaning under a data-derived scale *s* | Meaning under self-scaling ρ |
|---|---|---|---|---|---|---|
| 1×1 | *s* | log price | session | Confirmed pivot | "one *s* per session" — arbitrary constant *k* inside *s* | **Same rate as the prior leg** (privileged) |
| 2×1 | 2*s* | log | session | Pivot | Twice an arbitrary constant | Twice the prior rate |
| 1×2 | *s*/2 | log | session | Pivot | Half | Half the prior rate |
| 4×1, 1×4, 8×1, 1×8, 3×1, 1×3 | *n*·*s* | log | session | Pivot | Grid points | Rate multiples — **only 1 is claim-privileged**; others are secondary |

**Touching / crossing / deviating** (each is a declared rule, not a chart reading):
- **cross:** close on the far side of *L*(*t*) after being on the near side at *t* − 1;
- **touch:** \|*x_t* − *L*(*t*)\| ≤ τ·σ_ℓ (τ is dimensionless because it is σ-scaled) without a close beyond;
- **hold:** *N* consecutive closes on the near side;
- **deviation:** (*x_t* − *L*(*t*))/σ_ℓ as a continuous state variable for ranking (GX-2).

**Forward outcome:** forward log change over *h* sessions signed by the ray's direction, or turn
incidence (§13.3), measured strictly after the event session.

**Researcher DoF per angle construct:** scale family (σ / ATR / fixed-% / self), lookback ℓ, *k*,
ray set, event type, τ, *N*, *h*, outcome, arithmetic vs log, time axis.

**Canonical ratios after normalization.** They keep their meaning only as **multiples of a
like-dimensioned reference rate** (self-scaling). Under σ/ATR scaling they are an arbitrary grid,
and a visually drawn angle has no statistical meaning at all (GA-5).

---

## 8. Price-time squaring — formulations compared

| Formulation | What is tested | Correspondence to Gann | Arbitrary choices introduced | Catalogue |
|---|---|---|---|---|
| Absolute price change vs elapsed days | ₹ moved = days elapsed | Literal C1/C9 | Conversion *u*, decimal shifting | GS-2 **R** |
| Price level vs calendar time | ₹ level = day count | Literal "square of a high/low" | *u*, decimal shifting | GS-1 **R** |
| Percentage change vs elapsed days | % moved = *q*·days | Loose | *q* (no theory value) | ≡ GA-2 fixed-% scale **S** |
| Log change vs elapsed days | log moved = *q*·days | Loose | *q* | ≡ GA-2 **S** |
| Normalized displacement vs normalized time (linear) | \|Δ*x*\|/σ = Δ*T* | Modern restatement | *k* in σ, ℓ | GS-4 ≡ GA-2 **S** |
| Normalized displacement vs √time | \|Δ*x*\|/(σ√Δ*T*) = 1 | **Not Gann** — random-walk geometry | ℓ, sign | GS-3 **S** |
| Price ratio vs time ratio to the prior leg | *A_cur*/*A_prev* = *D_cur*/*D_prev* | Faithful to "balance" | Leg definition, τ | GS-5 ≡ GA-3 **P** |
| Price magnitude vs elapsed time, same leg (rate = 1 in units) | Needs *c* | Literal | *c* | → GS-2 **R** |

**Conclusion:** the only squaring statement that is dimensionally valid, has a claim-privileged
constant, and is scale-free across stocks is the **ratio square** (GS-5), which is mathematically
the self-scaled 1×1 (GA-3).

---

## 9. Time cycles / anniversaries — precise definitions and separation from generic effects

A **cycle**, for this programme, is a claim that a turning-point hazard (or scale-free activity)
is elevated at a **specified elapsed time from a specified causal anchor**, relative to the same
stock's hazard at matched non-specified elapsed times.

| Claim type | Construct | Anchor | Pinned time | How it differs from generic effects |
|---|---|---|---|---|
| Equal intervals | GT-2 | Prior leg | *D*_{j−1} (stock's own) | Generic duration dependence is the time-only control (hazard vs elapsed time without *D*_{j−1}) |
| Multiples of prior intervals | GT-2 variant (*m* ∈ {1/2, 2}) | Prior leg | *m*·*D*_{j−1} | Placebo multipliers 0.8 / 1.25 |
| Move-duration recurrence | GT-7 | Legs | none (distributional) | Surrogate series preserving autocorrelation |
| Anniversaries | GT-1 | Major pivot | *n*·*Y* calendar | Random-anchor anniversaries absorb the stock's annual corporate calendar; placebo lags absorb elapsed-time hazard |
| Circle divisions | GT-3 | Major pivot | 45 … 360 days | Equal-coverage placebo sets |
| Time symmetry around a pivot | GT-2 (mirror form: time from prior pivot to *O* equals time from *O* to the next) | *O* | *D*_{j−1} | As GT-2 |
| Fixed seasonal | GT-4 | Calendar | Fixed dates | **Is** seasonality — descriptive only on N100 |

**Generic seasonality** (month-of-year, expiry-week, results season) and **autocorrelation**
(return or volatility persistence) are **controls**, not Gann effects. A spectral surrogate is
mandatory for any periodicity claim — the Family D rule: "a cycle family without a spectral null
will find cycles in noise".

---

## 10. Square of Nine — assessment

| Question | Answer |
|---|---|
| **A) Genuinely testable with N100 EOD?** | **Only the time-count reading (GN-2)** — scale-free in price, CA-immune, machine-definable once *c₀*, δ, τ are declared |
| **B) Testable only after substantial arbitrary mapping?** | **The price-level reading (GN-1)**. It needs a price unit (₹ vs paise), a decimal-shifting rule for high-priced stocks, raw prices, and exclusion of every CA-affected span. √ is not scale-invariant, so every unit choice produces a different hypothesis |
| **C) Not meaningfully testable?** | **The diagram as a whole (GN-4)** and **price-time coincidence (GN-3)**, which equates rupees and days |
| Is the diagram a statistical model? | **No.** It is a lookup device that becomes a model only once the mapping, anchor, tolerance and outcome are fixed in writing |
| Separately catalogued numeric relationships | GN-1 (price ladder (√*P_O* ± *m*δ)²), GN-2 (√-day positions). Both are **density-varying** event sets, so placebo sets must match density, not count |

The CA verdict from §14 applies to GN-1 without re-derivation: **no price basis rescues a
rupee-level ladder.**

---

## 11. Cross-sectional N100 formulations

### 11.1 The veneer test (applied to every cross-sectional construct)

A construct is admissible as **Family F** only if **all** hold:

1. **Own-path statistic** — computed from the stock's own price path (with a common market input
   allowed only as a declared residualization).
2. **Own outcome** — the same stock's forward behaviour (absolute, or relative to the N100
   cross-section).
3. **Single-stock meaning** — the claim is meaningful for one stock in isolation.
4. **Not a common event** — it is not a single date or index-level configuration applied identically
   to all stocks.

Constructs failing (4) are **index claims in disguise**: using 100 names to buy √*n* for them is
invalid under the CB-N50 rule (CLAUDE.md), ruling §7 ("no cross-sectional rank-IC manufactured by
applying an index rule to the equity universe"), and ruling #3 §4.

### 11.2 Architectures

| ID | Question | Statistical unit | Dependence structure | Veneer test | Status |
|---|---|---|---|---|---|
| **GX-1** | Does a stock entering a price-time configuration predict its **own** forward outcome? | **Stock-event** (one event per stock per leg/pivot, first occurrence) | Overlapping horizons within a stock; **same-date clustering across stocks** — errors clustered by date, and effective *n* nearer the number of distinct event dates than the event count | Pass (GA-3, GO-2, GT-1, GT-2, GT-3, GN-2 anchors are stock-specific) | **Architecture, P-compatible** |
| **GX-2** | Does a per-stock continuous price-time **state** (e.g. deviation from the self-scaled 1×1, time-overbalance ratio τ/*D*\*) rank the cross-section of forward returns? | **Formation date × stock**; statistic = cross-sectional rank IC per formation date; test on the IC time series | Overlapping horizons → serial correlation in the IC series (Newey–West or non-overlapping formations) | Pass if the state is own-path | **Architecture, P-compatible (Family F native)**. Null per the Family F definition: circular shift on the formation axis + same-universe random-rank |
| **GX-3** | Do many stocks reaching configurations **simultaneously** predict the **index**? | Date (one observation per session) | Single index path | **Fail**: the outcome is an index move and the configuration count is an index statistic | **R for Family F**. Admissible only as a Family C/D index hypothesis with its own `per_trade_pnl` RFA |
| **GX-4** | Are relationships universal (common parameters) or stock-specific? | Stock | Heterogeneity across ~198 entities | n/a (secondary analysis) | **D**. Stock-specific fitting multiplies *m* by the number of stocks |

### 11.3 Specific cross-sectional points

- **Synchronicity is a confounder, not a feature.** When many stocks hit a configuration on the
  same date (common anniversaries after a market-wide pivot, e.g. March 2020), the "effect" is a
  market factor. Every GX-1/GX-2 test needs either market-residualized outcomes or a same-date
  random-rank null.
- **Normalization makes comparability possible only for scale-free constructs.** Rank statistics
  (GX-2) remove residual level differences but cannot rescue a level-based construct (GN-1, GO-3).
- **Universality.** Theory-pinned constants (1×1 under self-scaling, one year, "exceeds the largest
  prior") are universal by construction. Any stock-specific constant is fitted, not theoretical.
- **Sector conditioning is unavailable.** No PIT sector-constituent table exists (C2-A6 recorded
  "NOT PIT — UNUSABLE"; DATA_STORE_MAP §9 notes sector membership is not PIT-tabled). A present-day
  sector map across 15 years is look-ahead. **Sector-neutral and sector-conditioned designs are
  excluded by substrate.**

---

## 12. Controls

### 12.1 Control menu (definitions)

| Control | Definition | Guards against |
|---|---|---|
| **Price-only** | Same event rule with the time condition removed (horizontal level, depth-only overbalance, retracement fraction) | "Gann effect" = price-level / reversal behaviour |
| **Time-only** | Same elapsed-time structure with the Gann-specific reference removed (hazard as a function of elapsed time; placebo lags / multipliers / counts of equal coverage) | Generic duration dependence; calendar coverage base rates |
| **Volatility / scale** | Condition on σ_ℓ, change in σ between legs, and absolute displacement in σ units | Volatility clustering; regime shifts |
| **Randomized anchor** | Replace each causal pivot by a random causal date of the same stock, matched on calendar month and prior σ | Anchor-free calendar effects; the stock's own annual corporate calendar |
| **Matched event** | Match event sessions to non-event sessions on momentum (e.g. trailing 21/63/252-session log change), σ, distance from running high, elapsed time since pivot, calendar month, and N100 tenure | Momentum, 52-week-high effect, reversal, trend exhaustion, time-of-life |
| **Shuffled history** | Replace the stock's own reference (ρ, *D*\*, *D*_{j−1}) with one drawn from another stock at a similar date | Whether the stock's own history matters at all (the core Gann claim) |
| **Placebo geometry** | Non-Gann ratios (0.8, 1.25), fractions (0.3, 0.45, 0.55, 0.7), lags (300, 330, 400, 430 d), δ (0.2, 0.3) | Coverage / density artefacts |
| **Spectral surrogate** | Phase-randomized series preserving the power spectrum | Spurious periodicity |
| **Formation-axis circular shift / same-date random rank** | Per the Family F definition | Serial structure; market-wide synchronous events |

### 12.2 The standard every serious candidate must meet

The claim tested is never "Gann correlates with returns". It is **incremental**:

> outcome ~ controls (price-only + time-only + σ + momentum + calendar) **+ Gann indicator**

and the Gann term must be non-zero in the pre-registered direction, **and** beat its placebo
geometry.

### 12.3 Confounder register

| Confounder | Constructs most exposed | Measurable in store? |
|---|---|---|
| Momentum (1–12 month) | GA-2, GA-3, GS-3, GO-2 | Yes (price) |
| Short-term reversal | GA-4, GO-1, GN-1 | Yes |
| Volatility clustering | GT-2, GT-7, GS-3 | Yes |
| Trend exhaustion / 52-week-high effect | GA-3, GO-2 | Yes |
| Time-of-life / firm age, N100 tenure | GT-6, GT-1 | Partly (listing date unaudited; tenure yes) |
| **Annual results / AGM / dividend seasonality** | **GT-1, GT-3** | **No earnings calendar**; dividend dates only partially (CA table sparse pre-2022) → **controlled indirectly** via random-anchor anniversaries and calendar-month matching |
| Quarterly results (~91 d) | GT-3 (90-day count) | No |
| Monthly derivatives expiry | GT-3, GN-2 | Derivable from calendar rules |
| Index reviews (Mar/Sep) | GT-4, GT-1 | Yes (membership dates) |
| Price-level / round-number clustering | GN-1, GO-3, GS-1 | Yes (raw) |
| Autocorrelation | All | Yes |
| Generic swing behaviour | All pivot-based | Yes (shuffled history) |

---

## 13. Causality / look-ahead risks

### 13.1 Rules every construct inherits

1. **Pivot stamping.** A pivot at *i* exists only from its confirmation session (*i* + *k*, or the
   swing-chart completion session). All rays, rates, durations and anniversaries are computed from
   that session onward.
2. **Scales strictly prior.** σ_ℓ and ATR_ℓ use data ending at *t* − 1 relative to the session at
   which they enter a statistic, and are frozen at the anchor when the theory says so (ray slope at
   *O*).
3. **Events at the close.** An EOD event is known at the close of *t*. Its outcome window begins
   **strictly after** *t*. Close(*t*) → close(*t* + *h*) is information-valid but not executable;
   open(*t* + 1) is executable. The start convention is a declared DoF.
4. **Membership at *t*.** An event is eligible only if the stock is an N100 member at *t*
   (`n100_membership`, half-open intervals).
5. **No repainting.** Zig-zag / percentage-filter pivots that revise past pivots are inadmissible
   unless every revision is time-stamped and only the then-current version is used.
6. **Left censoring.** Running extrema and "all-time" references begin 2010-01-04 (or first trade).

### 13.2 Construct-specific look-ahead traps

| Construct | Trap | Required statement |
|---|---|---|
| GT-1, GT-3 | Choosing "major" pivots with full-sample knowledge (e.g. the COVID low) | Major = trailing-window extremum confirmed with delay; no hindsight list |
| GA-3, GS-5, GT-2, GO-2 | Using the leg that ends at an unconfirmed pivot | Only confirmed legs define ρ, *D*, *D*\* |
| GO-2 | Knowing the trend "ended" when classifying a correction | Trend state evaluated with data ≤ *t* only |
| GN-1 | Backward-adjusted levels | Adjusted levels depend on future events (§14) |
| All with adjusted prices | View rewrites history when factors are ingested | Pin the factor-table snapshot by hash |

### 13.3 Event–outcome coupling

When the outcome is "turn incidence", the turn must be a pivot whose **confirmation** lies in
(*t*, *t* + *h* + *k*] and whose pivot session lies in [*t* + 1, *t* + *h*]. It must not share the
pivot that defined the event. Otherwise the outcome is partly determined by the event definition.

---

## 14. Corporate-action implications

Substrate facts (feasibility audit §E, §G):
- 112 bonus/split events inside membership (all factored);
- backward-adjusted **levels** carry look-ahead, and the view rewrites history on ingest;
- spin-offs (ITC, SIEMENS, Tata Motors, HINDUNILVR, VEDL; RELIANCE→JIOFIN absent from the store),
  rights issues (4) and special dividends (10) are **unadjusted in every basis**;
- ordinary dividends are never adjusted;
- the CA table cannot enumerate non-split events before ~2022.

| Construct class | Requires | Vulnerability |
|---|---|---|
| **Absolute level** (GA-1, GS-1, GS-2, GN-1, GN-3, GO-3) | Raw as-traded price | **Intrinsic.** Raw breaks the geometry at every ex-date; adjusted makes the level a function of the future; non-ratio events break both. **No basis rescues them** |
| **Log displacement / rates / ratios** (GA-2, GA-3, GS-3, GS-4, GS-5, GO-1, GO-2 price leg) | As-of-*t* causal adjustment (only factors with ex-date ≤ *t*), **or** raw with legs spanning any ex-date excluded | Survive bonus/split; **still break at unadjusted non-ratio events** → exclude legs/rays spanning an externally enumerated spin-off, rights issue or special dividend |
| **Durations / calendar distances** (GT-1, GT-2, GT-3, GN-2, GO-2 time leg) | Any basis for pivot detection | Time is immune. Pivot **detection** can still be fooled by an unadjusted price gap creating a spurious pivot → same exclusion windows around non-ratio events |
| **Ticker changes** | Entity-resolved series (`symbol_entity_intervals`) | Safe for members (0 multi-entity symbols). The Tata Motors demerger falls inside the TATAMOTORS label before the TMPV rename |
| **Dividends** | Declared basis: price path vs value | Ex-dividend gaps look like small down-moves and can trigger ray breaks, depth overbalance or retracement touches. Material only if a construct's tolerance is comparable to a dividend yield |

**Decision not taken here:** raw with exclusions vs as-of-*t* adjusted. Both are admissible for
scale-free constructs. Backward-adjusted levels are inadmissible for any level-reading construct.

---

## 15. Multiplicity map

### 15.1 Dimensions

| Dimension | A theory-mandated | B pre-specifiable researcher choice | C exploratory DoF |
|---|---|---|---|
| Gann construct | — | The pre-registered slate (§17) | Anything beyond the slate |
| Anchor / pivot rule | Swing-chart order *k* ∈ {1, 2, 3} | One *k*, or all three declared | Zig-zag %, fractal widths |
| Major-pivot significance | — | Trailing window *W* | Amplitude filters |
| Price transformation | — | Log (disclosed departure from arithmetic) | Arithmetic, %, ATR |
| Time transformation | Calendar for anniversaries/counts | Sessions vs calendar for rates/durations | Both |
| Year length | {365.25, 360} — theory-internal | One declared | — |
| Scale (angles) | Self-scaling (rate : rate) | ρ source: prior leg vs mean of prior legs | σ / ATR / fixed-% families |
| Angle / ratio set | 1×1 (under self-scaling) | Fan {1/2, 2} as secondary | Full 9-ray fan |
| Count set | "Exceeds the largest prior"; one year; *m* = 1 symmetry | {1/2, 2}; integer years 1–3 | Circle divisions; Sq9 δ |
| Tolerance τ / window *w* | — | One value, σ-scaled | Grids |
| Horizon *h* | — | 1–3 declared values | Grids |
| Event definition | — | Break vs touch (one primary) | Hold-*N* variants |
| Outcome | — | Signed change vs turn incidence (one primary) | Activity measures |
| Direction legs | — | Pooled up/down or separate | — |
| Stock | — | Pooled universal parameters | Stock-specific fitting (× ~198) |
| Aggregation | — | GX-1 or GX-2 (one primary) | Both |
| Price basis | — | Raw-with-exclusions vs as-of-*t* | Backward-adjusted (inadmissible for levels) |

### 15.2 Equivalence classes (count once)

- GS-5 ≡ GA-3 (touch)
- GS-4 ≡ GA-2 (*n* = 1)
- GO-1 serves as GO-2's price-only control and is not a separate test when used that way
- GT-7 is the non-predictive form of GT-2
- GO-5 is an auxiliary definition, not a test — but its *k* multiplies every consumer

### 15.3 Worked counts — **ILLUSTRATIVE ENUMERATIONS, NOT SELECTIONS**

The values in braces are placeholders that show the arithmetic. None is chosen.

| Construct | Formula | Illustrative enumeration | *m* |
|---|---|---|---:|
| GO-2 | *k* × axis × *h* × outcome × legs | {1,2,3} × {sess, cal} × {3 values} × {2} × {pooled} | 36 |
| GT-1 | *k* × *Y* × *W* × *w* × outcome × *n*-pooling | {2} × {365.25, 360} × {1} × {2} × {2} × {pooled} | 16 |
| GA-3 | *k* × ρ source × event × *h* × outcome | {2} × {2} × {break, touch} × {3} × {2} | 48 |
| GT-2 | *k* × *m*-set × axis × *w* × outcome | {2} × {1 or {½,1,2}} × {2} × {2} × {2} | 16–48 |
| **Slate of 3 (GO-2, GT-1, GA-3)** | sum | | **100** |
| Slate + GT-2 | sum | | **116–148** |
| Unconstrained angle family (GA-2/GA-4) | rays × scales × ℓ × *k* × τ × event × *h* | 9 × 3 × 3 × 3 × 3 × 2 × 3 | **4,374** |
| + stock-specific fitting | × ~198 entities | | ~866,000 |

**Qualitative consequence (arithmetic about design, not an RFA):**
- A three-digit *m* makes any Bonferroni/BH correction severe.
- The unconstrained angle family cannot be corrected into meaningfulness.
- Each shortlisted construct must reach pre-registration with **one primary cell** (one *k*, axis,
  *h*, outcome, event type). All other cells are declared robustness cells that **may not sit on the
  pass path**.

No power, `n_available` or effect-size band is computed here.

---

## 16. Data compatibility

Substrate as described by the feasibility audit (not re-audited):
- PIT N100 EOD, 2011-03-25 → 2026-09-11;
- 3,834 real sessions and 383,795 member-days;
- 216 symbols / 198 entities;
- survivorship-safe membership;
- EOD price history from 2010-01-04 for warm-up;
- 1m stock data only from 2023-01-02.

| Requirement | Available? | Constructs affected |
|---|---|---|
| Daily OHLC | Yes (`equity_bhavcopy`) | All |
| Causal (as-of-*t*) adjusted series | **Not materialized.** Constructible from `adjustment_factors` + raw; the existing view is backward | All displacement/rate constructs |
| Enumerated non-ratio CA events | **No** (store incomplete pre-2022) — external enumeration required | All (exclusion windows) |
| PIT membership | Yes (`isd/n100_membership.duckdb`) | All |
| Trading calendar | Yes (two artifact dates to declare: 2012-11-11, 2016-04-19) | All |
| Earnings / AGM calendar | **No** | GT-1, GT-3 confounder control is indirect only |
| PIT sector table | **No** (excluded by substrate) | Any sector-neutral design |
| Listing dates | `instrument_master.listing_date` (VARCHAR, unaudited) | GT-6 |
| Intraday | Only 2023-01-02 → | Sub-daily rays / session angles **NOT TESTABLE** on EOD |
| History ≥ several long-cycle periods | No | GT-5 NOT TESTABLE |
| History before 2010-01-04 | No | Left-censored anchors (§5.2) |

**Certification status (correction to the brief's wording).** The brief calls the substrate
"certified". Per the feasibility audit (`1aff3ae`, §L condition 2), **no scoped PTMS certificate has
been issued for the EOD surface**. Conditions 2–5 of that audit remain prerequisites for any outcome
read: scoped certification, non-ratio CA enumeration, the membership-precision disposition, and
BE/DVR inclusion rules. This catalogue does not depend on them; any test will.

---

## 17. Shortlist

### 17.0 Category lists

| List | Constructs |
|---|---|
| **A. Most faithful to Gann** | GO-2 (time overbalance — near-verbatim), GT-1 (anniversary), GA-3 / GS-5 (1×1 / squaring as rate balance), GT-2 (time balance) |
| **B. Most statistically testable** | GT-1, GT-2, GO-2, GS-3 |
| **C. Most causally clean** | GT-1 (calendar event from a confirmed pivot), GT-2, GO-2 (time leg), GN-2 |
| **D. Best suited to PIT N100** | GO-2, GA-3 (stock-specific self-scaling; GX-2 ranking natural), GT-1 (stock-specific anchors pass the veneer test) |
| **E. Highest risk of researcher DoF** | GA-2 / GA-4 (scale × ray fan), GN-1, GT-3 |
| **F. Likely pseudoscientific / non-falsifiable unless heavily constrained** | GN-1, GN-2, GN-3, GN-4, GT-3, GA-4, GO-4, GS-1, GS-2, GA-1, GA-5 |

### 17.1 Recommended candidates for formal pre-registration (not selected, not frozen)

Chosen on fidelity, falsifiability, causal cleanliness, dimensional validity, low DoF, N100 fit and
control availability — **not on expected profitability** (none was, or could be, assessed).

#### Candidate 1 — GO-2 Time overbalance

| Step | Specification |
|---|---|
| **THEORY CLAIM** | When a reaction within a trend lasts longer than the largest previous reaction in that trend, the trend has changed |
| **MATHEMATICAL CLAIM** | Per stock, confirmed pivots (swing-chart order *k*) define alternating legs. An **up-trend** holds while confirmed highs and lows ascend (trend rule declared). Its completed corrections (high → low legs) have durations *D*_1 … *D_J*. *D*\* = max_{j≤J} *D_j* (requires *J* ≥ *J*_min). For the current correction starting at confirmed high *O*: elapsed τ_t = *t* − *O*. **Time overbalance** at the first *t* with τ_t > *D*\*, while no close has exceeded the high at *O* and the trend rule is still unbroken. Mirror for down-trends. Claim: E[*s*·*r*_{t,h} \| overbalance, controls] < E[*s*·*r*_{t,h} \| no overbalance, controls], where *s* = +1 up-trend / −1 down-trend |
| **OBSERVABLE EVENT** | Session *t* of first time-overbalance within a correction; stock an N100 member at *t*; no enumerated non-ratio CA event inside [first pivot of trend, *t*] |
| **OUTCOME** | Primary option set (one to be pinned): (a) *s*·ln(*P̃*_{t+h}/*P̃_t*) with *h* declared; (b) trend-state flip (a confirmed lower low in an up-trend) within *h*. Outcome window strictly after *t* |
| **NULL** | The overbalance indicator carries no incremental information: its coefficient is 0 given controls |
| **CONTROL** | (i) **Price overbalance**: correction depth ln(*H_O*/min *L*) > largest prior correction depth; (ii) GO-1 retracement fraction; (iii) **time-only**: τ_t in sessions (hazard shape) without *D*\*; (iv) **shuffled history**: *D*\* from another stock at a similar date; (v) σ_ℓ, trailing momentum, distance from running high, calendar month; (vi) same-date random-rank / date-clustered errors. **Joint test**: time and price overbalance together vs each alone — the "price × time" content |
| **FALSIFICATION CONDITION** | Fails if, on the pre-registered primary cell, the time-overbalance coefficient is not significantly negative (for signed outcome) after multiplicity correction, **or** is not larger in magnitude than under the shuffled-history *D*\*, **or** vanishes once price overbalance and momentum are included. A wrong-sign result closes the construct — no sign-flip re-test (Family C rule, applied by analogy) |
| **Unresolved DoFs to pin** | *k*; trend rule; *J*_min; sessions vs calendar; *h*; outcome (a) vs (b); pooled vs separate legs; GX-1 vs GX-2; price basis; CA exclusion rule |

#### Candidate 2 — GT-1 Pivot anniversary

| Step | Specification |
|---|---|
| **THEORY CLAIM** | Important highs and lows mark future turning times at their anniversaries |
| **MATHEMATICAL CLAIM** | Per stock, a **major pivot** is a confirmed swing extreme (order *k*) that is also the extremum of the trailing *W* sessions, stamped at confirmation. For each major pivot date *d_O* and *n* ∈ 𝒩 (integer years, declared), the anniversary window is 𝒲 = {sessions within ±*w* of *d_O* + *n*·*Y*}. Claim: *P*(turn in [*t*+1, *t*+*h*] \| *t* ∈ 𝒲) > *P*(turn \| *t* ∉ 𝒲, matched) |
| **OBSERVABLE EVENT** | Session *t* ∈ 𝒲, with the pivot confirmed before *t*; stock a member at *t* |
| **OUTCOME** | Primary option set: (a) turn incidence per §13.3 within *h*; (b) \|ln(*P̃*_{t+h}/*P̃_t*)\|/σ_ℓ(*t*) (non-directional activity) |
| **NULL** | Outcome distribution in anniversary windows = matched non-anniversary windows |
| **CONTROL** | (i) **Placebo lags** (non-Gann year fractions, e.g. 300/330/400/430 days) from the same pivots; (ii) **random-anchor anniversaries**: anniversaries of random non-pivot dates of the same stock in the same calendar month, which absorbs the annual results/dividend calendar; (iii) calendar-month and expiry-week matching; (iv) σ_ℓ and momentum at *t*; (v) date-clustered errors — anniversaries of a market-wide pivot synchronize across stocks |
| **FALSIFICATION CONDITION** | Fails if anniversary-window incidence does not exceed **both** placebo-lag and random-anchor-anniversary incidence on the primary cell after correction. Passing against placebo lags only (not random anchors) is recorded as **annual-calendar seasonality, not Gann** |
| **Unresolved DoFs to pin** | *Y* ∈ {365.25, 360}; 𝒩; *W*; *k*; *w*; *h*; outcome (a) vs (b); CA exclusion windows around pivot detection |

#### Candidate 3 — GA-3 ≡ GS-5 Self-scaled 1×1 break

| Step | Specification |
|---|---|
| **THEORY CLAIM** | A trend is sound while it holds its 1×1; breaking the 1×1 signals weakening. Price and time are "square" when the move's rate matches its predecessor's |
| **MATHEMATICAL CLAIM** | Confirmed pivots *O'* → *O* bound the prior leg: *A* = \|*x_O* − *x_{O'}*\|, *D* = *O* − *O'* sessions, ρ = *A*/*D*. The new leg's ray is *L*(*t*) = *x_O* + sgn·ρ·(*t* − *O*), where sgn = +1 for a rising leg from a low and −1 for a falling leg from a high. **Break** = first *t* ≥ confirmation(*O*) with sgn·(*x_t* − *L*(*t*)) < 0 after sgn·(*x*_{t−1} − *L*(*t*−1)) ≥ 0. Claim: E[sgn·*r*_{t,h} \| break, controls] < E[sgn·*r*_{t,h} \| controls] |
| **OBSERVABLE EVENT** | First 1×1 break in the leg; member at *t*; no enumerated non-ratio CA event in [*O'*, *t*]; bonus/split handled by the declared basis |
| **OUTCOME** | Primary option set: (a) sgn·ln(*P̃*_{t+h}/*P̃_t*); (b) leg termination (confirmed opposite pivot) within *h* |
| **NULL** | The break carries no incremental information given controls |
| **CONTROL** | (i) **Price-only**: close below a horizontal level at the same current distance from *x_O*; (ii) **time-only**: same elapsed Δ*T*; (iii) **placebo rates**: ρ × {0.8, 1.25}; (iv) **shuffled history**: ρ from another stock's leg at a similar date; (v) GS-3 momentum-z since pivot; (vi) σ change between legs; (vii) date-clustered errors or same-date random rank |
| **FALSIFICATION CONDITION** | Fails if the 1×1 break coefficient is not significantly in the predicted direction on the primary cell after correction, **or** placebo rates or shuffled-history ρ perform as well — which would mean the stock's own rate carries no Gann-specific information — **or** it vanishes under momentum-z and price-only controls |
| **Unresolved DoFs to pin** | *k*; ρ source (prior leg vs mean of prior legs); break vs touch (GS-5 form); *h*; outcome; sessions vs calendar; log (disclosed departure from arithmetic) |

#### Alternate — GT-2 Time symmetry

Offered as an alternate, not a fourth primary, because it shares GO-2's pivot machinery and
confounders. Adding it raises slate *m* by ~16–48 (§15.3) for partly overlapping information.

| Step | Specification |
|---|---|
| **THEORY CLAIM** | A move lasts as long as the prior move |
| **MATHEMATICAL CLAIM** | Termination hazard of the current leg at elapsed τ = *D*_{j−1} (± *w*) exceeds the hazard at matched τ without that reference |
| **OBSERVABLE EVENT** | Session with \|τ_t − *D*_{j−1}\| ≤ *w*, current leg unconfirmed-ended at *t* |
| **OUTCOME** | Leg termination within *h* |
| **NULL** | Hazard(τ \| τ ≈ *D*_{j−1}) = Hazard(τ) |
| **CONTROL** | Elapsed-time-only hazard; placebo multipliers 0.8 / 1.25; shuffled *D*; σ regime |
| **FALSIFICATION CONDITION** | No hazard excess over the time-only curve and the placebo multipliers on the primary cell |

---

## 18. Rejected / non-testable constructs

| ID | Status | Reason |
|---|---|---|
| GA-1 | R | Price ≡ time by fiat; ₹ is not a common unit across N100; CA-fatal |
| GA-5 | NT | Pixel geometry; aspect-ratio dependent |
| GS-1 | R | Rupees ≡ days; decimal shifting makes it unfalsifiable; CA-fatal |
| GS-2 | R | Needs an exogenous points-per-day constant; CA-fatal. Scale-free residue lives in GT-2 |
| GN-3 | R | Equates rupee-derived and day-derived angles; CA-fatal |
| GN-4 | NT | Diagram reading is not a model |
| GO-4 | R | No data, no mechanism, unbounded DoF; also a market-wide claim |
| GT-5 | NT | ≤ 2 repetitions in 15.5 years |
| GX-3 | R for Family F | Veneer: an index claim priced with 100 names. Admissible only as a Family C/D index hypothesis under its own `per_trade_pnl` RFA |
| GT-4 | D (fails veneer on N100) | Common calendar date = one index event per date |
| GT-6, GT-7, GO-3, GO-5, GX-4 | D | Weak fidelity / non-predictive / not Gann-specific / auxiliary / secondary analysis |

---

## 19. Recommended next research step

In order. Nothing here authorizes a read.

1. **Operator rulings.**
   - **(a) Family placement.** Record whether stock-level Gann on N100 is a **Family F** hypothesis
     (the reading this catalogue assumes for its shortlist), leaving Family C (single-index
     `per_trade_pnl`) untouched as a separate family. The catalogue cannot make that
     reclassification itself.
   - **(b) Record today's exposure ruling.** Historical N100 EOD may be used; results may not be
     represented as pristine confirmation. Under GR-1.4 it should be appended to the register as a
     row **before** any read.
   - **(c) Accept, trim or amend the shortlist (§17.1).**
2. **Open a PTMS multiplicity register entry** for the accepted slate, with *m* pinned from §15
   before any read. This is outstanding programme-wide.
3. **Discharge feasibility-audit conditions 2–5** (scoped EOD certification; external non-ratio CA
   enumeration; membership-precision disposition; BE/DVR rules), and decide **price basis** (raw
   with exclusions vs as-of-*t* adjusted) and **dividend basis**. These are pre-registration
   inputs.
4. **Draft one pre-registration per accepted construct**: primary cell pinned, robustness cells
   declared off the pass path, controls and falsification conditions from §17.1, evidence label
   (historical = development / non-confirmatory per GR-1.3 and today's ruling).
5. **Then** RFA declarations, `rank_ic` for GX-2 or a per-event formulation for GX-1, with
   independently defended bands. **The band and power must be defended against the multiplicity
   *m* pinned in step 2, not against a single-test α.** A three-digit *m* on a finite formation
   count is the demonstrability arithmetic that closed C5, C4 and F1 — design arithmetic, noted here
   without computing power. Only after PROCEED and freeze may any outcome be read.

---

## 20. Governance status

- This is a **GANN CONSTRUCT CATALOGUE / HYPOTHESIS-DESIGN DOCUMENT**. **No construct is selected,
  frozen or approved** by appearing here, including the §17.1 shortlist.
- **No TRAIN/HOLDOUT was created. No RFA was run. No backtest, performance calculation, parameter
  search, threshold fit or optimization was performed.**
- **No outcome value was read.** This document queried no data store. Its data statements are
  carried from `PTMS_N100_EOD_FEASIBILITY_AUDIT_2026-09-14.md`, which read metadata and validity
  predicates only.
- **No existing hypothesis definition was modified**: Families B, C, D, F and G, and PTMS-G-PTSQ,
  are untouched.
- **Nothing here suggests Gann has predictive power.** The document defines what would have to be
  observed for any Gann construct to survive, and what would falsify it.
- **Open operator items raised:**
  - Family C vs F placement for stock-level Gann;
  - register row for today's exposure ruling;
  - shortlist decision;
  - PTMS multiplicity register;
  - the "certified" wording (no scoped EOD certificate yet).

---

## 21. Addendum — construct status after F0 and primary-source delta Δ1

**Authority:**
- `PTMS_GANN_PRIMARY_SOURCE_CLAIM_REGISTER_2026-09-14.md` §§22, 24, 26;
- the operator handoff of 2026-09-14 authorizing this update.

§§1–20 are preserved unedited. Where they conflict with this section, this section governs.

### 21.1 Status changes

| ID | Original status | Status now | Basis |
|---|---|---|---|
| GA-1 | R | **Arm 1 as GF-2** (framework), conditional on the translation ruling | 45° = one chart space per period; stocks 1 point per space on the daily chart ([MMPTC] pp. 1, 3, 5). The original objections (rupees ≡ days by fiat; CA-fatal on adjusted levels) stay as **design constraints** — scale-placebo controls and as-traded pricing — not grounds for rejection |
| GA-2 | S | Arm 3 | Data-derived scale; not Gann's convention |
| GA-3 | P | **Arm 2** | Not a test of Gann's documented angle method (register §26.6) |
| GA-4 | S | Folded into GF-2, **Gann's rays only** (1×1, 2×1, 1×2; red angles on squares of 9) | [MMPTC] p. 5; an arbitrary ray fan remains high-DoF |
| GA-5 | NT | NT (pixel sense) | The Master Chart space grid is mechanized as units under GF-2 |
| GS-1 | R | **Arm 1 as GF-3** (square of high / low) | [MMPTC] p. 4 |
| GS-2 | R | **Arm 1 as GF-3** (square of range) | [MMPTC] p. 4 |
| GS-3 | S | Arm 2 | Random-walk scale is modern |
| GS-4 | S | Arm 3 | — |
| GS-5 | P | Arm 2 | ≡ GA-3 |
| GT-1 | P | **Arm 1 as GF-5**, month/year resolution; 360-day form held | WSSS p. 55; [NSTD] p. 14 |
| GT-2 | P (alternate) | Arm 2 | Only a qualitative primary anchor (register TIM-08) |
| GT-3 | S | **Arm 1 as GF-4T** (circle divisions) and within **GF-1** (fractions of 144) | [MMPTC] pp. 2, 4, 8, 9 |
| GT-4 | D | Faithful at index level; Arm 3 on a stock cross-section | Register ANN-04 |
| GT-5 | NT | NT | Great Cycle / 56-year periods: at most one repetition in span |
| GT-6 | D | Hold | Age is from incorporation, not listing |
| GT-7 | D | Arm 2 | — |
| GN-1, GN-2 | S | **Hold** | Spiral / √P not in the primary sources inspected |
| GN-3 | R | R | As above |
| GN-4 | NT | NT | — |
| GO-1 | S | Partly Arm 1: halfway point of range or high as a GF-1 / GF-3 / GF-4P anchor and level | [MMPTC] pp. 3, 6, 7, 9. Generic eighths-of-range stays a control |
| GO-2 | P | Relative form → **Arm 2**; absolute durations → **GF-6** | Register §16, TIM-03/04, Δ-16 |
| GO-3 | D | Faithful, not price-time | Register PRB-04 |
| GO-4 | R | R | — |
| GO-5 | D | Hold | *k* not primary-pinned |
| — (new) | — | **GF-6** absolute reaction duration | Register TIM-03/04; [NSTD] p. 38 |
| — (new) | — | **GF-7** third-month / 3rd–4th move / 6–7 week culmination | Register TIM-01/09; [NSTD] pp. 14, 38 |
| GX-1, GX-2 | P-compatible | Unchanged, **relabelled** | Pooling across N100 is a statistical device, not a Gann claim (Gann: study each stock individually) |
| GX-4 | D | Elevated to a **required diagnostic** | Per-stock heterogeneity follows from Gann's individual-study principle |

### 21.2 Shortlist

The §17.1 shortlist (GO-2, GT-1, GA-3 ≡ GS-5, alternate GT-2) is **superseded**. The candidate set
is now GF-1 to GF-7, defined in `PTMS_GANN_FAITHFUL_CONSTRUCT_DEFINITION_2026-09-14.md`. **Not
selected, not frozen.**

### 21.3 Carried constraints

- **§4's dimensional analysis still applies.**
  - *Fidelity* requires Gann's own unit.
  - *Evidence of Gann-specific content* requires showing that the unit matters: scale placebos must
    underperform.
  - A faithful construct that works equally well under a non-Gann scale is not evidence for Gann.
- **§15's multiplicity must be recomputed** for GF-1 to GF-7 before any read. The GF grids are larger
  than the old slate.
- **§14's corporate-action analysis** now bites harder: GF-2, GF-3 and GF-4P are level constructs on
  as-traded prices.

### 21.4 Governance

- No outcome read; no RFA; no TRAIN/HOLDOUT; nothing frozen.
- No family definition modified.
- This addendum does not suggest Gann has predictive power.
