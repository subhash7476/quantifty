# M1c Protocol v1.1 — Residual Review (B2 / M2 / M3 / M8 resolutions only)

**Date:** 2026-09-29 · **Reviewed:** `M1C_RESEARCH_PROTOCOL_v1.1.md` (commit `cd0d670`). Scope: does any resolution of B2, M2, M3 or M8 create a *new* statistical or conceptual problem. Settled wording not reopened. No data, runs or code.

## Verdict per resolution

| Item | Original defect | Resolved? | New problem |
|---|---|---|---|
| B2 holdout | Undecided window | Yes: forward 250 sessions, blinded, one-shot | R-3 (CAS regime) |
| M2 null | Market-timing term in H0 | Yes: null is now clean | R-1 (estimand vs §2 boundary / MAP cell) |
| M3 isolation | §2 vs §4 contradiction | Yes: overlap admitted, report-only | R-4 (diagnostic contaminated by outcome) |
| M8 missing data | Judgement drops | Mechanical, exhaustive | R-2 (selection on future data; asymmetric bias) |

## Residual issues

**R-1 (M2) — MATERIAL. The netted estimand is a market-residual construction, but §2 still says "no market-residual construction" and "Not M1a/M1b".** f = s·(R_fwd − U_fwd) is a tail-names-versus-universe relative return, which is what M1a/M1b (status A, already tested) measure. On market-wide days most of the universe is in one tail, so U_fwd contains the cohort itself and market-wide reversion nets to ≈0 by construction. A pass therefore cannot be separated from known cross-sectional reversal and does not clearly fill MAP's M1c cell, which is defined as *absolute* reversion.
*Fix (either):* (a) keep the netted estimand, amend §2 to say only the *event definition* is non-residual, and state in §10/§13 that a pass credits M1c only as the "relative-to-universe form" with M1a overlap admitted; or (b) revert to fix (ii), raw f with an explicit statement that the estimand includes market-level reversal. Pick one before freeze.

**R-2 (M8) — MATERIAL. The mechanical rules select on future data, and the bias is asymmetric.**
- "Missing close in forward window with series continuing → drop" conditions eligibility on future trading and suspension. That is correlated with outcome and concentrated in the distressed tail.
- The terminal rule (zero accrual after the last close) records no loss after a delisting. Down-tail longs are disproportionately distress delisters, so the bias is toward positive f on the long leg. That favours H1, i.e. it is anti-conservative. Netting by U_fwd does not cancel it, because U barely contains those names.
- Requiring 316 *consecutive* closes on a bhavcopy-derived view is a de facto trading-frequency filter, which contradicts "no liquidity filter" in §3. The stated small-name-dominance disclosure is inaccurate.
*Fix:* keep the rules, but add report-only (a) per-leg counts of dropped and terminal-truncated formations for TRAIN and VAL, and (b) a pre-stated worst-case-bound sensitivity on VAL, with the pass labelled "attrition-fragile" if the bound flips the sign. Restate the §3 liquidity disclosure as "effective universe = names trading every session over the span".

**R-3 (B2) — MATERIAL. §7 says "all §9 windows are pre-CAS", which the forward HOLDOUT makes false.** Post-freeze sessions are CAS-era (live 2026-08-03). Category I closes become auction prints, and the first ~316 lookback sessions of holdout formations mix VWAP-close and auction-close regimes in the percentile reference. A regime shift between VAL and HOLDOUT also creates a confound for a reversion test (auction-print noise).
*Fix:* delete the sentence; pin "official bhavcopy close in every stage"; disclose the CAS break as a HOLDOUT non-stationarity; add a report-only Category I / II split of the HOLDOUT result.

**R-4 (M3) — MATERIAL. The §9.1 proxy uses forward prices.** "Closed back above that low within 3 sessions" classifies formation t using t+1..t+3, which overlaps the gap session and the forward window. A reclaim is partly the reversion outcome, so overlap rises with the effect itself, and the pre-stated "near-total overlap" reading in §11.4/§13 is confounded. Also undefined: the up-tail analogue, the threshold for "near-total", and what "replicated" means in §11.4.
*Fix:* define the proxy from information ≤ t only (breach of the prior 10-session low by C(t) or by the formation-window closes; drop the reclaim leg, or report it separately as outcome-dependent); state the up-tail mirror; pin a numeric "near-total" cut before any read; define "replicated" as "computed on VAL and recorded", with no threshold.

## Noted, not counted

- **R-5 (MINOR, arises from M2, in restored §11.3).** The fee rule prices only formation round trips, but the netted estimand is a hedged spread with a universe leg, and delivery-equity fees have no short leg. State that the fee gate is applied to the formation legs only, or pin the hedge-leg treatment.
- **HOLDOUT power (NO ISSUE, provided §12 is honoured).** 250 forward sessions against ~1,190 in VAL means an effect that just clears VAL has expected HOLDOUT t ≈ 0.46× the VAL t, so the gate is low-powered by design. This is already handled by §12/§15.2 (RFA must cover HOLDOUT size, else no read); keep it a hard precondition.

## Freeze recommendation

No new BLOCKER. **DO NOT FREEZE until R-1 to R-4 are corrected**; each is a targeted text change, no redesign.
