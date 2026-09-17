# GF-10 Mechanical Decision Record — v0.1

**Date:** 2026-09-17

**Status: CONSOLIDATED DECISION RECORD — NOT THE FROZEN SPECIFICATION.** No code, backtest, empirical
test, optimization or performance analysis was performed. No market data or outcome was read. No
governance or repository document was modified. **No locked decision is reopened.** Where an item is
fully determined by the locks it is marked **RESOLVED** and no new decision is created.

**Inputs:**

| Document | Role |
|---|---|
| `PTMS_GANN_GF10_FINAL_MECHANICAL_SPECIFICATION_DRAFT_2026-09-17.md` (commit `948f2ef`) | Parent draft; its C-1 … C-7 were subsequently resolved |
| `GF10_OPEN1_OPEN2_OPEN4_MECHANICAL_DECISION_ANALYSIS_2026-09-17.md` | Option analysis. Option letters below refer to its choices as locked by the operator |
| Operator lock sets of 2026-09-17 | OD-1 … OD-10; substrate; C-4 … C-7; X-1 = A; X-2 = A; OPEN-3b = A; OPEN-4.1/4.2/4.3/4.4/4.5 = A; SC-3 = A; OPEN-2.1 = A, 2.2 = A, 2.3 = B, 2.4 = A, 2.5 = B; OPEN-1 = A |
| `PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md` | R-1 (K3), R-2 / G-2(b) (O-R10), R-5, R-10, R-13, R-14 |
| `PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md` | §5 (K3 rows 1–13), §8.2 |

**Provenance markers used on every rule:**

| Marker | Meaning |
|---|---|
| **[GS]** | GANN SOURCE: wording or arithmetic verified in *45 Years in Wall Street* (1949) or another verified Gann book; register ID given |
| **[LOD]** | LOCKED OPERATOR / RESEARCH DECISION |
| **[NES]** | NOT ESTABLISHED BY SOURCE: Gann does not state this; it must never be attributed to him |

A rule can carry more than one marker. A [GS] marker on part of a rule does not extend to the rest of
the rule.

**Construct label:** GF-10 = **GANN-FAITHFUL SOURCE CONCEPT + EXPLICIT OPERATOR/RESEARCH CONVENTIONS.**
It is not "Gann's exact rule".

---

## 1. Locked mechanical model (end-to-end)

### 1.1 Causal chain

```text
Authoritative EOD daily bars (R-13 basis)
  └─► K3 line state and confirmed swing points (R-1)
        └─► confirmed S9 state; changes only at a K3 switch close (OPEN-3b = A)
              └─► D−1 state freeze: every daily-derived fact used on session D is as of the D−1 close
                    └─► current K3 move (bull: K3 decline from its swing high; bear: K3 rally from its swing low)
                          └─► reference universe = completed previous moves of the same type in the current S9 episode (OPEN-1 = A)
                                ├─► time reference R_T = greatest reference duration (K3 moves only; OPEN-2.4 = A)
                                └─► price reference R_P = over K3 declines ∪ qualifying 1/2-day reactions (bull only; C-4) — form: RQ-2
                                      └─► first objectively observable strict crossing (OD-7, OD-9)
                                            ├─► time crossing  ⇒ GF-10 EVENT (primary score; R-5 / R-10)
                                            └─► price crossing ⇒ price-overbalance flag (specificity contrast only; R-10)
                                                  └─► episode latch until S9 changes (OD-4/5/6, C-7)
```

### 1.2 Stage-by-stage statement with provenance

