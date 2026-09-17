# PTMS — GF-10 Final Mechanical Specification (DRAFT)

**Status: DRAFT — NOT A FREEZE.** No hash is issued. Nothing here authorizes execution. No code has
been written or changed. No market data, outcome, signal artifact or backtest was read. No parameter
was optimized, and no definition was chosen by looking at results.

**Construct label:** GF-10 = **GANN-FAITHFUL SOURCE CONCEPT + EXPLICIT OPERATOR/RESEARCH CONVENTIONS.**
It is **not** "Gann's exact rule". Every mechanical element below carries one of four classes, and the
classes are never merged:

| Code | Class |
|---|---|
| **GE** | GANN EXPLICIT — stated in the verified text |
| **GSI** | GANN STRONG INFERENCE — follows closely from the text or Gann's worked examples, but is not stated in the rule |
| **OD** | GANN SILENT — OPERATOR DECISION (the locked decisions OD-1 … OD-10, or earlier rulings) |
| **RD** | OUR RESEARCH DESIGN — required by the test architecture; no Gann basis claimed |

**Inputs this draft transcribes (not re-derived):**
- The GF-10 element matrix (2026-09-16 audit, delivered in session).
- Operator decisions OD-1 … OD-10 (2026-09-17).
- The ruling register `PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md`: R-1, R-2, R-5, R-10, R-11 to R-14, plus the G-1, G-2 and G-3 blocks.
- The completion memo `PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md` (§5, §7.3, §8.2).
- The faithful definition `PTMS_GANN_FAITHFUL_CONSTRUCT_DEFINITION_2026-09-14.md` (§12.1, §12.4).
- The freeze checklist `PTMS_GANN_STAGE1_FREEZE_CHECKLIST_2026-09-15.md`.

> **Headline:** the specification cannot be frozen as it stands. **Seven conflicts (C-1 … C-7, §14.1)**
> between the locked ODs and accepted rulings need an operator ruling. The three OD-10 conflicts
> (C-1 … C-3) decide whether the construct can be tested under the accepted design at all.
> **Fourteen groups of mechanical items (OPEN-1 … OPEN-14, §14.2) remain open, plus five documentation corrections (§14.3).**

---

## 1. Purpose and scope

1. Turn the completed GF-10 source audit and OD-1 … OD-10 into a mechanically reproducible
   specification.
2. Make every remaining underspecification explicit, so that once those items are ruled an
   implementer has no substantive interpretation left to make.
3. Record where the locked decisions conflict with accepted rulings, without resolving the conflicts.

**In scope:** the GF-10 score, the event, the trend-episode logic, the time and price legs, the
bull/bear mirror, the interface to the O-R10 outcome, and the interface to the statistical layer.

**Out of scope:**
- Any empirical read.
- The choice of any OPEN value.
- Editing the ruling register, the definition, the memo or the claim register. Their stale text is
  listed in §14.3.
- GF-1 and GF-4T/R8, except where GF-10 shares ruled machinery (K3, O-R10, T_c, the surrogate).

---

## 2. Source basis

**Source:** W. D. Gann, *45 Years in Wall Street* (1949). The operator PDF has SHA-256 `183ed235…`
(full identifier in the claim register §27.1). It was re-rendered and re-read from page scans in this
session. Exact wording is in the scans and in the VERIFIED claim-register rows. This draft uses only
short fragments.

| Locator | Content (fragment or paraphrase) | Register |
|---|---|---|
| p. 10 | Rule 8 "Time Periods"; time can over-balance price | Δ2-01 context |
| p. 11 | Market Over-Balanced paragraph. "Averages or individual stocks"; over-balance after "a considerable period of Time"; the greater the time, the greater the correction | Δ2-01 |
| p. 11 | Bull time clause: a decline's time period **exceeds** the time period of **a previous decline** → "indicates a change in trend" | Δ2-01 |
| pp. 11–12 | Bull price clause: price breaks a greater number of points than **the previous decline or reaction** → market "Over-Balanced", change "is taking place" | Δ2-02 |
| p. 12 | "Reverse this rule in a Bear Market". Bear precondition: declining "for a long period of Time". Bear time clause: **"the first time"** a rally exceeds the time period of **a previous rally** → trend changing, "at least temporarily" | Δ2-01 |
| p. 12 | Bear price clause: **"the first time"** price rallies more points than **a previous rally** → change "has started" | Δ2-02 |
| p. 12 | "The Time change is more important than reversal in price"; apply all of the rules at the time these reversals take place | Δ2-02 |
| p. 12 | Rule 9: higher tops and higher bottoms mean the main trend is up; keep high/low charts | (S9 basis) |
| p. 13 | Rule 10: breaking the last low on the 3-Day Chart indicates a change in trend, at least temporarily; in a bear market, crossing the last upswing top is the first signal | Δ2-11 |
| p. 39 | Keep in mind the greatest time period / greatest correction | Δ2-04 |
| pp. 60–61 | Averages adjusted for dividends and split-ups still give the trend; 3-day moves are the record, with 1- and 2-day moves "sometimes" used near extremes; moves "based on calendar days" | Δ2-10, Δ2-16, Δ3-01 |
| p. 62 | The longer the elapsed time when a top is crossed or a bottom broken, the greater the move | Δ2-15 |
| p. 63 | 3-Day Chart construction rule; worked example: last high 21 Apr 1942 to extreme low 28 Apr, called a 7-day decline of less than 6 points | Δ2-10 |
| pp. 66–67 | Gann's own 3-Day record departs from the strict rule in ≥ 7 of 61 swings (1912–14) | Δ3-02 |

---

## 3. Source-vs-operator boundary

Rules that apply to the whole specification:

1. **Rule 8 does not name a chart, a swing detector, a market-state test, a time unit, a clock, an
   outcome or a horizon.** Every such element here is OD or RD.
2. **"A previous" vs "the previous" vs "greatest".** The bull time clause and both bear clauses say
   *a previous*. The bull price clause says *the previous*. p. 39 separately names the *greatest* time
   period as a reference quantity. **OD-1's "greatest qualifying previous" is an operator decision
   informed by p. 39. It is not Rule 8's wording.**
3. **"First time"** is GE in both bear clauses and absent from both bull clauses. Applying it to the
   bull side (OD-6) is OD.
4. **The bear precondition** in the text is a long decline in time. **S9 bear (OD-3) is an
   operator/research convention for mechanical symmetry.** It is not Gann's literal bear condition.
5. **"Decline or reaction"** appears only in the bull price clause. The bull time clause says only
   *decline*. Both bear clauses say only *rally* and have no "reaction" counterpart. OD-2 preserves
   the distinction, but its mechanics are OPEN (§14.2 OPEN-2).
6. **The outcome (Rule 10 / O-R10)** is a separate Gann rule used as a research outcome (R-2, RD).
   Rule 8 itself says only that a change in trend is indicated, taking place or started.
7. **Time over price** is GE. Turning it into the statistic T(time) − T(price) is RD (R-10), and its
   p-value is OPEN (G-4).

---

## 4. Locked operator decisions OD-1 … OD-10

These decisions are transcribed as given. The **Relation to accepted rulings** column records
interactions only and does not change any decision.

