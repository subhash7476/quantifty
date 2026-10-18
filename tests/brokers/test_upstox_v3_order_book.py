"""
UpstoxAdapter against the current Upstox order API (checked against the docs on
2026-10-18; never against the live API):

- placement goes to V3 on the HFT host, with a tag Upstox accepts (40 characters
  at most, error UDAPI1119) that is derivable from the signal_id;
- a definite refusal is typed, so the handler can tell it from an ambiguous one;
- an ambiguous placement is looked up in the order book by that tag;
- after a restart, today's open orders are re-seeded from the order book;
- each fill carries the fee model's estimate, never a flat 0.0 when one is set.

Every test stubs `requests.request`; an unrouted call fails the test.
"""
from datetime import datetime
from unittest.mock import MagicMock

import pytest
import pytz
import requests

from core.brokers.mapping.upstox import UpstoxMapping
from core.brokers.upstox_adapter import (
    BrokerAmbiguousPlacementError, BrokerContractError, BrokerOrderNotFilledError,
    BrokerOrderRefusedError, BrokerUnavailableError, UpstoxAdapter, order_tag)
from core.clock import ReplayClock
from core.events import OrderStatus
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
from tests.brokers._upstox_http import HttpStatus, install, order_details, placed

EQUITY = "NSE_EQ|INE002A01018"
NOW = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
SHA_SIGNAL = "f" * 64   # the handler's fallback signal_id is a 64-character sha256


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


def _book_entry(order_id, signal_id, status="open", *, quantity=50, side="BUY"):
    return {"order_id": order_id, "tag": order_tag(signal_id), "status": status,
            "instrument_token": EQUITY, "transaction_type": side, "quantity": quantity,
            "filled_quantity": 0}


# --------------------------------------------------------------------------- #
# The tag
# --------------------------------------------------------------------------- #

def test_a_short_plain_signal_id_is_its_own_tag():
    assert order_tag("sig-live-1") == "sig-live-1"


@pytest.mark.parametrize("signal_id", [SHA_SIGNAL, "sig-NSE_EQ|INE002A01018-50", "a" * 41,
                                       "has space"])
def test_any_other_signal_id_becomes_a_40_character_hash_tag(signal_id):
    tag = order_tag(signal_id)
    assert len(tag) == 40
    assert tag == order_tag(signal_id)          # derivable again from the ledger
    assert tag != order_tag(signal_id + "x")


