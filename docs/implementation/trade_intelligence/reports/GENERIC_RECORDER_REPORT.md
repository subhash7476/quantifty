# Generic Trade Recorder — v2 Implementation Report

**Document:** Universal fill-seam trade recorder
**Date:** 2026-08-26
**Supersedes (for live capture):** TradeIntelligenceSink (M1, TS Basis Daily-only)
**Status:** Delivered — 14/14 tests green; execution suite 320 passed

---

## 1. What was built

`TradeRecorder` (`core/execution/portfolio/trade_recorder.py`) — a strategy-agnostic,
write-only recorder hooked at `ExecutionHandler._handle_broker_fill`
(`core/execution/handler.py`). Every executed trade from every strategy in PAPER and
LIVE flows through that single seam via `broker.subscribe_fills`, so no per-strategy
integration is ever needed again.

**Storage:** new table `executed_trades` in `data/signal_engine/trade_intelligence/trade_intelligence.duckdb`.
One round-trip row per position: keyed by the **entry fill_id**, INSERT at open,
UPDATE at close. Partial fills accumulate (VWAP entry price on adds, realized-pnl and
fee accrual across reduces). Flips finalize the old row AND insert the residual as a
new opposite-side trade. Signal snapshot + regime context are immutable after INSERT.

**Regime context:** India VIX close + Nifty trailing-20-session return, read from the
1d index store using the latest file ≤ entry date (today's file doesn't exist yet for
intraday fills); NULL when unavailable, never blocking.

**Toggle:** `ExecutionConfig.trade_recorder_enabled` (default `True`). Disable for bulk
historical replays that would pollute the learning DB. Any recorder failure logs and
disables itself — execution is never touched.

## 2. Handler wiring

| Change | Location |
|---|---|
| Construct `TradeRecorder` (failure → disabled, logged) | `handler.py __init__`, after PortfolioGreeks |
| Capture `signed_qty_before = net_quantity(symbol)` before `update_from_fill` | `_handle_broker_fill` |
| `trade_recorder.on_fill(fill, order, signed_qty_before, realized_pnl)` after `pnl_tracker.update` | `_handle_broker_fill` |

Restore replay (`_replay_state`) calls `process_fill` directly and does **not** pass
through `_handle_broker_fill` — recovered history cannot double-record.

## 3. M0 report §11 limitations — resolution map

| §11 Limitation | Resolution by the generic recorder |
|---|---|
| Exit reasons all `EXIT_SIGNAL` — builder cannot simulate TP/SL | Moot for live capture: exits come from real execution. Closing order metadata may carry `exit_reason` (strategies that attach it get exact TP/SL/recovery reasons); default fallback is `CLOSED`. Historical reconstruction remains EXIT_SIGNAL-only — accepted, it models a burned research window. |
| 23 NULL regime cells (early dataset dates) | Forward recording looks up regime from the *latest available* daily file at entry time, so historical store gaps don't apply. NULLs now only occur if the 1d index store is missing entirely — visible and diagnosable in live data. |
| Uses `fwd_ret_1m` from signals DB — no live MTM | Recorder stores actual fill prices and actual per-fill realized PnL from the position tracker — true MTM, strictly better than the research proxy. Fees accumulate per fill. |
| Forward runner integration not built | Structurally solved: the hook lives in `ExecutionHandler`, which every runner constructs (`fno_runner.py`, paper runners, future runners). Nothing to integrate per runner. |

## 4. Known constraints

- **Single-writer DuckDB:** one process may hold the write connection at a time. If an
  analytics script holds a long-lived connection to the same file while the runner
  records, writes fail-logged-and-disabled for those fills. Run analytics against a
  copy or in short sessions.
- **The M0 builder must not be re-run** against this file while the recorder is active:
  it unlinks the whole DB (ledger note, event #8).
- Strategy-side exit reasons require attaching `exit_reason` to the closing order's
  `metadata.strategy_metadata`; otherwise rows record `CLOSED`.

## 5. Tests

`tests/trade_intelligence/test_trade_recorder.py` — 14 passing:

entry insert / snapshot JSON immutability / short direction / regime NULLs without
index data / add-fill VWAP + fee accrual / close populates outcome / signal columns
unchanged after exit / exit_reason from closing metadata / partial-reduce then
finalize / flip closes old + opens residual / duplicate fill idempotent /
restart recovery via DB lookup / never raises on DB error / disabled noop.

`test_builder.py` (13) now skips when the operator-cleared DB holds no rows.

---

**End of Report**
