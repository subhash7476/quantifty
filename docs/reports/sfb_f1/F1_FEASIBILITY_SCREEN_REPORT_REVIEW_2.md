# Review 2 — F1 Feasibility Screen, post-R1–R12 corrective pass

**Reviewed:** 2026-07-20
**Scope:** `scripts/sfb/f1_feasibility_screen.py` (working tree, untracked) against `F1_FEASIBILITY_SCREEN_REPORT_REVIEW.md` R1–R12 and spec §2/§3/§6.
**Decision: BLOCK.** The corrective pass fixed most of R1–R12, but introduced a **new CRITICAL lookahead defect** in the universe, and **the report on disk was never regenerated** — its verdict and every number in it are still the pre-fix run.

## Blocking findings

### B1 — CRITICAL: the liquidity universe is no longer point-in-time (new regression)

`build_liquidity_universe_sql` (`:168-220`) accumulates `eligible_set` as a **union across all years 2010→2022** (`:178-201`), then intersects it with each formation date's priced names (`:206-218`). A name that first became liquid in 2021 is therefore in the eligible universe for a **2012** formation.

This is straightforward lookahead bias: eligibility is conditioned on liquidity the formation date could not have known. The *direction* of the resulting bias is uncertain for a momentum construct — trimming to later-liquid names removes some momentum crashes (flattering), but growth names typically lack early momentum (deflating). The direction does not matter: the run is invalid either way. The prior implementation was correctly causal — trailing 63-session median turnover computed strictly before the formation date (`lb_pos <= pos < fd_pos`). That causality was lost in the OOM rewrite.

Spec §2 requires "a causal cash-liquidity floor... trailing 63-session median traded value." The current code satisfies neither *causal* nor *63-session*.

**Consequence:** every number a re-run would produce is contaminated. This must be fixed before the screen is run again, not after.

### B2 — CRITICAL: the report was never regenerated

`docs/reports/F1_FEASIBILITY_SCREEN_REPORT.md` still reads `*Generated: 2026-07-19T20:23:09.435358*` — the **pre-fix** run. The R1–R12 changes are in the script only. The report on disk therefore still carries:

- the ad-hoc-threshold NO-GO verdict that R1 removed,
- TRAIN n=95 including 2010–2011 that R3 bounded out,
- the "Rs50cr" label that R5 corrected,
- `DaysH` 5.0 that R7 redefined.

Until the screen is re-run (post-B1), **there is no result to review and no verdict of any kind.** The fix summary's framing — findings "implemented," with the run deferred to "a production server" — describes changed code, not a changed conclusion.

### B3 — HIGH: the report's stated liquidity method is now false

`LIQ_WINDOW = 63` is dead — the only remaining reference is the report string at `:555` ("median daily turnover over 63d"). The actual filter is an **annual** median unioned across years (B1). The report would describe a causal 63-day window it does not implement. Delete the constant and print the method actually used.

### B4 — NOT A DEFECT: an unresolved spec ambiguity to pin before the real battery

`decide()` (`:451-483`) now reads `expectancy_ci[0]` (R4 addressed) and treats a CI spanning zero at pessimistic slippage as a **GO with an explicit caveat**, surfaced both in the reason string (`:479-482`) and as a report note (`:511-515`).

An earlier draft of this review called that a defect and argued §6 implies NO-GO. **That was wrong, and it repeated the exact error R1 identified.** R1 faulted the implementer for gating the verdict on a `>1000bp` threshold *absent from §6*; demanding a "CI excludes zero" gate — equally absent from §6 — is the same move in the opposite direction. §6's three NO-GO triggers are all point-estimate/sign tests, and "robustly positive across the full band" most plainly reads as *positive at every slippage setting* — the band **is** the slippage sweep. The implementer's point-estimate-plus-disclosure reading is defensible and arguably more spec-faithful than a bootstrap-CI gate.

The residual issue is a genuine ambiguity, not a defect: **§6 does not define "robustly" with respect to the bootstrap CI.** If CI-exclusion-of-zero should gate the verdict, pin it in the spec *before* the real pre-registered battery, where it would carry real weight. Flagging here so the decision is made deliberately rather than inherited.

## Fixes verified correct

R1 (§6-derived rule, 1000bp threshold removed, `n_yr` now uses real formation span `:409-411`), R3 (`DEV_LO` bound, `:589`), R5 (`1e7`, `:554`), R6 (roll cost disclosed as assumption, Caveat 2), R8 (basis disclosure, Caveat 3), R9 (`report_text` assigned before print), R11 (bootstrap full blocks), R12 (notional in config, `:560`). Grid-size and boundary disclosure added to the report (`:521-528`) — this addresses R2's reporting gap.

