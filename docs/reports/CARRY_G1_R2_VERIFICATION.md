# G1-R2 Re-Key — Verification, Round 4

**Reviewed:** 2026-07-21 · read-only re-measurement of the 1d index store · no data mutated,
no window read.
**Against:** the Gate-set-A contract in `CARRY_INDEX_REINGEST_SPEC.md` §3 and the six falsifiable
predictions in `CARRY_G1_R_VERIFICATION.md` §5.
**Method:** all 3,548 files opened directly, `read_only=True`; every quantity recomputed rather
than read off the ingest's own report.

---

## Verdict

**The beta blocker is closed — Gate A2 now PASSES on real, sane data. But the re-key that closed
it was performed by code that exists nowhere in the repository, and it did not do what the prompt
specified.** Gate A4 still fails, at 1,196 rows against a predicted 714.

| Gate A check | Requirement | Round 3 | Round 4 | Verdict |
|---|---|---|---|---|
| **A2 beta computability** | 252-session beta ≤ 2013-06-30 | 2014-02-14 | **2013-02-22** | **PASS** |
| A3 schema uniformity | all `timestamp` = `TIMESTAMP` | 3,548 / 3,548 | unchanged | PASS |
| **A4 symbol hygiene** | `symbol LIKE '%CNX%'` → 0 | 1,919 | **1,196** | **FAIL** |
| A5 no duplicates | ≤1 Nifty 50 row per file | 0 | **0** | PASS |
| A6 continuity | no 8%+ move at a source seam | not assessed | **0 in the new span** | PASS |
| A1 calendar completeness | known absences only | 10 declared as 7 | **not re-run** | open (§4) |

---

## 1. Measured state

```
total 1d files                 3,548   (2012-02-21 -> 2026-07-21)
NSE_INDEX|Nifty 50 sessions    3,548   (2012-02-21 -> 2026-07-21)
NSE_INDEX|S&P CNX Nifty rows       0
rows matching '%CNX%'          1,196   [gate needs 0]
files with >1 Nifty 50 row         0
earliest 252-session beta     2013-02-22   [gate needs <= 2013-06-30]
```

### Predictions from `CARRY_G1_R_VERIFICATION.md` §5

| # | Prediction | Measured | |
|---|---|---|---|
| 1 | Nifty 50 sessions 3,307 → **3,548** | 3,548 | **PASS** |
| 2 | Series start → **2012-02-21** | 2012-02-21 | **PASS** |
| 3 | Earliest beta in **Feb–Mar 2013**, ≤ 2013-06-30 | 2013-02-22 | **PASS** |
| 4 | `%CNX%` rows 1,919 → **714** | **1,196** | **FAIL** |
| 5 | No file with >1 Nifty 50 row | 0 | **PASS** |
| 6 | No OHLC change on dates already carrying a Nifty 50 row | **not verifiable** | see §3 |

### The re-keyed data is genuine

241 pre-2013 Nifty 50 rows, zero NULL closes, close range 4835.65 – 6082.30, opening at
**5607.15 on 2012-02-21** and **5938.80 on 2013-02-07** — historically correct levels for the
Nifty in that span. Zero rows violate `low ≤ open, close ≤ high`. Zero intra-span daily moves
above 8%. The seam into the pre-existing series is clean: 2013-02-07 close 5938.80 → 2013-02-08
close 5903.50, **−0.59%**. The identity fix recovered real history, not an artifact.

---

## 2. Why A4 still fails — three of five legacy names were not dispositioned as instructed

The 1,196 remaining rows are three disjoint populations:

| Rows | Span | Symbols |
|---:|---|---|
| 714 | 2015-03-02 → 2015-11-06 | `CNX DEFTY`, `CNX High Beta`, `CNX Low Volatility`, `CNX Alpha Index`, `CNX Shariah25`, `CNX Dividend Opportunities` — 6 × 119, pre-existing, niche indices with no modern successor |
| **482** | **2012-02-21 → 2013-02-07** | **`S&P CNX Nifty Shariah`, `S&P CNX 500 Shariah` — 2 × 241, still written through as separate identities** |
| 0 | — | `S&P CNX Nifty`, `S&P CNX 500`, `S&P CNX Nifty Dividend` — re-keyed or removed |

The §5 prompt was explicit that a legacy name with no modern successor must be **skipped and
counted, never written through**. `S&P CNX Nifty Shariah` and `S&P CNX 500 Shariah` are exactly
that case, and both are still in the store under their legacy identity. This is the same
fall-through the spec named as non-negotiable #3 — narrowed, not closed.

`S&P CNX Nifty Dividend` is *absent*, which the prompt permits only if it was skipped. Whether it
was skipped, deleted, or re-keyed into `Nifty Dividend Opportunities` cannot be determined,
because — see §3 — there is no artifact to read.

**A4 as written demands 0.** Two dispositions are available and the choice is the operator's:
either finish the skip (drop the 482 written-through rows and count them), or amend the gate to
name the surviving legacy indices as accepted exclusions **in the register**, with the six 2015
names and the two Shariah names listed explicitly. Quiet tolerance is not one of the options.

---

## 3. The governance defect — an unreproducible mutation of the source-of-truth store

**The re-key is not in the repository.** Measured:

- `scripts/ingest_index_history.py` — working-tree mtime 22:09, and its **entire** diff against
  HEAD is one line: `"S&P CNX Nifty": "NSE_INDEX|Nifty 50"` added to `CNX_TO_CURRENT`.
