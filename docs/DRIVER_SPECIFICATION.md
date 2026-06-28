# DRIVER_SPECIFICATION.md

**Status:** SPECIFICATION v1.0 — implementation-ready, not yet implemented.
**Owner:** Principal Systems Architect.
**Governing law:** `docs/PLATFORM_CONSTITUTION.md` v1.0 (Principles 1–5), `docs/ARCHITECTURE_DECISIONS.md` (ADR-001..006 — esp. ADR-006: the LoopDriver is the sole runtime orchestrator).
**Source material:** `docs/reports/RUNNER_DEPENDENCY_ANALYSIS.md`, `docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md`, `docs/reports/CAPABILITY_REVIEW.md`.
**Scope:** the **Deterministic Loop Driver** — the highest-priority missing platform pillar (`docs/PROJECT_STATE.md` → Planned #1).

> This document specifies a contract. It contains **no code** — only exact module references, signatures of existing collaborators, the file map the implementation will create/modify, and the behavioural rules an implementer must satisfy. Every reference below was verified against the live `F:\Nifty` tree.

---

## 0. Reading Map (what to hold in context)

| Concept | Existing module | Status |
|---|---|---|
| Deterministic clock | `core/clock.py` — `Clock` / `RealTimeClock` / `ReplayClock` | Present; **gap** (§6.4) |
| Event vocabulary | `core/events.py` — `SignalEvent`, `SignalType`, `OHLCVBar` | Present |
| Fill event | `core/execution/order_lifecycle.py` — `FillEvent` | Present (note: not in `events.py`) |
| Market data contract | `core/database/providers/base.py` — `MarketDataProvider` | Present |
| Execution spine | `core/execution/handler.py` — `ExecutionHandler` | Present |
| Liveness + staleness | `core/execution/watchdog.py` — `RuntimeWatchdog` | Present, **inert** |
| Telemetry transport | `core/messaging/telemetry.py` — `TelemetryPublisher` | Present (transport only) |
| Telemetry → UI | `flask_app/telemetry_bridge.py` — `TelemetryBridge` | Present |
| Market session gate | `core/database/utils/market_hours.py` — `MarketHours` | Present |
| Critical alerting | `core/alerts/alerter.py` — `alerter` | Present |

**The driver to be built does not exist anywhere in `F:\Nifty`.** The watchdog and telemetry *transport* exist; the loop that drives them, the telemetry gather-and-publish step, and the generic signal seam do not (`RUNNER_EXTRACTION_BLUEPRINT.md` "Duplication baseline").

---

## 1. Purpose

### 1.1 Why the driver exists

Every platform capability in `F:\Nifty` is presently **inert at runtime**. `ExecutionHandler` can turn a signal into a tracked broker order, `RuntimeWatchdog` can detect a frozen feed and trip the kill switch, `TelemetryPublisher` can push metrics to the dashboard — but **nothing calls them in a loop**. There is no orchestrator. This is the single reason Principle 3 (Deterministic Operation) and Principle 5 (No Trading On Stale Data) are *operationally unmet* despite the components existing (ADR-003, ADR-004; `PLATFORM_INVENTORY.md` §2.1–2.2).

The **Deterministic Loop Driver** is the single-threaded orchestrator that closes this gap. It pulls market data, advances the clock, asks a strategy-agnostic signal source what to do, routes the resulting signals through `ExecutionHandler`, and on every tick drives the watchdog and telemetry. It is the **integration seam** that makes the inert components into a running, observable, deterministic trading process.

### 1.2 Responsibilities (what the driver owns)

1. **Own the single execution path.** One loop, one thread, one ordering of events (ADR-003 — "single execution path", "deterministic event processing").
2. **Own time advancement.** Advance the `Clock` from bar timestamps so the live and replay decision paths traverse identical code (ADR-003; §6).
3. **Pull bars** from a `MarketDataProvider` and hand each to the signal source.
4. **Pull signals** from a strategy-agnostic `SignalSource` (§5) and **route** each to `ExecutionHandler.process_signal(...)` (§8).
5. **Drive the watchdog** every tick: `record_bar()` on bar arrival, `check_data_staleness()` and `write_heartbeat()` on cadence (§9) — **live mode only** (§6.5).
6. **Gather and publish telemetry** every tick from the execution/ledger snapshot (§10) — the gather step does **not** exist yet and is the driver's to own.
7. **Enforce a startup-validation gate**: refuse to enter the loop unless state recovery + reconciliation succeed (§11; ADR-001).
8. **Expose lifecycle control**: start, pause, resume, stop, with a clean, observable shutdown (§3).

### 1.3 Non-responsibilities (what the driver must NOT do)

The driver is **NOT a strategy engine, NOT a signal generator, NOT a backtesting framework.** Specifically it must never contain:

- **Signal generation / alpha logic of any kind.** It only *transports* `SignalEvent`s produced behind the `SignalSource` seam (ADR-002; Constitution §4–§5).
- **Exit-condition monitoring (TP / SL / time-stop).** This is strategy/execution *policy*, not orchestration. The old `core/runner.py` interleaved `_check_exit_conditions` into the loop body; the driver must **not** inherit it (`RUNNER_EXTRACTION_BLUEPRINT.md` §1 "Hidden risks"; `RUNNER_DEPENDENCY_ANALYSIS.md` §4). Strategies emit `SignalType.EXIT` through the **same** signal seam; the driver never decides when to exit.
- **Sizing, risk, margin, or fill bookkeeping.** These live exclusively in `ExecutionHandler` and its trackers (ADR-005; Constitution Principle 2). The driver routes; it does not compute.
- **Position/PnL truth.** The ledger (`PositionTracker` / `PnLTracker` / persistence) is the sole authority (ADR-001). The driver is a read-only consumer when it builds telemetry.
- **Any `Platform → Strategy` import.** The driver imports `SignalSource` (an abstract platform interface), never a concrete strategy (ADR-002).

> **One-line litmus test for any proposed driver feature:** if removing it would change *which* trades happen (rather than *whether the loop runs and is observable*), it belongs to a strategy or to `ExecutionHandler`, not the driver.

---

## 2. Design Principles (binding)

| # | Principle (Constitution / ADR) | How the driver satisfies it |
|---|---|---|
| 1 | **Ledger Is Truth** (Principle 1, ADR-001) | The driver never writes positions/PnL. It reads `ExecutionHandler.position_tracker` / `pnl_tracker` / `metrics` for telemetry only. Reconciliation must pass before trading (§11). |
| 2 | **Execution Before Alpha** (Principle 2, ADR-005) | The driver hands signals to `ExecutionHandler` and accepts its verdict (order or `None`). It adds no logic ahead of execution; risk/idempotency/kill-switch all live in the handler. |
| 3 | **Deterministic Processing** (Principle 3, ADR-003) | Single thread, single loop, single ordering. Time is **data-driven** via `Clock` (§6). A **pull** signal model (§5.2) — never push — preserves deterministic ordering. No hidden side effects. |
| 4 | **No Trading On Stale Data** (Principle 5, ADR-004) | The driver drives `RuntimeWatchdog` each tick; staleness trips `ExecutionHandler.activate_kill_switch` (§9). Watchdog is wall-clock and **gated to live mode** (§6.5). |
| 5 | **Platform / Strategy Separation** (§5, ADR-002) | The only strategy-facing surface is the abstract `SignalSource` (§5). The driver knows nothing of futures vs options vs discretionary vs replay. |

---

## 3. Runtime Lifecycle

### 3.1 States

| State | Meaning | Trading? | Watchdog/telemetry? |
|---|---|---|---|
| **STARTUP** | Constructing collaborators, recovering state, reconciling, validating (§11). | No | No |
| **RUNNING** | Normal loop: pull bar → advance clock → pull signals → route → drive watchdog/telemetry. | Yes | Yes |
| **PAUSED** | Loop continues to pull bars, advance clock, drive watchdog & telemetry, but **signal routing is suspended** (no new `process_signal` calls). Used for operator intervention without going blind. | No (gated) | Yes |
| **STOPPING** | Stop requested; finishing the current tick, flushing telemetry, closing publishers. | No | Final flush |
| **STOPPED** | Loop exited cleanly; resources released. Terminal. | No | No |
| **RECOVERY** | A sub-phase of STARTUP (and re-entered after a restart) where the ledger is restored and reconciled (§11). | No | No |

> **PAUSED is deliberate:** pausing must not blind the operator. The watchdog and heartbeat keep running so a paused-but-alive process is distinguishable from a dead one (Constitution §6, "Silent failure is unacceptable").

### 3.2 State transition diagram

```
                        construct()
                             │
                             ▼
                       ┌───────────┐   recovery/reconciliation FAIL
                       │  STARTUP  │──────────────────────────────► STOPPED
                       │ (RECOVERY │                                (refuse to trade
                       │  inside)  │                                 — ADR-001 §11.4)
                       └─────┬─────┘
                  validation │ PASS
                             ▼
            resume()   ┌───────────┐   pause()
        ┌──────────────│  RUNNING  │──────────────┐
        │              └─────┬─────┘               ▼
        │                    │ stop()        ┌───────────┐
        │                    │               │  PAUSED   │
        │                    │               └─────┬─────┘
        │                    │                     │ stop()
        │                    ▼                     │
        │              ┌───────────┐               │
        └─────────────►│ STOPPING  │◄──────────────┘
       (PAUSED→RUNNING)└─────┬─────┘
                             │ loop drained, telemetry flushed,
                             │ publishers closed
                             ▼
                       ┌───────────┐
                       │  STOPPED  │  (terminal)
                       └───────────┘
```

**Transition rules:**

- `STARTUP → RUNNING` is permitted **only** if §11 startup validation passes. Otherwise `STARTUP → STOPPED` with a critical alert.
- `RUNNING → STOPPING` is triggered by `stop()`, by data exhaustion in replay (`is_data_available` false for all symbols), or by the `max_bars` guard (§13).
- A **kill switch trip** (`ExecutionHandler._kill_switched == True`) does **not** stop the loop. The loop keeps running (so heartbeat/telemetry continue and the operator can see *why* it stopped trading), but `process_signal` becomes a no-op internally (`handler.py:447`). The driver treats kill-switched-and-running as a first-class, observable state — not a crash.
- `STOPPING → STOPPED` must be reachable even if telemetry flush fails (telemetry is fire-and-forget; §12.4).

---

## 4. Event Flow

### 4.1 Per-tick pipeline (the canonical ordering)

```
   ┌─────────────────────────────────────────────────────────────────────────┐
   │                      ONE DETERMINISTIC TICK (single thread)               │
   └─────────────────────────────────────────────────────────────────────────┘

  (1) MARKET DATA            (2) CLOCK                 (3) SIGNAL SOURCE
  MarketDataProvider         Clock.set_time(           SignalSource.on_bar(bar)
  .get_next_bar(sym) ──bar──►  bar.timestamp)  ──────►  → List[SignalEvent]
        │                     (replay: real advance;          │
        │                      live: no-op, now()=wall)        │
        │                                                       │ for each signal
        ▼                                                       ▼
  watchdog.record_bar()                              (4) EXECUTION
  (live only)                                         ExecutionHandler
        │                                             .process_signal(
        │                                                signal, bar.close)
        │                                                  │
        │                                                  ▼
        │                                            (5) LEDGER  (authority)
        │                                            broker → FillEvent →
        │                                            position_tracker /
        │                                            pnl_tracker / margin /
        │                                            reconciliation / persistence
        │                                                  │  (read-only snapshot)
        ▼                                                  ▼
  (7) WATCHDOG  ◄────────────────────────────────  (6) TELEMETRY
  check_data_staleness()                            publish_metrics / positions /
  write_heartbeat(bars)                             health  (built from §5 snapshot)
  (live only)                                       (throttled, fire-and-forget)
```

**Ordering is fixed and load-bearing** (ADR-003 "single ordering"):
1. **Market Data** — pull the next bar (`get_next_bar`). No bar → §7.3 / §7.4 handling.
2. **Clock** — advance from `bar.timestamp` *before* any signal is evaluated, so `handler.clock.now()` is bar-time in replay (§6).
3. **Signal Source** — synchronous pull `on_bar(bar) → List[SignalEvent]` (§5).
4. **Execution** — route each signal in list order to `process_signal(signal, bar.close)` (§8).
5. **Ledger** — the handler (and its broker fill callback) updates trackers/persistence. The driver does **not** touch the ledger here.
6. **Telemetry** — build the snapshot from the post-tick ledger state and publish (throttled).
7. **Watchdog** — staleness check + heartbeat write (cadence-gated, live only).

### 4.2 Authority flow (Principle 1, ADR-001)

```
Exchange → Broker → ExecutionHandler → Ledger(trackers+persistence) → Risk → Dashboard
                          ▲                       │
                          │ process_signal        │ read-only
   SignalSource ──────────┘                       └────────► Driver telemetry gather
   (Strategy→Platform)                                       (never writes back)
```

The driver sits on the **left** (it feeds signals in) and on the **far right** (it reads ledger state out for telemetry). It never short-circuits the authority chain.

---

## 5. Signal Source Interface

This is the **heart of the specification** — the seam that keeps the platform strategy-agnostic (ADR-002). Get it right and every other section follows.

### 5.1 Home and ownership

- **New package:** `core/runtime/` (created by this work).
- **New module:** `core/runtime/signal_source.py` — defines the abstract `SignalSource`.
- **Rationale:** the interface is **platform-owned** (the allowed dependency is `Strategy → Platform`; a concrete strategy *implements* this platform ABC). It lives beside the driver, not in any strategy. `core/execution/watchdog.py` is the precedent for "extracted infra that the driver drives"; `core/runtime/` is the natural home for the driver + its seam. (Alternative considered: place it in `core/execution/`. Rejected — the seam is orchestration, not order management; keeping it in `core/runtime/` avoids overloading the execution package.)

### 5.2 Contract: synchronous **pull**, never push

```
SignalSource (abstract):
    on_bar(bar: OHLCVBar) -> List[SignalEvent]
        # Called once per bar, synchronously, on the driver thread.
        # Returns zero or more SignalEvents to route, in priority order.
        # MUST be side-effect-free with respect to platform state.

    on_start(context) -> None      # optional lifecycle hook (warmup, subscribe)
    on_stop() -> None              # optional lifecycle hook (flush, close)
```

**Why pull, not push** (ADR-003): a push model (the source calls into the driver/handler on its own thread when it "feels like" emitting) destroys deterministic ordering and the single-thread guarantee. The driver **asks** the source on each bar, on the driver's thread, in a fixed order. This is the property that makes live == replay.

- The seam emits the **existing** `core/events.py:SignalEvent` (no new event type). The driver pairs each with `current_price = bar.close` and calls `ExecutionHandler.process_signal(signal, bar.close)`.
- The list order **is** the routing order. The source expresses priority by ordering; the driver does not re-rank.
- An empty list is the normal "do nothing this bar" case.
- The source receives only the bar (and an optional read-only context at `on_start`). It must obtain any other inputs itself; the driver will not inject analytics (the old `AnalyticsProvider` coupling is explicitly excluded — `RUNNER_DEPENDENCY_ANALYSIS.md` §2).

### 5.3 The four required client shapes (all satisfied by one seam)

| Client | How it implements `SignalSource` | Notes |
|---|---|---|
| **Futures strategy** | `on_bar` returns directional `BUY`/`SELL`/`EXIT` `SignalEvent`s for equity-futures symbols. | Multi-position book (3–10) is handled by the handler's per-symbol trackers, not the seam. |
| **Option strategy** | `on_bar` returns option `SignalEvent`s (the strike/expiry selection happens inside the source or via `core/execution/options/selector.py`). | Greeks limits enforced in `handler._check_greek_limits` (`handler.py:967` — MM9.3-S1B: portfolio + marginal aggregation across delta, vega, gamma; bool-returning D4 rejection gate), not the driver. |
| **Discretionary trader** | A `SignalSource` backed by a **thread-safe queue** the human/UI writes to; `on_bar` **drains the queue synchronously** and returns whatever was enqueued since the last bar. | This is how an inherently *asynchronous* actor fits a *synchronous pull* model without breaking the single path. The async write is absorbed at the queue; the read is deterministic on the driver thread. |
| **Replay engine** | A `SignalSource` that replays previously recorded `SignalEvent`s keyed by timestamp, returning those due at `bar.timestamp`. | Enables deterministic reproduction of a past session through the identical loop. Not a backtester — it injects recorded signals; it does not generate them. |

> The driver's code is **identical** for all four. It never branches on client type. That is the test of whether the seam is correct.

### 5.4 What the seam must NOT expose

- No callback the source can use to place orders directly (would bypass `process_signal`).
- No handle to the ledger, broker, or trackers (would violate ADR-001 / ADR-005).
- No driver-thread reentrancy (the source must not call back into the driver during `on_bar`).

---

## 6. Clock Behavior

### 6.1 Time is data-driven (ADR-003)

The deterministic guarantee is the **`Clock`**. The driver advances it from each bar's timestamp *before* evaluating signals, so every downstream timestamp (`handler.clock.now()`, order timestamps, persistence) is bar-time in replay and identical-code in live.

### 6.2 Replay mode

- Clock instance: `core/clock.py:ReplayClock(start_time)`.
- Each tick: `clock.set_time(bar.timestamp)` (`ReplayClock.set_time`, `clock.py:52`).
- Result: `clock.now()` returns the bar's timestamp; the decision path is fully reproducible.

### 6.3 Live mode

- Clock instance: `core/clock.py:RealTimeClock(timezone='Asia/Kolkata')`.
- `clock.now()` returns wall-clock IST (`clock.py:32`). Bars arrive in near-real-time; the bar timestamp is recorded by the watchdog (§9) but does **not** drive the live trade clock (live *is* wall-clock by definition).

### 6.4 ⚠️ Clock-interface gap (REQUIRED prerequisite)

`set_time(...)` exists **only on `ReplayClock`**. The base `Clock` (`clock.py:10`) and `RealTimeClock` (`clock.py:24`) have **no `set_time`**. The blueprint's "`Clock.set_time(bar.timestamp)`" is therefore **not uniform** across modes (`RUNNER_EXTRACTION_BLUEPRINT.md` §1 assumed it was).

**Resolution (a minor, in-scope platform addition — specify it, don't discover it):** add a **no-op `set_time(dt)` to the base `Clock`** so the driver can call `clock.set_time(bar.timestamp)` uniformly every tick. `ReplayClock` overrides it (real advance); `RealTimeClock` inherits the no-op (wall-clock is authoritative live). This keeps the driver branch-free on clock type while preserving correct semantics per mode. The alternative (driver branches `if mode == REPLAY`) is acceptable but couples the driver to clock concretions — prefer the no-op base method.

### 6.5 Timestamp ownership and the wall-clock split

Two clocks coexist and must not be confused (`RUNNER_DEPENDENCY_ANALYSIS.md` §6.5):

| Concern | Time source | Mode |
|---|---|---|
| **Trade decision path** | data-driven `Clock` (`set_time`/`now`) | both (deterministic) |
| **Watchdog staleness / heartbeat** | wall-clock `datetime.now()` / `time.time()` *inside `RuntimeWatchdog`* | **live only** |

The watchdog uses wall-clock internally (`watchdog.py:57,70,86`). In replay this is **meaningless and will false-trip** (a replay processes years of bars in seconds; "5 minutes without a bar" by wall-clock is nonsensical against bar-time). **The driver must drive the watchdog only in live mode** (§9.5). Replay runs the deterministic trade path *without* staleness/heartbeat.

---

## 7. Market Data Integration

### 7.1 Provider responsibilities (existing contract)

The driver consumes `core/database/providers/base.py:MarketDataProvider`:

- `get_next_bar(symbol) -> Optional[OHLCVBar]` — advances through history (replay) or returns the latest unseen bar (live).
- `is_data_available(symbol) -> bool` — more history exists (replay) / feed active (live).
- `get_latest_bar`, `reset`, `get_progress` — available but not required by the loop scaffold.

The driver holds **one** `MarketDataProvider` constructed over `config.symbols`. It does **not** implement a provider; it consumes the canonical one (live: the DuckDB-backed live provider fed by `core/database/ingestors/websocket_ingestor.py`; replay: the historical provider).

### 7.2 Bar arrival handling

Per tick, for each symbol in `config.symbols` (fixed order):
1. `bar = provider.get_next_bar(symbol)`.
2. If `bar is not None`: `clock.set_time(bar.timestamp)` (§6) → `watchdog.record_bar()` (live, §9) → `signals = source.on_bar(bar)` → route each (§8) → increment `bars_processed`.
3. Telemetry + staleness + heartbeat run on cadence after the symbol sweep (§4.1 steps 6–7).

### 7.3 Missing data (a `None` bar)

`get_next_bar` returning `None` has **mode-dependent meaning**:

- **Replay:** combined with `is_data_available(symbol) == False` → that symbol is exhausted. When *all* symbols are exhausted → `RUNNING → STOPPING` (clean end of replay).
- **Live:** `None` means "no new bar yet" — normal between bars. The driver does **not** treat this as an error. It moves on; the polling cadence (`config.poll_interval_s`, default 0.5s — matching the old `time.sleep(0.5)`, `RUNNER_EXTRACTION_BLUEPRINT.md` §1) governs how often it re-checks.

### 7.4 Stale data handling

A *prolonged* absence of live bars (feed frozen) is **not** the same as a momentary `None`. Detection and response belong to the watchdog (§9), not the bar-pull logic: `record_bar()` stamps each arrival; `check_data_staleness()` compares wall-clock elapsed against `RuntimeWatchdog.DATA_STALE_THRESHOLD` (5 minutes, `watchdog.py:33`) during market hours and trips the kill switch. The bar-pull path stays simple; the watchdog owns "the feed died."

---

## 8. Execution Integration

Reuses `core/execution/handler.py:ExecutionHandler` **unchanged**. The driver is a thin caller.

> **Price-feed coupling (MM9.2-S3-S2):** `LoopDriver._tick()` calls `execution.update_market_price(symbol, bar.close)` after advancing the deterministic clock (`set_time`) and before dispatching signals (`on_bar`). This is a data-feed operation, not a signal-dispatch or execution-policy operation. The driver remains unaware of execution logic; it passes market prices as raw data, in the same way it passes `bar.close` to `process_signal`. This coupling is minimal: one method, one scalar argument, no return value, no side effects on the driver. It does not violate the driver's neutrality principle, which prohibits the driver from making execution decisions — not from feeding data. The call is guarded on handler presence (the no-handler replay/inert/test path has nothing to warm); the second call inside `process_signal` overwrites the snapshot with an equal value (idempotent). This is the only driver→handler call besides `process_signal` (§8.1).

### 8.1 Signal routing

For each `SignalEvent` from `source.on_bar(bar)`, in list order:

- Call `handler.process_signal(signal, current_price=bar.close)` (`handler.py:372`). Signature: `process_signal(signal: SignalEvent, current_price: float) -> Optional[NormalizedOrder]`.
- `current_price` is **always `bar.close`** — deterministic, no separate price feed, no driver-side pricing.
- The handler performs (driver does none of this): Phase-0 authority + idempotency, mandatory SL/risk-R enforcement, kill-switch check, daily-trade-limit, drawdown check, position-stacking guard, greek limits, **capital-utilisation margin gate (MM9.1; ENTRY only — see §8.5)**, order creation, broker submit. The driver **accepts the verdict**: a `NormalizedOrder` (submitted) or `None` (skipped/blocked).
- **`EXECUTION_CALLS` metric semantic (changed in MM8.1C):**
  - *Before MM8:* "process_signal returned without raising."
  - *After MM8:* "execution path produced a non-None execution result."
  - The driver meters `RuntimeMetric.EXECUTION_CALLS` only when `process_signal` returns **non-`None`**. A `None` return — kill-switch exit, stacking guard, drawdown block, risk refusal, or broker failure — is **not** metered. The metric now counts actual broker execution attempts only.

### 8.2 Order submission path

Owned entirely by the handler (`process_signal` → `order_factory` → `broker.place_order`). The driver never constructs or submits orders.

### 8.3 Fill handling

**The driver does not handle fills.** `ExecutionHandler` subscribes to broker fills at construction via `self.broker.subscribe_fills(self._handle_broker_fill)` (`handler.py:132`); `_handle_broker_fill` (`handler.py:267`) ingests each `FillEvent` into `order_tracker` / `position_tracker` / `pnl_tracker`, updates realized equity via `_update_equity_metrics` (MM9.2-S4), and persists the trade.

> **Concurrency note (must be acknowledged, not glossed):** in **live** mode fills arrive on the **broker's WebSocket thread**, i.e. *off* the driver thread. This is the one place the single-thread model meets reality. The trackers are mutated by that callback; the driver only *reads* them (for telemetry) on its own thread. In **replay/paper** the broker delivers fills synchronously within `process_signal`, preserving strict determinism. The spec's position: the driver remains single-threaded for the *decision* path; fill ingestion is the handler's pre-existing async seam and is out of the driver's scope. Implementers must not add a second mutation path to the ledger from the driver.

### 8.4 Error handling

- `process_signal` may raise on hard rule violations (e.g. `enforce_risk_clearance` → raises; `enforce_execution_authority`). The driver wraps each `process_signal` call so that **one signal's failure does not kill the loop**: log at error, publish a telemetry log line (§10), continue to the next signal/bar. The loop's survival is itself an observability requirement (a dead loop is the worst outcome — §12).
- A raised exception is **never** swallowed silently (Constitution §6). It is logged via `core/logging:setup_logger("loop_driver")` and surfaced to telemetry.
- A kill-switched handler is **not** an error: `process_signal` simply returns `None` (`handler.py:447`). The driver keeps looping (§3.2).

### 8.5 Margin Gate (MM9.1 — extended by MM9.2-S1/S2)

The execution handler applies a pre-trade capital-utilisation check before registering any ENTRY order. This satisfies Constitution Principle 4 ("no trade without margin validation") at the capital-deployment layer.

- **Method:** `ExecutionHandler._check_margin_budget(order, current_price) -> tuple[bool, float]` — returns `(approved, utilisation)`.
- **Formula:** `utilisation = (used_current + incremental_est) / cash_balance`; `approved = utilisation <= config.max_capital_utilisation` (default `0.80`; boundary inclusive — equal-to-limit is approved). `used_current = margin_tracker.get_used_margin(prices)` where `prices = {sym: snap.price for sym, snap in self._price_cache.items()}` (MM9.2-S1: full price cache, not single-symbol; MM9.2-S3-S1: the cache is `Dict[str, PriceSnapshot]`, projected to `Dict[str, float]` immediately before the call so MarginTracker's signature — the MM9.4 SPAN seam — is unchanged); `incremental_est = _estimate_required_margin(qty * effective_multiplier, price) * margin_rate`, where `effective_multiplier` is `canonical_instrument.multiplier` (lot_size for F&O) or `instrument.multiplier` (1.0 for equity) as fallback.
- **Multiplier fix (MM9.2-S2):** `MarginTracker._calculate_single_exposure` now prefers `pos.instrument.lot_size` over `pos.instrument.multiplier` — restored Option positions compute `qty × price × lot_size` instead of `×1.0`. Zero-priced legs (`price=0.0`) remain in the iteration (guard is `is not None`, not truthy).
- **Placement:** fires AFTER order normalisation and `RiskManager.evaluate` (PHASE 2), BEFORE `order_tracker.add_order()` (PHASE 5). A rejected order is therefore never registered in the tracker — eliminating orphan orders on session recovery (the C2 correction). Rejection increments `metrics.rejected_trades`, logs a `MARGIN_BUDGET_REJECTED symbol=… utilisation=…% limit=…%` WARNING (no C3 disclosure — portfolio blindness resolved by MM9.2-S1), and returns `None`.
- **EXIT bypass (D8):** EXIT signals skip the gate unconditionally — closing a position reduces margin; gating an EXIT would block position-closing trades (the opposite of safety).
- **Denominator (`cash_balance`):** a construction-time scalar set from `ExecutionHandler(initial_capital=...)`, propagated through `build_runner(initial_capital=...)` (MM9.1-S4). Updates on every fill via `_update_equity_metrics(trade)` — BUY reduces `cash_balance` by `(qty × price + fees)`, SELL increases it by `(qty × price − fees)` (MM9.2-S4, I.H.1 resolved). Resets to the configured value on restart.
- **Outcome (D4):** rejection, NOT kill switch — the session continues; the next bar may clear headroom. Orthogonal to the drawdown gate (which trips the kill switch).
- **Cold-start residual (spec §8 R2):** At session restart, `_price_cache` is empty. Positions recovered via `_replay_state` are unpriced by the gate until their first signal warms the cache. Bounded to the first tick cycle per symbol. A one-shot WARNING is emitted at startup when recovered positions exist but the cache is cold (MM9.2-S1 D-S1-4).

### 8.6 Fresh-Book Gate (MM9.2-S3-S3)

The execution handler applies a **fresh-book preflight** before the capital gate (§8.5). This satisfies Constitution Principle 5 ("No Trading On Stale Data") at the **per-symbol price level** — distinct from the aggregate, live-only, wall-clock `RuntimeWatchdog` (§9), which cannot see a single symbol's feed dying inside an otherwise healthy universe.

- **Method:** `ExecutionHandler._check_book_priceable() -> PriceabilityResult` — a **pure** value object `(priceable: bool, stale_symbols: set[str], missing_symbols: set[str])` (frozen dataclass). The helper inspects only `position_tracker` and `_price_cache`; it performs **no** logging/metrics/journal/kill-switch/MarginTracker call/state mutation. All side effects live in the `process_signal` call-site.
- **Threshold:** `ExecutionConfig.max_price_age_s: float = float('inf')` (default **disabled**). A held position's snapshot is FRESH iff its age `<= max_price_age_s` (strictly greater-than → STALE; `age == threshold` is FRESH). MISSING = no `_price_cache` entry. A non-FLAT position that is STALE or MISSING makes the book UNPRICEABLE.
- **Disabled contract:** when `max_price_age_s == inf`, the helper returns `priceable=True` immediately without iterating — the gate is a no-op (existing behaviour preserved at default).
- **Placement:** runs inside `if signal.signal_type != SignalType.EXIT:`, **immediately before** `_check_margin_budget`. If the book is unpriceable, the capital gate is **never reached** — utilisation is never computed on a partial book (the C3 under-count class). EXIT bypasses the gate (closing a position reduces margin; gating an EXIT is unsafe).
- **On block:** `metrics.rejected_trades += 1`; a `PORTFOLIO_UNPRICEABLE symbol=… missing=… stale=… ages_s=…` WARNING is logged; one `EventType.PORTFOLIO_UNPRICEABLE` (Severity.WARNING) journal event is written — guarded `if self._journal:` and exception-wrapped so a journal failure can never change the trade path. Returns `None` (rejection, **not** kill switch).
- **Determinism:** age is `self.clock.now() - snap.timestamp` (ADR-003). The gate is all-mode (PAPER/LIVE/replay) and replay-identical — never `datetime.now()`.
- **Caveat (R1) — do NOT arm `600.0` yet:** a recovered position whose symbol is absent from `config.symbols` (e.g. an expired F&O instrument) never receives a bar, is permanently MISSING, and would block every entry indefinitely. Arming the gate requires a future startup validation that detects non-universe held positions (candidate MM9.2-S3-S4 / MM9.3). `float('inf')` is self-protecting at the default.

---

## 9. RuntimeWatchdog Integration

Reuses `core/execution/watchdog.py:RuntimeWatchdog` **unchanged**. The watchdog is *passive by design* — it has no thread; the driver drives it (`watchdog.py` module docstring).

### 9.1 Construction

`RuntimeWatchdog(execution=handler, heartbeat_path=config.heartbeat_path)` (default path `logs/heartbeat.json`, `watchdog.py:38`). The watchdog holds a reference to the same `ExecutionHandler` the driver routes through.

### 9.2 Bar recording

On every non-`None` bar arrival (§7.2), the driver calls `watchdog.record_bar()` (`watchdog.py:51`). This stamps `_last_bar_timestamp = datetime.now()` (wall-clock) and logs a "DATA RECOVERED" transition if the feed had previously gone stale.

### 9.3 Stale-feed detection

Once per tick (after the symbol sweep), the driver calls `watchdog.check_data_staleness()` (`watchdog.py:63`):
- No-op until the first bar (warmup) and outside market hours (`MarketHours.is_market_open()`).
- If `now - last_bar > DATA_STALE_THRESHOLD` (5 min) during market hours → sets `_data_healthy = False`, emits `alerter.critical(...)`, and calls `execution.activate_kill_switch("Data feed stale (…m)")` (`watchdog.py:82`).

### 9.4 Heartbeat generation

Once per tick, the driver calls `watchdog.write_heartbeat(bars_processed=<driver counter>)` (`watchdog.py:84`):
- Self-throttled to `HEARTBEAT_INTERVAL_S` (10s, `watchdog.py:35`) — the driver may call it every tick; the watchdog decides whether to write.
- Atomic write of `logs/heartbeat.json` with keys: `timestamp, market_open, data_healthy, equity, bars_processed, trades_today, kill_switched` (`watchdog.py:92`). `equity` is `execution.metrics.cash_balance` only (a **known simplification** — cash, not cash + open-position MTM; `RUNNER_EXTRACTION_BLUEPRINT.md` §2).

### 9.5 ⚠️ Live-mode gating (mandatory)

The watchdog uses wall-clock time and **must run only in live mode** (§6.5). In replay the driver **does not** call `record_bar` / `check_data_staleness` / `write_heartbeat` — otherwise it false-trips the kill switch and pollutes `heartbeat.json`. This is gated on `config.mode == LIVE`.

### 9.6 Kill-switch behavior

- The watchdog's only **action** is `execution.activate_kill_switch(reason)` (`handler.py:679`) — a soft kill: `_kill_switched = True`, critical alert, metrics persisted. Subsequent `process_signal` calls return `None`.
- The driver does **not** auto-clear the kill switch. Re-enabling trading after a stale-feed trip is an **operator decision** (a deactivation path on the handler / ops surface), never automatic — re-arming on a still-suspect feed is exactly the hazard ADR-004 guards against.
- A kill-switched loop **keeps running and keeps emitting heartbeat/telemetry** so the operator sees a live-but-halted process (§3.2).

---

## 10. Telemetry Integration

Reuses the **transport** `core/messaging/telemetry.py:TelemetryPublisher` and the UI path `flask_app/telemetry_bridge.py:TelemetryBridge`. **The gather-and-publish step does not exist in `F:\Nifty`** and is the driver's to build (`RUNNER_EXTRACTION_BLUEPRINT.md` §4 — "Transport yes / loop no"). Contrast with the watchdog, which is already a module.

### 10.1 Publisher construction

`TelemetryPublisher(host=config.telemetry_host, port=config.telemetry_port, node_name=config.telemetry_node, bind=...)` (`telemetry.py:13`). Default node `"trade_loop"`; default endpoint `tcp://127.0.0.1:5560` (the bridge's SUB endpoint, `CAPABILITY_REVIEW.md` §4). Topics become `telemetry.{metrics,positions,health}.trade_loop`.

### 10.2 Cadence

Throttled to `config.telemetry_interval_s` (the old `_telemetry_interval_s`, `RUNNER_DEPENDENCY_ANALYSIS.md` §3c). The driver tracks last-publish time and publishes at most once per interval — independent of the heartbeat cadence.

### 10.3 Metrics publishing — `publish_metrics(data)`

Built each interval from the **read-only** execution snapshot (these are the exact fields the old loop read; the coupling is documented in §10.7):
- `cash_balance`, `max_drawdown_pct`, `signals_received` from `handler.metrics` (`ExecutionMetrics`, `handler.py:83`).
- `trades_today` from `handler._trades_today`, `kill_switched` from `handler._kill_switched`.
- `data_healthy` from `watchdog.data_healthy` (`watchdog.py:47`), `bars_processed` from the driver counter, `market_open` from `MarketHours.is_market_open()`.

> **Drop the strategy-coupled line.** The old `_publish_telemetry` computed `active_count = len(self.strategies) - len(self._disabled_strategies)` (`RUNNER_DEPENDENCY_ANALYSIS.md` §3c, line 398). The driver has no `self.strategies`. This metric is **removed** (or, if a count is wanted, it is a plain int the driver already knows). This is the single strategy touch in the entire telemetry path and it does not survive into the platform.

### 10.4 Position publishing — `publish_positions(data)`

Two paths (MM9.3-S2):

**Enriched path** — when `LoopDriver` receives an injected `PortfolioView` (`portfolio_view is not None`, the production wiring via `fno_runner.py`): the payload is a full portfolio projection built from `PortfolioView.snapshot()`. Per-symbol entries carry real `pnl_pct` (computed from `_price_cache` and `Position.avg_price`) and `current_price`. A `_portfolio_summary` sentinel key (reserved metadata, never a valid NSE symbol) carries `cash_balance`, `realized_pnl`, `unrealized_pnl`, `mtm_equity`, `gross_exposure`, `used_margin`, and `portfolio_greeks` (delta/gamma/vega/theta/rho). The dashboard JS `updatePositions()` checks `position.quantity` — `_portfolio_summary` has none, so it is silently skipped.

**Degraded path** — when `PortfolioView` is absent (`None`, the pre-S2 default for tests and replay): the flat per-symbol pass-through from `position_tracker.get_all_positions()` with `pnl_pct=0.0` placeholder (unchanged from the original §10.4 contract). A startup `WARNING` makes the degradation observable.

The enriched path accesses `self._execution._price_cache` and `self._execution.metrics.cash_balance` — an infra-to-infra coupling pre-approved in MM9.2-S3-S2/MM9.3-S2 §S2.2. Both paths are read-only (ADR-001) and share the same best-effort, clock-throttled cadence as §10.2/§10.3 (§10.6). PortfolioView.snapshot() failures are caught and fall back to the degraded path (telemetry survives).

### 10.5 Health publishing — `publish_health(data)`

Node-level liveness: `node_name`, loop state (§3), `data_healthy`, `market_open`, uptime, last-tick timestamp. This is the "observable without broker login" requirement (Constitution §6) over the wire, complementary to the on-disk `heartbeat.json` (§9.4).

### 10.6 Fire-and-forget contract (and its honest cost)

`TelemetryPublisher` swallows all publish errors (`_safe_publish`, `telemetry.py:42` — "Telemetry failure must not break trading"). Therefore:
- Telemetry failure **never** propagates into the trade path (correct — Principle 2).
- Published telemetry is **not** a guaranteed record. The on-disk `heartbeat.json` and the persistence ledger are the durable truth; telemetry is best-effort observability.

### 10.7 ⚠️ Private-attribute coupling (acknowledge, don't rediscover)

Telemetry **and** the watchdog read **private** `ExecutionHandler` attributes — `handler._trades_today`, `handler._kill_switched` — and the internal `ExecutionMetrics` shape (`handler.py:83`). This is infra-to-infra coupling, not strategy coupling (`RUNNER_DEPENDENCY_ANALYSIS.md` §6.1), but it binds the driver to the handler's internal surface. The spec accepts this for v1 (the watchdog already does it). A future hardening could expose a public `handler.get_execution_stats()` (the seed exists near `handler.py:815`) and have both consumers read that instead; out of scope here, but recorded so it is a *decision*, not an accident.

---

## 11. Recovery Behavior

### 11.1 Restart behavior

On construction the driver enters **STARTUP/RECOVERY** before any bar is pulled. It must guarantee the ledger is restored and consistent before the loop can route a single signal (ADR-001, Constitution §7 "A position must never become untraceable").

### 11.2 Execution recovery (reuse — do NOT reimplement)

`ExecutionHandler._replay_state()` (`handler.py:219`) **already** restores, on construction when `load_db_state=True` (`handler.py:186`):
- all orders + the idempotency registry (`_seen_signals`),
- all fills → `order_tracker` + `position_tracker`,
- multi-leg groups,
- `_trades_today` (today's fills only).

The driver's responsibility is to **ensure this ran** (construct/accept a handler with `load_db_state=True`), **not** to re-restore state. Re-implementing restore in the driver would create a second source of position truth — a direct ADR-001 violation.

### 11.3 Reconciliation requirement

Before `STARTUP → RUNNING`, the driver invokes the handler's reconciliation engine (`handler.reconciliation`, a `ReconciliationEngine` over `position_tracker`, `handler.py:158`) to verify the restored ledger is consistent with broker truth. The engine's entry point is `ReconciliationEngine.reconcile(broker_positions: List[Dict]) -> List[ReconciliationAlert]` (`reconciliation.py:24`): it takes the broker's reported positions and returns a list of divergence alerts — **an empty list means consistent**; a non-empty list is a startup-gate failure (§11.4). The driver supplies `broker_positions` from the live broker adapter (live) or treats the check as vacuously clear in paper/replay where the broker has no independent book. (Broker-side reconciliation *depth* — pulling and normalizing live broker positions — is a separate, planned execution item, `PROJECT_STATE.md` Planned #6; the driver consumes whatever the engine returns and respects its verdict, never overwriting the ledger — ADR-001.)

### 11.4 Startup validation gate (hard stop)

`STARTUP → RUNNING` is permitted **only if** all hold:
1. `MarketDataProvider` constructed over a non-empty `config.symbols`.
2. `ExecutionHandler` constructed with `load_db_state=True` and `_replay_state()` completed without error.
3. Reconciliation (§11.3) reports consistent.
4. Broker reachable in the mode's required sense (live: auth/handshake OK; paper/mock: adapter present).

If **any** fails → the driver **refuses to start the loop**: emit `alerter.critical(...)`, log, transition `STARTUP → STOPPED`. **Trading on an unvalidated ledger is prohibited** (ADR-001; "the driver refuses to start" is the safe default, mirroring ADR-004's "protective control over optimism").

---

## 12. Failure Modes

For each: **detection**, **response**, **operator visibility**. The governing rule is Constitution §6 — *silent failure is unacceptable*; every failure must be observable without broker login.

### 12.1 Broker unavailable
- **Detection:** broker call raises / handshake fails (startup §11.4 step 4) or `place_order` raises during routing.
- **Response:** at startup → refuse to start (§11.4). At runtime → the failing `process_signal` is caught (§8.4); the loop survives. Repeated broker failures are a hard operational condition — the driver does **not** retry-spam; it logs, alerts, and (if the handler trips its own kill switch) goes to kill-switched-but-running.
- **Visibility:** `alerter.critical`, telemetry log line, `heartbeat.json` continues (process is alive), health publish reflects degraded broker.

### 12.2 Market data unavailable
- **Detection:** **replay** → `is_data_available` false for all symbols (clean exhaustion). **Live** → persistent `None` from `get_next_bar` (frozen feed).
- **Response:** replay exhaustion → `RUNNING → STOPPING` (normal end). Live freeze → handled by staleness (§12.3), not treated as a per-tick error.
- **Visibility:** replay end logged with final stats; live freeze surfaces via the staleness path below.

### 12.3 Stale data (the headline live hazard — ADR-004)
- **Detection:** `watchdog.check_data_staleness()` — `now - last_bar > 5 min` during market hours (`watchdog.py:75`).
- **Response:** `_data_healthy = False` → `alerter.critical` → `activate_kill_switch("Data feed stale (…m)")`. Trading halts; the loop keeps running. **No auto-recovery of trading** — `record_bar` will flip `data_healthy` back to true and log "DATA RECOVERED", but the kill switch stays set until an operator clears it (§9.6).
- **Visibility:** critical alert, `heartbeat.json` shows `data_healthy:false` + `kill_switched:true`, health telemetry shows degraded.

### 12.4 Telemetry failure
- **Detection:** `TelemetryPublisher` init or publish raises — but it is swallowed internally (`telemetry.py:18,53`).
- **Response:** **none in the trade path.** Telemetry failure is explicitly non-fatal (Principle 2). The loop, watchdog, and `heartbeat.json` are unaffected.
- **Visibility:** the **on-disk `heartbeat.json`** is the fallback liveness signal precisely because telemetry can silently die. If the dashboard goes dark but `heartbeat.json` is fresh, the operator knows it is a telemetry/transport problem, not a dead trader. This separation is intentional.

### 12.5 Reconciliation failure
- **Detection:** §11.3 reports inconsistency at startup, or a runtime reconciliation check (if driven) fails.
- **Response:** **at startup → refuse to start** (§11.4 — the strongest response, because an inconsistent ledger means positions may be untraceable, violating Constitution §7). At runtime → critical alert + operator escalation; the driver does not silently "fix" the ledger (ADR-001 — reconciliation detects/corrects against broker truth via the engine, it never lets the driver overwrite the ledger).
- **Visibility:** `alerter.critical`, refuse-to-start logged prominently, telemetry/health reflect the blocked state.

| Failure | Detection | Response | Loop survives? | Trading halts? |
|---|---|---|---|---|
| Broker unavailable | call raises / handshake | startup: refuse; runtime: catch + alert | yes (runtime) | maybe (handler kill) |
| Market data gone | `is_data_available`/`None` | replay: stop; live: → staleness | yes | no (until stale) |
| Stale data | watchdog 5-min | kill switch + alert | **yes** | **yes** |
| Telemetry failure | swallowed | none (non-fatal) | yes | no |
| Reconciliation fail | startup/runtime check | startup: **refuse to start** | n/a / yes | yes |

---

## 13. Configuration Model

A single config object (`core/runtime/config.py:DriverConfig`, new). Derived from the **infra-only** fields of the old `RunnerConfig` (the strategy fields `strategy_ids` / `log_signals` / `disable_state_update` are explicitly excluded — `RUNNER_DEPENDENCY_ANALYSIS.md` §4).

| Field | Type | Default | Purpose |
|---|---|---|---|
| `mode` | enum `LIVE` / `REPLAY` | — (required) | Gates clock semantics (§6) and watchdog (§9.5). |
| `symbols` | `List[str]` | — (required) | Instrument keys the provider tracks; non-empty (§11.4). |
| `poll_interval_s` | float | `0.5` | Live no-bar polling cadence (§7.3). |
| `max_bars` | `Optional[int]` | `None` | Replay/safety guard; `None` = unbounded (live). |
| `heartbeat_path` | str | `logs/heartbeat.json` | Watchdog beacon (§9.4). |
| `telemetry_enabled` | bool | `True` (live) / `False` (replay) | Whether to construct the publisher (§10). |
| `telemetry_host` | str | `127.0.0.1` | Publisher host. |
| `telemetry_port` | int | `5560` | Bridge SUB endpoint (§10.1). |
| `telemetry_node` | str | `trade_loop` | Telemetry topic suffix (§10.1). |
| `telemetry_interval_s` | float | (carried from old loop) | Telemetry throttle (§10.2). |
| `require_reconciliation_on_start` | bool | `True` | Startup gate strictness (§11.4); `False` only for explicit operator override. |

**Externally provided (not in `DriverConfig`, but required before a live run** — `SALVAGE_REPORT.md` §8 "Not done"): broker credentials / `.env`, DuckDB data paths, the instrument-master DB. The driver consumes already-constructed `ExecutionHandler` / `MarketDataProvider` / `Clock` / `SignalSource` (dependency injection) — it does not build them from raw config. This keeps the driver testable with mocks and the construction wiring at the entry-script layer (`scripts/`).

---

## 14. Acceptance Criteria

The driver is **complete** when all of the following are true and demonstrated:

### 14.1 Strategy-agnosticism (ADR-002)
- [ ] Forbidden-import scan over `core/runtime/` is **empty** (`core.strategies|runner|backtest|state|models|ftmo` → 0 hits), matching the platform-wide invariant (`PLATFORM_INVENTORY.md` header).
- [ ] The same driver runs all four `SignalSource` shapes (§5.3) with **no driver code change** — demonstrated by a futures-style, an option-style, a queue-backed discretionary, and a replay source.
- [ ] The driver imports `SignalSource` (abstract) only; it holds no reference to any concrete strategy.

### 14.2 Determinism (ADR-003)
- [ ] Single thread for the decision path; no concurrency in the loop body.
- [ ] Replaying the **same** recorded signals over the **same** bars produces **identical** order intent (same `process_signal` calls, same order, same `current_price = bar.close`).
- [ ] `clock.set_time(bar.timestamp)` (replay) advances before any signal evaluation; live uses `RealTimeClock.now()`; the base-`Clock` no-op `set_time` exists (§6.4).

### 14.3 No trading on stale data (ADR-004, §9)
- [ ] In **live** mode the driver calls `record_bar` / `check_data_staleness` / `write_heartbeat` each tick; in **replay** it calls none of them (§9.5).
- [ ] A simulated 5-minute live feed gap during market hours trips `activate_kill_switch`, halts routing, and the loop keeps running and emitting heartbeat.
- [ ] `logs/heartbeat.json` is written atomically with the 7 documented keys (§9.4).

### 14.4 Execution reuse (ADR-005, §8)
- [ ] All trading goes through `ExecutionHandler.process_signal(signal, bar.close)`; the driver creates/submits no orders and computes no sizing/risk/margin.
- [ ] A raised `process_signal` exception is caught, logged, surfaced to telemetry, and does **not** kill the loop.
- [ ] The driver never decides exits; `SignalType.EXIT` flows through the same seam.

### 14.5 Ledger truth + recovery (ADR-001, §11)
- [ ] The driver does not write positions/PnL; it only reads trackers for telemetry.
- [ ] Recovery reuses `ExecutionHandler._replay_state()` (no second restore path).
- [ ] Startup validation refuses `STARTUP → RUNNING` on reconciliation/recovery/broker/symbol failure, with a critical alert (§11.4).

### 14.6 Observability (Constitution §6, §10)
- [ ] Telemetry metrics/positions/health publish on cadence; the `active_count` strategy line is absent (§10.3).
- [ ] Telemetry failure is non-fatal and does not touch the trade path; `heartbeat.json` remains the durable liveness fallback (§12.4).
- [ ] PAUSED is distinguishable from STOPPED and from a dead process via heartbeat + health telemetry.

### 14.7 Lifecycle (§3)
- [ ] All six states reachable; transitions match §3.2 (including kill-switched-but-running and refuse-to-start).
- [ ] `stop()` drains the current tick, flushes telemetry, closes the publisher (`TelemetryPublisher.close`, `telemetry.py:55`), and reaches STOPPED even if the flush fails.

### 14.8 Prerequisites surfaced (not silently assumed)
- [ ] The base-`Clock` `set_time` no-op addition (§6.4) is implemented as part of this work.
- [ ] The private-attribute coupling (§10.7) and the live-fill off-thread seam (§8.3) are documented in code comments where they occur, so they are decisions, not surprises.

---

## 15. Runtime Event Journal

### 15.1 Purpose

A **durable, append-only operational audit trail** that records *what happened in the running process and why* — the lifecycle and incident record of the driver. It complements, and is deliberately distinct from, the three observability surfaces already specified:

- `logs/heartbeat.json` (§9.4) — current liveness snapshot.
- Telemetry (§10) — best-effort live stream to the dashboard.
- The ledger (orders/fills/positions/PnL via `ExecutionHandler` persistence; ADR-001) — the authoritative trading record.

The journal answers the operator's *post-hoc* question — "what sequence of events led here, and why did trading stop?" — which none of the three above answers durably. It is the on-disk narrative that survives a crash and a dark dashboard.

### 15.2 Location and format

- **Location:** `logs/runtime_events.jsonl`.
- **Format:** **JSON Lines** — exactly **one JSON object per line**, newline-terminated, UTF-8. No surrounding array, no commas between records. This makes the file **append-only by construction** (a writer only ever opens in append mode and writes one line) and tail-/grep-friendly for operators.
- **Append discipline:** the driver opens the file in append mode and writes complete lines; it never rewrites, truncates, or re-orders prior lines. A partially-written final line (crash mid-write) is tolerated by readers (skip-on-parse-error), never repaired in place.
- **Rotation (operational, out of v1 scope to *implement*, but reserved):** rotation, if added, must preserve append-only semantics (rotate to `runtime_events-YYYY-MM-DD.jsonl`; never edit a live file).

### 15.3 Event record schema

Every line is one object with these fields (all required):

| Field | Type | Description |
|---|---|---|
| `timestamp` | string | ISO-8601 with timezone, IST (`Asia/Kolkata`), wall-clock — consistent with `heartbeat.json` (§9.4). Operational time, not the deterministic trade `Clock` (§6.5). |
| `event_type` | string | One of the enumerated types in §15.4. |
| `severity` | string | `INFO` \| `WARNING` \| `CRITICAL`. |
| `source_component` | string | Emitting component, e.g. `LoopDriver`, `RuntimeWatchdog`, `ExecutionHandler`, `ReconciliationEngine`. |
| `message` | string | Human-readable one-line description. |
| `metadata` | object | Free-form structured context (may be `{}`). Event-specific keys — see §15.4. |

### 15.4 Minimum required event types

The driver must emit at least the following. Severity and typical source are normative; `metadata` keys are illustrative minimums.

| `event_type` | severity | source_component | Emitted when | Typical `metadata` |
|---|---|---|---|---|
| `STARTUP` | INFO | LoopDriver | Process enters STARTUP (§3.1). | `mode`, `symbols`, `pid` |
| `RECOVERY_STARTED` | INFO | LoopDriver | Before ledger recovery is ensured (§11.2). | — |
| `RECOVERY_COMPLETED` | INFO | LoopDriver | After `_replay_state()` restored state. | `orders`, `fills`, `trades_today` |
| `RECONCILIATION_PASS` | INFO | ReconciliationEngine | `reconcile(...)` returned an empty alert list (§11.3). | `positions_checked` |
| `RECONCILIATION_FAIL` | CRITICAL | ReconciliationEngine | `reconcile(...)` returned ≥1 alert; startup gate fails (§11.4). | `alerts` (list) |
| `RUNNING` | INFO | LoopDriver | `STARTUP → RUNNING` (gate passed, §3.2). | — |
| `PAUSED` | WARNING | LoopDriver | `RUNNING → PAUSED` (operator). | `reason` |
| `RESUMED` | INFO | LoopDriver | `PAUSED → RUNNING`. | — |
| `KILL_SWITCH_ACTIVATED` | CRITICAL | ExecutionHandler | Driver detects `_kill_switched` flipped true (edge-triggered, once). | `reason` |
| `WATCHDOG_STALE_DATA` | CRITICAL | RuntimeWatchdog | `check_data_staleness()` trips during market hours (§9.3). | `minutes_stale` |
| `BROKER_ERROR` | WARNING\|CRITICAL | LoopDriver | A `process_signal`/broker call raised (§8.4) or handshake failed (§11.4). | `error`, `signal_id` |
| `TELEMETRY_FAILURE` | WARNING | LoopDriver | A telemetry failure the driver can *observe* (e.g. publisher construction failed). See §15.6. | `detail` |
| `STOPPING` | INFO | LoopDriver | `→ STOPPING` (stop requested / replay exhausted / `max_bars`). | `trigger` |
| `STOPPED` | INFO | LoopDriver | Loop exited cleanly; terminal (§3.1). | `bars_processed`, `uptime_s` |

Edge-triggering rule: state-transition and incident events are written **once per occurrence**, not per tick. `KILL_SWITCH_ACTIVATED` and `WATCHDOG_STALE_DATA` are recorded on the transition into the condition (mirroring the watchdog's own `_data_stale_alerted` de-dup, `watchdog.py:67`), not repeatedly while the condition persists.

### 15.5 Heartbeat vs. Telemetry vs. Event Journal — three different questions

These three surfaces exist on purpose and must not be collapsed into one another:

| Surface | Answers | Shape | Durability |
|---|---|---|---|
| **Heartbeat** (`logs/heartbeat.json`, §9) | **"Is the process alive?"** | Single, overwritten snapshot — only *now* matters. | Latest-only (last write wins). |
| **Telemetry** (ZMQ → dashboard, §10) | **"What is the process seeing?"** | Continuous live stream of metrics/positions/health. | Ephemeral, fire-and-forget, lossy (§10.6). |
| **Event Journal** (`logs/runtime_events.jsonl`, §15) | **"What happened, and why?"** | Append-only sequence of discrete lifecycle/incident events. | Durable history; survives crash and dark dashboard. |

Worked example — a stale-feed trip during market hours produces, across the three: heartbeat flips `data_healthy:false` / `kill_switched:true` (you see the *current* bad state); telemetry's health stream goes degraded *if the dashboard is watching at that moment*; the journal records a `WATCHDOG_STALE_DATA` (CRITICAL) line followed by `KILL_SWITCH_ACTIVATED` (CRITICAL) with the reason — and those two lines are **still there tomorrow**, in order, explaining exactly what happened and why trading halted. That post-hoc "why", in order, is the journal's unique job.

### 15.6 Honest limits (consistent with the rest of the spec)

- **`TELEMETRY_FAILURE` is best-effort.** `TelemetryPublisher` swallows publish errors internally (`telemetry.py:42`; §10.6), so the driver cannot reliably detect every dropped publish. The journal records only telemetry failures the driver *can* observe (e.g. publisher init failure). This is a known limit, not a guarantee — stated so it is not mistaken for one.
- **Journal write failure is non-fatal to trading** (same principle as telemetry, §12.4): a failed journal append is logged and the loop continues. The journal is observability, not the trade path.

### 15.7 Authority boundary (non-negotiable)

- The journal is **append-only** and is **never a source of position truth.** It records *events about* trading; it does not record positions/PnL as authoritative state.
- The **ledger** (`ExecutionHandler` trackers + persistence) remains the **sole authoritative trading record** (Principle 1, ADR-001). Recovery (§11.2) restores from the ledger, **never** from the journal.
- Nothing may reconstruct positions, PnL, or order state from `runtime_events.jsonl`. If the journal and the ledger ever disagree, the ledger is right and the journal is merely an observation log. The journal is downstream of truth, never a substitute for it.

> **Scope note:** this section adds an observability *responsibility* to the driver (emit lifecycle/incident events). It does **not** change any execution, ledger, risk, or signal-routing responsibility specified in §1–§14, and it introduces no new trade path (ADR-006).

---

## Appendix A — File map (what implementation will create / modify)

> No code here — this is the decomposition the plan-rigor self-review checks against. "Modify" lines are minimal and additive.

**Create**
- `core/runtime/__init__.py` — package marker.
- `core/runtime/signal_source.py` — abstract `SignalSource` (§5.2): `on_bar`, `on_start`, `on_stop`.
- `core/runtime/config.py` — `DriverConfig` + `Mode` enum (§13).
- `core/runtime/driver.py` — the `LoopDriver`: lifecycle (§3), per-tick pipeline (§4), bar pull (§7), routing (§8), watchdog drive (§9), telemetry gather+publish (§10), startup gate (§11), runtime event journal emission (§15).

**Runtime artifacts written**
- `logs/heartbeat.json` — liveness snapshot (via `RuntimeWatchdog`, §9.4).
- `logs/runtime_events.jsonl` — append-only operational audit trail (§15).

**Modify (minimal, additive)**
- `core/clock.py` — add no-op `set_time(dt)` to base `Clock` (§6.4). `ReplayClock.set_time` already exists; `RealTimeClock` inherits the no-op.
- `scripts/` — a new entry script (e.g. `scripts/run_trade_loop.py`) wiring concrete `ExecutionHandler` + `MarketDataProvider` + `Clock` + a `SignalSource` + `RuntimeWatchdog` + `TelemetryPublisher` into a `LoopDriver`. (Wiring lives at the entry layer, §13 — not in the driver.)

**Reuse unchanged**
- `core/execution/handler.py`, `core/execution/watchdog.py`, `core/messaging/telemetry.py`, `core/database/providers/base.py`, `core/events.py`, `core/database/utils/market_hours.py`, `core/alerts/alerter.py`, `core/logging`.

---

## Appendix B — Explicit non-goals (so scope cannot creep)

- ❌ No strategy, signal generation, or alpha (ADR-002, §1.3).
- ❌ No exit-condition (TP/SL/time-stop) logic (§1.3).
- ❌ No backtesting framework — the replay `SignalSource` injects *recorded* signals; it does not generate or evaluate them (§5.3).
- ❌ No sizing / risk / margin / fill computation — all in `ExecutionHandler` (§8).
- ❌ No SPAN margin engine and no F&O product-model change — these are separate planned execution-depth items (`PROJECT_STATE.md` Planned #4–#5) and **block live option selling regardless of the driver** (`RUNNER_EXTRACTION_BLUEPRINT.md` Readiness caveats). The driver is required for *paper/intraday* operation and for closing Principle 3/5; it does not by itself make live carry trades legal.
- ❌ No platform redesign; no new event types (reuse `core/events.py`).
```