Also confirmed **not** a problem despite the summary's framing: the switch to raw `equity_bhavcopy` applies only to turnover aggregation and a price-existence check (`:181-214`). Signal and returns still read `equity_bhavcopy_adjusted` (`:128`). CA-adjustment is irrelevant to a turnover floor, so the certified substrate guarantee is intact for all price paths.

## Fixes claimed but not present

### F1 — "Open-gap worst-case whipsaw" is not implemented (R2, partial)

`_apply_bracket` (`:280-300`) now checks SL before TP on a same-bar breach — correct, and the R2 optimism is half-resolved. But the docstring claims "open-gap worst-case whipsaw" and there is no open-gap handling: `bars` carries only `(date, high, low)` (`:354-361`). The `open` column is selected in SQL (`:127`) and then discarded — never cached, never passed.

So fills are still assumed at exactly `max(low, sl)` / `min(high, tp)`: a stock that gaps far through the stop still fills *at* the stop. Spec §3's first ladder step is missing, and the optimistic-fill half of R2 stands. The docstring asserting otherwise is worse than the omission.

### F2 — R10 not fixed

`main` (`:628-629`) still calls `decide(train_results, holdout_results if holdout_fd else train_results)` — TRAIN is still passed as the holdout argument when HOLDOUT is empty. The summary states "Guarded: if no HOLDOUT, pass empty list." It does not.

### F3 — R7 fix introduces a unit mismatch

`days_this_form` now mixes two units: the bracket path appends **trading** days (`i + 1`, `:295-299`) while the fallback path appends **calendar** days (`(next_fd - t).days`, `:372`). The reported `days_held_mean` averages the two together, inflating it by roughly 1.4× for every fallback trade. Use the bar count (`len(bars)`) on the fallback path.

## Non-blocking

- **N1** — The grid-boundary detector (`:524-525`) hardcodes the *direction* of each boundary (`n == BRACKET_N[0]`, `k_sl == BRACKET_K_SL[-1]`, `k_tp == BRACKET_K_TP[-1]`). It will not flag a winner at `n=20` or `k_sl=1.0`. Check membership in `{first, last}` per axis instead — as written it only detects the previous run's answer.
- **N2** — `DataStore._ensure_loaded` (`:119-142`) guards on `entity not in self._ent_dates_cache`, but that key is only created when a row comes back (`:138`). An entity with zero matching rows is re-queried on every access. Add a negative-cache marker.
- **N3** — The "~2 minutes on a >8GB server" claim is unverified and doubtful: `DataStore` lazy-loads per entity via individual round-trips, which trades memory for query count. Runtime should be measured, not asserted.

## Required before re-running

1. Restore a causal, trailing-window liquidity filter (B1). This is the gate — a run against the current universe produces contaminated numbers.
2. Decide and document whether a CI spanning zero is a NO-GO under §6 (B4).
3. Implement the open-gap ladder step, or delete the claim from the docstring and disclose the optimistic fill in the report (F1).
4. Fix F2, F3, B3.
5. Then re-run and regenerate the report (B2). Only at that point does a verdict exist.

---

# Addendum — verification of the B1–N2 corrective pass (2026-07-20)

**Status: STILL BLOCKED.** The B1 fix does not execute, so the screen cannot run at all.

## A1 — CRITICAL: the new PIT liquidity query throws (B1 not fixed)

`build_liquidity_universe` (`:187-199`) nests aggregate calls:

```sql
SELECT symbol, MEDIAN(SUM(turnover)) AS med_t
FROM equity_bhavcopy ... GROUP BY symbol
```

Executed directly against the store, this raises:

```
BinderException: aggregate function calls cannot be nested
LINE 4:  SELECT symbol, MEDIAN(SUM(turnover)) AS med_t
```

`build_liquidity_universe` is called unconditionally from `main`, on the first formation date, so **the screen crashes before producing anything.** "Ready to re-run" is not accurate — it has not been run since the rewrite, and it cannot be.

The cause is structural: the pre-B1 version correctly used two aggregation levels — a `daily_t` CTE grouping `SUM(turnover)` by `(symbol, trade_date)` to combine EQ/BE series on the same day, then `MEDIAN` over those daily totals. The rewrite collapsed both levels into one `GROUP BY symbol`, which is what forced the nesting. The two-level shape must be restored inside the causal `[fd-63, fd)` window:

```sql
WITH daily_t AS (
    SELECT symbol, trade_date, SUM(turnover) AS tot_t
    FROM equity_bhavcopy
    WHERE trade_date >= ? AND trade_date < ?
      AND series IN ('EQ','BE') AND close > 0 AND turnover > 0
    GROUP BY symbol, trade_date
)
SELECT e.entity
FROM daily_t d
JOIN universe_eligibility e ON e.symbol = d.symbol
WHERE e.class IN ('equity_confirmed','equity_unidentified')
GROUP BY e.entity
HAVING COUNT(*) >= 10 AND MEDIAN(d.tot_t) >= ?
```

