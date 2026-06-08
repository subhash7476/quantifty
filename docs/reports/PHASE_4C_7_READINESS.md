# PHASE_4C_7_READINESS.md

**Type:** Readiness verdict — survey + Go/No-Go only; **no code.**
**Date:** 2026-06-08
**Question:** *Is Phase 4C.7 (wire the order seam — ship resolved `instrument_key` + product to the live broker adapter) ready to start?*
**Inputs:** `docs/reports/PHASE_4C_IMPLEMENTATION_PLAN.md` (§2 slice 4C.7 + Review Gate G1, §6.2 locked decisions) · `docs/reports/PHASE_4C_WIRING_REVIEW.md` · `docs/reports/MASTER_MATERIALIZATION_READINESS.md` · `docs/reports/MASTER_MATERIALIZATION_POLICY.md`.

---

## Verdict: **NO-GO**

4C.7 is the first slice that ships broker identity (`instrument_token` = resolved `instrument_key`, product from `ci.product`) to the **live** order path. The plan makes it conditional on objective preconditions. **Two of them fail right now**, each verifiable, so the verdict is certain — not a judgment call.

> A "Go" here would be the silent-failure pattern this whole phase exists to remove (the wiring review's own standard). The honest answer is **No**, with a checkable path to Yes.

## Blocking conditions

| # | Precondition | State | Evidence | Flips to GO when |
|---|---|---|---|---|
| 1 | **Gate G1 — `CanonicalInstrument` is the *sole* identity source on live order paths** | ❌ **OPEN** | `SOLE_IDENTITY_PATH_REVIEW.md` does **not exist** (glob: none). The wiring review still answers G1 **"Yes — legacy construction remains"**: 11 enumerated sites mint identity via `InstrumentParser.parse` / direct `Option`/`Equity` ctors (handler order-build `handler.py:513,621`, `OrderFactory:34`, `Position:47`, `NormalizedOrder:62-70`, restore paths, …). | the report is produced and concludes **"No — canonical is the sole identity source"**, with every live construction site either resolver-sourced or proven dead. |
| 2 | **Master materialized AND content-verified on disk** | ❌ **OPEN** | `data/instruments/**` is **empty** (glob: no files). No snapshot exists; the resolver returns `None` for everything; the coverage acceptance check (`MASTER_MATERIALIZATION_POLICY.md` §3) has never run. | the refresh job has run in the target env, the DB exists, and the §3 coverage assertions pass (segments non-empty, EQ ISIN, active weekly expiry per underlying). |
| 3 | **Staleness + fail-fast startup gate implemented** | ❌ **OPEN (designed, not built)** | `MASTER_MATERIALIZATION_POLICY.md` §4/§5 specify it, but nothing is implemented: no `EventType.INSTRUMENT_MASTER_UNAVAILABLE` (`event_journal.py:52-70`), no master check in `_run_startup_gate()` (`driver.py:326`), no `latest_snapshot_date()` on the resolver. The live F&O path still soft-falls-back silently. | policy §9 is implemented + tested: the gate refuses to start a LIVE F&O run on an absent/stale/under-covered master. |
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
