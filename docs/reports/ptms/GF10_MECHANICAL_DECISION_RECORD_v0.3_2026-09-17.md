# GF-10 Mechanical Decision Record — v0.3

**Date:** 2026-09-17

**Status: CONSOLIDATED DECISION RECORD — NOT AN IMPLEMENTATION SPECIFICATION, NOT A FREEZE.**
- No code, backtest, empirical test, optimization or performance analysis was performed.
- No market data or outcome was read. Nothing is frozen or hashed.
- **No locked decision is reopened.**

**Supersedes:**
- **v0.2** (`GF10_MECHANICAL_DECISION_RECORD_v0.2_2026-09-17.md`, uncommitted). It incorrectly
  recorded RQ-1 … RQ-7 as not decided.
- **v0.1** (commit `59e25da`), unchanged.

**Provenance of RQ-1 … RQ-11.** All eleven are **LOCKED operator decisions**. They were stated in the
operator's correction instruction of 2026-09-17, which confirms they were ruled in the preceding
conversation. That instruction is the recorded source for this ledger. RQ-8 … RQ-11 were stated in the
v0.2 update instruction and are reconfirmed by the correction.

**Construct label:** GF-10 = **GANN-FAITHFUL SOURCE CONCEPT + EXPLICIT OPERATOR/RESEARCH CONVENTIONS.**
It is not "Gann's exact rule".

**Provenance markers:**

| Marker | Meaning |
|---|---|
| **[GS]** | GANN SOURCE: verified wording or arithmetic; register ID given |
| **[LOD]** | LOCKED OPERATOR / RESEARCH DECISION |
| **[NES]** | NOT ESTABLISHED BY SOURCE; never to be attributed to Gann |

A [GS] marker on part of a rule does not extend to the rest of it.

**Document layout:**

| Part | Sections |
|---|---|
| LOCKED | §1 – §4, §9 |
| NEWLY SURFACED OPEN | §5 |
| Future implementation / empirical work | §8 |

---

## 0. Change log from v0.2

| # | Change |
|---|---|
| CL-1 | **Provenance corrected.** RQ-1 … RQ-7 restored as LOCKED: RQ-1 = A, RQ-2 = A, RQ-3 = C, RQ-4 = A, RQ-5 = A, RQ-6 = A, RQ-7 = B. The v0.2 notice that they were "not recorded in this conversation" is **removed**, along with every "OPEN — not recorded" status |
| CL-2 | All RQ-1 … RQ-11 entered in the decision ledger (§9) as LOCKED |
| CL-3 | The definitions, state machine and stage table now apply RQ-1 … RQ-7 (§1.2, §3.2, §3.6, §3.7, §3.8, §4) |
| CL-4 | OPEN-A, OPEN-B and OPEN-C **kept OPEN**, restated against the full lock set. OPEN-B is extended to the price leg, because RQ-4 = A adds a price latch |
| CL-5 | The re-run audit surfaced four further ambiguities from combinations of locks: **OPEN-D** (equal-high "established" under RQ-7 = B), **OPEN-E** (a successive LL session after an outside-day reaction session under RQ-6 = A / RQ-7 = B), **OPEN-F** (price-latch state for the matched contrast under RQ-3 = C / RQ-4 = A), **OPEN-G** (whether RQ-10 = B covers the RQ-4 price latch). Marked OPEN, not resolved |
| CL-6 | The contradiction audit was re-run (§7). v0.2 is now graded FAIL for the provenance error. The decision order (§10) covers only the OPEN items |

---

## 1. Locked mechanical model

### 1.1 Causal chain

```text
Authoritative EOD daily bars, R-13 as-of-t basis
  └─► K3 line state and confirmed swing points (R-1)
        └─► confirmed S9; changes only at a K3 switch close (OPEN-3b = A)
              └─► D−1 freeze; historical values re-based to as-of-D (RQ-9 = x)
                    └─► current K3 move from its first-occurrence swing extreme (OPEN-4.1/4.5)
                          └─► reference ledger of episode E: members by confirmation/completion close (RQ-1 = A, SC-3 = A),
                              completed on or before d_S (RQ-5 = A)
                                ├─► R_T = greatest same-type K3 duration (OD-1, OPEN-2.4 = A)
                                └─► R_P = one combined maximum over qualifying K3 moves (+ qualifying reactions, bull)
                                    (RQ-2 = A); literal magnitude windows (RQ-8 = A);
                                    reactions adjacent to a fresh leg high, top excluding reaction highs (RQ-6 = A, RQ-7 = B)
                                      └─► first objectively observable strict crossing (OD-7, OD-9)
                                          HF: EOD history + normalized genuine 1m on D (RQ-9 = A+x); DB: EOD
                                            ├─► time crossing ⇒ GF-10 EVENT; time latch (OD-4, C-7)
                                            │     HF no-bar session ⇒ no event, latch set (RQ-11 = D)
                                            └─► price crossing ⇒ price flag, recorded independently (RQ-3 = C);
                                                own first-per-episode latch (RQ-4 = A)
                                                  └─► formal T(time) − T(price) on matched candidates (RQ-3 = C)
                                                  └─► latches reset only at a new episode; HF time latch FALSE at substrate start (RQ-10 = B)
```

### 1.2 Stage table with provenance

