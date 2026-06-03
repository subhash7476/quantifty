# FTMO Architecture

## Scope
Reviewed `ftmo/` as the trusted runtime codebase, and cross-checked the design notes in `CLAUDE.md`, `DEVELOPER_GUIDE.md`, `docs/CODEBASE_OVERVIEW.md`, `docs/FTMO_CHALLENGE_SYSTEM.md`, `docs/FTMO_LIVE_DATA_PIPELINE.md`, `docs/LIVE_READINESS_AUDIT_REPORT.md`, `docs/SWEEP_CLASSIFIER_REPORT.md`, `ftmo/docs/ALPHASEEKER_HTF_IMPLEMENTATION.md`, and `ftmo/docs/FTMO_PROP_CHALLENGE_RESEARCH.md`.

## Architecture Review
`ftmo/` is structured around a single trading loop:
config -> data acquisition -> indicator and signal generation -> risk gate -> execution or backtest -> persistence -> UI or reporting.

The strongest boundary is the split between:
- `config.py` as the canonical parameter registry
- `detector.py` and `indicators.py` as deterministic signal construction
- `risk.py` as the hard gate
- `engine.py`, `simulation.py`, `live_trader.py`, and `rolling_live_trader.py` as execution and replay surfaces
- `db.py` as the local persistence contract
- `blueprint.py` as the Flask-facing presentation layer

The live path is production-shaped:
- MT5 connectivity is isolated in `mt5_downloader.py` and `live_trader.py`
- session timing and timestamp normalization are centralized
- sweep classifiers and tokenizers are loaded as local artifacts, not embedded ad hoc
- news blackout logic is explicit and time-bounded
- session state, equity state, and position recovery are handled inside the trader classes

The backtest path is equally coherent:
- `engine.py` replays the same trade setup logic used by live mode
- `simulation.py` re-evaluates FTMO challenge windows against the same risk engine
- `analytics.py` is post-run reporting, not strategy logic
- `db.py` persists canonical outputs for dashboard and review use

The research branch is intentionally separated:
- `ftmo/research/*` contains feature studies, acceptance analysis, exit studies, walk-forward work, and derived CSV and JSON artifacts
- these modules inform strategy evolution, but are not part of the core live loop

## Runtime Entry Points
- `python -m ftmo` -> `ftmo.__main__` -> `ftmo.cli.main()`
- `python -m ftmo.cli ...` for import, backtest, simulate, report, live, rolling-live, multi-live, download, symbols, portfolio, and portfolio-backtest
- `python -m ftmo.download_data` or direct script execution for MT5 downloads
- `ftmo.blueprint.ftmo_bp` is the Flask blueprint mounted by the outer app

## Config Requirements
- `ftmo/ftmo_trading.db` is the default DuckDB backing store
- `ftmo/cache_*.parquet`, `ftmo/*_M5.csv`, `ftmo/sweep_clf*.pkl`, and `ftmo/kline_vocab*.pkl` are required for the live and backtest workflow
- MT5 login, password, and server are required for live and download modes
- `Asia/Kolkata` is the operational timezone assumption throughout the package
- ForexFactory calendar fetch is an online dependency for live news blackout logic

## Summary
This is a coherent, production-shaped trading package with a clear separation between deterministic strategy logic, risk control, broker integration, persistence, and UI exposure.
