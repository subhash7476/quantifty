"""
Gate G1 — Wave 3 (#7-as-restored) position canonicalization.

Verifies the Option-B post-gate pass at the handler level: re-resolve each
restored DERIVATIVE position's identity through the (gate-verified) instrument
master and swap `Position.instrument` IN PLACE — futures EQUITY->FUTURE (H1),
options parser-lot 1 -> master lot (H2) — while preserving the symbol key (H3),
side, quantity, and avg_price. Equity / unresolved symbols are left legacy
(carve-out). Restore-at-construction stays legacy (Option B), so the Wave 3A
characterization suite (current pre-gate reality) is unaffected; canonicalization
is the explicit, separate post-gate step.

A tmp instrument master with lot 75 — distinct from BOTH the parser default (1)
and the production F4 value (65) — is injected, proving the swapped identity
came from the resolver, not the parser or the real DB.
"""
from datetime import datetime

import pytz

import core.execution.handler as handler_mod
from core.execution.handler import ExecutionHandler, ExecutionConfig
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.position_models import PositionSide
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
    positions resolve against (expiry/strike matched to the persisted symbols)."""
    rows = parse_instruments([
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|F1", "tradingsymbol": "NIFTYFUT",
         "name": "NIFTY", "expiry": "2026-06-25", "instrument_type": "FUT",
         "lot_size": MASTER_LOT, "tick_size": 5},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|O1", "tradingsymbol": EXPECTED_OPTION_SYMBOL,
         "name": "NIFTY", "expiry": "2026-06-16", "strike_price": 22500.0,
         "instrument_type": "CE", "lot_size": MASTER_LOT, "tick_size": 5},
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
        initial_capital=1_000_000_000.0,  # MM9.1: ample capital — characterization tests don't exercise the margin gate
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
    )
    return handler


def _signal(symbol, quantity, metadata=None):
    meta = {
        "quantity": quantity,
        "sl_distance": 5.0,
        "risk_r": 1.0,
        "signal_id": f"sig-canon-{symbol}-{quantity}",
    }
    if metadata:
        meta.update(metadata)
    return SignalEvent(
        strategy_id="g1canon",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=SignalType.BUY,
        confidence=1.0,
        metadata=meta,
    )


def _resolver(master_path):
    return InstrumentResolver(db_path=master_path)


# --------------------------------------------------------------------------- #
# H1 — restored futures position: EQUITY (pre-gate) -> FUTURE (canonicalized)
# --------------------------------------------------------------------------- #
def test_canonicalize_future_position_becomes_future(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"
    master_path = tmp_path / "master.duckdb"
    _write_master(master_path)

    ha = _build_handler(tmp_path, monkeypatch, store_path)
    ha.process_signal(_signal(FUTURES_SYMBOL, 50), current_price=23000.0)

    hb = _build_handler(tmp_path, monkeypatch, store_path)
    # Pre-gate restore reality (Wave 3A): EQUITY-typed.
    assert hb.position_tracker.get_all_positions()[FUTURES_SYMBOL].instrument.type \
        == InstrumentType.EQUITY

    hb.canonicalize_restored_positions(resolver=_resolver(master_path))

    pos = hb.position_tracker.get_all_positions()[FUTURES_SYMBOL]
    assert pos.instrument.type == InstrumentType.FUTURE        # H1 fixed at position level
    assert pos.instrument.multiplier == MASTER_LOT             # from the injected master
    assert pos.symbol == FUTURES_SYMBOL                        # symbol preserved (H3)
    assert pos.side == PositionSide.LONG                       # side preserved
    assert hb.position_tracker.net_quantity(FUTURES_SYMBOL) == 50.0   # qty preserved


# --------------------------------------------------------------------------- #
# H2 — restored option position: lot 1 (pre-gate) -> master lot (canonicalized)
# --------------------------------------------------------------------------- #
def test_canonicalize_option_position_lot_from_master(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"
    master_path = tmp_path / "master.duckdb"
    _write_master(master_path)

    ha = _build_handler(tmp_path, monkeypatch, store_path)
    ha.process_signal(_signal(OPTION_UNDERLYING, 75, metadata={"execution_mode": "option"}),
                      current_price=OPTION_PRICE)

    hb = _build_handler(tmp_path, monkeypatch, store_path)
    assert hb.position_tracker.get_all_positions()[EXPECTED_OPTION_SYMBOL].instrument.lot_size == 1

    hb.canonicalize_restored_positions(resolver=_resolver(master_path))

    pos = hb.position_tracker.get_all_positions()[EXPECTED_OPTION_SYMBOL]
    assert pos.instrument.type == InstrumentType.OPTION
    assert pos.instrument.lot_size == MASTER_LOT               # H2 fixed (1 -> 75)
    assert pos.instrument.multiplier == 1.0
    assert pos.symbol == EXPECTED_OPTION_SYMBOL                # symbol preserved (H3)
    assert hb.position_tracker.net_quantity(EXPECTED_OPTION_SYMBOL) == 75.0


# --------------------------------------------------------------------------- #
# H3 — symbol preserved byte-for-byte, so reconciliation still matches
# --------------------------------------------------------------------------- #
def test_canonicalize_preserves_symbol_for_reconciliation(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"
    master_path = tmp_path / "master.duckdb"
    _write_master(master_path)

    ha = _build_handler(tmp_path, monkeypatch, store_path)
    ha.process_signal(_signal(FUTURES_SYMBOL, 50), current_price=23000.0)

    hb = _build_handler(tmp_path, monkeypatch, store_path)
    hb.canonicalize_restored_positions(resolver=_resolver(master_path))

    matching = [{"symbol": FUTURES_SYMBOL, "quantity": 50, "side": "LONG"}]
    assert hb.reconciliation.reconcile(matching) == []        # still matches on symbol


# --------------------------------------------------------------------------- #
# Carve-out — an equity position is left legacy (canonicalize_symbol -> None)
# --------------------------------------------------------------------------- #
def test_canonicalize_leaves_equity_untouched(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"
    master_path = tmp_path / "master.duckdb"
    _write_master(master_path)

    ha = _build_handler(tmp_path, monkeypatch, store_path)
    ha.process_signal(_signal("INFY", 10), current_price=1500.0)

    hb = _build_handler(tmp_path, monkeypatch, store_path)
    hb.canonicalize_restored_positions(resolver=_resolver(master_path))

    pos = hb.position_tracker.get_all_positions()["INFY"]
    assert pos.instrument.type == InstrumentType.EQUITY        # unchanged (carve-out)
    assert pos.symbol == "INFY"
    assert hb.position_tracker.net_quantity("INFY") == 10.0
