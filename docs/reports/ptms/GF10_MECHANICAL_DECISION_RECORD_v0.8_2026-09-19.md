# GF-10 Mechanical Decision Record — v0.8

**Date:** 2026-09-19

**Status: CONSOLIDATED DECISION RECORD — NOT AN IMPLEMENTATION SPECIFICATION, NOT AN EMPIRICAL FREEZE.**
- No code, backtest, empirical test, optimization or performance analysis was performed.
- No market data or outcome was read. No event count was computed. Nothing is frozen or hashed.
- **No locked decision is reopened.**

**Supersedes:** v0.7 (`GF10_MECHANICAL_DECISION_RECORD_v0.7_2026-09-19.md`, commit `72b3f0d`), which is
kept unchanged. Earlier versions: v0.6 and v0.5 (`bdc40f6`), v0.4 (`bdc40f6`), v0.3 (`d9a9119`), v0.2
(superseded; provenance error) and v0.1 (`59e25da`).

**New in this version:** the operator rulings of 2026-09-19 (commit `49dbfa9`, `PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md`),
transcribed without change.

| Item | Operator ruling | Kind |
|---|---|---|
| OPEN-K(a) | **A1.** A stock without a P1 event is eligible in *w* iff a qualifying candidate is active on the week's last session D_L, in the D−1-frozen state used on D_L. OPEN-11's "last eligible trading session" means the last **NSE** session | GF-10 lock |
| K(a)-P1 | A candidate with 𝒰_T = ∅ (OPEN-1 = A, "cannot trigger") is **eligible → 0** | GF-10 lock |
| K(a)-P2 | Weeks of an episode after its P1 event (λ set) are **eligible → 0** | GF-10 lock |
| OPEN-K(b) | A score-0 stock-week's O-R10 applies **OPEN-12b/c/d at f_w = close(D_L)** in place of t_e | GF-10 lock |
| OPEN-K(c) | Two P1 events of one stock in one week: the **first** anchors O-R10 and its direction; the later is recorded, not scored | GF-10 lock |
| RR-1 | Penetration is **strictly beyond** the reference; equality is not a penetration | GF-10 lock (ratified) |
| RR-2 | **Literal:** the first post-event penetration must fall in O_1 … O_5; an HF same-session post-event break gives y = 0 | GF-10 lock (ratified) |
| OPEN-L | The contrast uses **one shared outcome per stock-week, anchored at f_w** (the OPEN-K(b) rule), for both legs | GF-10 lock |
| OPEN-M | Any observation with O_5 > Z is **excluded** (all primaries) | Panel-level ruling, applied |
| CAL-1 | **ISO Monday–Sunday** weeks (all primaries) | Panel-level ruling, applied |
| G-4 | Contrast p = (1 + #{b : Δ_b ≥ Δ}) / (B + 1), Δ = T(time) − T(price), B = 1999 joint surrogates | Panel-level ruling, applied |
| G-6 | No extra burn-in; at least **20** eligible names per formation date (per profile for GF-10) | Panel-level ruling, applied |
| G-7 | **Full-span** exclusion of observations whose dependency span contains a non-ratio ex-date | Panel-level ruling, applied |
| OPEN-N | A contrast stock-week whose contributing candidates have opposite directions is **excluded** (ruled after the v0.8 audit surfaced it) | GF-10 lock |
| RR-3 | **Ratified:** T(leg) = the T_c formula (mean over formation weeks of the per-date cross-sectional Spearman IC of the leg's score vs the shared y), per profile, with the 20-name floor | GF-10 lock (ratified) |

G-5 (missing bars), G-8 (seed 42) and G-9 (size check) are surrogate-layer rulings. They do not enter
the GF-10 mechanical definition; they are recorded in the rulings file and the freeze checklist.

**Result of this version (§7):** no contradiction among the **72 GF-10 locks**. The v0.8 audit
surfaced one unresolved item (OPEN-N) and one reading for ratification (RR-3), and the operator ruled
both the same day. **No GF-10 mechanical definition remains open.** Every observation of the primary
score and the contrast has a defined eligibility, score, direction, O-R10 and exclusion rule. The only
item left is the operator's confirmation of the GF-10 G-7 span start at freeze review (§3.12).

**Construct label:** GF-10 = **GANN-FAITHFUL SOURCE CONCEPT + EXPLICIT OPERATOR/RESEARCH CONVENTIONS.**
It is not "Gann's exact rule".

**Provenance markers:**

| Marker | Meaning |
|---|---|
| **[GS]** | GANN SOURCE: verified wording or arithmetic; register ID given |
| **[LOD]** | LOCKED OPERATOR / RESEARCH DECISION |
| **[NES]** | NOT ESTABLISHED BY SOURCE; never to be attributed to Gann |

A [GS] marker on part of a rule does not extend to the rest of it. **OPEN-F, CONF-1, OPEN-H, OPEN-I,
OPEN-J, OPEN-6, OPEN-11, OPEN-12, every latch, substrate homogeneity, all contrast scoring and the
whole outcome definition are operator/research conventions: [LOD] and [NES], never [GS].**

**Document layout:**

| Part | Sections |
|---|---|
| LOCKED | §1 – §4, §9 |
| Resolved record, OPEN (newly surfaced) and imported | §5 |
| Future implementation / empirical work | §8 |
| Supersessions (2026-09-17 specification draft; R-5 primary cell) | §11 |

---

## 0. Change log from v0.7

| # | Change | Sections |
|---|---|---|
| CL-1 | **OPEN-K(a) = A1, K(a)-P1 / K(a)-P2 = eligible → 0, OPEN-K(c) = first event** transcribed: score-0 eligibility, structural zeros, two-event weeks | §1.2-27; §3.9 |
| CL-2 | **RR-1, RR-2** ratified: strict penetration and the literal "first penetrated" move from readings to locks | §3.10 |
| CL-3 | **OPEN-K(b)**: O-R10 for a 0 = OPEN-12 at f_w. **OPEN-L**: the contrast's shared outcome at f_w. New §3.11 | §1.2-24/26; §3.11 |
| CL-4a | OPEN-N ruled (exclude); RR-3 ratified | §5.3 |
| CL-4 | Panel rulings applied: **OPEN-M** (exclude O_5 > Z), **CAL-1** (ISO week), **G-6** (no extra burn-in, min 20 names on the A1 eligible set), **G-7** (full-span CA exclusion; GF-10 span start stated for confirmation), **G-4** (contrast p). New §3.12 | §3.12 |
| CL-5 | Derived: X_ref exists for **every** eligible observation, including an episode's first candidate (S9 BULL itself needs confirmed bottoms) | §3.11 |
| CL-6 | Derived and disclosed: persistence asymmetry of the 0s (NC-25); mixed anchoring (NC-26); contrast y ≠ primary y (NC-27) | §3.9; §3.11; §6.11 |
| CL-7 | Audit over **72 locks**. The audit surfaced **OPEN-N** and **RR-3**; the operator ruled both (OPEN-N = exclude; RR-3 ratified) | §5.3; §7 |
| CL-8 | §11.2 extended (persistence A against R-5's repeating 1s) | §11.2 |

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
                                                  incomplete at the sample end ⇒ right-censored, excluded (OPEN-J)

Timestamps and weekly scores (OPEN-6, OPEN-11):
  every instant = bar end (HF: end of the genuine 1m bar; DB: close of the session)
  s(i, w) = 1 in the formation week containing the P1 event only; 0 eligible, no event; excluded if not eligible
  formation instant f_w = close of the week's last trading session; an event with t_e ≤ f_w belongs to w

Outcome of a P1 event (OPEN-12a–d), in strict time order:
  reference K3 swing confirmed (close ≤ D_e⁻)  →  candidate M formed (close of c)  →  M active (D_e ≥ c⁺)
    →  event observable; t_e = bar end  →  remainder of D_e (never outcome)  →  O_1 … O_5 = next five sessions
    →  O-R10 = 1 iff the reference is unpenetrated through t_e and first penetrated in O_1 … O_5
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
| 19 | Event timing | First objectively observable crossing. **Timestamp = bar end** (HF: end of the 1m bar; DB: close of the session, derived) | [GS] (inference); [LOD] OD-7, C-6, **OPEN-6** |
| 20 | GF-10 event (P1) | Time crossing. HF: first genuine 1m bar of the crossing session, t_e = its bar end; no genuine bar → no event, λ set. DB: the crossing session, t_e = its close | [GS] p. 12; [LOD] R-5, R-10, RQ-11 = D, **OPEN-6**; [NES] |
| 21 | Time latch λ | One GF-10 event per stock per episode; reset only at a new episode; HF: FALSE at substrate start. **Governs P1 only** | [GS] "first time" (bear only); [LOD] OD-4/6, C-7, RQ-10 = B, RQ-11 = D, OPEN-H = B; [NES] |
| 22 | Price flag (P2) and latch μ | Recorded independently of time eligibility; independent first-per-episode latch; HF: FALSE at substrate start; not evaluated on no-bar HF sessions. **μ governs P2 only** | [LOD] RQ-3 = C, RQ-4 = A, OPEN-C = A, OPEN-G = A, OPEN-F; [NES] |
| 23 | HF substrate start | λ = μ = FALSE. A candidate whose leg crossing held on a pre-substrate session is **spent for that leg** (no HF event or flag from it; no latch set). Applies to P1/P2. **For P3/P4, every candidate whose active span crosses S_HF is ineligible** (OPEN-I(b) = B-ii), so spent status never reaches P3/P4 | [LOD] RQ-10 = B, OPEN-B = B, OPEN-G = A, X-2 = A, **OPEN-I(b) = B-ii**; [NES] |
| 24 | Formal contrast (P3, P4) | T(time) − T(price) over **contrast-eligible** candidates: matched (𝒰_T ≠ ∅ ∧ 𝒰_P ≠ ∅) **and** substrate-homogeneous over the active span (all DB or all HF). Formed per profile, never pooled. **P3:** whether TC_M holds in the active span, **independent of λ**; in HF, recognized only at a genuine 1m bar (a no-bar date-level crossing is recognized at the next genuine bar in the span, if any). **P4:** whether PC_M holds in the active span, **independent of μ**; in HF, genuine bars only (OPEN-C). Both are candidate-level underlying conditions, not latch or reporting state. P1 is GF-10's primary score; P3/P4 exist only as R-10's specificity contrast. A candidate still active on the last session of the evaluation sample is **right-censored and excluded** (not 0, not carried). Weekly mapping: OPEN-11 (§3.9). Outcome: **one shared y per stock-week at f_w** (OPEN-L, §3.11). p: G-4. T(·) = T_c formula (**RR-3**). Opposite-direction weeks excluded (**OPEN-N**) | [GS] p. 12 ranking only; [LOD] RQ-3 = C, R-10, OPEN-F (wording; CONF-1 resolved), OPEN-H = B, **OPEN-I(a) = A-ii, OPEN-I(b) = B-ii, OPEN-J, OPEN-11**; [NES] |
| 25 | Move reset | Each qualifying K3 move is an independent candidate | [LOD] C-7 |
| 26 | Outcome | **Score-1 week (primary):** O-R10 per R-2 / G-2(b), anchored to the (first, OPEN-K(c)) P1 event: window = the five NSE sessions after D_e (remainder of D_e excluded); reference = last K3 swing of the G-2(b) type confirmed before the event; prior penetration ⇒ 0; 1 iff first penetration (strictly beyond) falls in the window (§3.10). **Score-0 week and every contrast stock-week:** the same rule at f_w (§3.11). O_5 > Z ⇒ excluded (OPEN-M) | [GS] Rule 10 (a separate rule); [NES]; [LOD] R-2, G-2(b), **OPEN-12a = B, 12b = B, 12c = C, 12d = B**, OPEN-6, **RR-1, RR-2, OPEN-K(b), OPEN-K(c), OPEN-L, OPEN-M** |
| 27 | Weekly score | 1 only in the formation week (ISO) containing the P1 event; **0 iff a qualifying candidate is active on the week's last session D_L and there is no event** (A1), including candidates with 𝒰_T = ∅ and post-event weeks of a latched episode; excluded otherwise; f_w = close(D_L); final-session events belong to that week (§3.9) | [LOD] **OPEN-11, OPEN-K(a) = A1, K(a)-P1, K(a)-P2, CAL-1**, G-2(b); [NES] |
| 28 | Panel rules | At least 20 eligible names per formation date, counted on the A1 set, per profile (G-6); no extra burn-in; full-span exclusion for non-ratio CAs (G-7; §3.12) | Panel rulings G-6, G-7 |
| 29 | Contrast statistic | T(leg) = T_c formula on the leg's score and the shared y (**RR-3**); a contrast stock-week with opposite-direction contributors is excluded (**OPEN-N**) | [LOD] RR-3, OPEN-N; [NES] |

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
| Rule 10 outcome; horizon; pooling; event-anchored window; reference timing; prior-penetration rule | Separate rule | ✔ (R-2, G-2(b), OPEN-12a–d) | ✔ |
| Bar-end timestamps; weekly score mapping; sample-end censoring | — | ✔ (OPEN-6, OPEN-11, OPEN-J) | ✔ |

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
| ts(τ) | Timestamp of 1m bar τ = its **bar end** (start label + 1 minute for the store's start-labelled bars, resolved through `core/market/bar_labeling.py`) | [LOD] OPEN-6 |
| close(D) | End of session D per `core/market/session_schedule.py` (special sessions by date). The DB instant for session D and the bar end of the daily bar | [LOD] OPEN-6 (DB analogue, derived) |
| e = (M, t_e, D_e) | A P1 event: its candidate, timestamp t_e (HF: ts of the event bar; DB: close(D_e)) and session D_e = d(t_e) | [LOD] OD-7, OPEN-6 |
| w; f_w | Formation week (calendar week); formation instant f_w = close of its last NSE session | [LOD] memo §7, OPEN-11 |
| O_k(e) | k-th session of 𝒟 after D_e, k = 1 … 5 | [LOD] R-2, OPEN-12b |
| X_ref(e) = (x_ref, d_ref) | O-R10 reference swing of e: level and first-occurrence date | [LOD] G-2(b), OPEN-12c |
| sample end Z | Last session of the evaluation sample (for the R-12 screen: 2022-12-30) | [LOD] R-12, OPEN-J |

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
  instants: the first such session D (instant = close(D), OPEN-6)

HF-homogeneous M (HF contrast):
  s_T(M) = 1  iff  ∃ τ ∈ 𝒯_M : TC_M(d(τ))                           else 0      (OPEN-I(a) = A-ii)
  s_P(M) = 1  iff  ∃ τ ∈ 𝒯_M : PC_M(τ)                              else 0      (OPEN-C = A, built into PC_M)
  instants: the first such genuine 1m bar τ (OD-7); instant = ts(τ), OPEN-6

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
- **Instants and weekly mapping (OPEN-6, OPEN-11; §3.9).** Every P3/P4 instant is a bar end (HF) or a
  session close (DB). s_T(i, w) = 1 in the week containing the P3 instant; s_P(i, w) = 1 in the week
  containing the P4 instant.
- **Statistic and outcome.** p: G-4 (§3.12). Outcome: one shared y per contrast stock-week by the f_w
  rule (OPEN-L, §3.11); the P3/P4 instants set scores, never the outcome. T(·) = the T_c formula
  (RR-3). A stock-week whose contributing candidates disagree in direction is excluded (OPEN-N).
- **Consistency with P1 (derived).** Every P1 event comes from a matched candidate with s_T = 1 at
  the same instant **if that candidate is contrast-eligible**. A later eligible candidate in the same
  episode can have s_T = 1 with no P1 event (NC-13). An eligible HF candidate whose time condition
  first held on a no-bar session has no P1 event (RQ-11 = D) but can have s_T = 1 at a later genuine
  bar (NC-15).
- **Consistency with P2 (derived).** A P2 flag from an eligible candidate implies s_P = 1 for it. An
  eligible candidate can have s_P = 1 with no P2 flag (μ already set). Unmatched and crossing
  candidates can produce P2 flags but contribute nothing to P4.
- **Sample-end censoring (OPEN-J, LOCKED).** A candidate still active on the last session Z of the
  evaluation sample (u > Z) is right-censored: **excluded from P3 and P4**, not scored 0, not carried
  beyond the sample. A candidate with u ≤ Z is complete. The test "still active at Z" needs only
  sessions ≤ Z (u is a confirmation close, observable when it happens), so OPEN-J reads nothing past
  the sample (derived). P1 and P2 are unchanged.

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


### 3.9 Timestamps and weekly scores (OPEN-6, OPEN-11) — new in v0.7

**Timestamp (OPEN-6).** A 1m bar τ is observable at ts(τ), its bar end: the 09:15–09:16 bar is
timestamped 09:16. Everything inside τ, including its high and low, is dated ts(τ). A DB observation
is a session. The derived bar-end analogue is close(D), which is v0.6's "observable at D's close".

**Clock unit (draft OPEN-8a, closed by derivation).** el_M(D) = cal(D) − cal(d_S) is an integer number
of calendar days fixed for the whole session D (OPEN-4.2/4.4). The time condition TC_M(D) therefore
holds from the session's first bar or not at all. OPEN-6 sets the **instant** at which a crossing is
recognized and the outcome anchor. It never changes the clock unit. HF P1 event: t_e = ts of the
first genuine 1m bar of D*_M (09:16 when the 09:15 bar is genuine). DB P1 event: t_e = close(D*_M).

**Weekly scores (OPEN-11).**

| Score | Value 1 | Value 0 | Excluded | Source population |
|---|---|---|---|---|
| s(i, w): GF-10 primary | A P1 event of stock *i* with t_e ∈ (f_{w−1}, f_w] | *i* eligible in *w* and no P1 event in *w* | *i* not eligible in *w* | **P1 only** |
| s_T(i, w): contrast time | A P3 instant (§3.7) of a CE candidate of *i* in (f_{w−1}, f_w] | per OPEN-11 | not eligible, or the candidate is OPEN-I(b)-crossing or OPEN-J-censored | **P3 only** |
| s_P(i, w): contrast price | A P4 instant of a CE candidate of *i* in (f_{w−1}, f_w] | per OPEN-11 | as s_T | **P4 only** |

- **Persistence A:** the score is 1 only in the week containing the instant. Later weeks of the same
  move or episode do not inherit it.
- **Formation instant:** f_w = close of the last NSE session of calendar week *w* (memo §7; OPEN-11).
  Every bar end on that session is ≤ f_w, so an event anywhere in the final session, including its
  last bar, belongs to *w*. A DB event on the final session has t_e = f_w and also belongs to *w*.
- **Source separation (derived from NC-13, NC-14).** OPEN-11's "event/crossing" is read as: *event* =
  P1 event, for s(i, w); *crossing* = P3/P4 instant, for s_T and s_P. Substituting one for the other
  would break the locked separation of the four populations. **P2 flags are never a score.**
- **A score of 1 is event-based (derived).** It does not re-test eligibility at f_w. A stock whose
  move ended after its event, inside *w*, still scores 1 for *w*.
- **Eligibility of a 0 (OPEN-K(a) = A1).** *i* scores 0 in *w* iff it has no P1 event in *w* and
  E(i, D_L) holds on the week's last NSE session D_L. E(i, D) is PIT membership plus an active candidate
  with (S9 BULL ∧ K3 decline) or (S9 BEAR ∧ K3 rally), read in the D−1-frozen state. Otherwise *i* is
  excluded. Eligibility cannot change inside a session (F-1 of the OPEN-K(a) analysis), so only the
  state on D_L matters. Consequences:
  - a candidate with u = D_L is still active on D_L and counts;
  - a candidate confirmed at c = D_L (first active session in *w*+1) does not.
- **Structural zeros (K(a)-P1, K(a)-P2).** Both of these are eligible, and score 0 when active on D_L:
  - a candidate with 𝒰_T = ∅ (it cannot trigger, by OPEN-1 = A);
  - any week of an episode after its P1 event (λ = TRUE; no further event is possible, by OD-4).

  They are 0s that could not have been 1 (NC-25).
- **Direction of a 0 (derived).** Under A1 the observation's direction is that of the candidate active
  on D_L. S9 is constant within a candidate and only one candidate is active on a session, so the
  direction is unique.
- **Two P1 events in one week (OPEN-K(c)).** The score is 1. The **first** event (smaller t_e) sets the
  direction and anchors O-R10. The later event is recorded, not scored.
- **Calendar (CAL-1).** Weeks are ISO Monday–Sunday. A Sunday session is the last session of its week,
  and f_w is its close.
- **1s and 0s are tested at different instants (disclosed, NC-26).** A 1 is certified at t_e; a 0 is
  tested at D_L.

### 3.10 Outcome of a P1 event (OPEN-12a–d) — new in v0.7

For a P1 event e = (M, t_e, D_e). Bull is shown; bear mirrors with highs and swing highs.

| Element | Definition | Status |
|---|---|---|
| Direction | Bull (S9 BULL, current K3 decline): the reference is a K3 **swing low**. Bear: a K3 **swing high** | LOCKED (G-2(b)) |
| Reference X_ref(e) | The last K3 swing low whose **confirmation close ≤ close(D_e⁻)**, i.e. the swing in the D−1-frozen state on D_e. Level x_ref^(D) on the common basis; first-occurrence date d_ref | LOCKED (OPEN-12c = C) |
| Excluded swings | Any swing confirmed at close(D_e) or later. HF: close(D_e) > t_e, so the swing is confirmed **after** the event. DB: close(D_e) = t_e, so it is confirmed **simultaneously**. OPEN-12c excludes both. The D−1 freeze excludes the same set (derived) | LOCKED (OPEN-12c; C-3) |
| Penetration | A low **strictly below** x_ref (bear: a high strictly above x_ref) on the intraday high/low basis. Equality is not a penetration | R-2 (intraday basis; "any" = any amount); **RR-1 LOCKED (2026-09-19): strict** |
| Prior penetration | A penetration at any observation in (d_ref, t_e]. HF: EOD sessions d_ref < d < D_e, plus genuine 1m bars of D_e with ts ≤ t_e. DB: EOD sessions d_ref < d ≤ D_e | LOCKED (OPEN-12d = B) |
| Window | O_1 … O_5 = the five sessions of 𝒟 after D_e. The remainder of D_e (instants in (t_e, close(D_e)]) is **not** Session 1 | LOCKED (OPEN-12a = B, OPEN-12b = B; R-2) |
| O-R10 | y(e) = 1 iff there is no prior penetration **and** the first penetration after t_e falls in O_1 … O_5. Otherwise y(e) = 0 | LOCKED (OPEN-12d = B; operator formula) |

**Derived — reference identity.** Swing lows are confirmed only at up-switch closes. D_e ∈ A(M) = (c, u],
and K3 has no switch strictly inside (c, u), so M's own swing low is confirmed at close(u) ≥ close(D_e)
and is excluded. The reference is therefore the K3 swing low confirmed at the **last up-switch before
c**, i.e. the swing low immediately preceding M's starting high X⁺. Bear mirror: the swing high
immediately preceding the current rally's starting low. The reference is fixed for all of M, whatever
session the event falls on.

**Derived — existence.** A P1 event needs 𝒰_T(M) ≠ ∅: a completed same-type K3 member of E, completed
≤ d_S. Its end is a K3 swing low confirmed at an up-switch before c. So X_ref(e) exists for every P1
event, and no P1 event has an undefined reference.

**Derived — EOD form.** On a common basis (below), for bull:

```
y(e) = 1  ⇔  min{ L_d : d_ref < d ≤ D_e } ≥ x_ref   ∧   min{ L_d : d ∈ O_1 … O_5 } < x_ref
```

*Proof by cases.* A penetration before D_e, or on D_e at or before t_e, is prior, so y = 0. A penetration
on D_e after t_e (HF only) is the first post-event penetration and falls outside O_1 … O_5, so y = 0.
Otherwise nothing is penetrated through close(D_e), and y = 1 iff some O_k penetrates. D_e's EOD low
covers every trade on D_e, including every genuine 1m low. Consequences:
- y(e) is the **same rule in HF and DB**. 1m data affects y only through which session D_e is.
- The order of events **inside the event bar** is immaterial: everything in it is dated t_e.
- **No 1m bar after t_e is read** for y. The outcome needs EOD bars through O_5 only.

**Derived — basis.** The test compares the reference with later lows. Ratio adjustment multiplies both
sides of every comparison by the same factor, so y is the same on any single ratio-adjusted basis
dated at or after the last ex-date ≤ O_5 (R-13). Whether events with an ex-date inside (d_ref, O_5] are
excluded is imported **G-7**.

**Derived reading — sessions.** "Full trading session" is read as a whole session of 𝒟: the NSE
calendar, including special sessions. It is the same session set K3 counts. "Full" contrasts with the
remainder of D_e. It is not a minimum-length rule.

**"First penetrated" — RR-2 LOCKED (2026-09-19), literal reading (NC-19).** Under the operator's formula, an HF event whose
reference is first broken later **the same session** scores **0**, not 1: that penetration is the first
one after t_e and it lies outside the window. For DB events this case cannot arise, because t_e =
close(D_e).

**Scope.** This section defines O-R10 for the score-1 weeks of the primary score. §3.11 covers score-0
weeks and the contrast; §3.12 covers exclusions (OPEN-M, G-7).

### 3.11 O-R10 for score-0 weeks and for the contrast (OPEN-K(b), OPEN-L) — new in v0.8

**The f_w rule (OPEN-K(b)).** This is §3.10 with the instant t_e replaced by f_w = close(D_L), the
DB-event analogue:

| Element | Definition |
|---|---|
| Direction | The direction of the observation (§3.9 for a 0). A contrast week whose contributing candidates disagree is excluded (OPEN-N) |
| Reference | The last K3 swing of the G-2(b) type with **confirmation close ≤ close(D_L⁻)** |
| Prior penetration | Any penetration (strictly beyond, RR-1) in (d_ref, f_w] gives y = 0 |
| Window | O_1 … O_5 = the five sessions after D_L |
| y | 1 iff there is no prior penetration and the first penetration after f_w falls in O_1 … O_5 |

- **Reference identity (derived, same argument as §3.10).** When the observation's candidate M is
  active on D_L, its own swing is confirmed at close(u) ≥ close(D_L) and is excluded. The reference is
  then the swing immediately preceding M's starting extreme, the same swing a P1 event of M would use.
  If a contrast week's crossing candidate ended before D_L, the reference is the last swing confirmed ≤
  close(D_L⁻). That can be the ended candidate's own swing: the rule is applied as written.
- **Existence (derived; closes the question of whether a first candidate has a reference).** A
  candidate is a member only if S9_c ∈ {BULL, BEAR} (§3.3). S9 BULL requires confirmed, strictly rising
  **bottoms**. Those bottoms are swing lows confirmed at up-switches before c. So a swing low confirmed
  ≤ close(D_L⁻) exists for every eligible bull observation. This includes an episode's first candidate
  (𝒰_T = ∅, K(a)-P1) and a stock whose data begin at 2011-03-25 or at listing. Bear mirror (falling
  tops). **No eligible observation lacks a reference.**
- **EOD form (derived).** y = 1 ⇔ min{L_d : d_ref < d ≤ D_L} ≥ x_ref ∧ min{L_d : d ∈ O_1 … O_5} < x_ref
  (bull). The f_w rule never reads 1m data.

**The contrast's outcome (OPEN-L).**
- Every contrast stock-week (i, w) — s_T = 1 or 0, and s_P = 1 or 0 — uses **one** y(i, w), computed
  by the f_w rule.
- T(time) and T(price) are formed from the same (i, w, y) set and differ only in the score column.
- The P3/P4 instants set the scores (§3.9), never the outcome.
- The contrast never reads P1 (Q-7): its y is computed from the f_w rule, not from the primary's
  event-anchored y.
- A contrast 0 is tested by A1 on contrast-eligible candidates. Unmatched candidates stay out of P3/P4
  (NC-8), so the primary and contrast 0 sets differ by design (NC-13/NC-14).

**Primary score-1 weeks are anchored at t_e, everything else at f_w (disclosed).**
- In the primary score, a 1 uses the event-anchored y (§3.10) and a 0 uses the f_w rule. This mixed
  anchoring is a consequence of OPEN-12a + OPEN-K(b) (NC-26).
- The contrast uses f_w throughout, so for the same stock-week, **y in T(time) can differ from y in
  the primary T_c** (NC-27).

### 3.12 Exclusions and panel rules applied to GF-10 (OPEN-M, G-6, G-7) — new in v0.8

| Rule | Applied to GF-10 |
|---|---|
| **OPEN-M** | Exclude any observation (primary 1 or 0; contrast week) whose O_5 > Z. O_k are counted from D_e (score-1 primary) or D_L (all others) on the NSE calendar alone, so no session after Z is read |
| **G-6a** | No burn-in beyond the state rules. A stock contributes from its first eligible observation; left-censoring labels per R-3 |
| **G-6b** | A formation date enters T_c only if **≥ 20 names** are in the score's population on it: 1s plus A1-eligible 0s. Per profile (DB/HF never pooled). The same floor applies to each contrast leg's per-date set (RR-3) |
| **G-7** | Exclude any observation whose **dependency span** contains a non-ratio CA ex-date. GF-10 span start (the research reading in the rulings file §2, **for operator confirmation at freeze review**): the earliest of d_ref and the start date d_h′ of the earliest member of 𝒰_T ∪ 𝒰_P. The span runs through O_5. For a 0 with 𝒰_T = ∅, the start is d_ref |
| **G-4** | p = (1 + #{b : Δ_b ≥ Δ}) / (B + 1), Δ = T(time) − T(price), B = 1999 joint surrogates, one-sided |

---

## 4. State machine and timeline (per stock; bull shown, bear mirrors)

```text
State (read on D from 𝔉(D), re-based as-of-D):
  K3: ℓ, runs, swing points (first-occurrence), RH and last establishing session, open reaction ρ (if any)
  S9: σ; episode E; λ(E); μ(E)                                   ← λ, μ: operational P1/P2 only
  Ledger(E): K3 members (dur on swing dates; literal mag; terminating close); reactions (mag; completion close)
  Candidate M: (P_S, d_S, c), time-spent flag, price-spent flag, matched?, CE?, s_T(M), s_P(M)
  Profile: DB | HF (from S_HF)                                    ← prof(D); the observation boundary is S_HF
  P1 event record: (M, t_e = bar end / session close, D_e, X_ref), y(e) once O_5 has closed   ← OPEN-6, OPEN-12
```

| Phase | What happens | Locks |
|---|---|---|
| **A. UP line** | Update RH. A session with H > RH (strict) is an establishing session e (the up-switch close establishes the first RH). If e⁺ is LL, ρ opens with Top = H_e; an outside-day LL session continues ρ normally (it raises RH for later reactions only). A 2nd LL session is ρ's 2nd session; a 3rd consecutive LL makes the run a K3 switch (ρ discarded). On the first non-LL close, ρ completes; if a BULL E is open it enters Ledger(E) | OPEN-2.x; RQ-6/7; OPEN-D/E; RQ-1 |
| **B. Down-switch close c** | X⁺ confirmed; S9 recomputed. On a change, E closes (ledger, λ, μ discarded) and a new E may open at c. If S9_c = BULL, M is a candidate member (SC-3 even when d_S < a). 𝒰_T and 𝒰_P fixed from members completed ≤ d_S; R_T on K3 swing dates; R_P = combined maximum of literal magnitudes. M is **matched** iff 𝒰_T ≠ ∅; s_T(M) = s_P(M) = 0 initially. Its contrast profile is provisionally prof(c⁺) | R-1; OPEN-3b; SC-3; RQ-1/2/5/8; OPEN-A; RQ-3 |
| **C. Active session D ∈ (c, u]** | **P1 (time, operational):** ¬λ ∧ 𝒰_T ≠ ∅ ∧ el > R_T (∧ HF: D ≥ S_HF, not time-spent) → DB: event at D; HF with G(D): event at the first genuine bar; HF without G(D): no event (RQ-11 = D). Each sets λ := TRUE. **P2 (price, operational):** HF with ¬G(D): skipped (μ unchanged). Otherwise if ¬μ ∧ 𝒰_P ≠ ∅ ∧ run > R_P (∧ HF: not price-spent) → flag (HF: the genuine bar; DB: D's close); μ := TRUE. Recorded whether or not M is matched or eligible. **P3/P4 (contrast, matched M only; λ and μ not read):** DB session: if TC_M(D), s_T(M) := 1; if run_M(D) > R_P, s_P(M) := 1. HF session with G(D): if TC_M(D), s_T(M) := 1 at D's first genuine bar; if PC_M(τ) at a genuine τ, s_P(M) := 1. HF session with ¬G(D): no P3/P4 update (A-ii; OPEN-C); a date-level TC_M crossing here is recognized at the next genuine bar in A(M). New lows extend run; no clock reset; no termination on a new high | OD-7/8/9; OPEN-4.x; RQ-3/4/8/9/11; OPEN-B/C; OPEN-H = B; OPEN-F; **OPEN-I(a) = A-ii** |
| **D. Up-switch close u** | M active on u, ends after it. **CE(M) is determined**: TRUE iff M is matched and prof is constant over (c, u]. If CE(M), s_T(M) and s_P(M) are final in the contrast of prof(A(M)); otherwise M is excluded from P3/P4 and any provisional scores are discarded. **If the sample ends first (M active on Z, u > Z), M is right-censored and excluded from P3/P4 (OPEN-J)**; P1/P2 output already emitted stands. If E continues, M enters the ledger: dur = cal(d_l) − cal(d_h); mag = literal minimum over (d_h, u] | OPEN-4.3; RQ-8; OPEN-A; **OPEN-I(b) = B-ii** |
| **E. Latches** | λ = TRUE stops GF-10 events (P1) in E. μ = TRUE stops recorded price flags (P2) in E. They are independent. **Neither affects P3 or P4** | OD-4/6; RQ-4; RQ-11; OPEN-H = B; OPEN-F |
| **F. S9 reset** | E closes; ledger, λ and μ discarded; new E with an empty ledger and λ = μ = FALSE; SC-3 joins; RQ-1 exclusion. P3/P4 are per-candidate and carry no episode state | OD-5; SC-3; RQ-1 |
| **G. HF substrate start S_HF** | For every open episode: λ := FALSE, μ := FALSE. Each active candidate is checked per leg on EOD-era sessions: a time crossing before S_HF → time-spent; an EOD price crossing before S_HF → price-spent. Spent legs emit nothing into P1/P2 and set no latch; unspent legs and later candidates proceed normally. **Every candidate active on both S_HF⁻ and S_HF (spent or not) is marked crossing: CE(M) = FALSE**, excluded from P3/P4; its P1/P2 treatment is unchanged. Candidates confirmed at c ≥ S_HF⁻ (first active session ≥ S_HF) are HF-homogeneous | RQ-10 = B; OPEN-G = A; OPEN-B = B; X-2 = A; **OPEN-I(b) = B-ii** |
| **H. Formal contrast** | Over complete candidates with CE(M), per profile (HF and DB never pooled): **P3** = s_T(M), from TC_M, independent of λ, HF-observable only at genuine bars; **P4** = s_P(M), from PC_M, independent of μ. T(time) − T(price) is computed from P3/P4 **only**, never from P1 or P2. Instants are bar ends / session closes (OPEN-6); weekly mapping per §3.9 (OPEN-11); censored candidates excluded (OPEN-J). Statistic and p: imported G-4. Outcome input: **OPEN-L** | RQ-3 = C; R-10; OPEN-F (CONF-1 resolved); OPEN-H = B; **OPEN-I(a) = A-ii; OPEN-I(b) = B-ii; OPEN-6; OPEN-11; OPEN-J**; X-2; G-4 |
| **I. Outcome of a P1 event** | At the event: fix t_e (bar end / session close), D_e and X_ref = the last swing of the G-2(b) type confirmed ≤ close(D_e⁻) (bull: the swing low preceding X⁺). Test prior penetration over (d_ref, t_e]; if found, y = 0. Otherwise skip the remainder of D_e; if the first penetration after t_e falls in O_1 … O_5, y = 1, else y = 0. y is final at close(O_5). Nothing in phases A–H reads y | R-2; G-2(b); **OPEN-12a = B, 12b = B, 12c = C, 12d = B**; OPEN-6; C-3; RR-1; RR-2 |
| **J. Week close f_w (ISO week)** | Primary: s(i, w) = 1 if a P1 event fell in *w* (the first one anchors, OPEN-K(c)); else 0 if a qualifying candidate is active on D_L (A1, incl. 𝒰_T = ∅ and latched episodes); else excluded. Contrast: s_T, s_P from P3/P4 instants in *w*; 0 by A1 on contrast-eligible candidates. For every observation except a primary 1: y by the f_w rule (§3.11). Drop the observation if O_5 > Z (OPEN-M) or its dependency span holds a non-ratio ex-date (G-7). Drop the date if fewer than 20 names remain (G-6b) | OPEN-11; OPEN-K(a)/(b)/(c); K(a)-P1/P2; OPEN-L; OPEN-M; CAL-1; G-6; G-7 |

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

P1 event and its outcome (OPEN-6, OPEN-12a–d), HF, bull:
  close(u₀): up-switch confirms swing low X⁻ (x_ref, d_ref)       ← reference established
  close(c):  down-switch confirms X⁺; M formed                    ← candidate forms (after u₀)
  D_e 09:15–09:16 genuine bar, TC_M(D_e) first true → t_e = 09:16  ← event; λ := TRUE
  prior: any low < x_ref in (d_ref, 09:16 on D_e]? → y = 0
  09:16 → close(D_e): not in the window; a first break here → y = 0 (NC-19)
  O_1 … O_5 (next five sessions): first break here → y = 1; none → y = 0
  same event in DB: t_e = close(D_e); prior test covers all of D_e; window identical

Event in the final session of week w (OPEN-11):
  last session of w, 15:29–15:30 bar → t_e = 15:30 = f_w → s(i, w) = 1; s(i, w+1) = 0 or excluded
  O_1 … O_5 fall in week w+1 and later

Two eligible matched candidates in one episode (OPEN-H = B, OPEN-F):
  M₁: TC holds → P1 event, λ := TRUE; s_T(M₁) = 1
  M₁: PC holds → P2 flag, μ := TRUE; s_P(M₁) = 1
  M₂ (later): TC holds → no P1 event (λ TRUE); s_T(M₂) = 1
  M₂: PC holds → no P2 flag (μ TRUE); s_P(M₂) = 1
  Contrast sees both candidates on both legs
```

---

## 5. OPEN items

### 5.1 Resolved before v0.8 (historical record)

| Item | Resolution | Version |
|---|---|---|
| CONF-1; OPEN-H | Wording of OPEN-F authoritative; OPEN-H = B | v0.5 |
| OPEN-I(a), OPEN-I(b) | A-ii; B-ii | v0.6 |
| OPEN-6, OPEN-11, OPEN-J, OPEN-12a–d; draft OPEN-8a | Locked; OPEN-8a closed by derivation | v0.7 |

### 5.2 Resolved in v0.8 (operator rulings of 2026-09-19)

| Item | v0.7 status | v0.8 resolution |
|---|---|---|
| OPEN-K(a) | Open | **A1** (§3.9) |
| K(a)-P1, K(a)-P2 | Open (OPEN-K(a) analysis §5) | **Eligible → 0** (§3.9) |
| OPEN-K(b) | Open | **OPEN-12 at f_w** (§3.11) |
| OPEN-K(c) | Open | **First event** (§3.9) |
| OPEN-L | Open | **Shared f_w outcome** (§3.11) |
| OPEN-M | Open | **Exclude O_5 > Z** (§3.12) |
| RR-1, RR-2 | Ratification requested | **Strict; literal** (§3.10) |
| CAL-1 (v0.7 §5.5) | Open | **ISO Monday–Sunday** (§3.9) |

### 5.3 Surfaced by the v0.8 audit — both ruled 2026-09-19

| Item | Issue | Ruling |
|---|---|---|
| **OPEN-N** | OPEN-L gives each contrast stock-week one y, which needs one direction. If S9 changes inside *w*, the P3 instant, the P4 instant and the A1 state on D_L can belong to opposite-direction candidates. OPEN-K(c) covers P1 only, and the contrast may not read P1 | **Exclude** such stock-weeks from the contrast. Not chosen: the first contrast instant; the A1 state on D_L. [LOD]; [NES] |
| **RR-3** | R-10 names T(time) − T(price); G-4 fixed its p; no text defined T(·) | **Ratified:** T(leg) = the T_c formula (memo §8.2), computed on s_leg(i, w) and the shared y(i, w), per profile, with the G-6b 20-name floor. [LOD] |

**Derived.**
- OPEN-N's exclusion is decided from the week's candidate directions alone. It reads no outcome.
- It applies to the contrast only. The primary score is unaffected (A1 + OPEN-K(c)).
- A stock-week excluded from the contrast by OPEN-N stays in the primary if the primary rules admit
  it. The populations already differ by design (NC-13/NC-14).

### 5.4 Imported (not GF-10 definitions)

- **Surrogate layer, ruled 2026-09-19:** G-5 (nearest bar in block), G-8 (seed 42), G-9 (full B per
  construct; failure stops the construct).
- **Tasks:** P-2 external CA enumeration (authorized; needed to apply G-7), P-3 code, P-4 G-S1
  (operator), P-5 freeze approval; checklist items 12, 13, 16.
- **Confirmation at freeze review:** the per-construct G-7 span start (§3.12).

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
| 6.10 | Matched contrast | **RESOLVED:** P3 independent of λ (OPEN-H = B); P4 independent of μ (OPEN-F); HF observability symmetric at genuine bars (OPEN-I(a) = A-ii); substrate-homogeneous eligibility (OPEN-I(b) = B-ii); sample-end censoring (OPEN-J). Four populations distinct (§3.7). **Outcome: shared f_w y (OPEN-L, v0.8); opposite-direction weeks excluded (OPEN-N); T(·) = T_c formula (RR-3)** |
| 6.11a | Timestamps and weekly scores | **RESOLVED** (OPEN-6, OPEN-11; §3.9). Score-0 eligibility and outcome: **RESOLVED v0.8** (A1; OPEN-K(b)) |
| 6.12 | P1 outcome | **RESOLVED** (OPEN-12a–d; §3.10). Windows past the sample end: **excluded (OPEN-M, v0.8)** |

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
| NC-18 | OPEN-12d = B: a bull decline long enough to overbalance in time may already have broken the preceding swing low (X_ref) before the time crossing. Such an event has y = 0 **by construction**. This caps the attainable association mechanically. It is a design consequence, never a defect to be "fixed" after results (§8) |
| NC-19 | Literal "first penetrated" (§3.10): an HF event whose reference first breaks later the same session scores 0. The operator's formula states this; it cannot arise in DB |
| NC-20 | RQ-11 = D × OPEN-11: an HF time crossing first true on a no-bar session produces no P1 event, so the week scores 0 (if eligible). λ is set, so no later P1 event occurs in that episode |
| NC-21 | OPEN-I(a) = A-ii × OPEN-11: the P3 instant, and so the week with s_T(i, w) = 1, can be later than the week of D*_M |
| NC-22 | GF-10's outcome is anchored to its event (OPEN-12a). GF-1 and GF-4T/R8 keep the formation-anchored O-R10 of memo §7. The primaries already use different direction anchors (G-2 recorded observation); they now also use different window anchors |
| NC-23 | A mid-week event's window can start before f_w. s(i, w) is fixed at t_e and depends on nothing after t_e, so this is not look-ahead in the predictor. Its timing difference against score-0 observations (anchored at f_w) is disclosed as NC-26 |
| NC-24 | X_ref can predate the episode start and S_HF. It is an EOD swing point, and HF may use EOD lookback (X-1 = A); its use does not make an HF event DB-era |
| NC-25 | **Persistence asymmetry of the 0s.** A 1 appears once per episode (OD-4, persistence A). Under A1 + K(a)-P2, the same episode then contributes a 0 in **every** later week in which a candidate is active on D_L. Under K(a)-P1, each episode's first candidate contributes 0s in every week it is active on D_L. Both are structural zeros that could not have been 1. The report template (checklist item 13) must disclose them. They are never to be revised after results (§8) |
| NC-26 | **Mixed anchoring in the primary score.** 1s: O-R10 at t_e (the window starts the session after D_e). 0s: O-R10 at f_w (the window starts after D_L). A mid-week event's window can therefore begin up to four sessions earlier than a same-week 0's |
| NC-27 | **Contrast y ≠ primary y.** The contrast uses the f_w rule for every stock-week (OPEN-L). The primary uses t_e for its 1s. For a stock-week holding both a P1 event and a P3 instant, T_c and T(time) can therefore use different y |
| NC-28 | **The G-6b floor is counted on the A1 set.** Under A1 the per-date population is the stocks active on D_L plus the week's 1s. That is the narrowest of the OPEN-K(a) readings. Whether a date meets 20 names is decided by the rule; its frequency may not inform any definition (§8) |

---

## 7. Internal-consistency audit (v0.8)

### 7.1 Result

**v0.8: PASS. No contradiction among the 72 GF-10 locks.** The 2026-09-19 rulings are consistent with
one another and with every v0.7 lock.
- **72 locks** = the 62 of v0.7 plus OPEN-K(a), K(a)-P1, K(a)-P2, OPEN-K(b), OPEN-K(c), RR-1, RR-2,
  OPEN-L, OPEN-N and RR-3.
- OPEN-M, CAL-1 and G-4 … G-9 are panel-level rulings. They are applied and cited here but not counted.
- The audit surfaced **OPEN-N** (contrast direction when legs disagree) and **RR-3** (T(·)). The
  operator ruled both the same day: exclude; ratified.

**Coherence statement.**
- **Primary score (GF-10's T_c): mechanically coherent and complete at the definitional level.** Every
  stock-week has an eligibility rule (A1), a score (OPEN-11), a unique direction (A1 / OPEN-K(c)), a
  reference that exists (§3.11), an O-R10 (§3.10 / §3.11), and exclusion rules (OPEN-M, G-7, G-6b).
- **Contrast (R-10): mechanically coherent and complete at the definitional level** (OPEN-N, RR-3
  ruled).
- The only item left for operator confirmation is the GF-10 G-7 span start (§3.12).

### 7.2 Checks added for v0.8

| ID | Check | Result |
|---|---|---|
| S-1 | A1 vs OPEN-11 / OPEN-K(c) | Consistent. A 1 is event-based (any t_e in *w*). A 0 is tested at D_L. A1 and OPEN-K(c) each give a unique direction |
| S-2 | A1 vs the D−1 freeze and OPEN-4.3 (A(M) = (c, u]) | Consistent. E(i, D_L) is read from the frozen state on D_L, so u = D_L counts and c = D_L does not (§3.9) |
| S-3 | K(a)-P1 vs OPEN-1 = A / NC-8 | Consistent. "Cannot trigger" constrains events, not eligibility. The candidate is a primary 0 and stays out of P3/P4 (unmatched) |
| S-4 | K(a)-P2 vs OD-4 / λ | Consistent. λ governs P1 events only (v0.5 scope). Eligibility never reads λ |
| S-5 | OPEN-K(b) vs OPEN-12b/c/d | Consistent. It is the DB-event analogue: the reference is confirmed ≤ close(D_L⁻), prior penetration runs over (d_ref, f_w], the window is after D_L |
| S-6 | OPEN-K(b) — existence of the reference | PASS. S9 BULL/BEAR requires confirmed bottoms/tops before c (§3.11). Holds for 𝒰_T = ∅ and at data start |
| S-7 | OPEN-L vs Q-7 (the contrast never reads P1) | Consistent. The shared y comes from the f_w rule, not from P1. Direction when legs disagree: excluded (OPEN-N) |
| S-8 | OPEN-L vs G-4 | Consistent. Δ is formed from one (i, w, y) set with two score columns; the surrogate panels recompute both legs on the same y definition. T(·) = T_c formula (RR-3) |
| S-9 | RR-1 vs OD-9 / R-2 | Consistent. Strictness is now ruled (no longer a derived reading) |
| S-10 | RR-2 vs the EOD form (§3.10) | Consistent. The EOD form and the profile invariance of y rest on the literal reading, which is now locked |
| S-11 | OPEN-M vs OPEN-J | Consistent and parallel. Both exclude, both are decided without a read past Z. OPEN-J governs candidate spans in P3/P4, OPEN-M outcome windows everywhere |
| S-12 | G-6b vs A1 | Consistent. The floor is counted on the A1 population per profile (NC-28) |
| S-13 | G-7 vs X-1 (EOD lookback) and OPEN-I(b) | Consistent. G-7 is an exclusion over the dependency span and does not change any profile rule. The span start is pending operator confirmation (§3.12) |
| S-14 | CAL-1 vs OPEN-11 formation instant | Consistent. A Sunday session is D_L of its ISO week |
| S-15 | Look-ahead under the new rulings | PASS. A1 reads only the D−1-frozen state on D_L, i.e. information from closes ≤ D_L⁻. The f_w rule reads (d_ref, f_w] as the prior span and O_1 … O_5 only as the outcome. OPEN-M reads the calendar only. G-7 reads CA metadata only |
| S-16 | P1/P2 vs P3/P4 contamination under the new rulings | PASS. The primary 0s never read P3/P4. The contrast never reads P1 or P2. K(a)-P2 reads the **eligibility** of a latched episode, not λ's value as a score |

### 7.3 Checks required by the v0.7 handoff (re-verified under v0.8)

| ID | Check | Result |
|---|---|---|
| Q-1 | **Look-ahead** | PASS for P1 and the weekly score. The event uses the D−1 freeze plus genuine 1m bars ≤ t_e. The reference is confirmed ≤ close(D_e⁻). s(i, w) is fixed at t_e ≤ f_w. y uses sessions after D_e only as the outcome. Prior penetration reads only (d_ref, t_e]. OPEN-J reads nothing past Z (§3.7). **No price movement at or before t_e can make y = 1**: a prior penetration forces 0, and a same-session post-event break forces 0 (NC-19). Retrospective CE(M) and OPEN-J are accepted as contrast-only (operator principle; they never feed P1) |
| Q-2 | **Timestamp ordering** | PASS. Strict order: close(u₀) [reference] < close(c) [candidate] < t_e ≤ close(D_e) < O_1. close(u₀) < close(c) because K3 switches alternate and never share a close. t_e > close(c) because D_e ≥ c⁺. t_e ≤ f_w for the week containing D_e. One convention throughout: bar end (HF) and session close (DB). Intra-bar order is immaterial because everything inside the event bar is dated t_e (§3.10). The clock unit is unaffected (§3.9, draft OPEN-8a) |
| Q-3 | **Event/outcome overlap** | PASS. The event session D_e is never an outcome session (12b), and anything on D_e is either prior (0) or outside the window (0). Windows of successive events of one stock cannot overlap within an episode (one P1 event per episode). They can overlap across episodes, which is a statistical dependence (AC₁ handling, R-14 statistic), not a mechanical ambiguity |
| Q-4 | **Reference-swing confirmation timing** | PASS. 12c and the D−1 freeze select the same swing set (confirmation close ≤ close(D_e⁻)). HF: a swing confirmed at close(D_e) is after t_e. DB: it is simultaneous with t_e. Both are excluded. Derived: the reference is the swing preceding X⁺, fixed for the whole candidate, and it exists for every P1 event (§3.10) |
| Q-5 | **Incomplete-window treatment** | **PASS (v0.8).** Candidate spans at the sample end: OPEN-J. Every observation with O_5 > Z: excluded (OPEN-M), decided from the calendar alone. A reference exists for every eligible observation (§3.11), so no window is incomplete for lack of one |
| Q-6 | **HF/DB boundary leakage** | PASS. y is an EOD-only rule, identical in both profiles (§3.10 EOD form), so a window crossing S_HF reads no profile-specific data. The event's profile is set by D_e (X-1/X-2). An HF event may use a pre-S_HF reference swing (NC-24). OPEN-J and OPEN-11 do not change CE(M), so crossing candidates stay out of P3/P4. Weekly scores are formed per population, and HF and DB are never pooled (C-2) |
| Q-7 | **P1/P2 vs P3/P4 contamination** | PASS. s(i, w) reads P1 only. s_T and s_P read P3 and P4 only. P2 is never a score (§3.9). OPEN-12 defines y for P1 events only and is not applied to P3/P4 instants by default (§3.7, OPEN-L). OPEN-J excludes P3/P4 candidates and leaves P1/P2 output byte-unchanged. NC-13/NC-14/NC-20/NC-21 record where counts legitimately differ |

### 7.4 v0.7 locks vs prior locks (re-verified)

| ID | Check | Result |
|---|---|---|
| Z-1 | OPEN-6 vs OD-7 | Consistent: the first observable instant of a bar is its end |
| Z-2 | OPEN-6 vs OPEN-4.2/4.4 (calendar-day clock) | Consistent: OPEN-6 sets instants, not the clock (§3.9) |
| Z-3 | OPEN-6 vs RQ-11 = D / OPEN-C / A-ii | Consistent: the genuine-bar rules pick *which* bar; OPEN-6 dates it |
| Z-4 | OPEN-6 vs DB (X-1) | Consistent: the DB analogue is close(D), already v0.6's DB instant |
| Z-5 | OPEN-11 vs OD-7 / C-6 | Consistent: the event is never deferred. f_w is a sampling instant only |
| Z-6 | OPEN-11 vs OD-4 / λ | Consistent: at most one P1 event per episode gives at most one score-1 week per episode per stock (several episodes in one week: OPEN-K(c)) |
| Z-7 | OPEN-11 vs OPEN-H = B / OPEN-F / A-ii | Consistent: contrast scores come from P3/P4 instants. Weeks can differ from P1's (NC-21) |
| Z-8 | OPEN-11 vs G-2(b) (ineligible ≠ 0) | Consistent: "excluded = not eligible" restates G-2(b). The eligibility instant for 0s is OPEN-K(a) |
| Z-9 | OPEN-J vs OPEN-I(b) = B-ii | Consistent: both are P3/P4 eligibility rules decided per candidate. A candidate may fail either |
| Z-10 | OPEN-J vs OPEN-H = B (existential scores) | Consistent: censoring removes truncated spans instead of scoring them 0, so there is no truncation bias |
| Z-11 | OPEN-J vs P1/P2 | Consistent: explicitly unchanged |
| Z-12 | OPEN-12a vs C-6 / OD-7 | Consistent: the window follows the event, not the week-end |
| Z-13 | OPEN-12a vs memo §7 ("next 5 sessions" after formation) | **Supersession for GF-10 events** (like C-6). The memo text still defines GF-1/GF-4T/R8 (NC-22). For GF-10's score-0 observations the anchor is f_w with the OPEN-12 prior-penetration rule (OPEN-K(b), v0.8) |
| Z-14 | OPEN-12b vs OPEN-6 | Consistent: bar-end observability, then the window starts at the next session |
| Z-15 | OPEN-12c vs D−1 freeze (C-3) and OPEN-3b | Consistent: same selected set (Q-4) |
| Z-16 | OPEN-12c vs G-2(b) ("last completed swing direction") | Consistent: 12c fixes timing, G-2(b) fixes the type |
| Z-17 | OPEN-12d vs R-2 ("any penetration", intraday basis) | Consistent: 12d adds only the ordering condition. Strictness is a derived reading (§3.10) |
| Z-18 | OPEN-12d vs OPEN-12b | Consistent. The remainder of D_e is neither prior nor window, and a break there gives 0 under the literal formula (NC-19) |
| Z-19 | OPEN-12 vs RQ-11 = D | Consistent: a no-bar crossing produces no P1 event, so there is nothing to anchor. A-ii's deferral is P3-only, so no P1 event lands on a deferred bar |
| Z-20 | OPEN-12 vs R-13 / RQ-9 basis | Consistent: y is basis-invariant on any single ratio-adjusted basis dated at or after the last ex-date ≤ O_5 (§3.10). CA exclusion stays G-7 |

### 7.5 Checks required by the v0.6 handoff (re-verified)

| ID | Check | Result |
|---|---|---|
| W-1 | No locked decision contradicts another | PASS (§7.8 register) |
| W-2 | OPEN-I(a) does not alter P1 / RQ-11 | PASS. §3.8 row "HF no-bar time crossing" keeps no-event + λ := TRUE and states the A-ii deferral applies to P3 only. §4 C lists P1 and P3 separately. Divergence disclosed (NC-15) |
| W-3 | OPEN-I(b) does not alter P1/P2 | PASS. §3.7 P1/P2 rows state "includes crossing candidates" / "whether or not … contrast-eligible". §3.8 eligibility row: "Its P1/P2 treatment is exactly the preceding rows". §4 G keeps the spent-leg rules for P1/P2 |
| W-4 | P3/P4 remain latch-independent | PASS. §3.7 formulation contains no λ or μ term; §3.8 "Latch scope"; §4 C "λ and μ not read"; §4 E |
| W-5 | λ and μ not consulted by P3/P4 | PASS (as W-4). CE(M) is built from 𝒰_T and prof only; neither reads a latch |
| W-6 | HF and DB not pooled | PASS. CE assigns each eligible candidate to exactly one profile; crossing candidates are in neither; §3.8 "DB end / separation"; §4 H "per profile" |
| W-7 | Observation boundary explicit | PASS. prof(D) in §3.1; homogeneity classes in §3.7 (u < S_HF / c⁺ ≥ S_HF / crossing); §4 state line and phase G; NC-17 |
| W-8 | Ledger ↔ state machine agreement | PASS. OPEN-I(a) = A-ii is applied in §4 C/H and in ledger §3.7/§3.8/§4 C; OPEN-I(b) = B-ii in §4 B/D/G/H and in ledger §3.7/§3.8/§4 D/G. Every ledger "Applied in" cell was checked against its target |
| W-9 | No unresolved OPEN-I reference | PASS. Text scan: OPEN-I appears only as "OPEN-I(a) = A-ii", "OPEN-I(b) = B-ii", "OPEN-I is fully RESOLVED", in §5.2 (resolved table), in the change log, and in historical v0.5 rows (e.g. v0.5 OPEN-I(a) in §3.7's symmetry note) |

### 7.6 Checks carried from v0.5 (re-verified)

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

### 7.7 Checks added for v0.6 (re-verified)

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

### 7.8 Lock-by-lock register (72)

**Unaffected** means v0.7 does not change the text that applies it. **Scoped** means its text says it
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
| v0.7 | OPEN-6 | Consistent (Z-1 … Z-4, Q-2) |
| v0.7 | OPEN-11a, OPEN-11e, OPEN-11f | Consistent (Z-5 … Z-8, Q-7) |
| v0.7 | OPEN-J | Consistent (Z-9 … Z-11, Q-1) |
| v0.7 | OPEN-12a, 12b, 12c, 12d | Consistent (Z-12 … Z-20, Q-1 … Q-4) |
| v0.8 | OPEN-K(a) = A1, K(a)-P1, K(a)-P2, OPEN-K(c) | Consistent (S-1 … S-4) |
| v0.8 | OPEN-K(b), OPEN-L, OPEN-N, RR-3 | Consistent (S-5 … S-8) |
| v0.8 | RR-1, RR-2 | Consistent (S-9, S-10) |

Count: 43 (v0.3) + 7 (OPEN-A … OPEN-G) + 1 (OPEN-H) + 2 (OPEN-I(a), OPEN-I(b)) + 9 (OPEN-6; OPEN-11a,
11e, 11f; OPEN-J; OPEN-12a, 12b, 12c, 12d) = **62**. The ledger (§9) has fewer rows than locks because
C-1/C-2/C-3 share one row and OPEN-11's three parts share one row. v0.8 adds 10: OPEN-K(a), K(a)-P1, K(a)-P2, OPEN-K(b), OPEN-K(c), RR-1, RR-2, OPEN-L, OPEN-N, RR-3 = **72**.

v0.7 changes the text applying OD-7, C-3 and G-2(b) only by adding cross-references (§1.2-19/20/26,
§3.10). Their content is unchanged.

### 7.9 Items exposed by the v0.7 audit (historical; all ruled 2026-09-19)

- **OPEN-K, OPEN-L, OPEN-M** (§5.3). None is created by a v0.7 ruling's content. All three follow from
  OPEN-12a = B anchoring O-R10 to a P1 event, which leaves observations without a P1 event, and windows
  past Z, undefined. OPEN-M was already flagged in the spec draft (§16 X16).
- **Deliberately not raised as open** (resolved by derivation or by an existing lock, §3.9–§3.10):
  - intra-bar ordering in the event bar;
  - the DB timestamp;
  - the clock unit;
  - the existence of the reference;
  - swings confirmed at close(D_e);
  - the remainder of D_e;
  - HF/DB outcome equivalence;
  - basis across an ex-date (invariance derived; exclusion is G-7);
  - special sessions as outcome sessions.
- **Two ratification requests** (RR-1 penetration strictness; RR-2 the literal "first penetrated",
  NC-19), §5.3. These are readings of locked text that change y; they are not new decisions.

---

## 8. Future work — what empirical testing must NOT decide

**Definitional (before any data read; never from results):**
- None open. Any later change to a lock in §9 is a new version, made before any data read.
- Every lock in §9, including:
  - NC-18: an event already past its reference scores 0 by design, and must never be re-defined after
    seeing how often it happens;
  - NC-25: the structural zeros from K(a)-P1/P2, likewise.
- Any later threshold, window, adjacency or source rule.

No choice may be justified by event counts, coverage, "too few/many events", IC, Sharpe, surrogate p,
contrast p, size-check outcome or any O-R10 association. This includes counts of P3/P4 candidates
excluded by OPEN-I(b) = B-ii or OPEN-J, the share of events with y = 0 by prior penetration (NC-18),
or the number of windows cut by the sample end (OPEN-M), the number of structural zeros (NC-25), the
number of dates below the 20-name floor (NC-28), or the number of observations excluded by G-7.

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
- First-occurrence ties.
- **OPEN-6:** bar-end timestamps from the start-labelled store via `bar_labeling.py`. DB instant =
  close(D) from `session_schedule.py`. A test must show that a final-session event is assigned to its
  own week (t_e ≤ f_w).
- **OPEN-11:** s(i, w) is built from P1 only and s_T/s_P from P3/P4 only. A test must show that
  deleting all P2 flags changes no score.
- **OPEN-J:** a test must show a candidate active on Z is absent from P3/P4 and that no session > Z is
  read to decide it.
- **OPEN-12:**
  - reference = the swing preceding X⁺ (bull) or X⁻ (bear);
  - a swing confirmed at close(D_e) is never used;
  - the remainder of D_e is not Session 1;
  - a prior penetration gives 0;
  - an HF same-session post-event break gives 0;
  - the EOD form (§3.10) equals the event-level definition on constructed cases;
  - y reads no 1m bar after t_e.

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
| **OPEN-6** | Formal timestamp = bar end (1m); DB analogue = session close (derived) | **LOCKED (v0.7)** | §1.2-19/20; §3.1 ts, close; §3.9; §4 I; Z-1 … Z-4 |
| **OPEN-11** (a, e, f) | Score 1 only in the week containing the event/crossing (persistence A); 0 = eligible, no event; excluded = not eligible; f_w = close of the week's last trading session; final-session events belong to that week | **LOCKED (v0.7)** | §1.2-27; §3.9; §4 H; Z-5 … Z-8 |
| **OPEN-J** | P3/P4 candidate incomplete at the sample end: right-censored, excluded; not 0; not carried. P1/P2 unchanged | **LOCKED (v0.7)** | §1.2-24; §3.7; §4 D/H; Z-9 … Z-11 |
| **OPEN-12a = B** | O-R10 window anchored to the actual P1 event timestamp | **LOCKED (v0.7)** | §1.2-26; §3.10; §4 I; Z-12/13 |
| **OPEN-12b = B** | Remainder of the event session is not Session 1; the next session is | **LOCKED (v0.7)** | §3.10; §4 I; Z-14 |
| **OPEN-12c = C** | Reference = last K3 swing completed/confirmed before the event; none confirmed with or after it | **LOCKED (v0.7)** | §3.10; §4 I; Z-15/16 |
| **OPEN-12d = B** | Penetration on or before t_e ⇒ 0; 1 requires the first penetration strictly after t_e within the five sessions | **LOCKED (v0.7)** | §3.10; §4 I; Z-17/18 |
| **OPEN-K(a) = A1** | A stock without a P1 event is eligible iff a qualifying candidate is active on D_L (D−1-frozen state) | **LOCKED (v0.8)** | §1.2-27; §3.9; S-1, S-2 |
| **K(a)-P1** | 𝒰_T = ∅ candidate: eligible → 0 | **LOCKED (v0.8)** | §3.9; S-3; NC-25 |
| **K(a)-P2** | Post-event weeks of a latched episode: eligible → 0 | **LOCKED (v0.8)** | §3.9; S-4; NC-25 |
| **OPEN-K(b)** | O-R10 of a 0 = OPEN-12b/c/d at f_w | **LOCKED (v0.8)** | §1.2-26; §3.11; S-5, S-6 |
| **OPEN-K(c)** | Two P1 events in one week: the first anchors | **LOCKED (v0.8)** | §3.9; S-1 |
| **RR-1** | Penetration strictly beyond | **LOCKED (v0.8)** | §3.10; S-9 |
| **RR-2** | Literal "first penetrated" | **LOCKED (v0.8)** | §3.10; S-10; NC-19 |
| **OPEN-L** | One shared y per contrast stock-week at f_w | **LOCKED (v0.8)** | §1.2-24; §3.11; S-7, S-8; NC-27 |
| OPEN-M | Exclude O_5 > Z (panel ruling, applied) | RULED 2026-09-19 (panel) | §3.12; S-11 |
| CAL-1 | ISO Monday–Sunday (panel ruling, applied) | RULED 2026-09-19 (panel) | §3.9; S-14 |
| G-4, G-6, G-7 | p formula; no extra burn-in, min 20 names; full-span CA exclusion (panel rulings, applied) | RULED 2026-09-19 (panel); G-7 span start for confirmation | §3.12; S-8, S-12, S-13 |
| **OPEN-N** | Contrast stock-week with opposite-direction contributing candidates: excluded | **LOCKED (v0.8)** | §1.2-24/29; §3.11; §5.3 |
| **RR-3** | T(leg) = T_c formula on the leg's score and the shared y, per profile, 20-name floor | **LOCKED (v0.8, ratified)** | §1.2-29; §3.12; §5.3 |

## 10. Remaining decisions and tasks

| Step | Item | Owner |
|---|---|---|
| 1 | G-7 span start per construct (§3.12; rulings file §2) | Operator, at freeze review |
| 2 | P-2 external CA enumeration (authorized) | Research |
| 3 | Freeze transcription of this record (item 19) and of the GF-1 / GF-4T/R8 cells | Research |

**No GF-10 mechanical definition remains open.** Primary, P2 and contrast are all complete at the
definitional level.

v0.8 is a consolidated decision record: not an implementation specification and not an empirical
freeze.

---

## 11. Supersessions

### 11.1 The 2026-09-17 specification draft

`PTMS_GANN_GF10_FINAL_MECHANICAL_SPECIFICATION_DRAFT_2026-09-17.md` is left unedited. The following
parts of it are superseded by this record and must not be read as open.

| Draft location | Superseded by |
|---|---|
| §5.1 L5 "start anchor OPEN-12" | OPEN-12a = B (§3.10) |
| §5.2 τ "subject to … OPEN-6"; s_T/s_P "OPEN-11"; y "OPEN-12" | §3.1, §3.9, §3.10 |
| §10 F3 (event timestamp), F8 (score mapping) | OPEN-6, OPEN-11 (§3.9) |
| §12 OPEN-12a–d bullets | OPEN-12a = B, 12b = B, 12c = C, 12d = B (§3.10) |
| §14.2 OPEN-6, OPEN-11, OPEN-12 | Locked (§5.2) |
| §14.2 OPEN-8a | Closed by derivation (§3.9) |
| §16 X2 (event bar also penetrates the reference) | OPEN-12d: a penetration at or before t_e ⇒ 0 |
| §16 X19 (event after the formation instant in the final session) | OPEN-11: impossible, since t_e ≤ f_w for every final-session bar |
| §16 X16 (window boundary inside an outcome window) | Candidate spans: OPEN-J. Outcome windows: **OPEN-M = exclude (v0.8)** |

The draft's remaining §14.2 items were already treated in the v0.3–v0.6 chain, which v0.6 §5.4
reflects. They are not re-analysed here.

### 11.2 What freeze-checklist item 2 must transcribe for GF-10 (not R-5's sentence)

R-5's cell (memo §11.F) reads: *"Score = 1 at week-end t if the calendar-day duration from the current
decline's swing-high date to t exceeds the duration of the **immediately preceding** completed K3
decline, and no up-switch has occurred."* That is a **state** score: 1 in every week while the condition
holds. The locked chain has since replaced it with an **event** score. Four locks got it there:

| Lock | Replaces in R-5's cell |
|---|---|
| C-5 / OD-1 | "immediately preceding" → **greatest** qualifying same-type K3 move in the current episode |
| C-6 / OD-7 | evaluation "at week-end *t*" → the **first objectively observable crossing** (a bar end or session close) |
| OD-4 / λ (with RQ-11 = D) | a run of weeks → **at most one P1 event per episode** |
| OPEN-11a (persistence A) | → the score is 1 **only in the formation week containing the event** |

**The freeze must transcribe the GF-10 primary cell as §1.2 rows 7–21, 26 and 27 and §3.9 of this
record, and must cite these supersessions.** Transcribing R-5's sentence would silently revert C-5,
C-6, OD-4 and OPEN-11a. The outcome sentence ("break of the last K3 swing low within the next 5
sessions") is likewise superseded by OPEN-12a–d (§3.10; Z-13) and, for the 0s, OPEN-K(b) (§3.11).

The weeks in which R-5's state score would have printed **repeating 1s** (the condition still holding
week after week) now print **one 1 followed by structural 0s** under persistence A + A1 + K(a)-P2
(NC-25). This is the direct counterpart of OPEN-11a's supersession and must be disclosed with it.

---

**NO CODE. NO BACKTEST. NO EMPIRICAL TESTING. NO MARKET OUTCOMES READ. NO LOCKED DECISION REOPENED.
NOT FROZEN. NOT AN IMPLEMENTATION SPECIFICATION.**
