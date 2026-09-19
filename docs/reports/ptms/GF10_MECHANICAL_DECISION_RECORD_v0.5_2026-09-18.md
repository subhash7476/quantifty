# GF-10 Mechanical Decision Record — v0.5

**Date:** 2026-09-18

**Status: CONSOLIDATED DECISION RECORD — NOT AN IMPLEMENTATION SPECIFICATION, NOT A FREEZE.**
- No code, backtest, empirical test, optimization or performance analysis was performed.
- No market data or outcome was read. No event count was computed. Nothing is frozen or hashed.
- **No locked decision is reopened.**

**Supersedes:** v0.4 (`GF10_MECHANICAL_DECISION_RECORD_v0.4_2026-09-17.md`, uncommitted at the time of
writing), which is kept unchanged. Earlier versions: v0.3 (`d9a9119`), v0.2 (superseded; provenance
error) and v0.1 (`59e25da`).

**New in this version:** operator rulings made after v0.4, in conversation:

| Item | Operator ruling | Effect |
|---|---|---|
| CONF-1 | **RESOLVED.** The **wording** of OPEN-F is intended: *the matched time-vs-price contrast's price input is independent of the episode price latch μ.* The letter "A" in the earlier response is **not authoritative** where it conflicts with that wording | OPEN-F stands as worded. In substance it matches v0.3 option **(c)** (*"contrast price score ignores latching within the matched set"*), **not** v0.3 option (a). v0.3 (b), a second latch over the matched set, is excluded by OPEN-H = B's candidate-level ruling |
| OPEN-H | **LOCKED = B.** *For the formal contrast only, evaluate the underlying time condition per matched candidate independently of λ* | Operational GF-10 emission stays first-per-episode and λ-governed. The contrast does **not** inherit λ's first-event suppression. The contrast time input asks whether TC_M(D) holds for that candidate. The contrast price input stays independent of μ. The operational price-flag population stays first-per-episode and μ-governed. The contrast measures **candidate-level underlying conditions**, not the latch or reporting state |

**No mechanical ambiguity remains from the v0.4 OPEN-H / CONF-1 pair.** The audit re-run (§7)
surfaced **one new ambiguity, OPEN-I**, which OPEN-H = B created. It is recorded in §5 and not
resolved here.

**Construct label:** GF-10 = **GANN-FAITHFUL SOURCE CONCEPT + EXPLICIT OPERATOR/RESEARCH CONVENTIONS.**
It is not "Gann's exact rule".

**Provenance markers:**

| Marker | Meaning |
|---|---|
| **[GS]** | GANN SOURCE: verified wording or arithmetic; register ID given |
| **[LOD]** | LOCKED OPERATOR / RESEARCH DECISION |
| **[NES]** | NOT ESTABLISHED BY SOURCE; never to be attributed to Gann |

A [GS] marker on part of a rule does not extend to the rest of it. **OPEN-F, CONF-1, OPEN-H, OPEN-I,
every latch, and all contrast scoring are operator/research conventions: [LOD] and [NES], never
[GS].**

**Document layout:**

| Part | Sections |
|---|---|
| LOCKED | §1 – §4, §9 |
| OPEN (newly surfaced) and imported | §5 |
| Future implementation / empirical work | §8 |

---

## 0. Change log from v0.4

