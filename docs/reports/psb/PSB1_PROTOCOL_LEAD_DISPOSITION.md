# PSB-1 Protocol Independent Review — Lead Disposition

**Date:** 2026-07-13
**Author:** Claude (Lead Reviewer, protocol author)
**Review disposed:** `docs/reports/PSB1_PROTOCOL_INDEPENDENT_REVIEW.md` (DeepSeek V4, 2026-07-13) — verdict **APPROVE WITH MINOR REVISIONS**
**Outcome:** all findings **ACCEPTED** (F1–F5 + two minors + the Prompt-1 loader caveat); folded into `PSB1_PROTOCOL.md` **Rev 2**. Protocol remains DRAFT pending operator ratification.

---

## Dispositions

### F1 — Unequal-n confound in the selection statistic: ACCEPTED (verdict-affecting)

Verified by construction: t scales with √n, so the declared-window t-statistic hands C1/C2 (~572 weekly formations) a structural ~2× advantage over C3/C4 (~143) at identical IC/SD — a thumb on the scale against the delivery candidates the program was designed around.

**Resolution (Rev 2 §8):** ranking among eligible candidates is now by **maximum projected sealed power** (§7) — size-invariant across dev windows because it uses the common sealed n\*, and it is literally the program's objective ("most likely to clear a sealed gate"). The declared-window Bonferroni-deflated p is retained in two roles: (i) an **evidence floor** — a promotion recommendation still requires deflated p < 0.05, and its n-dependence there is *intentional* (less dev evidence should mean a harder promotion case); (ii) a robustness ranking column. **No cascade:** if the max-power eligible candidate fails the evidence floor, the battery reports "no winner recommended" — walking down the list is a forking path. Tie-break re-pinned for the power scale (it saturates near 1): powers within 0.02 are tied → smaller deflated p → higher net spread.

### F2 — Delisting exclusion inflates the reversal candidates: ACCEPTED (verdict-affecting)

Verified directionally: reversal scores are long recent losers, imminent delistings concentrate among recent losers, and §4.2's exclusion censors exactly that left tail — an upward bias landing on C1 and C4's revert leg, the most fee- and tail-sensitive candidates.

**Resolution (Rev 2 §4.2):** the primary metric keeps the exclusion (no synthesized return in the headline number), but every candidate report now carries a **mandatory robustness column** re-computing mean IC and net spread with a pinned imputation: a scored name with no price at *t'* receives that date's **worst realized forward return among scored names** — data-driven, no synthetic −100%. If a candidate's mean-IC sign differs between primary and imputed columns, the discrepancy is flagged to the operator; it can never be silently dropped.

### F3 — Weekly IC autocorrelation: ACCEPTED (disclosure + pinned trigger)

Correct: positive lag-1 AC in the IC series inflates the naive t and therefore §7's power projection — the quantity this program exists to state honestly. **Resolution (Rev 2 §6/§7):** every candidate reports its IC lag-1 autocorrelation; if |AC₁| > 0.1, a Newey–West (lag 4) t-statistic and a power projection using the NW-adjusted SE are reported as robustness columns. Primary stays the pre-registered simple t (changing the primary post-hoc per candidate would itself be a fork; the trigger and lags are pinned now).

### F4 — C4 continuation leg: ACCEPTED (ratification acknowledgment)

Correct observation: at `p_i(t) → 1`, C4's score is mechanically one-week continuation. The protocol's defense stands (conditions on delivery, one-week window, no sealed read), but the CSMP fence is a credibility fence. **Resolution (Rev 2 §5-C4):** operator ratification of this protocol explicitly acknowledges C4's continuation leg, and the successor program's D2 prior-exposure disclosure must cover it.

### F5 — Net spread is an upper bound: ACCEPTED (labeling)

**Resolution (Rev 2 §6):** the net top-quintile spread is labeled an **upper bound on realizable economics** (same-close formation, no execution lag) wherever it is reported.

### Minor — data-integrity stop rule false halts: ACCEPTED (re-scoped)

The >|20%| trigger as written would halt on legitimate earnings moves. **Resolution (Rev 2 §11.3):** the halt condition is re-scoped to the gate-(b) meaning — a large move that the corporate-action layer's classification would label **undocumented residue** (adjustment mismatch), not any large genuine move. Genuine large moves are logged, not halting.

### Minor — baseline fee symmetry: ACCEPTED (pinned)

**Resolution (Rev 2 §6):** the EW-universe baseline leg is charged the same gate-(d) fees + κ slippage on its own membership-churn turnover — the net spread is apples-to-apples by construction.

### Prompt-1 loader caveat: ACCEPTED (carried to Prompt 1)

`load_window()` selects `adj_close` only. **Resolution (Rev 2 §2, loader row):** the Phase-1 harness must carry `deliv_pct` through the **same `rn=1` turnover-primary listing pick** as the price, so delivery and price always describe the same listing. This is a named acceptance criterion for Prompt 1.

---

## Status after this disposition

`PSB1_PROTOCOL.md` is at **Rev 2**, DRAFT. Remaining path to freeze: operator ratification (which now explicitly includes the F4 acknowledgment) → stamp **FROZEN** → Prompt 1 (Phase-1 screening harness + synthetic dev-proof) issued to DeepSeek V4.
