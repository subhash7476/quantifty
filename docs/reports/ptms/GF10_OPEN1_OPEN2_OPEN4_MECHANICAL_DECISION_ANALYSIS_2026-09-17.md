# GF-10 — OPEN-1 / OPEN-2 / OPEN-4 Mechanical Decision Analysis

**Date:** 2026-09-17

**Status: DECISION-SUPPORT MEMO — NOT A RULING, NOT A FREEZE.**
- **No choice is made here.**
- No data was tested or read.
- No code was written.
- Nothing was optimized.
- No governance or repository document was modified.
- Every "effect on event population" statement is **structural reasoning from the definitions**, not
  an observed count.

**Parent draft:** `PTMS_GANN_GF10_FINAL_MECHANICAL_SPECIFICATION_DRAFT_2026-09-17.md` (commit `948f2ef`).
Its conflicts C-1 … C-7 are now resolved by the operator (§0). That file has not been edited.

**Class codes:**

| Code | Meaning |
|---|---|
| **GE** | Gann explicit |
| **GSI** | Gann strong inference |
| **GWI** | Gann weak inference: a Gann usage elsewhere, not in Rule 8 |
| **OD** | Operator decision (Gann silent) |
| **RD** | Our research design |

**Per-option criteria (as requested):**

| # | Criterion |
|---|---|
| ① | Source support |
| ② | Gann inference vs research design |
| ③ | Required data |
| ④ | Causality / reproducibility |
| ⑤ | Arbitrary degrees of freedom (DoF) |
| ⑥ | Effect on event population (structural) |
| ⑦ | HF/DB compatibility |
| ⑧ | Conflicts / dependencies |

---

## 0. Locked baseline this memo assumes

| Item | Locked content |
|---|---|
| OD-1 | Time leg compared with the **greatest qualifying previous** decline (bull) or rally (bear) |
| OD-2 | "Decline or reaction" preserved; 1/2/3-day framework recognized; **reaction ≠ K3** |
| OD-3 | Bear = S9 bear (research convention) |
| OD-4/5/6 | First exceedance per S9 episode; reset on S9 reversal or cessation; symmetric bull/bear |
| OD-7 | Event = first objectively observable crossing |
| OD-8/9 | Running extreme; strict `>` |
| OD-10 | Finest available resolution |
| Substrate | **HF** = genuine 1-minute profile where available. **DB** = separate daily profile where 1m is unavailable. **HF and DB never pooled**. For an event on session D, **all daily-derived K3/S9 information is frozen as of the D−1 close** |
| C-4 | Eligibility stays K3-based. Bull current move = **K3 decline**; bear current move = **K3 rally**. A reaction may serve **only as a bull price-leg comparator** and creates no alternative current-event detector. Reaction mechanics OPEN |
| C-5 | OD-1 supersedes "immediately preceding" |
| C-6 | OD-7 supersedes week-end event timing |
| C-7 | **Move-level reset + episode-level first-event latch** |

**K3 facts used below.** These are imported from memo §5 rows 1–13 (R-1) and not re-decided:
- A **down-switch** is 3 consecutive sessions each with a lower low than the prior session (literal
  reading; the symmetric reading is robustness only).
- An **up-switch** is 3 consecutive sessions each with a higher high **and** a higher low.
- Inequalities are strict.
- **Swing high** = the maximum daily high while the line is UP, dated on the day of that high.
- A swing extreme is usable from the close of the 3rd qualifying session.
- Outside days extend a DOWN lower-low count; inside days break runs.

**S9 reading used below (conditional).** S9 compares **confirmed** K3 tops and bottoms (draft
OPEN-3b, not yet ruled):
- A top is confirmed at the down-switch close that ends its UP line.
- A bottom is confirmed at the up-switch close that ends its DOWN line.
- **Therefore S9 can change only at a K3 switch close.** Every statement below marked "(under
  confirmed-S9)" depends on this reading.

### 0.1 Structural consequences of the locked baseline

These follow from the locks; they are not choices.

- **SC-1.** A bull-eligible K3 decline is confirmed at a down-switch close, D_c. S9 at D_c includes
  **the top this decline starts from**. The decline is bull-eligible only if that starting top is a
  higher top **and** bottoms are rising (under confirmed-S9). So eligibility depends partly on the
  current move's own start.
- **SC-2.** Under the D−1 freeze, the **earliest event session for a decline is D_c + 1**.
- **SC-3.** An S9 BULL episode can **begin at the same down-switch close** that confirms the current
  decline (the new higher top completes the BULL pattern). The episode and the current move can
  therefore begin at the same instant, while the move's starting extreme is **dated before** the
  episode start.
- **SC-4.** While the line is DOWN, no new top or bottom is confirmed. **S9 cannot change during a K3
  decline** (under confirmed-S9). Move termination by up-switch and any S9 change coincide at the
  same switch close.

---

# OPEN-1 — Previous-move lookback (time leg; "greatest qualifying previous")

**Source baseline for all options:**
- [45Y] **Rule 8** (p. 11; p. 12 bear) compares with **a** previous decline or rally. It gives **no
  lookback**. (GE for "a previous"; silent on scope.)
- [45Y] **p. 39** (Δ2-04): keep in mind the greatest time period, glossed in the register as the
  greatest correction **in an advance** / greatest rally time **in a decline**. This supports a
  "greatest within the current advance or decline" scope as **GWI**: it is a separate statement from
  Rule 8, and "advance" is not mechanically delimited.
