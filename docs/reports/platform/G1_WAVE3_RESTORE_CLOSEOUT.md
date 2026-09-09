# G1_WAVE3_RESTORE_CLOSEOUT.md

**Type:** Gate G1 — Migration Target **#2 (Restore Path)** closeout audit. **Read-only evidence review; no code changed in this audit.**
**Date:** 2026-06-10
**Scope:** Decide whether Migration Target #2 (Restore Path: #7-as-restored positions + #8 orders) can formally move to **COMPLETE**, having implemented both halves of the Option-B post-gate canonicalization pass.
**Basis (file:line, verified 2026-06-10):** `core/execution/handler.py`, `core/execution/order_tracker.py`, `core/execution/position_tracker.py`, `core/execution/canonical_restore.py`, `core/execution/persistence/{execution_store,order_repository}.py`, `core/execution/reconciliation.py`, `core/runtime/driver.py`, `core/brokers/{paper_broker,upstox_adapter}.py`, `core/instruments/resolver.py`. Full suite **409 passing, 0 failing**.

**Verdict: Migration Target #2 → COMPLETE. Gate G1 remains OPEN** (the forward sites #4/#6/#7 and the Wave-5 closure proof are outstanding; #2 is one input to Section-6 closure, not the whole gate).

---

## A — Restore identity flow (future + option)

**Claimed flow:** `_replay_state` → legacy identity → MM.4 gate → canonicalization pass → canonical identity.

**Evidence:**
- **Legacy at construction (pre-gate, Option B).** Orders: `order_repository.py:60` `InstrumentParser.parse(row[1])` → `Option`/`Equity` (no Future branch). Positions: rebuilt by replaying fills through `position_tracker.get_position(symbol)` → `InstrumentParser.parse` (`position_tracker.py:31`). Both run inside `ExecutionHandler.__init__` (`handler.py:186-187`), strictly **before** the driver gate.
- **Gate then canonicalize.** `LoopDriver._run_startup_gate` (`driver.py:335`): `_check_master_readiness()` (`:357`) → `_canonicalize_restored_ledger()` (`:364`) → `_reconcile_ledger()` (`:366`). The canonicalization pass is gated on the SAME condition as MM.4 (`is_live ∧ has_derivatives ∧ master_readiness is not None`), so it runs only on a verified-master gate-pass (FRESH/WARN), never on BLOCK (proven: `test_driver_gate_ordering.py::test_gate_skips_*_on_block`).
- **Both halves swap in place.** `canonicalize_restored_positions` iterates **every** entry in `position_tracker.get_all_positions()`; `canonicalize_restored_orders` iterates **every** `order_tracker.order_states()`. Each calls the shared `canonical_restore.canonicalize_symbol(symbol, as_of, resolver)` and, on a non-None result, swaps `.instrument` in place.

**No remaining derivative restore object left legacy after gate-pass — with one documented bound:**
- **Futures: always canonicalized.** `canonicalize_symbol` → `resolve_future` derives a `Future` for any futures-shaped symbol **even when the master is absent** (ADR-003; pinned by `test_master_absent_still_derives_future`). No futures restore object can remain `EQUITY` after the pass.
- **Options: canonicalized iff the master carries the contract.** `resolve_option` returns `None` when the snapshot has no matching `(underlying, expiry, strike, type)`, and the pass then **leaves the legacy `Option` (lot=1)** in place. For a **currently-tradeable** option this cannot happen on a gate-pass (MM.4 verified active-expiry coverage for the traded underlyings, and a freshly-tradeable contract is in the same master), so the live path is self-consistent. The residual case is a restored option for an **expired/rolled** contract no longer in the current snapshot — not a live-tradeable position. **Documented limitation, not a #2 blocker.**
- Equity / non-derivative symbols are an intentional **carve-out** (`canonicalize_symbol` → `None`; out of the F&O sole-source scope, ISIN-less symbol).

**A — PASS** (futures fully closed; options closed for the live-tradeable set, with the expired-contract edge documented).

---

## B — Reconciliation (symbol preserved; behavior unchanged)

- **Symbol preserved through both migrations.** `PositionTracker.replace_instrument` rebuilds the `Position` with the swapped instrument but keeps the `_positions` **symbol key** and the instrument's `.symbol`; `OrderTracker.replace_instrument` mutates `.instrument` in place (the new `Future`/`Option` carries the same `.symbol`). Pinned: `test_g1_restore_order_canonicalization.py` (`order.symbol == FUTURES_SYMBOL` / `== EXPECTED_OPTION_SYMBOL`) and the position sibling (`test_canonicalize_preserves_symbol_for_reconciliation` → `reconcile([...]) == []`).
- **Reconciliation engine unchanged + identity-blind.** `reconciliation.py` keys exclusively on `symbol` (`broker_map[symbol]`, `position_tracker._positions` by symbol, `net_quantity(symbol)`); it reads no `instrument_type`/lot/expiry. The file is **not modified by this wave** (canonicalization runs strictly before `_reconcile_ledger`, on the symbol-preserved ledger — H3).

