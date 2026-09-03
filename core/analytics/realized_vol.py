"""Annualized realized volatility from 1m index candles.

Returns vol in PERCENTAGE POINTS (e.g. 14.5 = 14.5%) so it is directly comparable
to `OptionChainRow.iv`, which Upstox returns in the same percent units.

1-minute log returns are annualized by sqrt(trading_days * bars_per_session); only
intra-session returns are used, so overnight gaps never leak a fake vol spike into
the estimate.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Optional

import duckdb

from core.database.utils.symbol_utils import get_exchange_from_key

ROOT = Path(__file__).resolve().parents[2]
MARKET_DATA_DIR = ROOT / "data" / "market_data"
CANDLES_1M_DIR = MARKET_DATA_DIR / "nse" / "candles" / "1m"
TRADING_DAYS_PER_YEAR = 252
BARS_PER_SESSION = 375


def _candles_1m_dir(symbol: str) -> Path:
    """1m store dir for a symbol's exchange (nse for NSE_*, bse for BSE_INDEX|SENSEX)."""
    return MARKET_DATA_DIR / get_exchange_from_key(symbol) / "candles" / "1m"


def _load_sessions(symbol: str, lookback_files: int = 5) -> List[List[float]]:
    files = sorted(_candles_1m_dir(symbol).glob("*.duckdb"), reverse=True)
    sessions: List[List[float]] = []
    for f in files:
        if len(sessions) >= lookback_files:
            break
        try:
            con = duckdb.connect(str(f), read_only=True)
            rows = con.execute(
                "SELECT close FROM candles WHERE symbol = ? AND timeframe = '1m' "
                "ORDER BY timestamp ASC",
                [symbol],
            ).fetchall()
            con.close()
        except Exception:
            continue
        closes = [float(r[0]) for r in rows if r[0] is not None and float(r[0]) > 0]
        if len(closes) >= 2:
            sessions.append(closes)
    return sessions


def annualized_rv_pct(sessions: List[List[float]]) -> Optional[float]:
    log_ret: List[float] = []
    for closes in sessions:
        log_ret.extend(
            math.log(closes[i] / closes[i - 1])
            for i in range(1, len(closes))
            if closes[i] > 0 and closes[i - 1] > 0
        )
    if len(log_ret) < 2:
        return None
    mean = sum(log_ret) / len(log_ret)
    variance = sum((r - mean) ** 2 for r in log_ret) / (len(log_ret) - 1)
    per_bar = math.sqrt(max(variance, 0.0))
    annualized = per_bar * math.sqrt(TRADING_DAYS_PER_YEAR * BARS_PER_SESSION)
    return annualized * 100.0


def session_realized_vol_pct(symbol: str, lookback_files: int = 5) -> Optional[float]:
    """Realized vol over the most recent `lookback_files` sessions of 1m bars."""
    return annualized_rv_pct(_load_sessions(symbol, lookback_files))
