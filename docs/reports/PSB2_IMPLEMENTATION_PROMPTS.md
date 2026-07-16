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

### Next after this prompt

1. Claude re-reviews Rev 2.
2. Operator ratifies → **FROZEN**, §9 immutability attaches.
3. Prompt 1 (Phase 1 harness adaptation + synthetic dev-proof) issued.
