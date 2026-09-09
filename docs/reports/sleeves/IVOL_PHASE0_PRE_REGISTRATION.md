# IVOL Sleeve — Phase 0 Pre-Registration (DRAFT)

**Status:** DRAFT. To be **FROZEN** on operator approval (SHA-256 over the whole file);
bands cannot be revised in response to results once frozen.
**Parent design:** `SIGNAL_ENGINE_DESIGN.md` — a new sleeve candidate (idiosyncratic-volatility
family), validated standalone before it may enter the combined engine. Originates in
`IVOL_PHASE0_RESEARCH_RECORD.md` (Phase 0 brainstorm).
**Consumes:** no sealed data. This document authorizes the RFA power pre-check and, if it
returns PROCEED, the TRAIN/HOLDOUT empirical protocol. The 2023→present window stays
**sealed and unread** until §9's acceptance rule is met on TRAIN and HOLDOUT.

---

## 1. Hypothesis (falsifiable)

Cross-sectional dispersion in **idiosyncratic realized volatility** over single-stock futures
predicts forward returns. Names with **high** idiosyncratic volatility **underperform** (they
are lottery-like, overpriced by retail); names with **low** idiosyncratic volatility
**outperform**. This is the high-IVOL-underperforms anomaly (Ang–Hodrick–Xing–Zhang 2006/2009;
Frazzini–Pedersen 2014, *Betting Against Beta*).

Sign is declared now and cannot be flipped after seeing results: **the predicted rank-IC of
`z_ivol` (high = high vol) vs forward returns is NEGATIVE.** Long low-`z_ivol` (low vol),
short high-`z_ivol` (high vol). (Economic reading: lottery preference — retail overpays for
high-vol/lottery payoffs; India's retail dominance amplifies the effect.) If realized IC is
significant with the *opposite* (positive) sign, the hypothesis is falsified, not re-labelled.

**Relation to prior work:** IVOL is **not** own-name momentum (Trend), not basis (Carry), not
option-implied skew (Skew), not lead-lag diffusion (LAG). It is a **levels/risk** signal —
slow-moving, like Carry's basis, which is the structural reason its turnover (and thus fee
drag) is low. The closest prior read is **PSB-1 C5** (cash-equity low-vol, monthly banded),
disclosed in §10.

---

## 2. Universe & point-in-time membership

- **Universe:** NSE F&O-eligible single-stock names, **point-in-time** — a name is eligible
  at formation *t* only if it was F&O-listed and liquid at *t* (same rule as Carry/Trend/LAG).
- **Continuous prices:** built from near-month futures with the T-3 roll rule (identical to
  Carry §3.4). The roll-adjusted continuous series already exists at
  `data/signal_engine/trend/continuous.duckdb` (363 underlyings) and is **reused without
  modification** (third reuse, after Trend and LAG).
- **Liquidity screen:** trailing 20-day median futures turnover ≥ ₹5 cr (same as Carry/Trend/LAG).
- **Sector graph:** G2-R classification, certified (0 unclassified). Used in neutralization (§4).
- **Expected N per formation:** ~120–180 names (same substrate as Carry/Trend/LAG).

---

## 3. Signal construction (exact, pre-registered)

For each name *i* at monthly formation *t*, using the continuous (roll-adjusted) futures close:

