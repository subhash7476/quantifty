# SE-3 Confirmatory Run — Lead Review

**Reviewer:** Claude (review only, per standing role split)
**Date:** 2026-08-06
**Under review:** `SE3_SUBSTRATE_CERTIFICATION.md`, `SE3_CONFIRMATORY_REPORT.md`,
`SE3_CONFIRMATORY_SNAPSHOT.json`, `scripts/se3/{certify_substrate,run_confirmatory,collect_option_spreads}.py`,
`tests/se3/{test_confirmatory,test_spread_collection}.py`
**Against:** `SE3_PRE_REGISTRATION.md` (FROZEN, SHA-256 `917c688b…`) and `SE3_IMPLEMENTATION_PROMPT.md`

---

## 0. Verdict

**The read is valid. The conclusion drawn from it is not.**

G1 and G2 stand: mean daily cross-sectional rank IC **−0.1124**, NW(5) t **−21.5157**, n 1,680,
significant and correctly signed. sd_IC 0.1940 sits inside the declared band [0.1877, 0.26] (D2
PASS). Windows were respected — the NIFTY index-option leg and the 2026 tail are demonstrably
unread. The construction reproduces the probe's *clean* skip-a-day form, not the contaminated
same-day form (probe A skip-a-day −0.1130 / sd 0.1877 vs same-day −0.1298 / 0.1938).

**But `SE3_CONFIRMATORY_REPORT.md` §7 reads the frozen outcome matrix into the wrong row.** It
records "Candidate for design" on the strength of D1 rungs that are not net-of-cost as
pre-reg §5.1 defines them. On the artifact as computed, the correct cell is
**NO-BUILD — "real but unharvestable," the pre-declared expected outcome.** That is CRITICAL-1.

**No part of this review requires re-running Phase 2.** The snapshot stands. Every correction below
is to reports, gates, or the D1 diagnostic layer, and none can touch G1 or G2.

---

## 1. BLOCKING — two questions I cannot answer from the artifacts

These gate the grading of HIGH-2 and MEDIUM-1. Answer before the run is written into `CLAUDE.md`.

### B-1 — What were NW t and n_dates on the pre-fix run?

The report states Phase 2 was executed, recorded **G1 FAIL at p = 2.0**, the p-value formula was
corrected, and a re-run recorded **G1 PASS at p ≈ 0**.

`p = 2.0` is impossible for any defensible formula — it is `2·(1 − cdf(t))` evaluated at `t = −21.5`
without `abs()`. The correction is therefore *forced*, not chosen, which is materially different
from selecting a rule that favours a result.

**The discriminating fact is whether the test statistic moved.**

- If **NW t was −21.5157 on both runs**, the re-run recomputed a deterministic function of an
  unchanged statistic. The one-shot property is intact in substance; this is a **disclosed
  deviation**, not a defective read.
- If **t moved**, the read itself changed after a result was seen, and this is TS Basis's failure
  mode — a de-authorization question, not a documentation one.

Report the pre-fix **t and n_dates together.** If `n_dates` also moved, that is a worse story than a
formula bug, because it means the eligible set changed across runs.

### B-2 — Which end does the 1,680th date sit on?

Certification says **1,679** usable dates; Phase 2 consumed **1,680**. Print the first and last
formation date each script considers eligible.

- **Warmup end** (expected): Phase 1's waterfall subtracts a flat 20 warmup dates while Phase 2
  honours A10's actual **≥18-observation** floor, which legitimately admits one earlier date. Then
  **Phase 2 is correct and Phase 1's waterfall line is the wrong one** — fix the report, not the run.
- **Tail end:** a return was constructed reaching past the last available date. The fence proof
  (max read 2022-12-30) constrains this but does not fully settle it, because the per-name row shift
  can pair across a gap. That would be a fence question, not a counting question.

---

## 2. CRITICAL-1 — the outcome matrix is read into the wrong row

**Where:** `SE3_CONFIRMATORY_REPORT.md` §7; `run_confirmatory.py:234`.

Pre-reg §5.1 defines the D1 net as *"assumed round-trip option costs of 0 / 25 / 50 / 100 bps of
premium, **plus** statutory charges (options STT is sell-side on premium; exchange, SEBI, stamp, GST)
**and the futures-leg hedge cost**."*

The implementation computes:

