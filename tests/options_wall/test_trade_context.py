"""Entry context: the regime and signal cycle the executor acted on."""
from datetime import date, datetime

from core.options_wall import persistence as p

SYM = "NSE_INDEX|Nifty 50"


def _regime(db, ts, pin):
    p.write_regime(SYM, {"trade_date": ts.date(), "regime": "Positive GEX (Stable)",
                         "pin_strike": pin, "net_gex_cr": 250.0, "atm_iv": 14.0,
                         "realized_vol": 9.0, "underlying_ltp": 100.0,
                         "put_wall": 98.0, "call_wall": 102.0},
                  ts=ts, db_path=db)


class _Res:
    def __init__(self, strike, score):
        self.expiry, self.strike, self.option_type = "2026-09-15", strike, "CE"
        self.screen, self.structure, self.regime = "iv_rv", "iron_fly", "Positive GEX"
        self.score, self.credit, self.iv_minus_rv = score, 120.0, 5.0
        self.pin_conviction, self.reason = 0.7, "IV over RV at a pinned strike"
        self.legs = [{"side": "SELL", "type": "CE", "strike": strike}]


def test_regime_at_returns_the_cycle_at_or_before_entry(tmp_path):
    db = tmp_path / "res.duckdb"
    _regime(db, datetime(2026, 9, 10, 9, 30), pin=100.0)
    _regime(db, datetime(2026, 9, 10, 10, 0), pin=101.0)
    _regime(db, datetime(2026, 9, 10, 11, 0), pin=102.0)

    got = p.regime_at(SYM, datetime(2026, 9, 10, 10, 30), db_path=db)
    assert got["pin_strike"] == 101.0          # nearest before, not nearest overall
    assert got["regime"] == "Positive GEX (Stable)"


def test_regime_at_matches_an_exact_cycle_timestamp(tmp_path):
    db = tmp_path / "res.duckdb"
    _regime(db, datetime(2026, 9, 10, 10, 0), pin=101.0)
    got = p.regime_at(SYM, datetime(2026, 9, 10, 10, 0), db_path=db)
    assert got["pin_strike"] == 101.0


def test_regime_at_will_not_cross_into_another_trade_date(tmp_path):
    db = tmp_path / "res.duckdb"
    _regime(db, datetime(2026, 9, 9, 15, 0), pin=100.0)
    assert p.regime_at(SYM, datetime(2026, 9, 10, 9, 20), db_path=db) is None


def test_regime_at_on_a_db_that_does_not_exist(tmp_path):
    assert p.regime_at(SYM, datetime(2026, 9, 10, 10, 0),
                       db_path=tmp_path / "missing.duckdb") is None


def test_signal_at_returns_the_whole_scan_cycle_before_entry(tmp_path):
    db = tmp_path / "res.duckdb"
    p.write_scan_results([_Res(100.0, 0.9)], SYM, ts=datetime(2026, 9, 10, 9, 30),
                         db_path=db)
    p.write_scan_results([_Res(101.0, 0.8), _Res(102.0, 0.95)], SYM,
                         ts=datetime(2026, 9, 10, 10, 0), db_path=db)
    p.write_scan_results([_Res(103.0, 0.7)], SYM, ts=datetime(2026, 9, 10, 11, 0),
                         db_path=db)

    rows = p.signal_at(SYM, datetime(2026, 9, 10, 10, 30), db_path=db)
    assert {r["strike"] for r in rows} == {101.0, 102.0}
    assert rows[0]["score"] == 0.95            # best first
    assert rows[0]["reason"]


def test_signal_at_will_not_cross_into_another_trade_date(tmp_path):
    db = tmp_path / "res.duckdb"
    p.write_scan_results([_Res(100.0, 0.9)], SYM, ts=datetime(2026, 9, 9, 15, 0),
                         db_path=db)
    assert p.signal_at(SYM, datetime(2026, 9, 10, 9, 20), db_path=db) == []


def test_signal_at_on_a_db_that_does_not_exist(tmp_path):
    assert p.signal_at(SYM, datetime(2026, 9, 10, 10, 0),
                       db_path=tmp_path / "missing.duckdb") == []
