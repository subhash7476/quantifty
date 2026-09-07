# Options-Wall Iron Fly — Expected TP vs. Manual Exits

> **Superseded 2026-09-07:** the config table below records the settings as they were *before* the fix.
> `tp_frac` is now 0.25 and `sl_mult` has been replaced by `sl_frac` (0.5 x max_loss).
> See [OPTIONS_WALL_TP_NEVER_FIRES_2026-09-07.md](OPTIONS_WALL_TP_NEVER_FIRES_2026-09-07.md).

Generated 2026-09-07 11:52 IST from `data/options/wall_scan_results.duckdb` (`trades`).

## The rule (`core/options_wall/paper_executor.py`)

`PaperConfig` defaults are used everywhere — nothing overrides them:

| Param | Value | Meaning |
|---|---|---|
| `tp_frac` | **0.5** | close when gross P&L ≥ 50% of entry net credit |
| `sl_mult` | 2.0 | close when gross P&L ≤ −200% of net credit |
| `squareoff` | 15:15 | time stop, only when DTE ≤ 1 |
| — | — | plus immediate exit on GEX regime flip to Negative |

TP is measured on **gross** P&L: `unrealized_pnl = net_credit − mark_to_close`, fees
excluded from the trigger (they are only netted out at booking).

So: **TP fires when the fly can be bought back for half the credit it was sold for.**

## Trade log

`TP gross` = 0.5 × credit. `TP net` = TP gross − entry fees − exit fees (exit fees taken
from the actual close; at a real TP they'd be slightly lower, so TP net is a mild
under-estimate). `% of TP` = how far the manual exit got toward the target.

| id | Underlying | Entry | Exit | Reason | Credit | TP gross | TP net | Got gross | Got net | % of TP |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Nifty 50 | 08-17 12:46 | 08-17 12:47 | regime_flip | 8,929 | 4,464 | 4,252 | −660 | −872 | −14.8% |
| 2 | Nifty 50 | 09-02 14:29 | 09-03 12:36 | **manual** | 15,817 | 7,909 | 7,667 | 1,099 | 857 | 13.9% |
| 3 | Nifty 50 | 09-03 13:25 | 09-04 13:58 | **manual** | 14,291 | 7,146 | 6,914 | 1,134 | 903 | 15.9% |
| 4 | SENSEX | 09-04 09:52 | 09-04 09:52 | regime_flip | 52,035 | 26,018 | 25,641 | 21 | −356 | 0.1% |
| 5 | SENSEX | 09-04 09:57 | 09-04 13:58 | **manual** | 52,815 | 26,408 | 26,036 | 1,569 | 1,198 | 5.9% |
| 6 | SENSEX | 09-04 13:59 | 09-07 10:52 | **manual** | 13,581 | 6,790 | 6,556 | 425 | 190 | 6.3% |
| 7 | Nifty 50 | 09-04 14:05 | 09-07 10:51 | **manual** | 10,787 | 5,393 | 5,174 | −135 | −354 | −2.5% |

All in ₹, 1 lot (qty 75 / 65 / 20 as recorded).

## Reading

- Five of seven exits were **manual**; none reached TP. The best manual exit (trade 3)
  banked 15.9% of the target.
- Expected TP on the two trades closed this morning: **₹6,556 net on SENSEX #6** (booked
  ₹190) and **₹5,174 net on Nifty #7** (booked −₹354).
- `return_on_margin` at TP would have been 43–74% of max loss per trade — i.e. the rule is
  aiming at a large, slow move in theta, not a quick scalp. Holding an ATM fly to half the
  credit typically needs most of the remaining DTE.
- No trade is open right now (last scan 11:52, zero open rows), so nothing is currently
  working toward a TP.
