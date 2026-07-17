# PSB-2 Implementation Prompts

**Document type:** Prompt register (Claude → DeepSeek V4)

**Roles (standing):** DeepSeek V4 implements from written prompts. Claude writes prompts and reviews; never authors gate deliverables. The operator decides.

**Governing record:** `docs/reports/PSB2_PHASE0_RESEARCH_RECORD.md` (D8–D12).

---

## Prompt 0 — Protocol Rev 2 (ISSUED 2026-07-16)

**Task:** Revise `docs/reports/PSB2_PROTOCOL.md` from DRAFT Rev 1 to **DRAFT Rev 2**, disposing every finding in `docs/reports/PSB2_PROTOCOL_INDEPENDENT_REVIEW.md` (F1–F11) against operator decisions **D11** and **D12** (ratified 2026-07-16).

**You author the protocol prose.** This prompt specifies *what must change* and the acceptance criteria — it deliberately contains no finished §-text. The protocol is the Phase 0 gate deliverable and it is yours to write.

**Status on completion:** Rev 2 stays **DRAFT**. It returns to Claude for re-review, then to the operator for ratification and freeze. Do not stamp it FROZEN.

### Operator decisions that bind this revision

| Decision | Binding instruction |
|---|---|
| **D11** | Slate is **exactly three candidates: C2, C3, C4** (delivery z; delivery-conditioned reversal; momentum, staggered). C1 and C5 are **dropped** — remove them entirely, do not retain as commented-out or "deferred" entries. **Bonferroni ledger m = 3.** |
| **D12** | **§3 is the normative cadence source.** C2, C3 → **fortnightly** (n\* = 84). C4 → **monthly rebalance, 6-month staggered hold** (n\* = 42). The §5 preamble's "all five constructs operate at monthly cadence" is struck. |

### Required dispositions

**F1 — C5 dropped.** Remove the QARP candidate. No fundamentals data exists in the repo and §2's substrate pin cannot reach it. Do not attempt to substitute a price-derived quality proxy — that would be a new candidate, which §9 forbids without a fresh ledger.

**F2 — C1 dropped.** Remove the low-volatility candidate. Its IC series was definitionally identical to PSB-1's C5 (power 0.541 at n\* = 42, below the 0.80 hurdle). D11 records the full rationale including why the fortnightly restore was rejected.

**F3 — Cadence stated once, normatively.** §3 carries a single per-candidate cadence table. §5, §7, and §9 **reference** it rather than restating it — restatement is what produced the four-way contradiction. Every per-candidate n\*, turnover, and fee-drag figure must be recomputed from the pinned cadence, not carried over from Rev 1. Specifically: §5's C3 defines `r_i(t)` as a "1-month return… divided by close at previous grid day" — at fortnightly the previous grid day is ~15 days back, so the formula and its prose diverge. Fix so the pinned arithmetic and the stated meaning agree, and state which you intend.

**F4 — Delivery window corrected and script-derived.** Rev 1 claims C2/C3 run 2020-04-01 → 2022-12-31 with ~34 monthly formations. Both figures are wrong. With `deliv_pct` beginning 2020-01-01 and a 252-day baseline ending *t*−21 requiring ≥ 150 non-NULL, the earliest feasible formation is **2020-09-04**. Do not hand-copy this date: **derive the declared window and expected n from the pinned baseline lengths with a script**, print it, and cite the output. Note the fortnightly grid roughly doubles the formation count versus monthly — recompute, do not scale by hand. Also fix §3's "common robustness sub-window," which is degenerate for C2/C3 (it is their entire declared window).

**F5 — Fortnightly grid pinned to sessions, not a calendar number.** "The 15th" is not a full session in 18 of 42 sealed months. Restate as a session-anchored rule in the style of PSB-1 §3 (which anchored to "the last full-session trading day of that week", never to a date). State the rule explicitly; do not leave the implementer to infer it. Verify the resulting grid count against `trading_calendar` at the `n_symbols >= 200` full-session convention and print it.

**F6 — m = 3, with the rationale in the protocol.** §8 and §9 both carry m = 3. **Include D11's data-independence reasoning in the protocol text itself**, not merely by reference: both drops are independent of any PSB-2 data (C5's from a schema fact, C1's from PSB-1's already-banked results), neither candidate is ever scored on PSB-2 data, so neither consumes a chance at a PSB-2 false positive and neither may inflate the penalty. This is the difference between a correct ledger and the appearance of a loosened correction, and it must be legible to a reader who was not in the room.

**F7 — Bands reconciled to the ratified slate.** C1 and C5 are gone, so their band drift is moot. For the surviving candidates, ensure §5's preamble describes the slate it actually contains — Rev 1's preamble asserted "banded exit at ≤ 0.30" while its body defined 0.40, and asserted "turnover ≤ 0.17" against Phase 0 §1's ≤ 0.06. Pin the real numbers and delete the contradicting summary claims.

**F8 — Horizon-invariance stated as a pinned assumption.** D10's ratified rationale projects fortnightly power by holding the *monthly* δ and SD fixed while doubling n\*. The 15-day IC is a different random variable from the 30-day IC; its δ and SD are unmeasured. Record this in §9 as an explicit, acknowledged assumption rather than leaving it implicit in a rationale cell. Additionally: fortnightly cadence should *raise* the IC series' AC₁ (adjacent formations overlap, and a 252-day σ barely moves in 15 days), which inflates the simple-t projection. §6/§7's AC₁ > 0.1 trigger and Newey–West columns already exist for this but are **report-only, never gating** — so a fortnightly candidate can clear a frozen 0.80 hurdle on a projection its own reported AC₁ shows is optimistic. Do not change the gating rule (that would be a post-hoc fork); **do** state the exposure plainly in §7 so the operator reads the power number with it in view.

**F9 — C4's formula and prose reconciled.** `s = r_12 − r_1` is not "the 12-month return skipping the most recent month" (that is `(1+r_12)/(1+r_1) − 1`). Decide which construct is intended, pin it, and make the prose match. Also fix the self-contradictory "trailing 1-month return (skip most recent month)" — the trailing 1-month return *is* the most recent month; it is the subtracted term, not a skipped one.

**F10 — §2 pins tidied.** Drop `open` from the Prices pin unless a surviving candidate uses it (none does). Restore PSB-1 §2's `universe_membership` **joined to `universe_eligibility` for `entity`**, or state explicitly why the entity join is intentionally omitted — given the substrate's time-aware entity resolution is the hard-won result of PSB-1 Prompts 2–5, silent omission is a regression in specificity.

**F11 — §8's ranking rationale corrected (new; raised at review disposition).** The slate is now deliberately mixed-cadence, so §8's claim that projected power is "size-invariant across unequal dev windows because it evaluates every candidate on the **common sealed n\***" is **false** — n\* is 84 for C2/C3 and 42 for C4, and power scales with δ√n\*/SD, handing a fortnightly candidate √2 in noncentrality at equal δ/SD.

