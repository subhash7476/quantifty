# SESSION_BOOTSTRAP.md

**Purpose:** get a new Claude session productive in ≤ 5 minutes. This file is **current truth only** — no history, no changelog. (History lives in `docs/CHANGELOG_PLATFORM.md`; status detail in `docs/PROJECT_STATE.md`.)

---

## Repository Mission

`F:\Nifty` is a professional-grade **execution, risk, ledger, and operations platform** for Indian derivatives trading. Its job is to **safely execute, monitor, reconcile, and risk-manage** trading activity.

**The platform does not generate alpha.** It is strategy-agnostic and must remain usable even when no strategies exist.

## Supported Trading Books

1. **Equity Futures (directional)** — hold 3–15 trading days, 3–10 concurrent positions.
2. **Index Option Selling** — NIFTY and BANKNIFTY options.

The platform assumes no specific entry methodology for either book.

## Current Platform Status

- **Clean platform core.** Every surviving module is platform infrastructure (or thin strategy-residue / dead-code). **Verified: zero Platform→Strategy imports**; no strategy / research / ML / backtest / scanner code.
- **Present and working:** Market Data, Instrument Master, Execution (`ExecutionHandler` OMS/EMS core), Ledger (trackers + persistence), Risk (limits, greeks, portfolio greeks, kill switch), Reconciliation, Options Infrastructure (selector, greeks, chain, structural analytics), Observability (ZMQ telemetry + bridge + alerting + logging), Operations Dashboard (Flask, 5 infra blueprints), and a deterministic-runtime **watchdog** (heartbeat + staleness).
- **Runtime reality:** the deterministic **LoopDriver now exists** (`core/runtime/driver.py`, Phases A–G) and drives the runtime chain `Bar → Clock → SignalSource → LoopDriver → ExecutionHandler → RuntimeWatchdog → RuntimeEventJournal`. The watchdog is **driven** (live-gated), the **startup gate** (F) validates recovery + reconciliation before RUNNING, and **execution routing** (G routing sub-slice) forwards each pulled signal to `ExecutionHandler.process_signal(signal, bar.close)`. The loop is **no longer execution-free** — it routes. An internal **Runtime Observability Layer** (`core/runtime/metrics.py` — in-process metric counters, inert-by-default, injected) instruments the loop without changing it, and the `LoopDriver` now **publishes runtime metrics (H.1), node health/liveness (H.2), and positions (H.3) over the ZMQ wire** via `RuntimeTelemetryPublisher` (clock-throttled, best-effort, observation only) — **§10 telemetry is complete** (`telemetry.{metrics,health,positions}.{node}`). **`PortfolioView`** (`core/execution/portfolio_view.py`) projects a unified portfolio snapshot (positions / cash / realized+unrealized PnL / MTM equity / exposure / margin / portfolio Greeks) from the existing trackers — a projection, **not** a source of truth (ADR-001). As of MM9.3-S2, it is **wired into the LoopDriver's telemetry pipeline**: the driver's `_build_positions()` produces an enriched payload with real `pnl_pct`, financial fields, and `portfolio_greeks` (delta/gamma/vega/theta/rho) when a `PortfolioView` is injected (production path via `fno_runner.py`), and falls back to a degarded raw pass-through when absent.

## Current Runtime Status

- **Milestone ledger:**
  - Runtime Spine — **COMPLETE**
  - PortfolioView — **COMPLETE**
  - Metrics Publishing (H.1) — **COMPLETE**
  - Health Publishing (H.2) — **COMPLETE**
  - Position Publishing (H.3) — **COMPLETE**
