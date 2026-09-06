# MM7E — Composition Root Implementation Report (Design B)

**Type:** Implementation — the first production composition root (`scripts/fno_runner.py`) that constructs the live `LoopDriver`, accepting the `SignalSource` by dependency injection. **No production `SignalSource`, no strategy, no alpha, no broker adapter, no F4/#4/#5 work.**
**Date:** 2026-06-12
**Basis:** `MM7E_ENTRY_SCRIPT_REVIEW.md` (E1–E7 map + §10 Design B challenge) · `ADR-MM7E-1` (inject-don't-construct) · `MM7C_SIGNALSOURCE_CHARACTERIZATION.md` (C1–C6) · `MM7D1_SYNTHETIC_WIRING_PROOF.md` (the isolation construction reused).
**Starting state:** G1 CLOSED · 493 passing · no production entry script (`LoopDriver(...)` built only under `tests/`).
**Ending state:** G1 CLOSED · **505 passing · 0 failing** · `scripts/fno_runner.py` is the first production composition root; MM7A T1 flipped from tripwire to acceptance.

> **Scope guard.** Design B (ADR-MM7E-1): the root constructs the four mechanical collaborators and **accepts** the source. It builds **no** `SignalSource` — the characterization net injects test-local synthetic sources (`NoopSource`, `BuyExitSource`) under `tests/`. NiftyShield untouched; F3/F4/#4/#5/4C.7 untouched; `ExecutionMode.LIVE` out of scope.

---

## 1. What landed

**`scripts/fno_runner.build_runner(*, source, symbols, underlyings=None, …)`** — the composition root. Required production inputs are `source` (the DI seam), `symbols` (the universe), and `underlyings` (for an F&O universe). It:

1. **Refuses** (semantic refusals the driver does not own, MM7E §4):
   - `source is None` → `ValueError` (the T1 `source present` clause; a live runtime with no signal origin is a silent no-op).
   - `ExecutionMode.LIVE` ∧ `broker_positions is None` → `ValueError` (#6's territory; named, not built).
   - `has_derivatives(symbols)` ∧ no `underlyings` → `ValueError` (the W4 trap: no checker ⇒ vacuous gate + disabled G1 canonicalization).
2. **Warns** (warn > refuse) when `ExecutionMode.PAPER` ∧ `broker_positions is None` — a vacuous reconcile is acceptable on paper but the operator must know the gate has no teeth.
3. **Constructs the four collaborators** (Design B): one shared `clock` → `PaperBroker(clock)`, `ExecutionHandler(load_db_state=True, ExecutionMode.PAPER)`, `LiveDuckDBMarketDataProvider(symbols, db_manager)`, and the `LoopDriver` itself, targeting **`Mode.LIVE`**.
4. **Injects `build_master_readiness(underlyings, db_path=…)`** when (and only when) `has_derivatives(symbols)` — the activation switch for the G1 restore-canonicalization half (W4 / Finding E1-c); `None` for an equity universe (the carve-out).

The driver still owns the structural refusals (clock/provider/LIVE-handler inside `run()`); the root adds only the semantic layer. `master_db_path`/`clock`/`provider`/`db_manager`/`journal`/`metrics_path`/`max_bars` are optional injection seams defaulting to the production construction — the same DI the driver uses (config.py:9-13) — so the net can isolate the canonical store, the live provider, and the wall clock.

**This is also the live call-site MM.7 blocker #4 was missing:** `build_master_readiness(...)` is now invoked by a production module, not only a test.

---

## 2. Tests (the §6 characterization net) — +12 net, 493 → 505

**New `tests/scripts/_runner_harness.py`** — mirrors `_doubles.py`: the MM7C/MM7D.1 isolation (monkeypatch `handler_mod.ExecutionStore` → tmp; Finding E1-a), a tmp `DatabaseManager` (singleton reset), a `FakeMarketDataProvider`, a `ReplayClock(FIXED_DT)` (the handler's recovery calls `clock.now()` at construction, so a `None`-returning `FakeClock` is unusable here), a fixture instrument master (the T4 `parse_instruments`+`write_snapshot` pattern), and the two test-local synthetic sources.

| File | Tests | Pins |
|---|---|---|
| `test_fno_runner_composition.py` | 5 | The root builds the handler with `load_db_state=True`; constructs `PaperBroker`; targets `Mode.LIVE`+`ExecutionMode.PAPER`; injects the **real** resolver-backed checker for F&O (returns FRESH over the fixture master) and omits it for equity; the injected `source` is the one the driver carries (Design B). |
| `test_fno_runner_refusal.py` | 4 | The §4 contract: refuse on missing source / F&O-without-underlyings / `ExecutionMode.LIVE`-without-`broker_positions`; **warn** (not refuse) on vacuous paper reconcile. |
| `test_fno_runner_activation_path.py` | 2 | The E5 G1-protected sequence fires end-to-end via the production root on a FRESH F&O run — `seq == ["READINESS","CANONICALIZE_POSITIONS","CANONICALIZE_ORDERS","RECONCILE"]` + `RECONCILIATION_PASS`/`RUNNING` journaled; and the equity paper rung runs the MM7D.1 BUY/EXIT spine to a clean **STOPPED** (2 orders, 2 fills, position FLAT). |

**MM7A T1 converted (`tests/scripts/test_fno_entry_wiring.py`):** the two absence tripwires (`test_no_scripts_module_constructs_a_loopdriver`, `test_no_runner_script_exists_yet`) are **consciously flipped** to acceptance — the script now exists, is the runner entry point, and the driver `build_runner` builds for a live F&O universe satisfies every `_fno_live_contract` clause. The doubles-based predicate + 5 rejection cases are retained as the executable spec.

**MM7D.1 test 8 narrowed:** `test_proof_harness_is_test_local_not_an_entry_script` previously asserted "no `scripts/` builds a `LoopDriver`" (the T1 tripwire duplicated). Now that MM7E intentionally landed the script, it asserts only the proof's own test-locality (lives under `tests/`, defines its own source). No other test changed; the G1 closure guard (`core/`-scoped) is untouched — `fno_runner` uses the normal `process_signal` path, so the `process_group_signal`/`_check_greek_limits` carve-outs stay dead.

Validation: `pytest tests/scripts -q` → **21 passed**; `pytest -q` → **505 passed, 0 failing**.

---

## 3. TDD trail

RED first: with the net written and no `scripts/fno_runner.py`, `pytest tests/scripts` failed with `ModuleNotFoundError: No module named 'scripts.fno_runner'` (feature missing) — 3 collection errors + the refusal-before-construction tests already green. GREEN: after landing `build_runner`, one real defect surfaced (`FakeClock.now()` → `None` crashes the handler's construction-time recovery `clock.now().date()`); fixed by the harness using `ReplayClock(FIXED_DT)` (real `now()`, no-op `sleep`), the same clock MM7D.1 used. Re-run → 21 passed, then full suite 505 passed.

---

## 4. Design B honoured (the §10 / ADR-MM7E-1 decision, in code)

- **Zero source construction:** `fno_runner.py` imports no strategy/source module and constructs no `SignalSource`; `source` is a required parameter. The only `SignalSource` reference is the type import + the parameter.
- **W1 left MM7E:** the net injects `NoopSource`/`BuyExitSource` (test-local). The production source is still absent and is the next slice's concern.
- **Smallest root:** four constructed objects, not five. The root is a *partial* composition root — terminal source construction relocates to the strategy slice (the honest §10.2 Q4 caveat).

---

## 5. Stop condition

Implementation complete. Tests green (505 passing, 0 failing). Report written. Commit created. **Did NOT:** build a production `SignalSource`/strategy/broker adapter; touch F3/F4/#4/#5/4C.7; enable `ExecutionMode.LIVE`. The next slices are #6 (broker-positions adapter + W3 refusal, to give reconciliation teeth) and — separately — the strategy `SignalSource`.

*Filed under the G1 / MM7A–E review-first, characterize-before-change discipline. Companion to `MM7E_ENTRY_SCRIPT_REVIEW.md` (§10) and `ADR-MM7E-1`.*
