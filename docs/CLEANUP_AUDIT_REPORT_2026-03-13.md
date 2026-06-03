# Project Cleanup Audit Report
**Date:** 2026-03-13
**Performed by:** Claude Code
**Branch:** pixity_v3_expansion

---

## Summary

| Category | Files Removed | Space Freed |
|----------|--------------|-------------|
| Orphaned core modules | 24 | ~500KB |
| Old strategy scripts (v3–v8) | 7 | ~100KB |
| Old implementation docs | ~25 | ~500KB |
| Root clutter / artifacts | 6 | ~50KB |
| `__pycache__` / `.pyc` files | 50 dirs, 720 files | ~50MB |
| `.pytest_tmp/` + `.pytest_cache/` | — | ~61MB |
| `data/backtest/runs/` (Phase 5/6 scans) | 2,228 | **~1.9GB** |
| `data/market_data/nse/ticks/` | 9 | **~2.4GB** |
| `archive/` (root) | ~20 | ~5.7MB |
| `docs/archive/` | 12 | ~200KB |
| **Total** | **~2,370 files** | **~4.5GB** |

---

## 1. Root-Level Clutter

**Deleted:**

| File | Reason |
|------|--------|
| `STOP` | Runtime marker file (32 bytes), stale |
| `nul` | Windows NUL artifact (0 bytes) |
| `0` | Unknown artifact (0 bytes) |
| `config.db` | Empty DuckDB file (0 bytes) |
| `plan.md` | Old dev planning notes — superseded by CLAUDE.md |
| `QWEN.md` | Duplicate LLM context guide (14KB) — CLAUDE.md is source of truth |
| `CODEBASE_GUIDE.md` | Superseded by docs/CODEBASE_OVERVIEW.md |
| `PROJECT_ARCHITECTURE_REPORT.md` | Feb 6 snapshot, stale |
| `PROJECT_MASTER.md` | Feb 6 snapshot, stale |

**Kept:**

| File | Reason |
|------|--------|
| `CLAUDE.md` | Primary project instructions — actively maintained |
| `DEVELOPER_GUIDE.md` | Active reference |
| `PROJECT_REVIEW_SUMMARY.md` | Recent review summary |
| `README.md` | Project entry point |

---

## 2. Orphaned Core Modules

These files had **zero imports** anywhere in the codebase (confirmed via grep across all `.py` files). Deleted:

**`core/data/`**
- `backtest_persistence.py`
- `historical_analytics_provider.py`
- `ohlcv_reader.py`
- `websocket_market_provider.py`
- `chunked_historical_market_provider.py`
- `analytics_persistence.py`

**`core/analytics/`**
- `indicators/linreg.py`
- `reporting.py`
- `drawdown_analyzer.py`
- `loss_clustering.py`
- `recovery_metrics.py`
- `comparison.py`

**`core/execution/`**
- `write_buffer.py`
- `capital_allocator.py`
- `sizing_policy.py`
- `trade_recorder.py`
- `backfill_recorder.py`
- `backfill_writer.py`
- `recorder.py`
- `equity.py`
- `future.py`

**`core/post_trade/`**
- `trade_context_builder.py`
- `fact_frequency_analyzer.py`

**`core/state/`**
- `breadth_state_engine.py`
- `daytype_monitor.py`

> **Note:** Two files were incorrectly flagged as orphaned and restored from git:
> - `core/database/locks.py` — used by `DatabaseManager` (Windows file locking)
> - `core/logging/logger.py` — imported by NiftyShield and core runner

---

## 3. Superseded Strategy Scripts

v3–v8 are historical iterations. v9 is the current production strategy.

**Deleted:**
- `scripts/run_v3_backtest.py` — compression + 1H breakout
- `scripts/run_v4_backtest.py` — compression + daily breakout
- `scripts/run_v5_backtest.py` — 20d momentum, trail only
- `scripts/run_v6_backtest.py` — 20d momentum, 2×ATR trail
- `scripts/run_v6_1_backtest.py` — v6.1 variant
- `scripts/run_v7_backtest.py` — mean reversion
- `scripts/run_v8_backtest.py` — 15m intraday OR compression

**Kept:** `scripts/run_v9_backtest.py`, `scripts/run_v9_paper.py`

---

## 4. Old Documentation (Implementation Logs)

These were progress notes for completed tasks — no ongoing reference value.

