# Strategy and Options

## Sources

> These lessons were extracted from the pre-salvage codebase (prior to 2026-06-04). Source documents were not ported; references below are historical only.

- `docs/NIFTYSHIELD_IMPLEMENTATION.md` *(historical — not present in current repo)*
- `docs/MCX_GOLD_OPTIONS_COMMODITY_INTEGRATION_REPORT.md` *(historical)*
- `docs/COMMODITY_TRADING_IMPLEMENTATION_SUMMARY.md` *(historical)*
- `docs/COMMODITY_TRADING_SYSTEM_PLAN.md` *(historical)*
- `docs/STRATEGY_RESEARCH_LOG.md` *(historical)*
- `docs/OPTIONS_ANALYSIS_DASHBOARD_PLAN.md` *(historical — not present in current repo)*

## Core conclusions

- The strongest strategy work was not in one-off entries; it was in separating strategy intent from execution, risk, and pricing assumptions.
- NiftyShield is a structured premium-selling system, not a naive directional bet.
- Its value comes from regime-aware structure selection, explicit VIX gating, adjustment rules, and bounded session lifecycle.
- Its biggest weaknesses are execution realism and pricing realism, especially around IV skew, gap risk, and slippage.

## Commodity and options lessons

- Synthetic pricing is useful for architecture, but live drift must be measured before trusting conclusions.
- Risk should be budgeted in explicit rupee and margin terms.
- Leg adjustments should be validated after costs, not just judged by visual comfort.
- Event-day controls and expiry-specific risk pockets matter.

## Common strategy lesson

- A strategy can look clean in backtests and still fail in live conditions if the pricing model is too forgiving.
- The correct order is: pricing realism first, risk budgeting second, structure optimization third.

