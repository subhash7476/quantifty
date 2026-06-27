# MM9.2-S3 — Price Availability & Exposure Freshness: Implementation Specification

---

## 0. Scope and Context

**Status:** MM9.1 complete (S1–S4). MM9.2-S1 (handler-owned `_latest_prices`) and MM9.2-S2 (lot_size preference, zero-price guard, cold-cache warning) complete.

**This document:** Architecture-only specification for MM9.2-S3. No production code, no tests, no documentation edits are produced here.

**Problem statement:** `_latest_prices: Dict[str, float]` carries no timestamps. Any price in it may be seconds or hours old depending on when that symbol last generated a signal. The margin gate at MM9.1-S3 uses this cache without checking freshness. A position in a symbol that has not signaled recently is computed at a stale mark; a position in a symbol that has never signaled since startup contributes zero — the same C3 under-count class that MM9.2-S1 closed. Constitution Principle 5 ("No Trading On Stale Data") is currently enforced at the feed level by the watchdog but not at the per-symbol price level.

**What MM9.2-S3 specifies:**
- Timestamp tracking alongside `_latest_prices`
- Freshness semantics: what "fresh" means, what threshold governs it, what "missing" and "stale" mean
- A pre-flight "fresh-book" gate preceding `_check_margin_budget`: block a new entry when any held position cannot be freshly priced
- Journal and telemetry for the block condition
- The exact call-site location and data-structure changes in `handler.py`
- The configurable threshold in `ExecutionConfig`
- A new `EventType` in `event_journal.py`
- Test cases and DoD

**Out of scope for MM9.2-S3:**
- Per-bar price feed hook (driver calls `handler.update_market_price(sym, bar.close)` every bar, not only on signals). This is the upstream fix that reduces how often the freshness gate fires. It requires a LoopDriver change and is documented as a named follow-on — MM9.2-S4 or the first slice of MM9.3.
- SPAN-based margin estimation (MM9.4 seam)
- `avg_price` seeding as a fallback (rejected in MM9.2-S1 D-S1-3; block-on-unpriceable is the principled alternative)
- Any changes to MarginTracker (stateless invariant preserved)

---

## 1. Current Implementation Review

### 1.1 Where prices enter the system

All price entries to the cache originate in a single location:

```
handler.py:472  self._latest_prices[signal.symbol] = current_price
```

`current_price` is the parameter passed by `LoopDriver._dispatch_signals`, which calls `process_signal(signal, bar.close)` (driver.py:645). The value is always the close price of the bar whose processing triggered the signal. The driver sets `self._clock.set_time(bar.timestamp)` before calling `on_bar` for that bar (driver.py:582), so `self.clock.now()` inside `process_signal` is the bar's timestamp, not wall-clock.

The cache update at line 472 runs unconditionally for every signal including EXIT signals ("keeps the price warm for later entries," per its comment). It is the first statement in the `try` block, before any gate or idempotency check.

No other code path updates `_latest_prices`.

### 1.2 Who owns the prices

`ExecutionHandler` owns `_latest_prices` exclusively. It is an instance variable initialised in `__init__` to an empty dict. No external component reads or writes it; it is passed into `MarginTracker.get_used_margin()` as a caller-supplied argument on each gate check.

### 1.3 Where MarginTracker reads them

`_check_margin_budget` (handler.py:951-977) calls:

```python
used_current = self.margin_tracker.get_used_margin(self._latest_prices)
```

`get_used_margin` delegates to `get_exposure(current_prices)` which iterates `self.position_tracker._positions` and calls `current_prices.get(sym)` for each held symbol. `MarginTracker` never retains any price state; it reads only what the caller supplies.

### 1.4 Timestamps

`_latest_prices` is `Dict[str, float]`. There is no timestamp field, no parallel timestamp dict, no age calculation anywhere in `handler.py`. The time at which a price was recorded is irretrievable from `_latest_prices` alone.

### 1.5 Current stale price handling

There is no per-symbol freshness mechanism. Two related safeguards exist but address different scopes:

**Cold-cache warning (MM9.2-S2 D-S1-4):** At `__init__`, if `position_tracker` has held positions and `_latest_prices` is empty, a WARNING is logged. This fires once at construction time and does not block any trade.

**RuntimeWatchdog (watchdog.py):** Monitors whether any bar arrives from the feed (aggregate-level staleness). `record_bar()` is called in `_drive_watchdog()` after the symbol sweep. If `datetime.now() - _last_bar_timestamp > DATA_STALE_THRESHOLD` (5 minutes) during market hours, the watchdog calls `execution.activate_kill_switch(...)`. This detects systemic feed death. It does NOT detect per-symbol staleness: if NIFTY bars flow but FINNIFTY's feed dies, the watchdog sees healthy bars and does not fire.

