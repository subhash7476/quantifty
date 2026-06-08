"""
Phase 4C.2 — CanonicalInstrument value object
(CANONICAL_INSTRUMENT_ARCHITECTURE.md §D2/§D3).

One immutable, asset_class-discriminated value object. Resolves the
multiplier/lot_size duality (§D3.1: multiplier == lot_size), marks INDEX as
non-tradable (§D2.2), validates required fields per class, and imports no broker
or strategy code (ADR-002 / §D6.3).
"""
import ast
import pathlib
from datetime import date

import pytest

from core.instruments.canonical import AssetClass, CanonicalInstrument
from core.instruments.option import OptionType


def _opt():
    return CanonicalInstrument(
        asset_class=AssetClass.OPTION, exchange="NSE",
        underlying="NSE_INDEX|Nifty 50", expiry=date(2026, 2, 25),
        strike=22500.0, option_type=OptionType.CALL, lot_size=75,
        tick_size=0.05, display_symbol="NIFTY26FEB2522500CE",
    )


def test_option_mints_canonical_id():
    assert _opt().canonical_id == "NSE:OPT:NIFTY:2026-02-25:22500:CE"


def test_multiplier_equals_lot_size():
    ci = _opt()
    assert ci.multiplier == ci.lot_size == 75


def test_equity_multiplier_is_one_and_keys_on_isin():
    eq = CanonicalInstrument(asset_class=AssetClass.EQUITY, exchange="NSE",
                             isin="INE002A01018")
    assert eq.lot_size == 1
    assert eq.multiplier == 1.0
    assert eq.canonical_id == "NSE:EQ:INE002A01018"


def test_index_is_not_tradable():
    idx = CanonicalInstrument(asset_class=AssetClass.INDEX, exchange="NSE",
                              underlying="NSE_INDEX|Nifty 50")
    assert idx.tradable is False
    assert idx.canonical_id == "NSE:IDX:NIFTY"


def test_option_is_tradable():
    assert _opt().tradable is True


def test_instance_is_frozen():
    ci = _opt()
    with pytest.raises(Exception):
        ci.lot_size = 1


def test_option_requires_strike():
    with pytest.raises(ValueError):
        CanonicalInstrument(
            asset_class=AssetClass.OPTION, exchange="NSE", underlying="NIFTY",
            expiry=date(2026, 2, 25), option_type=OptionType.CALL,
        )


def test_equity_requires_isin():
    with pytest.raises(ValueError):
        CanonicalInstrument(asset_class=AssetClass.EQUITY, exchange="NSE")


def test_symbol_prefers_display_symbol():
    assert _opt().symbol == "NIFTY26FEB2522500CE"


def test_symbol_falls_back_to_canonical_id():
    idx = CanonicalInstrument(asset_class=AssetClass.INDEX, exchange="NSE",
                              underlying="NIFTY")
    assert idx.symbol == "NSE:IDX:NIFTY"


def test_no_broker_or_strategy_import_in_canonical_core():
    import core.instruments.canonical as canonical_mod
    import core.instruments.identity as identity_mod

    for mod in (canonical_mod, identity_mod):
        tree = ast.parse(pathlib.Path(mod.__file__).read_text(encoding="utf-8"))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
        joined = " ".join(names)
        assert "broker" not in joined
        for forbidden in ("strategies", "runner", "backtest", "ftmo"):
            assert forbidden not in joined
