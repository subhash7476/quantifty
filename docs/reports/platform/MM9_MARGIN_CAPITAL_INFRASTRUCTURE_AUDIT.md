# MM9 — Margin, Capital, Portfolio, and Risk Infrastructure Audit

**Date:** 2026-06-16
**Status:** Evidence-only audit — no design, no implementation.
**Produced from:** `core/execution/`, `core/risk/`, `docs/`, `scripts/fno_runner.py`. All statements sourced from specific files and lines.

---

## 1. Current Margin Reality

### What exists

`core/execution/margin_tracker.py` is the sole margin-related module. It has two methods:

- `get_exposure(current_prices, symbol)` — gross exposure = `position.quantity × current_price × position.instrument.multiplier`
- `get_used_margin(current_prices)` — returns `get_exposure(...) × self.margin_rate`, where `margin_rate` defaults to `0.2` (20%)

Evidence: `margin_tracker.py:11–39`.

`MarginTracker` is instantiated inside `ExecutionHandler.__init__` at `handler.py:163`:
```python
self.margin_tracker = MarginTracker(self.position_tracker)
```

`PortfolioView.snapshot()` (`portfolio_view.py:57–65`) calls `margin_tracker.get_exposure()` and `get_used_margin()` and includes them in `PortfolioSnapshot.gross_exposure` and `PortfolioSnapshot.used_margin`. `PortfolioView` was **not wired into the runtime** at audit time (2026-06-16). As of MM9.3-S2/S3 (2026-06-28), it is **wired** in two places: (1) `LoopDriver._build_positions()` for telemetry (S2), and (2) `ExecutionHandler._handler_portfolio_view` for the drawdown risk gate (S3).

### Where margin is enforced

Nowhere. `process_signal` in `handler.py` does not call `margin_tracker` at any point. The capital-flow path from signal to broker does not gate on margin. Evidence: `handler.py:439–600` — the pre-trade gates are: authority guard, idempotency, kill switch, daily trade limit, `RiskManager.evaluate()` (quantity/symbol/kill-switch checks), drawdown (via `ExecutionMetrics`). **`margin_tracker` is never called in the execution path.**

### Where margin is not enforced

Every execution path. Pre-trade, intra-day, and at portfolio level. The broker adapter (`UpstoxAdapter.place_order`) does not receive margin information; the order payload is `{"instrument_token", "transaction_type", "order_type", "quantity", "product", "price"}` — no margin field.

### Whether margin affects execution decisions

No. `MarginTracker` is a calculator that is read by `PortfolioView` (for display) and by telemetry H.3 (`used_margin` in the `PortfolioSnapshot` surface, `portfolio_view.py:63`). It has no gating role. It does not affect order sizing, order routing, or rejection.

`SESSION_BOOTSTRAP.md` §"Current Gaps": **"Margin depth (§8). `MarginTracker` is a flat 20% rate, not SPAN — insufficient for real option-selling margin."**
`PROJECT_STATE.md` §Blocked: "Live derivatives trading is blocked on the SPAN margin engine (Planned #5)."

---

## 2. Capital Flow Audit

### Signal → Risk Validation

`handler.py:447`: `enforce_execution_authority(not self._processing_signal)` — blocks re-entry.
`handler.py:459`: `enforce_signal_idempotency(signal_id, self._seen_signals)` — blocks duplicate signals.

**STATUS: COMPLETE** — authority + idempotency gates exist and are enforced.

### Risk Validation → Position Sizing

`handler.py:468–501`: Entry signals are required to carry `sl_distance` and `risk_r` in `signal.metadata`. If missing with a real broker, conservative defaults are injected with a warning. These fields propagate to order metadata but **position sizing based on risk amount is not computed from them** — the signal carries a pre-computed `quantity` field that flows directly to `NormalizedOrder.quantity`.

`ExecutionConfig.default_quantity = 100.0` is the fallback. There is no `risk_amount / sl_distance`-based lot sizing in the handler.

**STATUS: PARTIAL** — `sl_distance`/`risk_r` are validated as present; actual risk-amount-to-quantity derivation is not performed inside the platform. The signal carries quantity; the handler does not compute it.

### Position Sizing → Margin Check

There is no margin check step. After quantity validation, the handler proceeds directly to `RiskManager.evaluate(order)`.

**STATUS: MISSING** — no margin check between sizing and broker submission.

### Margin Check → Execution

