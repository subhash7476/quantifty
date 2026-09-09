# Runner Extraction Blueprint + Readiness Assessment (`F:\Nifty`)

**Date:** 2026-06-04  **Source:** `D:\BOT\root\core\runner.py` (543 lines), per `RUNNER_DEPENDENCY_ANALYSIS.md`.
**Scope:** extraction blueprint only. **No code written. No migration performed. No architecture redesigned.**
**Goal:** preserve platform infrastructure (4 capabilities) while permanently excluding strategy infrastructure.

---

## Duplication baseline (what already exists in `F:\Nifty`)

Verified by grep before planning:
- **`TelemetryPublisher` / `ZmqPublisher` / `TelemetryBridge`** — present and import-clean (the transport the telemetry loop needs).
- **`scripts/market_ingestor.py`** already runs its **own** heartbeat (`logs/market_ingestor_status.json` via `_update_heartbeat`) and `telemetry.publish_health(...)` — i.e. the **data-ingestion node** is already observable. This is a *precedent pattern*, **not** a duplicate of the trade-loop capabilities.
- **`ExecutionHandler.activate_kill_switch`** exists (handler.py:679) and is already called internally (STOP-file, risk). The **staleness→kill-switch** path is **not** present.
- **No `TradingRunner`-equivalent orchestrator, no trade-loop heartbeat (`heartbeat.json`), no trade-metrics telemetry, no staleness watchdog** exist in `F:\Nifty`. Providers expose `get_next_bar`, but nothing drives a deterministic trade loop.

**Net:** all four target capabilities are **absent** from the trading path in `F:\Nifty` today. Only the telemetry *transport* and a *separate* data-node heartbeat exist.

---

## 1. Deterministic loop scaffold

- **Functions/methods:** `run()` (the loop scaffold only), the cadence + `max_bars` guard + streaming/`sleep`/exhaustion handling; the data-driven `Clock.set_time(bar.timestamp)`; the bar-pull via `MarketDataProvider`; `RunnerConfig` (infra fields); `_get_stats()`, `stop()`, `is_running`.
- **Line ranges:** `run()` 113–169; clock-advance + bar-arrival hook 232–244 (extracted from inside `_process_symbol`); `_get_stats` 465–477; `stop` 479–481; `RunnerConfig` 31–41 (infra fields only); constants/state 49–94.
- **Required dependencies:** `Clock`, `MarketDataProvider` (`get_next_bar`, `is_data_available`), `ExecutionHandler` (loop invokes `process_signal`), `time`, `setup_logger`, `MarketHours` (for the periodic hooks it drives).
- **Unwanted dependencies:** `BaseStrategy`/`StrategyContext` (17), `AnalyticsProvider` (16), `save_signal` (24), `DatabaseManager` (22, via `_update_runner_state`), and the entire `_process_symbol` body (249–319), `_check_exit_conditions` (171–229), `_update_runner_state` (483–542).
- **Extraction difficulty: HIGH.** The scaffold and the strategy body live in the **same two methods** (`run` / `_process_symbol`). The infra (clock advance, bar arrival, periodic hooks, `process_signal` dispatch) is physically interleaved with strategy iteration. Extraction = separating "drive the loop" from "decide what to do per bar" behind a generic signal-source seam — a real refactor, not a copy.
- **Hidden risks:**
  - The loop currently calls `execution.process_signal` *and* contains `_check_exit_conditions` (TP/SL/time-stop exit policy). That exit-monitoring is **strategy/execution-policy**, not pure infra — deciding it stays out is a judgment call; the scaffold must not silently inherit it.
  - `time.sleep(0.5)` polling cadence and `is_data_available` semantics are provider-specific; behavior depends on the live provider's contract.
  - The "deterministic" guarantee is the **data-driven `Clock`**; if the bar-arrival hook is relocated incorrectly, live/backtest equivalence breaks silently.
- **Already duplicated in `F:\Nifty`?** **No.** No orchestrator/trade loop exists.

## 2. Heartbeat generation