| OD | Decision (locked) | Class | Relation to accepted rulings |
|---|---|---|---|
| **OD-1** | Time leg: compare against the **greatest qualifying previous** decline (bull) or rally (bear) | OD (informed by p. 39, Δ2-04; **not** Rule 8 wording) | **Supersedes R-5's primary comparison ("immediately preceding")** — conflict C-5. Lookback universe OPEN-1; qualifying set OPEN-2 |
| **OD-2** | Preserve "decline **or reaction**"; recognize Gann's 1-, 2- and 3-day move/reaction framework rather than equating reaction with K3 | OD | Detector OPEN-2. Touches R-1 row 7 (exception not mechanized) and G-2(b) eligibility ("K3 decline") — conflict C-4 |
| **OD-3** | Bear condition = **S9 bear** | OD / RD (mechanical symmetry) | Consistent with G-2(b). Gann's "declining for a long period of Time" is documented separately and is not operationalized |
| **OD-4** | **First exceedance per trend episode** | OD | New. R-5's cell had no per-episode limit |
| **OD-5** | A trend episode **resets on S9 state reversal or cessation of the operative S9 state** | OD | New. S9 imported unchanged (§11) |
| **OD-6** | First-exceedance applies **symmetrically** to bull and bear | OD (GE for bear only) | New |
| **OD-7** | The event is the **first objectively observable date/bar** on which the threshold is crossed; **not** deferred to week-end, to the move's completion, or to the outcome | OD | Supersedes the event-date wording of R-5's cell ("score = 1 at week-end *t*") — conflict C-6 |
| **OD-8** | Price endpoint = **running extreme**. Decline magnitude = starting high − lowest price so far. Rally magnitude = highest price so far − starting low. Trigger when running magnitude **strictly exceeds** the reference | OD (GSI basis: p. 63 high/low measurement) | Refines R-10's price-overbalance score. The price-leg comparator is not set by OD-1 — OPEN-9 |
| **OD-9** | **Strict `>`**; equality does not trigger | OD (GE: "exceeds", "greater") | Consistent with R-1's strict-inequality convention |
| **OD-10** | Evaluate at the **finest consistently available historical resolution — currently 1-minute bars** | OD / RD (Gann specified no clock) | **Conflicts C-1, C-2 and C-3** |

---

## 5. Formal GF-10 construct

### 5.1 Layered architecture (four separate clocks)

GF-10 uses five separate objects. They must not be merged.

| Layer | Object | Clock | Governing source |
|---|---|---|---|
| **L1 — Daily state** | K3 line state and swing points (R-1); S9 state (§12.1); O-R10 reference swing points | Completed NSE session (daily H/L) | R-1, §12.1, G-2 |
| **L2 — Move structure** | Current counter-move and the set of qualifying previous moves (declines, reactions, rallies) | OPEN-2 (the 1/2/3-day framework is daily; its intraday observability is OPEN) | OD-2 |
| **L3 — Event clock** | First observable bar on which a leg's threshold is crossed | 1-minute bars (OD-10), **blocked by C-1 to C-3** | OD-7, OD-8, OD-9, OD-10 |
| **L4 — Formation grid** | Per-stock score sampled for the cross-sectional IC | Last session of each calendar week (memo §7) | R-14 / memo §8.2 |
| **L5 — Outcome window** | O-R10 binary outcome | 5 sessions (R-2); **start anchor OPEN-12** | R-2, G-2(b) |

### 5.2 Symbols

| Symbol | Meaning | Status |
|---|---|---|
| *i* | Stock (PIT N100 member) | RD (memo §7) |
| τ | An L3 evaluation instant (a 1m bar, subject to OPEN-5 and OPEN-6) | OD-10 / OPEN |
| *d*(τ) | NSE session containing τ | RD |
| S9(*i*, τ) ∈ {BULL, BEAR, NONE} | S9 state visible at τ (visibility rule OPEN-3c) | OD-3 / R-1 import |
| E(*i*, τ) | The trend episode containing τ (§11) | OD-5 |
| M_cur(*i*, τ) | Current counter-move: a decline in BULL, a rally in BEAR | OD-2 / OPEN-2, OPEN-4 |
| (t_S, P_S) | Causal start of M_cur: timestamp and price (high for a decline, low for a rally) | OPEN-4 |
| Q_T(*i*, τ) | Set of qualifying previous moves for the time leg | OD-1 / OPEN-1, OPEN-2 |
| Q_P(*i*, τ) | Set of qualifying previous moves for the price leg | OPEN-9 |
| dur(M) | Duration of a completed move | GSI (calendar days, high → low) / OPEN-8 at 1m |
| mag(M) | Points of a completed move (start extreme to end extreme) | GSI / OPEN-9 |
| R_T = max_{M∈Q_T} dur(M) | Time reference | OD-1 |
| R_P | Price reference | OPEN-9 |
| el(τ) | Elapsed time of M_cur from t_S to τ | R-5 ("to *t*") / OPEN-8 |
| run(τ) | Running magnitude: P_S − min low over (t_S, τ] for a decline; max high over (t_S, τ] − P_S for a rally | OD-8 / OPEN-5 |
| ev_T(*i*, E), ev_P(*i*, E) | Time-leg and price-leg event timestamps in episode E, or null | OD-4, OD-7 |
| s_T(*i*, w), s_P(*i*, w) | Binary scores at formation week *w* | OPEN-11 |
| y(*i*, w) | O-R10 binary outcome | R-2, G-2(b), OPEN-12 |

### 5.3 Construct statement

For stock *i* in episode E with operative S9 state σ ∈ {BULL, BEAR}:

- The **time-leg event** is the first τ in E at which, while *i* is in a qualifying current
  counter-move, **el(τ) > R_T** holds on an observable bar (OD-1, OD-4, OD-7, OD-9).
- The **price-leg event** is the first τ in E at which **run(τ) > R_P** holds on an observable bar
  (OD-4, OD-7, OD-8, OD-9; R_P is OPEN-9).
- **At most one event per leg per episode** (OD-4). Whether the two legs keep independent
  first-exceedance latches is OPEN-7b.
- The **GF-10 primary score** is the time leg (R-5, R-10). The price leg exists only as the
  specificity contrast (R-10, RD).

---

## 6. Bull implementation (σ = BULL)

| # | Element | Specification | Class |
|---|---|---|---|
| B1 | Eligibility | S9(*i*, τ) = BULL (OD-3 mirror of the Rule 9 basis) and *i* is in a qualifying current decline **or reaction** (OD-2). G-2(b) text says "S9 bull + **K3 decline**" — see C-4 | OD / RD; C-4 |
| B2 | Current move | Decline or reaction per the OPEN-2 detector; start = its starting high (OPEN-4) | OD-2; OPEN-2, OPEN-4 |
| B3 | Time comparator | Greatest duration among qualifying previous **declines** in the OPEN-1 universe. Whether reactions qualify for the time leg is OPEN-2g (the bull time clause says "decline" only) | OD-1; OPEN-1, OPEN-2g |
| B4 | Time trigger | el(τ) > R_T, strict | GE (exceeds) + OD-9 |
| B5 | Price comparator | "decline or reaction" (GE). Greatest vs immediately preceding vs other: OPEN-9 | GE / OPEN-9 |
| B6 | Price trigger | P_S − min low over (t_S, τ] > R_P, strict | OD-8, OD-9 |
| B7 | "First time" | Applied by OD-6 (not in the bull text) | OD |
| B8 | Strength wording | Bull time "indicates a change in trend"; bull price change "is taking place". No "at least temporarily" in the bull clauses | GE (recorded, not operationalized) |
| B9 | Outcome direction | Break of the last K3 swing low (G-2(b)), anchored on the **last completed swing direction**. **Not** the contemporaneous K3 line state used for GF-1/GF-4T/R8 | RD (G-2(b), transcribed) |

