# ISD Phase-0 — Candidate Family Ranking (v3, post-lead-review)

**Date:** 2026-08-26 · **Status:** Investigation complete; lead review
(`ISD_PHASE0_CANDIDATE_RANKING_REVIEW.md`) findings R1–R11 applied — this version
is the decision sheet the freeze will be built from. **The pre-registration is NOT
frozen.** Governing principle (operator): *spend freedom before the preregistration,
not after it.*

No backtests, no tuning, no new signal-level reads of the equity 1m store.
Formation counts are calendar arithmetic (RFA-free); effect bands are anchored on
in-house OOS priors (CB-N50 HOLDOUT IC +0.029) and the published literature.

---

## 1. Method note

- **Power metric:** `rank_ic` family — daily cross-sectional IC over ~200 names;
  per-day IC observations are the formation unit. RFA contract v2, one-sided
  α = 0.05, power ≥ 0.80 hurdle.
- **All power figures below are script-generated** from `scripts/rfa/power.py`
  (`power_at` / `n_required`, t-distribution, one-sided) — **verbatim output;
  no hand-derived numbers** (review R1; spec guardrail 7).
- **Cost basis:** certified G6 — round trip ≈ fees + slippage. The G6 ticket
  table row at ₹5L tickets is **4.47 bp fees** (5.88 bp at ₹2L) + drift
  p90 ≈ 2.35–2.90 bp/side (deciles 2–9) ⇒ ≈ 10 bp round trip at the ₹5L
  operating point (review R11).
- **Effect-size anchor:** CB-N50 HOLDOUT +0.029 (50 names, close-to-close). The
  TRAIN +0.059 is selection-inflated (the C2 shrinkage lesson). **Transferability
  caveat (review R7):** CB-N50 used EOD close-to-close *reversal + basis*
  features; neither ISD family shares that feature family. The band asserts a
  **plausibility envelope anchored on the nearest in-house OOS read — not
  precedent**. Directionally, intraday-derived features carry more information
  than EOD features, so the band is more likely conservative than generous —
  an argument, not a measurement.

## 2. Formation counts (calendar, exact; as-of date pinned: 2026-08-24)

| Window | Sessions | √n |
|---|---|---|
| TRAIN 2023-01-02 → 2024-11-30 | 474 | 21.8 |
| HOLDOUT 2024-12-01 → 2025-12-31 | 270 | 16.4 |
| SEALED 2026-01-01 → as-of 2026-08-24 | 159 | 12.6 |
| Deep vendor TRAIN 2015-02-02 → 2022-12-31 | 1,962 | 44.3 |

## 3. Cost canvas — ILLUSTRATION ONLY (review R4)

Daily EOD-flat L/S at ~10 bp round trip, 250 rebalances/yr:

| Turnover τ | Annual drag |
|---|---|
| 0.25 | ~6.3%/yr |
| 0.30 | ~7.5%/yr |
| 0.40 | ~10.0%/yr |
| 0.50 | ~12.5%/yr |

**Binding commitment (replaces the canvas):** τ is **measured per cell on TRAIN**
at the frozen parameters and the net-spread gate is applied at **each cell's
measured τ** — never at an assumed τ. An unbanded daily-rebalanced rank book can
turn over ~1.0+/day (≈27%/yr drag) — off this canvas entirely; the banded-exit
cells exist precisely to control it, and the ledger records the measured value
per cell. The canvas is not the operating point (review R4).

---

## 4. RESOLUTION 1 — SEALED fence / power problem

**Decision: keep the proposed calendar fences; add a mechanical SEALED-spend
floor of n_sealed ≥ 317 sessions, with the power table pre-registered from
`power.py` output. Projected spend date ≈ 2027-03 (calendar estimate, disclosed,
not a commitment).**

- At n = 159 (read today) central power is **0.545** — a likely waste of the
  one-shot SEALED read.
- `n_required(δ=0.028, sd=0.20, power=0.80) = **317**` — the floor. At the
  floor, central power = 0.800 (t-distribution, exact).