| # | Stage | Locked content | Provenance |
|---|---|---|---|
| 1 | Data | **HF:** genuine 1m on the observation session for detection; EOD for K3/S9 and all historical sessions, pre-substrate allowed (X-1 = A; RQ-9 = A). **DB:** EOD only where 1m is unavailable. Populations never pooled; HF may use EOD lookback; DB-era observations never become HF events (X-2 = A) | [LOD]; [NES] |
| 2 | Price basis | Every price compared on D is on the R-13 as-of-D basis; HF 1m prices normalized first | [LOD] (R-13, RQ-9 = x); [NES] |
| 3 | K3 | Strict 3-Day Chart (memo §5 rows 1–13). The line moves to the top/bottom of the 3rd day at a switch | [GS] Δ2-10 construction; [LOD] R-1 (labelled approximation); [GS] Δ3-02 record departures |
| 4 | S9 | Last two confirmed tops and bottoms strictly rising = BULL; strictly falling = BEAR; else NONE. Changes only at a switch close | [GS] Rule 9 (p. 12); [LOD] OPEN-3b = A; S9 as a Rule 8 precondition [NES] |
| 5 | Bear condition | S9 BEAR | [LOD] OD-3; Gann's "declining for a long period of Time" [GS] Δ2-01; equivalence [NES] |
| 6 | D−1 freeze | All daily-derived facts used on D are as of D⁻ | [LOD]; [NES] |
| 7 | Current move | Bull: K3 decline from the K3 swing high. Bear: K3 rally from the K3 swing low. Reactions never create a current move | [GS] p. 11, p. 63 (from a high/low); [LOD] C-4, OPEN-4.1 |
| 8 | Ties (starting extreme) | First occurrence | [LOD] OPEN-4.5; [NES] |
| 9 | Time clock | Integer calendar days from the starting-extreme date to the observation date; not stopped at the running extreme | [GS] Δ3-06, p. 61; [LOD] OPEN-4.2, OPEN-4.4 |
| 10 | Termination | At the confirmed opposite K3 switch; no intraday price break | [LOD] OPEN-4.3 |
| 11 | Episode | Maximal constant S9 ∈ {BULL, BEAR}; resets on reversal or cessation | [LOD] OD-5; [NES] |
| 12 | Membership | **By confirmation close** (a K3 move) or completion close (a reaction), inside [a, b). A move confirmed at the creating switch is included (SC-3). A move confirmed under the previous episode is **not** carried into the new one, even if it completes after the switch | [LOD] SC-3 = A, RQ-1 = A; [NES] |
| 13 | Reference ledger | Completed previous same-type moves that are episode members, completed **on or before d_S**. No carryover, fixed N, calendar lookback or entire history. The first qualifying move in an episode cannot trigger | [GS] "a previous" Δ2-01/02; [GS] greatest time period Δ2-04 (separate statement); [LOD] OD-1, OPEN-1 = A, RQ-1 = A, RQ-5 = A; [NES] |
| 14 | Time reference | R_T = greatest duration among ledger K3 moves of the same type; reactions excluded | [GS] "decline" (bull time clause); [LOD] OPEN-2.4 = A. Duration endpoint: **OPEN-A** |
| 15 | Reaction (bull only) | 1 or 2 consecutive strict LL sessions inside a K3 UP line; a 3rd LL is a K3 down-switch. Bounded. **Must begin on the session immediately after the session that established the running K3-leg high.** **Top = that running leg high immediately before the reaction; highs made during the reaction are excluded.** Near-extreme = this structural adjacency, not a numeric threshold | [GS] "decline or reaction" Δ2-02; [GS] near-extreme 2-day moves Δ2-10, Δ3-01 (discretionary); [LOD] OD-2, OPEN-2.1/2.2/2.3/2.5, RQ-6 = A, RQ-7 = B; [NES]. **OPEN-D, OPEN-E** |
| 16 | Magnitudes | Current: P_S to the literal extreme strictly after the start session through the observation instant. Reference K3 move: same literal window through its terminating close. Reaction: Top − low of its last session (= literal minimum of its sessions). HF: EOD history + normalized 1m on D. DB: EOD | [GS] p. 63 (inference); [LOD] OD-8, RQ-8 = A, RQ-9 = A+x; [NES] |
| 17 | Price reference | **Bull:** R_P = **one combined maximum** over ledger K3 declines and ledger qualifying reactions. **Bear:** maximum over ledger K3 rallies | [GS] "the previous decline or reaction" / "a previous rally" Δ2-02; [LOD] C-4, OPEN-2.4, RQ-2 = A; "greatest" for price [NES] |
| 18 | Triggers | Strict `>` | [GS] "exceeds", "greater"; [LOD] OD-9 |
| 19 | Event timing | First objectively observable crossing | [GS] "is taking place" / "has started" (inference); [LOD] OD-7, C-6 |
| 20 | GF-10 event | Time crossing. HF: first genuine 1m bar of the crossing session; no genuine bar → no event, time latch set. DB: crossing session | [GS] time > price (p. 12); [LOD] R-5, R-10, RQ-11 = D; [NES] |
| 21 | Time latch | One GF-10 event per stock per episode; set by an event or an RQ-11 = D no-bar crossing; reset at a new episode; HF: FALSE at substrate start | [GS] "the first time" (bear clauses only); [LOD] OD-4/6, C-7, RQ-10 = B, RQ-11 = D; [NES] |
| 22 | Price flag and latch | Price flags recorded independently of time-leg eligibility, with an **independent first-per-episode price latch** | [GS] "the first time" in the bear price clause (bear only); [LOD] RQ-3 = C, RQ-4 = A; [NES]. No-bar: **OPEN-C**. Substrate start: **OPEN-G** |
| 23 | Formal contrast | T(time) − T(price) uses **matched candidates**: those for which both 𝒰_T ≠ ∅ and 𝒰_P ≠ ∅ | [LOD] RQ-3 = C, R-10; [NES]. Latch interaction: **OPEN-F** |
| 24 | Move reset | Each qualifying K3 move is an independent candidate | [LOD] C-7 |
| 25 | Outcome (context) | O-R10 per R-2 / G-2(b) | [GS] Rule 10 Δ2-11 (a separate rule); use for Rule 8 [NES]; [LOD] |

---

## 2. Source fact vs operator decision