- **Runtime chain (live today):** `Bar → Clock → SignalSource → LoopDriver → ExecutionHandler → RuntimeWatchdog → RuntimeEventJournal`. **Execution routing is present** (Phase G routing sub-slice) — each pulled `SignalEvent` is routed to `ExecutionHandler.process_signal(signal, current_price=bar.close)` in list order, gated on handler presence + RUNNING state (PAUSED suspends, §3.1).
- **LoopDriver phases complete (A–H — feature-complete):** A (lifecycle state machine), B (journal on transitions), C (tick loop + clock advancement + market data), D (SignalSource pull — collected), E (RuntimeWatchdog: `record_bar` per bar, staleness + heartbeat per tick, all live-gated; `WATCHDOG_STALE_DATA` edge-triggered), F (startup gate: recovery reuse + reconciliation before RUNNING, LIVE requires a handler, refuse-to-start on divergence), G (execution routing + §8.4 per-signal `BROKER_ERROR` isolation + IN-001 `KILL_SWITCH_ACTIVATED` single source — emitted from the handler `_kill_switched` edge, watchdog proxy retired), H (§10 telemetry: H.1 metrics / H.2 health / H.3 positions).
- **Runtime primitives complete:** `SignalSource`, `DriverConfig`, `RuntimeEventJournal`, `Clock.set_time`.
- **Tests:** `tests/runtime/` — **214 / 214 passing** (+2 from #6b.3 namespace acceptance tests), incl. the `ast` forbidden-import guard (ADR-002), the seam no-execution-coupling guard, the routing-era ADR-006 guard (the driver is the sole `process_signal` caller), the Runtime Observability Layer suite (`test_telemetry_sink.py` + `test_driver_telemetry.py`), and the ZMQ publishing suites (`test_telemetry_publisher.py` + `test_driver_telemetry_publish.py` + `test_driver_position_publish.py` — metrics H.1 + health H.2 + positions H.3). Full repo suite **541 passing** (incl. `tests/execution/test_portfolio_view.py`, the read-only `PortfolioView`; `tests/runtime/test_reconcile_symbol_namespace.py` acceptance test flipped 2 alerts → 0 via token-primary wiring `core/brokers/token_rekey.py`; +3 Planned #4 product-default tests in `test_upstox_mapping.py` / `test_place_order_resolution.py`).
- **Next runtime pillar:** the deterministic **LoopDriver is feature-complete** (A–H + the Phase G closers — §8.4 `BROKER_ERROR` isolation and the IN-001 kill-switch single source). No LoopDriver work remains. Next priorities move **off the driver** to execution depth for derivatives — the F&O product/segment model and a real SPAN margin engine, then broker-side reconciliation (`PROJECT_STATE.md` Planned #4–#6).

## Architecture Principles (from `docs/PLATFORM_CONSTITUTION.md`)

1. **Ledger Is Truth** — internal ledger is the source of truth (Exchange → Broker → Execution → Ledger → Risk → Dashboard). Nothing overrides ledger truth.
2. **Execution Before Alpha** — order correctness / fills / position accuracy / risk / reconciliation outrank indicators / models / predictions.
3. **Deterministic Operation** — single execution path, single position truth, deterministic event processing, auditable state. No hidden side effects.
4. **Risk Before Trading** — no trade without size, risk amount, stop, margin validation, and risk clearance.
5. **No Trading On Stale Data** — monitor feed freshness, detect stale data, alert, and trip protective controls.

## Current Gaps (what the constitution requires but isn't done)

1. **Deterministic loop driver — MET (feature-complete).** The `LoopDriver` runs the full chain — lifecycle, journal, tick loop, signal pull, watchdog (E), startup gate (F), execution routing with §8.4 per-signal `BROKER_ERROR` isolation (G), the IN-001 `KILL_SWITCH_ACTIVATED` single-source migration, and all §10 telemetry (H.1/H.2/H.3). Signals become orders through the single path (ADR-006); **no LoopDriver work remains.**
2. **Watchdog wiring — MET.** `RuntimeWatchdog` is now driven by the `LoopDriver` (live-gated `record_bar` / `check_data_staleness` / `write_heartbeat`); Principle 5 / §6 satisfied operationally for the staleness + heartbeat path.
3. **Margin depth (§8).** `MarginTracker` currently enforces a portfolio-aware flat-rate margin model. The `MarginCalculator` Protocol (MM9.4-S1) establishes the architectural seam, the SPAN parameter data pipeline (MM9.4-S2, `core/risk/span/`) provides the deterministic data foundation, and `SpanMarginCalculator` (MM9.4-S3) implements the first concrete SPAN-based calculator. The remaining step is the composition-root swap + buying-power gate (MM9.4-S4).
4. **Broker product model (§9) — RESOLVED (2026-06-15).** `core/brokers/mapping/upstox.py` now emits NRML (`"D"`) for FUTURE/OPTION and CNC (`"D"`) for EQUITY by default. Explicit `ci.product` override path preserved. Adapter `or "I"` fallback unreachable for tradable instruments. 541 passing.
5. **Broker-side reconciliation depth (§3).** Token-primary reconciliation wiring is COMPLETE (#6b.3 — `core/brokers/token_rekey.py`, `rekey_broker_positions_by_token`; namespace false-divergence eliminated; `UNRECONCILABLE_UNMAPPED_POSITION` alert introduced). Remaining: wire `broker_positions` at the `fno_runner` LIVE rung (gated on a first-hand authenticated non-empty position capture before `ExecutionMode.LIVE` is enabled).
6. **Soft strategy residue.** `CaptureEngine` + `metrics_service` read strategy-analytics tables; `legacy_adapter.save_signal`; strategy DDL in `database/schema.py`/`queries.py`/`writers.py`.
7. **Dead code.** Seven `core/data/*` legacy twins (0 importers) duplicate canonical `core/database/*`.

## Active Priorities

1. **LoopDriver — COMPLETE.** The deterministic runtime is feature-complete (A–H + the Phase G closers: §8.4 `BROKER_ERROR` isolation and the IN-001 kill-switch single source). The next execution priority is **#4 below** — deepen execution for derivatives (F&O product/segment model + a real SPAN margin engine), which blocks live derivatives trading.
2. **Refactor soft strategy residue** (decouple `CaptureEngine` inputs; relocate `save_signal`; prune strategy DDL).
3. **Remove dead `core/data/*` twins.**
4. **Deepen execution for derivatives**: F&O product/segment model **COMPLETE (2026-06-15)**. Remaining: a real SPAN margin engine (Planned #5).

## Forbidden Directions (from `docs/PLATFORM_CONSTITUTION.md` §4–§5)

The platform must **never** contain, and you must **not** add:
- Strategies, signal generation, alpha research, market-regime research.
- Machine learning: model training, feature engineering, labels, training pipelines.
- Backtesting engines, walk-forward frameworks, research simulations.
- Scanners / screeners / opportunity engines.
- Research notebooks, optimization experiments, parameter sweeps.
- **Any `Platform → Strategy` dependency.** Allowed direction is `Strategy → Platform` only.

When uncertain whether something belongs: **keep platform code smaller**; strategy/research stays out of this repo.

## Key Documents To Read (in order)

1. `docs/PLATFORM_CONSTITUTION.md` — governing law (mission, principles, responsibilities, boundaries).
2. `docs/PROJECT_STATE.md` — completed / in-progress / planned / blocked / deferred.
3. `docs/PLATFORM_INVENTORY.md` — every module classified, with KEEP/REFACTOR/REMOVE.
4. `docs/ARCHITECTURE_DECISIONS.md` — the binding ADRs.
5. `docs/reports/CAPABILITY_REVIEW.md`, `docs/reports/RUNNER_DEPENDENCY_ANALYSIS.md`, `docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md` — deep context for the loop/observability work.
6. `docs/reports/SALVAGE_REPORT.md` — what was migrated/dropped and why.

## Current Next Steps

1. Read `docs/PLATFORM_CONSTITUTION.md` + `docs/PROJECT_STATE.md`.
2. The **LoopDriver is feature-complete** (A–H + Phase G closers). Pick up the next execution-depth priority (Active Priority #4 / `PROJECT_STATE.md` Planned #4–#5): the F&O product/segment model and a real SPAN margin engine, which block live derivatives trading (TDD, suite green-on-merge).
3. Keep every change inside the constitution: platform-only, no strategy, no research, `Strategy → Platform` only.
