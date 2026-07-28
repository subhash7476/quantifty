"""Tests for option contract selection and live-quote derivation.

Three defects these tests exist to prevent, all of which are silent — the page
renders a plausible number and nothing errors:

1. Picking the arithmetically-nearest strike when that strike is an illiquid
   half-strike carrying zero OI (observed live: ICICIPRULI 505 PE, OI=0, while
   500 PE carried 383,875).
2. Deriving prev_close from `ohlc.close`. Intraday that field tracks the CURRENT
   session and equals last_price, so every change_pct renders as 0.00%.
3. Inferring "stale feed" from an unchanged price. A thin strike does not print
   on every 2s poll; observed live, 9 of 10 contracts held the same LTP across
   5 seconds while the feed timestamp advanced normally.
"""
from datetime import date, datetime, timedelta, timezone

import duckdb
import pytest

from core.analytics.options_selection import MIN_OI, pick_expiry, select_option
from core.brokers.upstox_market_data import UpstoxMarketData
from flask_app.blueprints.ts_basis_daily import LIVE_MAX_AGE_SEC, _market_state


TRADE_DATE = date(2026, 7, 27)
EXPIRY = date(2026, 8, 25)


def _chain_con(rows, expiry=EXPIRY, trade_date=TRADE_DATE, underlying="TICKERX"):
    """In-memory stock_options_bhavcopy holding exactly `rows`.

    rows: (strike, option_type, settle, open_int)
    """
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE stock_options_bhavcopy (
            underlying VARCHAR, expiry_dt DATE, strike DOUBLE, option_type VARCHAR,
            settle DOUBLE, open_int BIGINT, contracts BIGINT, trade_date DATE
        )
    """)
    for strike, otype, settle, oi in rows:
        con.execute(
            "INSERT INTO stock_options_bhavcopy VALUES (?,?,?,?,?,?,?,?)",
            [underlying, expiry, strike, otype, settle, oi, 10, trade_date],
        )
    return con


# --- strike selection ------------------------------------------------------

def test_picks_strike_nearest_to_forward():
    con = _chain_con([(100.0, "CE", 5.0, 5000), (105.0, "CE", 3.0, 5000),
                      (110.0, "CE", 1.5, 5000)])
    sel = select_option(con, "TICKERX", "CE", EXPIRY, forward=104.0)
    assert sel["strike"] == 105.0
    assert sel["snapped"] is False


def test_snaps_off_zero_oi_half_strike_to_nearest_liquid_strike():
    """The ICICIPRULI case: 505 is arithmetically nearest to a 503.9 forward but
    carries no OI, so it is untradeable. Selection must land on 500."""
    con = _chain_con([(495.0, "PE", 12.25, 9250), (500.0, "PE", 14.35, 383875),
                      (505.0, "PE", 19.70, 0), (510.0, "PE", 22.45, 146150)])
    sel = select_option(con, "TICKERX", "PE", EXPIRY, forward=503.9)
    assert sel["nearest_strike"] == 505.0, "nearest by distance is still 505"
    assert sel["strike"] == 500.0, "but selection must snap to the liquid strike"
    assert sel["snapped"] is True
    assert sel["oi"] >= MIN_OI


def test_does_not_snap_when_nearest_strike_is_liquid():
    """Guard against over-eager snapping: a healthy nearest strike must win even
    when a neighbour carries far more OI."""
    con = _chain_con([(100.0, "CE", 5.0, 999999), (105.0, "CE", 3.0, 5000)])
    sel = select_option(con, "TICKERX", "CE", EXPIRY, forward=104.5)
    assert sel["strike"] == 105.0
    assert sel["snapped"] is False


def test_snap_threshold_is_inclusive_at_min_oi():
    """OI exactly at MIN_OI is tradeable and must not trigger a snap."""
    con = _chain_con([(100.0, "CE", 5.0, MIN_OI), (105.0, "CE", 3.0, 50000)])
    sel = select_option(con, "TICKERX", "CE", EXPIRY, forward=100.0)
    assert sel["strike"] == 100.0
    assert sel["snapped"] is False


def test_penny_strike_selection():
    """Penny names (IDEA ~13, YESBANK ~23) have coarse strikes; nearest still wins."""
    con = _chain_con([(12.0, "CE", 1.1, 500000), (13.0, "CE", 0.75, 800000),
                      (14.0, "CE", 0.45, 600000)])
    sel = select_option(con, "TICKERX", "CE", EXPIRY, forward=13.2)
    assert sel["strike"] == 13.0


def test_returns_none_when_chain_is_empty():
    con = _chain_con([])
    assert select_option(con, "TICKERX", "CE", EXPIRY, forward=100.0) is None


def test_synthetic_forward_from_put_call_parity_when_future_missing():
    """With no futures close, the forward is implied by the strike minimising
    |CE - PE|: F = K + C - P."""
    con = _chain_con([
        (100.0, "CE", 8.0, 5000), (100.0, "PE", 2.0, 5000),   # |C-P| = 6
        (105.0, "CE", 5.0, 5000), (105.0, "PE", 4.5, 5000),   # |C-P| = 0.5 -> chosen
    ])
    sel = select_option(con, "TICKERX", "CE", EXPIRY, forward=None)
    assert sel["forward"] == pytest.approx(105.5)  # 105 + 5.0 - 4.5
    assert sel["strike"] == 105.0


# --- expiry selection ------------------------------------------------------

def test_skips_expiry_inside_the_min_dte_window():
    """The live case: on 27 Jul the 28 Jul monthly expires tomorrow and carries
    almost no time value. Selection must roll to the next monthly."""
    con = _chain_con([(100.0, "CE", 5.0, 5000)], expiry=date(2026, 7, 28))
    con.execute(
        "INSERT INTO stock_options_bhavcopy VALUES "
        "('TICKERX', DATE '2026-08-25', 100.0, 'CE', 9.0, 5000, 10, DATE '2026-07-27')"
    )
    assert pick_expiry(con, "TICKERX", min_dte=7, today=date(2026, 7, 27)) == date(2026, 8, 25)


def test_expiry_exactly_at_min_dte_is_accepted():
    """Boundary: >= min_dte, so exactly 7 days out qualifies."""
    con = _chain_con([(100.0, "CE", 5.0, 5000)], expiry=date(2026, 8, 3))
    assert pick_expiry(con, "TICKERX", min_dte=7, today=date(2026, 7, 27)) == date(2026, 8, 3)


def test_falls_back_to_last_expiry_when_all_are_inside_the_window():
    """Better to return the only listed contract than nothing at all."""
    con = _chain_con([(100.0, "CE", 5.0, 5000)], expiry=date(2026, 7, 28))
    assert pick_expiry(con, "TICKERX", min_dte=7, today=date(2026, 7, 27)) == date(2026, 7, 28)


# --- quote derivation: the ohlc.close trap ---------------------------------

class _FakeResp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _quote_payload(last_price, net_change, ohlc_close, key="NSE_FO|111111"):
    return {"data": {"NSE_FO:XYZ": {
        "instrument_token": key, "last_price": last_price, "net_change": net_change,
        "ohlc": {"open": 1.0, "high": 2.0, "low": 0.5, "close": ohlc_close},
        "volume": 1000, "oi": 2000.0, "timestamp": "2026-07-28T13:04:54.072+05:30",
    }}}


def test_prev_close_uses_net_change_not_ohlc_close(monkeypatch):
    """THE REGRESSION TEST. ohlc.close is set equal to last_price, exactly as the
    live intraday payload does. Deriving prev_close from it yields 0.00% change;
    the correct derivation (last_price - net_change) yields the real move."""
    monkeypatch.setattr(
        "core.brokers.upstox_market_data.requests.get",
        lambda *a, **k: _FakeResp(_quote_payload(last_price=8.06, net_change=2.62,
                                                 ohlc_close=8.06)),
    )
    monkeypatch.setattr("core.auth.credentials.credentials.get", lambda *a, **k: "tok")

    q = UpstoxMarketData().fetch_quotes_batch(["NSE_FO|111111"])["quotes"]["NSE_FO|111111"]

    assert q["prev_close"] == pytest.approx(5.44)
    assert q["change_pct"] == pytest.approx(48.16, abs=0.01)
    assert q["change_pct"] != 0.0, "ohlc.close would have produced exactly 0.00%"


def test_change_pct_is_none_when_prev_close_is_zero(monkeypatch):
    """A contract whose previous close was 0 must not raise ZeroDivisionError."""
    monkeypatch.setattr(
        "core.brokers.upstox_market_data.requests.get",
        lambda *a, **k: _FakeResp(_quote_payload(last_price=5.0, net_change=5.0,
                                                 ohlc_close=5.0)),
    )
    monkeypatch.setattr("core.auth.credentials.credentials.get", lambda *a, **k: "tok")

    q = UpstoxMarketData().fetch_quotes_batch(["NSE_FO|111111"])["quotes"]["NSE_FO|111111"]
    assert q["prev_close"] == 0
    assert q["change_pct"] is None


def test_missing_token_reports_error_rather_than_empty_success(monkeypatch):
    """An expired token must surface as an error the UI can show, not as a
    successful response with no quotes (which would render as blank prices)."""
    monkeypatch.setattr("core.auth.credentials.credentials.get", lambda *a, **k: None)
    result = UpstoxMarketData().fetch_quotes_batch(["NSE_FO|111111"])
    assert result["quotes"] == {}
    assert "token" in result["error"].lower()


def test_http_error_is_reported(monkeypatch):
    class _Err:
        status_code = 502
        text = "bad gateway"

    monkeypatch.setattr("core.brokers.upstox_market_data.requests.get",
                        lambda *a, **k: _Err())
    monkeypatch.setattr("core.auth.credentials.credentials.get", lambda *a, **k: "tok")
    result = UpstoxMarketData().fetch_quotes_batch(["NSE_FO|111111"])
    assert result["quotes"] == {}
    assert "502" in result["error"]


# --- market state ----------------------------------------------------------

def _iso(dt):
    return dt.isoformat()


def test_fresh_feed_is_live_even_when_no_price_moved():
    """THE KEY CASE. Observed live: 9 of 10 contracts held an identical LTP across
    5 seconds while the feed was healthy. State must depend on the timestamp only,
    so an unmoved price is still LIVE."""
    now = datetime(2026, 7, 28, 13, 11, 20, tzinfo=timezone.utc)
    state, age = _market_state([_iso(now - timedelta(seconds=2))], now=now)
    assert state == "LIVE"
    assert age == pytest.approx(2, abs=0.01)


def test_old_feed_is_closed():
    now = datetime(2026, 7, 28, 20, 0, tzinfo=timezone.utc)
    state, _ = _market_state([_iso(now - timedelta(hours=5))], now=now)
    assert state == "CLOSED"


def test_small_negative_age_from_clock_skew_is_still_live():
    """The local clock can sit slightly behind the exchange feed (observed -0.9s).
    A feed marginally 'in the future' is healthy, not stale."""
    now = datetime(2026, 7, 28, 13, 0, tzinfo=timezone.utc)
    state, age = _market_state([_iso(now + timedelta(seconds=0.9))], now=now)
    assert state == "LIVE"
    assert age < 0


def test_far_future_timestamp_is_not_live():
    """abs() must not turn a wildly wrong timestamp into a LIVE verdict."""
    now = datetime(2026, 7, 28, 13, 0, tzinfo=timezone.utc)
    state, _ = _market_state([_iso(now + timedelta(hours=3))], now=now)
    assert state == "CLOSED"


def test_state_uses_the_newest_timestamp_across_contracts():
    """One thin contract lagging must not drag the whole panel to CLOSED."""
    now = datetime(2026, 7, 28, 13, 0, tzinfo=timezone.utc)
    state, _ = _market_state(
        [_iso(now - timedelta(hours=4)), _iso(now - timedelta(seconds=3))], now=now)
    assert state == "LIVE"


def test_no_timestamps_is_stale():
    assert _market_state([])[0] == "STALE"
    assert _market_state([None, None])[0] == "STALE"


def test_unparseable_timestamp_is_stale():
    assert _market_state(["not-a-timestamp"])[0] == "STALE"


def test_boundary_at_live_max_age():
    now = datetime(2026, 7, 28, 13, 0, tzinfo=timezone.utc)
    inside, _ = _market_state([_iso(now - timedelta(seconds=LIVE_MAX_AGE_SEC))], now=now)
    outside, _ = _market_state([_iso(now - timedelta(seconds=LIVE_MAX_AGE_SEC + 1))], now=now)
    assert inside == "LIVE"
    assert outside == "CLOSED"
