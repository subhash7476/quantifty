# Live trading — the switch, and what to check before using it

> **Off by default, off for both paper runners, and not finished.** Nothing in this
> repository routes a real order unless you write the code that asks for it, and
> today the Upstox order call fails even then (gap 0 below). No strategy here is
> validated for real money. Read the whole page first.

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
(but read gap 0 first: the order call behind it does not work yet):

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

The SPAN and instrument-master checks run only when `symbols` contains NSE F&O keys.
A universe of index keys only (the way NiftyShield subscribes, trading options
through its handler) skips both.

When LIVE starts, it reconciles the restored ledger against the broker's actual
positions (`get_positions`) instead of the vacuous paper reconcile, and refuses to
start on a mismatch. It does not re-check during the session.

**The paper runners cannot be flipped:**
- `scripts/nifty_shield_paper_runner.py` passes `ExecutionMode.PAPER` literally, and
  that file is inside NiftyShield's frozen execution hash.
- Options-Wall's executor has no broker path at all.

To trade live you write your own entry script around `build_runner`, with your own
`SignalSource`. Strategies only emit `SignalEvent`s; they never touch the broker.

## Known gaps in the live order path — read these

0. **The Upstox order call does not work yet.** `UpstoxAdapter.place_order` expects
   an `OrderEvent`, but `ExecutionHandler` sends a `NormalizedOrder`. It reads
   `order.signal_id_reference`, which `NormalizedOrder` does not have, so it raises
   before any HTTP call; and it compares the side enum to the string `"BUY"`, so
   every order would go out as SELL. The handler catches the error, logs it, and
   returns the order as if it had been placed (group legs are logged and skipped).
   These are findings F-UPX-1/2 in `tests/execution/test_g1_characterization.py`.
   Fix and test them before anything else on this page matters.
1. **Multi-leg structures are not atomic.** `ExecutionHandler.process_group_signal`
   risk-checks every leg, then sends each leg as its own **MARKET** order, one after
   another. A leg that the broker rejects is **logged and skipped**. With shorts emitted
   before wings, a rejected wing leaves a **naked short option**. Upstox's multi-order
   API is not used.
2. **MARKET orders only** for group legs, with no limit price. Upstox applies market
   price protection (MPP) to MARKET / SL-M orders; the adapter does not set
   `market_protection` itself.
3. **No re-pricing or partial-fill management.** Order status comes from the broker's
   order-details endpoint; the adapter retries transport errors with backoff, nothing more.
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
- [ ] The kill switch is understood: the `STOP` file at the repo root blocks starts, and a stale feed trips the kill switch
- [ ] Start with the minimum size, and watch the first session in the Upstox app
- [ ] Holidays: `core/market/nse_holidays.py` and `trading_calendar.py` cover the year you are trading in (and `strategies/nifty_shield_v1/exchange_holidays.py`, if you derived from NiftyShield)
