# MM13 — Knowledge-Consuming SignalSource Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the `Knowledge → [Strategy]` arrow — a `KnowledgeObject` from `DRAOrchestrator` drives a `SignalSource` through `GuardedSignalSource → ExecutionHandler → PaperBroker`, proven by an integration test.

**Architecture:** One new strategy (`KnowledgeSignalSource`) reads a cached `KnowledgeObject` and emits a single contract-valid BUY. One new composition-root factory (`build_msi_paper_runner`) wires the six real DRA collaborators + the source into the existing `fno_runner.build_runner` in PAPER mode. An integration test drives the whole stack with `FakeMarketDataProvider` fed real 1m bars and asserts the runtime telemetry counters.

**Tech Stack:** Python 3.10+, DuckDB, pytest. Reuses `core/msi/dra/*`, `core/runtime/*`, `scripts/fno_runner.py`, `tests/runtime/_doubles.py`.

**Spec:** `docs/superpowers/specs/2026-07-06-mm13-knowledge-signalsource-design.md`

## Global Constraints

- **PAPER only** — `ExecutionMode.PAPER`; never LIVE.
- **No changes to frozen files, `scripts/fno_runner.py`, or `core/runtime/guarded_signal_source.py`** — MM13 only consumes seams.
- **Strategies Stay Dumb (Principle 1)** — the source emits `SignalEvent` only; no broker/sizing/risk logic. `sl_distance`/`risk_r` are *declarations*, not sizing.
- **Signal contract (guard drops violators as `SIGNAL_CONTRACT_REJECTED`)** — every BUY MUST have `signal.timestamp == bar.timestamp`, `metadata["sl_distance"]` numeric `> 0`, `metadata["risk_r"]` numeric `> 0`.
- **Scope fence — do NOT build:** persistent Knowledge store (`data/msi/knowledge.duckdb`), multi-file/90-day-spanning observation reader, validation harness, real-artifact authoring, EXIT/regime-transition logic, live/real-provider CLI entrypoint.
- **Conventions** — no docstrings/comments on unchanged code; no over-engineering; prefer editing existing files; frequent commits.

**Fixed values (verified against the copied data):**
- Traded equity: `NSE_EQ|INE139A01034` (full 1m coverage on 2026-02-27).
- Regime inputs: `NSE_INDEX|Nifty 50` + `NSE_INDEX|India VIX` (read by the DRA from the 1d file).
- Evaluation date: `date(2026, 2, 27)`.
- 1d observation DB: `data/market_data/nse/candles/1d/2026-02-27.duckdb`.
- 1m bars DB: `data/market_data/nse/candles/1m/2026-02-27.duckdb`.
- Artifact dir: `tests/msi/fixtures/test_artifact` (experimental fixture — permitted for a PAPER proof).

---

### Task 1: `KnowledgeSignalSource` — the first concrete strategy

**Files:**
- Create: `core/strategies/__init__.py`
- Create: `core/strategies/knowledge_signal_source.py`
- Create: `tests/strategies/test_knowledge_signal_source.py`

**Interfaces:**
- Consumes: `core.runtime.signal_source.SignalSource`, `core.events.{OHLCVBar, SignalEvent, SignalType}`, and a duck-typed `orchestrator` with `run(evaluation_date: date, artifact_ref: str) -> KnowledgeObject`.
- Produces: `KnowledgeSignalSource(orchestrator, evaluation_date: date, artifact_ref: str, traded_symbol: str, latent_variable: str = "market_regime", strategy_id: str = "mm13_knowledge_reader", sl_frac: float = 0.01, risk_r: float = 1.0)` with `on_start(context=None) -> None` and `on_bar(bar) -> List[SignalEvent]`.

- [ ] **Step 1: Write the failing test**

Create `tests/strategies/test_knowledge_signal_source.py`:

