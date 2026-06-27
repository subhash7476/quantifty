# MM9.2-S3-S3 — Fresh Price Gate: Implementation Specification

**Status:** READY FOR IMPLEMENTATION  
**Milestone:** MM9.2 (Portfolio Margin Awareness) — Slice 3, Sub-step 3  
**Prerequisites:** MM9.2-S3-S1 (PriceSnapshot), MM9.2-S3-S2 (per-bar feed hook) — both COMPLETE and committed  
**Implementation target:** GLM  
**Spec version:** 1.0  
**Author:** Architecture review  

---

## Context

S3-S1 introduced `PriceSnapshot` (frozen dataclass: `price: float`, `timestamp: datetime`) and replaced the two parallel dicts (`_latest_prices` + `_price_timestamps`) with a single `_price_cache: Dict[str, PriceSnapshot]`.

S3-S2 introduced the per-bar feed hook in `LoopDriver._tick()`: every bar warms `_price_cache` via `execution.update_market_price(symbol, bar.close)` before `source.on_bar()` runs. This eliminated the signal-only staleness problem — the signaling symbol is always fresh, and held symbols receive warmth from every data tick in the driver's universe.

S3-S3 closes the remaining gap: no gate currently blocks `process_signal` when held positions have stale or absent prices. Without this gate, `_check_margin_budget` can run on a partial book and return a misleadingly low utilisation, allowing a new entry that exceeds true capital utilisation.

---

## §1 — Repository Impact

### 1.1 Production files changed

| File | Change |
|------|--------|
| `core/execution/handler.py` | (a) Add `max_price_age_s: float = float('inf')` to `ExecutionConfig` dataclass. (b) Add `_check_book_priceable()` private method. (c) Add freshness gate call-site in `process_signal` inside `if signal.signal_type != SignalType.EXIT:`, immediately before the MM9.1 capital gate (`_check_margin_budget`). |
| `core/runtime/event_journal.py` | (a) Add `PORTFOLIO_UNPRICEABLE = "PORTFOLIO_UNPRICEABLE"` to `EventType` enum. (b) Add `EventType.PORTFOLIO_UNPRICEABLE: Severity.WARNING` to `_DEFAULT_SEVERITY`. |

### 1.2 New test file

`tests/execution/test_handler_s3_s3_gate.py` — created from scratch. See §7 for full test plan.

### 1.3 Existing tests requiring modification

**None.** The default `max_price_age_s = float('inf')` disables the gate. No existing test can reference a field that does not yet exist in `ExecutionConfig`. Any existing test that constructs `ExecutionConfig()` without specifying `max_price_age_s` gets `float('inf')` by default — gate is a no-op, existing behaviour is preserved.

GLM must verify this assumption by searching for any test file that calls `_check_book_priceable` or imports `PORTFOLIO_UNPRICEABLE` — both should produce zero hits before implementation begins (confirming they do not yet exist).

### 1.4 Documentation

No documentation files are added or modified during S3-S3 implementation. The coupling note in `docs/DRIVER_SPECIFICATION.md` was committed as a prerequisite before S3-S2. The KB sync (PROJECT_STATE, CHANGELOG) is a post-implementation step for the human author.

---

## §2 — Behaviour

### 2.1 Freshness threshold

`max_price_age_s` specifies the maximum age of a `PriceSnapshot` in seconds. A snapshot is FRESH if its age is <= `max_price_age_s`. A snapshot is STALE if its age is strictly greater.

### 2.2 Configuration location

`ExecutionConfig.max_price_age_s: float = float('inf')`

This field is placed after `max_capital_utilisation` (the last existing field). It is part of `ExecutionConfig` — not a constructor parameter of `ExecutionHandler`, not a global constant, not a separate config object.

### 2.3 Default and initial rollout

Default is `float('inf')` (gate disabled). See §6 for the full rationale, which turns on the scenario of non-universe recovered positions causing a permanent block if the gate is armed before that scenario is handled.

Operators enable the gate by setting `max_price_age_s=600.0` in their `ExecutionConfig`. 600 seconds (10 x 1-minute bars) is the recommended operational threshold once the prerequisite conditions in §6 are satisfied.

### 2.4 Disabled behaviour

