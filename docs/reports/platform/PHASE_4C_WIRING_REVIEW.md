# PHASE_4C_WIRING_REVIEW.md

**Type:** Wiring review at the 4C.5 pause — **no code changes; survey only.**
**Date:** 2026-06-08
**Phase:** after 4C.1–4C.5 (build-seam adaptation), before 4C.6/4C.7.
**Purpose:** the precursor to the formal **Review Gate G1** (`docs/reports/PHASE_4C_IMPLEMENTATION_PLAN.md` §2). Answers three questions: who consumes `InstrumentResolver`, what is `InstrumentMaster`'s status, and which legacy identity paths remain.
**Basis:** direct grep of `core/**` (non-docs) for `InstrumentResolver`/`CanonicalInstrument`/`UpstoxMapping`, `InstrumentMaster`/`instrument_db`, and `InstrumentParser.parse`; suite at 300 passing.

> Every claim is `file:line`-anchored. The headline is deliberately honest (see §4): **today the answer to Gate G1 is still "Yes — legacy construction remains."** A gate that reported green here would be the silent-failure pattern this work exists to remove.

---

## 1. Resolver consumers (who uses `InstrumentResolver` / the canonical layer)

| Consumer | Site | Status | Notes |
|---|---|---|---|
| `OptionsContractSelector` | `selector.py:6,70,109` | **WIRED but DORMANT** | 4C.5: sources `lot_size` from `resolve_option(...)`. The handler instantiates `OptionsContractSelector()` **without** a resolver (`handler.py:505`), so a default resolver is built over the **absent** master DB → `resolve_option` returns `None` → falls back to `INDEX_LOT_SIZES` (`selector.py:109-114`). Identical legacy lot today; resolver-sourced once the DB is materialized. |
| `UpstoxMapping` | `brokers/mapping/upstox.py:31` | **DORMANT (not wired)** | Composes a resolver. **No live code imports `UpstoxMapping`** — only `tests/brokers/test_upstox_mapping.py`. It is built, tested architecture awaiting the 4C.7/4C.8 order/recon seams. |
| `InstrumentResolver` itself | `instruments/resolver.py` | reader of the master | The only reader of the master SSOT; `resolve_equity/index/future/option`, `resolve_by_instrument_key`, as_of-aware. |
| Tests | `tests/instruments/*`, `tests/brokers/test_upstox_mapping.py`, `tests/execution/test_selector_resolves.py` | green (44 tests) | Exercise the canonical layer in isolation against fixture masters. |

**Net:** the **only live consumer** of the resolver is the selector, and it is **dormant** because the master DB is absent (so the byte-for-byte legacy fallback runs). `UpstoxMapping`/`CanonicalInstrument` do **not** appear on any runtime path yet.

---

## 2. `InstrumentMaster` (`instrument_db.py`) status

- **Importers in code: ZERO.** Grep for `InstrumentMaster` / `instrument_db` across `core/**` returns only `instrument_db.py` itself (class definition + its own docstring example). No execution, runtime, broker, or facade module imports it.
- **Schema consistency:** 4C.1 changed the master to a snapshot time-series (`PRIMARY KEY (instrument_key, snapshot_date)`). `InstrumentMaster`'s queries are `... LIMIT 1` with **no snapshot filter** (`instrument_db.py:50,118,143`), so against a multi-snapshot table they would return an **arbitrary** snapshot. Because nothing calls it and the prod DB is absent, this has **no live effect**.
- **Decision (locked, `PHASE_4C_IMPLEMENTATION_PLAN.md` §6.1): DEPRECATE, do not repair.** `InstrumentResolver` is the one reader of the master. `InstrumentMaster` is dead code to be removed when convenient; it must **not** be made snapshot-aware. No work is spent fixing its queries.

---

## 3. Remaining legacy identity paths (construct identity WITHOUT the resolver)

All of these still mint identity from `InstrumentParser.parse` / direct `Equity`/`Option` construction — i.e. **not** through `InstrumentResolver`, and they do **not** produce a `CanonicalInstrument`:

