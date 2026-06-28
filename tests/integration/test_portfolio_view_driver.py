"""
Block C — Integration: handler fill → driver telemetry has Greek payload (MM9.3-S2).

C1 drives a real ExecutionHandler (PaperBroker) through a fill-adjacent path,
wires the result into a LoopDriver with PortfolioView, and asserts the enriched
payload reaches the telemetry transport with a non-zero Greek exposure.

PaperBroker.place_order() returns a broker_id but does NOT invoke the fill
callback synchronously (paper_broker.py:26-43). Therefore process_signal warms
the price cache and returns a NormalizedOrder but does NOT populate the position
tracker. As a documented limitation, C1 seeds a real Position in the tracker's
`_positions` dict after process_signal — the position itself is not being tested;
the telemetry pipeline's ability to aggregate and publish Greeks IS.
"""

from datetime import datetime

import pytz

import core.execution.handler as handler_mod
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.position_models import Position, PositionSide
from core.execution.portfolio_view import PortfolioView
from core.instruments.equity import Equity
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.runtime.metrics import InMemoryTelemetrySink
from core.runtime.telemetry_publisher import RuntimeTelemetryPublisher


FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


class _SpyTransport:
    """Minimal FakeTelemetryTransport stand-in for the integration test."""
    def __init__(self):
        self.published_positions = []
    def publish_metrics(self, data): pass
    def publish_health(self, data): pass
    def publish_positions(self, data):
        self.published_positions.append(data)
    def publish_log(self, level, msg): pass
    def close(self): pass


def test_driver_publishes_greek_exposure_on_telemetry_cadence(tmp_path, monkeypatch):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(mode=ExecutionMode.PAPER),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
    )

    # Submit a buy signal — process_signal warms the price cache and validates
    # the signal flows through all gates correctly.
    signal = SignalEvent(
        strategy_id="test_strat",
        symbol="NSE_EQ|INE001",
        timestamp=FIXED_DT,
        signal_type=SignalType.BUY,
        confidence=0.9,
        metadata={"signal_id": "SIG-C1", "entry_price": 100.0},
    )
    result = handler.process_signal(signal, current_price=100.0)
    assert result is not None, "process_signal must accept the test signal"

    # Populate price cache (warmed by process_signal via update_market_price)
    assert "NSE_EQ|INE001" in handler._price_cache

    # Seed a real equity position in the tracker (PaperBroker does not invoke
    # the fill callback; see module docstring).
    handler.position_tracker._positions["NSE_EQ|INE001"] = Position(
        instrument=Equity("NSE_EQ|INE001"),
        side=PositionSide.LONG,
        quantity=100,
        avg_price=100.0,
    )

    # Build PortfolioView from the handler's existing PortfolioGreeks instance
    pv = PortfolioView(
        position_tracker=handler.position_tracker,
        pnl_tracker=handler.pnl_tracker,
        margin_tracker=handler.margin_tracker,
        portfolio_greeks=handler.portfolio_greeks,
    )

    # Wire LoopDriver with a spy transport
    transport = _SpyTransport()
    sink = InMemoryTelemetrySink()
    pub = RuntimeTelemetryPublisher(transport, sink)

    cfg = DriverConfig(mode=Mode.REPLAY, symbols=["NSE_EQ|INE001"],
                       telemetry_interval_s=0.0)
    driver = LoopDriver(
        cfg,
        clock=clock,
        execution=handler,
        telemetry=sink,
        publisher=pub,
        portfolio_view=pv,
    )

    # Drive telemetry — publishes positions including the enriched portfolio data
    driver._drive_telemetry()

    assert transport.published_positions, "telemetry must have been published"
    payload = transport.published_positions[-1]
    assert "_portfolio_summary" in payload, (
        "enriched path must include _portfolio_summary"
    )
    pg = payload["_portfolio_summary"]["portfolio_greeks"]
    assert pg["delta"] > 0, "an equity long position must have positive delta"
