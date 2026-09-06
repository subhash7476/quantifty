# G1_WAVE4A3_O2_IMPLEMENTATION_REPORT.md

**Type:** Gate G1 — Wave 4A.3 **O2 (forward option EXIT) migration**. Production change (handler else branch) + the one intended characterization update + report + commit. **InstrumentParser, persistence, broker payloads, #6/#7, the Wave-5 guard NOT touched.**
**Date:** 2026-06-11
**Scope (locked):** migrate **O2 only** — the non-option-mode instrument-construction `else` branch in `ExecutionHandler.process_signal` (`core/execution/handler.py:557`). Route a derivative EXIT symbol through `canonical_restore.canonicalize_symbol` (canonical derivation) **before** the `InstrumentParser.parse` fallback, so an option-shaped EXIT derives a master-lot `Option` instead of the parser's resolver-blind `Option(lot_size=1)`. Per `docs/reports/G1_WAVE4_OPTION_PATH_REVIEW.md` §3 (O2) / §6 step 3, and `docs/reports/G1_WAVE4A1_CHARACTERIZATION_REPORT.md` §4 (the M4 intended-change note).

**Result:** `pytest -q` → **415 passed, 0 failing**. **Exactly one** assertion update — M4's EXIT `lot_size 1 → 65` (the single allowed intended change, justified + payload-proven below). O1 (Wave 4A.2) is already COMPLETE; with O2 closed both forward option identity sites now derive from the canonical master. G1 stays OPEN (#6/#7 + the Wave-5 guard remain).

---

## 1 — Files changed

| File | Change | LOC |
|---|---|---|
| `core/execution/handler.py` | O2 migration: the `else` branch now calls `canonicalize_symbol` (futures **and** options) before `InstrumentParser.parse`, replacing the futures-only `resolve_future` call. | +14 / −3 |
| `tests/execution/test_g1_wave4a1_option_characterization.py` | M4 updated to the post-O2 reality: EXIT lot is the master lot (65), renamed `test_m4_option_exit_derives_master_lot_and_position_quantity`, with an added broker-payload proof. | +21 / −13 |
| `docs/reports/G1_WAVE4A3_O2_IMPLEMENTATION_REPORT.md` | This report. | new |

`instrument_parser.py`, the persistence layer / ledger schema, the broker bridge, the selector (O1), `#6`/`#7`, and the Wave-5 guard are **untouched**.

---

## 2 — Derivation mechanism

**Before (O2 = "parse-built, resolver-blind"):** an EXIT carrying the option symbol fails the option-mode guard (`execution_mode=="option" ∧ signal_type != EXIT` is False for an EXIT), falls to the `else` branch, where `resolve_future` misses on the option-shaped symbol (it is not `…FUT`), so `InstrumentParser.parse(option_symbol)` builds `Option(lot_size=1)` — resolver-blind, the master never consulted.

**After (O2 = "canonical-derived"):** the `else` branch derives through the existing restore primitive:

```text
else:
    derived = canonicalize_symbol(signal.symbol, signal.timestamp)   # future-then-option
    instrument = derived if derived is not None else InstrumentParser.parse(signal.symbol)
```

