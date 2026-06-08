"""
Phase 4C.6 — GreeksCalculator dispatches on asset_class (close the isinstance surface).

GreeksCalculator.calculate previously branched on `isinstance(instrument, Equity/
Future/Option)` — a legacy subclass tree that a `CanonicalInstrument` (asset_class-
discriminated, no subclass) silently misses, falling through to zero Greeks. 4C.6
dispatches on the asset class: canonical objects expose `.asset_class`; legacy
objects are normalised from `.type` (InstrumentType names align with AssetClass).

RED here = the canonical-input cases (they return zero on the isinstance code) and
the source guard. The legacy cases are parity guards — they must stay identical.
"""
import ast
import inspect
import textwrap
from datetime import date

from core.instruments.equity import Equity
from core.instruments.future import Future
from core.instruments.option import Option, OptionType
from core.instruments.canonical import AssetClass, CanonicalInstrument
from core.risk.greeks.greeks_calculator import GreeksCalculator
from core.risk.greeks.black76_engine import Black76Engine
from core.risk.greeks.greeks_model import Greeks


# --- legacy parity (must not change) ---------------------------------------

def test_legacy_equity_delta_is_signed_quantity():
    g = GreeksCalculator.calculate(Equity("RELIANCE"), quantity=100, underlying_price=2600.0)
    assert g == Greeks(delta=100.0, gamma=0.0, vega=0.0, theta=0.0, rho=0.0)


def test_legacy_future_delta_scaled_by_multiplier():
    fut = Future("NIFTY26JUNFUT", underlying="NIFTY", expiry=date(2026, 6, 25), multiplier=75.0)
    g = GreeksCalculator.calculate(fut, quantity=2, underlying_price=23100.0)
    assert g.delta == 150.0
    assert (g.gamma, g.vega, g.theta, g.rho) == (0.0, 0.0, 0.0, 0.0)


def test_legacy_option_matches_black76():
    opt = Option(symbol="NIFTY26JUN23000CE", underlying="NIFTY", expiry=date(2026, 6, 25),
                 strike=23000.0, option_type=OptionType.CALL, lot_size=50, multiplier=1.0)
    g = GreeksCalculator.calculate(opt, quantity=-50.0, underlying_price=23100.0,
                                   volatility=0.15, time_to_expiry=0.05, risk_free_rate=0.05)
    expected = Black76Engine.calculate_greeks(
        F=23100.0, K=23000.0, T=0.05, r=0.05, sigma=0.15, option_type=OptionType.CALL
    ) * (-50.0 * 1.0)
    assert g == expected


# --- canonical dispatch (the new capability — RED on the isinstance code) ----

def test_canonical_equity_dispatches():
    ci = CanonicalInstrument(asset_class=AssetClass.EQUITY, exchange="NSE",
                             isin="INE002A01018", lot_size=1)
    g = GreeksCalculator.calculate(ci, quantity=100, underlying_price=2600.0)
    assert g == Greeks(delta=100.0, gamma=0.0, vega=0.0, theta=0.0, rho=0.0)


def test_canonical_future_delta_uses_lot_size_multiplier():
    ci = CanonicalInstrument(asset_class=AssetClass.FUTURE, exchange="NSE",
                             underlying="NIFTY", expiry=date(2026, 6, 25), lot_size=75)
    g = GreeksCalculator.calculate(ci, quantity=2, underlying_price=23100.0)
    assert g.delta == 150.0  # qty * multiplier(==lot_size)


def test_canonical_option_matches_black76():
    ci = CanonicalInstrument(asset_class=AssetClass.OPTION, exchange="NSE",
                             underlying="NIFTY", expiry=date(2026, 6, 25),
                             strike=23000.0, option_type=OptionType.CALL, lot_size=50)
    g = GreeksCalculator.calculate(ci, quantity=-1.0, underlying_price=23100.0,
                                   volatility=0.15, time_to_expiry=0.05, risk_free_rate=0.05)
    expected = Black76Engine.calculate_greeks(
        F=23100.0, K=23000.0, T=0.05, r=0.05, sigma=0.15, option_type=OptionType.CALL
    ) * (-1.0 * 50.0)  # multiplier == lot_size
    assert g == expected


def test_canonical_index_returns_zero():
    """INDEX is a non-tradable reference underlying — no Greeks."""
    ci = CanonicalInstrument(asset_class=AssetClass.INDEX, exchange="NSE", underlying="NIFTY")
    g = GreeksCalculator.calculate(ci, quantity=1, underlying_price=23100.0)
    assert g == Greeks(0.0, 0.0, 0.0, 0.0, 0.0)


# --- structural guard: the legacy subclass isinstance tree is gone ----------

def test_no_isinstance_dispatch_on_legacy_subtypes():
    src = textwrap.dedent(inspect.getsource(GreeksCalculator.calculate))
    tree = ast.parse(src)
    legacy_types = {"Equity", "Future", "Option"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "isinstance":
            names = {a.id for a in node.args if isinstance(a, ast.Name)}
            assert not (names & legacy_types), (
                f"calculate() still isinstance-dispatches on legacy subtypes {names & legacy_types}"
            )
