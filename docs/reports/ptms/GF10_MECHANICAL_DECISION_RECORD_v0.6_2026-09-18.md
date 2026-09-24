# GF-10 Mechanical Decision Record — v0.6

**Date:** 2026-09-18

**Status: CONSOLIDATED DECISION RECORD — NOT AN IMPLEMENTATION SPECIFICATION, NOT AN EMPIRICAL FREEZE.**
- No code, backtest, empirical test, optimization or performance analysis was performed.
- No market data or outcome was read. No event count was computed. Nothing is frozen or hashed.
- **No locked decision is reopened.**

**Supersedes:** v0.5 (`GF10_MECHANICAL_DECISION_RECORD_v0.5_2026-09-18.md`), which is kept unchanged.
Earlier versions: v0.4 (`…_v0.4_2026-09-17.md`), v0.3 (`d9a9119`), v0.2 (superseded; provenance
error) and v0.1 (`59e25da`).

**New in this version:** operator rulings on OPEN-I, made after v0.5:

| Item | Operator ruling | Scope |
|---|---|---|
| OPEN-I(a) | **LOCKED = A-ii.** HF time scoring in the formal contrast requires genuine 1m observability. TC_M(D) may become true at the date level on a session with no genuine 1m bar. That date-level crossing is **not** an HF-observable crossing. If the candidate remains active, the time score is recognized at the **next genuine 1m observation within the active span**, consistent with the crossing instant being the first objectively observable HF instant (OD-7) | P3/P4 only. **P1 and RQ-11 = D unchanged** |
| OPEN-I(b) | **LOCKED = B-ii.** A candidate whose active span crosses the HF substrate boundary S_HF is **excluded from both P3 and P4**. It is not reassigned, split, or scored across DB and HF profiles. This is a **contrast-population eligibility rule**; it does not declare the underlying GF-10 candidate invalid | P3/P4 only. **P1/P2 unchanged** |

**Principle made explicit (from OPEN-I(b) = B-ii):** *a formal-contrast candidate must have a
homogeneous observation substrate across its active span.* A candidate whose active span is entirely
DB is eligible for the DB contrast; one entirely HF is eligible for the HF contrast; one crossing S_HF
is excluded from P3/P4. **This never excludes a candidate from P1/P2.**

**OPEN-I is fully RESOLVED.** The v0.6 audit (§7) surfaced one further definitional item, **OPEN-J**
(right-censoring of P3/P4 candidates at the end of the evaluation sample). It is pre-existing since
v0.5, not created by the OPEN-I rulings, and is recorded in §5.3 without being resolved.

**Construct label:** GF-10 = **GANN-FAITHFUL SOURCE CONCEPT + EXPLICIT OPERATOR/RESEARCH CONVENTIONS.**
It is not "Gann's exact rule".

**Provenance markers:**

| Marker | Meaning |
|---|---|
| **[GS]** | GANN SOURCE: verified wording or arithmetic; register ID given |
| **[LOD]** | LOCKED OPERATOR / RESEARCH DECISION |
| **[NES]** | NOT ESTABLISHED BY SOURCE; never to be attributed to Gann |

A [GS] marker on part of a rule does not extend to the rest of it. **OPEN-F, CONF-1, OPEN-H, OPEN-I,
OPEN-J, every latch, substrate homogeneity, and all contrast scoring are operator/research
conventions: [LOD] and [NES], never [GS].**

**Document layout:**

| Part | Sections |
|---|---|
| LOCKED | §1 – §4, §9 |
| Resolved record, OPEN (newly surfaced) and imported | §5 |
| Future implementation / empirical work | §8 |

---

## 0. Change log from v0.5

