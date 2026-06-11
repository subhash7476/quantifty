# SOLE_IDENTITY_PATH_REVIEW.md

**Type:** Gate G1 review + migration plan — **survey + plan only; NO order-path code in this document or this turn.**
**Date:** 2026-06-09
**Phase:** Review Gate G1 (`PHASE_4C_IMPLEMENTATION_PLAN.md` §2) — the last identity-scope readiness track before 4C.7.
**Question G1 answers:** *Can any live F&O execution path construct an instrument identity WITHOUT going through `InstrumentResolver` / `CanonicalInstrument`?*
**Verdict (2026-06-11): NO — `CanonicalInstrument` is the sole identity source on the live F&O path. GATE G1 CLOSED.** All Section-6 closure criteria are met and mechanically proven (`tests/g1/test_g1_closure_guard.py`, 19 tests) and confirmed by the final closeout audit (`G1_CLOSEOUT_REPORT.md`). *(Historical: this opened "Yes — legacy construction remains"; the document below is the plan that drove it to "No", retained as the migration record.)*
**Scope (locked, mirrors the MM.4 gate):** "sole identity source" is asserted on the **live F&O path** — the only path where the MM.4 startup gate guarantees the master is present. Equity-only-LIVE and paper/replay are explicit **carve-outs**, not forced-canonical.
**Basis (file:line, verified 2026-06-09):** `handler.py`, `order_factory.py`, `position_models.py`, `position_tracker.py`, `order_models.py`, `persistence/{order,position}_repository.py`, `options/selector.py`, `greeks/greeks_calculator.py`. Supersedes the pre-MM.5 enumeration in `PHASE_4C_WIRING_REVIEW.md` §3.

> **G1 / 4C.7 boundary (load-bearing — do not cross):** G1 makes `CanonicalInstrument` the identity **source** — construct canonical, then *derive* the legacy `Option`/`Future`/`Equity` from it. **The broker payload is byte-for-byte unchanged** (same symbol, same fields). The moment the payload *uses* the canonical `instrument_key` / `ci.product`, that is **4C.7** (a behavior change) and stays blocked. Keeping G1 behavior-preserving is also what keeps the Section 4 characterization tests green across the migration.

---

## Section 1 — Current State (the 11 legacy identity sites)

| # | Site | Lines | Object created | Runtime frequency | Criticality |
|---|---|---|---|---|---|
| 1 | `handler.process_signal` non-option branch | `handler.py:513` | legacy `Option`/`Future`/`Equity` via `InstrumentParser.parse(signal.symbol)` | per non-option signal (every futures/equity order) | **HIGH** — primary order-build identity |
| 2 | `handler` batch/group order build | `handler.py:621` | legacy instrument via `parse` | per signal in a batch/group order | **HIGH** — order-build identity (batch) |
| 3 | `handler._check_greek_limits` | `handler.py:720` | legacy instrument via `parse`, fed to `GreeksCalculator.calculate` | per option signal (pre-trade risk gate) | **MED** — transient; identity never leaves the site; greeks are now `asset_class`-dispatched (4C.6) |
| 4 | `handler` option branch → selector | `handler.py:505` → `selector.py:115` | legacy `Option`; **`lot_size` already resolver-sourced** (`selector.py:108-113`, F4: NIFTY→65) | per option signal | **HIGH** — the live option-sizing site (F4 active-on-materialization) |
| 5 | `OrderFactory.create_order` | `order_factory.py:34` | legacy instrument via `parse` | per order **iff** invoked — **handler builds `NormalizedOrder` directly, not via `OrderFactory`** (caller audit needed: likely non-runtime/parallel) | **LOW–MED** — verify live reachability (prove-dead candidate) |
| 6 | `Position(symbol=…)` ctor | `position_models.py:47` | legacy instrument via `parse(symbol or "")` | every `Position` built by symbol (tracker default + restore) | **HIGH** — position identity |
| 7 | `PositionTracker.get_position` | `position_tracker.py:31` | legacy instrument → FLAT `Position` | **VERY HIGH** — every lookup of an untracked symbol (per signal) | **HIGH** — position-key identity |
| 8 | Order restore (replay) | `order_repository.py:60` | legacy `NormalizedOrder.instrument` via `parse(row[1])` | once per persisted order, **at handler construction** (`load_db_state=True` → `_replay_state`, `handler.py:186-187`) | **HIGH** — the restart-flip; **center of gravity** |
| 9 | Position restore (replay) | `position_repository.py:51` | legacy `Position.instrument` via `parse(row[0])` | once per persisted position, **at handler construction** | **HIGH** — the restart-flip; **center of gravity** |
| 10 | `NormalizedOrder(symbol=…)` ctor | `order_models.py:62-70` | **direct `Equity(symbol)` — ALWAYS Equity, even for options/futures** (latent defect) | per `NormalizedOrder` built by symbol — **handler builds via `instrument=`, so this branch is likely dormant** | **LOW–MED** — prove-dead candidate; flag the always-Equity defect |
| 11 | `GreeksCalculator.calculate` dispatch | `greeks_calculator.py:23-34` | none — dispatches on `_asset_class(instrument)` (4C.6) | per greek calc | **DONE** — already `asset_class`-dispatched; works for canonical **and** legacy |