`RiskManager.evaluate` (`risk_manager.py:58–96`) checks: global kill switch, daily trade limit, max order quantity, symbol allow/deny list. Returns `RiskDecision(APPROVED/REJECTED)`. No margin field, no exposure field, no buying-power field.

`handler.py`: `enforce_risk_clearance(risk_approved, reason=...)` raises `ExecutionRuleError` if `REJECTED`, blocking the order.

**STATUS: PARTIAL** — pre-trade gates exist for quantity/symbol/kill-switch; margin-based gate is **MISSING**.

### Execution → Position Tracking

`handler.py:_handle_broker_fill` receives broker fills via the `subscribe_fills` callback. On a fill: `order_tracker.process_fill(fill)` → `position_tracker.update_from_fill(fill)` → G1 Wave 4B canonicalization at the fill seam → `pnl_tracker.update(fill, realized_pnl)` → group/TLP updates.

**STATUS: COMPLETE** — fill → position update path is implemented, tested (569 tests passing), and includes canonical identity upgrade at the fill seam (`handler.py:345–348`).

### Position Tracking → PnL Tracking

`pnl_tracker.py` tracks: `_realized_pnl` per symbol (accumulated from fill events), unrealized via `(current_price - avg_price) × quantity × multiplier × direction` (`pnl_tracker.py:46–57`). Multiplier-aware. Updated on every fill.

**STATUS: COMPLETE** — realized + unrealized PnL tracking is implemented. MTM equity is computed in `PortfolioView.snapshot()` as `cash_balance + unrealized_pnl`.

### Summary Table

| Stage | Status | Evidence |
|---|---|---|
| Signal | COMPLETE | `handler.py` authority + idempotency |
| Risk Validation | COMPLETE | `RiskManager.evaluate` — kill-switch / qty / symbol |
| Position Sizing | PARTIAL | `sl_distance`/`risk_r` present-checked; no qty derivation |
| Margin Check | **MISSING** | No call to `margin_tracker` in execution path |
| Execution | COMPLETE | `broker.place_order` via typed exception contract (MM7K.1) |
| Position Tracking | COMPLETE | `position_tracker.update_from_fill`, canonical at fill seam |
| PnL Tracking | COMPLETE | `pnl_tracker` realized + unrealized, multiplier-aware |

---

## 3. Existing Risk Infrastructure

### Current RiskManager capabilities

`core/execution/risk_manager.py`:

| Control | Classification |
|---|---|
| Global kill switch | COMPLETE |
| Daily trade limit (`max_daily_trades`) | COMPLETE |
| Max order quantity | COMPLETE |
| Symbol allow/deny list | COMPLETE |

### Pre-trade controls

| Control | Classification |
|---|---|
| Idempotency (duplicate signal rejection) | COMPLETE |
| Authority guard (re-entry prevention) | COMPLETE |
| Kill switch check | COMPLETE |
| Daily trade limit | COMPLETE |
| Max quantity per order | COMPLETE |
| Symbol allow/deny | COMPLETE |
| Signal carries `sl_distance`/`risk_r` | PARTIAL (defaults injected) |
| Margin check (buying power) | MISSING |
| Exposure check (portfolio-level) | MISSING |

### Exposure controls

`MarginTracker.get_exposure()` computes gross exposure but **is never called as a gate**. No pre-trade exposure limit exists. No notional-cap per underlying. No max portfolio notional.

**STATUS: PLACEHOLDER** — the calculation exists; enforcement does not.

### Drawdown controls

`ExecutionMetrics.update_drawdown(total_equity)` tracks `max_equity` and `max_drawdown_pct` (`handler.py:103–113`). `ExecutionConfig.max_drawdown_limit = 0.05` (5%). The drawdown check in `process_signal` calls `activate_kill_switch` if `current_dd > config.max_drawdown_limit`.

**STATUS: COMPLETE** — drawdown-to-kill-switch path exists and is live.

### Portfolio-level controls

`ExecutionConfig` has `max_portfolio_delta`, `max_portfolio_vega`, `max_gamma_exposure` (`handler.py:79–81`). `PortfolioGreeks` is instantiated in `ExecutionHandler.__init__` (`handler.py:172`). However `process_group_signal` (the group-based path that calls `_check_greek_limits`) **has no live caller** — confirmed by the G1 closeout audit (`G1_CLOSEOUT_REPORT.md`, `CHANGELOG_PLATFORM.md` 2026-06-11).

