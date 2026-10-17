"""
The live order path through a REAL UpstoxAdapter (F-UPX-1/2/3; README audit L1, L3, L4).

The live-rung tests (tests/scripts/test_fno_runner_live_rung.py) wire the driver
around a MagicMock broker, which answers any attribute. So a live run that could
not be built (UpstoxAdapter had no subscribe_fills), an order that raised on
signal_id_reference before any HTTP call, a payload that sent every order as SELL,
and fills that nothing ever fetched all passed there. Here the adapter is real and
only its HTTP layer is stubbed (_upstox_http.py). An unrouted call fails the test,
so no test can reach Upstox.
"""

import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytz
import requests

import core.execution.handler as handler_mod
from core.brokers.mapping.upstox import UpstoxMapping
from core.brokers.upstox_adapter import (BrokerContractError, BrokerOrderNotFilledError,
                                         BrokerUnavailableError, UpstoxAdapter)
from core.clock import ReplayClock
from core.events import OrderStatus as BrokerOrderStatus
from core.events import SignalEvent, SignalType
from core.execution.handler import ExecutionMode
from core.execution.order_lifecycle import FillEvent, OrderStatus
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
from core.execution.portfolio.trade_recorder import TradeRecorder
from core.runtime.signal_source import SignalSource

import scripts.fno_runner as fno_runner
from tests.brokers._upstox_http import install, order_details, placed

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _runner_harness import EQUITY, NoopSource, build  # noqa: E402

NOW = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
BROKER_ID = "231019025562880"


def _adapter(tmp_path):
    adapter = UpstoxAdapter("key", "secret", "token", ReplayClock(NOW))
    adapter._req_interval = 0
    # Equity orders never consult the mapping; an absent master keeps place_order
    # from opening the operator's real instrument master.
    adapter._mapping = UpstoxMapping(db_path=tmp_path / "no_master.duckdb")
    return adapter


def _order(side=OrderSide.BUY, quantity=50, signal_id="sig-live-1"):
    return NormalizedOrder(symbol=EQUITY, side=side, quantity=quantity,
                           order_type=OrderType.MARKET, strategy_id="live",
                           signal_id=signal_id, timestamp=NOW)


def _details(status, *, quantity, filled, average_price, status_message=None):
    return order_details(BROKER_ID, status, quantity=quantity, filled=filled,
                         average_price=average_price, instrument_token=EQUITY,
                         transaction_type="BUY", status_message=status_message)


def _placed_adapter(tmp_path, monkeypatch, order, *details):
    """A real adapter that has placed `order`, with the fill callback recording."""
    http = install(monkeypatch)
    http.route("POST", "/order/place", placed(BROKER_ID))
    if details:
        http.route("GET", "/order/details", *details)
    adapter = _adapter(tmp_path)
    fills = []
    adapter.subscribe_fills(fills.append)
    adapter.place_order(order)
    return adapter, http, fills


def _patch_live_creds(monkeypatch):
    creds = MagicMock()
    creds.has_upstox_token = True
    creds.is_token_expired = False
    monkeypatch.setattr(fno_runner, "_live_credentials", creds)


def _bootstrap_trades(db_manager):
    """fno_runner doesn't create the trades table (the NiftyShield session does,
    scripts/nifty_shield_paper/session.py); a fresh tmp db needs it."""
    from core.database.schema import TRADING_TRADES_SCHEMA, TRADING_TRADE_CONTEXT_SCHEMA
    with db_manager.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)
        conn.execute(TRADING_TRADE_CONTEXT_SCHEMA)


def _trades(db_manager):
    with db_manager.trading_reader() as conn:
        return conn.execute(
            "SELECT signal_id, symbol, side, quantity, entry_price FROM trades").fetchall()


def _isolate_trade_recorder(tmp_path, monkeypatch):
    monkeypatch.setattr(handler_mod, "TradeRecorder",
                        lambda: TradeRecorder(db_path=str(tmp_path / "ti.duckdb")))


# --------------------------------------------------------------------------- #
# F-UPX-3 / L3 — build_runner builds a LIVE driver around the real adapter
# --------------------------------------------------------------------------- #