def test_a_64_character_signal_id_goes_out_with_a_tag_upstox_accepts(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place", placed("A-1"))

    _adapter(tmp_path).place_order(_order(signal_id=SHA_SIGNAL))

    [call] = http.calls_to("POST", "hft/order/place")
    assert len(call["json"]["tag"]) <= 40


# --------------------------------------------------------------------------- #
# Placement: V3 on the HFT host
# --------------------------------------------------------------------------- #

def test_placement_goes_to_v3_on_the_hft_host_as_one_unsliced_order(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place", placed("A-1"))

    assert _adapter(tmp_path).place_order(_order()) == "A-1"

    [call] = http.calls
    assert call["path"] == "hft/order/place"
    assert call["json"]["slice"] is False


def test_success_with_more_than_one_order_id_is_ambiguous(tmp_path, monkeypatch, alerts):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place",
               {"status": "success", "data": {"order_ids": ["A-1", "A-2"]}})
    adapter = _adapter(tmp_path)

    with pytest.raises(BrokerAmbiguousPlacementError, match="exactly one"):
        adapter.place_order(_order())

    alerts.critical.assert_called_once()


@pytest.mark.parametrize("ids", [[], [""], [None], "A-1", [True]])
def test_success_without_one_usable_order_id_is_ambiguous(tmp_path, monkeypatch, alerts, ids):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place", {"status": "success", "data": {"order_ids": ids}})

    with pytest.raises(BrokerAmbiguousPlacementError):
        _adapter(tmp_path).place_order(_order())


def test_a_numeric_order_id_is_taken_as_text(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place", {"status": "success", "data": {"order_ids": [123]}})

    assert _adapter(tmp_path).place_order(_order()) == "123"


# --------------------------------------------------------------------------- #
# Definite refusals are typed
# --------------------------------------------------------------------------- #

def test_a_reply_with_status_error_is_a_refusal_and_nothing_is_pending(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place",
               {"status": "error", "errors": [{"errorCode": "UDAPI1119",
                                               "message": "Tag length exceeded"}]})
    adapter = _adapter(tmp_path)

    with pytest.raises(BrokerOrderRefusedError, match="UDAPI1119"):
        adapter.place_order(_order())

    adapter.poll_fills()            # nothing pending, nothing unconfirmed: no call
    assert len(http.calls) == 1


def test_a_4xx_is_a_refusal(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place", HttpStatus(400))

    with pytest.raises(BrokerOrderRefusedError, match="400"):
        _adapter(tmp_path).place_order(_order())
    assert len(http.calls) == 1


def test_a_refusal_is_counted_by_the_handler_as_a_broker_error():
    # The frozen handler catches BrokerUnavailableError, counts it toward its
    # broker-error threshold and returns no order; a refusal must land there.
    assert issubclass(BrokerOrderRefusedError, BrokerUnavailableError)
    assert not issubclass(BrokerOrderRefusedError, BrokerAmbiguousPlacementError)


def test_an_unroutable_order_type_is_refused_before_any_call(tmp_path, monkeypatch):
    http = install(monkeypatch)
    order = _order()
    object.__setattr__(order, "order_type", "LIMIT")

    with pytest.raises(BrokerOrderRefusedError, match="only MARKET"):
        _adapter(tmp_path).place_order(order)
    assert http.calls == []


# --------------------------------------------------------------------------- #
# An ambiguous placement is looked up in the order book
# --------------------------------------------------------------------------- #

def _ambiguous(tmp_path, monkeypatch, signal_id="sig-amb"):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place", requests.exceptions.ReadTimeout("read timed out"))
    adapter = _adapter(tmp_path)
    with pytest.raises(BrokerAmbiguousPlacementError):
        adapter.place_order(_order(signal_id=signal_id))
    return adapter, http


@pytest.mark.parametrize("envelope", [True, False], ids=["data-envelope", "bare-list"])
def test_an_ambiguous_placement_found_in_the_order_book_is_polled_from_then_on(
        tmp_path, monkeypatch, alerts, envelope):
    adapter, http = _ambiguous(tmp_path, monkeypatch)
    book = [_book_entry("X-7", "sig-other"), _book_entry("A-9", "sig-amb")]
    http.route("GET", "/order/retrieve-all",
               {"status": "success", "data": book} if envelope else book)
    http.route_order("GET", "/order/details", "A-9",
                     _details("A-9", "complete", filled=50, average_price=101.0))

    adapter.poll_fills()            # found, polled, filled: nothing left to raise

    [fill] = adapter.fills
    assert (fill.quantity, fill.price, fill.fill_id) == (50, 101.0, "A-9-50")
    assert "A-9" in alerts.critical.call_args.args[0]
    adapter.poll_fills()
    assert len(http.calls_to("GET", "/order/retrieve-all")) == 1


def test_an_ambiguous_placement_not_in_the_order_book_stays_unconfirmed(
        tmp_path, monkeypatch, alerts):
    adapter, http = _ambiguous(tmp_path, monkeypatch)
    http.route("GET", "/order/retrieve-all", [_book_entry("X-7", "sig-other")])

    for _ in range(2):
        with pytest.raises(BrokerAmbiguousPlacementError, match="sig-amb"):
            adapter.poll_fills()

    assert len(http.calls_to("GET", "/order/retrieve-all")) == 2
    assert http.calls_to("GET", "/order/details") == []


def test_two_book_orders_with_the_same_tag_are_a_contract_error(tmp_path, monkeypatch, alerts):
    adapter, http = _ambiguous(tmp_path, monkeypatch)
    http.route("GET", "/order/retrieve-all",
               [_book_entry("A-1", "sig-amb"), _book_entry("A-2", "sig-amb")])

    with pytest.raises(BrokerContractError, match="2 Upstox orders") as raised:
        adapter.poll_fills()
    assert "unconfirmed" in str(raised.value)   # still held, still reported


@pytest.mark.parametrize("body", [{"status": "error"}, {"status": "success", "data": {}},
                                  "garbled", [1, 2]])
def test_an_unreadable_order_book_keeps_the_placement_unconfirmed(
        tmp_path, monkeypatch, alerts, body):
    adapter, http = _ambiguous(tmp_path, monkeypatch)
    http.route("GET", "/order/retrieve-all", body)

    with pytest.raises(BrokerContractError, match="order book") as raised:
        adapter.poll_fills()
    assert "sig-amb" in str(raised.value)


def test_an_unreachable_order_book_is_an_outage_and_the_placement_stays_unconfirmed(
        tmp_path, monkeypatch, alerts):
    adapter, http = _ambiguous(tmp_path, monkeypatch)
    http.route("GET", "/order/retrieve-all", requests.exceptions.ConnectTimeout("timeout"))

    with pytest.raises(BrokerAmbiguousPlacementError, match="order book"):
        adapter.poll_fills()


# --------------------------------------------------------------------------- #
# Restart: today's open orders are re-seeded from the order book
# --------------------------------------------------------------------------- #

def test_resume_polls_a_book_order_from_the_quantity_the_ledger_already_holds(
        tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("GET", "/order/retrieve-all", [_book_entry("R-1", "sig-restart", quantity=75)])
    http.route_order("GET", "/order/details", "R-1",
                     _details("R-1", "complete", quantity=75, filled=75, average_price=102.0))
    adapter = _adapter(tmp_path)
    order = _order(signal_id="sig-restart", quantity=75)

    result = adapter.resume_orders([(order, 25, 100.0)])
    adapter.poll_fills()

    assert (result.not_found, result.duplicated) == ([], [])
    [fill] = adapter.fills         # only the 50 filled since the restart
    assert fill.quantity == 50
    assert fill.price == pytest.approx((102.0 * 75 - 100.0 * 25) / 50)
    assert fill.order_id == str(order.correlation_id)


def test_resume_reports_missing_and_duplicated_orders_separately(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("GET", "/order/retrieve-all",
               [_book_entry("D-1", "sig-dup"), _book_entry("D-2", "sig-dup")])
    adapter = _adapter(tmp_path)
    missing, duplicated = _order(signal_id="sig-gone"), _order(signal_id="sig-dup")

    result = adapter.resume_orders([(missing, 0, 0.0), (duplicated, 0, 0.0)])

    assert result.not_found == [missing]
    assert result.duplicated == [duplicated]
    adapter.poll_fills()            # neither is polled
    assert http.calls_to("GET", "/order/details") == []


def test_resume_with_nothing_open_makes_no_call(tmp_path, monkeypatch):
    http = install(monkeypatch)

    result = _adapter(tmp_path).resume_orders([])
    assert (result.not_found, result.duplicated) == ([], [])
    assert http.calls == []


# --------------------------------------------------------------------------- #
# Fees
# --------------------------------------------------------------------------- #

def _flat_plus_turnover(order, price):
    return 20.0 + 0.001 * order.quantity * price


def test_partial_fills_carry_fees_that_add_up_to_the_whole_orders_estimate(
        tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place", placed("A-1"))
    http.route_order("GET", "/order/details", "A-1",
                     _details("A-1", "open", quantity=75, filled=25, average_price=100.0),
                     _details("A-1", "complete", quantity=75, filled=75, average_price=101.0))
    adapter = _adapter(tmp_path)
    adapter.fee_model = _flat_plus_turnover
    adapter.place_order(_order(quantity=75))

    adapter.poll_fills()
    adapter.poll_fills()

    first, second = adapter.fills
    assert first.fee == pytest.approx(20.0 + 0.001 * 25 * 100.0)
    assert first.fee + second.fee == pytest.approx(20.0 + 0.001 * 75 * 101.0)


def test_a_resumed_order_is_charged_only_for_what_fills_after_the_restart(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("GET", "/order/retrieve-all", [_book_entry("R-1", "sig-r", quantity=75)])
    http.route_order("GET", "/order/details", "R-1",
                     _details("R-1", "complete", quantity=75, filled=75, average_price=100.0))
    adapter = _adapter(tmp_path)
    adapter.fee_model = _flat_plus_turnover
    adapter.resume_orders([(_order(signal_id="sig-r", quantity=75), 25, 100.0)])

    adapter.poll_fills()

    [fill] = adapter.fills
    assert fill.fee == pytest.approx(0.001 * 50 * 100.0)   # the flat part was booked before


def test_without_a_fee_model_a_fill_carries_no_fee(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place", placed("A-1"))
    http.route("GET", "/order/details", _details("A-1", "complete", filled=50, average_price=100.0))
    adapter = _adapter(tmp_path)
    adapter.place_order(_order())

    adapter.poll_fills()

    assert adapter.fills[0].fee == 0.0


# --------------------------------------------------------------------------- #
# Rejects are reported with the order's identity; cancel uses the HFT host
# --------------------------------------------------------------------------- #

def test_a_reject_names_the_order_by_correlation_id_and_status(tmp_path, monkeypatch, alerts):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place", placed("A-1"))
    http.route("GET", "/order/details", _details("A-1", "cancelled", filled=0, average_price=0.0))
    adapter = _adapter(tmp_path)
    order = _order()
    adapter.place_order(order)

    with pytest.raises(BrokerOrderNotFilledError) as raised:
        adapter.poll_fills()

    [ended] = raised.value.not_filled
    assert ended.correlation_id == str(order.correlation_id)
    assert ended.status is OrderStatus.CANCELLED


def test_cancel_goes_to_v3_on_the_hft_host(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("DELETE", "hft/order/cancel",
               {"status": "success", "data": {"order_id": "A-1"}, "metadata": {"latency": 30}})

    assert _adapter(tmp_path).cancel_order("A-1") is True
    [call] = http.calls
    assert call["params"] == {"order_id": "A-1"}


# --------------------------------------------------------------------------- #
# Review fixes (PR #49): no pre-send failure is reported as placed; tags never
# exceed 40 characters; a tag on another side or size is not the order; a
# raising fee model never holds back a fill; any broker can be resumed
# --------------------------------------------------------------------------- #

def test_any_failure_before_sending_is_a_refusal(tmp_path, monkeypatch):
    http = install(monkeypatch)
    adapter = _adapter(tmp_path)
    adapter._mapping = None

    def broken_master(*a, **k):
        raise RuntimeError("instrument master locked by another process")
    monkeypatch.setattr("core.brokers.upstox_adapter.UpstoxMapping", broken_master)

    with pytest.raises(BrokerOrderRefusedError, match="nothing was sent"):
        adapter.place_order(_order())
    assert http.calls == []


def test_the_frozen_handler_counts_a_refusal_and_returns_no_order(tmp_path, monkeypatch):
    """Through the real ExecutionHandler: a 200 reply with status "error" used to
    be a RuntimeError that the handler returned as a placed order."""
    from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
    from core.events import SignalEvent, SignalType
    from tests.execution.test_g1_characterization import _build_handler, _signal

    http = install(monkeypatch)
    http.route("POST", "hft/order/place", {"status": "error", "errors": [{"errorCode": "X"}]})
    adapter = _adapter(tmp_path)
    handler, _ = _build_handler(tmp_path, monkeypatch, tmp_path / "execution.db",
                                load_db_state=True, broker=adapter)

    order = handler.process_signal(_signal(EQUITY, 50), current_price=2500.0)

    assert order is None
    assert handler._consecutive_broker_errors == 1


def test_a_tag_with_a_trailing_newline_is_hashed():
    newline = chr(10)
    assert order_tag("a" * 40 + newline) != "a" * 40 + newline
    assert len(order_tag("a" * 40 + newline)) == 40
    assert order_tag("abc" + newline) != "abc" + newline


def test_a_book_order_with_the_tag_but_another_side_or_size_is_not_matched(
        tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("GET", "/order/retrieve-all",
               [_book_entry("S-1", "sig-x", side="SELL"), _book_entry("Q-1", "sig-x", quantity=75)])
    adapter = _adapter(tmp_path)
    order = _order(signal_id="sig-x")

    result = adapter.resume_orders([(order, 0, 0.0)])

    assert result.not_found == [order]


def test_a_raising_fee_model_books_the_fill_without_a_fee(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("POST", "hft/order/place", placed("A-1"))
    http.route("GET", "/order/details", _details("A-1", "complete", filled=50, average_price=100.0))
    adapter = _adapter(tmp_path)

    def broken(order, price):
        raise ValueError("no fee schedule for this segment")
    adapter.fee_model = broken
    adapter.place_order(_order())

    adapter.poll_fills()

    [fill] = adapter.fills
    assert (fill.quantity, fill.fee) == (50, 0.0)


def test_a_broker_that_pushes_its_own_fills_resumes_nothing():
    from core.brokers.base import BrokerAdapter

    class Pushing(BrokerAdapter):
        def place_order(self, order): return "1"
        def get_order_status(self, order_id): return OrderStatus.OPEN
        def get_positions(self): return {}
        def cancel_order(self, order_id): return True

    result = Pushing().resume_orders([(_order(), 0, 0.0)])
    assert (result.not_found, result.duplicated) == ([], [])
