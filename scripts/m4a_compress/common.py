"""M4a-CE - shared constants, paths and the frozen Params.

Protocol: docs/reports/research/m4a_compress_protocol.json (mirrored by Params; a test asserts equality).
The panel is the certified, hashed BKV-1 dev snapshot (panel_dev / calendar_dev / membership_dev.parquet,
formation data <= 2022-12-30). It is read, never rebuilt and never written by this package.
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
SNAPSHOT_DIR = DATA_ROOT / "research" / "breakout_volume"          # the BKV-1 dev snapshot (read-only input)
OUT_DIR = DATA_ROOT / "research" / "m4a_compress"
RESEARCH_DOCS = REPO / "docs" / "reports" / "research"
PROTOCOL_PATH = RESEARCH_DOCS / "m4a_compress_protocol.json"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# No HOLDOUT stage exists in this package: the snapshot ends 2022-12-30 and no later price is ever loaded.
STAGES = {
    "TRAIN": (dt.date(2012, 1, 2), dt.date(2017, 12, 29)),
    "VAL": (dt.date(2018, 1, 1), dt.date(2022, 12, 30)),
}
DEV_CUTOFF = dt.date(2022, 12, 30)
BKV_PANEL_SHA256 = "46de7d4d6b3c1fc2d0a4954ccc3455787c6f86af2d30054ae549764a2a3b2ef4"    # BKV-1 freeze record


@dataclass(frozen=True)
class Params:
    fast: int = 10                          # ATR_fast / RV_fast window (sessions, ending at t)
    slow: int = 60                          # ATR_slow / RV_slow window
    pct_window: int = 252                   # trailing-percentile window of the fast/slow ratio, ending at t, t included
    q_low: float = 0.20                     # compression: percentile <= 0.20
    q_high: float = 0.80                    # persistence comparator (high state): percentile >= 0.80
    quiet: int = 20                         # = max(H, 20) for both horizons: no same-state flag in the prior 20 sessions
    base_window: int = 252                  # trailing baseline for the outcome normaliser, ending at t
    horizons: tuple = (5, 20)
    min_normal_names: int = 100             # a date enters the vs-normal contrast only if its normal cohort has >= 100 names
    alpha: float = 0.05                     # one-sided, Holm over the 4 primary cells
    n_boot: int = 10_000
    boot_seed: int = 20260930
    n_perm: int = 2_000
    perm_seed: int = 20260931


P = Params()
