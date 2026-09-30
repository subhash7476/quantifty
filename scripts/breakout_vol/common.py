"""BKV-1 — shared constants, paths and the frozen Params.

Protocol: docs/reports/research/breakout_volume_protocol.json (mirrored by Params; a test asserts equality).
The worktree carries no `data/`, so every store path is absolute under DATA_ROOT (the live checkout).
"""
from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("F:/Nifty/data")
EQUITY_DB = DATA_ROOT / "market_data" / "equity_bhavcopy.duckdb"
OUT_DIR = DATA_ROOT / "research" / "breakout_volume"
RESEARCH_DOCS = REPO / "docs" / "reports" / "research"
PROTOCOL_PATH = RESEARCH_DOCS / "breakout_volume_protocol.json"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

STAGES = {
    "TRAIN": (dt.date(2012, 1, 2), dt.date(2017, 12, 29)),
    "VAL": (dt.date(2018, 1, 1), dt.date(2022, 12, 30)),
    "HOLDOUT": (dt.date(2023, 1, 2), dt.date(2026, 9, 29)),
}
DEV_CUTOFF = dt.date(2022, 12, 30)          # the dev snapshot holds nothing after this date
PANEL_START = dt.date(2010, 1, 4)


@dataclass(frozen=True)
class Params:
    range_n: tuple = (20, 63)                # closing-range lengths (sessions)
    horizons: tuple = (5, 20)                # holding period (sessions), entry open t+1 -> close t+H
    onset_quiet: int = 20                    # no same-side breakout flag in the prior 20 sessions
    vol_window: int = 20                     # median volume over the prior 20 sessions, today excluded
    av_threshold: float = 2.0                # abnormal volume: V_t >= 2 x median(V_{t-20..t-1})
    lookback_required: int = 84              # valid rows on every session t-83..t (= 63 + 20 + 1)
    min_bench_names: int = 100               # benchmark set size floor per (date, H)
    short_session_ratio: float = 0.40        # regular session iff total EQ turnover >= 0.40 x centred 21-session median
    short_session_window: int = 21
    calendar_min_symbols: int = 200          # trading_calendar.n_symbols floor (PSB convention)
    terminal_guard: int = 60                 # series-end judged only if >= 60 sessions of data remain after it
    universe_size: int = 200
    alpha: float = 0.05                      # one-sided, Holm over the primary family
    notional: float = 500_000.0              # Rs per name for the fee computation
    base_kappa_bp: float = 5.0               # slippage bp per side, base scenario
    kappas_bp: tuple = (0.0, 2.5, 5.0, 10.0)
    n_boot: int = 10_000
    boot_seed: int = 20260930
    n_perm: int = 5_000
    perm_seed: int = 20260931


P = Params()
