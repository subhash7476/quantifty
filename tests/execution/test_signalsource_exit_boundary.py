"""
MM.7C — C2: the EXIT resolution boundary (finding C1 of MM7B).

An EXIT SignalEvent names only the symbol; the handler resolves the close against
its OWN position tracker (handler.py:586-591): side from the held position, quantity
= the full held quantity. So a SignalSource never needs the position quantity to
exit — it decides WHEN to exit; the handler resolves WHAT to close. EXIT also
bypasses the non-EXIT risk-field requirement (handler.py:461,491-493).

This pins that boundary so MM7D's strategy emits bare EXIT signals (no sizing, no
sl_distance/risk_r) and relies on the handler to close. Real ExecutionHandler over
an isolated tmp PaperBroker + ExecutionStore. ZERO production code changed.
"""
from datetime import datetime

import pytz

import core.execution.handler as handler_mod
from core.execution.handler import ExecutionHandler, ExecutionConfig
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.order_models import OrderSide
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
EQUITY = "RELIANCE"


def _build_handler(tmp_path, monkeypatch):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")))
    clock = ReplayClock(FIXED_DT)
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock, broker=PaperBroker(clock), config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"), load_db_state=True)


def _sig(signal_type, metadata):
    return SignalEvent(strategy_id="mm7c", symbol=EQUITY, timestamp=FIXED_DT,
                       signal_type=signal_type, confidence=1.0, metadata=dict(metadata))


def _open_long(h, qty=50):
    h.process_signal(
        _sig(SignalType.BUY, {"quantity": qty, "sl_distance": 5.0, "risk_r": 1.0,
                              "signal_id": "open"}),
        current_price=2500.0)


# --------------------------------------------------------------------------- #
# EXIT is resolved by the handler against its own ledger — the source supplies
# no quantity, yet the close covers the full held position.
# --------------------------------------------------------------------------- #
def test_exit_resolved_by_handler_closes_full_position(tmp_path, monkeypatch):
    h = _build_handler(tmp_path, monkeypatch)
    _open_long(h, qty=50)
    assert h.position_tracker.net_quantity(EQUITY) == 50.0

    exit_sig = _sig(SignalType.EXIT, {"signal_id": "exit"})  # NO quantity, NO side
    order = h.process_signal(exit_sig, current_price=2550.0)

    assert order is not None
    assert order.side == OrderSide.SELL          # handler-derived (was LONG)
    assert order.quantity == 50                  # handler-derived from the held position
    assert "quantity" not in exit_sig.metadata   # the source provided none


# --------------------------------------------------------------------------- #
# EXIT on a flat book is a no-op — nothing to close (handler.py:587-588).
# --------------------------------------------------------------------------- #
def test_exit_on_flat_position_returns_none(tmp_path, monkeypatch):
    h = _build_handler(tmp_path, monkeypatch)
    order = h.process_signal(_sig(SignalType.EXIT, {"signal_id": "exit-flat"}),
                             current_price=2500.0)
    assert order is None


# --------------------------------------------------------------------------- #
# EXIT bypasses the non-EXIT risk-field requirement: a bare EXIT (no sl_distance,
# no risk_r) still closes the position (handler.py:461).
# --------------------------------------------------------------------------- #
def test_exit_bypasses_risk_field_requirement(tmp_path, monkeypatch):
    h = _build_handler(tmp_path, monkeypatch)
    _open_long(h, qty=50)
    order = h.process_signal(_sig(SignalType.EXIT, {"signal_id": "exit-bare"}),
                             current_price=2550.0)
    assert order is not None and order.quantity == 50
