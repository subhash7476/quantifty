"""
MM.7C — C6: the SignalSource lifecycle the driver guarantees.

Pins the contract MM7D's strategy lifecycle relies on (driver.py:521-552,
560-588):
- on_start fires exactly once, BEFORE the loop pulls any bar;
- on_bar fires once per bar;
- on_stop fires exactly once on shutdown;
- the clock is advanced to bar.timestamp BEFORE on_bar (so a source reading a
  clock sees the bar's time, not the prior tick's) — ADR-003;
- an empty-list return is a no-op (no routing, loop still advances).

ZERO production code changed.
"""
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.runtime.signal_source import SignalSource

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, bar_series)

_SYM = "NSE_FO|53001"


class _ClockObservingSource(SignalSource):
    """Holds a clock (permitted — a clock is not the ledger/broker/handler) and
    records clock.now() at each on_bar so the test can prove the driver advanced
    the clock to bar.timestamp BEFORE calling on_bar."""

    def __init__(self, clock):
        self._clock = clock
        self.seen = []   # (clock_now_at_call, bar_timestamp)

    def on_bar(self, bar):
        self.seen.append((self._clock.now(), bar.timestamp))
        return []


# --------------------------------------------------------------------------- #
# on_start once before the loop; on_bar once per bar; on_stop once.
# --------------------------------------------------------------------------- #
def test_lifecycle_hooks_fire_in_order_and_counts():
    source = FakeSignalSource()
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=[_SYM], max_bars=3)
    d = LoopDriver(cfg, clock=FakeClock(),
                   provider=FakeMarketDataProvider({_SYM: bar_series(_SYM, 3)}),
                   source=source)
    d.run()
    assert source.started == 1
    assert source.bars_at_start == 0          # on_start ran before any bar was seen
    assert len(source.bars_seen) == 3         # on_bar once per bar
    assert source.stopped == 1                # on_stop once on shutdown


# --------------------------------------------------------------------------- #
# The clock is advanced to bar.timestamp BEFORE on_bar (ADR-003).
# --------------------------------------------------------------------------- #
def test_clock_is_advanced_before_on_bar():
    clock = FakeClock()
    bars = bar_series(_SYM, 3)
    source = _ClockObservingSource(clock)
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=[_SYM], max_bars=3)
    d = LoopDriver(cfg, clock=clock,
                   provider=FakeMarketDataProvider({_SYM: bars}),
                   source=source)
    d.run()
    assert len(source.seen) == 3
    for now_at_call, bar_ts in source.seen:
        assert now_at_call == bar_ts          # clock already at this bar's time


# --------------------------------------------------------------------------- #
# An empty-list return is a no-op: no routing, but the loop still advances bars.
# --------------------------------------------------------------------------- #
def test_empty_list_is_a_noop():
    handler = FakeExecutionHandler(reconcile_alerts=[])
    source = FakeSignalSource(signals_per_bar=[[], [], []])   # always empty
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=[_SYM], max_bars=3)
    d = LoopDriver(cfg, clock=FakeClock(),
                   provider=FakeMarketDataProvider({_SYM: bar_series(_SYM, 3)}),
                   execution=handler, source=source)
    d.run()
    assert d.bars_processed == 3              # loop advanced
    assert handler.routed == []               # nothing routed
    assert d.signals_pulled == 0
