# GF-10 Mechanical Decision Record — v0.4

**Date:** 2026-09-17

**Status: CONSOLIDATED DECISION RECORD — NOT AN IMPLEMENTATION SPECIFICATION, NOT A FREEZE.**
- No code, backtest, empirical test, optimization or performance analysis was performed.
- No market data or outcome was read. Nothing is frozen or hashed.
- **No locked decision is reopened.**

**Supersedes:** v0.3 (commit `d9a9119`), which is kept unchanged. Earlier versions: v0.2 (superseded;
provenance error) and v0.1 (`59e25da`).

**New in this version:** operator rulings of 2026-09-17 on OPEN-A … OPEN-G.

| Item | Operator ruling (verbatim label and wording) | Maps to v0.3 option |
|---|---|---|
| OPEN-A | **A** — K3 swing date for time; literal extreme for price | (a) |
| OPEN-B | **B** — pre-HF-crossed candidate is spent; no HF event/latch | (b) |
| OPEN-C | **A** — no HF price evaluation without genuine 1m | (a) |
| OPEN-D | **A** — only strictly new extreme establishes anchor | (a) |
| OPEN-E | **A** — outside-day reaction continues normally | (i) *(v0.3 labelled the choices i–iv)* |
| OPEN-F | **A** — matched contrast independent of price latch | **see ⚠ CONF-1** |
| OPEN-G | **A** — HF price latch starts FALSE | (a) |

> **⚠ CONF-1 — Label/wording mismatch on OPEN-F (recorded, not resolved).** In v0.3, option **(a)**
> read *"Contrast uses the independent record as-is (μ from all candidates)"*, i.e. the contrast
> **does** inherit the price latch. The operator's wording, *"matched contrast independent of price
> latch"*, describes v0.3 option **(c)** (*"contrast price score ignores latching within the matched
> set"*), or possibly **(b)**. This record applies the **wording**, because it is the explicit
> statement of intent, and flags the letter for operator confirmation. If the operator meant v0.3
> (a), §3.7, §3.8, §4 H and §9 must be amended.

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
| Confirmation and newly surfaced OPEN | §5 |
| Future implementation / empirical work | §8 |

---

## 0. Change log from v0.3

| # | Change | Sections |
|---|---|---|
| CL-1 | OPEN-A … OPEN-G entered as LOCKED (OPEN-F by wording; CONF-1) | §9 |
| CL-2 | **OPEN-A = A:** reference duration keeps the K3 swing dates; reference price magnitude keeps the literal extreme. The dual endpoint is disclosed (NC-10) | §1.2-14/16; §3.4 |
| CL-3 | **OPEN-B = B:** an HF candidate that satisfied a leg's crossing on a pre-substrate session is **spent for that leg**: no HF event or flag from it, and no latch set | §3.8; §4 G |
| CL-4 | **OPEN-C = A:** no HF price evaluation on a session without a genuine 1m bar; that session's EOD extreme enters as history from the next session | §3.5; §3.8; §4 C |
| CL-5 | **OPEN-D = A:** only a strictly new running leg extreme establishes a reaction anchor | §3.6; §4 A |
| CL-6 | **OPEN-E = A (v0.3 (i)):** an outside-day reaction session continues the reaction normally; a following LL session is its 2nd session with the original top | §3.6; §4 A |
| CL-7 | **OPEN-F (by wording):** the matched contrast's price score does not depend on the episode price latch μ | §3.7; §3.8; §4 H |
| CL-8 | **OPEN-G = A:** HF price latch μ := FALSE at substrate start | §3.8; §4 G |
| CL-9 | Audit re-run. **One new ambiguity surfaced, OPEN-H** (per-candidate score definition and time/price latch symmetry inside the matched contrast, created by OPEN-F with OD-4). **CONF-1** added | §5; §7 |
| CL-10 | New disclosure notes NC-10 … NC-12 | §6.10 |

---

## 1. Locked mechanical model

### 1.1 Causal chain

```text
Authoritative EOD daily bars, R-13 as-of-t basis
  └─► K3 line state and confirmed swing points (R-1)
        └─► confirmed S9; changes only at a K3 switch close (OPEN-3b = A)
              └─► D−1 freeze; historical values re-based to as-of-D (RQ-9 = x)
                    └─► current K3 move from its first-occurrence swing extreme (OPEN-4.1/4.5)
                          └─► episode ledger: members by confirmation/completion close (RQ-1 = A, SC-3 = A); completed ≤ d_S (RQ-5 = A)
                                ├─► R_T = greatest same-type K3 duration on K3 swing dates (OD-1, OPEN-2.4 = A, OPEN-A = A)
                                └─► R_P = one combined maximum (RQ-2 = A) of literal-window magnitudes (RQ-8 = A, OPEN-A = A)
                                    over K3 moves (+ bull reactions: strictly-new-high anchor, top before reaction,
                                    outside-day continuation — RQ-6 = A, RQ-7 = B, OPEN-D = A, OPEN-E = A)
                                      └─► first objectively observable strict crossing (OD-7, OD-9)
                                          HF: EOD history + normalized genuine 1m on D; no genuine bar → no price evaluation (RQ-9, OPEN-C = A)
                                          DB: EOD
                                            ├─► time crossing ⇒ GF-10 EVENT; time latch λ (OD-4, C-7)
                                            │     HF no-bar session ⇒ no event, λ set (RQ-11 = D)
                                            └─► price crossing ⇒ price flag, recorded independently; price latch μ (RQ-3 = C, RQ-4 = A)
                                                  └─► formal T(time) − T(price) on matched candidates; price score not dependent on μ (RQ-3 = C, OPEN-F)
                                                  └─► HF substrate start: λ = μ = FALSE (RQ-10 = B, OPEN-G = A);
                                                      pre-substrate-crossed candidates spent per leg (OPEN-B = B)
```

