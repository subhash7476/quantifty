# CSMP Phase 1 — Operator Ratification & Author-Lock

**Date:** 2026-07-12
**Operator:** Subhash (program operator — the sole party empowered to ratify)
**Recorded by:** Claude (Lead Reviewer — recording the operator's decision; not making it)
**Applies to:** `CSMP_PHASE1_RESEARCH_DOSSIER.md` Rev 5 → **Rev 6 (RATIFIED, author-locked — NOT yet frozen)**

> **This record does not freeze the dossier.** Charter §6 row 2 orders Phase 2 as
> *"institutional-style critique; revisions folded in; dossier FROZEN"* — **review first, then
> freeze.** What this record does is **ratify the three open decisions and lock the authors**: Claude
> and DeepSeek make no further self-initiated changes. The dossier goes to Phase 2 as a stable
> artifact, **not an immutable one**. Phase-2 findings are folded in, and the immutable **FROZEN**
> stamp lands at **Rev 7**, after that review — never before it.

> **Pre-seal attestation.** As of this timestamp the sealed held-out window
> (**2023-01 → 2026-06**) has **not been read**. No number in the dossier, in
> `CSMP_PHASE1_OPERATOR_DECISIONS.md`, or in this record was computed on, informed by,
> or inspected against it. Every figure below is a dev-window (2012-01 → 2022-12)
> quantity or a calendar fact, reproducible from the three named scripts at seed
> `20260711`. **The decisions ratified here are therefore pre-registered in the strict
> sense: they were committed before the data that will judge them was seen.**

---

## 1. The three decisions, ratified

All three §3.4 inference decisions are **RATIFIED AS RECOMMENDED**.

| | Decision | Ratified value |
|---|---|---|
| **D-i** | CI method (validity) | **One-sided 95% Student-t lower bound** on the monthly `IC_t` series, selected by the pre-registered *coverage-closest-to-nominal* rule. Coverage 0.957 / one-sided Type-I 0.049 at n=42 (nominal 0.95 / 0.05). The moving-block **L=12 percentile CI is retired to a reported, non-gating robustness arm** — it covers at 0.811 (Type-I 0.129, ≈2.6× nominal) and is **invalid** at this sample size. |
| **D-ii** | Tail (power) | **One-sided.** H₁ was directional from §3.3 onward (`mean_IC > 0`); a two-sided test spends half its α guarding an outcome with no decision attached. A one-sided 95% lower bound excluding zero satisfies charter D3's "block-bootstrap 95% CI excluding zero" on a plain reading, and the operator ratifies that reading **here, before the seal**. |
| **D-iii** | Extension design | **Single-shot.** The sealed window is scored **once**, at #42, at full one-sided α = 0.05 (power ≈ **0.41**), and is then **spent and never re-read**. The Pocock group-sequential alternative is **declined**; O'Brien–Fleming was already disqualified (it collapses the primary read to 0.04 power). The naive "re-read annually until it clears" calendar is **prohibited** — its family-wise Type-I is 0.130, the exact level of the `mb_L12` bug D-i removed. |

### 1.1 Why D-ii's timestamp matters, and where it lives

One-sided testing is legitimate **only** when the direction was committed before the data.
It was: `mean_IC > 0` is stated in §3.3 of the dossier from Rev 1 (2026-07-11), and this
record ratifies it 2026-07-12 — both **before** the first sealed read (Phase 6, not yet
run). This paragraph exists so that fact is explicit in the record rather than implicit in
a revision history.

### 1.2 The D-i selection — **CORRECTED 2026-07-12 by Phase-2 finding F1**

> **This section originally read: "the coverage rule selected against power (Student-t 0.398
> vs stationary's 0.453) — the evidence the rule was not reverse-engineered."** The Phase-2
> independent reviewer falsified that framing (`CSMP_PHASE2_INDEPENDENT_REVIEW.md` **F1**,
> HIGH; accepted in `CSMP_PHASE2_LEAD_DISPOSITION.md`). **It is corrected here, not
> supplemented.** Two things were wrong: the comparison **omitted `iid_perc` entirely** — the
> actual relevant foil, which has *higher* power than Student-t **and** is the winner under a
> literal reading of the rule as written; and the rule itself was **underspecified**, never
> naming *which* calibration metric "closest to nominal" referred to.

The full candidate table:

| CI method | 2-sided coverage | 1-sided Type-I | 1-sided power @ dev IC |
|---|---:|---:|---:|
| **Student-t (selected)** | 0.957 | **0.049** | **0.398** |
| `iid_perc` (the two-sided-reading winner) | **0.949** | 0.054 | 0.418 |
| stationary bootstrap (mean-block 3) | 0.924 | 0.064 | 0.453 |
| moving-block L=12 (retired incumbent) | 0.811 | 0.129 | 0.538 |
| *nominal* | *0.950* | *0.050* | *—* |

**The rule as first written was ambiguous.** Under **two-sided coverage** it selects
`iid_perc` (0.949, distance 0.001). Under **one-sided Type-I** it selects Student-t (0.049,
distance 0.001). The guardrail sentence disambiguated *coverage vs. narrowness* — it never
disambiguated *which calibration metric*.

**Ratified disambiguation (2026-07-12):** *because the primary gate is a one-sided lower
bound, select the method whose **one-sided null rejection rate at n = 42 is closest to nominal
0.050**; two-sided coverage is reported as a sanity check, not used to select.* Calibrate the
statistic you actually use. This is also the independent reviewer's own primary fix. The rule
is applied **mechanically to the §5.2-corrected table** (Phase-2 **F2**), and whatever it
selects **is** the gate; the non-selected arms (`iid_perc`, `mb_L12`) are reported as
non-gating, so both readings stay visible and neither can be preferred after the sealed result
is seen.

**What survives of the integrity claim, stated accurately:** Student-t is the **lowest-power
valid candidate** (0.398, vs `iid_perc` 0.418 and stationary 0.453). The selection is
therefore still **not** power-seeking. But it was **not** the clean, unambiguous application
the original wording implied, and the disambiguation was made **after** the table was seen —
**pre-seal, on a corrected table, and disclosed**, which is what makes it legitimate. It is
disclosed rather than dressed up.

*(Ordering note, for the record: the operator memo insisted D-i be settled* first *and D-ii
second. "One-sided Type-I closeness" is a criterion that only exists once D-ii is decided — so
the original selection reached for a criterion the program's own sequencing had not yet
unlocked. The sealed window is untouched, so nothing about this can have been informed by the
outcome; it is a repairable ordering defect, and this is the repair.)*

---

## 2. Charter §6 — **SUPERSEDED 2026-07-12 by Phase-2 finding F3**

> **This section originally ratified a *reframing*: that charter §6's Approval precondition
> is "an epistemic condition, not a risk gate," and is therefore "satisfied-in-substance by
> disclosure" because a PaperBroker consumer puts no capital at risk.** The Phase-2
> independent reviewer rejected that (`CSMP_PHASE2_INDEPENDENT_REVIEW.md` **F3**, MEDIUM;
> accepted in `CSMP_PHASE2_LEAD_DISPOSITION.md`), and **the operator has ratified the
> reviewer's fix instead.**
>
> **The reasoning that was wrong.** The reframing modelled **capital risk and nothing else.**
> It did not answer **anchoring, sunk cost, or the quiet promotion of a Not-Approved artifact
> into an operationally trusted one** — as dashboards, reports, and engineering investment
> accumulate around a running system, "exploratory" erodes without anyone deciding to erode
> it. That cost is real and it is not zero. **Changing what counts as satisfying a charter
> precondition is an amendment; calling it a reframing made it sound cheaper than it is.**

**Ratified in its place — an explicit, dated amendment to charter §6, with controls:**

> **Charter §6 amendment (2026-07-12).** An Inconclusive Phase-6 result leaves the artifact
> **Not Approved**. The top-40 PaperBroker consumer may still be built and run, as an
> explicitly **exploratory** deployment, under these controls:
>
> 1. It is **not** Phase-7 completion, and must not be recorded as such.
> 2. It may **never** appear in Approved / Deployable / certified language — in code,
>    dashboards, or reports.
> 3. It runs under a **separate exploratory runbook**, distinct from the production consumer
>    path.
> 4. Its forward data may enter **only a fresh pre-registration with frozen rules and fresh
>    α** — never a re-read of the spent window, never a retrofit of this one.

The engineering path is unchanged; what changes is that it is now recorded as **an amendment
with teeth rather than a definitional escape.** That is better governance, it is auditable,
and it costs the program nothing.

**What this does and does not license:**

- **Licensed:** building the `PublishedArtifact v2` + A2 harness (§2.2 items 1–2)
  unconditionally, and running the top-40 EW `GuardedSignalSource` consumer on
  **PaperBroker only** (§2.2 item 3) regardless of the Phase-6 verdict.
- **Not licensed:** calling an Inconclusive result a confirmation; deploying LIVE; changing
  any parameter of the frozen construct; re-reading the sealed window.

**Why the engineering path survives the amendment.** At ≈41% power, **Inconclusive is the
modal outcome (~59%) even if momentum works exactly as well out-of-sample as it did
in-sample.** If Inconclusive is treated as a dead end, the program strands on its own most
likely result. It is instead the *expected, non-failing* output that still ships the
engineering deliverable §2.2 already names as the point, and the program continues on
**forward data with fresh α** — new months, not re-reads.

**What the amendment changes is the guardrails, not the path.** The consumer still gets
built; it simply cannot quietly become a trusted, Approved-sounding system while the artifact
that produced it was never approved. That was the gap in my original framing, and the four
controls above are what close it.

---

## 3. The headline the freeze must carry

> **A valid, one-sided, correctly-covered test on 42 months is ~41% powered against the
> program's own point estimate. The single likeliest outcome of Phase 6 is
> "Inconclusive."**

This was computed **before the window was spent, not after** — which is the entire value of
the pre-registration discipline, and the most important thing Phase 1 produced. It is not a
failure of the design; it is the honest ceiling of the available sample. The alternative on
offer (the retired L=12 interval's apparent 0.538 power) was **a false-positive rate
wearing power's clothes**.

§11 of the frozen dossier must state this in exactly these plain terms.

---

## 4. Author-lock, and the road to freeze

**The dossier is authorized to advance to Rev 6 — RATIFIED and author-locked**, by the mechanical
application of §1–§3 above: no new analysis, no new numbers
(`CSMP_IMPLEMENTATION_PROMPTS.md` Prompt 6).

**What "author-locked" means, and what it does not.**

- **It binds the authors.** Claude and DeepSeek make **no further self-initiated revision.** The
  three decisions are stable and will not improve under another in-house pass; every author-initiated
  revision from here degrades the independent review it exists to feed, and adds sunk cost to a
  document that has already reached the edge of what its author-and-reviewer pair can self-verify.
  That limit is not a failure — **it is the signal that the handoff is due.**
- **It does not bind the Phase-2 reviewer.** The reviewer may challenge **anything**, including the
  three decisions ratified here and the §2 reframing. **Because the sealed window is still untouched,
  changing a ratified decision pre-seal remains entirely legitimate** — and enabling exactly that is
  why the charter puts the review *before* the freeze. A review that cannot change anything is
  theater.

**Why that distinction is load-bearing here, specifically.** This program has already found one
methodological error of precisely the kind Phase 2 exists to catch: the pre-registered L=12 CI was
**under-covering by ~4×**, and it survived two prior reviews before the coverage simulation exposed
it. The MSRP precedent is the same story — its Phase-2 review returned PASS WITH REQUIRED REVISIONS
on **M2, "an outright methodological error that would bake an anti-conservative test into an
immutable document."** The base rate of such findings in this program is **not** negligible. Freezing
before the review would leave the next one with nowhere to go.

**If Phase 2 lands a real finding:** it goes to the operator, the evidence is re-derived from the
scripts, the operator re-affirms or revises, and *then* the dossier freezes at Rev 7. The
ratification in §1 is **the operator's position on the current evidence — not a wall against pre-seal
correction.**

**Independence ledger — spent.** DeepSeek V4 authored the dossier and self-reviewed it
(`CSMP_PHASE1_LEAD_REVIEW.md` §Independence states this explicitly). Claude authored the
D-i/D-ii/D-iii memo and reviewed the dossier. **Neither is independent of this document any
longer.** The Phase-2 review must be conducted by a **third frontier model** that has
touched none of it (`CSMP_PHASE2_INDEPENDENT_REVIEW_PROMPT.md`).

**The safeguard that makes that review meaningful:** every number in the dossier is
re-derivable from three persisted, dev-only, seeded scripts —
`scripts/csmp/phase1_prereg_analysis.py`, `phase1_ci_coverage.py`,
`phase1_group_sequential.py` (seed `20260711`). The Phase-2 reviewer can re-derive the
evidence **without trusting either author**. That is the correct and sufficient check.

---

## 5. Sequence from here (charter §6 order — review, then freeze)

| # | Step | Owner |
|---|---|---|
| 1 | Apply §1–§3 to the dossier; stamp **Rev 6 — RATIFIED, author-locked, pending Phase-2** (Prompt 6) | DeepSeek V4 |
| 2 | Lead-Review the Rev 6 diff — mechanical-fidelity check only (did the ratification get applied, and did anything else move?) | Claude |
| 3 | Commit Rev 6 + this record + the three rederivation scripts | — |
| 4 | **Prepare the reviewer's handoff: a dev-truncated store (data ≤ 2022-12-30).** The Phase-2 reviewer must *execute* the three scripts — a review that cannot re-derive the numbers is only a prose critique — but the equity store physically spans 2010 → 2026-07, so full access would leave the seal resting on the reviewer's goodwill. All three scripts are dev-only, so **every dossier number still re-derives on the truncated store while the sealed window is physically absent.** (Same construction gate (c) used to prove PIT membership.) | Operator |
| 4b | **Phase-2 independent review** — adversarial, by a third frontier model (`CSMP_PHASE2_INDEPENDENT_REVIEW_PROMPT.md` — see its §1.1) | Operator issues |
| 5 | Fold Phase-2 findings; operator re-affirms or revises any decision they overturn | Operator / DeepSeek |
| 6 | **Rev 7 — FROZEN.** The construct fence becomes immutable | — |
| 7 | Phase 6 — the single sealed read, subject to the §8 A1 VOID precondition | — |

**Nothing in this record reads, or is informed by, the sealed held-out window
(2023-01 → 2026-06). It remains sealed.**