When `max_price_age_s == float('inf')`, `_check_book_priceable()` MUST return `(True, set())` immediately without iterating `_price_cache` or `position_tracker`. This is not a micro-optimisation: it is the correctness contract that prevents gate logic from running when the operator has not opted in.

Implementation: `if math.isinf(self.config.max_price_age_s): return True, set()`

### 2.5 Timestamp source

All price timestamps are assigned by `update_market_price()` using `self.clock.now()`. The freshness gate evaluates age as `self.clock.now() - snap.timestamp`. **Never use `datetime.now()`** — this would break determinism (ADR-003) and make backtest replay non-deterministic.

### 2.6 Comparison rule

A snapshot is STALE if: `(self.clock.now() - snap.timestamp).total_seconds() > self.config.max_price_age_s`

Strictly greater-than. The consequence is described in §2.7.

### 2.7 Equality boundary

A snapshot whose age is **exactly** `max_price_age_s` is classified FRESH (allowed). The rule `age > threshold` means the boundary is inclusive-FRESH. This is consistent with Python convention and avoids off-by-one edge cases at the first bar (where `age == 0` and threshold is finite). A test must assert this explicitly (see §7, TC-U4).

### 2.8 Missing-symbol behaviour (symbol in positions but absent from cache)

If a symbol appears in `position_tracker.get_all_positions()` with a non-FLAT side AND has no entry in `_price_cache`, it is classified UNPRICEABLE (equivalent to infinitely stale). The gate blocks. The symbol is included in the `missing_symbols` set in the log and event payload.

This is the correct treatment: a position with no price cannot be included in the margin book. Silently excluding it would produce the same C3 class defect (under-counted utilisation) that the gate is designed to prevent.

### 2.9 Cache-empty behaviour

If `_price_cache` is entirely empty AND the position tracker has non-FLAT positions, all held symbols are MISSING — the gate blocks. If `_price_cache` is empty AND all positions are FLAT, the book is vacuously priceable — the gate passes.

### 2.10 EXIT signal handling

EXIT signals bypass the freshness gate entirely. This is inherited from the existing outer guard `if signal.signal_type != SignalType.EXIT:`. The freshness gate call-site is inside this guard, so EXIT signals reach `order_tracker` and `broker` without passing through `_check_book_priceable()`. Exiting a position always reduces margin. Blocking EXIT on account of stale prices would create a worse outcome (stranded positions that cannot be closed).

### 2.11 PAPER vs LIVE mode

The gate is **mode-independent**. It reads only `_price_cache` and `self.clock.now()`, both of which are mode-independent. The MM8 watchdog (WATCHDOG_STALE_DATA) is live-only and wall-clock-based; the freshness gate is all-mode and deterministic-clock-based. Operators running in PAPER mode with a finite `max_price_age_s` will see blocking behaviour on stale prices — this is intentional and desirable for staging validation.

### 2.12 Startup cold window

On the first sweep through `LoopDriver._tick()`, symbols are processed in iteration order over `config.symbols`. Symbols later in the list are NOT yet in `_price_cache` when earlier symbols' signals fire within the same sweep. This is a bounded, self-resolving cold window: after one complete sweep, all universe symbols are in `_price_cache`.

Consequence: if a signal arrives in the very first sweep while a held position's symbol has not yet been ticked, the gate will block it (MISSING). This is correct — the book genuinely cannot be priced at that moment. The block is transient and resolves within the same sweep. GLM must not add startup bypass logic.

### 2.13 Replay behaviour

Replay feeds historical bars through `LoopDriver._tick()` with a deterministic clock. The gate is fully replay-identical: the same decision (FRESH, STALE, MISSING) is reproduced on every run of the same replay. This is the correct behaviour — gate decisions are part of the trading record and must be reproducible.

### 2.14 Interaction with kill switch

The kill switch check (handler.py:537) runs at step 2 of `process_signal`, before the freshness gate. A kill-switched handler returns `None` before evaluating freshness. Conversely, the freshness gate never trips the kill switch: it returns `None` (no order placed) and emits a WARNING-severity journal event. The kill switch is a separate, more severe mechanism (Severity.CRITICAL, KILL_SWITCH_ACTIVATED) activated only by breach of hard limits.

