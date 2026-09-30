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
