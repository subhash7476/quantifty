"""
Phase 4C.5 — Build-seam adaptation (CANONICAL_INSTRUMENT_ARCHITECTURE.md §D9.5).

Conservative slice: OptionsContractSelector keeps its selection *policy* and keeps
returning a legacy `Option`, but sources the real `lot_size` from the master via
InstrumentResolver when the master is present. When the master is absent (today's
runtime), it falls back to the hardcoded INDEX_LOT_SIZES byte-for-byte — so the
output type and identity never flip on DB presence (ADR-003 determinism). Full
CanonicalInstrument flow into orders is deferred to 4C.7 (needs the materialized DB).
"""
from datetime import date, datetime

from scripts.fetch_instrument_master import parse_instruments, write_snapshot
from core.events import SignalType
from core.execution.options.selector import OptionsContractSelector, INDEX_LOT_SIZES
from core.instruments.option import Option, OptionType
from core.instruments.resolver import InstrumentResolver


_TS = datetime(2026, 2, 1, 13, 0)
_POLICY = {"expiry_date": date(2026, 2, 25)}


def test_falls_back_to_hardcoded_lot_when_master_absent(tmp_path):
    resolver = InstrumentResolver(db_path=tmp_path / "absent.duckdb")
    sel = OptionsContractSelector(resolver=resolver)
    opt = sel.select("NSE_INDEX|Nifty 50", 22500.0, SignalType.BUY, _TS, _POLICY)
    assert isinstance(opt, Option)
    assert opt.lot_size == INDEX_LOT_SIZES["NSE_INDEX|Nifty 50"] == 75


def test_uses_resolver_lot_size_when_master_present(tmp_path):
    path = tmp_path / "instruments.duckdb"
    rows = [{
        "segment": "NSE_FO", "instrument_key": "NSE_FO|54710",
        "tradingsymbol": "NIFTY25FEB2622500CE", "name": "NIFTY",
        "expiry": "2026-02-25", "strike_price": 22500.0,
        "instrument_type": "CE", "lot_size": 50, "tick_size": 5,
    }]
    write_snapshot(parse_instruments(rows, "2026-02-01"), db_path=path)
    sel = OptionsContractSelector(resolver=InstrumentResolver(db_path=path))
    opt = sel.select("NSE_INDEX|Nifty 50", 22500.0, SignalType.BUY, _TS, _POLICY)
    # master says 50, overriding the hardcoded 75
    assert opt.lot_size == 50


def test_symbol_strike_and_type_unchanged_by_resolver(tmp_path):
    """Identity construction (symbol/strike/expiry/type) is unchanged — only the
    lot_size source moves."""
    sel = OptionsContractSelector(resolver=InstrumentResolver(db_path=tmp_path / "absent.duckdb"))
    opt = sel.select("NSE_INDEX|Nifty 50", 22500.0, SignalType.BUY, _TS, _POLICY)
    assert opt.symbol == "NIFTY25FEB2622500CE"
    assert opt.strike == 22500.0
    assert opt.expiry == date(2026, 2, 25)
    assert opt.option_type == OptionType.CALL


def test_policy_override_beats_resolver(tmp_path):
    path = tmp_path / "instruments.duckdb"
    rows = [{
        "segment": "NSE_FO", "instrument_key": "NSE_FO|54710",
        "tradingsymbol": "NIFTY25FEB2622500CE", "name": "NIFTY",
        "expiry": "2026-02-25", "strike_price": 22500.0,
        "instrument_type": "CE", "lot_size": 50, "tick_size": 5,
    }]
    write_snapshot(parse_instruments(rows, "2026-02-01"), db_path=path)
    sel = OptionsContractSelector(resolver=InstrumentResolver(db_path=path))
    policy = {"expiry_date": date(2026, 2, 25), "lot_size_override": 25}
    opt = sel.select("NSE_INDEX|Nifty 50", 22500.0, SignalType.BUY, _TS, policy)
    assert opt.lot_size == 25


def test_default_selector_preserves_legacy_behavior():
    """OptionsContractSelector() with no resolver (handler's call site) behaves
    exactly as before: legacy Option, hardcoded lot."""
    sel = OptionsContractSelector()
    opt = sel.select("NSE_INDEX|Nifty 50", 22500.0, SignalType.BUY, _TS, _POLICY)
    assert isinstance(opt, Option)
    assert opt.lot_size == 75
