# CLAUDE.md — Trading Platform

## Project Overview
Production-grade, deterministic algorithmic trading platform.
- **Language**: Python 3.10+
- **Database**: DuckDB (single source of truth)
- **Broker**: Upstox V2 (REST + WebSocket)
- **UI**: Flask + Tailwind CSS
- **Shell**: Use Unix syntax (forward slashes, `/dev/null` not `NUL`)

---

## Architecture Principles (DO NOT VIOLATE)

1. **Strategies Stay Dumb** — emit `SignalEvent` only; no broker/sizing/risk logic inside strategies
2. **Analytics Produce Facts** — all indicators pre-computed offline; runtime is read-only
3. **Execution Owns Reality** — risk, sizing, and broker interaction live exclusively in `core/execution/`
4. **Runner is Neutral** — single-threaded orchestrator; live and backtest data treated identically
5. **Audit-First** — every trade must be explainable by exact analytical facts

### Layer Flow
```
CLI Scripts → DuckDB → Core Logic → Facade → Flask UI
```

---

## Key Directories

| Path | Purpose |
|------|---------|
| `core/strategies/` | Strategy implementations (emit signals only) |
| `core/execution/` | Risk, sizing, broker interaction |
| `core/backtest/runner.py` | `BacktestRunner` with `_run_pixityAI_batch()` |
| `core/strategies/pixityAI_batch_events.py` | Vectorized event generation |
| `core/strategies/precomputed_signals.py` | Feed pre-computed events to backtest engine |
| `core/filters/` | Signal quality filters (Kalman, pipeline) |
| `core/strategies/regime/` | HMM regime observer/classifier/executor |
| `core/models/pixityAI_config.json` | PixityAI strategy config |
| `core/models/nifty_shield_config.json` | NiftyShield strategy config |
| `core/strategies/nifty_shield_strategy.py` | NiftyShield — self-contained weekly options seller |
| `scripts/nifty_shield_runner.py` | NiftyShield live daemon (30s poll) |
| `scripts/nifty_shield_backtest.py` | NiftyShield walk-forward backtest |
| `flask_app/blueprints/niftyshield.py` | NiftyShield Flask blueprint (`/nifty-shield/`) |
| `core/data/options_provider.py` | Upstox V3 option chain fetcher + DuckDB cache |
| `core/analytics/options_analytics.py` | Options structural engine (PCR, GEX, OI, Max Pain) |
| `core/messaging/options_publisher.py` | SSE publisher for real-time option chain updates |
| `app_facade/options_facade.py` | Options facade — bridge between Flask UI and core |
| `flask_app/blueprints/options.py` | Options dashboard Flask blueprint (`/options/`) |
| `flask_app/templates/options/index.html` | Options dashboard UI template |
| `tests/analytics/test_options.py` | Options engine unit + integration tests (17 tests) |
| `flask_app/` | Thin Flask UI — display only, no computation |
| `scripts/` | CLI entry points for backtests, scans, training |
| `data/market_data/nse/candles/1m/` | 1-min DuckDB candle files by date |
| `docs/` | Strategy research logs and implementation summaries |
| `docs/NIFTYSHIELD_IMPLEMENTATION.md` | Full NiftyShield design + API reference |
| `docs/OPTIONS_ANALYSIS_DASHBOARD_PLAN.md` | Options dashboard design + implementation plan |

---

## Data Layout

- **1-min candles**: `data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb`
  - Equities (`NSE_EQ|INE...`): 2024-10-17 to present
  - `NSE_INDEX|Nifty 50`: 2023-01-02 to present
  - `NSE_INDEX|Nifty Bank`: 2023-01-02 to present (backfilled Feb 2026, 292K bars)
- **Daily intermarket**: `data/market_data/nse/candles/1d/{date}.duckdb` (Nifty 50, Bank Nifty, India VIX)
- **Symbol format**: `NSE_EQ|INE...` (equities), `NSE_INDEX|Nifty 50` / `NSE_INDEX|Nifty Bank` (index)
- **ALL NSE_INDEX symbols have volume=0** — never use VWAP or vol_z filters on index data
- **BankNifty ingest script**: `scripts/fetch_intermarket_data.py --include-1m` (uses 10-day chunks for 1m — 29-day chunks cause sporadic 400s)

---

## Backtesting Rules

- **Disable idempotency guard**: `execution._is_signal_already_executed = lambda sid: False`
- **90-day warmup**: data loading extends before `start_time` for indicator computation
- **Swing detection is CAUSAL**: use `result.iloc[i + period]` assignment — never centered window
- **Position stacking guard**: handler must block new entry while a position is open on same symbol
- **Position tracker must update on paper fills**: `FillEvent` → `position_tracker.update_from_fill()`
- **Fee model**: NSE equity intraday — Rs 20 brokerage + STT 0.025% + exchange/SEBI/GST/stamp

