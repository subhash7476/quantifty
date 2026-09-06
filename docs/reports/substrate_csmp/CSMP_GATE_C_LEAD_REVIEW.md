# CSMP Gate (c) — Lead Review

**Gate:** (c) Survivorship / point-in-time universe membership
**Deliverable reviewed:** `scripts/csmp/build_universe.py`, `scripts/csmp/audit_universe.py`,
`docs/reports/CSMP_GATE_C_UNIVERSE_AUDIT.md`, and the new store tables
(`universe_membership`, `universe_intervals`, `instrument_master`, `universe_eligibility`,
`universe_probes`) in `data/market_data/equity_bhavcopy.duckdb`.
**Implementer:** DeepSeek V4. **Reviewer:** Claude.
**Date:** 2026-07-11

## Verdict: **PASSED** (two findings, both hardened in-review — see Independence caveat)

The report's claims were not taken at face value (the gate-(b) rounds established that a
DeepSeek report can read PASS while carrying a real defect). Every load-bearing claim was
re-derived independently against the store. All seven acceptance criteria hold.

## What was verified independently (falsifiable checks, with results)

| # | Acceptance criterion | Independent check | Result |
|---|----------------------|-------------------|--------|
| 1 | `equity_bhavcopy` bit-unmodified (7,030,920 rows) | `COUNT(*)` against the store | **7,030,920 — OK** |
| 2 | Membership keyed to monthly rebalances 2012→present, per-entity, `method` recorded, intervals derived | table shape + 175 distinct rebalance dates, 35,000 cells, per-entity join | **OK** (200/rebalance, 0 shortfall, 0 duplicate `(rebalance,symbol)`) |
| 3 | No-leak test in code and passes | read `membership_as_of` — it is an **independent** point-in-time reimplementation (filters every source row `≤ t`) cross-checked against stored membership on 16 sampled rebalances | **PASS** (see F2 on strength) |
| 4 | ≥10 named delisted retained; no present-day survivor list as input | `universe_intervals` + last-trade-per-entity; the only external list (today's NIFTY-200) is fetched to `universe_probes` as validation-only | **OK** (94 delisted entities; 112 of 200 first-rebalance members absent from today's list) |
| 5 | Non-equity exclusion via `symbol_isin` (ISIN primary, name fallback); `ICICIMOM30` resolved/named | queried every membership cell's eligibility class + any non-`INE` ISIN in membership | **OK** — 0 non-equity cells; the 3 `equity_unidentified` cells are `ANGELBRKG` and `BURGERKING` (real companies); `ICICIMOM30` = 0 cells, named as a hole; `LIQUIDBEES` excluded by `INF*` |
| 6 | Byte-identical re-run | ran `audit_universe.py` three times, `diff` | **identical** |
| 7 | No diffs outside `scripts/csmp/`, `docs/reports/`, `data/market_data/`; no frozen-component diffs; no gate-(d) work | `git status` | **OK** (only the two scripts + audit MD are new; store gained new tables only) |

Structural review of `build_universe.py`: ranking is a total order with a deterministic
tiebreak (`sorted(rows, key=lambda r: (-median, symbol))[:200]`); per-rebalance queries
filter `BETWEEN lookback_start AND t` (no forward row reachable); raw `turnover` is the
metric (split-conserved, so gate (b)'s adjusted view is correctly not consulted); entity
continuity is a union-find over `symbol_changes` with a stable representative; the five
derived tables are dropped-and-rebuilt each run and the gate-(a)/(b) store is never written.

## Findings

**F1 (MEDIUM) — criterion-6 compliance was incidental, not guaranteed.** Three report
sections sliced a Python list (`[:14]` / `LIMIT 1`) off a SELECT with a tie-ambiguous or
absent `ORDER BY`: the delisted-examples list (`ORDER BY exit_date DESC` — many entities
share an exit date, and 200 share `NULL`), the today's-list-omission examples (`SELECT symbol
… WHERE rebalance_date=?` with **no** `ORDER BY`), and the retention example (`LIMIT 1` on a
tied `MAX(trade_date)`). The report reproduced byte-identically on the review machine, but the
displayed rows depended on unspecified DuckDB scan order — a latent criterion-6 failure across
a different plan/thread-count/version. **Hardened:** added deterministic tiebreaks
(`ORDER BY exit_date DESC NULLS LAST, symbol, entity`; `ORDER BY rank`; `ORDER BY 2, 1`).
No count changed (membership, 94-delisted, 112-omission all identical); only the row order is
now pinned. Re-ran the audit twice post-fix: byte-identical.

**F2 (LOW) — §3 overstated the no-leak test.** The prose called the test "adversarial" and the
recomputation a "store truncated at `t`." It is not a physically truncated store; it is a
second implementation (`membership_as_of`) that re-filters an in-memory series to `≤ t`. That
is a legitimate and useful **differential** point-in-time cross-check — it catches a leak in
either implementation — but it cannot catch a leak present identically in both, and the
membership rule is point-in-time by construction regardless. **Hardened:** the §3 conclusion
now states plainly that the test is an independent point-in-time recomputation that agrees
with the stored membership, without the "adversarial/truncated-store" overclaim. This is the
gate-(b) lesson (a report's verdict must not claim more than its test demonstrates) applied
pre-emptively.

Neither finding changes the verdict: the point-in-time and survivorship properties hold on the
data, and the exclusion/continuity/reproduction criteria are met.

## Independence caveat

The charter locks DeepSeek V4 as implementer and Claude as Lead Reviewer. The operator
authorized Claude to fix any failures in this round ("you are authorized to fix all and
proceed further"). The gate **passed on its own numbers before any fix**; the two hardening
edits above are defensive (they pin determinism and correct an overclaim) and change no gate
number. As in the gate-(b) R5 round, the same party reviewed and edited, so no fully
independent party has checked the hardening edits — but they are confined to report ordering
and prose, and the audit regenerates byte-identically after them.

## Inheritances discharged / carried forward

- **Closed:** gate (b)'s `ICICIMOM30` `unidentified_instrument` gap — resolved via the NSE
  `EQUITY_L` instrument master (absent ⇒ named as a hole; 0 membership cells).
- **Consumed, not re-derived:** `symbol_isin`, `symbol_changes`, `ca_scope_exclusions` /
  `ca_evidence_exceptions` (overlap flagged for gate (e): 122 + 8 member-cells, not dropped).
- **Carried to gate (e):** the `turnover_top200` universe is the point-in-time panel the
  transmission triage ranks over; the gate-(b) quarantine overlap is flagged there.

**Gate (d) (delivery-equity fee model) is unblocked.**
