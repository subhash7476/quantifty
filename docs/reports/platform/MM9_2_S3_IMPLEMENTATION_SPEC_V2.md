# MM9.2-S3 — Price Availability & Exposure Freshness
## Implementation Specification v2.0

> **Supersedes:** `MM9_2_S3_IMPLEMENTATION_SPEC.md` (v1.0)
> **Changes from v1.0:** Slice resequencing (cache → feed hook → gate); PriceSnapshot replaces parallel dicts; max_price_age_s default revised; PORTFOLIO_UNPRICEABLE rationale made explicit; driver-handler coupling pre-documented.

---

## 0. Scope and Context

**Status:** MM9.1 complete (S1-S4). MM9.2-S1 (handler-owned `_latest_prices`) and MM9.2-S2 (lot_size preference, zero-price guard, cold-cache warning) complete.

**Problem statement:** `_latest_prices: Dict[str, float]` carries no timestamps and updates only on signal arrival — not on every bar. The margin gate uses this cache without checking freshness. Any held position in a symbol that has not signaled recently is priced at a stale mark; one that has never signaled since startup contributes zero to `used_margin`. This is the same C3 under-count class that MM9.2-S1 closed. Constitution Principle 5 ("No Trading On Stale Data") is enforced at the feed level by the watchdog but not at the per-symbol price level.

**v1.0 sequencing defect:** The original spec introduced the freshness gate before the per-bar price feed hook. A strategy producing signals every 20-30 minutes would have continuously blocked itself under the 10-minute default threshold, because `_latest_prices` only updates on signals. The gate's correctness depended on a later milestone that had not yet landed. v2.0 fixes this by sequencing correctly: establish the infrastructure, wire the feed hook, then activate the gate.

**v2.0 slice sequence:**

| Slice | Deliverable | Gate state |
|---|---|---|
| **S3-S1** | `PriceSnapshot` replaces parallel dicts; `update_market_price()` public method on handler | Gate does not exist |
| **S3-S2** | Per-bar feed hook: driver calls `update_market_price` on every bar | Gate does not exist |
| **S3-S3** | Fresh-book preflight gate in `process_signal`; `max_price_age_s = float('inf')` default; `EventType.PORTFOLIO_UNPRICEABLE` | Gate exists, disabled by default |
| **Follow-on** | Operator sets `max_price_age_s = 600.0` after staging validation | Gate active at 10-minute threshold |

**Why float('inf') in S3-S3, not 600.0 directly:** Even with the per-bar feed hook in place, the first live deployment of the gate should be observable before it enforces. `float('inf')` lets operators see `PORTFOLIO_UNPRICEABLE` journal events and `rejected_trades` increments in paper mode before the gate blocks anything in live mode. The 600.0 production value is set explicitly by the operator after validating no false positives in staging.

**Out of scope:**
- SPAN-based margin estimation (MM9.4 seam)
- `avg_price` seeding as a fallback (rejected in MM9.2-S1 D-S1-3; block-on-unpriceable is the principled alternative)
- Any changes to `MarginTracker` (stateless invariant preserved throughout)

---

## 1. Current Implementation Review

### 1.1 Where prices enter the system

All price entries originate in a single location:

```
handler.py:472  self._latest_prices[signal.symbol] = current_price
```

`current_price` is passed by `LoopDriver._dispatch_signals` as `bar.close` (driver.py:645). The driver sets `self._clock.set_time(bar.timestamp)` before calling `on_bar`, so `self.clock.now()` inside `process_signal` is the bar's deterministic timestamp. The cache update runs unconditionally for every signal including EXIT signals. No other code path updates `_latest_prices`.

### 1.2 Who owns the prices

`ExecutionHandler` owns `_latest_prices` exclusively. Initialised in `__init__` to an empty dict. Passed to `MarginTracker.get_used_margin()` as a caller-supplied argument.

### 1.3 Where MarginTracker reads them

`_check_margin_budget` (handler.py:951-977) calls:

```python
used_current = self.margin_tracker.get_used_margin(self._latest_prices)
```

`MarginTracker` never retains price state; it reads only what the caller supplies.

### 1.4 Timestamps

`_latest_prices` is `Dict[str, float]`. No timestamp field, no parallel dict, no age calculation. The recording time is unrecoverable from the cache alone.

### 1.5 Current stale price handling

