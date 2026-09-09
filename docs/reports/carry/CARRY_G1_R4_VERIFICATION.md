# G1 Vendor Gap Fill — Verification, Round 6

**Run:** 2026-07-22 · fill executed through committed code at operator direction
(*"see if you can use it to fill the gap and close this data chapter"*), then independently
re-measured.
**Sources:** operator CSVs `data/market_data/vendor/niftyindices/NIFTY 50_Historical_PR_*.csv`
(2010–2013, 1,000 sessions) as the fill source; NSE archive rows already in the store as the
cross-check.

---

## Verdict — the 59-session gap is closed and independently corroborated. Gate A is not yet all-green, and the reason is a genuine pre-existing defect the new gate surfaced.

| Check | Before | After | |
|---|---|---|---|
| Nifty 50 sessions | 3,489 | **3,559** | 59 filled from vendor + 11 fetched from archive |
| Files with no Nifty 50 row | 59 | **0** | gap closed |
| Earliest 252-session beta | 2013-05-23 | **2013-02-19** | A2 PASS |
| A3 schema | PASS | PASS | |
| A4 symbol hygiene | FAIL (unamended; printed FAIL at 714) | **PASS** | 714 rows, all 6 symbols registered exclusions |
| A5 duplicates | PASS | PASS | |
| A6 continuity | PASS | PASS | 3 large moves, all known COVID |
| **B1 cross-source agreement** | never ran (glob bug) | **PASS — max close diff 0.0000** | |
| **A7 contiguity (new)** | did not exist | surfaced 16 missing sessions → **PASS** after fetch | see §3 |
| A1 calendar completeness | reported PASS in prior rounds | **FAIL — 16, then 5 after fetch** | left failing deliberately; see §3 |
| B2 extended floor | never ran | FAIL — 7 of 2015's absences unfilled | expected; see §4 |

---

## 1. The corroboration is the headline

Across **all 401 dates** where the operator CSVs and the store overlap — **including all 182 rows
written by the untraceable ad-hoc SQL** — there are **zero** OHLC mismatches beyond 0.005, and the
committed Gate B1 measures **max close difference = 0.0000 index points**.

This substantively resolves the rounds 4–5 provenance anxiety. We still cannot say *what process*
wrote those 182 rows, but their *values* are now proven correct to the tick against an independent
authoritative source. That is a **stronger** guarantee than an archive re-run would have produced,
since the archive is most likely what the ad-hoc SQL drew from — an archive re-run would have
compared a source against itself.

All 59 gap dates were covered by the vendor files; 0 were uncovered.

---

## 2. What was done, and how it differs from the two operations that went wrong

- **Insert-only.** `fill_gap_from_vendor()` writes the absent `NSE_INDEX|Nifty 50` row into files
  that have none. It never deletes, and never touches a date that already carries one. The two
  prior incidents were both deletions.
- **Snapshot first, in code.** Every target file's full contents were written to
  `data/market_data/nse/candles/1d_snapshots/pre_vendor_fill_20260722T141047.csv` — **1,475 rows
  across 59 files** — *before* any write. The copy-first discipline was specified three times and
  skipped twice; putting it inside the committed function is what makes it non-optional.
- **Committed and re-runnable.** `python scripts/ingest_index_history.py --fill-from-vendor`.

Supporting fixes, all latent bugs:

| Fix | Why it mattered |
|---|---|
| `VENDOR_GLOB = "*.csv"` (was `nifty50_*.csv`) | matched **zero** operator files; Gate B had been silently skipping since it was written |
| `_parse_date` + `%d %b %Y` | vendor serves `31 Dec 2012`; previously unparseable |
| A4 rewritten against `ACCEPTED_CNX_EXCLUSIONS` | the gate demanded 0 and could only ever print FAIL; the six discontinued 2015 indices are now **named** exclusions, not quietly tolerated ones |
| B2 bound `2011-01-31` → `2013-06-30` | the old bound presumed a vendor-ingest path that was never built |
| `"Exactly 7"` label | printed a hardcoded 7 over a 10-element set (round 3 finding) |

**The 2010 and 2011 vendor files were deliberately not ingested.** TRAIN is pinned at 2016-03-31
and beta from 2013-02-22 covers it with years to spare, so extending the series to 2010 buys no
formation anything and would mix sources without need. Those files earn their keep as B1
cross-check data. A recorded choice, not an oversight — reversible if the operator wants the
longer series.

---

## 3. Gate A7 found 16 missing sessions on its first run — and they are not the ones it was built for

The new contiguity gate flagged 16 trading dates absent from the Nifty 50 series:

```
2012-03-03  2012-04-28  2012-09-08  2012-11-11  2013-05-11  2013-10-09
2013-11-03  2014-03-19  2014-03-22  2014-12-15  ...  2020-11-14
```

