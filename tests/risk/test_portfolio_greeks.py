"""
Phase 0 hygiene — PortfolioGreeks dict-iteration defect.

Discovery finding (PORTFOLIO_STATE_DISCOVERY.md §4.6): calculate_portfolio_greeks
iterated `for position in get_all_positions()` where get_all_positions() returns a
Dict[str, Position]. Iterating a dict yields its KEYS (symbol strings), so a `str`
was passed where a `Position` was expected -> AttributeError on the first non-empty
book. These tests prove correct aggregation over real Position objects, determinism,
sign-by-side, that the Option branch is reached, and that the empty-book behavior is
unchanged.
"""

from datetime import date

from core.execution.position_tracker import PositionTracker
from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity
from core.instruments.option import Option, OptionType
from core.risk.greeks.portfolio_greeks import PortfolioGreeks
from core.risk.greeks.greeks_calculator import GreeksCalculator
from core.risk.greeks.greeks_model import Greeks


def _tracker_with(*positions: Position) -> PositionTracker:
    pt = PositionTracker()
    for pos in positions:
        pt._positions[pos.symbol] = pos
    return pt


def test_processes_nonempty_position_set():
    """A non-empty book must be aggregated, not crash on str keys."""
    pt = _tracker_with(
        Position(instrument=Equity("RELIANCE"), side=PositionSide.LONG,
                 quantity=100, avg_price=2500.0),
    )
    pg = PortfolioGreeks(pt)

    net = pg.calculate_portfolio_greeks(
        market_prices={"RELIANCE": 2600.0},
        volatilities={},
        time_to_expiry_map={},
    )

    # Equity delta == signed quantity; other greeks zero.
    assert net.delta == 100.0
    assert net.gamma == 0.0
    assert net.vega == 0.0


def test_aggregation_sums_signed_by_side():
    """LONG contributes +qty delta, SHORT contributes -qty delta."""
    pt = _tracker_with(
        Position(instrument=Equity("RELIANCE"), side=PositionSide.LONG,
                 quantity=100, avg_price=2500.0),
        Position(instrument=Equity("TCS"), side=PositionSide.SHORT,
                 quantity=40, avg_price=3500.0),
    )
    pg = PortfolioGreeks(pt)

    net = pg.calculate_portfolio_greeks(
        market_prices={"RELIANCE": 2600.0, "TCS": 3400.0},
        volatilities={},
        time_to_expiry_map={},
    )

    assert net.delta == 60.0  # 100 long - 40 short


def test_aggregation_is_deterministic():
    """Same inputs -> identical Greeks across repeated calls (ADR-003)."""
    pt = _tracker_with(
        Position(instrument=Equity("RELIANCE"), side=PositionSide.LONG,
                 quantity=100, avg_price=2500.0),
        Position(instrument=Equity("TCS"), side=PositionSide.SHORT,
                 quantity=40, avg_price=3500.0),
    )
    pg = PortfolioGreeks(pt)
    prices = {"RELIANCE": 2600.0, "TCS": 3400.0}

    first = pg.calculate_portfolio_greeks(prices, {}, {})
    second = pg.calculate_portfolio_greeks(prices, {}, {})

    assert first == second


def test_option_branch_matches_single_position_calc():
    """A one-option book equals the GreeksCalculator result for that leg
    (proves a real Position, not a str key, reaches the option branch)."""
    opt = Option(
        symbol="NIFTY26JUN23000CE",
        underlying="NIFTY",
        expiry=date(2026, 6, 25),
        strike=23000.0,
        option_type=OptionType.CALL,
        lot_size=50,
        multiplier=1.0,
    )
    pt = _tracker_with(
        Position(instrument=opt, side=PositionSide.SHORT,
                 quantity=50, avg_price=120.0),
    )
    pg = PortfolioGreeks(pt)

    net = pg.calculate_portfolio_greeks(
        market_prices={"NIFTY": 23100.0},
        volatilities={opt.symbol: 0.15},
        time_to_expiry_map={opt.symbol: 0.05},
    )

    expected = GreeksCalculator.calculate(
        instrument=opt,
        quantity=-50.0,  # SHORT
        underlying_price=23100.0,
        volatility=0.15,
        time_to_expiry=0.05,
        risk_free_rate=0.05,
    )
    assert net == expected


def test_empty_portfolio_is_zero():
    """Empty book stays Greeks(0,...) — existing behavior unchanged."""
    pg = PortfolioGreeks(PositionTracker())

    net = pg.calculate_portfolio_greeks({}, {}, {})

    assert net == Greeks(0.0, 0.0, 0.0, 0.0, 0.0)
