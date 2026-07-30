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

from core.analytics.options_selection import (
    MIN_OI, MAX_SPREAD_PCT, STRIKE_BAND, pick_expiry, select_option,
    screen_candidate, pick_screened_strike,
)
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


def _quote_payload_with_depth(last_price, net_change, ohlc_close,
                              bid=None, ask=None, key="NSE_FO|111111"):
    depth = {}
    if bid is not None or ask is not None:
        depth = {"buy": [{"price": bid}] if bid is not None else [],
                 "sell": [{"price": ask}] if ask is not None else []}
    return {"data": {"NSE_FO:XYZ": {
        "instrument_token": key, "last_price": last_price, "net_change": net_change,
        "ohlc": {"open": 1.0, "high": 2.0, "low": 0.5, "close": ohlc_close},
        "volume": 1000, "oi": 2000.0, "depth": depth,
        "timestamp": "2026-07-28T13:04:54.072+05:30",
    }}}


def test_quote_exposes_best_bid_and_ask_from_depth(monkeypatch):
    monkeypatch.setattr(
        "core.brokers.upstox_market_data.requests.get",
        lambda *a, **k: _FakeResp(_quote_payload_with_depth(
            last_price=8.0, net_change=0.0, ohlc_close=8.0, bid=7.9, ask=8.1)),
    )
    monkeypatch.setattr("core.auth.credentials.credentials.get", lambda *a, **k: "tok")
    q = UpstoxMarketData().fetch_quotes_batch(["NSE_FO|111111"])["quotes"]["NSE_FO|111111"]
    assert q["best_bid"] == pytest.approx(7.9)
    assert q["best_ask"] == pytest.approx(8.1)


def test_quote_bid_ask_are_none_when_depth_absent(monkeypatch):
    monkeypatch.setattr(
        "core.brokers.upstox_market_data.requests.get",
        lambda *a, **k: _FakeResp(_quote_payload_with_depth(
            last_price=8.0, net_change=0.0, ohlc_close=8.0)),  # no depth
    )
    monkeypatch.setattr("core.auth.credentials.credentials.get", lambda *a, **k: "tok")
    q = UpstoxMarketData().fetch_quotes_batch(["NSE_FO|111111"])["quotes"]["NSE_FO|111111"]
    assert q["best_bid"] is None
    assert q["best_ask"] is None


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


def test_non_json_200_response_is_reported_not_raised(monkeypatch):
    """A status-200 response with an unparseable body (e.g. an HTML error page
    behind a 200) must not propagate a JSONDecodeError — the selection module
    has no try/except around this call and relies on the error-dict contract."""
    class _BadJsonResp:
        status_code = 200

        def json(self):
            raise ValueError("Expecting value: line 1 column 1 (char 0)")

    monkeypatch.setattr("core.brokers.upstox_market_data.requests.get",
                        lambda *a, **k: _BadJsonResp())
    monkeypatch.setattr("core.auth.credentials.credentials.get", lambda *a, **k: "tok")
    result = UpstoxMarketData().fetch_quotes_batch(["NSE_FO|111111"])
    assert result["quotes"] == {}
    assert result["error"]


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


# --- pure tradeability screen ------------------------------------------------

