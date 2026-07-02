# Nifty Trading Platform

Production-grade, deterministic algorithmic trading platform for Indian equity derivatives.

**Stack:** Python 3.10+ · DuckDB · Upstox V2 (REST + WebSocket) · Flask + Tailwind CSS

---

## Quick Start

```bash
pip install -r requirements.txt
python scripts/run_flask.py          # Start dashboard (localhost:5000)
python -m pytest tests/ -q           # Run test suite
```

---

## Architecture

```
CLI Scripts → DuckDB → Core Logic → Facade → Flask UI
```

The platform follows five architecture principles:

1. **Strategies Stay Dumb** — emit `SignalEvent` only; no broker/sizing/risk logic inside strategies
2. **Analytics Produce Facts** — all indicators pre-computed offline; runtime is read-only
3. **Execution Owns Reality** — risk, sizing, and broker interaction live exclusively in `core/execution/`
4. **Runner is Neutral** — single-threaded orchestrator; live and backtest data treated identically
5. **Audit-First** — every trade must be explainable by exact analytical facts

See `CLAUDE.md` for the full development guide and `docs/PLATFORM_CONSTITUTION.md` for governance.

---

## Milestone Status

| Milestone | Status |
|-----------|--------|
| MM9 — Margin enforcement | **Complete** (SPAN margin, calendar spreads, ELM) |
| MM10 — Complete SPAN portfolio margin | **Complete** (ADR-011/012/013, margin architecture closed) |
| MM11 — Platform consolidation | **In progress** (MM11.1–MM11.5 done; MM11.6 documentation audit) |
| MM12 — External Strategy Integration Contract | **Future** |
| MM13 — Broker reconciliation | **Future** |

---

## Key Directories

| Path | Purpose |
|------|---------|
| `core/execution/` | Risk, sizing, broker interaction |
| `core/brokers/` | Broker adapters — Upstox and PaperBroker |
| `core/instruments/` | Canonical instrument model, resolver, and master DB |
| `core/runtime/` | LoopDriver, telemetry, signal source contracts |
| `core/risk/span/` | SPAN margin parser, calculator, snapshot |
| `core/database/` | DuckDB/SQLite persistence (manager, schema, writers) |
| `flask_app/` | Thin Flask UI — display only, no computation |
| `scripts/` | CLI entry points — data ingestion, runners |
| `tests/` | Unit and integration tests by domain |
| `docs/` | Architecture docs, reports, ADRs |

---

## Data Layout

- **1-min candles**: `data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb`
- **Instrument master**: `data/instruments/nse_fo_instruments.duckdb`
- **SPAN files**: `reference/span/` (archived PC-SPAN XML)
- **Option chain**: `data/market_data/options.duckdb`
- **Runtime events**: `logs/runtime_events.jsonl`
- **Execution state**: `data/execution.db` (SQLite — orders, fills, positions)

---

## Governance

See `docs/PLATFORM_CONSTITUTION.md` — the foundational governance document.

Architecture decisions are recorded in `docs/ARCHITECTURE_DECISIONS.md` (append-only ADRs).

Project status tracked in `docs/PROJECT_STATE.md`.

Development conventions in `CLAUDE.md`.