**STATUS: PLACEHOLDER** — Greek limit infrastructure exists; `_check_greek_limits` is unreachable from the live `LoopDriver` path.

### Derivatives-specific controls

No derivatives-specific pre-trade controls exist. No lot-size-validated exposure. No product-specific (NRML/MIS) margin lookup. No SPAN-based initial margin or exposure margin. No open interest–based limits.

**STATUS: MISSING**

---

## 4. Portfolio State Audit

### Services and ownership

| Concern | Owner | Location |
|---|---|---|
| Orders | `OrderTracker` | `core/execution/order_tracker.py` |
| Fills | `FillRepository` + `OrderTracker.process_fill` | `core/execution/persistence/fill_repository.py` |
| Positions | `PositionTracker` | `core/execution/position_tracker.py` |
| Capital / cash | `ExecutionMetrics.cash_balance` (flat float) | `handler.py:95,183` |
| Realized PnL | `PnLTracker._realized_pnl` | `core/execution/pnl_tracker.py` |
| Unrealized PnL | `PnLTracker.get_unrealized_pnl()` | computed on demand from positions + prices |
| MTM Equity | `PortfolioView.snapshot().mtm_equity` | `portfolio_view.py:62` (not in runtime) |
| Gross exposure | `MarginTracker.get_exposure()` | `margin_tracker.py:19` (not gated) |
| Used margin | `MarginTracker.get_used_margin()` | `margin_tracker.py:37` (not gated) |

### Persistence model

The canonical execution-truth substrate is **SQLite** (`data/execution.db` via `ExecutionStore`). Orders, fills, positions are stored there. Recovery restores from SQLite via `_replay_state()`.

`DuckDB` (`trading.db`) holds `trades` and `trade_context` — audit/analytics projection only. The `orders` and `positions` DDL in DuckDB is orphaned (noted in `PROJECT_STATE.md` §Phase 0: "the DuckDB `orders`/`positions` DDL is orphaned, slated for the Planned #2 schema-residue prune").

### Recovery model

`ExecutionHandler._replay_state()` (`handler.py:226–272`) re-loads orders from `OrderRepository.get_all()`, fills from `FillRepository.get_all()`, replays them into `OrderTracker` and `PositionTracker`, reconstructs groups, and restores `_trades_today`. Triggered on `load_db_state=True` at construction — how `build_runner` constructs the handler (`scripts/fno_runner.py`).

Recovery is COMPLETE for the ledger. Post-gate canonicalization (G1 Wave 3) upgrades restored instrument identity after the master is verified (live F&O only).

### Reconciliation model

`ReconciliationEngine.reconcile(broker_positions)` (`reconciliation.py`) compares `PositionTracker._positions` against broker positions by token-primary key (`instrument_token = NSE_FO|<token>`). Alerts: `QUANTITY_MISMATCH`, `ORPHANED_BROKER_POSITION`, `UNRECONCILABLE_UNMAPPED_POSITION`.

The re-key chain (MM7J.3, `token_rekey.py`) is COMPLETE. Live-wiring at `ExecutionMode.LIVE` is structurally present in `fno_runner.py` but gated on a first-hand authenticated non-empty broker position capture (live account has zero positions; not yet funded).

---

## 5. Derivatives Readiness Assessment

### F&O-specific infrastructure already existing

| Component | Status | Evidence |
|---|---|---|
| `CanonicalInstrument` + `InstrumentResolver` | COMPLETE | `core/instruments/canonical.py`, `resolver.py`; 4C.1–4C.7 COMPLETE |
| Instrument master DB (NSE_FO snapshot) | COMPLETE | `data/instruments/nse_fo_instruments.duckdb` (66k rows, 2026-06-09) |
| Daily master refresh job | COMPLETE (mechanism; OS task not installed) | `scripts/fetch_instrument_master.py`, `run_refresh()` |
| Startup master-readiness gate | COMPLETE | `core/instruments/master_readiness.py`, `LoopDriver._run_startup_gate` |
| F&O product/segment defaults | COMPLETE | `core/brokers/mapping/upstox.py` — NRML for FUTURE/OPTION |
| Broker payload via CanonicalInstrument | COMPLETE (4C.7) | `upstox_adapter.place_order` routes via `UpstoxMapping.to_broker()` |
| `OptionsContractSelector` (lot + expiry selection) | COMPLETE | `core/execution/options/selector.py`; master-sourced lot_size (65) |
| `GreeksCalculator` + `PortfolioGreeks` | COMPLETE (infrastructure) | `core/risk/greeks/` |
| Options analytics (PCR, GEX, OI, Max Pain) | COMPLETE | `core/analytics/options_analytics.py` |
| Entry-script composition root | COMPLETE (PAPER rung) | `scripts/fno_runner.py` |