## 7. Bear implementation (σ = BEAR)

| # | Element | Specification | Class |
|---|---|---|---|
| R1 | Eligibility | S9(*i*, τ) = BEAR (OD-3) and *i* is in a qualifying current rally. **Gann's bear precondition is "declining for a long period of Time". It is recorded here and not operationalized; S9 bear is not that condition** | OD / RD; C-4 |
| R2 | Current move | Rally per OPEN-2; start = its starting low (OPEN-4). Whether 1- and 2-day rallies count (the text has no bear "reaction") is OPEN-2h | OD-2 mirror / OPEN |
| R3 | Time comparator | Greatest duration among qualifying previous **rallies** in the OPEN-1 universe | OD-1; OPEN-1 |
| R4 | Time trigger | el(τ) > R_T, strict | GE (exceeds) + OD-9 |
| R5 | Price comparator | "a previous rally" (GE); selection OPEN-9 | GE / OPEN-9 |
| R6 | Price trigger | max high over (t_S, τ] − P_S > R_P, strict | OD-8, OD-9 |
| R7 | "First time" | **GE** in both bear clauses. Mechanized as first per episode (OD-4). The textual scope of "first time" (first in a long decline, per rally, or per episode) is not stated by Gann; per-episode is OD | GE wording / OD mechanics |
| R8 | Strength wording | Bear time "at least temporarily"; bear price change "has started" | GE (recorded, not operationalized) |
| R9 | Outcome direction | Cross of the last K3 swing top within the horizon (G-2(b)) | RD |
| R10 | Mirror | "Reverse this rule in a Bear Market" is GE for mirroring. **Pooling bull and bear into one IC is RD (G-2(b))** | GE / RD |

---

## 8. Time-leg definition

| # | Element | Specification | Class |
|---|---|---|---|
| T1 | Quantity | Duration of the current counter-move compared with a previous counter-move's duration | GE |
| T2 | Comparator | max over the qualifying set (OD-1) | OD |
| T3 | Unit (completed moves) | Calendar days (R-9 / §12.1 for 1949 rules; p. 61 states calendar days for 3-day moves) | GSI for Rule 8 |
| T4 | Endpoints (completed moves) | From the high's date to the low's date (decline), mirror for a rally (p. 63 "7-day decline" example; memo §7.3) | GSI |
| T5 | Endpoints (current move) | From t_S to τ (R-5 cell "to *t*") | OD (R-5) |
| T6 | Resolution under a 1m clock | Integer calendar-day dates, fractional calendar time, or session-minute time? A calendar-day threshold crosses at midnight, which is never a trading bar | **OPEN-8** |
| T7 | Timestamp of a move's extreme | Date of the extreme bar (daily) or the minute of the extreme (1m)? For ties, first or last occurrence? | **OPEN-8b** |
| T8 | Strictness | `>` | GE + OD-9 |
| T9 | Qualifying set | Declines only, or declines and reactions (bull); rallies of which size (bear) | **OPEN-2g/h** |
| T10 | Lookback universe | — | **OPEN-1** |
| T11 | No qualifying previous move | Stock ineligible, score 0, or other? | **OPEN-1c** |

## 9. Price-leg definition

| # | Element | Specification | Class |
|---|---|---|---|
| P1 | Quantity | Points of the current move compared with points of a previous decline-or-reaction (bull) or rally (bear) | GE |
| P2 | Current magnitude | Running extreme (OD-8) | OD |
| P3 | Completed-move magnitude | Start extreme to end extreme on high/low prices | GSI (p. 63) |
| P4 | Comparator selection | Immediately preceding (R-10 wording), greatest (the OD-1 analogue), or other | **OPEN-9** |
| P5 | Unit | Points on the ratio-adjusted as-of-*t* series (R-13, §12.1). Under OD-10 the 1m store is back-adjusted to the current basis (C-3) | RD / C-3 |
| P6 | Strictness | `>` | GE ("greater") + OD-9 |
| P7 | Role | Specificity contrast only; not a primary score | RD (R-10) |
| P8 | Relation to time leg | For T(time) − T(price) to compare like with like, the qualifying set, universe and episode latch must match, or any difference must be declared | **OPEN-9** (coupled to G-4) |

---

## 10. Event / flag definition

| # | Element | Specification | Class |
|---|---|---|---|
| F1 | Event | First observable bar in the episode on which the leg's strict threshold holds while eligible | OD-4, OD-7, OD-9 |
| F2 | Event date | *d*(τ_event), the NSE session of the event bar | OD-7 |
| F3 | Event timestamp | Bar start, bar end, or first instant the crossing becomes knowable? Depends on the bar-labelling convention and observability rule | **OPEN-6** |
| F4 | Not deferred | Not to week-end, move completion or outcome | OD-7 |
| F5 | Detectability lag | The event cannot come before the moment the current move is itself detectable as a move (for example, a 3-day down-switch confirms only at the close of its 3rd session) | **OPEN-4b** |
| F6 | State visibility | S9 and K3 at τ: the state as of the last completed session close, or updated intraday? | **OPEN-3c** |
| F7 | Latch | Once ev_T(*i*, E) is set, no further time-leg event may be emitted until E ends | OD-4 (§11 guarantees) |
| F8 | Score mapping | How events become the weekly score s(*i*, w) | **OPEN-11** |

---

## 11. Trend-episode state machine

**S9 import, unchanged (§12.1):** BULL iff the last two K3 tops **and** the last two K3 bottoms are
both rising; BEAR iff both are falling; otherwise NONE. K3 is imported unchanged from R-1 and memo §5
rows 1–13.

**Episode definition (OD-5).** An episode is a maximal contiguous run of L1 sessions with the same
operative S9 state σ ∈ {BULL, BEAR}. It ends on any change of S9(*i*): BULL→BEAR, BULL→NONE,
BEAR→BULL or BEAR→NONE. A return to the same state after NONE starts a **new** episode, because
"cessation" ends the old one. *Operator to confirm this reading of "cessation" (OPEN-3d).*

```
States: NONE | BULL(E, latch_T, latch_P) | BEAR(E, latch_T, latch_P)

on S9 update at session close d (visibility per OPEN-3c):
  if S9_new != current σ:
      close episode E (record end = d)
      if S9_new in {BULL, BEAR}: open new E', latch_T := False, latch_P := False
      else: go to NONE
on L3 bar τ while BULL/BEAR:
  if not eligible(i, τ): continue          # OPEN-2, OPEN-4, C-4
  if not latch_T and el(τ) > R_T(τ):  emit ev_T; latch_T := True
  if not latch_P and run(τ) > R_P(τ): emit ev_P; latch_P := True   # latch independence: OPEN-7b
```

**Guarantees the implementation must provide (OD-4, OD-5, OD-6):**