| # | Stage | Locked content | Provenance |
|---|---|---|---|
| 1 | Data | **HF profile:** genuine 1m observations for event detection; authoritative EOD daily data for K3/S9 context, which may extend before the 1m substrate begins (X-1 = A). **DB profile:** daily only, where 1m is unavailable. **HF and DB event/result populations are never pooled**; HF may use EOD history as causal lookback without turning DB-era observations into HF events (X-2 = A) | [LOD]; [NES] (Gann specifies no data resolution) |
| 2 | K3 | Strict 3-Day Chart, all memo §5 implementation assumptions: literal down-switch = 3 consecutive lower lows; up-switch = 3 consecutive higher highs **and** higher lows; strict inequality; day-over-day; outside/inside-day handling; 2-day exception not applied; usable from the confirming close | Construction rule [GS] Δ2-10 (p. 63); strict mechanization [LOD] (R-1, "approximation of a discretionary Gann detector"); Gann's record departs in ≥ 7 of 61 swings [GS] Δ3-02 |
| 3 | S9 | BULL iff the last two confirmed K3 tops and the last two confirmed K3 bottoms are both rising; BEAR iff both falling; else NONE. Changes only at a confirmed K3 switch close | Rule 9 higher tops and bottoms [GS] (p. 12); S9 mechanization and use as Rule 8 state [LOD]; S9 as a Rule 8 precondition [NES] |
| 4 | Bear condition | S9 BEAR | [LOD] (OD-3). Gann's bear wording is a decline "for a long period of Time" [GS] Δ2-01 (p. 12). S9 bear as that condition [NES] |
| 5 | D−1 freeze | For an event on session D, K3/S9 state and every daily-derived move, reference and reaction fact is as of the D−1 close | [LOD]; [NES] |
| 6 | Current move | Bull: a K3 decline starting at its K3 swing high. Bear: a K3 rally starting at its K3 swing low. Reactions never create a current move (C-4) | Measurement from a high/low [GS] (p. 11 "from any high or low"; p. 63 example); K3 as the move object [LOD] |
| 7 | Starting-extreme ties | First occurrence of an equal extreme price | [LOD] (OPEN-4.5); [NES] |
| 8 | Time clock | Starts at the starting swing-extreme **date**; ends at the **event observation date**; not stopped at the date of the running price extreme | Calendar-day differences, start date excluded [GS] Δ3-06 (worked examples), Δ2-10 / p. 61 ("based on calendar days", 3-day moves); applied to Rule 8 and to the current-move endpoint [LOD] (OPEN-4.2, OPEN-4.4) |
| 9 | Termination | The current move ends at the confirmed opposite K3 switch. No intraday price-break termination | [LOD] (OPEN-4.3) |
| 10 | Episode | Maximal run of closes with constant S9 ∈ {BULL, BEAR}. Resets on S9 reversal **or** cessation | [LOD] (OD-5); [NES] |
| 11 | SC-3 | A K3 move **confirmed** at the switch close that creates the episode is a member of that episode. Its starting extreme may predate the episode; it is not truncated | [LOD] (SC-3 = A); [NES] |
| 12 | Reference universe | Completed previous moves of the same type within the current episode. No carryover across episodes. No fixed N, no calendar lookback, no entire history. The first qualifying move in an episode has no reference and cannot trigger | "a previous decline/rally" [GS] Δ2-01/02; greatest time period as reference [GS] Δ2-04 (p. 39, separate statement); episode scope and "greatest" in Rule 8 [LOD] (OD-1, OPEN-1); [NES] |
| 13 | Time reference | Greatest duration among completed previous **K3** moves of the same type (bull: K3 declines; bear: K3 rallies). Reactions excluded | Bull time clause says "decline" [GS] Δ2-01; exclusion of reactions [LOD] (OPEN-2.4 = A) |
| 14 | Reaction | Bull: a 1- or 2-session structure of consecutive strict lower lows inside a K3 UP line. A 3rd consecutive lower-low session is a K3 down-switch, not a reaction. Bounded to that structure (not kept alive until trend resumption). Starts from the running extreme of the K3 leg in progress. "Near an extreme" is structural (the anchor), not numeric | "decline or reaction" [GS] Δ2-02 (bull price clause only); 2-day reactions not recorded except near extremes [GS] Δ2-10, Δ3-01 (discretionary); "reaction ≠ K3", the 1/2-day bound, the anchor and the structural near-extreme reading [LOD] (OD-2, OPEN-2.1/2.2/2.3/2.5); [NES]. **Source tension (disclosure):** Gann also calls a recorded 3-day move a "3-day reaction" [GS] Δ3-04 (p. 66) |
| 15 | Price comparator | Bull: completed K3 declines and qualifying reactions (Rule 8 bull price clause). Bear: completed K3 rallies only | Bull "decline or reaction" [GS]; bear "a previous rally" [GS] Δ2-02; restriction of reactions to the bull price leg [LOD] (C-4, OPEN-2.4); comparator form: **RQ-2** |
| 16 | Magnitude | Running extreme: bull = starting high − lowest price reached so far; bear = highest price reached so far − starting low | High/low measurement [GS] (p. 63 example; strong inference); running form [LOD] (OD-8); [NES] |
| 17 | Triggers | Strict `>`; equality does not trigger | "exceeds", "greater" [GS] Δ2-01/02; equality treatment [LOD] (OD-9) |
| 18 | Event timing | First objectively observable crossing; not deferred to week-end, move completion or outcome | "is taking place" / "has started" [GS] Δ2-02 (strong inference only); mechanization [LOD] (OD-7) |
| 19 | GF-10 event | The time-leg crossing. The price leg is the specificity contrast, not a score | Time outranks price [GS] Δ2-02 (p. 12); T(time) − T(price) and the primary/contrast roles [LOD] (R-5, R-10) |
| 20 | Latch | One GF-10 event per stock per S9 episode; later candidates in a latched episode cannot trigger | "the first time" in bear clauses only [GS] Δ2-01/02; per-episode latch and bull symmetry [LOD] (OD-4, OD-6, C-7); [NES] |
| 21 | Move reset | Each qualifying current K3 move is an independent candidate. A candidate that terminates without triggering ends. Another candidate may arise in the same episode | [LOD] (C-7) |
| 22 | Outcome (context only) | O-R10 per R-2 / G-2(b) | Rule 10 [GS] Δ2-11 (a separate rule); its use as Rule 8's outcome [NES]; [LOD] |

---

## 2. Source fact vs operator decision (summary)

| Rule | GANN SOURCE | LOCKED OPERATOR / RESEARCH DECISION | NOT ESTABLISHED BY SOURCE |
|---|---|---|---|
| Stocks as well as averages | ✔ p. 11 | — | — |
| Compare durations of current vs previous decline/rally | ✔ Δ2-01 | — | — |
| Compare points of current vs previous decline or reaction (bull) / rally (bear) | ✔ Δ2-02 | — | — |
| Strict exceedance | ✔ "exceeds", "greater" | Equality = no trigger | Equality treatment |
| "The first time" | ✔ bear clauses only | Applied per episode, both directions | Per-episode scope; bull use |
| Time more important than price | ✔ p. 12 | T(time) − T(price) contrast | Any statistic |
| "Greatest" as comparator | Greatest time period named separately (p. 39) | ✔ OD-1 / OPEN-1 | "Greatest" as Rule 8's comparator |
| Calendar days | ✔ 3-day moves (p. 61); worked examples Δ3-06 | Applied to Rule 8 | Rule 8's own unit |
| Measurement from a high / to a low | ✔ p. 11, p. 63 (inference) | Running form; first-occurrence ties | Running form; tie rule |
| 3-Day Chart | ✔ construction rule (discretionary in practice) | Strict K3 | K3 as Rule 8's detector |
| Market state | Rule 9 higher tops/bottoms | S9 bull/bear | S9 as a Rule 8 precondition; S9 bear as the bear condition |
| Episode, reset, latch | — | ✔ | ✔ |
| Reaction class | "decline or reaction"; 2-day reactions recorded only near extremes; "3-day reaction" (p. 66) | 1/2-day bound; reaction ≠ K3; structural anchor | The bound; the anchor |
| Reactions in the time leg | Bull time clause says "decline" | Excluded | — |
| D−1 freeze; HF/DB profiles; 1m evaluation | — | ✔ | ✔ |
| Termination at the opposite K3 switch | — | ✔ | ✔ |
| Rule 10 outcome; 5 sessions; weekly formation; pooling | Rule 10 is a separate rule | ✔ | ✔ |

