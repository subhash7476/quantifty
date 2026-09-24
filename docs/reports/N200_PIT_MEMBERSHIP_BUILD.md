# Nifty 200 PIT Membership (A1) — Build Report

**Date:** 2026-09-12 · **Store:** `data/isd/n200_membership.duckdb`
(`n200_events`, `n200_membership`, `n200_audit`)
**Sources:** 228 NSE/IISL press releases (`data/reference/nse_index_pr/`,
`manifest.csv`, plus `ind_prs23082021.ocr.txt` — the OCR transcript of the one
scanned release, held beside the PDFs with a manifest row carrying both sha256s) + today's official lists (`ind_nifty200list_20260912.csv`,
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
(31 pairs, asserted present or the build fails).

## Gates

| Gate | Result |
|---|---|
| Backward-walk breaks | **0** |
| Forward-replay breaks | **0** |
| **Union reconciliation** (Nifty 200 = Nifty 100 + Nifty Midcap 100, 2018-06-29 → 2026-09-11) | **44 dates checked, 0 mismatches** |
| Canonical per-symbol parity (events vs intervals) | **0 violators** |
| Missing symbols / missing effective dates (N200) | **0 / 0** |
| Overlapping intervals per symbol / open at terminal | **0 / 200** |
| Intervals asserting membership before the security listed | **2** (§Residuals 1) |
| Member counts == 200 | **42 dates read 201 or 202** — every one accounted for below |
| Terminal open set vs today's official 200 | exact — but see the note below |

**The terminal check is an identity, not evidence.** The forward replay is the exact inverse
composition of the backward walk over the same ordered event list, so whenever backward breaks
are 0 it *must* return the anchor — delete an entire press release and it still passes, because
the launch state simply shifts to absorb it. It is retained as a self-consistency assertion on
the two walks, and `n200_audit.terminal_is_identity` says so in the store.

**What actually supports the post-2018 table** is therefore (a) parse fidelity against the
primary PDFs, (b) member counts of exactly 200 from 2020-06-26 onward outside the documented DVR
episode, and (c) the union gate, which reconstructs Nifty 200 from two independently walked
streams and is the only check here that can see a missing inclusion paired with a missing
exclusion. The union gate does not cover 2011–2018: before 2018-06-29 the midcap stream is spread
across five renamed labels and reconstructing it is a separate problem.

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

1. **Two intervals assert membership before the security existed.** `MGL` (listed 2016-07-01)
   and `PNBHOUSING` (listed 2016-11-07) both carry genuine, balanced demotion exits
   (2022-03-31 / 2020-09-25) but their **entries appear in no press release in the archive**
   (every 2016–2022 review verified present; full-text search clean). The backward walk therefore
   carries them to LAUNCH_DATE. Reported per name by the `pre_listing_intervals` gate rather than
   left implicit. Entry bounds from listing date + the 3-month IPO rule:
   MGL ∈ [2017-03, 2022-03), PNBHOUSING ∈ [2017-09, 2020-09).
   **The error is in the interval start, not in the membership** — from their true entries onward
   both are correct, which is why the union gate reconciles exactly over 2018→2026.

2. **Member-count deviations — all 42, with causes.** The gate records every date whose count is
   not 200; none is unexplained, and the composition is:

   | Span | Count | Composition |
   |---|--:|---|
   | 2011-07-19 (launch) → 2015-10-19 | **201** | 200 + 2 phantoms (§1) − 1 unsourced genuine entry |
   | 2016-04-01 → 2017-03-31 | **202** | 201 (NSE-stated DVR era) + 2 − 1 |
   | 2017-07-05 → 2020-03-19 | **201** | 201 (DVR era); ABIRLANUVO's unmatched exit removes the earlier surplus |
   | 2023-09-29, 2024-03-28 | **201** | 201 (second DVR episode) |

   So across 2011–2015 the table carries **two members too early and one member missing** — a net
   of +1. That decomposition is derivable (the phantoms are provable, the count is measured); the
   identity of the missing entry is **not** derivable from the corpus and is not claimed.
   The launch state is itself one of the 42: it is a member count like any other, and it was
   previously the one span the gate never evaluated.

3. **The count gate bounds the net error, never the gross.** Two missed events of opposite sign
   cancel and leave it reading exactly 200 — §2's own 2020-06-26 → 2022-03-31 span is the concrete
   case, reading 200 while still carrying MGL early. This is precisely the blind spot the union
   gate exists to cover, and it is covered from 2018-06-29 on. **For 2011 → mid-2018 no such
   independent check exists**, so the honest statement for that era is the one in §1–§2, not a
   claim of exactness.

4. **Launch composition (2011-07-19) rests on backward induction** — no public inaugural list
   exists. Era labels across the 31 renames are exact per `symbol_changes` effective dates.

5. For A1 consumption: **2018-06-29 → present is independently reconciled and exact.** The
   2011–2018 span carries the bounded uncertainty in §1–§2 — 2 names too early, 1 missing, out of
   ~200. Immaterial to a diversified cross-sectional result, but disclosed rather than smoothed.

## Usage

```sql
-- members on DATE 'D'
select symbol from n200_membership
where valid_from <= DATE 'D' and (valid_to is null or valid_to > DATE 'D');
```

Symbols are **as-printed at the time** (era-correct across renames);
join to prices via `symbol_entity_intervals`/ISIN as usual.
Reproduce: `python scripts/isd/build_n200_membership.py`.
