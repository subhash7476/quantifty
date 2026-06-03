# Trade Learning Protocol V1 (TLP V1)

**Status:** Live — NiftyShield wired, StockDaytype inline, PixityAI infrastructure built
**Version:** TLP_V1_CORE
**Last updated:** 2026-03-13

---

## 1. Overview

TLP V1 records every closed trade with full structural context — regime, VIX, spread structure, MAE, MFE, exit efficiency, and hold duration. The goal is to identify where alpha concentrates and where it leaks (e.g. profit target too early, stop loss too tight, wrong structure for the regime).

---

## 2. What Is Captured Per Trade

| Field | Source | Description |
|-------|--------|-------------|
| `regime` | DayType model | Predicted state at entry (Choppy / BullTrend / BearTrend) |
| `confidence` | DayType model | Model confidence at 13pm checkpoint |
| `vix` | India VIX daily close | VIX level that day |
| `structure` | `_select_structure()` | Spread chosen (short_straddle / iron_fly / bull_put_spread / bear_call_spread / short_strangle) |
| `session_type` | Entry hour | AM (< 12:30) or PM (≥ 12:30) |
| `mae_rs` | Real-time tracking | Max adverse excursion in Rs during trade life |
| `mfe_rs` | Real-time tracking | Max favorable excursion in Rs during trade life |
| `pnl_net_rs` | At close | Realized net P&L after costs |
| `exit_efficiency` | Computed at close | `pnl_net / mfe_rs` — how much of the available profit was captured |
| `hold_bars` | Bar counter | Number of 1m bars held while POSITIONED |
| `exit_reason` | Close trigger | profit_target / stop_loss / time_exit / emergency_exit |

---

## 3. Architecture

### 3A. Storage

| Table | Strategy | Notes |
|-------|----------|-------|
| `tlp_trade_log` | NiftyShield (+ any future strategy) | Unified cross-strategy log |
| `stock_paper_trades` | StockDaytype | TLP fields inline (MAE/MFE already captured) |
| `ns_paper_trades` | NiftyShield | Extended with `mfe_rs`, `exit_efficiency`, `hold_bars` |

### 3B. Components

| Component | File | Status |
|-----------|------|--------|
| `TLPLogger` | `core/analytics/capture.py` | **Live** — singleton initialised in unified_runner |
| `CaptureEngine` | `core/analytics/capture.py` | Built — designed for PixityAI equity context (HMM, CSAD, breadth) |
| `MetricsService` | `core/analytics/metrics_service.py` | Built — frozen percentile buffers (requires `daily_structural_metrics` table) |
| `DiagnosticsEngine` | `core/analytics/diagnostic_engine.py` | Built — post-hoc MAE/MFE from 1m bars for directional equity trades |
| Structural Review | `scripts/perform_structural_review.py` | **Live** — cross-strategy CLI report |

### 3C. Data Flow

```
NiftyShield _manage()          → tracks _mfe_rs, _max_loss_rs, _hold_bars per bar
NiftyShield _close()           → computes exit_efficiency
                               → _persist_trade_exit() saves to ns_paper_trades
                               → TLPLogger.record() saves to tlp_trade_log

StockDaytype _persist_trade_exit() → saves MAE/MFE/efficiency inline to stock_paper_trades
                                   → (not yet wired to TLPLogger)

perform_structural_review.py   → reads tlp_trade_log + stock_paper_trades
                               → outputs cross-strategy analysis
```

---

## 4. How to Run Structural Review

```bash
# All strategies
python scripts/perform_structural_review.py

# NiftyShield only
python scripts/perform_structural_review.py --strategy nifty_shield

# StockDaytype only
python scripts/perform_structural_review.py --strategy stock_daytype

# Date range + lower threshold
python scripts/perform_structural_review.py --start-date 2026-01-01 --min-trades 3
```

**Output sections:**

For NiftyShield:
- Structure performance (WR, avg net, MFE, MAE, exit efficiency per spread type)
- Exit reason breakdown (profit_target / stop_loss / time_exit with avg hold bars)
- Regime × VIX cross-tab (which regime+VIX combination earns most)
- MAE/MFE diagnostic (captured vs available premium)

For StockDaytype:
- Coverage report (how many trades have each TLP field populated)
- Expectancy by regime and dispersion percentile bucket
- Signal percentile decay curve
- MAE/MFE efficiency diagnostic

---

## 5. Exit Efficiency — Interpretation

```
exit_efficiency = pnl_net_rs / mfe_rs
```

| Range | Meaning |
|-------|---------|
| 0.8 – 1.0 | Excellent — captured most of available profit |
| 0.5 – 0.8 | Good — reasonable exit timing |
| 0.2 – 0.5 | Poor — left significant premium on table |
| < 0 | Exit was a loss despite favorable excursion (gave back all gains) |

A consistent efficiency below 0.5 on `profit_target` exits suggests the 50% threshold may be too early. A high efficiency on `stop_loss` exits means the stop fired near the worst point (good). A low efficiency on `time_exit` means the time stop is suboptimal.

---

## 6. What Is Not Yet Wired

| Gap | Path to fix |
|-----|-------------|
| StockDaytype → tlp_trade_log | Call `get_tlp_logger().record()` in `_persist_trade_exit()` |
| V9 PM Scalper → tlp_trade_log | Same — add `mfe_rs` tracking to V9 strategy + TLPLogger call |
| PixityAI `CaptureEngine` | Requires `regime_insights` + `daily_structural_metrics` tables to be populated |
| Dispersion / breadth fields | Not computed in live unified_runner currently |

---

## 7. TLP V2 Considerations

When enough data accumulates (≥ 200 NiftyShield trades):
- Add confidence-band on exit_efficiency by structure
- Add time-of-day analysis (which hold_bars range has highest efficiency)
- Add rolling 20-trade efficiency trend (is the edge stable or decaying?)
- Bump version to `TLP_V2_CORE` and freeze all V1 records

---

*Every loss is a paid lesson. Every win is a reproducible fact.*
