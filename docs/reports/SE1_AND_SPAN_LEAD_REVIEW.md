# Lead Review — SPAN Ingest Activation (Part A) + SE-1 Counting Pass (Part B)

**Date:** 2026-08-04
**Reviewer role:** research lead (review only)
**Under review:** `SPAN_INGEST_ACTIVATION_REPORT.md`, `SE1_EVENT_COUNTING_REPORT.md`
**Prompt:** `SE1_COUNTING_PASS_AND_SPAN_INGEST_PROMPT.md`

---

## Verdict

| Part | Verdict |
|---|---|
| **Part A — SPAN ingest** | **ACCEPT WITH ONE CRITICAL CORRECTION.** The build is sound; §6's backfill claim is falsified and the correction is worth more than the original task. |
| **Part B — SE-1 counting** | **ACCEPT.** No defects found. The pass did exactly what it was built to do, including producing the result that damages the ranking that commissioned it. |

Both parts honoured the discipline that matters most: **the two failed predictions (A-P4, B-P5) were reported as failures and acted on, not smoothed.** A-P4's failure is what redirected the job to the `.s` settlement file; without it the 2028 panel would have been silently intraday.

---

# CRITICAL-1 — §6 "No historical backfill is possible" is falsified

## The internal contradiction

`SPAN_INGEST_ACTIVATION_REPORT.md` contains both of these:

- **§1.1 step 5:** a direct GET on `.../fno/31-07-2026/nsccl.20260731.s.zip` returned **HTTP 200** on 2026-08-04 — a date **four days old**, and one not in the SPA listing.
- **§6:** *"the `archive.nseclearing.in` market-reports surface retains a short window (current + previous day by design)."*

The evidence in §1.1 already contradicts §6. The listing shows two days; the **date-path URL served a fourth-day-old file**. §6 generalised from what the SPA *listed* to what the host *serves*, and those are different questions.

This is the pitfall register's own case, restated: recording absence as a fact about the world without having probed for it. It is the same shape as the 46 downloadable NSE sessions recorded as permanent archive gaps.

## Measured retention — lead probe, 2026-08-04

Ranged GETs against the implementer's own confirmed template, browser UA, `%{http_code}`:

| Date probed | Result |
|---|---|
| 2026-07-28 | **206** (served) |
| 2026-07-03 | **206** |
| 2026-02-03 | **206** |
| 2025-08-04 | **206** |
| 2025-07-01 | **206** |
| 2025-05-05 | 404 |
| 2025-03-03 | 404 |
| 2025-01-06 | 404 |
| 2024-11-04 / 2024-10-01 / 2024-09-02 / 2024-08-05 | 404 |
| 2023-08-04 / 2020-08-04 / 2016-08-04 | 404 |

All probed dates are trading days, so the 404s are genuine absence, not weekend artifacts.

**Retention is a rolling window of roughly 14 months**, with the boundary between **2025-05-05 (absent)** and **2025-07-01 (served)** — not "current + previous day."

## What this is worth

**Roughly 280 trading sessions of end-of-day settlement SPAN files are retrievable right now**, and the report says they are not.

It is a **decaying asset**. The daily job now protects the leading edge, but the trailing edge drops off at approximately one session per day. Every day of delay is one session lost permanently — the exact cost structure §6 correctly identified and then mislocated.

## Required actions

1. **Correct §6.** Replace the retention claim with the measured window and the probe evidence. State the boundary as bracketed (2025-05-05 → 2025-07-01), not as a point, unless walked precisely.
2. **Run the backfill immediately.** Highest-urgency item outstanding on the platform, because it is the only one losing value hourly. Reuse the repaired path; the settlement-flag assertion and raw-first retention already apply unchanged.
3. **Determine the exact boundary by walking backward** during the backfill rather than by a separate bisect — the walk has to happen anyway.
4. **Apply A.4-6 discipline in the backfill.** A 404 on a past trading day inside the window is a real miss and may be cached; a 404 outside the window is the retention edge and must be recorded as *retention boundary*, not as *source gap*. Do not let the two collapse into one label.
5. **Audit the sibling ingests for the same claim.** The futures and options ingests are recorded in CLAUDE.md as **unaudited** for the miss-cache pattern. This finding raises the prior that a "the source doesn't have it" claim elsewhere is also an unprobed assumption.

