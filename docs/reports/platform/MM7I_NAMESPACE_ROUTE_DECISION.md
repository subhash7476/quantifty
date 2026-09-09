# MM7I — Namespace-Mapping Route Decision (#6b.2)

**Type:** Decision — freeze the namespace-mapping route (R1 adapter-local `instrument_key` remap vs R2 full 4C.8 canonical reconcile) before any #6b.2 implementation. **No code. No adapter change. No reconciliation change. No 4C.8 work. Decision + report only.**
**Date:** 2026-06-12
**Basis:** `MM7G_NAMESPACE_CHARACTERIZATION.md` (the three namespaces, R1/R2 framing, §6.4 invalidators) · `MM7H_SHAPE_ADAPTER_REPORT.md` (#6b.1 shape adapter COMPLETE, §4 remaining work) · first-hand re-verification of every cited site (below).
**Starting state:** 516 passing · 0 failing · #6b.1 COMPLETE · #6b.2 NOT STARTED.
**Ending state (this slice):** unchanged — 516 passing · 0 failing · **#6b.2 route FROZEN = R1** · no production/test edit.

> **Scope guard.** This slice writes only this report. It touches no production code and no test. It does not start #6b.2, #6b.3, 4C.6/4C.7/4C.8, F3, or F4. It freezes the route so #6b.2 can be sized and implemented against a settled decision.

---

## 0. Headline

**Decision: take R1 — adapter-local `trading_symbol → instrument_key` remap, wired at the composition root, reusing the already-built `UpstoxMapping`.** It is unblocked today (mapping landed at 4C.4), it stays inside the G1 / 4C.7 boundary *if placed correctly* (NOT in `core/execution/`), it is fully revertible, and it makes the eventual 4C.8 strictly easier — never harder. R2 (full 4C.8 canonical↔canonical reconcile) remains the architected end-state but is blocked on resuming the paused 4C.6→4C.8 chain and is not a prerequisite for live reconcile.

The decision is conditional on two pre-checks (master coverage + `instrument_token` preservation, §4.4) and one explicit policy (unmapped-symbol handling, §4.3). Absent those, the recommendation flips to R2 (§7).

---

## 1. R1 analysis — adapter-local instrument_key remap

**Mechanism.** The broker book is re-keyed from namespace #2 (`trading_symbol`, e.g. `NIFTY26JAN2623500CE`) to namespace #1 (`instrument_key`, e.g. `NSE_FO|53001`) *before* it reaches `reconcile()`, so its keys match the internal ledger as-is. `reconcile()` is untouched.

**What already exists (no new logic needed for the translation itself):**
- `UpstoxMapping._ikey_by_tradingsymbol: tradingsymbol → instrument_key` (`core/brokers/mapping/upstox.py:60`).
- `UpstoxMapping.from_broker_position(raw) -> Optional[CanonicalInstrument]` (`:74-81`): prefers `raw['instrument_token']`/`['instrument_key']`, else falls back to `_ikey_by_tradingsymbol[trading_symbol]`, returns `None` if unmappable.
- `UpstoxMapping.to_broker(canonical) -> BrokerRef` exposing `BrokerRef.instrument_key` (`:62-72`, `base.py:17-21`).

**What R1 must ADD (small):**
1. A **public** `trading_symbol → instrument_key` accessor on `UpstoxMapping`. Today the only `instrument_key`-yielding paths are `_ikey_by_tradingsymbol` (private) and a `from_broker_position(...) → to_broker(...).instrument_key` round-trip. R1 needs a thin direct accessor (e.g. `reconcile_key(raw) -> Optional[str]`) so the consumer does not reach into a private dict or pay a canonical round-trip that could mis-resolve ambiguous symbols. This lives in the **mapping layer** (`core/brokers/mapping/`), where `instrument_key` is legal.
2. A **composition-root binding** in `scripts/fno_runner.py`: on the `ExecutionMode.LIVE` rung only, `broker_positions = lambda: to_reconcile_positions(_remap_keys(broker.get_positions(), mapping))`, where `_remap_keys` rewrites each `Position` dict key via the accessor. `to_reconcile_positions` (`core/execution/broker_positions_adapter.py`, shape-only) is **unchanged**.
3. A defined **unmapped policy** (§4.3).

**Cost:** one small mapping accessor + one root wiring closure + one `upstox_adapter` follow-up (preserve `instrument_token`, §4.4). No `reconcile()` rewrite. No persisted-state change (reconcile is in-memory, startup-gate-only — `driver.py:482`). **Unblocked.**

**Acceptance:** flips `test_mismatched_namespace_same_position_double_false_divergence` from **2 alerts → 0** (§6).

---

## 2. R2 analysis — full 4C.8 (canonical↔canonical)

**Mechanism.** Per `PHASE_4C_IMPLEMENTATION_PLAN.md` §4C.8, `reconciliation.py` is rewritten to match on `canonical_id`: both the broker book (via `from_broker_position`) and the internal ledger are projected to namespace #3 before comparison.

**What R2 requires beyond the mapping:**
- Resume the **paused** 4C.6→4C.7→4C.8 chain (`PROJECT_STATE`: "4C.1–4C.5 IN PROGRESS, paused before 4C.6"). 4C.7 (wiring `BrokerMapping` into the order/restore path) is the gating dependency and is the very thing the G1 guard currently asserts is **not** wired (`test_g1_closure_guard.py:343-352`, `test_order_path_does_not_import_broker_mapping`).
- **Re-key the restored ledger to `canonical_id`.** Today `canonicalize_restored_positions` swaps `Position.instrument` but **preserves the `_positions` key byte-for-byte** (`handler.py:267-287`, "preserving symbol/side/quantity/avg_price (H3)"; `replace_instrument(symbol, legacy)` keeps the key). Matching on `canonical_id` requires either re-keying `_positions` to `canonical_id` or computing `canonical_id` for the internal side at compare time — a deeper change touching the ledger's identity contract.
- Rewrite `reconcile()` and its three nets to the canonical key.

**Cost:** large, multi-slice, couples live-safety reconcile to resuming a paused phase. **Blocked.** R2 is the correct **end-state** (it removes the `trading_symbol`-string fragility R1 carries) but is not justifiable as a #6b prerequisite — the same coupling anti-pattern #6a explicitly avoided.

---

## 3. Boundary review (I1) — does R1 violate any G1 boundary?

**No — provided the `instrument_key` step is placed in the mapping layer / composition root, NOT in `core/execution/`.** The G1 boundary is enforced by two executable guards:

| Guard | Site | What it forbids |
|---|---|---|
| `test_instrument_key_absent_from_execution` | `tests/g1/test_g1_closure_guard.py:333-340` | the literal string `instrument_key` in **any** `.py` under `core/execution/` |
| `test_order_path_does_not_import_broker_mapping` | `tests/g1/test_g1_closure_guard.py:343-352` | `core/execution/handler.py` importing `core.brokers.mapping` (that wiring **is** 4C.7) |

**Evidence that `core/execution` is `instrument_key`-unaware today, and must stay so:**
- The guard at `test_g1_closure_guard.py:336-340` greps every `core/execution/*.py` for `instrument_key` and asserts `offenders == []`. `reconcile()` matches raw symbol strings with no translation (`reconciliation.py:54,57,77`). The shape adapter is shape-only and key-verbatim (`broker_positions_adapter.py:24-33`) — MM7H had to **remove** the literal `instrument_key` from even its *docstring* to pass this guard (MM7H §1, "GREEN").

**Therefore R1's placement is load-bearing:**
- ❌ Putting the remap inside `core/execution/broker_positions_adapter.py` or `reconciliation.py` → references `instrument_key` and imports `core.brokers.mapping` → **fails both guards**. Forbidden.
- ✅ Putting the translation primitive in `core/brokers/mapping/upstox.py` (already references `instrument_key` legitimately, `:57,60,75`) and the binding in `scripts/fno_runner.py` (composition root, outside `core/`) → **crosses no guard**. The canonical→broker-key seam already lives in `core/brokers/mapping/` by design (`base.py:1-8`, "the seam that keeps broker identity out of the canonical model").

**Verdict I1: R1 does not violate G1 when the remap lives in `core/brokers/mapping/` + the composition root. It would violate G1 only if implemented inside `core/execution/` — which the route explicitly does not do.**

---

## 4. Recommendation

### 4.1 Decision — R1, placed correctly

Take **R1**. It satisfies the four properties the decision turns on:
- **Unblocked** — the mapping it consumes is landed and tested (4C.4; `UpstoxMapping`, `tests/brokers/test_upstox_mapping.py`). No paused phase to resume.
- **Boundary-clean** — §3: mapping layer + composition root, never `core/execution/`.
- **Revertible** — §5.
- **Non-obstructive to 4C.8** — I4 / §5.

### 4.2 Smallest production location (I2) — recommend: **mapping** (primitive) + **runtime/composition-root** (binding)

Of the four candidates (`adapter`, `runtime`, `mapping`, `broker`):

| Candidate | Verdict |
|---|---|
| **adapter** (`core/execution/broker_positions_adapter.py`) | ❌ G1: cannot reference `instrument_key` (`test_g1_closure_guard.py:336-340`). The shape function stays shape-only. |
| **broker** (`core/brokers/upstox_adapter.py`) | ❌ G1: forbidden to import `CanonicalInstrument` (`test_g1_closure_guard.py:312-330`); also discards `instrument_token` today (`:131-134`). Wrong home for a mapping-projection lookup. |
| **mapping** (`core/brokers/mapping/upstox.py`) | ✅ **The translation primitive belongs here** — `_ikey_by_tradingsymbol` already lives here (`:60`); add one public `trading_symbol → instrument_key` accessor. `instrument_key` is legal in this layer. |
| **runtime / composition root** (`scripts/fno_runner.py`) | ✅ **The binding belongs here** — `broker_positions` is already injected at `:51,137`; the re-key closure wraps `broker.get_positions()` on the LIVE rung only, outside `core/`. |

**Recommend one:** the **mapping layer** is the smallest single *production home for the new logic* (one accessor); the composition root contributes only a wiring lambda (no domain logic). This split keeps the fallible `instrument_key` lookup out of both `core/execution/` (G1) and the shape adapter (single responsibility, MM7F F3 / MM7H §2).

### 4.3 Unmapped-symbol policy (must be decided with the route)

`from_broker_position` returns `None` for an unmapped `trading_symbol` (`upstox.py:79-80`). R1 must define behavior. **Recommended: fail-loud — an unmapped broker position keeps its `trading_symbol` key and therefore surfaces as `ORPHANED_BROKER_POSITION`** (it cannot be matched to any internal `instrument_key`). Rationale: a live broker position the platform cannot identify is a genuine reconciliation divergence and *should* refuse startup (`driver.py:483-493`) — silently dropping it would re-introduce the exact silent-orphan hazard #6b exists to close. This policy is itself gated by the master-readiness the driver already enforces before reconcile (`driver.py` startup-gate ordering, `test_g1_closure_guard.py:377-389`).

### 4.4 Pre-checks (gate R1 before #6b.2 codes)

1. **Master coverage** — confirm every live-tradable F&O `trading_symbol` resolves in `_ikey_by_tradingsymbol` (or via `instrument_token`). A coverage hole turns R1 into a false-orphan generator (§7.1).
2. **`instrument_token` preservation** — `UpstoxAdapter.get_positions()` currently discards the raw payload's `instrument_token` (`:131-134`, reads only `trading_symbol`/`quantity`/`average_price`). #6b.2 should preserve it so `from_broker_position` uses the **preferred** stable `instrument_token` key rather than the `trading_symbol` string fallback (`upstox.py:75-78`). This is a `core/brokers/` change (legal) and is shared work R1 and R2 both need.

---

## 5. Migration path (I3) — R1 is fully revertible if 4C.8 lands

R1 introduces exactly three reversible artifacts and **zero** persisted state (reconcile runs only at the startup gate, in memory — `driver.py:462-494`):

| R1 artifact | On 4C.8 landing |
|---|---|
| Public `trading_symbol → instrument_key` accessor on `UpstoxMapping` | Keep or delete — 4C.8 uses `from_broker_position → canonical_id` instead; the accessor becomes dead and is removed in one edit. |
| Composition-root re-key closure (`fno_runner` LIVE rung) | Replaced by the 4C.8 binding (no re-key; reconcile projects both sides to `canonical_id`). One-line swap. |
| `to_reconcile_positions` shape adapter | **Retained** — 4C.8 still needs the `Dict[str,Position] → List[Dict]` shape transform; route-independent (MM7H §2.2). |
| `instrument_token` preservation in `upstox_adapter` | **Retained** — 4C.8 needs it too (the preferred `from_broker_position` ikey path). R1 doing it first is a head start. |

**Migration steps R1 → R2:** (1) resume + land 4C.6/4C.7; (2) rewrite `reconcile()` to compare `canonical_id` via `from_broker_position`; (3) re-key (or compute-at-compare) the restored ledger to `canonical_id` (the H3 ledger change R2 owns intrinsically); (4) delete the R1 root re-key closure + accessor; (5) flip the namespace tests' bridge from instrument_key to canonical_id. No data migration, no schema change, no backfill. **Clean and bounded.**

### I4 — Would R1 make 4C.8 harder? **No — strictly easier or neutral.**

- R1 leaves `reconciliation.py` **pristine** (the remap lives at the root, not in the engine) — 4C.8's rewrite starts from the same untouched file.
- R1 adds **no new namespace** — it reuses the same `UpstoxMapping` (4C.4) that 4C.8 consumes.
- R1 delivers the **shared prerequisites** early: shape adapter (retained) and `instrument_token` preservation (retained) — both reduce 4C.8's remaining surface.
- The only R1-specific code (accessor + root closure) is deleted in two edits.

The one honest non-reduction: 4C.8 must re-key the restored ledger to `canonical_id` (H3). R1 neither adds nor removes that — it is intrinsic to R2 regardless of route. **Proof R1 doesn't make it harder: R1 writes nothing into `reconciliation.py`, the ledger keying, or any persisted store — the three surfaces 4C.8 must change. It only adds removable code in the mapping + root layers 4C.8 leaves behind.**

---

## 6. Acceptance criteria (I5) — what characterization flips

**Headline flip:** `tests/runtime/test_reconcile_symbol_namespace.py::test_mismatched_namespace_same_position_double_false_divergence` — currently asserts **2 alerts** (`QUANTITY_MISMATCH` + `ORPHANED_BROKER_POSITION`, lines 138-160) → must assert **0 alerts** (identical position under two namespaces reconciles clean).

**Tests that must change (all in `tests/runtime/test_reconcile_symbol_namespace.py` unless noted):**

| Test | Change | Post-R1 verdict |
|---|---|---|
| shared `_bridge` helper (`:57-62`) | route the broker book through the R1 remap + inject a `UpstoxMapping` double providing `trading_symbol → instrument_key` (`NIFTY26JAN2623500CE → NSE_FO|53001`, `RELIANCE → NSE_EQ|INE…`) | n/a (structural) |
| `test_mismatched_namespace_same_position_double_false_divergence` (`:138-160`) | **assertion flip 2 → 0** | `[]` |
| `test_aligned_namespace_consistent_position_no_alert` (`:70-82`) | re-express: internal ledger keyed on the **instrument_key** the broker `trading_symbol` maps to (today's "RELIANCE"=="RELIANCE" alignment breaks once the broker side is remapped to instrument_key) | `[]` |
| `test_aligned_namespace_quantity_mismatch_single_alert` (`:90-106`) | same re-express; genuine qty divergence still detected | exactly **1** `QUANTITY_MISMATCH` |
| `test_orphaned_broker_position_when_internal_empty` (`:114-126`) | define against the §4.3 unmapped/empty-internal policy | exactly **1** `ORPHANED_BROKER_POSITION` |

**New tests required:**
- `tests/brokers/test_upstox_mapping.py` — a case for the new public `trading_symbol → instrument_key` accessor (hit + miss).
- An **unmapped-symbol** case pinning the §4.3 fail-loud policy (`from_broker_position → None` → position retains `trading_symbol` key → `ORPHANED_BROKER_POSITION`, not silently dropped).

**Tests that must stay GREEN unchanged (prove R1 stayed in its lane):**
- `tests/execution/test_to_reconcile_positions.py` (shape adapter — R1 does not touch `to_reconcile_positions`).
- `tests/execution/test_broker_positions_adapter.py`, `tests/execution/test_reconciliation_broker.py` (use `"RELIANCE"` both sides through the shape adapter with **no** remap — they exercise shape, not the wired root remap; they stay green **only if** the remap lives at the composition root, not in the shape function — a second reason for the §4.2 placement).
- `tests/g1/test_g1_closure_guard.py::test_instrument_key_absent_from_execution` and `::test_order_path_does_not_import_broker_mapping` — **must stay green**; their continued passing is the proof R1 did not breach the boundary (§3).

---

## 7. Challenge — what could make R1 a mistake

R1 is **not unconditionally safe.** It rests on assumptions that, if false, make R2 the correct call:

1. **`_ikey_by_tradingsymbol` coverage is complete and current.** R1 maps the broker side by `trading_symbol` lookup (`upstox.py:78`). If the master projection is stale or incomplete, live positions resolve to `None` → under the §4.3 fail-loud policy they become `ORPHANED_BROKER_POSITION` → the driver refuses to start on **every** run with an unmapped contract (`driver.py:483-493`) — the *same* refuse-to-start failure R1 was built to remove, now triggered by coverage instead of namespace. **This is the single biggest risk.**
2. **Upstox `trading_symbol` is byte-stable against the master's `tradingsymbol`.** If Upstox's display-symbol formatting drifts from the master (`upstox.py:59-60`), the fallback key silently fails. Mitigated only by preferring `instrument_token` (§4.4) — which the adapter currently discards (`upstox_adapter.py:131-134`). Until that follow-up lands, R1 rests on a fragile string equality.
3. **The internal ledger key stays `instrument_key`/display symbol.** Verified true today — `canonicalize_restored_positions` swaps `.instrument` but preserves the `_positions` key (`handler.py:284-287`; `replace_instrument`). If a future change re-keys `_positions` to `canonical_id`, R1's "both sides → instrument_key" target collapses and R2 becomes mandatory.
4. **The new accessor resolves unambiguously.** If `trading_symbol → instrument_key` is not 1:1 in the master (collisions across expiries/segments), a direct accessor can mis-resolve; R1 would then need the fuller `from_broker_position → canonical` disambiguation, enlarging the slice toward R2.

### What evidence would change the recommendation (→ R2)

- **Measured master coverage < 100%** of live-tradable F&O `trading_symbol`s, or demonstrated `trading_symbol` format drift → R1's fail-loud policy becomes a startup-blocker; prefer R2 (canonical matching is robust to display-symbol formatting).
- **A committed plan to re-key `PositionTracker._positions` to `canonical_id`** → R1's instrument_key target is invalidated; go R2.
- **A scheduled near-term resume of Phase-4C (4C.6→4C.8) before #6b is needed live** → building-then-reverting R1 is wasted motion; finish 4C.8 directly.
- **Evidence the `trading_symbol → instrument_key` map is not 1:1** → the cheap accessor is unsafe; R1's cost converges on R2's.

Absent that evidence, and with the §4.4 pre-checks passing, **R1 is the correct route.**

---

## 8. Deliverable checklist

1. **R1 analysis** — §1.
2. **R2 analysis** — §2.
3. **Boundary review (I1)** — §3.
4. **Recommendation (I2 location, I3 revert, I4 4C.8 impact)** — §4, §5.
5. **Migration path** — §5.
6. **Acceptance criteria (I5)** — §6.
7. **Challenge (assumptions + flip evidence)** — §7.

---

## 9. Stop condition / return summary

**Decision made. Report written. No code, no test, no adapter/reconciliation/broker edit, no 4C.8/F3/F4. 516 passing · 0 failing (unchanged).**

- **Route FROZEN = R1** (adapter-local `trading_symbol → instrument_key` remap, reusing the built `UpstoxMapping`).
- **Placement (I2):** translation primitive in `core/brokers/mapping/upstox.py`; binding closure at the `scripts/fno_runner.py` composition root, LIVE rung only. **Never `core/execution/`** (G1).
- **I1:** R1 crosses no G1 guard when placed per §3; it would only breach if put in `core/execution/`.
- **I3 / I4:** fully revertible (zero persisted state); makes 4C.8 strictly easier or neutral — `reconciliation.py`, ledger keying, and persistence left untouched.
- **I5 acceptance:** flip `test_mismatched_namespace_same_position_double_false_divergence` 2 → 0; re-express the aligned/orphan cases for the new instrument_key broker namespace; add accessor + unmapped-policy tests; keep the G1 guards and shape-adapter nets green.
- **Conditions:** R1 holds only if master coverage is complete, `instrument_token` is preserved (§4.4), and the unmapped policy is fail-loud (§4.3). Coverage gaps, a ledger re-key to `canonical_id`, a near-term 4C resume, or a non-1:1 symbol map flip the call to R2 (§7).
- **4C.8 / R2** remains the architected end-state; resume it on the Phase-4C track, **not** as a #6b gate.

*Filed under the G1 / MM7A–H review-first, characterize-before-change, decide-before-implement discipline. Companion to `MM7G_NAMESPACE_CHARACTERIZATION.md` (R1/R2 framing) and `MM7H_SHAPE_ADAPTER_REPORT.md` (#6b.1 shape adapter). Next slice: #6b.2 implementation of R1.*
