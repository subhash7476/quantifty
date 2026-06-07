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
from core.events import OHLCVBar, SignalEvent, SignalType
from core.execution.position_tracker import PositionTracker
from core.runtime.signal_source import SignalSource

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


def make_signal(symbol: str = "A", signal_type: SignalType = SignalType.BUY,
                ts: Optional[datetime] = None) -> SignalEvent:
    return SignalEvent(strategy_id="test", symbol=symbol, timestamp=ts or _T0,
                       signal_type=signal_type, confidence=1.0)


class FakeSignalSource(SignalSource):
    """
    Scripts the signals returned per on_bar call and records the full lifecycle
    so the driver's seam wiring can be asserted:

    - bars_seen: every bar passed to on_bar, in call order.
    - started / start_context / bars_at_start: how often on_start fired, the
      context it received, and how many bars had been seen when it ran (0 proves
      on_start runs before the loop pulls any bar).
    - stopped: how often on_stop fired.

    on_bar returns the i-th scripted signal list for the i-th call; once the
    script is exhausted it returns [] (the normal do-nothing bar). Lists are
    returned verbatim (no copy-reorder) so order/identity assertions hold.
    """

    def __init__(self, signals_per_bar: Optional[List[List[SignalEvent]]] = None):
        self._script = list(signals_per_bar or [])
        self.bars_seen: List[OHLCVBar] = []
        self.started = 0
        self.start_context = "UNSET"
        self.bars_at_start: Optional[int] = None
        self.stopped = 0

    def on_start(self, context=None) -> None:
        self.started += 1
        self.start_context = context
        self.bars_at_start = len(self.bars_seen)

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        i = len(self.bars_seen)
        self.bars_seen.append(bar)
        return self._script[i] if i < len(self._script) else []

    def on_stop(self) -> None:
        self.stopped += 1


class FakeWatchdog:
    """
    Duck-typed RuntimeWatchdog stand-in (NOT a subclass — the real watchdog
    requires an ExecutionHandler in its constructor, which the driver tests must
    never build). Records the driver's calls so the wiring can be asserted, and
    lets a test script a staleness trip without wall-clock / market-hours games.

    record_bar()            — counted; a fresh bar clears staleness (recovery).
    check_data_staleness()  — counted; on the stale_after-th call it flips
                              data_healthy False, simulating a >5-min feed gap
                              that trips the kill switch (the real watchdog's
                              activate_kill_switch side effect lives on its own
                              ExecutionHandler, not here).
    write_heartbeat(bars)   — records each bars_processed value it was given.
    data_healthy            — the public health flag the driver edge-detects.
    """

    def __init__(self, stale_after: Optional[int] = None):
        self.record_bar_calls = 0
        self.staleness_checks = 0
        self.heartbeats: List[int] = []
        self._stale_after = stale_after
        self.data_healthy = True

    def record_bar(self) -> None:
        self.record_bar_calls += 1
        self.data_healthy = True

    def check_data_staleness(self) -> None:
        self.staleness_checks += 1
        if self._stale_after is not None and self.staleness_checks == self._stale_after:
            self.data_healthy = False

    def write_heartbeat(self, bars_processed: int = 0) -> None:
        self.heartbeats.append(bars_processed)


class FakeReconciliation:
    """
    Duck-typed ReconciliationEngine stand-in. reconcile() returns the scripted
    alert list regardless of the broker positions it is handed (an empty list
    means consistent; a non-empty list is a startup-gate failure), and records
    each call's argument so the gate's call/no-call behavior is assertable.
    """

    def __init__(self, alerts: Optional[List] = None):
        self._alerts = list(alerts or [])
        self.reconcile_calls: List = []

    def reconcile(self, broker_positions) -> List:
        self.reconcile_calls.append(broker_positions)
        return list(self._alerts)


class FakeExecutionHandler:
    """
    Duck-typed ExecutionHandler stand-in for the startup gate + execution routing
    (NOT a subclass — the real handler builds a broker, trackers, and
    persistence). It carries:

    - reconciliation: a FakeReconciliation with scriptable alerts;
    - _replay_state(): a spy that records calls so a test can assert the driver
      NEVER re-restores state (ADR-001 — recovery happened at construction);
    - process_signal(signal, current_price): the canonical execution entry point
      (Phase G routing target, §8.1). A recording spy: it appends each
      (signal, current_price) pair to `routed` in call order so a test can assert
      WHAT was routed, in WHICH order, at WHICH price (always bar.close). It is
      otherwise inert — it submits no order, touches no ledger, and returns None,
      keeping the slice narrow (the driver routes; it does not execute).
    - position_tracker: a REAL PositionTracker (the ledger's position truth) so
      Phase H.3 position publishing reads a real get_all_positions() snapshot; a
      test populates it directly via `position_tracker._positions[...]`.
    """

    def __init__(self, reconcile_alerts: Optional[List] = None,
                 raise_on: Optional[str] = None):
        self.reconciliation = FakeReconciliation(reconcile_alerts)
        self.replay_state_calls = 0
        self.routed: List = []
        self.position_tracker = PositionTracker()
        # process_signal raises for a signal whose symbol == raise_on (§8.4
        # per-signal exception isolation testing); None = never raises.
        self._raise_on = raise_on
        # The handler's own kill-switch flag (IN-001 single-source observation).
        # A test flips it to simulate a handler-caused trip (drawdown / broker /
        # daily-limit); the real handler owns this attribute (§10.7).
        self._kill_switched = False

    def _replay_state(self) -> None:
        self.replay_state_calls += 1

    def process_signal(self, signal, current_price):
        if self._raise_on is not None and signal.symbol == self._raise_on:
            raise RuntimeError(f"process_signal boom on {signal.symbol}")
        self.routed.append((signal, current_price))
        return None


class FakeTelemetryTransport:
    """
    Duck-typed stand-in for the ZMQ wire transport (core/messaging/telemetry.py
    TelemetryPublisher) — NO real socket, so unit tests carry no network
    dependency. Records every published payload and close() call so the bridge
    wiring is assertable; with fail=True it raises to prove publishing is
    best-effort (a transport fault must never stop trading).

    publish_metrics(data)   — records the payload, or raises if fail.
    publish_positions(data) — records the payload, or raises if fail.
    publish_log(level, msg) — records the (level, message) pair, or raises if fail.
    close()                 — counts closes, or raises if fail.
    """

    def __init__(self, fail: bool = False, fail_on_close: bool = False):
        self.published: List[Dict] = []
        self.published_health: List[Dict] = []
        self.published_positions: List[Dict] = []
        self.published_logs: List[tuple] = []
        self.closed = 0
        self._fail = fail
        self._fail_on_close = fail_on_close

    def publish_metrics(self, data: Dict) -> None:
        if self._fail:
            raise RuntimeError("ZMQ transport down")
        self.published.append(data)

    def publish_health(self, data: Dict) -> None:
        if self._fail:
            raise RuntimeError("ZMQ transport down")
        self.published_health.append(data)

    def publish_positions(self, data: Dict) -> None:
        if self._fail:
            raise RuntimeError("ZMQ transport down")
        self.published_positions.append(data)

    def publish_log(self, level: str, message: str) -> None:
        if self._fail:
            raise RuntimeError("ZMQ transport down")
        self.published_logs.append((level, message))

    def close(self) -> None:
        if self._fail_on_close:
            raise RuntimeError("transport close failed")
        self.closed += 1
