"""Iron-fly builder: ATM centering, %-snapped wings, credit/margin, marking, spread cap."""
from datetime import date

import pytest

from core.data.options_provider import OptionChainRow
from core.options_wall.fly import (build_iron_fly, exit_fees, mark_to_close,
                                    unrealized_pnl)

TRADE_DATE = date(2026, 8, 14)

# spot 100; realistic premia — CE decreases with strike, PE increases with strike,
# ATM richest relative to OTM wings so an ATM short straddle collects net credit.
_PREMIA = {
    97: (4.0, 0.5), 98: (3.2, 0.8), 99: (2.5, 1.2), 100: (1.8, 1.8),
    101: (1.2, 2.5), 102: (0.8, 3.2), 103: (0.5, 4.0),
}


def _mid_row(strike, ot, ltp, spread=0.02):
    r = OptionChainRow(strike=float(strike), option_type=ot,
                       instrument_key=f"{ot}{strike}", tradingsymbol=f"{ot}{strike}",
                       expiry="2026-08-18", ltp=ltp, underlying_ltp=100.0)
    r.best_bid = ltp - spread / 2
    r.best_ask = ltp + spread / 2
    return r


def _chain(spread=0.02):
    rows = []
    for k, (ce, pe) in _PREMIA.items():
        rows.append(_mid_row(k, "CE", ce, spread))
        rows.append(_mid_row(k, "PE", pe, spread))
    return rows


def test_build_fly_centers_atm_and_snaps_wings():
    fly = build_iron_fly(_chain(), spot=100.0, wing_pct=0.03, qty=75, trade_date=TRADE_DATE)
    assert fly.short_strike == 100.0
    assert fly.call_wing == 103.0   # nearest listed to 100*1.03
    assert fly.put_wing == 97.0     # nearest listed to 100*0.97


def test_build_fly_net_credit_and_max_loss():
    fly = build_iron_fly(_chain(), spot=100.0, wing_pct=0.03, qty=75, trade_date=TRADE_DATE)
    # credit/unit = (CE100 1.8 + PE100 1.8) - (CE103 0.5 + PE97 0.5) = 2.6
    assert fly.net_credit_per_unit == pytest.approx(2.6)
    assert fly.net_credit == pytest.approx(195.0)
    # width = max(103-100, 100-97) = 3 -> width value 3*75=225; max loss = 225-195
    assert fly.max_loss == pytest.approx(30.0)
    assert fly.entry_fees > 0


def test_build_fly_returns_none_when_a_wing_leg_missing():
    chain = [r for r in _chain() if not (r.strike == 103.0 and r.option_type == "CE")]
    assert build_iron_fly(chain, spot=100.0, wing_pct=0.03, qty=75, trade_date=TRADE_DATE) is None


def test_build_fly_returns_none_when_a_leg_spread_too_wide():
    # widen only the ATM CE far beyond the 5% cap
    chain = _chain()
    for r in chain:
        if r.strike == 100.0 and r.option_type == "CE":
            r.best_bid, r.best_ask = 1.0, 3.0   # (3-1)/2 = 100% spread
    assert build_iron_fly(chain, spot=100.0, wing_pct=0.03, qty=75,
                          trade_date=TRADE_DATE, max_spread_pct=0.05) is None


def test_build_fly_requires_live_book_on_each_leg():
    # entry requires a live bid/ask per leg (spec §3); ltp-only must not open
    chain = _chain()
    for r in chain:
        if r.strike == 100.0 and r.option_type == "CE":
            r.best_bid = None
            r.best_ask = None
    assert build_iron_fly(chain, spot=100.0, wing_pct=0.03, qty=75,
                          trade_date=TRADE_DATE) is None


def test_unrealized_pnl_zero_when_marks_equal_entry():
    fly = build_iron_fly(_chain(), spot=100.0, wing_pct=0.03, qty=75, trade_date=TRADE_DATE)
    mids = {(l.strike, l.option_type): l.entry_mid for l in fly.legs}
    assert unrealized_pnl(fly, mids) == pytest.approx(0.0)


def test_unrealized_pnl_positive_when_cheaper_to_close():
    fly = build_iron_fly(_chain(), spot=100.0, wing_pct=0.03, qty=75, trade_date=TRADE_DATE)
    # halve every leg mid -> cost to close halves -> profit
    mids = {(l.strike, l.option_type): l.entry_mid / 2 for l in fly.legs}
    assert unrealized_pnl(fly, mids) > 0
    assert exit_fees(fly, mids, TRADE_DATE) > 0


# --------------------------------------------------------------------------- #
# Tick-aware quote-spread guard (operator finding, 2026-09-08)
# --------------------------------------------------------------------------- #

def test_one_tick_book_on_a_cheap_wing_is_not_a_wide_spread():
    """The live 2026-09-08 iron fly: a 23300 PE quoted 0.45/0.50 was rejected at
    "10.5%" for a ONE-TICK spread, while a 24000 CE at 1.05/1.10 passed at 4.7%
    for the SAME one tick. A percentage-only guard is unsatisfiable below
    `tick / max_pct` (Re 1.00 at the 5% default), so it was a price threshold
    wearing a liquidity guard's clothes -- and it bit the deep-OTM wings, which
    are a fly's cheapest legs by construction."""
    from core.analytics.options_selection import spread_ok

    ok, pct = spread_ok(0.45, 0.50, 0.05)
    assert ok, "a one-tick book is the tightest the exchange can express"
    assert pct > 0.10                       # ...and still reports as >10%

    ok_rich, pct_rich = spread_ok(1.05, 1.10, 0.05)
    assert ok_rich and pct_rich < 0.05      # same one tick, passed before too


def test_genuinely_wide_books_still_fail():
    """The floor is ONE tick, not an exemption for cheap options."""
    from core.analytics.options_selection import spread_ok

    assert not spread_ok(0.45, 0.60, 0.05)[0]     # 3 ticks on a cheap leg
    assert not spread_ok(100.0, 110.0, 0.05)[0]   # 9.5% on a rich leg
    assert not spread_ok(0.0, 0.50, 0.05)[0]      # no bid


def _quoted_row(strike, ot, bid, ask):
    r = OptionChainRow(strike=float(strike), option_type=ot,
                       instrument_key=f"{ot}{strike}", tradingsymbol=f"{ot}{strike}",
                       expiry="2026-09-15", ltp=(bid + ask) / 2,
                       underlying_ltp=23650.0)
    r.best_bid, r.best_ask = bid, ask
    return r


def test_build_iron_fly_accepts_a_one_tick_wing():
    """End-to-end: the fly the operator saw must now build."""
    from core.options_wall.fly import build_iron_fly

    chain = [
        _quoted_row(23650, "CE", 47.15, 47.30),
        _quoted_row(23650, "PE", 28.50, 28.55),
        _quoted_row(24000, "CE", 1.05, 1.10),
        _quoted_row(23300, "PE", 0.45, 0.50),
    ]
    fly = build_iron_fly(chain, spot=23650.0, wing_pct=0.015, qty=65,
                         trade_date=date(2026, 9, 8), max_spread_pct=0.05)
    assert fly is not None, "the one-tick wing still blocks the structure"
    assert fly.short_strike == 23650
    assert {l.strike for l in fly.legs} == {23650, 24000, 23300}