### 2.15 Interaction with MM9.1 capital gate

The freshness gate runs **before** the capital gate (`_check_margin_budget`). If the freshness gate blocks, the capital gate is never evaluated — no utilisation computation runs on a partial book. If the freshness gate passes (all held positions FRESH), the capital gate runs exactly as before. The two gates are independent; neither gate modifies shared state of the other.

---

## §3 — Event Design

### 3.1 New EventType: PORTFOLIO_UNPRICEABLE

Add to `core/runtime/event_journal.py`:

```python
# In EventType enum:
PORTFOLIO_UNPRICEABLE = "PORTFOLIO_UNPRICEABLE"

# In _DEFAULT_SEVERITY:
EventType.PORTFOLIO_UNPRICEABLE: Severity.WARNING,
```

### 3.2 Justification vs existing types

`WATCHDOG_STALE_DATA` (existing, CRITICAL) is compared below:

| Attribute | WATCHDOG_STALE_DATA | PORTFOLIO_UNPRICEABLE |
|-----------|---------------------|-----------------------|
| Component | RuntimeWatchdog | ExecutionHandler |
| Scope | Aggregate feed (all symbols) | Per-signal, per held position |
| Trigger | Wall-clock elapsed since last bar | Deterministic clock age of cached snapshot |
| Severity | CRITICAL (raise halt, ops page) | WARNING (block entry, log to audit trail) |
| Mode | Live only | All modes (PAPER, LIVE, replay) |
| Clock | Wall clock | `self.clock.now()` (deterministic) |
| Operator response | Restart feed, investigate broker | Investigate symbol-specific feed health |
| Entry point | `_drive_watchdog()` in LoopDriver | `process_signal()` in ExecutionHandler |

These are distinct enough to warrant a distinct EventType. Mapping PORTFOLIO_UNPRICEABLE to WATCHDOG_STALE_DATA would conflate component-level and portfolio-level staleness and give operators misleading severity guidance.

### 3.3 Why the freshness gate emits a journal event when the MM9.1 capital gate does not

The MM9.1 capital gate increments `rejected_trades` and logs a WARNING but does not write a journal event. The freshness gate does. The distinction is defensible: a margin budget rejection is a routine operational limit hit, expected under normal market conditions. A price-unavailability event is a structural data-quality signal — it indicates a specific symbol's feed is broken or a position recovery resulted in a non-universe holding. Audit-trail visibility is warranted for the latter.

### 3.4 Journal event payload

```python
self._journal.record(
    event_type=EventType.PORTFOLIO_UNPRICEABLE,
    context={
        "signal_id": signal.signal_id,
        "signal_symbol": signal.symbol,
        "missing_symbols": sorted(missing),   # never-seen in _price_cache
        "stale_symbols": sorted(stale),        # seen but age > threshold
        "stale_ages_s": {sym: age for sym, age in stale_ages.items()},
        "max_price_age_s": self.config.max_price_age_s,
    }
)
```

The `_journal` reference may be `None` (common in backtest tests). The call-site must guard: `if self._journal:`.

---

## §4 — Runtime Ordering

The authoritative ordering for a single bar cycle is:

```
LoopDriver._tick()
|
+-- for symbol in config.symbols:
|   +-- bar = provider.get_bar(symbol)            # data fetch
|   +-- clock.set_time(bar.timestamp)             # deterministic clock advance
|   +-- execution.update_market_price(            # [S3-S2] cache warm — all held
|   |       symbol, bar.close)                    #   symbols warmed each tick
|   +-- signals = source.on_bar(bar)              # strategy evaluation (read-only)
|   +-- _dispatch_signals(signals, bar)
|       +-- for signal in signals:
|           +-- process_signal(signal, current_price)
|               |
|               +-- update_market_price(          # ensures signaling symbol is
|               |       signal.symbol,            #   always current-bar fresh
|               |       current_price)            #   (belt-and-suspenders vs S3-S2)
|               +-- [step 2]  kill switch check   # returns None if activated
|               +-- [step 3]  daily trade limit
|               +-- [step 4]  drawdown kill
|               +-- [step 5]  stacking guard
|               +-- [step 6]  risk checks
|               +-- [step 7]  order creation
|               +-- [step 8]  pre-trade risk
|               |
|               +-- if signal.signal_type != SignalType.EXIT:
|                   |
|                   +-- [S3-S3] _check_book_priceable()   <-- FRESHNESS GATE
|                   |   +-- if not priceable:
|                   |       +-- log WARNING
|                   |       +-- journal PORTFOLIO_UNPRICEABLE
|                   |       +-- metrics.rejected_trades += 1
|                   |       +-- return None
|                   |
|                   +-- [MM9.1] _check_margin_budget()    <-- CAPITAL GATE
|                       +-- if not approved:
|                           +-- log WARNING
|                           +-- metrics.rejected_trades += 1
|                           +-- return None
|
|               +-- order_tracker.add_order(order)
|               +-- broker.place_order(order)
|
+-- _drive_watchdog()     # live-only, wall-clock aggregate feed check
```