---

## 3. Mathematical definitions

### 3.1 Primitives

| Symbol | Definition | Provenance |
|---|---|---|
| 𝒟 | Ordered set of NSE sessions; d⁻ is the session before d; cal(d) is the calendar date of d | [LOD] |
| H_d, L_d | Authoritative EOD high and low of session d, on the R-13 as-of-*t* ratio-adjusted basis | [LOD] (R-13, X-1) |
| LL(d) | L_d < L_{d⁻} (strict, day-over-day) | [LOD] (R-1) |
| HH(d), HL(d) | H_d > H_{d⁻}; L_d > L_{d⁻} | [LOD] (R-1) |
| ℓ_d ∈ {UP, DOWN, ∅} | K3 line state as of the close of d (memo §5) | [LOD] (R-1) |
| Down-switch close c | A close at which ℓ changes UP → DOWN (3rd consecutive LL session) | [GS] Δ2-10 construction; [LOD] literal mechanization |
| Up-switch close u | A close at which ℓ changes DOWN → UP (3rd consecutive HH ∧ HL session) | same |
| Swing high X⁺ = (h, d_h, c) | h = max H_d over the UP line ended at down-switch close c; d_h = the **first** session in that line with H_d = h; confirmed at c | [LOD] (R-1; OPEN-4.5 first occurrence — see §6.5) |
| Swing low X⁻ = (l, d_l, u) | l = min L_d over the DOWN line ended at up-switch close u; d_l = the **first** session in that line with L_d = l; confirmed at u | [LOD] (R-1; OPEN-4.1 and OPEN-4.5 mirror — see §6.5) |
| S9_d ∈ {BULL, BEAR, NONE} | From the last two confirmed tops {h} and bottoms {l} as of close d. BULL iff both pairs strictly rising; BEAR iff both strictly falling; else NONE. S9_d ≠ S9_{d⁻} only if d is a switch close | [LOD] (OPEN-3b = A) |
| Frozen state at D | 𝔉(D) = every quantity above as of the close of D⁻ | [LOD] (D−1 freeze) |

### 3.2 S9 episode

An **episode** E = (σ, a, b) is a maximal half-open interval of closes [a, b) such that:
- S9_d = σ ∈ {BULL, BEAR} for all a ≤ d < b;
- a is the close at which S9 became σ (a switch close);
- b is the next close at which S9 ≠ σ (reversal to the opposite state **or** cessation to NONE), or
  +∞ if none has occurred.

A return to σ after NONE opens a **new** episode. [LOD] (OD-5)

**Membership (SC-3 = A).** A K3 move whose **confirming** switch close c satisfies a ≤ c < b belongs
to E. The case c = a is included; the move's starting extreme date may be earlier than a. [LOD]

### 3.3 Current bull decline and current bear rally

- **Current bull decline** in E (σ = BULL): M = (X⁺, c, u), where X⁺ is a swing high confirmed at
  down-switch close c ∈ [a, b), and u is the next up-switch close (u = +∞ until it occurs). [LOD]
  (C-4, OPEN-4.1)
- **Current bear rally** in E (σ = BEAR): M = (X⁻, u, c), where X⁻ is a swing low confirmed at
  up-switch close u ∈ [a, b), and c is the next down-switch close. [LOD] (mirror)
- **Starting extreme:** (P_S, d_S) = (h, d_h) for a bull decline; (l, d_l) for a bear rally. [LOD]
  (OPEN-4.1, OPEN-4.5)
- **Active sessions (D−1 freeze + OPEN-4.3):** for a bull decline, M is active on session D iff
  c ≤ D⁻ and ¬(u ≤ D⁻), i.e. D ∈ (c, u]. The terminating session u is itself active: the reversal is
  confirmed only at u's close. Mirror for bear. [LOD] — **RESOLVED**

By SC-4 of the analysis memo (under OPEN-3b = A), no S9 change can occur strictly between c and u.
The episode containing M therefore cannot end while M is active, except at u itself. **RESOLVED**

### 3.4 Elapsed time and time trigger

| Symbol | Definition | Provenance |
|---|---|---|
| el_M(D) | cal(D) − cal(d_S), an integer number of calendar days, start date excluded. Evaluated on the observation session D | [GS] Δ3-06 day-count arithmetic; [LOD] OPEN-4.2 and OPEN-4.4 |
| dur(M′) | For a completed reference bull decline: cal(d_l′) − cal(d_h′). Bear rally: cal(d_h′) − cal(d_l′) | [GS] p. 63 "7-day decline" (strong inference); [LOD] |
| 𝒰_T(M, D) | {M′ : M′ a K3 move of the same type (bull: decline; bear: rally), M′ ∈ E, M′ ≠ M, M′ completed by D⁻, M′ previous to M} | [LOD] (OPEN-1 = A; OPEN-2.4 = A). "Completed" §6.1 RESOLVED; boundary RQ-1 |
| R_T(M, D) | max_{M′∈𝒰_T} dur(M′); **undefined** if 𝒰_T = ∅ | [LOD] (OD-1) |
| Time crossing | TC_M(D) ⇔ M active on D ∧ 𝒰_T ≠ ∅ ∧ el_M(D) > R_T | [LOD] (OD-9) |

Because every same-type reference M′ ≠ M in E completes at or before c (the previous opposite line
ended at c), 𝒰_T and R_T are **constant over M's active sessions**. No snapshot rule is needed.
**RESOLVED.**

### 3.5 Running extreme and reference magnitude

