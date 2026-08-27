import logging
from datetime import datetime
from typing import Optional

from core.database.manager import DatabaseManager
from core.market.session_schedule import CAS_EFFECTIVE, session_window
from core.messaging.zmq_handler import ZmqPublisher

logger = logging.getLogger(__name__)

CAS_MARKABLE_PREFIX = "NSE_EQ|"


def is_carry_forward(symbol, bar_ts, op, hi, lo, cl, vol) -> bool:
    """True if this bar is a stale-LTP artifact of the CAS cash halt.

    During 15:15-15:35 the Upstox feed keeps broadcasting the last traded price
    with quantity 0, so a bar materialises with no trades behind it.

    EQUITIES ONLY. The predicate discriminates on volume == 0, and NSE_INDEX
    symbols carry volume 0 on every bar of every session — applying it to an
    index would mark that index's real closing value as fabricated.
    """
    if not symbol.startswith(CAS_MARKABLE_PREFIX):
        return False
    if bar_ts.date() < CAS_EFFECTIVE or int(vol) != 0:
        return False
    auction = session_window("cash_auction", bar_ts.date())
    if auction is None:
        return False
    return auction[0] <= bar_ts.time() < auction[1] and op == hi == lo == cl

class DBTickAggregator:
    """
    Deterministic aggregator that reads raw ticks from today's live buffer
    and produces OHLCV bars in the same buffer.
    """

    def __init__(self, db_manager: DatabaseManager, zmq_publisher: Optional[ZmqPublisher] = None):
        self.db_manager = db_manager
        self.zmq_publisher = zmq_publisher

    def aggregate(self, symbols, db_manager, zmq_publisher):
        for symbol in symbols:
            try:
                self._aggregate_one(symbol, db_manager, zmq_publisher)
            except Exception as e:
                logger.error(f"Aggregation failed for {symbol}: {e}")

    def _aggregate_one(self, symbol, db_manager, zmq_publisher):
        with db_manager.live_buffer_reader() as conns:
            if 'ticks' not in conns:
                return
            ticks_conn = conns['ticks']
            last_bar_ts = None
            if 'candles' in conns:
                res = conns['candles'].execute(
                    "SELECT MAX(timestamp) FROM candles WHERE symbol=? AND timeframe='1m' AND is_synthetic=FALSE",
                    [symbol],
                ).fetchone()
                last_bar_ts = res[0] if res and res[0] else None
            start_ts = last_bar_ts if last_bar_ts else datetime(2000, 1, 1)
            rows = ticks_conn.execute(
                """
                SELECT date_trunc('minute', timestamp) AS bar_ts,
                       first(price ORDER BY timestamp ASC) AS op,
                       max(price) AS hi, min(price) AS lo,
                       last(price ORDER BY timestamp ASC) AS cl,
                       sum(volume) AS vol
                FROM ticks WHERE symbol=? AND timestamp>=? GROUP BY 1 ORDER BY 1 ASC
                """,
                [symbol, start_ts],
            ).fetchall()

        current_minute = datetime.now().replace(second=0, microsecond=0)
        completed = [r for r in rows if r[0] < current_minute and r[1] is not None and r[4] is not None]
        if not completed:
            return

        with db_manager.live_candles_writer() as candles_conn:
            for bar_ts, op, hi, lo, cl, vol in completed:
                synthetic = is_carry_forward(symbol, bar_ts, op, hi, lo, cl, vol)
                candles_conn.execute(
                    """
                    INSERT INTO candles
                    (symbol, timeframe, timestamp, open, high, low, close, volume, is_synthetic)
                    VALUES (?, '1m', ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (symbol, timeframe, timestamp) DO UPDATE SET
                        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                        close=EXCLUDED.close, volume=EXCLUDED.volume,
                        is_synthetic=EXCLUDED.is_synthetic
                    """,
                    [symbol, bar_ts, op, hi, lo, cl, int(vol), synthetic],
                )

        if zmq_publisher:
            for bar_ts, op, hi, lo, cl, vol in completed:
                zmq_publisher.publish(
                    f"market.candle.1m.{symbol}", "market_candle",
                    {"symbol": symbol, "timeframe": "1m", "timestamp": bar_ts.isoformat(),
                     "open": float(op), "high": float(hi), "low": float(lo),
                     "close": float(cl), "volume": int(vol)},
                )