**Ordering rationale:**

1. `update_market_price` (S3-S2, driver-level) runs before `source.on_bar()` — strategies receive a signal at a point when the full driver-universe price cache is warm.
2. `update_market_price` (process_signal, signal-level) runs first inside `process_signal` — this is belt-and-suspenders; after S3-S2 the signaling symbol was already warmed, but this ensures it is fresh to the exact bar being processed (not any prior partial-sweep state).
3. Freshness gate before capital gate — a partial book (missing or stale prices) would cause `get_exposure()` in `MarginTracker` to silently exclude those symbols (it calls `current_prices.get(sym)` which returns `None` for missing keys, then `_calculate_single_exposure` returns 0.0 for `None` price). This produces an artificially low utilisation, bypassing the margin budget check. The freshness gate prevents this class of defect entirely.
4. Both gates inside `if not EXIT` — EXIT signals reduce exposure; gating them on price availability is unsafe.
5. `order_tracker.add_order()` only runs after both gates pass — no orphaned order records on gate rejection.
6. Watchdog runs after the per-symbol sweep at the driver level — it is a separate, aggregate, wall-clock mechanism with no interaction with the per-signal freshness gate.

---

## §5 — Failure Matrix

| # | Condition | Gate result | EventType | Log severity | `return` | `rejected_trades` |
|---|-----------|-------------|-----------|-------------|----------|-------------------|
| F1 | All held positions FRESH (age <= threshold), non-EXIT | Pass | — | — | Proceeds to capital gate | +0 |
| F2 | One or more held positions STALE (age > threshold), non-EXIT | Block | PORTFOLIO_UNPRICEABLE | WARNING | None | +1 |
| F3 | One or more held positions MISSING (no entry in `_price_cache`), non-EXIT | Block | PORTFOLIO_UNPRICEABLE | WARNING | None | +1 |
| F4 | Cache empty, non-FLAT positions, non-EXIT | Block | PORTFOLIO_UNPRICEABLE | WARNING | None | +1 |
| F5 | Cache empty, all positions FLAT (empty book), non-EXIT | Pass | — | — | Proceeds to capital gate | +0 |
| F6 | EXIT signal, any cache state | Pass (gate bypassed by outer guard) | — | — | Proceeds normally | +0 |
| F7 | `max_price_age_s == float('inf')` (disabled), non-EXIT | Pass (early return, no iteration) | — | — | Proceeds to capital gate | +0 |
| F8 | PAPER mode, stale price | Block | PORTFOLIO_UNPRICEABLE | WARNING | None | +1 |
| F9 | LIVE mode, stale price | Block | PORTFOLIO_UNPRICEABLE | WARNING | None | +1 |
| F10 | Startup first sweep, held symbol not yet ticked (MISSING) | Block (transient, resolves <=1 sweep) | PORTFOLIO_UNPRICEABLE | WARNING | None | +1 |
| F11 | Non-universe recovered position (permanent MISSING) | Block (permanent until position closed or gate disabled) | PORTFOLIO_UNPRICEABLE | WARNING | None | +1 per signal |
| F12 | `age == max_price_age_s` exactly (equality boundary) | Pass (not strictly greater-than) | — | — | Proceeds to capital gate | +0 |
| F13 | Kill switch already active at step 2 | Gate not reached (None returned before gate) | — | — | None | +0 |
| F14 | `_journal is None` (backtest, no journal configured) | Block or Pass per normal rules; journal write silently skipped | — | WARNING (logger only) | None if blocked | +1 if blocked |

