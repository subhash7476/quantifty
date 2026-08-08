"""
LoopDriver DS2-2 — the pre-signal publish hook seam (NIFTY_SHIELD_STAGE2
_PREREQ_IMPLEMENTATION_PROMPT §4A).

Covers the per-session seam the Stage-2 live 13:00 fact publisher is wired
through:
- fires once per session, on the first bar at/after the checkpoint time;
- fires BEFORE on_bar on that bar (the fact must exist when the source reads it);
- a fresh session re-arms the latch; bars before the checkpoint never fire it;
- a failing hook must not kill the loop (the source then reads no fact and
  skips the session — DS2-4);
- absent wiring leaves the loop unchanged.

The hook itself is generic: the test records what it receives; the real wiring
(the daytype hook) is covered in tests/daytype.
"""
from datetime import datetime, time as dt_time
from typing import List

import pytz

from core.events import OHLCVBar, SignalEvent
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.signal_source import SignalSource

from _doubles import FakeClock, FakeMarketDataProvider, make_bar

_UTC = pytz.UTC


def _cfg(symbols=("A",), max_bars=None, poll=0.5):
    return DriverConfig(mode=Mode.REPLAY, symbols=list(symbols),
                        max_bars=max_bars, poll_interval_s=poll)


class _RecordingSource(SignalSource):
    """Records each on_bar's timestamp into a shared log alongside the hook, so
    the publish-before-on_bar ordering on the checkpoint bar is assertable."""

    def __init__(self, log: list):
        self._log = log

    def on_start(self, context=None) -> None:
        pass

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        self._log.append(("on_bar", bar.timestamp))
        return []

    def on_stop(self) -> None:
        pass


def _two_sessions_bars():
    """Session 1 = 2026-06-05, session 2 = 2026-06-06, each with 12:59/13:00/13:01."""
    out = []
    for day in (5, 6):
        for hour, minute in ((12, 59), (13, 0), (13, 1)):
            out.append(make_bar(
                "A", datetime(2026, 6, day, hour, minute, tzinfo=_UTC)))
    return out


# --------------------------------------------------------------------------- #
# Fires once per session, at/after the checkpoint, before on_bar
# --------------------------------------------------------------------------- #
def test_hook_fires_once_per_session_at_checkpoint():
    calls = []
    bars = _two_sessions_bars()
    d = LoopDriver(
        _cfg(), clock=FakeClock(),
        provider=FakeMarketDataProvider({"A": bars}),
        publish_hook=lambda ts: calls.append(ts),
        publish_checkpoint_time=dt_time(13, 0),
    )
    d.run()
    assert calls == [
        datetime(2026, 6, 5, 13, 0, tzinfo=_UTC),
        datetime(2026, 6, 6, 13, 0, tzinfo=_UTC),
    ]


def test_hook_fires_before_on_bar_on_checkpoint_bar():
    log = []
    bars = _two_sessions_bars()
    d = LoopDriver(
        _cfg(), clock=FakeClock(),
        provider=FakeMarketDataProvider({"A": bars}),
        source=_RecordingSource(log),
        publish_hook=lambda ts: log.append(("publish", ts)),
        publish_checkpoint_time=dt_time(13, 0),
    )
    d.run()
    checkpoint_ts = datetime(2026, 6, 5, 13, 0, tzinfo=_UTC)
    idx_publish = log.index(("publish", checkpoint_ts))
    idx_on_bar = log.index(("on_bar", checkpoint_ts))
    assert idx_publish < idx_on_bar          # fact written before the source reads


def test_hook_does_not_fire_before_checkpoint():
    calls = []
    bars = [make_bar("A", datetime(2026, 6, 5, 12, 58, tzinfo=_UTC)),
            make_bar("A", datetime(2026, 6, 5, 12, 59, tzinfo=_UTC))]
    d = LoopDriver(
        _cfg(), clock=FakeClock(),
        provider=FakeMarketDataProvider({"A": bars}),
        publish_hook=lambda ts: calls.append(ts),
        publish_checkpoint_time=dt_time(13, 0),
    )
    d.run()
    assert calls == []


# --------------------------------------------------------------------------- #
# Per-session latch + best-effort failure + no-wiring no-op
# --------------------------------------------------------------------------- #
def test_hook_fires_once_per_session_not_per_bar():
    calls = []
    bars = _two_sessions_bars()
    d = LoopDriver(
        _cfg(), clock=FakeClock(),
        provider=FakeMarketDataProvider({"A": bars}),
        publish_hook=lambda ts: calls.append(ts),
        publish_checkpoint_time=dt_time(13, 0),
    )
    d.run()
    assert len(calls) == 2                   # once per session, not once per bar


def test_failing_hook_does_not_kill_loop():
    d = LoopDriver(
        _cfg(), clock=FakeClock(),
        provider=FakeMarketDataProvider({"A": _two_sessions_bars()}),
        publish_hook=lambda ts: (_ for _ in ()).throw(RuntimeError("boom")),
        publish_checkpoint_time=dt_time(13, 0),
    )
    d.run()
    assert d.bars_processed == 6
    assert d.state is RuntimeState.STOPPED


def test_unwired_hook_leaves_loop_unchanged():
    bars = _two_sessions_bars()
    d = LoopDriver(
        _cfg(), clock=FakeClock(),
        provider=FakeMarketDataProvider({"A": bars}),
    )
    d.run()
    assert d.bars_processed == 6
    assert d.signals_pulled == 0
    assert d.state is RuntimeState.STOPPED
