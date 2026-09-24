# GF-10 OPEN-K(a) — Score-0 Eligibility Instant: Specification Analysis

**Date:** 2026-09-19 · **Branch:** `research/ptms-price-time-market-structure`

**Status: ANALYSIS FOR AN OPERATOR RULING. NOT A DECISION, NOT A FREEZE.**
- No recommendation is made.
- No market data or outcome was read. No code was written.
- **Scope: OPEN-K(a) only.** It covers when a stock without a P1 event counts as eligible for formation
  week *w*. OPEN-K(b) (the outcome of a 0) and OPEN-K(c) (two events in one week) are touched only
  where an alternative forces them.

**Authority:**
- GF-10 record v0.7 (`72b3f0d`), §3.9 and §5.3.
- Pre-registration memo `PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md` §7 and §11.F.
- Ruling register G-2(b).

---

## 1. The specification language that creates the question

**OPEN-11 (locked 2026-09-19; v0.7 header):**
> "Weekly formation score: **1** = a GF-10 event/crossing occurred in the formation week; **0** =
> eligible, no event; **excluded** = not eligible. … **Formation instant** = close of the last eligible
> trading session of the week."

**G-2(b) (ruling register, 2026-09-15):**
> "**S9 bull + K3 decline** → bull GF-10 score/outcome; **S9 bear + K3 rally** → mirrored bear GF-10
> score/outcome; … S9 no-state stocks and stocks not in the required counter-move are **ineligible, not
> zero**"

**Memo §7 (common to all three primaries):**
> "formation at the last session of each calendar week; … eligibility = PIT member with a confirmed K3
> state and the construct's anchor available."

**Memo §11.F, GF-10 cell (R-5):**
> "Stock in S9 bull state and in a K3 decline. Score = 1 at week-end *t* if … and no up-switch has
> occurred."

**v0.7 §3.9 (which records the gap):**
> "**A score of 1 is event-based (derived).** It does not re-test eligibility at f_w. … **Not ruled
> here:** the instant or span at which a **score-0** stock is judged eligible in *w*, and its outcome
> (OPEN-K)."

**Why these texts leave a gap.**
- G-2(b) defines **what state** is eligible: S9 bull with a K3 decline in progress, or the bear mirror.
- Memo §7 adds PIT membership.
- None of them says **at which instant, or over which span of *w*,** that state is tested.
- Memo §7 and R-5 were written for a **week-end state score**. There, the test instant was
  automatically the week-end.
- OPEN-11 replaced that score with an **event score over the whole week** (t_e ∈ (f_{w−1}, f_w]).
  That fixes the test for 1s through the event, and leaves the 0s without a stated test.

---

## 2. What the existing locks already fix

These facts restrict the alternatives. None is a new choice.

**F-1 — Eligibility is a per-session state and cannot change inside a session.**
- Under the D−1 freeze (C-3, OPEN-3b = A), K3 and S9 on session D are read as of D⁻.
- A candidate M is active on D ∈ A(M) = (c, u] (OPEN-4.3).
- PIT membership changes at session boundaries.
- So the state

  E(i, D) := PIT(i, D) ∧ ∃ M active on D with (S9 BULL ∧ K3 decline) or (S9 BEAR ∧ K3 rally)

  is constant through D. "Changes during the week" can only mean changes **between sessions**.

**F-2 — S9 is constant within a candidate's active span** (v0.7 §3.3). S9 changes only at a K3 switch
close, and every such close is some c or u. Within *w*, eligibility therefore switches only at:
- a candidate's start (c⁺);
- a candidate's end (after u);
- a PIT entry or exit.

**F-3 — A P1 event certifies eligibility at its own instant.** A P1 event needs an active candidate in
S9 BULL or BEAR at t_e. Whether PIT membership is part of P1 detection is the panel's G-6 question and
is not re-opened here.

---

## 3. The three required distinctions

### 3.1 Weeks that contain a P1 event (score 1)

| Element | Current specification |
|---|---|
| Rule | s(i, w) = 1 iff stock *i* has a P1 event with t_e ∈ (f_{w−1}, f_w] (OPEN-11; v0.7 §3.9) |
| Eligibility test | Implicit, at t_e, through F-3 |
| Re-test at f_w | **None.** v0.7 §3.9 records this as a derived reading of OPEN-11's "1 = … event occurred in the formation week". It is a research derivation, not an operator lock. Under alternative A below, 1s and 0s would be tested at different instants (§4) |

