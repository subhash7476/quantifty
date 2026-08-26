# TI Implementation Ledger

**Document ID:** TI-LEDGER-001
**Version:** v1.0
**Status:** Active — Append-Only Event Log

---

## Purpose

Single source of truth for all Trade Intelligence milestone transitions, review dispositions, certification verdicts, and deviations. Append-only — never edit existing rows.

---

## Event Log

| # | Date | Milestone | Event | Reference |
|---|---|---|---|---|
| 1 | 2026-07-29 | M0 | Implementation Plan approved (frozen, two required changes applied) | `TRADE_INTELLIGENCE_IMPLEMENTATION_PLAN.md` |
| 2 | 2026-07-29 | M0 | Implementation complete — builder + schema + 13 tests passing | `reports/M0_IMPLEMENTATION_REPORT.md` |
| 3 | 2026-07-30 | M1 | TradeIntelligenceSink implemented — write-only, deltas-driven, idempotent | `core/execution/portfolio/trade_intelligence_sink.py` |
| 4 | 2026-07-30 | M1 | Sink integrated into CarryRebalancerHook + paper replay | `carry_rebalancer.py`, `ts_basis_daily_paper_replay.py` |
| 5 | 2026-07-30 | M1 | Bug fix: NOOP-held positions were not evaluated by exit policy (no delta generated) | `carry_rebalancer.py:_apply_exit_policy` |
| 6 | 2026-07-30 | M2 | Analytics report — TRAIN/HOLDOUT split, exit analysis, P&L dist, failure clusters | `run_m2_analytics.py`, `TRADE_INTELLIGENCE_M2_ANALYTICS.md` |
| 7 | 2026-07-30 | M3 | Option snapshot enrichment — schema + snapshot_options.py using select_book_options | `snapshot_options.py`, schema updated in builder + sink |
| 8 | 2026-08-26 | v2 | Operator reset — `trades` table cleared (10,530 rows deleted; TS Basis Daily research-only, windows burned). Old builder tests now skip on empty DB | `data/signal_engine/trade_intelligence/trade_intelligence.duckdb` |
| 9 | 2026-08-26 | v2 | Generic TradeRecorder built — strategy-agnostic, hooked at `ExecutionHandler._handle_broker_fill`; new `executed_trades` table (round-trip grain, entry fill_id PK); resolves M0 report §11 limitations. 14/14 tests green; execution suite 320 passed | `core/execution/portfolio/trade_recorder.py`, `core/execution/handler.py`, `reports/GENERIC_RECORDER_REPORT.md` |

> Note appended with event #8: re-running the M0 historical builder (`build_trade_intelligence.py`) unlinks the whole DB file and would destroy `executed_trades` live-capture data alongside its own table. Do not run it against this file while the recorder is active.
