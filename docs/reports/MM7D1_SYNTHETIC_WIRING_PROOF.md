# MM.7D.1 — Synthetic Wiring Proof (Infrastructure Validation)

**Type:** Implementation — the smallest synthetic `SignalSource` + integration harness that proves the runtime executes a known order and closes it, end-to-end. **No production SignalSource, no entry script, no broker adapter, no strategy, no alpha, no market data, no option chain.**
**Date:** 2026-06-11
**Basis:** `MM7D_SYNTHETIC_SOURCE_REVIEW.md` (design) · `MM7C_SIGNALSOURCE_CHARACTERIZATION.md` (seam contract) · `MM7A_CHARACTERIZATION_REPORT.md` (T1/T4 net).
**Starting state:** G1 CLOSED · 484 passing · 0 failing · no production SignalSource/strategy/entry script.
**Ending state:** G1 CLOSED · **493 passing · 0 failing** (+9) · still no production SignalSource/strategy/entry script — the proof is test-local.

> **Scope guard.** NiftyShield is ABANDONED. Nothing here references, ports, migrates, or resurrects NiftyShield, `D:\BOT\root`, or any options-seller alpha. The synthetic source carries no market data, OHLCV, option chain, strategy logic, broker alpha, greeks, volatility, indicators, or chain provider. It exists only to make the wired runtime execute a BUY and close it with an EXIT, so the infrastructure can be observed doing its job.

---

## 0. Pre-implementation review (agreement / alternatives / assumptions)

- **Agree with MM7D**, with one applied refinement: I did **not** rebuild the "canonicalization fires on a derivative" case. MM7A T4 already pins it with the real `build_master_readiness` factory, and reproducing it needs a real derivative + master, which drags in Open Finding **F4** (forbidden by the stop condition). Tier A proves the **equity no-op**; the positive half is cited, not duplicated.
- **Alternatives rejected:** (a) source in `tests/runtime/_doubles.py` — that file is the shared *seam-double* kit, not the place for a BUY/EXIT strategy double; (b) a `scripts/` entry script — flips the MM7A T1 tripwire and falsely claims a production entry point (MM7E owns that); (c) calling `process_signal` directly without a `LoopDriver` — would not prove the *wiring*, only the handler.
- **Assumptions, all verified in code:** `InstrumentParser.parse("NSE_EQ|INE…") → Equity` with `.symbol` preserved (`instrument_parser.py:46`); `canonicalize_symbol` returns `None` for equity (`canonical_restore.py:36-40`); MM7C's proven risk values (price 2500, sl 5.0, risk_r 1.0, qty hint 50) clear risk clearance; `correlation_id`/`fill_id` are random UUIDs, so determinism is asserted on the *deterministic projection*, not raw rows.
- **Questions:** none that change implementation — the two real open decisions (F4 lot, derivative symbol-shape) live only in Tier B, which MM7D defers and the stop condition forbids touching.

---

## 1. Tests added (+9, all green)

File: **`tests/runtime/test_synthetic_wiring_proof.py`**. Drives a **real** `ExecutionHandler` (`ExecutionMode.PAPER`) + `PaperBroker` + `ExecutionStore` + a real `LoopDriver`, all against an **isolated tmp `execution.db`** (the MM7C isolation construction — `data/execution.db` is never touched).

| # | Test | Proves |
|---|---|---|
| 1 | `test_synthetic_source_emits_buy_then_exit` | call-indexed BUY→EXIT→∅; `on_start`/`on_stop` once; `signals_pulled == 2`; STOPPED |
| 2 | `test_buy_carries_valid_risk_fields_clean_path` | BUY's real `sl_distance`+`risk_r` take the clean path (no "missing risk definition" warn) |
| 3 | `test_equity_roundtrip_persists_orders_and_fills` | 2 orders {BUY,SELL}, 2 fills @ close; full-qty EXIT; position ends FLAT |
| 4 | `test_restart_restores_ledger_and_idempotency` | new handler on same db restores 2 orders/2 fills + `_seen_signals`; re-emit rejected |
| 5a | `test_reconciliation_pass_when_book_matches` | restored open long vs matching broker book → `RECONCILIATION_PASS` → RUNNING |
| 5b | `test_reconciliation_fail_when_book_diverges` | qty mismatch → `RECONCILIATION_FAIL` → refused (no RUNNING, `bars_processed==0`, critical alert) |
| 6 | `test_canonicalization_noop_on_equity` | equity REPLAY never triggers `canonicalize_restored_{positions,orders}` |
| 7 | `test_determinism_two_runs_identical_artifacts` | two independent runs → identical emitted stream + identical ledger projection |
| 8 | `test_proof_harness_is_test_local_not_an_entry_script` | proof lives under `tests/`; no `scripts/` module constructs a `LoopDriver` (MM7A T1) |

