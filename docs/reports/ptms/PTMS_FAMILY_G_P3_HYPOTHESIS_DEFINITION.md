# PTMS Family G — P3 hypothesis definition

**Hypothesis ID:** `PTMS-G-PTSQ` — *the option-implied price-time square*
**Date:** 2026-09-14 · **Phase:** P3 only · **Status:** CANDIDATE, NOT FROZEN (operator freezes, §18)
**Substrate:** NIFTY index-options EOD, certified 2026-09-13
(`PTMS_FAMILY_G_INDEX_OPTIONS_SUBSTRATE_CERTIFICATION_2026-09-13.md`, commit `4632193`, re-verified `29ec3b6`)

**Access level of this document: meta / design only.** Writing it read no option price, no
settlement, no open interest and no outcome. The only data touched was structural and date-level:
the expiry ladder, the resolved final trading day of each expiry, and the session spacing between
them. No construct was computed, no P&L calculated, no strike ranked, no scan run, no RFA gate run,
no declaration frozen, and no TRAIN or HOLDOUT read taken. No covariate (spot, VIX, futures,
realized vol) is used or needed.

> ## Headline — read before anything else
>
> **The hypothesis below is well-posed, uses only the certified surface, and is expected to be
> ABANDONED at the RFA.** That is a prediction from arithmetic (§13.6), not a gate result.
>
> HOLDOUT holds **35** structurally eligible weekly cycles over 0.673 years, so
> `ncp = S·√T = S × 0.820`. At the upper edge of a defensible Sharpe band (S = 1.00) the maximum
> achievable power is **0.200**. Power 0.80 needs **S ≈ 3.1**, or **323** cycles (6.2 years) even
> at the optimistic corner.
>
> **This is a property of the window, not of the construct.** Any Family G hypothesis that yields
> one P&L number per weekly cycle and is confirmed on this HOLDOUT faces the same wall. That is the
> RS-MOM finding again, and it is recorded in §13.7 for the operator's decision on Family G as a
> whole.

---

## 1. Research question

**Does the distance the NIFTY forward has already travelled, measured against the distance the
option market priced for that much elapsed time, predict whether the remaining time premium of the
same expiry is over- or under-priced?**

Stated operationally: late in a weekly cycle, compare the realized displacement of the
option-implied forward with the straddle-implied expected displacement for the same elapsed time.
If the ratio is at or above 1 (*price has outrun time*), a short at-the-money straddle held to
settlement earns more than when the ratio is below 1 (*time has outrun price*). The long straddle
earns more in the second case.

### The five research objects, kept distinct

| Object | What it is in this hypothesis | Source | Role |
|---|---|---|---|
| **A. Index state** | The NIFTY forward to expiry E, `F`. **Never observed directly.** Inferred inside the options surface by put-call parity | `option_bhavcopy` only | Input to the price-time construct |
| **B. Option contract state** | `close` and `contracts` of the CE and PE at one strike, on one expiry, on two sessions; `settle` on the final trading day | `option_bhavcopy` | Price inputs, tradeability, settlement |
| **C. Price×time relationship** | `R`, the ratio of realized forward displacement to straddle-implied displacement over the same session count (§3) | Derived from A and B | **The construct under test** |
| **D. Market-structure variable** | The listed expiry ladder and its resolved final trading day, which defines the clock. The ATM straddle is the market's own price of time (§4) | Ladder + calendar | Defines the time axis and the scale |
| **E. Forward outcome** | Net, premium-normalized P&L of a straddle opened at formation and settled at the final trading day, signed by the construct (§5) | `option_bhavcopy` `settle` + fee model | The dependent variable |

Objects C and E share no price observation. C is built entirely from sessions at or before
formation; E from the formation close and the final-trading-day settlement.

---

## 2. Economic mechanism

Two published effects point the same way, and one well-known effect points the other way. The
hypothesis commits to the first sign **before any data** (§16 says what happens if the second is
true).

**Declared mechanism — implied volatility overreacts to recent realized movement.**
- Option sellers mark implied volatility up after a large realized move and down after a quiet
  stretch, by more than subsequent realized volatility justifies. Documented as overreaction in
  index options (Stein 1989, *Overreactions in the options market*) and as short-horizon
  under-reaction and longer-horizon over-reaction in implied volatility (Poteshman 2001).
- If so, after `R ≥ 1` the remaining straddle is rich (short earns), and after `R < 1` it is cheap
  (long earns).
- In the language the programme started from: a Gann "price-time square" is the point where price
  travelled equals time elapsed on a common scale. The Brownian `√time` law makes that scale
  exact, and the at-the-money straddle quotes it in index points (§3). `R = 1` *is* the square, and
  the claim is that the market mis-prices time when the square is broken.

**Opposing mechanism, declared as the principal threat — volatility clustering.**
Large moves beget large moves (GARCH-type persistence). If clustering dominates overreaction, then
after `R ≥ 1` the remaining realized move is *also* large and the short straddle loses. That would
produce the opposite sign. **It is not a second hypothesis.** A significant opposite sign ABANDONs
this hypothesis and may not be re-registered as a flipped-sign successor (§16).

**Why the null leans against passing.** The design is a long/short overlay (§5), so under "no
timing information" its expected value is `(2p − 1) · VRP`, where `p = P(R ≥ 1)` and `VRP` is the
unconditional short-straddle premium. With implied volatility at or above realized, `p < 0.5` by
pure arithmetic:

| implied / realized vol | P(R ≥ 1) under the null | Null sign of the overlay |
|---|--:|---|
| 1.00 | 0.425 | negative |
| 1.10 | 0.380 | negative |
| 1.20 | 0.338 | negative |
| 1.30 | 0.300 | negative |

*(Pure arithmetic: `R ≥ 1 ⇔ |Z| ≥ √(2/π) · ratio` for a zero-drift Gaussian forward. No data.)*

This is deliberate. A short-only conditional rule would pass on the unconditional volatility risk
premium alone. MSRP's triage found the unconditional short straddle net-positive on 2023–2025, so
such a pass would say nothing about price and time. **The overlay cannot be manufactured into a
pass by the VRP.** The cost is power, and the power is already insufficient (§13).

---

## 3. Exact Price × Time construct

### 3.1 Candidate price×time families considered

Five families were weighed on **non-outcome grounds only**: units, anchor definability on EOD
options data, free parameters, and whether they need an uncertified covariate. **None was
computed.**

| # | Family | Exact form | Anchor / interval | Units & normalization | Free parameters | Needs uncertified surface? | Disposition |
|---|---|---|---|---|---|---|---|
| **1** | **√-time implied-displacement ratio** | `R = \|F_f − F_a\| / (Π_a · √((τ_a − τ_f)/τ_a))` | Anchor and formation fixed in sessions before the resolved FTD | Dimensionless; the scale is the market's own straddle | **0 fitted**; 2 fixed offsets, threshold `1` implied by the construct | No | **SELECTED** |
| 2 | Gann angle (price per unit time) | `θ = (F_f − F_a)/(k · Δsessions)` against 1×1, 2×1 … | Same | Index points per session; needs `k` ("1 point = 1 session") | `k` plus the angle set: unit-dependent, no defensible `k` | No | Rejected: `k` is arbitrary and the angle set is a multiplicity farm |
| 3 | Time-cycle counts (square of nine, fixed counts to turning points) | Turning point declared at session counts `{n_i}` from a pivot | Needs pivot detection on the forward path | Sessions | Pivot rule, count set, tolerance | Pivot detection over multi-week paths needs a contiguous forward series across expiries (roll rule) | Rejected: ≥ 3 free choices plus a roll construction |
| 4 | Price-time symmetry of the prior swing | Retracement time `≈` advance time | Pivots on the prior swing | Sessions ↔ points, needs a scale | Pivot rule, symmetry tolerance | Same roll problem; swings span expiries | Rejected: same as 3 |
| 5 | Square of the prior range | `(range_prev)² ∝ duration_prev` | Prior cycle's high–low of the forward | Points² per session | Range definition | **Yes.** An intraday forward high/low does not exist in EOD options (option highs and lows are not synchronous, so no parity forward can be formed from them). Index intraday high/low would be an uncertified covariate | Rejected: requires an uncertified covariate |

Family 1 is the only one that (a) has a scale the market itself quotes, (b) has zero fitted
parameters, and (c) lives entirely inside one expiry's contracts on the certified store.

### 3.2 Definitions (Family 1, exact)

**Clock.** For a settling expiry `E`, let `FTD(E)` be its resolved final trading day (§8). Let
`t(k)` denote the trading session `k` sessions before `FTD(E)` on the trading calendar, so
`t(0) = FTD(E)`.

| Symbol | Definition |
|---|---|
| Anchor session | `a = t(4)` |
| Formation session | `f = t(2)` |
| Sessions remaining | `τ_a = 4`, `τ_f = 2` (sessions to FTD, FTD counted, anchor/formation not) |
| Elapsed fraction | `(τ_a − τ_f)/τ_a = 2/4` |
| Eligible strikes on session `s` | `𝒦(s)`: strikes `K` of expiry `E` where **both** CE and PE rows exist with `contracts > 0` |
| ATM strike | `K*(s) = argmin_{K ∈ 𝒦(s)} \|C_s(K) − P_s(K)\|`; ties go to the **lower** strike |
| Option price | `C_s(K)`, `P_s(K)` = `close` on session `s` |
| Parity forward | `F_s = K*(s) + C_s(K*(s)) − P_s(K*(s))` |
| ATM straddle | `Π_s = C_s(K*(s)) + P_s(K*(s))` |
| **Construct** | **`R = \|F_f − F_a\| / (Π_a · √(1/2))`** |
| **Signal** | **`s = +1` (short straddle) if `R ≥ 1`; `s = −1` (long straddle) if `R < 1`** |

**Why the scale is exact, not heuristic.** For a zero-drift forward with volatility `σ`, the ATM
straddle satisfies `Π ≈ E|F_T − F| = √(2/π) · σ · F · √τ` (Brenner–Subrahmanyam). The expected
absolute displacement over the first `τ_a − τ_f` of `τ_a` remaining sessions is therefore
`Π_a · √((τ_a − τ_f)/τ_a)`. `R` is realized displacement divided by *market-implied expected*
displacement over the same time. `R = 1` is the price-time square with no free scale.

