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


def _continuous_only(start: time, end: time):
    """Every segment trades one continuous window, with no auction (pre-CAS shape)."""
    return {"cash_cat1": (start, end), "cash_cat2": (start, end),
            "cash_auction": None, "derivatives": (start, end)}


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
    date(2023, 11, 12): _continuous_only(time(18, 15), time(19, 15)),
    date(2024, 11, 1): _continuous_only(time(18, 0), time(19, 0)),
    date(2025, 10, 21): _continuous_only(time(13, 45), time(14, 45)),
}


def session_window(segment: str, on: date):
    """(start, end) for `segment` on `on`, or None if the segment does not exist."""
    if segment not in SEGMENTS:
        raise KeyError(f"unknown segment {segment!r}; expected one of {SEGMENTS}")
    special = SPECIAL_SESSIONS.get(on)
    if special is not None:
        return special[segment]
    resolved = _SCHEDULE[0][1]
    for effective_from, windows in _SCHEDULE:
        if on >= effective_from:
            resolved = windows
    return resolved[segment]


def is_open(segment: str, dt: datetime) -> bool:
    """True if `segment` is open at `dt`. End boundary is exclusive."""
    window = session_window(segment, dt.date())
    if window is None:
        return False
    start, end = window
    return start <= dt.time() < end


def any_open(dt: datetime) -> bool:
    """True if any segment is open at `dt`."""
    return any(is_open(seg, dt) for seg in SEGMENTS)