def test_build_runner_constructs_live_driver_around_real_upstox_adapter(
        tmp_path, monkeypatch):
    http = install(monkeypatch)
    _patch_live_creds(monkeypatch)
    _isolate_trade_recorder(tmp_path, monkeypatch)
    adapter = _adapter(tmp_path)

    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,),
              execution_mode=ExecutionMode.LIVE, broker=adapter,
              broker_positions=None)

    assert d._execution.broker is adapter
    assert d._execution.config.mode is ExecutionMode.LIVE
    assert adapter._fill_callback == d._execution._handle_broker_fill
    assert http.calls == []  # building the driver touches no endpoint


# --------------------------------------------------------------------------- #
# F-UPX-1 / F-UPX-2 / L1 — the payload a NormalizedOrder produces
# --------------------------------------------------------------------------- #

def test_buy_order_payload_carries_buy_signal_id_tag_and_instrument_key(
        tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "/order/place", placed(BROKER_ID))

    broker_id = _adapter(tmp_path).place_order(_order(OrderSide.BUY))

    assert broker_id == BROKER_ID
    [call] = http.calls_to("POST", "/order/place")
    payload = call["json"]
    assert payload["transaction_type"] == "BUY"
    assert payload["tag"] == "sig-live-1"
    assert payload["instrument_token"] == EQUITY
    assert payload["quantity"] == 50
    assert payload["order_type"] == "MARKET"
    assert payload["price"] == 0
    assert payload["product"] == "I"


def test_sell_order_payload_carries_sell(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "/order/place", placed(BROKER_ID))

    _adapter(tmp_path).place_order(_order(OrderSide.SELL))

    [call] = http.calls_to("POST", "/order/place")
    assert call["json"]["transaction_type"] == "SELL"


def test_unmappable_side_is_refused_before_any_call(tmp_path, monkeypatch):
    """F-UPX-2 was a silent default: anything not equal to "BUY" went out as
    SELL. A side the adapter cannot map must stop the order, not pick one."""
    http = install(monkeypatch)

    with pytest.raises(BrokerContractError, match="side"):
        _adapter(tmp_path).place_order(_order(side="BUY"))

    assert http.calls == []


def test_get_order_status_maps_documented_complete_to_filled(tmp_path, monkeypatch):
    """Upstox reports a filled order as "complete" (order-status appendix); the
    map only knew "completed", so every filled order raised as unknown."""
    http = install(monkeypatch)
    http.route("GET", "/order/details",
               _details("complete", quantity=50, filled=50, average_price=2501.5))

    assert _adapter(tmp_path).get_order_status(BROKER_ID) is BrokerOrderStatus.FILLED


# --------------------------------------------------------------------------- #
# L4 — a filled live order becomes a FillEvent through the subscribed callback
# --------------------------------------------------------------------------- #

def test_filled_order_produces_fill_event_through_subscribed_callback(
        tmp_path, monkeypatch):
    order = _order(OrderSide.BUY, quantity=50)
    adapter, http, fills = _placed_adapter(
        tmp_path, monkeypatch, order,
        _details("complete", quantity=50, filled=50, average_price=2501.5))
    assert fills == []  # placing an order is not a fill

    adapter.poll_fills()

    [fill] = fills
    assert isinstance(fill, FillEvent)
    assert fill.order_id == str(order.correlation_id)  # the handler's key, not Upstox's
    assert fill.symbol == EQUITY
    assert fill.side == "BUY"
    assert fill.quantity == 50.0
    assert fill.price == 2501.5
    assert fill.timestamp == NOW
    assert fill.fee == 0.0
    [call] = http.calls_to("GET", "/order/details")
    assert call["params"] == {"order_id": BROKER_ID}


def test_completed_order_is_not_polled_again(tmp_path, monkeypatch):
    adapter, http, fills = _placed_adapter(
        tmp_path, monkeypatch, _order(),
        _details("complete", quantity=50, filled=50, average_price=2501.5))

    adapter.poll_fills()
    adapter.poll_fills()

    assert len(fills) == 1
    assert len(http.calls_to("GET", "/order/details")) == 1


