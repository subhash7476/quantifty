# Trade Intelligence Observatory — Implementation Plan

**Document:** Trade Intelligence — Implementation Roadmap
**Date:** 2026-07-29
**Status:** Accepted — Implementation Baseline (v1.0)
**Review History:** Proposed → Approved with two required changes → Frozen M0

---

## 0. Preamble

This plan implements the Trade Intelligence Observatory as a standalone research database. It introduces no changes to signal construction, facts publishing, recovery filtering, exit policy, or the rebalancer. It reads from existing data stores and writes to a new `trade_intelligence.duckdb`.

Principle: **Trade Intelligence is a research database, not an execution database.** Its only purpose is answering "why did this trade work/fail?" across thousands of trades.

---

## 1. Database Design

**Location:** `data/signal_engine/trade_intelligence/trade_intelligence.duckdb`

**Table — `trades`:**

```sql
CREATE TABLE IF NOT EXISTS trades (
    -- Identity (immutable)
    trade_id           VARCHAR PRIMARY KEY,      -- {underlying}_{entry_date}_{side}
    underlying         VARCHAR NOT NULL,
    side               VARCHAR NOT NULL,          -- 'LONG' | 'SHORT'
    entry_date         DATE NOT NULL,
    strategy_name      VARCHAR NOT NULL,          -- 'ts_basis_daily'
    strategy_version   VARCHAR NOT NULL,          -- git commit hash

    -- Signal snapshot (immutable — never updated after INSERT)
    z_ts               DOUBLE,
    raw_z              DOUBLE,
    quintile           TINYINT,
    rank_in_date       INTEGER,                   -- rank by |z_ts|, eligible names only
    basis_reverting    BOOLEAN,
    sector             VARCHAR,

    -- Regime context (immutable)
    vix_at_entry       DOUBLE,
    nifty_20d_at_entry DOUBLE,

    -- Outcome (NULL until exit — populated by UPDATE)
    exit_date          DATE,
    days_held          INTEGER,
    exit_reason        VARCHAR,                   -- EXIT_SIGNAL|EXIT_TP|EXIT_SL|EXIT_RECOVERY
    stock_return       DOUBLE                     -- signed for position direction
);

CREATE INDEX IF NOT EXISTS idx_trades_entry ON trades (entry_date);
CREATE INDEX IF NOT EXISTS idx_trades_underlying ON trades (underlying);
CREATE INDEX IF NOT EXISTS idx_trades_exit ON trades (exit_date);
```

**Why one table:** Every analysis joins signal + lifecycle + outcome. Signal columns never updated after INSERT. Outcome columns transition NULL → populated on exit.

**Trade identification:** `{underlying}_{entry_date}_{side}`. Natural key, collision-proof per rebalancer book constraints.

**Rank definition (frozen):** `rank_in_date` = position when sorting by `|z_ts|` descending within `eligible=TRUE` names on `formation_date`. `rank=1` = strongest signal that day.

**Exit reason enum (frozen):** `EXIT_SIGNAL` (dropped from quintile), `EXIT_TP` (take-profit fired), `EXIT_SL` (stop-loss fired), `EXIT_RECOVERY` (basis_reverting triggered exit).

---

## 2. Component Architecture

```
ts_signals.duckdb ──┐
ts_facts.duckdb ────┤
1d index store ─────┼──→ build_trade_intelligence.py ──→ trade_intelligence.duckdb
sector CSV ─────────┘
```

---

## 3. Historical Builder

**File:** `scripts/signal_engine/ts_basis_daily/build_trade_intelligence.py`

**Algorithm:**

1. Load eligible facts from `ts_facts.duckdb` for TRAIN + HOLDOUT windows
2. Load `fwd_ret_1m` from `ts_signals.duckdb` for all formation dates
3. Load index regime (VIX, Nifty) from 1d index store
4. Load sector mapping from `sector_classification.csv`
5. Sort facts by (formation_date, z_ts)
6. For each formation_date, compute `rank_in_date` by `|z_ts|` descending
7. Simulate portfolio delta logic (same as `rebalance_book()`):
   - Select top-N by z_ts for longs, bottom-N for shorts
   - Apply 0.25σ band suppression
   - Track held positions across dates
