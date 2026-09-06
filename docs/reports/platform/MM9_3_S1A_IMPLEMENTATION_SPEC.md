# MM9.3-S1A — Greek Gate Semantic Correction
## Implementation Specification

**Status:** PENDING IMPLEMENTATION
**Parent spec:** `docs/reports/MM9_3_IMPLEMENTATION_SPEC.md` (§5, Slice S1A)
**Preceded by:** MM9.2 COMPLETE (696 tests passing)
**Followed by:** MM9.3-S1B (portfolio Greek aggregation) — may start only after S1A merges
**Date drafted:** 2026-06-28
**Scope:** ONE slice — `_check_greek_limits` semantic correction. S1B/S2/S3 are explicitly out of scope.

---

## 0. Summary

`_check_greek_limits` (`core/execution/handler.py:964-1005`) today raises
`ExecutionRuleError` on a marginal-delta breach — crash-escalation semantics that
contradict the D4 rejection-gate pattern established by MM9.1 (`_check_margin_budget`)
and MM9.2-S3-S3 (`_check_book_priceable`). S1A converts it to a bool-returning gate,
wires the call site, and adds the EXIT bypass — **without** changing what it computes
(it remains a marginal-only delta check; S1B replaces the body).

**One production file changes. One production line changes.** Six new tests land;
one transient characterization test is written-then-deleted within the slice.

### Correction to the parent spec (§5 / S1A.3)

The parent MM9.3 spec proposes a WARNING log line shaped
`"[%s] Greek delta breach (marginal)..." self.runner_id, ...`. **`self.runner_id`
does not exist on `ExecutionHandler`** (grep-verified: no `runner_id` attribute is
assigned anywhere in `handler.py`). The established D4 WARNING convention in this file,
set by MM9.1 and MM9.2-S3-S3, is a **constant token prefix** carrying `symbol` and
`signal_id`:

```
MARGIN_BUDGET_REJECTED symbol=%s signal_id=%s utilisation=%.2f%% limit=%.2f%%   (handler.py:780)
PORTFOLIO_UNPRICEABLE symbol=%s signal_id=%s missing=%s stale=%s ages_s=%s     (handler.py:744)
```

S1A therefore uses the token `GREEK_DELTA_BREACH` with `symbol`/`signal_id`, **no
runner_id prefix**, to match the file's existing pattern. This is the single deviation
from the parent spec and it is forced by the codebase.

---

## 1. Repository Impact Review

### 1.1 Files modified — exactly ONE

| File | Slice | Exact change | Lines (current) |
|------|-------|--------------|------------------|
| `core/execution/handler.py` | S1A | (a) signature `-> bool`; (b) EXIT early-return; (c) `raise ExecutionRuleError` → `rejected_trades += 1` + WARNING + `return False` + terminal `return True`; (d) call-site `if not ...: return None` | method body 964-1005; call site 613 |

No other production file is touched. `core/execution/rules.py` keeps
`ExecutionRuleError` (it is still raised by `enforce_signal_idempotency`,
`enforce_risk_clearance`, the daily-trade-limit path at handler.py:586, and the
RiskManager rejection at handler.py:721). S1A removes exactly **one** of the four
`raise ExecutionRuleError(...)` sites in `handler.py` — the one inside
`_check_greek_limits` at line 1004.

### 1.2 Files NOT modified (verified)

| File | Reason |
|------|--------|
| `core/execution/rules.py` | `ExecutionRuleError` stays; three other call sites still raise it |
| `core/execution/config.py` | (N/A — config lives in `handler.py`) |
| `core/execution/handler.py` `ExecutionConfig` | Greek limit fields already present: `max_portfolio_delta=1000.0`, `max_portfolio_vega=500.0`, `max_gamma_exposure=100.0` (handler.py:99-101) |
| `core/risk/greeks/portfolio_greeks.py` | S1B territory |
| `core/risk/greeks/greeks_calculator.py` | S1B territory |
| `core/risk/greeks/black76_engine.py` | S1B territory |
| `core/execution/portfolio_view.py` | S2/S3 territory |
| `core/runtime/driver.py` | S2 territory; S1A adds zero driver coupling |
| `scripts/fno_runner.py` | S2 territory |
| `core/instruments/instrument_parser.py` | **Intentionally unchanged** — G1 carve-out #3; see §1.5 |
| Any `EventType` enum / journal / alerter | S1A introduces **no** new event type, **no** journal write, **no** kill-switch interaction |

### 1.3 Existing call sites of `_check_greek_limits`