| # | Path | Site | Produces |
|---|---|---|---|
| 1 | Handler `process_signal` non-option branch | `handler.py:513` | legacy `Option`/`Equity` |
| 2 | Handler batch/group order build | `handler.py:621` | legacy `Option`/`Equity` |
| 3 | Handler `_check_greek_limits` | `handler.py:720` | legacy (then `GreeksCalculator` isinstance) |
| 4 | Handler option branch (selector) | `handler.py:505` → `selector.py` | legacy `Option` (lot_size now resolver-sourced, but the **object is still a legacy `Option`**, not canonical) |
| 5 | `OrderFactory.create_order` | `order_factory.py:34` | legacy |
| 6 | `Position` legacy `symbol=` ctor | `position_models.py:47` | legacy |
| 7 | `PositionTracker` symbol→position | `position_tracker.py:31` | legacy |
| 8 | Order restore (replay) | `order_repository.py:60` | legacy (re-parses persisted display symbol) |
| 9 | Position restore (replay) | `position_repository.py:51` | legacy |
| 10 | `NormalizedOrder` legacy `symbol=` ctor | `order_models.py:62-70` | direct `Equity` |
| 11 | `GreeksCalculator` dispatch | `greeks_calculator.py:27,38,52` | `isinstance(Equity/Future/Option)` — legacy-typed |

**Why these were deliberately left (per the 4C.5 design decision):**
- **ADR-003 determinism.** The build seam's output type must not flip on DB presence. "Canonical-if-resolvable-else-legacy" would yield different types in different environments and, worse, across a restart (a fresh order built canonical, then `order_repository.py:60` re-parses the persisted symbol back to legacy). So 4C.5 keeps legacy types and only moves the `lot_size` *source*.
- **Equity needs ISIN.** A canonical `EQUITY` requires `isin` (`canonical.py:_validate`); a bare display symbol (`"RELIANCE"`) cannot supply one while the master is absent, so forcing canonical here would raise on the live equity path. Equity stays legacy until the master ingests NSE_EQ with ISIN.
- **Greeks stay legacy-correct.** Keeping legacy types means `isinstance` dispatch (`greeks_calculator.py`) and `_check_greek_limits` still fire — **zero regression** in the untested live path. The `asset_class` dispatch (4C.6) is done only when canonical actually flows (4C.7, DB present).

---

## 4. Gate G1 answer (honest)

> **Q: Can any live execution path still construct an instrument without going through `InstrumentResolver`?**
> **A (today): YES.** Orders, positions, greeks, and persistence-restore all still build legacy `Option`/`Equity` via `InstrumentParser.parse` / direct construction (§3). `CanonicalInstrument` does **not** flow into orders. The resolver is consulted only for the selector's `lot_size`, and even that is **dormant** because the master DB is absent.

This is the expected state after the *conservative* 4C.5 and is **not** a failure — it is the truthful baseline the formal Gate G1 will close.

### The true unblocker
**Materializing the master DB (`data/instruments/…`, run `scripts/fetch_instrument_master.py`) is the single prerequisite** for both Gate G1 and 4C.7:
- with the DB present, the resolver returns real `CanonicalInstrument`s (incl. NSE_EQ + ISIN once ingest covers equities),
- 4C.7 can then make the order-build seam resolve a `CanonicalInstrument` and call `UpstoxMapping.to_broker(ci)` for `instrument_key` + product,
- 4C.6 converts greeks to `asset_class` dispatch as canonical begins to flow,
- and the remaining §3 paths are migrated to the resolver, flipping the Gate G1 answer to **"No."**

### What is already true (the foundation)
- Canonical identity, resolver (as_of-aware, observable fallback), and the Upstox mapping (round-trip-proven) exist and are **44 tests** green.
- They are **unwired** into the runtime — so the live system behaves exactly as before this phase (full suite **300 passing**, no regressions).

---

## Appendix — source anchors

| Claim | Anchor |
|---|---|
| Selector consults resolver for lot_size; legacy Option returned | `core/execution/options/selector.py:70,109-118` |
| Handler builds selector without a resolver | `core/execution/handler.py:505` |
| UpstoxMapping composes resolver; no live importer | `core/brokers/mapping/upstox.py:31` (grep: only tests import it) |
| InstrumentMaster has zero code importers | grep `InstrumentMaster`/`instrument_db` over `core/**` → only `instrument_db.py` |
| InstrumentMaster LIMIT-1 queries, snapshot-blind | `core/instruments/instrument_db.py:50,118,143` |
| Legacy parser call sites | `handler.py:513,621,720`; `order_factory.py:34`; `position_models.py:47`; `position_tracker.py:31`; `order_repository.py:60`; `position_repository.py:51` |
| NormalizedOrder legacy Equity ctor | `core/execution/order_models.py:62-70` |
| Greeks isinstance dispatch | `core/risk/greeks/greeks_calculator.py:27,38,52` |
| Full suite green | 300 passing (44 canonical-layer tests) |
