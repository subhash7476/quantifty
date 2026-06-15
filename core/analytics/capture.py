"""
Capture Engine
--------------
Snapshots market structural state at signal generation time.
Universal capture service for Trade Learning Protocol V1.
"""
from datetime import datetime, time
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import pandas as pd

from core.database.manager import DatabaseManager
from core.analytics.metrics_service import StructuralMetricsService
from core.events import TradeStructuralContext

logger = logging.getLogger(__name__)

class CaptureEngine:
    def __init__(self, db_manager: DatabaseManager, metrics_service: StructuralMetricsService):
        self.db = db_manager
        self.metrics = metrics_service
        self._nifty_universe = []
        self._load_universe()

    def _load_universe(self):
        """Load the fixed Nifty universe version 1."""
        csv_path = Path("data/nifty-50-stock-list.csv")
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                self._nifty_universe = df['Symbol'].tolist()
            except Exception as e:
                logger.error(f"Failed to load Nifty universe CSV: {e}")

    def capture_context(self, 
                        symbol: str, 
                        timestamp: datetime, 
                        signal_rank: int, 
                        signal_percentile: float,
                        sl_distance: float, 
                        risk_r: float,
                        signal_score: float = 0.0) -> TradeStructuralContext:
        """
        Snapshots the structural truth at this specific timestamp.
        """
        # 1. HMM Regime from previous session EOD
        regime, confidence = self._get_previous_regime(timestamp)
        
        # 2. Session Type
        session_type = "AM" if timestamp.time() < time(12, 30) else "PM"
        
        # 3. Breadth (Adv/Dec)
        breadth = self._calculate_breadth(timestamp)
        
        # 4. Dispersion & Volatility (Percentiles)
        csad, atr = self._get_current_metrics(timestamp)
        pctls = self.metrics.get_percentiles(csad, atr, timestamp.date())
        
        # 5. Index Trend (Return from open to now)
        index_trend = self._get_index_trend(timestamp)

        return TradeStructuralContext(
            regime_state=regime,
            regime_confidence=confidence,
            session_type=session_type,
            index_trend=index_trend,
            dispersion_value=csad,
            dispersion_pct=pctls["dispersion_pct"],
            volatility_value=atr,
            volatility_pct=pctls["volatility_pct"],
            breadth_ratio=breadth,
            signal_rank=signal_rank,
            signal_score=signal_score,
            signal_percentile=signal_percentile,
            sl_distance=sl_distance,
            risk_r=risk_r,
            model_version="TLP_V1_CORE",
            universe_version="NIFTY_UNIVERSE_V1"
        )

    def _get_previous_regime(self, ts: datetime) -> Tuple[str, float]:
        """Fetches the finalized HMM state from the last trading day."""
        try:
            with self.db.signals_reader() as conn:
                row = conn.execute("""
                    SELECT regime, persistence_score 
                    FROM regime_insights 
                    WHERE timestamp < ? 
                    ORDER BY timestamp DESC LIMIT 1
                """, [ts.date().isoformat()]).fetchone()
                if row:
                    return str(row[0]), float(row[1])
        except Exception:
            pass
        return "UNKNOWN", 0.0

    def _calculate_breadth(self, ts: datetime) -> float:
        """Approximates breadth by comparing current prices to open."""
        # For V1, we return neutral if real-time scanning is not implemented in runner
        return 0.5

    def _get_current_metrics(self, ts: datetime) -> Tuple[float, float]:
        """Approximates CSAD and ATR for percentile snapshot."""
        # Pull latest available metrics from signals.db
        try:
            with self.db.signals_reader() as conn:
                row = conn.execute("""
                    SELECT dispersion_csad, volatility_atr 
                    FROM daily_structural_metrics 
                    WHERE timestamp <= ? 
                    ORDER BY timestamp DESC LIMIT 1
                """, [ts.date().isoformat()]).fetchone()
                if row:
                    return float(row[0]), float(row[1])
        except Exception:
            pass
        return 0.0, 0.0

    def _get_index_trend(self, ts: datetime) -> str:
        """Placeholder for index trend logic."""
        return "NEUTRAL"