**Cold-cache warning (MM9.2-S2):** At `__init__`, if held positions exist and `_latest_prices` is empty, a WARNING is logged. Fires once; does not block.

**RuntimeWatchdog:** Monitors aggregate feed staleness. Trips kill switch if no bar arrives for 5 minutes during market hours. Uses wall-clock `datetime.now()` — cannot be used on the trade decision path (ADR-003). Does NOT detect per-symbol staleness: if NIFTY bars flow but FINNIFTY's feed dies, the watchdog remains healthy.

---

## 2. Stale Prices Are Currently Possible

### S1 — Startup / Cold Cache

After restart, `_latest_prices = {}`. PositionTracker restores held positions (ADR-001). Until each held symbol first signals, its contribution to `used_margin` is 0 — a direct C3 regression.

### S2 — Non-Signaling Held Symbols

The cache updates only on signal arrival. A held FINNIFTY position that has not signaled in 45 minutes carries a 45-minute-old mark. **This is the root cause that S3-S2 (per-bar feed hook) eliminates.**

### S3 — Per-Symbol Market Halt or Circuit Breaker

FINNIFTY trips a circuit breaker. NIFTY and BANKNIFTY bars continue; the watchdog stays healthy. Any NIFTY entry signal during the halt uses the stale pre-halt FINNIFTY mark. **This is the scenario the watchdog cannot see. The freshness gate (S3-S3) catches it.**

### S4 — Feed Reconnect Within Watchdog Window

A 4.5-minute disconnect. Watchdog threshold not reached. Feed reconnects. Prices are 4.5 minutes old; handler resumes accepting entries with stale marks.

### S5 — Weekend / Overnight Restart

`_latest_prices = {}`. Watchdog does not fire (market closed). Held positions contribute 0.

### S6 — Partial Cache Coverage

5-symbol universe; only 2 have signaled. A new entry on a signaled symbol computes portfolio margin for the other 3 as 0. Gate approves on a partial book.

### S7 — Late or Delayed Ticks (out of scope)

Delayed `bar.timestamp`. The deterministic clock advances to the delayed time; the price reflects the most recent bar received. A data provider concern, not a cache concern. Explicitly excluded.

**Summary:** S1-S6 are genuine gaps. S2 is resolved by S3-S2 (feed hook). S1 and S3-S6 are caught by S3-S3 (gate). S7 is excluded.

---

## 3. Alternative Architectures

### Architecture A — Timestamp Validation Inside MarginTracker

**Verdict:** Rejected. Breaks `get_used_margin(Dict[str, float])` — the MM9.4 SPAN seam. Couples a stateless computational object to a clock dependency.

### Architecture B — Handler-Owned PriceSnapshot Cache (recommended)

Replace `_latest_prices: Dict[str, float]` with `_price_cache: Dict[str, PriceSnapshot]` where `PriceSnapshot` bundles `price` and `timestamp`. A new public method `update_market_price(symbol, price)` is the sole writer. A preflight method `_check_book_priceable()` gates entry signals. `MarginTracker.get_used_margin` receives a projected `Dict[str, float]` — signature unchanged.

**PriceSnapshot vs parallel dicts:** v1.0 proposed `_latest_prices` and `_price_timestamps` as parallel dicts requiring atomic paired updates. If additional metadata (bid/ask, source, latency, quality flag) is added in future, N parallel dicts become increasingly fragile. A single `PriceSnapshot` value type eliminates the synchronization concern at negligible cost.

**Design invariant:** The margin gate either confirms every held position is freshly priced and calls `get_used_margin` on the full book, or it never calls `get_used_margin` at all. Partial-book utilization is eliminated by construction.

**Verdict:** Recommended.

### Architecture C — Dedicated PriceCache Class

**Verdict:** Over-engineered for current scope. `PriceSnapshot` (a value type inside `handler.py`) is not Architecture C — it keeps dict ownership in the handler and adds no new class boundary. Architecture C becomes appropriate when a third component needs to read from the same cache.

### Architecture D — Central Runtime Freshness Service

**Verdict:** Rejected. ADR-001 and ADR-002 boundary concerns.

### Comparison Table

