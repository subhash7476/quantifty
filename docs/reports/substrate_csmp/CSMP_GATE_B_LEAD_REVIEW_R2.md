# CSMP Gate (b) — Lead-Reviewer Verdict, Round 2 (post R1–R9 remediation)

**Reviewer:** Claude (Lead Reviewer, per `CSMP_PHASE0_CHARTER.md` role split)
**Implementer:** DeepSeek V4 (Prompt 2R → commit `49409e0`)
**Date:** 2026-07-10
**Reviews:** `CSMP_GATE_B_LEAD_REVIEW.md` (Round 1) step 5 — "Lead Reviewer re-verifies §2
arithmetic and issues the verdict."

**Deliverables reviewed:** `scripts/csmp/ingest_corporate_actions.py`,
`scripts/csmp/audit_corporate_actions.py`, `docs/reports/CSMP_GATE_B_CORPORATE_ACTIONS_AUDIT.md`,
`docs/reports/CSMP_GATE_B_MOVES.csv`, tables `corporate_actions` / `adjustment_factors`
and view `equity_bhavcopy_adjusted`.

---

## Verdict: **NOT PASSED — REJECTED (still structural)**

Round 1's catastrophic defects (dividends-as-splits, 5,940× adjusted prices, screen
artifacts) are genuinely fixed. The store is now sane. But the remediation introduced a new
class of defect that is more dangerous than the one it replaced, because it is *plausible*:

1. **The split source is circular.** All 105 non-ETF splits were inferred from the very
   price gaps they are then used to explain. 100% of them sit exactly on a screened
   ≤ −20% move. 73 of 112 have zero corroboration from any BSE event.
2. **The adjusted view is still wrong** — `prev_close` is mis-scaled on every ex-date row.
   The audit's own §4 correctly detected this (22 mismatches) and the commit dismissed it.
3. **Missing split legs are silently masked.** 48 "CA-explained" moves are explained by a
   factor whose magnitude does not remotely match the move. TITAN 2011-06-23 fell −94.7%;
   the only ingested factor is a 1:1 bonus implying −50%. Its missing 1:10 split means
   TITAN's entire pre-2011 adjusted history is wrong by **10×** — and the audit reports it
   as *explained*.

The commit message states *"Structural ingest fixes complete"* and attributes NOT PASSED
solely to *"honest market volatility, not CA artifacts."* Its own generated report
contradicts this on the same page: 22 continuity mismatches and 4 hand-verify failures.

**Quarantine from Round 1 stands and is extended:** `equity_bhavcopy_adjusted` and all
`action_type='SPLIT'` rows of `adjustment_factors` must not be used downstream. The gate-(a)
raw store remains sound and unaffected.

---

## Round-1 findings — disposition

| R1 | Finding | Status |
|----|---------|--------|
| F1 | Dividends ingested as splits | **FIXED** — mapping corrected, 9,004 rows purged, plain-float fallback deleted |
| F2 | No split source | **REJECTED FIX** — replaced by circular inference (see C1) |
| F3 | Move screen spans series/suspension gaps | **FIXED** — EQ+BE union, gap ≤ 5d, resumption section |
| F4 | Continuity check vacuous | **TEST FIXED, BUG EXPOSED, NOT REPAIRED** (see C2) |
| F5 | §2 hand-verify verifies nothing | **IMPLEMENTED AS SPECIFIED — SPECIFICATION WAS WRONG** (see H1) |
| F6 | ex_date is really the record date | **PARTIAL** — done for splits; bonuses still keyed on `BCRD_FROM` |
| F7 | Dividend double-count | **FIXED** — deduped on (symbol, amount, ±7d) |
| F8 | Split factor convention inverted | **FIXED** — factor = new_FV/old_FV; observed range 0.01–0.5 ✓ |
| F9 | Report hygiene | **PARTIAL** — MD is now reviewable; CSV sidecar is empty (H3); dead code not removed (L1) |

---

## Verification performed by the reviewer

All numbers re-derived read-only from `equity_bhavcopy.duckdb` this session.

