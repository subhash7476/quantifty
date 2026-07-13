"""PSB-1 screening harness (Phase 1).

Implements the FROZEN protocol `docs/reports/PSB1_PROTOCOL.md` Rev 2 exactly:
loader (§2), grids (§3), common scoring rules (§4), candidate scores C1-C5 (§5),
metrics (§6), power projection (§7). This is a library; it computes no candidate
score on real data by itself. Phase 2 drivers (one per candidate) call it after the
Phase-1 Lead Review PASS.

Determinism (§10): no RNG in this module. Every real-data load asserts and prints the
dev fence MAX(trade_date) <= 2022-12-31 (§1/§10); the sole real-store touch permitted
in Phase 1 is `fence_check` (dates only).

Derived from the CSMP `run_a2_validation.load_window()` at commit 0ae1dc4 (ever-member
entity restriction + rn=1 turnover-primary listing dedup), re-implemented here (csmp is
feature-frozen; not imported) and extended to carry deliv_pct through the SAME rn=1 pick
as the price (§2 loader row; Prompt-1 AC-3).
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

import duckdb
import numpy as np
from scipy.stats import nct, spearmanr, t as student_t

from core.execution.equity.delivery_fees import delivery_equity_fees

# ---------------------------------------------------------------------------
# PINNED PARAMETERS — exhaustive, quoting PSB1_PROTOCOL.md §9 (AC-4).
# No value below may change without a new battery (PSB-2) and a fresh ledger.
# ---------------------------------------------------------------------------
DEV_HI = date(2022, 12, 31)               # dev fence (§1/§3)
SEALED_LO = date(2023, 1, 1)              # sealed window start (§7 n* range; not read)
SEALED_HI = date(2026, 6, 30)            # sealed window end   (§7 n* range; not read)

C1_C2_C5_DEV_LO = date(2012, 1, 1)        # §3 dev window, price/vol candidates
C3_C4_DEV_LO = date(2020, 4, 1)           # §3 dev window, delivery candidates
COMMON_SUBWINDOW_LO = date(2020, 4, 1)    # §3/§8 common robustness sub-window

FORMATION_RET_DAYS = 5                     # 5-day formation return (§5 C1/C4; §9)
BETA_WEEKS = 52                            # 52-week beta window (§5 C2; §9)
BETA_MIN_WEEKS = 40                        # >=40 of 52 weeks (§5 C2; §9)
DELIV_MEAN_DAYS = 5                        # 5-day delivery mean (§5 C3; §9)
DELIV_MEAN_MIN = 3                         # >=3 non-NULL (§5 C3; §9)
DELIV_BASE_DAYS = 60                       # 60-day delivery baseline ending t-5 (§5 C3; §9)
DELIV_BASE_MIN = 40                        # >=40 non-NULL (§5 C3; §9)
VOL_DAYS = 252                             # 252-day vol window (§5 C5; §9)
VOL_MIN = 200                              # >=200 obs (§5 C5; §9)
QUINTILE = 0.20                            # quintile portfolios, EW (§6/§9)
C5_EXIT_BAND = 0.40                        # C5 two-quintile exit band (§5 C5/§9)
KAPPA = 0.0005                             # 5 bp/side slippage (§2/§9)
BONFERRONI_M = 5                           # Bonferroni m=5 (§8/§9)
POWER_HURDLE = 0.80                        # power hurdle (§7/§9)
ALPHA = 0.05                               # one-sided (§7/§9)
AC1_TRIGGER = 0.10                         # |AC1| robustness trigger (§6/§7/§9)
NW_LAG = 4                                 # Newey-West lag (§6/§7/§9)
POWER_TIE_BAND = 0.02                     # power tie band (§8/§9)
MIN_NAMES = 5                              # CSMP-inherited: skip a date with <5 scored names (§4)
CAP = 1e7                                  # notional book for fee fractionalisation (CSMP; DP-flat immaterial at book scale)

WEEKLY_PPY = 52
MONTHLY_PPY = 12

STORE = "data/market_data/equity_bhavcopy.duckdb"


# ===========================================================================
# §2 Loading
# ===========================================================================
@dataclass
class Panel:
    cal: list                # sorted full-session trading days (<= cutoff) — master trading-day axis
    cal_pos: dict            # date -> index in cal
    px: dict                 # (entity, date) -> adj close
    dp: dict                 # (entity, date) -> deliv_pct (or None)
    ent_dates: dict          # entity -> sorted list of dates with px
    reb_dates: list          # sorted rebalance dates (<= cutoff)
    memb: dict               # rebalance_date -> list[entity]
    observed_max: date


def load_panel(db_path=STORE, cutoff=DEV_HI):
    """Load the dev-fenced panel. Asserts + prints observed MAX(trade_date) <= cutoff (§1/§10).

    Carries deliv_pct through the SAME rn=1 turnover-primary listing pick as adj_close
    (§2 loader row / AC-3). Price load restricted to ever-member entities (Prompt-13 fix).
    """
    con = duckdb.connect(str(db_path), read_only=True)
    cal = [r[0] for r in con.execute(
        "SELECT trade_date FROM trading_calendar WHERE n_symbols>=200 AND trade_date<=? "
        "ORDER BY trade_date", [cutoff]).fetchall()]
    reb = defaultdict(list)
    for rd, ent in con.execute(
        "SELECT um.rebalance_date, e.entity "
        "FROM universe_membership um JOIN universe_eligibility e ON e.symbol=um.symbol "
        "WHERE um.rebalance_date<=? ORDER BY um.rebalance_date, um.rank", [cutoff]).fetchall():
        reb[rd].append(ent)
    rows = con.execute("""
        SELECT entity, trade_date, adj_close, deliv_pct FROM (
          SELECT e.entity, a.trade_date, a.close adj_close, a.deliv_pct, a.turnover, a.symbol,
            ROW_NUMBER() OVER (PARTITION BY e.entity, a.trade_date
                               ORDER BY a.turnover DESC NULLS LAST, a.symbol) rn
          FROM equity_bhavcopy_adjusted a JOIN universe_eligibility e ON e.symbol=a.symbol
          WHERE a.trade_date<=?
            AND e.entity IN (SELECT DISTINCT e2.entity
                             FROM universe_membership m
                             JOIN universe_eligibility e2 ON e2.symbol=m.symbol)
        ) WHERE rn=1""", [cutoff]).fetchall()
    con.close()

    px, dp, ent_dates = {}, {}, defaultdict(list)
    for ent, d, cl, dpv in rows:
        if cl is not None and cl > 0:
            px[(ent, d)] = float(cl)
            ent_dates[ent].append(d)
        dp[(ent, d)] = None if dpv is None else float(dpv)
    for e in ent_dates:
        ent_dates[e].sort()
    observed_max = max(d for (_, d) in px)
    assert observed_max <= cutoff, f"SEALED LEAK: {observed_max} > {cutoff}"
    print(f"Sealed fence OK: observed MAX(trade_date)={observed_max} <= cutoff={cutoff}")

    cal_pos = {d: i for i, d in enumerate(cal)}
    reb_dates = sorted(reb)
    return Panel(cal, cal_pos, px, dp, ent_dates, reb_dates, dict(reb), observed_max)


def fence_check(db_path=STORE, cutoff=DEV_HI):
    """The ONLY permitted real-store touch in Phase 1 (§7 exception / P7): dates only.

    Runs the fenced MAX(trade_date) query and asserts/prints it <= cutoff. Computes no
    score, loads no prices/symbols beyond the aggregate date.
    """
    con = duckdb.connect(str(db_path), read_only=True)
    observed = con.execute(
        "SELECT MAX(trade_date) FROM equity_bhavcopy_adjusted WHERE trade_date<=?",
        [cutoff]).fetchone()[0]
    con.close()
    assert observed is not None and observed <= cutoff, f"FENCE FAIL: {observed} > {cutoff}"
    print(f"Fence-check OK (dates only): MAX(trade_date)={observed} <= cutoff={cutoff}")
    return observed


# ===========================================================================
# §3 Grids
# ===========================================================================
def weekly_grid(cal):
    """Last full-session day of each ISO week (§3)."""
    out = {}
    for d in cal:
        y, w, _ = d.isocalendar()
        out[(y, w)] = d
    return sorted(out.values())


def monthly_grid(cal):
    """Last full-session day of each calendar month (§3)."""
    out = {}
    for d in cal:
        out[(d.year, d.month)] = d
    return sorted(out.values())


def sealed_grid_count(db_path, cadence):
    """§7.1 n*: grid dates in [2023-01-01, 2026-06-30] at cadence, from trading_calendar
    (dates only — the §1/§7 exception). Does not read prices or symbols."""
    con = duckdb.connect(str(db_path), read_only=True)
    cal = [r[0] for r in con.execute(
        "SELECT trade_date FROM trading_calendar WHERE n_symbols>=200 "
        "AND trade_date>=? AND trade_date<=? ORDER BY trade_date",
        [SEALED_LO, SEALED_HI]).fetchall()]
    con.close()
    g = weekly_grid(cal) if cadence == "weekly" else monthly_grid(cal)
    return len(g)


# ===========================================================================
# §4 helpers
# ===========================================================================
def _pct_rank(values):
    """Fractional percentile ranks in [0,1], average ties, min->0 max->1 (§4.4)."""
    a = np.asarray(values, float)
    n = len(a)
    if n == 1:
        return np.array([0.0])
    _, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
    csum = np.cumsum(counts)
    start = csum - counts
    avg = (start + csum - 1) / 2.0
    ranks = avg[inv]
    return ranks / (n - 1)


def _price(panel, ent, d):
    return panel.px.get((ent, d))


def _ret(panel, ent, d0, d1):
    p0, p1 = panel.px.get((ent, d0)), panel.px.get((ent, d1))
    if p0 and p1 and p0 > 0:
        return p1 / p0 - 1.0
    return None


def _day_back(panel, t, k):
    """The k-th full-session trading day before t on the master axis, or None."""
    i = panel.cal_pos.get(t)
    if i is None or i - k < 0:
        return None
    return panel.cal[i - k]


def members_at(panel, t):
    """Membership at formation date t = most recent rebalance_date <= t (§2)."""
    lo, hi, best = 0, len(panel.reb_dates) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if panel.reb_dates[mid] <= t:
            best = panel.reb_dates[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return panel.memb.get(best, []) if best is not None else []


# ===========================================================================
# §5 candidate scores  ->  {entity: score} for formation date t
# ===========================================================================
def score_c1(panel, t):
    tb = _day_back(panel, t, FORMATION_RET_DAYS)
    if tb is None:
        return {}
    out = {}
    for e in members_at(panel, t):
        r = _ret(panel, e, tb, t)
        if r is not None:
            out[e] = -r
    return out


def _weekly_grid_index(wgrid):
    return {d: i for i, d in enumerate(wgrid)}


def market_weekly_returns(panel, wgrid):
    """r_mkt(w) = EW mean of r_i(w-5, w) over members at w with both prices (§5 C2)."""
    rmkt = {}
    for w in wgrid:
        wb = _day_back(panel, w, FORMATION_RET_DAYS)
        if wb is None:
            continue
        rs = [r for e in members_at(panel, w) if (r := _ret(panel, e, wb, w)) is not None]
        if rs:
            rmkt[w] = float(np.mean(rs))
    return rmkt


def score_c2(panel, t, wgrid, widx, rmkt):
    gi = widx.get(t)
    if gi is None or gi - BETA_WEEKS < 0:
        return {}
    window = wgrid[gi - BETA_WEEKS:gi]           # 52 grids preceding t, formation week excluded
    tb = _day_back(panel, t, FORMATION_RET_DAYS)
    if tb is None or t not in rmkt:
        return {}
    rm_t = rmkt[t]
    out = {}
    for e in members_at(panel, t):
        xs, ys = [], []
        for g in window:
            if g not in rmkt:
                continue
            gb = _day_back(panel, g, FORMATION_RET_DAYS)
            if gb is None:
                continue
            ri = _ret(panel, e, gb, g)
            if ri is None:
                continue
            xs.append(rmkt[g]); ys.append(ri)
        if len(ys) < BETA_MIN_WEEKS:
            continue
        r_form = _ret(panel, e, tb, t)
        if r_form is None:
            continue
        x = np.asarray(xs); y = np.asarray(ys)
        beta, alpha = np.polyfit(x, y, 1)
        resid = y - (alpha + beta * x)
        dof = len(y) - 2
        if dof <= 0:
            continue
        sigma = math.sqrt(float(resid @ resid) / dof)
        if not (sigma > 0):
            continue
        resid_t = r_form - alpha - beta * rm_t
        out[e] = -resid_t / sigma
    return out


def _deliv_window(panel, ent, end_idx, n_days):
    """Non-NULL deliv_pct values over the n_days ending at cal[end_idx]."""
    vals = []
    for j in range(max(0, end_idx - n_days + 1), end_idx + 1):
        v = panel.dp.get((ent, panel.cal[j]))
        if v is not None:
            vals.append(v)
    return vals


def score_c3(panel, t):
    it = panel.cal_pos.get(t)
    if it is None or it - FORMATION_RET_DAYS < 0:
        return {}
    base_end = it - FORMATION_RET_DAYS
    if base_end - DELIV_BASE_DAYS + 1 < 0:
        return {}
    out = {}
    for e in members_at(panel, t):
        recent = _deliv_window(panel, e, it, DELIV_MEAN_DAYS)
        if len(recent) < DELIV_MEAN_MIN:
            continue
        base = _deliv_window(panel, e, base_end, DELIV_BASE_DAYS)
        if len(base) < DELIV_BASE_MIN:
            continue
        mu = float(np.mean(base)); sd = float(np.std(base, ddof=1))
        if not (sd > 0):
            continue
        out[e] = (float(np.mean(recent)) - mu) / sd
    return out


def score_c4(panel, t):
    c1 = score_c1(panel, t)
    c3 = score_c3(panel, t)
    if not c3:
        return {}
    ents = list(c3.keys())
    p = dict(zip(ents, _pct_rank([c3[e] for e in ents])))
    out = {}
    for e in c1:                                  # formation-complete = C1 and C3 (§5 C4)
        if e in p:
            out[e] = c1[e] * (1 - 2 * p[e])       # c1[e] = -r_i(t-5,t); s = -r*(1-2p)
    return out


def score_c5(panel, t):
    it = panel.cal_pos.get(t)
    if it is None or it - VOL_DAYS + 1 < 0:
        return {}
    lo = it - VOL_DAYS + 1
    out = {}
    for e in members_at(panel, t):
        closes = [(j, panel.px[(e, panel.cal[j])]) for j in range(lo, it + 1)
                  if (e, panel.cal[j]) in panel.px]
        rets = [closes[k][1] / closes[k - 1][1] - 1.0
                for k in range(1, len(closes)) if closes[k - 1][0] == closes[k][0] - 1]
        if len(rets) < VOL_MIN:
            continue
        sd = float(np.std(rets, ddof=1))
        if not (sd > 0):
            continue
        out[e] = -sd
    return out


CANDIDATES = {
    "C1": {"cadence": "weekly", "dev_lo": C1_C2_C5_DEV_LO},
    "C2": {"cadence": "weekly", "dev_lo": C1_C2_C5_DEV_LO},
    "C3": {"cadence": "weekly", "dev_lo": C3_C4_DEV_LO},
    "C4": {"cadence": "weekly", "dev_lo": C3_C4_DEV_LO},
    "C5": {"cadence": "monthly", "dev_lo": C1_C2_C5_DEV_LO},
}


# ===========================================================================
# §6 metrics + §4.2 imputation
# ===========================================================================
@dataclass
class CandidateResult:
    cid: str
    dates: list
    ic: np.ndarray
    ic_imputed: np.ndarray
    n_dates: int
    mean_ic: float
    sd_ic: float
    tstat: float
    pvalue: float
    ac1: float
    nw_t: float | None
    mean_ic_imputed: float
    excl_counts: list
    fwd_missing_counts: list
    net_spread: float
    gross_spread: float
    q1_q5: float
    fee_slip_drag_bp: float
    turnover: float
    fees_topq: float
    fees_base: float
    first_half_ic: float
    second_half_ic: float
    n_star: int
    power: float
    power_half: float
    power_nw: float | None


def _one_sided_t(ic):
    n = len(ic)
    mean = float(np.mean(ic)); sd = float(np.std(ic, ddof=1))
    se = sd / math.sqrt(n)
    tstat = mean / se if se > 0 else 0.0
    p = float(student_t.sf(tstat, df=n - 1))
    return mean, sd, tstat, p


def _ac1(x):
    x = np.asarray(x, float)
    if len(x) < 3:
        return 0.0
    xm = x - x.mean()
    denom = float(xm @ xm)
    return float(xm[:-1] @ xm[1:] / denom) if denom > 0 else 0.0


def _nw_se(x, lag=NW_LAG):
    x = np.asarray(x, float)
    n = len(x)
    xm = x - x.mean()
    g0 = float(xm @ xm) / n
    lrv = g0
    for k in range(1, lag + 1):
        gk = float(xm[:-k] @ xm[k:]) / n
        lrv += 2 * (1 - k / (lag + 1)) * gk
    lrv = max(lrv, 1e-18)
    return math.sqrt(lrv / n)


def _forward(panel, ent, t, tp):
    return _ret(panel, ent, t, tp)


def date_ic(s_all, fwd_all):
    """Per-date primary and §4.2-imputed Spearman IC.

    Primary excludes names with no forward (fwd is None). Imputed sets a missing forward
    to that date's worst realized forward among scored names (§4.2). Returns
    (primary_ic, imputed_ic) or (None, None) if fewer than MIN_NAMES have a forward.
    """
    present = [(s, f) for s, f in zip(s_all, fwd_all) if f is not None]
    if len(present) < MIN_NAMES:
        return None, None
    s_p = [s for s, _ in present]; f_p = [f for _, f in present]
    rho, _ = spearmanr(s_p, f_p)
    worst = min(f_p)
    f_imp = [f if f is not None else worst for f in fwd_all]
    rho_imp, _ = spearmanr(s_all, f_imp)
    return float(rho), float(rho_imp)


def _simulate(seq, ppy):
    """seq: list of (t, holdings) where holdings = list[(entity, fwd_return)].
    Returns ann_net, ann_gross, net_returns, total_fees. Fees+slippage on entry/exit
    turnover (CSMP simulate); baseline leg charged the same way (§6)."""
    V = CAP; prev = set(); grets = []; nrets = []; total_fee = 0.0
    for t, hold in seq:
        names = [e for e, _ in hold]
        N = max(len(names), 1)
        gross = float(np.mean([r for _, r in hold])) if hold else 0.0
        cur = set(names)
        ent = cur - prev; ex = prev - cur
        fee = sum(delivery_equity_fees(side="BUY", trade_value=V / N, trade_date=t).total for _ in ent) \
            + sum(delivery_equity_fees(side="SELL", trade_value=V / N, trade_date=t).total for _ in ex)
        slip = KAPPA * (len(ent) + len(ex)) * (V / N)
        total_fee += fee + slip
        Vn = (V - fee - slip) * (1 + gross)
        nrets.append(Vn / V - 1.0); grets.append(gross); V = Vn; prev = cur
    npd = len(seq)
    if npd == 0:
        return 0.0, 0.0, np.array([]), 0.0
    ann_net = (V / CAP) ** (ppy / npd) - 1
    ann_gross = float(np.prod([1 + g for g in grets]) ** (ppy / npd) - 1)
    return ann_net, ann_gross, np.array(nrets), total_fee


def _quintile_sequences(scored_by_date, banded):
    """Build top-quintile, bottom-quintile and baseline holding sequences.
    scored_by_date: list of (t, [(entity, score, fwd)]). banded: C5 hysteresis (§5 C5)."""
    topq, botq, base = [], [], []
    held = set()
    for t, rows in scored_by_date:
        rows_sorted = sorted(rows, key=lambda r: r[1], reverse=True)
        n = len(rows_sorted)
        ntop = max(1, round(QUINTILE * n))
        top_set = {r[0] for r in rows_sorted[:ntop]}
        if banded:
            keep_thresh = max(1, round(C5_EXIT_BAND * n))
            keep_set = {r[0] for r in rows_sorted[:keep_thresh]}
            new_held = (held & keep_set) | top_set
            held = new_held
            topq.append((t, [(e, r) for (e, s, r) in rows if e in held]))
        else:
            topq.append((t, [(e, r) for (e, s, r) in rows if e in top_set]))
        bot_set = {r[0] for r in rows_sorted[-ntop:]}
        botq.append((t, [(e, r) for (e, s, r) in rows if e in bot_set]))
        base.append((t, [(e, r) for (e, s, r) in rows]))
    return topq, botq, base


def evaluate_candidate(panel, cid, score_fn, db_path=STORE):
    """Run one candidate end-to-end over its declared dev window. score_fn(t)->{entity:score}."""
    meta = CANDIDATES[cid]
    cadence = meta["cadence"]; dev_lo = meta["dev_lo"]
    grid = weekly_grid(panel.cal) if cadence == "weekly" else monthly_grid(panel.cal)
    ppy = WEEKLY_PPY if cadence == "weekly" else MONTHLY_PPY
    gidx = {d: i for i, d in enumerate(grid)}

    forms = [d for d in grid if dev_lo <= d <= DEV_HI
             and gidx[d] + 1 < len(grid) and grid[gidx[d] + 1] <= DEV_HI]

    ic_list, ic_imp_list, dates = [], [], []
    excl_counts, fwd_missing = [], []
    scored_by_date = []
    for t in forms:
        tp = grid[gidx[t] + 1]
        scores = score_fn(t)
        members = members_at(panel, t)
        excl_counts.append(len(members) - len(scores))
        rows_primary = []           # (entity, score, fwd) fwd present
        s_all, fwd_all = [], []     # for imputed IC (fwd may be None)
        missing = 0
        for e, s in scores.items():
            f = _forward(panel, e, t, tp)
            s_all.append(s); fwd_all.append(f)
            if f is None:
                missing += 1
            else:
                rows_primary.append((e, s, f))
        fwd_missing.append(missing)
        rho, rho_imp = date_ic(s_all, fwd_all)
        if rho is None:
            continue
        ic_list.append(rho); ic_imp_list.append(rho_imp); dates.append(t)
        scored_by_date.append((t, rows_primary))

    ic = np.array(ic_list); ic_imp = np.array(ic_imp_list)
    mean, sd, tstat, p = _one_sided_t(ic)
    ac1 = _ac1(ic)
    nw_t = None
    if abs(ac1) > AC1_TRIGGER:
        nw_se = _nw_se(ic)
        nw_t = float(np.mean(ic)) / nw_se if nw_se > 0 else 0.0

    half = len(ic) // 2
    fh = float(np.mean(ic[:half])) if half else float("nan")
    sh = float(np.mean(ic[half:])) if len(ic) - half else float("nan")

    banded = (cid == "C5")
    topq, botq, base = _quintile_sequences(scored_by_date, banded)
    tq_net, tq_gross, _, tq_fee = _simulate(topq, ppy)
    bq_net, bq_gross, _, _ = _simulate(botq, ppy)
    bs_net, bs_gross, _, bs_fee = _simulate(base, ppy)
    net_spread = tq_net - bs_net
    gross_spread = tq_gross - bs_gross
    q1_q5 = tq_gross - bq_gross
    drag_bp = (tq_gross - tq_net) * 1e4
    turnovers = []
    prev = set()
    for t, hold in topq:
        cur = {e for e, _ in hold}
        turnovers.append(len(cur - prev) / max(len(cur), 1)); prev = cur
    turnover = float(np.mean(turnovers)) if turnovers else 0.0

    n_star = sealed_grid_count(db_path, cadence)
    power, power_half = _power(mean, sd, n_star)
    power_nw = None
    if nw_t is not None:
        nw_se = _nw_se(ic)
        sd_eff = nw_se * math.sqrt(len(ic))
        power_nw, _ = _power(mean, sd_eff, n_star)

    return CandidateResult(
        cid=cid, dates=dates, ic=ic, ic_imputed=ic_imp, n_dates=len(ic),
        mean_ic=mean, sd_ic=sd, tstat=tstat, pvalue=p, ac1=ac1, nw_t=nw_t,
        mean_ic_imputed=float(np.mean(ic_imp)) if len(ic_imp) else float("nan"),
        excl_counts=excl_counts, fwd_missing_counts=fwd_missing,
        net_spread=net_spread, gross_spread=gross_spread, q1_q5=q1_q5,
        fee_slip_drag_bp=drag_bp, turnover=turnover, fees_topq=tq_fee, fees_base=bs_fee,
        first_half_ic=fh, second_half_ic=sh,
        n_star=n_star, power=power, power_half=power_half, power_nw=power_nw)


# ===========================================================================
# §7 power projection
# ===========================================================================
def _power(delta, sd, n_star):
    """Projected power for a one-sided 95% t-gate on n_star obs (§7.2).
    Noncentral-t with ncp = delta * sqrt(n_star) / sd; and reported-only at delta/2."""
    if not (sd > 0) or n_star < 2:
        return 0.0, 0.0
    tcrit = student_t.ppf(1 - ALPHA, df=n_star - 1)
    ncp = delta * math.sqrt(n_star) / sd
    ncp_half = (delta / 2) * math.sqrt(n_star) / sd
    return float(nct.sf(tcrit, n_star - 1, ncp)), float(nct.sf(tcrit, n_star - 1, ncp_half))


SCORE_FUNCS = {
    "C1": lambda p: (lambda t: score_c1(p, t)),
    "C3": lambda p: (lambda t: score_c3(p, t)),
    "C4": lambda p: (lambda t: score_c4(p, t)),
    "C5": lambda p: (lambda t: score_c5(p, t)),
}


def make_score_fn(panel, cid):
    """Return the score_fn(t) for a candidate (C2 needs precomputed market returns)."""
    if cid == "C2":
        wg = weekly_grid(panel.cal)
        widx = _weekly_grid_index(wg)
        rmkt = market_weekly_returns(panel, wg)
        return lambda t: score_c2(panel, t, wg, widx, rmkt)
    return SCORE_FUNCS[cid](panel)
