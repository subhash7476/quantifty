"""
A LIVE restart with orders still open in the ledger (PR #47 review, G).

The adapter's set of orders to poll lives in memory, so after a restart nothing
polled an order placed earlier the same day: if it filled at Upstox since, the
ledger fell behind, and the startup reconcile refused every restart. build_runner
now hands those orders to the adapter, which finds each in the Upstox order book
by tag, side and quantity, and the driver's startup gate polls once before it
reconciles. Every order that is not resumed (not found, found more than once, or
the order book unreadable) is named in a critical alert.

Orders are validity DAY, so an open order from an earlier day is dead and is not
resumed; PAPER fills inline, so it never resumes anything.
"""

from datetime import timedelta
from unittest.mock import MagicMock

import json

import requests

import scripts.fno_runner as fno_runner
from core.brokers.mapping.upstox import UpstoxMapping
from core.brokers.upstox_adapter import BrokerOrderNotFilledError, UpstoxAdapter, order_tag
from core.clock import ReplayClock
from core.execution.handler import ExecutionMode
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.persistence.order_repository import OrderRepository
from core.runtime.event_journal import RuntimeEventJournal
from tests.brokers._upstox_http import install, order_details

from _runner_harness import EQUITY, FIXED_DT, NoopSource, build


def _ledger_with(tmp_path, *orders):
    repo = OrderRepository(ExecutionStore(str(tmp_path / "execution.db")))
    for order in orders:
        repo.save(order)


def _order(signal_id, timestamp):
    return NormalizedOrder(symbol=EQUITY, side=OrderSide.BUY, quantity=50,
                           order_type=OrderType.MARKET, strategy_id="live",
                           signal_id=signal_id, timestamp=timestamp)


def _adapter(tmp_path, monkeypatch):
    adapter = UpstoxAdapter("key", "secret", "token", ReplayClock(FIXED_DT))
    adapter._req_interval = 0
    adapter._mapping = UpstoxMapping(db_path=tmp_path / "no_master.duckdb")
    monkeypatch.setattr("core.brokers.upstox_adapter.alerter", MagicMock())
    return adapter


def _live(tmp_path, monkeypatch, alerts, adapter, broker_positions=lambda: [], journal=None):
    creds = MagicMock()
    creds.has_upstox_token = True
    creds.is_token_expired = False
    monkeypatch.setattr(fno_runner, "_live_credentials", creds)
    monkeypatch.setattr(fno_runner, "alerter", alerts)
    return build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,),
                 execution_mode=ExecutionMode.LIVE, broker=adapter,
                 broker_positions=broker_positions, journal=journal)


def _book(order_id, signal_id, status="open"):
    return {"order_id": order_id, "tag": order_tag(signal_id), "status": status,
            "transaction_type": "BUY", "quantity": 50}


def test_a_fill_that_landed_during_the_restart_is_booked_before_the_startup_reconcile(
        tmp_path, monkeypatch):
    """The broker already holds the +50 the ledger has not booked. The startup
    gate's poll books it first, so reconciliation passes instead of refusing."""
    http = install(monkeypatch)
    http.route("GET", "/order/retrieve-all", [_book("R-1", "sig-open-today")])
    http.route("GET", "/order/details",
               order_details("R-1", "complete", quantity=50, filled=50, average_price=2501.0,
                             instrument_token=EQUITY, transaction_type="BUY"))
    _ledger_with(tmp_path, _order("sig-open-today", FIXED_DT - timedelta(hours=2)))
    alerts = MagicMock()
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    driver = _live(tmp_path, monkeypatch, alerts, _adapter(tmp_path, monkeypatch),
                   broker_positions=lambda: [{"symbol": EQUITY, "quantity": 50, "side": "LONG"}],
                   journal=journal)

    driver.run()

    events = [json.loads(line)["event_type"]
              for line in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]
    assert "RECONCILIATION_PASS" in events and "RECONCILIATION_FAIL" not in events
    assert driver._execution.position_tracker.net_quantity(EQUITY) == 50
    alerts.critical.assert_not_called()


