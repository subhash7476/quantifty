# MM13 — First Knowledge-Consuming SignalSource (PAPER integration proof)

**Document type:** Design spec (approved — ready for implementation planning)

**Status:** Approved

**Date:** 2026-07-06

**Milestone:** MM13 (Axis 1 of the MSI-engine productionization roadmap —
see `docs/reports/MSI_ENGINE_PRODUCTIONIZATION_SCOPING.md` §4, §7, §8)

---

## 1. Goal

Close the `Knowledge → [Strategy]` arrow.

Prove that a `KnowledgeObject` produced by `DRAOrchestrator` can drive a
`SignalSource` through `GuardedSignalSource → ExecutionHandler → PaperBroker`
and produce an observable fill.

This directly fixes the two gaps the scoping document named:

- **"The DRA is wired to nothing."** No script imports `core.msi` today; it
  executes only from tests. MM13 adds the first composition root that runs
  `DRAOrchestrator` outside a test.
- **"The `→ Strategy` arrow is unbuilt."** Nothing consumes Knowledge today.
  MM13 adds the first concrete `SignalSource` that reads a `KnowledgeObject`.

MM13 is **Axis 1** (integration / plumbing) from the scoping document — cheap,
front-runnable, and provable **now** against the existing experimental artifact.
It is explicitly **not** Axis 2 (real content: research harness, validation
harness, first Approved artifact).

## 2. Scope decisions (settled)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data source | **Real 1d candle store** | `data/market_data/nse/candles/1d/2026-02-27.duckdb` holds exactly Nifty 50 + India VIX. Verified: `DuckDBObservationReader.read(date(2026,2,27), symbols)` returns 10 real Observations. Real market values through the fixture artifact make the proof meaningful rather than synthetic. |
| Run scope | **Single day, one regime** | DRA evaluates one fixed date → one `KnowledgeObject` → source emits one entry signal; replay a bounded set of 1m bars through PAPER; observe the fill. Smallest thing that proves the full arrow. |
| Signal mapping altitude | **Trivial (dictated, not chosen)** | Principle 1 (Strategies Stay Dumb). The regime→signal map is a plumbing proof, not alpha. |

## 3. Architecture

Three new files. **No changes to any frozen file, to `fno_runner.py`, or to
`GuardedSignalSource`** — MM13 only *consumes* existing seams.

### 3.1 `core/strategies/knowledge_signal_source.py` — `KnowledgeSignalSource(SignalSource)`

The first concrete `SignalSource`. Implements the `core/runtime/signal_source.py`
contract and stays dumb (Principle 1: emit `SignalEvent` only; no broker/sizing/
risk logic inside). The name is deliberately general — it reads a
`KnowledgeObject`, not specifically a regime — so the same seam serves any
latent variable a later strategy chooses to act on.

- **Construction** — takes the injected `DRAOrchestrator`, the fixed
  `evaluation_date`, the `artifact_ref`, and a `latent_variable` selector
  (default `"market_regime"`). The latent variable to act on is a **parameter,
  not a hard-coded literal** — the source selects the matching `Estimate` from
  `market_state.estimates` by this field. This keeps the selection out of the
  code body without expanding scope (one constructor argument).
- **`on_start(context)`** — runs the DRA **once** for the fixed `evaluation_date`
  via the injected `DRAOrchestrator`, and caches the returned `KnowledgeObject`
  in an instance field. No persistence — the KnowledgeObject lives in-process for
  the run's duration. This is the one lifecycle hook a source may receive inputs
  through (signal_source.py §5.2/5.4); the DRA collaborators are injected into
  the source at construction, not pulled from the driver context.
- **`on_bar(bar)`** — reads the selected `Estimate` (`latent_variable ==`
  the configured selector, default `"market_regime"`) from the cached
  `market_state.estimates`. Emission policy:
  - Emit **one** `SignalEvent` (BUY) on the first bar after Knowledge is known;
    return `[]` on every subsequent bar (single-emit).
  - Single-emit is deliberate: emitting every bar would be masked by the
    position-stacking guard and make the proof unreadable.
  - **No EXIT branch.** Knowledge is computed once in `on_start` and never
    re-evaluated during the run, so the regime cannot change mid-run — an
    EXIT-on-regime-change branch would be dead code in the single-day/one-regime
    scope (YAGNI). Regime transitions + EXIT belong to the deferred multi-day
    scope, not MM13.
