"""
MM.1 — master freshness primitives (MASTER_MATERIALIZATION_POLICY.md §3).

Centralizes the two freshness facts every consumer (startup gate, dashboard, ops)
must compute identically:
  - InstrumentResolver.latest_snapshot_date(): MAX(snapshot_date) on disk, or None.
  - expected_snapshot_date(now): the latest NSE trading day whose 08:30 IST refresh
    cutoff has passed — pure, MarketHours-based (IST + NSE holidays).

Pure + unwired: no driver, no network. Calendar logic is tested against a
monkeypatched trading-day calendar so it is independent of the live holiday list,
plus delegation to MarketHours.is_trading_day is proven (holiday-awareness).
"""
from datetime import date, datetime, time, timedelta

from core.database.utils.market_hours import MarketHours
from core.instruments.master_freshness import REFRESH_CUTOFF, expected_snapshot_date
from core.instruments.resolver import InstrumentResolver
from scripts.fetch_instrument_master import parse_instruments, write_snapshot


def _row(ikey, snap):
    return {"segment": "NSE_FO", "instrument_key": ikey, "tradingsymbol": "NIFTYx",
            "name": "NIFTY", "instrument_type": "CE", "expiry": "2026-06-25",
            "strike_price": 22500.0, "lot_size": 75, "tick_size": 5}


# --- InstrumentResolver.latest_snapshot_date -------------------------------

def test_latest_snapshot_date_absent_is_none(tmp_path):
    r = InstrumentResolver(db_path=tmp_path / "nope.duckdb")
    assert r.latest_snapshot_date() is None


def test_latest_snapshot_date_single(tmp_path):
    db = tmp_path / "m.duckdb"
    write_snapshot(parse_instruments([_row("NSE_FO|1", None)], "2026-06-02"), db_path=db)
    assert InstrumentResolver(db_path=db).latest_snapshot_date() == date(2026, 6, 2)


def test_latest_snapshot_date_returns_max(tmp_path):
    db = tmp_path / "m.duckdb"
    write_snapshot(parse_instruments([_row("NSE_FO|1", None)], "2026-06-01"), db_path=db)
    write_snapshot(parse_instruments([_row("NSE_FO|1", None)], "2026-06-02"), db_path=db)
    assert InstrumentResolver(db_path=db).latest_snapshot_date() == date(2026, 6, 2)


# --- expected_snapshot_date (pure calendar logic) --------------------------

def _week(monkeypatch, *, non_trading=frozenset()):
    """Calendar where Mon–Fri trade except dates in `non_trading`."""
    def fake(dt=None):
        d = (dt or datetime.now()).date() if isinstance(dt, datetime) else dt
        return d.weekday() < 5 and d not in non_trading
    monkeypatch.setattr(MarketHours, "is_trading_day", staticmethod(fake))


def _monday():
    d = date(2026, 6, 8)
    return d - timedelta(days=d.weekday())  # Monday of that ISO week, whatever 06-08 is


def test_expected_is_today_after_cutoff(monkeypatch):
    _week(monkeypatch)
    tue = _monday() + timedelta(days=1)
    assert expected_snapshot_date(datetime.combine(tue, time(10, 0))) == tue


def test_expected_is_prev_trading_day_before_cutoff(monkeypatch):
    _week(monkeypatch)
    mon, tue = _monday(), _monday() + timedelta(days=1)
    before = datetime.combine(tue, time(REFRESH_CUTOFF.hour, REFRESH_CUTOFF.minute)) - timedelta(minutes=1)
    assert expected_snapshot_date(before) == mon


def test_expected_skips_weekend(monkeypatch):
    _week(monkeypatch)
    fri, sat = _monday() + timedelta(days=4), _monday() + timedelta(days=5)
    assert expected_snapshot_date(datetime.combine(sat, time(10, 0))) == fri


def test_expected_skips_holiday(monkeypatch):
    # Tuesday is an NSE holiday → Wednesday-before-cutoff expects Monday.
    mon, tue, wed = _monday(), _monday() + timedelta(days=1), _monday() + timedelta(days=2)
    _week(monkeypatch, non_trading={tue})
    before = datetime.combine(wed, time(8, 0))
    assert expected_snapshot_date(before) == mon