| Check | Result |
|-------|--------|
| SPLIT events vs factors | 114 events, 112 factors, 2 duplicate `(symbol, ex_date)` keys |
| SPLIT factor provenance | 105 `bhavcopy_gap_*`, 7 `ETF_AMC_notice_*` — **0 from an independent CA feed** |
| Gap-inferred splits sitting exactly on a screened ≤ −20% move | **105 of 105** |
| SPLIT factors with no BSE event within ±7 days | **73 of 112** |
| Gap-inferred splits on stocks with prev_close < ₹25 | 26 (all at the ₹0.10 → ₹0.05 tick floor) |
| BONUS factor provenance | 888 of 888 from the independent BSE feed ✓ |
| RELIANCE adjusted close 2017-09-06 / 2017-09-07 | 411.35 / 409.05 → ratio 1.006 — **backward adjustment is correct** |
| RELIANCE raw prev_close on ex-date 2017-09-07 | 1,645.40 = prior raw close — NSE does **not** pre-adjust prev_close |
| RELIANCE adjusted prev_close 2017-09-07 vs adjusted close 2017-09-06 | 822.70 vs 411.35 — exactly 2× = 1/F, a real view bug |
| Sidecar CSV rows with a populated `class` column | **0 of 5,609** |
| CA-explained moves whose observed return deviates > 15pp from the factor-implied drop | **48 of 569 (8%)** |

---

## Findings

### C1 — CRITICAL — the split source is circular; 26 penny-stock ticks became splits

`ingest_splits_from_bhavcopy()` labels a symbol-day a SPLIT when `prev_close/close` snaps to
{2, 5, 10, 25, 50, 100, 200, 500, 1000} and volume scales. `audit_corporate_actions.py` §3
then classifies a large move as **CA-explained** if any factor < 1 exists within 7 days.
The evidence set and the explanation set are the same rows: **105 of 105 gap-inferred splits
sit exactly on a move the screen flags.** Every such split is self-explaining by construction.
Round 1's F2 acceptance test ("every real split gap must become CA-explained") is satisfied
tautologically and therefore proves nothing.

The false positives are not hypothetical. A −50% move with a volume spike — the ordinary
signature of a collapse — is indistinguishable from a 1:2 split under this rule:

| Symbol | Ex-date | prev_close | close | Assigned factor |
|--------|---------|-----------:|------:|----------------:|
| VISESHINFO | 2016-03-10, 2016-06-15, 2016-06-29, 2019-02-18, 2019-04-11, 2019-08-07 | ₹0.10 | ₹0.05 | 0.5 **× 6 events** |
| MVL | 2019-10-09 **and** 2019-10-11 | ₹0.10 | ₹0.05 | 0.5 × 2 |
| UVSL | 2020-03-17 | ₹0.10 | ₹0.05 | 0.5 |
| SRPL-**RE** | 2023-07-21 | ₹0.10 | ₹0.05 | 0.5 |

These are sub-rupee stocks moving one tick cluster at the price floor, not sub-divisions.
VISESHINFO is assigned six splits, so its pre-2016 adjusted history is divided by 2⁶ = 64.
MVL "splits" twice in two days — physically impossible. `SRPL-RE` is a rights entitlement,
not a share line at all. 73 of 112 splits have no corroborating BSE row of any kind.

**Fix:** a price gap may *locate* an ex-date; it may never *establish* that a corporate
action occurred. Splits need an external source — NSE's CF-CA archive (`nsearchives`) or
BSE's `corporates_act.html` subdivision filter — with the price gap used only to snap the
ex-date. Absent that, exclude the symbol-date from the universe rather than inventing a
factor. At minimum, gap inference must be refused where `prev_close` is below a few rupees
and where the same symbol repeats within a year.

### C2 — CRITICAL — `equity_bhavcopy_adjusted.prev_close` is wrong on every ex-date row

The view scales `open/high/low/close` by `cum_price_factor` computed over events with
`ex_date > trade_date` — correct backward adjustment (verified: RELIANCE adj 411.35 → 409.05
across its 2017 bonus, a 0.6% real move). It then scales `prev_close` on row *t* by that
**same** factor. But `prev_close(t)` is `close(t−1)`, whose correct cumulative factor
additionally includes the event *at t*. Raw bhavcopy `prev_close` is unadjusted (verified:
RELIANCE 2017-09-07 raw prev_close = 1,645.40 = the prior raw close), so nothing compensates.

Result: `adj_prev_close(t) = adj_close(t−1) / F_t` — off by exactly the ex-date factor,
i.e. 2× for a 1:1 bonus. §4 measured this precisely (RELIANCE 822.70 vs 411.35; INFY 1,434.25
vs 717.12; ASIANPAINT 5,118.20 vs 511.82 — a 10× split) and reported **22 mismatches**.
These are real defects in the authoritative research view, not test noise, and the commit
message does not mention them.

