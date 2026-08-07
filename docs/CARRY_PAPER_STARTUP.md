# Carry PAPER Startup Guide

**Strategy:** Carry (residual futures basis, positive sign) — the platform's
first production-validated strategy (TRAIN → HOLDOUT → SEALED all PASS;
SEALED net +20.52%). This guide covers running it in **PAPER mode only** —
all fills are simulated by `PaperBroker`, no real orders are ever placed.

**Entry point:** `scripts/carry_forward_runner.py` (forward, bhavcopy-driven).
`scripts/carry_paper_runner.py` exists but drives a 1m-candle provider that
cannot resolve the strategy's plain-underlying symbols — use the forward
runner unless that provider path is separately repaired.

---

## 1. Prerequisite checks

Run all of these before starting. **PAPER mode does not need Upstox
credentials** — `fno_runner` only refuses a missing/expired token for
`ExecutionMode.LIVE`. The checks below are data-freshness and wiring gates,
not login gates.

### 1.1 Data freshness

| Store | Path | Freshness gate |
|---|---|---|
| Futures bhavcopy | `data/market_data/futures_bhavcopy.duckdb` | `MAX(trade_date)` = latest NSE trading day (`inst_type='FUTSTK'`) |
| Carry facts | `data/signal_engine/carry/facts.duckdb` | `MAX(formation_date)` = last completed month-end; must have `raw_z` + `basis_reverting` columns |
| Carry signals | `data/signal_engine/carry/signals.duckdb` | used only by `carry_refresh_facts.py` forward append |

```
python -c "import duckdb;c=duckdb.connect('data/market_data/futures_bhavcopy.duckdb',read_only=True);print(c.execute(\"SELECT MAX(trade_date) FROM futures_bhavcopy\").fetchone()[0])"
```

Facts must be current through the last completed month-end before a rebalance
can fire. If stale, run the facts refresh:

```
python scripts/carry_refresh_facts.py     # exit 0 up-to-date · 1 refreshed · 2 stale (needs bhavcopy)
```

### 1.2 Upstox connectivity

Not required for PAPER. The runner constructs `PaperBroker` — no Upstox API
calls, no token. Connectivity to Upstox is only a LIVE-mode concern.

### 1.3 Instrument master currency

The instrument master (`data/instruments/nse_fo_instruments.duckdb`) is read
by the master-readiness gate. For PAPER the gate is advisory; for a clean run
confirm `MAX(snapshot_date)` is the latest NSE session:

```
python -c "import duckdb;c=duckdb.connect('data/instruments/nse_fo_instruments.duckdb',read_only=True);print(c.execute('SELECT MAX(snapshot_date) FROM instruments').fetchone()[0])"
```

### 1.4 Facts schema (added 2026-08-07)

`CarryRebalancerHook._execute` hard-selects `raw_z` and `basis_reverting`
from `carry_facts`. The on-disk facts DB was migrated (copy-first baseline,
then `ALTER TABLE ... ADD COLUMN`, matching main `1593cc7`) to carry both
nullable columns. Verify:

```
python -c "import duckdb;c=duckdb.connect('data/signal_engine/carry/facts.duckdb',read_only=True);print([r[0] for r in c.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='carry_facts'\").fetchall()]);c.close()"
```

### 1.5 Credentials / config (write no secrets here)

- `config/credentials.json` — Upstox API key/secret/access token. **PAPER does
  not read it.** Required only for `ExecutionMode.LIVE`.
- `.env` — `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`, `UPSTOX_ACCESS_TOKEN`,
  Telegram token/chat id, Flask `SECRET_KEY`. Loaded by Flask/scheduler
  entry points, not by the PAPER runner.
- `.env.example` and `config/credentials.template.json` are the templates;
  fill from the operator's Upstox dashboard when LIVE is ever authorized.

---

## 2. Start command

```
python scripts/carry_forward_runner.py            # forward PAPER, polls for new bhavcopy
python scripts/carry_forward_runner.py --dry-run  # one pass then exit (dry-run check)
```

The dry-run was verified on this branch: it executed the 2026-07-31
formation end-to-end — **41 longs / 41 shorts**, determinism hash
`358161d05cf2f059` — matching the value recorded on `main` for the same
formation. No real orders are placed in either mode.

## 3. Expected output

```
2026-08-07 14:02:53,845 carry_forward INFO Carry forward: 360 symbols, run=forward-YYYY-MM-DD, start=2026-07-31
2026-08-07 14:02:56,592 carry_forward INFO Forward PAPER started. Run ID: forward-YYYY-MM-DD
...
carry_rebalancer INFO CarryRebalancer: executing 2026-07-31
carry_rebalancer INFO Rebalance done: 0 exits, 82 entries, ~Rs 3270 fees + ~Rs 5000 slippage
carry_forward  INFO Carry rebalance: 2026-07-31 41L/41S fees=3270 slip=5000
carry_forward  INFO Forward PAPER stopped. Hash: 358161d05cf2f059
```

Between formations the runner polls (default 60 s) and logs nothing new. On a
formation date it computes target book + deltas, places simulated fills on the
position tracker, and writes per-formation metrics (fees/slippage/turnover/
concentration/margin) to `data/signal_engine/carry/production.duckdb` via the
`CarryMetricsDB` schema (4 tables: `run_metadata`, `rebalance_summary`,
`rebalance_positions`, `equity_curve`).

## 4. PAPER mode behavior

- **No real orders.** Every fill goes through `PaperBroker` → `FillEvent` →
  `position_tracker.update_from_fill()`; equity is simulated, no capital moves.
- **Fixed research-identical gross** of ₹1 Cr (`paper_gross_exposure_policy`),
  not P&L-reactive. LIVE sizing is deliberately unimplemented (bridge §8
  no-re-optimization guardrail).
- **Monthly cadence.** Rebalances only on `carry_facts` formation dates
  (month-end, ~126 formations). Between dates the strategy emits nothing.
- **Run ID** is date-stamped; each formation's structural metrics are
  determinism-hashable for replay verification.
- **Staleness guard:** `carry_refresh_facts.py` fails loudly (exit 2) if the
  bhavcopy hasn't advanced past the last formation — no silent skips.

---

## 5. PAPER moratorium note

Carry and **TS Basis (monthly)** are the **only active PAPER strategies** in
this repository. New research constructs are **frozen per the standing
moratorium**: any future construct must clear the RFA power-pre-check
(`governance/rfa/`) and a fresh pre-registration before any code, and no
screening battery promotes to capital. PAPER stays limited to these two
validated sleeves until the operator explicitly authorizes otherwise.

## 6. Tests

The portfolio suite covers the rebalancer, metrics, metrics-DB, and runner
paths:

```
python -m pytest tests/portfolio -q      # 48 passing
```
