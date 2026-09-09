# G1_WAVE2_IMPLEMENTATION_REPORT.md

**Type:** Gate G1 — **Wave 2 implementation report. Migration Target #1 ONLY (Future Resolution Path).**
**Date:** 2026-06-09
**Parent plan:** `SOLE_IDENTITY_PATH_REVIEW.md` (Section 5, Wave 2) · `G1_WAVE1_REPORT.md` · `G1_WAVE2A_BROKER_PAYLOAD_REVIEW.md`
**Scope (locked):** Migrate site **#1** (`handler.process_signal` non-option branch, `handler.py:513`) from `InstrumentParser.parse` (which mistypes futures as Equity — F-PARSE-1) to `resolve_future → CanonicalInstrument → derive legacy Future`. **No other site touched.** No commits.
**Outcome:** F-PARSE-1 corrected. A futures-style symbol now builds a `Future` (canonical-sourced lot/expiry) while the broker-facing `symbol`/`side`/`quantity`/`order_type` stay byte-identical. **379 tests passing, 0 failing.**

---

## 1 — Files changed

| File | Change | Lines |
|---|---|---|
| `core/execution/futures.py` | **NEW.** Module-level `resolve_future(symbol, timestamp, resolver=None) -> Optional[Future]`. Regex-detects an NSE monthly future symbol, resolves a `CanonicalInstrument` via `InstrumentResolver.resolve_future`, and derives a legacy `Future` from it. Canonical stays internal. | whole file (~57) |
| `core/execution/handler.py` | **EDIT (#1 site only).** `process_signal` non-option `else` branch now calls `resolve_future(...)`; falls through to the unchanged `InstrumentParser.parse(...)` when the symbol is not a future. | `513` (was 1 line, now 4) |
| `tests/execution/test_g1_characterization.py` | **EDIT.** `test_build_order_futures_currently_falls_back_to_equity`: assertion corrected `EQUITY → FUTURE`; docstring/comments updated. Function name and every symbol/side/quantity/order_type assertion preserved. | 144–168 |
| `tests/execution/test_futures_resolution.py` | **NEW.** 3 unit tests for `resolve_future` (non-future → None; master-present canonical lot/expiry; master-absent ADR-003 fallback). | whole file (~50) |

**Untouched (verified):** `InstrumentParser` (so #2 `process_group_signal:621` is unchanged), `order_factory.py` (#5 dead), `order_models.py` (#10 dead branch), selector (#4), `_check_greek_limits` (#3), `UpstoxAdapter`, `PaperBroker`, reconciliation, persistence schemas, restore (`order_repository.get_all` / `_replay_state`), `instrument_key` routing, MM.7.

---

## 2 — Exact migration path

**Before (`handler.py:512-513`):**
```python
else:
    instrument = InstrumentParser.parse(signal.symbol)
```
`InstrumentParser.parse` has only an Option regex + Equity fallback (`instrument_parser.py:8-46`), so `NIFTY26JUNFUT` (no Option match) → `Equity("NIFTY26JUNFUT")`. **F-PARSE-1.**

**After (`handler.py:512-515`):**
```python
else:
    from core.execution.futures import resolve_future
    future = resolve_future(signal.symbol, signal.timestamp)
    instrument = future if future is not None else InstrumentParser.parse(signal.symbol)
```

**`resolve_future` pipeline (`core/execution/futures.py`):**
```
signal.symbol ──FUT regex──► (underlying, yy, mon)
              │ no match → return None  (equity/option fall through to parse, unchanged)
              ▼
InstrumentResolver.resolve_future(underlying, as_of=signal.timestamp.date())
              ▼
CanonicalInstrument  (internal only: read .underlying, .expiry, .lot_size; discard)
              ▼
Future(symbol=original_symbol, underlying, expiry, multiplier=lot_size)
              ▼
NormalizedOrder(instrument=Future, …)   ← symbol/side/quantity/order_type unchanged
```

- **Detection** keys on the `…FUT` symbol shape, not on master presence — so the FUTURE *type* is deterministic (ADR-003). When the master is absent (`resolve_future` → `None`), a `Future` is still derived from the symbol-parsed month with `multiplier=1.0`, so the type never flips on DB presence.
- **Canonical containment:** `ci` is read for three economic facts and then dropped; it is never persisted, never sent to the broker, never placed on `NormalizedOrder`. The object that flows downstream is the legacy `Future`.
- **Equity carve-out preserved:** `RELIANCE` does not match the FUT regex → `resolve_future` returns `None` → unchanged `InstrumentParser.parse` → `Equity`. Equity remains legacy-by-design (ISIN-less symbol, out of F&O scope).

---

## 3 — Characterization failures encountered

Implementation applied first, then the suite run to **prove the failure is caused by correcting F-PARSE-1** (one red, six green):

```
tests/execution/test_g1_characterization.py
  test_build_order_equity_non_option_branch ........ PASSED
  test_build_order_futures_currently_falls_back_to_equity ... FAILED
  test_build_order_option_via_selector_branch ...... PASSED
  test_persist_order_and_fill_rows ................. PASSED
  test_restore_round_trip .......................... PASSED
  test_reconcile_restored_ledger_against_broker .... PASSED
  test_real_execution_db_untouched ................. PASSED
  → 1 failed, 6 passed
```

The single failure, verbatim:
```
assert order.instrument_type == InstrumentType.EQUITY
E  AssertionError: assert <InstrumentType.FUTURE: 'FUTURE'> == <InstrumentType.EQUITY: 'EQUITY'>
   where instrument = Future(symbol='NIFTY26JUNFUT', type=FUTURE, multiplier=65.0,
                             underlying='NIFTY', expiry=date(2026, 6, 30))
```

---

## 4 — Why each failure occurred

**One failure, exactly the intended tripwire.** Before line `assert order.symbol == FUTURES_SYMBOL` passed (payload identity preserved); the next line — `assert order.instrument_type == InstrumentType.EQUITY` — failed because #1 flipped the derived type to `FUTURE`. That is the corrected behavior, not a regression.

**Cleanliness of the failure (verified before running):** the test fails on the `instrument_type` assertion and nothing else — no error during persist or fill. `OrderRepository.save` (`order_repository.py:19-37`) writes only common fields (`symbol, side, quantity, order_type, strategy_id, signal_id, timestamp, metadata`); there is no `instrument_type` column and no option/equity-specific attribute read, so a `Future`-backed order (which lacks `lot_size`/`strike`) persists without a missing-attribute error. The fill write reads only `fill.symbol/quantity/price/side/fee`. (The `no such table: trades` stderr line is pre-existing and harmless — logged-and-swallowed in `_handle_broker_fill` for *every* test, equity included; rows still persist, confirmed by the green persist test.)

**No collateral failures:** the other six tests use `RELIANCE` (equity, FUT-regex miss → unchanged) or the option-via-selector path (#4, untouched), or exercise persist/restore/reconcile over the equity order — none of which `resolve_future` alters.

---

## 5 — Test updates performed

1. **`test_build_order_futures_currently_falls_back_to_equity`** (name **retained** — it is the named artifact the task pinned to flip):
   - `assert order.instrument_type == InstrumentType.EQUITY` → `== InstrumentType.FUTURE`.
   - Docstring + inline comments rewritten to describe the post-migration reality.
   - **Preserved exactly:** `order.symbol == FUTURES_SYMBOL`, `order.side == OrderSide.BUY`, `order.quantity == 50`, `order.order_type == OrderType.MARKET`, `broker.received[0].symbol == FUTURES_SYMBOL`. The broker-facing payload assertions are byte-for-byte unchanged.
   - *Note on the name:* `…currently_falls_back_to_equity` is now historically inaccurate; it is kept deliberately so the named-test artifact survives the migration (a rename would read as "the named test is gone"). Accuracy is carried by the docstring.

2. **`tests/execution/test_futures_resolution.py`** (new, 3 tests) — covers the two branches the characterization suite does not: equity/option → `None` passthrough, and the master-absent FUTURE derivation (ADR-003).

---

## 6 — Before/after order-build examples

**Futures signal `NIFTY26JUNFUT`, qty 50, BUY, as_of 2026-06-09:**

| Field | BEFORE (#1 not applied) | AFTER (#1 applied) |
|---|---|---|
| `order.symbol` | `"NIFTY26JUNFUT"` | `"NIFTY26JUNFUT"` *(unchanged)* |
| `order.instrument_type` | `EQUITY` *(mistype — F-PARSE-1)* | **`FUTURE`** |
| `order.instrument` | `Equity("NIFTY26JUNFUT")` | `Future(symbol='NIFTY26JUNFUT', underlying='NIFTY', expiry=2026-06-30, multiplier=65.0)` |
| `order.side` | `BUY` | `BUY` *(unchanged)* |
| `order.quantity` | `50` | `50` *(unchanged)* |
| `order.order_type` | `MARKET` | `MARKET` *(unchanged)* |
| broker received `.symbol` | `"NIFTY26JUNFUT"` | `"NIFTY26JUNFUT"` *(unchanged)* |

**Equity signal `RELIANCE`, qty 50, BUY:** identical before/after — FUT regex miss → `InstrumentParser.parse` → `Equity("RELIANCE")`, type `EQUITY`. (Proven green by `test_build_order_equity_non_option_branch`.)

**Option signal (selector branch, #4):** untouched — `OptionsContractSelector` still builds the `Option`. (Proven green by `test_build_order_option_via_selector_branch`: `NIFTY16JUN2622500CE`, lot 65.)

---

## 7 — Confirmation: broker payload contract unchanged

The identity-bearing fields every broker adapter reads (`G1_WAVE2A` §4, invariants I1–I4) are **byte-identical** for the futures order:
- **I1 `order.symbol`** = `"NIFTY26JUNFUT"` — preserved verbatim (the `Future` is constructed with `symbol=original_symbol`). Pinned green by the characterization test (`order.symbol` **and** `broker.received[0].symbol`).
- **I2 `order.side`** = `BUY`, **I3 `order.quantity`** = `50`, **I4 `order.order_type`** = `MARKET` — all unchanged (this migration touches only instrument construction, not side/qty/type).
- **I5 `product`** — never entered `NormalizedOrder`; canonical `instrument_key`/`product` are not read by any payload (the G1/4C.7 line stays uncrossed; `ci` is discarded after reading 3 economic facts).
- **I6 derived `instrument_type` value** = `FUTURE` — this is the *intended* correction (consumed by persistence/greeks dispatch, not the wire). It is a value change for futures orders only; see §8.

The only broker that accepts the handler's output (`PaperBroker`, per `G1_WAVE2A` §4) received the same `NormalizedOrder` object the handler returned (`sent is order` style assertion green). **No wire-facing byte changed.**

---

## 8 — Confirmation: persistence contract unchanged

`OrderRepository.save` (`order_repository.py:19-37`) writes a fixed column set: `correlation_id, symbol, side, quantity, order_type, strategy_id, signal_id, timestamp, metadata`. **There is no `instrument_type` column.** Therefore:
- **Format/shape is byte-stable** — same INSERT, same columns, same serialization. A `Future`-backed order persists exactly like any other order (only the in-memory instrument object differs; no `Future`-specific attribute is serialized).
- The order-row **value** for `symbol` is `"NIFTY26JUNFUT"` (unchanged). `instrument_type` is not persisted at all, so the FUTURE correction has **zero** persistence footprint.

This is a **value** distinction, not a **format** change: the persisted schema and serialization are unchanged; the only thing the migration alters is the in-memory `instrument_type` (an un-persisted derived view). Proven green by `test_persist_order_and_fill_rows` (over the equity order; the futures order persists through the same unchanged `save`).

---

## 9 — Confirmation: restore contract unchanged

Restore is **out of scope (Target #2)** and untouched. `OrderRepository.get_all` (`order_repository.py:46-78`) still rebuilds instruments via `InstrumentParser.parse(row[1])` at handler construction — the legacy-at-construction behavior locked by `SOLE_IDENTITY_PATH_REVIEW.md` §3 (Option B). No restore code was modified. Proven green by `test_restore_round_trip`.

*(Side note, not a change:* a restored futures order would re-`parse` to `Equity` on reload, exactly as before this wave — the restore-path canonicalization is Wave 4, deliberately not done here. This wave does not alter that.)*

---

## 10 — Confirmation: reconciliation contract unchanged

`ReconciliationEngine` and its inputs were not touched. Reconciliation matches on `symbol`/`quantity`/`side` derived from the position tracker, which is fed by `_handle_broker_fill` → `parse(symbol)` (unchanged, #6/#7 are Wave 3). The futures order's `symbol` is preserved, so any reconciliation keyed on it is unaffected. Proven green by `test_reconcile_restored_ledger_against_broker` (PASS + `QUANTITY_MISMATCH`).

---

## Validation

```
python -m pytest tests/execution/test_g1_characterization.py -q   → 7 passed
python -m pytest tests/execution tests/instruments -q             → 100 passed
python -m pytest tests/execution/test_futures_resolution.py -q    → 3 passed
python -m pytest tests/ -q                                        → 379 passed
```

| Metric | Count |
|---|---|
| Passing (full suite) | **379** |
| Failing | **0** |
| Newly added tests | **3** (`test_futures_resolution.py`) |
| Characterization tests updated | **1** (`test_build_order_futures_currently_falls_back_to_equity`, assertion `EQUITY → FUTURE`) |
| Baseline before Wave 2 | 376 passing (369+ reported; characterization 7/7 from Wave 2A) |

---

## Scope adherence

**Implemented:** #1 only (`handler.py:513` non-option branch → `resolve_future`).
**NOT touched (verified):** #2 (`process_group_signal:621`, still `InstrumentParser.parse`), #4 (selector), #3 (`_check_greek_limits`), #5/#10 (dead), `UpstoxAdapter`, `PaperBroker`, reconciliation, persistence schemas, SQLite format, `instrument_key` routing, MM.7, F3, F4. No opportunistic cleanup, no dead-code removal, no refactor outside #1. No commits.

**Gate status:** G1 remains **OPEN**. This closes Wave 2 site #1 only; #2/#4 (Wave 2 remainder), Wave 3, and Wave 4 (restore, Option B) remain. The Wave 5 guard test (closure proof) is not in scope here.

**STOP** — #1 migration implemented, characterization test updated, report written. Review report only; no commits.
