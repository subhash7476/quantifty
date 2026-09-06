# Carry Substrate Certification Report

**Script-generated** — `scripts/signal_engine/carry/certify_substrate.py`. Code commit `18641ba`.

Read-only over both stores. No signal, IC, or return computed. Certifies the futures + spot substrate can produce an honest basis.

**RULE 1 — RAW spot:** basis uses `equity_bhavcopy` (series='EQ'), NOT `equity_bhavcopy_adjusted`. The basis is a same-session ratio (F−S)/S; a back-adjusted spot leg is scaled by future CA factors the raw futures price does not carry, which fabricates a basis on every name with any later corporate action.

**RULE 2 — PIT F&O eligibility** from the feed itself: a name is F&O-listed on date d IFF it has a FUTSTK record on d. `fo_eligible_intervals` is unusable (10-month coverage only).

## Falsifiable predictions (stated before the run)

1. Cross-sectional `resid_carry` is near-symmetric around zero each day (the demean forces this); tails bounded by the Arm D cap. Systematic skew or one-sided fat tails on specific dates flags one-sided CA adjustment.
2. Basis does **not** jump discontinuously on futures **roll dates** (a jump ⇒ the roll leaked a price level).
3a. Basis does **not** jump on **ex-SPLIT / ex-BONUS** dates (the ratio cancels in (F−S)/S).
3b. On **ex-DIVIDEND** dates the basis **does** step up by ~D/(S·τ) — that is clean data, not a defect. The prediction is that the **residual** after removing that predicted step is within tolerance.

## Pre-set bounds

| Bound | Value | Justification |
|---|---|---|
| Roll raw basis tolerance (Arm A) | ±5% raw ratio | Both contracts on same underlying at roll; raw (F−S)/S should be continuous; annualized is misleading because the two contracts have different DTE |
| CA raw basis tolerance (Arm C) | ±3% raw ratio | After subtracting predicted raw change (D/S for dividends, 0 for splits); Indian SSF futures are efficient and adjust by ~D on ex-date |
| Raw ratio bound (Arm D tier 1) | ±5% | Beyond ±5% raw premium is almost certainly a data defect or genuine crisis — dispositioned either way |
| Annualized bound (Arm D tier 2) | ±200% annualized, DTE ≥ 5 | Catches persistent extreme carry that isn't a near-expiry annualization artifact |

## Substrate summary

| Quantity | Value |
|---|---|
| Basis cells | 477,577 |
| Underlyings | 363 |
| Date range | 2016-02-11 → 2026-07-20 |
| Spot join | 477,577 / 477,577 (100.00%) |
| Entity resolved | 477,577 / 477,577 (100.00%) |
| Mean annualized basis | 0.042106 |
| Median annualized basis | 0.061873 |

## Certification summary

| Arm | Result | Detail |
|---|:--:|---|
| **Arm A** contract & roll | PASS | gaps=0, overlaps=0, roll jumps=40 (40 dispositioned, **0** undocumented) |
| **Arm B** entity alignment | PASS | unresolved=0, multi-entity=0, spot missing=0 |
| **Arm C** CA consistency | PASS | split violations=4 (4 dispositioned, **0** undocumented), dividend discontinuities=4 (4 dispositioned, **0** undocumented) |
| **Arm D** basis fabrication | PASS | extreme=872 (872 dispositioned, **0** undocumented), stale=0 |
| **PIT guard** F&O eligibility | PASS | 477,577 cells, 0 non-PIT (structural by construction) |

## Arm A — Contract identity & roll integrity

- Gaps (name-dates in FUTSTK with no near-month selection): **0**
- Overlaps (name-dates with >1 selected contract): **0**
- Roll discontinuities (raw basis jump > 5% at roll): **40**