| Symbol | Definition | Status |
|---|---|---|
| run_M(τ) (bull) | P_S − min{ price lows observed in the window W_M(τ) } | OD-8 locked; the window W_M(τ) is **RQ-8**; in HF the source and basis of lows before D are **RQ-9** |
| run_M(τ) (bear) | max{ highs in W_M(τ) } − P_S | Mirror |
| mag(M′) (completed K3 decline) | h′ − l′ (swing values) | [LOD] (swing points per R-1, OPEN-4.1 mirror); consistency with run: **RQ-8** |
| mag(M′) (completed K3 rally) | h′ − l′ | Mirror |

### 3.6 Reaction (bull; used only in the bull price comparator)

Inside a K3 UP line, a **bull reaction** ρ is a maximal run of consecutive LL sessions s₁ (, s₂) such
that:
- the session before s₁ is not LL (or the run begins after an up-switch close);
- the run has length k ∈ {1, 2}.

A 3rd consecutive LL session makes the run a K3 down-switch; the run is then **not** a reaction.
[LOD] (OPEN-2.1 = A, OPEN-2.3 = B)

| Symbol | Definition | Status |
|---|---|---|
| Top_ρ | Running maximum of H over the K3 UP leg in progress, as of the close before s₁ | [LOD] (OPEN-2.2 = A); inclusion of reaction-session highs: **RQ-6** |
| Low_ρ | L_{s_k}, the low of the last reaction session (strictly lowest in the run by LL) | **RESOLVED** |
| mag(ρ) | Top_ρ − Low_ρ (> 0 by construction) | **RESOLVED** |
| Completion | ρ is classified and completed at the close of the first session after s_k that is not LL. Only then is k known to be 1 or 2 and not a K3 switch | **RESOLVED** (bounded structure, OPEN-2.3 = B). Under the D−1 freeze it is usable from the following session |
| Qualification ("near extreme") | Structural anchor to the running leg extreme; no numeric threshold | [LOD] (OPEN-2.5 = B); adjacency to that extreme: **RQ-7** |
| Bear "higher-high" structures | Defined by OPEN-2.1's wording but **unused** (C-4: reactions only in the bull price leg) | **RESOLVED — not operative** (see NC-1) |

### 3.7 Price reference and price trigger

| Symbol | Definition | Status |
|---|---|---|
| 𝒰_P(M, D) (bull) | {completed K3 declines in E previous to M} ∪ {completed qualifying bull reactions in E previous to M}, all completed by D⁻ | [GS] "decline or reaction"; [LOD] C-4. Precedence rule: **RQ-5** |
| 𝒰_P(M, D) (bear) | {completed K3 rallies in E previous to M} | [GS] "a previous rally"; [LOD] |
| R_P(M, D) | **Form OPEN:** max_{x∈𝒰_P} mag(x) is the natural reading of OPEN-1 = A, but OD-1 was scoped to the time leg | **RQ-2** |
| Price crossing | PC_M(τ) ⇔ M active on d(τ) ∧ 𝒰_P ≠ ∅ ∧ run_M(τ) > R_P | [LOD] (OD-8, OD-9); eligibility alignment with the time leg: **RQ-3** |

### 3.8 GF-10 event, observation and latch

| Symbol | Definition | Status |
|---|---|---|
| Time-event session D*_M | min{ D ∈ 𝒟 : TC_M(D) } | [LOD] (OD-7) |
| Observability | el_M(D) depends only on the date, so TC_M(D) is objectively known before any price on D. **HF:** the event instant is the first genuine (non-synthetic) 1m bar of D*. **DB:** the event is session D* | Session: **RESOLVED**. Exact timestamp convention: imported draft OPEN-6 (does not change the session population). HF sessions without genuine bars: **RQ-11** |
| GF-10 event | ev(i, E) = the first D*_M over candidates M ∈ E, taken in confirmation order, provided E is not latched | [LOD] (OD-4, C-7) |
| Episode latch | λ(E) := TRUE at the first GF-10 event in E. While λ(E) = TRUE, no candidate in E can emit a GF-10 event. λ resets only when a new episode opens | [LOD] (OD-4/5/6) |
| Price-leg latch | Separate or shared with λ(E) | **RQ-4** |

### 3.9 Structural consequence (derived from the locks, not a choice)

Under OPEN-1 = A, the first K3 decline (bull) or rally (bear) confirmed in an episode has
𝒰_T = ∅ **unless** RQ-1 admits a move completed at the episode-creating switch.

- **Down-switch-created BULL episode (SC-3 case):** the current decline is confirmed at c = a. No
  same-type move completed within E exists yet, so it cannot trigger. **Its own completion** makes it
  the reference for the next decline.
- **Up-switch-created BULL episode:** E begins at u = a. The decline that just completed at u was
  confirmed **before** a. Whether it is a reference is **RQ-1**.

---

## 4. State machine and timeline (per stock; bull shown, bear mirrors)

```text
Per-stock state carried from close to close (all daily-derived; read on D as of D⁻):
  K3: line ℓ, run counters, swing points
  S9: σ ∈ {BULL, BEAR, NONE}; episode E = (σ, a); latch λ(E)
  E-ledger: completed same-type K3 moves in E (duration, magnitude); completed qualifying reactions in E
  Candidate M: (P_S, d_S, c) or none
```