---

## §6 — Configuration

### 6.1 Recommendation: keep `float('inf')` as the shipped S3-S3 default

**Do NOT change the default to 600.0 in this slice.**

The rationale is a concrete failure scenario, not generic caution:

**Non-universe recovered position scenario:**
After an F&O expiry, the position ledger retains the expired option position (e.g., `NSE_FO|NIFTY23JUN19500CE`) until the operator explicitly closes it or it is rolled. The instrument is no longer in `config.symbols` for the new session. `LoopDriver._tick()` only ticks symbols in `config.symbols`. The expired instrument never receives a `bar`, never enters `_price_cache`, and is permanently MISSING. With `max_price_age_s=600.0`, the freshness gate blocks every new entry indefinitely — a trading-wide outage from a single recovered position whose symbol is not in the driver universe.

This scenario is reachable in production F&O usage. Resolving it requires either (a) a startup validation that detects non-universe held positions and alerts the operator, or (b) a mechanism to source prices for non-universe held positions from a secondary channel. Neither is in scope for S3-S3.

**Prerequisite to arm 600.0:**
A future sub-step (candidate: MM9.2-S3-S4 or MM9.3) must add startup detection of non-universe held positions. At startup, if `position_tracker` has non-FLAT positions whose symbols are absent from `config.symbols`, the handler should journal a CRITICAL event and either halt or force-close those positions. Only after that prerequisite is complete is it safe for operators to set `max_price_age_s=600.0`.

### 6.2 Threshold constraint for future operators

When operators do arm the gate, the threshold must satisfy: `max_price_age_s >= 2 x bar_interval_seconds`. For 1-minute bars, this means `max_price_age_s >= 120`. At 600s, the margin is 5x.

The reason is intra-tick ordering: within a single `_tick()` sweep, held symbols are warmed in iteration order. When symbol A's signal is processed, symbol B (later in the iteration order) may not yet have been ticked this sweep — its snapshot is from the previous sweep, up to one bar old. The threshold must absorb this one-bar staleness without false-positive blocking.

### 6.3 Field definition

```python
# In ExecutionConfig (core/execution/handler.py), after max_capital_utilisation:
max_price_age_s: float = float('inf')
```

No validator, no range check. Operators are responsible for setting a value consistent with their bar interval and the prerequisites in §6.1.

---

## §7 — Testing Plan (TDD — RED -> GREEN)

All tests go in `tests/execution/test_handler_s3_s3_gate.py`. Use the existing handler test fixture patterns (see `tests/execution/test_handler.py` for setup conventions: `PaperBroker`, `MockOrderTracker`, synthetic `SignalEvent`, etc.).

Write each test, watch it fail (RED), implement the minimal code to pass it (GREEN), then move to the next.

### Phase 0 — Characterization (before writing any S3-S3 code)

**TC-C1: `max_price_age_s` not yet in `ExecutionConfig`**
```python
# Assert that ExecutionConfig() lacks `max_price_age_s` attribute
# Confirms the field does not pre-exist; DELETE after S3-S3 implementation
assert not hasattr(ExecutionConfig(), 'max_price_age_s')
```

**TC-C2: `PORTFOLIO_UNPRICEABLE` not yet in EventType**
```python
assert not hasattr(EventType, 'PORTFOLIO_UNPRICEABLE')
```

### Phase 1 — Unit tests for `_check_book_priceable()`

All tests configure `max_price_age_s=60.0` and use a mock clock set to a known time.

**TC-U1: flat book -> vacuously priceable**
Position tracker has no non-FLAT positions. Assert `_check_book_priceable()` returns `(True, set())`.

**TC-U2: disabled gate -> always priceable**
Position tracker has a non-FLAT position with a stale snapshot. `max_price_age_s=float('inf')`. Assert `(True, set())`.

**TC-U3: fresh snapshot -> priceable**
Position tracker has one non-FLAT position (symbol `X`). Cache has `X` with `clock.now() - 30s`. `max_price_age_s=60`. Assert `(True, set())`.

