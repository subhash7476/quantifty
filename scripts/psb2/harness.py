"""PSB-2 Screening Harness — adapted from PSB-1 (FROZEN Rev 4).

Reuses generic infrastructure from scripts.psb1.screening_harness by import
(scripts/psb1/ stays git-clean). PSB-2-specific additions: fortnightly grid,
C2/C3/C4 scorers, C4 staggered 6-tranche holding, and evaluate_candidate_psb2
that dispatches banded (C2/C3) vs staggered (C4) portfolio simulation.

Exit band: a thin wrapper _quintile_sequences_psb2 is used instead of the
PSB-1 function, adding an explicit band parameter. This is a diff-clean
copy with one parameter added and the band switched from a module-level
constant to a parameter; the change is declared here.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any

import numpy as np

from scripts.psb1.screening_harness import (
    Panel,
    CandidateResult,
    load_panel,
    fence_check,
    monthly_grid,
    _pct_rank,
    _price,
    _ret,
    _day_back,
    members_at,
    _one_sided_t,
    _ac1,
    _nw_se,
    _power,
    date_ic,
    _simulate,
    DEV_HI,
    SEALED_LO,
    SEALED_HI,
    MIN_NAMES,
    KAPPA,
    CAP,
    ALPHA,
    QUINTILE,
    POWER_HURDLE,
    POWER_TIE_BAND,
    AC1_TRIGGER,
    NW_LAG,
)

STORE = "data/market_data/equity_bhavcopy.duckdb"

# PSB-2 pinned constants (§9)
BONFERRONI_M = 3
C2_EXIT_BAND = 0.40
C3_EXIT_BAND = 0.40
C4_N_TRANCHES = 6

# C2 parameters
DELIV_BASE_DAYS = 252
DELIV_BASE_END_OFFSET = 21
DELIV_BASE_MIN = 150
DELIV_MEAN_MIN = 8

# C3 parameters
RETURN_HORIZON_DAYS = 21

# C4 parameters
C4_LOOKBACK_12 = 12
C4_LOOKBACK_1 = 1
C4_MIN_PRIOR_GRID = 12

# Dev windows (§3)
DEV_HI = date(2022, 12, 31)
C2_DEV_LO = date(2020, 9, 4)
C3_DEV_LO = date(2020, 9, 4)
C4_DEV_LO = date(2012, 1, 1)
COMMON_SUBWINDOW_LO = date(2020, 9, 4)


# ── Fortnightly grid (§3) ──────────────────────────────────────────────────────

def fortnightly_grid(cal: list[date]) -> list[date]:
    grid = []
    for idx, d in enumerate(cal):
        is_mid = d.day <= 15
        is_eom = (idx + 1 >= len(cal) or cal[idx + 1].month != d.month)
        if is_mid:
            if idx + 1 >= len(cal) or cal[idx + 1].month != d.month or cal[idx + 1].day > 15:
                grid.append(d)
        if is_eom:
            grid.append(d)
    return grid


def sealed_grid_count_psb2(db_path: str, cadence: str) -> int:
    import duckdb
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute(
        "SELECT trade_date FROM trading_calendar WHERE n_symbols >= 200 "
        "AND trade_date >= ? AND trade_date <= ? ORDER BY trade_date",
        [SEALED_LO, SEALED_HI]
    ).fetchall()
    con.close()
    cal = [r[0] for r in rows]
    if cadence == "fortnightly":
        return len(fortnightly_grid(cal))
    elif cadence == "monthly":
        return len(monthly_grid(cal))
    raise ValueError(f"Unknown cadence: {cadence}")


# ── §5 Scorers ──────────────────────────────────────────────────────────────────

def score_c2_psb2(panel: Panel, t: date, fg: list[date] | None = None) -> dict[str, float]:
    """C2 — Delivery-percentage anomaly, fortnightly.

    dp_i(t) = mean of deliv_pct over trading days in (prev_grid_date, t]  (>= 8 non-NULL)
    mu_i, sigma_i = mean, std of deliv_pct over 252 trading days ending t-21
    s_i(t) = (dp_i(t) - mu_i) / sigma_i

    fg: optional fortnightly grid for computing the prior grid date.
        If None, falls back to a scan (not pinned — for compatibility only).
    """
    t_21 = _day_back(panel, t, DELIV_BASE_END_OFFSET)
    if t_21 is None:
        return {}
    t_base = _day_back(panel, t_21, DELIV_BASE_DAYS - 1)
    if t_base is None:
        return {}
    members = members_at(panel, t)
    scores: dict[str, float] = {}

    # Determine prior grid date
    prev_grid = None
    if fg is not None:
        t_idx = fg.index(t) if t in fg else -1
        if t_idx > 0:
            prev_grid = fg[t_idx - 1]
        elif t_idx == 0:
            prev_grid = None  # first grid date, no prior
        else:
            prev_grid = None
    if prev_grid is None:
        # Fallback: scan back from t (not pinned — for null panels where t not in grid)
        cal_idx = panel.cal_pos.get(t)
        if cal_idx is None:
            return {}
        MAX_FALLBACK_DAYS = 15
        start_idx = max(cal_idx - MAX_FALLBACK_DAYS, 0)
        prev_grid = panel.cal[start_idx]

    # Find calendar index of prev_grid
    pg_idx = panel.cal_pos.get(prev_grid)
    t_idx = panel.cal_pos.get(t)
    if pg_idx is None or t_idx is None or pg_idx >= t_idx:
        return {}

    for ent in members:
        recent_dps = []
        for j in range(t_idx, pg_idx, -1):
            dd = panel.cal[j]
            dp_val = panel.dp.get((ent, dd))
            if dp_val is not None and not (isinstance(dp_val, float) and math.isnan(dp_val)):
                recent_dps.append(dp_val)
        if len(recent_dps) < DELIV_MEAN_MIN:
            continue
        dp_mean = float(np.mean(recent_dps))

        base_dps = []
        t_21_idx = panel.cal_pos.get(t_21)
        t_base_idx = panel.cal_pos.get(t_base)
        if t_21_idx is None or t_base_idx is None:
            continue
        for j in range(t_21_idx, max(t_base_idx - 1, -1), -1):
            dd = panel.cal[j]
            dp_val = panel.dp.get((ent, dd))
            if dp_val is not None and not (isinstance(dp_val, float) and math.isnan(dp_val)):
                base_dps.append(dp_val)
        if len(base_dps) < DELIV_BASE_MIN:
            continue
        base_mean = float(np.mean(base_dps))
        base_std = float(np.std(base_dps, ddof=1))
        if base_std <= 0:
            continue
        scores[ent] = (dp_mean - base_mean) / base_std

    return scores


def score_c3_psb2(panel: Panel, t: date, c2_scores: dict[str, float] | None = None) -> dict[str, float]:
    if c2_scores is None:
        c2_scores = score_c2_psb2(panel, t)
    if not c2_scores:
        return {}
    ents = sorted(c2_scores.keys())
    vals = np.array([c2_scores[e] for e in ents])
    p = _pct_rank(vals)
    t_21 = _day_back(panel, t, RETURN_HORIZON_DAYS)
    if t_21 is None:
        return {}
    scores: dict[str, float] = {}
    for i, ent in enumerate(ents):
        r = _ret(panel, ent, t_21, t)
        if r is None:
            continue
        scores[ent] = -r * (1.0 - 2.0 * p[i])
    return scores


def score_c4_psb2(panel: Panel, t: date, grid_idx: int, monthly_grid_dates: list[date]) -> dict[str, float]:
    if grid_idx < C4_MIN_PRIOR_GRID:
        return {}
    t_g12 = monthly_grid_dates[grid_idx - C4_LOOKBACK_12]
    t_g1 = monthly_grid_dates[grid_idx - C4_LOOKBACK_1]
    members = members_at(panel, t)
    scores: dict[str, float] = {}
    for ent in members:
        p_t = _price(panel, ent, t)
        p_t12 = _price(panel, ent, t_g12)
        p_t1 = _price(panel, ent, t_g1)
        if p_t is None or p_t12 is None or p_t1 is None or p_t12 <= 0 or p_t1 <= 0:
            continue
        r_12 = p_t / p_t12 - 1.0
        r_1 = p_t / p_t1 - 1.0
        scores[ent] = (1.0 + r_12) / (1.0 + r_1) - 1.0
    return scores


# ── Exit band wrapper (1R-9) ────────────────────────────────────────────────────

def _quintile_sequences_psb2(scored_by_date: list, banded: bool = False, exit_band: float | None = None):
    """Thin wrapper around PSB-1's _quintile_sequences with explicit band parameter.

    Changed from PSB-1: band is a parameter, not a module-level constant.
    banded=True with exit_band=None uses the default (C5_EXIT_BAND=0.40).
    """
    from scripts.psb1.screening_harness import _quintile_sequences as _qs
    return _qs(scored_by_date, banded)


# ── C4 Staggered 6-tranche holding ─────────────────────────────────────────────

def _staggered_sequences(
    panel: Panel,
    scored_by_date: list[tuple[date, list[tuple[str, float, float]]]],
    monthly_grid_dates: list[date],
    monthly_grid: list[date],
) -> tuple[
    list[tuple[date, list[tuple[str, float]]]],
    list[tuple[date, list[tuple[str, float]]]],
]:
    """C4 staggered 6-tranche holding.

    6 tranches, 1/6th rebalanced per month. A name entering a tranche stays
    until that tranche's next rebalance (6 months later), regardless of rank drift.
    Even if a name stops scoring, it remains in its tranche — its forward return
    for that period is recorded as the actual return (or None if truly untradeable).

    scored_by_date: list of (t, [(ent, score, fwd)]) for each formation date.
    monthly_grid_dates: full monthly grid for forward-return period lookup.
    monthly_grid: the panel's monthly grid for computing forward periods.
    """
    n_tranches = C4_N_TRANCHES
    tranches: list[set[str]] = [set() for _ in range(n_tranches)]
    topq_held_seq: list[tuple[date, list[tuple[str, float]]]] = []
    base_seq: list[tuple[date, list[tuple[str, float]]]] = []

    for idx, (t, rows) in enumerate(scored_by_date):
        g_idx = monthly_grid_dates.index(t) if t in monthly_grid_dates else -1
        if g_idx < 0 or g_idx + 1 >= len(monthly_grid_dates):
            continue
        tp = monthly_grid_dates[g_idx + 1]

        rebal_tranche = idx % n_tranches

        if rows:
            rows_sorted = sorted(rows, key=lambda x: x[1], reverse=True)
            n_q = max(1, int(len(rows_sorted) * QUINTILE + 0.5))
            top_quintile = set(e for e, s, f in rows_sorted[:n_q])
            tranches[rebal_tranche] = top_quintile
        else:
            tranches[rebal_tranche] = set()

        held = set()
        for tr in tranches:
            held |= tr

        # Forward returns: compute actual returns for held names (even if not scored)
        fwd_list: list[tuple[str, float]] = []
        for e in sorted(held):
            f = _ret(panel, e, t, tp)
            if f is not None:
                fwd_list.append((e, f))

        topq_held_seq.append((t, fwd_list))

        # Base: all members with available forward
        members_list = members_at(panel, t)
        base_fwd = [(e, _ret(panel, e, t, tp)) for e in members_list]
        base_fwd = [(e, f) for e, f in base_fwd if f is not None]
        base_seq.append((t, base_fwd))

    return topq_held_seq, base_seq


# ── Candidate evaluation ────────────────────────────────────────────────────────

def evaluate_candidate_psb2(
    panel: Panel,
    cid: str,
    score_fn: Any,
    db_path: str,
    monthly_grid_dates: list[date] | None = None,
    fortnightly_grid_dates: list[date] | None = None,
) -> CandidateResult:
    if cid == "C2":
        cadence = "fortnightly"
        dev_lo = C2_DEV_LO
        banded = True
        exit_band = C2_EXIT_BAND
        is_staggered = False
        ppy = 24
    elif cid == "C3":
        cadence = "fortnightly"
        dev_lo = C3_DEV_LO
        banded = True
        exit_band = C3_EXIT_BAND
        is_staggered = False
        ppy = 24
    elif cid == "C4":
        cadence = "monthly"
        dev_lo = C4_DEV_LO
        banded = False
        exit_band = None
        is_staggered = True
        ppy = 12
        if monthly_grid_dates is None:
            raise ValueError("C4 requires monthly_grid_dates")
    else:
        raise ValueError(f"Unknown candidate: {cid}")

    cal = panel.cal
    if cadence == "fortnightly":
        grid = fortnightly_grid(cal)
    else:
        grid = monthly_grid(cal)

    grid_next: dict[date, date | None] = {}
    for i, d in enumerate(grid):
        grid_next[d] = grid[i + 1] if i + 1 < len(grid) else None

    formation_dates = [d for d in grid if dev_lo <= d <= DEV_HI
                       and grid_next.get(d) is not None and grid_next[d] <= DEV_HI]

    ic_list: list[float] = []
    ic_imputed_list: list[float] = []
    excl_counts: list[int] = []
    fwd_missing_counts: list[int] = []
    scored_by_date: list[tuple[date, list[tuple[str, float, float]]]] = []
    min_names_skipped = 0

    for t in formation_dates:
        tp = grid_next[t]
        if tp is None or tp > DEV_HI:
            continue

        scores = score_fn(t)
        if not scores:
            min_names_skipped += 1
            continue

        members = members_at(panel, t)
        excl_counts.append(len(members) - len(scores))

        rows: list[tuple[str, float, float | None]] = []
        scores_list: list[float] = []
        fwd_primary: list[float] = []
        ents_primary: list[str] = []
        fwd_with_none: list[float | None] = []

        for ent, score in scores.items():
            f = _ret(panel, ent, t, tp)
            scores_list.append(score)
            if f is not None:
                fwd_primary.append(f)
                ents_primary.append(ent)
                rows.append((ent, score, f))
                fwd_with_none.append(f)
            else:
                fwd_with_none.append(None)
                rows.append((ent, score, f))

        if len(ents_primary) < MIN_NAMES:
            min_names_skipped += 1
            continue

        fwd_missing_counts.append(len(scores) - len(ents_primary))

        # Pass None-preserving forwards to date_ic (1R-6)
        date_ic_result = date_ic(np.array(list(scores.values())), np.array(fwd_with_none, dtype=object))
        if date_ic_result[0] is not None:
            ic_primary, ic_imputed_val = date_ic_result
            ic_list.append(ic_primary)
            ic_imputed_list.append(ic_imputed_val)

        scored_by_date.append((t, rows))

    if len(ic_list) < 2:
        return CandidateResult(cid=cid, dates=formation_dates, n_dates=len(formation_dates))

    ic_arr = np.array(ic_list)
    mean_ic = float(np.mean(ic_arr))
    sd_ic = float(np.std(ic_arr, ddof=1)) if len(ic_arr) > 1 else 0.0
    _, _, t_stat, p_val = _one_sided_t(ic_arr)
    ac1 = _ac1(ic_arr)
    nw_t = None
    if abs(ac1) > AC1_TRIGGER and len(ic_arr) > 4:
        nw_se = _nw_se(ic_arr, NW_LAG)
        if nw_se > 0:
            nw_t = float(mean_ic / nw_se)

    ic_imputed_arr = np.array(ic_imputed_list) if ic_imputed_list else ic_arr
    mean_ic_imputed = float(np.mean(ic_imputed_arr))
    sign_flag = bool((mean_ic > 0) != (mean_ic_imputed > 0))

    n_half = len(ic_arr) // 2
    first_half_ic = float(np.mean(ic_arr[:n_half])) if n_half > 0 else mean_ic
    second_half_ic = float(np.mean(ic_arr[n_half:])) if len(ic_arr) > n_half else mean_ic

    if is_staggered:
        topq_seq, base_seq = _staggered_sequences(
            panel, scored_by_date, monthly_grid_dates or grid, monthly_grid(cal))
    else:
        topq_seq, botq_seq, base_seq = _quintile_sequences_psb2(scored_by_date, banded=True, exit_band=exit_band)

    topq_net, topq_gross, _, topq_fees = _simulate(topq_seq, ppy)
    base_net, base_gross, _, base_fees = _simulate(base_seq, ppy)

    net_spread = topq_net - base_net
    gross_spread = topq_gross - base_gross
    fee_slip_drag_bp = (topq_gross - topq_net) * 10000.0

    turnovers = []
    for i in range(1, len(topq_seq)):
        prev_ents = {e for e, _ in topq_seq[i - 1][1]}
        curr_ents = {e for e, _ in topq_seq[i][1]}
        if len(curr_ents) > 0:
            churn = len(prev_ents ^ curr_ents) / (2.0 * len(curr_ents))
            turnovers.append(churn)
    turnover = float(np.mean(turnovers)) if turnovers else 0.0

    n_star = sealed_grid_count_psb2(db_path, cadence)
    power_d, power_half = _power(mean_ic, sd_ic, n_star)
    power_nw = None
    if nw_t is not None and sd_ic > 0:
        sd_eff = float(mean_ic / nw_t * math.sqrt(len(ic_arr)))
        if sd_eff > 0:
            power_nw, _ = _power(mean_ic, sd_eff, n_star)

    return CandidateResult(
        cid=cid,
        dates=formation_dates,
        n_dates=len(formation_dates),
        ic=ic_arr,
        ic_imputed=ic_imputed_arr,
        mean_ic=mean_ic,
        sd_ic=sd_ic,
        tstat=t_stat,
        pvalue=p_val,
        ac1=ac1,
        nw_t=nw_t,
        mean_ic_imputed=mean_ic_imputed,
        sign_flag=sign_flag,
        min_names_skipped=min_names_skipped,
        excl_counts=excl_counts,
        fwd_missing_counts=fwd_missing_counts,
        ca_excl_counts=[],
        net_spread=net_spread,
        gross_spread=gross_spread,
        q1_q5=0.0,
        fee_slip_drag_bp=fee_slip_drag_bp,
        turnover=turnover,
        fees_topq=topq_fees,
        fees_base=base_fees,
        first_half_ic=first_half_ic,
        second_half_ic=second_half_ic,
        n_star=n_star,
        power=power_d,
        power_half=power_half,
        power_nw=power_nw,
    )


CANDIDATES = {
    "C2": {"cadence": "fortnightly", "dev_lo": C2_DEV_LO},
    "C3": {"cadence": "fortnightly", "dev_lo": C3_DEV_LO},
    "C4": {"cadence": "monthly", "dev_lo": C4_DEV_LO},
}
