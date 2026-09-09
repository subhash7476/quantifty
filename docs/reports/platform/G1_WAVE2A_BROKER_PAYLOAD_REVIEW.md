# G1_WAVE2A_BROKER_PAYLOAD_REVIEW.md

**Type:** Gate G1 — Wave 2A. **Broker Payload Truth review + characterization-suite basis.** Resolves the open caveat in `G1_WAVE1_REPORT.md` Section 3. **No identity-site migration; no canonical changes; no order-path behavior change.**
**Date:** 2026-06-09
**Question (from Wave 1 §3):** `UpstoxAdapter.place_order` reads `order.price` / `order.signal_id_reference`, neither of which exists on `NormalizedOrder` — yet `handler.py:563` passes a `NormalizedOrder` to `broker.place_order`. Is Upstox the live path? Is there a conversion layer? Or is the Upstox path broken/unexercised?
**Basis (file:line, verified 2026-06-09):** `handler.py`, `brokers/{upstox_adapter,paper_broker,broker_base,base}.py`, `events.py`, `order_models.py`, full `tests/` tree.

---

## 0 — Dispositive finding (answers all three questions at once)

**No production code constructs a real `ExecutionHandler` with any broker.** Repo-wide, `ExecutionHandler(` resolves to exactly one definition (`handler.py:112`) and **zero** instantiations outside tests; every runtime/driver test injects `FakeExecutionHandler` (`tests/runtime/_doubles.py`). The runtime driver takes an `execution=` handler by injection but **nothing in `core/`, `scripts/`, `flask_app/`, or `app_facade/` builds one and feeds it a broker.**

Therefore: **there is no wired live execution path today.** "Is Upstox the live broker?" is moot — *no broker is wired into a real handler anywhere.* The ABC split and the `NormalizedOrder` AttributeError below are corroborating detail, not the thesis.

