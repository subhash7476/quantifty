# MM.7B — Production SignalSource Review

**Type:** Review — map the real strategy → `SignalEvent` seam. **No production code, no entry script, no SignalSource implementation, no adapter implementation.**
**Date:** 2026-06-11
**Question:** *Where do live trading decisions originate, what object should implement `SignalSource`, what does it need, how does it connect to the runtime, and can paper/live be identical?*
**Basis (file:line, verified 2026-06-11):** `core/runtime/signal_source.py` · `core/events.py` · `core/execution/handler.py:432` (`process_signal`) · `core/execution/order_factory.py:27` · `core/database/legacy_adapter.py:75` · `core/analytics/options_analytics.py` · `MM7_LIVE_WIRING_REVIEW.md` (W1) · `MM7A_CHARACTERIZATION_REPORT.md` (T1) · `G1_CLOSEOUT_REPORT.md` · `PROJECT_STATE.md`.

---

## 0. Verdict

**No production strategy exists in this repository.** `SignalEvent(...)` is constructed **only in tests and docs** — there is no `core/strategies/`, no `*nifty_shield*` module, and no signal-generating object anywhere in `core/`/`scripts/`/`flask_app/`. The salvage migration deliberately excluded all strategies (`PROJECT_STATE.md` Completed §1). The signal-origination layer is therefore **greenfield**, not "wired wrong."

This is exactly why MM7B precedes implementation: the `LoopDriver` needs a `SignalSource`, the seam exists and is tested, but **nothing on either side of it produces a real `SignalEvent`.** Implementing the entry script next would force a stub source or invented wiring — the same review-first violation G1 avoided. The seam's shape is fully known; what it must *carry* and *connect to* is mapped below.

---

## 1. Which production strategy currently generates trading decisions?

**None.** Evidence:

- `SignalEvent(` appears in 12 files — **all tests, `_doubles.py`, or docs** (`grep`, 2026-06-11). Zero `core/` production producers.
- `core/strategies/**` → **no files**. `*nifty_shield*` → **no files**. `docs/**/*NIFTYSHIELD*` → **no files**. The strategy tier CLAUDE.md describes (PixityAI, NiftyShield, FTMO) belongs to the pre-salvage platform (`D:\BOT\root`) and was **not migrated**.
- The G1 closeout already recorded the consequence: "no live `LoopDriver` is constructed outside tests" and "`process_signal`'s only runtime caller is `LoopDriver._dispatch_signals`" — so even the execution path has no upstream producer driving it.
- **Analytics are not a signal source (ADR-002).** `OptionsAnalytics` (`core/analytics/options_analytics.py`) produces structural **facts** (PCR, GEX, Max Pain, ATM) — "Analytics Produce Facts; runtime is read-only" (CLAUDE.md). It must **not** emit `SignalEvent`s; it is an input a strategy *consumes*, not the strategy.

**Conclusion:** the first production `SignalSource` will be the **first strategy ported into this repo**, not an adapter over something already here. The documented intent (CLAUDE.md / the unmigrated `D:\BOT\root` design) is the **NiftyShield weekly options seller** — a regime-adaptive premium-selling strategy entering at 13:00 and managing structured exits. It is the natural first candidate, but it **does not exist here yet** and porting it is MM7D, not this review.

---

## 2. The `SignalEvent` contract a source must emit (the live `process_signal` path)