8. On each formation_date, for each held position:
   - **New position:** INSERT trade row with signal snapshot + regime context
   - **Continued position:** nothing (held, still in target)
   - **CLOSE position:** UPDATE trade row with exit_date, days_held, stock_return, exit_reason
   - **FLIP position:** UPDATE old trade (CLOSE) + INSERT new trade (OPEN)
9. Stock return: compound `fwd_ret_1m` from entry_date through exit_date
   - LONG: product of (1 + daily_ret) - 1
   - SHORT: product of (1 - daily_ret) - 1

**Portfolio parameters (frozen):**
```
MAX_POSITIONS = 5
QUINTILE_FRAC = 0.20
ADV_CAP_FRAC = 0.10
BAND_SIGMA = 0.25
```

---

## 4. Tests

**File:** `tests/trade_intelligence/test_builder.py`

| Test | What |
|---|---|
| `test_trade_insert_on_entry` | New position creates row with all signal columns populated |
| `test_trade_update_on_exit` | CLOSE populates exit_date, days_held, stock_return |
| `test_signal_snapshot_immutable` | Signal columns unchanged after UPDATE |
| `test_cumulative_return_long` | LONG return = compounding (1+ret) |
| `test_cumulative_return_short` | SHORT return = compounding (1-ret) |
| `test_flip_creates_two_trades` | FLIP = one CLOSE + one OPEN |
| `test_regime_context_populated` | vix_at_entry and nifty_20d populated on INSERT |
| `test_sector_mapped` | sector from CSV on INSERT |
| `test_empty_outcome_on_open` | Open trades have NULL outcome columns |
| `test_rank_computed` | rank=1 for highest \|z_ts\| in formation |

---

## 5. Files

| File | Purpose |
|---|---|
| `data/signal_engine/trade_intelligence/` | DB directory |
| `scripts/signal_engine/ts_basis_daily/build_trade_intelligence.py` | Historical builder |
| `tests/trade_intelligence/__init__.py` | Test package |
| `tests/trade_intelligence/test_builder.py` | Builder tests |
| `docs/implementation/trade_intelligence/README.md` | Program overview |
| `docs/implementation/trade_intelligence/TRADE_INTELLIGENCE_IMPLEMENTATION_PLAN.md` | This document |
| `docs/implementation/trade_intelligence/IMPLEMENTATION_LEDGER.md` | Event log |

---

## 6. Milestones

| ID | Milestone | Scope |
|---|---|---|
| **M0** | Trade Intelligence Foundation | Schema + builder + tests + report |
| M1 | TradeIntelligenceSink | Live capture via rebalancer callback |
| M2 | Analytics | Win-rate/expectancy by feature, exit analysis |
| M3 | Option Snapshots | DTE, premium, IV, OI at entry |
| M4 | Option Lifecycle | Daily MTM (only if M2 justifies) |

M0 only is authorized. M1–M4 are placeholders.

---

## 7. Verification Gates (M0)

- [ ] Builder runs without error on TRAIN + HOLDOUT
- [ ] All 10 tests pass
- [ ] Trade count ≈ expected (~formations × avg positions per leg × 2 / avg days held)
- [ ] Mean stock_return ≈ baseline mean signed return
- [ ] Winner ratio ≈ baseline hit rate
- [ ] No NULLs in signal columns for INSERT-ed rows
- [ ] No NULLs in outcome columns for UPDATE-d rows (closed trades)
- [ ] No exit_date < entry_date

---

## 8. Non-Goals

- Options tracking (M3)
- Trade event log for debugging (after analytics prove useful)
- Modifying signal construction, facts publishing, or the rebalancer
- Forward runner integration (M1)
- Real-time MTM — uses `fwd_ret_1m` from signals DB

---

**End of Document**
