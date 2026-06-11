# MM.7 LIVE WIRING REVIEW

**Type:** Review — survey + wiring map only. **No code. No implementation.**
**Date:** 2026-06-11
**Question:** *What does the missing F&O runtime entry script have to construct and inject so that the MM.7 production master-readiness checker, the deferred `broker_positions` reconciliation, and the LoopDriver startup gate participate in a real live run?*
**Scope:** The single thing standing between a feature-complete deterministic runtime and live F&O participation is the **entry script** — `LoopDriver(...)` is constructed only in `tests/runtime/`. This review maps exactly what that script must wire, the shape mismatches it must bridge, the modes it makes F&O-capable, and the characterization net required before it is written.
**Discipline:** Identical review-first method that drove Gate G1 — survey with file/line evidence, classify, name preconditions, define the test net. The implementation is a *later* slice (Planned #4, F&O runtime).

**Governing inputs:** `core/runtime/driver.py` · `core/instruments/master_readiness.py` · `core/execution/reconciliation.py` · `core/execution/handler.py` · `core/runtime/config.py` · `core/runtime/instrument_scope.py` · `core/brokers/upstox_adapter.py` · `docs/PROJECT_STATE.md` (Planned #4/#6, Open Findings F3/F4) · `docs/reports/PHASE_4C_7_READINESS.md` · `docs/reports/PHASE_F_STARTUP_GATE_PLAN.md` · `docs/reports/G1_CLOSEOUT_REPORT.md`.

---

## 0. Verdict

**The F&O entry script does not exist, and it is the sole live call-site for three already-built mechanisms** (MM.7 checker, the Phase-F reconciliation gate, the G1 canonicalization passes). Every collaborator it must inject **exists and is tested in isolation**; what is unbuilt is the **composition root** that constructs them against real broker/data dependencies and hands them to `LoopDriver`.

Two **bridging gaps** and three **hard preconditions** sit between "all parts exist" and "a live F&O run is correct." None is an architecture defect — they are the seams the entry script is responsible for, deliberately deferred out of the MM scope (`PROJECT_STATE.md` Planned #4/#6).

**This review writes no code.** It is the map the F&O runtime slice will build against.

---

## 1. How `LoopDriver` is constructed

The DI surface is the full constructor (`core/runtime/driver.py:144-154`). The config object holds *settings*; every *collaborator* is injected, and "wiring those lives at the entry-script layer (`scripts/`), not [in `DriverConfig`]" (`core/runtime/config.py:9-13`).

| Param | Type | Required for live? | Who builds it (entry script) | Status today |
|---|---|---|---|---|
| `config` | `DriverConfig` | **Yes** | construct with `Mode.LIVE` + F&O `symbols` (`NSE_FO|...`) | exists |
| `clock` | `Clock` | **Yes** (`run()` raises without it, `:496-499`) | `RealTimeClock` for LIVE | exists |
| `provider` | `MarketDataProvider` | **Yes** | `LiveDuckDBMarketDataProvider(symbols, db_manager)` (`core/database/providers/live_market.py:20`) | exists |
| `journal` | `RuntimeEventJournal` | optional (no-op absent) | construct once | exists |
| `source` | `SignalSource` | **Yes in practice** (no source ⇒ no signals ⇒ no trades) | **DOES NOT EXIST** — see §6 finding **W1** | **gap** |
| `watchdog` | `RuntimeWatchdog` | recommended for live (ADR-004) | over the same handler | exists |
| `execution` | `ExecutionHandler` | **Yes** — `run()` raises in LIVE without it (`:505-506`) | see §1.1 | exists, not wired |
| `broker_positions` | `Callable[[], List[Dict]]` | needed for a *non-vacuous* reconcile gate | see §3 — **shape bridge W2** | **gap** |
| `telemetry` | `TelemetrySink` | optional (defaults to `NullTelemetrySink`, `:177`) | `InMemoryTelemetrySink` or null | exists |
| `publisher` | `RuntimeTelemetryPublisher` | optional | ZMQ publisher | exists |
| `master_readiness` | `Callable[[], ReadinessVerdict]` | **Yes for live F&O** (else gate is vacuous) | `build_master_readiness(...)` — see §2 | exists, not wired |

### 1.1 The `ExecutionHandler` the script must build

`ExecutionHandler.__init__` (`handler.py:118-188`) needs `db_manager`, `clock`, `broker` (`BrokerAdapter`), and **`load_db_state=True`** (the default). Three facts the entry script depends on:

- **Recovery is the handler's, run at construction.** `load_db_state=True` ⇒ `_replay_state()` runs in `__init__` (`handler.py:186-187`). The driver **reuses** this and never re-restores (ADR-001) — `_run_startup_gate` only emits `RECOVERY_STARTED`/`RECOVERY_COMPLETED` around the already-done work (`driver.py:346-352`). So the entry script must construct the handler with `load_db_state=True` **before** handing it to the driver; the driver assumes a restored ledger.
- **Reconciliation lives on the handler.** `self.reconciliation = ReconciliationEngine(self.position_tracker)` (`handler.py:158`). The driver calls `self._execution.reconciliation.reconcile(self._broker_positions())` (`driver.py:464`) — so the broker book is compared against the **handler's** restored tracker.
- **`ExecutionMode` ≠ `Mode`.** The handler carries its own `ExecutionMode` (`DRY_RUN`/`PAPER`/`LIVE`, `handler.py:59-63`) inside `ExecutionConfig`, independent of `DriverConfig.Mode` (`LIVE`/`REPLAY`). The entry script sets **both**, and they are orthogonal — see §4.

---

## 2. How `build_master_readiness(...)` is injected

The production factory **already exists**: `core/instruments/master_readiness.py:88-104`.

```
build_master_readiness(underlyings, *, db_path=None, as_of=None) -> Callable[[], ReadinessVerdict]
```

It constructs the real `InstrumentResolver` once and returns the zero-arg `() -> assess(resolver, underlyings)` callable — the live replacement for the test-injected verdict lambda. It is **evaluation only**; it never downloads/refreshes/repairs the master (Decision 6). It was proven end-to-end FRESH through the gate (`tests/runtime/test_driver_master_readiness.py`), but **its only caller is that test** — `PROJECT_STATE.md` records blocker #4 as **"BUILT, not yet wired."**

**Injection contract for the entry script:**

```
driver = LoopDriver(
    config=DriverConfig(mode=Mode.LIVE, symbols=[...NSE_FO keys...]),
    ...,
    master_readiness=build_master_readiness(["NIFTY", "BANKNIFTY"], db_path=<master db>),
)
```

Two non-obvious wiring constraints:

- **`underlyings` is explicit, NOT derived from `config.symbols`.** The symbols are broker keys (`NSE_FO|54710`); deriving an underlying from one would itself require resolving the master — bootstrap-fragile (`master_readiness.py:88` docstring; MM.7 reasoning). The entry script passes the traded underlyings *by name*.
- **The gate only fires on the live derivative path.** `_check_master_readiness` is a no-op unless `is_live ∧ has_derivatives(symbols) ∧ master_readiness is not None` (`driver.py:383-386`). `has_derivatives` keys on the `NSE_FO`/`MCX_FO` segment prefix (`instrument_scope.py:16-21`). So: **equity-only LIVE, paper, and replay never invoke the checker even when injected** — and a **live F&O run with the checker absent is a vacuous pass** (mirroring deferred reconciliation). The entry script *must* inject it for the gate to have teeth, and the G1 canonicalization passes (`_canonicalize_restored_ledger`, `driver.py:439-444`) gate on the *same* condition — so **without this callable, the restored ledger is never canonicalized either.**

---

## 3. How `broker_positions` reconciliation is wired

The driver consumes a `broker_positions` callable and feeds its result to the reconciliation engine (`driver.py:446-477`). It is **vacuously clear** today: gated on `require_reconciliation_on_start ∧ self._broker_positions is not None` (`driver.py:462-463`), and the callable is injected only in tests (`PROJECT_STATE.md` Planned #6: "LIVE reconciliation is structurally present but vacuous until this lands").

### 3.1 Bridging gap **W2 — shape mismatch (must be adapted, cannot be passed through)**

The two ends do not have the same type:

- **Driver/engine expect** `Callable[[], List[Dict[str, Any]]]` where each dict is `{'symbol': str, 'quantity': float, 'side': str}` and `side` is a **string** `'LONG'`/`'SHORT'` upper-cased (`reconciliation.py:24,46-52`).
- **The broker adapter returns** `Dict[str, Position]` keyed by symbol, with `quantity` already `abs()`'d and `side` a **`PositionSide` enum** (`upstox_adapter.py:126-152`).

So the entry script (or Planned #6) **cannot inject `broker.get_positions` directly** — it must wrap it into an adapter that:
1. takes `.values()` of the dict → a list;
2. emits `side` as `pos.side.value`/`.name` (a string), not the enum object — otherwise `reconciliation.py:47` (`bp.get('side','').upper()`) silently fails to normalize and the signed-quantity comparison is wrong;
3. preserves the sign convention reconciliation relies on (it re-signs from `side`, `reconciliation.py:48-51`).

This adapter is **the deliverable of Planned #6**, not the entry script proper — but the entry script is its sole consumer, so the review names it here. `UpstoxMapping.from_broker_position` (4C.8) is the intended canonical-keyed version; the interim string-keyed reconcile (`reconciliation.py:57-85`) keys on the raw symbol.

### 3.2 Hazard **W3 — `broker_positions()` failure escapes `run()` uncaught**

`PROJECT_STATE.md` Planned #6 already records this and it is confirmed in the code: `_run_startup_gate` (hence `self._broker_positions()`, `driver.py:464`) runs **before** `run()`'s `try/finally` (`driver.py:524-549`). A broker auth/transport exception from the callable therefore **propagates uncaught out of `run()`, leaving the driver in `RECOVERY` with no `STOPPED` and no journal record.** Planned #6 must convert this into a startup refusal → journal event → `STOPPED` (same contract as `RECONCILIATION_FAIL`). The entry script must not paper over this with its own try/except — the refusal belongs inside the gate.

---

## 4. Which runtime modes become F&O-capable

There are **two orthogonal mode concepts**, and "F&O-capable" is the *intersection* of three switches:

1. **`DriverConfig.Mode`** — `LIVE` vs `REPLAY` (`config.py:24-34`). Gates the clock (RealTime vs Replay) and the watchdog (live-only, `driver.py:759`).
2. **`ExecutionHandler.ExecutionMode`** — `DRY_RUN` / `PAPER` / `LIVE` (`handler.py:59-63`). Gates whether orders actually hit the broker.
3. **`has_derivatives(symbols)`** — the F&O scope switch (`instrument_scope.py`). Gates the master-readiness gate **and** the G1 canonicalization passes.

| Driver `Mode` | Handler `ExecutionMode` | `has_derivatives`? | What runs | F&O-capable? |
|---|---|---|---|---|
| REPLAY | PAPER/DRY_RUN | yes | replay clock, no watchdog, **master gate skipped** (`is_live` false), no canonicalization | Backtest only — not a "live" path |
| LIVE | PAPER | **yes** | RealTime clock, watchdog, **master gate active**, **canonicalization active**, reconcile vacuous (no `broker_positions`), no real orders | **Yes — the first safe F&O target** (paper fills, full gate) |
| LIVE | LIVE | **yes** | all of the above + real broker orders + non-vacuous reconcile (once #6 lands) | **Yes — true live F&O**, blocked on Planned #4/#5 + F4 |
| LIVE | PAPER/LIVE | no (equity only) | gate + canonicalization **skipped** by design | Not F&O (equity path unchanged) |

**Conclusion:** the F&O-capable path is **`Mode.LIVE` + `has_derivatives` symbols + a `master_readiness` checker injected.** The handler's `ExecutionMode` then chooses paper-vs-real fills. The natural first deployment is **`Mode.LIVE` / `ExecutionMode.PAPER`** — it exercises the *entire* startup gate, watchdog, canonicalization, and (with the #6 adapter) reconciliation against the real broker book, while no capital moves. That is the rung the entry script should target first.

---

## 5. Live-enablement preconditions the entry script inherits (not its to fix, but it must not start without them)

These are tracked elsewhere; the entry script is where they become *active*, so they are restated as start-blockers:

- **P1 — F4 lot verification (hard).** Once the entry script exists, the live option path sizes with the **unverified NIFTY lot=65 / BANKNIFTY=30** the materialized master resolves (`PROJECT_STATE.md` F4; `selector.py:108-113`). "The instant the F&O entry script exists, the live option path sizes with the unverified 65." **Verify 65/30 against exchange circulars before any `ExecutionMode.LIVE` F&O run.**
- **P2 — F3 tick-size disposition (defect, currently inert).** `CanonicalInstrument.tick_size` is stored ~100× too large (paise not rupees, `PROJECT_STATE.md` F3). No live consumer today, but it becomes execution-affecting the moment 4C.7 wires canonical attributes into order pricing/rounding. Disposition must be **known** before 4C.7; not a blocker for the *entry script* itself (which doesn't price off tick yet), but on the same critical path.
- **P3 — Planned #4 / #5 (F&O product model + SPAN margin).** Live *derivatives trading* is formally blocked on the F&O product/segment model (hardcoded intraday `product:"I"`) and the margin engine (`PROJECT_STATE.md` Blocked). The entry script can run **`Mode.LIVE`/`ExecutionMode.PAPER`** ahead of these, but **`ExecutionMode.LIVE` F&O is blocked until #4/#5 land.**

---

## 6. New findings surfaced by this review

- **W1 — No production `SignalSource` exists.** Every `SignalSource` subclass is a test double (`tests/runtime/_doubles.py:113`, `tests/runtime/test_signal_source.py`); there is **no production class that adapts an F&O strategy into the `on_bar → List[SignalEvent]` seam.** The entry script needs one, and it does not exist yet. This is a peer of "the entry script doesn't exist" — the script has **nothing to inject as `source`** today. Building the F&O `SignalSource` is part of the Planned #4 slice and should be named explicitly (it was implicit under "order routing").
- **W2 — broker-positions shape bridge** (§3.1) — `Dict[str, Position]` → `List[Dict]` with string `side`. Owned by Planned #6; consumed by the entry script.
- **W3 — `broker_positions()` failure escapes `run()`** (§3.2) — already in Planned #6; restated with code evidence.
- **W4 — the master-readiness checker is load-bearing for *canonicalization*, not just the gate.** Because `_canonicalize_restored_ledger` shares the `master_readiness is not None` gate (`driver.py:439-444`), **omitting the checker silently disables the entire G1 restore-canonicalization** the program just closed — the restored ledger stays legacy-typed. The entry script injecting the checker is what *activates* G1's restore half on the live path; this coupling must be explicit in the script and its tests.

---

## 7. Characterization tests required (before the entry script is written)

Following the G1 discipline — pin reality first, then build. These are **new test files**, not implementation:

1. **`tests/scripts/test_fno_entry_wiring.py` (composition characterization).** Assert the entry script (once it exists) constructs a `LoopDriver` whose injected collaborators satisfy the live-F&O contract: `Mode.LIVE`, `has_derivatives(config.symbols)` true, `master_readiness` not None, `execution` not None, `source` not None. This is the guard that the script *is* F&O-capable per §4. (Red until the script exists — it is the script's acceptance test.)
2. **`tests/execution/test_broker_positions_adapter.py` (W2 bridge).** Pin that the #6 adapter turns `UpstoxAdapter.get_positions()`'s `Dict[str, Position]` into the `List[Dict]` reconciliation consumes, with `side` a string and signs preserved; feed it a LONG, a SHORT, and a FLAT and assert `reconcile()` produces **no false QUANTITY_MISMATCH/ORPHANED alert** against a matching restored tracker. (This is the test that proves §3.1 is bridged correctly.)
3. **`tests/runtime/test_driver_broker_positions_failure.py` (W3 hazard).** Pin **current** behavior (a raising `broker_positions` escapes `run()` with the driver left in `RECOVERY`, no `STOPPED`, no journal) as a RED-documenting characterization, so Planned #6's fix flips it to refusal→`STOPPED`→journal. (G1 Wave-3A method: encode the defect before fixing it.)
4. **`tests/runtime/test_driver_canonicalization_requires_checker.py` (W4 coupling).** Assert that on a LIVE+derivative run **without** a `master_readiness` checker, `_canonicalize_restored_ledger` is a no-op (restored ledger stays legacy), and **with** the real `build_master_readiness` checker it canonicalizes — pinning that the checker is the activation switch for G1's restore half, not just the gate.
5. **F4 verification harness (P1).** A one-shot check (not a unit test) that asserts the materialized master's NIFTY/BANKNIFTY lot sizes equal the exchange-circular values, run as a **start precondition** before `ExecutionMode.LIVE`. Until it passes, the live option path must refuse.

Tests 1–4 are unit-level and mergeable independently; test 5 is an operational gate. None requires the entry script to exist first except #1 (its acceptance test).

---

## 8. Recommended program framing

This review confirms the assessment that the **Identity Architecture Program (Gate G1) is COMPLETE** and the critical path has shifted. The next program is **Live F&O Enablement**, and MM.7 wiring is its first phase. Suggested ordering, each a separate slice:

1. **MM.7 wiring / F&O entry script (Planned #4 core)** — the composition root: construct handler (`load_db_state=True`) + provider + clock + `build_master_readiness(...)` + the F&O `SignalSource` (W1), target `Mode.LIVE`/`ExecutionMode.PAPER` first. Tests 1 + 4 above.
2. **Broker-side reconciliation (Planned #6)** — the W2 adapter + the W3 refusal contract. Tests 2 + 3.
3. **F4 verification + F3 disposition** — P1/P2; gates `ExecutionMode.LIVE`.
4. **F&O product/segment model + margin (Planned #4/#5)** — unblocks true live derivatives.
5. **4C.7 broker payload** — ships resolved `instrument_key`/product to the live adapter (stays blocked until 1–4).

**No code was written or changed by this review.**

---

*Filed under the G1 review-first discipline. Companion to `SOLE_IDENTITY_PATH_REVIEW.md`, `PHASE_4C_7_READINESS.md`, and `PHASE_F_STARTUP_GATE_PLAN.md`.*