| # | Change | Sections |
|---|---|---|
| CL-1 | **CONF-1 RESOLVED:** OPEN-F is locked by its wording. The letter "A" is non-authoritative where it conflicts. The v0.4 ⚠ banner is removed; the v0.4 §5.1 confirmation-request entry is replaced by a resolved entry (v0.5 §5.1); audit row B-15 becomes resolved row B-15R | header; §5; §7; §9 |
| CL-2 | **OPEN-H = B LOCKED:** contrast time input = the underlying condition TC_M(D) per matched candidate, independent of λ | §1.1; §1.2-24; §3.7; §3.8; §4 H; §9 |
| CL-3 | The formal contrast is written as **four named populations**: P1 operational GF-10 events; P2 operational price flags; P3 contrast time score; P4 contrast price score | §1.2-24; §3.7; §4 H |
| CL-4 | The per-candidate score form, which v0.4 §5.2(i) left open, is **derived from the OPEN-H = B wording**: an existential indicator over the candidate's active span, applied symmetrically to both legs. This was not chosen freely. No statistic is defined here; T(·) stays with imported G-4 / OPEN-11 | §3.7 |
| CL-5 | Audit re-run over **51 locks** (50 + OPEN-H = B). **One new OPEN, OPEN-I:** HF observability (G(D)) and the substrate-start / spent-leg rules inside the candidate-level contrast | §5; §7 |
| CL-6 | New disclosure notes NC-13, NC-14 | §6.11 |
| CL-7 | §10 now holds OPEN-I only (CONF-1 and OPEN-H removed) | §10 |

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
                                            └─► P3/P4 FORMAL CONTRAST on matched candidates (RQ-3 = C, R-10):
                                                  P3 time score  = TC_M holds for M; independent of λ (OPEN-H = B)
                                                  P4 price score = PC_M holds for M; independent of μ (OPEN-F wording; CONF-1 resolved)
                                                  G(D) observability and S_HF / spent-leg treatment inside P3/P4: OPEN-I
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
| 21 | Time latch λ | One GF-10 event per stock per episode; reset only at a new episode; HF: FALSE at substrate start. **Governs P1 only** | [GS] "first time" (bear only); [LOD] OD-4/6, C-7, RQ-10 = B, RQ-11 = D, **OPEN-H = B**; [NES] |
| 22 | Price flag (P2) and latch μ | Recorded independently of time eligibility; independent first-per-episode latch; HF: FALSE at substrate start; not evaluated on no-bar HF sessions. **μ governs P2 only** | [LOD] RQ-3 = C, RQ-4 = A, OPEN-C = A, OPEN-G = A, **OPEN-F**; [NES] |
| 23 | HF substrate start | λ = μ = FALSE. A candidate whose leg crossing held on a pre-substrate session is **spent for that leg** (no HF event or flag from it; no latch set). Applies to P1/P2; application to P3/P4 is **OPEN-I** | [LOD] RQ-10 = B, OPEN-B = B, OPEN-G = A, X-2 = A; [NES] |
| 24 | Formal contrast (P3, P4) | T(time) − T(price) over matched candidates (𝒰_T ≠ ∅ ∧ 𝒰_P ≠ ∅). **P3:** per matched candidate, whether TC_M(D) holds in its active span, **independent of λ**. **P4:** per matched candidate, whether PC_M(τ) holds in its active span, **independent of μ**. Both are candidate-level underlying conditions, not latch or reporting state. P1 is GF-10's primary score; P3/P4 exist only as R-10's specificity contrast. Statistic T(·): imported G-4 / OPEN-11 | [GS] p. 12 ranking only; [LOD] RQ-3 = C, R-10, **OPEN-F (wording; CONF-1 resolved), OPEN-H = B**; [NES]. Observability and S_HF inside P3/P4: **OPEN-I** |
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
| Time more important than price | ✔ p. 12 (**the ranking only**) | Roles; matched contrast; four populations; candidate-level P3 independent of λ and P4 independent of μ (R-10, RQ-3, OPEN-F, CONF-1, OPEN-H = B) | Any statistic; the matched set; candidate-level scoring; latch treatment |
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
| A(M) | Active span of M: sessions D ∈ (c, u] | [LOD] OPEN-4.3 |

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
strictly with D and R_T is constant, TC_M(D) ⇒ TC_M(D′) for every later active D′ (derived).

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

**The four populations (OPEN-H = B, OPEN-F wording, CONF-1 resolved).** These populations are
distinct. None of them is derived from another's latch state.

| Pop. | Name | Membership / value | Latch | Role | Status |
|---|---|---|---|---|---|
| **P1** | Operational GF-10 event population | Per episode E, at most one event: the first observable time crossing by any candidate while λ(E) = FALSE, under the HF/DB, no-bar (RQ-11 = D) and spent-leg (OPEN-B = B) rules of §3.8 | λ(E), first-per-episode | GF-10's **primary score** (R-5, R-10) | LOCKED (OD-4, OD-7, C-7, RQ-10, RQ-11, OPEN-B) |
| **P2** | Operational (independent) price-flag population | Per episode E, at most one flag: the first observable price crossing by any candidate while μ(E) = FALSE, **whether or not the candidate is matched**, under OPEN-C, OPEN-B and OPEN-G | μ(E), first-per-episode, independent of λ | Recorded fact; not a score | LOCKED (RQ-3 = C, RQ-4 = A, OPEN-C, OPEN-G) |
| **P3** | Contrast time score (candidate-level) | For each **matched** candidate M: s_T(M) ∈ {0, 1} | **None.** Independent of λ | Specificity contrast only (R-10) | **LOCKED (OPEN-H = B)**; HF observability / S_HF: OPEN-I |
| **P4** | Contrast price score (candidate-level) | For each **matched** candidate M: s_P(M) ∈ {0, 1} | **None.** Independent of μ | Specificity contrast only (R-10) | **LOCKED (OPEN-F wording; CONF-1 resolved)**; HF observability / S_HF: OPEN-I |

**Deterministic formulation of P3 / P4, per matched candidate M:**

```
s_T(M) = 1  iff  ∃ D ∈ A(M) : TC_M(D)            else 0      (λ never consulted — OPEN-H = B)
s_P(M) = 1  iff  ∃ τ with d(τ) ∈ A(M) : PC_M(τ)  else 0      (μ never consulted — OPEN-F)
Crossing instant, where defined: the first objectively observable instant at which the condition holds (OD-7).
```

- **Derived, not chosen.** OPEN-H = B asks *"whether the underlying time condition TC_M(D) is satisfied
  for that candidate"*. That is an existential over the candidate's active span, so the score is a
  binary indicator. OPEN-F applies the same candidate-level, latch-free treatment to price. This
  answers v0.4 OPEN-H sub-question (i): an existential indicator is the same whether read "at any
  instant" or "at the first crossing".
