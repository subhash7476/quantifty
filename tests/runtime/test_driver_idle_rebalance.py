"""LoopDriver — the rebalance hook on a no-bar tick (`rebalance_on_idle`).

Why the seam exists: NiftyShield's underlying prints its last 1m bar at the
15:29 cash auction while its options trade to 15:40, so a purely bar-driven
exit manager cannot reach a 15:35 hard exit — the position would be carried
overnight. The flag is opt-in because a book-level rebalancer (Carry) must
never see a between-bars invocation.
"""
from __future__ import annotations

from datetime import datetime

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver


class _StubClock:
    def __init__(self, now: datetime):
        self._now = now
        self.sleeps = 0

    def now(self) -> datetime:
        return self._now

    def set_time(self, ts) -> None:
        self._now = ts

    def sleep(self, _s) -> None:
        self.sleeps += 1


def _driver(*, on_idle: bool, hook, execution=object()) -> LoopDriver:
    cfg = DriverConfig(mode=Mode.LIVE, symbols=["NSE_INDEX|Nifty 50"],
                       rebalance_on_idle=on_idle)
    return LoopDriver(cfg, rebalance_hook=hook, execution=execution)


def test_idle_rebalance_is_off_by_default():
    assert DriverConfig(mode=Mode.LIVE, symbols=["A"]).rebalance_on_idle is False


def test_no_bar_tick_does_not_call_the_hook_when_disabled():
    calls = []
    _driver(on_idle=False, hook=lambda ts, ex: calls.append(ts))\
        ._drive_idle_rebalance()
    assert calls == []


def test_no_bar_tick_calls_the_hook_at_the_clocks_own_time_when_enabled():
    """The hook gets the CLOCK's time, not a bar timestamp — that is the whole
    point: after 15:29 there is no bar to read a time from."""
    calls = []
    now = datetime(2026, 9, 8, 15, 33, 0)
    driver = _driver(on_idle=True, hook=lambda ts, ex: calls.append(ts))
    driver._clock = _StubClock(now)
    driver._drive_idle_rebalance()
    assert calls == [now]


def test_idle_rebalance_needs_both_a_hook_and_an_execution_handler():
    driver = _driver(on_idle=True, hook=None)
    driver._clock = _StubClock(datetime(2026, 9, 8, 15, 33, 0))
    driver._drive_idle_rebalance()               # no hook — no-op, no raise

    calls = []
    driver = _driver(on_idle=True, hook=lambda ts, ex: calls.append(ts),
                     execution=None)
    driver._clock = _StubClock(datetime(2026, 9, 8, 15, 33, 0))
    driver._drive_idle_rebalance()
    assert calls == []                           # no handler — nothing to route