def test_screen_passes_tight_liquid_strike():
    ok, spread, reason = screen_candidate(
        bid=9.9, ask=10.1, oi=5000, volume=500,
        min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert ok is True
    assert spread == pytest.approx(0.02, abs=1e-6)   # 0.2/10.0
    assert reason is None


def test_screen_rejects_wide_spread():
    ok, spread, reason = screen_candidate(
        bid=9.0, ask=11.0, oi=5000, volume=500,
        min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert ok is False
    assert spread == pytest.approx(0.2, abs=1e-6)     # 2.0/10.0
    assert "spread" in reason


def test_screen_spread_boundary_is_inclusive():
    # spread exactly 5%: bid=9.75 ask=10.25 mid=10 -> 0.5/10 = 0.05
    ok, spread, _ = screen_candidate(
        bid=9.75, ask=10.25, oi=5000, volume=500,
        min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert ok is True
    assert spread == pytest.approx(0.05, abs=1e-9)


def test_screen_rejects_low_oi_and_low_volume():
    ok_oi, _, r_oi = screen_candidate(9.9, 10.1, oi=50, volume=500,
                                      min_oi=100, min_volume=50, max_spread_pct=0.05)
    ok_vol, _, r_vol = screen_candidate(9.9, 10.1, oi=5000, volume=10,
                                        min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert ok_oi is False and "OI" in r_oi
    assert ok_vol is False and "vol" in r_vol


def test_screen_rejects_missing_or_nonpositive_quote():
    ok, spread, reason = screen_candidate(None, None, oi=5000, volume=500,
                                          min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert ok is False and spread is None and "quote" in reason


def test_pick_chooses_nearest_forward_among_passing():
    cands = [
        {"strike": 100.0, "bid": 9.9,  "ask": 10.1, "oi": 5000, "volume": 500},
        {"strike": 105.0, "bid": 5.95, "ask": 6.05, "oi": 5000, "volume": 500},
    ]
    chosen, reason = pick_screened_strike(cands, forward=104.0,
                                          min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert reason is None
    assert chosen["strike"] == 105.0
    assert "spread_pct" in chosen


def test_pick_snaps_past_wide_nearest_to_a_tight_neighbour():
    cands = [
        {"strike": 105.0, "bid": 4.0, "ask": 8.0, "oi": 5000, "volume": 500},   # nearest, wide
        {"strike": 100.0, "bid": 9.95, "ask": 10.05, "oi": 5000, "volume": 500},  # tight
    ]
    chosen, reason = pick_screened_strike(cands, forward=104.0,
                                          min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert reason is None
    assert chosen["strike"] == 100.0


def test_pick_returns_reason_when_none_pass():
    cands = [{"strike": 100.0, "bid": 4.0, "ask": 8.0, "oi": 5000, "volume": 500}]
    chosen, reason = pick_screened_strike(cands, forward=100.0,
                                          min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert chosen is None
    assert "spread" in reason


# --- live forward resolution -------------------------------------------------

def _inst_con(rows, snap=date(2026, 7, 27)):
    """rows: (name, tradingsymbol, expiry_iso, strike, instrument_type, key, lot)."""
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE instruments (
            instrument_key VARCHAR, tradingsymbol VARCHAR, name VARCHAR,
            expiry VARCHAR, strike DOUBLE, instrument_type VARCHAR,
            lot_size BIGINT, snapshot_date DATE
        )
    """)
    for name, tsym, exp, strike, itype, key, lot in rows:
        con.execute("INSERT INTO instruments VALUES (?,?,?,?,?,?,?,?)",
                    [key, tsym, name, exp, strike, itype, lot, snap])
    return con, snap


class _StubMD:
    def __init__(self, ltps=None, quotes=None):
        self._ltps = ltps or {}
        self._quotes = quotes or {}

    def fetch_ltp_batch(self, keys):
        return {k: self._ltps[k] for k in keys if k in self._ltps}

    def fetch_quotes_batch(self, keys):
        return {"quotes": {k: self._quotes[k] for k in keys if k in self._quotes},
                "error": None}


def test_resolve_live_forwards_maps_ticker_to_future_ltp():
    from core.analytics.options_selection import _resolve_live_forwards
    con, snap = _inst_con([
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0, "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0, "FUT", "NSE_FO|58419", 3000),
    ])
    md = _StubMD(ltps={"NSE_FO|58419": 251.4})
    fwds = _resolve_live_forwards(
        con, snap, [("WIPRO", "LONG")], {"WIPRO": date(2026, 8, 25)}, md)
    assert fwds == {"WIPRO": 251.4}


def test_resolve_live_forwards_omits_names_with_no_key_or_no_price():
    from core.analytics.options_selection import _resolve_live_forwards
    con, snap = _inst_con([
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0, "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0, "FUT", "NSE_FO|58419", 3000),
    ])
    md = _StubMD(ltps={})  # key resolves but no live price
    fwds = _resolve_live_forwards(
        con, snap, [("WIPRO", "LONG"), ("NOSUCH", "SHORT")],
        {"WIPRO": date(2026, 8, 25), "NOSUCH": date(2026, 8, 25)}, md)
    assert fwds == {}


# --- orchestrator: two-pass live anchor + screen -----------------------------

def _full_env(chain_rows, inst_rows, fut_rows=None):
    """Return (o, f, inst, snap) in-memory DBs for _build_contracts.

    chain_rows: (underlying, expiry, strike, otype, settle, oi, contracts, trade_date)
    inst_rows : (name, tradingsymbol, expiry_iso, strike, instrument_type, key, lot)
    fut_rows  : (underlying, expiry, close, trade_date)
    """
    o = duckdb.connect(":memory:")
    o.execute("""CREATE TABLE stock_options_bhavcopy (
        underlying VARCHAR, expiry_dt DATE, strike DOUBLE, option_type VARCHAR,
        settle DOUBLE, open_int BIGINT, contracts BIGINT, trade_date DATE)""")
    for r in chain_rows:
        o.execute("INSERT INTO stock_options_bhavcopy VALUES (?,?,?,?,?,?,?,?)", list(r))

    f = duckdb.connect(":memory:")
    f.execute("""CREATE TABLE futures_bhavcopy (
        underlying VARCHAR, expiry_dt DATE, close DOUBLE, trade_date DATE)""")
    for r in (fut_rows or []):
        f.execute("INSERT INTO futures_bhavcopy VALUES (?,?,?,?)", list(r))

    inst, snap = _inst_con(inst_rows)
    return o, f, inst, snap


EXP = date(2026, 8, 25)


def test_build_live_anchor_centres_on_live_forward_and_passes_screen():
    from core.analytics.options_selection import _build_contracts
    chain = [("WIPRO", EXP, 240.0, "CE", 6.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 250.0, "CE", 4.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 260.0, "CE", 2.0, 5000, 10, TRADE_DATE)]
    inst_rows = [
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "FUT", "NSE_FO|58419", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 250.0, "CE",  "NSE_FO|250CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 260.0, "CE",  "NSE_FO|260CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 240.0, "CE",  "NSE_FO|240CE", 3000),
    ]
    o, f, inst, snap = _full_env(chain, inst_rows,
                                 fut_rows=[("WIPRO", EXP, 241.0, TRADE_DATE)])
    md = _StubMD(
        ltps={"NSE_FO|58419": 251.4},                      # live fwd -> ATM 250
        quotes={"NSE_FO|250CE": {"best_bid": 3.98, "best_ask": 4.02,
                                 "oi": 9000, "volume": 6000},
                "NSE_FO|260CE": {"best_bid": 1.9, "best_ask": 2.1,
                                 "oi": 9000, "volume": 6000},
                "NSE_FO|240CE": {"best_bid": 5.9, "best_ask": 6.1,
                                 "oi": 9000, "volume": 6000}})
    rows = _build_contracts(o, f, inst, [("WIPRO", "LONG")],
                            min_dte=7, today=TRADE_DATE, market_data=md)
    r = rows[0]
    assert r["anchor_source"] == "live"
    assert r["forward"] == pytest.approx(251.4)
    assert r["strike"] == 250.0            # nearest to live fwd, screen passes
    assert r["screen"] == "pass"
    assert r["spread_pct"] == pytest.approx(0.01, abs=1e-6)


def test_build_flags_when_no_strike_is_tradeable():
    from core.analytics.options_selection import _build_contracts
    chain = [("WIPRO", EXP, 250.0, "CE", 4.0, 5000, 10, TRADE_DATE)]
    inst_rows = [
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "FUT", "NSE_FO|58419", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 250.0, "CE",  "NSE_FO|250CE", 3000),
    ]
    o, f, inst, snap = _full_env(chain, inst_rows,
                                 fut_rows=[("WIPRO", EXP, 250.0, TRADE_DATE)])
    md = _StubMD(ltps={"NSE_FO|58419": 250.0},
                 quotes={"NSE_FO|250CE": {"best_bid": 2.0, "best_ask": 6.0,  # ~100% wide
                                          "oi": 9000, "volume": 6000}})
    rows = _build_contracts(o, f, inst, [("WIPRO", "LONG")],
                            min_dte=7, today=TRADE_DATE, market_data=md)
    r = rows[0]
    assert r["screen"] == "no_tradeable_strike"
    assert "spread" in r["screen_reason"]
    assert r["ticker"] == "WIPRO"          # kept, not dropped


def test_build_skips_screen_and_falls_back_when_no_live_feed():
    from core.analytics.options_selection import _build_contracts, _EOD_ONLY
    chain = [("WIPRO", EXP, 240.0, "CE", 6.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 250.0, "CE", 4.0, 5000, 10, TRADE_DATE)]
    inst_rows = [
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 240.0, "CE",  "NSE_FO|240CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 250.0, "CE",  "NSE_FO|250CE", 3000),
    ]
    o, f, inst, snap = _full_env(chain, inst_rows,
                                 fut_rows=[("WIPRO", EXP, 241.0, TRADE_DATE)])
    rows = _build_contracts(o, f, inst, [("WIPRO", "LONG")],
                            min_dte=7, today=TRADE_DATE, market_data=_EOD_ONLY)
    r = rows[0]
    assert r["screen"] == "skipped"
    assert r["anchor_source"] == "eod_future"
    assert r["forward"] == pytest.approx(241.0)   # EOD future close
    assert r["strike"] == 240.0                    # EOD nearest-to-forward


def test_build_live_feed_miss_falls_back_to_eod_skipped():
    """Forward resolves live (anchor_source='live') but the batched option quote
    fetch comes back empty for every candidate key -> Pass B must fall back to
    the EOD chain rather than crash on an all-miss quotes dict. Distinct from the
    _EOD_ONLY test above, which never builds candidate keys in the first place."""
    from core.analytics.options_selection import _build_contracts
    chain = [("WIPRO", EXP, 240.0, "CE", 6.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 250.0, "CE", 4.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 260.0, "CE", 2.0, 5000, 10, TRADE_DATE)]
    inst_rows = [
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "FUT", "NSE_FO|58419", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 250.0, "CE",  "NSE_FO|250CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 260.0, "CE",  "NSE_FO|260CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 240.0, "CE",  "NSE_FO|240CE", 3000),
    ]
    o, f, inst, snap = _full_env(chain, inst_rows,
                                 fut_rows=[("WIPRO", EXP, 241.0, TRADE_DATE)])
    md = _StubMD(ltps={"NSE_FO|58419": 251.4}, quotes={})   # live fwd, no option quotes
    rows = _build_contracts(o, f, inst, [("WIPRO", "LONG")],
                            min_dte=7, today=TRADE_DATE, market_data=md)
    r = rows[0]
    assert r["anchor_source"] == "live"
    assert r["screen"] == "skipped"
    assert r["strike"] == 250.0   # EOD _fill_eod nearest-to-forward(251.4) fallback


def test_build_is_stable_across_two_calls_same_inputs():
    """The panel caches per formation; re-resolving the same book with the same
    live snapshot must yield the same strike (no per-call churn)."""
    from core.analytics.options_selection import _build_contracts
    chain = [("WIPRO", EXP, 240.0, "CE", 6.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 250.0, "CE", 4.0, 5000, 10, TRADE_DATE)]
    inst_rows = [
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "FUT", "NSE_FO|58419", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 240.0, "CE",  "NSE_FO|240CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 250.0, "CE",  "NSE_FO|250CE", 3000),
    ]
    o, f, inst, snap = _full_env(chain, inst_rows,
                                 fut_rows=[("WIPRO", EXP, 241.0, TRADE_DATE)])
    md = _StubMD(ltps={"NSE_FO|58419": 249.0},
                 quotes={"NSE_FO|250CE": {"best_bid": 3.98, "best_ask": 4.02,
                                          "oi": 9000, "volume": 6000},
                         "NSE_FO|240CE": {"best_bid": 5.98, "best_ask": 6.02,
                                          "oi": 9000, "volume": 6000}})
    r1 = _build_contracts(o, f, inst, [("WIPRO", "LONG")], 7, TRADE_DATE, md)[0]
    r2 = _build_contracts(o, f, inst, [("WIPRO", "LONG")], 7, TRADE_DATE, md)[0]
    assert r1["strike"] == r2["strike"] == 250.0
    assert r1["screen"] == r2["screen"] == "pass"


def test_build_snapped_when_nearest_strike_fails_screen():
    """The strike nearest the live forward (250) has a spread too wide to trade;
    a farther in-band strike (260) is tight and passes. Orchestrator must snap
    past the nearest and select the farther tradeable strike."""
    from core.analytics.options_selection import _build_contracts
    chain = [("WIPRO", EXP, 240.0, "CE", 6.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 250.0, "CE", 4.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 260.0, "CE", 2.0, 5000, 10, TRADE_DATE)]
    inst_rows = [
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "FUT", "NSE_FO|58419", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 250.0, "CE",  "NSE_FO|250CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 260.0, "CE",  "NSE_FO|260CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 240.0, "CE",  "NSE_FO|240CE", 3000),
    ]
    o, f, inst, snap = _full_env(chain, inst_rows,
                                 fut_rows=[("WIPRO", EXP, 241.0, TRADE_DATE)])
    md = _StubMD(
        ltps={"NSE_FO|58419": 251.4},                        # live fwd -> nearest strike 250
        quotes={"NSE_FO|250CE": {"best_bid": 2.0, "best_ask": 6.0,    # nearest, wide (spread 100%)
                                 "oi": 9000, "volume": 6000},
                "NSE_FO|260CE": {"best_bid": 1.95, "best_ask": 2.05,  # farther, tight (spread 5%)
                                 "oi": 9000, "volume": 6000}})
    # 240CE deliberately has no live quote -> screen_candidate rejects it on
    # "no quote" regardless of distance, so 260 is the only passing candidate.
    rows = _build_contracts(o, f, inst, [("WIPRO", "LONG")],
                            min_dte=7, today=TRADE_DATE, market_data=md)
    r = rows[0]
    assert r["nearest_strike"] == 250.0
    assert r["strike"] == 260.0             # nearest of the two passing, since 250 fails
    assert r["screen"] == "snapped"
    assert r["snapped"] is True
