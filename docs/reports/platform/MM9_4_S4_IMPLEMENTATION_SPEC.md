# MM9.4-S4 Implementation Specification
## Composition Swap & Buying-Power Integration — SPAN Becomes the Active Margin Engine

**Status:** PENDING IMPLEMENTATION
**Preceded by:** MM9.4-S1 — `MarginCalculator` Protocol & SPAN Seam (COMPLETE, ADR-007) · MM9.4-S2 — SPAN Parameter Sourcing (COMPLETE) · MM9.4-S3 — `SpanMarginCalculator`, first concrete `MarginCalculator` (COMPLETE)
**Followed by:** Closes MM9.4. Spread/NOV credits and protocol-v2 formalisation are later (MM9.5 / MM10).
**Test baseline:** 791 passing (must remain green)
**Date drafted:** 2026-06-28
**Type:** Architecture + specification only. **No production code. No patches. No commits.**

---

## 0. Reading Guide — What S4 Ships vs What S4 Does NOT

S4 is the **composition** slice. S1 built the seam, S2 built the immutable data, S3 built the
computation. **Everything needed to compute SPAN margin already exists and is tested.** S4 introduces
**zero new business logic.** It does exactly four mechanical things:

1. **Inject** the margin calculator into `ExecutionHandler` instead of hard-constructing it (DI).
2. **Construct** `SpanMarginCalculator` at the composition root (`build_runner`) from an already-loaded,
   already-validated `SpanSnapshot`, and inject it for the F&O path.
3. **Re-source** the gate's two margin terms — *used margin* (already protocol-sourced) and *required
   margin* (the proposed-order term) — so both come from the **same** SPAN calculator.
4. **Wire** the SPAN startup-readiness gate into the driver, mirroring the existing master-readiness gate.

| Scope | Content |
|---|---|
| **S4 CODE scope** | (a) `ExecutionHandler.__init__` gains an optional injected `span_snapshot`, defaulting to today's `MarginTracker`. (b) `_check_margin_budget` sources the *required-margin* term from the calculator's `get_incremental_margin` when the injected calculator provides it, else the existing flat path. (c) `build_runner` loads the snapshot, constructs `SpanMarginCalculator`, injects it, and builds the SPAN readiness checker. (d) `LoopDriver` gains a `span_readiness` checker + a `_check_span_readiness` gate mirroring `_check_master_readiness`. |
| **S4 DOCUMENT scope** | The exact composition wiring, the buying-power formulas after the swap, the gate-mechanism decision (how an off-protocol method is reached without growing the protocol), the startup ordering, and the rollback path. **Every decision is made here so the implementer makes none.** |

**The S4 deliverable, in one sentence:** at the F&O composition root, load the validated `SpanSnapshot`,
build `SpanMarginCalculator`, inject it as `ExecutionHandler`'s `MarginCalculator`, re-source the gate's
required-margin term to SPAN, and gate startup on SPAN readiness — so margin numbers become SPAN-sourced
while gate ordering, kill switch, logging, telemetry, and replay determinism are byte-for-byte unchanged.

---

## 0.1 As-Built Anchors — READ BEFORE CODING (load-bearing)

S4 wires **already-shipped** code. The authoritative surfaces (verified against the current tree):

```python
# core/risk/span/span_calculator.py  (S3, as built)
class SpanMarginCalculator:
    def __init__(self, position_tracker, span_snapshot, margin_rate: float = 1.0): ...
    margin_rate: float
    def get_exposure(self, current_prices, symbol=None) -> float: ...          # protocol v1
    def get_used_margin(self, current_prices) -> float: ...                    # protocol v1
    def get_incremental_margin(self, symbol, quantity, price, lot_size=1.0) -> float:  # off-protocol
    # raises MissingRiskArray / MissingRiskMetric on lookup faults

# core/execution/margin_tracker.py  (incumbent)
class MarginTracker:
    def __init__(self, position_tracker, margin_rate: float = 0.2): ...
    margin_rate = 0.2                                                          # protocol v1
    # get_exposure / get_used_margin only — NO get_incremental_margin

# core/risk/margin_calculator.py  (protocol v1 — NOT changed by S4)
class MarginCalculator(Protocol):
    margin_rate: float
    def get_exposure(self, current_prices, symbol=None) -> float: ...
    def get_used_margin(self, current_prices) -> float: ...

# core/risk/span/span_repository.py
class SpanRepository:
    def __init__(self, data_dir: Path = SPAN_DATA_DIR): ...
    def latest_version(self) -> Optional[date]: ...
    def load(self, version: date) -> SpanSnapshot:   # raises FileNotFoundError / ValueError

# core/risk/span/span_readiness.py
def build_span_readiness(repository) -> Callable[[], SpanReadinessVerdict]: ...
# SpanReadinessVerdict.state ∈ {ReadinessState.FRESH, ReadinessState.BLOCK}
```

**Three facts that drive every decision below:**

1. `MarginTracker.margin_rate == 0.2` but `SpanMarginCalculator.margin_rate == 1.0`. The gate's
   incremental term multiplies by `margin_rate` (`handler.py:1163`). A naïve object-only swap therefore
   silently changes that term **and** leaves it model-inconsistent with `get_used_margin` (§3.2). This is
   why the required-margin term must be re-sourced, not merely re-pointed.
2. `_estimate_required_margin(quantity, price)` returns **raw notional** `quantity * price`
   (`handler.py:1094-1097`) and carries the author's own seam comment: *"Future MM9.x: replace with
   broker/SPAN margin engine."* That comment marks the exact wiring point S4 fulfils — making this
   **margin-source replacement** (in-scope), not execution redesign (non-goal).
3. `get_incremental_margin` is **not** on `MarginCalculator` and `MarginTracker` does **not** have it.
   S4 reaches it **without** growing the protocol (§3.3, Design Q2).

---

## 1. Architectural Objectives

### 1.1 Why this slice contains no new business logic

Every formula S4 uses already exists and is unit-tested in S3: scan-risk lookup, the
`max(scan_risk, short_option_minimum)` reduction, per-position margin, exposure, and the proposed-order
incremental. The admission **policy** — the utilisation ratio and the `<= max_capital_utilisation`
threshold (`handler.py:1165-1166`) — is unchanged. S4 only changes **which object supplies the numbers**
and **where it is constructed**. There is no new computation, no new gate, no new threshold, no new
formula. The slice is pure wiring: dependency injection + source substitution + a readiness-gate call
that reuses an existing contract.

