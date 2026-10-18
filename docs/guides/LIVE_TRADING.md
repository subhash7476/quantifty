# Live trading — the switch, and what to check before using it

> **Off by default, off for both paper runners, and unproven.** Nothing in this
> repository routes a real order unless you write the code that asks for it. The live
> path through `UpstoxAdapter` was repaired on 2026-10-17. It has never placed a real
> order, and it still has known gaps (gap 0 below). No strategy here is validated for
> real money. Read the whole page first.

## Two independent settings

| Setting | Values | Decides |
|---|---|---|
| `Mode` (`core/runtime/config.py`) | `LIVE` / `REPLAY` | the clock and data: wall-clock live bars vs. replayed history |
| `ExecutionMode` (`core/execution/handler.py`) | `PAPER` / `LIVE` | the orders: `PaperBroker` synthetic fills vs. `UpstoxAdapter` real orders |

NiftyShield runs **`Mode.LIVE` + `ExecutionMode.PAPER`**: live Upstox data, synthetic
fills, no capital. Options-Wall reads live chains and simulates its trades in its own
paper executor, outside the execution layer, so it has no order mode at all.

## The switch

The live switch exists in exactly one place, the F&O composition root
`scripts/fno_runner.py::build_runner`. You pass it `ExecutionMode.LIVE` and a broker
(read gap 0 first):

```python
from core.brokers.upstox_adapter import UpstoxAdapter
from core.auth.credentials import credentials
from core.execution.handler import ExecutionMode
from core.clock import RealTimeClock
from scripts.fno_runner import build_runner

clock = RealTimeClock()
broker = UpstoxAdapter(api_key=credentials.get("api_key"),
                       api_secret=credentials.get("api_secret"),
                       access_token=credentials.get("access_token"),
                       clock=clock)
driver = build_runner(source=my_signal_source,          # your SignalSource
                      symbols=[...],               # instrument keys you trade
                      underlyings=[...],           # F&O only: see core/instruments/master_readiness.py
                      execution_mode=ExecutionMode.LIVE,
                      broker=broker, clock=clock)
driver.run()
```

`build_runner` **refuses to start** a LIVE run when:
- there is no signal source;
- `ExecutionMode.LIVE` is requested without a broker (it will not let a PaperBroker
  pass as live);
- the Upstox token is missing or expired;
- an F&O universe is given without `underlyings` (no instrument-master readiness or
  reconciliation);
- today's SPAN snapshot is missing (LIVE F&O blocks; PAPER only warns).

The SPAN and instrument-master checks run only when `symbols` contains F&O keys
(`NSE_FO|…` or `MCX_FO|…`).
A universe of index keys only (the way NiftyShield subscribes, trading options
through its handler) skips both.

When LIVE starts, it reconciles the restored ledger against the broker's actual
positions (`get_positions`) instead of the vacuous paper reconcile, and refuses to
start on a mismatch. It does not re-check during the session. The reconcile compares
positions only. So `build_runner` also sends a critical alert when the restored ledger
holds an order placed today that is not recorded as filled. The run still starts.
Nothing polls an order placed before a restart, and it may have filled since. It may
also be an order Upstox rejected or cancelled (gap 0), or one whose placement failed or
was refused: the handler records every order before it calls the broker and never closes
a failed one. No funded account exists, so none of this has run against a real
account.

**The paper runners cannot be flipped:**
- `scripts/nifty_shield_paper_runner.py` passes `ExecutionMode.PAPER` literally, and
  that file is inside NiftyShield's frozen execution hash.
- Options-Wall's executor has no broker path at all.

To trade live you write your own entry script around `build_runner`, with your own
`SignalSource`. Strategies only emit `SignalEvent`s; they never touch the broker.

## Known gaps in the live order path — read these