**Fix:** in the view, join `prev_close` against the cumulative factor of the *previous*
trading row (equivalently, multiply by `cum_price_factor(t) × F_t` where an event exists at
`t`). §4 then becomes a true regression test and should read 0.

### C3 — CRITICAL — direction-only matching masks missing split legs

§3 accepts a CA as explaining a move on sign agreement alone: `factor < 1 and ret < 0`, any
factor, any magnitude, within 7 days. It never asks whether the factor *accounts for* the
move. 48 of 569 CA-explained moves (8%) deviate more than 15 percentage points from the drop
their factor implies:

| Date | Symbol | Observed | Factor-implied | Factor | Reality |
|------|--------|---------:|---------------:|-------:|---------|
| 2011-06-23 | TITAN | −94.7% | −50.0% | 0.5 (bonus) | 1:1 bonus **+ 1:10 split**; split leg absent |
| 2016-12-01 | SUNILHITEC | −94.7% | −50.0% | 0.5 | combined action, one leg absent |
| 2024-04-04 | CUPID | −94.8% | −50.0% | 0.5 | combined action, one leg absent |
| 2010-07-29 | MMTC | −93.9% | −50.0% | 0.5 | combined action, one leg absent |
| 2023-06-05 | HARDWYN | −91.8% | −25.0% | 0.75 | combined action, one leg absent |
| 2016-08-11 | KTIL | −50.9% | −3.8% | 0.9615 | a −51% move "explained" by a 3.8% bonus |

This is exactly the failure mode Round 1's F2 was meant to eliminate, now hidden behind a
green label. TITAN's pre-2011 adjusted prices are wrong by 10×, and the audit counts it
toward the CA-explained total. Note the gap detector *cannot* catch these: a combined
bonus+split gap does not snap to an integer split ratio (TITAN's 18.9× fails the 15%
cluster tolerance), so C1's method is structurally blind to precisely the events C3 exposes.

**Fix:** require magnitude agreement — `|ret − (factor − 1)| ≤ tol` — to label a move
CA-explained. Every move that matches on direction but not magnitude is an *incomplete
adjustment* and must be reported in its own bucket. That bucket is the real acceptance test
for split coverage.

### H1 — HIGH — §2's assertion is mathematically wrong; the 4 FAILs are spurious

**This one is mine.** Round 1's F5 specified `assert adj_before ≈ raw_after`. That is only
valid for a symbol's *most recent* event. `adj_before` carries the product of **all** future
factors; `raw_after` carries none. For RELIANCE's 2017 bonus, adj_before = 1,645.40 × 0.5
(2017) × 0.5 (2024) = 411.35 while raw_after = 818.10 — a correct adjustment that the
assertion calls a FAIL. Reading the table confirms the pattern exactly: only each symbol's
newest event passes (RELIANCE 2024 ✓, 2017 ✗; INFY 2018 ✓, 2015 ✗, 2014 ✗).

DeepSeek implemented the specification faithfully. The 4 reported FAILs are artifacts of my
brief, not data defects, and the commit correctly declined to "fix" the data. It should,
however, have flagged the contradiction rather than shipping a self-refuting table.

