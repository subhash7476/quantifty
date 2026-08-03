# OSC — SD/Breadth Probe: Implementation Prompt

**For:** DeepSeek V4 (implementer)
**Author:** Claude (prompt + review only, per standing role split)
**Date:** 2026-08-02
**Context:** `INDEX_CONSTRUCT_DIAGNOSIS.md` — read it first, especially §9.

---

## 0. What this is, and what it is not

**OSC** (Option Surface Cross-section) is a *candidate* construct: rank Nifty
option strike-expiry cells by richness against a fitted fair surface, trade the
cheap tail long and the rich tail short, delta-hedged daily and vega-balanced, so
that index direction and the overall level of vol both cancel. Metric would be
`rank_ic`.

**This task does not build OSC.** It does not pre-register it, does not gate it,
and does not decide whether it works. It answers exactly one question:

> What is the time-series standard deviation of the daily cross-sectional rank IC
> on the Nifty option surface, and how much effective breadth does that surface
> actually have?

That number decides whether OSC is worth designing at all. If effective breadth
collapses, we kill OSC for the cost of one script — the RFA gate's whole purpose.

**You are measuring a property of the data, not evaluating a strategy.** Do not
report a verdict on OSC. Report the numbers.

---

## 1. HARD CONSTRAINTS — violating any of these invalidates the work

1. **Window fence: `2023-01-02` ≤ `trade_date` ≤ `2025-12-31`, inclusive. Nothing
   outside.** This is the window already burned by `scripts/msrp/triage_fee_impact.py`
   (`DEV_START`/`DEV_END`), so reading it costs nothing.
   **`2016-02-11` → `2022-12-31` is an unread confirmatory window and must not be
   touched by this task in any form** — not for calibration, not for a sanity check,
   not for a plot, not "just to see". Implement the fence as an assertion that
   hard-fails on any row outside it, and print the observed min/max `trade_date` in
   the report as proof.
2. **No tuning.** Every filter, window, and functional form is pinned in §3 below.
   If a pinned choice produces something broken (e.g. IV inversion fails on most
   cells), **stop and report it** — do not substitute a choice of your own and
   continue. A reported failure is a successful outcome for this task.
3. **Read-only.** No writes to any file under `data/`.
4. **State predictions before running.** §5 lists them. Record whether each held.
   Do not revise a prediction after seeing results.

---

## 2. Inputs

| Source | Fields used |
|---|---|
| `data/market_data/options_bhavcopy.duckdb` → `option_bhavcopy` | `symbol`, `expiry_dt`, `strike`, `option_type`, `settle`, `contracts`, `open_int`, `trade_date` |
| `data/market_data/futures_bhavcopy.duckdb` → `futures_bhavcopy` | `underlying`, `inst_type`, `expiry_dt`, `trade_date`, `settle` |

`symbol` is `'NIFTY'` only (the store contains no other index — see
`INDEX_CONSTRUCT_DIAGNOSIS.md` §5 for why). Do not attempt BankNifty; it is not
in the store.

---

## 3. Pinned specification

### 3.0 Order of operations — read this before 3.1

§3.1's moneyness band depends on `F`, and §3.2's forward is derived from traded
option prices. Resolve the circularity in this fixed order, per `(trade_date, expiry_dt)`:

1. Build the **raw traded universe**: `contracts > 0 AND open_int > 0`. No moneyness
   constraint, no DTE constraint, no `settle` floor.
2. Derive `F` from that raw universe per §3.2.
3. *Then* apply the full §3.1 filter, including the moneyness band and the DTE band.

Do not iterate between the two. Do not use a spot-based proxy for `F` in step 1.

### 3.1 Cell filter (applied per `trade_date`, after §3.0 step 2)

A cell is one `(expiry_dt, strike, option_type)`. Keep a cell only if **all** hold:

- `contracts > 0` **and** `open_int > 0` — traded, not model-settled. This is not
  optional: NSE settlement prices for untraded strikes are theoretical values, and
  inverting them fabricates implied vols. This filter is the substrate defence.
- `settle >= 0.50` — penny options invert to garbage IV.
- `7 <= DTE <= 60` where `DTE = expiry_dt - trade_date` in calendar days.
- `abs(ln(strike / F)) <= 0.15` where `F` is the forward from §3.2.
- Use **OTM cells only**: calls where `strike >= F`, puts where `strike < F`. This
  avoids double-counting the same vol point through put-call parity, and OTM is
  where the traded liquidity is.

*Expected consequence, not a bug:* the near-ATM strike `K*` used for the §3.2 parity
forward contributes only one of its two legs to the panel. That is intended.