| G | Guarantee |
|---|---|
| E1 | At most one time-leg event per (stock, episode) |
| E2 | At most one price-leg event per (stock, episode) (if the latches are independent — OPEN-7b) |
| E3 | Latches reset only when an episode opens. Not at a move's end, a week-end, a CA, a data gap or a PIT membership change (the treatment of those is OPEN-7c) |
| E4 | Bull and bear follow the identical latch logic (OD-6) |
| E5 | Latch state is a function of past bars only (causal); replaying a prefix of the data reproduces identical events |

**Consequence to be confirmed by the operator (not a new interpretation):** under OD-4 and OD-5
literally, once a time-leg event fires, no later counter-move in the same S9 episode can produce
another GF-10 time event, however many further declines occur before S9 changes (OPEN-7a).

---

## 12. Outcome definition (research design; Rule 8 does not prescribe it)

Transcribed from R-2 and G-2(b) with no further choice:

- **Bull:** outcome = 1 iff the last K3 swing low is penetrated intraday within the next 5 sessions.
- **Bear:** outcome = 1 iff the last K3 swing top is penetrated intraday within the next 5 sessions.
- Any penetration counts. The basis is intraday high/low. The outcome is binary. Report wording:
  "minor change in trend".
- An O-R10 event opposite to the construct's direction is outcome **0**.
- S9 NONE stocks, and stocks not in the required counter-move, are **ineligible, not zero**.
- GF-10's outcome anchors on the **last completed swing direction**. GF-1 and GF-4T/R8 use the
  **contemporaneous K3 line state**. The two anchors must stay distinct (G-2 recorded observation).

**OPEN at the interface with OD-7:**
- **OPEN-12a — Window start.** Which "next 5 sessions"? After the formation week-end *w* (memo §7), or
  after the event timestamp?
- **OPEN-12b — Event-session inclusion.** If anchored to the event, does the remainder of the event
  session count as session 1?
- **OPEN-12c — Reference swing.** The "last K3 swing low/top" as of when: formation, event, or last
  completed session before the event?
- **OPEN-12d — Coincidence.** An outcome penetration on the same bar as, or before, the event bar.

---

## 13. Statistical layer (imported; nothing here is new)

| Element | Specification | Source | Status |
|---|---|---|---|
| Statistic | T_c = mean over formation weeks of the per-date cross-sectional Spearman IC of score vs O-R10 | Memo §8.2, R-14 | Ruled |
| Pooling | Bull and bear observations in one per-date IC; m = 3 | G-2(b) | Ruled |
| Surrogate leg | p_sur from B = 1999 synchronized stationary block-bootstrap panels of **daily** bar vectors (ln H/C₋₁, ln L/C₋₁, ln C/C₋₁), mean block 20 sessions, real calendar, identical code | R-14 | Ruled; **C-2** |
| Specificity leg | T(time) − T(price); one-sided p from the surrogate joint distribution | R-10 | **p formula OPEN (G-4)**; comparator symmetry OPEN-9 |
| Pass rule | Confirmatory IUT: p_sur ≤ α **and** specificity ≤ α; α = 0.05/3 one-sided; screen kill on surrogate leg only | Memo §8.2, §10; R-12 | Ruled |
| Specificity failure | Retired; no confirmatory test | G-1 | Ruled |
| Missing bars, seed, size check | — | G-5, G-8, G-9 | OPEN |
| Burn-in, minimum names | — | G-6 | OPEN |
| CA exclusion windows | — | G-7 | OPEN |
| Screen | Non-confirmatory, 2011-03-25 → 2022-12-30, only after freeze and the G-S1 append | R-12 | Accepted in principle; **C-1** |

---

## 14. Remaining OPEN mechanical items

### 14.1 Blocking conflicts (operator ruling required; not resolved here)

| ID | Conflict | Evidence | Operator question |
|---|---|---|---|
| **C-1** | **OD-10 vs the admissible windows.** The 1m equity store starts **2023-01-02** (CLAUDE.md data layout; PTMS 1m certificate 2023-01-02 → 2026-09-11). The only authorized read, the R-12 screen, is **2011-03-25 → 2022-12-30**, which has **no 1m data**. The span with 1m data was found **signal-spent** by the R-11 audit (formal freshness ruling pending) | CLAUDE.md; R-11 status row; R-12 | Which evaluation clock applies to which window? Does "finest *consistently* available" mean daily for 2011–2022? Is a mixed-resolution construct admissible? |
| **C-2** | **OD-10 vs the R-14 surrogate.** The accepted null resamples **daily** bar vectors and generates no intra-session path, so a 1m-timestamped event has no null distribution under the accepted surrogate | Memo §8.2; R-14 | Re-specify the surrogate (a new R-14 element), or restrict the event clock to daily for the surrogate-tested construct? |
| **C-3** | **OD-10 vs the R-13 substrate and price basis.** R-13 certifies N100 **EOD** with an as-of-*t* ratio-adjusted basis. The 1m store is a different certified substrate: native start-labelled clock, `is_synthetic = FALSE` required, 4 GAP sessions, CAS carry-forward bars from 2026-08-03, special sessions per `SPECIAL_SESSIONS`, HDFC 99/100 exception, and a back-adjusted-to-current basis. **Never join 1m and bhavcopy prices across a CA.** L1 (daily K3/S9) and L3 (1m) would read from different stores on different bases | R-13; PTMS substrate certificate §5; CLAUDE.md pitfalls | Which store feeds L1 and which feeds L3? Is a single-basis derivation (daily bars built from 1m, or vice versa) required? |
| **C-4** | **OD-2 vs R-1 row 7 and G-2(b).** R-1 / memo §5 row 7: the 1- and 2-day exception is discretionary, and "any mechanized exception rule would be an invention (Arm 2)". G-2(b) eligibility is "S9 bull + **K3 decline**", with the recorded observation that the K3 line is DOWN for a bull-eligible stock. OD-2's 1- and 2-day reactions can occur while the K3 line is UP | Memo §5 row 7; Δ3-01, Δ3-02; G-2 block | Is the OD-2 detector (a) a new move detector distinct from K3 (and on what basis Gann-faithful rather than Arm 2), or (b) a reopening of R-1 row 7? How is G-2(b)'s "K3 decline" eligibility restated? |
| **C-5** | **OD-1 supersedes R-5's primary comparison.** R-5 RULING row, memo §7.3 row 3 and definition §12.4 row 5 all pin "immediately preceding", with greatest as robustness | R-5; memo §7.3; def. §12.4 | Record the supersession (as R-5 did for ruling 7). Does "immediately preceding" become the off-path robustness variant? (checklist §5 consolidation) |
| **C-6** | **OD-7 vs R-5's cell and the weekly formation.** R-5's cell scores "at week-end *t*". OD-7 fixes the event intra-period, but T_c remains a weekly cross-sectional statistic | R-5; memo §7, §8.2 | Record the supersession of the event-date wording. The score mapping is OPEN-11 |
| **C-7** | **OD-4/OD-5 vs R-5's "before any up-switch".** R-5 bounds the score by the current decline ("before any up-switch"). OD-4/OD-5 bound events by the S9 episode | R-5 | Does a move-level termination condition still apply before the event (OPEN-4c)? |

### 14.2 OPEN items

