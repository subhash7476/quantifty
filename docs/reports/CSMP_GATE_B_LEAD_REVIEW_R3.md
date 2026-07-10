# CSMP Gate (b) — Lead-Reviewer Verdict, Round 3 (post CF-CA split swap)

**Reviewer:** Claude (Lead Reviewer, per `CSMP_PHASE0_CHARTER.md` role split)
**Implementer:** DeepSeek V4 (commit `ec0e836` — "swap bhavcopy-gap splits for NSE CF-CA primary source")
**Date:** 2026-07-10
**Supersedes:** `CSMP_GATE_B_LEAD_REVIEW_R2.md` (commit `49409e0`) for finding C1 only.

**Deliverables reviewed:** `scripts/csmp/ingest_corporate_actions.py`,
`scripts/csmp/audit_corporate_actions.py`, `docs/reports/CSMP_GATE_B_CORPORATE_ACTIONS_AUDIT.md`,
`docs/reports/CSMP_GATE_B_MOVES.csv`, tables `corporate_actions` / `adjustment_factors`,
view `equity_bhavcopy_adjusted`.

---

## Verdict: **NOT PASSED — REJECTED**

R2's **C1 is fixed at the source layer and only there.** Every SPLIT factor now traces to an
exchange document: 583 of 592 to `NSE_CF-CA_*`, 9 to the ETF patch list, **zero to
`bhavcopy_gap_*`**. The circular-inference defect is genuinely gone, the penny-stock tick
"splits" are gone, and `VISESHINFO`'s six fabricated splits are gone. That was the right fix
and it was executed.

But the commit stopped there. **`audit_corporate_actions.py` was not touched by `ec0e836`**
(`git log` on that path ends at `49409e0`). Every audit-side finding from R2 — C2, C3, H1,
H2, H3, M2, M3, L1 — survives untouched into this round, and the generated report proves it:
the Match column still prints the literal `{match}`, the sidecar CSV's `class` column is still
empty on all 5,609 rows, and §4 now reports **31** continuity mismatches (up from 22, because
there are more splits to be wrong about).

Worse, the new primary source introduced a defect of its own. Sourcing the *event* correctly
does not mean deriving the *factor* correctly. The parser reads face values by regex-scanning
free text, and it is wrong on **42 of the 544 splits that have price evidence (7.7%)** — nine
of them by more than 2×, one with the sign inverted, one silently reduced to a no-op.

**Quarantine stands and is extended.** `equity_bhavcopy_adjusted` and all
`action_type='SPLIT'` rows of `adjustment_factors` must not be used downstream. The gate-(a)
raw store remains sound and unaffected.

---

## Round-2 findings — disposition

| R2 | Finding | Status after `ec0e836` |
|----|---------|------------------------|
| C1 | Split source is circular | **FIXED at source** — 0 `bhavcopy_gap_*` factors remain. Replaced by a new *derivation* defect (see D1) |
| C2 | `adjusted.prev_close` wrong on every ex-date row | **NOT FIXED** — view line 428 unchanged; §4 now reports 31 mismatches |
| C3 | Direction-only matching masks missing legs | **NOT FIXED** — classifier line 237 unchanged; now masks D1 as well |
| H1 | §2 assertion mathematically wrong | **NOT FIXED** — 5 spurious FAILs reported as gate failures |
| H2 | Match column renders literal `{match}` | **NOT FIXED** — line 160 still a plain string |
| H3 | Sidecar CSV unclassified | **NOT FIXED** — CSV written line 212, classified line 228; 0 of 5,609 rows populated |
| M1 | ETF splits double-inserted / citations discarded | **FIXED incidentally** (gap pass deleted). New problem: 2 of 9 ETF factors are numerically wrong (see D3) |
| M2 | Special-dividend detection fails silently | **NOT FIXED** |
| M3 | Hand-verify covers 4 symbols, not 11 | **NOT FIXED** |
| L1 | Dead code | **NOT FIXED** — `requests` / `HTTPAdapter` / `Retry` / `get_session()` / `SESSION` still imported and defined in an ingest that reads only local CSVs; `dev_residue` still computed and unused |

---

## Verification performed by the reviewer

All numbers re-derived read-only from `equity_bhavcopy.duckdb` this session.

