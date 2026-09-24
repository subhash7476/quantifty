# GF-10 Mechanical Decision Record — v0.2

**Date:** 2026-09-17

**Status: CONSOLIDATED DECISION RECORD — NOT AN IMPLEMENTATION SPECIFICATION, NOT A FREEZE.**
- No code, backtest, empirical test, optimization or performance analysis was performed.
- No market data or outcome was read. Nothing is frozen or hashed.
- **No locked decision is reopened.**

**Supersedes:** v0.1 (`GF10_MECHANICAL_DECISION_RECORD_v0.1_2026-09-17.md`, commit `59e25da`), which is
kept unchanged.

> **⚠ Decision provenance notice.** This version incorporates the RQ decisions that are **recorded
> in this conversation**:
>
> | Decision | Where recorded |
> |---|---|
> | RQ-8 = A (literal running-price window, applied identically to current and reference moves) | Operator update instruction |
> | RQ-9 = A + x | Operator update instruction |
> | RQ-10 = B | Operator update instruction |
> | RQ-11 = D | Operator update instruction |
>
> **Decisions on RQ-1 … RQ-7 do not appear in this conversation record.** They are therefore
> **not incorporated** and remain **OPEN — OPERATOR DECISION NOT RECORDED** (§5, §9). If they were
> ruled elsewhere, they must be supplied verbatim and entered in v0.3. They are not inferred here.

**Construct label:** GF-10 = **GANN-FAITHFUL SOURCE CONCEPT + EXPLICIT OPERATOR/RESEARCH CONVENTIONS.**
It is not "Gann's exact rule".

**Provenance markers:**

| Marker | Meaning |
|---|---|
| **[GS]** | GANN SOURCE: verified wording or arithmetic; register ID given |
| **[LOD]** | LOCKED OPERATOR / RESEARCH DECISION |
| **[NES]** | NOT ESTABLISHED BY SOURCE; must never be attributed to Gann |

A [GS] marker on part of a rule does not extend to the rest of it.

---

## 0. Change log from v0.1

| # | Change | Sections |
|---|---|---|
| CL-1 | **RQ-8 = A incorporated; v0.1 inconsistency corrected.** Reference price magnitude is no longer the K3 endpoint difference h′ − l′. It uses the **same literal running-price window** as the current move: all lows (bull) or highs (bear) **strictly after** the starting-extreme session, through the move's last active session | §1.2 row 16; §3.5; §4 phases C–D; §6 |
| CL-2 | **RQ-9 = A + x incorporated.** Historical sessions (before the observation session D) use authoritative EOD extremes. The observation session D uses genuine 1m extremes (`is_synthetic = FALSE`) in HF. Every price used on D, including historical EOD values, P_S and reference magnitudes, is expressed on the R-13 as-of-D basis; 1m prices are normalized to that basis before any comparison | §1.2 rows 1, 16; §3.1; §3.5; §4 phase C |
| CL-3 | **RQ-10 = B incorporated.** At the HF substrate start, the latch of every open episode is FALSE. Episode ledgers still use EOD history (X-2 = A) | §3.8; §4 phase G; §5 |
| CL-4 | **RQ-11 = D incorporated.** On an HF session with no genuine 1m bar for the stock, a date-determined time crossing emits **no HF event**, but **sets the episode latch** | §3.8; §4 phases C, E |
| CL-5 | Wording fix: v0.1 §3.4 said same-type references complete "at or before c (the previous opposite line ended at c)". Corrected: a same-type reference K3 move completes at its terminating switch close u′, and **u′ ≤ d_S** | §3.4 |
| CL-6 | Added a **decision ledger** (§9) and a **contradiction audit** (§7) | §7, §9 |
| CL-7 | **New OPEN items surfaced by the audit** (created by combining locks, not reopening them): **OPEN-A** (reference-duration endpoint vs literal price window), **OPEN-B** (an HF candidate already crossed before the substrate start, under RQ-10 = B, X-2 = A and OD-7), **OPEN-C** (price leg on a no-bar HF session under RQ-11 = D) | §5 |
| CL-8 | New disclosure notes NC-5 … NC-7 | §6.10 |
| CL-9 | §6 check table updated (6.4 now RESOLVED) | §6 |

---

## 1. Locked mechanical model (end-to-end)

### 1.1 Causal chain

```text
Authoritative EOD daily bars, R-13 as-of-t basis
  └─► K3 line state and confirmed swing points (R-1)
        └─► confirmed S9; changes only at a K3 switch close (OPEN-3b = A)
              └─► D−1 freeze: every daily-derived fact used on session D is as of the D⁻ close,
                  re-expressed on the as-of-D basis (RQ-9 x)
                    └─► current K3 move (bull: K3 decline from its first-occurrence swing high;
                        bear: K3 rally from its first-occurrence swing low)
                          └─► reference ledger = completed previous same-type moves in the current S9 episode (OPEN-1 = A)
                                ├─► R_T = greatest reference duration (K3 moves only; OPEN-2.4 = A)
                                └─► R_P = price reference: K3 declines ∪ qualifying 1/2-day reactions (bull);
                                    K3 rallies (bear); form OPEN (RQ-2); every magnitude on the literal window (RQ-8 = A)
                                      └─► first objectively observable strict crossing on D (OD-7, OD-9)
                                          HF: time leg at the first genuine 1m bar of D; price leg on EOD history + normalized 1m on D (RQ-9 = A+x)
                                          DB: session D on EOD
                                            ├─► time crossing ⇒ GF-10 EVENT (R-5 / R-10)
                                            │     HF session with no genuine bar ⇒ no event, latch set (RQ-11 = D)
                                            └─► price crossing ⇒ price-overbalance flag (contrast only; R-10)
                                                  └─► episode latch until S9 changes (OD-4/5/6, C-7);
                                                      HF latch FALSE at substrate start (RQ-10 = B)
```

### 1.2 Stage table with provenance