```python
from datetime import date, datetime
from typing import Optional

from core.events import OHLCVBar, SignalType
from core.msi.contracts.estimate import Estimate
from core.msi.contracts.knowledge import KnowledgeObject
from core.msi.contracts.market_state import MarketState
from core.strategies.knowledge_signal_source import KnowledgeSignalSource

_TS = datetime(2026, 2, 27, 9, 15)
TRADED = "NSE_EQ|INE139A01034"


def _knowledge(regime_value: Optional[float], latent: str = "market_regime") -> KnowledgeObject:
    estimates = ()
    if regime_value is not None:
        estimates = (Estimate(latent_variable=latent, value=regime_value,
                              uncertainty=0.15, dimension="regime_class"),)
    ms = MarketState(evaluation_timestamp=_TS, estimates=estimates)
    return KnowledgeObject(
        knowledge_id="k-1", evaluation_timestamp=_TS, artifact_version="v1.0.0",
        runtime_version="msi-v1.0", market_state=ms, provenance_reference="prov-1")


class _StubOrch:
    def __init__(self, knowledge: KnowledgeObject):
        self._knowledge = knowledge
        self.calls = 0

    def run(self, evaluation_date, artifact_ref):
        self.calls += 1
        return self._knowledge


def _bar(ts=_TS, close=357.4) -> OHLCVBar:
    return OHLCVBar(symbol=TRADED, timestamp=ts, open=close, high=close,
                    low=close, close=close, volume=1000)


def _source(regime_value=0.0):
    orch = _StubOrch(_knowledge(regime_value))
    src = KnowledgeSignalSource(orch, date(2026, 2, 27), "artifact/ref",
                                traded_symbol=TRADED)
    return src, orch


def test_on_start_runs_dra_once_and_caches_regime():
    src, orch = _source(regime_value=2.0)
    src.on_start()
    assert orch.calls == 1


def test_no_signal_before_on_start():
    src, _ = _source()
    assert src.on_bar(_bar()) == []


def test_emits_one_contract_valid_buy_on_first_bar():
    src, _ = _source(regime_value=0.0)
    src.on_start()
    out = src.on_bar(_bar())
    assert len(out) == 1
    sig = out[0]
    assert sig.signal_type is SignalType.BUY
    assert sig.symbol == TRADED
    assert sig.timestamp == _TS
    assert float(sig.metadata["sl_distance"]) > 0
    assert float(sig.metadata["risk_r"]) > 0
    assert sig.metadata["knowledge_id"] == "k-1"
    assert sig.metadata["regime_value"] == 0.0


def test_single_emit_then_silent():
    src, _ = _source()
    src.on_start()
    assert len(src.on_bar(_bar())) == 1
    assert src.on_bar(_bar(ts=datetime(2026, 2, 27, 9, 16))) == []


def test_no_emit_when_selected_estimate_absent():
    orch = _StubOrch(_knowledge(regime_value=None))
    src = KnowledgeSignalSource(orch, date(2026, 2, 27), "ref", traded_symbol=TRADED)
    src.on_start()
    assert src.on_bar(_bar()) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/strategies/test_knowledge_signal_source.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.strategies.knowledge_signal_source'`.

- [ ] **Step 3: Create the package marker**

Create `core/strategies/__init__.py` (empty file).

- [ ] **Step 4: Write minimal implementation**

Create `core/strategies/knowledge_signal_source.py`:

