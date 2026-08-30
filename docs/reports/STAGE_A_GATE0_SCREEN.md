# Stage A — Gate 0 Screen (script-generated)

**Generated:** 2026-08-29 by `scripts/stage_a/gate0.py`  
**Data read: NONE.** Fee schedules, declared anchors, and power arithmetic only.  
**Status:** a screen, not a result. Nothing here measures any phenomenon.

## 0a — Cost floor (era-accurate, frozen fee module)

Round-trip futures cost at the canonical Rs 2Cr notional (`core/execution/futures/futures_fees.py`), plus the measured slippage lane (0.66-0.78 bp/side, both sides) and the D5 basis mean (0.4 bp).

| Window | Fees mean | min | max | Round-trip cost lane |
|---|---:|---:|---:|---:|
| DISCOVERY 2012-2018 | 2.667 | 2.517 | 3.217 | **4.39-4.63 bp** |
| HOLDOUT   2019-2022 | 2.042 | 1.743 | 2.543 | **3.76-4.00 bp** |
| SEALED    2023-today | 2.340 | 1.743 | 2.693 | **4.06-4.30 bp** |
| CURRENT   2024-10+ | 2.693 | 2.693 | 2.693 | **4.41-4.65 bp** |

**Applied cost floor (current era, midpoint): 4.53 bp round trip.**

## 0c — The invariant: required NET annualized Sharpe per gate

`ncp = S_ann * sqrt(T)`, so cadence cancels. The Sharpe required for power 0.8 at one-sided a=0.05 therefore depends ONLY on the gate's calendar length — **not** on horizon, event density, or conditioning. Every family in the slate faces the identical bar.

| Gate | n (1 trade/session) | Required NET S_ann |
|---|---:|---:|
| HOLDOUT 2019-2022  (first alpha gate under Stage A) | 988 | **1.219** |
| TRAIN   2012-2018  (if it still carried alpha) | 1699 | **0.929** |
| SEALED  2023-today | 873 | **1.297** |
| SEALED  at A's power floor | 1270 | **1.075** |

**The governing number is 1.22** — the net annualized Sharpe a construct must deliver to be settleable at HOLDOUT. It does not move if you trade more often, condition harder, or pick a different horizon.

**Judged against A's ratified NET band** (the only operator-approved effect band for this substrate) — like for like, net against net:

- pessimistic 0.70 — **below** the 1.22 requirement
- central 1.075 — **below** the requirement (this is the section-8 defect: HOLDOUT cannot settle the central case)
- optimistic 1.45 — **above** the requirement (which is why the RFA returned PROCEED at the optimistic corner)

So under the section-8 amendment (**judge at the central corner**), the HOLDOUT gate cannot settle ANY construct on this substrate whose honest central net S_ann is below 1.22. That is family-invariant and is the first Gate-0 finding.

**The only same-substrate empirical anchor** is A's own realized TRAIN net: 1.271 bp/trade (`trial_ledger.jsonl`, script-generated) = S_ann **0.20** — **6.2x below** the requirement. For reference RS-MOM was abandoned for requiring S_ann >= 1.30.

## 0c (cont.) — Where the families differ: the cost drag

Cost is a **fixed** bp charge per round trip, so in Sharpe terms its bite grows as the horizon shrinks: `drag_ann = (cost_bp / SD_horizon) * sqrt(cadence)`. Required **gross** S_ann = required net + drag.

**Gross ceiling used below: 2.15** — derived, not invented: A's ratified optimistic NET corner (1.45) plus A's own cost drag (0.70). It is the most generous GROSS reading the operator has ever approved for this substrate.

| Family | Scenario | Horizon | Trades/yr | SD | Cost drag | **Req. GROSS S_ann** | vs A measured | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| F-OPEN | A's design (EOD hold, 1/session) | 313m | 237 | 100 bp | 0.70 | **1.92** | 2.8x | PLAUSIBLE |
| F-OPEN | short-horizon variant | 60m | 237 | 44 bp | 1.59 | **2.81** | 4.1x | IMPLAUSIBLE |
| F-GAP | large-gap conditioned, EOD hold | 313m | 78 | 100 bp | 0.40 | **1.62** | 2.4x | PLAUSIBLE |
| F-VOL | vol-state conditional | 120m | 190 | 62 bp | 1.01 | **2.23** | 3.3x | IMPLAUSIBLE |
| F-RANGE | breakout | 60m | 152 | 44 bp | 1.28 | **2.49** | 3.7x | IMPLAUSIBLE |
| F-RANGE | failed breakout | 60m | 59 | 44 bp | 0.80 | **2.02** | 3.0x | PLAUSIBLE |
| F-TOD | time-of-day bucket, standalone | 60m | 237 | 44 bp | 1.59 | **2.81** | 4.1x | IMPLAUSIBLE |
| F-REL | N/BN divergence, 30-min | 30m | 356 | 31 bp | 2.76 | **3.98** | 5.9x | IMPLAUSIBLE |
| F-REL | N/BN divergence, 15-min | 15m | 630 | 22 bp | 5.20 | **6.42** | 9.5x | IMPLAUSIBLE |

**Families clearing the ratified gross ceiling (2.15): 3 of 9.** The "vs A measured" column is the multiple of A's TRAIN gross S_ann (0.68) each family would have to deliver.

> **Caveat on A's gross figure.** `A_HOLDOUT_CLOSURE.md` decomposes TRAIN as gross +4.41 bp, fees ~1.8 bp, slippage 1.46 bp, net +1.27 bp. That does not reconcile: the frozen fee module A's own code calls returns a **2.667 bp** mean over TRAIN, not 1.8 bp, and 4.41 - 4.53 is negative where the ledger records +1.27. The ledger's **net** is script-generated and trusted; the narrative **gross** is not. Treat A's gross S_ann as a range ~0.68–0.89 and the multiples above as indicative. Flagged for the operator; not resolved here (resolving it is a DISCOVERY read).

### Diagnostic — where the cost drag stops binding (leaves the intraday quadrant)

Holding across sessions amortizes one round trip over a larger move. This is the ISD reassessment's option (b), **not** intraday, and it carries overnight risk the intraday quadrant does not.

| Hold | Trades/yr | SD | Cost drag | Req. GROSS S_ann |
|---|---:|---:|---:|---:|
| 2 sessions | 118 | 141 bp | 0.35 | **1.57** |
| 3 sessions | 79 | 173 bp | 0.23 | **1.45** |
| 5 sessions | 47 | 224 bp | 0.14 | **1.36** |
| 10 sessions | 24 | 316 bp | 0.07 | **1.29** |

The drag falls toward zero, but the floor never goes below the invariant **1.22** net. Longer holds fix the *cost* problem and leave the *demonstrability* problem untouched.
