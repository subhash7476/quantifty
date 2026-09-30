# M3a × M5b — Range Breakout + Abnormal-Volume Confirmation — Research Report (BKV-1)

**Question.** When an individual stock breaks out of a multi-day closing range, does unusually high same-day volume distinguish breakouts that continue from breakouts that fail?
**Protocol:** `BREAKOUT_VOLUME_PROTOCOL.md` v1.0, frozen at commit `84fcd99` (record `breakout_volume_FREEZE.json`); **no forward return existed before that commit.** Two logged verifier/output amendments followed (A1, A2 — §7.4); neither touched the engine, the analysis, the classification rule or any result.
**Branch / worktree:** `research/breakout-volume`, `F:\Nifty_bkv`. **All tables are rendered by `scripts/breakout_vol/build_report.py` from the files in `docs/reports/research/breakout_volume/`. Numbers quoted in the prose were transcribed by hand and cross-checked against those tables (the cross-check found and corrected the errors listed in §7.4, item E).**

---

## 1. Executive summary

* **Final classification: C5 — construct-scoped** (the pre-registered criterion was tested on data and failed). `classification.json` = "C5". No defect trigger fired. **The HOLDOUT (2023-01 → 2026-09) was never read** — the protocol stops at a failed VAL — so no window was spent and the operator question about spending it never arose.
* **Primary test.** 8 pre-declared cells (N ∈ {20, 63} × H ∈ {5, 20} × up/down). The statistic is the paired within-date difference in direction-signed, market-excess forward return between breakouts **with** abnormal volume (B) and **without** (C). **0 of 8 cells is confirmed in VAL** (Holm-8 adjusted p = 1.000 in every cell; smallest unadjusted one-sided p = 0.159, down-side N=20 H=5, d̄ = +39 bp, 95 % CI [−36, +125] bp).
* **The up-side sign is opposite to the hypothesis in every cell and both windows.** Volume-confirmed *upside* breakouts continued *less* than unconfirmed ones (VAL d̄ = −52, −104, −6, −24 bp; TRAIN −10, −87, −39, −80 bp). The pre-registered test is one-sided in the continuation direction, so this is a **distinct finding, never counted as support**, and no test of it was pre-registered (the two-sided p for the N=20 H=5 cell would be ≈ 0.05 unadjusted).
* **Power is the binding constraint, and it is disclosed as such.** The minimum detectable effect (80 % power, one-sided) is 67–253 bp per cell in VAL (§5). A null here means *this design cannot demonstrate a volume premium smaller than that*; it does **not** show that volume is irrelevant.
* **Auditability.** All six independent checks pass in both stages (§6): a pure-SQL re-derivation matches the engine on **19,761 (TRAIN) and 17,067 (VAL) events with zero exceptions** (max |Δf| ≈ 2e-12 bp); a raw as-traded rebuild, a hand Newey–West + `statsmodels` kernel, accounting identities and fee arithmetic agree. Nothing is marked NOT AUDITABLE.
* **Economics (descriptive).** Round-trip statutory + DP cost ≈ 22 bp of notional before slippage. In VAL the up-side B arm is negative net of cost in all four cells; in TRAIN it is net-positive in three of four (largest at H = 20, which carries 2012–17 market drift in a raw, un-netted number). The down-side B arm shows positive short-proxy nets in VAL but is not distinguishable from C and flips sign across windows (§8).

## 2. Frozen research question and protocol

See `BREAKOUT_VOLUME_PROTOCOL.md`. Pinned before any result: closing-range breakout `C_t > max(C_{t−N..t−1})` (N = 20, 63; mirror for downside), **onset only** (no same-side breakout flag in the prior 20 sessions), abnormal volume `V_t ≥ 2 × median(V_{t−20..t−1})`, arms A = B ⊔ C and the control D, entry at the adjusted open of t+1, exit at the close of t+H (H = 5, 20), estimand `f = sign·(R − R_m)` in bp with `R_m` the equal-weight mean over the PIT top-200 members with a resolved window, paired-by-date contrast, calendar-aware Newey–West with lag H, Holm over 8 cells. Vault vocabulary mapping (C4–C9) fixed in protocol §10.

## 3. Exact signal / event definitions

For entity *e*, regular-calendar session *t*, adjusted OHLCV:

| Object | Formula (units) |
|---|---|
| Range level | `Mx_N(t) = max(C_{t−N}…C_{t−1})`, `Mn_N(t) = min(C_{t−N}…C_{t−1})` (price) |
| Breakout | `UP = [C_t > Mx_N]`, `DN = [C_t < Mn_N]` |
| Onset | `UP ∧ (UP_s = 0 ∀ s∈[t−20, t−1])` (same for DN) — uses breakout flags only, never volume |
| Abnormal volume | `AV = V_t / median(V_{t−20}…V_{t−1})`, `ABN = [AV ≥ 2.0]` (shares ratio) |
| Arms | B = onset ∧ ABN; C = onset ∧ ¬ABN; A = B ⊔ C; D = ABN ∧ ¬UP ∧ ¬DN ∧ (no ABN in t−20…t−1), signed by sign(C_t − C_{t−1}) |
| Return | `R = C_{t+H}/O_{t+1} − 1`; `R_m` = mean R over members at t with a resolved window (≥ 100 names) |
| Estimand | `f = sign·(R − R_m)·10⁴` bp, sign = +1 up/D_up, −1 down/D_dn; continuation > 0 |
| Test | `d(t) = m_B(t) − m_C(t)` on dates with both arms; d̄; SE from calendar-aware NW, lag = H; one-sided Student-t, n−1 df; Holm-8 |

## 4. Data provenance and sample construction

* **Store and snapshot.** `equity_bhavcopy_adjusted` (CA-adjusted OHLC, volume divided by the cumulative bonus/split factor). One hashed snapshot of 1,341,582 rows ≤ 2022-12-30 (the store runs to 2026-09-29; fence non-vacuous): panel `46de7d4d…`, calendar `73addee2…`, membership `db87add8…` (`manifest_dev.json`, in the freeze record).
* **Universe.** PSB/CSMP point-in-time top-200 by trailing-6-month median turnover, monthly rebalance; membership at *t* = the **last rebalance strictly before t**; entity by `universe_eligibility`; delisted names stay while listed.
* **Calendar.** 26 snapshot-span dates removed by rule (weekends, Muhurat/short sessions by turnover < 0.40 × neighbourhood, n_symbols < 200 — incl. 2016-04-19 which the store lists as `unresolved`, and 2017-07-10 whose cause is unverified); list in `breakout_volume_diagnostics_outcome_free.json`. The rule was checked outcome-free against a trailing median: identical dates.
* **Sessions.** TRAIN 2012-01-02 → 2017-12-29 = 1,474; VAL 2018-01-01 → 2022-12-30 = 1,233.
* **Eligibility.** Valid rows on all 84 sessions t−83…t and PIT member. Eligible name-days: TRAIN 290,347; VAL 246,287 (of 290,600 / 246,600 member-days — 99.9 %).
* **Funnel (reconciliation).** Breakout flags before the onset rule vs events after it (counts only, from the outcome-free diagnostics): TRAIN N20 up 36,408 → 4,533; VAL N20 up 30,248 → 3,775. Cell-level funnel below; every row satisfies *formed = resolved + dropped + window-beyond-stage + no-benchmark* and *A = B + C* (asserted in code and re-checked by VP4).

**VAL funnel**

