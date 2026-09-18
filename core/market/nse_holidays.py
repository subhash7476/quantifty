"""NSE trading holidays — the single list, importable without the database stack.

Source: https://www.nseindia.com/resources/exchange-communication-holidays
Add each calendar year's list when NSE publishes it; code that needs a future
session count hard-fails on a year with no entries rather than guessing.

2023-2025 entries: extracted from NSE-published circulars; supplied for
incorporation into the repository. Weekday market-closed dates only. Holidays
that fell on a weekend, Diwali Muhurat dates, and the 2024-01-22 special trading
holiday are deliberately not listed here; special sessions and weekend trading
days are a separate mechanism.
"""
from __future__ import annotations

from datetime import date, timedelta

NSE_HOLIDAYS: frozenset[date] = frozenset({
    date(2023, 1, 26),   # Republic Day
    date(2023, 3, 7),    # Holi
    date(2023, 3, 30),   # Shri Ram Navami
    date(2023, 4, 4),    # Shri Mahavir Jayanti
    date(2023, 4, 7),    # Good Friday
    date(2023, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2023, 5, 1),    # Maharashtra Day
    date(2023, 6, 28),   # Bakri Id
    date(2023, 8, 15),   # Independence Day
    date(2023, 9, 19),   # Ganesh Chaturthi
    date(2023, 10, 2),   # Mahatma Gandhi Jayanti
    date(2023, 10, 24),  # Dussehra
    date(2023, 11, 14),  # Diwali-Balipratipada
    date(2023, 11, 27),  # Guru Nanak Jayanti
    date(2023, 12, 25),  # Christmas
    date(2024, 1, 26),   # Republic Day
    date(2024, 3, 8),    # Mahashivratri
    date(2024, 3, 25),   # Holi
    date(2024, 3, 29),   # Good Friday
    date(2024, 4, 11),   # Id-Ul-Fitr (Ramzan Id)
    date(2024, 4, 17),   # Shri Ram Navami
    date(2024, 5, 1),    # Maharashtra Day
    date(2024, 6, 17),   # Bakri Id
    date(2024, 7, 17),   # Muharram
    date(2024, 8, 15),   # Independence Day
    date(2024, 10, 2),   # Mahatma Gandhi Jayanti
    date(2024, 11, 15),  # Guru Nanak Jayanti
    date(2024, 12, 25),  # Christmas
    date(2025, 2, 26),   # Mahashivratri
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Id-Ul-Fitr (Ramzan Id)
    date(2025, 4, 10),   # Shri Mahavir Jayanti
    date(2025, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Ganesh Chaturthi
    date(2025, 10, 2),   # Mahatma Gandhi Jayanti / Dussehra
    date(2025, 10, 22),  # Diwali-Balipratipada
    date(2025, 11, 5),   # Guru Nanak Jayanti
    date(2025, 12, 25),  # Christmas
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