## What it does *not* change

**SE-5 is not unblocked.** Fourteen months is not a research panel for a margin-shock event study, and the clustering hazard that just fired on SE-1 applies with more force here — a volatility spike changes scanning ranges across every contract simultaneously, so nominal contract-events will vastly exceed effective ones.

What the backfill *does* buy is the ability to **probe the observation structure now instead of discovering it in 2028**: event frequency, cross-contract clustering, and an `N_eff` estimate. That is precisely the lesson SE-1 just taught at a cost of one script. Do not let the backfill become a licence to build SE-5.

---

# Part A — everything else: ACCEPT

- **URL determination (§1.1)** is a proper evidence chain: stub falsified against a known-good date, guesses eliminated, SPA API located, direct GET confirmed, `isSetl`/`setlQualifier` verified inside the payload. This is how a source claim should be established.
- **A-P4 FAIL is the most valuable output of Part A.** Both on-disk samples are intraday (`isSetl=0`, `setlQualifier=early`). Had the prediction not been pinned in advance, the job would plausibly have targeted the `i1` begin-day file — the archive would have filled for two years with the wrong publication, and `SpanRepository` would have reported a healthy archive throughout. This is the "container checks are not content checks" failure caught before it happened.
- **Raw-first retention and the settlement assertion** are correctly ordered: parse failure exits non-zero with the raw durable; a non-settlement payload is refused rather than archived.
- **A.3-1 fix via staging path** is the right call over re-keying the append-only guard, given existing tests pin that behaviour.
- **Chain placement last, asserted not printed** — correct, and directly addresses the "freshness value printed but never asserted is documentation, not a control" finding.

**Minor, non-blocking:** `file_hash` is now the SHA-256 of the archived zip with the `.spn` hash in `metadata["spn_sha256"]`. That satisfies `SpanRepository.load()`'s verification contract, but the zip is a container whose bytes could in principle change without the `.spn` changing. The `.spn` hash is the semantically meaningful one. No action required — just ensure any future integrity claim cites `spn_sha256`, not `file_hash`.

---

# Part B — ACCEPT, no defects

## The one thing I went looking for, and did not find

With announcement-date coverage at 13.6% (9 of 66), a cluster count of 22 **cannot** come from distinct announcement dates as §B.4-5 defined them. I expected to find the effective date silently substituted — the substitution §B.4-4 explicitly forbade.

It was not. §4 reports **both** bases and labels them: `n_clusters_struct = 22` (month-resolution structural) and `n_clusters_sourced = 2`, with the explicit note that the latter *"reflects the §3 coverage rate, not the true cluster count."* That is the correct handling and it is disclosed in the right place. Credit where due.

## Findings accepted

- 70 raw → 4 artifacts → **66 genuine** (58 scheduled / 8 ad-hoc), **22 clusters**, ratio **3.0**.
- Required `δ/sd`: **0.3501** at name level, **0.6264** at cluster level — **≈4.7×** the dossier's 0.13.
- **NSE's own `DUMMY*` placeholder rows** (`DUMMYREL`, `DUMMYTATAM`, `DUMMYHDLVR`) fabricated 6 spurious events before exclusion. This is a substrate defect in the official source and belongs in the pitfall register: *the vendor's test data is in the production archive.*
- ZOMATO→ETERNAL correctly collapsed; TATAMOTORS→TMPV disclosed as a sensitivity rather than silently decided. Correct — the demerger is genuinely ambiguous at entity grain.
- 2018-05 MCWB gap **not crossed**. Correct, and it makes 66 a **floor**, not a point estimate. Say so explicitly in the report.

