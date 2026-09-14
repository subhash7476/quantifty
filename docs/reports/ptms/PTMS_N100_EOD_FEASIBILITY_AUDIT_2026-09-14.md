# PTMS — Nifty-100 EOD Stock-Panel Feasibility Audit

**Date:** 2026-09-14 · **Branch:** `research/ptms-price-time-market-structure`
**Type:** DATA-ONLY FEASIBILITY AUDIT. It answers one question: *do we hold a clean,
point-in-time Nifty-100 EOD stock panel from which a price-time / Gann-type hypothesis could later
be asked without survivorship bias, look-ahead or hidden universe contamination?*
It does **not** ask whether Gann works, define a construct, read an outcome, run an RFA, split
TRAIN/HOLDOUT, or select a parameter.

**Access level:** meta, plus validity predicates. Schema, row counts, dates, symbols, membership
intervals, CA/entity metadata. On price rows, only null / non-positive / OHLC-ordering predicates,
**counted**. No return, no cross-date price ratio, no signal, no label, no P&L. See §10.

---

## A. Executive verdict

**B — FEASIBLE WITH CONDITIONS.**

The substrate is materially better than the N100 discussion to date assumed:

1. **A genuine Nifty-100 PIT membership table exists.** It is not a Nifty-200 proxy:
   `data/isd/n100_membership.duckdb`, NIFTY 50 ∪ NIFTY NEXT 50, built from 228 NSE/IISL
   press releases and gated month by month against NSE's own MCWB constituent files. It resolves
   daily from **2011-03-25 → 2026-09-11**.
2. **PIT membership × EOD price joins almost perfectly.** Over 3,834 real sessions,
   **383,795 of 383,796 member-day slots carry an EOD price** (the one miss is source-side). There
   are zero invalid OHLC rows, zero pre-listing slots and zero post-delisting slots. Every member
   slot resolves to exactly one entity.
3. **The history is ~4.2× the certified 1m route:** 15.5 years and ~384k stock-days, against
   3.7 years and ~92k.

The conditions are real and none is cosmetic (§11). The EOD surface has no scoped certification.
Backward-adjusted price **levels carry look-ahead**. Spin-offs, rights issues, special and ordinary
dividends are **unadjusted**, and the CA table cannot enumerate them before ~2022. Four membership
boundaries are dated only to ±1 month. **Whether any historical window can be confirmatory is a
governance question this audit cannot settle** (§10).

---

## B. Data sources inspected

| Source | What was read |
|---|---|
| `docs/DATA_STORE_MAP.md` §1, §9, §9b, §10–§12 | Stated coverage, PIT claims, price-basis finding |
| `docs/reports/ops_data/DATABASE_CENSUS_2026-09-03.md` | Store inventory |
| `data/market_data/equity_bhavcopy.duckdb` | Schema and counts of all 17 tables/views; `equity_bhavcopy` presence and validity predicates on member rows; `trading_calendar`, `ingest_meta`, `adjustment_factors`, `corporate_actions`, `ca_*`, `symbol_changes`, `symbol_entity_intervals`, `symbol_isin`, `universe_membership`, `universe_eligibility` |
| `data/isd/n100_membership.duckdb` | `n100_membership` (263 intervals), `n100_audit` |
| `data/isd/n200_membership.duckdb` | `n200_membership` (587 intervals); `n200_events` metadata (effective/announcement dates, `eff_src`) |
| `data/reference/mcwb_manifest.json` | Month status only |
| `data/reference/nse_index_pr/*.pdf` (228) | Regex over extracted text for effective-date phrasing only |
| `data/market_data/bhavcopy_raw/secfull_20200413.csv`, `…/legacy_20160419.404` | Series counts and one symbol's presence; marker existence |
| Code | `scripts/isd/build_n100_membership.py`, `build_n200_membership.py` (effective-date parser), `scripts/csmp/build_universe.py` (turnover universe), `scripts/csmp/ingest_corporate_actions.py` (`build_adjusted_view`), `scripts/psb1/contract_arms.py` (Arm A detection) |
| Reports | `N200_PIT_MEMBERSHIP_BUILD.md`, `PTMS_N100_REVIEW_AND_A1_RESOLUTION_2026-09-13.md`, `psb/PSB1_SUBSTRATE_CERTIFICATION.md` (disposition tables), `PTMS_C2_PIT_ENTITY_CERTIFICATION_2026-09-12.md`, `PTMS_A5_RESULT_AND_C2_DISPOSITION_2026-09-12.md`, `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` |

The queries ran from uncommitted, read-only scratch scripts (`eod_coverage{,2,3}.py` in the session
scratchpad). They are not part of the repo; every figure is re-derivable from the table and column
names given. Every number below comes from a query run on 2026-09-14 against the stores as they
stood that day.

---

## C. Membership reconstruction (§1 and §4)

### C.1 What exists — three different tables, only one of which is Nifty-100

