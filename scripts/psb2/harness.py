"""PSB-2 Screening Harness — adapted from PSB-1 (FROZEN Rev 4).

Reuses generic infrastructure from scripts.psb1.screening_harness by import
(scripts/psb1/ stays git-clean). PSB-2-specific additions: fortnightly grid,
C2/C3/C4 scorers, C4 staggered 6-tranche holding, and a evaluate_candidate
that dispatches banded (C2/C3) vs staggered (C4) portfolio simulation.

Imported unchanged from PSB-1 (verified identical):
  Panel, CandidateResult, load_panel, fence_check, monthly_grid,
  sealed_grid_count (extended for fortnightly), _pct_rank, _price, _ret,
  _day_back, _day_forward, members_at, _one_sided_t, _ac1, _nw_se, _power,
  date_ic, _quintile_sequences, _simulate, MIN_NAMES, KAPPA, CAP, ALPHA,
  QUINTILE, POWER_HURDLE, POWER_TIE_BAND, AC1_TRIGGER, NW_LAG, BONFERRONI_M
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any

import numpy as np
import scipy.stats as ss

from scripts.psb1.screening_harness import (
    Panel,
    CandidateResult,
    load_panel,
    fence_check,
    monthly_grid,
    sealed_grid_count,
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
    _quintile_sequences,
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
BONFERRONI_M = 3                # m=3 (D11, data-independence rationale)
C2_EXIT_BAND = 0.40             # banded exit at top two quintiles
C3_EXIT_BAND = 0.40             # same band
C4_N_TRANCHES = 6               # staggered 6-tranche holding

# C2 parameters
DELIV_BASE_DAYS = 252
DELIV_BASE_END_OFFSET = 21      # baseline ends at t-21
DELIV_BASE_MIN = 150            # ≥ 150 non-NULL
DELIV_MEAN_MIN = 8              # ≥ 8 non-NULL (fortnightly)

# C3 parameters
RETURN_HORIZON_DAYS = 21        # 21-trading-day return for r_i(t)

# C4 parameters
C4_LOOKBACK_12 = 12             # g-12 for r_12
C4_LOOKBACK_1 = 1               # g-1 for r_1
C4_MIN_PRIOR_GRID = 12          # requires 12 prior grid dates

# Dev windows (per-candidate, §3)
DEV_HI = date(2022, 12, 31)
C2_DEV_LO = date(2020, 9, 4)
C3_DEV_LO = date(2020, 9, 4)
C4_DEV_LO = date(2012, 1, 1)
COMMON_SUBWINDOW_LO = date(2020, 9, 4)

# ── Fortnightly grid (§3) ──────────────────────────────────────────────────────

def fortnightly_grid(cal: list[date]) -> list[date]:
    """Last full session on or before the 15th + last full session per month."""
    grid = []
    for idx, d in enumerate(cal):
        is_mid = d.day <= 15
        is_eom = (idx + 1 >= len(cal) or cal[idx + 1].month != d.month)
        if is_mid:
            next_idx = idx + 1
            is_last_mid = True
            if next_idx < len(cal) and cal[next_idx].month == d.month and cal[next_idx].day <= 15:
                is_last_mid = False
            if is_last_mid:
                grid.append(d)
        if is_eom:
            grid.append(d)
    return grid


def sealed_grid_count_psb2(db_path: str, cadence: str) -> int:
    """n* count for PSB-2 cadences. Dates only — no prices."""
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
    else:
        raise ValueError(f"Unknown cadence: {cadence}")


# ── §5 Scorers ──────────────────────────────────────────────────────────────────

def score_c2_psb2(panel: Panel, t: date) -> dict[str, float]:
    """C2 — Delivery-percentage anomaly, fortnightly.

    dp_i(t) = mean of deliv_pct over fortnight's trading days ending t  (≥ 8 non-NULL)
    μ_i, σ_i = mean, std of deliv_pct over 252 trading days ending t-21 (≥ 150 non-NULL, σ_i > 0)
    s_i(t) = (dp_i(t) - μ_i) / σ_i
    """
    t_21 = _day_back(panel, t, DELIV_BASE_END_OFFSET)
    if t_21 is None:
        return {}
    t_base = _day_back(panel, t_21, DELIV_BASE_DAYS - 1)
    if t_base is None:
        return {}

    members = members_at(panel, t)
    scores: dict[str, float] = {}

    for ent in members:
        # Fortnightly mean (trading days since prior grid date)
        # We define "fortnight" as trading days from the prior grid date to t.
        # For the harness we use a sliding window approach: the last ~10 trading days.
        # We find the first date on or after the prior grid date by scanning from t back.
        # Simpler: take the most recent ~10 full-session days ending at t.
        recent_dps = []
        cal_idx = panel.cal_pos.get(t)
        if cal_idx is None:
            continue
        for j in range(cal_idx, max(cal_idx - 20, -1), -1):
            dd = panel.cal[j]
            dp_val = panel.dp.get((ent, dd))
            if dp_val is not None and not (isinstance(dp_val, float) and math.isnan(dp_val)):
                recent_dps.append(dp_val)
            if len(recent_dps) >= 15:
                break
        if len(recent_dps) < DELIV_MEAN_MIN:
            continue
        dp_mean = float(np.mean(recent_dps))

        # Baseline 252 days ending t-21
        base_dps = []
        for j in range(panel.cal_pos.get(t_21, -1), max(panel.cal_pos.get(t_base, -1) - 1, -1), -1):
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
    """C3 — Delivery-conditioned reversal, fortnightly.

    p_i(t) = percentile rank of C2 score s^{C2}_i(t) among scored names.
    r_i(t) = trailing 21-trading-day return (close at t / close at t-21 days, minus 1).
    s_i(t) = -r_i(t) * (1 - 2·p_i(t))
    """
    if c2_scores is None:
        c2_scores = score_c2_psb2(panel, t)
    if not c2_scores:
        return {}

    # Percentile ranks of C2 scores
    ents = sorted(c2_scores.keys())
    vals = np.array([c2_scores[e] for e in ents])
    p = _pct_rank(vals)  # [0,1]

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
    """C4 — Momentum 12-1, monthly.

    Let g = monthly grid index. For a name scored at grid date t_g:
      r_{12,i}(g) = P_i(t_g) / P_i(t_{g-12}) - 1
      r_{1,i}(g)  = P_i(t_g) / P_i(t_{g-1}) - 1
      s_i(g)      = (1 + r_12) / (1 + r_1) - 1

    Requires 12 prior grid dates of price history.
    """
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


# ── C4 Staggered 6-tranche holding ─────────────────────────────────────────────

def _staggered_sequences(
    panel: Panel,
    scored_by_date: list[tuple[date, dict[str, float]]],
    monthly_grid_dates: list[date],
) -> tuple[
    list[tuple[date, list[tuple[str, float]]]],  # topq: (t, [(ent, fwd)])
    list[tuple[date, list[tuple[str, float]]]],  # base: (t, [(ent, fwd)])
]:
    """C4 staggered 6-tranche holding.

    6 tranches, 1/6th rebalanced per month. A name entering a tranche stays
    until that tranche's next rebalance (6 months later), regardless of rank drift.
    Returns (topq_held, base) sequences for _simulate().

    scored_by_date: list of (t, {ent: score}) for each monthly grid date.
    monthly_grid_dates: full monthly grid for forward-return lookup.
    """
    n_tranches = C4_N_TRANCHES
    tranches: list[set[str]] = [set() for _ in range(n_tranches)]
    topq_held_seq: list[tuple[date, list[tuple[str, float]]]] = []
    base_seq: list[tuple[date, list[tuple[str, float]]]] = []

    for idx, (t, rows) in enumerate(scored_by_date):
        # Find forward return date (next monthly grid date)
        g_idx = monthly_grid_dates.index(t) if t in monthly_grid_dates else -1
        if g_idx < 0 or g_idx + 1 >= len(monthly_grid_dates):
            continue
        tp = monthly_grid_dates[g_idx + 1]

        # Current tranche to rebalance (round-robin)
        rebal_tranche = idx % n_tranches

        # Score-ranked entities (rows = [(ent, score, fwd)])
        if not rows:
            # No scores: liquidate the rebalancing tranche; hold everything else
            tranches[rebal_tranche] = set()
            held = set()
            for tr in tranches:
                held |= tr
            topq_held_seq.append((t, [(e, f) for e, s, f in sorted(rows) if e in held]))
            base_seq.append((t, []))
            continue

        # Sort by score descending
        rows_sorted = sorted(rows, key=lambda x: x[1], reverse=True)
        n_q = max(1, int(len(rows_sorted) * QUINTILE + 0.5))
        top_quintile = set(e for e, s, f in rows_sorted[:n_q])

        # Liquidate the rebalancing tranche, replace with current top quintile
        tranches[rebal_tranche] = top_quintile

        # All held names across all tranches
        held = set()
        for tr in tranches:
            held |= tr

        # Forward returns for held names (use the stored fwd from rows)
        fwd_map = {e: f for e, s, f in rows}
        topq_held_seq.append((t, [(e, fwd_map[e]) for e in sorted(held) if e in fwd_map]))

        # Base: all scored entities with available forward
        base_seq.append((t, [(e, f) for e, s, f in rows]))

    return topq_held_seq, base_seq


# ── Candidate evaluation ────────────────────────────────────────────────────────

DAYS_PER_YEAR = 365.25


def evaluate_candidate_psb2(
    panel: Panel,
    cid: str,
    score_fn: Any,
    db_path: str,
    monthly_grid_dates: list[date] | None = None,
) -> CandidateResult:
    """Evaluate one PSB-2 candidate.

    Parameters:
      panel: loaded Panel
      cid: "C2", "C3", or "C4"
      score_fn: function t → {ent: score}
      db_path: for sealed n* count (dates only)
      monthly_grid_dates: required for C4 (staggered)
    """
    # Determine cadence and dev window
    if cid == "C2":
        cadence = "fortnightly"
        dev_lo = C2_DEV_LO
        banded = True
        exit_band = C2_EXIT_BAND
        is_staggered = False
        ppy = 24  # 24 fortnightly periods per year (~24 * 15 days)
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

    # Grid
    cal = panel.cal
    if cadence == "fortnightly":
        grid = fortnightly_grid(cal)
    else:
        grid = monthly_grid(cal)

    # Build grid → next-grid mapping for forward returns
    grid_dates = grid
    grid_next: dict[date, date | None] = {}
    for i, d in enumerate(grid_dates):
        grid_next[d] = grid_dates[i + 1] if i + 1 < len(grid_dates) else None

    # Formation dates: within dev window with forward available
    formation_dates = [d for d in grid_dates if dev_lo <= d <= DEV_HI and grid_next.get(d) is not None and grid_next[d] <= DEV_HI]

    # Score and compute IC per formation date
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

        s_all: list[float] = []
        fwd_all: list[float] = []
        fwd_primary: list[float] = []
        ents_primary: list[str] = []
        rows: list[tuple[str, float, float]] = []

        for ent, score in scores.items():
            f = _ret(panel, ent, t, tp)
            if f is not None:
                s_all.append(score)
                fwd_all.append(f)
                fwd_primary.append(f)
                ents_primary.append(ent)
                rows.append((ent, score, f))
            else:
                s_all.append(score)

        if len(ents_primary) < MIN_NAMES:
            min_names_skipped += 1
            continue

        fwd_missing_counts.append(len(scores) - len(ents_primary))

        # Imputation: missing forward = worst realized forward return among scored names at this date
        if len(fwd_primary) > 0:
            worst_fwd = float(np.min(fwd_primary))
            fwd_imputed: list[float] = []
            for ent, score in scores.items():
                f = _ret(panel, ent, t, tp)
                if f is not None:
                    fwd_imputed.append(f)
                else:
                    fwd_imputed.append(worst_fwd)
            ic_primary, ic_imputed = date_ic(
                np.array(list(scores.values())),
                np.array(fwd_imputed),
            )
        else:
            ic_primary, ic_imputed = None, None

        if ic_primary is not None:
            ic_list.append(ic_primary)
        if ic_imputed is not None:
            ic_imputed_list.append(ic_imputed)

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

    # Split half
    n_half = len(ic_arr) // 2
    first_half_ic = float(np.mean(ic_arr[:n_half])) if n_half > 0 else mean_ic
    second_half_ic = float(np.mean(ic_arr[n_half:])) if len(ic_arr) > n_half else mean_ic

    # ── Portfolio simulation ──
    if is_staggered:
        topq_seq, base_seq = _staggered_sequences(panel, scored_by_date, monthly_grid_dates or grid)
    else:
        topq_seq, botq_seq, base_seq = _quintile_sequences(scored_by_date, banded=True)

    topq_net, topq_gross, _, topq_fees = _simulate(topq_seq, ppy)
    base_net, base_gross, _, base_fees = _simulate(base_seq, ppy)

    net_spread = topq_net - base_net
    gross_spread = topq_gross - base_gross
    fee_slip_drag_bp = (topq_gross - topq_net) * 10000.0

    # Turnover
    turnovers = []
    for i in range(1, len(topq_seq)):
        prev_ents = {e for e, _ in topq_seq[i - 1][1]}
        curr_ents = {e for e, _ in topq_seq[i][1]}
        if len(curr_ents) > 0:
            churn = len(prev_ents ^ curr_ents) / (2.0 * len(curr_ents))
            turnovers.append(churn)
    turnover = float(np.mean(turnovers)) if turnovers else 0.0

    # Power projection
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


# ── Candidate registry ──────────────────────────────────────────────────────────

CANDIDATES = {
    "C2": {"cadence": "fortnightly", "dev_lo": C2_DEV_LO},
    "C3": {"cadence": "fortnightly", "dev_lo": C3_DEV_LO},
    "C4": {"cadence": "monthly", "dev_lo": C4_DEV_LO},
}
