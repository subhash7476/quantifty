# G1-R2 Applied Fix — Verification, Round 5

**Reviewed:** 2026-07-22 · read-only re-measurement of the 1d index store · no data mutated,
no window read.
**Against:** Gate set A (`CARRY_INDEX_REINGEST_SPEC.md` §3) and the required corrections in
`CARRY_G1_R2_VERIFICATION.md` §5.
**Method:** all 3,548 files opened directly, `read_only=True`; every claim in the delivered
completion report re-derived from the store rather than accepted.

---

## Verdict — **NOT ACCEPTED. The store lost 59 sessions of the market leg.**

The two code changes are correct and worth keeping. The data operation that accompanied them
destroyed real Nifty 50 history, and the completion report scored two gates in the wrong
direction.

| Claim in the completion report | Measured | |
|---|---|---|
| Guard changed to containment test | `"CNX " in name`, `__SKIP__` handling added | **TRUE** |
| Map widened (`S&P CNX 500`, two Shariah skips) | present in diff | **TRUE** |
| 482 Shariah rows deleted | 482 gone | **TRUE** |
| **A4 (CNX hygiene) PASS — "714 CNX rows"** | **714 ≠ 0; committed gate prints FAIL** | **FALSE — gate result inverted** |
| **A2 PASS — "beta from 2013-05-23"** | gate genuinely does pass; the date is the damage signature | **TRUE but inadequate — the gate is blind, see §2** |
| **Provenance established, rebuildable from committed code** | rows still originate from ad-hoc SQL | **FALSE** |
| Vendor CSVs present and required | present; **matched by the ingest glob: none** | **MISLEADING** |

---

## 1. The damage — 59 contiguous sessions of `NSE_INDEX|Nifty 50` are gone

```
NSE_INDEX|Nifty 50 sessions   3,548  ->  3,489     (-59)
files with NO Nifty 50 row        0  ->     59
affected span              2012-11-15 -> 2013-02-07   (contiguous, no survivors)
affected files             28 rows -> 25 rows each
fully empty files                 0
```

Each of the 59 files lost exactly three rows: the two Shariah names **and `NSE_INDEX|Nifty 50`**.
The other 182 pre-2013 files lost only the two Shariah rows and kept their Nifty 50.

**The cause is not reconstructable, and this report does not assert one.** The SQL was ad-hoc and
not retained, so what can be shown is only this: 59 Nifty 50 rows present at round 4 are absent at
round 5; the affected dates are contiguous; and they are co-located with the Shariah deletion in
both time and file set. The most plausible reading is that the Shariah cleanup over-matched on
this subset — but that is an inference, not a measurement, and it is recorded as one. (Writing an
inferred mechanism into a governance report as fact is the specific failure this track has now
made five rounds of corrections for; it applies to the reviewer too.)

The hole sits immediately before the old series start — the *exact* 241-session block round 4
had just recovered. **A quarter of the newly recovered history was destroyed by the operation
meant to finish recovering it.**

Nothing is permanently lost: the NSE archive serves all 59 dates, so this is fully re-ingestable.

---

## 2. Every Gate-A check passes over the hole — a defect in the gate contract, not just the data

This is the load-bearing finding, and it is worse than the deletion itself.

| Check | Why it cannot see 59 missing sessions |
|---|---|
| **A1 calendar completeness** | Compares **file existence** against the equity calendar. All 3,548 files still exist — they just no longer contain a Nifty 50 row. Blind by construction. |
| **A2 beta computability** | Only asks the **date of the 252nd session**. Losing 59 early sessions pushed it 2013-02-22 → **2013-05-23**, still ≤ 2013-06-30, so it prints PASS. The slipped date *is* the damage signature, and it was reported as a pass detail. |
| **A5 no duplicates** | Counts `> 1`. A count of `0` is not `> 1`. |
| **A6 continuity** | Computes % change between **consecutive available** rows. The seam across the hole is 2012-11-13 close 5666.95 → 2013-02-08 close 5903.50 = **+4.17%**, under the 8% threshold. A three-month gap reads as a quiet day. |

**Gate set A has no contiguity check on the Nifty 50 series itself.** Add one before P2:
*every date in the equity trading calendar within the store's span must carry exactly one
`NSE_INDEX|Nifty 50` row* — file existence is not row existence. Without it, the gate certifies a
series with holes in it, which is precisely what it did here.

**Generalize it: a completeness check on the container is not a check on the contents.** Before
trusting `CARRY_SUBSTRATE_CERTIFICATION_SPEC.md` (P2) or the G2 sector checks, grep both for the
same file-existence-as-proxy pattern. This class of blind spot is unlikely to appear only once.

> The A2 movement was visible in the completion report itself — round 4 recorded 2013-02-22, the
> report says 2013-05-23. A number that moves in the wrong direction between rounds is a finding,
> not a detail. It was printed and not interrogated.

---

## 3. A4 was reported PASS against a gate that requires zero