| # | Location | Caller | Reachable in production? | S1A change |
|---|----------|--------|--------------------------|------------|
| 1 | `handler.py:613` | `ExecutionHandler.process_signal` | **Yes** — `process_signal` is the sole runtime caller reachable from `LoopDriver._dispatch_signals` (ADR-006; confirmed by `G1_CLOSEOUT_REPORT.md`) | Wrap with `if not self._check_greek_limits(...): return None` |
| 2 | none | `process_group_signal` (handler.py:861) does **not** call it | n/a | none |

There is exactly **one** call site. The G1 closure guard
(`tests/g1/test_g1_closure_guard.py:235`) lists `_check_greek_limits` among the three
audited `InstrumentParser.parse` hosts in `handler.py`; S1A does not move, add, or
remove any `parse` call, so that AST guard stays green by construction (see §4.4).

### 1.4 Backward compatibility analysis

| Surface | Pre-S1A | Post-S1A | Breaking? |
|---------|---------|----------|-----------|
| `process_signal(...)` return type | `Optional[NormalizedOrder]` | unchanged | No |
| `process_signal(...)` return *value* on a delta breach | **raises `ExecutionRuleError`** (crash) | returns `None` (silent skip) | **Behaviourally different — this is the fix**. No *type* change; no *caller* depends on the raise (the only production caller, `LoopDriver._dispatch_signals`, wraps `process_signal` in a per-signal try/except that would otherwise log `BROKER_ERROR` on the raise). |
| `_check_greek_limits` return type | `None` (implicit) | `bool` | Private method; only one internal caller, which S1A updates atomically. No external importer (grep-verified). |
| `ExecutionConfig` greek fields | present | unchanged | No |
| `ExecutionRuleError` | raised here | removed here only | No — class + 3 other raise sites intact |
| Public API (`ExecutionHandler`, `build_runner`, `process_signal` signature) | — | unchanged | No |
| Telemetry payload (`_build_positions`, metrics.json) | — | unchanged | No |
| Journal events | none from this gate | none | No |
| Kill switch | none from this gate | none | No |

**Net:** S1A is a behaviour-correcting, signature-tightening change to one private
method and its single call site. No public API changes. No new coupling.

### 1.5 `InstrumentParser` — intentionally unchanged

The `InstrumentParser.parse(signal.symbol)` call at handler.py:978 **stays exactly
where it is**, inside `_check_greek_limits`. This is the G1 Wave-5 carve-out #3
(`G1_WAVE5_CLOSURE_GUARD_REPORT.md`, `SOLE_IDENTITY_PATH_REVIEW.md`): the parse result
is transient — it feeds `GreeksCalculator.calculate()` for asset-class dispatch only
(Equity/Future/Option), never crosses the broker/persistence/canonical boundary, and is
correct on legacy types. S1A touches only the *rejection mechanism* (raise → return
bool), not the *identity source*. S1B will later add the migration TODO comment; S1A
does not.

---

## 2. Implementation Plan

### 2.1 Current code (read-only reference)

```python
# handler.py:613 (call site, inside process_signal, after _check_risk_limits/enforce_risk_clearance)
# Phase 9C: Greek Risk Check
self._check_greek_limits(signal, current_price)
```

```python
# handler.py:964-1005 (method body)
def _check_greek_limits(self, signal: SignalEvent, current_price: float):
    """Phase 9C: Check if the new order would breach portfolio Greek limits. ..."""
    meta = signal.metadata or {}
    underlying_price = meta.get('underlying_price', current_price)
    iv = meta.get('iv', 0.20)
    tte = meta.get('tte', 0.0)
    instrument = InstrumentParser.parse(signal.symbol)
    qty = self._calculate_position_size(signal, current_price)
    if signal.signal_type == SignalType.SELL:
        qty = -qty
    from core.risk.greeks.greeks_calculator import GreeksCalculator
    new_greeks = GreeksCalculator.calculate(
        instrument=instrument, quantity=qty,
        underlying_price=underlying_price, volatility=iv, time_to_expiry=tte,
    )
    # ... portfolio-aggregation comments elided (S1B territory) ...
    if abs(new_greeks.delta) > self.config.max_portfolio_delta:
        raise ExecutionRuleError(
            f"Order Delta {new_greeks.delta:.2f} exceeds limit {self.config.max_portfolio_delta}")
```

### 2.2 Method signature change

```python
# BEFORE
def _check_greek_limits(self, signal: SignalEvent, current_price: float):

# AFTER
def _check_greek_limits(self, signal: SignalEvent, current_price: float) -> bool:
```

Return contract: `True` = signal proceeds; `False` = rejected (caller returns `None`).
Never returns `None`. Never raises.

### 2.3 EXIT bypass — first statement of the method body

