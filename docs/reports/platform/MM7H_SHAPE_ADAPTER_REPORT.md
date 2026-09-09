# MM7H — Broker-Position Shape Adapter (#6b.1)

**Type:** Implementation — the broker-position **shape** adapter: `Dict[str, Position]` → `List[Dict]`, enum `side` → string `side`. **No namespace mapping. No instrument_key work. No reconciliation change. No live wiring. No 4C.8. No F3/F4.**
**Date:** 2026-06-12
**Basis:** `MM7G_NAMESPACE_CHARACTERIZATION.md` (the #6b split: 6b.1 shape / 6b.2 namespace / 6b.3 live) · `MM7F_BROKER_POSITIONS_ADAPTER_REVIEW.md` (F1 contract map, F3 ownership = standalone fn, §5 `test_to_reconcile_positions.py`).
**Starting state:** 509 passing · 0 failing · #6a COMPLETE · #6b split (6b.1/6b.2/6b.3).
**Ending state:** **516 passing · 0 failing** (+7 adapter unit tests) · **#6b.1 COMPLETE** · 6b.2 / 6b.3 NOT STARTED.

> **Scope guard.** Shape only. The symbol KEY is carried through verbatim — this slice does **no** namespace translation (6b.2), no live wiring (6b.3), no reconciliation/broker edit, no 4C.8.

---

## 1. Implementation

**New `core/execution/broker_positions_adapter.py` — one pure function:**

```python
def to_reconcile_positions(positions: Dict[str, Position]) -> List[Dict[str, Any]]:
    return [
        {"symbol": symbol, "quantity": pos.quantity, "side": pos.side.value}
        for symbol, pos in positions.items()
    ]
```

This resolves the two-ended contract mismatch (MM7F F1):

| Aspect | broker `get_positions()` | reconcile() needs | Adapter action |
|---|---|---|---|
| container | `Dict[str, Position]` (`base.py:27`) | `List[Dict]` (`reconciliation.py:24`) | `.items()` → list |
| `side` | `PositionSide` **enum** (`position_models.py:15-18`) | **string** `.upper()`-ed (`reconciliation.py:47`) | `pos.side.value` |
| `quantity` | **absolute** (`position_models.py:26`; `upstox_adapter.py:147`) | unsigned, re-signed from `side` (`reconciliation.py:48-51`) | passed through unchanged |
| `symbol` | dict key | dict `symbol` (`reconciliation.py:43`) | **dict key, verbatim** (no namespace map) |

It is the single production home for the transform that previously existed only as duplicated test glue (`_bridge`, `_broker_positions_as_dicts`) — MM7F F3. **LONG / SHORT / FLAT semantics are preserved exactly:** `side.value` yields `"LONG"`/`"SHORT"`/`"FLAT"`, which `reconcile()` re-signs (`LONG`→`+abs`, `SHORT`→`-abs`) and treats FLAT/zero as non-orphan — so no semantic is added or lost; the adapter only changes representation.

**TDD trail.** RED: new `tests/execution/test_to_reconcile_positions.py` (7 tests) failed with `ModuleNotFoundError: core.execution.broker_positions_adapter` (feature missing). GREEN: added the function → 7 passed. One real regression surfaced and was fixed: the G1 closure guard (`test_instrument_key_absent_from_execution`) failed because the module **docstring** contained the literal `instrument_key`; removed the token (the adapter does no key work, so the guard is correctly enforcing the 4C.7 boundary) → green.

**Glue repointed (the MM7F F3 consolidation).** The three existing nets' local bridges now delegate to the production function, so they exercise the real code end-to-end through the `UpstoxAdapter` shape — no assertion changed:
- `tests/execution/test_broker_positions_adapter.py` `_bridge` → `to_reconcile_positions(adapter.get_positions())`
- `tests/execution/test_reconciliation_broker.py` `_broker_positions_as_dicts` → same
- `tests/runtime/test_reconcile_symbol_namespace.py` `_bridge` → same

---

## 2. Why namespace mapping was excluded

**6b.1 is deliberately shape-only; the symbol KEY passes through verbatim.** MM7G established that the broker keys positions on `trading_symbol` (e.g. `NIFTY26JAN2623500CE`, `upstox_adapter.py:131-132`) while the internal ledger keys on the driver instrument key (e.g. `NSE_FO|53001`, `handler.py:326`), and `reconcile()` matches them by raw string (`reconciliation.py:54,57,77`). Mapping between those namespaces is a **separate concern** from shape, for three reasons:

1. **Separation of concerns / single responsibility (MM7F F3).** Shape is a pure, broker-agnostic, total function (every `Position` maps). Namespace mapping is partial (depends on the instrument-master projection, can return `None` for an unmapped symbol) and broker-specific. Fusing them would make the shape adapter depend on `UpstoxMapping` + master readiness — coupling a trivial total transform to a fallible lookup.
2. **It needs a real decision MM7G flagged but did not make (route R1 vs R2).** Parity requires *both* sides in one namespace — either both → `instrument_key` (adapter-local remap, R1) or both → `canonical_id` (full 4C.8, R2). That choice is 6b.2's scope; landing it inside 6b.1 would pre-commit it. Keeping 6b.1 shape-only leaves the seam clean for whichever route 6b.2 picks (the mapping is applied to the *input dict's keys* before this function, or to its output — either way this function is unchanged).
3. **The 4C.7 / G1 boundary forbids it here.** `core/execution/` must not reference `instrument_key` (G1 closure guard `test_instrument_key_absent_from_execution`); the canonical→broker-key seam lives in `core/brokers/mapping/` and is not wired into the execution/order path (that wiring is 4C.7, still blocked). A namespace-mapping adapter in `core/execution/` would cross that line. Shape-only keeps 6b.1 inside the boundary.