```python
from datetime import date
from typing import Any, List, Optional

from core.events import OHLCVBar, SignalEvent, SignalType
from core.runtime.signal_source import SignalSource


class KnowledgeSignalSource(SignalSource):
    """First Knowledge-consuming SignalSource (MM13). Runs the DRA once at
    on_start, caches the KnowledgeObject, and emits a single contract-valid BUY
    on the first bar. Reads the estimate named by `latent_variable`; emits
    nothing if that estimate is absent. Stays dumb (Principle 1): sl_distance
    and risk_r are declarations, not sizing.
    """

    def __init__(self, orchestrator, evaluation_date: date, artifact_ref: str,
                 traded_symbol: str, latent_variable: str = "market_regime",
                 strategy_id: str = "mm13_knowledge_reader",
                 sl_frac: float = 0.01, risk_r: float = 1.0):
        self._orchestrator = orchestrator
        self._evaluation_date = evaluation_date
        self._artifact_ref = artifact_ref
        self._traded_symbol = traded_symbol
        self._latent_variable = latent_variable
        self._strategy_id = strategy_id
        self._sl_frac = sl_frac
        self._risk_r = risk_r
        self._knowledge = None
        self._regime_value: Optional[float] = None
        self._emitted = False

    def on_start(self, context: Optional[Any] = None) -> None:
        self._knowledge = self._orchestrator.run(
            self._evaluation_date, self._artifact_ref)
        self._regime_value = self._select_estimate_value(self._knowledge)

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        if self._knowledge is None or self._regime_value is None or self._emitted:
            return []
        self._emitted = True
        return [SignalEvent(
            strategy_id=self._strategy_id,
            symbol=self._traded_symbol,
            timestamp=bar.timestamp,
            signal_type=SignalType.BUY,
            confidence=0.9,
            metadata={
                "signal_id": f"MM13-{bar.timestamp.isoformat()}",
                "entry_price": bar.close,
                "sl_distance": round(bar.close * self._sl_frac, 2),
                "risk_r": self._risk_r,
                "knowledge_id": self._knowledge.knowledge_id,
                "latent_variable": self._latent_variable,
                "regime_value": self._regime_value,
            },
        )]

    def _select_estimate_value(self, knowledge) -> Optional[float]:
        for estimate in knowledge.market_state.estimates:
            if estimate.latent_variable == self._latent_variable:
                return estimate.value
        return None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/strategies/test_knowledge_signal_source.py -q`
Expected: PASS (5 passed).

- [ ] **Step 6: Commit**

```bash
git add core/strategies/__init__.py core/strategies/knowledge_signal_source.py tests/strategies/test_knowledge_signal_source.py
git commit -m "feat(mm13): KnowledgeSignalSource — first Knowledge-consuming SignalSource"
```

---

### Task 2: `build_msi_paper_runner` composition root + end-to-end integration proof

**Files:**
- Create: `scripts/msi_paper_runner.py`
- Create: `tests/msi/test_mm13_integration.py`

**Interfaces:**
- Consumes: `KnowledgeSignalSource` (Task 1); the six DRA collaborators in `core/msi/dra/*`; `scripts.fno_runner.build_runner`; `tests/runtime/_doubles.py::FakeMarketDataProvider`.
- Produces: `build_dra_orchestrator(obs_db_path: str) -> DRAOrchestrator` and `build_msi_paper_runner(*, traded_symbol, evaluation_date, artifact_ref, obs_db_path, provider, clock, telemetry=None, db_manager=None, max_bars=None, latent_variable="market_regime") -> LoopDriver`.

- [ ] **Step 1: Write the failing integration test**

Create `tests/msi/test_mm13_integration.py`:

