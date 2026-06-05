"""
Shared test doubles for LoopDriver runtime tests.

Not a test module (no test_ prefix, so pytest does not collect it). Provides
lightweight, deterministic fakes injected into the driver:
- FakeClock: records set_time / sleep calls; no real time, no real sleeping.
- FakeMarketDataProvider: scripts bars per symbol; replay (exhausts) or live
  (always available, may yield scripted None gaps).
- make_bar / bar_series: OHLCVBar builders with controllable timestamps.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytz

from core.clock import Clock
from core.database.providers.base import MarketDataProvider
from core.events import OHLCVBar

_UTC = pytz.UTC
_T0 = datetime(2026, 6, 5, 9, 15, 0, tzinfo=_UTC)


def make_bar(symbol: str = "A", ts: Optional[datetime] = None,
             close: float = 100.0) -> OHLCVBar:
    ts = ts or _T0
    return OHLCVBar(symbol=symbol, timestamp=ts, open=close, high=close,
                    low=close, close=close, volume=0.0)


def bar_series(symbol: str = "A", n: int = 3, start: Optional[datetime] = None,
               step_minutes: int = 1, close: float = 100.0) -> List[OHLCVBar]:
    start = start or _T0
    return [make_bar(symbol, start + timedelta(minutes=i * step_minutes), close)
            for i in range(n)]


class FakeClock(Clock):
    """
    Deterministic clock: set_time records the new time (and history); sleep is a
    no-op that only records the requested durations (so live-poll tests are fast
    and assertable). now() returns the last set time.
    """

    def __init__(self):
        self.times: List[datetime] = []
        self.sleeps: List[float] = []
        self._now: Optional[datetime] = None

    def now(self) -> Optional[datetime]:
        return self._now

    def set_time(self, dt: datetime) -> None:
        self._now = dt
        self.times.append(dt)

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)


class FakeMarketDataProvider(MarketDataProvider):
    """
    Scripts bars per symbol.

    replay (default): get_next_bar yields each scripted bar then None;
        is_data_available is True until the script for that symbol is consumed,
        then False (so the loop ends on exhaustion).
    live (live=True): is_data_available is always True (feed active); a script
        entry may be None to simulate a no-bar poll, and once consumed
        get_next_bar returns None forever (the loop ends via max_bars / stop()).
    """

    def __init__(self, bars_by_symbol: Dict[str, List[Optional[OHLCVBar]]],
                 live: bool = False):
        super().__init__(list(bars_by_symbol.keys()))
        self._scripts = {s: list(b) for s, b in bars_by_symbol.items()}
        self._idx = {s: 0 for s in self._scripts}
        self._live = live

    def get_next_bar(self, symbol: str) -> Optional[OHLCVBar]:
        script = self._scripts[symbol]
        i = self._idx[symbol]
        if i < len(script):
            self._idx[symbol] = i + 1
            return script[i]  # may be None for a scripted live gap
        return None

    def get_latest_bar(self, symbol: str) -> Optional[OHLCVBar]:
        i = self._idx[symbol]
        return self._scripts[symbol][i - 1] if i > 0 else None

    def is_data_available(self, symbol: str) -> bool:
        if self._live:
            return True
        return self._idx[symbol] < len(self._scripts[symbol])

    def reset(self, symbol: str) -> None:
        self._idx[symbol] = 0

    def get_progress(self, symbol: str):
        return (self._idx[symbol], len(self._scripts[symbol]))
