# G1_WAVE4A1_CHARACTERIZATION_REPORT.md

**Type:** Gate G1 — Wave 4A.1 **Option-Path Characterization Expansion**. **Tests + report only; NO production code, NO migration, NO canonicalization edit, NO KB sync.**
**Date:** 2026-06-11
**Scope (locked):** add the missing Wave-4 characterization net (M1–M6) for the live forward F&O **option** order-build path, all **green on current code**, encoding today's reality exactly. Driven by `docs/reports/G1_WAVE4_OPTION_PATH_REVIEW.md` §4 + `docs/reports/SOLE_IDENTITY_PATH_REVIEW.md` §2/§4.
**Deliverable file added:** `tests/execution/test_g1_wave4a1_option_characterization.py` (6 tests).

**Result:** `pytest tests/execution -q` → **51 passed**. `pytest -q` → **415 passed, 0 failing** (was 409; +6 new). **Zero production change, zero assertion update.** No migration started.

---

## 1 — Tests added

All six live in `tests/execution/test_g1_wave4a1_option_characterization.py`, on the same harness as the Wave-2A net (`test_g1_characterization.py`): a **real** `ExecutionHandler` wired to a spy `PaperBroker` over an **isolated** tmp `ExecutionStore` + `DatabaseManager(data_root=tmp)`. `FIXED_DT = 2026-06-09`. Every asserted literal is an **observed** byte (recorded by running the same selector/parser the handler uses against the present master), not an idealized value.