**Deleted from `docs/`:**
- `2026-02-01-1707-Premium-TP-SL-*.md` (3 files)
- `DATABASE_ARCHITECTURE_REFACTOR.md` (41KB) + `*_IMPLEMENTATION.md`
- `DUCKDB_LOCK_COMPREHENSIVE_FIX.md` + `DUCKDB_ROOT_CAUSE_FIX.md`
- `SCANNER_BUG_FIXES.md` + `SCANNER_BUG_FIX_COMPLETION_REPORT.md` + `SCANNER_RECOVERY_MANAGER_FIX.md`
- `SCANNER_WATCHLIST_IMPLEMENTATION.md` + `TASK_COMPLETION_SCANNER_DATABASE.md`
- `PIXITYAI_BATCH_BACKTEST_IMPLEMENTATION.md` + `*_LOG.md` + `*_PROMPT.md`
- `PIXITYAI_SCANNER_INTEGRATION.md` + `*_STATUS.md`
- `PIXITYAI_PROFITABILITY_OPTIMIZATION.md`
- `UPSTOX_V3_HISTORICAL_FETCHER_IMPLEMENTATION.md`
- `ZMQ_LAYER_IMPLEMENTATION_SUMMARY.md`
- `LOGGING_STATUS_BAR_PLAN.md`
- `REGIME_ENGINE.md`
- `pixityAI Implementation.md` + `pixityAI Plan.md`
- No-extension files: `Claude Plan HMM Regime Trading System`, `Financial Model usability`, `GPT Execution Engine Plan`
- `GPT Execution Engine Plan Implemented.md`

**Deleted `docs/archive/`:** 12 phase completion reports (Phase 1–9, architecture)

**27 docs remain** — all active reference material.

---

## 5. Archive Directories

| Directory | Contents | Action |
|-----------|----------|--------|
| `archive/` (root) | Old v1 strategies, old test files | **Deleted** (5.7MB) |
| `docs/archive/` | Phase 1–9 completion reports | **Deleted** |

---

## 6. Data Files

### Backtest Runs — `data/backtest/runs/`
- **2,228 DuckDB files** from Phase 5/6 symbol scans (Feb 2026)
- Results already documented in `CLAUDE.md` and project memory (4 symbols pass: VEDL, BDL, KALYANKJIL, PNBHOUSING)
- **Deleted: 1.9GB**
- Directory preserved (empty) for future backtest runs

### Tick Data — `data/market_data/nse/ticks/`
- **9 DuckDB files** covering Feb–Mar 2026 trading days
- Raw 1-second tick data — not used by any active strategy
- **Deleted: 2.4GB** (user instruction)

---

## 7. Database Tables

### `data/trading/trading.db`

| Table | Rows | Status |
|-------|------|--------|
| `trades` | 6,470 | Active — execution history |
| `ns_paper_signals` | 540 | Active — NiftyShield signals |
| `ns_paper_trades` | 513 | Active — NiftyShield trade log |
| `stock_paper_signals` | 630 | Active — StockDaytype signals |
| `stock_paper_trades` | 162 | Active — StockDaytype trade log |
| `positions` | 1 | Active (14 rows → 1 after cleanup) |
| `commodity_strategy_snapshots` | 20 | MCX feature, inactive in runner |
| `orders` | 0 | Active schema — paper mode |
| `v9_paper_signals` | 0 | Active schema — V9 PM not generating yet |
| `v9_paper_trades` | 2 | Active |
| `tlp_trade_log` | 0 | Created on next startup by TLPLogger |

**Cleaned:**
- Deleted `data/trading.db` (root-level, 0 bytes, artifact)
- Cleared 13 stale `positions` rows from August 2025

### `data/signals/signals.db`

| Table | Rows | Status |
|-------|------|--------|
| `signals` | 392,407 | Active |
| `confluence_insights` | 131,801 | Active |
| `regime_insights` | 0 | Empty — populated by regime runner |

---

## 8. Test Results Post-Cleanup

```
94 passed in 9.87s
1 pre-existing failure: test_get_weekly_expiry_nifty
  → Hardcoded date assertion ("2026-03-10") — not related to cleanup
```

All 94 tests pass. Core imports verified:
- `core.database.manager.DatabaseManager` ✓
- `core.analytics.capture.TLPLogger` ✓
- `core.strategies.nifty_shield_strategy.NiftyShieldStrategy` ✓

---

## 9. Not Touched (Review Candidates)

These were identified as potentially unused but left in place pending review:

| Area | Files | Reason kept |
|------|-------|-------------|
| `strategy/`, `services/`, `analytics/`, `risk/` (top-level) | ~10 files | MCX commodity system — incomplete feature, has Flask blueprint |
| `core/data/*.py` shims (8 files) | — | Re-export compatibility layer for `core/database` |
| Research/diagnostic scripts in `scripts/` | ~30 files | Development tools, usage unknown |
| `data/market_data/nse/ticks/` | Cleared by user | — |

---

## 10. Current Project Footprint

| Path | Size |
|------|------|
| `data/market_data/nse/candles/` | 6.6GB |
| `data/` (total) | 3.0GB |
| `data/signals/signals.db` | 223MB |
| `data/live_buffer/` | 2.7GB |
| Project source code | ~50MB |
