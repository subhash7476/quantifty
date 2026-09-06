# G1_WAVE3A_CHARACTERIZATION_REPORT.md

**Type:** Gate G1 — **Wave 3A. Restore characterization expansion. Tests + report ONLY; NO production code, NO restore/persistence/reconciliation/broker changes, NO canonical migration.**
**Date:** 2026-06-10
**Parent plan:** `SOLE_IDENTITY_PATH_REVIEW.md` (Option B locked) · `G1_WAVE3_RESTORE_REVIEW.md` (the defect survey this pins) · `G1_WAVE1_REPORT.md` · `G1_WAVE2A_BROKER_PAYLOAD_REVIEW.md` · `G1_WAVE2_IMPLEMENTATION_REPORT.md`
**Objective:** apply the F-PARSE-1 discipline to **H1 (Restore Identity Asymmetry)** and **H2 (Restored Option Lot Drift)** — pin current (defective) restore reality with green characterization tests *before* the Wave 3 migration changes it.
**Outcome:** 9 new characterization tests, all green on first run (they encode current behavior exactly). Full suite **379 → 388 passing, 0 failing**. The defects are now tripwired: the Wave 3 Option-B pass cannot land without deliberately flipping named assertions.

---

## 1 — Files reviewed (file:line, verified 2026-06-10)

