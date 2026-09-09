# NiftyShield — broker margin, 15:35 exit, and the stale session panel

**Date:** 2026-09-08 · **Branch:** `fix/options-wall-tp-sl-thresholds`

**Operator requests:** (1) size NiftyShield on the Upstox margin API, as options-wall
does; (2) stop time-exiting at 15:15 — hold to the strategy's own TP/SL until 15:35;
(3) the dashboard reported a prior-day structure under "this session".

---

## 1. Margin now comes from the broker's basket, not the local engine

### The defect this removes

With no SPAN snapshot for the day, `NseMarginEngine` degrades to the flat-rate
`MarginTracker`, which prices 20% of premium notional. On the 2026-09-07 bear call
spread it returned **Rs 4,619** against the broker's **Rs 79,902** — a 17x
understatement. A sizing clamp that understates margin 17x is not a conservative
approximation of a broker RMS; it is a gate that cannot fire.

### What changed

`NiftyShieldExecutionHandler._enter_structure` sizes the structure against
`POST /v2/charges/margin` — one call for the **whole structure** per lot count, so
the figure carries the spread benefit a hedged book actually earns. A per-leg sum
cannot express that benefit. This is the same call `/options-wall/api/margin` makes,
with the same `product="D"`.

| Seam | Change |
|---|---|
| `nifty_shield_marks.py` | `OptionMarksSource.instrument_keys(symbols)` — default `{}`; `ChainSnapshotMarksSource` resolves broker keys from the latest snapshot |
| `nifty_shield_sizing.py` | `structure_margin_over_upstox_basket(...)` returning `Callable[[int], float]`, memoised per lot count; `UpstoxMarginUnavailable` |
| `nifty_shield_handler.py` | `use_broker_margin` construction flag; `_structure_margin_fn` selects basket vs engine; `_journal_margin` records the figure actually used |
| `nifty_shield_paper_runner.py` | LIVE opts in; REPLAY does not |

**Live verification** (2026-09-08, real broker call, ATM bear call spread
23650/23800 CE at lot size 65):

```
lots 1 -> Rs 36,430.29
lots 2 -> Rs 72,865.26
final_lots @ budget Rs 250,000 -> 1
```

### Two deliberate design decisions

**Failure skips the entry; it never degrades.** `fetch_basket_margin` returns an
`error` field rather than raising. Falling back to the local engine on that error
would reproduce the exact 17x understatement this path exists to remove, and would
do it silently — the repo's documented "a swallowed failure becomes a fact about
the world" pitfall. A basket the broker cannot price journals `ENTRY_SKIPPED` at
CRITICAL and the structure is not entered.

**The margin authority is a composition decision, never inferred.** REPLAY, the
smoke run and the tests use `StaticMarksSource`, which has no broker identity.
Inferring the authority from "does this source happen to carry instrument keys"
would make *no broker session* silently mean *size it locally* — the same fallback,
one layer down. So `use_broker_margin` is an explicit constructor flag: LIVE passes
`True`, REPLAY passes `False`, and `ENTRY_MARGIN.engine` records which authority
priced each entry (`UpstoxBasketMargin` vs the engine class name).

### ADR conflict, stated

CLAUDE.md ADR-011/012/013 make `NseMarginEngine` the **sole sizing authority in
every mode**, and say broker margin is a deferred LIVE-only capability. This change
departs from that for NiftyShield's live path, by operator decision, on the
empirical ground above. No `MarginProvider` abstraction was built — it is one
concrete call, per the same ADR note. `span`/`elm` are journalled as `None` under
the basket: Upstox does not decompose the figure, and inventing a split would be
worse evidence than admitting there is none.

---

## 2. The hard exit moves 15:15 to 15:35

### Why 15:15 was wrong, and what the bars actually show

15:15 is the **cash** Category-I close. This book is F&O, and the derivatives
segment trades to **15:40** post-CAS (`core/market/session_schedule.py`). Option
premia keep decaying the whole time; the old rule cut every trade at another
segment's close.

Investigating why no bars arrive after 15:30 (2026-09-07, `NSE_INDEX|Nifty 50`):

```
15:15  23760.30   <- last real print
15:16  23760.30   \
...    23760.30    |  13 carry-forward bars (identical close, no trades behind them)
15:28  23760.30   /
15:29  23779.15   <- the auction print = the official close
(nothing after 15:29)
```

This is **not an ingestion defect**. It is the documented CAS pattern: the 1m store
is built from the cash feed, the Nifty 50 index is computed from cash constituents,
and there is no cash trading after the 15:29 auction. Every equity symbol in that
file ends at 15:29 too. So the index is dark from 15:29 while its options trade for
another eleven minutes.

