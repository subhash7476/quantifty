# Regime and Signal Quality

## Sources

- `docs/HMM_REGIME_STRATEGY_REPORT.md`
- `docs/SIGNAL_QUALITY_PIPELINE_DESIGN.md`
- `docs/SIGNAL_QUALITY_IMPLEMENTATION_SUMMARY.md`
- `docs/SIGNAL_QUALITY_FILTERS_USAGE.md`

## Core conclusions

- The HMM regime classifier worked as a classifier, but it did not make the cash index strategy profitable by itself.
- The execution layer failed on Nifty cash primarily because the instrument lacked usable volume for the confirmation stack.
- The VIX threshold baseline was too conservative for Indian markets and produced too few trades.
- Signal filters can improve cleanliness, but a filter that looks good on paper can still be catastrophic on one symbol and irrelevant on another.

## What the research established

- Regime classification is best used as a market-timing filter for other strategies.
- Equity stocks with real volume are more suitable than Nifty cash for volume-dependent filters.
- The meta-model layer did not add meaningful edge in the cases tested.
- Kalman and volatility filters were inconsistent across symbols and periods, so they were not production-ready.

## Recommended pattern

- Use regime state to decide when to trade.
- Use symbol-level alpha to decide what to trade.
- Use execution filters only when they can be validated against real feed behavior.
- Treat model confidence as a control signal, not as proof of edge.

