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
- **Runtime reality:** the Flask app + options dashboard boot and render; there is **no live trading loop yet**, so the watchdog and trade-telemetry are **present but not driven**.

## Architecture Principles (from `docs/PLATFORM_CONSTITUTION.md`)

1. **Ledger Is Truth** — internal ledger is the source of truth (Exchange → Broker → Execution → Ledger → Risk → Dashboard). Nothing overrides ledger truth.
2. **Execution Before Alpha** — order correctness / fills / position accuracy / risk / reconciliation outrank indicators / models / predictions.
3. **Deterministic Operation** — single execution path, single position truth, deterministic event processing, auditable state. No hidden side effects.
4. **Risk Before Trading** — no trade without size, risk amount, stop, margin validation, and risk clearance.
5. **No Trading On Stale Data** — monitor feed freshness, detect stale data, alert, and trip protective controls.

## Current Gaps (what the constitution requires but isn't done)

1. **Deterministic loop driver — ABSENT.** Highest-priority gap. No orchestrator runs the data→signal→execution loop. This is *why* the watchdog and trade-telemetry are inert.
2. **Watchdog wiring — UNMET.** `core/execution/watchdog.py` exists and is tested, but nothing calls it → Principle 5 / §6 unmet operationally.
3. **Margin depth (§8).** `MarginTracker` is a flat 20% rate, not SPAN — insufficient for real option-selling margin.
4. **Broker product model (§9).** `upstox_adapter.place_order` hardcodes `product:"I"` (intraday) — no NRML/carry for futures or overnight option selling.
5. **Broker-side reconciliation depth (§3).** Internal reconciliation exists; ledger-vs-live-broker reconciliation needs work.
6. **Soft strategy residue.** `CaptureEngine` + `metrics_service` read strategy-analytics tables; `legacy_adapter.save_signal`; strategy DDL in `database/schema.py`/`queries.py`/`writers.py`.
7. **Dead code.** Seven `core/data/*` legacy twins (0 importers) duplicate canonical `core/database/*`.

## Active Priorities

1. **Extract the deterministic loop scaffold** from `core/runner.py` (strategy body excluded) and **wire the watchdog + telemetry** to it — closes gaps 1 + 2 and satisfies Principles 3/5 + §6.
2. **Refactor soft strategy residue** (decouple `CaptureEngine` inputs; relocate `save_signal`; prune strategy DDL).
3. **Remove dead `core/data/*` twins.**
4. **Deepen execution for derivatives**: F&O product/segment model + a real margin engine (sequence after the loop exists).

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
2. Pick up **Active Priority #1**: extract the deterministic loop scaffold per `docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md` (heartbeat + staleness are already extracted; the loop driver is the remaining piece) and wire `RuntimeWatchdog`.
3. Keep every change inside the constitution: platform-only, no strategy, no research, `Strategy → Platform` only.