A `SignalSource` returns `List[SignalEvent]`; the driver routes each to `ExecutionHandler.process_signal(signal, current_price=bar.close)` (the **sole** live order path — `OrderFactory.create_order` is the G1 #5 *dead* carve-out; the handler builds orders internally per the Phase-9A note at `handler.py:29`). So the contract a source must satisfy is **what `process_signal` reads**, not what `OrderFactory` reads:

`SignalEvent` fields (`core/events.py:72-80`): `strategy_id`, `symbol`, `timestamp`, `signal_type` (BUY/SELL/EXIT/NEUTRAL), `confidence`, `metadata: Dict`, optional `context: TradeStructuralContext`.

What `process_signal` requires (`handler.py:432-520`):

| Field | Requirement | Notes |
|---|---|---|
| `symbol` | broker-facing instrument key/symbol | The handler resolves it **canonically** (futures→`resolve_future`, option→selector/`canonicalize_symbol`) — G1 closed this. An F&O source emits the contract symbol; identity is the handler's. |
| `signal_type` | BUY / SELL / EXIT | EXIT bypasses risk enforcement (`handler.py:461`). |
| `metadata['sl_distance']`, `metadata['risk_r']` | **mandatory for non-EXIT** | TLP V1 risk enforcement (`handler.py:457-482`); absent → defaults-with-warning only for the mock broker, else risk-clearance path. A real source **must** populate both. |
| `metadata['signal_id']` | optional | Handler derives a deterministic `sha256(symbol_strategy_timestamp)` if absent (`handler.py:444-449`) — so idempotency works without the source supplying one, but a source MAY set it. |
| sizing (`quantity`) | **NOT required from the source** | The handler sizes via `_calculate_position_size` = `default_quantity·(0.5+confidence·0.5)` (`handler.py:819-824`); `OrderFactory`'s `metadata['quantity']` read is on the dead path. **Sizing is execution's (ADR-005)** — a source must not size. |
| `context` | optional `TradeStructuralContext` | Audit snapshot; not required for routing. |

**Finding C1 (EXIT is resolved handler-side).** `process_signal`/the handler close the EXIT against the handler's **own** position tracker — the source emits `EXIT` for a symbol and the handler resolves quantity/side from its ledger (the dead `OrderFactory.create_order:39-46` shows the same intent). **So a source never needs the position quantity to exit** — it only needs to decide *when* to exit. This materially relaxes the seam's no-ledger constraint (see §4).

---

## 3. What object should implement `SignalSource`, and what data does it need injected?

**Object:** a new **strategy-owned** class implementing `SignalSource.on_bar(bar) -> List[SignalEvent]` (`signal_source.py:91`), living in a `core/strategies/` (or `strategies/`) module that depends on the platform, never the reverse (ADR-002). The driver never branches on its type (§5.3).

**What the seam injects (the hard boundary, `signal_source.py:73-89` / §5.4):**
- **`bar`** — the only per-call input. The driver advances the clock to `bar.timestamp` *before* `on_bar`, and pairs each returned signal with `current_price=bar.close` when routing (ADR-003).
- **optional read-only `context` at `on_start`** — which **MUST NOT** be or expose the ledger, broker, or `ExecutionHandler`.

**What the source must obtain itself (constructed by the entry script and passed to the *source's own constructor*, not through the driver seam):**
- **Option-chain data** — the OHLCV `bar` the driver supplies is **not** an option chain. A weekly-options strategy needs strikes/IV/greeks, so it must hold its **own** `OptionsProvider` (`core/data/options_provider.py`) / `OptionsAnalytics` handle, injected at construction. This is the single biggest data dependency and is **orthogonal to the driver's `MarketDataProvider`**.
- **Its strategy config** (e.g., the NiftyShield JSON: structures, VIX bands, wing offsets, exit thresholds).
- **A clock reference (optional)** for "as-of" chain reads — but decision *time* must come from `bar.timestamp`, never wall-clock, to keep replay==live (ADR-003).

**What it MUST NOT hold (§5.4 / ADR-001 / ADR-005 / ADR-006):** the ledger/trackers, the broker, the `ExecutionHandler`, or a driver handle. It places no orders and reads no position truth.

---

## 4. How it connects to provider / clock / portfolio state / execution handler

| Collaborator | Connection | Constraint |
|---|---|---|
| **MarketDataProvider** | **Indirect.** The driver pulls bars from the provider and hands them to `on_bar`. The source never touches the bar provider directly. | For option-chain data it uses its **own** `OptionsProvider` (a different data source), injected at construction. |
| **Clock** | **Indirect.** Reads `bar.timestamp`; decisions are data-clock-driven. A clock ref may be injected for chain "as-of" reads but must not drive decision *time*. | Wall-clock forbidden in the decision path (ADR-003). |
| **Portfolio state** | **NOT injected** (§5.4 forbids a ledger handle). | **Finding C2 — shadow state.** Stateful exits (NiftyShield profit-target 50%, stop-loss 2×, delta-adjustment >0.55) need to know the open structure's entry premium / current P&L. Since the seam forbids reading the ledger, the source must track its **own emitted intent** ("I opened a short straddle at premium P at 13:00") and compute exit *timing* from that shadow state + the current bar/chain. Time-only exits (15:15) need no state. The handler still resolves the EXIT mechanics against its ledger (C1). **This shadow-state-vs-ledger boundary is the central design decision MM7D must make — and MM7C must pin.** |
| **ExecutionHandler** | **Never** (ADR-006). | The source returns signals; only the driver calls `process_signal`. The `SignalSource` seam holds no handler handle (statically guarded, G1). |

**Reconciling stateful options-selling with the dumb-source rule:** the strategy stays "dumb" about the *ledger* but may be *stateful* about its *own intent*. Entry decisions read bar+chain; exit decisions read bar+chain+shadow-state; the handler owns sizing, fills, and EXIT resolution. No architecture principle is bent — the source never sees broker truth.

---

## 5. Can paper and live be identical?

**Yes for the source itself — with one data-layer caveat.**

- The `SignalSource` is **mode-agnostic**: it sees bars + chain data and emits signals deterministically from `bar.timestamp`. Paper vs live differs only in the handler's `ExecutionMode` (PAPER simulated fills vs LIVE broker orders) — **downstream** of the source. The `DriverConfig.Mode` (LIVE/REPLAY) only changes the clock/watchdog, also outside the source.
- **Caveat (C3 — option-chain data parity).** Live, the source's `OptionsProvider` fetches the chain from Upstox V3; in replay/backtest it must read **recorded** chains with the **same shape**, keyed by `bar.timestamp`. If the chain source is not made replay-symmetric, paper/live diverge at the *data* layer even though the *decision* logic is identical. This is the one thing that can break the paper==live guarantee, and it is a data-provider concern (Planned #7 unified market-data), not a source-logic concern.

So: **decision logic is paper/live identical by construction; the obligation is to make the option-chain feed replay-symmetric.** MM7C must include a determinism characterization that pins this.

---

## 6. Characterization tests required before implementation (MM7C)

Pin the seam's *consumer contract* and the *boundaries* before any strategy code, so MM7D builds against a green net (the G1 / MM7A discipline). All are characterization — no strategy logic:

1. **`SignalEvent` → `process_signal` consumer contract.** Pin what the handler requires of an emitted signal: non-EXIT **must** carry `sl_distance` + `risk_r` (else risk-clearance/defaults path); `signal_id` auto-derives when absent; sizing is handler-side (source must not set quantity). Guards MM7D against emitting invalid signals.
2. **EXIT-resolved-by-handler (C1).** Pin that an `EXIT` `SignalEvent` for a symbol is resolved against the handler's own position (quantity/side handler-derived) — so the source need not know position size to exit. Pin that EXIT bypasses risk enforcement.
3. **Seam boundary (§5.4 / C2).** Pin that the `SignalSource` seam exposes **no** ledger/broker/handler handle — i.e., a source *cannot* read positions through the contract, forcing the shadow-state design. (Mechanical: the `on_start` context and `on_bar` signature carry no such object.)
4. **Determinism / paper==live (C3).** Pin that identical (bar, chain) inputs at identical `bar.timestamp` yield identical signals, and that the source reads no wall-clock — the replay==live guarantee at the source level. Flag the option-chain replay-symmetry obligation.
5. **List-order routing.** Pin (reusing the existing ABC tests) that a multi-leg structure's signals are returned in routing order and the driver does not re-rank — relevant for option structures emitting multiple legs in one bar.
6. **`on_start`/`on_bar`/`on_stop` lifecycle** against the driver — once-per-bar, after clock advance, empty-list no-op — using a *characterization* source double (not the real strategy).

These tests do **not** implement a strategy; they pin the contract a strategy must meet and the boundaries it must respect.

---

## 7. Recommendation: MM7C next, and why this order

**Recommended next prompt: MM.7C — SignalSource Characterization** (the §6 net), review/test-only. Then MM7D implements the first strategy as a `SignalSource` against that green net.

**Why characterize before implementing (and before the entry script):**

```
MM7B SignalSource Review            ← (this) origin mapped: greenfield, contract known
   ↓
MM7C SignalSource Characterization  ← pin the consumer contract + §5.4 boundary + determinism
   ↓
MM7D SignalSource Implementation    ← port the first strategy (NiftyShield candidate) to the seam
   ↓
MM7E Entry Script Wiring            ← compose LoopDriver with a REAL source (MM7A T1 acceptance flips)
   ↓
MM7F Broker Positions Adapter       ← MM7A T2 contract
   ↓
MM7G W3 Refusal Contract            ← flip MM7A T3 defect-pin to refusal
   ↓
F4 Verification → F3 Disposition → Product/Margin → 4C.7
```

This order is forced by the MM7B finding: the entry script (MM7E) **cannot** be built honestly before a real source exists, because its acceptance test (MM7A T1) requires `source present` and its canonicalization test (T4) requires a real run. Building MM7E first would mean a stub source or invented wiring — the two bad outcomes the review-first discipline exists to prevent. Characterizing the seam's consumer contract (MM7C) first means MM7D's strategy is built against pinned behavior, and MM7E then wires *known-good* parts — exactly how G1 sequenced characterize → migrate → close.

**No production code, entry script, SignalSource, or adapter was created by this review.**

---

*Filed under the G1 / MM7A review-first, characterize-before-change discipline. Companion to `MM7_LIVE_WIRING_REVIEW.md` and `MM7A_CHARACTERIZATION_REPORT.md`.*
