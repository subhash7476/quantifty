# CHANGELOG_PLATFORM.md

Append-only history of major platform milestones for `F:\Nifty`. Newest entries at the top. Record *what happened*; rationale and current status live in `docs/ARCHITECTURE_DECISIONS.md` and `docs/PROJECT_STATE.md`.

Format: `## YYYY-MM-DD — <milestone>` with a short factual description and source reference.

---

## 2026-06-06 — LoopDriver Execution Routing — routing sub-slice (Phase G)
Wired signal routing into the `LoopDriver` (`core/runtime/driver.py` `_dispatch_signals`): each pulled `SignalEvent` is forwarded, in list order, to the canonical `ExecutionHandler.process_signal(signal, current_price=bar.close)` (§8.1). `current_price` is always `bar.close` — deterministic, so live and replay traverse the identical routing path. Routing is gated on handler presence **and** the RUNNING state (PAUSED suspends it without going blind, §3.1); the no-handler path (replay/inert/test) collects only, and `signals_pulled` still counts unconditionally (Phase D preserved). `_tick` is untouched, so watchdog `record_bar`/heartbeat ordering is byte-for-byte unchanged. ADR-006: the driver is the sole runtime caller of `process_signal`; the `SignalSource` seam holds no handler handle (statically guarded). The Phase E/F "routes nothing" AST guard inverted to `test_driver_routes_through_process_signal`; every watchdog behavioral test is unchanged. Deliberately narrow — no orders/fills/sizing/risk/telemetry. Added `tests/runtime/test_driver_execution_routing.py` (11 tests) + a `process_signal` recording spy on `FakeExecutionHandler`; runtime suite **155 passing**. Runtime flow now `Bar → Clock → SignalSource → LoopDriver → ExecutionHandler → RuntimeWatchdog → RuntimeEventJournal`. **Deferred (close Phase G next):** per-signal exception isolation (§8.4, `BROKER_ERROR`) and the IN-001 `KILL_SWITCH_ACTIVATED` single-source migration — now reachable, since `process_signal` can trip the handler's own kill switch while the driver still observes only `watchdog.data_healthy`.
*Ref: docs/DRIVER_SPECIFICATION.md §8; ADR-005, ADR-006; ARCHITECTURE_DECISIONS.md IN-001; docs/PROJECT_STATE.md.*

## 2026-06-06 — LoopDriver Startup Gate / Recovery (Phase F)
Added the §11 startup-validation gate to the `LoopDriver` (`core/runtime/driver.py`), run inside `run()` before the loop when an `ExecutionHandler` is injected. Sequence: `RECOVERY_STARTED` → reuse the handler's already-run recovery (`load_db_state=True`; the driver **never** calls `_replay_state()` — ADR-001) → `RECOVERY_COMPLETED` → reconcile the restored ledger against broker truth (`handler.reconciliation.reconcile(broker_positions)`) → empty = `RECONCILIATION_PASS` → `RUNNING`, non-empty = `RECONCILIATION_FAIL` → `abort_startup()` (STOPPED + critical alert; tick loop never runs). Reconciliation branches by **source presence** (require flag + injected `broker_positions`), not by mode; vacuously clear for paper/replay and for LIVE until the broker book is wired (Planned #6). **LIVE mode now requires an injected `ExecutionHandler`** — `run()` raises `RuntimeError` without one; the no-handler ungated path is replay/inert/test only. Still execution-free — no `process_signal` (ADR-006); the watchdog guard was narrowed from "no `ExecutionHandler` dependency" to the real ADR-006 invariant (no `process_signal` call), allowing the legitimate handler reference the gate requires. Phase E watchdog tests updated to inject a `FakeExecutionHandler`; added `FakeExecutionHandler`/`FakeReconciliation` + `test_driver_startup_gate.py`; runtime suite increased to **144 passing**.
*Ref: docs/DRIVER_SPECIFICATION.md §11; ADR-001, ADR-006; docs/PHASE_F_STARTUP_GATE_PLAN.md; docs/PROJECT_STATE.md.*

