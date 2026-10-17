import time
import logging
import requests
from typing import Dict, Optional, Tuple
from core.brokers.base import BrokerAdapter
from core.brokers.broker_position import BrokerPosition
from core.brokers.mapping.upstox import UpstoxMapping  # 4C.7
from core.events import OrderStatus
from core.execution.order_lifecycle import FillEvent
from core.execution.order_models import NormalizedOrder, OrderSide, OrderType
from core.execution.position_tracker import Position
from core.execution.position_models import PositionSide
from core.instruments.instrument_base import InstrumentType  # 4C.7 fail-fast
from core.clock import Clock


class BrokerAuthError(Exception):
    """Token expired or invalid (HTTP 401/403)."""


class BrokerUnavailableError(Exception):
    """Broker unreachable: timeout, network error, 5xx, or rate limit exhausted."""


class BrokerContractError(Exception):
    """Broker response violated expected schema: missing field, malformed payload, non-success status, or unknown status value."""


# An explicit map, never a default: F-UPX-2 sent every order SELL because the
# side was compared to the string "BUY" and anything else fell through.
_TRANSACTION_TYPE = {OrderSide.BUY: "BUY", OrderSide.SELL: "SELL"}

# Upstox order statuses (API docs, order-status appendix).
_ORDER_STATUS = {
    # Terminal
    "complete":                               OrderStatus.FILLED,
    "rejected":                               OrderStatus.REJECTED,
    "cancelled":                              OrderStatus.CANCELLED,
    "cancelled after market order":           OrderStatus.CANCELLED,
    # Active / live on exchange
    "open":                                   OrderStatus.OPEN,
    "trigger pending":                        OrderStatus.OPEN,
    "modify pending":                         OrderStatus.OPEN,
    "modify validation pending":              OrderStatus.OPEN,
    "modified":                               OrderStatus.OPEN,
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

_TERMINAL = {OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED}


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
        self._mapping: Optional[UpstoxMapping] = None  # 4C.7: lazy-init on first place_order
        self._fill_callback = None
        # broker order_id -> (order, filled quantity, average price) already
        # reported as fills; an order leaves once Upstox reports it terminal.
        self._pending: Dict[str, Tuple[NormalizedOrder, int, float]] = {}

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

    def place_order(self, order: NormalizedOrder) -> str:
        # 4C.7: route using canonical identity when available; fail fast for derivatives
        # that lack it (master absent/stale is a misconfiguration, not a fallback case).
        if self._mapping is None:
            self._mapping = UpstoxMapping()
        ci = getattr(order, "canonical_instrument", None)
        if ci is not None:
            try:
                ref = self._mapping.to_broker(ci)
            except LookupError as e:
                raise BrokerContractError(
                    f"No Upstox mapping for {ci.canonical_id} — "
                    f"master projection may be stale: {e}"
                ) from e
            instrument_token = ref.instrument_key
            product_code = ref.product_code or "I"
        else:
            itype = getattr(order, "instrument_type", None)
            if itype in {InstrumentType.OPTION, InstrumentType.FUTURE}:
                raise BrokerContractError(
                    f"Derivative order for {order.symbol} has no canonical_instrument — "
                    "master absent or stale; refusing to route with display symbol."
                )
            instrument_token = order.symbol
            product_code = "I"

        if order.side not in _TRANSACTION_TYPE:
            raise BrokerContractError(
                f"Order for {order.symbol} has unmappable side {order.side!r}; refusing to route")
        # NormalizedOrder carries no price, so MARKET is the only routable type.
        if order.order_type is not OrderType.MARKET:
            raise BrokerContractError(
                f"Order for {order.symbol} has order_type {order.order_type!r}; "
                "only MARKET is routable (NormalizedOrder has no price)")

        payload = {
            "quantity": int(order.quantity),
            "product": product_code,
            "validity": "DAY",
            "price": 0,
            "tag": order.signal_id,
            "instrument_token": instrument_token,
            "order_type": "MARKET",
            "transaction_type": _TRANSACTION_TYPE[order.side],
            "disclosed_quantity": 0,
            "trigger_price": 0,
            "is_amo": False,
        }

        try:
            response = self._make_request("POST", "/order/place", data=payload)
            if response and response.get("status") == "success":
                order_id = response["data"]["order_id"]
                self.logger.info(f"Order placed successfully. ID: {order_id}")
                self._pending[order_id] = (order, 0, 0.0)
                return order_id
            else:
                error_msg = response.get("errors", "Unknown error") if response else "No response"
                raise RuntimeError(f"Failed to place order: {error_msg}")
        except Exception as e:
            self.logger.error(f"Critical failure in place_order: {e}")
            raise

    def _order_details(self, order_id: str) -> Tuple[OrderStatus, int, float, Optional[str]]:
        """(status, filled quantity, average price, status message) from
        GET /order/details."""
        response = self._make_request("GET", "/order/details", params={"order_id": order_id})
        # BrokerAuthError / BrokerUnavailableError propagate from _make_request

        if not response or response.get("status") != "success":
            raise BrokerContractError(
                f"Unexpected order status response: status={response.get('status') if response else None}"
            )

        try:
            data = response["data"]
            status_str = data.get("status", "")
            filled = int(data.get("filled_quantity") or 0)
            average_price = float(data.get("average_price") or 0.0)
            message = data.get("status_message")
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            raise BrokerContractError(f"Malformed order status payload: {e}") from e

        status = _ORDER_STATUS.get(status_str.lower())
        if status is None:
            raise BrokerContractError(f"Unknown Upstox order status: {status_str!r}")
        return status, filled, average_price, message

    def get_order_status(self, order_id: str) -> OrderStatus:
        return self._order_details(order_id)[0]

    def poll_fills(self) -> None:
        """Report what Upstox has filled since the last poll, for every order
        this adapter placed that is not yet terminal.

        Each newly filled quantity goes to the subscribed callback as a FillEvent
        keyed on the order's correlation_id and symbol (the handler's keys, not
        Upstox's), priced so the fills' VWAP equals Upstox's average_price. One
        GET /order/details per pending order; no call when none is pending.
        Synchronous: the caller drives it from the single-threaded loop.

        An order whose details can't be fetched stays pending for the next poll;
        the other orders are still polled, and BrokerUnavailableError is raised
        at the end so the caller can count the outage. Auth and contract errors
        propagate at once. The fee is 0.0 — order details carry no charges.
        """
        deferred = []
        for broker_id, (order, reported, reported_avg) in list(self._pending.items()):
            try:
                status, filled, average_price, message = self._order_details(broker_id)
            except BrokerUnavailableError as e:
                self.logger.warning(
                    f"Fill poll for order {broker_id} deferred, broker unavailable: {e}")
                deferred.append(broker_id)
                continue

            if filled > reported:
                delta = filled - reported
                price = (average_price * filled - reported_avg * reported) / delta
                self._emit_fill(FillEvent(
                    fill_id=f"{broker_id}-{filled}",
                    order_id=str(order.correlation_id),
                    symbol=order.symbol,
                    quantity=delta,
                    price=price,
                    timestamp=self.clock.now(),
                    side=order.side.value,
                    fee=0.0,
                ))
                self._pending[broker_id] = (order, filled, average_price)

            if status in _TERMINAL:
                del self._pending[broker_id]
                if status is not OrderStatus.FILLED:
                    self.logger.error(
                        f"Order {broker_id} ({order.side.value} {order.quantity} {order.symbol}) "
                        f"{status.value.lower()} by broker with {filled} filled: {message}")

        if deferred:
            raise BrokerUnavailableError(
                f"Fill poll could not reach Upstox for order(s) {deferred}; will retry")

    def _emit_fill(self, fill: FillEvent) -> None:
        if self._fill_callback is None:
            raise RuntimeError(
                f"Fill {fill.fill_id} has no receiver; call subscribe_fills before placing orders")
        self._fill_callback(fill)

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
