# TS Basis Daily — Options Selection

**Formation date:** 2026-07-27 (latest) · **Generated:** 2026-07-27
**Source:** `scripts/ts_basis_daily_options.py`
**Reference data:** stock-options bhavcopy EOD **2026-07-27** — *not a live quote.*

Maps the 10-name TS Basis Daily book to tradeable single-stock options:
**LONG (Q5) → buy CE**, **SHORT (Q1) → buy PE**.

## Selection rules (operator-chosen)

- **Strike:** ATM — nearest listed strike to the expiry forward, with a liquidity
  guard that snaps off any zero/thin-OI half-strike to the nearest strike carrying
  real open interest (`MIN_OI = 100`).
- **Expiry:** nearest monthly ≥ 7 days out → **2026-08-25**. Skips the 2026-07-28
  contract (expires next day, near-zero time value). Stock options are monthly only.
- **Forward (ATM anchor):** latest Aug-25 single-stock **future** close.

## The book

| Ticker | Dir | Opt | Expiry | Fwd | Strike | Prem (EOD) | OI | Vol | Lot | Premium / lot |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| YESBANK | LONG | CE | 2026-08-25 | 23.1 | **23** | 0.80 | 24,786,700 | 503 | 31,100 | ₹24,880 |
| WIPRO | LONG | CE | 2026-08-25 | 175.3 | **175** | 5.45 | 5,133,000 | 2,190 | 3,000 | ₹16,350 |
| WAAREEENER | LONG | CE | 2026-08-25 | 2737.7 | **2750** | 111.40 | 37,275 | 354 | 175 | ₹19,495 |
| VOLTAS | LONG | CE | 2026-08-25 | 1327.1 | **1320** | 52.15 | 50,250 | 188 | 375 | ₹19,556 |
| VEDL | LONG | CE | 2026-08-25 | 266.6 | **265** | 11.55 | 1,422,550 | 1,028 | 1,150 | ₹13,282 |
| 360ONE | SHORT | PE | 2026-08-25 | 1136.6 | **1140** | 42.70 | 13,500 | 29 | 500 | ₹21,350 |
| ABCAPITAL | SHORT | PE | 2026-08-25 | 402.2 | **400** | 14.10 | 632,400 | 113 | 3,100 | ₹43,710 |
| ADANIENSOL | SHORT | PE | 2026-08-25 | 1710.9 | **1720** | 76.50 | 18,225 | 36 | 675 | ₹51,638 |
| JSWSTEEL | SHORT | PE | 2026-08-25 | 1250.4 | **1260** | 35.35 | 99,900 | 41 | 675 | ₹23,861 |
| LAURUSLABS | SHORT | PE | 2026-08-25 | 1722.9 | **1720** | 49.55 | 194,650 | 708 | 850 | ₹42,118 |

**Liquidity snap:** none — every ATM strike carried real OI this formation.

## Caveats (mechanical, not advice)

- **Premiums are EOD 2026-07-27**, not live. The next session's chain will differ — re-pull
  the live chain before trading. No live Upstox token was present at generation time.
- **The strategy was validated on the linear long/short *futures* basis, not on options.**
  An ATM option has delta ≈ 0.5, so option P&L ≈ ½ × underlying move × lot, plus theta
  and bid-ask cost the backtest never modeled. Options add convexity and time decay that
  the TS Basis Daily net-spread results do not reflect.
- **Daily cadence (~1-day hold)** against a monthly option: per-day theta on a 4-week ATM
  is modest, but single-stock option bid-ask spreads are wide — round-trip slippage can
  dominate a 1-day edge.
- **Penny names** (IDEA fwd 13.2, YESBANK 23.1) have coarse strikes and large %/tick;
  the ATM strike is a rough fit and premium is a couple of ticks.

## Reproduce

```bash
python scripts/ts_basis_daily_options.py                 # latest formation
python scripts/ts_basis_daily_options.py 2026-07-23      # specific date
python scripts/ts_basis_daily_options.py --top 5 --min-dte 7
```
