"""A — shared frozen-parameter machinery for the gate runners (TRAIN/HOLDOUT).

Parity contract: `returns_of` + `session_arrays` must reproduce the sealed
TRAIN run's numbers exactly (w45 mean net bp = 1.271397244236667 on the TRAIN
fence, seed 42). Every constant below is frozen by A_PHASE0_PRE_REGISTRATION.md
(D1-D6); edit nothing here without a freeze-breaking decision.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np

from core.execution.futures.futures_fees import breakeven_round_trip_bps

ROOT = Path(__file__).resolve().parents[2]
CANDLE_DIR_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"

NF = "NSE_INDEX|Nifty 50"
VENDOR_LAST = date(2023, 1, 31)   # vendor era boundary (certified)
CAS_EFFECTIVE = date(2026, 8, 3)  # CAS era boundary

PREREG_SHA = "ccb32090704a33962fe13cda5b66de9026378b01"
SEED = 42
NULL_ITERS = 1000
NW_LAG = 5
CANONICAL = 20_000_000.0
BASIS_MEAN_BP = 0.4               # D5: carry drift over the hold

# measured entry-drift p90 by era and cell (A_COST_SUBSTRATE_MEASUREMENTS.md)
SLIP_BP = {
    "w30": {"vendor": 0.78, "native": 0.70},
    "w45": {"vendor": 0.73, "native": 0.66},
}
ENTRY_BAR = {"w30": 31, "w45": 46}
WINDOW_END = {"w30": 30, "w45": 45}
CELLS = ("w30", "w45")


def era_of(d: date) -> str:
    if d >= CAS_EFFECTIVE:
        return "cas"
    if d > VENDOR_LAST:
        return "native"
    return "vendor"


def fees_bp(trade_date: date) -> float:
    return breakeven_round_trip_bps(price=1000.0, quantity=20_000,
                                    trade_date=trade_date)


def session_arrays(d: date):
    """Frozen construct inputs for one session, or None if invalid."""
    path = CANDLE_DIR_1M / f"{d.isoformat()}.duckdb"
    if not path.exists():
        return None
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute(
            "SELECT timestamp, open, close FROM candles "
            "WHERE symbol = ? ORDER BY timestamp", [NF]).fetchall()
    finally:
        con.close()
    if not rows:
        return None
    if rows[0][0].date().isoformat() != d.isoformat():
        return None                      # session-validity: date-stamped first bar
    opens = [float(r[1]) for r in rows]
    closes = [float(r[2]) for r in rows]
    exit_i = next((i for i, r in enumerate(rows)
                   if r[0].time().hour == 15 and r[0].time().minute == 14),
                  None)
    if exit_i is None or exit_i < 1 or closes[exit_i] <= 0:
        return None                      # 15:14 exit bar present
    out = {"exit_close": closes[exit_i], "valid": {}, "feature": {},
           "entry_open": {}}
    for cell in CELLS:
        wend, ebar = WINDOW_END[cell], ENTRY_BAR[cell]
        if len(rows) <= ebar or closes[wend] <= 0 or opens[ebar] <= 0 \
                or opens[0] <= 0:
            out["valid"][cell] = False
            continue
        out["valid"][cell] = True
        out["feature"][cell] = (closes[wend] - opens[0]) / opens[0]
        out["entry_open"][cell] = opens[ebar]
    if not any(out["valid"].values()):
        return None
    return out


def returns_of(cell: str, features: np.ndarray, entry: np.ndarray,
               exit_close: np.ndarray, fee: np.ndarray,
               trade_dates) -> np.ndarray:
    """Net per-trade returns (bp) at the frozen cost application."""
    gross = (exit_close - entry) / entry * 1e4
    sign = np.sign(features)
    eras = np.asarray([era_of(d) for d in trade_dates])
    slip = np.zeros(len(features))
    for e in ("vendor", "native", "cas"):
        m = eras == e
        lane = SLIP_BP[cell][e if e in ("vendor", "native") else "native"]
        slip[m] = lane * 2.0
    return sign * (gross - BASIS_MEAN_BP) - np.asarray(fee) - slip


def nw_t(series: np.ndarray, lag: int = NW_LAG) -> float:
    n = len(series)
    if n < 3:
        return 0.0
    m = float(np.mean(series))
    e = series - m
    nw_var = float(np.mean(e * e))
    for k in range(1, min(lag, n - 1) + 1):
        ck = float(np.mean(e[k:] * e[:-k]))
        nw_var += 2.0 * (1.0 - k / (lag + 1.0)) * ck
    if nw_var <= 0:
        return 0.0
    return m / np.sqrt(nw_var / n)


def ac1(series: np.ndarray) -> float:
    n = len(series)
    if n < 4:
        return 0.0
    m = float(np.mean(series))
    num = float(np.sum((series[1:] - m) * (series[:-1] - m)))
    den = float(np.sum((series - m) ** 2))
    return num / den if den > 0 else 0.0


def load_cell(fence_lo: date, fence_hi: date, cell: str) -> dict:
    """Load a cell's frozen inputs over a fence; refuses out-of-fence dates."""
    dates = []
    d = fence_lo
    while d <= fence_hi:
        if (CANDLE_DIR_1M / f"{d.isoformat()}.duckdb").exists():
            dates.append(d)
        d += timedelta(days=1)
    feat, entry, exitc, fee, out_dates = [], [], [], [], []
    invalid = 0
    for dd in dates:
        sa = session_arrays(dd)
        if sa is None:
            invalid += 1
            continue
        if not sa["valid"][cell]:
            continue
        feat.append(sa["feature"][cell])
        entry.append(sa["entry_open"][cell])
        exitc.append(sa["exit_close"])
        fee.append(fees_bp(dd))
        out_dates.append(dd)
    return {"features": np.asarray(feat), "entry": np.asarray(entry),
            "exit": np.asarray(exitc), "fee": np.asarray(fee),
            "dates": out_dates, "invalid": invalid}