| Criterion | A: MT timestamps | **B: PriceSnapshot** | C: PriceCache class | D: Central svc |
|---|---|---|---|---|
| MarginTracker stays stateless | No | **Yes** | Yes | Yes |
| MM9.4 seam unchanged | No | **Yes** | Yes | Risky |
| Deterministic clock | Awkward | **Inherent** | Inherent | Requires injection |
| Parallel-dict drift risk | N/A | **None (bundled)** | None | None |
| Appropriate abstraction level | Wrong layer | **Correct** | Premature | Over-engineered |

---

## 4. PriceSnapshot Design

### 4.1 Definition

```python
@dataclass(frozen=True)
class PriceSnapshot:
    price: float
    timestamp: datetime
```

Defined at module level in `handler.py`, after imports, before `ExecutionConfig`. `frozen=True` prevents mutation after recording. No methods — pure value type.

### 4.2 Cache field

```python
self._price_cache: Dict[str, PriceSnapshot] = {}
```

Replaces both `self._latest_prices` and `self._price_timestamps`.

### 4.3 Writer: update_market_price

```python
def update_market_price(self, symbol: str, price: float) -> None:
    self._price_cache[symbol] = PriceSnapshot(price=price, timestamp=self.clock.now())
```

Public method (no underscore) because `LoopDriver` calls it from outside. No side effects beyond the cache update. No logging, no gate checks, no metrics — a pure data-feed operation. Called by:
- `process_signal` at its first line (replaces `self._latest_prices[signal.symbol] = current_price`)
- `LoopDriver._tick()` for every bar (S3-S2 addition)

### 4.4 Projection for MarginTracker

```python
prices = {sym: snap.price for sym, snap in self._price_cache.items()}
used_current = self.margin_tracker.get_used_margin(prices)
```

Replaces the existing `self.margin_tracker.get_used_margin(self._latest_prices)` in `_check_margin_budget`. MarginTracker signature unchanged.

### 4.5 Cold-cache warning update

The MM9.2-S2 cold-cache warning at `__init__` currently checks `not self._latest_prices`. After S3-S1: `not self._price_cache`.

---

## 5. Freshness Semantics

### 5.1 Definitions

**Fresh:** `_price_cache[symbol]` exists AND `self.clock.now() - _price_cache[symbol].timestamp <= timedelta(seconds=config.max_price_age_s)`.

**Stale:** Entry exists but age exceeds `max_price_age_s`.

**Missing:** No entry in `_price_cache`. Includes cold-start and symbols never seen.

**Unpriceable:** Stale or missing. Both are treated identically by the gate.

**Fully-priceable book:** All held positions have a fresh snapshot. An empty held book is vacuously fully-priceable.

**Incremental leg:** The signaling symbol's snapshot — always fresh because `update_market_price` is called at the start of `process_signal`. The stacking guard (line 560) ensures the signal's symbol has no held position, so it is never evaluated by `_check_book_priceable()`.

### 5.2 Threshold

New field on `ExecutionConfig`:

```python
max_price_age_s: float = float('inf')
# Gate disabled by default. Set to 600.0 after validating no false positives in staging.
```

**Why float('inf') is the correct initial default:** The gate is new infrastructure. Deploying it disabled allows operators to observe `PORTFOLIO_UNPRICEABLE` events in paper/staging without blocking live entries, then enable enforcement deliberately. This is not a workaround — it is a controlled rollout mechanism.

**Recommended production value: 600.0 (10 minutes).** Rationale:
- With S3-S2 in place, prices update on every bar. A 10-minute gap means 10 bars with no price update for a held symbol — indicating a genuine per-symbol feed problem, not a strategy cadence issue.
- The watchdog threshold is 5 minutes (systemic). The freshness gate at 10 minutes catches per-symbol halts the watchdog misses, with a wider window to avoid false positives.

### 5.3 Behavior when unpriceable

- Block the entry. `process_signal` returns `None`.
- Increment `metrics.rejected_trades`.
- Log WARNING: `PORTFOLIO_UNPRICEABLE symbol=<S> signal_id=<id> missing=<set> stale=<set> ages_s=<dict>`
- Journal one `EventType.PORTFOLIO_UNPRICEABLE` event (Severity.WARNING).
- `_check_margin_budget` is never reached — no partial-book utilization computed.

**Why block rather than compute on partial book:** Excluding an unpriceable symbol from `get_used_margin` sets its contribution to 0, understating `used_current`, making `utilisation` appear lower — the gate approves an entry that a full-mark calculation would reject. This is the C3 under-count defect in a different form. Blocking is the only constitution-aligned option.