| cell | formed | resolved in stage | dropped | window beyond stage | no benchmark | terminal ⊂ resolved | B / C / D resolved | A = B + C | identity: resolved + dropped + beyond + no-bench = formed |
|---|---|---|---|---|---|---|---|---|---|
| N20_H5_up | 5066 | 5049 | 1 | 16 | 0 | 0 | 1425 / 2344 / 1280 | ✓ | ✓ |
| N20_H5_dn | 4711 | 4699 | 1 | 11 | 0 | 1 | 626 / 3384 / 689 | ✓ | ✓ |
| N20_H20_up | 5066 | 5010 | 2 | 54 | 0 | 4 | 1412 / 2326 / 1272 | ✓ | ✓ |
| N20_H20_dn | 4711 | 4574 | 2 | 135 | 0 | 2 | 615 / 3274 / 685 | ✓ | ✓ |
| N63_H5_up | 4155 | 4141 | 0 | 14 | 0 | 1 | 1216 / 996 / 1929 | ✓ | ✓ |
| N63_H5_dn | 3135 | 3126 | 1 | 8 | 0 | 1 | 590 / 1517 / 1019 | ✓ | ✓ |
| N63_H20_up | 4155 | 4111 | 2 | 42 | 0 | 2 | 1201 / 991 / 1919 | ✓ | ✓ |
| N63_H20_dn | 3135 | 3064 | 2 | 69 | 0 | 1 | 579 / 1475 / 1010 | ✓ | ✓ |

**TRAIN funnel**

| cell | formed | resolved in stage | dropped | window beyond stage | no benchmark | terminal ⊂ resolved | B / C / D resolved | A = B + C | identity: resolved + dropped + beyond + no-bench = formed |
|---|---|---|---|---|---|---|---|---|---|
| N20_H5_up | 5990 | 5956 | 0 | 34 | 0 | 2 | 1790 / 2712 / 1454 | ✓ | ✓ |
| N20_H5_dn | 5479 | 5473 | 1 | 5 | 0 | 0 | 718 / 3996 / 759 | ✓ | ✓ |
| N20_H20_up | 5990 | 5868 | 0 | 122 | 0 | 6 | 1764 / 2670 / 1434 | ✓ | ✓ |
| N20_H20_dn | 5479 | 5420 | 1 | 58 | 0 | 5 | 718 / 3948 / 754 | ✓ | ✓ |
| N63_H5_up | 4855 | 4827 | 0 | 28 | 0 | 3 | 1464 / 1246 / 2117 | ✓ | ✓ |
| N63_H5_dn | 3437 | 3434 | 1 | 2 | 0 | 0 | 554 / 1732 / 1148 | ✓ | ✓ |
| N63_H20_up | 4855 | 4765 | 0 | 90 | 0 | 6 | 1448 / 1236 / 2081 | ✓ | ✓ |
| N63_H20_dn | 3437 | 3406 | 1 | 30 | 0 | 1 | 553 / 1711 / 1142 | ✓ | ✓ |

## 5. Primary results

Units: bp of entry-open notional, direction-signed so that continuation is positive, net of the same-window equal-weight universe return. m_B and m_C are the means of the per-date cohort means over each arm's own dates, so m_B − m_C differs slightly from d̄, which is the mean of the per-date differences over the paired dates only (the *n_B*, *n_C* columns count events). MDE80 = (z₀.₉₅ + z₀.₈₀)·SE = 2.486·SE.

### 5.1 VAL — confirmatory (Holm over the 8 cells)

| N | H | side | pair dates | n_B | n_C | m_B (bp) | m_C (bp) | d̄ = B−C (bp) | NW SE | t | p (1-sided) | Holm-8 p | MDE80 (bp) | 95% block-boot CI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 5 | up | 505 | 1425 | 2344 | -36.4 | 15.8 | -52.4 | 27.1 | -1.94 | 0.973 | 1.000 | 67 | [-105, -3] |
| 20 | 5 | dn | 329 | 626 | 3384 | 59.6 | 19.7 | 39.1 | 39.0 | 1.00 | 0.159 | 1.000 | 97 | [-36, 125] |
| 20 | 20 | up | 500 | 1412 | 2326 | -74.5 | 41.1 | -104.3 | 58.0 | -1.80 | 0.964 | 1.000 | 144 | [-220, 8] |
| 20 | 20 | dn | 320 | 615 | 3274 | 83.2 | 4.9 | 58.5 | 75.4 | 0.78 | 0.219 | 1.000 | 187 | [-106, 225] |
| 63 | 5 | up | 367 | 1216 | 996 | -11.2 | -26.9 | -6.1 | 31.2 | -0.20 | 0.578 | 1.000 | 78 | [-65, 55] |
| 63 | 5 | dn | 236 | 590 | 1517 | -5.5 | 27.2 | -6.8 | 46.4 | -0.15 | 0.558 | 1.000 | 115 | [-105, 84] |
| 63 | 20 | up | 365 | 1201 | 991 | -28.9 | -14.2 | -23.8 | 59.3 | -0.40 | 0.656 | 1.000 | 147 | [-139, 92] |
| 63 | 20 | dn | 234 | 579 | 1475 | -37.2 | 73.1 | -117.4 | 101.7 | -1.15 | 0.875 | 1.000 | 253 | [-290, 49] |

**Reading.** No cell has Holm-adjusted p below 0.05; none is confirmed (classifier: `val_confirmed = []`). Every up-side cell has d̄ < 0. The down-side sign is positive at N=20 and mixed at N=63. Every 95 % CI contains zero except the N=20 H=5 up cell, whose CI lies entirely below zero (the wrong-signed direction). MDEs (67–253 bp) exceed the point estimates in all cells: the design has power only against sizeable effects.

### 5.2 TRAIN — descriptive only (no decision, nothing pinned or changed on it)

| N | H | side | pair dates | n_B | n_C | m_B (bp) | m_C (bp) | d̄ = B−C (bp) | NW SE | t | p (1-sided) | Holm-8 p | MDE80 (bp) | 95% block-boot CI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 5 | up | 601 | 1790 | 2712 | -15.8 | -4.4 | -10.0 | 21.9 | -0.46 | 0.676 |  | 55 | [-52, 32] |
| 20 | 5 | dn | 359 | 718 | 3996 | 32.6 | -5.2 | 33.4 | 29.4 | 1.14 | 0.129 |  | 73 | [-24, 93] |
| 20 | 20 | up | 593 | 1764 | 2670 | -36.7 | 2.8 | -87.4 | 51.9 | -1.69 | 0.954 |  | 129 | [-186, 9] |
| 20 | 20 | dn | 359 | 718 | 3948 | 60.4 | 14.3 | 2.7 | 61.3 | 0.04 | 0.482 |  | 152 | [-122, 122] |
| 63 | 5 | up | 438 | 1464 | 1246 | -23.6 | 13.6 | -39.5 | 27.0 | -1.46 | 0.928 |  | 67 | [-94, 14] |
| 63 | 5 | dn | 215 | 554 | 1732 | 78.0 | 71.3 | 56.6 | 41.2 | 1.37 | 0.086 |  | 102 | [-14, 129] |
| 63 | 20 | up | 432 | 1448 | 1236 | -19.0 | 47.7 | -80.5 | 56.9 | -1.41 | 0.921 |  | 142 | [-186, 20] |
| 63 | 20 | dn | 215 | 553 | 1711 | 107.7 | 46.2 | 126.0 | 87.3 | 1.44 | 0.075 |  | 217 | [-43, 303] |

