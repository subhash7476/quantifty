import dataclasses
import hashlib
import re
import time
import logging
import requests
from typing import Callable, Dict, List, Optional, Tuple
from core.alerts.alerter import alerter
from core.brokers.base import BrokerAdapter, ResumeResult
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


class BrokerAmbiguousPlacementError(BrokerUnavailableError):
    """A placement failed after the request may have reached Upstox (timeout, dropped
    connection, 5xx, or a success reply with no order id). The order may be live. It
    is never resent; an operator reconciles against the broker's order book."""


class BrokerOrderRefusedError(BrokerUnavailableError):
    """The order was definitely not placed: refused before it was sent (no mapping,
    an unroutable side or order type), or refused by Upstox (a 4xx, or a reply with
    status "error"). A BrokerUnavailableError subclass so the handler's broker-error
    branch counts it and returns no order."""


class BrokerOrderNotFilledError(Exception):
    """Upstox ended an order this adapter placed as rejected or cancelled. Any
    quantity it did fill has already been reported as fills. `not_filled` lists
    each order as an EndedOrder."""


@dataclasses.dataclass(frozen=True)
class EndedOrder:
    """An order Upstox ended without filling it in full."""
    correlation_id: str
    status: OrderStatus
    description: str


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

# The fill poll runs on the single-threaded loop: one short attempt per call, no
# backoff. The next loop iteration is the retry.
_POLL_ATTEMPTS = 1
_POLL_TIMEOUT_S = 3
# Orders missing from the order book at a restart are looked for again no more
# often than this, so watching them costs one book call per interval, not per poll.
_WATCH_INTERVAL_S = 30

# Upstox rejects a tag over 40 characters (UDAPI1119). A signal_id that is short
# and plain is sent as is; anything else is sent as a hash prefix, so the tag is
# always derivable from the ledger's signal_id when looking the order up later.
_TAG_MAX = 40
_PLAIN_TAG = re.compile(r"[A-Za-z0-9_-]{1,40}")


def _whole(value) -> Optional[int]:
    """`value` as a whole number, or None when it is not one."""
    try:
        number = float(value)
        whole = int(number)
    except (TypeError, ValueError, OverflowError):
        return None
    return whole if number == whole else None


def order_tag(signal_id: str) -> str:
    """The Upstox order tag for a signal_id: deterministic, at most 40 characters."""
    signal_id = str(signal_id)
    if _PLAIN_TAG.fullmatch(signal_id):
        return signal_id
    return hashlib.sha256(signal_id.encode("utf-8")).hexdigest()[:_TAG_MAX]


