"""
Phase 4C.3 — InstrumentResolver (CANONICAL_INSTRUMENT_ARCHITECTURE.md §D7).

The resolver is the only reader of the master SSOT and returns CanonicalInstrument
objects. It is deterministic and point-in-time (`as_of`): lot sizes change over
time (the SEBI 50->75 revision, §D7.4), so resolution must pick the snapshot
effective at the trade date. When the master is absent it fails loud (returns
None), never silently wrong.

The fixture master is built through the real 4C.1 ingest pipeline.
"""
import logging
from datetime import date

import pytest

from scripts.fetch_instrument_master import parse_instruments, write_snapshot
from core.instruments.canonical import AssetClass
from core.instruments.option import OptionType
from core.instruments.resolver import InstrumentResolver


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "instruments.duckdb"
    current = [
        {"segment": "NSE_EQ", "instrument_key": "NSE_EQ|INE002A01018",
         "tradingsymbol": "RELIANCE", "name": "RELIANCE INDUSTRIES",
         "instrument_type": "EQ", "lot_size": 1, "tick_size": 5,
         "isin": "INE002A01018"},
        {"segment": "NSE_INDEX", "instrument_key": "NSE_INDEX|Nifty 50",
         "tradingsymbol": "Nifty 50", "name": "Nifty 50",
         "instrument_type": "INDEX", "lot_size": 0, "tick_size": 0.0},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|53001",
         "tradingsymbol": "NIFTY26FEBFUT", "name": "NIFTY",
         "expiry": "2026-02-26", "instrument_type": "FUT",
         "lot_size": 75, "tick_size": 5},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|53002",
         "tradingsymbol": "NIFTY26MARFUT", "name": "NIFTY",
         "expiry": "2026-03-26", "instrument_type": "FUT",
         "lot_size": 75, "tick_size": 5},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|54710",
         "tradingsymbol": "NIFTY26FEB2522500CE", "name": "NIFTY",
         "expiry": "2026-02-25", "strike_price": 22500.0,
         "instrument_type": "CE", "lot_size": 75, "tick_size": 5},
    ]
    write_snapshot(parse_instruments(current, "2026-02-01"), db_path=path)

    # Same logical option in two snapshots with different lot sizes (as_of test).
    revised = {"segment": "NSE_FO", "instrument_key": "NSE_FO|99999",
               "tradingsymbol": "NIFTY24DEC2522500CE", "name": "NIFTY",
               "expiry": "2024-12-25", "strike_price": 22500.0,
               "instrument_type": "CE", "tick_size": 5}
    write_snapshot(parse_instruments([{**revised, "lot_size": 50}], "2024-01-01"), db_path=path)
    write_snapshot(parse_instruments([{**revised, "lot_size": 75}], "2024-12-01"), db_path=path)
    return path


def test_resolve_equity(db):
    r = InstrumentResolver(db_path=db)
    ci = r.resolve_equity("INE002A01018")
    assert ci.asset_class == AssetClass.EQUITY
    assert ci.canonical_id == "NSE:EQ:INE002A01018"
    assert ci.isin == "INE002A01018"
    assert ci.multiplier == 1.0


def test_resolve_index(db):
    r = InstrumentResolver(db_path=db)
    ci = r.resolve_index("NSE_INDEX|Nifty 50")
    assert ci.asset_class == AssetClass.INDEX
    assert ci.canonical_id == "NSE:IDX:NIFTY"
    assert ci.tradable is False


def test_resolve_future_picks_nearest_active(db):
    r = InstrumentResolver(db_path=db, as_of=date(2026, 2, 1))
    ci = r.resolve_future("NIFTY")
    assert ci.asset_class == AssetClass.FUTURE
    assert ci.expiry == date(2026, 2, 26)
    assert ci.canonical_id == "NSE:FUT:NIFTY:2026-02-26"


def test_resolve_option(db):
    r = InstrumentResolver(db_path=db)
    ci = r.resolve_option("NSE_INDEX|Nifty 50", date(2026, 2, 25), 22500.0, OptionType.CALL)
    assert ci.asset_class == AssetClass.OPTION
    assert ci.canonical_id == "NSE:OPT:NIFTY:2026-02-25:22500:CE"
    assert ci.lot_size == 75
    assert ci.display_symbol == "NIFTY26FEB2522500CE"


def test_resolve_option_as_of_returns_effective_lot_size(db):
    r_old = InstrumentResolver(db_path=db, as_of=date(2024, 6, 1))
    r_new = InstrumentResolver(db_path=db, as_of=date(2025, 6, 1))
    old = r_old.resolve_option("NIFTY", date(2024, 12, 25), 22500.0, "CE")
    new = r_new.resolve_option("NIFTY", date(2024, 12, 25), 22500.0, "CE")
    assert old.lot_size == 50
    assert new.lot_size == 75


def test_resolution_is_cached_and_deterministic(db):
    r = InstrumentResolver(db_path=db)
    a = r.resolve_option("NIFTY", date(2026, 2, 25), 22500.0, OptionType.CALL)
    b = r.resolve_option("NIFTY", date(2026, 2, 25), 22500.0, OptionType.CALL)
    assert a is b  # served from cache, same instance


def test_absent_master_returns_none_not_crash(tmp_path):
    r = InstrumentResolver(db_path=tmp_path / "does_not_exist.duckdb")
    assert r.resolve_equity("INE002A01018") is None
    assert r.resolve_option("NIFTY", date(2026, 2, 25), 22500.0, "CE") is None


def test_as_of_before_history_warns_and_returns_earliest(db, caplog):
    """as_of preceding every snapshot is a stale-data hazard (Constitution §6,
    ADR-004): the earliest snapshot may carry wrong attributes, so the fallback
    must be observable, never silent."""
    r = InstrumentResolver(db_path=db, as_of=date(2020, 1, 1))
    with caplog.at_level(logging.WARNING, logger="core.instruments.resolver"):
        ci = r.resolve_option("NIFTY", date(2024, 12, 25), 22500.0, "CE")
    assert ci.lot_size == 50  # earliest available snapshot
    assert any("snapshot" in rec.message.lower() for rec in caplog.records)


def test_resolve_by_instrument_key(db):
    """Broker bridge support (4C.4): map a broker instrument_key back to canonical."""
    r = InstrumentResolver(db_path=db)
    ci = r.resolve_by_instrument_key("NSE_FO|54710")
    assert ci.canonical_id == "NSE:OPT:NIFTY:2026-02-25:22500:CE"
    assert ci.display_symbol == "NIFTY26FEB2522500CE"


def test_resolve_by_instrument_key_unknown_returns_none(db):
    r = InstrumentResolver(db_path=db)
    assert r.resolve_by_instrument_key("NSE_FO|00000") is None
