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

## PSB-1 — Panel Screening Battery, Increment 1

**Status:** CLOSED 2026-07-14. Outcome: **"no winner recommended"** — the protocol worked as designed. PSB-2 authorized as the successor.

### Summary
Screened 5 candidates (C1–C5) on dev data (2012–2022) against the CSMP-certified equity store + NIFTY-200 point-in-time universe. The delivery-percentage field (NSE's unique advantage) anchored C3/C4. Every candidate ran through the frozen `PSB1_PROTOCOL.md` Rev 2: exact §5 formulas, Spearman rank IC, net top-quintile spread under gate-(d) era-accurate fees + κ=5bp/side slippage, §4.2 imputed-forward-return robustness column, §7 power projection against the 2023–2026 sealed window (≥0.80 hurdle), Bonferroni-deflated selection (m=5).

### Phase 2 Results (all numbers script-generated, no hand-edited numbers)

| Cand | n | Mean IC | t | p | Power δ | Q1-Q5 gross | Net spread | Fee drag | Outcome |
|---|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|---|
| C1 reversal (weekly) | 569 | +0.023 | 3.76 | 9e-5 | 0.68 | +1.1% | −16.8% | 1293 bp | Not eligible (net<0, power<0.80) |
| C2 residual rev (weekly) | 529 | **+0.035** | **6.63** | **4e-11** | **0.99** | **+14.9%** | −8.6% | 1422 bp | Not eligible (net<0) |
| C3 delivery z (weekly) | 143 | +0.025 | 2.93 | 0.002 | 0.95 | **+17.5%** | −2.5% | 1384 bp | Not eligible (net<0) |
| C4 C1×C3 (weekly) | 143 | −0.003 | −0.42 | 0.66 | 0.02 | −0.3% | −16.1% | 1677 bp | Not eligible |
| **C5 low-vol (monthly, banded)** | **131** | **+0.068** | **3.14** | **0.001** | 0.54 | **+16.2%** | **+4.3%** | **14 bp** | Closest — clears IC+spread, misses power |

### Fee finding — the dominant structural constraint
- Delivery-equity STT is **0.1% per leg** (vs intraday 0.025% sell-only). At weekly cadence with ~0.80 turnover, the **STT alone** imposes ~13pp/yr cost — no known Indian equity cross-sectional effect clears a 13pp hurdle. C1–C4 all confirm this: gross Q1-Q5 spreads of +1% to +17% are consumed by 12–17pp/yr fee drag.
- C5 clears fees via **monthly cadence + banded exit** (0.40 exit band). Turnover drops to ~0.04, fee drag to ~14 bp/yr.
- The STT is the binding constraint, not the signal. Any candidate that clears fees at all will almost certainly clear IC and power.

### Substrate — certified
The `equity_bhavcopy_adjusted` view (7,030,920 rows) is certified by the four-arm contract suite (`scripts/psb1/contract_arms.py`): zero structural filters, entity grain, the whole panel. Six structural defects were repaired across Prompts 2–5: entity-grain cumulative factors (rename seams), time-aware entity resolution (recycled DTIL ticker), series-crossing prev_close LAG (246 cells), the DVL→DTIL mis-key (NSE feed error), the evidence-screen blind spot (f≥0.75 no-reprice), and ISIN issuer-prefix entity fragmentation. The adjusted-series continuity invariant returns 0 view-induced fabrications.

### Key files
| File | Purpose |
|------|---------|
| `scripts/psb1/screening_harness.py` | PSB-1 harness: loader, grids (§3), C1–C5 scoring (§5), metrics (§6), power (§7), AC₁/Newey–West |
| `scripts/psb1/certify_substrate.py` | Four-arm contract suite (Arm A–D) + structural guard runner |
| `scripts/psb1/contract_arms.py` | The contract test library (intra-symbol CA-shape, cross-symbol handoff, prev_close identity, factor evidence) |
| `scripts/psb1/disposition_register.py` | Committed disposition register (ETF splits, demergers, store exceptions) |
| `scripts/psb1/repair_*.py` | Prompt-specific validate-then-apply runners (copy-first discipline) |
| `scripts/csmp/build_universe.py` | Universe membership + `symbol_entity_intervals` + ISIN issuer linkage |
| `scripts/csmp/ingest_corporate_actions.py` | `build_adjusted_view()` (entity-grain, time-aware), factor overrides (DVL→DTIL), orphan invariant, evidence screen |
| `core/execution/equity/delivery_fees.py` | Era-accurate NSE delivery-equity fee model (STT both legs, stamp, NSE/SEBI/GST, DP per sell line) |
| `docs/reports/PSB1_PROTOCOL.md` | **FROZEN Rev 2** — the pre-registered screening protocol |
| `docs/reports/PSB1_PHASE0_RESEARCH_RECORD.md` | Phase 0 brainstorm, operator decisions D1–D7 |
| `docs/reports/PSB1_C{1..5}_REPORT.md` | Script-generated candidate reports |
| `docs/reports/PSB1_SUBSTRATE_CERTIFICATION.md` | Substrate certification report (four-arm contract) |
| `tests/psb1/` | 38 tests (scoring unit tests + contract arm unit tests) |

### PSB-2 — authorized, pending Phase 0
A fee-survivable battery. Every candidate must clear the cost structure by construction: monthly cadence, banded exits, low turnover, or entry/exit asymmetry that avoids STT on both sides. Substrate and harness reused. Pending a Phase 0 research record with candidate slate + operator decisions.

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
- **DELIVERY-EQUITY FEES DOMINATE WEEKLY STRATEGIES** — STT is 0.1% **per leg** (both buy and sell) for delivery equity vs 0.025% sell-only for intraday. At weekly turnover ~0.80, STT alone imposes ~13pp/yr. No known Indian equity cross-sectional effect clears a 13pp fee hurdle. Monthly+banded constructs are the only fee-survivable path. Confirmed by PSB-1 Phase 2: C1 gross +1.1% → net −16.8%; C5 gross +16.2% → net +4.3% (14 bp/yr drag).
- **Fabricated adjusted returns from CA mis-keys survive both screens** — a factor registered to the wrong symbol (DVL→DTIL), dropped by the events CTE (PHILIPCARB/PCBL ISIN fragmentation), or spanning a recycling ticker (DTIL/DVL entity union) produces a false >|20%| return invisible to R1's gap filter. The four-arm contract suite catches all three classes at entity grain with zero structural filters.
- **An entity is not one symbol for all time** — NSE recycles vacated tickers (DTIL→tea business). Time-aware entity resolution via `symbol_entity_intervals` is required; union-find alone is not sufficient.
- **An ISIN is not one entity for all time** — face-value changes re-issue the security with a new ISIN serial (PHILIPCARB/PCBL, INE602A01015→INE602A01031). ISIN issuer-prefix linkage is required; full-ISIN matching severs a company at exactly the corporate action it must adjust for.

---

## Development Conventions

- **No over-engineering** — don't add error handling, helpers, or abstractions for one-time use
- **No docstrings/comments** on code you didn't change
- **No backwards-compatibility shims** — delete unused code completely
- **Validate with train/test split** — in-sample results are meaningless
- Before modifying any file, **read it first** — understand existing patterns
- Prefer editing existing files over creating new ones
