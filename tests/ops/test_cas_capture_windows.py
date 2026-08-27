import inspect
from datetime import datetime

from core.database.utils.market_hours import MarketHours


def test_derivatives_tail_is_inside_the_capture_window():
    # 15:35 on a post-CAS trading day: cash shut, F&O live.
    dt = datetime(2026, 8, 3, 15, 35)
    assert not MarketHours.is_market_open(dt)
    assert MarketHours.is_derivatives_open(dt)
    assert MarketHours.is_any_open(dt)


def test_chain_poller_gates_on_derivatives_not_cash():
    from scripts.nifty_shield_paper import chain_poller

    source = inspect.getsource(chain_poller)
    assert "is_derivatives_open" in source
    assert "if not MarketHours.is_market_open()" not in source


def test_wall_poller_gates_on_derivatives_not_cash():
    from core.options_wall import poller

    source = inspect.getsource(poller)
    assert "is_derivatives_open" in source
    assert "if not MarketHours.is_market_open()" not in source


def test_market_ingestor_gates_on_any_open():
    import scripts.market_ingestor as ingestor

    source = inspect.getsource(ingestor)
    assert "is_any_open" in source
