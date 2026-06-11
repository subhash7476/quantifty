# MM.7A — Live F&O Enablement Characterization Report

**Type:** Characterization net. **No production code, no entry script, no SignalSource, no reconciliation adapter, no fixes.** Tests + report only.
**Date:** 2026-06-11
**Basis:** `MM7_LIVE_WIRING_REVIEW.md` (findings W1–W4 + §7 test plan) · `G1_CLOSEOUT_REPORT.md` (G1 CLOSED, live call-graph audit) · `PROJECT_STATE.md` (Planned #4/#6, F3/F4).
**Starting state:** G1 CLOSED · 441 passing · 0 failing · MM.7 NOT WIRED.
**Ending state:** G1 CLOSED · **463 passing · 0 failing** · MM.7 NOT WIRED (unchanged — this is the safety net, not the wiring).

This builds the executable net the future MM.7 wiring + Planned #6 will be checked against — pinning current reality (including one defect, RED-documented) before any live-enablement code is written, exactly as the G1 waves pinned restore identity before migrating it.

---

## 1. Tests added (+22, all green)

| File | Tests | Maps to | Kind |
|---|---|---|---|
| `tests/scripts/test_fno_entry_wiring.py` | 9 | W1 + §4 mode matrix | Absence tripwire + acceptance predicate |
| `tests/execution/test_broker_positions_adapter.py` | 6 | W2 | Contract pin (shape + enum-vs-string + LONG/SHORT/FLAT) |
| `tests/runtime/test_driver_broker_positions_failure.py` | 3 | W3 | RED-documenting defect characterization |
| `tests/runtime/test_driver_canonicalization_requires_checker.py` | 4 | W4 | Coupling pin (real factory) |

Validation (this session):

```
pytest tests/scripts -q     →   9 passed
pytest tests/runtime -q     → 267 passed
pytest tests/execution -q   →  64 passed
pytest -q                   → 463 passed, 0 failing
```

Net: **441 → 463 passing, 0 failing.** No production code touched, so no regression surface.

---

## 2. Behaviors pinned

**T1 — F&O entry wiring acceptance (`tests/scripts/test_fno_entry_wiring.py`).**
- **Current absence (tripwire):** no module under `scripts/` constructs a `LoopDriver`, and no `scripts/*runner*` entry point exists. These flip RED the instant an F&O entry script lands — the signal to convert the predicate below into that script's real acceptance assertion.
- **Acceptance predicate `_fno_live_contract(driver)`** — the five clauses the entry script must satisfy: `Mode.LIVE`, `has_derivatives(symbols)`, `execution` present, `master_readiness` present, `source` present. Proven all-true against a correctly-wired driver (built from the shared doubles), which also **runs end-to-end to a clean STOPPED** — so the contract is demonstrably *sufficient* to drive the loop, not just structurally complete.
- **Rejection:** the predicate flags each missing clause individually (REPLAY mode, equity-only universe, no execution, no master_readiness, no source) — documenting the contract by showing each absence.

**T2 — broker-positions adapter contract (`tests/execution/test_broker_positions_adapter.py`).**
- The broker returns `Dict[str, Position]` (a dict; `side` a `PositionSide` enum; `quantity` absolute); reconciliation needs `List[Dict]` with a **string** `side`. Pinned as a genuine two-ended mismatch.
- **The naive pass-through breaks:** injecting `side` as the enum object raises `AttributeError` inside `reconcile` (`enum.upper()`), proving an adapter is *required*, not optional.
- A correct bridge preserves semantics across **LONG** (matches internal → no alert), **SHORT** (orphan detected, re-signed to `-5.0` — string round-trip survives), and **FLAT** (`quantity 0` → no orphan alert).

**T3 — W3 reconciliation-failure defect (`tests/runtime/test_driver_broker_positions_failure.py`).**
- A raising `broker_positions()` **propagates uncaught out of `run()`** (the gate runs before `run()`'s `try/finally`).
- The driver is left **stuck in `RECOVERY`** — `bars_processed == 0`, never STOPPED.
- The journal shows `RECOVERY_COMPLETED` but **no `RECONCILIATION_FAIL`, no `STOPPED`, no critical alert** — the failure is silent, unlike a real reconciliation divergence.
- This is GREEN today (it encodes the defect) and is designed to FLIP when Planned #6 converts the failure into a refusal → journal → STOPPED.

**T4 — W4 canonicalization activation (`tests/runtime/test_driver_canonicalization_requires_checker.py`).**
- Driven by the **real** `build_master_readiness(...)` factory over a materialized fixture master (not a verdict lambda).
- **Without** a checker: a LIVE + derivative run does **not** canonicalize the restored ledger (`canonicalize_calls == 0`, `canonicalize_order_calls == 0`) — the G1 restore-canonicalization is silently inert.
- **With** the real factory: both halves fire exactly once (positions #7-as-restored + orders #8).
- The checker alone is **not sufficient**: REPLAY and equity-only universes still skip canonicalization even with a real checker injected — pinning the full `is_live ∧ has_derivatives ∧ checker-present` gate.

---

## 3. W1 findings — no production `SignalSource` / no live `LoopDriver`

Confirmed and pinned. Every `SignalSource` is a test double; no `scripts/` module constructs a `LoopDriver`; no `*runner*` script exists. The composition root (entry script) **and** the strategy→`on_bar` adapter (`SignalSource`) are both absent — the driver has nothing to inject as `source` today. T1's tripwire makes this absence a standing, observable fact rather than a prose claim. **Building the F&O `SignalSource` is a named peer of building the entry script** (Planned #4), not a sub-detail of "order routing."

## 4. W2 findings — broker-positions shape bridge

Confirmed and pinned (T2). `UpstoxAdapter.get_positions()` → `Dict[str, Position]` with enum `side`; `ReconciliationEngine.reconcile` → `List[Dict]` with string `side` and signed re-derivation. **`broker.get_positions` cannot be injected as `broker_positions` directly** — the enum `side` raises in `reconcile`. The Planned-#6 adapter must listify, stringify `side`, and preserve the sign convention; T2 is its acceptance contract (the `_bridge` test glue is the shape it must reproduce, not an implementation).

## 5. W3 findings — `broker_positions()` failure escapes `run()`

Confirmed and pinned (T3) with executable evidence: the exception escapes `run()`, the driver stays in `RECOVERY`, and nothing is journaled. This is the **only RED-documenting characterization** in the net — it asserts the defect so the fix is forced to flip it. Planned #6 owns the fix (refusal → journal event → STOPPED, same contract as `RECONCILIATION_FAIL`); the entry script must **not** wrap the callable in its own try/except — the refusal belongs inside the gate.

## 6. W4 findings — master-checker ↔ canonicalization coupling

Confirmed and pinned (T4). Because `_canonicalize_restored_ledger` shares the MM.4 gate condition, **omitting the master-readiness checker silently disables the G1 restore-canonicalization the identity program just closed.** Injecting `build_master_readiness(...)` is therefore not just "turning on the staleness gate" — it is the activation switch for the restored-ledger identity upgrade on the live path. The entry script's tests must assert canonicalization actually fires, or a wiring omission regresses G1 invisibly.

---

## 7. Recommended implementation sequence

Unchanged from the MM.7 review §8, now backed by a green net. Each slice has its acceptance/regression tests already in place:

1. **MM.7 wiring — F&O entry script + F&O `SignalSource` (Planned #4 core).** Construct handler (`load_db_state=True`) + provider + clock + `build_master_readiness(...)` + the new `SignalSource`; target `Mode.LIVE` / `ExecutionMode.PAPER` first. **Gated by T1** (convert the predicate to the script's assertion; the tripwires flip RED on arrival) **and T4** (assert canonicalization fires).
2. **Broker-side reconciliation (Planned #6).** Implement the W2 adapter (acceptance = **T2**) and convert the W3 escape into a startup refusal (target = flipping **T3** from defect-pin to refusal-pin).
3. **F4 lot verification + F3 tick disposition.** Hard precondition for `ExecutionMode.LIVE` F&O — verify NIFTY 65 / BANKNIFTY 30 against exchange circulars; normalize F3 paise→₹ before any 4C.7 price-rounding consumer.
4. **F&O product/segment model + SPAN margin (Planned #4/#5).** Unblocks true live derivatives.
5. **4C.7 broker payload.** Stays blocked until 1–4.

**Sequencing rule the net enforces:** do not advance a slice until its characterization test is addressed — T1/T4 for the entry script, T2/T3 for reconciliation. The defect (T3) must be flipped, not deleted.

---

*Filed under the G1 review-first / characterize-before-change discipline. Companion to `MM7_LIVE_WIRING_REVIEW.md`.*
