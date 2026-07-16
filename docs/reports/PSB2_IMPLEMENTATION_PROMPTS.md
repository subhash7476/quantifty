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