### 3.2 Weeks with no P1 event (score 0 or excluded)

Not ruled. This is OPEN-K(a). The alternatives are in §4.

### 3.3 Eligibility changes during the week

These can occur only between sessions (F-1). Each alternative in §4 states what it does with them.

---

## 4. The mechanically distinct alternatives

Only alternatives with a textual anchor in the existing specification are listed.

v0.7 §5.3 also named "across all of *w*" (eligible on every session). No spec text anchors that
option, so it is **not** carried forward here. That is a correction to v0.7's sub-item list.

### Alternative A — point test at the formation instant

**Anchor:** memo §7 ("formation at the last session of each calendar week"); R-5 ("at week-end *t*").
This keeps the memo's week-end state test for 0s.

Rule: *i* is eligible in *w* iff its state holds at the formation instant f_w. There are two readings of
"state at f_w", and they differ only when a K3 switch closes on the week's last session D_L:

| Variant | Eligible iff | Differs when |
|---|---|---|
| **A1** — session state on D_L | E(i, D_L): the D−1-frozen state used for every observation on D_L. A candidate with u = D_L is still active on D_L | An up-switch (bull) or down-switch (bear) confirms at close(D_L). A1 counts *i* as eligible. A2 does not |
| **A2** — state after close(D_L) | The state with D_L's close applied, i.e. the frozen state of D_L⁺. R-5's "and no up-switch has occurred" reads naturally this way | A switch at close(D_L) that **starts** a new candidate: A2 counts *i* as eligible although no session of *w* was ever active for it. A1 does not |

**Eligibility changes during the week under A.** Only the state at f_w counts. Examples:
- A stock eligible Monday–Thursday whose move ended Thursday (u = Thursday) and which has no event is
  **excluded**.
- A stock that became eligible only on Friday scores **0**.
- A stock with a Tuesday event scores **1** even if ineligible at f_w (§3.1).
- So 1s are tested at t_e and 0s at f_w. That asymmetry is a property of A, to be disclosed if A is
  chosen.

### Alternative B — span test over the week

**Anchor:** OPEN-11's own event window. A 1 can arise at any instant in (f_{w−1}, f_w], and B tests 0s
over the same window. A second anchor is textual: OPEN-11 says "close of the last **eligible** trading
session of the week". If "eligible" there means *stock-eligible* rather than *an NSE trading session*,
then a stock with no eligible session in *w* has no formation instant and is excluded. That is exactly
B. v0.7 §3.9 read "eligible trading session" as the calendar session, but **the wording supports both
readings**, and the operator may wish to state which was meant.

Rule: *i* is eligible in *w* iff E(i, D) holds for **at least one** session D of *w*. Its 0 then means
"the construct could have fired this week and did not", which is the same set of sessions on which a 1
could have occurred.

**Eligibility changes during the week under B:**
- A stock eligible on any session of *w* and without an event scores **0**, whatever its state at f_w.
- 1s and 0s are tested over the same span, so there is no asymmetry with §3.1.
- **Forced dependency:** if the eligible sessions in *w* carry **both directions**, the observation's
  direction is not fixed. This happens when a bull candidate ends and a bear candidate begins after an
  S9 change. Direction is needed for OPEN-K(b)'s outcome. B therefore requires OPEN-K(b) to name the
  direction, for example the last eligible session's.
- The same applies if *w* straddles S_HF (DB and HF are never pooled). **Inside the R-12 screen window
  (≤ 2022-12-30) this cannot happen**, because the 1m equity substrate starts 2023-01-02.

### Summary

| | A1 | A2 | B |
|---|---|---|---|
| Test for a 0 | E(i, D_L) | State after close(D_L) | ∃ D ∈ *w*: E(i, D) |
| Textual anchor | Memo §7, R-5 week-end | R-5 "no up-switch has occurred" | OPEN-11 event window; "last eligible trading session" (stock reading) |
| Same test as the 1s? | No (1s at t_e) | No | Yes (same span) |
| Move ended mid-week, no event | Excluded | Excluded | 0 |
| Move started on the last session only | 0 | 0 | 0 |
| Switch confirmed at close(D_L) | Ending candidate: eligible; starting: not eligible | Ending: not eligible; starting: eligible | Ending: eligible (active on D_L); starting: not eligible (first active session is in *w*+1) |
| Direction of a 0 is unique? | Yes | Yes | No (needs OPEN-K(b)) |