| # | Stage | Locked content | Provenance |
|---|---|---|---|
| 1 | Data | **HF:** genuine 1m observations on the observation session for event detection. Authoritative EOD daily data for K3/S9 and every historical session, which may extend before the 1m substrate (X-1 = A; RQ-9 = A). **DB:** EOD only, where 1m is unavailable. **HF and DB event/result populations are never pooled.** HF may use EOD history as causal lookback; DB-era observations never become HF events (X-2 = A) | [LOD]; [NES] |
| 2 | Price basis | Every price compared on session D is on the R-13 ratio-adjusted **as-of-D** basis. HF 1m prices on D are normalized to that basis first (RQ-9 = x) | [LOD] (R-13, RQ-9); [NES] |
| 3 | K3 | Strict 3-Day Chart with memo §5 rows 1–13: literal down-switch = 3 consecutive lower lows; up-switch = 3 consecutive higher highs **and** higher lows; strict inequalities; day-over-day; outside/inside-day rules; 2-day exception not applied; usable from the confirming close | Construction [GS] Δ2-10 (p. 63); mechanization [LOD] (R-1, labelled approximation); record departures [GS] Δ3-02 |
| 4 | S9 | BULL iff the last two confirmed K3 tops **and** the last two confirmed bottoms are strictly rising; BEAR iff both strictly falling; else NONE. Changes only at a K3 switch close | Rule 9 [GS] (p. 12); mechanization and use in Rule 8 [LOD] (OPEN-3b = A); S9 as a Rule 8 precondition [NES] |
| 5 | Bear condition | S9 BEAR | [LOD] (OD-3). Gann's wording "declining for a long period of Time" [GS] Δ2-01; S9 bear as that condition [NES] |
| 6 | D−1 freeze | For session D, all daily-derived K3/S9, move, ledger and reaction facts are as of the D⁻ close | [LOD]; [NES] |
| 7 | Current move | Bull: K3 decline from its K3 swing high. Bear: K3 rally from its K3 swing low. Reactions never create a current move | Measuring from a high/low [GS] (p. 11; p. 63 example); K3 as the move object [LOD] (C-4, OPEN-4.1) |
| 8 | Starting-extreme ties | First occurrence of an equal extreme | [LOD] (OPEN-4.5); [NES] |
| 9 | Time clock | From the starting-extreme **date** to the **observation session date**, in integer calendar days (start date excluded). Not stopped at the running price extreme | Calendar-day differences [GS] Δ3-06, p. 61; applied to Rule 8 and to this endpoint [LOD] (OPEN-4.2, OPEN-4.4) |
| 10 | Termination | At the confirmed opposite K3 switch close. No intraday price-break termination | [LOD] (OPEN-4.3) |
| 11 | Episode | Maximal run of closes with constant S9 ∈ {BULL, BEAR}. Resets on reversal **or** cessation | [LOD] (OD-5); [NES] |
| 12 | SC-3 | A move **confirmed** at the episode-creating switch close belongs to that episode; its start may predate the episode; it is not truncated | [LOD] (SC-3 = A) |
| 13 | Reference ledger | Completed previous same-type moves within the current episode. No carryover; no fixed N, calendar lookback or entire history. The first qualifying move in an episode has no reference and cannot trigger | "a previous" [GS] Δ2-01/02; greatest time period [GS] Δ2-04 (separate statement); episode scope and greatest [LOD] (OD-1, OPEN-1 = A); [NES]. Boundary: RQ-1 OPEN; precedence: RQ-5 OPEN |
| 14 | Time reference | Greatest duration among completed same-type **K3** moves in the ledger. Reactions excluded | "decline" in the bull time clause [GS] Δ2-01; exclusion [LOD] (OPEN-2.4 = A). Duration endpoint: OPEN-A |
| 15 | Reaction (bull only) | A 1- or 2-session run of consecutive strict lower lows inside a K3 UP line. A 3rd consecutive lower low is a K3 down-switch. Bounded to that structure. Starts from the running extreme of the K3 leg in progress. "Near an extreme" is structural, not numeric | "decline or reaction" [GS] Δ2-02; near-extreme 2-day moves [GS] Δ2-10, Δ3-01 (discretionary); bound, anchor, structural reading, reaction ≠ K3 [LOD] (OD-2, OPEN-2.1/2.2/2.3/2.5); [NES]. Top definition RQ-6 OPEN; adjacency RQ-7 OPEN |
| 16 | Magnitudes | **Current move:** bull run = P_S − lowest low strictly after the start session through the observation instant; bear mirror. **Reference move:** the same literal window, from strictly after its start session through its last active session (terminating close). **Reaction:** Top_ρ − low of its last session. **HF:** historical sessions use EOD extremes; the observation session uses normalized genuine 1m extremes. **DB:** EOD throughout | High/low measurement [GS] (p. 63, strong inference); running form [LOD] (OD-8); literal window for both [LOD] (RQ-8 = A); data source and basis [LOD] (RQ-9 = A+x); [NES] |
| 17 | Price comparator | Bull: completed K3 declines ∪ qualifying reactions. Bear: completed K3 rallies | [GS] Δ2-02; [LOD] (C-4, OPEN-2.4). **Form: RQ-2 OPEN** |
| 18 | Triggers | Strict `>`; equality does not trigger | "exceeds"/"greater" [GS]; equality [LOD] (OD-9) |
| 19 | Event timing | First objectively observable crossing; not deferred to week-end, move completion or outcome | "is taking place"/"has started" [GS] (strong inference); [LOD] (OD-7, C-6) |
| 20 | GF-10 event | The time crossing. **HF:** first genuine 1m bar of the crossing session. **No genuine bar that session → no HF event, latch set.** **DB:** crossing session | Time outranks price [GS] p. 12; roles [LOD] (R-5, R-10); no-bar rule [LOD] (RQ-11 = D); [NES] |
| 21 | Latch | One GF-10 event per stock per episode. Set by an emitted event **or** by an RQ-11 = D no-bar crossing. Reset only when a new episode opens. **HF: FALSE for every episode open at the substrate start** | "the first time" (bear clauses only) [GS] Δ2-01/02; [LOD] (OD-4, OD-6, C-7, RQ-10 = B, RQ-11 = D); [NES] |
| 22 | Move reset | Each qualifying K3 move is an independent candidate. A non-triggering candidate ends at termination; others may arise in the same episode | [LOD] (C-7) |
| 23 | Price-leg eligibility and latch | RQ-3 OPEN, RQ-4 OPEN; no-bar sessions: OPEN-C | — |
| 24 | Outcome (context) | O-R10 per R-2 / G-2(b) | Rule 10 [GS] Δ2-11 (a separate rule); use as Rule 8's outcome [NES]; [LOD] |

