# NiftyShield PAPER — 2026-09-15 trade: take-profit after 2 minutes, Rs 140 gross

**Verdict:** not a malfunction — the second live instance of the design limit recorded in
`NIFTY_SHIELD_TRADE_2026-09-11_EARLY_TAKE_PROFIT.md`. The take-profit threshold on a 7-DTE
vertical is **Rs 121 gross**, below the **Rs 133 round-trip fee**, so the rule closed the
structure two minutes after entry for **~Rs 6 net**. The ~Rs 2,000 the operator saw is the
structure's later mark-to-market (Rs 1,794 gross at the panel snapshot), which the take-profit
forwent by closing at 13:03.

## 1. The trade

| | |
|---|---|
| Group | `2bc7bd8b-b090-5162-9486-29133aa8dcc1` |
| Structure | bear call spread, 1 lot × 65, expiry 2026-09-22, DTE 7 |
| Entry | SELL 23300CE @ 174.50 (13:01:15), BUY 23500CE @ 83.25 (13:01:19) |
| Exit | BUY 23300CE @ 169.05, SELL 23500CE @ 79.95 (13:03:25), reason `take_profit` |
| Credit | (174.50 − 83.25) × 65 = **Rs 5,931.25** |
| Gross P&L | 354.25 − 214.50 = **Rs 139.75** (spread value fell 2.15 pts) |
| Fees (round trip) | 73.80 + 59.55 = **Rs 133.36** |
| Net | **Rs 6.39** |
| Margin (Upstox basket) | Rs 38,766.59 |
| Panel MTM at later snapshot | marks 111.00 / 47.35 → spread 63.65 → **Rs 1,794 gross** |

Sources: `data/nifty_shield/journal.jsonl` (ENTRY_MARGIN 13:01:21, STRUCTURE_CLOSE 13:03:25),
`data/nifty_shield/trading/trading.db` (`trades`, exit prices and fees), operator screenshot.

## 2. Why it fired

`NiftyShieldExitManager._take_profit_hit`: `pnl >= profit_target_decay_frac × available_decay_frac × credit`.

- `available_decay_frac` (7 DTE): 7 × 5/7 × 6.25 = 31.25 trading hours; a 2.5 h hold leaves
  √(28.75/31.25), so available decay = **4.083%**.
- Threshold = 0.50 × 0.04083 × 5,931.25 = **Rs 121.10** — the spread only has to lose
  **1.86 points** of value.
- `structure_credit` is in rupees (premium × filled qty), so there is no unit error; the gross
  P&L of Rs 139.75 at the close cleared Rs 121.10 as designed.

What moved the spread in those two minutes was not measured for this note.

## 3. Checks that came back clean

| Check | Result |
|---|---|
| Threshold reproduces | 121.10 from the formula above |
| Credit units | Rs, from fills (`structure_credit`, nifty_shield_handler.py:140) |
| Exit fills vs recorded P&L | 139.75 reproduces from `trades.exit_price` |
| Fee schedule | option schedule (`0f46f9b`, in HEAD and in the running session): 45.32 + 28.48 = 73.80 and 26.01 + 33.55 = 59.55 reproduce exactly — Finding #2 of the 09-11 note is fixed on this path |

## 4. What the second data point adds

| Trade | DTE | Threshold | Round-trip fees | Threshold / fees | Held | Net |
|---|---:|---:|---:|---:|---:|---:|
| 2026-09-11 bull put | 4 | Rs 123.94 | Rs 116.81 | 1.06× | 28 min | Rs 26 |
| 2026-09-15 bear call | 7 | Rs 121.10 | Rs 133.36 | **0.91×** | **2 min** | **Rs 6** |

1. **At 7 DTE the threshold is below the fees.** Available decay shrinks as DTE grows
   (4.08% at 7 DTE vs 7.26% at 4 DTE), so a take-profit at exactly the threshold now loses
   money net. Both take-profits to date netted under Rs 30.
2. **Paper fills at marks; LIVE would cross four half-spreads** against a 2.15-point gain, so
   the same exit in LIVE is plausibly negative.
3. **The foregone upside is now observed, not hypothetical.** The 09-11 note could only
   argue the trade-off; today the structure was worth Rs 1,794 gross at the later snapshot
   (a bear call spread benefiting from the BearTrend regime the source selected it for). One
   session is not evidence that holding beats the take-profit — it is a data point for open
   item 5 of `NIFTY_SHIELD_REMEDIATION_2026-09-08.md`, and the stop side of that trade-off
   (Rs 121 target vs a stop 25× larger) is unmeasured.

**Not changed.** The parameter was pinned by a derivation that deliberately reads no trades
(`derive_anchoring_params.py` §3), and the remediation's rule is not to refit on n=1 — now
n=2. A change that is *not* a refit is available if the operator wants one: a take-profit
that cannot fire below round-trip costs is a floor derived from the fee schedule, not from
outcomes. That is a design decision for the operator, not something this note applies.
