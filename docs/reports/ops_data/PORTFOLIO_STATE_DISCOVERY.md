# PORTFOLIO_STATE_DISCOVERY.md

**Type:** Architecture discovery & planning — **no code written, no code modified, no commits.**
**Date:** 2026-06-06
**Scope:** Inventory of all existing portfolio, position, account, exposure, margin, and PnL infrastructure in `F:\Nifty`.
**Governing law:** `docs/PLATFORM_CONSTITUTION.md` v1.0 · `docs/ARCHITECTURE_DECISIONS.md` (ADR-001..006) · `docs/DRIVER_SPECIFICATION.md` v1.0.
**Basis:** direct source read of `core/execution/*`, `core/risk/greeks/*`, `core/database/*`, `core/brokers/*`, `app_facade/*`; cross-checked against `docs/PLATFORM_INVENTORY.md` and `docs/PROJECT_STATE.md`.

> This document is a survey and a recommendation. It implements nothing. Every claim carries a `file:line` anchor so it is checkable, not asserted.

---

> **STATUS UPDATE (2026-06-07) — Phase 0 Hygiene COMPLETE.** The two confirmed defects below are **RESOLVED** (TDD, +12 tests, full suite 201 → 213, no regressions): **§4.6** PortfolioGreeks dict-iteration and **§4.5** broker `get_positions` Position-constructor mismatch (commit *"Fix portfolio greeks aggregation and broker position mapping"*).
>
> The **ledger-ownership recommendation** in §3 / §5 / §6 — *SQLite `data/execution.db` = canonical execution truth; DuckDB `trading.db` = audit/analytics projection* — is recorded as **APPROVED ARCHITECTURAL DIRECTION, not implemented fact.** No persistence change, data migration, or DDL prune was made in Phase 0; the orphaned DuckDB `orders`/`positions` DDL prune remains **Planned #2**. Strengthening evidence found during Phase 0: the live idempotency gate uses the SQLite-derived `_seen_signals` registry (`handler.py:392,227`), while the DuckDB `trades` query `_is_signal_already_executed` (`handler.py:686`) has **no live caller** — DuckDB is not an execution authority.
>
> All other gaps (§4.1–4.4, §4.7–4.9) and the PortfolioView / H.3 / margin work remain **open** as described below.

---

## 0. Executive summary

`F:\Nifty` has **component-level** position/PnL/margin/greeks infrastructure but **no portfolio abstraction**. There is exactly one class in the tree whose name contains Portfolio, Account, Ledger, or Exposure — `PortfolioGreeks` (`core/risk/greeks/portfolio_greeks.py:9`) — and it is unwired and contains a defect. Everything else is a set of per-symbol trackers hanging off `ExecutionHandler`.

Five findings dominate everything below:

1. **There is no "ledger" object.** "The ledger" in ADR-001 is a *concept* implemented by four cooperating pieces (`position_tracker`, `pnl_tracker`, the persistence repos, and `ExecutionMetrics.cash_balance`) — there is no single surface that answers "what does the book look like."
2. **The ledger is split across two physical databases.** Position/fill/order *truth* persists to **SQLite** (`data/execution.db`); trade-audit/idempotency persists to **DuckDB** (`trading.db`). CLAUDE.md calls DuckDB the "single source of truth," but recovery actually restores from SQLite.
3. **Equity = cash only.** No live mark-to-market exists anywhere in a running path. Unrealized PnL, exposure, and portfolio greeks all require a `current_prices`/vol map that **nothing live injects**.
4. **There is no account-state infrastructure at all.** No funds/holdings/margin broker endpoints; `cash_balance` is seeded from a hardcoded `initial_capital=100000.0`.
5. **Broker reconciliation is currently impossible, not merely vacuous** — the one broker-position read constructs the `Position` model with wrong kwargs and would raise `TypeError`.