**TC-U4: age == threshold -> priceable (equality boundary)**
Cache has `X` with `clock.now() - 60s` exactly. `max_price_age_s=60`. Assert `(True, set())`.

**TC-U5: age > threshold -> not priceable, stale set**
Cache has `X` with `clock.now() - 61s`. `max_price_age_s=60`. Assert `result == (False, {'X'})`.

**TC-U6: symbol missing from cache -> not priceable, missing set**
Position tracker has non-FLAT position on `X`. Cache is empty. `max_price_age_s=60`. Assert `(False, {'X'})`.

**TC-U7: mix of fresh and stale -> not priceable, stale in set**
Positions on `X` (fresh) and `Y` (stale). Assert returns `(False, {'Y'})`.

**TC-U8: mix of fresh and missing -> not priceable, missing in set**
Positions on `X` (fresh) and `Y` (missing). Assert returns `(False, {'Y'})`.

**TC-U9: FLAT position on stale symbol -> priceable (FLAT is excluded)**
Position tracker has `X` as FLAT (PositionSide.FLAT) with stale/missing snapshot. Assert `(True, set())`. FLAT positions do not contribute to margin and must not trigger the gate.

### Phase 2 — Call-site unit tests (via `process_signal`)

Build a minimal handler with `max_price_age_s=60.0`, mock clock, one non-FLAT position on `AAPL`, paper broker, mock order tracker.

**TC-S1: EXIT signal bypasses gate entirely**
`_price_cache` empty. Send EXIT signal for `AAPL`. Assert `process_signal` does NOT return `None` for the gate reason; order is placed.

**TC-S2: non-EXIT with stale held position -> returns None**
Advance clock past threshold for `AAPL` snapshot. Send ENTRY signal for `AAPL`. Assert `process_signal` returns `None`.

**TC-S3: non-EXIT with fresh prices -> proceeds to capital gate**
Warm `AAPL` with current-bar price. Send ENTRY signal. Assert the flow reaches `_check_margin_budget` (verify by checking `rejected_trades` count and broker call count separately).

**TC-S4: `rejected_trades` incremented on gate block**
Trigger a freshness block. Assert `handler.metrics.rejected_trades` incremented by 1.

**TC-S5: logger WARNING emitted on block**
Use `caplog` or mock logger. Assert a WARNING-level log containing `PORTFOLIO_UNPRICEABLE` and the stale symbol name is emitted on block.

**TC-S6: journal event written on block**
Inject a mock journal. Trigger freshness block. Assert `journal.record` called with `event_type=EventType.PORTFOLIO_UNPRICEABLE`.

**TC-S7: journal event not written when `_journal is None`**
Construct handler without journal (common in backtest). Trigger freshness block. Assert no `AttributeError` raised and broker never called.

**TC-S8: disabled gate does not block even with missing prices**
`max_price_age_s=float('inf')`. Cache empty. Non-FLAT position. Send ENTRY signal. Assert order is placed (gate does not block).

### Phase 3 — Integration tests

**TC-I1: end-to-end with handler + paper broker + signal + freshness block**
Full handler lifecycle: `__init__`, position opened via prior FillEvent, prices advanced past threshold, new ENTRY signal. Assert no order placed, `rejected_trades == 1`.

**TC-I2: gate unblocks after `update_market_price` called**
Same setup as TC-I1 but call `handler.update_market_price(symbol, price)` before sending the second signal. Assert order is placed, `rejected_trades == 0` for the second signal.

**TC-I3: two consecutive bars — second bar warms cache and unblocks**
Simulate two bar ticks via `update_market_price`. After first bar (stale), gate blocks. After second bar (fresh), gate passes. Confirms the self-resolving nature of the startup cold window.

### Phase 4 — Acceptance tests (Definition of Done)

**TC-A1: EventType.PORTFOLIO_UNPRICEABLE exists and has Severity.WARNING**
```python
from core.runtime.event_journal import EventType, EventJournal
assert EventType.PORTFOLIO_UNPRICEABLE == "PORTFOLIO_UNPRICEABLE"
journal = EventJournal.__new__(EventJournal)
assert journal._get_severity(EventType.PORTFOLIO_UNPRICEABLE).name == "WARNING"
```

