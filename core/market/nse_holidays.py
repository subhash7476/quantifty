"""NSE trading holidays — the single list, importable without the database stack.

Source: https://www.nseindia.com/resources/exchange-communication-holidays
Add each calendar year's list when NSE publishes it; code that needs a future
session count hard-fails on a year with no entries rather than guessing.
"""
from __future__ import annotations

from datetime import date, timedelta

NSE_HOLIDAYS: frozenset[date] = frozenset({
    date(2026, 1, 15),   # Municipal Corporation Election - Maharashtra
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 3),    # Holi
    date(2026, 3, 26),   # Shri Ram Navami
    date(2026, 3, 31),   # Shri Mahavir Jayanti
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 5, 28),   # Bakri Id
    date(2026, 6, 26),   # Muharram
    date(2026, 9, 14),   # Ganesh Chaturthi
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra
    date(2026, 11, 10),  # Diwali-Balipratipada
    date(2026, 11, 24),  # Prakash Gurpurb Sri Guru Nanak Dev
    date(2026, 12, 25),  # Christmas
})


def sessions_after(start: date, end: date, holidays: frozenset[date] = NSE_HOLIDAYS) -> list[date]:
    """Weekday non-holiday dates in (start, end]."""
    out, d = [], start + timedelta(days=1)
    while d <= end:
        if d.weekday() < 5 and d not in holidays:
            out.append(d)
        d += timedelta(days=1)
    return out