- **Functions/methods:** `_write_heartbeat()`.
- **Line ranges:** 352–384; state `_last_heartbeat_time` (90), const `HEARTBEAT_INTERVAL_S` (52); reads `_bar_count`, `_data_healthy`.
- **Required dependencies:** stdlib `time, datetime, json, tempfile, os`; `MarketHours.is_market_open()`; `ExecutionHandler` (`.metrics.cash_balance`, `._trades_today`, `._kill_switched`).
- **Unwanted dependencies:** none.
- **Extraction difficulty: LOW.** Self-contained; atomic temp-file + `os.replace`. Lift-and-shift once it can read the execution snapshot.
- **Hidden risks:**
  - Reads **private** `ExecutionHandler` attrs (`_trades_today`, `_kill_switched`) and the `ExecutionMetrics` shape (defined inside `handler.py`). Coupled to execution internals — stable only as long as that surface is.
  - Writes a fixed path `logs/heartbeat.json`. **Naming convention coexists with** `market_ingestor_status.json` — two heartbeat files by design; ensure any external watchdog reads the right one (no collision, but two conventions).
  - `equity` is reported as `metrics.cash_balance` only (not cash + open-position MTM) — a known simplification to carry forward knowingly.
- **Already duplicated in `F:\Nifty`?** **Partially / precedent only.** `market_ingestor` writes a *different* status file for the *data* node. The *trade-loop* `heartbeat.json` is **not** present.

## 3. Data-staleness watchdog

- **Functions/methods:** `_check_data_staleness()` + the `_last_bar_timestamp` update / recovery (the bar-arrival hook).
- **Line ranges:** 331–350; input update 237–241; state `_last_bar_timestamp` / `_data_stale_alerted` / `_data_healthy` (85–87); const `DATA_STALE_THRESHOLD` (50).
- **Required dependencies:** `datetime`; `MarketHours.is_market_open()`; `alerter.critical()`; `ExecutionHandler.activate_kill_switch()`.
- **Unwanted dependencies:** none — but its **input** (`_last_bar_timestamp`) is currently set inside the strategy-coupled `_process_symbol`.
- **Extraction difficulty: MEDIUM.** The check is clean, but its trigger (the "a bar arrived" timestamp) must be **relocated onto the infra bar-pull path** (same relocation the deterministic scaffold needs). It also hard-depends on `activate_kill_switch`, so it cannot exist without an `ExecutionHandler`.
- **Hidden risks:**
  - Uses **wall-clock** `datetime.now()` for the staleness delta (operational), distinct from the deterministic trade `Clock`. Correct for live, but means the watchdog is meaningless in backtest — must be gated to live mode or it will false-trip.
  - It **acts** by tripping the global kill switch — a real risk-control side effect. Extracting it ports a control action, not just a sensor; mis-wiring the threshold or market-hours guard could halt live trading or fail to.
  - Depends on `MarketHours` correctly reflecting the venue calendar (NSE) — a wrong calendar mutes or mis-fires the alert.
- **Already duplicated in `F:\Nifty`?** **No.** No staleness/kill-switch-on-stale path exists.

## 4. Telemetry publishing

- **Functions/methods:** `_publish_telemetry()`; the telemetry calls inside `_log_signal` / `_log_trade`.
- **Line ranges:** 386–430; `_log_signal` 432–438 (telemetry line 437–438); `_log_trade` 462–463; state `_last_telemetry_time` / `_telemetry_interval_s` (93–94).
- **Required dependencies:** `time`; `TelemetryPublisher` (`publish_metrics/positions/health`); `ExecutionHandler` (`.metrics.{cash_balance,max_drawdown_pct,signals_received}`, `._trades_today`, `._kill_switched`); `PositionTracker.get_all_positions()`; `MarketHours.is_market_open()`.
- **Unwanted dependencies:** **one line** — `active_count = len(self.strategies) - len(self._disabled_strategies)` (398). Drop or pass an int.
- **Extraction difficulty: LOW–MEDIUM.** Clean after removing the one strategy-count line; reads only infra collaborators otherwise.
- **Hidden risks:**
  - Same private-attr / `ExecutionMetrics`-shape coupling to `ExecutionHandler` as heartbeat.
  - Depends on `PositionTracker.get_all_positions()` returning objects with `.quantity` / `.avg_entry_price` — shape coupling. `pnl_pct` was originally a hardcoded `0.0` placeholder; as of MM9.3-S2 (2026-06-28), the enriched path via `PortfolioView` computes real per-position `pnl_pct` from `(current_price - avg_price) / avg_price * 100`. The fallback path (no `PortfolioView` injected) retains the `0.0` placeholder.
  - Fire-and-forget by design (errors swallowed) — failures are silent; do not treat published telemetry as a guaranteed record.
