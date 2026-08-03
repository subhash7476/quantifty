# OSC — Regime-vs-Signal Diagnostic: Implementation Prompt

**For:** DeepSeek V4 | **Author:** Claude (prompt + review only)
**Date:** 2026-08-02
**Commissioned by:** `OSC_SD_PROBE_REVIEW_2.md` §5. Read §2 and §3 first.

---

## 0. Why this runs before the feature decision

Review-2 listed two open items: **(1)** respecify the feature, **(2)** this
diagnostic. **Run (2) first — its outcome may make (1) moot**, and it is a small
addition to `scripts/osc/sd_probe.py` rather than new work.

Three results from the corrective run point the same way and are probably one
phenomenon, not three:

- `N_eff ≈ 1.9` — the surface moves as ~2 independent bets;
- backward IC (+0.0185) ≈ forward IC (+0.0198) — the predictor "predicts" the past
  as well as the future;
- `sd_IC` ≈ 0.20 identical across every variant tried.

**The hypothesis this task tests: the cross-sectional ranking is nearly static.** If
the same cells are ranked rich day after day, then what presents as 283 fresh daily
bets is a small number of persistent structural tilts — e.g. "OTM puts are always
rich" — restated 737 times. A static ranking still produces a significant rank IC
and a t-stat of +2.73, while representing roughly one bet, not 737 × 283.

If that is what is happening, OSC is a **static smile tilt**. A static tilt is a
single P&L stream, which is a `per_trade_pnl` construct — and therefore back at the
index power wall that `INDEX_CONSTRUCT_DIAGNOSIS.md` §1 documents. That would be a
kill, and it is better found now than after a declaration.

**Do not build any part of OSC. Do not read 2016–2022. Do not tune.** Same hard
constraints as `OSC_SD_PROBE_PROMPT.md` §1, unchanged.

## 1. Diagnostics

Reuse the existing pipeline and the **skip-a-day convention** throughout: predictors
are formed from data at `t−1` or earlier, targets are `dh_return` over `t → t+1`.
This is not optional — it is what keeps CRITICAL-1 from re-entering.

**D-1 — richness persistence.** Cell-level autocorrelation of `richness` at lags 1,
5 and 20 trading days, matched on `(expiry_dt, strike, option_type)`. Report the
pooled median and the interquartile range.

**D-2 — change IC.** Spearman between **`Δrichness_{t−1} = richness_{t−1} −
richness_{t−2}`** and `dh_return` over `t → t+1`.

> Note the double lag. The obvious form, `richness_t − richness_{t−1}`, contains
> `ε_t`, which reappears with opposite sign in the target and would re-create the
> exact contamination C-1 removed. Use `t−1` and `t−2`. This is pinned.

Report `mean_IC`, `sd_IC`, AC₁, NW t (lag 5), alongside the level IC for comparison.

**D-3 — rank persistence.** Spearman between the cross-sectional richness ranking on
day `t` and on days `t+1`, `t+5`, `t+20`, over cells common to both. Report medians.
This measures staticness directly.

**D-4 — frozen-ranking control (the decisive one).** For each cell, compute its mean
richness **rank** over a trailing 60-day window ending at `t−1`. Use that frozen
historical rank as the predictor against `dh_return` over `t → t+1`. Report the same
statistics as D-2.

If a ranking computed from stale data predicts as well as the live one, the live
signal carries no incremental information — it is a standing tilt.

## 2. Pre-registered interpretation — fixed before the run

| Result | Reading |
|---|---|
| D-4 IC ≥ 80% of the level IC (0.0198) | **Static tilt.** OSC is not a cross-sectional signal. It is one persistent bet and belongs under `per_trade_pnl`, where the index power wall applies. Treat as a kill pending operator review. |
| D-4 IC 40–80% of level IC | Mixed: a real standing tilt plus some incremental daily information. Both must be sized separately before any declaration. |
| D-4 IC < 40% of level IC **and** D-2 change IC materially non-zero (NW t ≥ 2) | Genuine daily cross-sectional signal. Proceed to the feature decision (Review-2 §5 item 1). |
| D-2 change IC ≈ 0 **and** D-4 IC high | Confirms the static reading regardless of D-1/D-3. |

Corroborating expectations, not decisive on their own: under the static hypothesis
D-1 autocorrelation is high (lag-1 > 0.7, still elevated at lag 20) and D-3 rank
persistence stays high at `t+20`.

**Do not adjust these thresholds after seeing results.**

## 3. Deliverables

| Path | Content |
|---|---|
| `scripts/osc/regime_diagnostic.py` | Reuses `sd_probe.py` helpers; no duplicated Black-76 code. |
| `scripts/osc/sd_probe.py` | Refactor only — see §3.1. Behaviour must not change. |
| `docs/reports/OSC_REGIME_DIAGNOSTIC_REPORT.md` | Script-generated; no hand-edited numbers. |
| `tests/osc/test_regime_diagnostic.py` | Cover the D-2 double-lag construction and the D-4 trailing-window rank (both are easy to off-by-one). |

### 3.1 Extract the shared panel builder — do not duplicate it

`sd_probe.py` currently does everything inside `run()`, so the paired panel is not
importable. You face a fork, and this pins which branch to take:

**Extract** the pipeline from load through the paired `(richness, dh_return_scaled)`
panel into a function — `build_paired_panel()` — in `sd_probe.py`, and have both
scripts call it. **Do not copy the pipeline into `regime_diagnostic.py`.** Two copies
will drift, and a drifted panel means the diagnostic is not measuring the surface
the probe measured, which would silently void the comparison against 0.0198.

**Parity requirement.** The refactor must not change behaviour. After it, re-run
`sd_probe.py` and confirm it reproduces **`sd_IC = 0.2068`, `mean_IC = +0.0198`
(skip-a-day) exactly**. State the reproduced values in the diagnostic report. If they
differ at all, stop and report — the refactor broke something, and `sd_IC = 0.2068`
is a banked result that a refactor is not permitted to move.

Report must include the fence proof with **observed** min/max `trade_date` (the
MEDIUM-1 fix from Review-1 — do not echo the constants), all four diagnostics, and
the §2 rung applied mechanically without editorialising.

## 4. What must not happen

- Do not read 2016–2022.
- Do not use `richness_t − richness_{t−1}` for D-2. Double lag is pinned.
- Do not select among D-2/D-4 variants on which gives the friendlier answer.
- Do not respecify the feature (Review-2 §5 item 1) as part of this task — that is
  an operator decision informed by this result, not a change to make while running it.