### What SPAN would consume (dependencies already satisfied)

- `CanonicalInstrument.multiplier` (= lot size) — exists
- `CanonicalInstrument.asset_class` (OPTION / FUTURE) — exists
- Option strike, expiry, underlying from resolver — exists
- Position quantity from `PositionTracker` — exists
- Current prices (bar close) from `LoopDriver` tick — exists
- Greeks (delta, vega, gamma) from `GreeksCalculator` / `black76_engine.py` — exists

### What SPAN would need that does not currently exist

- SPAN parameter sets (scanning ranges, volatility shifts, price shifts) per underlying — **MISSING** (no SPAN config file, no Upstox margin API integration)
- Portfolio scan result aggregation (worst-case loss across scenarios) — **MISSING**
- Pre-trade buying-power check (initial margin + exposure margin) — **MISSING**; current `get_used_margin()` is a flat rate, not scenario-based
- Inter-contract spread credits (correlated positions netting) — **MISSING**
- Per-order margin reservation and release (position open/close margin delta) — **MISSING**
- Any hook from `MarginTracker` (or a successor) into `process_signal` — **MISSING**; the current architecture has a margin calculator with zero execution coupling

---

## 6. Margin Gap Analysis

| Mention | Where | Classification |
|---|---|---|
| "Margin validation" required before order submission | `PLATFORM_CONSTITUTION.md §4` (Principle 4) | MISSING |
| "Margin-aware execution" | `PLATFORM_CONSTITUTION.md §8` (Option Selling Requirements) | MISSING |
| "Margin checks" | `PLATFORM_CONSTITUTION.md §3` (Risk responsibilities) | MISSING |
| "`MarginTracker` flat 20% rate, not SPAN" | `SESSION_BOOTSTRAP.md §"Current Gaps" gap #3` | PLACEHOLDER |
| "Margin engine — a real SPAN/exposure model" | `PROJECT_STATE.md Planned #5` | PLANNED |
| "Live derivatives trading blocked on SPAN margin engine" | `PROJECT_STATE.md §Blocked` | PLANNED / BLOCKING |
| `MarginTracker.get_used_margin()` | `margin_tracker.py:37` | PLACEHOLDER (computes; not enforced) |
| `PortfolioSnapshot.used_margin` | `portfolio_view.py:64` | PLACEHOLDER (exposed in view; not gated) |
| `max_portfolio_delta / vega / gamma` in `ExecutionConfig` | `handler.py:79–81` | **LIVE** as of MM9.3-S1B (2026-06-28). `_check_greek_limits` reads them for portfolio-level delta+vega+gamma rejection. |
| SPAN (any occurrence in `core/` or `scripts/`) | Zero occurrences | DEFERRED (only in `PROJECT_STATE.md` Planned #5 description) |
| Buying power | Zero occurrences anywhere | MISSING |
| Derivatives margin | Zero occurrences in `core/` | MISSING |

---

## 7. Candidate MM9 Scope

Based strictly on repository evidence, the smallest coherent margin-related milestone is:

**A pre-trade margin gate that blocks order submission when estimated used margin would exceed a configured capital fraction — using the existing `MarginTracker` calculation as the estimate, wired into `process_signal` as a rejectable gate.**

This is the minimum that satisfies Constitution Principle 4 ("no trade without margin validation") for any live path. It does not require SPAN. It replaces the current zero-enforcement state with an explicit, testable gate.

### Dependencies already satisfied

- `MarginTracker` and `get_used_margin()` — exists, tested, multiplier-aware
- `ExecutionConfig` — has a natural slot for a `max_margin_utilisation` parameter
- `ExecutionMetrics.cash_balance` — the denominator for a margin ratio check
- `PositionTracker` — tracked positions are the numerator input
- `RiskManager.evaluate` — the existing gating pattern to follow
- Pre-trade gate hooks in `process_signal` — the control-flow location is established

### Dependencies not yet satisfied

- Current prices at gate time — `current_price` (bar close) covers only the current signal's symbol; a portfolio-wide margin check needs prices for all open positions (not always available at signal time in a single-symbol bar loop)
- No "free capital" concept — `cash_balance` is a flat float in `ExecutionMetrics`; it does not account for margin already locked by open positions
- No `margin_budget` or `max_margin_utilisation` field in `ExecutionConfig`

### Architectural risks

- Current prices for all open positions may not be available when the gate runs (single-symbol bar subscription). A portfolio-margin gate needs multi-symbol price state.
- `MarginTracker.margin_rate = 0.2` is a placeholder; wiring this as a blocking control before SPAN exists creates a regime where the margin estimate is wrong by construction for option selling (option margin is non-linear; depends on Greeks + volatility, not gross notional × 20%).
- Any change to `process_signal`'s gating logic is high-consequence — it is the sole execution path (ADR-006), tested by 569 tests.

### Operational risks

- Wiring a flat-rate gate for option-selling before SPAN may block valid trades (over-estimation) or permit invalid ones (under-estimation). The 20% rate has no basis in NSE/SEBI margin norms for index options.

---

## 8. Architectural Constraints

Any future margin implementation must preserve:

**ADR-001 — Ledger Is Truth.** Margin calculations are a derived view of ledger state; they must read trackers (position, order) but must not write to them. `MarginTracker` correctly observes `PositionTracker`; any successor must maintain the same one-directional dependency. Margin is used for display and gating; never a source of position truth.

**ADR-003 — Deterministic Operation.** A margin gate must be deterministic: same state + same prices → same margin decision. This precludes any non-deterministic external margin API call inside `process_signal` (e.g., polling Upstox's margin calculator in the hot path). Margin parameters must be local and reproducible. Replays must traverse the same gate as live runs.

**ADR-006 — LoopDriver is the sole orchestrator.** The margin gate belongs inside `process_signal` (or the RiskManager it calls), never in a separate parallel process or dashboard write-through. The gate must be part of the single execution path.

**Constitution Principle 4 — Risk Before Trading.** "Required before order submission: Position size, Risk amount, Stop definition, **Margin validation**, Risk clearance." A margin gate is not optional; it is a constitutional requirement. Any milestone that wires live derivatives trading without a margin gate violates Principle 4.

**Constitution §8 — Option Selling Requirements.** "The platform must support: Margin-aware execution." A flat-rate 20% estimator does not satisfy this for index option selling (where initial margin + exposure margin + assignment margin applies, and varies by strike distance and volatility). SPAN or an equivalent structural model is the constitutional target.

**ADR-004 — No Trading on Stale Data.** Extended by ADR-MM7F-1: a broker margin API that returns stale or unreadable data must be treated as unverifiable, and a gate that depends on it must fail-loud (refuse to start), not fall back to a vacuous pass.

**ADR-MM7F-1 — A Faulting Source Is a Startup Refusal.** If margin parameters are fetched from an external source at startup, a faulting fetch must be a refuse-to-start — consistent with how a faulting `broker_positions` callable is treated.

**`LoopDriver._run_startup_gate` ordering.** Any margin-budget initialization must slot after `_check_master_readiness()` and after `_canonicalize_restored_ledger()` (canonical instrument identity must be verified before margin calculations reference `ci.multiplier` or `ci.asset_class`). It must slot before the tick loop runs.

**CanonicalInstrument boundary (G1 closure guard).** A SPAN engine will consume `CanonicalInstrument` facts (lot_size, asset_class, underlying, strike, expiry). It must do so within `core/risk/` or `core/execution/` where `CanonicalInstrument` import is permitted, and must not allow the canonical object to cross broker-payload, persistence, or reconciliation boundaries. The G1 closure guard (`tests/g1/test_g1_closure_guard.py`) will catch violations.

---

## 9. One-Sentence Assessment

F:\Nifty currently has **a flat-rate 20% gross-exposure calculator (`MarginTracker`) that is instantiated in `ExecutionHandler`, exposed in `PortfolioView`, but never consulted in the execution decision path — making margin enforcement structurally absent despite the calculator existing** margin infrastructure, and the largest remaining capital-management gap is **the absence of any pre-trade buying-power gate in `process_signal`, without which the Constitution's "no trade without margin validation" requirement (Principle 4) is unmet and live derivatives trading cannot proceed safely**.