0. **The live broker path is repaired but unproven.** PR #47 (2026-10-17) fixed the
   three defects that stopped it, F-UPX-1/2/3. `UpstoxAdapter` had no
   `subscribe_fills`, so `build_runner` could not be built. It read a field
   `NormalizedOrder` does not have, and it sent every order as SELL. The PR also added
   fill polling (gap 3). A follow-up (2026-10-18) moved placement and cancellation
   to V3 on `api-hft.upstox.com`, kept the order tag within Upstox's 40-character
   limit, typed every definite refusal, and added the order-book lookups, the fee
   estimate and the `trades` tables (gap 3). The tests drive a real `UpstoxAdapter`
   with only the HTTP call stubbed. No Upstox order endpoint has been called. Still
   open (see `docs/reports/platform/PR45_PR47_CODE_REVIEW_2026-10-17.md`):
   - **An unexpected error is reported as placed (L2).** The handler counts
     `BrokerUnavailableError` and trips the kill switch on `BrokerAuthError`. Every
     definite refusal now raises `BrokerOrderRefusedError`, a `BrokerUnavailableError`,
     so it is counted and no order is returned. Any other exception from
     `place_order` is logged, and the order is returned as if it had been placed.
     `handler.py` is inside NiftyShield's frozen execution hash.
   - **A partially filled order keeps only its first chunk in `trades`.**
     `trades.signal_id` is unique, so a later chunk's insert fails, and the handler
     swallows the error. Positions and `fills` rows stay correct. A partial exit is
     recorded as a new entry, and the final chunk's exit is written to that row, so the
     real entry row is never closed.
   - **Rejected and cancelled orders stay open in the handler's `OrderTracker`.** The
     adapter raises a critical alert and the driver journals the event, but nothing
     tells the handler.
   - **Checked against Upstox's docs only (2026-10-18), never a live response:**
     - placement is `POST /v3/order/place` and cancellation `DELETE /v3/order/cancel`,
       both on `api-hft.upstox.com`. V2 place-order is marked deprecated there. Order
       details, the order book and positions stay on `api.upstox.com/v2`;
     - the tag: Upstox rejects one over 40 characters (error `UDAPI1119`). It is the
       handler's `signal_id` when that is at most 40 letters, digits, `_` or `-`,
       otherwise the first 40 hex digits of the signal_id's SHA-256. The handler's
       fallback signal_id is a 64-character digest, so it always takes the hash form;
     - the order book's response is documented both as a bare list and inside a
       `{"status": "success", "data": [...]}` envelope; both are accepted;
     - every other response shape follows Upstox's published examples.
1. **Multi-leg structures are not atomic.** `LoopDriver` routes every leg as its own
   `process_signal` call, so each leg passes the handler's risk, greek, margin and
   kill-switch gates only when its turn comes, then goes out as its own **MARKET**
   order. A leg rejected by one of those gates or by the broker is **logged and
   skipped** while earlier legs stand, so with shorts emitted before wings a rejected
   wing leaves a **naked short option**. (`process_group_signal`, which pre-checks
   all legs, has no caller on this path.) Upstox's multi-order API is not used.
2. **MARKET orders only**, for every order: `OrderType` has no limit member and
   `NormalizedOrder` carries no limit price. Upstox applies market
   price protection (MPP) to MARKET / SL-M orders; the adapter does not set
   `market_protection` itself.
3. **Live fills come from polling, and a placement is never resent.**
   - **The poll.** `LoopDriver` calls `UpstoxAdapter.poll_fills()` once per loop
     iteration. It also runs while paused or kill-switched, and once more at
     shutdown. Each pending order gets one `GET /order/details`: a single 3 s attempt
     with no backoff.
   - **Fills.** Each newly filled quantity becomes a `FillEvent`, priced so that the
     fills' VWAP equals Upstox's `average_price`. The fill is booked before the status
     is read. Nothing is booked when:
     - the reply is not a `success` object;
     - the filled quantity is missing, goes down, or exceeds the order;
     - a new fill has a missing or non-positive price.

     An unknown or missing status, or a `complete` order short of its quantity, still
     books the newly filled part. Either way the order stays pending, and the poll
     raises `BrokerContractError`, which counts as a failed poll. There is no
     re-pricing.
   - **Placement.** `POST /v3/order/place` on `api-hft.upstox.com` is sent **once**,
     unsliced, with a 10 s timeout.
     - **Unknown outcome.** It is unknown whether Upstox took the order after a
       timeout, a dropped connection, a 5xx, or a 200 reply that is unreadable or
       reports success without exactly one order id. The adapter raises
       `BrokerAmbiguousPlacementError`, sends a critical alert and holds the order as
       unconfirmed. The handler returns no order.
     - **Looking it up.** Each later poll looks the order up in the order book
       (`GET /order/retrieve-all`) by its tag. Once it is found there, a critical alert
       names its order id and its fills are polled like any other order's. While it
       is not found, the poll fails, so the kill switch latches within three
       iterations and stays latched until a restart.
     - **Definite refusal.** A 4xx, a 200 reply with status `error`, or an order the
       adapter cannot route (no instrument mapping, an unmappable side, a non-MARKET
       type) raises `BrokerOrderRefusedError`. A 429 raises `BrokerUnavailableError`.
       Neither is retried. Both count toward the handler's three consecutive failed
       placements, which latch the switch until restart. A 401/403 latches it at once.
   - **Fees.** Order details carry no charges. Each fill carries the handler's own fee
     schedule (`_calculate_fees`, set by `build_runner`) for the quantity filled so
     far, less what earlier fills of the order carried, so a partly filled order pays
     the flat brokerage once. It is an estimate; Upstox's actual charges are not read.
   - **Restart.** The ledger records an order before it is sent. At a LIVE start,
     `build_runner` hands the adapter every order from today that the ledger shows
     not fully filled. Each is looked up in the order book by its tag and polled from
     the quantity the ledger already holds, so nothing is booked twice; a reject or
     cancel among them is reported by the first poll. An order not in the book never
     reached Upstox and gets a warning. If the order book can't be read, nothing
     polls those orders, and the alert is critical.
   - **Kill switch from the poll.** Three consecutive outage polls trip a releasable
     kill switch, lifted by the first clean poll unless the data feed is stale. An
     auth failure trips it at once and ends polling. Any other repeated failure
     latches it until restart.