- [WSSS] p. 176 (F0-TOB-04, VERIFIED): watch the greatest reaction "from any point" as a stock moves
  up. This is a **price** reference in another book. The anchor "any point" is undefined.
- **Rule 9** (p. 12): main trend by higher tops and bottoms. It is the basis of S9, not a lookback
  rule.
- **No source gives a lookback length.**

### Option 1-A — Entire available history (left-censored at data start or listing)

| # | Analysis |
|---|---|
| ① | None direct. p. 39 says "at all times" but scopes the quantity to an advance or decline. Rule 8 is silent |
| ② | RD. Reading "at all times" as history-wide is not supported by the gloss "in an advance" |
| ③ | Full daily H/L history per stock; the listing date |
| ④ | Causal (completed moves by the D−1 close). **Not reproducible across start dates**: the same stock-date gets a different R_T under a different data start. Censoring at 2011-03-25 (DB) or 2023-01-02 (HF, if HF daily state comes only from 1m — see X-1) |
| ⑤ | No numeric DoF. The censoring point is inherited, not chosen. One scope DoF: whether declines from **all** S9 states count (see 1-G) |
| ⑥ | R_T is **non-decreasing** over a stock's life, so exceedance gets structurally harder as history lengthens, and the event population drifts with calendar position. Under an unrestricted state set, the greatest "decline" is typically a main-trend (bear-state) decline, not a counter-move, so R_T measures a different kind of move from the current K3 decline |
| ⑦ | **Weakest.** HF and DB censor at different dates, so identical price paths give different R_T by profile. If HF may read pre-2023 daily history, that raises the pooling question (X-2) |
| ⑧ | X-1, X-2; mixing of trend and counter-trend moves; left-censoring disclosure (as R-3 does for GF-1) |

### Option 1-B — Current S9 episode only

| # | Analysis |
|---|---|
| ① | GWI via p. 39 ("in an advance"). S9 as the delimiter of "an advance" is OD-3/RD |
| ② | Scope is GWI. The delimiter is RD. Exactly matches the locked episode latch (OD-4/5) |
| ③ | Daily H/L; K3; S9 history of the current episode |
| ④ | Causal and reproducible given K3/S9; independent of data start once the episode is inside data |
| ⑤ | One structural DoF: **membership at the boundary** (SC-3). Is a move "in the episode" if confirmed before, at, or after episode start? Plus the empty-universe rule (1c) |
| ⑥ | Under SC-3 and "completed after episode start", the **first decline of every episode has an empty universe**. Its fate is decided entirely by 1c. If empty means ineligible, the first evaluable decline is the 2nd. Its universe holds exactly one move, so **"greatest" coincides with "immediately preceding" for that decline** (the C-5-superseded comparison, reached by another route). Combined with the first-event latch, early-episode declines carry most of the event mass structurally |
| ⑦ | Good. The episode is daily-derived, frozen at D−1, and identical in both profiles given the same daily bars |
| ⑧ | 1c (empty universe); SC-3 boundary membership; the declines that **form** the BULL pattern (between the two rising bottoms) fall before the episode and are excluded |

### Option 1-C — Fixed calendar lookback of L days

| # | Analysis |
|---|---|
| ① | None. Gann numbers exist (Rule 8 windows to 185 days; Rule 4's 60–65 days greatest average reaction; Rule 10's 1–5 years), but **none is stated as a lookback for Rule 8** |
| ② | RD. Taking L from a Gann number would still be operator selection, not Gann support |
| ③ | Daily H/L over L days (plus the move durations that straddle the edge) |
| ④ | Causal and reproducible given L and a boundary rule |
| ⑤ | **L** (continuous), plus the boundary rule (move included by start date, end date, or whole move inside) |
| ⑥ | R_T is **non-monotone**: an old long move can expire **during** a current decline, lowering R_T mid-move and creating a crossing without new price or time information. Requires a snapshot rule (4-R below) |
| ⑦ | Compatible if L fits inside each profile's data; HF near 2023-01-02 is censored |
| ⑧ | L cannot be chosen from results (§Q). Snapshot rule |

### Option 1-D — Research or formation window

| # | Analysis |
|---|---|
| ① | None |
| ② | RD (purely administrative) |
| ③ | Daily H/L from window start |
| ④ | **Not reproducible across windows**: the same stock-date gets a different R_T in the 2011–2022 screen than in any later window. The construct depends on the analyst's window choice |
| ⑤ | The window start (inherited, but not a property of the market) |
| ⑥ | As 1-A, but reset at each window start. Events cluster late in the window as R_T grows |
| ⑦ | The HF window (2023+) and DB window (2011–2022) define different constructs |
| ⑧ | Conflicts with the confirmatory-reuse principle: a construct must not change when the window changes |

### Option 1-E — Current K3 "major swing"

| # | Analysis |
|---|---|
| ① | Δ3-03 (p. 61–62): "major swings are of greater importance". Δ3-09: Gann's major-swing population is discretionary. Rule 9 keeps weekly and monthly charts. **No major-swing detector is given** |
| ② | Requires a **new detector** (weekly K3, a swing-size filter, a hierarchy). That would be RD, and a mechanized one risks Arm-2 status by the same logic as memo §5 row 7 |
| ③ | Depends on the invented detector |
| ④ | Causal only if the major detector is causal. Major swings confirm late |
| ⑤ | Every parameter of the new detector |
| ⑥ | Undetermined until the detector exists |
| ⑦ | Depends on the detector. A weekly detector is daily-derived, so compatible |
| ⑧ | Conflicts with "do not invent Gann support". Would reopen R-1's scope |

