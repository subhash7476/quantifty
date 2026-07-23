# TS Basis Sleeve — Phase 0 Pre-Registration (DRAFT)

**Status:** DRAFT. To be **FROZEN** on operator approval (SHA-256 over the whole file);
bands cannot be revised in response to results once frozen.
**Parent design:** `SIGNAL_ENGINE_DESIGN.md` — this is a new sleeve, validated
standalone before it may enter the combined engine.
**Consumes:** no sealed data. This document authorizes the RFA power pre-check and, if
it returns PROCEED, the TRAIN/HOLDOUT empirical protocol. The 2023→present window stays
**sealed and unread** until the acceptance rule is met on TRAIN and HOLDOUT.

---

## 0. Prior exposure — the discipline core (mandatory)

The cross-sectional carry signal (Carry v2, positive sign, `CARRY_V2_PRE_REGISTRATION.md`
SHA `74c7311c…`) has been seen on TRAIN and HOLDOUT. The TS Basis signal is constructed
from the same underlying data (annualized futures basis, `raw_ann_basis` column in
`signals.duckdb`) but processes it differently: where cross-sectional carry ranks names
against each other at each formation date, TS Basis ranks each name against its own
history. The two signals read from the same source but compute different statistics; they
are partially correlated (both use the basis as input) but measure different dimensions.

Consequence: this is NOT a clean-sheet greenfield. The TRAIN window has been seen for the
cross-sectional carry sign, and because the same basis data was used to construct the TS
signal, the IC magnitude on TRAIN carries an "in-sample" flavor — it was not pre-registered
before seeing these data. This is disclosed here and accounted for in §7:

1. **TRAIN carries ZERO confirmatory weight for the TS Basis sign** — it is spent on
   cross-sectional carry sign discovery. The train IC is reported for completeness but
   the acceptance gate relies on HOLDOUT alone.
2. **Only HOLDOUT (2021–2022, ~24 monthly formations) provides out-of-sample confirmation.**
   It is a small window and may be underpowered. The bar is therefore set accordingly (§5).
3. **Multiplicity:** the operator has now tested at least two basis-derived signals on the
   same data. m ≥ 2. The evidence floor deflates accordingly.

---

## 1. Hypothesis (falsifiable)

For each single-stock-futures underlying, the annualized basis (`F−S`)/S × 365/DTE)
exhibits time-series persistence: when a name's current basis is unusually wide relative
to its own trailing 504-day distribution, the basis tends to remain wide, and the stock
continues to outperform over the following month. When unusually narrow, underperformance
persists.

Formally: `z_ts_i(t) = (basis_i(t) − μ_i(t)) / σ_i(t)`, where μ_i(t) and σ_i(t) are the
trailing 504-calendar-day mean and standard deviation of `basis_i` at time t. The
cross-sectional rank of `z_ts_i` on formation date t predicts the cross-sectional rank of
forward 1-month returns.

Sign is declared now and cannot be flipped: **long high z_ts, short low z_ts.**
(Economic reading: unusually wide basis signals elevated demand for leveraged longs or
scarce borrow — the underlying pressure persists rather than mean-reverting within one month.)

If realized IC is significant with the *opposite* sign on HOLDOUT, the hypothesis is
falsified — not re-labelled.

While this sign aligns with the cross-sectional carry v2 positive sign (both: high
basis → long), they are analytically distinct: cross-sectional carry ranks against peers;
TS Basis ranks against the name's own history. It is possible for one to work while the
other does not.

---

## 2. Universe & point-in-time membership

- **Universe:** NSE F&O-eligible single-stock names, **point-in-time.** Same universe as
  cross-sectional carry — a name is eligible at formation t only if it was F&O-listed and
  liquid at t.
- **Liquidity screen:** trailing 20-day median futures turnover ≥ ₹5 Cr. Same as carry.
- **ADV cap:** position ≤ 10% of trailing 20-day average daily value, enforced at
  construction (§6).
- **Expected N per formation:** ~120–180 names post-screen. Same as carry.

---

## 3. Signal construction (exact, pre-registered)

No dividends. No cross-sectional demeaning. No beta/sector neutralization. The signal
is computed per-name, purely from the time series of its own basis.

1. **Load basis:** for each underlying at each monthly formation date, read `raw_ann_basis`
   from the basis panel (annualized `(F−S)/S × 365/DTE`).
2. **Trailing statistics:** compute μ_i(t) = mean of `raw_ann_basis_i` over the prior
   504 calendar days (all formation dates within that window). Compute σ_i(t) similarly
   (sample std, ddof=1). Require ≥12 prior observations within the window.
