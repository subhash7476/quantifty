"""Carry daily-bar provider — bhavcopy FUTSTK daily close for REPLAY.

Bridge: CARRY_IMPLEMENTATION_BRIDGE.md §4.1 + WS-D. One bar per underlying
per trading day. Used by LoopDriver REPLAY for the parity gate.

1m replay over 10y x 120 names is infeasible; Carry needs daily close only.
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
        self._data: Dict[str, List[OHLCVBar]] = {}
        self._indices: Dict[str, int] = {}
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
            bars = []
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

            for td, o, h, l, c in rows:
                ts = datetime.combine(td, time(15, 30))
                bars.append(OHLCVBar(
                    symbol=sym,
                    timestamp=ts,
                    open=float(o) if o else 0.0,
                    high=float(h) if h else 0.0,
                    low=float(l) if l else 0.0,
                    close=float(c) if c else 0.0,
                    volume=0,
                ))

            self._data[sym] = bars
            self._indices[sym] = 0

        con.close()

    def get_next_bar(self, symbol: str) -> Optional[OHLCVBar]:
        if symbol not in self._data:
            return None
        idx = self._indices.get(symbol, 0)
        bars = self._data[symbol]
        if idx >= len(bars):
            return None
        bar = bars[idx]
        self._indices[symbol] = idx + 1
        return bar

    def get_latest_bar(self, symbol: str) -> Optional[OHLCVBar]:
        if symbol not in self._data:
            return None
        idx = self._indices.get(symbol, 0)
        bars = self._data[symbol]
        if idx > 0:
            return bars[idx - 1]
        elif bars:
            return bars[0]
        return None

    def is_data_available(self, symbol: str) -> bool:
        if symbol not in self._data:
            return False
        return self._indices.get(symbol, 0) < len(self._data[symbol])

    def reset(self, symbol: str) -> None:
        if symbol in self._indices:
            self._indices[symbol] = 0

    def get_progress(self, symbol: str) -> Tuple[int, int]:
        if symbol not in self._data:
            return (0, 0)
        return (self._indices.get(symbol, 0), len(self._data[symbol]))
