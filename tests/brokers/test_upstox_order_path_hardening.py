"""
Review findings A-E and H on the live Upstox order path (PR #47 code review).

The adapter is real and only `requests.request` is stubbed (_upstox_http.py); an
unrouted call fails the test, so nothing here can reach Upstox.

A  a placement is never resent, and an ambiguous one is not forgotten
B  one bad order does not starve the others' fills
C  a fill is never booked at a zero or missing price
D  a `complete` order is never dropped without its full quantity reported
E  a reject or cancel is alerted and surfaced, not just logged
H  the poll makes one short attempt, and an outage stalls the loop for one call
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
import pytz
import requests

from core.brokers.mapping.upstox import UpstoxMapping
from core.brokers.upstox_adapter import (
    BrokerAmbiguousPlacementError, BrokerContractError, BrokerOrderNotFilledError,
    BrokerUnavailableError, UpstoxAdapter)
from core.clock import ReplayClock
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
from tests.brokers._upstox_http import HttpStatus, install, order_details, placed

EQUITY = "NSE_EQ|INE002A01018"
NOW = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


@pytest.fixture
def alerts(monkeypatch):
    recorder = MagicMock()
    monkeypatch.setattr("core.brokers.upstox_adapter.alerter", recorder)
    return recorder


def _adapter(tmp_path):
    adapter = UpstoxAdapter("key", "secret", "token", ReplayClock(NOW))
    adapter._req_interval = 0
    adapter._mapping = UpstoxMapping(db_path=tmp_path / "no_master.duckdb")
    adapter.fills = []
    adapter.subscribe_fills(adapter.fills.append)
    return adapter


def _order(signal_id="sig-1", quantity=50, side=OrderSide.BUY):
    return NormalizedOrder(symbol=EQUITY, side=side, quantity=quantity,
                           order_type=OrderType.MARKET, strategy_id="live",
                           signal_id=signal_id, timestamp=NOW)


def _details(order_id, status, *, quantity=50, filled, average_price):
    return order_details(order_id, status, quantity=quantity, filled=filled,
                         average_price=average_price, instrument_token=EQUITY,
                         transaction_type="BUY")


def _without(payload, *keys):
    for key in keys:
        del payload["data"][key]
    return payload


def _with_status(payload, status):
    payload["data"]["status"] = status
    return payload


def _placed_adapter(tmp_path, monkeypatch, *orders, order_ids=("A-1", "B-2")):
    http = install(monkeypatch)
    http.route("POST", "/order/place", *(placed(i) for i in order_ids[:len(orders)]))
    adapter = _adapter(tmp_path)
    for order in orders:
        adapter.place_order(order)
    return adapter, http


# --------------------------------------------------------------------------- #
# A - a placement is never resent
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("failure", [
    requests.exceptions.ReadTimeout("read timed out"),
    requests.exceptions.ConnectionError("connection reset"),
    HttpStatus(502),
    HttpStatus(503),
])
def test_a_placement_that_may_have_reached_upstox_is_never_resent(
        tmp_path, monkeypatch, alerts, failure):
    http = install(monkeypatch)
    http.route("POST", "/order/place", failure, placed("SECOND-ORDER"))
    adapter = _adapter(tmp_path)

    with pytest.raises(BrokerAmbiguousPlacementError):
        adapter.place_order(_order())

    assert len(http.calls_to("POST", "/order/place")) == 1  # the resend is the duplicate order
    assert issubclass(BrokerAmbiguousPlacementError, BrokerUnavailableError)  # the handler counts it


def test_an_ambiguous_placement_is_alerted_and_not_forgotten(tmp_path, monkeypatch, alerts):
    http = install(monkeypatch)
    http.route("POST", "/order/place", requests.exceptions.ReadTimeout("read timed out"))
    adapter = _adapter(tmp_path)
    with pytest.raises(BrokerAmbiguousPlacementError):
        adapter.place_order(_order(signal_id="sig-ambiguous"))

    alerts.critical.assert_called_once()
    assert "sig-ambiguous" in alerts.critical.call_args.args[0]
    # The order may be live, so the poll fails until an operator reconciles;
    # that is how the driver's kill switch learns of it. It makes no HTTP call.
    with pytest.raises(BrokerAmbiguousPlacementError, match="sig-ambiguous"):
        adapter.poll_fills()
    assert http.calls_to("GET", "/order/details") == []


def test_a_definite_rejection_is_not_ambiguous(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "/order/place", HttpStatus(400), placed("SECOND-ORDER"))
    adapter = _adapter(tmp_path)

    with pytest.raises(BrokerUnavailableError) as raised:
        adapter.place_order(_order())

    assert not isinstance(raised.value, BrokerAmbiguousPlacementError)
    assert len(http.calls_to("POST", "/order/place")) == 1
    adapter.poll_fills()  # nothing unconfirmed, nothing pending


def test_a_rate_limited_placement_is_not_ambiguous(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "/order/place", HttpStatus(429), placed("SECOND-ORDER"))
    adapter = _adapter(tmp_path)

    with pytest.raises(BrokerUnavailableError) as raised:
        adapter.place_order(_order())

    assert not isinstance(raised.value, BrokerAmbiguousPlacementError)
    assert len(http.calls_to("POST", "/order/place")) == 1


def test_a_success_reply_without_an_order_id_is_ambiguous(tmp_path, monkeypatch, alerts):
    http = install(monkeypatch)
    http.route("POST", "/order/place", {"status": "success", "data": {}})
    adapter = _adapter(tmp_path)

    with pytest.raises(BrokerAmbiguousPlacementError):
        adapter.place_order(_order())

    alerts.critical.assert_called_once()


@pytest.mark.parametrize("body", [[{"order_id": "A-1"}], "garbled", None],
                         ids=["array", "text", "null"])
def test_a_success_reply_that_is_not_an_object_is_an_ambiguous_placement(
        tmp_path, monkeypatch, alerts, body):
    http = install(monkeypatch)
    http.route("POST", "/order/place", body)
    adapter = _adapter(tmp_path)

    with pytest.raises(BrokerAmbiguousPlacementError):  # never a raw AttributeError
        adapter.place_order(_order())

    alerts.critical.assert_called_once()
    assert len(http.calls_to("POST", "/order/place")) == 1


# --------------------------------------------------------------------------- #
# B - one bad order does not starve the others
# --------------------------------------------------------------------------- #

def test_an_order_with_an_unknown_status_does_not_hide_the_next_orders_fill(
        tmp_path, monkeypatch):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order("first"), _order("second"))
    http.route_order("GET", "/order/details", "A-1",
                    _details("A-1", "brand new status", filled=0, average_price=0.0))
    http.route_order("GET", "/order/details", "B-2",
                     _details("B-2", "complete", filled=50, average_price=2501.5))

    with pytest.raises(BrokerContractError, match="A-1"):
        adapter.poll_fills()

    assert [(f.quantity, f.price) for f in adapter.fills] == [(50.0, 2501.5)]
    # A-1 stays pending and is polled again; B-2 is done.
    with pytest.raises(BrokerContractError):
        adapter.poll_fills()
    assert len(http.calls_to("GET", "/order/details")) == 3


@pytest.mark.parametrize("bad", [
    lambda: _without(_details("A-1", "open", filled=0, average_price=0.0), "status"),
    lambda: _with_status(_details("A-1", "open", filled=0, average_price=0.0), None),
    lambda: {"status": "error", "errors": [{"message": "boom"}]},
    lambda: {"status": "success", "data": None},
    lambda: [{"order_id": "A-1", "status": "open"}],   # a bare array, as retrieve-all documents
    lambda: "not an object",
])
def test_a_malformed_reply_is_a_contract_error_not_a_crash(tmp_path, monkeypatch, bad):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order("first"), _order("second"))
    http.route_order("GET", "/order/details", "A-1", bad())
    http.route_order("GET", "/order/details", "B-2",
                     _details("B-2", "complete", filled=50, average_price=2501.5))

    with pytest.raises(BrokerContractError):  # never AttributeError / TypeError
        adapter.poll_fills()

    assert len(adapter.fills) == 1  # B-2 still got through


def test_a_reject_that_coexists_with_a_worse_error_is_still_carried_on_it(
        tmp_path, monkeypatch, alerts):
    """The raised error is the most severe kind; a reject in the same sweep rides
    on it as .not_filled so the driver can still journal it."""
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order("first"), _order("second"))
    http.route_order("GET", "/order/details", "A-1",
                    _details("A-1", "brand new status", filled=0, average_price=0.0))
    http.route_order("GET", "/order/details", "B-2",
                     _details("B-2", "rejected", filled=0, average_price=0.0))

    with pytest.raises(BrokerContractError) as raised:
        adapter.poll_fills()

    [rejected] = raised.value.not_filled
    assert "B-2" in rejected and "rejected" in rejected


def test_the_filled_part_is_reported_even_when_the_status_is_unknown(tmp_path, monkeypatch):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order(quantity=75))
    http.route("GET", "/order/details",
               _details("A-1", "brand new status", quantity=75, filled=25, average_price=100.0))

    with pytest.raises(BrokerContractError, match="brand new status"):
        adapter.poll_fills()

    assert [(f.quantity, f.price) for f in adapter.fills] == [(25.0, 100.0)]


# --------------------------------------------------------------------------- #
# C - never a fill at a zero or missing price
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("average_price", [0.0, None, "n/a"])
def test_new_fills_with_no_usable_price_are_not_booked(tmp_path, monkeypatch, average_price):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order())
    http.route("GET", "/order/details",
               _details("A-1", "open", filled=20, average_price=average_price),
               _details("A-1", "complete", filled=50, average_price=101.0))

    with pytest.raises(BrokerContractError, match="average_price"):
        adapter.poll_fills()
    assert adapter.fills == []

    adapter.poll_fills()  # the order stayed pending; the next poll books it correctly
    assert [(f.quantity, f.price) for f in adapter.fills] == [(50.0, 101.0)]


def test_a_missing_average_price_is_tolerated_when_nothing_new_filled(tmp_path, monkeypatch):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order())
    http.route("GET", "/order/details",
               _without(_details("A-1", "open", filled=0, average_price=0.0), "average_price"))

    adapter.poll_fills()

    assert adapter.fills == []


# --------------------------------------------------------------------------- #
# D - a `complete` order is never dropped short
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("payload", [
    lambda: _without(_details("A-1", "complete", filled=50, average_price=101.0),
                     "filled_quantity"),
    lambda: _details("A-1", "complete", filled=0, average_price=0.0),
    lambda: _details("A-1", "complete", filled=30, average_price=101.0),
])
def test_a_complete_order_that_is_not_fully_reported_stays_pending(
        tmp_path, monkeypatch, payload):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order(quantity=50))
    http.route("GET", "/order/details", payload())

    with pytest.raises(BrokerContractError):
        adapter.poll_fills()

    assert len(adapter._pending) == 1  # not dropped


def test_a_short_complete_order_still_reports_the_quantity_it_has(tmp_path, monkeypatch):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order(quantity=50))
    http.route("GET", "/order/details",
               _details("A-1", "complete", filled=30, average_price=101.0))

    with pytest.raises(BrokerContractError):
        adapter.poll_fills()

    assert [(f.quantity, f.price) for f in adapter.fills] == [(30.0, 101.0)]


def test_cumulative_filled_quantity_going_down_is_a_contract_error(tmp_path, monkeypatch):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order(quantity=50))
    http.route("GET", "/order/details",
               _details("A-1", "open", filled=40, average_price=100.0),
               _details("A-1", "open", filled=30, average_price=100.0))
    adapter.poll_fills()

    with pytest.raises(BrokerContractError, match="filled_quantity"):
        adapter.poll_fills()

    assert [f.quantity for f in adapter.fills] == [40.0]


def test_a_filled_quantity_past_the_order_is_a_contract_error(tmp_path, monkeypatch):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order(quantity=50))
    http.route("GET", "/order/details",
               _details("A-1", "open", quantity=50, filled=51, average_price=100.0))

    with pytest.raises(BrokerContractError, match="filled_quantity"):
        adapter.poll_fills()

    assert adapter.fills == []


# --------------------------------------------------------------------------- #
# E - a reject or cancel is alerted and surfaced
# --------------------------------------------------------------------------- #

def test_a_rejected_order_is_alerted_and_raised_once(tmp_path, monkeypatch, alerts):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order("sig-hedge"))
    rejected = _details("A-1", "rejected", filled=0, average_price=0.0)
    rejected["data"]["status_message"] = "Insufficient funds"
    http.route("GET", "/order/details", rejected)

    with pytest.raises(BrokerOrderNotFilledError, match="Insufficient funds"):
        adapter.poll_fills()

    alerts.critical.assert_called_once()
    message = alerts.critical.call_args.args[0]
    assert "sig-hedge" in message and "rejected" in message.lower()
    adapter.poll_fills()  # once: the order is gone, the next poll is clean
    assert len(http.calls_to("GET", "/order/details")) == 1


def test_a_cancelled_partial_order_reports_its_fill_then_the_cancel(
        tmp_path, monkeypatch, alerts):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order(quantity=75))
    http.route("GET", "/order/details",
               _details("A-1", "cancelled", quantity=75, filled=30, average_price=99.0))

    with pytest.raises(BrokerOrderNotFilledError, match="30"):
        adapter.poll_fills()

    assert [(f.quantity, f.price) for f in adapter.fills] == [(30.0, 99.0)]
    alerts.critical.assert_called_once()


def test_an_ordinary_fill_raises_nothing_and_alerts_nothing(tmp_path, monkeypatch, alerts):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order())
    http.route("GET", "/order/details",
               _details("A-1", "complete", filled=50, average_price=101.0))

    adapter.poll_fills()

    alerts.critical.assert_not_called()


# --------------------------------------------------------------------------- #
# H - one short attempt, and an outage stalls the loop for one call
# --------------------------------------------------------------------------- #

def test_the_poll_makes_one_short_attempt_per_order(tmp_path, monkeypatch):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order())
    http.route("GET", "/order/details", requests.exceptions.ReadTimeout("slow"))

    with pytest.raises(BrokerUnavailableError):
        adapter.poll_fills()

    [call] = http.calls_to("GET", "/order/details")  # not 3 attempts
    assert call["timeout"] <= 5  # not the 10 s used elsewhere


def test_an_outage_ends_the_sweep_at_the_first_failure_and_rotates_that_order(
        tmp_path, monkeypatch):
    adapter, http = _placed_adapter(tmp_path, monkeypatch, _order("first"), _order("second"))
    http.route_order("GET", "/order/details", "A-1", requests.exceptions.ReadTimeout("slow"))
    http.route_order("GET", "/order/details", "B-2",
                     _details("B-2", "complete", filled=50, average_price=2501.5))

    with pytest.raises(BrokerUnavailableError, match="1 more"):
        adapter.poll_fills()
    assert len(http.calls_to("GET", "/order/details")) == 1  # B-2 not tried this time

    # The stuck order moved to the back, so the next sweep reaches B-2 first.
    with pytest.raises(BrokerUnavailableError):
        adapter.poll_fills()
    assert [(f.quantity, f.price) for f in adapter.fills] == [(50.0, 2501.5)]


def test_get_order_status_keeps_its_default_retries(tmp_path, monkeypatch):
    http = install(monkeypatch)
    down = requests.exceptions.ConnectionError("down")
    http.route("GET", "/order/details", down, down,
               _details("A-1", "complete", filled=50, average_price=101.0))

    status = _adapter(tmp_path).get_order_status("A-1")

    assert status.value == "FILLED"
    assert len(http.calls_to("GET", "/order/details")) == 3
