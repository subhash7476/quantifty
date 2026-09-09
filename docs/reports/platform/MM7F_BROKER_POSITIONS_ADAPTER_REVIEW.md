# MM.7F — Broker-Positions Reconciliation Path Review (Planning Only)

**Type:** Review — reconciliation-path map + adapter-necessity verdict + ownership + characterization plan. **No code. No adapter. No W3 fix. No reconciliation change. No broker change. Review only.**
**Date:** 2026-06-12
**Basis:** `MM7_LIVE_WIRING_REVIEW.md` (W2/W3 + §3) · `MM7A_CHARACTERIZATION_REPORT.md` (T2/T3 net) · `MM7E_ENTRY_SCRIPT_REVIEW.md` (§4 refusal, §10 Design B) · `MM7E_IMPLEMENTATION_REPORT.md` (the landed root).
**Starting state:** G1 CLOSED · 505 passing · 0 failing · MM7E COMPLETE — `scripts/fno_runner.py` is the production composition root, accepting `broker_positions` by injection (default `None`).

> **Scope guard.** This review writes no code, builds no adapter, does not touch `core/execution/reconciliation.py`, does not touch any broker, and does not fix W3. It maps the path and recommends the next slice.

---

## 0. The required question — is a broker-positions adapter still required after MM7E?

**Verdict: PARTIAL.** A *transformation* between the broker's return shape and the reconciliation input is unavoidable — pure "Design B / direct consumption" is provably impossible (the naive pass-through raises). But (a) it is a ~4-line pure function, not a heavyweight adapter abstraction, and (b) it is **not on the MM7E paper rung's critical path at all** — at `Mode.LIVE`/`ExecutionMode.PAPER` the correct wiring is `broker_positions=None` (vacuous reconcile), and wiring the PaperBroker book would actively *break* reconciliation. The transformation becomes critical only at the real-broker (`UpstoxAdapter`) rung, which is already gated behind #6 / F4 / #4 / #5.

### Design A vs Design B, against the evidence

```
Design A:  PaperBroker / Broker → Adapter → Reconciliation
Design B:  PaperBroker / Broker → Direct consumption → Reconciliation
```

**Design B (literal pass-through) is impossible.** The two ends do not share a type, and the mismatch is not silently tolerated — it raises:

- Reconciliation requires `List[Dict[str, Any]]`, each `{'symbol': str, 'quantity': float, 'side': str}`, and it calls `bp.get('side', '').upper()` (`reconciliation.py:24,39-52`, `.upper()` at `:47`).
- Every `BrokerAdapter.get_positions()` returns `Dict[str, Position]` (`core/brokers/base.py:27`), with `side` a `PositionSide` **enum** and `quantity` already `abs()`'d (`upstox_adapter.py:126-152`; `paper_broker.py:48-49`).
- Passing the enum through provably raises `AttributeError` inside `reconcile` (enum has no `.upper()`) — pinned green at `tests/execution/test_broker_positions_adapter.py:84-89`.

So a `dict→list` + `enum→string` + `re-sign-from-side` transformation is **mandatory** before any real broker book reaches `reconcile()`. Design A is the only correct shape. **But** the "Adapter" box is small: the entire transformation already exists, twice, as four-line test glue — `_bridge` (`test_broker_positions_adapter.py:44-50`) and `_broker_positions_as_dicts` (`test_reconciliation_broker.py:26-31`):

```python
[{"symbol": sym, "quantity": pos.quantity, "side": pos.side.value}
 for sym, pos in adapter.get_positions().items()]
```

This is the whole adapter. The open question is therefore not "Design A or B" (A wins on type evidence) but **"is this worth a dedicated abstraction, and is it on any current critical path?"** — answered PARTIAL below.

---

## 1. Findings

### F1 — Actual contract mismatch (the real shape map)