```python
net = gross - cost_b - cost_t        # run_confirmatory.py:234 — spread rung only
```

`_statutory_option_costs` (`:242`) and `_futures_stt_sell_rate` (`:95`) are written, correct, and
**never wired into the net.** The report says so itself: *"Statutory charges below are listed as an
additional labelled cost layer, not folded into the net."*

**Consequence:** no rung in the D1 table is a net-of-cost number as the pre-registration defines it.
The 0 bp and 25 bp rungs are not "positive net" — they are gross-of-statutory. §7 cites matrix row 1
("Significant, correct sign / Positive → candidate for design") on the strength of two figures that
do not exist as computed.

The direction of the omission is known even where the magnitude is not: option STT is **sell-side on
premium**, this is a **daily-formation** construct (~252 round trips/yr), and the futures hedge leg
carries its own STT and charges. Every rung's net is optimistic, and the rungs nearest the decision
boundary are the ones the omission moves.

**The frozen matrix decides this, not the operator and not the implementer.** A P&L that flips sign
across an admittedly unmeasurable assumption is "negative **or indistinguishable**" — matrix row 2:

> **NO-BUILD. The IC finding stands and is recorded. This is the expected outcome given `N_eff` 5.9
> and §5.**

**Required:** recompute D1 with statutory and futures-leg costs folded into `net` per §5.1, and
correct §7 to row 2. This is a diagnostic recomputation on the frozen panel — it cannot touch G1,
G2, or the snapshot's IC fields, and it is not a second read.

---

## 3. HIGH-1 — D1 is reported in uninterpretable units

`gross_total = 6.8166` is a sum of **vega-scaled unit P&L** over 1,680 days. It is not a return, not
a Sharpe, and not comparable to capital. Nothing in the report converts it to anything a reader can
size against, yet §7 draws a build-relevant conclusion from its sign.

Given `N_eff` 4.7 — **below** the probe's 5.9, as Q8's withdrawn prediction anticipated — a ~50-name
book carries roughly five independent bets. Pre-reg §4 pinned exactly this: a `rank_ic` PROCEED does
not imply a `per_trade_pnl` PROCEED.

**Required:** either express D1 in a unit that supports the claim made from it, or state plainly
that it supports no sizing claim. The second is cheaper and is what §4 already anticipates.

---

## 4. HIGH-2 — the one-shot read was re-executed after a result was seen

Grading depends on **B-1**. Regardless of that answer, this must be recorded permanently in the
report and in `CLAUDE.md`, in the same way TS Basis's gate defect is recorded — so no later reader
mistakes this for an untouched one-shot.