**Critical gap:** The watchdog uses wall-clock `datetime.now()` — deliberately, because it is a process-health monitor for the live runner. Any freshness check on the decision path must use the deterministic clock (`self.clock.now()`) to satisfy ADR-003.

---

## 2. Stale Prices Are Currently Possible

The following scenarios all leave `_latest_prices` in a state where held positions are priced at a mark that does not reflect the present bar's market reality.

### S1 — Startup / Cold Cache (post-recovery)

After a restart, `_latest_prices = {}` and `_price_timestamps = {}` (once added). `PositionTracker` restores all held positions from the persistence store (ADR-001). Until the first signal arrives for each held symbol, the margin gate sees 0.0 for those positions. The MM9.2-S1 cold-cache warning fires once but allows trading to proceed immediately. Any new entry signal in the session can create a NormalizedOrder based on a portfolio where held positions contribute no margin — a direct regression to the C3 defect class.

### S2 — Non-Signaling Held Symbols (signal-only update design)

By MM9.2-S1 D-S1-2, the cache updates only when a signal arrives for a symbol. A held position in FINNIFTY that has not generated a signal for 45 minutes has a 45-minute-old price in the cache. An incoming NIFTY entry signal would compute portfolio margin using this stale FINNIFTY mark. The error magnitude scales with the mark-to-market drift of FINNIFTY over that interval.

### S3 — Per-Symbol Market Halt or Circuit Breaker

FINNIFTY trips a circuit breaker. Its feed goes silent. NIFTY and BANKNIFTY bars continue arriving, so the watchdog does not trip. The held FINNIFTY position's price in `_latest_prices` is the last bar before the halt. After the halt ends, the position's actual mark may differ significantly. Any NIFTY entry signal during or after the halt computes portfolio margin at the stale FINNIFTY mark. This is the scenario the watchdog explicitly cannot see — per-symbol staleness within an otherwise healthy aggregate feed.

### S4 — Feed Reconnect

A transient disconnect causes 4.5 minutes of no bars. The watchdog approaches but has not yet tripped its 5-minute threshold. The feed reconnects. Prices in `_latest_prices` are 4.5 minutes old. The watchdog does not fire (never exceeded threshold). The handler resumes accepting entries with stale marks in the margin calculation.

### S5 — Weekend / Overnight Restart

Runner starts Saturday morning or before market open. `_latest_prices = {}`. The watchdog's `check_data_staleness()` only fires during `MarketHours.is_market_open()`, so it does not trip. If the operator runs a backtest or test scenario on weekend, the price cache remains empty and all held positions price at 0.

### S6 — Partial Cache Coverage (multi-symbol universe)

Live session, 5-symbol universe. Strategy signals NIFTY and BANKNIFTY first. FINNIFTY, MIDCPNIFTY, and SENSEX50 have not yet signaled. A new NIFTY entry while all five have held positions sees only NIFTY + BANKNIFTY in the cache; the other three contribute 0 to `used_margin`. The margin gate approves based on a partial book.

### S7 — Late or Delayed Ticks (data quality)

Market data provider delivers a delayed bar (stale `bar.timestamp` relative to wall-clock). The deterministic clock advances to the delayed timestamp, and `_latest_prices` is updated with the delayed close. This is a data-quality concern, not a cache-staleness concern per se — the price in the cache reflects the most recent bar the system actually received, which is correct from a deterministic-replay standpoint. Flagged here for completeness but is **out of scope** for MM9.2-S3: the appropriate response to delayed ticks is in the data provider layer, not the execution layer.

**Summary:** S1, S2, S3, S4, S5, S6 are genuine price-availability gaps that MM9.2-S3 must address. S7 is a data provider concern and is explicitly excluded.

---

## 3. Alternative Architectures

### Architecture A — Timestamp Validation Inside MarginTracker

**Description:** Change `get_used_margin`'s signature to accept `Dict[str, Tuple[float, datetime]]`. MarginTracker checks price age internally and skips symbols whose price exceeds a freshness threshold.

**Assessment:**
- **Complexity:** Moderate. Breaks the existing call signature; any SPAN integration (MM9.4) must adapt.
- **Determinism:** MarginTracker would need access to the current time. Injecting the deterministic clock into MarginTracker couples a stateless computational object to a runtime dependency.
- **Stateless invariant:** Violated. The MM9.4 seam expects `get_used_margin(prices: Dict[str, float])`. Changing the signature now creates a SPAN compatibility constraint.
- **Maintainability:** Poor. MarginTracker becomes a freshness enforcer, blurring the boundary between exposure calculation and policy.

**Verdict:** Rejected. Violates the stateless invariant and the MM9.4 seam.

### Architecture B — Freshness Gate in ExecutionHandler (recommended)

