import time
import logging
import requests
from typing import Dict, Optional
from core.brokers.base import BrokerAdapter
from core.brokers.broker_position import BrokerPosition
from core.events import OrderEvent, OrderStatus
from core.execution.position_tracker import Position
from core.execution.position_models import PositionSide
from core.clock import Clock


class BrokerAuthError(Exception):
    """Token expired or invalid (HTTP 401/403)."""


class BrokerUnavailableError(Exception):
    """Broker unreachable: timeout, network error, 5xx, or rate limit exhausted."""


class BrokerContractError(Exception):
    """Broker response violated expected schema: missing field, malformed payload, non-success status, or unknown status value."""


class UpstoxAdapter(BrokerAdapter):

    BASE_URL = "https://api.upstox.com/v2"

    def __init__(self, api_key: str, api_secret: str, access_token: str, clock: Clock):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.clock = clock
        self.logger = logging.getLogger(__name__)
        self._last_req_time = 0.0
        self._req_interval = 0.11  # slightly above 0.1 → 9 req/sec

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_req_time
        if elapsed < self._req_interval:
            time.sleep(self._req_interval - elapsed)
        self._last_req_time = time.time()

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None):
        self._rate_limit()
        url = f"{self.BASE_URL}{endpoint}"

        retries = 3
        backoff = 1.0

        for attempt in range(retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self._get_headers(),
                    json=data,
                    params=params,
                    timeout=10,
                )

                if response.status_code in (401, 403):
                    self.logger.error(f"Authentication failed on {endpoint} (HTTP {response.status_code}).")
                    raise BrokerAuthError(f"Upstox token expired or invalid (HTTP {response.status_code})")

                if response.status_code == 429:
                    if attempt == retries - 1:
                        raise BrokerUnavailableError(
                            f"Rate limit exhausted on {endpoint} after {retries} attempts"
                        )
                    time.sleep(backoff * (2 ** attempt))
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Upstox API error on {endpoint}: {e}")
                if attempt == retries - 1:
                    raise BrokerUnavailableError(f"Broker unreachable on {endpoint}: {e}") from e
                time.sleep(backoff * (2 ** attempt))

        raise BrokerUnavailableError(f"Request exhausted without response on {endpoint}")

    def place_order(self, order: OrderEvent) -> str:
        payload = {
            "quantity": int(order.quantity),
            "product": "I",  # INTRADAY
            "validity": "DAY",
            "price": order.price if order.order_type.value == "LIMIT" else 0,
            "tag": order.signal_id_reference,
            "instrument_token": order.symbol,
            "order_type": "MARKET" if order.order_type.value == "MARKET" else "LIMIT",
            "transaction_type": "BUY" if order.side == "BUY" else "SELL",
            "disclosed_quantity": 0,
            "trigger_price": 0,
            "is_amo": False,
        }

        try:
            response = self._make_request("POST", "/order/place", data=payload)
            if response and response.get("status") == "success":
                order_id = response["data"]["order_id"]
                self.logger.info(f"Order placed successfully. ID: {order_id}")
                return order_id
            else:
                error_msg = response.get("errors", "Unknown error") if response else "No response"
                raise RuntimeError(f"Failed to place order: {error_msg}")
        except Exception as e:
            self.logger.error(f"Critical failure in place_order: {e}")
            raise

    def get_order_status(self, order_id: str) -> OrderStatus:
        response = self._make_request("GET", "/order/details", params={"order_id": order_id})
        # BrokerAuthError / BrokerUnavailableError propagate from _make_request

        if not response or response.get("status") != "success":
            raise BrokerContractError(
                f"Unexpected order status response: status={response.get('status') if response else None}"
            )

        try:
            status_str = response["data"].get("status", "")
        except (KeyError, TypeError) as e:
            raise BrokerContractError(f"Malformed order status payload: {e}") from e

        mapping = {
            # Terminal
            "completed":                              OrderStatus.FILLED,
            "rejected":                               OrderStatus.REJECTED,
            "cancelled":                              OrderStatus.CANCELLED,
            # Active / live on exchange
            "open":                                   OrderStatus.OPEN,
            "trigger pending":                        OrderStatus.OPEN,
            "modify pending":                         OrderStatus.OPEN,
            "cancel pending":                         OrderStatus.OPEN,
            "not cancelled":                          OrderStatus.OPEN,
            "not modified":                           OrderStatus.OPEN,
            # Submission / validation in flight
            "put order req received":                 OrderStatus.SUBMITTED,
            "open pending":                           OrderStatus.SUBMITTED,
            "validation pending":                     OrderStatus.SUBMITTED,
            # AMO states
            "after market order req received":        OrderStatus.SUBMITTED,
            "modify after market order req received": OrderStatus.SUBMITTED,
        }

        result = mapping.get(status_str.lower())
        if result is None:
            raise BrokerContractError(f"Unknown Upstox order status: {status_str!r}")
        return result

    def get_positions(self) -> Dict[str, Position]:
        response = self._make_request("GET", "/portfolio/short-term-positions")
        # BrokerAuthError / BrokerUnavailableError propagate from _make_request

        if not response or response.get("status") != "success":
            raise BrokerContractError(
                f"Unexpected positions response: status={response.get('status') if response else None}"
            )

        positions = {}
        try:
            for pos_data in response["data"]:
                symbol = pos_data["trading_symbol"]
                qty = float(pos_data["quantity"])
                avg_price = float(pos_data["average_price"])

                if qty > 0:
                    side = PositionSide.LONG
                elif qty < 0:
                    side = PositionSide.SHORT
                else:
                    side = PositionSide.FLAT

                positions[symbol] = BrokerPosition(
                    symbol=symbol,
                    side=side,
                    quantity=abs(qty),
                    avg_price=avg_price,
                    last_updated=self.clock.now(),
                    instrument_token=pos_data.get("instrument_token"),
                )
        except (KeyError, ValueError, TypeError) as e:
            raise BrokerContractError(f"Malformed position payload: {e}") from e

        return positions

    def cancel_order(self, order_id: str) -> bool:
        response = self._make_request("DELETE", "/order/cancel", params={"order_id": order_id})
        # BrokerAuthError / BrokerUnavailableError propagate from _make_request
        return bool(response and response.get("status") == "success")
