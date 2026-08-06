# SE-3 — Confirmatory Substrate Certification (Phase 1)

**Window:** 2016-02-11 -> 2022-12-31 (inclusive) | **Run:** script-generated, no hand-edited numbers
**Variant A only.** NIFTY index-option leg 2016-02-11 -> 2022-12-31 is NOT read by this run and remains unread.

## 1. Fence proof (S6)

- stock options: observed `trade_date` range [2016-02-11, 2022-12-30]
- stock futures: observed `trade_date` range [2016-02-11, 2022-12-30]
- Hard assertion per source: `assert FENCE_START <= min and max <= FENCE_END` — **PASSED**

## 2. Window ledger (post-run)

| Leg | Window | State entering this run | State after |
|---|---|---|---|
| **OPTSTK stock options** | **2016-02-11 -> 2022-12-31** | Skew-exposed 2016-07->2020-12; **unspent** 2021-01->2022-12 | **SPENT — this is the confirmatory read** |
| NIFTY index options | 2016-02-11 -> 2022-12-31 | Unread, 1,701 dates | **Unread — variant A does not touch the index leg** |
| OPTSTK stock options | 2023-01-02 -> 2025-12-31 | **Spent** by the breadth probe | Unchanged — out of bounds here |
| NIFTY index options | 2023-01-02 -> 2025-12-31 | Already burned | Unchanged — out of bounds here |
| Both legs | 2026-01-01 -> 2026-07 | Unread | **Preserved — deliberately reserved** |

## 3. S1 — PIT membership

- Valid MCWB snapshots: 125 | Union of member symbols in fence: 71
- Pollution findings (DUMMY*/TMPV* excluded, reported by symbol and first-seen month): {'DUMMYREL': '2023-07-01', 'TMPV': '2025-10-01', 'DUMMYTATAM': '2025-10-01', 'DUMMYHDLVR': '2025-12-01'}
- MCWB fill(s) applied (month M missing -> latest valid snapshot before it):
  - needed snapshot 2018-05-01; filled from 2018-04-01 (applied to 21 trade dates)
