# C2 Phase 0.5 — Turnover-Reduction Mini-Battery — Lead Review

**Reviewer:** Claude (Lead Reviewer)
**Date:** 2026-07-18
**Under review:** `docs/reports/C2_PHASE0_5_MINIBATTERY.md` (digest `d7c5d462`), `scripts/c2_phase0_5_minibattery.py`, `tests/csmp/test_phase0_5.py`
**Method:** ran the incumbent C2 on TRAIN 2011–2018 through the frozen harness as an anchor; recomputed every variant's power independently (noncentral-t) from reported IC/SD; recomputed the report digest; confirmed fidelity + tests.

---

## Verdict: **NO WINNER — CONFIRMED. C2 retire/shelve (roadmap path b) is the correct, evidence-based outcome. Sealed window and HOLDOUT both preserved.**

The terminal "no variant cleared TRAIN power ≥ 0.80" is independently sound. One recurring reporting defect (n label) is disclosed below; it does not change the verdict.

## What I independently confirmed

| Check | Result |
|---|---|
| Anchor: incumbent C2 on TRAIN 2011–2018 (frozen harness) | mean IC 0.022552, SD 0.100137, net −0.4348%, turnover 0.2884, power 0.6563 — **matches report ref row exactly** |
| Independent power recompute (noncentral-t, per-variant n*) | V1 0.4242 (n*=42), V2/V3/ref 0.6563 (n*=84) — **all match; all < 0.80** |
| Any variant clears 0.80 | **No** (wide margin) |
| Digest `d7c5d462` over sealed region | reproduces exactly |
| Fidelity (`test_fidelity.py`) | green → score_c2 provably frozen |
| Phase 0.5 tests | 9/9 (15/15 incl. fidelity) |
| HOLDOUT (2019–2022) | not scored for selection — single-look preserved, not spent |
| Sealed window (2023–2026) | untouched (fence proven both runs) |

**The finding is real and mechanistic.** Turnover reduction worked exactly as designed — V2's 0.60 band cut turnover 0.288 → 0.168 and lifted net −0.43% → −0.14% — but the gross spread on 2011–2018 is too small for *any* turnover setting to push net positive under delivery-equity fees (STT both legs). The signal (mean IC +0.023) is weaker on TRAIN than the PSB-2 sample (+0.035), and the fee floor is unforgiving. This is the fee-dominance result PSB-1/PSB-2 established, a third time. No turnover trick rescues a sub-gross-of-fees construct.

## Reporting defect (MEDIUM, non-blocking) — n label recurrence
My anchor scored **165** formations; the report labels ref "n = 215." Every statistic matches to 6 digits, so the IC vector is 165 elements — **215 is the fortnightly grid count**, not the scored n. This is the Phase 0.4 H2 conflation, **not carried into the new runner**. Non-blocking (power uses n*=84; mean/SD are on the 165), but the report should read "165 scored / 215 grid," and the fix should be back-ported to `c2_phase0_5_minibattery.py` so grid-vs-scored n stops recurring. Cosmetic also: §S6's "Candidates with power ≥ 0.80:" header lists candidates all below 0.80.

## Roadmap implication
- **C2 is retired.** PSB-2's sole recommendation does not survive the extended-history evidence-strengthening. This is Phase 0 doing its job: the cheap dev-side steps (0.4 re-estimation, 0.5 turnover battery) killed C2 **before** a single sealed read was spent.
- **The 2023–2026 sealed window was never read.** It remains a preserved, unspent asset for any future construct — no contamination, no burned one-shot.
- **No successor is authorized by this outcome.** Any new construct starts its own pre-registration; C2's retirement is a clean close, not a hand-off.

*Anchor numbers script-generated from the frozen harness + independent recompute. Sealed window unread; HOLDOUT unspent.*
