"""Date-keyed, segment-named NSE session windows.

The single authority for "when is segment X open on date D". SEBI's Closing
Auction Session (circular 2026-01-16, operative 2026-08-03) split what used to
be one 09:15-15:30 session into four differently-bounded segments, so a single
MARKET_CLOSE constant can no longer express the truth.

Era-schedule shape mirrors core/execution/equity/intraday_fees.py's
_STT_INTRADAY_SCHEDULE: newest era last, resolved by scanning for the latest
entry whose effective date is <= the queried date.
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


def session_window(segment: str, on: date):
    """(start, end) for `segment` on `on`, or None if the segment does not exist."""
    if segment not in SEGMENTS:
        raise KeyError(f"unknown segment {segment!r}; expected one of {SEGMENTS}")
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
