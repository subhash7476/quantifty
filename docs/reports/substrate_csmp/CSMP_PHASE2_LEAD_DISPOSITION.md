# CSMP Phase 2 — Lead-Reviewer Disposition of the Independent Review

**Date:** 2026-07-12
**Author:** Claude (Lead Reviewer)
**Subject:** `CSMP_PHASE2_INDEPENDENT_REVIEW.md` — GPT-5 / Codex, verdict **PASS WITH REQUIRED REVISIONS** (F1 HIGH, F2 MEDIUM, F3 MEDIUM)
**Disposition:** **All three findings ACCEPTED.** Two of them land on my own work, and one of them falsifies a claim I wrote into three documents.

---

## 0. Seal integrity — verified independently, before anything else

The reviewer executed the scripts by placing a dev-truncated store at the hardcoded path and restoring the full store afterwards. That is a data-integrity event, and it outranks every finding, so I verified it first rather than accepting the report:

| Check | Required (gate (a) final PASS) | Observed |
|---|---|---|
| `equity_bhavcopy` rows | 7,030,920 | **7,030,920** ✓ |
| Date span | 2010-01-04 → 2026-07-09 | **2010-01-04 → 2026-07-09** ✓ |
| Symbols | 4,132 | **4,132** ✓ |
| Tables | 16 | **16, all present** ✓ |
| File mtime | — | **unchanged (Jul 10)** — moved aside and back, never rewritten |

**The full store is intact and the seal held.** The reviewer's truncated store carried 0 priced rows on/after 2023-01-01 in both `equity_bhavcopy` and `equity_bhavcopy_adjusted`.

*One disclosure the reviewer made and I endorse:* the truncated store retained **382 `adjustment_factors` rows with `ex_date` ≥ 2023-01-01**. These are bare multiplicative factors (`symbol, ex_date, factor, action_type, source`) — no prices, returns, or cash amounts. They leak *the existence and date of a corporate action* in the sealed window, not any price or return. Nothing in this review consumed them (the scripts are dev-fenced and assert it). It is immaterial here, and it is now on the record rather than discovered later. **For the Phase-6 handoff, the truncation should drop them too** unless byte-exact backward adjustment provably requires them.

---

## 1. The findings — all three verified at the source, not accepted on report

I re-derived each finding against the code rather than trusting the review.

### F1 (HIGH) — **CONFIRMED, and it is worse than the reviewer states**

The reviewer's claim: the written rule is *"coverage closest to nominal"*, but the printed table makes **`iid_perc`** closest on **two-sided coverage** (0.949, distance 0.001) while the ratified method is **Student-t** (0.957, distance 0.007). Student-t wins only on **one-sided Type-I** (0.049, distance 0.001, vs `iid_perc`'s 0.054, distance 0.004).

**Verified.** `scripts/csmp/phase1_ci_coverage.py:3-5` states the rule as *"closest to nominal, judged on COVERAGE, not narrowness"*, and line 131 prints *"Selection rule: coverage closest to nominal at n=42."* **The guardrail disambiguates coverage-vs-narrowness. It never names which calibration metric.** The rule is genuinely underspecified, exactly as claimed.

**What the reviewer did not say, and I must.** The operator memo insisted D-i be settled **first**, as a validity question, and D-ii (the tail) **second**, as a power question — that ordering was the memo's headline argument. But **"one-sided Type-I closeness" is a criterion that only exists once D-ii is decided.** At the moment D-i was applied, the only available reading of "coverage" was two-sided — under which the rule selects `iid_perc`, not Student-t. **The selection therefore used a criterion that the program's own stated sequencing had not yet unlocked.** That is a real ordering defect, and it is mine.

**Why it is still repairable, and not fatal:** the sealed window is untouched, so no disambiguation can be informed by the outcome. This is precisely the correction a pre-seal review exists to make.

### F2 (MEDIUM) — **CONFIRMED**

`dev_ic_series()` builds the IC population under `if p12 and p1 and pa and pb and p12 > 0 and pa > 0` — **a name with no `t+1` price (`pb`) is silently dropped.** That is *the same survivorship bug §5.2 was written to kill*, and which B1 fixed in the main analysis — still live in **the script that selects the gate**. The dossier asserts §5.2 is "binding on every forward return in the IC set"; the calibration code does not honour it.

Numerically small today (0.0458 vs the §5.2-correct 0.0457). **Small is not aligned** — and see §2: it is load-bearing for F1.

### F3 (MEDIUM) — **CONFIRMED. This one overturns my recommendation, which the operator ratified on my advice.**

I argued charter §6's Approval precondition is "an epistemic condition, not a risk gate — satisfied-in-substance by disclosure," because at PaperBroker scale there is no capital at risk.

**I modeled capital risk and nothing else.** The reviewer named what I did not: **anchoring, sunk cost, and the quiet promotion of a Not-Approved artifact into an operationally trusted one** as dashboards, reports, and engineering investment accumulate around it. That is a real cost, it is not zero, and "no capital at risk" does not answer it. **Changing what counts as satisfying a charter precondition is an amendment, and calling it a reframing made it sound cheaper than it is.**

The reviewer's fix is better governance than mine, and I endorse it: keep the engineering path, but record it as an **explicit charter amendment with controls** — (i) the post-Inconclusive consumer is **not** Phase-7 completion; (ii) it may never appear in Approved/Deployable language; (iii) it gets a separate exploratory runbook; (iv) its forward data may enter **only** a fresh pre-registration with frozen rules and fresh α.