### Option 1-F — Current campaign ("advance" from its origin low)

The universe is the moves completed since the origin extreme of the current advance: the lowest
confirmed K3 bottom preceding the S9 NONE/BEAR → BULL transition (mirror for a decline).

| # | Analysis |
|---|---|
| ① | GWI via p. 39 ("in an advance"); Δ3-07 shows Gann uses campaign tops elsewhere, with "campaign" undefined |
| ② | Scope GWI. The **origin rule is RD** |
| ③ | Daily H/L; K3; S9 history back to the origin |
| ④ | Causal. Reproducible given the origin rule |
| ⑤ | **Origin rule** (which bottom: the last bottom before the BULL transition; the lowest bottom in the preceding NONE/BEAR stretch; the first rising bottom of the pattern) |
| ⑥ | Unlike 1-B, it includes the declines that formed the rising-bottom pattern, so the first episode decline usually has a non-empty universe. The **1c rule matters less** |
| ⑦ | Good (daily-derived). A long NONE/BEAR stretch before the origin may reach back toward the HF data start (X-1) |
| ⑧ | Origin DoF; boundary membership |

### Option 1-G — Same-state history

The universe is all previous counter-moves that occurred under the same S9 state, across every past
episode, from the data start.

| # | Analysis |
|---|---|
| ① | None direct. It combines Rule 8 "a previous" (unscoped) with the counter-move nature of the rule |
| ② | RD |
| ③ | Full daily history; K3; S9 |
| ④ | Causal. Same start-date dependence as 1-A |
| ⑤ | No numeric DoF; censoring inherited |
| ⑥ | Removes 1-A's trend/counter-trend mixing, but keeps the non-decreasing R_T and calendar drift |
| ⑦ | Same weaknesses as 1-A (X-1, X-2) |
| ⑧ | X-1, X-2 |

### Option 1-H — Last N qualifying moves (count-based)

| # | Analysis |
|---|---|
| ① | None |
| ② | RD |
| ③ | Daily H/L; K3 |
| ④ | Causal; reproducible given N |
| ⑤ | **N**. N = 1 reproduces the superseded "immediately preceding" (C-5) and is therefore excluded by lock |
| ⑥ | R_T is non-monotone as moves roll off |
| ⑦ | Compatible |
| ⑧ | N cannot be chosen from results; snapshot rule |

### OPEN-1 sub-items (for every option)

| Sub-item | Question |
|---|---|
| **1b** | Is R_T computed once when the current move becomes eligible (D_c close), or refreshed at each D−1 close? Only non-monotone universes (1-C, 1-H) make these differ. Under 1-A, 1-B, 1-F and 1-G no qualifying **decline** completes inside a K3 DOWN line (SC-4), so R_T is constant during the move — unless reactions enter the time-leg set (OPEN-2 §2.6) |
| **1c** | Empty universe: ineligible, score 0, or other. Load-bearing under 1-B |
| **1d** | Boundary membership: by start date, confirmation date or end date; SC-3 moves; left-censored first move at data start |
| **1e** | Bear mirror: the same universe rule applied to rallies (OD-6 symmetry). Requires no new DoF |

---

# OPEN-2 — Reaction definition

**Scope under C-4:** a reaction is **not** a current-event detector. It can only enter:
- (i) the **bull price-leg comparator** set, and
- (ii) possibly the **time-leg comparator** set (§2.6).

**Source baseline:**

| Source | What it says | Class |
|---|---|---|
| Rule 8 bull price (pp. 11–12) | "previous decline **or reaction**" | GE |
| Rule 8 bull time (p. 11) | "decline" only | GE |
| Rule 8 bear clauses (p. 12) | "rally" only; no reaction term | GE |
| p. 63 (K3 construction) | A 2-day reaction is **not recorded** | GE |
| p. 63 | 2-day moves **are** recorded near an extreme high or low, especially in wide fluctuations | GE (discretionary) |
| p. 61 (Δ3-01) | 3-day moves are the record; "we sometimes use 1 and 2-day moves" when extremes are reached "and we wish to catch a turn" | GE (discretionary) |
| p. 66 (Δ3-04) | Gann calls a recorded 3-Day Chart move **"a 3-day reaction"** | GE |
| Rule 4 (pp. 8–9, Δ2-08) | "reaction" used for 3-week and 60–65-day counter-moves | GE |
| [TST] p. 64 (F0-TOB-08) | Stocks seldom react more than two days in very active markets | GE, other book |
| [WSSS] pp. 176–177 (F0-TOB-04/05) | Reaction points **and** reaction time both watched | GE, other book |

> **Recorded source tension (the lock is not reopened).** In Gann's usage "reaction" names
> counter-moves of **every** length: 2-day (p. 63), 3-day recorded swings (p. 66), weeks (Rule 4). The
> source does **not** define "reaction" as a size class below K3. It is at least as consistent with
> "decline or reaction" being a near-synonymous pair. **OD-2's "reaction ≠ K3" is therefore an
> operator decision (OD), not a source finding.** This must be disclosed in the freeze document.

**Structural fact (not a choice).** Under literal K3, three consecutive lower-low sessions **are** a
K3 down-switch. Any "3-day reaction" defined by lower lows is therefore, by construction, a K3 decline
and cannot also be a reaction (OD-2). A 3-day reaction distinct from K3 would need a comparison rule
other than K3's (see §2.1). **Under the lock, the non-empty reaction class is structurally the 1- and
2-day moves, unless a non-K3 3-day rule is invented.**

