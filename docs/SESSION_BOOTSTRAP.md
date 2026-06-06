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
- **Runtime reality:** the deterministic **LoopDriver now exists** (`core/runtime/driver.py`, Phases A–G) and drives the runtime chain `Bar → Clock → SignalSource → LoopDriver → ExecutionHandler → RuntimeWatchdog → RuntimeEventJournal`. The watchdog is **driven** (live-gated), the **startup gate** (F) validates recovery + reconciliation before RUNNING, and **execution routing** (G routing sub-slice) forwards each pulled signal to `ExecutionHandler.process_signal(signal, bar.close)`. The loop is **no longer execution-free** — it routes. An internal **Runtime Observability Layer** (`core/runtime/metrics.py` — in-process metric counters, inert-by-default, injected) instruments the loop without changing it, and the `LoopDriver` now **publishes runtime metrics (H.1) and node health/liveness (H.2) over the ZMQ wire** via `RuntimeTelemetryPublisher` (clock-throttled, best-effort, observation only). The one remaining §10 telemetry item is **position publishing (H.3)**.

## Current Runtime Status

- **Runtime chain (live today):** `Bar → Clock → SignalSource → LoopDriver → ExecutionHandler → RuntimeWatchdog → RuntimeEventJournal`. **Execution routing is present** (Phase G routing sub-slice) — each pulled `SignalEvent` is routed to `ExecutionHandler.process_signal(signal, current_price=bar.close)` in list order, gated on handler presence + RUNNING state (PAUSED suspends, §3.1).
- **LoopDriver phases complete:** A (lifecycle state machine), B (journal on transitions), C (tick loop + clock advancement + market data), D (SignalSource pull — collected), E (RuntimeWatchdog: `record_bar` per bar, staleness + heartbeat per tick, all live-gated; `WATCHDOG_STALE_DATA` + `KILL_SWITCH_ACTIVATED` edge-triggered), F (startup gate: recovery reuse + reconciliation before RUNNING, LIVE requires a handler, refuse-to-start on divergence), G — **routing sub-slice** (route each pulled signal to `process_signal`; deferred to close G: §8.4 `BROKER_ERROR` isolation + IN-001 kill-switch consolidation).
- **Runtime primitives complete:** `SignalSource`, `DriverConfig`, `RuntimeEventJournal`, `Clock.set_time`.
- **Tests:** `tests/runtime/` — **201 / 201 passing**, incl. the `ast` forbidden-import guard (ADR-002), the seam no-execution-coupling guard, the routing-era ADR-006 guard (the driver is the sole `process_signal` caller), the Runtime Observability Layer suite (`test_telemetry_sink.py` + `test_driver_telemetry.py`), and the ZMQ publishing suites (`test_telemetry_publisher.py` + `test_driver_telemetry_publish.py` — metrics H.1 + health H.2).
- **Next runtime pillar:** LoopDriver telemetry **Phase H.3 — Position Publishing (§10.4)** — the last §10 gap (H.1 metrics + H.2 health are done) — plus Phase G's remaining increments (§8.4 `BROKER_ERROR` isolation + IN-001 `KILL_SWITCH_ACTIVATED` single-source consolidation).

## Architecture Principles (from `docs/PLATFORM_CONSTITUTION.md`)

1. **Ledger Is Truth** — internal ledger is the source of truth (Exchange → Broker → Execution → Ledger → Risk → Dashboard). Nothing overrides ledger truth.
2. **Execution Before Alpha** — order correctness / fills / position accuracy / risk / reconciliation outrank indicators / models / predictions.
3. **Deterministic Operation** — single execution path, single position truth, deterministic event processing, auditable state. No hidden side effects.
4. **Risk Before Trading** — no trade without size, risk amount, stop, margin validation, and risk clearance.
5. **No Trading On Stale Data** — monitor feed freshness, detect stale data, alert, and trip protective controls.

## Current Gaps (what the constitution requires but isn't done)

1. **Deterministic loop driver — PARTIAL.** The `LoopDriver` exists and runs through Phase E (lifecycle, journal, tick loop, signal pull, watchdog). **Remaining:** Phase F (startup gate / recovery), Phase G (execution routing — the data→signal→**execution** path is still open), Phase H (telemetry). Until G lands, no signal becomes an order.
2. **Watchdog wiring — MET.** `RuntimeWatchdog` is now driven by the `LoopDriver` (live-gated `record_bar` / `check_data_staleness` / `write_heartbeat`); Principle 5 / §6 satisfied operationally for the staleness + heartbeat path.
3. **Margin depth (§8).** `MarginTracker` is a flat 20% rate, not SPAN — insufficient for real option-selling margin.
4. **Broker product model (§9).** `upstox_adapter.place_order` hardcodes `product:"I"` (intraday) — no NRML/carry for futures or overnight option selling.
5. **Broker-side reconciliation depth (§3).** Internal reconciliation exists; ledger-vs-live-broker reconciliation needs work.
6. **Soft strategy residue.** `CaptureEngine` + `metrics_service` read strategy-analytics tables; `legacy_adapter.save_signal`; strategy DDL in `database/schema.py`/`queries.py`/`writers.py`.
7. **Dead code.** Seven `core/data/*` legacy twins (0 importers) duplicate canonical `core/database/*`.

## Active Priorities

1. **Finish the LoopDriver** (the scaffold + watchdog are done): **Phase F — Startup Gate / Recovery** (the §11 ledger-validation gate, reusing `ExecutionHandler._replay_state` + `reconciliation.reconcile`), then **Phase G — Execution Routing** (`process_signal`, ADR-006 single path), then **Phase H — Telemetry**. Safety gates (E watchdog, F startup) land **before** execution (G) by design.
2. **Refactor soft strategy residue** (decouple `CaptureEngine` inputs; relocate `save_signal`; prune strategy DDL).
3. **Remove dead `core/data/*` twins.**
4. **Deepen execution for derivatives**: F&O product/segment model + a real margin engine (sequence after execution routing exists).

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
2. Pick up **Active Priority #1**: implement **LoopDriver Phase F — Startup Gate / Recovery** per `docs/DRIVER_SPECIFICATION.md` §11 and `docs/PHASE_F_STARTUP_GATE_PLAN.md` (TDD, runtime suite green-on-merge). Execution routing (Phase G) stays deferred until F is green.
3. Keep every change inside the constitution: platform-only, no strategy, no research, `Strategy → Platform` only.