3. **Z-score:** `z_ts_i(t) = (basis_i(t) − μ_i(t)) / σ_i(t)`.
4. **Winsorize:** clip z_ts to ±3σ. (Conservative: the denominator σ is already
   per-name, but extreme jumps from a single outlier month still need containment.)
5. **Output:** store `z_ts` per `(formation_date, underlying)` in a signal table.

No further processing. The cross-sectional rank of z_ts within each formation date
determines quintile membership.

---

## 4. Portfolio construction (same as carry)

- **Formation:** monthly, last trading day of each calendar month.
- **Quintile:** top 20% of names by z_ts → **LONG**. Bottom 20% → **SHORT**.
- **Weighting:** equal-weight within each leg (`half_gross / n` per name).
- **ADV cap:** position ≤ 10% of trailing 20-day ADV, enforced after equal-weight
  allocation and re-normalized per leg.
- **No-trade band:** 0.25σ of cross-sectional target weights. Deltas |Δ| < band are
  suppressed; positions that are merely scaled stay at their current size until the
  next rebalance crosses the band. OPEN/CLOSE/FLIP are never suppressed.
- **Gross exposure:** ₹1 Cr (₹50 lakh/leg), fixed.

---

## 5. Fees (era-accurate, same as carry)

Canonical futures fee model from `core/execution/futures/futures_fees.py`:
- STT: 0.0100% ≤ 2023-03-31 · 0.0125% 2023-04-01 → 2024-09-30 · 0.0200% ≥ 2024-10-01
  (SELL side only, derivatives rate)
- Exchange txn: 0.0021% pre-2024-10 / 0.00189% post-2024-10 (both legs)
- SEBI: 0.0001% (both legs, stable)
- Stamp: 0.010% pre-2020-07-01 / 0.002% post-2020-07-01 (BUY side)
- GST: era-accurate 18% post-2017-07-01, service-tax rates pre-2017
- Brokerage: ₹20 flat per order
- Slippage: 5 bp/side (modeling choice, fixed)

---

## 6. Falsifiable predictions (before the HOLDOUT read)

1. **HOLDOUT IC is positive-signed** (high z_ts → high forward return) and significant
   at the one-sided α level adjusted for multiplicity (§7).
2. **Net quintile spread > 0** under §5 fees, annualized.
3. **Magnitude is comparable to TRAIN** (IC likely in the +0.03 to +0.09 range, given
   the partial correlation with cross-sectional carry).

If HOLDOUT is negative-signed or insignificant **and** net ≤ 0, the persistence hypothesis
is falsified. There is no v2 — this is a distinct signal from cross-sectional carry, and
there is no sign-flip path since the positive sign was assigned from the cross-sectional
carry v2's own experiment.

---

## 7. Multiplicity & evidence floor

| Signal tested | Test | Window | Outcome |
|---|---|---|---|
| Cross-sectional carry | Sign(−) | TRAIN | Falsified (v1) |
| Cross-sectional carry | Sign(+) | TRAIN | Seen (v2, discovered-on-train) |
| Cross-sectional carry | Sign(+) | HOLDOUT | Confirmed |
| Cross-sectional carry | Sign(+) | SEALED | Confirmed (+20.52%) |
| **TS Basis** | Sign(+) | TRAIN | **Seen (this document — prior exposure)** |
| **TS Basis** | Sign(+) | HOLDOUT | **To be tested** |

m ≥ 2 (cross-sectional carry sign discovery on TRAIN + TS Basis sign discovery on TRAIN).
HOLDOUT significance at **Bonferroni α = 0.05/2 = 0.025**, one-sided.

Note: the SEALED read for cross-sectional carry does not increment m for TS Basis —
it was a confirmation of the carry sign on an independent window and did not involve
the TS Basis construction.

---

## 8. What would make this illegitimate (explicit guardrail)

- Touching the lookback window (504d), min_obs (12), or any construction parameter
  after seeing the HOLDOUT result. All are declared here and frozen.
- Spinning a negative HOLDOUT IC as "still directionally aligned with carry" — the
  sign test is binary and the declared sign is unfalsifiable only if it loses.
- Using TRAIN as confirmation — it is burned for this signal's sign discovery.
- Composite-splitting: testing TS Basis on a subset of names (e.g., Nifty 50 only)
  after the full-book result is seen and claiming that subset as a distinct construct.
- Re-running HOLDOUT more than once.

---

## 9. Freeze

To be frozen on operator approval. SHA-256 over this file.