## 2.1 What counts as a 1-, 2- and 3-day reaction (daily bars; all bull context, K3 UP line)

| Option | ① Source | ② Class | ③ Data | ④ Causality | ⑤ DoF | ⑥ Population (structural) | ⑦ HF/DB | ⑧ Conflicts |
|---|---|---|---|---|---|---|---|---|
| **2.1-a** A reaction session has a **lower low** than the prior session. 1-day = one such session; 2-day = two consecutive; a 3rd consecutive = K3 switch (becomes a decline) | Mirrors p. 63's "lower Bottoms" wording used for the down-switch | GSI (mirror of the K3 criterion); applying it below 3 days is OD | Daily H/L | Known at the close of each session; causal | None numeric; strict inequality imported | Widest reaction set: every lower-low session in an UP line | Identical (daily) | Consistent with the literal K3 asymmetry |
| **2.1-b** Lower low **and** lower high | Mirrors the symmetric K3 reading (robustness only under R-1) | RD (uses the non-primary K3 reading) | Daily H/L | Causal | None numeric | Narrower than 2.1-a (inside-range drops excluded) | Identical | Inconsistent with R-1's primary literal reading |
| **2.1-c** Close below prior close | No: Gann's swing record is tops and bottoms; R-2 uses the H/L basis | RD | Daily C | Causal | None | Different population (close-based) | Identical | Conflicts with the H/L basis of R-1/R-2 |
| **2.1-d** A distinct 3-day reaction class via a non-K3 rule | None | RD (invention) | — | — | Every rule parameter | — | — | Conflicts with "do not invent" and with OD-2's framework unless ruled |

**Also required for any option:**

| ID | Question |
|---|---|
| **2.1-e** | **Reaction top**: prior session's high (local), or the UP line's running top (highest high of the current K3 up leg). The p. 63 example measures from "last high" to "extreme low", which is GSI for a top-of-leg anchor |
| **2.1-f** | **Reaction end**: the first session that is not a lower low, or the first session with a higher high, or the first new high above the reaction top |
| **2.1-g** | **Reaction magnitude and duration**: top − lowest low of the reaction; calendar days from top date to low date. Δ3-06: Gann's day counts are calendar-day differences, start date excluded (GSI) |

## 2.2 "Near extremes" / "very wide fluctuations"

> **Load-bearing structural point.** p. 63 says a 2-day reaction is **not recorded**, except near
> extremes or in wide fluctuations. Unconditional inclusion of 1- and 2-day reactions therefore
> **contradicts** the p. 63 non-recording rule, and exclusion of all of them nullifies OD-2. **The
> condition cannot be dropped silently in either direction.** This is the reverse of K3 (R-1), where
> dropping the exception meant *excluding* short moves.

| Option | ① Source | ② Class | ③ Data | ④ Causality | ⑤ DoF | ⑥ Population | ⑦ HF/DB | ⑧ Conflicts |
|---|---|---|---|---|---|---|---|---|
| **N-0** Include all 1/2-day reactions; declare the departure | Contradicts p. 63 "do not record it" outside extremes | RD (declared departure) | Daily H/L | Causal | None | Maximal | Identical | p. 63; memo §5 row 7 caution |
| **N-1** Reaction qualifies only if its top **is** the running extreme high of a scope S | GSI for "when extreme highs … are reached" (p. 61) | Condition GSI; **scope S is OD** | Daily H/L + scope history | Causal | Scope S: current K3 up-leg (degenerate: every leg top is a leg high, so ≈ N-0); episode high; campaign high (1-F); all-time-to-date high (as R-3 for GF-1). No numeric DoF | Shrinks from ≈N-0 (leg scope) to rare (all-time scope) | Identical; all-time scope censored by profile (X-1) | **Couples to OPEN-1** if the same scope is reused |
| **N-2** Top within x% (or k ATR) of a running extreme | No numeric basis | RD | Daily H/L | Causal | x or k, plus scope | Continuous in x | Identical | Numeric parameter must not come from results |
| **N-3** "Very wide fluctuations" test (the session or reaction range ≥ k × a trailing average range) | Condition GE ("especially if … very wide"); no measure | RD | Daily H/L, trailing window | Causal | k, window, averaging | Continuous in k | Identical | Two numeric DoF |
| **N-4** N-1 **or** N-3 (Gann lists both circumstances) | GE (both named), discretionary | RD | As N-1 + N-3 | Causal | Union of the above | Larger than either alone | Identical | As above |

