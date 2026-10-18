"""
Broker Adapter Interface
------------------------
Abstracts the broker-specific API (REST/WS) behind a standard interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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

    def poll_fills(self) -> None:
        """Reports fills that have happened since the last call, through the
        subscribed callback. LoopDriver calls it once per loop iteration in LIVE
        mode. A broker that pushes its own fills has nothing to poll."""
        return None

    def resume_orders(self, orders) -> "ResumeResult":
        """Takes back, after a restart, the (order, filled quantity, average price)
        the ledger shows still open, so poll_fills covers them again. A broker that
        pushes its own fills has nothing to resume."""
        return ResumeResult()


@dataclass(frozen=True)
class ResumeResult:
    """What resume_orders could not take back: orders not found at the broker,
    and orders whose tag the broker holds more than once."""
    not_found: List = field(default_factory=list)
    duplicated: List = field(default_factory=list)