**Measured: all 16 have no store file at all.** They are therefore A1's defect, not A7's — and A7
has been corrected to separate the two classes, reporting "no file" as informational and failing
only on "file present, row absent" (the blind spot it exists for, now **0**).

These are real sessions: Saturday special sessions and Diwali **Muhurat** trading days
(2013-11-03, 2020-11-14). They are in `equity_bhavcopy` and absent from the 1d index store.

**A1 was reported PASS in prior rounds and is FAIL at 16.** A1's code was not touched this
session, and an insert-only fill cannot change file existence — so **A1 has been failing all along
and no prior round re-ran it.** Round 3 flagged exactly this risk when it found three dates added
to the allow-list rather than reported as failures; the finding was larger than it looked.

**At least one is inside TRAIN** (2020-11-14). A 252-day beta window spanning a missing session is
computed over 251 real sessions plus a silent skip. Sixteen sessions across fourteen years is a
small effect, but it is not nothing, and it must be dispositioned before P2 rather than discovered
during it.

### Resolution — 11 of 16 recovered from the archive

`--fetch-missing` (operator-authorized) recovered **11**; **5** returned HTTP 404; **0** network
errors. Store: 3,548 → **3,559 files**, A2 improves to **2013-02-19**, and **A7 now PASSES —
every store file in span carries a Nifty 50 row.**

The 5 the archive does not serve, with evidence gathered rather than assumed:

| Date | Weekday | `equity_bhavcopy` rows | Reading |
|---|---|--:|---|
| 2012-11-11 | **Sunday** | **14** | Not a trading session — a bhavcopy artifact. Exclude from the calendar; do not source. |
| 2013-10-09 | Wed | 1,357 | Real session — **filled from operator CSV** |
| 2014-03-19 | Wed | 1,479 | Real session — **filled from operator CSV** |
| 2014-12-15 | Mon | 1,498 | Real session — **filled from operator CSV** |
| 2016-06-20 | Mon | 1,542 | Real session — **filled from operator CSV** |

### Closed — the operator supplied all four

Four single-date CSVs downloaded from
[niftyindices.com/reports/historical-data](https://www.niftyindices.com/reports/historical-data)
and inserted via `_create_absent_date_files()`. Verified against source: closes 6007.45 /
6524.05 / 8219.60 / 8238.50 all match exactly; `timestamp` is `TIMESTAMP` in each.

**Store: 3,563 files. A1's remaining miss is 1 — `2012-11-11`, the Sunday artifact.** Every real
trading session in span now has a file, and the only open A1 item is a date that should be dropped
from the calendar rather than sourced.

These four files carry the Nifty 50 row only, since the vendor serves one index per download.
Sufficient for the Carry market leg; the same site serves Bank Nifty / VIX / sector indices for
those dates if P2 ever needs them.

> **Process note.** The first attempt ran the full `--fill-from-vendor` path, which auto-ran
> Gate A + B across all 3,563 files — several minutes of sweep for a four-row insert, and it
> would have inserted **nothing**: `fill_gap_from_vendor()` returns early when no *existing* file
> needs a row, which was now true, so the new absent-date phase was unreachable. Both fixed: the
> early return now calls that phase, and `--fill-from-vendor` no longer auto-runs the gate suite.
> **Match the verification to the size of the change** — a four-row insert warrants checking those
> four rows, not re-certifying the store.

---

## 4. B2 fails for a correct reason

B2 checks that the seven known 2015 absences are filled from source (b). The supplied vendor files
span **2010–2013** and cannot cover 2015. This is source coverage, not a store defect — either
supply 2015 vendor data or re-scope B2 to the span the operator actually provided.

---

## 5. State for P2

**Closed:** the 59-session gap · A2 · A3 · A4 (registered) · A5 · A6 · B1 at 0.0000 · the
values-provenance question for all 241 pre-2013 rows · the Gate-B glob bug · the copy-first
discipline, now enforced in code.

**Open before P2:** A1/A7's 16 missing sessions (§3) · B2's source coverage (§4) · the P2 spec and
G2 checks should be grepped for the same *file-existence-as-proxy-for-row-existence* pattern that
A7 was invented to catch — this class of blind spot is unlikely to appear only once.

**Windows untouched:** SEALED 2023-01-01 → 2026-07-20 unread; HOLDOUT 2021–2022 unspent; no TRAIN
read taken. TRAIN remains pinned at 2016-03-31.

**The lesson, sixth round.** Every prior round found the previous one wrong by re-measuring. This
round is the first where the fix was verified before being announced — and the new gate found a
defect in the *same run* that closed the old one. Gates earn their keep on first contact; the
question for P2 is which other checks test the container instead of the contents.
