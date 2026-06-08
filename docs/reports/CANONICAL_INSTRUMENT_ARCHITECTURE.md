# CANONICAL_INSTRUMENT_ARCHITECTURE.md

**Type:** Architecture discovery & design — **no code written, no code modified, no commits.**
**Date:** 2026-06-08
**Phase:** 4A (Canonical Instrument Architecture) + 4B (Broker Mapping Discovery)
**Scope:** Design the platform-owned canonical instrument identity, the instrument resolver, and the broker mapping layer that all F&O *and equity/index* pillars depend on. Inventory current reality; recommend a foundation; sequence Phase 4C.
**Governing law:** `docs/PLATFORM_CONSTITUTION.md` v1.0 · `docs/ARCHITECTURE_DECISIONS.md` (ADR-001..006) · `docs/PROJECT_STATE.md` (Planned #4 product model, #5 SPAN, #6 reconciliation).
**Builds on:** `docs/reports/FNO_PRODUCT_DISCOVERY.md` (the identity problem) · `docs/reports/PORTFOLIO_STATE_DISCOVERY.md` (the ledger/PortfolioView consumer).
**Basis:** direct source read of `core/instruments/*`, `core/brokers/*`, `core/execution/{order_models,position_models,margin_tracker,reconciliation,order_factory,handler}.py`, `core/execution/options/selector.py`, `core/risk/greeks/greeks_calculator.py`, `scripts/fetch_instrument_master.py`; filesystem check of `data/instruments/`.

> This document designs and recommends. It implements nothing. Every current-state claim carries a `file:line` anchor so it is checkable, not asserted. Deliverable 10 (the implementation scope) is the **separate** file `docs/reports/PHASE_4C_IMPLEMENTATION_PLAN.md`.

---

## 0. Executive summary

The platform has **no canonical instrument identity**. A contract is named three incompatible ways — the constructed **display symbol** (`NIFTY26FEB2522500CE`), the broker **`instrument_key`** (`NSE_FO|54710`), and the broker **`tradingsymbol`** — with no resolution layer between them (`FNO_PRODUCT_DISCOVERY.md` §2). The order path ships the *display symbol* as the Upstox `instrument_token` (`upstox_adapter.py:86`) with no resolve step, so live F&O order placement cannot work. SPAN (Planned #5), the product model (Planned #4), and reconciliation (Planned #6) all sit downstream of this one missing node.

This report makes seven design commitments, each justified and constitution-anchored:

1. **The platform owns identity; the broker does not.** The canonical primary key is a **broker-independent structured key** (Option B, §D4) — e.g. `NSE:OPT:NIFTY:2026-02-25:22500:CE`, `NSE:EQ:INE002A01018` (anchored on **ISIN**, not ticker), `NSE:FUT:NIFTY:2026-02-26`, `NSE:IDX:NIFTY`. `instrument_key`/`tradingsymbol`/`exchange_token` become **broker-mapping attributes**, never identity. Rejected: synthetic minted IDs (Option A) — they introduce a new minting authority (a second source of truth), are non-deterministic, and carry migration risk, all of which fight ADR-003.

2. **One immutable `CanonicalInstrument` value object, discriminated by `asset_class`** {EQUITY, INDEX, FUTURE, OPTION} — *not* a deep subclass tree. This collapses the `multiplier` vs `lot_size` duality (`FNO_PRODUCT_DISCOVERY.md` §3.3) and the current 3-way metadata divergence into reads of one object.

3. **Equity and Index are first-class from day one** — not derivatives afterthoughts. The platform's two books are **equity swing (Bucket 1)** and **index option selling (Bucket 2)**; equities have the deeper historical coverage used by research/backtest. The current `InstrumentType` enum has **no `INDEX`** (`instrument_base.py:6`), and the instrument master ingests **only NSE_FO + MCX_FO** (`fetch_instrument_master.py:83`) — equities and indices are absent from the SSOT entirely. Both are §D1 gaps Phase 4C must close.

4. **The instrument-master DB is the single source of truth; the `InstrumentResolver` is the only reader.** Selection *policy* (which strike/expiry to pick) stays in `OptionsContractSelector`; lot_size/tick_size/broker identity come from **resolving**, not local hardcoded tables (`selector.py:10,16,29`).

5. **Resolution is point-in-time (`as_of`-aware), not "current snapshot."** Backtesting is a first-class consumer (§D8) and contract attributes change over time — this repo documents the post-2024 SEBI lot revision (NIFTY 50→75; `selector.py:9`), and `resolve_active_future(..., as_of=)` already takes a date (`instrument_db.py:59`). A current-only resolver gives wrong historical sizing/notional/P&L. The resolved `CanonicalInstrument` carries the `lot_size`/`tick_size` **effective at `as_of`**.

6. **Underlying-name normalization is part of identity.** The key embeds the underlying, but the repo spells it three ways — `NSE_INDEX|Nifty 50` (selector input), `"NIFTY"` (short name, `selector.py:22`), and the master `name` column. The key is only deterministic if normalization is deterministic (§D4.3).

7. **The broker mapping is a tested, bidirectional, per-broker translation layer** (`CanonicalInstrument ⇄ broker identity`, `broker position/order → CanonicalInstrument`), behind a `BrokerMapping` interface — so the platform stays portable across Upstox / Zerodha / Fyers / IB without redesigning internal models.

**Constitutional note (task discrepancy, surfaced not buried):** the task names **Bucket 1 = "Equity Swing Trading, 3–15 day holding"** (i.e. *cash* equity, CNC product), while Constitution §9 names **"Equity Futures."** These are different instruments with different identity (ISIN cash vs dated future), product, and margin. This design makes **`EQUITY` (cash, CNC, ISIN-anchored, no expiry) first-class** to serve Bucket 1, and notes equity-futures are *also* representable as `FUTURE` with an equity underlying — so both readings are served. The discrepancy should be reconciled in the Constitution or a future ADR; it is not resolved invisibly here.

---

## D1 — Current instrument inventory (architecture map)

Every concept touching instrument/contract/identity, with location, ownership, purpose, consumers, deficiencies, reuse.

### D1.1 In-memory class hierarchy (`core/instruments/`)

| Concept | Location | Owns / carries | Consumers | Deficiencies | Reuse |
|---|---|---|---|---|---|
| `InstrumentType` | `instrument_base.py:6` | enum EQUITY/FUTURE/OPTION | everything | **No INDEX**; no segment/product | Extend → `asset_class` (add INDEX) |
| `Instrument` (base) | `instrument_base.py:12` | `symbol`, `type`, `multiplier=1.0` | orders, positions, margin, greeks | `multiplier` defaults 1.0, **never set from master**; identity == `symbol` (display) | Becomes the field set of `CanonicalInstrument` |
| `Equity` | `equity.py:6` | hardcodes `multiplier=1.0` | parser, order factory | No ISIN, no tick_size, no segment | Folds into `asset_class=EQUITY` |
| `Option` | `option.py:12` | `underlying, expiry, strike, option_type, lot_size=1` | selector, greeks | Carries `lot_size` **and** `multiplier` separately (the duality) | Field source for OPTION rows |
| `Future` | `future.py:6` | `underlying, expiry` | greeks only | **No `lot_size`, no strike**; never built by the parser | Field source for FUTURE rows |
| `OptionType` | `option.py:7` | CALL=`CE`/PUT=`PE` | selector, parser | — | Keep as-is |
| `InstrumentParser` | `instrument_parser.py:8` | regex `symbol → Option \| Equity` | `handler.py:513,621,720`; `order_factory.py:34`; `position_models.py:47` | **Never builds `Future`**; parsed options get `lot_size=1, multiplier=1.0` (`:38-40`) — real size discarded; no master lookup | Re-target to delegate to the resolver |

### D1.2 Instrument master (authoritative data, DuckDB)

| Concept | Location | State | Deficiencies |
|---|---|---|---|
| `InstrumentMaster` | `instrument_db.py:24` | read-only lookup: `resolve(tradingsymbol)→instrument_key` (`:39`), `resolve_option(name,expiry,strike,type)` (`:163`), `resolve_active_future(name,prefix,as_of)` (`:59`), `find_options` (`:126`), `get_lot_size(key)` (`:111`) | The **only** component that knows real `instrument_key`/`lot_size` — but **no execution path calls it**. `resolve_option` already admits a "tradingsymbol format mismatch" (`:165`). |
| Master schema | `fetch_instrument_master.py:38-49` | `instruments(instrument_key PK, tradingsymbol, name, expiry TEXT, strike, instrument_type, lot_size, exchange)` | **No `isin`, no `tick_size`, no `multiplier`, no `product`/`segment`** beyond `exchange`. `instrument_type ∈ {FUT,CE,PE}`. |
| Ingest scope | `fetch_instrument_master.py:83` | filters `segment ∈ {NSE_FO, MCX_FO}` | **Equities (NSE_EQ) and indices (NSE_INDEX) are never ingested** → not in the SSOT at all. |
| Physical DB | `data/instruments/nse_fo_instruments.duckdb` | **ABSENT** — `data/instruments/` does not exist (filesystem check, 2026-06-08) | Every DB-backed path silently falls back to hardcoded defaults; live behavior == fallbacks. |

### D1.3 Execution & selection surfaces

| Concept | Location | Role | Hardcoded metadata (deficiency) |
|---|---|---|---|
| `OptionsContractSelector` | `selector.py:37` | signal → `Option` (the live execution path, `handler.py:505`) | `INDEX_LOT_SIZES` {Nifty 75, BankNifty 35} (`:10`); `INDEX_STRIKE_STEPS` (`:16`); `INDEX_EXPIRY_WEEKDAY` (`:29`); builds symbol itself; sets `multiplier=1.0` (`:106`); **no master lookup** |
| `OptionsProvider` | `core/data/options_provider.py` | option-chain + expiry/strike (dashboard/analytics) | second copy of expiry/lot tables (FNO §1.3) — divergent from selector |
| `OrderFactory` | `order_factory.py:34` | pure `SignalEvent → NormalizedOrder` | also `InstrumentParser.parse` — same `Future`-blind, master-blind path |
| Handler option path | `handler.py:503-513` | routes `execution_mode=="option"` → selector, else parser; order built `instrument=` (`:537`) | preserves type but never resolves identity |
| `greeks_calculator` | `greeks_calculator.py:27,38,52` | `isinstance(instrument, Equity/Future/Option)` branch | **the migration-risk surface** for the subclass→value-object change (§D9) |

### D1.4 Order / position / margin / recon plumbing

| Concept | Location | Identity / size handling | Deficiency |
|---|---|---|---|
| `NormalizedOrder` | `order_models.py:27` | carries an `Instrument`; `.symbol` = `instrument.symbol` (display) | legacy `symbol=/instrument_type=` path coerces **everything to `Equity`** (`:62-70`); **no product/segment/exchange**; `OrderType` only MARKET (`:16`) |
| `Position` | `position_models.py:21` | `instrument`, `side`, `quantity` (abs), `avg_price`; identity `instrument.symbol` (`:55`); legacy ctor re-parses via `InstrumentParser` (`:47`) | identity is the display string, not a canonical key |
| `MarginTracker` | `margin_tracker.py:10` | exposure = Σ `qty × price × instrument.multiplier` (`:35`); used = `× 0.2` (`:11,39`) | `multiplier`=1.0 for all parser output → **F&O notional understated**; `lot_size` ignored |
| `ReconciliationEngine` | `reconciliation.py:24` | `reconcile(List[{symbol,quantity,side}])` matches on `symbol` string (`:57`) | matches display symbol vs broker `trading_symbol`; format mismatch unresolved |
| `UpstoxAdapter.place_order` | `upstox_adapter.py:79` | `instrument_token = order.symbol` (`:86`); `product:"I"` hardcoded (`:82`) | ships display symbol as token; no resolve; no NRML/CNC |
| `UpstoxAdapter.get_positions` | `upstox_adapter.py:126` | `Dict[str,Position]` keyed by `trading_symbol` (`:143`) | output shape ≠ `reconcile` input (FNO §3.7) |
| Broker ABC **A** | `base.py:11` | `place_order(OrderEvent)`, `get_order_status`, **`get_positions`**, `cancel_order` | `UpstoxAdapter` extends this |
| Broker ABC **B** | `broker_base.py:6` | `place_order(NormalizedOrder)`, `cancel_order`, `subscribe_fills` — **no `get_positions`** | **the handler imports THIS** (`handler.py:47`); the two ABCs are unreconciled |

### D1.5 The architecture map (current)

```
            SignalEvent.symbol  ("NSE_INDEX|Nifty 50"  or  an equity symbol)
                     │
       ┌─────────────┴───────────────┐
       │ execution_mode=="option"?   │
       ▼ yes                         ▼ no
  OptionsContractSelector       InstrumentParser.parse
  (hardcoded lot/expiry/step)   (Option regex | Equity; never Future)
       │  builds display symbol      │  lot_size=1, multiplier=1.0
       └──────────────┬──────────────┘
                      ▼
              NormalizedOrder(instrument=…)   .symbol = DISPLAY symbol
                      │
            ┌─────────┼───────────────────────────────┐
            ▼         ▼                                 ▼
     PositionTracker  MarginTracker (×multiplier=1.0)   broker.place_order(order)
     (key = display)  (notional understated)            instrument_token = order.symbol  ← WRONG for F&O
                                                         (no resolve(); InstrumentMaster never called)

   InstrumentMaster (SSOT)  ──X──  not on the order path; DB file ABSENT; EQ/INDEX never ingested
```

Three identifiers, zero resolution, an absent SSOT, and equities/indices outside the master. That is the foundation Phase 4C replaces.

---

## D2 — Asset taxonomy (design only)

### D2.1 Decision: a flat discriminated value object, not a subclass tree

```
CanonicalInstrument                       (one immutable value object)
   asset_class: EQUITY | INDEX | FUTURE | OPTION    ← the discriminator
   …shared identity + economics fields (§D3)…
   …derivative fields (expiry/strike/option_type) present only when the class implies them…
```

Rejected alternative — the **subclass hierarchy** (`Equity`/`Future`/`Option : Instrument`, today's shape). Reasons:

1. **It re-creates the `multiplier`/`lot_size` duality.** Subclasses each decide their own size convention (`Equity.multiplier=1.0`, `Option.lot_size`), and downstream code must `isinstance`-branch to read size (`greeks_calculator.py:27-52`). A single object with one `lot_size`/`multiplier` convention removes the branch.
2. **Resolver/serialization simplicity.** A resolver that returns a single type serializes uniformly to telemetry/journal/DB and round-trips through broker mapping without per-type adapters.
3. **Optional fields are honest.** `expiry/strike/option_type` are `None` for EQUITY/INDEX — explicit and validated by `asset_class`, rather than encoded by which subclass was instantiated.

The discriminator **is** the taxonomy; behavior that genuinely differs by class (e.g. greeks) dispatches on `asset_class`, not Python type.

### D2.2 The minimal hierarchy and why each member is required

| `asset_class` | Required by | Tradable? | Identity anchor | Derivative fields |
|---|---|---|---|---|
| **EQUITY** | Bucket 1 (swing), research, backtest, portfolio | Yes (CNC/MIS) | **ISIN** | none |
| **INDEX** | Bucket 2 underlying, data, research, greeks underlying-price | **No** (reference only) | exchange + normalized name | none |
| **FUTURE** | Constitution §9 (equity-futures, carry), index futures | Yes (NRML/MIS) | underlying + expiry | expiry |
| **OPTION** | Bucket 2 (index option selling), greeks, SPAN | Yes (NRML/MIS) | underlying + expiry + strike + type | expiry, strike, option_type |

- **INDEX is not removable** even though you never place an order on it: it is the *underlying* for OPTION/FUTURE (the SPAN and greeks scenario input is the underlying price), the symbol research/backtest load (`NSE_INDEX|Nifty 50`, volume=0), and the thing `OptionsContractSelector` is handed as `signal.symbol`. Marking it `asset_class=INDEX, tradable=False` makes "you cannot send an order for an index" a **validated invariant**, not a latent bug.
- **EQUITY is not an afterthought** — it is Bucket 1 and the deepest historical dataset. Anchoring its identity on **ISIN** (which Upstox already embeds: `NSE_EQ|INE002A01018`) makes equity identity broker-independent for free.
- **No redundancy:** there is exactly one object; `asset_class` + nullable derivative fields express all four without a fifth concept. We deliberately do **not** add separate INDEX_OPTION vs STOCK_OPTION classes — that distinction is `underlying.asset_class`, derivable, not a new node.

### D2.3 Underlying as a typed reference

A derivative's `underlying` is itself a normalized identity (an EQUITY ISIN or an INDEX name), not a free string. This is what lets SPAN net by underlying and greeks fetch the right spot. The canonical key embeds the *normalized underlying token* (§D4.3), and the resolver can return the underlying's own `CanonicalInstrument` on request.

---

## D3 — Canonical instrument proposal (design only)

One immutable value object, **sourced from the master DB**, addressed by the resolver. Fields, why each belongs, and which future system consumes it:

| Field | Belongs because | Consumed by |
|---|---|---|
| `canonical_id` (str, structured key §D4) | the platform-owned primary identity, broker-independent | **everything** — PortfolioView keying, journal, telemetry, recon match, order routing lookup |
| `asset_class` (enum) | the discriminator defining which other fields are valid + tradability | greeks dispatch, SPAN grouping, risk (refuse INDEX orders), product defaulting |
| `underlying` (normalized token \| None) | net exposure/margin by underlying; fetch spot for greeks | **SPAN** (per-underlying netting), **Live Greeks**, exposure view |
| `exchange` (NSE/MCX/BSE) | disambiguate same name across venues; routing | Order Routing, broker mapping, fees |
| `segment` (NSE_EQ/NSE_FO/NSE_INDEX/MCX_FO) | the §3.5 missing concept; drives product/fees/margin model | **Product model (#4)**, **SPAN (#5)**, fee model |
| `product` (CNC/NRML/MIS) | replaces hardcoded `product:"I"` (`upstox_adapter.py:82`); enables carry & overnight selling | **Order Routing (#4)**, margin (carry vs intraday) |
| `expiry` (date \| None) | contract lifecycle; expiry netting; roll | SPAN inter-month, expiry service, recon, backtest as-of |
| `strike` (float \| None) | option identity; moneyness | SPAN scan, greeks, selector |
| `option_type` (CE/PE \| None) | option identity; payoff direction | SPAN, greeks, P&L |
| `lot_size` (int, **effective at `as_of`**) | the *real* contract multiplier; resolves the duality (§D3.1) | **SPAN/margin notional**, sizing, P&L, exposure |
| `tick_size` (float) | LIMIT-price rounding, order validity (§3.12 gap) | Order Routing (price rounding), validity checks |
| `multiplier` (float) | unified size convention (§D3.1): `= lot_size` for F&O, `1` for cash | margin/exposure/greeks — **one** size source |
| `isin` (str \| None) | broker-independent equity anchor; corporate-action tracking | EQUITY identity, holdings recon, research join |
| `freeze_qty` (int \| None) | regulatory max qty per order | Order Routing (slice large orders), risk |
| `broker_mappings` (lookup, **not** stored on the value object) | broker identity is a *mapping*, not identity — §D6 | Order Routing, reconciliation |

### D3.1 The size-convention decision (resolves the `multiplier`/`lot_size` duality)

**Decision: store `quantity` in *lots*, set `multiplier = lot_size`, so `notional = qty_lots × lot_size × price` everywhere.** For EQUITY/INDEX `lot_size = 1 ⇒ multiplier = 1` (cash is "1-share lots", arithmetic unchanged). This:
- retires the divergence where `Equity.multiplier=1.0` and `Option.lot_size` are separate, unreconciled fields (`equity.py:10`, `option.py:18`);
- fixes the understated F&O notional in `MarginTracker._calculate_single_exposure` (`margin_tracker.py:35`) — it keeps reading `instrument.multiplier`, which is now correct;
- gives SPAN/greeks/sizing **one** size source.

This is the single most load-bearing modelling decision for SPAN; it must be stated as an invariant in Phase 4C so every consumer reads the same convention.

### D3.2 What it explicitly is NOT
- ❌ not a broker object (no `instrument_key`/`tradingsymbol` *as identity* — those live in the mapping, §D6);
- ❌ not mutable (frozen value object; ADR-003 determinism);
- ❌ not a ledger/position (it is the *identity* a position references);
- ❌ not a current-only snapshot (lot_size/tick_size are the values **effective at `as_of`**, §D5/§D7).

---

## D4 — Identity rules

### D4.1 The question, answered

**Primary key = `canonical_id`, a deterministic broker-independent structured key (Option B).**

Format (one scheme, asset-class-shaped):

```
EQUITY :  NSE:EQ:<ISIN>                          e.g. NSE:EQ:INE002A01018      (RELIANCE)
INDEX  :  NSE:IDX:<NORM_NAME>                     e.g. NSE:IDX:NIFTY            NSE:IDX:BANKNIFTY
FUTURE :  <EXCH>:FUT:<NORM_UNDERLYING>:<EXPIRY>   e.g. NSE:FUT:NIFTY:2026-02-26
OPTION :  <EXCH>:OPT:<NORM_UNDERLYING>:<EXPIRY>:<STRIKE>:<CE|PE>
                                                 e.g. NSE:OPT:NIFTY:2026-02-25:22500:CE
```

`<EXPIRY>` is ISO `YYYY-MM-DD`; `<STRIKE>` is the exact strike; `<NORM_*>` is the normalized underlying token (§D4.3).

### D4.2 Comparison of the three options

| Criterion | A — synthetic minted ID | **B — broker-independent structured key (chosen)** | C — broker `instrument_key` as identity |
|---|---|---|---|
| Stability | Stable vs attribute change, but needs a registry to stay stable | Derivatives: the (underlying,expiry,strike,type) tuple is **immutable for the contract's life** ⇒ stable. Equity: anchored on **ISIN** (survives ticker renames) | Unstable — broker re-keys, differs per broker |
| Portability | Platform-internal, portable — but only via the registry | **Fully portable**; no broker concept in the key | **Zero** — Upstox-specific (`NSE_FO|54710`) |
| Migration risk | High — must mint + backfill IDs for all history; a new authority | Low — key is *derivable* from existing display-symbol fields; no backfill authority | N/A (rejected) |
| Broker independence | Yes (after registry) | **Yes, by construction** | No |
| Determinism (ADR-003) | **No** — minting is a side-effecting allocation | **Yes** — pure function of contract attributes | Yes but wrong owner |
| Testing simplicity | Needs a registry fixture | **Pure**: assert `key(attrs) == expected` | Needs broker fixtures for identity |

**Recommendation: Option B.** It is the only option that is simultaneously deterministic (ADR-003), broker-independent (the task's core principle: *platform owns identity*), and migration-cheap (the key is reconstructable from what the display symbol already encodes). Option A's minting registry would be a **second source of truth** — exactly what ADR-001 forbids. Option C hard-couples identity to Upstox, which the portability mandate rejects.

### D4.3 Underlying-name normalization (a required sub-rule)

The key is deterministic **only if** the underlying token is. The repo carries three spellings of the same underlying:

| Source | Spelling | Anchor |
|---|---|---|
| `SignalEvent.symbol` / selector input | `NSE_INDEX|Nifty 50`, `NSE_INDEX|Nifty Bank` | `selector.py` input |
| Selector short name | `NIFTY`, `BANKNIFTY` | `INDEX_SHORT_NAMES` (`selector.py:22`) |
| Master `name` column | broker `name` field (e.g. `NIFTY`) | `fetch_instrument_master.py:104` |

**Rule:** a single canonical `normalize_underlying()` mapping is the sole authority (`NSE_INDEX|Nifty 50 → NIFTY`, `NSE_INDEX|Nifty Bank → BANKNIFTY`, equity `→ ISIN`). It is pure, table-driven, and the **only** place the spelling decision lives — retiring the three scattered tables. Without it, two code paths can mint two different keys for one contract, defeating identity.

### D4.4 Identity vs display vs broker-match
- **Identity (routing/keying):** `canonical_id` (Option B).
- **Human/logs:** `display_symbol` (`NIFTY26FEB2522500CE`) — derived, never authoritative.
- **Broker recon match:** `tradingsymbol`/`instrument_key` **via the mapping** (§D6), never by string-equality on the display symbol (today's `reconciliation.py:57` bug).

---

## D5 — Broker reality inventory (document reality; do not redesign)

Classification of every identifier/field currently in the repo as a **Platform concept** (we own it) or a **Broker concept** (belongs in the mapping):

| Field / concept | Location | Today | Classification | Target home |
|---|---|---|---|---|
| `symbol` (display) | `instrument_base.py:14` | used **as identity** everywhere | **Platform (display only)** — misused as identity | `display_symbol`, derived |
| `instrument_key` (`NSE_FO\|54710`) | `instrument_db.py`, `upstox_adapter.py:86` | shipped as order token / PK in master | **Broker** | `BrokerMapping` |
| `tradingsymbol` | `instrument_db.py:39`; `upstox_adapter.py:143` | recon match, master lookup | **Broker** | `BrokerMapping` |
| `exchange_token` | (Upstox master field, not yet stored) | unused | **Broker** | `BrokerMapping` |
| `product` (`"I"`) | `upstox_adapter.py:82` | hardcoded intraday | **Platform** (intent) → **Broker** (code) | `product` field + mapping translates to broker code |
| `exchange` | `fetch_instrument_master.py:108` | stored as segment proxy | **Platform** | `exchange`/`segment` fields |
| `lot_size` | master + `option.py:18` + `selector.py:10` | 3 divergent sources | **Platform** (exchange truth, cached) | `CanonicalInstrument.lot_size` (as-of) |
| `strike`/`expiry`/`option_type` | `option.py` | on the Option | **Platform** | canonical fields |
| `isin` | *(embedded in EQ instrument_key only)* | not extracted | **Platform** | `isin` field |
| `tick_size` | *(absent everywhere)* | — | **Platform** | `tick_size` field |
| broker `order_id` | `upstox_adapter.py:97` | returned by place_order | **Broker** | order record, not identity |
| position identity | `position_models.py:55` | `instrument.symbol` (display) | **Platform** | `canonical_id` |
| `transaction_type` BUY/SELL | `upstox_adapter.py:88` | mapped from `order.side` | **Broker code** | mapping translates `OrderSide` |

**Reality summary:** the platform currently lets *broker concepts* (`instrument_key`, `tradingsymbol`) and a *display string* stand in for identity, while the genuinely platform-owned economic facts (`lot_size`, `tick_size`, `isin`) are either hardcoded, divergent, or absent. The mapping layer (§D6) exists to hold the broker column **out** of the canonical model.

---

## D6 — Broker mapping architecture (design only)

### D6.1 Responsibilities

```
                         BrokerMapping  (interface; one impl per broker)
   CanonicalInstrument  ───────────────────────────────────►  broker identity
   (canonical_id)        to_broker(ci, broker) -> BrokerRef    {instrument_key,
                                                                 tradingsymbol,
                                                                 exchange_token,
                                                                 product_code}
   broker position  ────────────────────────────────────────►  CanonicalInstrument
   {trading_symbol, qty…}  from_broker_position(raw) -> ci      (via resolver)

   broker order ack ────────────────────────────────────────►  CanonicalInstrument
   {order_id, instrument_token}  from_broker_order(raw) -> ci
```

`BrokerRef` is the per-broker bundle of broker concepts (§D5). The canonical model never imports it; the mapping is the only place a broker string appears next to a `canonical_id`.

### D6.2 How it works
- **Source of pairs:** the broker's own instrument master (Upstox `complete.json.gz`, already downloaded by `fetch_instrument_master.py`). The mapping is *built by resolving* each broker row into a `canonical_id` and storing `(canonical_id ⇄ BrokerRef)` — i.e. the mapping is a **projection of the master**, refreshed on the same daily cadence.
- **Outbound (order routing):** at `place_order`, `to_broker(ci, "upstox")` yields the `instrument_key` for `instrument_token` (fixing `upstox_adapter.py:86`) and the broker `product_code` from `ci.product` (fixing the hardcoded `"I"`).
- **Inbound (reconciliation):** `from_broker_position` maps each broker `trading_symbol` back to a `canonical_id`, so `ReconciliationEngine` compares **canonical_id ↔ canonical_id**, not display-vs-trading strings (fixing `reconciliation.py:57`).

### D6.3 How it stays broker-agnostic
- The platform depends only on the `BrokerMapping` **interface**; `UpstoxMapping`, `ZerodhaMapping`, … are swappable implementations. Adding a broker = one new impl + its master loader; **zero** change to `CanonicalInstrument`, resolver, execution, SPAN, recon.
- The canonical model has **no broker import** (an `ast` forbidden-import guard, mirroring ADR-002's strategy guard, can assert this).

### D6.4 How it is tested
1. **Round-trip property test:** `from_broker(to_broker(ci)) == ci` for a sampled cross-section (EQ/IDX/FUT/OPT) — the core correctness invariant.
2. **Golden fixtures per broker:** a frozen slice of the broker master with expected `canonical_id` for each row (`assert resolve(row).canonical_id == expected`). Detects broker re-keys.
3. **Coverage/orphan test:** every active contract the platform can emit has a mapping; every broker position resolves (no silent `None`).
4. **No-broker-in-core scan:** import guard over the canonical package.

---

## D7 — Instrument resolver architecture (design only)

### D7.1 Definition & API

`InstrumentResolver` — read-only, deterministic, over the master DB (SSOT). It is the **only** reader of the master and the only minter of `canonical_id`.

```
InstrumentResolver(master: InstrumentMaster, as_of: date | None)

  # canonical lookups (return CanonicalInstrument)
  resolve(canonical_id: str)                                  -> CanonicalInstrument
  resolve_equity(isin_or_symbol: str)                         -> CanonicalInstrument
  resolve_index(name: str)                                    -> CanonicalInstrument
  resolve_future(underlying: str, as_of: date|None=None)      -> CanonicalInstrument   # nearest active
  resolve_option(underlying, expiry, strike, option_type,
                 as_of: date|None=None)                       -> CanonicalInstrument

  # broker bridges (delegate to BrokerMapping, §D6)
  resolve_broker_key(instrument_key: str, broker: str)        -> CanonicalInstrument
  resolve_broker_position(raw: dict, broker: str)             -> CanonicalInstrument
```

The existing `InstrumentMaster.resolve_option`/`resolve_active_future` (`instrument_db.py:59,163`) are the *spiritual ancestors* — the resolver wraps the master and returns canonical objects instead of bare `instrument_key` strings.

### D7.2 What owns truth
- **Exchange-published instrument master = truth**, cached in DuckDB by `fetch_instrument_master.py`. The resolver never invents lot/tick/expiry; it reads them. (The hardcoded selector tables become a **last-resort fallback**, logged loudly, not the primary path.)
- For EQUITY/INDEX the master must be **extended** to ingest NSE_EQ + NSE_INDEX (today it skips them, `fetch_instrument_master.py:83`) — Phase 4C work.

### D7.3 Caching
- The master is **daily-static**, so the resolver loads the relevant slice once per process and serves from an in-memory dict keyed by `canonical_id`. Cache key is **`(canonical_id, as_of)`** so backtest as-of reads don't collide with live reads.
- Cache is read-only and rebuildable from the DB (no second source of truth; ADR-001).

### D7.4 Determinism & point-in-time (the `as_of` rule)
- The resolver is a **pure function of `(master snapshot, query, as_of)`** — same inputs ⇒ same `CanonicalInstrument` (ADR-003).
- **`as_of` is first-class.** Lot/tick values change (post-2024 SEBI 50→75; `selector.py:9`). The resolver returns the value **effective at `as_of`** (default = today for live; the bar date for backtest). This requires the master to be **effective-dated** for the attributes that drift (at minimum `lot_size`) — a schema item for Phase 4C. Live and backtest therefore traverse the identical resolution path with different `as_of`, satisfying ADR-003's "live == replay."

---

## D8 — Dependency graph

Which future pillars consume `CanonicalInstrument` and `InstrumentResolver`:

```
                ┌───────────────────────────────────────────────┐
                │  Instrument master DB (SSOT)                   │
                │  + EQ/INDEX ingest + isin/tick_size + as-of    │  ← Phase 4C extends
                └───────────────────────┬───────────────────────┘
                                        │
                ┌───────────────────────▼───────────────────────┐
                │  InstrumentResolver  (only reader, as_of-aware)│
                │  CanonicalInstrument (identity = canonical_id) │  ← Phase 4C core
                └───┬───────────┬──────────┬──────────┬─────────┘
                    │           │          │          │
        ┌───────────▼──┐  ┌─────▼─────┐ ┌──▼───────┐ ┌▼──────────────┐
        │ BrokerMapping │  │ Product / │ │ Order    │ │ Expiry service │
        │ (Upstox/…)    │  │ Segment   │ │ Routing  │ │ (retire 3      │
        │  (#6 recon)   │  │ model (#4)│ │ (#4)     │ │  weekday tbls) │
        └───────┬───────┘  └─────┬─────┘ └──┬───────┘ └────────────────┘
                │                │          │
        ┌───────▼───────┐  ┌─────▼──────────▼─────┐
        │ Broker recon   │  │ SPAN margin engine   │  ← #5: nets by underlying/expiry,
        │ (#6) canonical │  │ (#5)                 │     needs lot_size + greeks + grouping
        │ ↔ canonical    │  └─────┬────────────────┘
        └───────┬───────┘        │
                │          ┌──────▼───────┐  ┌──────────────┐  ┌──────────────────┐
                └─────────►│ PortfolioView │  │ Live Greeks  │  │ Research/Backtest │
                           │ evolution     │  │ (underlying  │  │ + Historical Data │
                           │ (key by       │  │  spot via    │  │ (as_of resolution)│
                           │  canonical_id)│  │  underlying) │  └──────────────────┘
                           └───────────────┘  └──────────────┘
```

| Pillar | Consumes canonical | Consumes resolver | Why |
|---|---|---|---|
| Product/Segment model (#4) | `segment`,`product`,`tick_size`,`freeze_qty` | resolve at order build | replaces hardcoded `"I"`; enables carry/overnight |
| SPAN margin (#5) | `underlying`,`expiry`,`strike`,`option_type`,`lot_size` | resolve legs | nets by underlying/expiry; `multiplier=lot_size` notional |
| Broker recon (#6) | `canonical_id`,`isin` | resolve_broker_position | canonical↔canonical match; holdings via ISIN |
| Funds & Margin APIs | `segment`,`product` | — | margin model keyed by product |
| PortfolioView evolution | `canonical_id` | — | one stable position key (today display string) |
| Live Greeks | `underlying`,`option_type`,`strike`,`expiry` | resolve underlying spot | fixes the marginal-only greek check |
| Research/Backtest | all + **`as_of`** | resolve_*(as_of) | correct historical lot/notional/P&L |
| Historical Data Services | `canonical_id`,`isin`,`segment` | — | join price history on a stable key incl. EQ/INDEX |
| Order Routing | `tick_size`,`freeze_qty`,broker ref | to_broker | price rounding, qty slicing, correct token |

Everything Planned (#4/#5/#6) plus PortfolioView, greeks, and the research/data services are **downstream of this one node** — confirming the FNO report's "build the canonical seam first."

---

## D9 — Migration strategy

**Pattern: strangler-fig, seam-by-seam, behavior-preserving — no big-bang.** The platform keeps running (Runtime, PortfolioView, Telemetry, Execution untouched in behavior) while identity is introduced behind existing seams.

### D9.1 Known migration-risk surface (evidenced)
- **`isinstance` on subclasses → 3 call sites, all in `core/risk/greeks/greeks_calculator.py:27,38,52`.** This is the *only* place the subclass→value-object change breaks; it converts to an `asset_class` dispatch. Bounded and known (grep, 2026-06-08).
- **Legacy `symbol=` constructors** in `NormalizedOrder` (`order_models.py:62-70`) and `Position` (`position_models.py:47`) that coerce to `Equity`/re-parse — these become resolver calls.
- **`InstrumentParser.parse` call sites:** `handler.py:513,621,720`, `order_factory.py:34`, `position_models.py:47` — re-targeted to the resolver (parser becomes a thin fallback).

### D9.2 Sequence (each step independently shippable, suite stays green)
1. **Extend the SSOT first** (no consumers yet): add NSE_EQ + NSE_INDEX ingest, `isin`/`tick_size` columns, and effective-dated `lot_size` to `fetch_instrument_master.py` + schema. Materialize `data/instruments/…duckdb` (today absent). Pure additive; nothing reads it yet.
2. **Introduce `CanonicalInstrument` + `normalize_underlying` + `canonical_id` minting** as new pure modules. No wiring. Unit-tested in isolation (`key(attrs)==expected`).
3. **Introduce `InstrumentResolver`** over the master, returning canonical objects, `as_of`-aware. No wiring. Tested against the materialized DB + fallback.
4. **Introduce `BrokerMapping` (Upstox)** as a master projection. Round-trip + golden tests. No wiring.
5. **Adapt at the build seam (behavior-preserving):** `OptionsContractSelector` keeps its *policy* but obtains `lot_size`/`tick_size`/identity by resolving; `InstrumentParser` delegates to the resolver with a logged fallback. `CanonicalInstrument` carries the old `.symbol` (= `display_symbol`) and `.multiplier`/`.type` so `NormalizedOrder`/`Position`/`MarginTracker`/greeks read unchanged — **identical numbers, now correct lot_size**. (`MarginTracker` notional *changes* only because `multiplier` is finally right — a fix, gated behind a test that asserts the new value.)
6. **Adapt the greeks dispatch** (the 3 isinstance sites) to `asset_class`.
7. **Wire the order seam:** `place_order` uses `to_broker(ci).instrument_key` for `instrument_token` and `ci.product` for the product code. This is the first **behavior change for live F&O** (previously broken) — gated, paper-tested.
8. **Wire recon:** `from_broker_position` so `ReconciliationEngine` matches canonical↔canonical.

PortfolioView/Telemetry/Driver are untouched in steps 1–6 (they read `.symbol`, still present); only steps 7–8 change live order/recon behavior, which is *currently broken*, so there is no working behavior to regress. Each step is RED→GREEN TDD with the full suite green before the next.

### D9.3 What does not change
- ADR-001 (no new store — the resolver reads the existing master; the mapping is a projection), ADR-002 (no Platform→Strategy; canonical core has no broker/strategy import), ADR-003 (deterministic, `as_of`), ADR-006 (no new runtime path — the resolver is pure infra, never an orchestrator).

---

## Appendix A — Source anchors (every current-state claim is checkable)

| Claim | Anchor |
|---|---|
| InstrumentType has no INDEX; base multiplier=1.0 | `core/instruments/instrument_base.py:6,16` |
| Equity hardcodes multiplier=1.0 | `core/instruments/equity.py:10` |
| Option carries lot_size + multiplier separately | `core/instruments/option.py:18,33,38` |
| Future has no lot_size/strike; never parsed | `core/instruments/future.py:6`; `core/instruments/instrument_parser.py:21-46` |
| Parser builds Option(lot_size=1,multiplier=1.0) or Equity only | `core/instruments/instrument_parser.py:33-46` |
| InstrumentMaster resolve/resolve_option/resolve_active_future(as_of)/get_lot_size | `core/instruments/instrument_db.py:39,163,59,111` |
| Master schema: no isin/tick_size/multiplier/product | `scripts/fetch_instrument_master.py:38-49` |
| Ingest skips EQ/INDEX (NSE_FO+MCX_FO only) | `scripts/fetch_instrument_master.py:83` |
| Master DB physically absent | `data/instruments/` does not exist (filesystem check 2026-06-08) |
| Selector hardcoded lot/step/expiry tables; multiplier=1.0 | `core/execution/options/selector.py:10,16,29,106` |
| Selector short-name table (name spelling) | `core/execution/options/selector.py:22` |
| Handler option vs parser routing; order built instrument= | `core/execution/handler.py:503-513,536` |
| OrderFactory uses InstrumentParser | `core/execution/order_factory.py:34` |
| NormalizedOrder legacy coerces to Equity; no product; MARKET only | `core/execution/order_models.py:16,62-70` |
| Position identity = instrument.symbol; legacy re-parses | `core/execution/position_models.py:47,55` |
| MarginTracker exposure via multiplier; flat 0.2 | `core/execution/margin_tracker.py:11,35,39` |
| Reconcile matches on symbol string | `core/execution/reconciliation.py:24,57` |
| Two BrokerAdapter ABCs (A has get_positions, B does not) | `core/brokers/base.py:11,27` vs `core/brokers/broker_base.py:6` |
| Handler imports broker_base (no get_positions) | `core/execution/handler.py:47` |
| place_order: instrument_token=order.symbol; product:"I" | `core/brokers/upstox_adapter.py:82,86` |
| get_positions returns Dict[str,Position] keyed by trading_symbol | `core/brokers/upstox_adapter.py:126-150` |
| isinstance(subclass) migration surface (3 sites) | `core/risk/greeks/greeks_calculator.py:27,38,52` |
| Underlying spelled `NSE_INDEX\|Nifty 50` / `NIFTY` | `core/execution/options/selector.py:22,29` |
</content>
</invoke>
