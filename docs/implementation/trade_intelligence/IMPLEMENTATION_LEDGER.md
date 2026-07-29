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