## §B.6 verdict — upheld

`22 < 30` and `3.0 ≥ 3`. **The rule triggers.** I accept the verdict and it binds me: the dossier's SE-1 ranking must be revised in writing.

Note the ratio sits exactly on its boundary. That does not weaken the verdict — the cluster condition (22 vs 30) clears comfortably and `δ/sd = 0.6264` is the operative number regardless of which side of 3.0 the ratio lands. Had the verdict rested on the ratio alone I would have called it knife-edge; it does not.

## Two cautions for whoever picks this up

**B-C1 — Do not pool Nifty 50 and Next 50 to raise `n`.** It is the obvious next move and it is wrong. A name dropped from the Nifty 50 is typically *added* to the Next 50 in the same review: one index event, two register rows, **opposite-signed and partially offsetting flow**. Pooling would double-count the events and net away the effect being measured. If both indices are used, the unit must be the *entity-review*, not the index-membership row.

**B-C2 — The report calls 13.6% announcement coverage "the binding constraint." At cluster resolution it is not.** If the honest observation unit is the cluster — which §B.6 just established — then **22 announcement dates are needed, not 66.** Fifty-eight of the 66 events are scheduled semi-annual reviews with a published four-week notice convention, so they collapse into a small number of review announcements. That reframes the sourcing task from "an intractable 66-item hunt at 13.6% yield" to **roughly 22 lookups** — a day of work, not a wall.

This does not rescue SE-1's arithmetic. It does mean the *stated* binding constraint is the wrong one, and the report should be corrected on this point before anyone concludes SE-1 is dead for a reason that does not hold.

---

# Consequences for the dossier

`STRUCTURAL_ALPHA_DOSSIER_2.md` claimed SE-1 was *"the only candidate whose demonstrability arithmetic is comfortable rather than marginal"* and ranked it **#1** on that basis. **That claim is now false and the ranking must be revised in writing before any RFA declaration**, per §B.6.

The honest restatement:

- SE-1's required `δ/sd` at the honest observation unit is **0.6264**, not 0.13. It is **marginal, not comfortable.**
- Whether it survives depends on whether published Indian inclusion-premium effect sizes support a cluster-level `δ/sd` above 0.63 — a question to be answered **against the literature**, not against this platform's data, and not by re-deriving the unit after seeing the number.
- **No candidate in the dossier now has comfortable arithmetic.** That is the correct and uncomfortable state of the ledger, and it should be recorded as such rather than resolved by promoting whichever candidate is least measured.

The pass cost one script and no market data, and it falsified the lead's own top-ranked claim before any window was opened. That is the gate working exactly as designed.

---

# Actions, in priority order

| # | Action | Urgency |
|---|---|---|
| 1 | **Run the SPAN backfill** (~280 sessions, decaying ~1/day) | **Immediate — losing value hourly** |
| 2 | Correct `SPAN_INGEST_ACTIVATION_REPORT.md` §6 with the measured window and probe evidence | Immediate |
| 3 | Revise SE-1's ranking and the "comfortable arithmetic" claim in `STRUCTURAL_ALPHA_DOSSIER_2.md` | Before any RFA declaration |
| 4 | Correct the "binding constraint" framing in `SE1_EVENT_COUNTING_REPORT.md` per B-C2; state 66 is a floor | With the next edit |
| 5 | Add the `DUMMY*` source-pollution finding to CLAUDE.md's pitfall register | With the next edit |
| 6 | Audit futures/options ingests for unprobed "source doesn't have it" claims | Soon |
| 7 | Source the ~22 cluster announcement dates; decide SE-1 against the literature | After 3 |

Nothing here authorizes construct work. No pre-registration exists, no gate has been run, and the sealed windows remain as inventoried.
