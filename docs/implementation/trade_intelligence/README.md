# TI — Trade Intelligence Observatory

**Program:** Trade Intelligence Implementation
**Architecture Reference:** TRADE_INTELLIGENCE_IMPLEMENTATION_PLAN.md (Frozen M0)
**Status:** Implementation Phase — M0 in progress

---

## Overview

The Trade Intelligence Observatory is a standalone research database that records every trade made by the TS Basis Daily strategy. Its purpose is post-trade learning: why did this trade work, why did it fail, what patterns emerge across thousands of trades?

It consumes existing signal, facts, and regime data. It produces no trading decisions. It is a pure observer of the strategy.

## Architecture

```
ts_signals.duckdb ──┐
ts_facts.duckdb ────┤
1d index store ─────┼──→ build_trade_intelligence.py ──→ trade_intelligence.duckdb
sector CSV ─────────┘
```

Single table `trades` — one row per (underlying, entry_date, side). INSERT at entry with immutable signal snapshot. UPDATE at exit with outcome.

## Documents

| Document | Purpose |
|---|---|
| `TRADE_INTELLIGENCE_IMPLEMENTATION_PLAN.md` | Frozen schema, component design, milestone roadmap |
| `IMPLEMENTATION_LEDGER.md` | Append-only event log — milestone status, reviews, certifications |
| `reports/` | Per-milestone implementation reports |

## Milestones

| ID | Milestone | Status |
|----|-----------|--------|
| M0 | Trade Intelligence Foundation | In progress |
| M1 | TradeIntelligenceSink (live capture) | Not started |
| M2 | Analytics | Not started |
| M3 | Option Snapshots | Not started |
| M4 | Option Lifecycle | Not started |

## Code Location

- Builder: `scripts/signal_engine/ts_basis_daily/build_trade_intelligence.py`
- Tests: `tests/trade_intelligence/test_builder.py`
- DB: `data/signal_engine/trade_intelligence/trade_intelligence.duckdb`

---

**End of Document**
