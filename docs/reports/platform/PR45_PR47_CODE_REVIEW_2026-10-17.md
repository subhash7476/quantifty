# Code review: PR #45 and PR #47 — 2026-10-17

**Scope.**
- **PR #45** (`claude/priceless-engelbart-60d190`, f5e766c): the Options-Wall `PaperExecutor` refuses new entries while the repo-root `STOP` file exists.
- **PR #47** (`claude/vigorous-chandrasekhar-207f58`, cb27cf9): it fixes F-UPX-1/2/3 in `UpstoxAdapter`, adds `poll_fills`, and adds a live-only `fill_poll` hook to `LoopDriver`, wired by `build_runner`.

**Method.**
- **Reviewers:** four, one per angle (#45; #47 adapter; #47 runtime; #47 tests), each in a read-only checkout of the PR branch. They reproduced findings with scratch probes that stub only `requests.request`; no repo file was edited and no network call was made.
- **Skeptics:** every finding then went to skeptics told to refute it (two for high or critical, one otherwise). 26 findings went in; 21 survived and 5 were refuted. Overlapping findings are merged below.
- **Tests:** run separately on each branch.
  - **#45:** `tests/options_wall` 123 passed.
  - **#47:** brokers, runtime, scripts, execution, nifty_shield_paper, risk and ops gave 1418 passed and 10 failed. The same 10 fail on clean `main` because the checkout has no instrument master or futures store.
- **E008:** both branches hash to `101bae72…`, and neither touches a file in `EXECUTION_GLOBS`.

## Verdict

- **#45: mergeable.** Its three findings are all low, and two are test-only. The STOP gate itself is correct: it covers every entry path (`open_paper_trade` has one caller) and never blocks an exit (TP, SL, the time stop, manual close).
- **#47: fix A–D before merging.** No production caller uses `ExecutionMode.LIVE` today, so merging cannot affect NiftyShield or any paper run; `fill_poll` is `None` on every existing construction site. But the PR's purpose is a live path that works. As written, A can put a second real order on the book that the ledger never sees, and B–D can lose or mis-price real fills without anyone noticing.

## PR #47 findings (survived refutation)

| # | Sev | Finding | Where | Fix |
|---|---|---|---|---|
| A | **high** | **A placement can be duplicated.** `place_order` goes through `_make_request`, which retries any `RequestException`. That includes a ReadTimeout after Upstox has already accepted the order, and a 5xx raised by `raise_for_status`. The resend places a second order, and only the last order id enters `_pending`, so the first order's fill is never polled. The retry code predates the PR; the PR is what makes it reachable from `ExecutionHandler`. Reproduced by two reviewers; all 4 skeptics upheld it at high. | `core/brokers/upstox_adapter.py:184` (→ `_make_request` retry loop) | Never resend `POST /order/place`. On a timeout or 5xx, raise a distinct ambiguous-placement error. Before any resubmit, look the order up in the order book by `tag == signal_id`. Add a stub test that routes `[ReadTimeout, placed]` and asserts exactly one POST. |
| B | medium | **One bad order starves every other order's fills.** `poll_fills` catches only `BrokerUnavailableError` per order. A `BrokerContractError` aborts the whole sweep: an unknown status string, a non-success envelope or a malformed field. A `null` status escapes as a raw `AttributeError`, because `.lower()` runs outside the try block. The bad order stays first in `_pending`, so every later order (including exits placed after the kill-switch trip) is never polled. `DRIVER_SPECIFICATION.md` §12.1 says the opposite ("polling continues so fills of earlier orders are still recorded"). | `upstox_adapter.py:217, 243`; `docs/DRIVER_SPECIFICATION.md:502` | Catch contract errors per order the way `deferred` already handles unavailability, and raise one aggregate error at the end. Move the status lookup inside the try block and treat `None` as an error. Emit the filled-quantity delta before resolving the status. Correct §8.3/§12.1. |
| C | medium | **A missing or zero `average_price` books a fill at price 0.** `float(data.get('average_price') or 0.0)` and the VWAP back-out turn it into a `FillEvent` priced 0.0. Cost basis, P&L, equity and the drawdown gate are all wrong, with no warning. After a 0-priced chunk, the next chunk is booked at an inflated price. | `upstox_adapter.py:212, 250` | When `filled > reported`, require `average_price > 0`. Otherwise raise `BrokerContractError` and keep the order pending without emitting. |
| D | low–medium | **A `complete` order with a missing or short `filled_quantity` is dropped silently.** `int(... or 0)` reads it as 0, no fill is emitted, and the order is deleted from `_pending`. An error is logged only for non-FILLED terminal states. The position never reaches the ledger. | `upstox_adapter.py:211, 265` | Treat a missing field as a contract error. On FILLED, require `filled == order.quantity`, otherwise raise and keep the order pending. Add tests. |
| E | low | **A broker reject or cancel is only logged.** There is no alert, journal event or handler notification, so the handler's `OrderTracker` keeps the order open. Example: a rejected hedge leg next to a filled short leg leaves an unhedged short, with one log line as the only trace. | `upstox_adapter.py:265-270` | Call `alerter.critical` on a non-FILLED terminal status, and surface the event to the driver (a typed error after the sweep, or a status callback). |
| F | low | **Auth failures are journaled every iteration, not once per incident.** The `BrokerAuthError` branch emits `BROKER_ERROR` and re-activates the kill switch on every iteration. With a dead token and any order pending, that is a 401 call every 0.5 s and a journal line each time. The spec and docstring say "edge-triggered". `test_auth_failure_trips_the_kill_switch_at_once` raises only once, so it passes for the wrong reason. | `core/runtime/driver.py:700`; `tests/runtime/test_driver_fill_poll.py:164` | Gate on the first failure of the incident, as the generic branch already does. Consider stopping polling after an auth trip. Make the test fail on every poll and assert exactly one event. |
| G | low | **The spec over-claims startup reconciliation.** It says reconciliation catches orders lost across a restart. It compares positions only, so an order still open at shutdown that fills after the restart is never ingested. The in-memory `_pending` limit itself is declared in the PR; the spec text is what is wrong. | `docs/DRIVER_SPECIFICATION.md:344` | Rewrite the bullet. Optionally, at LIVE start, refuse or alert when the restored tracker holds non-terminal orders, or re-seed `_pending` from the order book by tag. Also consider one final poll at shutdown. |
| H | low | **The poll can stall the single-threaded loop during an outage.** Each pending order costs up to 3 attempts × 10 s timeout plus 3 s of backoff, so about 33 s per order per iteration. Bars, exits, the watchdog and telemetry wait meanwhile. | `upstox_adapter.py:243` → `_make_request` | Give the poll path a single short attempt with no backoff (the next iteration is the retry), or fetch the whole order book in one request. |

**Refuted (not listed above):**
- 4xx responses being retried and classed as unavailable: unchanged behaviour that predates the PR.
- `fee=0.0` on live fills, and `_pending` living only in memory: both declared in the PR as remaining work.
- The kill-switch test not checking which mechanism tripped: a skeptic showed it already fails when the fill-poll trip is removed.
- The 200-only HTTP stub: a coverage gap, not a defect.

**Not verified (reviewer note, no skeptic pass):** with an order pending, about three poll intervals of outage trip the hard, non-releasable kill switch. That is the same "latch outlives the fault" pattern `CLAUDE.md` records for 2026-10-06; only stale-data trips are releasable. Decide deliberately whether a fill-poll outage should latch.

## PR #45 findings (all low)

| # | Finding | Where | Fix |
|---|---|---|---|
| 1 | **The Options-Wall badge says "Tradeable" while `STOP` blocks every entry.** `tradeability()` promises to mirror `PaperExecutor.step`, but it gained no STOP check. This is the trade-31 failure the badge was built to prevent: an operator closes a fly by hand expecting to re-enter on a visible row. | `core/options_wall/tradeability.py:52`; `flask_app/blueprints/options_wall.py:60` | Add a `stop_present` input and a `kill_switch` state after the window checks, a badge entry, and a test. |
| 2 | **Existing executor tests read the live `STOP` file.** About 20 tests build `PaperExecutor` with the default `ROOT/STOP`. With the operator's kill switch engaged in `F:\Nifty`, 11 of them fail, and the "no entry" tests pass vacuously. | `core/options_wall/paper_executor.py:73` | Add an autouse fixture in `tests/options_wall/conftest.py` that points the default at a tmp path. A module-level `STOP_FILE` constant makes that easy. |
| 3 | **The log-latch reset is untested.** Replacing `_stop_logged.discard(...)` with `pass` leaves all 29 tests green: the test's second STOP episode starts with a fly already open, so it never reaches the latch. | `tests/options_wall/test_paper_executor.py:389` | Clear the latch with a flat step that opens no fly, then assert two log records across two episodes. |

## What was clean

- **#45:**
  - Every entry path is gated.
  - Exits and manual close are never gated.
  - The STOP path matches the orchestrator's, ExecutionHandler's and the /ops/ kill button's when started under the orchestrator.
  - Snapshots, scan trail and regime writes continue while stopped.
  - The poller construction is unchanged.
- **#47:**
  - Fill idempotence within a process (cumulative `filled_quantity`, `fill_id = order-filled`).
  - The status map now matches Upstox V2 (`complete`, not `completed`).
  - `FillEvent` keys use the handler's `correlation_id`.
  - No import cycles, and no other `BrokerAdapter` subclass breaks.
  - No existing caller regresses (nothing in production constructs `UpstoxAdapter`).
  - No assertions were weakened.
  - Test isolation: every adapter test stubs HTTP, and unrouted calls fail.
  - `fill_poll` is `None` on every PAPER, REPLAY and NiftyShield construction site.

## Re-check after fixes (same day)

Each PR's session fixed its findings. Both new heads were checked out clean (detached worktrees) and re-verified. Both were then merged to `main` on 2026-10-17: #45 as `da4f78d`, #47 as `7391089`. On `main` after both merges, the E008 hash is `101bae72…` and `orchestrator.py start --dry-run` gives the usual plan.

**#45 → 2085e68.**
- **Finding 1 (badge):** `tradeability()` takes `stop_present` and returns a `kill_switch` state, checked after the entry window. That matches `step()`, which tests STOP last before opening a fly. `api_farm` reads `paper_executor.STOP_FILE`, and the badge map has a red "Kill switch" entry.
- **Finding 2 (test isolation):** `STOP_FILE` is a module constant, and an autouse fixture in `tests/options_wall/conftest.py` points it at `tmp_path`.
- **Finding 3 (latch reset):** the test clears the latch with a 15:20 flat step, which opens no fly, then asserts two log records.
- **Tests:** `tests/options_wall` 125 passed, and still 125 passed with a real `STOP` file in the checkout root.
- **E008:** hash `101bae72…` matches, and no `EXECUTION_GLOBS` file is touched.

**#47 → a4ea0f8** (0640673 + a4ea0f8 on top of the reviewed cb27cf9).

| # | Fix as landed |
|---|---|
| A | `POST /order/place` makes one attempt (`attempts=1`, `ambiguous_on_failure=True`). These raise `BrokerAmbiguousPlacementError`: a timeout, a dropped connection, a 5xx, an unreadable 200, or a success reply with no `order_id`. A 4xx stays a definite refusal. The order is held in `_unconfirmed` with `alerter.critical`, and every later poll fails on it, so the driver hard-trips. The order-book lookup by tag was not built, because the Upstox docs contradict themselves on the response shape. |
| B | Every pending order is polled. Contract errors are collected per order and raised once after the sweep as the most severe kind. A null or non-text status is a `BrokerContractError`. The filled delta is emitted before the status is read. |
| C | A new fill requires `average_price > 0`, and the backed-out chunk price must also be positive. Otherwise the order stays pending and nothing is emitted. |
| D | `filled_quantity` must be present, whole and within `reported..order.quantity`. `complete` with less than the full quantity is a contract error, and the order stays pending. |
| E | A reject or cancel fires `alerter.critical` and raises `BrokerOrderNotFilledError`. The driver journals it every time without counting it as a failure. One that rides on a more severe error is still journaled, via `.not_filled`. |
| F | An auth failure gives one journal line and one hard trip, and polling stops (`_fill_poll_halted`). |
| G | The spec bullet is rewritten (reconciliation compares positions only). The driver polls once more at shutdown. `build_runner` alerts at a LIVE start when the ledger holds a same-day order not recorded as filled. |
| H | Each poll is one 3 s attempt with no backoff. The sweep stops at the first unreachable order and rotates it to the back. |
| Latch note | A pure outage (`type(exc) is BrokerUnavailableError`, exact type) trips a **releasable** switch, lifted by the first clean sweep unless the data feed is stale. Everything else latches hard, including ambiguous placements (a subclass). Checked against the frozen handler: `activate_kill_switch` never downgrades a hard trip, and `release_kill_switch` refuses while one is active. So the poll can only ever lift its own outage trip. |

- **E008:** hash `101bae72…` matches, and no `EXECUTION_GLOBS` file is touched.
- **Tests:** 1468 passed and 10 failed across brokers, runtime, scripts, execution, nifty_shield_paper, risk and ops. The pre-fix run had 1418 passed. The 10 failures are the same 10 that fail on clean `main` (no instrument master or futures store in the checkout).
- **Residual (low, not a blocker):** an ambiguous placement goes through the handler's `except BrokerUnavailableError` branch. That branch returns `None`, not the order, and counts toward the threshold; it does not trip at once. The rest of the same symbol sweep can still place orders, for example the next leg of a structure routed leg by leg (`LIVE_TRADING.md` Gap 1). The hard trip follows within `broker_error_threshold` (3) poll iterations, about 1.5 s of idle ticks. Tripping at once would need a handler change, which is inside E008.
- **Still open, declared in the PR body:**
  - the handler returns the order on a generic broker exception (L2);
  - rejected and cancelled orders stay open in `OrderTracker`;
  - a second partial fill fails the unique `trades.signal_id` insert;
  - live fills carry `fee=0.0`;
  - `fno_runner` does not create `trades`;
  - nothing re-seeds the poller from the broker order book.