Operator authorization was obtained, which satisfies prompt §7 ("restarting a one-shot read after a
partial execution is a decision for the operator, not a retry"). Process was followed. The
disclosure requirement is separate from and survives the authorization.

The same question applies to the D1 "degenerate ladder" fix: **confirm it changed only `net`, and
left `gross` and the IC untouched.** The current table shows identical gross (6.8166) at every rung,
which is *correct* — gross is cost-free by construction — so the original "all rungs identical
gross" symptom was not itself the defect.

---

## 5. MEDIUM-1 — the S3 gate certified a set Phase 2 did not consume

`SE3_CONFIRMATORY_REPORT.md` §9 asserts: *"S3: 1679 usable dates … **this is the count Phase 2
consumed**"* — while §3 of the same script-generated report states `n_dates 1680`. Both cannot hold.

Magnitude is one date in 1,680 and cannot move a t of −21.5. The governance point is the finding:
**the reconciliation between Phase 1's certified set and Phase 2's consumed set was asserted in
prose and never asserted in code.** That is this repo's own pitfall — *a value that is printed but
never asserted is documentation, not a control* — reappearing inside the very gate built to enforce
it.

**Required:** resolve via B-2, correct the false sentence, and have Phase 2 assert
`n_dates == certified_usable` at startup rather than restate it in prose afterward.

---

## 6. MEDIUM-2 — the universe contains 51 names on a 50-member index

`SE3_SUBSTRATE_CERTIFICATION.md` §6: **p90 = 51** names/day for 2016 and 2017 (median 50, p10 49).

A PIT Nifty 50 snapshot has exactly 50 members, so p90 = 51 means some dates carry a name that is
not a member. Likeliest cause is a duplicate underlying across a symbol rename — the repo's own
"an entity is not one symbol for all time" pitfall, and the same class of defect as the `DUMMY*`
source pollution SE-1 found.

**S1 reports PASS**, which is the finding: **S1 checks that membership *resolves*, not that its
*cardinality* is right.** A membership gate that cannot notice 51 members in a 50-member index is
checking the wrong property.

Cannot move the verdict at t = −21.5. **Required:** add `assert n_members == 50` per snapshot to S1,
and report which symbol pairs collide.

---

## 7. The finding itself — read this before celebrating the magnitude

The realized |IC| of **0.1124** is **3.6× the top** of the declared δ band [0.0146, 0.0311] and
~7.7× its centre. It lands within 0.0006 of the probe's skip-a-day **−0.1130** — the number
`CLAUDE.md` explicitly **prohibits as the δ anchor** because it came from the burned window.

Two readings, and the report picks neither:

1. **A genuine, large, stable effect.** Indian single-stock options are well documented as carrying
   high IV relative to RV.
2. **A mechanism that is real but not a premium.** `richness_i` is the residual of σ on rv; the
   delta-hedged return over `t+1 → t+2` is dominated by the **vega × ΔIV** term. So an IC of −0.11
   is substantially a restatement of **name-level IV mean reversion** — high IV today, lower IV
   tomorrow — which is a known statistical property, not evidence of a capturable premium.

**Reading 2 is what the artifact actually supports**, because it predicts exactly the pattern
observed: a very large, very stable IC alongside a D1 P&L that does not survive plausible costs.
That is the textbook shape of "real but unharvestable."

**And cross-window stability is not independent evidence here.** The confirmatory shares a code
lineage with the probe, and the prompt's own helper cross-check test (§1.7) *guarantees* the two
modules agree on `_newey_west`, expiry picking, front-month RV and `N_eff`. A shared construction
artifact would reproduce across both windows **by design** and pass that test. The test converts a
copy-paste risk into a checked invariant — it does not make the second measurement independent of
the first. Any successor must state this explicitly rather than cite 2016–2022 and 2023–2025 as two
confirmations.

---

## 8. What went right — worth recording

- **Fence discipline held.** Index-option leg 2016–2022 unread; 2026 tail preserved; max read
  2022-12-30.
- **Variant B is absent, not disabled**, and the absence is mechanically tested.
- **The skip-a-day convention reproduces the probe's corrective run**, including the contract being
  held fixed across the return window — the ambiguity the prompt resolved at §3.2 was implemented as
  specified.
- **A5 is doing real work**: 20,616,246 rows → 3,897,393 traded (−81%). The prompt predicted S3
  would bite and it did not; the reason is now clear and is a legitimate empirical finding —
  row-level attrition is severe, but name-level survival needs only one traded strike per side
  inside a ±10% band, so Q1's FAIL is correct rather than suspicious.
- **The 2018-05 MCWB gap was stopped on and escalated**, not silently patched — the prompt's
  "stop and report" discipline working as intended.
- **§9.2 spread collection shipped** as a standalone append-only collector, correctly independent of
  this run.

---

## 9. Disposition

| Item | Grade | Action |
|---|---|---|
| B-1 pre-fix t / n_dates | **BLOCKING** | Answer before `CLAUDE.md` is written |
| B-2 which end the extra date sits on | **BLOCKING** | Print first/last eligible formation date per script |
| Outcome matrix row | **CRITICAL** | Fold §5.1 costs into net; correct §7 to **NO-BUILD** |
| D1 units | **HIGH** | State that D1 supports no sizing claim |
| One-shot re-execution | **HIGH** | Disclose permanently in report and `CLAUDE.md` |
| 1,679 vs 1,680 | **MEDIUM** | Assert equality in code; correct §9's sentence |
| 51 names on a 50-member index | **MEDIUM** | `assert n_members == 50`; report colliding symbols |
| Magnitude interpretation | **NOTE** | Record the IV-mean-reversion reading and the shared-lineage caveat |

**G1 and G2 are not in question.** The construct demonstrably ranks Nifty 50 constituents on
subsequent delta-hedged underperformance, at a significance no reasonable cost assumption touches.
What is in question is the sentence that follows from it — and on the artifact as computed, that
sentence is **NO-BUILD, with the IC finding standing and recorded.**
