# G1-R Re-Ingest — Verification, Round 3

**Reviewed:** 2026-07-21 · read-only measurement of the 1d index store as produced by
`scripts/ingest_index_history.py` · no data mutated, no window read.
**Against:** the Gate-set-A contract in `CARRY_INDEX_REINGEST_SPEC.md` §3.
**Method:** every file in the store opened directly; gate quantities recomputed independently
rather than read off the ingest's own report.

---

## Verdict

**The re-ingest acquired the data that closes the beta blocker, and then hid it under an
un-canonicalized symbol.** Two of the six Gate-A checks fail, and both failures are the same
single defect.

| Gate A check | Requirement | Measured | Verdict |
|---|---|---|---|
| A1 calendar completeness | known absences only | 10 absences declared | see §4 (label defect) |
| **A2 beta computability** | **252-session beta ≤ 2013-06-30** | **2014-02-14** | **FAIL** |
| A3 schema uniformity | all `timestamp` = `TIMESTAMP` | 3,548 / 3,548 `TIMESTAMP` | **PASS** |
| **A4 symbol hygiene** | **`symbol LIKE '%CNX%'` → 0** | **1,919 rows** | **FAIL** |
| A5 no duplicates | ≤1 Nifty 50 row per file | 0 files with >1 | **PASS** |
| A6 continuity | no 8%+ move at a source seam | not re-run here | not assessed |

The prior session's summary reported the A2 number correctly (**2014-02-14**) but did not
compare it against the gate the same script implements (`ingest_index_history.py:285`, needs
`≤ 2013-06-30`). Reported as a fact, not evaluated as a gate.

---

## 1. Measured state of the store

```
total 1d files                     3,548
timestamp type histogram           {'TIMESTAMP': 3548}
files with >1 Nifty 50 row         0
NSE_INDEX|Nifty 50 sessions        3,307   (2013-02-08 -> 2026-07-21)
files before 2013-02-08            241     (2012-02-21 -> 2013-02-07)
rows matching '%CNX%'              1,919
earliest 252-session beta date     2014-02-14
```

Note `3,307 + 241 = 3,548` — exactly the file count. Every file in the store has an index
row; 241 of them simply do not have it under the name `Nifty 50`.

---

## 2. The defect — `S&P CNX Nifty` is the Nifty 50, written through as a separate identity

The 1,919 CNX rows are two disjoint populations:

| Rows | Span | Symbols |
|---:|---|---|
| **1,205** | **2012-02-21 → 2013-02-07** | `S&P CNX Nifty`, `S&P CNX 500`, `S&P CNX Nifty Shariah`, `S&P CNX 500 Shariah`, `S&P CNX Nifty Dividend` — **5 × 241, written by this re-ingest** |
| 714 | 2015-03-02 → 2015-11-06 | `CNX DEFTY`, `CNX High Beta`, `CNX Low Volatility`, `CNX Alpha Index`, `CNX Shariah25`, `CNX Dividend Opportunities` — 6 × 119, pre-existing, six niche indices with no modern successor (round 2 §1) |

**`NSE_INDEX|S&P CNX Nifty` is the Nifty 50.** That was the index's official name until the
2013 rebrand (S&P CNX Nifty → CNX Nifty → Nifty 50). Its 241 sessions are genuine Nifty 50
history sitting in the store under an alias, invisible to every query that selects
`symbol = 'NSE_INDEX|Nifty 50'` — including the beta computation §4 of the pre-registration
depends on.

### Root cause

`scripts/ingest_index_history.py:117-122`:

```python
mapped = CNX_TO_CURRENT.get(name)
if mapped is not None:
    return mapped
if name.startswith("CNX "):
    raise ValueError(f"Unmapped CNX index name: {name!r}")
return f"NSE_INDEX|{name}"
```

Two aligned misses:

1. `CNX_TO_CURRENT` (line 45) contains `"CNX Nifty"` but **not** `"S&P CNX Nifty"` — the name
   the archive actually serves for 2012-02-21 → 2013-02-07.
2. The hard-fail guard is prefix-anchored on `"CNX "`, so `"S&P CNX Nifty"` does not match it
   and falls through to line 122, written through as `NSE_INDEX|S&P CNX Nifty`.

This is precisely the fall-through the spec named as non-negotiable #3 — *"Any index name not
in the map and not already `NSE_INDEX|`-canonical must be skipped and counted, never written
through as `f"NSE_INDEX|{raw_name}"`. The fall-through is what created six pre-2016 CNX
indices living as separate identities from their post-2016 selves."* The guard was written to
catch exactly this and was anchored one token too narrowly.

---

## 3. Impact — A4 and A2 are one defect, and it is recoverable without re-downloading

The 241 hidden sessions all sit **before** the current Nifty 50 start. Canonicalizing them
moves the series start from 2013-02-08 back to **2012-02-21** and pushes the 252nd session
from 2014-02-14 to roughly **late February 2013** — the 241 pre-2013-02-08 sessions plus ~11
more. That is comfortably inside the `≤ 2013-06-30` gate.

**So Gate A2 fails on a naming bug, not on missing data.** The archive backfill did its job:
the spec's core claim — *"Backfilling to the archive floor puts ~750 index sessions before
TRAIN's first formation … and TRAIN does not move"* — is upheld by the acquisition and
defeated only by the symbol write-through. The fix is a re-key of existing rows plus a map
entry; **no re-download is required**, and TRAIN stays pinned at 2016-03-31.

