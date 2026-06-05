# PROJECT_STATE.md

**Purpose:** track current repository status. Populated from `docs/PLATFORM_CONSTITUTION.md`, `docs/PLATFORM_INVENTORY.md`, `docs/reports/SALVAGE_REPORT.md`, `docs/reports/CAPABILITY_REVIEW.md`, `docs/reports/RUNNER_DEPENDENCY_ANALYSIS.md`, and `docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md`.

**Last updated:** 2026-06-05

---

## Completed

- **Salvage migration concluded.** Infra-only Upstox bot (Nifty / equity / options) carried from `D:\BOT\root` into `F:\Nifty`; strategies, indicators, research, ML, backtesting, scanners, and FTMO excluded. *(docs/reports/SALVAGE_REPORT.md)*
- **`ExecutionHandler` restored.** The OMS/EMS core (`core/execution/handler.py`) that the initial migration had dropped is back and import-clean; the wrongly-kept `pixityAI_risk_engine.py` was removed. *(docs/reports/SALVAGE_REPORT.md §8)*
- **Options dashboard tier added.** `options_analytics`, `options_publisher`, `options_facade`, options blueprint/templates, and `run_options_engine.py` migrated; Flask app boots with 5 infra blueprints; `/options/` and `/database/` render 200. *(docs/reports/SALVAGE_REPORT.md §8)*
- **Import-closure + render verification green.** Full `core` + `app_facade` import-walk clean; forbidden-import scan (strategies/indicators/runner/backtest/state/models/ftmo) empty; `base.html` dead nav links fixed. *(docs/reports/SALVAGE_REPORT.md §8)*
- **Capability review completed.** The five surviving platform capabilities assessed (TLP, ExecutionHandler, heartbeat, ZMQ telemetry, deterministic runner). *(docs/reports/CAPABILITY_REVIEW.md)*
- **Runner dependency analysis + extraction blueprint produced.** Import-level classification of `core/runner.py`; per-capability extraction plan with difficulty and hidden risks. *(docs/reports/RUNNER_DEPENDENCY_ANALYSIS.md, docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md)*
- **Platform Constitution authored.** v1.0 foundational governance document. *(docs/PLATFORM_CONSTITUTION.md)*
- **Platform Inventory completed.** All 125 modules classified into single categories with KEEP/REFACTOR/REMOVE; constitution cross-analysis. *(docs/PLATFORM_INVENTORY.md)*
- **`RuntimeWatchdog` extracted.** `core/execution/watchdog.py` — heartbeat (`logs/heartbeat.json`, byte-for-byte keys) + data-staleness→kill-switch, strategy-free, both paths smoke-tested. *(docs/PLATFORM_INVENTORY.md — Observability)*
- **Repository knowledge system established.** `docs/SESSION_BOOTSTRAP.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE_DECISIONS.md`, `docs/CHANGELOG_PLATFORM.md`.
- **`DRIVER_SPECIFICATION.md` authored + ADR-006.** v1.0 implementation-ready spec for the deterministic LoopDriver (14 sections + Runtime Event Journal §15); ADR-006 binds all trading intent to the single `SignalSource → LoopDriver → ExecutionHandler → Ledger` path. *(docs/DRIVER_SPECIFICATION.md, ADR-006)*
- **`SignalSource` seam implemented.** `core/runtime/signal_source.py` — the strategy-agnostic abstract pull interface (`on_bar`/`on_start`/`on_stop`); stdlib + `core.events` only; 14 unit tests incl. an `ast` forbidden-import guard. *(docs/DRIVER_SPECIFICATION.md §5, ADR-002, ADR-006)*
- **`DriverConfig` implemented.** `core/runtime/config.py` — `DriverConfig` + `Mode` (LIVE/REPLAY); all 11 §13 fields with spec defaults, mode-aware `telemetry_enabled`, isolation-level validation, frozen; 14 unit tests. *(docs/DRIVER_SPECIFICATION.md §13)*

