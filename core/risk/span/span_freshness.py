"""
SPAN Freshness — Expected trading-date computation (MM9.4-S2).

The expected SPAN snapshot date is the latest NSE trading day whose 08:30 IST
refresh cutoff has passed. This mirrors the logic in
core/instruments/master_freshness.py and uses MarketHours for holiday/weekend
awareness, ensuring both the instrument master and SPAN snapshot gates agree
on what day it is.
"""

from datetime import date, datetime
from typing import Optional

from core.instruments.master_freshness import expected_snapshot_date


def expected_span_date(now: Optional[datetime] = None) -> date:
    """Compute the expected SPAN snapshot date.

    Returns the latest NSE trading day whose published SPAN file should be
    available and current. Delegates to the instrument master freshness
    function so both gates agree on what day it is.

    Args:
        now: The current datetime (UTC-aware). If None, uses datetime.now(UTC).

    Returns:
        A trading date.
    """
    return expected_snapshot_date(now)