### 5.4 Lifecycle phases

| Phase | Behavior |
|---|---|
| Startup with recovered positions | Per-bar feed hook warms cache within first bar cycle; gate unblocks organically |
| Startup with no held positions | Vacuously fully-priceable; gate never fires |
| Market open | S3-S2 ensures every bar updates the cache; gate stays green as long as bars flow |
| Per-symbol halt | Symbol's snapshot ages past threshold; gate blocks new entries; EXIT bypass unchanged |
| Systemic feed failure | Watchdog fires kill switch before gate sees stale prices; gate not reached |
| Backtest / replay | Deterministic clock advances with `bar.timestamp`; gate is fully deterministic and replay-identical |
| Gate disabled (float('inf')) | All rows above: gate passes vacuously; PORTFOLIO_UNPRICEABLE never emitted |

---

## 6. Runtime Behavior Matrix

All conditions apply to non-EXIT signals only. EXIT bypasses the freshness gate and margin gate unchanged from MM9.1-S3. When `max_price_age_s = float('inf')`, the gate is disabled and all blocking rows collapse to Allow.

| Condition | Allow / Block | Log level | Journal event | rejected_trades | Kill switch |
|---|---|---|---|---|---|
| All held positions fresh | Allow | — | — | No | No |
| No held positions (flat book) | Allow | — | — | No | No |
| `max_price_age_s = float('inf')` | Allow | — | — | No | No |
| One or more held positions MISSING | Block | WARNING | `PORTFOLIO_UNPRICEABLE` | +1 | No |
| One or more held positions STALE | Block | WARNING | `PORTFOLIO_UNPRICEABLE` | +1 | No |
| EXIT signal (any portfolio state) | Allow | — | — | No | No |
| Systemic feed dead (watchdog fired) | — (kill switch active; no signals arrive) | Watchdog handles | `WATCHDOG_STALE_DATA` | — | Yes (watchdog) |

**Journal event structure:**
```json
{
  "event_type": "PORTFOLIO_UNPRICEABLE",
  "severity": "WARNING",
  "source_component": "ExecutionHandler",
  "message": "Entry blocked: held book cannot be fully priced",
  "metadata": {
    "signal_symbol": "NSE_INDEX|Nifty 50",
    "signal_id": "<uuid>",
    "missing_symbols": [],
    "stale_symbols": ["NSE_FO|FINNIFTY24DEC19500CE"],
    "ages_s": {"NSE_FO|FINNIFTY24DEC19500CE": 742.3},
    "max_price_age_s": 600.0
  }
}
```

**Log rate-limiting:** Suppress duplicate WARNINGs for an unchanged stale set. Re-log when the stale set changes. Implementation mechanism is left to the implementer; flooding must be prevented.

---

## 7. Repository Impact

### 7.1 Production files

**`core/execution/handler.py`** — primary change surface across all three slices:

*S3-S1 changes:*
- Add `PriceSnapshot` frozen dataclass (after imports, before `ExecutionConfig`)
- Replace `self._latest_prices: Dict[str, float] = {}` with `self._price_cache: Dict[str, PriceSnapshot] = {}`
- Update cold-cache warning: `not self._latest_prices` → `not self._price_cache`
- Replace `self._latest_prices[signal.symbol] = current_price` (line 472) with `self.update_market_price(signal.symbol, current_price)`
- Add public method `update_market_price(self, symbol: str, price: float) -> None`
- Update `_check_margin_budget`: project `_price_cache` to `Dict[str, float]` before `get_used_margin`
- Confirm `from dataclasses import dataclass` and `from datetime import datetime, timedelta` are present

*S3-S3 changes:*
- Add `max_price_age_s: float = float('inf')` to `ExecutionConfig`
- Add private method `_check_book_priceable() -> tuple[bool, set[str]]`
- Add freshness preflight call-site in `process_signal` inside `if signal.signal_type != SignalType.EXIT:`, immediately before `_check_margin_budget`

**`core/runtime/driver.py`** — S3-S2 only:
- In `_tick()`, after `self._clock.set_time(bar.timestamp)` and before `source.on_bar(bar)`, add: `self._execution.update_market_price(symbol, bar.close)`

