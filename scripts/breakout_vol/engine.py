"""BKV-1 engine: dense panel, signal detection (no outcomes), forward outcomes.

Detection (`detect_events`) touches no forward price. `attach_outcomes` is the only function that
reads t+1.. prices, and is called only after the freeze.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

from scripts.breakout_vol import common as C
from scripts.breakout_vol.common import P, Params

KIND_SIGN = {"up": 1, "dn": -1, "dup": 1, "ddn": -1}
ST_NORMAL, ST_TERMINAL, ST_DROPPED, ST_BEYOND = 0, 1, 2, 3


@dataclass
class Panel:
    entities: list
    sessions: np.ndarray            # datetime64[D], the regular-session calendar
    O: np.ndarray
    H: np.ndarray
    L: np.ndarray
    C: np.ndarray
    V: np.ndarray
    TO: np.ndarray
    valid: np.ndarray
    member: np.ndarray
    dropped_sessions: pd.DataFrame  # calendar dates removed by the regular-session rule, with the reason


def regular_calendar(cal: pd.DataFrame, p: Params = P) -> tuple[np.ndarray, pd.DataFrame]:
    """Regular sessions = trading_calendar dates with n_symbols >= 200, Mon-Fri, and total EQ turnover
    >= ratio x the centred 21-session median (removes Muhurat / special / defect sessions)."""
    cal = cal.copy()
    cal["trade_date"] = pd.to_datetime(cal["trade_date"])
    cal["n_symbols"] = cal["n_symbols"].fillna(0).astype(int)
    base = cal[(cal["n_symbols"] >= p.calendar_min_symbols) & (cal["trade_date"].dt.weekday < 5)].reset_index(drop=True)
    med = base["tot_turnover_eq"].rolling(p.short_session_window, center=True,
                                          min_periods=p.short_session_window // 2 + 1).median()
    ratio = base["tot_turnover_eq"] / med
    keep = ratio >= p.short_session_ratio
    dropped = cal[~cal["trade_date"].isin(base.loc[keep, "trade_date"])].copy()
    dropped["reason"] = np.where(dropped["trade_date"].dt.weekday >= 5, "weekend",
                                 np.where(dropped["n_symbols"] < p.calendar_min_symbols, "n_symbols<200",
                                          "short_session_turnover"))
    return base.loc[keep, "trade_date"].to_numpy(dtype="datetime64[D]"), dropped[["trade_date", "n_symbols", "tot_turnover_eq", "reason"]]


def build_panel(panel_df: pd.DataFrame, cal_df: pd.DataFrame, memb_df: pd.DataFrame, p: Params = P) -> Panel:
    sessions, dropped = regular_calendar(cal_df, p)
    T = len(sessions)
    ents = sorted(panel_df["entity"].unique())
    eidx = {e: i for i, e in enumerate(ents)}
    E = len(ents)
    d = panel_df.copy()
    d["trade_date"] = pd.to_datetime(d["trade_date"]).values.astype("datetime64[D]")
    pos = np.searchsorted(sessions, d["trade_date"].to_numpy())
    ok = (pos < T) & (sessions[np.minimum(pos, T - 1)] == d["trade_date"].to_numpy())
    d, pos = d[ok], pos[ok]
    ei = d["entity"].map(eidx).to_numpy()
    arrs = {}
    for name, col in (("O", "open"), ("H", "high"), ("L", "low"), ("C", "close"), ("V", "volume"), ("TO", "turnover")):
        a = np.full((E, T), np.nan)
        a[ei, pos] = d[col].to_numpy(dtype=float)
        arrs[name] = a
    valid = np.ones((E, T), bool)
    for name in ("O", "H", "L", "C", "V"):
        a = arrs[name]
        valid &= np.isfinite(a) & (a > 0)
    for name in ("O", "H", "L", "C", "V", "TO"):
        arrs[name] = np.where(valid, arrs[name], np.nan)
    member = np.zeros((E, T), bool)
    m = memb_df.copy()
    m["rebalance_date"] = pd.to_datetime(m["rebalance_date"]).values.astype("datetime64[D]")
    rebs = np.sort(m["rebalance_date"].unique())
    # strictly-prior rebalance: the last r with r < t
    which = np.searchsorted(rebs, sessions, side="left") - 1
    for k, r in enumerate(rebs):
        cols = np.where(which == k)[0]
        if len(cols) == 0:
            continue
        ents_r = [eidx[e] for e in m.loc[m["rebalance_date"] == r, "entity"] if e in eidx]
        member[np.ix_(ents_r, cols)] = True
    return Panel(ents, sessions, arrs["O"], arrs["H"], arrs["L"], arrs["C"], arrs["V"], arrs["TO"], valid, member, dropped)


def load_panel(tag: str = "dev", p: Params = P) -> Panel:
    return build_panel(pd.read_parquet(C.OUT_DIR / f"panel_{tag}.parquet"),
                       pd.read_parquet(C.OUT_DIR / f"calendar_{tag}.parquet"),
                       pd.read_parquet(C.OUT_DIR / f"membership_{tag}.parquet"), p)


# ---------------------------------------------------------------- detection (no forward information)
def _df(a: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(a.T)                                  # T x E


def eligibility(pn: Panel, p: Params = P) -> np.ndarray:
    cnt = _df(pn.valid.astype(float)).rolling(p.lookback_required).sum().to_numpy().T
    return (cnt == p.lookback_required) & pn.member


def volume_state(pn: Panel, p: Params = P) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """median of the PRIOR vol_window volumes (today excluded), AV ratio, abnormal flag."""
    med = _df(pn.V).rolling(p.vol_window).median().shift(1).to_numpy().T
    with np.errstate(invalid="ignore", divide="ignore"):
        av = pn.V / med
    abn = np.isfinite(av) & (av >= p.av_threshold)
    return med, av, abn


def _prior_sum(flag: np.ndarray, w: int) -> np.ndarray:
    """count of True over the w sessions strictly before t (t-w .. t-1); NaN where the window is incomplete."""
    return _df(flag.astype(float)).rolling(w).sum().shift(1).to_numpy().T


def detect_masks(pn: Panel, n: int, p: Params = P) -> dict:
    C = _df(pn.C)
    mx = C.rolling(n).max().shift(1).to_numpy().T
    mn = C.rolling(n).min().shift(1).to_numpy().T
    with np.errstate(invalid="ignore"):
        up = pn.C > mx
        dn = pn.C < mn
    elig = eligibility(pn, p)
    med, av, abn = volume_state(pn, p)
    q = p.onset_quiet
    up_on = up & (_prior_sum(up, q) == 0)
    dn_on = dn & (_prior_sum(dn, q) == 0)
    quiet_vol = _prior_sum(abn, q) == 0
    cprev = C.shift(1).to_numpy().T
    d_evt = abn & ~up & ~dn & quiet_vol
    with np.errstate(invalid="ignore"):
        d_up = d_evt & (pn.C > cprev)
        d_dn = d_evt & (pn.C < cprev)
    return {"mx": mx, "mn": mn, "med": med, "av": av, "abn": abn, "elig": elig,
            "up": up, "dn": dn,
            "up_on": up_on & elig, "dn_on": dn_on & elig, "dup": d_up & elig, "ddn": d_dn & elig}


def detect_events(pn: Panel, p: Params = P) -> pd.DataFrame:
    """One row per (entity, session, N, kind). Signal-side information only (nothing after t)."""
    rows = []
    for n in p.range_n:
        m = detect_masks(pn, n, p)
        for kind in ("up", "dn", "dup", "ddn"):
            key = {"up": "up_on", "dn": "dn_on", "dup": "dup", "ddn": "ddn"}[kind]
            ei, ti = np.nonzero(m[key])
            ref = m["mx"] if kind in ("up", "dup") else m["mn"]
            rows.append(pd.DataFrame({
                "entity": np.asarray(pn.entities, dtype=object)[ei], "e": ei, "t": ti,
                "date": pn.sessions[ti], "N": n, "kind": kind,
                "close": pn.C[ei, ti], "prev_close": pn.C[ei, ti - 1],
                "ref_level": ref[ei, ti] if kind in ("up", "dn") else np.nan,
                "vol": pn.V[ei, ti], "med_vol": m["med"][ei, ti], "av": m["av"][ei, ti],
                "abn": m["abn"][ei, ti]}))
    ev = pd.concat(rows, ignore_index=True)
    ev["arm"] = np.where(ev["kind"].isin(["up", "dn"]), np.where(ev["abn"], "B", "C"), "D")
    return ev


# ---------------------------------------------------------------- outcomes (reads t+1..t+H)
def window_returns(pn: Panel, h: int, p: Params = P) -> dict:
    """Per (entity, t): entry open t+1, exit close t+h. Status: 0 normal, 1 terminal-truncated,
    2 dropped (missing entry, or a hole with the series resuming, or an unresolved hole near the data end),
    3 beyond the panel. Also the overnight gap O[t+1]/C[t]-1."""
    E, T = pn.valid.shape
    R = np.full((E, T), np.nan)
    st = np.full((E, T), ST_BEYOND, np.int8)
    exit_idx = np.full((E, T), -1, np.int64)
    gap = np.full((E, T), np.nan)
    ar = np.arange(T)
    for e in range(E):
        v = pn.valid[e]
        if not v.any():
            st[e, : T - h] = ST_DROPPED
            continue
        last_valid = int(np.nonzero(v)[0].max())
        # next_invalid[i] = smallest j >= i with ~v[j] (T if none)
        inv = np.where(~v, ar, T)
        next_invalid = np.minimum.accumulate(inv[::-1])[::-1]
        for t in range(T - h):
            st[e, t] = ST_DROPPED
            if not v[t]:
                continue
            k = next_invalid[t + 1]
            if k > t + h:                                          # every session t+1..t+h valid
                R[e, t] = pn.C[e, t + h] / pn.O[e, t + 1] - 1.0
                st[e, t], exit_idx[e, t] = ST_NORMAL, t + h
            elif k > t + 1 and last_valid < k and (T - 1 - k) >= p.terminal_guard:
                R[e, t] = pn.C[e, k - 1] / pn.O[e, t + 1] - 1.0    # series ended: accrue to the last close
                st[e, t], exit_idx[e, t] = ST_TERMINAL, k - 1
            if st[e, t] != ST_DROPPED:
                gap[e, t] = pn.O[e, t + 1] / pn.C[e, t] - 1.0
    return {"R": R, "status": st, "exit_idx": exit_idx, "gap": gap}


def benchmark(pn: Panel, wr: dict, p: Params = P) -> tuple[np.ndarray, np.ndarray]:
    """Equal-weight mean window return over ALL members at t with a resolved window."""
    ok = pn.member & np.isfinite(wr["R"]) & np.isin(wr["status"], (ST_NORMAL, ST_TERMINAL))
    cnt = ok.sum(axis=0)
    tot = np.where(ok, wr["R"], 0.0).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        rm = np.where(cnt >= p.min_bench_names, tot / cnt, np.nan)
    return rm, cnt


def attach_outcomes(pn: Panel, ev: pd.DataFrame, p: Params = P) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Adds, per horizon h: R_h, Rm_h, status_h, exit_date_h, f_h (signed market-excess, bp), raw_h (signed raw, bp)."""
    ev = ev.copy()
    sign = ev["kind"].map(KIND_SIGN).to_numpy()
    bench_rows = []
    ei, ti = ev["e"].to_numpy(), ev["t"].to_numpy()
    ev["gap"] = np.nan
    ev["entry_date"] = np.where(ti + 1 < len(pn.sessions), pn.sessions[np.minimum(ti + 1, len(pn.sessions) - 1)], np.datetime64("NaT"))
    for h in p.horizons:
        wr = window_returns(pn, h, p)
        rm, cnt = benchmark(pn, wr, p)
        r = wr["R"][ei, ti]
        ev[f"R{h}"] = r
        ev[f"Rm{h}"] = rm[ti]
        ev[f"status{h}"] = wr["status"][ei, ti]
        xi = wr["exit_idx"][ei, ti]
        ev[f"exit_t{h}"] = xi
        ev[f"exit_date{h}"] = np.where(xi >= 0, pn.sessions[np.maximum(xi, 0)], np.datetime64("NaT"))
        ev[f"f{h}"] = 1e4 * sign * (r - ev[f"Rm{h}"].to_numpy())
        ev[f"raw{h}"] = 1e4 * sign * r
        if h == p.horizons[0]:
            ev["gap"] = wr["gap"][ei, ti]
        bench_rows.append(pd.DataFrame({"t": np.arange(len(pn.sessions)), "date": pn.sessions, "H": h,
                                        "Rm": rm, "n_bench": cnt}))
    return ev, pd.concat(bench_rows, ignore_index=True)


