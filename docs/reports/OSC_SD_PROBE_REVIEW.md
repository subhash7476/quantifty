# OSC SD/Breadth Probe — Lead Review

**Date:** 2026-08-02
**Reviewer:** Claude (review only, per standing role split)
**Artifacts reviewed:** `scripts/osc/sd_probe.py`, `docs/reports/OSC_SD_PROBE_REPORT.md`
**Against:** `docs/reports/OSC_SD_PROBE_PROMPT.md`

**Verdict: DO NOT ACT ON THE GREEN RUNG.** One CRITICAL defect makes the headline
IC partly mechanical and leaves `sd_IC` measured on a contaminated feature. A
corrective run is specified in §7. The window fence held and the work is otherwise
competent — this is a fixable defect, not a failed task.

---

## 1. What passed

- **The fence held.** The assertion at `sd_probe.py:475-476` is real and executes
  before any downstream work. The SQL at `:153-154` bounds the load. **2016–2022
  was not read.** (But see MEDIUM-1 — the *report's evidence* for this is fabricated.)
- **No tuning.** Every pinned constant in prompt §3 appears verbatim at
  `sd_probe.py:20-30`. Ordering per prompt §3.0 is correctly implemented:
  traded filter (`:210`) → forward (`:217-229`) → remaining filters (`:246-264`).
- **IV discard of 0.00% is credible, not swallowed.** `implied_vol` (`:76-88`)
  catches only `ValueError`/`RuntimeError` from `brentq` and returns NaN, which is
  then counted (`:275`) rather than silently dropped. With `settle ≥ 0.5`,
  `|m| ≤ 0.15`, `7 ≤ DTE ≤ 60` and OTM-only, essentially every price lies inside
  no-arbitrage bounds with IV in `[0.01, 5.0]`. P6 held legitimately.
- **AC₁ = −0.0138** — the overlapping-formation threat did not materialise, so the
  NW t is not flattered by autocorrelation.

## 2. CRITICAL-1 — `richness_t` and `dh_return` share `settle_t` with opposite signs

This is deductive from the code, not a hypothesis.

- `iv_t` is inverted from `settle_t` (`:271`) and is strictly increasing in it.
- `richness_t = iv_t − fitted_iv_t` (`:289`). The surface fit absorbs the
  cross-sectional common component, so `richness_t` is increasing in cell-level
  `settle_t`.
- `dh_return = settle_{t+1} − settle_t − delta_t·(F_{t+1} − F_t)` (`:332`) is
  **decreasing** in `settle_t`.

Write `settle_t = V_t + ε_t`, where `ε_t` is microstructure noise — bid-ask bounce,
a settlement price struck off a wide spread, rounding. Then:

```
richness_t   ≈  idiosyncratic_t + a·ε_t        (a > 0)
dh_return    ≈  true_dh − ε_t + ε_{t+1}
```

Their cross-sectional covariance carries a term `−a·Var(ε)` — **negative, on every
single day, by construction.** The measured `mean_IC = −0.0615` at `NW t = −8.49`
is exactly the sign and the implausible strength this predicts.

Option settlement prices are the worst case for this: NSE strikes them by
procedure, spreads on non-ATM strikes are wide, and the probe's own filter admits
cells trading at `settle ≥ 0.50`, where one tick is a large fraction of premium.

**This does not prove the IC is entirely artifact.** The genuine VRP effect predicts
the same negative sign, so the real effect and the bounce are *confounded and
inseparable as measured*. That is the problem: the report cannot distinguish them,
and neither can anyone reading it.

### Why this contaminates the deliverable, not just a number we agreed to discard

Prompt §7 already forbids carrying `mean_IC` forward, so a biased mean would have
been harmless. **The damage is to `sd_IC`, which is the one number this task
existed to produce.**

**Direction of the bias, worked through — and it does not favour my own objection.**
The bounce contributes `−a·Var(ε)` to each day's cross-sectional covariance. Were
`Var(ε)` constant across days, that is a *deterministic offset*: it shifts
`mean_IC` and leaves `sd_IC` untouched. `sd_IC` moves only insofar as `Var(ε)`
itself varies day to day with vol regime and liquidity — which **adds** variance.
So the honest expectation is that the artifact inflates `|mean_IC|` strongly and
inflates `sd_IC` mildly, if at all. **The corrected `sd_IC` is therefore more likely
to come in below 0.2032 than above it, and the Green rung will probably survive
C-1.** C-1 is confirmation, not rescue.

**The grounds for suspending are not that the number is probably wrong.** They are
that **the feature which produced 0.2032 is not a feature anyone would trade.** Its
predictor shares a noise term with its own target. Whatever C-1's skip-a-day
predictor turns out to be, *its* dispersion is what the RFA requires, and that has
not been measured. Green ends at 0.2207 against a measured 0.2032 — **8.6% of
headroom** — which is not enough room to wave through an unmeasured substitution.

## 3. MEDIUM-1 — the fence proof in the report proves nothing

`_write_report` at `:498-499`:

```python
l(f"- Observed min `trade_date`: {FENCE_START.date()}")
l(f"- Observed max `trade_date`: {FENCE_END.date()}")
```

These print the **constants**, not the observed values. The report's line
"Observed min `trade_date`: 2023-01-02" is `FENCE_START` echoed back, and would read
identically if the data spanned 2016.

The fence *did* hold — `_assert_fence` (`:471-476`) computes the true min/max and
asserts on them. But it prints them only to stdout and never passes them to the
report. **The artifact of record contains no evidence for its central governance
claim.** This is the repo's own recurring failure mode: *"a freshness value that is
printed but never asserted is documentation, not a control"* (CLAUDE.md, Known
Pitfalls). Here it is the inverse — asserted but not recorded.

