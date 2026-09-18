"""Date-keyed, segment-named NSE session windows.

The single authority for "when is segment X open on date D". SEBI's Closing
Auction Session (circular 2026-01-16, operative 2026-08-03) split what used to
be one 09:15-15:30 session into four differently-bounded segments, so a single
MARKET_CLOSE constant can no longer express the truth.

Era-schedule shape mirrors core/execution/equity/intraday_fees.py's
_STT_INTRADAY_SCHEDULE: newest era last, resolved by scanning for the latest
entry whose effective date is <= the queried date.

Two layers, in order: SPECIAL_SESSIONS (a single date that does not follow the
era schedule at all, e.g. Diwali Muhurat) wins over the era table. This module
answers "when is segment X open on a date the market trades"; whether the market
trades on a given date is the trading calendar's question, not this one's.
"""
from __future__ import annotations

from datetime import date, datetime, time

CAS_EFFECTIVE = date(2026, 8, 3)

SEGMENTS = ("cash_cat1", "cash_cat2", "cash_auction", "derivatives")

_SCHEDULE = (
    (date(1900, 1, 1), {
        "cash_cat1": (time(9, 15), time(15, 30)),
        "cash_cat2": (time(9, 15), time(15, 30)),
        "cash_auction": None,
        "derivatives": (time(9, 15), time(15, 30)),
    }),
    (CAS_EFFECTIVE, {
        "cash_cat1": (time(9, 15), time(15, 15)),
        "cash_cat2": (time(9, 15), time(15, 30)),
        "cash_auction": (time(15, 15), time(15, 35)),
        "derivatives": (time(9, 15), time(15, 40)),
    }),
)


def _special(*windows):
    """Every segment trades `windows`, with no auction (pre-CAS special-session shape).

    More than one window means the session has a recess: NSE's special Saturdays
    trade a block, stop, and trade a second block.
    """
    return {"cash_cat1": windows, "cash_cat2": windows,
            "cash_auction": (), "derivatives": windows}


# NSE occasionally trades a single one-hour session outside the era schedule
# (Diwali Muhurat), sometimes on a day that is not even a weekday. An era table
# cannot express that, so this one is consulted first.
#
# The windows are DERIVED FROM THE STORE rather than from memory: the native 1m
# era is start-labelled, so start = the first bar's stamp and end = the last
# bar's stamp + 1 minute. Each session carries exactly 60 distinct minutes per
# symbol in data/market_data/nse/candles/1m/{date}.duckdb, which is what makes
# every row below re-checkable:
#   2023-11-12  bars 18:15..19:14  ->  [18:15, 19:15)   12,180 bars / 203 symbols
#   2024-11-01  bars 18:00..18:59  ->  [18:00, 19:00)   12,180 bars / 203 symbols
#   2025-10-21  bars 13:45..14:44  ->  [13:45, 14:45)   12,420 bars / 207 symbols
# Only the continuous ("normal") market is expressed. No bar attests to the
# pre-open or the closing session, so neither is asserted here.
#
# MAINTENANCE: this table is load-bearing, and a special session that is NOT in
# it falls back to the era schedule - which answers 09:15-15:30 and is wrong in
# both directions: an evening session reads closed while it trades, and an
# afternoon one reads open across six hours it was shut. Add the next Muhurat
# before it happens, the same standing obligation core/market/nse_holidays.py
# carries for its holiday list.
SPECIAL_SESSIONS = {
    # Diwali Muhurat - one continuous hour.
    date(2023, 11, 12): _special((time(18, 15), time(19, 15))),
    date(2024, 11, 1): _special((time(18, 0), time(19, 0))),
    date(2025, 10, 21): _special((time(13, 45), time(14, 45))),
    # NSE special Saturdays, traded in two blocks of 45 and 60 minutes with a
    # 90-minute recess between them - the shape of a primary-site session
    # followed by a disaster-recovery-site session. Bars: 09:15..09:59 and
    # 11:30..12:29 on both dates, in every NSE_EQ symbol.
    date(2024, 3, 2): _special((time(9, 15), time(10, 0)), (time(11, 30), time(12, 30))),
    date(2024, 5, 18): _special((time(9, 15), time(10, 0)), (time(11, 30), time(12, 30))),
}


def session_windows(segment: str, on: date) -> tuple:
    """Every interval `segment` is open on `on` - more than one on a split session.

    `session_window` collapses these to outer bounds; a caller that needs the
    minutes the market was actually open (a contiguity census, say) needs them
    all.
    """
    special = SPECIAL_SESSIONS.get(on)
    if special is not None:
        return special[segment]
    resolved = _SCHEDULE[0][1]
    for effective_from, windows in _SCHEDULE:
        if on >= effective_from:
            resolved = windows
    window = resolved[segment]
    return () if window is None else (window,)


def session_window(segment: str, on: date):
    """Outer (start, end) for `segment` on `on`, or None if it does not trade.

    On a split session this spans the recess, so it answers "when does the
    session run", not "is it open now" - ask is_open() for that.
    """
    if segment not in SEGMENTS:
        raise KeyError(f"unknown segment {segment!r}; expected one of {SEGMENTS}")
    windows = session_windows(segment, on)
    return (windows[0][0], windows[-1][1]) if windows else None


def is_open(segment: str, dt: datetime) -> bool:
    """True if `segment` is open at `dt`. End boundary is exclusive.

    A split session's recess is closed, so this is not simply "inside
    session_window", which spans it.
    """
    if segment not in SEGMENTS:
        raise KeyError(f"unknown segment {segment!r}; expected one of {SEGMENTS}")
    return any(start <= dt.time() < end for start, end in session_windows(segment, dt.date()))


def any_open(dt: datetime) -> bool:
    """True if any segment is open at `dt`."""
    return any(is_open(seg, dt) for seg in SEGMENTS)