The recommended path is **not** a new service concept — it is the two pillars already named in `PLATFORM_INVENTORY.md` §4: **"Ledger as an explicit surface"** (#2) and **"Margin engine"** (#3), plus the in-flight **LoopDriver Phase H.3 Position Publishing**. The recommendation is to consolidate, not invent.

---

## 1. Current-state architecture map

### 1.1 The component graph (all portfolio-relevant state)

```
                         ExecutionHandler  (core/execution/handler.py:112)
                         the de-facto "portfolio" — owns every tracker
                                       │
   ┌──────────────┬──────────────┬────┴───────┬───────────────┬──────────────┐
   ▼              ▼              ▼             ▼               ▼              ▼
PositionTracker  PnLTracker   MarginTracker  PortfolioGreeks  GroupPnLTracker  ExecutionMetrics
position_tracker pnl_tracker  margin_tracker  (risk/greeks/   groups/group_     (handler.py:83
.py:17           .py:12       .py:10          portfolio_       pnl.py:14         dataclass)
   │              │            │              greeks.py:9)      │                │
 POSITIONS      REALIZED      GROSS          NET GREEKS        PER-GROUP        CASH / EQUITY /
 (per symbol)   PnL accum     EXPOSURE       (unwired,         REALIZED PnL     DRAWDOWN
   │            + UNREALIZED  + flat-20%      defective)        + UNREALIZED      (cash only)
   │            (needs prices) margin                                            │
   ▼            (needs prices)                                                   ▼
 Position        realized only                                          logs/execution_metrics.json
 (immutable      live                                                   (handler.py:191 _persist_metrics)
  snapshot,
  position_
  models.py:21)
   │
   ▼  persist (SQLite)
 PositionRepository ──► ExecutionStore ──► data/execution.db   (SQLite: orders, fills, positions)
 (persistence/position_repository.py:8)    (persistence/execution_store.py:11)
```

### 1.2 Component inventory

| Component | Location | Purpose | State held |
|---|---|---|---|
| **`ExecutionHandler`** | `core/execution/handler.py:112` | OMS/EMS spine; constructs and owns all trackers (`handler.py:150-166`). | Acts as the *implicit* portfolio root. |
| **`PositionTracker`** | `core/execution/position_tracker.py:17` | Single source of position truth; netting/flip/avg-price math (`update_from_fill`, `:49`). | `_positions: Dict[str, Position]` in memory. |
| **`Position`** | `core/execution/position_models.py:21` | Immutable per-symbol snapshot (`side`, `quantity`, `avg_price`). | — |
| **`PnLTracker`** | `core/execution/pnl_tracker.py:12` | Realized PnL accumulator + unrealized calc *given prices*. | `_realized_pnl: Dict[str,float]` (`:15`). |
| **`MarginTracker`** | `core/execution/margin_tracker.py:10` | Gross exposure + flat-rate (`margin_rate=0.2`) used-margin estimate. | None (derives from positions + prices). |
| **`PortfolioGreeks`** | `core/risk/greeks/portfolio_greeks.py:9` | Net portfolio greeks aggregation. | None; **unwired + defective** (§4.6). |
| **`GroupPnLTracker`** | `core/execution/groups/group_pnl.py:14` | Multi-leg (spread) realized + unrealized PnL. | `_group_realized_pnl: Dict[UUID,float]`. |
| **`ExecutionMetrics`** | `core/execution/handler.py:83` | Account-ish scalars: `cash_balance`, `max_equity`, `daily_pnl`, `max_drawdown_pct`. | The closest thing to an "account." |
| **`ReconciliationEngine`** | `core/execution/reconciliation.py:20` | Diff internal positions vs broker positions → alerts. | None (pure compare). |
| **Persistence repos** | `core/execution/persistence/{order,fill,position}_repository.py` | Durable order/fill/position store + restore. | SQLite `data/execution.db`. |
| **`TradingWriter`** | `core/database/writers.py:181` | Writes `trades` + `trade_context` (TLP) and exit updates. | DuckDB `trading.db`. |

### 1.3 The split-ledger map (critical)

Position/PnL "truth" is **not** in one place. It is split across two engines with overlapping table names:

| Concern | Physical store | Written by | Read / restored by |
|---|---|---|---|
| Orders, **Fills**, **Positions** (operational truth) | **SQLite** `data/execution.db` | `OrderRepository` / `FillRepository` / `PositionRepository` (via `ExecutionStore`, `execution_store.py:20` DDL) | `ExecutionHandler._replay_state()` (`handler.py:219`) — **this is the recovery source of truth.** |
| **Trades** (audit), `trade_context` (TLP), exit MAE/MFE | **DuckDB** `trading.db` | `TradingWriter.save_trade` / `update_trade_exit` (`writers.py:181,242`) | Idempotency cross-check `SELECT … FROM trades` (`handler.py:686`). |
| `orders` / `positions` tables **also defined in DuckDB** | DuckDB `trading.db` (`schema.py:57,93`) | **Not written by the execution path** (writers.py only `INSERT INTO trades`). | Orphaned DDL — legacy twins. |

**Consequence:** `_replay_state()` restores positions/fills from **SQLite**, while idempotency reads `trades` from **DuckDB**. The DuckDB `orders`/`positions` tables (`schema.py:57,93`) are dead structure. CLAUDE.md's "DuckDB = single source of truth" is **false for execution truth** — that lives in SQLite.

### 1.4 Where this state is consumed at runtime

| Consumer | What it reads | Notes |
|---|---|---|
| `LoopDriver` (Phase H.1/H.2) | `handler.metrics`, `handler._trades_today`, `handler._kill_switched`, `watchdog.data_healthy` | `core/runtime/driver.py` — read-only for telemetry (ADR-001). Phase **H.3 (positions) not yet built.** |
| `RuntimeWatchdog` | `execution.metrics.cash_balance` for `heartbeat.json` `equity` field | Documented simplification: equity = cash, not cash+MTM (`DRIVER_SPECIFICATION.md` §9.4). |
| `OpsFacade.get_live_metrics` | `execution.metrics` only — signals/trades/drawdown (`ops_facade.py:23-30`) | **Does NOT read positions, PnL, margin, or greeks.** The dashboard surfaces no book. |
| `options_publisher` | (option-chain structural data; not the ledger) | Cross-role only. |

**No facade reads `position_tracker`, `pnl_tracker`, `margin_tracker`, or `portfolio_greeks`.** The portfolio is invisible to the UI today.

---

## 2. Ownership analysis

| Concern | Current owner | Correct per constitution? |
|---|---|---|
| Position truth | `PositionTracker`, owned by `ExecutionHandler` (`handler.py:150`) | ✅ ADR-001 — "position truth lives in the execution trackers." |
| PnL truth | `PnLTracker` + `GroupPnLTracker`, owned by handler | ✅ but realized-only is live (§4). |
| Account/cash truth | `ExecutionMetrics.cash_balance`, owned by handler (`handler.py:174`) | ⚠️ Exists but is a hardcoded seed, not broker-sourced. |
| Margin | `MarginTracker`, owned by handler | ⚠️ Flat-rate placeholder, not SPAN (`PLATFORM_INVENTORY.md` §2.4). |
| Exposure | `MarginTracker.get_exposure` (`margin_tracker.py:19`) | ✅ gross-notional only; no netting/portfolio view. |
| Greeks aggregation | `PortfolioGreeks`, owned by handler (`handler.py:166`) | ⚠️ Owned correctly; non-functional (§4.6). |
| Durable ledger | persistence repos (SQLite) + `TradingWriter` (DuckDB) | ⚠️ **Split ownership across two DBs** — no single ledger owner. |
| Reconciliation | `ReconciliationEngine`, owned by handler (`handler.py:158`) | ✅ owned correctly; broker feed missing (§4.5). |
| Recovery | `ExecutionHandler._replay_state()` (`handler.py:219`) | ✅ ADR-001 / §11.2 — driver reuses, never reimplements. |
| Telemetry of the book | `LoopDriver` read-only consumer | ✅ ADR-001 — driver reads, never writes (positions pending H.3). |

**The single structural truth of ownership:** `ExecutionHandler` is the *de-facto* portfolio. There is no `Portfolio`/`Account`/`Ledger` object — every concern is a tracker attribute on the handler, with **no unifying read surface**. The seed of one exists: `ExecutionHandler.get_stats()` (`handler.py:800`) already assembles realized/unrealized/used-margin into one dict — but it requires `current_prices` that no live caller supplies, and no facade calls it.

---

## 3. ADR-001 ("Ledger Is Truth") compliance analysis

Authority chain (ADR-001): `Exchange → Broker → Execution Engine → Ledger → Risk Engine → Dashboard`.

| ADR-001 requirement | Status | Evidence |
|---|---|---|
| Position/PnL truth lives in execution trackers | ✅ **Compliant** | `PositionTracker`/`PnLTracker` are the only mutators; mutated solely via `_handle_broker_fill` (`handler.py:267-289`). |
| Dashboard/facades are read-only | ✅ **Compliant** | `OpsFacade` only reads `metrics` (`ops_facade.py`); no write path. |
| Durable, reconstructable ledger; recovery restores from it | ⚠️ **Partial** | Restore works (`_replay_state`, `handler.py:219`) **but from SQLite only**; the "single source of truth" is split (§1.3), and the durable record is two stores that can drift. |
| Single source of truth | ❌ **Violated in substrate** | Two `positions` tables + two `orders` tables across SQLite and DuckDB (`execution_store.py:55`, `schema.py:93`). Truth is SQLite; DuckDB twins are orphaned. This is *soft residue*, not a hard ADR-002 violation, but it directly contradicts "single source." |
| Reconciliation detects/corrects vs broker, never lets broker overwrite | ⚠️ **Structurally present, operationally dead** | `ReconciliationEngine.reconcile` (`reconciliation.py:24`) is correct, but no working broker-position feed exists (§4.5), so it never runs against reality. |
| Telemetry/driver never writes back to the ledger | ✅ **Compliant** | `LoopDriver` reads `handler.*` for telemetry only; H.3 spec keeps positions read-only (`DRIVER_SPECIFICATION.md` §10.4). |

**Verdict:** ADR-001 is honored at the *behavioral* level (one mutation path; read-only consumers) but **compromised at the substrate level** — there is no single physical ledger, and "single source of truth" is contradicted by the SQLite/DuckDB split. Any Portfolio Service must **not** add a third store or a second mutation path; it must read the one true ledger (SQLite execution truth) and expose it.

---

## 4. Gap analysis

### 4.1 No portfolio abstraction (the headline gap)
There is no object that answers "what is the book." State is scattered across five trackers + `ExecutionMetrics`, joined only inside `handler.get_stats()` (`handler.py:800`) — which is unreachable live (needs prices). **Pillar #2 from `PLATFORM_INVENTORY.md` §4 ("Ledger as an explicit surface") is unbuilt.**

### 4.2 Equity = cash only; no live mark-to-market
- `RuntimeWatchdog` heartbeat `equity` = `cash_balance` only (`DRIVER_SPECIFICATION.md` §9.4; `handler.py:196`).
- `pnl_tracker.get_unrealized_pnl(current_prices, …)` (`pnl_tracker.py:29`) and `margin_tracker.get_exposure(current_prices)` (`margin_tracker.py:19`) and `portfolio_greeks.calculate_portfolio_greeks(market_prices, …)` (`portfolio_greeks.py:17`) **all require a price/vol map that nothing live injects.**
- **Net:** unrealized PnL, exposure, and portfolio greeks are *capabilities*, not *live facts*. Only realized PnL is live.

### 4.3 `daily_pnl` is never written
`ExecutionMetrics.daily_pnl` defaults `0.0` (`handler.py:90`) and `_update_equity_metrics` (`handler.py:785`) updates only `cash_balance` and drawdown — **`daily_pnl` is never assigned.** `get_stats()` returns it verbatim (`handler.py:815`), so any consumer of "daily PnL" reads a constant zero.

### 4.4 No broker account state
- No funds/holdings/margin endpoints anywhere (`grep` over `core/brokers/*`, `core/api/upstox_client.py` → **no matches**).
- `cash_balance` / `max_equity` seed from hardcoded `initial_capital=100000.0` (`handler.py:127,174`). The platform never learns the real account balance.

### 4.5 Broker reconciliation is impossible, not vacuous
- `BrokerAdapter` ABC has **no** `get_positions` (`broker_base.py:6-35`) — only `place_order`/`cancel_order`/`subscribe_fills`.
- `UpstoxBrokerAdapter.get_positions()` exists (`upstox_adapter.py:125`) but constructs `Position(symbol=…, quantity=…, avg_entry_price=…, last_update=…)` — kwargs that the `Position` model **does not accept** (it takes `avg_price` / `last_updated`, `position_models.py:30-39`). This raises `TypeError` at runtime. So the only broker-position read is **broken**, and it isn't on the ABC the driver depends on. This concretely backs `PROJECT_STATE.md` Planned #6.

### 4.6 `PortfolioGreeks` is unwired and defective
- **Defect:** `calculate_portfolio_greeks` iterates `for position in positions:` where `positions = get_all_positions()` returns a **dict** (`portfolio_greeks.py:32-33`; `position_tracker.py:166`). Iterating a dict yields **keys (symbol strings)**, then passes a `str` where a `Position` is expected → `AttributeError` on first non-empty book.
- **Unwired:** no live caller injects `market_prices`/`volatilities`/`time_to_expiry_map`. `handler._check_greek_limits` (`handler.py:706`) sidesteps the portfolio aggregate entirely and checks only the *marginal* order delta (`handler.py:745`), with current portfolio greeks explicitly skipped (`handler.py:737-744`).

### 4.7 Margin is a flat-rate placeholder
`MarginTracker(margin_rate=0.2)` (`margin_tracker.py:11`) → `used_margin = gross_exposure × 0.20`. No SPAN, no option-selling margin, no netting/hedge offset. Insufficient for §8 option selling (`PLATFORM_INVENTORY.md` §2.4, Planned #5). **Live derivatives trading is blocked on this** (`PROJECT_STATE.md` Blocked).

### 4.8 Exposure is gross-notional only
`get_exposure` (`margin_tracker.py:19`) sums `quantity × price × multiplier` per symbol. No long/short netting, no per-underlying aggregation, no sector/concentration view — yet the constitution names "Portfolio exposure tracking" (§9) and "Exposure monitoring" (§3 Risk) as platform responsibilities.

### 4.9 Multi-leg PnL exists but is option-blind on greeks
`GroupPnLTracker` (`group_pnl.py:14`) tracks realized + unrealized per group correctly, but unrealized still needs `current_prices` (`group_pnl.py:36`) — same MTM gap as §4.2. Group-level greeks/margin do not exist.

### 4.10 Gap-to-constitution summary

| Constitution requirement | Present? | Gap |
|---|---|---|
| §3 Ledger: Positions / PnL / Trade history | Partial | Split substrate; realized-only PnL live. |
| §3 Risk: Exposure monitoring | Weak | Gross-notional only; no live prices. |
| §3 Risk: Greeks monitoring / Portfolio Greeks aggregation (§8) | Defective | Unwired + dict-iteration bug. |
| §3 Risk: Margin checks (§8 margin-aware) | Placeholder | Flat-20%, not SPAN. |
| §3 Reconciliation: Broker reconciliation | Dead | Engine present; broker feed broken. |
| §9 Equity Futures: Portfolio exposure tracking | Weak | No netting/concentration. |
| Account state (funds/holdings/balance) | Absent | Hardcoded seed only. |

---

## 5. Recommended Portfolio Service architecture

> **This is the realization of two already-named pillars** (`PLATFORM_INVENTORY.md` §4 #2 "Ledger as an explicit surface" and #3 "Margin engine"), and the natural consumer for **LoopDriver Phase H.3 Position Publishing** (`DRIVER_SPECIFICATION.md` §10.4). It is not a new concept and **must not** become a new authority.

### 5.1 Hard constraints (state these in the implementation, so it cannot be mis-built)

1. **Read-only consumer of the single ledger truth (ADR-001).** The service computes *views* (MTM equity, exposure, net greeks); it **never** mutates positions/PnL. The sole mutation path stays `broker fill → ExecutionHandler._handle_broker_fill → trackers` (`handler.py:267`).
2. **No second position-truth path.** It reads `PositionTracker` / `PnLTracker` (or their consolidation), never a parallel store. It must not reconstruct positions from the journal or from DuckDB (`DRIVER_SPECIFICATION.md` §15.7).
3. **Not a runtime orchestrator (ADR-006).** It is fed by the `LoopDriver`/`ExecutionHandler`; it is **not** a new loop and never calls `process_signal`. If a price feed is needed for MTM, it is injected *by the driver tick*, not pulled by a second loop.
4. **No `Platform → Strategy` import (ADR-002).** Pure infra; forbidden-import scan over its package must be empty.
5. **No new physical store.** It reads the existing ledger; persistence (if any) reuses the SQLite execution substrate. Resolving the SQLite/DuckDB split is a prerequisite, not part of this service (§6 Phase 0).

### 5.2 Shape: a read-side aggregation surface, not a new owner

```
              current_prices (injected by LoopDriver tick — the ONE MTM seam)
                              │
                              ▼
        ┌─────────────────────────────────────────────────┐
        │            PortfolioView  (read-only)            │   core/execution/  (beside the trackers)
        │  built from a price snapshot + the live ledger   │   — NOT a new package owning truth
        ├─────────────────────────────────────────────────┤
        │ positions:   PositionTracker.get_all_positions() │ ◄── single source (handler.py:150)
        │ realized:    PnLTracker.get_realized_pnl()        │
        │ unrealized:  PnLTracker.get_unrealized_pnl(px)    │
        │ mtm_equity:  cash_balance + Σ unrealized          │ ◄── fixes "equity = cash only" (§4.2)
        │ exposure:    MarginTracker.get_exposure(px)       │
        │ used_margin: MarginEngine.requirement(positions)  │ ◄── pillar #3 (replaces flat-20%)
        │ net_greeks:  PortfolioGreeks(px, iv, tte)         │ ◄── after §4.6 defect fixed
        └─────────────────────────────────────────────────┘
                              │ read-only
            ┌─────────────────┼─────────────────────┐
            ▼                 ▼                       ▼
   LoopDriver H.3       OpsFacade (NEW              RiskEngine (future):
   publish_positions    get_portfolio())            pre-trade checks read
   telemetry.positions  → dashboard book view       the SAME view (no 2nd calc)
```

Three design choices, each constitution-anchored:

- **It is a *view builder*, not a stateful service.** Given a price snapshot, it returns an immutable portfolio snapshot. This keeps it deterministic (ADR-003) and side-effect-free (it cannot become a hidden authority). It is the generalization of the existing `handler.get_stats()` seed (`handler.py:800`), made reachable by supplying the price map the driver already has at `bar.close`.
- **The MTM price seam is the driver tick.** The single honest place to get a price is the `LoopDriver`'s per-bar `bar.close` (already used for routing, `DRIVER_SPECIFICATION.md` §8.1). The driver builds the view each telemetry interval and publishes it (H.3). No second price feed, no second loop (ADR-006).
- **The dashboard finally sees the book.** A new read-only `OpsFacade.get_portfolio()` exposes the view (positions, MTM equity, exposure, greeks) — the gap in §1.4. Read-only, so ADR-001 holds.

### 5.3 What it explicitly is NOT
- ❌ Not a new source of position/PnL truth (ADR-001).
- ❌ Not a runtime loop / orchestrator (ADR-006).
- ❌ Not a margin *policy* engine itself — it *consumes* a `MarginEngine` (pillar #3); SPAN is its own work item (Planned #5).
- ❌ Not a broker-account fetcher — funds/holdings ingestion is a separate broker-layer item (§4.4), though the view should *display* real cash once that lands.

---

## 6. Recommended implementation phases

Ordered by dependency and by "unblocks the most." Each phase is independently shippable and constitution-checkable. **None of this is started here — it is the proposed sequence.**

### Phase 0 — Prerequisite hygiene (no new features)
- **Resolve the split-ledger (§1.3, §3).** Decide the single execution-truth substrate (SQLite `execution.db` is the de-facto truth today via `_replay_state`). Prune the orphaned DuckDB `orders`/`positions` DDL (`schema.py:57,93`) — this is already `PROJECT_STATE.md` Planned #2 (strategy-residue / schema prune). *Rationale: a Portfolio Service over two stores inherits the drift.*
- **Fix the two latent defects** so the existing components are trustworthy: `PortfolioGreeks` dict-iteration (`portfolio_greeks.py:32`) and `UpstoxBrokerAdapter.get_positions` kwargs (`upstox_adapter.py:135`). Defects, not redesign.

### Phase 1 — `PortfolioView` read surface (pillar #2)
- Generalize `handler.get_stats()` (`handler.py:800`) into an immutable `PortfolioView` built from `(ledger, current_prices)`: positions, realized/unrealized PnL, **MTM equity** (fixes §4.2), gross exposure, used margin.
- Wire `daily_pnl` correctly (close §4.3) or remove the dead field.
- Read-only; no new store; no mutation path. Unit-testable with a fixed price map (determinism, ADR-003).

### Phase 2 — Driver H.3 Position Publishing consumes the view
- Implement `DRIVER_SPECIFICATION.md` §10.4 (`PROJECT_STATE.md` Planned #1, Phase H.3) by publishing `PortfolioView` positions on `telemetry.positions.{node}`, same cadence/best-effort as H.1/H.2. The driver supplies `bar.close` as the price seam (§5.2). Closes the last §10 telemetry gap.

### Phase 3 — Dashboard portfolio view
- Add read-only `OpsFacade.get_portfolio()` + a dashboard tile (closes §1.4 — the book is invisible today). Strictly read-only (ADR-001).

### Phase 4 — Margin engine (pillar #3, `PROJECT_STATE.md` Planned #5)
- Replace flat-rate `MarginTracker` (`margin_tracker.py`) with a real SPAN/exposure model; `PortfolioView.used_margin` switches to it. **Unblocks live option selling** (`PROJECT_STATE.md` Blocked). Independent, large; sequenced after the view exists so there is a consumer.

### Phase 5 — Broker account + reconciliation feed (`PROJECT_STATE.md` Planned #6)
- Add `get_positions`/`get_funds`/`get_holdings` to the `BrokerAdapter` ABC (`broker_base.py`), implement on `UpstoxBrokerAdapter`, normalize to the ledger `Position` model. Feed the **already-built** `ReconciliationEngine` (`reconciliation.py:24`) and the LoopDriver startup gate's `broker_positions` source (`DRIVER_SPECIFICATION.md` §11.3). Replace hardcoded `initial_capital` with real broker cash (closes §4.4). Convert a raising `broker_positions()` into startup-refusal → journal → STOPPED (Planned #6's stated contract).

### Phase 6 — Portfolio greeks live (§8)
- With Phase 5's price/IV inputs flowing, wire `PortfolioGreeks` into the live view for true portfolio-greeks monitoring (Constitution §8). Depends on the §4.6 fix (Phase 0) and a live IV/price source.

### Dependency order
```
Phase 0 (hygiene) ──► Phase 1 (PortfolioView) ──► Phase 2 (H.3 telemetry)
                                  │                       └─► Phase 3 (dashboard)
                                  ├─► Phase 4 (SPAN margin)  ── unblocks live option selling
                                  └─► Phase 5 (broker account + recon) ──► Phase 6 (live greeks)
```

---

## Appendix A — Source anchors (every claim is checkable)

| Claim | Anchor |
|---|---|
| Handler owns all trackers | `core/execution/handler.py:150-166` |
| Position truth + netting math | `core/execution/position_tracker.py:17,49` |
| Realized-only PnL accumulator | `core/execution/pnl_tracker.py:15,29` |
| Flat-20% margin | `core/execution/margin_tracker.py:11,37` |
| Equity = cash; daily_pnl never set | `core/execution/handler.py:90,785,815` |
| `get_stats` seed (needs prices) | `core/execution/handler.py:800` |
| Hardcoded initial capital | `core/execution/handler.py:127,174` |
| SQLite execution store DDL | `core/execution/persistence/execution_store.py:55` |
| DuckDB orphaned orders/positions DDL | `core/database/schema.py:57,93` |
| TradingWriter writes only `trades` to DuckDB | `core/database/writers.py:181,242` |
| Recovery restores from SQLite | `core/execution/handler.py:219-265` |
| Idempotency reads DuckDB `trades` | `core/execution/handler.py:686-694` |
| Reconciliation engine (no broker feed) | `core/execution/reconciliation.py:24` |
| BrokerAdapter ABC lacks get_positions | `core/brokers/broker_base.py:6-35` |
| Broken broker get_positions kwargs | `core/brokers/upstox_adapter.py:125-143` vs `core/execution/position_models.py:30-39` |
| PortfolioGreeks dict-iteration defect | `core/risk/greeks/portfolio_greeks.py:32-33` |
| Greek limit checks marginal only | `core/execution/handler.py:706-747` | **RESOLVED** by MM9.3-S1B (2026-06-28): portfolio-level delta+vega+gamma aggregation. |
| Dashboard reads metrics only | `app_facade/ops_facade.py:23-30` |
| Only Portfolio* class in tree | `core/risk/greeks/portfolio_greeks.py:9` (grep: no Account/Ledger/Exposure classes) |
| Pillars #2/#3 already named | `docs/PLATFORM_INVENTORY.md` §4 |
| H.3 position publishing planned | `docs/PROJECT_STATE.md` Planned #1; `docs/DRIVER_SPECIFICATION.md` §10.4 |