class UpstoxAdapter(BrokerAdapter):

    BASE_URL = "https://api.upstox.com/v2"
    # Order placement and cancellation are served from the HFT host. V2 place-order
    # is marked deprecated there; V3 returns a list of order ids.
    HFT_URL = "https://api-hft.upstox.com/v3"

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
        # Estimated charges for a fill: fee_model(order, price) prices the order's
        # quantity. build_runner sets it to the handler's own fee schedule, so a live
        # fill is charged like a paper one. None charges 0.0.
        self.fee_model: Optional[Callable[[NormalizedOrder, float], float]] = None
        # broker order_id -> (order, filled quantity, average price, fee) already
        # reported as fills; an order leaves once Upstox reports it terminal.
        self._pending: Dict[str, Tuple[NormalizedOrder, int, float, float]] = {}
        # Placements that failed ambiguously (the order may be live): keyed on the
        # order's correlation_id. Each poll looks them up in the order book by tag;
        # one found there is polled like any other order. poll_fills keeps failing
        # while any is held, so the driver halts trading until an operator reconciles.
        self._unconfirmed: Dict[str, NormalizedOrder] = {}
        # Orders the ledger held open at a restart that the order book did not show:
        # correlation_id -> (order, filled, average price). Watched without failing
        # the poll, and adopted if they appear.
        self._watch: Dict[str, Tuple[NormalizedOrder, int, float]] = {}
        self._watch_checked_at: Optional[float] = None

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

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                      params: Optional[Dict] = None, *, attempts: int = 3,
                      timeout: float = 10, placement: bool = False,
                      base_url: Optional[str] = None):
        """One HTTP call, retried up to `attempts` times with backoff.

        `placement` is for a request that must never be resent (order placement).
        When its last attempt fails, a failure that leaves it unknown whether Upstox
        acted on it raises BrokerAmbiguousPlacementError, and a 4xx raises
        BrokerOrderRefusedError, in place of BrokerUnavailableError.
        """
        self._rate_limit()
        url = f"{base_url or self.BASE_URL}{endpoint}"

        backoff = 1.0

        for attempt in range(attempts):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self._get_headers(),
                    json=data,
                    params=params,
                    timeout=timeout,
                )

                if response.status_code in (401, 403):
                    self.logger.error(f"Authentication failed on {endpoint} (HTTP {response.status_code}).")
                    raise BrokerAuthError(f"Upstox token expired or invalid (HTTP {response.status_code})")

                if response.status_code == 429:
                    if attempt == attempts - 1:
                        raise BrokerUnavailableError(
                            f"Rate limit exhausted on {endpoint} after {attempts} attempts"
                        )
                    time.sleep(backoff * (2 ** attempt))
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Upstox API error on {endpoint}: {e}")
                if attempt == attempts - 1:
                    if placement and self._may_have_reached_broker(e):
                        raise BrokerAmbiguousPlacementError(
                            f"{endpoint} failed after the request may have reached Upstox: {e}") from e
                    if placement:
                        raise BrokerOrderRefusedError(
                            f"Upstox refused the order on {endpoint}: {e} "
                            f"{self._error_body(e)}".rstrip()) from e
                    raise BrokerUnavailableError(f"Broker unreachable on {endpoint}: {e}") from e
                time.sleep(backoff * (2 ** attempt))

        raise BrokerUnavailableError(f"Request exhausted without response on {endpoint}")

    @staticmethod
    def _may_have_reached_broker(error: requests.exceptions.RequestException) -> bool:
        """A timeout, dropped connection, unreadable body or 5xx leaves it unknown
        whether Upstox acted; a 4xx is a definite refusal."""
        if isinstance(error, requests.exceptions.HTTPError) and error.response is not None:
            return error.response.status_code >= 500
        return True

    @staticmethod
    def _error_body(error: requests.exceptions.RequestException) -> str:
        """Upstox's `errors` from a failed reply, when it has a readable one."""
        response = getattr(error, "response", None)
        try:
            body = response.json() if response is not None else None
        except ValueError:
            return ""
        errors = body.get("errors") if isinstance(body, dict) else None
        return f"errors={errors!r:.300}" if errors else ""

    def place_order(self, order: NormalizedOrder) -> str:
        # Nothing has been sent while the payload is built, so any failure there is
        # a definite refusal, never an order the handler should report as placed.
        try:
            payload = self._payload(order)
        except BrokerOrderRefusedError:
            raise
        except Exception as e:
            raise BrokerOrderRefusedError(
                f"Order for {order.symbol} could not be prepared, so nothing was sent: {e!r}"
            ) from e
        return self._send(order, payload)

    def _payload(self, order: NormalizedOrder) -> Dict:
        """The V3 placement body for an order; raises BrokerOrderRefusedError for an
        order that cannot be routed."""
        # 4C.7: route using canonical identity when available; fail fast for derivatives
        # that lack it (master absent/stale is a misconfiguration, not a fallback case).
        if self._mapping is None:
            self._mapping = UpstoxMapping()
        ci = getattr(order, "canonical_instrument", None)
        if ci is not None:
            try:
                ref = self._mapping.to_broker(ci)
            except LookupError as e:
                raise BrokerOrderRefusedError(
                    f"No Upstox mapping for {ci.canonical_id} — "
                    f"master projection may be stale: {e}"
                ) from e
            instrument_token = ref.instrument_key
            product_code = ref.product_code or "I"
        else:
            itype = getattr(order, "instrument_type", None)
            if itype in {InstrumentType.OPTION, InstrumentType.FUTURE}:
                raise BrokerOrderRefusedError(
                    f"Derivative order for {order.symbol} has no canonical_instrument — "
                    "master absent or stale; refusing to route with display symbol."
                )
            instrument_token = order.symbol
            product_code = "I"

        if order.side not in _TRANSACTION_TYPE:
            raise BrokerOrderRefusedError(
                f"Order for {order.symbol} has unmappable side {order.side!r}; refusing to route")
        # NormalizedOrder carries no price, so MARKET is the only routable type.
        if order.order_type is not OrderType.MARKET:
            raise BrokerOrderRefusedError(
                f"Order for {order.symbol} has order_type {order.order_type!r}; "
                "only MARKET is routable (NormalizedOrder has no price)")

        return {
            "quantity": int(order.quantity),
            "product": product_code,
            "validity": "DAY",
            "price": 0,
            "tag": order_tag(order.signal_id),
            "instrument_token": instrument_token,
            "order_type": "MARKET",
            "transaction_type": _TRANSACTION_TYPE[order.side],
            "disclosed_quantity": 0,
            "trigger_price": 0,
            "is_amo": False,
            # One order per placement: a sliced order returns several ids, which
            # the one-order-per-signal ledger cannot hold.
            "slice": False,
        }

    def _send(self, order: NormalizedOrder, payload: Dict) -> str:
        try:
            # One attempt: resending a POST whose first copy Upstox may have
            # accepted places a second order the ledger never sees.
            response = self._make_request("POST", "/order/place", data=payload, attempts=1,
                                          placement=True, base_url=self.HFT_URL)
            # The request got a 200. Only an explicit "error" is a definite refusal;
            # a reply that is not an object, or says neither, leaves it unknown
            # whether the order is live.
            if not isinstance(response, dict) or response.get("status") not in ("success", "error"):
                raise BrokerAmbiguousPlacementError(
                    f"Upstox replied 200 with an unreadable placement result: {response!r:.200}")
            if response["status"] == "error":
                raise BrokerOrderRefusedError(
                    f"Upstox refused the order: {response.get('errors', 'no errors given')!r:.300}")
            order_ids = self._placed_order_ids(response)
            if len(order_ids) != 1:
                raise BrokerAmbiguousPlacementError(
                    f"Upstox reported success with order ids {order_ids!r}; expected exactly one")
            order_id = order_ids[0]
            self.logger.info(f"Order placed successfully. ID: {order_id}")
            self._pending[order_id] = (order, 0, 0.0, 0.0)
            return order_id
        except BrokerAmbiguousPlacementError as e:
            self._unconfirmed[str(order.correlation_id)] = order
            alerter.critical(
                f"ORDER PLACEMENT UNCONFIRMED: {order.side.value} {order.quantity} {order.symbol} "
                f"signal_id={order.signal_id} - it may be live at Upstox and was NOT resent. "
                f"Check the Upstox order book. ({e})")
            self.logger.error(f"Critical failure in place_order: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Critical failure in place_order: {e}")
            raise

    @staticmethod
    def _placed_order_ids(response: Dict) -> List[str]:
        """The ids in V3's `data.order_ids`, as text. Empty when the list is missing
        or holds anything but non-empty ids, so the caller treats it as ambiguous."""
        data = response.get("data")
        ids = data.get("order_ids") if isinstance(data, dict) else None
        if not isinstance(ids, list):
            return []
        valid = [str(i) for i in ids
                 if isinstance(i, (str, int)) and not isinstance(i, bool) and str(i)]
        return valid if len(valid) == len(ids) else []

    def _fetch_order(self, order_id: str, *, attempts: int, timeout: float) -> Dict:
        """The `data` object of GET /order/details."""
        response = self._make_request("GET", "/order/details", params={"order_id": order_id},
                                      attempts=attempts, timeout=timeout)
        # BrokerAuthError / BrokerUnavailableError propagate from _make_request

        if not isinstance(response, dict) or response.get("status") != "success":
            raise BrokerContractError(
                "Unexpected order status response: status="
                f"{response.get('status') if isinstance(response, dict) else type(response).__name__}"
            )
        data = response.get("data")
        if not isinstance(data, dict):
            raise BrokerContractError(
                f"Malformed order status payload: data is {type(data).__name__}")
        return data

    @staticmethod
    def _resolve_status(data: Dict) -> OrderStatus:
        raw = data.get("status")
        if not isinstance(raw, str) or not raw:
            raise BrokerContractError(f"Order status missing or not text: {raw!r}")
        status = _ORDER_STATUS.get(raw.lower())
        if status is None:
            raise BrokerContractError(f"Unknown Upstox order status: {raw!r}")
        return status

    def get_order_status(self, order_id: str) -> OrderStatus:
        return self._resolve_status(self._fetch_order(order_id, attempts=3, timeout=10))

    @staticmethod
    def _filled_quantity(data: Dict) -> int:
        value = data.get("filled_quantity")
        try:
            if value is None or isinstance(value, bool):
                raise ValueError("absent")
            number = float(value)
            if number != int(number):
                raise ValueError("not a whole number")
        except (TypeError, ValueError, OverflowError) as e:
            raise BrokerContractError(
                f"filled_quantity missing or malformed: {value!r} ({e})") from e
        return int(number)

    @staticmethod
    def _average_price(data: Dict, filled: int) -> float:
        value = data.get("average_price")
        try:
            price = float(value)
        except (TypeError, ValueError) as e:
            raise BrokerContractError(
                f"average_price missing or malformed with {filled} filled: {value!r}") from e
        if not price > 0:
            raise BrokerContractError(f"average_price {value!r} is not positive with {filled} filled")
        return price

    def poll_fills(self) -> None:
        """Report what Upstox has filled since the last poll, for every order
        this adapter placed that is not yet terminal.

        Each newly filled quantity goes to the subscribed callback as a FillEvent
        keyed on the order's correlation_id and symbol (the handler's keys, not
        Upstox's), priced so the fills' VWAP equals Upstox's average_price. One
        short GET /order/details per pending order, a single attempt with no
        backoff (the next poll is the retry); no call when none is pending.
        Synchronous: the caller drives it from the single-threaded loop.

        A placement that failed ambiguously is first looked up in the order book
        (GET /order/retrieve-all) by its tag. One found there is polled from then
        on; one not found stays unconfirmed.

        A problem with one order never stops the others from being polled, and
        is raised once, after the sweep, as the most severe kind found:
        BrokerContractError (a reply that can't be trusted: the order stays
        pending and is polled again), BrokerAmbiguousPlacementError (a placement
        that may be live and is unresolved), BrokerUnavailableError (the sweep
        stops at the first unreachable order, bounding the stall to one call,
        and moves it to the back), BrokerOrderNotFilledError (an order ended
        rejected or cancelled; reported once). BrokerAuthError aborts at once.
        Order details carry no charges, so each fill's fee is the fee_model's
        estimate for the quantity filled so far, less what earlier fills carried.
        """
        unavailable, contract, not_filled = [], [], []
        check_watch = bool(self._watch) and self._watch_due()
        if self._unconfirmed or check_watch:
            try:
                book = self._fetch_order_book(attempts=_POLL_ATTEMPTS, timeout=_POLL_TIMEOUT_S)
            except (BrokerUnavailableError, BrokerContractError) as e:
                book = None
                if self._unconfirmed:
                    target = unavailable if isinstance(e, BrokerUnavailableError) else contract
                    target.append(f"order book: {e}")
                else:
                    self.logger.warning(f"Order book unreadable while watching for orders "
                                        f"missing after a restart: {e}")
            if book is not None:
                if self._unconfirmed:
                    contract.extend(self._resolve_unconfirmed(book))
                if check_watch:
                    self._resolve_watch(book)
        order_ids = list(self._pending)
        for position, broker_id in enumerate(order_ids):
            try:
                ended = self._poll_order(broker_id)
            except BrokerUnavailableError as e:
                self.logger.warning(
                    f"Fill poll for order {broker_id} deferred, broker unavailable: {e}")
                unavailable.append(f"{broker_id}: {e}")
                skipped = len(order_ids) - position - 1
                if skipped:
                    unavailable.append(f"{skipped} more order(s) not polled this sweep")
                self._pending[broker_id] = self._pending.pop(broker_id)
                break
            except BrokerContractError as e:
                self.logger.error(f"Fill poll for order {broker_id} unusable: {e}")
                contract.append(f"{broker_id}: {e}")
                continue
            if ended:
                not_filled.append(ended)
        self._raise_poll_problems(unavailable, contract, not_filled)

    def _poll_order(self, broker_id: str) -> Optional[EndedOrder]:
        """Poll one pending order; returns an EndedOrder if it ended rejected or
        cancelled. Reports the filled delta before looking at the status, so a
        fill is never held back by a status the adapter can't read."""
        order, reported, reported_avg, reported_fee = self._pending[broker_id]
        data = self._fetch_order(broker_id, attempts=_POLL_ATTEMPTS, timeout=_POLL_TIMEOUT_S)

        filled = self._filled_quantity(data)
        if not reported <= filled <= order.quantity:
            raise BrokerContractError(
                f"filled_quantity {filled} is outside {reported}..{order.quantity} "
                "(already reported..ordered)")
        if filled > reported:
            average_price = self._average_price(data, filled)
            delta = filled - reported
            price = (average_price * filled - reported_avg * reported) / delta
            if not price > 0:
                raise BrokerContractError(
                    f"average_price {average_price} with {filled} filled implies a "
                    f"non-positive price {price} for the new {delta}")
            try:
                fee_so_far = self._fee(order, filled, average_price)
            except Exception as e:
                # The fill matters more than its fee estimate: book it at no fee
                # now; the next fill's estimate covers the cumulative difference.
                self.logger.error(f"Fee estimate failed for order {broker_id}; fill booked "
                                  f"with no fee: {e!r}")
                fee_so_far = reported_fee
            self._emit_fill(FillEvent(
                fill_id=f"{broker_id}-{filled}",
                order_id=str(order.correlation_id),
                symbol=order.symbol,
                quantity=delta,
                price=price,
                timestamp=self.clock.now(),
                side=order.side.value,
                fee=fee_so_far - reported_fee,
            ))
            self._pending[broker_id] = (order, filled, average_price, fee_so_far)
            reported = filled

        status = self._resolve_status(data)
        if status not in _TERMINAL:
            return None
        if status is OrderStatus.FILLED:
            if reported != order.quantity:
                raise BrokerContractError(
                    f"status complete but only {reported} of {order.quantity} reported filled")
            del self._pending[broker_id]
            return None

        del self._pending[broker_id]
        description = (
            f"order {broker_id} ({order.side.value} {order.quantity} {order.symbol}, "
            f"signal_id={order.signal_id}) {status.value.lower()} by Upstox with "
            f"{reported} filled: {data.get('status_message')}")
        self.logger.error(description)
        alerter.critical(f"ORDER NOT FILLED: {description}")
        return EndedOrder(str(order.correlation_id), status, description)

    def _fee(self, order: NormalizedOrder, filled: int, average_price: float) -> float:
        """The fee_model's estimate for `filled` of the order at its average price."""
        if self.fee_model is None or filled <= 0:
            return 0.0
        return float(self.fee_model(dataclasses.replace(order, quantity=filled), average_price))

    def _fetch_order_book(self, *, attempts: int, timeout: float) -> List[Dict]:
        """The day's orders from GET /order/retrieve-all. The docs show both a bare
        list and a {"status": "success", "data": [...]} envelope; either is accepted."""
        response = self._make_request("GET", "/order/retrieve-all",
                                      attempts=attempts, timeout=timeout)
        if isinstance(response, dict) and response.get("status") == "success":
            response = response.get("data")
        if not isinstance(response, list) or not all(isinstance(o, dict) for o in response):
            raise BrokerContractError(
                f"Unexpected order book response: {response!r:.200}")
        return response

    def _book_matches(self, book: List[Dict], order: NormalizedOrder) -> Tuple[List[str], List[str]]:
        """Order ids in the book that carry this order's tag, side and quantity, and
        ids that carry its tag on another side or quantity (logged; not this order
        as placed, e.g. one modified at Upstox)."""
        tag = order_tag(order.signal_id)
        matches, mismatched = [], []
        for entry in book:
            if entry.get("tag") != tag or not entry.get("order_id"):
                continue
            same = (entry.get("transaction_type") == _TRANSACTION_TYPE.get(order.side)
                    and _whole(entry.get("quantity")) == int(order.quantity))
            if same:
                matches.append(str(entry["order_id"]))
            else:
                mismatched.append(str(entry["order_id"]))
                self.logger.error(
                    f"Order book entry {entry.get('order_id')} carries the tag of "
                    f"signal_id={order.signal_id} but is {entry.get('transaction_type')} "
                    f"{entry.get('quantity')}, not {order.side.value} {order.quantity}; ignored")
        return matches, mismatched

    def _watch_due(self) -> bool:
        """At most one order-book check every _WATCH_INTERVAL_S for watched orders."""
        now = time.monotonic()
        if self._watch_checked_at is not None and now - self._watch_checked_at < _WATCH_INTERVAL_S:
            return False
        self._watch_checked_at = now
        return True

    def _resolve_watch(self, book: List[Dict]) -> None:
        """Adopt any order missing at restart that has since appeared in the book."""
        for key, (order, filled, average_price) in list(self._watch.items()):
            matches, _ = self._book_matches(book, order)
            if len(matches) != 1:
                continue
            del self._watch[key]
            self._pending[matches[0]] = (order, filled, average_price,
                                         self._safe_fee(order, filled, average_price))
            message = (f"ORDER FOUND AT UPSTOX AFTER A RESTART: {order.side.value} {order.quantity} "
                       f"{order.symbol} signal_id={order.signal_id} is order {matches[0]}; its "
                       "fills are polled from now on.")
            self.logger.error(message)
            alerter.critical(message)

    def _safe_fee(self, order: NormalizedOrder, filled: int, average_price: float) -> float:
        """_fee, but a raising fee model gives 0.0 (logged): seeding a resumed order
        must never fail on its fee estimate."""
        try:
            return self._fee(order, filled, average_price)
        except Exception as e:
            self.logger.error(f"Fee estimate failed for resumed {order.symbol} "
                              f"signal_id={order.signal_id}; seeded with no fee: {e!r}")
            return 0.0

    def _resolve_unconfirmed(self, book: List[Dict]) -> List[str]:
        """Look each unconfirmed placement up in the order book. One found there
        moves to the poll; returns a problem for each tag found more than once."""
        problems = []
        for key, order in list(self._unconfirmed.items()):
            matches, _ = self._book_matches(book, order)
            if not matches:
                continue
            if len(matches) > 1:
                problems.append(
                    f"{len(matches)} Upstox orders carry the tag of signal_id={order.signal_id}: "
                    f"{matches}")
                continue
            del self._unconfirmed[key]
            self._pending[matches[0]] = (order, 0, 0.0, 0.0)
            message = (f"UNCONFIRMED PLACEMENT FOUND AT UPSTOX: {order.side.value} {order.quantity} "
                       f"{order.symbol} signal_id={order.signal_id} is order {matches[0]}; "
                       "its fills are polled from now on.")
            self.logger.error(message)
            alerter.critical(message)
        return problems

    def resume_orders(self, orders) -> ResumeResult:
        """Re-seed the poll after a restart.

        `orders` holds (order, filled quantity, average price) for each order the
        ledger shows placed today and not fully filled. Each is looked up in the
        order book by tag, side and quantity; one found there is polled from the
        quantity and average price the ledger already holds, so a fill it booked
        before the restart is not booked again (the fee already charged is
        re-estimated from the fee model). Returns the orders not found, those found
        more than once, and those whose tag the book holds on another side or
        quantity; none of them is polled. An order not found is watched: the poll
        checks the book for it every _WATCH_INTERVAL_S and adopts it if it
        appears (a placement that failed ambiguously may not be visible yet). One
        order book call; errors propagate.
        """
        orders = list(orders)
        if not orders:
            return ResumeResult()
        book = self._fetch_order_book(attempts=3, timeout=10)
        not_found, duplicated, mismatched = [], [], []
        for order, filled, average_price in orders:
            filled, average_price = int(filled), float(average_price)
            matches, other = self._book_matches(book, order)
            if len(matches) == 1:
                self._pending[matches[0]] = (order, filled, average_price,
                                             self._safe_fee(order, filled, average_price))
            elif matches:
                duplicated.append(order)
            elif other:
                mismatched.append(order)
            else:
                not_found.append(order)
                self._watch[str(order.correlation_id)] = (order, filled, average_price)
        return ResumeResult(not_found=not_found, duplicated=duplicated, mismatched=mismatched)

    def _raise_poll_problems(self, unavailable, contract, not_filled) -> None:
        parts = []
        if contract:
            parts.append("unusable reply: " + "; ".join(contract))
        if self._unconfirmed:
            parts.append("unconfirmed placement (may be live, was not resent): " + "; ".join(
                f"{o.side.value} {o.quantity} {o.symbol} signal_id={o.signal_id}"
                for o in self._unconfirmed.values()))
        if unavailable:
            parts.append("unreachable: " + "; ".join(unavailable))
        if not_filled:
            parts.append("not filled: " + "; ".join(e.description for e in not_filled))
        if not parts:
            return
        message = " | ".join(parts)
        if contract:
            error = BrokerContractError(message)
        elif self._unconfirmed:
            error = BrokerAmbiguousPlacementError(message)
        elif unavailable:
            error = BrokerUnavailableError(message)
        else:
            error = BrokerOrderNotFilledError(message)
        # A reject folded into a more severe error still has to reach the journal.
        error.not_filled = list(not_filled)
        raise error

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
        response = self._make_request("DELETE", "/order/cancel", params={"order_id": order_id},
                                      base_url=self.HFT_URL)
        # BrokerAuthError / BrokerUnavailableError propagate from _make_request
        return bool(response and response.get("status") == "success")