| Phase | What happens | Governing lock |
|---|---|---|
| **A. Before a K3 switch** (line UP) | LL runs of 1–2 sessions are recorded as reactions **once completed** (the next non-LL close). Each has Top_ρ = running leg high before s₁ (RQ-6, RQ-7). No current bull candidate exists. The E-ledger may gain reactions only if a BULL episode is open | OPEN-2.1/2.2/2.3/2.5; OPEN-1 |
| **B. At a K3 down-switch close c** | (1) Swing high X⁺ = (h, first d_h) confirmed. (2) S9 recomputed with the new top. If σ changes, the old episode closes and λ is discarded; a new episode opens at a = c if σ ∈ {BULL, BEAR}. (3) The 1–2 LL sessions before the 3rd are the switch run, **not** reactions (OPEN-2.1). (4) If S9_c = BULL, M = (X⁺, c) becomes a candidate of the episode current at c, including an episode created at c itself (**SC-3**: d_h may be earlier than a). (5) R_T and R_P are fixed from the E-ledger (completed by c) | R-1; OPEN-3b; SC-3; OPEN-4.1/4.5; OPEN-1 |
| **C. During the current move** (sessions D ∈ (c, u]) | On each D, using 𝔉(D): M is active. If λ(E) = FALSE and 𝒰_T ≠ ∅ and el_M(D) > R_T → GF-10 event at the first observable instant of D; set λ(E) = TRUE. The price leg is evaluated intraday (HF: 1m lows on D; DB: daily low of D) against R_P, subject to RQ-3, RQ-4, RQ-8, RQ-9. New lows extend run_M; they do not reset the clock. A new high above P_S does **not** terminate M | OD-7/8/9; OPEN-4.2/4.3/4.4; C-7 |
| **D. When the move terminates** (up-switch close u) | M is active on session u and inactive from u's next session. Swing low X⁻ = (l, first d_l) confirmed. M becomes a **completed K3 decline**: dur = cal(d_l) − cal(d_h), mag = h − l. It enters the E-ledger if E continues past u. If M did not trigger, it simply ends (move reset) | OPEN-4.3; C-7 |
| **E. When a GF-10 event triggers** | λ(E) = TRUE. Every later candidate in E is evaluated for nothing on the time leg. Completed moves still enter the ledger (inert while latched) | OD-4/6; C-7 |
| **F. When S9 resets** (at a switch close, by SC-4 coinciding with c or u) | E closes; its ledger and latch are discarded (no carryover). If the new σ ∈ {BULL, BEAR}: a new episode with an empty ledger and λ = FALSE. A move confirmed at that same close joins the new episode (SC-3). A move **completed** at that close: **RQ-1** | OD-5; OPEN-1; SC-3 |

**Timeline illustrations (dates schematic):**

```text
SC-3 (down-switch creates BULL):
  d_h ... [LL][LL][LL=c]   S9: NONE → BULL at c;  E opens at a = c
  M confirmed at c, member of E, d_S = d_h < a.  Ledger(E) = ∅  → M cannot trigger (OPEN-1 = A)
  ... up-switch at u (S9 still BULL) → M completes → Ledger(E) = {M}
  next down-switch c₂ → M₂ candidate; R_T = dur(M); eligible from c₂'s next session

Up-switch creates BULL (RQ-1):
  prior decline M₀ confirmed at c₀ (S9 = NONE), completes at u = a where S9: NONE → BULL
  Is M₀ ∈ Ledger(E)?  RQ-1.  If yes, the first decline confirmed in E can trigger; if no, it cannot.
```

---

## 5. Remaining unresolved mechanical questions

Only questions that can change the GF-10 event population (or the matched price-contrast population)
are listed. Each can be ruled without reopening a lock.

### RQ-1 — Episode membership of a reference move **completed** at the episode-creating switch

| Field | Entry |
|---|---|
| Ambiguity | SC-3 = A covers a move **confirmed** at the creating switch. OPEN-1 = A says "completed previous move … within that S9 episode". A K3 decline confirmed before a but **completed** at the up-switch close u = a that creates a BULL episode (mirror: a rally completed at a down-switch creating BEAR) fits one phrase and not the other |
| Why it matters | Decides whether the first K3 decline confirmed in an up-switch-created episode has a time reference, and so whether it can trigger. The lock sentence "first qualifying move in an episode has no previous reference universe" reads most naturally under (a); (b) would give the first *candidate* a reference |
| Choices | (a) Membership by confirmation close only: excluded (consistent with the SC-3 test). (b) Membership by completion close: included. (c) Included only if its confirmation close already had the same σ (always false here, so equivalent to (a)) |
| Source support | None. Episodes are not a Gann concept |
| Classification | Operator-defined |
| Dependencies | None. Upstream of RQ-3 |

### RQ-2 — Price-comparator form over the mixed set

| Field | Entry |
|---|---|
| Ambiguity | OD-1 fixed "greatest" for the **time** leg. OPEN-1 = A says "greatest qualifying completed previous move of the same type" without naming a leg. For the bull price leg, is R_P the maximum over K3 declines ∪ reactions (a reaction may therefore be the reference), and is "same type" the union ("decline or reaction")? |
| Why it matters | Sets R_P for every price-leg evaluation and the content of the T(time) − T(price) contrast. Under "greatest" the reaction set changes R_P only when a reaction is deeper than every K3 decline in the episode. Under any other form (e.g. most recent), shallow 1–2-day reactions would often be the reference |
| Choices | (a) R_P = max over the union (reaction allowed to be the greatest). (b) R_P = max over K3 declines only; reactions used only when no K3 decline exists. (c) Two separate references (decline, reaction); trigger on exceeding either or both. (d) Other form (most recent), which is inconsistent with the C-5 supersession of "immediately preceding" for time |
| Source support | "the previous decline **or** reaction" [GS] Δ2-02 (a single comparator, disjunctive; "the previous" is singular); "greatest" as comparator [NES] for price in Rule 8. The greatest **reaction** as a price reference appears in *Wall Street Stock Selector* (F0-TOB-04, [WSSS] p. 176), another book |
| Classification | Operator-defined (source constrains the set, not the form) |
| Dependencies | After RQ-5, RQ-6, RQ-7 (the contents of the set) |

### RQ-3 — Candidate-set alignment between the time and price legs

| Field | Entry |
|---|---|
| Ambiguity | Reactions can exist in an episode before the first K3 decline completes. A candidate can then have 𝒰_P ≠ ∅ but 𝒰_T = ∅ (it cannot trigger GF-10). Is the price leg evaluated for such candidates? |
| Why it matters | R-10's contrast compares T(time) with T(price). If the eligible candidate populations differ, the contrast mixes a population difference with a time-vs-price difference |
| Choices | (a) Price leg evaluated only for candidates with 𝒰_T ≠ ∅ (matched populations). (b) Price leg evaluated wherever 𝒰_P ≠ ∅ (unmatched; disclose). (c) Both reported, with (a) on the pass path |
| Source support | None (time-over-price ranking [GS] p. 12 says nothing about eligibility) |
| Classification | Operator-defined (research design) |
| Dependencies | RQ-1, RQ-2. Coupled to imported G-4 (contrast p) |

