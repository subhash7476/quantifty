# TS Basis Filter — SD / Breadth / Marginal-Value / Gate-Stability Probe Report

**Date:** 2026-08-03  |  **Window:** 2016-02-11 -> 2022-12-31 (burned TRAIN+HOLDOUT)
**Fence:** hard-stop at 2022-12-31 — sealed window (2023-01-01 -> 2026-07-24, 876 formations) untouched.

## 1. Resolved sources and fence proof

- **Signal store/column:** `data/signal_engine/ts_basis_daily/ts_signals.duckdb` → `signals.z_ts` 
  (this is the daily build's own output — `build_ts_basis_daily.py` OUT_DB; `ts_facts.duckdb`/`z_carry_neut` is the publish layer, not the construction).
- **OI source:** `futures_bhavcopy.chg_in_oi` on the near-month FUTSTK contract per (underlying, trade_date). Verified: `chg_in_oi` agrees with computed `open_int_t − open_int_{t−1}` (e.g. TCS 54,000 / 81,600 / −241,800). Coverage 100% (305,112/305,112 underlying-days).
- **Cross-section:** full eligible daily universe (every non-null `z_ts`), NOT top-5 per side. Rows loaded 303,639, formations 1697, underlyings 288.
- **Fence proof:** observed formation range [2016-02-17, 2022-12-30] — assertion PASSED.

## 2. Base statistics (H=1 primary, H=5 robustness)

| Series | n | mean IC | sd_IC | AC1 | NW t | avg names |
|---|---|---|---|---|---|---|
| H=1d (primary) | 1676 | 0.0495 | 0.0924 | 0.0257 | 22.3064 | 179 |
| H=5d (robust)  | 1598 | 0.0286 | 0.0916 | 0.3814 | 8.7442 | 179 |

## 3. Eight configurations — IC + breadth (H=1)

| Config | n | mean IC | sd_IC | AC1 | NW t | avg names | N_eff | PC1 |
|---|---|---|---|---|---|---|---|---|
| base | 1676 | 0.0495 | 0.0924 | 0.0257 | 22.3064 | 179 | 10.1 | 0.292 |
| G1 | 1500 | 0.0490 | 0.0915 | 0.0245 | 21.2230 | 181 | 10.3 | 0.285 |
| G2 | 1680 | 0.0387 | 0.1205 | 0.0169 | 12.8221 | 96 | — | — |
| G3 | 1595 | 0.0500 | 0.0920 | 0.0009 | 22.2632 | 179 | 9.9 | 0.294 |
| full | 1433 | 0.0402 | 0.1189 | 0.0129 | 12.2930 | 97 | — | — |
| drop_G1 | 1600 | 0.0398 | 0.1202 | 0.0103 | 13.0446 | 96 | — | — |
| drop_G2 | 1427 | 0.0496 | 0.0912 | -0.0033 | 21.1495 | 181 | 10.2 | 0.289 |
| drop_G3 | 1505 | 0.0387 | 0.1189 | 0.0234 | 12.0779 | 97 | — | — |

## 4. Power — fixed-δ and own-δ (two-sided, target 0.80)

| Config | sd_IC | n | fixed-δ power | own-δ power | n_req @0.015 | n_req @0.020 | n_req @0.029 |
|---|---|---|---|---|---|---|---|
| base | 0.0924 | 1676 | 1.000 | 1.000 | 300 | 170 | 82 |
| G1 | 0.0915 | 1500 | 1.000 | 1.000 | 294 | 167 | 81 |
| G2 | 0.1205 | 1680 | 1.000 | 1.000 | 509 | 287 | 138 |
| G3 | 0.0920 | 1595 | 1.000 | 1.000 | 297 | 168 | 81 |
| full | 0.1189 | 1433 | 1.000 | 1.000 | 496 | 280 | 134 |
| drop_G1 | 0.1202 | 1600 | 1.000 | 1.000 | 507 | 286 | 137 |
| drop_G2 | 0.0912 | 1427 | 1.000 | 1.000 | 293 | 166 | 80 |
| drop_G3 | 0.1189 | 1505 | 1.000 | 1.000 | 496 | 280 | 134 |

## 5. Marginal-value verdict (drop-column, full vs full-minus-gate)

| Gate | Δn | Δsd_IC | Δ fixed-δ power | Δ own-δ power | Δ n_req@0.020 | Verdict |
|---|---|---|---|---|---|---|
| G1 | -167 | -0.0013 | 0.0000 | 0.0000 | -6 | **KEEP** |
| G2 | +6 | 0.0277 | 0.0000 | 0.0000 | +114 | **REMOVE** |
| G3 | -72 | -0.0000 | 0.0000 | 0.0000 | +0 | **REMOVE** |

*Saturation note:* on this burned window own-δ power is 1.0 for every config (IC 0.049, t≈22 — the TRAIN/HOLDOUT selection surface is strong in-sample). Δown-δ power is therefore ≈0 and cannot discriminate; the verdict uses Δ n_req@0.020 (positive = the gate adds required formations = net cost). This is a *burned-window* reading, not a confirmatory one — it measures relative cost, not absolute feasibility.*

## 6. Gate Stability — regime consistency (required output)

| Gate | Bull | Bear | High VIX | Low VIX | Pre-COVID | COVID | Post-COVID | Consistency | Concentration | Stability-clear? |
|---|---|---|---|---|---|---|---|---|---|---|
| G1 | +0.0003 | -0.0027 | +0.0015 (circular) | +0.0000 (circular) | +0.0004 | +0.0018 | -0.0009 | 3/5 | COVID 82% | **NO** |
| G2 | -0.0089 | -0.0134 | -0.0064 | -0.0117 | -0.0088 | -0.0063 | -0.0176 | 0/7 | — | **NO** |
| G3 | +0.0020 | -0.0026 | +0.0004 | +0.0023 | +0.0026 | +0.0010 | -0.0019 | 5/7 | Pre-COVID 73% | **NO** |

Rule (a): a gate's self-defining axis is excluded from its own consistency count (G1's VIX cells marked circular).
Rule (b): concentration anchored on the calendar axis (Pre/COVID/Post — mutually exclusive, exhaustive); Bull/Bear and VIX are corroborating lenses.

## 7. Predictions (held/failed)

| # | Prediction | Result |
|---|---|---|
| P1 | G2 raises sd_IC vs base | **HELD** |
| P2 | G1 and G3 lower n vs base; G2 leaves n unchanged | **HELD** |
| P3 | base N_eff is materially larger than OSC's option-cell N_eff ≈ 1.9 (equities less correlated than option cells) | **HELD** |
| P4 | at fixed δ, every gate's power ≤ base | **HELD** |
| P5 | at own δ, at least one gate fails to beat its drop-column (REMOVE recommended) | **HELD** |
| P6 | at least one §5-passing gate is not stability-clear (regime-dependent) | **HELD** |

## 8. G1 sensitivity (k ∈ {1.25, 1.5, 2.0})

| k | n | mean IC | sd_IC |
|---|---|---|---|
| 1.25 | 1345 | 0.0490 | 0.0912 |
| 1.5 | 1500 | 0.0490 | 0.0915 |
| 2.0 | 1572 | 0.0490 | 0.0919 |

## 9. Carry-forward note

- Mean IC is **diagnostic only** — the RFA δ anchor must be defended independently (never this burned mean, never the sealed +0.077).
- The preserved 876-formation sealed window was not read.
