# Overlay-instead-of-stop — measurement before build

Ran 2026-09-07 against `data/market_data/options_bhavcopy.duckdb` (NIFTY, EOD closes,
2023-01-01 → 2026-07-17). **Recommendation: do not build it.**

## What was tested

| Policy | Rules |
|---|---|
| **A — stop only** (current, post-fix) | TP `+0.25 × credit` · SL `−0.50 × L0` · time stop at DTE-1 |
| **B — overlay then stop** | Same, but the first time `pnl ≤ −0.25 × L0` (once only, DTE ≥ 1) add a second ATM fly at that day's pin. Thereafter TP on combined credit; **SL still anchored to `L0`** so the overlay never widens the rupee floor. |

`L0` = the original fly's max_loss. Marks are EOD closes — intraday triggers cannot fire,
and regime-flip exits are not modelled.

**Prediction stated before running:** overlay lowers stop-out frequency and raises mean P&L
(the added credit pays for part of the loss) but worsens the tail and roughly doubles peak
margin, so P&L-per-margin should not improve.

## Run 1 — our actual instrument (weekly, entries DTE 2–5). n = 337

| | A | B |
|---|---:|---:|
| mean P&L | +2.57 | +3.26 |
| worst | −170.30 | −220.60 |
| exits | tp 69 / sl 27 / time_stop 241 | tp 69 / sl 27 / time_stop 241 |

**Those identical exit counts are the finding.** The overlay fired on 47 of 337 trades and
the exit reason changed on **zero** of them. Instrumenting why:

- Path length: **186 of 337 trades get exactly one managed mark**, 151 get two.
- Of the 47 overlays, **35 had zero days of runway** — added and time-stopped the same
  session — and 12 had exactly one day.
- Only **12 of 337 trades (3.6%)** actually exercised the overlay.

Both differences above come from those same 12 trades — the mean improvement and the
tail deterioration are the same handful of observations, not independent signals. **This run
cannot answer the question**: under the `dte <= 1` time stop there is no room for a defence
to operate. The overlay is starved by the same rule that starves the TP.

## Run 2 — runway, but a broken base (DTE 10–28, wing still ±1.5%). n = 2,146

Policy A mean −5.80, **median −34.80**, 1,165 of 2,146 stopping out. A ±1.5% wing is far too
narrow for a 28-day horizon; spot leaves the tent almost surely. **This run is discarded** —
it measures whether an overlay rescues a structurally unsound fly (it does not: B better on
390 of 931, worse on 513), which is not the question. Superseded by run 3.

## Run 3 — runway AND a coherent base (DTE 10–28, wing ±1.5% × √(dte/3.5)). n = 2,277

Wings scaled to horizon, so a 14-DTE entry gets ≈±3.0%. The overlay fly is scaled by its own
remaining horizon. Policy A now behaves like a real short-premium construct: **TP on 1,245 of
2,277 (55%), median +78.05.**

| | A | B |
|---|---:|---:|
| mean P&L | **−12.29** | **−12.31** |
| median | +78.05 | +77.90 |
| total | −27,985.6 | −28,036.7 |
| p05 | −346.20 | **−385.25** |
| worst | −661.10 | **−780.15** |
| mean margin | 395.02 | **563.54** |
| exits | tp 1245 / sl 736 / ts 296 | tp 1158 / sl 705 / ts 414 |

Overlay fired on **908/2277 (39.9%)** with real runway. On those trades: **better on 427,
worse on 458**, mean −0.06, median −1.05.

**The overlay is a coin flip that costs 43% more margin and deepens the tail.** Mean and
median P&L are unchanged to two decimal places; p05 worsens by 39 points and the worst case
by 119; capital committed rises 395 → 564.

> **Do not read `P&L / margin` (−0.0311 → −0.0218) as an improvement.** Both are negative;
> dividing a similar loss by a larger margin base yields a smaller-magnitude negative. That
> is an artifact of normalising a loss, not a gain.

Note the base is negative-expectancy in this sample (mean −12.29 despite a +78 median) — a
short-premium tail profile. The A-vs-B comparison is trade-for-trade on identical entries,
so that does not confound it, but neither policy is a recommendation to trade this construct.

## Why not to build it

1. **Under our current rules it would almost never act.** 35 of 47 firings had zero runway;
   3.6% of trades exercised it; exit reason changed on zero. We would be building schema
   changes, group-exit semantics and a manage-loop rewrite for machinery that gets one
   usable opportunity in 28 trades.
2. **Given a coherent base and real runway, it adds nothing.** 427 better / 458 worse over
   908 firings, mean difference −0.06, with a materially worse tail and 43% more capital.
3. **The idea is not separable from the time stop.** An overlay only has room if we hold
   into expiry day — the change we declined this morning because expiry-day gamma is where a
   short fly's max loss is realised. "Overlay instead of stop" and "hold into expiry day"
   are one decision, not two.

## What would change the answer

- **Intraday marks.** The executor marks every ~0.9s; this study marks once a day. The
  snapshot store holds only 2026-09-04 and 2026-09-07, so an intraday version is impossible
  today. Retaining `wall_chain_snapshots` for a few months would make it possible.
- **A pin-aware overlay.** This study re-centres on the day's ATM. Our executor has
  `session_regime.pin_strike`; an overlay centred on the GEX pin rather than ATM is a
  different rule and was not tested.

## Incidental finding

Run 3's horizon-scaled wing gives the base fly a 55% TP rate and a +78 median, against the
fixed ±1.5% wing's 43% and −34.80. **`wing_pct` is currently a constant in `PaperConfig`
regardless of DTE.** That is a separate question from the overlay and was not the object of
this study, but it is the more promising thread of the two.