```python
def _check_greek_limits(self, signal: SignalEvent, current_price: float) -> bool:
    if signal.signal_type == SignalType.EXIT:
        return True  # reducing risk is always allowed
    ...
```

**Why inside the method, not at the call site:** at handler.py:613 the call site is
**not** inside the `if signal.signal_type != SignalType.EXIT:` guard — that guard wraps
the *downstream* margin gate at line 726 and the priceability gate at line 734, both of
which sit after PHASE 1. The Greek gate runs earlier, at [9C] (before instrument
resolution). The EXIT bypass therefore must live in the method itself. This mirrors the
parent spec §5.4 design decision. (`_check_risk_limits` itself has no EXIT early-return
— it handles SELL by checking the resulting short against `max_position_size` — so the
parent spec's analogy is loose; the design stands on its own merit: closing a position
reduces portfolio exposure and must never be blocked by an exposure cap.)

### 2.4 Rejection mechanism — replace the raise

```python
# AFTER (replaces handler.py:1003-1005)
if abs(new_greeks.delta) > self.config.max_portfolio_delta:
    self.metrics.rejected_trades += 1
    # signal_id derived inside the helper (§2.4a) — same canonical logic as
    # process_signal at handler.py:517-522; deterministic, never diverges.
    sig_id = getattr(signal, 'signal_id', signal.metadata.get('signal_id'))
    if not sig_id:
        from hashlib import sha256
        raw_id = f"{signal.symbol}_{signal.strategy_id}_{signal.timestamp.isoformat()}"
        sig_id = sha256(raw_id.encode()).hexdigest()
    self.logger.warning(
        "GREEK_DELTA_BREACH symbol=%s signal_id=%s delta=%.2f limit=%.2f",
        signal.symbol, sig_id, new_greeks.delta, self.config.max_portfolio_delta,
    )
    return False
return True
```

`sig_id` is derived **inside the helper** via the same canonical logic `process_signal`
uses at handler.py:517-522 (see §2.4a). The method stays a two-parameter gate; no
`signal_id` is threaded from the caller.

**WARNING shape — D4 pattern compliance:**
- Token prefix `GREEK_DELTA_BREACH` mirrors `MARGIN_BUDGET_REJECTED` and
  `PORTFOLIO_UNPRICEABLE`.
