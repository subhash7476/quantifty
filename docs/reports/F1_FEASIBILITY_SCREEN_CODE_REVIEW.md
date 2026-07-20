# Code Review — F1 Feasibility Screen

**Reviewed:** 2026-07-19
**Scope:** uncommitted working tree — `scripts/sfb/f1_feasibility_screen.py`, `docs/reports/F1_FEASIBILITY_SCREEN_REPORT.md`, `docs/reports/F1_FEASIBILITY_SCREEN_SPEC.md`, `tests/sfb/test_f1_feasibility_screen.py`; plus the `core/execution/futures.py` → `futures/` package split (docstring/reference-only changes).
**Decision:** **BLOCK** — the GO verdict is not supported by what the code actually computes.

## Summary

The harness runs and produces a GO, but the simulation does **not implement the pre-registered F1 construct** from the spec. Three spec-mandated mechanics are missing or wrong, and every deviation biases the result toward GO. The verdict authorizes spending money on vendor data, so this is decision-critical, not cosmetic.

The `futures.py`→`futures/` package split (separate workstream) is a clean, low-risk rename — see LOW section.

## Findings

### CRITICAL

**C1 — The bracket ladder is never applied to the simulation.**
`simulate_portfolio` unpacks `n, k_sl, k_tp = bracket_params` (`f1_feasibility_screen.py:295`) and then never references them. `_apply_bracket` (`:232`) and `_get_atr` (`:205`) are defined and unit-tested but are **not called anywhere in the pipeline**. Because the sim ignores the bracket params, `select_bracket` (`:395`) runs 64 grid points that all return the identical result; the strict `>` comparison keeps the first, so the report's "Best Bracket Params (TRAIN-selected): n=5, k_sl=1.0, k_tp=2.0" is exactly `BRACKET_N[0]/BRACKET_K_SL[0]/BRACKET_K_TP[0]` — no selection occurred. Spec §3 explicitly requires the ATR-scaled, TRAIN-fold-selected ladder. The defining feature of the construct is absent, and the report claims it was fitted.

**C2 — The holding period is 1 trading day, not the ~monthly bracketed hold.**
`simulate_portfolio` sets `tp = cal[idx + 1]` (`:315`) and computes `gross_ret = p1/p0 - 1` from month-end close to the *next session's* close (`:331`). Spec §3 line 54 states a "~monthly hold"; `_apply_bracket` is designed for holds up to `n`=20 days. The sim therefore buys at month-end, sells one day later, and sits in cash until the next month. Reported gross (0.68% TRAIN) is a **1-day momentum-continuation figure**, not a monthly-hold return — different economics entirely, and the metric is then labelled/consumed as a per-formation (monthly) expectancy.

**C3 — Cost is understated: single round-trip, no roll turnover, and no early-era pessimistic lean.**
`simulate_portfolio` charges exactly one BUY at `t` + one SELL at `tp` (`:333-334`). Spec §4 requires roll frequency/per-roll round-trips bound from the real 2023+ panel applied to every formation — omitted (consistent with the 1-day hold in C2, but a monthly-hold near-month future needs ≥1 roll). Separately, the same slippage band is applied to TRAIN (2012–2018) and HOLDOUT; spec §4 lines 70–74 require leaning the early era to the pessimistic end and make "survives only at the optimistic end" a NO-GO. Both omissions push net expectancy up and weaken the conservatism invariant that the screen exists to enforce.

Net effect of C1–C3: the screen designed to *kill weak constructs* cannot kill anything, because it is not running the construct. The GO cannot be trusted.

### HIGH

**H1 — `turnover_drag_bp` is mislabelled "bp/yr".**
`turnover_drag_bp = (gross_mean - net_mean) * 10000` (`:368`) is the per-formation round-trip cost in bp. The report column and the surrounding narrative ("13–43 bp/yr; futures STT is much cheaper") read it as annualized. With ~13 monthly formations/yr the annual drag is ~13× larger (roughly 170–560 bp/yr on these numbers) — and higher still once the omitted roll round-trips (C3) are added. The "cheap fees" thesis that justifies the whole cash→futures pivot is resting on this mislabel.

**H2 — Unit tests give false confidence by testing only the disconnected units.**
`test_bracket_atr_simple` (`test_f1_feasibility_screen.py:76`) exercises `_apply_bracket` in isolation and passes (full suite exits 0), but nothing tests that the pipeline *invokes* brackets — which it does not (C1). There is no integration test asserting the reported hold length, that distinct bracket params produce distinct results, or that roll cost is charged. Green tests here do not evidence a correct screen.

### MEDIUM

**M1 — `_apply_bracket` uses fabricated OHLC even if it were wired in.**
`high = entry_price * 1.005`, `low = entry_price * 0.995` are hardcoded every day (`:242-243`); `_get_atr` uses `open` as the high and `close` as the low (`:219-220`). The panel loads only close and open (`load_prices_and_turnover`, `:104-126`) — no high/low. So the "daily-OHLC bracket" in spec §3/§4 is not buildable on the loaded substrate. Either load real H/L, or honestly drop brackets from the cash screen and stop reporting bracket selection.

**M2 — Dead / misleading imports and helpers.** `spearmanr`, `t as t_dist` (`:21-22`), `math`, `field`, `timedelta`, and `_forward` (`:195`) are unused; `_get_atr`/`_apply_bracket` are unreachable from the pipeline. Per repo convention (no speculative/dead code) these should go once C1–C3 are resolved.

### LOW

**L1 — futures package split is clean.** `core/execution/futures.py` deleted; `futures/` package now holds `resolve.py` (the former module body) + `futures_fees.py` + `__init__.py`. `margin_tracker.py` and the two touched tests only update the `futures.py:49` → `futures/resolve.py:49` reference strings and the `_CONSTRUCT_ALLOWED` / derivation-point paths in `test_g1_closure_guard.py`. No behavior change; the G1 closure-guard whitelist was correctly kept in sync. No issues.

**L2 — Readability.** `build_liquidity_universe:159` nests a ternary inside an `if` (`if d.month != cal[i+1].month if i+1 < len(cal) else True:`) — correct but hard to parse; extract to a named `is_month_end`.

## Validation

| Check | Result |
|---|---|
| Tests (`tests/sfb`) | PASS (exit 0) — but pass/fail does not change the verdict, since the passing units are exactly the disconnected ones (H2). |
| Report reproducibility | Report numbers match the current script output faithfully — the defect is that the script computes the wrong construct, not that the report misreports the script. |

## Required before this can be a GO

1. Wire ATR + bracket exit into `simulate_portfolio` (or explicitly drop brackets and remove the selection/reporting of them) — **and** load real daily high/low if brackets stay.
2. Replace the 1-day `tp = cal[idx+1]` hold with the spec's ~monthly bracketed hold.
3. Charge roll turnover per formation and lean early-era slippage pessimistic; re-check the conservatism invariant.
4. Fix the `bp/yr` label (or actually annualize the drag) and add an integration test that fails if brackets/roll/hold-length regress.

Once 1–4 are done, re-run and let the verdict fall where it falls — it may well flip to NO-GO, which is a valid and useful screen outcome.