| Table | What it actually is | Span | Usable as PIT N100? |
|---|---|---|---|
| `isd/n100_membership.duckdb:n100_membership` | **Official NIFTY 100** = NIFTY 50 leg ∪ NIFTY NEXT 50 leg, each walked from NSE/IISL press releases, gated monthly vs MCWB | 2011-03-25 → open (anchor 2026-09-11) | **YES** |
| `isd/n200_membership.duckdb:n200_membership` | Official NIFTY 200 from the same PR corpus, unreconciled before 2018-06-29 | 2011-07-19 → open | No — a superset, and N100 cannot be derived from it alone |
| `equity_bhavcopy.duckdb:universe_membership` | **Not an index.** CSMP's mechanical turnover rank (`method = turnover_top200`): top 200 entities by median turnover, month-end | 177 rebalances, 2012-01-31 → 2026-09-11 | **NO** |

**The DATA_STORE_MAP phrase "PIT Nifty-200-style membership from 2012-01-31" refers to
`universe_membership`, and it is a liquidity proxy, not an index.** Measured against official N100
at its 177 rebalance dates:

| Proxy slice | Official N100 members it contains (of 100) |
|---|---|
| Turnover rank ≤ 100 | median **70** (min 59, max 80) |
| Turnover rank ≤ 200 | median **94** (min 86, max 98) |

Neither is Nifty-100, and "top-100 of the proxy" misses ~30 constituents a month. **Using it for an
N100 experiment would be hidden universe contamination.** No derivation from Nifty-200 is needed,
because the N100 table is built directly from the N50 and Next50 streams.

### C.2 How the N100 table was built — and what licenses it

- **Source:** 228 NSE/IISL press releases parsed into dated include/exclude events. The two legs,
  NIFTY 50 and NIFTY NEXT 50, are walked backward from the official lists of 2026-09-12
  (`ind_nifty100list_20260912.csv`, Next50 list). They are then replayed forward into half-open
  `[valid_from, valid_to)` intervals and relabelled era-correctly across 32 dated renames
  (31 N200 pairs plus INFOSYSTCH→INFY, asserted from `symbol_changes`).
- **Independent check:** 198 monthly NSE MCWB archives (2010-01 → 2026-07). MCWB is an
  absolute-state source: each month lists the full N50 and Next50 constituent sets, so an error
  cannot propagate. Gate G3 compares walk-implied month-end sets with MCWB sets on every valid
  month: **368 month-legs, 0 mismatches.** The 2026-09-13 review reproduced this with an
  independent parser (184 months, 0 mismatches).
- **Overrides:** 23 point edits (R1–R8), each evidence-keyed. Without them 260 of 368 month-legs
  fail, so they are load-bearing. The monthly gate constrains them, though not below a month.
- **Status:** this is the historical official constituent record, not an approximation. The residual
  imprecision is only in dating, below.

### C.3 Earliest date, latest date, daily resolution

| Question | Answer | Evidence |
|---|---|---|
| Earliest reconstructable date | **2011-03-25** | `LAUNCH_DATE` = first effective date in the corpus. The launch state is backward-induced, and MCWB-attested at the 2011-03 month-end |
| Before 2011-03-25 | **Not built.** MCWB exists for 2010-01 → 2011-02 (14 months), so a monthly-grain extension is possible, but intra-month dates would be unpinned | Builder docstring: "pre-corpus membership is MCWB-attested (2010) and out of scope" |
| Latest date | **2026-09-11** (anchor). Last composition change 2026-03-30; 100 intervals open | The Sep-30-2026 review (27 N50/Next50 events) is parsed and held out |
| Every trading day? | **Yes.** All 3,836 calendar sessions in span resolve. **0** interval boundaries fall off-calendar | Query |
| Member count per session | 100 on 3,389 · **101 on 422** · **99 on 25** | See C.5 |

### C.4 Are additions and deletions effective on known dates?

- **Convention verified in text.** 179 of 228 PRs say *"effective from D (close of D−1)"*, e.g.
  `ind_prs27022014.pdf`: "effective from March 28, 2014 (close of March 27, 2014)". So
  `valid_from = D` is the **first session of the new composition**: no one-day look-ahead and no lag.
- **49 PRs lack the "close of" phrase**, mostly 2011–2013. The same convention is assumed for them,
  **not verified file by file**.
- Effective dates are announced 2–51 days ahead (median 36). Membership at D was public before D.
- **Four boundaries are dated only to within a month.** Their month-end sets are MCWB-correct, but
  the day inside the month is inferred:

  | Override | Event | Date used | Basis |
  |---|---|---|---|
  | R5 | GRASIM out of N50, VEDL N50 in (from Next50), SUNTV Next50 in | 2017-05-26 | Inferred from a same-event strategy-index PR |
  | R7 | ACC out of Next50 / back in | 2020-09-25 / 2020-11-02 | Review-batch date / first-trading-day convention |
  | R8 | JIOFIN transient exit | 2023-09-01 | Bracket start, stated ±30d |
  | R8 | ITCHOTELS transient exit | 2025-03-28 | Review-batch date |

  Immaterial at monthly cadence. **Material at daily cadence:** up to ~4 weeks of one name's
  membership is unpinned at each boundary.

### C.5 Member-count deviations (all attested, none unexplained)