**TC-A2: `ExecutionConfig.max_price_age_s` defaults to `float('inf')`**
```python
import math
assert math.isinf(ExecutionConfig().max_price_age_s)
```

**TC-A3: gate is a no-op when disabled (float('inf'))**
No new rejections in any scenario when `max_price_age_s=float('inf')`.

**TC-A4: gate blocks before capital gate (ordering verification)**
Mock `_check_margin_budget` to raise an exception. Configure gate to block (stale prices). Assert the exception is NOT raised (capital gate never reached).

**TC-A5: gate uses deterministic clock, not wall clock**
Freeze `datetime.now` to a value far in the future. Confirm the gate result is driven by `clock.now()` only.

### Phase 5 — Regression tests

**TC-R1: existing handler tests pass unchanged**
Run the full `tests/execution/test_handler.py` suite. Zero failures expected (default `float('inf')` disables gate).

**TC-R2: MM9.1 capital gate still fires for MARGIN_BUDGET cases**
Warm all prices (gate passes), but configure a position that exceeds `max_capital_utilisation`. Assert capital gate blocks and `rejected_trades` increments (not freshness gate).

---

## §8 — Risks

### R1: Non-universe recovered position -> permanent trading block (CRITICAL)

**Scenario:** F&O position on `NSE_FO|NIFTY23JUN19500CE` survives into a new session. The instrument is no longer in `config.symbols`. The driver never ticks it. Its cache entry is permanently MISSING. With `max_price_age_s=600.0`, every ENTRY signal triggers `_check_book_priceable()` -> block -> `rejected_trades` increments indefinitely. The operator sees a flood of PORTFOLIO_UNPRICEABLE warnings but no new trades execute.

**Mitigation in this slice:** Default is `float('inf')` (gate disabled). This scenario is self-protecting at the default.

**Required before arming 600.0:** Startup validation that detects non-universe held positions and journals a CRITICAL event. Track as MM9.2-S3-S4 or MM9.3 prerequisite.

### R2: Intra-tick ordering staleness (LOW — bounded, threshold absorbs it)

**Scenario:** Within one `_tick()` sweep over `config.symbols`, held symbol B appears after symbol A in iteration order. When A's ENTRY signal fires, B has not yet been ticked this sweep. B's snapshot is from the previous sweep — up to one bar interval old. If `max_price_age_s` is set close to the bar interval, B appears STALE during the brief window before its own bar arrives.

**Mitigation:** The recommended operational threshold (600s) is 10x a 1-minute bar. The stale window for B is at most one bar (60s) — well below threshold. §6.2 documents the constraint `max_price_age_s >= 2 x bar_interval_seconds` explicitly.

### R3: First-sweep startup cold window (LOW — transient, self-resolving)

**Scenario:** At startup, the first sweep through `_tick()` warms symbols in iteration order. An early signal for a held position on a late-in-order symbol will observe that position as MISSING and block. The block resolves as soon as the symbol's bar is processed in the same sweep.

**Mitigation:** This is correct behaviour (the book truly cannot be priced at that moment). No bypass logic should be added. The Failure Matrix (F10) documents it as expected. It produces a brief burst of PORTFOLIO_UNPRICEABLE WARNINGs at startup with `max_price_age_s` armed — operators should expect this and not alert on isolated startup occurrences.

### R4: Journal write determinism (LOW — side-effect, post-decision)

**Scenario:** The journal's `record()` method uses wall-clock IST for the event's own `timestamp` field. This is a fire-and-forget write. If the write fails or throws, it should not affect the gate decision or `process_signal`'s return value.

**Mitigation:** The journal write must be wrapped to prevent propagation of exceptions:

```python
if self._journal:
    try:
        self._journal.record(EventType.PORTFOLIO_UNPRICEABLE, context={...})
    except Exception:
        self.logger.exception("journal write failed for PORTFOLIO_UNPRICEABLE")
```

The gate decision (return `None`) is made before the journal write. Journal wall-clock timestamps do not affect determinism.

### R5: `rejected_trades` conflation (LOW — monitoring concern)

