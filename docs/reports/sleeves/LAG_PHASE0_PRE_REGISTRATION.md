# LAG Sleeve — Phase 0 Pre-Registration (DRAFT)

**Status:** DRAFT. To be **FROZEN** on operator approval (SHA-256 over the whole file);
bands cannot be revised in response to results once frozen.
**Parent design:** `SIGNAL_ENGINE_DESIGN.md` — a new sleeve candidate (information-diffusion
family), validated standalone before it may enter the combined engine. Originates in
`LAG_PHASE0_RESEARCH_RECORD.md` (Phase 0 brainstorm).
**Consumes:** no sealed data. This document authorizes the RFA power pre-check and, if it
returns PROCEED, the TRAIN/HOLDOUT empirical protocol. The 2023→present window stays
**sealed and unread** until §9's acceptance rule is met on TRAIN and HOLDOUT.

**Correction note vs. the research record:** `LAG_PHASE0_RESEARCH_RECORD.md` §5 computed the
pre-screen with a non-conventional SD band `[0.16, 0.20]` and the full-window `n=125`. The
binding numbers below use the convention-compliant bands (`sd [0.10, 0.18]`, identical to
Carry/Trend/Skew — same substrate, cadence, and cross-section) and `n* = 42` (sealed window,
per `governance/rfa/declarations/{trend,flow}.py` and `scripts/rfa/power.py`). The corrected
optimistic corner clears cleanly (power ≈ 0.89), matching the Trend/Skew pattern. The research
record's "razor-thin central case" framing was an artifact of the miscalculation; this file
supersedes it.

---

## 1. Hypothesis (falsifiable)

Cross-sectional dispersion in **sector-lead information diffusion** over single-stock futures
predicts forward returns. Within each sector, the most-liquid name (the **leader**) impounds
sector information first; **laggard** names catch up with a measurable delay. Names that have
under-moved their leader (large positive leader-minus-own gap) will catch **up** toward the
leader; names that have over-moved their leader (negative gap) will fade **back** toward it.
The tradeable signal is the convergence-to-leader gap.

