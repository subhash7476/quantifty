# Review — F1 Feasibility Screen Report

**Reviewed:** 2026-07-20
**Artifact under review:** `docs/reports/F1_FEASIBILITY_SCREEN_REPORT.md` (generated 2026-07-19T20:23:09)
**Against:** `docs/reports/F1_FEASIBILITY_SCREEN_SPEC.md` (DRAFT) and `scripts/sfb/f1_feasibility_screen.py`
**Supersedes:** `F1_FEASIBILITY_SCREEN_CODE_REVIEW.md` (2026-07-19)

**Decision: the reported NO-GO is not supported as computed. Do not act on it in either direction.**

## Relation to the prior review

The prior code review BLOCKED on C1–C3: the bracket ladder was never called, the hold was 1 trading day, and cost omitted roll turnover and the early-era pessimistic lean. **The corrective pass genuinely fixed all three.** The bracket is now wired into `simulate_portfolio` (`:347-357`), the hold runs to the next formation date (`:315-321`), roll cost is charged (`:370-373`), and `TRAIN_SLIPPAGE_MULT = 1.5` is applied (`:298`). H1's `bp/yr` mislabel is addressed — the drag is now annualized (`:407-408`). Real daily high/low are loaded (`:116-146`), resolving M1's substrate gap.

The findings below are **new, second-order issues** in the corrected run, not a re-litigation of C1–C3.

## Findings

### CRITICAL

**R1 — The NO-GO verdict does not follow from the spec's decision rule.**

Spec §6 lists three NO-GO triggers. Against the reported numbers, **none of them fire**:

| §6 NO-GO trigger | Reported | Fires? |
|---|---|---|
| Net expectancy ≤ 0 anywhere in the band on TRAIN | +0.0149 / +0.0127 / **+0.0082** | No |
| HOLDOUT sign-flips | +0.0314 / +0.0299 / +0.0269, all positive | No |
| Turnover-drag consumes the gross edge | gross +0.0176 → net +0.0082 (edge reduced ~53%, not consumed) | No |

The verdict comes **entirely** from `decide()`'s `turnover_drag_bp_yr > 1000` check (`f1_feasibility_screen.py:467`) — a threshold that appears nowhere in §6. It fires at 1126 bp/yr in a case where §6's own "edge consumed" condition is explicitly false: net expectancy stays at +0.0082/formation (≈ +10%/yr against ~21%/yr gross).

The spec is a DRAFT and explicitly "not a pre-registration," so this is not a pre-registration violation. It is an **undisclosed deviation from the stated decision rule**: the report presents a verdict as though §6 produced it, and §6 does not.

Compounding this, the threshold is compared against a fragile quantity. `n_yr = len(all_net) / (cutoff.year - form_dates[0].year)` (`:407`) mixes a count of *simulated* formations with a *calendar-year* span taken from an unused first element:

- TRAIN: 95 / (2018 − **2010**) = 11.875/yr → drag 1126 bp/yr. (Reproduced exactly; this arithmetic only works with `form_dates[0].year = 2010`, which independently confirms R3.)
- HOLDOUT: 47 / (2022 − 2019) = 15.67/yr → drag 1005 bp/yr, vs. a true ~11.75/yr → ~750 bp/yr. **Overstated ~30%.**

TRAIN lands near the correct 12/yr by coincidence. HOLDOUT does not. A 1126-vs-1000 verdict should not rest on a denominator that is demonstrably wrong 30% of the time it is evaluated.

**R2 — The bracket is selected to near-inert and implemented optimistically, biasing every number toward GO.**

Two independent problems in the mechanic the spec calls the defining feature of the construct:

*Selected to grid edge.* `select_bracket` (`:435-450`) grid-searches 64 combinations on TRAIN and returns **n=5 (grid minimum), k_sl=2.5 (grid maximum), k_tp=5.0 (grid maximum)** — the shortest hold window with the widest possible stop and target, i.e. the configuration that fires *least often*. Corroborating symptom: `DaysH` is **exactly 5.0 on all six report rows**. Since `max_days` takes the max across names (`:379`), this means at least one name per formation never triggers within the 5-day window and falls through to the month-end fallback (`:353-357`). The optimizer is selecting the bracket away.

*Implemented optimistically.* `_apply_bracket` (`:267-273`) checks **take-profit before stop-loss** within each bar — if both levels are breached intraday, it books the profit. Spec §3 mandates the opposite: a conservative ladder of "open-gap → **worst-case whiplash** → High/Low intercept → period-close fallback." Neither the open-gap step nor the worst-case whiplash step is implemented; fills are assumed at exactly `min(high, tp)` / `max(low, sl)`, so a gap straight through a stop still fills at the stop. Both deviations bias toward GO.

The prior review's core critique — *the screen is not running the construct it claims to* — therefore partially survives its own fix. The bracket is wired in but is neither conservative nor materially active.

*Reporting gap:* the report's "Best Bracket Params (TRAIN-selected)" line does not disclose that 64 combinations were searched on a fold §0 already flags as not clean, nor that the winner sits at three grid boundaries — which normally indicates the true optimum lies outside the grid.

