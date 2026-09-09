# CSMP Gate (b) — Lead-Reviewer Verdict, Round 4

**Reviewer:** Claude (Lead Reviewer, per `CSMP_PHASE0_CHARTER.md` role split)
**Implementer:** DeepSeek V4 (commit `91e7963` — "hand-verify now tests per-event factor, not cumulative view")
**Date:** 2026-07-10
**Supersedes:** `CSMP_GATE_B_LEAD_REVIEW_R3.md` (commit `ec0e836`) for finding H1 only.

**Deliverables reviewed:** `scripts/csmp/ingest_corporate_actions.py`,
`scripts/csmp/audit_corporate_actions.py`, `docs/reports/CSMP_GATE_B_CORPORATE_ACTIONS_AUDIT.md`,
`docs/reports/CSMP_GATE_B_MOVES.csv`, tables `corporate_actions` / `adjustment_factors`,
view `equity_bhavcopy_adjusted`.

---

## Verdict: **NOT PASSED — REJECTED**

`91e7963` fixed exactly one finding — R3/H1 — and fixed it correctly. Nothing else moved.
`git log` on `scripts/csmp/ingest_corporate_actions.py` still ends at `ec0e836`; the commit's
23 inserted lines all fall inside the §2 hand-verify block of the audit script. D1, D2, D3, D4,
H2, H3, M1, M2, M3 and L1 survive verbatim into this round.

**The headline finding of this round is what the H1 fix reveals.** The new assertion is
`raw_before × factor ≈ raw_after` within 10%. That is precisely the price-evidence regression
test R3 asked for in step 2 of its Path to PASS — the single test named as "the one that
matters." It is now **in the file**, it is **correct**, and it is applied to twelve
hand-picked events belonging to five large-cap symbols with clean 1:1 bonuses. It passes
10 of 10 evaluable events.

Run the same assertion across every split in the store and it fails **70 times out of 542**.

The test exists. It is scoped to the symbols that cannot fail it. That is a worse state than
not having the test, because §6 now prints `Hand-verify assertions: 10 PASS / 0 FAIL` and a
reader takes it as evidence of factor correctness across the store.

**Quarantine stands.** `equity_bhavcopy_adjusted` and all `action_type='SPLIT'` rows of
`adjustment_factors` must not be used downstream. The gate-(a) raw store remains sound.

---

## Round-3 findings — disposition

| R3 | Finding | Status after `91e7963` |
|----|---------|------------------------|
| D1 | Split factor regex-scraped from free text; wrong on 7.7% | **NOT FIXED** — ingest untouched; count re-measured this round at 70/542 (see N1) |
| D2 | View scales `prev_close` by the wrong cumulative factor | **NOT FIXED** — line 428 unchanged; §4 still reports 31 |
| D3 | Direction-only matching masks D1 and the ETF errors | **NOT FIXED** — classifier line 244 unchanged |
| D4 | Combined bonus+split actions lose the bonus leg | **NOT FIXED** |
| H1 | §2 assertion mathematically wrong; 5 spurious FAILs | **FIXED** — now per-event, `raw_before × factor` vs `raw_after`. Correct. See N2 for the scoping defect it exposes |
| H2 | Match column renders literal `{match}` | **NOT FIXED** — line 164 is still a plain string concatenated onto an f-string |
| H3 | Sidecar CSV unclassified | **NOT FIXED** — written line 219, classified line 235; **0 of 5,609** rows populated |
| M1 | §3's "Detail" column prints the class, not the detail | **NOT FIXED** — lines 278/284 emit `c[4]`; `c[5]` is computed and discarded |
| M2 | Special-dividend detection fails silently | **NOT FIXED** |
| M3 | Hand-verify covers 5 symbols, not the 11 listed | **NOT FIXED** — loop still breaks at `len(events) >= 12` |
| L1 | Dead code | **NOT FIXED** — `requests` / `HTTPAdapter` / `Retry` / `time` / `timedelta` / `get_session()` / `SESSION` still present in an ingest that reads only local CSVs; `dev_residue` still computed and unused |

---

## Verification performed by the reviewer

All numbers re-derived read-only from `equity_bhavcopy.duckdb` this session.

| Check | Result |
|-------|--------|
| SPLIT factor provenance | 583 `NSE_CF-CA_*`, 9 `ETF_AMC_notice_*`, 0 `bhavcopy_gap_*` ✓ (C1 remains fixed) |
| SPLIT factors with `factor > 1` (consolidations) | **0** |
| SPLIT factors with `factor = 1.0` (no-op) | **1** (`DWARKESH` 2017-08-10) |
| Splits with usable ex-date price evidence | 542 |
| Compounded ex-date factor vs observed raw gap, deviation > 15% | **70 of 542 (12.9%)** |
| …of those, off by more than 2× | **17** |
| ETF patch-list factors vs observed gap | 7 of 9 agree; `QGOLDHALF` off 2×, `AXISGOLD` off 20% |
| Sidecar CSV rows with a populated `class` column | **0 of 5,609** |
| `ingest_corporate_actions.py` touched by `91e7963` | **No** — last change `ec0e836` |