- The floor is mechanical: the sealed read may be taken only when (a) HOLDOUT
  PASS, (b) the forward-PAPER interval (Q5) is complete, and (c) n_sealed ≥ 317.
  No judgment at spend time.

**Pre-registered power table (script output, `power.py`, one-sided α=0.05):**

```
SEALED today   n=159  central (δ=.028 sd=.20): 0.5450
SEALED floor   n=317  pessimistic (δ=.020 sd=.25): 0.4129
SEALED floor   n=317  central (δ=.028 sd=.20): 0.8000
SEALED floor   n=317  optimistic (δ=.035 sd=.15): 0.9937
HOLDOUT        n=270  central: 0.7421
TRAIN          n=474  central: 0.9191
n_required central (0.028, 0.20, 0.80): 317
n_required optimistic (0.035, 0.15, 0.80): 115
n_required pessimistic (0.020, 0.25, 0.80): 968   (~2029 — impractical)
n_required pessimistic (0.020, 0.25, 0.95): 1693
```

**Calibration disclosure (review R5):** at the floor, pessimistic-corner power
is 0.41 — **if truth sits at the pessimistic corner, a SEALED FAIL happens 59%
of the time even though the effect is real.** Raising the floor to cover that
corner needs n ≈ 968 (~2029) — impractical, so the compromise stands. The read
is calibrated to detect the central effect; a FAIL retires the construct
regardless and cannot distinguish "weaker than central" from "unlucky." Disclosed
now, not discovered later.

## 5. RESOLUTION 2 — #3 and #1 are the same signal. Collapse #3 into #1.

`rank(x_i − x̄) ≡ rank(x_i)` for a scalar x̄ (the cross-sectional mean / index
return is one constant per day). Identical rank book and identical rank IC under
either IC definition (Pearson IC is affine-invariant — review R1 verification).
The variance-deflation argument in v1 is retracted.

What survives from #3: the equal-weight-mean deflation is a **book-construction
detail** inside #1 (sizing/spread measurement), pre-registered as such. The
beta-residualized variant is mathematically distinct but **rejected**: rolling-beta
estimation is a tuning surface; refusing it now is spending freedom.

**Consequence: the battery is {1, 4} — two families.**

## 6. RESOLUTION 3 — Exact mechanism / sign pins + labels/execution (review R2)

**Family 1 — Opening-drive continuation (sign pinned by mechanism, no TRAIN burn):**
- Mechanism: the opening-period return is the market's fastest information
  channel — order-flow imbalance and early informed trading propagate intraday
  (partial adjustment), amplified by attention-driven chasing and algo momentum.
  Academic anchor: intraday momentum, index level (Gao, Han, Li & Zhou 2018,
  *JFE*); NSE-specific: the pre-open call auction concentrates opening
  information into a single auction print, sharpening exactly this signal;
  in-house: index-pair work found intraday index *trends* (+1.10/+1.17 slopes).
- Sign: **continuation**. CB-N50's negative daily *close-to-close* momentum is
  scoped out by horizon. If the pinned sign reads negative on TRAIN, the family
  is **closed** (§9) — no sign-flip fishing. Net prior: modestly favorable —
  the best-evidenced family and the cheapest to kill cleanly (review §3).