### 1.2 Stage table with provenance

| # | Stage | Locked content | Provenance |
|---|---|---|---|
| 1 | Data | **HF:** genuine 1m on the observation session for detection; EOD for K3/S9 and all history, pre-substrate allowed. **DB:** EOD where 1m is unavailable. Populations never pooled; HF may use EOD lookback; DB-era observations never become HF events | [LOD] X-1 = A, X-2 = A, RQ-9 = A; [NES] |
| 2 | Price basis | All prices compared on D on the as-of-D basis; HF 1m normalized first | [LOD] R-13, RQ-9 = x; [NES] |
| 3 | K3 | Strict 3-Day Chart (memo §5 rows 1–13) | [GS] Δ2-10; [LOD] R-1; [GS] Δ3-02 |
| 4 | S9 | Confirmed tops and bottoms strictly rising = BULL; strictly falling = BEAR; else NONE; changes only at a switch close | [GS] Rule 9; [LOD] OPEN-3b = A; precondition [NES] |
| 5 | Bear condition | S9 BEAR | [LOD] OD-3; [GS] "declining for a long period of Time"; equivalence [NES] |
| 6 | D−1 freeze | Daily-derived facts on D as of D⁻ | [LOD]; [NES] |
| 7 | Current move | Bull: K3 decline from its swing high. Bear: K3 rally from its swing low | [GS] p. 11, p. 63; [LOD] C-4, OPEN-4.1 |
| 8 | Starting-extreme ties | First occurrence | [LOD] OPEN-4.5; [NES] |
| 9 | Time clock | Integer calendar days from the starting-extreme date to the observation date | [GS] Δ3-06, p. 61; [LOD] OPEN-4.2/4.4 |
| 10 | Termination | Confirmed opposite K3 switch; no intraday break | [LOD] OPEN-4.3 |
| 11 | Episode | Constant S9 ∈ {BULL, BEAR}; resets on reversal or cessation | [LOD] OD-5; [NES] |
| 12 | Membership | By confirmation close (K3 move) or completion close (reaction) in [a, b). SC-3 included; a move confirmed under the previous episode is not carried | [LOD] SC-3 = A, RQ-1 = A; [NES] |
| 13 | Ledger | Completed previous same-type members, completed ≤ d_S; no carryover; the first qualifying move cannot trigger | [GS] Δ2-01/02, Δ2-04; [LOD] OD-1, OPEN-1, RQ-1, RQ-5; [NES] |
| 14 | Time reference | R_T = greatest dur over ledger K3 moves; dur on **K3 swing dates** | [GS] "decline"; [GS] p. 63 (inference); [LOD] OPEN-2.4 = A, **OPEN-A = A** |
| 15 | Reaction (bull only) | 1–2 consecutive strict LL sessions in a K3 UP line, starting on the session immediately after a session that set a **strictly new** running leg high. Top = that high (reaction-session highs excluded). A reaction session that is an outside day **continues normally** (a following LL is its 2nd session, same top). A 3rd LL → K3 switch | [GS] Δ2-02, Δ2-10, Δ3-01; [LOD] OD-2, OPEN-2.1/2.2/2.3/2.5, RQ-6 = A, RQ-7 = B, **OPEN-D = A, OPEN-E = A**; [NES] |
| 16 | Magnitudes | Current: P_S to the literal extreme after the start session through the observation instant. Reference K3 move: literal extreme over its window through its terminating close (**not** K3 swing values). Reaction: top − last-session low. HF: EOD history + normalized genuine 1m on D (**no 1m term without a genuine bar**). DB: EOD | [GS] p. 63 (inference); [LOD] OD-8, RQ-8 = A, RQ-9 = A+x, **OPEN-A = A, OPEN-C = A**; [NES] |
| 17 | Price reference | Bull: one combined maximum over ledger K3 declines and reactions. Bear: maximum over ledger K3 rallies | [GS] Δ2-02; [LOD] C-4, OPEN-2.4, RQ-2 = A; "greatest" for price [NES] |
| 18 | Triggers | Strict `>` | [GS]; [LOD] OD-9 |
| 19 | Event timing | First objectively observable crossing | [GS] (inference); [LOD] OD-7, C-6 |
| 20 | GF-10 event | Time crossing. HF: first genuine 1m bar of the crossing session; no genuine bar → no event, λ set. DB: the crossing session | [GS] p. 12; [LOD] R-5, R-10, RQ-11 = D; [NES] |
| 21 | Time latch λ | One GF-10 event per stock per episode; reset only at a new episode; HF: FALSE at substrate start | [GS] "first time" (bear only); [LOD] OD-4/6, C-7, RQ-10 = B, RQ-11 = D; [NES] |
| 22 | Price flag and latch μ | Recorded independently of time eligibility; independent first-per-episode latch; HF: FALSE at substrate start; not evaluated on no-bar HF sessions | [LOD] RQ-3 = C, RQ-4 = A, **OPEN-C = A, OPEN-G = A**; [NES] |
| 23 | HF substrate start | λ = μ = FALSE. A candidate whose leg crossing held on a pre-substrate session is **spent for that leg** (no HF event or flag from it; no latch set) | [LOD] RQ-10 = B, **OPEN-B = B, OPEN-G = A**, X-2 = A; [NES] |
| 24 | Formal contrast | T(time) − T(price) over matched candidates (𝒰_T ≠ ∅ ∧ 𝒰_P ≠ ∅); the **price score does not depend on μ** | [LOD] RQ-3 = C, R-10, **OPEN-F (wording; CONF-1)**; [NES]. Per-candidate score and latch symmetry: **OPEN-H** |
| 25 | Move reset | Each qualifying K3 move is an independent candidate | [LOD] C-7 |
| 26 | Outcome (context) | O-R10 per R-2 / G-2(b) | [GS] Rule 10 (a separate rule); [NES]; [LOD] |