def test_partial_fills_emit_only_the_new_quantity_at_its_own_price(
        tmp_path, monkeypatch):
    adapter, _, fills = _placed_adapter(
        tmp_path, monkeypatch, _order(quantity=75),
        _details("open", quantity=75, filled=25, average_price=100.0),
        _details("complete", quantity=75, filled=75, average_price=101.0))

    adapter.poll_fills()
    adapter.poll_fills()

    assert [(f.quantity, f.price) for f in fills] == [(25.0, 100.0), (50.0, 101.5)]
    assert fills[0].fill_id != fills[1].fill_id


def test_open_order_with_nothing_filled_stays_pending(tmp_path, monkeypatch):
    adapter, _, fills = _placed_adapter(
        tmp_path, monkeypatch, _order(),
        _details("open", quantity=50, filled=0, average_price=0.0),
        _details("complete", quantity=50, filled=50, average_price=2501.5))

    adapter.poll_fills()
    assert fills == []

    adapter.poll_fills()
    assert [(f.quantity, f.price) for f in fills] == [(50.0, 2501.5)]


def test_rejected_order_emits_nothing_and_is_dropped(tmp_path, monkeypatch, caplog):
    adapter, http, fills = _placed_adapter(
        tmp_path, monkeypatch, _order(),
        _details("rejected", quantity=50, filled=0, average_price=0.0,
                 status_message="Insufficient funds"))

    with caplog.at_level(logging.ERROR, logger="core.brokers.upstox_adapter"):
        with pytest.raises(BrokerOrderNotFilledError):  # surfaced once, see hardening tests
            adapter.poll_fills()
    adapter.poll_fills()

    assert fills == []
    assert len(http.calls_to("GET", "/order/details")) == 1
    assert any("rejected" in r.message and "Insufficient funds" in r.message
               for r in caplog.records)


def test_partially_filled_then_cancelled_emits_the_filled_part(tmp_path, monkeypatch):
    adapter, http, fills = _placed_adapter(
        tmp_path, monkeypatch, _order(quantity=75),
        _details("cancelled", quantity=75, filled=30, average_price=99.0))

    with pytest.raises(BrokerOrderNotFilledError):
        adapter.poll_fills()
    adapter.poll_fills()

    assert [(f.quantity, f.price) for f in fills] == [(30.0, 99.0)]
    assert len(http.calls_to("GET", "/order/details")) == 1


def test_unavailable_broker_is_reported_and_the_order_stays_pending(
        tmp_path, monkeypatch):
    """The poll raises so the driver can count the failure; the order is not lost."""
    down = requests.exceptions.ConnectionError("connection reset")
    adapter, _, fills = _placed_adapter(
        tmp_path, monkeypatch, _order(),
        down,  # the poll makes one attempt per call
        _details("complete", quantity=50, filled=50, average_price=2501.5))

    with pytest.raises(BrokerUnavailableError):
        adapter.poll_fills()
    assert fills == []

    adapter.poll_fills()
    assert [(f.quantity, f.price) for f in fills] == [(50.0, 2501.5)]


def test_poll_with_nothing_pending_makes_no_call(tmp_path, monkeypatch):
    http = install(monkeypatch)
    adapter = _adapter(tmp_path)
    adapter.subscribe_fills(lambda fill: None)

    adapter.poll_fills()

    assert http.calls == []


def test_fill_with_no_subscriber_raises_rather_than_vanishing(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "/order/place", placed(BROKER_ID))
    http.route("GET", "/order/details",
               _details("complete", quantity=50, filled=50, average_price=2501.5))
    adapter = _adapter(tmp_path)
    adapter.place_order(_order())

    with pytest.raises(RuntimeError, match="subscribe_fills"):
        adapter.poll_fills()


# --------------------------------------------------------------------------- #
# End to end — signal -> real adapter -> poll -> handler trackers and ledger
# --------------------------------------------------------------------------- #

