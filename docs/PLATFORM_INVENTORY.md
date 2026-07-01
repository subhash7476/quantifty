# PLATFORM_INVENTORY.md

**Date:** 2026-06-04  **Governing document:** `docs/PLATFORM_CONSTITUTION.md` v1.0
**Basis:** enumeration of the actual `F:\Nifty` tree (125 `.py` modules) + import-trace verification. **No architecture redesigned. No code written. No features proposed.**
**Method:** each module classified into **exactly one** category by *dominant role*; cross-roles noted. Verdicts: KEEP / REFACTOR / REMOVE.

> Verified this pass: (a) **no Platform→Strategy import** anywhere (`core.strategies|runner|backtest|state|models|ftmo` scan = empty) → §5 boundary holds; (b) seven `core/data/*` modules have **0 importers** (dead legacy twins of `core/database/*`).

---

## Market Data

> **Note (MM11.3):** This section is superseded by the verified current-state evidence in `docs/reports/MM11_IMPLEMENTATION_SPECIFICATION.md` §0a. Twelve `core/data/` legacy modules previously listed here under "KEEP (verify)" or "REMOVE" verdicts have been removed per the deletion record in `docs/reports/MM11_REMOVAL_LEDGER.md`. The only remaining `core/data/` modules are `options_provider.py` (KEEP — options dashboard) and `MarketDataFeedV3_pb2.py` (KEEP — protobuf wire schema). See §4 below for the consolidated post-MM11.2 dead-code verdicts now resolved.

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `core/database/providers/{base,live_market,market_data,resampling_wrapper,zmq_market}.py` | Canonical provider layer (live/historical/zmq/resampled bars) | DatabaseManager, zmq_handler | **KEEP** | The lineage actually imported by facades/ingestors. Constitution §3 Market Data. |
| `core/database/ingestors/{websocket_ingestor,db_tick_aggregator,recovery_manager}.py` | Live WS ingest, tick→bar aggregation, recovery | DuckDB, zmq, upstox feed | **KEEP** | Canonical ingest path. (recovery_manager also serves Reconciliation.) |
| `core/database/utils/{market_hours,market_session}.py` | Market session handling (NSE calendar) | stdlib | **KEEP** | Canonical; used by handler/watchdog/telemetry. §3 "Market session handling". |
| `core/data/options_provider.py` | Upstox V3 option-chain fetch + cache | DatabaseManager | **KEEP** | Live (imported by options_facade). *Cross-role: Options Infra.* |
| `core/data/duckdb_client.py`, `core/data/schema.py`, `core/data/tick_aggregator.py` | DuckDB client + market-data schema + aggregation helpers | duckdb | **KEEP (verify)** | Appear live via options/data path; confirm against canonical `core/database` twins. |
| `core/data/MarketDataFeedV3_pb2.py` | Protobuf decode for Upstox MarketDataFeed V3 | protobuf | **KEEP** | Required to decode the live WS feed. |
| `core/brokers/upstox_market_data.py` | Broker market-data adapter (WS subscribe/decode) | upstox feed, pb2 | **KEEP** | Live market-data ingress. |
| `core/analytics/resampler.py` | Bar resampling (timeframe aggregation) | pandas | **KEEP** | Pure data transform. |
| `scripts/{market_ingestor,fetch_upstox_historical,fetch_intermarket_data}.py` | Live ingest node; historical backfill; index/intermarket fetch | providers, telemetry | **KEEP** | Market-data ingestion/backfill. (`fetch_intermarket_data` leans strategy-adjacent — verify it's not feeding a removed daytype feature.) |

## Instrument Master

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `core/instruments/{instrument_base,equity,future,option,instrument_parser,instrument_db}.py` | Instrument metadata model + FO symbol parsing + instrument DB | DuckDB | **KEEP** | §3 Instrument metadata; `future.py`/`option.py` directly serve the supported books. |
| `scripts/fetch_instrument_master.py` | Fetch/refresh NSE FO instrument master | upstox API | **KEEP** | Instrument-master maintenance. |

## Execution

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `core/execution/handler.py` | OMS/EMS core — `process_signal`, risk/idempotency gates, order creation, recovery | order_*, risk, trackers, persistence, clock, broker | **KEEP** | The execution spine (Principle 2/3/4). |
| `core/execution/{order_factory,order_lifecycle,order_models,order_tracker,rules}.py` | Order construction, lifecycle/fills, normalized models, tracking, authority/idempotency rules | events | **KEEP** | §3 Execution: create/submit/modify/cancel/fill. |
| `core/execution/groups/{order_group,group_tracker,group_pnl}.py` | Multi-leg order grouping + group PnL | order_models | **KEEP** | Needed for option spreads / multi-leg. |
| `core/execution/backfill_models.py` | Backfill order/position models from broker/DB | persistence | **KEEP (verify)** | Recovery-adjacent; confirm usage. |
| `core/brokers/{broker_base,base,paper_broker,mock_broker_adapter,upstox_adapter}.py` | Broker abstraction + paper/mock/live adapters | requests | **KEEP / REFACTOR** | KEEP all; **REFACTOR `upstox_adapter`** — `place_order` hardcodes `product:"I"` (intraday) → blocks §9 carry / overnight option selling. `base.py` vs `broker_base.py` = possible duplicate (verify). |
| `core/api/upstox_client.py` | Upstox REST client (auth'd HTTP) | requests | **KEEP** | Broker transport. |
| `core/events.py` | Event types (Signal/Order/Trade/Fill/OHLCV) — deterministic event vocabulary | — | **KEEP** | Spine of deterministic processing (Principle 3). *Cross-role: Utilities.* |
| `core/clock.py` | Data-driven deterministic clock | — | **KEEP** | Backtest==live determinism (Principle 3). |

## Ledger

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `core/execution/{position_tracker,position_models,pnl_tracker}.py` | Position truth + PnL | events | **KEEP** | Principle 1 ledger truth (positions, PnL). |
| `core/execution/persistence/{execution_store,order_repository,fill_repository,position_repository}.py` | Durable order/fill/position store + restore | DuckDB | **KEEP** | The persistent ledger; powers recovery. |
| `core/database/{manager,writers,queries,schema,locks}.py` | DuckDB manager, writers, queries, schema, lock coordination | duckdb | **KEEP / REFACTOR** | KEEP as ledger substrate; **REFACTOR `schema.py`/`queries.py`/`writers.py`** — they still carry strategy-specific DDL (`ns_paper_*`, daytype, pixity, `runner_state`, `tlp_trade_log`) = soft strategy residue (§10). |
| `core/database/legacy_adapter.py` | `save_signal` etc. — legacy signal persistence | manager | **REFACTOR** | Persists *strategy* signals (strategy output in the platform ledger) → strategy-boundary residue. *Cross-role: Strategy Coupling.* |
| `core/database/__init__.py` | Package exports (`db_cursor`, etc.) | — | **KEEP** | Public DB surface. |

## Risk

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `core/execution/{risk_manager,risk_models}.py` | Pre-trade risk limits, sizing, clearance | events | **KEEP** | Principle 4 (risk before trading). |
| `core/execution/margin_tracker.py` | Margin usage tracking | position_tracker | **REFACTOR** | Flat 20% rate, not SPAN — insufficient for real §8 option-selling margin. |
| `core/risk/greeks/{black76_engine,greeks_calculator,greeks_model,portfolio_greeks}.py` | Option pricing + greeks + portfolio aggregation | math/scipy | **KEEP** | §8 greeks monitoring + portfolio greeks. *Cross-role: Options Infra.* |

## Reconciliation

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `core/execution/reconciliation.py` | Position/state reconciliation engine | position_tracker | **KEEP** | §3 Reconciliation; Principle 1. (Verify breadth of *broker-side* reconciliation — may be partial vs §3 "Broker reconciliation".) |
| `core/database/ingestors/recovery_manager.py` | Startup/state recovery for ingest | DuckDB | **KEEP** | §7 recovery after restart. (Primary role Market Data ingest; reconciliation cross-role.) |

## Options Infrastructure

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `core/execution/options/selector.py` | ATM/expiry/strike → Option instrument selection | instruments | **KEEP** | §8 option execution support. |
| `core/analytics/options_analytics.py` | PCR / Net GEX / OI / Max Pain structural engine | options_provider | **KEEP** | Powers the options dashboard (structural metrics, not a trading signal). |
| `core/messaging/options_publisher.py` | SSE/ZMQ push of live option chain | zmq_handler | **KEEP** | Live options push. *Cross-role: Observability transport.* |
| `core/instruments/option.py` | Option instrument model | instrument_base | **KEEP** | (Primary role Instrument Master; options pillar.) |
| `scripts/run_options_engine.py` | Options engine entry point | options_publisher | **KEEP** | Options dashboard runtime. |

## Observability

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `core/messaging/{zmq_handler,telemetry}.py` | ZMQ pub/sub primitive + fire-and-forget telemetry | pyzmq | **KEEP** | §6 telemetry; also load-bearing for options push + zmq market data. |
| `flask_app/telemetry_bridge.py` | ZMQ→SSE bridge for the dashboard | zmq_handler | **KEEP** | §6 observability to UI. |
| `core/execution/watchdog.py` | **NEW** — heartbeat.json + data-staleness→kill-switch | handler, MarketHours, alerter | **KEEP (unwired)** | Implements Principle 5 + §6 heartbeat. **Present but inert** — no loop drives it yet (see Missing). |
| `core/execution/health_monitor.py` | In-process health counter (uptime/error count) | — | **KEEP** | Feeds ops dashboard health tile (ops_facade dep). Thin; superseded conceptually by watchdog. |
| `core/analytics/diagnostic_engine.py` | Diagnostics writer (DuckDB) | duckdb, pandas | **KEEP** | Clean diagnostics sink; handler dependency. |
| `core/alerts/{alerter,telegram_notifier}.py` | Critical alerting + Telegram channel | requests | **KEEP** | §6 alerting / "observable without broker login". |
| `core/logging/{__init__,logger,log_reader}.py` | Structured logging + log reader | — | **KEEP** | §6 error reporting / audit. |

## Dashboard

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `flask_app/__init__.py`, `flask_app/middleware.py` | App factory (5 infra blueprints) + middleware | blueprints | **KEEP** | Ops dashboard shell. |
| `flask_app/blueprints/{auth,dashboard,database,options}.py`, `flask_app/blueprints/ops/{__init__,routes}.py` | Auth, system dashboard, DB browser, options, ops health | facades | **KEEP** | §3 Operations Dashboard. |
| `app_facade/{__init__,auth_facade,data_facade,ops_facade,options_facade}.py` | Flask↔core facades | core services | **KEEP** | Read-only UI bridge (Principle 1: dashboard never overrides ledger). |
| `core/auth/{auth_service,credentials,models,password}.py` | Dashboard auth / access control | — | **KEEP** | UI access control. *Cross-role: Utilities.* |
| `scripts/run_flask.py` | Flask entry point | flask_app | **KEEP** | Dashboard runtime. |

## Utilities

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `core/database/utils/symbol_utils.py` | Symbol parsing/normalization | — | **KEEP (verify)** | Canonical twin of the broken `core/data/symbol_utils.py` (already removed). Confirm `get_instrument_info` completeness. |
| `scripts/migrate_monolith_to_isolated.py` | One-time monolith→isolated migration tool | DBs | **KEEP / REMOVE** | One-shot utility; remove once migration is closed (§10 keep platform smaller). |
| `core/*/__init__.py` (package markers) | Package exports | — | **KEEP** | Structural. |

## Strategy Coupling

| Module(s) | Purpose | Key deps | Verdict | Reasoning |
|---|---|---|---|---|
| `core/analytics/capture.py` | `CaptureEngine` (entry-time structural snapshot) + `TLPLogger` (trade-outcome log) | metrics_service, DB, analytics tables | **REFACTOR** | `TLPLogger` is clean audit infra (KEEP half); `CaptureEngine` reads strategy-analytics tables (`regime_insights`, `daily_structural_metrics`) and is half-stubbed → decouple inputs. Handler hook is optional/guarded. |
| `core/analytics/metrics_service.py` | `StructuralMetricsService` (percentiles from analytics tables) | DatabaseManager | **REFACTOR** | Only reachable as a `CaptureEngine` dependency; reads strategy-analytics tables. Keep only as long as capture is wired; otherwise removable. |
| `core/analytics/__init__.py` | analytics package marker | — | **KEEP** | Structural. |

*(Note: `legacy_adapter.py` and the strategy DDL inside `database/schema.py` are also strategy residue — filed under Ledger with REFACTOR verdicts to avoid double-listing.)*

## Dead Code

> **Note (MM11.3):** This section is superseded by `docs/reports/MM11_IMPLEMENTATION_SPECIFICATION.md` §0a and the deletion record in `docs/reports/MM11_REMOVAL_LEDGER.md`. All 12 `core/data/` legacy modules listed below — including the two "REMOVE (pending)" items and the three "KEEP (verify)" items that §0a corrected to REMOVE — have been removed in MM11.2. The Dead Code ledger is now closed for the `core/data/` domain. Remaining dead-code targets (strategy-shaped DDL, `AnalyticsQuery`, etc.) are tracked in later MM11 slices.

| Module(s) | Purpose | Verdict | Reasoning |
|---|---|---|---|
| `core/data/{market_hours,market_session,db_tick_aggregator,websocket_ingestor,recovery_manager,live_market_provider,historical_market_provider}.py` | Legacy monolith data layer | **REMOVE** | **Verified 0 importers** each; superseded by canonical `core/database/*`. Pure duplication (§10). |
| `core/data/{market_data_provider,duckdb_market_data_provider}.py` | Legacy provider twins | **REMOVE (pending)** | 1 internal importer each (self-referential within the dead `core/data` cluster); `data_facade` uses `core.database` only. Confirm the lone importer is itself dead, then remove. |
| `core/data/__init__.py` | Package marker for the mixed `core/data` dir | **KEEP** | Still needed while `options_provider.py` (live) resides here. |

---

## Constitution cross-analysis

### 1. Required by the constitution & already present ✅
- **Market Data** (live ingest, historical, instrument metadata, session handling, option chain) — §3 ✓
- **Execution** (create/submit/modify/cancel/fill/recovery via `handler` + order layer) — §3 ✓
- **Ledger** (orders/fills/positions/PnL/trade-history via trackers + persistence) — §3, Principle 1 ✓
- **Risk** (limits, greeks, portfolio greeks, kill switch; margin present-but-shallow) — §3, Principle 4 ✓
- **Reconciliation** (`reconciliation.py` + recovery) — §3, §7 ✓
- **Observability** (telemetry + bridge + alerting + logging; heartbeat/staleness now extracted) — §6 ✓ (wiring caveat below)
- **Operations Dashboard** (Flask shell + 5 infra blueprints + facades) — §3 ✓
- **Options Infrastructure** (selector, greeks, portfolio greeks, chain, structural analytics) — §8 ✓
- **Strategy boundary** — §5 ✓ (**verified**: zero Platform→Strategy imports)
- **Operational safety** (kill switch, restart recovery, reconciliation, audit trail) — §7 ✓

### 2. Required by the constitution but MISSING ❌
1. **Deterministic loop / single execution path *driver* (Principle 3).** No runner/orchestrator exists in `F:\Nifty`. Components exist; nothing drives them in a deterministic loop. **Highest-priority gap.**
2. **Principle 5 + §6 — operationally unmet despite extraction.** `watchdog.py` now *exists* but is **inert**: no live process calls `record_bar`/`check_data_staleness`/`write_heartbeat`. Until the loop driver wires it, the platform is **not** monitoring feed freshness and **not** emitting a trade heartbeat. (Capability present; obligation unmet.)
3. **§6 — per-process live trading observability.** Telemetry transport exists, but there is no *trading* process to emit metrics/positions/health (it's the same missing loop). The data-ingest node (`market_ingestor`) is observable; the trade node does not exist yet.
4. **§8 — margin-aware execution (depth).** SPAN/exposure margining missing; only flat-rate `MarginTracker`.
5. **§9 — futures carry / overnight option selling (broker product).** Order path is intraday-only (`product:"I"`); no NRML/carry product/segment awareness.
6. **§3 — broker-side reconciliation (depth).** Internal reconciliation exists; reconciliation *against live broker positions* needs verification — likely partial.

### 3. Components that VIOLATE the constitution ⚠️
- **Hard violations (Platform→Strategy, §5; or §4 non-responsibilities): NONE.** No strategy/research/ML/backtest/scanner modules; no Platform→Strategy import (verified).
- **Soft residue (boundary/§10 "keep platform smaller"):**
  - `core/analytics/capture.py` (`CaptureEngine`) + `core/analytics/metrics_service.py` — read strategy-analytics tables; strategy-coupled inputs. → **REFACTOR.**
  - `core/database/legacy_adapter.py` (`save_signal`) — persists strategy signals into the platform ledger. → **REFACTOR.**
  - `core/database/schema.py` / `queries.py` / `writers.py` — embed strategy-specific table DDL (`ns_paper_*`, daytype, pixity, `runner_state`, `tlp_trade_log`). Not executable strategy code, but strategy data definitions inside platform schema. → **REFACTOR (prune).**
  - `core/data/*` dead twins — duplication that bloats the platform. → **REMOVE.**

### 4. Components that should become future platform pillars 🏛️
*(Identification only — not a redesign.)*
1. **Deterministic loop driver** — the missing spine; the natural owner that wires `watchdog` + telemetry + execution (the deferred runner-scaffold extraction).
2. **Ledger as an explicit surface** — consolidate `position_tracker` + `pnl_tracker` + persistence repos behind one "ledger truth" API (Principle 1).
3. **Margin engine** — a real SPAN/exposure margin model is foundational for §8 option selling.
4. **Broker order-product/segment model** — F&O product/expiry/segment awareness, foundational for §9 carry and overnight option selling.
5. **Broker reconciliation service** — periodic ledger-vs-broker position/holdings reconciliation (Principle 1, §3, §7).
6. **Unified market-data layer** — collapse the duplicated `core/data` ↔ `core/database/providers` lineages into one canonical provider stack.

---

## Summary

`F:\Nifty` is, by inventory, a **clean platform core**: every surviving module is platform infrastructure or a thin strategy-residue/dead-code item — **no hard constitutional violation, no strategy/research/ML/backtest code, no Platform→Strategy dependency**. The constitution's execution, ledger, risk, reconciliation, observability, options, and dashboard responsibilities are all represented.

The gap between *what exists* and *what the constitution requires* is concentrated in three places: (1) the **deterministic loop driver is absent**, which leaves the freshly-extracted **watchdog inert** (Principle 5/§6 unmet operationally); (2) **execution depth** for derivatives (SPAN margin, F&O product type) is not yet built; and (3) **soft strategy residue** (capture/metrics_service inputs, `save_signal`, strategy DDL, dead `core/data` twins) should be refactored or removed to honor §10. None of these require redesign — they are the explicit next work items, with the loop driver as the single highest-priority pillar.