| File | Evidence taken |
|---|---|
| `core/execution/handler.py:118-265` | `load_db_state=True` default (`:127`); `ExecutionStore()` built internally (`:145`); `_replay_state()` invoked at construction (`:186-187`); replay sequence — orders (`:224`), seen-signals (`:227-228`), fills → `order_tracker.process_fill` + `position_tracker.update_from_fill` (`:231-234`), group reconstruction (`:236-256`), `_trades_today` (`:258-261`) |
| `core/execution/handler.py:498-547` | forward order-build branches: option-via-selector (`:503-511`), `resolve_future` → `parse` fallback (`:512-515`, Wave 2 #1) |
| `core/execution/persistence/order_repository.py:46-78` | `get_all()` rebuilds every order's instrument via `InstrumentParser.parse(row[1])` (`:60`) — **site #8** |
| `core/execution/persistence/fill_repository.py:41-64` | `get_all()` returns `FillEvent(symbol=row[2], …)` — symbol string only, no instrument |
| `core/execution/persistence/position_repository.py:42-65` | `load_all()` exists (and parses, `:51`) but has **zero callers repo-wide** — #9 dead on restore |
| `core/execution/persistence/execution_store.py:24-63` | the three `CREATE TABLE`s — only `symbol` carries identity; no type/expiry/strike/lot/`instrument_key` column |
| `core/execution/position_tracker.py:27-32, 49-164` | `get_position` → `InstrumentParser.parse(symbol)` (`:31`, **site #7**); `update_from_fill` carries `pos.instrument` into the new `Position` (`:152-159`); snapshot write per fill (`:161-162`) |
| `core/execution/position_models.py:47` | `Position(symbol=…)` fallback also parses (site #6; not restore-driven) |
| `core/instruments/instrument_parser.py:8-46` | Option regex + Equity fallback only — **no Future branch**; `Option(lot_size=1, multiplier=1.0)` hardcoded (`:33-41`) |
| `core/execution/reconciliation.py:24-87` | `broker_map` keyed on raw `bp['symbol']` (`:43,54`); internal iteration over `_positions` symbol keys (`:57`); only `net_quantity` compared — no instrument field consulted |
| `core/execution/options/selector.py:105-123` | forward option lot is resolver-sourced (`ci.lot_size`, F4 = 65) with `INDEX_LOT_SIZES` fallback |
| `tests/execution/test_g1_characterization.py` | Wave 2A fixture pattern reused; confirms gaps 1–3 of `G1_WAVE3_RESTORE_REVIEW.md` §4 (no futures/option restore pins; round-trip asserts no `instrument_type`) |

## 2 — Restore-path map (proven, not assumed)

The required `persist → SQLite → restore → InstrumentParser.parse` chain holds for both futures and options:

```
FORWARD (handler A)
  futures: process_signal → resolve_future → Future            handler.py:512-515  (Wave 2 #1)
  option:  process_signal → OptionsContractSelector.select
           → Option(lot_size=ci.lot_size=65)                   handler.py:503-511, selector.py:108-121
        ↓ order persisted — symbol/side/qty/type/ids only      order_repository.py:19-37
        ↓ PaperBroker fill persisted — symbol string only      fill_repository.py:13-39
SQLite (data/execution.db schema)                              execution_store.py:24-63
  orders(correlation_id, symbol, side, quantity, order_type,
         strategy_id, signal_id, timestamp, metadata)          ← NO structural identity column
  fills(fill_id, order_id, symbol, quantity, price, side, fee, timestamp)
  positions(symbol, side, quantity, avg_price, timestamp)      ← written per fill, NEVER read back
RESTORE (handler B, at construction — BEFORE the MM.4 gate)
  ExecutionHandler.__init__(load_db_state=True)                handler.py:186-187
    _replay_state()                                            handler.py:219
      order_repo.get_all() → InstrumentParser.parse(row[1])    order_repository.py:60   ← site #8
        NIFTY26JUNFUT      → Equity   (no Future branch)       instrument_parser.py:46
        NIFTY16JUN2622500CE → Option(lot_size=1)               instrument_parser.py:33-41
      fill_repo.get_all() → update_from_fill(fill)             handler.py:231-234
        → get_position(symbol) → InstrumentParser.parse        position_tracker.py:31   ← site #7
        → Position(instrument=parsed, …)                       position_tracker.py:152-159
      (positions table NEVER read — load_all has no caller)    position_repository.py:42
```

Behavioral proof in the suite (beyond static reading): `test_restore_ignores_positions_snapshot_table` corrupts the `positions` snapshot row (`quantity=999`) and shows restore still reports the fill-derived 50 — the snapshot table is **write-only** on restore, exactly as `G1_WAVE3_RESTORE_REVIEW.md` §2 found.

## 3 — Characterization tests added

`tests/execution/test_g1_restore_characterization.py` — **9 tests**, real `ExecutionHandler` + spy `PaperBroker` over an isolated tmp `ExecutionStore` (the Wave 2A fixture pattern; real `data/execution.db` untouched).

| Group | Test | Pins |
|---|---|---|
| **A** (H1) | `test_restore_future_order_reverts_to_equity` | forward order `FUTURE` → restored order **`EQUITY`**, `symbol`/side/qty/type/signal_id preserved. **The EQUITY assertion is intentional.** |
| **A** (H1) | `test_restore_future_position_rebuilt_as_equity` | restored futures position instrument is Equity-typed, net 50; *also pins that the forward position is Equity-typed too* (site #7 parses on both paths — the H1 asymmetry is order-level) |
| **B** (H2) | `test_restore_option_order_lot_drifts_to_one` | forward order lot **65** (master-resolved, F4) → restored order lot **1**, multiplier 1.0, `symbol` preserved, type stays `OPTION`, qty 75 unaffected. **The lot==1 assertion is intentional.** |
| **B** (H2) | `test_restore_option_position_lot_is_one` | restored option position instrument lot 1; *also pins that the forward position instrument lot is 1* (selector's lot-65 Option lives only on the order) |
| persistence | `test_ledger_schema_persists_only_symbol_identity` | exact column sets of `orders`/`fills`/`positions`; red if any structural identity column (`instrument_type`/`expiry`/`strike`/`option_type`/`lot_size`/`multiplier`/`instrument_key`) is ever added |
| persistence (H6) | `test_restore_ignores_positions_snapshot_table` | snapshot row corrupted → restore unaffected; #9/`load_all` stays dead (a second position-truth source would violate ADR-001) |
| **C** (H3) | `test_reconciliation_matches_restored_future_by_symbol_string` | EQUITY-mistyped restored future reconciles PASS on the symbol string (fixture carries no identity field); divergent qty → `QUANTITY_MISMATCH` |
| **C** (H3) | `test_reconciliation_matches_restored_option_by_symbol_string` | lot-1 drift invisible to reconciliation — only `net_quantity` + symbol consulted |
| **C** (H3) | `test_reconciliation_keys_on_raw_symbol_not_canonical_identity` | a broker-formatted symbol (`NSE_FO\|NIFTY26JUNFUT`) for the same instrument fails to match on **both** sides (`QUANTITY_MISMATCH` + `ORPHANED_BROKER_POSITION`) — matching is raw-string equality, not canonical identity |

All 9 were **green on first run** — they encode current behavior, no production code was touched.

## 4 — Current defects pinned

| Defect | Current reality (now asserted) | Tripwire assertion |
|---|---|---|
| **H1** | `NIFTY26JUNFUT`: fresh runtime = `FUTURE`, restored runtime = `EQUITY` | `ro.instrument_type == InstrumentType.EQUITY` |
| **H2** | option order: forward lot = 65, restored lot = 1 (multiplier 1.0) | `ro.instrument.lot_size == 1` |
| **H3** (safety property, not migrated) | reconciliation keys on the raw `symbol` string; instrument_type/canonical identity/`instrument_key` never consulted | Group C trio |
| **H6** (guard) | `positions` snapshot table write-only on restore | corrupted-snapshot test |

## 5 — Why each defect is currently occurring

- **H1:** the Wave 2 fix (`resolve_future`) was applied to **one site only** — the forward `process_signal` non-option branch (`handler.py:512-515`). Restore rebuilds instruments at `order_repository.py:60` and `position_tracker.py:31` via `InstrumentParser.parse`, which has only an Option regex + an Equity fallback (`instrument_parser.py:21,46`) — no Future branch. Since the SQLite ledger persists **no** `instrument_type` column (`execution_store.py:24-63`), nothing carries the forward-path FUTURE correction across the restart; the symbol re-parses to `Equity`.
- **H2:** the forward option instrument comes from `OptionsContractSelector.select`, which sources `lot_size` from the resolver (`selector.py:108-113` → 65, F4). The ledger persists no lot, so restore re-parses the option symbol and `InstrumentParser.parse` **hardcodes** `Option(lot_size=1, multiplier=1.0)` (`instrument_parser.py:39-40`). The drift is in the *instrument attribute*; `NormalizedOrder.quantity` (persisted absolute number, 75) is unaffected — pinned explicitly.
- **H3/H6:** structural — `reconciliation.py` was written symbol-keyed; `position_repository.load_all` was orphaned when restore moved to fill replay. Characterized as the safety properties the migration must preserve, not defects to fix in Wave 3.

## 6 — Migration hazards (carried forward, now partially tripwired)

From `G1_WAVE3_RESTORE_REVIEW.md` §5 — status after Wave 3A:

| Hazard | Tripwire now? |
|---|---|
| **H1** forward/restore type asymmetry | **YES** — Group A goes red the moment restore types FUTURE |
| **H2** option lot drift | **YES** — Group B goes red the moment restored lot ≠ 1 |
| **H3** reconciliation symbol-keyed | **YES** — Group C red if matching semantics change; the byte-preserved-`.symbol` obligation is now executable |
| **H4** master-unverified at construction | partial — no driver-level test (see §7); Option B avoids it by design |
| **H5** #7 scope creep | partial — the position tests document #7 parses on *both* paths, so an in-place post-gate swap (not a `get_position` edit) is the only change that keeps them coherent |
| **H6** #9 dual-source | **YES** — the corrupted-snapshot test goes red if `load_all` is ever wired into restore |
| **H7/H8** idempotency/group coupling | NO — see §7 |

Additional hazard surfaced while characterizing (refines H1's blast radius): **the position-level identity was never FUTURE, even forward** — site #7 parses on the fresh path too, so forward futures *positions* are already Equity-typed and forward option *positions* already carry lot 1. The order-level instrument is where the forward/restore divergence actually lives today. Consequence for Wave 3: canonicalizing restored **positions** (plan step 5) changes position identity relative to the *forward* runtime too, not just relative to restore — the forward position-construction wave (#6/#7) and the restore pass must converge on the same identity, or a restart will flip position identity in the *opposite* direction (restored canonical vs fresh legacy). Sequencing #6/#7 relative to the restore pass needs an explicit decision (see §8).

## 7 — Coverage gaps that still remain

1. **No driver-level post-gate ordering test** (`G1_WAVE3_RESTORE_REVIEW.md` §4 gap 4 / §6 step 2): nothing asserts the recovery → master-readiness → *(hook point)* → reconcile sequence contract the Option-B pass must slot into. Deliberately not added here — it characterizes a hook that does not exist yet; it belongs to the first Wave 3 implementation step.
2. **H7 (idempotency) unpinned:** no test asserts `_seen_signals`/`signal_id` survive a canonicalization pass (the restored `signal_id` is asserted, but not the registry's behavior under instrument swap — untestable until the pass exists).
3. **H8 (group reconstruction) unpinned:** no multi-leg/group restore characterization; group metadata round-trip is unexercised for derivatives.
4. **No SHORT-side derivative restore case** (all pins are BUY/LONG); netting/flip on restore is covered for equity in the Wave 2A suite only.
5. **Master-absent restore environment:** Group B's forward lot-65 assertion (like the Wave 2A suite's) depends on the materialized master being present; a master-absent environment reads 75 and goes red — a meaningful divergence by design, but worth knowing when running elsewhere.

## 8 — Recommended prerequisites before actual Wave 3 (#2 implementation)

1. **Decide the #6/#7-vs-restore sequencing** (new, from §6): the post-gate pass canonicalizes *restored* position identity while the *forward* tracker still parse-builds (sites #6/#7, planned as their own wave). Either (a) accept a temporary fresh-vs-restored position-identity divergence in the opposite direction, documented, or (b) run the position-construction wave first/together. Owner call; the plan's wave separation (H5) argues for (a) + documentation.
2. **Add the driver-level gate-ordering characterization** (§7 gap 1) as the first implementation step (plan §6 step 2), before introducing the hook.
3. **F4 verification stays a hard precondition for the restore pass going live** — step 5 of the plan makes restored option lots master-resolved (65), the same unverified value as forward #4 (`G1_WAVE3_RESTORE_REVIEW.md` §6).
4. **Honor the in-place-swap contract** (H7/H8): mutate only `.instrument`; never reconstruct `NormalizedOrder`/`signal_id`/`correlation_id`. The Group A/B restored-field assertions (signal_id, qty, side) are the partial net; consider a dedicated idempotency pin when the pass exists.
5. **Reconcile the §5 wave-numbering caveat** in `SOLE_IDENTITY_PATH_REVIEW.md` when Wave 3 lands (`G1_WAVE3_RESTORE_REVIEW.md` §0).

---

## Validation

```
python -m pytest tests/execution/test_g1_restore_characterization.py -q  → 9 passed
python -m pytest tests/execution -q                                      → 37 passed
python -m pytest -q                                                      → 388 passed
```

| Metric | Count |
|---|---|
| Passing (full suite) | **388** |
| Failing | **0** |
| New tests added | **9** (`tests/execution/test_g1_restore_characterization.py`) |
| Production code changed | **0 files** |
| Baseline before Wave 3A | 379 passing |

## Scope adherence

**Added:** the characterization suite + this report. **NOT touched (verified — working tree contains only the two new files):** restore logic, persistence, reconciliation, broker adapters, `InstrumentParser`, canonical layer, driver, MM.7 wiring, F3, F4. No bug fixes, no refactors. **Gate G1 remains OPEN.** Wave 3 (#2 restore migration) and Wave 4 (#4 option migration) remain NOT STARTED — this wave only built their safety net.