---

## DayTypeEngine — Feature Blocks

| Block | Features | Notes |
|-------|----------|-------|
| A | gap_pct, prev_day_return, etc. | Excluded from 13pm prod model |
| B | open_5m_ret, open_30m_range, etc. | Opening structure |
| C–F | partial_return, partial_clv, TWAP, rotation | Intraday Nifty structure |
| **H** | **bn_nf_open_5m_spread, bn_nf_correlation_5m, etc.** | **BankNifty intermarket (new)** |

- **logistic_13pm_prod**: 41 features, Block A excluded, trained 2023–2025, **80% val accuracy**
- **Block H** computed in `build_intraday_features.py` + `DayTypeEngine._compute_block_h()`
- Live: `DayTypeEngine.on_bn_bar(bar)` feeds BN bars; `v9_pm_runner` fetches BN from live buffer
- Retrain: `python scripts/build_intraday_features.py && python scripts/train_daytype_classifier.py`

---

## NiftyShield Strategy — Current Config

- **Type**: Regime-adaptive weekly options premium selling (structure chosen at entry per DayType + VIX)
- **Structures**: `short_straddle` (Choppy+VIX≤14) | `iron_fly` (Choppy+VIX 14–16) | `short_strangle` (Choppy+VIX>16) | `bull_put_spread` (BullTrend) | `bear_call_spread` (BearTrend)
- **Entry**: 13:00pm (same bar as 13pm checkpoint, `entry_after_minutes=0`)
- **Sizing**: Choppy=2 lots, Trend=1 lot, VIX>16→–1 lot (except strangle), VIX>20→skip
- **Wing offsets**: iron_fly ±100pts | directional spreads ±150pts | strangle OTM ±50pts
- **Exit**: profit_target 50% of net premium | stop_loss 2× | time_exit 15:15 | delta_adjustment >0.55 (short legs only)
- **P&L**: `(short_pnl + wing_pnl) × lot_size × lots − costs`
- **IV model**: VIX daily close ÷ 100 (flat); Black-76 synthetic pricing
- **DB tables**: `ns_paper_signals`, `ns_paper_trades` in trading.db (`structure` column per trade)
- **Dashboard**: `/nifty-shield/` (state, open position, Greeks, trade history)
- **Backtest**: `python scripts/nifty_shield_backtest.py --walkforward`
- **Full doc**: `docs/NIFTYSHIELD_IMPLEMENTATION.md`

---

## PixityAI Strategy — Current Config

- **Timeframe**: 15m (better than 1h — more trades, better edge)
- **Meta-model**: DISABLED (`skip_meta_model=True`) — anti-predictive on equities
- **Signal quality filter**: DISABLED — regime-dependent, catastrophic in hostile periods
- **R:R**: SL = 1×ATR, TP = 2×ATR, time stop = 12 bars
- **Profitable symbols** (Phase 6 scan): VEDL, BDL, KALYANKJIL, PNBHOUSING

---

## Options Analysis Dashboard — In Progress

- **Type**: Real-time options structural analysis for Nifty 50 and BankNifty
- **Data source**: Upstox V3 Option Chain API, 5-second snapshots
- **Metrics**: PCR (put-call ratio), Net GEX (gamma exposure), OI buildup patterns, Max Pain, IV smile
- **Architecture**: `OptionsProvider` (fetch + DuckDB cache) → `OptionsAnalytics` (structural engine) → `OptionsFacade` → Flask blueprint
- **Provider**: `core/data/options_provider.py` — fetches chain from Upstox V3, caches in `data/market_data/options.duckdb`
- **Analytics**: `core/analytics/options_analytics.py` — PCR, GEX, OI analysis, Max Pain, ATM detection
- **Facade**: `app_facade/options_facade.py` — `get_structural_data()`, `get_option_chain()`, `get_gex_distribution()`, `get_summary()`
- **SSE**: `core/messaging/options_publisher.py` — real-time push to UI
- **Flask**: `/options/` blueprint + `/api/` endpoints for structural data, chain, GEX, OI distribution
- **Expiry logic**: Nifty=Tuesday, BankNifty=Wednesday weekly; `get_weekly_expiry()` + `get_expiry_list()` (instrument DB)
- **Instrument DB**: `data/instruments/nse_fo_instruments.duckdb` — strikes, expiries, lot sizes
- **Tests**: `tests/analytics/test_options.py` — 17 tests (provider, analytics, integration), all passing
- **Full plan**: `docs/OPTIONS_ANALYSIS_DASHBOARD_PLAN.md`

---

## FTMO Challenge System — Key Files

