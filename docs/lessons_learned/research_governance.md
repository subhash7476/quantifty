# Research Governance

## Sources

- `docs/STRATEGY_RESEARCH_LOG.md`
- `docs/CLEANUP_AUDIT_REPORT_2026-03-13.md`
- `PROJECT_REVIEW_SUMMARY.md`
- `REPO_AUDIT.md`

## Core conclusions

- Most strategy versions failed for repeated structural reasons, not because the implementation was missing one more indicator.
- The recurring problems were fee sensitivity, path dependence, over-filtering, fragile exits, and symbol-specific behavior.
- The best work-flow was walk-forward evaluation with non-destructive promotion of models and outputs.

## Governance rules that survived the research cycle

- Keep historical runs immutable.
- Promote models only after out-of-sample validation.
- Use verdict logic that is explicit about why a configuration is accepted or rejected.
- Treat research artifacts as evidence, not as deployment targets.
- Keep feature generation causal and reproducible.

## What to avoid

- Do not infer universal edge from one profitable symbol.
- Do not overgeneralize from a single backtest window.
- Do not turn research scripts into production dependencies without a clear infrastructure need.

