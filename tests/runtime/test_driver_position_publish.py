"""
Unit tests for LoopDriver Phase H.3 — Position Publishing (§10.4).

The driver publishes a positions snapshot on `telemetry.positions.{node}` over
the injected RuntimeTelemetryPublisher, on the SAME cadence and best-effort
contract as H.1 metrics / H.2 health. The payload is a READ-ONLY projection of
ledger truth — `execution.position_tracker.get_all_positions()` — and computes
no PnL (per-position `pnl_pct` is a documented placeholder until live MTM,
§10.4). Read-only consumer of the ledger (ADR-001); never mutates trackers.

Proven here:
1. positions are published during a run, with the documented per-position schema;
2. publishing follows the same cadence as metrics, and is throttled by interval;
3. without an ExecutionHandler the driver still publishes (an empty book);
4. building the payload never mutates the position tracker (read-only);
5. a transport failure on positions publish is non-fatal (loop survives);
6. the positions projection is deterministic across identical runs.

No real network: a FakeTelemetryTransport double records calls; the real
RuntimeTelemetryPublisher + InMemoryTelemetrySink are used (real code).
"""

from datetime import datetime

import pytz

from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.metrics import InMemoryTelemetrySink
from core.runtime.telemetry_publisher import RuntimeTelemetryPublisher

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeTelemetryTransport, bar_series)

_UTC = pytz.UTC
_START = datetime(2026, 6, 5, 9, 15, tzinfo=_UTC)
_POSITION_KEYS = {"quantity", "avg_price", "side", "pnl_pct"}


def _replay_cfg(max_bars=None, tel_interval=0.0):
    return DriverConfig(mode=Mode.REPLAY, symbols=["A"], max_bars=max_bars,
                        telemetry_interval_s=tel_interval)


def _open(handler, symbol, side, quantity, avg_price):
    handler.position_tracker._positions[symbol] = Position(
        instrument=Equity(symbol), side=side, quantity=quantity, avg_price=avg_price)


def _driver(cfg, transport, execution=None):
    sink = InMemoryTelemetrySink()
    pub = RuntimeTelemetryPublisher(transport, sink)
    return LoopDriver(cfg, clock=FakeClock(),
                      provider=FakeMarketDataProvider({"A": bar_series("A", 4, start=_START)}),
                      execution=execution, telemetry=sink, publisher=pub)


# --------------------------------------------------------------------------- #
# (1) positions are published during a run, with the documented schema
# --------------------------------------------------------------------------- #
def test_positions_payload_published_with_documented_schema():
    transport = FakeTelemetryTransport()
    handler = FakeExecutionHandler()
    _open(handler, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    _driver(_replay_cfg(max_bars=3), transport, execution=handler).run()

    assert transport.published_positions                       # positions published
    last = transport.published_positions[-1]
    assert set(last) == {"RELIANCE"}
    assert set(last["RELIANCE"]) == _POSITION_KEYS             # exact per-position schema
    assert last["RELIANCE"]["quantity"] == 10
    assert last["RELIANCE"]["avg_price"] == 2500.0
    assert last["RELIANCE"]["side"] == "LONG"
    assert last["RELIANCE"]["pnl_pct"] == 0.0                  # placeholder (§10.4 gap)


# --------------------------------------------------------------------------- #
# (1b) the payload reflects the full multi-position book (read straight from
#      get_all_positions — no filtering, no new logic)
# --------------------------------------------------------------------------- #
def test_build_positions_reflects_full_book():
    transport = FakeTelemetryTransport()
    handler = FakeExecutionHandler()
    _open(handler, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    _open(handler, "TCS", PositionSide.SHORT, 5, 3500.0)
    d = _driver(_replay_cfg(max_bars=2), transport, execution=handler)

    payload = d._build_positions()

    assert set(payload) == {"RELIANCE", "TCS"}
    assert payload["TCS"]["side"] == "SHORT"
    assert payload["TCS"]["quantity"] == 5


# --------------------------------------------------------------------------- #
# (2) positions publish on the SAME cadence as metrics; throttled by interval
# --------------------------------------------------------------------------- #
def test_positions_publish_on_the_same_cadence_as_metrics():
    transport = FakeTelemetryTransport()
    handler = FakeExecutionHandler()
    _open(handler, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    _driver(_replay_cfg(max_bars=3, tel_interval=0.0), transport, execution=handler).run()

    assert (len(transport.published_positions)
            == len(transport.published)
            == len(transport.published_health) == 3)


def test_positions_publish_is_throttled_by_interval():
    transport = FakeTelemetryTransport()
    handler = FakeExecutionHandler()
    _open(handler, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    _driver(_replay_cfg(max_bars=3, tel_interval=10_000.0), transport, execution=handler).run()

    assert len(transport.published_positions) == 1             # only the first tick


# --------------------------------------------------------------------------- #
# (3) without an ExecutionHandler the driver still publishes an empty book
# --------------------------------------------------------------------------- #
def test_positions_empty_without_execution_handler():
    transport = FakeTelemetryTransport()
    d = _driver(_replay_cfg(max_bars=2), transport, execution=None)
    d.run()

    assert d.state is RuntimeState.STOPPED
    assert transport.published_positions                       # still published
    assert transport.published_positions[-1] == {}             # empty book


# --------------------------------------------------------------------------- #
# (4) building the payload is read-only — the tracker is never mutated
# --------------------------------------------------------------------------- #
def test_build_positions_does_not_mutate_tracker():
    transport = FakeTelemetryTransport()
    handler = FakeExecutionHandler()
    _open(handler, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    d = _driver(_replay_cfg(max_bars=2), transport, execution=handler)

    before = handler.position_tracker.get_all_positions()
    d._build_positions()

    assert handler.position_tracker.get_all_positions() == before
    assert handler.position_tracker.get_all_positions()["RELIANCE"].quantity == 10


# --------------------------------------------------------------------------- #
# (5) a transport failure on positions publish is non-fatal
# --------------------------------------------------------------------------- #
def test_positions_transport_failure_is_non_fatal():
    transport = FakeTelemetryTransport(fail=True)              # every publish raises
    handler = FakeExecutionHandler()
    _open(handler, "RELIANCE", PositionSide.LONG, 10, 2500.0)
    d = _driver(_replay_cfg(max_bars=2, tel_interval=0.0), transport, execution=handler)
    d.run()

    assert d.state is RuntimeState.STOPPED                     # loop survived
    assert d.bars_processed == 2
    assert transport.published_positions == []                 # failure swallowed


# --------------------------------------------------------------------------- #
# (6) the positions projection is deterministic across identical runs
# --------------------------------------------------------------------------- #
def test_positions_projection_is_deterministic_across_runs():
    def run_once():
        transport = FakeTelemetryTransport()
        handler = FakeExecutionHandler()
        _open(handler, "RELIANCE", PositionSide.LONG, 10, 2500.0)
        _open(handler, "TCS", PositionSide.SHORT, 5, 3500.0)
        _driver(_replay_cfg(max_bars=2, tel_interval=0.0), transport, execution=handler).run()
        return transport.published_positions

    assert run_once() == run_once()
