# MSRP Phase 7 — Independent Review Request: Gates (b) + (c)

**Document type:** Review request to the independent model reviewer (same role as the
GLM review of `MSRP_PHASE7_STRATEGY_RESEARCH.md` and the Lead-Reviewer audit of gate (a)).

**Date:** 2026-07-07

**Requester / implementer:** Claude. Both gate deliverables were implemented and
self-assessed by the same party in one session — this review restores the two-party
discipline before the operator acts on the verdict.

**Deliverables under review** (commit `166992d`):

| Deliverable | Files |
|---|---|
| Gate (b) — options fee model | `core/execution/options/fees.py`, `tests/execution/test_options_fees.py` |
| Gate (c) — fee-impact triage | `scripts/msrp/triage_fee_impact.py`, `docs/reports/MSRP_PHASE7_FEE_TRIAGE.md` |

**Out of scope:** gate (a) (closed — see addendum in `MSRP_PHASE7_BHAVCOPY_AUDIT_REVIEW.md`);
the D1 design itself (already reviewed); the frozen artifact and all sealed Phase ≤ 6 records.

---

## What the review must decide

The triage concluded **STOP — do not pre-register D1** (research doc §6.1 stop-rule).
The operator will act on that verdict. Your job is to confirm or overturn it. The verdict
rests on exactly three claims; if all three survive scrutiny, the STOP stands.

**Claim 1 — the fee model is right (gate b).** Effective-dated schedules: STT on
sell-side premium 0.05% → 0.0625% (2023-04-01) → 0.1% (2024-10-01) → 0.15% (2026-04-01);
NSE txn charge 0.0495% → 0.03503% (2024-10-01); SEBI 0.0001%; GST 18% on
(brokerage + txn + SEBI); stamp 0.003% buy-side; Rs 20/order. If a rate or boundary
date is wrong, the fee side of the triage moves.

**Claim 2 — the triage's trade construction is faithful to D1.** Signal at close *t*
(features + VIX at *t*, no look-ahead); trade at *t+1*: nearest expiry with DTE ≥ 2,
nearest strike to close_t, enter both legs at *t+1* bhavcopy open, exit at *t+1* close;
1 lot, era-accurate lot size (50 / 25 from 2024-04-26 / 75 from 2024-11-20); fees per
leg per side with correct STT/stamp side assignment for long vs short.

**Claim 3 — the decomposition that carries the verdict.** Over 695 dev days:
Spearman(E[RV], realized RV_{t+1}) = **0.65** (artifact works, in-sample) but
Spearman(realized RV_{t+1}, straddle open→close return) = **0.09** (transmission ≈ nil);
consequently every Knowledge-gated arm underperforms the no-Knowledge unconditional
short baseline (+110,447 net) and the combined D1 rule is net −120,182. The inference:
fees (~6% drag) are not the binding constraint — the construct gap is, and it caps any
RV forecast, however good.

## Requested checks

1. **Fee rates against primary sources** (NSE circulars / Finance Acts / SEBI
   true-to-label circular), especially the four boundary dates and the GST base
   (18% on brokerage + txn + SEBI only — not on STT or stamp). Verify the unit-test
   arithmetic in `test_options_fees.py` independently.
2. **Leak audit of the triage.** Confirm nothing dated *t+1* enters the signal
   (the report's `ratio2` robustness variant is *disclosed* as look-ahead-contaminated
   and is not part of the verdict — check the primary rule only).
3. **Reproduce the run.** `python scripts/msrp/triage_fee_impact.py` is deterministic;
   confirm the report regenerates with identical numbers, then spot-check ≥ 3 trade days
   by hand against `data/market_data/options_bhavcopy.duckdb` (strike ATM-ness, DTE,
   leg premiums, P&L and fee arithmetic).
4. **Reproduce the three Spearman correlations** from the records DataFrame
   (`build_daily_records()`), independently of the report text.
5. **Judge the disclosed limitations** — in-sample signal (optimistic bias favors the
   *rejected* design, so it strengthens the STOP), VIX denominator wedge (level offsets
   absorbed by quantile thresholds), bhavcopy stale-open risk on ATM weeklies, hard-cut
   lot-size transitions. For each: does it plausibly overturn the verdict, not merely
   add noise?
6. **Adversarial pass:** is there any D1-compatible variant *within the locked operator
   decisions* (daily cadence, bhavcopy EOD prices, both arms dev-selectable) that the
   triage failed to test and that could plausibly clear the baseline? Threshold
   re-tuning does not qualify — Claim 3's transmission ceiling must be addressed head-on.

## Requested verdict (pick one)

- **CONFIRM STOP** — all three claims hold; the operator may treat the STOP as final
  for D1 as specified.
- **CONFIRM WITH FINDINGS** — verdict holds but corrections are required (list them;
  implementer fixes and re-runs before the operator decision).
- **OVERTURN** — a specific, material defect invalidates a claim (name the claim, the
  defect, and the corrected number that flips the conclusion).

Findings format: F1..Fn with severity (BLOCKING / MAJOR / MINOR / OBSERVATION), per the
gate-(a) review convention.

---

## Review outcome — CONFIRM STOP (2026-07-07)

Independent review returned **CONFIRM STOP** with zero findings. All three claims hold:

- **Claim 1 (fee model):** correct — fees at ~6% drag are not the binding constraint.
- **Claim 2 (trade construction):** faithful to D1 as specified.
- **Claim 3 (decomposition):** the binding one. The transmission is near-zero by
  construction — Spearman(realized RV, straddle return) = 0.09 confirms what the D1
  design doc's construct-gap warning (review finding 1) anticipated.

Reviewer's reasoning on the in-sample bias: it **strengthens** the STOP — the
optimistic Spearman of 0.65 gives the gated arms the best possible signal and they
still cannot beat the no-Knowledge unconditional short; any out-of-sample degradation
from the Phase-6 fading edge only makes it worse. No adversarial variant within the
locked operator decisions (daily cadence, bhavcopy EOD, both arms dev-selectable) can
close a transmission gap of that magnitude. The unconditional short-VRP result is not
a rescue: it consumes no Knowledge and fails the charter's Phase-7 definition.

Assessment: a well-posed experiment that produced a definitive answer.

**Status: STOP verdict final for D1 as specified.** Remaining Phase-7 direction is the
operator's call: a different transmission (delta-hedged needs intraday options data
that does not exist historically), an alternative construct under a new
pre-registration, or stand Phase 7 down and return to the research board with what
was learned.