def test_live_fill_reaches_position_order_tracker_and_ledger(tmp_path, monkeypatch):
    http = install(monkeypatch)
    _patch_live_creds(monkeypatch)
    _isolate_trade_recorder(tmp_path, monkeypatch)
    http.route("POST", "/order/place", placed(BROKER_ID))
    http.route("GET", "/order/details",
               _details("complete", quantity=50, filled=50, average_price=2501.5))
    adapter = _adapter(tmp_path)
    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,),
              execution_mode=ExecutionMode.LIVE, broker=adapter,
              broker_positions=lambda: [], initial_capital=1_000_000_000.0)
    handler = d._execution
    _bootstrap_trades(handler.db_manager)
    signal = SignalEvent(
        strategy_id="live", symbol=EQUITY, timestamp=NOW,
        signal_type=SignalType.BUY, confidence=1.0,
        metadata={"quantity": 50, "sl_distance": 5.0, "risk_r": 1.0,
                  "signal_id": "sig-live-e2e"})

    order = handler.process_signal(signal, current_price=2500.0)

    assert order is not None
    [call] = http.calls_to("POST", "/order/place")
    assert call["json"]["transaction_type"] == "BUY"
    assert call["json"]["tag"] == "sig-live-e2e"
    assert call["json"]["instrument_token"] == EQUITY
    assert handler.position_tracker.net_quantity(EQUITY) == 0.0  # not filled yet

    adapter.poll_fills()

    assert handler.position_tracker.net_quantity(EQUITY) == 50.0
    assert handler.order_tracker.get_status(str(order.correlation_id)) is OrderStatus.FILLED
    conn = sqlite3.connect(str(tmp_path / "execution.db"))
    try:
        rows = conn.execute("SELECT order_id, quantity, price, side FROM fills").fetchall()
    finally:
        conn.close()
    assert rows == [(str(order.correlation_id), 50.0, 2501.5, "BUY")]
    assert _trades(handler.db_manager) == [("sig-live-e2e", EQUITY, "BUY", 50, 2501.5)]


# --------------------------------------------------------------------------- #
# The loop drives the poll — a LIVE run built by build_runner records the fill
# --------------------------------------------------------------------------- #

class BuyOnceSource(SignalSource):
    """One BUY on the first bar, nothing after."""

    def __init__(self):
        self.calls = 0

    def on_bar(self, bar):
        self.calls += 1
        if self.calls > 1:
            return []
        return [SignalEvent(
            strategy_id="live", symbol=EQUITY, timestamp=bar.timestamp,
            signal_type=SignalType.BUY, confidence=1.0,
            metadata={"quantity": 50, "sl_distance": 5.0, "risk_r": 1.0,
                      "signal_id": "sig-live-run"})]


def _live_run(tmp_path, monkeypatch, http, **build_kwargs):
    _patch_live_creds(monkeypatch)
    _isolate_trade_recorder(tmp_path, monkeypatch)
    adapter = _adapter(tmp_path)
    driver = build(
        tmp_path, monkeypatch, source=BuyOnceSource(), symbols=(EQUITY,),
        execution_mode=ExecutionMode.LIVE, broker=adapter,
        broker_positions=lambda: [], initial_capital=1_000_000_000.0,
        **build_kwargs)
    _bootstrap_trades(driver._execution.db_manager)
    return adapter, driver


def test_live_run_records_the_fill_of_an_order_it_placed(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "/order/place", placed(BROKER_ID))
    http.route("GET", "/order/details",
               _details("complete", quantity=50, filled=50, average_price=2501.5))
    _, driver = _live_run(tmp_path, monkeypatch, http, max_bars=3, n_bars=3)

    driver.run()

    handler = driver._execution
    assert len(http.calls_to("POST", "/order/place")) == 1
    assert handler.position_tracker.net_quantity(EQUITY) == 50.0
    [state] = handler.order_tracker.order_states()
    assert state.status is OrderStatus.FILLED
    assert state.average_price == 2501.5
    conn = sqlite3.connect(str(tmp_path / "execution.db"))
    try:
        assert conn.execute("SELECT COUNT(*) FROM fills").fetchone() == (1,)
    finally:
        conn.close()
    assert _trades(handler.db_manager) == [("sig-live-run", EQUITY, "BUY", 50, 2501.5)]
    # Once terminal the order is no longer polled.
    assert len(http.calls_to("GET", "/order/details")) == 1


