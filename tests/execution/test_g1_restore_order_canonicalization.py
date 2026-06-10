"""
Gate G1 — Wave 3 (#8) restored ORDER canonicalization.

Verifies the Option-B post-gate pass at the handler level for the ORDER half
(the sibling of #7-as-restored, test_g1_restore_canonicalization.py): re-resolve
each restored DERIVATIVE order's identity through the (gate-verified) instrument
master and swap `NormalizedOrder.instrument` IN PLACE — futures EQUITY->FUTURE
(H1), options parser-lot 1 -> master lot (H2) — while preserving the symbol,
correlation_id, signal_id, side, quantity, and order_type (H7/H8: in-place swap,
never reconstruct the order, so the tracker key and idempotency/group identity
are untouched). Equity / unresolved symbols are left legacy (carve-out).
Restore-at-construction stays legacy (Option B), so the Wave 3A characterization
suite (current pre-gate reality) is unaffected; canonicalization is the explicit,
separate post-gate step.

A tmp instrument master with lot 75 — distinct from BOTH the parser default (1)
and the production F4 value (65) — is injected, proving the swapped identity came
from the resolver, not the parser or the real DB.
"""
from datetime import datetime

import pytz

import core.execution.handler as handler_mod
from core.execution.handler import ExecutionHandler, ExecutionConfig
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.order_models import OrderSide, OrderType
from core.instruments.instrument_base import InstrumentType
from core.instruments.resolver import InstrumentResolver
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from scripts.fetch_instrument_master import parse_instruments, write_snapshot

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
FUTURES_SYMBOL = "NIFTY26JUNFUT"
OPTION_UNDERLYING = "NSE_INDEX|Nifty 50"
OPTION_PRICE = 22500.0
EXPECTED_OPTION_SYMBOL = "NIFTY16JUN2622500CE"   # expiry 2026-06-16, strike 22500
MASTER_LOT = 75   # distinct from parser default (1) and production F4 (65)


def _write_master(path):
    """A minimal master carrying the exact NIFTY future + option the restored
    orders resolve against (expiry/strike matched to the persisted symbols)."""
    rows = parse_instruments([
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|F1", "tradingsymbol": "NIFTYFUT",
         "name": "NIFTY", "expiry": "2026-06-25", "instrument_type": "FUT",
         "lot_size": MASTER_LOT, "tick_size": 0.05},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|O1", "tradingsymbol": EXPECTED_OPTION_SYMBOL,
         "name": "NIFTY", "expiry": "2026-06-16", "strike_price": 22500.0,
         "instrument_type": "CE", "lot_size": MASTER_LOT, "tick_size": 0.05},
    ], "2026-06-08")
    write_snapshot(rows, db_path=path)


def _build_handler(tmp_path, monkeypatch, store_path):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore", lambda *a, **k: ExecutionStore(str(store_path))
    )
    clock = ReplayClock(FIXED_DT)
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
    )
    return handler


def _signal(symbol, quantity, metadata=None):
    meta = {
        "quantity": quantity,
        "sl_distance": 5.0,
        "risk_r": 1.0,
        "signal_id": f"sig-ocanon-{symbol}-{quantity}",
    }
    if metadata:
        meta.update(metadata)
    return SignalEvent(
        strategy_id="g1ocanon",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=SignalType.BUY,
        confidence=1.0,
        metadata=meta,
    )


def _resolver(master_path):
    return InstrumentResolver(db_path=master_path)


def _order_by_symbol(handler, symbol):
    for state in handler.order_tracker.order_states():
        if state.order.symbol == symbol:
            return state.order
    raise AssertionError(f"no restored order for {symbol}")


