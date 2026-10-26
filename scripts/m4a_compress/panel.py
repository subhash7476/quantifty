"""M4a-CE panel loader: the certified BKV-1 dev snapshot, verified by hash and fence before use."""
from __future__ import annotations

import hashlib

import pandas as pd

from scripts.breakout_vol.common import P as BKV_P
from scripts.breakout_vol.engine import Panel, build_panel
from scripts.m4a_compress import common as C


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_panel() -> Panel:
    d = C.SNAPSHOT_DIR
    got = sha256_file(d / "panel_dev.parquet")
    if got != C.BKV_PANEL_SHA256:
        raise RuntimeError(f"panel snapshot hash {got[:12]} is not the frozen BKV-1 dev panel {C.BKV_PANEL_SHA256[:12]}")
    panel = pd.read_parquet(d / "panel_dev.parquet")
    if panel["trade_date"].max() > pd.Timestamp(C.DEV_CUTOFF):
        raise RuntimeError(f"fence violated: panel holds prices after {C.DEV_CUTOFF}")
    return build_panel(panel, pd.read_parquet(d / "calendar_dev.parquet"), pd.read_parquet(d / "membership_dev.parquet"), BKV_P)