Worst twelve by ratio:

| Symbol | Ex-date | Stored | Implied by price | Error |
|--------|---------|-------:|-----------------:|------:|
| VERTOZ | 2025-06-25 | 0.1000 | 7.2166 | 72.2× |
| DOLPHIN | 2024-01-25 | 0.1000 | 1.3396 | 13.4× |
| DWARKESH | 2017-08-10 | 1.0000 | 0.0996 | 10.0× |
| DPSCLTD | 2011-12-15 | 0.0455 | 0.0048 | 9.5× |
| RNBDENIMS | 2026-04-02 | 0.3333 | 0.0594 | 5.6× |
| VISESHINFO | 2013-01-03 | 0.1000 | 0.5352 | 5.4× |
| ATLASCYCLE | 2017-10-30 | 0.5000 | 0.1268 | 3.9× |
| KSHITIJPOL | 2022-10-27 | 0.2000 | 0.5966 | 3.0× |
| EMAMILTD | 2010-07-21 | 0.1667 | 0.4905 | 2.9× |
| SHRENIK | 2020-10-08 | 0.5000 | 0.1830 | 2.7× |
| MINDACORP | 2015-01-05 | 0.2000 | 0.5229 | 2.6× |
| RESURGERE | 2010-09-15 | 0.1000 | 0.0406 | 2.5× |

Seven of these twelve (`DOLPHIN`, `RNBDENIMS`, `VISESHINFO` 2013, `ATLASCYCLE`, `KSHITIJPOL`,
`SHRENIK`, `MINDACORP`) do not appear anywhere in R3. R3's enumeration was not exhaustive and
must not be treated as the fix list.

**Caveat, stated plainly:** a minority of these implied gaps may themselves be contaminated —
a thin BE-series print, a stock that gapped on news the same session. The test is a screen, not
an oracle. That is why the acceptance criterion below is "0 violations **or** an itemised,
individually justified exception list," and not "0 violations."

---

## Findings

### N1 — CRITICAL — the acceptance metric is not in the code, so no two rounds measure the same thing

R3 measured 42 violations out of 544 splits with evidence. I measure **70 out of 542**. Both
numbers are honest. They differ because the metric was never written down as code: R3 compared
the stored SPLIT factor; I compounded every factor sharing that symbol and ex-date (the quantity
the view actually applies) before comparing. Neither definition lives in
`audit_corporate_actions.py`, so each round re-invents it in throwaway SQL and gets a different
answer.

The Phase-0 charter requires the gate artifact to be **reproducible on re-run**. The audit
report says so in its own subtitle. Today the number that decides the gate cannot be reproduced
from the repository at all — it exists only in two reviewers' scratch sessions, and it disagrees
with itself.

**Fix:** the price-evidence test must be a section of `audit_corporate_actions.py`, emitting a
count and a full violation table into the report. Definition to codify: for each `(symbol,
ex_date)` carrying at least one SPLIT factor, let `F = Π factor` over all factors at that
`(symbol, ex_date)`, and let `implied = close(first EQ session ≥ ex) / close(last EQ session <
ex)`. Violation iff `|F − implied| / implied > 0.15`. Acceptance: 0, or an itemised exception
list carried in the repository.

Until this lands, **no reported figure for D1 is trustworthy**, including mine.

### N2 — CRITICAL — the H1 fix is correct and is scoped to the events that cannot fail it

`audit_corporate_actions.py:150-160` now computes `adj_bef = r_bef * fac` and asserts it within
10% of `r_aft`. That is the right assertion. But the event set it runs on is chosen by the
collection loop at lines 121-132, which breaks at `len(events) >= 12` after taking three events
each from `RELIANCE`, `TCS`, `INFY`, `HDFCBANK` — five symbols whose every factor is a 1:1 bonus
or a clean face-value split, plus one `WIPRO` bonus. `BEL`, `BPCL`, `BHARATFORG`, `HINDZINC`
and `OIL` are advertised in `sample_syms` and never reached (this is R3/M3, still open).

The consequence is not merely thin coverage. §6 of the shipped report prints
`Hand-verify assertions: 10 PASS / 0 FAIL` directly above the gate verdict, and `verified_fail`
is one of the three conditions in the `fail` list at lines 361-368. A reader — or a future
gate-(c) author — reasonably concludes that factor derivation has been verified. It has been
verified on the 2.2% of the store guaranteed to pass.

**Fix:** delete the twelve-event cap. Run the assertion over every split with price evidence.
This is the same change as N1 — N2 is what happens if you fix M3 without fixing N1: you get a
slightly larger sample of the same false assurance.

Related: the commit message for `91e7963` states "All 12 events PASS (was 5 PASS / 5 FAIL)."
The report says 10 PASS, 0 FAIL. Two of the twelve (`RELIANCE` 2009-11-26, `TCS` 2009-06-16)
have no prior close in the store, render as `—`, and are counted in neither column. The commit
message overstates by two.

### N3 — HIGH — `Adj before` now names two different quantities in one document