---

## 2. Source fact vs operator decision (summary)

| Rule | GANN SOURCE | LOCKED OPERATOR / RESEARCH | NOT ESTABLISHED BY SOURCE |
|---|---|---|---|
| Stocks as well as averages | ✔ p. 11 | — | — |
| Duration of current vs previous decline/rally | ✔ Δ2-01 | Greatest in episode (OD-1, OPEN-1) | Greatest; episode scope |
| Points of current vs previous decline or reaction (bull) / rally (bear) | ✔ Δ2-02 | Comparator form OPEN (RQ-2) | — |
| Strict exceedance | ✔ "exceeds", "greater" | Equality = no trigger (OD-9) | Equality treatment |
| "The first time" | ✔ bear clauses only | Per episode, both directions (OD-4/6) | Bull use; episode scope |
| Time more important than price | ✔ p. 12 | Time = primary event; price = contrast (R-10) | Any statistic |
| Calendar days | ✔ p. 61 (3-day moves); Δ3-06 examples | Applied to Rule 8 | Rule 8's own unit |
| Measurement from high / to low | ✔ p. 11, p. 63 (inference) | Running form (OD-8); literal window for current and reference (RQ-8 = A); first-occurrence ties (OPEN-4.5) | Running form; window; ties |
| 3-Day Chart | ✔ construction (discretionary in practice) | Strict K3 (R-1) | K3 as Rule 8's detector |
| Market state | Rule 9 | S9 bull/bear (OD-3, OPEN-3b) | S9 as a precondition; S9 bear as the bear condition |
| Episode, reset, latch, move reset | — | ✔ | ✔ |
| Reaction class | "decline or reaction"; near-extreme 2-day moves; "3-day reaction" (p. 66) | 1/2-day bound, anchor, reaction ≠ K3 | Bound; anchor |
| Reactions in time leg | "decline" only in bull time clause | Excluded (OPEN-2.4) | — |
| D−1 freeze; HF/DB; 1m; EOD history; basis normalization; substrate-start latch; no-bar rule | — | ✔ | ✔ |
| Termination at opposite K3 switch | — | ✔ (OPEN-4.3) | ✔ |
| Rule 10 outcome, horizon, pooling | Rule 10 is a separate rule | ✔ | ✔ |

---

## 3. Mathematical definitions

### 3.1 Primitives

| Symbol | Definition | Provenance |
|---|---|---|
| 𝒟; d⁻; cal(d) | NSE sessions; the previous session; calendar date | [LOD] |
| H_d^(D), L_d^(D) | Authoritative EOD high/low of session d on the R-13 as-of-D basis (d < D) | [LOD] (R-13, RQ-9 = A+x) |
| h_τ^(D), l_τ^(D) | HF only: high/low of the genuine (`is_synthetic = FALSE`) 1m bar τ on session D, normalized to the as-of-D basis | [LOD] (RQ-9 = A+x) |
| G(D) | HF only: TRUE iff session D has at least one genuine 1m bar for the stock | [LOD] (RQ-11) |
| LL(d), HH(d), HL(d) | Strict day-over-day comparisons on EOD bars | [LOD] (R-1) |
| ℓ_d ∈ {UP, DOWN, ∅} | K3 line state as of close d | [LOD] (R-1) |
| c, u | Down-switch close (3rd consecutive LL); up-switch close (3rd consecutive HH ∧ HL) | [GS] Δ2-10; [LOD] |
| X⁺ = (h, d_h, c) | h = max EOD high over the UP line ended at c; d_h = **first** session in that line with high h | [LOD] (R-1, OPEN-4.1, OPEN-4.5) |
| X⁻ = (l, d_l, u) | l = min EOD low over the DOWN line ended at u; d_l = **first** session with low l | [LOD] (R-1, OPEN-4.1/4.5 mirror; v0.1 §6.5) |
| S9_d | BULL iff the last two confirmed tops and the last two confirmed bottoms are strictly rising; BEAR iff strictly falling; else NONE. S9_d ≠ S9_{d⁻} only at a switch close | [LOD] (OPEN-3b = A) |
| 𝔉(D) | Every daily-derived quantity as of the D⁻ close | [LOD] (D−1 freeze) |

**Basis note.** A historical value used on D (P_S, reference magnitudes, EOD lows) is expressed as of
D. A corporate action between a reference's completion and D re-expresses that reference on D's basis.
Exclusion windows are imported from G-7.

### 3.2 S9 episode and membership

- E = (σ, a, b) is a maximal interval of closes [a, b) with S9 = σ ∈ {BULL, BEAR}.
- a is the switch close at which S9 became σ; b is the next change (reversal or cessation), or +∞.
- A return to σ after NONE opens a new episode. [LOD] (OD-5)
- **Membership of a move by confirmation close c:** a ≤ c < b, including c = a (SC-3 = A).
- **Membership of a move confirmed before a but completed at a: OPEN (RQ-1).**

### 3.3 Current bull decline / current bear rally

- **Bull:** M = (X⁺, c, u), with S9_c = BULL, member of E by §3.2. P_S = h, d_S = d_h. [LOD]
- **Bear:** M = (X⁻, u, c) mirror. P_S = l, d_S = d_l. [LOD]
- **Active sessions:** M is active on D iff its confirmation close ≤ D⁻ and its termination close is
  not ≤ D⁻; i.e. D ∈ (c, u] for bull. The terminating session is active. [LOD] (D−1 freeze,
  OPEN-4.3) — **RESOLVED**
- Under OPEN-3b = A, S9 cannot change strictly between c and u, so E does not end while M is active
  except at u. — **RESOLVED**

### 3.4 Time leg

