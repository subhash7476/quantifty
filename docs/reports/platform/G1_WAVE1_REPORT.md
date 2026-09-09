# G1_WAVE1_REPORT.md

**Type:** Gate G1 — **Wave 1 execution report (prove-dead caller audit). Survey + verdicts only; NO order-path code written this turn.**
**Date:** 2026-06-09
**Parent plan:** `SOLE_IDENTITY_PATH_REVIEW.md` (Section 5, Wave 1).
**Wave 1 scope (locked):** Caller audit of `OrderFactory` (#5) and `NormalizedOrder(symbol=)` (#10); dead/carve-out verdicts; document #3 carve-out. **No live-path behavior change.**
**Basis (file:line, verified 2026-06-09):** `order_factory.py`, `order_models.py`, `handler.py`, `persistence/order_repository.py`, `brokers/{upstox_adapter,paper_broker,mock_broker_adapter}.py`, full `tests/` tree.
**Outcome:** Both audited sites are **DEAD** (prod + tests). Neither is pulled into Wave 2. Removal is deferred to a tracked cleanup (out of this report's scope).

---

## 1 — Reachability Analysis: #5 and #10

### #5 — `OrderFactory.create_order` (`order_factory.py:27,34`)

**Verdict: DEAD — zero call sites repo-wide, in production and tests.**

| Evidence | Finding |
|---|---|
| Only import of `OrderFactory` in the execution layer | `handler.py:29` — **commented out**: `# from core.execution.order_factory import OrderFactory # Replaced by internal logic for Phase 9A` |
| Repo-wide grep `create_order` | Matches only the **definition** at `order_factory.py:27` + doc references. **No `.create_order(` invocation anywhere** (core, scripts, flask_app, app_facade). |
| Repo-wide grep `OrderFactory` | Matches only its own class body (`order_factory.py:15,20`) + docs. No instantiation, no import that is not commented out. |
| Test tree (`tests/`) | **No** reference to `OrderFactory` or `create_order`. |

**Mechanism today:** The handler builds orders inline (`handler.py:536`, `:643`) via `NormalizedOrder(instrument=...)`, bypassing the factory entirely since "Phase 9A." The factory's `InstrumentParser.parse` at `order_factory.py:34` is therefore **unreachable** — it cannot construct a live identity because nothing constructs an `OrderFactory`.

**Classification confirmed:** `CARVE-OUT (prove-dead)` → **proven dead.** Not MIGRATE. Not Wave 2.

---

### #10 — `NormalizedOrder(symbol=…)` fallback branch (`order_models.py:43-44, 62-70`)

**Verdict: DEAD branch on a LIVE constructor.** The `symbol=`/`instrument_type=` keyword path and its fallback body are never exercised; the `instrument=` path is heavily live.

Every `NormalizedOrder(` construction site, repo-wide, passes `instrument=` (never `symbol=`):

| Site | Line | Arg used | Status |
|---|---|---|---|
| handler `process_signal` | `handler.py:536` | `instrument=instrument` | **LIVE** |
| handler `process_group_signal` | `handler.py:643` | `instrument=instrument` | **LIVE** |
| order restore (replay) | `order_repository.py:62` | `instrument=instrument` | **LIVE** (restore) |
| `OrderFactory.create_order` | `order_factory.py:67` | `instrument=instrument` | dead (see #5) |
| Test tree (`tests/`) | — | **no `NormalizedOrder(symbol=...)` anywhere** | — |

**The dead code, precisely:** `order_models.py:43-44` (the `symbol` / `instrument_type` keyword params) and `:62-70` (the `if resolved_instrument is None:` fallback body). Because no caller omits `instrument`, the `None` branch is **never taken**.

**Latent always-Equity defect (`order_models.py:66-70`):** both arms of the fallback construct `Equity(resolved_symbol)` — even when `instrument_type == OPTION/FUTURE`. If a caller ever used `symbol=` with a non-equity type, the order would be **mistyped as Equity**. Today this is harmless *only because the branch is unreached.* It is a tripwire for any future caller and must not be silently folded — fix-or-delete in the cleanup, tracked here.

**Classification confirmed:** `CARVE-OUT (prove-dead)` → **proven dead branch.** Not Wave 2. The live `instrument=` constructor stays.

---

## 2 — Characterization Test Inventory (Section 4 net)

**Claim (verified by full, un-truncated `tests/` grep): none of the four Section 4 golden-path characterization tests exist today.** The live order-build/persist/restore/reconcile path is unpinned, exactly as the plan asserts.

| Section 4 test | Required behavior pinned | Exists? | Closest existing coverage (and why it does NOT count) |
|---|---|---|---|
| **1. Build order** | Real `ExecutionHandler.process_signal` (option + futures) → assert `NormalizedOrder` (symbol, lot/qty, side, type) byte-for-byte | **NO** | All `process_signal` tests use `FakeExecutionHandler` (`tests/runtime/_doubles.py:258`); the real handler is never constructed. Driver tests (`test_driver_execution_routing.py`, `test_driver_watchdog.py`) only assert *that* `process_signal` is routed, via AST — never the payload. |
| **2. Persist** | Order + position rows written to the SQLite ledger → assert persisted fields | **NO** | No test references `OrderRepository` / `PositionRepository` / `.save(`. |
| **3. Restore** | Handler with `load_db_state=True` → assert restored orders/positions = persisted (round-trip) | **NO** | No test references `load_db_state`, `_replay_state` (real), or `get_all()`. The `_replay_state` spy in `_doubles.py:218` only records *that* it was called. |
| **4. Reconcile** | Restored ledger vs broker-position fixture → assert reconciliation verdict | **PARTIAL — does not count** | `tests/execution/test_reconciliation_broker.py` exercises `ReconciliationEngine.reconcile()` **in isolation** with hand-built test glue (`_broker_positions_as_dicts`), not over a restored handler ledger. Pins the engine contract, not the live path. |

**Consequence:** The regression net Section 4 requires as a **precondition to any migration wave does not yet exist.** Building it is the first task of Wave 2 (see Section 5), and each of the four tests must assert the broker-facing payload explicitly (the G1/4C.7 tripwire, Section 3 below).

---

## 3 — Broker-Payload Invariants (the G1/4C.7 boundary)

G1 must keep the broker payload **byte-for-byte unchanged**. Stated broker-agnostically, the identity-bearing field every adapter reads is **`order.symbol`** (= `NormalizedOrder.instrument.symbol`, the *display* symbol — `order_models.py:84-85`). After migration, the legacy object *derived* from `CanonicalInstrument` must reproduce the identical `.symbol`.

**Invariants that must hold across all three adapters read (`upstox_adapter`, `paper_broker`, `mock_broker_adapter`):**

| # | Invariant | Source of truth |
|---|---|---|
| I1 | **`order.symbol` byte-identical** before/after migration | read by all three adapters (`upstox_adapter.py:86` → `instrument_token`; `paper_broker.py:32,37`; `mock_broker_adapter.py:32`) |
| I2 | **`order.side`** unchanged (`BUY`/`SELL`) | `upstox_adapter.py:88`, `paper_broker.py:33,38`, `mock_broker_adapter.py:36` |
| I3 | **`order.quantity`** unchanged (the F4 lot value flows through here — pin current behavior, whatever F4 verification later decides) | `upstox_adapter.py:81`, `paper_broker.py:34,39`, `mock_broker_adapter.py:33` |
| I4 | **`order.order_type`** unchanged (`MARKET`) | `upstox_adapter.py:84,87` |
| I5 | **`product` stays hardcoded `"I"` (INTRADAY); payload never reads `ci.instrument_key` / `ci.product`** | `upstox_adapter.py:82` — **this is the load-bearing G1/4C.7 line.** The moment the payload *uses* canonical `instrument_key`/`product`, it is 4C.7, not G1. |
| I6 | Derived `instrument_type` **value** unchanged (`EQUITY`/`OPTION`/`FUTURE`) — consumed by persistence (`order_models.py:88,94`) and greeks asset-class dispatch, not by the wire, but still a payload-equivalence surface | `order_models.py:87-89` |

**Open caveat (new finding — register, do not block):** `upstox_adapter.place_order(self, order: OrderEvent)` (`upstox_adapter.py:79`) reads **`order.price`** (`:84`) and **`order.signal_id_reference`** (`:85`) — **neither attribute exists on `NormalizedOrder`** (it has `signal_id`, no `price`). Yet `handler.py:563` passes a `NormalizedOrder` to `self.broker.place_order(order)`. So one of: (a) Upstox is not the exercised live broker in this build (paper/mock is), (b) an unseen conversion sits between handler and adapter, or (c) the live Upstox path is latently broken. **Do not present the Upstox payload as "the live payload"** until this is resolved. The invariants above are anchored on `order.symbol`, which holds across all three adapters regardless. Resolving this typing mismatch is a Wave-2 precondition input (it determines which adapter the characterization tests must assert against).

---

## 4 — Dead-Code Verdicts

| Site | Verdict | Action (deferred — NOT this turn) | Wave 2? |
|---|---|---|---|
| **#5** `OrderFactory` (whole class, `order_factory.py`) | **DEAD** — no caller in prod or tests; only import is commented out | Remove the class + module in a tracked cleanup commit (revertible, no live behavior change) | **No** |
| **#10** `NormalizedOrder(symbol=…)` branch (`order_models.py:43-44, 62-70`) | **DEAD branch** on a live constructor | Remove the `symbol`/`instrument_type` kwargs + the `None` fallback body. This **also eliminates the always-Equity defect** (`:66-70`). Live `instrument=` path untouched | **No** |
| **#3** `handler._check_greek_limits` (`handler.py:720`) | **CARVE-OUT (documented)** — not dead, but out of sole-source scope | None. Justification below. | **No** |

**#3 carve-out justification (required Wave 1 deliverable):** `handler.py:720` calls `InstrumentParser.parse(signal.symbol)` to build a **transient** instrument fed only to `GreeksCalculator.calculate` (`handler.py:727`). The identity **never leaves the site** — it is not persisted, not sent to the broker, not stored on any position/order. `GreeksCalculator` is `asset_class`-dispatched (4C.6) and correct on legacy types. Therefore **no canonical construction is needed**; #3 stays legacy by explicit decision. This is a documented carve-out, not a gap.

**Why neither #5 nor #10 goes to Wave 2:** Wave 2's "or else MIGRATE" clause fires only if the audit finds a *live* caller. It found none. Dead code is removed in cleanup, not migrated to canonical — migrating a path nothing reaches would be wasted surface.

---

## 5 — Recommended Wave 2 Scope

**Precondition (load-bearing — do this FIRST, before any site migration):** Build the **Section 4 characterization net**, which currently **does not exist** (Section 2 above). No migration wave may merge until all four are green. Specifically:

1. Construct a **real** `ExecutionHandler` in a test, drive `process_signal` with an option and a futures signal, assert the resulting `NormalizedOrder` (symbol, qty/lot, side, type) — pinning invariants **I1–I4, I6**.
2. Persist order+position to a temp SQLite ledger; assert rows.
3. Construct a handler with `load_db_state=True` over that ledger; assert the restore round-trip.
4. Reconcile the restored ledger vs a broker-position fixture; assert the verdict — **over the restored handler**, not the engine in isolation.
   Each test asserts the broker-facing payload explicitly (I1–I6) so a payload-byte change trips the G1/4C.7 boundary.

**Then — Wave 2 site migration (`SOLE_IDENTITY_PATH_REVIEW.md` Wave 2):**

| Site | Action |
|---|---|
| **#1** `handler.py:513` (futures) | `resolve_future` → `CanonicalInstrument` → derive legacy `Future`. Same broker payload (I1–I6). Equity arm stays carve-out (ISIN-less, out of F&O scope). |
| **#2** `handler.py:621` (batch, futures) | Mirror of #1 on the group path. |
| **#4** `selector.py` option path | Have `select()` resolve a `CanonicalInstrument` and derive the legacy `Option`; `lot_size` already resolver-sourced. **Gated: F4 (lot 65/30) must be exchange-verified before this path goes LIVE** (verification tracked separately; characterization test pins *current* F4 lot as behavior regardless). |

**Explicitly NOT in Wave 2:** #5, #10 (dead — cleanup, not migration); #3, #11, equity, paper/replay (carve-outs); #6/#7 (Wave 3); #8/#9 restore (Wave 4, Option B post-gate upgrade).

**Resolve before Wave 2 coding:** the Upstox `OrderEvent`-vs-`NormalizedOrder` attribute mismatch (Section 3 caveat) — it determines which adapter the characterization tests assert against.

---

## Status & next step

**Wave 1 COMPLETE (report only — no order-path code written).** #5 and #10 proven dead; #3 carve-out documented; broker invariants I1–I6 fixed; characterization net confirmed absent; Wave 2 scope recommended (net-first, then #1/#2/#4 with #4 F4-gated). **G1 remains OPEN ("Yes — legacy construction remains").** Awaiting review before authorizing Wave 2. Wave 2 is **not** authorized by this report.