- The 241 pre-2013 store files — mtime **22:33–22:34**, the only files in the whole store with
  fresh timestamps. Something ran *after* the script edit and rewrote exactly those files.
- `git status --untracked-files=all` over `scripts/` and `docs/` shows no new file.

**That one-line edit cannot have produced this state.** `ingest_rows()` deletes then inserts
keyed on the *new* symbol (`ingest_index_history.py:174-184`), so a re-run with a widened map
*adds* `NSE_INDEX|Nifty 50` rows and **leaves the old `S&P CNX Nifty` rows in place**. Those rows
are gone — 0 remain. Something explicitly deleted them, and that something is not in git, not in
the working tree, and not untracked on disk.

**Operator answer (asked 2026-07-22, before this finding was treated as terminal):
ad-hoc SQL, not retained.** So there is no artifact to commit and no `git add` that closes this.
The re-key is real, correct-looking, and **unreproducible as it stands** — precisely the condition
P2 cannot certify around. Disposition is §5.1: regenerate the 241 sessions deterministically from
the NSE archive through the committed ingest, which both restores provenance and independently
checks the ad-hoc SQL's output against source.

**Blast radius is contained.** Measured across the boundary: every one of the 241 pre-2013 files
holds **28 rows / 28 distinct symbols**, identical to 2013-02-08, 2013-03-01 and 2013-06-03, with
`NSE_INDEX|Nifty Bank` present throughout. The mutation did not drop or duplicate sibling index
rows.

Consequences, in order of weight:

1. **The store cannot be rebuilt from the repo.** Re-running the committed pipeline from scratch
   does not reproduce the store the Carry sleeve is about to be certified against. This breaks the
   deterministic-re-runnable-scripts constraint that every prior gate in this program was held to.
2. **Prediction 6 is unverifiable.** "No OHLC value changes for any date already carrying a Nifty
   50 row" needs a pre-mutation baseline to check against. The copy-first discipline the prompt
   mandated — *validate on a copy of the store, then apply* — would have produced exactly that
   baseline. It was not followed, so the check cannot be run, now or later.
3. **The partial hand-edit is still uncommitted**, and on its own it is misleading: it looks like
   the fix, it is a fragment of step 1, and it rewrites no rows.

None of this impugns the *data* — §1 shows the recovered series is sound on every check that can
still be run without a baseline. It impugns the **provenance**, and provenance is what a substrate
certification certifies.

---

## 4. Not re-run this round

- **A1 calendar completeness** and the round-3 §4 finding it carries: `run_final_gates` declares a
  10-date `known_absences` set and prints `"Exactly 7 calendar misses remain"`. Three dates
  (`2015-02-02`, `2015-02-17`, `2015-09-25`) were added to the allow-list rather than reported as
  gate failures. **Widening an allow-list is a gate result and must be reported as one** — with
  the NSE-holiday or `trading_calendar` evidence for each date, or a reclassification to FAIL.
  Still open.
- The dead second `known_absences` in `main()` and the `line.split(",")` parse fragility — both
  still open, both LOW.

---

## 5. Required to close G1

1. **Regenerate the 241 sessions from the archive through the committed ingest.** The operator
   has confirmed the re-key was ad-hoc SQL that was not retained, so there is nothing to commit
   and provenance must be *rebuilt*, not recovered. Fix `canonicalize()` first (steps 2–3 below),
   then delete and re-ingest `2012-02-21 → 2013-02-07` from the NSE archive — free, no window
   touched, TRAIN unmoved.

   **Do this as a validated comparison, not a blind overwrite.** Snapshot the current 241 files
   first (the copy-first baseline that was skipped the first time), regenerate, then diff
   archive-derived OHLC against the ad-hoc-SQL rows and report the mismatch count. A clean diff
   converts today's unverifiable rows into certified ones and retires prediction 6 honestly; a
   dirty diff means the ad-hoc SQL got something wrong and the archive wins. Either outcome is
   worth more than the current state, in which neither can be claimed.
2. **Disposition the 482 written-through Shariah rows** — finish the skip, or register them as
   accepted exclusions alongside the six 2015 names and amend A4's text. Then A4 passes or is
   formally waived; it does not stay red.
3. **Fix the guard, not just the map** — `canonicalize()` still tests `name.startswith("CNX ")`
   (`ingest_index_history.py:121`), so the next legacy alias still falls through to line 123. This
   was step 2 of the G1-R2 prompt and it was not done.
4. **Report A1 honestly** and fix the `"Exactly 7"` label (step 5, not done).
5. **Commit the working-tree edit as part of a complete deliverable**, not on its own.

---

## 6. What this round does not certify

Gate set A only. `CARRY_SUBSTRATE_CERTIFICATION_SPEC.md` (P2) remains **unrun**; the G2 cleanup
remains open and unaffected. The pre-registration is still **DRAFT and unfrozen**, and its §9
sentence *"beta warms up off 2010+ adjusted spot"* is still wrong about the market leg — that
correction must land before freeze.

**Windows untouched:** SEALED 2023-01-01 → 2026-07-20 unread; HOLDOUT 2021–2022 unspent; no TRAIN
read taken. Nothing here reads futures or any return series.

**The standing lesson, once more.** Round 3's numbers were correct and its conclusion was stale
within hours, because the store moved underneath the report. Round 4 found that only by
re-measuring. Do not accept a prior report's claim about the store — including this one.
