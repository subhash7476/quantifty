# CSMP Phase 2 — Independent Model Review: prompt for the reviewer

**Issued:** 2026-07-12
**Issued by:** the operator (Subhash)
**To:** a **third frontier model** — one that has never seen this program before.
**Charter basis:** `CSMP_PHASE0_CHARTER.md` §6 row 2 — *"Independent model review: institutional-style
critique; revisions folded in; dossier FROZEN."* **Review first. Freeze after.**

---

## 0. Why you, and why this is not a formality

Two models have already worked this document. **DeepSeek V4** authored the research dossier and then
reviewed its own work (it says so, in writing, in `CSMP_PHASE1_LEAD_REVIEW.md` §Independence).
**Claude** wrote the memo that produced three of its most important decisions and reviewed the dossier
twice. **Neither is independent of this artifact any longer. You are the only independent check that
will ever run before the sealed data is read.**

Take the adversarial stance. **Your objective is to find flaws in this pre-registration before it is
frozen — not to ratify it.** A pre-registration is the one artifact whose defects are cheapest to fix
now and most expensive afterwards: once frozen, the document is immutable and the data is spent.

**Here is the fact that should calibrate your skepticism.** The dossier originally pre-registered a
moving-block (L=12) bootstrap confidence interval as its decision gate. **That interval under-covers
by roughly 4× at the actual sample size** — an 81% interval sold as a 95% one, a one-sided Type-I
error of 0.129 against a nominal 0.05. It would have let the gate approve a worthless artifact about
one time in eight *while presenting itself as conservative*. It survived **two prior reviews** by the
two models above. It was caught only by a coverage simulation run late.

**The base rate of that class of error in this program is not zero, and you are the last line.**
Deference is the failure mode here. If you find nothing, say so plainly and defend it — but do not
arrive at "looks rigorous" because the document is long, confident, and full of tables. It is
*designed* to look rigorous. That is precisely the condition under which the last error hid.

---

## 1. The one hard constraint: **do not read the sealed window**

The held-out window is **2023-01 → 2026-06**. It has never been read. Its integrity is the entire
value of everything else in this program.

- **Do not compute anything on it. Do not inspect it. Do not ask for a preview of it.**
- Every number you check must be a **dev-window (2012-01 → 2022-12)** quantity or a **calendar fact**.
- If your review would be strengthened by "just checking" a sealed-window statistic — **that is the
  exact temptation the whole architecture exists to defeat.** Say what you would want and why; do not
  take it.

A review that breaks the seal has destroyed the thing it was convened to protect.

### 1.1 Access & seal integrity — how the operator makes that constraint structural

**The seal must not depend on your goodwill, and it does not.** Section 3 asks you to *execute* the
three analysis scripts, because a review that cannot re-derive the numbers is only a prose critique.
But the equity store physically spans **2010 → 2026-07**: the sealed window lives inside it, one query
away from anyone who can open it. An honour-based seal is the weakest possible protection against a
reviewer who has been told — correctly — to be adversarial and thorough.

**So the operator supplies you with a dev-truncated store: all data ≤ 2022-12-30, with the sealed
window physically absent.**

- All three scripts are **dev-only by construction** (they read nothing past 2022-12-30 and assert it),
  so **every number in the dossier still re-derives in full** on the truncated store. You lose nothing.
- The sealed window is **not there to be read** — the seal becomes a structural fact, not a promise.
- This mirrors the construction gate (c) already used to prove its universe was point-in-time
  (membership as-of `t` must be identical computed from the full store or from a store truncated at
  `t`).

**If you have been handed a store that contains post-2022-12-30 data, stop and tell the operator
before you run anything.** That is a setup error, and proceeding would put the seal at risk. Likewise,
if some check you want genuinely requires sealed data, **name it as a limitation in your report** —
under "what I could not check, and why" — rather than reaching for the data.

---

## 2. What you are reviewing, and what you may attack