def stage_bounds(sessions: np.ndarray, stage: str) -> tuple[int, int]:
    """First and last session index inside the stage window."""
    s0, s1 = (np.datetime64(x) for x in C.STAGES[stage])
    lo = int(np.searchsorted(sessions, s0, side="left"))
    hi = int(np.searchsorted(sessions, s1, side="right")) - 1
    return lo, hi


def in_stage(ev: pd.DataFrame, sessions: np.ndarray, stage: str, h: int) -> pd.Series:
    """Stage containment on session indices: formation t >= stage start AND the whole forward window
    (or its terminal truncation) ends inside the stage. Resolved windows only (normal/terminal, f present)."""
    lo, hi = stage_bounds(sessions, stage)
    ok = ev["status" + str(h)].isin([ST_NORMAL, ST_TERMINAL]) & ev["f" + str(h)].notna()
    return ok & (ev["t"] >= lo) & (ev["exit_t" + str(h)] <= hi)


def dropped_in_stage(ev: pd.DataFrame, sessions: np.ndarray, stage: str, h: int) -> pd.Series:
    """Tail-classified events whose window is dropped, and whose nominal window t+h lies inside the stage."""
    lo, hi = stage_bounds(sessions, stage)
    return (ev["status" + str(h)] == ST_DROPPED) & (ev["t"] >= lo) & (ev["t"] + h <= hi)