`ingest_index_history.py:317` passes only on `total == 0`; at 714 it appends `A4-cnx` to
`failures` and prints `FAIL: 714 CNX references remain`. The report records **PASS · "714 CNX rows
(6 niche indices only)"**.

The *reasoning* behind treating the six 2015 niche indices as acceptable is sound and was
anticipated in round 3. But round 4 §2 was explicit about the only two legal routes: **finish the
skip, or amend the gate to name them as accepted exclusions in the register.** Neither was done.
Declaring PASS against an unamended gate that prints FAIL is the third route, and it is the one
that must never be taken — it converts a known, defensible exclusion into an undocumented one.

---

## 4. Provenance is still not established

The §5.1 correction was specific: **snapshot the 241 files → fix `canonicalize()` → delete and
re-ingest 2012-02-21 → 2013-02-07 from the NSE archive through the committed ingest → diff
archive-derived OHLC against the ad-hoc rows.**

What happened instead: `canonicalize()` was fixed (correctly), and then rows were deleted by
another ad-hoc operation. **The corrected ingest was never run.** So:

- The 3,489 surviving pre-2013 Nifty 50 rows *still* originate from the first night's ad-hoc SQL.
  No committed code has ever written them.
- The store is **still not rebuildable from the repo** — the claim "provenance established" is
  the opposite of the measured state.
- The copy-first snapshot was skipped a second time, so the 59 deleted rows cannot be diffed
  against what replaces them.

The good news is that the fixed `canonicalize()` makes the correct path *cheaper* than what was
attempted: a clean re-ingest of the 241-session block now skips the Shariah names automatically,
restores the 59 lost sessions, and produces committed provenance — in one run.

---

## 5. Vendor files are present but invisible to the ingest

`data/market_data/vendor/niftyindices/` holds three files:
`NIFTY 50_Historical_PR_01012010to31122010.csv` and the 2011 / 2012 equivalents.

`VENDOR_DIR.glob("nifty50_*.csv")` matches **zero** of them — the stem is `NIFTY 50_` (with a
space), not `nifty50_`. **Gate set B will continue to silently skip** (`"source (b) not supplied"`)
with the files sitting right there. Either rename to `nifty50_2010.csv` … `nifty50_2012.csv`, or
widen the glob and teach `parse_vendor_file` the vendor's actual column headers. "Verified the
files are present" is not the same as "the pipeline can read them" — the second was not checked.

---

## 6. Required to close G1 — one operation, not four

1. **Snapshot** `data/market_data/nse/candles/1d/` for 2012-02-21 → 2013-02-07 (241 files). This
   is the third time the copy-first step has been specified; it has been skipped twice.
2. **Delete and re-ingest that block from the NSE archive** through the now-corrected committed
   ingest. Restores the 59 lost sessions, skips the Shariah names by construction, and gives every
   pre-2013 row committed provenance for the first time.

   **This recovery is demonstrated, not hoped for.** Round 3 §2 recorded the five `S&P CNX …`
   populations as *"5 × 241, written by this re-ingest"* — the archive path already produced all
   241 dates through the committed ingest once. The only change is that `canonicalize()` now maps
   the name instead of writing it through.

   **Verify before deleting.** Fetch and parse the archive for 2012-02-21 → 2013-02-07 and confirm
   it yields all 241 dates (including the 59) *before* touching the store. The snapshot covers
   rollback; verify-first ensures a third mishap cannot deepen the hole.
3. **Diff** archive-derived OHLC against the snapshot and report the mismatch count — the check
   that retires round 4's prediction 6.
4. **Add the contiguity gate** (§2) and re-run **all** of Gate set A, reporting each check's
   printed verdict verbatim — not a summarized one.
5. **Disposition the 714 rows in the register**, or amend A4's text to name the six 2015 indices
   as accepted exclusions. Then A4 genuinely passes.
6. **Make the vendor files loadable** (§5), or state that Gate B is deliberately skipped.

Do not run P2 until 1–5 are done. A substrate certification over a series with a 59-session hole
and no committed provenance certifies nothing.

---

## 7. What is genuinely good here

The `canonicalize()` change is exactly right — containment test, explicit `__SKIP__` sentinel,
skip-and-count rather than write-through. It closes the naming-bug class for good, including the
next legacy alias nobody has thought of yet. Keep it, commit it, and let it do the re-ingest.

**Windows untouched:** SEALED 2023-01-01 → 2026-07-20 unread; HOLDOUT 2021–2022 unspent; no TRAIN
read taken. TRAIN remains pinned at 2016-03-31 — none of this moves a formation.

**The lesson, a fifth time.** Round 3 was stale within hours. Round 4 found it by re-measuring.
Round 5 found that the fix for round 4 deleted data while reporting two gates green. **Every round
of this track has found the previous round wrong by re-measuring rather than re-reading — and the
one thing that has never yet been done, across three separate instructions, is taking the snapshot
before the write.**
