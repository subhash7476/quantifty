# PHASE_4C_IMPLEMENTATION_PLAN.md

**Type:** Implementation plan — ready for execution. **Not yet implemented; no code written in this phase.**
**Date:** 2026-06-08
**Phase:** 4C — Canonical Instrument Model
**Predecessor:** `docs/reports/CANONICAL_INSTRUMENT_ARCHITECTURE.md` (Phase 4A/4B design) · `docs/reports/FNO_PRODUCT_DISCOVERY.md`
**Governing law:** `docs/PLATFORM_CONSTITUTION.md` v1.0 · ADR-001/002/003/006 · `docs/PROJECT_STATE.md` (Planned #4/#5/#6).
**Methodology:** TDD (RED→GREEN), strangler-fig, one shippable slice per step, full suite green between slices. Mirrors the LoopDriver phasing already used in this repo.

> This is the exact scope of Phase 4C. It implements the §D9 migration as ordered, independently-shippable slices. It does **not** implement SPAN (#5), the full product model (#4), or reconciliation (#6) — it builds the **foundation those consume**. Slices 4C.7–4C.8 are the only ones that change live behavior, and only for paths that are currently broken.

---

## 1. Goal & success definition

Replace three-way-divergent, broker-coupled, display-string identity with **one platform-owned canonical identity** sourced from an `as_of`-aware instrument-master SSOT, addressed by a deterministic resolver, bridged to brokers by a tested mapping layer — covering **EQUITY, INDEX, FUTURE, OPTION** from day one.

**Phase 4C is DONE when:**
1. `InstrumentResolver.resolve_*(...)` returns a `CanonicalInstrument` for each of EQ/IDX/FUT/OPT, sourced from the materialized master, `as_of`-correct.
2. `canonical_id` is deterministic and broker-independent; `key(attrs) == expected` holds in unit tests with no DB.
3. `UpstoxMapping` round-trips (`from_broker(to_broker(ci)) == ci`) across a sampled EQ/IDX/FUT/OPT cross-section.
4. The live order path ships the **`instrument_key`** (resolved) as `instrument_token` and the **product code** from `ci.product` — F&O order placement is structurally correct (paper-verified).
5. `ReconciliationEngine` matches **canonical_id ↔ canonical_id**.
6. The `multiplier == lot_size` invariant holds; `MarginTracker` F&O notional is correct (test-asserted).
7. Canonical core has **no broker/strategy import** (ast guard green); full suite green; no regression in Runtime/PortfolioView/Telemetry/Execution behavior.

**Explicitly out of scope (downstream phases):** SPAN parameter sourcing & scenario engine (#5); NRML/carry *risk* policy (#4 beyond the product field); the funds/holdings endpoints (#6 beyond position recon); unifying the two `BrokerAdapter` ABCs (recommended as a #6 companion, noted in §6).

---

## 2. Slices (each = one PR, RED→GREEN, suite green before next)

### 4C.1 — Extend the SSOT (master ingest + schema), no consumers
**Files changed:** `scripts/fetch_instrument_master.py` (ingest NSE_EQ + NSE_INDEX; add `isin`, `tick_size`; effective-dated `lot_size`), schema in same file (`_CREATE_TABLE`).
**Files created:** none (data artifact materialized by running the script; consider renaming `nse_fo_instruments.duckdb` → `instruments.duckdb` since it is no longer FO-only — decision recorded in this slice).
**Tests:** `tests/instruments/test_master_ingest.py` — EQ/INDEX rows present; `isin`/`tick_size` populated; lot_size effective-dating shape; idempotent refresh.
**Risk:** additive only; nothing reads the new columns yet.

### 4C.2 — `CanonicalInstrument` + identity (pure, unwired)
**Files created:** `core/instruments/canonical.py` (`CanonicalInstrument` frozen value object, `AssetClass` enum incl. INDEX, `tradable` rule), `core/instruments/identity.py` (`normalize_underlying()`, `canonical_id(attrs)` minting per §D4.1).
**Tests:** `tests/instruments/test_canonical.py`, `tests/instruments/test_identity.py` — `key(attrs)==expected` for all four classes; underlying normalization table; `multiplier==lot_size` invariant; INDEX is non-tradable; ast guard (no broker/strategy import).
**Risk:** none; no wiring.

### 4C.3 — `InstrumentResolver` (over the master, as_of-aware, unwired)
**Files created:** `core/instruments/resolver.py` (`InstrumentResolver`, the §D7 API).
**Files changed:** `core/instruments/instrument_db.py` only if a thin read helper is needed (prefer additive).
**Tests:** `tests/instruments/test_resolver.py` — resolve EQ/IDX/FUT/OPT from a fixture DB; `as_of` returns effective lot_size (50 vs 75 across the SEBI boundary); deterministic; cache keyed by `(canonical_id, as_of)`; loud fallback when master absent.
**Risk:** none; no wiring.

### 4C.4 — `BrokerMapping` interface + `UpstoxMapping` (projection, unwired)
**Files created:** `core/brokers/mapping/base.py` (`BrokerMapping` ABC, `BrokerRef`), `core/brokers/mapping/upstox.py` (`UpstoxMapping`).
**Tests:** `tests/brokers/test_upstox_mapping.py` — round-trip `from_broker(to_broker(ci))==ci`; golden fixtures (frozen master slice → expected canonical_id); orphan/coverage; product-code translation (`CNC/NRML/MIS` ⇄ Upstox).
**Risk:** none; no wiring.

### 4C.5 — Adapt the build seam (behavior-preserving)
**Files changed:** `core/execution/options/selector.py` (policy kept; lot_size/tick_size/identity via resolver; hardcoded tables → logged fallback), `core/instruments/instrument_parser.py` (delegate to resolver, thin fallback). `CanonicalInstrument` exposes `.symbol`(=display)/`.type`/`.multiplier` so `NormalizedOrder`/`Position`/`MarginTracker` read unchanged.
**Tests:** `tests/execution/test_selector_resolves.py`, updated parser tests — same display symbol out; lot_size now from master; fallback path logged.
**Risk:** low; numbers identical except corrected lot_size (asserted).
**Gate:** on completion, **Review Gate G1** (below) must be produced and pass before 4C.7.

### 4C.6 — Greeks dispatch on `asset_class` (close the isinstance surface)
**Files changed:** `core/risk/greeks/greeks_calculator.py:27,38,52` (isinstance → `asset_class`).
**Tests:** updated greeks tests — EQ/FUT/OPT branches via asset_class; parity with prior numbers.
**Risk:** bounded to 3 known sites (grep-verified).

### REVIEW GATE G1 — Sole Identity Path (mandatory, blocks 4C.7)
**When:** after 4C.5 (and 4C.6), **before any change to order routing (4C.7).**
**Why:** 4C.7 begins shipping `instrument_key` / `product` / broker identity to live adapters. That is only safe if `CanonicalInstrument` is already the *sole* identity source — otherwise a live order could be built from a non-canonical instrument and routed with a wrong/absent broker key.

**Required deliverable — a written report answering one question:**

> **Can any live execution path still construct an instrument without going through `InstrumentResolver`?**
> **Required answer: No.**

**Evidence the report must present (checkable, file:line-anchored):**
- Every live instrument-construction site is enumerated: `handler.py` order-build (`:503-513` selector/parser branch), `OrderFactory.create_order` (`order_factory.py:34`), `Position` legacy ctor (`position_models.py:47`), `NormalizedOrder` legacy ctor (`order_models.py:62-70`), `OptionsContractSelector.select` (`selector.py`).
- For each: it now obtains identity from `InstrumentResolver` (or a `CanonicalInstrument` the resolver produced), **or** it is proven dead on the live path (no `LoopDriver`-reachable caller).
- A grep-backed scan shows no live path calls `InstrumentParser.parse` / constructs `Equity`/`Option`/`Future` directly to obtain *order identity* (fallbacks must be logged + non-authoritative).
- Backtest/research paths resolve with an explicit `as_of`.

**Outcome:** the report (e.g. `docs/reports/SOLE_IDENTITY_PATH_REVIEW.md`) must conclude **"No — `CanonicalInstrument` is the sole identity source"** with evidence. If the honest answer is still "Yes," 4C.7 does **not** start; the offending path is migrated first. This is a hard gate, reviewable on the same footing as the ADR-002 import scan.

### 4C.7 — Wire the order seam (first live-behavior change; currently broken)
**Precondition:** Review Gate G1 passed.
**Files changed:** `core/brokers/upstox_adapter.py:82,86` (`instrument_token` = resolved `instrument_key`; product code from `ci.product`), the handler order-build seam (`handler.py:503-545`) to carry the resolved `CanonicalInstrument`.
**Tests:** `tests/brokers/test_place_order_resolution.py` — F&O order ships instrument_key not display symbol; product honored; equity path unchanged. Paper-broker end-to-end.
**Risk:** medium — but the path it replaces is non-functional for F&O, so there is no working behavior to regress; gate behind paper test.

### 4C.8 — Wire reconciliation (canonical ↔ canonical)
**Files changed:** `core/execution/reconciliation.py` (match on `canonical_id` via `from_broker_position`), the broker→recon normalizer.
**Tests:** `tests/execution/test_recon_canonical.py` — broker position resolves to canonical_id; QUANTITY_MISMATCH/ORPHANED detected on canonical keys; format-mismatch bug gone.
**Risk:** low — recon is operationally dead today (no live feed), so this is additive correctness.

---

## 3. Tests required (summary)

| Area | New test file | Core assertion |
|---|---|---|
| Master ingest | `tests/instruments/test_master_ingest.py` | EQ/INDEX present; isin/tick_size; effective-dated lot |
| Canonical object | `tests/instruments/test_canonical.py` | frozen; multiplier==lot_size; INDEX non-tradable |
| Identity | `tests/instruments/test_identity.py` | `key(attrs)==expected`; underlying normalization; determinism |
| Resolver | `tests/instruments/test_resolver.py` | as_of lot_size (50/75); 4 asset classes; cache; fallback |
| Broker mapping | `tests/brokers/test_upstox_mapping.py` | round-trip; golden; coverage; product translation |
| Selector seam | `tests/execution/test_selector_resolves.py` | same display; lot from master |
| Greeks | (update existing) | asset_class dispatch parity |
| Order seam | `tests/brokers/test_place_order_resolution.py` | instrument_key shipped; product honored |
| Recon | `tests/execution/test_recon_canonical.py` | canonical↔canonical match |
| Import guard | within test_canonical | no broker/strategy import in canonical core |

---

## 4. ADR implications

**Propose a new ADR (text below) — do NOT append it in Phase 4A/4B; it is enacted when Phase 4C lands.** `ARCHITECTURE_DECISIONS.md` is append-only; this is the draft to add at implementation time.

> ### ADR-007 — Platform Owns Instrument Identity (draft, enact in 4C)
> **Status:** Proposed.
> **Decision:** The platform's canonical instrument identity is a **deterministic, broker-independent structured key** (`canonical_id`), minted by the `InstrumentResolver` from exchange-master attributes (derivatives: underlying+expiry+strike+type; equity: ISIN). Broker identifiers (`instrument_key`, `tradingsymbol`, `exchange_token`, product codes) are **mapping attributes**, never identity, isolated in a per-broker `BrokerMapping`. Identity resolution is **`as_of`-aware** (live==replay, ADR-003). The canonical core imports no broker or strategy code (ADR-002).
> **Consequences:** identity survives broker swaps; a second minting authority is forbidden (ADR-001); display symbols are derived, not authoritative; `multiplier == lot_size` is a platform invariant.

**Existing ADRs honored:** ADR-001 (no new store/authority — resolver reads the master, mapping is a projection), ADR-002 (import guard), ADR-003 (deterministic + as_of), ADR-006 (resolver is pure infra, never a runtime orchestrator).

**Constitution follow-up (non-blocking):** reconcile §9 "Equity Futures" vs the task's "Equity Swing (cash)" — both are now representable; the wording should be aligned (separate ticket).

---

## 5. Files: created vs changed (consolidated)

**Created:** `core/instruments/canonical.py`, `core/instruments/identity.py`, `core/instruments/resolver.py`, `core/brokers/mapping/base.py`, `core/brokers/mapping/upstox.py`, + the test files in §3. Draft `ADR-007` (enacted at 4C close).

**Changed:** `scripts/fetch_instrument_master.py` (+schema), `core/execution/options/selector.py`, `core/instruments/instrument_parser.py`, `core/risk/greeks/greeks_calculator.py`, `core/brokers/upstox_adapter.py`, `core/execution/handler.py` (order-build seam), `core/execution/reconciliation.py`.

**Data artifact materialized:** `data/instruments/instruments.duckdb` (today absent).

**Untouched (no behavior change):** `core/runtime/*` (driver/telemetry/journal), `core/execution/portfolio_view.py`, `core/execution/position_tracker.py`, `core/execution/pnl_tracker.py`, the watchdog — they read `.symbol`/`.multiplier`, both preserved.

---

## 6. Sequencing notes & dependencies

- **Strict order:** 4C.1 → 4C.2 → 4C.3 → 4C.4 (all unwired) → 4C.5 → 4C.6 → 4C.7 → 4C.8. Slices 1–4 are pure additions; 5–6 are behavior-preserving adapts; 7–8 are the only live-behavior changes and touch only currently-broken paths.
- **Unblocks:** Planned #4 (product/segment now on the canonical object), #5 (SPAN consumes `underlying/expiry/strike/lot_size` + the `multiplier==lot_size` notional), #6 (recon now canonical↔canonical; the two-ABC merge + funds endpoint remain #6's own scope).
- **Recommended companion for #6 (not in 4C):** collapse the two `BrokerAdapter` ABCs (`base.py` vs `broker_base.py`) and put `get_positions` on the driver's contract — flagged here because 4C.8 surfaces it, but it is reconciliation scope, not identity scope.

### 6.1 Standing decisions (locked — do not relitigate in later slices)
- **`InstrumentMaster` (`instrument_db.py`) → DEPRECATE, do not repair.** 4C.1 made it schema-inconsistent (composite `(instrument_key, snapshot_date)` PK means its `... LIMIT 1` reads return an arbitrary snapshot). It has **no live caller** and the prod DB is absent, so it is not a live break. The decision is **not** to make it snapshot-aware; `InstrumentResolver` is the one reader of the master. The wiring slices retire `instrument_db.py` usages rather than fixing its queries; it is removed once no caller remains.
- **Snapshot retention → DOCUMENT, do not solve (in 4C).** Daily full-master snapshots grow `instruments` (~100k rows/day) and `resolve_future`/`resolve_index` Python-filter after a coarse SQL pull. Acceptable at current scale; a retention policy / snapshot index is a follow-up, recorded in §7, **not** built in Phase 4C.
- **Sole-identity gate (G1) is mandatory before 4C.7.** See Review Gate G1 in §2.

---

## 7. Risk register

| Risk | Mitigation |
|---|---|
| as_of effective-dating from daily snapshots | **DONE (4C.3):** master is a snapshot time-series; resolver returns the snapshot effective at `as_of`. When `as_of` precedes all snapshots it **logs a warning** and returns the earliest (observable, not silent — Constitution §6 / ADR-004); pinned by `test_as_of_before_history_warns_and_returns_earliest`. |
| Underlying normalization misses a symbol | table-driven `normalize_underlying`; loud failure, never silent wrong key (4C.2) |
| Display-symbol consumers break on value-object swap | `CanonicalInstrument` preserves `.symbol/.multiplier`; isinstance surface bounded to 3 greeks sites (4C.6) |
| Live order seam regression | path is broken today for F&O; gated behind paper-broker e2e + Review Gate G1; equity path explicitly asserted unchanged |
| Master DB still absent at runtime | resolver fallback logs loudly (not silent); 4C.1 makes materialization a documented prerequisite |
| Snapshot table growth (~100k rows/day) | **Documented, not solved in 4C** (§6.1): add retention policy / snapshot index when the real master is materialized at scale |
