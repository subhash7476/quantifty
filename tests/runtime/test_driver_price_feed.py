"""
MM9.2-S3-S2 — Per-Bar Price Feed Hook (driver -> handler wiring).

Validates DRIVER_SPECIFICATION.md §8 (price-feed coupling) and
MM9_2_S3_IMPLEMENTATION_SPEC_V2.md §9 (S3-S2): `LoopDriver._tick()` calls
`execution.update_market_price(symbol, bar.close)` on EVERY bar, after the
deterministic clock is advanced (`set_time`) and BEFORE `source.on_bar`. This
is the first slice that makes the handler's price cache bar-driven rather
than signal-driven — a held symbol that never signals still gets priced every
bar (eliminates stale-price scenario S2). No freshness gate exists yet.

Coverage (spec §9 S3-S2 Definition of Done):
  * cache updated for a symbol even when on_bar returns no signals
  * cache updated for ALL symbols each bar (not only the signaling one)
  * call placed after set_time (snapshot timestamp == bar timestamp)
  * call placed before on_bar (price warm precedes signal routing)
  * price == bar.close, deterministically, in bar order
  * no-handler (replay/inert/test) path unaffected by the guard
  * end-to-end: a REAL ExecutionHandler's _price_cache is warmed by the loop
"""

from datetime import datetime

import pytz

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.brokers.paper_broker import PaperBroker
from core.execution.handler import ExecutionConfig, ExecutionHandler
from core.execution.persistence.execution_store import ExecutionStore
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, make_bar, make_signal)

_T0 = datetime(2026, 6, 5, 9, 15, 0, tzinfo=pytz.UTC)
_T1 = datetime(2026, 6, 5, 9, 16, 0, tzinfo=pytz.UTC)


def _replay_cfg(symbols, max_bars=None):
    return DriverConfig(mode=Mode.REPLAY, symbols=list(symbols), max_bars=max_bars)


class _PriceFeedSpy(FakeExecutionHandler):
    """FakeExecutionHandler that also captures the deterministic clock's now()
    at each update_market_price call — proves the driver advances the clock
    (set_time) BEFORE warming the cache (spec §9 S3-S2: timestamp == bar ts)."""

    def __init__(self, clock):
        super().__init__()
        self._clock = clock
        self.captured_clock_now = []

    def update_market_price(self, symbol, price):
        self.captured_clock_now.append(self._clock.now())
        super().update_market_price(symbol, price)


class _ProbingSource(FakeSignalSource):
    """FakeSignalSource that records how many prices had been cached by the
    time on_bar runs — proves update_market_price fires BEFORE on_bar."""

    def __init__(self, handler, signals_per_bar=None):
        super().__init__(signals_per_bar)
        self._handler = handler
        self.price_count_at_on_bar = []

    def on_bar(self, bar):
        self.price_count_at_on_bar.append(len(self._handler.price_updates))
        return super().on_bar(bar)


def _build_real_handler(tmp_path, monkeypatch, clock):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
    )


# --------------------------------------------------------------------------- #
# cache warmed for a symbol that produces NO signals (the core S3-S2 win)
# --------------------------------------------------------------------------- #
def test_cache_warmed_for_non_signaling_symbol():
    handler = FakeExecutionHandler()
    source = FakeSignalSource()  # on_bar returns [] — no signals ever
    d = LoopDriver(_replay_cfg(("B",), max_bars=1), clock=FakeClock(),
                   provider=FakeMarketDataProvider(
                       {"B": [make_bar("B", ts=_T0, close=42.0)]}),
                   source=source, execution=handler)
    d.run()
    # Despite no signal firing, the bar's price reached the handler.
    assert handler.price_updates == [("B", 42.0)]
    assert handler.routed == []  # nothing routed (no signals)


# --------------------------------------------------------------------------- #
# cache warmed for ALL symbols each bar, not only the signaling one
# --------------------------------------------------------------------------- #
def test_cache_warmed_for_all_symbols_each_bar():
    handler = FakeExecutionHandler()
    # Symbol A fires a signal; symbol B is silent. One bar each.
    sig_a = make_signal("A")
    source = FakeSignalSource([[sig_a]])  # only the first on_bar returns a signal
    d = LoopDriver(_replay_cfg(("A", "B"), max_bars=2), clock=FakeClock(),
                   provider=FakeMarketDataProvider({
                       "A": [make_bar("A", ts=_T0, close=100.0)],
                       "B": [make_bar("B", ts=_T0, close=200.0)],
                   }),
                   source=source, execution=handler)
    d.run()
    # Both symbols warmed in config-list (symbol-sweep) order.
    assert handler.price_updates == [("A", 100.0), ("B", 200.0)]
    # Only A produced a signal.
    assert [s for (s, _) in handler.routed] == [sig_a]


