"""VWAP-XREV regime labels (POST-PRIMARY robustness only). Every label for session t uses
the prior close (t-1) and earlier. Nifty 50 and India VIX from the certified 1d store."""
from __future__ import annotations

import datetime as dt

import duckdb
import numpy as np
import pandas as pd

from scripts.vwap_rev import common as C

D1_DIR = C.DATA_ROOT / "market_data" / "nse" / "candles" / "1d"


def _closes(lo: dt.date, hi: dt.date) -> pd.DataFrame:
    rows = []
    for p in sorted(D1_DIR.glob("*.duckdb")):
        d = dt.date.fromisoformat(p.stem)
        if d < lo or d > hi:
            continue
        con = duckdb.connect(str(p), read_only=True)
        try:
            r = con.execute("select symbol, close from candles where symbol in "
                            "('NSE_INDEX|Nifty 50','NSE_INDEX|India VIX')").fetchall()
        finally:
            con.close()
        m = dict(r)
        rows.append({"date": d, "nifty": m.get("NSE_INDEX|Nifty 50"), "vix": m.get("NSE_INDEX|India VIX")})
    return pd.DataFrame(rows).dropna().set_index("date")


def labels(sessions: list[dt.date]) -> pd.DataFrame:
    cl = _closes(dt.date(2022, 6, 1), sessions[-1])
    out = []
    dates = list(cl.index)
    for t in sessions:
        prior = [d for d in dates if d < t]
        if len(prior) < 61:
            out.append({"date": t, "nifty_ret60": np.nan, "vix_prior": np.nan, "vix_terc": np.nan})
            continue
        ret60 = cl.loc[prior[-1], "nifty"] / cl.loc[prior[-61], "nifty"] - 1
        vix_hist = cl.loc[prior, "vix"].to_numpy()
        terc = np.nan
        if len(vix_hist) >= 60:
            lo, hi = np.quantile(vix_hist, [1 / 3, 2 / 3])
            v = vix_hist[-1]
            terc = 0 if v <= lo else (1 if v <= hi else 2)
        out.append({"date": t, "nifty_ret60": ret60, "vix_prior": vix_hist[-1], "vix_terc": terc})
    df = pd.DataFrame(out)
    df["mkt_regime"] = np.where(df["nifty_ret60"] >= 0.05, "bull",
                                np.where(df["nifty_ret60"] <= -0.05, "bear", "choppy"))
    df.loc[df["nifty_ret60"].isna(), "mkt_regime"] = None
    return df