After `91e7963`, §2's `Adj before` column is `raw_before × factor` — a per-event quantity.
§4's `adj_before` is a close read from `equity_bhavcopy_adjusted` — a cumulative quantity. The
report uses the same label for both, in adjacent sections, with no note.

`RELIANCE` 2017-09-07 appears as `Adj before = 822.70` in §2 and `adj_before = 411.35` in §4.
Both are correct under their own definition. A reader comparing the two sections concludes the
report contradicts itself, or — worse — that one of them is the bug, and stops reading.

**Fix:** rename §2's column to `raw_before × factor` and §4's to `adj_close(t−1)`. Neither is
"adj before."

### D1 — CRITICAL — carried forward from R3, unchanged

`parse_nse_cf_ca_splits()` lines 129-141 still extract every integer from the purpose string
with a decimal-blind `\d+` and guess which two are face values. Three failure modes, all still
present and all confirmed above: a neighbouring number captured instead of the face value
(`DPSCLTD` takes the bonus ratio, `EMAMILTD` takes the dividend amount); consolidations
inverted, since `nums[i] >= 10 and nums[i+1] <= nums[i]` can only return `new_fv <= old_fv`
(`VERTOZ`, stored 0.1, truth 10.0); and degenerate `old_fv == new_fv` silently stored as
factor 1.0 (`DWARKESH`).

See R3 §D1 for the full analysis and the proposed anchored, decimal-aware parse. Nothing has
changed. Add to the R3 fix list: reject-and-count is mandatory, not optional — `DOLPHIN`'s
implied 1.34 and `RNBDENIMS`'s implied 0.059 against a stored 0.333 are not near-misses of a
face-value parse, they are records the parser should have refused.

### D2 — CRITICAL — carried forward from R3, unchanged

`equity_bhavcopy_adjusted` line 428 still scales `prev_close(t)` by `cum_price_factor(t)`.
The correct cumulative factor for `close(t−1)` additionally includes the event at `t`, and raw
bhavcopy `prev_close` is unadjusted, so nothing compensates. §4 reports **31** mismatches.
Any return computed as `close/prev_close` from this view is wrong on every ex-date.

### D3 — CRITICAL — carried forward from R3, unchanged

Line 244 still labels a move CA-explained on direction agreement alone, at any magnitude,
within 7 days. All 70 mis-derived factors land in the CA-explained bucket. `VERTOZ` 2025-06-25
is a `factor < 1` against a **+622%** implied move, so direction disagrees and it is filed as
`genuine` — a 72× data error recorded as market behaviour.

### D4 — HIGH — carried forward from R3, unchanged

The NSE CF-CA purpose text names the bonus in `STER`, `EMAMILTD` and `DPSCLTD`; the parser reads
past it and emits only the split leg.

### H2, H3, M1, M2, M3, L1 — carried forward from R3, unchanged

Verified individually against the current source this round. `{match}` still prints literally in
all twelve rows of §2 — so the per-event PASS/FAIL that `91e7963` was written to produce **does
not appear in the artifact it ships**. The count in the summary line is the only evidence the
assertion ran.

---

## Path to PASS

The R3 path stands. One item is promoted to the top, and one is added.

1. **Codify the price-evidence test in `audit_corporate_actions.py` (N1).** Definition as
   specified above. Emit the full violation table, not a count. Do this *first* — it is the
   instrument by which every other split fix is measured, and until it exists no one, reviewer
   or implementer, can tell whether a change helped.
2. **Un-scope the hand-verify (N2, M3).** Delete the twelve-event cap; the assertion is already
   correct. Steps 1 and 2 are the same code.
3. **Re-derive the split factors (D1).** Anchored, decimal-aware face-value parse of the FV
   clause only; allow `factor > 1`; reject-and-count rather than guess. Parse the bonus leg from
   the same purpose string (D4).
4. **Verify the 9 ETF entries against price evidence (D3).** `QGOLDHALF` is 1:50, not 1:100.
   `AXISGOLD` does not reconcile. Cite figures for all nine or drop the symbol.
5. **Fix the view's `prev_close` scaling (D2)**; re-run §4. Acceptance: 0 mismatches.
6. **Add magnitude agreement to the classifier (D3).** Give direction-match / magnitude-mismatch
   its own bucket. Acceptance: empty.
7. **Report hygiene:** fix the `{match}` f-string (H2), write the sidecar after classification
   (H3), print `c[5]` in the Detail column (M1), disambiguate the `Adj before` label (N3), count
   silent rejections (M2), delete the dead HTTP stack (L1).
8. Only then is the dev-window residue (4,141) a meaningful number.

Per the role split, remediation is DeepSeek's; this document is the review of record for
commit `91e7963`. `CSMP_GATE_B_LEAD_REVIEW_R3.md` remains the record for `ec0e836`.

---

## Note to the implementer

`91e7963` did the hardest correct thing in this whole gate — it wrote the assertion that
compares a derived factor against the market's own repricing — and then pointed it at twelve
events that were never in doubt. The assertion is right. Aim it at the other 530.
