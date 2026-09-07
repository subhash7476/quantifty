"""Options-Wall evidence analytics — closed trades joined to entry regime."""
from datetime import datetime

from core.options_wall import evidence, persistence as pers
from core.options_wall.fly import FlyLeg, IronFly

SYM = "NSE_INDEX|Nifty 50"


def _fly():
    legs = [FlyLeg("SELL", "CE", 100.0, 2.0), FlyLeg("SELL", "PE", 100.0, 2.0),
            FlyLeg("BUY", "CE", 103.0, 0.5), FlyLeg("BUY", "PE", 97.0, 0.5)]
    return IronFly(short_strike=100.0, call_wing=103.0, put_wing=97.0, legs=legs,
                   net_credit_per_unit=3.0, qty=65, net_credit=195.0,
                   entry_fees=5.0, max_loss=100.0)


def _open_close(db, entry_ts, net_pnl, reason, rom):
    tid = pers.open_paper_trade(SYM, "2026-09-10", _fly(), entry_ts, db_path=db)
    pers.close_paper_trade(tid, entry_ts, exit_mark=0.0, exit_fees=5.0,
                           gross_pnl=net_pnl + 10, net_pnl=net_pnl,
                           exit_reason=reason, return_on_margin=rom, db_path=db)


def test_summary_breaks_down_expectancy(tmp_path):
    db = tmp_path / "results.duckdb"
    pers.write_regime(SYM, {"regime": "Positive GEX (Stable)", "atm_iv": 16.0,
                            "realized_vol": 13.0, "pin_conviction": 70.0},
                      ts=datetime(2026, 9, 8, 9, 30), db_path=db)
    _open_close(db, datetime(2026, 9, 8, 10, 0), net_pnl=100.0, reason="tp", rom=0.1)
    _open_close(db, datetime(2026, 9, 8, 11, 0), net_pnl=-50.0, reason="sl", rom=-0.05)

    s = evidence.evidence_summary("NIFTY", db_path=db)
    assert s["n_closed"] == 2
    assert s["overall"]["n"] == 2 and s["overall"]["wins"] == 1
    assert s["overall"]["total_net"] == 50.0
    assert s["overall"]["win_rate"] == 0.5
    assert set(s["by_exit_reason"]) == {"tp", "sl"}
    assert s["by_exit_reason"]["tp"]["total_net"] == 100.0
    # Both trades entered after the 09:30 Positive-GEX regime with IV−RV = 3 pt.
    assert s["by_regime"]["Positive GEX"]["n"] == 2
    assert s["by_iv_band"]["2–4 pt"]["n"] == 2


def test_summary_empty_db_is_zero(tmp_path):
    s = evidence.evidence_summary("NIFTY", db_path=tmp_path / "none.duckdb")
    assert s["n_closed"] == 0 and s["overall"]["n"] == 0


def test_open_trades_excluded(tmp_path):
    db = tmp_path / "results.duckdb"
    pers.open_paper_trade(SYM, "2026-09-10", _fly(),
                          datetime(2026, 9, 8, 10, 0), db_path=db)
    assert evidence.evidence_summary("NIFTY", db_path=db)["n_closed"] == 0
