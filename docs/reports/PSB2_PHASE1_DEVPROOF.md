# PSB-2 Phase 1 — Dev-Proof Report (Prompt 1R2, Round 3)
**Script-generated** — `scripts/psb2/run_devproof.py`. Commit `0b30800`.
Seed `20260716`. 30 entities, 3500 calendar days. 2026-07-17.

## Grid Identity (R2-11)

- C2/C3 dev fortnightly: 56 (expected 56) — **PASS**
- C4 dev monthly: 132 (expected 132) — **PASS**
- Common sub-window: 28 (expected 28) — **PASS**
- First: 2020-09-15 (expected 2020-09-15) — **PASS**
- Last: 2022-12-30 (expected 2022-12-30) — **PASS**

## Signal Recovery (R2-1/R2-2, R3-3 criterion corrected)

Signal built as per-step drift over (t, tp]; delivery elevated in recent window.

Prediction: signal IC > 3x null SE (corrected from 1R's 3x|null IC| per R3-3).

| Candidate | Null IC (s0) | Null IC (s100) | Null SE | Signal IC | C4 IC | Sig/SE | Status |
|-----------|-------------|----------------|---------|-----------|-------|--------|--------|
| C2 | -0.0198 | -0.0727 | 0.0236 | 0.1638 | 0.0208 | 6.9x | **PASS** |
| C3 | -0.0556 | 0.0417 | 0.0219 | 0.1034 | 0.0015 | 4.7x | **PASS** |
| C4 | -0.0023 | -0.0068 | 0.0163 | 0.5302 | 0.0603 | 3.7x | **PASS** |

*Note: C2/C3 originally FAIL under 1R's 3x|null IC| criterion (divides by noise draw).
Corrected per R3-3 to 3x null SE. All three > 3.0 sigma. See Prompt 1R3 R3-3.*

## Null Prediction (R2-4)

| Candidate | Seed 0 | Seed 100 | |IC| < 0.05? |
|-----------|--------|----------|-------------|
| C2 | -0.0198 | -0.0727 | FAIL |
| C3 | -0.0556 | 0.0417 | FAIL |
| C4 | -0.0023 | -0.0068 | PASS |

## S1 Determinism (R2-3)

PYTHONHASHSEED=0: `8453b3e86f4089a9...`  
PYTHONHASHSEED=1: `8453b3e86f4089a9...`  
Result: **IDENTICAL**
Sample: Sealed fence OK: observed MAX(trade_date)=2022-12-30 <= cuto...

Deliberate break: Broken child returncode=1 (expect !=0): GUARD TRIPPED. All guards: PASS.

## Fence (R2-5b)

Store: 7,030,920. Fenced: 2022-12-30. Unfenced: 2026-07-09. **PASS**.

Known limitation: load_panel tautology. Flag for operator.

## Missing-Forward Panel (R2-7)

Primary IC: 0.0129, Imputed IC: 0.0185, Different: **YES**

## G — Fees

Signal C2: net=0.2529 < gross=0.2922 drag=400.0bp to=0.3917 PASS
Signal C3: net=0.1682 < gross=0.2152 drag=476.8bp to=0.4986 PASS
Signal C4: net=0.9714 < gross=0.9738 drag=25.0bp to=0.0278 PASS
Null C2: net=-0.0805 < gross=-0.0371 drag=441.4bp to=0.6094 PASS
Null C3: net=-0.0966 < gross=-0.0549 drag=424.8bp to=0.5969 PASS
Null C4: net=-0.0037 < gross=-0.0011 drag=28.0bp to=0.0692 PASS

## Summary

Time: 75.0s.
