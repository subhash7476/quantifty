"""
Instrument-master readiness verdict (MASTER_MATERIALIZATION_POLICY.md §4).

Maps freshness + coverage FACTS to a FRESH / WARN / BLOCK verdict. **Coverage is
the hard gate; date is the early-warning proxy** (§4) — a master dated today but
missing its derivative contracts BLOCKs regardless of date (the schema-shift risk
a date-only check misses).

Ownership (MM.4_DESIGN_REVIEW.md §3-impl, Decision 5): the resolver supplies
facts, this module owns the judgment, the LoopDriver owns the gate decision. The
pure verdict core is `evaluate`; `assess` gathers facts from a resolver. Neither
creates readiness — this is evaluation only, never a refresh/repair (Decision 6).
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Iterable, Optional

from core.database.utils.market_hours import MarketHours
from core.instruments.master_freshness import expected_snapshot_date

# Derivative segments whose coverage the live F&O gate asserts (§4).
_DERIVATIVE_SEGMENTS = ("NSE_FO", "MCX_FO")


class ReadinessState(Enum):
    """The three master-readiness outcomes (policy §4)."""
    FRESH = "FRESH"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ReadinessVerdict:
    """A readiness outcome plus the facts behind it. `reason` is set on BLOCK only
    (`absent` | `coverage` | `stale`) so the gate can journal why it refused."""
    state: ReadinessState
    reason: Optional[str] = None
    latest: Optional[date] = None
    expected: Optional[date] = None


def _previous_trading_day(d: date) -> date:
    """The NSE trading day immediately before `d` (IST holidays/weekends)."""
    prev = d - timedelta(days=1)
    while not MarketHours.is_trading_day(datetime.combine(prev, time(12, 0))):
        prev -= timedelta(days=1)
    return prev


def evaluate(latest: Optional[date], expected: date, *,
             coverage_ok: bool) -> ReadinessVerdict:
    """Pure verdict from facts. Precedence (§4): absent → coverage → stale → warn
    → fresh. Coverage is checked before the date proxy — a current-dated master
    that fails coverage still BLOCKs."""
    if latest is None:
        return ReadinessVerdict(ReadinessState.BLOCK, "absent", None, expected)
    if not coverage_ok:
        return ReadinessVerdict(ReadinessState.BLOCK, "coverage", latest, expected)
    if latest >= expected:
        return ReadinessVerdict(ReadinessState.FRESH, None, latest, expected)
    if latest == _previous_trading_day(expected):
        return ReadinessVerdict(ReadinessState.WARN, None, latest, expected)
    return ReadinessVerdict(ReadinessState.BLOCK, "stale", latest, expected)


def assess(resolver, underlyings: Iterable[str], now: Optional[datetime] = None,
           derivative_segments: Iterable[str] = _DERIVATIVE_SEGMENTS) -> ReadinessVerdict:
    """Gather freshness + coverage facts from `resolver` and return the verdict.

    Coverage = a derivative segment is present and non-empty AND an active expiry
    (>= expected) exists for every traded underlying (§4 minimum, Decision 1) — any
    cadence, not specifically weekly (BankNifty is monthly-only). Read-only;
    never refreshes the master.
    """
    now = now or MarketHours.get_ist_now()
    expected = expected_snapshot_date(now)
    latest = resolver.latest_snapshot_date()
    if latest is None:
        return evaluate(None, expected, coverage_ok=False)
    segment_present = any(resolver.segment_row_count(seg) > 0
                          for seg in derivative_segments)
    expiries_present = all(resolver.active_expiry_present(u, expected)
                           for u in underlyings)
    return evaluate(latest, expected, coverage_ok=segment_present and expiries_present)