**Do not re-open the ranking rule.** Power remains the ranking statistic and is still sound: because each candidate's δ and SD are measured at its own cadence (per F8, the 15-day IC is its own random variable), projected power still answers "how likely is this candidate to clear *its own* sealed gate," which is the program's stated objective. What is broken is only the justification text. Correct it to the true distinction: power is invariant to **dev-window length** (the accident PSB-1's F1 actually addressed), **not** to cadence — and cadence-dependence is legitimate because cadence is a design choice, not a data accident. Note this was already imprecise in PSB-1 (182 weekly vs 42 monthly n\*) but never bit, because PSB-1 returned "no winner"; PSB-2 is deliberately mixed-cadence, so it is now load-bearing.

**Preserve §8's divergence-reporting rule** ("if the winner differs across rankings, all are presented and the operator decides") and flag in the text that it is now **expected to trigger**: power ranking favors C2/C3 via n\* = 84, while the evidence floor favors C4, which has the full 2012–2022 monthly dev window against C2/C3's delivery-limited ~28.

### Acceptance criteria

1. Exactly three candidates in §5 and §9's ledger. No C1, no C5, no residue.
2. m = 3 in §8 and §9, **with the data-independence rationale written into the protocol**.
3. One normative cadence table in §3; §5/§7/§9 reference it. No cadence figure restated anywhere.
4. Every n\*, formation count, declared window, turnover, and fee-drag figure is **script-derived and printed**, not hand-carried from Rev 1. The repo rule stands: no hand-edited numbers.
5. The fortnightly grid rule is session-anchored and unambiguous for all 12 months of any year.
6. §9's pinned-parameter list is exhaustive for the three surviving candidates and contains no orphan pins from the dropped two.
7. §8's ranking rationale states the dev-window-vs-cadence distinction and preserves divergence reporting.
8. F8's horizon-invariance assumption and AC₁ exposure are stated, not implied.
9. Rev 1's known contradictions are gone: no "all five constructs," no "monthly only," no "≤ 0.30 band" preamble against a 0.40 body.
10. Status line reads **DRAFT Rev 2**, cites this prompt and D11/D12, and does **not** claim FROZEN.

### Explicitly not authorized

No new candidates or variants (§9 — the ledger is closed at three). No sealed read. No new ingestion (D4 stands; it was re-affirmed, not re-opened, when C5 was dropped rather than rescued). No change to §7's 0.80 hurdle, §8's eligibility conditions, or the gating/report-only split — loosening a hurdle to admit a candidate is the forking path this protocol exists to prevent. No strategy code; nothing lands in `core/strategies/`.

### Outcome

**Rev 2 delivered 2026-07-16. Re-reviewed: DO NOT FREEZE** — one BLOCK, three failed acceptance criteria. See `PSB2_PROTOCOL_INDEPENDENT_REVIEW.md` §"Rev 2 Re-Review". Superseded by Prompt 0R below.

---

## Prompt 0R — Protocol Rev 3 (ISSUED 2026-07-16)

**Task:** Revise `docs/reports/PSB2_PROTOCOL.md` from DRAFT Rev 2 to **DRAFT Rev 3**, closing R1–R6 of the Rev 2 re-review. **Rev 2's substance is accepted** — the slate, cadence, grid rule, C4 formula, and F11 disposition all stand. These are text fixes against work already done: no re-analysis, no re-derivation, no operator decision required. Do not re-open anything Rev 2 settled.

**Status on completion:** DRAFT Rev 3. Returns to Claude for re-review, then the operator. Do not stamp FROZEN.

### Required fixes

**R1 — BLOCK. Write the m = 3 data-independence rationale into §8.** Rev 2 justifies m = 3 only as "corresponds to the three live candidates," which is circular and reads as a loosened correction applied after the two weakest candidates were dropped. The reasoning already exists in D11 — transcribe it into §8 with its logic intact, not as a cross-reference: both drops are **data-independent** (C5's from a schema fact, C1's from PSB-1's already-banked results); neither candidate is ever scored on PSB-2 data; neither consumes a chance at a PSB-2 false positive; therefore neither may inflate the penalty, and deflating by candidates that cannot produce a result would be an arbitrary tax on the ones that can. §9 immutability makes the protocol's own text the permanent record of its defensibility — a reader reconstructing this program's integrity reads §8, not the Phase 0 decision table.

**R2 — Record F8's assumption and exposure.** Add to §9's pinned list the explicit, acknowledged assumption that projected fortnightly power carries δ and SD across horizons (the 15-day IC is a different random variable from the 30-day IC; its δ and SD are unmeasured). Add to §7 the AC₁ exposure in plain terms: fortnightly formations overlap, so AC₁ should rise, inflating the simple-t projection — and because the AC₁/Newey–West columns are report-only, a fortnightly candidate **can clear the frozen 0.80 hurdle on a projection its own reported AC₁ shows is optimistic**. Do not change the gating rule; state the exposure so the operator reads the power number with it in view.

**R3 — Per-candidate declared dev windows in §3.** "Dev window: all candidates on 2012-01-01 → 2022-12-31" is false for C2/C3, which cannot form before 2020-09-04 — that is their *whole* declared window, not a sub-window of a larger one. Follow PSB-1 §3's shape: state each candidate's declared window explicitly (C2/C3: 2020-09-04 → 2022-12-31; C4: 2012-01-01 → 2022-12-31) and drop the "sub-window" framing for C2/C3. This is load-bearing: §7 takes δ/SD from the declared window and §8's evidence floor is computed on the declared-window p.

**R4 — Delete the orphan pin.** §9 still pins "252-day vol window with ≥ 200 obs" — C1's parameter. No surviving candidate computes a volatility window (C2's 252-day window is the *delivery* baseline, separately pinned). Remove it and re-verify the whole §9 list against the three live candidates; an exhaustive ledger containing an unused parameter is stale, not exhaustive.

**R5 — Script-derive the formation count.** "~55 fortnightly formations ceiling" is a hand estimate and is wrong. The count over 2020-09-04 → 2022-12-31 at the pinned `n_symbols >= 200` convention is **56** (28 mid-month + 28 month-end; September 2020's mid-month grid date is 2020-09-15, in range). Recompute with a script, print the output, cite it, and drop the tilde. The repo rule stands: no hand-edited numbers.

**R6 — Reconcile the findings ledger.** The status line and §13 claim "F1–F10". F11 *is* addressed correctly in §7/§8 — credit it. Cite `PSB2_IMPLEMENTATION_PROMPTS.md` §Prompt 0R alongside D11/D12.

### Acceptance criteria

1. §8 contains the data-independence argument in full, legible without reference to any other document.
2. §9 records the horizon-invariance assumption; §7 states the AC₁ exposure.
3. §3 declares a per-candidate dev window; no "sub-window" framing for C2/C3.
4. §9's pinned list maps 1:1 onto parameters the three live candidates actually use — no orphans.
5. The formation count is script-derived, printed, and reads 56.
6. Status line and §13 reconcile to F1–F11 and cite Prompt 0R.
7. Nothing Rev 2 settled is re-opened.

### Next after this prompt

1. Claude re-reviews Rev 3.
2. Operator ratifies → **FROZEN**, §9 immutability attaches.
3. Prompt 1 (Phase 1 harness adaptation + synthetic dev-proof) issued.

### Outcome

**Rev 3 delivered 2026-07-16. Re-reviewed: DO NOT FREEZE CLEAN** — R1 (the Rev 2 BLOCK) closed and closed well; R2's AC₁ half, R3, R5, R6 closed; R5 independently reproduced by executing `scripts/psb2/count_grid_dates.py`. Three localized text defects remain in §7/§9 (S1–S3), none changing a computed number. **S1 originates in this prompt's own R2 wording, not in the implementation.** See `PSB2_PROTOCOL_INDEPENDENT_REVIEW.md` §"Rev 3 Re-Review". Superseded by Prompt 0R2 below.

---

## Prompt 0R2 — Protocol Rev 4 (ISSUED 2026-07-16)

**Task:** Revise `docs/reports/PSB2_PROTOCOL.md` from DRAFT Rev 3 to **DRAFT Rev 4**, closing S1–S3 of the Rev 3 re-review (`PSB2_PROTOCOL_INDEPENDENT_REVIEW.md` §"Rev 3 Re-Review") plus the freeze checklist.

**Rev 3's substance is accepted in full.** R1's data-independence rationale, the per-candidate declared windows, the script-derived counts, §7's AC₁ exposure, and the entire slate/cadence/formula set all stand — verified, including an independent execution of `count_grid_dates.py` that reproduced all four counts. What remains is **three localized text edits in §7 and §9.**

**Status on completion:** DRAFT Rev 4. Returns to Claude for re-review, then the operator. Do not stamp FROZEN.

**Scope discipline:** no formula, hurdle, band, window, cadence, count, or slate entry is in scope. **If a proposed edit would change a number, it is out of scope — stop and say so rather than making it.**

### S1 — §9's horizon-invariance paragraph: delete or replace. **This defect originates in Prompt 0R's R2, not in your implementation of it.**

R2 instructed you to record *"the explicit, acknowledged assumption that projected fortnightly power carries δ and SD across horizons."* **That instruction was wrong.** §7 makes no such assumption: line 109 takes `δ` = the candidate's own dev mean IC and `SD_dev` = its own dev IC SD, each measured at its own cadence. Fortnightly δ/SD → fortnightly n\* = 84 is **horizon-consistent**. You implemented the instruction faithfully; the result is a paragraph that is either **false** (read as describing §7's method) or **vacuous** (read as "the values are unmeasured before the run" — true of every parameter in every protocol).

F8's actual target was **D10's ratified rationale** — the 0.54 → 0.80 projection, which held PSB-1's *monthly* δ = 0.068 / SD = 0.2479 fixed while doubling n\* to 84. That was the rescue projection for the **low-volatility candidate D11 dropped.**

**Do not re-scope the paragraph to D10's cadence choice.** That would pin an assumption describing a dead candidate inside the live protocol's immutable ledger.

Choose one disposition and state why:

- **(a) Delete it.** No live candidate's projection carries δ/SD across horizons, so there is no assumption to pin.
- **(b) Replace it** with an accurate statement: §7's projection is horizon-consistent for every live candidate, and F8's cross-horizon concern was specific to the dropped C1/C5 rescue — moot for C2/C3, whose fortnightly cadence rests on delivery-signal dispersion grounds, not a horizon assumption.

Either way, the §9 entry must be **true of the three live candidates**.

### S2 — §9's "(exhaustive)" list is not exhaustive. Run the sweep R4 asked for.

Prompt 0R's R4 required: *"re-verify the whole §9 list against the three live candidates."* The named orphan (252-day vol window) was deleted; **the sweep was not run.** Two omissions found on review:

- **C4's 12-1 lookback** (`r_12` at *g*−12, `r_1` at *g*−1) — the candidate's entire signal definition.
- **C3's 21-trading-day return horizon** in `r_i(t)`. §9's "252-day delivery baseline ending *t*−21" pins t−21 as the baseline **endpoint** — a different parameter that merely shares the number 21.

**Do not patch in these two.** They are *evidence the sweep was not run*, not a complete list of what it will find. **Derive §9's list from §5's three formula blocks and §3's grid rules directly**, parameter by parameter, and state in your response how you enumerated it. If the sweep surfaces omissions this review did not name, that is the sweep working as intended.

The available defense does not hold: one could argue §9 is a summary and §5 pins the formulas (protected by §9 bullet 2). But **§9 already re-lists C2's formula parameters** — "252-day delivery baseline ending t−21" and "fortnightly delivery mean with ≥ 8 non-NULL" come straight out of C2's formula block. So §9 re-states formula parameters, includes C2's, and drops C3's and C4's. Either the list is exhaustive as labelled, or the label goes.

For the record, this is a **record-integrity** defect, not a protection gap: the parameters *are* protected via §5 + §9 bullet 2, and C4's signal is not unpinned. The problem is a document whose entire authority rests on precise pinning permanently asserting a completeness it does not have.

### S3 — §7's dropped-candidate residue

§7's AC₁ paragraph reads: *"Adjacent fortnightly formations overlap in their trailing **252-day σ** and 252-day delivery baseline."*

No live candidate computes a price-volatility window. The only live σ is C2's **delivery** std over 252 trading days ending *t*−21 — which the same sentence already names as the delivery baseline. So the phrase is C1 residue (inherited from F8's wording, which described C1's price σ) and names one object twice as though it were two.

**Fix only the referent.** The AC₁ exposure argument itself is sound and lands exactly as asked — preserve it intact.

### Freeze checklist (audit-trail integrity, not housekeeping)

1. **Commit `scripts/psb2/count_grid_dates.py`.** §3 cites it as the provenance for 56. A frozen protocol citing a script absent from git has a **broken provenance chain** — the number becomes unverifiable at exactly the moment it becomes immutable. It must land in the same commit as the protocol.
2. **Delete the stray 0-byte file `=`** in the repo root (shell-redirect artifact).

### Acceptance criteria

1. §9 contains no statement that is false or vacuous with respect to the three live candidates.
2. §9's pinned list is **derived from §5/§3** and maps 1:1 onto the live candidates' parameters — no orphans, no omissions. **Your enumeration method is stated.**
3. §7 contains no dropped-candidate residue; the AC₁ exposure argument survives intact.
4. **No formula, hurdle, band, window, cadence, count, or slate entry changed from Rev 3.** The diff touches §7, §9, and the status line only.
5. `count_grid_dates.py` is tracked; the stray `=` is gone.
6. Status line reads **DRAFT Rev 4**, cites this prompt, and does not claim FROZEN.

### Explicitly not authorized

No new candidates or variants (§9 — the ledger is closed at three). No sealed read. No new ingestion (D4 stands). No change to §7's 0.80 hurdle, §8's eligibility conditions or ranking rule, or the gating/report-only split. **No re-opening of R1's §8 rationale, the per-candidate declared windows, or the script-derived counts** — all reviewed, verified, and accepted.

### Next after this prompt

1. Claude re-reviews Rev 4.
2. Operator ratifies → status stamped **FROZEN**, §9 immutability attaches.
3. Prompt 1 (Phase 1 harness adaptation + synthetic dev-proof) issued to DeepSeek V4.

---

## Prompt 1 — Phase 1: harness adaptation + synthetic dev-proof (ISSUED 2026-07-16)

**Task:** Adapt the PSB-1 screening harness to the three constructs pinned in `docs/reports/PSB2_PROTOCOL.md` **§5 (FROZEN Rev 4, `eb3d66f`)**, and produce the synthetic dev-proof that §11.2 requires as the Phase 1 gate.

**Status on completion:** returns to Claude for Lead Review (§11.2), then to the operator to authorize Phase 2. **No candidate runs on real data under this prompt.**

### The governing change: the protocol is frozen

§9 immutability attached at `eb3d66f`. Nothing in §3, §5, §7, §8, or §9 may change — not by you, not by the operator, not by me. A change requires a new battery (PSB-3) with a fresh ledger.

**Your job is to implement the frozen text exactly, not to improve it.** Two consequences that govern everything below:

1. **The code is now the only place a frozen parameter can be silently mis-implemented.** Before the freeze, a wrong constant was a protocol defect the review caught. After it, a wrong constant is a *code* defect that produces authoritative-looking results from a spec nobody violated on paper. That is what this dev-proof exists to prevent.
2. **If any part of §3/§5/§7/§8 is ambiguous or unimplementable as written — STOP and escalate. Do not interpret.** You do not have authority to resolve a frozen ambiguity, and neither do I. Silently choosing a reading is the single failure mode that would void the pre-registration, because the protocol would no longer describe what ran. Escalate to the operator with the exact text and the readings it admits.

### Precondition — the Phase 0 gate (§11.1)

Run `scripts/psb1/certify_substrate.py` (Arm A–D). It must return **0 undocumented violations**. §11.1 is a structural gate: no Phase 1 without a certified substrate. **Capture its output verbatim in the Phase 1 report** — the 0-violations line is part of the gate's audit trail, not merely a precondition you checked.

### Hard constraints

**1. `scripts/psb1/*.py` is read-only.** `screening_harness.py` generated PSB-1's C1–C5 reports — a **closed program** whose results must remain reproducible from this repo. Editing it retroactively invalidates a published result set.

**2. Any PSB-1 machinery PSB-2 reuses must be demonstrably the same code.** §2 pins the harness lineage as inherited "without modification," and that must be **verifiable**, whichever route you take:

- If you **import** from `scripts/psb1/`: `scripts/psb1/` stays git-clean against `eb3d66f`.
- If you **copy** shared machinery into `scripts/psb2/` (CLAUDE.md's copy-first discipline permits this): every copied-and-unchanged function must be **diff-clean against its psb1 original**, and any function you deliberately changed must be named as changed, with the reason.

State which route you took and how you made it verifiable. A silently divergent copy of `evaluate_candidate` or `_power` is the risk here — it would run PSB-2 on machinery that is no longer the certified machinery.

**3. The C1–C5 names collide across batteries, and the constructs differ.** This is a silent-wrong-result hazard, not a style matter:

| Name | PSB-1 (in `screening_harness.py`) | PSB-2 (§5, frozen) |
|---|---|---|
| C2 | residual reversal, weekly (uses market weekly returns) | **delivery z-score**, fortnightly |
| C3 | delivery z, weekly (60-day baseline ending *t*−5) | **delivery-conditioned reversal**, fortnightly |
| C4 | C1×C3 interaction, weekly | **momentum 12-1, monthly, staggered 6-tranche** |

PSB-2's C2 is **not** PSB-1's C2. PSB-1's `score_c2` / `score_c3` / `score_c4` implement **different constructs**. PSB-2's C2 is closest to PSB-1's C3 — but with a **252-day baseline ending t−21 (≥ 150 non-NULL)**, not PSB-1's 60-day ending t−5. Reusing those functions, or their names, silently produces wrong results that look right. Name PSB-2's scorers unambiguously.

**4. Phase 1 touches real data at exactly two points:** `certify_substrate.py`, and `trading_calendar` **dates** for grid verification (pre-2023 dev calendar; the sealed count is §1's dates-only exception). **No candidate score touches real data** — that is Phase 2, after the §11.2 Lead Review. The fence test below stays on synthetic data; do not let it become a third touchpoint.

### What must be built

- **The fortnightly grid** per §3 — "last full session on or before the 15th" + "last full session per month." PSB-1's harness has `weekly_grid` / `monthly_grid` only.
- **The three §5 scorers.**
- **`sealed_grid_count` for fortnightly cadence** (§7).
- **C4's staggered 6-tranche holding** — genuinely new machinery. PSB-1 has banded exit only (`_quintile_sequences(scored_by_date, banded)`). Highest-risk new code in this prompt.

**C4 — keep the two paths separate.** Staggered holding affects **turnover → fees → net spread** (eligibility gate ii) and nothing else. It must **not** touch the score → IC → power path (gates i and iii). The new machinery belongs in the portfolio-simulation layer, not in scoring.

### What the dev-proof must prove

Repo discipline applies: **state each prediction as a falsifiable claim before the run, then run.** Design the planted scenarios yourself — PSB-1's `run_synthetic_devproof.py` is the working template.

**A. Formula fidelity — the core obligation.** Planted-signal recovery is **necessary but not sufficient**: a scorer using a 200-day baseline instead of 252, ending at *t*−20 instead of *t*−21, or thresholding at ≥ 120 non-NULL instead of ≥ 150, would still recover a planted signal and still return ~0 on a null panel. Signal recovery tests the **pipeline**; it does not test whether the code implements the **frozen formula**.

Therefore: on a **tiny hand-constructed panel with exact expected values**, assert one check per pinned §9 parameter — such that a wrong constant makes the assertion **fail on a known input**. §9's ledger is your checklist; it was made exhaustive for exactly this purpose. Cover at minimum: the 252-day baseline and its *t*−21 endpoint; the ≥ 150 and ≥ 8 non-NULL thresholds; C3's 21-trading-day return horizon; C4's g−12 and g−1 lookbacks and its 12-prior-grid-date requirement; the 0.40 band; κ = 5 bp/side; m = 3; the 0.80 hurdle at α = 0.05 one-sided.

If you cannot write an exact expected value for a pinned parameter because §5 admits two readings — **that is the escalation trigger.** Stop and report it.

**B. Grid identity.** The harness's fortnightly grid over 2020-09-04 → 2022-12-31 must be **identical — same count and same dates** — to `scripts/psb2/count_grid_dates.py`: 56 (28 mid-month + 28 month-end, first 2020-09-15, last 2022-12-30). Sealed: 84 fortnightly / 42 monthly. If the harness and frozen §3 disagree, the protocol's declared n is wrong and Phase 2 cannot start. This is the most direct check that the frozen document and the code agree.

**C. Planted-signal recovery.** Each of C2, C3, C4 recovers a planted signal of known direction, and returns ~0 IC on a null panel (no false eligibility).

**D. C3's sign convention.** `s = −r·(1−2p)`: at p = 0 (low delivery) → reversal; at p = 1 (high delivery) → continuation. Plant **both** regimes; show the recovered sign matches §5's stated hypothesis in each. An interaction-term sign error is the classic defect that survives to production looking plausible.

**E. Staggered mechanics.** A name entering a tranche stays until **that tranche's** next rebalance regardless of rank drift (§5 C4); realized turnover ≈ 1/6 per month. **C4's IC is invariant to the holding mechanism** — if staggering changes the IC, that is a bug.

**F. Dev fence.** A load at the pinned cutoff asserts and prints observed `MAX(trade_date) ≤ 2022-12-31`. Plant a 2023 row on a **synthetic** panel and show the fence **raises** — not warns, not filters silently.

**G. Fees and slippage.** Net spread < gross; κ = 5 bp/side on traded notional; era-accurate `delivery_equity_fees`.

**H. Determinism (§10).** Same inputs → **byte-identical** outputs across two runs. **Pin the synthetic panels' RNG seed** — the dev-proof must itself be reproducible.

### Deliverables

- `scripts/psb2/` — the adapted harness and the dev-proof runner.
- `docs/reports/PSB2_PHASE1_DEVPROOF.md` — **script-generated; no hand-edited numbers** (the repo rule, and it applies with particular force to a document certifying a frozen spec).
- Tests, in the shape of `tests/psb1/`.
- Committed as produced (§11.3's git-visible ordering discipline).

### Acceptance criteria

1. `certify_substrate.py` returns 0 undocumented violations; output captured in the report.
2. Reuse of PSB-1 machinery is demonstrably identical code, by the route you declare (psb1 git-clean, or diff-clean copies).
3. PSB-2's scorers are unambiguously named; no PSB-1 scorer is reused for a PSB-2 construct.
4. Fortnightly grid **dates** (not just counts) identical to `count_grid_dates.py`; sealed 84/42.
5. One formula-fidelity assertion per pinned §9 parameter, each failing on a wrong constant.
6. C2/C3/C4 each recover a planted signal; null panel ~0.
7. C3's sign verified in both delivery regimes.
8. Staggered mechanics verified; C4's IC invariant to the holding mechanism.
9. Fence raises on a planted post-fence row.
10. Determinism verified across two runs; RNG seed pinned.
11. Every number in the report script-generated.
12. No candidate score on real data.
13. Predictions stated before results.

### Explicitly not authorized

**No change to the frozen protocol** (§9) — ambiguity escalates, it does not get resolved in code. **No sealed read.** **No real candidate runs** (Phase 2, and only after the §11.2 Lead Review). **No strategy code; nothing in `core/strategies/`.** **No new ingestion** (D4). **No edits to `scripts/psb1/`.** No new candidates or variants — the ledger is closed at three.

### Next after this prompt

1. Claude Lead Review of the harness + dev-proof (the §11.2 gate).
2. Operator authorizes Phase 2.
3. Prompt 2 — candidate runs in the §11.3 order: **C2 → C3 → C4**, one report per candidate, committed as produced.

### Outcome

**Delivered 2026-07-16 (`8a95a28`, `f961d19`). Lead Review: BLOCK — Phase 1 does not pass §11.2.** Five of thirteen acceptance criteria unmet (5, 6, 7, 8, 10) while the dev-proof reported all-PASS: the S1 determinism proof hashes empty output from two crashed subprocesses; the signal-recovery arm plants a signal no candidate can read; arms D and E were omitted entirely; the fidelity suite is mutation-insensitive. Four correctness defects behind the green tests. See `PSB2_PHASE1_LEAD_REVIEW.md`. Superseded by Prompt 1R below.

---

## Prompt 1R — Phase 1 remediation: make the dev-proof provable (ISSUED 2026-07-16)

**Task:** Close every finding in `docs/reports/PSB2_PHASE1_LEAD_REVIEW.md` and re-submit the Phase 1 gate deliverable — the harness (`scripts/psb2/`), the fidelity suite (`tests/psb2/`), and the regenerated `docs/reports/PSB2_PHASE1_DEVPROOF.md`.

**Status on completion:** returns to Claude for Lead Review (§11.2), then to the operator to authorize Phase 2. **No candidate runs on real data under this prompt.** Every constraint in Prompt 1 carries forward unchanged — the protocol is still FROZEN at `eb3d66f`, `scripts/psb1/` is still read-only, ambiguity still escalates rather than getting resolved in code.

### What is accepted — do not re-open

Reviewed, verified, and standing. Re-deriving any of these wastes the round and risks regressing them:

- **The reuse route.** Importing from `scripts.psb1.screening_harness` keeps `scripts/psb1/` git-clean and verifiable. `git status` confirms it. Keep it.
- **Scorer naming.** `score_c2_psb2` / `score_c3_psb2` / `score_c4_psb2` correctly avoid the cross-battery C1–C5 collision Prompt 1 flagged.
- **`BONFERRONI_M = 3`**, correctly overriding PSB-1's 5.
- **C4's 12-1 formula** — `(1 + r_12) / (1 + r_1) − 1` with grid-index lookbacks (`g−12`, `g−1`) rather than calendar-day approximation. Exactly §5. The subtle part, done right.
- **C3's ordering** — percentile ranks across all C2-scored names *before* dropping names lacking a 21-day return. Matches §5's "among names scored at *t*".
- **Per-candidate `ppy`** (24/12) and `sealed_grid_count_psb2`'s cadence dispatch — §7's mixed-cadence n\* implemented correctly.
- **The dev fence.** Real and passing.

### The governing problem: the suite was shaped to pass

This is the finding that produced every other finding, and it is the one thing this prompt exists to fix.

Prompt 1 asked for the right things in the right words. §A required assertions *"such that a wrong constant makes the assertion **fail on a known input**."* §C required planted-signal recovery. §H required byte-identical outputs. The delivery **claimed** all three and **delivered** none, and reported 10/10 PASS and all-predictions-PASS while doing so.

The mechanism was not one bug. It was a consistent pattern of **choosing the assertion that passes over the assertion that discriminates**:

- Determinism was proven by hashing two crashed subprocesses' empty stdout — `SHA256("") = e3b0c44298fc1c14`, printed for both seeds, reported "IDENTICAL".
- Signal recovery was proven on a panel where the signal is planted in prices and every candidate reads `deliv_pct`, which is independent noise — so C2's IC is ≈0 **by construction**, and the report's own table shows C3's null IC (0.0350) beating its signal IC (0.0296).
- Formula fidelity was proven by five assertions of the form `assert H.KAPPA == 0.0005` — a literal compared to a literal — and four more that pass under mutation of the very parameter they name.
- Arms D and E were not built at all.
- The one prediction that could have failed the signal arm was never written; the three that were written (`null |IC| < 0.05`, `fenced <= cutoff < unfenced`, `net < gross`) cannot fail against a broken harness.

**A test that cannot fail is not evidence. It is worse than no test, because it converts unknown risk into false confidence** — which is exactly the lesson PSB-1 paid for across ten review rounds and recorded in `PSB1_SUBSTRATE_CERTIFICATION.md`. Every one of the four correctness defects below sat **inside the declared scope of a test that reported PASS.**

So the standard for this round is not "add tests." It is: **for every claim the report makes, the run must have been capable of contradicting it.** Where you cannot construct a discriminating check, say so and escalate — an honest gap is worth more than a green tick that means nothing.

### Part 1 — The dev-proof (the §11.2 gate)

**1R-1 — S1 determinism must be capable of failing.** `run_devproof.py:168-181` passes `env={"PYTHONHASHSEED": hs}`, which **replaces** the environment rather than extending it. The stripped environment drops what Python needs to locate site-packages; `import numpy` fails; `subprocess.run` without `check=True` does not raise; `stderr` is captured and never read; `stdout` is `""`. Both digests are the empty-string hash.

Fix: `env={**os.environ, "PYTHONHASHSEED": hs}`; assert `returncode == 0` and surface `stderr` on failure; **assert the digest is not the empty digest.** A proof that reports success when its subject never ran is not a proof. Verify by deliberately breaking the child once and confirming S1 reports FAIL.

**1R-2 — Plant the signal in the feature each candidate reads.** `run_devproof.py:59-97` plants into forward prices while `deliv_pct = rng.uniform(0.2, 0.7)` is drawn identically in both panels. No delivery-scoring candidate can see it.

Fix: for **C2/C3**, elevate `deliv_pct` for the names that subsequently outperform, so the delivery z-score carries real information. For **C4**, plant a persistent 12-1 trend in the price path (note the current planting writes single-cell spikes *after* the random walk is generated, so the jump reverts the next day and never propagates — build the path with the signal in it, don't overwrite cells afterward).

Then state the recovery prediction **before** the run, per the repo's falsifiable-prediction rule. Suggested and sufficient: **signal-arm mean IC > +0.10 and ≥ 3× the null-arm |IC|, for each of C2, C3, C4** — and it must appear in the Predictions table where it can fail. If a candidate cannot clear it, that is a result to report, not a threshold to lower.

**1R-3 — Build the two omitted arms.** Prompt 1 required A–H. The report contains A, B, C, F, G, H. **D and E were never built.**

- **D — C3's sign convention.** `s = −r·(1−2p)`: at p = 0 (low delivery) → reversal; at p = 1 (high delivery) → continuation. Plant **both** regimes and show the recovered sign matches §5's hypothesis in each. The existing `test_c3_21_day_return_horizon` plants one regime and asserts both names score positive — it does not test the split.
- **E — Staggered mechanics.** A name entering a tranche stays until **that tranche's** next rebalance regardless of rank drift; realized turnover ≈ 1/6 per month; **C4's IC is invariant to the holding mechanism** — if staggering moves the IC, that is a bug. This is the arm that would have caught 1R-6, on the code Prompt 1 called "the highest-risk new code in this prompt."

**1R-4 — Strengthen the near-unfalsifiable predictions.** `net < gross` holds for any non-zero fee model, correct or not. Add a check with teeth: assert the fee on a **known** trade value at a **known** date equals the era-accurate `delivery_equity_fees` figure computed independently, and assert κ contributes exactly 5 bp/side of traded notional. The **turnover** column is the informative number and is currently unasserted — C2 reports 0.4677 against §3's ~0.15 design premise. On i.i.d. synthetic data high turnover is expected and is **not** a defect; but §3's turnover premise is what the entire fee-survivability case rests on, so E's ≈1/6 check must actually assert, and C2/C3's banded turnover should be measured on a panel with a persistent signal where the band can bite.

**1R-5 — The §11.1 gate must be enforced, not narrated.** The report prints the certifier's `CERTIFICATION INCOMPLETE - HALT items above must be resolved` and `Arm B | HALT | 4 splice fabrications`, then editorializes: *"resolved by fragmentation test."* Three problems: `certify_substrate.py:265` reads `b_halt = arm_b.splices  # ALL splices HALT (none dispositioned)` — Arm B is zero-tolerance **by design**, so "resolved" contradicts the suite's contract and has no register entry behind it; `_certify()` is **dead code**, never called, and `main()` reads a possibly-stale `certify_output.txt` off disk; and the HALT never enters `all_pass`.

Fix: reconcile the 4 splices against the **committed** disposition register. Then either they are dispositioned — in which case Arm B reports "(4 dispositioned, 0 undocumented)" like Arms A/D and the gate passes honestly — or they are not, **in which case §11.1 is not satisfied and you stop and escalate.** Call `_certify()` or delete it; gate on its result. **Do not resolve this by editing the report's prose.** Note `docs/reports/PSB1_SUBSTRATE_CERTIFICATION.md` currently carries an uncommitted modification in the working tree; establish what it is before relying on it.

**1R-5b — The fence arm: report the limitation truthfully. This one is my defect, not yours.**

Prompt 1 §F told you to *"plant a 2023 row on a **synthetic** panel and show the fence **raises** — not warns, not filters silently,"* and §4 told you the fence test *"stays on synthetic data."* **Both instructions were unsatisfiable, and you were right not to force them:**

- `load_panel` **cannot** raise on a post-fence row. It filters at `screening_harness.py:128` (`WHERE a.trade_date<=?`) and asserts at line 145 — downstream of the filter, hence structurally unreachable. A planted 2023 row is silently dropped. `scripts/psb1/` is read-only, so this is not yours to fix.
- `fence_check` is **by design** a real-store touch: *"The ONLY permitted real-store touch in Phase 1: dates + counts only... evidence that sealed data is physically present and was excluded, not merely that a WHERE clause filtered (Lead Review S2/S3)."* PSB-1's Lead Review already found this tautology and built `fence_check` as the answer. §4's synthetic-only instruction contradicts the control's purpose.

**Calling `fence_check()` on the real store was the right call** and it stands — dates and counts only, no prices, symbols, or scores; on the best reading not a §1 breach, since §1 prohibits loading *price/delivery/volume/universe data* and an aggregate loads none of those.

What is required is only **honesty about what the fence proves**:

1. State in §F as a **known limitation** that `load_panel`'s in-loader assert is tautological (filter precedes assert) and that the real protection is `fence_check`'s three-way `fenced <= cutoff < unfenced`. The current line *"Sealed fence OK: observed MAX(trade_date)=... <= cutoff"* printed from a filtered load implies a check that did not occur — that is the same shape as every other finding in this round, even though here the underlying control is sound.
2. **Optional, and report whatever you find:** run the planted-row experiment on a synthetic panel anyway and report truthfully that the row is filtered, not raised. A documented negative is worth more than an unstated assumption. **Do not "fix" `load_panel` to make it raise** — psb1 is read-only and that would invalidate PSB-1's published results.
3. §1's sole-exception clause names `trading_calendar` only, while `fence_check` reads `equity_bhavcopy_adjusted` metadata. The protocol is FROZEN and cannot be edited. **Flag this for operator disposition in your response** — do not resolve it yourself.

### Part 2 — Correctness defects

**1R-6 — `date_ic` is fed pre-imputed forwards** (`harness.py:425-438`). PSB-1's `date_ic(s_all, fwd_all)` **expects `None`** in `fwd_all` and does the §4.2 imputation itself. PSB-2 substitutes `worst_fwd` first, so `present` filters nothing: **`ic_primary` is computed over the imputed vector** — and that IC is §8(i)'s eligibility statistic and §7's power δ — while `ic_primary == ic_imputed` identically collapses the §4.2 robustness column to a duplicate and pins `sign_flag` to `False` forever.

Fix: pass forwards with `None` preserved, exactly as PSB-1 does at its lines 736-737. Delete the misaligned `s_all`/`fwd_all` draft at `harness.py:409-417` (score appended when forward is `None`, forward not — the lists have different lengths). **This is latent on a dense synthetic panel** — `_ret` is never `None`, so imputation never fires. It activates on real data at delistings and universe exits. Your regenerated dev-proof must include a panel with **missing forwards** so this path is exercised; a §4.2 column that cannot differ from the primary is not a robustness check.

**1R-7 — C2's fortnight window is improvised** (`harness.py:146-164`). §5 pins `dp_i(t) = mean of deliv_pct over fortnight's whole trading days ending t (≥ 8 non-NULL)`. The code scans back **20** trading days and stops at **15** non-NULL:

```python
for j in range(cal_idx, max(cal_idx - 20, -1), -1):
    ...
    if len(recent_dps) >= 15:
        break
```

Neither 20 nor 15 is in §9's exhaustive pinned list; both were invented at implementation time, and the window is systematically longer than a fortnight (~10-11 trading days). The comments above the code ("the last ~10 trading days") contradict the code below them.

Root cause is structural: `score_c2_psb2(panel, t)` cannot see the grid, so it cannot know the prior grid date. Fix: pass the fortnightly grid (or the prior grid date) into the scorer and average `deliv_pct` over trading days in **`(prev_grid_date, t]`**, requiring ≥ 8 non-NULL. §9 immutability is not yet breached — no candidate result exists — but it attaches the moment one does.

**If you believe §5's "fortnight's whole trading days ending t" admits more than one reading, that is the escalation trigger from Prompt 1 — stop and report it. Do not choose a reading.**

**1R-8 — C4 drops held names that stop scoring** (`harness.py:308-309`). §5: *"A name held in any tranche remains held until its tranche's next rebalance date, regardless of rank drift."* But `if e in fwd_map` filters out any held name not scored at `t` — left the universe, lost 12 prior grid dates, missing forward. Its return for the period vanishes, and since `_simulate` derives `cur` from the holdings list, it is charged a phantom SELL and a phantom BUY if it later re-scores, with the intervening return silently discarded. This corrupts §8(ii)'s net spread in both directions.

Fix: hold the name at its actual forward return until its tranche rebalances. A genuinely untradeable name exits through the §4.2 imputation rule, not by disappearing.

*(For the record: the union-of-6-cohorts breadth is **not** a defect — an overlapping 6-month-hold portfolio holding ~6 cohorts' worth of names is inherent to the construct. Do not "fix" it. The equal-weight-across-union vs. average-of-cohort-means distinction diverges only for names held in multiple tranches; if you change it, say so and why.)*

**1R-9 — The exit band is not plumbed** (`harness.py:343, 350, 476`). `exit_band = C2_EXIT_BAND` is assigned and **never passed**; `_quintile_sequences(scored_by_date, banded=True)` takes no band parameter and reads PSB-1's module-level `C5_EXIT_BAND`. PSB-2's `C2_EXIT_BAND`/`C3_EXIT_BAND` are read by **no code path**. Both are 0.40 today, so behavior is accidentally correct — and `test_exit_band` asserts the dead constant and reports PASS.

Fix: add an explicit band parameter and pass PSB-2's constant. Since `scripts/psb1/` is read-only, the honest routes are a thin PSB-2 wrapper or a diff-clean copy into `scripts/psb2/` with the parameter added and the change declared per Prompt 1's constraint 2. **State which route you took.** An unparameterized borrow of a PSB-1 constant is a hidden coupling, not the "without modification" lineage §2 pins.

### Part 3 — The fidelity suite

**1R-10 — Rebuild it so every test can fail.** The commit message claims coverage of "every pinned §9 parameter with exact expected values"; the docstring claims "a wrong constant makes the assertion fail on a known input." **Both are false for 9 of 10 tests.**

*Five are constant tautologies* — `test_exit_band`, `test_staggered_tranches`, `test_power_hurdle`, `test_bonferroni_m`, `test_slippage_kappa` assert only `H.X == literal`. They exercise no harness behavior. Delete them or make them behavioral: assert the band **changes which names are held**, that κ **moves the net return by 5 bp/side**, that the hurdle **drops a candidate at 0.79 and passes it at 0.81**.

*Four are mutation-insensitive* — each passes under mutation of the parameter it names:

| Test | Why it cannot fail |
|---|---|
| `test_c2_252_day_baseline_ending_t21` | Plants `dp=0.80` across **20** flat recent days, so any window length yields mean 0.80. Docstring says "z ≈ 16.7"; assertion is `z > 1.0`. Cannot detect 1R-7. |
| `test_c2_fortnightly_mean_min_8` | Baseline region holds ~30 non-NULL against the required 150, so the entity is skipped by the **baseline** rule. Set `DELIV_MEAN_MIN = 5` and it still passes. |
| `test_c3_21_day_return_horizon` | Every close is 100.0 except at `t`, so any horizon *k* gives `r = 110/100 − 1`. |
| `test_c4_lookback` | All off-grid closes are 100.0 and `t_12` is *set* to 100.0 — a no-op update. Any *k* ≠ 1 yields `r_12 = 0.20`. Sensitive to `g−1` only. |

**The standard: vary the planted data along the axis the parameter indexes.** Vary `deliv_pct` by day so a wrong window shifts the mean. Vary closes along the whole path so a wrong horizon shifts the return. Give the baseline ≥150 valid observations so the min-8 branch is the only one that can fire. Then **verify by mutation**: change the constant, watch the test fail, change it back. A test you have not seen fail is a test you have not written.

Assert **exact expected values**, not directional bounds — §9's ledger is the checklist, and it was made exhaustive for precisely this purpose.

**1R-11 — Grid identity must use the real calendar.** `run_devproof.py:209-212` builds the grid from `_bday_span(...)`, a holiday-free Mon-Fri calendar — not `trading_calendar` at the pinned `n_symbols >= 200` convention. The counts 56/132/28 are arithmetically forced for *any* calendar with a session on each side of the 15th, so they cannot fail; the date assertions are validated only against the fake calendar. Prompt 1's criterion 4 requires the **dates**, not just counts, identical to `count_grid_dates.py`. Read the real `trading_calendar` (dates only — §1's stated exception) and assert the full date list.

### Part 4 — Hygiene (non-blocking; fold into this round)

`q1_q5` hardcoded `0.0` with `botq_seq` computed and discarded — PSB-1's gross Q1-Q5 column is silently zero for every candidate; decide whether PSB-2 reports it and either wire it or drop the field. `DEV_HI` imported then shadowed (`harness.py:44, 81`). Unused imports: `scipy.stats as ss`, `sealed_grid_count`, `CAP`, `POWER_TIE_BAND`. The module docstring claims `_day_forward` and `BONFERRONI_M` are "imported unchanged from PSB-1" — neither is. `_ret` recomputed per name in the imputation loop. `.get(t_21, -1)` defaults silently yield an empty range → a name skipped without a signal; a missing calendar position should raise. `tp` computed and unused, `panel` unused in `_staggered_sequences`, and `g_idx + 1 >= len(...)` silently drops the last formation. `fortnightly_grid` double-appends if a month's last session falls on or before the 15th (unreachable on the NSE calendar; one guard closes it). `tests/psb2/run_quick.py` is a debug runner still in the tree — `f961d19` removed two such artifacts and missed this one, and §A of the report shells out to it. `_build_panel` inserts row-by-row (~105k `con.execute` calls, the bulk of the 391s runtime) while `executemany` is already used in the same file.

### Acceptance criteria

1. S1 inherits the environment, asserts `returncode == 0`, rejects the empty digest, and has been **observed to FAIL** when the child is deliberately broken.
2. The signal is planted in the feature each candidate reads; a recovery prediction is stated **before** the run and appears in the Predictions table.
3. Arms D and E exist and report; C3's sign verified in **both** delivery regimes; C4's IC verified invariant to the holding mechanism; turnover ≈ 1/6 asserted.
4. `date_ic` receives `None`-preserving forwards; the dev-proof includes a **missing-forward** panel; primary and §4.2 columns are shown to **differ** on it.
5. C2's window is `(prev_grid_date, t]` with ≥ 8 non-NULL. **No unpinned constant appears in any scorer.**
6. C4 holds names to their tranche's rebalance regardless of rank drift; no phantom churn.
7. The 0.40 band is plumbed and read by the code path that applies it; the route (wrapper or diff-clean copy) is declared.
8. Every fidelity test **fails under mutation of the parameter it pins** — verified by mutation, and the verification is stated. No test asserts a constant against a literal.
9. Grid identity asserts the full **date list** against the real `trading_calendar`.
10. §F states `load_panel`'s tautological assert as a known limitation and names `fence_check` as the actual protection; the §1 sole-exception question is flagged for operator disposition, not resolved.
11. §11.1 Arm B is reconciled against the committed disposition register and gated in code — or escalated. Not resolved in prose.
12. Every number in the report script-generated. No hand-edited numbers.
13. No candidate score on real data.
14. Prompt 1's constraints hold: `scripts/psb1/` git-clean, protocol untouched, ambiguity escalated.

### Explicitly not authorized

**No change to the frozen protocol** (§9) — 1R-7 in particular must be escalated, not interpreted, if §5 admits two readings. **No sealed read.** **No real candidate runs** (Phase 2, after the §11.2 Lead Review). **No edits to `scripts/psb1/`.** **No new candidates or variants** — the ledger is closed at three. **No strategy code.** **No new ingestion** (D4).

**And specific to this round: no weakening of a check to make it pass.** If the signal arm cannot clear the recovery prediction, report the failure — do not lower the threshold. If a fidelity assertion is hard to construct exactly, escalate — do not fall back to a directional bound and call it fidelity. The entire cost of this round was assertions chosen for passing over discriminating; repeating that pattern to clear this prompt would be the same defect wearing a different mask.

### Next after this prompt

1. Claude Lead Review of the remediated harness + dev-proof (the §11.2 gate, second attempt).
2. Operator authorizes Phase 2.
3. Prompt 2 — candidate runs in the §11.3 order: **C2 → C3 → C4**, one report per candidate, committed as produced.

### Outcome

**Delivered 2026-07-16 (`5671026`; debug cleanup `947b99a`). Lead Review Round 2: BLOCK — but the round did its job.** The dev-proof **reported FAIL** rather than tuning the threshold: the culture fix landed. The remaining blocker is scaffolding, not the harness — the C2/C3 planted boost cancels exactly in the forward return, so those arms were never given a signal to find, while C4 (planted correctly) recovers at IC 0.1147 vs null −0.0144 on the same pipeline. Fence disclosure, real-calendar grid identity, and the four correctness fixes all landed. Three criteria self-declared pending. See `PSB2_PHASE1_LEAD_REVIEW_2.md`. Superseded by Prompt 1R2 below.

---

## Prompt 1R2 — Phase 1 Round 3: give the C2/C3 arms a signal to find (ISSUED 2026-07-16)

**Task:** Close R2-1 … R2-8 of `docs/reports/PSB2_PHASE1_LEAD_REVIEW_2.md` and finish the items your Round 2 summary listed as pending. Re-submit the Phase 1 gate deliverable.

**Status on completion:** returns to Claude for Lead Review (§11.2, third attempt), then to the operator to authorize Phase 2. **No candidate runs on real data.** Every Prompt 1 and Prompt 1R constraint carries forward: protocol FROZEN at `eb3d66f`, `scripts/psb1/` read-only, ambiguity escalates rather than getting resolved in code.

**This is a smaller prompt than 1R.** Most of it is finishing work you have already scoped. One item is a genuine blocker, and the fix is already written — in your own file.

### Start here: you did the hard part right

Round 1's dev-proof reported all-PASS on a harness that could not have failed it. **Round 2's stated a prediction, ran, and published `FAIL` against its own gate.** That is the single most valuable thing in the round, it is exactly what 1R asked for — *"a result to report, not a threshold to lower"* — and it is what let this review find a real defect instead of shipping a green tick. Hold that line in Round 3: several items below will surface uncomfortable numbers, and the correct response to every one of them is to report it.

**Accepted; do not re-open, do not re-derive:**

- The honest FAIL reporting and the recovery prediction in the table (criterion 2, structurally met).
- **The fence disclosure** (§F) — the `load_panel` tautology stated as a known limitation, `fence_check` named as the real protection, the §1 sole-exception question flagged for **operator** disposition rather than resolved. Exactly right (criterion 10).
- **Grid identity against the real `trading_calendar`** — 56/132/28, first/last dates, all PASS (criterion 9).
- **The four correctness fixes** (1R-6 `None`-preserving forwards, 1R-7 `(prev_grid_date, t]`, 1R-8 held-name retention, 1R-9 explicit band parameter with the route declared).
- **CSV `COPY`** data generation (391s → 38s).
- Everything accepted in Prompt 1R's "What is accepted" list still stands.

### R2-1 — BLOCKER: the C2/C3 planted signal cancels exactly. The fix is in your file.

`run_devproof.py:59-73` builds a random walk, then overwrites price at each grid date:

```python
price[i, tp_idx] = price[i, tp_idx - 1] * (1 + boost)
```

`fwd_fg` maps **every** grid date to its successor, so every grid date but `fg[0]` is overwritten. For a formation `t = fg[i]` and its forward `tp = fg[i+1]`, **both are grid dates and both carry the same factor**:

```
price(t)  = W(t−1)  × (1 + boost)
price(tp) = W(tp−1) × (1 + boost)

fwd = price(tp)/price(t) − 1 = W(tp−1)/W(t−1) − 1        ← (1 + boost) cancels
```

The boost divides out for **54 of ~55 formations**. C2's delivery z-score is being correlated against the bare random walk. That is the whole of the 0.0044 signal IC — **not evidence about the scorer.**

Secondary defect, same lines: the overwrite runs *after* the walk is generated, so `price[:, tp_idx+1]` was already computed from the un-boosted cell. The boost is a one-day spike that reverts and never propagates. 1R warned about exactly this — *"don't overwrite cells afterward"* — and the warning was applied to the C4 branch but not to C2/C3.

**The template is your own C4 branch** (`run_devproof.py:74-79`): drift added to the per-step return, compounding through the path, never overwritten. It is the only scenario built that way and the only one that passes. Build C2/C3's return signal the same way — a per-step drift over `(t, tp]` for the names that should outperform, so the signal survives into `price(tp)/price(t)`.

### R2-2 — Make the delivery plant a per-date signal, not a constant-group ramp

`run_devproof.py:87-91` ramps `deliv_pct` from 0.10 → 0.70 across the whole calendar for `sig_set = entities[:n_sig]` — **fixed membership for all time**. Two problems that will persist even after R2-1:

1. **A ramp is a trend; C2 detects an anomaly.** C2 measures recent-fortnight mean against a 252-day baseline ending *t*−21. A linear ramp yields a near-constant gap while inflating the baseline σ — a flat z ≈ +0.5 for every `sig_set` name at every date, with no within-group dispersion to rank on.
2. **Constant membership degenerates the signal to group identity.** C2 exists to find a name whose delivery is abnormal *right now*.

Fix: hold `deliv_pct` stationary (0.35 + noise) for everyone, then at each formation `t` elevate it over `(prev_grid, t]` **for the names that will outperform over `(t, tp]`** — with that outperformance built into the price path per R2-1. The two plants must be **coupled to the same per-date name set**; that coupling is what makes the recovery prediction meaningful.

### R2-3 — Report the S1 result

The report's §H says *"See S1 section below (run via `_s1_child.py`)"* — **there is no S1 section below.** The next heading is §F. No digest, no comparison, no verdict, anywhere. Your summary also lists `_s1_child.py` as pending, so it is unclear the child runs at all.

Criterion 1 requires more than working code: the proof must have been **observed to FAIL** when the child is deliberately broken. Land `_s1_child.py`, report both digests and the verdict, and state the deliberate-break observation. Round 1's S1 was vacuous; Round 2's is absent. Unreported is not proven.

### R2-4 — Restore the null prediction and diagnose the sign

C2 null IC **−0.0687**, C3 **−0.0811**. Prompt 1's C-P1 required `null |IC| < 0.05`; both breach it — and **the null prediction is no longer in the report**. Round 1's Predictions table carried C-P1/F-P1/G-P1; Round 2's has only the recovery prediction. A bound stopped being asserted at exactly the point it started failing. I take that as inadvertent, and it is still the Round 1 pattern in miniature.

Restore the null prediction to the Predictions table and let it fail if it fails. Then diagnose: at `N_ENTITIES = 20` the per-date Spearman SD ≈ 0.23, so SE over ~55 dates ≈ 0.031 and −0.069 is ≈ 2.2 SE — reachable by one unlucky seed, but both candidates lean the same way, which is what a systematic bias looks like. **Check it against a second seed before concluding.** If it is seed luck, say so with the evidence; if it is bias, that is a finding.

Also restore the panel to **30 entities / 3500 days** unless you can show the CSV `COPY` win survives at that size (it very likely does — the old cost was 105k per-row `INSERT`s, not the row count). At 20 entities a quintile is 4 names and every IC in the report is noisier than it needs to be.

### R2-5 — The fidelity suite (1R-10, still open)

Round 1's report had `## A — Formula-Fidelity Tests`; **Round 2's report has no §A at all.** The tautological suite was correctly condemned and nothing replaced it — coverage went from misleading to absent. This is the criterion that guards the frozen §9 parameters, and Prompt 1's framing is unchanged: after the freeze, *a wrong constant is a code defect that produces authoritative-looking results from a spec nobody violated on paper.*

Build it per 1R-10, unchanged: exact expected values; vary the planted data along the axis each parameter indexes; **verify by mutation** — change the constant, watch the test fail, change it back — and state that you did. No test may assert a constant against a literal. **Criterion 8.**

### R2-6 — Arms D and E (1R-3, still open)

- **D — C3's sign in both delivery regimes.** p = 0 (low delivery) → reversal; p = 1 (high delivery) → continuation. Plant both; show the recovered sign matches §5 in each. R2-2's per-date coupling makes this straightforward to construct.
- **E — Staggered mechanics.** A name stays in its tranche until *that tranche's* rebalance regardless of rank drift; turnover ≈ 1/6 per month **asserted**; C4's IC invariant to the holding mechanism. This is the acceptance test for 1R-8 and for the code Prompt 1 called "the highest-risk new code in this prompt" — it is the check that would confirm your own fix independently.

**Criterion 3.**

### R2-7 — The missing-forward panel (criterion 4)

1R-6's code fix is reported done, but nothing demonstrates it. Add a panel with **missing forwards** (delisting / universe exit) and show the primary and §4.2-imputed columns **differing**. A §4.2 column that cannot differ from the primary is not a robustness check — that was the Round 1 defect, and only this panel proves it is gone.

### R2-8 — Make the report's stamp true

`PSB2_PHASE1_DEVPROOF.md:2` reads **"Commit `f961d19`"** — the *pre-remediation* commit. `run_devproof.py` captures `git rev-parse HEAD` at runtime, so the report was generated before the work was committed and permanently cites code that lacks the changes it describes. Regenerate after commit, or stamp `git describe --dirty` and say so. For a script-generated artifact whose authority is its provenance, the stamp must be true.

Also: **`947b99a` is not the remediation** — it only deletes debug files; the work is `5671026`. Cite the right commit in your Round 3 summary.

### Housekeeping (fold in)

`tests/psb2/run_quick.py` cleanup (self-declared pending). `_s1_child.py` as a proper standalone file (covered by R2-3). Any remaining Prompt 1R Part 4 hygiene items not yet closed.

### Scope discipline

**R2-1 and R2-2 are edits to `run_devproof.py` scaffolding only.** No scorer, no formula, no pinned constant, no §9 parameter is in scope. **If a proposed fix would change one, stop and escalate — that is the trigger, not the fix.**

This matters more than usual right now: the C2/C3 arms currently fail, and the tempting reading is "the scorer is wrong." **That reading is not supported.** The arms were correlating against a cancelled signal, and C4 recovers on the same pipeline. Fix the plant first, then read the result. If C2/C3 still fail against a correctly-planted, correctly-coupled signal, **that is a real finding — report it and stop.** Do not adjust a scorer to make an arm pass.

### Acceptance criteria

1. C2/C3 return signal built into the price path; the planted boost survives into `price(tp)/price(t)`.
2. `deliv_pct` plant is per-date and coupled to the same names the return plant favors; baseline stationary.
3. C2, C3, C4 each clear the stated recovery prediction — **or the failure is reported with the plant demonstrated correct.**
4. S1 reports both digests and a verdict, and has been **observed to FAIL** on a deliberately broken child.
5. Null prediction restored to the Predictions table; the −0.07/−0.08 sign diagnosed against a second seed.
6. Panel restored to 30 entities / 3500 days, or the reduction justified with timings.
7. Fidelity suite rebuilt, mutation-verified, verification stated; no constant-vs-literal assertions.
8. Arms D and E exist and report; C3's sign verified in both regimes; C4's IC invariant to holding; turnover ≈ 1/6 asserted.
9. Missing-forward panel shows primary ≠ §4.2-imputed.
10. Report stamp is true to the committed code.
11. Every number script-generated. No hand-edited numbers.
12. No candidate score on real data.
13. No scorer, formula, or pinned constant changed. Ambiguity escalated.

### Explicitly not authorized

**No change to the frozen protocol** (§9). **No sealed read.** **No real candidate runs.** **No edits to `scripts/psb1/`.** **No new candidates or variants.** **No strategy code.** **No new ingestion** (D4).

**And, carried forward from 1R because it is the standing rule of this program: no weakening a check to make it pass.** If an arm fails against a correct plant, that is a result. If a fidelity assertion resists exact construction, escalate. Round 2 honored this — keep honoring it.

### Next after this prompt

1. Claude Lead Review (the §11.2 gate, third attempt).
2. Operator authorizes Phase 2.
3. Prompt 2 — candidate runs in the §11.3 order: **C2 → C3 → C4**, one report per candidate, committed as produced.

### Outcome

**CONDITIONAL PASS** at `c0dfb92` (`docs/reports/PSB2_PHASE1_LEAD_REVIEW_3.md`, amended 2026-07-17). The substantive §11.2 gate is met: the harness recovers a planted signal in all three arms at 4–33σ. Four items remain — R3-1 … R3-4 — carried into Prompt 1R3.

---

## Prompt 1R3 — Phase 1 close-out: assert what the labels claim (ISSUED 2026-07-17)

**Task:** Close R3-1 … R3-4 of `docs/reports/PSB2_PHASE1_LEAD_REVIEW_3.md` (amended 2026-07-17). Re-submit for a diff check, not a full review round.

**Status on completion:** returns to Claude for a **diff check** (§11.2 is substantively met — see below), then to the operator to authorize Phase 2. **No candidate runs on real data.** Every Prompt 1, 1R and 1R2 constraint carries forward: protocol FROZEN at `eb3d66f`, `scripts/psb1/` read-only, ambiguity escalates rather than getting resolved in code.

**This is the smallest prompt in the sequence.** Four items. Three are half-hour fixes. One — R3-4 — is a real defect I missed in the first review pass, and it is the only item that touches a live code path.

### Start here: the gate is met, and three of these carry corrections to my own specs

**Round 3 passed the thing that matters.** R2-1 — the Round 2 blocker — is closed decisively: you diagnosed the cancellation from the review, rebuilt the plant on the C4 template rather than patching it, and the recovery numbers moved from noise to 4–33σ. The determinism proof is real, the §4.2 imputation path is live, and the fidelity suite drives the harness instead of restating constants to itself. **You are not being asked to re-litigate any of that.**

Three of the items below carry corrections to my own specs, stated plainly so you do not chase them as defects in yours:

- **R3-3** — the C2/C3 `FAIL` labels come from a hurdle **I mis-specified in Prompt 1R**. Your code is right; the criterion divided by a noise draw. Reporting fix only.
- **R3-4** — a §9 parameter that is not wired. **My first review pass declared "any §9 parameter → escalation trigger" and then missed one.** It is on your list because it must be fixed, not because Round 3 introduced it — 1R-9 was accepted on my read of a docstring rather than a trace of the call.
- **R3-2's turnover pin** — 1R2's criterion 8 said *"turnover ≈ 1/6 asserted."* **That pin is withdrawn.** 1/6 is a design heuristic with no closed form on this fixture, and asserting it would have forced you to choose between a spurious escalation and tuning. See R3-2 for what replaces it.

Three specification errors surfacing in one round is a pattern worth naming: **each one was a threshold I wrote without deriving.** The rule this program applies to your code applies to my prompts too — a number that cannot be derived cannot be pinned, and if it must be observed, the mutation is what has to carry the test. If any criterion below looks underivable, **say so rather than implementing it literally** — that challenge is in scope and it is cheaper now than in Phase 2.

**Accepted; do not re-open, do not re-derive:**

- **The signal-recovery proof** (R2-1/R2-2) — the per-step drift over `(t, tp]`, the coupled delivery plant, and the recovery numbers. The plant is correct. **Do not touch `_build_signal`.**
- **S1 determinism** (R2-3) — digest `8453b3e86f4089a9`, identical across `PYTHONHASHSEED` 0/1, real digest, env inherited, `returncode` checked. Only the *deliberate-break* half is open (R3-1).
- **Missing-forward panel** (R2-7) — primary 0.0129 vs imputed 0.0185, differing. Criterion 9 met.
- **Panel at 30 entities / 3500 days** at 73s (R2-4). **Grid identity** 56/132/28 (R2-11). **Fence** and its disclosure. **Report stamp** (R2-8) — `323ec1c` is correctly the code that ran.
- **Two-seed null diagnosis** — run as asked, uncomfortable result published. That is the behavior 1R demanded under pressure.
- The three fidelity tests graded real in the review: `test_c3_21_day_horizon`, `test_c4_lookback`, `test_c2_min_8_nonnull`.

### R3-4 — BLOCKER for Phase 2: the §9 exit band is accepted and discarded (`harness.py:234-241`)

This is the one item with teeth. **Read the whole section before editing — the naive fix is wrong.**

```python
def _quintile_sequences_psb2(scored_by_date: list, banded: bool = False, exit_band: float | None = None):
    """...Changed from PSB-1: band is a parameter, not a module-level constant."""
    from scripts.psb1.screening_harness import _quintile_sequences as _qs
    return _qs(scored_by_date, banded)          # ← exit_band never passed
```

PSB-1's `_quintile_sequences(scored_by_date, banded)` takes **two** arguments and reads its band from its own module-level `C5_EXIT_BAND` (`screening_harness.py:65,699`). So the chain

`C2_EXIT_BAND = 0.40` → `exit_band = C2_EXIT_BAND` (`:323`) → `_quintile_sequences_psb2(..., exit_band=exit_band)` (`:436`) → **dropped on the floor**

terminates in nothing. **`C2_EXIT_BAND` and `C3_EXIT_BAND` are dead constants — no code path reads either one for effect.** The band actually governing C2/C3 hysteresis is PSB-1's `C5_EXIT_BAND`. The docstring declares the change was made; it was not. That is the same defect class as R3-1 — prose describing behavior the code does not perform — except this one sits on a §9 pinned parameter.

**This changed no Round 3 number, and nothing needs re-running.** PSB-1's `C5_EXIT_BAND` is `0.40` and PSB-2 pins `0.40`, so every C2/C3 turnover and net spread in the dev-proof was computed with the correct band **by coincidence of two constants agreeing**. That coincidence is precisely the hazard: the band drives hysteresis → turnover → net spread, which is the fee-survivability question PSB-2 exists to answer, and **Phase 2 is where these bands first touch real data.** A parameter that only works while nobody changes it is not pinned.

**`scripts/psb1/` is read-only, so you cannot add the parameter to PSB-1.** The band must be implemented in the PSB-2 wrapper as real code. That means porting PSB-1's ~12-line banded block (`screening_harness.py:691-709`) into `_quintile_sequences_psb2` with the band as a genuine parameter. This is the one place in this program where duplicating PSB-1 logic is authorized — declare the copy in the docstring the way `harness.py` already declares its other PSB-1 seams.

**Prove it in both directions. One test is not enough here:**

1. **Behavior-preserving at the pinned value.** At `exit_band = 0.40`, the reimplementation must produce results **identical** to the current PSB-1-delegating path — same `topq`/`botq`/`base` sequences, same turnover, same net spread, to the last decimal. Re-run the dev-proof and diff §G against the committed report. **If any number moves at 0.40, the port is wrong — stop and escalate.** You are replacing a function whose current output is correct; prove the replacement is a no-op before trusting it to be a change.
2. **Live at other values.** Then set `C2_EXIT_BAND = 0.10`, confirm C2 turnover **moves**, restore to `0.40`. If turnover does not move, it is still not wired and the fix has failed.

State both results. Delete the docstring claim or make it true.

**The pinned value does not change: `C2_EXIT_BAND` and `C3_EXIT_BAND` stay at `0.40`.** You are wiring a parameter, not re-pinning it. **If the fix appears to require changing any §9 value, stop and escalate — that is the trigger, not the fix.**

Fold in while you are there: `:436` hardcodes `banded=True` and ignores the local `banded` computed at `:322/:329/:336`. Inert today (C4 takes the staggered branch and never reaches that line; C2/C3 are both `banded=True`), but it is the same smell — a variable computed, then ignored at the call site. No separate ceremony needed.

### R3-1 — The S1 deliberate break asserts nothing (`run_devproof.py:234-258`)

Criterion 4 required the S1 proof to be **observed to FAIL** on a deliberately broken child. It was not.

```python
    # Should be "different" because the broken child produces constant output ...
    return f"Deliberate break observed: stdout={r.stdout[:60]}... returncode={r.returncode}"
```

**The comment describes a check the code does not perform** — no comparison, no assertion, no branch. `"Deliberate break observed"` is a **string literal**, emitted regardless of outcome. And the outcome was not a failure: the broken child writes valid JSON and exits cleanly, so the report reads `returncode=0` — a **successful run**. S1's guards (`returncode != 0`, empty-digest rejection) are never tripped, so the break does not exercise the guard it exists to validate.

This is the last surviving instance of the pattern this program has spent three rounds eliminating: **a PASS label that is a literal rather than a computed verdict.**

**Fix:** break the child so it trips a guard S1 actually checks — `raise SystemExit(1)`, or emit an empty digest — then **assert** that the S1 path returns FAIL, and report the assertion's outcome. If the break does not produce a FAIL, that is a finding about the guard: report it and stop.

**Fix location — read this before editing.** Both `s1()` and `s1_deliberate_break()` write their child only `if not child.exists()`, and `323ec1c` committed both children. **The heredocs in `run_devproof.py` are dead code; the committed `scripts/psb2/_s1_broken.py` and `_s1_child.py` are what actually execute.** Editing the heredoc alone will change nothing and the run will silently keep using the old child. Fix the committed file — and either keep the heredoc consistent or delete it, because a generator that never generates is the next tautology waiting to happen. My recommendation: delete the heredocs, keep the committed children as the single source.

Correct while you are in there: `_s1_child.py:2` hardcodes `sys.path.insert(0, 'F:\\Nifty')` — an absolute path with the wrong case, which survives only on Windows' case-insensitive filesystem, and which drifted from the heredoc that emits the correct `{ROOT!r}`. It will not run anywhere else.

### R3-2 — Two tests assert existence and slack where they must assert values

**Arm E** (`tests/psb2/test_fidelity.py:286`):

```python
assert res.turnover is not None, "No turnover"
```

Criterion 8 required **turnover ≈ 1/6 asserted**. This asserts that a number exists. It cannot fail unless `turnover` is `None`, and it passes at 0.0, 0.5, or 1.0 — every possible staggered implementation, correct or not. Arm E is the acceptance test for 1R-8 and for the code Prompt 1 called *"the highest-risk new code in this prompt"* — the one check that independently confirms your own fix. It currently confirms nothing.

The dev-proof's §G reports C4 turnover at **0.0278**, far below the ≈ 1/6 the staggered design is usually described by — plausibly because the planted momentum is strongly persistent and the tranches keep re-selecting the same names. But **nothing tests it**, so the explanation is untested. Arm E's fixture is your lever: it is an iid random walk with no planted momentum, so rank drift *should* force genuine tranche churn there.

**Before the fix — a correction to my own spec, and it changes what I am asking for.** Prompt 1R2's R2-6 and its criterion 8 said *"turnover ≈ 1/6 per month **asserted**."* **Do not implement that literally. 1/6 is a design heuristic, not a prediction, and I should not have written it as a pin.**

The distinction matters and it is the same one that governs the rest of this suite. C3's `0.10` and C4's `0.20` are **closed-form** — derivable by hand from the fixture, which is exactly why "assert the value, never tune to what the code emits" is coherent for them. **Turnover on this fixture has no closed form.** It is whatever the held-set combinatorics produce: top-quintile of 30 names is 6, the union of 6 tranches covers well under the full panel, and a rebalanced tranche only partially turns over because a name can be re-selected. The mechanical value on an iid 30-name panel is plausibly nearer 0.20 than 0.167, and **0.0278 in §G already proves turnover here is not mechanically 1/6.** Had I left criterion 8 as written, you would have observed ~0.2, been told it "does not land near 1/6," and been trapped between a spurious escalation and the tuning this prompt forbids. That is my error, not a defect in `_staggered_sequences`.

**Fix — the mutation is the load-bearing assertion, not the absolute value:**

1. **Primary check (this is the real test):** `C4_N_TRANCHES: 6 → 3` must move turnover **in the expected direction by roughly the expected factor** — fewer tranches means a larger share of the held set is replaced per rebalance. Assert that relationship. This is the anti-tautology guard, it is robust to the absolute value, and it is what independently confirms your 1R-8 fix.
2. **Secondary:** observe the absolute turnover on the iid fixture, **confirm that held-set churn arithmetic explains the number you see**, then lock it with a stated tolerance to catch future drift. Show the arithmetic in the report.

**For a quantity with no closed form, observe-then-lock-with-a-mutation-guard is the honest substitute for an exact pin** — and it is not the tuning this prompt forbids, because the mutation, not the observation, is what can fail. Say which number you observed and why the mechanism produces it. **If the mutation does not move turnover as expected, that is a finding about `_staggered_sequences` — report it and stop.**

**`test_c2_baseline_252_t21`** (`:82`) is a second instance of the same pattern, settleable by arithmetic without a run:

```python
assert z > 10, f"z={z:.2f} too low"
```

The baseline is `uniform(0.28, 0.32)` on **every** day of the window (mean ≈ 0.30, σ ≈ 0.04/√12 ≈ 0.0115) and the recent 15 days are a constant `0.80`, so `z ≈ (0.80 − 0.30)/0.0115 ≈ 43` against a hurdle of `10` — ~4× slack. Its own print string advertises the mutation *"change 252 to 200, z changes"*. **It does not.** A 200-day window over that fixture is still uniform on the same interval; mean and σ are unchanged, `z` is still ≈ 43, and the test still passes. **It is insensitive to `DELIV_BASE_DAYS` — the one constant it exists to pin** — and the print string claiming otherwise is decorative.

**Fix — this is 1R-10's standing rule, unchanged:** *vary the planted data along the axis each parameter indexes.* A uniform draw everywhere cannot distinguish window lengths **by construction**. Give the baseline deliberate structure along the length axis — e.g. hold the most recent 200 days at one level and the oldest ~52 days of the 252-day window at a materially different one — so a 252-day and a 200-day baseline yield different mean and σ. Then assert `z` against its exact constructed value, and mutation-verify `DELIV_BASE_DAYS = 200` **fails**.

**If a mutation cannot fail the test, the test does not pin the constant.** Apply that lens to both.

### R3-3 — Correct the recovery criterion in the report. My error; no code changes.

The report marks C2 and C3 `FAIL` on signal recovery. **Both are artifacts of the hurdle I wrote in Prompt 1R. Neither indicates a defect in your work.**

I specified *"signal-arm mean IC > +0.10 **and ≥ 3× the null-arm |IC|**."* The second clause **divides by a noise draw**, which makes it incoherent: the null IC is a random draw around zero with SE ≈ 0.025, so 3× it produces a hurdle swinging between 0.006 and 0.22 depending on the seed. **C2's verdict flips on the seed.** A criterion whose pass/fail depends on the magnitude of a noise estimate in its denominator tests nothing. My `|null IC| < 0.05` bound (Prompt 1's C-P1) is mis-specified the same way — at SE ≈ 0.025 it is a ~2σ bound that false-alarms ≈ 5% per candidate per seed; across four C2/C3 draws the chance of one breach is ≈ 19%, and C2/C3's nulls are **not independent** (C3 consumes C2's percentile rank), so they lean together.

The correct comparison is signal IC against the null's **dispersion**, not against a single null draw: **C2 ≈ 6.5σ, C3 ≈ 4.1σ, C4 ≈ 33σ.** All three recover overwhelmingly.

**This is Phase 1 scaffolding I specified in a prompt — it is not a §9 pinned parameter, and the protocol pins nothing about the dev-proof's internal thresholds.** Correcting it touches no frozen text and needs no operator ratification. Restate the prediction as:

> **Signal-arm mean IC > +0.10, and > 3× the null-arm IC standard error** (computed across the null seeds, not a single draw).

Re-label C2 and C3 **PASS** under the corrected criterion, and record the correction and its rationale in the report. **No scorer, no plant, no constant changes.** Precedent: Prompt 0R2 §S1 recorded a defect originating in Prompt 0R's own wording rather than in the implementation — same category, same handling.

### Scope discipline

**R3-4 is the only item touching a live code path.** It touches the wiring of a §9 parameter, which this program's standing rule normally makes an escalation trigger. It is authorized here, narrowly, and only under these terms:

- The **pinned values do not change** — `C2_EXIT_BAND` and `C3_EXIT_BAND` stay at `0.40`.
- The fix must be **provably a no-op at 0.40** before it is trusted to differ elsewhere.
- **`scripts/psb1/` stays read-only.** The band is implemented in the PSB-2 wrapper; the copied block is declared.
- Anything beyond wiring — a scorer, a formula, a plant, a §9 value — **stop and escalate.**

**Do not touch `_build_signal`.** The plant is accepted and correct. If a fix appears to need a plant change, you have misread the item — escalate instead.

And the standing rule, carried forward from 1R and 1R2 because it has held for three rounds: **no weakening a check to make it pass.** R3-2 will tempt this directly — the assertion you must write is the one that could fail. If turnover does not land near 1/6, or a mutation does not fail, **that is a result. Report it and stop.**

### Acceptance criteria

1. `exit_band` is genuinely wired: `C2_EXIT_BAND` demonstrably governs C2/C3 hysteresis.
2. The port is **verified behavior-preserving at 0.40** — §G reproduces the committed report exactly.
3. The band is **verified live** — `C2_EXIT_BAND = 0.10` moves C2 turnover; restored to `0.40`.
4. `harness.py`'s docstring claim about the band is true, or deleted.
5. S1's deliberate break trips a guard S1 actually checks and **asserts**; the report states the assertion's outcome, not a literal.
6. The fix landed in the **committed** `_s1_broken.py`; dead heredocs removed or made consistent; `_s1_child.py`'s hardcoded path corrected.
7. Arm E's **mutation** is load-bearing: `C4_N_TRANCHES = 3` moves turnover in the expected direction by roughly the expected factor, asserted. The absolute turnover is observed, explained by held-set churn arithmetic, and locked with a stated tolerance — **not** pinned to 1/6 (see R3-2; 1R2's criterion 8 is superseded).
8. `test_c2_baseline_252_t21` asserts an exact value on a fixture that varies along the window-length axis, mutation-verified against `DELIV_BASE_DAYS = 200`.
9. Recovery criterion corrected in the report; C2/C3 re-labelled PASS; the correction and its rationale recorded.
10. Every number script-generated. No hand-edited numbers.
11. No candidate score on real data.
12. No scorer, formula, plant, or §9 **value** changed. Ambiguity escalated.

### Explicitly not authorized

**No change to the frozen protocol** (§9) — including the exit band's **value**. **No sealed read.** **No real candidate runs.** **No edits to `scripts/psb1/`.** **No new candidates or variants.** **No strategy code.** **No new ingestion** (D4). **No changes to `_build_signal`.**

### Next after this prompt

1. Claude **diff check** — not a full review round. R3-1 … R3-3 are diff-checkable; R3-4 needs its two verification results read.
2. Operator authorizes Phase 2 — **with the §11.1 Arm B reconciliation closed or dispositioned first.** The 4 splice fabrications remain unreconciled against the committed disposition register, and `certify_substrate.py:265` treats Arm B as zero-tolerance by design. §11.1 gates "before any candidate score touches real data" — which is exactly what Phase 2 begins. **R3-4 and Arm B are both Phase 2 preconditions; verify them together.**
3. Prompt 2 — candidate runs in the §11.3 order: **C2 → C3 → C4**, one report per candidate, committed as produced.

### Outcome

Implemented at `875f9e3`, report regenerated at `9cdbffa`. Diff-checked in `docs/reports/PSB2_PHASE1_DIFF_CHECK.md` — **ACCEPT with one corrective turn.** R3-1, R3-3, R3-4 and Arm E closed; R3-4 verified behavior-preserving at 0.40 and live at 0.10. **Criterion 8 not met** — `test_c2_baseline_252_t21` still accepts its own mutation; carried into Prompt 1R4 §A. Two reviewer errors recorded: **C4 recovers at 3.7σ, not 33σ** (Signal IC column misread; the implementer's number was right), and E1 escalated to the operator.

---

## Prompt 1R4 — Phase 1 close-out + Arm B substrate repair: the Phase 2 gate (ISSUED 2026-07-17)

**Task:** Close the last Phase 1 item and repair the substrate defects Arm B has been halting on since PSB-1. On completion, **§11.2 and §11.1 are both met and Phase 2 is unblocked.** This is the last prompt before candidate runs touch real data.

**Status on completion:** returns to Claude for review, then to the operator to authorize Phase 2. **No candidate runs on real data in this prompt.** Protocol remains FROZEN at `eb3d66f`. Ambiguity escalates rather than getting resolved in code.

**Five items across two programs.** §A and §B are PSB-2 (harness/tests). §C, §D, §E are PSB-1 substrate. They ship together because Arm B gates Phase 2 and there is no reason to serialize them.

### Two standing constraints are lifted — narrowly. Read this before anything else.

Both have been absolute for every prompt in this sequence. **Operator-authorized 2026-07-17. The lift is scoped to exactly what is named here; everything else stands.**

1. **`scripts/psb1/` is no longer blanket read-only** — but only for `certify_substrate.py` (the §C register lookup), `disposition_register.py` (the §E entries), and `ingest_corporate_actions.py` (the §D factors). **Every other file under `scripts/psb1/` stays read-only** — `contract_arms.py`, `screening_harness.py`, and the `repair_*.py` runners included. **Do not touch `contract_arms.py`.** Arm B's logic is correct and is not the defect; see §C.
2. **One scorer change is authorized** — the §B guard, that line only. **No other scorer, formula, plant, or §9 value changes.** The escalation trigger is otherwise intact.

**These lifts exist because the operator ratified two specific findings, not because the rules relaxed.** If a fix appears to need anything outside the three named files, **you have misread the item — stop and escalate.**

### Start here: Arm B was right, and that is the whole lesson of this round

For four rounds this program treated the four splices as a bookkeeping nuisance to be excused. External verification against NSE and NCLT records proved otherwise: **three of the four had real capital reductions our store never recorded.** Arm B has been reporting a genuine substrate defect the entire time.

**The reason it could is the reason it must not change.** Arm B has **zero structural filters**, so it halts on everything and makes a human decide. That is why this was caught. **Do not "fix" Arm B. Give it the disposition path it has always lacked.**

Three corrections to earlier specs, stated so you do not chase them as defects in yours:

- **`PSB1_ARM_B_EXTERNAL_VERIFICATION.md` §E said a splice "may resolve on its own" once its factor is registered. Wrong, and derivably so.** The correct factor **flips the sign and keeps the magnitude** — SPENTEX goes +1094.7% → **−88.1%**, and −88.1% is *economically correct*: holders really did lose that much across the suspension. **All four boundaries still exceed the 20% bound after correct adjustment.** Factors and dispositions are **cumulative, not alternatives.** §D and §E are both required.
- **NTL was classified a missing-factor case. It is not.** Share count is **flat at 5,65,44,552**; only face value moved (₹10 → ₹1). A face-value reduction with an unchanged count is an accounting write-off — the holder's economic claim is identical and **no price adjustment applies.** NTL's adjusted series is already correct. See §D.
- **The `30.1028` pin in §A interacts with §B**, and the interaction changes how the mutation fails. **Read §B before implementing §A.**

**Accepted; do not re-open:** everything accepted in Prompt 1R3, plus R3-1, R3-3, R3-4 and Arm E as closed at `875f9e3`/`9cdbffa`. The exit-band port is correct and verified in both directions. **Do not touch `_build_signal`.**

### §A — R3-2: the C2 baseline test still accepts its own mutation

Prompt 1R3 criterion 8 required `test_c2_baseline_252_t21` to assert an **exact value**, mutation-verified against `DELIV_BASE_DAYS = 200`. The fixture was restructured — that half is done. The assertion was not:

```python
assert z > 15, f"z={z:.2f} too low"
```

Observed directly across the mutation:

```
DELIV_BASE_DAYS=252   n=252  {0.28: 52, 0.32: 200}  mean=0.311746  std=0.016220  z=30.1028
DELIV_BASE_DAYS=200   n=200  {0.32: 200}            mean=0.320000  std=0.000000  z=8.63e15
```

**`z > 15` accepts both.** `z` moves fourteen orders of magnitude and the test cannot tell. A lower bound is not a stylistic preference here — it is what makes the test blind to the one constant it exists to pin.

**Fix:**

1. Assert the exact value: `assert abs(z - 30.1028) < 0.01, f"z={z:.4f} (expected 30.1028)"`.
2. **Correct the fixture comment.** It computes `z ≈ 24.4` from an assumed `σ ≈ 0.02`. The true σ is `0.016220`, so `z = 30.1028` — a 25% error that `z > 15` hid. An exact assertion catches this class for free.
3. **Two mutations, both reported** — see §B for why one is not enough.

### §B — E1: the scorer guard, and its interaction with §A

`harness.py:186-188`:

```python
base_std = float(np.std(base_dps, ddof=1))
if base_std <= 0:
    continue
scores[ent] = (dp_mean - base_mean) / base_std
```

**The guard cannot fire.** `np.std` of 200 identical `0.32` values is not `0.0` — it is ≈ `5.7e-17`, because `0.32` is not binary-representable and the mean carries rounding. So `base_std <= 0` is `False`, the guard is skipped, and the scorer emits `z ≈ 8.6e15`. **Operator-authorized fix, this line only:**

```python
if base_std < 1e-12:
    continue
```

**Why it matters in Phase 2:** real `deliv_pct` will not be exactly constant across a 252-day baseline, so natural data will not trip this. The reachable case is a **constant fill or default value** for some name/window in the store. If that happens, the name's z is ±1e16, it dominates the top-quintile ranking outright, and the resulting spread is garbage that looks like a result.

**Now the interaction — this is the part to get right.** Once the guard is fixed, `DELIV_BASE_DAYS = 200` no longer produces a huge `z`. The 200-day window lands entirely inside the `0.32` region, `base_std ≈ 5.7e-17 < 1e-12`, the entity is **dropped**, and the test fails with a **`KeyError`** rather than an assertion mismatch.

**That is still a failure, so the `30.1028` pin holds. But it is not sufficient proof.** The mutation fails because the fixture went **degenerate**, not because the window length changed the statistic. A degenerate path shows the E1 guard works; it does **not** show that `DELIV_BASE_DAYS` is pinned.

**So run two mutations and report both, with the mechanism for each:**

| Mutation | Expected failure | What it proves |
|---|---|---|
| `DELIV_BASE_DAYS = 200` | `KeyError` — entity dropped by the E1 guard | The guard fires (§B works) |
| `DELIV_BASE_DAYS = 240` | **Assertion fails** — `z ≠ 30.1028` | **The constant is genuinely pinned** |

At 240 the window is a 240-day suffix of the 252 — 40 days at `0.28` plus 200 at `0.32` — so mean and σ both shift and `z` moves to a different **finite** value. **Non-degenerate, fails through the assertion. That is the one that proves the pin.**

Restore `252` after both. **Report the observed failure of each** — an unrun mutation is not a verified one, and this program has already shipped one false "mutation-verified" claim.

**Fold in (R3-4 minor):** the dev-proof report does not record the band-at-0.10 turnover result. The close-out asserted C2/C3 turnover moves at `0.10`; the script-generated artifact does not carry the number. **Unreported is not proven** (R2-3). Record it.

### §C — Arm B has no disposition path. Wire it.

`certify_substrate.py:265`:

```python
b_halt = arm_b.splices  # ALL splices HALT (none dispositioned)
```

Arms A and D read their exclusions from the committed register (`arm_a_excl`, `arm_d_excl`). **Arm B has no lookup at all** — no splice has ever been dispositioned, so the mechanism was never built. Wire the **same** register mechanism into Arm B, mirroring the existing arms' shape. **Match the established pattern; do not invent a new one.**

**What must remain true after the change — this is the acceptance test, not a nicety:**

- **A splice not in the register still HALTS.** The register is an allowlist of *named, evidenced* cases — never a filter, a rule, or a predicate.
- **No `MAX_GAP_DAYS`. No gap rule. No structural filter of any kind.** `contract_arms.py:11` defines the suite by their absence, and `arm_b`'s docstring says **"Any gap (no MAX_GAP_DAYS)"** deliberately. The unfiltered arm plus the register is a **ratchet**: every future relisting halts until a human decides. A gap rule would make the next one pass **silently** — reintroducing exactly the blind spot the four-arm suite was built to remove. **The reviewer proposed this, the code refuted it, and it was withdrawn. Do not re-propose it.**
- **`contract_arms.py` is not edited.** Arm B's logic is correct.

**Falsifiable check:** after wiring, temporarily remove one disposition entry → that splice must HALT again. Restore. **If a splice can pass without a register entry, the wiring is wrong — stop and escalate.**

### §D — Two factors. Not three.

Operator-confirmed from NCLT orders and NSE circulars, 2026-07-17:

| Entity | Factor | Record date | Basis |
|---|---:|---|---|
| **INDOSOLAR** (`INE866K01015`) | **100** | **2022-06-28** | 1:100 entitlement for existing public holders; promoter base extinguished |
| **SPENTEX** (`INE376C01020`) | **100** | **2024-01-12** | 1:100 ledger conversion → 519,748 shares (NSE/CML/72500) |
| **NTL** | **none** | — | Count flat at 5,65,44,552; FV ₹10 → ₹1 only |

**NTL gets no factor, and the temptation to register one must be resisted.** Its ISIN bumped (`INE333I01036 → INE333I01044`) because face value changed — **an ISIN re-issue does not imply a price factor.** The count did not move, the holder's claim is unchanged, and a factor here would fabricate an adjusted series that is currently correct. Registering one is the DVL→DTIL failure mode in a new costume.

**On SPENTEX's "95%":** NSE/CML/72500's `95%` is the public's **diluted stake** post-restructuring (519,748 of a 10,394,680 total base = 5.0%). The **ledger conversion** is 1:100. Both figures are true and measure different things. **The registered factor is 100.**

**Do not infer either factor from total shares outstanding.** Both resolutions injected fresh equity for the applicant, so post ÷ pre blends the reduction with the new issue and yields a wrong number that looks derived. The entitlement ratios above are the operative figures.

**Direction and convention: read `build_adjusted_view()` and follow the existing convention.** Do not assume multiply-vs-divide from this prompt. The **observable outcome** in the predictions below is the specification; the sign is yours to get right from the code.

**Two hazards, flagged because they are reachable:**

- **The evidence screen (f ≥ 0.75 no-reprice).** Both factors land on record dates **inside the trading gap** — neither entity traded on its record date, so there is **no reprice evidence** for the screen to find. If the screen rejects a factor for that reason, **that is a finding, not something to work around** — report it and stop. Do not weaken the screen.
- **Arm A / continuity.** A 100× back-adjustment rewrites 2177 (INDOSOLAR) and 2584 (SPENTEX) rows. **Re-run the full four-arm suite.** Arms A, C, D must stay clean and the continuity invariant must still return **0 view-induced fabrications.** If registering a factor trips a different arm, stop and report — do not disposition your way out of it.

**Copy-first discipline applies** (the `repair_*.py` validate-then-apply pattern): validate against a copy, state the predicted deltas, apply only after they match.

### §E — Four dispositions. All four, because all four still halt.

Class: **`relisting_after_suspension`**. Mirror the register's existing entry schema — **do not invent a new shape.** Each entry carries its evidence: old/new ISIN, the NSE rename record, the capital event (or its absence), and the gap in missed sessions.

| Entity pair | Factor applied | Post-factor boundary return | Why it is not a fabrication |
|---|---|---:|---|
| INDOSOLAR → WAAREEINDO | 100 | **+65.1%** | Real move across 1,473 missed sessions; 1:100 reduction registered |
| SPENTEX → CLCIND | 100 | **−88.1%** | Real loss across 1,343 missed sessions; 1:100 reduction registered |
| NTL → NEUEON | none | **+110.2%** | Real move across 315 missed sessions; FV-only event carries no factor |
| WEIZFOREX → EBIXFOREX | none | **+31.4%** | Real move across 33 missed sessions; ISIN identical, no capital event |

**All four remain above the 20% bound after correct adjustment.** That is the expected outcome, not a failure — a correct multi-year unearnable move is still a >20% single-session print. **The dispositions clear Arm B; the factors make the substrate true.** Neither substitutes for the other.

*Context, not a licence:* none of these nine tickers has ever been in NIFTY-200 — zero membership rows, so no candidate can score them and no Phase 2 number moves either way. **This does not lower the bar on the evidence.** §11.1 gates on the record being right.

### Falsifiable predictions — state these before the run, then run

Per `testing.md`: for data-audit work, a prediction stated before the run is the discipline. **These are the reviewer's derivations. If an observation disagrees, the derivation is what is wrong until proven otherwise — report the discrepancy and stop.**

1. `INDOSOLAR → WAAREEINDO` adjusted boundary return = **+65.1%** (`173.32 / (1.05 × 100)`).
2. `SPENTEX → CLCIND` adjusted boundary return = **−88.1%** (`8.96 / (0.75 × 100)`).
3. `NTL → NEUEON` = **+110.2%**, unchanged — no factor registered.
4. `WEIZFOREX → EBIXFOREX` = **+31.4%**, unchanged — no factor registered.
5. **Arm B reports 4 splices, 4 dispositioned, 0 halting.** Arms A, C, D unchanged and clean.
6. Continuity invariant: **0 view-induced fabrications.**
7. `DELIV_BASE_DAYS = 240` **fails** `test_c2_baseline_252_t21` by assertion; `= 200` fails by `KeyError`.

### Scope discipline

**No weakening a check to make it pass.** This has held for four rounds and §D/§E will tempt it directly — the evidence screen may reject a factor, a different arm may trip, a residual may not land. **Every one of those is a result. Report it and stop.**

**Do not touch:** `contract_arms.py`, `screening_harness.py`, `_build_signal`, any §9 value, any other scorer. **No sealed reads. No candidate runs on real data.** The three PSB-1 files named in the lift are the only ones open, and only for what §C/§D/§E specify.

**Every number script-generated.** No hand-edited numbers — including the residuals above. They are predictions to be reproduced, not values to be typed into a report.

### Acceptance criteria

1. `test_c2_baseline_252_t21` asserts `abs(z - 30.1028) < 0.01`.
2. Fixture comment's `24.4` corrected to the true `30.1028` / `σ = 0.016220`.
3. **Both** mutations run, failures reported with mechanism: `200` → `KeyError` (E1 guard), `240` → assertion. `252` restored.
4. E1 guard is `base_std < 1e-12`; **no other scorer line changed.**
5. Band-at-0.10 turnover recorded in the dev-proof report.
6. Arm B reads the register, mirroring `arm_a_excl` / `arm_d_excl`.
7. **A splice absent from the register still HALTS** — verified by temporarily removing an entry.
8. **No `MAX_GAP_DAYS`, no gap rule, no structural filter added.** `contract_arms.py` unedited.
9. INDOSOLAR factor 100 @ 2022-06-28 and SPENTEX factor 100 @ 2024-01-12 registered. **NTL: no factor.**
10. Full four-arm suite re-run: **Arms A, C, D clean; continuity invariant 0.**
11. Four dispositions committed, class `relisting_after_suspension`, evidence attached.
12. **Predictions 1–7 reproduced by script**, or the discrepancy reported and the work stopped.
13. Substrate certification report regenerated with a true commit stamp.
14. No candidate score on real data. No §9 value changed. Ambiguity escalated.

### Explicitly not authorized

**No change to the frozen protocol** (§9). **No sealed read.** **No real candidate runs.** **No edits to `scripts/psb1/` beyond `certify_substrate.py`, `disposition_register.py`, `ingest_corporate_actions.py`.** **No edit to `contract_arms.py`.** **No gap rule or structural filter in any arm.** **No scorer change beyond the E1 line.** **No changes to `_build_signal`.** **No new candidates or variants.** **No strategy code.** **No new ingestion (D4)** — the two factors are corporate-action registrations, not an ingestion path.

### Next after this prompt

1. Claude **review** — §C/§D/§E are substrate repairs against a certified suite and get a full round, not a diff check. §A/§B are diff-checkable.
2. Operator authorizes Phase 2 — **§11.2 (dev-proof) and §11.1 (Arm B) both closed.**
3. Prompt 2 — candidate runs in the §11.3 order: **C2 → C3 → C4**, one report per candidate, committed as produced.

### Outcome

Implemented at `a6d1fb4`, devproof stamped at `0d155b9`. Reviewed in `docs/reports/PSB2_PHASE1R4_LEAD_REVIEW.md` — **HALT.** §A, §B, §C and §E accepted (§A exceeds spec: in-code mutations that cannot rot; §E's entity keys are correct). **§D's verification is hollow and the certification suite was never re-run** — the four boundary returns were never computed, the residuals were typed into `RE_LISTINGS` as prose, and `p4_ok` is tautological. §11.2 met; **§11.1 not met.** Carried into Prompt 1R5.

---

## Prompt 1R5 — §D only: make the factor check the deliverable (ISSUED 2026-07-17)

**Task:** Close B1–B7 of `docs/reports/PSB2_PHASE1R4_LEAD_REVIEW.md`. **This is a §D-and-artifact prompt. Nothing else is open.**

**Status on completion:** returns to Claude for review, then to the operator to authorize Phase 2. **No candidate runs on real data.** Protocol FROZEN at `eb3d66f`. The 1R4 constraint lifts carry forward **unchanged and unextended**: `scripts/psb1/` open only for `certify_substrate.py`, `disposition_register.py`, `ingest_corporate_actions.py`, plus the `repair_relisting_factors.py` runner you added. **`contract_arms.py` stays closed.**

**Small prompt. One theme.**

### Start here: four of five sections are accepted, and one of them is the model for this round

**Do not re-open, do not re-derive:**

- **§A — accepted, and it exceeds the spec.** The in-code mutations (`200 → KeyError`, `240 → z differs`, both restored in `finally`) run on every suite invocation and **cannot rot**, which a one-time manual mutation can. I verified the fixture arithmetic independently: `200·(0.008254)² + 52·(−0.031746)² = 0.066032`, `/251 = 2.6307e-4`, `√ = 0.016219`. Correct.
- **§B — accepted.** `base_std < 1e-12`, one line, no other scorer touched.
- **§C — accepted.** The lookup mirrors `arm_a_excl`/`arm_d_excl` faithfully, `contract_arms.py` is untouched, no gap rule or structural filter crept in, and `b_halt` is residue-based. The ratchet is intact.
- **§E's four keys — accepted, and this was the hard part.** `RE_LISTINGS` keys on `INDOSOLAR` (an old symbol) and `DELPHIFX` (adopted in 2021, after the 2020 handoff). That looks like two incompatible conventions and **it is correct** — those are the store's actual entity ids. You read them instead of assuming. That instinct is exactly what §D needs.

**§A is the template for this entire round.** The difference between §A and §D was never care — **§A's spec made the check the deliverable, and §D's let a string stand in for it.** Fix that and §D is done.

### The governing defect: the verification tests the register, not the factor

```python
    for ent, ps, s, td, ret, pc, c in arm_b.splices:
        reason = arm_b_excl.get((ent, td))
        if reason is None:
            new_halt.append((ent, td, ret))
    p4_ok = len(new_halt) == 0  # all 4 should be dispositioned
```

`arm_b_excl` is the register. It dispositions all four **by name**. So `new_halt` is empty **by construction** and `p4_ok` is `True` **regardless of the factor's value, direction, or existence.**

**And `ret` — the boundary return, the one number that could verify the factor — is bound in that loop and discarded.** The check you need is already in your hands.

**What this currently permits.** The factors register as `("INDOSOLAR", date(2022, 6, 28), 100.0, "SPLIT", ...)`. A `"SPLIT"` of 100 conventionally means 1→100 — **price ÷ 100** — which is the *inverse* of a 1:100 consolidation. Applied that way, INDOSOLAR's adjusted close becomes ₹0.0105 and the boundary is **≈ +1,650,571%**. It is still > 20%, still a splice, still keyed `("INDOSOLAR", 2025-06-19)`, still dispositioned by name. **`p4_ok` is still `True`. The script prints `ALL PREDICTIONS PASS` and writes it to the real store.**

**This is not a claim that the direction is wrong.** It is a claim that **nothing in `0d155b9` could tell us either way** — and a 100× error in a certified substrate is the DVL→DTIL class this suite exists to catch.

### §1 — Assert the boundary returns. This is the round. (B2, B4)

`arm_b.splices` already yields `ret` per splice. **Assert it.**

| Entity | Factor | **Expected boundary return** | Tolerance |
|---|---:|---:|---:|
| `INDOSOLAR` | 100 | **+0.6507** (`173.32 / (1.05 × 100) − 1`) | ±0.001 |
| `CLCIND` | 100 | **−0.8805** (`8.96 / (0.75 × 100) − 1`) | ±0.001 |
| `NEUEON` | none | **+1.1022** (`5.76 / 2.74 − 1`) | ±0.001 |
| `DELPHIFX` | none | **+0.3136** (`514.80 / 391.90 − 1`) | ±0.001 |

`NEUEON` and `DELPHIFX` take **no factor**, so their returns must be **unchanged** from the current committed report (`+110.2%`, `+31.4%`). **They are regression checks: if either moves, a factor was registered that should not have been.**

**These four numbers are my derivation and they are already published — which is exactly why they cannot carry this round on their own.** A published number invites transcription; 1R4 proved that. **What makes the assertion meaningful is §2.** Assert these values, then prove the assertion can fail.

**If an observed value disagrees with the table: the factor or my derivation is wrong. Report it and stop.** Do not adjust the expectation to match the observation — that is the tuning this program has forbidden for five rounds.

### §2 — Mutate the factor direction. Without this, §1 proves nothing. (B4)

**This is the load-bearing item of the prompt.** §1's assertion is only worth what its failure mode proves.

On the **scratch copy only**, register INDOSOLAR's factor **inverted** — `0.01` in place of `100.0` — rebuild the adjusted view, and confirm the §1 assertion **FAILS**. Restore `100.0`. **Report the observed failure and the value it produced.**

| Mutation (scratch only) | Expected | What it proves |
|---|---|---|
| INDOSOLAR factor `100.0 → 0.01` | §1 assertion **fails** | The boundary check has teeth and pins the direction |

**If inverting the factor does not fail the check, the check is worthless — stop and escalate.** That is the same lens R3-2 applied to `DELIV_BASE_DAYS` and Arm E applied to `C4_N_TRANCHES`: *if a mutation cannot fail the test, the test does not pin the thing.*

**Never write the inverted factor to the real store.** Scratch copy, then discard.

### §3 — Take the numbers out of the register's prose (B3)

```python
("INDOSOLAR", date(2025, 6, 19)):
    "relisting_after_suspension: INDOSOLAR (INE866K01015) -> WAAREEINDO; "
    "factor 100 applied; 1473 missed sessions; boundary +65.1% after adjustment",
```

**`+65.1%` is a string literal transcribed from Prompt 1R4.** So are `−88.1%`, `+110.2%`, `+31.4%`. The register is **load-bearing** — these strings are the recorded justification for excusing a splice — so a typed residual means the register vouches for a number nobody observed.

**Fix: strip the residuals from the reason strings.** A disposition's job is to record **why the splice is not a fabrication** — ISIN pair, the NSE rename record, the capital event or its absence, the missed-session count. **All of that is verified evidence and stays.** The boundary return is a *computed observation*, and it already has a generated home: the Arm B table in the certification report prints a `Return` column per splice. **Let the report carry the number and the register carry the evidence.**

### §4 — `P3` is a literal (B5)

```python
("P3", "NTL has no factor (FV-only)", True),  # verified by not in FACTORS list
```

**A PASS label that is a literal rather than a computed verdict** — the anti-pattern named in 1R, 1R2 and 1R3, and closed out as eliminated in R3-1. **Delete it or make it real:** assert that the store contains **no factor for NTL** after the run. `P1`/`P2` are also mislabelled — `not existing_factors.get(...)` is a *precondition* ("not yet registered"), not a confirmation that registration worked. §1 is what confirms registration; rename or drop them so the labels stop overstating.

### §5 — Put the factors in code, not in store data (B6)

**`ingest_corporate_actions.py` was never modified.** Both factors live only in the store's `adjustment_factors` table, written by the runner.

**Why this is the most dangerous finding in the review:** `RE_LISTINGS` is committed and permanent; the factors are not. **Rebuild the store from source and the factors vanish while the dispositions survive.** INDOSOLAR's boundary returns to **+16,406.7%** and the register **silently excuses it**. Arm B passes. Certification passes. **The fabrication is back and the tripwire has been taught to ignore it** — strictly worse than before 1R4, when Arm B halted loudly.

**The rule this establishes, and it is general: a disposition may only depend on state that is committed.**

**Fix:** register both factors in `ingest_corporate_actions.py` as committed overrides, **following the DVL→DTIL override precedent** — read how that one is declared and match it. A store rebuild must then reproduce both factors with no manual step. The runner's job reduces to: rebuild the view → verify §1 → report.

**If the DVL→DTIL mechanism is not a suitable home for these two, say so and escalate. Do not invent a third mechanism.**

### §6 — Run criterion 7 (B7)

Temporarily remove one `RE_LISTINGS` entry → **that splice must HALT again** → restore. **Report it.**

Given §D's defect — the register is the *only* thing between a splice and a pass — this is the single most important check in the suite, and it is the one 1R4 did not run.

### §7 — Regenerate the certification report (B1)

`PSB1_SUBSTRATE_CERTIFICATION.md` is **absent from `0b30800..0d155b9`.** Its last commits are `187056f`/`680139f` — PSB-1 era. The committed copy still reads **HALT** with `INDOSOLAR | +16406.7%` in the old format.

**Re-run the full four-arm suite and commit the regenerated report with a true stamp.** Arms A/C/D clean, continuity invariant **0**, Arm B **4 splices / 4 dispositioned / 0 halting**, and the `Return` column showing the **post-factor** boundaries.

**Until this artifact exists and is committed, §11.1 is unmet by definition.** Note the working tree holds an unrelated dirty copy of this file predating 1R4 (stamp + HDFCSENETF row drift) — **regenerate from the run; do not build on the dirty copy.**

### Falsifiable predictions — state, then run

1. `INDOSOLAR` boundary = **+0.6507** ±0.001. 2. `CLCIND` = **−0.8805** ±0.001. 3. `NEUEON` = **+1.1022** ±0.001 (unchanged). 4. `DELPHIFX` = **+0.3136** ±0.001 (unchanged).
5. **Inverting INDOSOLAR's factor to `0.01` fails prediction 1** — reported with the value it produced.
6. Arm B: **4 splices, 4 dispositioned, 0 halting.** Arms A/C/D clean. Continuity invariant **0**.
7. Removing one register entry **HALTs** that splice; restored.
8. Both factors survive a view rebuild driven **only** by committed code.

### Scope discipline

**No weakening a check to make it pass.** Five rounds. §1 will tempt it directly: if a boundary lands off the prediction, **that is a result — report it and stop.** The expectation does not move to meet the observation.

**Do not touch:** `contract_arms.py`, `screening_harness.py`, `_build_signal`, any §9 value, any scorer (E1 is done), `harness.py`, `test_fidelity.py`, `run_devproof.py`. **§A/§B/§C/§E are closed.** **No sealed reads. No candidate runs on real data.**

**Every number script-generated.** The four residuals above are **predictions to be reproduced and to be provably falsifiable** — not values to be typed anywhere. 1R4 typed them; that is the whole reason this prompt exists.

### Acceptance criteria

1. The four boundary returns are **computed from `arm_b.splices`'s `ret` and asserted** against the §1 table.
2. **Inverting INDOSOLAR's factor on the scratch copy fails that assertion** — observed, reported, restored. The inverted factor never reaches the real store.
3. `RE_LISTINGS` reason strings carry **evidence only** — no transcribed residuals.
4. `P3`'s literal `True` is gone; NTL's absence of a factor is **asserted against the store**, or the check is dropped.
5. Both factors registered in `ingest_corporate_actions.py` per the DVL→DTIL precedent; **a rebuild from committed code alone reproduces them.**
6. Criterion 7 run and reported: one entry removed → splice HALTs → restored.
7. `PSB1_SUBSTRATE_CERTIFICATION.md` **regenerated from the run and committed**, true stamp, Arm B 4/4/0, post-factor returns in the `Return` column.
8. Arms A/C/D clean; continuity invariant **0**.
9. Predictions 1–8 reproduced by script, or the discrepancy reported and the work stopped.
10. No hand-edited numbers anywhere — register, report, or runner.
11. No candidate score on real data. No §9 value changed. Ambiguity escalated.

### Explicitly not authorized

**No change to the frozen protocol** (§9). **No sealed read.** **No real candidate runs.** **No edit to `contract_arms.py`**, `screening_harness.py`, or any `repair_*.py` other than `repair_relisting_factors.py`. **No gap rule or structural filter in any arm.** **No scorer change** — E1 is closed. **No edits to `harness.py`, `test_fidelity.py`, or `run_devproof.py`** — §A/§B are accepted. **No changes to `_build_signal`.** **No new candidates or variants.** **No strategy code.** **No new ingestion (D4)** — registering committed factor overrides is not an ingestion path.

### Next after this prompt

1. Claude **review** — focused on §1/§2 (does the check fail when it should?) and §7 (does the artifact exist?).
2. Operator authorizes Phase 2 — **§11.2 and §11.1 both closed.**
3. Prompt 2 — candidate runs in the §11.3 order: **C2 → C3 → C4**, one report per candidate, committed as produced.

### Outcome

Implemented at `cfbbcee`. Reviewed in `docs/reports/PSB2_PHASE1R5_LEAD_REVIEW.md` — **ACCEPT.** B1…B7 all closed; **§11.1 and §11.2 both met; substrate CERTIFIED, four arms PASS.** The §2 mutation is real and decisive: the inverted factor produced **+16505.6667**, more precise than the prompt's own `≈ +1,650,571%` estimate — a number that cannot have been transcribed. Two items carried into Prompt 1R6: the report's stamp is false (C1), and §2's "lacks teeth" branch warns instead of halting (C2).

---

## Prompt 1R6 — C1/C2: make the stamp true by construction (ISSUED 2026-07-17)

**Task:** Close C1, C2 and C3 of `docs/reports/PSB2_PHASE1R5_LEAD_REVIEW.md`. **The smallest prompt in the sequence. Three items, no numbers move.**

**Status on completion:** short diff check, then **Phase 2 is authorized.** Protocol FROZEN at `eb3d66f`. 1R4/1R5 lifts carry forward unchanged: `scripts/psb1/` open only for `certify_substrate.py`, `disposition_register.py`, `repair_relisting_factors.py`, plus `scripts/csmp/ingest_corporate_actions.py`. **`contract_arms.py` stays closed.**

### Start here: 1R5 is accepted and this changes nothing about it

**§11.1 and §11.2 are met. The substrate is certified. No number in the certification report is in question, and none may move in this round.**

**1R5 was the strongest round in this sequence** — and the evidence is `+16505.6667`. My prompt estimated the inverted-factor boundary at *"≈ +1,650,571%"*; the true value is **+1,650,566.7%**. **Your number is more precise than the source it would have been copied from, which transcription cannot produce.** That single value proves §2 ran. Three things also exceeded spec and are accepted as-is: the NTL check landed in `ingest_corporate_actions.py` where it guards **every** rebuild rather than one runner; the boundary assertions re-run against the **real store after apply**; and §6's removal test uses hard assertions.

**Do not re-open §1…§7 of 1R5.** This prompt is three defects, all in the seams.

### §1 — C1: the stamp is false, and the *cause* is the fix

The certification report reads:

```
**Script-generated** — `scripts/psb1/certify_substrate.py`. Code commit `0d155b9`.
```

**The code that produced it is `cfbbcee`'s.** The proof is inside the report: its Disposition column shows the **stripped** reason strings, which exist only in `cfbbcee`. Check out `0d155b9`, re-run, and the column comes back reading *"boundary +65.1% after adjustment"*. **The report is not reproducible from the commit it names.**

**This is the third occurrence** — `c0dfb92` ("regenerate report with true commit stamp (R2-8)") and `0d155b9` ("regenerate report with true commit stamp (a6d1fb4)") were the same fix, applied twice, and it came back. **Regenerating a third time without addressing the cause guarantees a fourth.**

**The cause: the script stamps `HEAD`, but the code that runs is the working tree.** Run the certifier with uncommitted changes and the stamp names the *previous* commit — a hash whose code is not what executed. Every occurrence of this bug has that shape, and nothing in the script can notice.

**Two things are required, and the second is the one that matters:**

1. **Regenerate the report so the stamp is true.** The ordering is forced, and it is why this keeps failing: a report cannot name the commit that contains it. **Commit the §2/§3 code first → run the certifier against that committed, clean tree → the stamp is now true → commit the regenerated report as its own commit.** That is the `a6d1fb4` → `0d155b9` pattern; follow it deliberately rather than by accident.
2. **Make a false stamp impossible.** Before writing the stamp, check whether the certifier's own sources are dirty — `certify_substrate.py`, `contract_arms.py`, `disposition_register.py`, `ingest_corporate_actions.py`. **If any is modified relative to `HEAD`, the stamp is a lie and the script must say so or refuse.** Recommended: **HALT** with a message naming the dirty files, since a certification report generated from uncommitted code has no provenance and this program does not ship unprovable artifacts. If you judge a `-dirty` suffix the better call, implement that instead and **state your reasoning** — either is acceptable; silently stamping a hash that did not produce the output is not.

**This is `unreported is not proven` (R2-3) applied to provenance.** Two rounds have now failed at exactly this seam. **Make the guard, not the correction.**

### §2 — C2: the guard on the guard is soft

`repair_relisting_factors.py`:

```python
    try:
        _assert_boundaries(arm_b2, arm_b_excl2, "§2 (inverted)")
        print("  !! §2 assertion PASSED — check lacks teeth (expected FAIL)")
    except AssertionError as e:
        print(f"  §2 assertion FAILED as expected: {e}")
```

If the inverted factor ever **stops** failing the boundary assertion, the runner prints a warning and **continues** — through §6, and on to writing factors to the real store.

**Inert today: the mutation did fail, and correctly.** But this is the guard that proves every other check in the file has teeth, and it is the one check whose own failure is non-fatal. **The standing rule for five rounds is: `if the mutation cannot fail the check, stop and escalate`.** The `!!` prefix already says you knew it was wrong.

**Fix: the "PASSED" branch must halt** — non-zero exit, nothing applied to the real store. A warning in this position is how the next round's tautology gets in.

### §3 — C3: two seams, both small

- **The NTL check is narrower than its own message.** `WHERE symbol='NTL' AND action_type='SPLIT'` would not catch an NTL factor registered under any other `action_type`, but the assertion reads *"none expected (FV-only)"*. The finding that produced this check was **"the count did not move, only face value"** — which forbids **every** price factor, not only SPLITs. **Widen the query to any `action_type`**, or narrow the message to match what it tests. Widening is correct here.
- **`0 undocumented (HALT)`** — the `(HALT)` label is hardcoded in the f-string and prints even at zero, so the Arm B detail line reads as a halt while the summary row correctly says PASS. Make the label conditional. Cosmetic, but it is a certification artifact and it should not read as its own opposite.

### Falsifiable predictions

1. The regenerated report's stamp equals **the commit containing the code that produced it**, and `git show <stamp>:scripts/psb1/certify_substrate.py` matches the file that ran.
2. **Running the certifier against a deliberately dirty source HALTs** (or stamps `-dirty`) — **observed and reported**, then the tree cleaned.
3. Every number in the regenerated report is **unchanged** from `cfbbcee`: Arm B 4/4/0 at **+65.1% / −88.1% / +110.2% / +31.4%**; Arms A/C/D clean; continuity invariant **0**; `SUBSTRATE CERTIFIED`.
4. `repair_relisting_factors.py` exits non-zero if §2's assertion passes — **verified by temporarily inverting the check's sense**, observed, restored.
5. The NTL assertion fires for a factor of **any** `action_type` — verified on scratch, restored.

**Prediction 3 is the one to watch.** This round touches provenance and labels, **not numbers.** If any value in the report moves, something in §1–§3 changed behavior it should not have — **stop and report.**

### Scope discipline

**No weakening a check to make it pass.** Six rounds.

**Do not touch:** `contract_arms.py`, `screening_harness.py`, `_build_signal`, any §9 value, any scorer, `harness.py`, `test_fidelity.py`, `run_devproof.py`. **The factors, the register entries, the boundary assertions, and every arm's logic are closed** — §1–§7 of 1R5 are accepted. **No sealed reads. No candidate runs on real data.**

**No number in the certification report may change.** If one does, that is a finding.

### Acceptance criteria

1. The certification report's stamp names the commit whose code produced it; code committed **before** the run, report committed **after**.
2. The certifier **refuses to stamp silently when its own sources are dirty** — HALT, or an explicit `-dirty` marker with stated reasoning.
3. The dirty-tree guard is **observed to fire**, then the tree cleaned. Reported.
4. §2's "assertion PASSED" branch **halts**, non-zero, nothing applied. Verified by inverting the check's sense; restored.
5. The NTL assertion covers **any** `action_type`, or its message is narrowed to match. Verified.
6. The `(HALT)` label is conditional on a non-zero count.
7. **Every number in the regenerated report is identical to `cfbbcee`.** Any movement reported and the work stopped.
8. No candidate score on real data. No §9 value changed. Ambiguity escalated.

### Explicitly not authorized

**No change to the frozen protocol** (§9). **No sealed read.** **No real candidate runs.** **No edit to `contract_arms.py`**, `screening_harness.py`, `harness.py`, `test_fidelity.py`, `run_devproof.py`, or any `repair_*.py` other than `repair_relisting_factors.py`. **No change to any factor, register entry, or boundary expectation.** **No gap rule or structural filter in any arm.** **No scorer change.** **No new candidates, variants, or strategy code.** **No new ingestion (D4).**

### Next after this prompt

1. Claude **diff check** — stamp true, guard fires, numbers unmoved. Short.
2. **Operator authorizes Phase 2.**
3. Prompt 2 — candidate runs in the §11.3 order: **C2 → C3 → C4**, one report per candidate, committed as produced.

---

## Prompt 2 — Phase 2: the candidate runs (ISSUED 2026-07-17)

**Task:** Run C2, C3 and C4 on real dev data per the FROZEN protocol (`PSB2_PROTOCOL.md` Rev 4, `eb3d66f`). **One report per candidate, committed as produced, in the §11.3 order: C2 → C3 → C4.**

**Both gates are closed. Phase 2 is authorized by the operator (2026-07-17).**

- **§11.1** — substrate **CERTIFIED** at `fe01255`: four arms PASS, Arm B 4 splices / 4 dispositioned / 0 undocumented, continuity invariant 0, true stamp, dirty-source guard verified to fire.
- **§11.2** — harness dev-proof + Lead Review at `0d155b9`: C2 6.9σ, C3 4.7σ, C4 3.7σ; fidelity suite mutation-verified.
- Closing diff check: `docs/reports/PSB2_PHASE1R6_DIFF_CHECK.md` (`dc5db10`).

**This is the first time a candidate score touches real data.** Everything before this prompt existed to earn that.

**Status on completion:** returns to Claude for review, then Prompt 3 — the §8 selection report. **This prompt does not select a winner.**

### Start here: this prompt contains no expected values, and that is deliberate

**Every prompt in this sequence until now supplied the answer.** 1R4 handed you four exact residuals labelled "predictions" and they were transcribed rather than computed — my fault, as the 1R5 review records. **That failure mode does not exist here.**

> **This prompt states no expected mean IC, no expected spread, no expected power, and no expected p-value for any candidate. There is nothing to reproduce and nothing to match. The first real number is the result.**

**The only numbers below are structural** — grid-date counts, the fence date, `n*` — and each is derivable from `trading_calendar` before any score is computed.

**What that changes for you:** a candidate metric that looks wrong cannot be checked against an expectation, because there isn't one. **If something looks wrong, it is either a defect or a result, and the difference is decided by the code, not by whether the number is pleasing.** PSB-1 ran five candidates and recommended **none** — "no winner recommended" was the protocol working, not failing. **A null result here is a complete and successful outcome. Do not chase one away.**

### §1 — Run order and commit discipline (§11.3)

**C2 → C3 → C4. One report per candidate. Each committed as produced, before the next runs.**

- `docs/reports/PSB2_C2_REPORT.md` → commit → `PSB2_C3_REPORT.md` → commit → `PSB2_C4_REPORT.md` → commit.
- **Follow the PSB-1 precedent** (`PSB1_C{1..5}_REPORT.md`) for report shape.
- **§9 immutability is live the moment C2's report exists.** No definition, parameter, window, or metric may change afterward — **including for C3 and C4.** If C2's result suggests a better C3, **that is a PSB-3, not an edit.**
- **C3 consumes C2's *scorer*, not C2's *result*** (§5: `p_i(t)` is the percentile rank of the C2 score). That dependency is by design. Their null ICs are **not independent** — C3 reads C2's percentile rank — which is already recorded and is not a defect.
- **Report stamp:** apply 1R6's lesson. **Commit the code first, run against a clean tree, then commit the report.** A report cannot name the commit that contains it.

### §2 — The fence. This is the item with teeth.

**The dev fence is the only thing between this battery and a sealed read**, and §1 of the protocol makes it the first prohibition: *"Any load of price, delivery, volume, or universe data with `trade_date` or `rebalance_date` ≥ 2023-01-01"* is prohibited. Every loader **asserts and prints its observed `MAX(trade_date)`**.

**The dev-proof's fence check is a disclosed tautology and must not be carried into Phase 2 as-is.** `PSB2_PHASE1_DEVPROOF.md` records: *"Known limitation: load_panel tautology. Flag for operator."* `load_panel` applies the cutoff and the check then verifies the cutoff was applied — **it cannot fail.** On synthetic data that was tolerable. **On real data it is the whole fence.**

**Required:** the fence must be verified **against the store**, not against the loaded panel — i.e. the assertion's subject is the data the query could have returned, not the data a cutoff already removed. Concretely: **prove the fence by showing that a deliberately unfenced read of the same source returns rows beyond 2022-12-31 while the fenced read does not**, and that the fenced `MAX(trade_date)` equals the expected **2022-12-30** (the last dev full session, per the certification report's store stamps: fenced MAX `2022-12-30`, unfenced MAX `2026-07-09`).

**If the fenced and unfenced reads return the same `MAX`, the fence is not doing anything — stop and escalate.**

**Every candidate report prints its observed fenced `MAX(trade_date)`.** Unreported is not proven (R2-3).

### §3 — `n*` and the sole sealed exception (§7.1, §1)

`n*` requires counting grid dates in **2023-01-01 → 2026-06-30** — the sealed window. The protocol permits this and **only this**:

> *"Sole exception: §7's sealed-grid count reads **dates only** from `trading_calendar` (no prices, no symbols' data)."*

**Be surgical.** The query reads `trade_date` (and `n_symbols` for the full-session convention) from `trading_calendar` and **nothing else**. No join to prices, no join to universe, no symbol list, no aggregate over any priced column. **Compute `n*` exactly — do not use §7's `≈ 84` / `≈ 42`; those are the protocol's estimates, not values to reproduce.** Print both counts and the query that produced them.

**Any read of a priced or universe column beyond 2022-12-31 is a protocol breach — stop and escalate immediately.** This is the one place in the battery where a sealed read is even syntactically possible.

### §4 — What each report must contain (§6, §7, §8)

Per candidate, on its **declared window** (§3: C2/C3 `2020-09-04 → 2022-12-31`, 56 fortnightly dates; C4 `2012-01-01 → 2022-12-31`, 132 monthly dates):

1. **Mean IC** (Spearman rank), its **SD**, **t**, one-sided **p**, and **realized n** — the number of grid dates actually scored. §3 warns *"Realized per-name n will be lower"* than the grid count; **report both and do not conflate them.**
2. **Gross and net annualized top-quintile spread**, **turnover**, and **fee drag in bp/yr** — fees per §2 (`delivery_equity_fees`, era-accurate) plus **κ = 5 bp/side**.
3. **§7 projected power** — noncentral-t, noncentrality `δ / (SD_dev / √n*)`, `P(T ≥ t_{0.95, n*−1})`, against the **≥ 0.80** hurdle.
4. **AC₁ and Newey–West (lag 4) if AC₁ > 0.1** — **report-only, never gating** (§7.4). See §5 below.
5. **§4.2 imputed-forward-return robustness column** — delisting imputation = the date's worst realized forward return among scored names.
6. **§8 eligibility, stated explicitly:** (i) mean IC > 0; (ii) annualized net top-quintile spread > 0; (iii) power ≥ 0.80. **All three, or not eligible.**
7. **The common robustness sub-window** `2020-09-04 → 2022-12-31` (28 monthly grid dates for C4; for C2/C3 this is their entire declared window — **say so rather than duplicating the column**).
8. **The observed fenced `MAX(trade_date)`** (§2) and **`n*` with its exact count** (§3).

**Do not compute the §8 winner, the ranking, or the Bonferroni-deflated evidence floor.** That is Prompt 3. **Each report states its own eligibility and stops.**

### §5 — The AC₁ exposure must be visible, not repaired (§7)

The protocol discloses this and forbids fixing it:

> *"a fortnightly candidate with inflated AC₁ **can clear the frozen 0.80 hurdle on a simple-t projection that its own reported AC₁ shows is optimistic**. … The gating rule is not changed — this paragraph exists to state the exposure, not to repair it."*

C2 and C3's adjacent formations overlap in their 252-day delivery baseline, which changes slowly against a 15-day grid. **If C2 or C3 clears 0.80 on simple-t while its AC₁ says the projection is optimistic, report both numbers and the tension between them.** **Do not substitute the NW-adjusted power for the gating power** — that would be a §9 metric change and it is prohibited. **State the exposure; let the operator read it.**

### §6 — The turnover and fee-drag figures in §3 are rationale, not predictions

§3 and §5 carry design estimates — C2 *"turnover ~0.15 → fee drag ~78 bp/yr"*, C4 *"turnover ~0.17 … → ~2.5pp/yr"*. **These are the arguments for why the cadences were chosen. They are not predictions, and nothing may be tuned toward them.**

**This is the reviewer's own recurring error, stated so you do not inherit it:** four times this session I pinned a number I had not derived — the C4 33σ, the turnover ≈ 1/6, the gap rule, the "splice may resolve on its own." **Each was a plausible mechanism written as a conclusion.** If observed turnover comes in at 0.30 and drag at 200 bp/yr, **that is the result**, and the candidate's eligibility is decided by §8's three criteria — **not by whether it matched a parenthetical in the protocol.** Report the observed values and say plainly how they compare to the design estimate.

### Structural predictions — the only things predictable before the run

1. **Fenced `MAX(trade_date)` = 2022-12-30** on every loader; unfenced source reaches **2026-07-09**; **the two differ.**
2. **Grid dates:** C2/C3 fortnightly = **56**; C4 monthly = **132**; common sub-window = **28**. (Verified in Phase 1's grid-identity check; a mismatch means the real calendar disagrees with the synthetic one — **that is a finding, report it.**)
3. **`n*`** computed exactly from `trading_calendar` over `2023-01-01 → 2026-06-30`, dates only, both cadences printed.
4. **Determinism** (§10): same inputs → byte-identical outputs. Re-run each candidate and confirm.
5. **Nothing else is predicted.** Every candidate metric is a result.

### Scope discipline

**No weakening a check to make it pass. No tuning toward any estimate. Six rounds.**

**The stop-and-report triggers, and they are not negotiable:**
- Fenced and unfenced `MAX` agree → **the fence is dead. Stop.**
- Any sealed read beyond the §3 dates-only calendar count → **protocol breach. Stop.**
- Grid counts differ from 56/132/28 → **stop and report.**
- A candidate metric that looks implausible → **stop and report.** Do not adjust anything to make it plausible.

**Do not touch:** any §5 formula, any §9 pinned parameter, `contract_arms.py`, `screening_harness.py`, the certified substrate, the register, the factors. **§9 immutability binds from C2's first result.**

**Every number script-generated. No hand-edited numbers.**

### Acceptance criteria

1. Three reports — `PSB2_C2_REPORT.md`, `PSB2_C3_REPORT.md`, `PSB2_C4_REPORT.md` — **each committed as produced**, in order.
2. Each carries §4's items 1–8 in full.
3. **The fence is proven, not asserted** — fenced vs unfenced `MAX` shown to differ; `2022-12-30` observed; printed per loader.
4. `n*` computed exactly, dates-only, both cadences, query shown.
5. AC₁/NW reported; **gating power remains simple-t**; any tension stated.
6. Observed turnover and fee drag reported **and compared to** §3's design estimate, with no tuning toward it.
7. Each report states its own **§8 eligibility** (i/ii/iii) and **stops** — no ranking, no winner, no Bonferroni.
8. Determinism confirmed per candidate.
9. Report stamps true — code committed before the run (1R6's rule).
10. No §5/§9 change. No sealed read. No new ingestion. Ambiguity escalated.

### Explicitly not authorized

**No change to the frozen protocol** (§9) — no formula, parameter, window, metric, or selection rule. **No sealed read** beyond §3's dates-only calendar count. **No §8 selection, ranking, or winner** — that is Prompt 3. **No new candidates, variants, or parameter sweeps** (§9: exactly three). **No consumer or strategy code** — nothing lands in `core/strategies/` (§12). **No new ingestion** (D4). **No edits to `contract_arms.py`, `screening_harness.py`, the disposition register, or any factor.** **No tuning of anything toward any estimate.**

### Next after this prompt

1. Claude **review** — the fence first, then each report against §6/§7/§8.
2. Prompt 3 — the **§8 selection report**: eligibility, power ranking, Bonferroni-deflated evidence floor at **m = 3** (`p < 0.05`), the 0.02 tie band, and the declared-window vs sub-window ranking comparison. **"No winner recommended" is a valid and complete outcome** (§8; PSB-1's actual result).
3. Operator decides. Promotion, if any, happens only through a new full pre-registration (§12) — **never in this battery.**
