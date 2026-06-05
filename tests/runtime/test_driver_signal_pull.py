"""
Unit tests for LoopDriver Phase D — SignalSource integration (pull only).

Validates DRIVER_SPECIFICATION.md §5 / §7.2 in the still-inert loop:
- source.on_bar(bar) is called once per bar, with the bar the clock advanced to,
  and signals are collected in list order (never re-ranked);
- signals_pulled counts the collected signals; an empty list is a no-op;
- on_start fires once before the loop pulls any bar (context=None), on_stop fires
  once on shutdown (and exactly once when stop() interrupts mid-run);
- the source stays OPTIONAL: with no source the loop is byte-for-byte Phase-C
  inert (runs, advances the clock, counts bars, pulls nothing).

Signals are pulled but NOT routed — there is no ExecutionHandler here. Routing
is Phase E, deliberately deferred until this phase is green.
"""

from typing import List

from core.events import OHLCVBar, SignalEvent, SignalType
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState

from _doubles import (FakeClock, FakeMarketDataProvider, FakeSignalSource,
                      bar_series, make_bar, make_signal)


def _cfg(symbols=("A",), max_bars=None, poll=0.5):
    return DriverConfig(mode=Mode.REPLAY, symbols=list(symbols),
                        max_bars=max_bars, poll_interval_s=poll)


# --------------------------------------------------------------------------- #
# on_bar is pulled once per bar, with the right bar, in order
# --------------------------------------------------------------------------- #
def test_on_bar_called_once_per_bar_in_order():
    bars = bar_series("A", 3)
    source = FakeSignalSource()
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bars}), source=source)
    d.run()
    assert source.bars_seen == bars            # once each, same objects, in order


def test_on_bar_receives_bar_after_clock_advance():
    # The clock must be advanced to bar.timestamp BEFORE on_bar sees it (§7.2).
    bars = bar_series("A", 2)
    clock = FakeClock()

    class _AssertingSource(FakeSignalSource):
        def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
            # The clock's current time equals this bar's timestamp at pull time.
            assert clock.now() == bar.timestamp
            return super().on_bar(bar)

    d = LoopDriver(_cfg(), clock=clock,
                   provider=FakeMarketDataProvider({"A": bars}),
                   source=_AssertingSource())
    d.run()
    assert clock.times == [b.timestamp for b in bars]


# --------------------------------------------------------------------------- #
# Collection: count + order preservation + empty no-op
# --------------------------------------------------------------------------- #
def test_signals_pulled_counts_all_returned_signals():
    s0 = [make_signal("A"), make_signal("B")]
    s1 = [make_signal("C")]
    source = FakeSignalSource([s0, s1])         # bar2 falls off the script -> []
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}),
                   source=source)
    d.run()
    assert d.signals_pulled == 3
    assert d.bars_processed == 3


def test_empty_signal_list_is_a_noop():
    source = FakeSignalSource()                 # every on_bar returns []
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 4)}),
                   source=source)
    d.run()
    assert d.signals_pulled == 0
    assert d.bars_processed == 4
    assert d.state is RuntimeState.STOPPED


def test_signal_order_preserved_not_reranked():
    # Deliberately NOT in any natural sort order — the driver must hand them to
    # its dispatch seam verbatim (list order IS routing order, §5.2).
    s_sell = make_signal("Z", SignalType.SELL)
    s_buy = make_signal("A", SignalType.BUY)
    s_exit = make_signal("M", SignalType.EXIT)
    ordered = [s_sell, s_buy, s_exit]

    class _RecordingDriver(LoopDriver):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.dispatched: List[SignalEvent] = []

        def _dispatch_signals(self, signals, bar):
            self.dispatched.extend(signals)
            super()._dispatch_signals(signals, bar)

    d = _RecordingDriver(_cfg(max_bars=1), clock=FakeClock(),
                         provider=FakeMarketDataProvider({"A": [make_bar("A")]}),
                         source=FakeSignalSource([ordered]))
    d.run()
    assert d.dispatched == ordered              # identity + order, untouched


# --------------------------------------------------------------------------- #
# Lifecycle hooks: on_start before the loop, on_stop on shutdown
# --------------------------------------------------------------------------- #
def test_on_start_called_once_before_loop_with_none_context():
    source = FakeSignalSource()
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 2)}),
                   source=source)
    d.run()
    assert source.started == 1
    assert source.start_context is None         # §5.4: no ledger/broker/handler
    assert source.bars_at_start == 0            # fired before any bar was pulled


def test_on_stop_called_once_on_shutdown():
    source = FakeSignalSource()
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 2)}),
                   source=source)
    d.run()
    assert source.stopped == 1


def test_on_stop_called_once_when_stopped_midrun():
    box = []

    class _StoppingProvider(FakeMarketDataProvider):
        def get_next_bar(self, symbol):
            bar = super().get_next_bar(symbol)
            if bar is not None and self._idx[symbol] == 1:
                box[0].stop()
            return bar

    source = FakeSignalSource()
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=_StoppingProvider({"A": bar_series("A", 5)}),
                   source=source)
    box.append(d)
    d.run()
    assert d.state is RuntimeState.STOPPED
    assert source.stopped == 1                  # not double-fired by stop()+finally


# --------------------------------------------------------------------------- #
# The source is OPTIONAL — no source => Phase-C inert loop, unchanged
# --------------------------------------------------------------------------- #
def test_no_source_runs_phase_c_inert():
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 3)}))
    d.run()
    assert d.bars_processed == 3
    assert d.signals_pulled == 0
    assert d.state is RuntimeState.STOPPED


def test_signals_pulled_starts_at_zero():
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 2)}),
                   source=FakeSignalSource())
    assert d.signals_pulled == 0