| Sessions | Count | Cause |
|---|---:|---|
| 2016-04-01 → 2017-09-28 (372 sessions) | 101 | Tata Motors DVR as an additional NIFTY 50 security (NSE-stated) |
| 2023-08-21 → 2023-08-31 (9) | 101 | JIOFIN transient after demerger listing |
| 2025-01-29 → 2025-03-27 (41) | 101 | ITCHOTELS transient after demerger listing |
| 2020-09-25 → 2020-10-30 (25) | 99 | ACC absent from Next50 in NSE's own Sep/Oct-2020 reports |

### C.6 Mergers, demergers, renames, delistings — membership side

- **Renames:** era-correct labels, e.g. SESAGOA → SSLT (2013-10-04) → VEDL (2015-05-07),
  CROMPGREAV → CGPOWER (2017-03-08), TATAMOTORS → TMPV (2025-10-24). **Every member slot's label
  exists in the price store on that date (§D).**
- **Mergers:** HDFC's interval closes 2023-07-13, and its last trade is 2023-07-12.
- **Share classes:** `TATAMTRDVR` (ISIN `IN9155A01020`) is a genuine member 2016-04-01 → 2017-09-29.
  `universe_eligibility` classes it `non_equity_isin`, so any filter on that table would silently
  drop a real constituent.
