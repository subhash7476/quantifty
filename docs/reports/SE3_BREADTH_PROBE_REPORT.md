# SE-3 — Index-versus-constituent dispersion: Breadth / SD Probe Report

**Date:** 2026-08-05  |  **Window:** 2023-01-02 -> 2025-12-31 (index leg burned; stock leg **SPENT** by this probe)
**Unread windows preserved:** NIFTY index options 2016-02-11 -> 2022-12-31 (1,701 dates); stock options 2021-01-01 -> 2022-12-31; both legs 2026-01-01 -> 2026-07

## 1. Fence proof

- **stock**: observed `trade_date` range [2023-01-02, 2025-12-31] — inside fence
- **idx**: observed `trade_date` range [2023-01-02, 2025-12-31] — inside fence
- **fut**: observed `trade_date` range [2023-01-02, 2025-12-31] — inside fence
- Hard assertion per source at top of pipeline: `assert FENCE_START <= min and max <= FENCE_END` — **PASSED** on all three legs
- First usable formation date (complete 60-trading-day warmup inside fence): **2023-03-28** — variant B's 60-day window is binding; variant A's 21-day RV warmup completes earlier.

## 2. Window ledger (state entering vs after this probe)

| Leg | Window | State entering this probe | State after |
|---|---|---|---|
| NIFTY index options | 2023-01-02 -> 2025-12-31 | **Already burned** — MSRP triage + OSC SD probe | Unchanged — costs nothing |
| OPTSTK stock options | 2023-01-02 -> 2025-12-31 | **Not previously read for research** | **SPENT by this probe** |
| NIFTY index options | 2016-02-11 -> 2022-12-31 | Unread, 1,701 dates | **Preserved — untouched** |
| OPTSTK stock options | 2016-07-31 -> 2020-12-31 | **Prior-exposed** — Skew sleeve TRAIN | Unchanged |
| OPTSTK stock options | 2021-01-01 -> 2022-12-31 | Unread | **Preserved — untouched** |
| Both legs | 2026-01-01 -> 2026-07 | Unread | **Preserved — untouched** |

## 3. Attrition (absolute row counts)

| Stage | Stocks | NIFTY |
|---|---|---|
| Option rows in fence (member universe) | 8,549,977 | 1,127,502 |
| After PIT membership + F&O-live | 7,812,572 | — |
| Traded (contracts>0, OI>0) | 2,770,433 | 621,635 |
| On selected expiry (§3.2) | 1,825,719 | 111,105 |
| With forward (§3.3) | 1,825,719 | 111,105 |
| Settle >= 0.5 | 1,660,400 | 110,249 |
| |ln(strike/F)| <= 0.1 | 1,289,018 | 100,030 |
| ATM-IV (date-name cells) | 36,872 | 738 |
| After t+1 pairing (date-name cells) | 36,776 | — |

Dropped (date, name) tallies:

| Drop reason | Stocks | NIFTY |
|---|---|---|
| §3.2 no expiry in [7,60] | 0 | 0 |
| §3.3 no forward | 0 | 0 |
| §3.4 no ATM IV cell | 5 | 0 |
| IV inversion discard (attempted) | 10/73752 (0.0%) | 0/1476 (0.0%) |
| §3.7 pairing dropped (neither leg paired to t+1) | 47 | — |

## 4. Names per day (variant A and B universes)

**Variant A** (>=20 names with sigma & rv on the date):

| Year | median | p10 | p90 |
|---|---|---|---|
| 2023 | 50 | 49 | 50 |
| 2024 | 50 | 50 | 50 |
| 2025 | 50 | 49 | 50 |

**Variant B** (>=40 paired obs in trailing 60d):

| Year | median | p10 | p90 |
|---|---|---|---|
| 2023 | 50 | 49 | 50 |
| 2024 | 50 | 48 | 50 |
| 2025 | 49 | 47 | 50 |

## 5. THE HEADLINE NUMBERS

| Variant | n_dates | mean_IC | **sd_IC** | Newey-West t (lag 5) | AC1 |
|---|---|---|---|---|---|
| A (pure cross-section) | 713 | -0.1298 | **0.1938** | -14.6401 | 0.0721 |
| B (index-anchored) | 484 | -0.1196 | **0.1989** | -9.5577 | 0.2194 |

