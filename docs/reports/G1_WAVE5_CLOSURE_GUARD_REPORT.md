# G1_WAVE5_CLOSURE_GUARD_REPORT.md

**Type:** Gate G1 — Wave 5 mechanical **closure guard** (the ADR-002-style proof, `SOLE_IDENTITY_PATH_REVIEW.md` §6 criterion #5). **Test-only; NO production-code behavior changed in this wave.**
**Date:** 2026-06-11
**Deliverable:** `tests/g1/test_g1_closure_guard.py` (19 tests) — a committed guard that FAILS if any new `InstrumentParser.parse` / direct legacy `Option(...)` / `Future(...)` construction becomes reachable from the live F&O order-build or post-gate-restore path, or if a `CanonicalInstrument` crosses the `NormalizedOrder` / persistence / broker boundary.
**Basis (file:line, verified 2026-06-11):** `core/execution/handler.py`, `core/execution/options/selector.py`, `core/execution/futures.py`, `core/execution/canonical_restore.py`, `core/instruments/instrument_parser.py`, `core/execution/persistence/{order,position}_repository.py`, `core/execution/persistence/execution_store.py`, `core/execution/{order_models,position_models,position_tracker,order_tracker,order_factory}.py`, `core/runtime/driver.py`, `core/brokers/{paper_broker,upstox_adapter}.py`, `core/brokers/mapping/*`.

**Verdict: G1 CLOSEABLE.** Every Section-6 closure criterion that a mechanical guard can assert is now asserted and green. The guard is the missing criterion #5; with it, criteria #1–#5 hold simultaneously and are continuously enforced. The remaining items below the line are **documented exclusions**, not open identity-path gaps.

---

## 1 — Closure criteria checked (mapped to `SOLE_IDENTITY_PATH_REVIEW.md` §6)

| §6 criterion | Guard test(s) | Kind |
|---|---|---|
| **#1** No live F&O order path creates identity from `InstrumentParser.parse` | `test_process_signal_parse_is_only_the_guarded_fallback`, `test_no_unclassified_instrumentparser_parse_site_in_core`, `test_handler_parse_calls_confined_to_audited_functions` | AST + grep |
| **#2** No live F&O order path constructs `Option`/`Future` directly from a symbol; every identity is resolver-sourced or derived from a `CanonicalInstrument` | `test_process_signal_constructs_no_legacy_option_or_future_directly`, `test_process_signal_routes_options_through_selector`, `test_process_signal_derivative_identity_via_canonicalize_symbol`, `test_no_unwhitelisted_legacy_option_future_construction_in_core`, `test_derivation_points_resolve_through_canonical`, `test_forward_futures_order_identity_is_canonical_derived`, `test_forward_option_order_identity_is_canonical_derived` | AST + grep + characterization |
| **#3** `CanonicalInstrument` is the sole identity source incl. across restart (Option-B post-gate upgrade) | `test_canonicalize_runs_after_readiness_before_reconcile`, `test_canonicalize_gated_like_mm4_and_upgrades_both_halves`, `test_restore_is_legacy_at_construction_then_upgrades_post_gate` | AST + characterization |
| **#4** Carve-outs documented, not silent | `_PARSE_ALLOWED` + `_CONSTRUCT_ALLOWED` allowlists (each site carries its written classification); `test_position_symbol_constructor_has_no_production_callers` | grep |
| **#5** Mechanically verifiable closure guard exists | **this whole file** | — |
| **Boundary** `CanonicalInstrument` never crosses `NormalizedOrder` / persistence / broker payload | `test_canonical_not_imported_on_order_persistence_broker_boundary`, `test_instrument_key_absent_from_execution`, `test_order_path_does_not_import_broker_mapping`, `test_forward_order_instrument_is_legacy_not_canonical`, `test_persisted_order_schema_is_symbol_keyed` | AST + grep + characterization |

The five Wave-5 guard requirements stated in the task map onto the above: **(1)** no live identity via parse/legacy `Option`/`Future` → criterion #1/#2 rows; **(2)** all live derivative identity via `CanonicalInstrument` + derive-to-legacy → criterion #2 rows; **(3)** no `CanonicalInstrument` across `NormalizedOrder`/persistence/broker → Boundary row; **(4)** restore upgrades only after MM.4, before reconcile → criterion #3 rows; **(5)** #6 stays dead → criterion #4 row.

---

## 2 — Evidence gathered

### 2.1 Live F&O order-build entry (`ExecutionHandler.process_signal`)
AST of the function body proves:
- **Zero** `Option(...)` / `Future(...)` construction calls — identity is delegated.
- The **option ENTRY** branch instantiates `OptionsContractSelector` and calls `.select(...)` (O1).
- The **non-option / EXIT** branch calls `canonicalize_symbol(...)` (#1 futures, O2 option-EXIT).
- The **only** `InstrumentParser.parse` call is the equity/unresolved fallback inside an `IfExp.orelse` (`derived if derived is not None else InstrumentParser.parse(...)`, `handler.py:583`) — proven by collecting every `parse` Call node in the function and asserting each is a descendant of an `IfExp.orelse`.

### 2.2 Repo-wide identity-construction inventory (the ADR-002 closure proof)
AST scan of every `core/**/*.py`:
- **`InstrumentParser.parse`** appears in exactly 6 files, all in the audited `_PARSE_ALLOWED` allowlist: `handler.py` (guarded fallback #1 + batch boundary #2 + greek-limit #3), `position_tracker.py` (#7 `get_position` FLAT default, master-independent), `position_models.py` (#6 ctor, dead), `order_repository.py` (#8 restore-at-construction), `position_repository.py` (#9 restore-at-construction + dead `load_all`), `order_factory.py` (#5, dead). A new site outside the allowlist fails the guard.
- **Direct `Option(...)` / `Future(...)` construction** appears in exactly 4 files, all in `_CONSTRUCT_ALLOWED`: `instrument_parser.py` (the legacy parser), and the three whitelisted derive-to-legacy boundaries `futures.py` / `selector.py` / `canonical_restore.py`. Class definitions (`option.py`, `future.py`) are `ClassDef`, not `Call`, so they do not appear. A new direct construction fails the guard.
- Inside `handler.py`, `parse` is confined to `{process_signal, process_group_signal, _check_greek_limits}` — it cannot leak into a new handler function unnoticed.

### 2.3 Derive-to-legacy boundary is genuinely canonical
`futures.py`, `canonical_restore.py`, `selector.py` each reference `InstrumentResolver` and call `resolve_future`/`resolve_option` — identity is resolved through a `CanonicalInstrument`, then derived to legacy, not hand-built. Characterization confirms a live futures ENTRY yields a legacy `Future` (not the parser's EQUITY mistype) and a live option ENTRY yields a legacy `Option` with the selector-computed symbol preserved byte-for-byte.

### 2.4 `CanonicalInstrument` containment (the G1 / 4C.7 boundary)
- AST import scan: `order_models.py`, both persistence repositories, `execution_store.py`, `paper_broker.py`, `upstox_adapter.py` **do not import** `core.instruments.canonical` / `CanonicalInstrument`. (The only `CanonicalInstrument` references in `core/execution/` are docstrings; the real usages live in `core/brokers/mapping/*`, the 4C.7-blocked projection, unwired into the order path.)
- `instrument_key` has **zero** references in `core/execution/` (grep).
- `handler.py` does **not** import `core.brokers.mapping` (wiring it is 4C.7).
- Characterization: a forward F&O order's `.instrument` is a legacy type, never a `CanonicalInstrument`; the `orders`/`positions` DDL carries `symbol` and **no** `instrument_key` / `canonical_id` / `lot_size` column.

### 2.5 Restore upgrade ordering (Option B)
- AST of `LoopDriver._run_startup_gate`: call linenos prove `_check_master_readiness` < `_canonicalize_restored_ledger` < `_reconcile_ledger`.
- AST of `_canonicalize_restored_ledger`: gated on `is_live` ∧ `has_derivatives` ∧ `master_readiness` (the MM.4 condition) and upgrades **both** halves (`canonicalize_restored_positions` + `canonicalize_restored_orders`).
- Characterization: a restored futures order is `EQUITY` at construction (Option B, master-independent) and only the post-gate `canonicalize_restored_orders()` flips it to `FUTURE`.

### 2.6 #6 dead
No production module (excluding the definition `position_models.py`) contains `Position(symbol=` — the parser-defaulting ctor branch has no live caller.

### 2.7 Test run
- `pytest tests/g1/test_g1_closure_guard.py -q` → **19 passed**.
- `pytest -q` → **441 passed, 0 failing** (422 prior + 19 new). No regressions.

---

## 3 — Remaining exclusions (documented, NOT identity-path gaps)

| Exclusion | Why it is out of the sole-source scope |
|---|---|
| **Equity** order/position identity (`InstrumentParser.parse` → `Equity` fallback at `handler.py:583`) | Out of the F&O scope; a bare equity symbol has no ISIN to build a canonical `EQUITY` (`canonical.py` `_validate`). Explicit carve-out. |
| **#3 greek-limit** (`_check_greek_limits`, `handler.py:790`) | Identity is transient and never leaves the site; greeks dispatch on `asset_class` (4C.6), correct on legacy types. |
| **#2 batch** (`process_group_signal`, `handler.py:691`) | No option branch on the batch path; a batched signal is `parse`-built. Documented scope boundary (tracked under #2), not a #4 site — no live caller constructs a `LoopDriver` to drive it. |
| **#5 `OrderFactory` / #10 `NormalizedOrder(symbol=)`** | Prove-dead (Wave 1): the handler builds `NormalizedOrder(instrument=...)` directly; these have no live caller. `#10`'s always-`Equity` defect is tracked, not silently folded. |
| **Restore-at-construction (#8/#9)** stays legacy by design (Option B) | Deterministic, master-independent at construction; the post-gate pass re-resolves it before any live F&O use (guarded above). |
| **Expired/rolled restored option** not in the current snapshot → left legacy | Not a live-tradeable position (`G1_WAVE3_RESTORE_CLOSEOUT.md` §A). Documented limitation. |
| **`core/brokers/mapping/*`** (the only `instrument_key` / `CanonicalInstrument`-in-broker code) | The 4C BrokerMapping projection — **unwired** into the order path; wiring it IS 4C.7, still blocked. The guard asserts the order path does not import it. |

**Orthogonal open findings (not identity-path):** F3 (tick-size paise scaling) and F4 (NIFTY 65 / BANKNIFTY 30 lot exchange-verification) remain open per `PROJECT_STATE.md`; both gate the option path going **live** (which is additionally blocked by the absent F&O entry script), not G1 closure, which is behavior-preserving and keeps current master values.

---

## 4 — Final recommendation

**G1 CLOSEABLE.**

The mechanical closure guard (criterion #5) now exists, is committed, and is green alongside the full suite (441 passing). All identity-path closure criteria (#1–#4) hold and are continuously enforced by AST + grep + characterization checks; every legacy `parse` / `Option` / `Future` site in `core/` is either a whitelisted canonical-derivation point or a documented carve-out, and a regression (a new unaudited identity-construction site, or a `CanonicalInstrument` crossing the order/persistence/broker boundary) will fail the guard. The only remaining items are documented exclusions and the orthogonal F3/F4 live-enablement preconditions.

Per the task scope, this report stops at "G1 CLOSEABLE" and does **not** perform the final G1 audit — that audit consumes this guard as its mechanical evidence and flips `SOLE_IDENTITY_PATH_REVIEW.md`'s verdict to "No — `CanonicalInstrument` is the sole identity source."