- **Not defined here:** the statistic T(·), its p-value (imported **G-4**), the mapping of candidate
  scores and instants to weekly formation scores s_T(i, w), s_P(i, w) (imported **OPEN-11**), the
  timestamp label (imported **OPEN-6**) and the outcome anchor (imported **OPEN-12**). No statistic is
  invented in this record.
- **Consistency with P1 (derived).** The candidate that emits an episode's P1 event has s_T = 1 with
  the same D*_M. A later matched candidate in the same episode can have s_T = 1 with no P1 event
  (NC-13).
- **Consistency with P2 (derived).** A P2 flag from a matched candidate implies s_P = 1 for that
  candidate. A matched candidate can have s_P = 1 with no P2 flag (μ already set). An unmatched
  candidate can produce a P2 flag but contributes nothing to P4.
- **Open inside P3/P4 (OPEN-I):** whether the G(D) observability rule and the S_HF / spent-leg rules,
  which are defined for P1/P2, also apply to P3/P4. As written, TC_M carries no G(D) term while PC_M
  does (OPEN-C).

### 3.8 Events, latches and profile rules (operational populations P1, P2)

| Rule | Definition | Status |
|---|---|---|
| D*_M | min{ D : TC_M(D) } | LOCKED |
| λ(E), μ(E) | FALSE when E opens | LOCKED |
| Latch scope | λ governs P1 only. μ governs P2 only. **Neither is consulted by P3 or P4** | **LOCKED (OPEN-H = B; OPEN-F)** |
| DB GF-10 event | ¬λ → event at D*_M; λ := TRUE | LOCKED |
| HF GF-10 event | ¬λ ∧ G(D*_M) ∧ D*_M ≥ S_HF ∧ M not time-spent → event at the first genuine 1m bar; λ := TRUE | LOCKED |
| HF no-bar time crossing | ¬λ ∧ ¬G(D*_M) ∧ D*_M ≥ S_HF ∧ M not time-spent → no event; λ := TRUE | LOCKED (RQ-11 = D) |
| HF price flag | ¬μ ∧ G(D) ∧ PC_M(τ) ∧ M not price-spent → flag at genuine bar τ; μ := TRUE | LOCKED (RQ-4, OPEN-C) |
| HF no-bar price | No evaluation; μ unchanged; D's EOD low enters LowHist from D⁺ | LOCKED (OPEN-C = A) |
| HF substrate start | At S_HF, for every open episode: λ := FALSE, μ := FALSE. K3, S9, ledger and candidates carried from EOD | LOCKED (RQ-10 = B, OPEN-G = A) |
| Spent candidate (per leg) | M active at S_HF is **time-spent** if ∃ D < S_HF with D active and el_M(D) > R_T. It is **price-spent** if ∃ D < S_HF with D active and the EOD run (DB rule) exceeds R_P^(D). A spent leg emits no HF event or flag from M and sets no latch. The other leg of M, and every other candidate, are unaffected. Effect on P3/P4: **OPEN-I** | LOCKED for P1/P2 (OPEN-B = B) |
| DB end / separation | DB events stop at the end of DB availability; never pooled with HF. P3/P4 are formed **per profile** and never pooled | RESOLVED; NC-6 |

---

## 4. State machine and timeline (per stock; bull shown, bear mirrors)

```text
State (read on D from 𝔉(D), re-based as-of-D):
  K3: ℓ, runs, swing points (first-occurrence), RH and last establishing session, open reaction ρ (if any)
  S9: σ; episode E; λ(E); μ(E)                                   ← λ, μ: operational P1/P2 only
  Ledger(E): K3 members (dur on swing dates; literal mag; terminating close); reactions (mag; completion close)
  Candidate M: (P_S, d_S, c), time-spent flag, price-spent flag, matched?, s_T(M), s_P(M)
  Profile: DB | HF (from S_HF)
```

