# NiftyShield PAPER — 2026-09-11 trade: why it closed after 28 minutes

**Verdict:** not a malfunction. The take-profit fired exactly as the 2026-09-08
remediation designed it (§4.1 of `NIFTY_SHIELD_REMEDIATION_2026-09-08.md`). It
fired early because on a 4-DTE structure the threshold is **Rs 124 gross**, about
the size of the round-trip fees, and a ~7-point spot drift plus 28 minutes of
theta cleared it. The trade booked **Rs 42.51 net as recorded, Rs 26.19 net
under the correct option fee schedule.**

It is the first live data point for open item 5 of that report ("take-profit vs
holding to the clock — measure on forward paper"), and it surfaces two things
the remediation did not weigh: the threshold against fees/slippage, and against
the stop.

## 1. The trade

| | |
|---|---|
| Group | `9a63c2b4-8b0f-5e2a-9755-938e4d15ca4d` |
| Structure | bull put spread, 1 lot × 65 (base 2 lots × regime_mult 0.5), expiry 2026-09-15, DTE 4 |
| Entry | SELL 23350PE @ 100.75 (13:01:27), BUY 23200PE @ 48.25 (13:01:43) |
| Exit | BUY 23350PE @ 96.10, SELL 23200PE @ 45.80 (13:29:10), reason `take_profit` |
| Credit | (100.75 − 48.25) × 65 = **Rs 3,412.50** |
| Close cost | (96.10 − 45.80) × 65 = Rs 3,269.50 |
| Gross P&L | **Rs 143.00** (spread value fell 2.20 pts) |
| Margin (Upstox basket) | Rs 36,211.43 |

Sources: `data/nifty_shield/journal.jsonl` (ENTRY_MARGIN 13:01:50, STRUCTURE_CLOSE
13:29:11), `data/nifty_shield/execution.db` (orders/fills),
`data/nifty_shield/trading/trading.db`.

## 2. Why the take-profit fired

`NiftyShieldExitManager._take_profit_hit` closes when
`pnl >= profit_target_decay_frac × available_decay_frac × credit`.

`available_decay_frac` is carried on the signal (`structures.available_decay_frac`):
4 DTE → 4 × 5/7 × 6.25 = 17.86 trading hours; a 2.5 h hold leaves
√(15.36/17.86), so available decay = **7.26%** (signal value
`0.07263815045042965` — reproduces exactly).

Threshold = 0.50 × 0.07264 × 3,412.50 = **Rs 123.94** (3.6% of credit, i.e. the
spread only has to lose **1.9 points** of value).

At 13:29:10 gross P&L was Rs 143.00 ≥ 123.94 → close.

**What moved it** (Upstox 1m, `NSE_INDEX|Nifty 50`): spot 23,343 at entry, dipped
to 23,320.7 at 13:11 (−25 pts, adverse), recovered to ~23,350 by 13:29 (+7 pts).
The spread's net delta is positive (short ATM put, long 150-pt OTM put), so a
small up-drift plus half an hour of theta was enough.

## 3. What the numbers say about the rule

| Quantity | Rs | vs TP threshold |
|---|---:|---:|
| TP threshold (gross) | 123.94 | 1.0× |
| Round-trip fees as recorded | 100.49 | 0.81× |
| Round-trip fees, correct option schedule | 116.81 | **0.94×** |
| Stop (0.5 × max loss 6,337.50) | 3,168.75 | **25.6×** |

1. **The threshold is gross and sits at ~the fee line.** Under the correct fee
   schedule a take-profit at exactly the threshold nets **Rs 7**. Today's slight
   overshoot is what left Rs 26.
2. **Paper fills both entry and exit at marks; LIVE crosses the spread on all
   four.** Selling the short / buying the wing at entry gives up one half-spread
   per leg on the credit, and buying back / selling out at exit gives up one per
   leg again — four half-spreads against a 2.20-point gain. Per-leg half-spreads
   of 0.55 pt erase it. (Arithmetic, not a measured bid/ask — the traded expiry's
   quotes at 13:29 were not pulled for this note.)
3. **Size against the stop.** The take-profit is 25.6× smaller than the stop.
   When it fires early the structure forgoes the rest of the session's decay,
   while the loss it can still take on other days is unchanged in size. Whether
   that trade-off beats holding to 15:35 is exactly open item 5, and it can only
   be answered over many sessions.

None of this is a reason to change the parameter now. The remediation's own
rule applies: don't refit on n=1. It is evidence for open item 5.

## 4. Separate finding — fee schedule still wrong on this path

The recorded fees reproduce the **equity-intraday** schedule (flat STT 0.025% on
every leg, stamp both sides), not `core/execution/options/fees.py`. Per leg:

| Fill | Side | Premium | Recorded | Correct |
|---|---|---:|---:|---:|
| 23350PE open | SELL | 100.75 | 25.71 | 36.14 |
| 23200PE open | BUY | 48.25 | 24.61 | 24.99 |
| 23350PE close | BUY | 96.10 | 25.61 | 26.38 |
| 23200PE close | SELL | 45.80 | 24.56 | 29.30 |
| **Total** | | | **100.49** | **116.81** |

This is Finding #2 of `NIFTY_SHIELD_REMEDIATION_2026-09-08.md`, listed there as
open. `option_order_fees` is still imported only by `core/options_wall/fly.py`
and two audit scripts, not the NiftyShield execution path. Reported P&L is
overstated by Rs 16.32 on this trade.

## 5. Reproduce

- Threshold/fees: `option_order_fees(premium=…, quantity=65, side=…, trade_date=date(2026, 9, 11))`
  with STT sell rate 0.0015 and exchange txn 0.0003503 for this date.
- Spot: `GET /v2/historical-candle/intraday/NSE_INDEX|Nifty 50/1minute`
  (the local 1m store was locked by the live ingestor at the time of writing).