| Symbol | Definition | Status |
|---|---|---|
| el_M(D) | cal(D) − cal(d_S) (integer calendar days, start excluded) | [LOD] (OPEN-4.2, OPEN-4.4); [GS] Δ3-06 arithmetic |
| dur(M′) | Bull reference decline: cal(d_l′) − cal(d_h′), using the **K3 swing-low date**; bear mirror | Carried from v0.1 (R-5 "high date to low date"; memo §7.3). **Endpoint consistency with RQ-8 = A: OPEN-A** |
| 𝒰_T(M, D) | {M′ : same-type K3 move, member of E, M′ ≠ M, terminated by D⁻, previous to M} | [LOD] (OPEN-1 = A, OPEN-2.4 = A); boundary RQ-1; precedence RQ-5 (no effect on K3 references, see below) |
| R_T(M) | max_{M′∈𝒰_T} dur(M′); undefined if 𝒰_T = ∅ (M cannot trigger) | [LOD] (OD-1, OPEN-1) |
| TC_M(D) | M active on D ∧ 𝒰_T ≠ ∅ ∧ el_M(D) > R_T | [LOD] (OD-9) |

**Constancy (RESOLVED).** A same-type K3 reference M′ in E terminates at its opposite switch close
u′. The next line is the UP line containing d_S, so **u′ ≤ d_S < c**. No same-type K3 move can
terminate while M is active (its own termination is the next opposite switch). 𝒰_T and R_T are
therefore constant over M's active sessions. RQ-5's precedence cut cannot change 𝒰_T; it affects only
reactions (§3.7).

### 3.5 Running extreme and magnitudes (RQ-8 = A, RQ-9 = A + x)

**Current bull move M, observed at instant τ on session D:**

```
LowHist_M(D)  = min{ L_d^(D) : d_S < d ≤ D⁻ }                         (EOD, as-of-D; +∞ if empty)
LowObs_M(τ)   = HF: min{ l_τ′^(D) : genuine 1m bars τ′ ≤ τ on D }      (normalized)
                DB: L_D^(D)                                              (EOD of D; observable at D's close)
run_M(τ)      = P_S^(D) − min( LowHist_M(D), LowObs_M(τ) )
```

The bear mirror uses highs: run_M(τ) = max(HighHist, HighObs) − P_S^(D).

**Completed reference K3 decline M′, used on session D:**

```
mag^(D)(M′) = h′^(D) − min{ L_d^(D) : d_h′ < d ≤ u′ }                  (literal window; EOD; as-of-D)
```

- The window runs from strictly after the start session through the move's last active session (its
  terminating close u′), the **same literal rule** as the current move. [LOD] (RQ-8 = A)
- Every lower low in (d_h′, c′), including one below the eventual K3 swing low l′, is included.
  Sessions in (d_l′, u′] cannot lower the minimum.
- Bear mirror: mag^(D)(M′) = max{ H_d^(D) : d_l′ < d ≤ c′ } − l′^(D).

**Reaction ρ (bull):** mag^(D)(ρ) = Top_ρ^(D) − L_{s_k}^(D). Top_ρ is per §3.6 (RQ-6 OPEN).

**Historical basis (RESOLVED).** Reference magnitudes and reactions are entirely historical (completed
by D⁻), so they are EOD only in both profiles. Only the current move's observation-session term uses
1m (HF).

### 3.6 Reaction (bull only)

- Inside a K3 UP line, a bull reaction ρ is a maximal run s₁ (, s₂) of consecutive LL sessions of
  length k ∈ {1, 2}, followed by a non-LL session.
- A 3rd consecutive LL makes the run a K3 down-switch, which is not a reaction. [LOD] (OPEN-2.1 = A,
  OPEN-2.3 = B)
- **Completion:** at the close of the first following non-LL session. Usable from the next session
  (D−1). — **RESOLVED**
- **Top_ρ:** running maximum of EOD highs over the K3 UP leg in progress, as of the close before s₁
  **or** through s_k. **OPEN (RQ-6).** [LOD] anchor (OPEN-2.2 = A)
- **Qualification:** structural anchor to the running leg extreme (OPEN-2.5 = B). **Adjacency OPEN
  (RQ-7).**
- **Bear "higher-high" structures:** not operative (C-4, OPEN-2.4). See NC-1.

### 3.7 Price leg

| Symbol | Definition | Status |
|---|---|---|
| 𝒰_P(M, D) bull | {completed K3 declines in E previous to M} ∪ {completed qualifying reactions in E previous to M}, completed by D⁻ | [GS] Δ2-02; [LOD] C-4. Boundary RQ-1; **precedence of reactions between d_S and c: RQ-5** |
| 𝒰_P(M, D) bear | {completed K3 rallies in E previous to M} | [GS]; [LOD] |
| R_P^(D)(M) | **OPEN (RQ-2):** greatest over the union, or another form | — |
| PC_M(τ) | M active on D ∧ 𝒰_P ≠ ∅ ∧ run_M(τ) > R_P^(D) | [LOD] (OD-8, OD-9). Evaluation scope RQ-3; latch RQ-4; no-bar sessions OPEN-C |

### 3.8 GF-10 event, latch and profile rules

| Symbol | Definition | Status |
|---|---|---|
| D*_M | min{ D : TC_M(D) } over M's active sessions | [LOD] (OD-7) |
| λ(E) | Episode latch; FALSE when E opens | [LOD] (OD-4) |
| **DB event** | If ¬λ(E): GF-10 event at session D*_M; λ(E) := TRUE | [LOD] |
| **HF event** | If ¬λ(E) and G(D*_M): GF-10 event at the first genuine 1m bar of D*_M; λ(E) := TRUE | [LOD] (X-1, OD-7). Exact timestamp label: imported draft OPEN-6 |
| **HF no-bar crossing** | If ¬λ(E) and ¬G(D*_M): **no event**; λ(E) := TRUE | [LOD] (RQ-11 = D) |
| **HF substrate start** | For every episode open at the first HF session: λ(E) := FALSE, regardless of any pre-substrate crossing. Ledgers keep their EOD history | [LOD] (RQ-10 = B, X-2 = A). Already-crossed active candidate: **OPEN-B** |
| DB profile end | DB events stop at the end of DB availability; no latch carries into HF (by RQ-10 = B) | **RESOLVED** |
| Profile separation | A DB event and an HF event may exist in the same calendar episode; they belong to different, never-pooled populations | **RESOLVED** (X-2 = A); NC-6 |

