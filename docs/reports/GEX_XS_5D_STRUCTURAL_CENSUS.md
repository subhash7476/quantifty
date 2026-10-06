# GEX-XS-5D — Structural census of the cross-section (pre-run, no outcomes)

**Date:** 2026-10-06 · **Script:** `scripts/gex_xs_5d/structural_census.py` · **Output:** `data/research/gex_xs_5d/xs_census_{dev,sealed}.csv`

**What it read:** stock-option chains and stock-futures closes on each phase-0 formation date. **What it did not read:** equity bars, any outcome, the results calendar, or any GEX value. It applied the frozen per-name validity rule (§4 D3) and checked whether an ATM IV exists on the frozen IV expiry (§5 D5). It then counted names. Results exclusions and control drops come later, so these counts are upper bounds on the final cross-section.

**Why it was run:** while timing the runner, a probe that always used the next-month expiry found few names with an ATM IV (8 of 85 on 2016-03-01). The frozen rule uses next month only when the near month expires inside the target window. If that failure held, expiry weeks would go void under the 80-name floor. This census measures it under the frozen rule.

## Result

| Stage | Formations | Below 80 names before later drops | Median names (no expiry in window) | Median names (expiry in window) |
|---|--:|--:|--:|--:|
| DEV | 339 | **6** (2016: 2, 2020: 4) | 140 | 132 |
| SEALED | 184 | **0** | 189 | 186.5 |

Per-year medians of names with an ATM IV are 107.5 (2016), 136, 145, 140, 124 (2020), 152 and 187 for DEV, and 184, 180, 210.5 and 206 for SEALED.

- **The next-month concern does not materialize.** Expiry weeks lose about 5 % of names, not most of them. The probe was misleading because it forced the next-month expiry on every date.
- **Expected voids are within the 10 % notice threshold (§8).** That is 6 + 3 in DEV, adding the three formations the strict in-stage control lookback voids by construction, plus any that results and control drops push under 80. In SEALED it is 0 + 3.
- **Disclosed as prior exposure:** this counted SEALED-window option chains for name validity and IV existence. It is structural data, of the same kind as the declaration's coverage census. It reads no outcome and computes no GEX.
