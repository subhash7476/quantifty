"""The trades table: open a paper trade, read it back open, then close it."""
from datetime import date, datetime

from core.options_wall import persistence as p
from core.options_wall.fly import build_iron_fly
from tests.options_wall.test_fly import _chain


def test_open_then_close_trade(tmp_path):
    db = tmp_path / "res.duckdb"
    fly = build_iron_fly(_chain(), spot=100.0, wing_pct=0.03, qty=75,
                         trade_date=date(2026, 8, 14))
    tid = p.open_paper_trade("NSE_INDEX|Nifty 50", "2026-08-18", fly,
                             datetime(2026, 8, 14, 10, 0), db_path=db)
    assert tid > 0

    opens = p.open_trades("NSE_INDEX|Nifty 50", db_path=db)
    assert len(opens) == 1
    assert opens[0]["exit_ts"] is None
    assert opens[0]["short_strike"] == 100.0
    assert opens[0]["net_credit"] == fly.net_credit

    p.close_paper_trade(tid, datetime(2026, 8, 14, 14, 0), exit_mark=1000.0,
                        exit_fees=230.0, gross_pnl=500.0, net_pnl=270.0,
                        exit_reason="tp", db_path=db)
    assert p.open_trades("NSE_INDEX|Nifty 50", db_path=db) == []


def test_all_trades_returns_open_and_closed_newest_first(tmp_path):
    db = tmp_path / "res.duckdb"
    fly = build_iron_fly(_chain(), spot=100.0, wing_pct=0.03, qty=75,
                         trade_date=date(2026, 8, 14))
    t1 = p.open_paper_trade("NSE_INDEX|Nifty 50", "2026-08-18", fly,
                            datetime(2026, 8, 14, 10, 0), db_path=db)
    t2 = p.open_paper_trade("NSE_INDEX|Nifty 50", "2026-08-25", fly,
                            datetime(2026, 8, 15, 10, 0), db_path=db)
    p.close_paper_trade(t1, datetime(2026, 8, 14, 14, 0), exit_mark=1000.0,
                        exit_fees=230.0, gross_pnl=500.0, net_pnl=270.0,
                        exit_reason="tp", db_path=db)

    rows = p.all_trades("NSE_INDEX|Nifty 50", db_path=db)
    assert [r["trade_id"] for r in rows] == [t2, t1]        # newest entry first
    assert rows[0]["exit_ts"] is None                        # t2 still open
    assert rows[1]["exit_reason"] == "tp"                    # t1 closed


def test_open_trade_marks_computes_unrealized_pnl():
    from core.options_wall.engine import _open_trade_marks
    trade = {
        "qty": 2,
        "net_credit": 200.0,  # (60 + 40) short - (0 wing) = 100/unit × 2
        "entry_legs": (
            '[{"side":"SELL","type":"CE","strike":100,"mid":60.0},'
            '{"side":"SELL","type":"PE","strike":100,"mid":40.0},'
            '{"side":"BUY","type":"CE","strike":110,"mid":0.0},'
            '{"side":"BUY","type":"PE","strike":90,"mid":0.0}]'),
    }
    mids = {(100, "CE"): 55.0, (100, "PE"): 30.0, (110, "CE"): 5.0, (90, "PE"): 4.0}
    # cost to close = (55 + 30) short - (5 + 4) wings = 76/unit × 2 = 152
    mark, unrealized, legs = _open_trade_marks(trade, mids)
    assert mark == 152.0
    assert unrealized == 48.0                                # 200 credit - 152 mark
    assert legs[0]["cur_mid"] == 55.0


def test_open_trade_marks_none_when_a_leg_is_unquoted():
    from core.options_wall.engine import _open_trade_marks
    trade = {"qty": 1, "net_credit": 100.0,
             "entry_legs": '[{"side":"SELL","type":"CE","strike":100,"mid":60.0}]'}
    mark, unrealized, legs = _open_trade_marks(trade, {})     # no quotes
    assert mark is None and unrealized is None
    assert legs[0]["cur_mid"] is None
