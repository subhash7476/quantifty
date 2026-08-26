# TI — Trade Intelligence Observatory

**Program:** Trade Intelligence Implementation
**Architecture Reference:** TRADE_INTELLIGENCE_IMPLEMENTATION_PLAN.md (Frozen M0)
**Status:** Implementation Phase — M0–M3 delivered; v2 universal recorder live

---

## Overview

The Trade Intelligence Observatory is a standalone research database that records trades for post-trade learning: why did this trade work, why did it fail, what patterns emerge?

It consumes execution reality and produces no trading decisions. It is a pure observer.

**v2 (2026-08-26):** capture is now universal and strategy-agnostic. A generic `TradeRecorder` hooked at `ExecutionHandler._handle_broker_fill` records every executed trade from every strategy in PAPER and LIVE — no per-strategy integration required. The TS Basis Daily-specific sink (`TradeIntelligenceSink`) remains for the historical rebalancer-replay path only.

## Architecture

```
Every strategy ──→ ExecutionHandler._handle_broker_fill ──→ TradeRecorder ──→ trade_intelligence.duckdb.executed_trades
(ts_basis_daily historical rebuild only) ──→ build_trade_intelligence.py ──→ trade_intelligence.duckdb.trades
```

Two tables:
- `executed_trades` — live capture, one round-trip row per position (entry fill → exit fill), keyed by entry fill_id. Signal snapshot + regime context immutable at INSERT; outcome columns populate on close.
- `trades` — M0 historical builder reconstruction of TS Basis Daily TRAIN/HOLDOUT (cleared 2026-08-26 by operator reset).

## Documents

| Document | Purpose |
|---|---|
| `TRADE_INTELLIGENCE_IMPLEMENTATION_PLAN.md` | Frozen schema, component design, milestone roadmap |
| `IMPLEMENTATION_LEDGER.md` | Append-only event log — milestone status, reviews, certifications |
| `reports/` | Per-milestone implementation reports |
| `reports/GENERIC_RECORDER_REPORT.md` | v2 universal recorder + M0 §11 limitations resolution |

## Code Location

- Universal recorder: `core/execution/portfolio/trade_recorder.py` (wired in `core/execution/handler.py`, toggle: `ExecutionConfig.trade_recorder_enabled`)
- Historical builder (TS Basis Daily only): `scripts/signal_engine/ts_basis_daily/build_trade_intelligence.py`
- Tests: `tests/trade_intelligence/test_trade_recorder.py` (14), `tests/trade_intelligence/test_builder.py` (13, data-dependent)
- DB: `data/signal_engine/trade_intelligence/trade_intelligence.duckdb`

---

**End of Document**
