"""
MM.7C — C5: multi-leg signal ordering is preserved; the driver does not re-rank.

A structured options strategy (e.g. an iron-fly) emits SEVERAL legs from one bar.
The seam contract is that the returned list order IS the routing order
(signal_source.py:39-44) — the driver forwards each to process_signal in list
order and never re-ranks (driver.py:_dispatch_signals). MM7D can therefore rely on
leg order (e.g. sell-before-buy-the-wings) being honored end-to-end.

Pinned with a FakeSignalSource scripted to return a 4-leg list on one bar and a
FakeExecutionHandler that records routing order. ZERO production code changed.
"""
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.events import SignalEvent, SignalType

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, bar_series)

_SYM = "NSE_FO|53001"


def _leg(symbol, signal_type):
    return SignalEvent(strategy_id="ironfly", symbol=symbol, timestamp=None,
                       signal_type=signal_type, confidence=1.0,
                       metadata={"signal_id": symbol})


def _run(legs):
    handler = FakeExecutionHandler(reconcile_alerts=[])
    # The whole multi-leg structure is emitted on the first bar; later bars empty.
    source = FakeSignalSource(signals_per_bar=[legs])
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=[_SYM], max_bars=3)
    d = LoopDriver(cfg, clock=FakeClock(),
                   provider=FakeMarketDataProvider({_SYM: bar_series(_SYM, 3)}),
                   execution=handler, source=source)
    d.run()
    return handler.routed


# --------------------------------------------------------------------------- #
# A 4-leg structure is routed in the exact list order the source returned.
# --------------------------------------------------------------------------- #
def test_multileg_routing_order_is_preserved():
    legs = [
        _leg("NIFTY_CE_SELL", SignalType.SELL),   # short call
        _leg("NIFTY_PE_SELL", SignalType.SELL),   # short put
        _leg("NIFTY_CE_BUY", SignalType.BUY),     # long call wing
        _leg("NIFTY_PE_BUY", SignalType.BUY),     # long put wing
    ]
    routed = _run(legs)
    routed_symbols = [s.symbol for s, _ in routed]
    assert routed_symbols == [leg.symbol for leg in legs]   # order preserved, not re-ranked


# --------------------------------------------------------------------------- #
# The driver does not reorder by side/type — a BUY emitted before a SELL stays
# first.
# --------------------------------------------------------------------------- #
def test_driver_does_not_rerank_by_side():
    legs = [_leg("FIRST_BUY", SignalType.BUY), _leg("SECOND_SELL", SignalType.SELL)]
    routed = _run(legs)
    assert [s.symbol for s, _ in routed] == ["FIRST_BUY", "SECOND_SELL"]
