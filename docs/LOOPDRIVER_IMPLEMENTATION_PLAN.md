## LOOPDRIVER_IMPLEMENTATION_PLAN.md

**Status:** PLAN — no code yet. Phased build plan for the `LoopDriver`.
**Implements:** `docs/DRIVER_SPECIFICATION.md` (the contract), governed by `docs/ARCHITECTURE_DECISIONS.md` (ADR-001..006) and `docs/PLATFORM_CONSTITUTION.md`.
**Goal:** build the `LoopDriver` as a sequence of small, independently-mergeable, green-on-merge phases — never one oversized PR — preserving deterministic development.

> No code in this document. It defines phases, their surfaces, tests, risks, and order.

> **⚠️ Phase-label note (read before cross-referencing).** This document keeps its **original A–H labels** below (A,B,C lifecycle/journal/loop; D signal pull; **E ExecutionHandler; F RuntimeWatchdog; G Telemetry; H Recovery/startup gate**). The actual build sequence chosen in `docs/PROJECT_STATE.md` / `docs/SESSION_BOOTSTRAP.md` **relabels the later phases** to a safety-first order: **E = RuntimeWatchdog (this doc's F), F = Startup Gate/Recovery (this doc's H), G = Execution Routing (this doc's E), H = Telemetry (this doc's G)**. So "Phase E" in the state docs = watchdog, but "Phase E" here = execution. Each PROJECT_STATE bullet names the mapping in its trailing reference; trust the state docs for *what's done*, this doc for *per-phase design detail*.
>
> **⚠️ "Phase H — Telemetry" naming (read before recording new work).** In **both** this doc (G — Telemetry integration) and the state docs (Phase H — Telemetry), "Telemetry" means the **§10 ZMQ `TelemetryPublisher` wire transport** — the per-interval metrics/positions/health snapshot published over the wire. That phase is **still planned**. A separate, smaller piece of work — an **internal in-process metric-counter layer** (`core/runtime/metrics.py`: `RuntimeMetric` / `TelemetrySink` / `Null`/`InMemoryTelemetrySink`, driven by the `LoopDriver`) — has **already landed** and was recorded as the standalone **"Runtime Observability Layer"** milestone (CHANGELOG 2026-06-06; PROJECT_STATE Completed), **deliberately not labeled "Phase H"** to avoid the collision. The counter layer is a **foundation** the §10 publisher can read from and publish; it does **not** satisfy Phase H — Telemetry.

---

## 0. Prerequisites (all already merged)

The runtime building blocks the driver consumes by dependency injection exist and are tested:

- `core/runtime/signal_source.py` — `SignalSource` ABC (§5).
- `core/runtime/config.py` — `DriverConfig` + `Mode` (§13).
- `core/runtime/event_journal.py` — `RuntimeEventJournal` + `EventType`/`Severity` (§15).
- `core/clock.py` — `Clock.set_time` uniform no-op (§6.4) + `ReplayClock`/`RealTimeClock`.
- `core/execution/watchdog.py` — `RuntimeWatchdog` (`record_bar`/`check_data_staleness`/`write_heartbeat`, §9).
- `core/execution/handler.py` — `ExecutionHandler` (`process_signal`, `_replay_state`, `reconciliation`, `activate_kill_switch`, §8/§11).
- `core/messaging/telemetry.py` — `TelemetryPublisher` (transport, §10).
- `core/database/providers/base.py` — `MarketDataProvider` (§7).

**No prerequisite work remains.** Every phase below only touches the new driver file and tests.

---

## 1. Cross-cutting decisions (apply to every phase)

- **One production file grows:** `core/runtime/driver.py` (the `LoopDriver` class), per spec Appendix A. Each phase adds methods/behavior to the same class; no phase rewrites a prior one.
- **Dependency injection, constructor evolves incrementally.** Each phase adds the collaborator parameter it needs (`config` → `journal` → `provider`+`clock` → `source` → `execution` → `watchdog` → `telemetry`). This causes minor constructor churn across PRs but keeps each PR's surface minimal and honest. *(Alternative: declare the full DI signature in Phase A with later collaborators unused — rejected: ships dead parameters and untested wiring ahead of need.)*
- **Test doubles, introduced once and reused:** a shared `tests/runtime/_doubles.py` (or `conftest.py` fixtures) providing `FakeMarketDataProvider` (scripted bars → exhaustion / live `None`), `FakeSignalSource` (scripted signal lists), and a `FakeExecutionHandler`/mock exposing `process_signal`, `metrics`, `_trades_today`, `_kill_switched`, `position_tracker`. Introduced in Phase C, extended as needed. Real collaborators are never constructed in driver unit tests.
- **Determinism guardrail (ADR-003):** single thread, single loop, fixed per-tick ordering (§4.1). No phase may add concurrency to the decision path.
- **Strategy-agnostic guardrail (ADR-002/006):** every phase keeps `core/runtime/driver.py` free of `strategies|runner|backtest|state|models|ftmo` imports. An `ast` forbidden-import test (mirroring `test_signal_source.py`) lands with Phase A and guards every subsequent phase.

