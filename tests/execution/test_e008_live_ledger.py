"""
The 2026-10-18 E008 batch (README audit L2, the #45/#47 review residuals, N1).

- A placement whose outcome is unknown is never reported as placed, and latches
  the kill switch at once; a definite refusal closes the order as REJECTED.
- An order the broker rejects or cancels is closed in the ledger, and stays
  closed across a restart.
- `trades` holds one row per position, however the fills are chunked.
- A failed group leg stops the remaining legs and latches the switch.
- NiftyShield sizes on the instrument master's lot, not a hard-coded one.
"""
from datetime import datetime

import pytest
import pytz

import core.execution.handler as handler_mod
from core.brokers.base import BrokerAdapter
from core.brokers.upstox_adapter import (
    BrokerAmbiguousPlacementError, BrokerAuthError, BrokerOrderRefusedError,
    BrokerUnavailableError)
from core.database.manager import DatabaseManager
from core.database.schema import TRADING_TRADE_CONTEXT_SCHEMA, TRADING_TRADES_SCHEMA
from core.events import OrderStatus as EventOrderStatus
from core.events import SignalEvent, SignalType
from core.execution.groups.order_group import OrderGroupType
from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.order_lifecycle import FillEvent, OrderStatus
from core.execution.persistence.execution_store import ExecutionStore
from core.clock import ReplayClock

NOW = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
SYMBOL = "RELIANCE"
_REAL_RECORDER = handler_mod.TradeRecorder


class StubBroker(BrokerAdapter):
    """Takes orders without filling them; `errors` maps a call index to the
    exception that call raises."""

    def __init__(self, errors=None):
        self.errors = dict(errors or {})
        self.placed = []

    def place_order(self, order):
        index = len(self.placed)
        self.placed.append(order)
        if index in self.errors:
            raise self.errors[index]
        return f"B-{index}"

    def get_order_status(self, order_id):
        return EventOrderStatus.OPEN

    def get_positions(self):
        return {}

    def cancel_order(self, order_id):
        return True


class _Journal:
    def __init__(self):
        self.records = []

    def record(self, event_type, message, severity=None, source_component=None, metadata=None):
        self.records.append((event_type.value, message, getattr(severity, "value", severity),
                             metadata or {}))


def _handler(tmp_path, monkeypatch, broker, *, journal=None):
    monkeypatch.setattr(handler_mod, "ExecutionStore",
                        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")))
    monkeypatch.setattr(handler_mod, "TradeRecorder",
                        lambda: _REAL_RECORDER(db_path=str(tmp_path / "ti.duckdb")))
    monkeypatch.setattr(handler_mod, "alerter", _Alerts())
    monkeypatch.setattr(DatabaseManager, "_instance", None)   # a singleton; restored after
    db = DatabaseManager(data_root=tmp_path)
    with db.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)
        conn.execute(TRADING_TRADE_CONTEXT_SCHEMA)
    handler = ExecutionHandler(db_manager=db, clock=ReplayClock(NOW), broker=broker,
                               config=ExecutionConfig(), initial_capital=1_000_000_000.0,
                               metrics_path=str(tmp_path / "metrics.json"), journal=journal)
    handler._kill_switch_disabled = True   # never read the checkout's own STOP file
    return handler


class _Alerts:
    def __init__(self):
        self.critical_messages = []

    def critical(self, message):
        self.critical_messages.append(message)

    def warning(self, message):
        pass


def _signal(signal_id, quantity=75, signal_type=SignalType.BUY, symbol=SYMBOL):
    return SignalEvent(strategy_id="live", symbol=symbol, timestamp=NOW,
                       signal_type=signal_type, confidence=1.0,
                       metadata={"quantity": quantity, "sl_distance": 5.0, "risk_r": 1.0,
                                 "signal_id": signal_id})


def _tracked(handler):
    [state] = handler.order_tracker.order_states()
    return state


def _fill(order, fill_id, quantity, price, side, fee=0.0):
    return FillEvent(fill_id=fill_id, order_id=str(order.correlation_id), symbol=order.symbol,
                     quantity=quantity, price=price, timestamp=NOW, side=side, fee=fee)