Gann's "sometimes" / "when we wish to catch a turn" wording is discretionary. **Every N option is a
mechanization of a discretionary practice** and must carry the same label as R-1 ("approximation of a
discretionary Gann practice").

## 2.3 Overlap, nesting and transition

| ID | Question | Options (no choice made) | Notes |
|---|---|---|---|
| **2.3-a** | Two 1-day reactions separated by one non-qualifying session | (i) two separate reactions; (ii) merged into one if the intervening session makes no new high above the reaction top | (ii) needs a merge criterion; (i) is literal day-counting |
| **2.3-b** | Inside day between two lower-low sessions | (i) breaks the reaction (mirrors memo §5 row 13 for K3); (ii) ignored | (i) keeps consistency with K3 |
| **2.3-c** | A 1- or 2-day reaction that becomes a K3 decline (3rd lower-low session) | (i) re-labelled as the K3 decline; not counted as a reaction; (ii) both recorded | (ii) double-counts one price path in the comparator set. Under C-4 the resulting K3 decline may be the **current** move, and it must never be its own previous comparator |
| **2.3-d** | Reaction occurring inside a K3 DOWN line (a 1–2 session lower-low burst within the decline) | (i) not a reaction (part of the decline); (ii) a reaction | Bull reactions are counter-moves to an advance, so (i) is the only reading consistent with "counter-move". Still to be ruled |
| **2.3-e** | Reaction whose top is later exceeded and then reacts again below the old low | Each new top starts a new reaction; the earlier one closes at its end rule (2.1-f) | Depends on 2.1-e/f |
| **2.3-f** | Timing of recognition | A reaction enters the comparator set only once **ended** (2.1-f) by the D−1 close | Consistent with the D−1 freeze |

## 2.4 Minimum size

| Option | ① Source | ② Class | ③ Data | ④ Causality | ⑤ DoF | ⑥ Population | ⑦ HF/DB | ⑧ Conflicts |
|---|---|---|---|---|---|---|---|---|
| **M-0** None (strict lower low guarantees positive magnitude) | No scale-free minimum in source | OD (silence respected) | — | Causal | None | Maximal | Identical | None |
| **M-1** Nominal points (5–7 points; 2–3 for low-priced stocks; [TST]/[WSSS]) | GE in nominal points, price-level dependent (Δ3-10) | Stage-2 translation (**R-15 open**) | As-traded price | Causal | Price-level bands | — | Basis conflict with the adjusted series | **Blocked by R-15** |
| **M-2** Percentage threshold | None | RD | Daily H/L | Causal | x% | Continuous | Identical | Must not come from results |
| **M-3** Volatility-scaled threshold | None | RD | Trailing range | Causal | k, window | Continuous | Identical | Two numeric DoF |

## 2.5 Daily vs intraday detection

| Option | ① Source | ② Class | ③ Data | ④ Causality | ⑤ DoF | ⑥ Population | ⑦ HF/DB | ⑧ Conflicts |
|---|---|---|---|---|---|---|---|---|
| **D-daily** Reactions from daily bars | GE: "1 and 2-day moves" are day-counted | GSI | Daily H/L | Frozen at the D−1 close (comparator info) | None | — | **Identical definition in HF and DB** | None |
| **D-intraday** Reactions from intraday swings (HF only) | None | RD | 1m | Causal only with an intraday detector | Intraday detector parameters | Different object from DB | **Breaks HF/DB definitional identity**; DB cannot reproduce it | Conflicts with the day-counted source and with the D−1 freeze of daily-derived structure |

## 2.6 Do reactions qualify for the **time** leg?

| Option | ① Source | ② Class | ③ Data | ④ Causality | ⑤ DoF | ⑥ Population (structural) | ⑦ HF/DB | ⑧ Conflicts |
|---|---|---|---|---|---|---|---|---|
| **TL-0** No. Time leg = K3 declines only (bull) / K3 rallies only (bear) | GE: bull time clause says "decline"; bear clauses "rally" | GE wording, literal | Daily H/L | Causal | None | Baseline | Identical | None. Symmetric with bear |
| **TL-1** Yes (bull), because Gann watches reaction time elsewhere (Rule 4; [WSSS] pp. 176–177) | GWI | OD | Daily H/L | Causal | Imports all OPEN-2 DoF into the primary leg | Under "greatest", a reaction raises R_T only if its duration exceeds every K3 decline in the universe. Structurally this is most likely when the universe holds few or no K3 declines (e.g. 1-B early in an episode, which also changes 1c's role) | Identical if D-daily | **Asymmetric with bear** (no bear reaction term) unless 1–2-day rallies are also admitted, which has no bear text. Makes the primary GF-10 leg depend on the least-sourced mechanics |

## 2.7 Which reactions qualify for the **bull price** leg?

| ID | Question | Options (no choice made) |
|---|---|---|
| **2.7-a** | State context | Only reactions within an S9 BULL state (episode or campaign per OPEN-1) / any state |
| **2.7-b** | Line context | Only within a K3 UP line (2.3-d(i)) |
| **2.7-c** | Filter | Per N-0 … N-4 and M-0 … M-3 |
| **2.7-d** | Transition | Excluding reactions absorbed into K3 declines (2.3-c(i)) |
| **2.7-e** | Union | The comparator set = qualifying K3 declines ∪ qualifying reactions ("decline **or** reaction") |
| **2.7-f** | Universe | Whether the price leg uses the same universe as the time leg (OPEN-1) |

> **Critical dependency on OPEN-9 (price comparator, out of scope here).** If the price comparator is
> "greatest", adding small reactions rarely changes R_P (they are shallower than most declines by
> construction: 1–2 sessions). If it is "immediately preceding", the preceding object will often be a
> small reaction, making price exceedance near-automatic for any K3 decline, which empties the
> T(time) − T(price) contrast of content. **OPEN-2's price-leg answer cannot be judged independently
> of OPEN-9.**

**Bear mirror (2.7-g).** Bear clauses have no "reaction". C-4 grants reactions to the bull price leg
only. The bear price comparator is therefore K3 rallies only, unless ruled otherwise. **This makes the
pooled bull/bear price legs asymmetric by construction.** It is a disclosure item under G-2(b)
pooling, not a choice.

---

# OPEN-4 — Current-move mechanics (bull shown; bear mirrors)

## 4.1 Starting extreme P_S

| Option | ① Source | ② Class | ③ Data | ④ Causality | ⑤ DoF | ⑥ Population | ⑦ HF/DB | ⑧ Conflicts |
|---|---|---|---|---|---|---|---|---|
| **S-a** The K3 swing high: max daily high while UP, dated on that day (memo §5 row 2) | p. 63: the line moves to "the top" of each day; p. 63 example measures from the "last high". p. 11: count "from any high or low" | GSI | Daily H/L | Fixed and known at D_c close; immutable afterwards under literal K3 | None (imported) | Baseline | Identical (daily-derived; frozen D−1) | Consistent with C-4 (K3-based) |
| **S-b** High of the session before the first lower-low session of the switch run | None beyond the day-comparison mechanics | RD | Daily H/L | Causal | None | Differs from S-a when the leg top came earlier than the last pre-switch session; gives a later/lower start, so shorter elapsed time and smaller magnitude | Identical | Inconsistent with R-1's swing-high definition |
| **S-c** Running episode or campaign high | GWI (campaign tops, Δ3-07) | RD | Daily H/L + OPEN-1 scope | Causal | Scope | Longer "current move" that can span several K3 legs; no longer "the K3 decline" | Identical | **Conflicts with C-4** (current move = K3 decline) |

## 4.2 Detection lag vs causal timestamp (clock start)

| Option | ① Source | ② Class | ③ Data | ④ Causality | ⑤ DoF | ⑥ Population (structural) | ⑦ HF/DB | ⑧ Conflicts |
|---|---|---|---|---|---|---|---|---|
| **C-a** Clock counts from the swing-high date (retroactive); eligibility from D_c + 1 (D−1 freeze) | p. 11 "from any high or low"; memo §5 row 4 | GSI (count origin); eligibility lag = locked substrate rule | Daily H/L | Causal: the origin date is historical, the eligibility respects the freeze | None | By D_c + 1, elapsed ≥ the switch run plus any days since the top. If R_T is below that, **OD-7 places the event on the first eligible bar of D_c + 1** (a structural mass at first eligibility, not a crossing observed in real time) | HF: first eligible 1m bar of D_c + 1. DB: session D_c + 1 (exact timestamp convention OPEN-6) | None. Must be disclosed |
| **C-b** Clock counts from the confirmation date D_c | None; contradicts "from any high or low" | RD | Daily | Causal | None | Shortens elapsed by the confirmation lag; removes the first-eligibility mass | Identical | **Conflicts with the GSI count origin** and with how reference durations are measured (high → low) |
| **C-c** Retroactive clock, but suppress events already exceeded at first eligibility | None | RD | Daily | Causal | None | Removes short-R_T cases entirely | Identical | **Conflicts with OD-7** ("first objectively observable crossing"): the crossing is first observable at D_c + 1 |

## 4.3 Move termination (move-level reset per C-7)

| Option | ① Source | ② Class | ③ Data | ④ Causality | ⑤ DoF | ⑥ Population (structural) | ⑦ HF/DB | ⑧ Conflicts |
|---|---|---|---|---|---|---|---|---|
| **T-a** Terminates at a K3 up-switch confirmed by the D−1 close. The move stays eligible through all of session D_u (the switch confirms at D_u's close) | p. 63: the line turns up after 3 days of higher tops and bottoms | GSI (K3 is the move object under C-4) | Daily H/L | Causal; purely daily-derived | None | A move can remain eligible while price is already above P_S intraday or on prior sessions (the up-switch needs 3 sessions), so a time event can fire during a recovery | Identical | By SC-4, termination and any S9 change coincide at the same switch close (under confirmed-S9) |
| **T-b** T-a, **or** earlier when price trades above P_S | GWI: a decline that has regained its start is no longer a decline. No explicit text | OD | HF: 1m highs on D; DB: daily highs to D−1 (or D) | Causal. **Needs a ruling on whether raw price (not K3/S9) on session D may be used** — the D−1 freeze covers K3/S9 only | Price basis (high vs close); observability (OPEN-5e) | Removes time events that would fire after full recovery | **HF and DB diverge** (intraday vs daily termination) unless the price test is restricted to D−1 daily data | Interaction with OD-7 (same bar exceeds P_S and crosses R_T) |
| **T-c** T-a plus S9 change | OD-5 | OD (locked at episode level) | — | — | None | Redundant under confirmed-S9 (SC-4); not redundant if S9 visibility is ruled otherwise (OPEN-3c) | Identical | OPEN-3b/3c |

## 4.4 New lows (bull) / new highs (bear) and the current-duration endpoint

| ID | Item | Content |
|---|---|---|
| **4.4-a** | New lows | Extend the running magnitude (OD-8, locked) and move the eventual swing low. They **do not** reset the clock. No choice |
| **4.4-b** | New high equal to or above P_S | See T-b; ties in §4.5 |
| **4.4-c** | Current elapsed endpoint (dependency, not a new option) | **E-a — to τ:** the existing R-5 cell wording ("from the current swing high to *t*"). **E-b — to the date of the running low:** mirrors how reference durations are measured (high date → low date, p. 63; GSI) |

Asymmetry between E-a and E-b:
- **Under E-a**, a decline that has bottomed and moves sideways keeps accruing time.
- **Under E-b**, the time leg can cross only on a session that makes a new low after R_T days. That
  couples the time leg to new price lows and structurally shifts it toward the price leg, which
  weakens the time-vs-price contrast.
- **E-a is the current ruling text. Adopting E-b would be a supersession of R-5's cell and must be
  ruled explicitly.**

## 4.5 Ties

| ID | Case | Options | Constraint |
|---|---|---|---|
| **4.5-a** | Equal highs defining P_S within the UP leg | First occurrence (longer elapsed) / last occurrence (shorter elapsed) | The **same rule** must apply to reference-move endpoints (their start high and end low), or elapsed and R_T are measured inconsistently |
| **4.5-b** | Equal low defining a reference move's end | First / last occurrence | Same rule as 4.5-a |
| **4.5-c** | Running low equal to the prior running low | No extension (strict: "lowest price reached so far" unchanged) | Follows from OD-8/OD-9; no choice |
| **4.5-d** | el(τ) = R_T or run(τ) = R_P | No trigger (OD-9, locked) | — |
| **4.5-e** | Intraday minute of the P_S high (HF) | Irrelevant if the time metric counts calendar dates. Relevant if continuous (draft OPEN-8, out of scope) | Dependency |

## 4.6 Interaction with K3 confirmation (imports; no new choices)

| ID | Interaction |
|---|---|
| **4.6-a** | Initialization: no swing high exists before the first K3 switch, so the first decline after initialization has P_S only once its UP leg is complete. Burn-in G-6 |
| **4.6-b** | Outside/inside days alter D_c (memo §5 row 13), and therefore the eligibility start (SC-2) and the first-eligibility mass (C-a) |
| **4.6-c** | SC-1: bull eligibility requires the decline's **own** starting top to be a higher top (under confirmed-S9). A decline that starts from a lower top is never bull-eligible, whatever its duration |
| **4.6-d** | SC-3: a decline confirmed at the same close that starts a BULL episode. Its membership in the episode (for the latch and for 1-B's universe) must be ruled (1d) |

## 4.7 Interaction with C-7 (move-level reset + episode-level latch)

- **Move-level reset:** each K3 decline in a BULL episode gets its own P_S, clock and running
  magnitude, and its own R_T (per OPEN-1 at its eligibility, or refreshed per 1b).
- **Episode-level latch:** once a time-leg event fires in the episode, later declines in that episode
  are evaluated for nothing on the time leg. Price-leg latch independence is a draft item (OPEN-7b,
  out of scope).
- **Coincidence under confirmed-S9 (SC-4):** the move ends at an up-switch close, and any episode
  change happens at a switch close. A move therefore cannot straddle an episode change mid-line. The
  one boundary case is SC-3 at the **start**.
- **Under T-b** a move can end mid-line, while the episode continues until the next switch close. No
  new move starts until the next down-switch, so there is no "orphan" current move.

---

## Cross-cutting dependencies (named)

| ID | Dependency |
|---|---|
| **X-1** | In the HF profile, do daily K3/S9 bars come from 1m aggregation (history from 2023-01-02) or from the EOD store (history from 2011)? This decides HF censoring for 1-A, 1-F, 1-G and N-1 (all-time scope) |
| **X-2** | Does "never pool HF and DB" forbid an HF event from using DB-era daily history as **lookback input** (not as observations)? |
| **X-3** | Price basis between daily-derived P_S / reference moves and intraday running lows in HF (the stores have different CA bases). Previously C-3; resolved at the profile level, but the within-HF daily/intraday basis identity must be stated |
| **X-4** | OPEN-3b (confirmed-S9 reading) underlies SC-1 … SC-4 |
| **X-5** | OPEN-9 (price comparator) governs whether the OPEN-2 price-leg set has any bite (§2.7) |
| **X-6** | OPEN-8 (time metric) governs 4.5-e and the first-eligibility mass (C-a) |

---

## 1. Locked decisions

1. OD-1 … OD-10 (as §0).
2. Substrate: HF / DB separate profiles, never pooled; K3/S9 daily information frozen at the D−1 close
   for events on D.
3. C-4: K3-based eligibility; current move = K3 decline (bull) / K3 rally (bear); reactions only as a
   bull price-leg comparator; reaction mechanics open.
4. C-5: OD-1 supersedes "immediately preceding".
5. C-6: OD-7 supersedes week-end event timing.
6. C-7: move-level reset plus episode-level first-event latch.
7. Imported, unchanged: K3 (R-1, memo §5 rows 1–13); O-R10 and G-2(b); statistic and surrogate
   (R-14); G-1; G-3.

## 2. Remaining operator decisions (this memo's scope)

**OPEN-1**

| ID | Decision |
|---|---|
| 1-scope | Universe: 1-A / 1-B / 1-C / 1-D / 1-E / 1-F / 1-G / 1-H / other |
| 1-param | If 1-C, L; if 1-F, the origin rule; if 1-H, N ≥ 2 |
| 1b | R_T snapshot: at eligibility, or refreshed at each D−1 close |
| 1c | Empty-universe rule |
| 1d | Boundary membership, including SC-3 moves and left-censored moves |
| 1e | Confirm the identical rule for bear rallies |

**OPEN-2**

| ID | Decision |
|---|---|
| 2.1 | Reaction criterion (2.1-a/b/c/d); reaction top (2.1-e); end rule (2.1-f); magnitude and duration convention (2.1-g) |
| 2.2 | Near-extreme/wide-fluctuation treatment (N-0 … N-4, with scope or parameters) and its approximation label |
| 2.3 | Nesting and transition rules (2.3-a … f) |
| 2.4 | Minimum size (M-0 / M-2 / M-3; M-1 is blocked by R-15) |
| 2.5 | Daily or intraday detection |
| 2.6 | Time-leg inclusion (TL-0 / TL-1), and the bear consequence |
| 2.7 | Bull price-leg qualification (2.7-a … f); acknowledgment of the bear asymmetry (2.7-g) |
| Disclosure | Record in the freeze document that "reaction ≠ K3" is OD, with the source tension (p. 66 "3-day reaction"; Rule 4 usage) |

**OPEN-4**

| ID | Decision |
|---|---|
| 4.1 | Starting extreme (S-a / S-b; S-c conflicts with C-4) |
| 4.2 | Clock origin and first-eligibility treatment (C-a / C-b / C-c; C-b and C-c carry conflicts) |
| 4.3 | Termination (T-a / T-b / T-c), and whether raw session-D price may be used under the D−1 freeze |
| 4.4-c | Confirm E-a (current R-5 text) or supersede with E-b |
| 4.5 | Tie rule (first/last occurrence), applied identically to current and reference moves |
| 4.6-d | SC-3 episode-membership rule (shared with 1d) |

**Cross-cutting:** X-1, X-2, X-3.

## 3. Dependencies

| Upstream | → Downstream | Why |
|---|---|---|
| X-1, X-2 | 1-A, 1-F, 1-G, N-1 (all-time) | Censoring and pooling scope |
| OPEN-3b (confirmed-S9) | SC-1 … SC-4, 1-B, 1d, 4.3, 4.6 | S9 change timing |
| 4.1, 4.5 | 1-scope, 2.1-e/g | Move endpoints must be defined before a universe of moves or reactions can be measured |
| 2.3-c (transition) | 1d, 2.7-d | A reaction absorbed into the current K3 decline must not be its own comparator |
| 2.6 (time-leg inclusion) | 1b, 1c | Reactions completing mid-universe change R_T behaviour and empty-universe incidence |
| 2.2 N-1 scope | 1-scope | Can reuse or differ from the OPEN-1 scope |
| OPEN-9 (price comparator) | 2.7 | Determines whether reaction inclusion matters |
| 4.4-c (E-a/E-b) | Time-vs-price contrast (R-10, G-4) | E-b couples the time leg to new lows |
| 4.2 C-a | OPEN-6, OPEN-8 | First-eligibility event timestamp and metric |
| 4.3 T-b | OPEN-5e, OPEN-6 | Same-bar ordering of a P_S breach and a crossing |

## 4. Questions that empirical testing must NOT decide

1. The lookback universe (any of 1-A … 1-H) and any parameter L, N or origin rule.
2. The R_T snapshot rule and the empty-universe rule.
3. Whether "reaction ≠ K3" holds (locked; disclosure only).
4. The reaction criterion, top anchor, end rule, nesting and transition rules.
5. Whether and how "near extremes" or "wide fluctuations" are applied, and any x, k or window.
6. Any minimum reaction size.
7. Daily vs intraday reaction detection.
8. Whether reactions enter the time leg; which reactions enter the price leg.
9. The starting extreme, clock origin, termination rule, E-a vs E-b, and tie rules.
10. The SC-3 membership rule.
11. X-1 and X-2 (HF history source; pooling scope).
12. Any choice justified by event count, coverage, IC, Sharpe, p-value, the surrogate result or the
    contrast result, including "too few events" or "too many events".

**Event-population reasoning in this memo is structural and may inform understanding only. No
decision may be justified by a measured event count.**

## 5. Recommended order for human decisions

Ordered by dependency, not preference.

| Step | Decisions | Reason |
|---|---|---|
| **1** | **X-1, X-2** (HF daily history source; whether lookback may cross the HF/DB boundary) | Decides which OPEN-1 options are feasible in HF at all |
| **2** | **OPEN-3b confirmation** (confirmed-S9 reading) | SC-1 … SC-4 rest on it; draft OPEN-3, out of this memo's scope but upstream |
| **3** | **OPEN-4 move objects:** 4.1 starting extreme → 4.5 tie rule → 4.2 clock origin → 4.4-c E-a/E-b → 4.3 termination (including the session-D raw-price question) | Define the move before any set of moves |
| **4** | **SC-3 membership** (4.6-d / 1d) | Needed by both the latch and an episode-scoped universe |
| **5** | **OPEN-2:** 2.5 daily/intraday → 2.1 criterion, top, end, magnitude → 2.3 nesting and transition → 2.2 near-extremes → 2.4 minimum size → 2.6 time-leg inclusion → 2.7 price-leg qualification | Reactions must be defined before they can qualify for any universe |
| **6** | **OPEN-1:** scope → parameter (if any) → 1b snapshot → 1c empty universe → 1e bear confirmation | "Qualifying previous" is only defined after steps 3–5 |
| **7** | Then **OPEN-9** (price comparator), re-reading 2.7 against it | §2.7 critical dependency |
| **8** | Downstream draft items (OPEN-5, 6, 7, 8, 11, 12), then G-4 … G-9 | Unchanged from the parent draft |

---

**NO DATA WAS TESTED OR READ. NO CODE WAS WRITTEN. NOTHING WAS OPTIMIZED, CHOSEN, FROZEN OR HASHED.
NO GOVERNANCE OR REPOSITORY DOCUMENT WAS MODIFIED.**
