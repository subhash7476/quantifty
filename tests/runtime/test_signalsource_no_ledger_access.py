"""
MM.7C — C3: the SignalSource seam exposes no ledger / broker / handler (§5.4).

The driver injects only the bar (per on_bar) and an optional read-only context at
on_start — and in practice passes NOTHING to on_start (driver.py:522 calls
self._source.on_start() with no argument). A source therefore cannot read position
truth through the contract, which FORCES the shadow-state design for stateful
strategies (MM7B finding C2): a strategy tracks its OWN emitted intent, never the
platform ledger.

This pins the boundary mechanically (signature + source-text inspection + the
driver's empty on_start injection). ZERO production code changed.
"""
import inspect

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.runtime.event_journal import RuntimeEventJournal
from core.runtime.signal_source import SignalSource

from _doubles import (FakeClock, FakeMarketDataProvider, FakeSignalSource,
                      bar_series)

_SYM = "NSE_FO|53001"


# --------------------------------------------------------------------------- #
# The contract signatures carry no ledger/broker/handler — only bar + optional
# read-only context.
# --------------------------------------------------------------------------- #
def test_on_bar_signature_takes_only_bar():
    params = list(inspect.signature(SignalSource.on_bar).parameters)
    assert params == ["self", "bar"]


def test_on_start_signature_takes_only_optional_context():
    params = list(inspect.signature(SignalSource.on_start).parameters)
    assert params == ["self", "context"]


# --------------------------------------------------------------------------- #
# The seam module IMPORTS no execution/broker/ledger type — it binds only the
# bar/signal value objects (signal_source.py:29). The class docstring may name
# ExecutionHandler in prose (to explain the §5.4 prohibition); what matters is
# that no such type is actually imported/bound, so a source cannot hold one.
# --------------------------------------------------------------------------- #
def test_seam_module_imports_no_ledger_or_broker_or_handler():
    import core.runtime.signal_source as ss_mod
    forbidden = ["ExecutionHandler", "BrokerAdapter", "PositionTracker",
                 "OrderTracker", "ReconciliationEngine", "LoopDriver"]
    bound = [name for name in forbidden if hasattr(ss_mod, name)]
    assert bound == [], f"seam module imports a forbidden handle: {bound}"


# --------------------------------------------------------------------------- #
# The driver injects NOTHING into on_start — context is None — so even the one
# optional injection point exposes no ledger. (REPLAY so no handler is required;
# the on_start injection is mode-independent — driver.py:521-522.)
# --------------------------------------------------------------------------- #
def test_driver_passes_no_context_to_on_start(tmp_path):
    source = FakeSignalSource()
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=[_SYM], max_bars=2)
    d = LoopDriver(
        cfg, clock=FakeClock(),
        provider=FakeMarketDataProvider({_SYM: bar_series(_SYM, 3)}),
        journal=RuntimeEventJournal(path=str(tmp_path / "ev.jsonl")),
        source=source,
    )
    d.run()
    assert source.started == 1
    assert source.start_context is None     # the driver hands the source nothing