def _trades(handler):
    with handler.db_manager.trading_reader() as conn:
        return conn.execute(
            "SELECT signal_id, side, quantity, entry_price, exit_price, pnl, fees FROM trades "
            "ORDER BY rowid").fetchall()


# --------------------------------------------------------------------------- #
# Placement failures (L2 and the ambiguous-placement residual)
# --------------------------------------------------------------------------- #

def test_an_unexpected_placement_error_is_not_reported_as_placed(tmp_path, monkeypatch):
    journal = _Journal()
    handler = _handler(tmp_path, monkeypatch, StubBroker({0: RuntimeError("bug after send")}),
                       journal=journal)

    assert handler.process_signal(_signal("sig-1"), 100.0) is None

    assert handler._kill_switched and handler._kill_hard
    assert _tracked(handler).status is OrderStatus.CREATED   # it may be live: kept open
    [(event, _, severity, metadata)] = [r for r in journal.records if r[0] == "BROKER_ERROR"]
    assert severity == "CRITICAL" and metadata["error_type"] == "RuntimeError"


def test_an_ambiguous_placement_latches_the_switch_at_once_and_blocks_the_next_leg(
        tmp_path, monkeypatch):
    broker = StubBroker({0: BrokerAmbiguousPlacementError("timed out")})
    handler = _handler(tmp_path, monkeypatch, broker)

    assert handler.process_signal(_signal("sig-leg1"), 100.0) is None
    assert handler._kill_switched and handler._kill_hard
    assert handler._consecutive_broker_errors == 0      # not a refusal; not counted
    assert handler.process_signal(_signal("sig-leg2", symbol="TCS"), 100.0) is None
    assert len(broker.placed) == 1                      # the next leg never went out


def test_a_definite_refusal_closes_the_order_as_rejected_across_a_restart(tmp_path, monkeypatch):
    handler = _handler(tmp_path, monkeypatch, StubBroker({0: BrokerOrderRefusedError("400")}))

    assert handler.process_signal(_signal("sig-1"), 100.0) is None
    assert handler._consecutive_broker_errors == 1 and not handler._kill_switched
    assert _tracked(handler).status is OrderStatus.REJECTED

    restarted = _handler(tmp_path, monkeypatch, StubBroker())
    assert _tracked(restarted).status is OrderStatus.REJECTED


@pytest.mark.parametrize("error, hard", [(BrokerAuthError("401"), True),
                                         (BrokerUnavailableError("429"), False)])
def test_auth_and_rate_limit_failures_keep_their_old_handling(tmp_path, monkeypatch, error, hard):
    handler = _handler(tmp_path, monkeypatch, StubBroker({0: error}))

    assert handler.process_signal(_signal("sig-1"), 100.0) is None
    assert handler._kill_switched is hard


def test_a_paper_fill_that_fails_after_placement_still_returns_the_order(tmp_path, monkeypatch):
    from core.brokers.paper_broker import PaperBroker
    handler = _handler(tmp_path, monkeypatch, PaperBroker(ReplayClock(NOW)))

    def broken(fill):
        raise ValueError("ledger write failed")
    monkeypatch.setattr(handler, "_handle_broker_fill", broken)

    assert handler.process_signal(_signal("sig-1"), 100.0) is not None
    assert not handler._kill_switched


# --------------------------------------------------------------------------- #
# Rejects and cancels from the broker
# --------------------------------------------------------------------------- #

def test_a_broker_reject_closes_the_order_and_survives_a_restart(tmp_path, monkeypatch):
    handler = _handler(tmp_path, monkeypatch, StubBroker())
    order = handler.process_signal(_signal("sig-1"), 100.0)

    assert handler.record_order_ended(str(order.correlation_id), EventOrderStatus.REJECTED,
                                      "Insufficient funds")
    assert _tracked(handler).status is OrderStatus.REJECTED

    restarted = _handler(tmp_path, monkeypatch, StubBroker())
    assert _tracked(restarted).status is OrderStatus.REJECTED


