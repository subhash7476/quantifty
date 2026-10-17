> **HISTORICAL — not a description of the current repository.** This is the June 2026 note written when
> infrastructure was copied from `D:\bot\root` into `F:\Nifty` (the SALVAGE migration). Its "Excluded Files"
> list (strategies, scanners, indicators, `core/execution/handler.py`, ...) is the state at that moment only;
> the tree has changed substantially since — `core/execution/handler.py` and `strategies/` now exist, for
> example. Moved from the repo root to `docs/archive/` on 2026-10-17. For the current layout see `README.md`,
> `DEVELOPER_GUIDE.md` and `docs/SESSION_BOOTSTRAP.md`.

# Nifty Migration Report

## Scope
Clean-slate infrastructure-only rebuild from `D:\bot\root`.

## Copied Files
- configuration under `config/`
- `core/auth/`
- `core/brokers/`
- `core/api/`
- `core/data/`
- `core/database/`
- `core/execution/` without strategy-specific modules
- `core/events.py`
- `core/clock.py`
- `core/alerts/`
- `core/logging/`
- `core/messaging/`
- `core/instruments/`
- `core/risk/greeks/`
- `core/analytics/resampler.py`
- docs from `docs/` and `ftmo/docs/`
- root docs/manifests listed in the allowlist

## Excluded Files
- strategies
- alpha engines
- scanners
- signal generators
- feature factories
- ranking systems
- indicator libraries
- experimental scripts
- abandoned research implementations
- generated outputs
- caches
- backfills
- `__pycache__`
- logs
- `core/execution/handler.py`
- `core/database/providers/analytics.py`
- strategy/analytics-facing code that was not proven to be infrastructure

## Unresolved Dependencies
- broker connectivity for live execution
- DuckDB/pandas/numpy/flask and other retained runtime libraries
- modules intentionally excluded because they are strategy-contaminated

## Required Environment Variables
- broker credentials and API keys
- database paths
- telemetry/alerting credentials if enabled

## Required Runtime Assets
- database files
- broker configuration data
- event/logging sinks
- runtime config artifacts used by retained modules

## Notes
- This repo is intentionally a clean-slate rebuild of reusable platform infrastructure.
- The package exports were narrowed to match the actual files retained in the tree.
