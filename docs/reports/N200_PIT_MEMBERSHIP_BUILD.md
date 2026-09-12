# Nifty 200 PIT Membership (A1) — Build Report

**Date:** 2026-09-12 · **Store:** `data/isd/n200_membership.duckdb`
(`n200_events`, `n200_membership`, `n200_audit`)
**Sources:** 228 NSE/IISL press releases (`data/reference/nse_index_pr/`,
`manifest.csv`, plus `ind_prs23082021.ocr.txt` — the committed OCR transcript of
the one scanned release, manifest row carries both sha256s) + today's official lists (`ind_nifty200list_20260912.csv`,
`ind_nifty100list_20260912.csv`, `ind_niftymidcap100list_20260912.csv`)
+ NSE symbol-change records (`equity_bhavcopy.duckdb:symbol_changes`).
**Builder:** `scripts/isd/build_n200_membership.py` (parse → backward walk
from anchor → forward replay → gates).

## Method (one paragraph)

Every press release is parsed into dated
`(effective_date, index, action, company, symbol)` events (handles numbered
tables, two-column layouts, wrapped rows/symbols, scanned-image OCR, single-
company notices, revocation tables, ticker renames). Each event carries
`symbol_status` (`parsed / resolved_company / resolved_alias /
superseded / duplicate / void_covid / manual_delisting`). The N200 chain
walks backward from today's official 200 list through reverse-dated official
changes, then replays forward into `[valid_from, valid_to)` intervals.
Renames use exact effective dates from NSE's own `symbol_changes` table
(18 pairs, asserted present or the build fails).

## Gates (all green)

| Gate | Result |
|---|---|
| Backward breaks | **0** |
| Terminal open set vs today's official 200 | **exact match (200/200, EXTRA 0 / MISSING 0)** |
| Canonical per-symbol parity (events vs intervals) | **0 violators** |
| Missing symbols / missing effective dates (N200) | **0 / 0** |
| Member counts | **200 every session** except documented deviations below |
| **Union reconciliation** (Nifty 200 = Nifty 100 + Nifty Midcap 100, 2018-06-29 →) | **42 dates checked, 0 mismatches** |

## Documented deviations (all with named causes)

- **DVR as 201st security:** 2016-04-01 → 2020-06-26 and 2023-09-29 →
  2024-08-30 counts read 201. Each episode is a stated NSE decision
  ("the Nifty 200 index shall have 201 securities", ind_prs22022016_2.pdf).
- **Mar-2020 COVID void:** reviews w.e.f. 2020-03-27 were deferred
  (ind_prs23032020/25032020) then declared **null and void** except N50/Bank
  (ind_prs13052020); review re-run w.e.f. 2020-06-26. Keyed on the **effective
  date**, not a file list — the source voids the releases dated Feb 18, Mar 12
  and Mar **19**, and a filename set previously named Mar **16** instead.
  **604 rows** marked `void_covid`.
- **Revocations:** Sep-2024 IDEA/CentralBank and Mar-2024 IREDA inclusions
  cancelled by later PRs (28 directives → `superseded`).
- **ABIRLANUVO exit 2017-07-05:** delisted (trading suspended w.e.f.
  2017-07-05 per NSE circular CML35172 dtd 2017-07-04). **No IISL exclusion
  PR exists anywhere in the 228-file archive** (verified by full-text
  search). Interval closed at suspension, status `manual_delisting` —
  the single non-PR-sourced boundary in the table.
- **Future-announced:** Sep-30-2026 review (14 events) parsed but held out
  of the walk (effective > anchor date 2026-09-11).

## Residuals (known, bounded)

1. **Pre-Apr-2016 count reads 201, not 200** (all other eras exact).
   Cause: two launch-state members are provably impossible —
   **MGL** (listed 2016-07-01) and **PNBHOUSING** (listed 2016-11-07) per
   `instrument_master` — yet both have genuine parsed demotion exits
   (Mar-2022 / Sep-2020, multi-section, balanced reviews). Their N200/
   Midcap100 **entries appear in no press release in the archive**
   (every 2016-2022 review verified present; full-text search clean).
   Net composition error pre-2016 is therefore **+1 member**
   (2 phantoms − 1 unidentified absentee), i.e. ≤2 names out of ~200.
   Entry bounds from listing + 3-month IPO rule: MGL ∈ [2017-03, 2022-03),
   PNBHOUSING ∈ [2017-09, 2020-09).
2. **Launch composition (2011-07-19) rests on backward induction**
   (no public inaugural list exists); it satisfies count==200 only up to
   the +1 above. Era labels across the 18 renames are exact per
   `symbol_changes` effective dates.
3. For A1 consumption (monthly formations, 2012+): from ~2018 on the
   table is **exact** (terminal gate proves the full 2012→present walk
   reproduces today's list; every post-2018 event is sourced). The
   2011–2017 span carries bounded uncertainty (the two phantoms above
   are wrongly eligible from 2011 instead of their true ~2017 entries,
   one true member wrongly ineligible over the same span) — ≤2 names out
   of ~200, immaterial to any diversified cross-sectional result but
   disclosed here.

## Usage

```sql
-- members on DATE 'D'
select symbol from n200_membership
where valid_from <= DATE 'D' and (valid_to is null or valid_to > DATE 'D');
```

Symbols are **as-printed at the time** (era-correct across renames);
join to prices via `symbol_entity_intervals`/ISIN as usual.
Reproduce: `python scripts/isd/build_n200_membership.py`.