def test_a_partly_filled_cancel_keeps_its_fill_and_stays_cancelled(tmp_path, monkeypatch):
    handler = _handler(tmp_path, monkeypatch, StubBroker())
    order = handler.process_signal(_signal("sig-1"), 100.0)
    handler._handle_broker_fill(_fill(order, "f1", 25, 100.0, "BUY"))

    handler.record_order_ended(str(order.correlation_id), EventOrderStatus.CANCELLED, "cancelled")

    restarted = _handler(tmp_path, monkeypatch, StubBroker())
    state = _tracked(restarted)
    assert (state.status, state.filled_quantity) == (OrderStatus.CANCELLED, 25)
    assert restarted.position_tracker.net_quantity(SYMBOL) == 25


def test_an_unknown_order_ended_by_the_broker_is_reported_not_raised(tmp_path, monkeypatch):
    handler = _handler(tmp_path, monkeypatch, StubBroker())
    assert handler.record_order_ended("no-such-order", EventOrderStatus.REJECTED, "x") is False


# --------------------------------------------------------------------------- #
# trades: one row per position
# --------------------------------------------------------------------------- #

def test_entry_chunks_of_one_order_grow_one_trades_row(tmp_path, monkeypatch):
    handler = _handler(tmp_path, monkeypatch, StubBroker())
    order = handler.process_signal(_signal("sig-entry"), 100.0)

    handler._handle_broker_fill(_fill(order, "f1", 25, 100.0, "BUY", fee=10.0))
    handler._handle_broker_fill(_fill(order, "f2", 50, 101.5, "BUY", fee=5.0))

    [(signal_id, side, quantity, entry, exit_price, pnl, fees)] = _trades(handler)
    assert (signal_id, side, quantity, exit_price) == ("sig-entry", "BUY", 75, 0.0)
    assert entry == pytest.approx(101.0)
    assert fees == pytest.approx(15.0)


def test_a_chunked_exit_closes_the_entry_row_at_its_vwap(tmp_path, monkeypatch):
    handler = _handler(tmp_path, monkeypatch, StubBroker())
    entry = handler.process_signal(_signal("sig-entry"), 101.0)
    handler._handle_broker_fill(_fill(entry, "f1", 75, 101.0, "BUY"))
    exit_order = handler.process_signal(_signal("sig-exit", signal_type=SignalType.EXIT), 110.0)

    handler._handle_broker_fill(_fill(exit_order, "x1", 25, 110.0, "SELL", fee=2.0))
    assert len(_trades(handler)) == 1            # a partial exit is not a new entry
    handler._handle_broker_fill(_fill(exit_order, "x2", 50, 112.0, "SELL", fee=3.0))

    [(signal_id, _, quantity, _, exit_price, pnl, fees)] = _trades(handler)
    assert (signal_id, quantity) == ("sig-entry", 75)
    assert exit_price == pytest.approx((25 * 110.0 + 50 * 112.0) / 75)
    assert pnl == pytest.approx(25 * 9.0 + 50 * 11.0)
    assert fees == pytest.approx(5.0)


def test_an_unchunked_round_trip_writes_the_same_row_as_before(tmp_path, monkeypatch):
    handler = _handler(tmp_path, monkeypatch, StubBroker())
    entry = handler.process_signal(_signal("sig-entry"), 100.0)
    handler._handle_broker_fill(_fill(entry, "f1", 75, 100.0, "BUY", fee=7.0))
    exit_order = handler.process_signal(_signal("sig-exit", signal_type=SignalType.EXIT), 104.0)
    handler._handle_broker_fill(_fill(exit_order, "x1", 75, 104.0, "SELL", fee=8.0))

    assert _trades(handler) == [("sig-entry", "BUY", 75, 100.0, 104.0, pytest.approx(300.0),
                                 pytest.approx(15.0))]


def test_a_fill_that_flips_the_position_closes_the_row_and_opens_one(tmp_path, monkeypatch):
    handler = _handler(tmp_path, monkeypatch, StubBroker())
    entry = handler.process_signal(_signal("sig-entry", quantity=50), 100.0)
    handler._handle_broker_fill(_fill(entry, "f1", 50, 100.0, "BUY"))
    exit_order = handler.process_signal(_signal("sig-exit", signal_type=SignalType.EXIT), 105.0)

    handler._handle_broker_fill(_fill(exit_order, "x1", 75, 105.0, "SELL"))   # 25 beyond flat

    closed, opened = _trades(handler)
    assert closed[0] == "sig-entry" and closed[4] == pytest.approx(105.0)
    assert (opened[0], opened[1], opened[2], opened[4]) == ("sig-exit", "SELL", 25, 0.0)


