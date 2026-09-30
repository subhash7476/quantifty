# BKV-1 research log (append-only; corrections are appended rows, never edits)

| # | When (2026-09-30) | Entry |
|---|---|---|
| L1 | 16:0x | Goal received: M3a x M5b, auditability-first. Read: coverage map v1.1, closure ledger (branch `docs/vwap-ledger-closure`, `5144d52`), M1c protocol v1.3, VWAP report, exposure register. |
| L2 | 16:2x | Advisor consulted before any code: primary estimand = paired B-C contrast on market-excess signed returns; PIT top-200 universe; onset-only; strictly-prior membership; separate SQL-path verifier; HOLDOUT is an operator decision. Adopted. One deviation: instead of asking now, the HOLDOUT question is asked only if VAL confirms (a VAL failure makes it moot). |
| L3 | 16:46 | Dev snapshot built (panel <= 2022-12-30; store runs to 2026-09-29, fence non-vacuous). No forward return computed. |
| L4 | 17:0x | Outcome-free diagnostics: event counts by stage/arm/N (`breakout_volume_diagnostics_outcome_free.json`). Counts only. |
| L5 | 17:2x | Pipeline validated on a SYNTHETIC snapshot (130 names, delistings, holes): numpy engine and SQL verifier agree event-for-event (0 exceptions); verifier flags a tampered ledger. No real price used. |
| L6 | 17:3x | Protocol + JSON written; Params mirrored by test; freeze next. |
| L7 | 17:5x | Advisor pass 2 (pre-freeze). Fixed: VP2 compared adjusted vs raw price LEVELS (would fail on any name with a later bonus/split -> spurious C4) -> now compares scale-free margin; dry-run fixture now contains real 2:1 splits (VP2 skips/passes correctly, VP5(c) rebuilds adjusted from factors at 100%); the HOLDOUT marker now records the full-snapshot hashes; R9 move-size confound declared. |
| L8 | 17:5x | Outcome-free: strictly-prior trailing-21 turnover median drops the identical 10 short-session dates as the centred median (max dropped 0.30, min kept 0.52). |
| L9 | 17:1x | Freeze `84fcd99`. TRAIN run (39 s). Verification TRAIN: VP1 SQL-vs-engine 19,761/19,761 events, 0 exceptions, f diff 1.8e-12 bp; VP2, VP3, VP4, VP6 pass; **VP5(a) FAILED** (symbol-level clean set). Investigated instead of choosing: all 11 offending entities carry a CA under a renamed symbol -> verifier defect, not data/engine. Amendment A1 (entity-level), tested on a fixture with a rename chain; logged amend + re-freeze. TRAIN numbers untouched. |
| L10 | 17:2x | VAL run + verification (all six checks pass, stop=false). CLASSIFY crashed on JSON tuple keys (output only) -> amendment A2, logged re-freeze. VAL: 0 of 8 cells confirmed (min one-sided p 0.159) -> STOP, HOLDOUT never read. |
| L11 | 17:5x | Post-primary R1-R9, worked examples, report built from CSVs; changelog entry. Final: C5 construct-scoped; HOLDOUT unread. |
| L12 | 18:0x | Final review found: gap-decomposition mislabel (R excludes the gap) -> erratum A3 + rebuilt table; prose claims scoped/corrected (TRAIN up-side net, by-year, arm A TRAIN dn N63 t=5.09 not replicated in VAL, R9 tercile-cut granularity, 'none typed by hand'). Next: reproducibility re-run under the current freeze. |
| L13 | 18:2x | Reproducibility tested: TRAIN+VAL re-run under the final freeze (after A1-A3) -> cells/cohort/costs/bench/accounting byte-identical, event ledgers frame-identical. |
