import json
import logging
from typing import List
from datetime import datetime
from uuid import UUID

from core.execution.persistence.execution_store import ExecutionStore
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType, InstrumentType, OrderMetadata


class OrderRepository:
    def __init__(self, store: ExecutionStore):
        self.store = store
        self.logger = logging.getLogger(__name__)

    def save(self, order: NormalizedOrder):
        try:
            conn = self.store.get_connection()
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO orders 
                    (correlation_id, symbol, side, quantity, order_type, strategy_id, signal_id, timestamp, metadata, group_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(order.correlation_id),
                        order.symbol,
                        order.side.value,
                        order.quantity,
                        order.order_type.value,
                        order.strategy_id,
                        order.signal_id,
                        order.timestamp.isoformat(),
                        json.dumps(
                            order.metadata.__dict__) if order.metadata else "{}",
                        str(order.group_id) if order.group_id else None
                    )
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            self.logger.error(
                f"Failed to save order {order.correlation_id}: {e}")
            raise

    def get_all(self) -> List[NormalizedOrder]:
        orders = []
        try:
            conn = self.store.get_connection()
            try:
                rows = conn.execute(
                    "SELECT correlation_id, symbol, side, quantity, order_type, "
                    "strategy_id, signal_id, timestamp, metadata, group_id "
                    "FROM orders ORDER BY timestamp ASC").fetchall()
                for row in rows:
                    meta_dict = json.loads(row[8])
                    metadata = OrderMetadata(
                        **meta_dict) if meta_dict else None

                    # Parse symbol into Instrument object
                    from core.instruments.instrument_parser import InstrumentParser
                    instrument = InstrumentParser.parse(row[1])

                    order = NormalizedOrder(
                        correlation_id=row[0],
                        instrument=instrument,
                        side=OrderSide(row[2]),
                        quantity=float(row[3]),
                        order_type=OrderType(row[4]),
                        strategy_id=row[5],
                        signal_id=row[6],
                        timestamp=datetime.fromisoformat(row[7]),
                        metadata=metadata,
                        group_id=UUID(row[9]) if row[9] else None
                    )
                    orders.append(order)
            finally:
                conn.close()
        except Exception as e:
            self.logger.error(f"Failed to load orders: {e}")
        return orders