**Consequence (honest):** wired to a live reconcile *as-is*, this adapter would orphan every position (MM7G §2.1, pinned by `test_mismatched_namespace_same_position_double_false_divergence`). That is expected and safe — **6b.1 ships no live wiring** (`fno_runner` still refuses `ExecutionMode.LIVE` without `broker_positions`; the paper rung runs `broker_positions=None`). The adapter gains a live call-site only after 6b.2 (namespace) + 6b.3 (wiring).

---

## 3. Validation

| Command | Result |
|---|---|
| `pytest tests/execution/test_to_reconcile_positions.py -q` | **7 passed** (adapter unit) |
| `pytest tests/execution/test_to_reconcile_positions.py tests/execution/test_broker_positions_adapter.py tests/execution/test_reconciliation_broker.py tests/runtime/test_reconcile_symbol_namespace.py -q` | **20 passed** (unit + repointed MM7A / Phase-0 / MM7G nets) |
| `pytest -q` | **516 passed, 0 failing** (509 baseline + 7) |

The repointed nets pin that the production function reproduces the previously-glued contract exactly: enum→string trap (`test_naive_passthrough_with_enum_side_breaks_reconcile` still green — the raw enum still breaks reconcile, proving the adapter is required), LONG/SHORT/FLAT (`test_bridge_*`), end-to-end orphan/mismatch over the real `UpstoxAdapter` payload (`test_reconciliation_broker.py`), and the namespace hazard unchanged (`test_reconcile_symbol_namespace.py` — shape adapter carries the broker key through, so the 2-alert mismatch still stands; 6b.2 will flip it).

---

## 4. Remaining work (#6b.2)

**6b.2 — symbol-namespace mapping (the substantive risk, MM7G §4).** Decide route **R1** (adapter-local `trading_symbol → instrument_key` remap via the already-built `UpstoxMapping.from_broker_position`, `core/brokers/mapping/upstox.py:74-81` — unblocked) vs **R2** (full 4C.8 canonical↔canonical reconcile rewrite). Acceptance = flip `test_reconcile_symbol_namespace.py::test_mismatched_namespace_same_position_double_false_divergence` from 2 alerts → 0 (identical position under two namespaces must reconcile clean). The mapping is applied to the broker book's keys *around* `to_reconcile_positions` (before, on the input dict, or after, on the output `symbol`) — this shape function does not change. Note the 4C.7/G1 boundary: an `instrument_key`-aware step belongs in the broker/mapping layer or the composition root, not in `core/execution/`.

**6b.3 — live wiring.** Bind `broker_positions=lambda: to_reconcile_positions(<namespace-mapped> broker.get_positions())` in `fno_runner` on the `ExecutionMode.LIVE` rung only, behind F4. The #6a W3 guard (`driver.py:469-481`) already protects the raise path.

**Adapter follow-up (noted, not done):** `UpstoxAdapter.get_positions()` currently discards the raw payload's `instrument_token` (reads only `trading_symbol`/`quantity`/`average_price`, `:131-134`). For R1/R2 to use the preferred `from_broker_position` ikey path (rather than the `trading_symbol` fallback), 6b.2 should preserve `instrument_token` — a broker-layer change, out of 6b.1's shape-only scope.

---

## 5. Additional review (stated before coding)

1. **Assumptions:** (a) `symbol` = the broker dict KEY, verbatim, no translation (the established `_bridge` contract); (b) `Position.quantity` is absolute (brokers `abs()`; reconcile re-signs) so it passes through; (c) `Position.side` is a `PositionSide` enum whose `.value ∈ {LONG,SHORT,FLAT}`; (d) `{}` → `[]`.
2. **Alternative design considered:** teach `reconcile()` to accept `Dict[str, Position]` directly (transform in the engine) — **rejected** (MM7F F3: recouples the broker-agnostic engine to `Position`/`PositionSide`; also out of scope). A `BrokerAdapter` method returning reconcile-shape — **rejected** (couples broker to one consumer, loses keyed access). **Chosen:** standalone pure function, wired by the composition root in 6b.3.
3. **What could invalidate it:** (a) if 6b.2 picks the `canonical_id` route, the *caller* re-keys the dict — the function stays shape-only and unaffected, but a shape-only adapter wired live *without* 6b.2 orphans every position (expected; no live wiring here); (b) if a broker ever returned a **signed** quantity, the passthrough would double-count once reconcile re-signs — relies on the absolute-quantity invariant; (c) if `Position.side` were ever a raw string, `.value` would raise — relies on the enum type.

---

## 6. Stop condition

Implementation complete (`core/execution/broker_positions_adapter.py`, one pure function). Tests green (**516 passing, 0 failing**). Report written. Commit follows. **Did NOT:** implement namespace mapping (6b.2), live wiring (6b.3), 4C.8, F3, or F4; change `reconciliation.py` or any broker. The next slice is **#6b.2** — the symbol-namespace mapping (route R1 vs R2).

*Filed under the G1 / MM7A–G review-first, characterize-before-change discipline. Companion to `MM7G_NAMESPACE_CHARACTERIZATION.md` (#6b split) and `MM7F_BROKER_POSITIONS_ADAPTER_REVIEW.md` (F3 ownership).*