- Membership resolves for every date in span: **PASS**
- S1 cardinality (lead review MEDIUM-2): every date's membership is 50 or 51 symbols — **PASS**
  - distinct roster sizes seen: [('2016-02', 50), ('2016-03', 50), ('2016-04', 50), ('2016-05', 51), ('2016-06', 51), ('2016-07', 51), ('2016-08', 51), ('2016-09', 51), ('2016-10', 51), ('2016-11', 51), ('2016-12', 51), ('2017-01', 51), ('2017-02', 51), ('2017-03', 51), ('2017-04', 51), ('2017-05', 51), ('2017-06', 51), ('2017-07', 51), ('2017-08', 51), ('2017-09', 51), ('2017-10', 50), ('2017-11', 50), ('2017-12', 50), ('2018-01', 50), ('2018-02', 50), ('2018-03', 50), ('2018-04', 50), ('2018-05', 50), ('2018-06', 50), ('2018-07', 50), ('2018-08', 50), ('2018-09', 50), ('2018-10', 50), ('2018-11', 50), ('2018-12', 50), ('2019-01', 50), ('2019-02', 50), ('2019-03', 50), ('2019-04', 50), ('2019-05', 50), ('2019-06', 50), ('2019-07', 50), ('2019-08', 50), ('2019-09', 50), ('2019-10', 50), ('2019-11', 50), ('2019-12', 50), ('2020-01', 50), ('2020-02', 50), ('2020-03', 50), ('2020-04', 50), ('2020-05', 50), ('2020-06', 50), ('2020-07', 50), ('2020-08', 50), ('2020-09', 50), ('2020-10', 50), ('2020-11', 50), ('2020-12', 50), ('2021-01', 50), ('2021-02', 50), ('2021-03', 50), ('2021-04', 50), ('2021-05', 50), ('2021-06', 50), ('2021-07', 50), ('2021-08', 50), ('2021-09', 50), ('2021-10', 50), ('2021-11', 50), ('2021-12', 50), ('2022-01', 50), ('2022-02', 50), ('2022-03', 50), ('2022-04', 50), ('2022-05', 50), ('2022-06', 50), ('2022-07', 50), ('2022-08', 50), ('2022-09', 50), ('2022-10', 50), ('2022-11', 50), ('2022-12', 50)]
  - the 51-symbol case is the DVR era — TATAMTRDVR double-listed alongside TATAMOTORS (2016-2017); months: [datetime.date(2016, 5, 2), datetime.date(2016, 5, 3), datetime.date(2016, 5, 4), datetime.date(2016, 5, 5), datetime.date(2016, 5, 6), datetime.date(2016, 5, 9), datetime.date(2016, 5, 10), datetime.date(2016, 5, 11), datetime.date(2016, 5, 12), datetime.date(2016, 5, 13), datetime.date(2016, 5, 16), datetime.date(2016, 5, 17), datetime.date(2016, 5, 18), datetime.date(2016, 5, 19), datetime.date(2016, 5, 20), datetime.date(2016, 5, 23), datetime.date(2016, 5, 24), datetime.date(2016, 5, 25), datetime.date(2016, 5, 26), datetime.date(2016, 5, 27), datetime.date(2016, 5, 30), datetime.date(2016, 5, 31), datetime.date(2016, 6, 1), datetime.date(2016, 6, 2), datetime.date(2016, 6, 3), datetime.date(2016, 6, 6), datetime.date(2016, 6, 7), datetime.date(2016, 6, 8), datetime.date(2016, 6, 9), datetime.date(2016, 6, 10), datetime.date(2016, 6, 13), datetime.date(2016, 6, 14), datetime.date(2016, 6, 15), datetime.date(2016, 6, 16), datetime.date(2016, 6, 17), datetime.date(2016, 6, 20), datetime.date(2016, 6, 21), datetime.date(2016, 6, 22), datetime.date(2016, 6, 23), datetime.date(2016, 6, 24), datetime.date(2016, 6, 27), datetime.date(2016, 6, 28), datetime.date(2016, 6, 29), datetime.date(2016, 6, 30), datetime.date(2016, 7, 1), datetime.date(2016, 7, 4), datetime.date(2016, 7, 5), datetime.date(2016, 7, 7), datetime.date(2016, 7, 8), datetime.date(2016, 7, 11), datetime.date(2016, 7, 12), datetime.date(2016, 7, 13), datetime.date(2016, 7, 14), datetime.date(2016, 7, 15), datetime.date(2016, 7, 18), datetime.date(2016, 7, 19), datetime.date(2016, 7, 20), datetime.date(2016, 7, 21), datetime.date(2016, 7, 22), datetime.date(2016, 7, 25), datetime.date(2016, 7, 26), datetime.date(2016, 7, 27), datetime.date(2016, 7, 28), datetime.date(2016, 7, 29), datetime.date(2016, 8, 1), datetime.date(2016, 8, 2), datetime.date(2016, 8, 3), datetime.date(2016, 8, 4), datetime.date(2016, 8, 5), datetime.date(2016, 8, 8), datetime.date(2016, 8, 9), datetime.date(2016, 8, 10), datetime.date(2016, 8, 11), datetime.date(2016, 8, 12), datetime.date(2016, 8, 16), datetime.date(2016, 8, 17), datetime.date(2016, 8, 18), datetime.date(2016, 8, 19), datetime.date(2016, 8, 22), datetime.date(2016, 8, 23), datetime.date(2016, 8, 24), datetime.date(2016, 8, 25), datetime.date(2016, 8, 26), datetime.date(2016, 8, 29), datetime.date(2016, 8, 30), datetime.date(2016, 8, 31), datetime.date(2016, 9, 1), datetime.date(2016, 9, 2), datetime.date(2016, 9, 6), datetime.date(2016, 9, 7), datetime.date(2016, 9, 8), datetime.date(2016, 9, 9), datetime.date(2016, 9, 12), datetime.date(2016, 9, 14), datetime.date(2016, 9, 15), datetime.date(2016, 9, 16), datetime.date(2016, 9, 19), datetime.date(2016, 9, 20), datetime.date(2016, 9, 21), datetime.date(2016, 9, 22), datetime.date(2016, 9, 23), datetime.date(2016, 9, 26), datetime.date(2016, 9, 27), datetime.date(2016, 9, 28), datetime.date(2016, 9, 29), datetime.date(2016, 9, 30), datetime.date(2016, 10, 3), datetime.date(2016, 10, 4), datetime.date(2016, 10, 5), datetime.date(2016, 10, 6), datetime.date(2016, 10, 7), datetime.date(2016, 10, 10), datetime.date(2016, 10, 13), datetime.date(2016, 10, 14), datetime.date(2016, 10, 17), datetime.date(2016, 10, 18), datetime.date(2016, 10, 19), datetime.date(2016, 10, 20), datetime.date(2016, 10, 21), datetime.date(2016, 10, 24), datetime.date(2016, 10, 25), datetime.date(2016, 10, 26), datetime.date(2016, 10, 27), datetime.date(2016, 10, 28), datetime.date(2016, 11, 1), datetime.date(2016, 11, 2), datetime.date(2016, 11, 3), datetime.date(2016, 11, 4), datetime.date(2016, 11, 7), datetime.date(2016, 11, 8), datetime.date(2016, 11, 9), datetime.date(2016, 11, 10), datetime.date(2016, 11, 11), datetime.date(2016, 11, 15), datetime.date(2016, 11, 16), datetime.date(2016, 11, 17), datetime.date(2016, 11, 18), datetime.date(2016, 11, 21), datetime.date(2016, 11, 22), datetime.date(2016, 11, 23), datetime.date(2016, 11, 24), datetime.date(2016, 11, 25), datetime.date(2016, 11, 28), datetime.date(2016, 11, 29), datetime.date(2016, 11, 30), datetime.date(2016, 12, 1), datetime.date(2016, 12, 2), datetime.date(2016, 12, 5), datetime.date(2016, 12, 6), datetime.date(2016, 12, 7), datetime.date(2016, 12, 8), datetime.date(2016, 12, 9), datetime.date(2016, 12, 12), datetime.date(2016, 12, 13), datetime.date(2016, 12, 14), datetime.date(2016, 12, 15), datetime.date(2016, 12, 16), datetime.date(2016, 12, 19), datetime.date(2016, 12, 20), datetime.date(2016, 12, 21), datetime.date(2016, 12, 22), datetime.date(2016, 12, 23), datetime.date(2016, 12, 26), datetime.date(2016, 12, 27), datetime.date(2016, 12, 28), datetime.date(2016, 12, 29), datetime.date(2016, 12, 30), datetime.date(2017, 1, 2), datetime.date(2017, 1, 3), datetime.date(2017, 1, 4), datetime.date(2017, 1, 5), datetime.date(2017, 1, 6), datetime.date(2017, 1, 9), datetime.date(2017, 1, 10), datetime.date(2017, 1, 11), datetime.date(2017, 1, 12), datetime.date(2017, 1, 13), datetime.date(2017, 1, 16), datetime.date(2017, 1, 17), datetime.date(2017, 1, 18), datetime.date(2017, 1, 19), datetime.date(2017, 1, 20), datetime.date(2017, 1, 23), datetime.date(2017, 1, 24), datetime.date(2017, 1, 25), datetime.date(2017, 1, 27), datetime.date(2017, 1, 30), datetime.date(2017, 1, 31), datetime.date(2017, 2, 1), datetime.date(2017, 2, 2), datetime.date(2017, 2, 3), datetime.date(2017, 2, 6), datetime.date(2017, 2, 7), datetime.date(2017, 2, 8), datetime.date(2017, 2, 9), datetime.date(2017, 2, 10), datetime.date(2017, 2, 13), datetime.date(2017, 2, 14), datetime.date(2017, 2, 15), datetime.date(2017, 2, 16), datetime.date(2017, 2, 17), datetime.date(2017, 2, 20), datetime.date(2017, 2, 21), datetime.date(2017, 2, 22), datetime.date(2017, 2, 23), datetime.date(2017, 2, 27), datetime.date(2017, 2, 28), datetime.date(2017, 3, 1), datetime.date(2017, 3, 2), datetime.date(2017, 3, 3), datetime.date(2017, 3, 6), datetime.date(2017, 3, 7), datetime.date(2017, 3, 8), datetime.date(2017, 3, 9), datetime.date(2017, 3, 10), datetime.date(2017, 3, 14), datetime.date(2017, 3, 15), datetime.date(2017, 3, 16), datetime.date(2017, 3, 17), datetime.date(2017, 3, 20), datetime.date(2017, 3, 21), datetime.date(2017, 3, 22), datetime.date(2017, 3, 23), datetime.date(2017, 3, 24), datetime.date(2017, 3, 27), datetime.date(2017, 3, 28), datetime.date(2017, 3, 29), datetime.date(2017, 3, 30), datetime.date(2017, 3, 31), datetime.date(2017, 4, 3), datetime.date(2017, 4, 5), datetime.date(2017, 4, 6), datetime.date(2017, 4, 7), datetime.date(2017, 4, 10), datetime.date(2017, 4, 11), datetime.date(2017, 4, 12), datetime.date(2017, 4, 13), datetime.date(2017, 4, 17), datetime.date(2017, 4, 18), datetime.date(2017, 4, 19), datetime.date(2017, 4, 20), datetime.date(2017, 4, 21), datetime.date(2017, 4, 24), datetime.date(2017, 4, 25), datetime.date(2017, 4, 26), datetime.date(2017, 4, 27), datetime.date(2017, 4, 28), datetime.date(2017, 5, 2), datetime.date(2017, 5, 3), datetime.date(2017, 5, 4), datetime.date(2017, 5, 5), datetime.date(2017, 5, 8), datetime.date(2017, 5, 9), datetime.date(2017, 5, 10), datetime.date(2017, 5, 11), datetime.date(2017, 5, 12), datetime.date(2017, 5, 15), datetime.date(2017, 5, 16), datetime.date(2017, 5, 17), datetime.date(2017, 5, 18), datetime.date(2017, 5, 19), datetime.date(2017, 5, 22), datetime.date(2017, 5, 23), datetime.date(2017, 5, 24), datetime.date(2017, 5, 25), datetime.date(2017, 5, 26), datetime.date(2017, 5, 29), datetime.date(2017, 5, 30), datetime.date(2017, 5, 31), datetime.date(2017, 6, 1), datetime.date(2017, 6, 2), datetime.date(2017, 6, 5), datetime.date(2017, 6, 6), datetime.date(2017, 6, 7), datetime.date(2017, 6, 8), datetime.date(2017, 6, 9), datetime.date(2017, 6, 12), datetime.date(2017, 6, 13), datetime.date(2017, 6, 14), datetime.date(2017, 6, 15), datetime.date(2017, 6, 16), datetime.date(2017, 6, 19), datetime.date(2017, 6, 20), datetime.date(2017, 6, 21), datetime.date(2017, 6, 22), datetime.date(2017, 6, 23), datetime.date(2017, 6, 27), datetime.date(2017, 6, 28), datetime.date(2017, 6, 29), datetime.date(2017, 6, 30), datetime.date(2017, 7, 3), datetime.date(2017, 7, 4), datetime.date(2017, 7, 5), datetime.date(2017, 7, 6), datetime.date(2017, 7, 7), datetime.date(2017, 7, 10), datetime.date(2017, 7, 11), datetime.date(2017, 7, 12), datetime.date(2017, 7, 13), datetime.date(2017, 7, 14), datetime.date(2017, 7, 17), datetime.date(2017, 7, 18), datetime.date(2017, 7, 19), datetime.date(2017, 7, 20), datetime.date(2017, 7, 21), datetime.date(2017, 7, 24), datetime.date(2017, 7, 25), datetime.date(2017, 7, 26), datetime.date(2017, 7, 27), datetime.date(2017, 7, 28), datetime.date(2017, 7, 31), datetime.date(2017, 8, 1), datetime.date(2017, 8, 2), datetime.date(2017, 8, 3), datetime.date(2017, 8, 4), datetime.date(2017, 8, 7), datetime.date(2017, 8, 8), datetime.date(2017, 8, 9), datetime.date(2017, 8, 10), datetime.date(2017, 8, 11), datetime.date(2017, 8, 14), datetime.date(2017, 8, 16), datetime.date(2017, 8, 17), datetime.date(2017, 8, 18), datetime.date(2017, 8, 21), datetime.date(2017, 8, 22), datetime.date(2017, 8, 23), datetime.date(2017, 8, 24), datetime.date(2017, 8, 28), datetime.date(2017, 8, 29), datetime.date(2017, 8, 30), datetime.date(2017, 8, 31), datetime.date(2017, 9, 1), datetime.date(2017, 9, 4), datetime.date(2017, 9, 5), datetime.date(2017, 9, 6), datetime.date(2017, 9, 7), datetime.date(2017, 9, 8), datetime.date(2017, 9, 11), datetime.date(2017, 9, 12), datetime.date(2017, 9, 13), datetime.date(2017, 9, 14), datetime.date(2017, 9, 15), datetime.date(2017, 9, 18), datetime.date(2017, 9, 19), datetime.date(2017, 9, 20), datetime.date(2017, 9, 21), datetime.date(2017, 9, 22), datetime.date(2017, 9, 25), datetime.date(2017, 9, 26), datetime.date(2017, 9, 27), datetime.date(2017, 9, 28), datetime.date(2017, 9, 29)]
  - cardinality issues (any count outside {50, 51}): none

