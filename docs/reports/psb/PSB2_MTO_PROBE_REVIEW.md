# MTO Feasibility Probe — Lead Review (Roadmap Phase 0.1)

**Date:** 2026-07-17
**Reviewer:** Claude (Lead Reviewer). Download executed by DeepSeek V4 via `scripts/probe_historical_mto.py`.
**Scope:** `data/mto_probe/` (2,717 files, 154 MB), reviewed read-only against `data/market_data/equity_bhavcopy.duckdb`. No store writes; sealed window untouched (probe span 2010–2020 is entirely pre-fence).

## Verdict: **PASS** — G0.1 cleared. Phase 0.2 (MTO parser + store backfill) is unblocked, subject to the requirements in §5.

The scoping question (`PSB2_DELIVERY_HISTORY_SCOPING.md`) is answered definitively: the pre-2020 delivery data exists, is served by NSE's archive for the **entire** 2010–2020 span, parses cleanly, and — on the 2020 overlap — is **byte-equivalent to the SECFULL data already in the store**.

## 1. Coverage (criterion 1)

| Year | Files | | Year | Files |
|---|---|---|---|---|
| 2010 | 251 | | 2016 | 246 |
| 2011 | 247 | | 2017 | 248 |
| 2012 | 247 | | 2018 | 246 |
| 2013 | 248 | | 2019 | 244 |
| 2014 | 243 | | 2020 | 250 |
| 2015 | 247 | | **Total** | **2,717** |

Against the store's own trading calendar (2,732 trading days 2010–2020): **2,717 matched, 15 missing, 0 spurious** (no MTO file exists for a non-trading day). All 15 missing days are **Saturday/Sunday special sessions** (Muhurat sessions, 2020-02-01 budget Saturday, etc.) — the probe's date generator yields weekdays only (`trading_days()` filters `weekday() < 5`), so these were never requested. This is a probe-script limitation, not an archive gap; the 15 dates are enumerable from the store calendar and must be fetched in Phase 0.2.

## 2. Format (criterion 2)

Spot-checked 2010 / 2014 / 2019 / 2020 files. Layout is **stable comma-separated** across all eras (not fixed-width as the scoping doc feared):

- Header records: type `10` (file header with date), a `Trade Date <...>` line, and a column-header line.
- Data records: `20,<srno>,<SYMBOL>,<SERIES>,<qty_traded>,<deliv_qty>,<deliv_pct>` — **7 fields**.
- **Parser trap:** the human-readable column-header line lists only 6 columns (it omits the series column that data rows carry). Any header-driven parser will mis-map; parse by record type and position.
- Era variant: the 2020-12-31 `Trade Date` line omits Settlement No/Date fields — harmless; do not key on that line's field count.
- Zero undersized/corrupt files (no file < 2 KB); zero implausible values in sampled days (all `0 ≤ deliv_pct ≤ 100`, all `deliv_qty ≤ qty_traded`).

## 3. Store reconciliation (criterion 3) — the decisive result

**2020 overlap (MTO vs SECFULL-derived store values), series EQ:**

| Date | Common symbols | deliv_qty exact match | deliv_pct within 0.01 |
|---|---|---|---|
| 2020-06-01 | 1,515 | **1,515 / 1,515** | 1,515 / 1,515 |
| 2020-12-31 | 1,481 | **1,481 / 1,481** | 1,481 / 1,481 |

MTO and SECFULL report the **same underlying data** — the backfill introduces no source-inconsistency seam at the 2020 boundary.

**Pre-2020 symbol join (MTO EQ symbols vs store EQ rows, same date):**

| Date | MTO EQ | Store EQ | Overlap |
|---|---|---|---|
| 2010-01-04 | 1,223 | 1,223 | **100.0%** (0 unmatched either side) |
| 2014-07-01 | 1,190 | 1,190 | **100.0%** |
| 2019-01-02 | 1,493 | 1,493 | **100.0%** |

The join is exact at symbol+series+date grain on every sampled date. (Store-side rename/entity handling is unaffected — the backfill writes at the same raw symbol grain the store already uses.)

**Series scope:** MTO carries EQ, SM, GB, and bond/ETF series — **no BE rows**. This is *consistent* with the store's existing convention: SECFULL also provides no BE delivery (318,766 post-2020 BE rows, 0 non-NULL `deliv_pct`). BE is trade-for-trade (delivery compulsory by definition). The backfill therefore leaves BE `deliv_pct` NULL exactly as SECFULL does — no new inconsistency; whether BE should be *defined* as 100% is a protocol-level question for the C2-VAL pre-registration, not an ingester decision.

## 4. Write containment (criterion 4)

All artifacts confined to `data/mto_probe/`. `git status`: only the expected docs and the probe script itself; store file untouched (opened read-only in this review).

## 5. Requirements carried into Phase 0.2 (backfill)

1. **Fetch the 15 weekend special-session files** — drive the ingest date list from the store's trading calendar, never from a weekday generator (the CSMP gate-(a) lesson, again).
2. **Parse by record type/position**, not the 6-column header line; handle the 2020 `Trade Date` line variant.
3. **EQ-series backfill only** into `deliv_qty`/`deliv_pct` (matching SECFULL semantics); other MTO series (SM/GB/N*) are out of scope for C2's NIFTY-200 universe.
4. **Copy-first discipline:** backfill a copy of the store, diff, swap; then re-run the four-arm contract suite (`scripts/psb1/certify_substrate.py`) before any C2 re-estimation. The substrate certification is void until re-certified.
5. **Era map extension:** MTO becomes a fourth source era (delivery-only, 2010–2019); SECFULL still wins from 2020-01-01. Per-date source provenance must be recorded as the existing eras are.
6. Bonus fact for Phase 0.4: coverage reaches **2010**, not just 2012 — the delivery-z 252-day baseline can begin producing formations from ~late 2010, giving C2's SD re-estimation roughly **a decade** of formations (~240+ fortnightly) versus the current 55.

## 6. What this does *not* establish

- Nothing about C2's IC or SD on pre-2020 data — that is Phase 0.4, and it may still falsify the recommendation (that is the point of doing it before the sealed read).
- No store change has occurred; `equity_bhavcopy` is bit-identical to its certified state.