Sign is declared now and cannot be flipped after seeing results: **long high-gap names
(predicted catch-up in the leader's direction), short low-gap names (predicted fade).** This is
a **continuation/convergence** bet on the leader's directional information, not an unconditional
reversal. (Economic reading: slow information diffusion along the sector graph in a
high-friction, retail-heavy market — Hou-Moskowitz 2006, *Market Frictions, Price Delay, and
the Cross-Section of Expected Returns*; the anomaly's magnitude scales with frictions, so
India's structurally larger frictions predict a larger delay premium than the US ~0.03 baseline.)
If realized IC is significant with the *opposite* sign, the hypothesis is falsified, not
re-labelled.

**Relation to prior work / prior sleeves:** LAG is **not** own-name momentum (Trend, dead at
TRAIN p=0.131) — it ranks names by the *leader's* past return residualized against the name's
own, i.e. cross-autocorrelation not autocorrelation. It is **not** unconditional reversal
(PSB-1 C1, dead on fees) — it is conditioned on the sector leader's directional signal, so it
trades laggards in the leader's direction, not against it. The novelty is the **sector leader
as the information reference**, which the certified G2-R sector graph makes a first-class input.

---

## 2. Universe & point-in-time membership

- **Universe:** NSE F&O-eligible single-stock names, **point-in-time** — a name is eligible
  at formation *t* only if it was F&O-listed and liquid at *t* (same rule as Carry/Trend §2).
- **Continuous prices:** built from near-month futures with the T-3 roll rule (identical to
  Carry §3.4 / Trend §3.2). The roll-adjusted continuous series already exists at
  `data/signal_engine/trend/continuous.duckdb` (363 underlyings, 477,577 FUTSTK cells) and is
  **reused without modification**.
- **Liquidity screen:** trailing 20-day median futures turnover ≥ ₹5 cr (same as Carry/Trend).
- **Sector graph:** G2-R classification, certified (0 unclassified). Used both to define the
  leader (§3.1) and in neutralization (§4).
- **Minimum sector size:** sectors with **< 4 eligible names** at formation *t* are dropped
  from signal computation that formation (the leader/laggard distinction is statistically
  vacuous in tiny sectors). Pinned at freeze.
- **Expected N per formation:** ~120–180 names (same substrate as Carry/Trend).

---

## 3. Signal construction (exact, pre-registered)

For each name *i* in sector *s* (|sector_s| ≥ 4) at monthly formation *t*, using the continuous
(roll-adjusted) futures close:

### 3.1 Sector leader identification (pinned)
The leader `L_s(t)` is the name in sector *s* with the highest **trailing-20-session median
futures turnover** at formation *t*. Rationale: the most liquid name is where information
impounds first (highest attention, tightest spreads, informed flow). This choice is
outcome-relevant and is pinned here — not "largest market cap" or any attention proxy selected
after seeing ICs.

### 3.2 Catch-up gap (the signal)
1. **Horizon log-returns** for each horizon *h* ∈ {63, 126, 252} trading days:
   - `leader_ret_{s,t,h} = ln(adj_close_{L_s,t}) − ln(adj_close_{L_s,t−h})`
   - `own_ret_{i,t,h} = ln(adj_close_{i,t}) − ln(adj_close_{i,t−h})`
   - `gap_{i,t,h} = leader_ret_{s,t,h} − own_ret_{i,t,h}`
2. **Multi-horizon composite:** `lag_{i,t} = mean_h(gap_{i,t,h})` — the average catch-up gap
   across the three horizons (same horizons as Trend §3 for direct comparability).
3. **Winsorize ±3σ** cross-sectionally; **cross-sectional z-score** to zero mean / unit SD
   across the eligible universe on each date → `z_lag_{i,t}`.

**Sign reading:** high `z_lag` (leader moved more than the name → name lagged) predicts the
name catches up in the leader's direction → higher forward return. Low/negative `z_lag`
(name out-moved the leader → overshot) predicts fade → lower forward return.

### 3.3 Horizon rationale
63/126/252 trading days ≈ 3/6/12 months — the standard delay-diffusion lookbacks
(Hou-Moskowitz use up to 12 months). Equal-weighting across horizons reduces
horizon-specific noise, matching Trend's design choice.

---

## 4. Neutralization

Before ranking, residualize `z_lag_i` against:
- **Market beta** (trailing 252-day beta to Nifty 50), and
- **Sector** (NSE sector dummies)

via a single cross-sectional OLS per formation; the **residual** is the tradeable signal
`z_lag_neut_i`. Same methodology as Carry/Trend §4.

**Note on redundancy:** the gap signal is already *within-sector* (relative to the sector's own
leader), so sector-neutralization is partly redundant by construction — the signal cannot
represent a pure sector bet. It is applied anyway so the composite combination places all
sleeves on an equal sector-neutral footing. Market-beta neutralization is the meaningful step.

---

## 5. Metric — and why rank-IC

**Primary metric:** cross-sectional **Spearman rank-IC** of `z_lag_neut` at formation *t* vs.
the forward one-month name return (using spot adjusted returns), measured at monthly formations.
One-sided test (sign declared POSITIVE in §1).
**Secondary (reported, not the gate):** net top-minus-bottom quintile spread under §8 fees.

**Why rank-IC / one-sided:** LAG is a cross-sectional ranking signal with a committed direction
(convergence to leader), so rank-IC with a declared positive sign is the correct test. The RFA
contract v2 permits independent delta/SD bands for rank-IC, avoiding the crossed-corner
artifact that withdrew O1. Two-sided was considered (as insurance against a wrong-sign result,
per the v1-Carry lesson) and **rejected**: the diffusion thesis commits to a specific direction
(continuation with the leader), and a wrong-sign result is informative — it falsifies the
diffusion mechanism rather than surviving as an unlabelled effect.

---

## 6. Portfolio construction

- **Form:** beta-neutral, sector-neutral, dollar-neutral cross-sectional long/short.
- **Weights:** proportional to `z_lag_neut` (z-weighted), renormalized to fixed gross exposure;
  **ADV-capped per name** (position ≤ 10% of 20-day futures ADV).
- **Rebalance cadence:** **monthly**, aligned with Carry. (Signal computed daily but the book
  rebalances monthly.)
- **Turnover penalty:** rebalances smaller than 0.25σ of target weight are suppressed.

Inherited verbatim from Carry/Trend §6 — LAG is only the ranking signal; the book mechanics are
shared across the engine.

---

## 7. RFA power pre-check (declared bands — frozen at approval)

`metric = rank_ic`, one-sided test (sign declared in §1), power hurdle **0.80**.

| Quantity | Band | Provenance |
|---|---|---|
| **delta** (mean cross-sectional IC) | **[0.035, 0.045]** | The structural bet. Hou-Moskowitz (2006) price-delay is one of the most robust US anomalies at cross-sectional IC ~0.02–0.03, and its magnitude **scales with market frictions** — India's retail dominance, thinner mid/small SSF names, and concentrated attention imply a larger delay premium than the US baseline. The pessimistic bound (0.035) sits just above the US level; the optimistic (0.045) is the India-enlarged upside. **This band is the load-bearing assumption** — if India's delay is not larger than the US's, the pessimistic bound is too high and TRAIN will say so. Literature-defended, not derived from an in-sample read. |
| **SD** (IC dispersion across formations) | **[0.10, 0.18]** | Identical to Carry/Trend/Flow. Monthly cross-sectional IC dispersion for a ~120–180-name SSF cross-section is dominated by true time-variation, not sampling noise. LAG uses the same substrate, cadence, and cross-section size as those sleeves — no defensible reason for its SD band to differ. Using the identical band ensures the RFA comparison is apples-to-apples across sleeves. |
| **n\*** (formations in the sealed projection window) | **= 42** (monthly, sealed 2023-01 → 2026-07) | The futures continuous series spans 2016-02-11 → 2026-07-20 (same raw bhavcopy as Carry/Trend/Flow). After a 12-month lookback warmup, the first feasible formation is 2017-02. Window allocation (§9): TRAIN 2017-02 → 2020-12, HOLDOUT 2021-01 → 2022-12, **SEALED 2023-01 → 2026-07 (~42 monthly formations)** — matching the Flow/Skew allocation that maximizes the sealed window. **The calendar lever is exhausted** — NSE F&O history before 2016 is not obtainable (SFB-1/F1 lockdown finding). |

### 7.1 The honest power picture — standalone vs. combined

`ncp = (delta / SD) · √n*`, one-sided α = 0.05. Using `scripts/rfa/power.py`:

| Corner | delta | SD | ncp (n*=42) | Power | Verdict |
|---|---|---|---|---|---|
| Optimistic | 0.045 | 0.10 | 2.916 | **~0.89** | **PROCEED** |
| Central | 0.040 | 0.14 | 1.852 | ~0.57 | below hurdle |
| Pessimistic | 0.035 | 0.18 | 1.260 | ~0.34 | below hurdle |

At n* = 42, clearing standalone power 0.80 needs per-formation IR `delta/SD ≥ ~0.39`:
- **Optimistic corner** `(0.045 / 0.10)` → IR 0.45 → **clears** → RFA **PROCEED**.
  (Legitimate, not a crossed corner — delta and SD are independently defended per the RFA
  contract v2; the optimistic corner is `(delta_hi, sd_lo)` as the gate evaluates.)
- **Central** `(0.040 / 0.14)` → IR 0.286 → standalone power ≈ 0.57 → below hurdle.

Same structural constraint as Carry/Trend §7.1. **The 0.80 power hurdle binds at the combined
engine level, not per-sleeve.** LAG's standalone TRAIN/HOLDOUT read is a
sign + magnitude + fee + persistence check (§9 gates 2, 4, 5), not a standalone 0.80 gate.

### 7.2 AC₁ / overlap
Monthly non-overlapping formations → no overlap-induced autocorrelation inflation. AC₁ still
reported at TRAIN; if materially positive (|AC₁| > 0.10), the effective-n haircut is applied
via Newey-West SE (same as PSB/Trend protocol).

---

## 8. Fees & cost model

Same as Carry/Trend §8: `core/execution/futures/futures_fees.py` (already implemented).
- Futures STT sell-side only: 0.0125% (TRAIN period) / 0.02% (post-Oct-2024).
- Exchange txn, SEBI fee, stamp duty, GST — all era-accurate.
- Brokerage: default Rs 20/order (discount broker futures).
- Slippage: κ = 5 bp/side, plus ADV position cap as impact control.

LAG's slow-diffusion construction should produce turnover comparable to or lower than Trend's
realized 0.69 at monthly cadence — the signal moves slowly with the leader.

---

## 9. Acceptance rule (pre-registered, evaluated before any sealed read)

**Windows (pinned, from the continuous futures series 2016-02-11 → 2026-07-20):**
- **TRAIN:** 2017-02 → 2020-12 (~47 monthly formations). First formation 2017-02 allows
  12-month lookback warmup from 2016-02-11. Beta warms up off pre-TRAIN history (Nifty 50
  daily from 2012-02-21).
- **HOLDOUT:** 2021-01 → 2022-12 (24 monthly).
- **SEALED:** 2023-01-01 → 2026-07-20 (~42 monthly) — **untouched** until gates 1–5 pass.

This is the Flow/Skew allocation (sealed starts 2023-01), chosen to maximize the sealed window
and thus n*. It gives TRAIN 47 formations (vs Trend's 59) — slightly less estimation data, but
still comparable to Skew's 54 and sufficient for IC/SD estimation.

Ordered gates. Each must pass on the stated window before the next window is touched:

1. **RFA gate** (declared bands, §7): single-sleeve bar is **PROCEED** (optimistic corner
   power ~0.89). ABANDON is dispositive.
2. **TRAIN:** mean rank-IC significant with the **declared (positive) sign** (t via AC₁-
   corrected SE); net quintile spread > 0 under §8 fees; realized IC SD inside the declared
   [0.10, 0.18] band (if SD > 0.18, the C2 wide-SD failure repeats and the sleeve stops here,
   sealed window preserved).
3. **HOLDOUT:** sign and net-spread persist; **no parameter touched** between TRAIN and
   HOLDOUT.
4. **Composite power check** (engine level, not standalone): LAG's TRAIN-estimated IR feeds
   the combined-engine power projection with Carry's read; the 0.80 hurdle binds on the
   composite, not on LAG alone.
5. **Only then**, one **SEALED** read (2023-01 → present), reported whatever it shows.

Any gate failure → sleeve does not advance; **no successor is auto-authorized**; sealed window
stays sealed if not yet reached.

---

## 10. Prior-exposure disclosure

The operator's prior reads in the momentum/reversal/diffusion neighborhood:
- **Trend (SSF TSMOM, dead at TRAIN):** the closest prior read. Same substrate (the continuous
  series LAG reuses), same forward returns. Trend is own-name autocorrelation; LAG is
  cross-autocorrelation conditioned on the sector leader — statistically distinct objects, but
  disclosed as **prior-adjacent**. **m counts this.**
- **PSB-1 C1 (weekly unconditional reversal, cash equity, dead on fees):** a reversal
  construct on a different substrate and cadence. Disclosed; the family-wise penalty applies if
  LAG's realized correlation with unconditional reversal is high.
- **SFB-1/F1 (cash-synthesized 12-1 momentum, inconclusive):** approximate, not equivalent
  (single-horizon, no sector conditioning, concentrated ≤10-name book).
- **Carry (SSF residual basis, survived):** a different economic family (financing vs
  diffusion). Correlation to be measured on TRAIN; disclosed regardless.

**No sector-lead / cross-autocorrelation diffusion construct has been screened on this data.**
The multiplicity penalty is pinned at declaration freeze; the honest minimum is **m ≥ 2**
(Trend is the unavoidable prior-adjacent read). The Bonferroni evidence floor tightens
accordingly. If LAG-IC residualized against Trend's signal drops below 60% of raw (same sign),
LAG is momentum in disguise and dies regardless of its standalone number (§11 prediction 3).

---

## 11. Falsifiable predictions (stated before the run)

1. **(Load-bearing)** LAG rank-IC on TRAIN is **positive-signed** and its AC₁-corrected t-stat
   clears the threshold. The India-friction structural bet specifically predicts mean IC
   **≥ 0.04** — if realized IC is in [0.02, 0.04] (the US range, not enlarged), the bet is
   falsified even if nominally significant.
2. The **diffusion mechanism exists**: within-sector cross-autocorrelation
   `corr(leader_ret_{t}, laggard_ret_{t+1})` is positive and significant.
3. **Not subsumed by own-name momentum**: LAG-IC after residualizing against Trend's signal
   stays ≥ 60% of raw LAG-IC, same sign.
4. Net quintile spread > 0 under §8 futures fees at monthly turnover.
5. Realized TRAIN IC SD lands inside the declared **[0.10, 0.18]** band.

If (1) or (4) fails, LAG is not a viable sleeve. If (3) fails, LAG is momentum in disguise and
is not a *new* sleeve regardless of its standalone IC. The engine composition reverts to
**Carry solo** (or whatever else has survived by then).

---

## 12. Key files (to be created)

| File | Purpose |
|---|---|
| `governance/rfa/declarations/lag.py` | Frozen RFA declaration (bands, n*=42, one-sided positive) |
| `scripts/signal_engine/lag/build_lag.py` | §3 signal construction (leader ID + catch-up gap → z → neutralized) |
| `scripts/signal_engine/lag/run_train.py` | §9 TRAIN read → `LAG_TRAIN_REPORT.md` |
| `tests/signal_engine/lag/` | leader-ID + gap-construction + neutralization + fee unit tests |
| `docs/reports/LAG_TRAIN_REPORT.md` | script-generated TRAIN report (no hand-edited numbers) |

`build_continuous.py` and the continuous-series store are **reused from Trend** — no new
substrate build.

---

## 13. Engine viability — empirical, not projected

Same discipline as Carry/Trend §13. The composite engine power is decided **empirically from
realized quantities after TRAIN**, never from a pre-freeze projection. The binding 0.80 hurdle
applies at the combined-engine level after ≥2 sleeves have TRAIN reads.

At the time of LAG's TRAIN, **Carry is the only other surviving sleeve** (Trend and Skew both
failed at TRAIN; Flow was killed at the RFA gate). The composite is therefore **Carry + LAG
(2 sleeves)** if LAG passes. At n* = 42 with central per-sleeve IR ≈ 0.25:
`composite IR ≈ √(2 × 0.25²) = 0.35` → standalone-composite power ≈ 0.50 at n* = 42. This does
not clear 0.80. With upper-band per-sleeve IR (~0.45): `composite IR ≈ √(2 × 0.45²) = 0.64`
→ power ~0.85, clears.

**Consequence stated plainly:** a 2-sleeve engine (Carry + LAG) clears 0.80 only at the
optimistic end of the realized-IR band. This is the same structural risk Trend §13 carried.
The honest path: if LAG passes TRAIN and HOLDOUT but the realized-composite power sits below
0.80, the engine either accepts a sub-0.80 composite (documented, with the realized numbers)
or stops and does not force a third sleeve in to reach the hurdle — per CLAUDE.md's guard
against re-weighting existing sleeves to hit a target. **The composite verdict is determinative;
the sealed window stays sealed until the hurdle is cleared or the engine accepts the realized
 shortfall explicitly.**

---

## 14. Freeze

On approval: compute SHA-256 over this file (excluding this line), record it here and in
`lag.py`, and treat §1 (sign), §3 (construction — leader rule, gap formula, min sector size),
§4 (neutralization), §6 (cadence/caps), §7 (bands), §9 (acceptance rule) and §10 (prior
exposure / m) as immutable. Any change after freeze starts a new pre-registration.