1. **Trailing daily log returns** from the continuous series (60-session window, matching
   Trend's `VOL_WINDOW`).
2. **Realized volatility:** `rv_{i,t} = std_dev(daily_log_rets_{i, t-60:t}) × √252`.
3. **Cross-sectional z-score:** standardize `rv_{i,t}` to zero mean / unit SD across the
   eligible universe on each date → `z_ivol_{i,t}` (high = high idiosyncratic vol).
   Winsorize ±3σ before z-scoring.
4. **(No vol-scaling of returns)** — unlike Trend, the signal IS the volatility level, not a
   vol-scaled return. The construction is a levels ranking, not a momentum ranking.

### 3.1 Window rationale
60 trading days ≈ 3 months — the standard short-horizon IVOL lookback (Ang et al. use ~1 month;
3 months balances responsiveness against estimation noise on the ~150-name SSF cross-section).
The choice is pinned here; it is outcome-relevant and is not selected after seeing ICs.

---

## 4. Neutralization

Before ranking, residualize `z_ivol_i` against:
- **Market beta** (trailing 252-day beta to Nifty 50), and
- **Sector** (NSE sector dummies)

via a single cross-sectional OLS per formation; the **residual** is the tradeable signal
`z_ivol_neut_i`. Same methodology as Carry/Trend/LAG §4.

**This is what makes the signal "idiosyncratic."** The raw `z_ivol` is total-volatility rank;
residualizing against beta removes the systematic (market) component cross-sectionally, leaving
the idiosyncratic-vol ranking — the BAB construct. Sector dummies remove any sector-level vol
clustering (e.g., financials being structurally higher-vol). After this step, `z_ivol_neut` is
the IVOL anomaly signal.

---

## 5. Metric — and why rank-IC

**Primary metric:** cross-sectional **Spearman rank-IC** of `z_ivol_neut` at formation *t* vs.
the forward one-month name return (using spot adjusted returns), measured at monthly formations.
**One-sided test, NEGATIVE direction** (sign declared in §1: high vol → low return).
**Secondary (reported, not the gate):** net top-minus-bottom quintile spread under §8 fees.

**Why rank-IC / one-sided negative:** IVOL is a cross-sectional ranking signal with a committed
direction (low-vol outperforms), so rank-IC with a declared negative sign is the correct test.
Two-sided was considered (as insurance against a wrong-direction result, per the v1-Carry lesson)
and **rejected**: the IVOL direction is one of the most replicated in the literature and a
wrong-sign result is informative — it falsifies the anomaly rather than surviving unlabelled.

---

## 6. Portfolio construction

- **Form:** beta-neutral, sector-neutral, dollar-neutral cross-sectional long/short.
- **Weights:** proportional to `z_ivol_neut` (z-weighted), renormalized to fixed gross exposure;
  **ADV-capped per name** (position ≤ 10% of 20-day futures ADV).
- **Rebalance cadence:** **monthly**, aligned with Carry. IVOL is a slow-moving levels signal;
  intra-month rebalancing is unnecessary (C5 realized 14 bp/yr drag at monthly+banded).
- **Turnover penalty:** rebalances smaller than 0.25σ of target weight are suppressed.

Inherited from Carry/Trend/LAG §6 — IVOL is only the ranking signal; book mechanics are shared.

---

## 7. RFA power pre-check (declared bands — frozen at approval)

`metric = rank_ic`, one-sided test (sign declared NEGATIVE in §1; delta is the magnitude |IC|),
power hurdle **0.80**.

| Quantity | Band | Provenance |
|---|---|---|
| **delta** (\|mean IC\|) | **[0.040, 0.060]** | The BAB / high-IVOL-underperforms anomaly is among the strongest documented: Ang–Hodrick–Xing–Zhang (2006) and Frazzini–Pedersen (2014, t>5) report cross-sectional IC ~0.04–0.06. **PSB-1 C5 realized +0.068 on Indian cash equity** — the highest IC of any candidate this repo has run. The pessimistic bound (0.040) is the literature floor; the optimistic (0.060) sits just under C5's realized 0.068, leaving room for the India-retail-amplification upside without overclaiming. Literature + C5 defended, not derived from an in-sample futures read. |
| **SD** (IC dispersion across formations) | **[0.10, 0.18]** | Identical to Carry/Trend/Flow/LAG. Monthly cross-sectional IC dispersion for a ~120–180-name SSF cross-section is dominated by true time-variation. **C5's cash-equity dispersion was higher** (the reason its composite power was only 0.54) — disclosed as the counterevidence; the bet is that the futures substrate (liquid, filtered, beta-neutralized) has lower dispersion. The gate-2 SD band check is the honest arbiter: if realized SD > 0.18, the C2 wide-SD stop fires and the sleeve halts. |
| **n\*** (formations in the sealed projection window) | **= 42** (monthly, sealed 2023-01 → 2026-07) | Same allocation as Flow/Skew/LAG. Continuous futures 2016-02-11 → 2026-07-20; first feasible formation 2017-02 (252-day beta warmup). TRAIN 2017-02 → 2020-12, HOLDOUT 2021-01 → 2022-12, SEALED 2023-01 → 2026-07 (~42). Calendar lever exhausted (NSE F&O pre-2016 unobtainable). |

### 7.1 The honest power picture — standalone vs. combined

`ncp = (delta / SD) · √n*`, one-sided α = 0.05. Verified against `scripts/rfa/power.py`:

| Corner | delta | SD | ncp (n*=42) | Power | Verdict |
|---|---|---|---|---|---|
| Optimistic | 0.060 | 0.10 | 3.889 | **0.9853** | **PROCEED** |
| Central | 0.050 | 0.14 | 2.315 | **0.7361** | below 0.80 but **near** |
| Pessimistic | 0.040 | 0.18 | 1.441 | 0.4096 | below |

At n* = 42, clearing standalone power 0.80 needs IR `delta/SD ≥ ~0.39`:
- **Optimistic** `(0.060 / 0.10)` → IR 0.60 → **clears comfortably** (n_required = 19).
- **Central** `(0.050 / 0.14)` → IR 0.357 → standalone power 0.7361, **just below** (n_required = 50; window holds 42).

**IVOL is the first candidate whose central case approaches standalone 0.80** (0.7361 vs
~0.55–0.57 for everyone else) — a direct consequence of C5's strong prior IC. As with all
sleeves, the 0.80 hurdle binds at the **composite** level with Carry; IVOL's standalone
TRAIN/HOLDOUT read is a sign + magnitude + fee + persistence check (§9 gates 2, 4, 5).

### 7.2 AC₁ / overlap
Monthly non-overlapping formations → no overlap autocorrelation. AC₁ reported at TRAIN; if
|AC₁| > 0.10, Newey-West SE haircut applies (same as PSB/Trend/LAG protocol).

---

## 8. Fees & cost model

Same as Carry/Trend/LAG §8: `core/execution/futures/futures_fees.py`.
- Futures STT sell-side only: 0.0125% (TRAIN) / 0.02% (post-Oct-2024).
- Exchange txn, SEBI, stamp, GST — era-accurate. Brokerage Rs 20/order.
- Slippage κ = 5 bp/side, plus ADV cap.

IVOL's slow-moving levels construction should produce turnover comparable to or below C5's
monthly-banded 0.04 (C5 realized 14 bp/yr drag) — the lowest of any candidate family.

---

## 9. Acceptance rule (pre-registered, evaluated before any sealed read)

**Windows:** TRAIN 2017-02 → 2020-12 (~47 monthly); HOLDOUT 2021-01 → 2022-12 (24 monthly);
SEALED 2023-01-01 → 2026-07-20 (~42 monthly) — **untouched** until gates 1–5 pass.
(Same Flow/Skew/LAG allocation maximizing the sealed window.)

Ordered gates:

1. **RFA gate** (declared bands, §7): single-sleeve bar is **PROCEED** (optimistic corner
   power 0.9853). ABANDON is dispositive.
2. **TRAIN:** mean rank-IC significant with the **declared (negative) sign** (t via AC₁-corrected
   SE, tested in the negative direction); net quintile spread > 0 under §8 fees (long low-vol,
   short high-vol); realized IC SD inside the declared [0.10, 0.18] band (if SD > 0.18, the C2
   wide-SD stop fires, sealed window preserved).
3. **HOLDOUT:** sign and net-spread persist; **no parameter touched** between TRAIN and HOLDOUT.
4. **Composite power check** (engine level): IVOL's TRAIN-estimated IR feeds the combined-engine
   power projection with Carry's read; 0.80 binds on the composite.
5. **Only then**, one **SEALED** read (2023-01 → present), reported whatever it shows.

Any gate failure → sleeve does not advance; **no successor auto-authorized**; sealed window
stays sealed if not yet reached.

---

## 10. Prior-exposure disclosure

- **PSB-1 C5 (cash-equity low-vol, monthly banded):** the **closest prior read**. C5 produced
  mean IC +0.068 (t=3.14, p=0.001), net +4.3%, 14 bp/yr drag — it cleared significance + sign +
  net and died only on composite power (0.54). IVOL differs in substrate (futures vs cash),
  universe (SSF-liquid vs broader cash), fee structure, and explicit beta-neutralization
  (residual vol, the BAB construct). Disclosed as prior-adjacent; **m counts this.**
- **Trend (dead) and LAG (dead):** in the broader vol/momentum neighborhood but different
  signals (own-name return, leader-gap). Disclosed.
- **Carry (survived):** different family (basis vs vol). Correlation measured on TRAIN.

With C5 + Trend + LAG, the honest minimum is **m ≥ 3** for the family-wise penalty. The exact
m and Bonferroni evidence floor are pinned at declaration freeze.

---

## 11. Falsifiable predictions (stated before the run)

1. **(Load-bearing)** IVOL rank-IC on TRAIN is **negative-signed** and its AC₁-corrected t-stat
   clears the threshold (|t| > 1.96, negative direction). The India-retail structural argument
   predicts mean |IC| **≥ 0.05** — if realized |IC| is in [0.02, 0.04] (weaker than C5), the
   amplification bet is falsified even if nominally significant.
2. IVOL is **not subsumed by Carry**: IC after residualizing against Carry's signal stays
   ≥ 60% of raw, same sign.
3. Net quintile spread > 0 (long low-vol, short high-vol) under §8 futures fees at monthly
   turnover.
4. Realized TRAIN IC SD lands inside the declared **[0.10, 0.18]** band (if > 0.18, the C2
   wide-SD pattern repeats and §9 gate 2 stops the sleeve).

If (1) or (3) fails, IVOL is not a viable sleeve. If (2) fails, IVOL is redundant with Carry
and adds no composite breadth regardless of its standalone IC.

---

## 12. Key files (to be created)

| File | Purpose |
|---|---|
| `governance/rfa/declarations/ivol.py` | Frozen RFA declaration (bands, n*=42, one-sided, negative sign) |
| `scripts/signal_engine/ivol/build_ivol.py` | §3 signal construction (realized vol → z → neutralized) |
| `scripts/signal_engine/ivol/run_train.py` | §9 TRAIN read → `IVOL_TRAIN_REPORT.md` |
| `tests/signal_engine/ivol/` | vol-construction + neutralization + fee unit tests |
| `docs/reports/IVOL_TRAIN_REPORT.md` | script-generated TRAIN report (no hand-edited numbers) |

Continuous-series store reused from Trend (fourth use: Carry-built → Trend → LAG → IVOL).

---

## 13. Engine viability — empirical, not projected

At IVOL's TRAIN, **Carry is the only other survivor.** The composite is **Carry + IVOL (2
sleeves)** if IVOL passes. Crucially, Carry (basis) and IVOL (volatility) are **different
economic families** → plausibly weakly correlated → the breadth thesis rewards this most
(`IR ≈ √(Σ IR_i²)` rewards independence, not size).

At n* = 42 with Carry IR ≈ 0.31 (HOLDOUT IC 0.046 / SD ~0.15) and IVOL central IR ≈ 0.36:
`composite IR ≈ √(0.31² + 0.36²) = 0.47` (if uncorrelated) → composite power at n*=42 ≈ 0.90.
**This clears 0.80 at the composite with central assumptions** — the first 2-sleeve pairing in
the engine projected to do so, because both members are decorrelated and both have real
(>0.03) ICs. (Projection only; the composite verdict is empirical after TRAIN, per §9 gate 4.)

If realized IVOL IR is weaker (pessimistic ~0.20) or Carry/IVOL correlation is high (>0.4),
composite power drops below 0.80 and the engine either accepts the realized shortfall
explicitly or stops — never forces a third sleeve to hit the target.

---

## 14. Freeze

On approval: compute SHA-256 over this file (excluding this line), record it here and in
`ivol.py`, and treat §1 (sign — negative), §3 (construction — 60-day vol window), §4
(neutralization), §6 (cadence/caps), §7 (bands), §9 (acceptance rule) and §10 (prior exposure
/ m) as immutable. Any change after freeze starts a new pre-registration.
