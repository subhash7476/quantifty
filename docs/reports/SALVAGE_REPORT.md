# Salvage Report — Upstox Bot (Nifty / Equity / Options) Migration to `F:\Nifty`

**Source:** `D:\BOT\root`  **Target:** `F:\Nifty`  **Date:** 2026-06-04
**Goal:** Conclude Codex's partial migration. Keep **runnable core infrastructure** for the Upstox bot (Nifty + equity + options dashboard). **Drop all strategies, indicators, alpha/research engines, and FTMO.**

---

## 0. Scope assumption (please confirm)

"Core infra, no strategies, no indicators" has two readings. The user said **"bot"** and named the **options dashboard**, so this report assumes:

> **Reading (b): a runnable platform = broker connectivity + market data + execution/order management + options dashboard + Flask shell + auth + persistence — with all trading logic removed.**

Not reading (a) "just the `core/` Python library." That distinction is the source of the biggest gap below. **If you actually want only the `core/` library (no Flask, no scripts), say so and Sections 3–4 shrink dramatically.**

---

## 1. Headline findings

1. **Codex's `core/` triage was largely right but made one inverted call:** it **dropped `core/execution/handler.py`** (the execution orchestrator — *the* thing that turns a signal into a broker order) and its two infra deps (`core/analytics/capture.py`, `core/analytics/diagnostic_engine.py`), while **keeping `core/execution/pixityAI_risk_engine.py`** — a strategy-only module imported solely by PixityAI/backtest code. That is exactly backwards and must be fixed.

2. **Whole runnable layers are missing from the target.** `F:\Nifty` has **no `flask_app/`, no `app_facade/`, no `scripts/`**, and `core/analytics/` contains only `resampler.py`. As-is the target is a **library, not a bot** — and the **options dashboard the user explicitly asked for cannot run** (its blueprint, template, facade, analytics engine, publisher, and entry script were never copied).

3. **The infra/strategy boundary is genuinely clean at the import level.** `core/execution`, `core/data`, `core/risk`, `core/messaging`, `core/portfolio`, `core/post_trade`, and the options facade import **zero** strategy modules and **zero** `core/analytics/indicators/`. So a clean cut is achievable — the cut points are well-defined.