**B — PASS.**

---

## C — Persistence (schema unchanged)

- `execution_store.py` DDL (the only execution-truth schema): `orders` (correlation_id, symbol, side, quantity, order_type, strategy_id, signal_id, timestamp, metadata), `fills` (fill_id, order_id, symbol, quantity, price, side, fee, timestamp), `positions` (symbol, side, quantity, avg_price, timestamp). **No `instrument_type` / `expiry` / `strike` / `option_type` / `lot_size` / `instrument_key` column; no new table; no new storage format.** This wave added **zero DDL**.
- The canonicalization swaps are **in-memory only** — `PositionTracker.replace_instrument` mutates the `_positions` dict; `OrderTracker.replace_instrument` mutates the tracked `NormalizedOrder.instrument`. Neither calls a repository / writes the SQLite ledger. Canonical identity is never persisted (the G1/4C.7 boundary holds: a restart re-derives legacy and re-canonicalizes post-gate).

**C — PASS.**

---

## D — Broker boundary (no CanonicalInstrument leak)

- **`canonicalize_symbol` returns legacy types only** — `Future` / `Option` built from `ci.expiry`/`ci.lot_size`/`ci.underlying`; the `CanonicalInstrument` is read then discarded (`canonical_restore.py:37-69`). No code path stores or forwards the `ci`.
- **`instrument_key` has ZERO references in `core/execution/`** (grep). The only `instrument_key` consumers are `core/brokers/mapping/*` (the 4C BrokerMapping projection — **unwired into the order path**; that wiring IS 4C.7, still blocked) and `upstox_market_data.py` (LTP fetch that takes a string key, unrelated to order identity).
- **Broker payload is symbol-keyed on both brokers.** `paper_broker.place_order` → `symbol = order.symbol`; `upstox_adapter.place_order` → `"instrument_token": order.symbol`. Neither derives the payload from a canonical `instrument_key`.
- Restored orders are **not re-sent** to the broker (they reconstruct idempotency `_seen_signals` + group state); canonicalizing their instrument has no broker-payload effect by construction.

**D — PASS.** CanonicalInstrument does not cross the `NormalizedOrder` / broker-payload / instrument_key-routing boundary.

---

## E — Closure criteria (can #2 move to COMPLETE?)

Against `SOLE_IDENTITY_PATH_REVIEW.md` Section 6:
- **#1 (no parse on the live order path):** futures order-build (#1) migrated in Wave 2; restore (#8/#9) is legacy-at-construction but **canonicalized post-gate before any live F&O use** — satisfied for the restore path. `InstrumentParser.parse` **is still called at construction** by design (Option B); that is allowed precisely because the post-gate pass re-resolves it.
- **#2 / #3 (canonical sole source incl. across restart):** restored futures + (live-tradeable) options are canonical-derived after the gate (axis A). The restart round-trip no longer leaves a live-tradeable F&O entry legacy-typed.
- **#4 (carve-outs documented):** equity + paper/replay + the expired-option edge are named (axis A).

**Open items reviewed:**
- **Forward sites #4 (option selector → canonical `Option`) and #6/#7 (forward `Position`/`get_position` construction): NOT migrated.** These are separate Migration Targets, not part of #2 (restore).
- **F4 (NIFTY lot 65 / BANKNIFTY 30 exchange verification): OPEN.** A precondition for the **live option path** generally (forward #4 and the restored-option lot alike); tracked separately, not a #2-restore blocker (restore preserves whatever the master holds, identical to forward).
- **F3 (tick-size paise scaling): OPEN**, 4C.7-scoped, no execution consumer today.
- **Wave-5 AST/grep closure guard (criterion #5): NOT WRITTEN.** Until that mechanical guard exists, **full Gate G1 cannot be declared closed** even though every behavioral criterion the restore path touches is met.

**E — Migration Target #2 → COMPLETE; Gate G1 → still OPEN.** #2 is one input to the gate; closure additionally requires #4, #6/#7, and the Wave-5 guard.

---

## Verdict & next step

| Axis | Result |
|---|---|
| A — restore identity flow | PASS (futures fully; options for live-tradeable set; expired-contract edge documented) |
| B — reconciliation | PASS (symbol preserved both halves; engine unchanged) |
| C — persistence | PASS (zero DDL; in-memory swaps; canonical never persisted) |
| D — broker boundary | PASS (legacy-only return; instrument_key absent from execution; symbol-keyed payloads) |
| E — closure criteria | #2 → COMPLETE; **G1 OPEN** (forward #4/#6/#7 + Wave-5 guard remain) |

**Audit clean for Migration Target #2.** Recommended sequence: commit the #8 implementation, commit the restore-path closeout (KB sync + this report), then authorize Wave 4 (#4 option path, F4-gated). The Wave-5 AST/grep guard is the remaining mechanical step to flip the whole-gate verdict to "No".