def test_live_run_trips_the_kill_switch_when_fill_polls_keep_failing(
        tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "/order/place", placed(BROKER_ID))
    http.route("GET", "/order/details", requests.exceptions.ConnectionError("down"))
    _, driver = _live_run(tmp_path, monkeypatch, http, max_bars=6, n_bars=6)

    driver.run()

    handler = driver._execution
    assert handler._kill_switched
    assert handler.position_tracker.net_quantity(EQUITY) == 0.0  # the fill never arrived


def test_build_runner_hands_the_driver_the_live_adapters_poll(tmp_path, monkeypatch):
    install(monkeypatch)
    adapter, driver = _live_run(tmp_path, monkeypatch, None)

    assert driver._fill_poll == adapter.poll_fills


def test_build_runner_gives_a_paper_driver_no_fill_poll(tmp_path, monkeypatch):
    driver = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,))

    assert driver._fill_poll is None


def test_a_broker_that_pushes_its_own_fills_needs_no_poll(tmp_path):
    from core.brokers.base import BrokerAdapter

    class PushBroker(BrokerAdapter):
        def place_order(self, order): return "1"
        def get_order_status(self, order_id): return BrokerOrderStatus.OPEN
        def get_positions(self): return {}
        def cancel_order(self, order_id): return True

    assert PushBroker().poll_fills() is None


def test_partial_fills_keep_position_and_fill_ledger_true_through_the_handler(
        tmp_path, monkeypatch):
    """Position truth, which reconciliation checks, is right after a partial fill.

    KNOWN HANDLER DEFECT (handler.py is frozen for the E008 window, so pinned
    here, not fixed): _handle_broker_fill writes one `trades` row per fill that
    does not leave the position flat, each keyed on the order's signal_id, and
    trades.signal_id is UNIQUE. The second chunk of one order's entry therefore
    fails its insert (swallowed by the handler's broad except, logged as
    "Failed to process broker fill: UNIQUE constraint failed"), so `trades`
    holds the first chunk only. Fix after the window closes.
    """
    http = install(monkeypatch)
    _patch_live_creds(monkeypatch)
    _isolate_trade_recorder(tmp_path, monkeypatch)
    http.route("POST", "/order/place", placed(BROKER_ID))
    http.route("GET", "/order/details",
               _details("open", quantity=75, filled=25, average_price=100.0),
               _details("complete", quantity=75, filled=75, average_price=101.0))
    adapter = _adapter(tmp_path)
    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,),
              execution_mode=ExecutionMode.LIVE, broker=adapter,
              broker_positions=lambda: [], initial_capital=1_000_000_000.0)
    handler = d._execution
    _bootstrap_trades(handler.db_manager)
    order = handler.process_signal(SignalEvent(
        strategy_id="live", symbol=EQUITY, timestamp=NOW, signal_type=SignalType.BUY,
        confidence=1.0, metadata={"quantity": 75, "sl_distance": 5.0, "risk_r": 1.0,
                                  "signal_id": "sig-partial"}),
        current_price=2500.0)

    adapter.poll_fills()
    assert handler.position_tracker.net_quantity(EQUITY) == 25.0
    assert handler.order_tracker.get_status(str(order.correlation_id)) is OrderStatus.PARTIALLY_FILLED

    adapter.poll_fills()
    assert handler.position_tracker.net_quantity(EQUITY) == 75.0
    assert handler.order_tracker.get_status(str(order.correlation_id)) is OrderStatus.FILLED
    conn = sqlite3.connect(str(tmp_path / "execution.db"))
    try:
        fills = conn.execute("SELECT quantity, price FROM fills ORDER BY timestamp, rowid").fetchall()
    finally:
        conn.close()
    assert fills == [(25.0, 100.0), (50.0, 101.5)]
    assert _trades(handler.db_manager) == [("sig-partial", EQUITY, "BUY", 25, 100.0)]