| Check | Result |
|-------|--------|
| SPLIT factor provenance | 583 `NSE_CF-CA_*`, 9 `ETF_AMC_notice_*`, **0 `bhavcopy_gap_*`** ✓ |
| SPLIT factors with `factor > 1` (consolidations) | **0** — yet the store contains at least one true consolidation |
| SPLIT factors with `factor = 1.0` (no-op) | **1** (`DWARKESH` 2017-08-10) |
| Splits with usable ex-date price evidence | 544 of 592 |
| Stored factor vs observed raw ex-date gap, deviation > 15% | **42 of 544 (7.7%)** |
| …of those, off by more than 2× | **9** |
| ETF patch-list factors vs observed gap | 7 of 9 agree; `QGOLDHALF` off 2×, `AXISGOLD` off 20% |
| Sidecar CSV rows with a populated `class` column | **0 of 5,609** (unchanged) |
| `audit_corporate_actions.py` touched by `ec0e836` | **No** — last change `49409e0` |
| Bonus leg present within ±30d of a combined-action split | `ONGC`, `HINDZINC`, `TITAN` ✓ (offset 0); `STER`, `DPSCLTD`, `EMAMILTD` **absent** |

---

## Findings

### D1 — CRITICAL — the CF-CA factor is derived by regex-scanning free text; 7.7% are wrong

`parse_nse_cf_ca_splits()` (lines 129–141) extracts **every** integer in the purpose string
and then guesses which two are the face values:

```python
nums = [int(s) for s in re.findall(r"\d+", purpose)]
for i in range(len(nums) - 1):
    if nums[i] >= 10 and nums[i + 1] <= nums[i]:
        old_fv, new_fv = nums[i], nums[i + 1]
        break
if old_fv is None and nums[-2] >= 10: old_fv, new_fv = nums[-2], nums[-1]
if old_fv is None:
    old_fv = max(nums); new_fv = min(n for n in nums if n != old_fv)
```

The purpose text is not a face-value field. It carries bonus ratios, dividend amounts, and
prose. Three failure modes, all present in the store:

**(a) A neighbouring number is captured instead of the face value.**

| Symbol | Ex-date | Purpose | Stored | Truth | Observed gap |
|--------|---------|---------|-------:|------:|-------------:|
| DPSCLTD | 2011-12-15 | `Bonus 22:1 And Face Value Split From Rs.10/- To Re.1/-` | 0.0455 (=1/22) | 0.1 | 0.0048 |
| KCP | 2010-09-02 | `1st Interim Dividend Rs.2.50 … Split From Rs.10/- To Re.1/-` | 0.2 | 0.1 | 0.1016 |
| EMAMILTD | 2010-07-21 | `Dividend Rs.6/- … Split From Rs.2/- To Re.1/-` | 0.1667 (=1/6) | 0.5 | 0.4905 |
| STLTECH | 2010-03-09 | `Bon 1:1/Fv Spl Rs.5tors.2` | 0.2 | 0.4 | — |

`DPSCLTD` picks the bonus ratio; `KCP` and `EMAMILTD` pick the dividend amount. The
decimal-blind `\d+` regex is why: `Rs.2.50` yields `[2, 50]`.

**(b) Consolidations get an inverted factor.** The `nums[i] >= 10 and nums[i+1] <= nums[i]`
rule can only ever return `new_fv <= old_fv`, so `factor <= 1` by construction. A reverse
split is unrepresentable:

| Symbol | Ex-date | Purpose | Stored | Truth |
|--------|---------|---------|-------:|------:|
| VERTOZ | 2025-06-25 | `Consolidation Of Equity Shares From Re 1 … To Rs 10 …` | 0.1 | **10.0** (observed gap 9.4995) |

VERTOZ's entire pre-2025 adjusted history is wrong by **95×**, and because the factor is
`< 1` while the move is `+850%`, §3's direction test does not even flag it.

**(c) A degenerate `old_fv == new_fv` becomes a silent no-op.**
`DWARKESH` 2017-08-10 — `…Dividend - Rs 10 Per Share/Face Value Split (Sub-Division) - From
Rs 10/- Per Share To Re 1/- Per Share` — yields `nums[0]=10, nums[1]=10` → **factor 1.0**,
stored and applied. Observed gap: 0.0996. A 10× error that the store records as "adjusted."

**Fix:** parse the face values from the *face-value clause*, not the whole string — a decimal-
aware anchored pattern (`(?:Rs|Re)\.?\s*([\d.]+)\s*(?:/-)?\s*(?:Per Share)?\s*To\s*(?:Rs|Re)\.?\s*([\d.]+)`)
applied to the `Fv Splt|Face Value Split|Sub-Division|Consolidation` clause only. Allow
`factor > 1` for consolidations. **Reject, do not guess**, when no clause parses or when
`old_fv == new_fv`: emit the row to a rejects table with the purpose text and a count.
`ec0e836` reduced 112 unsourced splits to 0; it must not now ship 42 mis-derived ones.

