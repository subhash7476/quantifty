"""Carry daily-bar provider — bhavcopy FUTSTK daily close for REPLAY.

Bridge: CARRY_IMPLEMENTATION_BRIDGE.md §4.1 + WS-D. One bar per underlying
per trading day. Used by LoopDriver REPLAY for the parity gate.

1m replay over 10y x 120 names is infeasible; Carry needs daily close only.

FIX (2026-07-24): Calendar-driven provider. Global cursor over union of trading
dates, ensuring all symbols deliver the same date per tick. Previously used
independent cursors per symbol, causing within-tick date misalignment when
listing histories differ.

API: Call advance_tick() after consuming get_next_bar() for all symbols.
This two-step pattern is required because LoopDriver sweeps symbols and the
provider cannot know when the sweep is complete.

See CARRY_REPLAY_INFRA_TEST_REPORT.md §3 for measurement and §5 for
the regression test that enforces this fix.
"""
from __future__ import annotations

from datetime import date as Date, datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb

from core.database.providers.base import MarketDataProvider
from core.events import OHLCVBar


class DailyBhavcopyProvider(MarketDataProvider):
    """Provides one daily bar per underlying from futures bhavcopy.

    Symbols are underlyings (e.g. "ACC", "ADANIENT"), not futures contract
    symbols. The provider reads near-month futures data from the bhavcopy
    store and produces one OHLCVBar per underlying per trading day.

    CALENDAR-DRIVEN (FIXED 2026-07-24):
    - A global cursor advances through the union of trading dates.
    - get_next_bar(symbol) returns that date's bar for the symbol, or None.
    - This ensures all symbols deliver the same date per tick.
    - Symbols with no data for a given date correctly return None.

    USAGE PATTERN (required for calendar alignment):
        for symbol in symbols:
            bar = provider.get_next_bar(symbol)
        provider.advance_tick()  # Must call after consuming all symbols

    The advance_tick() method exists because LoopDriver sweeps symbols and
    cannot notify the provider when the sweep is complete. The provider
    therefore requires explicit tick advancement.
    """

    def __init__(
        self,
        underlyings: List[str],
        bhavcopy_db: str,
        start_date: Optional[Date] = None,
        end_date: Optional[Date] = None,
    ):
        super().__init__(underlyings)
        self._bhavcopy_db = Path(bhavcopy_db)
        self._start_date = start_date
        self._end_date = end_date

        self._calendar: List[Date] = []
        self._calendar_idx = 0

        self._data: Dict[str, Dict[Date, OHLCVBar]] = {}
        self._load_data()

    def _load_data(self):
        con = duckdb.connect(str(self._bhavcopy_db), read_only=True)
        con.execute("SET threads=4")

        where_clauses = ["inst_type = 'FUTSTK'"]
        if self._start_date:
            where_clauses.append(f"trade_date >= '{self._start_date}'")
        if self._end_date:
            where_clauses.append(f"trade_date <= '{self._end_date}'")
        where = " AND ".join(where_clauses)

        for sym in self.symbols:
            rows = con.execute(f"""
                WITH near_month AS (
                    SELECT trade_date, underlying, expiry_dt,
                           open, high, low, close,
                           ROW_NUMBER() OVER (
                               PARTITION BY trade_date, underlying
                               ORDER BY expiry_dt ASC
                           ) AS rn
                    FROM futures_bhavcopy
                    WHERE {where}
                      AND underlying = '{sym}'
                )
                SELECT trade_date, open, high, low, close
                FROM near_month
                WHERE rn = 1
                ORDER BY trade_date
            """).fetchall()

            self._data[sym] = {}
            for td, o, h, l, c in rows:
                ts = datetime.combine(td, time(15, 30))
                self._data[sym][td] = OHLCVBar(
                    symbol=sym,
                    timestamp=ts,
                    open=float(o) if o else 0.0,
                    high=float(h) if h else 0.0,
                    low=float(l) if l else 0.0,
                    close=float(c) if c else 0.0,
                    volume=0,
                )

        con.close()

        self._build_calendar()

    def _build_calendar(self):
        con = duckdb.connect(str(self._bhavcopy_db), read_only=True)
        con.execute("SET threads=4")

        where_clauses = ["inst_type = 'FUTSTK'"]
        if self._start_date:
            where_clauses.append(f"trade_date >= '{self._start_date}'")
        if self._end_date:
            where_clauses.append(f"trade_date <= '{self._end_date}'")
        where = " AND ".join(where_clauses)

        symbol_list = ", ".join(f"'{sym}'" for sym in self.symbols)
        rows = con.execute(f"""
            SELECT DISTINCT trade_date
            FROM futures_bhavcopy
            WHERE {where}
              AND underlying IN ({symbol_list})
            ORDER BY trade_date
        """).fetchall()

        self._calendar = [row[0] for row in rows]
        con.close()

    def get_next_bar(self, symbol: str) -> Optional[OHLCVBar]:
        if symbol not in self._data:
            return None
        if self._calendar_idx >= len(self._calendar):
            return None

        current_date = self._calendar[self._calendar_idx]
        return self._data[symbol].get(current_date)

    def advance_tick(self) -> bool:
        """Advance to next trading date.

        Returns True if advanced, False if already at end of calendar.

        This must be called after consuming bars for all symbols at the current date.
        """
        if self._calendar_idx >= len(self._calendar):
            return False
        self._calendar_idx += 1
        return True

    def get_latest_bar(self, symbol: str) -> Optional[OHLCVBar]:
        if symbol not in self._data:
            return None

        if self._calendar_idx == 0:
            return None

        latest_date = self._calendar[self._calendar_idx - 1]
        return self._data[symbol].get(latest_date)

    def is_data_available(self, symbol: str) -> bool:
        if symbol not in self._data:
            return False
        return self._calendar_idx < len(self._calendar)

    def reset(self, symbol: str) -> None:
        self._calendar_idx = 0

    def get_progress(self, symbol: str) -> Tuple[int, int]:
        if symbol not in self._data:
            return (0, 0)
        return (self._calendar_idx, len(self._calendar))