4. **Basket-margin sizing** (`POST /v2/charges/margin`) is a pre-trade estimate. The
   broker RMS is the authority that accepts or rejects the order.

## Upstox / SEBI requirements for API orders (verify before going live)

From **1 April 2026** (SEBI retail-algo framework, NSE circular NSE/INVG/67858),
Upstox requires:

- **A registered static IP.** Place, modify and cancel order calls (and multi-order
  and GTT) must come from the static IP registered on your app. Calls from other IPs
  may be blocked. A home connection with a dynamic IP will not work for live orders.
  Paper trading is unaffected, because market data, option chains and the margin API
  are not order calls.
- **One active API app per user.** If you create a new app, the older ones are
  deleted.
- **Exchange algo registration above 10 orders per second.** This platform places a
  handful of orders per session.

Rules change. Check the primary sources yourself:
- Upstox: [Algo registration & static IP requirement](https://upstox.com/developer/api-documentation/announcements/algo-trading-circular),
  [Configure static IPs](https://upstox.com/developer/api-documentation/appendix/my-apps-support-for-algo-trading-circular/),
  [community announcement](https://community.upstox.com/t/important-new-sebi-exchange-mandates-for-api-trading-effective-1st-april-2026/14822)
- NSE: [circular INVG67858](https://nsearchives.nseindia.com/content/circulars/INVG67858.pdf)

## Checklist before the first real order

- [ ] Static IP registered on your Upstox app, and the trading machine egresses from it
- [ ] Your strategy has its own out-of-sample evidence. Paper results here are not evidence.
- [ ] You have read [NIFTY_SHIELD.md](NIFTY_SHIELD.md) / [OPTIONS_WALL.md](OPTIONS_WALL.md) known limitations if you derived from them
- [ ] Multi-leg risk handled: wings first, or a broker-side basket, or defined-risk only
- [ ] `python scripts/ops/preflight.py` is GO and the SPAN file is present
- [ ] The kill switch is understood:
  - **The `STOP` file** blocks orchestrator starts. In a running handler, the first signal processed while the file exists latches the kill switch until restart. Deleting the file does not re-enable entries, and exits still go through. The handler looks for the file in the working directory, so run from the repo root.
  - **A stale feed** trips the kill switch only if you pass `build_runner` a `watchdog_factory`, for example `lambda ex: RuntimeWatchdog(ex)` with `RuntimeWatchdog` from `core.execution.watchdog`. It writes `logs/heartbeat.json`, which **/ops/** reads; `scripts/nifty_shield_paper_runner.py` passes its own `heartbeat_path`. The snippet above passes none, so its run has no stale-feed trip.
  - **Auth and broker failures:**
    - an auth failure, from a placement or a poll, latches it at once;
    - an unresolved placement latches it within three loop iterations;
    - three failed placements in a row latch it, definite 4xx refusals and 429s included;
    - three failed polls in a row latch it, unless the last was a pure outage. An outage trips a releasable switch instead, lifted by the first clean poll, or by the feed's recovery if the feed was stale at that poll.

    Every latch holds until restart.
- [ ] Every open item in gap 0 is fixed, or you accept it. You have checked the order host, API version, `tag` rule and response shapes against a live response.
- [ ] You know how to reconcile your positions against the Upstox order book after an ambiguous placement or a restart
- [ ] Start with the minimum size, and watch the first session in the Upstox app
- [ ] Holidays: `core/market/nse_holidays.py` and `trading_calendar.py` cover the year you are trading in (and `strategies/nifty_shield_v1/exchange_holidays.py`, if you derived from NiftyShield)