| # | Change | Sections |
|---|---|---|
| CL-1 | **OPEN-I(a) = A-ii LOCKED:** in the HF contrast, the time score counts only at a genuine 1m bar; a date-level crossing on a no-bar session is recognized at the next genuine 1m bar in the active span, if any. P1/RQ-11 unchanged | §1.1; §1.2-24; §3.7; §4 C/H; §9 |
| CL-2 | **OPEN-I(b) = B-ii LOCKED:** a candidate whose active span crosses S_HF is excluded from P3 and P4; not reassigned, split or cross-scored. P1/P2 unchanged | §1.2-23/24; §3.7; §3.8; §4 B/G/H; §9 |
| CL-3 | **Substrate homogeneity** stated as the P3/P4 eligibility principle; new primitives prof(D) and the contrast-eligibility predicate CE(M) | §3.1; §3.7 |
| CL-4 | P3/P4 formulation rewritten per profile (DB, HF). With A-ii, the HF time and price legs share the same observability rule; the v0.5 observability asymmetry is removed | §3.7 |
| CL-5 | Derived: OPEN-B spent flags can never reach P3/P4 (every spent candidate straddles S_HF and is excluded) | §3.7; §3.8; NC-16 |
| CL-6 | OPEN-I moved from OPEN to RESOLVED/LOCKED; all OPEN-I references updated to the locked rulings or kept as historical/audit text | throughout |
| CL-7 | Audit re-run over **53 locks** (51 + OPEN-I(a) + OPEN-I(b)). **One newly surfaced definitional item, OPEN-J** (sample-end censoring of P3/P4 candidates), pre-existing since v0.5 | §5.3; §7 |
| CL-8 | New disclosure notes NC-15 … NC-17 | §6.11 |

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
                                      └─► candidate-level conditions TC_M(D) (time) and PC_M(τ) (price)
                                            │   first objectively observable strict crossing (OD-7, OD-9)
                                            │   HF: EOD history + normalized genuine 1m on D; no genuine bar → no price evaluation (RQ-9, OPEN-C = A)
                                            │   DB: EOD
                                            ├─► P1 OPERATIONAL: time crossing ⇒ GF-10 EVENT; time latch λ (OD-4, C-7)
                                            │     HF no-bar session ⇒ no event, λ set (RQ-11 = D)
                                            ├─► P2 OPERATIONAL: price crossing ⇒ price flag, recorded independently; price latch μ (RQ-3 = C, RQ-4 = A)
                                            │     HF substrate start: λ = μ = FALSE (RQ-10 = B, OPEN-G = A);
                                            │     pre-substrate-crossed candidates spent per leg (OPEN-B = B)
                                            └─► P3/P4 FORMAL CONTRAST on matched, substrate-homogeneous candidates (RQ-3 = C, R-10):
                                                  eligibility: active span entirely DB or entirely HF; crossing S_HF ⇒ excluded (OPEN-I(b) = B-ii)
                                                  P3 time score  = TC_M holds for M; independent of λ (OPEN-H = B);
                                                                   HF: recognized only at a genuine 1m bar (OPEN-I(a) = A-ii)
                                                  P4 price score = PC_M holds for M; independent of μ (OPEN-F wording; CONF-1 resolved);
                                                                   HF: genuine 1m bar only (OPEN-C = A, built into PC_M)
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
| 14 | Time reference | R_T = greatest dur over ledger K3 moves; dur on **K3 swing dates** | [GS] "decline"; [GS] p. 63 (inference); [LOD] OPEN-2.4 = A, OPEN-A = A |
| 15 | Reaction (bull only) | 1–2 consecutive strict LL sessions in a K3 UP line, starting on the session immediately after a session that set a **strictly new** running leg high. Top = that high (reaction-session highs excluded). A reaction session that is an outside day **continues normally** (a following LL is its 2nd session, same top). A 3rd LL → K3 switch | [GS] Δ2-02, Δ2-10, Δ3-01; [LOD] OD-2, OPEN-2.1/2.2/2.3/2.5, RQ-6 = A, RQ-7 = B, OPEN-D = A, OPEN-E = A; [NES] |
| 16 | Magnitudes | Current: P_S to the literal extreme after the start session through the observation instant. Reference K3 move: literal extreme over its window through its terminating close (**not** K3 swing values). Reaction: top − last-session low. HF: EOD history + normalized genuine 1m on D (**no 1m term without a genuine bar**). DB: EOD | [GS] p. 63 (inference); [LOD] OD-8, RQ-8 = A, RQ-9 = A+x, OPEN-A = A, OPEN-C = A; [NES] |
| 17 | Price reference | Bull: one combined maximum over ledger K3 declines and reactions. Bear: maximum over ledger K3 rallies | [GS] Δ2-02; [LOD] C-4, OPEN-2.4, RQ-2 = A; "greatest" for price [NES] |
| 18 | Triggers | Strict `>` | [GS]; [LOD] OD-9 |
| 19 | Event timing | First objectively observable crossing | [GS] (inference); [LOD] OD-7, C-6 |
| 20 | GF-10 event (P1) | Time crossing. HF: first genuine 1m bar of the crossing session; no genuine bar → no event, λ set. DB: the crossing session | [GS] p. 12; [LOD] R-5, R-10, RQ-11 = D; [NES] |
| 21 | Time latch λ | One GF-10 event per stock per episode; reset only at a new episode; HF: FALSE at substrate start. **Governs P1 only** | [GS] "first time" (bear only); [LOD] OD-4/6, C-7, RQ-10 = B, RQ-11 = D, OPEN-H = B; [NES] |
| 22 | Price flag (P2) and latch μ | Recorded independently of time eligibility; independent first-per-episode latch; HF: FALSE at substrate start; not evaluated on no-bar HF sessions. **μ governs P2 only** | [LOD] RQ-3 = C, RQ-4 = A, OPEN-C = A, OPEN-G = A, OPEN-F; [NES] |
| 23 | HF substrate start | λ = μ = FALSE. A candidate whose leg crossing held on a pre-substrate session is **spent for that leg** (no HF event or flag from it; no latch set). Applies to P1/P2. **For P3/P4, every candidate whose active span crosses S_HF is ineligible** (OPEN-I(b) = B-ii), so spent status never reaches P3/P4 | [LOD] RQ-10 = B, OPEN-B = B, OPEN-G = A, X-2 = A, **OPEN-I(b) = B-ii**; [NES] |
| 24 | Formal contrast (P3, P4) | T(time) − T(price) over **contrast-eligible** candidates: matched (𝒰_T ≠ ∅ ∧ 𝒰_P ≠ ∅) **and** substrate-homogeneous over the active span (all DB or all HF). Formed per profile, never pooled. **P3:** whether TC_M holds in the active span, **independent of λ**; in HF, recognized only at a genuine 1m bar (a no-bar date-level crossing is recognized at the next genuine bar in the span, if any). **P4:** whether PC_M holds in the active span, **independent of μ**; in HF, genuine bars only (OPEN-C). Both are candidate-level underlying conditions, not latch or reporting state. P1 is GF-10's primary score; P3/P4 exist only as R-10's specificity contrast. Statistic T(·): imported G-4 / OPEN-11 | [GS] p. 12 ranking only; [LOD] RQ-3 = C, R-10, OPEN-F (wording; CONF-1 resolved), OPEN-H = B, **OPEN-I(a) = A-ii, OPEN-I(b) = B-ii**; [NES]. Sample-end censoring: **OPEN-J** |
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
| "The first time" | ✔ bear time and price clauses only | λ and μ per episode, both directions; λ/μ govern the operational populations P1/P2 only (OD-4, RQ-4, OPEN-H = B, OPEN-F) | Bull use; scope; any latch in the contrast |
| Time more important than price | ✔ p. 12 (**the ranking only**) | Roles; matched contrast; four populations; candidate-level P3 independent of λ and P4 independent of μ; HF observability in P3; substrate-homogeneous contrast eligibility (R-10, RQ-3, OPEN-F, CONF-1, OPEN-H = B, OPEN-I(a) = A-ii, OPEN-I(b) = B-ii) | Any statistic; the matched set; candidate-level scoring; latch treatment; observability rule; eligibility |
| Calendar days | ✔ p. 61; Δ3-06 | Applied to Rule 8 | Rule 8's own unit |
| High/low measurement | ✔ p. 11, p. 63 (inference) | Running form, literal windows, ties | Form; windows; ties |
| 3-Day Chart | ✔ (discretionary) | Strict K3 | K3 as Rule 8's detector |
| Market state | Rule 9 | S9 | Precondition; bear equivalence |
| Reactions | "decline or reaction"; near-extreme 2-day moves; "3-day reaction" | Bound; ≠ K3; strictly-new-high anchor; top before reaction; outside-day continuation (OD-2, OPEN-2.x, RQ-6/7, OPEN-D/E) | Every mechanical element |
| Episodes, latches, D−1, HF/DB, 1m, basis, substrate start, substrate homogeneity, spent candidates, no-bar rules, termination | — | ✔ | ✔ |
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
| A(M) | Active span of M: sessions D ∈ (c, u] | [LOD] OPEN-4.3 |
| prof(D) | Observation profile of session D for the stock: **DB** if D < S_HF (or the stock has no HF substrate), **HF** if D ≥ S_HF. This is the state line "Profile: DB \| HF (from S_HF)" of §4; the observation boundary is S_HF | [LOD] X-1, X-2; [NES] |
| 𝒯_M | HF: the genuine 1m bars τ with d(τ) ∈ A(M) | [LOD] OPEN-I(a) = A-ii |

**Basis note.** Every historical value used on D is expressed as of D. CA exclusion windows are
imported from G-7.

### 3.2 Episode and membership — unchanged (SC-3 = A, RQ-1 = A)

- E = (σ, a, b) is a maximal [a, b) with S9 = σ ∈ {BULL, BEAR}; reset on reversal or cessation.
- K3 move membership: confirmation close ∈ [a, b).
- Reaction membership: completion close ∈ [a, b). A completion close cannot coincide with a switch
  close. — RESOLVED
- A move confirmed before a is never a member. — RESOLVED

### 3.3 Current move — unchanged

- M = (X⁺, c, u) bull (S9_c = BULL, member of E), with P_S = h, d_S = d_h. Bear mirror.
- Active on D ∈ A(M) = (c, u].
- S9 constant inside the active span.

### 3.4 Time leg (OPEN-A = A) — unchanged

| Symbol | Definition | Status |
|---|---|---|
| el_M(D) | cal(D) − cal(d_S) | LOCKED |
| dur(M′) | Bull: cal(d_l′) − cal(d_h′) on the **K3 swing dates**; bear mirror | LOCKED (OPEN-A = A) |
| 𝒰_T(M) | Same-type K3 members of E completed ≤ d_S | LOCKED |
| R_T(M) | max dur over 𝒰_T; undefined if empty | LOCKED |
| TC_M(D) | M active on D ∧ 𝒰_T ≠ ∅ ∧ el_M(D) > R_T | LOCKED |

R_T is constant while M is active (u′ ≤ d_S). — RESOLVED

TC_M(D) is a **date-level** condition. It contains no λ term and no G(D) term. Because el_M rises
strictly with D and R_T is constant, TC_M(D) ⇒ TC_M(D′) for every later active D′ (derived). Its
HF **observability** for the contrast is set by OPEN-I(a) = A-ii (§3.7), not by TC_M itself.

### 3.5 Magnitudes (RQ-8 = A, RQ-9 = A+x, OPEN-A = A, OPEN-C = A) — unchanged

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
swing-low date d_l′. The price leg uses the literal minimum over (d_h′, u′], which can fall on an
earlier session than d_l′ (NC-10).