- **Labels/execution (pinned):** feature window 09:15–10:00 (cell);
  feature = (window-end bar close − 09:15 open)/09:15 open; entry at the bar
  **open immediately after the window-end close** (10:01 bar open for the
  09:15–10:00 cell; 09:46 for the 09:15–09:45 cell); exit at the **15:29 bar
  close**. IC label = the hold-leg return **entry open → 15:29 close only** —
  the signal window is **excluded from the label by construction** (a label
  overlapping the signal window mechanically inflates continuation — the
  review's single easiest false TRAIN pass). P&L ledger uses the same
  entry/exit prices + fees + measured slippage; the IC label and P&L algebra
  are declared explicitly (they may legitimately differ; the pre-registration
  says how).

**Family 4 — Overnight-gap (sign via the declared TRAIN-burn protocol, CARRY
precedent):**
- Mechanism: the gap is the market's only overnight information channel. It has
  an information component (continuation) and a noise/overreaction component
  (auction liquidity provision — fade). Not separable ex-ante without event
  classification (a tuning surface — refused). Literature: tug-of-war (Lou,
  Polk & Skouras 2019, *JFE*) is monthly-horizon; retail-sentiment overnight
  moves reverse intraday (Berkman et al. 2012, *JFE*); news gaps continue. The
  document's two-mechanisms reading is accurate. Net prior: symmetric coin-flip
  on sign (review §3).
- Sign: **discovered ONCE on TRAIN (474 formations), then frozen** — the CARRY
  precedent. Declared in the pre-registration; HOLDOUT/SEALED tests are one-sided
  in the registered direction. **Disclosure (review R3): Family 4 reads TRAIN
  twice — sign discovery + IC gate; its effective m = 2 and its TRAIN IC gate is
  conditional on the TRAIN-discovered sign.** Family 1's mechanism-pin avoids
  this; the asymmetry is a genuine advantage, kept visible.
- **Labels/execution (pinned):** signal = the gap, measured as (09:15 auction
  open − prev_close)/prev_close from the certified daily store (PIT ISIN join,
  G5 machinery; CA ex-dates excluded). Entry at the **09:16 bar open** (the
  auction print at 09:15 is not reachable in size — the 09:15 bar is the auction
  bar); exit at the **15:29 bar close**. IC label = **09:16 open → 15:29 close**
  — no overlap with the signal (measured at 09:15 open).

**Distinctness of {1, 4}:** gap = overnight information (prev_close → 09:15 open);
drive = intraday flow (09:15 → 10:00). Different information sets. **ρ₁₄
commitment (review R8):** the two *books'* return correlation is **reported at
TRAIN, never optimized on**; composite talk waits until both families have their
own gate results. The breadth thesis only earns its power claim if ρ is genuinely
low — measured, not assumed.

## 7. RESOLUTION 4 — The 2015 archive is not needed. Native-only.

- Native TRAIN (474 formations): SE(sd) ≈ sd/√(2n) ≈ 0.20/√948 ≈ **0.65%** —
  already precise (7× more formations than C2's killer 55-formation estimate).
- Deep TRAIN (1,962 vendor formations) halves SE(sd) to ~0.3% — but the vendor
  SD is **era-mismatched**: 85 names, single-source, pre-2023 regime, different
  adjustment basis. The C2 lesson is SD off the *same substrate as the
  confirmatory read*, not more history.
- The vendor archive stays a certified, **unread reserve outside this program**
  (Q1 discipline: substrate frozen at native-only; reading it after first results
  "just to check" would evaporate its option value and is forbidden — review §5).

## 8. RESOLUTION 5 — Precise MDE / RFA declaration inputs

Per family, one declaration each (`rank_ic`, contract v2), frozen with SHA
digests before any gate:

| Input | Value | Justification |
|---|---|---|
| δ band | **[0.020, 0.035]**, central **0.028** | plausibility envelope anchored on CB-N50 HOLDOUT +0.029 (shrunk); ~200-name cross-section may dilute → central rounds down; **no direct prior exists for these feature families** (R7) |
| sd band | **[0.15, 0.25]**, central **0.20** | CB-N50 RFA band, unchanged |
| n (sealed floor) | **317** | `n_required(0.028, 0.20, 0.80) = 317` (script) |
| **MDE** | **0.028** | the central δ at which the floor yields power 0.80 |
| RFA verdict | PROCEED | optimistic 0.9937 > 0.80; central 0.8000 at the floor |
| Gates | TRAIN family IC significant (one test per family, α 0.05 after BH, see §9) → HOLDOUT one-shot (α 0.05) → paper + floor → SEALED one-shot | spec §7/§9 + Q5 |

## 9. Final battery and pre-registration decision sheet

**Battery: {1 = Opening-drive continuation, 4 = Overnight-gap}** — both
`rank_ic` daily cross-sections over the certified native universe (~200 names),
EOD-flat, dollar-neutral, ADV-capped, measured-cost model. #2 (reversal), #5
(expiry), #3 (as a separate family), OI: all dropped (reasons: v2 document).

Frozen in the pre-registration (freedom spent now):
1. **Fences:** TRAIN 2023-01-02→2024-11-30 · HOLDOUT 2024-12-01→2025-12-31 ·
   SEALED 2026-01-01→present, with **n_sealed ≥ 317 spend floor** (≈ 2027-03).
2. **Signs:** #1 continuation (mechanism); #4 TRAIN-burned once (declared, m=2
   disclosed).
3. **Substrate:** native-only; vendor archive excluded by rule.
4. **Grid (frozen, small):** per family 4 cells — F1: opening windows
   {09:15–09:45, 09:15–10:00} × band widths {20%, 40%}; F4: entry {09:16 open,
   09:16 close} × band widths {20%, 40%} (the draft's banded-exit dimension
   was dropped at freeze — an EOD-flat book has no exit-band role); trial
   ledger before running; ≥2-of-4 qualifying cells; matched nulls (random
   entries + circular-shift).
5. **BH scope (declared, review R3):** family-wise — per-cell α = 0.05/4 =
   0.0125 within each family's 4 cells; the TRAIN gate is **one family-level
   IC test per family at α = 0.05**; cell selection is a selection criterion,
   not a p-value. Family 4's effective m = 2 disclosed above.
6. **Costs:** fee module + measured slippage; **net-spread gate at each cell's
   measured τ on TRAIN** (re-measured on HOLDOUT at frozen parameters — no
   edits); measured τ published in the ledger.
7. **RFA declarations:** the table in §8, frozen with SHA digests.
8. **Q5 paper interval:** ≥ 3 months forward PAPER, coincident with the floor;
   sealed read only when all three gates (HOLDOUT PASS, paper complete,
   n ≥ 317) hold. **Contamination rule (review R6): during the paper interval
   only the pre-registered mechanical criteria may act — no parameter edits, no
   early abort on eyeballed P&L; any discretionary change restarts the paper
   clock and is logged in the trial ledger.** This closes the TS Basis Daily
   failure mode (iterative promotion on evaluation surfaces) at its last
   remaining entrance.
9. **Covariates (review R9):** **none in v1** — VIX regime, delivery-%, and any
   other conditioner are excluded; a future conditioning variant is a new
   pre-registered construct with pre-committed signs (spec §4 rule).
10. **Slippage-model boundary (review R10, accepted):** G6 drift is bar-to-bar
    (latency/short-horizon), not own-order impact, halts, or circuit limits;
    decile profile is flat. Valid as a research hurdle at ₹5L tickets in
    F&O-eligible names; not a live-fill claim. ADV cap in every cell's book;
    live-paper divergence is information when it arrives.

No open questions remain before drafting the pre-registration document.

---

## Appendix — review disposition

| Finding | Disposition |
|---|---|
| R1 wrong power figures | fixed — all figures regenerated from `scripts/rfa/power.py`; floor raised 315→317 (central 0.7980 at 315 < 0.80) |
| R2 labels/execution unpinned | pinned per family/cell (§6); signal window excluded from IC label |
| R3 BH scope + m disclosure | BH family-wise declared; Family 4 m=2 disclosed (§9.5) |
| R4 turnover asserted | canvas demoted to illustration; measured-τ commitment (§3) |
| R5 calibration risk | disclosure sentence added (§4) |
| R6 paper contamination | rule frozen (§9.8) |
| R7 anchor honesty | band relabeled plausibility envelope (§1) |
| R8 ρ₁₄ | report-at-TRAIN commitment (§6) |
| R9 covariates | excluded from v1 (§9.9) |
| R10 slippage boundary | accepted, documented (§9.10) |
| R11 fee citation / as-of | 4.47 bp at ₹5L cited; as-of date 2026-08-24 pinned |