TRAIN and VAL agree on sign in 6 of 8 cells and on the up-side sign in all four; neither window shows a cell with a positive, significant B − C.

### 5.3 Secondary and control quantities (report-only, unadjusted, never gates)

Arm means are of per-date cohort means (bp, market-excess) with NW t against zero; the event-weighted contrast, the two-way (entity × date) clustered event contrast, and the within-date permutation p are second and third estimators of the same B − C statistic (§6 cross-checks). The attrition-bound column recomputes d̄ after replacing dropped/terminal events by the pre-specified worst values.

**VAL**

| N | H | side | A cohort mean (t) | B cohort mean (t) | C cohort mean (t) | D control (t) | n_D | event-wtd B−C | 2-way-cluster b (t; p) | permutation p | attrition-bound d̄ (p) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 5 | up | -2.3 (-0.17) | -36.4 (-1.91) | 15.8 (1.04) | -35.1 (-1.96) | 1280 | -35.7 | -43.1 (-2.26; 0.988) | 0.978 | -54.4 (0.977) |
| 20 | 5 | dn | 25.5 (2.23) | 59.6 (2.07) | 19.7 (1.49) | 17.3 (0.69) | 689 | 59.4 | 44.6 (1.51; 0.066) | 0.104 | 39.1 (0.159) |
| 20 | 20 | up | -9.3 (-0.35) | -74.5 (-2.27) | 41.1 (1.15) | -15.6 (-0.41) | 1272 | -91.1 | -113.2 (-2.71; 0.996) | 0.982 | -113.8 (0.974) |
| 20 | 20 | dn | 27.0 (0.97) | 83.2 (1.40) | 4.9 (0.17) | 4.6 (0.11) | 685 | 80.1 | 74.7 (1.46; 0.073) | 0.167 | 37.4 (0.317) |
| 63 | 5 | up | -25.0 (-1.42) | -11.2 (-0.51) | -26.9 (-1.36) | -23.1 (-1.47) | 1929 | -2.1 | 8.2 (0.35; 0.364) | 0.574 | -6.1 (0.578) |
| 63 | 5 | dn | 5.8 (0.38) | -5.5 (-0.21) | 27.2 (1.25) | 14.9 (0.70) | 1019 | -8.0 | -12.1 (-0.40; 0.655) | 0.572 | -6.8 (0.558) |
| 63 | 20 | up | -35.2 (-0.98) | -28.9 (-0.65) | -14.2 (-0.36) | -8.0 (-0.25) | 1919 | -27.4 | -33.4 (-0.75; 0.773) | 0.667 | -25.8 (0.668) |
| 63 | 20 | dn | 34.5 (0.98) | -37.2 (-0.62) | 73.1 (1.54) | -16.5 (-0.44) | 1010 | -87.6 | -79.2 (-1.18; 0.881) | 0.928 | -119.3 (0.880) |

**TRAIN**

| N | H | side | A cohort mean (t) | B cohort mean (t) | C cohort mean (t) | D control (t) | n_D | event-wtd B−C | 2-way-cluster b (t; p) | permutation p | attrition-bound d̄ (p) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 5 | up | -13.0 (-1.04) | -15.8 (-0.88) | -4.4 (-0.36) | -10.2 (-0.62) | 1454 | -4.4 | 10.9 (0.60; 0.274) | 0.662 | -15.1 (0.751) |
| 20 | 5 | dn | -5.0 (-0.43) | 32.6 (1.41) | -5.2 (-0.44) | 1.9 (0.11) | 759 | 46.8 | 54.4 (2.10; 0.018) | 0.119 | 33.4 (0.129) |
| 20 | 20 | up | -3.3 (-0.12) | -36.7 (-1.03) | 2.8 (0.09) | -11.6 (-0.30) | 1434 | -53.9 | -9.0 (-0.26; 0.601) | 0.970 | -100.0 (0.972) |
| 20 | 20 | dn | 26.3 (1.11) | 60.4 (1.35) | 14.3 (0.57) | 20.3 (0.57) | 754 | -25.7 | 51.7 (1.20; 0.115) | 0.490 | -20.6 (0.628) |
| 63 | 5 | up | -10.5 (-0.77) | -23.6 (-1.50) | 13.6 (0.77) | -29.0 (-2.10) | 2117 | -37.4 | -25.3 (-1.28; 0.900) | 0.918 | -39.5 (0.928) |
| 63 | 5 | dn | 82.4 (5.09) | 78.0 (2.53) | 71.3 (4.44) | 14.1 (0.88) | 1148 | 11.8 | 5.4 (0.18; 0.427) | 0.084 | 56.6 (0.086) |
| 63 | 20 | up | 18.4 (0.54) | -19.0 (-0.47) | 47.7 (1.09) | -51.5 (-1.58) | 2081 | -47.3 | -25.3 (-0.64; 0.738) | 0.929 | -80.5 (0.921) |
| 63 | 20 | dn | 83.3 (2.34) | 107.7 (1.83) | 46.2 (1.17) | 17.2 (0.54) | 1142 | 21.3 | 66.9 (1.34; 0.091) | 0.072 | 122.0 (0.083) |

