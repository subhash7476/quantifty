# ISD-OVERNIGHT-GAP — Research Feasibility Assessment

**VERDICT: PROCEED** — not provably infeasible — this is a floor, not authorization to build.

- Methodology version: `2.0.0`
- Declaration SHA-256: `e476a03b0d13fb1814cfe246d4c0d17a71f17359fc03f94d157a458724c7862f`
- Metric: rank_ic | Test: one_sided | Power hurdle: 0.8
- Formations available: 317 (daily, Same fences as ISD-OPEN-DRIVE: TRAIN 2023-01-02 -> 2024-11-30 (474); HOLDOUT 2024-12-01 -> 2025-12-31 (270); SEALED 2026-01-01 -> present, spent only at n_sealed >= 317 AND Q5 paper interval complete. n_available = 317.

TRAIN double-duty disclosure: this family reads TRAIN twice (sign discovery once, then the family IC gate); both are declared and accounted in the pre-registration's multiplicity accounting (m = 2). The sign registration and its digest are recorded in the trial ledger BEFORE the HOLDOUT read is taken.

Substrate: native-only; vendor archive excluded by rule (Q1). AC1 disclosure identical to ISD-OPEN-DRIVE (NW/AC1-corrected harness statistics; RFA gate no AC haircut; optimistic corner clears at AC1 = 0.3, effective n ~ 171, corner power ~ 0.92).)

## Optimistic corner

| Quantity | Value |
|---|---|
| delta (high) | 0.035 |
| SD (low) | 0.15 |
| n (raw, no AC haircut) | 317 |
| **Max achievable power** | **0.9938** |

The corner is **intentionally unrealistic.** This independence holds for
`rank_ic` because IC mean and IC dispersion are separately estimable — a
declaration coupling them (e.g. deriving one from the other) is invalid and
the gate's `validate()` will reject it. With independence established,
(delta_hi, sd_lo) describes a large edge with unusually stable outcomes —
the least plausible combination in practice and the most generous to the
construct. This maximizes the burden of proof for ABANDON, so a firing gate
is unarguable, while correspondingly weakening PROCEED to its stated meaning
of *not provably infeasible*.

## Formations required for power 0.80

| Band point | n required |
|---|---|
| Optimistic corner | 115 |
| Central | 329 |
| Pessimistic | 968 |
| **Available** | **317** |

## Declared bands and provenance

**delta: [0.02, 0.035]**

Family 4 (overnight-gap cross-sectional): daily cross-sectional rank IC of the stock-specific overnight gap - (09:15 auction open - prev_close)/prev_close, from the certified daily store joined on PIT ISIN keys (G5 machinery; CA ex-dates excluded) - against the SAME-DAY hold-leg return (09:16 open -> 15:29 close).

SIGN: not pinned by mechanism - the gap has an information component (news: intraday continuation) and a noise/overreaction component (opening-auction liquidity provision: intraday fade), and the two cannot be separated ex-ante without event classification (a tuning surface, refused). The direction is therefore discovered ONCE on TRAIN (474 formations) and then frozen - the declared CARRY precedent (v1 sign discovery, v2 registered). The confirmatory tests (HOLDOUT, SEALED) are one-sided in the TRAIN-registered direction; the opposite direction reads as failure. Effective m = 2 for this family (sign discovery + family IC gate), disclosed in the pre-registration (ISD_PHASE0_CANDIDATE_RANKING_REVIEW R3).

Defense of magnitude [0.020, 0.035]:
Plausibility envelope anchored on the nearest in-house OOS cross-sectional read (CB-N50 HOLDOUT IC +0.029, daily close-to-close, 50 names) - an anchor of plausibility, not precedent: no direct prior exists for gap cross-sectionals (review R7). Literature on the gap sign is directionally split (below), but both camps document GAP-SIZE effects of comparable magnitude to ordinary daily cross-sectional effects:
(a) Fade side: Berkman, Koch, Tuttle & Zhang (2012, JFE) - retail-sentiment-driven overnight moves reverse intraday; the classical gap-fill statistic (time-series, single-instrument) was a high-power NULL in the FTMO corpus on USTEC/XAUUSD - the cross-sectional version here is the untested quadrant.
(b) Continue side: information-runup literature - news gaps continue as information diffuses; the tug-of-war decomposition (Lou, Polk & Skouras 2019, JFE) is MONTHLY-horizon and says nothing decisive about same-day intraday gap behavior.
(c) The band is symmetric about the CB-N50 anchor because the two mechanisms are judged roughly equal ex-ante; TRAIN resolves the sign and the magnitude band is frozen regardless of what TRAIN shows.

**SD: [0.15, 0.25]**

Identical cross-section to ISD-OPEN-DRIVE (the ~200-name certified native 1m panel, G5 PIT membership) - same band [0.15, 0.25], same rationale: the 200-name cross-section reduces the sampling-noise component of daily rank-IC versus CB-N50's 50-name panel (sd_lo = 0.15 defensible), while daily-frequency return noise and regime variation keep sd_hi = 0.25 honest. The gap feature is measured from the certified daily store (prev_close) joined on PIT ISIN keys; gap measurement noise (auction print vs bar construction) is bounded by the G4 certification (first-bar artifact: 36 rows/65M, all classified and immaterial).

No TRAIN read has been taken; SD is re-measured on TRAIN (474 formations) for the harness's Newey-West statistics; the frozen band is not revised in response.

**Prior exposure**

Same program-wide inventory as ISD-OPEN-DRIVE (see ISD_PHASE0_CANDIDATE_RANKING.md v3, S1):

1. Native equity 1m store read ONLY by Phase-1 certification (G1-G7); no signal-level read. The certified DAILY equity store (prev_close, CA ground truth) has been read by CSMP/CARRY/PSB research - as a substrate, not for gap-feature ICs.

2. CB-N50 (CLOSED, TRAIN+HOLDOUT burned): daily close-to-close cross-sectional reversal +0.029 HOLDOUT; daily momentum -0.02. Closest in-house anchor for daily cross-sectional predictability; different feature family.

3. Index-pair research: intraday index ratio TRENDS - index-level continuation prior; no gap-feature read.

4. FTMO corpus: time-series gap-fade / ORB null (0/41) - the single-instrument flavor of exactly this family's fade hypothesis; scoped to the time-series quadrant.

5. PSB-1/2 (CLOSED): monthly/fortnightly delivery-equity - fee-died; delivery-% is a READ factor and is NOT used here (no conditioning covariates in v1).

6. CARRY / TS Basis (production / research-only): monthly/daily cross-sectional basis over ~180 SSF names - different feature space; TS Basis Daily is selection-contaminated research-only, not a prior either way.

7. SEALED 2026-01-01 -> spend date (n >= 317): genuinely unread.

## Scope

This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,
turnover, or economic significance. A construct can clear this gate and still fail
on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not
clearance.
