# FNO_PRODUCT_DISCOVERY.md

**Type:** Architecture discovery & planning — **no code written, no code modified, no commits.**
**Date:** 2026-06-07
**Scope:** Inventory of all existing F&O product infrastructure in `F:\Nifty` — instruments, contracts, options, futures, expiry handling, margin handling, broker metadata — with a canonical-model proposal and the SPAN / reconciliation dependency graphs.
**Governing law:** `docs/PLATFORM_CONSTITUTION.md` v1.0 · `docs/ARCHITECTURE_DECISIONS.md` (ADR-001..006) · `docs/PROJECT_STATE.md` (Planned #4 F&O product model, #5 SPAN margin, #6 broker reconciliation).
**Basis:** direct source read of `core/instruments/*`, `core/brokers/*`, `core/execution/{margin_tracker,reconciliation,order_models,position_models,handler}.py`, `core/execution/options/selector.py`, `core/data/options_provider.py`, `scripts/fetch_instrument_master.py`; plus a filesystem check of `data/instruments/`.

> This document is a survey and a recommendation. It implements nothing. Every claim carries a `file:line` anchor so it is checkable, not asserted. It is the F&O analog of `docs/reports/PORTFOLIO_STATE_DISCOVERY.md`.

---

## 0. Executive summary

The platform has a **partial, three-way-divergent** F&O model. There is an instrument class hierarchy, an authoritative instrument-master schema, and an options-execution path — but they do not share a single source of truth, and three of the four core flows for live derivatives are broken or absent.

Six findings dominate:

1. **There is no canonical instrument identity.** A contract is described by *three* different identifiers that are never reconciled: the constructed **display symbol** (`NIFTY26FEB2522500CE`), the broker **`instrument_key`** (`NSE_FO|54710`), and the broker **`tradingsymbol`**. The order path ships the display symbol as the Upstox `instrument_token` (`upstox_adapter.py:86`) with **no resolution step** — so live F&O order placement cannot work (equities survive only because `NSE_EQ|…` passes through unchanged).
2. **Contract metadata has three divergent hardcoded sources** (`OptionsContractSelector`, `OptionsProvider`, `InstrumentParser`) plus an authoritative DB (`InstrumentMaster`) that **none of the execution path consults — and which is not even present on disk** (`data/instruments/` does not exist). Live behavior is therefore entirely the hardcoded fallbacks.
3. **`multiplier` and `lot_size` are two unreconciled contract-size concepts.** Exposure uses `instrument.multiplier` (`margin_tracker.py:35`), which is `1.0` for every parsed instrument — so F&O notional is **understated** and `lot_size` (the real contract multiplier) is ignored in the margin path.
4. **Futures are structurally unreachable.** A `Future` class exists (`future.py:6`) but `InstrumentParser.parse` only ever produces an `Option` or an `Equity` (`instrument_parser.py:14-46`) — nothing in the signal→order path constructs a `Future`.
5. **Margin is a flat 20% placeholder** (`margin_tracker.py:11,39`) — no SPAN, no option-selling margin, no multi-leg offset — even though the multi-leg grouping infrastructure (`OrderGroup.group_id`, `GroupPnLTracker`) and the IV/greeks engine (`black76_engine`) needed to feed SPAN already exist.
6. **The broker layer is split and incomplete:** two divergent `BrokerAdapter` ABCs, the execution handler depends on the one **without** `get_positions` (`handler.py:47` → `broker_base.py`), the concrete `UpstoxAdapter` implements the **other** (`base.py`), order product is hardcoded to intraday (`product:"I"`, `upstox_adapter.py:82`), and there are **no funds/holdings/margin endpoints anywhere**.

The single structural root, made explicit in §2: **both SPAN and reconciliation sit downstream of one missing layer — a canonical instrument identity/resolution seam over the instrument-master DB.** Build that first; SPAN (Planned #5), the F&O product model (Planned #4), and broker reconciliation (Planned #6) all consume it.

---

## 1. Current-state inventory

### 1.1 The instrument model (in-memory class hierarchy)

| Component | Location | Carries | Notes |
|---|---|---|---|
| `InstrumentType` | `core/instruments/instrument_base.py:6` | EQUITY / FUTURE / OPTION | No INDEX, no FUTURE-vs-OPTION segment. |
| `Instrument` (base) | `instrument_base.py:12` | `symbol`, `type`, `multiplier=1.0` | Frozen dataclass. `multiplier` defaults 1.0 and is **never set from the master**. |
| `Equity` | `equity.py:6` | — | Hardcodes `multiplier=1.0`. |
| `Option` | `option.py:12` | `underlying`, `expiry`, `strike`, `option_type`, `lot_size=1` | Carries `lot_size` **and** `multiplier` separately (the duality, §3.3). |
| `Future` | `future.py:6` | `underlying`, `expiry` | **No `lot_size`, no strike.** Structurally never built by the parser (§3.1). |
| `OptionType` | `option.py:7` | CALL=`CE` / PUT=`PE` | — |
| `InstrumentParser` | `instrument_parser.py:8` | — | `parse()` → `Option` (regex `^([A-Z]+)(\d2)([A-Z]3)(\d2)(\d+)(CE\|PE)$`) **or** `Equity` fallback. **Never a `Future`.** Parsed options get `lot_size=1`, `multiplier=1.0` (`:38-40`) — the real lot size is discarded. |

### 1.2 The instrument master (authoritative data, DuckDB)

| Component | Location | Notes |
|---|---|---|
| `InstrumentMaster` | `core/instruments/instrument_db.py:24` | Read-only lookup: `resolve(tradingsymbol)→instrument_key`, `resolve_option(name,expiry,strike,type)`, `find_options`, `get_lot_size(instrument_key)`, `resolve_active_future(name,prefix,as_of)`. The **only** component that knows the real `instrument_key`/`lot_size`. |
| Master schema | `scripts/fetch_instrument_master.py:39-47` | `instruments(instrument_key PK, tradingsymbol, name, expiry, strike, instrument_type, lot_size, exchange)`. Segments ingested: **NSE_FO, MCX_FO** (`:83`). `instrument_type` ∈ {`FUT`,`CE`,`PE`}. **No `tick_size`, no `multiplier`, no `product`/`segment`-beyond-exchange, no margin fields.** |
| Physical DB | `data/instruments/nse_fo_instruments.duckdb` | **ABSENT** — the `data/instruments/` directory does not exist in this working copy. Every DB-backed path (resolve, expiry-from-DB, lot-size-from-DB) therefore silently falls back to hardcoded defaults. |

### 1.3 Options & futures execution surfaces

| Component | Location | Role | Hardcoded metadata |
|---|---|---|---|
| `OptionsContractSelector` | `core/execution/options/selector.py:37` | signal→Option contract (execution). | `INDEX_LOT_SIZES` {Nifty=**75**, BankNifty=**35**} (`:10`); `INDEX_STRIKE_STEPS` {50,100} (`:16`); `INDEX_EXPIRY_WEEKDAY` {Nifty=Tue, BankNifty=Wed, FINNIFTY=Tue, MIDCPNIFTY=Mon} (`:29`). Builds the symbol itself; **does not consult the master DB.** Sets `multiplier=1.0` (`:105`). |
| `OptionsProvider` | `core/data/options_provider.py` | option-chain fetch + expiry/strike helpers (dashboard/analytics). | `EXPIRY_WEEKDAY` {Nifty=Tue, BankNifty=Wed} (`:95`); `get_weekly_expiry` uses master DB **if present** else weekday calc (`:504-541`); `get_lot_size` master-or-`75` (`:594-613`). |
| Handler option path | `core/execution/handler.py:503-513` | routes `execution_mode=="option"` → selector, else `InstrumentParser.parse`. | Order built with `instrument=` (preserves the real type, `:536`). |
| Multi-leg grouping | `core/execution/groups/{order_group,group_tracker,group_pnl}.py` | `OrderGroup.group_id` (`order_group.py:34`), `GroupPnLTracker` (`group_pnl.py:14`). | Legs can be grouped — **the hook SPAN offsets need (§5).** Not yet consumed by margin. |
| IV / greeks | `core/risk/greeks/{black76_engine,greeks_calculator,portfolio_greeks}.py`, `core/analytics/options_analytics.py` | Black-76 pricing + greeks; portfolio-greeks aggregation (fixed in Phase 0). | The per-contract IV/vol source SPAN scenarios need (§5). |

### 1.4 Margin handling

`MarginTracker` (`core/execution/margin_tracker.py:10`) — the entire margin surface:
- `get_exposure(prices)` = Σ `pos.quantity × price × pos.instrument.multiplier` (`:31-35`).
- `get_used_margin(prices)` = `get_exposure × margin_rate` with `margin_rate=0.2` (`:11,39`).
- **No SPAN, no option-selling/short-premium margin, no inter-leg/inter-month offset, no per-underlying netting, no exposure margin.** `multiplier` is `1.0` for everything the parser builds (§3.3), so F&O exposure is understated.

### 1.5 Broker metadata & order/position plumbing

| Concern | Location | State |
|---|---|---|
| `BrokerAdapter` ABC **(A)** | `core/brokers/base.py:11` | `place_order(OrderEvent)`, `get_order_status`, **`get_positions`**, `cancel_order`. **`UpstoxAdapter` extends this.** |
| `BrokerAdapter` ABC **(B)** | `core/brokers/broker_base.py:6` | `place_order(NormalizedOrder)`, `cancel_order`, `subscribe_fills`. **No `get_positions`. The execution handler imports THIS** (`handler.py:47`). |
| `UpstoxAdapter.place_order` | `core/brokers/upstox_adapter.py:79-105` | Hardcodes `product:"I"` (intraday, `:82`), `validity:"DAY"`; `instrument_token = order.symbol` (`:86`) — **no `instrument_key` resolution**. |
| `UpstoxAdapter.get_positions` | `upstox_adapter.py:126-152` | Returns `Dict[str, Position]` keyed by `trading_symbol`; signed-qty→side with `abs(qty)` (Phase-0 fix). |
| Funds / holdings / margin | `core/brokers/*`, `core/api/*` | **None.** No `get_funds`/`get_holdings`/`get_margin` endpoint exists. Cash is the hardcoded `initial_capital=100000.0` seed (per `PORTFOLIO_STATE_DISCOVERY.md` §4.4). |
| `NormalizedOrder` | `core/execution/order_models.py:27` | Carries an `Instrument`; **but the legacy `symbol=/instrument_type=` path coerces *everything* to `Equity`** (`:66-70`). **No `product`/`segment`/`exchange` field.** `OrderType` enum has only `MARKET` (`:16`). |
| `Position` | `core/execution/position_models.py:21` | `instrument`, `side`, `quantity` (abs), `avg_price`. Identity is `instrument.symbol` (`:55`). |
| `ReconciliationEngine` | `core/execution/reconciliation.py:24` | `reconcile(List[Dict{symbol,quantity,side}])` → net-qty compare → `QUANTITY_MISMATCH` / `ORPHANED_BROKER_POSITION`. **Input format does not match `get_positions`'s `Dict[str,Position]` output (§3.7).** |
| Fee model | `handler.py:761-779` | **NSE-equity-intraday only** (Rs 20 + STT 0.025% + exch/SEBI/GST/stamp). No F&O premium/contract cost model. |

### 1.6 Expiry handling (scattered)

Expiry truth lives in **three** places, none authoritative, all index-only:
- `OptionsContractSelector.INDEX_EXPIRY_WEEKDAY` (`selector.py:29`) — execution path.
- `OptionsProvider.EXPIRY_WEEKDAY` + `get_weekly_expiry` (`options_provider.py:95,504`) — analytics path.
- `InstrumentMaster.resolve_active_future` (`instrument_db.py:59`) — DB path (futures), `find_options` (options).

No monthly-expiry concept for futures, no equity-F&O expiry, **no holiday/trading-calendar awareness** (weekday math ignores NSE holidays), and the `Option`/`Future` classes hold an `expiry` field but no expiry *logic*.

---

## 2. The instrument-identity problem (the spine)

Everything below hangs off one missing node. A contract today has three unreconciled names:

```
   display_symbol            broker instrument_key        broker tradingsymbol
   "NIFTY26FEB2522500CE"     "NSE_FO|54710"               (Upstox-formatted, may differ)
        │                          │                            │
   built by selector          authoritative PK in          returned by
   (selector.py:96) /         the master DB                 get_positions
   parsed by regex            (instrument_db.py)            (upstox_adapter.py:132)
   (instrument_parser.py)
        │                          │                            │
        └─── order.symbol ─────────┼──── place_order ships order.symbol AS
             (the display sym)     │     instrument_token (upstox_adapter.py:86)
                                   │     → invalid for F&O; no resolve() step
                                   │
        reconciliation matches on  └──── resolve_option() exists but is
        the symbol STRING                NOT wired into the order path
        (reconciliation.py:57)
```

Consequences:
- **Order placement** (live F&O) is broken: `instrument_token` must be the `instrument_key`, but the order carries the display symbol and nothing resolves it. `InstrumentMaster.resolve` / `resolve_option` exist (`instrument_db.py:39,163`) but are **not called** in `handler.py` or `upstox_adapter.py` (verified: no `resolve`/`instrument_key` reference in either).
- **Reconciliation** matches internal `Position.symbol` (display) against broker `trading_symbol` — and `resolve_option`'s docstring already admits a "tradingsymbol format mismatch" (`instrument_db.py:165`).
- **Margin/SPAN** keys positions by the same symbol and needs `lot_size`/strike/expiry that the display symbol only *encodes textually*, not structurally.

This is why §4 centers the canonical model on identity + resolution, and why §5/§6 both list it as their root dependency.

---

## 3. Gap analysis

| # | Gap | Evidence | Impact |
|---|---|---|---|
| 3.1 | **Futures unreachable via the signal path.** `InstrumentParser` never builds a `Future`. | `instrument_parser.py:14-46`; `future.py:6` | No futures trading through `process_signal`; `Future` is dead-ish. Blocks Planned #4 carry/futures. |
| 3.2 | **Three divergent hardcoded metadata sources** + authoritative DB unused by execution **and absent on disk**. | `selector.py:10,29`; `options_provider.py:95`; `instrument_parser.py:38`; `data/instruments/` missing | Lot size / expiry / strike-step can disagree; live = fallbacks. A SEBI lot-size change must be edited in ≥3 places. |
| 3.3 | **`multiplier` vs `lot_size` duality, unreconciled.** Exposure uses `multiplier` (=1.0); `lot_size` ignored in margin. | `margin_tracker.py:35`; `instrument_base.py:14`; `option.py:18` | F&O notional & margin **understated**; the single most load-bearing modelling bug for SPAN. |
| 3.4 | **No `instrument_key` resolution in the order path.** | `upstox_adapter.py:86`; no `resolve` in `handler.py` | Live F&O order placement cannot work. |
| 3.5 | **No `product`/`segment` on the order; product hardcoded intraday.** | `order_models.py:27`; `upstox_adapter.py:82` | No NRML/carry, no overnight option selling. = **Planned #4**. |
| 3.6 | **Two divergent `BrokerAdapter` ABCs; the driver's depends on the one without `get_positions`.** | `base.py:11` vs `broker_base.py:6`; `handler.py:47` | Reconciliation feed can't be typed against the driver's broker contract. = blocks **Planned #6**. |
| 3.7 | **`get_positions` output ≠ `reconcile` input format.** `Dict[str,Position]` vs `List[Dict{symbol,quantity,side}]`. | `upstox_adapter.py:150` vs `reconciliation.py:24-30` | A normalization shim is required before recon can run against the live broker. |
| 3.8 | **No funds/holdings/margin broker endpoints.** | grep over `core/brokers/*`,`core/api/*` → none | No real cash, no broker-side margin, no holdings reconciliation. |
| 3.9 | **Margin is flat-20%; no SPAN, no short-option margin, no offsets.** | `margin_tracker.py:11,39` | = **Planned #5**; blocks live option selling (`PROJECT_STATE.md` Blocked). |
| 3.10 | **Fee model equity-intraday only.** | `handler.py:761` | F&O P&L/cost (premium STT, futures STT, higher GST base) mis-modelled in backtest/paper. |
| 3.11 | **Expiry handling scattered, index-only, holiday-blind.** | `selector.py:29`; `options_provider.py:95` | No monthly/futures expiry, no equity-F&O expiry, no NSE holiday calendar. |
| 3.12 | **No `tick_size` anywhere.** | master schema `fetch_instrument_master.py:39`; no field | LIMIT-price rounding / order-validity checks impossible. |
| 3.13 | **`NormalizedOrder` legacy path coerces non-equity to `Equity`.** | `order_models.py:66-70` | Silent loss of Option/Future identity if any caller uses the `symbol=` constructor. |

---

## 4. Canonical instrument model proposal (design only — not implemented)

**Principle:** one immutable `Instrument` value object, **sourced from the instrument-master DB as the single source of truth**, addressed by a resolution seam. The three hardcoded tables (§1.3) and the parser's `lot_size=1` collapse into reads of this object.

### 4.1 Canonical fields

```
Instrument (canonical)
  instrument_key   broker identity / PK            ("NSE_FO|54710")   <- order routing key
  display_symbol   human / internal symbol         ("NIFTY26FEB2522500CE")
  tradingsymbol    broker display                  (recon match key)
  underlying       ("NIFTY", "RELIANCE")
  exchange/segment NSE_EQ | NSE_FO | NSE_INDEX | MCX_FO
  asset_class      EQUITY | INDEX | FUTURE | OPTION   (extends InstrumentType)
  product          MIS | NRML | CNC                 <- the §3.5 / Planned #4 field
  expiry           date | None
  strike           float | None
  option_type      CE | PE | None
  lot_size         int      (the real contract multiplier)
  tick_size        float    (new; §3.12)
  multiplier       == lot_size for F&O, 1 for cash  <- resolves the §3.3 duality
  freeze_qty       int | None (regulatory max per order)
```

### 4.2 Decisions to make explicit (not prose)

1. **Contract-size duality (§3.3).** Pick one: store `quantity` in **shares** (= lots × lot_size) and set `multiplier = 1`, **or** store `quantity` in **lots** and set `multiplier = lot_size`. Exposure/margin/greeks must all read the same convention. Recommended: quantity-in-lots + `multiplier = lot_size`, so `notional = qty_lots × lot_size × price` everywhere, and retire `Equity.multiplier=1.0`/`Option.lot_size` drift.
2. **Identity is `instrument_key`.** The order path routes on `instrument_key`; `display_symbol` is for humans/logs; recon matches on `tradingsymbol` (or `instrument_key` once positions carry it).
3. **Master DB is SSOT; the resolver is the only reader.** `OptionsContractSelector` keeps *selection policy* (which strike/expiry to pick) but obtains lot_size/tick_size/instrument_key by **resolving**, not from a local table.
4. **Expiry becomes a service over the master** (next weekly/monthly, holiday-aware), retiring the three weekday tables.

### 4.3 The resolution seam (the new node §2 needs)

```
InstrumentResolver (read-only, over the master DB)
  resolve(instrument_key)                         -> Instrument
  resolve_symbol(display_symbol | tradingsymbol)  -> Instrument
  resolve_option(underlying, expiry, strike, ot)  -> Instrument   (exists in spirit: instrument_db.py:163)
  resolve_future(underlying, as_of)               -> Instrument   (exists in spirit: instrument_db.py:59)
```
Constitution fit: pure infra (ADR-002), read-only/deterministic (ADR-003), no new ledger (ADR-001). It does **not** place orders or own positions.

---

## 5. Dependency graph — SPAN margin engine (Planned #5)

SPAN margin is defined by **offsets across legs and across an underlying** — an iron-fly's requirement is a fraction of its four legs summed. A per-instrument `qty×price×rate` model (today) misses the entire reason SPAN exists.

```
        +---------------------------------------------------------+
        |  [ROOT] Canonical Instrument + Resolver (§4)            |  <- MISSING
        |  underlying . expiry . strike . option_type . lot_size |
        +---------------+-----------------------------------------+
                        |
        +---------------v-----------+   +--------------------------+
        | Position book (in lots)    |   | Multi-leg grouping        | <- EXISTS, unused by margin
        | PositionTracker            |   | OrderGroup.group_id /     |   (group_pnl.py:14,
        +---------------+-----------+   | GroupPnLTracker           |    order_group.py:34)
                        |                +-------------+------------+
        +---------------v-----------+                 |
        | Market data: price +       |                 |
        | underlying price           | <- live-MTM seam|   (PORTFOLIO_STATE_DISCOVERY §4.2)
        +---------------+-----------+                 |
        +---------------v-----------+                 |
        | Per-contract IV / vol      | <- EXISTS       |
        | black76_engine /           |   (risk/greeks/*)|
        | options_analytics          |                 |
        +---------------+-----------+                 |
        +---------------v-----------------------------v------------+
        | SPAN parameter set (scan range, vol shift, inter-month & | <- ABSENT (external file,
        | inter-commodity spread credits, short-option minimum)    |   exchange-published)
        +---------------+------------------------------------------+
        +---------------v-----------+
        | Scenario / portfolio risk  | <- NEW engine (replaces flat 0.2,
        | engine -> SPAN array       |   margin_tracker.py:39)
        +---------------+-----------+
                        v
        PortfolioView.used_margin (consumer)  +  RiskManager pre-trade margin check
```

**SPAN blockers, in order:** (1) canonical instrument + resolver (root); (2) the `multiplier`/`lot_size` decision (§4.2.1) — without it every notional is wrong; (3) a SPAN **parameter source** (exchange file — not present anywhere); (4) wiring the existing IV/greeks feed; (5) teaching margin to net by `group_id` (today per-leg). Pieces already present: position book, group grouping, Black-76 IV, the `PortfolioView.used_margin` consumer slot.

---

## 6. Dependency graph — broker reconciliation (Planned #6)

```
        +---------------------------------------------------------+
        |  [ROOT] Canonical identity (§2/§4)                      |  <- MISSING
        |  instrument_key <-> tradingsymbol <-> display_symbol    |
        +---------------+-----------------------------------------+
                        |
        +---------------v-----------+
        | Unify the BrokerAdapter    | <- FIX: handler depends on broker_base (no
        | ABC; add get_positions to  |   get_positions, broker_base.py:6); Upstox
        | the driver's contract      |   implements base.py:11. Merge the two.
        +---------------+-----------+
        +---------------v-----------+
        | Position normalization     | <- FIX: get_positions returns Dict[str,Position]
        | Dict[str,Position] ->       |   (upstox_adapter.py:150); reconcile wants
        | List[{symbol,qty,side}]     |   List[Dict] (reconciliation.py:24)
        +---------------+-----------+
        +---------------v-----------+   +--------------------------+
        | ReconciliationEngine       |   | Broker funds endpoint     | <- ABSENT
        | (EXISTS, reconciliation.py)|   | get_funds -> cash recon / |   (no /funds, no
        +---------------+-----------+   | replace initial_capital   |    holdings)
                        |                +--------------------------+
                        v
        LoopDriver startup gate broker_positions() source (DRIVER_SPECIFICATION §11.3;
        PROJECT_STATE Planned #6: a raising broker_positions() must become
        startup-refusal -> journal -> STOPPED)
```

**Reconciliation blockers, in order:** (1) canonical identity so internal symbol == broker key (root); (2) collapse the two `BrokerAdapter` ABCs and put `get_positions` on the driver's contract; (3) a `Position`→recon-format normalizer (§3.7); (4) a funds endpoint for cash reconciliation and to retire the hardcoded `initial_capital`. The `ReconciliationEngine` and the startup-gate seam already exist and are correct — they are starved of a typed, identity-consistent feed.

---

## 7. Shared root & recommended sequence (proposal — nothing started)

Both Planned #5 (SPAN) and Planned #6 (reconciliation), and Planned #4 (product model), are **downstream of one node**: the canonical instrument + resolver over the master DB.

```
  Populate/verify master DB (data/instruments — currently absent)
        |
        v
  Canonical Instrument + InstrumentResolver (§4)  --+--------------+---------------+
        | (resolves multiplier/lot_size duality)    |              |               |
        v                                           v              v               v
  Order path: product field + instrument_key   SPAN margin    Broker recon    Expiry service
  resolution (Planned #4)                       (Planned #5)   (Planned #6)    (retire 3 tables)
```

This document recommends the canonical model + resolver as the **first** F&O work item; #4/#5/#6 consume it. None of this is implemented here.

---

## Appendix A — Source anchors (every claim is checkable)

| Claim | Anchor |
|---|---|
| InstrumentType / Instrument base (multiplier=1.0) | `core/instruments/instrument_base.py:6,12` |
| Option (lot_size + multiplier separate) | `core/instruments/option.py:12-18` |
| Future (no lot_size; never parsed) | `core/instruments/future.py:6`; `core/instruments/instrument_parser.py:14-46` |
| Parser builds Option(lot_size=1) or Equity only | `core/instruments/instrument_parser.py:33-46` |
| InstrumentMaster (resolve / resolve_option / lot_size) | `core/instruments/instrument_db.py:39,111,163` |
| Master schema (no tick_size/multiplier); NSE_FO+MCX_FO | `scripts/fetch_instrument_master.py:39-47,83` |
| Master DB physically absent | `data/instruments/` does not exist (filesystem check) |
| MarginTracker flat 20%; exposure via multiplier | `core/execution/margin_tracker.py:11,35,39` |
| Reconcile input format (List[Dict]) | `core/execution/reconciliation.py:24-30` |
| Two BrokerAdapter ABCs | `core/brokers/base.py:11` vs `core/brokers/broker_base.py:6` |
| Handler imports broker_base (no get_positions) | `core/execution/handler.py:47` |
| place_order product:"I"; instrument_token=order.symbol | `core/brokers/upstox_adapter.py:82,86` |
| get_positions returns Dict[str,Position] | `core/brokers/upstox_adapter.py:126-150` |
| No funds/holdings/margin endpoints | grep `core/brokers/*`,`core/api/*` -> none |
| No instrument_key resolution in order path | grep `handler.py`,`upstox_adapter.py` -> none |
| NormalizedOrder legacy coerces to Equity; no product field | `core/execution/order_models.py:27,66-70` |
| OptionsContractSelector hardcoded lot/expiry tables | `core/execution/options/selector.py:10,16,29` |
| OptionsProvider expiry/lot tables | `core/data/options_provider.py:95,504,594` |
| Multi-leg grouping (SPAN offset hook) | `core/execution/groups/order_group.py:34`; `group_pnl.py:14` |
| IV/greeks engine (SPAN scenario input) | `core/risk/greeks/black76_engine.py`; `core/analytics/options_analytics.py` |
| Fee model equity-intraday only | `core/execution/handler.py:761-779` |
