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
   fill polling (gap 3). Its tests drive a real `UpstoxAdapter` with only the HTTP
   call stubbed. No Upstox order endpoint has been called. Still open (see the PR and
   `docs/reports/platform/PR45_PR47_CODE_REVIEW_2026-10-17.md`):
   - **Some broker errors are reported as placed (L2).** The handler counts
     `BrokerUnavailableError` and trips the kill switch on `BrokerAuthError`. Any
     other exception from `place_order` is logged, and the order is returned as if it
     had been placed. Examples are an explicit refusal in a 200 reply, or an
     unmappable side. `handler.py` is inside NiftyShield's frozen execution hash
     until the E008 window ends.
   - **A partially filled order keeps only its first chunk in `trades`.**
     `trades.signal_id` is unique, so a later chunk's insert fails, and the handler
     swallows the error. Positions and `fills` rows stay correct. A partial exit is
     recorded as a new entry, and the final chunk's exit is written to that row, so the
     real entry row is never closed.
   - **Rejected and cancelled orders stay open in the handler's `OrderTracker`.** The
     adapter raises a critical alert and the driver journals the event, but nothing
     tells the handler.
   - **Live fills carry `fee=0.0`.** Upstox order details carry no charges, so live
     P&L and the drawdown gate see no costs.
   - **`fno_runner` does not create the `trades` table** (the NiftyShield session
     does). A LIVE run on a fresh machine writes no `trades` rows.
   - **Pending orders live only in adapter memory.** Nothing re-seeds them from the
     Upstox order book after a restart, and nothing looks up an ambiguous placement
     (gap 3) by its tag.
   - **Not checked against Upstox:**
     - the adapter uses `api.upstox.com/v2`, while Upstox's docs show the order
       endpoints on `api-hft.upstox.com` and mark V2 place/cancel deprecated in
       favour of V3;
     - the maximum `tag` length is undocumented. The tag is the handler's
       `signal_id`: the source's `metadata["signal_id"]` if it sets one, otherwise a
       64-character SHA-256 hex digest;
     - response shapes follow Upstox's published examples, not a captured live
       response.
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
   - **Placement.** `POST /order/place` is sent **once**, with a 10 s timeout.
     - **Unknown outcome.** It is unknown whether Upstox took the order after a
       timeout, a dropped connection, a 5xx, or a 200 reply that is unreadable or
       reports success without an `order_id`. The adapter raises
       `BrokerAmbiguousPlacementError`, sends a critical alert and holds the order as
       unconfirmed. The handler returns no order. Every later poll fails on it, so the
       kill switch latches within three iterations and stays latched until a restart.
       Check the order against the Upstox order book.
     - **After a restart.** The unconfirmed order's fill is never polled. If it
       filled, the ledger is missing that fill, and the LIVE startup reconcile refuses
       every restart until the ledger and the Upstox positions agree.
     - **Definite refusal.** A 4xx or a 429 raises `BrokerUnavailableError` and is not
       retried. It counts toward the handler's three consecutive failed placements,
       which latch the switch until restart. A 401/403 latches it at once.
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
- [ ] Every open item in gap 0 is fixed, or you accept it. You have checked Upstox's current order host, API version and `tag` length.
- [ ] You know how to reconcile your positions against the Upstox order book after an ambiguous placement or a restart
- [ ] Start with the minimum size, and watch the first session in the Upstox app
- [ ] Holidays: `core/market/nse_holidays.py` and `trading_calendar.py` cover the year you are trading in (and `strategies/nifty_shield_v1/exchange_holidays.py`, if you derived from NiftyShield)