**Description:** Handler owns a parallel `_price_timestamps: Dict[str, datetime]` populated alongside `_latest_prices`. Before calling `_check_margin_budget`, a preflight method `_check_book_priceable()` iterates all held positions, checks whether each has a fresh timestamp, and returns `(fully_priceable: bool, stale_symbols: set[str])`. If not fully priceable, the entry is blocked (same path as `MARGIN_BUDGET_REJECTED`). `MarginTracker.get_used_margin` receives `_latest_prices` unchanged — the gate either proves the book is fresh and proceeds, or never reaches the margin calculation.

**Assessment:**
- **Complexity:** Low. Two new instance variables, one new method, one new field on `ExecutionConfig`. No changes to `MarginTracker`.
- **Determinism:** Uses `self.clock.now()` (the deterministic bar clock) for both recording and age comparison. Replay-identical by construction.
- **Runtime cost:** O(P) where P = number of open positions — same order as the existing `get_used_margin` call. Called once per non-EXIT entry signal.
- **Maintainability:** High. Clear separation: handler owns freshness policy, MarginTracker owns exposure arithmetic.
- **SPAN compatibility:** `MarginTracker.get_used_margin(Dict[str, float])` is unchanged. MM9.4 seam is unaffected.

**Design invariant:** The margin gate either receives a fully-fresh price for every held position and computes utilization, or it never computes utilization at all. Partial-book utilization is eliminated by construction.

**Verdict:** Recommended.

### Architecture C — Dedicated PriceCache Abstraction

**Description:** A new `PriceCache` class wraps both `_latest_prices` and `_price_timestamps`. It exposes `update(symbol, price, timestamp)`, `get(symbol)`, `get_all_fresh(max_age_s) -> Dict[str, float]`, and `has_fresh(symbol, max_age_s) -> bool`. Handler replaces the two raw dicts with a `PriceCache` instance.

**Assessment:**
- **Complexity:** Higher. New class, new file, interface design, dependency injection for testing.
- **Determinism:** Same as B if the clock is passed correctly.
- **Runtime cost:** Same as B.
- **Maintainability:** Better abstraction, but premature for the current scope. The "cache" has a single writer and single reader within a single class.
- **SPAN compatibility:** Compatible if `PriceCache.get_all_fresh()` returns `Dict[str, float]`.

**Verdict:** Over-engineered for MM9.2-S3 scope. Appropriate if the price cache acquires additional readers (e.g., P&L tracker, Greeks engine) in a future milestone. Document as the path to take when a third reader emerges; do not implement now.

### Architecture D — Central Runtime Freshness Service

**Description:** A shared service component holds all symbol prices and their ages; ExecutionHandler, GreeksEngine, P&L tracker all read from it.

**Assessment:**
- **Complexity:** High. New component, new coupling surface, potential ADR-001 concern (another source of price truth).
- **Determinism:** Requires careful clock threading through the shared service.
- **Maintainability:** Entangles subsystems that currently have clear ownership.

**Verdict:** Rejected. ADR-001 and ADR-002 boundary concerns; over-engineered.

### Comparison Table

| Criterion | A: MT timestamps | **B: Handler gate** | C: PriceCache | D: Central svc |
|---|---|---|---|---|
| MarginTracker stays stateless | No | **Yes** | Yes | Yes |
| MM9.4 seam unchanged | No | **Yes** | Yes | Risky |
| Deterministic clock | Possible but awkward | **Inherent** | **Inherent** | Requires injection |
| Lines of new production code | ~60 | **~50** | ~100 | ~200 |
| Partial-book possible | Yes | **No (invariant)** | Yes if misused | Yes if misused |
| Appropriate abstraction level | Wrong layer | **Correct** | Premature | Over-engineered |

---

## 4. Freshness Semantics

### 4.1 Definitions

**Fresh:** A symbol's price is fresh if and only if:
1. `_price_timestamps[symbol]` exists (price has been observed at least once), AND
2. `self.clock.now() - _price_timestamps[symbol] <= timedelta(seconds=config.max_price_age_s)`

**Stale:** The price exists but condition (2) is false. Age has exceeded `max_price_age_s`.

**Missing:** `symbol` has no entry in `_price_timestamps` (equivalently, no entry in `_latest_prices`). Includes the cold-start condition for all symbols.

**Unpriceable:** A held position is unpriceable when its price is either stale or missing. From the gate's perspective, stale and missing are treated identically: the book cannot be confirmed fresh.

**Fully-priceable book:** All held positions (those with `PositionSide != FLAT` in `position_tracker`) have a fresh price. An empty held book is vacuously fully-priceable — a flat-start entry is never blocked.

