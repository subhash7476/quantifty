# PHASE_4C_7_READINESS.md

**Type:** Readiness verdict — survey + Go/No-Go only; **no code.**
**Date:** 2026-06-08
**Question:** *Is Phase 4C.7 (wire the order seam — ship resolved `instrument_key` + product to the live broker adapter) ready to start?*
**Inputs:** `docs/reports/PHASE_4C_IMPLEMENTATION_PLAN.md` (§2 slice 4C.7 + Review Gate G1, §6.2 locked decisions) · `docs/reports/PHASE_4C_WIRING_REVIEW.md` · `docs/reports/MASTER_MATERIALIZATION_READINESS.md` · `docs/reports/MASTER_MATERIALIZATION_POLICY.md`.

---

> **Status update (2026-06-09) — the blocking table below is the 2026-06-08 snapshot; current state has advanced.** Since this verdict: **Phase MM.1–MM.4** built the staleness + coverage startup gate condition #3 designed (logic implemented + tested, 352 green; commits `f8b26cd`/`db7a7d4`), and **Phase MM.5** materialized + content-verified the master, **closing condition #2** (`data/instruments/nse_fo_instruments.duckdb`, 65,383 rows, coverage + resolver + gate all green — `MM.5_MATERIALIZATION_REPORT.md`). **The verdict remains NO-GO**, now on three open items tracked in `PROJECT_STATE.md`: **Gate G1** (condition #1, unchanged — the longest pole), the **OS-scheduled refresh job** (policy §2 — next milestone **MM.6**, `MM.6_REFRESH_JOB_PLAN.md`), and **production checker wiring** into a live F&O entry script (the MM.4 gate logic exists but is injected only in tests — milestone **MM.7**). The point-in-time table is retained below as the historical record; `PROJECT_STATE.md` is the live tracker.

## Verdict: **NO-GO**

4C.7 is the first slice that ships broker identity (`instrument_token` = resolved `instrument_key`, product from `ci.product`) to the **live** order path. The plan makes it conditional on objective preconditions. **Two of them fail right now**, each verifiable, so the verdict is certain — not a judgment call.

> A "Go" here would be the silent-failure pattern this whole phase exists to remove (the wiring review's own standard). The honest answer is **No**, with a checkable path to Yes.

## Blocking conditions

| # | Precondition | State | Evidence | Flips to GO when |
|---|---|---|---|---|
| 1 | **Gate G1 — `CanonicalInstrument` is the *sole* identity source on live order paths** | ❌ **OPEN (plan produced 2026-06-09)** | `SOLE_IDENTITY_PATH_REVIEW.md` now **exists** — but as the migration **plan**, concluding **"Yes — legacy construction remains" (OPEN)**: 11 sites surveyed + classified (MIGRATE/DERIVE/CARVE-OUT), restore strategy Option B locked, 5 waves, measurable closure criterion. **No order-path code written.** The 11 sites still mint identity via `InstrumentParser.parse` / direct ctors (`handler.py:513,621`, `OrderFactory:34`, `Position:47`, `NormalizedOrder:62-70`, restore paths, …). | the review is executed (Waves 1–5) and **re-concludes "No — canonical is the sole identity source"**, every live F&O construction site resolver-sourced/derived or proven dead, with the AST guard test green. |
| 2 | **Master materialized AND content-verified on disk** | ✅ **CLOSED (MM.5, 2026-06-09)** | `data/instruments/nse_fo_instruments.duckdb` materialized via the production path — single snapshot `2026-06-08`, 65,383 rows; the §3 coverage acceptance check **passed** (segments non-empty, EQ-ISIN 100%, active weekly expiry present for NIFTY + BANKNIFTY), resolution returns `CanonicalInstrument` (not `None`), and `assess()` → FRESH. *(`MM.5_MATERIALIZATION_REPORT.md`)* | ✅ cleared. |
| 3 | **Staleness + fail-fast startup gate implemented** | ⚠ **PARTIAL (gate logic MM.4 + refresh MM.6 + checker factory MM.7 all BUILT; only the live entry-script call-site remains)** | **Gate logic** (MM.1–MM.4, `f8b26cd`/`db7a7d4`): `INSTRUMENT_MASTER_UNAVAILABLE`/`_STALE`, the master check in `_run_startup_gate()` (before reconciliation), `latest_snapshot_date()` + `assess()` + coverage facts. **Refresh job** (MM.6): validate-before-publish staging, IST stamping, transactional writes, `run_refresh` + OS-scheduler artifact (OS-task install pending). **Production checker** (MM.7): `build_master_readiness(underlyings, db_path)` constructs the real resolver-backed checker, proven through the gate FRESH end-to-end (369 green). **Remaining:** the live **F&O entry script** that constructs the `LoopDriver` and passes the checker in does **not** exist (`LoopDriver` is constructed only in tests) — that is the F&O runtime slice (Planned #4: provider/execution/order routing), **not** an MM-scope item. | the F&O entry script constructs the live `LoopDriver` and invokes `build_master_readiness(...)` (Planned #4 / F&O runtime). |
| 4 | **Finding 2 — `options_provider` snapshot-blind reads** | ✅ **DONE** | Remediated + committed (`654ba49`): all four master reads scope to the latest snapshot; +4 TDD tests; suite 312 green. | — (cleared) |

## What this session did — and did NOT — advance

This session closed 4C.6 (greeks `asset_class` dispatch) and Finding 2 (options chain-discovery reads). **Neither touches Gate G1.** Greeks dispatch and chain-discovery are *not* order-identity construction: the 11 legacy identity sites the wiring review enumerated (order-build, factory, position/order ctors, restore) are **untouched**. G1 is therefore **fully open and independent** — do not read "Finding 2 cleared" as momentum toward G1. It is a separate gate that still requires its own migration + report.

**Design ≠ precondition met.** `MASTER_MATERIALIZATION_POLICY.md` *specifies* conditions 2 and 3; it does not satisfy them. A materialized, verified master and a *working* fail-fast gate are the preconditions — the policy is the blueprint for building them, not evidence they exist.

## Path to GO (ordered)

1. **Implement the materialization policy** (`MASTER_MATERIALIZATION_POLICY.md` §9): `latest_snapshot_date()` + coverage `master_readiness()`, `INSTRUMENT_MASTER_UNAVAILABLE`, the `_run_startup_gate()` integration (LIVE + F&O scoped), the source-contract test, and the scheduled refresh job. → clears **#3**.
2. **Materialize + verify** the master in the target environment; confirm §3 coverage passes. → clears **#2**. (Do this early — Finding 1: snapshot history is forward-only and unrecoverable for past dates.)
3. **Migrate the 11 legacy identity sites** to resolver-sourced `CanonicalInstrument` (or prove them dead), then **produce `SOLE_IDENTITY_PATH_REVIEW.md`** concluding "No." → clears **#1** (the hard gate, plan §2).
4. **Re-evaluate this verdict.** Only when #1–#3 are all ✅ does 4C.7 start.

**Sequencing note:** #1 and #2 are independent and can proceed in parallel; #3 (G1) is the longest pole and the true unblocker — it is pure identity-path migration, unaffected by the master being present. 4C.8 (canonical reconciliation) remains downstream of 4C.7 and is not in scope here.
