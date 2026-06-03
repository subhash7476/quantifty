# Live Operations

## Sources

- `docs/LIVE_READINESS_AUDIT_REPORT.md`
- `docs/CODEBASE_OVERVIEW.md`

## Core conclusions

- The live paper system became acceptable only after the audit fixed the state-management bugs, telemetry wiring, staleness checks, and startup recovery gaps.
- The most important live risks were not signal logic; they were lifecycle and state integrity.
- Trade counters, seen-signal tracking, and broker reconciliation are mandatory if the process can restart mid-session.
- A live runner must detect stale data, heartbeat loss, and calendar exceptions before it places orders.

## Fixed issues that mattered most

- Trade-limit counters must increment on actual fills.
- Signal deduplication must survive restarts.
- Warmup history must be long enough to support the indicator stack.
- Position sizing must not confuse capital limits with unit limits.
- Dashboard telemetry must be wired to real runtime state.
- Market holiday and session gating must be explicit.

## Remaining caution points

- Reconciliation on startup is still a real broker requirement, even if paper mode tolerates it.
- Consecutive-loss circuit breakers and clock-drift checks are still worth adding.
- A live system should fail closed on missing data, not continue as if nothing happened.

## Operational rule of thumb

If a trading system is hard to restart safely, it is not ready for unattended live use.