---

## 4. State machine and timeline (per stock; bull shown, bear mirrors)

```text
State (daily-derived, read on D as of D⁻, re-based to as-of-D):
  K3: ℓ, run counters, swing points (first-occurrence dates)
  S9: σ; episode E = (σ, a); latch λ(E)
  Ledger(E): completed same-type K3 moves (dur, literal mag window) ; completed qualifying reactions (bull)
  Candidate M: (P_S, d_S, c) or none
  Profile: DB (EOD only) | HF (EOD history + genuine 1m on D)
```

| Phase | What happens | Governing locks |
|---|---|---|
| **A. Line UP, no current bull candidate** | 1–2-session LL runs are recorded as reactions **on completion** (the next non-LL close), with Top_ρ per RQ-6 and qualification per RQ-7. They enter Ledger(E) only if a BULL episode is open and they are members of it | OPEN-2.1/2.2/2.3/2.5; OPEN-1; RQ-6/7 OPEN |
| **B. Down-switch close c** | (1) X⁺ = (h, first d_h) confirmed. (2) S9 recomputed. If σ changes: E closes, and its ledger and λ are discarded; if the new σ ∈ {BULL, BEAR}, a new E opens at a = c with an empty ledger and λ = FALSE. (3) The switch-run sessions are not reactions. (4) If S9_c = BULL, M = (X⁺, c) is a candidate of the episode current at c, **including one created at c (SC-3)**; d_S may precede a. (5) 𝒰_T and R_T fixed (constant, §3.4). 𝒰_P fixed subject to RQ-1, RQ-2, RQ-5. A move completed at c belongs to the episode per RQ-1 (OPEN) | R-1; OPEN-3b; SC-3; OPEN-4.1/4.5; OPEN-1 |
| **C. Active session D ∈ (c, u]** | Using 𝔉(D) re-based to as-of-D. **Time leg:** if ¬λ(E) ∧ 𝒰_T ≠ ∅ ∧ el_M(D) > R_T → DB: event at D; HF with G(D): event at the first genuine 1m bar of D; HF without G(D): no event (RQ-11 = D). In every case λ(E) := TRUE. **Price leg:** run_M(τ) from EOD lows over (d_S, D⁻] and the observation-session term (HF: normalized genuine 1m lows up to τ; DB: EOD low of D), compared with R_P (RQ-2) under RQ-3/RQ-4. No-bar HF sessions: OPEN-C. New lows extend run; the clock is not reset; a new high above P_S does not terminate M | OD-7/8/9; OPEN-4.2/4.3/4.4; C-7; RQ-8 = A; RQ-9 = A+x; RQ-11 = D |
| **D. Up-switch close u (termination)** | M is active on u and inactive from the next session. X⁻ = (l, first d_l) confirmed. If E continues past u, M enters Ledger(E) as a completed decline: dur = cal(d_l) − cal(d_h) (OPEN-A), mag by the literal window over (d_h, u]. A non-triggering M simply ends (move reset) | OPEN-4.3; C-7; RQ-8 = A |
| **E. Latch set** (emitted event or RQ-11 = D no-bar crossing) | λ(E) = TRUE. Later candidates in E cannot emit GF-10 events. Completed moves still enter the ledger (inert while latched) | OD-4/6; C-7; RQ-11 = D |
| **F. S9 reset** (only at a switch close; coincides with some c or u) | E closes and its ledger and λ are discarded. If the new σ ∈ {BULL, BEAR}, a new episode opens with an empty ledger and λ = FALSE. A move confirmed at that close joins it (SC-3). A move completed at that close: RQ-1 | OD-5; OPEN-1; SC-3 |
| **G. HF substrate start** (first HF session) | For every open episode: λ(E) := FALSE (RQ-10 = B). K3, S9, the ledger and the current candidate are carried from EOD history (X-1/X-2 = A). A candidate active at the start is evaluated from the first HF session; if el > R_T already held on a pre-substrate date: **OPEN-B** | RQ-10 = B; X-1/X-2 = A; OD-7 |

**Timelines (schematic):**

```text
SC-3 (down-switch creates BULL):
  d_h … [LL][LL][LL = c]   S9: NONE → BULL at c; E opens at a = c
  M member of E; d_S = d_h < a; Ledger(E) = ∅ → M cannot trigger
  … up-switch u (S9 still BULL) → Ledger(E) = {M: dur = cal(d_l) − cal(d_h), mag over (d_h, u]}
  next down-switch c₂ → M₂; R_T = dur(M); M₂ active from the session after c₂

HF no-bar crossing (RQ-11 = D):
  M active; D* has el > R_T; G(D*) = FALSE → no HF event; λ(E) = TRUE → no later HF event in E

HF substrate start (RQ-10 = B):
  E open since a (EOD era); λ(E) := FALSE at the first HF session
  candidate M active at the start with el already > R_T on an earlier date → OPEN-B
  otherwise the first HF session with el > R_T and G = TRUE emits the event
```

---

## 5. Remaining OPEN items

### 5.1 Recorded RQs not decided in this conversation (content as analysed in v0.1 §5)