**Acceptance test (this is the one that matters):** for every split with price evidence,
`|stored_factor − close(ex)/close(ex−1)| / implied ≤ 0.15` after compounding all legs at that
ex-date. Today: 42 violations. Required: 0, or an explicit, itemised, individually justified
exception list.

### D2 — CRITICAL — R2/C2 is unfixed and the audit measures it as a gate failure

`equity_bhavcopy_adjusted` line 428 still scales `prev_close(t)` by `cum_price_factor(t)`.
`prev_close(t)` is `close(t−1)`, whose correct cumulative factor additionally includes the
event at `t`. Raw bhavcopy `prev_close` is unadjusted, so nothing compensates:
`adj_prev_close(t) = adj_close(t−1) / F_t`.

§4 measures this precisely and reports **31 mismatches** across the 20 continuity symbols
(RELIANCE 822.70 vs 411.35; KOTAKBANK 2132.60 vs 426.52 — a 5× split; ASIANPAINT 5118.20 vs
511.82 — 10×). The count rose from 22 to 31 purely because more splits now exist. The fix
was specified in R2 step 2 and not attempted.

Any downstream return computed as `close/prev_close` from this view is wrong on every ex-date
— which is precisely the day a momentum signal must not be wrong.

**Fix:** join `prev_close` against the cumulative factor of the *previous* trading row.
Acceptance: §4 reads 0.

### D3 — CRITICAL — direction-only matching now masks D1 and the ETF errors

§3 labels a move CA-explained on `factor < 1 and ret < 0` — any magnitude, within 7 days
(line 237). It never asks whether the factor *accounts for* the move. Consequently:

- All 42 mis-derived factors from D1 land in the **CA-explained** bucket. `DPSCLTD` −99.5% is
  "explained" by a factor implying −95.5%. `RESURGERE` −95.9% is "explained" by 0.1 (−90%),
  its true gap being 0.0406.
- `QGOLDHALF` 2021-12-16: patch list says 100:1 (factor 0.01); the observed gap is 0.0202 —
  a **1:50** unit split. Reported CA-explained. `AXISGOLD` 2020-07-23: factor 0.01, observed
  0.0120 — 20% off, and gold does not move 20% in a session. Both ETF entries cite only
  "AMC notice" with no figures; both are wrong or unverified.
- `VERTOZ` 2025-06-25 (D1b) is a **+850%** move with a `factor < 1`. Direction disagrees, so
  it is not even CA-explained — it sits in the "genuine" bucket, in the sealed window,
  as a 9.5× data error labelled market behaviour.

**Fix (unchanged from R2/C3):** require magnitude agreement to label a move CA-explained.
Report direction-match / magnitude-mismatch as its own bucket. That bucket, not the
dev-window residue, is the real acceptance test for split coverage — and today it would
contain at least 42 rows.

### D4 — HIGH — combined bonus+split actions still lose the bonus leg

R2/F6 ("bonuses keyed on `BCRD_FROM`, the record date, not the ex-date") was marked PARTIAL
and remains so. Where the BSE record date coincides with the NSE ex-date the legs compound
correctly (`ONGC`, `HINDZINC`, `TITAN` — all offset 0, all now correct). Where the bonus is
absent from the BSE feed entirely, the split factor alone under-adjusts:

| Symbol | Ex-date | Action | Legs found | Product | Observed gap |
|--------|---------|--------|-----------:|--------:|-------------:|
| STER | 2010-06-21 | Bonus 1:1 + FV 2→1 | 1 | 0.5 | 0.2696 |
| EMAMILTD | 2010-07-21 | Div + FV 2→1 | 1 | 0.1667 | 0.4905 |
| DPSCLTD | 2011-12-15 | Bonus 22:1 + FV 10→1 | 1 | 0.0455 | 0.0048 |

The NSE CF-CA purpose text *names the bonus* in each case. It is being discarded: the parser
extracts a split from the string and drops the `Bon 1:1` it just read past. Parse both legs
from the same record and insert both.

### H1 — HIGH — §2's assertion is still mathematically wrong; the 5 FAILs are still spurious

Unchanged from R2/H1, and it was **my** specification error. `assert adj_before ≈ raw_after`
holds only for a symbol's most recent event: `adj_before` carries the product of all future
factors, `raw_after` carries none. RELIANCE 2017 "FAIL" (411.35 vs 818.10) is a *correct*
adjustment. Only each symbol's newest event passes. The report's §6 nonetheless cites
"5 hand-verify assertion failure(s)" as a gate-failure reason.

