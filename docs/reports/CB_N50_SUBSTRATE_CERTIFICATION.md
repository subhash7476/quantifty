# CB-N50 Substrate Certification — Phase 1
Generated: 2026-08-01

**Overall: PASS**

## Membership Source

Constituent lists are from the official NSE Monthly Constituent Weight Bulletin (MCWB) data, tabulated from NSE-published PDFs. The data files are:
- `data/reference/nifty50_pit_membership.json` — 127 months, 2016-01-01 -> 2026-07-01
- `data/reference/nifty50_pit_weights.json` — 127 months of free-float weights, available for breadth scoring in TRAIN build

**Provenance notes:** Two months (2018-05-01, 2026-07-01) were not available in the MCWB archive and are filled from the preceding month's bulletin. All symbols including special characters (e.g. `M&M`, `BAJAJ-AUTO`) are preserved exactly as they appear in the MCWB data.

---

## G1 — Universe
**PASS: True**
Official Nifty 50 PIT membership from NSE Monthly Constituent Weight Bulletins (MCWB). Source: tabulated NSE PDFs. Each trade date's membership is the bulletin for its month (YYYY-MM-01). Two months (2018-05-01, 2026-07-01) were not available in the MCWB archive and are filled from the preceding month's bulletin.

- **n_dates_checked**: 20
- **n_dates_ok**: 17
- **n_dates_missing**: 3
- **total_constituent_dates_checked**: 1009
- **total_constituent_dates_present**: 1005
- **coverage_rate**: 99.6
- **coverage_threshold**: 95%
- **membership_source**: F:\Nifty\data\reference\nifty50_pit_membership.json
- **n_membership_months**: 127
- **membership_date_range**: 2016-01-01 -> 2026-07-01

#### Fill notes
- **2018-05-01**: MCWB bulletin not available; filled from 2018-04-01
- **2026-07-01**: MCWB bulletin not available; filled from 2026-06-01

### Sample checks (20 dates)
- 2016-06-02: OK (51/51 present)
- 2016-06-10: OK (51/51 present)
- 2016-06-30: OK (51/51 present)
- 2016-07-13: OK (51/51 present)
- 2017-06-12: OK (51/51 present)
- 2017-07-20: OK (51/51 present)
- 2017-09-12: OK (50/50 present)
- 2017-11-06: OK (50/50 present)
- 2018-04-24: OK (50/50 present)
- 2019-08-16: OK (50/50 present)

## G2 — Data Coverage
**PASS: True**
Official Nifty 50 PIT constituent equity bhavcopy availability, 2016-01-01 -> 2026-07-31. Membership per MCWB month key; missing months fall back to previous available bulletin.

- **total_constituent_dates**: 131550
- **total_misses**: 138
- **miss_rate**: 0.105
- **threshold**: 1%
- **dates_checked**: 2621
- **dates_below_30**: 0

#### Top missing symbols
- DUMMYHDLVR: 42 dates
- DUMMYREL: 21 dates
- DUMMYTATAM: 21 dates
- ITCHOTELS: 20 dates
- TMPV: 15 dates
- JIOFIN: 13 dates
- ETERNAL: 6 dates

## G3 — Futures
**PASS: True**
Nifty futures data availability + roll date identification

- **futures_date_range**: 2016-02-11 to 2026-07-31
- **n_trade_dates**: 2582
- **n_total_rows**: 7746
- **n_expiries**: 131
- **n_gaps_gt_5d**: 0
- **roll_dates_total**: 130

## G4 — Execution Price
**PASS: True**
Nifty futures near-month open auction prices

- **total_contract_dates**: 2582
- **open_valid**: 2582
- **open_zero**: 0
- **open_valid_rate**: 100.0
- **threshold**: 90%

## G5 — Roll Rule
**PASS: True**
Roll rule (2 days before expiry) is mechanically applicable

- **total_trade_dates**: 2582
- **total_roll_dates**: 355

## Weights Data

Nifty 50 free-float weight data from NSE MCWB bulletins (data/reference/nifty50_pit_weights.json). Format: {'YYYY-MM-01': {'SYMBOL': weight_pct, ...}}. Weights are available but not consumed by substrate certification; they are needed for breadth score computation during TRAIN build.
- **n_months**: 127
- **date_range**: 2016-01-01 -> 2026-07-01
