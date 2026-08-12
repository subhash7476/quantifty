import logging
from datetime import datetime
from typing import Optional

from core.database.manager import DatabaseManager
from core.messaging.zmq_handler import ZmqPublisher

logger = logging.getLogger(__name__)

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
                candles_conn.execute(
                    """
                    INSERT INTO candles
                    (symbol, timeframe, timestamp, open, high, low, close, volume, is_synthetic)
                    VALUES (?, '1m', ?, ?, ?, ?, ?, ?, FALSE)
                    ON CONFLICT (symbol, timeframe, timestamp) DO UPDATE SET
                        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                        close=EXCLUDED.close, volume=EXCLUDED.volume, is_synthetic=FALSE
                    """,
                    [symbol, bar_ts, op, hi, lo, cl, int(vol)],
                )

        if zmq_publisher:
            for bar_ts, op, hi, lo, cl, vol in completed:
                zmq_publisher.publish(
                    f"market.candle.1m.{symbol}", "market_candle",
                    {"symbol": symbol, "timeframe": "1m", "timestamp": bar_ts.isoformat(),
                     "open": float(op), "high": float(hi), "low": float(lo),
                     "close": float(cl), "volume": int(vol)},
                )
