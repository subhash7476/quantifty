# M1c Protocol v1.2 — Independent Freeze Review

**Date:** 2026-09-29 · **Reviewed:** `M1C_RESEARCH_PROTOCOL_v1.2.md` (commit `bb58393`), full text incl. Change Log and consistency audit. No data, runs or code. Settled items not reopened.

## 1. Is the R-2 attrition bound actually conservative? — Directionally yes; not in all cases; and uncalibrated in size

Definitions (§3.2): m_L = minimum *retained* long-leg formation return, M_S = maximum *retained* short-leg formation return; every attrited formation (dropped **and** terminal-truncated) is replaced by its leg's worst retained value.

- **F-1 (MATERIAL) — not conservative for terminal-truncated formations, under the literal reading.** "Retained" reads as the complement of "attrited", and attrited includes terminal-truncated. Then m_L/M_S exclude terminal formations' own observed returns. A terminal formation whose observed return is worse than m_L (a delisting after a long fall is exactly this case) is replaced by the *better* value m_L, so the sensitivity improves it. That is anti-conservative for the very population the bound exists to cover.
  *Smallest fix:* one sentence — "a terminal-truncated formation is replaced by its leg's worst retained value only if that is worse for the leg than its observed return; otherwise its observed return stands", or equivalently count terminal formations in the retained set when computing m_L/M_S.
- **F-2 (MINOR) — the bound is an extreme-order statistic.** m_L/M_S are single-observation minima/maxima: (a) hostage to one outlier, including any surviving adjusted-price artifact; (b) stringency depends on stage size (VAL ≈ 5 years, HOLDOUT ≈ 1 year), so the two gates are not equally harsh; (c) the fragility verdict is decided by attrition rate × |m_L| rather than by the signal, so it can be near-unattainable. All of that is direction-safe (over-conservative), so it does not block freeze, but the protocol should say the harshness is accepted by design.
  *Smallest fix:* add to the §3.2 report-only list the identity of the m_L and M_S formations and the break-even attrition fraction (the fraction at which the stage mean crosses zero).
- **F-3 (MINOR) — "dropped" is ambiguous.** §3.1's trailing-span drops cannot be leg-classified (the formation never forms). *Fix:* define attrited = tail-classified formations whose forward window is dropped or truncated.
- **F-4 (MINOR, no change needed beyond reporting).** TRAIN pinning is not attrition-adjusted, and attrition (pro-H1 on the long leg) grows with H, so the pin leans slightly toward larger H. VAL is fenced by the fragility rule; report attrition per (family, H) combination on TRAIN.
- **Disclosed and correctly left unbounded:** the eligibility selection from the 316-session rule and beyond-sample wipeouts. Verdict on sufficiency: acceptable **only if the support claim is scoped** (F-5).
- **F-5 (MINOR).** Add to the §10 scope-limit sentence: a pass supports the pinned family/horizon **in the continuously-trading effective universe only**. The only unbounded bias is pro-H1 and concentrated in the tail, so the claim must carry the restriction.

## 2. Does Option A genuinely restore M1c? — Yes, as the MAP *cell*; one wording contradiction

Verified consistent across §1, §2, §6, §8, §10, §11, §14: event definition and estimand are both own-history, absolute, non-ranked and non-residual; f = s·R_fwd is the same object in §3.2, §8.1, §10 and §11.3; no netting formula survives (only prohibitions and the withdrawal record). This matches the MAP definition ("reverts in absolute terms").

- **F-6 (MINOR) — §2's mechanism narrative contradicts §1's disclosure.** §2 says exhaustion of *this instrument's* flow; §1 says a pass does not attribute to single-instrument exhaustion (market-wide reversal is part of the estimand). *Fix:* label the §2 narrative "motivating hypothesis"; state that the test supports the absolute-reversion cell only.
- **F-7 (MINOR) — residual drift term in H0.** Under no predictability E[f] = E[s·μ] + market-timing covariance. The covariance is disclosed; the sign-imbalance × drift term is not. It was assessed as second-order earlier, so no change of design, but it costs nothing to make inspectable: report E[s] and the unconditional mean forward return per stage (report-only).

## 3. Other v1.2 checks (no new contradiction found)

§7 CAS text, §9.1 formation-time proxy (no forward prices; "near-total" pinned at ≥ 90% on TRAIN; "replicated" defined), §9.2 split (cannot-overturn clause), §11.3 fee scope (formation legs only, long-side schedule as a cost-scale proxy — direction is right, since delivery STT exceeds the intraday sell-side schedule), §12 fragility outcomes, and the §11.5 / §12 / §13 fragility wording are mutually consistent.

## 4. Classification

- BLOCKERS: none.
- MATERIAL: F-1.
- MINOR: F-2, F-3, F-4, F-5, F-6, F-7.

## 5. Freeze recommendation

**FREEZE**, conditional on the one-sentence F-1 amendment (mechanical text, no re-review needed). F-2 to F-7 are clarifications that may be folded in at the same time.