Validation: `pytest tests/runtime/test_synthetic_wiring_proof.py -q` → **9 passed**; `pytest -q` → **493 passed, 0 failing** (484 → 493). No production code changed.

**The synthetic source** is the MM7D §1 design, implemented test-local: a `SignalSource` subclass whose entire state is an emit counter — `on_bar #0 → [BUY]` (real `sl_distance`+`risk_r`+`quantity` hint), `#1 → [EXIT]` (bare), `#2+ → []`. It is ledger-blind (holds no handler/broker/tracker — MM7C C3) and ignores the bar's prices, emitting on call index for maximal determinism (MM7C C4).

---

## 2. Runtime path exercised

The full spine, through real components (driver evidence in parentheses):

```
SyntheticBuyExitSource.on_bar #0 → [BUY]
  └─ LoopDriver._dispatch_signals (driver.py:590-631) routes in list order
       └─ ExecutionHandler.process_signal(BUY, bar.close=2500)  (handler.py:432)
            ├─ signal_id auto-derived sha256 (handler.py:447-449)
            ├─ idempotency lock (handler.py:452-455)
            ├─ risk fields read — clean path, no warn-default (handler.py:457-482)
            ├─ instrument = Equity (canonicalize→None; parse) (handler.py:581-583)
            ├─ quantity = hint 50, handler-bounded (handler.py:594)
            ├─ order_tracker.add_order → ORDERS row (handler.py:629)
            └─ PaperBroker.place_order → synth FillEvent → _handle_broker_fill (handler.py:638-657)
                 ├─ order_tracker.process_fill → FILLS row (handler.py:325)
                 ├─ position_tracker.update_from_fill → LONG 50 (handler.py:326)
                 └─ canonicalize_symbol(equity)→None → position left legacy (handler.py:338-341)
SyntheticBuyExitSource.on_bar #1 → [EXIT]
  └─ process_signal(EXIT, 2500): current_position LONG → SELL full 50 (handler.py:586-591)
       └─ fill → position FLAT
```

The **restart + gate** path (driver `run()`): `RECOVERY_STARTED`/`RECOVERY_COMPLETED` (reuse, never re-restore — ADR-001, `driver.py:347-351`) → `_check_master_readiness` (equity ⇒ not applicable, `:383-386`) → `_canonicalize_restored_ledger` (equity carve-out no-op, `:439-442`) → `_reconcile_ledger` (`:462-476`) → PASS→RUNNING or FAIL→`abort_startup`→STOPPED.

---

## 3. Persistence artifacts observed

**SQLite `execution.db`** (canonical execution truth, ADR-001) — asserted via `order_repo`/`fill_repo`:
- `orders` — **2 rows**: BUY then SELL (the EXIT, handler-resolved), each qty 50.
- `fills` — **2 rows**: entry + exit, both @ `bar.close` (2500).
- `positions` — write-on-update snapshot; net **FLAT** after the round-trip (`position_tracker.get_position(EQUITY).side is FLAT`).

