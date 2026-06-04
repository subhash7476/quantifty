# PROJECT_STATE.md

**Purpose:** track current repository status. Populated from `docs/PLATFORM_CONSTITUTION.md`, `docs/PLATFORM_INVENTORY.md`, `docs/reports/SALVAGE_REPORT.md`, `docs/reports/CAPABILITY_REVIEW.md`, `docs/reports/RUNNER_DEPENDENCY_ANALYSIS.md`, and `docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md`.

**Last updated:** 2026-06-04

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

## In Progress

- *(none actively mid-change.)* The repository is at a clean checkpoint: knowledge system just established, ready for the next build step (the deterministic loop driver).

## Planned

1. **Deterministic loop driver** — extract the loop scaffold from `core/runner.py` (strategy body excluded) and **wire `RuntimeWatchdog` + telemetry** to it. Highest priority; closes Principle 3/5 + §6 operationally. *(docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md item 1)*
2. **Refactor soft strategy residue** — decouple `CaptureEngine`/`metrics_service` inputs from strategy-analytics tables; relocate `legacy_adapter.save_signal`; prune strategy-specific DDL from `database/schema.py`/`queries.py`/`writers.py`. *(docs/PLATFORM_INVENTORY.md §3)*
3. **Remove dead `core/data/*` twins** — seven modules with 0 importers, duplicates of canonical `core/database/*`. *(docs/PLATFORM_INVENTORY.md — Dead Code)*
4. **F&O broker product/segment model** — replace the hardcoded intraday `product:"I"` so futures carry and overnight option selling are possible. *(docs/PLATFORM_INVENTORY.md §2, §9)*
5. **Margin engine** — a real SPAN/exposure model to replace the flat-rate `MarginTracker`. *(docs/PLATFORM_INVENTORY.md §2, §8)*
6. **Broker-side reconciliation** — ledger-vs-live-broker position/holdings reconciliation. *(docs/PLATFORM_INVENTORY.md §2)*
7. **Unified market-data layer** — collapse the duplicated `core/data` ↔ `core/database/providers` lineages. *(docs/PLATFORM_INVENTORY.md — future pillars)*

## Blocked

- **Live derivatives trading** is blocked on two execution-depth items: the **F&O product model** (Planned #4) and the **SPAN margin engine** (Planned #5). Paper/intraday operation is not blocked.
- **Principle 5 / §6 operational compliance** is blocked on the **deterministic loop driver** (Planned #1) — `RuntimeWatchdog` exists but cannot run until something drives it.

## Deferred

- **`CaptureEngine` full structural capture** — left half-stubbed (`_calculate_breadth`→0.5, `_get_index_trend`→"NEUTRAL"); the `TLPLogger` half is clean and retained. Revisit only when a strategy needs it. *(docs/reports/CAPABILITY_REVIEW.md #1)*
- **`HealthMonitor` consolidation** — the thin in-process counter is kept for the ops dashboard tile; conceptually superseded by `RuntimeWatchdog`. Consolidation deferred. *(docs/PLATFORM_INVENTORY.md — Observability)*
- **`scripts/migrate_monolith_to_isolated.py` removal** — one-shot migration tool; remove once migration is conclusively closed. *(docs/PLATFORM_INVENTORY.md — Utilities)*
- **Repository-level `git commit`** of the migration + knowledge system — changes remain uncommitted in `F:\Nifty`; committing was not requested. *(docs/reports/SALVAGE_REPORT.md §8)*
- **Stale top-level docs rewrite** — `CLAUDE.md` / `README.md` / `PROJECT_REVIEW_SUMMARY.md` still describe the old multi-strategy platform; rewrite for the infra-only repo. *(docs/reports/SALVAGE_REPORT.md §8)*
