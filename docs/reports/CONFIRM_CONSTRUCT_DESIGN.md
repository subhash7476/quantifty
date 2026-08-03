# New Construct Design — "Confirmed Rotation" (working label: CONFIRM)

**Status:** DESIGN PROPOSAL — no code, no data read, no window spent.
**Branch:** research/strategy-challenge
**Question it answers:** can the three conditioning ideas (VIX regime, per-name futures OI
confirmation, expiry-day avoidance) be fused into a construct that is **genuinely new** — not
TS Basis relabeled, not Carry relabeled — while keeping only the *important* part of the basis
premise?

---

## 1. The line we are not crossing

The re-authorization assessment is explicit: a "new" basis-family construct that reuses the same
spent window is the selection failure a second time, wearing a fresh name. So the design is bound
by three invariants:

1. **No time-series basis z-score.** ts_basis's identity *is* its 252-row `z_ts` construction.
   We do not use it. The moment we do, this is ts_basis.
2. **No carried overlays.** `basis_reverting`, TP@0.5%, recovery filter, sector cap, |z|
   threshold tuning — all fitted on seen data — are not inherited. This construct is frozen
   with the gates as *primary features*, not as filters bolted onto a known signal.
3. **Cross-sectional rank-IC evaluation, not single-series P&L.** This is the platform's proven
   architecture (Carry's home) and the only evaluation that escapes the per_trade_pnl power wall.

---

## 2. The construct's thesis (stated before any data read)

> Cross-sectional carry on the SSF universe predicts returns **conditional on three things**:
> (a) the regime is dispersion-friendly (VIX not in an extreme-stress state), (b) the move is
> backed by real capital commitment in the futures market (OI building in the signal direction),
> and (c) we are not entering into a mechanically distorted expiry session.

That is a different hypothesis from ts_basis ("time-series basis deviation predicts return") and
from Carry ("residual basis predicts return"). The **conditional admission** — the gates are the
signal, not noise reduction around one — is the construct's identity.

### Why each gate is structural, not a filter

| Gate | Role in the construct | Why it is identity, not overlay |
|---|---|---|
| **G1 — VIX regime** | Book-level admission / exposure | Carry is an idiosyncratic-dispersion harvest. In stress regimes correlation→1 and the cross-section has no separation — the signal's raw material disappears. Bet-sizing on regime is the thesis, not a tunable risk knob. (Dossier Edge 3.) |
| **G2 — OI confirmation** | Name-level admission | A basis call means "the futures price is rich/cheap." Institutional conviction shows up as OI *building* in that direction; unwinding contradicts it. Capital commitment is the confirmation mechanism. (Dossier Edge 6 — per-name futures OI, never read against basis before.) |
| **G3 — Expiry avoidance** | Timing | Dealer gamma hedging distorts price discovery on expiry sessions; entries near them are mechanically contaminated. (Dossier Edge 2, reduced form.) |

---

## 3. What is borrowed from ts_basis (the "important part")

Only the **carry premise and the universe** — the economic raw material, stripped of the
time-series apparatus:

- **Universe:** the ~180-name SSF cross-section (fee-survivable; STT 0.0125% sell-only).
- **Carry premise:** near-month futures vs spot basis contains return information (KMPV carry).
- **Directionality:** high basis → LONG, low basis → SHORT (same sign convention as ts_basis).

That is the entire overlap. Everything else below is new.

## 4. What is NOT carried (explicitly)

| ts_basis component | Status |
|---|---|
| 252-row time-series z-score (`z_ts`, `LOOKBACK_ROWS=252`) | **DROPPED** — replaced by cross-sectional carry score |
| `basis_reverting` filter | **DROPPED** |
| TP@0.5% exit policy | **DROPPED** |
| Recovery-state filter | **DROPPED** |
| Sector cap (max-2/leg) | **DROPPED** |
| |z| threshold tuning | **DROPPED** |
| Daily cadence panel | **DROPPED** — monthly/fortnightly only (fee constraint; daily is research-only by operator) |

---

## 5. Signal construction (pre-specified)

For each formation date `t`:

```
1. basis_u(t) = (F_near(u,t) / S(u,t) − 1) × 252          # annualized carry per name
   z_xs(u,t)  = cross-sectional z-score of basis within the eligible universe at t
                 (winsorized ±3σ; universe = ADV-qualified SSF names)

2. CONFIRM(u,t) = sign(OI_chg_1d(u,t)) == sign(z_xs(u,t))  # G2 — name-level admission
   OI_chg_1d  = chg_in_oi(u, t) / open_int(u, t)   (open_int from futures_bhavcopy)
   # LONG candidates require OI building up; SHORT candidates require OI building down.

3. REGIME(t)  = vix_med_252 / vix_t               # G1 — book-level exposure
   exposure(t) = clip(REGIME(t), 0.25, 2.0)
   # formation fully taken when REGIME(t) ≥ 0.5 (VIX ≤ 2× its median)

4. EXEC_DATE(t+1) must not be an F&O expiry day      # G3 — timing

Book = names where CONFIRM==TRUE, split into LONG (z_xs>0) / SHORT (z_xs<0),
       sized equal-weight × exposure(t), top-K per side (K=5, matching the
       platform's concentrated convention).
```

**Design decisions pinned now (no tuning on TRAIN):**
- Carry window: raw 1-day basis, annualized. (Alternative 5-day smoothing is a documented
  variant, decided by coin-flip tie-break rule on TRAIN, not by looking at results.)
- OI change window: 1-day. (5-day variant is the B-variant.)
- Exposure clip: [0.25, 2.0]; hard-gate threshold: REGIME ≥ 0.5.
- K=5 per side; monthly cadence (fortnightly is the C-variant).

---

## 6. What makes it a different construct (the honest checklist)

| Test | ts_basis | Carry | CONFIRM |
|---|---|---|---|
| Signal | time-series basis z | residual (beta+sector-neut) basis | **cross-sectional raw carry × OI confirmation** |
| OI condition | none | none | **required (G2)** |
| Regime gate | none | none | **VIX exposure scaling (G1)** |
| Expiry avoidance | none | none | **yes (G3)** |
| Primary hypothesis | basis deviation predicts | basis level predicts | **basis level predicts *given* OI backing, healthy dispersion, clean execution** |

If a reviewer cannot tell it apart from ts_basis, the design failed.

---

## 7. Evaluation windows — honest about the constraint

- **TRAIN / HOLDOUT** (2016–2018 / 2019–2022): selection and confirm. Cross-sectional rank-IC
  (Spearman, Newey-West), net spread with SSF fee model.
- **Confirm surface:** the monthly basis family has **no clean sealed window left** (2023–2026
  spent for Carry / de-authorized for TS Basis / failed for IVOL). Therefore this construct,
  like every new SSF construct, confirms by **forward paper** — new months accrued after today
  are the only un-contaminated surface. The sealed window must not be re-read for a basis-family
  member.
- The G2 surface (per-name futures OI vs basis forward returns) is **unread** — recorded in the
  prior-exposure table below; that is the genuinely novel measurement this construct adds.

---

## 8. Prior exposure disclosure

| Read | Relevance to CONFIRM |
|---|---|
| TS Basis monthly SEALED (+22.57%, de-authorized) | Same *premise* family — disclosed, not usable as a confirm window |
| Carry SEALED (+20.52%, PASS) | Same universe, different (residual) signal — its sealed is spent |
| TS Basis Daily equity signal-strength (past 30d) | Pre-spec baseline only; direction hit ≈54% motivates the gates |
| Dossier Edges 3, 6, 2 | Source of the three gate mechanisms |
| **Per-name futures OI vs basis forward returns** | **UNREAD — the novel surface this construct measures** |
| **VIX-conditioned SSF cross-sectional carry** | **UNREAD** |

---

## 9. What this is NOT

- NOT TS Basis revived (no z_ts, no overlays, no spent-window read).
- NOT Carry relabeled (Carry has no OI/regime/expiry gates; this is a conditional-admission
  construct, not a neutralized-residual rotation).
- NOT an index-timing strategy (per_trade_pnl on indices is dead).
- NOT a sealed-window spend — it is a TRAIN/HOLDOUT + forward-paper research program.

---

## 10. Open questions for the operator before implementation

1. **Base ingredient:** is "cross-sectional raw carry (basis level)" the right borrowed piece,
   or should we also neutralise beta/sector like Carry? (Recommendation: **do not neutralise** —
   that is Carry's identity; keeping raw carry + OI confirmation makes CONFIRM distinct.)
2. **OI window:** 1-day vs 5-day OI change. (Coin-flip tie-break on TRAIN, pre-registered.)
3. **Cadence:** monthly primary, fortnightly variant.
4. **Sealed discipline:** confirm by forward paper only — operator sign-off that no basis-family
   sealed read is authorised for this construct.