**Incremental leg:** The signaling symbol's price — always fresh because line 472 updates `_latest_prices[signal.symbol]` and (after S3-S2) `_price_timestamps[signal.symbol] = self.clock.now()` before any gate runs. Additionally, the position stacking guard (line 560) ensures no held position exists on the signal's symbol for a non-EXIT entry, so the signal's symbol is never checked by `_check_book_priceable()`.

### 4.2 Threshold Configuration

New field on `ExecutionConfig`:

```
max_price_age_s: float = 600.0
```

Default: 600 seconds (10 minutes). Rationale:
- The watchdog's `DATA_STALE_THRESHOLD` is 5 minutes (systemic feed death). The per-symbol threshold is set higher to avoid false positives from brief signal gaps in active strategies while still catching genuine per-symbol halts.
- For 1-minute bars: 10 minutes = 10 consecutive bars without a signal for a held symbol before blocking. A circuit-breaker halt is detected within one session interval (30-60 minutes depending on market), and no new entries accumulate on an unpriced portfolio during that window.
- For strategies with longer signal intervals (e.g., 30-minute bars or event-driven signals with gaps longer than 10 minutes), operators must configure `max_price_age_s` to a value greater than their maximum expected signal gap. This is a deliberate trade-off: a larger threshold reduces false blocks, a smaller threshold catches per-symbol halts faster.
- `max_price_age_s = float('inf')` disables the freshness gate (all prices are always considered fresh). This is the escape hatch for strategies with very infrequent signals until the per-bar feed hook is implemented.

### 4.3 Behavior When Stale / Missing / Partially Available

**When stale or missing:**
- Block the new entry signal entirely. `process_signal` returns `None`.
- Increment `self.metrics.rejected_trades += 1`.
- Log `WARNING` with reason `PORTFOLIO_UNPRICEABLE`, including the signal symbol, the set of stale/missing held symbols, their recorded ages or "NEVER SEEN".
- Journal one `EventType.PORTFOLIO_UNPRICEABLE` event with `Severity.WARNING` and metadata `{stale_symbols: [...], ages_s: {...}}`.
- The `_check_margin_budget` call is never reached — no partial-book utilization is ever computed.

**When partially available (some symbols fresh, some not):**
- The same outcome as fully unavailable: block and log. There is no "compute on the partial book" mode. This is the core invariant.

**Rationale for blocking over computing:** Excluding a held symbol from `get_used_margin` (treating it as 0 contribution) would under-count `used_current` — exactly the C3 defect class. If a FINNIFTY short position's mark is stale (market moved up), treating it as 0 understates the margin consumed by that short, making `utilisation` appear lower than it is, potentially approving an entry that a full-mark calculation would reject. Blocking is always the conservative, constitution-aligned action.

### 4.4 Behavior During Lifecycle Phases

**Startup / cold cache:** `_latest_prices` and `_price_timestamps` are both empty. The MM9.2-S2 cold-cache WARNING fires once at `__init__`. When the first non-EXIT signal arrives, the signal's symbol gets a fresh timestamp. Any held positions in other symbols remain unpriceable → `_check_book_priceable()` returns `False` → entry blocked. Blocking continues until the first signal for each held symbol warms its cache entry. This closes the R2 gap identified in MM9.2-S1: rather than allowing trades on an unpriced portfolio, the system refuses until all held marks are confirmed.

**Backtest / replay:** The deterministic clock advances with `bar.timestamp`. `_price_timestamps` records the bar time. Age comparisons use bar times. A 90-day backtest with 1-minute bars will never produce a stale price for a symbol that signals every bar. If the strategy signals infrequently (e.g., every 30 minutes), stale detection fires correctly for the backtest cadence. Replay is fully deterministic: the same sequence of signals produces the same freshness outcomes.

**Market open (first bars):** First bars arrive, clock advances. Strategies may emit entry signals immediately. If there are held positions from the prior session (recovered positions, live-only), `_check_book_priceable()` blocks until those symbols' first bars arrive and produce signals. If the held symbol is in the active universe, its bar will be processed within the first bar cycle. If it is not (e.g., expired instrument), it will never price — a permanent block for new entries on that portfolio until the stale position is closed. This is correct behavior: an expired-instrument position should be closed before new entries proceed.

**Market close / overnight:** The last bar of the session prices all symbols. The clock stops advancing. On the next startup, `max_price_age_s` comparison will find all prices from the prior session stale (potentially 18+ hours ago). This is handled by the startup/cold-cache path above.

---

## 5. Runtime Behavior Matrix

The following matrix specifies the exact disposition for each condition. "Allow" means `process_signal` proceeds past the freshness check. "Block" means `process_signal` returns `None` at the freshness preflight. All conditions apply only to non-EXIT signals (EXIT bypasses all margin gates, unchanged from MM9.1-S3).

