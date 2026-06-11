"""
MM.7C — C4: SignalSource determinism / replay==live parity (MM7B finding C3).

A source's decisions must be a pure function of the inputs it sees — the bar (and
any chain it reads), keyed by bar.timestamp — with NO wall-clock dependency. Then
the same (bar, timestamp) sequence yields the same signals whether the run is live
or a replay; paper and live differ only downstream in the handler's fill mode.

This pins determinism with a characterization source (a pure bar→signal mapping —
NOT a strategy): identical input sequences routed through two independent drivers
produce identical signal streams, and each emitted signal carries bar.timestamp
(time comes from the bar, not the clock-of-the-day). The replay/live data-parity
obligation for the OPTION CHAIN (a source-owned OptionsProvider) is documented in
MM7C_SIGNALSOURCE_CHARACTERIZATION.md §C4 — it is a data-layer requirement, not a
seam-logic one. ZERO production code changed.
"""
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.runtime.signal_source import SignalSource
from core.events import SignalEvent, SignalType

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      bar_series)

_SYM = "NSE_FO|53001"


class _DeterministicSource(SignalSource):
    """Pure bar→signal mapping: BUY when close is above a threshold, else nothing.
    Reads ONLY the bar — no wall-clock, no external state. (A characterization
    double, not a strategy.)"""

    def __init__(self, threshold: float):
        self._threshold = threshold

    def on_bar(self, bar):
        if bar.close > self._threshold:
            return [SignalEvent(strategy_id="det", symbol=bar.symbol,
                                timestamp=bar.timestamp, signal_type=SignalType.BUY,
                                confidence=1.0, metadata={})]
        return []


def _run(threshold, closes):
    bars = [b for b in bar_series(_SYM, len(closes))]
    bars = [b.__class__(symbol=b.symbol, timestamp=b.timestamp, open=c, high=c,
                        low=c, close=c, volume=0.0) for b, c in zip(bars, closes)]
    handler = FakeExecutionHandler(reconcile_alerts=[])
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=[_SYM], max_bars=len(closes))
    d = LoopDriver(cfg, clock=FakeClock(),
                   provider=FakeMarketDataProvider({_SYM: bars}),
                   execution=handler, source=_DeterministicSource(threshold))
    d.run()
    return handler.routed, bars


# --------------------------------------------------------------------------- #
# Identical (bar sequence, timestamps) → identical routed signal stream.
# --------------------------------------------------------------------------- #
def test_identical_inputs_yield_identical_signals():
    routed_a, _ = _run(100.0, [99.0, 101.0, 102.0])
    routed_b, _ = _run(100.0, [99.0, 101.0, 102.0])

    def shape(routed):
        return [(s.symbol, s.signal_type, s.timestamp, price) for s, price in routed]

    assert shape(routed_a) == shape(routed_b)
    # Two of the three bars cleared the threshold.
    assert len(routed_a) == 2


# --------------------------------------------------------------------------- #
# Time comes from the bar: every emitted signal carries bar.timestamp (no
# wall-clock-of-the-day), and current_price is bar.close.
# --------------------------------------------------------------------------- #
def test_signals_are_keyed_to_bar_time_not_wall_clock():
    routed, bars = _run(100.0, [101.0, 102.0])
    emitted_ts = [s.timestamp for s, _ in routed]
    assert emitted_ts == [bars[0].timestamp, bars[1].timestamp]
    # current_price paired at routing is bar.close (ADR-003 deterministic pricing).
    assert [price for _, price in routed] == [101.0, 102.0]