Fix: pass `obs_min`/`obs_max` out of `_assert_fence` and print the real values.

## 4. MEDIUM-2 — N_eff = 1.9 is reported as good news; it is the opposite

P3 was written as "median `N_eff` < 25" and passed at **1.9**, so the table reads
**HELD**. Mechanically correct, economically backwards — and the report draws no
consequence from it.

**First, the apparent contradiction is not one.** `sd_IC = 0.2032` implies roughly
`1/sd² + 3 ≈ 27` effective independent cross-sectional observations, against a
reported `N_eff` of 1.9 — a factor of ~14. Both can be right: **Spearman rank
correlation is invariant to a common additive shift in returns.** The PC1 vol-level
factor (61% of variance) moves all cells together and therefore barely perturbs
their *ranks*. `N_eff` measures return co-movement; `sd_IC` measures rank-statistic
sampling error. They are different quantities and the report should say so, because
a reader will otherwise assume one of them is a bug.

**Second, `N_eff` ≈ 2 is a serious economic finding.** Under Grinold–Kahn
`IR = IC·√BR`, breadth is set by independent bets — ~2, not the 283 cells per day.
A book built on these rankings is close to a two-position book wearing a
283-position costume. It does not block the RFA (demonstrability only), but it
directly attacks the *economic* case and it is precisely the "PROCEED is not
authorization" caveat. It belongs in the report's conclusions, not buried in a
passed-predictions table.

## 5. MEDIUM-3 — buckets keyed on raw `strike`, not moneyness

`:376-378` computes the decile from `strike`, but prompt §3.7 specified **moneyness**
decile. `m` was computed at `:254` and then dropped from the paired frame at `:336`,
so it was unavailable and `strike` was substituted without note.

`paired` mixes expiries with different forwards on the same date. Because forwards
across near expiries differ only by carry, strike ranking closely tracks moneyness
ranking, so impact is likely small — but it is an undisclosed deviation from a
pinned spec, and prompt §1.2 required deviations be reported and stopped on, not
substituted.

## 6. LOW findings

- **L-1, attrition conflates two stages.** `after_traded` (621,635) → `after_settle_floor`
  (589,963) is 31,672 cells, and that span covers both the settle floor *and* the
  inner merge on forwards at `:242`, which silently drops cells whose expiry had no
  forward. The report attributes all 31,672 to the settle floor. **The split between
  the two is unknown** — do not assume the merge is the smaller part; 1,794 expiry-dates
  were dropped for want of a forward and each can carry many strikes. Report them as
  separate rows.
- **L-2, dead code.** `unique_fwds` (`:295-297`) is built and never used; `rung`
  (`:434`) is assigned and never read. CLAUDE.md: delete unused code completely.