# --------------------------------------------------------------------------- #
# call placed AFTER set_time: snapshot timestamp == bar timestamp (via clock)
# --------------------------------------------------------------------------- #
def test_update_market_price_called_after_set_time():
    clock = FakeClock()
    handler = _PriceFeedSpy(clock)
    d = LoopDriver(_replay_cfg(("A",), max_bars=1), clock=clock,
                   provider=FakeMarketDataProvider(
                       {"A": [make_bar("A", ts=_T0, close=99.0)]}),
                   source=FakeSignalSource(), execution=handler)
    d.run()
    # At the moment update_market_price ran, the clock had already been
    # advanced to the bar's timestamp — so the snapshot will carry bar ts.
    assert handler.captured_clock_now == [_T0]
    assert handler.price_updates == [("A", 99.0)]


# --------------------------------------------------------------------------- #
# call placed BEFORE on_bar: price warm precedes signal routing
# --------------------------------------------------------------------------- #
def test_update_market_price_called_before_on_bar():
    handler = FakeExecutionHandler()
    sig = make_signal("A")
    source = _ProbingSource(handler, [[sig]])
    d = LoopDriver(_replay_cfg(("A",), max_bars=1), clock=FakeClock(),
                   provider=FakeMarketDataProvider(
                       {"A": [make_bar("A", ts=_T0, close=77.0)]}),
                   source=source, execution=handler)
    d.run()
    # By the time on_bar ran for this bar, the price was already cached.
    assert source.price_count_at_on_bar == [1]
    assert handler.price_updates == [("A", 77.0)]
    assert handler.routed == [(sig, 77.0)]


# --------------------------------------------------------------------------- #
# price == bar.close, deterministically, in bar order
# --------------------------------------------------------------------------- #
def test_price_feed_records_bar_close_in_order():
    handler = FakeExecutionHandler()
    d = LoopDriver(_replay_cfg(("A",), max_bars=None), clock=FakeClock(),
                   provider=FakeMarketDataProvider({
                       "A": [make_bar("A", ts=_T0, close=100.0),
                             make_bar("A", ts=_T1, close=200.0)],
                   }),
                   source=FakeSignalSource(), execution=handler)
    d.run()
    assert handler.price_updates == [("A", 100.0), ("A", 200.0)]


# --------------------------------------------------------------------------- #
# no-handler (replay/inert/test) path is unaffected by the guard
# --------------------------------------------------------------------------- #
def test_no_handler_path_unaffected_by_price_feed_guard():
    source = FakeSignalSource()
    d = LoopDriver(_replay_cfg(("A",), max_bars=1), clock=FakeClock(),
                   provider=FakeMarketDataProvider(
                       {"A": [make_bar("A", ts=_T0, close=10.0)]}),
                   source=source, execution=None)
    d.run()  # must not raise — the price-feed call is guarded on handler presence
    assert len(source.bars_seen) == 1  # Phase D signal-pull preserved


# --------------------------------------------------------------------------- #
# end-to-end: a REAL ExecutionHandler's _price_cache is warmed by the loop
# --------------------------------------------------------------------------- #
def test_real_handler_price_cache_warmed_by_loop(tmp_path, monkeypatch):
    clock = ReplayClock(_T0)
    handler = _build_real_handler(tmp_path, monkeypatch, clock)
    # Same clock instance is shared by driver and handler (production wiring):
    # the driver's set_time(bar.ts) is what the handler's clock.now() returns.
    bar = make_bar("NSE_EQ|AAA", ts=_T1, close=234.5)
    d = LoopDriver(_replay_cfg(("NSE_EQ|AAA",), max_bars=1), clock=clock,
                   provider=FakeMarketDataProvider({"NSE_EQ|AAA": [bar]}),
                   source=FakeSignalSource(), execution=handler)
    d.run()
    snap = handler._price_cache["NSE_EQ|AAA"]
    assert snap.price == 234.5            # == bar.close
    assert snap.timestamp == _T1          # == bar.timestamp (via clock.now())