**`core/runtime/event_journal.py`** — S3-S3 only:
- Add `PORTFOLIO_UNPRICEABLE = "PORTFOLIO_UNPRICEABLE"` to `EventType` enum
- Add `EventType.PORTFOLIO_UNPRICEABLE: Severity.WARNING` to `_DEFAULT_SEVERITY`

**No changes to:**
- `core/execution/margin_tracker.py` — `get_used_margin(Dict[str, float])` signature unchanged
- `core/execution/watchdog.py` — feed-level monitoring unchanged
- `scripts/fno_runner.py` — `ExecutionConfig` default is backward-compatible

**Pre-implementation prerequisite (not a code change):**
- `docs/DRIVER_SPECIFICATION.md` must document the driver→handler price-feed coupling before the S3-S2 PR opens (see §8)

### 7.2 Test files

New test file per slice (see §9). No existing tests require modification through S3-S1 and S3-S2. For S3-S3, the default `float('inf')` means existing tests that do not explicitly set a finite threshold are unaffected.

### 7.3 Behavioral changes by slice

| Slice | Mode | Change |
|---|---|---|
| S3-S1 | All | None observable. PriceSnapshot is a mechanical refactor. |
| S3-S2 | Live / paper | Every bar warms the cache, not only signals. Held positions kept continuously priced. |
| S3-S3 (float('inf')) | All | PORTFOLIO_UNPRICEABLE events become visible in journal. No blocking. |
| Follow-on (600.0) | Live / paper | New entries blocked when any held symbol unpriced for >10 minutes. |
| Follow-on (600.0) | Backtest | Sparse-signal strategies may see new rejections, surfacing previously silent stale-price assumptions. |

---

## 8. Driver–Handler Coupling Pre-Documentation

**This section specifies what must be added to `docs/DRIVER_SPECIFICATION.md` before the S3-S2 PR is opened.**

The LoopDriver is described as a "neutral orchestrator" that is agnostic to execution policy. S3-S2 introduces a new call: `self._execution.update_market_price(symbol, bar.close)` inside `_tick()`. Without prior documentation, this could be misread as violating the driver's neutrality principle.

**Addition location:** The section of DRIVER_SPECIFICATION.md describing `LoopDriver._tick()` or the driver–execution interface (whichever currently specifies what the driver may call on its execution collaborator).

**Text to add:**

> **Price-feed coupling (MM9.2-S3-S2):** `LoopDriver._tick()` calls `execution.update_market_price(symbol, bar.close)` after advancing the deterministic clock and before dispatching signals. This is a data-feed operation, not a signal-dispatch or execution-policy operation. The driver remains unaware of execution logic; it passes market prices as raw data, in the same way it passes `bar.close` to `process_signal`. This coupling is minimal: one method, one scalar argument, no return value, no side effects on the driver. It does not violate the driver's neutrality principle, which prohibits the driver from making execution decisions — not from feeding data.

This note must be committed before the S3-S2 implementation PR is opened, so the coupling is documented at the point it is introduced.

---

## 9. Slice Plan

---

### Slice S3-S1 — PriceSnapshot and update_market_price

**Objective:** Replace parallel dicts with a bundled value type. Expose a public writer. No gate; no behavioral change; zero regression risk.

**Files touched:** `core/execution/handler.py`

**Pseudocode changes:**

```
# 1. New dataclass (after imports, before ExecutionConfig):
@dataclass(frozen=True)
class PriceSnapshot:
    price: float
    timestamp: datetime

# 2. __init__: replace _latest_prices
self._price_cache: Dict[str, PriceSnapshot] = {}

# 3. __init__: update cold-cache warning guard
if held > 0 and not self._price_cache:
    self.logger.warning("latest-price cache is cold; ...")

# 4. process_signal line 472:
self.update_market_price(signal.symbol, current_price)  # replaces direct dict write

# 5. New public method:
def update_market_price(self, symbol: str, price: float) -> None:
    self._price_cache[symbol] = PriceSnapshot(price=price, timestamp=self.clock.now())

# 6. _check_margin_budget: project before calling get_used_margin
prices = {sym: snap.price for sym, snap in self._price_cache.items()}
used_current = self.margin_tracker.get_used_margin(prices)
```