---

## 2. Source fact vs operator decision

| Rule | GANN SOURCE | LOCKED OPERATOR / RESEARCH | NOT ESTABLISHED BY SOURCE |
|---|---|---|---|
| Stocks as well as averages | ✔ p. 11 | — | — |
| Duration vs a previous decline/rally | ✔ Δ2-01 | Greatest; episode; membership; completed ≤ d_S; K3 swing dates (OD-1, OPEN-1, RQ-1, RQ-5, OPEN-A) | All of those |
| Points vs the previous decline or reaction (bull) / a previous rally (bear) | ✔ Δ2-02 | Combined maximum; literal extremes (RQ-2, RQ-8, OPEN-A) | "Greatest" for price; windows |
| Strict exceedance | ✔ | Equality = no trigger | Equality treatment |
| "The first time" | ✔ bear time and price clauses only | λ and μ per episode, both directions | Bull use; scope |
| Time more important than price | ✔ p. 12 | Roles; matched contrast; price score independent of μ (R-10, RQ-3, OPEN-F) | Any statistic |
| Calendar days | ✔ p. 61; Δ3-06 | Applied to Rule 8 | Rule 8's own unit |
| High/low measurement | ✔ p. 11, p. 63 (inference) | Running form, literal windows, ties | Form; windows; ties |
| 3-Day Chart | ✔ (discretionary) | Strict K3 | K3 as Rule 8's detector |
| Market state | Rule 9 | S9 | Precondition; bear equivalence |
| Reactions | "decline or reaction"; near-extreme 2-day moves; "3-day reaction" | Bound; ≠ K3; strictly-new-high anchor; top before reaction; outside-day continuation (OD-2, OPEN-2.x, RQ-6/7, OPEN-D/E) | Every mechanical element |
| Episodes, latches, D−1, HF/DB, 1m, basis, substrate start, spent candidates, no-bar rules, termination | — | ✔ | ✔ |
| Rule 10 outcome; horizon; pooling | Separate rule | ✔ | ✔ |

---

## 3. Mathematical definitions

### 3.1 Primitives

| Symbol | Definition | Provenance |
|---|---|---|
| 𝒟; d⁻; cal(d) | NSE sessions; previous session; calendar date | [LOD] |
| H_d^(D), L_d^(D) | EOD high/low of session d < D, as-of-D basis | [LOD] R-13, RQ-9 |
| h_τ^(D), l_τ^(D) | HF: genuine 1m bar τ on D, normalized to as-of-D | [LOD] RQ-9 = A+x |
| G(D) | HF: TRUE iff D has ≥ 1 genuine (`is_synthetic = FALSE`) 1m bar for the stock | [LOD] RQ-11, OPEN-C |
| LL, HH, HL | Strict day-over-day comparisons on EOD bars | [LOD] R-1 |
| ℓ_d; c; u | K3 line state; down-switch close; up-switch close | [GS] Δ2-10; [LOD] R-1 |
| X⁺ = (h, d_h, c); X⁻ = (l, d_l, u) | K3 swing high/low; first-occurrence dates | [LOD] R-1, OPEN-4.1/4.5 |
| S9_d | Per OPEN-3b = A | [LOD] |
| S_HF | First session of the HF substrate for the stock | [LOD] X-1 |

**Basis note.** Every historical value used on D is expressed as of D. CA exclusion windows are
imported from G-7.

### 3.2 Episode and membership — unchanged from v0.3 (SC-3 = A, RQ-1 = A)

- E = (σ, a, b) is a maximal [a, b) with S9 = σ ∈ {BULL, BEAR}; reset on reversal or cessation.
- K3 move membership: confirmation close ∈ [a, b).
- Reaction membership: completion close ∈ [a, b). A completion close cannot coincide with a switch
  close. — RESOLVED
- A move confirmed before a is never a member. — RESOLVED

### 3.3 Current move — unchanged from v0.3

- M = (X⁺, c, u) bull (S9_c = BULL, member of E), with P_S = h, d_S = d_h. Bear mirror.
- Active on D ∈ (c, u].
- S9 constant inside the active span.

### 3.4 Time leg (OPEN-A = A)

| Symbol | Definition | Status |
|---|---|---|
| el_M(D) | cal(D) − cal(d_S) | LOCKED |
| dur(M′) | Bull: cal(d_l′) − cal(d_h′) on the **K3 swing dates**; bear mirror | **LOCKED (OPEN-A = A)** |
| 𝒰_T(M) | Same-type K3 members of E completed ≤ d_S | LOCKED |
| R_T(M) | max dur over 𝒰_T; undefined if empty | LOCKED |
| TC_M(D) | M active on D ∧ 𝒰_T ≠ ∅ ∧ el_M(D) > R_T | LOCKED |