**DuckDB `trading.db`** (audit projection) — `save_trade`/`update_trade_exit` are *attempted* and gracefully degrade in the tmp sandbox (the tmp `trading.db` lacks the `trades` schema, so the write is swallowed by `_handle_broker_fill`'s try/except — logged "no such table: trades"). This is a **tmp-isolation artifact, not a wiring defect**: it occurs *after* `process_fill`/`update_from_fill`, so the canonical `execution.db` persistence is unaffected. The proof asserts on `execution.db` (the source of truth), exactly as MM7D §5 recommended.

**Journal `runtime_events.jsonl`** — `STARTUP, RECOVERY_STARTED, RECOVERY_COMPLETED, RECONCILIATION_PASS, RUNNING, STOPPING, STOPPED` on a clean run; `RECONCILIATION_FAIL` (no RUNNING) on a divergent book.

---

## 4. Restore proof

Test 4: handler #1 runs the BUY→EXIT round-trip; a **fresh** handler #2 constructed on the **same** `execution.db` (`load_db_state=True`) restores at construction — `order_repo.get_all()` and `fill_repo.get_all()` both return 2 rows, and the derived BUY `signal_id` is present in handler #2's restored `_seen_signals`. Re-emitting the recorded BUY (same symbol/strategy/timestamp) then raises `ExecutionRuleError` (idempotency, `rules.py:17`). The driver reuses recovery and never re-restores (ADR-001).

---

## 5. Reconciliation proof

Both verdict paths, with the **real** `ReconciliationEngine`:
- **PASS (5a):** establish an open long (BUY-only, `max_bars=1`); restart; broker book `[{EQUITY, 50, LONG}]` matches the restored ledger → no alert → `RECONCILIATION_PASS` → RUNNING → STOPPED.
- **FAIL (5b):** same restored long, broker book `[{EQUITY, 30, LONG}]` → `QUANTITY_MISMATCH` → `RECONCILIATION_FAIL` journaled, `abort_startup`, **no RUNNING**, `bars_processed == 0` (loop never ran), and a **critical** alert — a loud refusal, distinct from the silent W3 defect (MM7A T3).

Each gate run writes its own journal file so the assertion reads that run's outcome, not the establish run's.

---

## 6. Determinism proof

Test 7: two independent runs (separate tmp roots, fresh source/handler each) produce an **identical emitted signal stream** (`source.emitted` — `[("BUY",t0),("EXIT",t1)]` both) and an **identical ledger projection** — `(symbol, side, quantity, signal_id)` per order and `(symbol, side, quantity, price)` per fill. Random UUIDs (`correlation_id`/`fill_id`) are deliberately excluded; everything decision-relevant is bit-stable because the source keys on call index and `bar.timestamp`, never wall-clock (MM7C C4; `current_price` is always `bar.close`, ADR-003).

---

## 7. Why a production SignalSource was NOT required

Because the goal is **wiring validation, not strategy.** The MM7D.1 brief and MM7D §0/§7 both mandate proving the spine *without* landing a production `SignalSource` or entry script. A test-local source is sufficient and strictly better here:

1. **It proves exactly what's in question** — that signals flowing through `LoopDriver → ExecutionHandler → PaperBroker → persistence → restore → reconciliation` produce the right artifacts. Nothing about that requires the source to be production-placed.
2. **It keeps the MM7A T1 tripwire honest** — T1 must flip only when a *real production entry script* lands (MM7E). A production source/script now would either trip T1 prematurely or force me to weaken it. Test 8 asserts the proof stays under `tests/` and no `scripts/` module builds a `LoopDriver`.
3. **It avoids importing decisions that don't belong to this slice** — a production source forces choices (where it lives, how it's configured, its chain provider for the derivative path) that are MM7E's, and the derivative path drags in F4. The characterization did not prove production placement is needed; per the "avoid new abstractions unless characterization proves them" rule, none was added.

**Conclusion:** the runtime is no longer "wired and tested in pieces" — it **executes a known order and closes it end-to-end**, with restore and reconciliation proven on both verdict paths, deterministically, with zero market-data/chain/alpha surface. The next slice is MM7E (production entry script under `scripts/`, which flips MM7A T1 and reuses these proven parts); the Tier-B canonicalization extension remains gated on F4 + the symbol-shape decision.

---

## 8. Stop condition

Synthetic wiring proof complete. Tests green (493 passing, 0 failing). Report written. Commit created. **Did NOT:** build a production strategy/entry script/broker adapter; start MM7E, F3, F4, or 4C.7. NiftyShield not referenced beyond the abandonment note.

*Filed under the G1 / MM7A / MM7B / MM7C / MM7D review-first, characterize-before-change discipline.*