def test_an_order_not_in_the_order_book_is_named_in_a_critical_alert(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("GET", "/order/retrieve-all", {"status": "success", "data": []})
    _ledger_with(tmp_path, _order("sig-never-sent", FIXED_DT - timedelta(hours=2)))
    alerts = MagicMock()

    _live(tmp_path, monkeypatch, alerts, _adapter(tmp_path, monkeypatch))

    alerts.critical.assert_called_once()
    message = alerts.critical.call_args.args[0]
    assert "sig-never-sent" in message and "BUY 50" in message
    assert "not in the Upstox order book" in message and "failed ambiguously" in message


def test_an_order_whose_tag_the_book_holds_twice_is_named_and_not_polled(tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("GET", "/order/retrieve-all", [_book("D-1", "sig-dup"), _book("D-2", "sig-dup")])
    _ledger_with(tmp_path, _order("sig-dup", FIXED_DT - timedelta(hours=2)))
    alerts = MagicMock()

    _live(tmp_path, monkeypatch, alerts, _adapter(tmp_path, monkeypatch))

    alerts.critical.assert_called_once()
    message = alerts.critical.call_args.args[0]
    assert "sig-dup" in message and "more than one" in message


def test_an_unreadable_order_book_leaves_the_orders_unpolled_and_alerts_critically(
        tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("GET", "/order/retrieve-all", requests.exceptions.ConnectTimeout("timeout"))
    _ledger_with(tmp_path, _order("sig-open-today", FIXED_DT - timedelta(hours=2)))
    alerts = MagicMock()

    _live(tmp_path, monkeypatch, alerts, _adapter(tmp_path, monkeypatch))

    alerts.critical.assert_called_once()
    message = alerts.critical.call_args.args[0]
    assert "sig-open-today" in message and "order book" in message


def test_an_open_order_from_an_earlier_day_is_not_resumed(tmp_path, monkeypatch):
    http = install(monkeypatch)
    _ledger_with(tmp_path, _order("sig-yesterday", FIXED_DT - timedelta(days=1)))
    alerts = MagicMock()

    _live(tmp_path, monkeypatch, alerts, _adapter(tmp_path, monkeypatch))

    assert http.calls == []
    alerts.critical.assert_not_called()


def test_a_restart_with_a_clean_ledger_makes_no_call(tmp_path, monkeypatch):
    http = install(monkeypatch)
    alerts = MagicMock()

    _live(tmp_path, monkeypatch, alerts, _adapter(tmp_path, monkeypatch))

    assert http.calls == []
    alerts.critical.assert_not_called()


def test_paper_never_resumes_open_orders(tmp_path, monkeypatch):
    alerts = MagicMock()
    monkeypatch.setattr(fno_runner, "alerter", alerts)
    _ledger_with(tmp_path, _order("sig-open-today", FIXED_DT - timedelta(hours=2)))

    build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,))

    alerts.critical.assert_not_called()
    alerts.warning.assert_not_called()


def test_an_order_upstox_rejected_before_the_restart_is_reported_by_the_first_poll(
        tmp_path, monkeypatch):
    http = install(monkeypatch)
    http.route("GET", "/order/retrieve-all", [_book("R-1", "sig-rejected", "rejected")])
    http.route("GET", "/order/details",
               order_details("R-1", "rejected", quantity=50, filled=0, average_price=0.0,
                             instrument_token=EQUITY, transaction_type="BUY",
                             status_message="Insufficient funds"))
    _ledger_with(tmp_path, _order("sig-rejected", FIXED_DT - timedelta(hours=2)))
    adapter = _adapter(tmp_path, monkeypatch)

    _live(tmp_path, monkeypatch, MagicMock(), adapter)

    try:
        adapter.poll_fills()
    except BrokerOrderNotFilledError as exc:
        [ended] = exc.not_filled
        assert "Insufficient funds" in ended.description
    else:
        raise AssertionError("the reject was not reported")


def test_a_live_runner_charges_fills_by_the_handlers_fee_schedule(tmp_path, monkeypatch):
    install(monkeypatch)
    adapter = _adapter(tmp_path, monkeypatch)

    driver = _live(tmp_path, monkeypatch, MagicMock(), adapter)

    assert adapter.fee_model == driver._execution._calculate_fees


def test_build_runner_creates_the_trades_tables(tmp_path, monkeypatch):
    driver = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,))

    with driver._execution.db_manager.trading_reader() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
    assert {"trades", "trade_context"} <= tables