R_T is constant while M is active (u′ ≤ d_S). — RESOLVED

### 3.5 Magnitudes (RQ-8 = A, RQ-9 = A+x, OPEN-A = A, OPEN-C = A)

```
Current bull M, instant τ on session D:
  LowHist_M(D) = min{ L_d^(D) : d_S < d ≤ D⁻ }                               (+∞ if empty)
  HF:  if G(D):  LowObs_M(τ) = min{ l_τ′^(D) : genuine 1m bars τ′ ≤ τ on D }
                 run_M(τ)    = P_S^(D) − min(LowHist_M(D), LowObs_M(τ))
       if ¬G(D): no price evaluation on D                                     (OPEN-C = A)
  DB:  run_M(D) = P_S^(D) − min(LowHist_M(D), L_D^(D))                        (observable at D's close)
Reference K3 decline M′ (literal extreme; OPEN-A = A):
  mag^(D)(M′) = h′^(D) − min{ L_d^(D) : d_h′ < d ≤ u′ }
Reference bull reaction ρ:
  mag^(D)(ρ) = Top_ρ^(D) − L_{s_k}^(D)
Bear: mirrors with highs.
```

**Dual endpoint (OPEN-A = A, disclosed).** For the same reference move, the time leg uses the K3
swing-low date d_l′, while the price leg uses the literal minimum over (d_h′, u′]. That minimum can fall
on an earlier session than d_l′ (NC-10).

### 3.6 Reaction (bull only) — RQ-6 = A, RQ-7 = B, OPEN-D = A, OPEN-E = A

| Element | Definition | Status |
|---|---|---|
| Running leg high | RH(d) = max{ H_x : x in the current K3 UP line, x ≤ d } | LOCKED |
| Establishing session | Session e with H_e **strictly greater** than RH(e⁻). The up-switch close establishes the line's first RH. An equal high does not establish | **LOCKED (OPEN-D = A)** |
| Reaction ρ | s₁ = e⁺ (immediately after an establishing session e) with LL(s₁); s₂ = s₁⁺ with LL(s₂) optional; k ∈ {1, 2}; completed at the first following non-LL close; a 3rd consecutive LL → K3 switch | LOCKED (OPEN-2.1/2.3, RQ-7) |
| Top_ρ | H_e (highs of s₁ … s_k excluded) | LOCKED (RQ-6) |
| Outside-day session | If s₁ (or s₂) is LL and also has H > RH, the reaction **continues normally**: a following LL session is the next session of the same ρ with Top_ρ = H_e. The outside day does raise RH for **later** reactions, but it does not start a new reaction inside ρ | **LOCKED (OPEN-E = A)** |
| Establishing inside ρ | Sessions of ρ are never establishing sessions for a reaction that overlaps ρ | RESOLVED (follows from OPEN-E = A) |
| After ρ completes | The completing non-LL session (or any later session) establishes a new anchor only if its high is strictly > RH, where RH already includes any outside-day high inside ρ | RESOLVED (OPEN-D = A with RH definition) |
| Membership / precedence | Completion close ∈ [a, b) (RQ-1); ≤ d_S (RQ-5) | LOCKED |
| Bear HH structures | Not operative | NC-1 |

### 3.7 Price leg

| Symbol | Definition | Status |
|---|---|---|
| 𝒰_P(M) bull | Ledger K3 declines ∪ qualifying reactions of E, completed ≤ d_S | LOCKED |
| 𝒰_P(M) bear | Ledger K3 rallies of E, completed ≤ d_S | LOCKED |
| R_P^(D)(M) | One combined maximum of mag^(D) over 𝒰_P | LOCKED (RQ-2 = A) |
| PC_M(τ) | M active on d(τ) ∧ 𝒰_P ≠ ∅ ∧ run_M(τ) > R_P^(D) (HF only when G(d(τ))) | LOCKED (OD-8/9, OPEN-C) |
| Recorded price flag | First PC_M in E while μ(E) = FALSE; μ(E) := TRUE; recorded regardless of 𝒰_T | LOCKED (RQ-3 = C, RQ-4 = A) |
| Matched candidate | 𝒰_T ≠ ∅ ∧ 𝒰_P ≠ ∅ (⇔ 𝒰_T ≠ ∅, derived v0.3 §3.7) | LOCKED |
| Contrast price input | For matched candidates, a price score that **does not depend on μ(E)** | LOCKED by wording (OPEN-F; CONF-1). Exact per-candidate score: **OPEN-H** |

### 3.8 Events, latches and profile rules

