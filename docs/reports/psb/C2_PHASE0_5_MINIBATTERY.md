# C2 Phase 0.5 -- Turnover-Reduction Mini-Battery

## Fence Assertions

| Run | Observed MAX | Cutoff | Store MAX | Status |
|---|---|---|---|---|
| TRAIN | 2018-12-31 | 2018-12-31 | 2026-07-09 | PASS |
| HOLDOUT | 2022-12-30 | 2022-12-31 | 2026-07-09 | PASS |

## Variant Slate (S4)

| ID | Cadence | Exit band | Hold | Mechanism |
|---|---|---|---|---|
| V1 | monthly | 0.4 | single |  |
| V2 | fortnightly | 0.6 | single |  |
| V3 | fortnightly | 0.4 | staggered 3-period |  |
| ref | fortnightly | 0.4 | single | (reference, not counted) |

## Phase A: TRAIN Results (2011 -> 2018)

| ID | n | Mean IC | SD_IC | AC_1 | Net spread | Gross spread | Fee drag (bp) | Turnover | Power (n*) | Power >= 0.80? |
|---|---|---|---|---|---|---|---|---|---|
| V1 | 95 | 0.023391 | 0.102562 | -0.0974 | -2.9514% | -1.5423% | 155.1 | 0.3707 | 0.4242 (n*=42) | no |
| V2 | 215 | 0.022552 | 0.100137 | 0.0100 | -0.1441% | 1.1582% | 144.7 | 0.1679 | 0.6563 (n*=84) | no |
| V3 | 215 | 0.022552 | 0.100137 | 0.0100 | -0.6094% | 0.6636% | 141.8 | 0.1649 | 0.6563 (n*=84) | no |
| ref | 215 | 0.022552 | 0.100137 | 0.0100 | -0.4348% | 1.8777% | 245.7 | 0.2884 | 0.6563 (n*=84) | no |

### Selection (S6)

**No winner:** no variant cleared TRAIN power >= 0.80.

Candidates with power >= 0.80:
- V1: net=-2.9514%, power=0.4242
- V2: net=-0.1441%, power=0.6563
- V3: net=-0.6094%, power=0.6563

## Phase B: HOLDOUT Confirmation (2019 -> 2022)

No variant advanced to HOLDOUT confirmation.

---
**SHA-256:** `d7c5d46205449d692d89a36328a6581e50ca49f4a3e1d57acb71e5100de5bb91`
**Generated (outside seal):** 2026-07-18 10:30 UTC