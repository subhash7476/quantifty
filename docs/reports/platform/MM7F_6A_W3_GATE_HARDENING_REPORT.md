# MM.7F #6a — W3 Gate Hardening Implementation Report

**Type:** Implementation — convert a raising `broker_positions()` from an uncaught escape into a clean startup refusal. **No adapter. No reconciliation-logic change. No broker change. `ExecutionMode.LIVE` untouched.**
**Date:** 2026-06-12
**Basis:** `MM7F_BROKER_POSITIONS_ADAPTER_REVIEW.md` (§7 #6a; F4 — W3 is a driver-gate property, independent of the adapter) · `MM7_LIVE_WIRING_REVIEW.md` §3.2 (W3) · `MM7A_CHARACTERIZATION_REPORT.md` (T3 net).
**Starting state:** G1 CLOSED · 505 passing · 0 failing · W3 RED-documented (a raising `broker_positions()` escaped `run()`).
**Ending state:** G1 CLOSED · **505 passing · 0 failing** · W3 closed — the fault is now a refuse-to-start (`RECONCILIATION_FAIL` → critical alert → `STOPPED`).

> **Scope guard.** Gate hardening only. `core/execution/reconciliation.py`, both brokers, and the adapter (#6b) are untouched. The broker-positions *shape adapter* and the symbol-namespace decision remain #6b, bundled with the `ExecutionMode.LIVE` rung behind F4.

---

## 1. What changed

**`core/runtime/driver.py` — `_reconcile_ledger` (the §11 startup gate).** The single broker-book read was unguarded:

```python
alerts = self._execution.reconciliation.reconcile(self._broker_positions())
```

`self._broker_positions()` runs inside the gate, *before* `run()`'s `try/finally` (driver.py:524), so any exception (broker auth/transport — `upstox_adapter.py:60-62` raises `RuntimeError` on 401/403) propagated uncaught out of `run()`, leaving the driver stuck in `RECOVERY` with no `STOPPED`, no journal, no alert. Now the call is wrapped and a raise is routed into the **existing** refusal contract — identical in shape to a real reconciliation divergence (driver.py:465-475) and a master BLOCK (driver.py:394-403):

```python
try:
    broker_book = self._broker_positions()
except Exception as exc:
    self._emit(EventType.RECONCILIATION_FAIL, f"broker-positions source failed: {exc}")
    alerter.critical(f"LoopDriver refused to start: broker-positions source raised ({exc})")
    self.abort_startup()
    return False
alerts = self._execution.reconciliation.reconcile(broker_book)
...
```

`abort_startup()` runs from `RECOVERY` (set at gate entry, driver.py:346; it accepts `{STARTUP, RECOVERY}`, driver.py:321) and transitions to `STOPPED` emitting the `STOPPED` event (driver.py:319-323). `_reconcile_ledger` returns `False` → `_run_startup_gate` returns `False` → `run()` returns before the loop (driver.py:513-514), so `bars_processed == 0`.

**Nothing else changed.** The transformation/adapter, reconciliation comparison logic, and broker code are untouched. `except Exception` (not bare `except`) lets `KeyboardInterrupt`/`SystemExit` still propagate.

---

## 2. The flip (T3 net) — `tests/runtime/test_driver_broker_positions_failure.py`

The file was the only RED-documenting characterization in the MM7A net; #6a flips its assertions from "the defect" to "the refusal contract." Same harness (`_driver`, `alerts` fixture, `_events`), same raising-`broker_positions` injection, inverted expectations:

| Behavior | Before (defect pin) | After (#6a refusal pin) |
|---|---|---|
| `run()` on a raising source | `pytest.raises(RuntimeError)` — escapes | **no raise**; `run()` returns cleanly |
| terminal state | `RECOVERY` (stuck) | **`STOPPED`** (clean refusal) |
| `RECONCILIATION_FAIL` journaled | absent | **present** |
| `STOPPED` journaled | absent | **present** |
| critical alert | none (silent) | **`critical` emitted** |
| `bars_processed` | `0` | `0` (**kept**) |
| `RECONCILIATION_PASS` / `RUNNING` | absent | absent (kept — gate refused) |

Three tests: `test_broker_positions_exception_does_not_escape_run`, `test_driver_reaches_stopped_after_broker_positions_raises`, `test_reconciliation_fail_and_stopped_journaled_with_critical_alert`.

---

## 3. TDD trail

- **RED:** flipped the three T3 assertions, ran against the unhardened driver → 3 failed, all with `RuntimeError` escaping at `driver.py:464` (the exact W3 defect). Confirmed the tests fail for the right reason (missing behavior, not a typo).
- **GREEN:** added the `try/except` in `_reconcile_ledger` → `pytest tests/runtime/test_driver_broker_positions_failure.py` → **3 passed**.
- **Regression:** `pytest -q` → **505 passed, 0 failing** (unchanged count — the flip altered assertions, not the test population; no other suite touched the W3 path).

---

## 4. What this does NOT do (scope boundary)

- **No adapter (#6b).** The `Dict[str, Position]` → `List[Dict]` shape bridge and the symbol-namespace mapping (MM7F F1-note / risk 1) are unbuilt and remain #6b, gated with the `ExecutionMode.LIVE` rung behind F4.
- **No reconciliation-logic change.** `reconcile()` is byte-for-byte unchanged.
- **No broker change.** `UpstoxAdapter` / `PaperBroker` untouched.
- **No `ExecutionMode.LIVE`.** `fno_runner` still refuses `ExecutionMode.LIVE` without `broker_positions` (fno_runner.py:79-83). #6a hardens the gate *for when* a real callable is eventually wired; at the current `ExecutionMode.PAPER` rung `broker_positions` is `None` and the guarded block does not execute.

---

## 5. Stop condition

Implementation complete. Tests green (505 passing, 0 failing). Report written. Commit created. **Did NOT:** build the broker-positions adapter, change reconciliation logic, change any broker, or enable `ExecutionMode.LIVE`. The next slice is **#6b** — the broker-positions shape adapter + symbol-namespace decision, bundled with the `ExecutionMode.LIVE` rung behind F4.

*Filed under the G1 / MM7A–F review-first, characterize-before-change discipline. Companion to `MM7F_BROKER_POSITIONS_ADAPTER_REVIEW.md` (§7 #6a).*