## 2026-06-05 — LoopDriver Watchdog Integration (Phase E)
Wired `RuntimeWatchdog` into the `LoopDriver` (`core/runtime/driver.py`; watchdog reused unchanged): per-bar `record_bar()`, per-tick `check_data_staleness()` + `write_heartbeat(bars_processed)` after the symbol sweep, **all live-mode gated** (replay drives none). Heartbeat generation and staleness monitoring are now operationally driven. A stale-feed trip is recorded to the runtime journal edge-triggered as `WATCHDOG_STALE_DATA` + `KILL_SWITCH_ACTIVATED` (observed via the watchdog's public `data_healthy` flag). The loop remains execution-free — no `ExecutionHandler` routing, no `process_signal` (ADR-006). Added `FakeWatchdog` + 11 watchdog tests; runtime suite increased to **135 passing**. Runtime chain: `Bar → Clock → SignalSource → RuntimeWatchdog → RuntimeEventJournal`.
*Ref: docs/DRIVER_SPECIFICATION.md §9; ADR-004; docs/PROJECT_STATE.md.*

## 2026-06-05 — Deterministic LoopDriver build (Phases A–D) + runtime primitives
Built the `core/runtime/` package and the deterministic loop scaffold. Primitives: `SignalSource` (strategy-agnostic pull seam), `DriverConfig` (+ `Mode`), `RuntimeEventJournal` (append-only `logs/runtime_events.jsonl`), `Clock.set_time`. `LoopDriver` phases: A (six-state lifecycle + §3.2 transitions), B (journal emission on transitions, edge-triggered), C (tick loop + clock advancement + market-data pull, replay-exhaustion vs live-poll, `max_bars`, cooperative stop), D (SignalSource pull — signals collected in list order but **not routed**). Strategy-agnostic (`ast` forbidden-import guard); single-threaded deterministic decision path (ADR-003). Execution-free throughout.
*Ref: docs/DRIVER_SPECIFICATION.md; docs/LOOPDRIVER_IMPLEMENTATION_PLAN.md; ADR-002/003/006; docs/PROJECT_STATE.md.*

## 2026-06-04 — Repository knowledge system established
Created the permanent knowledge base under `docs/`: `docs/SESSION_BOOTSTRAP.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE_DECISIONS.md` (ADR-001…ADR-005), and this changelog.

## 2026-06-04 — RuntimeWatchdog extracted
Extracted the heartbeat generator and data-staleness watchdog from `core/runner.py` into `core/execution/watchdog.py` (`RuntimeWatchdog`). Strategy-free; preserves `logs/heartbeat.json` keys byte-for-byte; staleness trips `ExecutionHandler.activate_kill_switch` during market hours. Both paths smoke-tested. Passive by design — not yet driven by a loop.
*Ref: docs/PLATFORM_INVENTORY.md (Observability); docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md.*

## 2026-06-04 — Platform Inventory completed
Classified all 125 surviving modules into single categories with KEEP/REFACTOR/REMOVE verdicts and a constitution cross-analysis. Verified zero Platform→Strategy imports; identified seven dead `core/data/*` twins (0 importers), soft strategy residue, and the missing deterministic loop driver as the top pillar.
*Ref: docs/PLATFORM_INVENTORY.md.*

## 2026-06-04 — Platform Constitution created
Authored `docs/PLATFORM_CONSTITUTION.md` v1.0 — mission, five core principles (Ledger Is Truth; Execution Before Alpha; Deterministic Operation; Risk Before Trading; No Trading On Stale Data), platform responsibilities, explicit non-responsibilities, and the strategy boundary.
*Ref: docs/PLATFORM_CONSTITUTION.md.*

## 2026-06-04 — Runner capability review, dependency analysis, and extraction blueprint produced
Reviewed the five surviving platform capabilities (Trade Learning Protocol, ExecutionHandler, heartbeat, ZMQ telemetry, deterministic runner); performed an import-level dependency analysis of `core/runner.py`; produced a per-capability extraction blueprint with difficulty ratings and hidden risks, plus a readiness assessment for a futures + option-selling core.
*Ref: docs/reports/CAPABILITY_REVIEW.md; docs/reports/RUNNER_DEPENDENCY_ANALYSIS.md; docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md.*

## 2026-06-04 — ExecutionHandler restored
Restored `core/execution/handler.py` (842-line OMS/EMS core) and its infra dependencies (`capture.py`, `diagnostic_engine.py`, `metrics_service.py`) that the initial migration had dropped; removed the wrongly-retained strategy module `pixityAI_risk_engine.py`. Fixed dead navigation links in `flask_app/templates/base.html`. Verified the Flask app boots with 5 infra blueprints and `/options/`, `/database/` render 200.
*Ref: docs/reports/SALVAGE_REPORT.md §8.*

## 2026-06-04 — Salvage migration concluded
Concluded the infra-only migration of the Upstox bot (Nifty / equity / options) from `D:\BOT\root` into `F:\Nifty`. Added the options-dashboard + Flask + facade + scripts tiers; removed FTMO, strategy docs, and orphaned/broken `core/data` analytics plumbing; rewrote `requirements.txt` from an AST scan of actual imports. Full `core` + `app_facade` import-walk clean; forbidden-import scan (strategies/indicators/runner/backtest/state/models/ftmo) empty.
*Ref: docs/reports/SALVAGE_REPORT.md.*