**Fix:** assert `adj_before ≈ adj_after` (adjusted close either side of the ex-date, continuous
up to the day's genuine return), or `adj_before ≈ raw_after × cum_factor(t)`.

### H2 — HIGH — the Match column still renders the literal `{match}`

`audit_corporate_actions.py:157-160` builds the row by `+` concatenation and the final
fragment `" | {match} |"` is a plain string, not an f-string. Every row of §2 in the shipped
report prints `{match}`. The per-event PASS/FAIL column does not exist in the artifact.

### H3 — HIGH — the sidecar CSV is still unclassified

`CSMP_GATE_B_MOVES.csv` is written at line 212, before the classification loop at line 228.
Verified: `class` and `detail` empty on all 5,609 rows. The 4,141 dev-window "genuine" moves
— the sole stated reason for NOT PASSED — remain unauditable by anyone. Move the write below
the loop and emit `wnd`, `cls`, `detail`.

### M1 — MEDIUM — §3's "Detail" column prints the class, not the detail

Lines 271 and 277 emit `{c[4]}` under a `Detail` header; `c[4]` is the class. Every row of
both sample tables reads `CA-explained` or `genuine` — the factor, ex-date and gap computed
into `c[5]` are never shown. This is why §3 cannot be used to spot D1: the evidence is
computed and thrown away one column short.

### M2 — MEDIUM — special-dividend detection still fails silently

`ingest_special_dividends()` does `float(amt_str)` on `ratio_or_fv`, which for `Table2` rows
is the free-text `Details` field. `except ValueError: continue` and `if amt >= P: continue`
both drop rows with no counter. 11 factors from 10,771 dividend events, and no way to tell
parse failures from threshold rejections. Count and report both.

### M3 — MEDIUM — "hand-verified" still covers 5 symbols, not the 11 listed

The collection loop (lines 118–128) breaks at `len(events) >= 12` with 3 events per symbol,
so it always stops after RELIANCE, TCS, INFY, HDFCBANK (+WIPRO). `BEL`, `BPCL`, `BHARATFORG`,
`HINDZINC`, `OIL` are advertised in `sample_syms` and never tested. Sample per symbol.

Related: §4's "Ex-dates" column counts *factor rows*, not distinct dates — ONGC shows
`2011-02-08` twice because it has both a BONUS and a SPLIT factor on that date.

### L1 — LOW — dead code (unchanged)

`ingest_corporate_actions.py` imports `requests`, `HTTPAdapter`, `Retry`, `time`, `timedelta`
and defines `get_session()` / `SESSION`, none used — the module reads local CSVs only.
`audit_corporate_actions.py:243-247` computes `dev_residue`, never used, with a comment
conceding its definition is wrong. The `factor > 1.0` branch at line 237 is unreachable today
(0 factors > 1) — but per D1b it *should* be reachable, so fix the source rather than delete
the branch.

---

## Path to PASS

1. **Re-derive the split factors (D1).** Anchored, decimal-aware face-value parse of the
   FV clause only; allow `factor > 1`; reject-and-count rather than guess. Parse the bonus
   leg from the same purpose string (D4).
2. **Add the price-evidence regression test.** For every split with price evidence,
   compounded factors at the ex-date must match `close(ex)/close(ex−1)` within 15%.
   Acceptance: 0 violations, or an itemised exception list. This is the test that would have
   caught D1, D3 and D4 in one run, and it is the single most valuable thing to add.
3. **Verify the 9 ETF entries against price evidence (D3).** `QGOLDHALF` is 1:50, not 1:100.
   `AXISGOLD` does not reconcile. Cite figures for all nine or drop the symbol.
4. **Fix the view's `prev_close` scaling (D2)**; re-run §4. Acceptance: 0 mismatches.
5. **Add magnitude agreement to the classifier (D3)** and give direction-match /
   magnitude-mismatch its own bucket. Acceptance: empty.
6. **Correct §2's assertion (H1)**, fix the `{match}` f-string (H2), write the sidecar after
   classification (H3), print `c[5]` in the Detail column (M1), count silent rejections (M2),
   sample per symbol (M3), delete the dead HTTP stack (L1).
7. Only then is the dev-window residue (4,141) a meaningful number. It cannot be assessed at
   all today, because H3 means no one can see which rows it contains.

Per the role split, remediation is DeepSeek's; this document is the review of record for
commit `ec0e836`. `CSMP_GATE_B_LEAD_REVIEW_R2.md` remains the record for `49409e0`.

---

## Note on the price-evidence test vs. R2/C1

Using price gaps to *validate* a sourced factor is not the circularity R2 rejected. C1's sin
was using the gap to **establish that an action occurred**. Here the exchange establishes the
event and the ratio; the gap only checks the arithmetic. A split whose factor cannot be
reconciled against the market's own repricing is a parse bug, and the market is the only
witness available. That test is what separates D1 from a clean ingest, and its absence is why
`ec0e836` shipped believing the source swap had finished the job.