### 3.6 Reaction (bull only) — RQ-6 = A, RQ-7 = B, OPEN-D = A, OPEN-E = A — unchanged

| Element | Definition | Status |
|---|---|---|
| Running leg high | RH(d) = max{ H_x : x in the current K3 UP line, x ≤ d } | LOCKED |
| Establishing session | Session e with H_e **strictly greater** than RH(e⁻). The up-switch close establishes the line's first RH. An equal high does not establish | LOCKED (OPEN-D = A) |
| Reaction ρ | s₁ = e⁺ (immediately after an establishing session e) with LL(s₁); s₂ = s₁⁺ with LL(s₂) optional; k ∈ {1, 2}; completed at the first following non-LL close; a 3rd consecutive LL → K3 switch | LOCKED (OPEN-2.1/2.3, RQ-7) |
| Top_ρ | H_e (highs of s₁ … s_k excluded) | LOCKED (RQ-6) |
| Outside-day session | If s₁ (or s₂) is LL and also has H > RH, the reaction **continues normally**: a following LL session is the next session of the same ρ with Top_ρ = H_e. The outside day raises RH for **later** reactions only; it does not start a new reaction inside ρ | LOCKED (OPEN-E = A) |
| Establishing inside ρ | Sessions of ρ are never establishing sessions for a reaction that overlaps ρ | RESOLVED (follows from OPEN-E = A) |
| After ρ completes | The completing non-LL session (or any later session) establishes a new anchor only if its high is strictly > RH, where RH already includes any outside-day high inside ρ | RESOLVED (OPEN-D = A with RH definition) |
| Membership / precedence | Completion close ∈ [a, b) (RQ-1); ≤ d_S (RQ-5) | LOCKED |
| Bear HH structures | Not operative | NC-1 |

### 3.7 Price leg and the formal contrast

| Symbol | Definition | Status |
|---|---|---|
| 𝒰_P(M) bull | Ledger K3 declines ∪ qualifying reactions of E, completed ≤ d_S | LOCKED |
| 𝒰_P(M) bear | Ledger K3 rallies of E, completed ≤ d_S | LOCKED |
| R_P^(D)(M) | One combined maximum of mag^(D) over 𝒰_P | LOCKED (RQ-2 = A) |
| PC_M(τ) | M active on d(τ) ∧ 𝒰_P ≠ ∅ ∧ run_M(τ) > R_P^(D) (HF only when G(d(τ))) | LOCKED (OD-8/9, OPEN-C) |
| Matched candidate | 𝒰_T ≠ ∅ ∧ 𝒰_P ≠ ∅ (⇔ 𝒰_T ≠ ∅, derived v0.3 §3.7) | LOCKED |
| Substrate-homogeneous | prof(D) is constant over D ∈ A(M): **DB-homogeneous** iff u < S_HF (or no HF substrate); **HF-homogeneous** iff min A(M) ≥ S_HF (i.e. c⁺ ≥ S_HF); **crossing** iff min A(M) < S_HF ≤ u | **LOCKED (OPEN-I(b) = B-ii)** |
| CE(M) — contrast-eligible | Matched ∧ substrate-homogeneous. CE(M) assigns M to exactly one contrast, prof(A(M)) ∈ {DB, HF}. A crossing candidate has CE = FALSE and is not reassigned, split or cross-scored | **LOCKED (OPEN-I(b) = B-ii)** |

**Substrate homogeneity principle (OPEN-I(b) = B-ii).** A formal-contrast candidate must have a
homogeneous observation substrate across its active span. Homogeneity is judged on the **active span
A(M) = (c, u]** only. References (R_T, R_P, ledger) built from EOD history before S_HF are permitted
for an HF-homogeneous candidate, because HF may use EOD lookback (X-1 = A, X-2 = A). CE(M) is an
eligibility rule for P3/P4. **It does not invalidate M and has no effect on P1 or P2.**

**The four populations (OPEN-H = B, OPEN-F wording, OPEN-I(a) = A-ii, OPEN-I(b) = B-ii).** These
populations are distinct. None of them is derived from another's latch state.

| Pop. | Name | Membership / value | Latch | Role | Status |
|---|---|---|---|---|---|
| **P1** | Operational GF-10 event population | Per episode E, at most one event: the first observable time crossing by any candidate while λ(E) = FALSE, under the HF/DB, no-bar (RQ-11 = D) and spent-leg (OPEN-B = B) rules of §3.8. **Includes candidates crossing S_HF**, as those rules already provide | λ(E), first-per-episode | GF-10's **primary score** (R-5, R-10) | LOCKED (OD-4, OD-7, C-7, RQ-10, RQ-11, OPEN-B) — unchanged by OPEN-I |
| **P2** | Operational (independent) price-flag population | Per episode E, at most one flag: the first observable price crossing by any candidate while μ(E) = FALSE, **whether or not the candidate is matched or contrast-eligible**, under OPEN-C, OPEN-B and OPEN-G | μ(E), first-per-episode, independent of λ | Recorded fact; not a score | LOCKED (RQ-3 = C, RQ-4 = A, OPEN-C, OPEN-G) — unchanged by OPEN-I |
| **P3** | Contrast time score (candidate-level) | For each candidate with **CE(M)**: s_T(M) ∈ {0, 1}, per profile | **None.** Independent of λ | Specificity contrast only (R-10) | LOCKED (OPEN-H = B, OPEN-I(a) = A-ii, OPEN-I(b) = B-ii) |
| **P4** | Contrast price score (candidate-level) | For each candidate with **CE(M)**: s_P(M) ∈ {0, 1}, per profile | **None.** Independent of μ | Specificity contrast only (R-10) | LOCKED (OPEN-F wording; CONF-1 resolved; OPEN-I(b) = B-ii) |

**Deterministic formulation of P3 / P4, per candidate M with CE(M):**

```
DB-homogeneous M (DB contrast):
  s_T(M) = 1  iff  ∃ D ∈ A(M) : TC_M(D)                             else 0
  s_P(M) = 1  iff  ∃ D ∈ A(M) : run_M(D) > R_P^(D)  (DB rule)        else 0
  instants: the first such session D (observable at D's close; label per imported OPEN-6)

HF-homogeneous M (HF contrast):
  s_T(M) = 1  iff  ∃ τ ∈ 𝒯_M : TC_M(d(τ))                           else 0      (OPEN-I(a) = A-ii)
  s_P(M) = 1  iff  ∃ τ ∈ 𝒯_M : PC_M(τ)                              else 0      (OPEN-C = A, built into PC_M)
  instants: the first such genuine 1m bar τ (OD-7)

Crossing M (CE = FALSE): no s_T, no s_P; absent from both contrasts                (OPEN-I(b) = B-ii)

In every case λ and μ are never consulted (OPEN-H = B; OPEN-F).
```

- **HF time observability (OPEN-I(a) = A-ii).** If TC_M first becomes true at the date level on a
  session D with ¬G(D), that date-level crossing is **not** an HF-observable crossing. Because TC_M is
  monotone in D (§3.4), it still holds at every later active session. The time score is recognized at
  the first genuine 1m bar τ ∈ 𝒯_M with d(τ) > D. If no genuine bar remains in A(M), s_T(M) = 0. This
  is the formula above; nothing further is chosen.
- **Symmetry (derived).** With A-ii, the HF time and price legs follow the same rule: each counts only
  at a genuine 1m bar in A(M). A no-bar price crossing surfaces at the next genuine bar through
  LowHist (NC-11), and a no-bar time crossing surfaces at the next genuine bar through TC_M's
  monotonicity. The v0.5 observability asymmetry (v0.5 OPEN-I(a)) is removed.
