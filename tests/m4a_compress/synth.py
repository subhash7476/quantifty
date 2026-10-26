"""Synthetic snapshot frames (same schema as the BKV-1 dev snapshot) for the M4a tests."""
import numpy as np
import pandas as pd


def make_frames(E=12, T=140, seed=0, cut=None, holes=None, start="2015-01-05"):
    """cut: {entity_idx: last_session_index}; holes: {entity_idx: [session indices with no row]}."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=T)
    rows = []
    for e in range(E):
        c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, T)))
        o = c * np.exp(rng.normal(0, 0.003, T))
        v = np.exp(rng.normal(10, 0.3, T))
        wid = np.exp(rng.normal(0, 0.4, T)) * 0.006                   # varying daily range width
        for t in range(T):
            if cut and e in cut and t > cut[e]:
                break
            if holes and e in holes and t in holes[e]:
                continue
            rows.append((f"E{e:02d}", dates[t], f"S{e}", "EQ", o[t], max(o[t], c[t]) * (1 + wid[t]),
                         min(o[t], c[t]) * (1 - wid[t]), c[t], v[t], v[t] * c[t], 1))
    panel = pd.DataFrame(rows, columns=["entity", "trade_date", "symbol", "series", "open", "high", "low", "close",
                                        "volume", "turnover", "n_listings"])
    cal = pd.DataFrame({"trade_date": dates, "n_symbols": 300, "tot_turnover_eq": 1e9})
    memb = pd.DataFrame({"rebalance_date": [dates[0] - pd.Timedelta(days=1)] * E,
                         "entity": [f"E{e:02d}" for e in range(E)], "symbol": [f"S{e}" for e in range(E)],
                         "rank": range(1, E + 1)})
    return panel, cal, memb, dates