| Rule | Definition | Status |
|---|---|---|
| D*_M | min{ D : TC_M(D) } | LOCKED |
| λ(E), μ(E) | FALSE when E opens | LOCKED |
| DB GF-10 event | ¬λ → event at D*_M; λ := TRUE | LOCKED |
| HF GF-10 event | ¬λ ∧ G(D*_M) ∧ D*_M ≥ S_HF ∧ M not time-spent → event at the first genuine 1m bar; λ := TRUE | LOCKED |
| HF no-bar time crossing | ¬λ ∧ ¬G(D*_M) ∧ D*_M ≥ S_HF ∧ M not time-spent → no event; λ := TRUE | LOCKED (RQ-11 = D) |
| HF price flag | ¬μ ∧ G(D) ∧ PC_M(τ) ∧ M not price-spent → flag at genuine bar τ; μ := TRUE | LOCKED (RQ-4, OPEN-C) |
| HF no-bar price | No evaluation; μ unchanged; D's EOD low enters LowHist from D⁺ | **LOCKED (OPEN-C = A)** |
| HF substrate start | At S_HF, for every open episode: λ := FALSE, μ := FALSE. K3, S9, ledger and candidates carried from EOD | **LOCKED (RQ-10 = B, OPEN-G = A)** |
| Spent candidate (per leg) | M active at S_HF is **time-spent** if ∃ D < S_HF with D active and el_M(D) > R_T. It is **price-spent** if ∃ D < S_HF with D active and the EOD run (DB rule) exceeds R_P^(D). A spent leg emits no HF event or flag from M and sets no latch. The other leg of M, and every other candidate, are unaffected | **LOCKED (OPEN-B = B)** |
| DB end / separation | DB events stop at the end of DB availability; never pooled with HF | RESOLVED; NC-6 |

---

## 4. State machine and timeline (per stock; bull shown, bear mirrors)

```text
State (read on D from 𝔉(D), re-based as-of-D):
  K3: ℓ, runs, swing points (first-occurrence), RH and last establishing session, open reaction ρ (if any)
  S9: σ; episode E; λ(E); μ(E)
  Ledger(E): K3 members (dur on swing dates; literal mag; terminating close); reactions (mag; completion close)
  Candidate M: (P_S, d_S, c), time-spent flag, price-spent flag
  Profile: DB | HF (from S_HF)
```