# --------------------------------------------------------------------------- #
# H1 — restored futures order: EQUITY (pre-gate) -> FUTURE (canonicalized)
# --------------------------------------------------------------------------- #
def test_canonicalize_future_order_becomes_future(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"
    master_path = tmp_path / "master.duckdb"
    _write_master(master_path)

    ha = _build_handler(tmp_path, monkeypatch, store_path)
    ha.process_signal(_signal(FUTURES_SYMBOL, 50), current_price=23000.0)

    hb = _build_handler(tmp_path, monkeypatch, store_path)
    # Pre-gate restore reality (Wave 3A): EQUITY-typed (parser has no Future branch).
    assert _order_by_symbol(hb, FUTURES_SYMBOL).instrument.type == InstrumentType.EQUITY

    hb.canonicalize_restored_orders(resolver=_resolver(master_path))

    order = _order_by_symbol(hb, FUTURES_SYMBOL)
    assert order.instrument.type == InstrumentType.FUTURE       # H1 fixed at order level
    assert order.instrument.multiplier == MASTER_LOT            # from the injected master
    assert order.symbol == FUTURES_SYMBOL                       # symbol preserved (H3)
    assert order.side == OrderSide.BUY                          # side preserved
    assert order.quantity == 50                                 # qty preserved
    assert order.order_type == OrderType.MARKET                 # type preserved


# --------------------------------------------------------------------------- #
# H2 — restored option order: lot 1 (pre-gate) -> master lot (canonicalized)
# --------------------------------------------------------------------------- #
def test_canonicalize_option_order_lot_from_master(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"
    master_path = tmp_path / "master.duckdb"
    _write_master(master_path)

    ha = _build_handler(tmp_path, monkeypatch, store_path)
    ha.process_signal(_signal(OPTION_UNDERLYING, 75, metadata={"execution_mode": "option"}),
                      current_price=OPTION_PRICE)

    hb = _build_handler(tmp_path, monkeypatch, store_path)
    assert _order_by_symbol(hb, EXPECTED_OPTION_SYMBOL).instrument.lot_size == 1

    hb.canonicalize_restored_orders(resolver=_resolver(master_path))

    order = _order_by_symbol(hb, EXPECTED_OPTION_SYMBOL)
    assert order.instrument.type == InstrumentType.OPTION
    assert order.instrument.lot_size == MASTER_LOT              # H2 fixed (1 -> 75)
    assert order.instrument.multiplier == 1.0
    assert order.symbol == EXPECTED_OPTION_SYMBOL               # symbol preserved (H3)
    assert order.quantity == 75


# --------------------------------------------------------------------------- #
# H7/H8 — in-place swap preserves correlation_id / signal_id and the tracker key
# (orders are not reconstructed, so idempotency + group identity are untouched)
# --------------------------------------------------------------------------- #
def test_canonicalize_order_preserves_identity_keys(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"
    master_path = tmp_path / "master.duckdb"
    _write_master(master_path)

    ha = _build_handler(tmp_path, monkeypatch, store_path)
    ha.process_signal(_signal(FUTURES_SYMBOL, 50), current_price=23000.0)

    hb = _build_handler(tmp_path, monkeypatch, store_path)
    before = _order_by_symbol(hb, FUTURES_SYMBOL)
    corr_id, signal_id = before.correlation_id, before.signal_id

    hb.canonicalize_restored_orders(resolver=_resolver(master_path))

    after = _order_by_symbol(hb, FUTURES_SYMBOL)
    assert after.correlation_id == corr_id                     # H7: identity unchanged
    assert after.signal_id == signal_id                        # H7: idempotency key intact
    # Tracker key preserved — the in-place swap kept the same OrderState entry.
    assert hb.order_tracker.get_order(corr_id).order is after


# --------------------------------------------------------------------------- #
# Carve-out — an equity order is left legacy (canonicalize_symbol -> None)
# --------------------------------------------------------------------------- #
def test_canonicalize_leaves_equity_order_untouched(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"
    master_path = tmp_path / "master.duckdb"
    _write_master(master_path)

    ha = _build_handler(tmp_path, monkeypatch, store_path)
    ha.process_signal(_signal("INFY", 10), current_price=1500.0)

    hb = _build_handler(tmp_path, monkeypatch, store_path)
    hb.canonicalize_restored_orders(resolver=_resolver(master_path))

    order = _order_by_symbol(hb, "INFY")
    assert order.instrument.type == InstrumentType.EQUITY      # unchanged (carve-out)
    assert order.symbol == "INFY"
    assert order.quantity == 10
