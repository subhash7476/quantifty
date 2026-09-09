# MM.7E — Entry Script Review (Planning Only)

**Type:** Review — composition-root map + runtime recommendation + characterization plan. **No code. No `scripts/`. No `SignalSource`. No broker adapter. No fixes.** Report only.
**Date:** 2026-06-11
**Basis:** `MM7_LIVE_WIRING_REVIEW.md` (W1–W4 + mode matrix) · `MM7A_CHARACTERIZATION_REPORT.md` (T1–T4 net) · `MM7C_SIGNALSOURCE_CHARACTERIZATION.md` (C1–C6 consumer contract) · `MM7D1_SYNTHETIC_WIRING_PROOF.md` (the spine proven end-to-end, test-local) · `PROJECT_STATE.md` (Planned #4/#6, Open Findings F3/F4).
**Starting state:** G1 CLOSED · 493 passing · 0 failing · MM7A/B/C/D.1 COMPLETE · **no production entry script exists** (`LoopDriver(...)` is constructed only under `tests/`).

> **Scope guard.** NiftyShield is ABANDONED — not referenced, ported, or resurrected. This review writes no code, creates no `scripts/`, builds no `SignalSource` or broker adapter, and touches none of W3/F3/F4/4C.7. It is the map the MM7E implementation slice will build against.

---

## 0. Pre-recommendation review (A / B / C / D)

### A — Do I agree with the current MM7 roadmap?

**Yes, with one sequencing refinement.** The roadmap (MM7A §7 / MM7 §8) is: **MM7E** entry script (target `Mode.LIVE`/`ExecutionMode.PAPER`) → **#6** broker-positions adapter + W3 refusal → **F4/F3** → **#4/#5** product+margin → **4C.7** payload. This is correct: each slice already has its acceptance/regression net in place (T1/T4 gate MM7E; T2/T3 gate #6), and the characterize-before-change discipline that closed G1 is preserved.

The **refinement**: MM7E as written couples two unbuilt things under one heading — the **composition root** (the script that wires `LoopDriver`) and the **production `SignalSource`** (W1, the strategy→`on_bar` adapter). These are independently testable and independently riskful. I recommend MM7E land the composition root against a **deterministic, non-alpha production source** (the smallest real `SignalSource` that satisfies C1–C6) and treat a *real strategy* source as a separate slice. Rationale in §7 + Alternative B.

### B — Alternative implementation order considered

**Considered and rejected: "broker adapter (#6) before the entry script."** Argument for it: W2/W3 are the only *unbuilt collaborators* with a known shape mismatch, and T2/T3 already pin them, so they could merge independently. **Rejected because** the entry script is the **sole consumer** of the adapter (MM7 §3.1) — building #6 first produces a tested artifact with no call site, and the first deployment target (`Mode.LIVE`/`ExecutionMode.PAPER`) is **vacuously clear without `broker_positions`** (driver.py:462-463), so the script can land and run the full gate *before* #6. The roadmap order (script first, paper-safe; then #6 to give reconciliation teeth) is correct. The genuine refinement is the W1 split inside MM7E (A above), not a reorder of MM7E vs #6.

### C — Assumptions (all stated; the load-bearing ones flagged)

1. **`ExecutionStore` path is hardcoded in the handler.** `ExecutionHandler.__init__` constructs `ExecutionStore()` **with no argument** (handler.py:145), which defaults to `data/execution.db` (execution_store.py:11). **The entry script cannot redirect the canonical DB by construction** — production *wants* `data/execution.db`, so this is correct for live, but it means the script has no DI seam for the store path (tests monkeypatch `handler_mod.ExecutionStore`). **Load-bearing for E1** — see Finding E1-a.
2. **`load_db_state=True` is the default** (handler.py:127); recovery runs at handler construction (handler.py:186-187), and the driver reuses it (driver.py:348-351, ADR-001). The script must construct the handler *before* the driver.
3. **The first deployment is paper-safe.** `Mode.LIVE` + `ExecutionMode.PAPER` exercises the entire gate/watchdog/canonicalization with **no real orders** — assumed acceptable as the first rung (MM7 §4). True for `PaperBroker`; the synthetic proof (MM7D.1) already drove this exact handler/broker pair end-to-end.
4. **A production `MarketDataProvider` for live exists** — `LiveDuckDBMarketDataProvider(symbols, db_manager)` (MM7 §1, live_market.py:20). Not re-verified line-by-line this slice; assumed from the MM7 review. **Flagged** as the dependency I have *least* independent evidence for (§7 risk #3).
5. **F4 (lot 65/30) and F3 (tick paise) are inert at `ExecutionMode.PAPER`** for the *wiring* itself — but F4 becomes live-affecting the instant the option path sizes a real order (PROJECT_STATE F4). Assumed: MM7E may wire the spine at PAPER without F4 verification, but **must refuse `ExecutionMode.LIVE` F&O until F4 is verified** (§7 risk #1).

### D — Questions whose answers would materially change implementation

1. **What is the production `SignalSource` MM7E injects — a real strategy, or the minimal deterministic source?** This is the single largest fork (A/B above). If "real strategy," MM7E pulls in alpha + an `OptionsProvider` (MM7C C4 chain-parity, §4) + F4 — a much larger slice. If "minimal source," MM7E is pure composition. **Recommendation: minimal source; defer strategy.** Stated as a recommendation so it does not block — but a contrary owner decision materially expands MM7E.
2. **Equity-first or F&O-first for the first live run?** An **equity** `Mode.LIVE`/`PAPER` script needs *no* `master_readiness`, *no* F4, and skips canonicalization by design (driver.py:383-386) — it is the smallest possible composition root and flips T1 cleanly. An **F&O** script is the actual MM7 objective but inherits F4 + the W4 canonicalization-activation obligation. **Recommendation: stand the composition root up on equity first (proves the root), then add the F&O symbol set + `build_master_readiness` to give the gate teeth** — both within MM7E, equity as the inner rung.

These are the only two questions that change the *shape* of MM7E. Everything else (which provider class, telemetry on/off, watchdog wiring) is determined by the contract below and needs no owner input.

---

## 1. Findings (E1 — Composition Root)

**The first production composition root is the file that does not yet exist:** a module under `scripts/` (e.g. `scripts/fno_runner.py`) that constructs the collaborators and calls `LoopDriver(...).run()`. Today **every** `LoopDriver` construction is under `tests/` (MM7A T1 tripwire; confirmed). The composition root's job is purely DI — `DriverConfig` carries *settings*; "wiring those lives at the entry-script layer (`scripts/`), not [in `DriverConfig`]" (config.py:9-13).

**The five objects it must construct, with the dependency each pulls in (file:line evidence):**

| Object | Constructor (verified) | Dependencies it forces |
|---|---|---|
| **`LoopDriver`** | `driver.py:144-154` — `__init__(config, clock, provider, journal, source, watchdog, execution, broker_positions, telemetry, publisher, master_readiness)`; only `config` is non-optional in `__init__`, but `run()` raises without `clock`+`provider` (driver.py:496-499) and without `execution` in LIVE (driver.py:505-506) | all of the below |
| **`ExecutionHandler`** | `handler.py:118-127` — `__init__(db_manager, clock, broker, risk_manager=None, capture_engine=None, config=None, metrics_path=..., initial_capital=100000.0, load_db_state=True)` | `DatabaseManager`, `Clock`, `BrokerAdapter`; internally constructs `ExecutionStore()` **no-arg → `data/execution.db`** (handler.py:145), `OrderRepository`/`FillRepository`/`PositionRepository`, `PositionTracker`, `OrderTracker`, **`ReconciliationEngine(self.position_tracker)`** (handler.py:158), `TradingWriter(db_manager)` (audit DuckDB). Recovery runs in `__init__` when `load_db_state=True` (handler.py:186-187). |
| **`PaperBroker`** | `PaperBroker(clock)` (MM7C/MM7D.1 construction; satisfies `BrokerAdapter`; synchronous synth fill via `_handle_broker_fill`, gated `isinstance(broker, PaperBroker)`) | shares the driver/handler `Clock` |
| **`ExecutionStore`** | `execution_store.py:11` — `__init__(db_path="data/execution.db")` | **constructed *inside* the handler, no-arg** (handler.py:145) — **not** a driver/handler DI parameter. SQLite at `data/execution.db` is the canonical truth (ADR-001). |
| **`MasterReadiness`** (the checker callable) | `master_readiness.py:88-104` — `build_master_readiness(underlyings, *, db_path=None, as_of=None) -> Callable[[], ReadinessVerdict]`; builds the real `InstrumentResolver` once, returns `lambda: assess(resolver, traded)` | `InstrumentResolver` over the materialized master DB (`data/instruments/nse_fo_instruments.duckdb`); **`underlyings` passed by name**, NOT derived from `config.symbols` (master_readiness.py:95 docstring) |

### Finding E1-a — the `ExecutionStore` path is not a DI seam
The handler hardcodes `ExecutionStore()` (handler.py:145). For **production this is correct** (live wants `data/execution.db`), so MM7E needs no change — but the composition root has **no knob** to point the canonical store elsewhere, and any MM7E *test* must monkeypatch `handler_mod.ExecutionStore` (the MM7C/MM7D.1 isolation construction) exactly as the existing nets do. Worth stating so the implementer does not look for a constructor argument that isn't there.

### Finding E1-b — `ExecutionMode` ≠ `Mode`, set on two different objects
The script sets `DriverConfig.Mode` (LIVE/REPLAY, config.py:24-34) on the driver **and** `ExecutionMode` (DRY_RUN/PAPER/LIVE, inside `ExecutionConfig`) on the handler — orthogonal (MM7 §1.1, §4). `Mode.LIVE`/`ExecutionMode.PAPER` is the first safe rung.

### Finding E1-c — the master checker is load-bearing for canonicalization, not just the gate (W4)
`_canonicalize_restored_ledger` (driver.py:439-444) is gated on the **same** `is_live ∧ has_derivatives ∧ master_readiness is not None` condition as the staleness gate (driver.py:383-386). **Omitting `build_master_readiness(...)` silently disables the entire G1 restore-canonicalization** the program just closed — the restored ledger stays legacy-typed. Injecting the checker is the *activation switch* for G1's restore half on the live path (MM7A T4 pins this). The script's tests must assert canonicalization actually fires.

---

## 2. Dependency Map (E3)

For each driver dependency: **Required?** (for the first F&O `Mode.LIVE`/`PAPER` rung) · **Stub-able?** · **Missing today?**

| Dependency | Required? | Optional? | Stub-able? | Missing today? | Evidence |
|---|---|---|---|---|---|
| `config` (`DriverConfig`, `Mode.LIVE`, F&O `symbols`) | **Yes** | no | no (it's the settings) | no | config.py:24-34; driver.py:144 |
| `clock` (`RealTimeClock` for LIVE) | **Yes** — `run()` raises without it | no | `ReplayClock` for tests | no | driver.py:496-499; clock.py |
| `provider` (`LiveDuckDBMarketDataProvider`) | **Yes** — `run()` raises without it | no | `FakeMarketDataProvider` in tests | **partially** — class exists (live_market.py:20); production instantiation unproven | driver.py:496-499; MM7 §1 |
| `source` (`SignalSource`) | **Yes in practice** — no source ⇒ no signals ⇒ no trades | yes (`__init__`) | test doubles only | **YES — W1: no production `SignalSource` exists** | MM7 §6 W1; MM7A §3 |
| `execution` (`ExecutionHandler`, `load_db_state=True`) | **Yes** — LIVE raises without it | no | exists, never wired to a live root | exists, **not wired** | driver.py:505-506; handler.py:118-127 |
| `broker` (inside handler; `PaperBroker` first, `UpstoxAdapter` for real) | **Yes** | no | `PaperBroker` *is* the paper rung | `PaperBroker` exists; live `UpstoxAdapter` exists | handler.py:121,132 |
| `broker_positions` (`Callable[[], List[Dict]]`) | **No for the paper rung** (vacuous → clean) ; **Yes** for a non-vacuous reconcile | yes | test lambdas | **YES — W2 shape bridge (#6) unbuilt** | driver.py:462-463; MM7 §3.1 |
| `master_readiness` (`build_master_readiness(...)`) | **Yes for live F&O** (else gate + canonicalization both vacuous) | yes | exists, only test-injected | exists (MM7), **not wired** | driver.py:383-386,439-444; master_readiness.py:88 |
| `journal` (`RuntimeEventJournal`) | recommended (no-op if absent) | yes | n/a | exists | driver.py:147; MM7 §1 |
| `watchdog` (`RuntimeWatchdog`) | recommended for live (ADR-004) | yes | `FakeWatchdog` | exists | driver.py:149 |
| `telemetry` / `publisher` | optional (defaults `NullTelemetrySink`) | yes | null sink | exists | driver.py:152-153,177 |
| `db_manager` (`DatabaseManager`, for the handler) | **Yes** (handler dep) | no | tmp-root in tests | exists | handler.py:119 |

**Two genuinely missing production pieces:** `source` (W1) and `broker_positions` (W2/#6). Everything else exists; what is unbuilt is the **root that constructs them** plus those two collaborators.

---

## 3. Runtime Recommendation (E2)

Three candidates evaluated:

| Candidate | Verdict | Why |
|---|---|---|
| **`Mode.REPLAY`** | **Not the live target** | `is_live` false ⇒ master gate, canonicalization, and watchdog all skipped (driver.py:383, 439, live-only watchdog). This is the *backtest* path — it proves nothing about live participation that MM7D.1 didn't already prove deterministically. Useful only as a test harness. |
| **`Mode.LIVE` + `ExecutionMode.PAPER`** | **RECOMMENDED FIRST** | Exercises the **entire** startup gate (recovery → master readiness → canonicalization → reconciliation), the watchdog, and real `RealTimeClock`/live provider polling — against the real broker book once #6 lands — **while no capital moves** (`PaperBroker` synth fills). It is the smallest composition that is genuinely "live" yet capital-safe, and it is **not blocked** on F4/#4/#5 (those gate `ExecutionMode.LIVE` only). MM7D.1 already proved this exact handler+broker pair drives the spine end-to-end. |
| **`Mode.LIVE` + `ExecutionMode.LIVE`** | **Blocked — not the first target** | Real broker orders. Inherits **F4** (live option sizing with the unverified lot 65/30 — PROJECT_STATE F4, a hard precondition), **#4/#5** (F&O product model + SPAN margin — `Blocked` in PROJECT_STATE), and a non-vacuous **#6** reconcile. Cannot be the first rung. |

**Recommended first supported runtime: `Mode.LIVE` + `ExecutionMode.PAPER`,** with the **inner rung** being an **equity** universe (no `master_readiness`/F4 needed — proves the composition root), then **promote to an F&O** universe + `build_master_readiness([...])` within the same slice to give the gate and canonicalization teeth (Question D-2). `ExecutionMode.LIVE` is explicitly out of MM7E.

---

## 4. Refusal Policy (E4)

What startup *should* do for each missing dependency, with the current code behavior and the rationale:

| Missing | Current behavior | Should | Rationale |
|---|---|---|---|
| **No `SignalSource`** | `run()` proceeds; loop runs inert (source optional, driver.py:521) — **no trades, no error** | **Refuse at the composition root** (the script asserts `source is not None` before constructing the driver) — *not* inside `run()` | A live trading runtime with no signal origin is a silent no-op, the most dangerous failure mode (looks healthy, does nothing). The seam keeps `source` optional for the inert replay path (Phase C/D); the **script** is where "a live run needs a source" becomes a refusal. This is exactly the T1 acceptance predicate (`source` present). Do **not** make `run()` raise — that would break the legitimate inert path. |
| **No `broker_positions` adapter** | Reconciliation is **vacuously clear** (driver.py:462-463) — starts clean | **Warn (paper) / Refuse (real)** | At `ExecutionMode.PAPER` a vacuous reconcile is acceptable (no real book to diverge from) — emit a WARNING that reconciliation is vacuous, so the operator knows the gate has no teeth yet. At `ExecutionMode.LIVE`, starting without reconciling the real broker book is unsafe → the script should refuse to start `ExecutionMode.LIVE` without `broker_positions` (this is #6's territory; MM7E names it). |
| **No `master_readiness`** (F&O universe) | Gate + canonicalization both **silently skipped** (driver.py:383-386, 439-442) — **starts, but G1 restore-canonicalization is inert (W4)** | **Refuse for a live F&O run** | This is the W4 trap: a live F&O run without the checker is a *vacuous pass* that also disables canonicalization, regressing G1 invisibly. The composition root must inject `build_master_readiness(...)` whenever `has_derivatives(symbols)` — and its acceptance test (T1 clause + T4) must assert canonicalization fires. Equity-only LIVE legitimately has no checker (carve-out), so the refusal is conditioned on `has_derivatives`. |
| **No `provider`** | `run()` **raises `RuntimeError`** (driver.py:496-499) | **Refuse (already does)** — keep | Correct as-is; the script need add nothing. Same for **no `clock`** (driver.py:496-499) and **no `execution` in LIVE** (driver.py:505-506). |

**Policy summary:** the **driver already refuses** the structural essentials (clock/provider/LIVE-handler) inside `run()`. MM7E's refusal contract adds the **semantic** refusals at the **composition root** — `source` present, `master_readiness` present when `has_derivatives`, and (deferred to #6) `broker_positions` present before `ExecutionMode.LIVE`. **Refuse > warn > fallback** throughout — fallback is never appropriate for a trading runtime (refuse-to-start is the safe default, driver.py:343 / Constitution §7). W3's uncaught-`broker_positions()`-exception refusal is **#6's** to fix, not MM7E's; the script must **not** wrap the callable in its own try/except (the refusal belongs inside the gate — MM7 §3.2).

---

## 5. Activation Path (E5) — the G1-protected sequence

How `Master Readiness → Restore Canonicalization → Reconciliation` becomes **active** in the production runtime. The chain is already coded inside `_run_startup_gate` (driver.py:335-370); MM7E's job is to inject the three things that flip it from vacuous to live:

```
Handler construction (load_db_state=True)        handler.py:186-187  →  _replay_state() restores ledger LEGACY-typed
        ↓  (driver reuses; never re-restores — ADR-001)
LoopDriver.run()                                  driver.py:481
        ↓  is_live ∧ execution present
_run_startup_gate()                               driver.py:335
        ├─ RECOVERY_STARTED / RECOVERY_COMPLETED  driver.py:347-351
        ├─ _check_master_readiness()              driver.py:372-417
        │     gate: is_live ∧ has_derivatives(symbols) ∧ master_readiness is not None   driver.py:383-385
        │     BLOCK → INSTRUMENT_MASTER_UNAVAILABLE → abort_startup → STOPPED            driver.py:394-403
        │     WARN  → INSTRUMENT_MASTER_STALE (start, durable record)                    driver.py:404-416
        ├─ _canonicalize_restored_ledger()        driver.py:419-444
        │     SAME gate (driver.py:439-441) → canonicalize_restored_positions()+_orders()  (handler-owned in-place swap)
        │     futures EQUITY→FUTURE (H1), option parser-lot→master-lot (H2), symbol byte-preserved (H3)
        ├─ _reconcile_ledger()                     driver.py:446-477
        │     driven iff require_reconciliation_on_start ∧ broker_positions is not None   driver.py:462-463
        │     reconcile(broker_positions()) → alerts? → RECONCILIATION_FAIL → abort → STOPPED   driver.py:464-475
        │     else RECONCILIATION_PASS                                                    driver.py:476
        └─ start() → RUNNING                       driver.py:369
```

**The three injections that activate it (all MM7E's responsibility):**
1. **Master readiness** — inject `build_master_readiness(underlyings, db_path=<master>)` (master_readiness.py:88). Without it, the gate AND canonicalization are both skipped (W4 / Finding E1-c).
2. **Restore canonicalization** — *no new injection*; it rides on the same `master_readiness is not None` gate (driver.py:439-441). Injecting the checker (1) is what activates it. The handler methods `canonicalize_restored_positions/orders` already exist (G1 Wave 3/4).
3. **Reconciliation** — inject `broker_positions` (the #6 adapter, `Dict[str,Position]`→`List[Dict]` with string `side` — W2). Until #6, this is vacuously clear (paper-safe). `ReconciliationEngine` already lives on the handler (handler.py:158); the driver calls it (driver.py:464).

**G1-protection note:** this exact ordering (readiness *before* canonicalization *before* reconciliation) is the locked Option-B sequence (G1 Wave 3B). MM7E must not reorder it, and its tests must assert the sequence fires on a FRESH F&O run (extending MM7A T4 from a unit-level checker test to the script's end-to-end acceptance).

---

## 6. Characterization Plan (E6)

Tests required **before** MM7E implementation. Most already exist as the MM7A net (their tripwires flip RED when the script lands — that is the signal to convert the predicate into the script's real assertion). New files named precisely; **no implementation here.**

**Already in place (MM7A) — convert/observe on arrival:**

| File | Test names | Role for MM7E |
|---|---|---|
| `tests/scripts/test_fno_entry_wiring.py` | `test_no_scripts_module_constructs_loopdriver` (T1 tripwire) ; `test_no_runner_entry_point_exists` ; `_fno_live_contract(driver)` acceptance predicate + its 5 rejection cases | **The acceptance test.** Tripwires flip RED when `scripts/fno_runner.py` lands → convert the predicate (`Mode.LIVE` ∧ `has_derivatives` ∧ `execution` ∧ `master_readiness` ∧ `source` all present) into the script's assertion. |
| `tests/runtime/test_driver_canonicalization_requires_checker.py` | `test_*_without_checker_no_canonicalize` ; `test_*_with_real_factory_canonicalizes_once` (T4) | Assert MM7E's injected `build_master_readiness` makes canonicalization **fire** (W4 / E5). Reuse against the real script-built driver. |
| `tests/execution/test_broker_positions_adapter.py` | T2 LONG/SHORT/FLAT + enum-raises-pass-through | #6's acceptance; MM7E only consumes the adapter. |
| `tests/runtime/test_driver_broker_positions_failure.py` | T3 RED-documenting | #6 flips it; MM7E must **not** wrap the callable. |

**New files MM7E must add (acceptance for the composition root):**

| File | Test names | Pins |
|---|---|---|
| `tests/scripts/test_fno_runner_composition.py` | `test_runner_builds_handler_with_load_db_state_true` ; `test_runner_constructs_paperbroker_for_paper_rung` ; `test_runner_injects_master_readiness_when_derivatives` ; `test_runner_omits_checker_for_equity_universe` ; `test_runner_targets_mode_live_executionmode_paper_first` | The root constructs each of the five E1 objects with the correct settings; equity vs F&O conditioning of the checker (Finding E1-c). Built with the MM7C/MM7D.1 isolation construction (monkeypatch `handler_mod.ExecutionStore` → tmp; Finding E1-a). |
| `tests/scripts/test_fno_runner_refusal.py` | `test_refuses_when_source_missing` ; `test_refuses_live_executionmode_without_broker_positions` ; `test_refuses_fno_live_without_master_readiness` ; `test_warns_when_reconciliation_vacuous_on_paper` | The §4 refusal contract at the composition root (semantic refusals the driver does not own). |
| `tests/scripts/test_fno_runner_activation_path.py` | `test_fresh_fno_run_sequences_readiness_canonicalize_reconcile` ; `test_paper_rung_runs_to_clean_stopped` | The E5 G1-protected sequence fires end-to-end on a FRESH F&O run via the **real** `build_master_readiness` + a fixture master; the paper rung reaches a clean STOPPED (the MM7D.1 spine, now driven by the production root not a test-local harness). |

**Sequencing rule the net enforces (unchanged from MM7A §7):** do not land MM7E until T1's tripwire is consciously flipped to the acceptance assertion and T4 (canonicalization fires) is green against the real script-built driver. The T3 defect is #6's to flip, not MM7E's.

---

## 7. Risk Assessment (E7)

**1 — Highest-risk dependency: the production `SignalSource` (W1).**
It does not exist (MM7 §6 / MM7A §3), and it is the one collaborator that carries *judgment* — every other dependency is mechanical plumbing the MM7D.1 proof already exercised. Its risk is twofold: (a) it is the only place a real strategy's correctness/alpha enters, and (b) a real options source drags in the **chain-parity obligation** (MM7C C4 §4 — a replay-symmetric `OptionsProvider`, *not* a live API call inside `on_bar`) **and F4** (live option lot sizing). **Mitigation:** split it out of MM7E (Recommendation A/B). MM7E ships the composition root against the *minimal deterministic* production source (smallest real `SignalSource` honoring C1–C6, no alpha, no chain); the *strategy* source is a separate, later slice with its own net. This keeps MM7E pure plumbing — the part that is fully de-risked by MM7C+MM7D.1.

**2 — Missing production abstraction: the `broker_positions` adapter (W2/#6).**
The two ends do not share a type — `UpstoxAdapter.get_positions()` returns `Dict[str, Position]` with an *enum* `side`; `ReconciliationEngine.reconcile` needs `List[Dict]` with a *string* `side` (MM7 §3.1; T2 proves the naive pass-through raises). This abstraction is unbuilt; MM7E consumes it but the paper rung runs without it (vacuous reconcile). It is correctly **#6's** deliverable, not MM7E's — but it is the missing piece between "paper-safe" and "live-correct." Its absence also hides **W3** (an uncaught `broker_positions()` exception escapes `run()` — driver.py:464 runs before `run()`'s try/finally, MM7 §3.2): MM7E must resist the temptation to paper over W3 in the script.

**3 — Assumption most likely to be wrong: that a production `MarketDataProvider` is drop-in ready.**
This is the dependency I have the *least* independent evidence for — `LiveDuckDBMarketDataProvider(symbols, db_manager)` is cited from the MM7 review (live_market.py:20) but not re-verified end-to-end this slice, and live polling cadence + bar-arrival semantics under `RealTimeClock` are unexercised (MM7D.1 used a `FakeMarketDataProvider` with `ReplayClock`). If the live provider's `get_next_bar`/poll contract differs from the fake's, the loop's "no bar → poll one interval" path (driver.py:540-544) is the first thing to break in a real `Mode.LIVE` run. **Mitigation:** a thin live-provider contract test against the fake's shape before MM7E wires it.

**4 — What could invalidate the MM7 plan?**
If the owner decides MM7E must ship a **real strategy** source (not the minimal one), the slice's risk profile flips from "mechanical plumbing, fully netted" to "alpha + chain-parity + F4," and the clean T1/T4 acceptance no longer bounds it — MM7E would then *require* F4 verification and a replay-symmetric chain provider before it could even be paper-safe, collapsing two roadmap slices into one large, under-netted slice. The plan stays valid **iff** MM7E is scoped to the composition root + minimal source (Recommendation A). The secondary invalidator is **F4**: if the materialized lot (65/30) is *wrong* and unverified when an `ExecutionMode.LIVE` F&O run is attempted, every live option is mis-sized — which is why F4 verification is a hard gate *between* MM7E (paper) and any live-money F&O run, exactly where the roadmap places it.

---

## 8. Recommended Implementation Sequence (and the alternative considered)

**Recommended (refines MM7A §7):**

1. **MM7E.a — Composition root, equity rung.** `scripts/fno_runner.py` constructs handler (`load_db_state=True`, `ExecutionMode.PAPER`) + `PaperBroker` + `RealTimeClock` + live provider + a **minimal deterministic production `SignalSource`**, target `Mode.LIVE` on an **equity** universe (no `master_readiness`, no F4). Flips T1; acceptance = `test_fno_runner_composition.py` + the equity-carve-out clause. *Smallest thing that makes the root real.*
2. **MM7E.b — F&O rung + activation.** Add the F&O symbol set + `build_master_readiness([...])`. Acceptance = T4 (canonicalization fires) + `test_fno_runner_activation_path.py` (E5 sequence) + the §4 refusal tests. Still `ExecutionMode.PAPER` — paper-safe, full gate teeth, reconciliation vacuous.
3. **#6 — broker-positions adapter + W3 refusal.** W2 bridge (acceptance T2) + flip W3 (T3 defect → refusal→journal→STOPPED). Gives reconciliation teeth.
4. **F4 verification + F3 disposition.** Hard precondition for `ExecutionMode.LIVE` F&O.
5. **#4/#5 product+margin → 4C.7 payload.** Unblocks true live derivatives; 4C.7 stays blocked until 1–4.
6. **(separate slice) Strategy `SignalSource`** — the real alpha + replay-symmetric `OptionsProvider`, on its own net.

**Alternative considered (rejected — see §0.B):** "#6 broker adapter before the entry script." Rejected because the script is the adapter's sole consumer and the first deployment is vacuous-reconcile-safe without it, so building #6 first yields a tested artifact with no call site. The retained refinement from this alternative is *not* a reorder but the **W1 split** (strategy source out of MM7E), which is what actually shrinks MM7E's risk.

---

## 9. Stop Condition

Review complete. Report written. **No code changed, no `scripts/` created, no `SignalSource`/broker adapter built, no tests added, no commit made.** W3/F3/F4/4C.7 untouched; MM7E/F3/F4/4C.7 implementation NOT started.

### Return summary (the four requested answers)

1. **Recommended first runtime mode:** `Mode.LIVE` + `ExecutionMode.PAPER` — exercises the entire startup gate, canonicalization, watchdog, and (with #6) reconciliation against the real broker book while no capital moves; not blocked on F4/#4/#5. Stand the composition root up on an **equity** universe first (no checker/F4), then promote to an **F&O** universe + `build_master_readiness(...)` within MM7E. `ExecutionMode.LIVE` is out of scope.
2. **Highest-risk dependency:** the production `SignalSource` (W1) — the only collaborator carrying judgment, and the one that drags in chain-parity (MM7C C4) and F4. **Mitigation: split it out of MM7E**; ship the root against a minimal deterministic source, defer the strategy source to its own slice.
3. **Required characterization before MM7E implementation:** convert the MM7A T1 tripwire (`tests/scripts/test_fno_entry_wiring.py`) into the script's acceptance assertion and keep T4 (`test_driver_canonicalization_requires_checker.py`) green against the real script-built driver; add `tests/scripts/test_fno_runner_composition.py`, `…_refusal.py`, and `…_activation_path.py` (§6). T2/T3 remain #6's gate.
4. **Questions to answer before coding:** (a) Does MM7E inject a **minimal deterministic** source or a **real strategy** source? (recommend minimal — a "real strategy" answer materially expands the slice into F4 + chain-parity territory). (b) **Equity-first or F&O-first** for the first live run? (recommend equity rung first within MM7E, then F&O). No other open question changes MM7E's shape.

---

*Filed under the G1 / MM7A–D review-first, characterize-before-change discipline. Companion to `MM7_LIVE_WIRING_REVIEW.md`, `MM7A_CHARACTERIZATION_REPORT.md`, `MM7C_SIGNALSOURCE_CHARACTERIZATION.md`, `MM7D1_SYNTHETIC_WIRING_PROOF.md`.*

---

## 10. MM7E.1 — Composition Root Scope Challenge (Design A vs Design B)

**Type:** Scope challenge — planning only. **No code. No tests. No commits.** Appended 2026-06-12.

**The assumption under challenge:** *"MM7E requires a production `SignalSource`."* The body of this review (§0.A, §7-1) already pushed back on it once — recommending the *strategy* source be split out and MM7E ship "the root against a **minimal deterministic production source**." That wording is the soft form of the fork. This section makes the cut precise.

### 10.1 The two designs, stated exactly

- **Design A — root owns source creation.** MM7E constructs all five E1 objects, *including* a production `SignalSource` (the §7 "minimal deterministic" source: a real, no-alpha implementation honoring C1–C6 that MM7E imports and instantiates).
- **Design B — root accepts source by injection.** MM7E constructs **four** objects (`LoopDriver`, `ExecutionHandler`, `PaperBroker`, `provider`) and takes `SignalSource` as a **parameter**. The first production source — minimal or strategy — is deferred to a later slice. MM7E depends only on the C1–C6 *consumer protocol*, never on any concrete source module.

The difference is **not** "minimal vs strategy source" (that fork is §7's, and it lives *inside* Design A). The difference is **who owns construction of the source object.** Design A: MM7E. Design B: MM7E's caller.

### 10.2 The five questions

**Q1 — Which design minimizes risk? → Design B.**
Every risk in §7 that is not pure plumbing enters through the *source*: alpha/judgment (§7-1a), the chain-parity obligation (MM7C C4, §7-1b), and F4 live-lot sizing. Design A, even at "minimal," still requires MM7E to author and construct a production C1–C6 implementation — new production code with its own correctness burden, and a standing temptation to grow it toward the real strategy (the §7-4 invalidator: "two roadmap slices collapse into one under-netted slice"). Design B reduces MM7E's source-risk surface to **zero**: no source is imported, instantiated, or owned, so none of §7-1/§7-4 can attach to the slice. The injected object is a test double in the net and a real source only when a later slice provides one.

**Q2 — Which design minimizes coupling? → Design B.**
Design B is textbook dependency inversion: MM7E depends on the `SignalSource` *protocol* (the C1–C6 consumer contract this program already characterized), not on any concrete source. Zero import edge from `scripts/fno_runner.py` to any strategy/source module. Design A hard-wires MM7E to one concrete minimal-source implementation, and through it to whatever that source pulls in (C4 `OptionsProvider` the moment it touches a chain). B keeps the composition root pure plumbing — exactly the part MM7C+MM7D.1 already de-risked.

**Q3 — Which design better matches MM7D.1? → Design B, decisively.**
MM7D.1 proved the spine by **injecting a test-local synthetic source** into the driver (`source` is already a `LoopDriver.__init__` parameter, driver.py:144). MM7D.1 never had the harness *construct* a production source — it *received* one. Design B is the production-shaped continuation of precisely that pattern: same injection seam, promoted from test-local to the runner's signature. Design A *diverges* from MM7D.1 by making the root own a construction step MM7D.1 deliberately never performed. The MM7D.1 spine, driven by the Design-B root with an injected source, is a one-line change of *who supplies the source* — not a new construction path.

**Q4 — Which design gives the smallest production composition root? → Design B (four objects, not five).**
Honest caveat: a true composition root is the *single* place the whole graph is wired, so Design B does not *delete* source construction — it **relocates** it to a higher root (the strategy slice) that constructs the source and calls the runner. So MM7E under B is a *partial* root / builder, not the terminal one. That is the correct shape here: the paper rung is capital-safe and fully testable with an injected (test-double or minimal) source, and the terminal root that wires a *real* source legitimately belongs to the slice that owns alpha. Smallest root within MM7E, at the honest cost of "no single file can yet run live unaided" — which is already true today and is not MM7E's job to resolve.

**Q5 — Would Design B remove W1 from MM7E entirely? → Yes.**
W1 is "no production `SignalSource` exists." Under Design B, MM7E never needs one to exist: its acceptance tests inject doubles (exactly as the MM7A `_fno_live_contract` predicate only asserts `source is not None`, and MM7D.1 supplied a synthetic), and its refusal contract (§4) is unchanged — the runner still asserts `source is not None` before constructing the driver. So W1 leaves MM7E's critical path completely and becomes **solely** the strategy slice's concern. Under Design A, W1 stays *inside* MM7E (the minimal source is W1, partially discharged), keeping the slice coupled to source authorship. B is the only design that makes the §7-1 mitigation total rather than partial.

### 10.3 Reconciliation with the body of this review

§0.A and §7-1 already said "split the strategy source out; ship against a minimal deterministic source." Design B is the **sharper, fully-consistent** form of that recommendation: it removes the residual coupling the §7 wording left in by *not constructing the minimal source inside MM7E either*. Nothing in §1–§9 contradicts B — the refusal policy (§4: assert `source is not None` at the root), the activation path (§5: the three injections are `master_readiness` + `broker_positions`, *not* the source), and the characterization plan (§6: T1 predicate is presence-only; MM7D.1 spine is injection-driven) are all already written in injection terms. Adopting B changes one word in §8.1: MM7E.a constructs the root and **accepts** a source rather than **building** one.

### 10.4 Deliverable

- **Recommended design: B.** MM7E constructs the four mechanical collaborators and exposes a typed `SignalSource` injection seam with a not-None refusal; it does **not** construct a source. It wins on all five axes (risk, coupling, MM7D.1 fidelity, root size, W1 removal) and is the unbroken continuation of the seam MM7D.1 already proved.
- **Rationale:** the source is the sole carrier of judgment and the sole gateway to chain-parity (C4) and F4; keeping its construction out of MM7E confines the slice to fully-de-risked plumbing, holds T1/T4 as a clean acceptance boundary, and prevents the §7-4 collapse of two slices into one under-netted one. The only cost — that no single file can yet run live unaided — is already the status quo and is correctly the strategy slice's debt, not MM7E's.
- **Should MM7E own `SignalSource` creation? No.** MM7E owns the *composition of the four collaborators* and the *injection point and refusal* for the source — not the source's construction. The first concrete source (minimal or strategy) is a later slice that wires the terminal root. MM7E does **not** require a production `SignalSource`; it requires the **seam** for one.

**Scope note:** challenge complete, findings appended. No code, no `scripts/`, no `SignalSource`, no tests, no commit. The recommendation tightens §7-1/§8.1 from "ship a minimal source" to "inject the source"; it does not alter the runtime target (§3), the refusal contract (§4), the activation sequence (§5), or the net (§6).
