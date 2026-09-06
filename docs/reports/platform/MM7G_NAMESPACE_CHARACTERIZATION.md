# MM7G — Broker-Position Namespace Characterization

**Type:** Characterization — map the broker-position vs execution-ledger symbol namespaces, pin current `reconcile()` behavior across matched/mismatched namespaces, and settle the 4C.8 dependency with first-hand code evidence. **No adapter. No reconciliation change. No broker change. No 4C.8 work.**
**Date:** 2026-06-12
**Basis:** `MM7F_BROKER_POSITIONS_ADAPTER_REVIEW.md` (F1-note / risk 1 — the namespace mismatch) · `MM7F_6A_W3_GATE_HARDENING_REPORT.md` (#6a DONE) · `MM7E_IMPLEMENTATION_REPORT.md` (the composition root) · `PHASE_4C_IMPLEMENTATION_PLAN.md` §4C.8 · `CANONICAL_INSTRUMENT_ARCHITECTURE.md` §D6.
**Starting state:** G1 CLOSED · 505 passing · 0 failing · MM7E COMPLETE · #6a COMPLETE · #6b NOT STARTED.
**Ending state:** G1 CLOSED · **509 passing · 0 failing** (+4 namespace characterization tests) · #6b still NOT STARTED.

> **Scope guard.** Characterization only. This slice writes one test file and this report. It touches no production code: `core/execution/reconciliation.py`, both brokers, the driver, and `core/brokers/mapping/*` are untouched. It does **not** start #6b, 4C.8, F3, or F4.

---

## 0. Headline

The shape mismatch (`Dict[str, Position]`→`List[Dict]`, enum→string) is cosmetic and already netted (MM7F). **The substantive problem is that three different symbol namespaces are in play and `reconcile()` matches them by raw string** (`reconciliation.py:54,57,77`):

1. **Internal ledger key** = `instrument_key` / order `instrument_token` (e.g. `NSE_FO|53001`).
2. **Upstox position symbol** = broker `trading_symbol` (e.g. `NIFTY26JAN2623500CE`).
3. **Canonical id** = `canonical_id` (the 4C platform identity).

A shape-only adapter wired to a live reconcile would orphan **every** position. **New evidence this slice (not in MM7F):** the key-mapping mechanism — `UpstoxMapping.from_broker_position` — **already exists and is tested** (`core/brokers/mapping/upstox.py:74-81`; `tests/brokers/test_upstox_mapping.py`). MM7F's load-bearing assumption C5 ("4C.8 … assumed available or buildable … not verified this slice") is now **verified**: the *mapping* is built (4C.4); only the *reconcile-wiring* (4C.8) is paused.

---

## 1. Namespace mappings

### 1.1 The three namespaces (file:line)

| Namespace | Carrier | Example | Where set |
|---|---|---|---|
| **Internal ledger key** | `PositionTracker._positions` dict key = `fill.symbol` | `NSE_FO|53001` | `handler.py:326` `update_from_fill(fill)`; the order's `instrument_token` (`upstox_adapter.py:86` `"instrument_token": order.symbol`). `reconcile()` iterates these raw keys (`reconciliation.py:57`). |
| **Upstox position symbol** | `Position` dict key in `UpstoxAdapter.get_positions()` = `pos_data['trading_symbol']` | `NIFTY26JAN2623500CE` | `upstox_adapter.py:131-132` (`symbol = pos_data['trading_symbol']`; `positions[symbol] = Position(...)`). The raw payload's `instrument_token` is **discarded** — only `trading_symbol`, `quantity`, `average_price` are read (`upstox_adapter.py:131-134`). |
| **Canonical id** | `CanonicalInstrument.canonical_id` | `<deterministic structured key>` | `UpstoxMapping.from_broker_position(raw)` → `resolver.resolve_by_instrument_key(ikey)` (`mapping/upstox.py:74-81`). |

### 1.2 How `reconcile()` matches — raw string, no translation

`reconcile(broker_positions: List[Dict])` (`reconciliation.py:24`):
- builds `broker_map[symbol] = qty` keyed on the dict's `symbol` (`:43,53-54`),
- iterates `self.position_tracker._positions` keys (`:57`) and looks them up in `broker_map` (`:64`) → `QUANTITY_MISMATCH` if `abs(internal_net - broker_qty) > 1e-6` (`:67-74`),
- iterates `broker_map` keys and checks `has_open_position(symbol)` (`:77-78`) → `ORPHANED_BROKER_POSITION` if absent (`:79-85`).

Both checks are exact-string keyed. **No namespace translation exists anywhere in `reconcile()`.**

### 1.3 The mapping that already exists (4C.4, built — NOT 4C.8)

`UpstoxMapping` (`core/brokers/mapping/upstox.py`) is a projection of the instrument master holding both directions:
- `_ref_by_canonical: canonical_id → BrokerRef(instrument_key, tradingsymbol)` (`:57-58`),
- `_ikey_by_tradingsymbol: tradingsymbol → instrument_key` (`:59-60`).

`from_broker_position(raw)` (`:74-81`) prefers `raw['instrument_token']`/`['instrument_key']`, else falls back to `_ikey_by_tradingsymbol[raw['trading_symbol']]`, then resolves to a `CanonicalInstrument`. This is exactly the bridge from namespace #2 → #1/#3. It is **landed and tested** (`tests/brokers/test_upstox_mapping.py`, plan row "Broker mapping").

---

## 2. Examples

### 2.1 Mismatch (the hazard) — identical economic position, double false divergence

```
Internal ledger:  { "NSE_FO|53001": LONG 50 }          # keyed on instrument_key
Broker (Upstox):  { "NIFTY26JAN2623500CE": LONG 50 }   # keyed on trading_symbol
                  (same contract, same quantity)
reconcile() →  QUANTITY_MISMATCH   (NSE_FO|53001: internal 50 vs broker 0)
            +  ORPHANED_BROKER_POSITION (NIFTY26JAN2623500CE: broker 50 vs internal 0)
```

A perfectly-reconciled book is reported as **two** divergences. Scaled to N live positions: **2N false alerts**, and the startup gate refuses to start every run (`driver.py:483-490` → `abort_startup` → `STOPPED`). Pinned: `test_mismatched_namespace_same_position_double_false_divergence`.

### 2.2 Match (aligned) — clean

```
Internal ledger:  { "RELIANCE": LONG 10 }
Broker (Upstox):  { "RELIANCE": LONG 10 }   # trading_symbol == ledger key (accidental alignment)
reconcile() → []   # no alerts
```

This is the alignment the existing net (`test_reconciliation_broker.py`, `test_broker_positions_adapter.py`) relies on by using `"RELIANCE"` on both sides — it **masks** §2.1. Pinned: `test_aligned_namespace_consistent_position_no_alert`.

### 2.3 The fix the built mapping enables (illustrative — NOT implemented here)

```
from_broker_position({"trading_symbol": "NIFTY26JAN2623500CE", ...})
  → _ikey_by_tradingsymbol["NIFTY26JAN2623500CE"] = "NSE_FO|53001"   # namespace #2 → #1
  → reconcile keys now agree → []   (correct)
```

---

## 3. Characterization results (G5 — `tests/runtime/test_reconcile_symbol_namespace.py`)

Four tests, all run through the **real** `UpstoxAdapter.get_positions()` shape + the MM7F-documented shape bridge, isolating the namespace variable. **They pin current behavior; they fix nothing.**

| # | Test | Pins (current behavior) |
|---|---|---|
| namespace match | `test_aligned_namespace_consistent_position_no_alert` | keys agree, position identical → `reconcile() == []` |
| qty mismatch, matching ns | `test_aligned_namespace_quantity_mismatch_single_alert` | keys agree, qty differs → exactly **one** `QUANTITY_MISMATCH`, no spurious orphan |
| orphaned broker position | `test_orphaned_broker_position_when_internal_empty` | empty internal, broker holds `trading_symbol` position → one `ORPHANED_BROKER_POSITION` |
| namespace mismatch | `test_mismatched_namespace_same_position_double_false_divergence` | identical position under two namespaces → **two** alerts (`QUANTITY_MISMATCH` + `ORPHANED_BROKER_POSITION`) |

**Validation:** `pytest tests/runtime/test_reconcile_symbol_namespace.py -q` → **4 passed**. `pytest tests/runtime -q` → **291 passed**. `pytest -q` → **509 passed, 0 failing** (505 baseline + 4).

### G1 — PaperBroker position key vs execution ledger key

**Identical namespace by construction, but never exercised divergently — the PaperBroker book is permanently empty.** `PaperBroker.get_positions()` returns `self.tracker.get_all_positions()` (`paper_broker.py:48-49`), a `PositionTracker` keyed on `fill.symbol` — the *same* keying as the execution ledger's `PositionTracker` (`position_tracker.py:24,159`). So the two namespaces are structurally identical. **But** `PaperBroker.place_order` never updates `self.tracker` (`paper_broker.py:26-43`; `tracker` appears only at `:22,49`), so `get_positions()` always returns `{}`. **Verdict: namespaces identical, no transformation needed — and no live divergence possible, because PaperBroker contributes zero keys.** (This is *why* MM7E correctly wires `broker_positions=None` at PAPER, MM7F F2.)

### G2 — Upstox position symbol vs execution ledger symbol

- **Upstox:** `trading_symbol`, e.g. `NIFTY26JAN2623500CE` (`upstox_adapter.py:132`).
- **Ledger:** `instrument_key`, e.g. `NSE_FO|53001` (`handler.py:326` + `upstox_adapter.py:86`).

> **Can a live broker position be reconciled today without transformation?**
> **No — twice over.** (1) Shape/type: `Dict[str, Position]` with an enum `side` vs `List[Dict]` with a string `side` — naive pass-through raises `AttributeError` (`test_broker_positions_adapter.py:84-89`). (2) Namespace: `trading_symbol` ≠ `instrument_key`, and `reconcile()` is raw-string keyed (`reconciliation.py:54,57,77`) — every position orphans (§2.1, pinned). Both transformations are mandatory before any real broker book reaches `reconcile()`.

### G3 — First point ORPHANED_BROKER_POSITION can occur

**Code site:** `reconciliation.py:77-85` (the second loop) — the first time a `broker_map` key is absent from the internal tracker.
**Production path:** `LoopDriver._reconcile_ledger` → `reconcile(broker_book)` (`driver.py:482`), on the **first startup gate of a live run with a real `broker_positions` source wired**. **It cannot occur in production today:** at `ExecutionMode.PAPER` `broker_positions=None` (vacuous, `driver.py:462-463`), and #6b — the only thing that wires a live source — is not started. **So the first point it can occur is the moment #6b wires a shape-only (non-key-mapping) adapter to the live reconcile gate.** Concrete example: §2.1 / `test_mismatched_namespace_same_position_double_false_divergence`.

### G4 — Is 4C.8 required for namespace parity?

**C — Required before #6b — with one decisive refinement: the *mapping mechanism* is already built; only the *reconcile-wiring* (4C.8 proper) is paused, and #6b does not need the full wiring to achieve parity.**

Evidence:
- **Parity is required before #6b.** A shape-only adapter without key-mapping orphans every live position (§2.1, pinned). #6b cannot wire a meaningful live reconcile without it.
- **The mapping is built (4C.4, not 4C.8).** `UpstoxMapping.from_broker_position` + `_ikey_by_tradingsymbol` already translate `trading_symbol → instrument_key → canonical_id` (`mapping/upstox.py:60,74-81`), tested (`tests/brokers/test_upstox_mapping.py`). This is the §D6 reconciliation mapping seam.
- **4C.8-the-slice is one of two ways to consume it.** Per `PHASE_4C_IMPLEMENTATION_PLAN.md:89-92`, 4C.8 rewrites `reconciliation.py` to match on `canonical_id` via `from_broker_position` (both sides → namespace #3). That is the architected path but is **paused** (PROJECT_STATE: "4C.1–4C.5 IN PROGRESS, paused before 4C.6"; 4C.6/4C.7/4C.8 not done). **Alternatively**, #6b's adapter can call the already-built `UpstoxMapping` to re-key the broker book from `trading_symbol → instrument_key` (namespace #2 → #1) so it matches the internal ledger as-is — no `reconcile()` rewrite, unblocked today.

So: **namespace parity is a hard prerequisite for #6b (answer C); the full 4C.8 reconcile-rewrite is NOT a hard prerequisite — the mapping it would consume already exists and #6b can consume it directly.** This corrects MM7F's open question D1/assumption C5.

> ⚠ **One caveat on the canonical_id path.** The restored internal ledger keeps its key as the **instrument_key/display symbol** byte-for-byte (G1 Wave 3/4B: `canonicalize_restored_positions` swaps `.instrument` but preserves `.symbol` — "so reconciliation, run next, still matches — H3"). It does **not** re-key `_positions` to `canonical_id`. So a parity solution that maps only the *broker* side to `canonical_id` introduces a **third** mismatch (ledger=instrument_key vs broker=canonical_id). Parity requires **both sides in the same namespace** — either both → `instrument_key` (adapter-local remap, smaller) or both → `canonical_id` (full 4C.8, also re-keys the restored ledger). #6b must pick one explicitly.

---

## 4. 4C.8 dependency verdict

**Namespace parity is REQUIRED before #6b (G4 = C). The 4C.8 *slice* is NOT a hard blocker — its mapping dependency (4C.4 `UpstoxMapping`) is already landed and tested.** #6b therefore has two routes to parity:

| Route | Scope | Re-keys | Blocked? |
|---|---|---|---|
| **R1 — adapter-local instrument_key remap** | #6b adapter calls `UpstoxMapping` to map broker `trading_symbol → instrument_key`; `reconcile()` untouched | broker side only → namespace #1 | **Unblocked** (mapping built) |
| **R2 — full 4C.8 (canonical↔canonical)** | rewrite `reconciliation.py` to match on `canonical_id` via `from_broker_position`; re-key both restored ledger + broker book | both sides → namespace #3 | Blocked on resuming 4C.6→4C.8 |

Both deliver parity. **R1 is smaller and unblocked; R2 is the architected end-state.** The single decision that sizes #6b is which route — and #6b must own that decision explicitly, because shipping a shape-only adapter (neither route) silently orphans every live position.

---

## 5. Recommended implementation sequence

1. **#6b-0 (decision, do first):** choose **R1 (instrument_key remap, recommended)** vs **R2 (full 4C.8)**. R1 unblocks live reconcile now using the built mapping; R2 waits on resuming the paused 4C.6→4C.8 chain. The namespace test (§3) is the acceptance the chosen route must satisfy (mismatched case must go from 2 alerts → 0).
2. **#6b-1 (adapter shape):** promote the duplicated `_bridge`/`_broker_positions_as_dicts` glue into one `to_reconcile_positions(Dict[str, Position]) -> List[Dict]` (MM7F F3). Repoint `test_broker_positions_adapter.py` + `test_reconciliation_broker.py` at it.
3. **#6b-2 (key mapping):** wire the chosen route. For R1: the adapter (or its composition-root closure) maps each broker position's `trading_symbol → instrument_key` via `UpstoxMapping` before reconcile. Flip the mismatched-namespace test from "2 alerts" to "0 alerts" as the acceptance flip.
4. **#6b-3 (wire live):** bind `broker_positions=lambda: to_reconcile_positions(broker.get_positions())` in `fno_runner` **only** on the `ExecutionMode.LIVE` rung, behind F4. The #6a W3 guard (`driver.py:469-481`) already protects the raise path.
5. **Adapter side preservation:** add `instrument_token` to `UpstoxAdapter.get_positions()`'s read (it currently discards it, `:131-134`) so R1/R2 can use the preferred `from_broker_position` ikey path instead of relying solely on the `trading_symbol` fallback.

---

## 6. Additional review requirements

### 6.1 Is the adapter still necessary?

**Yes — the shape transform is mandatory (unchanged from MM7F), AND a key-mapping step is now confirmed mandatory.** The naive enum pass-through raises (`test_broker_positions_adapter.py:84-89`); the namespace mismatch orphans every position (§2.1, pinned this slice). The adapter is a small pure function (shape) **plus** a key-remap call into the already-built `UpstoxMapping`. It remains off the MM7E/PAPER critical path (G1: PaperBroker book empty) and critical only at the `ExecutionMode.LIVE` rung.

### 6.2 Should #6b be split?

**Yes — into the four sub-steps in §5 (#6b-0…#6b-3), with #6b-0 (the R1-vs-R2 route decision) pulled to the front.** The decision sizes the slice; the shape work (#6b-1) is an afternoon and independent of the route; the key-mapping (#6b-2) is the substantive risk; the live wiring (#6b-3) is gated behind F4 regardless. Splitting lets the shape consolidation land independently of the route decision.

### 6.3 Should 4C.8 move forward?

**Not as a prerequisite for #6b.** If #6b takes **R1**, 4C.8 is not on its path — the built `UpstoxMapping` suffices. 4C.8 (canonical↔canonical reconcile) remains the desirable architected end-state and should resume on the Phase-4C track (after 4C.6/4C.7), but it should **not** gate #6b. Forcing 4C.8 first would couple a live-safety reconcile fix to resuming a paused multi-slice phase for no technical reason — the same anti-pattern #6a avoided by decoupling from #6b.

### 6.4 What could invalidate this recommendation?

1. **`_ikey_by_tradingsymbol` coverage gaps.** R1 relies on every live `trading_symbol` being present in the master projection (`mapping/upstox.py:46-60`). If the master is stale/incomplete, `from_broker_position` returns `None` → an unmapped broker position. The #6b adapter must define behavior for `None` (treat as orphan? refuse? — a real decision), and this is gated by the same master-readiness the driver already enforces (`driver.py:372-417`). **A coverage hole would push toward R2 or a stricter readiness gate.**
2. **Upstox `trading_symbol` instability.** If Upstox's `trading_symbol` formatting drifts from the master's `tradingsymbol`, the fallback key fails. Preferring `instrument_token` (§5 step 5) mitigates this — but the adapter currently discards it.
3. **A second live broker.** Confirmed `BrokerMapping` is already a per-broker ABC (`mapping/base.py:25-36`) with `UpstoxMapping` one impl — so a second broker reinforces R1's standalone-mapping design and does not invalidate it.
4. **The restored-ledger key assumption.** If a future change re-keys `PositionTracker._positions` to `canonical_id` (not just swapping `.instrument`), R1's "both sides → instrument_key" target breaks and R2 becomes mandatory. Verified today the key is preserved (G1 Wave 4B H3); a change there would flip the verdict.

---

## 7. Stop condition / return summary

Characterization complete. Report written. One test file added (`tests/runtime/test_reconcile_symbol_namespace.py`, 4 tests). **No adapter, no reconciliation change, no broker change, no 4C.8 work, no F3, no F4.** Commit follows.

1. **Namespaces:** three — internal ledger `instrument_key` (`NSE_FO|53001`), Upstox `trading_symbol` (`NIFTY26JAN2623500CE`), canonical `canonical_id`. `reconcile()` matches raw strings (`reconciliation.py:54,57,77`); no translation.
2. **G1:** PaperBroker key ≡ ledger key (both `PositionTracker`/`fill.symbol`), but the PaperBroker book is permanently empty — no transformation, no divergence.
3. **G2:** live reconcile today is impossible without transformation — shape **and** namespace.
4. **G3:** `ORPHANED_BROKER_POSITION` first occurs at `reconciliation.py:77-85`, reachable in production only when #6b wires a shape-only live source.
5. **G4 / 4C.8 verdict:** **C — required before #6b** — but the *mapping mechanism* (`UpstoxMapping.from_broker_position`, 4C.4) is **already built and tested**; only the *reconcile-wiring* (4C.8) is paused, and #6b can achieve parity via R1 (adapter-local instrument_key remap) without it. MM7F's unverified assumption C5 is now verified.
6. **Sequence:** split #6b into route-decision → shape → key-map → live-wire; recommend **R1** (unblocked); resume 4C.8 on the 4C track but **not** as a #6b gate.

*Filed under the G1 / MM7A–F review-first, characterize-before-change discipline. Companion to `MM7F_BROKER_POSITIONS_ADAPTER_REVIEW.md` (F1-note / risk 1), `PHASE_4C_IMPLEMENTATION_PLAN.md` (§4C.8), and `CANONICAL_INSTRUMENT_ARCHITECTURE.md` (§D6).*