```python
import sys
from datetime import date
from pathlib import Path

import duckdb
import pytest

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import OHLCVBar
from core.execution.persistence.execution_store import ExecutionStore
from core.runtime.metrics import InMemoryTelemetrySink, RuntimeMetric

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from _doubles import FakeMarketDataProvider  # sanctioned driver-test provider

from scripts.msi_paper_runner import build_msi_paper_runner

REPO = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = str(REPO / "tests" / "msi" / "fixtures" / "test_artifact")
OBS_DB = str(REPO / "data" / "market_data" / "nse" / "candles" / "1d" / "2026-02-27.duckdb")
BARS_DB = str(REPO / "data" / "market_data" / "nse" / "candles" / "1m" / "2026-02-27.duckdb")
EVAL_DATE = date(2026, 2, 27)
TRADED = "NSE_EQ|INE139A01034"


def _real_bars(n=5):
    rows = duckdb.connect(BARS_DB, read_only=True).execute(
        "SELECT timestamp,open,high,low,close,volume FROM candles "
        "WHERE symbol=? ORDER BY timestamp ASC LIMIT ?", [TRADED, n]).fetchall()
    return [OHLCVBar(symbol=TRADED, timestamp=r[0], open=float(r[1]),
                     high=float(r[2]), low=float(r[3]), close=float(r[4]),
                     volume=int(r[5] or 0)) for r in rows]


@pytest.mark.skipif(not Path(OBS_DB).exists() or not Path(BARS_DB).exists(),
                    reason="real candle store not present in this tree")
def test_knowledge_derived_signal_routes_to_broker(tmp_path, monkeypatch):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")))
    DatabaseManager.reset_instance()
    dbm = DatabaseManager(data_root=str(tmp_path))

    bars = _real_bars(5)
    provider = FakeMarketDataProvider({TRADED: bars})
    clock = ReplayClock(bars[0].timestamp)
    sink = InMemoryTelemetrySink()

    driver = build_msi_paper_runner(
        traded_symbol=TRADED, evaluation_date=EVAL_DATE, artifact_ref=ARTIFACT_DIR,
        obs_db_path=OBS_DB, provider=provider, clock=clock,
        telemetry=sink, db_manager=dbm, max_bars=5)
    driver.run()

    assert sink.get(RuntimeMetric.SIGNALS_RECEIVED) == 1
    assert sink.get(RuntimeMetric.SIGNALS_ROUTED) == 1
    assert sink.get(RuntimeMetric.EXECUTION_CALLS) == 1
    assert sink.get(RuntimeMetric.SIGNAL_CONTRACT_REJECTIONS) == 0
    assert driver._source.quarantined is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/msi/test_mm13_integration.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.msi_paper_runner'`.

- [ ] **Step 3: Write the composition root**

Create `scripts/msi_paper_runner.py`:

```python
"""MM13 composition root — the first script to import core.msi.

Wires the six real DRA collaborators + a DRAOrchestrator into a
KnowledgeSignalSource, then injects that source into fno_runner.build_runner in
PAPER mode. The caller supplies the bar provider + clock (the proof injects a
FakeMarketDataProvider fed real bars); this factory does not construct a live
provider. Scope-fenced per docs/superpowers/specs/2026-07-06-mm13-*.md.
"""

from datetime import date
from typing import Optional

from core.clock import Clock
from core.database.manager import DatabaseManager
from core.database.providers.base import MarketDataProvider
from core.execution.handler import ExecutionMode
from core.msi.dra.default_artifact_evaluator import DefaultArtifactEvaluator
from core.msi.dra.default_evidence_builder import DefaultEvidenceBuilder
from core.msi.dra.default_knowledge_builder import DefaultKnowledgeBuilder
from core.msi.dra.default_knowledge_publisher import DefaultKnowledgePublisher
from core.msi.dra.duckdb_observation_reader import DuckDBObservationReader
from core.msi.dra.filesystem_artifact_loader import FilesystemArtifactLoader
from core.msi.dra.knowledge_repository import KnowledgeRepository
from core.msi.dra.orchestrator import DRAOrchestrator
from core.runtime.driver import LoopDriver
from core.runtime.metrics import TelemetrySink
from core.strategies.knowledge_signal_source import KnowledgeSignalSource

import scripts.fno_runner as fno_runner


def build_dra_orchestrator(obs_db_path: str) -> DRAOrchestrator:
    return DRAOrchestrator(
        observation_reader=DuckDBObservationReader(obs_db_path),
        evidence_builder=DefaultEvidenceBuilder(),
        artifact_loader=FilesystemArtifactLoader(),
        artifact_evaluator=DefaultArtifactEvaluator(),
        knowledge_builder=DefaultKnowledgeBuilder(),
        knowledge_publisher=DefaultKnowledgePublisher(KnowledgeRepository()),
    )


def build_msi_paper_runner(
    *,
    traded_symbol: str,
    evaluation_date: date,
    artifact_ref: str,
    obs_db_path: str,
    provider: MarketDataProvider,
    clock: Clock,
    telemetry: Optional[TelemetrySink] = None,
    db_manager: Optional[DatabaseManager] = None,
    max_bars: Optional[int] = None,
    latent_variable: str = "market_regime",
) -> LoopDriver:
    orchestrator = build_dra_orchestrator(obs_db_path)
    source = KnowledgeSignalSource(
        orchestrator=orchestrator,
        evaluation_date=evaluation_date,
        artifact_ref=artifact_ref,
        traded_symbol=traded_symbol,
        latent_variable=latent_variable,
    )
    return fno_runner.build_runner(
        source=source,
        symbols=[traded_symbol],
        execution_mode=ExecutionMode.PAPER,
        provider=provider,
        clock=clock,
        db_manager=db_manager,
        telemetry=telemetry,
        max_bars=max_bars,
    )
```

