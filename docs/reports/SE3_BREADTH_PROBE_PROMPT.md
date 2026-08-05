# SE-3 — Breadth / SD Probe: Implementation Prompt

**For:** DeepSeek V4 (implementer)
**Author:** Claude (prompt + review only, per standing role split)
**Date:** 2026-08-05
**Context to read first:** `STRUCTURAL_ALPHA_DOSSIER_2.md` §SE-3 (lines 265–309) and its
revision banner (lines 10–24); `OSC_SD_PROBE_PROMPT.md` (this task is its direct
descendant); `OSC_RFA_ABANDON.md` (what happens when breadth collapses).

---

## 0. What this is, and what it is not

**SE-3** (index-versus-constituent implied correlation / dispersion premium) is a
*candidate* construct: rank Nifty 50 constituents by how rich their own options are
relative to the level the index vol and implied correlation say they should be, then
harvest the spread in vol space — short the rich names' vol, long the cheap names',
delta-hedged daily. Metric would be `rank_ic`.

The dossier ranks SE-3 **best-mechanism of anything in it** (§5: *"the most likely of
anything here to be intact in 2040"*) and simultaneously refuses to rank it higher than
#3, for exactly one reason: **its effective breadth has never been measured.** That is
the single number standing between the best mechanism in the dossier and a declaration.

**This task does not build SE-3.** It does not pre-register it, does not gate it, does
not decide whether it works, and does not produce a δ. It answers one question:

> On a daily cross-section of Nifty 50 constituents ranked on option richness, what is
> the time-series standard deviation of the cross-sectional rank IC, and how much
> **effective** breadth does that cross-section actually have?

You are **measuring a property of the data, not evaluating a strategy.** Do not report a
verdict on SE-3. Report the numbers and the pre-registered rung.

**Why this probe is worth running at all.** OSC collapsed to `N_eff = 1.9` against 283
nominal cells because every cell shared one underlying's vol level. Here the units are
**50 different companies with idiosyncratic vol**, and the Carry↔IVOL measurement
(ρ = −0.04) says name-level signals genuinely decorrelate in this universe. But a
market-wide vol shock still moves all 50 names' options together, and that is precisely
the failure mode that killed OSC. **The honest prior is: better than OSC, worse than
nominal.** Where it lands between those is what you are measuring.

---

## 1. HARD CONSTRAINTS — violating any of these invalidates the work

1. **Window fence: `2023-01-02` ≤ `trade_date` ≤ `2025-12-31`, inclusive, on BOTH
   option legs and on every auxiliary series.** Implement as an assertion that
   hard-fails on any row outside it. Print observed min/max `trade_date` per source in
   the report as proof.

   **Nothing before 2023-01-02 and nothing after 2025-12-31 may be read, in any form** —
   not for warmup, not for calibration, not for a sanity check, not for a plot, not
   "just to see". This is not a stylistic preference:
   - `2016-02-11 → 2022-12-31` is the **1,701-date unread index-option confirmatory
     window**, deliberately preserved through OSC's entire probe/review/abandon
     sequence at zero cost. It is the most valuable unspent asset in the options
     substrate. Do not touch it.
   - `2026-01-01 → 2026-07` is a short unread tail on both legs. Leave it.

2. **Warmup comes from inside the fence.** §3.5 needs 21 trading days and §3.6 needs a
   60-trading-day trailing window. Both must be filled from data at or after
   `2023-01-02`. Consequently the **first usable formation date is not 2023-01-02** —
   it is the first date with a complete trailing window inside the fence. Compute it,
   do not hardcode it, and report it. Any implementation that reaches back before the
   fence to fill a warmup window has failed constraint 1.

3. **The `t+1` forward return must also lie inside the fence.** The final in-window
   date has no pair; drop it and count it. Do not fetch 2026-01 to complete it.

4. **No tuning.** Every filter, window, band, and functional form is pinned in §3. If a
   pinned choice produces something broken (IV inversion fails on most cells, fewer
   than 20 names survive on a typical day, β regressions do not converge), **stop and
   report it.** Do not substitute a choice of your own and continue. **A reported
   failure is a successful outcome for this task.**

5. **Read-only.** No writes anywhere under `data/`.

6. **State the §6 predictions before running.** Record HELD / FAILED per row. Do not
   revise a prediction after seeing a result.

7. **Reuse the tested Black-76 code.** Import `black76_price`, `black76_delta`,
   `black76_vega`, `implied_vol`, and `_parity_forward` from `scripts/osc/sd_probe.py`.
   Do not reimplement them. A second, divergent Black-76 in this repo is a defect, not
   a convenience — and those functions already carry unit tests against hand-computed
   values (`tests/osc/test_sd_probe.py`).

---

## 2. Window ledger — what this probe SPENDS

State this in the report, verbatim and prominently. The last lead review faulted a
**stale window ledger**; do not repeat that.

| Leg | Window | State entering this probe | State after |
|---|---|---|---|
| NIFTY index options | 2023-01-02 → 2025-12-31 | **Already burned** — `scripts/msrp/triage_fee_impact.py` (`DEV_START`/`DEV_END`) read short/long ATM straddle P&L net of fees here; OSC's SD probe read it again by design | Unchanged — costs nothing |
| OPTSTK stock options | 2023-01-02 → 2025-12-31 | **Not previously read for research.** (`scripts/ts_basis_daily_options_signal_strength.py` touches only a rolling ~30-day live-signal window, not this span) | **SPENT by this probe** |
| NIFTY index options | 2016-02-11 → 2022-12-31 | Unread, 1,701 dates | **Preserved — untouched** |
| OPTSTK stock options | 2016-07-31 → 2020-12-31 | **Prior-exposed** — the Skew sleeve read TRAIN here (25-delta risk-reversal, monthly, IC −0.018, t = −1.15, FAILED at §9 gate 2) | Unchanged |
| OPTSTK stock options | 2021-01-01 → 2022-12-31 | Unread (Skew's HOLDOUT was never opened — the sleeve died at TRAIN) | **Preserved — untouched** |
| Both legs | 2026-01-01 → 2026-07 | Unread | **Preserved — untouched** |

**This is a deliberate trade and the reasoning must be recorded, not assumed.** The
probe needs a window burned on the *index* leg, because §3.6's variant B reads index
options directly. Only `2023-2025` qualifies. Spending the stock-option leg there is
the price; it buys preservation of the entire 1,701-date index window and the
joint-clean 2021–2022 stock-option window.

**The alternative was considered and rejected:** probing on `2016-07 → 2020-12` (where
the *stock* leg is Skew-exposed) would have required reading unread index options across
~1,100 dates. That trades a cheap asset for an expensive one.

---

## 3. Pinned specification

### 3.0 Inputs

| Source | Table | Fields |
|---|---|---|
| `data/market_data/stock_options_bhavcopy.duckdb` | `stock_options_bhavcopy` | `underlying`, `expiry_dt`, `strike`, `option_type`, `settle`, `contracts`, `open_int`, `trade_date` |
| `data/market_data/options_bhavcopy.duckdb` | `option_bhavcopy` | same fields; `symbol = 'NIFTY'` only |
| `data/market_data/futures_bhavcopy.duckdb` | `futures_bhavcopy` | `underlying`, `inst_type`, `expiry_dt`, `trade_date`, `settle` |
| `data/reference/mcwb_manifest.json` + `mcwb_*.zip` | — | PIT Nifty 50 membership + weights |

**BANKNIFTY is out of scope, decided now and recorded before measuring.** The dossier
(§4) flags its recovery as optional and warns that deciding after measuring would change
the breadth arithmetic post hoc. It is excluded because this probe measures the breadth
of the **constituent** cross-section; a second index leg adds one column to a ~40-column
panel and cannot move `N_eff` materially. Its recovery remains a separate, independently
justified ingest task. Do not add it, and do not treat its absence as a limitation of
this measurement.

### 3.1 Universe — PIT Nifty 50 membership

Follow `scripts/se1/count_index_events.py` exactly:

- Read the MCWB monthly archives via `data/reference/mcwb_manifest.json`, `status ==
  "valid"` records only, from `nifty50_mcwb.csv` inside each zip.
- **Exclude `DUMMY_SYMBOLS = {"DUMMYREL", "DUMMYTATAM", "DUMMYHDLVR"}`** — NSE's own
  test rows, verified 2026-08-04 against the raw CSVs. Treat any *new* `DUMMY*` or
  `TMPV*` symbol you encounter as a source-pollution finding to report, not a member.
- MCWB is a **month-end snapshot**. Apply month *M*'s membership to trading dates in
  month *M+1* only. Never apply a snapshot to dates preceding it — that is lookahead.
- Additionally require the name to be **F&O-live on the date**: at least one
  `inst_type='FUTSTK'` row in `futures_bhavcopy` for that `underlying` and `trade_date`.
  This is the point-in-time eligibility guard the dossier §D requires.

Also parse and retain each member's **weight** from the MCWB CSV (see §3.8). If the
weight column cannot be located in a given archive's layout, **stop and report it** —
do not substitute equal weights.

### 3.2 Expiry selection, per `(trade_date, underlying)`

Pick the **nearest expiry with `DTE >= 7`**, where `DTE = expiry_dt - trade_date` in
calendar days, subject to `DTE <= 60`. If no expiry falls in `[7, 60]`, drop that
`(date, name)` and count it.

The `DTE >= 7` floor removes expiry-week pin/gamma distortion. It is pinned, not tuned.

Apply the identical rule to NIFTY.

### 3.3 Forward, per `(trade_date, underlying, expiry_dt)`

- **Single stocks:** `futures_bhavcopy` settle for the matching
  `(underlying, inst_type='FUTSTK', expiry_dt, trade_date)`. Stock options and stock
  futures share expiries, and single-stock option books are too thin for a reliable
  parity strike. If the futures row is absent, fall back to the parity procedure below;
  if that also fails, drop and count.
- **NIFTY:** `_parity_forward` from `scripts/osc/sd_probe.py` (put-call parity on the
  strike with smallest `abs(call_settle - put_settle)` among strikes with both legs
  traded, `r = 0.065` flat, `T = DTE/365`), falling back to `FUTIDX` settle. This
  preserves consistency with the OSC measurement it will be compared against.

### 3.4 ATM implied vol, per `(trade_date, underlying)`

Cell filter — keep a cell only if **all** hold:

- `contracts > 0` **and** `open_int > 0` — traded, not model-settled. **This is the
  substrate defence and is not optional.** NSE settlement prices for untraded strikes
  are theoretical values; inverting them fabricates implied vols. Single-stock chains
  are far more sparsely traded than NIFTY, so this filter does more work here than it
  did in OSC — expect it to remove a large share of rows, and report how much.
- `settle >= 0.50`.
- `abs(ln(strike / F)) <= 0.10`. Tighter than OSC's 0.15 because this task needs an
  ATM *level*, not a surface, and single-stock wings are unreliable.

From the survivors take:
- `iv_call` = Black-76 IV of the **nearest-OTM call** (smallest `strike >= F`),
- `iv_put` = Black-76 IV of the **nearest-OTM put** (largest `strike < F`),

and set `sigma = mean(iv_call, iv_put)` when both exist, else whichever exists. If
neither exists, drop `(date, name)` and count it.

Inversion: `scipy.optimize.brentq` over `sigma ∈ [0.01, 5.0]`, tol `1e-6`, via the
imported `implied_vol`. Discard non-convergent cells; **report the discard rate
separately for stocks and for NIFTY.** Do not widen the bracket.

### 3.5 Realized vol, per `(trade_date, underlying)`

`rv` = annualized SD of the trailing **21 trading days** of log returns on the
**front-month FUTSTK settle** series (`inst_type='FUTSTK'`, nearest expiry with
`DTE >= 7` as of each historical date), `sqrt(252)` scaling, requiring `>= 18` return
observations. **Drop the return computed across a roll** (any date where the front-month
`expiry_dt` differs from the previous date's) — a roll gap is not a price move.

*Why futures and not the adjusted equity panel:* the futures settle is the instrument the
delta hedge actually trades, it needs no corporate-action adjustment, and it avoids
pulling the equity entity-resolution stack (`symbol_entity_intervals`, ISIN issuer
prefixes) into a measurement task that does not need it. The adjusted-equity alternative
was considered and rejected for that reason; record the choice.

### 3.6 The two richness signals — measure BOTH

The dossier frames SE-3 as index-versus-constituent. It is worth being explicit that the
**cross-sectional form does not strictly require the index leg to rank names** — a
per-date cross-sectional fit absorbs the market-wide vol/correlation level into its
intercept, which is exactly the component the dispersion trade neutralizes rather than
bets on. Whether the explicit index anchor earns its keep is itself measurable, so
measure it.

**Variant A — pure constituent cross-section (no index leg in the signal).**
Per `trade_date`, OLS across surviving names:

```
sigma_i = a + b * rv_i + eps_i
```

`richness_A_i = eps_i` (the residual). Positive = the name's option is rich relative to
its own realized vol and the day's cross-sectional norm. Require `>= 20` names on the
date, else drop the date and count it.

**Variant B — index-anchored.**
Per name, a trailing **60-trading-day** OLS of the name's ATM IV on the index ATM IV:

```
sigma_i(s) = alpha_i + beta_i * sigma_I(s),   s in the trailing 60 trading days
```

requiring `>= 40` paired observations, then

```
richness_B_i = sigma_i(t) - (alpha_i_hat + beta_i_hat * sigma_I(t))
```

Names failing the 40-observation minimum are dropped from variant B **only** — variant A
keeps them. Report the two universes' sizes separately; they are not the same panel and
must not be silently merged.

### 3.7 Forward return — daily delta-hedged, Bakshi–Kapadia discrete

For each `(date, name)` cell used in §3.4, surviving on both `t` and `t+1` with the same
`(expiry_dt, strike, option_type)`:

```
dh_return        = (V_{t+1} - V_t) - Delta_t * (F_{t+1} - F_t)
dh_return_scaled = dh_return / max(vega_t, 1e-6)
```

`V` is `settle`; `Delta_t`, `vega_t` are Black-76 at `t` using the §3.4 IV; `F` is that
name's own §3.3 forward for that expiry on each date.

Where §3.4 used both a call and a put, average their `dh_return_scaled`. Where only one
leg paired to `t+1`, use that one. Where neither paired, drop `(date, name)` and count
it — **report the attrition rate; it matters, because cells that fail to trade on `t+1`
do not fail at random.**

### 3.8 Implied correlation — diagnostic only, NOT the signal

Per `trade_date`, on the surviving names with PIT weights `w_i` **renormalized to sum to
1 over survivors**:

```
rho_imp = (sigma_I^2 - sum_i w_i^2 sigma_i^2) / (sum_{i != j} w_i w_j sigma_i sigma_j)
```

Report: median `rho_imp`, its 10th/90th percentiles, the **fraction of dates where
`rho_imp` falls outside `[0, 1]`**, and the **median renormalization mass** (the share of
true index weight the surviving names represent). **Do not clip `rho_imp`** — clipping is
a modelling choice and this is a diagnostic. **Do not use `rho_imp` as a per-name
signal**; it is one number per day and per-name it is degenerate. It is reported so the
eventual pre-registration can judge whether the index-implied-correlation framing is
even well-posed on this substrate.

A low renormalization mass or a high out-of-range rate is a **finding**, not a bug to
paper over.

### 3.9 Daily cross-sectional IC

Spearman rank correlation per `trade_date`, between `richness` at `t` and
`dh_return_scaled` over `t → t+1`. Require `>= 20` paired names, else drop the date.
Compute independently for variant A and variant B.

**Expected sign is NEGATIVE** (rich options subsequently underperform, delta-hedged).
Report the sign you find. **Do not flip anything to make it come out right.**

### 3.10 Effective breadth — the headline measurement

Unlike OSC, **the units here persist**: a Nifty 50 constituent is on the panel every day
it is a member, so no bucket-coordinate workaround is needed. Measure directly on names.

Build the daily `(date × name)` panel of `dh_return_scaled`. On a rolling
**60-trading-day** window, over names populated throughout that window:

- `rho_bar` = mean off-diagonal Pearson correlation across names.
- `N_eff = N / (1 + (N - 1) * rho_bar)`, `N` = names populated throughout the window.
- `PC1 share` = variance fraction explained by the first principal component.

Report the **median across rolling windows** of `rho_bar`, `N_eff`, and PC1 share, plus
the median `N` and the median raw names-per-day, so the gap between nominal and effective
breadth is visible.

**Compute the same three quantities on the cross-sectionally demeaned panel as a
secondary diagnostic — and label it with this warning in the report:** demeaning
mechanically induces `rho_bar ≈ -1/(N-1)`, which drives `N_eff` toward `N` by
construction. **The demeaned `N_eff` is an artifact and must never be quoted as the
breadth of this cross-section.** It is reported only to show how much of the raw
correlation is a common level versus genuine pairwise co-movement. The **raw `N_eff` is
the headline**, and it is the number directly comparable to OSC's 1.9 and the TS Basis
filter probe's 10.1.

---

## 4. Deliverables

| Path | Content |
|---|---|
| `scripts/se3/breadth_probe.py` | The probe. Single entry point, deterministic, no CLI tuning knobs beyond `--out`. |
| `docs/reports/SE3_BREADTH_PROBE_REPORT.md` | **Script-generated. No hand-edited numbers.** |
| `tests/se3/test_breadth_probe.py` | Fence test (an out-of-window date raises); MCWB month-end → next-month application (asserts no lookahead); roll-day return exclusion in §3.5; the `N_eff` formula against a hand-computed correlation matrix; the demeaning artifact (assert demeaned `N_eff` > raw `N_eff` on synthetic data with a common factor). |

The report must contain, **in this order**:

1. **Fence proof** — observed min/max `trade_date` per source, the assertion's presence,
   and the computed first usable formation date with its warmup justification.
2. **Window ledger** — §2's table, updated to post-run state.
3. **Attrition table** — absolute row counts, not just percentages: rows in; after the
   traded filter; after `settle >= 0.50`; after the moneyness band; after IV inversion;
   after the §3.2 expiry rule; after `t+1` pairing; after the 20-name minimum. Separate
   columns for stocks and NIFTY. Include the dropped-`(date, name)` tallies from §3.2,
   §3.3, §3.4.
4. **Names per day** — median, 10th, 90th percentile, by year, for variant A and B
   universes separately.
5. **THE HEADLINE NUMBERS** — for A and B: `n_dates`, `mean_IC`, **`sd_IC`**,
   Newey–West t-stat (lag 5), `AC1` of the daily IC series.
6. **Breadth** — median raw `rho_bar`, raw `N_eff`, raw PC1 share, median `N`, median
   raw names/day; then the demeaned trio under its warning label.
7. **Implied-correlation diagnostics** — §3.8's five quantities.
8. **Feasibility read-out** — apply §5's ladder mechanically, at **both** confirmatory-`n`
   readings, for both variants. State the rung. **Do not editorialize beyond the rung.**
9. **Predictions** — §6's table with HELD / FAILED per row.
10. **Implementation notes** — anything in §3 that could not be implemented as pinned.

---

## 5. Pre-registered decision ladder

Computed with `scripts/rfa/power.py`, two-sided, α = 0.05, power 0.80. The δ anchors are
**identical to OSC's** so the two measurements are directly comparable; the script must
invert them via `power.n_required` / `power.power_at` rather than hardcoding thresholds.

**The confirmatory `n` is genuinely ambiguous and both readings must be reported.** SE-3's
backward confirmatory window would be `2016-02-11 → 2022-12-31`, and whether the Skew
sleeve's TRAIN read spends part of it is a judgement the operator makes, not this probe:

| Reading | Confirmatory window | `n` | Basis |
|---|---|---|---|
| **Permissive** | 2016-02-11 → 2022-12-31 | **1,701** | Skew read a *different quantity* (25-delta risk-reversal) at a *different cadence* (monthly) — prior exposure to disclose, not a window spent |
| **Strict** | 2021-01-01 → 2022-12-31 | **≈495** | Skew's 2016-07 → 2020-12 TRAIN is treated as spent for any option-cross-section work |

Report the ladder rung under **both**. Do not pick one.

| Rung | Meaning |
|---|---|
| **Green** | Feasible even at a pessimistic δ = 0.015 → proceed to design |
| **Amber** | Feasible only if δ ≥ 0.020 can be **independently** defended |
| **Red-amber** | Feasible only at δ ≥ 0.029 — which is CB-N50's *stock* HOLDOUT IC and has no claim on option cells. Likely not defensible |
| **ABANDON** | Infeasible at any defensible δ |

This ladder is fixed now, before the run. **Do not adjust it after seeing `sd_IC`.**

Note the arithmetic asymmetry so it is not discovered late: under the strict reading
`√495 ≈ 22.2` versus `√1701 ≈ 41.2`, so the strict reading demands an effect roughly
**1.85× larger** for the same rung. A result that is Green permissive and Red-amber
strict is a real and likely outcome, and reporting it as such is the correct output.

---

## 6. Falsifiable predictions — state these in the report, then run

| # | Prediction |
|---|---|
| P1 | Median names/day (variant A) ≥ 35 across 2023–2025 |
| P2 | Raw `rho_bar` ≥ 0.15 — a common vol factor is present in name-level delta-hedged returns |
| P3 | Raw median `N_eff` < 15 — nominal breadth (~45) substantially overstates effective breadth |
| P4 | Raw median `N_eff` > 1.9 — this cross-section is genuinely broader than OSC's surface |
| P5 | `mean_IC` for variant A is **negative** (rich underperforms) |
| P6a | `sd_IC(A)` ≤ 0.30 |
| P6b | `sd_IC(A)` ≥ 0.15 — a value below this would be surprising and warrants a bug hunt |
| P7 | `sd_IC(B) ≥ sd_IC(A)` — the trailing-β estimate adds estimation noise, so the explicit index anchor should *cost* dispersion unless it buys real signal |
| P8 | IV inversion discard rate < 10% of cells passing §3.4's filters (looser than OSC's 5% because single-stock books are thinner) |
| P9 | `t+1` pairing attrition < 25% of `(date, name)` cells |
| P10 | Median renormalization mass (§3.8) ≥ 0.85 — the surviving names carry most of the index's weight |

**P3 and P4 are deliberately two-sided around the live risk.** If P3 fails in the
*favourable* direction (effective breadth far higher than expected), that is a notable
result and must be flagged rather than glossed — it would be surprising and warrants a
second look for a bug, most likely a leak of cross-sectional demeaning into the raw
panel. If P4 fails, SE-3's escape-A claim is dead on the same rock as OSC's and the
report should say so plainly at rung level without editorializing further.

---

## 7. What must NOT happen

- **Do not read outside `2023-01-02 → 2025-12-31`.** Stated twice deliberately. The
  1,701-date index window survived OSC's entire lifecycle unspent; do not be the run
  that costs it.
- **Do not carry `mean_IC` forward as the δ for a future RFA declaration.** 2023–2025 is
  prior-exposed on the index leg and now spent on the stock leg; inheriting an effect
  size from a short contaminated read is the specific error that retired C2 (`CLAUDE.md`,
  PSB-2 carry-forward caveats) and the specific correction the dossier's revision banner
  applies to SE-1. **Only the dispersion `sd_IC` is transportable**, and even that must be
  argued rather than assumed in the eventual declaration.
- **Do not build any part of SE-3** — no signal module, no backtest, no P&L, no fee
  model, no `governance/rfa/declarations/se3.py`. Those come after a design is approved,
  and only if the ladder says Green or defensible Amber.
- **Do not add BANKNIFTY**, and do not treat its absence as a limitation of this
  measurement (§3.0).
- **Do not "fix" a bad result by changing a pinned parameter.** If the moneyness band,
  DTE window, or name minimum looks wrong, say so in the report and stop.
- **Do not quote the demeaned `N_eff` as breadth** (§3.10).
- **Do not clip `rho_imp`** (§3.8).

---

## 8. Known open problem — the δ anchor is NOT an output of this task

§5's ladder is keyed to assumed δ values, and §7 forbids inheriting `mean_IC` from the
burned window as δ. Both are correct, and together they mean **this probe cannot by
itself authorize SE-3 even if it returns Green** — it supplies the SD half of the RFA
input and leaves the δ half open.

Naming it now so it is not discovered late: the δ anchor must be established at *design*
time from an **external** source — Goyal & Saretto (JFE 2009) on IV-minus-realized-vol
ranking of delta-hedged option positions, and Bakshi & Kapadia (RFS 2003) for the
delta-hedged-gains construct itself — **not** from this probe's `mean_IC`, **not** from
CB-N50's stock-cross-section +0.029, and **not** from OSC's +0.0167.

**Do not attempt to resolve this as part of this task.** Just do not let a Green result be
read as "proceed to build."

There is a second open problem the eventual pre-registration inherits and this probe
cannot answer: the dossier's §G warning that **a dispersion book reports an attractive
Sharpe until correlation goes to one, and the noncentral-t gate will not see that.**
Breadth and dispersion are necessary, not sufficient. Nothing measured here bears on the
tail.

---

## 9. Review

Return the three deliverables plus a short note on anything in §3 that could not be
implemented as pinned. Claude reviews against this prompt; the operator decides whether
SE-3 proceeds to design.
