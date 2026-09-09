# G1_CLOSEOUT_REPORT.md

**Type:** Gate G1 — **Final Closeout Audit.** Read-only evidence review; **no production code, no tests changed in this audit** (only the verdict-flip KB sync: this report + `SOLE_IDENTITY_PATH_REVIEW.md`, `PROJECT_STATE.md`, `CHANGELOG_PLATFORM.md`).
**Date:** 2026-06-11
**Question G1 answers:** *Can any live F&O execution path construct an instrument identity WITHOUT going through `InstrumentResolver` / `CanonicalInstrument`?*
**Verdict: NO. GATE G1 → CLOSED.** Every Section-6 closure criterion (`SOLE_IDENTITY_PATH_REVIEW.md`) is met, mechanically proven by `tests/g1/test_g1_closure_guard.py` (Wave 5), and independently confirmed by the call-graph audit below. `CanonicalInstrument` is the sole identity source on the live F&O path; the broker payload is byte-for-byte unchanged (the G1 / 4C.7 boundary holds — 4C.7 stays blocked).
**Basis (file:line, verified 2026-06-11):** `core/execution/handler.py`, `core/execution/options/selector.py`, `core/execution/futures.py`, `core/execution/canonical_restore.py`, `core/instruments/instrument_parser.py`, `core/execution/persistence/{order,position}_repository.py`, `core/execution/persistence/execution_store.py`, `core/execution/{order_models,position_models,position_tracker,order_tracker,order_factory}.py`, `core/runtime/driver.py`, `core/brokers/{paper_broker,upstox_adapter}.py`, `core/brokers/mapping/*`, `core/instruments/master_readiness.py`. Full suite **441 passing, 0 failing**.

---

## A — Scope of the audit

This is the formal closeout the prior closeouts deferred. `G1_WAVE3_RESTORE_CLOSEOUT.md` declared Migration Target #2 COMPLETE but G1 OPEN; the Wave-4 / Wave-4B implementations migrated the forward option (#4/O1/O2) and forward position (#7) paths; `G1_WAVE5_CLOSURE_GUARD_REPORT.md` delivered the mechanical guard (criterion #5) and concluded **G1 CLOSEABLE**. This audit re-derives the verdict **independently of the guard** (does the live call graph actually have a single canonical order path?) and, agreeing, flips the gate.

The Wave-5 guard is the *standing* enforcement; this audit is the *one-time* human confirmation that the guard guards the right surface.

---

## B — Closure criteria, re-verified (`SOLE_IDENTITY_PATH_REVIEW.md` §6)