- **Mandatory signal shape (guard contract, verified against
  `guarded_signal_source.py` / `conformance.py`).** For the emitted BUY to pass
  `GuardedSignalSource` (ADR-018) rather than be dropped as a
  `SIGNAL_CONTRACT_REJECTED`, it MUST satisfy:
  - `signal.timestamp == bar.timestamp` (time comes from the bar, never
    wall-clock — architecture §4.1);
  - `metadata["sl_distance"]` numeric and `> 0`;
  - `metadata["risk_r"]` numeric and `> 0`
    (the §4.2 mandatory reserved keys — the strategy *declares* its intended
    stop distance and risk unit; the execution layer sizes from them. This is a
    declaration, not sizing, so Principle 1 holds).
  MM13 emits a trivial-but-valid declaration: `sl_distance = round(bar.close *
  sl_frac, 2)` (default `sl_frac = 0.01`) and `risk_r = 1.0` — both constructor
  parameters. The regime value and `knowledge_id` are also stamped into
  `metadata` so the test can prove Knowledge actually flowed into the signal.

### 3.2 `scripts/msi_paper_runner.py` — the composition root

The production entry point that does not exist today. Responsibilities:

1. **Build the DRA.** Construct the six collaborators —
   `DuckDBObservationReader` (pointed at the real 1d file),
   `DefaultEvidenceBuilder`, `FilesystemArtifactLoader` (pointed at the fixture
   artifact directory), `DefaultArtifactEvaluator`, `DefaultKnowledgeBuilder`,
   `DefaultKnowledgePublisher` (over the in-memory `KnowledgeRepository`) — and
   wire them into a `DRAOrchestrator`.
2. **Construct the source.** Build `KnowledgeSignalSource` around the
   orchestrator, the fixed `evaluation_date`, the `artifact_ref`, and the
   `latent_variable` selector (default `"market_regime"`).
3. **Inject into the runner.** Call
   `fno_runner.build_runner(source=..., symbols=[traded_symbol],
   execution_mode=ExecutionMode.PAPER, provider=..., clock=..., telemetry=...,
   db_manager=..., max_bars=...)`. `build_runner` wraps the source in
   `GuardedSignalSource` and builds the `LoopDriver` (no change to `fno_runner`
   required — it already accepts these injection points). Verified: the
   `build_runner` `Mode.LIVE` startup gate (startup/recovery/reconciliation)
   **passes** for an equity PAPER universe (no derivatives → no
   underlyings/SPAN required); reconciliation is vacuous-but-warned.
4. **Traded universe vs. regime inputs are separate.** The DRA reads the
   *regime inputs* (`NSE_INDEX|Nifty 50` + `NSE_INDEX|India VIX`) from the 1d
   file inside `on_start`. The *traded symbol* is a separate liquid equity
   (`NSE_EQ|INE139A01034`, which has full 1m coverage on 2026-02-27) whose bars
   drive the loop; the BUY is emitted on that equity. Regime gates an equity
   trade — index symbols are not order-routable and carry `volume=0`.
5. **Drive bars deterministically — `FakeMarketDataProvider` fed real bars.**
   The composition-root *factory* accepts an injected `provider` + `clock` +
   `max_bars`. The MM13 proof drives a bounded list of **real** `OHLCVBar`s read
   directly from `data/market_data/nse/candles/1m/2026-02-27.duckdb` through
   `tests/runtime/_doubles.py::FakeMarketDataProvider` + a `ReplayClock`.
   **Rationale (verified):** `DuckDBMarketDataProvider`'s historical read path
   returns empty for the copied per-date store (`MarketDataQuery.get_ohlcv`
   yields 0 rows — a historical-reader/partition-resolution gap), so it would
   silently stall the loop. `FakeMarketDataProvider` is the sanctioned
   driver-test provider (`base.py` names it "MockDataProvider: Test data"),
   keeps the proof hermetic and deterministic, and still drives the real
   Knowledge→execution arrow with real price bars. A live/real-provider CLI
   entrypoint for operator runs is **deferred** (it needs either the
   historical-reader fix or the live feed — rung-1 LIVE+PAPER, same status as
   `fno_runner` itself) and is out of MM13's proof scope.

### 3.3 `tests/msi/test_mm13_integration.py` — the proof

Integration test asserting the end-to-end arrow (see §5).

## 4. Data flow

