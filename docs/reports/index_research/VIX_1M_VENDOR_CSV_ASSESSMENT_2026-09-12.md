# `INDIA VIX_minute.csv` — Assessment

**Date:** 2026-09-12 · **Branch:** `research/ptms-price-time-market-structure`
**Asset:** `data/market_data/INDIA VIX_minute.csv` — 42,791,141 bytes, mtime 2026-09-12 14:33,
**gitignored** (`.gitignore:23 /data/`), untracked, provenance not stated in-repo.
**Access level:** meta + substrate verification. No signal, label, or fitted parameter was
computed; the cross-store comparison is an equality check of the same series from two
sources, the same class as the G1-B1 index gate.

**Verdict: a high-value, genuinely unread surface — and not yet usable. Certify before use;
do not stitch into the canonical store.**

---

## 1. What it is

| Property | Value |
|---|---|
| Schema | `date,open,high,low,close,volume` |
| Rows | **938,695** |
| Span | **2015-01-09 09:15 → 2025-03-05 11:30** |
| Sessions | **2,515** |
| Bars/session | 375 on **2,471** sessions; median 375, min 53, max 377 |
| Volume | uniformly **0** — correct for an index |
| Duplicate timestamps | **0** |
| Null closes | **0** |
| Close range | 9.69 → 86.43 (plausible for India VIX incl. the COVID spike) |

## 2. Why it matters

The canonical 1m store holds India VIX on **117 of 3,612 files** — 2024-11-29 → 2026-09-11,
26.3% of sessions in that span (the P1 correction committed earlier today). This CSV covers
**2,515 of the 2,518 calendar sessions** between 2015-01-09 and 2025-03-05 — a **99.88%
complete decade** of 1m India VIX that the canonical store does not have.

Only three calendar sessions are absent: **2015-01-16, 2016-04-19, 2019-07-02.** Zero CSV
dates fall outside the trading calendar.

Given the PTMS budget picture, an *unread* surface is the scarce thing. Nothing in the
exposure register reads this file: no script references it, and it appeared after every
gated lineage closed. Its exposure level is **none**.

## 3. Verification against the canonical store

**Timestamp convention — same, no offset.** Joining CSV to canonical over the overlap era
at minute-shifts of −1 / 0 / +1 gives **8,227 / 8,249 / 8,227** matched bars. Shift **0**
wins, so the CSV uses the **same labelling convention as the canonical store** — there is
no one-minute misalignment of the kind that would inject a silent one-bar lead or lag.

**Values — independently confirmed.** Over the 8,249 overlapping bars (22 canonical files,
2024-11 → 2025-03):

| Metric | Value |
|---|---|
| Fraction exactly equal | **0.9999** |
| Mean abs difference | **0.000005** |
| Max abs difference | **0.040000** |

This is an independent cross-source confirmation that the CSV carries the same series as
the canonical feed. It is the strongest provenance evidence available without a vendor
statement, and it is the same test that closed the G1-B1 index gate.

## 4. Defects found — all bounded, none fatal

| # | Defect | Extent | Assessment |
|---|---|---|---|
| D1 | **Structurally invalid OHLC** — `high < low`, or `open`/`close` outside `[low, high]` | **2,547 rows across 28 sessions, entirely in 2018 (1,319) and 2019 (1,228)** | A localized era defect, not pervasive (0.27% of rows). Must be quarantined or repaired before any use; the affected sessions are enumerable |
| D2 | **Short sessions** | 41 sessions below 375 bars (10 with 60, 2 with 105, min 53) | Enumerable; treat as ineligible rather than pad |
| D3 | **Truncated tail** | Ends mid-session at **2025-03-05 11:30** | The download stopped; the last session is partial and must be dropped. 2025-03-06 → present is simply absent |
| D4 | **Sub-minute timestamps** | 46 sessions start 09:15:01/09:15:02; 28 end 15:29:01 | Tick-resampling residue. Floor to the minute, or the join key breaks |
| D5 | **Unknown provenance** | No vendor named, no ingest script, no checksum | §3 substitutes measurement for a provenance statement; that is weaker than a stated source and must be recorded as such |

**Not a defect — Diwali Muhurat.** 600 rows sit outside regular clock hours (≈18:15–19:14)
on exactly ten dates: 2015-11-11, 2016-10-30, 2017-10-19, 2018-11-07, 2019-10-27,
2020-11-14, 2021-11-04, 2022-10-24, 2023-11-12, 2024-11-01. These are **Muhurat trading
sessions**, all present in `trading_calendar`, and this file *has* them — a surface the 1d
index store is separately known to be missing. Correct data; do not filter it out as an
anomaly.

## 5. What this does and does not change

**Changes.** The P1 conclusion "no continuous intraday VIX history exists" was correct
about the *canonical store* and is now incomplete about the *repo*. A decade of 1m India
VIX exists on disk. Any PTMS hypothesis wanting intraday volatility state as a covariate
is no longer data-blocked outright — it is **certification-blocked**, which is a different
and much cheaper problem.

**Does not change.** This file is **not** the canonical store and must not be silently
stitched into it (standing rule; the `1m_vendor` precedent). It is uncertified,
unversioned, gitignored, and of unstated origin. Nothing may be gated on it until it has
an ingest script, a recorded source, a checksum, and a certification pass.

## 6. Recommended path (not authorized here)

1. **Record provenance** — operator states the vendor/source and how it was obtained.
2. **Ingest script**, committed and re-runnable, writing to a clearly vendor-labelled
   location — never into `nse/candles/1m/{date}.duckdb`. Copy-first baseline before any
   write to an existing store (standing lesson: provenance cannot be reconstructed after
   the fact).
3. **Certification arms**, all meta/substrate level: contiguity against `trading_calendar`;
   D1 quarantine with the 28 sessions enumerated; D2/D3/D4 handling rules fixed in code;
   the §3 overlap equality re-run as a gate, not a one-off.
4. **Extend the overlap check** — canonical VIX 1m runs to 2026-09-11, so the 2024-11-29 →
   2025-03-05 overlap can be re-tested continuously as canonical coverage improves.
5. Only then may a hypothesis declare it as a data surface, with an exposure-register row.

This belongs in **P2 (substrate certification)**, not P0/P1, and is a candidate to be run
alongside it rather than ahead of it.
