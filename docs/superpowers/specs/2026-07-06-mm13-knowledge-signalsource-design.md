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

### 3.1 `core/strategies/regime_reader_source.py` — `RegimeReaderSource(SignalSource)`

The first concrete `SignalSource`. Implements the `core/runtime/signal_source.py`
contract and stays dumb (Principle 1: emit `SignalEvent` only; no broker/sizing/
risk logic inside).

- **`on_start(context)`** — runs the DRA **once** for the fixed `evaluation_date`
  via the injected `DRAOrchestrator`, and caches the returned `KnowledgeObject`
  in an instance field. No persistence — the KnowledgeObject lives in-process for
  the run's duration. This is the one lifecycle hook a source may receive inputs
  through (signal_source.py §5.2/5.4); the DRA collaborators are injected into
  the source at construction, not pulled from the driver context.
- **`on_bar(bar)`** — reads the regime `Estimate` (`latent_variable ==
  "market_regime"`) from the cached `market_state.estimates`. Emission policy:
  - Emit **one** `SignalEvent` (BUY) on the first bar after Knowledge is known.
  - Emit EXIT if the regime value changes from the value last acted on (won't
    fire in the single-day/one-regime scope, but the branch is defined so the
    contract is complete and honest).
  - Otherwise return `[]` (the normal do-nothing case).
  - Single-emit is deliberate: emitting every bar would be masked by the
    position-stacking guard and make the proof unreadable.
- The emitted `SignalEvent` carries a well-formed shape (valid `strategy_id`,
  `symbol`, `timestamp`, `signal_type`, `confidence`) so it passes
  `GuardedSignalSource`'s per-signal boundary validation (ADR-018 / conformance
  §4). The guard enforces *shape*, not rate — a correctly-shaped mechanical
  signal is not filtered away.

### 3.2 `scripts/msi_paper_runner.py` — the composition root

The production entry point that does not exist today. Responsibilities:

1. **Build the DRA.** Construct the six collaborators —
   `DuckDBObservationReader` (pointed at the real 1d file),
   `DefaultEvidenceBuilder`, `FilesystemArtifactLoader` (pointed at the fixture
   artifact directory), `DefaultArtifactEvaluator`, `DefaultKnowledgeBuilder`,
   `DefaultKnowledgePublisher` (over the in-memory `KnowledgeRepository`) — and
   wire them into a `DRAOrchestrator`.
2. **Construct the source.** Build `RegimeReaderSource` around the orchestrator
   and the fixed `evaluation_date`.
3. **Inject into the runner.** Call
   `fno_runner.build_runner(source=..., symbols=[...],
   execution_mode=ExecutionMode.PAPER, provider=..., clock=..., max_bars=...)`.
   `build_runner` wraps the source in `GuardedSignalSource` and builds the
   `LoopDriver` (no change to `fno_runner` required — it already accepts these
   injection points).
4. **Drive bars deterministically.** Inject a `DuckDBMarketDataProvider` +
   a replay `Clock` + a bounded `max_bars` over the copied candle store.
   **Not** the default `LiveDuckDBMarketDataProvider` + `RealTimeClock`: the
   copied data ends 2026-05-11 and a live run today (2026-07-06) would receive
   zero bars and stall — a vacuous "proof". Deterministic replay is Principle 4's
   sanctioned path ("live and backtest data treated identically") and is exactly
   the isolation the `fno_runner` docstring calls the characterization net.

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
   → KnowledgeObject                            [cached in RegimeReaderSource.on_start]

1m bars (DuckDBMarketDataProvider, replay clock, bounded max_bars)
   → LoopDriver.on_bar
   → RegimeReaderSource.on_bar → SignalEvent (BUY, once)
   → GuardedSignalSource        [ADR-018 boundary validation — shape passes]
   → ExecutionHandler.process_signal
   → PaperBroker                 [synthetic fill, no capital]
   → Fill + journal entry        ✅ observable
```

## 5. Success criterion

**Not "it runs."** MM13 succeeds when a **Knowledge-derived `SignalEvent`
produces an observable PaperBroker fill and a journal entry**, asserted by the
integration test. Concretely, the test verifies:

1. The DRA run yields a `KnowledgeObject` with a `market_regime` estimate over
   the real 1d data.
2. `RegimeReaderSource.on_bar` emits exactly one BUY `SignalEvent` for the run.
3. That signal traverses `GuardedSignalSource` without being rejected or
   quarantined (right shape).
4. `ExecutionHandler` routes it to `PaperBroker` and a fill is produced,
   recorded in the position tracker and the runtime event journal.

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
