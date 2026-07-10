# CLAUDE.md — Trading Platform

## Project Overview
Production-grade, deterministic algorithmic trading platform.
- **Language**: Python 3.10+
- **Database**: DuckDB (single source of truth)
- **Broker**: Upstox V2 (REST + WebSocket)
- **UI**: Flask + Tailwind CSS
- **Shell**: Use Unix syntax (forward slashes, `/dev/null` not `NUL`)

---

## Feature-Frozen Components

Components certified as stable and no longer receiving feature changes:

| Component | File | Frozen Since | Notes |
|-----------|------|-------------|-------|
| ParserRegistry | `core/risk/span/span_parser.py` | MM9.5 | Parser registration infrastructure |
| ParserV400 | `core/risk/span/parser_v400.py` | MM9.5 | NSE SPAN v4.00 XML parser |
| SpanSnapshot | `core/risk/span/span_snapshot.py` | MM9.5 | Immutable DTOs |
| SpanRepository | `core/risk/span/span_repository.py` | MM9.5 | Read-only archive access |
| SpanReadiness | `core/risk/span/span_readiness.py` | MM9.5 | Startup readiness evaluation |
| SpanMarginCalculator | `core/risk/span/span_calculator.py` | MM10.2 | Contract-level SPAN margin computation |
| MarginCalculator Protocol | `core/risk/margin_calculator.py` | MM10.1 | Protocol v2 — stable interface |
| ELM Rates | `core/risk/elm_rates.py` | MM10.4 | Regulatory ELM constants — NSCCL source |
| NseMarginEngine | `core/risk/nse_margin_engine.py` | MM10.4 | Margin composition layer (SPAN + credits + ELM) |

## Margin Architecture — Two Authorities (MM10, closed)

- **Sizing/computation authority**: `NseMarginEngine` — sole margin calculator in research, backtest, paper, and LIVE (unchanged in every mode). It is a deterministic implementation of publicly available NSE Clearing margin rules, not a broker RMS clone — perfect broker parity is structurally unreachable at retail.
- **Order-acceptance authority**: the broker RMS, at the gateway only — never consulted for sizing, never overrides `NseMarginEngine`'s computed margin.
- Broker margin reconciliation (fetch/compare/log broker vs. local) is a **deferred LIVE-only capability** — no code exists today; do not build a `MarginProvider` abstraction or a validation-policy config ahead of a concrete need (no production strategy, no funded LIVE account exists yet).
- *(ADR-011, ADR-012, ADR-013 — `docs/ARCHITECTURE_DECISIONS.md`)*

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
| `core/execution/` | Risk, sizing, broker interaction |
| `core/brokers/` | Broker adapters — Upstox and PaperBroker |
| `core/brokers/mapping/` | Canonical ↔ Upstox instrument mapping |
| `core/instruments/` | Canonical instrument model, resolver, and master DB |
| `core/runtime/` | LoopDriver, telemetry, signal source contracts |
| `core/analytics/options_analytics.py` | Options structural engine (PCR, GEX, OI, Max Pain) |
| `core/data/options_provider.py` | Upstox V3 option chain fetcher + DuckDB cache |
| `core/messaging/options_publisher.py` | SSE publisher for real-time option chain updates |
| `app_facade/options_facade.py` | Options facade — bridge between Flask UI and core |
| `flask_app/blueprints/options.py` | Options dashboard Flask blueprint (`/options/`) |
| `flask_app/templates/options/index.html` | Options dashboard UI template |
| `flask_app/` | Thin Flask UI — display only, no computation |
| `scripts/fno_runner.py` | F&O live runner (Upstox, PAPER and LIVE modes) |
| `scripts/` | CLI entry points — data ingestion, instrument master, runners |
| `tests/` | Unit and integration tests by domain |
| `docs/` | Architecture docs, reports, and implementation notes |
| `docs/DRIVER_SPECIFICATION.md` | LoopDriver spec and behavior contracts |
| `docs/PLATFORM_CONSTITUTION.md` | Architectural principles and invariants |

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

## Production Strategy Status

- No production strategy currently exists in this repository.
- The strategy layer (`core/strategies/`) is intentionally unimplemented — greenfield.
- Future strategy work must be designed fresh against the current infrastructure.
- Architectural decisions must not assume any specific future strategy.
- Historical strategy designs (NiftyShield, PixityAI) existed in a prior codebase and were not ported during the SALVAGE migration (2026-06-04).

---

## Options Analysis Dashboard — In Progress

Real-time options structural analysis (PCR, Net GEX, OI buildup, Max Pain, IV smile) for Nifty 50 and BankNifty, from the Upstox V3 option chain at 5-second snapshots.

- **Flow**: `options_provider.py` → `options_analytics.py` → `options_facade.py` → `/options/` blueprint; SSE push via `options_publisher.py` (paths in Key Directories above)
- **Expiry**: Nifty=Tuesday, BankNifty=Wednesday weekly — `get_weekly_expiry()` / `get_expiry_list()` against `data/instruments/nse_fo_instruments.duckdb`
- **Tests**: `tests/analytics/test_options.py` — 17 tests, passing
- **Full detail**: `docs/archive/OPTIONS_ANALYSIS_DASHBOARD_PLAN.md`

---

## Known Pitfalls

- Trailing stops on intraday equity **hurt** — cut winners on normal pullbacks
- Directional filters (daily EMA trend) **removed winning counter-trend trades**
- Fee impact is massive at Rs 500 risk — STT alone is 0.025% of turnover per leg
- Single-period validation is misleading — always run full walk-forward
- Index data (Nifty) has volume=0 — kills vol_z and VWAP filters silently
- Position tracker not updated → equity=cash only, DD wrong, TP/SL/time stops never fire

---

## Development Conventions

- **No over-engineering** — don't add error handling, helpers, or abstractions for one-time use
- **No docstrings/comments** on code you didn't change
- **No backwards-compatibility shims** — delete unused code completely
- **Validate with train/test split** — in-sample results are meaningless
- Before modifying any file, **read it first** — understand existing patterns
- Prefer editing existing files over creating new ones
