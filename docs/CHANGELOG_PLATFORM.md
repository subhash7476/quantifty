# CHANGELOG_PLATFORM.md

Append-only history of major platform milestones for `F:\Nifty`. Newest entries at the top. Record *what happened*; rationale and current status live in `docs/ARCHITECTURE_DECISIONS.md` and `docs/PROJECT_STATE.md`.

Format: `## YYYY-MM-DD — <milestone>` with a short factual description and source reference.

---

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