---

## 2. Phases

Each phase: Purpose · Files · Dependencies · Test strategy · Risks, then the four required questions.

---

### Phase A — Lifecycle state machine only

- **Purpose:** the `LoopDriver` skeleton with the six states (STARTUP, RUNNING, PAUSED, STOPPING, STOPPED, RECOVERY) and the §3.2 transitions (`start`/`pause`/`resume`/`stop`), as pure in-memory logic. No loop, no IO, no collaborators except `DriverConfig`.
- **Files affected:** create `core/runtime/driver.py`; create `tests/runtime/test_driver_lifecycle.py`; add the forbidden-import guard test.
- **Dependencies:** `DriverConfig` (merged). Nothing else.
- **Test strategy:** drive every legal transition and assert resulting `state`; assert illegal transitions are rejected (e.g. `resume` when not PAUSED); assert terminal STOPPED; assert PAUSED is distinct from STOPPED; forbidden-import `ast` scan of the module.
- **Risks:** over-modeling states/transitions beyond §3.2 (build exactly the spec's set, no more); defining a "kill-switched" pseudo-state (per §3.2 it is *not* a state — the loop keeps running; do not model it as a state here).

1. **Available:** a constructable `LoopDriver(config)` with inspectable lifecycle state and transition methods.
2. **Disabled:** everything operational — no bar pull, no clock advance, no signals, no execution, no watchdog, no telemetry, no journal.
3. **New tests:** `test_driver_lifecycle.py` (transition table, illegal transitions, terminal state) + forbidden-import guard.
4. **Merge independently?** **Yes.** Pure logic, fully testable, ships green.

---

### Phase B — Journal integration

- **Purpose:** wire `RuntimeEventJournal` into the Phase-A transitions so each state change emits its event (`STARTUP`, `RUNNING`, `PAUSED`, `RESUMED`, `STOPPING`, `STOPPED`) once per occurrence (edge-triggered, §15.4).
- **Files affected:** `core/runtime/driver.py`; create `tests/runtime/test_driver_journal.py`.
- **Dependencies:** Phase A; `RuntimeEventJournal` (merged).
- **Test strategy:** inject a real `RuntimeEventJournal` pointed at a `tmp_path`; drive transitions; assert exactly the expected event sequence (type + severity) and **no per-tick duplication**; assert a journal write failure does not break a transition (journal already swallows, §15.6).
- **Risks:** emitting transition events more than once; coupling lifecycle correctness to journal success (the transition must complete even if the journal write fails).

1. **Available:** lifecycle transitions are durably recorded to `logs/runtime_events.jsonl`.
2. **Disabled:** all operational behavior still off (no loop/exec/etc.); incident events (`KILL_SWITCH_ACTIVATED`, `WATCHDOG_STALE_DATA`, `BROKER_ERROR`, `TELEMETRY_FAILURE`, reconciliation/recovery events) not yet emitted — they arrive with their owning phases.
3. **New tests:** `test_driver_journal.py` (event-per-transition, edge-triggering, write-failure tolerance).
4. **Merge independently?** **Yes.** Builds only on A.

---

### Phase C — Tick loop skeleton + Clock advancement + Market data

- **Purpose:** the runnable-but-inert loop (§4.1 steps 1–2, §6, §7). Pull bars from `MarketDataProvider` per symbol in fixed order; `clock.set_time(bar.timestamp)` before any per-bar work; count `bars_processed`; honor `max_bars`; replay exhaustion (`is_data_available` false for all symbols → STOPPING) vs live no-bar poll (`poll_interval_s` via `clock.sleep`); cooperative `stop()`. **No signals, no execution.**
- **Files affected:** `core/runtime/driver.py`; create `tests/runtime/_doubles.py`; create `tests/runtime/test_driver_loop.py`.
- **Dependencies:** Phases A–B; `Clock` (+`set_time`, merged); `MarketDataProvider` (merged).
- **Test strategy:** `FakeMarketDataProvider` scripts a finite bar sequence; assert clock advances to each `bar.timestamp` (replay) before the (currently empty) per-bar step; assert exhaustion → STOPPING → STOPPED; assert `max_bars` halts; assert `stop()` interrupts mid-run; assert live mode polls and ignores `None` bars without error; assert multi-symbol fixed ordering.
- **Risks (highest-risk phase):** the determinism crux — clock advance **must** precede per-bar work or live==replay breaks silently; live busy-spin if poll/sleep mis-wired; `max_bars`/exhaustion/stop interaction; multi-symbol ordering must be fixed; do **not** advance the clock from wall-clock in replay.

1. **Available:** the driver *runs* — deterministically pulls bars and advances time, end-to-end, with clean start/exhaust/stop. Observable via journal lifecycle events.
2. **Disabled:** signals are not pulled (or pulled-and-discarded), nothing is executed, no watchdog, no telemetry.
3. **New tests:** `test_driver_loop.py` (clock-advance ordering, replay exhaustion, live poll, `max_bars`, `stop()`, multi-symbol order) + `_doubles.py`.
4. **Merge independently?** **Yes** — a runnable inert loop is a coherent, shippable unit.

---

### Phase D — SignalSource integration

- **Purpose:** call `source.on_bar(bar)` once per bar (§5.2) and collect the returned `List[SignalEvent]` in order. **Signals are not routed yet** — counted/journaled only.
- **Files affected:** `core/runtime/driver.py`; create `tests/runtime/test_driver_signal_pull.py`.
- **Dependencies:** Phase C; `SignalSource` (merged).
- **Test strategy:** `FakeSignalSource` returns scripted lists (incl. empty); assert `on_bar` is called once per bar with the right bar; assert returned order is preserved and not re-ranked; assert empty list is a no-op; assert the driver branches on no client type (same path for any source).
- **Risks:** accidentally acting on signals here (must stay inert until E); re-ranking the list (forbidden — list order is routing order); calling `on_bar` off the driver thread (must stay synchronous).

1. **Available:** deterministic signal *pull* — the seam is exercised in the live loop, signals collected per bar.
2. **Disabled:** execution — signals are not sent to `process_signal`; no orders, no fills.
3. **New tests:** `test_driver_signal_pull.py` (once-per-bar, order preserved, empty-list no-op).
4. **Merge independently?** **Yes.** Builds on C; harmless without E.

---

### Phase E — ExecutionHandler integration

- **Purpose:** route each pulled signal to `ExecutionHandler.process_signal(signal, bar.close)` in list order (§8). Isolate per-signal exceptions (one failure logs + emits `BROKER_ERROR`, loop survives, §8.4). Detect a kill-switch flip (`_kill_switched`) edge-triggered → `KILL_SWITCH_ACTIVATED` journal event; keep looping (§3.2). **No exit logic, no sizing/risk** (forbidden — handler owns them).
- **Files affected:** `core/runtime/driver.py`; create `tests/runtime/test_driver_execution.py`; extend `_doubles.py` with `FakeExecutionHandler`.
- **Dependencies:** Phases C–D; `ExecutionHandler` (merged).
- **Test strategy:** `FakeExecutionHandler` records `process_signal(signal, current_price)` calls; assert `current_price == bar.close`; assert routing order == list order; assert a raised `process_signal` is caught, journaled `BROKER_ERROR`, loop continues to next signal/bar; assert a kill-switched handler returns `None` and the loop keeps running and emits `KILL_SWITCH_ACTIVATED` exactly once; assert the driver never calls any exit/TP/SL logic.
- **Risks (high):** an unhandled `process_signal` exception killing the loop (must be isolated); accidentally implementing exit/risk/sizing (ADR-005 violation); duplicate `KILL_SWITCH_ACTIVATED` emission; the off-thread live-fill seam (§8.3) — the driver must only *read* trackers, never add a second ledger-write path.

1. **Available:** end-to-end paper/replay trading — signals become orders through the single execution path (ADR-006). The driver is now a functional trading loop.
2. **Disabled:** staleness protection (no watchdog yet), telemetry, and the startup safety gate — so this phase is **not yet safe for live**.
3. **New tests:** `test_driver_execution.py` (routing order, `current_price=bar.close`, exception isolation, kill-switch-but-running, no-exit-logic guard).
4. **Merge independently?** **Yes**, for paper/replay. **Live deployment must wait for F + H.**

---

### Phase F — RuntimeWatchdog integration

- **Purpose:** drive `RuntimeWatchdog` (§9): `record_bar()` on each bar arrival, `check_data_staleness()` + `write_heartbeat(bars_processed)` once per tick — **live mode only** (§9.5). Emit edge-triggered `WATCHDOG_STALE_DATA` (and the resulting `KILL_SWITCH_ACTIVATED`) journal events.
- **Files affected:** `core/runtime/driver.py`; create `tests/runtime/test_driver_watchdog.py`.
- **Dependencies:** Phase C (bar-arrival hook + loop) and an injected `ExecutionHandler` (the watchdog trips its kill switch). **Independent of D/E** — can be merged any time after C.
- **Test strategy:** inject a real `RuntimeWatchdog` over a fake handler; in **live** mode assert `record_bar`/`check_data_staleness`/`write_heartbeat` are driven and `logs/heartbeat.json` is written; simulate a >5-min gap during market hours → kill switch trips, loop keeps running, `WATCHDOG_STALE_DATA` journaled once; in **replay** mode assert none of the watchdog methods are called (no false-trip).
- **Risks:** running the wall-clock watchdog in replay → false trips (must gate on `config.is_live`); duplicate stale events (edge-trigger); private-attr coupling to `_kill_switched` (acknowledge, §10.7).

1. **Available:** Principle 5 / ADR-004 operational — stale live data trips the kill switch and is durably recorded; heartbeat beacon live.
2. **Disabled:** telemetry stream; startup gate.
3. **New tests:** `test_driver_watchdog.py` (live drive + heartbeat, stale→kill+journal, replay-gated-off).
4. **Merge independently?** **Yes** (after C). Recommended **before E** so trading is born into a stale-data-protected loop.

---

### Phase G — Telemetry integration

- **Purpose:** build the per-interval metrics/positions/health snapshot from the read-only execution + watchdog + position-tracker state and publish via `TelemetryPublisher` (§10), throttled to `telemetry_interval_s`. Drop the legacy `active_count` strategy line (§10.3). Fire-and-forget (§10.6); a publisher/construction failure emits `TELEMETRY_FAILURE` (§15.6) and never breaks the loop.
- **Files affected:** `core/runtime/driver.py`; create `tests/runtime/test_driver_telemetry.py`.
- **Dependencies:** Phase C (loop) + injected `ExecutionHandler` (and `RuntimeWatchdog` for `data_healthy`). Gated by `config.telemetry_enabled`.
- **Test strategy:** fake publisher captures `publish_metrics/positions/health` payloads; assert throttle (≤ once per interval); assert metrics built from `handler.metrics`/`_trades_today`/`_kill_switched` and positions from `position_tracker.get_all_positions()`; assert no `active_count`/strategy field; assert a raised publish does not break the loop and emits `TELEMETRY_FAILURE`.
- **Risks:** a telemetry exception killing the loop (must be non-fatal); leaking a strategy-coupled field; private-attr coupling (§10.7); over-publishing (ignore throttle).

1. **Available:** live dashboard observability (metrics/positions/health over ZMQ), complementing heartbeat + journal.
2. **Disabled:** startup gate (if H not yet merged).
3. **New tests:** `test_driver_telemetry.py` (throttle, snapshot fields, no strategy field, non-fatal failure + `TELEMETRY_FAILURE`).
4. **Merge independently?** **Yes** (after C). Pure observability; lowest operational risk among the IO phases.

---

### Phase H — Recovery & reconciliation startup gates

- **Purpose:** the §11 startup-validation gate. On `start()`: emit `RECOVERY_STARTED`; ensure `ExecutionHandler._replay_state()` ran (handler constructed with `load_db_state=True`) → `RECOVERY_COMPLETED`; run `handler.reconciliation.reconcile(broker_positions)` → empty list = `RECONCILIATION_PASS`, non-empty = `RECONCILIATION_FAIL`; verify provider over non-empty symbols + broker reachable. **Refuse `STARTUP → RUNNING` on any failure** (→ STOPPED + critical) (§11.4). Reuse `_replay_state` — never re-restore (ADR-001).
- **Files affected:** `core/runtime/driver.py`; create `tests/runtime/test_driver_startup_gate.py`.
- **Dependencies:** Phase A (state machine) + injected `ExecutionHandler`. Independent of D/E/F/G mechanically, but **must precede live/paper-against-real-ledger runs**.
- **Test strategy:** fake handler/reconciliation returns empty vs non-empty alert lists → assert RUNNING vs refuse-to-start (STOPPED + `RECONCILIATION_FAIL` + critical); assert recovery events emitted in order; assert the driver does **not** re-run state restore itself; assert empty-symbols / unreachable-broker refuse to start; assert reconciliation is treated as vacuously clear in paper/replay where the broker has no book.
- **Risks:** re-implementing state restore in the driver (ADR-001 violation — must reuse `_replay_state`); letting the loop start on a failed gate; reconciliation requiring broker positions (define the paper/replay vacuous-clear path); over-strictness blocking paper dev (respect `require_reconciliation_on_start`).

1. **Available:** the driver refuses to trade on an unvalidated/inconsistent ledger — the last safety pillar (§11.4, ADR-001). Combined with F, the loop is now live-safe.
2. **Disabled:** nothing further — this is the final functional phase; remaining work (broker-side reconciliation depth, SPAN margin, F&O product model) is out of LoopDriver scope (`PROJECT_STATE.md` Planned #4–#6).
3. **New tests:** `test_driver_startup_gate.py` (pass/fail gate, recovery event order, no-re-restore, empty-symbols/broker refusal, paper vacuous-clear).
4. **Merge independently?** **Yes** (after A + handler injection). Recommended **before E** for live readiness.

---

## 3. Recommended PR breakdown

One PR per phase, each green-on-merge — **8 PRs**:

| PR | Phase | Touches |
|----|-------|---------|
| 1 | A — lifecycle state machine | `driver.py` (new), `test_driver_lifecycle.py`, import-guard test |
| 2 | B — journal on transitions | `driver.py`, `test_driver_journal.py` |
| 3 | C — loop + clock + market data | `driver.py`, `_doubles.py`, `test_driver_loop.py` |
| 4 | F — watchdog (live-gated) | `driver.py`, `test_driver_watchdog.py` |
| 5 | H — recovery + reconciliation gate | `driver.py`, `test_driver_startup_gate.py` |
| 6 | D — signal pull | `driver.py`, `test_driver_signal_pull.py` |
| 7 | E — execution routing | `driver.py`, `test_driver_execution.py`, extend `_doubles.py` |
| 8 | G — telemetry | `driver.py`, `test_driver_telemetry.py` |

Optional combination: **A+B** are both small and tightly related (state machine + its event emission) and may ship as one PR if reviewer prefers. **C and E should each stay standalone** (highest risk/size). A final tiny PR may add a `scripts/run_trade_loop.py` wiring example + the `PROJECT_STATE`/`CHANGELOG` updates once E+F+H land.

## 4. Estimated complexity per phase

| Phase | Complexity | Why |
|-------|-----------|-----|
| A | Low–Medium | Pure state-machine logic; main risk is scope discipline |
| B | Low | Thin wiring of journal into existing transitions |
| C | **High** | Determinism crux: clock-advance ordering, replay/live semantics, exhaustion/`max_bars`/`stop`, multi-symbol order |
| D | Low | Seam already tested; just call + collect |
| E | **High** | Routing + exception isolation + kill-switch handling + no-exit discipline (§8) |
| F | Medium | Watchdog drive + live-mode gating + edge-triggered incident events |
| G | Medium | Snapshot gather (private-attr coupling), throttle, fire-and-forget |
| H | Medium–High | Startup gate, reconciliation semantics, reuse-not-reimplement recovery |

## 5. Recommended order of implementation

**A → B → C → F → H → D → E → G**

Rationale (safety-first, deterministic): stand up the **inert, observable loop** first (A, B, C); add the two **protective gates while still inert** — F (stale-data kill, ADR-004) and H (startup ledger gate, ADR-001); only then enable signal **pull** (D) and **execution** (E), so the moment trades can occur they are born into a loop already guarded by F and H; finish with **telemetry** (G), the lowest-risk pure-observability layer, once metrics are meaningful.

This deviates from the alphabetical labels by pulling F and H ahead of D/E — deliberately, so that **execution (the only phase where capital moves) is never merged ahead of the staleness and startup safety gates.** If a strictly label-ordered sequence is preferred, A→B→C→D→E→F→G→H is acceptable **only if E is not deployed live until F and H land**.

---

## 6. Out of scope for the LoopDriver (do not absorb)

- Strategy/signal generation, exit/TP/SL policy (ADR-002/005; §1.3).
- Sizing/risk/margin/fill bookkeeping (owned by `ExecutionHandler`; §8).
- Broker-side reconciliation depth, SPAN margin, F&O product model (`PROJECT_STATE.md` Planned #4–#6) — these block *live* trading regardless of the driver.
- Any second orchestration path or direct `process_signal` caller (ADR-006).