| Test | Pins (observed, current code) |
|---|---|
| **M1** `test_m1_option_build_master_absent_falls_back_to_index_lot` | Handler-level NIFTY BUY option, **master ABSENT** (selector's internally-constructed `InstrumentResolver` monkeypatched to an absent DB). Symbol `NIFTY16JUN2622500CE` (byte-identical to the master-present case), `instrument_type==OPTION`, `lot_size==75` (`INDEX_LOT_SIZES` fallback, **not** master 65), side BUY, qty 75, MARKET. Broker payload symbol matches. |
| **M2** `test_m2_banknifty_default_option_build_falls_back_to_index_lot` | Handler-level **BANKNIFTY** BUY option, default path. Symbol `BANKNIFTY17JUN2652000CE`, strike `52000.0` (step-100 ATM), expiry `2026-06-17` with `weekday()==2` (Wednesday), `OptionType.CALL`, `lot_size==35` (fallback — the 2026-06-09 snapshot carries only **monthly** BANKNIFTY, so the computed **weekly** contract is unresolved), side BUY, qty 30, MARKET. |
| **M3** `test_m3_sell_signal_builds_put_option` | Handler-level NIFTY **SELL→PUT**. Symbol `NIFTY16JUN2622500PE` (CE→PE suffix flip), `option_type==PUT`, `lot_size==65` (master-resolved), `side==SELL`, qty 75, MARKET. |
| **M4** `test_m4_option_exit_uses_parser_lot_one_and_position_quantity` | Option **EXIT identity (O2)**. Open a LONG option via the selector ENTRY path (position keyed by `NIFTY16JUN2622500CE`), then EXIT carrying that **option symbol** → `else` branch → `resolve_future` (regex miss) → `InstrumentParser.parse` → `Option(lot_size==1)`, resolver-blind. `instrument_type==OPTION`, `side==SELL`, `quantity==75` (= `current_position.quantity`, **position-sourced, lot-independent**), MARKET. Explicitly asserts ENTRY lot (65) ≠ EXIT lot (1) — proof the two legs take different identity paths today. |
| **M5** `test_m5_forward_option_order_carries_legacy_option_not_canonical` | **CanonicalInstrument containment tripwire.** `NormalizedOrder.instrument` `isinstance Option` and **not** `CanonicalInstrument`; no canonical-only attribute (`instrument_key`, `product`, `asset_class`) present on the payload object; `order.symbol == NIFTY16JUN2622500CE` (selector-computed, not a master `display_symbol`); broker received the **same** instrument object. |
| **M6** `test_m6_option_order_persist_and_restore_round_trip` | **Forward option order persist + restore round-trip.** Handler A builds + persists the option order; the `orders` row carries `symbol==NIFTY16JUN2622500CE`, `BUY`, `75.0`, `MARKET`. Handler B (`load_db_state=True`) restores from the same ledger: restored order `symbol`/`side`/`quantity`/`instrument_type` match verbatim; `position_tracker.net_quantity(NIFTY16JUN2622500CE)==75.0` (rebuilt from the replayed BUY fill). |

---

## 2 — Behaviors pinned

- **Master-absent determinism (ADR-003) at the handler level (M1).** Previously only the *selector unit* pinned master-absent; nothing pinned it through the handler order-build — the exact surface O1 edits. The option **type never flips on DB presence**; the symbol is byte-identical to the master-present case; only the lot source changes (master 65 → fallback 75).
- **Non-NIFTY structural axis (M2).** BANKNIFTY short name, strike step 100, default weekly **Wednesday** expiry, and the current **fallback** lot 35 for the (unresolved) weekly contract.
- **SELL→PUT branch (M3).** `selector.py:97` `option_type` selection, untested at the handler level until now.
- **O2 EXIT identity (M4).** The EXIT leg's `parse`-built `Option(lot=1)` and that EXIT sizing is **position-sourced** (so the lot-1 drift does not mis-size the close today). This is the characterization that makes the O2 migration provably behavior-preserving.
- **G1/4C.7 boundary on the forward option path (M5).** The order carries a legacy `Option`, never a `CanonicalInstrument`; no canonical field leaks into the broker payload; the symbol stays selector-computed.
- **Option persistence/restore parity (M6).** The Section-4 persist/restore net used an **equity** order; the option payload round-trip is now pinned specifically.

---

## 3 — Coverage gaps closed

Before this wave the handler-level option order-build had **one** characterization (`test_build_order_option_via_selector_branch`), exercising only **NIFTY / BUY→CALL / master-present**. Closed:

| Axis | Before | After |
|---|---|---|
| Master **absent** (handler-level) | unpinned (selector-unit only) | **M1** |
| Non-NIFTY underlying (**BANKNIFTY**, step-100, Wed expiry) | unpinned | **M2** |
| **SELL→PUT** option_type branch | unpinned | **M3** |
| Option **EXIT** identity (O2, lot-1, position-sourced qty) | unpinned | **M4** |
| CanonicalInstrument **containment** (forward option) | unpinned | **M5** |
| Option **persist+restore** round-trip | equity only | **M6** |

Net: the option path now has the same axis breadth (master present/absent · BUY/SELL · NIFTY/BANKNIFTY · ENTRY/EXIT · containment · round-trip) the review §4 requires as the precondition for the #4 migration.

---

## 4 — Remaining migration risks

1. **O1 master-absent determinism (HIGH, now netted).** The riskiest #4 property — the derived type/identity must not flip on DB presence. **M1** now pins it through the handler; a migration that changes the master-absent lot/type/symbol goes red.
2. **O2 EXIT identity (MED, now netted).** Genuine Section-6 criterion-#2 gap, but EXIT sizing is position-sourced (lot-independent), so it is identity-only, not a sizing risk today. **M4** pins both the current lot-1 reality and the position-sourced quantity. *Migration note:* if O2 routes EXIT through `canonicalize_symbol`, M4's `lot_size==1` assertion may become the master lot — that is the **one** allowed intended change, and it must be accompanied by proof that EXIT `quantity` stays `current_position.quantity` (broker payload unaffected). Every other M4 assertion must stay green.
3. **Payload byte drift (MED).** Any accidental use of `ci.display_symbol` / master `tradingsymbol` crosses into 4C.7. Netted by **M5** + the existing byte-for-byte literal in `test_build_order_option_via_selector_branch`.
4. **BANKNIFTY weekly is currently fallback-sized (LOW, documented).** The 2026-06-09 snapshot carries only **monthly** BANKNIFTY; the computed **weekly** contract is unresolved, so the default BANKNIFTY option path uses the **fallback lot 35**, not the master's 30. M2 pins this as today's reality. The master-resolved monthly lot (30) is reachable only via a `policy["expiry_date"]` override — see finding below — and is therefore **not** on the default live path.
5. **Latent finding (out of #4 scope): `option_policy["expiry_date"]` breaks order persistence.** Passing a `date` object in `option_policy` flows into `strategy_metadata` and fails JSON serialization in `order_repository.save` (`TypeError: Object of type date is not JSON serializable`). This is why M2 pins the default (no-override) path. Not a #4 site; flag for a separate slice (the override path cannot currently persist an order). No fix in this wave.

**Expected-failure count for the #4 migration remains zero** (behavior-preserving DERIVE). M1–M6 plus the existing six must be green **before and after** the migration; a red is a signal the refactor changed a byte, to be re-examined, not re-asserted (the sole exception being the M4 EXIT-lot intended change noted above, justified and payload-proven).

---

## 5 — Validation

```text
pytest tests/execution/test_g1_wave4a1_option_characterization.py -q   ->  6 passed
pytest tests/execution -q                                              -> 51 passed
pytest -q                                                              -> 415 passed, 0 failing
```

No assertion updates caused by migration (no migration performed). No behavior changes. Baseline was 409; +6 new = 415.

---

## Stop

Tests green, report written, commit created. NOT started: `selector.py` edit, `handler.py` edit, O1 migration, O2 migration, #6/#7, Wave-5 guard. G1 stays OPEN.
