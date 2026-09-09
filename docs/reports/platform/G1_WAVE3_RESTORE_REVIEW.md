# G1_WAVE3_RESTORE_REVIEW.md

**Type:** Gate G1 — **Wave 3 planning / characterization review of the Restore Path. Survey + mapping + sequencing only; NO code, NO tests, NO schema, NO restore/reconciliation/broker changes this turn.**
**Date:** 2026-06-09
**Parent plan:** `SOLE_IDENTITY_PATH_REVIEW.md` (Restore Strategy = Section 3 Option B; sites #8/#9) · `G1_WAVE1_REPORT.md` · `G1_WAVE2A_BROKER_PAYLOAD_REVIEW.md` · `G1_WAVE2_IMPLEMENTATION_REPORT.md`
**Target:** Migration Target **#2 — Restore Path** (the user/Implementation-Status name). Anchored on Section-1 **site #8** (order restore) and **site #9** (position restore).
**Basis (file:line, verified 2026-06-09):** `core/execution/handler.py`, `core/execution/persistence/{order_repository,position_repository,fill_repository,execution_store}.py`, `core/execution/position_tracker.py`, `core/execution/position_models.py`, `core/execution/reconciliation.py`, `core/instruments/instrument_parser.py`, `core/runtime/driver.py`, `tests/execution/test_g1_characterization.py`, full `tests/` tree.
**Outcome:** Restore path fully mapped. The headline is an **identity asymmetry** the Wave-2 forward fix did not touch: only the *display symbol* survives persistence, so restore rebuilds identity by re-parsing that symbol — and `InstrumentParser.parse` still has no Future branch and hardcodes option `lot_size=1`. Restore is *not yet started*; Option B (post-gate canonicalization) is the locked approach and remains unbuilt. **No code written.**

---

## 0 — Numbering reconciliation (read this first)

Three numbering schemes collide across the G1 documents. This report anchors on the **Section-1 site numbers** (most stable) and notes the others:

| Scheme | Source | "Restore" is called… |
|---|---|---|
| **Site numbers** (used here) | `SOLE_IDENTITY_PATH_REVIEW.md` §1 (the 11 sites) | **#8** (order restore), **#9** (position restore) |
| **Wave numbers** | `SOLE_IDENTITY_PATH_REVIEW.md` §5 | **Wave 4** (restore); Wave 3 = position construction (#6/#7) |
| **Migration-Target #N** | `SOLE_IDENTITY_PATH_REVIEW.md` Implementation Status / "NEXT ACTIVE TARGET" | **#2 — Restore Path** |

**The user's task title "Wave 3 (#2 Restore Path)" = the Restore Path** (Migration-Target #2 / sites #8–#9). That is the plain reading and the subject of this report. ⚠️ **Caveat for the implementer:** this is *not* the same "Wave 3" as `SOLE_IDENTITY_PATH_REVIEW.md` §5 (where Wave 3 = position #6/#7 and restore = Wave 4). When this work is implemented and KB-synced, **reconcile the §5 wave table** so the document is not internally self-contradictory. No plan content is changed by this report.

---

## 1 — Current restore flow (file:line)

Restore is driven by `load_db_state=True` (default) at **handler construction**, *before* the driver's startup gate.

```
ExecutionHandler.__init__(load_db_state=True)         handler.py:127, 186-187
  └─ ExecutionStore("data/execution.db")              handler.py:145  (default real ledger)
  └─ _replay_state()                                  handler.py:219
       │
       ├─ SQLite ─────────────────────────────────────────────────────────────────
       │   orders   = order_repo.get_all()            handler.py:224 → order_repository.py:46-78
       │   fills    = fill_repo.get_all()             handler.py:231 → fill_repository.py:41-64
       │   (positions table is NEVER read — see §2 / H6 below)
       │
       ├─ Object reconstruction ───────────────────────────────────────────────────
       │   per order:  instrument = InstrumentParser.parse(row[1])   order_repository.py:60
       │               NormalizedOrder(instrument=…)                 order_repository.py:62-72
       │   per fill:   FillEvent(symbol=row[2], …)  (symbol string only, no instrument)
       │                                                             fill_repository.py:49-57
       │
       ├─ Execution state ─────────────────────────────────────────────────────────
       │   order_tracker.add_order(order, persist=False)            handler.py:226
       │   _seen_signals.add(order.signal_id)  (idempotency)        handler.py:227-228
       │   per fill: order_tracker.process_fill(fill, persist=False) handler.py:233
       │   per fill: position_tracker.update_from_fill(fill, persist=False) handler.py:234
       │            └─ get_position(symbol) → InstrumentParser.parse(symbol)  position_tracker.py:31  (SITE #7)
       │            └─ Position(instrument=parsed, …)               position_tracker.py:152-159
       │   group reconstruction from order metadata                 handler.py:236-256
       │   _trades_today = today's fills                            handler.py:258-261
       │
       ▼
  driver.run() → STARTUP → _run_startup_gate()        driver.py:335
       ├─ enter_recovery(); RECOVERY_STARTED/COMPLETED  (REUSES _replay_state — never re-restores, ADR-001)  driver.py:346-352
       ├─ _check_master_readiness()   (MM.4: BLOCK/WARN/skip)        driver.py:357, 366-411
       │     └─ Reconciliation ──────────────────────────────────────────────────────
       └─ _reconcile_ledger()                                       driver.py:360, 413-444
             └─ reconciliation.reconcile(broker_positions())        driver.py:431 → reconciliation.py:24-87
             (LIVE broker-positions source NOT wired yet → vacuously clear; driver.py:422-424)
       └─ start() → RUNNING                                         driver.py:363
```

**Construction-vs-gate timing (verified, matches plan §1):** `_replay_state()` runs inside `__init__` (`handler.py:186-187`), which is **before** `_check_master_readiness()` (`driver.py:357`). So any canonical resolution done *at the restore site* would resolve against a **not-yet-gate-verified** master — the precise reason Option B defers canonicalization to *after* the gate.

---

## 2 — Identity ownership: what survives persistence

**Only the display `symbol` string survives. No structural identity field is persisted.**

| Field | `orders` table | `positions` table | `fills` table | Survives? |
|---|---|---|---|---|
| `symbol` (display) | ✔ `execution_store.py:28` | ✔ `:57` | ✔ `:44` | **YES** — sole identity carrier |
| `side` / `quantity` / `order_type` | ✔ | ✔ (side/qty) | ✔ (side/qty/price) | YES (not identity) |
| `instrument_type` (EQUITY/OPTION/FUTURE) | ✘ no column | ✘ | ✘ | **NO** — re-derived |
| `expiry` | ✘ | ✘ | ✘ | **NO** |
| `strike` | ✘ | ✘ | ✘ | **NO** |
| `option_type` (CE/PE) | ✘ | ✘ | ✘ | **NO** |
| `instrument_key` (canonical) | ✘ | ✘ | ✘ | **NO** — never persisted (G1/4C.7 boundary holds) |
| `lot_size` / `multiplier` | ✘ | ✘ | ✘ | **NO** — re-derived |

Schema source of truth: `execution_store.py:24-63` (three `CREATE TABLE` statements).

**Consequence — restore re-derives ALL structural identity from the symbol string via `InstrumentParser.parse`:**
- A futures symbol (`NIFTY26JUNFUT`) → no Option-regex match → **`Equity`** (`instrument_parser.py:21,46`; no Future branch — **F-PARSE-1 is still live on the restore path**).
- An option symbol (`NIFTY16JUN2622500CE`) → Option regex match → `Option(..., lot_size=1, multiplier=1.0)` (**hardcoded** `instrument_parser.py:39`).
- An equity symbol → `Equity`.

**Finding — positions table is write-only on restore.** `position_repository.load_all()` (`position_repository.py:42`) is the documented #9 restore site, but **repo-wide grep shows it has ZERO callers** (only its own definition). `_replay_state` never calls it (`handler.py:219-265`). Positions are reconstructed **exclusively by replaying fills** through `update_from_fill → get_position(symbol) → parse` (**site #7**, `position_tracker.py:31`). The `positions` snapshot table is written on every fill (`position_tracker.py:161-162`) but never read back. This **refines `SOLE_IDENTITY_PATH_REVIEW.md` §1**, which lists #9 as exercised "once per persisted position, at handler construction" — in the current code it is **not** exercised on restore.

---

## 3 — Canonical migration candidates (where persisted identity → `CanonicalInstrument`)

Every place restore re-derives identity from the symbol string is a candidate for the Option-B **post-gate canonicalization pass**. Per Option B (`SOLE_IDENTITY_PATH_REVIEW.md` §3), these are **NOT** migrated at the restore site (that stays legacy-at-construction, master-independent, ADR-003); they are re-resolved through `InstrumentResolver` **after** `_check_master_readiness()` passes and **before** `_reconcile_ledger()`.

| # | Persisted identity → reconstruction site | Current legacy build | Canonical conversion (post-gate) |
|---|---|---|---|
| **#8** | `order_repository.py:60` — `parse(row[1])` per restored order | `Option`/`Equity` (never `Future`) | re-resolve order's `symbol` → `CanonicalInstrument` → derive legacy `Future`/`Option`; replace `NormalizedOrder.instrument` on live-F&O entries |
| **#7 (restore-driven)** | `position_tracker.py:31` — `parse(symbol)` per replayed fill | `Option`/`Equity` (never `Future`) | re-resolve each tracked position's `symbol` → canonical → derive legacy; replace the `Position.instrument` |
| **#9** | `position_repository.py:42` — `parse(row[0])` | dead on restore (no caller) | **none** — do not wire `load_all`; canonicalization works off the fill-rebuilt tracker, not the snapshot table |

**The conversion key is always `order.symbol` / `position.symbol`** — the only field that survived. `InstrumentResolver.resolve_future` / `resolve_option` (the resolvers Wave 2 #1 already uses, `core/execution/futures.py`) are the resolution entry points; canonical stays internal (read `.expiry`/`.lot_size`/`.underlying`, derive legacy, discard `ci` — the G1/4C.7 containment Wave 2 established).

**Carve-outs (stay legacy on restore, by design):** equity entries (ISIN-less symbol; out of F&O scope) and paper/replay. The post-gate pass touches **live-F&O** entries only.

---

## 4 — Characterization coverage

### Already covered
| Test | Pins | File |
|---|---|---|
| `test_restore_round_trip` | order round-trips (symbol/side/qty) via second handler `load_db_state=True`; position net qty rebuilt from replayed fill (**equity only**) | `test_g1_characterization.py:236-255` |
| `test_reconcile_restored_ledger_against_broker` | reconcile over a restored ledger → PASS + `QUANTITY_MISMATCH` (**equity only**) | `:262-279` |
| `test_persist_order_and_fill_rows` | persisted order/fill rows (the inputs restore reads back) | `:199-229` |
| `test_real_execution_db_untouched` | restore isolation — real `data/execution.db` never touched | `:286-299` |

### Still unprotected (gaps Wave 3 must close BEFORE migrating)
1. **No futures restore test.** Nothing pins that a restored `NIFTY26JUNFUT` currently rebuilds as **`Equity`** (the F-PARSE-1 asymmetry, H1). Without it, the post-gate pass that flips it to `FUTURE` has no red→green tripwire — the mirror of what `test_build_order_futures_currently_falls_back_to_equity` did for the forward path.
2. **No option restore test.** Nothing pins that a restored option rebuilds with **`lot_size=1`** (H2) vs the forward selector's `65`. The restore/forward lot divergence is currently invisible to the suite.
3. **No restore→`instrument_type` assertion.** `test_restore_round_trip` asserts symbol/side/qty but **not** `restored.instrument_type` — so a type flip on restore would pass silently today.
4. **No driver-level post-gate test.** `tests/runtime/test_driver_startup_gate.py` exercises the gate ordering, but nothing asserts identity is canonical *after* the gate and *before* reconcile (the Option-B contract — does not exist yet because the pass does not exist).
5. **No reconciliation-keying test for derivatives.** Reconciliation matches on the **symbol string** (`reconciliation.py:57,64` — `_positions` keys and `broker_map` keys), never on instrument type. Covered implicitly for equity; not pinned for an option/future symbol.

**Verdict: characterization coverage is NOT sufficient to start migrating.** The equity round-trip is pinned; the two derivative behaviors the migration will actually change (futures type flip, option lot) are unpinned. Gaps 1–3 are the Section-4 precondition for Wave 3 and must be added as *characterization of current (defective) reality* first — green before, deliberately flipped after.

---

## 5 — Migration hazards

Ranked most→least severe.

- **H1 — Forward/restore identity asymmetry (the spine).** Wave 2 fixed the *forward* path (`process_signal → resolve_future → Future`, `handler.py:513`), but the *restore* path (`order_repository.py:60`, `position_tracker.py:31`) still re-parses the symbol with **no Future branch**. **Failure mode:** the *same* live futures position is `FUTURE` when freshly built and **`EQUITY` after a restart** — `instrument.multiplier`/asset-class dispatch (greeks, margin, P&L) silently change across a restart. This asymmetry is the entire reason Option B exists (`G1_WAVE2_IMPLEMENTATION_REPORT.md` §9 confirms a restored futures order re-parses to `Equity`).

- **H2 — Restored-option lot drift.** `InstrumentParser.parse` hardcodes `Option(lot_size=1)` (`instrument_parser.py:39`); the forward selector path produces master-resolved `lot_size=65` (#4, F4). **Failure mode:** a restored option carries `lot_size=1` vs `65` live — any sizing/greeks/margin keyed off `instrument.lot_size` is wrong by 65× after a restart, with no error. (Note: `NormalizedOrder.quantity` is persisted as the absolute number and is unaffected; the drift is in the *instrument's* lot attribute, which downstream greeks/margin read.)

- **H3 — Reconciliation matches on symbol string, not canonical identity.** `reconciliation.py:57-64` keys both internal `_positions` and `broker_map` on the raw `symbol`. The `driver.py:354-355` comment ("reconciliation matches positions through canonical identity") is **aspirational, not actual**. **Failure mode:** canonicalizing restore identity does **not** by itself make reconciliation canonical-correct — if a future broker book emits a differently-formatted symbol, matching still breaks. Register this: the post-gate pass must preserve `.symbol` byte-for-byte (as Wave 2 did) so reconciliation keeps matching; do **not** assume canonicalization "fixes" reconciliation.

- **H4 — Master-not-yet-verified at construction (sequencing collision).** `_replay_state` runs before `_check_master_readiness` (`handler.py:186` vs `driver.py:357`). **Failure mode:** any canonicalization done at the restore site would resolve against an unverified/absent master → env-dependent restore type-flip (ADR-003 violation). Option B avoids this by construction; a non-Option-B shortcut (canonicalize inside `_replay_state`) would re-introduce it. **Do not.**

- **H5 — #7 coupling (scope creep).** Restore reconstructs *position* identity through `tracker.get_position → parse` (**#7**), which the plan classifies under the *position-construction* wave, not restore. **Failure mode:** folding #7's migration into the restore wave couples two waves the plan deliberately separates, defeating per-wave rollback. **Mitigation:** the Option-B post-gate pass re-resolves what #7 built **additively** (replace `Position.instrument` on the rebuilt tracker) **without modifying `get_position`/#7**. Keep #7's code untouched in this wave.

- **H6 — #9 is dead; do not resurrect it.** `position_repository.load_all` has no caller (§2). **Failure mode:** "migrating #9" by wiring `load_all` into restore would create a **second** position-truth source (snapshot table vs fill-replay) — exactly the dual-source-of-truth ADR-001 prohibits. **Mitigation:** leave `load_all` dead; canonicalize the fill-rebuilt tracker only.

- **H7 — Idempotency/seen-signals coupling.** `_replay_state` also rebuilds `_seen_signals` from restored orders (`handler.py:227-228`) and `_trades_today` (`:258-261`). **Failure mode:** a canonicalization pass that *rebuilds* orders rather than *re-resolving their instrument in place* could disturb `correlation_id`/`signal_id` and corrupt the idempotency registry. **Mitigation:** mutate only `.instrument`; never reconstruct the `NormalizedOrder`/`signal_id`.

- **H8 — Group reconstruction depends on restored orders.** Groups are rebuilt from restored order metadata (`handler.py:236-256`). **Failure mode:** if canonicalization replaces order objects, group membership keyed on `correlation_id` can desync. **Mitigation:** same as H7 — in-place instrument swap only.

---

## 6 — Recommended implementation sequence (ordering only — no code, no pseudocode)

1. **Close the characterization gaps (Section 4, gaps 1–3) FIRST.** Add restore tests that pin *current* reality: restored futures → `EQUITY` (H1), restored option → `lot_size=1` (H2), and a `restored.instrument_type` assertion on the round-trip. Green before any production change. These are the red→green tripwires for steps 4–5.
2. **Add a driver-level characterization test for gate ordering** asserting the post-gate hook point exists in the sequence recovery → master-readiness → **(new hook)** → reconcile (initially a no-op assertion of call order), so step 4 has a contract to satisfy.
3. **Introduce the post-gate canonicalization entry point in the driver startup sequence** — positioned strictly *after* `_check_master_readiness()` returns True and strictly *before* `_reconcile_ledger()` (`driver.py:357` → new step → `driver.py:360`). Live-F&O scope only; gated by the same `is_live ∧ has_derivatives ∧ master-ready` condition as MM.4. No-op when not applicable (preserves paper/replay/equity behavior).
4. **Canonicalize restored ORDER identity (#8)** — re-resolve each live-F&O restored order's `symbol` via the existing resolver and swap `NormalizedOrder.instrument` **in place** (preserve `correlation_id`/`signal_id`/`symbol`/`side`/`quantity`/`order_type`). Flip the H1 futures test EQUITY→FUTURE; keep every payload-byte assertion green.
5. **Canonicalize restored POSITION identity (#7 as driven by restore)** — re-resolve each tracked position's `symbol` and swap `Position.instrument` **in place** on the fill-rebuilt tracker. Do **not** touch `get_position`/#7 source (H5) and do **not** wire `load_all`/#9 (H6). Resolve the H2 lot drift here (restored option lot now matches forward).
6. **Re-run reconciliation last** (unchanged engine) and confirm it still matches on the preserved `.symbol` (H3) — assert PASS over the canonicalized ledger.
7. **KB sync** — update `SOLE_IDENTITY_PATH_REVIEW.md` Implementation Status (#2 restore → COMPLETE), reconcile the §5 wave-numbering caveat (§0 of this report), and update `PROJECT_STATE`/`CHANGELOG` per KB-sync discipline. One revertible commit per step (3–6) so any step rolls back independently.

**F4 dependency reminder:** step 5 makes restored option identity master-resolved (lot 65), the same F4-gated value as forward #4 — the F4 exchange verification precondition applies equally to the restore path going live.

---

## Deliverable

### 1 — Findings summary
- **Phase 0:** Decision **A (track)**. Both reports are cited as "Evidence" in `SOLE_IDENTITY_PATH_REVIEW.md` Implementation Status, and every other `docs/reports/*.md` (20 files incl. the Wave-2 implementation report) is git-tracked; the two were the only untracked stragglers. Committed as **"G1 Investigation Reports"** (`0d2c74f`, docs-only). Working tree clean.
- **Restore persists only the display `symbol`** (§2). All structural identity (type/expiry/strike/option_type/lot/`instrument_key`) is re-derived by `InstrumentParser.parse` on restore.
- **The forward fix did not reach restore (H1).** `resolve_future` is on `process_signal` only; `order_repository.py:60` and `position_tracker.py:31` still re-parse → futures restore as **Equity**, options restore with **lot_size=1**.
- **#9 is dead on restore; restore rebuilds positions from fills (#7).** `position_repository.load_all` has no caller repo-wide.
- **Reconciliation keys on the symbol string, not canonical identity (H3).**

### 2 — Risk ranking
**H1** (forward/restore type asymmetry) > **H2** (option lot drift) > **H3** (reconciliation symbol-keyed) > **H4** (master-unverified at construction) > **H5** (#7 scope-creep) > **H6** (#9 dual-source) > **H7/H8** (idempotency/group coupling). H1–H2 are silent data-corruption-across-restart risks; H4–H8 are "easy wrong way to implement it" risks that Option B + in-place swap avoid.

### 3 — Recommended Wave 3 plan
Option B, sequenced in Section 6: **characterize current restore reality (futures→Equity, option lot=1, instrument_type) → add driver post-gate hook between master-readiness and reconcile → canonicalize restored orders (#8) in place → canonicalize restored positions (#7-as-restored) in place → re-reconcile on preserved symbol.** Live-F&O scope only; equity/paper/replay carve-outs preserved; `load_all`/#9 stays dead; per-step revertible commits.

### 4 — Is characterization coverage sufficient?
**No.** The equity round-trip and reconcile are pinned, but the two derivative behaviors the migration will change — futures type flip (H1) and option lot (H2) — are **unprotected**, and `test_restore_round_trip` does not assert `instrument_type`. Closing Section-4 gaps 1–3 is the **first task** of Wave 3 implementation, before any production change.

---

## Status & next step
**Wave 3 (Restore Path / #2) characterized — review only, no implementation.** Phase 0 report-tracking commit done (`0d2c74f`); this review written and left **untracked** (no commit, per task). Restore path mapped (§1), identity ownership established (§2), canonical candidates identified (§3), coverage gaps and hazards enumerated (§4/§5), Option-B sequence recommended (§6). **G1 remains OPEN.** Awaiting authorization before any Wave 3 code. Wave 3 is **not** authorized by this report.