- **Already duplicated in `F:\Nifty`?** **Transport yes, loop no.** `TelemetryPublisher`/bridge exist and `market_ingestor` already publishes *health*; the **trade-metrics/positions** publish loop is **not** present.

---

## Extraction summary

| # | Capability | Methods | Lines | Difficulty | Strategy deps | In `F:\Nifty`? |
|---|---|---|---|---|---|---|
| 1 | Deterministic loop scaffold | `run` (scaffold) + clock/bar hook | 113–169, 232–244 | **HIGH** | interleaved body | No |
| 2 | Heartbeat generation | `_write_heartbeat` | 352–384 | **LOW** | none | No (data-node precedent only) |
| 3 | Staleness watchdog | `_check_data_staleness` + bar hook | 331–350, 237–241 | **MEDIUM** | none (input relocation) | No |
| 4 | Telemetry publishing | `_publish_telemetry` (+`_log_*`) | 386–430 | **LOW–MED** | 1 line | Transport yes / loop no |

**Recommended extraction order (low-risk first):** 2 → 4 → 3 → 1. Heartbeat and telemetry are near lift-and-shift and validate the execution-snapshot coupling; staleness adds the bar-arrival hook + kill-switch wiring; the deterministic scaffold is last because it requires the signal-source seam and absorbs the relocated bar hook from #3.

---

## Readiness Assessment

> **"If these capabilities are extracted successfully, does `F:\Nifty` possess a complete platform core suitable for building an equity-futures + index-option-selling system?"**

### What `F:\Nifty` would then have (verified present)
- **Execution core:** `ExecutionHandler` (idempotency, risk gates, order creation, reconciliation, recovery), `PositionTracker`, `PnLTracker`, `MarginTracker`, `risk_manager`, kill switch.
- **Options stack:** `execution/options/selector.py`, full greeks (`black76_engine`, `greeks_calculator`, `greeks_model`, `portfolio_greeks`) and the **greek-limit gate** (`handler._check_greek_limits`, line 706).
- **Market data:** providers (live/historical/zmq/resampling), websocket ingestor, options provider, instrument DB, `MarketHours`.
- **Messaging/observability:** ZMQ transport + telemetry + bridge + (after extraction) heartbeat, staleness, trade telemetry.
- **UI:** Flask shell + options dashboard.
- **Loop:** (after extraction) a deterministic scaffold with a generic signal-source seam.

### Verdict: **YES — a complete platform *core* suitable for *building* such a system — with two execution-completeness caveats that are out of scope of these four extractions but block *live* option selling.**

The four extractions close the **orchestration + observability** gap. Combined with the already-present execution/options/greeks/data tiers, `F:\Nifty` would hold the full neutral infrastructure on which an equity-futures + index-option-selling strategy can be built. By design it would still lack the **strategy/signal layer** (intended — the user supplies it via the loop's signal seam).

**Caveats to flag (not part of capabilities 1–4, but required before *live* deployment):**
1. **Broker product model is intraday-only.** `upstox_adapter.place_order` hardcodes `product: "I"` (INTRADAY). Index-option **selling** (overnight/carry) and **futures** positions typically require `NRML` (delivery/carry) product. The order path must gain product/segment awareness for F&O before live carry trades — paper/intraday works as-is.
2. **Margin model is a flat rate.** `MarginTracker` uses `margin_rate=0.2` (20%), not SPAN/exposure margining. Adequate for paper simulation; **insufficient for real option-selling margin** (short-option SPAN can dwarf a flat 20%).

### One-line answer
**Yes for building (the platform core is complete and neutral); conditional for going live** — the deterministic loop + heartbeat + staleness + telemetry extractions give you a runnable, observable, deterministic core, but the broker product model (intraday-only) and the margin model (flat-rate) must be extended before real index-option selling or futures carry.
