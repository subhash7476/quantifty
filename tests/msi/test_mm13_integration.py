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

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests" / "runtime"))
from _doubles import FakeMarketDataProvider

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