4. **FTMO is wrongly present in the target.** `F:\Nifty\ftmo\` + `FTMO_*` docs are the forex/gold prop-firm system — a separate strategy stack, not the Upstox bot. Should be removed from this repo.

5. **The DuckDB schema/queries/writers carry strategy table DDL** (daytype, pixity, niftyshield tables). These files are load-bearing infra and must be kept, but they embed strategy-specific table definitions that can optionally be pruned later (cosmetic, not blocking).

---

## 2. What Codex already migrated (✅ keep, verified infra)

These are in `F:\Nifty\core\` and are correctly classified as infrastructure:

| Module | Role |
|---|---|
| `core/auth/` | Upstox OAuth/token management |
| `core/brokers/` | `upstox_adapter`, `upstox_market_data`, `paper_broker`, `mock_broker_adapter`, `broker_base` |
| `core/api/` | API client layer |
| `core/data/` | Market data providers, websocket ingestor, duckdb client, options_provider, market hours/session, resampling, schema |
| `core/database/` | `manager`, `writers`, `queries`, `schema`, `locks`, `legacy_adapter`, `ingestors/`, `providers/` |
| `core/execution/` (partial) | trackers, order factory/lifecycle/models, risk_manager, margin/pnl tracker, reconciliation, persistence, groups, health_monitor, options/ selector |
| `core/events.py`, `core/clock.py` | Event bus + clock |
| `core/alerts/`, `core/logging/`, `core/messaging/`, `core/instruments/` | Cross-cutting infra |
| `core/risk/greeks/` | Black-76, greeks model, portfolio greeks |
| `core/analytics/resampler.py` | Bar resampling |
| `config/`, `docs/`, root manifests | Config + documentation |

---

## 3. Gaps — infra that MUST be salvaged but is missing or wrong in the target

### 3a. Fix the inverted execution call (critical)
- **ADD `core/execution/handler.py`** — 842 lines, the execution orchestrator. Imports only `core.execution.*`, `core.events`, `core.clock`, `core.brokers`, `core.risk.greeks`, `core.database`, `core.instruments`, and `core.analytics.{capture,diagnostic_engine}`. **No strategy imports.** Without it the bot cannot place a trade.
- **ADD `core/analytics/capture.py`** — handler dependency (TLP capture). Clean (only a docstring mentions strategy names).
- **ADD `core/analytics/diagnostic_engine.py`** — handler dependency. Clean (stdlib + duckdb + pandas only).
- **REMOVE `core/execution/pixityAI_risk_engine.py`** from the target — strategy-only; imported solely by `pixityAIMetaStrategy.py` and `core/backtest/runner.py`, neither of which is migrated.

### 3b. Options dashboard tier (user explicitly wants options) — entirely absent
All clean-bounded; needed for the options dashboard to run:
- `core/analytics/options_analytics.py` — PCR / Net GEX / OI / Max Pain engine. Imports only `core.logging` + `core.data.options_provider`. **Judgment call flagged in §6.**
- `core/messaging/options_publisher.py` — SSE/ZMQ publisher (imports `core.messaging.zmq_handler` only).
- `app_facade/options_facade.py` — facade bridging Flask ↔ core (imports options_provider, options_analytics, database).
- `flask_app/blueprints/options.py` + `flask_app/templates/options/` — dashboard UI.
- `scripts/run_options_engine.py` — the options engine entry point.

### 3c. Flask shell + facade + entry points (needed for reading (b))
- `flask_app/__init__.py`, `middleware.py`, `telemetry_bridge.py`, `static/`, `templates/base.html`
- **Infra blueprints to keep:** `auth.py`, `dashboard.py`, `database.py`, `options.py`
- **Infra facades to keep:** `auth_facade.py`, `data_facade.py`, `options_facade.py`, `ops_facade.py` *(verify ops_facade has no strategy deps before keeping)*
- **Entry scripts:** `run_flask.py`, `run_options_engine.py`
- **`app_facade/__init__.py`** — trim exports to only the kept facades.

### 3d. Data / instrument / ingest scripts (infra)
Keep from `scripts/`: `fetch_instrument_master.py`, `fetch_upstox_historical.py`, `market_ingestor.py`, `fetch_intermarket_data.py` *(if Nifty/BankNifty intermarket data is wanted)*, plus DB migration helpers (`migrate_monolith_to_isolated.py`) as needed.

### 3e. Requirements
`requirements.txt` migrated, but it was generated by `pipreqs` and is **incomplete for the bot** (missing `duckdb`, `flask`, `protobuf`; broker SDK not listed). Regenerate against the final kept tree, or hand-add: `duckdb`, `flask`, `protobuf`, the Upstox/broker SDK actually used, `websocket-client`. (`pyzmq` is already present.)

---

## 4. What to DROP (strategies, indicators, research, FTMO)

### Strategies — `core/strategies/` (delete entire dir)
`commodity_trend.py`, `daily_regime_strategy_v2.py`, `ehma_pivot.py`, `nifty_shield_strategy.py`, `pixityAIMetaStrategy.py`, `pixityAI_batch_events.py`, `pixityAI_event_generator.py`, `precomputed_signals.py`, `stock_daytype_paper.py`, `regime/`, `options_portfolio/`, `registry.py`, `base.py` — all of the user's named exclusions (commodity_trend, daily regime, ehma_pivot, nifty shield, all pixity, stock daytype) plus the rest.

### Indicators — `core/analytics/indicators/` (delete)
`atr, ema, rsi, macd, adx, vwap, ut_bot` — user said no indicators; nothing in the keep-set imports them.

### Strategy analytics / feature factories — drop from `core/analytics/`
Drop: `pixityAI_feature_factory.py`, `pixityAI_labeler.py`, `confluence_engine.py`, `regime_engine.py`, `dispersion.py`, `day_features.py`, `models.py` *(used only by the dropped db providers/analytics)*. **Verify then likely drop:** `metrics_service.py`, `populator.py`. **Keep:** `capture.py`, `diagnostic_engine.py`, `options_analytics.py`, `resampler.py`.

### Strategy orchestration layers
- `core/runner.py` + `core/backtest/` — runner has `_run_pixityAI_batch()` and is imported only by strategy/backtest scripts. Drop (user adds own runner later).
- `core/state/daytype_engine.py` — Stock-DayType feature. Drop.
- `core/models/` — all `pixityAI_*`, `nifty_shield_config.json`, `regime_map_*`. Drop.
- `core/portfolio/`, `core/post_trade/` — **verify**: keep only if a kept module imports them (handler does **not**). Likely drop unless wanted as infra (see §6).
- `core/database/providers/analytics.py` — pulls `confluence_engine` + `IndicatorResult`; drop (Codex already excluded it).

### Top-level strategy dirs (delete)
`strategy/`, `analytics/` (root), `risk/` (root, `premium_risk_model.py`), `models/` (root daytype), `services/` (`commodity_strategy_orchestrator.py`).

### Strategy scripts (~50 of 81) — drop
All `alpha_seeker_*`, `train_*`, `label_*`, `*_scan*`, `research_*`, `build_*_features*`, `sweep*`, `optimize_*`, `*backtest*`, `run_phase*`, plus strategy runners `unified_runner.py`, `live_runner.py`, `nifty_shield_runner.py`, `strategy_runner_node.py`, `live_daytype_engine.py`, etc.

### Strategy Flask blueprints / templates / facades (drop)
Blueprints: `niftyshield.py`, `commodities.py`, `scanner.py`, `propdeskmode.py`, `backtest.py`. Templates: `niftyshield/`, `commodities/`, `scanner/`, `propdeskmode/`, `paper_trading/`, `ftmo/`, `backtest/`. Facades: `analytics_facade.py`, `backtest_facade.py`, `commodities_facade.py`, `scanner_facade.py`.

### FTMO (drop from this repo)
`F:\Nifty\ftmo\` and `FTMO_ARCHITECTURE.md`, `FTMO_DEPENDENCIES.md`, `FTMO_MIGRATION_REPORT.md`, `ftmo/docs/`. FTMO already lives in its own repo (`F:\ftmo` / propbot). It is not the Upstox bot.

### Strategy docs (drop from `docs/`)
`HMM_REGIME_STRATEGY_REPORT.md`, `MCX_*`, `SWEEP_CLASSIFIER_REPORT.md`, `NIFTYSHIELD_*`, `STOCK_DAYTYPE_*`, `DAYTYPE_*`, `SIGNAL_QUALITY_*`, `COMMODITY_*`, `EDGE_ANALYSIS.md`, `STRATEGY_RESEARCH_LOG.md`, `ftmo_trading_plan.md`, `mcx_commodity_strategy*`. **Keep** infra docs: `OPTIONS_ANALYSIS_DASHBOARD_PLAN.md`, `DATA_PIPELINE.md`, `CODEBASE_OVERVIEW.md`, `DEVELOPER_GUIDE.md`.

### Generated data / caches (drop, regenerate)
`*.duckdb`, `*.parquet`, `*.pkl`, `*.joblib`, `*.csv`, `trading.db`, `logs/`, `__pycache__/`, `models/*.joblib`.

---

## 5. Database schema caveat
`core/database/{schema,queries,writers}.py` and `core/database/providers/base.py` reference strategy-specific tables (e.g. `ns_paper_*`, daytype, pixity). They are **load-bearing infra — keep them**. The strategy table DDL inside is dead weight, not a runtime problem; prune later if desired. Do **not** block migration on this.

---

## 6. Judgment calls flagged for you

1. **`options_analytics.py` (PCR / GEX / Max Pain):** technically "indicators," but it's the **options dashboard's engine**, not a trading signal, and you explicitly want options. **Recommendation: keep.** Veto if you want the dashboard to show raw chain only.
2. **`core/portfolio/` + `core/post_trade/`:** not imported by handler or any kept entry point. **Recommendation: drop** unless you consider portfolio allocation / trade-truth part of "core infra" you'll build on.
3. **Reading (a) vs (b):** if you want only the `core/` library, drop all of §3c/§3d and this becomes a pure-library migration.

---

## 7. Recommended execution plan (after you approve this report)

1. **Fix target `core/`:** add `handler.py` + `capture.py` + `diagnostic_engine.py`; remove `pixityAI_risk_engine.py`.
2. **Add the dashboard + shell tier** (§3b, §3c): flask_app (infra blueprints only), app_facade (kept facades only), options engine, entry scripts.
3. **Remove FTMO + strategy docs** from the repo.
4. **Run an import-closure check** from the real entry points (`run_flask.py`, `run_options_engine.py`, broker/data/execution infra). The bucket lists above are necessary but **not sufficient** — only a resolved import graph (with strategy files as hard cut points) proves nothing is broken. Any unresolved import = either a missed infra file to add, or a strategy seam to stub/remove.
5. **Regenerate `requirements.txt`** against the final tree.
6. **Smoke test:** `python run_flask.py` boots, `/options/` renders, broker auth handshake runs in paper/mock mode.

---

## 8. Migration completed — 2026-06-04 (executed, verified)

User approved reading (b) + §6 recommendations. Executed against `F:\Nifty`:

**Added (infra):**
- `core/execution/handler.py` (the orchestrator that was missing)
- `core/analytics/capture.py`, `diagnostic_engine.py`, `metrics_service.py` (handler transitive deps — `metrics_service` surfaced via import-closure)
- `core/analytics/options_analytics.py` (options dashboard engine)
- `app_facade/{__init__,auth_facade,data_facade,ops_facade,options_facade}.py`
- `flask_app/` shell: `__init__.py` (blueprint registrations trimmed to auth/dashboard/database/ops/options), `middleware.py`, `telemetry_bridge.py`, `static/`, infra blueprints + templates only
- `scripts/`: `run_flask.py`, `run_options_engine.py`, `fetch_instrument_master.py`, `fetch_upstox_historical.py`, `market_ingestor.py`, `fetch_intermarket_data.py`, `migrate_monolith_to_isolated.py`
- `requirements.txt` rewritten from an AST scan of actual imports (duckdb, pandas, numpy, pyarrow, Flask, requests, websockets, protobuf, pyzmq, pytz)

**Removed:**
- `core/execution/pixityAI_risk_engine.py` (strategy-only, was wrongly kept)
- `core/data/{analytics_provider,cached_analytics_provider,duckdb_analytics_provider}.py` (orphaned — depended on the dropped strategy `providers/analytics.py`) and `core/data/symbol_utils.py` (broken in source, unused)
- `ftmo/` + `FTMO_ARCHITECTURE.md` + `FTMO_DEPENDENCIES.md` + `FTMO_MIGRATION_REPORT.md`
- ~19 strategy docs under `docs/`

**Also fixed:** `flask_app/templates/base.html` sidebar had 7 dead `url_for()` links to the de-registered blueprints (backtest, scanner, paper_trading, ftmo, niftyshield, propdeskmode, commodities) — every authenticated page would have 500'd with a `BuildError`. Nav trimmed to Dashboard / Database / Options / Operations.

**Verification (all green):**
- `flask_app.create_app()` builds with exactly `['auth','dashboard','database','ops','options']`
- **Render smoke test** (authenticated `test_client`): `/options/` → **200**, `/database/` → **200**; `base.html` + `dashboard.html` render with no `BuildError`. All template `url_for` targets ⊆ the 5 registered blueprints.
- `D:\BOT\root` is **not** pip-installed in the venv → the F:\Nifty-only import closure is trustworthy (no silent shadowing).
- `core.execution.handler`, options pipeline (`options_facade` / `options_publisher` / `options_analytics` / `options_provider`) import clean **resolving only `F:\Nifty` modules**
- Full `pkgutil` import-walk of `core` + `app_facade`: **all modules import clean**
- `compileall` of `core app_facade flask_app scripts`: no errors
- Forbidden-import scan (strategies/indicators/runner/backtest/state/models/ftmo): **zero hits**

**Not done (left for you):**
- `git commit` — changes are staged/untracked in the `F:\Nifty` repo, not committed (no commit was requested).
- `CLAUDE.md` / `README.md` / `PROJECT_REVIEW_SUMMARY.md` / `REPO_AUDIT.md` in `F:\Nifty` still describe the full multi-strategy platform — **stale**, should be rewritten for the infra-only repo.
- Runtime config: broker credentials/`.env`, DuckDB data paths, instrument master DB must be provided before live/paper run.
- `logs/`, `entities.json`, `mempalace.yaml` are leftover non-infra artifacts (harmless; remove if desired).
