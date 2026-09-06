# TS Basis — Strategy Pipeline Summary

**Branch:** `carry/cadence-decay` (in `F:\Nifty-carry-cadence`)
**Generated:** 2026-07-23
**Status:** Strategy pipeline built, pre-registration DRAFT (unfrozen), SEALED window unread

---

## 1. Strategy Overview

**Signal:** `z_ts = (basis_now − trailing_mean) / trailing_std` — per-name time-series
z-score of the annualized futures basis against its own 504-day trailing distribution.

**Direction:** high z_ts (unusually wide basis) → LONG, low z_ts → SHORT.
The basis persists — unusually wide predicts continued outperformance within the month.

**Construction:** single-step — no dividend adjustment, cross-sectional demeaning,
or beta/sector neutralization. Reads `raw_ann_basis` from the existing basis panel,
computes trailing mean and std per underlying, stores z_ts in `ts_signals.duckdb`.

---

## 2. Results vs Cross-Sectional Carry

| | TS Basis | Carry (monthly) | Delta |
|---|---|---|---|
| **TRAIN net** | **+18.4%** | +12.8% | **+554 bp** |
| **HOLDOUT net** | **+14.8%** | +7.0% | **+784 bp** |
| TRAIN IC | +0.070 (t=4.55) | +0.041 | 1.7x |
| HOLDOUT IC | +0.043 (t=2.19) | — | — |
| Max drawdown (TRAIN) | -11.1% | -6.4% | Deeper |
| Max drawdown (HOLDOUT) | -3.2% | -5.2% | Shallower |
| Sharpe (TRAIN) | 1.62 | 1.61 | — |
| Fee drag | 168 bp | 154 bp | — |
| Turnover | 1.53 | 1.44 | — |
| Construction steps | 1 (z-score) | 5 (div, cs, win, beta, sector) | Simpler |

---

## 3. Pipeline Structure

| Artifact | Path | Status |
|---|---|---|
| Pre-registration | `docs/reports/TS_BASIS_PHASE0_PRE_REGISTRATION.md` | DRAFT, unfrozen |
| RFA declaration | `governance/rfa/declarations/ts_basis.py` | Written |
| Signal construction | `scripts/signal_engine/ts_basis/build_ts_signals.py` | Built (17,496 signals, 113 formations) |
| Net-spread gate | `scripts/signal_engine/ts_basis/run_net_spread.py` | **PASS** |
| Net-spread report | `docs/reports/TS_BASIS_NET_SPREAD_REPORT.md` | Generated |
| Net-spread snapshot | `docs/reports/TS_BASIS_NET_SPREAD_SNAPSHOT.json` | Generated |
| Drawdown analysis | `scripts/signal_engine/ts_basis/run_drawdown.py` | Complete |
| Drawdown report | `docs/reports/TS_BASIS_DRAWDOWN_REPORT.md` | Generated |
| Capacity analysis | `scripts/signal_engine/ts_basis/run_capacity.py` | Complete |
| Capacity report | `docs/reports/TS_BASIS_CAPACITY_REPORT.md` | Generated |
| Sealed read protocol | `docs/reports/TS_BASIS_SEALED_READ_PROTOCOL.md` | DRAFT, unfrozen |

---

## 4. Pre-Registration Key Points

**Hypothesis:** cross-sectional rank of `z_ts` predicts cross-sectional rank of forward
1-month returns. Sign = positive (high z → long). Declared and unflippable.

**Prior exposure:** TRAIN window was seen for cross-sectional carry sign discovery.
TS Basis reads from the same underlying basis data. TRAIN carries ZERO confirmatory
weight for TS Basis. Confirmation comes from HOLDOUT (2021–2022, ~24 formations) alone.

**Multiplicity:** m ≥ 2 (carry sign discovery + TS Basis sign discovery, both on TRAIN).
HOLDOUT significance at Bonferroni α = 0.025, one-sided.

**Acceptance:** HOLDOUT IC must be positive-signed and significant at α = 0.025
AND net > 0 under §5 fees. If both pass, SEALED read authorized.

---

## 5. Gate Checklist

| Gate | Status | Notes |
|---|---|---|
| TRAIN net > 0 | **PASS** | +18.4% |
| HOLDOUT net > 0 | **PASS** | +14.8% |
| HOLDOUT IC sign | **PASS** | +0.043 (positive as declared) |
| TRAIN net-spread gate | **PASS** | — |
| HOLDOUT net-spread gate | **PASS** | — |
| Pre-reg frozen (SHA-256) | **PENDING** | Operator action |
| RFA power pre-check | **PENDING** | Declaration written, gate unrun |
| SEALED read | **PENDING** | Awaiting freeze + operator authorization |

---

## 6. What's Not Done (requires operator)

- **Pre-registration freeze** — SHA-256 lock on `TS_BASIS_PHASE0_PRE_REGISTRATION.md`
- **RFA gate run** — `scripts/rfa/gate.py` with the `ts_basis` declaration
- **SEALED read** — one-shot 2023-01-01 → 2026-07-20, governed by `TS_BASIS_SEALED_READ_PROTOCOL.md`
- **Weekly cadence check** — cadence decay analysis for TS Basis (deferred: monthly already proven)
- **Composite evaluation** — TS Basis + Carry combined (if both independently validated)

---

## 7. Cadence-Decay Findings (background)

The weekly cadence analysis on `carry/cadence-decay` found:

| Finding | Result |
|---|---|
| Quintile persistence (1w) | 35% long / 43% short |
| Quintile persistence (4w) | 29% long / 31% short |
| Weekly vs monthly net | Monthly beats weekly by 1,265 bp |
| IC stability | IC stable +0.055–0.058 across 1w/2w/3w/1m |
| Spread accumulation | 69% by week 1, linear through month-end |

**Conclusion:** monthly rebalancing remains correct. Weekly rotation produces fresher
signals but the ~3x fee drag consumes the edge. These findings apply to cross-sectional
carry; TS Basis at weekly cadence has not been run.

---

## 8. Files Created (this worktree)

```
F:\Nifty-carry-cadence\
├── docs/reports/
│   ├── CARRY_CADENCE_DECAY_REPORT.md
│   ├── CARRY_PERSISTENCE_REPORT.md
│   ├── CARRY_WEEKLY_VS_MONTHLY_REPORT.md
│   ├── TS_BASIS_CAPACITY_REPORT.md
│   ├── TS_BASIS_DRAWDOWN_REPORT.md
│   ├── TS_BASIS_NET_SPREAD_REPORT.md
│   ├── TS_BASIS_NET_SPREAD_SNAPSHOT.json
│   ├── TS_BASIS_PHASE0_PRE_REGISTRATION.md
│   └── TS_BASIS_SEALED_READ_PROTOCOL.md
├── governance/rfa/declarations/
│   └── ts_basis.py
├── scripts/signal_engine/
│   ├── carry/
│   │   ├── cadence_decay.py
│   │   ├── persistence.py
│   │   ├── ts_basis_reversal.py
│   │   ├── weekly_vs_monthly.py
│   │   ├── build_carry.py          (modified: weekly formation grid)
│   │   └── neutralize.py           (modified: weekly_signals.duckdb)
│   └── ts_basis/
│       ├── build_ts_signals.py
│       ├── run_net_spread.py
│       ├── run_drawdown.py
│       └── run_capacity.py
```