```
1d file (Nifty 50 + India VIX)
   → DuckDBObservationReader.read(evaluation_date, symbols)
   → DefaultEvidenceBuilder.build()
   → ReferenceTestArtifact.evaluate()          [fixture threshold classifier]
   → MarketState
   → DefaultKnowledgeBuilder.build()
   → KnowledgeObject                            [cached in KnowledgeSignalSource.on_start]

1m bars (DuckDBMarketDataProvider, replay clock, bounded max_bars)
   → LoopDriver._dispatch_signals   [SIGNALS_RECEIVED counter++]
   → KnowledgeSignalSource.on_bar → SignalEvent (BUY, once)
   → GuardedSignalSource        [ADR-018 boundary validation — shape passes, not quarantined]
   → LoopDriver routes           [SIGNALS_ROUTED counter++]
   → ExecutionHandler.process_signal → non-None NormalizedOrder  [EXECUTION_CALLS counter++]
   → PaperBroker.place_order     [order accepted, broker_id returned]
   → telemetry counters + journal entry   ✅ observable
```

**PaperBroker fill semantics (why the proof keys off order acceptance, not a
position fill):** `PaperBroker.place_order()` returns a broker_id but does **not**
invoke the fill callback (`paper_broker.py:26-43`). No `FillEvent` is emitted, so
`process_signal` does not populate the position tracker (the documented CLAUDE.md
pitfall "position tracker must update on paper fills"). Wiring `FillEvent` →
`position_tracker.update_from_fill()` is execution-layer work outside MM13's scope
fence (§6). MM13 therefore proves the arrow by the **observable, real** effect:
the Knowledge-derived signal is *accepted and routed* to the broker (telemetry
counters + journal), not by a synthetic position fill.

## 5. Success criterion

**Not "it runs."** MM13 succeeds when a **Knowledge-derived `SignalEvent` is
accepted and routed through the full runtime stack to the broker** — observable
via telemetry counters and the runtime event journal — asserted by the
integration test. Concretely, the test verifies:

1. The DRA run yields a `KnowledgeObject` with the selected estimate (default
   `market_regime`) over the real 1d data.
2. `KnowledgeSignalSource.on_bar` emits exactly one BUY `SignalEvent` for the run.
3. That signal traverses `GuardedSignalSource` without being rejected or
   quarantined (`guarded_source.quarantined is False`; no `STRATEGY_ERROR`/
   `STRATEGY_QUARANTINED` journal record).
4. The `LoopDriver` routes it to `ExecutionHandler.process_signal`, which returns
   a non-None `NormalizedOrder` and places the order on `PaperBroker`. Observable
   as `InMemoryTelemetrySink` counters: `SIGNALS_RECEIVED >= 1`,
   `SIGNALS_ROUTED >= 1`, `EXECUTION_CALLS >= 1`, plus the routed-order journal
   entry.

**Note:** the proof keys off *order acceptance*, not a position-tracker fill —
see the PaperBroker fill-semantics note in §4. A position fill would require
`FillEvent` wiring that §6 fences out of MM13.

## 6. Explicit exclusions (scope fence — do NOT build these in MM13)

- **No `data/msi/knowledge.duckdb` / persistent Knowledge store.**
  `KnowledgeRepository` stays in-memory. Durable Knowledge publication is A4 /
  Axis 2.
- **No multi-file or 90-day-spanning observation reader.** A single 1d file
  suffices: the fixture artifact consumes only a point-in-time `vix_close`, so
  `lookback_days=90` is declarative-only on this path. A spanning reader is
  Axis 2 work and must not be built here.
- **No validation harness and no real-artifact authoring.** MM13 reuses the
  experimental fixture artifact (`tests/msi/fixtures/test_artifact/`). Governance
  permits this: MSI-009 §13 requires *Active Published (validated)* artifacts
  only for **production** runs; an experimental PAPER integration proof does not.
- **No changes to frozen components, `fno_runner.py`, or `GuardedSignalSource`.**
  MM13 consumes seams; it does not modify them.
- **No LIVE execution mode.** PAPER only.
- **No live/real-provider CLI entrypoint.** MM13 ships the composition-root
  *factory* (`build_msi_paper_runner`) with an injected provider; the proof
  drives it with `FakeMarketDataProvider`. A runnable operator entrypoint needs
  the historical-reader fix or the live feed (rung-1) and is deferred.
- **No EXIT / regime-transition logic** (see §3.1 — dead code in the single-day
  scope; deferred to multi-day).

## 7. Governance reconciliation