## In Progress

- **`RuntimeEventJournal`** — durable append-only operational audit trail (`logs/runtime_events.jsonl`, one JSON object per line, the 14 spec event types + 6-field schema). Building now per spec; complements `heartbeat.json` / telemetry / ledger and is **never a source of position truth** (ledger remains authoritative). *(docs/DRIVER_SPECIFICATION.md §15)*

## Planned

1. **LoopDriver — the final major runtime build.** `core/runtime/driver.py`: the single-threaded orchestrator that wires the completed `SignalSource` seam + `DriverConfig`, the in-progress `RuntimeEventJournal`, and the existing `RuntimeWatchdog` + telemetry into the deterministic loop (startup-validation gate, per-tick pipeline, recovery, failure modes). Includes the base-`Clock` `set_time` no-op prerequisite (§6.4). Last big runtime pillar; closes Principle 3/5 + §6 operationally. *(docs/DRIVER_SPECIFICATION.md §§3–12, ADR-006; docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md item 1)*
2. **Refactor soft strategy residue** — decouple `CaptureEngine`/`metrics_service` inputs from strategy-analytics tables; relocate `legacy_adapter.save_signal`; prune strategy-specific DDL from `database/schema.py`/`queries.py`/`writers.py`. *(docs/PLATFORM_INVENTORY.md §3)*
3. **Remove dead `core/data/*` twins** — seven modules with 0 importers, duplicates of canonical `core/database/*`. *(docs/PLATFORM_INVENTORY.md — Dead Code)*
4. **F&O broker product/segment model** — replace the hardcoded intraday `product:"I"` so futures carry and overnight option selling are possible. *(docs/PLATFORM_INVENTORY.md §2, §9)*
5. **Margin engine** — a real SPAN/exposure model to replace the flat-rate `MarginTracker`. *(docs/PLATFORM_INVENTORY.md §2, §8)*
6. **Broker-side reconciliation** — ledger-vs-live-broker position/holdings reconciliation. *(docs/PLATFORM_INVENTORY.md §2)*
7. **Unified market-data layer** — collapse the duplicated `core/data` ↔ `core/database/providers` lineages. *(docs/PLATFORM_INVENTORY.md — future pillars)*

## Blocked

- **Live derivatives trading** is blocked on two execution-depth items: the **F&O product model** (Planned #4) and the **SPAN margin engine** (Planned #5). Paper/intraday operation is not blocked.
- **Principle 5 / §6 operational compliance** is blocked on the **LoopDriver** (Planned #1) — `RuntimeWatchdog`, the `SignalSource` seam, and `DriverConfig` exist, but nothing drives them until the LoopDriver lands.

## Deferred

- **`CaptureEngine` full structural capture** — left half-stubbed (`_calculate_breadth`→0.5, `_get_index_trend`→"NEUTRAL"); the `TLPLogger` half is clean and retained. Revisit only when a strategy needs it. *(docs/reports/CAPABILITY_REVIEW.md #1)*
- **`HealthMonitor` consolidation** — the thin in-process counter is kept for the ops dashboard tile; conceptually superseded by `RuntimeWatchdog`. Consolidation deferred. *(docs/PLATFORM_INVENTORY.md — Observability)*
- **`scripts/migrate_monolith_to_isolated.py` removal** — one-shot migration tool; remove once migration is conclusively closed. *(docs/PLATFORM_INVENTORY.md — Utilities)*
- **Repository-level `git commit`** of the migration + knowledge system — changes remain uncommitted in `F:\Nifty`; committing was not requested. *(docs/reports/SALVAGE_REPORT.md §8)*
- **Stale top-level docs rewrite** — `CLAUDE.md` / `README.md` / `PROJECT_REVIEW_SUMMARY.md` still describe the old multi-strategy platform; rewrite for the infra-only repo. *(docs/reports/SALVAGE_REPORT.md §8)*