**Primary artifact:** `docs/reports/CSMP_PHASE1_RESEARCH_DOSSIER.md` (Rev 6 — RATIFIED, author-locked,
**not yet frozen**).

**Supporting record — read all of it:**

| Document | What it is |
|---|---|
| `CSMP_PHASE0_CHARTER.md` | The locked program decisions (D1–D5) the dossier operationalizes |
| `CSMP_PHASE1_OPERATOR_DECISIONS.md` | Claude's memo that produced decisions D-i / D-ii / D-iii |
| `CSMP_PHASE1_FREEZE_RATIFICATION.md` | The operator's ratification of those three, and the charter-§6 reframing |
| `CSMP_PHASE1_LEAD_REVIEW.md` | DeepSeek's **self-review** (states its own non-independence) |
| `CSMP_PHASE1_DOSSIER_LEAD_REVIEW.md` | Claude's review (B1–B4, S1–S9, A1–A3, R1–R4) |
| `CSMP_GATE_A…E` audits + lead reviews | The five data-precondition gates the dossier inherits |

**Everything is in scope — including the decisions the operator has already ratified.**

> **Explicit mandate.** You may challenge **D-i** (the Student-t CI), **D-ii** (the one-sided test),
> **D-iii** (the single-shot design), the charter-§6 epistemic reframing, the power analysis, the cost
> model, the delisting convention — **anything**. The operator's ratification is *his position on the
> current evidence*, **not a wall against pre-seal correction**. Because the sealed window is still
> untouched, **a change you trigger is entirely legitimate and will be folded in before the freeze.**
> That is why the charter puts your review *before* the freeze, and it is the only reason this review
> is worth running. **Do not treat the ratified decisions as settled. Nothing is settled until it is
> frozen, and nothing is frozen yet.**

---

## 3. Re-derive; do not trust the authors

**Do not take a single number on faith.** Every figure in the dossier is reproducible from three
dev-only, seeded scripts (seed `20260711`):

| Script | Produces |
|---|---|
| `scripts/csmp/phase1_prereg_analysis.py` | the §2.1 / §8 / §11 dev-window numbers (mean IC, CI, spreads, turnover, risk metrics) |
| `scripts/csmp/phase1_ci_coverage.py` | the §3.4 **D-i** coverage simulation (the CI-method selection) |
| `scripts/csmp/phase1_group_sequential.py` | the §3.4 **D-iii** FWER, α-spending boundaries, and decay scenarios |

**Run them** (on the dev-truncated store — §1.1) **and read them.** They exist precisely so you can
re-derive the evidence **without trusting either author.** A number that does not reproduce — or a
script whose method does not match what the dossier claims it did — is a first-class finding.

Read the **code**, not just the output: **the last big error was a method error, not an arithmetic
one.** For instance, the coverage simulation resamples **i.i.d.** from the empirical 131-month dev IC
distribution, justified by a claim that the IC series carries negligible serial dependence. **Is that
justification sound? What happens to the selected method if it is not?** That is the shape of question
that pays here.

---

## 4. Charter lenses (§6), applied

Apply these five explicitly, and say what you found under each:

1. **Hidden assumptions** — what must be true for this design to work that the document never states?
2. **Leaking features** — can anything in the score, universe, or label see the future, even by a day?
3. **Unstable labels** — is the forward return well-defined in every edge case (delisting, suspension,
   partial month)?
4. **Causal vs. merely predictive** — is the economic rationale doing real work, or decorating a
   correlation?
5. **Unmodelled uncertainty** — what error bar is missing, and would its absence change a decision?

---

## 5. Places the authors already suspect are weak — and the ones they may not

Attack these, but **do not be limited to them.** A list of known weak points is also a map of where
the authors were already looking, and the dangerous error is the one nobody was looking for.

**Statistical**

- The **i.i.d. resampling assumption** inside the D-i coverage simulation (§3 above).
- The **effective sample size** argument (§11, S3): the claim that the ~200-name cross-section reduces
  each month's *measurement error* but not the *month-to-month dispersion of the true IC*, so the
  effective n is **42, not ~8,400**. Is that decomposition right?