- [ ] **Step 4: Run the integration test to verify it passes**

Run: `python -m pytest tests/msi/test_mm13_integration.py -q`
Expected: PASS (1 passed). This asserts the Knowledge-derived signal is received, routed, and reaches `process_signal` (`EXECUTION_CALLS == 1`), was not rejected by the guard (`SIGNAL_CONTRACT_REJECTIONS == 0`), and the source was not quarantined.

- [ ] **Step 5: Run the full MSI + strategies suite to confirm no regression**

Run: `python -m pytest tests/msi tests/strategies -q`
Expected: PASS (existing MSI tests + the new tests, all green).

- [ ] **Step 6: Commit**

```bash
git add scripts/msi_paper_runner.py tests/msi/test_mm13_integration.py
git commit -m "feat(mm13): msi_paper_runner composition root + end-to-end PAPER proof"
```

---

### Task 3: Knowledge-base sync — record MM13 completion

**Files:**
- Modify: `docs/PROJECT_STATE.md` (MM13 Planned → Complete)
- Modify: the repo's changelog file (confirm exact path in Step 1)

- [ ] **Step 1: Locate the state/changelog files**

Run: `ls docs/PROJECT_STATE.md docs/CHANGELOG.md 2>/dev/null; git log --oneline -5`
Expected: confirm the exact filenames the repo uses for project state and changelog (adjust the paths below if they differ).

- [ ] **Step 2: Update PROJECT_STATE**

In `docs/PROJECT_STATE.md`, move the MM13 entry from Planned to Complete with a one-line summary: "MM13 — first Knowledge-consuming SignalSource (`KnowledgeSignalSource`) proven end-to-end through `fno_runner` in PAPER via `scripts/msi_paper_runner.py`; Knowledge→[Strategy] arrow closed. Axis 2 (validation harness, real artifact) unchanged downstream."

- [ ] **Step 3: Update the changelog**

Add a dated MM13 entry mirroring the PROJECT_STATE summary.

- [ ] **Step 4: Commit**

```bash
git add docs/PROJECT_STATE.md docs/CHANGELOG.md
git commit -m "docs(mm13): mark MM13 complete — Knowledge→Strategy arrow closed"
```

---

## Definition of Done

- `tests/strategies/test_knowledge_signal_source.py` and `tests/msi/test_mm13_integration.py` pass.
- `python -m pytest tests/msi tests/strategies -q` is green.
- A script (`scripts/msi_paper_runner.py`) imports `core.msi` and runs `DRAOrchestrator` outside a test — the "DRA is wired to nothing" gap is closed.
- No frozen file, `fno_runner.py`, or `guarded_signal_source.py` was modified.