| Rule | GANN SOURCE | LOCKED OPERATOR / RESEARCH | NOT ESTABLISHED BY SOURCE |
|---|---|---|---|
| Stocks as well as averages | ✔ p. 11 | — | — |
| Duration comparison with a previous decline/rally | ✔ Δ2-01 | Greatest; episode scope; confirmation membership; completed ≤ d_S (OD-1, OPEN-1, RQ-1, RQ-5) | Greatest; scope; membership; cut |
| Points comparison with the previous decline or reaction (bull) / a previous rally (bear) | ✔ Δ2-02 | One combined maximum (RQ-2) | "Greatest" for price in Rule 8 |
| Strict exceedance | ✔ | Equality = no trigger (OD-9) | Equality treatment |
| "The first time" | ✔ bear time and bear price clauses only | Per-episode time latch and price latch, both directions (OD-4/6, RQ-4) | Bull use; episode scope |
| Time more important than price | ✔ p. 12 | Primary/contrast roles; matched contrast (R-10, RQ-3) | Any statistic |
| Calendar days | ✔ p. 61; Δ3-06 | Applied to Rule 8 | Rule 8's own unit |
| High/low measurement | ✔ p. 11, p. 63 (inference) | Running form; literal windows; first-occurrence ties (OD-8, RQ-8, OPEN-4.5) | Form; windows; ties |
| 3-Day Chart | ✔ (discretionary in practice) | Strict K3 (R-1) | K3 as Rule 8's detector |
| Market state | Rule 9 | S9 (OD-3, OPEN-3b) | Precondition; bear equivalence |
| Reactions | "decline or reaction"; near-extreme 2-day moves; "3-day reaction" (p. 66) | 1/2-day bound; reaction ≠ K3; adjacency to a fresh leg high; top excludes reaction highs (OD-2, OPEN-2.x, RQ-6, RQ-7) | Every mechanical element |
| Reactions in the time leg | "decline" only | Excluded (OPEN-2.4) | — |
| Episodes, latches, D−1, HF/DB, 1m, basis normalization, substrate start, no-bar rule, termination | — | ✔ | ✔ |
| Rule 10 outcome; horizon; pooling | Rule 10 is a separate rule | ✔ | ✔ |

---

## 3. Mathematical definitions

### 3.1 Primitives

| Symbol | Definition | Provenance |
|---|---|---|
| 𝒟; d⁻; cal(d) | NSE sessions; the previous session; calendar date | [LOD] |
| H_d^(D), L_d^(D) | EOD high/low of session d < D on the as-of-D basis | [LOD] R-13, RQ-9 |
| h_τ^(D), l_τ^(D) | HF: high/low of the genuine 1m bar τ on D, normalized to as-of-D | [LOD] RQ-9 = A+x |
| G(D) | HF: TRUE iff D has ≥ 1 genuine (`is_synthetic = FALSE`) 1m bar for the stock | [LOD] RQ-11 |
| LL, HH, HL | Strict day-over-day comparisons on EOD bars | [LOD] R-1 |
| ℓ_d; c; u | K3 line state; down-switch close; up-switch close | [GS] Δ2-10; [LOD] R-1 |
| UP line of a leg | Sessions from its up-switch close through the session before the next down-switch run completes (the line moves to the top of the 3rd day) | [GS] Δ2-10; [LOD] R-1 |
| X⁺ = (h, d_h, c) | h = max EOD high over the UP line ended at c; d_h = first session with that high | [LOD] R-1, OPEN-4.1/4.5 |
| X⁻ = (l, d_l, u) | Mirror | [LOD] |
| S9_d | Per OPEN-3b = A | [LOD] |
| 𝔉(D) | Daily-derived state as of D⁻ | [LOD] |

**Basis note.** Every historical value used on D is expressed as of D. A corporate action between a
value's session and D re-bases it. Exclusion windows are imported from G-7.

### 3.2 Episode and membership (SC-3 = A, RQ-1 = A)

- E = (σ, a, b): maximal [a, b) with S9 = σ ∈ {BULL, BEAR}. a is a switch close; b is the next
  reversal or cessation (or +∞). A return to σ after NONE opens a new episode. [LOD] OD-5
- **K3 move membership:** confirmation close c_M with a ≤ c_M < b. [LOD] SC-3, RQ-1
- **Reaction membership:** completion close with a ≤ close < b. A reaction completion close cannot
  coincide with a switch close: it is a non-LL session inside an UP line, while a down-switch close is
  LL and an up-switch close ends a DOWN line. — **RESOLVED**
- **Consequence (RQ-1 = A):** a K3 move confirmed before a is never a member of E, even if it completes
  at a or later. In an up-switch-created episode, the first K3 decline confirmed in E has an empty time
  ledger and cannot trigger. — **RESOLVED**

### 3.3 Current move

- **Bull:** M = (X⁺, c, u), S9_c = BULL, member of E. P_S = h, d_S = d_h.
- **Bear:** mirror, with P_S = l, d_S = d_l.
- **Active on D** iff D ∈ (c_M, termination close]; the terminating session is active. — **RESOLVED**
- S9 cannot change strictly inside the active span (OPEN-3b = A). — **RESOLVED**

### 3.4 Time leg

| Symbol | Definition | Status |
|---|---|---|
| el_M(D) | cal(D) − cal(d_S) | LOCKED (OPEN-4.2/4.4) |
| dur(M′) | Bull: cal(d_l′) − cal(d_h′) (K3 swing dates); bear mirror | Carried (R-5 "high date to low date"). **Endpoint consistency: OPEN-A** |
| 𝒰_T(M) | {M′ : same-type K3 move; member of E; completed (terminating close) ≤ d_S} | LOCKED (OPEN-1, OPEN-2.4, RQ-1, RQ-5) |
| R_T(M) | max_{𝒰_T} dur; undefined if 𝒰_T = ∅ (cannot trigger) | LOCKED (OD-1) |
| TC_M(D) | M active on D ∧ 𝒰_T ≠ ∅ ∧ el_M(D) > R_T | LOCKED (OD-9) |

**Constancy (RESOLVED).** A same-type K3 reference terminates at u′ ≤ d_S (the UP line containing d_S
begins at u′). Nothing enters 𝒰_T while M is active, so R_T is constant, and RQ-5's cut is
automatically satisfied for K3 references.

### 3.5 Magnitudes (RQ-8 = A, RQ-9 = A+x)