## 4. Attrition (absolute row counts)

| Stage | Rows |
|---|---|
| Rows in fence, member universe | 20,616,246 |
| Traded (contracts>0, OI>0) | 3,897,393 |
| §3.2 no expiry in [7,60] (date-name) | 82 |
| §3.3 no forward (date-name) | 0 |
| §3.4 no ATM IV cell (date-name) | 113 |
| IV inversion discard (A9) | 1/169325 (0.0%) |

## 5. S5 — IV inversion discard rate by year

| Year | attempted | discarded | rate |
|---|---|---|---|
| 2016 | 21682 | 0 | 0.0% |
| 2017 | 24703 | 0 | 0.0% |
| 2018 | 24416 | 0 | 0.0% |
| 2019 | 24381 | 0 | 0.0% |
| 2020 | 24702 | 1 | 0.0% |
| 2021 | 24646 | 0 | 0.0% |
| 2022 | 24795 | 0 | 0.0% |

## 6. S2 — names/day surviving A1-A11, by year

| Year | median names/day | p10 | p90 |
|---|---|---|---|
| 2016 | 50 | 49 | 51 |
| 2017 | 50 | 50 | 51 |
| 2018 | 50 | 49 | 50 |
| 2019 | 50 | 50 | 50 |
| 2020 | 50 | 50 | 50 |
| 2021 | 50 | 50 | 50 |
| 2022 | 50 | 50 | 50 |

## 7. S3 — usable-date waterfall vs 1,701

| Line | Count |
|---|---|
| trading dates 2016-02-11 .. 2022-12-31 (stock-options store) | 1701 |
|   - dates before first usable formation date (A10 RV warmup: 2016-03-10) | -19 |
|   - tail dates with no t+1 / t+2 pair inside the fence | -2 |
|   - dates with < 20 names surviving A1-A11 (richness computable) | -0 |
|   - dates with < 20 PAIRED names for the IC (A13) | -0 |
| **= USABLE CONFIRMATORY FORMATION DATES** | **1680** |

**S3: PASS** — usable dates 1680 vs `S3_MIN_USABLE_DATES = 756`.
At or above 756: every claim about the declared band's central case survives; the run proceeds with the shortfall reported.

## 8. Implementation notes

- Reuses `implied_vol`, `_parity_forward` from `scripts/osc/sd_probe.py` (A14). No reimplementation.
- Variant B absent; no index-options database reference anywhere in this module (tested).
- 2018-05 MCWB fill per operator decision 2026-08-05 (April and June 2018 rosters verified identical).
- Nothing under `data/` is written (read-only).
