"""
Unit tests for the Clock set_time extension (DRIVER_SPECIFICATION.md §6.4).

Validates the minimal, additive change that lets the LoopDriver call
clock.set_time(bar.timestamp) UNIFORMLY (branch-free) on every tick:
- the base Clock exposes a no-op set_time;
- RealTimeClock inherits the no-op and ignores external time ownership;
- ReplayClock keeps owning deterministic time advancement (unchanged);
- existing behavior (now / sleep / advance) is preserved.
"""

from datetime import datetime, timedelta

import pytz

from core.clock import Clock, RealTimeClock, ReplayClock

_IST = pytz.timezone("Asia/Kolkata")
_BAR_TS = datetime(2026, 6, 5, 9, 15, 0, tzinfo=pytz.UTC)


# --------------------------------------------------------------------------- #
# Base Clock: set_time present and a no-op
# --------------------------------------------------------------------------- #
def test_base_clock_has_set_time():
    assert hasattr(Clock, "set_time")


def test_base_clock_set_time_is_noop_returns_none():
    c = Clock()
    assert c.set_time(_BAR_TS) is None
    # now() still returns a tz-aware UTC time, unaffected by set_time.
    assert c.now().tzinfo is not None


# --------------------------------------------------------------------------- #
# RealTimeClock: inherits the no-op, ignores external time ownership
# --------------------------------------------------------------------------- #
def test_realtime_clock_inherits_set_time():
    assert RealTimeClock.set_time is Clock.set_time


def test_realtime_clock_set_time_does_not_take_ownership():
    rtc = RealTimeClock()
    before = rtc.now()
    # Try to force the clock far into the past; it must ignore it.
    assert rtc.set_time(datetime(2000, 1, 1, tzinfo=pytz.UTC)) is None
    after = rtc.now()
    assert after.year >= 2026        # still wall-clock, not the injected past
    assert before.tzinfo is not None and after.tzinfo is not None


def test_realtime_clock_now_still_ist():
    rtc = RealTimeClock()
    # Wall-clock IST: offset is +05:30.
    assert rtc.now().utcoffset() == timedelta(hours=5, minutes=30)


# --------------------------------------------------------------------------- #
# ReplayClock: deterministic ownership preserved (unchanged semantics)
# --------------------------------------------------------------------------- #
def test_replay_clock_set_time_owns_time():
    rc = ReplayClock(start_time=datetime(2026, 1, 1, tzinfo=pytz.UTC))
    rc.set_time(_BAR_TS)
    assert rc.now() == _BAR_TS


def test_replay_clock_advance_still_works():
    start = datetime(2026, 6, 5, 9, 15, 0, tzinfo=pytz.UTC)
    rc = ReplayClock(start_time=start)
    rc.advance(timedelta(minutes=1))
    assert rc.now() == start + timedelta(minutes=1)


def test_replay_clock_overrides_base_set_time():
    # ReplayClock must NOT use the base no-op; it has its own override.
    assert ReplayClock.set_time is not Clock.set_time


# --------------------------------------------------------------------------- #
# Uniform, branch-free driver usage (the whole point of §6.4)
# --------------------------------------------------------------------------- #
def test_set_time_is_uniform_across_clock_types():
    replay = ReplayClock(start_time=datetime(2026, 1, 1, tzinfo=pytz.UTC))
    live = RealTimeClock()
    # The driver calls set_time identically on any clock without branching.
    for clock in (replay, live):
        assert clock.set_time(_BAR_TS) is None
    # Replay took the timestamp; live ignored it.
    assert replay.now() == _BAR_TS
    assert live.now().year >= 2026
