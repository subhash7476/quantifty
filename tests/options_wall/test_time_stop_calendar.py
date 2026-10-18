"""The time stop fires on the last session before expiry (pilot spec §5.4), not on
the calendar day before it. Counting calendar days carried a fly into expiry day
whenever that day was a weekend or a holiday."""
import logging
from datetime import date, datetime, time

import pytest

from core.analytics.options_analytics import (
    GEXResult, OIAnalysisResult, OptionsStructuralData, PCRResult,
)
from core.data.options_provider import OptionChainRow
from core.market import session_schedule, trading_calendar
from core.market.trading_calendar import OutsideCoverage, previous_session
from core.options_wall import paper_executor
from core.options_wall.paper_executor import PaperConfig, PaperExecutor, time_stop_day

_PREMIA = {
    97: (4.0, 0.5), 98: (3.2, 0.8), 99: (2.5, 1.2), 100: (1.8, 1.8),
    101: (1.2, 2.5), 102: (0.8, 3.2), 103: (0.5, 4.0),
}
NIFTY = "NSE_INDEX|Nifty 50"


def _chain(expiry):
    rows = []
    for k, (ce, pe) in _PREMIA.items():
        for ot, ltp in (("CE", ce), ("PE", pe)):
            r = OptionChainRow(strike=float(k), option_type=ot, instrument_key=f"{ot}{k}",
                               tradingsymbol=f"{ot}{k}", expiry=expiry, ltp=ltp, iv=15.0,
                               underlying_ltp=100.0)
            r.best_bid, r.best_ask = ltp - 0.01, ltp + 0.01
            rows.append(r)
    return rows


def _structural(expiry):
    gex = GEXResult(net_gamma_total=10.0, net_gamma_ce=1.0, net_gamma_pe=1.0,
                    gamma_by_strike={100.0: 10.0, 101.0: 1.0}, zero_gamma_level=None,
                    regime="Positive GEX (Stable)")
    return OptionsStructuralData(
        underlying=NIFTY, underlying_ltp=100.0, expiry=expiry, timestamp=datetime.now(),
        pcr=PCRResult(pcr=1.0, total_ce_oi=1, total_pe_oi=1), gex=gex,
        oi_analysis=OIAnalysisResult())


def _opened(tmp_path, expiry, opened_at):
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=tmp_path / "r.duckdb")
    assert ex.step(NIFTY, _chain(expiry), _structural(expiry), 1.0, opened_at) == "open"
    return ex


def _step(ex, expiry, now):
    return ex.step(NIFTY, _chain(expiry), _structural(expiry), 1.0, now)


@pytest.mark.parametrize("expiry, stop_day", [
    (date(2026, 8, 18), date(2026, 8, 17)),    # Tue expiry, Mon session
    (date(2026, 10, 19), date(2026, 10, 16)),  # Mon expiry (Dussehra-shifted), Fri session
    (date(2026, 4, 15), date(2026, 4, 13)),    # Wed expiry, Tue 04-14 holiday
])
def test_the_stop_day_is_the_last_session_before_expiry(expiry, stop_day):
    assert time_stop_day(expiry) == stop_day


def _with_sessions(monkeypatch, additional=(), special=None):
    monkeypatch.setattr(trading_calendar, "ADDITIONAL_SESSIONS",
                        trading_calendar.ADDITIONAL_SESSIONS | set(additional))
    monkeypatch.setattr(session_schedule, "SPECIAL_SESSIONS",
                        {**session_schedule.SPECIAL_SESSIONS, **(special or {})})


def test_a_sunday_muhurat_before_a_monday_expiry_leaves_the_stop_on_the_friday(monkeypatch):
    # Diwali 2026: a Sun 11-08 Muhurat ahead of the weekly that the Tue 11-10 holiday
    # moves to Mon 11-09. The poller never runs on a Sunday.
    muhurat = date(2026, 11, 8)
    _with_sessions(monkeypatch, additional={muhurat},
                   special={muhurat: session_schedule._special((time(18, 0), time(19, 0)))})
    assert previous_session(date(2026, 11, 9)) == muhurat
    assert time_stop_day(date(2026, 11, 9)) == date(2026, 11, 6)