**Net effect of R1 + R2:** the verdict is driven by a rule the spec does not contain, applied to numbers produced by a construct biased in the opposite direction. **This review does not adjudicate GO vs. NO-GO** — a corrected run could plausibly land either way, and the pattern is unusual enough to warrant it (TRAIN weak and ambiguous, HOLDOUT robustly positive, which is the inverse of the normal overfitting signature).

### HIGH

**R3 — TRAIN is mislabelled; it silently includes 2010–2011.**
`train_fd = sorted([d for d in active if d <= TRAIN_HI])` (`:562`) has **no lower bound**. Verified against the store: the calendar spans **2010-01-04** to 2022-12-30, giving 108 candidate month-ends ≤ 2018-12-31 against only **84** in 2012–2018. The report's n=95 exceeds 84 by 11, confirming pre-2012 formations are included. The report's heading "## TRAIN (2012-2018)" is false — the actual span is roughly 2011-02 to 2018-12. This also means `select_bracket` fitted the ladder on a wider window than declared.

**R4 — The confidence interval is computed, reported, and then ignored by the decision rule.**
TRAIN expectancy CI straddles zero at both **mid (−0.0019, +0.0272)** and **pessimistic (−0.0064, +0.0227)**. Spec §6's GO condition requires net expectancy "**robustly** positive across the *full* band on **both** TRAIN and HOLDOUT," and §4's conservatism invariant makes optimistic-end-only survival a NO-GO. A CI containing zero at the conservative end is the most direct evidence in the whole report bearing on that criterion — and `decide()` (`:455-477`) never reads `expectancy_ci`. Whatever the verdict ends up being, it should be derived from this, not from an ad-hoc drag threshold.

### MEDIUM

**R5 — Liquidity floor misstated by 10× in the report.** `LIQ_MIN_MEDIAN_TURNOVER = 50_000_000` is **Rs 5 crore**, but `:529` formats it as `Rs{…/1e6:.0f}cr` → "Rs50cr" (1 crore = 1e7, not 1e6). The report overstates its own universe filter tenfold. A Rs 5cr median-turnover floor is very loose as an F&O-eligibility proxy — over-inclusive, an optimistic bias on tradability. Spec §2 accepts that direction *only* for a robust NO-GO; it is not acceptable support for a GO.

**R6 — Cost params were never calibrated from the real futures panel, and the report does not say so.** Spec §2/§4 require bounding roll frequency and per-roll round-trips from the observed roll structure in the 2023+ `futures_candles` panel. The script hardcodes `ROLL_ROUND_TRIPS_PER_FORMATION = 0.5` and the slippage band as constants with no reference to `futures_candles` anywhere. The report's Configuration block lists "Roll cost: 0.5 extra round-trips/formation" as if calibrated. Given the drag threshold is the sole verdict driver (R1), an uncalibrated roll assumption is load-bearing.

**R7 — `DaysH` is not a mean days-held, and is degenerate here.** `all_days.append(max_days)` (`:382`) records the **max** across the ≤10 names, reported as `days_held_mean`. Worse, the month-end fallback (`:353-357`) exits at the next formation close — up to ~21 sessions later — while hardcoding `days_held = n_max` (5). The reported holding period is therefore understated by roughly 4× for every fallback trade, which R2 shows is most of them.

**R8 — Basis/carry disclosure missing.** Spec §3 requires the ignored basis-convergence term to be disclosed. The report's Caveat 2 covers roll, bid-ask, and impact — not basis.

### LOW

**R9 — `NameError` on the no-eligible-formations path.** `:556` calls `print(report)` before `report` is assigned. Unreachable in this run, but it would crash instead of writing the intended report.

**R10 — `decide()` double-checks TRAIN when HOLDOUT is empty.** `:598` passes `train_results` as the holdout argument. Harmless here; misleading if it ever fires.

**R11 — Bootstrap block truncation.** `blocks[:len(arr)]` (`:422`) truncates the last sampled block, slightly biasing toward earlier-drawn blocks. Immaterial at n=95.

**R12 — Position notional is an undisclosed free parameter.** `POSITION_NOTIONAL = 1_000_000` sets the base for the fixed-fee components; cost-as-a-fraction therefore depends on a constant that appears nowhere in the report's Configuration block.

## Required before this report can support a spend decision

1. Derive the verdict from §6's stated criteria, using the CI (R4) rather than an ad-hoc drag threshold — or amend §6 to contain the threshold and say so in the report.
2. Fix `n_yr` to use the actual formation span, not `cutoff.year − form_dates[0].year` (R1).
3. Implement the spec §3 conservative ladder: SL before TP on same-bar breach, plus the open-gap step (R2).
4. Bound TRAIN below at 2012-01-01, or relabel the window honestly (R3).
5. Calibrate roll cost from `futures_candles` as §4 requires, or disclose it as an assumption in the report body (R6).
6. Fix the Rs5cr/Rs50cr label (R5); report `DaysH` as a mean and stop hardcoding it on the fallback path (R7).
7. Re-run and let the verdict fall where it falls. Note that a GO would additionally require clearing R2's optimistic bias and R5's over-inclusive universe — under spec §0/§2, an optimistically-biased screen can support a NO-GO but not a GO.
