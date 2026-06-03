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