**OPEN-1 — Time-comparator lookback universe** (OD-1 fixes "greatest"; the universe is not fixed).
Candidates to be ruled between, without preference:
- (a) the stock's entire available history (left-censored at data start or listing);
- (b) the current trend episode only;
- (c) a fixed calendar lookback (length to be stated);
- (d) history within the formation window or research window;
- (e) the current K3 major swing;
- (f) other.

Sub-items:
- **1b.** Is the universe measured at τ (expanding) or fixed at episode start?
- **1c.** What happens when the universe contains no qualifying move?
- **1d.** Are moves straddling the universe boundary included, and are left-censored moves at data
  start included?
- **Dependency:** OPEN-1 cannot be closed before OPEN-2, because "qualifying" is defined there.

**OPEN-2 — 1/2/3-day move/reaction detector** (OD-2). The source says 3-day moves are the record,
and 1- and 2-day moves are "sometimes" used near extremes (p. 61, p. 63). Gann gives no mechanical
rule. The following must be specified:
- **2a.** What constitutes a **1-day** reaction: a single session with a lower low than the prior
  session? lower high **and** lower low? relative to the running top or to the prior session?
- **2b.** What constitutes a **2-day** reaction (consecutive sessions, the same comparisons)?
- **2c.** What constitutes a **3-day** reaction: identical to the K3 down-switch (memo §5 rows 11–13),
  or a separate definition?
- **2d.** Are the "near extremes" / "very wide fluctuations" conditions part of the detector? If so,
  how are they defined? If not, the declared departure must be recorded (see C-4).
- **2e.** Overlap: how nested or overlapping reactions are handled (a 1-day inside a 2-day inside a
  3-day; consecutive reactions separated by one up session).
- **2f.** Transition: when a reaction grows into a larger move, whether it is re-labelled, how its
  start is kept, and whether the smaller labels are retracted.
- **2g.** Qualifying set per leg: for the bull time leg ("decline" only in the text), do reactions
  qualify? For the bull price leg ("decline or reaction"), which sizes qualify?
- **2h.** Bear mirror: the bear clauses say "rally" only. Are 1- and 2-day rallies recognized?
- **2i.** Predecessor selection among multiple qualifying moves, beyond "greatest" (OD-1). Tie-breaks
  when two moves have equal duration (irrelevant for the max value but relevant if a move identity is
  recorded).
- **2j.** Minimum size (points or %) for a reaction to qualify, or none.
- **2k.** Whether reactions are defined on daily bars only (L1/L2), or also on intraday bars.

