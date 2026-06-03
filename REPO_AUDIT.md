# Repository Audit

- Root: `D:\bot\root`
- Files audited: `2924`
- Dependency count: direct in-repo Python import dependencies for `.py` files; `0` for non-Python files.
- Recommendation: `Keep` for source/config/runtime assets; `Delete` for generated logs, caches, and reproducible artifacts.

## Category Counts
- Data Pipeline: `1704`
- Experimental / Dead Code: `513`
- Infrastructure: `247`
- Research Utility: `127`
- Backtesting Framework: `78`
- Configuration: `68`
- Monitoring: `59`
- Documentation: `45`
- Strategy Logic: `26`
- Risk Management: `22`
- Indicator Logic: `19`
- Broker Integration: `16`

## File Audit

| File path | Category | Dependency count | Recommendation | Justification |
|---|---:|---:|---|---|
| `.claude/settings.json` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `.claude/settings.local.json` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `.env.example` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `.gitignore` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `.mcp.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `.vscode/extensions.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `2026-05-25` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `analytics/__init__.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `analytics/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `analytics/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `analytics/__pycache__/options_greeks.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `analytics/__pycache__/options_greeks.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `analytics/__pycache__/structured_metrics.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `analytics/__pycache__/structured_metrics.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `analytics/options_greeks.py` | Indicator Logic | `0` | Keep | Computes indicators, features, or market-derived signals. |
| `analytics/structured_metrics.py` | Monitoring | `0` | Keep | Captures logs, telemetry, health, or operational status. |
| `app_facade/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `app_facade/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `app_facade/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `app_facade/__pycache__/backtest_facade.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `app_facade/__pycache__/backtest_facade.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `app_facade/__pycache__/commodities_facade.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `app_facade/__pycache__/commodities_facade.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `app_facade/__pycache__/options_facade.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `app_facade/__pycache__/options_facade.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `app_facade/analytics_facade.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `app_facade/auth_facade.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `app_facade/backtest_facade.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `app_facade/commodities_facade.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `app_facade/data_facade.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `app_facade/ops_facade.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `app_facade/options_facade.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `app_facade/scanner_facade.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `backfills/confluence_consumer/CDSL/20260101_20260131_15b92db0e2efd1fc/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/CDSL/20260101_20260131_15b92db0e2efd1fc/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/CDSL/20260115_20260130_68f14c9654d56990/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/CDSL/20260115_20260130_68f14c9654d56990/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/NSE_EQ_INE002A01018/20260101_20260131_5777d921a11a8294/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/NSE_EQ_INE002A01018/20260101_20260131_5777d921a11a8294/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/NSE_EQ_INE002A01018/20260101_20260131_c82a3ea1dfb79fa8/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/NSE_EQ_INE002A01018/20260101_20260131_c82a3ea1dfb79fa8/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/NSE_EQ_INE089A01031/20251231_20260130_d3d69b444fe79383/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/NSE_EQ_INE089A01031/20251231_20260130_d3d69b444fe79383/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/NSE_EQ_INE742F01042/20251231_20260130_5029f05d2b82c692/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/confluence_consumer/NSE_EQ_INE742F01042/20251231_20260130_5029f05d2b82c692/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/daily_regime_v2/CDSL/20260115_20260130_0a6931ac13da6265/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/daily_regime_v2/CDSL/20260115_20260130_0a6931ac13da6265/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/daily_regime_v2/CDSL/20260115_20260130_280b1d361b7ca598/equity.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/daily_regime_v2/CDSL/20260115_20260130_280b1d361b7ca598/signals.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/daily_regime_v2/CDSL/20260115_20260130_280b1d361b7ca598/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/daily_regime_v2/CDSL/20260115_20260130_280b1d361b7ca598/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/daily_regime_v2/CDSL/20260115_20260130_280b1d361b7ca598/trades.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/CDSL/20260115_20260130_020df70f99298f6c/equity.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/CDSL/20260115_20260130_020df70f99298f6c/signals.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/CDSL/20260115_20260130_020df70f99298f6c/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/CDSL/20260115_20260130_020df70f99298f6c/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/CDSL/20260115_20260130_020df70f99298f6c/trades.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/CDSL/20260115_20260130_52126c570bc64ac5/equity.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/CDSL/20260115_20260130_52126c570bc64ac5/signals.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/CDSL/20260115_20260130_52126c570bc64ac5/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/CDSL/20260115_20260130_52126c570bc64ac5/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/CDSL/20260115_20260130_52126c570bc64ac5/trades.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_2997475bc42c920f/equity.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_2997475bc42c920f/signals.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_2997475bc42c920f/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_2997475bc42c920f/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_2997475bc42c920f/trades.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_578113443464f543/equity.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_578113443464f543/signals.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_578113443464f543/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_578113443464f543/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_578113443464f543/trades.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_b3c2e916a69f0407/equity.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_b3c2e916a69f0407/signals.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_b3c2e916a69f0407/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_b3c2e916a69f0407/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_b3c2e916a69f0407/trades.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_eecf4867e97ac730/equity.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_eecf4867e97ac730/signals.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_eecf4867e97ac730/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_eecf4867e97ac730/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_eecf4867e97ac730/trades.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_f6280ad11205e97c/signals.csv` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_f6280ad11205e97c/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ehma_pivot/NSE_EQ_INE742F01042/20251231_20260130_f6280ad11205e97c/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ultimate_trading_dashboard/NSE_EQ_INE00H001014/20260101_20260131_e2740834c65338b7/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ultimate_trading_dashboard/NSE_EQ_INE00H001014/20260101_20260131_e2740834c65338b7/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ultimate_trading_dashboard/NSE_EQ_INE854D01024/20260101_20260131_75c4d1554d6a0e1c/spec.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `backfills/ultimate_trading_dashboard/NSE_EQ_INE854D01024/20260101_20260131_75c4d1554d6a0e1c/summary.json` | Backtesting Framework | `0` | Delete | Derived backtest output; reproducible and safe to regenerate. |
| `CLAUDE.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `config/__pycache__/settings.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `config/__pycache__/settings.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `config/credentials.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `config/credentials.py` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `config/credentials.template.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `config/market_universe.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `config/settings.py` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `config/zmq.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `config/zmq_test.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `config/zmq_test_2.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/__init__.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/__pycache__/clock.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/__pycache__/clock.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/__pycache__/events.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/__pycache__/events.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/__pycache__/runner.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/__pycache__/runner.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/alerts/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/alerts/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/alerts/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/alerts/__pycache__/alerter.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/alerts/__pycache__/alerter.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/alerts/__pycache__/telegram_notifier.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/alerts/__pycache__/telegram_notifier.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/alerts/alerter.py` | Monitoring | `1` | Keep | Captures logs, telemetry, health, or operational status. |
| `core/alerts/telegram_notifier.py` | Monitoring | `0` | Keep | Captures logs, telemetry, health, or operational status. |
| `core/analytics/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/capture.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/capture.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/confluence_engine.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/confluence_engine.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/day_features.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/day_features.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/diagnostic_engine.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/diagnostic_engine.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/dispersion.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/metrics_service.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/metrics_service.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/models.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/models.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/options_analytics.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/options_analytics.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/pixityAI_feature_factory.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/pixityAI_feature_factory.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/resampler.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/__pycache__/resampler.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/capture.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/analytics/confluence_engine.py` | Infrastructure | `8` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/analytics/day_features.py` | Indicator Logic | `1` | Keep | Computes indicators, features, or market-derived signals. |
| `core/analytics/diagnostic_engine.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/analytics/dispersion.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/analytics/indicators/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/adx.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/adx.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/atr.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/atr.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/base.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/base.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/ema.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/ema.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/macd.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/macd.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/rsi.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/rsi.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/ut_bot.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/ut_bot.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/vwap.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/__pycache__/vwap.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/analytics/indicators/adx.py` | Indicator Logic | `1` | Keep | Computes indicators, features, or market-derived signals. |
| `core/analytics/indicators/atr.py` | Indicator Logic | `1` | Keep | Computes indicators, features, or market-derived signals. |
| `core/analytics/indicators/base.py` | Indicator Logic | `0` | Keep | Computes indicators, features, or market-derived signals. |
| `core/analytics/indicators/ema.py` | Indicator Logic | `1` | Keep | Computes indicators, features, or market-derived signals. |
| `core/analytics/indicators/macd.py` | Indicator Logic | `1` | Keep | Computes indicators, features, or market-derived signals. |
| `core/analytics/indicators/rsi.py` | Indicator Logic | `1` | Keep | Computes indicators, features, or market-derived signals. |
| `core/analytics/indicators/ut_bot.py` | Indicator Logic | `1` | Keep | Computes indicators, features, or market-derived signals. |
| `core/analytics/indicators/vwap.py` | Indicator Logic | `2` | Keep | Computes indicators, features, or market-derived signals. |
| `core/analytics/metrics_service.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/analytics/models.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/analytics/options_analytics.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/analytics/pixityAI_feature_factory.py` | Indicator Logic | `1` | Keep | Computes indicators, features, or market-derived signals. |
| `core/analytics/pixityAI_labeler.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/analytics/populator.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/analytics/regime_engine.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/analytics/resampler.py` | Indicator Logic | `0` | Keep | Computes indicators, features, or market-derived signals. |
| `core/api/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/api/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/api/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/api/__pycache__/upstox_client.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/api/__pycache__/upstox_client.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/api/upstox_client.py` | Broker Integration | `0` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `core/auth/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/__pycache__/auth_service.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/__pycache__/auth_service.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/__pycache__/credentials.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/__pycache__/credentials.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/__pycache__/models.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/__pycache__/models.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/__pycache__/password.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/__pycache__/password.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/auth/auth_service.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/auth/credentials.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/auth/models.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/auth/password.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/backtest/__pycache__/usdinr_attribution.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/backtest/__pycache__/usdinr_attribution.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/backtest/portfolio_backtest.py` | Backtesting Framework | `5` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `core/backtest/runner.py` | Backtesting Framework | `18` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `core/backtest/scan_persistence.py` | Backtesting Framework | `3` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `core/backtest/symbol_scanner.py` | Backtesting Framework | `2` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `core/backtest/usdinr_attribution.py` | Backtesting Framework | `0` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `core/brokers/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/base.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/base.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/broker_base.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/broker_base.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/mock_broker_adapter.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/mock_broker_adapter.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/paper_broker.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/paper_broker.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/upstox_market_data.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/__pycache__/upstox_market_data.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/brokers/base.py` | Broker Integration | `2` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `core/brokers/broker_base.py` | Broker Integration | `1` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `core/brokers/mock_broker_adapter.py` | Broker Integration | `3` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `core/brokers/paper_broker.py` | Broker Integration | `5` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `core/brokers/upstox_adapter.py` | Broker Integration | `4` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `core/brokers/upstox_market_data.py` | Broker Integration | `1` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `core/clock.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/__init__.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/data/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/data/__pycache__/MarketDataFeedV3_pb2.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/data/__pycache__/MarketDataFeedV3_pb2.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/data/__pycache__/options_provider.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/data/__pycache__/options_provider.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/data/analytics_provider.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/cached_analytics_provider.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/db_tick_aggregator.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/duckdb_analytics_provider.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/duckdb_client.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/duckdb_market_data_provider.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/historical_market_provider.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/live_market_provider.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/market_data_provider.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/market_hours.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/market_session.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/MarketDataFeedV3.proto` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/MarketDataFeedV3_pb2.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/options_provider.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/recovery_manager.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/schema.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/symbol_utils.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/tick_aggregator.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/data/websocket_ingestor.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/__init__.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/legacy_adapter.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/legacy_adapter.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/locks.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/locks.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/manager.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/manager.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/queries.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/queries.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/schema.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/schema.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/writers.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/__pycache__/writers.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/ingestors/__init__.py` | Data Pipeline | `0` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/ingestors/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/ingestors/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/ingestors/__pycache__/db_tick_aggregator.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/ingestors/__pycache__/db_tick_aggregator.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/ingestors/__pycache__/recovery_manager.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/ingestors/__pycache__/recovery_manager.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/ingestors/__pycache__/websocket_ingestor.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/ingestors/__pycache__/websocket_ingestor.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/ingestors/db_tick_aggregator.py` | Data Pipeline | `2` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/ingestors/recovery_manager.py` | Data Pipeline | `3` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/ingestors/websocket_ingestor.py` | Data Pipeline | `2` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/legacy_adapter.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/locks.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/manager.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/providers/__init__.py` | Data Pipeline | `5` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/providers/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/analytics.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/analytics.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/base.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/base.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/live_market.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/live_market.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/market_data.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/market_data.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/zmq_market.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/__pycache__/zmq_market.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/providers/analytics.py` | Data Pipeline | `5` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/providers/base.py` | Data Pipeline | `1` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/providers/live_market.py` | Data Pipeline | `4` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/providers/market_data.py` | Data Pipeline | `5` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/providers/resampling_wrapper.py` | Data Pipeline | `6` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/providers/zmq_market.py` | Data Pipeline | `5` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `core/database/queries.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/schema.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/utils/__init__.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/utils/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/utils/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/utils/__pycache__/market_hours.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/utils/__pycache__/market_hours.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/utils/__pycache__/market_session.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/utils/__pycache__/market_session.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/utils/__pycache__/symbol_utils.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/utils/__pycache__/symbol_utils.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/database/utils/market_hours.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/utils/market_session.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/utils/symbol_utils.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/database/writers.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/events.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/__init__.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/handler.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/handler.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/margin_tracker.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/margin_tracker.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/order_factory.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/order_factory.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/order_lifecycle.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/order_lifecycle.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/order_models.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/order_models.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/order_tracker.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/order_tracker.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/pixityAI_risk_engine.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/pixityAI_risk_engine.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/pnl_tracker.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/pnl_tracker.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/position_models.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/position_models.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/position_tracker.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/position_tracker.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/reconciliation.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/reconciliation.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/risk_manager.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/risk_manager.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/risk_models.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/risk_models.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/rules.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/__pycache__/rules.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/backfill_models.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/groups/__pycache__/group_pnl.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/groups/__pycache__/group_pnl.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/groups/__pycache__/group_tracker.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/groups/__pycache__/group_tracker.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/groups/__pycache__/order_group.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/groups/__pycache__/order_group.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/groups/group_pnl.py` | Risk Management | `3` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/execution/groups/group_tracker.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/groups/order_group.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/handler.py` | Infrastructure | `33` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/health_monitor.py` | Monitoring | `0` | Keep | Captures logs, telemetry, health, or operational status. |
| `core/execution/margin_tracker.py` | Risk Management | `1` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/execution/options/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/options/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/options/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/options/__pycache__/selector.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/options/__pycache__/selector.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/options/selector.py` | Strategy Logic | `2` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/execution/order_factory.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/order_lifecycle.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/order_models.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/order_tracker.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/persistence/__pycache__/execution_store.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/persistence/__pycache__/execution_store.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/persistence/__pycache__/fill_repository.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/persistence/__pycache__/fill_repository.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/persistence/__pycache__/order_repository.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/persistence/__pycache__/order_repository.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/persistence/__pycache__/position_repository.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/persistence/__pycache__/position_repository.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/execution/persistence/execution_store.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/persistence/fill_repository.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/persistence/order_repository.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/execution/persistence/position_repository.py` | Risk Management | `3` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/execution/pixityAI_risk_engine.py` | Risk Management | `2` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/execution/pnl_tracker.py` | Risk Management | `2` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/execution/position_models.py` | Risk Management | `2` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/execution/position_tracker.py` | Risk Management | `5` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/execution/reconciliation.py` | Risk Management | `1` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/execution/risk_manager.py` | Risk Management | `2` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/execution/risk_models.py` | Risk Management | `0` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/execution/rules.py` | Risk Management | `0` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/instruments/__pycache__/equity.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/equity.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/future.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/future.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/instrument_base.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/instrument_base.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/instrument_db.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/instrument_db.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/instrument_parser.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/instrument_parser.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/option.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/__pycache__/option.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/instruments/equity.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/instruments/future.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/instruments/instrument_base.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/instruments/instrument_db.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/instruments/instrument_parser.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/instruments/option.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/logging/__init__.py` | Monitoring | `0` | Keep | Captures logs, telemetry, health, or operational status. |
| `core/logging/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/logging/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/logging/__pycache__/log_reader.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/logging/__pycache__/log_reader.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/logging/__pycache__/logger.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/logging/__pycache__/logger.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/logging/log_reader.py` | Monitoring | `0` | Keep | Captures logs, telemetry, health, or operational status. |
| `core/logging/logger.py` | Monitoring | `2` | Keep | Captures logs, telemetry, health, or operational status. |
| `core/messaging/__init__.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/messaging/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/messaging/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/messaging/__pycache__/telemetry.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/messaging/__pycache__/telemetry.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/messaging/__pycache__/zmq_handler.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/messaging/__pycache__/zmq_handler.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/messaging/options_publisher.py` | Monitoring | `3` | Keep | Captures logs, telemetry, health, or operational status. |
| `core/messaging/telemetry.py` | Monitoring | `1` | Keep | Captures logs, telemetry, health, or operational status. |
| `core/messaging/zmq_handler.py` | Monitoring | `0` | Keep | Captures logs, telemetry, health, or operational status. |
| `core/models/nifty_shield_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/pixityAI_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/pixityAI_global_15m.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_ine002a01018_15m.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_ine002a01018_15m_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/pixityAI_ine002a01018_15m_oos.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_ine002a01018_15m_oos_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/pixityAI_ine002a01018_1h.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_ine002a01018_1h_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/pixityAI_ine002a01018_1h_oos.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_ine002a01018_1h_oos_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/pixityAI_ine040a01034_15m.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_ine040a01034_15m_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/pixityAI_ine040a01034_15m_oos.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_ine040a01034_15m_oos_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/pixityAI_ine040a01034_1h.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_ine040a01034_1h_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/pixityAI_ine040a01034_1h_oos.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_ine040a01034_1h_oos_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/pixityAI_meta_filter.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_nifty50_15m.joblib` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `core/models/pixityAI_nifty50_15m_config.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/models/regime_map_validation.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `core/portfolio/__init__.py` | Risk Management | `1` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/portfolio/allocator.py` | Risk Management | `0` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/portfolio/engine.py` | Risk Management | `0` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/post_trade/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/post_trade/trade_truth_model.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/risk/greeks/__pycache__/black76_engine.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/risk/greeks/__pycache__/black76_engine.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/risk/greeks/__pycache__/greeks_calculator.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/risk/greeks/__pycache__/greeks_calculator.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/risk/greeks/__pycache__/greeks_model.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/risk/greeks/__pycache__/greeks_model.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/risk/greeks/__pycache__/portfolio_greeks.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/risk/greeks/__pycache__/portfolio_greeks.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/risk/greeks/black76_engine.py` | Risk Management | `1` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/risk/greeks/greeks_calculator.py` | Risk Management | `6` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/risk/greeks/greeks_model.py` | Risk Management | `0` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/risk/greeks/portfolio_greeks.py` | Risk Management | `5` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/runner.py` | Infrastructure | `13` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/state/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/state/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/state/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/state/__pycache__/daytype_engine.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/state/__pycache__/daytype_engine.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/state/daytype_engine.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `core/strategies/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/base.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/base.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/daily_regime_strategy_v2.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/daily_regime_strategy_v2.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/ehma_pivot.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/ehma_pivot.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/nifty_shield_strategy.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/nifty_shield_strategy.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/pixityAI_event_generator.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/pixityAI_event_generator.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/pixityAIMetaStrategy.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/pixityAIMetaStrategy.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/registry.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/registry.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/stock_daytype_paper.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/stock_daytype_paper.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/v9_pm_scalper.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/v9_pm_scalper.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/v9_pm_scalper_strategy.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/__pycache__/v9_pm_scalper_strategy.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/base.py` | Strategy Logic | `2` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/commodity_trend.py` | Strategy Logic | `2` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/daily_regime_strategy_v2.py` | Strategy Logic | `2` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/ehma_pivot.py` | Strategy Logic | `2` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/nifty_shield_strategy.py` | Risk Management | `11` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `core/strategies/options_portfolio/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/options_portfolio/__pycache__/directional_spread.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/options_portfolio/__pycache__/dispersion.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/options_portfolio/__pycache__/event_calendar.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/options_portfolio/__pycache__/iron_condor.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/options_portfolio/__pycache__/position_book.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/options_portfolio/__pycache__/risk_guard.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/options_portfolio/__pycache__/vix_regime.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `core/strategies/pixityAI_batch_events.py` | Strategy Logic | `4` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/pixityAI_event_generator.py` | Strategy Logic | `6` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/pixityAIMetaStrategy.py` | Strategy Logic | `4` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/precomputed_signals.py` | Strategy Logic | `2` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/regime/__init__.py` | Strategy Logic | `2` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/regime/classifier.py` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/regime/observer.py` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/registry.py` | Strategy Logic | `1` | Keep | Defines trading rules, signal generation, or execution intent. |
| `core/strategies/stock_daytype_paper.py` | Strategy Logic | `2` | Keep | Defines trading rules, signal generation, or execution intent. |
| `data/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `data/backtest/backtest_index.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/backtest/summaries/backtest_index.db` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/backtest/v3_compression_candidates.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/backtest_index.db` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `data/config.db` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `data/config/.writer.lock` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/config/config.db` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/data_manager_duckdb.py` | Data Pipeline | `1` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `data/execution.db` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/am_checkpoint_edge.json` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/am_session_diagnostic.json` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/breadth_cluster_centroids.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/breadth_cluster_labels.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/breadth_cluster_summary.txt` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/cluster_centroids.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/cluster_labels.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/cluster_summary.txt` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/intraday_features_10am.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/intraday_features_11am.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/intraday_features_13pm.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/nifty50_breadth_2023.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/nifty50_breadth_2024.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/nifty50_breadth_2025.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/nifty50_breadth_2026.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/nifty_day_features_2023.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/nifty_day_features_2024.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/nifty_day_features_2025.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/nifty_day_features_2026.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/pca_variance.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/pm_expectancy.json` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/pm_expectancy_raw.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/pm_expectancy_raw_v2.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/pm_timing_stats.json` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/remaining_excursion.json` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/stock_930am_test_results.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/stocks_fast_2023.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/stocks_fast_2024.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/stocks_fast_2025.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/stocks_fast_2026.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/stocks_universal_labels.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/day_type/v9_trades.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/features/dispersion_results.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/instruments/nse_fo_instruments.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/live_buffer/.last_rollover` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/live_buffer/.writer.lock` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/live_buffer/candles_today.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/live_buffer/ticks_today.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/.schema_version` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/.writer.lock` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/mcx/candles/1m/2026-03-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-01-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-02-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-03-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-04-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-05-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-06-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-07-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-08-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-09-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-10-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-11-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2023-12-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-01-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-02-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-03-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-04-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-05-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-06-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-07-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-08-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-09-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-10-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-11-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2024-12-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-01-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-02-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-03-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-04-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-05-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-06-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-07-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-08-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-09-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-10-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-11-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2025-12-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-01-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1d/2026-02-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-01-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-02-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-03-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-04-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-05-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-06-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-07-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-08-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-09-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-10-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-11-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2023-12-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-01-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-02-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-03-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-04-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-05-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-06-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-07-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-08-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-09-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-10-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-11-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2024-12-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-01-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-02-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-03-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-04-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-05-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-06-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-07-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-08-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-09-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-10-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-11-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2025-12-31.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-14.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-01-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-26.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-02-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-03.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-12.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-18.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-19.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-25.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-03-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-01.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-02.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-09.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-10.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-13.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-15.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-16.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-17.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-20.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-21.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-22.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-23.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-24.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-27.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-28.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-29.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-04-30.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-05-04.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-05-05.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-05-06.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-05-07.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-05-08.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/nse/candles/1m/2026-05-11.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/options.duckdb.wal` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/market_data/options_poller.duckdb` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/nifty-50-stock-list.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/pixityAI_labeled_events.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/pixityAI_labeled_events_ine002a01018_15m.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/pixityAI_labeled_events_ine002a01018_1h.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/pixityAI_labeled_events_ine040a01034_15m.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/pixityAI_labeled_events_ine040a01034_1h.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/pixityAI_labeled_events_nifty50_15m.csv` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/regime_backtest_results.json` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/resampler_duckdb.py` | Data Pipeline | `1` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `data/scanner/scanner_index.db` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/signals/.writer.lock` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/signals/signals.db` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/trading.db` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/trading/.writer.lock` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/trading/trading.db` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/trading/trading.db-shm` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
| `data/trading/trading.db-wal` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `DEVELOPER_GUIDE.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/BREADTH_INFRASTRUCTURE.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/Claudereasearch-12052026.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/CLEANUP_AUDIT_REPORT_2026-03-13.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/CODEBASE_OVERVIEW.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/COLLABORATOR_STRATEGY_BRIEF.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/COMMODITY_TRADING_IMPLEMENTATION_SUMMARY.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/COMMODITY_TRADING_SYSTEM_PLAN.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/DATA_PIPELINE.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/DAYTYPE_CLASSIFIER.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/DISPERSION_RESEARCH_IMPLEMENTATION_PLAN.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/EDGE_ANALYSIS.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/FTMO_CHALLENGE_SYSTEM.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/FTMO_LIVE_DATA_PIPELINE.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/ftmo_trading_plan.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/FTMO_V2_IMPLEMENTATION_SUMMARY.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/HMM_REGIME_STRATEGY_REPORT.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/INDEX_MICROSTRUCTURE_PROFILING.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/LIVE_READINESS_AUDIT_REPORT.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/mcx_commodity_strategy.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/mcx_commodity_strategy_plan.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/MCX_GOLD_OPTIONS_COMMODITY_INTEGRATION_REPORT.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/NIFTYSHIELD_IMPLEMENTATION.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/OPTIONS_ANALYSIS_DASHBOARD_PLAN.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/SIGNAL_QUALITY_FILTERS_USAGE.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/SIGNAL_QUALITY_IMPLEMENTATION_SUMMARY.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/SIGNAL_QUALITY_PIPELINE_DESIGN.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/STOCK_DAYTYPE_CLASSIFIER.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/STRATEGY LAYOUT.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/STRATEGY_RESEARCH_LOG.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/superpowers/plans/2026-05-12-options-portfolio.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/SWEEP_CLASSIFIER_REPORT.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/TRADE_LEARNING_PROTOCOL_V1.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/V9_INTEGRATION_SUMMARY.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `docs/V9_OPTIONS_INTEGRATION.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `entities.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `flask_app/__init__.py` | Infrastructure | `15` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/__pycache__/middleware.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/__pycache__/middleware.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/auth.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/auth.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/backtest.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/backtest.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/commodities.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/commodities.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/dashboard.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/dashboard.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/database.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/database.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/niftyshield.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/niftyshield.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/options.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/options.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/options_portfolio.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/paper_trading.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/paper_trading.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/propdeskmode.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/propdeskmode.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/scanner.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/__pycache__/scanner.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/auth.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/backtest.py` | Infrastructure | `10` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/commodities.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/dashboard.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/database.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/niftyshield.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/ops/__init__.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/ops/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/ops/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/ops/__pycache__/routes.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/ops/__pycache__/routes.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `flask_app/blueprints/ops/routes.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/options.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/propdeskmode.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/scanner.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/blueprints/Signal & Trend by strat` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/middleware.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/telemetry_bridge.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/auth/login.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/backtest/index.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/base.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/commodities/index.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/dashboard.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/database/index.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/ftmo/index.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/niftyshield/index.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/ops/index.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/options/index.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/paper_trading/index.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/propdeskmode/index.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `flask_app/templates/scanner/index.html` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/.calendar_cache.json` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/__init__.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/__main__.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/analytics.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/analytics.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/blueprint.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/blueprint.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/cli.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/cli.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/config.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/config.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/db.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/db.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/detector.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/detector.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/engine.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/engine.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/indicators.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/indicators.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/ingest.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/ingest.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/kline_tokenizer.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/kline_tokenizer.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/live_trader.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/live_trader.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/mt5_downloader.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/mt5_downloader.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/mt5_time.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/mt5_time.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/portfolio_backtester.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/portfolio_backtester.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/portfolio_trader.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/portfolio_trader.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/risk.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/risk.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/rolling_live_trader.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/rolling_live_trader.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/session.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/session.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/simulation.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/simulation.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/sweep_classifier.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/__pycache__/sweep_classifier.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/alpha_seeker_eurusd.csv` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `ftmo/alpha_seeker_us100.csv` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `ftmo/alpha_seeker_xauusd.csv` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `ftmo/analytics.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/blueprint.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/cache_eurusd_m5-old.parquet` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/cache_eurusd_m5.parquet` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/cache_gbpjpy_m5.parquet` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/cache_gbpusd_m5.parquet` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/cache_m5.parquet` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/cache_rolling_xauusd_m5.parquet` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/cache_us30_cash_m5.parquet` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/cache_ustec_m5.parquet` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/cache_xagusd_m5.parquet` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/cache_xauusd_m5-old.parquet` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/cache_xauusd_m5.parquet` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/cli.py` | Infrastructure | `18` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/config.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/db.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/detector.py` | Strategy Logic | `2` | Keep | Defines trading rules, signal generation, or execution intent. |
| `ftmo/docs/ALPHASEEKER_HTF_IMPLEMENTATION.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `ftmo/docs/FTMO_PROP_CHALLENGE_RESEARCH.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `ftmo/download_data.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/download_eurusd.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `ftmo/download_xauusd.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `ftmo/engine.py` | Backtesting Framework | `5` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `ftmo/EURUSD_M5.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/ftmo_trading.db` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/GBPJPY_M5.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/GBPUSD_M5.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/indicators.py` | Indicator Logic | `1` | Keep | Computes indicators, features, or market-derived signals. |
| `ftmo/ingest.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/kline_tokenizer.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/kline_vocab.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/kline_vocab_eurusd.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/kline_vocab_gbp.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/kline_vocab_gbpjpy.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/kline_vocab_gbpusd.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/kline_vocab_us30_cash.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/kline_vocab_xagusd.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/live_session_20260426.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `ftmo/live_session_20260427.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `ftmo/live_session_xauusd_20260527.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `ftmo/live_session_xauusd_20260528.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `ftmo/live_session_xauusd_20260602.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `ftmo/live_trader.py` | Broker Integration | `6` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `ftmo/mt5_downloader.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/mt5_time.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/portfolio_backtester.py` | Backtesting Framework | `3` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `ftmo/portfolio_scan_diagnostics.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/portfolio_trader.py` | Broker Integration | `12` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `ftmo/research/__init__.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/acceptance_structure.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/baselines.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/compound_filter.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/context_classifier.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/continuation_features.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/early_exit_gate.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/exit_simulator.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/htf_builder.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/risk_overlay.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/stats.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/sweep_features.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/trade_lifecycle.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/trade_tagger.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/__pycache__/walkforward.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/research/acceptance_structure.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/baseline_c_sessions_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/baselines.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/baselines_xauusd.json` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/compound_filter.py` | Research Utility | `2` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/context_classifier.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/context_combos_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/continuation_features.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/early_exit_gate.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/exit_simulator.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/htf_builder.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/marginal_effects_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_by_outcome_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_close_location_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_compression_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_features_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_reclaim_speed_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_rej_vs_acc_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_score_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_time_outside_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_wf_test_rva_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_wf_test_score_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_wf_train_rva_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/acceptance_wf_train_score_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/compression_h4trend_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/compression_rolling_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/continuation_by_outcome_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/continuation_correlations_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/continuation_features_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/exit_models_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/failure_states_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/gate_htf_redundancy_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/gate_test_comparison_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/gate_test_conditional_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/gate_train_comparison_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/gate_train_conditional_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/lifecycle_summary_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/lifecycle_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/mfe_distribution_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/phase10_counts_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/phase10_summary_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/phase10_year_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/phase8_summary_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/phase9_atr_gate_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/phase9_final_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/risk_overlay_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/s0_baseline_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/s1_baseline_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/sweep_closed_above_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/sweep_correlations_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/sweep_depth_buckets_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/sweep_depth_rolling_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/sweep_features_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/phase2/time_distribution_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/risk_overlay.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/stats.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/sweep_features.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/tagged_trades_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/trade_lifecycle.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/trade_tagger.py` | Research Utility | `5` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/walkforward.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/window_summary_anchored_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/research/window_summary_rolling_xauusd.csv` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `ftmo/risk.py` | Risk Management | `1` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `ftmo/rolling_live_trader.py` | Broker Integration | `5` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `ftmo/session.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/simulation.py` | Backtesting Framework | `3` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `ftmo/strategies/__pycache__/base.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/strategies/__pycache__/base.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/strategies/__pycache__/london_breakout.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/strategies/__pycache__/london_breakout.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/strategies/__pycache__/ny_momentum.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/strategies/__pycache__/ny_momentum.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/strategies/__pycache__/sweep_reversal.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/strategies/__pycache__/sweep_reversal.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/strategies/__pycache__/trend_pullback.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/strategies/__pycache__/trend_pullback.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmo/strategies/base.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/strategies/london_breakout.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/strategies/ny_momentum.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/strategies/sweep_reversal.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/strategies/trend_pullback.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_classifier.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_eurusd.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_eurusd_s1.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_eurusd_s2.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_gbpjpy.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_gbpjpy_s1.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_gbpjpy_s2.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_gbpusd.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_gbpusd_s1.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_gbpusd_s2.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_s1.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_s2.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_us30_cash.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_us30_cash_s1.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_us30_cash_s2.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_xagusd.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_xagusd_s1.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_clf_xagusd_s2.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_labels.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_labels_eurusd.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_labels_gbpjpy.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_labels_gbpusd.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_labels_us30_cash.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/sweep_labels_xagusd.pkl` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/trade_log.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/trade_log_eurusd.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/trade_log_rolling_xauusd.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/trade_log_xauusd.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/US100_M5.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/US30.cash_M5.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/USTEC_M5.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/XAGUSD_M5.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmo/XAUUSD_M5.csv` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ftmoresearchphase2` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `ftmoresearchphase2s0_baseline_xauusd.csv` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `logs/backtest_bp.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/commodity_runner.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/daily_fill.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/database_bp.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/eod_rollover.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/execution_handler.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/execution_handler.log.1` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/execution_handler.log.2` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/execution_handler.log.3` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/execution_handler.log.4` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/execution_metrics.json` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/flask.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/flask_app.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/health_status.json` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/heartbeat.json` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/historical_fetch.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/intermarket_fetch.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/live_runner.log` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `logs/manual_fix.log` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `logs/market_ingestor.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/market_ingestor_status.json` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/nifty_shield_runner.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/nifty_shield_strategy.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/ns_backtest.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/options.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/options_analytics.log` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `logs/options_bp.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/options_facade.log` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `logs/options_portfolio_bp.log` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `logs/options_portfolio_runner.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/options_provider.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/options_publisher.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/options_runner.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/regime_backtest.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/sessions/session_20260130.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `logs/sessions/session_20260205.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `logs/sessions/session_20260206.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `logs/sessions/session_20260209.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `logs/smoke_metrics.json` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/stock_daytype_runner.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/trading_runner.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/trading_runner.log.1` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/trading_runner.log.2` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/trading_runner.log.3` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/trading_runner.log.4` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/trading_runner.log.5` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/unified_live_runner.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/v9_paper_live.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/v9_paper_trades.csv` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `logs/v9_pm_runner.log` | Monitoring | `0` | Delete | Generated operational log or telemetry artifact; not source-of-truth code. |
| `mempalace.yaml` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/lgbm_10am/metadata.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/lgbm_10am/model.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/lgbm_10am/scaler.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/lgbm_11am/metadata.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/lgbm_11am/model.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/lgbm_11am/scaler.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/lgbm_13pm/metadata.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/lgbm_13pm/model.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/lgbm_13pm/scaler.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_10am/metadata.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_10am/model.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_10am/scaler.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_11am/metadata.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_11am/model.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_11am/scaler.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_13pm/metadata.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_13pm/model.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_13pm/scaler.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_13pm_prod/metadata.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_13pm_prod/model.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_13pm_prod/scaler.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_v1_13pm_prod/metadata.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_v1_13pm_prod/model.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_v1_13pm_prod/scaler.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_v2_13pm_prod/metadata.json` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_v2_13pm_prod/model.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/logistic_v2_13pm_prod/scaler.pkl` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_1000am/features.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_1000am/model.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_1000am/scaler.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_1000am_enhanced/features.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_1000am_enhanced/model.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_1000am_enhanced/scaler.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_930am/features.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_930am/model.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_930am_enhanced/features.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_930am_enhanced/model.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/stock_930am_enhanced/scaler.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/universal_stocks/kmeans_3.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `models/daytype/universal_stocks/scaler.joblib` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `ops/change_proposal.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `ops/decision_gate.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `ops/session_log.py` | Monitoring | `0` | Keep | Captures logs, telemetry, health, or operational status. |
| `PROJECT_REVIEW_SUMMARY.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `pyproject.toml` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `README.md` | Documentation | `0` | Keep | Narrative documentation or operational notes. |
| `requirements.txt` | Configuration | `0` | Keep | Defines runtime settings, model metadata, or project config. |
| `risk/__init__.py` | Risk Management | `0` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `risk/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `risk/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `risk/__pycache__/premium_risk_model.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `risk/__pycache__/premium_risk_model.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `risk/premium_risk_model.py` | Risk Management | `0` | Keep | Controls sizing, exposure, stops, limits, or portfolio risk. |
| `scripts/__pycache__/alpha_seeker_eurusd.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/alpha_seeker_gbpusd.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/daily_historical_fill.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/daily_historical_fill.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/fetch_instrument_master.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/fetch_instrument_master.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/init_refactored_db.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/init_refactored_db.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/label_sweeps.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/market_ingestor.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/market_ingestor.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/nifty_shield_runner.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/nifty_shield_runner.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/options_portfolio_runner.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/stock_daytype_runner.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/stock_daytype_runner.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/train_sweep_clf.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/v9_pm_runner.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/__pycache__/v9_pm_runner.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `scripts/alpha_seeker_eurusd.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/alpha_seeker_gbpusd.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/alpha_seeker_htf.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/alpha_seeker_london_breakout.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/alpha_seeker_phase2.py` | Infrastructure | `11` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/alpha_seeker_us100.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/alpha_seeker_xauusd.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/analyze_conf.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/analyze_conf_v2.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/analyze_detailed.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/analyze_scan.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/analyze_trade_context.py` | Research Utility | `4` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/audit_breadth_expectancy.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/audit_index_breadth_interaction.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/audit_stock_breadth_confluence.py` | Research Utility | `2` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/backfill_strategies.py` | Backtesting Framework | `0` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/backtest.py` | Backtesting Framework | `2` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/backtest_breadth_rs_filter.py` | Backtesting Framework | `2` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/backtest_stock_breadth_filter.py` | Backtesting Framework | `2` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/backtest_stock_classifier_performance.py` | Backtesting Framework | `0` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/backup.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/bar1_exit_test.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/build_intraday_features.py` | Indicator Logic | `2` | Keep | Computes indicators, features, or market-derived signals. |
| `scripts/build_stock_day_features.py` | Indicator Logic | `3` | Keep | Computes indicators, features, or market-derived signals. |
| `scripts/build_stock_features_fast.py` | Indicator Logic | `2` | Keep | Computes indicators, features, or market-derived signals. |
| `scripts/causal_stock_pipeline.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/check_database_imports.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/check_db_schema.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/check_mcx_instruments.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/check_scan_progress.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/check_scanner_data.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/cleanup_data.py` | Data Pipeline | `1` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `scripts/clear_runner_state.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/cluster_breadth_day_types.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/cluster_day_types.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/cluster_stocks_universal.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/compare_10am_models.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/daily_historical_fill.py` | Data Pipeline | `7` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `scripts/daily_review.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/diagnose_am_checkpoint_edge.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/diagnose_am_session.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/diagnose_data.py` | Research Utility | `2` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/diagnose_remaining_excursion.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/diagnostic_split.py` | Research Utility | `4` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/download_dukascopy.py` | Data Pipeline | `0` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `scripts/evaluate_intraday_prediction.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/fetch_instrument_master.py` | Data Pipeline | `0` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `scripts/fetch_intermarket_data.py` | Data Pipeline | `7` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `scripts/fetch_upstox_historical.py` | Broker Integration | `7` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `scripts/fix_db.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/generate_breadth_features.py` | Indicator Logic | `2` | Keep | Computes indicators, features, or market-derived signals. |
| `scripts/generate_comprehensive_stock_features.py` | Data Pipeline | `3` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `scripts/generate_day_features.py` | Indicator Logic | `2` | Keep | Computes indicators, features, or market-derived signals. |
| `scripts/health_check.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/init_db.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/init_refactored_db.py` | Research Utility | `3` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/inspect_db.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/label_sweeps.py` | Research Utility | `6` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/listen_telemetry.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/live_daytype_engine.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/live_runner.py` | Broker Integration | `14` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `scripts/manage_users.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/market_data_node.py` | Data Pipeline | `3` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `scripts/market_ingestor.py` | Broker Integration | `11` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `scripts/market_scanner_node.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/migrate_monolith_to_isolated.py` | Research Utility | `3` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/migrate_v9_to_db.py` | Research Utility | `2` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/mock_zmq_publisher.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/nifty_shield_backtest.py` | Backtesting Framework | `4` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/nifty_shield_realdata_backtest.py` | Backtesting Framework | `4` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/nifty_shield_runner.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/optimize_premium_tp_sl.py` | Research Utility | `11` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/perform_structural_review.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/pm_timing_stats.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/populate_fo_stocks.py` | Data Pipeline | `3` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `scripts/quick_comparison.py` | Research Utility | `2` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/research_dispersion.py` | Research Utility | `2` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/research_stock_10am_enhanced.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/research_stock_930am_enhanced.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/rolling_sweep_backtest.py` | Backtesting Framework | `5` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/run_3_sample_backtests.py` | Backtesting Framework | `2` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/run_combo_backtest.py` | Backtesting Framework | `1` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/run_compression_scan.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/run_flask.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/run_options_engine.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/run_overnight_scan.py` | Research Utility | `6` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/run_phase6_scan.ps1` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/run_pm_expectancy.py` | Backtesting Framework | `0` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/run_symbol_scan.py` | Research Utility | `6` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/run_trading.py` | Broker Integration | `2` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `scripts/run_v9_backtest.py` | Backtesting Framework | `0` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/run_v9_paper.py` | Backtesting Framework | `1` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/smoke_test.py` | Research Utility | `9` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/start_all.bat` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/stop_mock_publisher.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/strategy_runner_node.py` | Infrastructure | `13` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/sync_fo_universe.py` | Data Pipeline | `1` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `scripts/test_fetch_options.py` | Data Pipeline | `2` | Keep | Ingestion, transformation, storage, or derived data artifact. |
| `scripts/test_premium_tp_sl.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/test_signal_quality_filters.py` | Research Utility | `1` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/test_single_backtest.py` | Backtesting Framework | `2` | Keep | Simulates, records, or evaluates historical trading behavior. |
| `scripts/test_zmq_market_flow.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/train_daytype_classifier.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/train_gbp_sweep_clf.py` | Research Utility | `6` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/train_global_model.py` | Research Utility | `6` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/train_stock_10am_model.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/train_stock_classifier_930.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/train_sweep_clf.py` | Research Utility | `3` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/unified_live_runner.py` | Broker Integration | `22` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `scripts/unified_runner.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `scripts/update_analytics.py` | Research Utility | `2` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/upstox_auth.py` | Broker Integration | `1` | Keep | Talks to broker APIs, market data feeds, or live order plumbing. |
| `scripts/validate_sweep_clf_holdout.py` | Research Utility | `7` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `scripts/vwap_validation.py` | Indicator Logic | `4` | Keep | Computes indicators, features, or market-derived signals. |
| `scripts/weekly_review.py` | Research Utility | `0` | Keep | Ad hoc analysis, research outputs, training artifacts, or exploratory tooling. |
| `services/__pycache__/commodity_strategy_orchestrator.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `services/__pycache__/commodity_strategy_orchestrator.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `services/commodity_strategy_orchestrator.py` | Strategy Logic | `10` | Keep | Defines trading rules, signal generation, or execution intent. |
| `strategy/__init__.py` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `strategy/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/filters/__init__.py` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `strategy/filters/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/filters/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/filters/__pycache__/liquidity_filter.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/filters/__pycache__/liquidity_filter.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/filters/liquidity_filter.py` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `strategy/options/__init__.py` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `strategy/options/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/options/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/options/__pycache__/strike_selector.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/options/__pycache__/strike_selector.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/options/strike_selector.py` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `strategy/regime/__init__.py` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `strategy/regime/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/regime/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/regime/__pycache__/volatility_regime.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/regime/__pycache__/volatility_regime.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `strategy/regime/volatility_regime.py` | Strategy Logic | `0` | Keep | Defines trading rules, signal generation, or execution intent. |
| `tests/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/__pycache__/conftest.cpython-313-pytest-9.0.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/__pycache__/conftest.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/__pycache__/conftest.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/__pycache__/test_pixityAI_logic.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/__pycache__/test_pixityAI_logic.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/__pycache__/test_runner.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/__pycache__/test_runner.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/analytics/__pycache__/test_options.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/analytics/__pycache__/test_options.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/analytics/__pycache__/test_options_greeks_module.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/analytics/__pycache__/test_options_greeks_module.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/analytics/__pycache__/test_structured_metrics.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/analytics/__pycache__/test_structured_metrics.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/analytics/__pycache__/test_usdinr_attribution.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/analytics/__pycache__/test_usdinr_attribution.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/analytics/test_options.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/analytics/test_options_greeks_module.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/analytics/test_structured_metrics.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/analytics/test_usdinr_attribution.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/auth/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/auth/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/auth/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/auth/__pycache__/test_service.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/auth/__pycache__/test_service.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/auth/test_service.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/conftest.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/database/__init__.py` | Infrastructure | `0` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/database/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/database/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/database/__pycache__/test_manager.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/database/__pycache__/test_manager.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/database/__pycache__/test_queries_instrument_fallback.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/database/__pycache__/test_queries_instrument_fallback.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/database/test_manager.py` | Infrastructure | `5` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/database/test_queries_instrument_fallback.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_broker_integration.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_broker_integration.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_commodity_orchestrator.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_commodity_orchestrator.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_exit_handling.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_exit_handling.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_invariants.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_invariants.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_margin.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_margin.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_multi_leg.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_multi_leg.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_option_parser.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_option_parser.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_option_positioning.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_option_positioning.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_order_intake.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_order_intake.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_order_lifecycle.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_order_lifecycle.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_pnl.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_pnl.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_premium_risk_model.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_premium_risk_model.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_reconciliation.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_reconciliation.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_replay.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_replay.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_risk_integration.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_risk_integration.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_risk_manager.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/__pycache__/test_risk_manager.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/execution/test_broker_integration.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_commodity_orchestrator.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_exit_handling.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_invariants.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_margin.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_multi_leg.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_option_parser.py` | Infrastructure | `4` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_option_positioning.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_order_intake.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_order_lifecycle.py` | Infrastructure | `5` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_pnl.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_premium_risk_model.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_reconciliation.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_replay.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_risk_integration.py` | Infrastructure | `6` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/execution/test_risk_manager.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/flask_app/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/flask_app/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/flask_app/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/flask_app/__pycache__/test_commodities_integration.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/flask_app/__pycache__/test_commodities_integration.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/flask_app/test_commodities_integration.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/ftmo/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/ftmo/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/ftmo/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/ftmo/__pycache__/test_detector.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/ftmo/__pycache__/test_detector.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/ftmo/__pycache__/test_mt5_time.cpython-313-pytest-9.0.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/ftmo/__pycache__/test_mt5_time.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/ftmo/test_detector.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/ftmo/test_mt5_time.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/strategies/__init__.py` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/__init__.cpython-314.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/test_daily_regime_v2.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/test_daily_regime_v2.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/test_ehma_pivot.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/test_ehma_pivot.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/test_liquidity_filter.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/test_liquidity_filter.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/test_strike_selector.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/test_strike_selector.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/test_volatility_regime.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/__pycache__/test_volatility_regime.cpython-314-pytest-8.4.2.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/options_portfolio/__pycache__/__init__.cpython-313.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/options_portfolio/__pycache__/test_directional_spread.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/options_portfolio/__pycache__/test_iron_condor.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/options_portfolio/__pycache__/test_risk_guard.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/options_portfolio/__pycache__/test_vix_regime.cpython-313-pytest-9.0.3.pyc` | Experimental / Dead Code | `0` | Delete | Empty or obsolete artifact with no clear production role. |
| `tests/strategies/test_daily_regime_v2.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/strategies/test_ehma_pivot.py` | Infrastructure | `3` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/strategies/test_liquidity_filter.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/strategies/test_strike_selector.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/strategies/test_volatility_regime.py` | Infrastructure | `1` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/test_pixityAI_logic.py` | Infrastructure | `5` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `tests/test_runner.py` | Infrastructure | `2` | Keep | Platform plumbing, app wiring, or runtime support code. |
| `trading.db` | Data Pipeline | `0` | Delete | Derived data artifact or cache; should not be versioned as source. |