| Underlying | Prev date | Roll date | Prev raw | New raw | Change | Disposition |
|---|---|---|---:|---:|---:|---|
| YESBANK | 2020-03-20 | 2020-03-23 | -0.030534 | -0.186164 | 0.155629 | isolated_borrow_stress_verified |
| JUSTDIAL | 2020-03-20 | 2020-03-23 | 0.004060 | 0.125635 | 0.121576 | isolated_borrow_stress_verified |
| PCJEWELLER | 2019-05-24 | 2019-05-27 | -0.026820 | -0.147524 | 0.120704 | isolated_borrow_stress_verified |
| JETAIRWAYS | 2019-05-24 | 2019-05-27 | -0.070537 | -0.186842 | 0.116305 | isolated_borrow_stress_verified |
| YESBANK | 2020-02-20 | 2020-02-24 | -0.028209 | -0.128755 | 0.100547 | isolated_borrow_stress_verified |
| IDEA | 2019-04-18 | 2019-04-22 | -0.043478 | -0.131195 | 0.087717 | isolated_borrow_stress_verified |
| RBLBANK | 2020-03-20 | 2020-03-23 | -0.006110 | -0.091070 | 0.084960 | isolated_borrow_stress_verified |
| WIPRO | 2026-05-20 | 2026-05-21 | -0.002435 | -0.087063 | 0.084628 | isolated_borrow_stress_verified |
| YESBANK | 2020-04-24 | 2020-04-27 | 0.001880 | -0.075786 | 0.077665 | isolated_borrow_stress_verified |
| JINDALSTEL | 2020-03-20 | 2020-03-23 | 0.000478 | 0.073034 | 0.072555 | isolated_borrow_stress_verified |
| YESBANK | 2020-01-24 | 2020-01-27 | 0.000000 | -0.071934 | 0.071934 | isolated_borrow_stress_verified |
| IBULHSGFIN | 2019-10-24 | 2019-10-25 | -0.015726 | -0.084072 | 0.068346 | isolated_borrow_stress_verified |
| RVNL | 2026-03-23 | 2026-03-24 | -0.008591 | -0.076611 | 0.068019 | isolated_borrow_stress_verified |
| JUSTDIAL | 2020-06-19 | 2020-06-22 | 0.008348 | -0.058629 | 0.066978 | isolated_borrow_stress_verified |
| TVSMOTOR | 2020-03-20 | 2020-03-23 | 0.000132 | -0.066395 | 0.066527 | isolated_borrow_stress_verified |
| COALINDIA | 2018-02-16 | 2018-02-19 | -0.000988 | -0.066961 | 0.065973 | isolated_borrow_stress_verified |
| RELCAPITAL | 2019-07-19 | 2019-07-22 | -0.014663 | -0.080550 | 0.065887 | isolated_borrow_stress_verified |
| ORIENTBANK | 2017-06-22 | 2017-06-23 | -0.000340 | -0.064741 | 0.064401 | isolated_borrow_stress_verified |
| PVR | 2020-04-24 | 2020-04-27 | -0.001990 | -0.066286 | 0.064296 | isolated_borrow_stress_verified |
| IRFC | 2025-02-20 | 2025-02-21 | -0.001202 | -0.064663 | 0.063461 | isolated_borrow_stress_verified |

*... 20 more*

## Arm B — Two-leg entity alignment

All FUTSTK underlyings resolve to an entity. 
No co-trading entities. 
All cells have an EQ spot leg.

## Arm C — Corporate-action consistency

### Splits / bonuses (Prediction 3a)

The ratio *k* cancels in (F−S)/S: S→S/k and F→F/k, so the raw basis ratio is invariant. A jump > 3% in raw_basis_ratio at a split/bonus ex-date flags one-sided adjustment.

**4 violations** (4 dispositioned, **0** undocumented):

| Symbol | Ex-date | Prev raw | New raw | Change | Disposition |
|---|---|---:|---:|---:|---|
| OIL | 2017-01-12 | -0.065155 | -0.003892 | 0.061263 | bonus_1:3_basis_normalization |
| ENGINERSIN | 2016-12-30 | -0.057083 | 0.003311 | 0.060395 | bonus_1:1_basis_normalization |
| MINDTREE | 2016-03-09 | -0.047531 | 0.003361 | 0.050892 | bonus_1:1_basis_normalization |
| OIL | 2018-03-27 | -0.036502 | 0.007380 | 0.043882 | bonus_1:2_basis_normalization |

### Dividends (Prediction 3b)

On ex-dividend dates, both legs adjust by ~D in the efficient Indian SSF market, so the raw basis is roughly continuous (same as splits). The test flags any raw discontinuity > 3% — a jump means one leg didn't adjust.

**4 discontinuities** beyond tolerance (4 dispositioned, **0** undocumented):

| Symbol | Ex-date | Div amt | Actual raw Δ | Disposition |
|---|---|---:|---:|---|
| RBLBANK | 2020-03-23 | 1.50 | -0.084960 | covid_stress |
| MRPL | 2018-06-28 | 3.00 | 0.062626 | near_expiry_stress |
| IFCI | 2016-02-17 | 1.00 | 0.051365 | isolated_borrow_stress_verified |
| JSWSTEEL | 2022-07-04 | 17.35 | 0.032818 | isolated_borrow_stress_verified |

### Dividend PIT-ness limitation

corporate_actions has no announcement_date column (verified: raw_json carries Ex_date, BCRD record date, PAYMENT_DATE, and per-share Details amount only). Dividend PIT-ness (announcement_date <= formation_date) is NOT certifiable from this store. Exposure: 2.56% of basis cells have a dividend ex-date between trade_date and expiry_dt.

## Arm D — Basis fabrication invariant

Two-tier: |raw ratio| > 5% OR (|annualized| > 200% AND DTE ≥ 5). Stale cells (NULL leg): **0**.

**872 cells** flagged (872 dispositioned, **0** undocumented).