**OPEN-3 — S9 mechanics to import explicitly** (S9 itself is not modified). The freeze document must
cite, not restate loosely:
- **3a.** The K3 parameters S9 depends on: memo §5 rows 1–13 (strict inequality, no gap handling,
  initialization, literal up/down switch asymmetry, day-over-day comparison, outside/inside days,
  exception not applied, confirmation at the 3rd session's close).
- **3b.** S9 inputs: the "last two" K3 tops and bottoms — **confirmed** swing points only, and the
  point at which the latest top or bottom enters the comparison.
- **3c.** Visibility: the S9 state seen by an intraday bar on session *d*. The close of *d*−1, or
  updated during *d* if a K3 switch confirms at *d*'s close?
- **3d.** "Cessation" (OD-5): confirm that BULL→NONE→BULL opens a new episode.
- **3e.** Initialization: no S9 state until two confirmed tops and two confirmed bottoms exist (burn-in
  interaction with G-6).
- **3f.** Equal consecutive tops or bottoms under S9 (neither rising nor falling → NONE?). This follows
  from "rising"/"falling", but the freeze must state it.

**OPEN-4 — Causal start of the current move.**
- **4a.** Which extreme is P_S: the K3 swing high confirmed by the down-switch; the highest high since
  the last qualifying low; the high preceding the detected 1- or 2-day reaction?
- **4b.** When the start becomes known (detection lag) versus the timestamp the clock counts from
  (retroactive to the extreme's own timestamp, per memo §5 row 4 "time counts run from the extreme's
  own date"). The event cannot precede detection.
- **4c.** Move termination: the condition that ends M_cur without an event (K3 up-switch? a new high
  above P_S? an OPEN-2 opposite move?), and whether a new move in the same episode then starts a fresh
  pre-event evaluation (C-7).
- **4d.** If price makes a new high above P_S before any detection, does the start move forward?
- **4e.** Ties: equal highs at the start (first or last occurrence).

**OPEN-5 — The exact 1-minute price observation** (only if C-1 to C-3 admit a 1m clock).
- **5a.** Fields: 1m `high`/`low` for running extremes; which field defines P_S and completed-move
  extremes (1m or daily; see C-3).
- **5b.** Missing bars: in-session gaps; the four certified GAP sessions; halts; sessions with no bars.
- **5c.** Timestamp convention: the native start-labelled clock resolved via
  `core/market/bar_labeling.py` (certificate obligation); how an end-labelled era would be handled if
  ever used.
- **5d.** Session boundaries: pre-open excluded or not; CAS (15:15 continuous end; auction print at
  15:28/15:29); `is_synthetic = TRUE` bars excluded; Muhurat and special sessions per
  `SPECIAL_SESSIONS`.
- **5e.** Observability within a bar: is a bar's high/low treated as knowable only at bar close, or at
  any instant within the bar? When one bar sets a new low and also contains the crossing, when is the
  crossing observable?
- **5f.** Intra-bar ordering: when one 1m bar makes both a new high above P_S and a new low, the order
  is unknown.
- **5g.** Price basis of the 1m series relative to L1 (C-3).

**OPEN-6 — Signal timestamp.** The event *date* is the session of the event bar (OD-7). The event
*timestamp* is not yet fixed: bar start label, bar end, or bar end plus a processing latency. The
timestamp from which the outcome window is measured (OPEN-12) must use the same convention.

**OPEN-7 — Stickiness and retrigger behaviour.**
- **7a.** Operator confirmation of the literal OD-4/OD-5 consequence (§11): one time-leg event per S9
  episode, regardless of later moves.
- **7b.** Are the time-leg and price-leg latches independent?
- **7c.** Latch behaviour across a data gap, a CA exclusion window (G-7), a PIT membership exit and
  re-entry, and window or burn-in boundaries. The rule must not create a new episode where S9 did not
  change, unless explicitly ruled.
- **7d.** Does a threshold still exceeded on later bars re-emit (no, per OD-4)? Does a crossing that
  reverses (price rebounds so run(τ) falls back below R_P) un-set the latch (no event retraction is
  implied by OD-4; to be confirmed)?

**OPEN-8 — Time unit at the event clock.**
- **8a.** Comparison of el(τ) with R_T: integer calendar days (date difference), fractional calendar
  time, or trading time?
- **8b.** Timestamps of completed-move extremes: date or minute; ties.
- **8c.** Under integer calendar days, a time crossing becomes observable only on the first bar of a
  session dated ≥ start date + R_T + 1. Confirm that this is intended, or rule otherwise.

**OPEN-9 — Price-leg comparator and contrast symmetry.** OD-1 applies to the time leg only. R-10 says
"preceding decline's points". State:
- **9a.** the price-leg comparator (immediately preceding, greatest, or other);
- **9b.** its lookback universe;
- **9c.** its qualifying set ("decline or reaction");
- **9d.** whether an asymmetric construction between the legs is accepted for T(time) − T(price), and
  how that is disclosed.

This is coupled to G-4.

**OPEN-10 — Bull/bear pooling (documentation, not a new decision).** The freeze document must state
all three:
- Gann's wording differs between bull and bear ("first time" and "at least temporarily" appear only in
  bear clauses; "reaction" appears only in the bull price clause; the bull price clause says "is taking
  place", the bear says "has started").
- Pooling is RD (G-2(b)).
- The bear "first time" is mirrored into bull by OD-6.

A per-direction descriptive breakdown is off the pass path, if listed in checklist §5.

**OPEN-11 — Score persistence on the formation grid.** Given an event timestamp, define s(*i*, *w*):
- (a) 1 only in the formation week containing the event;
- (b) 1 in every formation week from the event until the episode ends;
- (c) 1 from the event until the current move ends;
- (d) other.

Also:
- **11e.** The score at *w* when the stock is eligible and no event occurred (0), or not eligible
  (excluded — G-2(b)).
- **11f.** An event on the last session of a week, after the formation instant (the formation instant
  itself must be defined: the week's last session close?).

**OPEN-12 — Outcome window anchoring** (§12, OPEN-12a–d).

**OPEN-13 — Imported unresolved gaps** (by reference; none closes here): G-4 (contrast p), G-5
(missing-bar neighbourhood), G-6 (burn-in and minimum names), G-7 (CA exclusion windows), G-8 (seed),
G-9 (size-check inner draws and failure action); preconditions P-1 … P-5 (freeze checklist §6).

**OPEN-14 — Robustness set consolidation.** What replaces "greatest-prior as robustness" now that
greatest is primary (C-5)? Whether a daily-clock variant is listed. All off the pass path (checklist
item 12).

### 14.3 Documentation correction backlog (flagged only; no file edited)

| # | Document location | Defect |
|---|---|---|
| D-1 | Ruling register R-5 "Frozen if accepted" | Bear mirror recorded as S9 without documenting Gann's "declining for a long period of Time"; bear "first time" not represented. OD-3 and OD-6 now cover the specification, but the text should cross-reference them |
| D-2 | Ruling register R-10 | Price leg omits "or reaction" |
| D-3 | Definition §12.4 row 2 | "In an advancing market" is not in the clause; "the previous decline" where the time clause says "a previous" |
| D-4 | Claim register Δ2-02 | Paraphrase "A decline breaking …" changes the subject (the price); omits "or reaction"; does not show the bear clause's own "first time" / "has started" |
| D-5 | R-5 / memo §7.3 / def. §12.4 rows 4–5 | "Immediately preceding" primary is superseded by OD-1 (C-5); event-at-week-end superseded by OD-7 (C-6) |

---

## 15. Data requirements

| Layer | Requirement | Source / obligation |
|---|---|---|
| L1 | Daily high, low and close per stock per session; PIT N100 membership; NSE calendar (`nse_holidays`, 2012-11-11 artifact, 2016-04-19 check) | R-13 scoped EOD certification; C-3 |
| L1 basis | Ratio-adjusted as-of-*t* series; CA exclusion windows | R-13; G-7; external CA enumeration outstanding (P-2) |
| L2 | The same daily bars as L1 (unless OPEN-2k rules intraday) | OPEN-2 |
| L3 | 1m high/low (and close if needed) per stock, start-labelled, `is_synthetic = FALSE`, declared GAP sessions, special-session windows, CAS handling, HDFC 99/100 pin | PTMS 1m substrate certificate §5; **blocked by C-1 to C-3** |
| L4 | Formation calendar: last NSE session of each calendar week | Memo §7 |
| L5 | Daily intraday high/low for the 5 sessions after the anchor (OPEN-12) | R-2 |
| Surrogate | Daily bar vectors for the synchronized bootstrap | R-14; C-2 |
| Exposure | Screen only on 2011-03-25 → 2022-12-30, after freeze and G-S1 | R-12; R-11 |

---

## 16. Edge cases (each must have a ruled treatment before freeze)

| # | Case | Governing item |
|---|---|---|
| X1 | Time and price thresholds cross on the same bar | OPEN-7b (independent latches) |
| X2 | An event bar that also penetrates the O-R10 reference swing | OPEN-12d |
| X3 | S9 changes at the close of the session in which an event fired | OPEN-3c, OD-5 |
| X4 | The current move starts before episode start (a decline in progress when S9 turns BULL) | OPEN-4, OPEN-1b |
| X5 | No qualifying previous move in the universe | OPEN-1c |
| X6 | A qualifying previous move of zero calendar-day duration (a same-session high and low under a 1-day reaction) | OPEN-2a, OPEN-8 |
| X7 | Equal durations or magnitudes (el = R_T; run = R_P) | OD-9: no trigger |
| X8 | Equal highs at the move start; equal lows at a completed move's end | OPEN-4e, OPEN-8b |
| X9 | Outside or inside days inside a reaction | Memo §5 row 13 for K3; OPEN-2e for reactions |
| X10 | A CA ex-date inside the current move or inside a reference move | G-7, C-3 |
| X11 | A GAP session, halt or missing 1m bars inside the move | OPEN-5b, G-5 |
| X12 | A PIT N100 exit or entry mid-episode | OPEN-7c, G-6 |
| X13 | A Muhurat or special session inside the move (calendar-day counting; session windows) | OPEN-5d, OPEN-8 |
| X14 | Post-CAS carry-forward bars at 15:15–15:27 | OPEN-5d (`is_synthetic`) |
| X15 | Left-censored first move at data start or listing | OPEN-1d, G-6 |
| X16 | A window boundary (2022-12-30) inside an episode or an outcome window | R-12, OPEN-12 |
| X17 | A 1m bar that makes both a new high above P_S and a new low | OPEN-5f |
| X18 | A new high above P_S before the reaction is detected | OPEN-4d |
| X19 | The event fires after the formation instant in a week's last session | OPEN-11f |
| X20 | A stock eligible for BULL on some bars and NONE on others within one session | OPEN-3c |

---

## 17. Pseudocode (non-executable by design: every OPEN item is an unresolved symbol)

```text
# ---- imported, ruled ----
K3            := R1_K3_ALGORITHM                # memo §5 rows 1–13, unchanged
S9            := DEF_12_1_S9                    # last two confirmed K3 tops & bottoms
O_R10         := R2_G2b_OUTCOME                 # binary, 5 sessions, intraday H/L, direction per G-2(b)
T_c           := MEMO_8_2_STATISTIC             # weekly per-date Spearman IC, pooled bull+bear
SURROGATE     := R14_SYNC_BLOCK_BOOTSTRAP       # daily bar vectors, block 20, B=1999
FORMATION     := LAST_NSE_SESSION_OF_WEEK       # memo §7

# ---- locked operator decisions ----
COMPARATOR_T  := GREATEST                       # OD-1
BEAR_STATE    := S9_BEAR                        # OD-3
LATCH_SCOPE   := PER_EPISODE                    # OD-4, OD-6 (both directions)
EPISODE_RESET := ON_S9_CHANGE                   # OD-5
EVENT_TIMING  := FIRST_OBSERVABLE_BAR           # OD-7
RUN_EXTREME   := RUNNING                        # OD-8
CMP           := STRICT_GT                      # OD-9
EVAL_CLOCK    := OD_10_ONE_MINUTE               # BLOCKED: C-1, C-2, C-3

# ---- unresolved (NO DEFAULTS) ----
PREDECESSOR_UNIVERSE   := OPEN_1
EMPTY_UNIVERSE_RULE    := OPEN_1c
detect_moves()         := OPEN_2               # 1/2/3-day declines, reactions, rallies
QUALIFYING_SET_T       := OPEN_2g_2h
S9_VISIBILITY          := OPEN_3c
move_start()           := OPEN_4               # (t_S, P_S), detection lag, termination
BAR_OBSERVABILITY      := OPEN_5e
INTRABAR_ORDER         := OPEN_5f
EVENT_TIMESTAMP_RULE   := OPEN_6
LATCH_INDEPENDENCE     := OPEN_7b
LATCH_ACROSS_GAPS      := OPEN_7c
TIME_METRIC            := OPEN_8
COMPARATOR_P, UNIVERSE_P, QUALIFYING_SET_P := OPEN_9
SCORE_PERSISTENCE      := OPEN_11
OUTCOME_ANCHOR         := OPEN_12
CONTRAST_P             := G_4
MISSING_BAR, BURN_IN, CA_WINDOWS, SEED, SIZE_CHECK := G_5, G_6, G_7, G_8, G_9

# ---- per stock ----
for each stock i:
    for each session d:                                   # L1
        update K3(i, d); s9 = S9(i, d)
        if s9 != episode(i).state:
            close episode(i); if s9 in {BULL, BEAR}: open episode(i, s9) with latch_T = latch_P = False
        moves(i) = detect_moves(i, d)                     # L2, OPEN_2
    for each bar tau in EVAL_CLOCK(i):                    # L3, blocked
        sigma = S9_VISIBILITY(i, tau); if sigma == NONE: continue
        m = current_move(i, tau, sigma)                   # OPEN_2, OPEN_4
        if m is None or not eligible(i, tau, m): continue # C-4 restatement of G-2(b)
        Q_T = qualifying(moves(i), PREDECESSOR_UNIVERSE, QUALIFYING_SET_T, before=m.start)
        if Q_T empty: apply EMPTY_UNIVERSE_RULE; continue
        R_T = max(duration(M, TIME_METRIC) for M in Q_T)
        el  = elapsed(m.t_S, tau, TIME_METRIC)
        if not latch_T and CMP(el, R_T) and BAR_OBSERVABILITY(tau):
            emit ev_T(i, episode, EVENT_TIMESTAMP_RULE(tau)); latch_T = True
        R_P = price_reference(moves(i), COMPARATOR_P, UNIVERSE_P, QUALIFYING_SET_P)
        run = running_magnitude(m, tau, sigma, INTRABAR_ORDER)   # OD-8
        if not latch_P and CMP(run, R_P) and BAR_OBSERVABILITY(tau):
            emit ev_P(i, episode, EVENT_TIMESTAMP_RULE(tau)); latch_P = True

# ---- formation / outcome / statistic ----
for each formation week w:
    s_T(i,w), s_P(i,w) = SCORE_PERSISTENCE(events, w)     # OPEN_11
    y(i,w)             = O_R10(i, anchor = OUTCOME_ANCHOR)  # OPEN_12
T_time  = T_c(s_T, y);  T_price = T_c(s_P, y)
p_sur   = rank(T_time among SURROGATE draws)              # C-2
p_spec  = CONTRAST_P(T_time - T_price, SURROGATE)         # G-4
```

---

## 18. Freeze checklist (GF-10-specific; the global checklist governs everything else)

| # | Item | Status |
|---|---|---|
| F-1 | Operator rulings on C-1, C-2 and C-3 (evaluation clock vs window, surrogate, substrate/basis) | **OPEN — blocking** |
| F-2 | Operator ruling on C-4 (OD-2 detector vs R-1 row 7 and G-2(b) eligibility) | **OPEN — blocking** |
| F-3 | Supersession entries for C-5, C-6 and C-7 recorded in the ruling register (operator-owned) | **OPEN** |
| F-4 | OPEN-1 … OPEN-12 each ruled in writing (OPEN-2 before OPEN-1) | **OPEN** |
| F-5 | OPEN-13: G-4 … G-9 closed; P-1 … P-5 satisfied | **OPEN** (global checklist) |
| F-6 | OPEN-14 robustness set consolidated, off the pass path | **OPEN** |
| F-7 | G-2(b) transcribed verbatim, with the distinct-anchor observation | RULED — TO TRANSCRIBE |
| F-8 | S9 and K3 imported by citation (OPEN-3 items stated) | RULED (import) / OPEN-3 |
| F-9 | Documentation backlog D-1 … D-5 corrected, with original text preserved | **OPEN** |
| F-10 | Per-element class labels (GE/GSI/OD/RD) carried into the freeze document | This draft |
| F-11 | §20 non-attribution list carried into the freeze document and every report | This draft |
| F-12 | Freeze document committed, hashed and operator-approved | **NOT STARTED** |

---

## 19. Provenance / source locators

| Item | Locator |
|---|---|
| Book | *45 Years in Wall Street*, W. D. Gann, 1949. Operator PDF SHA-256 `183ed235…` (claim register §27.1). Not committed |
| Rule 8 over-balance | pp. 11–12 → Δ2-01, Δ2-02 (VERIFIED; re-verified from 200 dpi scans in session) |
| Greatest time period | p. 39 → Δ2-04 |
| Elapsed time at breakout | p. 62 → Δ2-15 |
| 3-Day Chart; calendar days; 1/2-day moves | pp. 61, 63 → Δ2-10, Δ3-01; record departures pp. 66–67 → Δ3-02 |
| Rule 9 (S9 basis) | p. 12 |
| Rule 10 (O-R10) | p. 13 → Δ2-11 |
| Adjusted averages | pp. 60–61 → Δ2-16 |
| Rulings | `PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md`: R-1, R-2, R-5, R-9, R-10 to R-14; G-1, G-2, G-3 blocks |
| K3 algorithm | Memo §5 rows 1–13 |
| GF-10 cell | Memo §7.3, §11.F; definition §12.4 |
| Statistic / surrogate | Memo §8.2, §10 |
| Gaps | `PTMS_GANN_STAGE1_FREEZE_CHECKLIST_2026-09-15.md` §4, §6 |
| 1m substrate | `docs/reports/index_research/PTMS_SUBSTRATE_CERTIFICATE_2026-09-13.md` §5; `core/market/bar_labeling.py`; `core/market/session_schedule.py` |
| Source audit | GF-10 element matrix (31 rows), delivered in session 2026-09-16 |
| Operator decisions | OD-1 … OD-10, operator message 2026-09-17 |

---

## 20. Statements that must NOT be attributed to Gann

None of the following may be described as Gann's rule, Gann's method or Gann's text:

1. That a strict mechanical 3-Day Chart (K3) is Gann's detector. It is a labelled approximation (R-1).
2. That any mechanical 1-, 2- or 3-day reaction detector is Gann's.
3. That S9 (last two K3 tops and bottoms rising or falling) is a Rule 8 precondition.
4. That S9 bear is Gann's bear condition. His wording is a decline "for a long period of Time".
5. That Rule 8 compares against the "greatest" previous decline or rally. That is OD-1, informed by
   p. 39.
6. That Rule 8 compares against the "immediately preceding" move.
7. That "the first time" applies to bull markets in Gann's text.
8. That a trend episode resets on an S9 change, or that exceedance is counted once per episode.
9. That Rule 8 specifies calendar days, a 1-minute clock, or any intraday evaluation.
10. That the event occurs on the first observable 1m bar.
11. That the running-extreme form of the price measurement is stated in Rule 8 (the high/low basis is
    a strong inference; the running form is OD-8).
12. That equality does not trigger (the strictness is textual; the equality treatment is OD-9).
13. That Rule 10's break of the last swing low is Rule 8's outcome.
14. That the 5-session horizon has any Gann basis.
15. That weekly formation has any Gann basis.
16. That pooling bull and bear observations is Gann's.
17. That T(time) − T(price), or any p-value on it, is Gann's test. Gann states only that time is more
    important than price.
18. That the surrogate null, T_c, the IUT or α have any Gann basis.
19. That a ratio-adjusted per-stock series is Gann's basis. p. 60–61 concern averages only.
20. That GF-10 used alone reflects Gann's practice. He says to apply all of the rules.
21. That any positive result shows Gann's documented method works. Any result is evidence about this
    specified construct only, and never confirmation.

---

## A. FROZEN BY OPERATOR (locked decisions only)

1. **OD-1** Time leg compared against the greatest qualifying previous decline/rally.
2. **OD-2** "Decline or reaction" preserved; 1/2/3-day framework recognized (detector open).
3. **OD-3** Bear condition = S9 bear (operator/research convention).
4. **OD-4** First exceedance per trend episode.
5. **OD-5** Episode resets on S9 reversal or cessation.
6. **OD-6** First-exceedance applied symmetrically to bull and bear.
7. **OD-7** Event = first objectively observable date/bar of the threshold crossing; not deferred.
8. **OD-8** Running-extreme magnitude; trigger when strictly greater than the reference.
9. **OD-9** Strict `>`; equality does not trigger.
10. **OD-10** Evaluate at the finest consistently available resolution, currently 1-minute bars.

*"Locked" means decided by the operator. It does not mean frozen in the pre-registration sense:
nothing is hashed, and C-1 to C-7 must be ruled first.*

## B. SOURCE-ESTABLISHED (supported by the source audit)

1. Rule 8 applies to "Averages or individual stocks" (p. 11). **GE**
2. Rule 8 compares a current decline's **time period** with a previous decline's (p. 11), and a bear
   rally's with a previous rally's (p. 12). **GE**
3. Rule 8 compares **points** of the current move with the previous decline **or reaction** (bull) or
   a previous rally (bear) (pp. 11–12). **GE**
4. The comparison words are "exceeds" and "greater". **GE**
5. "A previous" (bull time, both bear clauses) and "the previous" (bull price) are both used. **GE**
6. "The first time" appears in both bear clauses and in neither bull clause. **GE**
7. The bear precondition wording is a decline "for a long period of Time". **GE**
8. "Reverse this rule in a Bear Market". **GE**
9. The change "indicates", "is taking place" (bull price), "has started" (bear price), and is "at least
   temporarily" (bear time). **GE**
10. Time change is more important than reversal in price; apply all of the rules. **GE** (p. 12)
11. Greatest time period is named as a reference quantity (p. 39). **GE**, as a separate statement
    from Rule 8.
12. A previous move is a completed move. **GSI**
13. Moves are counted in calendar days (p. 61, for 3-day moves). **GSI** for Rule 8.
14. Duration runs from the high date to the low date (p. 63 "7-day decline"). **GSI**
15. Moves are measured on high/low extremes (p. 63; Rule 9 high/low charts). **GSI**
16. The change is indicated at the moment of exceedance ("is taking place" / "has started"). **GSI**
17. "Over-Balanced" wording attaches to the price clauses; time can over-balance price (p. 10). **GSI**
    for the "time overbalance" label.
18. The 3-Day Chart is the record; 1- and 2-day moves are used "sometimes" near extremes (p. 61, p. 63);
    Gann's record departs from the strict rule (pp. 66–67). **GE**
19. **Not source-established:** K3 as Rule 8's detector, S9 as its precondition, calendar days in
    Rule 8 itself, any intraday clock, Rule 10 as Rule 8's outcome.

## C. STILL OPEN BEFORE FREEZE

**Blocking conflicts**
- **C-1** 1m clock vs admissible windows (1m data only 2023+, which is spent; screen window
  2011–2022 has no 1m).
- **C-2** 1m clock vs the daily-bar R-14 surrogate.
- **C-3** 1m substrate/basis vs the R-13 EOD as-of-*t* basis.
- **C-4** OD-2 reaction detector vs R-1 row 7 (mechanized exception = Arm 2) and G-2(b) "K3 decline"
  eligibility.
- **C-5** OD-1 supersedes R-5 "immediately preceding" (record the supersession; robustness
  replacement).
- **C-6** OD-7 supersedes R-5's "score at week-end" event wording.
- **C-7** R-5 "before any up-switch" vs OD-4/OD-5 episode latch.

**Mechanical items**
- **OPEN-1** Time-comparator lookback universe (1b expanding/fixed; 1c empty universe; 1d boundary and
  censoring). Depends on OPEN-2.
- **OPEN-2** 1/2/3-day detector (2a–2c definitions; 2d extreme/wide-fluctuation condition; 2e overlap;
  2f transition; 2g/2h qualifying sets per leg and bear mirror; 2i predecessor/tie rule; 2j minimum
  size; 2k daily vs intraday).
- **OPEN-3** S9 import (3a K3 parameters; 3b confirmed inputs; 3c intraday visibility; 3d cessation →
  new episode; 3e initialization; 3f equal tops/bottoms).
- **OPEN-4** Causal start of the current move (4a which extreme; 4b detection lag vs clock start;
  4c termination; 4d new high before detection; 4e ties).
- **OPEN-5** 1m observation (5a fields; 5b missing bars/GAP/halts; 5c timestamp labelling;
  5d session/CAS/synthetic/special sessions; 5e intra-bar observability; 5f intra-bar ordering;
  5g basis).
- **OPEN-6** Event timestamp convention (vs event date).
- **OPEN-7** Stickiness (7a confirm one event per S9 episode; 7b leg-latch independence; 7c gaps/CA/PIT
  exits; 7d no retraction).
- **OPEN-8** Time metric at the event clock (8a integer vs continuous; 8b extreme timestamps and ties;
  8c midnight-crossing observability).
- **OPEN-9** Price-leg comparator, universe and qualifying set; contrast symmetry with the time leg.
- **OPEN-10** Bull/bear pooling disclosure text (documentation).
- **OPEN-11** Score persistence on the weekly formation grid; formation instant.
- **OPEN-12** Outcome window anchor (12a start; 12b event-session inclusion; 12c reference swing
  timing; 12d coincident penetration).
- **OPEN-13** G-4, G-5, G-6, G-7, G-8, G-9; P-1 … P-5.
- **OPEN-14** Robustness set consolidation after C-5.
- **D-1 … D-5** Documentation corrections.

---

**NOTHING WAS TESTED, READ, OPTIMIZED, IMPLEMENTED, FROZEN OR HASHED.** No ruling-register,
definition, memo or claim-register text was modified.