**Units:** index points ÷ index points, so dimensionless. It is comparable across the 100→50
strike-grid change and across index levels, because nothing is measured in strikes or in points.
**Directionality:** `R` is unsigned. The hypothesis is about the magnitude of price against time,
not direction. **Threshold:** `1`, fixed by the construct. **Not estimated, not searched.**
**Estimation budget:** **zero.** No parameter of `R` or `s` is fitted to any data, in any window.

**Discounting.** Parity is taken at `r = 0`. Over ≤ 4 sessions the discount factor on `K*` is
`≈ 1 − 0.065 × 4/250 ≈ 0.999`. It enters `F_f` and `F_a` almost identically and so cancels to first
order in `F_f − F_a`. **Dividends** do not enter: `F` is the forward to `E` itself, not spot.

### 3.3 Why (4, 2)

- **Formation `t(2)`** leaves two sessions of premium to realize. `t(1)` leaves a one-session
  outcome dominated by the expiry-day auction and gamma noise. `t(3)` shortens the construct
  interval to one session.
- **Anchor `t(4)`** is the largest offset that keeps the construct interval inside the life of the
  same weekly contract across both regimes (session spacing between consecutive FTDs is 4–5 in
  TRAIN and 3–5 in HOLDOUT, §10).
- This choice was made **from the ladder's session spacing alone**, before any option price was
  seen. It counts as 2 declared degrees of freedom (§14), not zero.

---

## 4. Market-structure component

PTMS's market-structure component is here the **option market's own structure of time**: the
listed expiry ladder, which fixes the clock, and the ATM straddle, which prices time in index
points. **No open-interest, PCR, max-pain, OI-change or volume variable enters the primary
hypothesis.**

Every market-structure quantity touched by this design is classified below.

| Quantity | Class | Used where | Fitted? |
|---|---|---|---|
| Listed expiry set, `expiry_dt` | **Structural descriptor** | Ladder (§8) | No |
| Resolved final trading day `FTD(E)` | **Structural descriptor** | Clock | No |
| Session spacing between FTDs | **Structural descriptor** | Offset choice (§3.3), eligibility counts | No |
| Strike grid (100 → 50 at 2020) | **Structural descriptor** | Irrelevant to `R`, which is unit-free | No |
| `contracts > 0` | **Structural descriptor** (tradeability predicate) | `𝒦(s)`, eligibility | No |
| `K*(s)` | **Feature** (depends on prices) | `F`, `Π`, the traded strike | No |
| `F_s` (parity forward) | **Feature** | `R` | No |
| `Π_s` (ATM straddle) | **Feature** | `R` scale, outcome normalization | No |
| `R` | **Signal-linked** | `s` | No |
| `s ∈ {+1, −1}` | **Signal** | Outcome sign | No |
| Threshold `1` | Construct constant | `s` | **No**: implied by the construct |
| Offsets `(4, 2)` | Declared design constant | Clock | **No**: set from ladder spacing |
| Slippage `κ`, quantity `Q` | Declared cost constants | §9 | **No** |
| `open_int`, PCR, max pain, OI change, IV surface | **Feature, EXCLUDED** | Nowhere | — |
| **Fitted parameters** | — | — | **None** |

---

## 5. Exact option outcome

**Instrument:** NIFTY weekly index options only. **Expiry:** the single settling expiry `E` whose
resolved FTD defines the cycle (§8). **Strike:** `K*(f)`, the formation-session ATM strike (§3.2).
It is not re-ranked, not re-chosen, and not moved to a neighbour. **Legs:** one CE and one PE at
`K*(f)`, equal quantity. **Direction:** neutral in the underlying. Short straddle when `s = +1`,
long straddle when `s = −1`.

**Entry:** formation session `f`, at `close` of each leg. **Exit:** none. **Held to settlement** at
`FTD(E)`.

**Settlement value per unit:**
`V = settle_CE(E, K*(f), FTD) + settle_PE(E, K*(f), FTD)`, from the FTD rows of the same contracts.

**Gross premium-normalized P&L:**

- short (`s = +1`): `g = (Π_f − V) / Π_f`
- long (`s = −1`): `g = (V − Π_f) / Π_f`

**Net per-cycle outcome:** `z = g − φ − κ_eff`, where

- `φ` = fees for the legs actually traded, divided by `Π_f · Q` (§9)
- `κ_eff = κ` applied once, at entry (settlement has no spread)

