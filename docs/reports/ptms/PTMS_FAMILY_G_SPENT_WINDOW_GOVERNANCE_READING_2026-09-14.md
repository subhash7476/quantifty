# PTMS Family G — what "signal-level SPENT" means for 2023–2025

**Date:** 2026-09-14 · **Type:** governance reading (the ruling itself is the operator's)
**Question from the operator:** does "signal-level spent" (A) forbid every future hypothesis from
using those observations, or (B) only forbid calling them fresh confirmation data?
**Scope honoured:** no market outcome read, no RFA run, `PTMS-G-PTSQ` unchanged (candidate commit
`3e08f63`, spec SHA-256 `d8707b3a…`), exposure register not modified. The only computation was
power arithmetic on hypothetical sample sizes, which touches no data.

---

## 1. Answer: B. The written policy has no rule that says A

The policy is closer to B than to A, but B needs tightening: the restriction is on **evidential
status**, not on access. Four provisions settle it.

| Provision | Text | What it establishes |
|---|---|---|
| Register, header | "**This register authorizes nothing.** It records reads. It does not grant or withhold permission to read; that is the operator's call." | Being spent is a record, not a ban. Whether anyone may read the window is decided per case by the operator |
| Register §1, level table | `signal`: "Spends budget? **Yes**" | What is consumed is *budget*. The table never says *prohibited* |
| Register §8, maintenance rule | "a project that fails to record one cannot later claim the window was **fresh**"; "`n_available` must be justified against this register" | The consequence of a read is **loss of freshness**, and that loss reaches the RFA through `n_available` |
| Alignment record §1 | "**Out-of-sample** — measured on a window that was **unread when the specification froze**" | Defines the property a spent window has lost |
| Alignment record §6 | "A declared `n_available` over a read window is a **false power calculation**" | Spent observations may not count toward confirmatory sample size |

**The provision that answers the "but this is a new hypothesis" argument directly** is register §1,
*Lineage-local vs global*: a construct's "untouched" designation "does not make the underlying
observations globally unread for successor research." **Freshness belongs to observations, not to
hypotheses.** A hypothesis being new does not make the data it would read new.

**Gap in the written policy, for the operator to close.** Nothing states what spent budget
*permits*. The reading above is the only one consistent with the texts cited, but it is not written
down as a rule. P3 reconciliation §1.1 treats budget as fixable by "nobody — only calendar time",
which describes confirmatory use and says nothing about other uses.

## 2. Why the restriction exists: the hypothesis is new, but the information is not

The operator's premise — that G was defined independently and has read no 2023–2025 outcome —
is **true of data reads and false of information.**

1. **MSRP's result on that window entered this design.** `PTMS_FAMILY_G_P3_HYPOTHESIS_DEFINITION.md`
   §11.3 records it. MSRP's D1 verdict on 2023–2025 was that a conditional straddle timing rule
   lost money net while the unconditional short straddle made money, and that next-day realized
   vol was nearly orthogonal to straddle P&L. That verdict **motivated the long/short overlay over
   a short-only rule** and **pushed the Sharpe band down.** A design shaped by what a window showed
   cannot be validated on that window. This is the adaptive-reuse problem: the same data, analysed
   in a sequence where each step is informed by earlier results.
2. **The outcomes are nearly the same random variable.** MSRP evaluated near-expiry at-the-money
   NIFTY straddle P&L over 2023–2025. G's outcome is near-expiry at-the-money NIFTY straddle P&L
   over the same sessions. Knowing MSRP's result is partial knowledge of G's outcome series before
   G ever reads it.
3. **Programme-level multiplicity.** Every hypothesis tested on the same observations adds a draw
   against one realized history. A per-hypothesis "fresh" label would let a programme test
   indefinitely on one window while reporting a nominal α each time.

None of this is a defect in G. The disclosure in §11.3 is what makes G honest. It is also why
2023–2025 cannot be exchanged for an unread window.

## 3. Classification of 2023–2025 for PTMS-G-PTSQ

**Non-confirmatory evidence.**

| Candidate category | Fits? | Why |
|---|---|---|
| TRAIN | **No** | G fits nothing, so its TRAIN (§10) is a *gate*: a pass lets the hypothesis proceed. Putting a spent window on the pass path gives a gate-shaped verdict on data whose information already shaped the design |
| Secondary / replication | **No** | Replication means independent confirmation, and spent data cannot supply it |
| HOLDOUT or RFA `n_available` | **No** | Alignment §1 (out-of-sample definition), alignment §6 and register §8 |
| **Non-confirmatory evidence** | **Yes** | May be read and reported. **Cannot pass any gate and cannot add to confirmatory n.** It has the same standing as §14.2's secondaries S1/S2 |

**Option the operator may add before freezing (not recommended by default).** The window could be
used as a **falsification-only screen**: a failure would ABANDON, while a pass would carry no
weight. The asymmetry is defensible, because nobody tunes a construct in order to fail. It would
still be a change to G's specification, so it must be decided **before** the freeze. It adds a way
to kill a true effect on a different regime.

**Worked precedent already in G.** §5's settlement-semantics check is confined to 2023–2025
*because* that window is spent. It reads settlement values, computes no outcome statistic, and
feeds no gate. That is exactly the "non-confirmatory, zero-weight" use formalized here.

## 4. If G were frozen before reading 2023–2025, could that window add sample size?

**Two levels, two answers.**

- **Data-mining within the hypothesis: no.** If the specification is frozen before the read,
  nothing in it is tuned on 2023–2025. Adding the window would not be snooping by *this*
  hypothesis.
- **Legitimate increase in confirmatory sample size: also no.** Freezing first removes the risk of
  within-hypothesis snooping. It does **not** restore out-of-sample status to a window that was
  read before the specification existed. 2023–2025 fails alignment §1's definition however the
  freeze is ordered, and §2 above gives the substantive reasons: the design is informed by the
  window, and the outcome is correlated with a result already known. Pooling it would raise the
  nominal n while the effective independence stayed lower than that n implies.
- **Non-confirmatory sample size: yes.** Declared before any read, the window can enlarge a
  descriptive or falsification-only analysis (§3).

## 5. Even the most permissive reading does not change the RFA verdict

This is power arithmetic on **hypothetical** sample sizes (`scripts/rfa/power.py`, one-sided,
α = 0.05, cadence 52). It reads no data and is **not a design option**: the pooled figures count
observations that §3 rules non-confirmatory.

| n | Composition | Power at S = 1.00 | Power at S = 0.625 |
|--:|---|--:|--:|
| 35 | HOLDOUT only (the valid design) | 0.200 | 0.127 |
| ~185 | HOLDOUT + ~150 cycles of 2023–2025 | 0.593 | 0.319 |
| ~288 | HOLDOUT + TRAIN + 2023–2025 | 0.759 | 0.430 |

(~150 is ≈ 52 weekly cycles a year × 3, an approximation; the 2023–2025 ladder was not counted.)

**Even pooling every certified window after 2020, including the one that cannot confirm anything,
does not reach 0.80 at the optimistic corner.** So the wall is not only "HOLDOUT is small". It is
that the certified Family G surface after 2020 is too short for a single-underlying weekly
hypothesis at a defensible Sharpe. §13.7 of the P3 definition stands, in a stronger form.

## 6. Separate open question, not decided here

The **observation-shaped exposure** question (P3 reconciliation §1.2; P3 definition §11.2) asks
whether reads of the NIFTY *index path* through other stores spend G's windows. It is a different
question from this one, which concerns a read of the **options store itself**. It remains open.

## 7. For the operator

1. Rule A or B. The texts support B, read as "spent means not confirmatory; access is the
   operator's call".
2. If B, codify what spent budget permits as a register rule. Rows and rules are append-only, so a
   new §-level rule is needed, not an edit.
3. Decide, **before freezing G**, whether 2023–2025 is (a) not used at all, which is the current
   specification, or (b) added as a falsification-only screen, which changes the specification.
   Neither option changes the predicted RFA verdict.
