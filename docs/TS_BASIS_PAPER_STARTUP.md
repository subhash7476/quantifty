# TS Basis (Monthly) PAPER Startup Guide

**Strategy:** TS Basis — per-name time-series basis z-score
(`z_ts = (basis − trailing_mean) / trailing_std`), positive sign: **long
high-basis, short low-basis**. The construct is **MONTHLY-rebalanced** on the
top/bottom quintile of the ~180-name SSF universe (pre-registration
`TS_BASIS_PHASE0_PRE_REGISTRATION.md`, SHA `07265b50…`; RFA declaration
`governance/rfa/declarations/ts_basis.py`, `cadence="monthly"`).

**Status (2026-07-31 reauthorization assessment):** SEALED read is
**de-authorized** (selection defect, not signal falsification) — the sealed
result survives a ~160,000× multiplicity penalty, but the authorizing gate did
not hold. The standing is **PAPER candidate**: only **forward PAPER months**
can resolve the de-authorization. The sealed window is **not re-opened**;
this runner is forward-only.

**Entry point:** `scripts/ts_basis_forward_runner.py` (forward, bhavcopy-driven).

---

## 1. Prerequisite checks

Run all of these before starting. **PAPER mode does not need Upstox
credentials** — no Upstox API calls, no token; fills are simulated by
`PaperBroker`.

### 1.1 Data freshness

| Store | Path | Freshness gate |
|---|---|---|
| Futures bhavcopy | `data/market_data/futures_bhavcopy.duckdb` | `MAX(trade_date)` = latest NSE trading day (`inst_type='FUTSTK'`) |
| TS Basis facts | `data/signal_engine/ts_basis/ts_facts.duckdb` | `MAX(formation_date)` = latest formation; must have `raw_z` + `basis_reverting` columns |
| TS Basis signals | `data/signal_engine/ts_basis/ts_signals.duckdb` | rebuilt incrementally by the runner's startup refresh |

```
python -c "import duckdb;c=duckdb.connect('data/market_data/futures_bhavcopy.duckdb',read_only=True);print(c.execute(\"SELECT MAX(trade_date) FROM futures_bhavcopy\").fetchone()[0])"
```

The runner refreshes signals + facts at startup and after each bhavcopy
advance (via the frozen `build_ts_signals.py` and `publish_facts.py` — the
signal construction is **not** re-derived).

### 1.2 Upstox connectivity

Not required for PAPER. No Upstox calls are made; the runner uses
`DailyBhavcopyProvider` over the local `futures_bhavcopy.duckdb`.

### 1.3 Instrument master currency

Advisory for PAPER (same as Carry): confirm `MAX(snapshot_date)` in
`data/instruments/nse_fo_instruments.duckdb` is the latest NSE session before
a clean run.

### 1.4 Facts schema + monthly cadence (added 2026-08-07)

Two things were repaired on this branch:

1. **Facts schema:** `CarryRebalancerHook._execute` hard-selects `raw_z` and
   `basis_reverting`. `ts_facts.duckdb` was migrated (copy-first baseline,
   `ALTER TABLE ... ADD COLUMN`) to carry both nullable columns.
2. **Cadence enforcement:** the on-disk `ts_facts.duckdb` was rebuilt
   **weekly** (2026-07-26, commit `03fc76a`), contradicting the frozen
   **monthly** construct. The runner now wraps the hook in a
   `MonthEndRebalanceGate` that fires only on the **last formation date of
   each calendar month** — 535 weekly formations collapse to 123 monthly
   rebalance points, matching the pre-registered monthly design. The gate
   re-reads the facts DB when `MAX(formation_date)` advances, so a newly
   published month-end is picked up by a running process.

### 1.5 Credentials / config (write no secrets here)

Same as Carry — `config/credentials.json` and `.env` hold Upstox/Telegram
credentials that are **not read in PAPER mode**; they exist for Flask /
scheduler entry points and any future LIVE authorization. See
`docs/CARRY_PAPER_STARTUP.md` §1.5.

---

## 2. Start command

```
python scripts/ts_basis_forward_runner.py            # forward PAPER, polls for new bhavcopy
python scripts/ts_basis_forward_runner.py --dry-run  # one pass then exit
```

The module imports cleanly (verified) and the gate wiring is verified against
the real facts DB: non-month-end weekly dates are refused, month-end dates
pass through to the rebalancer. The startup refresh rebuilds TS signals
non-incrementally by default, which is heavy — the first start takes longer
than subsequent ones. **No real orders are placed in either mode.**

## 3. Expected output

```
2026-08-07 ... ts_basis_forward INFO TS Basis forward: N symbols, run=ts-basis-forward-YYYY-MM-DD, start=<max facts date>
2026-08-07 ... ts_basis_forward INFO Refreshing TS Basis signals...
2026-08-07 ... ts_basis_forward INFO Refreshing TS Basis facts...
2026-08-07 ... ts_basis_forward INFO TS Basis forward PAPER started. Run ID: ts-basis-forward-YYYY-MM-DD
2026-08-07 ... carry_rebalancer INFO CarryRebalancer: executing <month-end date>
2026-08-07 ... ts_basis_forward INFO TS Basis rebalance: <date> 36L/36S fees=... slip=...
```

Between month-end formations the runner polls (60 s default) and logs nothing
new. Metrics are written to `data/signal_engine/carry/production.duckdb`
under a `ts-basis-forward-*` run id (reusing the `CarryMetricsDB` schema, with
`z_carry_neut` holding `z_ts` for compatibility).

## 4. PAPER mode behavior

- **No real orders.** Every fill is a `PaperBroker` simulation → `FillEvent`
  → `position_tracker.update_from_fill()`; no capital moves.
- **Monthly cadence, enforced.** The `MonthEndRebalanceGate` restricts
  rebalances to the last formation date of each calendar month. This matches
  the frozen construct; it does **not** re-open the sealed window.
- **Full-quintile book.** The runner uses the frozen equal-weight top/bottom
  20% construction (the previous runner's `max_positions_per_leg=5`
  divergence was removed to match the pre-reg §4 and the replay runner).
- **Forward-only.** Starts from the max facts date and moves forward. The
  sealed window (2023-01-01 → 2026-07-20) is historical data on disk; no
  research read is taken, no `run_sealed.py` is invoked, and no conclusion is
  drawn from it. `run_sealed.py` remains guarded against running.
- **Sign is fixed +1** (long high `z_ts`, short low `z_ts`). No sign-flip
  path exists.

---

## 5. PAPER moratorium note

Carry and **TS Basis (monthly)** are the **only active PAPER strategies** in
this repository. New research constructs are **frozen per the standing
moratorium**: any future construct must clear the RFA power-pre-check
(`governance/rfa/`) and a fresh pre-registration before any code, and no
screening battery promotes to capital. TS Basis Daily is explicitly
**research-only** (operator decision 2026-08-01) — no promotion path, sealed
window preserved. PAPER stays limited to the two validated monthly sleeves
until the operator explicitly authorizes otherwise.

## 6. Tests

The shared portfolio suite covers the rebalancer/metrics/runner paths used by
both PAPER strategies:

```
python -m pytest tests/portfolio -q      # 48 passing
```
