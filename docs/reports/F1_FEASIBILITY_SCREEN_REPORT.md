# F1 Feasibility Screen Report
*Generated: 2026-07-20T16:09:08.955349*

## Caveats (read before interpreting)

1. **Signal prior-exposed.** 12-1 momentum on this panel ran as PSB-2 C4
   (dropped on power 0.4110). TRAIN is not a clean fold.
2. **Cost assumed, not measured.** Roll cost, bid-ask, and impact are modeled,
   not observed. Roll frequency is an uncalibrated assumption — the
   spec-required 2023+ futures panel was inaccessible (NSE blocks).
3. **Basis/carry ignored.** Futures-to-cash basis convergence over the ~monthly
   hold is small vs. momentum dispersion but adds unmodeled noise.
4. **Not a promote path.** A GO means worth buying vendor data for a proper
   pre-registered battery. It does not bless the construct for live trading.
5. **No sealed-window signal read.** Returns computed only up to 2022-12-31.
6. **Bracket fills modeled on daily OHLC.** Open-gap approximated via daily
   low/entry; intraday fills assume execution at level (conservative SL-first).

## Verdict: **GO**

GO: net expectancy positive across full slippage band on both TRAIN and HOLDOUT. Recommend purchasing vendor futures data. CAVEAT: CI lower bound <= 0 at pessimistic slippage — net expectancy is not robustly positive at the conservative end.

**Note:** the GO is conditional — net expectancy CI spans zero at the
conservative end of the slippage band. A vendor-data battery would need
to resolve this with real futures prices.

## Best Bracket Params (TRAIN-selected)
- ATR period: 21d, n=5, k_sl=2.5, k_tp=5.0
- Grid searched: 4x4x4 = 64 combinations
  **Note:** winner at grid boundary (n=min, k_sl=max, k_tp=max). True optimum may lie outside.

## TRAIN (2012-2018)
| Slippage     |  n  |   Exp    | CI_low   | CI_high  | MaxDD    | DaysH | TD_bp/yr | Gross    | Net      |
|---------------------------------------------------------------------------------------------------------|
| optimistic   |  83 |  +0.0154 |  -0.0024 *|  +0.0306 |  -0.4234 |  18.8 |      327 |  +0.0181 |  +0.0154 |
| mid          |  83 |  +0.0132 |  -0.0047 *|  +0.0284 |  -0.4345 |  18.8 |      596 |  +0.0181 |  +0.0132 |
| pessimistic  |  83 |  +0.0087 |  -0.0091 *|  +0.0239 |  -0.4570 |  18.8 |     1135 |  +0.0181 |  +0.0087 |
  * CI lower bound <= 0 at this point

## HOLDOUT (2019-2022)
| Slippage     |  n  |   Exp    | CI_low   | CI_high  | MaxDD    | DaysH | TD_bp/yr | Gross    | Net      |
|---------------------------------------------------------------------------------------------------------|
| optimistic   |  47 |  +0.0312 |  +0.0126  |  +0.0579 |  -0.2800 |  18.5 |      229 |  +0.0332 |  +0.0312 |
| mid          |  47 |  +0.0297 |  +0.0111  |  +0.0564 |  -0.2857 |  18.5 |      409 |  +0.0332 |  +0.0297 |
| pessimistic  |  47 |  +0.0267 |  +0.0081  |  +0.0534 |  -0.2972 |  18.5 |      769 |  +0.0332 |  +0.0267 |
  * CI lower bound <= 0 at this point

## Configuration
- Signal: 12-1 cross-sectional momentum, skip most-recent month
- Portfolio: <=10 names, equal-weight, monthly formation
- Bracket: ATR-21d, SL before TP (conservative), open-gap approximated via daily bar low
- Universe: cash liquidity proxy (>=Rs5cr median daily turnover over trailing 63d, causal per-formation-date computation)
- Slippage sweep: optimistic 5bp, mid 10bp, pessimistic 20bp
- TRAIN slippage multiplier: 1.5x
- Roll cost assumption: 0.5 extra round-trips/formation
- Position notional: Rs10L
- TRAIN window: 2012-01-01 to 2018-12-31
- HOLDOUT window: 2019-01-01 to 2022-12-30