# ── Unified TLP Logger ─────────────────────────────────────────────────────────

TLP_TRADE_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS tlp_trade_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy        TEXT    NOT NULL,
    session_date    TEXT    NOT NULL,
    regime          TEXT,
    confidence      REAL,
    vix             REAL,
    structure       TEXT,
    session_type    TEXT,
    entry_time      TEXT,
    entry_price     REAL,
    exit_time       TEXT,
    exit_reason     TEXT,
    mae_rs          REAL,
    mfe_rs          REAL,
    pnl_net_rs      REAL,
    exit_efficiency REAL,
    hold_bars       INTEGER,
    tlp_version     TEXT    DEFAULT 'TLP_V1_CORE',
    created_at      TEXT    DEFAULT CURRENT_TIMESTAMP
);
"""

_tlp_logger = None  # module-level singleton, set by init_tlp_logger()


def init_tlp_logger(db_manager):
    """Call once at startup (e.g. from unified_runner.py) to initialise the singleton."""
    global _tlp_logger
    _tlp_logger = TLPLogger(db_manager)
    return _tlp_logger


def get_tlp_logger():
    return _tlp_logger


class TLPLogger:
    """
    Unified trade outcome logger for TLP V1.

    Works across all strategy consumers.
    Each strategy calls .record() once at trade close.

    Stored in tlp_trade_log (trading.db).
    Queried by scripts/perform_structural_review.py.
    """

    def __init__(self, db_manager):
        self.db = db_manager
        self._init_db()

    def _init_db(self):
        try:
            with self.db.trading_writer() as conn:
                conn.execute(TLP_TRADE_LOG_SCHEMA)
        except Exception as exc:
            logger.error(f"[TLP] DB init failed: {exc}")

    def record(
        self,
        strategy: str,
        session_date: str,
        regime: Optional[str] = None,
        confidence: Optional[float] = None,
        vix: Optional[float] = None,
        structure: Optional[str] = None,
        session_type: Optional[str] = None,
        entry_time=None,
        entry_price: Optional[float] = None,
        exit_time=None,
        exit_reason: Optional[str] = None,
        mae_rs: Optional[float] = None,
        mfe_rs: Optional[float] = None,
        pnl_net_rs: Optional[float] = None,
        exit_efficiency: Optional[float] = None,
        hold_bars: Optional[int] = None,
    ):
        def _ts(v):
            return v.isoformat() if hasattr(v, "isoformat") else (str(v) if v else None)

        try:
            with self.db.trading_writer() as conn:
                conn.execute(
                    """
                    INSERT INTO tlp_trade_log
                    (strategy, session_date, regime, confidence, vix, structure,
                     session_type, entry_time, entry_price, exit_time, exit_reason,
                     mae_rs, mfe_rs, pnl_net_rs, exit_efficiency, hold_bars)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    [
                        strategy, session_date, regime, confidence, vix, structure,
                        session_type, _ts(entry_time), entry_price, _ts(exit_time),
                        exit_reason, mae_rs, mfe_rs, pnl_net_rs, exit_efficiency, hold_bars,
                    ],
                )
            logger.info(
                f"[TLP] {strategy} | {session_date} | {exit_reason} | "
                f"net Rs {pnl_net_rs:+,.0f} | eff={exit_efficiency:.2f} | "
                f"MAE={mae_rs:+,.0f} MFE={mfe_rs:+,.0f}"
                if (pnl_net_rs is not None and exit_efficiency is not None
                        and mae_rs is not None and mfe_rs is not None)
                else f"[TLP] {strategy} | {session_date} | {exit_reason}"
            )
        except Exception as exc:
            logger.error(f"[TLP] record() failed: {exc}")
