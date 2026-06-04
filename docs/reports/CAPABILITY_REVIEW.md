# Architectural Review — Surviving Platform Capabilities (`F:\Nifty`)

**Date:** 2026-06-04  **Basis:** direct source inspection of `D:\BOT\root` (authoritative full versions) cross-checked against the migrated `F:\Nifty` tree. **No strategy modules inspected.** No new architecture proposed; no replacement code.

**Objective:** decide whether these five are foundational platform infrastructure that must be preserved before redesigning `F:\Nifty`.

---

## System map (how the five relate)

```
                         ┌──────────────────────────────────────────────┐
                         │              DETERMINISTIC RUNNER (5)          │
                         │              core/runner.py  [NOT migrated]    │
                         │   single-threaded loop: data → signal → exec   │
                         │   hosts heartbeat(3) + telemetry(4) wiring     │
                         └───────┬───────────────┬───────────────┬───────┘
              bars/signals       │               │ each tick      │ each tick
                                 ▼               ▼                ▼
   ┌───────────────────────────────────┐  ┌──────────────┐  ┌──────────────────────┐
   │      EXECUTIONHANDLER (2)          │  │ HEARTBEAT (3)│  │  ZMQ TELEMETRY (4)    │
   │  core/execution/handler.py [KEEP] │  │ file beacon +│  │ zmq_handler/telemetry │
   │  process_signal() OMS/EMS core    │  │ staleness →  │  │  → telemetry_bridge   │
   │  risk · idempotency · trackers ·  │◄─┤ kill switch  │  │  → SSE → dashboard     │
   │  reconciliation · recovery        │  │ (reads exec) │  └──────────────────────┘
   │            │                      │  └──────────────┘
   │            │ optional hook        │
   │            ▼                      │
   │   TRADE LEARNING PROTOCOL (1)     │
   │   capture.py: CaptureEngine +     │
   │   TLPLogger → tlp_trade_log       │
   └───────────────────────────────────┘
```