---

## 2. The sequencing that matters: **F1 cannot be resolved on the current table**

`iid_perc`'s two-sided coverage sits **0.001** from nominal. That is knife-edge — and **F2 says the table it sits in was computed on the wrong IC series.** You do not ratify a frozen gate on a table you have just declared miscomputed.

**Therefore: fix F2 first, then resolve F1 on the corrected table.**

And resolve it the way a pre-registration should: **ratify the *rule*, not the *method*.** Name the disambiguated criterion, apply it mechanically to the corrected table, and **take whatever it selects** — including `iid_perc`, if that is what it selects. That is the only form of this decision that cannot be accused of picking the answer first.

**Falsifiable prediction, stated before the re-run** (house discipline — say what the numbers must show, then run): *the §5.2 correction shifts the dev IC population negligibly (0.0458 → ~0.0457); the selection does **not** flip; Student-t remains closest on one-sided Type-I.* **If it does flip, the frozen gate changes and the reviewer gets a confirmatory look at the corrected table** (not a full second cycle).

### Which criterion is right

**One-sided Type-I closeness — because the gate is one-sided.** Calibrate the statistic you actually use. Two-sided coverage is a property of an interval the program does not employ; it appears in the table only because D-i was written before D-ii in exposition. Three further supports:

1. **It is the independent reviewer's own primary fix** (*"rewrite D-i as a one-sided-gate calibration rule… then keep Student-t"*). Recommending Student-t here is me **concurring with the independent party**, not defending my prior.
2. **Student-t errs conservative (0.049 < 0.050); `iid_perc` errs liberal (0.054 > 0.050).** The entire D-i episode existed to remove an anti-conservative test. Selecting the liberal candidate would be incoherent with the program's own stated value.
3. **Theory agrees a priori.** Percentile bootstrap intervals are liberal at small n without studentization/BCa; Student-t on a mean is the textbook-correct interval. The choice is principled independent of the table.

**Guard against the "two plausible gates" attack** the reviewer names: pre-register **one** gate, and require the **other reading's bound to be reported as non-gating** at Phase 6, alongside the retired `mb_L12` arm. Both readings stay visible; neither can be silently chosen after the result is seen.

---

## 3. The claim I got wrong, in three documents — correct it, do not supplement it

The ratification record §1.2, `PROJECT_STATE.md`, and `CHANGELOG_PLATFORM.md` all carry:

> *"the rule selected **against power** (Student-t 0.398 vs stationary's 0.453) — the evidence the rule was not reverse-engineered."*

**Two things are wrong with that.** (i) The stationary bootstrap was **never** the rule's winner under either reading — the relevant foil is **`iid_perc`**, which my §1.2 table **omitted entirely**, and which has **higher power than Student-t (0.418 vs 0.398)** *and* is the literal two-sided winner. (ii) The line implies a clean, unambiguous selection. F1 shows the rule was underspecified. **I wrote a triumphant integrity line, and a sharper reader punctured it.**

**Honest replacement:**

> Student-t is the **lowest-power valid candidate** (0.398, vs `iid_perc` 0.418 and stationary 0.453) — chosen on **one-sided calibration for a one-sided gate**, not for power. The rule as first written was **underspecified** between the one-sided and two-sided readings (Phase-2 **F1**); under a literal two-sided reading it selects `iid_perc`. It was **disambiguated to one-sided pre-seal, on a corrected table, and disclosed** — not resolved after the fact.

The integrity signal survives — the selected method is still the lowest-power valid candidate — but it must be stated *accurately*, and the ambiguity disclosed rather than papered over. **This gets corrected before Rev 7 freezes it in.**

---

## 4. Verdict on the review, and the sequence

**The Phase-2 review is ACCEPTED in full.** It is a strong, genuinely independent piece of work: it re-derived every load-bearing number on the truncated store, confirmed the seal structurally, cleared D-ii / D-iii / the 41% finding / the construct on their merits, and found **two defects in the calibration path that two prior reviews missed** — one of them a survivorship bug of exactly the class this program has already been bitten by once.

**Scope of Rev 7 is exactly F1 + F2 + F3 + the §3 record correction. Nothing else reopens.** D-ii, D-iii, the power analysis, K=40, the cost model, and the decision table were examined and cleared; they are not in play.

| # | Step | Owner |
|---|---|---|
| 1 | **F2:** refactor `phase1_ci_coverage.py` onto the §5.2 `fwd()` convention; re-run; publish the corrected table | DeepSeek |
| 2 | **F1:** apply the ratified criterion **mechanically** to the corrected table; whatever it selects is the gate | DeepSeek |
| 3 | Operator ratifies the corrected D-i **wording**, and the **F3 charter amendment + 4 controls** | Operator |
| 4 | **§3 record correction** in the ratification record, PROJECT_STATE, CHANGELOG | Claude |
| 5 | **Rev 7 — FROZEN** | DeepSeek |
| 6 | Mechanical review of the Rev 7 diff — *or* a confirmatory look by the Phase-2 reviewer **if the F2 re-run flipped the selected method** | Claude / reviewer |

---

**This is the review working exactly as designed.** The dossier was deliberately *not* frozen before the independent read — and the independent read then caught a gate-definition ambiguity and a survivorship bug in the calibration script, **both pre-seal, both cheap to fix now, both expensive after.** Had the freeze landed first, as originally planned, neither would have had anywhere to go.

**The sealed window (2023-01 → 2026-06) has not been read.**