---

## 5. Coupled questions (not instant/span, but needed to evaluate E(i, D))

These concern **which state counts as eligible**, not **when** it is tested. Both come from existing
text and are listed so that ruling OPEN-K(a) does not silently decide them.

| ID | Question | Where it already appears | Status |
|---|---|---|---|
| K(a)-P1 | Is a candidate with an **empty reference universe** (𝒰_T = ∅; under OPEN-1 = A the first candidate of every episode "cannot trigger") eligible, making the week a 0, or ineligible? | `GF10_OPEN1_OPEN2_OPEN4_MECHANICAL_DECISION_ANALYSIS_2026-09-17.md` row **1c** ("Empty universe: ineligible, score 0, or other"); spec draft T11 / OPEN-1c; memo §7 "the construct's anchor available" | Not locked in any record from v0.1 to v0.7 |
| K(a)-P2 | Is a stock whose episode latch is already set (λ = TRUE after its P1 event) still eligible in later weeks of the same episode, making those weeks 0s, although no further event is possible (OD-4)? | Follows from OD-4 plus OPEN-11 "0 = eligible, no event". R-5's state score had no latch | Not addressed in any record |

The alternatives in §4 apply unchanged whichever way P1 and P2 are ruled. P1 and P2 change only E(i, D).

### 5.1 K(a)-P1 in detail: what the existing text does and does not say

**What is locked.** OPEN-1 = A (v0.1 §1.2 row 12):
> "The first qualifying move in an episode has no reference and cannot trigger"

This is a statement about **event capability**. It does not say whether such a candidate's stock-week is
a 0 or is excluded. The question was posed explicitly as **1c**:
- analysis 2026-09-17 row 1c: "Empty universe: ineligible, score 0, or other";
- spec draft T11: "Stock ineligible, score 0, or other? **OPEN-1c**".

No record from v0.1 to v0.7 rules it. **The answer is not determined by the current specification.**

**Text supporting "eligible, so a 0":**
- G-2(b) defines eligibility by state, "S9 bull + K3 decline". It names only two ineligible classes,
  "S9 no-state stocks and stocks not in the required counter-move". An empty-universe candidate is in
  neither class.
- OPEN-11 says "0 = eligible, no event".
- Read literally, these two texts give a 0.

**Text supporting "ineligible, so excluded":**
- Memo §7: "eligibility = PIT member with a confirmed K3 state **and the construct's anchor available**".
  For GF-10, the comparison move is part of what the score needs.
- R-5's cell defines the score against "the immediately preceding completed K3 decline". That is
  undefined when no such decline exists in the episode.
- NC-8 (derived, locked chain): the same candidate is never matched and is **excluded** from P3/P4.
  "Eligible" would treat it differently in the primary score than in the contrast. The populations
  already differ by design (NC-13/NC-14), so this is a consistency consideration, not a contradiction.

**Mechanical consequence, independent of data.**
- Under "eligible", every stock-week on which the only active candidate has 𝒰_T = ∅ enters the IC as a
  0 that **could not have been 1**. It is a structural zero, not an observed non-event.
- Under "ineligible", those stock-weeks are excluded, and only candidates able to fire contribute 0s.
- Both are coherent with all 62 locks.
- The bear mirror is identical (the first K3 rally of a BEAR episode).
- Interaction with OPEN-K(a)-B: a week can contain an unmatched candidate that ends and a matched one
  that starts. Under the span rule, the ruling decides whether that week counts through the matched
  session alone.

**Status:** operator decision required. No recommendation.

---

## 6. What this analysis does not do

- It chooses none of A1, A2 or B, and neither of K(a)-P1 or K(a)-P2.
- It does not define the outcome or reference of a 0 (OPEN-K(b)) or the two-event case (OPEN-K(c)).
- It reads no data. No alternative is characterised by how many observations it would include or
  exclude, and none may be chosen on that basis (v0.7 §8).

**NO CODE. NO DATA READ. NO RECOMMENDATION. NOT A FREEZE.**