### RQ-4 — Price-leg latch

| Field | Entry |
|---|---|
| Ambiguity | OD-4 latches the GF-10 (time) event per episode. Does the price flag have its own first-per-episode latch, share λ(E), or not latch? |
| Why it matters | Determines how many price flags an episode can produce and whether a time event suppresses later price flags. This changes the price-overbalance score population, and so the contrast |
| Choices | (a) Independent first-per-episode latch (symmetry with OD-4). (b) Shared latch: the first event of either leg latches both. (c) The price leg latches only on the time event |
| Source support | "the first time" appears in the bear **price** clause as well as the bear time clause [GS] Δ2-02, which supports a per-leg "first time" for bear only |
| Classification | Operator-defined, with partial source wording |
| Dependencies | RQ-3 |

### RQ-5 — Precedence: must a reference be "previous" to the current move's starting extreme, or only to its confirmation?

| Field | Entry |
|---|---|
| Ambiguity | Between the swing high date d_S and the down-switch close c, the UP line can still contain a completed 1-day reaction (LL, non-LL, then the 3-LL switch run). That reaction lies **within** the current decline's price path, yet completes before c |
| Why it matters | Such a reaction measures part of the current decline from the same top, so it can enter R_P and compare the move partly with itself. This does **not** affect R_T (K3 references always complete on or before d_S), only the price leg |
| Choices | (a) A reference must complete on or before d_S (strictly previous to the move's start). (b) A reference must complete before c. (c) Exclude references whose span overlaps [d_S, c] |
| Source support | "previous" [GS] Δ2-01/02; the current move starts at the swing high [LOD] OPEN-4.1. (a) and (c) are the readings consistent with the locked start, but the source does not fix the cut |
| Classification | Operator-defined (source-constrained) |
| Dependencies | None. Upstream of RQ-2 |

### RQ-6 — Reaction top: include highs made on the reaction sessions?

| Field | Entry |
|---|---|
| Ambiguity | A reaction session is defined by a lower low. It may also make a higher high (an outside day) above the running leg high. Is Top_ρ taken before s₁ (excluding that high) or including the reaction sessions' highs? |
| Why it matters | Changes mag(ρ) whenever an outside day starts a reaction; this can change R_P (under RQ-2(a)) |
| Choices | (a) Top_ρ = running leg high as of the close before s₁. (b) Top_ρ = running leg high through s_k. (c) Outside-day sessions do not start a reaction (they are not reactions) |
| Source support | None specific. K3 swing highs include outside-day highs within the UP line (R-1 memo §5 row 13 handles outside days for run counts only) |
| Classification | Operator-defined |
| Dependencies | None |

### RQ-7 — "Near an extreme": adjacency of the reaction to the running leg extreme

| Field | Entry |
|---|---|
| Ambiguity | OPEN-2.5 = B anchors a qualifying reaction to the preceding K3 leg's running extreme. It does not say whether the reaction must **begin immediately** after the session that set that extreme, or whether any 1–2-day LL run later in the leg (after non-LL sessions that made no new high) still qualifies, measured from the same extreme |
| Why it matters | Without adjacency, every 1–2-day LL run in an UP leg qualifies (the analysis memo noted a leg-scope anchor is otherwise ≈ no condition). Several reactions can share one top, and mag(ρ) can capture a multi-session pullback from an earlier high. With adjacency, only reactions starting from a fresh leg high qualify |
| Choices | (a) No adjacency: every bounded LL run in the leg qualifies, measured from the running leg high. (b) Adjacency: the session before s₁ must have set the running leg high. (c) Adjacency within the reaction bound: the leg high must have been set within the 2 sessions before s₁ |
| Source support | 1- and 2-day moves are used "when extreme highs or lows are reached and we wish to catch a turn" [GS] Δ3-01 (p. 61); 2-day moves recorded "near" extremes [GS] Δ2-10 (p. 63). Supports a link to the extreme, not its exact form. Discretionary |
| Classification | Operator-defined (source-motivated) |
| Dependencies | RQ-6 |

### RQ-8 — Running-extreme window and consistency with reference magnitudes

| Field | Entry |
|---|---|
| Ambiguity | Reference K3 magnitudes use swing values h − l, where l is the minimum low **while the line is DOWN**. Gann's line moves to the low of the third day and follows lows from there [GS] Δ2-10. The current move uses "lowest price reached so far" (OD-8) from P_S. Two windows are undefined: (i) whether the starting session's own low counts; (ii) whether lows on non-LL sessions between d_S and the switch run count, when they are below the eventual K3 swing low. K3 ignores such a low; a literal "reached so far" includes it |
| Why it matters | A current magnitude and reference magnitudes measured over different windows are not like-for-like. The price trigger can fire or not purely from the window difference. Current and reference must use one rule |
| Choices | (a) Literal: run uses all lows strictly after d_S through τ; reference magnitudes recomputed the same way (h − min L over (d_h, d_l]), **not** the K3 swing value l. (b) K3-consistent: run uses lows from the switch run onward (plus intraday on D); references use h − l. (c) Literal for current, K3 for references (the unreconciled literal state of the locks) — inconsistent, listed only for completeness. (d) Include the start session's low in both |
| Source support | p. 63 example: "last high" to "extreme low" [GS] (strong inference for extremes); Δ2-10 line construction [GS]. Neither fixes the window |
| Classification | Operator-defined (a consistency requirement created by combining OD-8 with R-1) |
| Dependencies | None. Upstream of RQ-2 and RQ-9. Bear mirror identical |

### RQ-9 — HF price source for the running extreme and price-basis alignment

| Field | Entry |
|---|---|
| Ambiguity | X-1 = A assigns K3/S9 context to EOD and event detection to 1m. The running extreme on session D mixes (i) lows of sessions before D and (ii) intraday lows on D. It is not locked whether (i) comes from EOD or from 1m for sessions inside the 1m substrate. The EOD series is ratio-adjusted as of *t* (R-13); the 1m store is back-adjusted to the current basis (CLAUDE.md: never join 1m and bhavcopy prices across a CA), so points differ by the CA ratio across any later corporate action. The 1m session low can also differ from the EOD low of the same session |
| Why it matters | P_S (EOD) − 1m low compared with R_P (EOD): a basis or source mismatch shifts the price trigger by the CA ratio or by the EOD-vs-1m low difference. Price-leg population only (the time leg is date-based) |
| Choices | Source: (a) EOD lows for sessions before D, 1m lows on D; (b) 1m lows throughout the 1m substrate, EOD before it. Basis: (x) express 1m prices on the R-13 as-of-*t* basis (convert via the CA factor) before comparison; (y) compare in ratio form within a session, only where OD-8's points definition can be shown equivalent — otherwise not admissible |
| Source support | None (a data question) |
| Classification | Operator-defined (source choice); implementation (basis conversion, verifiable by the ratio test) |
| Dependencies | RQ-8 |

### RQ-10 — HF substrate start: episodes and latches already in progress

| Field | Entry |
|---|---|
| Ambiguity | With EOD context before 2023-01-02 (X-1 = A), an S9 episode can be open at the 1m start, and a time crossing may have occurred earlier in it on a pre-substrate date. X-2 = A forbids turning that into an HF event. It does not say whether that pre-substrate crossing **latches** the episode for HF |
| Why it matters | Decides whether the first HF event of an episode can occur on a later candidate in an episode that, on EOD evidence, had already "triggered". It also governs the HF event population near the substrate start |
| Choices | (a) Causal replay: date-based time crossings before the substrate start set λ(E) (no event emitted), so no HF event later in that episode. (b) λ starts FALSE at the substrate start for every open episode. (c) Episodes open at the substrate start are excluded from HF until S9 resets |
| Source support | None |
| Classification | Operator-defined |
| Dependencies | RQ-1 (ledger membership before the start). Mirror at the DB profile end: DB events simply stop; no latch carries forward — **RESOLVED** by X-2 = A |

### RQ-11 — HF sessions without genuine 1m bars

| Field | Entry |
|---|---|
| Ambiguity | The time crossing on D is date-determined. In HF the event instant is the first genuine 1m bar of D. If D has no genuine bars for the stock (declared GAP session, halt, all-synthetic), is the event placed on D, moved to the next session with genuine bars, or dropped? The same applies to the price leg's intraday lows on D |
| Why it matters | Moving the event changes its session (and so the formation week and outcome window). Dropping it changes the event population. The latch consequence differs by choice |
| Choices | (a) Event on D with the session-open timestamp regardless of bars (time leg is date-based). (b) Deferred to the next session with genuine bars, if the move is still active. (c) No event; the latch is not set; later candidates can still trigger. (d) No event, but the latch **is** set (causal crossing occurred) |
| Source support | None |
| Classification | Operator-defined; the GAP list itself is an implementation fact (PTMS 1m certificate) |
| Dependencies | RQ-10 |

---

## 6. Checks requested by the operator (verified against the analysis memo)

| # | Item | Verdict | Basis |
|---|---|---|---|
| 6.1 | What a "completed" reference move is | **RESOLVED.** A K3 decline completes at the up-switch close that confirms its swing low (mirror for rallies). A reaction completes at the close of the first following non-LL session, or never (it becomes a K3 switch). Values: swing points (subject to RQ-8's consistency choice) | R-1; OPEN-2.1/2.3; §3.3, §3.6 |
| 6.2 | Reference eligibility at its confirmation close or the next session | **RESOLVED — no population difference.** Under the D−1 freeze a fact confirmed at close x is usable from the next session. Every same-type K3 reference completes at or before the current move's confirmation c, and the current move is active only from c's next session, so the two readings coincide | D−1 freeze; §3.4 |
| 6.3 | Alignment of current and reference moves under D−1 | **RESOLVED for the time leg** (references complete on or before d_S; R_T constant). **OPEN for the price leg:** RQ-5 (precedence cut) and RQ-1 (boundary) | §3.4; RQ-1; RQ-5 |
| 6.4 | Same price basis for current and reference magnitudes | **OPEN (HF only): RQ-9.** DB uses one EOD series throughout — **RESOLVED** for DB | R-13; X-1; CLAUDE.md CA pitfall |
| 6.5 | Equal highs/lows in reference moves | **RESOLVED (derived).** A K3 swing point is a single object with one date. OPEN-4.5 fixes first occurrence for the swing high that starts a bull decline and, by the locked bear mirror (OPEN-4.1), for the swing low that starts a bear rally. A reference decline's start high and end low are those same objects, so they carry first-occurrence dates. Magnitudes use values, so ties do not affect them. A reaction low cannot tie (strict LL). A reaction top's date is unused (reactions are not in the time leg) | OPEN-4.1; OPEN-4.5; OPEN-2.4 |
| 6.6 | Strict separation of bull and bear universes | **RESOLVED.** An episode has one σ; the universe is same-type moves within the episode; no carryover. A BULL episode's references are K3 declines (+ reactions for the price leg) only; completed K3 rallies in a BULL episode are never references | OPEN-1; OD-5; OPEN-2.4; C-4 |
| 6.7 | Interaction between K3 moves and 1/2-day reactions | **Mostly RESOLVED:** a 3rd LL converts to K3; the switch run is never a reaction; reactions only in UP lines; bounded; never a current move; never in the time leg. **OPEN:** RQ-5 (reactions between d_S and c), RQ-6 (outside-day top), RQ-7 (adjacency) | OPEN-2.1/2.3/2.4; C-4 |
| 6.8 | May a reaction be the greatest reference when mixed with K3 declines? | **OPEN: RQ-2** | OD-1 scope; OPEN-1 wording |
| 6.9 | Remaining ambiguity in the time comparison | **RESOLVED:** integer calendar-day difference from the first-occurrence swing-extreme date to the observation session date; R_T = greatest same-type K3 duration in the episode (constant over the move); strict `>`; evaluated on NSE sessions; the first session with el > R_T while active is the event session, observable at the session's first instant. **Open only where HF data are missing (RQ-11)**, at the substrate start (RQ-10), and at the episode boundary (RQ-1). The exact timestamp convention (imported draft OPEN-6) does not change the session population |

### 6.10 Noted consistency items (no decision needed)

| ID | Note |
|---|---|
| **NC-1** | OPEN-2.1's "higher-high structures" (bear reactions) do not satisfy "a third qualifying session becomes K3": the K3 up-switch needs higher highs **and** higher lows. Bear reactions are not operative (C-4, OPEN-2.4), so there is no effect. Record so a later extension does not assume symmetry |
| **NC-2** | The K3 switch asymmetry (literal down = LL only; up = HH ∧ HL) makes bull and bear current moves structurally different. This is an R-1 disclosure item under G-2(b) pooling |
| **NC-3** | A structural concentration of events on the first active session (c's next session) occurs whenever R_T is below the confirmation lag (analysis memo C-a). This is a consequence of OPEN-4.2 + OD-7 + D−1. **Disclose; do not adjust** |
| **NC-4** | "Reaction ≠ K3" is an operator decision. Gann calls a recorded 3-day move a "3-day reaction" (Δ3-04, p. 66) and uses "reaction" for multi-week moves (Δ2-08). Disclosure only |

---

## 7. What empirical testing must NOT decide

### 7.1 Definitional questions — decided before any data read, never from results

1. RQ-1 … RQ-11, every choice listed in §5.
2. Every locked decision in this record (not reopenable by results).
3. Any change of: K3 rules, S9 rule, episode reset, latch, starting extreme, tie rule, clock origin
   and endpoint, termination rule, SC-3 membership, reference universe, reaction bound and anchor,
   time-leg exclusion of reactions, strict inequality, profile separation, D−1 freeze.
4. Any threshold, window, lookback, minimum size or adjacency rule introduced later.

**No choice may be justified by:** event counts, coverage, "too few" or "too many" events, IC,
Sharpe, surrogate p, contrast p, size-check outcome, or any O-R10 association.

### 7.2 Empirical questions — answered only by the pre-registered read, after freeze

1. Whether the GF-10 time event is associated with O-R10 beyond the synchronized surrogate null (R-14).
2. Whether T(time) exceeds T(price) under the ruled contrast (R-10, G-4).
3. Descriptive event-population statistics: **reported, never used to revise a definition.**

### 7.3 Implementation questions — settled by code review and deterministic tests, not by results

1. K3 / S9 state-machine correctness against memo §5 rows 1–13 (hand-constructed bar sequences).
2. Replay determinism: the same inputs give byte-identical events; causal prefix invariance (truncating
   data after D does not change events on or before D).
3. D−1 freeze enforcement (no session-D daily fact used on D).
4. Basis conversion correctness once RQ-9 is ruled (ratio test: EOD/1m = 1 except at CA ratios).
5. HF data hygiene: `is_synthetic = FALSE`; bar-label resolution via `core/market/bar_labeling.py`;
   declared GAP sessions; special sessions (`SPECIAL_SESSIONS`); calendar (`nse_holidays`).
6. The exact event timestamp convention (imported draft OPEN-6), consistently applied.

**Imported and still open elsewhere, not re-analysed here:** G-4 (contrast p), G-5 (missing-bar
neighbourhood), G-6 (burn-in / minimum names), G-7 (CA exclusion windows), G-8 (seed), G-9 (size
check); draft OPEN-11 (score persistence on the weekly grid) and OPEN-12 (outcome window anchor);
P-1 … P-5.

---

## 8. Recommended decision order (one at a time)

Ordered by dependency: each decision needs only those above it.

| Step | Decision | Why at this position |
|---|---|---|
| **1** | **RQ-1** — membership of a move completed at the episode-creating switch | Independent; fixes which moves are in any ledger |
| **2** | **RQ-8** — running-extreme window and reference-magnitude consistency | Independent; defines magnitudes used by every price comparison |
| **3** | **RQ-5** — precedence cut for references (start date vs confirmation) | Independent; fixes which completed items are "previous" |
| **4** | **RQ-6** — reaction top (outside-day highs) | Independent; defines mag(ρ) |
| **5** | **RQ-7** — adjacency of reactions to the running leg extreme | Needs RQ-6; fixes the reaction set |
| **6** | **RQ-2** — price-comparator form over K3 declines ∪ reactions | Needs RQ-5, RQ-6, RQ-7, RQ-8 (set contents and magnitudes) |
| **7** | **RQ-3** — time/price candidate-set alignment | Needs RQ-1, RQ-2 |
| **8** | **RQ-4** — price-leg latch | Needs RQ-3 |
| **9** | **RQ-9** — HF lows source and basis alignment | Needs RQ-8 |
| **10** | **RQ-10** — HF substrate-start latch initialization | Needs RQ-1 |
| **11** | **RQ-11** — HF sessions without genuine 1m bars | Needs RQ-10 |

After step 11, the GF-10 event and price-flag populations are fully defined on both profiles. The next
items are imported, and none may be decided from results:
- draft OPEN-11 (weekly score mapping) and OPEN-12 (outcome window);
- G-4 … G-9;
- the freeze document.

---

**NO CODE. NO BACKTEST. NO EMPIRICAL TESTING. NO OPTIMIZATION. NO PERFORMANCE ANALYSIS. NO LOCKED
DECISION REOPENED. NOTHING FROZEN OR HASHED. NO EXISTING DOCUMENT MODIFIED.**
