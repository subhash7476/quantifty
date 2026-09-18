"""Which dates NIFTY actually traded — sessionhood, not schedule.

Composes three committed sets, in this precedence:

  1. ADDITIONAL_SESSIONS -> session   (every session off the weekday rule)
  2. weekend             -> not a session
  3. SPECIAL_CLOSURES    -> not a session
  4. NSE_HOLIDAYS        -> not a session
  5. otherwise weekday   -> session

`session_schedule.SPECIAL_SESSIONS` does NOT decide sessionhood; it only says
when a session runs. Nor does the 1m store: 2026-02-01 traded although its
Nifty 50 bars were never captured.

Coverage is declared, not inferred. Outside COVERAGE_FIRST..COVERAGE_LAST the
holiday, closure and additional-session sets are not asserted complete, so any
question about such a date raises rather than falling back to the weekday rule.
Extending coverage means adding that year's holidays, closures and weekend or
special sessions first.
"""
from __future__ import annotations

from datetime import date, timedelta

from core.market.nse_holidays import NSE_HOLIDAYS

COVERAGE_FIRST = date(2023, 1, 1)
COVERAGE_LAST = date(2026, 12, 31)

# Longest walk previous_session may take. The largest real gap in coverage is a
# weekend plus holidays; anything longer means the chronology is wrong.
MAX_LOOKBACK_DAYS = 10

ADDITIONAL_SESSIONS: frozenset[date] = frozenset({
    date(2023, 11, 12),  # Sun - Diwali Muhurat
    date(2024, 1, 20),   # Sat - full session
    date(2024, 3, 2),    # Sat - DR special session (split)
    date(2024, 5, 18),   # Sat - DR special session (split)
    date(2025, 2, 1),    # Sat - Union Budget session
    date(2026, 2, 1),    # Sun - Union Budget session (Nifty 1m not captured)
})

# Weekday market-wide closures that are not ordinary NSE_HOLIDAYS entries.
SPECIAL_CLOSURES: frozenset[date] = frozenset({
    date(2024, 1, 22),   # special trading holiday
    date(2024, 5, 20),   # election closure, NSE/CMTR/61518
    date(2024, 11, 20),  # Maharashtra Assembly election closure, NSE/CMTR/64960
})


class OutsideCoverage(ValueError):
    """The date lies outside the declared calendar coverage."""


def _require_covered(d: date) -> None:
    if not COVERAGE_FIRST <= d <= COVERAGE_LAST:
        raise OutsideCoverage(
            f"{d} is outside declared calendar coverage "
            f"{COVERAGE_FIRST}..{COVERAGE_LAST}")


def is_session(d: date) -> bool:
    """True if NIFTY actually traded on `d`."""
    _require_covered(d)
    if d in ADDITIONAL_SESSIONS:
        return True
    if d.weekday() >= 5:
        return False
    if d in SPECIAL_CLOSURES or d in NSE_HOLIDAYS:
        return False
    return True


def previous_session(d: date) -> date:
    """The greatest actual NIFTY session date strictly less than `d`."""
    s = d - timedelta(days=1)
    for _ in range(MAX_LOOKBACK_DAYS):
        if is_session(s):
            return s
        s -= timedelta(days=1)
    raise LookupError(f"no session within {MAX_LOOKBACK_DAYS} days before {d}")