| Condition | Allow / Block | Log (level) | Journal event | metrics.rejected_trades | Kill switch | Notes |
|---|---|---|---|---|---|---|
| All held positions have fresh prices | Allow | None | None | No | No | Happy path. Gate passes through, `_check_margin_budget` runs normally. |
| No held positions (flat book) | Allow | None | None | No | No | Vacuously fully-priceable. |
| One or more held positions MISSING (never seen) | Block | WARNING: `PORTFOLIO_UNPRICEABLE symbol=<S> missing=<set>` | `PORTFOLIO_UNPRICEABLE` (WARNING) | +1 | No | Includes cold-start case. |
| One or more held positions STALE (age > threshold) | Block | WARNING: `PORTFOLIO_UNPRICEABLE symbol=<S> stale=<set> ages_s=<dict>` | `PORTFOLIO_UNPRICEABLE` (WARNING) | +1 | No | Includes per-symbol halt case. |
| Cold-start with no held positions | Allow | None (cold-cache warning already fired at `__init__`) | None | No | No | Flat book, vacuously priceable. Entry proceeds. |
| Systemic feed staleness (watchdog fires) | Kill switch already activated | Watchdog logs independently | `WATCHDOG_STALE_DATA` (CRITICAL) | (no new signals reach gate) | Yes (watchdog) | Watchdog fires first. Freshness gate never reached. |
| `max_price_age_s = float('inf')` (disabled) | Allow | None | None | No | No | Operator opted out of per-symbol freshness. All prices permanently fresh. |
| EXIT signal on any portfolio state | Allow | None | None | No | No | EXIT bypasses freshness gate and margin gate (unchanged from MM9.1-S3). |
| Entry signal for signaling symbol while held positions unpriced | Block | WARNING: `PORTFOLIO_UNPRICEABLE` | `PORTFOLIO_UNPRICEABLE` | +1 | No | Signal's own symbol is always fresh (line 472 ran). Block is for held positions only. |

**Journal event specification (`PORTFOLIO_UNPRICEABLE`):**
```json
{
  "event_type": "PORTFOLIO_UNPRICEABLE",
  "severity": "WARNING",
  "source_component": "ExecutionHandler",
  "message": "Entry blocked: held book cannot be fully priced",
  "metadata": {
    "signal_symbol": "NSE_INDEX|Nifty 50",
    "signal_id": "<uuid>",
    "stale_symbols": ["NSE_FO|FINNIFTY..."],
    "missing_symbols": [],
    "ages_s": {"NSE_FO|FINNIFTY...": 742.3},
    "max_price_age_s": 600.0
  }
}
```

**Rate-limiting on WARNING logs:** The same `stale_symbols` set logging repeatedly across consecutive bars would flood logs during a prolonged halt. The implementation should track the last-logged stale set and suppress identical consecutive WARNINGs, re-logging only when the stale set changes (a new symbol becomes stale or a previously stale symbol becomes fresh). This is an implementation note — the spec does not mandate a specific de-duplication mechanism, but the implementer must prevent log flooding.

---

## 6. Repository Impact

### 6.1 Production Files

**`core/execution/handler.py`** — primary change surface:
- `__init__`: Add `self._price_timestamps: Dict[str, datetime] = {}` alongside `_latest_prices`.
- `process_signal` line 472: Add `self._price_timestamps[signal.symbol] = self.clock.now()` immediately after the existing `self._latest_prices[signal.symbol] = current_price`.
- New private method `_check_book_priceable() -> tuple[bool, set[str]]` (see §7 for full pseudocode).
- `process_signal` lines 681-694 (margin gate block): Add freshness preflight call to `_check_book_priceable()` inside `if signal.signal_type != SignalType.EXIT:`, before the `_check_margin_budget` call. Block path mirrors the existing `MARGIN_BUDGET_REJECTED` pattern: increment `rejected_trades`, log WARNING, return `None`.
- Import: ensure `datetime` and `timedelta` are available via `from datetime import datetime, timedelta`.

**`core/execution/handler.py` — `ExecutionConfig` dataclass** (line 68):
- Add field: `max_price_age_s: float = 600.0`

**`core/runtime/event_journal.py`** — one addition:
- Add to `EventType` enum: `PORTFOLIO_UNPRICEABLE = "PORTFOLIO_UNPRICEABLE"`
- Add to `_DEFAULT_SEVERITY` dict: `EventType.PORTFOLIO_UNPRICEABLE: Severity.WARNING`

**No changes to:**
- `core/execution/margin_tracker.py` — stateless invariant preserved; `get_used_margin(Dict[str, float])` signature unchanged.
- `core/runtime/driver.py` — LoopDriver is unaware of per-symbol freshness; remains unchanged.
- `core/execution/watchdog.py` — feed-level staleness monitoring unchanged; no new coupling.
- `scripts/fno_runner.py` — `ExecutionConfig` default is backward-compatible; no runner change needed.

