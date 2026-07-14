# PSB-1 Substrate Certification Report

**Script-generated** — `scripts/psb1/certify_substrate.py`. Code commit `61d383b`. Real store, read-only.

Invariants accumulated across Prompts 2–4, tested independently on the post-Prompt-4 real store.

| # | Invariant | Result | Threshold | Evidence |
|---|---|:--:|---:|
| I-1  adj_close continuity (cons. grain) | FAIL | 0 | 2 violations |
| I-2  prev_close column fabrications | PASS | 0 | 0 |
| I-3  co-trading entities (overlapping spans) | PASS | 0 | 0 |
| I-4  (entity,ex_date) double-apply | PASS | 0 |  |
| I-5  first-session unadj. ex-date prev_close | PASS | 0 | 0 |
| I-6  universe_membership unchanged | PASS | 0 | real=35000 backup=35000 +0 / -0 |
| I-7  row count == 7,030,920 | PASS | 7030920 | 7030920 |
| I-8  gate-(b) §4 continuity | PASS | 0 | 20 mega-cap symbols |
| I-9  symbol_entity_intervals (1 DTIL split) | PASS | None | 4133 rows, multi=1 (DTILx2) |
| I-10 DVL→DTIL re-key confirmed | PASS | None | DVL=0 DTIL=1 BONUS |

**CERTIFICATION FAILED — invariants above must be resolved.**

### Violations: I-1  adj_close continuity (cons. grain)

- `('PCBL', datetime.date(2018, 4, 19), 1.049844926894107, 0.20996898537882144)`
- `('ESSENTIA', datetime.date(2022, 2, 7), 0.9999999999999999, 0.33333333333333337)`