- **Cross-table inconsistency (not adjudicated).** By definition N100 ⊂ N200. At month-ends, N100
  members absent from the PR-derived `n200_membership` are:

  | Year | Slots |
  |---|---|
  | 2011 | 412 (400 fall before N200's 2011-07-19 start) |
  | 2012 | 24 |
  | 2013 | 15 |
  | 2014 | 24 |
  | 2015 | 41 |
  | 2016 | 21 |
  | 2017 | 4 |
  | 2018–2022 | **0** |
  | 2023 | 1 (JIOFIN transient) |
  | 2025 | 2 (ITCHOTELS transient) |
  | 2026 | 0 |

  This matches the N200 build's own disclosure that 2011 → mid-2018 has no independent
  reconciliation. N100 does not consume `n200_membership`, and it is separately MCWB-gated
  monthly. **Which table is wrong for 2012–2017 is not resolved here.**

### C.7 Build-record defect (carried from the 2026-09-13 review, still open)

`n100_audit` persists count violations, terminals, overrides and the pre-listing screen (**0**).
It does **not** persist G1 breaks, **G3 (the load-bearing MCWB gate)** or G5. A reader of the
store cannot see that G3 ran.

---

## D. EOD panel coverage (§2 and §5)

**Store:** `equity_bhavcopy` — 7,158,443 rows, 2010-01-04 → 2026-09-11, 4,145 distinct dates;
series EQ 6,596,242 / BE 562,201. Source format by era (`ingest_meta`): `legacy` 2010–2019,
`secfull` 2020 →, one `udiff` day in 2026.

**Join:** `n100_membership` on (symbol, trade_date), against every `trading_calendar` session in
2011-03-25 → 2026-09-11.

### D.1 Calendar artifacts (two dates that are not sessions)

| Date | Calendar row | Store | Member slots |
|---|---|---|---:|
| 2012-11-11 (Sunday) | `equity_store`, 14 symbols | 14 gold-ETF rows only | 100 |
| 2016-04-19 | `source = 'unresolved'`, no count | **No rows.** Raw archive holds `legacy_20160419.404` | 101 |

Both are calendar defects, not missing prices. CLAUDE.md already lists 2012-11-11 as an operator
pre-freeze calendar item. They are excluded from the counts below and must be declared.

### D.2 Observation table (real sessions)

| Year | Sessions | PIT N100 slots | EOD price observations | Coverage | BE-series only | Distinct members |
|---|---:|---:|---:|---:|---:|---:|
| 2011 (from 03-25) | 190 | 19,000 | 19,000 | 100.00% | 0 | 106 |
| 2012 | 251 | 25,100 | 25,100 | 100.00% | 0 | 107 |
| 2013 | 250 | 25,000 | 25,000 | 100.00% | 0 | 108 |
| 2014 | 244 | 24,400 | 24,400 | 100.00% | 0 | 105 |
| 2015 | 248 | 24,800 | 24,800 | 100.00% | 0 | 110 |
| 2016 | 247 | 24,886 | 24,886 | 100.00% | 0 | 117 |
| 2017 | 248 | 24,985 | 24,985 | 100.00% | 0 | 107 |
| 2018 | 246 | 24,600 | 24,600 | 100.00% | 0 | 110 |
| 2019 | 245 | 24,500 | 24,500 | 100.00% | 0 | 109 |
| 2020 | 252 | 25,175 | 25,174 | 99.996% | 52 | 112 |
| 2021 | 248 | 24,800 | 24,800 | 100.00% | 204 | 111 |
| 2022 | 248 | 24,800 | 24,800 | 100.00% | 29 | 115 |
| 2023 | 246 | 24,609 | 24,609 | 100.00% | 9 | 113 |
| 2024 | 249 | 24,900 | 24,900 | 100.00% | 0 | 111 |
| 2025 | 249 | 24,941 | 24,941 | 100.00% | 10 | 113 |
| 2026 (to 09-11) | 173 | 17,300 | 17,300 | 100.00% | 0 | 107 |
| **Total** | **3,834** | **383,796** | **383,795** | **99.9997%** | **304** | **216** |

### D.3 Distribution and losses

| Measure | Value |
|---|---|
| Constituents priced per session | median **100** · min **99** · max **101** |
| Sessions below 99% / 95% / 90% coverage | **0 / 0 / 0** (the lowest real session is 99/100 = 99.0%) |
| Constituent-days lost to missing data | **1**: DMART 2020-04-13. **NSE's own source file for that date has no BE series at all** (EQ 1,515, SM 45, GB 33…), and DMART traded in BE 2020-03-04 → 05-26. Source-side, not an ingest loss |
| Lost to "not yet listed" | **0** (G6 pre-listing screen also 0) |
| Lost to delisting | **0**: every exiting member's interval closes on or before its last trade |
| Lost to suspension | **0** beyond the DMART case |
| Lost to entity / label issues | **0**: all 383,795 present slots resolve to exactly one entity interval; no member slot lacks a row under its label while its entity trades under another |
| Lost to calendar artifacts | 201 slots on 2 non-sessions (§D.1) |
| Duplicate EQ+BE rows for a member-day | **0** |

**Store-wide zero-BE sessions** (2010-05-16, 2012-11-11, 2020-04-13, 2020-09-28, 2022-03-07): only
2020-04-13 touches a member.

### D.4 Invalid price rows (predicates on member rows only, counted)

| Predicate | Rows |
|---|---:|
| `close` null or ≤ 0 | 0 |
| any of `open/high/low` null or ≤ 0 | 0 |
| `high < low` | 0 |
| `close` outside `[low, high]` | 0 |
| `open` outside `[low, high]` | 0 |
| `volume` null or 0 | 0 |
| `prev_close` null or ≤ 0 | 0 |

### D.5 Survivorship

The price layer is not survivorship-filtered. Names that left the market remain in the store with
their full traded history: RANBAXY to 2015-04-01, CAIRN to 2017-04-25, ABIRLANUVO to 2017-07-04,
HDFC to 2023-07-12, and others. Membership is external to the price store. Unlike the vendor 1m
archive (56/100 members present in 2015), nothing here was selected by present-day existence.

---

## E. Corporate-action audit (§3)

### E.1 What the tables hold

| Table | Rows | Content |
|---|---:|---|
| `adjustment_factors` | 1,218 | BONUS 606 · SPLIT 601 · SPECIAL_DIVIDEND 11. Sourced from NSE CF-CA annual CSVs. *(The map stamped 1,194 on 2026-09-12 — a moving count.)* |
| `corporate_actions` | 11,976 | `action_type` is only DIVIDEND 10,771 · BONUS 606 · SPLIT 599. **Spin-offs, amalgamations, schemes, rights issues and buybacks are stored as `DIVIDEND`, distinguishable only by `purpose_raw`** |
| `ca_evidence_exceptions` / `ca_scope_exclusions` | 16 / 13 | **0 rows on any N100 member** |
| `ca_parse_rejects` | 22 | 7 on members, all non-equity "bonus" debentures/preference shares (NTPC 2015, DRREDDY 2011, BRITANNIA ×3, ZEEL 2014, TVSMOTOR 2025). Correctly not price factors |

### E.2 Split / bonus — available, complete for members, entity-correct

- **112 bonus/split events fall inside an N100 membership interval** (75 bonus on 50 symbols,
  37 split on 34). **112/112 have a factor**, and no member factor lacks a CA row.
- Factors attach to the entity **as of the ex-date** through `symbol_entity_intervals`, so a
  factor keyed to a post-rename symbol reaches the same company's pre-rename prints, and a recycled
  ticker cannot borrow another company's factor.
- **Completeness beyond the CA table:** contract-suite Arm A flags any intra-symbol move sitting on a
  canonical CA ratio without a documented factor, including bonus-shaped ~−33% moves (large-genuine
  threshold 0.30). Per the 2026-09-13 review §7, the whole-panel Arm A residue **contains no N100 or
  N200 member**. The contract suite was **not re-run** for this audit.

### E.3 Events the adjusted series does **not** treat

Inside N100 membership, 2011-03-25 → 2026-09-11, from the store:

| Class | Events | Adjusted? |
|---|---|---|
| **Spin-off / scheme of arrangement** | ITC 2025-01-06 · SIEMENS 2025-04-07 · TVSMOTOR 2025-08-25 · TATAMOTORS (row keyed `TMPV`) 2025-10-14 · HINDUNILVR 2025-12-05 · VEDL 2026-04-30 | **No factor** |
| **Spin-off absent from the store entirely** | RELIANCE → JIOFIN (2023; JIOFIN lists 2023-08-21). **No `corporate_actions` row exists** | **No factor** |
| **Rights issues** | BHARTIARTL 2021-09-27 · GRASIM 2024-01-10 · TATACONSUM 2024-07-26 · ADANIENT 2025-11-17 | **No factor** |
| **Special dividends** | LT 2023-08-02 · COLPAL 2024-05-22 · HINDUNILVR 2024-11-06 · BAJFINANCE 2025-05-09 · CIPLA 2025-06-27 · HDFCBANK 2025-07-25 · PIDILITIND 2025-08-13 · TCS 2026-01-16 · BAJAJHLDNG 2026-06-30 · NESTLEIND 2026-07-10 | **No factor**, although the view *does* adjust the 11 store-wide special dividends that carry one. **Treatment is inconsistent across names** |
| Ordinary dividends | All | **Never adjusted.** The adjusted series is a price-return series, not total return |
| Buybacks | 8 (LT, ZYDUSLIFE ×2, BAJAJ-AUTO ×2, INFY, WIPRO…) | Conventionally no price adjustment |

PSB-1 Arm A records SIEMENS 2025-04-07 as a "CA-shaped orphan — demerger" disposition, so the
certified adjusted series **knowingly** carries that break. Non-ratio-shaped events (most
demergers, rights issues) are outside Arm A's detection by design.

### E.4 The CA table cannot prove absence before ~2022

`corporate_actions` rows attached to member entities inside membership, by year:

| Year | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All rows | 13 | 5 | 8 | 10 | 19 | 14 | 22 | 14 | 15 | 7 | 15 | 60 | 62 | 118 | 172 |
| Dividend-purpose | 5 | 5 | 3 | 5 | 9 | 4 | 5 | 5 | 7 | 6 | 13 | 47 | 56 | 103 | 148 |

Roughly a hundred large companies produce 3–13 dividend records a year before 2021. The table is
clearly **not** a complete record of dividends or non-split events in the early years. **The
absence of a spin-off, rights or special-dividend row before ~2022 is therefore not evidence that no
such event occurred.** The 2023 RELIANCE/JIOFIN demerger is missing even in the dense era.
Bonus/split completeness rests on the separate NSE CF-CA factor files plus Arm A (§E.2), not on
this table.

### E.5 Is the adjustment causal?

**No — not for price levels.** `equity_bhavcopy_adjusted` is a backward adjustment: row *t* is
scaled by the cumulative product of factors whose `ex_date > t`
(`ingest_corporate_actions.py` `build_adjusted_view`, `cum` CTE). Consequences:

- **Level look-ahead.** An adjusted price on date *t* depends on bonuses and splits that happened
  after *t*. 50 member symbols had a bonus and 34 a split inside membership, so their pre-event
  adjusted levels are prices that never traded.
- **Ratios are safe between event-free dates.** Where no factor falls between two dates, the
  adjusted ratio equals the raw ratio, and across a factored event the ratio is corrected.
- **History is not stationary.** Every new factor ingested rescales all earlier rows of that
  entity. The view as queried today differs from the view as queried a month ago, so a pre-registered
  experiment must pin the factor-table snapshot, by hash.
- **Other stores differ.** The 1m store is back-adjusted by the vendor to the fetch-date basis
  (DATA_STORE_MAP §12), and `equity_bhavcopy` is as-traded. These are three bases that must never
  be joined silently.

### E.6 Do dividends matter?

They matter to the extent the future hypothesis treats price **level** or **path** as meaningful.
Ordinary dividends lower every ex-date price in both raw and adjusted series. For large-cap Indian
names that is typically a small fraction of price, recurring. Special dividends and spin-offs can be
large single-day level breaks. **Whether the hypothesis concerns traded price (dividends are part
of the path) or economic value (dividends must be added back) is a research-definition question,
left open here.**

---

## F. Entity / ticker mapping audit

| Check (N100 ever-members: 216 symbols → 198 entities) | Result |
|---|---|
| Member slots resolving to exactly one entity interval | **383,795 / 383,795** |
| Member symbols with no entity interval | **0** |
| Member symbols mapping to >1 entity (recycled tickers) | **0** (the repo's one recycled ticker, DTIL, never appears in N100) |
| Entities carrying >1 symbol over time (renames) | 25 |
| `symbol_changes` rows touching member symbols | 54 |
| Member symbols with >1 ISIN in `symbol_isin` / with none | 0 / 0 |
| Label mismatch (member label absent, same entity trading under another label that day) | **0** |
| Whole-panel A5 residue items (Arm A / quarantined) that are ever N100 or N200 members | **0** (2026-09-13 review §7) |

**One mapping hazard, not a defect.** The Tata Motors demerger CA row sits under `TMPV`
(ex-date 2025-10-14), while the store label changed from TATAMOTORS to TMPV only on 2025-10-24.
Entity continuity is asserted (both labels → entity `TATAMOTORS`); TMCV is a new entity from
2025-11-12, and a member from 2026-03-30. An experiment must carry the level break at 2025-10-14
inside the TATAMOTORS label.

---

## G. Price field choice (§6) — implications only, no choice made

| Property the hypothesis may rely on | Raw close (`equity_bhavcopy`, as-traded) | Backward-adjusted close (`equity_bhavcopy_adjusted`) |
|---|---|---|
| **Historical price level** — the number printed on the day, round-number and absolute-level geometry | **Preserved exactly.** The level is what market participants saw | **Not preserved.** Rescaled by later bonuses/splits; for every member with a later bonus (50) or split (34), pre-event levels never traded. **Contains look-ahead** |
| **Price movement** — change between two states | Correct between event-free dates; **wrong by the CA ratio across the 112 bonus/split ex-dates** | Correct across bonus/split; still wrong across spin-offs, rights, special dividends (§E.3) |
| **Time-distance between price states** | Unaffected; the session calendar is identical | Unaffected |
| **Causality** | Causal as a series; discontinuities are known on their ex-dates | Level at *t* uses events after *t*; ratios over event-free spans are unaffected |
| **Stability of history** | Fixed once ingested | Rewrites earlier rows whenever a factor is added; must be hash-pinned |

**Unresolved design options, for the pre-registration and not this audit:**
- raw levels with event-segmented paths;
- as-of-*t* adjustment (only factors with `ex_date ≤ t`, which restores causality for levels and
  movements at the cost of a time-varying basis);
- backward-adjusted series restricted to scale-free quantities.

**Material rule regardless of choice:** any construct that reads absolute price levels from the
backward-adjusted view has look-ahead by construction.

---

## H. Historical depth (§7) — candidate windows, no partition implied

| Window | Start | End | Years | Sessions | Stock-day obs | Distinct members | Known caveats |
|---|---|---|---:|---:|---:|---:|---|
| **A. Maximum defensible** | 2011-03-25 | 2026-09-11 | 15.47 | 3,834 | 383,795 | 216 | All of B and C below; two calendar artifacts to declare |
| **B. Conservative, higher-assurance** | 2018-06-29 | 2026-09-11 | 8.20 | 2,033 | 203,324 | 174 | Starts where the PR-derived N200 first reconciles independently and N100 ⊂ N200 holds (except two transients); after the 2018-05 MCWB gap and the DVR 101-member era. Still carries R7/R8 unpinned dates, BE-series names (ADANITRANS, ADANIGREEN, DMART), the one source-side miss, and **all** unadjusted 2023–2026 spin-offs and special dividends |
| **C. Early, lower-assurance (usable with disclosure)** | 2011-03-25 | 2018-06-28 | 7.26 | 1,801 | 180,471 | 155 | 5 of 8 override groups (R1–R5, including R5's inferred date); no independent N200 cross-check and 141 month-end N100⊄N200 slots after N200's 2011-07-19 launch; MCWB missing 2018-05; 49 PRs without explicit "close of" wording; `legacy` bhavcopy format; CA table too sparse to enumerate non-split events |
| **Materially compromised** | 2010-01-04 | 2011-03-24 | 1.22 | ~303 | — | — | **No daily PIT membership** (MCWB monthly only). Usable only as price warm-up history, never as a membership-defined observation window without a separate build |

Other boundaries worth knowing (descriptions only): `secfull` format era from 2020-01-01
(1,665 sessions, 166,524 obs); 2011-03-25 → 2022-12-30 (2,917 sessions, 292,045 obs);
2023-01-02 → 2026-09-11 (917 sessions, 91,750 obs, the span the 1m route also covers).

---

## I. EOD vs 1m (§9)

| | **EOD N100** (`equity_bhavcopy` × `n100_membership`) | **1m N100** (canonical 1m store × `n100_membership`) |
|---|---|---|
| Historical depth | 2011-03-25 → 2026-09-11 · **15.5 y · 3,834 sessions** | 2023-01-02 → 2026-09-11 · **3.7 y · 917 files** (913 OK, 4 GAP). Vendor 1m 2015–2025 is uncertified and survivorship-shaped (56/100 members in 2015) |
| Cross-sectional coverage | 383,795 / 383,796 member-days; 1 source-side miss | 0 absent cells after the 2026-09-13 backfill, except HDFC on 130 sessions (accepted 99/100) |
| PIT quality | Same table. Carries R1–R8 and the lower-assurance 2011–2018 span | Same table, restricted to 2023+ (only the R8 inferences apply) |
| Provenance | NSE official bhavcopy (exchange close, as-traded); raw archive retained with `.404` markers; whole panel certified under PSB-1 (four-arm contract), then HALTed on the 2026-09-12 PTMS re-run on residue outside N100/N200 scope. **No PTMS scoped certificate for EOD** | Upstox historical API, re-fetched; basis unflagged in schema; **PTMS scoped certificate issued 2026-09-13** (C1–C4) |
| Corporate-action handling | As-traded plus an explicit, auditable, entity-time-aware factor table (bonus/split complete for members). Spin-offs, rights, special and ordinary dividends unadjusted. Backward view has level look-ahead | Vendor back-adjusted to fetch date, verified 32/32 on bonus/split. Treatment of demergers/special dividends by the vendor is unknown. Same level look-ahead, with no factor table to audit |
| Observation count | ~**384k** stock-days (OHLC, 1 print/day) | ~**92k** stock-days (~34M bars) |
| Main limitations | No intraday path; non-ratio CA events unadjusted; CA table incomplete pre-2022; four ±1-month boundaries matter at daily cadence; no scoped certificate; historical windows already read by several lineages (§10) | 3.7 years ≈ one macro regime; CAS synthetic bars from 2026-08-03; bar-labelling by rule; window already read at signal level (E-1, E-2, E-3) |
| Scientific suitability | A materially deeper substrate for **any price-time construct expressible at daily (or coarser) resolution** across several market regimes. **Cannot** carry intraday time structure | The only substrate for intraday time structure; too short for multi-regime evidence |

**Honest reading.** For a question whose time axis is sessions, weeks or months, EOD gives ~4.2× the
calendar and ~4.2× the stock-days of 1m, on an equally clean PIT join. For a question whose time axis
is minutes within the session, EOD is not a substitute at all. **The original N100 "test" was never
defined** (`PTMS_N100_INTENDED_EXPERIMENT_AUDIT_2026-09-14.md`), so which axis it needs is itself
unresolved.

---

## J. Blockers (§8)

| Item | Status | Detail / required treatment |
|---|---|---|
| N100 reconstruction (vs N200) | **GREEN** | Genuine N100, not derived from N200. **RED if `universe_membership` is ever substituted** (median 70/100 overlap) |
| PIT membership — monthly cadence | **GREEN** | 368 month-legs, 0 MCWB mismatches |
| PIT membership — daily cadence | **AMBER** | Four ±1-month boundaries (R5, R7 ×2, R8 ×2) need a declared disposition |
| PIT membership record | **AMBER** | G1/G3/G5 not persisted in `n100_audit`; 49 PRs lack explicit effective-date wording |
| Entity mapping | **GREEN** | 100% single-entity resolution; 0 label mismatches |
| Ticker changes | **GREEN** | Era-correct labels; 54 member-touching renames handled |
| Delisted companies | **GREEN** | Present in store; 0 post-delisting slots |
| Missing EOD observations | **GREEN** | 1 source-side miss in 383,796 |
| Calendar artifacts | **AMBER** | 2012-11-11 and 2016-04-19 must be dropped or declared (operator calendar item) |
| BE series / DVR share class | **AMBER** | 304 BE-only member-days; TATAMTRDVR classed `non_equity_isin` elsewhere. Inclusion rule must be declared |
| Survivorship bias | **GREEN** | External membership; delisted names retained; 0 pre-listing |
| Early history 2011-03-25 → 2018-06-28 | **AMBER** | Lower-assurance membership (C.6); sparse CA records |
| Early history before 2011-03-25 | **RED** for that segment only | No daily PIT membership; does not affect windows A/B/C |
| Corporate actions — bonus / split | **GREEN** | 112/112 factored; Arm A residue outside N100 |
| Corporate actions — spin-offs, schemes, rights, special dividends | **AMBER** | Unadjusted; the store cannot enumerate them pre-2022, and one 2023 demerger is absent. **Needs external enumeration and a declared treatment.** RED if left untreated in a level- or path-based construct |
| Dividends (ordinary) | **AMBER** | Price-return only; the price-vs-value basis must be declared |
| Price adjustment / look-ahead | **AMBER** | Backward-adjusted **levels** contain look-ahead; the view rewrites history on each factor ingest. **RED if adjusted levels feed a level-based rule** |
| Look-ahead — membership | **GREEN** | Effective-date convention verified (179 PRs); composition announced 2–51 days ahead |
| Substrate certification | **AMBER** | No scoped PTMS certificate for the EOD surface; whole-panel contract suite last HALTed on residue outside N100 |
| Confirmatory status of historical windows | **UNRESOLVED — governance, not data** | §10. May leave no confirmatory history at all; does not change the substrate verdict |

---

## K. Research-budget / exposure statement (§10)

**Inspected:** everything in §B. Concretely:
- schema, counts and dates;
- membership intervals and audit rows;
- the MCWB manifest;
- effective-date phrasing in PR text;
- CA / factor / entity / ISIN / symbol-change metadata;
- one raw bhavcopy's series counts and one symbol's presence;
- the adjusted view's SQL;
- validity predicates on member price rows, 2011-03-25 → 2026-09-11, returned only as counts.

**Outcome-linked information read: none.**
- No return, forward return, cross-date price ratio, rank, IC, spread, signal, label or P&L was
  computed.
- No TRAIN / HOLDOUT / SEALED artifact or snapshot of any lineage was opened.

**Incidental disclosure:**
- The PSB-1 certification report's disposition table (consulted for which CA events are
  dispositioned) prints substrate-QA return magnitudes for CA-shaped moves. Those figures were not
  used and are not reproduced here.
- The exposure register rows read for this section print headline statistics of past studies.

**Exposure consumed by this audit:** none. Level **meta**, plus ingest-QA validity predicates, which
are neither a retained feature nor linked to an outcome. Under register §1 neither level spends
budget. **Process deviation:** register §8 asks for a row *before* a read. None was appended,
because register writes are the operator's. Proposed row, for the operator to append if they agree:

> | M-1 | Equity EOD panel × `isd/n100_membership` | 2011-03-25 → 2026-09-11 | **meta** (+ validity predicates, counts only) | — (substrate feasibility; no hypothesis) | `PTMS_N100_EOD_FEASIBILITY_AUDIT_2026-09-14.md` |

**Existing exposure that a future N100 EOD experiment inherits** (recorded, not adjudicated):

| Row | Surface / window | Level |
|---|---|---|
| Q-1, Q-2 | Equity EOD, dev ≤ 2022-12-30 (PSB-1/PSB-2 on a turnover-200 universe containing ~94% of N100 members) | signal |
| Q-3 | Equity EOD, 2011–2018 (C2 Phase 0.5) | signal |
| Q-5 | Equity EOD adjusted, dev ≤ 2022-12-30 (CSMP momentum artifact) | signal |
| Q-4 | Equity EOD, 2012–2023 (N200 regime HMM) | feature |
| Q-6 | Equity EOD adjusted, 2023-01 → 2026-06 — **UNREAD for CSMP only** (lineage-local, register §1) | unread |
| §5b clusters | `scripts/signal_engine/` (19 equity-EOD readers → rows F-1…F-5, fences through SEALED 2023 →) and `scripts/mrlc_test/` (→ E-3, 2023 →). **The register does not state the equity-EOD windows of these reads separately** | signal |
| D-2 | CB-N50 on Nifty-50 constituents, 2016–2022 (surface recorded as the 1d index store) | signal |

Under GR-1.2 and GR-1.3, and pending the open file-shaped vs observation-shaped ruling, **it is
possible that no historical EOD window for these names can be confirmatory for a new hypothesis**;
any confirmatory evidence would then have to come from forward sessions. This audit does not decide
that. It is a governance constraint on **use** of the substrate, not a defect **in** it.

---

## L. Final verdict (§11)

### **B. FEASIBLE WITH CONDITIONS**

The historical data can support a future, properly governed N100 stock-level price-time experiment
at daily or coarser resolution, **once the conditions below are satisfied.** Nothing found makes it
dishonest in principle. Several items would make it dishonest if left implicit.

### Conditions that must be satisfied before hypothesis definition

1. **Exposure ruling (operator).**
   - Settle file-shaped vs observation-shaped exposure.
   - State which of windows A/B/C, if any, may serve as non-confirmatory development evidence, and
     which could ever be confirmatory under GR-1.3.
   - Record the equity-EOD windows of the §5b `signal_engine` / `mrlc_test` readers.
   - Append this audit's meta row.
   This comes first, because it decides whether the history is evidence or only a training ground.
2. **Scoped EOD substrate certification (operator decision)** for N100 × `equity_bhavcopy`
   (± adjusted view) over the chosen window. It should include:
   - a scoped contract-suite run;
   - persisting G1/G3/G5 into `n100_audit`;
   - declaring the two calendar artifacts (2012-11-11, 2016-04-19);
   - declaring the source-side DMART 2020-04-13 miss.
3. **Non-factor corporate-action enumeration from an authoritative external source** for every
   member inside membership: spin-offs, schemes, rights issues, special dividends.
   `corporate_actions` cannot be relied on before ~2022, and it omits the 2023 RELIANCE/JIOFIN
   demerger. This is data work requiring operator authorization; this audit builds nothing.
4. **Membership-precision disposition** for the four ±1-month boundaries, required only if the
   eventual cadence is finer than monthly.
5. **Declared inclusion rules** for BE-series member-days (304) and for the TATAMTRDVR share class.

### Choices that belong to pre-registration, before any outcome read

- **Price basis:** raw, as-of-*t* adjusted, or backward-adjusted restricted to scale-free
  quantities. If any adjusted series is used, pin the factor-table snapshot by hash.
- **Dividend basis:** price path or value.

### Dates

| | |
|---|---|
| **Earliest defensible date** | **2011-03-25** (daily PIT N100 membership begins; EOD prices from 2010-01-04 available as warm-up only) |
| **Latest available date** | **2026-09-11** (membership anchor and last EOD session; the Sep-30-2026 review is parsed and excluded) |
| **Recommended historical window (substrate)** | **A: 2011-03-25 → 2026-09-11**, carrying 2011-03-25 → 2018-06-28 as a disclosed lower-assurance segment, with **B (2018-06-29 → 2026-09-11)** as the higher-assurance subset. How any of it may be used is condition 1, not a substrate property |

### Unresolved scientific questions — deliberately NOT decided here

- What the price-time / Gann-type construct is, and whether it is Gann-specific at all.
- Its time resolution (daily, weekly, monthly, intraday), which decides whether EOD can host it and
  whether the ±1-month boundaries matter.
- Price basis (raw vs as-of-*t* vs backward-adjusted) and dividend basis (price vs value).
- The unit of observation and what makes observations independent (stock-day, stock-event,
  cross-sectional formation).
- Family placement (Family F per the catalogue) and multiplicity slot, RFA metric and bands.
- Any TRAIN / HOLDOUT / confirmatory partition, and whether the pre-2018 segment is used.
- Treatment of spin-offs, rights and special dividends once enumerated.
- Inclusion of BE-series days and non-ordinary share classes.

---

STOP. No outcome reads. No RFA. No hypothesis. No parameters. No freeze. No infrastructure.
