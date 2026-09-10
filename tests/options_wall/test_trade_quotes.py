"""Widened leg quotes must not move the mark arithmetic."""
import json

from core.data.options_provider import OptionChainRow
from core.options_wall.engine import _open_trade_marks, _snapshot_quotes


def _row(strike, ot, **kw):
    r = OptionChainRow(strike=strike, option_type=ot, instrument_key=f"{ot}{strike}",
                       tradingsymbol=f"{ot}{strike}", expiry="2026-09-15",
                       ltp=kw.pop("ltp", 10.0), underlying_ltp=100.0, **kw)
    r.best_bid = kw.get("best_bid")
    r.best_ask = kw.get("best_ask")
    return r


def _fly_trade(qty=75, credit=7500.0):
    legs = [{"side": "SELL", "type": "CE", "strike": 100.0, "mid": 50.0},
            {"side": "SELL", "type": "PE", "strike": 100.0, "mid": 50.0},
            {"side": "BUY", "type": "CE", "strike": 102.0, "mid": 25.0},
            {"side": "BUY", "type": "PE", "strike": 98.0, "mid": 25.0}]
    return {"qty": qty, "net_credit": credit, "entry_legs": json.dumps(legs)}


def _quoted_chain():
    rows = []
    for strike, ot, bid, ask in ((100.0, "CE", 39.0, 41.0), (100.0, "PE", 39.0, 41.0),
                                 (102.0, "CE", 19.0, 21.0), (98.0, "PE", 19.0, 21.0)):
        r = _row(strike, ot, iv=14.5, delta=0.5, gamma=0.01, theta=-3.0, vega=1.2,
                 oi=1000, volume=50)
        r.best_bid, r.best_ask = bid, ask
        rows.append(r)
    return rows


def test_quote_carries_bid_ask_ltp_iv_and_greeks():
    q = _snapshot_quotes(_quoted_chain())[(100.0, "CE")]
    assert q["bid"] == 39.0 and q["ask"] == 41.0
    assert q["mid"] == 40.0 and q["ltp"] == 10.0
    assert q["iv"] == 14.5 and q["delta"] == 0.5 and q["theta"] == -3.0
    assert q["oi"] == 1000 and q["volume"] == 50


def test_mid_falls_back_to_ltp_when_book_is_empty():
    r = _row(100.0, "CE", ltp=12.0)
    assert _snapshot_quotes([r])[(100.0, "CE")]["mid"] == 12.0


def test_row_without_any_price_is_absent_from_quotes():
    r = _row(100.0, "CE", ltp=0.0)
    assert (100.0, "CE") not in _snapshot_quotes([r])


def test_mark_and_unrealized_match_hand_computed_mids():
    quotes = _snapshot_quotes(_quoted_chain())
    mark, unrealized, legs = _open_trade_marks(_fly_trade(), quotes)
    # cost to close = 40 + 40 - 20 - 20 = 40 per unit, x 75 qty
    assert mark == 40.0 * 75
    assert unrealized == 7500.0 - 40.0 * 75
    assert len(legs) == 4


def test_leg_exposes_entry_and_live_quote_side_by_side():
    quotes = _snapshot_quotes(_quoted_chain())
    _, _, legs = _open_trade_marks(_fly_trade(), quotes)
    short_ce = next(l for l in legs if l["strike"] == 100.0 and l["type"] == "CE")
    assert short_ce["entry_mid"] == 50.0
    assert short_ce["cur_mid"] == 40.0
    assert short_ce["bid"] == 39.0 and short_ce["ask"] == 41.0
    assert short_ce["iv"] == 14.5


def test_any_unquoted_leg_blanks_the_mark_but_keeps_the_legs():
    quotes = _snapshot_quotes(_quoted_chain())
    del quotes[(98.0, "PE")]
    mark, unrealized, legs = _open_trade_marks(_fly_trade(), quotes)
    assert mark is None and unrealized is None
    assert len(legs) == 4
    assert next(l for l in legs if l["strike"] == 98.0)["cur_mid"] is None