- The **decay simulation** behind D-iii: what exactly was assumed about the post-2026 world, and does
  the single-shot-over-Pocock conclusion survive a different but equally reasonable assumption?
- The **power figures** (≈0.41 one-sided at the dev effect size). Rederive them.
- **Program-wide multiplicity** — gates (a)–(e) each made decisions and each looked at the dev data. Is
  the pre-registration's α honest about everything that has already been looked at?

**Construct / data**

- **§5.2 rule 2** — a name with no session after `t` books a **0% step**. The authors concede 0% is
  generous in exactly momentum's left tail (the realistic generator is a suspension ahead of a
  bankruptcy delisting, whose true value is nearer −100%). Is the −100% sensitivity an adequate answer?
- **K = 40**, and the claim (S8) that **no selection occurred** — that a top-30 book was never computed,
  so K could not have been tuned. **Verify that against the gate-(e) code; do not accept it.**
- The **turnover / slippage 2× correction** (B3): traded notional is claimed to be 47.5%/month, twice
  the gate-(e) `two_way` metric. Check the arithmetic and its cross-check against the reported fee drag.
- **Gate (c)'s mechanical `turnover_top200`** standing in for true NIFTY-200 membership.
- The **A1 VOID precondition** — is re-running the corporate-action move screen actually sufficient to
  catch a bad split factor before it manufactures phantom momentum?

**Governance**

- The **charter-§6 reframing** (`CSMP_PHASE1_FREEZE_RATIFICATION.md` §2): the claim that running a
  PaperBroker consumer on a **Not-Approved** artifact costs nothing because no capital is at risk, so
  §6's Approval precondition is "satisfied-in-substance by disclosure." **Is that true?** Is there a
  real cost the argument ignores — anchoring, sunk cost, the quiet promotion of an exploratory system
  into a trusted one, the reputational weight of a strategy that is visibly *running*? Argue it.
- The **honesty of the decision table (§10)**. Does every possible outcome land somewhere, and is any
  row a disguised escape hatch?

---

## 6. Deliverable

Write **`docs/reports/CSMP_PHASE2_INDEPENDENT_REVIEW.md`**.

**Verdict — exactly one of:**

- **PASS** — safe to freeze as-is.
- **PASS WITH REQUIRED REVISIONS** — freeze only after the named findings are folded in.
- **NOT PASSED** — a defect serious enough that the pre-registration must be reworked.

**Findings — `F1 … Fn`**, each with:

| Field | Requirement |
|---|---|
| **Severity** | CRITICAL (invalidates the test) / HIGH (biases it) / MEDIUM (weakens it) / LOW (documentation) |
| **Claim** | One sentence: what is wrong. |
| **Failure scenario** | **Concrete**: the specific input or state under which this produces a *wrong verdict*. Not "this could be unsound" — **show the path to the wrong answer.** |
| **Evidence** | What you re-derived, and how it differs from what the dossier says. |
| **Fix** | The minimal change that closes it, pre-seal. |

Record explicitly, as well: **what you checked and found sound** (negative findings are evidence, and
they tell the operator where your review was actually strong), and **what you could not check, and
why**.

**Finally — one judgment the authors cannot make for themselves.** The document concedes that even a
valid, correctly-covered, one-sided test on 42 months is only **~41% powered** against the program's
own point estimate — so **"Inconclusive" is the single most likely outcome (~59%) even if the
hypothesis is exactly true.** The authors argue this is the honest ceiling of the available sample and
that the program should proceed anyway, building the engineering deliverable regardless of verdict and
buying further power from *new* forward months rather than re-reads.

**Do you agree that a ~41%-powered experiment is worth running?** Say so plainly, and say why. If your
answer is no, say what would have to change.

---

**The sealed window (2023-01 → 2026-06) has not been read. Do not be the one who reads it.**