Until it is fixed, the pre-registration's §4 beta neutralization is **not computable as
written** for TRAIN's early formations — the same blocker round 2 §2 raised, still open, now
for a different reason.

---

## 4. Secondary defects (LOW — record, do not block)

1. **The absence count contradicts its own label.** `run_final_gates` declares a
   10-date `known_absences` set (`ingest_index_history.py:457-459`) and then prints
   `"Exactly 7 calendar misses remain: {known_absences}"` (line 487) — printing ten dates
   under the word "seven". The spec's Gate A1 allows *exactly* the 7 named dates and calls any
   other miss a FAIL; three dates (`2015-02-02`, `2015-02-17`, `2015-09-25`) were added to the
   allow-list rather than reported as gate failures. That may well be correct — they are
   plausibly holidays absent from the equity calendar — but **widening an allow-list is a gate
   result, and it was not reported as one.**
2. **Dead variable.** `main()` defines a second, 7-date `known_absences`
   (lines 529-530) that is never read. Harmless, but it is the stale copy of the number in
   dispute above.
3. **Latent parse fragility.** `parse_archive_csv` uses `line.split(",")` (line 135); an index
   name containing a comma would shift fields silently. Does not bite on the current files —
   the same LOW finding round 2 §3 recorded for the G2 script.

---

## 5. Required correction — G1-R2 (implementation prompt, issue as-is)

> **Task: G1-R2 — canonicalize the pre-2013 index identity.** Edit
> `scripts/ingest_index_history.py` and re-key the affected rows. Do not re-download the
> archive; the data is already local. Do not touch the pre-registration.
>
> 1. **Widen the map.** Add the served 2012-era names to `CNX_TO_CURRENT`, at minimum
>    `"S&P CNX Nifty": "NSE_INDEX|Nifty 50"` and `"S&P CNX 500": "NSE_INDEX|Nifty 500"`.
>    Derive the full set from the store — `SELECT DISTINCT symbol ... WHERE symbol LIKE '%CNX%'`
>    — not from recall. A name with no modern successor (`S&P CNX Nifty Shariah`,
>    `S&P CNX 500 Shariah`, `S&P CNX Nifty Dividend`) maps to nothing and must be **skipped and
>    counted**, never written through.
> 2. **Fix the guard, not just the map.** Replace `name.startswith("CNX ")` with a test that
>    fires on any name containing `CNX` (and any other legacy vendor prefix present in the
>    store). The bug is that an unmapped legacy name could reach line 122 at all; a wider map
>    with the same narrow guard leaves the next alias to slip through silently.
> 3. **Re-key existing rows in place.** For the 241 files 2012-02-21 → 2013-02-07, rewrite
>    `NSE_INDEX|S&P CNX Nifty` → `NSE_INDEX|Nifty 50` (delete-then-insert, preserving OHLC and
>    the `source` provenance column). Copy-first discipline: validate on a copy of the store,
>    then apply. Assert exactly one `NSE_INDEX|Nifty 50` row per file afterward.
> 4. **Re-run Gate set A** and report every check, pass or fail.
> 5. **Report the A1 allow-list honestly.** For each of `2015-02-02`, `2015-02-17`,
>    `2015-09-25`, state the evidence that it is a genuine non-session (NSE holiday list or
>    absence from `trading_calendar`), or reclassify it as a gate failure. Fix the
>    `"Exactly 7"` label to print the set's actual size. Delete the dead `known_absences` in
>    `main()`.
>
> **Falsifiable predictions — state PASS/FAIL on each before reporting anything else:**
> - `NSE_INDEX|Nifty 50` sessions rise from 3,307 to **3,548** — one per file in the store.
> - Series start moves from 2013-02-08 to **2012-02-21**.
> - Earliest 252-session beta lands in **Feb–Mar 2013**, satisfying `≤ 2013-06-30`; Gate A2 PASS.
> - Rows matching `%CNX%` fall from 1,919 to **714** — the six 2015 niche indices only.
>   (Gate A4 as written demands 0; if those six are to remain, the gate must be amended to
>   name them as accepted exclusions, in the register, rather than quietly tolerated.)
> - No file has more than one `NSE_INDEX|Nifty 50` row.
> - No OHLC value changes for any date already carrying a Nifty 50 row.

---

## 6. What this round does not certify

This verifies **G1-R against the Gate-A contract only**. It is not a substrate certification:
`CARRY_SUBSTRATE_CERTIFICATION_SPEC.md` (P2) remains unrun, and the G2 cleanup listed in round
2 §8 (widen Tier 1, adopt NSE labels over the hand register, `evidence` column, Tier-2
interval handling) remains open and is unaffected by this finding.

The pre-registration is still **DRAFT and unfrozen**, and its §9 sentence *"beta warms up off
2010+ adjusted spot"* is still factually wrong about the market leg — the correction
`CARRY_INDEX_REINGEST_SPEC.md` §1.2 called for has not been made. That edit must land before
freeze.

**Windows untouched:** SEALED 2023-01-01 → 2026-07-20 unread; HOLDOUT 2021–2022 unspent; no
TRAIN read taken. Nothing here reads futures or any return series.