# --------------------------------------------------------------------------- #
# Group legs
# --------------------------------------------------------------------------- #

def test_a_failed_group_leg_stops_the_rest_and_latches_the_switch(tmp_path, monkeypatch):
    broker = StubBroker({1: BrokerOrderRefusedError("400 on the hedge")})
    handler = _handler(tmp_path, monkeypatch, broker)
    legs = [_signal(f"sig-{s}", quantity=50, symbol=s) for s in ("RELIANCE", "TCS", "INFY")]

    assert handler.process_group_signal(legs, OrderGroupType.CUSTOM) is None

    assert len(broker.placed) == 2                  # the third leg never went out
    assert handler._kill_switched and handler._kill_hard
    assert any("BROKEN" in m for m in handler_mod.alerter.critical_messages)


def test_a_group_whose_first_leg_fails_sends_nothing_more(tmp_path, monkeypatch):
    broker = StubBroker({0: BrokerOrderRefusedError("400")})
    handler = _handler(tmp_path, monkeypatch, broker)
    legs = [_signal(f"sig-{s}", quantity=50, symbol=s) for s in ("RELIANCE", "TCS")]

    assert handler.process_group_signal(legs, OrderGroupType.CUSTOM) is None
    assert len(broker.placed) == 1
    assert not handler._kill_switched               # one refusal: counted, not latched


# --------------------------------------------------------------------------- #
# N1: NiftyShield never sizes on a lot the instrument master disagrees with
# --------------------------------------------------------------------------- #

def _lot_handler(monkeypatch, lots_by_symbol, journal):
    import logging
    from types import SimpleNamespace
    import core.execution.options.nifty_shield_handler as nsh

    def fake_canonicalize(symbol, timestamp):
        lot = lots_by_symbol.get(symbol)
        return SimpleNamespace(lot_size=lot) if lot else None
    monkeypatch.setattr(nsh, "canonicalize_symbol", fake_canonicalize)
    alerts = _Alerts()
    monkeypatch.setattr(nsh, "alerter", alerts)
    handler = nsh.NiftyShieldExecutionHandler.__new__(nsh.NiftyShieldExecutionHandler)
    handler._strategy_cfg = {"lot_size": 65}
    handler._journal = journal
    handler.logger = logging.getLogger("test")
    return handler, alerts


def _legs(*symbols):
    return [_signal(f"sig-{s}", symbol=s) for s in symbols]


def test_the_configured_lot_is_used_when_the_master_agrees(monkeypatch):
    journal = _Journal()
    handler, alerts = _lot_handler(monkeypatch, {"A": 65, "B": 65}, journal)
    assert handler._structure_lot_size(_legs("A", "B"), "g", "SPREAD") == 65
    assert journal.records == [] and alerts.critical_messages == []


@pytest.mark.parametrize("lots", [{"A": 75, "B": 75}, {"A": 65, "B": 75}],
                         ids=["lot-revised", "legs-disagree"])
def test_a_lot_the_master_disagrees_with_skips_the_entry_loudly(monkeypatch, lots):
    journal = _Journal()
    handler, alerts = _lot_handler(monkeypatch, lots, journal)

    assert handler._structure_lot_size(_legs("A", "B"), "g", "SPREAD") is None

    [(event, message, severity, metadata)] = journal.records
    assert (event, severity, metadata["configured_lot"]) == ("ENTRY_SKIPPED", "CRITICAL", 65)
    assert "re-pin" in message
    assert len(alerts.critical_messages) == 1


def test_contracts_the_master_does_not_carry_fall_back_to_the_configured_lot(monkeypatch):
    journal = _Journal()
    handler, _ = _lot_handler(monkeypatch, {"A": 65}, journal)   # B: an expired contract
    assert handler._structure_lot_size(_legs("A", "B"), "g", "SPREAD") == 65
    assert journal.records == []