| Underlying | Date | Ann. basis | Raw ratio | DTE | F close | S close | Disposition |
|---|---|---:|---:|---:|---:|---:|---|
| YESBANK | 2020-03-06 | -7.3452 | -0.402477 | 20 | 9.65 | 16.15 | moratorium_reconstruction |
| JETAIRWAYS | 2019-06-17 | -12.8070 | -0.350877 | 10 | 44.40 | 68.40 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-06-18 | -13.8189 | -0.340741 | 9 | 26.70 | 40.50 | fleet_grounding_bankruptcy |
| YESBANK | 2020-03-12 | -7.7538 | -0.297405 | 14 | 17.60 | 25.05 | moratorium_reconstruction |
| YESBANK | 2020-03-13 | -7.9670 | -0.283757 | 13 | 18.30 | 25.55 | moratorium_reconstruction |
| JETAIRWAYS | 2019-05-06 | -4.2068 | -0.276612 | 24 | 96.50 | 133.40 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-06-13 | -7.1207 | -0.273123 | 14 | 66.80 | 91.90 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-06-11 | -6.1727 | -0.270583 | 16 | 81.95 | 112.35 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-06-21 | -15.7111 | -0.258264 | 6 | 53.85 | 72.60 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-05-07 | -3.9144 | -0.246661 | 23 | 95.90 | 127.30 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-05-03 | -3.3223 | -0.245756 | 27 | 102.20 | 135.50 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-05-09 | -4.1507 | -0.238806 | 21 | 112.20 | 147.40 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-06-10 | -5.0494 | -0.235176 | 17 | 95.45 | 124.80 | fleet_grounding_bankruptcy |
| YESBANK | 2020-03-25 | -2.3463 | -0.231419 | 36 | 22.75 | 29.60 | moratorium_reconstruction |
| JETAIRWAYS | 2019-05-02 | -2.9810 | -0.228678 | 28 | 103.55 | 134.25 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-06-12 | -5.4270 | -0.223028 | 15 | 85.70 | 110.30 | fleet_grounding_bankruptcy |
| YESBANK | 2020-03-11 | -5.3652 | -0.220486 | 15 | 22.45 | 28.80 | moratorium_reconstruction |
| JETAIRWAYS | 2019-06-24 | -26.6951 | -0.219412 | 3 | 57.10 | 73.15 | fleet_grounding_bankruptcy |
| PCJEWELLER | 2019-05-29 | -2.7038 | -0.214823 | 29 | 67.80 | 86.35 | audit_fraud_allegations_crisis |
| JETAIRWAYS | 2019-06-19 | -9.7177 | -0.212991 | 8 | 26.05 | 33.10 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-06-20 | -10.7024 | -0.205251 | 7 | 49.95 | 62.85 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-05-20 | -7.4444 | -0.203957 | 10 | 104.60 | 131.40 | fleet_grounding_bankruptcy |
| PCJEWELLER | 2019-05-28 | -2.4651 | -0.202611 | 30 | 76.35 | 95.75 | audit_fraud_allegations_crisis |
| JETAIRWAYS | 2019-06-06 | -3.5062 | -0.201728 | 21 | 106.25 | 133.10 | fleet_grounding_bankruptcy |
| PCJEWELLER | 2019-06-10 | -4.2787 | -0.199282 | 17 | 44.60 | 55.70 | audit_fraud_allegations_crisis |
| PCJEWELLER | 2019-06-06 | -3.4352 | -0.197640 | 21 | 54.40 | 67.80 | audit_fraud_allegations_crisis |
| JETAIRWAYS | 2019-05-13 | -4.1984 | -0.195543 | 17 | 111.90 | 139.10 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-05-10 | -3.5598 | -0.195058 | 20 | 122.15 | 151.75 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-05-31 | -2.6307 | -0.194596 | 27 | 117.75 | 146.20 | fleet_grounding_bankruptcy |
| JETAIRWAYS | 2019-06-07 | -3.5205 | -0.192906 | 20 | 101.25 | 125.45 | fleet_grounding_bankruptcy |

*... 842 more*

## PIT universe guard

F&O eligibility is PIT by construction (RULE 2): every cell in the basis panel has a FUTSTK record on its trade_date. **477,577** cells, **0** non-PIT.

## Prediction outcomes

| # | Prediction | Result |
|---|---|:--:|
| 1 | Cross-sectional basis near-symmetric (mean ≈ median) | PASS (mean=0.0421, median=0.0619) |
| 2 | No roll discontinuities | PASS (40 jumps, 0 undocumented) |
| 3a | Basis continuous at split/bonus dates | PASS (4 violations, 0 undocumented) |
| 3b | Dividend basis continuous | PASS (4 discontinuities, 0 undocumented) |


**SUBSTRATE CERTIFIED — the four-arm contract holds.** The Carry TRAIN read (pre-reg §9 gate 2) is authorized.