| Phase | What happens | Locks |
|---|---|---|
| **A. UP line** | Update RH. A session with H > RH (strict) is an establishing session e (the up-switch close establishes the first RH). If e⁺ is LL, ρ opens with Top = H_e; an outside-day LL session continues ρ normally (it raises RH for later reactions only). A 2nd LL session is ρ's 2nd session; a 3rd consecutive LL makes the run a K3 switch (ρ discarded). On the first non-LL close, ρ completes; if a BULL E is open it enters Ledger(E) | OPEN-2.x; RQ-6/7; OPEN-D/E; RQ-1 |
| **B. Down-switch close c** | X⁺ confirmed; S9 recomputed. On a change, E closes (ledger, λ, μ discarded) and a new E may open at c. If S9_c = BULL, M is a candidate member (SC-3 even when d_S < a). 𝒰_T and 𝒰_P fixed from members completed ≤ d_S; R_T on K3 swing dates; R_P = combined maximum of literal magnitudes. M is **matched** iff 𝒰_T ≠ ∅; s_T(M) = s_P(M) = 0 initially | R-1; OPEN-3b; SC-3; RQ-1/2/5/8; OPEN-A; RQ-3 |
| **C. Active session D ∈ (c, u]** | **P1 (time, operational):** ¬λ ∧ 𝒰_T ≠ ∅ ∧ el > R_T (∧ HF: D ≥ S_HF, not time-spent) → DB: event at D; HF with G(D): event at the first genuine bar; HF without G(D): no event. Each sets λ := TRUE. **P2 (price, operational):** HF with ¬G(D): skipped (μ unchanged). Otherwise if ¬μ ∧ 𝒰_P ≠ ∅ ∧ run > R_P (∧ HF: not price-spent) → flag (HF: the genuine bar; DB: D's close); μ := TRUE. Recorded whether or not M is matched. **P3/P4 (contrast, matched M only):** if TC_M(D), s_T(M) := 1; if PC_M(τ) at an observable τ on D, s_P(M) := 1. **λ and μ are not read.** Treatment of ¬G(D) and of spent legs / S_HF for P3/P4: OPEN-I. New lows extend run; no clock reset; no termination on a new high | OD-7/8/9; OPEN-4.x; RQ-3/4/8/9/11; OPEN-B/C; **OPEN-H = B; OPEN-F** |
| **D. Up-switch close u** | M active on u, ends after it; s_T(M), s_P(M) final. If E continues, M enters the ledger: dur = cal(d_l) − cal(d_h); mag = literal minimum over (d_h, u] | OPEN-4.3; RQ-8; OPEN-A |
| **E. Latches** | λ = TRUE stops GF-10 events (P1) in E. μ = TRUE stops recorded price flags (P2) in E. They are independent. **Neither affects P3 or P4** | OD-4/6; RQ-4; RQ-11; **OPEN-H = B; OPEN-F** |
| **F. S9 reset** | E closes; ledger, λ and μ discarded; new E with an empty ledger and λ = μ = FALSE; SC-3 joins; RQ-1 exclusion. P3/P4 are per-candidate and carry no episode state | OD-5; SC-3; RQ-1 |
| **G. HF substrate start S_HF** | For every open episode: λ := FALSE, μ := FALSE. Each active candidate is checked per leg on EOD-era sessions: a time crossing before S_HF → time-spent; an EOD price crossing before S_HF → price-spent. Spent legs emit nothing into P1/P2 and set no latch; unspent legs and later candidates proceed normally. **P3/P4 for candidates active across S_HF: OPEN-I** | RQ-10 = B; OPEN-G = A; OPEN-B = B; X-2 = A |
| **H. Formal contrast** | Over matched candidates, per profile (HF and DB never pooled): **P3** = s_T(M), from TC_M, independent of λ; **P4** = s_P(M), from PC_M, independent of μ. T(time) − T(price) is computed from P3/P4 **only**, never from P1 or P2. Statistic and weekly mapping: imported G-4 / OPEN-11 | RQ-3 = C; R-10; **OPEN-F (CONF-1 resolved); OPEN-H = B**; X-2; G-4 |

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
  M's P3/P4 scores: OPEN-I(b)

HF no-bar session (RQ-11 = D, OPEN-C = A):
  D with ¬G(D): time crossing → no event, λ := TRUE; price: not evaluated, μ unchanged
  D⁺ with G: LowHist now includes L_D (EOD) → a price flag may occur at D⁺'s first genuine bar (NC-11)
  M's P3 score / instant for a crossing first holding on D: OPEN-I(a)

Two matched candidates in one episode (OPEN-H = B, OPEN-F):
  M₁: TC holds → P1 event, λ := TRUE; s_T(M₁) = 1
  M₁: PC holds → P2 flag, μ := TRUE; s_P(M₁) = 1
  M₂ (later, matched): TC holds → no P1 event (λ TRUE); s_T(M₂) = 1
  M₂: PC holds → no P2 flag (μ TRUE); s_P(M₂) = 1
  Contrast sees both candidates on both legs
```

---

## 5. OPEN items

### 5.1 Resolved in v0.5 (kept for the record)

| Item | v0.4 status | v0.5 resolution |
|---|---|---|
| CONF-1 | Confirmation requested: OPEN-F letter "A" vs its wording | **RESOLVED.** Wording authoritative. The letter is non-authoritative where it conflicts. The wording corresponds in substance to v0.3 option (c) |
| OPEN-H | OPEN: per-candidate scores and latch symmetry | **LOCKED = B** (§3.7, §4 H). Sub-question (i) is answered by derivation from the ruling's wording (§3.7). Sub-question (ii) is answered by the ruling: candidates after λ is set keep their candidate-level time score |

### 5.2 OPEN-I — HF observability and substrate-start rules inside the candidate-level contrast (surfaced v0.5)

| Field | Entry |
|---|---|
| Exact issue | OPEN-H = B removes **λ** from the contrast time input, and OPEN-F removes **μ** from the contrast price input. Neither ruling says whether the contrast also drops the **other** suppression rules, which are defined for the operational populations and are **not symmetric between the legs**. **(a) Observability, G(D):** TC_M(D) (§3.4) is date-level with no G(D) term, so read literally, s_T(M) = 1 when the time condition first holds on a no-bar HF session. PC_M(τ) has OPEN-C built into its definition ("HF only when G"), so the price leg cannot score on a no-bar session. On such a crossing, RQ-11 = D gives P1 no event, and no HF crossing instant exists for P3. **(b) Substrate start / spent legs (OPEN-B = B):** a candidate active across S_HF whose time (or price) condition first held on an EOD-era session is time-spent (or price-spent) for P1/P2. It is unstated whether that candidate enters the HF contrast, the DB contrast or neither, and with which leg scores. Its legs can first hold in different eras (cf. NC-12: a candidate can be time-spent but price-live) |
| Why it matters | (a) replaces the latch asymmetry that OPEN-H = B removed with an **observability asymmetry** between P3 and P4. On HF no-bar sessions it moves T(time) − T(price) in one direction by construction, not by content, which is the defect class OPEN-H was raised to remove. It also fixes whether a P3 crossing has an instant, which the imported OPEN-6/11/12 need. (b) sets which candidates, and which leg scores, belong to each profile's contrast. This bears on HF/DB non-pooling (C-2, X-2) and on DB-era observations never becoming HF observations (X-2, OD-7) |
| Choices (a) | (a-i) Contrast time score is date-level as written: s_T = 1 on a no-bar crossing; instant undefined or = the session. (a-ii) Apply the observability rule symmetrically: the P3 time condition counts only at an observable instant (a genuine 1m bar), so a no-bar crossing is observed at the next genuine bar in A(M), if any. This mirrors the price leg's NC-11 behaviour; TC_M is monotone, so it still holds there. (a-iii) Exclude from the HF contrast any matched candidate whose time **or** price condition first holds on a no-bar session. (a-iv) Other |
| Choices (b) | (b-i) Inherit OPEN-B = B: a spent leg scores 0 in the HF contrast (the candidate stays matched). (b-ii) Exclude candidates active across S_HF from both profiles' contrasts. (b-iii) Assign the candidate to the profile in force at its confirmation close c, scoring each leg by that profile's rules over A(M). (b-iv) Assign each leg's score to the profile in which its condition first becomes observable, and admit the candidate to a profile's contrast only when both legs are scored in that profile. (b-v) Other |
| Dependencies | OPEN-H = B, OPEN-F (created by them). Interacts with OPEN-C = A, RQ-11 = D, OPEN-B = B, RQ-10 = B, OPEN-G = A, X-2 = A, OD-7. Coupled to imported G-4, OPEN-6, OPEN-11, OPEN-12. (a) and (b) are independent of each other |
| Provenance | [NES]. No Gann source bears on it. [GS] p. 12 fixes only the time-over-price ranking. Any answer is [LOD] |
| Classification | **Definitional** (it sets the membership and values of P3/P4). Not implementation-level. It is a gap created by OPEN-H = B and OPEN-F, not a reopening; every lock it touches stays as ruled for P1/P2 |
| Scope | Affects **only** the formal contrast (P3/P4). P1 (the GF-10 event population, the primary score) and P2 are fully defined without it |

### 5.3 Imported, open elsewhere (not re-analysed)

- **Gaps:** G-4 (contrast p), G-5, G-6, G-7 (also needed for RQ-9 = x re-basing), G-8, G-9.
- **Preconditions:** P-1 … P-5, including the R-13 external CA list (P-2).
- **Draft items:** OPEN-6 (timestamp label), OPEN-11 (weekly score mapping, now including how the
  P3/P4 candidate indicators map to s_T(i, w), s_P(i, w)), OPEN-12 (outcome window).

---

## 6. Checks

| # | Item | v0.5 verdict |
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
| 6.10 | Matched contrast | **Latch treatment RESOLVED:** P3 independent of λ (OPEN-H = B); P4 independent of μ (OPEN-F; CONF-1 resolved). Four populations distinct (§3.7). **Observability and S_HF inside P3/P4: OPEN-I** |

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
| NC-11 | OPEN-C = A with RQ-9: a price crossing that occurred on a no-bar HF session can surface as a flag on the next session with genuine bars (via its EOD low in history) if the move is still active and μ is FALSE. This is the first HF-observable instant (OD-7), not a same-session flag |
| NC-12 | OPEN-B = B makes a candidate's spent status per leg: a candidate can be time-spent but price-live, or the reverse |
| NC-13 | OPEN-H = B: in an episode with several matched candidates, P3 can hold more time crossings than P1 holds events. Every P1 event comes from a matched candidate (the event requires 𝒰_T ≠ ∅) with s_T = 1 at the same D*_M (derived). The GF-10 event count and the contrast's time count are **different objects** and must never be substituted for each other |
| NC-14 | OPEN-F: likewise, P2 flags and P4 scores are different objects. P2 includes unmatched candidates, which P4 excludes, and P4 includes post-μ candidates, which P2 excludes |

---

## 7. Contradiction audit (re-run for v0.5)

### 7.1 Result

**v0.5: PASS, with one new definitional OPEN (OPEN-I).**
- **51 locked decisions** audited: the 50 of v0.4 (the v0.3 set of 43 plus OPEN-A … OPEN-G) plus
  **OPEN-H = B**. CONF-1's resolution confirms OPEN-F's wording. It is not a new lock.
- No contradiction among the 51 locks. No contradiction between §1.2, §2, §3, §4 and §9.
- The v0.4 contradiction candidate, an OPEN-F letter "A" = v0.3 (a) alongside a μ-independent
  contrast, is **removed**: the document no longer maps OPEN-F to v0.3 (a) anywhere.
- **No mechanical ambiguity remains from the v0.4 OPEN-H / CONF-1 pair.**
- **Newly surfaced:** **OPEN-I** (§5.2), created by OPEN-H = B and OPEN-F. It is a gap, not a
  contradiction. It is confined to P3/P4 and is not resolved here.

### 7.2 Checks carried from v0.4 (re-verified)

| ID | Check | Result |
|---|---|---|
| B-1 | OPEN-A = A vs RQ-8 = A (literal price for references) | Consistent: RQ-8 governs price only; time keeps the K3 dates (NC-10) |
| B-2 | OPEN-A = A vs OPEN-4.4 = A (current time endpoint = observation date) | Consistent: different objects (current vs reference) |
| B-3 | OPEN-B = B vs RQ-10 = B | Consistent: the latch stays FALSE; only the spent candidate's leg is suppressed in P1/P2 |
| B-4 | OPEN-B = B vs X-2 = A and OD-7 | Consistent for P1/P2: no DB-era crossing becomes an HF event. For P3/P4: OPEN-I(b) |
| B-5 | OPEN-B = B vs C-7 (move reset) | Consistent: later candidates in the episode are unaffected |
| B-6 | OPEN-C = A vs RQ-11 = D | Consistent for P1/P2: the time leg latches on no-bar sessions; the price leg is not evaluated (legs independent, RQ-4). For P3: OPEN-I(a) |
| B-7 | OPEN-C = A vs RQ-9 = A+x and OD-7 | Consistent: the session's EOD low enters as history; the earliest HF observation is the next genuine bar (NC-11) |
| B-8 | OPEN-D = A vs OPEN-4.5 = A (first occurrence) | Consistent (an equal later high does not take over the role) |
| B-9 | OPEN-D = A vs RQ-7 = B | Consistent: it defines "established" |
| B-10 | OPEN-E = A vs RQ-6 = A | Consistent: Top stays H_e; outside-day highs are excluded from Top but raise RH |
| B-11 | OPEN-E = A vs OPEN-2.1 = A / OPEN-2.3 = B | Consistent: the 2-session bound and the 3rd-LL → K3 rule are unchanged |
| B-12 | OPEN-E = A vs OPEN-D = A | Consistent: an outside-day session inside ρ raises RH for later anchors only |
| B-13 | OPEN-F (wording) vs RQ-3 = C / RQ-4 = A | Consistent: P2 is still recorded with μ; only P4 ignores μ |
| B-14 | OPEN-F (wording) vs OD-4 (time λ) | v0.4 gap OPEN-H is now **closed by OPEN-H = B**: P3 ignores λ too, so the contrast's latch treatment is symmetric |
| B-15R | OPEN-F letter "A" vs v0.3 option (a) | **RESOLVED (CONF-1).** Wording authoritative; substance = v0.3 (c). No remaining text maps OPEN-F to v0.3 (a) |
| B-16 | OPEN-G = A vs OPEN-B = B | Consistent: μ FALSE at start; the price-spent candidate is suppressed individually |
| B-17 | OPEN-G = A vs RQ-4 = A | Consistent |

### 7.3 Checks added for v0.5

| ID | Check | Result |
|---|---|---|
| V-1 | OPEN-H = B vs OD-4 (first exceedance per episode) | Consistent: OD-4 governs P1, which is unchanged. OPEN-H = B scopes the λ-free evaluation to the contrast only |
| V-2 | OPEN-H = B vs C-7 (move reset + episode latch) | Consistent: C-7's move-level reset is what makes each candidate a unit for P3. Its episode latch applies to P1 |
| V-3 | OPEN-H = B vs RQ-10 = B / RQ-11 = D | No contradiction: both are λ rules for P1. Whether their **non-latch** parts (no-bar observability, S_HF) carry to P3 is **OPEN-I** |
| V-4 | OPEN-H = B vs RQ-3 = C (matched contrast) | Consistent: P3 is defined only over matched candidates, the same set as P4 |
| V-5 | OPEN-F wording (CONF-1) vs RQ-4 = A | Consistent: μ remains the independent first-per-episode latch of P2 |
| V-6 | OPEN-H = B vs OPEN-F | Consistent and symmetric: both legs are latch-free, candidate-level conditions |
| V-7 | Candidate-level scoring vs operational latches | Consistent: P1 ⊂ time-scored candidates and P2-from-matched ⊂ price-scored candidates (NC-13/14). The contrast is computed from P3/P4 only (§4 H). No latch is read by P3/P4 |
| V-8 | OPEN-B = B vs OPEN-H = B / OPEN-F | Gap, not a contradiction: spent status is defined for P1/P2 only → **OPEN-I(b)** |
| V-9 | OPEN-C = A vs OPEN-H = B | Gap: PC_M has G(D) built in; TC_M does not → observability asymmetry in P3/P4 → **OPEN-I(a)** |
| V-10 | OPEN-G = A vs OPEN-F | Consistent: OPEN-G sets μ for P2; P4 does not read μ |
| V-11 | HF/DB separation (C-2, X-1, X-2, NC-6) | Consistent: P1–P4 are all formed per profile; the contrast is never pooled. Profile assignment of candidates straddling S_HF → OPEN-I(b) |
| V-12 | D−1 information boundary (C-3, §1.2-6) | Consistent: TC_M and PC_M read daily-derived facts as of D⁻ (R_T, R_P, ledger, K3, S9) plus same-session 1m (HF) or D's own EOD bar (DB), exactly as in P1/P2. OPEN-H = B adds no information |
| V-13 | First-observable-crossing rule (OD-7) | Consistent: the P3/P4 crossing instant, where defined, is the first observable instant (§3.7). The case where no HF observable instant exists is **OPEN-I(a)** |
| V-14 | Current/reference alignment (§6.3) | Consistent: P3/P4 use the same TC_M / PC_M, R_T, R_P, 𝒰_T, 𝒰_P as P1/P2; no new reference object |
| V-15 | Reaction / K3 separation (OD-2, OPEN-2.4 = A) | Consistent: reactions stay out of R_T (so out of P3) and in bull R_P (so in P4), as in P1/P2 |
| V-16 | Literal price windows vs K3 time dates (OPEN-A = A, RQ-8 = A) | Consistent: P3 inherits dur on K3 swing dates, P4 inherits literal-window magnitudes. The dual endpoint is unchanged (NC-10) |
| V-17 | RQ-3 = C: P2 recorded regardless of 𝒰_T | Consistent: P2 still includes unmatched candidates; P4 excludes them (NC-14) |
| V-18 | Matched ⇔ 𝒰_T ≠ ∅ vs NC-8 | Consistent: the episode's first candidate is never matched → absent from P3/P4 |
| V-19 | §2 attribution | No [LOD] is attributed to Gann. OPEN-F, CONF-1, OPEN-H, OPEN-I, latches and candidate-level scoring appear only in the LOCKED OPERATOR / [NES] columns; the [GS] cell for p. 12 is limited to the ranking — PASS |
| V-20 | §9 ↔ sections | Every ledger row mapped. OPEN-H = B is applied in §1.1, §1.2-21/22/24, §2, §3.7, §3.8 and §4 C/E/H. OPEN-I is in §5.2 and §10 — PASS |
| V-21 | Internal text scan for the retired mapping | No sentence maps OPEN-F to v0.3 (a). No sentence lists CONF-1 or OPEN-H as open — PASS |

### 7.4 Lock-by-lock register (51)

Each lock was re-read against §1–§4 as amended. **Unaffected** means v0.5 does not change the text
that applies it. **Scoped** means its text now says it governs the operational populations P1/P2.
**Gap** means OPEN-I, for P3/P4 only.

| Group | Locks | Result |
|---|---|---|
| OD | OD-1, OD-2, OD-3, OD-5, OD-6, OD-8, OD-9, OD-10 | Unaffected |
| OD | OD-4 | Scoped to P1 (V-1) |
| OD | OD-7 | Unaffected; applies to P3/P4 instants; no-instant case → OPEN-I(a) |
| C | C-1/C-2/C-3 (one ledger row), C-4, C-5, C-6 | Unaffected; C-2 extends to P3/P4 (V-11) |
| C | C-7 | Consistent (V-2) |
| X | X-1 = A | Unaffected |
| X | X-2 = A | Consistent; straddling candidates in P3/P4 → OPEN-I(b) |
| OPEN-3/4 | OPEN-3b, OPEN-4.1, 4.2, 4.3, 4.4, 4.5 | Unaffected |
| SC | SC-3 = A | Unaffected |
| OPEN-2 | OPEN-2.1, 2.2, 2.3, 2.4, 2.5 | Unaffected (V-15) |
| OPEN-1 | OPEN-1 = A | Unaffected (NC-8) |
| RQ | RQ-1, RQ-2, RQ-5, RQ-6, RQ-7, RQ-8, RQ-9 | Unaffected (V-12, V-14, V-16) |
| RQ | RQ-3 = C | Consistent (V-4, V-17) |
| RQ | RQ-4 = A | Scoped to P2 (V-5) |
| RQ | RQ-10 = B, RQ-11 = D | Scoped to P1; non-latch parts in P3 → OPEN-I (V-3) |
| OPEN-A…G | OPEN-A, OPEN-D, OPEN-E | Unaffected |
| OPEN-A…G | OPEN-B = B | Scoped to P1/P2; OPEN-I(b) (V-8) |
| OPEN-A…G | OPEN-C = A | Unaffected for P2; OPEN-I(a) (V-9) |
| OPEN-A…G | OPEN-F | Confirmed by wording (CONF-1; B-15R) |
| OPEN-A…G | OPEN-G = A | Scoped to P2 (V-10) |
| New | OPEN-H = B | Consistent with all of the above (V-1 … V-7) |

Count: 43 (v0.3) + 7 (OPEN-A … OPEN-G) + 1 (OPEN-H) = **51**.

---

## 8. Future work — what empirical testing must NOT decide

**Definitional (before any data read; never from results):**
- **OPEN-I.**
- Every lock in §9.
- Any later threshold, window, adjacency or source rule.

No choice may be justified by event counts, coverage, "too few/many events", IC, Sharpe, surrogate p,
contrast p, size-check outcome or any O-R10 association. This includes counts of P3/P4 candidates
under the alternative OPEN-I choices.

**Empirical (pre-registered read, after freeze only):**
- GF-10 events (P1) vs O-R10 beyond the surrogate null (R-14).
- T(time) vs T(price) on matched candidates, from P3/P4 (R-10, RQ-3 = C, G-4).
- Descriptive statistics: reported, never used to revise definitions.

**Implementation (code review and deterministic tests, not results):**
- K3/S9 (memo §5); establishing-session strictness; outside-day continuation.
- D−1 freeze; causal prefix invariance; byte-identical replay.
- As-of-D re-basing and 1m normalization (ratio test).
- G(D) via `is_synthetic = FALSE`, `bar_labeling.py`, GAP sessions and `SPECIAL_SESSIONS`.
- Independent λ/μ; per-leg spent flags at S_HF.
- **P3/P4 computed without reading λ or μ; P1/P2 and P3/P4 kept as separate outputs** (a test must
  show that toggling λ/μ state cannot change s_T or s_P).
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
| RQ-3 = C | Price flags independent (P2); formal contrast on matched candidates (P3/P4) | LOCKED | §3.7; §4 H |
| RQ-4 = A | Independent first-per-episode price latch (P2) | LOCKED | §3.8 |
| RQ-5 = A | References completed ≤ d_S | LOCKED | §3.4; §3.7 |
| RQ-6 = A | Reaction top excludes reaction-session highs | LOCKED | §3.6 |
| RQ-7 = B | Reaction begins immediately after the establishing session | LOCKED | §3.6 |
| RQ-8 = A | Literal running-price window, current and reference | LOCKED | §3.5 |
| RQ-9 = A+x | EOD history; genuine 1m on D; as-of-D normalization | LOCKED | §3.1; §3.5 |
| RQ-10 = B | HF time latch FALSE at substrate start | LOCKED | §3.8; §4 G |
| RQ-11 = D | HF no-bar time crossing: no event, latch set (P1) | LOCKED | §3.8; §4 C |
| OPEN-A = A | K3 swing dates for time; literal extreme for price | LOCKED | §1.2-14/16; §3.4; §3.5 |
| OPEN-B = B | Pre-HF-crossed candidate spent (per leg); no HF event/flag; no latch | LOCKED | §1.2-23; §3.8; §4 G |
| OPEN-C = A | No HF price evaluation without a genuine 1m bar | LOCKED | §1.2-16/22; §3.5; §3.8 |
| OPEN-D = A | Only a strictly new extreme establishes the anchor | LOCKED | §1.2-15; §3.6 |
| OPEN-E = A | Outside-day reaction continues normally | LOCKED | §1.2-15; §3.6 |
| **OPEN-F** | Matched contrast price input independent of the episode price latch μ (wording authoritative; substance = v0.3 (c)) | **LOCKED (wording; CONF-1 resolved)** | §1.2-22/24; §3.7; §3.8; §4 H |
| OPEN-G = A | HF price latch starts FALSE | LOCKED | §1.2-22/23; §3.8 |
| **OPEN-H = B** | For the formal contrast only, the time input is the underlying condition TC_M(D) per matched candidate, independent of λ; operational P1 unchanged | **LOCKED (v0.5)** | §1.1; §1.2-21/24; §2; §3.7; §3.8; §4 C/E/H |
| CONF-1 | OPEN-F letter vs wording | **RESOLVED (v0.5): wording authoritative** | §5.1; §7.2 B-15R |
| OPEN-I | HF observability (G(D)) and S_HF / spent-leg treatment inside P3/P4 | **OPEN (surfaced v0.5), definitional** | §5.2 |

## 10. Remaining decision order

| Step | Item | Depends on |
|---|---|---|
| 1 | OPEN-I (a) observability and (b) S_HF / spent legs inside P3/P4, independent of each other | OPEN-H = B, OPEN-F (locked) |

CONF-1 and OPEN-H are closed.

**Readiness by population:**
- **P1 (GF-10 event population, the primary score) and P2 (price flags)** are defined at the mechanical
  level. They do not depend on OPEN-I.
- **P3/P4 (the R-10 specificity contrast)** are defined except for OPEN-I.

After OPEN-I, the remaining work is the imported items: OPEN-6, OPEN-11 (including the P3/P4 →
weekly-score mapping), OPEN-12, G-4 … G-9 and P-1 … P-5. The freeze document comes after those.
v0.5 is a consolidated decision record, not a freeze.

---

**NO CODE. NO BACKTEST. NO EMPIRICAL TESTING. NO MARKET OUTCOMES READ. NO LOCKED DECISION REOPENED.
NOT FROZEN. NOT AN IMPLEMENTATION SPECIFICATION.**
