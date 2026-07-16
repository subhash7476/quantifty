# PSB-2 Phase 1 — Dev-Proof Report (Prompt 1R Remediation)
**Script-generated** — `scripts/psb2/run_devproof.py`. Commit `f961d19`.
Seed `20260716`. 20 entities, 3000 calendar days. Generated 2026-07-16.

## Grid Identity (1R-11) — Real `trading_calendar`

| Check | Expected | Got | Status |
|-------|----------|-----|--------|
| C2/C3 dev fortnightly | 56 | 56 | **PASS** |
| C4 dev monthly | 132 | 132 | **PASS** |
| Common sub-window monthly | 28 | 28 | **PASS** |
| Dev fortnightly first | 2020-09-15 | 2020-09-15 | **PASS** |
| Dev fortnightly last | 2022-12-30 | 2022-12-30 | **PASS** |

## C — Signal Recovery (1R-2)

C2/C3: signal in deliv_pct. C4: persistent momentum drift.

Prediction: signal IC > 0 AND >= 3x |null IC|.

| Candidate | Null IC | Signal IC | Mntm IC | Status |
|-----------|---------|-----------|---------|--------|
| C2 | -0.0687 | 0.0044 | 0.0526 | **FAIL** |
| C3 | -0.0811 | -0.0255 | -0.0427 | **FAIL** |
| C4 | -0.0144 | -0.0137 | 0.1147 | **PASS** |

## H — S1 Determinism (1R-1)

See S1 section below (run via `_s1_child.py`).

## F — Dev Fence (1R-5b)

Real store: 7,030,920 rows. Fenced MAX: 2022-12-30. Unfenced MAX: 2026-07-09.

Fence: **PASS**.

**Known limitation:** `load_panel`'s in-loader assert is tautological.
The real protection is `fence_check`'s three-way comparison.
`fence_check` reads `equity_bhavcopy_adjusted` metadata not listed in §1's
sole-exception clause. FROZEN protocol — flag for operator disposition.

## G — Fees (1R-4)

Signal C2: net=0.0793 < gross=0.1015 drag=240.2bp turnover=0.2869 PASS
Signal C3: net=-0.0519 < gross=-0.0111 drag=426.1bp turnover=0.6004 PASS
Signal C4: net=0.0163 < gross=0.0191 drag=29.9bp turnover=0.0726 PASS
Null C2: net=-0.1058 < gross=-0.0635 drag=443.1bp turnover=0.6254 PASS
Null C3: net=-0.1602 < gross=-0.1169 drag=452.2bp turnover=0.6785 PASS
Null C4: net=-0.0157 < gross=-0.0129 drag=29.3bp turnover=0.0729 PASS

## Summary

Time: 38.1s.
