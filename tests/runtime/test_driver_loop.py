"""
Unit tests for LoopDriver Phase C — tick loop skeleton.

Validates DRIVER_SPECIFICATION.md §4/§6/§7 in the inert loop:
- run() pulls bars, advances the clock to each bar.timestamp BEFORE per-bar
  work, counts bars, and shuts down cleanly to STOPPED;
- replay exhaustion ends the run; live no-bar polls (clock.sleep) and continues;
- the max_bars guard halts; stop() interrupts mid-run;
- multi-symbol bars are pulled in fixed config order;
- run() requires an injected clock + provider;
- a full run emits the STARTUP/RUNNING/STOPPING/STOPPED lifecycle (Phase B+C).
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal

from _doubles import FakeClock, FakeMarketDataProvider, bar_series, make_bar

_FIXED = datetime(2026, 6, 5, 9, 15, 0, tzinfo=ZoneInfo("Asia/Kolkata"))


def _cfg(symbols=("A",), max_bars=None, poll=0.5):
    return DriverConfig(mode=Mode.REPLAY, symbols=list(symbols),
                        max_bars=max_bars, poll_interval_s=poll)


# --------------------------------------------------------------------------- #
# Replay: run to exhaustion
# --------------------------------------------------------------------------- #
def test_replay_runs_all_bars_then_stopped():
    bars = bar_series("A", 3)
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bars}))
    d.run()
    assert d.bars_processed == 3
    assert d.state is RuntimeState.STOPPED


def test_clock_advances_to_each_bar_timestamp_in_order():
    bars = bar_series("A", 3)
    clock = FakeClock()
    d = LoopDriver(_cfg(), clock=clock,
                   provider=FakeMarketDataProvider({"A": bars}))
    d.run()
    assert clock.times == [b.timestamp for b in bars]


def test_empty_data_stops_immediately():
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": []}))
    d.run()
    assert d.bars_processed == 0
    assert d.state is RuntimeState.STOPPED


def test_bars_processed_starts_at_zero():
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 2)}))
    assert d.bars_processed == 0


# --------------------------------------------------------------------------- #
# max_bars guard
# --------------------------------------------------------------------------- #
def test_max_bars_halts_single_symbol():
    d = LoopDriver(_cfg(max_bars=4), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 10)}))
    d.run()
    assert d.bars_processed == 4
    assert d.state is RuntimeState.STOPPED


def test_max_bars_exact_with_multi_symbol():
    # Inner per-symbol guard keeps the count exact even across symbols.
    provider = FakeMarketDataProvider(
        {"A": bar_series("A", 5), "B": bar_series("B", 5)})
    d = LoopDriver(_cfg(symbols=("A", "B"), max_bars=3), clock=FakeClock(),
                   provider=provider)
    d.run()
    assert d.bars_processed == 3


# --------------------------------------------------------------------------- #
# Multi-symbol fixed ordering
# --------------------------------------------------------------------------- #
def test_multi_symbol_pulled_in_fixed_order():
    a = bar_series("A", 2, start=datetime(2026, 6, 5, 9, 15, tzinfo=ZoneInfo("UTC")))
    b = bar_series("B", 2, start=datetime(2026, 6, 5, 10, 0, tzinfo=ZoneInfo("UTC")))
    clock = FakeClock()
    d = LoopDriver(_cfg(symbols=("A", "B")), clock=clock,
                   provider=FakeMarketDataProvider({"A": a, "B": b}))
    d.run()
    # Each tick pulls A then B (config order): A0, B0, A1, B1.
    assert clock.times == [a[0].timestamp, b[0].timestamp,
                           a[1].timestamp, b[1].timestamp]
    assert d.bars_processed == 4


# --------------------------------------------------------------------------- #
# Live: no-bar poll
# --------------------------------------------------------------------------- #
def test_live_none_bar_triggers_sleep_then_continues():
    # Script: first pull yields no bar (gap), second yields a bar. live=True so
    # the feed never "exhausts"; max_bars=1 ends the run after the real bar.
    bar = make_bar("A")
    provider = FakeMarketDataProvider({"A": [None, bar]}, live=True)
    clock = FakeClock()
    d = LoopDriver(_cfg(max_bars=1, poll=0.25), clock=clock, provider=provider)
    d.run()
    assert clock.sleeps == [0.25]          # slept once on the no-bar pass
    assert d.bars_processed == 1
    assert d.state is RuntimeState.STOPPED


# --------------------------------------------------------------------------- #
# Cooperative stop mid-run
# --------------------------------------------------------------------------- #
def test_stop_interrupts_mid_run():
    box = []

    class _StoppingProvider(FakeMarketDataProvider):
        def get_next_bar(self, symbol):
            bar = super().get_next_bar(symbol)
            if bar is not None and self._idx[symbol] == 1:  # after the first bar
                box[0].stop()
            return bar

    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=_StoppingProvider({"A": bar_series("A", 5)}))
    box.append(d)
    d.run()
    assert d.bars_processed == 1            # stopped right after the first bar
    assert d.state is RuntimeState.STOPPED


# --------------------------------------------------------------------------- #
# run() preconditions
# --------------------------------------------------------------------------- #
def test_run_requires_clock_and_provider():
    with pytest.raises(RuntimeError, match="clock and market-data provider"):
        LoopDriver(_cfg()).run()  # no clock/provider injected


# --------------------------------------------------------------------------- #
# Lifecycle + journal integration (Phase B + C)
# --------------------------------------------------------------------------- #
def test_full_run_emits_lifecycle_sequence(tmp_path):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"),
                                  now=lambda: _FIXED)
    d = LoopDriver(_cfg(), clock=FakeClock(),
                   provider=FakeMarketDataProvider({"A": bar_series("A", 2)}),
                   journal=journal)
    d.run()
    types = [json.loads(l)["event_type"]
             for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]
    assert types == ["STARTUP", "RUNNING", "STOPPING", "STOPPED"]
    assert d.bars_processed == 2