| Phase | What happens | Locks |
|---|---|---|
| **A. UP line** | Update RH. A session with H > RH (strict) is an establishing session e (the up-switch close establishes the first RH). If e⁺ is LL, ρ opens with Top = H_e; an outside-day LL session continues ρ normally (it raises RH for later reactions only). A 2nd LL session is ρ's 2nd session; a 3rd consecutive LL makes the run a K3 switch (ρ discarded). On the first non-LL close, ρ completes; if a BULL E is open it enters Ledger(E) | OPEN-2.x; RQ-6/7; OPEN-D/E; RQ-1 |
| **B. Down-switch close c** | X⁺ confirmed; S9 recomputed. On a change, E closes (ledger, λ, μ discarded) and a new E may open at c. If S9_c = BULL, M is a candidate member (SC-3 even when d_S < a). 𝒰_T and 𝒰_P fixed from members completed ≤ d_S; R_T on K3 swing dates; R_P = combined maximum of literal magnitudes | R-1; OPEN-3b; SC-3; RQ-1/2/5/8; OPEN-A |
| **C. Active session D ∈ (c, u]** | **Time:** ¬λ ∧ 𝒰_T ≠ ∅ ∧ el > R_T (∧ HF: D ≥ S_HF, not time-spent) → DB: event at D; HF with G(D): event at the first genuine bar; HF without G(D): no event. Each sets λ := TRUE. **Price:** HF with ¬G(D): skipped (μ unchanged). Otherwise if ¬μ ∧ 𝒰_P ≠ ∅ ∧ run > R_P (∧ HF: not price-spent) → flag (HF: the genuine bar; DB: D's close); μ := TRUE. Recorded whether or not M is matched. New lows extend run; no clock reset; no termination on a new high | OD-7/8/9; OPEN-4.x; RQ-3/4/8/9/11; OPEN-B/C |
| **D. Up-switch close u** | M active on u, ends after it. If E continues, M enters the ledger: dur = cal(d_l) − cal(d_h); mag = literal minimum over (d_h, u] | OPEN-4.3; RQ-8; OPEN-A |
| **E. Latches** | λ = TRUE stops GF-10 events in E. μ = TRUE stops **recorded** price flags in E. They are independent | OD-4/6; RQ-4; RQ-11 |
| **F. S9 reset** | E closes; ledger, λ and μ discarded; new E with an empty ledger and λ = μ = FALSE; SC-3 joins; RQ-1 exclusion | OD-5; SC-3; RQ-1 |
| **G. HF substrate start S_HF** | For every open episode: λ := FALSE, μ := FALSE. Each active candidate is checked per leg on EOD-era sessions: a time crossing before S_HF → time-spent; an EOD price crossing before S_HF → price-spent. Spent legs emit nothing and set no latch; unspent legs and later candidates proceed normally | RQ-10 = B; OPEN-G = A; OPEN-B = B; X-2 = A |
| **H. Formal contrast** | Over matched candidates: time input from the GF-10 events (λ-governed); price input **independent of μ**. The exact per-candidate price score and the time/price latch symmetry are OPEN-H | RQ-3 = C; OPEN-F; R-10; G-4 |

**Timelines (schematic):**

```text
Outside-day reaction (OPEN-E = A, OPEN-D = A):
  e: H_e new RH → s₁: LL and H_{s₁} > H_e (outside) → s₂: LL → s₃: non-LL
  ρ = {s₁, s₂}, Top = H_e, mag = H_e − L_{s₂}; RH after ρ = H_{s₁}
  s₃ establishes only if H_{s₃} > H_{s₁}

Equal high (OPEN-D = A):
  e: H_e = RH (not strictly above) → e⁺ LL: not a reaction

HF start with a spent candidate (OPEN-B = B, OPEN-G = A, RQ-10 = B):
  E open; M active; el_M > R_T already on an EOD-era date → M time-spent
  at S_HF: λ = μ = FALSE; M emits no HF event; M's price leg is checked separately
  next candidate M₂ in E can emit an HF event normally

HF no-bar session (RQ-11 = D, OPEN-C = A):
  D with ¬G(D): time crossing → no event, λ := TRUE; price: not evaluated, μ unchanged
  D⁺ with G: LowHist now includes L_D (EOD) → a price flag may occur at D⁺'s first genuine bar (NC-11)
```

---

## 5. Confirmation and OPEN items

### 5.1 CONF-1 — OPEN-F letter confirmation

| Field | Entry |
|---|---|
| Issue | The operator's label "A" does not match v0.3 option (a). The wording "independent of price latch" matches v0.3 (c) (or (b)) |
| Recorded as | The wording |
| Needed | A one-line operator confirmation: wording intended (no change), or v0.3 (a) intended (amend §1.2-24, §3.7, §4 H, §9) |
| Nature | Recording ambiguity, not a mechanical choice |

### 5.2 OPEN-H — Per-candidate scores and latch symmetry inside the matched contrast

| Field | Entry |
|---|---|
| Ambiguity | Under OPEN-F the contrast's price input ignores μ, but the time input is the GF-10 event, which is governed by λ (OD-4, first per episode). Two things are undefined: (i) the price score of a matched candidate (e.g. 1 iff PC_M holds at any observable instant in its active span, or first crossing only); (ii) how matched candidates after a time latch are treated. Their time score is structurally 0 (they cannot emit), while their price score can be 1 |
| Why it matters | Changes T(price) relative to T(time) inside the R-10 specificity leg. Latched time scores against unlatched price scores differ by construction, not by content |
| Choices | (a) Keep as is: time λ-governed, price per candidate (disclose the asymmetry). (b) Time input for the contrast also evaluated per matched candidate, ignoring λ (a contrast-only time score; the GF-10 event population is unchanged). (c) Restrict the contrast to matched candidates in episodes **before** λ is set (and the candidate that sets it). (d) Other |
| Source | "The Time change is more important than reversal in price" [GS] p. 12 fixes the ranking only |
| Classification | Operator-defined (research design); created by OPEN-F with OD-4, not a reopening |
| Dependencies | CONF-1 (if v0.3 (a) was meant, OPEN-H becomes moot as posed). Coupled to imported G-4 and draft OPEN-11 (weekly score mapping) |

### 5.3 Imported, open elsewhere (not re-analysed)

- **Gaps:** G-4 (contrast p), G-5, G-6, G-7 (also needed for RQ-9 = x re-basing), G-8, G-9.
- **Preconditions:** P-1 … P-5, including the R-13 external CA list (P-2).
- **Draft items:** OPEN-6 (timestamp label), OPEN-11 (weekly score mapping), OPEN-12 (outcome window).

---

## 6. Checks

| # | Item | v0.4 verdict |
|---|---|---|
| 6.1 | "Completed" reference | RESOLVED |
| 6.2 | Eligibility timing | RESOLVED |
| 6.3 | Current/reference alignment | RESOLVED |
| 6.4 | Price basis | RESOLVED (RQ-9 = A+x; OPEN-C = A for no-bar sessions) |
| 6.5 | Equal highs/lows | RESOLVED (K3 swing points; OPEN-D = A for anchors) |
| 6.6 | Bull/bear separation | RESOLVED |
| 6.7 | K3 moves vs reactions | RESOLVED (OPEN-D = A, OPEN-E = A) |
| 6.8 | Reaction as greatest reference | RESOLVED (RQ-2 = A) |
| 6.9 | Time comparison | RESOLVED (OPEN-A = A; OPEN-B = B) |
| 6.10 | Matched contrast | Price input independent of μ (OPEN-F by wording); **CONF-1, OPEN-H** |

### 6.11 Disclosure notes (no decision)

| ID | Note |
|---|---|
| NC-1 | Bear HH reaction structures do not become K3; not operative |
| NC-2 | The K3 switch asymmetry makes bull and bear moves structurally different |
| NC-3 | Events concentrate on the first active session when R_T is below the confirmation lag |
| NC-4 | "Reaction ≠ K3" is an operator decision; Gann uses "3-day reaction" (Δ3-04) |
| NC-5 | An HF observation-session 1m extreme is replaced by the EOD extreme from the next session |
| NC-6 | One calendar episode can yield DB and HF events; never pooled |
| NC-7 | RQ-10 = B vs RQ-11 = D differ by circumstance; consistent |
| NC-8 | The first candidate of every episode has 𝒰_T = ∅ (derived) |
| NC-9 | A qualifying reaction can set R_P above every ledger K3 decline (derived) |
| NC-10 | OPEN-A = A: one reference move carries a K3 swing-low **date** for time and a possibly earlier literal-minimum **price** for magnitude |
| NC-11 | OPEN-C = A with RQ-9: a price crossing that occurred on a no-bar HF session can surface as a flag on the next session with genuine bars (via its EOD low in history) if the move is still active and μ is FALSE. This is the first HF-observable instant (OD-7), not a same-session flag |
| NC-12 | OPEN-B = B makes a candidate's spent status per leg: a candidate can be time-spent but price-live, or the reverse |

---

## 7. Contradiction audit (re-run for v0.4)

### 7.1 Result

**v0.4: PASS.**
- No contradiction among the **50 locked decisions** in §9: the v0.3 set of 43, plus OPEN-A … OPEN-G.
- No contradiction between §1.2, §2, §3, §4 and §9.
- **Remaining:** **CONF-1** (a recording ambiguity on OPEN-F's letter) and **OPEN-H** (a gap created by
  OPEN-F with OD-4).
- The v0.3 hazard (OPEN-B choice (a) vs X-2 / OD-7) is **removed**: OPEN-B = B is consistent with both.

### 7.2 Checks

| ID | Check | Result |
|---|---|---|
| B-1 | OPEN-A = A vs RQ-8 = A (literal price for references) | Consistent: RQ-8 governs price only; time keeps the K3 dates (NC-10) |
| B-2 | OPEN-A = A vs OPEN-4.4 = A (current time endpoint = observation date) | Consistent: different objects (current vs reference) |
| B-3 | OPEN-B = B vs RQ-10 = B | Consistent: the latch stays FALSE; only the spent candidate's leg is suppressed |
| B-4 | OPEN-B = B vs X-2 = A and OD-7 | Consistent: no DB-era crossing becomes an HF event |
| B-5 | OPEN-B = B vs C-7 (move reset) | Consistent: later candidates in the episode are unaffected |
| B-6 | OPEN-C = A vs RQ-11 = D | Consistent: time leg latches on no-bar sessions; price leg is not evaluated (legs independent, RQ-4) |
| B-7 | OPEN-C = A vs RQ-9 = A+x and OD-7 | Consistent: the session's EOD low enters as history; the earliest HF observation is the next genuine bar (NC-11) |
| B-8 | OPEN-D = A vs OPEN-4.5 = A (first occurrence) | Consistent in principle (an equal later high does not take over the role) |
| B-9 | OPEN-D = A vs RQ-7 = B | Consistent: it defines "established" |
| B-10 | OPEN-E = A vs RQ-6 = A | Consistent: Top stays H_e; outside-day highs are excluded from Top but raise RH |
| B-11 | OPEN-E = A vs OPEN-2.1 = A / OPEN-2.3 = B | Consistent: the bound of 2 sessions and the 3rd-LL → K3 rule are unchanged |
| B-12 | OPEN-E = A vs OPEN-D = A | Consistent: an outside-day session inside ρ raises RH for later anchors only |
| B-13 | OPEN-F (wording) vs RQ-3 = C / RQ-4 = A | Consistent: flags are still recorded with μ; only the contrast input ignores μ |
| B-14 | OPEN-F (wording) vs OD-4 (time λ) | No contradiction; **gap OPEN-H** (latch asymmetry inside the contrast) |
| B-15 | OPEN-F letter "A" vs v0.3 option (a) text | **Mismatch → CONF-1** |
| B-16 | OPEN-G = A vs OPEN-B = B | Consistent: μ FALSE at start; the price-spent candidate is suppressed individually |
| B-17 | OPEN-G = A vs RQ-4 = A | Consistent |
| B-18 | §2 attribution | No [LOD] attributed to Gann — PASS |
| B-19 | §9 ↔ sections | Every ledger row mapped; CONF-1 and OPEN-H in §5 — PASS |

---

## 8. Future work — what empirical testing must NOT decide

**Definitional (before any data read; never from results):**
- CONF-1; OPEN-H.
- Every lock in §9.
- Any later threshold, window, adjacency or source rule.

No choice may be justified by event counts, coverage, "too few/many events", IC, Sharpe, surrogate p,
contrast p, size-check outcome or any O-R10 association.

**Empirical (pre-registered read, after freeze only):**
- GF-10 events vs O-R10 beyond the surrogate null (R-14).
- T(time) vs T(price) on matched candidates (R-10, RQ-3 = C, G-4).
- Descriptive statistics: reported, never used to revise definitions.

**Implementation (code review and deterministic tests, not results):**
- K3/S9 (memo §5); establishing-session strictness; outside-day continuation.
- D−1 freeze; causal prefix invariance; byte-identical replay.
- As-of-D re-basing and 1m normalization (ratio test).
- G(D) via `is_synthetic = FALSE`, `bar_labeling.py`, GAP sessions and `SPECIAL_SESSIONS`.
- Independent λ/μ; per-leg spent flags at S_HF.
- First-occurrence ties; timestamp label (imported OPEN-6).

---

## 9. Decision ledger

| ID | Decision | Status | Applied in |
|---|---|---|---|
| OD-1 | Time leg: greatest qualifying previous decline/rally | LOCKED | §1.2-14; §3.4 |
| OD-2 | "Decline or reaction"; 1/2/3-day framework; reaction ≠ K3 | LOCKED | §1.2-15; §3.6 |
| OD-3 | Bear = S9 bear | LOCKED | §1.2-5 |
| OD-4 | First exceedance per S9 episode | LOCKED | §1.2-21; §3.8 |
| OD-5 | Reset on S9 reversal or cessation | LOCKED | §1.2-11; §4 F |
| OD-6 | Symmetric bull/bear | LOCKED | §1.2-21 |
| OD-7 | First objectively observable crossing | LOCKED | §1.2-19; §3.8 |
| OD-8 | Running extreme | LOCKED | §1.2-16; §3.5 |
| OD-9 | Strict `>` | LOCKED | §1.2-18 |
| OD-10 | Finest available resolution | LOCKED (via HF/DB) | §1.2-1 |
| C-1/C-2/C-3 | HF 1m / DB daily; never pooled; D−1 freeze | LOCKED | §1.2-1, 6 |
| C-4 | K3 eligibility; K3 current move; reactions only bull price comparator | LOCKED | §1.2-7, 15, 17 |
| C-5 | OD-1 supersedes "immediately preceding" | LOCKED | §3.4 |
| C-6 | OD-7 supersedes week-end timing | LOCKED | §1.2-19 |
| C-7 | Move-level reset + episode-level first-event latch | LOCKED | §1.2-21/25; §4 |
| X-1 = A | HF 1m detection; EOD K3/S9 context, pre-substrate allowed | LOCKED | §1.2-1 |
| X-2 = A | Never pool; HF may use EOD lookback | LOCKED | §1.2-1; §3.8 |
| OPEN-3b = A | S9 on confirmed K3 points; switch-close changes; D−1 | LOCKED | §1.2-4 |
| OPEN-4.1 = A | Start at K3 swing high / low | LOCKED | §3.3 |
| OPEN-4.2 = A | Clock from the starting-extreme date | LOCKED | §3.4 |
| OPEN-4.3 = A | Terminate at confirmed K3 reversal | LOCKED | §3.3 |
| OPEN-4.4 = A | Time endpoint = observation date | LOCKED | §3.4 |
| OPEN-4.5 = A | First occurrence of an equal starting extreme | LOCKED | §3.1 |
| SC-3 = A | Move confirmed at the creating switch included | LOCKED | §3.2 |
| OPEN-2.1 = A | 1/2-day LL/HH structures; 3rd → K3 | LOCKED | §3.6 |
| OPEN-2.2 = A | Reaction from the running leg extreme | LOCKED | §3.6 |
| OPEN-2.3 = B | Bounded structure | LOCKED | §3.6 |
| OPEN-2.4 = A | Reactions excluded from time; bull price only | LOCKED | §1.2-14/17 |
| OPEN-2.5 = B | Near-extreme structural | LOCKED | §3.6 |
| OPEN-1 = A | Current-episode universe; greatest; no carryover; first move cannot trigger | LOCKED | §1.2-13 |
| RQ-1 = A | Membership by confirmation close; no carry from the previous episode | LOCKED | §3.2 |
| RQ-2 = A | Bull price reference = one combined maximum (K3 declines + reactions) | LOCKED | §3.7 |
| RQ-3 = C | Price flags independent; formal contrast on matched candidates | LOCKED | §3.7; §4 H |
| RQ-4 = A | Independent first-per-episode price latch | LOCKED | §3.8 |
| RQ-5 = A | References completed ≤ d_S | LOCKED | §3.4; §3.7 |
| RQ-6 = A | Reaction top excludes reaction-session highs | LOCKED | §3.6 |
| RQ-7 = B | Reaction begins immediately after the establishing session | LOCKED | §3.6 |
| RQ-8 = A | Literal running-price window, current and reference | LOCKED | §3.5 |
| RQ-9 = A+x | EOD history; genuine 1m on D; as-of-D normalization | LOCKED | §3.1; §3.5 |
| RQ-10 = B | HF time latch FALSE at substrate start | LOCKED | §3.8; §4 G |
| RQ-11 = D | HF no-bar time crossing: no event, latch set | LOCKED | §3.8; §4 C |
| **OPEN-A = A** | K3 swing dates for time; literal extreme for price | **LOCKED** | §1.2-14/16; §3.4; §3.5 |
| **OPEN-B = B** | Pre-HF-crossed candidate spent (per leg); no HF event/flag; no latch | **LOCKED** | §1.2-23; §3.8; §4 G |
| **OPEN-C = A** | No HF price evaluation without a genuine 1m bar | **LOCKED** | §1.2-16/22; §3.5; §3.8 |
| **OPEN-D = A** | Only a strictly new extreme establishes the anchor | **LOCKED** | §1.2-15; §3.6 |
| **OPEN-E = A** | Outside-day reaction continues normally | **LOCKED** | §1.2-15; §3.6 |
| **OPEN-F** | Matched contrast independent of price latch | **LOCKED by wording — CONF-1** | §1.2-24; §3.7; §4 H |
| **OPEN-G = A** | HF price latch starts FALSE | **LOCKED** | §1.2-22/23; §3.8 |
| CONF-1 | OPEN-F label vs wording | **CONFIRMATION REQUESTED** | §5.1 |
| OPEN-H | Per-candidate contrast scores; time/price latch symmetry | **OPEN (surfaced v0.4)** | §5.2 |

## 10. Remaining decision order

| Step | Item | Depends on |
|---|---|---|
| 1 | CONF-1 | — |
| 2 | OPEN-H | CONF-1 |

After these, the GF-10 event, price-flag and matched-contrast populations are defined at the
mechanical level. Remaining work is the imported items (OPEN-6, OPEN-11, OPEN-12, G-4 … G-9,
P-1 … P-5), then the freeze document.

---

**NO CODE. NO BACKTEST. NO EMPIRICAL TESTING. NO MARKET OUTCOMES READ. NO LOCKED DECISION REOPENED.
NOT FROZEN. NOT AN IMPLEMENTATION SPECIFICATION.**