| Path | Purpose |
|------|---------|
| `ftmo/config.py` | All FTMO constants + `INSTRUMENT_CONFIG` (point values) + `SKIP_WEEKDAYS` |
| `ftmo/engine.py` | `FTMOBacktestEngine(df, sweep_classifier, sweep_classifier_s2, point_value)` |
| `ftmo/detector.py` | Sweep → structure shift → displacement → entry. Optional `sweep_classifier=` gate |
| `ftmo/session.py` | Vectorised session classifier |
| `ftmo/risk.py` | FTMO hard limits + internal overlay. `calculate_lot_size(state, pts, point_value=)` |
| `ftmo/live_trader.py` | `MT5LiveTrader(login, password, server, symbol, point_value)` |
| `ftmo/kline_tokenizer.py` | K-line tokenizer: M5 candles → discrete tokens (K-means, k=64) |
| `ftmo/sweep_classifier.py` | False sweep classifier: logistic on token histogram + structural features |
| `ftmo/cache_{sym}_m5.parquet` | Per-instrument M5 bar cache (e.g. `cache_xauusd_m5.parquet`) |
| `ftmo/trade_log_{sym}.csv` | Per-instrument live trade log |
| `ftmo/sweep_clf.pkl` | Combined (both sessions) sweep classifier |
| `ftmo/sweep_clf_s1.pkl` | Session 1 (London) sweep classifier |
| `ftmo/sweep_clf_s2.pkl` | Session 2 (NY) sweep classifier |
| `scripts/label_sweeps.py` | Extract labeled sweeps with session tag: `(hist, struct, label, session_num)` |
| `scripts/train_sweep_clf.py` | Train combined + S1 + S2 classifiers in one pass |
| `docs/FTMO_CHALLENGE_SYSTEM.md` | Full system design, backtest results, CLI reference |

### FTMO Backtest + Filter Training

```bash
python -m ftmo.cli backtest                         # baseline XAUUSD
python -m ftmo.cli backtest --symbol XAGUSD         # XAGUSD backtest
python scripts/label_sweeps.py                      # generate training labels (with session tag)
python scripts/train_sweep_clf.py                   # train combined + S1 + S2 classifiers
python -m ftmo.cli backtest --sweep-filter          # A/B: per-session classifiers preferred
python -m ftmo.cli live --login X --password Y --server Z [--symbol XAGUSD]
python -m ftmo.cli multi-live --config ftmo/accounts.json   # parallel accounts
```

### Sweep Classifier — Design

- **Tokenizer**: each candle → body_ratio + upper_wick/ATR + lower_wick/ATR → K-means cluster (0–63)
- **Features**: 64-dim token histogram of 20 pre-sweep bars + 3 structural features (extension, body ratio, close retrace)
- **Model**: LogisticRegression with `class_weight='balanced'`, threshold F1-optimized on training data
- **Gate in `scan_session()`**: if `classifier.is_valid(...)` returns False, sweep is skipped before structure shift detection runs
- **S1/S2 split**: live trader routes `_sweep_clf_s1` to London session, `_sweep_clf_s2` to NY session; fallback to combined if per-session files absent
- **Trained on 348 trades** — re-run `label_sweeps.py` + `train_sweep_clf.py` after label format was updated to 4-tuple (session tag added Mar 2026)

### TP / Pricing — Important

- **Signal `entry_price`**: structural displacement zone level (historical bar)
- **Actual fill**: live MT5 bid/ask at order time — may differ from zone price
- **TP is computed from actual fill**: `price ± RR_RATIO × risk_points` — guarantees true 2R
- **SL stays structural**: sweep extreme + 0.15 × ATR buffer (not adjusted for fill)

---

## Known Pitfalls

- Trailing stops on intraday equity **hurt** — cut winners on normal pullbacks
- Directional filters (daily EMA trend) **removed winning counter-trend trades**
- Fee impact is massive at Rs 500 risk — STT alone is 0.025% of turnover per leg
- Single-period validation is misleading — always run full walk-forward
- Index data (Nifty) has volume=0 — kills vol_z and VWAP filters silently
- Position tracker not updated → equity=cash only, DD wrong, TP/SL/time stops never fire
- **Sweep classifier trained on 348 trades** — small dataset; logistic preferred over Transformer to avoid overfitting; validate with held-out period before enabling live

---

## Development Conventions

- **No over-engineering** — don't add error handling, helpers, or abstractions for one-time use
- **No docstrings/comments** on code you didn't change
- **No backwards-compatibility shims** — delete unused code completely
- **Validate with train/test split** — in-sample results are meaningless
- Before modifying any file, **read it first** — understand existing patterns
- Prefer editing existing files over creating new ones
