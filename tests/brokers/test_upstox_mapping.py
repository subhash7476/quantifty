"""
Phase 4C.4 — Broker mapping (CANONICAL_INSTRUMENT_ARCHITECTURE.md §D6).

BrokerMapping is a tested, bidirectional, per-broker translation layer:
CanonicalInstrument <-> broker identity, and broker position/order ->
CanonicalInstrument. The canonical model never holds broker identifiers; the
mapping is the only place a broker string sits next to a canonical_id. It is a
projection of the master and stays broker-agnostic behind the BrokerMapping
interface (no strategy imports, ADR-002).
"""
import ast
import dataclasses
import pathlib
from datetime import date

import pytest

from scripts.fetch_instrument_master import parse_instruments, write_snapshot
from core.brokers.mapping.base import BrokerMapping, BrokerRef
from core.brokers.mapping.upstox import UpstoxMapping
from core.instruments.canonical import AssetClass, CanonicalInstrument
from core.instruments.resolver import InstrumentResolver


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "instruments.duckdb"
    rows = [
        {"segment": "NSE_EQ", "instrument_key": "NSE_EQ|INE002A01018",
         "tradingsymbol": "RELIANCE", "name": "RELIANCE INDUSTRIES",
         "instrument_type": "EQ", "lot_size": 1, "tick_size": 0.05,
         "isin": "INE002A01018"},
        {"segment": "NSE_INDEX", "instrument_key": "NSE_INDEX|Nifty 50",
         "tradingsymbol": "Nifty 50", "name": "Nifty 50",
         "instrument_type": "INDEX", "lot_size": 0, "tick_size": 0.0},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|53001",
         "tradingsymbol": "NIFTY26FEBFUT", "name": "NIFTY",
         "expiry": "2026-02-26", "instrument_type": "FUT",
         "lot_size": 75, "tick_size": 0.05},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|54710",
         "tradingsymbol": "NIFTY26FEB2522500CE", "name": "NIFTY",
         "expiry": "2026-02-25", "strike_price": 22500.0,
         "instrument_type": "CE", "lot_size": 75, "tick_size": 0.05},
    ]
    write_snapshot(parse_instruments(rows, "2026-02-01"), db_path=path)
    return path


def test_upstox_mapping_is_a_broker_mapping(db):
    assert isinstance(UpstoxMapping(db_path=db), BrokerMapping)


def test_to_broker_maps_option_to_instrument_key(db):
    m = UpstoxMapping(db_path=db)
    r = InstrumentResolver(db_path=db)
    ci = r.resolve_option("NIFTY", date(2026, 2, 25), 22500.0, "CE")
    ref = m.to_broker(ci)
    assert isinstance(ref, BrokerRef)
    assert ref.instrument_key == "NSE_FO|54710"
    assert ref.tradingsymbol == "NIFTY26FEB2522500CE"


def test_round_trip_preserves_identity_for_all_classes(db):
    m = UpstoxMapping(db_path=db)
    r = InstrumentResolver(db_path=db)
    originals = [
        r.resolve_equity("INE002A01018"),
        r.resolve_future("NIFTY", as_of=date(2026, 2, 1)),
        r.resolve_option("NIFTY", date(2026, 2, 25), 22500.0, "CE"),
    ]
    for ci in originals:
        ref = m.to_broker(ci)
        back = m.from_broker_position({"instrument_token": ref.instrument_key})
        assert back == ci


def test_from_broker_position_by_trading_symbol(db):
    m = UpstoxMapping(db_path=db)
    r = InstrumentResolver(db_path=db)
    ci = r.resolve_option("NIFTY", date(2026, 2, 25), 22500.0, "CE")
    back = m.from_broker_position(
        {"trading_symbol": "NIFTY26FEB2522500CE", "quantity": "-75"})
    assert back.canonical_id == ci.canonical_id


def test_product_code_translation(db):
    m = UpstoxMapping(db_path=db)
    r = InstrumentResolver(db_path=db)
    ci = r.resolve_option("NIFTY", date(2026, 2, 25), 22500.0, "CE")
    assert m.to_broker(dataclasses.replace(ci, product="MIS")).product_code == "I"
    assert m.to_broker(dataclasses.replace(ci, product="NRML")).product_code == "D"
    assert m.to_broker(dataclasses.replace(ci, product="CNC")).product_code == "D"


def test_to_broker_unmapped_instrument_raises(db):
    m = UpstoxMapping(db_path=db)
    ghost = CanonicalInstrument(asset_class=AssetClass.EQUITY, exchange="NSE",
                                isin="INE000X00000")
    with pytest.raises(LookupError):
        m.to_broker(ghost)


def test_from_broker_unknown_returns_none(db):
    m = UpstoxMapping(db_path=db)
    assert m.from_broker_position({"instrument_token": "NSE_FO|00000"}) is None


def test_mapping_imports_no_strategy_code():
    import core.brokers.mapping.base as base_mod
    import core.brokers.mapping.upstox as upstox_mod

    for mod in (base_mod, upstox_mod):
        tree = ast.parse(pathlib.Path(mod.__file__).read_text(encoding="utf-8"))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
        joined = " ".join(names)
        for forbidden in ("strategies", "runner", "backtest", "ftmo"):
            assert forbidden not in joined
