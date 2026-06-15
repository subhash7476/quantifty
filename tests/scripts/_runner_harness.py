"""
Shared harness for the MM7E composition-root net (tests/scripts/).

Not a test module (no test_ prefix). Mirrors tests/runtime/_doubles.py: it gives
the composition / refusal / activation-path suites the MM7C/MM7D.1 isolation
construction (monkeypatch handler_mod.ExecutionStore -> tmp; Finding E1-a) plus a
tmp-isolated DatabaseManager, a FakeMarketDataProvider, a fixture instrument
master, and two minimal SignalSources (a no-op gate driver and a BUY/EXIT spine
driver) so the production root scripts.fno_runner.build_runner can be exercised
end-to-end WITHOUT touching real data files, the real live provider, or
RealTimeClock.sleep.

ZERO production placement: the synthetic sources live here, under tests/, so
MM7E's Design B (inject the source, never construct one) is honoured by the net
itself.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import List

import pytz

_REPO_ROOT = Path(__file__).resolve().parents[2]
# pytest prepends each test file's OWN dir to sys.path, so tests/runtime/_doubles
# is not otherwise importable from tests/scripts/.
sys.path.insert(0, str(_REPO_ROOT / "tests" / "runtime"))

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.execution.handler import ExecutionMode
from core.execution.persistence.execution_store import ExecutionStore
from core.events import OHLCVBar, SignalEvent, SignalType
from core.runtime.signal_source import SignalSource

import scripts.fno_runner as fno_runner

from _doubles import FakeMarketDataProvider, bar_series

EQUITY = "NSE_EQ|INE002A01018"
DERIV = "NSE_FO|53001"
CLOSE = 2500.0
# A real, fixed clock time: the handler's recovery + metrics persistence call
# clock.now() at construction (handler.py:217,259), so a None-returning FakeClock
# is unusable here — ReplayClock supplies a real now() and a no-op sleep (so the
# Mode.LIVE no-bar poll never really sleeps), exactly as MM7D.1 used.
FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
SL_DISTANCE = 5.0
RISK_R = 1.0
QTY = 50


class NoopSource(SignalSource):
    """Emits nothing — drives the startup gate without any trading (so the F&O
    activation path can fire readiness->canonicalize->reconcile on the restored
    ledger without sizing a derivative order, keeping F4 out of MM7E)."""

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        return []


class BuyExitSource(SignalSource):
    """Call-indexed BUY-then-EXIT over one symbol (MM7D.1 SyntheticBuyExitSource,
    test-local). Ledger-blind, market-data-free; emits on call index."""

    def __init__(self, symbol: str = EQUITY):
        self._symbol = symbol
        self.calls = 0

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        i = self.calls
        self.calls += 1
        if i == 0:
            return [SignalEvent(
                strategy_id="syn", symbol=self._symbol, timestamp=bar.timestamp,
                signal_type=SignalType.BUY, confidence=1.0,
                metadata={"sl_distance": SL_DISTANCE, "risk_r": RISK_R, "quantity": QTY})]
        if i == 1:
            return [SignalEvent(
                strategy_id="syn", symbol=self._symbol, timestamp=bar.timestamp,
                signal_type=SignalType.EXIT, confidence=1.0, metadata={})]
        return []


def isolate_store(tmp_path, monkeypatch) -> DatabaseManager:
    """The MM7C/MM7D.1 isolation: redirect the handler's hardcoded ExecutionStore
    to tmp/execution.db (Finding E1-a — no DI seam for the store path) and hand
    back a tmp-rooted DatabaseManager (singleton reset first for hermeticity)."""
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")))
    DatabaseManager.reset_instance()
    return DatabaseManager(data_root=tmp_path)


def make_master(tmp_path, underlying: str = "NIFTY") -> Path:
    """A freshly-materialized single-snapshot master (today -> FRESH), via the
    production parse_instruments + write_snapshot path (T4 fixture pattern)."""
    from scripts.fetch_instrument_master import parse_instruments, write_snapshot
    from core.instruments.master_freshness import expected_snapshot_date
    from core.database.utils.market_hours import MarketHours

    today = expected_snapshot_date(MarketHours.get_ist_now()).isoformat()
    master = tmp_path / "instruments.duckdb"
    write_snapshot(parse_instruments([
        {"segment": "NSE_FO", "instrument_key": DERIV, "tradingsymbol": "NIFTYFUT",
         "name": underlying, "expiry": "2027-12-31", "instrument_type": "FUT",
         "lot_size": 75, "tick_size": 5},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|54710", "tradingsymbol": "NIFTYCE",
         "name": underlying, "expiry": "2027-12-31", "strike_price": 22500.0,
         "instrument_type": "CE", "lot_size": 75, "tick_size": 5},
    ], today), db_path=master)
    return master


def build(tmp_path, monkeypatch, *, source, symbols=(EQUITY,), underlyings=None,
          execution_mode=ExecutionMode.PAPER, broker=None,
          broker_positions=lambda: [],
          master_db_path=None, max_bars=3, n_bars=3, journal=None):
    """Construct a driver through the production root with the isolation seams
    injected. Production callers pass only source/symbols/underlyings; the net
    injects clock/provider/db_manager/metrics_path so nothing real is touched."""
    dbm = isolate_store(tmp_path, monkeypatch)
    provider = FakeMarketDataProvider(
        {symbols[0]: bar_series(symbols[0], n_bars, close=CLOSE)}, live=True)
    return fno_runner.build_runner(
        source=source, symbols=list(symbols), underlyings=underlyings,
        execution_mode=execution_mode, broker=broker,
        broker_positions=broker_positions,
        master_db_path=master_db_path, clock=ReplayClock(FIXED_DT), provider=provider,
        db_manager=dbm, metrics_path=str(tmp_path / "metrics.json"),
        journal=journal, max_bars=max_bars)