**Fix:** assert in a single space — `adj_before ≈ adj_after` (adjusted close either side of
the ex-date, which must be continuous up to the day's genuine return), or equivalently
`adj_before ≈ raw_after × cum_factor(t)`.

### H2 — HIGH — the Match column renders the literal `{match}`

`audit_corporate_actions.py:157-160` builds the row by `+` concatenation; the final fragment
`" | {match} |"` is a plain string, not an f-string. Every row of §2 prints `{match}`. The
per-event PASS/FAIL column — R3's headline deliverable — does not exist in the artifact, and
the PASS/FAIL counts underneath it come from a variable the table never displays.

### H3 — HIGH — the sidecar CSV is unclassified; the 4,312 failing moves are unauditable

`CSMP_GATE_B_MOVES.csv` is written at line 212, *before* the classification loop at line 228.
Its `class` and `detail` columns are empty for all 5,609 rows (verified: 0 populated). The MD
prints only 20 samples per bucket. So no artifact anywhere records which moves are the 4,312
dev-window "genuine" rows that are the sole stated reason for the NOT PASSED verdict. R9's
purpose — make the move table reviewable — is unmet. Move the CSV write below the loop and
emit `wnd`, `cls`, `detail`.

### M1 — MEDIUM — ETF splits double-inserted; the AMC citations are silently discarded

`ingest_splits_from_bhavcopy()` runs first with a plain `INSERT`; the gap rule already detects
the large ETF steps. `ingest_etf_splits()` then plain-`INSERT`s into `corporate_actions`
(no PK → duplicate event rows) and `INSERT OR IGNORE`s into `adjustment_factors` (PK
collision → dropped). Verified: `GOLDBEES` factor carries `source =
'bhavcopy_gap_2019-12-19_GOLDBEES'`, not the AMC notice. The curated citation — the entire
justification for the patch list — never reaches the factor table for gap-detected symbols.
This is the origin of the unexplained 114 events vs 112 factors. Ingest the curated list
*first*, and let it win.

Separately, 2 of the 9 ETF entries cite only `"AMC notice; sealed-window counterpart"` with
no price evidence, and 6 more give approximate closes (`"~3398->~34"`). Only GOLDBEES carries
verifiable figures. That is thin for a store described as "traceable."

### M2 — MEDIUM — special-dividend detection fails silently

`ingest_special_dividends()` does `float(amt_str)` on `ratio_or_fv`, which for `Table2` rows
is the free-text `Details` field. Non-numeric values hit `except ValueError: continue` with
no counter, as does `if amt >= P: continue`. 11 factors emerged from 10,771 dividend events
and there is no way to tell how many were skipped for parse failure versus threshold. Count
and report both rejection reasons; a silent `continue` in an ingest path is how Round 1's
defects survived to production.

### M3 — MEDIUM — "hand-verified" covers 4 symbols, not the 11 listed

The collection loop at lines 118–128 breaks once `len(events) >= 12`, and each symbol
contributes 3 events. It therefore always stops after RELIANCE, TCS, INFY, HDFCBANK
(+ WIPRO/ITC only because some have < 3 factors). The `sample_syms` list advertises 11
symbols including BEL, BPCL, BHARATFORG, HINDZINC, OIL — none are ever tested. Sample per
symbol, not per event.

### L1 — LOW — R9's "dead code removed" is not satisfied

`ingest_corporate_actions.py` still imports and defines an unused HTTP stack — `requests`,
`HTTPAdapter`, `Retry`, `time`, `timedelta`, and the whole `get_session()` / `SESSION`
machinery — although the module's docstring states "No re-download needed." It also opens a
second DuckDB connection `con2` to a file `con` already holds, for no reason.
`audit_corporate_actions.py:243-247` computes `dev_residue`, never uses it, and carries a
comment conceding the definition is wrong. The `factor > 1.0` branch of the classifier
(line 237) is unreachable — every factor in the store is < 1. The comment at line 465
("rebuild the adjusted view (dropped by purge)") is false; `DELETE` does not drop a view.

### L2 — LOW — the commit message overstates the result

*"Structural ingest fixes complete"* and *"NOT PASSED (4312 dev-window genuine large moves —
honest market volatility, not CA artifacts)"* are both contradicted by the report generated
in the same commit, which lists 22 continuity mismatches and 4 hand-verify failures in its
own fit-for-purpose block. A gate verdict must name every failing criterion, including the
ones the implementer believes are cosmetic.

---

## Path to PASS

1. **Do not ship the gap-inferred splits (C1).** Obtain a real split source (NSE CF-CA
   archive, or BSE `corporates_act.html` with the subdivision purpose filter). Purge all 105
   `bhavcopy_gap_*` factors. Use price gaps only to snap an ex-date to a sourced event.
2. **Fix the view's `prev_close` scaling (C2)** and re-run §4. Acceptance: 0 mismatches
   across the 20 continuity symbols.
3. **Add magnitude agreement to the classifier (C3).** Report direction-match /
   magnitude-mismatch as its own bucket. Acceptance: that bucket is empty — it is the
   only honest test that split coverage is complete.
4. **Correct §2's assertion (H1)** to compare within adjusted space, and fix the `{match}`
   f-string (H2). Re-run; expect all events to PASS on the current (correct) bonus factors.
5. **Write the sidecar after classification (H3)**; ingest the curated ETF list before the
   gap pass (M1); count and report silent rejections (M2); sample per symbol (M3).
6. Only then is the dev-window residue a meaningful number. Round 1 predicted the residue
   would decompose into ETF splits, special dividends, and screen artifacts. The current
   4,312 cannot be assessed at all, because H3 means no one can see which rows they are.

Per the role split, remediation is DeepSeek's; this document is the review of record for
commit `49409e0`. Round 1's review (`CSMP_GATE_B_LEAD_REVIEW.md`) remains the record for the
preceding deliverable and is superseded only in its F5 fix instruction, which was wrong (H1).