| ID | Question (short) | Why it matters | Choices (v0.1) | Source | Dependencies |
|---|---|---|---|---|---|
| **RQ-1** | Membership of a move **completed** (not confirmed) at the episode-creating switch | Whether the first decline of an up-switch-created episode can trigger | (a) exclude; (b) include; (c) ≡ (a) | None | — |
| **RQ-2** | Price-comparator form over K3 declines ∪ reactions | Sets R_P; contrast content | (a) max over union; (b) max over declines, reactions as fallback; (c) separate references; (d) other | "the previous decline **or** reaction" [GS]; greatest reaction in [WSSS] p. 176 | RQ-5, RQ-6, RQ-7 |
| **RQ-3** | Price-leg evaluation only where 𝒰_T ≠ ∅? | Matched populations for T(time) − T(price) | (a) matched; (b) unmatched; (c) both, (a) on path | None | RQ-1, RQ-2; G-4 |
| **RQ-4** | Price-leg latch | Price-flag population | (a) independent; (b) shared; (c) latch on the time event only | "first time" in the bear price clause [GS] (bear only) | RQ-3 |
| **RQ-5** | Must reactions complete on or before d_S (vs before c)? | Self-overlap of the price comparator (reactions inside the current decline) | (a) ≤ d_S; (b) < c; (c) no overlap with [d_S, c] | "previous" [GS]; start locked at d_S [LOD] | — (no effect on 𝒰_T, §3.4) |
| **RQ-6** | Reaction top includes the reaction-session (outside-day) highs? | mag(ρ) | (a) before s₁; (b) through s_k; (c) outside days are not reactions | None | — |
| **RQ-7** | Adjacency of a reaction to the fresh leg high | Size of the reaction set | (a) none; (b) the session before s₁ set the leg high; (c) within 2 sessions | p. 61 / p. 63 near extremes [GS] (discretionary) | RQ-6 |

**Status of each: OPEN — OPERATOR DECISION NOT RECORDED IN THIS CONVERSATION.**

### 5.2 New OPEN items surfaced by the v0.2 audit

**OPEN-A — Reference-duration endpoint vs the literal price window.**

| Field | Entry |
|---|---|
| Ambiguity | dur(M′) uses the K3 swing-low date d_l′ (v0.1 / R-5 "high date to low date"). Under RQ-8 = A the reference **price** extreme is the literal minimum over (d_h′, u′], which can occur on a different, earlier session than d_l′ (a pre-switch low below l′). The reference "low" is then one session for time and another for price |
| Why it matters | Changes R_T whenever the literal minimum precedes d_l′, and so changes the GF-10 time-event population |
| Choices | (a) Keep d_l′ (the K3 swing-low date; time stays K3-based, price literal) — disclose the dual endpoint. (b) Use the first-occurrence date of the literal minimum (time and price share one extreme). (c) Other |
| Source | p. 63 example measures a duration from "last high" to "extreme low" [GS] (strong inference). Neither choice is established for Rule 8 |
| Classification | Operator-defined; created by the combination of RQ-8 = A with R-5/R-1, not a reopening |
| Dependencies | None. The tie rule for (b) would follow OPEN-4.5 (first occurrence) |

**OPEN-B — An HF candidate already crossed before the substrate start.**

| Field | Entry |
|---|---|
| Ambiguity | Under RQ-10 = B the latch is FALSE at the first HF session. A candidate active at the start may have had el > R_T on an earlier, EOD-era date. The time condition still holds on the first HF session |
| Why it matters | If it emits there, an event lands on the substrate's first session. That is arguably a DB-era crossing turned into an HF event (X-2 = A), and not the "first objectively observable crossing" of OD-7 (that was pre-substrate). If not, that candidate is spent while the episode stays unlatched for later candidates |
| Choices | (a) Emit an HF event on the first HF session (with G = TRUE). (b) Candidate spent: no HF event from it; episode latch stays FALSE (RQ-10 = B), so later candidates may trigger. (c) Exclude candidates active at the start from HF |
| Tension | Choice (a) sits in tension with X-2 = A and OD-7. (b) and (c) are consistent with all locks. **Not resolved here** |
| Source | None |
| Classification | Operator-defined |
| Dependencies | RQ-10 = B (locked), X-2 = A (locked), OD-7 (locked) |

**OPEN-C — Price leg on an HF session with no genuine 1m bar.**

