"""VWAP-XREV engine: session VWAP, causal displacement z, rolling extreme threshold,
event detection (outcome-free) and forward-outcome measurement (freeze-gated).

Timeline conventions (1m bars are START-labelled; slot 0 = the 09:15 bar):
  decision bar k  -> observed at its close, i.e. clock 09:15 + (k+1) min; D = k+1
                     is the elapsed minutes since 09:15.
  entry           -> OPEN of bar k+delay  (delay = 1 primary: first tradable price)
  exit at H       -> CLOSE of bar (entry_bar - 1 + H)  (H bars held from the entry open)
Nothing at or after the entry bar enters any quantity used to decide an event.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd

from scripts.vwap_rev import common as C

D_MIN, D_MAX = 60, 295                      # decision window: 10:15 .. 14:10 elapsed
K_LO, K_HI = D_MIN - 1, D_MAX - 1           # decision bar slots 59 .. 294
N_BUCKETS = 16                              # 15-minute buckets over D in [60, 295]


def bucket_of(k: np.ndarray) -> np.ndarray:
    return (np.asarray(k) + 1 - D_MIN) // 15


@dataclass(frozen=True)
class Params:
    q: float = 0.99
    sigma_lookback: int = 20
    sigma_min_sessions: int = 15
    sigma_min_pairs: int = 200
    pool_sessions: int = 60
    first_event_session_index: int = 80
    min_valid_frac: float = 0.90
    horizons: tuple = (5, 10, 15, 30, 60)
    vwap_mode: str = "typical"            # typical | close
    norm_mode: str = "rms1m"              # rms1m | range | raw_bp
    entry_delay: int = 1
    dedup: str = "first_per_side"         # first_per_side | all
    universe: str = "fno"                 # fno | all


STAGES = (
    ("TRAIN", dt.date(2023, 1, 2), dt.date(2024, 6, 30)),
    ("VAL", dt.date(2024, 7, 1), dt.date(2025, 3, 31)),
    ("HOLDOUT", dt.date(2025, 4, 1), dt.date(2026, 9, 29)),
)


def stage_of(d: dt.date) -> str:
    for name, lo, hi in STAGES:
        if lo <= d <= hi:
            return name
    raise ValueError(d)


# ----------------------------------------------------------------------------
# per-session pure features
# ----------------------------------------------------------------------------
def session_vwap(s: dict, vwap_mode: str) -> tuple[np.ndarray, np.ndarray]:
    """Cumulative session VWAP through each bar (NaN until first volume) and the
    valid-bar mask. Invalid slots carry zero weight; VWAP is never imputed."""
    Cc = s["C"].astype(np.float64)
    ok = ~np.isnan(Cc)
    V = np.where(ok, s["V"].astype(np.float64), 0.0)
    if vwap_mode == "typical":
        price = (s["H"].astype(np.float64) + s["L"].astype(np.float64) + Cc) / 3.0
    elif vwap_mode == "close":
        price = Cc
    else:
        raise ValueError(vwap_mode)
    num = np.cumsum(np.where(ok, price * V, 0.0), axis=1)
    den = np.cumsum(V, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        vwap = np.where(den > 0, num / den, np.nan)
    return vwap, ok


def day_stats(s: dict, min_pairs: int) -> dict:
    """Per-symbol same-session scalars used ONLY by later sessions (prior state)."""
    Cc = s["C"].astype(np.float64)
    ok = ~np.isnan(Cc)
    both = ok[:, 1:] & ok[:, :-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(both, np.log(Cc[:, 1:] / Cc[:, :-1]), 0.0)
    cnt = both.sum(1)
    sig = np.sqrt((r ** 2).sum(1) / np.maximum(cnt, 1))
    sig[cnt < min_pairs] = np.nan
    H = np.where(ok, s["H"].astype(np.float64), np.nan)
    L = np.where(ok, s["L"].astype(np.float64), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        rng = (np.nanmax(H, 1) - np.nanmin(L, 1)) / np.nanmean(Cc, 1)
    rng[cnt < min_pairs] = np.nan
    dv = np.nansum(np.where(ok, Cc * s["V"].astype(np.float64), 0.0), axis=1)
    return {"sigma": sig, "range": rng, "dv": dv}


def displacement_z(s: dict, vwap: np.ndarray, ok: np.ndarray, scale_prior: np.ndarray,
                   norm_mode: str) -> np.ndarray:
    """z over decision slots K_LO-1 .. K_HI (one extra leading slot for z_prev).
    scale_prior: (nsym,) prior-session scale (NaN if unavailable)."""
    ks = np.arange(K_LO - 1, K_HI + 1)
    Cc = s["C"].astype(np.float64)[:, ks]
    V = vwap[:, ks]
    disp = (Cc - V) / V
    D = (ks + 1).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        if norm_mode == "rms1m":
            z = disp / (scale_prior[:, None] * np.sqrt(D)[None, :])
        elif norm_mode == "range":
            z = disp / (scale_prior[:, None] * np.sqrt(D / C.N_SLOTS)[None, :])
        elif norm_mode == "raw_bp":
            z = disp * 1e4
        else:
            raise ValueError(norm_mode)
    z = np.where(ok[:, ks], z, np.nan)
    return z


# ----------------------------------------------------------------------------
# streaming runner
# ----------------------------------------------------------------------------
@dataclass
class _State:
    hist: dict = field(default_factory=dict)     # sym -> list[(session_idx, sigma, range, dv)]
    pool: list = field(default_factory=list)     # per session: list[N_BUCKETS] of 1-D float32 |z|


def _prior(state: _State, sym: str, t_idx: int, p: Params):
    rows = [r for r in state.hist.get(sym, ()) if t_idx - p.sigma_lookback <= r[0] < t_idx]
    if len(rows) < p.sigma_min_sessions:
        return np.nan, np.nan, np.nan
    a = np.array([[r[1], r[2], r[3]] for r in rows], float)
    with np.errstate(invalid="ignore"):
        return (float(np.nanmean(a[:, 0])), float(np.nanmean(a[:, 1])),
                float(np.nanmean(a[:, 2])))


def _scale_vec(state, syms, t_idx, p):
    sig = np.full(len(syms), np.nan)
    rng = np.full(len(syms), np.nan)
    adv = np.full(len(syms), np.nan)
    for i, sym in enumerate(syms):
        sig[i], rng[i], adv[i] = _prior(state, str(sym), t_idx, p)
    return sig, rng, adv


def thresholds(pool: list, t_idx: int, p: Params) -> np.ndarray | None:
    """c[b] = q-quantile of |z| pooled over the prior `pool_sessions` sessions, bucket b.
    Uses ONLY sessions strictly before t. None if the pool is too thin."""
    prior = [x for x in pool[max(0, t_idx - p.pool_sessions):t_idx] if x is not None]
    if len(prior) < p.pool_sessions * 2 // 3:
        return None
    c = np.full(N_BUCKETS, np.nan)
    for b in range(N_BUCKETS):
        vals = np.concatenate([x[b] for x in prior])
        if len(vals) >= 5000:
            c[b] = np.quantile(vals, p.q)
    return c


def run_sessions(p: Params, sessions=None, membership=None, with_outcomes: bool = False,
                 stages: tuple = ("TRAIN", "VAL", "HOLDOUT"), progress: bool = False):
    """Iterate all regular sessions in order (warm-up state always built from the
    beginning). Returns (events DataFrame, per-session DataFrame)."""
    from scripts.vwap_rev import universe as U

    if with_outcomes:
        from scripts.vwap_rev import freeze as F
        F.assert_frozen()
    sessions = sessions or C.regular_sessions()
    membership = membership if membership is not None else U.load()
    state = _State()
    ev_rows, sess_rows = [], []
    for t_idx, (d, path) in enumerate(sessions):
        s = C.cached_session(d, path)
        syms = [str(x) for x in s["symbols"]]
        if p.universe == "fno":
            member = np.array([x in membership.get(d.isoformat(), ()) for x in syms])
        else:
            member = np.ones(len(syms), bool)
        vwap, ok = session_vwap(s, p.vwap_mode)
        sig_p, rng_p, adv_p = _scale_vec(state, syms, t_idx, p)
        scale = {"rms1m": sig_p, "range": rng_p, "raw_bp": np.ones(len(syms))}[p.norm_mode]
        z = displacement_z(s, vwap, ok, scale, p.norm_mode)         # (n, 237): slot K_LO-1 .. K_HI
        cum_ok = np.cumsum(ok, axis=1)
        ks = np.arange(K_LO - 1, K_HI + 1)
        vfrac = cum_ok[:, ks] / (ks + 1)[None, :]
        elig = (member[:, None] & np.isfinite(z) & (vfrac >= p.min_valid_frac)
                & np.isfinite(scale)[:, None])
        zw = z[:, 1:]                                                # decision slots K_LO..K_HI
        eligw = elig[:, 1:]
        az = np.abs(np.where(eligw, zw, np.nan))
        # pool for FUTURE sessions: this session's eligible |z| by bucket (no outcome data)
        bk = bucket_of(np.arange(K_LO, K_HI + 1))
        state.pool.append([az[:, bk == b][np.isfinite(az[:, bk == b])].astype(np.float32)
                           for b in range(N_BUCKETS)])
        thr = thresholds(state.pool, t_idx, p)                       # uses pool[..t_idx-1]
        st = stage_of(d) if t_idx >= p.first_event_session_index else "WARMUP"
        n_elig_names = int(eligw.any(axis=1).sum())
        sess_rows.append({"date": d, "idx": t_idx, "stage": st, "n_syms": len(syms),
                          "n_member": int(member.sum()), "n_elig_names": n_elig_names,
                          "thr_ok": thr is not None,
                          **({f"c{b}": thr[b] for b in range(N_BUCKETS)} if thr is not None else {})})
        if thr is not None and st in stages:
            ev_rows.extend(_detect(s, syms, d, t_idx, st, zw, z[:, 0], eligw, thr, vwap,
                                   ok, scale, adv_p, p, with_outcomes, member))
        dstat = day_stats(s, p.sigma_min_pairs)
        for i, sym in enumerate(syms):
            h = state.hist.setdefault(sym, [])
            h.append((t_idx, dstat["sigma"][i], dstat["range"][i], dstat["dv"][i]))
            if len(h) > 30:
                del h[:len(h) - 30]
        if progress and t_idx % 100 == 0:
            print(f"  session {t_idx} {d} events so far {len(ev_rows)}", flush=True)
    return pd.DataFrame(ev_rows), pd.DataFrame(sess_rows)


def _detect(s, syms, d, t_idx, stage, zw, z_prev0, eligw, thr, vwap, ok, scale, adv_p, p,
            with_outcomes, member) -> list[dict]:
    bk = bucket_of(np.arange(K_LO, K_HI + 1))
    cthr = thr[bk][None, :]
    usable = eligw & np.isfinite(cthr)
    up = usable & (zw >= cthr)
    dn = usable & (zw <= -cthr)
    rows = []
    adv_rank = pd.Series(np.where(member & np.isfinite(adv_p), adv_p, np.nan)).rank(pct=True).to_numpy()
    scale_rank = pd.Series(np.where(member & np.isfinite(scale), scale, np.nan)).rank(pct=True).to_numpy()
    for side, hit in ((+1, up), (-1, dn)):
        if p.dedup == "first_per_side":
            has = hit.any(axis=1)
            first = np.argmax(hit, axis=1)
            picks = [(i, first[i]) for i in np.nonzero(has)[0]]
        else:
            ii, jj = np.nonzero(hit)
            picks = list(zip(ii, jj))
        for i, j in picks:
            k = K_LO + int(j)
            zprev = zw[i, j - 1] if j > 0 else z_prev0[i]
            row = {"date": d, "idx": t_idx, "stage": stage, "symbol": syms[i], "side": side,
                   "k": k, "D": k + 1, "bucket": int(bk[j]), "z": float(zw[i, j]),
                   "c": float(cthr[0, j]), "z_prev": float(zprev) if np.isfinite(zprev) else np.nan,
                   "vwap_k": float(vwap[i, k]), "close_k": float(s["C"][i, k]),
                   "scale": float(scale[i]), "adv_rank": float(adv_rank[i]),
                   "scale_rank": float(scale_rank[i])}
            if with_outcomes:
                row.update(_outcomes(s, i, k, side, vwap, ok, p))
            rows.append(row)
    if with_outcomes and rows:
        bench = market_benchmark(s, member & np.isfinite(scale) if p.norm_mode != "raw_bp" else member,
                                 sorted({r["k"] for r in rows}), p.horizons, p.entry_delay)
        for r in rows:
            sgn = -r["side"]
            for H in p.horizons:
                m = bench[(r["k"], H)]
                r[f"R_ex_h{H}"] = r[f"R_h{H}"] - sgn * m * 1e4 if np.isfinite(r[f"R_h{H}"]) and np.isfinite(m) else np.nan
    return rows


def _outcomes(s, i, k, side, vwap, ok, p) -> dict:
    """Forward measures for one event. Strict: entry/exit bars must be valid."""
    e = k + p.entry_delay
    out = {}
    O = s["O"][i]
    Hh, Ll, Cc = s["H"][i], s["L"][i], s["C"][i]
    Vk = vwap[i, k]
    entry_ok = e < C.N_SLOTS and np.isfinite(O[e])
    for H in p.horizons:
        x = e - 1 + H
        key = f"h{H}"
        if not entry_ok or x >= C.N_SLOTS or not np.isfinite(Cc[x]):
            for f in ("R", "MFE", "MAE", "dstat", "dmov", "R_ex"):
                out[f"{f}_{key}"] = np.nan
            continue
        E = float(O[e])
        X = float(Cc[x])
        seg_h = Hh[e:x + 1]
        seg_l = Ll[e:x + 1]
        mx = float(np.nanmax(seg_h)) if np.isfinite(seg_h).any() else np.nan
        mn = float(np.nanmin(seg_l)) if np.isfinite(seg_l).any() else np.nan
        # reversion direction: side=+1 (up-displacement) -> short (-1); side=-1 -> long (+1)
        sgn = -side
        R = sgn * (X / E - 1.0) * 1e4
        if sgn > 0:
            mfe, mae = (mx / E - 1.0) * 1e4, (mn / E - 1.0) * 1e4
        else:
            mfe, mae = (1.0 - mn / E) * 1e4, -(mx / E - 1.0) * 1e4
        Vx = vwap[i, x]
        out[f"R_{key}"] = R
        out[f"MFE_{key}"] = mfe
        out[f"MAE_{key}"] = mae
        out[f"dstat_{key}"] = (abs(X - Vk) - abs(E - Vk)) / Vk * 1e4
        out[f"dmov_{key}"] = (abs(X - Vx) / Vx - abs(E - Vk) / Vk) * 1e4 if np.isfinite(Vx) else np.nan
        out[f"R_ex_{key}"] = np.nan          # filled by market_benchmark()
    out["E"] = float(O[e]) if entry_ok else np.nan
    return out


def market_benchmark(s, member, k_e_list, horizons, entry_delay) -> dict:
    """Equal-weight universe forward return over the identical (entry, exit) window."""
    out = {}
    O, Cc = s["O"].astype(np.float64), s["C"].astype(np.float64)
    for k in k_e_list:
        e = k + entry_delay
        for H in horizons:
            x = e - 1 + H
            if e >= C.N_SLOTS or x >= C.N_SLOTS:
                out[(k, H)] = np.nan
                continue
            r = Cc[member, x] / O[member, e] - 1.0
            out[(k, H)] = float(np.nanmean(r)) if np.isfinite(r).any() else np.nan
    return out
