# A — Phase-1 Index-Slice Certification Report

Generated: 2026-08-27T16:50:57 · runtime 190s · 1m files 3598 · 1d calendar sessions 3624 · Nifty sessions with bars 3574

**Read boundary:** raw bars + microstructure only; no construct signal, no entry/exit prices, no P&L (per A_CONSTRUCT_DEFINITION.md).

**Overall: FAIL**

| Gate | Verdict | Key figures |
|---|---|---|
| C1 contiguity | FAIL | missing file 35; missing rows 23; specials 12; regular holes 46 (runs: 2018-05-02..2018-05-04 (3), 2018-05-07..2018-05-11 (5), 2018-05-14..2018-05-18 (5), 2018-05-21..2018-05-25 (5), 2018-05-28..2018-05-31 (4), 2026-08-25..2026-08-26 (2), 2023-02-01..2023-02-03 (3), 2023-02-06..2023-02-10 (5), 2023-02-13..2023-02-17 (5), 2023-02-20..2023-02-24 (5), 2023-02-27..2023-03-01 (3), 2026-08-24..2026-08-24 (1)) |
| C2 completeness | FAIL | full 375-bar 3508; partials 66 |
| C3 validity | FAIL | sessions with issues 45; OHLC viol 0; dup 0; non-mono 0 (first examples: 2012-01-07, 2012-01-12, 2012-03-03, 2012-04-28, 2012-09-08, 2013-05-11, 2013-07-29, 2014-03-22) |
| C4 schema | PASS | {'timestamp': 3598} |
| C5 alignment | **REPORT** (see below) | vendor first-open vs official: n=2707 min=0.000000 med=0.000312 p99=0.002521 max=0.007387; vendor last-close vs official: n=2707 min=0.000000 med=0.000536 p99=0.003147 max=0.010783; vendor return diff: n=2706 min=0.000000 med=0.000778 p99=0.004403 max=0.011669 |
| C6 native opens | FAIL | 856/859 sessions with first-open == official open exactly; mismatches: [['2025-02-01', '2025-02-01T09:15:00', 23538.3, 23528.6], ['2026-02-25', '2026-02-24T09:15:00', 25641.8, 25512.6], ['2026-03-02', '2026-02-27T09:15:00', 25459.85, 24659.25]] |

## C5 — day-boundary alignment vs the certified 1d store

Relative differences [n, min, median, p99, max] in bp (x1e4):

- **Vendor era (2012-01-02 → 2023-01-31, ~2,700 sessions):** first-bar open vs official open `n=2707 min=0.000000 med=0.000312 p99=0.002521 max=0.007387`; last-bar close vs official close `n=2707 min=0.000000 med=0.000536 p99=0.003147 max=0.010783`; close-to-close return diff `n=2706 min=0.000000 med=0.000778 p99=0.004403 max=0.011669`.
- **Native era (2023-03-01 → present, ~880 sessions):** first-bar open vs official open `n=880 min=0.000000 med=0.000000 p99=0.000000 max=0.032467`; last-bar close vs official close `n=880 min=0.000000 med=0.000407 p99=0.002412 max=0.005115`; return diff `n=879 min=0.000000 med=0.000560 p99=0.003308 max=0.007413`.

Interpretation: the vendor era has no official 09:15 auction bar (first bar labeled 09:16) and no official-close print (last bar labeled 15:30); its boundary prints deviate from the official index by median ~3-5 bp, p99 ~25-32 bp, max ~74-108 bp, while intraday high/low match official exactly (sampled). The native era carries the exact auction open (C6) and its last bar is 15:29 — the residual ~4 bp median vs the official 15:30 close is the expected last-minute move.

## Defect register

| Class | Sessions | Detail |
|---|---|---|
| Regular block hole | 11 run(s) | 2018-05-02..2018-05-04 (3), 2018-05-07..2018-05-11 (5), 2018-05-14..2018-05-18 (5), 2018-05-21..2018-05-25 (5), 2018-05-28..2018-05-31 (4), 2026-08-25..2026-08-26 (2), 2023-02-01..2023-02-03 (3), 2023-02-06..2023-02-10 (5), 2023-02-13..2023-02-17 (5), 2023-02-20..2023-02-24 (5), 2023-02-27..2023-03-01 (3), 2026-08-24..2026-08-24 (1) |
| Regular single holes | 1 | 2026-08-24 |
| Special sessions absent from 1m | 12 | 2012-11-13, 2013-11-03, 2014-10-23, 2015-11-11, 2016-10-30, 2017-10-19, 2018-11-07, 2019-10-27, 2020-11-14, 2021-11-04, 2022-10-24, 2026-02-01 (Diwali Muhurat / Saturday specials present in the 1d calendar) |
| Recent ingest lag | 2 | 2026-08-25, 2026-08-26 |

**Special sessions (12) — out-of-shape, not defects for A:** 2012-11-13, 2013-11-03, 2014-10-23, 2015-11-11, 2016-10-30, 2017-10-19, 2018-11-07, 2019-10-27, 2020-11-14, 2021-11-04, 2022-10-24, 2026-02-01. All are Diwali Muhurat / evening special sessions: the vendor CSV carries them with evening timestamps (verified 17:23-18:32 on 2018-11-07, 18:23 on 2014-10-23), the 1m store's session-hour filter (09:15-15:30) excludes them by design, and the construct skips them by construction (no morning opening drive exists). They remain in the 1d calendar for continuity. **No fill is possible or needed** — filling them would require mutating the committed ingest's session filter for zero construct value.

**Permanent in-scope holes:** 2018-05-02..31 (22 sessions — absent from the vendor CSV itself; confirmed 0 rows for 201805xx in the source) and 2023-02-01..03-01 (20 sessions — vendor/native transition; vendor CSV ends 2023-01-31, Upstox cannot backfill). Plus recent lag 2026-08-24..26.

**Native-era first-bar defects (C6):** 2025-02-01 (first-bar open 4 bp off official — special session); 2026-02-25 and 2026-03-02 (first bar carries the PREVIOUS session's date stamp and open — live-ingest artifact; 50 bp and 3.25% off official respectively). The construct must skip sessions whose first bar is not stamped with the session date, or these must be repaired before the sealed window is read.

Snapshot: `data/a_index_intraday/index_slice_certification.json`

## Construct impact (amendment inputs for A_CONSTRUCT_DEFINITION.md)

1. **Signal base:** the vendor era has no 09:15 auction bar. The base must be 'the opening print (first bar open)' — era-consistent semantics; the vendor first bar approximates the auction (median 3.2 bp, p99 25 bp, max 74 bp).
2. **Exit fidelity:** the vendor-era last-bar close deviates from the official close (median 5.4 bp, p99 32 bp, max 108 bp). The pre-registration must choose between accepting this as a disclosed modeling assumption (distribution recorded here) or adding an exit-fidelity cost lane.
3. **Availability:** TRAIN loses the 2018-05 block (22 sessions) and singles; HOLDOUT loses ~6 specials; SEALED loses 2023-02-01..03-01 (20 sessions) and 2026 specials. Fences unchanged.