```
Current bull M at instant τ on session D:
  LowHist_M(D) = min{ L_d^(D) : d_S < d ≤ D⁻ }                              (+∞ if empty)
  LowObs_M(τ)  = HF: min{ l_τ′^(D) : genuine 1m bars τ′ ≤ τ on D }  (requires G(D))
                 DB: L_D^(D)                                         (observable at D's close)
  run_M(τ)     = P_S^(D) − min(LowHist_M(D), LowObs_M(τ))
Reference K3 decline M′ (used on D):
  mag^(D)(M′)  = h′^(D) − min{ L_d^(D) : d_h′ < d ≤ u′ }
Reference bull reaction ρ (used on D):
  mag^(D)(ρ)   = Top_ρ^(D) − L_{s_k}^(D)
Bear: mirror with highs (current rally: max over highs − P_S; reference rally: max{H : d_l′ < d ≤ c′} − l′).
```

- Reaction magnitude equals the literal window over its own sessions (s₁ … s_k), because strict LL
  makes L_{s_k} the minimum. It is consistent with RQ-8 = A. — **RESOLVED**
- References are historical, hence EOD in both profiles. — **RESOLVED**

### 3.6 Reaction (bull only) — RQ-6 = A, RQ-7 = B

| Element | Definition | Status |
|---|---|---|
| Leg running high | RH(d) = max{ H_x : x in the current K3 UP line, x ≤ d } | LOCKED (OPEN-2.2, R-1) |
| Establishing session | Session e whose high set RH(e) | LOCKED (RQ-7 = B). **Equal-high case: OPEN-D** |
| Reaction ρ | Consecutive LL sessions s₁ (, s₂), k ∈ {1, 2}, inside the UP line, with **s₁ = the session immediately after an establishing session e** (e = s₁⁻); followed by a non-LL session; a 3rd consecutive LL makes the run a K3 switch (not a reaction) | LOCKED (OPEN-2.1 = A, OPEN-2.3 = B, RQ-7 = B) |
| Top_ρ | RH(e) = H_e: the running leg high immediately before s₁. **Highs of s₁ … s_k are excluded** | LOCKED (RQ-6 = A) |
| Completion | Close of the first following non-LL session; usable from the next session | RESOLVED |
| Membership / precedence | Completion close ∈ [a, b) (RQ-1); completion close ≤ d_S of the current move (RQ-5) | LOCKED |
| Outside-day s₁ followed by LL s₂ | Continuation of ρ, or a new reaction from s₁ as a new establishing session? | **OPEN-E** |
| Bear "higher-high" structures | Not operative (C-4, OPEN-2.4) | NC-1 |

### 3.7 Price leg

| Symbol | Definition | Status |
|---|---|---|
| 𝒰_P(M) bull | {ledger K3 declines of E completed ≤ d_S} ∪ {qualifying reactions, members of E, completed ≤ d_S} | LOCKED (C-4, RQ-1, RQ-5, RQ-6, RQ-7) |
| 𝒰_P(M) bear | {ledger K3 rallies of E completed ≤ d_S} | LOCKED |
| R_P^(D)(M) | **max over 𝒰_P of mag^(D)**, one combined maximum; undefined if 𝒰_P = ∅ | LOCKED (RQ-2 = A) |
| PC_M(τ) | M active on D ∧ 𝒰_P ≠ ∅ ∧ run_M(τ) > R_P^(D) | LOCKED (OD-8, OD-9) |
| Price flag | First PC_M in E while the price latch μ(E) = FALSE, recorded independently of 𝒰_T (RQ-3 = C); μ(E) := TRUE | LOCKED (RQ-3 = C, RQ-4 = A). No-bar HF: **OPEN-C** |
| Matched candidate | M with 𝒰_T ≠ ∅ ∧ 𝒰_P ≠ ∅ | LOCKED (RQ-3 = C) |

**Structural note (RESOLVED, derived).** For bull, every K3 decline in 𝒰_T is also in 𝒰_P, so
𝒰_T ≠ ∅ ⇒ 𝒰_P ≠ ∅. For bear, 𝒰_P = 𝒰_T as sets of moves. **Matched candidates = candidates with
𝒰_T ≠ ∅** in both directions. Unmatched price-only candidates occur only for bull, when the ledger
holds qualifying reactions but no completed K3 decline. This is what makes OPEN-F bite.

### 3.8 Events, latches and profile rules

| Rule | Definition | Status |
|---|---|---|
| D*_M | min{ D : TC_M(D) } | LOCKED (OD-7) |
| λ(E), μ(E) | Time latch and price latch; both FALSE when E opens | LOCKED (OD-4, RQ-4) |
| DB GF-10 event | ¬λ(E) → event at D*_M; λ(E) := TRUE | LOCKED |
| HF GF-10 event | ¬λ(E) ∧ G(D*_M) → event at the first genuine 1m bar of D*_M; λ(E) := TRUE | LOCKED (X-1, OD-7). Timestamp label: imported OPEN-6 |
| HF no-bar time crossing | ¬λ(E) ∧ ¬G(D*_M) → no event; λ(E) := TRUE | LOCKED (RQ-11 = D) |
| HF substrate start | λ(E) := FALSE for every open episode; ledgers keep EOD history | LOCKED (RQ-10 = B, X-2 = A). Already-crossed candidates: **OPEN-B**. Price latch μ: **OPEN-G** |
| Price flag observation | HF: first genuine 1m bar τ with PC_M(τ). DB: session close of D | LOCKED (OD-7, RQ-9) |
| Formal contrast inputs | Time scores and price scores over matched candidates only | LOCKED (RQ-3 = C). Price-latch state within the matched set: **OPEN-F** |
| DB end / profile separation | DB events stop at the end of DB availability; a DB event and an HF event in one calendar episode are never pooled | RESOLVED (X-2 = A); NC-6 |

---

## 4. State machine and timeline (per stock; bull shown, bear mirrors)

```text
State (read on D from 𝔉(D), re-based as-of-D):
  K3: ℓ, runs, swing points (first-occurrence dates), leg running high RH and its establishing session
  S9: σ; episode E = (σ, a); time latch λ(E); price latch μ(E)
  Ledger(E): member K3 declines (dur, literal mag, terminating close) ; member qualifying reactions (mag, completion close)
  Candidate M: (P_S, d_S, c) or none
  Profile: DB | HF
```