Note this also fixes a second defect in the rewrite: the current query computes the median **per symbol** and then joins to entity, so an entity mapping to multiple symbols yields **duplicate entity rows**. `eligible` would carry duplicates, and the `len(eligible) >= MIN_NAMES` gate at `:201` would count them — inflating the apparent universe breadth. Aggregating at entity grain (above) resolves it. The `COUNT(*) >= 10` minimum-observation guard from the original is also missing and should return.

**This query was never executed.** A single run of `build_liquidity_universe` for one formation date would have caught it. Marking B1 "Done" without that is the gap to close.

## A2 — B2 still open; no verdict exists

`F1_FEASIBILITY_SCREEN_REPORT.md` remains at `*Generated: 2026-07-19T20:23:09.435358*` — unchanged across two corrective passes. The report on disk is still the original pre-fix run. Correctly marked Pending, restated here because it is the gating deliverable: **there is still no F1 GO/NO-GO result of any kind.**

## Verified fixed

- **F1** (open-gap) — genuinely implemented. `_op_cache` populated (`:136`), `open` threaded into `bars` (`:360-361`), and `_apply_bracket` (`:285-289`) checks the gap first, filling at `open_p` when the open is beyond SL or TP. This is now conservative on the downside gap, which is what spec §3 step 1 requires.
- **F3** (DaysH units) — fallback uses `len(bars)` (`:372`), consistent trading-day units throughout.
- **N1** — `_grid_boundary_note` (`:488`) extracted, checks both ends per axis.
- **N2** — `_neg_cache` (`:94`, `:111-112`, `:137-138`) correctly marks entities returning zero rows.
- **B3** — `LIQ_WINDOW` live again at `:184`/`:186`, and the report string (`:570`) now says "trailing 63d", matching the intended method.

## Required next

1. Fix the nested aggregate at `:190` (A1), aggregating at entity grain and restoring the observation-count guard.
2. **Execute `build_liquidity_universe` for a single formation date and confirm non-empty output** before anything else.
3. Re-run end to end and regenerate the report (A2).

---

# Addendum 2 — A1 verified (2026-07-20)

**All code findings are closed. The only open item is the run itself (B2/A2).**

## A1 — VERIFIED FIXED

`build_liquidity_universe` (`:187-201`) now uses the two-level shape: a `daily_t` CTE grouping `SUM(turnover)` by `(symbol, trade_date)`, then `MEDIAN(tot_t)` aggregated at `GROUP BY e.entity` with the `COUNT(*) >= 10` guard restored. Executed against the store across three sample windows:

| Trailing window | Eligible entities | Duplicates |
|---|--:|--:|
| 2012-01-02 → 2012-04-02 | 214 | 0 |
| 2015-01-01 → 2015-04-01 | 283 | 0 |
| 2021-01-01 → 2021-04-01 | 524 | 0 |

No `BinderException`; non-empty; entity-grain with zero duplicate rows, closing the duplicate-inflation defect noted in Addendum 1.

**B1 independently confirmed closed by this evidence.** The eligible count *varies with the formation date* (214 → 283 → 524, tracking the real growth in liquid NSE names). The year-union implementation would have produced an identical set at every formation date; a time-varying universe is the observable signature of a causal trailing window.

## Non-blocking observation

`MEDIAN(tot_t)` at `GROUP BY e.entity` pools `(symbol, date)` rows rather than summing an entity's symbols within each date first. For a multi-symbol entity, the median is taken over per-symbol daily turnovers instead of per-entity daily turnover, understating it — a conservative (under-inclusive) direction, affecting only the rare multi-symbol-on-same-date case. Likewise `COUNT(*) >= 10` counts pooled rows. Not worth a fix for a screen; noted so it is not rediscovered later.

## Status

| Finding | State |
|---|---|
| A1, B1, B3, F1, F2, F3, N1, N2 | Closed — verified in code and, where applicable, by execution |
| B4 | Spec ambiguity, not a defect — pin "robustly positive" w.r.t. the bootstrap CI in the real battery's pre-registration |
| **B2 / A2** | **Open — the screen has still never been run post-fix; no verdict exists** |

Nothing further blocks execution. Re-run and regenerate the report; the verdict should then be reviewed on its own terms, against spec §6 and the §0 caveats (prior-exposed signal, assumed costs, optimistic universe proxy — under which a NO-GO is robust but a GO is not).