- **Derived, not chosen (carried from v0.5).** OPEN-H = B asks *"whether the underlying time condition
  TC_M(D) is satisfied for that candidate"*, which is an existential over the active span, so the
  score is a binary indicator. OPEN-F applies the same candidate-level, latch-free treatment to price.
- **Spent flags never reach P3/P4 (derived).** A candidate is time- or price-spent only if it is
  active at S_HF with a crossing on some active D < S_HF (§3.8). Such a candidate is crossing, so
  CE = FALSE (NC-16).
- **Not defined here:** the statistic T(·), its p-value (imported **G-4**), the mapping of candidate
  scores and instants to weekly formation scores s_T(i, w), s_P(i, w) (imported **OPEN-11**), the
  timestamp label (imported **OPEN-6**) and the outcome anchor (imported **OPEN-12**). No statistic is
  invented in this record.
- **Consistency with P1 (derived).** Every P1 event comes from a matched candidate with s_T = 1 at
  the same instant **if that candidate is contrast-eligible**. A later eligible candidate in the same
  episode can have s_T = 1 with no P1 event (NC-13). An eligible HF candidate whose time condition
  first held on a no-bar session has no P1 event (RQ-11 = D) but can have s_T = 1 at a later genuine
  bar (NC-15).
- **Consistency with P2 (derived).** A P2 flag from an eligible candidate implies s_P = 1 for it. An
  eligible candidate can have s_P = 1 with no P2 flag (μ already set). Unmatched and crossing
  candidates can produce P2 flags but contribute nothing to P4.
- **Sample-end censoring of P3/P4:** OPEN-J (§5.3).

### 3.8 Events, latches and profile rules (operational populations P1, P2)

| Rule | Definition | Status |
|---|---|---|
| D*_M | min{ D : TC_M(D) } | LOCKED |
| λ(E), μ(E) | FALSE when E opens | LOCKED |
| Latch scope | λ governs P1 only. μ governs P2 only. **Neither is consulted by P3 or P4** | LOCKED (OPEN-H = B; OPEN-F) |
| DB GF-10 event | ¬λ → event at D*_M; λ := TRUE | LOCKED |
| HF GF-10 event | ¬λ ∧ G(D*_M) ∧ D*_M ≥ S_HF ∧ M not time-spent → event at the first genuine 1m bar; λ := TRUE | LOCKED |
| HF no-bar time crossing | ¬λ ∧ ¬G(D*_M) ∧ D*_M ≥ S_HF ∧ M not time-spent → no event; λ := TRUE. **Unchanged by OPEN-I(a)**: the A-ii deferral applies to P3 only, never to P1 | LOCKED (RQ-11 = D) |
| HF price flag | ¬μ ∧ G(D) ∧ PC_M(τ) ∧ M not price-spent → flag at genuine bar τ; μ := TRUE | LOCKED (RQ-4, OPEN-C) |
| HF no-bar price | No evaluation; μ unchanged; D's EOD low enters LowHist from D⁺ | LOCKED (OPEN-C = A) |
| HF substrate start | At S_HF, for every open episode: λ := FALSE, μ := FALSE. K3, S9, ledger and candidates carried from EOD | LOCKED (RQ-10 = B, OPEN-G = A) |
| Spent candidate (per leg) | M active at S_HF is **time-spent** if ∃ D < S_HF with D active and el_M(D) > R_T. It is **price-spent** if ∃ D < S_HF with D active and the EOD run (DB rule) exceeds R_P^(D). A spent leg emits no HF event or flag from M and sets no latch. The other leg of M, and every other candidate, are unaffected. For P3/P4: not applicable, since every spent candidate crosses S_HF and is ineligible (OPEN-I(b) = B-ii) | LOCKED for P1/P2 (OPEN-B = B) |
| Contrast eligibility at S_HF | Every candidate whose active span crosses S_HF, spent or not, is excluded from P3/P4. Its P1/P2 treatment is exactly the preceding rows | **LOCKED (OPEN-I(b) = B-ii)** |
| DB end / separation | DB events stop at the end of DB availability; never pooled with HF. P3/P4 are formed **per profile** from substrate-homogeneous candidates only and are never pooled | RESOLVED; NC-6; OPEN-I(b) = B-ii |

---

## 4. State machine and timeline (per stock; bull shown, bear mirrors)

```text
State (read on D from 𝔉(D), re-based as-of-D):
  K3: ℓ, runs, swing points (first-occurrence), RH and last establishing session, open reaction ρ (if any)
  S9: σ; episode E; λ(E); μ(E)                                   ← λ, μ: operational P1/P2 only
  Ledger(E): K3 members (dur on swing dates; literal mag; terminating close); reactions (mag; completion close)
  Candidate M: (P_S, d_S, c), time-spent flag, price-spent flag, matched?, CE?, s_T(M), s_P(M)
  Profile: DB | HF (from S_HF)                                    ← prof(D); the observation boundary is S_HF
```