Side observation, not repaired here: those 13 index carry-forward bars carry
`is_synthetic = FALSE`. CLAUDE.md already records that the `volume=0` detector is
`NSE_EQ`-only and that index-era must be resolved by rule — this is that gap
showing, and it is unrelated to the exit change.

### The consequence, and the seam that resolves it

`NiftyShieldExitDriver` is the LoopDriver's `rebalance_hook`, and the hook fires
**only when a bar arrives**. A 15:35 threshold against a bar stream that ends at
15:29 could never fire — the structure would be carried overnight, which is exactly
the orphan `close_open_structures.py` exists to repair.

`RuntimeConfig.rebalance_on_idle` (new, **default False**) also drives the hook on a
no-bar tick, at the clock's own time. NiftyShield opts in for LIVE only. Carry's
book-level rebalancer is untouched — a between-bars invocation would be wrong for
it, which is why the flag is opt-in rather than the new default.
`NiftyShieldExitDriver` takes `min_interval_s` (LIVE 15s, REPLAY 0) so a 0.5s poll
does not hammer the chain cache; REPLAY stays unthrottled because its bars arrive in
milliseconds of real time and every one must be evaluated.

Net effect: TP/SL are live-evaluated against poller chain marks from 13:00 straight
through to 15:35, and the hard flatten fires at 15:35.

### Config hash moved

`exit_time` is a certified strategy parameter, not a runtime seam, so the frozen
identity changed. **This needs operator ratification.**

```
new config_hash: 260c7cca64f2e1e37ba33e7ccf67314c480dd0e7119d683ddccda66417fc2b17
```

Note also that `exit_time` was previously **not the value in force**:
`NiftyShieldExitDriver._manager_for` hardcoded `{"hour": 15, "minute": 15}` and never
read the strategy config, so there were two sources of truth and only one was live.
Both now read from the config.

---

## 3. The dashboard scoped "this session" to the last published fact

`selectedSessionDate()` fell back to `state.window.fact.session_date`. Before today's
13:00 checkpoint the newest fact is **yesterday's**, so the gate strip scoped to
2026-09-07 and rendered "1 attempted this session" while the header said SYSTEM LIVE.
The count was correct for 2026-09-07 and wrong as presented.

- `/nifty-shield/api/live` now returns `today`; `selectedSessionDate()` prefers it.
- The `1 structure / session` gate names the date it counted.
- The Margin-fit gate's `ENTRY_MARGIN` lookup is scoped to that date — it was an
  unscoped `find()` over the whole window, so a day with no entry showed the previous
  day's margin as today's.
- When the newest fact is not today's, the hero says "last 13:00 fact", the VIX gate
  shows the fact's date instead of a pass/fail, and the verdict reads
  "No structure yet on `<date>` — awaiting the 13:00 fact".

The actual `_entered_today` entry gate was **not** touched; it was never broken.

---

## Tests

519 passing across the touched suites (`tests/execution/test_nifty_shield_*`,
`tests/nifty_shield_paper`, `tests/runtime`, `tests/flask`). New coverage:

- basket margin sizes the whole structure in one memoised call, at the FINAL
  (post-benefit) figure, with the right quantities and product code;
- it raises rather than degrading, on both a missing instrument key and a broker error;
- `final_lots` clamps lots down against the broker's figure;
- the hard exit fires at 15:35 and **holds at 15:16**, which used to close it;
- the idle-rebalance seam is off by default, passes the clock's own time when on,
  and no-ops without a hook or an execution handler;
- the exit-driver throttle floors repeat invocations without swallowing the eventual
  evaluation, and is unthrottled by default.

One fixture changed for a real reason: the synthetic REPLAY session ran 09:15-15:15
(361 bars), so the old exit fired on its final bar. At 15:35 it never closed and the
session was excluded from the window as "no-closed-structure". Extended to 382 bars
(to 15:36).

---

## Open items for the operator

1. **Ratify the new `config_hash`** `260c7cca...` — the frozen strategy identity moved.
2. **REPLAY parity for time-exit trades.** A replay of a *real* recorded session ends
   at 15:29 with the structure still open, because REPLAY has no idle ticks and the
   recorded bars stop at the auction print. LIVE closes it on a clock tick REPLAY has
   no analogue for. Any structure that survives to the hard exit will therefore not
   reproduce in replay. Not addressed here; needs a decision before the next
   replay-evidence artifact.
3. **`sealed_harness.py` still simulates exit at 15:15** (`EXIT_HOUR, EXIT_MINUTE`).
   Left alone deliberately — it is a sealed-read simulation artifact, and changing it
   is a governance action, not a bug fix.
4. **Restart required.** None of this is live until the runner restarts. The chain
   cache and the running session are on the old code.
5. The SPAN snapshot is still missing today. That no longer blocks correct sizing
   (the broker is the authority now), but SPAN/ELM evidence remains absent from the
   §7.7 trail.