Two of the five (heartbeat watchdog #3, runner #5) **are not yet in `F:\Nifty`** — they live in the un-migrated, strategy-coupled `core/runner.py`. The other three are present and import-clean.

---

## 1. Trade Learning Protocol — `core/analytics/capture.py` (+ `metrics_service.py`, `events.TradeStructuralContext`)

### A. Purpose
Records *why* a trade was taken (structural truth at signal time) and *how it behaved* (outcome at close), so edge can be attributed and leakage diagnosed. Implements the platform's "Audit-First" principle. Sits **beside ExecutionHandler** (entry-time capture) and **at strategy trade-close** (outcome log), writing to persistence.

It is two distinct halves:
- `CaptureEngine` — entry-time structural snapshot (handler-side).
- `TLPLogger` — trade-close outcome record (strategy-side).

**Depends on:** `DatabaseManager`, `StructuralMetricsService` (metrics_service), `events.TradeStructuralContext`, analytics tables `regime_insights` + `daily_structural_metrics` (signals.db), `data/nifty-50-stock-list.csv`, pandas.
**Depended on by:** `handler.py` (optional `capture_engine`, line 484–486); `scripts/unified_live_runner.py` (constructs `CaptureEngine`); `scripts/unified_runner.py` (`init_tlp_logger`); `core/strategies/nifty_shield_strategy.py` (`TLPLogger.record()` — the only live caller of the logger half).

### B. Code analysis
- **Entry points:** `CaptureEngine.capture_context(symbol, ts, signal_rank, signal_percentile, sl_distance, risk_r, signal_score)` → `TradeStructuralContext`; `TLPLogger.record(...)`; module singletons `init_tlp_logger()` / `get_tlp_logger()`.
- **Data flow:** signal → `handler.process_signal` → (if `capture_engine`) `capture_context()` reads `regime_insights` + `daily_structural_metrics` and `metrics.get_percentiles(...)` → builds `TradeStructuralContext` → attached to the trade. At close → strategy → `TLPLogger.record()` → `INSERT tlp_trade_log` (trading.db). Table is self-created via `TLP_TRADE_LOG_SCHEMA`.
- **Notable implementation reality:** `CaptureEngine` is **partly stubbed** — `_calculate_breadth()` returns a constant `0.5`, `_get_index_trend()` returns `"NEUTRAL"`; `model_version`/`universe_version` are hardcoded constants. So the "structural truth" is currently incomplete by design (V1 core).
- **External deps:** DuckDB (via DatabaseManager), pandas, a CSV on disk.

### C. Operational importance
- **Live trading: not required.** The handler hook is guarded (`if self.capture_engine and signal.signal_type != EXIT`) and `capture_engine` defaults to `None`.
- **Observability: post-trade only** — it is the analytics-of-record (TCA), not live monitoring.
- **Reconciliation / risk: no role.**

### D. Removal impact
- Runtime: **nothing breaks** — handler runs with the hook disabled; `TLPLogger`'s only live caller is a (excluded) strategy.
- Lost: permanent, **silent, unrecoverable** loss of per-trade structural attribution and outcome metrics (MAE/MFE/exit-efficiency/hold). You cannot backfill state you never captured. This is the platform's learning/feedback asset.

### E. Recommendation — **KEEP protocol + `TLPLogger`; REFACTOR `CaptureEngine`**
`TLPLogger` is clean, self-contained, exception-safe infra — keep. `CaptureEngine` is half-stubbed and hard-coupled to analytics tables/`metrics_service` that do not exist in an infra-only repo — its *inputs* must be decoupled from those specific feature sources before it is useful here. The capability is strategically important; the current entry-time implementation is not yet load-bearing.

---

## 2. ExecutionHandler — `core/execution/handler.py`

### A. Purpose
The OMS/EMS core: converts an abstract `SignalEvent` into a risk-checked, deduplicated, tracked broker order, and reconstructs live state after a crash. **Center of the system** — every order passes through it.

**Depends on:** `core.events`, `execution.rules` (authority/idempotency/risk-clearance enforcers), `order_models`/`order_lifecycle`/`order_tracker`/`order_factory`, `risk_manager`, `position_tracker`, `pnl_tracker`, `margin_tracker`, `groups/*`, `reconciliation`, `persistence/*` (execution_store, order/fill/position repositories), `clock`, `brokers.broker_base`, `alerter`, `DatabaseManager`, `instruments.instrument_parser`, `risk.greeks.portfolio_greeks`, `analytics.capture`, `database.writers`.
**Depended on by:** the runner (`TradingRunner.execution`), all live/backtest entry scripts, the options selector path, heartbeat (#3 reads its metrics/kill-switch).

### B. Code analysis
- **Entry point:** `process_signal(signal, current_price) -> Optional[NormalizedOrder]`. Plus startup recovery (orders + idempotency registry restore) and fill handling.
- **Pipeline (grounded, `process_signal`):** Phase 0 **authority enforcement** (`enforce_execution_authority` — single-signal reentrancy guard, `_processing_signal`) → **idempotency enforcement** (`enforce_signal_idempotency` against `_seen_signals`, locked immediately) → **mandatory risk enforcement** (`sl_distance`/`risk_r` required for non-EXIT; `enforce_risk_clearance` raises on violation; MockBroker gets conservative defaults) → risk-limit check → deterministic order creation → **TLP capture hook** → broker submit → `FillEvent` → position/pnl/margin trackers + reconciliation → persistence + `metrics.json`.
- **Data flow:** SignalEvent → risk/idempotency gates → `NormalizedOrder` → broker → `FillEvent` → trackers → DuckDB + metrics file.
- **External deps:** DuckDB, broker adapter (REST/WS), filesystem (`metrics_path`).

### C. Operational importance
- **Live trading: required — this is the trading core.**
- **Reconciliation: required** (`ReconciliationEngine`).
- **Risk control: required** (`risk_manager`, kill switch `_kill_switched`, greek limits, mandatory SL/risk-R enforcement).
- **Observability:** emits `ExecutionMetrics` / `get_execution_stats()` consumed by telemetry (#4) and heartbeat (#3).

### D. Removal impact
Total. No sizing, no risk gate, no idempotency (double-fills on signal replay), no position/PnL truth, no reconciliation, no crash recovery. **The platform cannot trade.** Nothing degrades gracefully.

### E. Recommendation — **KEEP** (untouched)
Foundational and irreplaceable. This is the file Codex wrongly dropped; it is now restored and import-clean in `F:\Nifty`.

---

## 3. Heartbeat monitoring — `core/execution/health_monitor.py` **and** the runner's file beacon

### A. Purpose
Answer "is the process alive and is data still flowing?" There are **two different mechanisms** under this name:
- `HealthMonitor` (`health_monitor.py`) — trivial in-process counter (uptime, error count → healthy/degraded). **Used only by `app_facade/ops_facade.py`** (one import) to populate the ops dashboard.
- The **real watchdog** in `runner.py`: `_write_heartbeat()` (atomic write of `logs/heartbeat.json` every 10 s for an **external watchdog**) and `_check_data_staleness()` (5-min no-bar threshold → `alerter.critical` + **`execution.activate_kill_switch()`**).

**Depends on:** ExecutionHandler (`metrics.cash_balance`, `_trades_today`, `_kill_switched`, `activate_kill_switch`), `MarketHours`, `alerter`, filesystem.
**Depended on by:** `ops_facade` (HealthMonitor); an external process/watchdog reads `heartbeat.json`.

### B. Code analysis
- **Entry points:** `HealthMonitor.get_status()` / `record_error()`; `runner._write_heartbeat()` / `_check_data_staleness()` invoked once per loop iteration.
- **Data flow:** runner loop → writes `heartbeat.json` (timestamp, market_open, data_healthy, equity, bars_processed, trades_today, kill_switched) via temp-file + `os.replace` (atomic) → and compares `now - _last_bar_timestamp` to `DATA_STALE_THRESHOLD`; if exceeded during market hours → critical alert + soft kill switch.
- **External deps:** filesystem (`logs/`), `MarketHours`.

### C. Operational importance
- **Reliable live trading: yes** — the staleness→kill-switch path is a genuine safety mechanism (prevents trading on a frozen feed). The `HealthMonitor` stub does **not** provide this.
- **Observability:** `heartbeat.json` is the external liveness signal; `HealthMonitor` feeds the ops tile.
- **Risk control: yes (indirect)** — it trips the kill switch.

### D. Removal impact
- Remove the watchdog: bot still trades, but **loses dead-feed detection** — worst case it acts on stale prices or appears "up" while idle. No crash, but a real operational hazard for unattended live.
- Remove `HealthMonitor`: the ops dashboard health tile breaks (ops_facade import error) — cosmetic.

### E. Recommendation — **KEEP capability; REFACTOR its home**
The meaningful watchdog (`_write_heartbeat` / `_check_data_staleness`) is essential for live but currently **trapped inside the strategy-coupled, un-migrated `runner.py`** and bound to the ExecutionHandler API. It must be **ported out of the runner into infra**, not deleted. `health_monitor.py` is too thin to rely on as the liveness layer. **Note: neither mechanism exists in `F:\Nifty` today except the `HealthMonitor` stub** — the real watchdog still has to be brought over.

---

## 4. ZMQ telemetry architecture — `core/messaging/zmq_handler.py`, `telemetry.py`, `flask_app/telemetry_bridge.py`

### A. Purpose
A decoupled pub/sub bus serving **two roles**: (a) fire-and-forget live telemetry to the dashboard, and (b) general inter-process transport (market data, options push). Cross-process messaging fabric.

**Layering:** `zmq_handler` (primitive: `ZmqPublisher`/`ZmqSubscriber` + versioned envelope) → `TelemetryPublisher` (non-invasive, exception-safe) → `TelemetryBridge` (SUB → SSE for Flask).
**Depends on:** `pyzmq` only — `zmq_handler` has **zero `core` imports** (clean primitive).
**Depended on by (zmq_handler):** `database/ingestors/db_tick_aggregator.py`, `database/providers/zmq_market.py`, `messaging/options_publisher.py`, `flask_app/telemetry_bridge.py`, `flask_app/__init__.py`. **Depended on by (TelemetryPublisher):** `runner.py`, `scripts/strategy_runner_node.py`, `scripts/unified_live_runner.py`, `scripts/market_ingestor.py`, `core/logging/logger.py`.

### B. Code analysis
- **Entry points:** `ZmqPublisher.publish(topic, msg_type, data, version)`, `ZmqSubscriber.recv(timeout_ms)`, `TelemetryPublisher.publish_{metrics,positions,health,log}(...)`, `TelemetryBridge.start()/subscribe()/unsubscribe()`, `get_telemetry_bridge()`.
- **Data flow:** runner `_publish_telemetry()` → `TelemetryPublisher` → ZMQ PUB `tcp://127.0.0.1:5560` → `TelemetryBridge` SUB (daemon thread, `topics=["telemetry"]`) → per-client `Queue(maxsize=10)` with **drop-oldest backpressure** → SSE → dashboard. Topics: `telemetry.{metrics,positions,health,logs}.{node}`. Envelope `{v,type,topic,ts,data}`.
- **Resilience (grounded):** `SNDHWM=1000`; publisher init failure is swallowed (`TelemetryPublisher.__init__` try/except); `_safe_publish` swallows publish errors ("telemetry failure must not break trading"); `close()` nulls socket ref first to avoid shutdown races; `LINGER=0`.
- **External deps:** pyzmq, TCP loopback.

### C. Operational importance
- **Live trading: not required** for the *telemetry* layer (fire-and-forget, failures swallowed).
- **Observability: required** — it is the only live feed of PnL/positions/health to the UI.
- **However the `zmq_handler` primitive is load-bearing** for the **market-data path** (`zmq_market` provider, `db_tick_aggregator`) and the **options live push** (`options_publisher`) — so the primitive is operationally important even though the telemetry wrapper is optional.

### D. Removal impact
- Remove telemetry layer only: dashboard goes dark (no live metrics/positions/health); **trading unaffected**.
- Remove `zmq_handler` primitive: also **breaks options live push and the ZMQ market-data ingestion path** — not just monitoring.

### E. Recommendation — **KEEP**
Clean, non-invasive, exception-safe, and widely depended upon (including by the options feature the user explicitly wants). Already migrated and import-clean.

---

## 5. Deterministic runner — `core/runner.py` (`TradingRunner`)

### A. Purpose
A **single-threaded, neutral orchestrator** that drives data → signal → execution with live and backtest data treated identically (reproducibility). It is also the **integration seam** that wires heartbeat (#3) and telemetry (#4) onto execution (#2).

**Depends on:** `strategies.base.BaseStrategy`, `database.providers.base` (`MarketDataProvider`, `AnalyticsProvider`), `ExecutionHandler`, `PositionTracker`, `Clock`, `DatabaseManager`, `MarketHours`, `legacy_adapter.save_signal`, `TelemetryPublisher`, `alerter`.
**Depended on by:** entry scripts (`run_trading.py`, `live_runner.py`, `strategy_runner_node.py`, etc.).

### B. Code analysis
- **Entry points:** `TradingRunner(config, db_manager, market_data_provider, analytics_provider, strategies, ...)`, `.run()`, `.stop()`; `RunnerConfig`.
- **Loop methods (grounded):** `run()` → `_process_symbol()` → `_check_exit_conditions()`, `_check_data_staleness()`, `_write_heartbeat()`, `_publish_telemetry()`, `_log_signal()/_log_trade()`, `_update_runner_state()`, `_get_stats()`. Constants `DATA_STALE_THRESHOLD = 5 min`, `HEARTBEAT_INTERVAL_S = 10 s`.
- **Data flow:** provider bars → strategies emit signals → `execution.process_signal()` → trackers; every tick also fires heartbeat + telemetry + staleness check.
- **External deps:** DuckDB, ZMQ (via telemetry), filesystem.
- **Coupling (the blocker):** imports `core.strategies.base.BaseStrategy` and `core.database.providers.base.AnalyticsProvider` (the latter dropped as strategy-analytics). Constructor takes `List[BaseStrategy]`. **Cannot be migrated unchanged** — which is exactly why it was excluded.

### C. Operational importance
- **Reliable live trading: yes** — it is the process that actually runs, and the only place heartbeat + telemetry + execution are orchestrated together.
- **Observability: yes (driver)** — it sources every telemetry snapshot.
- **Reconciliation/risk: indirect** — it delegates to ExecutionHandler but drives the loop that triggers reconciliation, staleness, and the kill switch.

### D. Removal impact
- Lose the unified live/backtest loop (reproducibility guarantee) and the single orchestration point for heartbeat + telemetry + execution.
- The platform retains its *components* (handler, telemetry, trackers) but has **nothing to run them** in a deterministic loop.
- As-is it **cannot** be migrated — it drags in strategy and dropped-analytics dependencies.

### E. Recommendation — **KEEP capability; REFACTOR the file**
The deterministic single-threaded orchestrator is foundational and a property professional platforms guard. The current file must be **decoupled** from concrete `BaseStrategy`/`AnalyticsProvider` (accept a generic signal source) before it belongs in an infra-only repo. It is also the natural home for the extracted heartbeat watchdog (#3). **Not in `F:\Nifty` today.**

---

## Verdict summary

| # | Capability | Live-trading required | Observability | Reconciliation/Risk | In `F:\Nifty` now | Recommendation |
|---|---|---|---|---|---|---|
| 1 | Trade Learning Protocol | No | Post-trade only | No | Yes (capture+TLPLogger) | **KEEP protocol / REFACTOR CaptureEngine** |
| 2 | ExecutionHandler | **Yes (core)** | Emits metrics | **Yes** | Yes | **KEEP** |
| 3 | Heartbeat watchdog | **Yes (live safety)** | Liveness beacon | **Yes (kill switch)** | Stub only | **KEEP / REFACTOR out of runner** |
| 4 | ZMQ telemetry | No (telemetry) / **Yes (primitive)** | **Yes** | No | Yes | **KEEP** |
| 5 | Deterministic runner | **Yes** | Drives telemetry | Drives the loop | No | **KEEP / REFACTOR (decouple)** |

**Conclusion:** all five are foundational platform infrastructure, not strategy artifacts — **none should be removed.** Three are clean infra already preserved in `F:\Nifty` (ExecutionHandler, ZMQ telemetry, the TLP log). Two foundational capabilities — the heartbeat/staleness **watchdog** and the deterministic **runner** — currently exist only inside the strategy-coupled `core/runner.py`, which was correctly left out of the migration. They must be **ported across with their strategy coupling severed** before any redesign; "preserve" here means *carry the capability over*, because the live-safety watchdog and the deterministic loop are **not yet present in `F:\Nifty`**. The only `CaptureEngine` and `runner.py` work is decoupling, not rewriting behaviour.