| Phase | What happens | Locks |
|---|---|---|
| **A. UP line** | Update RH. A session with H > RH (strict) is an establishing session e (the up-switch close establishes the first RH). If e⁺ is LL, ρ opens with Top = H_e; an outside-day LL session continues ρ normally (it raises RH for later reactions only). A 2nd LL session is ρ's 2nd session; a 3rd consecutive LL makes the run a K3 switch (ρ discarded). On the first non-LL close, ρ completes; if a BULL E is open it enters Ledger(E) | OPEN-2.x; RQ-6/7; OPEN-D/E; RQ-1 |
| **B. Down-switch close c** | X⁺ confirmed; S9 recomputed. On a change, E closes (ledger, λ, μ discarded) and a new E may open at c. If S9_c = BULL, M is a candidate member (SC-3 even when d_S < a). 𝒰_T and 𝒰_P fixed from members completed ≤ d_S; R_T on K3 swing dates; R_P = combined maximum of literal magnitudes. M is **matched** iff 𝒰_T ≠ ∅; s_T(M) = s_P(M) = 0 initially. Its contrast profile is provisionally prof(c⁺) | R-1; OPEN-3b; SC-3; RQ-1/2/5/8; OPEN-A; RQ-3 |
| **C. Active session D ∈ (c, u]** | **P1 (time, operational):** ¬λ ∧ 𝒰_T ≠ ∅ ∧ el > R_T (∧ HF: D ≥ S_HF, not time-spent) → DB: event at D; HF with G(D): event at the first genuine bar; HF without G(D): no event (RQ-11 = D). Each sets λ := TRUE. **P2 (price, operational):** HF with ¬G(D): skipped (μ unchanged). Otherwise if ¬μ ∧ 𝒰_P ≠ ∅ ∧ run > R_P (∧ HF: not price-spent) → flag (HF: the genuine bar; DB: D's close); μ := TRUE. Recorded whether or not M is matched or eligible. **P3/P4 (contrast, matched M only; λ and μ not read):** DB session: if TC_M(D), s_T(M) := 1; if run_M(D) > R_P, s_P(M) := 1. HF session with G(D): if TC_M(D), s_T(M) := 1 at D's first genuine bar; if PC_M(τ) at a genuine τ, s_P(M) := 1. HF session with ¬G(D): no P3/P4 update (A-ii; OPEN-C); a date-level TC_M crossing here is recognized at the next genuine bar in A(M). New lows extend run; no clock reset; no termination on a new high | OD-7/8/9; OPEN-4.x; RQ-3/4/8/9/11; OPEN-B/C; OPEN-H = B; OPEN-F; **OPEN-I(a) = A-ii** |
| **D. Up-switch close u** | M active on u, ends after it. **CE(M) is determined**: TRUE iff M is matched and prof is constant over (c, u]. If CE(M), s_T(M) and s_P(M) are final in the contrast of prof(A(M)); otherwise M is excluded from P3/P4 and any provisional scores are discarded. If E continues, M enters the ledger: dur = cal(d_l) − cal(d_h); mag = literal minimum over (d_h, u] | OPEN-4.3; RQ-8; OPEN-A; **OPEN-I(b) = B-ii** |
| **E. Latches** | λ = TRUE stops GF-10 events (P1) in E. μ = TRUE stops recorded price flags (P2) in E. They are independent. **Neither affects P3 or P4** | OD-4/6; RQ-4; RQ-11; OPEN-H = B; OPEN-F |
| **F. S9 reset** | E closes; ledger, λ and μ discarded; new E with an empty ledger and λ = μ = FALSE; SC-3 joins; RQ-1 exclusion. P3/P4 are per-candidate and carry no episode state | OD-5; SC-3; RQ-1 |
| **G. HF substrate start S_HF** | For every open episode: λ := FALSE, μ := FALSE. Each active candidate is checked per leg on EOD-era sessions: a time crossing before S_HF → time-spent; an EOD price crossing before S_HF → price-spent. Spent legs emit nothing into P1/P2 and set no latch; unspent legs and later candidates proceed normally. **Every candidate active on both S_HF⁻ and S_HF (spent or not) is marked crossing: CE(M) = FALSE**, excluded from P3/P4; its P1/P2 treatment is unchanged. Candidates confirmed at c ≥ S_HF⁻ (first active session ≥ S_HF) are HF-homogeneous | RQ-10 = B; OPEN-G = A; OPEN-B = B; X-2 = A; **OPEN-I(b) = B-ii** |
| **H. Formal contrast** | Over candidates with CE(M), per profile (HF and DB never pooled): **P3** = s_T(M), from TC_M, independent of λ, HF-observable only at genuine bars; **P4** = s_P(M), from PC_M, independent of μ. T(time) − T(price) is computed from P3/P4 **only**, never from P1 or P2. Statistic and weekly mapping: imported G-4 / OPEN-11. Sample-end censoring: OPEN-J | RQ-3 = C; R-10; OPEN-F (CONF-1 resolved); OPEN-H = B; **OPEN-I(a) = A-ii; OPEN-I(b) = B-ii**; X-2; G-4 |

**Timelines (schematic):**

```text
Outside-day reaction (OPEN-E = A, OPEN-D = A):
  e: H_e new RH → s₁: LL and H_{s₁} > H_e (outside) → s₂: LL → s₃: non-LL
  ρ = {s₁, s₂}, Top = H_e, mag = H_e − L_{s₂}; RH after ρ = H_{s₁}
  s₃ establishes only if H_{s₃} > H_{s₁}

Equal high (OPEN-D = A):
  e: H_e = RH (not strictly above) → e⁺ LL: not a reaction

HF start with a spent candidate (OPEN-B = B, OPEN-G = A, RQ-10 = B, OPEN-I(b) = B-ii):
  E open; M active; el_M > R_T already on an EOD-era date → M time-spent
  at S_HF: λ = μ = FALSE; M emits no HF event; M's price leg is checked separately (P1/P2)
  M crosses S_HF → CE(M) = FALSE → absent from P3 and P4
  next candidate M₂ in E (c₂ ≥ S_HF⁻) can emit an HF event normally and is HF-homogeneous

HF no-bar session (RQ-11 = D, OPEN-C = A, OPEN-I(a) = A-ii):
  D with ¬G(D): TC_M(D) first true → P1: no event, λ := TRUE; P2: price not evaluated, μ unchanged
  D⁺ with G, M still active: P3: s_T(M) := 1 at D⁺'s first genuine bar (NC-15)
                             P4: LowHist includes L_D → s_P(M) := 1 at D⁺'s first genuine bar if PC_M holds (NC-11)
  if D = u (no active session remains): s_T(M) = 0 from this crossing

Two eligible matched candidates in one episode (OPEN-H = B, OPEN-F):
  M₁: TC holds → P1 event, λ := TRUE; s_T(M₁) = 1
  M₁: PC holds → P2 flag, μ := TRUE; s_P(M₁) = 1
  M₂ (later): TC holds → no P1 event (λ TRUE); s_T(M₂) = 1
  M₂: PC holds → no P2 flag (μ TRUE); s_P(M₂) = 1
  Contrast sees both candidates on both legs
```

---

## 5. OPEN items

### 5.1 Resolved in v0.5 (historical record)

| Item | v0.4 status | v0.5 resolution |
|---|---|---|
| CONF-1 | Confirmation requested: OPEN-F letter "A" vs its wording | **RESOLVED.** Wording authoritative. The letter is non-authoritative where it conflicts. The wording corresponds in substance to v0.3 option (c) |
| OPEN-H | OPEN: per-candidate scores and latch symmetry | **LOCKED = B.** Sub-question (i) answered by derivation from the ruling's wording; sub-question (ii) answered by the ruling |

### 5.2 Resolved in v0.6

| Item | v0.5 status | v0.6 resolution |
|---|---|---|
| OPEN-I(a) | OPEN: HF observability of the contrast time score (TC_M has no G(D) term; PC_M does) | **LOCKED = A-ii.** P3 counts only at a genuine 1m bar; a no-bar date-level crossing is recognized at the next genuine bar in A(M), if any. P1 and RQ-11 = D unchanged (§3.7, §3.8, §4 C) |
| OPEN-I(b) | OPEN: contrast treatment of candidates active across S_HF and of spent legs | **LOCKED = B-ii.** Candidates crossing S_HF are excluded from P3 and P4; no reassignment, split or cross-scoring. Contrast-eligibility rule only; P1/P2 unchanged (§3.7, §3.8, §4 D/G) |

**OPEN-I is fully RESOLVED/LOCKED.**

### 5.3 OPEN-J — Sample-end censoring of P3/P4 candidates (surfaced in the v0.6 audit)

| Field | Entry |
|---|---|
| Exact issue | s_T(M) and s_P(M) are existential indicators over the whole active span A(M) = (c, u], and CE(M) is fixed at u (§4 D). A candidate still active on the **last session of the evaluation sample** has no observed u. Its scores may be 0 only because the span is truncated, and its HF/DB homogeneity is known but its span is incomplete. The record does not say whether such a candidate enters P3/P4, or with what scores |
| Why it matters | Censored candidates enter the contrast either as scored 0s (biasing both T(time) and T(price) toward 0, and not symmetrically, because the legs reach their thresholds at different times) or not at all. It changes P3/P4 membership at every sample end: the development / holdout / sealed window boundaries used by the freeze. P1 and P2 are event populations with no 0 scores, so they are not affected |
| Choices | (i) Score over the observed part of A(M): a censored candidate enters with the scores reached by the sample end. (ii) Exclude from P3/P4 any candidate whose u falls after the sample end (a completeness eligibility rule, parallel to OPEN-I(b) = B-ii). (iii) Leave it to the imported sample-window / freeze definitions (G-5 … G-9, OPEN-12) and state the dependency here. (iv) Other |
| Dependencies | OPEN-H = B and OPEN-F (the existential indicator form); OPEN-I(b) = B-ii (eligibility fixed at u). Coupled to imported G-4, OPEN-11, OPEN-12 and the freeze's window boundaries |
| Provenance | [NES]. No Gann source bears on it; any answer is [LOD] |
| Classification | **Definitional** (P3/P4 membership and values). Not implementation-level |
| Origin | Pre-existing since v0.5 (it follows from the v0.5 span-indicator form). **Not created by OPEN-I(a) or OPEN-I(b).** Recorded in v0.6 because this audit is the first to check the contrast's span boundaries explicitly |
| Scope | P3/P4 only. P1 and P2 are fully defined without it |

### 5.4 Imported, open elsewhere (not re-analysed)

- **Gaps:** G-4 (contrast p), G-5, G-6, G-7 (also needed for RQ-9 = x re-basing), G-8, G-9.
- **Preconditions:** P-1 … P-5, including the R-13 external CA list (P-2).
- **Draft items:** OPEN-6 (timestamp label), OPEN-11 (weekly score mapping, including how the P3/P4
  candidate indicators map to s_T(i, w), s_P(i, w)), OPEN-12 (outcome window).

---

## 6. Checks

| # | Item | v0.6 verdict |
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
| 6.10 | Matched contrast | **RESOLVED:** P3 independent of λ (OPEN-H = B); P4 independent of μ (OPEN-F); HF observability symmetric at genuine bars (OPEN-I(a) = A-ii); substrate-homogeneous eligibility (OPEN-I(b) = B-ii). Four populations distinct (§3.7). **Sample-end censoring: OPEN-J** |

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
| NC-8 | The first candidate of every episode has 𝒰_T = ∅ (derived); it is therefore never matched and contributes to neither P3 nor P4 |
| NC-9 | A qualifying reaction can set R_P above every ledger K3 decline (derived) |
| NC-10 | OPEN-A = A: one reference move carries a K3 swing-low **date** for time and a possibly earlier literal-minimum **price** for magnitude |
| NC-11 | OPEN-C = A with RQ-9: a price crossing that occurred on a no-bar HF session can surface as a flag on the next session with genuine bars (via its EOD low in history) if the move is still active and μ is FALSE. This is the first HF-observable instant (OD-7), not a same-session flag. The same surfacing applies to s_P in P4 |
| NC-12 | OPEN-B = B makes a candidate's spent status per leg: a candidate can be time-spent but price-live, or the reverse |
| NC-13 | OPEN-H = B: in an episode with several eligible matched candidates, P3 can hold more time crossings than P1 holds events. The GF-10 event count and the contrast's time count are **different objects** and must never be substituted for each other |
| NC-14 | OPEN-F: likewise, P2 flags and P4 scores are different objects. P2 includes unmatched and crossing candidates, which P4 excludes, and P4 includes post-μ candidates, which P2 excludes |
| NC-15 | OPEN-I(a) = A-ii vs RQ-11 = D: for a time crossing first true on a no-bar HF session, P1 records **no event and sets λ**, while P3 recognizes s_T = 1 at the next genuine bar in A(M). This divergence is by design: P1 is latch/event state, P3 is the candidate-level condition. An HF P3 time instant can therefore fall on a later session than D*_M |
| NC-16 | OPEN-I(b) = B-ii with OPEN-B = B: every spent candidate crosses S_HF, so spent flags have no role in P3/P4. A crossing candidate can still produce P1 events and P2 flags per the §3.8 rules |
| NC-17 | Substrate homogeneity is judged on the active span only. An HF-homogeneous candidate's references (R_T, R_P, ledger) may come entirely from pre-S_HF EOD history (X-1, X-2). The profile is HF for every session ≥ S_HF (§3.1 prof), so a later session without genuine 1m bars is an **HF no-bar session** (A-ii, RQ-11, OPEN-C), not a return to DB; S_HF is the only observation boundary |

---

## 7. Internal-consistency audit (v0.6)

### 7.1 Result

**v0.6: PASS. OPEN-I fully resolved. One newly surfaced definitional item, OPEN-J (pre-existing, not
caused by the OPEN-I rulings).**
- **53 locked decisions** audited: the 51 of v0.5 plus **OPEN-I(a) = A-ii** and **OPEN-I(b) = B-ii**.
- No contradiction among the 53 locks. No contradiction between §1.2, §2, §3, §4 and §9.
- OPEN-I(a) does not alter P1 or RQ-11 = D. OPEN-I(b) does not alter P1 or P2.
- P3/P4 remain latch-independent: λ and μ are not consulted by P3 or P4.
- HF and DB are not pooled. The observation boundary (S_HF, via prof(D)) is explicit.
- The decision ledger (§9) and the state machine (§4) agree.
- Every remaining OPEN-I reference is either the locked ruling (A-ii / B-ii) or historical/audit text.

### 7.2 Checks required by the v0.6 handoff

| ID | Check | Result |
|---|---|---|
| W-1 | No locked decision contradicts another | PASS (§7.4 register) |
| W-2 | OPEN-I(a) does not alter P1 / RQ-11 | PASS. §3.8 row "HF no-bar time crossing" keeps no-event + λ := TRUE and states the A-ii deferral applies to P3 only. §4 C lists P1 and P3 separately. Divergence disclosed (NC-15) |
| W-3 | OPEN-I(b) does not alter P1/P2 | PASS. §3.7 P1/P2 rows state "includes crossing candidates" / "whether or not … contrast-eligible". §3.8 eligibility row: "Its P1/P2 treatment is exactly the preceding rows". §4 G keeps the spent-leg rules for P1/P2 |
| W-4 | P3/P4 remain latch-independent | PASS. §3.7 formulation contains no λ or μ term; §3.8 "Latch scope"; §4 C "λ and μ not read"; §4 E |
| W-5 | λ and μ not consulted by P3/P4 | PASS (as W-4). CE(M) is built from 𝒰_T and prof only; neither reads a latch |
| W-6 | HF and DB not pooled | PASS. CE assigns each eligible candidate to exactly one profile; crossing candidates are in neither; §3.8 "DB end / separation"; §4 H "per profile" |
| W-7 | Observation boundary explicit | PASS. prof(D) in §3.1; homogeneity classes in §3.7 (u < S_HF / c⁺ ≥ S_HF / crossing); §4 state line and phase G; NC-17 |
| W-8 | Ledger ↔ state machine agreement | PASS. OPEN-I(a) = A-ii is applied in §4 C/H and in ledger §3.7/§3.8/§4 C; OPEN-I(b) = B-ii in §4 B/D/G/H and in ledger §3.7/§3.8/§4 D/G. Every ledger "Applied in" cell was checked against its target |
| W-9 | No unresolved OPEN-I reference | PASS. Text scan: OPEN-I appears only as "OPEN-I(a) = A-ii", "OPEN-I(b) = B-ii", "OPEN-I is fully RESOLVED", in §5.2 (resolved table), in the change log, and in historical v0.5 rows (e.g. v0.5 OPEN-I(a) in §3.7's symmetry note) |

### 7.3 Checks carried from v0.5 (re-verified)

| ID | Check | Result |
|---|---|---|
| B-1 | OPEN-A = A vs RQ-8 = A | Consistent (NC-10) |
| B-2 | OPEN-A = A vs OPEN-4.4 = A | Consistent: different objects |
| B-3 | OPEN-B = B vs RQ-10 = B | Consistent: only the spent candidate's leg is suppressed in P1/P2 |
| B-4 | OPEN-B = B vs X-2 = A and OD-7 | Consistent for P1/P2. For P3/P4: crossing candidates excluded (OPEN-I(b) = B-ii), so no DB-era observation enters the HF contrast — consistent |
| B-5 | OPEN-B = B vs C-7 | Consistent |
| B-6 | OPEN-C = A vs RQ-11 = D | Consistent for P1/P2. For P3/P4: both legs now observe at genuine bars only (OPEN-I(a) = A-ii) — consistent |
| B-7 | OPEN-C = A vs RQ-9 = A+x and OD-7 | Consistent (NC-11) |
| B-8 … B-12 | OPEN-D / OPEN-E vs OPEN-4.5, RQ-7, RQ-6, OPEN-2.1/2.3 | Consistent (unchanged) |
| B-13 | OPEN-F vs RQ-3 = C / RQ-4 = A | Consistent: P2 recorded with μ; P4 ignores μ |
| B-14 | OPEN-F vs OD-4 | Closed by OPEN-H = B (v0.5) |
| B-15R | OPEN-F letter vs v0.3 (a) | Resolved (CONF-1, v0.5) |
| B-16, B-17 | OPEN-G = A vs OPEN-B = B, RQ-4 = A | Consistent |
| V-1 … V-7 | OPEN-H = B vs OD-4, C-7, RQ-10/11, RQ-3; OPEN-F vs RQ-4; OPEN-H vs OPEN-F; scoring vs latches | Consistent (unchanged; V-3 now closed by OPEN-I rulings) |
| V-8 | OPEN-B = B vs OPEN-H = B / OPEN-F | v0.5 gap → **closed by OPEN-I(b) = B-ii** (NC-16) |
| V-9 | OPEN-C = A vs OPEN-H = B | v0.5 gap → **closed by OPEN-I(a) = A-ii** (symmetry note, §3.7) |
| V-10 | OPEN-G = A vs OPEN-F | Consistent |
| V-11 | HF/DB separation | Consistent; straddling candidates → excluded (B-ii) |
| V-12 | D−1 boundary | Consistent: A-ii and CE(M) add no information; CE(M) is a function of the candidate's own span and S_HF, both known without looking ahead of the scoring instant except for u (fixed at §4 D, the candidate's end) |
| V-13 | First-observable-crossing rule (OD-7) | Consistent: HF P3/P4 instants are the first genuine bar at which the condition holds; DB instants are the first session |
| V-14 … V-18 | Current/reference alignment; reaction/K3 separation; literal windows vs K3 dates; RQ-3 recording; NC-8 | Consistent (unchanged) |
| V-19 | §2 attribution | PASS: OPEN-I, substrate homogeneity and OPEN-J appear only in the LOCKED OPERATOR / [NES] columns |

### 7.4 Checks added for v0.6

| ID | Check | Result |
|---|---|---|
| Y-1 | OPEN-I(a) = A-ii vs OD-7 | Consistent: A-ii is the first-observable rule applied to P3 |
| Y-2 | OPEN-I(a) = A-ii vs OPEN-C = A | Consistent and symmetric: both legs observe at genuine bars only in HF |
| Y-3 | OPEN-I(a) = A-ii vs OPEN-H = B | Consistent: A-ii sets observability, not latching; P3 still ignores λ |
| Y-4 | OPEN-I(a) = A-ii scope | A-ii governs HF-homogeneous candidates only; DB candidates have no genuine-bar requirement (DB uses EOD) — consistent with X-1/X-2 |
| Y-5 | OPEN-I(b) = B-ii vs OPEN-B = B | Consistent: B-ii makes spent status irrelevant to P3/P4 (NC-16) |
| Y-6 | OPEN-I(b) = B-ii vs RQ-10 = B / OPEN-G = A | Consistent: those reset latches for P1/P2; B-ii reads no latch |
| Y-7 | OPEN-I(b) = B-ii vs X-1 / X-2 (EOD lookback) | Consistent: homogeneity is judged on A(M) only; EOD-built references are allowed (NC-17) |
| Y-8 | OPEN-I(b) = B-ii vs C-7 (each move an independent candidate) | Consistent: exclusion is per candidate; other candidates in the same episode are unaffected |
| Y-9 | OPEN-I(b) = B-ii vs RQ-3 = C (matched contrast) | Consistent: CE(M) = matched ∧ homogeneous, a subset of the RQ-3 matched set |
| Y-10 | OPEN-I(a) × OPEN-I(b) | Independent: A-ii applies inside the HF contrast; B-ii decides who is in it |
| Y-11 | Boundary identity of "crossing" | Deterministic: crossing iff min A(M) < S_HF ≤ u. A candidate confirmed at c = S_HF⁻ has first active session S_HF and is HF-homogeneous; its confirmation close itself is not in A(M) |

### 7.5 Lock-by-lock register (53)

**Unaffected** means v0.6 does not change the text that applies it. **Scoped** means its text says it
governs P1/P2. **Consistent** means the check is listed above.

| Group | Locks | Result |
|---|---|---|
| OD | OD-1, OD-2, OD-3, OD-5, OD-6, OD-8, OD-9, OD-10 | Unaffected |
| OD | OD-4 | Scoped to P1 |
| OD | OD-7 | Consistent (Y-1, V-13) |
| C | C-1/C-2/C-3 (one ledger row), C-4, C-5, C-6 | Unaffected; C-2 extends to P3/P4 (W-6) |
| C | C-7 | Consistent (Y-8) |
| X | X-1 = A, X-2 = A | Consistent (Y-4, Y-7, B-4) |
| OPEN-3/4 | OPEN-3b, OPEN-4.1, 4.2, 4.3, 4.4, 4.5 | Unaffected |
| SC | SC-3 = A | Unaffected |
| OPEN-2 | OPEN-2.1, 2.2, 2.3, 2.4, 2.5 | Unaffected |
| OPEN-1 | OPEN-1 = A | Unaffected (NC-8) |
| RQ | RQ-1, RQ-2, RQ-5, RQ-6, RQ-7, RQ-8, RQ-9 | Unaffected |
| RQ | RQ-3 = C | Consistent (Y-9) |
| RQ | RQ-4 = A | Scoped to P2 |
| RQ | RQ-10 = B | Scoped to P1 (Y-6) |
| RQ | RQ-11 = D | Scoped to P1; unaltered by A-ii (W-2, NC-15) |
| OPEN-A…G | OPEN-A, OPEN-D, OPEN-E | Unaffected |
| OPEN-A…G | OPEN-B = B | Scoped to P1/P2 (Y-5) |
| OPEN-A…G | OPEN-C = A | Consistent (Y-2) |
| OPEN-A…G | OPEN-F | Consistent (B-13) |
| OPEN-A…G | OPEN-G = A | Scoped to P2 (Y-6) |
| v0.5 | OPEN-H = B | Consistent (Y-3) |
| v0.6 | OPEN-I(a) = A-ii | Consistent (Y-1 … Y-4, Y-10) |
| v0.6 | OPEN-I(b) = B-ii | Consistent (Y-5 … Y-11) |

Count: 43 (v0.3) + 7 (OPEN-A … OPEN-G) + 1 (OPEN-H) + 2 (OPEN-I(a), OPEN-I(b)) = **53**.

### 7.6 Newly exposed definitional ambiguity

- **OPEN-J** (§5.3): sample-end censoring of P3/P4 candidates. Pre-existing since v0.5, **not created
  by OPEN-I(a) or OPEN-I(b)**. Not resolved here.
- No other new ambiguity was found. In particular: the "crossing" boundary is deterministic (Y-11); a
  no-bar HF session after S_HF stays HF (NC-17), so no second boundary exists; and spent flags cannot
  reach P3/P4 (NC-16).

---

## 8. Future work — what empirical testing must NOT decide

**Definitional (before any data read; never from results):**
- **OPEN-J.**
- Every lock in §9.
- Any later threshold, window, adjacency or source rule.

No choice may be justified by event counts, coverage, "too few/many events", IC, Sharpe, surrogate p,
contrast p, size-check outcome or any O-R10 association. This includes counts of P3/P4 candidates
excluded by OPEN-I(b) = B-ii or affected by OPEN-J.

**Empirical (pre-registered read, after freeze only):**
- GF-10 events (P1) vs O-R10 beyond the surrogate null (R-14).
- T(time) vs T(price) on contrast-eligible candidates, from P3/P4 (R-10, RQ-3 = C, G-4).
- Descriptive statistics: reported, never used to revise definitions.

**Implementation (code review and deterministic tests, not results):**
- K3/S9 (memo §5); establishing-session strictness; outside-day continuation.
- D−1 freeze; causal prefix invariance; byte-identical replay.
- As-of-D re-basing and 1m normalization (ratio test).
- G(D) via `is_synthetic = FALSE`, `bar_labeling.py`, GAP sessions and `SPECIAL_SESSIONS`.
- Independent λ/μ; per-leg spent flags at S_HF.
- P3/P4 computed without reading λ or μ; P1/P2 and P3/P4 kept as separate outputs (a test must show
  that toggling λ/μ state cannot change s_T or s_P).
- **A-ii:** a test where TC_M first holds on a no-bar session must show P1 = no event + λ set, and
  s_T = 1 at the next genuine bar (or 0 if none remains in A(M)).
- **B-ii:** a test must show a crossing candidate is absent from P3/P4 while its P1/P2 output is
  byte-identical to the v0.5 rules.
- First-occurrence ties; timestamp label (imported OPEN-6).

---

## 9. Decision ledger

| ID | Decision | Status | Applied in |
|---|---|---|---|
| OD-1 | Time leg: greatest qualifying previous decline/rally | LOCKED | §1.2-14; §3.4 |
| OD-2 | "Decline or reaction"; 1/2/3-day framework; reaction ≠ K3 | LOCKED | §1.2-15; §3.6 |
| OD-3 | Bear = S9 bear | LOCKED | §1.2-5 |
| OD-4 | First exceedance per S9 episode (operational population P1) | LOCKED | §1.2-21; §3.8 |
| OD-5 | Reset on S9 reversal or cessation | LOCKED | §1.2-11; §4 F |
| OD-6 | Symmetric bull/bear | LOCKED | §1.2-21 |
| OD-7 | First objectively observable crossing | LOCKED | §1.2-19; §3.7; §3.8 |
| OD-8 | Running extreme | LOCKED | §1.2-16; §3.5 |
| OD-9 | Strict `>` | LOCKED | §1.2-18 |
| OD-10 | Finest available resolution | LOCKED (via HF/DB) | §1.2-1 |
| C-1/C-2/C-3 | HF 1m / DB daily; never pooled; D−1 freeze | LOCKED | §1.2-1, 6; §3.8; §4 H |
| C-4 | K3 eligibility; K3 current move; reactions only bull price comparator | LOCKED | §1.2-7, 15, 17 |
| C-5 | OD-1 supersedes "immediately preceding" | LOCKED | §3.4 |
| C-6 | OD-7 supersedes week-end timing | LOCKED | §1.2-19 |
| C-7 | Move-level reset + episode-level first-event latch | LOCKED | §1.2-21/25; §4 |
| X-1 = A | HF 1m detection; EOD K3/S9 context, pre-substrate allowed | LOCKED | §1.2-1; §3.1 prof |
| X-2 = A | Never pool; HF may use EOD lookback | LOCKED | §1.2-1; §3.7; §3.8 |
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
| RQ-3 = C | Price flags independent (P2); formal contrast on matched candidates (P3/P4) | LOCKED | §3.7; §4 H |
| RQ-4 = A | Independent first-per-episode price latch (P2) | LOCKED | §3.8 |
| RQ-5 = A | References completed ≤ d_S | LOCKED | §3.4; §3.7 |
| RQ-6 = A | Reaction top excludes reaction-session highs | LOCKED | §3.6 |
| RQ-7 = B | Reaction begins immediately after the establishing session | LOCKED | §3.6 |
| RQ-8 = A | Literal running-price window, current and reference | LOCKED | §3.5 |
| RQ-9 = A+x | EOD history; genuine 1m on D; as-of-D normalization | LOCKED | §3.1; §3.5 |
| RQ-10 = B | HF time latch FALSE at substrate start | LOCKED | §3.8; §4 G |
| RQ-11 = D | HF no-bar time crossing: no event, latch set (P1; unaltered by OPEN-I(a)) | LOCKED | §3.8; §4 C |
| OPEN-A = A | K3 swing dates for time; literal extreme for price | LOCKED | §1.2-14/16; §3.4; §3.5 |
| OPEN-B = B | Pre-HF-crossed candidate spent (per leg); no HF event/flag; no latch (P1/P2) | LOCKED | §1.2-23; §3.8; §4 G |
| OPEN-C = A | No HF price evaluation without a genuine 1m bar | LOCKED | §1.2-16/22; §3.5; §3.7; §3.8 |
| OPEN-D = A | Only a strictly new extreme establishes the anchor | LOCKED | §1.2-15; §3.6 |
| OPEN-E = A | Outside-day reaction continues normally | LOCKED | §1.2-15; §3.6 |
| OPEN-F | Matched contrast price input independent of the episode price latch μ (wording authoritative; substance = v0.3 (c)) | LOCKED (wording; CONF-1 resolved) | §1.2-22/24; §3.7; §3.8; §4 H |
| OPEN-G = A | HF price latch starts FALSE | LOCKED | §1.2-22/23; §3.8 |
| OPEN-H = B | For the formal contrast only, the time input is the underlying condition TC_M(D) per candidate, independent of λ; operational P1 unchanged | LOCKED (v0.5) | §1.1; §1.2-21/24; §2; §3.7; §3.8; §4 C/E/H |
| **OPEN-I(a) = A-ii** | P3/P4 only: HF contrast time score requires genuine 1m observability; a no-bar date-level TC_M crossing is recognized at the next genuine 1m bar in the active span, if any. P1/RQ-11 unchanged | **LOCKED (v0.6)** | §1.1; §1.2-24; §3.1 𝒯_M; §3.4; §3.7; §3.8; §4 C/H; NC-15 |
| **OPEN-I(b) = B-ii** | P3/P4 only: a candidate whose active span crosses S_HF is excluded from both contrasts; not reassigned, split or cross-scored; eligibility rule, not candidate invalidation. P1/P2 unchanged | **LOCKED (v0.6)** | §1.1; §1.2-23/24; §3.1 prof; §3.7 CE(M); §3.8; §4 B/D/G/H; NC-16, NC-17 |
| CONF-1 | OPEN-F letter vs wording | RESOLVED (v0.5): wording authoritative | §5.1; §7.3 B-15R |
| OPEN-I | HF observability and S_HF / spent-leg treatment inside P3/P4 | **RESOLVED (v0.6)**: (a) = A-ii, (b) = B-ii | §5.2 |
| OPEN-J | Sample-end censoring of P3/P4 candidates | **OPEN (surfaced v0.6 audit; pre-existing since v0.5), definitional** | §5.3 |

## 10. Remaining decision order

| Step | Item | Depends on |
|---|---|---|
| 1 | OPEN-J (sample-end censoring of P3/P4 candidates), unless the operator assigns it to the imported sample-window / freeze items | OPEN-H = B, OPEN-F, OPEN-I(b) = B-ii (locked); G-5 … G-9, OPEN-12 (imported) |

CONF-1, OPEN-H and OPEN-I are closed.

**Readiness by population:**
- **P1 (GF-10 event population, the primary score) and P2 (price flags)** are defined at the
  mechanical level. Neither depends on OPEN-J.
- **P3/P4 (the R-10 specificity contrast)** are defined at the mechanical level except for sample-end
  censoring (OPEN-J).

After OPEN-J, the remaining work is the imported items: OPEN-6, OPEN-11 (including the P3/P4 →
weekly-score mapping), OPEN-12, G-4 … G-9 and P-1 … P-5. The freeze document comes after those.
v0.6 is a consolidated decision record: not an implementation specification and not an empirical
freeze.

---

**NO CODE. NO BACKTEST. NO EMPIRICAL TESTING. NO MARKET OUTCOMES READ. NO LOCKED DECISION REOPENED.
NOT FROZEN. NOT AN IMPLEMENTATION SPECIFICATION.**
