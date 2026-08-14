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
