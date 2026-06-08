"""
Master freshness — pure calendar policy (MASTER_MATERIALIZATION_POLICY.md §3).

`expected_snapshot_date(now)` is the latest NSE trading day whose daily refresh
cutoff has passed: the date the master *should* carry. Comparing it against
`InstrumentResolver.latest_snapshot_date()` yields the FRESH/WARN/BLOCK staleness
signal (MM.2). Defining "expected" off a fixed cutoff (not "has the job run yet")
removes time-of-day ambiguity across restarts.

Pure: no DB, no network. Trading days / holidays / IST come from MarketHours.
"""
from datetime import date, datetime, time, timedelta
from typing import Optional

from core.database.utils.market_hours import MarketHours

# Daily refresh cutoff (IST): the scheduled job runs before the 09:15 open; after
# this time today's snapshot is expected to exist.
REFRESH_CUTOFF = time(8, 30)


def expected_snapshot_date(now: Optional[datetime] = None) -> date:
    """The most recent trading day whose REFRESH_CUTOFF has passed, in IST."""
    now = now or MarketHours.get_ist_now()
    today = now.date()
    if MarketHours.is_trading_day(now) and now.time() >= REFRESH_CUTOFF:
        return today
    d = today - timedelta(days=1)
    while not MarketHours.is_trading_day(datetime.combine(d, time(12, 0))):
        d -= timedelta(days=1)
    return d
