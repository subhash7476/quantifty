# PSB-2 Phase 1 — Dev-Proof Report (Prompt 1R2, Round 3)
**Script-generated** — `scripts/psb2/run_devproof.py`. Commit `947b99a`.
Seed `20260716`. 30 entities, 3500 calendar days. 2026-07-16.

## Grid Identity (R2-11)

- C2/C3 dev fortnightly: 56 (expected 56) — **PASS**
- C4 dev monthly: 132 (expected 132) — **PASS**
- Common sub-window: 28 (expected 28) — **PASS**
- First: 2020-09-15 (expected 2020-09-15) — **PASS**
- Last: 2022-12-30 (expected 2022-12-30) — **PASS**

## Signal Recovery (R2-1/R2-2)

Signal built as per-step drift over (t, tp]; delivery elevated in recent window.

| Candidate | Null IC (seed 0) | Null IC (seed 100) | Signal IC | C4 IC | Status |
|-----------|-----------------|-------------------|-----------|-------|--------|
| C2 | -0.0198 | -0.0727 | 0.1638 | 0.0208 | **FAIL** |
| C3 | -0.0556 | 0.0417 | 0.1034 | 0.0015 | **FAIL** |
| C4 | -0.0023 | -0.0068 | 0.5302 | 0.0603 | **PASS** |

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

Deliberate break: Deliberate break observed: stdout={"C2": null, "C3": null, "C4": null}... returncode=0

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

Time: 178.4s.
