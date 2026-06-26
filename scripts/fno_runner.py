"""
fno_runner — the first production composition root (MM7E, Design B / ADR-MM7E-1).

Constructs the four mechanical collaborators — LoopDriver, ExecutionHandler,
PaperBroker, and the market-data provider — and ACCEPTS a SignalSource by
dependency injection. It does NOT construct a SignalSource: per ADR-MM7E-1 the
first concrete source is a later strategy slice, so this root requires the *seam*
for a source, not a source. The driver itself already refuses missing
clock/provider/LIVE-handler inside run(); this root adds the SEMANTIC refusals it
owns (MM7E §4): a live run needs a source, a live F&O universe needs its master
readiness, and ExecutionMode.LIVE needs a real BrokerAdapter for order routing.

Target rung 1 — Mode.LIVE + ExecutionMode.PAPER: the entire startup gate,
restore-canonicalization, watchdog, and reconciliation exercised against the real
broker book while no capital moves (PaperBroker synthetic fills).

Target rung 2 — Mode.LIVE + ExecutionMode.LIVE: real broker order routing +
non-vacuous reconciliation. Requires an injected BrokerAdapter (UpstoxAdapter);
broker_positions is auto-constructed from the adapter via the token_rekey chain
(MM7J.3 + MM7K.1) unless overridden by the caller. Blocked on F&O product/margin
slices for derivatives; available immediately for equity intraday.

Wiring lives here, not in DriverConfig (config.py:9-13): every collaborator is
constructed from settings + injected seams, keeping the driver itself testable.
The optional clock/provider/db_manager/journal/metrics_path/max_bars parameters
default to the production construction and exist so the characterization net
can isolate the canonical store, the live provider, and the wall clock.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Sequence

from core.brokers.base import BrokerAdapter
from core.brokers.paper_broker import PaperBroker
from core.brokers.token_rekey import rekey_broker_positions_by_token
from core.clock import Clock, RealTimeClock
from core.database.manager import DatabaseManager
from core.database.providers.base import MarketDataProvider
from core.database.providers.live_market import LiveDuckDBMarketDataProvider
from core.execution.broker_positions_adapter import to_reconcile_positions
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.instruments.master_readiness import build_master_readiness
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.runtime.event_journal import RuntimeEventJournal
from core.runtime.instrument_scope import has_derivatives
from core.runtime.signal_source import SignalSource
from core.auth.credentials import credentials as _live_credentials

logger = logging.getLogger(__name__)


def _make_live_broker_positions(adapter: BrokerAdapter) -> Callable[[], List[Dict]]:
    """Build the broker_positions callable for the LIVE rung.

    Chains: adapter.get_positions() [MM7K.1 typed exceptions propagate]
         -> rekey_broker_positions_by_token() [MM7J.3 token-primary re-key]
         -> to_reconcile_positions() [MM7H shape adapter for reconcile engine].

    Positions with instrument_token=None are excluded from reconciliation and
    logged as warnings (UNRECONCILABLE_UNMAPPED_POSITION). Typed exceptions from
    get_positions() propagate to LoopDriver._reconcile_ledger (#6a / MM7F) which
    converts them to RECONCILIATION_FAIL -> STOPPED.
    """
    def _fetch() -> List[Dict]:
        rekeyed, unmappable = rekey_broker_positions_by_token(adapter.get_positions())
        if unmappable:
            logger.warning(
                "fno_runner: %d position(s) excluded from reconcile "
                "(instrument_token absent): %s",
                len(unmappable),
                [a.broker_value for a in unmappable],
            )
        return to_reconcile_positions(rekeyed)
    return _fetch


def build_runner(
    *,
    source: SignalSource,
    symbols: Sequence[str],
    underlyings: Optional[Sequence[str]] = None,
    execution_mode: ExecutionMode = ExecutionMode.PAPER,
    broker: Optional[BrokerAdapter] = None,
    broker_positions: Optional[Callable[[], List[Dict[str, Any]]]] = None,
    master_db_path: Optional[str] = None,
    clock: Optional[Clock] = None,
    provider: Optional[MarketDataProvider] = None,
    db_manager: Optional[DatabaseManager] = None,
    journal: Optional[RuntimeEventJournal] = None,
    metrics_path: Optional[str] = None,
    max_bars: Optional[int] = None,
    initial_capital: float = 100_000.0,
) -> LoopDriver:
    """Compose and return a live F&O LoopDriver around the injected source.

    Required production inputs are `source` (the DI seam), `symbols` (the traded
    universe), and — for an F&O universe — `underlyings` (the traded underlyings
    whose master coverage the gate asserts; not derivable from broker keys).

    For ExecutionMode.LIVE, `broker` must be supplied (an UpstoxAdapter or
    equivalent BrokerAdapter). `broker_positions` is then auto-constructed from
    the adapter via the token_rekey chain unless the caller overrides it.
    """
    # --- Semantic refusals at the composition root (MM7E §4 / ADR-MM7E-1) ----- #
    if source is None:
        raise ValueError(
            "fno_runner: a live run requires an injected SignalSource "
            "(ADR-MM7E-1: the root accepts the source, it does not construct one)"
        )

    # ExecutionMode.LIVE needs a real broker for order routing; PaperBroker
    # synthetic fills would silently produce a LIVE-flagged run with no real orders.
    if execution_mode is ExecutionMode.LIVE and broker is None:
        raise ValueError(
            "fno_runner: ExecutionMode.LIVE requires a real BrokerAdapter "
            "(inject an UpstoxAdapter); refusing to start without real order routing"
        )

    # MM8.3: refuse LIVE start when Upstox token is absent or expired — fail fast
    # before any collaborator is constructed (earlier diagnostics, no wasted work).
    if execution_mode is ExecutionMode.LIVE:
        if not _live_credentials.has_upstox_token or _live_credentials.is_token_expired:
            raise ValueError(
                "fno_runner: ExecutionMode.LIVE requires a valid, unexpired Upstox "
                "token; refresh the token before starting "
                "(CredentialManager.needs_daily_refresh is True)"
            )

    # A live F&O run with no checker is the W4 trap: a vacuous pass that also
    # disables G1 restore-canonicalization. The checker needs explicit underlyings
    # (broker keys can't derive them), so an F&O universe with no underlyings
    # cannot build one — refuse.
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

    # --- LIVE rung: auto-construct broker_positions from the token_rekey chain -- #
    # If the caller does not override broker_positions, build it from the injected
    # adapter. Typed exceptions from get_positions() propagate to the driver's
    # startup gate (MM7K.1 + MM7F #6a) — never swallowed here.
    if execution_mode is ExecutionMode.LIVE and broker_positions is None:
        broker_positions = _make_live_broker_positions(broker)

    # At PAPER a vacuous reconcile is acceptable, but the operator must KNOW the
    # gate has no teeth yet (warn > refuse — there is no real book to diverge).
    if execution_mode is ExecutionMode.PAPER and broker_positions is None:
        logger.warning(
            "fno_runner: reconciliation is vacuous (no broker_positions source) — "
            "the startup reconcile gate has no teeth at ExecutionMode.PAPER"
        )

    # --- Construct the four mechanical collaborators (Design B) --------------- #
    clock = clock if clock is not None else RealTimeClock()
    db_manager = db_manager if db_manager is not None else DatabaseManager()

    # LIVE rung: use the injected real broker for order routing.
    # PAPER rung: PaperBroker for synthetic fills (no capital).
    order_broker = broker if execution_mode is ExecutionMode.LIVE else PaperBroker(clock)

    provider = (provider if provider is not None
                else LiveDuckDBMarketDataProvider(list(symbols), db_manager))

    handler_kwargs: Dict[str, Any] = dict(
        db_manager=db_manager,
        clock=clock,
        broker=order_broker,
        config=ExecutionConfig(mode=execution_mode),
        load_db_state=True,  # recovery at construction (ADR-001); driver reuses it
        initial_capital=initial_capital,
    )
    if metrics_path is not None:
        handler_kwargs["metrics_path"] = metrics_path
    handler_kwargs["journal"] = journal
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
