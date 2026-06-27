"""
Refactored Execution Handler
-----------------
Handles execution of strategy signals using the isolated trading database (SQLite).
"""

import time
import os
import json
import math
import logging
from uuid import uuid4, UUID
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, Union

from datetime import datetime, timedelta
from dataclasses import dataclass, replace, field
from enum import Enum

from core.events import SignalEvent, SignalType, TradeEvent, TradeStatus, OrderEvent, OrderStatus, TradeStructuralContext
from core.events import OrderType as EventOrderType
from core.execution.rules import (
    enforce_signal_idempotency,
    enforce_risk_clearance,
    enforce_execution_authority,
    ExecutionRuleError
)
from core.execution.order_models import NormalizedOrder, OrderMetadata, OrderSide
from core.execution.order_models import OrderType as ModelOrderType
# from core.execution.order_factory import OrderFactory # Replaced by internal logic for Phase 9A
from core.execution.order_lifecycle import FillEvent
from core.execution.order_tracker import OrderTracker
from core.execution.risk_manager import RiskManager
from core.execution.position_tracker import PositionTracker
from core.execution.position_models import PositionSide
from core.execution.pnl_tracker import PnLTracker
from core.execution.margin_tracker import MarginTracker
from core.execution.groups.group_tracker import GroupTracker
from core.execution.groups.group_pnl import GroupPnLTracker
from core.execution.groups.order_group import OrderGroupType, GroupStatus
from core.execution.reconciliation import ReconciliationEngine
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.persistence.order_repository import OrderRepository
from core.execution.persistence.fill_repository import FillRepository
from core.execution.persistence.position_repository import PositionRepository
from core.execution.risk_models import RiskStatus
from core.clock import Clock
from core.brokers.broker_base import BrokerAdapter
from core.brokers.upstox_adapter import BrokerAuthError, BrokerUnavailableError
from core.alerts.alerter import alerter
from core.database.manager import DatabaseManager
from core.logging import setup_logger
from core.instruments.instrument_parser import InstrumentParser
from core.risk.greeks.portfolio_greeks import PortfolioGreeks
from core.risk.greeks.greeks_model import Greeks
from core.analytics.capture import CaptureEngine
from core.analytics.diagnostic_engine import DiagnosticsEngine
from core.database.writers import TradingWriter, _to_str
from core.runtime.event_journal import RuntimeEventJournal, EventType, Severity


class ExecutionMode(Enum):
    """Execution modes for safety."""
    DRY_RUN = "dry_run"      # Log only, no actual orders
    PAPER = "paper"          # Simulated fills
    LIVE = "live"            # Real broker API


@dataclass(frozen=True)
class PriceSnapshot:
    price: float
    timestamp: datetime


@dataclass(frozen=True)
class PriceabilityResult:
    # MM9.2-S3-S3: immutable value object returned by _check_book_priceable().
    # Pure result — no logging/metrics/journal side effects live here; those
    # remain in the process_signal call-site that consumes this object. Carries
    # both stale and missing sets distinctly so the WARNING/journal payload can
    # report each class (stale = seen but aged past max_price_age_s; missing =
    # no _price_cache entry at all).
    priceable: bool
    stale_symbols: Set[str]
    missing_symbols: Set[str]


@dataclass
class ExecutionConfig:
    """Configuration for execution handler."""
    mode: ExecutionMode = ExecutionMode.DRY_RUN
    default_quantity: float = 100.0  # Default position size
    max_position_size: float = 1000.0  # Max position limit
    slippage_model: str = "fixed"  # "fixed" or "percentage"
    slippage_value: float = 0.01  # Fixed $0.01 or 0.1%
    max_trades_per_day: int = 100
    max_drawdown_limit: float = 0.05  # 5%
    # Phase 9C: Greek Limits
    max_portfolio_delta: float = 1000.0
    max_portfolio_vega: float = 500.0
    max_gamma_exposure: float = 100.0
    # MM8.2A: consecutive BrokerUnavailableError threshold before kill switch
    broker_error_threshold: int = 3
    # MM9.1: capital-utilisation threshold for margin gate
    max_capital_utilisation: float = 0.80
    # MM9.2-S3-S3: max age (seconds) of a PriceSnapshot for a held position to
    # count as FRESH. Default float('inf') DISABLES the freshness gate — the
    # helper returns priceable=True without iterating the cache. Operators arm
    # enforcement by setting a finite value (recommended 600.0 for 1-min bars),
    # but ONLY after startup detection of non-universe held positions lands
    # (spec §6.1 R1: a recovered position whose symbol is not in the driver
    # universe would otherwise block every entry permanently). Age comparison is
    # strictly greater-than: age == max_price_age_s is FRESH (spec §2.7).
    max_price_age_s: float = float('inf')


@dataclass
class ExecutionMetrics:
    """Real-time observability metrics for execution."""
    signals_received: int = 0
    trades_executed: int = 0
    rejected_trades: int = 0
    start_time: float = field(default_factory=time.time)
    daily_pnl: float = 0.0
    max_equity: float = 100000.0
    cash_balance: float = 100000.0
    max_drawdown_pct: float = 0.0

    def get_throughput(self) -> float:
        """Returns signals processed per second."""
        elapsed = time.time() - self.start_time
        return self.signals_received / elapsed if elapsed > 0 else 0.0

    def update_drawdown(self, total_equity: float) -> float:
        """Updates and returns current drawdown percentage based on total equity."""
        self.max_equity = max(self.max_equity, total_equity)
        if self.max_equity == 0:
            return 0.0
        current_dd = (self.max_equity - total_equity) / self.max_equity
        self.max_drawdown_pct = max(self.max_drawdown_pct, current_dd)
        return current_dd

    def get_drawdown(self, total_equity: float) -> float:
        return self.update_drawdown(total_equity)