**Consequence for the suite (stated honestly):** the characterization suite does **not** pin a production-wired live path (none exists). It pins the **handler order-build / persist / restore code against the `PaperBroker` + `NormalizedOrder` contract** — the only broker that accepts what the handler actually emits, and the contract Wave 2 (#1/#2/#4) must preserve byte-for-byte. In the user's phrasing "the actual live broker contract," *live = exercisable*, and the only exercisable broker contract is **PaperBroker**, not Upstox.

---

## 1 — Q1: Is `UpstoxAdapter` the live broker path? — **No.**

| Evidence | file:line | Finding |
|---|---|---|
| `ExecutionHandler` instantiations repo-wide | `handler.py:112` (def only) | No production construction; tests use `FakeExecutionHandler` only. |
| `UpstoxAdapter` instantiations repo-wide | `tests/execution/test_reconciliation_broker.py:35`, `tests/brokers/test_upstox_positions.py:24,74` | Built **only in two tests**, both exercising `get_positions()` — **never `place_order()`**. |
| `UpstoxAdapter.place_order` invocations | — | **Zero, repo-wide.** The method is never called by anything. |

Upstox is neither wired into a handler nor invoked. It is dead with respect to order placement.

---

## 2 — Q2: Is there a conversion layer between `ExecutionHandler` and `UpstoxAdapter`? — **No.**

- The handler passes the **raw `NormalizedOrder`** to the broker: `broker_id = self.broker.place_order(order)` (`handler.py:563`) and `self.broker.place_order(order)` (`handler.py:673`). No `NormalizedOrder → OrderEvent` adapter sits between them.
- The one `signal_id_reference=` assignment in the handler (`handler.py:296`) builds a **`TradeEvent` for journaling on fill** (`handler.py:294-304`), not a broker order. It is unrelated to `place_order`.
- The two classes are not even on the same interface: the handler's broker type is `broker_base.BrokerAdapter` (`handler.py:47`), whose contract is **`place_order(order: NormalizedOrder)`** (`broker_base.py:16`). `UpstoxAdapter` extends a **different** ABC, `base.BrokerAdapter` (`upstox_adapter.py:11` → `core/brokers/base.py`), whose contract is **`place_order(order: OrderEvent)`** (`upstox_adapter.py:79`). (Two divergent `BrokerAdapter` ABCs — consistent with `FNO_PRODUCT_DISCOVERY.md` §6.)

There is no conversion layer because the two halves were never connected.

---

## 3 — Q3: Is the Upstox path broken/unexercised? — **Both.**

**Unexercised:** `place_order` is never called (Section 1).

**Broken against the handler's actual output type.** If a `NormalizedOrder` were handed to `UpstoxAdapter.place_order`, the payload build (`upstox_adapter.py:80-92`) fails:

| Payload key | Code | Outcome on a `NormalizedOrder` |
|---|---|---|
| `tag` | `order.signal_id_reference` (`:85`) | **AttributeError** — `NormalizedOrder` has `signal_id` (`order_models.py:33`), **no** `signal_id_reference`. Crashes here first. |
| `price` | `order.price if order.order_type.value == "LIMIT" else 0` (`:84`) | Latent only — short-circuits to `0` because `NormalizedOrder.order_type` is always `MARKET` (`OrderType` enum has only `MARKET`). `order.price` never evaluated, so the missing attribute is masked. |
| `transaction_type` | `"BUY" if order.side == "BUY" else "SELL"` (`:88`) | **Always `SELL`** — `NormalizedOrder.side` is an `OrderSide` enum (`order_models.py:29`), never the string `"BUY"`; enum-vs-str compare is always `False`. (Unreached today; behind the AttributeError.) |
| `instrument_token` | `order.symbol` (`:86`) | Works — `order.symbol` exists (`order_models.py:84`). |

**Findings (NOT fixed this wave — recorded per scope):**
- **F-UPX-1:** `UpstoxAdapter.place_order` is incompatible with `NormalizedOrder` (AttributeError on `signal_id_reference`).
- **F-UPX-2:** Even past F-UPX-1, `order.side == "BUY"` (enum vs str) makes **every Upstox order `SELL`**.
- **F-UPX-3:** Two divergent `BrokerAdapter` ABCs (`broker_base.py` vs `base.py`); handler and Upstox are on different ones.

These are the order-placement counterpart to the reconciliation/positions mismatches already logged in `FNO_PRODUCT_DISCOVERY.md` §6 / `CANONICAL_INSTRUMENT_ARCHITECTURE.md`. They are pre-existing; G1 does not touch them.

---

## 4 — The live, exercisable broker contract (what the suite pins)

`PaperBroker` is the only broker that accepts the handler's output:

- `PaperBroker(base.BrokerAdapter).place_order(order: Union[OrderEvent, NormalizedOrder])` (`paper_broker.py:26`) explicitly handles `NormalizedOrder` (`paper_broker.py:31-35`), reading **`order.symbol`**, **`order.side.value`**, **`order.quantity`** (price is `"MARKET"` — `NormalizedOrder` has no price).
- The handler special-cases it: `isinstance(self.broker, PaperBroker)` → simulate immediate fill (`handler.py:568-569`), routing a `FillEvent` through `_handle_broker_fill`.

**Broker-payload identity invariant (the field that would hit any real wire):** `order.symbol` (= `NormalizedOrder.instrument.symbol`, the display symbol). This is what `PaperBroker` reads (`paper_broker.py:32`), what `UpstoxAdapter` *would* map to `instrument_token` (`upstox_adapter.py:86`), and what `mock_broker_adapter` reads. The Wave 2 migration of #1/#2/#4 must keep `order.symbol`, `order.side`, `order.quantity`, `order.order_type` byte-identical against the `PaperBroker` contract — and `product` stays out of `NormalizedOrder` entirely (Upstox hardcodes `"I"`; the G1/4C.7 boundary).

---

## 5 — Characterization suite basis

The suite (`tests/execution/test_g1_characterization.py`, **7 tests, all green**) constructs a **real `ExecutionHandler`** wired with a **spy `PaperBroker`**, over an **isolated tmp `ExecutionStore`** and `DatabaseManager(data_root=tmp)`, and pins the four Section-4 golden paths against the PaperBroker + NormalizedOrder contract established above. Isolation is mandatory: `ExecutionStore()` defaults to the real `data/execution.db` (`execution_store.py:11`) and the handler builds it internally (`handler.py:145`), so tests monkeypatch `core.execution.handler.ExecutionStore` (bound name, `handler.py:41`) to a tmp path and a guard test asserts the real ledger is never created/written.

**Test map (1:1 with Section 4):**
| Section 4 | Test |
|---|---|
| 1. Build order (option + futures + equity) | `test_build_order_equity_non_option_branch` (equity carve-out), `test_build_order_futures_currently_falls_back_to_equity` (**#1 migration target**), `test_build_order_option_via_selector_branch` (**#4** selector branch) |
| 2. Persist | `test_persist_order_and_fill_rows` |
| 3. Restore (round-trip) | `test_restore_round_trip` |
| 4. Reconcile | `test_reconcile_restored_ledger_against_broker` (PASS + QUANTITY_MISMATCH) |
| isolation guard | `test_real_execution_db_untouched` |

**Observed pinned values (characterization = current reality, not idealized; hardcoded literals, not re-derived from the code under test):**
- Equity (`RELIANCE`): `symbol == "RELIANCE"`, `instrument_type == EQUITY`, side `BUY`, qty 50 (explicit `metadata["quantity"]` bypasses the confidence-weighted sizing formula), `order_type MARKET`.
- **Futures mistype (the #1 tripwire, new finding F-PARSE-1).** A futures-style symbol (`NIFTY26JUNFUT`) through the non-option branch is currently built as an **`Equity`**, *not* a `Future` — `InstrumentParser.parse` (`instrument_parser.py:8-46`) has only an Option regex + Equity fallback, **no Future branch** (despite `core/instruments/future.py` existing). So today `order.instrument_type == EQUITY` for futures, with `symbol` preserved verbatim. This contradicts the plan's wording that #1 "builds `Option`/`Future`/`Equity` via parse" (`SOLE_IDENTITY_PATH_REVIEW.md` #1): parse **never** yields a `Future`. The test pins this defective reality; Wave 2 #1 (`resolve_future → canonical → derive Future`) is precisely what flips the type to `FUTURE` while keeping `symbol` byte-identical — at which point the test's `EQUITY` assertion is the intended red flag to update, and the `symbol` assertion must stay green.
- **Option (master-resolved, observed):** for underlying `NSE_INDEX|Nifty 50` @ 22500 on 2026-06-09: `symbol == "NIFTY16JUN2622500CE"` (pure date/strike math, master-independent) and **`lot_size == 65`**. The lot is what `resolve_option` returned against the instrument master present on disk in this environment — i.e. an **observed master-resolved value of 65**, *not* an exchange-verification of F4 (lot `75→65`), which the plan tracks as a **separate open precondition** (`SOLE_IDENTITY_PATH_REVIEW.md` Wave-2 F4 gate). If the master is absent elsewhere, the selector falls back to `INDEX_LOT_SIZES` (75) and this assertion goes red — a meaningful divergence, not a flake. Wave 2 #4 must preserve these exact bytes.

**Status:** Truth resolved. Suite written and **green (7/7, `python -m pytest tests/execution/test_g1_characterization.py` → 7 passed)**. No migration, no canonical change, no order-path code change, no commits. Stopping for review.