**Expected sign is NEGATIVE** (rich options subsequently underperform delta-hedged). Nothing is flipped.

## 6. Breadth — raw panel (rolling 60-trading-day)

| Statistic | Value |
|---|---|
| Median rho_bar (raw) | 0.150 |
| **Median N_eff (raw)** | **5.9** |
| Median PC1 share (raw) | 20.17% |
| Median N (names populated through window) | 46 |
| Median raw names/day | 50 |

### Demeaned panel (SECONDARY — artifact warning)

> **WARNING:** demeaning mechanically induces rho_bar ~ -1/(N-1), which drives N_eff toward N by construction. **The demeaned N_eff is an artifact and must never be quoted as the breadth of this cross-section.** It is reported only to show how much of the raw correlation is a common level vs genuine pairwise co-movement. The **raw N_eff is the headline**, comparable to OSC's 1.9 and the TS Basis filter probe's 10.1.

| Statistic (demeaned) | Value |
|---|---|
| Median rho_bar | 0.001 |
| Median N_eff | 44.1 |
| Median PC1 share | 15.42% |

## 7. Implied-correlation diagnostics (§3.8, diagnostic only — NOT the signal)

| Quantity | Value |
|---|---|
| Dates with rho_imp computable | 737 |
| Median rho_imp | 0.259 |
| 10th percentile | 0.178 |
| 90th percentile | 0.424 |
| Fraction outside [0,1] | 0.3% |
| Median renormalization mass | 1.000 |

rho_imp is NOT clipped and NOT used as a per-name signal.

## 8. Feasibility read-out (decision ladder, §5)

Ladder applied mechanically via `power.n_required`, two-sided, power 0.80, at both confirmatory-n readings:

| Variant | sd_IC | n=1,701 (permissive) | n≈495 (strict) |
|---|---|---|---|
| A | 0.1938 | **Green** | **Red-amber** |
| B | 0.1989 | **Green** | **Red-amber** |

Rung semantics (identical to OSC's anchors, applied at both readings):

| Rung | Meaning |
|---|---|
| **Green** | Feasible even at a pessimistic δ = 0.015 -> proceed to design |
| **Amber** | Feasible only if δ >= 0.020 can be **independently** defended |
| **Red-amber** | Feasible only at δ >= 0.029 — CB-N50's *stock* HOLDOUT IC; no claim on option cells |
| **ABANDON** | Infeasible at any defensible δ |

**Do not editorialize beyond the rung.** The δ anchor is NOT an output of this probe (§8 of the prompt).

## 9. Predictions (pre-registered, state-before-run)

| # | Prediction | Actual | Held? |
|---|---|---|---|
| P1 | Median names/day (variant A) >= 35 | 50 | **HELD** |
| P2 | Raw rho_bar >= 0.15 | 0.150 | **HELD** |
| P3 | Raw median N_eff < 15 | 5.9 | **HELD** |
| P4 | Raw median N_eff > 1.9 | 5.9 | **HELD** |
| P5 | mean_IC (variant A) negative | -0.1298 | **HELD** |
| P6a | sd_IC(A) <= 0.30 | 0.1938 | **HELD** |
| P6b | sd_IC(A) >= 0.15 | 0.1938 | **HELD** |
| P7 | sd_IC(B) >= sd_IC(A) | 0.1989 | **HELD** |
| P8 | IV inversion discard rate < 10% (stocks) | 0.0% | **HELD** |
| P9 | t+1 pairing attrition < 25% of (date,name) cells | 0.1% | **HELD** |
| P10 | Median renormalization mass >= 0.85 | 1.000 | **HELD** |

## 10. Implementation notes

- All Black-76 functions imported from `scripts/osc/sd_probe.py` — no reimplementation.
- `_mcwb_rows` locates the `Security Symbol` and weight columns by header name, so archive layout drift is handled without touching the pinned spec.
- Source-pollution findings (DUMMY*/TMPV* excluded from membership): {'DUMMYREL': '2023-07-01', 'TMPV': '2026-06-01', 'DUMMYTATAM': '2025-10-01', 'DUMMYHDLVR': '2026-01-01'}
- Nothing under `data/` is written (read-only).
