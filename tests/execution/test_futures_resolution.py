"""
G1 Wave 2 Migration #1 — unit coverage for `resolve_future`.

The characterization suite (test_g1_characterization.py) pins the master-PRESENT
futures case end-to-end. These unit tests cover the two branches it does not:
  - a non-future symbol returns None (equity/option passthrough is unchanged), and
  - the master-ABSENT path still derives a FUTURE (ADR-003: type never flips on
    DB presence), with the symbol preserved byte-identical.
"""
from datetime import date, datetime

import pytz

from core.execution.futures import resolve_future
from core.instruments.future import Future
from core.instruments.instrument_base import InstrumentType
from core.instruments.resolver import InstrumentResolver

AS_OF = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


def test_non_future_symbols_return_none():
    # Equity and raw option symbols must fall through to InstrumentParser unchanged.
    assert resolve_future("RELIANCE", AS_OF) is None
    assert resolve_future("NIFTY16JUN2622500CE", AS_OF) is None


def test_master_present_resolves_canonical_lot_and_expiry():
    fut = resolve_future("NIFTY26JUNFUT", AS_OF)
    assert isinstance(fut, Future)
    assert fut.symbol == "NIFTY26JUNFUT"          # broker payload identity preserved
    assert fut.type == InstrumentType.FUTURE
    assert fut.underlying == "NIFTY"
    # Canonical-sourced from the on-disk master: nearest active NIFTY FUT, lot 65.
    assert fut.expiry == date(2026, 6, 30)
    assert fut.multiplier == 65.0


def test_master_absent_still_derives_future(tmp_path):
    # Resolver pointed at a non-existent master -> resolve_future returns None,
    # but the FUTURE type is still derived from the symbol (no type flip on DB
    # presence). Expiry falls back to the symbol-parsed month.
    empty = InstrumentResolver(db_path=tmp_path / "absent.duckdb")
    fut = resolve_future("NIFTY26JUNFUT", AS_OF, resolver=empty)
    assert isinstance(fut, Future)
    assert fut.symbol == "NIFTY26JUNFUT"
    assert fut.type == InstrumentType.FUTURE
    assert fut.underlying == "NIFTY"
    assert fut.expiry == date(2026, 6, 1)
    assert fut.multiplier == 1.0