def test_a_saturday_session_before_a_monday_expiry_leaves_the_stop_on_the_friday(monkeypatch):
    # a full Saturday session (e.g. a Budget day) is in ADDITIONAL_SESSIONS only
    _with_sessions(monkeypatch, additional={date(2026, 10, 17)})
    assert previous_session(date(2026, 10, 19)) == date(2026, 10, 17)
    assert time_stop_day(date(2026, 10, 19)) == date(2026, 10, 16)


def test_a_weekday_special_session_before_expiry_moves_the_stop_back_a_session(monkeypatch):
    # an afternoon weekday Muhurat, like 2025-10-21: a session early is the safe side
    muhurat = date(2026, 11, 16)
    _with_sessions(monkeypatch,
                   special={muhurat: session_schedule._special((time(13, 45), time(14, 45)))})
    assert previous_session(date(2026, 11, 17)) == muhurat
    assert time_stop_day(date(2026, 11, 17)) == date(2026, 11, 13)


def test_an_expiry_past_the_calendar_falls_back_to_the_last_weekday_and_warns_once(monkeypatch):
    monkeypatch.setattr(trading_calendar, "COVERAGE_LAST", date(2026, 10, 31))
    monkeypatch.setattr(paper_executor, "_uncovered_warned", set())
    with pytest.raises(OutsideCoverage):
        previous_session(date(2026, 11, 2))
    records = []

    class _Grab(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = _Grab(level=logging.WARNING)
    paper_executor.logger.addHandler(handler)
    try:
        assert time_stop_day(date(2026, 11, 2)) == date(2026, 10, 30)   # Mon expiry, Fri stop
        assert time_stop_day(date(2026, 11, 2)) == date(2026, 10, 30)
    finally:
        paper_executor.logger.removeHandler(handler)
    assert len(records) == 1
    assert "2026-11-02" in records[0]


def test_a_tuesday_expiry_is_squared_off_on_the_monday_not_the_friday(tmp_path):
    ex = _opened(tmp_path, "2026-11-17", datetime(2026, 11, 12, 10, 0))
    assert _step(ex, "2026-11-17", datetime(2026, 11, 13, 15, 35)) is None   # Fri: not yet
    assert _step(ex, "2026-11-17", datetime(2026, 11, 16, 15, 35)) == "time_stop"


def test_a_holiday_before_a_post_cas_expiry_stops_the_monday_at_1535(tmp_path):
    # Wed 11-11 expiry, Tue 11-10 holiday. Post-CAS the squareoff is 15:35 itself;
    # the pre-CAS 04-15 case below resolves to 15:28.
    ex = _opened(tmp_path, "2026-11-11", datetime(2026, 11, 6, 10, 0))
    assert _step(ex, "2026-11-11", datetime(2026, 11, 6, 15, 35)) is None
    assert _step(ex, "2026-11-11", datetime(2026, 11, 9, 15, 34)) is None
    assert _step(ex, "2026-11-11", datetime(2026, 11, 9, 15, 35)) == "time_stop"


def test_a_monday_expiry_is_squared_off_on_the_friday(tmp_path):
    ex = _opened(tmp_path, "2026-10-19", datetime(2026, 10, 15, 10, 0))
    assert _step(ex, "2026-10-19", datetime(2026, 10, 15, 15, 35)) is None   # Thu: not yet
    assert _step(ex, "2026-10-19", datetime(2026, 10, 16, 15, 30)) is None   # Fri, before 15:35
    assert _step(ex, "2026-10-19", datetime(2026, 10, 16, 15, 35)) == "time_stop"


def test_a_holiday_before_expiry_moves_the_stop_back_a_session(tmp_path):
    ex = _opened(tmp_path, "2026-04-15", datetime(2026, 4, 13, 10, 0))
    assert _step(ex, "2026-04-15", datetime(2026, 4, 13, 15, 35)) == "time_stop"


def test_a_fly_that_reaches_expiry_day_is_still_closed_at_the_squareoff(tmp_path):
    # e.g. the poller was down on the stop day: the expiry-day close is the safety net
    ex = _opened(tmp_path, "2026-10-19", datetime(2026, 10, 15, 10, 0))
    assert _step(ex, "2026-10-19", datetime(2026, 10, 19, 10, 0)) is None
    assert _step(ex, "2026-10-19", datetime(2026, 10, 19, 15, 35)) == "time_stop"
