"""
Broker Adapter Interface
------------------------
Abstracts the broker-specific API (REST/WS) behind a standard interface.
"""
from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional, List
from core.events import OrderEvent, OrderStatus
from core.execution.order_lifecycle import FillEvent
from core.execution.position_tracker import Position

class BrokerAdapter(ABC):
    """
    Abstract base class for all broker connections.
    """
    
    @abstractmethod
    def place_order(self, order: OrderEvent) -> str:
        """Dispatches an order to the broker. Returns broker_order_id."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus:
        """Queries the current status of an order."""
        pass

    @abstractmethod
    def get_positions(self) -> Dict[str, Position]:
        """Fetches current net positions from the broker."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Attempts to cancel an open order."""
        pass

    def subscribe_fills(self, callback: Callable[[FillEvent], None]) -> None:
        """Registers the fill callback. ExecutionHandler.__init__ calls this on
        whatever broker it is given (F-UPX-3: without it a live run can't be built)."""
        self._fill_callback = callback