**Acceptance criteria:**
- `handler._price_cache[sym].price` equals the value previously in `_latest_prices[sym]`
- `handler._price_cache[sym].timestamp` equals `self.clock.now()` at time of call
- EXIT signals update the cache (unconditional — same as before)
- `_latest_prices` no longer exists anywhere in handler.py
- All existing tests pass without modification

**Regression risk:** None.

**Definition of Done:**
- [ ] `PriceSnapshot` dataclass defined in `handler.py`
- [ ] `_price_cache` replaces `_latest_prices`; no `_price_timestamps` ever introduced
- [ ] `update_market_price` exists and is called from `process_signal`
- [ ] `_check_margin_budget` projects `_price_cache` before `get_used_margin`
- [ ] Cold-cache warning guard updated
- [ ] `from dataclasses import dataclass` present
- [ ] All existing tests pass unchanged

---

### Prerequisite: DRIVER_SPECIFICATION.md update

**Before the S3-S2 PR is opened,** commit the driver-handler coupling note specified in §8 to `docs/DRIVER_SPECIFICATION.md`. This is a documentation-only commit with no production code change.

---

### Slice S3-S2 — Per-Bar Price Feed Hook

**Objective:** Wire `update_market_price` into the bar-processing loop so every symbol's price is warmed on every bar, regardless of signal activity. Eliminates scenario S2 completely.

**Files touched:** `core/runtime/driver.py`

**Prerequisite:** S3-S1 merged. DRIVER_SPECIFICATION.md updated.

**Change in `_tick()`:**

```python
# After S3-S2, inside the bar-processing loop:
bar = provider.get_bar(symbol)
if bar is not None:
    self._clock.set_time(bar.timestamp)
    self._execution.update_market_price(symbol, bar.close)  # MM9.2-S3-S2
    signals = source.on_bar(bar)
    self._dispatch_signals(signals, bar)
```

Call placed after `set_time` (deterministic clock correct for timestamp) and before `on_bar` (price warmed before any signal processing on this bar).

**On double-call idempotency:** When `source.on_bar` produces signals, `process_signal` calls `update_market_price` again with the same `bar.close` and the same clock value. The second write is identical to the first — the PriceSnapshot is overwritten with an equal value. No side effects.

**Acceptance criteria:**
- After each bar cycle for symbol S (signal or no signal), `handler._price_cache[S].price == bar.close`
- `handler._price_cache[S].timestamp == bar.timestamp` (via `self.clock.now()`)
- Price cache is updated for ALL symbols in every bar cycle, not only signaling symbols
- All existing tests pass unchanged

**Regression risk:** Low.

**Definition of Done:**
- [ ] `self._execution.update_market_price(symbol, bar.close)` in `_tick()` after `set_time`, before `on_bar`
- [ ] DRIVER_SPECIFICATION.md note is already committed
- [ ] Unit test: cache updated for symbol even when on_bar returns no signals
- [ ] Unit test: cache timestamp matches bar timestamp
- [ ] All existing tests pass unchanged

---

### Slice S3-S3 — Fresh-Book Preflight Gate

**Objective:** Block entry signals when any held position cannot be freshly priced. Gate defaults to disabled. Introduce `EventType.PORTFOLIO_UNPRICEABLE`.

**Prerequisite:** S3-S2 merged.

**Files touched:**
- `core/execution/handler.py`
- `core/runtime/event_journal.py`

**`ExecutionConfig` addition:**

```python
max_price_age_s: float = float('inf')
# Gate disabled by default. Operator sets 600.0 after staging validation.
```

**New private method `_check_book_priceable()`:**

```python
def _check_book_priceable(self) -> tuple[bool, set[str]]:
    positions = self.position_tracker.get_all_positions()
    held = {sym for sym, pos in positions.items() if pos.side != PositionSide.FLAT}

    if not held:
        return True, set()  # vacuously priceable

    if self.config.max_price_age_s == float('inf'):
        return True, set()  # gate disabled

    now = self.clock.now()
    max_age = timedelta(seconds=self.config.max_price_age_s)
    unpriceable: set[str] = set()

    for sym in held:
        snap = self._price_cache.get(sym)
        if snap is None or now - snap.timestamp > max_age:
            unpriceable.add(sym)

    return len(unpriceable) == 0, unpriceable
```

Uses `self.clock.now()` (deterministic). Never `datetime.now()`.

**Call-site in `process_signal`** — inside `if signal.signal_type != SignalType.EXIT:`, immediately before `_check_margin_budget`:

```python
# MM9.2-S3: fresh-book preflight. EXIT bypass inherited from outer if.
priceable, unpriceable = self._check_book_priceable()
if not priceable:
    self.metrics.rejected_trades += 1
    missing = {s for s in unpriceable if self._price_cache.get(s) is None}
    aged = {
        s: round((self.clock.now() - self._price_cache[s].timestamp).total_seconds(), 1)
        for s in unpriceable if self._price_cache.get(s) is not None
    }
    self.logger.warning(
        "PORTFOLIO_UNPRICEABLE symbol=%s signal_id=%s missing=%s stale=%s ages_s=%s",
        order.symbol, signal_id, sorted(missing), sorted(aged.keys()), aged,
    )
    if self._journal:
        self._journal.record(
            EventType.PORTFOLIO_UNPRICEABLE,
            "Entry blocked: held book cannot be fully priced",
            source_component="ExecutionHandler",
            metadata={
                "signal_symbol": order.symbol,
                "signal_id": str(signal_id),
                "missing_symbols": sorted(missing),
                "stale_symbols": sorted(aged.keys()),
                "ages_s": aged,
                "max_price_age_s": self.config.max_price_age_s,
            },
        )
    return None
```

**`event_journal.py` additions:**

```python
# In EventType enum, after INSTRUMENT_MASTER_STALE:
PORTFOLIO_UNPRICEABLE = "PORTFOLIO_UNPRICEABLE"

# In _DEFAULT_SEVERITY:
EventType.PORTFOLIO_UNPRICEABLE: Severity.WARNING,
```

**Acceptance criteria:**
- `max_price_age_s = float('inf')` (default): no blocking, no journal events
- Flat book: gate always passes regardless of threshold
- EXIT signal: never evaluated by gate
- `max_price_age_s = 600`, held symbol MISSING: returns `None`, `rejected_trades += 1`
- `max_price_age_s = 600`, held symbol STALE: returns `None`, `rejected_trades += 1`
- `max_price_age_s = 600`, all held fresh: proceeds to `_check_margin_budget`
- `_check_margin_budget` never called when `_check_book_priceable()` returns False
- `journal.record(EventType.PORTFOLIO_UNPRICEABLE, ...)` does not raise

**Regression risk:** Low. Default `float('inf')` means all existing tests that do not explicitly configure a finite threshold are unaffected.

**Definition of Done:**
- [ ] `max_price_age_s: float = float('inf')` in `ExecutionConfig`
- [ ] `_check_book_priceable()` implemented
- [ ] Call-site added before `_check_margin_budget`, inside EXIT bypass guard
- [ ] `EventType.PORTFOLIO_UNPRICEABLE` in enum and `_DEFAULT_SEVERITY`
- [ ] All 626+ existing tests pass

---

### Slice S3-T — Test Coverage

**File:** `tests/execution/test_handler_s3_freshness.py`

All tests use an injected `MockClock`. `max_price_age_s` is always set explicitly when testing gate enforcement; default (`float('inf')`) is tested only for the "gate disabled" case.

| Test | Setup | Assertion |
|---|---|---|
| `test_price_snapshot_recorded` | Process signal at `bar_ts` | `_price_cache[sym].price` and `.timestamp == bar_ts` |
| `test_snapshot_updated_on_exit` | EXIT signal | `_price_cache[sym].timestamp` updated |
| `test_update_market_price_idempotent` | Call twice, same values | Second write overwrites; no error |
| `test_feed_hook_updates_non_signaling_symbol` | `update_market_price` called without signal | Cache updated; gate sees fresh price |
| `test_cold_start_blocks_entry` | Held position, empty `_price_cache`, `max_price_age_s=600` | Returns `None`, `rejected_trades == 1` |
| `test_fresh_price_allows_entry` | Held position, snapshot at `clock.now()`, `max_price_age_s=600` | Proceeds past gate |
| `test_stale_price_blocks_entry` | Held position, snapshot at `T - 700s`, `max_price_age_s=600` | Returns `None`, `rejected_trades == 1` |
| `test_flat_book_passes` | No held positions, `max_price_age_s=600` | Gate does not fire |
| `test_exit_bypasses_gate` | Held position, empty cache, EXIT, `max_price_age_s=600` | Not blocked |
| `test_partial_book_blocked` | Three held, two fresh, one missing, `max_price_age_s=600` | Returns `None` |
| `test_gate_disabled_default` | Held positions, ancient snapshots, `max_price_age_s=inf` | Proceeds past gate |
| `test_journal_event_on_block` | Held position, missing, `MockJournal`, `max_price_age_s=600` | `MockJournal.record` called with `EventType.PORTFOLIO_UNPRICEABLE` |
| `test_deterministic_clock_not_wall_clock` | `MockClock` at T2; snapshot at T1; T2-T1 > threshold | Gate fires; `datetime.now()` never called |
| `test_per_symbol_halt_scenario` | Symbol A fresh, B stale (simulated halt), both held; entry on A | Block: B unpriceable |
| `test_margin_budget_not_called_on_block` | Held position, missing, `max_price_age_s=600` | `margin_tracker.get_used_margin` not called (spy) |