- **L-3, fragile DTE tercile.** `:379-382` measures days from
  `paired["trade_date"].iloc[0]` — one fixed date — rather than each row's own
  `trade_date`. Inside a `groupby("trade_date")` every row shares a `trade_date`, so
  subtracting a constant preserves ordering and **the result is correct**. It is
  correct by luck; a future edit outside the groupby silently breaks it.

## 7. Corrective run — required before any design work

Same hard constraints as the original prompt (fence 2023-01-02..2025-12-31, no
tuning, read-only, 2016–2022 untouched). Deliverables overwrite the existing report.

**C-1 (the decisive test) — skip-a-day IC.** Add a second IC series computed with
the predictor lagged one extra day: `richness` measured at `t−1`, `dh_return` over
`t → t+1`. This breaks the shared `ε_t` (predictor now carries `ε_{t−1}`; return
carries `−ε_t + ε_{t+1}`) while leaving any genuine persistent richness signal
intact. Report `mean_IC`, **`sd_IC`**, AC₁ and NW t for both series side by side.

Pre-registered interpretation, fixed now:

| Skip-a-day outcome | Reading |
|---|---|
| `abs(mean_IC)` falls by **> 60%** vs same-day | Same-day IC was predominantly bounce. Treat the same-day number as void. |
| `abs(mean_IC)` falls **20–60%** | Both components present, inseparable at this resolution. |
| `abs(mean_IC)` falls **< 20%** | Bounce is not the dominant driver. |

**In all three cases the skip-a-day `sd_IC` — not the same-day one — is the number
that goes to the ladder**, because it is the only one measured on an
uncontaminated predictor.

**C-1b (the direct measurement) — backward IC.** Report the cross-sectional IC
between `richness_t` and the **prior** day's `dh_return` (`t−1 → t`). If bounce
dominates, this must come out strongly **positive** by the same mechanism:
`richness_t` carries `+a·ε_t`, and the return *into* `t` carries `+ε_t`. This
converts C-1 from an inference about a gap into a direct measurement of the
contamination. One extra Spearman call on data the pipeline already holds.

- Large positive backward IC (say `> +0.04`) → contamination confirmed, near-proof.
- Backward IC near zero → the same-day number is largely exonerated.

**C-2 — a genuinely bounce-free richness variant.** Recompute `richness` from a
**trailing** 2-day average IV, `(iv_{t−2} + iv_{t−1})/2`, which excludes `t`
entirely. A *centred* average `(iv_{t−1} + iv_t)/2` would still contain `ε_t` and
merely halve the shared-noise loading — a weaker copy of C-1 rather than an
independent check. Report the same statistics. This is a diagnostic, not a new
candidate feature — do not select between variants on results.

**C-3 — fix MEDIUM-1.** Return `obs_min`/`obs_max` from `_assert_fence` and write the
**observed** values into report §1.

**C-4 — fix MEDIUM-3.** Retain `m` through to `paired` and bucket on moneyness decile
as pinned. Report whether `N_eff` and PC1 move materially.

**C-5 — fix MEDIUM-2 presentation.** Add a short subsection stating (a) why
`sd_IC ≈ 0.20` and `N_eff ≈ 1.9` are consistent (rank invariance to a common shift),
and (b) that `N_eff ≈ 2` implies Grinold–Kahn breadth near 2, with the economic
consequence stated plainly.

**C-6 — fix L-1, L-2, L-3.**

### What must not happen

- **Do not read 2016–2022.**
- **Do not adjust the §6 ladder.** Its thresholds were fixed before the first run and
  remain fixed. If the corrected `sd_IC` lands in Amber or worse, that is the result.
- **Do not select between the same-day, skip-a-day and 2-day-average variants on
  which gives the friendlier number.** C-1's skip-a-day series is pre-designated as
  the ladder input. C-2 is a robustness column only.
- **Do not build any part of OSC.**

## 8. Standing

The Green rung is **suspended**, not overturned. `sd_IC = 0.2032` may well survive
C-1 — the genuine VRP effect predicts the same sign as the artifact, and 283 cells
per day is real breadth for a rank statistic. But it was measured on a predictor
that shares a noise term with its own target, inside an 8.6% margin, and the repo's
governing lesson is that a number reached through a defective gate is not
rehabilitated by being plausible (TS Basis, `CLAUDE.md`).

Re-run C-1, C-1b and C-2 through C-6, and the verdict stands on its own.
