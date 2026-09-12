# India VIX 1m — Ingest Verification and Grid-Seam Finding

**Date:** 2026-09-12 · **Branch:** `research/ptms-price-time-market-structure`
**Trigger:** operator statement of provenance for three VIX assets, including an Upstox 1m
backfill already written into the canonical store.
**Access level:** meta + substrate verification. No signal, label or fitted parameter was
computed. Cross-store equality checks are certification, the same class as the G1-B1 gate.

**Headline:** the ingest landed and is value-verified against an independent source at
99.98% exact. It also exposed a **dual intraday time grid** in the canonical store that
predates this work and is not recorded anywhere — plus two bounded defects.

---

## 1. Provenance, now on record

| Asset | Provenance (operator, 2026-09-12) | Status |
|---|---|---|
| `data/market_data/INDIA VIX_minute.csv` | External vendor download | Gitignored, uncertified. Assessed in `VIX_1M_VENDOR_CSV_ASSESSMENT_2026-09-12.md` |
| `data/market_data/India VIX Historical Data 101.csv` | External vendor download, VIX EOD | Gitignored, uncertified. §5 below |
| Canonical VIX 1m rows | **Upstox**, via `scripts/fetch_upstox_historical.py` — yearly runs + split-retries, `is_synthetic = FALSE` upserts | **Written into `data/market_data/nse/candles/1m/{date}.duckdb`.** Verified below |

## 2. The Upstox ingest — measured, and it supersedes a P1 correction

| Measure | Value |
|---|---|
| Files carrying VIX 1m | **1,165** of 3,613 |
| Rows | **435,244** (operator stated ~434k) |
| Span | **2022-01-03 → 2026-09-11** |
| Sessions/yr | 2022: 248 · 2023: 246 · 2024: 249 · 2025: 249 · 2026: 173 |
| Exactly 375 bars | 1,065 sessions |

**This supersedes the P1 §9 correction committed earlier today**, which recorded canonical
VIX 1m as "2024-11-29 → 2026-09-11, 117 of 445 sessions (26.3%)." That measurement was taken
**before** this ingest landed and is now wrong. Corrected in `DATA_STORE_MAP.md`. The
underlying P1 lesson stands unchanged: the map's *original* claim ("1m 2023-01-02→") was
wrong in both directions and had to be measured, not inherited.

**`is_synthetic = FALSE` on these rows is correct by rule.** Index symbols are not CAS
Category I, and the standing rule is that the `volume = 0` synthetic predicate is
**`NSE_EQ`-only** — indices carry volume 0 on every bar, so applying it to `NSE_INDEX` would
mark the index's own value as fabricated. Era must be resolved by rule, never by detection.
Verified: **zero** `NSE_INDEX` rows are marked synthetic in any post-CAS file.

## 3. Independent cross-verification — strong

Vendor CSV vs the canonical store over their full overlap:

| Measure | Value |
|---|---|
| Sessions compared | **789** |
| Bars compared | **294,131** |
| Fraction exactly equal | **0.99980** |
| Mean abs difference | **0.000002** |
| Max abs difference | **0.0500** (none exceed it) |

Two independently sourced feeds — an external vendor and Upstox — agree to 99.98% exact
across three years. That is the strongest provenance evidence this repo can produce without
a vendor attestation, and it is the same test that closed G1-B1.

---

## 4. Findings

### V1 — the canonical 1m store contains **two intraday time grids** (serious, pre-existing)

| Era | First bar | Last bar | Bars |
|---|---|---|---|
| 2012-01-02 → 2022-12-30 (index pair only) | **09:16** | **15:30** | 375 |
| 2023-01-02 → present (all symbols) | **09:15** | **15:29** | 375 |

The flip is at **2023-01-02**, with one exception: **2023-01-31 reverts to 09:16 → 15:30** —
the last date covered by the reference-CSV bundle (`ingest_reference_1m.py` docstring:
"CSVs have 1-minute OHLC from 2012-01-02 to 2023-01-31").

Note the ingest script's own constant reads `EXPECTED_BARS = 375  # 9:15 to 15:29 inclusive`
while the rows it wrote start at 09:16 — the vendor bundle's labelling was passed through
unchanged, against the script's stated expectation.

**Immediate consequence — a within-file misalignment in 2022.** The Upstox VIX backfill
wrote VIX on the **modern** grid, so in every 2022 file VIX sits on 09:15→15:29 while
`Nifty 50` and `Nifty Bank` sit on 09:16→15:30. Verified on 2022-04-20:

```
Nifty 50    n=375  09:16 -> 15:30
Nifty Bank  n=375  09:16 -> 15:30
VIX         n=378  09:15 -> 15:32
```

**Joining VIX to the index pair on `timestamp` for any 2022 session silently offsets them by
one minute.** For 2023 onward the grids agree and the join is clean.

**What is NOT established.** Whether the pre-2023 slice is bar-*end*-labelled while the modern
slice is bar-*open*-labelled. The natural test — does the last 1m bar's close equal the daily
close — **fails to discriminate**: it matches in neither era (2020-01-02: 1m 12282.35 vs 1d
12282.20; 2023-06-15: 18682.15 vs 18688.10), because the 1d index close comes from a different
source and an index close is not the last traded print. So the semantics are **unresolved**,
and `DATA_STORE_MAP.md`'s single claim ("timestamp = bar open, verified 2020-01-02:
09:16→15:30") conflates two conventions. Resolving this is a **P2 certification item**.

**Why this matters beyond VIX.** The seam falls exactly on the TRAIN/HOLDOUT ↔ SEALED
boundary of both index-1m lineages: A (TRAIN 2012–2018 / HOLDOUT 2019–2022 / SEALED 2023→)
and intraday analog path (identical fences). If the two eras are labelled differently, those
constructs' discovery windows and their confirmatory window sit on **different clocks**. This
is recorded for the operator; it is **not** an adjudication of either lineage, and no window
was spent establishing it.

### V2 — VIX bars past session end (bounded, 2022 only)

90 sessions carry 376–378 bars running to **15:31 / 15:32**: 28 × 376, 41 × 377, 21 × 378,
first at 2022-03-24. The index pair in the same files stops at 15:30. Upstox returned
trailing bars past the close. Enumerable; must be trimmed or the sessions quarantined.

Also present, and **correct**: 4 sessions of 60 bars at 18:15–19:14 (Diwali **Muhurat**), and
2 sessions of 105 bars ending 12:29 (2024-03-02, 2024-05-18 — NSE Saturday special sessions
with two windows). Do not filter these as anomalies. Four sessions have 374 bars.

### V3 — 10 post-CAS sessions carry **zero** equity synthetic marks (pre-existing, unrelated to VIX)

`2026-08-31, 09-01, 09-02, 09-03, 09-04, 09-07, 09-08, 09-09, 09-10, 09-11` — every post-CAS
session from 08-31 onward — have no `NSE_EQ` rows marked `is_synthetic`. The preceding 20
post-CAS sessions are marked correctly.

This is the **known** defect, now scoped: `mark_file()` returns 0 when a session has no
Category I list, so an unmarked session looks marked, and `data/cas/cas_category.duckdb` ends
**2026-08-28**. Nothing here was caused by the VIX ingest (VIX is an index symbol). Reported,
not repaired — it is a live substrate item and touching it is outside P0/P1 scope.

---

## 5. The VIX EOD CSV

`data/market_data/India VIX Historical Data 101.csv` — 3,822 data rows, **2010-01-04 →
2025-06-05**, schema `Date,Price,Open,High,Low,Vol.,Change %`, dates **DD-MM-YYYY**, UTF-8
**BOM**, `Vol.` empty throughout (correct for an index), `Price` = close. The
`Change %` column is a vendor-computed derived field.

It **extends VIX daily history back to 2010-01-04**, five years earlier than the canonical
1d store's 2015 start — and it stops 2025-06-05, so it does not replace the canonical series,
it prefixes it. Uncertified; the 2015 → 2025-06 overlap against the canonical 1d store is an
available equality check and has **not** been run. Not assessed further here.

---

## 6. Recommendations (none authorized here)

1. **Record V1 in the store map and treat it as a P2 gate**, not a footnote. Any construct
   joining index symbols across the 2023 boundary needs an explicit era rule, the way CAS has one.
2. **Resolve the labelling semantics** by a source-level check — the vendor bundle's own
   documentation, or an intraday cross-source comparison on a pre-2023 date against a third
   feed. The daily-close test is proven useless for this.
3. **Trim or quarantine V2's 90 sessions** before any use of 2022 VIX.
4. **Run the EOD CSV overlap check** (2015 → 2025-06) before relying on the 2010–2015 prefix.
5. **Escalate V3** to whoever owns `cas_category` — it blocks nothing in PTMS but is silently
   corrupting post-2026-08-28 tradeability flags for every F&O equity name.
6. The exposure level of all three assets remains **NONE**. Nothing has read them for research.