- Slots as **MM13** — "First External Strategy Validation — PAPER", already
  listed Planned in PROJECT_STATE. The first Knowledge-consuming `SignalSource`
  run through `fno_runner` in PAPER *is* the MM13 integration surface.
- **Precedent:** the heartbeat canary proved data→execution plumbing separately
  from alpha; MM13 proves Knowledge→execution plumbing separately from alpha the
  same way.
- **Downstream, unchanged:** Axis 2 (an MSI-010-class program: research authoring
  + validation harness + first Approved artifact) and MM14 (LIVE readiness +
  broker margin reconciliation) both sit after MM13.
- MM13 surfaces **which Knowledge fields a strategy actually needs** — the design
  input to Axis 2's real artifact. That is the strategic reason to build it first.

## 8. Risks and how the design handles them

| Risk | Handling |
|------|----------|
| Live provider yields zero bars (data ends 2026-05-11) | Inject `DuckDBMarketDataProvider` + replay clock + `max_bars`; never the live provider. Verified this provider exists and loads from the candle store. |
| 90-day lookback not satisfied by single-file reader | Not needed — fixture artifact uses point-in-time `vix_close` only; `lookback_days` is declarative on this path. Verified `read()` returns rows from the real 1d file. |
| Trivial signal filtered by the guard | Guard enforces *shape* (ADR-018), not rate. Emit a well-formed `SignalEvent`; single-emit avoids position-stacking masking. Verified guard responsibilities in `guarded_signal_source.py`. |
| Scope creep into Axis 2 | §6 fences persistence, spanning reader, validation, and real-artifact authoring out of MM13 explicitly. |
| PaperBroker emits no `FillEvent` → no position-tracker fill | Success criterion (§5) keys off order *acceptance* (telemetry counters `SIGNALS_ROUTED`/`EXECUTION_CALLS` + journal), not a position fill. `FillEvent` wiring is out of scope (§6). Verified against `paper_broker.py:26-43` and `tests/integration/test_portfolio_view_driver.py`. |

## 9. Verified facts underpinning this design

- `data/market_data/nse/candles/1d/2026-02-27.duckdb` contains exactly
  `NSE_INDEX|Nifty 50`, `NSE_INDEX|Nifty Bank`, `NSE_INDEX|India VIX`.
- `DuckDBObservationReader('…/1d/2026-02-27.duckdb').read(date(2026,2,27),
  ('NSE_INDEX|Nifty 50','NSE_INDEX|India VIX'))` returns 10 real Observations.
- `DuckDBMarketDataProvider` (`core/database/providers/market_data.py`) is the
  non-live backtest/replay provider; loads OHLCV upfront from the candle store.
- `fno_runner.build_runner` accepts `source`, `provider`, `clock`, `max_bars`,
  `execution_mode` injection points and wraps the source in `GuardedSignalSource`
  — no modification required.
- `GuardedSignalSource` enforces per-signal boundary validation and quarantine
  on raise; it does not rate-limit well-shaped signals.
- No script currently imports `core.msi` (`grep` over `scripts/`, `app_facade/`,
  `flask_app/` returns nothing) — MM13 is the first.
- **End-to-end prototype (proven).** A throwaway prototype wired the real DRA →
  `KnowledgeSignalSource` (with `sl_distance`/`risk_r` metadata) →
  `build_runner(execution_mode=PAPER, provider=FakeMarketDataProvider(real 1m
  bars), clock=ReplayClock, max_bars=5)` → `driver.run()`. Result:
  `SIGNALS_RECEIVED=1, SIGNALS_ROUTED=1, EXECUTION_CALLS=1`, log line "Order
  placed with broker" — the full arrow works. The `build_runner` `Mode.LIVE`
  startup gate passed for the equity PAPER universe.
- **Guard contract (proven by rejection then acceptance).** A BUY missing
  `sl_distance`/`risk_r` was dropped as `SIGNAL_CONTRACT_REJECTIONS=1`; adding
  both (numeric, > 0) plus `timestamp == bar.timestamp` cleared the guard.
- **Execution store init.** The integration test must supply a fresh
  `ExecutionStore` (tmp path) — pointing the handler at the real data-root
  without schema init raised "no such table: trades" during fill processing.
  Use the `tests/integration/test_portfolio_view_driver.py` monkeypatch pattern
  (`ExecutionStore(str(tmp_path / "execution.db"))` + `DatabaseManager(
  data_root=tmp_path)`).