### 6.2 Test Files

New test file: `tests/execution/test_handler_s3_freshness.py` (specified in §7.3).

Existing tests that must continue to pass without modification:
- `tests/execution/test_margin_tracker.py` — MarginTracker interface unchanged.
- `tests/execution/test_handler_margin_gate.py` — MM9.1-S3 tests; warm-cache paths are unaffected.
- `tests/execution/test_handler_s2_exposure.py` (if separate) — MM9.2-S2 tests; price cache update path is augmented, not replaced.

Regression check: Any existing test that calls `process_signal` with a non-EXIT signal while `position_tracker` has held positions and `_latest_prices`/`_price_timestamps` are empty will now return `None` (blocked by freshness gate) instead of proceeding. Tests that inject held positions must either:
1. Pre-warm the price cache by calling `process_signal` with a bar for each held symbol first, OR
2. Configure `ExecutionConfig(max_price_age_s=float('inf'))` to disable the gate in that test.

### 6.3 Documentation

No changes to `docs/` during implementation. `docs/PROJECT_STATE.md` and `docs/CHANGELOG.md` are updated after implementation is complete and tests pass (KB sync discipline).

### 6.4 Expected Behavioral Changes

**Live / paper mode:**
1. At startup with recovered positions, all new entry signals are blocked until each held position's symbol emits its first bar signal and warms the cache. Previously, entries were allowed immediately with under-counted margin.
2. During a per-symbol market halt (circuit breaker), new entries are blocked after `max_price_age_s` elapses without a price update for the halted symbol's position. Previously, entries proceeded with the stale pre-halt mark.
3. Operators with slow / event-driven strategies must configure `max_price_age_s` appropriately to avoid false blocks.

**Backtest mode:**
- For strategies that signal every bar cycle for each held symbol, behavior is unchanged — prices are fresh on every signal.
- For strategies with sparse signals, the freshness gate may produce additional `PORTFOLIO_UNPRICEABLE` rejections during periods where a held symbol has not re-signaled within `max_price_age_s`.

**Metrics:** `metrics.rejected_trades` now includes freshness-gate rejections in addition to margin-budget rejections.

---

## 7. Slice Plan

The implementation splits into two minimal production slices plus one test slice. S3-S2 depends on S3-S1 being merged first.

---

### Slice S3-S1 — Price Timestamp Tracking

**Objective:** Record when each price was last observed. No gate behavior change. Adds visibility with zero risk.

**Files touched:**
- `core/execution/handler.py` (two edits)

**Changes:**

1. In `__init__` (after `self._latest_prices: Dict[str, float] = {}`):
   ```
   Add: self._price_timestamps: Dict[str, datetime] = {}
   ```
   Confirm `from datetime import datetime` is present at the top of the file.

2. In `process_signal`, immediately after line 472 (`self._latest_prices[signal.symbol] = current_price`):
   ```
   Add: self._price_timestamps[signal.symbol] = self.clock.now()
   ```
   Uses the deterministic clock. `self.clock.now()` returns the bar's timestamp (the value set by `_clock.set_time(bar.timestamp)` in the driver before `process_signal` is called).

**Acceptance criteria:**
- After a signal is processed for symbol S, `handler._price_timestamps[S]` equals the bar's deterministic timestamp (not wall-clock).
- Processing a signal for S updates both `_latest_prices[S]` and `_price_timestamps[S]` in the same call.
- An EXIT signal updates the timestamp (same as price — keeps the mark warm).
- No existing test failures.

**Regression risk:** None. `_price_timestamps` is not read by any existing code path until S3-S2.

**Definition of Done:**
- [ ] `_price_timestamps: Dict[str, datetime] = {}` in `__init__`
- [ ] `_price_timestamps[signal.symbol] = self.clock.now()` at line 473 (after price update)
- [ ] `datetime` import confirmed present
- [ ] Unit test verifying timestamp is set and equals bar timestamp
- [ ] All existing tests pass unchanged

---

### Slice S3-S2 — Fresh-Book Preflight Gate

**Objective:** Block new entry signals when any held position cannot be freshly priced. Closes the per-symbol staleness gap and closes the MM9.2-S1 R2 cold-start gap structurally.

**Prerequisites:** S3-S1 merged.

**Files touched:**
- `core/execution/handler.py` (three edits: new field on `ExecutionConfig`, new private method, call-site in `process_signal`)
- `core/runtime/event_journal.py` (two additions: EventType and default severity)

**Changes in `ExecutionConfig` (handler.py line 85-86 area):**
```
Add after max_capital_utilisation:
    max_price_age_s: float = 600.0
```

**New private method `_check_book_priceable()`** in `ExecutionHandler`:

```
Signature: def _check_book_priceable(self) -> tuple[bool, set[str]]:

Logic:
  positions = self.position_tracker.get_all_positions()
  held_symbols = {sym for sym, pos in positions.items() if pos.side != PositionSide.FLAT}

  if not held_symbols:
      return True, set()  # vacuously fully-priceable

  if self.config.max_price_age_s == float('inf'):
      return True, set()  # gate disabled

  now = self.clock.now()
  max_age = timedelta(seconds=self.config.max_price_age_s)
  unpriceable: set[str] = set()

  for sym in held_symbols:
      ts = self._price_timestamps.get(sym)
      if ts is None:
          unpriceable.add(sym)  # MISSING — never seen
      elif now - ts > max_age:
          unpriceable.add(sym)  # STALE — age exceeded threshold

  return len(unpriceable) == 0, unpriceable
```

Notes:
- Uses `self.clock.now()` (deterministic). Does NOT use `datetime.now()`.
- `PositionSide.FLAT` import is already present in `handler.py`.
- `timedelta` import: add to `from datetime import datetime, timedelta`.
- `get_all_positions()` is the existing `PositionTracker` method that returns `Dict[str, Position]`.

**Call-site in `process_signal`** — insert immediately before the existing margin gate block (lines 681-694):

```python
# MM9.2-S3: fresh-book preflight — block entry when any held position is unpriced.
# EXIT bypasses: the outer guard (signal.signal_type != SignalType.EXIT) already applies.
priceable, stale_symbols = self._check_book_priceable()
if not priceable:
    self.metrics.rejected_trades += 1
    missing = {s for s in stale_symbols if s not in self._price_timestamps}
    aged = {s: round((self.clock.now() - self._price_timestamps[s]).total_seconds(), 1)
            for s in stale_symbols if s in self._price_timestamps}
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

This block is placed inside the existing `if signal.signal_type != SignalType.EXIT:` guard, immediately before the `_check_margin_budget` call. The EXIT bypass is inherited from the outer `if` — no new conditional needed.

**Changes to `event_journal.py`:**

In `EventType` enum, add after `INSTRUMENT_MASTER_STALE`:
```python
PORTFOLIO_UNPRICEABLE = "PORTFOLIO_UNPRICEABLE"
```

In `_DEFAULT_SEVERITY` dict, add:
```python
EventType.PORTFOLIO_UNPRICEABLE: Severity.WARNING,
```

**Acceptance criteria:**
- An entry signal arriving while held positions have no timestamp (cold start) returns `None` and increments `rejected_trades`.
- An entry signal arriving while a held position's price is older than `max_price_age_s` returns `None`.
- An entry signal arriving when all held positions have fresh timestamps proceeds to `_check_margin_budget` as before.
- A flat book (no held positions) never triggers the gate.
- An EXIT signal is never blocked by the gate.
- `EventType.PORTFOLIO_UNPRICEABLE` is a valid `EventType`; `journal.record(EventType.PORTFOLIO_UNPRICEABLE, ...)` does not raise.
- `max_price_age_s = float('inf')` on `ExecutionConfig` disables the gate: signals proceed even with arbitrarily old timestamps.
- The `_check_margin_budget` method is never called when `_check_book_priceable()` returns False.

**Regression risk:** Medium. Tests that inject held positions and process an entry signal without warming the price cache will now return `None`. Resolution: warm the cache first or set `max_price_age_s=float('inf')` for tests not exercising freshness behavior.

**Definition of Done:**
- [ ] `max_price_age_s: float = 600.0` field in `ExecutionConfig`
- [ ] `_check_book_priceable()` method implemented
- [ ] Freshness preflight call-site inserted at correct position in `process_signal`
- [ ] `EventType.PORTFOLIO_UNPRICEABLE` added to enum and `_DEFAULT_SEVERITY`
- [ ] Unit test: cold-start blocking
- [ ] Unit test: per-symbol staleness blocking
- [ ] Unit test: flat-book vacuous pass
- [ ] Unit test: EXIT bypass
- [ ] Unit test: `max_price_age_s=inf` disables gate
- [ ] Unit test: `journal.record(EventType.PORTFOLIO_UNPRICEABLE, ...)` succeeds
- [ ] All 626 existing tests pass (or are updated to warm cache / set `max_price_age_s=inf`)

---

### Slice S3-T — Test Coverage

**Objective:** Dedicated test module for MM9.2-S3 behaviour.

**File:** `tests/execution/test_handler_s3_freshness.py`

**Test cases (implementer writes to these contracts):**

| Test | Setup | Assertion |
|---|---|---|
| `test_timestamp_recorded_on_signal` | Fresh handler, process signal at `bar_ts` | `_price_timestamps[sym] == bar_ts` |
| `test_timestamp_updated_on_exit_signal` | Held position, process EXIT | `_price_timestamps[sym]` updated to EXIT bar's timestamp |
| `test_cold_start_blocks_entry` | Held position, `_price_timestamps = {}` | `process_signal` returns `None`, `rejected_trades == 1` |
| `test_fresh_price_allows_entry` | Held position, `_price_timestamps[held_sym]` set to `clock.now()` | `process_signal` proceeds past freshness gate |
| `test_stale_price_blocks_entry` | Held position, timestamp set to `clock.now() - timedelta(seconds=700)`, `max_price_age_s=600` | Returns `None`, `rejected_trades == 1` |
| `test_flat_book_allows_entry` | No held positions | `process_signal` not blocked by freshness gate |
| `test_exit_bypasses_gate` | Held position with missing timestamp, EXIT signal | Not blocked; EXIT proceeds |
| `test_partial_book_blocked` | Three held positions, two fresh, one missing | Returns `None` |
| `test_max_price_age_inf_disables_gate` | Held positions with old timestamps, `max_price_age_s=inf` | `process_signal` proceeds |
| `test_journal_event_on_block` | Held position, cold cache, `MockJournal` injected | `MockJournal.record` called with `EventType.PORTFOLIO_UNPRICEABLE` |
| `test_deterministic_clock_used` | Advance `MockClock` to T2; price recorded at T1; T2-T1 > threshold | Gate fires at deterministic time, not wall-clock |
| `test_per_symbol_halt_scenario` | Two symbols A (fresh) and B (stale), both held; entry signal on A | Block: B is a held position with stale price |

**Acceptance criteria:**
- All 12+ tests pass.
- No test uses `datetime.now()` for time assertions — all time assertions use the injected `MockClock`.
- `max_price_age_s` is always set explicitly in freshness-related tests to avoid reliance on the default.

**Definition of Done:**
- [ ] `test_handler_s3_freshness.py` exists with all tests above
- [ ] All tests green
- [ ] Test file uses `MockClock` for deterministic time control
- [ ] Total test count increases from 626 to at least 638

---

## 8. Known Limitation: Signal-Only Price Feed

The `_latest_prices` cache updates only on signal arrival (D-S1-2 from MM9.2-S1 spec). A held symbol that does not generate a signal for longer than `max_price_age_s` will be classified as stale, and new entries will be blocked until it signals again or until the operator sets `max_price_age_s=float('inf')`.

**The correct upstream fix** is a per-bar price feed hook: `LoopDriver._dispatch_signals` calls `handler.update_market_price(symbol, bar.close)` for every bar in every symbol sweep, not only when signals are dispatched. This ensures `_price_timestamps[symbol]` advances with bar time regardless of signal activity. This is a LoopDriver change (driver.py, likely 5-10 lines) that falls outside MM9.2-S3 scope:
1. It requires a new public method on `ExecutionHandler`
2. It is a driver-execution coupling change (the driver currently knows nothing about the price cache)
3. It makes the freshness gate precise rather than conservative — a meaningful behavioral change that warrants its own slice and test suite

This fix is designated **MM9.2-S4 / per-bar price feed hook**. Until it is implemented, the operator's configuration lever is `max_price_age_s`.

---

## 9. Open Questions (Resolved)

**Q: Should stale prices be excluded from `get_used_margin` (partial-book computation) rather than blocking entirely?**
Resolved: No. Excluding stale prices from the dict reduces `used_current`, making the utilization figure appear lower and the gate more permissive — the same C3 under-count defect. The design invariant ("never compute utilization on a partial book") is the only constitution-aligned option.

**Q: Should `avg_price` be used as a fallback for unpriced held positions?**
Resolved: No (reconfirms MM9.2-S1 D-S1-3). `avg_price` is an entry mark, not a current mark. Block-on-unpriceable is the correct alternative.

**Q: Should the gate use `datetime.now()` (wall-clock) for freshness checks?**
Resolved: No. The decision path must use `self.clock.now()` (deterministic bar clock) per ADR-003. Wall-clock is reserved for process-health monitoring (watchdog) and journal timestamps. Using `datetime.now()` inside `_check_book_priceable()` would make the gate non-deterministic and non-replayable.

**Q: Is `EventType.PORTFOLIO_UNPRICEABLE` the right journal event type, or should it use an existing type?**
Resolved: New type. `WATCHDOG_STALE_DATA` is a systemic feed-level event. `RECONCILIATION_FAIL` is for broker-ledger divergence. No existing type captures per-symbol price unavailability at the execution layer. Adding `PORTFOLIO_UNPRICEABLE` follows the existing pattern (MM4: `INSTRUMENT_MASTER_UNAVAILABLE`).

---

*End of MM9.2-S3 Implementation Specification*

*Architecture and planning only. No production code, no tests, no documentation edits were produced during this session.*