**Reading.** (i) The three estimators of B − C (cohort-paired, event-weighted, two-way-clustered) agree in sign in every VAL cell except the N=63 H=5 *up* cell (−6.1 vs −2.1 vs +8.2 bp — all ≈ 0). (ii) In VAL the permutation p and the NW p are both > 0.05 in all eight cells (no disagreement about the 0.05 line); the two-way-clustered event p is also > 0.05 everywhere (closest: 0.066 and 0.073 at down N=20). In TRAIN (descriptive) one cell differs: down N=20 H=5 has clustered-event p = 0.018 against NW p = 0.129 and permutation p = 0.119. (iii) The attrition bound moves nothing: dropped/terminal events number single digits per cell in VAL (funnel table). (iv) The control D (abnormal volume without a breakout, signed by the day's direction) shows no reliable continuation at any cell in VAL (|t| ≤ 1.96, and the only |t| near 2 is negative). (v) **Breakouts as such (arm A, the M3a-alone question), descriptive and unadjusted.** In VAL only one A cell has t > 2 (down-side N=20 H=5, +25.5 bp, t = 2.23, one of the 32 arm-cells). In **TRAIN** the down-side N = 63 arm A shows strong market-excess continuation — +82 bp at H = 5 (t = 5.09, 2,286 events) and +83 bp at H = 20 (t = 2.34) — that does **not** replicate in VAL (+6 bp, t = 0.38; +34 bp, t = 0.98). That is the most informative M3a-alone fact in the study: long-range downside breakouts continued in 2012–17 and did not in 2018–22. It is a TRAIN observation (descriptive, unadjusted, no decision) and it is not about volume.

## 6. Independent verification (two methods per headline number; disagreement ⇒ STOP)

| stage | check | result | pass |
|---|---|---|---|
| TRAIN | VP1 SQL vs engine (event-for-event) | 19,761 vs 19,761 events; only-in-one-side 0+0; arm mismatches 0; status mismatches 0+0; max abs Δf 1.8e-12 bp; max abs ΔR_m 1.8e-16 | True |
| TRAIN | VP2 raw as-traded rebuild (sample) | 36 of 36 verified (0 skipped CA, 0 multi-symbol); max rel ΔAV 1.5e-16; max abs ΔR5 1.1e-16; max abs ΔR20 2.2e-16; max abs Δmargin 2.2e-16; 7 price levels differ (later CA) but ratios agree | True |
| TRAIN | VP3 statistics (manual NW, statsmodels kernel, dict cohorts) | max abs Δ — d̄ 4.3e-14, SE 1.4e-14, t 4.4e-16, p 1.1e-16, kernel SE 2.1e-14, cohort d 9.1e-13 | True |
| TRAIN | VP4 accounting identities | duplicate keys 0; identity True; A=B⊔C True; one R_m per date True | True |
| TRAIN | VP5 volume (adjusted vs raw; CA rebuild; turnover flag) | adjusted=raw on 4,000 CA-free-entity rows (max abs Δ 0e+00); CA rebuild 3000/3000; turnover-based flag agrees on 97.2% of 14,272 breakouts | True |
| TRAIN | VP6 fee arithmetic | round trip 22.16 bp by hand = library | True |
| VAL | VP1 SQL vs engine (event-for-event) | 17,067 vs 17,067 events; only-in-one-side 0+0; arm mismatches 0; status mismatches 0+0; max abs Δf 1.8e-12 bp; max abs ΔR_m 1.7e-16 | True |
| VAL | VP2 raw as-traded rebuild (sample) | 35 of 36 verified (0 skipped CA, 1 multi-symbol); max rel ΔAV 0.0e+00; max abs ΔR5 1.1e-16; max abs ΔR20 2.2e-16; max abs Δmargin 1.1e-16; 2 price levels differ (later CA) but ratios agree | True |
| VAL | VP3 statistics (manual NW, statsmodels kernel, dict cohorts) | max abs Δ — d̄ 1.4e-14, SE 1.4e-14, t 4.4e-16, p 1.1e-16, kernel SE 2.1e-14, cohort d 4.5e-13 | True |
| VAL | VP4 accounting identities | duplicate keys 0; identity True; A=B⊔C True; one R_m per date True | True |
| VAL | VP5 volume (adjusted vs raw; CA rebuild; turnover flag) | adjusted=raw on 4,000 CA-free-entity rows (max abs Δ 0e+00); CA rebuild 3000/3000; turnover-based flag agrees on 96.9% of 12,121 breakouts | True |
| VAL | VP6 fee arithmetic | round trip 22.16 bp by hand = library | True |

**How each headline number is reproduced.** (1) *Event-level:* VP1 re-derives every event's existence, arm, AV, entry/exit prices, R, R_m and f in **pure SQL window functions** from the same snapshot (own calendar, own membership, own flag/onset logic, own terminal rule, own benchmark) and matches the numpy engine with zero exceptions. (2) *Raw-data level:* VP2 rebuilds seeded events from the RAW as-traded table with plain Python loops (Mx, the 10th/11th sorted volumes, AV, entry, exit, R) — scale-free quantities only, because adjusted price *levels* legitimately differ from raw ones for any name with a later bonus/split. (3) *Statistic level:* VP3 recomputes d̄, SE, t, p for all 16 cells from the cohort ledger by (a) a dictionary-arithmetic pure-Python Newey–West and (b) `statsmodels.stats.sandwich_covariance.S_hac_simple` on the zero-filled demeaned series, and rebuilds the cohort means from the event ledger; all agree to ≤ 1e-12. (4) *Alternative inference:* a within-date permutation test (5,000 draws) and a two-way-clustered event contrast are reported beside the NW statistic; in VAL none disagrees on the 0.05 line (one TRAIN cell does, §5.3). (5) *Data level:* adjusted volume equals raw volume on all sampled rows of entities with no bonus/split; for 3,000 sampled rows of CA entities the adjusted close and volume are rebuilt from `adjustment_factors` (3,000/3,000); an independent turnover-based (CA-invariant) abnormal-volume flag agrees with the volume flag on ≈ 97 % of breakouts (the residue is the price-move term: turnover = price × volume). (6) *Fees:* hand arithmetic = library.

## 7. Failure / leakage / bias audit

### 7.1 Audit table (control → evidence)

| Risk | Control | Evidence |
|---|---|---|
| Look-ahead in signal | flags use t−N…t only; entry = open of t+1; test perturbs everything after t and shows events ≤ t unchanged | `test_signal_is_causal…`; VP1 |
| Volume alignment | median over t−20…t−1 (today excluded); one row per (entity, date) for OHLC and V; test: ×1000 today's volume leaves its baseline unchanged | `test_volume_baseline_excludes_today`; VP1/VP2 |
| Price/volume timestamp mismatch | both come from the same daily row on the same regular-calendar index | VP2 (raw rows) |
| Info from t used as if earlier | none: the signal is a close-of-t object; earliest trade is the t+1 open; **R starts at that open, so the overnight gap G is excluded from R** (the tradable definition; decomposition in §9.4) | protocol §6 (erratum A3), `window_returns` |
| Survivorship / universe changes | PIT monthly top-200 by trailing turnover; membership strictly before t; delisted names kept while listed; terminal-price rule; attrition bound | §4; dropped/terminal events: single digits per cell |
| Overlapping events | onset-only with a 20-session quiet period = longest H; non-declustered variant (R3) reported separately | §9 |
| Event clustering | per-date cohort observation; HAC lag H; permutation & clustered checks | §5.3 |
| Duplicated observations | unique (entity, t, N, kind) (0 duplicates); one listing per entity-date (0 duplicate listings in the snapshot) | VP4 |
| Weighting mistakes | cohort-weighted primary reported beside event-weighted contrast; A = B ⊔ C identity | §5.3, VP4 |
| Denominator / sample-count errors | every cell reconciles by identity; benchmark identity Σ(R − R_m) = 0 shown on the worked dates | §4, §10 |
| Corporate actions | certified adjusted view for prices and volume; 2.6 % of events have a CA factor in [t−83, exit+1] — results without them are in R4 | §9 |
| Special / short sessions | rule-based removal; non-causal-median sensitivity checked (identical dates) | §4 |
| Cost assumptions | existing delivery-fee model both legs; κ scenarios, break-even κ reported; short leg is a cost-scale proxy | §8 |
| Multiple testing / parameter selection | 8-cell Holm family; nothing tuned on TRAIN; post-primary variants labelled non-classifying | §5, §9 |

### 7.2 Things that could still bias the result (stated, not corrected)

* **Not beta-adjusted.** Excess is over an equal-weight universe return. Volume-flagged breakouts may carry different beta; B − C only partly nets it.
* **Entry at the open of t+1** can be unfillable when a name is locked at a circuit; not modelled. Entry is the auction-opening print, not a filled price.
* **Top-200 turnover universe only** (large/liquid). Nothing is said about small caps, where volume signals and breakouts behave differently.
* **B days are larger-move days** by construction (declared confound R9; §9.5).
* **Prior exposure (GR-1.3).** 2012–22 equity EOD is signal-spent by PSB/CSMP/Gann/MRLC; VAL is a consistency check, not naive.
* **Cohort weighting** gives each formation date equal weight regardless of how many events it has; the event-weighted contrast is reported beside it and reaches the same conclusions.

### 7.3 Pre-run predictions (protocol §14) — scorecard

| Prediction | Outcome |
|---|---|
| A = B ⊔ C exactly in every cell | ✓ (all 16 cell-rows, both stages) |
| Σ(R − R_m) = 0 over the benchmark set on every date | ✓ by construction (worked example: 1.4e-15); the independent evidence is VP1's separately computed SQL R_m matching the ledger's on every event date (max abs Δ 1.7e-16) |
| Outcome-free event counts reproduce | ✓ (e.g. TRAIN N20 up B/C formed 1,800/2,733 in diagnostics; funnel shows formed 1,800 / 2,733 before containment) |
| VP1 agrees with the ledger with zero exceptions | ✓ (19,761 and 17,067 events) |
| < 1 of 8 VAL cells confirms under H0; modal outcome C5 | ✓ (0 of 8; C5) |

### 7.4 Deviations, amendments, and report errata (all logged)

* **A1** — VP5 "clean" names were defined by symbol, but adjustment is per entity; run on TRAIN it failed on 103/4,000 rows, all 11 offending entities carrying a corporate action under a *renamed* symbol (PHILIPCARB→PCBL etc.). The verifier population (VP5, and the VP2 skip rule) was corrected to entity level and tested on a synthetic rename chain. No engine/analysis code and no TRAIN number changed.
* **A2** — `classification.json` failed to serialise tuple keys; output-only fix, VAL cell table byte-identical.
* **A3** — protocol erratum (text only): §6 said the overnight gap is "part of R"; it is not — the engine (and the SQL verifier) start R at the t+1 open, which is the tradable definition. Corrected in the protocol amendments section; the estimand and every number are unchanged. The post-primary gap table (§9.4) had inherited the error and was rebuilt.
* **E — errata found by the final cross-check of the prose:** the gap decomposition mislabelled the post-open return; "up-side B is negative net of cost in every cell" was VAL-only; "no cell is stable across years" overstated; the arm-A reading omitted TRAIN; the tercile-cut granularity differed from the protocol text; "none typed by hand" was untrue. All corrected above.
* **Departure from the advisor's suggestion:** the HOLDOUT-spend question was not put to the operator up front; it is only relevant if VAL confirms, which it did not.

## 8. Economic / cost analysis (descriptive; the economic gate is conditional on a HOLDOUT confirmation and was not reached)

Round trip on ₹5,00,000: BUY at the entry-open date + SELL at the exit date, priced by the existing `delivery_fees.py` (STT 0.1 % per leg, exchange, SEBI, stamp on the buy leg, GST, DP on the sell) = ≈ 22 bp of notional (hand-checked in §10) plus slippage κ per side. Both directions are priced on the long-side delivery schedule as a conservative cost-scale proxy (a multi-day cash-delivery short is not implementable; no short fee schedule is invented — the down-side is mechanism evidence, not a strategy). "Gross raw B" is the un-netted direction-signed mean return (it includes market drift).

**VAL — B arm, event-weighted net (bp) by slippage scenario**

| N | H | side | n | gross raw B (bp) | statutory+DP RT (bp) | break-even κ (bp/side) | net @κ=0 | net @κ=2.5 | net @κ=5 | net @κ=10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 5 | up | 1425 | -17.7 | 21.8 | -19.8 | -39.5 | -44.5 | -49.5 | -59.5 |
| 20 | 5 | dn | 626 | 107.6 | 21.8 | 42.9 | 85.7 | 80.7 | 75.7 | 65.7 |
| 20 | 20 | up | 1412 | 6.7 | 21.8 | -7.5 | -15.1 | -20.1 | -25.1 | -35.1 |
| 20 | 20 | dn | 615 | 196.0 | 21.8 | 87.1 | 174.2 | 169.2 | 164.2 | 154.2 |
| 63 | 5 | up | 1216 | -2.4 | 21.7 | -12.1 | -24.1 | -29.1 | -34.1 | -44.1 |
| 63 | 5 | dn | 590 | 56.0 | 21.9 | 17.1 | 34.2 | 29.2 | 24.2 | 14.2 |
| 63 | 20 | up | 1201 | 1.9 | 21.8 | -9.9 | -19.8 | -24.8 | -29.8 | -39.8 |
| 63 | 20 | dn | 579 | 78.0 | 21.9 | 28.1 | 56.2 | 51.2 | 46.2 | 36.2 |

**TRAIN — B arm**

| N | H | side | n | gross raw B (bp) | statutory+DP RT (bp) | break-even κ (bp/side) | net @κ=0 | net @κ=2.5 | net @κ=5 | net @κ=10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 5 | up | 1790 | 33.4 | 22.1 | 5.6 | 11.2 | 6.2 | 1.2 | -8.8 |
| 20 | 5 | dn | 718 | 35.3 | 22.1 | 6.6 | 13.2 | 8.2 | 3.2 | -6.8 |
| 20 | 20 | up | 1764 | 116.4 | 22.1 | 47.1 | 94.2 | 89.2 | 84.2 | 74.2 |
| 20 | 20 | dn | 718 | -36.6 | 22.1 | -29.4 | -58.7 | -63.7 | -68.7 | -78.7 |
| 63 | 5 | up | 1464 | -4.5 | 22.1 | -13.3 | -26.7 | -31.7 | -36.7 | -46.7 |
| 63 | 5 | dn | 554 | 54.2 | 22.1 | 16.0 | 32.1 | 27.1 | 22.1 | 12.1 |
| 63 | 20 | up | 1448 | 71.3 | 22.1 | 24.6 | 49.2 | 44.2 | 39.2 | 29.2 |
| 63 | 20 | dn | 553 | 67.5 | 22.1 | 22.7 | 45.4 | 40.4 | 35.4 | 25.4 |

**Reading.** In **VAL**, up-side B is negative net of cost in every cell and every κ (even at κ = 0) — the gross raw mean is ≤ +7 bp against a 22 bp fee. In **TRAIN** it is not: up-side B nets +1, +84, −37, +39 bp at κ = 5 (N20H5, N20H20, N63H5, N63H20); the raw number includes 2012–17 market drift (it is not netted against the universe) and there is no B − C evidence behind it (§5.2). Down-side B shows positive short-proxy nets in VAL (24–164 bp at κ = 5), but (i) it is not distinguishable from the C arm (§5.1), (ii) it is not stable — TRAIN B raw signed means at down/N=20 are +35 bp (H=5) and −37 bp (H=20) — and (iii) a multi-day cash short is not implementable, so this is not an economic finding. The break-even κ is large and positive only where the raw mean is large.

## 9. Post-primary disclosure analyses (declared in protocol §13; **cannot change the label or be promoted**)

### 9.1 Variants (VAL; one-sided p of B − C)

| variant | cells | min one-sided p | cell of min p | d̄ there (bp) | # cells p<0.05 (unadjusted) | # cells with d̄>0 |
|---|---|---|---|---|---|---|
| PRIMARY | 8 | 0.159 | N20 H5 dn | 39.1 | 0 | 2 |
| R1_highlow_range | 8 | 0.327 | N20 H20 dn | 26.0 | 0 | 4 |
| R3_non_declustered | 8 | 0.471 | N63 H5 up | 1.2 | 0 | 1 |
| R2_av1.5 | 8 | 0.309 | N20 H20 up | 23.2 | 0 | 3 |
| R2_av3.0 | 8 | 0.028 | N63 H5 dn | 101.7 | 2 | 5 |
| R6_turnover_AV | 8 | 0.228 | N20 H5 dn | 29.7 | 0 | 2 |
| R4_no_CA_in_span | 8 | 0.159 | N20 H5 dn | 39.9 | 0 | 2 |
| R8_no_terminal | 8 | 0.159 | N20 H5 dn | 39.1 | 0 | 2 |

Cell-level d̄ (VAL, bp):

| N | H | side | PRIMARY | R1_highlow_range | R3_non_declustered | R2_av1.5 | R2_av3.0 | R6_turnover_AV | R4_no_CA_in_span | R8_no_terminal |
|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 5 | up | -52.40 | -55.80 | -12.30 | 5.50 | -57.10 | -57.70 | -42.70 | -52.40 |
| 20 | 5 | dn | 39.10 | -0.60 | -45.20 | 4.50 | 77.10 | 29.70 | 39.90 | 39.10 |
| 20 | 20 | up | -104.30 | -160.10 | -26.20 | 23.20 | -98.40 | -115.40 | -92.90 | -104.10 |
| 20 | 20 | dn | 58.50 | 26.00 | -31.20 | -10.10 | 75.20 | 4.80 | 56.70 | 58.50 |
| 63 | 5 | up | -6.10 | 14.10 | 1.20 | -24.30 | 25.60 | -5.70 | -13.80 | -6.10 |
| 63 | 5 | dn | -6.80 | 18.70 | -85.90 | -39.40 | 101.70 | -5.10 | -5.30 | -6.80 |
| 63 | 20 | up | -23.80 | -17.50 | -45.40 | -21.20 | -6.40 | -34.80 | -25.50 | -23.80 |
| 63 | 20 | dn | -117.40 | 28.70 | -96.00 | -226.00 | 41.30 | -94.70 | -122.10 | -117.40 |

Two down-side cells reach unadjusted p < 0.05 **only** under the AV ≥ 3.0 variant (N=20 H=5 p = 0.043; N=63 H=5 p = 0.028). That is 2 of 56 variant cells (chance expectation ≈ 2.8 at α = 0.05), it appears in one of seven variants, it was not the primary threshold, and it is exactly the shape the protocol pre-declares non-promotable (threshold chosen after the result). **Not promoted; refused as forking paths.** The non-declustered variant (R3) is negative in 7 of 8 cells (+1 bp in the eighth), consistent with the look-ahead-weighting artefact noted in the protocol for persistence-defined events.

### 9.2 By calendar year (VAL, H = 5, B − C in bp)

| N | side | 2018 | 2019 | 2020 | 2021 | 2022 |
|---|---|---|---|---|---|---|
| 20 | dn | 26.00 | -42.00 | 177.00 | 55.00 | 10.00 |
| 20 | up | -57.00 | -137.00 | -43.00 | -77.00 | 55.00 |
| 63 | dn | 68.00 | -143.00 | -3.00 | 18.00 | 67.00 |
| 63 | up | -50.00 | -4.00 | -38.00 | 36.00 | 18.00 |

Reading (VAL, all eight cells, by year): the up-side d̄ is negative in 4 of 5 years at N = 20 (both horizons) and in 3 of 5 years at N = 63, and positive only in 2022 at N = 20; the down-side changes sign across years in every cell (negative in 1–3 of 5 years). The wrong-signed up-side result is therefore reasonably persistent inside VAL, but each year has only 60–110 paired dates and no yearly cell is significant — descriptive only.

### 9.3 Breakout-depth terciles (R9; cuts fixed from pooled TRAIN ∪ VAL events — **per (N, side, H)** in the code, whereas the protocol text says per (N, side): a disclosed difference, because the resolved-event set differs slightly by H; the cuts barely move)

| N | H | side | tercile | depth range (bp) | share_B | n_B | n_C | pair_dates | d_mean | d_t | d_p_one |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 5 | up | 1 | 0–68 | 0.21 | 251 | 965 | 111 | -20.0 | -0.31 | 0.621 |
| 20 | 5 | up | 2 | 68–188 | 0.30 | 381 | 884 | 134 | -9.4 | -0.21 | 0.583 |
| 20 | 5 | up | 3 | 188–∞ | 0.62 | 793 | 495 | 162 | -88.9 | -1.67 | 0.952 |
| 20 | 20 | up | 1 | 0–69 | 0.20 | 246 | 958 | 110 | -82.7 | -0.71 | 0.762 |
| 20 | 20 | up | 2 | 69–188 | 0.30 | 379 | 874 | 134 | -122.7 | -1.13 | 0.869 |
| 20 | 20 | up | 3 | 188–∞ | 0.61 | 787 | 494 | 161 | -174.6 | -1.96 | 0.974 |
| 20 | 5 | dn | 1 | 0–59 | 0.08 | 109 | 1258 | 65 | 104.9 | 0.76 | 0.225 |
| 20 | 5 | dn | 2 | 59–161 | 0.12 | 152 | 1135 | 83 | 1.3 | 0.02 | 0.491 |
| 20 | 5 | dn | 3 | 161–∞ | 0.27 | 365 | 991 | 150 | -21.2 | -0.39 | 0.652 |
| 20 | 20 | dn | 1 | 0–59 | 0.08 | 107 | 1225 | 65 | -194.8 | -1.16 | 0.874 |
| 20 | 20 | dn | 2 | 59–161 | 0.12 | 148 | 1100 | 80 | 35.6 | 0.27 | 0.394 |
| 20 | 20 | dn | 3 | 161–∞ | 0.28 | 360 | 949 | 146 | -7.7 | -0.07 | 0.528 |
| 63 | 5 | up | 1 | 0–70 | 0.34 | 250 | 482 | 95 | -56.3 | -0.96 | 0.830 |
| 63 | 5 | up | 2 | 70–197 | 0.48 | 359 | 392 | 101 | -15.9 | -0.23 | 0.590 |
| 63 | 5 | up | 3 | 197–∞ | 0.83 | 607 | 122 | 56 | 94.4 | 1.25 | 0.108 |
| 63 | 20 | up | 1 | 0–71 | 0.34 | 244 | 479 | 94 | -155.6 | -0.99 | 0.839 |
| 63 | 20 | up | 2 | 71–198 | 0.48 | 356 | 390 | 101 | -21.1 | -0.19 | 0.574 |
| 63 | 20 | up | 3 | 198–∞ | 0.83 | 601 | 122 | 56 | -31.8 | -0.19 | 0.573 |
| 63 | 5 | dn | 1 | 0–67 | 0.16 | 105 | 567 | 51 | 62.7 | 0.70 | 0.244 |
| 63 | 5 | dn | 2 | 67–186 | 0.23 | 169 | 554 | 73 | -25.6 | -0.52 | 0.698 |
| 63 | 5 | dn | 3 | 186–∞ | 0.44 | 316 | 396 | 83 | 41.7 | 0.65 | 0.259 |
| 63 | 20 | dn | 1 | 0–67 | 0.16 | 106 | 549 | 50 | -90.7 | -0.45 | 0.672 |
| 63 | 20 | dn | 2 | 67–187 | 0.23 | 163 | 543 | 72 | 27.1 | 0.25 | 0.400 |
| 63 | 20 | dn | 3 | 187–∞ | 0.45 | 310 | 383 | 80 | -66.5 | -0.50 | 0.691 |

**Confound check.** B share rises steeply with depth (e.g. up N=20: 21 % → 30 % → 62 %), confirming that abnormal-volume breakouts are the deep ones. Within terciles, B − C is not significantly positive anywhere (largest positive t = 1.25, up N=63 H=5 deepest tercile); the largest |t| is negative (−1.96, up N=20 H=20 deepest tercile). So the wrong-signed pooled up-side result is not removed by conditioning on depth.

### 9.4 Overnight gap vs the primary window (VAL, raw direction-signed means, bp)

**R starts at the t+1 open, so the overnight gap G = O_{t+1}/C_t − 1 is not inside R.** The table shows G separately, R itself ("post-open"), and the move measured from the t close, (1+G)(1+R) − 1.

| N | side | quantity | n_B | n_C | mean_B | mean_C | diff_B_minus_C |
|---|---|---|---|---|---|---|---|
| 20 | dn | overnight gap G (t close → t+1 open) — NOT in R | 626 | 3384 | -16.7 | -9.2 | -7.5 |
| 20 | dn | post-open return = R, H=5 (the primary quantity, raw) | 626 | 3384 | 107.6 | 18.5 | 89.0 |
| 20 | dn | from the t close, H=5: (1+G)(1+R)−1 | 626 | 3384 | 91.6 | 9.6 | 82.0 |
| 20 | dn | post-open return = R, H=20 (raw) | 626 | 3384 | 196.0 | 31.8 | 164.2 |
| 20 | dn | from the t close, H=20: (1+G)(1+R)−1 | 626 | 3384 | 180.7 | 21.8 | 158.9 |
| 20 | up | overnight gap G (t close → t+1 open) — NOT in R | 1425 | 2344 | 50.2 | 29.0 | 21.1 |
| 20 | up | post-open return = R, H=5 (the primary quantity, raw) | 1425 | 2344 | -17.7 | 42.3 | -60.0 |
| 20 | up | from the t close, H=5: (1+G)(1+R)−1 | 1425 | 2344 | 31.4 | 71.3 | -39.9 |
| 20 | up | post-open return = R, H=20 (raw) | 1425 | 2344 | 6.7 | 156.5 | -149.8 |
| 20 | up | from the t close, H=20: (1+G)(1+R)−1 | 1425 | 2344 | 55.5 | 185.5 | -129.9 |
| 63 | dn | overnight gap G (t close → t+1 open) — NOT in R | 590 | 1517 | -8.3 | 2.6 | -10.9 |
| 63 | dn | post-open return = R, H=5 (the primary quantity, raw) | 590 | 1517 | 56.0 | 44.5 | 11.5 |
| 63 | dn | from the t close, H=5: (1+G)(1+R)−1 | 590 | 1517 | 48.0 | 46.2 | 1.8 |
| 63 | dn | post-open return = R, H=20 (raw) | 590 | 1517 | 78.0 | 82.7 | -4.6 |
| 63 | dn | from the t close, H=20: (1+G)(1+R)−1 | 590 | 1517 | 70.9 | 85.2 | -14.3 |
| 63 | up | overnight gap G (t close → t+1 open) — NOT in R | 1216 | 996 | 47.7 | 32.0 | 15.7 |
| 63 | up | post-open return = R, H=5 (the primary quantity, raw) | 1216 | 996 | -2.4 | -14.3 | 11.9 |
| 63 | up | from the t close, H=5: (1+G)(1+R)−1 | 1216 | 996 | 44.9 | 17.3 | 27.6 |
| 63 | up | post-open return = R, H=20 (raw) | 1216 | 996 | 1.9 | 21.1 | -19.2 |
| 63 | up | from the t close, H=20: (1+G)(1+R)−1 | 1216 | 996 | 48.8 | 53.2 | -4.4 |

Volume-confirmed up-side breakouts gap up more than unconfirmed ones (G: +21 bp at N = 20) but their post-open return R is lower (B − C = −60 bp at H = 5, −150 bp at H = 20, N = 20), so measured from the t close they are still behind (−40 / −130 bp). The tradable definition (entry at the open) therefore *reports the post-gap continuation only*; whatever continuation the gap contains is not credited to the strategy, and the B − C result is not driven by it.

## 10. Arithmetic / reconstruction ledger

Everything below is reproduced from raw rows and hand arithmetic; the files are in `docs/reports/research/breakout_volume/`:

| Ledger | File | Grain |
|---|---|---|
| Event ledger (every input to every f) | `events_{TRAIN,VAL}.csv.gz` | 1 row per (entity, session, N, kind) — signal quantities, entry/exit sessions, R, R_m, f, raw, status |
| Cohort ledger | `cohort_{TRAIN,VAL}.csv` | 1 row per (cell, formation date): n_B, n_C, m_B, m_C, d |
| Benchmark ledger | `bench_{TRAIN,VAL}.csv` | R_m and member count per (date, H) |
| Cell tables | `cells_*.csv` | every statistic in §5 |
| Cost tables | `costs_*.csv` | per arm, per κ |
| Reconciliation | `accounting_*.json` | sample funnel per cell |
| Verification | `verification_*.json`, `vp2_raw_sample_*.csv` | the six checks; sampled raw rebuilds |

**Path from the headline number to the raw observations** (VAL, N=20, H=5, up: d̄ = −52.4 bp): raw bhavcopy rows → adjusted OHLCV (certified view) → per-event `f` (event ledger) → per-date `m_B`, `m_C` (cohort ledger) → `d(t) = m_B − m_C` on 505 paired dates → d̄ → Newey–West SE → t → p. The last three steps and two example events are written out below with real numbers.

## Event example — arm B, up, N=20

**Event:** MCX (MCX), formation session t = 2018-10-24, N = 20, UP breakout, arm **B**, H = 5.

1. Range: the 20 closes 2018-09-24 … 2018-10-23 (raw, as traded; no corporate action in the span) have max = **799.80**. Close on t = **819.05** → C_t > max ✓ (margin 240.7 bp). Ledger level 159.9600 (adjusted; ratio close/level − 1 = 0.024069 vs raw 0.024069).
2. Volume: the 20 prior volumes sorted, the 10th and 11th are 648,720 and 676,987 → median = **662,853.5**; V_t = **1,914,114** → AV = 1,914,114 / 662,853.5 = **2.8877** (≥ 2.0 → ABN → B). Ledger AV = 2.8877.
3. Entry open t+1 (2018-10-25) = **810.00**; exit close t+5 (2018-10-31) = **702.40** → R = 702.40 / 810.00 − 1 = **-1328.40 bp** (ledger -1328.40 bp).
4. Benchmark R_m(t, 5) from the ledger = **546.18 bp** (equal-weight mean over the PIT members with a resolved window; see block below).
5. f = sign · (R − R_m) = +1 · (-1328.40 − 546.18) = **-1874.57 bp** (ledger f5 = -1874.57 bp).

Benchmark for t = 2018-10-24, H = 5: PIT members with a resolved window = **200**; Σ R = 10.923551; R_m = Σ R / n = 10.923551 / 200 = **546.1776 bp**; check Σ (R − R_m) = 1.44e-15 (identically 0). First 5 members: ABREL 962.7 bp, ACC 107.0 bp, ADANIENT 194.9 bp, ADANIPORTS 222.8 bp, ADANIPOWER 3864.7 bp.

## Event example — arm C, up, N=20

**Event:** RECLTD (RECLTD), formation session t = 2018-10-24, N = 20, UP breakout, arm **C**, H = 5.

1. Range: the 20 closes 2018-09-24 … 2018-10-23 (raw, as traded; no corporate action in the span) have max = **105.25**. Close on t = **108.10** → C_t > max ✓ (margin 270.8 bp). Ledger level 78.9375 (adjusted; ratio close/level − 1 = 0.027078 vs raw 0.027078).
2. Volume: the 20 prior volumes sorted, the 10th and 11th are 6,156,333 and 6,615,761 → median = **6,386,047.0**; V_t = **5,854,685** → AV = 5,854,685 / 6,386,047.0 = **0.9168** (< 2.0 → not abnormal → C). Ledger AV = 0.9168.
3. Entry open t+1 (2018-10-25) = **107.45**; exit close t+5 (2018-10-31) = **116.40** → R = 116.40 / 107.45 − 1 = **832.95 bp** (ledger 832.95 bp).
4. Benchmark R_m(t, 5) from the ledger = **546.18 bp** (equal-weight mean over the PIT members with a resolved window; see block below).
5. f = sign · (R − R_m) = +1 · (832.95 − 546.18) = **286.77 bp** (ledger f5 = 286.77 bp).

Benchmark for t = 2018-10-24, H = 5: PIT members with a resolved window = **200**; Σ R = 10.923551; R_m = Σ R / n = 10.923551 / 200 = **546.1776 bp**; check Σ (R − R_m) = 1.44e-15 (identically 0). First 5 members: ABREL 962.7 bp, ACC 107.0 bp, ADANIENT 194.9 bp, ADANIPORTS 222.8 bp, ADANIPOWER 3864.7 bp.

## Headline-cell aggregation and Newey–West arithmetic

**Cell VAL, N=20, H=5, side=up** — paired formation dates n = **505**.

* d̄ = Σ d(t) / n = -26485.3490 / 505 = **-52.4462 bp**
* g₀ = Σ (d−d̄)² / n = 183016878.67 / 505 = 362409.6607

| k | g_k = Σ(pairs k sessions apart) z_i z_j / n | weight 1−k/(H+1) | contribution 2·w·g_k |
|---|---|---|---|
| 1 | -1084.4415 | 0.8333 | -1807.4026 |
| 2 | 9909.0598 | 0.6667 | 13212.0798 |
| 3 | -4847.4685 | 0.5000 | -4847.4685 |
| 4 | -2608.8734 | 0.3333 | -1739.2489 |
| 5 | 10243.4740 | 0.1667 | 3414.4913 |

* LRV = g₀ + Σ contributions = **370642.1118**; SE = √(LRV / n) = √(370642.1118 / 505) = **27.0914 bp**
* t = d̄ / SE = -52.4462 / 27.0914 = **-1.9359**; one-sided p = P(T₍504₎ > t) = **0.9733**
* Table values: d̄ = -52.4462, SE = 27.0914, t = -1.9359, p = 0.9733.

First five and last three cohort observations (date, n_B, n_C, m_B, m_C, d = m_B − m_C):

| date | n_B | n_C | m_B (bp) | m_C (bp) | d (bp) |
|---|---|---|---|---|---|
| 2018-01-01 | 3 | 6 | -49.58 | -37.44 | -12.14 |
| 2018-01-02 | 3 | 1 | 204.01 | 354.22 | -150.22 |
| 2018-01-03 | 3 | 2 | 280.79 | 106.28 | 174.51 |
| 2018-01-04 | 2 | 1 | 307.90 | 407.04 | -99.14 |
| 2018-01-05 | 6 | 1 | 291.70 | 142.49 | 149.21 |
| 2022-12-08 | 1 | 7 | 53.58 | 254.15 | -200.57 |
| 2022-12-13 | 2 | 4 | 72.74 | 161.92 | -89.18 |
| 2022-12-14 | 3 | 2 | -254.63 | -122.90 | -131.73 |

## Fee arithmetic (one BUY 2019-06-03, one SELL 2019-06-12, ₹5,00,000 each)

BUY: STT 500.00 + exchange 17.2500 + SEBI 0.50 + stamp 50.00 + GST 3.1950 = ₹570.9450 (library ₹570.9450).
SELL: STT 500.00 + exchange 17.25 + SEBI 0.50 + GST 3.195 + DP 13.5×1.18 = ₹536.8750 (library ₹536.8750).
Round trip = ₹1107.82 / ₹5,00,000 = **22.16 bp** of notional, before slippage.


## 11. Classification

**Ledger-consistent Vault category: C5 — construct-scoped.** The pre-registered criterion (8-cell paired B − C > 0, Holm-8 in VAL) was tested on data and failed (0 of 8; smallest unadjusted p 0.159). C5 needs a predefined criterion that predates the read — it did (frozen at `84fcd99`).

*Scope of the closure (must always accompany the label):* the construct as specified — closing-range onset breakouts (N = 20, 63) in the PIT top-200 turnover universe, abnormal volume = same-day volume ≥ 2× the prior-20-session median, entry at the next open, holds of 5 and 20 sessions, market-excess continuation returns, 2018–2022 confirmatory window. It does **not** close M3a (range-escape continuation) or M5b (volume-confirmed moves) as mechanisms, and says nothing about other range definitions, thresholds, horizons, universes, event definitions or eras. C6 does not apply (no VAL confirmation), C7–C9 do not apply; C9 is unreachable on this substrate. The HOLDOUT window remains unspent.

*Reading `classification.json`:* every VAL cell carries `"fragile": true`. That flag is mechanical — the attrition-bound p inherits the primary's non-significance (Holm-adjusted bound p ≥ 0.05 in every cell), so it is not an attrition finding; attrition itself is single digits per cell and moves no estimate (§5.3).

**What the data establish.** On 2018–22 top-200 stocks there is no detectable positive difference between the continuation of volume-confirmed and unconfirmed breakouts at the pre-declared specification; on the up-side the point estimates are negative in every cell in both windows.
**What they do not establish.** That volume is irrelevant: the MDE (67–253 bp) means effects of a size plausible for a volume premium (tens of bp) could not have been detected. Nor anything about the unspent 2023-01 → 2026-09 window.

## 12. Recommended next research action

None on this construct. Any change (threshold, range definition, universe, horizon, event definition, the AV ≥ 3.0 down-side pattern) is a **new pre-registration** on a window not already spent; the post-primary tables here are disclosure and cannot seed a rescue. If a successor is ever written, the first design question is demonstrability: the MDE table shows that H = 20 cells are unpowered for any plausible volume effect, which is the same wall the Vault found for monthly cross-sections. Housekeeping: add this experiment to the closure ledger as **M3a × M5b — C5, construct-scoped, EMPIRICALLY TESTED** (M3a and M5b stay open); register the 2012–22 equity-EOD signal read (row Q-7) and note that the 2023+ window was not read.

## 13. Reproducibility

```bash
git worktree add -b research/breakout-volume ../Nifty_bkv origin/main    # then check out the branch commits
python -m scripts.breakout_vol.prep && python -m scripts.breakout_vol.diagnostics
python -m pytest tests/breakout_vol -q                                     # 30 tests incl. synthetic end-to-end with splits/renames
python -m scripts.breakout_vol.freeze                                      # (done at 84fcd99; amends logged in the freeze record)
python -m scripts.breakout_vol.run_stage TRAIN ; python -m scripts.breakout_vol.run_stage VAL
python -m scripts.breakout_vol.verify_independent TRAIN ; python -m scripts.breakout_vol.verify_independent VAL
python -m scripts.breakout_vol.run_stage CLASSIFY
python -m scripts.breakout_vol.post_primary ; python -m scripts.breakout_vol.worked_examples ; python -m scripts.breakout_vol.build_report
```
Determinism: seeded bootstrap (20260930) and permutation (20260931); results reproduce byte-for-byte from the hashed snapshot. **Tested, not asserted:** after amendments A1–A3 the final freeze was used to re-run TRAIN (first run pre-A1) and VAL (first run pre-A2); `cells`, `cohort`, `costs`, `bench` and `accounting` files were identical byte-for-byte and both event ledgers identical frame-for-frame (19,761 and 17,067 events). Data paths are absolute under `F:/Nifty/data` (the worktree carries no `data/`).
