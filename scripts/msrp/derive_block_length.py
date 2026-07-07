"""Derive the moving-block-bootstrap block length L from DEV-window RV autocorrelation.

Dossier §1.1: L is pinned from dev-window RV autocorrelation, NEVER held-out. This
script reads only 1m Nifty-50 files dated within the dev window (2023-01-02 ..
2025-12-31); it never opens a 2026 file, so the held-out seal is untouched.

Rule: L = smallest lag k>=1 with |ACF(k)| < 1.96/sqrt(n). Fallback (no such lag):
L = floor(n/20), recorded as an override.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import duckdb
import numpy as np
import pandas as pd

from core.msi.msrp.validation_scoring import compute_daily_rv


def _acf(vals: np.ndarray, nlags: int) -> np.ndarray:
    """Sample autocorrelation function: ACF(k) = auto-cov(k) / auto-cov(0)."""
    n = len(vals)
    demeaned = vals - np.mean(vals)
    denom = np.sum(demeaned ** 2)
    if denom == 0:
        return np.ones(nlags + 1)
    acf_vals = np.empty(nlags + 1)
    acf_vals[0] = 1.0
    for k in range(1, nlags + 1):
        acf_vals[k] = np.sum(demeaned[k:] * demeaned[:n - k]) / denom
    return acf_vals

NIFTY_50 = "NSE_INDEX|Nifty 50"
CANDLES_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
DEV_START = pd.Timestamp("2023-01-02").date()
DEV_END = pd.Timestamp("2025-12-31").date()


def load_dev_closes():
    closes_by_day = {}
    for f in sorted(CANDLES_1M.glob("*.duckdb")):
        try:
            d = pd.Timestamp(f.stem).date()
        except ValueError:
            continue
        if not (DEV_START <= d <= DEV_END):
            continue
        con = duckdb.connect(str(f), read_only=True)
        try:
            rows = con.execute(
                "SELECT timestamp, close FROM candles WHERE symbol = ? ORDER BY timestamp",
                [NIFTY_50],
            ).fetchall()
        finally:
            con.close()
        if not rows:
            continue
        day = pd.Timestamp(rows[0][0]).normalize()
        closes_by_day[day] = np.array([float(r[1]) for r in rows], dtype=float)
    return closes_by_day


def main() -> int:
    closes_by_day = load_dev_closes()
    rv = compute_daily_rv(closes_by_day)
    rv = rv[(rv.index >= pd.Timestamp(DEV_START)) & (rv.index <= pd.Timestamp(DEV_END))]
    vals = rv.to_numpy(dtype=float)
    n = len(vals)
    band = 1.96 / np.sqrt(n)
    nlags = min(40, n // 2)
    a = _acf(vals, nlags=nlags)

    L, override = None, False
    for k in range(1, nlags + 1):
        if abs(a[k]) < band:
            L = k
            break
    if L is None:
        L = n // 20
        override = True

    print(f"n_dev={n}  band=1.96/sqrt(n)={band:.6f}  nlags={nlags}")
    print("lag,acf,|acf|>=band")
    for k in range(1, nlags + 1):
        print(f"{k},{a[k]:.6f},{abs(a[k]) >= band}")
    print(f"PINNED L={L}  override={override}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