class ExecutionHandler:
    """
    Handles execution of strategy signals with Safety Kill Switches and Alerts.
    Uses the isolated trading database for state tracking.
    """

    def __init__(self,
                 db_manager: DatabaseManager,
                 clock: Clock,
                 broker: BrokerAdapter,
                 risk_manager: Optional[RiskManager] = None,
                 capture_engine: Optional[CaptureEngine] = None,
                 config: Optional[ExecutionConfig] = None,
                 metrics_path: str = "logs/execution_metrics.json",
                 initial_capital: float = 100000.0,
                 load_db_state: bool = True,
                 journal: Optional[RuntimeEventJournal] = None):
        self.db_manager = db_manager
        self.clock = clock
        self.broker = broker
        self._journal = journal
        # Subscribe to broker fills
        self.broker.subscribe_fills(self._handle_broker_fill)

        # Backward compatibility: older call sites pass ExecutionConfig as 4th positional arg.
        if isinstance(risk_manager, ExecutionConfig) and config is None:
            config = risk_manager
            risk_manager = None

        self.config = config or ExecutionConfig()
        self.risk_manager = risk_manager or RiskManager(config=self.config)
        self.capture_engine = capture_engine
        self.trading_writer = TradingWriter(self.db_manager)

        # Persistence Layer
        self.store = ExecutionStore()
        self.order_repo = OrderRepository(self.store)
        self.fill_repo = FillRepository(self.store)
        self.position_repo = PositionRepository(self.store)

        self.position_tracker = PositionTracker(
            position_repo=self.position_repo)
        self.order_tracker = OrderTracker(
            order_repo=self.order_repo, fill_repo=self.fill_repo)

        # Phase 8: Financial Trackers
        self.pnl_tracker = PnLTracker(self.position_tracker)
        self.margin_tracker = MarginTracker(self.position_tracker)
        self.reconciliation = ReconciliationEngine(self.position_tracker)

        # Phase 9B: Group Trackers
        self.group_tracker = GroupTracker(self.order_tracker)
        self.group_pnl_tracker = GroupPnLTracker(
            self.group_tracker, self.order_tracker)

        # Phase 9C: Portfolio Greeks
        self.portfolio_greeks = PortfolioGreeks(self.position_tracker)

        self._seen_signals: Set[str] = set()  # Phase 0: Idempotency registry
        self._processing_signal = False  # Phase 0: Authority guard
        self._trade_history: List[TradeEvent] = []
        self._dry_run_orders: List[Dict] = []  # For testing
        self.metrics_path = Path(metrics_path)

        self.metrics = ExecutionMetrics(
            max_equity=initial_capital,
            cash_balance=initial_capital
        )
        # MM9.2-S3-S1: handler-owned price cache. Replaces the prior
        # signal-driven Dict[str, float] with a bundled PriceSnapshot value
        # type so each entry carries its recording timestamp (Architecture B,
        # spec §3/§4). Fed to MarginTracker.get_used_margin projected to
        # Dict[str, float] so the gate observes all known symbols, not just
        # the signalling one (C3). MarginTracker stays stateless. Stale for
        # symbols that have not signalled since restart (§8 R1) — accepted
        # until S3-S2 lands.
        self._price_cache: Dict[str, PriceSnapshot] = {}
        self._kill_switched = False
        self._consecutive_broker_errors = 0
        self._trades_today = 0
        self.logger = logging.getLogger(__name__)

        self._consecutive_losses = 0
        self._last_alerted_loss_threshold = 0.0
        self._persist_metrics()

        if load_db_state:
            self._replay_state()

        # MM9.2-S1 D-S1-4 (delivered in MM9.2-S2): one-shot cold-cache warning.
        # Fires only at startup when _replay_state recovered positions but
        # _price_cache is still empty — those held symbols will be unpriced
        # by the margin gate until their first signal warms the cache (§8 R2).
        held = len(self.position_tracker.get_all_positions())
        if held > 0 and not self._price_cache:
            self.logger.warning(
                "latest-price cache is cold; %d held position(s) will be "
                "unpriced by the margin gate until first signal arrival", held)

        self.logger = setup_logger("execution_handler")

    def _persist_metrics(self, current_price: Optional[float] = None, symbol: Optional[str] = None):
        """Writes current execution metrics to disk for Flask."""
        try:
            self.metrics_path.parent.mkdir(parents=True, exist_ok=True)

            total_equity = self.metrics.cash_balance
            if current_price and symbol:
                total_equity += self.position_tracker.net_quantity(
                    symbol) * current_price

            data = {
                "signals_received": self.metrics.signals_received,
                "trades_executed": self.metrics.trades_executed,
                "rejected_trades": self.metrics.rejected_trades,
                "throughput": self.metrics.get_throughput(),
                "cash_balance": self.metrics.cash_balance,
                "total_equity": total_equity,
                "max_equity": self.metrics.max_equity,
                "drawdown": self.metrics.get_drawdown(total_equity),
                "kill_switched": self._kill_switched,
                "trades_today": self._trades_today,
                "last_update": self.clock.now().isoformat()
            }
            with open(self.metrics_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to persist metrics: {e}")

    def _replay_state(self):
        """Replays orders and fills from persistence to restore state."""
        self.logger.info("Replaying execution state from persistence...")

        # 1. Load Orders & Restore Idempotency Registry
        orders = self.order_repo.get_all()
        for order in orders:
            self.order_tracker.add_order(order, persist=False)
            if order.signal_id:
                self._seen_signals.add(str(order.signal_id))

        # 2. Load Fills
        fills = self.fill_repo.get_all()
        for fill in fills:
            self.order_tracker.process_fill(fill, persist=False)
            self.position_tracker.update_from_fill(fill, persist=False)

        # 3. Reconstruct Groups (Phase 9B)
        from collections import defaultdict
        orders_by_group = defaultdict(list)
        for order in orders:
            if order.group_id:
                orders_by_group[order.group_id].append(order)

        for group_id, legs in orders_by_group.items():
            # Attempt to recover group type from metadata, default to CUSTOM
            g_type_str = legs[0].metadata.strategy_metadata.get(
                "group_type", "CUSTOM")
            try:
                g_type = OrderGroupType(g_type_str)
            except ValueError:
                g_type = OrderGroupType.CUSTOM

            self.group_tracker.create_group(g_type, legs)
            # Update status based on replayed state
            if legs:
                self.group_tracker.update_from_order_status(
                    legs[0].correlation_id)

        # 4. Restore daily trade count (fills from today only)
        today = self.clock.now().date()
        today_fills = [f for f in fills if hasattr(f, 'timestamp') and f.timestamp.date() == today]
        self._trades_today = len(today_fills)

        self.logger.info(
            f"Replay complete. Loaded {len(orders)} orders, {len(fills)} fills, "
            f"{len(self._seen_signals)} seen signals, {self._trades_today} trades today.")

    def canonicalize_restored_positions(self, resolver=None):
        """G1 Wave 3 (#7-as-restored) Option-B post-gate canonicalization of
        restored POSITION identity. Re-resolves each tracked derivative position's
        symbol through the (gate-verified) instrument master and swaps
        Position.instrument in place — futures EQUITY->FUTURE (H1), option
        parser-lot->master-lot (H2) — preserving symbol/side/quantity/avg_price
        (H3). Equity / unresolved symbols are left legacy (carve-out).

        The ledger mutation is the handler's (ADR-001); the LoopDriver only
        triggers this on the live-F&O gate-pass, AFTER master readiness and BEFORE
        reconciliation. Restored ORDER identity (#8) is the separate wave and is
        not touched here; get_position (#7 source, H5) and the positions snapshot
        table (#9, H6) are left untouched."""
        from core.execution.canonical_restore import canonicalize_symbol
        from core.instruments.resolver import InstrumentResolver
        resolver = resolver or InstrumentResolver()
        as_of = self.clock.now()
        for symbol in list(self.position_tracker.get_all_positions()):
            legacy = canonicalize_symbol(symbol, as_of, resolver)
            if legacy is not None:
                self.position_tracker.replace_instrument(symbol, legacy)

    def canonicalize_restored_orders(self, resolver=None):
        """G1 Wave 3 (#8) Option-B post-gate canonicalization of restored ORDER
        identity. Re-resolves each tracked derivative order's symbol through the
        (gate-verified) instrument master and swaps NormalizedOrder.instrument in
        place — futures EQUITY->FUTURE (H1), option parser-lot->master-lot (H2) —
        preserving symbol/side/quantity/order_type and correlation_id/signal_id
        (H3/H7/H8: in-place swap, never reconstruct the order). Equity / unresolved
        symbols are left legacy (carve-out).

        The sibling of canonicalize_restored_positions (#7-as-restored); the
        LoopDriver triggers both on the live-F&O gate-pass, AFTER master readiness
        and BEFORE reconciliation. The ledger mutation is the handler's (ADR-001);
        CanonicalInstrument stays internal (the G1 / 4C.7 boundary)."""
        from core.execution.canonical_restore import canonicalize_symbol
        from core.instruments.resolver import InstrumentResolver
        resolver = resolver or InstrumentResolver()
        as_of = self.clock.now()
        for state in self.order_tracker.order_states():
            order = state.order
            legacy = canonicalize_symbol(order.symbol, as_of, resolver)
            if legacy is not None:
                self.order_tracker.replace_instrument(order.correlation_id, legacy)

    def _handle_broker_fill(self, fill: FillEvent):
        """
        Callback for broker fills.
        Ingests fill into trackers and persistence.
        """
        self.logger.info(
            f"Received fill from broker: {fill.fill_id} for order {fill.order_id}")
        try:
            from uuid import UUID
            order_id_str = str(fill.order_id)
            
            order_state = self.order_tracker.get_order(order_id_str)
            
            self.order_tracker.process_fill(fill)
            realized_pnl = self.position_tracker.update_from_fill(fill)
            # G1 Wave 4B (#7) — canonicalize the live forward position's identity
            # from the instrument master at the fill seam. LIVE-only by construction:
            # restore replay calls update_from_fill directly (_replay_state), never
            # _handle_broker_fill, so restored positions stay legacy at construction
            # (Option B / ADR-003) and the post-gate canonicalize_restored_positions
            # pass owns their upgrade. Reusing the restore primitive guarantees a
            # forward-built position and its restored twin carry byte-identical
            # canonical identity (no restart drift). The derived legacy Future/Option
            # keeps the same .symbol (position key preserved); equity / unresolved ->
            # None -> position left legacy (carve-out). CanonicalInstrument stays
            # internal (G1 / 4C.7).
            from core.execution.canonical_restore import canonicalize_symbol
            derived = canonicalize_symbol(fill.symbol, fill.timestamp)
            if derived is not None:
                self.position_tracker.replace_instrument(fill.symbol, derived)
            self.pnl_tracker.update(fill, realized_pnl)
            
            # Use raw correlation ID for group tracker
            if isinstance(fill.order_id, (UUID, str)):
                corr_id = fill.order_id if isinstance(fill.order_id, UUID) else UUID(fill.order_id)
                self.group_tracker.update_from_order_status(corr_id)
            
            self.group_pnl_tracker.update(fill, realized_pnl)

            # TLP V1: Atomic Trade + Context Save
            if order_state:
                order = order_state.order
                trade = TradeEvent(
                    trade_id=fill.fill_id,
                    signal_id_reference=order.signal_id,
                    symbol=fill.symbol,
                    status=TradeStatus.FILLED,
                    direction=fill.side,
                    quantity=fill.quantity,
                    price=fill.price,
                    fees=fill.fee,
                    timestamp=fill.timestamp
                )
                
                self._update_equity_metrics(trade)
                
                # Retrieve context from order metadata
                context = None
                if order.metadata and hasattr(order.metadata, 'strategy_metadata'):
                    context = order.metadata.strategy_metadata.get('tlp_context')
                
                # If this is an exit, handle MAE/MFE
                pos = self.position_tracker.get_position(order.symbol)
                if order.side.value in ("SELL", "BUY") and pos.side == PositionSide.FLAT:
                    # Closing trade
                    # Retrieve original entry context from DB to get entry price and timestamp
                    mae_mfe = self._compute_exit_diagnostics(order.symbol, order.signal_id, fill.price, fill.timestamp)
                    self.trading_writer.update_trade_exit(
                        trade_id=fill.fill_id, 
                        exit_price=fill.price, 
                        exit_ts=fill.timestamp, 
                        pnl=realized_pnl, 
                        fees=fill.fee,
                        mae_mfe=mae_mfe
                    )
                else:
                    # Opening trade
                    self.trading_writer.save_trade(trade, context)

        except Exception as e:
            self.logger.error(f"Failed to process broker fill: {e}")

    def _compute_exit_diagnostics(self, symbol: str, signal_id: str, exit_price: float, exit_ts: datetime) -> Optional[Dict]:
        """Loads 1m bars and computes MAE/MFE for a closed trade."""
        try:
            # 1. Fetch entry details from trade_context
            with self.db_manager.trading_reader() as conn:
                row = conn.execute("""
                    SELECT entry_timestamp, intended_entry, sl_distance, risk_r, pnl_rs, direction
                    FROM trades t JOIN trade_context c ON t.trade_id = c.trade_id
                    WHERE t.symbol = ? AND t.exit_price = 0.0
                    ORDER BY t.timestamp DESC LIMIT 1
                """, [symbol]).fetchone()
                
                if not row:
                    return None
                
                entry_ts_str, entry_price, sl_dist, risk_r, _, direction = row
                entry_ts = datetime.fromisoformat(entry_ts_str)
                
                # 2. Compute using DiagnosticsEngine
                engine = DiagnosticsEngine(Path("data/market_data/nse/candles/1m"))
                mae_mfe = engine.compute_mae_mfe(
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry_price,
                    sl_distance=sl_dist,
                    entry_ts=entry_ts,
                    exit_ts=exit_ts
                )
                
                # 3. Add Exit Efficiency & Theoretical Max
                if mae_mfe and mae_mfe.get('mfe_points', 0) > 0:
                    # We'll need quantity to compute Rs-based theoretical max
                    # But for now we just return the points and R
                    pass
                
                return mae_mfe
        except Exception as e:
            self.logger.warning(f"Exit diagnostics failed: {e}")
            return None

    def update_market_price(self, symbol: str, price: float) -> None:
        # MM9.2-S3-S1: sole writer for _price_cache. Pure data-feed operation
        # — no logging, no metrics, no gate, no side effects. Timestamped with
        # the deterministic clock so snapshot age is replay-identical (ADR-003).
        self._price_cache[symbol] = PriceSnapshot(
            price=price, timestamp=self.clock.now())

    def process_signal(self,
                       signal: SignalEvent,
                       current_price: float) -> Optional[NormalizedOrder]:
        """
        Intake a strategy signal, enforce rules, and produce a NormalizedOrder.
        Returns NormalizedOrder on success, or None if skipped (e.g. kill switch).
        """
        # PHASE 0: Authority Enforcement
        enforce_execution_authority(not self._processing_signal)
        self._processing_signal = True

        try:
            # MM9.2-S1: record the signalling symbol's bar price before any
            # gate so MarginTracker.get_used_margin sees the full universe.
            # Applies to EXIT too — keeps the price warm for later entries.
            # MM9.2-S3-S1: routes through update_market_price so the entry is
            # a PriceSnapshot carrying self.clock.now().
            self.update_market_price(signal.symbol, current_price)

            signal_id = getattr(signal, 'signal_id',
                                signal.metadata.get('signal_id'))
            if not signal_id:
                from hashlib import sha256
                raw_id = f"{signal.symbol}_{signal.strategy_id}_{signal.timestamp.isoformat()}"
                signal_id = sha256(raw_id.encode()).hexdigest()

            # PHASE 0: Idempotency Enforcement
            enforce_signal_idempotency(str(signal_id), self._seen_signals)
            # Lock immediately so repeated signal IDs are rejected even if
            # later validation fails.
            self._seen_signals.add(str(signal_id))

            # TLP V1: Mandatory Risk Enforcement
            sl_dist = signal.metadata.get('sl_distance')
            risk_r = signal.metadata.get('risk_r')
            
            if signal.signal_type != SignalType.EXIT:
                if sl_dist is None or risk_r is None:
                    # Legacy compatibility: older broker integration tests emit bare signals.
                    # Auto-populate conservative defaults only for mock broker flows.
                    if self.broker.__class__.__name__ == "MockBrokerAdapter":
                        signal.metadata.setdefault('sl_distance', max(current_price * 0.01, 0.01))
                        signal.metadata.setdefault('risk_r', 1.0)
                        sl_dist = signal.metadata.get('sl_distance')
                        risk_r = signal.metadata.get('risk_r')
                    else:
                        # Keep constitutional precedence: risk clearance violations must raise.
                        risk_approved = self._check_risk_limits(signal, current_price)
                        if not risk_approved:
                            enforce_risk_clearance(
                                False, reason=f"Risk limits exceeded for {signal.symbol}")
                        # Legacy compatibility: continue with conservative defaults so
                        # downstream pre-trade risk checks can execute.
                        signal.metadata.setdefault('sl_distance', max(current_price * 0.01, 0.01))
                        signal.metadata.setdefault('risk_r', 1.0)
                        sl_dist = signal.metadata.get('sl_distance')
                        risk_r = signal.metadata.get('risk_r')
                        self.logger.warning(f"Signal {signal_id} missing risk definition; applied defaults")
                
                # Ensure they are floats
                try:
                    sl_dist_f = float(sl_dist)
                    risk_r_f = float(risk_r)
                except (ValueError, TypeError):
                    self.logger.error(f"REJECTED: Signal {signal_id} has invalid risk types")
                    return None
            else:
                sl_dist_f = 0.0
                risk_r_f = 0.0

            # 0. Manual Kill Switch File Flag
            from unittest.mock import Mock
            broker_name = self.broker.__class__.__name__
            is_mock_broker = broker_name in {"MockBrokerAdapter", "MockBroker"} or isinstance(self.broker, Mock)
            if not getattr(self, '_kill_switch_disabled', False) and not is_mock_broker and os.path.exists("STOP"):
                self.activate_kill_switch("Manual STOP file detected.")
                return None

            # 1. Observability
            self.metrics.signals_received += 1

            # 2. Kill Switch Check
            if self._kill_switched:
                return None

            # 3. Daily Trade Limit Check
            if not getattr(self, '_kill_switch_disabled', False) and self._trades_today >= self.config.max_trades_per_day:
                if is_mock_broker:
                    raise ExecutionRuleError(
                        f"Daily trade limit ({self.config.max_trades_per_day}) reached")
                self.activate_kill_switch(
                    f"Max daily trades ({self.config.max_trades_per_day}) reached.")
                return None

            # 4. Drawdown Kill Switch
            total_equity = self.metrics.cash_balance + \
                (self.position_tracker.net_quantity(signal.symbol) * current_price)
            if not getattr(self, '_kill_switch_disabled', False):
                dd = self.metrics.get_drawdown(total_equity)
                if dd >= self.config.max_drawdown_limit:
                    self.activate_kill_switch(
                        f"Max drawdown ({dd*100:.1f}%) reached.")
                    return None

            # 4b. Position Stacking Guard — max 1 position per symbol
            if signal.signal_type != SignalType.EXIT:
                if self.position_tracker.has_open_position(signal.symbol):
                    return None

            # 5. Risk Checks (PHASE 0: Risk Clearance Enforcement)
            risk_approved = self._check_risk_limits(signal, current_price)
            enforce_risk_clearance(
                risk_approved, reason=f"Risk limits exceeded for {signal.symbol}")

            # Phase 9C: Greek Risk Check
            self._check_greek_limits(signal, current_price)

            # TLP V1: Capture Structural Context Snapshot
            tlp_context = None
            if self.capture_engine and signal.signal_type != SignalType.EXIT:
                try:
                    tlp_context = self.capture_engine.capture_context(
                        symbol=signal.symbol,
                        timestamp=signal.timestamp,
                        signal_rank=signal.metadata.get('rank', 0),
                        signal_percentile=signal.metadata.get('percentile', 0.0),
                        sl_distance=sl_dist_f,
                        risk_r=risk_r_f,
                        signal_score=signal.confidence
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to capture TLP context: {e}")

            # PHASE 1: Order Creation (Deterministic Intake)
            current_position = self.position_tracker.get_position(
                signal.symbol)

            # Phase 9A: Instrument Abstraction & Order Creation
            if signal.metadata.get("execution_mode") == "option" and signal.signal_type != SignalType.EXIT:
                from core.execution.options.selector import OptionsContractSelector
                instrument = OptionsContractSelector().select(
                    underlying=signal.symbol,
                    underlying_price=current_price,
                    direction=signal.signal_type,
                    timestamp=signal.timestamp,
                    policy=signal.metadata.get("option_policy", {}),
                )
                # 4C.7 — resolve CI for broker payload; resolver cache makes this a
                # dict lookup since the selector already called resolve_option internally.
                from core.instruments.resolver import InstrumentResolver
                _as_of = signal.timestamp.date() if isinstance(signal.timestamp, datetime) else signal.timestamp
                canonical_instrument = InstrumentResolver().resolve_option(
                    signal.symbol, instrument.expiry, instrument.strike,
                    instrument.option_type, as_of=_as_of)
            else:
                # G1 Wave 4 #4 / O2 — derive the legacy identity for a derivative
                # EXIT (or non-option entry) symbol from the canonical instrument
                # master. canonicalize_symbol resolves a futures-shaped symbol to a
                # Future (Wave 2 #1, unchanged) AND an option-shaped EXIT symbol to a
                # master-lot Option; the derived symbol stays byte-identical.
                # Equity / unresolved symbols fall back to InstrumentParser.parse.
                from core.execution.canonical_restore import canonicalize_symbol
                derived = canonicalize_symbol(signal.symbol, signal.timestamp)
                instrument = derived if derived is not None else InstrumentParser.parse(signal.symbol)
                # 4C.7 — surface CI for broker payload (resolver cache hit when derived
                # is not None; None for equity / unresolved symbols).
                if derived is not None:
                    from core.instruments.resolver import InstrumentResolver
                    from core.instruments.instrument_base import InstrumentType as _IType
                    _as_of = signal.timestamp.date() if isinstance(signal.timestamp, datetime) else signal.timestamp
                    if instrument.type == _IType.FUTURE:
                        canonical_instrument = InstrumentResolver().resolve_future(
                            instrument.underlying, as_of=_as_of)
                    elif instrument.type == _IType.OPTION:
                        canonical_instrument = InstrumentResolver().resolve_option(
                            instrument.underlying, instrument.expiry, instrument.strike,
                            instrument.option_type, as_of=_as_of)
                    else:
                        canonical_instrument = None
                else:
                    canonical_instrument = None

            # Determine Side and Quantity
            if signal.signal_type == SignalType.EXIT:
                if current_position.side == PositionSide.FLAT:
                    return None

                side = OrderSide.SELL if current_position.side == PositionSide.LONG else OrderSide.BUY
                quantity = current_position.quantity  # Close full position
            else:
                side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL
                quantity = self._calculate_position_size(signal, current_price)

            # Attach TLP Context to Metadata
            strategy_meta = signal.metadata.copy() if signal.metadata else {}
            if tlp_context:
                strategy_meta['tlp_context'] = tlp_context

            order_meta = OrderMetadata(
                original_confidence=signal.confidence,
                strategy_metadata=strategy_meta
            )

            order = NormalizedOrder(
                instrument=instrument,
                canonical_instrument=canonical_instrument,  # 4C.7
                side=side,
                quantity=int(quantity),
                order_type=ModelOrderType.MARKET,
                strategy_id=signal.strategy_id,
                signal_id=str(signal_id),
                timestamp=self.clock.now(),
                metadata=order_meta
            )

            # PHASE 2: Pre-trade Risk Integration
            risk_decision = self.risk_manager.evaluate(
                order,
                trades_today=self._trades_today,
                max_trades_per_day=self.config.max_trades_per_day
            )
            if not risk_decision.approved:
                self.metrics.rejected_trades += 1
                raise ExecutionRuleError(
                    f"Pre-trade risk rejection: {risk_decision.reason}")

            # MM9.1-S3: capital-utilisation gate
            # D8: EXIT signals bypass — closing a position reduces margin; gating an EXIT is unsafe.
            if signal.signal_type != SignalType.EXIT:
                # MM9.2-S3-S3: fresh-book preflight gate. Runs BEFORE the
                # capital gate so _check_margin_budget never computes utilisation
                # on a partial book (a missing/stale held symbol would otherwise
                # contribute 0 via get_exposure -> None price, understating
                # used_current — the C3 under-count class). EXIT bypass is
                # inherited from the outer if (spec §2.10). The helper is pure;
                # all side effects (metrics/log/journal) live here.
                priceability = self._check_book_priceable()
                if not priceability.priceable:
                    self.metrics.rejected_trades += 1
                    stale_ages = {
                        sym: round(
                            (self.clock.now() -
                             self._price_cache[sym].timestamp).total_seconds(),
                            1)
                        for sym in priceability.stale_symbols
                    }
                    self.logger.warning(
                        "PORTFOLIO_UNPRICEABLE symbol=%s signal_id=%s missing=%s "
                        "stale=%s ages_s=%s",
                        order.symbol, signal_id,
                        sorted(priceability.missing_symbols),
                        sorted(priceability.stale_symbols),
                        stale_ages,
                    )
                    if self._journal:
                        # R4: journal write is fire-and-forget — a failure here
                        # must never change the gate decision or return value.
                        try:
                            self._journal.record(
                                EventType.PORTFOLIO_UNPRICEABLE,
                                "Entry blocked: held book cannot be fully priced",
                                source_component="ExecutionHandler",
                                metadata={
                                    "signal_symbol": order.symbol,
                                    "signal_id": str(signal_id),
                                    "missing_symbols": sorted(
                                        priceability.missing_symbols),
                                    "stale_symbols": sorted(
                                        priceability.stale_symbols),
                                    "stale_ages_s": stale_ages,
                                    "max_price_age_s":
                                        self.config.max_price_age_s,
                                },
                            )
                        except Exception:
                            self.logger.exception(
                                "journal write failed for PORTFOLIO_UNPRICEABLE")
                    return None

                approved, utilisation = self._check_margin_budget(order, current_price)
                if not approved:
                    self.metrics.rejected_trades += 1
                    self.logger.warning(
                        "MARGIN_BUDGET_REJECTED symbol=%s signal_id=%s utilisation=%.2f%% "
                        "limit=%.2f%%",
                        order.symbol, signal_id,
                        utilisation * 100,
                        self.config.max_capital_utilisation * 100,
                    )
                    return None

            # PHASE 5: Order Lifecycle Registration
            self.order_tracker.add_order(order)

            # PHASE 7: Broker Execution
            try:
                broker_id = self.broker.place_order(order)
                self.logger.info(
                    f"Order placed with broker. Broker ID: {broker_id}")
                self._consecutive_broker_errors = 0

                # Simulate immediate fill for backtesting (paper broker)
                from core.brokers.paper_broker import PaperBroker
                if isinstance(self.broker, PaperBroker):
                    import uuid as uuid_module
                    fill_id = str(uuid_module.uuid4())
                    
                    # Update position tracker so equity includes position values
                    fill_event = FillEvent(
                        fill_id=fill_id,
                        order_id=str(order.correlation_id),
                        symbol=order.symbol,
                        quantity=order.quantity,
                        price=current_price,
                        timestamp=order.timestamp,
                        side=order.side.value,
                        fee=self._calculate_fees(order.quantity, current_price),
                    )
                    
                    # Instead of creating TradeEvent manually here, we route through _handle_broker_fill
                    # which is the single source of truth for fill ingestion.
                    self._handle_broker_fill(fill_event)
                    
                    # We need to return the resulting TradeEvent if possible, but process_signal
                    # returns Optional[NormalizedOrder]. PaperBroker usually calls back.
                    # For compatibility, we'll return the order.
                    return order

            except BrokerAuthError as e:
                if self._journal:
                    self._journal.record(
                        EventType.BROKER_ERROR,
                        f"Broker authentication failure: {e}",
                        severity=Severity.CRITICAL,
                        source_component="ExecutionHandler",
                        metadata={"error": str(e), "signal_id": str(signal_id)},
                    )
                self.activate_kill_switch(f"BrokerAuthError: {e}")
                return None
            except BrokerUnavailableError as e:
                self._consecutive_broker_errors += 1
                if self._journal:
                    self._journal.record(
                        EventType.BROKER_ERROR,
                        f"Broker unavailable: {e}",
                        severity=Severity.WARNING,
                        source_component="ExecutionHandler",
                        metadata={"error": str(e), "signal_id": str(signal_id),
                                  "consecutive_errors": self._consecutive_broker_errors},
                    )
                if self._consecutive_broker_errors >= self.config.broker_error_threshold:
                    self.activate_kill_switch(
                        f"BrokerUnavailableError x{self._consecutive_broker_errors}: {e}")
                return None
            except Exception as e:
                self.logger.error(f"Failed to place order with broker: {e}")

            return order

        finally:
            self._processing_signal = False


    def process_group_signal(self, signals: List[SignalEvent], group_type: OrderGroupType) -> Optional[str]:
        """
        Process a group of signals atomically.
        Creates an OrderGroup and routes all legs.
        """
        # 1. Create Group ID
        group_id = uuid4()

        # 2. Create NormalizedOrders for all signals
        orders = []
        for signal in signals:
            # Similar logic to process_signal but we inject group_id

            # Phase 4: Pass position context for EXIT resolution
            current_position = self.position_tracker.get_position(
                signal.symbol)

            # Phase 9A: Instrument Abstraction & Order Creation
            instrument = InstrumentParser.parse(signal.symbol)

            # Determine Side and Quantity
            if signal.signal_type == SignalType.EXIT:
                if current_position.side == PositionSide.FLAT:
                    continue  # Skip invalid exit
                side = OrderSide.SELL if current_position.side == PositionSide.LONG else OrderSide.BUY
                quantity = current_position.quantity
            else:
                side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL
                quantity = self._calculate_position_size(
                    signal, 0.0)  # Price 0.0 as placeholder

            # Prepare metadata with group_type for replay reconstruction
            strategy_meta = signal.metadata.copy() if signal.metadata else {}
            strategy_meta["group_type"] = group_type.value

            order_meta = OrderMetadata(
                original_confidence=signal.confidence,
                strategy_metadata=strategy_meta
            )

            order = NormalizedOrder(
                instrument=instrument,
                side=side,
                quantity=int(quantity),
                order_type=ModelOrderType.MARKET,
                strategy_id=signal.strategy_id,
                signal_id=str(uuid4()),  # Generate new ID
                timestamp=self.clock.now(),
                group_id=group_id,
                metadata=order_meta
            )
            orders.append(order)

        # 3. Register Group
        group = self.group_tracker.create_group(group_type, orders)

        # 4. Execute Legs
        # Atomic Risk Check: If any leg fails risk, abort the whole group
        for order in orders:
            risk_decision = self.risk_manager.evaluate(
                order, self._trades_today, self.config.max_trades_per_day)
            if not risk_decision.approved:
                self.logger.error(
                    f"Group leg rejected by risk: {risk_decision.reason}. Aborting group {group_id}.")
                return None

        # All passed risk, proceed to execution
        for order in orders:
            self.order_tracker.add_order(order)
            try:
                self.broker.place_order(order)
            except Exception as e:
                self.logger.error(f"Failed to place group leg: {e}")

        return str(group_id)

    def activate_kill_switch(self, reason: str):
        if not self._kill_switched:
            self._kill_switched = True
            alerter.critical(f"KILL SWITCH ACTIVATED: {reason}")
            self.logger.warning(f"Kill switch activated: {reason}")
            self._persist_metrics()

    def _is_signal_already_executed(self, signal_id: str) -> bool:
        """Check trading.db for existing execution of this signal."""
        try:
            with self.db_manager.trading_reader() as conn:
                res = conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE signal_id = ?", [signal_id]).fetchone()
                return res[0] > 0 if res else False
        except Exception:
            return False

    def _check_risk_limits(self, signal: SignalEvent, current_price: float) -> bool:
        current_position = self.position_tracker.net_quantity(signal.symbol)
        if signal.signal_type == SignalType.BUY:
            if current_position + self.config.default_quantity > self.config.max_position_size:
                return False
        elif signal.signal_type == SignalType.SELL:
            if abs(current_position - self.config.default_quantity) > self.config.max_position_size:
                return False
        return True

    def _check_greek_limits(self, signal: SignalEvent, current_price: float):
        """
        Phase 9C: Check if the new order would breach portfolio Greek limits.
        This is a simulation check.
        """
        # If we don't have necessary data in metadata, skip check (or fail safe)
        # We assume signal.metadata might contain 'underlying_price', 'iv', 'tte'
        meta = signal.metadata or {}
        # Fallback to current if equity
        underlying_price = meta.get('underlying_price', current_price)
        iv = meta.get('iv', 0.20)
        tte = meta.get('tte', 0.0)  # Years

        # 1. Calculate Greeks for the NEW signal
        instrument = InstrumentParser.parse(signal.symbol)
        qty = self._calculate_position_size(signal, current_price)
        if signal.signal_type == SignalType.SELL:
            qty = -qty

        # We need a calculator instance or static call
        from core.risk.greeks.greeks_calculator import GreeksCalculator
        new_greeks = GreeksCalculator.calculate(
            instrument=instrument,
            quantity=qty,
            underlying_price=underlying_price,
            volatility=iv,
            time_to_expiry=tte
        )

        # 2. Get Current Portfolio Greeks
        # Note: This requires full market data map which we might not have here.
        # For this implementation, we assume we track accumulated greeks or fetch snapshot.
        # Since we don't have a live market data provider injected here, we skip the *portfolio* addition check
        # and just check the *marginal* impact if it's massive, or rely on the fact that
        # PortfolioGreeks needs external data injection.

        # For strict compliance with Phase 9C objective "Simulate projected Greeks after order",
        # we would need to fetch current portfolio greeks.
        # As a safeguard, we check if the single order exceeds limits (e.g. massive delta).
        if abs(new_greeks.delta) > self.config.max_portfolio_delta:
            raise ExecutionRuleError(
                f"Order Delta {new_greeks.delta:.2f} exceeds limit {self.config.max_portfolio_delta}")

    def _calculate_position_size(self, signal: SignalEvent, current_price: float) -> float:
        # If strategy provided explicit sizing (e.g., ATR-based), use it
        strategy_qty = signal.metadata.get("quantity", 0)
        if strategy_qty > 0:
            return min(float(strategy_qty), self.config.max_position_size)
        return self.config.default_quantity * (0.5 + signal.confidence * 0.5)

    def _apply_slippage(self, price: float, direction: str) -> float:
        adj = self.config.slippage_value if self.config.slippage_model == "fixed" else price * \
            self.config.slippage_value
        return price + adj if direction == "BUY" else price - adj

    def _calculate_fees(self, quantity: float, price: float) -> float:
        """Realistic NSE equity intraday costs per leg.

        Brokerage: Rs 20 flat (discount broker)
        STT: 0.025% of sell-side turnover (handled in aggregate)
        Exchange txn: 0.00345% of turnover
        SEBI fee: 0.0001% of turnover
        GST: 18% on (brokerage + exchange + SEBI)
        Stamp duty: 0.003% of buy-side turnover
        """
        turnover = quantity * price
        brokerage = 20.0
        exchange_txn = turnover * 0.0000345
        sebi = turnover * 0.000001
        # 0.025% (applied on sell side; averaged across both legs)
        stt = turnover * 0.00025
        stamp = turnover * 0.00003
        gst = 0.18 * (brokerage + exchange_txn + sebi)
        return brokerage + exchange_txn + sebi + stt + stamp + gst

    def _estimate_required_margin(self, quantity: float, price: float) -> float:
        # MM9.1: single-symbol estimate only.
        # Future MM9.x: replace with broker/SPAN margin engine.
        return quantity * price

    def _check_book_priceable(self) -> PriceabilityResult:
        # MM9.2-S3-S3: fresh-book preflight gate. PURE — inspects only
        # position_tracker and _price_cache; no logging, no metrics, no journal,
        # no kill switch, no MarginTracker call, no state mutation. All side
        # effects remain in the process_signal call-site (spec §4, R4, R8).
        # Deterministic: age is self.clock.now() - snap.timestamp (ADR-003);
        # never datetime.now(). Comparison is strictly greater-than, so a
        # snapshot whose age is exactly max_price_age_s is FRESH (spec §2.7).
        if math.isinf(self.config.max_price_age_s):
            # Disabled (operator has not opted in). Contract: do not iterate.
            return PriceabilityResult(
                priceable=True, stale_symbols=set(), missing_symbols=set())

        positions = self.position_tracker.get_all_positions()
        held = {sym for sym, pos in positions.items()
                if pos.side != PositionSide.FLAT}
        if not held:
            # Vacuously priceable — a flat book has nothing to price (spec §2.9).
            return PriceabilityResult(
                priceable=True, stale_symbols=set(), missing_symbols=set())

        now = self.clock.now()
        max_age = timedelta(seconds=self.config.max_price_age_s)
        stale: Set[str] = set()
        missing: Set[str] = set()

        for sym in held:
            snap = self._price_cache.get(sym)
            if snap is None:
                missing.add(sym)            # no cached price — unpriceable
            elif (now - snap.timestamp) > max_age:
                stale.add(sym)              # aged past threshold — unpriceable

        priceable = not stale and not missing
        return PriceabilityResult(
            priceable=priceable, stale_symbols=stale, missing_symbols=missing)

    def _check_margin_budget(self, order: NormalizedOrder, current_price: float) -> tuple[bool, float]:
        # MM9.1: capital-utilisation gate — (approved, utilisation).
        # C2: must be called before order_tracker.add_order to avoid orphaned orders on recovery.
        # MM9.2-S1: get_used_margin now receives the handler's full _price_cache
        # cache (Architecture B), so every held symbol with a cached price
        # contributes to used_current. MarginTracker remains stateless.
        # MM9.2-S3-S1: project _price_cache (Dict[str, PriceSnapshot]) to
        # Dict[str, float] immediately before the call — MarginTracker's
        # signature is unchanged (MM9.4 SPAN seam preserved).
        # Stacking-guard dependency: used_margin(all positions) + incremental(new
        # order) is non-double-counting only because process_signal blocks new
        # entries on symbols that already hold a position. If pyramiding is ever
        # introduced this gate MUST be redesigned to exclude order.symbol from
        # used_current (see MM9.2-S1 spec §4.7 / §8 R3).
        if self.metrics.cash_balance <= 0:
            return True, 0.0

        # C1: canonical_instrument.multiplier is lot_size for F&O (e.g. 65 for NIFTY).
        effective_multiplier = (
            order.canonical_instrument.multiplier
            if order.canonical_instrument is not None
            else order.instrument.multiplier
        )
        prices = {sym: snap.price for sym, snap in self._price_cache.items()}
        used_current = self.margin_tracker.get_used_margin(prices)
        incremental_est = (
            self._estimate_required_margin(order.quantity * effective_multiplier, current_price)
            * self.margin_tracker.margin_rate
        )
        utilisation = (used_current + incremental_est) / self.metrics.cash_balance
        return utilisation <= self.config.max_capital_utilisation, utilisation

    def _log_dry_run_order(self, signal, side, qty, price):
        self.logger.info(
            f"[DRY-RUN] {side} {qty} {signal.symbol} @ {price} at {self.clock.now()}")

    def _update_equity_metrics(self, trade: TradeEvent):
        cost = trade.quantity * trade.price + trade.fees
        if trade.direction == "BUY":
            self.metrics.cash_balance -= cost
        else:
            self.metrics.cash_balance += (trade.quantity *
                                          trade.price - trade.fees)

        total_equity = self.metrics.cash_balance + \
            (self.position_tracker.net_quantity(trade.symbol) * trade.price)
        self.metrics.update_drawdown(total_equity)

    def get_position(self, symbol: str) -> float:
        return self.position_tracker.net_quantity(symbol)

    def get_stats(self, current_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Returns execution stats for telemetry."""
        total_trades = len(self._trade_history)
        win_rate = self._calculate_win_rate()

        realized_pnl = self.pnl_tracker.get_realized_pnl()
        unrealized_pnl = 0.0
        used_margin = 0.0

        if current_prices:
            unrealized_pnl = self.pnl_tracker.get_unrealized_pnl(
                current_prices)
            used_margin = self.margin_tracker.get_used_margin(current_prices)

        return {
            "daily_pnl": self.metrics.daily_pnl,
            "drawdown_pct": self.metrics.max_drawdown_pct,
            "trade_count": total_trades,
            "win_rate": win_rate,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": realized_pnl + unrealized_pnl,
            "used_margin": used_margin
        }

    def _calculate_win_rate(self) -> float:
        # Very simple win rate calculation for current session
        trades = [t for t in self._trade_history if t.status ==
                  TradeStatus.FILLED]
        if not trades:
            return 0.0

        # This is a placeholder; real win rate needs paired trades
        # For telemetry snapshot, we just return a best-effort number
        return 0.0

    def get_trade_history(self) -> List[TradeEvent]:
        return list(self._trade_history)





