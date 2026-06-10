# G1_WAVE3B_GATE_ORDERING_REVIEW.md

**Type:** Gate G1 — **Wave 3B. Gate-ordering review + driver-level characterization. Review + tests ONLY; NO production code, NO migration, NO restore/persistence/reconciliation/driver behavior change, NO commits until review.**
**Date:** 2026-06-10
**Parent plan:** `SOLE_IDENTITY_PATH_REVIEW.md` (Option B locked, §3) · `G1_WAVE3_RESTORE_REVIEW.md` (restore survey; §6 sequence) · `G1_WAVE3A_CHARACTERIZATION_REPORT.md` (restore reality pinned; §7 gap 1, §8 prereq 2)
**Objective:** answer the three questions Wave 3A left as the Wave-3 implementation preconditions — (1) *where exactly* does the Option-B post-gate canonicalization pass insert, (2) what is the proven recovery → readiness → reconciliation ordering it slots into, and (3) **must restored orders and restored positions migrate together, or separately?** — and build the one missing test (the driver-level post-gate ordering pin) needed to make question 3 decidable.
**Outcome:** insertion point mapped to a single line gap (`driver.py:357`→`:360`); ordering characterized and pinned at the **call level** (not just journal events); **decision: SEPARATE** — restored orders (#8) and restored positions (#7-as-restored) migrate as two independently-revertible commits in either order, because they reconstruct via independent mechanisms on independent objects and the only intervening gate (reconciliation) is symbol-keyed and identity-blind; **both are required for Section-6 closure**, and the interim order-vs-position type inconsistency between the two commits is **latent, not active** (no live consumer cross-checks them). 5 new driver-level characterization tests, green on first run. Full suite **388 → 393 passing, 0 failing**.

---

## 1 — The exact Option-B insertion point (file:line)

Option B (`SOLE_IDENTITY_PATH_REVIEW.md` §3, locked): `_replay_state()` keeps building **legacy** instruments at handler construction (master-independent, ADR-003); a **single post-gate canonicalization pass** re-resolves the restored ledger's identities through `InstrumentResolver` **after** the MM.4 master-readiness gate confirms the master is present and **before** reconciliation.

The pass inserts at **one line gap** inside `LoopDriver._run_startup_gate` (`core/runtime/driver.py:335-364`):

```
driver.py:346   self.enter_recovery()                       # STARTUP -> RECOVERY
driver.py:347   _emit(RECOVERY_STARTED)
driver.py:351   _emit(RECOVERY_COMPLETED)                    # reuse _replay_state; never re-run (ADR-001)
driver.py:352   _meter(RECOVERY_COUNT)
driver.py:357   if not self._check_master_readiness(): return False    # MM.4 gate
        ▲────────────────────────  OPTION-B HOOK INSERTION POINT  ────────────────────────▲
driver.py:360   if not self._reconcile_ledger(): return False          # reconciliation
driver.py:363   self.start()                                 # RECOVERY -> RUNNING
driver.py:364   return True
```

**Insertion contract (the single new statement Wave 3 adds):** between `driver.py:357` returning `True` and `driver.py:360`, exactly as `G1_WAVE3_RESTORE_REVIEW.md` §6 step 3 specified:

```python
        if not self._check_master_readiness():
            return False
        self._canonicalize_restored_ledger()      # <-- NEW (Option-B post-gate pass)
        if not self._reconcile_ledger():
            return False
```

**Gating condition (identical to MM.4, `driver.py:377-379`):** the pass is a no-op unless `self._config.is_live and has_derivatives(self._config.symbols) and <master ready>`. This preserves paper / replay / equity-only-LIVE behavior byte-for-byte (the carve-outs, `SOLE_IDENTITY_PATH_REVIEW.md` §3 / `G1_WAVE3_RESTORE_REVIEW.md` §3). Because the insertion is **after** `_check_master_readiness()` returns `True`, it runs on **FRESH and WARN** (both proceed) and **never on BLOCK** (BLOCK returns `False` at `:357`, before the hook).

**Why not earlier (at the restore site) or later (after reconcile):**
- **Not at `_replay_state` (`handler.py:219`, runs at construction `:186-187`):** that is *before* the MM.4 gate, so it would resolve against a not-yet-verified master → env-dependent restore type-flip (ADR-003 violation; `G1_WAVE3_RESTORE_REVIEW.md` H4). This is the precise collision Option B exists to avoid.
- **Not after `_reconcile_ledger` (`:360`):** reconciliation must match positions through trustworthy identity (MM.4 Decision 2, `driver.py:354-355`); canonicalizing after reconcile defeats that intent. (In practice reconciliation is symbol-keyed today — §3 H3 — so it would not *break*, but the ordering intent is to canonicalize first.)

---

## 2 — Recovery → readiness → reconciliation ordering (proven, not assumed)

### 2.1 The sequence (file:line)

| Step | What | Where | When |
|---|---|---|---|
| **recovery (the actual restore)** | `_replay_state()` rebuilds orders/fills/positions/seen-signals/groups | `handler.py:186-187` → `:219-265` | **handler construction**, before `run()` |
| recovery (driver bookkeeping) | `enter_recovery()`; `RECOVERY_STARTED`; `RECOVERY_COMPLETED` — the driver **reuses** the construction-time restore and **never** calls `_replay_state` itself (ADR-001) | `driver.py:346-352` | first thing in `_run_startup_gate` |
| **readiness (MM.4)** | `_check_master_readiness()` → FRESH/WARN proceed, BLOCK → `abort_startup()` | `driver.py:357`, `:366-411` | after RECOVERY_COMPLETED |
| **reconciliation** | `_reconcile_ledger()` → PASS proceeds, non-empty alerts → `abort_startup()` | `driver.py:360`, `:413-444` | after readiness |
| start | `start()` → RUNNING | `driver.py:363` | after reconciliation PASS |

So the proven order is **`_replay_state` (ctor) → RECOVERY_STARTED → RECOVERY_COMPLETED → master-readiness (MM.4) → reconciliation → RUNNING**, confirming `G1_WAVE3_RESTORE_REVIEW.md` §1 and `SOLE_IDENTITY_PATH_REVIEW.md` §1's construction-vs-gate timing.

### 2.2 The journal-vs-call gap (why Wave 3A's deferred test was actually needed)

`_check_master_readiness` emits a journal event **only on WARN (`INSTRUMENT_MASTER_STALE`) or BLOCK (`INSTRUMENT_MASTER_UNAVAILABLE`)** — **never on FRESH** (`driver.py:382-411`: FRESH falls through with no `_emit`). Consequence: on the **FRESH path** (the normal live-F&O start), the journal shows `RECOVERY_COMPLETED` immediately followed by `RECONCILIATION_PASS` with **nothing in between** — the readiness check, and therefore the Option-B hook's slot, is **invisible to the journal**.

The pre-existing ordering test (`test_driver_master_readiness.py::test_master_check_runs_before_reconciliation`) asserts journal order on the **WARN path only**, precisely because WARN is the only verdict that leaves a journal marker in the slot. That test cannot pin the FRESH-path slot. This is exactly why Wave 3A §7 gap 1 deferred the "driver-level post-gate ordering test" and §8 prereq 2 named it the first Wave-3 implementation step: the slot the hook occupies has to be pinned at the **call level**, not the journal level. §4 builds that test.

---

## 3 — Decision: do restored orders and restored positions migrate together or separately?

**Decision: SEPARATELY** — two independently-revertible commits (`G1_WAVE3_RESTORE_REVIEW.md` §6 steps 4 then 5), in **either order**. Both are required for Section-6 closure; neither alone closes G1. The reasoning, grounded in code:

### 3.1 They reconstruct via independent mechanisms on independent objects

| | Restored **order** identity (#8) | Restored **position** identity (#7-as-restored) |
|---|---|---|
| Rebuilt by | `order_repo.get_all()` → `InstrumentParser.parse(row[1])` | fill replay → `update_from_fill` → `get_position(symbol)` → `parse` |
| Site | `order_repository.py:60` | `position_tracker.py:31` |
| Lives on | `NormalizedOrder.instrument` | `Position.instrument` |
| Keyed by | `correlation_id` | `symbol` |
| Snapshot table (#9) | n/a | `position_repository.load_all` — **dead, no caller** (H6) |

The two objects never share an instrument; an in-place `.instrument` swap on one (the H7/H8-mandated mutation) cannot touch the other. There is no shared state to make them atomic.

### 3.2 The only gate between them and RUNNING is identity-blind

`_reconcile_ledger` (`driver.py:431`) calls `reconciliation.reconcile(...)`, which (`reconciliation.py:39-85`) iterates **`position_tracker._positions`** and keys both the broker map and the internal map on the **raw `symbol` string** — it never reads orders at all, and never reads any instrument field (type/lot/`instrument_key`). Pinned by the Wave 3A suite (Group C + H6).

Therefore:
- Canonicalizing **orders** has **zero** effect on the reconciliation verdict (orders are not consulted).
- Canonicalizing **positions** also has **zero** effect on the verdict, because the in-place swap preserves `.symbol` byte-for-byte (H3 mandate) and reconciliation keys only on symbol.

Either commit can land alone and leave reconciliation green. Neither can break the gate or the other. → no atomicity requirement.

### 3.3 The position identity is the corruption-relevant one; the order identity is mostly a record

What actually *consumes* a restored instrument after restart determines where the H1/H2 corruption bites:

- **Restored position `.instrument` is actively consumed by risk:** `PortfolioGreeks._calculate_position_greeks` (`portfolio_greeks.py:48,56,73`) reads `position.instrument` (`.underlying`, asset-class dispatch, multiplier/lot via `GreeksCalculator.calculate`); `MarginTracker` reads positions too. The H1 (Equity-typed future) / H2 (lot-1 option) corruption changes greeks/margin **silently across a restart** through the *position* instrument.
- **Restored order `.instrument` is largely inert post-restore:** group reconstruction reads `group_id`/`metadata`/`correlation_id` (`handler.py:236-256`), idempotency reads `signal_id` (`:227-228`) — neither reads `order.instrument`; reconciliation ignores orders; the restored order is **not re-sent to the broker**. Its instrument is a historical record, not a live input.

So the **position** canonicalization is the one that actually remediates the across-restart risk corruption; the **order** canonicalization is for record-consistency and the Section-6 closure proof ("no live-F&O order identity is parse-built"). They serve different ends, reinforcing that they are separable units of work — and that, if anything, the position pass is the higher-value half.

### 3.4 The cost of "separate": a latent, not active, interim inconsistency

Between the two commits, a restored future's **order** could be `FUTURE` (canonical) while its **position** is still `EQUITY` (parse-built) for the same symbol — a forward/restore-style asymmetry now living *within* a single restored runtime. This is acceptable because it is **latent**: no consumer cross-checks order-identity against position-identity (reconciliation is symbol-keyed; greeks read positions only; idempotency/groups read neither instrument). It is the same class of divergence Wave 3A §6 already documented for forward-vs-restore position identity. **It must be named in the Wave-3 KB sync** (mirrors `G1_WAVE3A` §8 prereq 1), not silently accepted. Per-commit revertibility (the reason for separating) is worth this documented latency.

### 3.5 Section-6 closure spans both

`SOLE_IDENTITY_PATH_REVIEW.md` §6 criterion #3 ("no restart leaves a live F&O entry legacy-typed once the gate has passed") covers **orders and positions**. "Separate" therefore means *separate commits*, not *one optional*. The Wave-5 AST/grep guard (§6 criterion #5) will fail if **either** an order- or a position-build path reaches `InstrumentParser.parse` on the live F&O restore path. Both must land before G1 flips to "No."

### 3.6 Recommended sequencing (a rollback-granularity choice, not a correctness one)

Because they are independent, order is free. The plan's order (#8 orders first, then #7-as-restored positions, `G1_WAVE3_RESTORE_REVIEW.md` §6 steps 4→5) is fine. A defensible alternative is **positions first** (the corruption-relevant, must-have half), so the highest-value fix lands and can be validated before the lower-impact order-record fix. Either way: **one revertible commit each, both behind the §1 gating condition, both with the Section-4 characterization suite green before and after.**

---

## 4 — Test built (the one missing test for the decision)

`tests/runtime/test_driver_gate_ordering.py` — **5 driver-level characterization tests, green on first run** (they encode current behavior; **zero production code changed**). This is the test Wave 3A §7 gap 1 / Wave 3 review §4 gap 4 + §6 step 2 named as the first Wave-3 step. It records the **call sequence** across both gate steps via a shared recorder (the master-readiness checker appends `"READINESS"`; a wrapped `reconciliation.reconcile` appends `"RECONCILE"`), so `seq` *is* the interleaving the Option-B hook inserts into — the contract the journal cannot express on the FRESH path (§2.2).

| Test | Pins |
|---|---|
| `test_fresh_call_order_is_readiness_then_reconcile` | FRESH: `seq == ["READINESS", "RECONCILE"]`. **The hook inserts at index 1** — the core insertion contract; post-migration becomes `["READINESS", "CANONICALIZE", "RECONCILE"]`. |
| `test_fresh_journal_has_no_master_event_in_the_slot` | FRESH emits no master event → `RECONCILIATION_PASS` is journaled immediately after `RECOVERY_COMPLETED`. Documents *why* a call-order spy (not the journal) defines the FRESH slot. |
| `test_warn_call_order_is_readiness_then_reconcile` | WARN: same call order (gate passes), `INSTRUMENT_MASTER_STALE` < `RECONCILIATION_PASS`, one warning alert. The hook runs on WARN too. |
| `test_block_stops_before_reconcile_and_before_hook_slot` | BLOCK: `seq == ["READINESS"]`, 0 bars, STOPPED, one critical alert, no `RECONCILIATION_PASS`/`RUNNING`. Reconcile **and the hook** are unreached — canonicalization never runs on a refused start. |
| `test_no_checker_records_reconcile_only` | No checker injected (today's live-F&O-deferred reality): `seq == ["RECONCILE"]` (readiness never invoked). The gated hook would likewise not canonicalize — consistent with the MM.4 vacuous-pass contract. |

**Why these make the §3 decision executable:** they pin that the hook's slot is a single, well-defined point between two calls that are *already independent* of order/position identity (readiness evaluates a handed-in verdict; reconcile reads positions-by-symbol). The tests demonstrate the gate neither consults restored order identity nor restored position instrument fields to decide pass/fail — the runtime-level confirmation of §3.2 that lets orders and positions migrate as separate commits without coupling through the gate.

No production code was touched, so no existing characterization assertion moved; the 5 new tests are pure additions.

---

## 5 — What this review did NOT do (scope adherence)

**Added:** the gate-ordering characterization suite + this report. **NOT touched (verified — working tree contains only the two new files):** `driver.py` (no hook added — `_run_startup_gate` unchanged), `handler.py`/`_replay_state`, persistence, `reconciliation.py`, `InstrumentParser`, the canonical layer, the resolver, MM.4/MM.7 wiring. **No restore migration, no `_canonicalize_restored_ledger` method, no commits.** Gate G1 remains **OPEN**; Wave 3 (#2 restore migration) and Wave 4 (#4 option) remain **NOT STARTED** — this review only mapped the insertion point, proved the ordering, decided the orders-vs-positions question, and built the slot's tripwire.

---

## 6 — Recommended Wave 3 implementation sequence (refines `G1_WAVE3_RESTORE_REVIEW.md` §6 with this review's findings)

1. *(done in 3A)* Restore reality pinned (futures→EQUITY, option lot=1, instrument_type).
2. *(done here)* Driver-level gate-ordering pinned at the call level — the hook slot is `driver.py:357`→`:360`, FRESH/WARN only, never BLOCK.
3. Introduce `_canonicalize_restored_ledger()` at the §1 insertion point, behind the MM.4 gating condition; no-op for paper/replay/equity. (One commit; adds the call, the method is initially a documented no-op satisfying the §4 `seq`-slot contract.)
4. **Either** canonicalize restored **orders** (#8) **or** restored **positions** (#7-as-restored) — **one independently-revertible commit each, in either order** (§3.6); in-place `.instrument` swap only (preserve `correlation_id`/`signal_id`/`symbol`/side/qty/order_type — H7/H8); do not touch `get_position`/#7 source (H5); do not wire `load_all`/#9 (H6). Flip the corresponding Wave-3A tripwire (futures EQUITY→FUTURE, option lot 1→65) per commit.
5. Re-run reconciliation last (unchanged engine); assert PASS on the canonicalized, symbol-preserved ledger (H3).
6. **KB sync** — name the latent interim order-vs-position inconsistency (§3.4); reconcile the `SOLE_IDENTITY_PATH_REVIEW.md` §5 wave-numbering caveat; update PROJECT_STATE/CHANGELOG.

**F4 dependency reminder:** the position/order option canonicalization makes restored option lots master-resolved (65) — the same F4-gated value as forward #4; exchange verification is a precondition for the restore option path going live.

---

## Validation

```
python -m pytest tests/runtime/test_driver_gate_ordering.py -q                                   → 5 passed
python -m pytest tests/runtime/test_driver_gate_ordering.py tests/runtime/test_driver_master_readiness.py tests/runtime/test_driver_startup_gate.py -q  → 23 passed
python -m pytest -q                                                                               → 393 passed
```

| Metric | Count |
|---|---|
| Passing (full suite) | **393** |
| Failing | **0** |
| New tests added | **5** (`tests/runtime/test_driver_gate_ordering.py`) |
| Production code changed | **0 files** |
| Baseline before Wave 3B | 388 passing |