| Aspect | `broker.get_positions()` returns | `reconcile()` requires | Mismatch? | Evidence |
|---|---|---|---|---|
| **Container type** | `Dict[str, Position]` (keyed by symbol) | `List[Dict[str, Any]]` | **Yes** — dict vs list | `base.py:27`; `reconciliation.py:24` |
| **Field carrier** | dataclass `Position` attributes | plain dict keys | **Yes** — object vs dict | `position_models.py:21-52`; `reconciliation.py:42,47` |
| **`symbol`** | `Position.symbol` property → `instrument.symbol` | `bp.get('symbol')` | name-compatible *if* keyed by the same namespace — **see F1-note** | `position_models.py:54-56`; `reconciliation.py:43` |
| **`quantity` semantics** | **absolute** (always `abs()`'d) | unsigned magnitude, re-signed from `side` | compatible — both unsigned, reconcile re-signs | `upstox_adapter.py:147`; `reconciliation.py:42-51` |
| **`side` representation** | `PositionSide` **enum** | **string** `'LONG'`/`'SHORT'` (`.upper()`-ed) | **Yes** — enum vs string; **the breaking one** | `position_models.py:15-18`; `reconciliation.py:47` |
| **`side` → sign** | enum carries direction | reconcile re-derives sign: `SHORT→-abs`, `LONG→+abs` | must survive the string round-trip (`enum.value`) | `reconciliation.py:48-51` |
| **`FLAT` / zero qty** | `PositionSide.FLAT`, `quantity 0.0` | `abs(qty)==0` ⇒ not an orphan | compatible (no alert) | `reconciliation.py:78`; test `:120-128` |

**Net mismatch = container (dict→list) + side carrier (enum→string).** Quantity, sign convention, and FLAT all survive once those two are bridged. The transformation is exactly: `.values()` → list, `pos.side.value` → string side, keep `pos.quantity` (already absolute). This is the contract `tests/execution/test_broker_positions_adapter.py` already pins (LONG no-alert `:95-105`, SHORT orphan re-signed `-5.0` `:108-117`, FLAT no-alert `:120-128`).

**F1-note (the mismatch the table understates — see F6-1).** The shape mismatch is trivial. The *symbol-namespace* mismatch is not. `UpstoxAdapter.get_positions()` keys on the broker's `trading_symbol` (`upstox_adapter.py:131-132`, e.g. `"NIFTY24..CE"`), whereas the handler's `PositionTracker` keys on the driver's symbol — broker instrument keys like `NSE_FO|54710`. `reconcile()` is a raw-string key match (`reconciliation.py:54,57,77`). A field-shape adapter that does not also reconcile the *key namespace* will make **every live position** an `ORPHANED_BROKER_POSITION` + `QUANTITY_MISMATCH`. The existing tests hide this by using `"RELIANCE"` on both sides. This is the substantive adapter problem; the enum→string fix is cosmetic by comparison.

### F2 — Live vs Paper: can reconciliation operate today on PaperBroker state without an adapter?

**No — and it must not try. The correct paper behavior is vacuous reconcile (`broker_positions=None`), which is what MM7E already wires.** Two independent reasons:

1. **PaperBroker's book is permanently empty.** `PaperBroker.place_order` (`paper_broker.py:26-43`) **never updates `self.tracker`** — the only references to `self.tracker` are its construction (`:22`) and `get_positions` (`:49`). Fills flow through the *handler's* tracker via the gated `_handle_broker_fill` path, not the broker's. So `PaperBroker.get_positions()` always returns `{}`. (Grep confirms: `tracker` appears only at `paper_broker.py:22,49`.)
2. **Wiring that empty book would manufacture false divergence.** `reconcile()` compares the handler's *restored* tracker (which may hold real positions) against the broker map. With an empty broker map, any open internal position trips `abs(internal_net - 0) > 1e-6` → `QUANTITY_MISMATCH` (`reconciliation.py:61-74`), aborting startup on a phantom. So at PAPER, `broker_positions=None` (vacuous-clear, `driver.py:462-463`) is not a stopgap — it is the *correct* design, and `fno_runner` already does exactly this and warns the operator the gate has no teeth (`fno_runner.py:103-107`).

**Conclusion:** for `Mode.LIVE` + `ExecutionMode.PAPER` (the MM7E target), the adapter is **deferrable — it is off the critical path**. Reconciliation against a *real* broker book is meaningful only with a `LIVE`-broker (`UpstoxAdapter`), i.e. `ExecutionMode.LIVE` — which `fno_runner` refuses today without `broker_positions` (`fno_runner.py:79-83`). So the adapter is **critical-path only for the `ExecutionMode.LIVE` rung**, which is itself blocked on F4 / #4 / #5. The adapter is therefore correctly sequenced *after* MM7E and *with* the `LIVE` rung, not before.

### F3 — Ownership of the transformation

**Recommendation: a standalone pure adapter function (the "Adapter" option), wired by the composition root.** Not the broker, not reconciliation.

| Candidate owner | Verdict | Why |
|---|---|---|
| **Broker** | **No** | `BrokerAdapter.get_positions() -> Dict[str, Position]` is the abstract contract two brokers implement (`base.py:27`; `upstox_adapter.py:126`, `paper_broker.py:48`). The keyed dict is the *useful* broker shape (callers index by symbol). Folding reconcile's list-of-dicts into the broker couples the broker to one consumer's primitive and loses keyed access. Violates "Strategies/brokers stay dumb." |
| **Reconciliation** | **No** | `reconcile()` deliberately takes a broker-agnostic primitive (`List[Dict]`), decoupled from the `Position` model and `PositionSide` enum (`reconciliation.py:24-32`). Teaching it to accept `Dict[str, Position]` couples the execution-core comparison engine to broker types and the enum — a regression of the decoupling that is its design. |
| **Adapter (standalone fn)** | **Yes — primary** | A pure `to_reconcile_positions(Dict[str, Position]) -> List[Dict]`. Single responsibility, broker-agnostic in, reconcile-shaped out, testable in isolation (T2 *is* its acceptance), and the natural home for the F1-note key-namespace mapping when it lands. Kills the duplicated `_bridge`/`_broker_positions_as_dicts` glue. |
| **Composition Root** | **Owns the wiring, not the transform** | The root binds it: `broker_positions=lambda: to_reconcile_positions(broker.get_positions())`. That closure is the root's job (it is where collaborators meet, per Design B / `config.py:9-13`). But the transformation *logic* should not be inlined in `fno_runner` — keep it a unit-testable function so the root stays pure plumbing. |

So: **Adapter owns the transformation; the composition root owns the binding.** This matches the Design-B grain MM7E already set (root wires, does not author logic).

### F4 — Does W3 depend on the adapter?

**No. W3 can and should be solved independently of (and before) the adapter.** W3 is the failure contract: a raising `broker_positions()` propagates uncaught out of `run()`, leaving the driver stuck in `RECOVERY` with no `STOPPED`, no `RECONCILIATION_FAIL`, no journal (pinned at `test_driver_broker_positions_failure.py`; root cause `driver.py:464` runs inside `_reconcile_ledger`, *before* `run()`'s `try/finally` at `:524`).

- **W3 is a driver-gate property, not a broker-shape property.** The fix is a `try/except` around `self._broker_positions()` in `_reconcile_ledger` (`driver.py:464`) that converts any exception into the existing refusal contract — `RECONCILIATION_FAIL` → `alerter.critical` → `abort_startup()` → `STOPPED` (mirroring the alert-path already there at `:465-475`). It touches no broker and no adapter.
- **The W3 net needs no adapter.** T3 injects a raising **lambda** directly (`test_driver_broker_positions_failure.py:80-85`) — it never constructs a broker or an adapter. The fix flips T3's assertions against that same lambda.
- **They are correctly sequenced together but are independent code.** The adapter introduces the *first real callable that can raise* (broker auth/transport — `upstox_adapter.py:60-62` raises `RuntimeError` on 401/403). So both want to land before `ExecutionMode.LIVE`. But W3 is a pure hardening of the gate that can land **now**, with zero broker dependency, and removes a live-safety hazard ahead of any adapter. **The adapter does not need to land first; if anything W3 should.**

### F5 — see §5 (Characterization Plan).

### F6 — see §6 (Risk Review).

---

## 2. Evidence index (file:line)

| Claim | Evidence |
|---|---|
| reconcile input = `List[Dict]`, `side` string `.upper()`-ed | `core/execution/reconciliation.py:24,39-52` (`.upper()` `:47`; re-sign `:48-51`) |
| broker output = `Dict[str, Position]`, `side` enum, `quantity` abs | `core/brokers/base.py:27`; `core/brokers/upstox_adapter.py:126-152` (abs `:147`); `core/brokers/paper_broker.py:48-49` |
| naive enum pass-through raises | `tests/execution/test_broker_positions_adapter.py:84-89` |
| the whole transformation = 4-line glue (×2, duplicated) | `tests/execution/test_broker_positions_adapter.py:44-50`; `tests/execution/test_reconciliation_broker.py:26-31` |
| LONG/SHORT/FLAT semantics preserved by the bridge | `test_broker_positions_adapter.py:95-128` |
| PaperBroker book always empty (place_order never updates tracker) | `core/brokers/paper_broker.py:22,26-43,49` (tracker only at `:22,49`) |
| PAPER vacuous reconcile is correct + warned | `core/runtime/driver.py:462-463`; `scripts/fno_runner.py:103-107` |
| reconcile aborts on phantom mismatch if empty broker book wired | `core/execution/reconciliation.py:61-74` |
| `ExecutionMode.LIVE` refused without `broker_positions` (root) | `scripts/fno_runner.py:79-83` |
| W3: raising callable escapes `run()`, driver stuck RECOVERY | `core/runtime/driver.py:464` vs `try/finally` `:524`; `tests/runtime/test_driver_broker_positions_failure.py` |
| W3 fix site = gate, no broker dependency; refusal contract exists | `core/runtime/driver.py:464-477` |
| symbol-namespace mismatch (broker `trading_symbol` vs internal key) | `core/brokers/upstox_adapter.py:131-132` vs `reconciliation.py:54,57,77`; MM7 §3.1 (4C.8 `UpstoxMapping.from_broker_position`) |
| reconcile is keyed on raw symbol string | `core/execution/reconciliation.py:54,57,77` |

---

## 3. Adapter necessity verdict

**PARTIAL.**

- **A transformation is required (YES).** `dict→list` + `enum→string` is mandatory before any real broker book reaches `reconcile()`; the naive pass-through raises (`test_broker_positions_adapter.py:84-89`). Pure "Design B / direct consumption" is impossible. Design A (Broker → Adapter → Reconciliation) is the only correct shape.
- **A dedicated heavyweight adapter is NOT required (NO).** The transform is a 4-line pure function (already written twice as test glue). It deserves *one* unit-tested function, not a class hierarchy.
- **It is not on the MM7E paper rung's critical path (NO).** At `Mode.LIVE`/`ExecutionMode.PAPER`, `broker_positions=None` is *correct* (PaperBroker book is empty; wiring it manufactures false alerts). The adapter is critical only at the `UpstoxAdapter` / `ExecutionMode.LIVE` rung — already gated behind #6/F4/#4/#5.

So: **required for live reconciliation, deferrable for everything MM7E ships, and small.** The honest engineering answer is "yes a transform, no a framework, not yet on the critical path."

---

## 4. Ownership recommendation

**A standalone pure function — `to_reconcile_positions(Dict[str, Position]) -> List[Dict]` — owned in the execution/broker-bridge layer, wired by the composition root via a closure.** Not on the broker (keeps both broker implementations dumb and the keyed dict intact), not in reconciliation (preserves its broker-agnostic primitive input and decoupling from `PositionSide`). The composition root owns only the binding `broker_positions=lambda: to_reconcile_positions(broker.get_positions())`. Promote the duplicated `_bridge` / `_broker_positions_as_dicts` glue into this single function so its contract has exactly one home (the one T2 already pins).

---

## 5. Characterization plan (tests required before implementation — no implementation here)

Most of the net **already exists** (MM7A T2/T3). The new work is small and additive.

**Already in place — reuse as acceptance:**

| File | Tests | Role |
|---|---|---|
| `tests/execution/test_broker_positions_adapter.py` | `test_adapter_returns_dict_reconcile_needs_list`, `test_position_side_is_enum_not_string`, `test_naive_passthrough_with_enum_side_breaks_reconcile`, `test_bridge_long/short/flat_*` | The adapter's acceptance contract (shape + enum-trap + LONG/SHORT/FLAT). When the production `to_reconcile_positions` lands, repoint these from `_bridge` to the real function. |
| `tests/execution/test_reconciliation_broker.py` | consistent / quantity-mismatch / orphaned-short | End-to-end reconcile over a (mocked) `UpstoxAdapter` payload; second consumer of the same glue to consolidate. |
| `tests/runtime/test_driver_broker_positions_failure.py` | T3 (3 tests, RED-documenting) | W3 defect pin; the W3 fix **flips** these. |

**New tests to add before the slice:**

| File | Test names | Acceptance criteria |
|---|---|---|
| `tests/execution/test_to_reconcile_positions.py` *(new — adapter unit)* | `test_listifies_dict_keyed_positions`; `test_side_enum_becomes_string`; `test_quantity_stays_absolute`; `test_flat_zero_qty_round_trips`; `test_empty_book_yields_empty_list` | The production function reproduces the `_bridge` contract exactly: dict→list, `pos.side.value` string, `pos.quantity` unchanged, FLAT→`"FLAT"`, `{}`→`[]`. Replaces the duplicated glue. |
| `tests/runtime/test_driver_broker_positions_failure.py` *(flip in #6 — author the target now)* | `test_raising_broker_positions_emits_reconciliation_fail`; `test_driver_reaches_stopped_after_broker_positions_raises`; `test_journal_records_refusal_and_critical_alert` | After the W3 fix: a raising `broker_positions` ⇒ `RECONCILIATION_FAIL` journaled, `state is STOPPED`, `bars_processed == 0`, one `alerter.critical`. The mirror image of the current RED pins. |
| `tests/execution/test_paper_broker_book_is_empty.py` *(new — F2 guard)* | `test_paper_broker_get_positions_empty_after_order`; `test_wiring_paper_book_would_orphan_internal` | Pin *why* PAPER must stay vacuous: `PaperBroker.get_positions() == {}` after `place_order`; and reconciling a non-empty internal tracker against that empty book yields `QUANTITY_MISMATCH` — proving the vacuous default is correct, not lazy. |
| `tests/execution/test_reconcile_symbol_namespace.py` *(new — F1-note, the real risk)* | `test_broker_trading_symbol_vs_internal_key_orphans`; `test_namespace_aligned_reconcile_passes` | Pin the key-namespace hazard: a broker `trading_symbol` that differs from the internal ledger key produces a false orphan; an aligned key reconciles clean. This is the test the existing net is *missing* (it uses matching `"RELIANCE"` both sides). Drives whether the adapter must also key-map (4C.8 `UpstoxMapping`). |

**Sequencing rule:** do not land the adapter/W3 slice until `test_to_reconcile_positions.py` is green against the real function, T3 is consciously flipped, and the symbol-namespace test has forced an explicit decision on key-mapping (align in the adapter now, or defer to 4C.8 with the live rung blocked until then).

---

## 6. Risk assessment

**1 — Highest-risk assumption: that the field-shape adapter is the whole job. It is not — the symbol-namespace mismatch (F1-note) is.**
The enum→string + dict→list bridge is trivial and fully netted. The unmodelled risk is that `UpstoxAdapter` keys positions on broker `trading_symbol` (`upstox_adapter.py:131-132`) while the internal ledger keys on the driver's instrument key (`NSE_FO|<token>`), and `reconcile()` is a raw string match (`reconciliation.py:54,57,77`). A shape-only adapter would orphan/mismatch **every** live position — a reconciliation that refuses to start *every time*, or worse, one quietly tuned to pass by disabling the check. Existing T2/Phase-0 tests mask this with matching `"RELIANCE"` strings. **Mitigation:** the adapter must own (or explicitly defer to 4C.8 `UpstoxMapping.from_broker_position`) the canonical-key mapping; the new namespace test forces the decision before any live reconcile.

**2 — Simplest implementation path:** promote the existing 4-line `_bridge` into one function `to_reconcile_positions`, repoint the two test files at it, and wire it in `fno_runner` only on the `ExecutionMode.LIVE` rung — *plus* the W3 `try/except` in `_reconcile_ledger`. The shape half is an afternoon; the genuine work is the key-namespace decision (risk 1).

**3 — What could eliminate the adapter entirely:** teaching `reconcile()` to accept `Dict[str, Position]` directly (move the transform into the engine) — **rejected**: it recouples the broker-agnostic comparison engine to the `Position`/`PositionSide` types, the exact decoupling that is its design (F3). Alternatively, the adapter *is* effectively eliminated for the entire MM7E surface because the paper rung needs `broker_positions=None` (F2) — so "eliminate" is already true for everything shipped to date; only the live-broker rung needs it.

**4 — Alternative design considered:** make `BrokerAdapter.get_positions()` return reconcile-shaped `List[Dict]` natively (Broker owns the transform). **Rejected** (F3): two brokers implement the contract, callers want keyed access, and it couples the broker to one consumer's primitive. The standalone-function design keeps the broker dumb and the engine decoupled.

---

## Additional review requirement (A / B / C / D)

### A — Do I agree with the current MM7 roadmap?

**Yes, with one decomposition refinement.** The roadmap sequences the adapter + W3 as a single item #6, *after* MM7E and *before* `ExecutionMode.LIVE` — which is correct: F2 proves the paper rung neither needs nor can use the adapter, so building it before MM7E would have produced a tested artifact with no live call-site, and W3's hazard only bites once a real callable is wired. The characterize-before-change net (T2/T3) is already in place. I agree the adapter is *not* the next blocker for the paper rung.

### B — Alternative roadmap proposed

**Split #6 into #6a and #6b, and pull #6a forward:**

- **#6a — W3 gate hardening (do now, decoupled).** `try/except` around `self._broker_positions()` in `_reconcile_ledger` → refusal → `STOPPED` → journal (flip T3). Zero broker/adapter dependency; removes a live-safety hazard regardless of when the adapter lands. Safe to land on top of MM7E immediately.
- **#6b — adapter + key-namespace, with the LIVE rung.** `to_reconcile_positions` (+ canonical key mapping / 4C.8), wired in `fno_runner` only for `ExecutionMode.LIVE`, behind F4. Acceptance = T2 + the new namespace test.

This is a *decomposition* of the roadmap's #6, not a reordering of #6 vs MM7E (that reorder was already correctly rejected in MM7E §0.B). The win: a risk-free safety fix (#6a) stops waiting behind the alpha-blocked live rung.

### C — Assumptions (all stated)

1. **Reconciliation keys on raw symbol strings** (`reconciliation.py:54,57,77`) and the internal tracker + broker must agree on that namespace. **Load-bearing** (risk 1).
2. **`UpstoxAdapter.get_positions()` is the live broker source** for real reconciliation; `PaperBroker` is never a meaningful reconcile source (F2). Assumed from `base.py:27` + the empty-book finding.
3. **The driver's refusal contract (`abort_startup` → `STOPPED` → journal) is the intended W3 target** — same shape as `RECONCILIATION_FAIL` (`driver.py:465-475`). Asserted by MM7/MM7A; not re-litigated.
4. **`ExecutionMode.LIVE` stays out of scope until F4/#4/#5** — so the adapter has no production consumer until then; `fno_runner` enforces this (`:79-83`).
5. **4C.8 `UpstoxMapping.from_broker_position` is the intended canonical-key path** (MM7 §3.1) — assumed available or buildable when #6b lands. Not verified this slice (I did not open 4C.8 code).

### D — Questions whose answers would materially change implementation

1. **Does the adapter key-map now, or defer to 4C.8?** If now, #6b grows to include canonical key resolution (the substantive work). If deferred, the live reconcile rung is **blocked** until 4C.8 — and that dependency must be explicit, because a shape-only adapter shipped without it would silently orphan every live position (risk 1). *This is the single answer that changes #6b's size.*
2. **Should #6a (W3 fix) land independently and now?** If yes (recommended), it is a small, risk-free driver hardening decoupled from the adapter. If the owner wants #6 to stay atomic, the W3 safety fix waits behind the alpha-blocked live rung for no technical reason.
3. **Is there ever a non-Upstox live broker?** If a second live broker is planned, the standalone-function design (F3) is reinforced; if Upstox is the only live broker forever, a broker-method transform becomes *defensible* (still not recommended, but the F3 trade-off softens).

---

## 7. Recommended next implementation slice

**#6a — W3 gate hardening (next, now, decoupled from the adapter).** A `try/except` in `_reconcile_ledger` (`driver.py:464`) converting any `broker_positions()` exception into the existing refusal contract (`RECONCILIATION_FAIL` → `alerter.critical` → `abort_startup` → `STOPPED` → journal). Acceptance = flipping T3 (`test_driver_broker_positions_failure.py`) from defect-pin to refusal-pin. No broker, no adapter, no reconciliation-logic change. This is the smallest safe step and removes a live-safety hazard ahead of the (alpha-blocked) live rung.

**Then #6b — adapter + key-namespace, bundled with the `ExecutionMode.LIVE` rung** (behind F4/#4/#5): promote `to_reconcile_positions`, decide key-mapping (align now vs defer to 4C.8), wire it in `fno_runner` for `ExecutionMode.LIVE` only.

---

## Stop condition / return summary

Review complete. Report written. **No code, no adapter, no W3 fix, no reconciliation change, no broker change, no tests, no commit.** `core/execution/reconciliation.py`, both brokers, and the driver are untouched.

1. **Adapter required?** **PARTIAL** — a `dict→list` + `enum→string` transformation is mandatory before any *real* broker book reaches `reconcile()` (pure pass-through provably raises), so Design A is the only correct shape; but it is a ~4-line function (not a framework) and is **off the MM7E paper rung's critical path** — at `ExecutionMode.PAPER` `broker_positions=None` is *correct* (PaperBroker's book is permanently empty; wiring it manufactures false alerts). Critical only at the `UpstoxAdapter` / `ExecutionMode.LIVE` rung, already gated behind #6/F4/#4/#5.
2. **Recommended owner:** a standalone pure function `to_reconcile_positions(Dict[str, Position]) -> List[Dict]` (execution/bridge layer), **wired by the composition root** via a closure — not the broker (keeps it dumb), not reconciliation (keeps it broker-agnostic).
3. **Required characterization:** reuse T2 (`test_broker_positions_adapter.py`) + T3 (`test_driver_broker_positions_failure.py`); add `test_to_reconcile_positions.py` (adapter unit), the T3 flip targets (W3 refusal→STOPPED→journal), `test_paper_broker_book_is_empty.py` (F2 guard), and — critically — `test_reconcile_symbol_namespace.py` (the key-namespace hazard the current net omits).
4. **Recommended next slice:** **#6a — W3 gate hardening now** (decoupled, risk-free, flips T3); **then #6b — adapter + key-namespace bundled with the `ExecutionMode.LIVE` rung** behind F4.
5. **Assumptions that may be wrong:** (a) that the field-shape bridge is the whole job — the **symbol-namespace** mismatch (broker `trading_symbol` vs internal `NSE_FO|<token>`, masked by matching-`"RELIANCE"` tests) is the real risk and would orphan every live position; (b) that 4C.8 `UpstoxMapping.from_broker_position` will be available when #6b needs canonical key-mapping (not verified this slice); (c) that `UpstoxAdapter` is the sole live broker source for reconciliation.

---

*Filed under the G1 / MM7A–E review-first, characterize-before-change discipline. Companion to `MM7_LIVE_WIRING_REVIEW.md` (§3), `MM7A_CHARACTERIZATION_REPORT.md` (T2/T3), and `MM7E_ENTRY_SCRIPT_REVIEW.md` (§4, §10).*