| # | Criterion | Audit finding | Evidence |
|---|---|---|---|
| **1** | No live F&O order path creates identity from `InstrumentParser.parse` | **MET** | `process_signal` (the sole order-build entry) calls `parse` only as the equity/unresolved fallback inside an `IfExp.orelse` (`handler.py:583`); futures (#1) → `resolve_future`, option ENTRY (#4/O1) → selector, option EXIT (O2) → `canonicalize_symbol`. Guard: `test_process_signal_parse_is_only_the_guarded_fallback`. |
| **2** | No live F&O path constructs `Option`/`Future` directly from a symbol; every identity is resolver-sourced or derived from a `CanonicalInstrument` | **MET** | AST: zero `Option(`/`Future(` calls in `process_signal`; every direct construction in `core/` is the legacy parser or one of three whitelisted derive-to-legacy points (`futures.py`, `selector.py`, `canonical_restore.py`), each resolving through `InstrumentResolver`. Characterization: live futures ENTRY → legacy `Future` (not the parser EQUITY mistype); live option ENTRY → legacy `Option`, symbol byte-stable. |
| **3** | `CanonicalInstrument` is the sole identity source incl. across restart | **MET** | Forward: futures (#1) + option (#4) + position (#7, fill seam) canonical-derived. Restart: restore stays legacy at construction (Option B), upgraded by the post-gate pass (`canonicalize_restored_orders` + `canonicalize_restored_positions`) — slotted after MM.4 readiness, before reconcile (`driver._run_startup_gate`, AST-pinned ordering). |
| **4** | Carve-outs documented, not silent | **MET** | Equity (ISIN-less, out of F&O scope), #3 greek-limit (transient), #2 batch (no live caller — see C), #5/#10 (prove-dead), restore-at-construction (Option B), expired-option edge — each named in the guard allowlists and §E below. |
| **5** | Mechanically verifiable closure guard exists | **MET** | `tests/g1/test_g1_closure_guard.py` — 19 tests (AST + grep + characterization), committed `87f5b2f`, green. A new unaudited identity-construction site or a `CanonicalInstrument` crossing the order/persistence/broker boundary fails it. |
| Boundary | `CanonicalInstrument` never crosses `NormalizedOrder` / persistence / broker payload | **MET** | No canonical import on the boundary files; `instrument_key` absent from `core/execution/`; order path does not import `core/brokers/mapping`; persisted DDL is symbol-keyed. |

---

## C — Independent call-graph audit (does the live path have a single canonical funnel?)

The guard asserts *structure*; this confirms *reachability* — that the parse-using carve-outs are not on any live path.

- **`process_signal` is the sole runtime order-build entry.** Its only non-docstring caller is `LoopDriver._dispatch_signals` → `self._execution.process_signal(signal, bar.close)` (`driver.py:627`). ADR-006 holds: the driver is the single runtime caller; the `SignalSource` seam holds no handler handle.
- **`process_group_signal` (the #2 batch path that still calls `InstrumentParser.parse`) has NO caller** — repo-wide grep finds only its definition. It is unreachable on the live path; its parse use is a documented dead/carve-out surface, not an open identity gap.
- **No live `LoopDriver(...)` is constructed** outside `tests/`. The only match in `core/`/`scripts/`/`flask_app/` is a *docstring* in `master_readiness.build_master_readiness` describing the future F&O entry script (`LoopDriver(master_readiness=...)`). So no production code can even drive the batch/option-live paths today — the live order funnel is exactly `process_signal`, which is fully canonical.
- **`_check_greek_limits` (#3)** is called only from `process_signal:540`; its `parse` result is transient and never leaves the site (greeks dispatch on `asset_class`, 4C.6).

The live identity funnel is therefore single and canonical. Nothing reaches a non-canonical construction on a live F&O order/restore path.

---

## D — Test evidence

- `pytest tests/g1/test_g1_closure_guard.py -q` → **19 passed**.
- `pytest -q` → **441 passed, 0 failing** (the Wave-5 guard added 19 to the prior 422; no regressions).
- The full G1 characterization corpus (Wave 2A / 3A / 3B / 4A1 / 4B / restore canonicalization) remains green — every migration wave's behavior-preserving claim still holds at closeout.

---

## E — Remaining exclusions (documented, NOT identity-path gaps)

Carried from `G1_WAVE5_CLOSURE_GUARD_REPORT.md` §3 and re-affirmed by this audit: equity carve-out; #3 greek-limit; #2 batch (no live caller); #5 `OrderFactory` / #10 `NormalizedOrder(symbol=)` prove-dead; restore-at-construction (Option B); expired/rolled restored option; `core/brokers/mapping/*` (the 4C.7-blocked projection, unwired into the order path). None are reachable as a non-canonical identity source on a live F&O path.

---

## F — What G1 closure does and does NOT unblock

**Closes:** the identity-architecture program. `CanonicalInstrument` is the sole live-F&O identity source; the closure guard standing-enforces it.

**Does NOT unblock live trading.** G1 was behavior-preserving (it changed *where* identity is sourced, not the broker payload). The critical path now shifts off identity architecture onto the live-enablement track, none of which G1 closure resolves:

1. **MM.7 live wiring** — the F&O entry script that constructs a live `LoopDriver`, injects `build_master_readiness(...)`, and wires the deferred `broker_positions` reconciliation source (Planned #4/#6). Until it exists, `process_signal`'s canonical option/futures path is never *driven* live.
2. **F3 — tick-size paise scaling** (open defect): normalize at ingest / resolver boundary before any 4C.7 price-rounding consumer.
3. **F4 — lot verification** (NIFTY 65 / BANKNIFTY 30): exchange-circular confirmation before the live option path sizes real orders.
4. **Live F&O enablement** — additionally gated by the F&O product/segment model (Planned #4) and the SPAN margin engine (Planned #5).

4C.7 (the broker-payload change that *uses* `ci.instrument_key`/`ci.product`) remains blocked; G1 closure is its identity-side precondition, not its trigger.

---

## Verdict

| Axis | Result |
|---|---|
| §6 criteria #1–#5 + boundary | ALL MET (§B) |
| Live call-graph single canonical funnel | CONFIRMED (§C) |
| Test suite | 441 passing, 0 failing (§D) |
| Carve-outs | documented, none live-reachable (§E) |

**GATE G1: OPEN → CLOSED (2026-06-11).** `SOLE_IDENTITY_PATH_REVIEW.md` flips to "No — `CanonicalInstrument` is the sole identity source." The next program is live-enablement (MM.7 wiring, F3, F4, F&O product/margin), a different class of work from the G1 identity program.
