"""Which minute does a 1m bar's timestamp refer to?

The per-day 1m store spans two labelling conventions:

  - **end-labelled** (vendor era): the bar stamped *t* covers *t−1 → t*, so a
    session opening at 09:15 has its first bar stamped **09:16**.
  - **start-labelled** (native era): the bar stamped *t* covers *t → t+1*, so
    the same session's first bar is stamped **09:15**.

The era is resolved from the **observed first-bar stamp, not the calendar
date** — the analog-path track's AP-D4 operator decision, generalized here.
Twenty January-2023 sessions carry provenance metadata that disagrees with
their actual labelling, so the date is not reliable and the bars are.

The rule is expressed against the session's own opening time rather than
against a hardcoded 09:15, which is what makes it hold on special sessions
too: Muhurat 2025-10-21 opens 13:45 and its first bar is stamped 13:45.

This module **refuses rather than guesses**. A first-bar stamp that is neither
the open nor one minute after it raises `UnknownLabeling`, which is the whole
point: an unrecognised stamp is a fact about the data, not a value to infer.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from core.market.session_schedule import session_window

NATIVE = "native"
VENDOR = "vendor"


class UnknownLabeling(ValueError):
    """The first bar's stamp matches neither labelling convention."""


def _shift(t: time, minutes: int) -> time:
    return (datetime(2000, 1, 1, t.hour, t.minute) + timedelta(minutes=minutes)).time()


def labeling_of(first_stamp: time, on: date, segment: str = "cash_cat1") -> str:
    """`NATIVE` or `VENDOR` for a session whose first bar is stamped `first_stamp`.

    Raises `UnknownLabeling` for any other stamp, and for a date on which the
    segment does not trade at all.
    """
    window = session_window(segment, on)
    if window is None:
        raise UnknownLabeling(f"{on}: segment {segment!r} does not trade")
    opens = window[0]
    if first_stamp == opens:
        return NATIVE
    if first_stamp == _shift(opens, 1):
        return VENDOR
    raise UnknownLabeling(
        f"{on}: first bar stamped {first_stamp} is neither the {opens} open "
        f"(start-labelled) nor {_shift(opens, 1)} (end-labelled)")


def covered_interval(stamp: time, labeling: str) -> tuple[time, time]:
    """The minute a bar stamped `stamp` actually covers, as [start, end)."""
    if labeling == NATIVE:
        return stamp, _shift(stamp, 1)
    if labeling == VENDOR:
        return _shift(stamp, -1), stamp
    raise ValueError(f"unknown labeling {labeling!r}")
