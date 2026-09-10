# Options-Wall trade detail panel — design

**Date:** 2026-09-10
**Branch:** `feat/options-wall-trade-detail-panel`
**Status:** approved, ready for implementation

## Problem

The Options-Wall paper-trades table (`/options/wall/`) renders one dense row per fly.
Everything else the platform already knows about a trade is invisible: fee split, max
loss, return-on-margin, exit reason, exit legs, and the regime/signal state that caused
the executor to open it. For an open trade there is no way to see what each leg is
actually quoting right now — only a single collapsed mid per leg.

`/api/trades` already returns `entry_fees`, `exit_fees`, `gross_pnl`, `max_loss`,
`return_on_margin`, `exit_reason`, `expiry` and `exit_legs`; the template parses none
of them. `exit_legs` in particular is persisted by `close_paper_trade`, serialised by
the endpoint, and rendered nowhere.

## Goal

Clicking any trade row — open or closed — opens a right-hand side panel with the full
detail of that trade. For an open trade the panel shows live per-leg quotes and marks,
updating on the page's existing poll.

## Non-goals

- No P&L-since-entry chart. (Considered; the 5 s snapshot history supports it, but it
  needs a new history endpoint and was explicitly scoped out.)
- No new writes. The poller remains the results DB's sole writer.
- No refactor of `index.html` into separate asset files. Inline `<style>`/`<script>` is
  this file's existing convention.

## Data path

Three options were considered:

| | Approach | Verdict |
|---|---|---|
| A | Live fields ride the existing `/api/trades` poll; one new `/api/trade/<id>/context` fetched once per panel open and cached client-side | **chosen** |
| B | One fat `/api/trade/<id>` returning live + context, polled while the panel is open | rejected — double-fetches live data the page already holds, adds a second poll against files the poller is writing |
| C | Widen `/api/trades` to embed context on every row | rejected — joins `session_regime` + `scan_results` for every trade on every 7 s poll to serve one open panel |

Entry context is immutable once the trade is open, so it is fetched once. Live marks
already refresh every 7 s via `loadTrades()`.

## Components

### 1. Live leg quotes — `core/options_wall/engine.py`

`_snapshot_mids` collapses `best_bid`/`best_ask` into a single float and discards IV,
greeks, OI and volume. Widen it to `_snapshot_quotes`, keyed the same
`(strike, option_type)`, with value:

```
{mid, bid, ask, ltp, iv, delta, gamma, theta, vega, oi, volume}
```

`mid` keeps its current definition exactly: bid/ask mid when both are positive, else LTP
when positive, else the quote is absent.

`_open_trade_marks` uses `q["mid"]` for the mark arithmetic — **mark, unrealized P&L and
the complete/incomplete rule are unchanged by construction** — and attaches the full
quote dict to each entry of `current_legs`.

`trades_view` additionally returns `quote_ts`: the newest snapshot timestamp for the
underlying, via the existing `store.snapshot_timestamps`. The blueprint serialises it
alongside `trades` so the panel can age its quotes instead of asserting "live" blindly.

### 2. Entry context — `core/options_wall/persistence.py`, `engine.py`, blueprint

Two read-only helpers, both resolving the row at-or-nearest-**before** the trade's
`entry_ts`, restricted to the same trade date:

- `regime_at(underlying, ts)` → one `session_regime` row (regime, pin strike, pin
  conviction, put/call wall, net GEX, ATM IV, realized vol, underlying LTP, sigma).
- `signal_at(underlying, ts)` → the `scan_results` rows of that cycle (screen,
  structure, score, credit, `iv_minus_rv`, `pin_conviction`, reason).

The executor fires on a scan cycle, so nearest-before resolves to the cycle it acted on.
Both return `None`/`[]` when the trade predates the relevant table.

`engine.trade_context(index, trade_id)` composes the two into one payload.

New endpoint, read-only like the rest of the blueprint:

```
GET /options/wall/api/trade/<int:trade_id>/context?index=NIFTY
```

### 3. Panel — `flask_app/templates/options_wall/index.html`

A right slide-over (~460 px) with backdrop.

**Placement constraint:** the panel node is a **sibling of `#trades-body`, never inside
it.** `paintTrades()` rebuilds that node's `innerHTML` wholesale every 7 s; a nested
panel would be destroyed on each poll.

**Interaction:**
- Row click → `openTradePanel(trade_id)`.
- The Exit button calls `event.stopPropagation()` so closing a trade does not also open
  the panel.
- `paintTrades()` re-renders an open panel from the fresh row, so an open trade's marks
  tick in place.
- Esc, backdrop click, and an explicit × all close it.
- State: `state.panelTradeId`, `state.contextCache` (keyed by `trade_id`).

**Sections:**

1. **Header** — OPEN/CLOSED chip, `#trade_id`, index, structure (`short_strike`, wings),
   expiry.
2. **Live** (open) — index spot from `state.regime.underlying_ltp`, current mark,
   unrealized P&L, quote age, market-phase badge.
   **Result** (closed) — exit time, exit reason, gross vs net P&L, return-on-margin,
   duration held.
3. **Legs** — four rows. Open: entry mid → live bid / ask / LTP / mid / IV / delta /
   theta. Closed: entry mid → exit mid, parsed from `exit_legs`.
4. **Economics** — net credit, entry fees, exit fees, max loss, qty.
5. **Entry context** — regime, pin strike + conviction, walls, net GEX, IV−RV, signal
   score and reason. Renders a plain "not recorded" line when the helpers return empty.

## Correctness constraints

**Staleness is displayed, not assumed.** The panel prints quote age and a market-phase
badge derived from `MarketHours.is_derivatives_open()`. Since CAS (2026-08-03) the feed
rebroadcasts a stale LTP through 15:15–15:40 while snapshot timestamps keep advancing —
so age alone cannot detect it, and the phase label is the honest signal. A price
presented as live must carry its age.

**The null-mark state gets explicit copy.** `_open_trade_marks` returns
`(None, None, legs)` if *any* leg is unquoted, and `trades_view`'s `except` blanks every
mid for that expiry on a read collision with the poller. In a table row that degrades to
a quiet `—`; in a detail panel it must say which case it is — "unquoted this cycle"
versus "market closed" — decided from `MarketHours`.

## Testing

`tests/options_wall/`:

- `test_engine_snapshot.py` — the widened quote shape; and that mark / unrealized P&L
  are byte-identical to the pre-change values for the same snapshot input (the
  invariance is the point of the refactor).
- `test_trades_persistence.py` — `regime_at` / `signal_at` nearest-before semantics,
  including the same-trade-date restriction and the empty-table case.

## Risks

- Widening `_snapshot_quotes` touches the mark path shared by the live executor's view.
  Mitigated by the invariance test above; the mark arithmetic itself is not edited.
- `store.snapshot_timestamps` runs a `DISTINCT` over the day's rows once per
  `trades_view` call (every 7 s). The store carries no secondary index by deliberate
  design; DuckDB scans a single day file (<600 k rows) in milliseconds.
- `index.html` is already 1,247 lines against the repo's 800-line guidance and this adds
  to it. Splitting it is out of scope and was not requested.