| Field | Entry |
|---|---|
| Ambiguity | RQ-11 = D fixes the time leg. On a no-bar HF session the observation-session price term LowObs has no 1m source. RQ-9 = A+x reserves EOD for **historical** sessions only |
| Why it matters | Price-flag population on no-bar sessions |
| Choices | (a) Price leg not evaluated on that session (the session's EOD low enters as history from the next session). (b) Use the session's EOD low as the observation term (a departure from RQ-9 = A for that session). (c) Mirror RQ-11 = D: no flag, but the price latch is set if EOD shows a crossing |
| Source | None |
| Classification | Operator-defined |
| Dependencies | RQ-3, RQ-4 (the price-leg scope and latch must exist first) |

### 5.3 Imported, open elsewhere (not re-analysed)

- **Gaps and preconditions:** G-4 (contrast p), G-5, G-6 (burn-in / minimum names), G-7 (CA exclusion
  windows; also needed by the RQ-9 = x normalization), G-8, G-9; P-1 … P-5.
- **Draft items:** OPEN-6 (exact timestamp label), OPEN-11 (weekly score mapping), OPEN-12 (outcome
  window anchor).
- **Implementation dependency for RQ-9 = x:** the CA factor list from R-13 (external enumeration
  outstanding, P-2).

---

## 6. Checks (updated from v0.1)

| # | Item | v0.2 verdict |
|---|---|---|
| 6.1 | "Completed" reference move | **RESOLVED.** K3 move: at its opposite switch close. Reaction: at the first following non-LL close |
| 6.2 | Eligibility at the confirmation close or the next session | **RESOLVED**, no population difference (D−1 freeze; u′ ≤ d_S < c) |
| 6.3 | Current/reference alignment under D−1 | Time leg **RESOLVED**. Price leg: RQ-1, RQ-5 OPEN |
| 6.4 | Same price basis | **RESOLVED** (RQ-9 = A+x): all comparisons on D are on the as-of-D basis; HF observation-session 1m normalized; history and references are EOD in both profiles |
| 6.5 | Equal highs/lows in references | **RESOLVED (derived)**: one first-occurrence date per K3 swing point. Under OPEN-A (b), the literal minimum's date would follow the same first-occurrence rule |
| 6.6 | Bull/bear universe separation | **RESOLVED** |
| 6.7 | K3 moves vs reactions | Mostly **RESOLVED**; RQ-5, RQ-6, RQ-7 OPEN |
| 6.8 | May a reaction be the greatest reference? | **OPEN (RQ-2)** |
| 6.9 | Time comparison | **RESOLVED**, except OPEN-A (reference endpoint), RQ-1 (boundary) and OPEN-B (substrate start). RQ-11 = D incorporated |

### 6.10 Disclosure notes (no decision)

| ID | Note |
|---|---|
| **NC-1** | Bear "higher-high" reaction structures do not become K3 on a 3rd session (the up-switch also needs higher lows). They are not operative |
| **NC-2** | The K3 switch asymmetry makes bull and bear current moves structurally different (R-1; disclose under G-2(b) pooling) |
| **NC-3** | Events concentrate structurally on a move's first active session whenever R_T is below the confirmation lag (OPEN-4.2 + OD-7 + D−1) |
| **NC-4** | "Reaction ≠ K3" is an operator decision; Gann uses "3-day reaction" (Δ3-04) and multi-week "reaction" (Δ2-08) |
| **NC-5** | HF running extreme: on D the observation term is the normalized 1m low; from D+1 the same session enters as its EOD low. The two may differ, so run can change between sessions without new trading (RQ-9 = A+x as locked) |
| **NC-6** | One calendar episode can hold a DB event (EOD era) and an HF event (after the substrate start, RQ-10 = B). The populations are never pooled (X-2 = A) |
| **NC-7** | RQ-10 = B (pre-substrate crossings do not latch) and RQ-11 = D (no-bar crossings inside the substrate do latch) treat unobservable crossings differently by period. This is **consistent** (different circumstances, each locked) and is disclosed, not a contradiction |

---

## 7. Contradiction audit

**Scope:** stage table (§1.2), source/operator separation (§2), mathematical definitions (§3), state
machine and timelines (§4), OPEN items (§5), checks (§6) and decision ledger (§9), cross-checked
against every lock listed in §9.

### 7.1 Result

**v0.1: FAIL.** Issues V1-1 … V1-5 below, all corrected in v0.2.

**v0.2: PASS — no contradiction** among the locked decisions or between the document's sections.

The audit also found:
- **three gaps** that combinations of locks leave undetermined (OPEN-A, OPEN-B, OPEN-C), each marked
  OPEN rather than resolved;
- **one reading hazard**: OPEN-B choice (a) would conflict with X-2 = A / OD-7 if adopted.

**Completeness caveat:** RQ-1 … RQ-7 are OPEN because no decision on them is recorded in this
conversation. The PASS covers internal consistency, not completeness.

### 7.2 Issues found

| ID | Location (v0.1) | Issue | Type | v0.2 disposition |
|---|---|---|---|---|
| V1-1 | §3.5 | Reference magnitude h′ − l′ (K3 endpoints) vs a literal "lowest reached so far" for the current move: non-like-for-like comparison | Inconsistency | **Corrected** (RQ-8 = A): same literal window for both (§3.5) |
| V1-2 | §3.4 | "completes at or before c (the previous opposite line ended at c)": wrong object | Wording error | **Corrected**: u′ ≤ d_S < c (§3.4) |
| V1-3 | §3.8, §4 C | HF observation described as "1m lows on D" without basis normalization; DB/HF history source unstated | Underspecified (then RQ-9 OPEN) | **Resolved** by RQ-9 = A+x (§1.2 rows 1–2, 16; §3.1; §3.5) |
| V1-4 | §3.8, §4 | No substrate-start latch rule; no no-bar rule | Underspecified (then RQ-10/11 OPEN) | **Resolved** by RQ-10 = B, RQ-11 = D (§3.8; §4 C, E, G) |
| V1-5 | — | No decision ledger; locks were stated only in prose | Traceability | **Added** §9 |
| V2-1 | §3.4 vs §3.5 | Reference **duration** endpoint (K3 swing-low date) vs reference **price** extreme (literal minimum) can differ after RQ-8 = A | Gap created by locks | **OPEN-A** |
| V2-2 | §3.8 / §4 G | Active candidate already crossed pre-substrate: emission at the substrate start would conflict with X-2 = A / OD-7; non-emission is not stated by RQ-10 = B | Gap / hazard | **OPEN-B** |
| V2-3 | §3.7 / §4 C | Price leg on a no-bar HF session: RQ-9 = A+x gives no observation-session source | Gap | **OPEN-C** |
| V2-4 | §3.1 | Historical values must be re-based to as-of-D when a CA falls between their session and D | Consistency requirement | **Stated** (§3.1 basis note); implementation depends on the R-13 CA list and G-7 |
| V2-5 | NC-7 | RQ-10 = B vs RQ-11 = D apparent asymmetry | Checked | **Not a contradiction**; disclosed |
| V2-6 | §1.2 rows 13/17 vs §3 | Stage table and math agree on ledger scope, reaction exclusion from time, bull-only reactions and strict `>` | Cross-check | PASS |
| V2-7 | §4 B/F vs §3.2 | SC-3 membership identical in math and state machine; RQ-1 flagged in both | Cross-check | PASS |
| V2-8 | §2 vs §1.2 | No row attributes an [LOD] item to Gann; "first time" is bear-only [GS] everywhere; S9 bear never called Gann's bear condition | Cross-check | PASS |
| V2-9 | §9 vs §1.2/§3/§4 | Every ledger entry maps to a section; every OPEN appears in §5 | Cross-check | PASS |

---

## 8. What empirical testing must NOT decide

**Definitional — decided before any data read, never from results:**
- RQ-1 … RQ-7;
- OPEN-A, OPEN-B, OPEN-C;
- every lock in §9;
- any later threshold, window, adjacency or source rule.

No choice may be justified by event counts, coverage, "too few/many events", IC, Sharpe, surrogate p,
contrast p, size-check outcome or any O-R10 association.

**Empirical — only in the pre-registered read, after freeze:**
- Association of GF-10 events with O-R10 beyond the surrogate null (R-14).
- T(time) vs T(price) (R-10, G-4).
- Descriptive population statistics: reported, never used to revise a definition.

**Implementation — settled by code review and deterministic tests, not results:**
- K3/S9 correctness (memo §5).
- D−1 freeze enforcement.
- Causal prefix invariance; byte-identical replay.
- As-of-D re-basing and 1m normalization (ratio test).
- `is_synthetic = FALSE`, `bar_labeling.py`, GAP sessions and `SPECIAL_SESSIONS` for G(D).
- First-occurrence tie handling.
- The timestamp label (imported OPEN-6).

---

## 9. Decision ledger

| ID | Decision | Status | Where applied |
|---|---|---|---|
| OD-1 | Time leg: greatest qualifying previous decline/rally | LOCKED | §1.2-13/14; §3.4 |
| OD-2 | "Decline or reaction" preserved; 1/2/3-day framework; reaction ≠ K3 | LOCKED | §1.2-15; §3.6 |
| OD-3 | Bear = S9 bear (research convention) | LOCKED | §1.2-5 |
| OD-4 | First exceedance per S9 episode | LOCKED | §1.2-21; §3.8 |
| OD-5 | Episode resets on S9 reversal or cessation | LOCKED | §1.2-11; §3.2; §4 F |
| OD-6 | Symmetric bull/bear first-exceedance | LOCKED | §1.2-21 |
| OD-7 | Event = first objectively observable crossing | LOCKED | §1.2-19; §3.8; OPEN-B |
| OD-8 | Running extreme | LOCKED | §1.2-16; §3.5 |
| OD-9 | Strict `>` | LOCKED | §1.2-18; §3.4; §3.7 |
| OD-10 | Finest available resolution | LOCKED (via HF/DB) | §1.2-1 |
| C-1/C-2/C-3 | HF 1m where available; DB daily elsewhere; never pooled; D−1 freeze of K3/S9 | LOCKED | §1.2-1, 6 |
| C-4 | K3-based eligibility; current move = K3 decline/rally; reactions only as bull price comparator | LOCKED | §1.2-7, 15, 17 |
| C-5 | OD-1 supersedes "immediately preceding" | LOCKED | §3.4 |
| C-6 | OD-7 supersedes week-end timing | LOCKED | §1.2-19 |
| C-7 | Move-level reset + episode-level first-event latch | LOCKED | §1.2-21/22; §4 D/E |
| X-1 = A | HF: 1m for detection; EOD for K3/S9 context, pre-substrate allowed | LOCKED | §1.2-1; §4 G |
| X-2 = A | Never pool populations; HF may use EOD lookback | LOCKED | §1.2-1; §3.8; OPEN-B |
| OPEN-3b = A | S9 on confirmed K3 points; changes only at a switch close; D−1 freeze | LOCKED | §1.2-4; §3.1 |
| OPEN-4.1 = A | Start at the K3 swing high / swing low | LOCKED | §1.2-7; §3.3 |
| OPEN-4.2 = A | Clock from the starting-extreme date | LOCKED | §1.2-9; §3.4 |
| OPEN-4.3 = A | Terminate at confirmed K3 reversal; no intraday price break | LOCKED | §1.2-10; §3.3 |
| OPEN-4.4 = A | Time endpoint = observation date | LOCKED | §1.2-9; §3.4 |
| OPEN-4.5 = A | First occurrence of equal starting extremes | LOCKED | §1.2-8; §3.1 |
| SC-3 = A | Move confirmed at the episode-creating switch is included; not truncated | LOCKED | §1.2-12; §3.2; §4 B |
| OPEN-2.1 = A | Reaction = 1/2-day LL (bull) / HH structures; 3rd session → K3 | LOCKED | §3.6 |
| OPEN-2.2 = A | Reaction starts from the running extreme of the preceding K3 leg | LOCKED | §3.6 |
| OPEN-2.3 = B | Reaction bounded to the 1/2-day structure | LOCKED | §3.6 |
| OPEN-2.4 = A | Reactions excluded from the time leg; bull price clause only | LOCKED | §1.2-14/17 |
| OPEN-2.5 = B | "Near an extreme" structural (anchor), not numeric | LOCKED | §3.6 |
| OPEN-1 = A | Reference universe = current S9 episode; greatest completed previous same-type move; no carryover; first move cannot trigger | LOCKED | §1.2-13; §3.4; §3.7 |
| RQ-1 | Membership of a move completed at the creating switch | **OPEN — not recorded** | §5.1 |
| RQ-2 | Price-comparator form | **OPEN — not recorded** | §5.1 |
| RQ-3 | Time/price candidate alignment | **OPEN — not recorded** | §5.1 |
| RQ-4 | Price-leg latch | **OPEN — not recorded** | §5.1 |
| RQ-5 | Precedence cut for references | **OPEN — not recorded** | §5.1 |
| RQ-6 | Reaction top | **OPEN — not recorded** | §5.1 |
| RQ-7 | Reaction adjacency | **OPEN — not recorded** | §5.1 |
| RQ-8 = A | Literal running-price window for current and reference moves | LOCKED | §1.2-16; §3.5 |
| RQ-9 = A+x | History = EOD; observation session = genuine 1m; normalize to as-of-D basis | LOCKED | §1.2-1/2/16; §3.1; §3.5 |
| RQ-10 = B | HF latch FALSE at substrate start | LOCKED | §3.8; §4 G |
| RQ-11 = D | HF no-bar crossing: no event, latch set | LOCKED | §3.8; §4 C/E |
| OPEN-A | Reference-duration endpoint vs literal price extreme | **OPEN (new)** | §5.2 |
| OPEN-B | Pre-substrate-crossed HF candidate | **OPEN (new)** | §5.2 |
| OPEN-C | Price leg on a no-bar HF session | **OPEN (new)** | §5.2 |

## 10. Recommended decision order for what remains

| Step | Decision | Depends on |
|---|---|---|
| 1 | Supply or rule **RQ-1** | — |
| 2 | **OPEN-A** | — |
| 3 | **RQ-5** | — |
| 4 | **RQ-6** | — |
| 5 | **RQ-7** | RQ-6 |
| 6 | **RQ-2** | RQ-5, RQ-6, RQ-7 |
| 7 | **RQ-3** | RQ-1, RQ-2 |
| 8 | **RQ-4** | RQ-3 |
| 9 | **OPEN-B** | locks only |
| 10 | **OPEN-C** | RQ-3, RQ-4 |

---

**NO CODE. NO BACKTEST. NO EMPIRICAL TESTING. NO MARKET OUTCOMES READ. NO LOCKED DECISION REOPENED.
NOT FROZEN. NOT AN IMPLEMENTATION SPECIFICATION.**