### 1.2 Responsibilities

| Concern | Owner after S4 | Changed by S4? |
|---|---|---|
| Compute SPAN margin (used / exposure / incremental) | `SpanMarginCalculator` (S3) | No — consumed, not modified |
| Decide admission (utilisation ≤ threshold; reject) | `ExecutionHandler._check_margin_budget` | **Policy unchanged**; required-margin *source* re-pointed |
| Hold the live book (positions) | `PositionTracker` (ADR-001 truth) | No |
| Load + validate the SPAN snapshot | `SpanRepository` (S2) | No — called at the root |
| Decide whether SPAN is fresh enough to start | `span_readiness.build_span_readiness` (S2) | No — wired into the driver gate |
| Construct + inject the calculator | `build_runner` (composition root) | **Yes — the swap lives here** |
| Project margin into telemetry | `PortfolioView` (reads `margin_tracker`) | No — automatically reads the injected instance |

### 1.3 Ownership & lifecycle

```
(startup, once)  build_runner:
                   repo = SpanRepository(data_dir)
                   span_readiness = build_span_readiness(repo)            # checker → driver gate
                   snapshot = repo.load(repo.latest_version())            # validated immutable DTO
                   handler = ExecutionHandler(..., span_snapshot=snapshot)# builds SpanMarginCalculator
(startup gate)   driver.startup(): _check_master_readiness → _check_span_readiness → reconcile
(session)        snapshot frozen for the whole session; gate reads SPAN numbers each signal
(shutdown)       calculator discarded; next session loads a fresh snapshot
```