- `symbol=%s signal_id=%s` ordering matches both existing gates.
- `delta` formatted to 2dp (matches the deleted raise's `{new_greeks.delta:.2f}`).
- `limit` formatted to 2dp.
- **No `runner_id`** (does not exist on the handler — §0 correction).
- Uses `self.logger` (the `setup_logger("execution_handler")` instance, handler.py:246).
- Uses `self.metrics.rejected_trades` (the `ExecutionMetrics` counter, handler.py:122),
  identical to how MM9.1/MM9.2 increment it at handler.py:720/736/779.

#### 2.4a `signal_id` derivation — inside the helper, not threaded

The two-parameter signature is preserved:

```python
def _check_greek_limits(self, signal: SignalEvent, current_price: float) -> bool:
```

`signal_id` for the WARNING is derived inside the method by replicating the canonical
logic already used at handler.py:517-522. The recommended form is **inline** (three
lines, shown in §2.4's code block) — it duplicates only six lines that already live at
517-522 and keeps the helper self-contained. An extracted `_signal_id_for_log(signal)`
private method is a **deferred refactor**, not an S1A requirement: pursue it only if
`process_signal` is independently refactored to reuse the same derivation (which would
make the helper the single derivation site for both). S1A must not couple to that
refactor.

**Why derive rather than thread (owner decision, review-approved):**
- Keeps the helper's responsibility focused on Greek gating.
- Avoids widening the private signature — S1B replaces the body without touching the
  signature again.
- Reduces coupling between `process_signal` and `_check_greek_limits`.

**Determinism guarantee:** the derivation is pure (same `symbol`/`strategy_id`/
`timestamp` → same sha256 hex). The idempotency-locked value at handler.py:528
(`str(signal_id)`) is byte-identical to the value derived here, because both consume the
same fields. The logged `signal_id` therefore matches the idempotency key exactly — no
divergence, despite the re-derivation. The derivation here is **observability-only**; the
authoritative lock already happened at line 525/528 before the call site, so this value
is never used for control flow.

### 2.5 Call-site change in `process_signal`

```python
# handler.py:612-613 BEFORE
# Phase 9C: Greek Risk Check
self._check_greek_limits(signal, current_price)

# AFTER
# Phase 9C: Greek Risk Check (S1A: bool-returning rejection gate; EXIT bypasses inside)
if not self._check_greek_limits(signal, current_price):
    return None
```

**Precise insertion:** the existing two lines at 612-613 are **replaced** (not
adjacent-inserted). The comment is updated in-place to document S1A semantics. No
surrounding lines move. The immediately-following block (TLP context capture, line 615+)
is untouched.

**Ordering relative to neighbours (unchanged):**
- Runs **after** `_check_risk_limits` + `enforce_risk_clearance` (PHASE 0/5, lines
  608-610) — so a `RiskManager` rejection still raises `ExecutionRuleError` first
  (regression guard R2 in §3.5).
- Runs **before** TLP context capture (line 615), PHASE 1 instrument resolution (line
  631), the priceability gate (line 734), and the margin gate (line 777). So the Greek
  gate is the **earliest** rejection-after-risk-clearance gate. A Greek rejection
  short-circuits all downstream work — no `NormalizedOrder` is built, no margin is
  estimated, no priceability check runs.

### 2.6 Logging behaviour

| Event | Level | Token | Emitted from | Conditions |
|-------|-------|-------|--------------|------------|
| Greek delta breach (marginal) | WARNING | `GREEK_DELTA_BREACH` | `_check_greek_limits` (via `self.logger.warning`) | Exactly when `abs(new_greeks.delta) > max_portfolio_delta` **and** signal is not EXIT |
| Pass | — | none | — | Silent (consistent with MM9.1/MM9.2 approval path) |
| EXIT bypass | — | none | — | Silent (consistent with margin-gate EXIT bypass) |

No `logger.info`, no `logger.error`, no `logger.exception` is added. No
`self.logger.exception` (that pattern is reserved for the journal-write-failure
fire-and-forget in MM9.2-S3-S3; the Greek gate does no journal write).

### 2.7 Rejection behaviour

A rejection performs exactly three side effects, **in this order**:

1. `self.metrics.rejected_trades += 1` — counter increments **exactly once** per
   rejected signal (no retry, no second increment downstream; the margin/priceability
   gates are never reached on a Greek rejection because of the `return None`).
2. `self.logger.warning("GREEK_DELTA_BREACH ...", ...)` — single line.
3. `return False` → caller executes `return None` → `process_signal` exits.

**No journal event.** No `self._journal.record(...)`. No `EventType` lookup. No
`Severity`. This is the D4 "rejection = metric + WARNING + None" contract, *minus* the
optional journal — the margin gate (MM9.1) writes no journal either; only
`PORTFOLIO_UNPRICEABLE` (MM9.2-S3-S3) journals, and S1A deliberately does **not** follow
that heavier pattern (S1A is a pure semantic correction; journaling would be a feature
addition).

### 2.8 EXIT bypass behaviour

`signal.signal_type == SignalType.EXIT` → `return True` immediately, **before** any
`InstrumentParser.parse`, sizing, or `GreeksCalculator.calculate` call. EXIT signals:
- Do not increment `rejected_trades`.
- Do not log.
- Do not compute Greeks.
- Proceed through `process_signal` to the downstream EXIT-aware path (the
  `OptionsContractSelector` / `canonicalize_symbol` branch at line 636 is gated on
  `signal.signal_type != SignalType.EXIT` for the option path; the EXIT path reuses the
  canonical-restore fallback at line 659).

### 2.9 Interaction with MM9.1 margin gate

| Concern | Behaviour |
|---------|-----------|
| Gate ordering | Greek gate [9C] runs **before** margin gate [MARGIN] (handler.py:777). A Greek rejection returns `None` before `_check_margin_budget` is reached. |
| Double-rejection | Impossible. On a Greek `return False`, `process_signal` returns immediately; the margin gate never runs. `rejected_trades` increments exactly once. |
| EXIT handling asymmetry (intentional) | Greek gate bypasses EXIT **inside the method**; margin gate bypasses EXIT **at the call site** (`if signal.signal_type != SignalType.EXIT:`, line 726). Both arrive at "EXIT is never gated" — different mechanism, same outcome. Documented; no action. |
| Shared counters | Both write `self.metrics.rejected_trades` (the single counter). Mutually exclusive on any one signal. |

### 2.10 Interaction with MM9.2 priceability gate

| Concern | Behaviour |
|---------|-----------|
| Ordering | Greek gate [9C] runs **before** priceability gate [PRICEABLE] (handler.py:734). A Greek rejection pre-empts the priceability check. |
| Portfolio book state | The Greek gate (S1A scope) reads **no** portfolio book state — it computes only the marginal signal delta. So an unpriceable/stale book does not affect S1A. (S1B will read `_price_cache` / `position_tracker`; S1A does not.) |
| Journal asymmetry (intentional) | `PORTFOLIO_UNPRICEABLE` writes a journal event; `GREEK_DELTA_BREACH` does not. S1A matches the **margin** gate (no journal), not the priceability gate (journal). |

---

## 3. TDD Plan

**Baseline:** **696 tests passing** (post-MM9.2-S4, per `PROJECT_STATE.md`).

**RED→GREEN order.** Tests are written first and must be red against the unchanged
codebase (for characterization) or red until the production change lands (for new
behaviour).

### 3.1 Characterization tests (transient — lock current broken behaviour)

Written against the **unchanged** codebase, before any production edit. They document
the defect being fixed. Both are deleted within the slice.

| ID | Test name | Asserts (current broken behaviour) | Disposition |
|----|-----------|--------------------------------------|-------------|
| C1 | `test_current_greek_gate_raises_executionruleerror_on_delta_breach` | A BUY signal whose computed marginal delta exceeds `max_portfolio_delta` causes `_check_greek_limits` to `raise ExecutionRuleError`. | **Deleted at end of S1A** (semantics fixed) |
| C2 | `test_current_greek_gate_checks_only_marginal_not_portfolio` | The gate's delta value reflects **only** the marginal signal, not `position_tracker` holdings. (Inject a non-FLAT position; assert the marginal-only delta is what's compared.) | **Left alive through S1A**, deleted by S1B. Documents the known interim limitation. |

C1 is red against the *post*-S1A code (the raise is gone); green against the unchanged
code. C2 is green against both S1A and the unchanged code (S1A does not change *what* is
computed, only *how* a breach is reported).

### 3.2 New unit tests — `tests/execution/test_greek_limits.py` (new file)

Six S1A tests. Each mocks only `_check_greek_limits` inputs (`signal`,
`current_price`, `signal_id`) and asserts on return type, raised exceptions (none),
`rejected_trades` counter, and log output. Construction reuses the
`_build_handler(tmp_path, monkeypatch, ...)` helper pattern from
`test_mm9_1_margin_gate.py` (DatabaseManager reset, ReplayClock, PaperBroker,
`load_db_state=True`, `metrics_path` under tmp).

| ID | Test name | What it verifies | Red because |
|----|-----------|------------------|-------------|
| U1 | `test_greek_gate_returns_bool` | `_check_greek_limits(...)` returns `bool` (not `None`) for both pass and breach inputs; `isinstance(result, bool)` | Current returns `None` on pass |
| U2 | `test_greek_gate_never_raises_on_delta_breach` | A breach input does **not** raise; returns `False` | Current raises `ExecutionRuleError` |
| U3 | `test_greek_gate_bypasses_exit_signal` | An EXIT signal returns `True`; `InstrumentParser.parse` is **not** called (monkeypatch/spy); `rejected_trades` unchanged; no WARNING | Current computes Greeks unconditionally (EXIT falls through to SELL branch) |
| U4 | `test_greek_gate_increments_rejected_trades_on_breach` | A breach increments `self.metrics.rejected_trades` by exactly 1; a pass leaves it unchanged | Current raises instead of incrementing |
| U5 | `test_greek_gate_logs_warning_on_breach` | `caplog` contains `"GREEK_DELTA_BREACH"` on a breach; contains `symbol` and `signal_id` values; **no** log line on pass; **no** log on EXIT | Current raises instead of logging |
| U6 | `test_greek_gate_passes_when_delta_within_limit` | Marginal delta `≤ max_portfolio_delta` returns `True`; boundary `==` is pass (strict `>` breach) | Current returns `None` on pass (not `True`) |

**Triggering a breach without realistic sizing:** construct `ExecutionConfig` with
`max_portfolio_delta` set very low (e.g. `0.5`) and a signal whose computed marginal
delta (equity: `qty × price_direction_factor`; default `default_quantity=100`,
`confidence=0.9` → `qty = 100 × (0.5 + 0.9×0.5) = 95`) comfortably exceeds it. Equity
delta ≈ quantity (GreeksCalculator equity branch), so `max_portfolio_delta=50.0` with
`default_quantity=100` → breach; `max_portfolio_delta=200.0` → pass. Pin exact numbers
in the test from `_calculate_position_size` output, not from intuition.

**Assertion on the EXIT-skip of `InstrumentParser.parse`:** monkeypatch
`handler_mod.InstrumentParser.parse` with a `Mock()`; assert `not mock.called` after an
EXIT call. This also guards against a future regression that moves the EXIT bypass
below the parse line.

### 3.3 Call-site / integration tests — append to `tests/execution/test_greek_limits.py`

| ID | Test name | What it verifies |
|----|-----------|------------------|
| I1 | `test_process_signal_returns_none_when_greek_gate_rejects` | Over-limit BUY → `process_signal` returns `None`; `rejected_trades == 1` |
| I2 | `test_process_signal_proceeds_when_greek_gate_passes` | Under-limit BUY → `process_signal` returns non-`None`; reaches PaperBroker fill path |
| I3 | `test_process_signal_exit_bypasses_greek_gate` | EXIT against an open LONG → `process_signal` does not return `None` at the greek step; `_check_greek_limits` called but returns `True` (spy) |
| I4 | `test_greek_gate_rejection_pre_empts_margin_gate` | Over-limit BUY with `max_capital_utilisation` also tight → `_check_margin_budget` is **not** called (spy); `rejected_trades == 1` (not 2) |
| I5 | `test_no_executionruleerror_from_greek_gate_in_process_signal` | `process_signal` on a breach does not raise (previously propagated); `LoopDriver._dispatch_signals`'s `BROKER_ERROR` journal path is not triggered by a Greek rejection |
| I6 | `test_greek_gate_rejection_does_not_create_order_tracker_entry` | Over-limit BUY → `process_signal` returns `None`; `order_tracker` contains **no** entry for the rejected signal's correlation/order id (no orphan). Mirrors MM9.1's `test_rejected_signal_order_not_in_tracker` (`test_mm9_1_margin_gate.py`) — makes the [9C]-before-[PHASE 5] ordering guarantee explicit as a standalone assertion. |

I1/I2 reuse `_make_signal(...)` from `test_mm9_1_margin_gate.py` (or define a local
factory in the new file). I3 needs a prior BUY fill to open the position (reuse the
PaperBroker fill path). I4 spies `_check_margin_budget` with `patch.object`. I6 inspects
`order_tracker.order_states()` (or equivalent) and asserts the rejected signal's order is
absent — the gate at [9C] runs strictly before `order_tracker.add_order(order)` at
[PHASE 5] (handler.py:790), so a Greek rejection cannot leave an orphan.

### 3.4 Regression guard — existing tests that must stay green

| File | Test(s) | Why unaffected |
|------|---------|----------------|
| `tests/g1/test_g1_closure_guard.py` | `test_handler_parse_calls_confined_to_audited_functions` (line 231), `test_no_unclassified_instrumentparser_parse_site_in_core` (line 218) | S1A does not move/add/remove any `InstrumentParser.parse` call. `_check_greek_limits` remains in the allowlist `{process_signal, process_group_signal, _check_greek_limits}` (line 235). The parse call stays inside `_check_greek_limits`. **Green by construction.** |
| `tests/execution/test_mm9_1_margin_gate.py` | all | S1A does not touch `_check_margin_budget`, its call site, or `ExecutionConfig.max_capital_utilisation`. |
| `tests/execution/test_handler_s3_s3_gate.py` | all | S1A does not touch `_check_book_priceable` or the freshness gate. |
| `tests/runtime/test_synthetic_wiring_proof.py` | `pytest.raises(ExecutionRuleError)` at line 260 | That test exercises the **idempotency** or **risk-clearance** path (line 50 imports `ExecutionRuleError`), not the greek gate. The raise removed by S1A is a different site. **Verify** by reading the test body before merge; it should be unaffected. |
| `tests/scripts/test_fno_runner_*.py` | all | `build_runner` unchanged; S1A is internal to `process_signal`. |

### 3.5 Expected counts

| Stage | Suite count | Delta |
|-------|-------------|-------|
| Baseline (pre-S1A) | 696 | — |
| + C1, C2 characterization (transient) | 698 | +2 |
| + U1-U6, I1-I6 new tests | 710 | +12 |
| − C1 deleted (semantics fixed) | 709 | −1 |
| **Final (S1A merged)** | **709** | **+13 net** (C2 retained) |

If C2 is *also* deleted at S1A close (owner option — it documents an interim state that
S1B will fix, so keeping it has value), final = 708. The parent spec §9 lists "All 6 S1A
tests green; suite ≥ 696 passing" — the floor is 696 + (6 new − C1 deleted) = 701
minimum if integration tests are folded. This spec's plan keeps them separate: **final
≥ 708**.

---

## 4. Risk Review

### 4.1 Architectural risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| A1 | The bool return is silently ignored by a future caller (drops the `if not ...`) | Low | High — a breach would no-op instead of reject | Only one caller exists and S1A updates it atomically. The G1 closure guard could be extended (out of S1A scope) to assert the call site shape, but the existing `_PARSE_ALLOWED` allowlist already pins `_check_greek_limits` as a parse host — a new caller would trip the guard. |
| A2 | EXIT bypass inside the method diverges from the call-site bypass pattern of MM9.1/MM9.2 | Low | Low — both achieve "EXIT never gated" | Documented in §2.3 and §2.9. The asymmetry is forced by gate ordering ([9C] is before the outer EXIT guard at line 726). No action. |
| A3 | `signal_id` re-derivation inside the helper could diverge from the idempotency-locked value | Low | Low | Deterministic sha256 of the same fields → byte-identical (§2.4a). Observability-only; never used for control flow. |

### 4.2 Behavioural risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| B1 | A signal that previously raised (and was caught upstream as a crash) now silently returns `None` — observability loss | Medium | Medium | The `GREEK_DELTA_BREACH` WARNING restores observability at the correct severity. Pre-S1A the raise hit `LoopDriver._dispatch_signals`'s per-signal try/except (Phase G §8.4) and was journaled as `BROKER_ERROR` — a mis-categorised event for a risk-gate rejection. S1A's WARNING is *more* correct. |
| B2 | `rejected_trades` double-counts if the margin gate also runs | None | — | Impossible: `return None` after `return False` short-circuits before the margin gate (§2.9). Test I4 pins this. |
| B3 | EXIT signals now skip Greek computation entirely — a stale greek cache is not refreshed on EXIT | Low | None | S1A does no caching. The "current portfolio greeks" concept is S1B. |
| B4 | The marginal-only check (S1A interim state) approves a signal that, combined with the portfolio, would breach | High (by design) | Medium | **Documented interim limitation** (parent spec §5, §6.1). C2 characterization test pins it. S1B replaces the body. Not a S1A defect — S1A is explicitly not portfolio-aware. |

### 4.3 Ordering risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| O1 | Greek gate runs before the priceability gate → could reject on a marginal delta while the book is unpriceable | Low | Low | S1A reads no book state; priceability is irrelevant to the marginal computation. Ordering is unchanged from pre-S1A; S1A only changes the *outcome* of a breach. |
| O2 | Greek gate runs before PHASE 1 instrument resolution → `InstrumentParser.parse` (not the canonical resolver) types the instrument | Medium (pre-existing) | Low | G1 carve-out #3 — accepted, documented (`G1_WAVE5_CLOSURE_GUARD_REPORT.md`). S1A does not change this; S1B adds the migration TODO. |
| O3 | S1B merged before S1A — TODO/state assumptions diverge | Low | Low | Enforce merge order: S1A precedes S1B (parent spec §1, §11 R9). S1A's `return True` terminal is the seam S1B's body replaces. |

### 4.4 Regression risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | G1 closure guard breaks | None | — | S1A does not touch `InstrumentParser.parse` sites. `_check_greek_limits` stays in `_PARSE_ALLOWED`. Green by construction (§3.4). |
| R2 | An existing `process_signal` test that expected the raise | Low | Medium | `grep -rn "_check_greek_limits\|ExecutionRuleError" tests/` (done): the only `ExecutionRuleError` test usages are `test_mm9_1_margin_gate.py:322` (risk-clearance path) and `test_synthetic_wiring_proof.py:260` (idempotency/risk path) — neither exercises the greek gate. No existing test asserts the greek raise. |
| R3 | `rejected_trades` count drifts in an unrelated test | Low | Low | S1A increments only on a breach, and only existing-default-config tests with a real delta breach trip it. Default `max_portfolio_delta=1000.0` with `default_quantity=100` → equity delta ~95, never breaches. Existing tests are unaffected. |
| R4 | `LoopDriver._dispatch_signals` per-signal isolation now never sees a `ExecutionRuleError` from this path | Low | Positive | The `BROKER_ERROR` journal path (Phase G §8.4) is no longer mis-triggered by a risk-gate rejection. This is a correctness improvement, not a regression. |

### 4.5 Documentation impact

| Doc | Update needed in S1A? |
|------|------------------------|
| `docs/DRIVER_SPECIFICATION.md` §8 (Greek gate) | **No** — the gate remains "no live caller" from the *driver's* perspective (it is a handler-internal gate). The §8 "dead code path" wording is accurate until S1B makes the gate portfolio-aware. S1A makes it *correct* but still marginal-only. Optional: a one-line note "S1A: semantics corrected to D4 rejection; body still marginal (S1B)". |
| `docs/reports/MM9_3_IMPLEMENTATION_SPEC.md` | **No edit to the parent** — this file is the S1A-specific refinement. Note the §0 correction (runner_id) for the parent's §5/S1A.3 example. |
| `docs/PROJECT_STATE.md` | One-line entry under MM9.3 In Progress after merge. |
| `docs/CHANGELOG_PLATFORM.md` | One entry: "MM9.3-S1A — `_check_greek_limits` converted from `raise ExecutionRuleError` to bool-returning D4 rejection gate; EXIT bypass; call-site wired. Body still marginal-only (S1B)." |
| `docs/reports/MM9_IMPLEMENTATION_PLAN.md` | Tick the S1A sub-box (parent spec §10.3 asks for the S1A/S1B split note). |
| ADRs | **None.** No new ADR (consistent with ADR-006 handler-owned gate, ADR-003 deterministic, ADR-001 no ledger mutation). |

---

## 5. Acceptance Checklist

Copy this into the merge request. Every box must be ticked.

### 5.1 Semantics
- [ ] `_check_greek_limits` return type is `bool` — **never raises, never returns `None`**
- [ ] `raise ExecutionRuleError(...)` at handler.py:1004 is **removed** (grep-verified: `grep -n "ExecutionRuleError" core/execution/handler.py` shows no match *inside* `_check_greek_limits`; the three other raise sites at 586/721 + the import at 26 remain)
- [ ] EXIT signal: returns `True` as the **first** statement; `InstrumentParser.parse` is not called (spy-verified)
- [ ] Delta breach (marginal): `abs(new_greeks.delta) > max_portfolio_delta` → `rejected_trades += 1` + WARNING + `return False`
- [ ] Delta within limit (incl. boundary `==`): `return True`
- [ ] WARNING token is `GREEK_DELTA_BREACH`; carries `symbol` and `signal_id`; uses `self.logger.warning`; **no `runner_id`**

### 5.2 Call site
- [ ] handler.py:613 is `if not self._check_greek_limits(signal, current_price): return None` — **two arguments only** (no `signal_id` parameter; derived inside the helper per §2.4a)
- [ ] No code between the `enforce_risk_clearance(...)` (line 610) and the greek call was deleted or reordered

### 5.3 Counters & side effects
- [ ] `rejected_trades` increments **exactly once** on a breach (test I1/I4)
- [ ] A Greek rejection leaves **no orphan order** in `order_tracker` (test I6 — [9C] runs strictly before [PHASE 5] `add_order`)
- [ ] **No** journal event written (`self._journal.record` not called from this gate)
- [ ] **No** kill-switch interaction (`activate_kill_switch` not called)
- [ ] **No** new `EventType` introduced
- [ ] **No** portfolio aggregation added (no `_price_cache`, `position_tracker`, or `portfolio_greeks` read inside the method — S1B territory)

### 5.4 Boundaries honoured
- [ ] `InstrumentParser` **intentionally unchanged** — parse call remains at handler.py:978 inside `_check_greek_limits`
- [ ] G1 closure guard (`tests/g1/test_g1_closure_guard.py`) green — `_check_greek_limits` still in `_PARSE_ALLOWED`
- [ ] Public APIs (`ExecutionHandler`, `process_signal` signature, `build_runner`, `ExecutionConfig`) **backward compatible**
- [ ] No new production file created

### 5.5 Tests
- [ ] C1 characterization written (red-then-green) → **deleted** at slice close
- [ ] C2 characterization written (documents interim marginal-only state) → **retained** for S1B
- [ ] U1-U6 green (6 unit tests)
- [ ] I1-I6 green (6 integration tests) — incl. **I6 orphan-order regression**
- [ ] Suite ≥ **708** passing, 0 failing
- [ ] `grep -rn "ExecutionRuleError" tests/execution/test_greek_limits.py` → no `pytest.raises(ExecutionRuleError)` referencing the greek gate

### 5.6 Documentation
- [ ] `PROJECT_STATE.md` MM9.3 In Progress line added
- [ ] `CHANGELOG_PLATFORM.md` entry added
- [ ] `MM9_IMPLEMENTATION_PLAN.md` S1A box ticked + S1A/S1B split note

---

## 6. Definition of Done (S1A alone)

S1A is **DONE** when **all** hold:

1. `_check_greek_limits` returns `bool`, never raises, EXIT bypasses, breach → metric + WARNING + `False`.
2. The single call site is `if not self._check_greek_limits(...): return None`.
3. `grep -n "ExecutionRuleError" core/execution/handler.py` shows **no** match inside `_check_greek_limits`.
4. `InstrumentParser.parse` is unchanged in location and count (G1 guard green).
5. Suite ≥ 708 passing, 0 failing.
6. C1 deleted; C2 retained.
7. No journal event, no kill-switch, no new `EventType`, no portfolio aggregation.
8. S1B has **not** started (merge-order gate — parent spec §11 R9).