**Construction-vs-gate timing (verified):** restore (#8/#9) runs inside `_replay_state()` at **handler construction** (`handler.py:186-187`), which is **before** the driver's MM.4 master-readiness gate (`driver.run()` → `_run_startup_gate`, reusing the constructed handler's state). A canonical restore would therefore resolve against a **not-yet-gate-verified** master — the constraint Section 3 resolves.

---

## Section 2 — Migration Classification

Legend: **MIGRATE** = construct `CanonicalInstrument` (resolver-sourced) and derive the legacy object from it · **DERIVE** = already resolver-sourced in part; complete the canonical-derivation · **CARVE-OUT** = out of the live-F&O sole-source scope, stays legacy by design (documented, not a gap).

| # | Site | Class | Rationale |
|---|---|---|---|
| 1 | handler:513 order-build | **MIGRATE** (futures) / **CARVE-OUT** (equity) | Futures: `resolve_future` → canonical → derive legacy `Future`. Equity: canonical `EQUITY` requires `isin` (`canonical.py:_validate`) which a bare symbol cannot supply, and equity is out of the F&O scope — stays legacy. |
| 2 | handler:621 batch build | **MIGRATE** (futures) / **CARVE-OUT** (equity) | Mirror of #1 on the batch path. |
| 3 | handler:720 greek-limit | **CARVE-OUT** | Identity is transient and never leaves the site; `GreeksCalculator` is `asset_class`-dispatched (4C.6) and correct on legacy types. No canonical needed. |
| 4 | selector (option) | **DERIVE** | `lot_size` is already resolver-sourced; complete it — have `select()` resolve a `CanonicalInstrument` and derive the legacy `Option` from it (same symbol/lot). Tie-in: **F4 (65) must be exchange-verified before this path goes live.** |
| 5 | OrderFactory.create_order | **CARVE-OUT (prove-dead)** → else MIGRATE | Handler builds `NormalizedOrder` directly; audit for a live caller. If none, mark dead (remove in a later cleanup); if live, MIGRATE like #1. |
| 6 | Position(symbol=) | **MIGRATE** | Position identity on the live path; build from a resolved canonical (derive legacy instrument). |
| 7 | tracker.get_position | **MIGRATE** | Highest-frequency identity construction; the position key must be canonical-sourced on the live F&O path. |
| 8 | order restore | **MIGRATE (via Section 3 Option B)** | Restart-flip. Migrated **not** at the restore site (stays legacy at construction) but via the post-gate canonical upgrade — see Section 3. |
| 9 | position restore | **MIGRATE (via Section 3 Option B)** | Same as #8. |
| 10 | NormalizedOrder(symbol=) | **CARVE-OUT (prove-dead)** | Handler builds via `instrument=`; this symbol= branch is likely dormant. Prove dead; **separately flag the always-`Equity` defect** (it would mistype an option/future) — fix or remove in cleanup, tracked, not silently folded. |
| 11 | greeks dispatch | **CARVE-OUT (done)** | 4C.6 — already `asset_class`-dispatched. |

**Net:** the live-F&O sole-source migration is **#1/#2 (futures), #4, #6, #7, #8/#9**. Carve-outs (#3, #5?, #10, #11, equity) are documented, not gaps. #5/#10 require a prove-dead caller audit first (Wave 1).

---

## Section 3 — Restore Strategy (LOCKED: Option B)

**Chosen: Option B — restore legacy at construction, then upgrade-to-canonical after the MM.4 gate passes.**

- **What:** `_replay_state()` keeps building **legacy** instruments at handler construction (#8/#9 unchanged at the restore site — deterministic, master-independent). After the driver's `_run_startup_gate` confirms master readiness (FRESH/WARN), a **single post-gate canonicalization pass** re-resolves the restored ledger's identities through `InstrumentResolver`, replacing legacy identity with canonical-derived identity on the live F&O entries.
- **Rationale:**
  1. **No env/restart type-flip (ADR-003).** Restore output never depends on master presence — it is always legacy at construction, so a missing/absent master can't make restore produce a different type. Canonical only ever appears *after* the gate has proven the master is present.
  2. **Resolves the sequencing collision** without re-opening MM.4. Option (a) (move the master-check before recovery) would reverse MM.4's deliberate `recovery → master-check → reconciliation` ordering (Decision 2); Option (c) (restore re-resolves) resolves against an unverified master. Option B touches neither.
  3. **Reconciliation stays canonical-correct:** the upgrade runs *before* reconciliation, so positions are matched through canonical identity (the MM.4 intent).
- **Locked — do not reopen.** Alternatives (a) move-check-before-recovery and (c) restore-re-resolves are **rejected** for the reasons above. Any future proposal to change this must cite new evidence, not re-litigate.

---

## Section 4 — Characterization Tests (safety net — BEFORE any migration)

The live order-build/restore path is **untested** (`PHASE_4C_WIRING_REVIEW.md`: "zero regression in the untested live path"). Before touching the riskiest surface in the repo, pin current behavior so every migration step is **provably behavior-preserving** (TDD applied to a refactor: identical assertions green before and after each wave). Required golden-path coverage:

1. **Build order** — option + futures signal → `process_signal` → assert the resulting `NormalizedOrder` (symbol, lot/quantity, side, type) byte-for-byte. (Option case pins the F4 lot value as the current behavior, whatever the exchange-verification later decides.)
2. **Persist** — order + position written to the SQLite ledger → assert the persisted rows (symbol string, fields).
3. **Restore** — construct a handler with `load_db_state=True` over that ledger → assert the restored orders/positions match what was persisted (the round-trip).
4. **Reconcile** — restored ledger vs a broker-position fixture → assert the reconciliation verdict (empty/PASS or the expected diff).

These four become the regression net; **no migration wave merges unless all four stay green.** They must assert the **broker-facing payload** explicitly (the G1/4C.7 boundary tripwire — if a payload byte changes, the migration crossed into 4C.7).

---

## Section 5 — Migration Waves (each with an explicit rollback point)

Each wave is an independent commit; the characterization suite (Section 4) must be green before and after. **Rollback = revert the wave's commit** (no forward-fix required); waves are ordered least→most risk so an early rollback never strands a later one.

| Wave | Scope | Sites | Rollback point |
|---|---|---|---|
| **1 — non-runtime / prove-dead** | Caller audit of `OrderFactory` (#5) and `NormalizedOrder(symbol=)` (#10); mark dead + carve-out (or pull into Wave 2 if live); document #3 carve-out. **No live-path behavior change.** | #5, #10, #3 | revert; nothing live touched |
| **2 — order construction** | `handler` order-build (#1 futures, #4 option-via-selector) construct `CanonicalInstrument` and derive the legacy object; same broker payload. | #1, #2, #4 | revert → back to `parse`-built legacy; characterization green proves parity |
| **3 — position construction** | `Position(symbol=)` (#6) + `tracker.get_position` (#7) build identity from a resolved canonical. | #6, #7 | revert → legacy position identity |
| **4 — restore path (Option B)** | Keep `_replay_state` legacy; add the **post-gate canonicalization pass** (Section 3) in the driver startup sequence, before reconciliation. The highest-risk wave. | #8, #9 (+ driver upgrade hook) | revert the upgrade pass → restore stays legacy (today's behavior); gate/reconcile unchanged |
| **5 — canonical-only validation** | The closure proof: an AST/grep guard test (ADR-002-style) asserting **no `InstrumentParser.parse` is reachable from the live F&O order-build/restore path**, and that every live-F&O order/position identity is canonical-derived. Flip this document's verdict to **"No."** | guard test | n/a (validation only) |

**F4 dependency:** Wave 2 (#4 option path) must not go *live* until F4 (lot 65/30) is exchange-verified — the verification is a precondition for the live option path, tracked separately.

---

## Section 6 — Gate Closure Definition (the crisp exit criterion)

**G1 closes — and this document flips to "No — `CanonicalInstrument` is the sole identity source" — iff all of the following are simultaneously true and proven:**

1. **No live F&O order path creates identity from `InstrumentParser.parse()`.** (Sites #1/#2 futures, #4 — migrated; #3 carve-out justified; restore #8/#9 legacy-at-construction but canonicalized post-gate before any live F&O use.)
2. **No live F&O order path constructs `Option`/`Future` directly from a symbol string** (bypassing the resolver). Every live-F&O order/position identity is either resolver-sourced or *derived* from a resolver-sourced `CanonicalInstrument`.
3. **`CanonicalInstrument` is the sole identity source on the live F&O path** — including across a restart (the Option B post-gate upgrade closes the persistence round-trip; no restart leaves a live F&O entry legacy-typed once the gate has passed).
4. **Carve-outs are documented, not silent:** equity (ISIN-less symbol; out of F&O scope) and paper/replay remain legacy by explicit decision, named here.
5. **Mechanically verifiable:** a committed guard test (Wave 5, ADR-002-style AST/import scan) fails if any `InstrumentParser.parse` / direct `Option`/`Future` construction becomes reachable from the live F&O order-build or post-gate-restore path. This is the measurable "green," not a subjective "looks migrated."

**Until #1–#5 hold with the Section 4 suite green, G1 remains OPEN and this document's verdict stays "Yes — legacy construction remains."**

> **CLOSURE (2026-06-11):** #1–#5 now all hold with the full suite green (441 passing). Criterion #5 is `tests/g1/test_g1_closure_guard.py` (19 AST + grep + characterization tests, commit `87f5b2f`); the final closeout audit (`G1_CLOSEOUT_REPORT.md`) independently confirmed the live call graph has a single canonical order funnel (`process_signal`, the only runtime caller of which is `LoopDriver._dispatch_signals`; the parse-using `process_group_signal`/#3 carve-outs have no live caller). **Gate G1 is CLOSED; this document's verdict is "No."**

---

## Implementation Status (live)

| Migration target | Status | Evidence |
|---|---|---|
| **Wave 1** — prove-dead audit (#5 `OrderFactory`, #10 `NormalizedOrder(symbol=)`), #3 carve-out | **COMPLETE** | `G1_WAVE1_REPORT.md` |
| **Wave 2A** — broker-payload truth + characterization net (7/7 green) | **COMPLETE** | `G1_WAVE2A_BROKER_PAYLOAD_REVIEW.md` |
| **#1** — `handler.process_signal` non-option branch → Future Resolution | **COMPLETE** | see below |
| **#2** — restore path | **COMPLETE** | Wave 3A (restore reality pinned) + Wave 3B (gate-ordering review, orders-vs-positions = SEPARATE) + Option-B slot wired (`driver._canonicalize_restored_ledger`) + **restored POSITION canonicalization (#7-as-restored) COMPLETE** (`canonical_restore.canonicalize_symbol` + `PositionTracker.replace_instrument` + `ExecutionHandler.canonicalize_restored_positions`) + **restored ORDER canonicalization (#8) COMPLETE** (`OrderTracker.replace_instrument`/`order_states` + `ExecutionHandler.canonicalize_restored_orders`; in-place `object.__setattr__` swap preserving correlation_id/signal_id/tracker-key — H7/H8). Both halves: futures EQUITY→FUTURE (H1), option parser-lot→master-lot (H2), symbol preserved (H3); restore-at-construction stays legacy (Option B) so Wave 3A characterization is green untouched. Full suite **409 passing**. |
| **#4** — option path (selector → canonical-derived `Option`; O1 ENTRY + O2 EXIT) | **COMPLETE** | Wave 4 (`selector.py` O1 derives `Option` from CI; `handler.py:581-583` O2 EXIT via `canonicalize_symbol`). Behavior-preserving; F4-gated for going *live*, not for the refactor. |
| **#7** — forward position construction | **COMPLETE** | Wave 4B (`handler._handle_broker_fill` canonicalizes the open position at the fill seam via `canonicalize_symbol`; restore twin matches post-gate). |
| **#6** — `Position(symbol=)` ctor / **#5** `OrderFactory` / **#10** `NormalizedOrder(symbol=)` | **CLOSED (dead)** | Prove-dead — no production caller (guarded by `test_position_symbol_constructor_has_no_production_callers` + the Wave-5 parse/construction inventory). |
| **Wave 5** — AST/grep/characterization closure guard (criterion #5) | **COMPLETE** | `tests/g1/test_g1_closure_guard.py` (19 tests). Flips the verdict to "No". *(G1_WAVE5_CLOSURE_GUARD_REPORT.md, G1_CLOSEOUT_REPORT.md)* |

**Target #1 — COMPLETE (2026-06-09).** Resolved **F-PARSE-1**. Implemented via:
- `core/execution/futures.py` — `resolve_future(symbol, timestamp, resolver=None)` (regex-detect → `InstrumentResolver.resolve_future` → `CanonicalInstrument` → derive legacy `Future`; canonical internal-only).
- `ExecutionHandler` integration — `handler.py:513` non-option `else` branch calls `resolve_future` first, falls through to the unchanged `InstrumentParser.parse` for non-futures.

Characterization coverage:
- `test_build_order_futures_currently_falls_back_to_equity` (characterization, assertion updated `EQUITY → FUTURE`; symbol/side/qty/type assertions preserved)
- `test_non_future_symbols_return_none`
- `test_master_present_resolves_canonical_lot_and_expiry`
- `test_master_absent_still_derives_future`

Broker payload / persistence / restore / reconciliation contracts **unchanged** (`G1_WAVE2_IMPLEMENTATION_REPORT.md` §7–10). Full suite **379 passing, 0 failing**.

---

## NEXT ACTIVE TARGET

**G1 is CLOSED — the identity-architecture program is complete.** All migration sites landed (#1 futures, #2 restore orders+positions, #4 option O1/O2, #7 forward position; #5/#6/#10 prove-dead carve-outs) and the Wave-5 closure guard + final closeout audit flipped the verdict to "No" (2026-06-11). The critical path now shifts **off identity** onto live-enablement: **MM.7 live wiring** (the F&O entry script that builds a live `LoopDriver` + injects `build_master_readiness` + wires `broker_positions` reconciliation), **F3** (tick-size paise scaling), **F4** (lot 65/30 exchange verification), and the **F&O product/segment model + SPAN margin** (Planned #4/#5) — none unblocked by G1 closure. 4C.7 (the broker-payload change) stays blocked. *(History below retained as the migration record.)*

**Wave-numbering reconciliation (per G1_WAVE3_RESTORE_REVIEW §0 / §6 step 7):** three numbering schemes coexist — Section-1 **site numbers** (restore = #8 order, #9 position), the §5 **wave table** (restore = "Wave 4"), and the Implementation-Status **Migration-Target** scheme (restore = "#2"). The work was executed under the **#2 / site-number** scheme; the §5 "Wave 4 = restore" label is the older planning name for the same work. No plan content changed — the §5 table is retained as historical, and the Migration-Target scheme above is authoritative for status.

---

## Status & next step

**Verdict (2026-06-11): G1 CLOSED ("No").** Wave 1 (prove-dead), Wave 2 #1 (Future Resolution), Migration Target #2 (Restore Path — #7-as-restored positions + #8 orders), Wave 4 #4 (option O1/O2), Wave 4B #7 (forward position at the fill seam), and Wave 5 (the AST/grep/characterization closure guard) are **all complete**; the formal closeout audit (`G1_CLOSEOUT_REPORT.md`) confirmed every Section-6 criterion and the single canonical live order funnel. Each wave was independently revertible with the Section-4 characterization net green before and after. 4C.7 stays blocked (G1 is behavior-preserving; 4C.7 is the broker-payload change that follows). **G1 is closed; the next program is live-enablement (MM.7 wiring, F3, F4, F&O product/margin).**
