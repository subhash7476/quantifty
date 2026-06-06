# PHASE_F_STARTUP_GATE_PLAN.md

**Status:** PLAN — no code. Focused implementation plan for **LoopDriver Phase F — Startup Gate / Recovery**.
**Implements:** `docs/DRIVER_SPECIFICATION.md` §11 (Recovery Behavior + Startup Validation Gate), governed by `docs/ARCHITECTURE_DECISIONS.md` (ADR-001 Ledger Is Truth; ADR-006 Sole Orchestrator) and `docs/PLATFORM_CONSTITUTION.md` §7 (a position must never become untraceable).
**Maps to:** `docs/LOOPDRIVER_IMPLEMENTATION_PLAN.md` "Phase H — Recovery & reconciliation startup gates" (this repo's working sequence relabels it **Phase F**, landing it before execution routing).

> No code in this document. Phases ship green-on-merge via TDD (tests first), runtime suite green after each.

---

## 1. Purpose

Make the driver **refuse to trade on an unvalidated or inconsistent ledger.** Before the loop routes (or, today, even pulls toward routing) a single signal, the driver must guarantee the ledger was restored from persistence and is consistent with broker truth. This is the last safety gate that must precede execution routing (Phase G): combined with the stale-data watchdog (Phase E), the loop is only ever *born* into a validated, protected state.

This phase is **still execution-free** — it adds the startup gate, not `process_signal`.

---

## 2. Responsibilities

1. Run a **startup-validation gate** on `start()` that must pass before `STARTUP → RUNNING`.
2. **Ensure** execution recovery ran — i.e. accept an `ExecutionHandler` constructed with `load_db_state=True` so `_replay_state()` already restored orders/fills/positions/idempotency. **Reuse, never re-restore** (ADR-001 — re-restoring would create a second source of position truth).
3. Run the handler's **reconciliation** against broker truth and honor its verdict (empty alerts = consistent).
4. Verify **preconditions**: non-empty symbols; broker reachable in the mode's required sense.
5. **Refuse to start** on any failure: `STARTUP → STOPPED`, critical alert, log — the loop never runs.
6. **Journal** the recovery + reconciliation outcome (the four events below), edge-triggered, once per startup.

Out of responsibility (explicitly): generating broker positions / normalizing the live broker book (that depth is `PROJECT_STATE.md` Planned #6), correcting the ledger (the engine detects; the driver never overwrites — ADR-001), runtime (mid-loop) reconciliation, and any signal routing.

---

## 3. Startup sequence (the gate)

Runs once, inside `run()` (or a `_startup_gate()` helper it calls), **when an `ExecutionHandler` is injected**. The no-handler path is the ungated A–E behavior — but it is **restricted to non-live modes** (see §3.1): a **LIVE** run with no handler is a wiring error and must not reach `RUNNING`.

```
construct() ───────────────► STARTUP            (RuntimeEventJournal: STARTUP, already emitted)
run():
  if execution is None:
    if config.is_live: ─────► REFUSE            (raise — §3.1: LIVE requires ExecutionHandler)
    else: start() ─────────► RUNNING            (REPLAY / inert: Phases A–E behavior, ungated)
  else:
    enter_recovery() ──────► RECOVERY           → emit RECOVERY_STARTED
    [step R] confirm _replay_state() ran        → emit RECOVERY_COMPLETED
    [step 1] symbols non-empty?                 (DriverConfig already enforces; re-assert §11.4#1)
    [step 4] broker reachable? (mode-dependent)
    [step 3] reconcile(broker_positions):
               empty  → emit RECONCILIATION_PASS
               non-empty (and require_reconciliation_on_start)
                      → emit RECONCILIATION_FAIL → ABORT
    all pass → start() ────► RUNNING            → emit RUNNING ; enter the tick loop
    any fail → abort_startup() ─► STOPPED        → critical alert + log ; loop never runs
```

Ordering is deliberate: recovery is confirmed **before** reconciliation (you reconcile the restored ledger, not an empty one), and both **before** `RUNNING`.

### 3.1 LIVE mode requires an injected ExecutionHandler (hard precondition)

**A LIVE run may not start without an injected `ExecutionHandler`.** The no-handler path exists **only for tests, replay, and inert runtime scenarios** — never live. In LIVE mode the handler is the ledger/recovery/reconciliation/kill-switch authority a real run cannot do without; starting live without it would skip the entire §11 gate and route (in Phase G) against no ledger — a direct ADR-001 / Constitution §7 violation.

- **Enforcement:** at `run()`, if `config.is_live and execution is None` → **raise** `RuntimeError("LIVE mode requires an injected ExecutionHandler")`, mirroring the existing clock/provider precondition check (a wiring error caught loud and early, before any state change — not a ledger-inconsistency STOPPED path).
- **REPLAY / inert:** no handler is fine — the gate is skipped and the loop runs ungated (Phases A–E behavior), so pure replay and unit/inert runs keep working without a ledger.
- **⚠️ Consequence for existing tests:** the Phase E watchdog tests run **LIVE with no handler injected**. Under this rule they must be updated in Phase F to inject a `FakeExecutionHandler` (a no-op recovery + empty reconcile), or be re-pointed appropriately. This is expected churn, not a regression — the live contract genuinely changed.

---

## 4. Recovery sequence (reuse — do NOT reimplement)

- `ExecutionHandler.__init__(..., load_db_state=True)` (`handler.py:127`) → `_replay_state()` (`handler.py:219`, invoked at `handler.py:186`) **already** restores: all orders + idempotency registry (`_seen_signals`), all fills → `order_tracker` + `position_tracker`, multi-leg groups, and `_trades_today`.
- The driver's job is to **ensure this happened**, not to redo it. It accepts a handler the wiring layer (`scripts/`) constructed with `load_db_state=True`; the driver does **not** call `_replay_state()` itself and holds no second restore path (ADR-001).
- `RECOVERY_COMPLETED` is emitted to mark the restored-ledger checkpoint. (If a cheap public signal of "restore ran" exists or is added on the handler, the gate may assert it; otherwise the contract is "inject an already-recovered handler," documented at the wiring layer.)

---

## 5. Reconciliation gate behavior

- Entry point: `handler.reconciliation.reconcile(broker_positions: List[Dict]) -> List[ReconciliationAlert]` (`reconciliation.py:24`).
- **Empty list ⇒ consistent ⇒ `RECONCILIATION_PASS`.** **Non-empty ⇒ divergence ⇒ `RECONCILIATION_FAIL` ⇒ refuse to start.**
- **Reconciliation branches by source presence, not by mode.** `reconcile()` is driven **only** when both hold: `config.require_reconciliation_on_start` is set **and** a `broker_positions` source (the optional `broker_positions` callable) was injected. When either is absent the check is **vacuously clear** — `RECONCILIATION_PASS` emitted, `reconcile()` never called:
  - **No source injected:** nothing to compare against → vacuous PASS. This covers **paper / replay** (the broker has no independent book) **and LIVE today**, because the real live broker-book fetch is not yet wired (Planned #6). LIVE reconciliation is therefore structurally present but vacuous for now — it gains teeth when that source lands with execution routing.
  - **`require_reconciliation_on_start=False`:** a deliberate operator override that skips reconciliation even when a source is present (default `True`).
- The driver **consumes the engine's verdict and never overwrites the ledger** (ADR-001). Pulling/normalizing the live broker book in depth is deferred (Planned #6); Phase F consumes whatever `broker_positions` it is handed.

---

## 6. Failure behavior (hard stop)

`STARTUP → RUNNING` is permitted **only if all** hold (§11.4):
1. `MarketDataProvider` over a **non-empty** `config.symbols`.
2. Handler constructed `load_db_state=True` and `_replay_state()` completed without error.
3. Reconciliation reports consistent (empty alerts), subject to `require_reconciliation_on_start`.
4. Broker reachable (live: auth/handshake OK; paper/mock: adapter present).

On **any** failure: `abort_startup()` → `STARTUP → STOPPED`, `alerter.critical(...)`, structured log; **the tick loop never starts.** "Trading on an unvalidated ledger is prohibited" — refuse-to-start is the safe default (mirrors ADR-004's protective-control-over-optimism). A reconciliation failure is the strongest case because an inconsistent ledger means positions may be untraceable (Constitution §7).

---

## 7. Journal events

All edge-triggered (once per startup), via the existing optional `RuntimeEventJournal` (no-op when absent). All four `EventType` values already exist (`event_journal.py`); **no new event types.**

| Event | When | Default severity |
|---|---|---|
| `RECOVERY_STARTED` | on `enter_recovery()` (STARTUP → RECOVERY) | INFO |
| `RECOVERY_COMPLETED` | after restored-ledger checkpoint confirmed | INFO |
| `RECONCILIATION_PASS` | `reconcile()` returns empty | INFO |
| `RECONCILIATION_FAIL` | `reconcile()` returns non-empty (gate fails) | CRITICAL |

On `RECONCILIATION_FAIL` (or any other gate failure) the existing `STOPPED` event follows from `abort_startup()`. On success, the existing `RUNNING` event follows from `start()`. Expected success sequence: `STARTUP → RECOVERY_STARTED → RECOVERY_COMPLETED → RECONCILIATION_PASS → RUNNING`. Expected failure sequence: `STARTUP → RECOVERY_STARTED → RECOVERY_COMPLETED → RECONCILIATION_FAIL → STOPPED`.

---

## 8. Driver state transitions involved

Reuses the existing §3.2 verbs already implemented in `core/runtime/driver.py` (Phase A) — **no new states, no new transitions**:

- `enter_recovery()` : `STARTUP → RECOVERY`
- `start()` : `RECOVERY → RUNNING` (gate passed) — also legal `STARTUP → RUNNING` for the no-handler ungated path
- `abort_startup()` : `STARTUP|RECOVERY → STOPPED` (refuse to start)
- (loop end, unchanged) `stop()` `RUNNING|PAUSED → STOPPING`, `finalize_stop()` `STOPPING → STOPPED`

Phase F wires these into a gate; it does not add to the state machine.

---

## 9. Dependencies required (all exist)

- **`ExecutionHandler`** — new optional DI param on `LoopDriver` (`execution: Optional[ExecutionHandler] = None`). Used for `_replay_state` recovery confirmation and `handler.reconciliation`. Constructed `load_db_state=True` at the wiring layer.
  - ⚠️ **Guard-test change:** Phase E's `test_driver_has_no_executionhandler_dependency` asserts the driver neither imports `ExecutionHandler` **nor** calls `process_signal`. Phase F legitimately **introduces the `ExecutionHandler` reference** (recovery + reconciliation are handler responsibilities, Constitution §3; §11 names them). The guard must **narrow to the real ADR-006 invariant: no `process_signal` call** — the import/reference becomes allowed, the routing call stays forbidden until Phase G.
- **`ReconciliationEngine.reconcile`** (`reconciliation.py:24`) — via `handler.reconciliation`.
- **Broker adapter** — for live `broker_positions` + reachability (paper/mock: presence check; live book depth deferred).
- **`alerter`** (`core/alerts/alerter.py`) — `critical(...)` on refuse-to-start.
- **`RuntimeEventJournal`** + the four `EventType` values — already present.
- **`DriverConfig.require_reconciliation_on_start`** + `mode`/`is_live` — already present.

DI evolution note: the handler enters the driver here (for the gate) but is **not yet routed to**; routing arrives in Phase G. The watchdog (Phase E) already holds its own handler reference, independent of this one.

---

## 10. What remains explicitly deferred

- **Execution routing (Phase G)** — `process_signal`, the data→signal→execution path, per-signal exception isolation, `BROKER_ERROR`. Phase F adds the handler reference but never calls `process_signal`.
- **Telemetry (Phase H)** — no metrics/positions/health publishing here.
- **Kill-switch event consolidation** — the `KILL_SWITCH_ACTIVATED` single-source-of-truth migration is a Phase G concern (see `ARCHITECTURE_DECISIONS.md` IN-001); Phase F does not touch the watchdog's emission.
- **Broker-side reconciliation depth** — pulling/normalizing the live broker book (`PROJECT_STATE.md` Planned #6); Phase F consumes whatever `broker_positions` it is handed.
  - **Deferred ownership of `broker_positions()` failure (Planned #6).** The injected `broker_positions` callable may **raise** (broker auth/handshake/transport failure). The startup gate runs **before** `run()`'s `try/finally` (driver.py — the gate at the top of `run()` precedes the loop's `try:`), so **today a raise propagates out of `run()` uncaught**, leaving the driver in `RECOVERY` with no `STOPPED` transition and no journal record. This is acceptable only because LIVE has no real book source wired yet (the callable is test-supplied). **Planned #6 owns converting this into a proper refusal path**: a `broker_positions()` exception must become a **startup refusal → journal event → `STOPPED`** (the same refuse-to-start contract as `RECONCILIATION_FAIL`), not an unhandled propagation. Documented here as deferred work; **not implemented in Phase F.**
- **Runtime (mid-loop) reconciliation** — only the *startup* gate is in scope.
- **Auto-clearing the kill switch / auto-recovery of trading** — operator-only (§9.6), unchanged.
- **SPAN margin / F&O product model** — execution-depth items, out of LoopDriver scope.

---

## 11. Test strategy (tests first)

New `tests/runtime/test_driver_startup_gate.py` + a `FakeExecutionHandler` (and minimal `FakeReconciliation`) in `tests/runtime/_doubles.py`:

- gate **pass** (empty reconcile) → `RUNNING`; events `RECOVERY_STARTED → RECOVERY_COMPLETED → RECONCILIATION_PASS` in order.
- reconcile **non-empty** → refuse to start: `STOPPED` + `RECONCILIATION_FAIL` (CRITICAL) + critical alert; tick loop never runs (0 bars).
- **no re-restore**: the driver does **not** call `_replay_state()` itself (reuse-only).
- **empty-symbols / unreachable-broker** → refuse to start.
- **paper/replay vacuous-clear**: reconciliation treated as consistent with no broker book.
- **REPLAY + no handler injected** → gate skipped; Phases A–E behavior preserved (regression).
- **LIVE + no handler injected** → `run()` **raises** `RuntimeError` (§3.1); loop never starts.
- **ADR-006 guard** (narrowed): driver still issues no `process_signal` call.
- existing runtime suite remains green; full suite re-run is the definition of "Phase F green."

**Existing-test churn (expected):** the Phase E live watchdog tests (`test_driver_watchdog.py`) construct a LIVE driver with no handler — under §3.1 they must inject a `FakeExecutionHandler` (no-op recovery, empty reconcile) to keep running live. Updating them is part of this phase.

Recommended: ship as one PR (`driver.py` + `_doubles.py` + `test_driver_startup_gate.py` + the watchdog-test update), green-on-merge, followed by the standalone `PROJECT_STATE`/`CHANGELOG` move once green.