| Phase | What happens | Locks |
|---|---|---|
| **A. UP line, no bull candidate** | On each close, update RH. A session e that sets RH is an establishing session (equal highs: OPEN-D). If the next session s₁ is LL, a reaction starts, with Top = H_e. If s₂ is also LL, it is a 2-day reaction; a 3rd LL turns the run into a K3 switch (not a reaction). On the first following non-LL close the reaction completes; if E is open (BULL) it enters Ledger(E) with mag = H_e − L_{s_k}. Outside-day s₁ followed by LL: OPEN-E | OPEN-2.1/2.2/2.3/2.5; RQ-6 = A; RQ-7 = B; RQ-1 = A |
| **B. Down-switch close c** | X⁺ = (h, first d_h) confirmed. S9 recomputed; on a change E closes (ledger, λ and μ discarded), and a new E opens at a = c with an empty ledger and λ = μ = FALSE. If S9_c = BULL, M = (X⁺, c) is a candidate member of the episode current at c, including one created at c (SC-3), even if d_S < a. 𝒰_T and 𝒰_P are fixed from ledger items completed ≤ d_S (RQ-5); R_T and R_P (combined maximum, RQ-2) follow. A K3 move confirmed before a is never in the new ledger (RQ-1) | R-1; OPEN-3b; SC-3; RQ-1; RQ-2; RQ-5 |
| **C. Active session D ∈ (c, u]** | **Time:** if ¬λ ∧ 𝒰_T ≠ ∅ ∧ el > R_T → DB: event at D; HF ∧ G(D): event at the first genuine bar; HF ∧ ¬G(D): no event. In all cases λ := TRUE. **Price:** if ¬μ ∧ 𝒰_P ≠ ∅ and run(τ) > R_P → price flag (HF: the genuine 1m bar; DB: D's close); μ := TRUE. Recorded whether or not M is matched (RQ-3). HF no-bar session: OPEN-C. New lows extend run; no clock reset; no termination on a new high | OD-7/8/9; OPEN-4.x; C-7; RQ-3/4/8/9/11 |
| **D. Up-switch close u** | M is active on u and ends after it. X⁻ confirmed. If E continues, M enters Ledger(E): dur = cal(d_l) − cal(d_h) (OPEN-A); mag over (d_h, u]. Its membership is by its confirmation close c (RQ-1), already fixed | OPEN-4.3; RQ-1; RQ-8 |
| **E. Latches set** | λ = TRUE: no further GF-10 events in E. μ = TRUE: no further price flags in E. Each latch is independent (RQ-4). Ledger updates continue (inert for a set latch) | OD-4/6; RQ-4; RQ-11 |
| **F. S9 reset** (a switch close) | E closes; its ledger, λ and μ are discarded. If the new σ ∈ {BULL, BEAR}: a new E with an empty ledger and λ = μ = FALSE. A move confirmed at that close joins (SC-3). A move confirmed earlier and completing at that close does **not** (RQ-1) | OD-5; SC-3; RQ-1 |
| **G. HF substrate start** | Every open episode: λ := FALSE (RQ-10 = B). K3, S9, ledger and candidate carried from EOD (X-1/X-2). μ at the start: OPEN-G. Candidate already past el > R_T (or run > R_P) on a pre-substrate date: OPEN-B | RQ-10 = B; X-1/X-2 = A |
| **H. Formal contrast** | T(time) and T(price) computed over matched candidates only. Which price-latch state applies within that set: OPEN-F | RQ-3 = C; R-10; G-4 |

**Timelines (schematic):**

```text
Up-switch-created BULL episode (RQ-1 = A):
  M₀ decline confirmed at c₀ (S9 NONE) … completes at u = a; S9: NONE → BULL; E opens at a
  M₀ ∉ Ledger(E)   (confirmed before a)
  UP leg in E: e sets RH, s₁ LL, non-LL → reaction ρ₁ ∈ Ledger(E)
  down-switch c₁ → M₁: 𝒰_T = ∅ (no GF-10 possible); 𝒰_P = {ρ₁} if ρ₁ completed ≤ d_S(M₁)
        → price flag possible (recorded, unmatched; RQ-3 = C); may set μ(E) (RQ-4) → OPEN-F

SC-3 (down-switch creates BULL):
  d_h … [LL][LL][LL = c = a]; M member of E; d_S < a; reactions of that UP leg completed before a ∉ Ledger(E)
  → 𝒰_T = 𝒰_P = ∅; M cannot trigger or flag; at u, M enters Ledger(E)

Reaction adjacency (RQ-6 = A, RQ-7 = B):
  e (new leg high H_e) → s₁ LL → s₂ LL → s₃ non-LL: ρ = {s₁, s₂}, Top = H_e, mag = H_e − L_{s₂}
  e → x (no new high, not LL) → s LL: not a reaction (s₁ not immediately after an establishing session)
```

---

## 5. Newly surfaced OPEN questions

Every item below arises from a **combination of locked decisions**. None reopens a lock.

**OPEN-A — Reference duration endpoint vs literal price extreme**

| Field | Entry |
|---|---|
| Ambiguity | dur(M′) ends at the K3 swing-low date d_l′. Under RQ-8 = A the reference price extreme is the literal minimum over (d_h′, u′], which can fall on an earlier session than d_l′ |
| Why it matters | Changes R_T, and so the GF-10 event population |
| Choices | (a) Keep d_l′ (time K3-based, price literal; disclose the dual endpoint). (b) Use the first-occurrence date of the literal minimum. (c) Other |
| Source | p. 63 measures a duration from "last high" to "extreme low" [GS] (inference only) |
| Classification | Operator-defined |
| Dependencies | None |

**OPEN-B — HF candidate already crossed before the substrate start (time and price legs)**

| Field | Entry |
|---|---|
| Ambiguity | RQ-10 = B sets λ FALSE at the substrate start. A candidate active at the start may already have satisfied el > R_T (or run > R_P) on an EOD-era date |
| Why it matters | Emitting on the first HF session would place a DB-era crossing into the HF population, in tension with X-2 = A and OD-7. Not emitting leaves the episode unlatched for later candidates |
| Choices | (a) Emit on the first HF session with G = TRUE. (b) Candidate spent for that leg: no HF event or flag from it, latch stays FALSE. (c) Exclude candidates active at the start from HF |
| Source | None |
| Classification | Operator-defined |
| Dependencies | OPEN-G (price-leg part) |

**OPEN-C — Price leg on an HF session with no genuine 1m bar**

| Field | Entry |
|---|---|
| Ambiguity | RQ-11 = D covers the time leg. RQ-9 = A+x gives the observation-session price term no source when G(D) = FALSE. RQ-4 = A adds a price latch whose behaviour here is unstated |
| Why it matters | Price-flag population and μ(E) |
| Choices | (a) Not evaluated that session; D's EOD low enters as history from D+1. (b) Use D's EOD low for that session (departs from RQ-9 = A for that session). (c) Mirror RQ-11 = D: no flag, μ := TRUE if the EOD low shows a crossing |
| Source | None |
| Classification | Operator-defined |
| Dependencies | None (RQ-3/RQ-4 now locked) |

**OPEN-D — "Established" under equal highs (RQ-7 = B)**

| Field | Entry |
|---|---|
| Ambiguity | If session e has H_e equal to the existing running leg high (not strictly above it), did e "establish" the running extreme for RQ-7 = B? |
| Why it matters | Decides whether an LL session immediately after an equal-high session starts a qualifying reaction. Changes the reaction set, so R_P |
| Choices | (a) Only a strictly new high establishes (the first occurrence keeps the role, consistent in spirit with OPEN-4.5). (b) An equal high also establishes |
| Source | None |
| Classification | Operator-defined |
| Dependencies | None |

**OPEN-E — Outside-day reaction session followed by another LL session**

| Field | Entry |
|---|---|
| Ambiguity | s₁ is LL and also makes a new leg high (outside day). Under RQ-6 = A its high is excluded from Top_ρ, yet s₁ establishes a new RH. If s₂ is LL, is s₂ (i) the second session of ρ (Top = H_{s₁⁻}), or (ii) the first session of a new reaction immediately after the establishing session s₁ (Top = H_{s₁}), or (iii) both? |
| Why it matters | Changes reaction magnitudes and count, so R_P |
| Choices | (i) Continuation only. (ii) New reaction only (ρ ends at s₁ as a 1-day reaction). (iii) Both recorded. (iv) An outside-day LL session cannot start or continue a reaction |
| Source | None |
| Classification | Operator-defined |
| Dependencies | OPEN-D (if s₁'s high equals RH) |

**OPEN-F — Price-latch state for the matched contrast (RQ-3 = C × RQ-4 = A)**

| Field | Entry |
|---|---|
| Ambiguity | Price flags are recorded over all candidates with an episode-level first-per-episode latch μ. An **unmatched** bull candidate (𝒰_T = ∅, reactions only) can set μ before any matched candidate exists, so the matched candidates' price scores would be suppressed by a flag outside the contrast set |
| Why it matters | Changes T(price) within the formal contrast, and so the R-10 specificity leg |
| Choices | (a) Contrast uses the independent record as-is (μ from all candidates). (b) Contrast uses a second price latch evaluated over matched candidates only. (c) Contrast price score ignores latching within the matched set |
| Source | None |
| Classification | Operator-defined |
| Dependencies | Coupled to imported G-4 |

**OPEN-G — Price latch at the HF substrate start (RQ-4 = A × RQ-10 = B)**

| Field | Entry |
|---|---|
| Ambiguity | RQ-10 = B was ruled for the GF-10 latch. It does not state whether the RQ-4 price latch μ is also reset to FALSE at the substrate start, or reconstructed from EOD history |
| Why it matters | HF price-flag population near the substrate start |
| Choices | (a) μ := FALSE (parallel to RQ-10 = B). (b) μ reconstructed causally from EOD-era crossings. (c) Other |
| Source | None |
| Classification | Operator-defined |
| Dependencies | OPEN-B (price-leg part) |

**Imported, open elsewhere (not re-analysed):**
- Gaps and preconditions: G-4 (contrast p), G-5, G-6, G-7 (also needed for RQ-9 = x re-basing), G-8,
  G-9; P-1 … P-5.
- Draft items: OPEN-6 (timestamp label), OPEN-11 (weekly score mapping), OPEN-12 (outcome window
  anchor).
- The R-13 external CA list (P-2), an implementation input for RQ-9 = x.

---

## 6. Checks

| # | Item | v0.3 verdict |
|---|---|---|
| 6.1 | "Completed" reference move | RESOLVED: K3 move at its terminating switch close; reaction at the first following non-LL close |
| 6.2 | Eligibility at confirmation vs next session | RESOLVED: no difference (D−1 freeze; RQ-5 = A) |
| 6.3 | Current/reference alignment under D−1 | RESOLVED: RQ-1 = A, RQ-5 = A |
| 6.4 | Same price basis | RESOLVED: RQ-9 = A+x |
| 6.5 | Equal highs/lows in references | RESOLVED for K3 swing points. Equal highs for reaction adjacency: OPEN-D |
| 6.6 | Bull/bear universe separation | RESOLVED |
| 6.7 | K3 moves vs reactions | RESOLVED except OPEN-D, OPEN-E |
| 6.8 | May a reaction be the greatest reference? | RESOLVED: yes, one combined maximum (RQ-2 = A) |
| 6.9 | Time comparison | RESOLVED except OPEN-A (reference endpoint) and OPEN-B (substrate start) |

### 6.10 Disclosure notes (no decision)

| ID | Note |
|---|---|
| NC-1 | Bear "higher-high" reaction structures do not become K3 on a 3rd session; not operative |
| NC-2 | The K3 switch asymmetry makes bull and bear moves structurally different (disclose under G-2(b) pooling) |
| NC-3 | Events concentrate structurally on a move's first active session when R_T is below the confirmation lag |
| NC-4 | "Reaction ≠ K3" is an operator decision; Gann uses "3-day reaction" (Δ3-04) and multi-week "reaction" (Δ2-08) |
| NC-5 | HF: an observation session's 1m low is replaced by its EOD low from the next session onward; the two can differ |
| NC-6 | One calendar episode can yield a DB event and an HF event; never pooled |
| NC-7 | RQ-10 = B (pre-substrate crossings do not latch) and RQ-11 = D (in-substrate no-bar crossings latch) differ by circumstance; consistent, disclosed |
| NC-8 | Under RQ-1 = A, every up-switch-created episode's first K3 candidate has 𝒰_T = ∅; under SC-3 every down-switch-created episode's first candidate has 𝒰_T = 𝒰_P = ∅ (derived) |
| NC-9 | Under RQ-2 = A with RQ-7 = B, a qualifying reaction can set R_P above every K3 decline in the ledger (derived; not a result) |

---

## 7. Contradiction audit (re-run after the correction)

### 7.1 Result

**v0.2: FAIL.** One provenance error (P-1 below). Its mechanical content was otherwise consistent
with the locks it contained.

**v0.3: PASS.**
- No contradiction among the 43 locked decisions in §9: OD-1 … OD-10, C-1 … C-7, X-1, X-2, OPEN-3b,
  OPEN-4.1 … 4.5, SC-3, OPEN-2.1 … 2.5, OPEN-1, RQ-1 … RQ-11.
- No contradiction between §1.2, §2, §3, §4 and §9.
- Seven OPEN questions remain (OPEN-A … OPEN-G), each a gap left by a combination of locks.
- One reading hazard is recorded: OPEN-B choice (a) vs X-2 = A / OD-7.

### 7.2 Issues checked

| ID | Check | Result |
|---|---|---|
| P-1 | v0.2 recorded RQ-1 … RQ-7 as OPEN / not recorded | **FAIL in v0.2 → corrected** (CL-1, §9) |
| A-1 | RQ-1 = A vs SC-3 = A (both membership by confirmation close) | Consistent |
| A-2 | RQ-1 = A vs OPEN-1 = A ("first qualifying move cannot trigger") | Consistent (NC-8) |
| A-3 | RQ-5 = A vs K3 references (u′ ≤ d_S always) | Consistent; binding only on reactions |
| A-4 | RQ-5 = A vs SC-3 (d_S < a) | Consistent; the SC-3 first candidate has empty ledgers |
| A-5 | RQ-6 = A vs RQ-7 = B (Top = H_e of the establishing session immediately before s₁) | Consistent. Gaps OPEN-D (equal highs) and OPEN-E (outside-day continuation) |
| A-6 | RQ-6 = A / RQ-7 = B vs OPEN-2.2 = A (running leg extreme) and OPEN-2.5 = B (structural near-extreme) | Consistent: RQ-7 = B specifies the structural condition |
| A-7 | RQ-2 = A vs RQ-8 = A (reaction magnitude = literal window over its sessions) | Consistent (§3.5) |
| A-8 | RQ-2 = A vs OPEN-2.4 = A (reactions only in the bull price leg) | Consistent |
| A-9 | RQ-3 = C vs RQ-4 = A | No contradiction; gap **OPEN-F** |
| A-10 | RQ-3 = C matched set vs time events | Consistent: matched ⇔ 𝒰_T ≠ ∅ (derived), so every GF-10 event is on a matched candidate |
| A-11 | RQ-4 = A vs RQ-10 = B | Gap **OPEN-G** |
| A-12 | RQ-4 = A vs RQ-11 = D | Gap **OPEN-C** |
| A-13 | RQ-8 = A vs dur endpoint (R-5 / R-1) | Gap **OPEN-A** |
| A-14 | RQ-10 = B vs X-2 = A / OD-7 | Gap **OPEN-B** (hazard under (a)) |
| A-15 | RQ-10 = B vs RQ-11 = D | Consistent (NC-7) |
| A-16 | RQ-9 = A+x vs D−1 freeze | Consistent: history ≤ D⁻ from EOD; D from 1m |
| A-17 | §2 attribution | No [LOD] item attributed to Gann; "first time" bear-only [GS] throughout; S9 bear never called Gann's condition — PASS |
| A-18 | §9 ↔ §1.2 / §3 / §4 mapping | Every ledger row maps to a section; every OPEN appears in §5 — PASS |

---

## 8. Future work — what empirical testing must NOT decide

**Definitional (before any data read; never from results):**
- OPEN-A … OPEN-G.
- Every lock in §9.
- Any later threshold, window, adjacency or source rule.

No choice may be justified by event counts, coverage, "too few/many events", IC, Sharpe, surrogate p,
contrast p, size-check outcome or any O-R10 association.

**Empirical (pre-registered read, after freeze only):**
- Association of GF-10 events with O-R10 beyond the surrogate null (R-14).
- T(time) vs T(price) on matched candidates (R-10, RQ-3 = C, G-4).
- Descriptive population statistics: reported, never used to revise a definition.

**Implementation (code review and deterministic tests, not results):**
- K3/S9 correctness (memo §5).
- The establishing-session and adjacency logic.
- D−1 freeze enforcement.
- Causal prefix invariance and byte-identical replay.
- As-of-D re-basing and 1m normalization (ratio test).
- G(D) via `is_synthetic = FALSE`, `bar_labeling.py`, GAP sessions and `SPECIAL_SESSIONS`.
- Independent latches λ and μ.
- First-occurrence ties.
- The timestamp label (imported OPEN-6).

---

## 9. Decision ledger

| ID | Decision | Status | Applied in |
|---|---|---|---|
| OD-1 | Time leg: greatest qualifying previous decline/rally | LOCKED | §1.2-14; §3.4 |
| OD-2 | "Decline or reaction" preserved; 1/2/3-day framework; reaction ≠ K3 | LOCKED | §1.2-15; §3.6 |
| OD-3 | Bear = S9 bear | LOCKED | §1.2-5 |
| OD-4 | First exceedance per S9 episode | LOCKED | §1.2-21; §3.8 |
| OD-5 | Reset on S9 reversal or cessation | LOCKED | §1.2-11; §3.2; §4 F |
| OD-6 | Symmetric bull/bear | LOCKED | §1.2-21 |
| OD-7 | First objectively observable crossing | LOCKED | §1.2-19; §3.8 |
| OD-8 | Running extreme | LOCKED | §1.2-16; §3.5 |
| OD-9 | Strict `>` | LOCKED | §1.2-18; §3.4; §3.7 |
| OD-10 | Finest available resolution | LOCKED (via HF/DB) | §1.2-1 |
| C-1/C-2/C-3 | HF 1m where available; DB daily elsewhere; never pooled; D−1 freeze of K3/S9 | LOCKED | §1.2-1, 6 |
| C-4 | K3-based eligibility; current move = K3 decline/rally; reactions only as bull price comparator | LOCKED | §1.2-7, 15, 17 |
| C-5 | OD-1 supersedes "immediately preceding" | LOCKED | §3.4 |
| C-6 | OD-7 supersedes week-end timing | LOCKED | §1.2-19 |
| C-7 | Move-level reset + episode-level first-event latch | LOCKED | §1.2-21/24; §4 D/E |
| X-1 = A | HF: 1m detection; EOD K3/S9 context, pre-substrate allowed | LOCKED | §1.2-1; §4 G |
| X-2 = A | Never pool populations; HF may use EOD lookback | LOCKED | §1.2-1; §3.8 |
| OPEN-3b = A | S9 on confirmed K3 points; changes only at a switch close; D−1 freeze | LOCKED | §1.2-4; §3.3 |
| OPEN-4.1 = A | Start at the K3 swing high / swing low | LOCKED | §1.2-7; §3.3 |
| OPEN-4.2 = A | Clock from the starting-extreme date | LOCKED | §1.2-9; §3.4 |
| OPEN-4.3 = A | Terminate at confirmed K3 reversal; no intraday break | LOCKED | §1.2-10; §3.3 |
| OPEN-4.4 = A | Time endpoint = observation date | LOCKED | §1.2-9; §3.4 |
| OPEN-4.5 = A | First occurrence of an equal starting extreme | LOCKED | §1.2-8; §3.1 |
| SC-3 = A | Move confirmed at the creating switch is included; not truncated | LOCKED | §1.2-12; §3.2; §4 B |
| OPEN-2.1 = A | 1/2-day LL (bull) / HH structures; 3rd session → K3 | LOCKED | §3.6 |
| OPEN-2.2 = A | Reaction starts from the running extreme of the preceding K3 leg | LOCKED | §3.6 |
| OPEN-2.3 = B | Reaction bounded to the 1/2-day structure | LOCKED | §3.6 |
| OPEN-2.4 = A | Reactions excluded from the time leg; bull price clause only | LOCKED | §1.2-14/17 |
| OPEN-2.5 = B | Near-extreme structural, not numeric | LOCKED | §3.6 |
| OPEN-1 = A | Current S9 episode; greatest completed previous same-type move; no carryover; first move cannot trigger | LOCKED | §1.2-13; §3.4; §3.7 |
| **RQ-1 = A** | Reference membership by confirmation close; a move confirmed under the previous episode is not carried into the new one | **LOCKED** | §1.2-12; §3.2; §4 B/F |
| **RQ-2 = A** | Bull price reference = one combined maximum over qualifying previous K3 declines and qualifying reactions | **LOCKED** | §1.2-17; §3.7 |
| **RQ-3 = C** | Price flags recorded independently; the formal T(time) − T(price) contrast uses matched candidates where both references exist | **LOCKED** | §1.2-22/23; §3.7; §4 C/H |
| **RQ-4 = A** | Independent first-per-episode price latch | **LOCKED** | §1.2-22; §3.8; §4 E |
| **RQ-5 = A** | Reference completed on or before the current move's starting-extreme date | **LOCKED** | §1.2-13; §3.4; §3.7 |
| **RQ-6 = A** | Reaction top excludes highs made during the reaction; uses the running K3-leg extreme immediately before the reaction | **LOCKED** | §1.2-15; §3.6 |
| **RQ-7 = B** | Reaction must begin immediately after the session that established the running K3-leg extreme | **LOCKED** | §1.2-15; §3.6; §4 A |
| **RQ-8 = A** | Literal running-price window for current and reference moves | **LOCKED** | §1.2-16; §3.5 |
| **RQ-9 = A+x** | History = EOD; observation session = genuine 1m; normalize to as-of-D | **LOCKED** | §1.2-1/2/16; §3.1; §3.5 |
| **RQ-10 = B** | HF GF-10 latch FALSE at substrate start | **LOCKED** | §3.8; §4 G |
| **RQ-11 = D** | HF no-bar time crossing: no event, latch set | **LOCKED** | §3.8; §4 C/E |
| OPEN-A | Reference duration endpoint vs literal price extreme | **OPEN (surfaced v0.2)** | §5 |
| OPEN-B | HF candidate crossed before the substrate start (time and price) | **OPEN (surfaced v0.2; extended v0.3)** | §5 |
| OPEN-C | Price leg on a no-bar HF session | **OPEN (surfaced v0.2)** | §5 |
| OPEN-D | "Established" under equal highs (RQ-7) | **OPEN (surfaced v0.3)** | §5 |
| OPEN-E | Outside-day reaction session followed by LL | **OPEN (surfaced v0.3)** | §5 |
| OPEN-F | Price-latch state for the matched contrast | **OPEN (surfaced v0.3)** | §5 |
| OPEN-G | Price latch at the HF substrate start | **OPEN (surfaced v0.3)** | §5 |

---

## 10. Recommended decision order (OPEN items only)

| Step | Decision | Depends on |
|---|---|---|
| 1 | OPEN-A | — |
| 2 | OPEN-D | — |
| 3 | OPEN-E | OPEN-D |
| 4 | OPEN-F | — |
| 5 | OPEN-C | — |
| 6 | OPEN-G | — |
| 7 | OPEN-B | OPEN-G |

---

**NO CODE. NO BACKTEST. NO EMPIRICAL TESTING. NO MARKET OUTCOMES READ. NO LOCKED DECISION REOPENED.
NOT FROZEN. NOT AN IMPLEMENTATION SPECIFICATION.**