`z` is the per-trade P&L series that the RFA metric `per_trade_pnl` refers to. **One `z` per
eligible cycle; no cycle is traded twice; holding windows never overlap** (formation `t(2)` is
always after the previous cycle's FTD, because FTD spacing is ≥ 3 sessions).

**Untraded handling:** a leg with `contracts = 0` at `K*` on `a` or `f` cannot be `K*`, because
`𝒦(s)` excludes it. If `𝒦(a)` or `𝒦(f)` is empty, **the cycle is ineligible: skipped, never
imputed, never moved to another strike or expiry.** Settlement needs no trade (`settle` is an
exchange-published settlement, not a print), but the FTD rows for both legs at `K*(f)` must exist.

**Pre-TRAIN verification required (settlement semantics).** The certification established that
`settle = 0` means worthless-at-expiry on the contract's own FTD. It did not establish that `settle`
on the FTD equals intrinsic value against the final settlement price for every strike. Before any
TRAIN read, a structural check must confirm, on every FTD in **already-spent** windows only
(2023-01-02 → 2025-12-31, MSRP-spent), that `min(settle_CE, settle_PE) = 0` and that
`K + settle_CE − settle_PE` is constant across strikes. The check yields no statistic about
outcomes. **If it fails, STOP: the outcome definition is not certified.**

---

## 6. Entry / exit specification

| Item | Rule |
|---|---|
| Decision time | After the close of session `f = t(2)`, using only rows dated `a` and `f` |
| Entry price | `close` of each leg on `f`. **Disclosed optimism:** bhavcopy `close` is the last traded price, not a bid/ask, and the CE and PE closes are not synchronous. `κ` (§9) is the only allowance |
| Quantity | `Q = 75` units per leg, constant across all eras (§9) |
| Exit | **None before expiry.** No stop, target, roll, adjustment, delta hedge or early close |
| Settlement | Cash-settled at `FTD(E)` via `V` (§5) |
| Position overlap | Impossible by construction (§5) |
| Missing FTD row | Cycle ineligible (the expiry never settled in the store; §8) |

---

## 7. Tradeability rule

1. **`contracts > 0` is the only tradeability predicate** (certification §D). `open_int > 0` is
   **not** used: it discards 6,478 real trades.
2. Both legs at `K*(a)` on the anchor session and both legs at `K*(f)` on the formation session
   must have `contracts > 0`. This is guaranteed by `𝒦(s)`.
3. The FTD rows for `(E, K*(f), CE)` and `(E, K*(f), PE)` must exist.
4. **Untraded rows' `close` values are never read into anything.** All 4,021,553 untraded rows
   carry a non-zero `close` that the market never printed.
5. **VOID rule.** If eligible cycles fall below **80 %** of structurally eligible cycles in either
   window (TRAIN < 83 of 103, HOLDOUT < 28 of 35), the hypothesis is **VOID as specified**. That is
   neither PASS nor ABANDON, and it closes this specification. A re-specification with a different
   eligibility rule is a new hypothesis and increments the programme's multiplicity count.

The eligible fraction cannot be known without reading `contracts` at a price-selected strike, so it
is **not** estimated here.

---

## 8. Expiry handling

**The Thursday/Tuesday trap.** TRAIN is entirely Thursday-expiry; HOLDOUT is Tuesday-expiry (with
Monday holiday shifts). Any construct expressed in weekdays, or in "the weekly", would compare
different objects across the windows. **This construct is expressed entirely in trading sessions
before the resolved FTD, so both windows share one clock.**

1. **`expiry_dt` is nominal.** `FTD(E)` = the latest trading-calendar session `≤ expiry_dt`.
2. **The ladder.** For each window, the cycles are the expiries `E` with `FTD(E)` inside the window
   **and** at least one row dated `FTD(E)`. A listing with no row on its resolved FTD never settled
   in the store and is not a cycle.
3. **One cycle per FTD.** If two settling expiries ever resolved to the same FTD, the one whose
   nominal `expiry_dt` is nearest the FTD would be used. None does in either window (measured).
4. **Anchor inside the window.** A cycle whose anchor `t(4)` precedes the window start is excluded,
   so that no read crosses a window boundary. The same holds at the end: `FTD ≤ 2026-09-11`.
5. **Q-G1.** A cycle is excluded if 2021-03-30 falls anywhere in `[t(4), FTD]`. **Skip, never
   interpolate.** Session counts use the calendar, which carries 2021-03-30, so offsets do not shift.
6. **Short cycles.** Where consecutive FTDs are 3 sessions apart (one HOLDOUT cycle), `t(4)` is one
   session before the previous FTD. Contract `E` is listed weeks ahead, so the anchor is still read
   on `E`. It is still subject to `contracts > 0` at `K*(a)`.
7. **Never-settling listings excluded structurally** (date-level evidence, no prices):

| `expiry_dt` | Listed rows | Last row | Why it never settles |
|---|---|---|---|
| 2026-03-26 | 2025-03-28 → 2025-07-31 | 2025-07-31 | Thursday-era long-dated listing, dropped at the Thursday→Tuesday move |
| 2026-03-31 | 2025-08-01 → 2025-12-26 | 2025-12-26 | Re-listed; the settling contract is **2026-03-30** (rows to its FTD) |
| 2026-06-25 | 2021-06-25 → 2025-07-31 | 2025-07-31 | Q-G4 orphan |

**Correction for the certification record.** Certification §E lists 2026-03-26 and 2026-03-31
among expiries "on non-trading days". Both are also **orphaned listings**: their last rows are
months before expiry, not merely a nominal-date shift. This matters only to the ladder, and the
ladder rule above handles it by construction. The operator may append the correction.

---

## 9. Cost model

**Era-accurate, from committed code:** `core/execution/options/fees.py::option_order_fees(premium,
quantity, side, trade_date)`, called per leg at entry.

| Component | Rate by `trade_date` | Side |
|---|---|---|
| STT on premium | 0.05 % (to 2023-03-31) · 0.0625 % (2023-04-01) · 0.10 % (2024-10-01) · **0.15 % (2026-04-01)** | Sell |
| Exchange transaction | 0.0495 % (to 2024-09-30) · 0.03503 % (2024-10-01) | Both |
| SEBI | 0.0001 % | Both |
| Stamp | 0.003 % | Buy |
| Brokerage | Rs 20 per order | Both |
| GST | 18 % on brokerage + exchange + SEBI | Both |
| **STT on exercise** | **Not in `fees.py`.** 0.125 % of intrinsic × `Q`, paid by the **holder** of an ITM option at settlement. **Applies to the long leg only.** The rate from 2026-04-01 must be taken from the Finance Act text and pinned before TRAIN | Long, ITM at FTD |

**Pre-TRAIN code requirement.** Add an exercise-STT schedule to `fees.py`, sourced from statute,
with a test. The rate is a regulatory constant, not market data, and it is **not chosen from any
outcome**. This is a code dependency, not an uncertified data surface.

**Quantity.** `Q = 75` units per leg in every era. Lot sizes changed across the windows, and an
NSE lot-size history is not a certified surface. Since `z` is premium-normalized, `Q` affects only
the fixed Rs 20 + GST component. Sizing is not under test.

**Slippage.** `κ = 1.0 %` of `Π_f`, charged once at entry, covering both legs' half-spreads and
close-to-fill non-synchronicity. **Not fitted.** Robustness `κ = 3.0 %` (§14).

**Mid-HOLDOUT regime change, disclosed.** Sell-side STT rises 0.10 % → 0.15 % on 2026-04-01,
inside HOLDOUT. It is applied by date and not averaged.

---

## 10. TRAIN / HOLDOUT boundary

| | **TRAIN** | **HOLDOUT** |
|---|---|---|
| Window | **2021-01-01 → 2022-12-31** | **2026-01-01 → 2026-09-11 — FROZEN; does not grow** |
| Calendar sessions / with data | 496 / 495 (Q-G1 missing) | 173 / 172 (2026-02-01 Budget Saturday) |
| Expiry weekday | Thursday (Wednesday on holiday shift) | Tuesday (Monday on holiday shift) |
| Ladder expiries settling in window | 104 | 36 |
| Excluded structurally | 1 touches Q-G1 | 1 anchor before window start |
| **Structurally eligible cycles** | **103** | **35** |
| Session spacing between consecutive FTDs | {4: 25, 5: 78} | {3: 1, 4: 8, 5: 26} |
| Eligible after tradeability | Unknown until read; VOID if < 83 | Unknown until read; VOID if < 28 |
| Traded-row share (whole window, certification §G) | 34.1 % | 58.8 % |

**The gap 2023-01-02 → 2025-12-31 is spent** (MSRP D1 triage, signal level) and is **never read**
by this hypothesis, except for the zero-statistic settlement-semantics check (§5), which is
confined there precisely because it is spent.

**Sequence and roles.** Nothing is fitted, so TRAIN is **not a selection surface**. It is a
confirmation gate:

1. RFA (§13): ABANDON ⇒ stop, no TRAIN read.
2. TRAIN gate: one-sided test of `mean(z) > 0` at α = 0.05. Fail ⇒ ABANDON, HOLDOUT unread.
3. HOLDOUT gate: the same test, once, at α = 0.05.

The two gates form a conjunction, so type-I error is not inflated. **No quantity may be changed
between TRAIN and HOLDOUT.** Pooling TRAIN and HOLDOUT (n = 138) is **not** a confirmatory design
and is barred.

---

## 11. Prior-exposure reconciliation

Component-wise, not path-literal. **Object A (the index path) is traced separately from objects
B/E (option prices),** because `F ≈ index level`, so any prior read of the NIFTY path in a window
is observation-shaped exposure of `R` in that window.

### 11.1 Surface: index-options EOD (objects B, E)

| Window | Prior consumer | Level | Effect on this hypothesis |
|---|---|---|---|
| 2016-07-01 → 2020-12-31 | Skew sleeve TRAIN (O-2) | signal, FAILED | Not used |
| **2021-01-01 → 2022-12-31** | Skew HOLDOUT *specified*, never read | none | **FRESH — TRAIN** |
| 2023-01-02 → 2025-12-31 | MSRP D1 straddle triage (O-2) | signal | Spent; not read, except the §5 zero-statistic check |
| **2026-01-01 → 2026-09-11** | None on this store | none | **FRESH — HOLDOUT** |
| 2026-09-* (dates unpinned) | **O-3** `cas_pcp_forward.py`: put-call-parity implied spot vs frozen `underlying_ltp`, from `wall_chain_snapshots` | signal, **different store** | **FLAG — observation-shaped overlap.** Same NIFTY option prices, and the same parity methodology, on HOLDOUT calendar dates ≤ 2026-09-11. At most two HOLDOUT cycles (FTDs 2026-09-01, 2026-09-08). The question O-3 asked (CAS LTP staleness) was not this one |

### 11.2 Surface: NIFTY index path (object A, observation-shaped)

| Row | Window | Level | Overlap |
|---|---|---|---|
| I-5 (A opening-drive), I-8 (intraday analog path) | HOLDOUT 2019-01-01 → 2022-12-31 | signal (gated) | **TRAIN 2021–2022**: the NIFTY path was read at signal level, intraday |
| D-2 (CB-N50) | 2016 → 2022 | signal (gated) | **TRAIN 2021–2022**: daily index returns, as the dependent variable of a constituent-breadth IC |
| I-3 (Nifty/Bank ratio MR) | 2023-01 → ~2026-05 | signal | **HOLDOUT 2026-01 → ~05**: the NIFTY path as half of a ratio |
| I-2 (regime facts → NiftyShield) | 2023-01-02 → 2026-07-03 | feature | **HOLDOUT 2026-01 → 07-03**: day-type labels on the path |

### 11.3 Class-level (hypothesis-class) exposure

| Source | What was learned | How it entered this document |
|---|---|---|
| O1 VRP declaration (`o1_vrp.py`, WITHDRAWN) | Literature band for unconditional short-vol Sharpe, 0.4–1.0 | Upper edge of the §13 band. **No data read** |
| MSRP Phase 7 fee triage verdict (2023–2025, spent) | A conditional next-day straddle timing rule was net-negative while the unconditional short straddle was net-positive; next-day RV was nearly orthogonal to unhedged straddle P&L | (a) Motivated the **overlay** design over short-only (§2). (b) Pushed the band **down**. Read at verdict-line level only, and never used to choose `R`, the offsets, the strike rule or the sign |

### 11.4 Disposition

- **No window this hypothesis would read is spent at signal level on its own store.**
- **Observation-shaped exposure exists in both windows** via the index path (11.2) and, in
  HOLDOUT, via O-3 (11.1). The register treats exposure as file-shaped. **Whether
  observation-shaped exposure spends budget is an open operator ruling.** Under a strict ruling,
  TRAIN is burned by I-5/I-8/D-2 and HOLDOUT by I-2/I-3.
- **Neither ruling changes the RFA verdict.** A strict ruling can only remove cycles: dropping the
  O-3 dates gives n = 33, which lowers power further.
- **This document's own exposure, for the register:** meta / structural. It covers ladder dates,
  FTD resolution and session spacing for both windows, plus the three excluded listings' first and
  last row dates. **No price, settlement, contracts count or open interest was read.**

---

## 12. Multiplicity declaration

| Level | Count | Treatment |
|---|---|---|
| Primary hypotheses tested | **m = 1** (`PTMS-G-PTSQ`, overlay `z`, one-sided) | α = 0.05, no correction needed at family level |
| Price×time families considered (§3.1) | 5 | Four rejected **on non-outcome grounds, never computed**. Disclosed, not counted in m |
| Secondary analyses (§14) | 2 | Descriptive only; **cannot pass the hypothesis** |
| Robustness variants (§14) | 5 | Reported only alongside the primary; **cannot rescue a failed primary** and cannot fail a passed one by themselves |
| TRAIN → HOLDOUT | 2 gates, conjunction | No inflation |
| Programme level (PTMS families A–G) | Operator's to set | This document assumes per-family α. If the operator imposes a programme-wide correction, α here shrinks, and the RFA verdict is unchanged (it can only get worse) |

---

## 13. RFA specification

**The RFA gate has not been run and no declaration has been frozen.** §13.6 is pre-computed
feasibility arithmetic from `scripts/rfa/power.py::power_at` / `n_required`, with no declaration
object and no market data. The operator runs the gate.

### 13.1 Declaration (exact field values for `governance/rfa/declaration.py::Declaration`)

| Field | Value |
|---|---|
| `name` | `PTMS-G-PTSQ` |
| `methodology_version` | `2.0.0` |
| `n_available` | **35** (HOLDOUT structurally eligible cycles) |
| `cadence` | `weekly — one settling NIFTY expiry per resolved final trading day` |
| `window` | `HOLDOUT 2026-01-01 -> 2026-09-11 (frozen)` |
| `test_type` | `one_sided` |
| `metric` | `per_trade_pnl` |
| `sharpe_lo` | **0.25** |
| `sharpe_hi` | **1.00** |
| `cadence_per_year` | **52** |
| `sharpe_provenance` | §13.4 |
| `prior_exposure` | §11, verbatim summary: TRAIN/HOLDOUT unspent on the options store; observation-shaped index-path exposure (I-5, I-8, D-2 on TRAIN; I-2, I-3 on HOLDOUT); O-3 parity-forward overlap on HOLDOUT 2026-09; class exposure O1 VRP (withdrawn, band only) and MSRP D1 verdict (design toward overlay, band down) |
| `delta_*`, `sd_*` | **Not supplied** (per_trade_pnl contract v2) |

**Why `per_trade_pnl` and not `rank_ic`.** The construct yields **one number per weekly cycle for
one underlying**. It is an index-level timing rule. Correlating `R` with `z` across 35 cycles is a
time-series statistic, and dressing it as a rank IC would repeat the error CLAUDE.md records
against CB-N50 ("a hidden index timing under a stock-level veneer"). Strikes of one expiry are not
an independent cross-section either: they share one underlying and one settlement.

### 13.2 Outcome and effect-size interpretation

Effect size is the **annualized Sharpe of `z`**, the net premium-normalized overlay P&L per cycle,
with `S_per-cycle = S / √52`. An S of 0.5 means that holding the overlay every week for a year
earns half a standard deviation of its annual P&L above zero, net of costs.

### 13.3 Minimum meaningful effect

**S = 0.25.** Below this, a weekly options overlay with a negative-carry long leg adds nothing an
operator would allocate to after model risk and execution error. It is the band's lower edge.

### 13.4 Defensible band — provenance

**[0.25, 1.00].**

- **Upper edge 1.00** is the top of the literature range for the *unconditional* short index-vol
  premium (0.4–1.0, the band O1 cited). The overlay harvests that premium on only `p ≈ 0.3–0.45` of
  cycles and **pays** it on the rest (§2). A timing overlay credibly beating the full unconditional
  harvest's best case would need an implied-volatility overreaction far larger than Stein (1989)
  or Poteshman (2001) report. The upper edge is generous, not central.
- **In-house evidence pulls down:** MSRP D1's conditional straddle rule was net-negative where the
  unconditional was net-positive, on a disjoint window.
- **Lower edge 0.25** = minimum meaningful effect (§13.3).
- Neither edge was derived from any Family G read, and neither may be revised after the gate.

### 13.5 Sample size and cadence

`n = 35`, `c = 52` ⇒ `T = n/c = 0.673` years, `√T = 0.820`. **Cadence cancels**
(`ncp = S·√T`). Using the realized cycle rate (~51/yr) instead of 52 moves `√T` by < 1 %.
TRAIN's 103 cycles do not enter the RFA: the confirmatory window is HOLDOUT.

### 13.6 Power calculation (arithmetic, not a gate run)

One-sided α = 0.05, `per_trade_pnl` unit SD, noncentral-t, evaluated at the optimistic corner:

| | Value |
|---|--:|
| Max achievable power at S = 1.00, n = 35 | **0.2003** |
| S required for power 0.80 at n = 35 | **≈ 3.1** |
| `n_required` at S = 1.00 (optimistic corner) | **323** cycles ≈ 6.2 years |
| `n_required` at S = 0.625 (central) | **825** cycles ≈ 15.9 years |
| `n_required` at S = 0.25 (pessimistic) | **5,146** cycles ≈ 99 years |

For comparison only (not a valid design): TRAIN n = 103 needs S ≈ 1.8, and pooled n = 138 needs
S ≈ 1.6.

### 13.7 Pass / fail, and what the verdict means

- **Rule:** power at the optimistic corner ≥ 0.80 ⇒ **PROCEED**; otherwise **ABANDON**.
- **Predicted verdict: ABANDON** (0.2003 < 0.80). The margin is large enough that no defensible
  band revision could reverse it. The required S of 3.1 is three times the band's generous upper
  edge.
- **ABANDON means:** `PTMS-G-PTSQ` is **permanently closed as specified**, including every
  variant in §14. Changing only the offsets `(4, 2)`, the threshold, the leg set (short-only,
  long-only), `κ`, `Q`, the strike rule, the clock, or the metric (to `rank_ic`) is the same
  hypothesis and is **barred**, not a successor. **TRAIN and HOLDOUT receive no read**, so both
  windows stay unspent on the options store for any genuinely different Family G hypothesis.
- **PROCEED would mean** only "not provably infeasible". It would not authorize construct code or a
  TRAIN read, and it would say nothing about fees or drawdown.
- **The structural finding the operator should weigh.** HOLDOUT's 0.673 years caps *every*
  single-underlying, one-P&L-per-cycle Family G hypothesis at `ncp = 0.82·S`. Whatever the
  construct, clearing 0.80 needs S ≥ 3.1, or a HOLDOUT of ≥ 6 years at S = 1. The endpoint is
  frozen, so calendar time cannot be the lever inside this research. Whether Family G should close
  at P3 or be re-scoped is the operator's decision. This document does not change either window.

---

## 14. Degrees of freedom

### 14.1 Declared a-priori choices (made without outcome data)

| # | Choice | Value | Basis |
|---|---|---|---|
| 1 | Underlying | NIFTY | Only certified underlying (not a choice) |
| 2 | Construct family | #1 √-time ratio | §3.1, non-outcome grounds |
| 3 | Anchor offset | `t(4)` | Ladder spacing (§3.3) |
| 4 | Formation offset | `t(2)` | Outcome-horizon reasoning (§3.3) |
| 5 | Clock | Trading sessions | Thursday/Tuesday invariance (§8) |
| 6 | Strike rule | `argmin \|C−P\|`, ties lower | ATM definition without spot |
| 7 | Price field | `close`, traded rows only | Only per-contract daily price in store |
| 8 | Threshold | `R ≥ 1` | Implied by construct |
| 9 | Sign mapping | `R ≥ 1` ⇒ short | Overreaction mechanism (§2) |
| 10 | Legs | Overlay (short and long) | VRP cannot manufacture a pass (§2) |
| 11 | Normalization | Per `Π_f` | Unit-free outcome across eras |
| 12 | `κ`, `Q` | 1.0 %, 75 | Cost convention, not fitted |
| 13 | VOID threshold | 80 % | Convention |
| 14 | Test | One-sided t on mean `z`, α = 0.05 | Standard |

**Fitted parameters: zero. Searched parameters: zero.** The design has 14 declared choices. The
honest reading is that choices 3, 4, 9 and 10 are the ones a data-snooper would have tuned. They
are frozen here, before any read, and §13.7 bars revisiting them.

### 14.2 Secondary analyses (descriptive, cannot pass)

- **S1:** short-only conditional (`s ∈ {+1, 0}`): reported to show how much of any effect is
  unconditional VRP.
- **S2:** difference of mean gross `g` between `R ≥ 1` and `R < 1` cycles, with a permutation
  p-value.

### 14.3 Robustness variants (cannot rescue)

- **R1:** offsets `(3, 1)`
- **R2:** calendar-day clock in place of sessions
- **R3:** `κ = 3.0 %`
- **R4:** Newey–West (lag 1) standard error in place of simple t
- **R5:** HOLDOUT truncated to FTD ≤ 2026-08-31 (removes O-3 overlap)

---

## 15. Known failure modes

1. **Power (§13).** Near-certain RFA ABANDON at n = 35.
2. **Weekend relocation.** Thursday expiry: `t(4)` = Friday, `t(2)` = Tuesday, so the weekend sits
   in the **construct** interval. Tuesday expiry: `t(4)` = Wednesday, `t(2)` = Friday, so the
   weekend sits in the **holding** interval. The session clock treats the weekend as zero variance
   while option prices decay across it. This biases `R` upward in TRAIN and gross short `g` upward
   in HOLDOUT. It is a window-comparability threat that R2 exposes but cannot resolve.
3. **Non-synchronous closes.** `close` is last trade per contract; CE and PE last trades can be
   minutes apart, which adds noise to `F` and so to `R`. This is attenuating, not biasing, for a
   liquid ATM near-expiry pair.
4. **Liquidity composition shift.** Traded share 34.1 % → 58.8 % between windows. SEBI's 2024
   rationalization to one weekly per exchange also concentrated NIFTY weekly volume. `K*` on
   thinner TRAIN chains may sit further from the true forward.
5. **Settlement semantics unverified** at intrinsic level (§5). STOP condition.
6. **Exercise STT unmodelled** in `fees.py` (§9). The long leg is understated in cost until fixed.
7. **Mid-HOLDOUT STT change** (2026-04-01).
8. **Orphaned listings** (§8). Handled by the ladder rule, but the certification's description was
   incomplete.
9. **EOD fill optimism.** Only `κ` stands between `close` and a real fill.
10. **Gamma at expiry.** Two sessions to settlement puts `z` near-binary for the short leg. The
    distribution is fat-tailed and one-sided t is fragile at n = 35. R4 only partially addresses it.
11. **Observation-shaped exposure** (§11.2), pending an operator ruling.
12. **Clustering sign** (§2). The data may favour the opposite mechanism; that is an ABANDON, not
    a finding to re-register.

---

## 16. Falsification

| Outcome | Verdict | Consequence |
|---|---|---|
| RFA power < 0.80 | **ABANDON** | Closed as specified (§13.7). Expected |
| Settlement-semantics check fails (§5) | **STOP** | Outcome not certified; no TRAIN read |
| Eligible cycles < 80 % in either window | **VOID** | Closed as specified; any re-spec increments multiplicity |
| TRAIN `mean(z) ≤ 0`, or one-sided p ≥ 0.05 | **ABANDON** | HOLDOUT unread |
| TRAIN significant with the **opposite** sign | **ABANDON** | **No flipped-sign successor** (clustering is not a new hypothesis) |
| HOLDOUT one-sided p ≥ 0.05 | **FAIL, closed** | No re-read, no extension of the endpoint |
| HOLDOUT passes | Hypothesis survives | Only then do S1/S2/R1–R5 get reported. Promotion is a separate, operator-owned step |

A robustness variant passing where the primary failed changes nothing.

---

## 17. What is NOT tested

- Index **direction**, trend, or any signed forecast of NIFTY
- Open interest, PCR, max pain, OI change, IV skew or term structure
- India VIX, NIFTY spot, futures or basis, realized volatility: **none is used, none is needed**
- Intraday option or index data
- BankNifty, FINNIFTY, stock options
- Any strike other than the formation ATM, and any expiry other than the cycle's settling weekly
- Delta hedging, early exit, stops, rolls
- Position sizing, portfolio construction, capacity, drawdown
- Gann angles, square-of-nine counts, swing symmetry, range squares (§3.1 families 2–5)
- Windows 2016–2020 (Skew-spent) and 2023–2025 (MSRP-spent)
- Any HOLDOUT date after 2026-09-11

---

## 18. Preregistration freeze hash procedure

**Not executed by this document.** The operator performs it; each step is append-only.

1. **Operator review and approval** of this document as committed. Any change before freeze is
   made by a new commit, never after.
2. **Spec digest.** `sha256sum docs/reports/ptms/PTMS_FAMILY_G_P3_HYPOTHESIS_DEFINITION.md`
   at the approved commit. Record the commit hash and the SHA-256.
3. **Declaration file.** Create `governance/rfa/declarations/ptms_g_ptsq.py` with exactly the §13.1
   values. Its `prior_exposure` and `sharpe_provenance` strings cite the spec's commit hash and
   SHA-256 from step 2.
4. **Declaration digest.** `governance.rfa.declaration.digest_of(path)`, the SHA-256 over the
   whole declaration file. This is the RFA freeze hash. Bands are frozen at this digest.
5. **Register append.** One row in `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` with the
   hypothesis ID, both digests, level `meta` (P3 design), and the §11.4 exposure of this document.
6. **Run the RFA gate** (`scripts/rfa/run_rfa.py`) against the frozen declaration. The report
   records the declaration digest.
7. **Immutability.** Any edit to the spec or declaration after step 4 produces a new digest and so
   a **new hypothesis**. It is not a revision, and it increments programme multiplicity. On
   ABANDON, both files are preserved as a record, not deleted.

---

*STOP. P3 ends here. No RFA gate run, no declaration frozen, no construct code, no TRAIN, no
HOLDOUT.*