### 3.2 Forward, per `(trade_date, expiry_dt)`

Derive `F` by **put-call parity** on the strike whose `abs(call_settle - put_settle)`
is smallest among strikes with both legs present and traded:

```
F = K* + exp(r * T) * (C(K*) - P(K*))
```

with `r = 0.065` flat, `T = DTE / 365`. A flat rate across 2023–2025 is deliberate
and adequate here: this task measures a **rank** IC, which is invariant to a
discount factor common to all cells on a date. Do not substitute a term structure.
If no strike on that expiry has both legs
traded, fall back to `futures_bhavcopy` settle for the matching
`(underlying='NIFTY', inst_type='FUTIDX', expiry_dt, trade_date)`. If neither is
available, **drop that expiry for that date** and count it in a dropped-expiry
tally reported in §4.

Parity is preferred over the futures settle because option and futures settlement
prices are struck by different procedures; parity keeps the forward internally
consistent with the very prices being inverted.

### 3.3 Implied vol

Black-76 on the forward, `discount = exp(-r*T)`, solved with `scipy.optimize.brentq`
over `sigma ∈ [0.01, 5.0]`, tolerance `1e-6`. Discard non-convergent cells and
report the discard rate. Do not widen the bracket.

### 3.4 Fair surface, fit per `trade_date`

OLS of `iv` on, with `m = ln(strike / F)` and `tau = ln(DTE)`:

```
iv ~ 1 + m + m^2 + tau + m*tau
```

Require `>= 30` cells on the date, else drop the date (report the count).

**`richness = iv - fitted_iv`** (the residual). Positive = rich.

### 3.5 Forward return — daily delta-hedged, Bakshi–Kapadia discrete

For each cell surviving on both `t` and `t+1` (same `expiry_dt`, `strike`,
`option_type`):

```
dh_return = (V_{t+1} - V_t) - Delta_t * (F_{t+1} - F_t)
```

where `V` is `settle`, `Delta_t` is the Black-76 delta at `t` using the §3.3 IV,
and `F` is the §3.2 forward **for that cell's own expiry** on each date.

Normalize into vol space so cells are comparable:

```
dh_return_scaled = dh_return / max(vega_t, 1e-6)
```

with `vega_t` the Black-76 vega at `t`. Cells not present on `t+1` are dropped
(report the attrition rate — it matters, since expiring cells drop out
non-randomly).

### 3.6 Daily cross-sectional IC

Spearman rank correlation, per `trade_date`, between `richness` at `t` and
`dh_return_scaled` over `t → t+1`. Require `>= 30` paired cells, else drop the date.

**Expected sign is NEGATIVE** (rich cells subsequently underperform). Report the
sign you find; do not flip anything to make it positive.

### 3.7 Effective breadth — measure in bucket space, not cell space

**Do not compute this on individual cells.** Cells expire: with a 7–60 DTE band,
most live well under 60 days, so "cells persisting across a rolling 60-day panel"
is a small, badly biased subset of long-dated survivors. That number would not be
the breadth of the surface you would actually trade.

Use a **stable coordinate** instead:

1. Assign every surviving cell to a bucket: **moneyness decile × DTE tercile**
   (~30 buckets). Decile and tercile edges are computed per `trade_date` on that
   date's surviving cells, so buckets are populated by construction.
2. Per `(trade_date, bucket)`, take the **mean `dh_return_scaled`**. This yields a
   ~30-column daily panel that persists even though its constituent cells do not.
3. On a rolling 60-day window of that bucket panel:
   - **Average pairwise correlation** `rho_bar` = mean off-diagonal Pearson
     correlation across buckets. Then `N_eff = N / (1 + (N - 1) * rho_bar)` with
     `N` = number of buckets populated throughout the window.
   - **PC1 variance share** = fraction of total variance explained by the first
     principal component of the same panel.

Report the median of `rho_bar`, `N_eff`, and PC1 share across all rolling windows,
plus the median number of populated buckets. Also report the median raw cell count
per day alongside, so the gap between raw breadth and effective breadth is visible.

---

## 4. Deliverables

| Path | Content |
|---|---|
| `scripts/osc/sd_probe.py` | The probe. Single entry point, deterministic, no CLI tuning knobs beyond `--out`. |
| `docs/reports/OSC_SD_PROBE_REPORT.md` | Script-generated. No hand-edited numbers. |
| `tests/osc/test_sd_probe.py` | Unit tests for Black-76 price/delta/vega and the parity forward against hand-computed values; a fence test asserting an out-of-window date raises. |

The report must contain, in this order:

1. **Fence proof** — observed min/max `trade_date`, and the assertion's presence.
2. **Attrition table** — rows in, after each §3.1 filter, after IV inversion, after
   `t+1` pairing, after the 30-cell minimum. Absolute numbers, not just percentages.
   Include the dropped-expiry tally from §3.2.
3. **Cells per day** — median, 10th, 90th percentile, by year.
4. **THE HEADLINE NUMBERS** — `n_dates`, `mean_IC`, **`sd_IC`**, Newey–West t-stat
   (lag 5), and `AC1` of the daily IC series.
5. **Breadth** — median `N_eff`, median PC1 variance share, median raw cell count.
6. **Feasibility read-out** — apply §6's ladder mechanically. State which rung the
   measured `sd_IC` lands on. **Do not editorialize beyond the rung.**
7. **Predictions** — §5's table with HELD / FAILED per row.

---

## 5. Falsifiable predictions — state these in the report, then run

| # | Prediction |
|---|---|
| P1 | Median surviving cells per day ≥ 150 across 2023–2025 |
| P2 | PC1 explains **≥ 50%** of `dh_return_scaled` variance — the surface is dominated by a vol-level factor |
| P3 | `N_eff` ≪ raw cell count; specifically median `N_eff` < 25 |
| P4 | `mean_IC` is **negative** (rich underperforms) |
| P5a | `sd_IC` ≤ 0.2943 (i.e. the ladder returns Green or Amber, not Red-amber/ABANDON) |
| P5b | `sd_IC` ≥ 0.15 (a value below this would be surprising and warrants a bug hunt) |
| P6 | IV inversion discard rate < 5% of cells passing §3.1 |

P5 is deliberately split at the ladder's 0.2943 boundary so that it discriminates
between verdicts rather than straddling two rungs.

If P2 or P3 fail in the *favourable* direction (surface far more diverse than
expected), that is a notable result and must be flagged rather than glossed —
it would be surprising and warrants a second look for a bug.

---

## 6. Pre-registered decision ladder

Computed from `scripts/rfa/power.py`, two-sided, power 0.80, against the **1,701**
unread formations in 2016-02-11 → 2022-12-31:

| Measured `sd_IC` | Meaning |
|---|---|
| ≤ 0.2207 | Feasible even at a pessimistic δ = 0.015. **Green** — proceed to design. |
| 0.2207 – 0.2943 | Feasible only if δ ≥ 0.020 can be independently defended. **Amber.** |
| 0.2943 – 0.4267 | Feasible only at δ ≥ 0.029, which is CB-N50's *stock* HOLDOUT IC and has no claim on option cells. **Red-amber** — likely not defensible. |
| > 0.4267 | Infeasible at any defensible δ. **ABANDON OSC.** |

This ladder is fixed now, before the run. Do not adjust it after seeing `sd_IC`.

---

## 7. What must NOT happen

- **Do not read 2016–2022.** Stated twice deliberately.
- **Do not carry the measured `mean_IC` forward as the δ for a future RFA
  declaration.** 2023–2025 is prior-exposed; inheriting an effect size from a short
  contaminated read is the specific error that retired C2 (`CLAUDE.md`, PSB-2
  carry-forward caveats). Only the *dispersion* `sd_IC` is transportable, and even
  that must be argued rather than assumed in the eventual declaration.
- **Do not build any part of OSC** — no signal module, no backtest, no P&L, no
  fee model, no `governance/rfa/declarations/osc.py`. Those come after a design is
  approved, and only if the ladder says Green or defensible Amber.
- **Do not "fix" a bad result by changing a pinned parameter.** If the moneyness
  band or DTE window looks wrong, say so in the report and stop.

---

## 8. Known open problem — the δ anchor is NOT an output of this task

§6's ladder is keyed to assumed δ values, and §7 forbids inheriting `mean_IC` from
the burned window as δ. Both are correct, and together they mean **this probe
cannot by itself authorize OSC even if it returns Green** — it supplies the SD half
of the RFA input and leaves the δ half open.

Naming it now so it is not discovered late: the δ anchor must be established at
*design* time from an **external** source — the option-VRP literature on
cross-sectional delta-hedged returns (Goyal & Saretto, JFE 2009, is the canonical
reference for IV-minus-realized-vol ranking on delta-hedged option positions;
Bakshi & Kapadia, RFS 2003, for the delta-hedged-gains construct itself) — not from
this probe's `mean_IC` and not from CB-N50's stock-cross-section +0.029.

**Do not attempt to resolve this as part of this task.** Just do not let a Green
result be read as "proceed to build."

## 9. Review

Return the three deliverables plus a short note on anything in §3 that could not be
implemented as pinned. Claude reviews against this prompt; the operator decides
whether OSC proceeds to design.