The injected `SpanMarginCalculator` is owned by the `ExecutionHandler` (held as `self.margin_tracker`,
typed `MarginCalculator`). Both `PortfolioView` instances (the handler-local one at `handler.py:212-217`
and the driver's at `fno_runner.py:189-194`) receive **the same instance** because both read
`execution.margin_tracker` — so telemetry and the risk gate observe one calculator (ADR-001: one source).

### 1.4 Dependency injection

S4's DI move is the standard "default to incumbent, inject the replacement". `ExecutionHandler` gains one
optional parameter and constructs the calculator at its single existing site:

```python
# ExecutionHandler.__init__  — new optional parameter
span_snapshot: Optional[SpanSnapshot] = None
...
# handler.py:196
self.margin_tracker: MarginCalculator = (
    SpanMarginCalculator(self.position_tracker, span_snapshot)
    if span_snapshot is not None
    else MarginTracker(self.position_tracker)
)
```

When no snapshot is injected (every existing test, every backtest, equity-only LIVE), the handler
constructs `MarginTracker` exactly as today (`handler.py:196`) — **zero behaviour change, zero test
churn.** The F&O composition root injects the snapshot. This is the same seam pattern the codebase already
uses for `risk_manager`, `config`, `journal`, etc.

### 1.5 Composition-root changes (summary; detail in §2)

- `ExecutionHandler.__init__`: add `span_snapshot` param; line 196 becomes the presence-checked swap.
- `build_runner`: construct repo + readiness checker + snapshot + inject; pass the readiness checker to the
  driver. **F&O path only** (equity-only LIVE / paper keep `MarginTracker`).
- `LoopDriver`: accept `span_readiness`; add `_check_span_readiness()` mirroring `_check_master_readiness`.

---

## 2. Composition Root

### 2.1 Where the snapshot is loaded, the repository constructed, the calculator instantiated

All of it lives in **`scripts/fno_runner.py :: build_runner`**, inside the existing derivatives branch
(the same branch that already builds `master_readiness`, `fno_runner.py:135-145`). The composition root
already owns "semantic refusals at startup" (`fno_runner.py:106-145`); SPAN construction joins that block.

```
build_runner(...):
  derivatives = has_derivatives(symbols)            # existing, fno_runner.py:135
  if derivatives:
      # ... existing master_readiness construction ...

      # --- NEW: SPAN parameter sourcing (S4) -------------------------------
      span_repo       = SpanRepository(span_data_dir)            # default data/span
      span_readiness  = build_span_readiness(span_repo)          # → driver startup gate
      span_version    = span_repo.latest_version()               # None ⇒ refuse (below)
      if span_version is None:
          raise ValueError("fno_runner: F&O universe requires a SPAN snapshot; archive empty")
      span_snapshot   = span_repo.load(span_version)             # validated immutable DTO (may raise)
      # ---------------------------------------------------------------------

  # ... existing handler_kwargs construction (fno_runner.py:173-180) ...
  if derivatives:
      handler_kwargs["span_snapshot"] = span_snapshot            # the SPAN swap is this one kwarg
  execution = ExecutionHandler(**handler_kwargs)
  ...
  return LoopDriver(..., master_readiness=master_readiness, span_readiness=span_readiness, ...)
```

### 2.2 Why inject the snapshot (not a constructed calculator) — Decision A

`SpanMarginCalculator(position_tracker, snapshot)` needs the **handler's** `PositionTracker`, which only
exists after the handler is constructed. Two options:

- **(A) Inject the `SpanSnapshot`; the handler builds the calculator (CHOSEN).** The handler constructs
  `SpanMarginCalculator(self.position_tracker, span_snapshot)` at the single existing site (`handler.py:196`)
  in place of `MarginTracker`. The handler owns its tracker, so the construction is local and one line.
  The handler-local `PortfolioView` (`handler.py:215`) and the driver's `PortfolioView`
  (`fno_runner.py:192`) then both observe the same SPAN instance with **zero post-construction
  re-assignment**. *Trade-off:* `ExecutionHandler` imports `SpanMarginCalculator` — acceptable, it already
  imports `MarginTracker` and `MarginCalculator`.
- **(B) Construct the calculator after the handler, then assign `execution.margin_tracker = ...`.**
  **Rejected:** the handler-local `PortfolioView` was already built around the old tracker; re-assigning
  afterwards leaves that view pointing at a stale instance — two sources of margin truth (violates §1.3 /
  ADR-001).

> **Naming note:** `self.margin_tracker` keeps its name (every consumer reads it). It is typed
> `MarginCalculator`; the concrete class behind it is now SPAN. Renaming the attribute is **out of scope**
> (it would touch `handler.py`, `portfolio_view.py`, `fno_runner.py`, and tests for no behavioural gain).

### 2.3 Every composition change — exhaustive list

| # | File | Change | Reason |
|---|---|---|---|
| C1 | `core/execution/handler.py:155-165` | Add `span_snapshot: Optional[SpanSnapshot] = None` to `__init__`. | DI seam for the SPAN swap. |
| C2 | `core/execution/handler.py:196` | `self.margin_tracker = SpanMarginCalculator(...) if span_snapshot else MarginTracker(...)`. | The swap, at the single construction site. |
| C3 | `core/execution/handler.py` import block | `from core.risk.span.span_calculator import SpanMarginCalculator` and `from core.risk.span.span_snapshot import SpanSnapshot`. | Construction + type hint. |
| C4 | `core/execution/handler.py:1160-1164` | Re-source the *required-margin* term (§3). | Make incremental SPAN-consistent (the design crux). |
| C5 | `scripts/fno_runner.py` (derivatives branch) | Construct `SpanRepository`, `build_span_readiness`, load snapshot; pass `span_snapshot=` into `handler_kwargs`; pass `span_readiness=` into `LoopDriver`; refuse an empty archive. | The composition root performs the swap + wires the gate. |
| C6 | `scripts/fno_runner.py` imports | `SpanRepository`, `build_span_readiness`. | Above. |
| C7 | `core/runtime/driver.py:155` | Add `span_readiness: Optional[Callable[[], SpanReadinessVerdict]] = None`. | Startup gate wiring (mirror master). |
| C8 | `core/runtime/driver.py` startup sequence (~line 370-380) | Add `if not self._check_span_readiness(): return False` after master-readiness, before reconcile; add `_check_span_readiness()` mirroring `_check_master_readiness` (driver.py:385). | SPAN freshness gate (§5/§6). |

Nothing else in production changes. In particular `portfolio_view.py`, `margin_tracker.py`,
`span_calculator.py`, `margin_calculator.py` (protocol), and the S2 SPAN data modules are **untouched**.

---

## 3. Buying-Power Integration

> **Principle held:** admission **policy** is unchanged — same utilisation ratio, same `<= threshold`
> comparison, same reject. S4 changes only the **source** of the two margin terms. (Task §3: "Only change
> the source of the margin calculation.")

### 3.1 The four quantities, before and after

The platform does not keep a literal `buying_power` field; buying power is implicit in the utilisation
gate (`handler.py:1136-1166`). Defining each term explicitly:

| Quantity | Definition | Source **before** (MarginTracker) | Source **after** (SpanMarginCalculator) |
|---|---|---|---|
| **Used margin** `M_used` | Margin consumed by the **current** book | `get_used_margin(prices)` = `Σ_i notional_i · 0.2` | `get_used_margin(prices)` = `Σ_i notional_i · max(scan_risk_i, short_opt_min_i) · 1.0` |
| **Required margin** `M_req` | Margin a **proposed** order would add | `_estimate_required_margin(qty·mult, px) · margin_rate` = `qty·mult·px · 0.2` | `get_incremental_margin(sym, qty, px, lot_size=mult)` = `qty·px·mult · max(scan_risk,short_opt_min) · 1.0` |
| **Available margin / buying power** `M_avail` | Head-room for new orders | `cash · max_util − M_used` (implicit) | `cash · max_util − M_used` (implicit, **same form**) |
| **Utilisation** `U` | Gate ratio | `(M_used + M_req) / cash` | `(M_used + M_req) / cash` (**same form**) |

The gate decision is **identical in shape** (`handler.py:1165-1166`):

```
U = (M_used + M_req) / cash_balance
admit ⇔ U <= config.max_capital_utilisation
```

Only `M_used` and `M_req` change *source*. Equivalently, buying power is
`M_avail = cash_balance · max_capital_utilisation − M_used`, and the order is admitted iff
`M_req <= M_avail` — unchanged algebra, SPAN-sourced inputs.

### 3.2 The required-margin re-sourcing (C4) — the load-bearing edit

**Why it cannot be skipped.** If S4 swapped only the object and left `_check_margin_budget` untouched,
the two terms would use **different margin models**:

- `M_used` (SPAN) applies the per-underlying risk fraction `max(scan_risk, short_opt_min)` per position.
- `M_req` (`_estimate_required_margin · margin_rate`) applies **no** risk fraction — and with
  `margin_rate = 1.0` it collapses to **raw notional**, ≈ 7–10× the true SPAN incremental and ≈ 5× the
  old flat term.

No value of `margin_rate` reconciles a per-position-fraction `M_used` with a scalar×notional `M_req`.
Only `get_incremental_margin` applies the risk fraction to the proposed order. So S4 **must** re-source
`M_req`. This is *margin-source replacement* (the planted seam at `handler.py:1096`), not a policy or
execution redesign. (This resolves the S3 forward-reference — S3 §0/§3.5 built `get_incremental_margin`
"for S4's gate to consume": S4 consumes it here.)

**The exact change at `handler.py:1160-1164`:**

```python
prices = {sym: snap.price for sym, snap in self._price_cache.items()}
used_current = self.margin_tracker.get_used_margin(prices)              # unchanged line

# C4: required-margin source — SPAN when the calculator provides it, else the flat path.
if hasattr(self.margin_tracker, "get_incremental_margin"):
    incremental_est = self.margin_tracker.get_incremental_margin(
        order.symbol, order.quantity, current_price, lot_size=effective_multiplier
    )                                                                   # SPAN already applies margin_rate
else:
    incremental_est = (
        self._estimate_required_margin(order.quantity * effective_multiplier, current_price)
        * self.margin_tracker.margin_rate
    )                                                                   # incumbent flat path, unchanged

utilisation = (used_current + incremental_est) / self.metrics.cash_balance   # unchanged
return utilisation <= self.config.max_capital_utilisation, utilisation       # unchanged
```

The call mapping is verified against both function bodies: `get_incremental_margin(symbol, quantity,
price, lot_size)` returns `quantity · price · lot_size · risk_pct · margin_rate`; passing
`lot_size=effective_multiplier` reproduces the flat path's `order.quantity · effective_multiplier ·
current_price` notional **plus** the SPAN risk fraction, and the trailing `× margin_rate` is dropped
because the calculator already applies it.

### 3.3 Mechanism decision — reach an off-protocol method without growing the protocol (Design Q2)

This is the one mechanism the engineer must not have to invent. **Decision: capability detection via
`hasattr(self.margin_tracker, "get_incremental_margin")`.** Rationale:

- **Protocol stays v1.** Task non-goal forbids "changes to the `MarginCalculator` protocol." S3 §2.5
  deferred any v2 to "an S4 decision"; **this S4 task overrides that — v1 stays.** So we cannot add
  `get_incremental_margin` to the protocol; we reach it on the concrete object only.
- **`MarginTracker` keeps working.** Equity-only LIVE and every backtest inject nothing ⇒ `MarginTracker`
  ⇒ no `get_incremental_margin` ⇒ the `else` branch runs the **existing, unchanged** flat formula.
  Byte-identical behaviour on the incumbent path (regression-proof, §8).
- **Capability check, not `isinstance`.** `hasattr` keeps the *gate* decoupled from the concrete
  `core.risk.span` class (the import for *construction* is localised to line 196). It is the looser,
  protocol-spirited choice and is recommended over `isinstance(SpanMarginCalculator)`.

`MissingRiskArray` raised by `get_incremental_margin` (e.g. an equity symbol with no SPAN array reaching
the SPAN gate) propagates as a **D4 reject** (§6) — which is the architectural reason equity universes
keep `MarginTracker` at the root and never inject SPAN.

### 3.4 What does NOT change in the gate

- The utilisation ratio, the threshold `config.max_capital_utilisation`, the `<=` comparison, the
  `(approved, utilisation)` return shape.
- The `cash_balance <= 0` early-return (`handler.py:1150-1151`).
- The stacking-guard dependency (used = all positions; incremental = new order; non-double-counting
  because `process_signal` blocks new entries on already-held symbols — `handler.py:1145-1149`).
- `_estimate_required_margin` itself stays in place (it serves the `else` branch); its seam comment is now
  fulfilled for the SPAN branch.

---

## 4. Execution Behaviour — Invariants (explicitly unchanged)

Every item below must be provably unchanged by S4 (proof obligations in §8).

| Invariant | Why S4 preserves it |
|---|---|
| **Execution flow** | `process_signal` → priceability → margin gate → order path is structurally identical. Only the margin gate's two *numeric sources* change. |
| **Gate ordering** | No gate added, removed, or reordered in `process_signal`. `_check_margin_budget` keeps its position and `(bool, float)` contract. |
| **Kill switch** | Untouched. `_kill_switched`, consecutive-error counting, and trip conditions are not in the edited lines. |
| **Logging** | No log line added/removed/reworded on the hot path. Dry-run logging, alert text unchanged. |
| **Telemetry** | `get_stats` keys (`used_margin`, `daily_pnl`, …) unchanged; `PortfolioView.snapshot()` field set unchanged. The *value* of `used_margin`/`gross_exposure` is now SPAN-sourced — same key, SPAN number. |
| **Replay** | Replay reconstructs the same calculator from the journaled snapshot identity (§5.4) ⇒ same margin ⇒ same gate decisions ⇒ same fills. |
| **Runtime determinism** | The calculator does zero I/O/clock access (S3); the snapshot is frozen for the session; `(snapshot, positions, prices) → margin` is pure (ADR-003). |
| **Backtest path** | Injects nothing ⇒ `MarginTracker` ⇒ identical to today. The 791-test baseline is the guard. |
| **Equity-only LIVE** | Not a derivatives universe ⇒ no SPAN injection ⇒ `MarginTracker` ⇒ unchanged. |

**Invariant list (must hold byte-for-byte on the non-SPAN path):** gate count, gate order, threshold
constant, return shapes, kill-switch logic, log lines, telemetry keys, `_estimate_required_margin` body,
`MarginTracker` body, the `MarginCalculator` protocol, and all 791 existing tests.

---

## 5. Startup Behaviour

### 5.1 Readiness requirements

For a **LIVE F&O** run, SPAN must be **present and fresh** before the driver starts trading, exactly as
the instrument master must be. S4 reuses the S2 readiness machinery and the driver's existing gate
contract — it does **not** invent a new readiness model.

### 5.2 Startup ordering (driver `_run_startup`, mirrors `_check_master_readiness`)

```
RECOVERY (handler load_db_state=True, reused)            # driver.py:360-365, unchanged
   ↓
_check_master_readiness()        BLOCK → abort_startup → STOPPED     # driver.py:370, unchanged
   ↓
_check_span_readiness()   (NEW)  BLOCK → abort_startup → STOPPED     # mirror of the above
   ↓
_canonicalize_restored_ledger()                          # unchanged
   ↓
_reconcile_ledger()              fail → STOPPED           # unchanged
   ↓
start()
```

`_check_span_readiness` is gated on the **same predicate** as the master gate — `LIVE ∧ has_derivatives ∧
span_readiness is not None` — so paper, replay, and equity-only LIVE are a **no-op** (return True).

### 5.3 Repository injection & snapshot loading

- The **repository** is constructed once in `build_runner` (`SpanRepository(data_dir)`), used to (a) build
  the readiness checker handed to the driver and (b) load the snapshot handed to the handler.
- The **snapshot** is loaded once in `build_runner` (`repo.load(repo.latest_version())`), frozen, and
  injected. The driver never loads; the calculator never loads (S3 invariant). One load per session.
- The **readiness checker** (`build_span_readiness(repo)`) is the authoritative "should we start" gate,
  evaluated inside `driver.startup()` — symmetric with `master_readiness`.

### 5.4 What prevents startup (exact list)

| Condition | Where it stops the run | Mechanism |
|---|---|---|
| Archive empty (`latest_version() is None`) for an F&O universe | `build_runner` | `raise ValueError` (composition-time refusal, joins `fno_runner.py:106-145`). No driver is returned. |
| Snapshot file missing for the resolved version | `build_runner` (`repo.load`) | `FileNotFoundError` propagates out of `build_runner` — fail fast, no driver. |
| Checksum mismatch / corrupt snapshot | `build_runner` (`repo.load`) | `ValueError` propagates out of `build_runner`. |
| Unsupported parser schema | `build_runner` (`repo.load`) | `UnsupportedSpanSchema` propagates out of `build_runner`. |
| Snapshot stale (older than expected trading date) | `driver._check_span_readiness` | `SpanReadinessVerdict.state == BLOCK` → emit + `abort_startup()` → `False` → STOPPED. |

> **Why both a composition-time refusal and a driver gate?** It mirrors the master pattern: the driver
> gate is the authoritative *freshness* verdict (BLOCK→STOPPED), while `build_runner` already owns hard
> *construction* refusals (it cannot build a SPAN calculator from an empty/corrupt archive). The snapshot
> the calculator holds is exactly the one the readiness gate blesses (same repository, same version), so
> there is no second source of truth.

### 5.5 Failure surfacing to operators (Design Q6)

- **Composition-time** (`build_runner` raise): the exception text names SPAN and the cause; it surfaces in
  the launch logs and aborts before any collaborator starts — the same place operators already see the
  existing `build_runner` refusals (LIVE-without-source, LIVE-without-broker, expired-token).
- **Driver gate** (`_check_span_readiness` BLOCK): mirror `_check_master_readiness` exactly — emit a SPAN
  readiness event (`EventType.SPAN_SNAPSHOT_UNAVAILABLE`, or the S2 SPAN-readiness event if one exists)
  with `{reason, snapshot_date, expected_date}`, raise `alerter.critical(...)`, call `abort_startup()`,
  return `False`. The operator sees a critical alert + a durable journal event, identical in shape to a
  refused master start.

---

## 6. Failure Modes

"Refuse > warn > fallback" (ADR-MM7F-1): the platform never trades on a guessed margin. Disposition per
case:

| Case | Detected where | Result | Operator action |
|---|---|---|---|
| **Repository unavailable** (dir missing / empty archive, F&O) | `build_runner` (`latest_version() is None`) | **Startup failure** — `ValueError`, no driver constructed. | Run the SPAN fetch job; verify `data/span/` is populated. |
| **Snapshot missing** (no file for version) | `build_runner` (`repo.load`) | **Startup failure** — `FileNotFoundError`. | Fetch the day's SPAN file; re-launch. |
| **Snapshot corrupt / checksum mismatch** | `build_runner` (`repo.load`) | **Startup failure** — `ValueError`. | Re-download; the integrity check refuses tampered data. |
| **Readiness failure** (stale) | `driver._check_span_readiness` | **Startup failure** — BLOCK → `abort_startup` → STOPPED. | Refresh the snapshot to the expected trading date. |
| **Calculator exception at runtime** (`MissingRiskArray`, `MissingRiskMetric`, `UnsupportedInstrument`) | `get_used_margin` / `get_incremental_margin` inside `_check_margin_budget` | **D4 reject** of that order (the exception denotes "cannot margin this order/book"); propagates as a per-signal rejection, not a flat-rate fallback. | Investigate the underlying's coverage in the snapshot / the instrument's canonical identity. |
| **Unsupported instrument** (asset class SPAN cannot margin reaching the SPAN gate) | `get_incremental_margin` | **D4 reject** (`UnsupportedInstrument`). The structural fix is to **not inject SPAN for that universe** (equity ⇒ `MarginTracker`). | Confirm the universe/calculator pairing at the root. |
| **Missing risk array** for a traded underlying | `get_incremental_margin` / `get_used_margin` | **D4 reject** (`MissingRiskArray`). | Ensure the underlying is in the published SPAN file; re-fetch. |

**Rule:** corrupt/missing/stale/empty → **startup failure** (before any order). Lookup faults on a
specific order/book at runtime → **D4 reject** of that order. Never a flat-rate substitution.

---

## 7. Migration Strategy

### 7.1 Transition `MarginTracker → SpanMarginCalculator` with no public-interface change

- **No public interface changes.** `MarginCalculator` (protocol) is untouched. `ExecutionHandler` gains
  one **optional** keyword (`span_snapshot=None`); all existing call sites compile and behave identically.
  `LoopDriver` gains one **optional** keyword (`span_readiness=None`). `PortfolioView`, `MarginTracker`,
  and `SpanMarginCalculator` signatures are unchanged.
- **Strangler swap at the root.** The incumbent (`MarginTracker`) remains the default everywhere; only the
  F&O composition root injects the replacement. Equity/backtest/paper paths are unchanged by construction.
- **One construction site.** The swap is concentrated at `handler.py:196` behind a presence check, so the
  set of consumers (gate, `PortfolioView`, `get_stats`) is identical before and after — they read
  `self.margin_tracker` (typed `MarginCalculator`) and neither knows nor cares which concrete class backs
  it, except the gate's deliberate capability check (§3.3).

### 7.2 Rollback strategy (Design Q8)

**Rollback is configuration, not code.** SPAN is active **iff** a snapshot is injected at the root. To
disable SPAN temporarily:

- **Operational rollback (no deploy):** stop injecting `span_snapshot` from `build_runner` — a single
  boolean at the root, `SPAN_MARGIN_ENABLED` (default on for F&O). Off ⇒ the handler falls back to
  `MarginTracker` automatically (the `else` branches in §2.2 and §3.2). No consumer change, no protocol
  change, no schema change.
- **Code rollback:** revert C5/C7/C8 (the root + driver wiring) and the platform returns to flat-rate
  margin with `MarginTracker`; C1–C4 are inert without injection. Because the injection point is a single
  optional parameter, the diff is small and self-contained.

The `SPAN_MARGIN_ENABLED` boolean is the *only* policy knob S4 adds, and it gates **construction**, not
computation — the cheapest possible rollback path.

---

## 8. Testing Strategy

Focus: **prove the composition changed while behaviour stayed stable.** No new margin math is tested here
(S3 covers it); S4 tests prove wiring, source-substitution, and invariance.

### 8.1 RED (write first; fail before S4 wiring exists)

```
R1  test_handler_defaults_to_margin_tracker_when_no_snapshot
      ExecutionHandler(...) with span_snapshot=None ⇒ isinstance(margin_tracker, MarginTracker).
R2  test_handler_uses_span_calculator_when_snapshot_injected
      ExecutionHandler(..., span_snapshot=<hand-built>) ⇒ isinstance(margin_tracker, SpanMarginCalculator);
      same instance reachable from the handler-local PortfolioView.
R3  test_margin_gate_sources_incremental_from_span_when_available
      With SPAN injected, _check_margin_budget's incremental term == get_incremental_margin(...) (the
      SPAN value), NOT _estimate_required_margin × margin_rate. Assert the exact number.
R4  test_margin_gate_keeps_flat_incremental_for_margin_tracker
      With MarginTracker (default), incremental term == _estimate_required_margin × 0.2 — byte-identical
      to today. Guards the regression path.
R5  test_missing_risk_array_at_gate_rejects_order
      SPAN injected, order on an underlying absent from the snapshot ⇒ MissingRiskArray surfaces as a
      D4 reject (order not admitted), never a flat-rate fallback.
R6  test_build_runner_injects_span_for_fno_universe
      build_runner(F&O symbols, a populated span dir) ⇒ handler.margin_tracker is SpanMarginCalculator
      and the same instance backs the driver's PortfolioView.
R7  test_build_runner_refuses_empty_span_archive_for_fno
      build_runner(F&O, empty span dir) ⇒ ValueError (composition-time refusal).
R8  test_driver_blocks_start_on_stale_span_snapshot
      LIVE ∧ derivatives ∧ span_readiness→BLOCK ⇒ startup returns False, abort_startup invoked, STOPPED.
R9  test_driver_span_gate_noop_for_paper_and_equity
      paper, replay, equity-only LIVE ⇒ _check_span_readiness returns True (no-op).
```

### 8.2 GREEN (minimum to pass)

```
G1  Add span_snapshot param + presence-checked construction at handler.py:196 (R1, R2).
G2  Capability-checked incremental re-source in _check_margin_budget (R3, R4, R5).
G3  build_runner derivatives branch: repo + readiness + snapshot load + injection (R6, R7).
G4  driver span_readiness param + _check_span_readiness mirroring _check_master_readiness (R8, R9).
```

### 8.3 Integration

```
I1  Full F&O composition: build_runner with a hand-seeded span dir → drive a signal → the margin gate
    admits/rejects on SPAN numbers; PortfolioView.snapshot().used_margin equals get_used_margin (SPAN).
I2  Telemetry parity: get_stats keys identical pre/post swap; only used_margin VALUE differs (SPAN vs flat).
I3  Same-instance proof: handler-local PortfolioView, driver PortfolioView, and the gate all read one
    SpanMarginCalculator object (id() equality).
```

### 8.4 Regression

```
X1  All 791 prior tests pass unchanged (no test edits). The default MarginTracker path is byte-identical.
X2  MarginCalculator protocol untouched; MarginTracker still conforms; S3 SpanMarginCalculator tests
    unchanged and passing.
X3  git diff --stat touches ONLY handler.py, fno_runner.py, driver.py (+ new S4 tests + docs). Zero diff
    in portfolio_view.py, margin_tracker.py, span_calculator.py, margin_calculator.py, and the S2 modules.
X4  Equity-only LIVE and paper runs: no SPAN construction, no span gate effect (R9, I-level smoke).
```

### 8.5 Acceptance Criteria

| # | Criterion |
|---|---|
| AC1 | F&O composition root injects the snapshot; `handler.margin_tracker` is `SpanMarginCalculator` for F&O, `MarginTracker` otherwise. |
| AC2 | The margin gate's **both** terms (used + required) are SPAN-sourced when SPAN is active; the flat path is byte-identical when it is not. |
| AC3 | Buying-power / utilisation **formula shape and threshold are unchanged**; only the term *sources* changed (§3.1). |
| AC4 | `MarginCalculator` protocol unchanged; `MarginTracker` still conforms; `SpanMarginCalculator` unchanged. |
| AC5 | LIVE F&O start is **blocked** when SPAN is absent/corrupt/stale (composition refusal or driver BLOCK); paper/replay/equity are no-ops. |
| AC6 | Runtime lookup faults (`MissingRiskArray`/`MissingRiskMetric`/`UnsupportedInstrument`) → **D4 reject**, never a flat-rate fallback. |
| AC7 | Both `PortfolioView` instances and the gate observe the **same** calculator instance. |
| AC8 | Zero diff in `portfolio_view.py`, `margin_tracker.py`, `span_calculator.py`, `margin_calculator.py`, S2 SPAN modules. |
| AC9 | All 791 prior tests pass; new S4 tests green; no test touches network or disk (hand-built snapshot, seeded dirs only). |
| AC10 | Rollback is a single root-level switch (`SPAN_MARGIN_ENABLED`); flipping it restores `MarginTracker` with no deploy. |

### 8.6 Definition of Done

- [ ] `handler.py`: `span_snapshot` param; presence-checked swap at line 196; capability-checked incremental re-source.
- [ ] `fno_runner.py`: repo + readiness + snapshot load + injection on the F&O branch; composition-time refusals.
- [ ] `driver.py`: `span_readiness` param; `_check_span_readiness` mirroring `_check_master_readiness`; slotted after master, before reconcile.
- [ ] `tests/...`: R1–R9, I1–I3 green; X1–X4 verified; filesystem-free (hand-built snapshot / seeded tmp dirs).
- [ ] Protocol, `MarginTracker`, `SpanMarginCalculator`, `PortfolioView`, S2 modules untouched (git diff --stat).
- [ ] All 791 prior tests pass; new tests green.
- [ ] Docs synced (§9.3). MM9.4 marked COMPLETE.

---

## 9. File-by-File Plan

### 9.1 Production files

| File | Change | Why |
|---|---|---|
| `core/execution/handler.py` | (a) `__init__` gains `span_snapshot: Optional[SpanSnapshot] = None`; (b) line 196 presence-checked swap; (c) imports `SpanMarginCalculator`, `SpanSnapshot`; (d) `_check_margin_budget` capability-checked incremental re-source (C1–C4). | The DI seam + the source substitution. The single construction site keeps both PortfolioViews on one instance. |
| `scripts/fno_runner.py` | Derivatives branch: construct `SpanRepository`, `build_span_readiness`, load snapshot, inject `span_snapshot=` into the handler, pass `span_readiness=` to `LoopDriver`; add composition-time refusal for an empty archive; new imports (C5–C6). | The composition root performs the swap and wires the startup gate (F&O only). |
| `core/runtime/driver.py` | Add `span_readiness` param; add `_check_span_readiness()` mirroring `_check_master_readiness`; slot the call after master-readiness and before reconcile (C7–C8). | SPAN freshness gate, reusing the existing readiness→STOPPED contract. |

**Not modified (and why):**

| File | Reason |
|---|---|
| `core/risk/margin_calculator.py` (protocol) | **v1 frozen** — task non-goal; growing it breaks `MarginTracker` conformance. The gate reaches `get_incremental_margin` by capability check, not via the protocol. |
| `core/execution/margin_tracker.py` | Incumbent default — must stay byte-identical for the regression baseline. |
| `core/risk/span/span_calculator.py` | S3 deliverable — consumed, not changed (non-goal). |
| `core/execution/portfolio_view.py` | Reads `margin_tracker`; automatically observes the injected instance — no edit. |
| `core/risk/span/span_repository.py`, `span_readiness.py`, `span_parser.py`, `span_freshness.py`, `span_pipeline.py`, `span_snapshot.py` | S2 data foundation — consumed, not changed. |

### 9.2 Test files

| File | Purpose |
|---|---|
| `tests/execution/test_mm9_4_s4_composition_swap.py` | **NEW.** R1–R5 (handler default/inject, gate source substitution, D4 reject), I2–I3 (telemetry parity, same-instance). |
| `tests/integration/test_mm9_4_s4_fno_root.py` | **NEW.** R6–R7 (build_runner injection + empty-archive refusal), I1 (end-to-end SPAN gate). |
| `tests/runtime/test_mm9_4_s4_span_readiness_gate.py` | **NEW.** R8–R9 (driver BLOCK on stale; no-op for paper/equity). |

### 9.3 Documentation files

| File | Change |
|---|---|
| `docs/reports/MM9_IMPLEMENTATION_PLAN.md` | Tick `MM9.4-S4`; mark **MM9.4 COMPLETE**; record the resolved S3 forward-reference (`get_incremental_margin` wired at the gate via capability check, protocol unchanged) and the deferral of spread/NOV credits + protocol-v2 to MM9.5/MM10. |
| `docs/PROJECT_STATE.md` | SPAN is the **active** margin engine for LIVE F&O; flat-rate `MarginTracker` retained for equity/backtest/paper and as the rollback path. |
| `docs/CHANGELOG_PLATFORM.md` | "MM9.4-S4 — composition swap: `SpanMarginCalculator` injected at the F&O root, gate used+required margin SPAN-sourced, SPAN startup-readiness gate wired; protocol/PortfolioView/MarginTracker unchanged; `SPAN_MARGIN_ENABLED` rollback switch." |
| `docs/architecture_decisions.md` | IN-note under ADR-007: the gate reaches `get_incremental_margin` via capability detection (no protocol v2); rollback is a single root switch. |
| `docs/SESSION_BOOTSTRAP.md` | "Current Gaps §8": SPAN margin **active**; MM9.4 closed; remaining SPAN work (spread credits / NOV) is MM9.5+. |

---

## 10. Additional Design Questions — Explicit Answers

1. **Where is the active `SpanSnapshot` obtained?**
   In `build_runner` (the F&O composition root): `repo = SpanRepository(data_dir)`,
   `snapshot = repo.load(repo.latest_version())`. Loaded once, frozen for the session, injected into the
   handler. Neither the driver nor the calculator ever loads it (§2.1, §5.3).

2. **How is the calculator injected into the execution engine?**
   `ExecutionHandler.__init__` gains `span_snapshot: Optional[SpanSnapshot] = None`. At the single
   construction site (`handler.py:196`) the handler builds `SpanMarginCalculator(self.position_tracker,
   span_snapshot)` when a snapshot is present, else `MarginTracker(self.position_tracker)`. So both
   `PortfolioView` instances and the gate observe one instance, with no post-construction re-assignment
   (§2.2, Decision A).

3. **Which existing object remains responsible for tracking margin *state*?**
   None — and that is unchanged. There is **no** margin-state holder: `MarginCalculator` implementations are
   stateless w.r.t. the portfolio (ADR-007 rule #1). The **position state** lives in `PositionTracker`
   (ADR-001 truth); both `MarginTracker` and `SpanMarginCalculator` read it on demand and cache nothing.
   The calculator holds only immutable config (the snapshot) and a scalar rate.

4. **Does `MarginTracker` disappear entirely, or become a thin state holder?**
   Neither. It **remains** the default `MarginCalculator` for equity, backtest, and paper paths, and is the
   rollback target when SPAN is disabled. It is not demoted to a state holder (it never held state); it is
   simply no longer the F&O default. It stays byte-identical (the 791-test regression baseline depends on
   it).

5. **How is buying power calculated after the swap?**
   Same formula, SPAN-sourced inputs (§3.1): `M_avail = cash_balance · max_capital_utilisation − M_used`,
   admit iff `M_req <= M_avail`, with `M_used = get_used_margin(prices)` (SPAN) and
   `M_req = get_incremental_margin(symbol, qty, price, lot_size=multiplier)` (SPAN). The threshold and the
   ratio are unchanged; only the two term sources moved from flat-rate to SPAN.

6. **How are startup failures surfaced to operators?**
   Two channels, both pre-trade: composition-time refusals raise out of `build_runner` (named exception in
   launch logs, no driver constructed), and the driver's `_check_span_readiness` BLOCK emits a journal
   event + `alerter.critical(...)` + `abort_startup()` → STOPPED — identical in shape to a refused
   master-readiness start (§5.5).

7. **How is replay guaranteed to use the correct snapshot?**
   The session journals the loaded snapshot identity (`snapshot_date` + `file_hash`, S2). Replay loads the
   same archive entry (version + checksum equality) and constructs an identical calculator; with identical
   positions and prices the gate reproduces every decision bit-for-bit (§4, §5.4; ADR-003). The calculator
   does zero runtime I/O and the snapshot is frozen for the session.

8. **What rollback path exists if SPAN must be temporarily disabled?**
   A single root-level switch (`SPAN_MARGIN_ENABLED`, default on for F&O). Off ⇒ `build_runner` injects no
   snapshot ⇒ the handler falls back to `MarginTracker` ⇒ the gate's `else` branch runs the unchanged flat
   formula. No deploy, no protocol change, no schema change. Code-level rollback is reverting the three
   wiring edits (§7.2).

---

## 11. Explicit Non-Goals (S4 must NOT include any of these)

- Changes to the `MarginCalculator` protocol (v1 stays; gate reaches `get_incremental_margin` by capability
  check) · changes to `SpanMarginCalculator` · new SPAN formulas · parser changes · repository changes ·
  readiness redesign (the gate is **reused**, not redesigned) · telemetry redesign · execution redesign
  (the gate's *source* changes; its policy/ordering/return shape do not) · `PortfolioView` redesign · driver
  redesign (one readiness-gate call is **added**, mirroring an existing one) · MM10 work.
- Spread/NOV credits, protocol-v2 formalisation, broker-margin reconciliation — deferred to MM9.5+.
- Renaming `self.margin_tracker` · introducing a margin-state holder · caching any portfolio-derived value.

---

## 12. Architecture Principles Preserved

| Principle | How S4 preserves it |
|---|---|
| **ADR-001 — Ledger Is Truth** | The calculator reads the live `PositionTracker` on demand; S4 adds no second position source. Both `PortfolioView`s and the gate read one calculator instance over one tracker. |
| **ADR-003 — Deterministic Processing** | The injected calculator does zero I/O/clock access; the snapshot is frozen for the session and journaled; replay == live (§4, §5.4). |
| **ADR-006 — Sole Orchestrator** | No new runtime path. The swap is construction-time; the gate keeps its single call site; the driver gains one readiness call in the existing startup sequence. |
| **ADR-007 — MarginCalculator Seam** | The swap happens entirely behind the protocol seam; the protocol is unchanged; the calculator exposes no admission policy (the handler still decides); no broker API at margin time. |
| Dependency injection | Snapshot + readiness checker injected at the root; the handler/driver load nothing. |
| Immutable reference data | The frozen `SpanSnapshot` is injected as config and never mutated. |
| Deterministic replay | Hard snapshot identity (date + hash) + pure compute reconstructs identical gate decisions. |
| Zero runtime network I/O | All SPAN acquisition is the S2 offline job; runtime does lookup-and-sum only. |
| Protocol stability | `MarginCalculator` v1 is untouched; `MarginTracker` still conforms; the off-protocol incremental is reached by capability check, not by growing the contract. |
| Stateless calculator | No positions/margin/equity cached; recomputed each call (S3 invariant carried forward). |

---

## Appendix A — The Swap, in Three Diffs (authoritative for the implementer)

```
# 1. core/execution/handler.py
__init__(..., span_snapshot: Optional[SpanSnapshot] = None)
line 196:
    self.margin_tracker: MarginCalculator = (
        SpanMarginCalculator(self.position_tracker, span_snapshot)
        if span_snapshot is not None
        else MarginTracker(self.position_tracker)
    )
_check_margin_budget (≈1160):
    if hasattr(self.margin_tracker, "get_incremental_margin"):
        incremental_est = self.margin_tracker.get_incremental_margin(
            order.symbol, order.quantity, current_price, lot_size=effective_multiplier)
    else:
        incremental_est = (self._estimate_required_margin(
            order.quantity * effective_multiplier, current_price) * self.margin_tracker.margin_rate)

# 2. scripts/fno_runner.py  (derivatives branch only)
    span_repo = SpanRepository(span_data_dir)
    span_readiness = build_span_readiness(span_repo)
    version = span_repo.latest_version()
    if version is None:
        raise ValueError("fno_runner: F&O universe requires a SPAN snapshot; archive empty")
    handler_kwargs["span_snapshot"] = span_repo.load(version)
    ...
    return LoopDriver(..., master_readiness=master_readiness, span_readiness=span_readiness, ...)

# 3. core/runtime/driver.py
__init__(..., span_readiness: Optional[Callable[[], SpanReadinessVerdict]] = None)
_run_startup: after _check_master_readiness, before _canonicalize/_reconcile:
    if not self._check_span_readiness(): return False
_check_span_readiness(): exact mirror of _check_master_readiness (driver.py:385) —
    guard (is_live ∧ has_derivatives ∧ span_readiness is not None); BLOCK → emit + abort_startup → False.
```

## Appendix B — Behavioural Delta Table (what an operator observes)

| Observable | Equity / backtest / paper | LIVE F&O (after S4) |
|---|---|---|
| `margin_tracker` concrete class | `MarginTracker` (unchanged) | `SpanMarginCalculator` |
| Gate used-margin source | flat `Σ notional · 0.2` | SPAN `Σ notional · risk_pct` |
| Gate required-margin source | `notional · 0.2` (flat) | SPAN `notional · risk_pct` (`get_incremental_margin`) |
| Utilisation formula / threshold | unchanged | unchanged |
| Startup gates | unchanged | + SPAN readiness (absent/corrupt/stale ⇒ refuse) |
| Telemetry keys | unchanged | unchanged (values SPAN-sourced) |
| Rollback | n/a | flip `SPAN_MARGIN_ENABLED` → `MarginTracker` |

## Appendix C — Slice Dependencies

```
MM9.4-S1 (protocol + seam, ADR-007)
      │
MM9.4-S2 (SPAN data foundation — SpanSnapshot, repository, readiness)
      │
MM9.4-S3 (SpanMarginCalculator — used/exposure/incremental; off-protocol get_incremental_margin)
      │
MM9.4-S4 (THIS SLICE: inject at the F&O root; gate used+required SPAN-sourced; SPAN readiness gate)  → MM9.4 COMPLETE
      │
MM9.5+   (spread/NOV credits, MarginCalculator v2 formalisation, broker-margin reconciliation)
```

S4 ships the composition and leaves the platform with **SPAN as the active margin engine for LIVE F&O**,
flat-rate `MarginTracker` retained for equity/backtest/paper and as the zero-deploy rollback path.