`canonicalize_symbol` (`core/execution/canonical_restore.py`) tries `resolve_future` first (futures-shaped → `Future`, **unchanged** from Wave 2 #1) then `_resolve_option` (option-shaped → master-lot `Option`). The two derivation properties:

1. **Futures unchanged.** `canonicalize_symbol` calls `resolve_future` first and returns it when non-None — byte-for-byte the prior behavior. The Wave-2A futures tripwire (`test_build_order_futures_currently_falls_back_to_equity`, `instrument_type == FUTURE`) stays green.
2. **Option EXIT now master-derived.** An option-shaped EXIT symbol resolves to `Option(symbol=signal.symbol, …, lot_size=ci.lot_size)`. The underlying token used by `_resolve_option` is the regex alpha-prefix `"NIFTY"`; `normalize_underlying("NIFTY") == normalize_underlying("NSE_INDEX|Nifty 50") == "NIFTY"` (`core/instruments/identity.py`), so the EXIT resolves the **same** master row the ENTRY selector resolved → lot 65, closing the ENTRY/EXIT identity asymmetry.
3. **Equity / unresolved unchanged.** A symbol matching neither regex (equity `NSE_EQ|INE…`, or an unresolved derivative) → `canonicalize_symbol` returns None → `InstrumentParser.parse` exactly as before. Equity tripwire (`test_build_order_equity_non_option_branch`) stays green.
4. **CanonicalInstrument stays internal.** `canonicalize_symbol` reads only the CI's economic facts (lot/expiry/underlying) and returns a legacy `Future`/`Option`; the CI never reaches `NormalizedOrder`, persistence, or the broker payload (G1 / 4C.7).

---

## 3 — Proof: symbol unchanged

- **Mechanism:** `canonicalize_symbol` and its `_resolve_option`/`resolve_future` derivations construct the legacy instrument with `symbol=symbol` — the **input** `signal.symbol` string, never `ci.display_symbol` / the master `tradingsymbol`. `grep display_symbol|tradingsymbol core/execution/handler.py core/execution/canonical_restore.py` → **NONE**.
- **Behavioral pins (green):**
  - M4 EXIT `exit_order.symbol == "NIFTY16JUN2622500CE"` (byte-identical to the ENTRY symbol).
  - M4 broker `broker.received[-1].symbol == "NIFTY16JUN2622500CE"`.
  - Futures `order.symbol == "NIFTY26JUNFUT"` and equity `order.symbol == "RELIANCE"` (Wave-2A) unchanged.

---

## 4 — Proof: broker payload unchanged (the one allowed lot change is sizing-neutral)

The single intended change is the EXIT instrument's `lot_size` byte (1 → 65). The review requires proof this does **not** perturb the broker payload, because EXIT sizing is position-sourced, not lot-sourced:

- **Quantity is position-sourced.** For an EXIT, `quantity = current_position.quantity` (`handler.py:568`) — never multiplied by `instrument.lot_size`. M4 asserts `exit_order.quantity == 75` AND `broker.received[-1].quantity == 75` (the open position quantity), unchanged by the lot derivation.
- **Side / order_type / symbol unchanged.** M4 asserts `side == SELL` (closing the LONG), `order_type == MARKET`, `symbol == "NIFTY16JUN2622500CE"`, `instrument_type == OPTION` — all green, all identical to the pre-O2 bytes.
- **The lot byte never reaches the wire on EXIT.** `instrument.lot_size` is an in-memory identity attribute; the persisted `orders` row and the broker payload carry the absolute `quantity` (75), not the lot. So the 1→65 change is an identity correction with **zero** payload effect — exactly the "intended change accompanied by proof that EXIT quantity stays current_position.quantity" the review §6/§4 mandated.

**M4 assertion delta (the only assertion change in this wave):**

| Assertion | Before (pre-O2) | After (post-O2) | Justification |
|---|---|---|---|
| `exit_order.instrument.lot_size` | `== 1` | `== NIFTY_MASTER_LOT` (65) | O2 derivation closes the resolver-blind gap; sizing-neutral (qty position-sourced). |
| ENTRY vs EXIT lot | `65 != 1` (differ) | `65 == 65` (agree) | The identity asymmetry O2 was created to close. |

Every other M4 assertion (symbol/side/quantity/order_type/instrument_type + the new broker-payload proof) is unchanged and green.

---

## 5 — Proof: persistence unchanged

- **Ledger schema untouched.** The migration edits only the in-memory instrument-derivation locus; no column is added/removed. `test_ledger_schema_persists_only_symbol_identity` (restore suite) — `orders`/`fills`/`positions` carry no structural-identity column — stays green.
- **Restore path untouched.** Restore re-derives identity via `order_repository.py:60` / `position_tracker.py:31` (`InstrumentParser.parse`), a different site this wave does not edit. The restore characterizations (H1/H2 — futures→Equity, option lot→1 on restore) stay green: the forward EXIT lot change does not alter what the persisted symbol-only ledger replays. The forward option **ENTRY** persist/restore round-trip (M6) is unchanged and green.

---

## 6 — Test results

```text
pytest tests/execution/test_g1_wave4a1_option_characterization.py -q   ->  6 passed
pytest tests/execution -q                                              -> 51 passed
pytest -q                                                              -> 415 passed, 0 failing
```

Pre-O2 (after O1): 415 passed. Mid-migration (production change, M4 not yet updated): **1 failed** — M4 only, `assert 65 == 1` (the predicted, isolated flip — the captured failure shows the derived `Option(... lot_size=65)` with the byte-identical symbol). Post-update: **415 passed, 0 failing**. No other test moved — confirming the change is surgically scoped to the option-EXIT identity.

---

## Stop

O2 migration complete, full suite green (415/0), report written, commit created. Both forward option identity sites (O1 selector ENTRY, O2 EXIT) now derive from the canonical master. **NOT touched:** `#6`/`#7`, the Wave-5 AST closure guard, persistence, the broker bridge, `InstrumentParser`. G1 stays OPEN (#6/#7 + Wave-5 guard remain). The option path remains **not-live** (F4 lot verification + the absent F&O entry script are downstream preconditions, unchanged by this wave).
