# Day Type and Microstructure

## Sources

- `docs/DAYTYPE_CLASSIFIER.md`
- `docs/INDEX_MICROSTRUCTURE_PROFILING.md`
- `docs/STRATEGY_RESEARCH_LOG.md`
- `docs/V9_INTEGRATION_SUMMARY.md`

## Core conclusions

- Intraday state is real and measurable, but only when the feature set is causal and the evaluation is done with strict walk-forward discipline.
- The strongest features came from opening structure, gap context, volatility structure, TWAP/VWAP relationships, and intraday rotation.
- Volume features were not useful for index instruments when the feed reported zero or unusable volume.
- K-means clustering with stable preprocessing produced usable day types; the useful result was not just the clusters but the operational checkpoints they enabled.

## Important findings

- Day-type classification can improve timing, but it is not a substitute for trade edge.
- The index profile work repeatedly showed that block A style features can be anti-predictive at certain times of day.
- The final lesson from the intraday work was that execution geometry often dominated prediction quality.
- In the PM impulse work, holding through the session was sometimes better than trying to force a tight geometry around entry and stop placement.

## Practical implications

- Use day types as a filter or context layer.
- Prefer causal checkpoints over retrospective labels.
- Drop features that cannot survive live feed constraints.
- Optimize the entry/exit geometry only after the regime and timing layer are stable.