**Scenario:** `rejected_trades` now accumulates blocks from both the freshness gate and the MM9.1 capital gate. A monitoring alert on this metric cannot distinguish between the two causes.

**Mitigation:** Operators should monitor `PORTFOLIO_UNPRICEABLE` journal events and `MARGIN_BUDGET_REJECTED` log lines separately. Adding a dedicated `fresh_gate_rejects` metric counter is a future concern — out of scope for S3-S3 but worth noting in the CHANGELOG.

### R6: MM9.4 SPAN seam compatibility (LOW — no conflict)

**Scenario:** MM9.4 will replace `MarginTracker.get_used_margin()` with a SPAN-based computation. The freshness gate runs before this projection. If the gate blocks, `get_used_margin` is never called — the SPAN seam is never reached. If the gate passes, the projection runs as before.

**Mitigation:** No action required. MM9.4 can replace the `get_used_margin` call-site without touching the freshness gate. The `MarginTracker` signature remains unchanged.

### R7: `get_all_positions()` allocation on every signal (NEGLIGIBLE)

**Scenario:** `position_tracker.get_all_positions()` returns `self._positions.copy()`. This allocates a new dict on every call to `_check_book_priceable()`, which is called on every non-EXIT signal.

**Mitigation:** None required at typical live trading frequencies (< 10 signals/minute). Do not pre-optimise.

### R8: `_check_book_priceable` must not call `get_exposure` or `get_used_margin`

**Scenario:** If GLM mistakenly implements `_check_book_priceable` by calling `MarginTracker.get_exposure()`, it will silently ignore MISSING symbols (they return 0.0 exposure) and return a number rather than a boolean, masking the defect the gate is designed to detect.

**Mitigation:** `_check_book_priceable()` must iterate `position_tracker.get_all_positions()` directly and check `_price_cache` membership and snapshot age. It must not call any `MarginTracker` method. TC-A4 (capital gate not reached when freshness blocks) verifies this ordering implicitly.

### R9: `math.isinf` import

`math` is not necessarily imported in `handler.py`. GLM must add `import math` if not present, or use `self.config.max_price_age_s == float('inf')` (which avoids the import but is less idiomatic). Either is acceptable; `math.isinf` is preferred for clarity.

### R10: Documentation drift risk after implementation

No additional doc update is required during S3-S3. The KB sync (PROJECT_STATE, CHANGELOG, MM9 plan §9) must be done immediately after the implementation commit — before moving to MM9.2-S4 or any other slice.

---

## Definition of Done

All of the following must be true before this slice is marked COMPLETE:

- [ ] `ExecutionConfig.max_price_age_s: float = float('inf')` exists in `handler.py`
- [ ] `_check_book_priceable() -> tuple[bool, set[str]]` exists in `ExecutionHandler`, returns early for `float('inf')`
- [ ] Freshness gate is inserted at the correct call-site inside `if signal.signal_type != SignalType.EXIT:`, immediately before `_check_margin_budget`
- [ ] `EventType.PORTFOLIO_UNPRICEABLE = "PORTFOLIO_UNPRICEABLE"` exists in `event_journal.py`
- [ ] `EventType.PORTFOLIO_UNPRICEABLE: Severity.WARNING` exists in `_DEFAULT_SEVERITY`
- [ ] `tests/execution/test_handler_s3_s3_gate.py` created with all TC-U, TC-S, TC-I, TC-A, TC-R tests passing (GREEN)
- [ ] All existing handler tests pass without modification
- [ ] `gate.blocks_on_stale` and `gate.passes_on_equality` are explicitly tested (TC-U5 and TC-U4)
- [ ] `gate.passes_when_disabled` is explicitly tested (TC-U2, TC-S8)
- [ ] Journal write is guarded by `if self._journal:` and exception-wrapped (R4)
- [ ] `_check_book_priceable` does not call any `MarginTracker` method (R8)
- [ ] `import math` present in `handler.py` or `float('inf')` comparison used directly
- [ ] KB sync committed (PROJECT_STATE, CHANGELOG)

---

*Spec produced for MM9.2-S3-S3. Predecessor slices (S3-S1, S3-S2) are COMPLETE. This slice is ready for implementation.*