**Definition of Done:**
- [ ] All 15 tests exist and pass
- [ ] No test uses `datetime.now()` for time assertions
- [ ] Test count increases from 626+ to at least 641

---

## 10. PORTFOLIO_UNPRICEABLE EventType — Explicit Rationale

New event types extend the platform's long-term observability contract and should only be added when no existing type covers the semantic domain. The following shows why reuse is not appropriate:

| | `WATCHDOG_STALE_DATA` | `PORTFOLIO_UNPRICEABLE` |
|---|---|---|
| **Emitting component** | `RuntimeWatchdog` | `ExecutionHandler` |
| **Scope** | Systemic — entire data feed | Per-symbol — one or more held positions |
| **Trigger** | No bar from any symbol for 5 min (wall-clock) | Held position unpriced at gate time (deterministic clock) |
| **Default severity** | `CRITICAL` (kill switch fires simultaneously) | `WARNING` (entry blocked; exits unaffected) |
| **Operator response** | Investigate broker / market data feed | Identify halted symbol; adjust threshold or close position |
| **Monitoring rule** | Alert: all trading blocked | Alert: new entries blocked for this portfolio |

`BROKER_ERROR` covers broker communication failures. `RECONCILIATION_FAIL` covers ledger-broker divergence. Neither maps to per-symbol price-cache availability.

The closest precedent in the existing enum is `INSTRUMENT_MASTER_UNAVAILABLE` (MM4): a new event type was added when the instrument DB was unavailable at startup, because no existing type captured that domain event. `PORTFOLIO_UNPRICEABLE` follows the same reasoning — distinct source, scope, severity, and required operational response. The enum addition is two lines; the observability benefit justifies it.

---

## 11. Open Questions (Resolved)

**Q: Should stale prices be excluded from `get_used_margin` (partial-book computation) rather than blocking?**
Resolved: No. Excluding stale prices reduces `used_current`, understates `utilisation`, permits entries a full-mark calculation would reject — the C3 under-count defect in a different form. "Never compute on a partial book" is the only constitution-aligned invariant.

**Q: Should `avg_price` seed unpriced positions at startup?**
Resolved: No (reconfirms MM9.2-S1 D-S1-3). `avg_price` is an entry mark. It is not uniformly conservative. Block-on-unpriceable is the correct alternative.

**Q: Should `datetime.now()` be used for freshness checks?**
Resolved: No. The decision path uses `self.clock.now()` (deterministic bar clock, ADR-003). Wall-clock is reserved for the watchdog (process-health monitoring) and journal timestamps (section 6.5 of DRIVER_SPECIFICATION.md).

**Q: Does v2.0 resequencing eliminate the need for the float('inf') transitional default?**
Resolved: Partly. With the per-bar feed hook (S3-S2) complete before the gate (S3-S3), there are no false positives from strategy signal cadence. However, `float('inf')` is still valuable as a deployment safety valve — it lets operators observe gate behavior in paper/staging before enabling enforcement in live. It is a controlled rollout mechanism, not a workaround for a design defect.

**Q: Does `update_market_price` being called twice per bar cause issues?**
Resolved: No. When `process_signal` runs (after the driver's per-bar call), it calls `update_market_price` again with the same `bar.close` and the same clock value. The PriceSnapshot is overwritten with an equal value. Idempotent.

---

*End of MM9.2-S3 Implementation Specification v2.0*

*Architecture and planning only. No production code, no tests, no documentation edits were produced in this session.*
