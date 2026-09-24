# TS Basis Daily Combo — Build Report

**Branch:** `paper/ts-daily-combo` · **Spec:** `TS_BASIS_DAILY_COMBO_SPEC.md` (as amended, A1)
**Status:** BUILT + dry-run validated. No daemon launched (see §6).
**Date:** 2026-09-24. Sleeve remains research-only — PAPER only, no LIVE, no sealed read.

---

## 1. Diff summary (uncommitted, on branch)

| File | Change |
|---|---|
| `core/execution/portfolio/carry_rebalancer.py` | +85/−13: `apply_signal_filters` helper, `compute_quintile_combo_book` sizer, `min_abs_z` / `exclude_reverting` / `legs_by_quintile` hook params + `_execute` wiring (quintile-pick branch + shared ADV/fwd filters with `facts_full` sync) |
| `scripts/ts_basis_daily_combo_forward.py` | NEW: forward PAPER runner (combo config, `TS_DAILY_COMBO_FORWARD` identity) |
| `tests/portfolio/test_combo_filter.py` | NEW: 11 tests (filter boundary/AND/identity, quintile-book sizing/ADV/empty-leg, hook defaults + param storage) |
| `docs/reports/ts_basis/TS_BASIS_DAILY_COMBO_SPEC.md` | NEW: spec + amendment A1 |

Frozen research files untouched: `build_ts_basis_daily.py`, `publish_facts.py`,
`apply_recovery_filter.py`, both signal/facts stores' builders, `production.duckdb` schema.

## 2. Findings during build

**F-live (live-edge trap, pre-existing):** `ts_basis_daily_forward_runner.py` passes
`signals_db_path` to the hook. Per `_load_fwd_names`' own docstring, that filter
(`fwd_ret_1m IS NOT NULL`) drops every name at the live edge, where the forward
return has not elapsed — the plain forward runner can never open live positions.
Combo runner sets `signals_db_path=None` (no exit policy needs it). Flagged for the
operator: the plain TS Daily forward runner has the same defect.

**A1 (spec amendment, fidelity):** spec v1 prescribed pre-rank filtering (20% cut on
the filtered pool). Measured on 5 dates (07-09, 07-30, 08-24, 09-18, 09-23), pre-rank
reproduces only ~50% of backtested legs and forces symmetric legs (09-23: 24L/24S
vs backtested 35L/38S; 07-30: 8L/8S vs 2L/32S) — conviction drops the weak middle
~40% before the cut, so the 20% cut falls on a different pool. `legs_by_quintile`
implements the backtest-exact path (filter within stored Q1/Q5, variable leg sizes).
Pre-rank helper retained (tested) for generic use; combo uses the exact path.

**09-24 observation (monthly-expiry compression):** 158/210 eligible names read
|z|≤0.7 (vs ~60 normally); only 33 combo-pass legs. 2026-09-24 is the September
monthly expiry (last Thursday). Leading hypothesis: expiry-week basis
normalisation compressed cross-sectional dispersion. Watch the next formations —
if dispersion does not recover, the combo book stays small by rule (correct
behavior, not a bug: `len<5` skip and empty-leg-hold rules in §4 of spec).

## 3. Dry-run evidence (2026-09-24, `--dry-run`)

- Run `ts-basis-daily-combo-forward-2026-09-24`, `TS_DAILY_COMBO_FORWARD`, single
  formation 2026-09-24: **8L/25S = 33 entries, 0 exits** — exactly the 33
  combo-pass legs in facts. Fees Rs 2,114 + slippage Rs 5,000 on Rs 1 Cr gross.
- Determinism hash `70d0b52f8072dae5`, identical across two runs.
- Stale rows from the pre-A1 dry-run (7L/7S) were deleted; the run holds exactly
  one summary row + 33 position rows. Re-ran clean to confirm.
- Tests: **56/56 green** (`tests/portfolio/` — 45 existing + 11 new).
- Provider loads 366 distinct historical underlyings (facts-history breadth);
  the traded book is formation-date-filtered as designed. Inefficient, same as
  the existing forward runner — left as-is.

## 4. Launch (NOT executed — operator action)

```bash
python scripts/ts_basis_daily_combo_forward.py
```

Foreground supervisor loop (60 s poll, refreshes signals+facts incl. recovery flag
each cycle, `--dry-run` for single pass). Suggested: run under the ops
orchestrator pattern or a supervised session; Ctrl+C stops cleanly. First live
rebalances to watch: leg sizes vs backtest pass rates (~26L/29S normal, small on
compression days), turnover (~0.7 one-way expected), fee drag (~18–19 bps/day at
current churn — see mechanics report §4).

## 5. What remains operator-side

- Supervised launch (above) + first-week read against §5 acceptance.
- Plain forward runner's live-edge `signals_db_path` defect (F-live) — separate fix.
- No commit made; review diff on `paper/ts-daily-combo` and merge when satisfied.
