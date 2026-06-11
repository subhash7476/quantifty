"""
fno_runner — the first production composition root (MM7E, Design B / ADR-MM7E-1).

Constructs the four mechanical collaborators — LoopDriver, ExecutionHandler,
PaperBroker, and the market-data provider — and ACCEPTS a SignalSource by
dependency injection. It does NOT construct a SignalSource: per ADR-MM7E-1 the
first concrete source is a later strategy slice, so this root requires the *seam*
for a source, not a source. The driver itself already refuses missing
clock/provider/LIVE-handler inside run(); this root adds the SEMANTIC refusals it
owns (MM7E §4): a live run needs a source, a live F&O universe needs its master
readiness, and ExecutionMode.LIVE needs a broker-positions reconciliation source.

Target runtime: Mode.LIVE + ExecutionMode.PAPER — the entire startup gate,
restore-canonicalization, watchdog, and reconciliation exercised against the real
broker book while no capital moves (PaperBroker synthetic fills). ExecutionMode.
LIVE is out of MM7E scope (gated on F4 + the F&O product/margin slices).

Wiring lives here, not in DriverConfig (config.py:9-13): every collaborator is
constructed from settings + injected seams, keeping the driver itself testable.
The optional clock/provider/db_manager/journal/metrics_path/max_bars parameters
default to the production construction and exist so the MM7E characterization net
can isolate the canonical store, the live provider, and the wall clock — the same
dependency-injection the driver uses.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Sequence

from core.brokers.paper_broker import PaperBroker
from core.clock import Clock, RealTimeClock
from core.database.manager import DatabaseManager
from core.database.providers.base import MarketDataProvider
from core.database.providers.live_market import LiveDuckDBMarketDataProvider
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.instruments.master_readiness import build_master_readiness
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.runtime.event_journal import RuntimeEventJournal
from core.runtime.instrument_scope import has_derivatives
from core.runtime.signal_source import SignalSource

logger = logging.getLogger(__name__)


def build_runner(
    *,
    source: SignalSource,
    symbols: Sequence[str],
    underlyings: Optional[Sequence[str]] = None,
    execution_mode: ExecutionMode = ExecutionMode.PAPER,
    broker_positions: Optional[Callable[[], List[Dict[str, Any]]]] = None,
    master_db_path: Optional[str] = None,
    clock: Optional[Clock] = None,
    provider: Optional[MarketDataProvider] = None,
    db_manager: Optional[DatabaseManager] = None,
    journal: Optional[RuntimeEventJournal] = None,
    metrics_path: Optional[str] = None,
    max_bars: Optional[int] = None,
) -> LoopDriver:
    """Compose and return a live-paper F&O LoopDriver around the injected source.

    Required production inputs are `source` (the DI seam), `symbols` (the traded
    universe), and — for an F&O universe — `underlyings` (the traded underlyings
    whose master coverage the gate asserts; not derivable from broker keys).
    """
    # --- Semantic refusals at the composition root (MM7E §4 / ADR-MM7E-1) ----- #
    # A live trading runtime with no signal origin is a silent no-op — the most
    # dangerous failure mode (looks healthy, does nothing). Refuse here, NOT in
    # run() (that would break the legitimate inert replay path). This is the T1
    # acceptance predicate's `source present` clause.
    if source is None:
        raise ValueError(
            "fno_runner: a live run requires an injected SignalSource "
            "(ADR-MM7E-1: the root accepts the source, it does not construct one)"
        )

    # Starting ExecutionMode.LIVE without reconciling the real broker book is
    # unsafe (#6's territory; MM7E names it). PAPER's vacuous reconcile is fine.
    if execution_mode is ExecutionMode.LIVE and broker_positions is None:
        raise ValueError(
            "fno_runner: ExecutionMode.LIVE requires a broker_positions "
            "reconciliation source (deferred to #6); refusing to start"
        )

    # A live F&O run with no checker is the W4 trap: a vacuous master-readiness
    # pass that ALSO silently disables G1 restore-canonicalization. The checker
    # needs explicit underlyings (broker keys can't derive them), so an F&O
    # universe with no underlyings cannot build one — refuse.
    derivatives = has_derivatives(symbols)
    master_readiness: Optional[Callable[[], Any]] = None
    if derivatives:
        if not underlyings:
            raise ValueError(
                "fno_runner: a live F&O universe requires underlyings for master "
                "readiness (MM7E §4 / W4); refusing to start"
            )
        master_readiness = build_master_readiness(
            list(underlyings), db_path=master_db_path
        )

    # At PAPER a vacuous reconcile is acceptable, but the operator must KNOW the
    # gate has no teeth yet (warn > refuse — there is no real book to diverge).
    if execution_mode is ExecutionMode.PAPER and broker_positions is None:
        logger.warning(
            "fno_runner: reconciliation is vacuous (no broker_positions source) — "
            "the startup reconcile gate has no teeth at ExecutionMode.PAPER"
        )

    # --- Construct the four mechanical collaborators (Design B) --------------- #
    # One shared clock flows to broker + handler + driver (single time source).
    clock = clock if clock is not None else RealTimeClock()
    db_manager = db_manager if db_manager is not None else DatabaseManager()
    broker = PaperBroker(clock)
    provider = (provider if provider is not None
                else LiveDuckDBMarketDataProvider(list(symbols), db_manager))

    handler_kwargs: Dict[str, Any] = dict(
        db_manager=db_manager,
        clock=clock,
        broker=broker,
        config=ExecutionConfig(mode=execution_mode),
        load_db_state=True,  # recovery at construction (ADR-001); driver reuses it
    )
    if metrics_path is not None:
        handler_kwargs["metrics_path"] = metrics_path
    execution = ExecutionHandler(**handler_kwargs)

    config = DriverConfig(mode=Mode.LIVE, symbols=list(symbols), max_bars=max_bars)

    return LoopDriver(
        config,
        clock=clock,
        provider=provider,
        journal=journal,
        source=source,
        execution=execution,
        broker_positions=broker_positions,
        master_readiness=master_readiness,
    )
