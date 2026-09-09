"""Frozen Phase-1A configuration for the intraday analog-path research.

Single source of truth: `config.json` in this directory. This module loads,
validates, and exposes it. The SHA-256 seal cited by
INTRADAY_ANALOG_PATH_PROTOCOL.md is computed over the *canonical* JSON form
(`json.dumps(CONFIG, sort_keys=True)`), not the raw file bytes, so it is
stable across line-ending normalization and whitespace churn — the seal
protects the semantic content. Edit nothing here or in the JSON without a
freeze-breaking decision.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, time
from pathlib import Path

_CFG_PATH = Path(__file__).resolve().with_name("config.json")

with open(_CFG_PATH, "r", encoding="utf-8") as fh:
    CONFIG = json.load(fh)

_CANONICAL = json.dumps(CONFIG, sort_keys=True, separators=(",", ":"))
CONFIG_SHA256 = hashlib.sha256(_CANONICAL.encode("utf-8")).hexdigest()

INSTRUMENT = CONFIG["instrument"]
CUTOFF = time(12, 30)

GRID_TIMES = [time.fromisoformat(t) for t in CONFIG["grid_times"]]
assert len(GRID_TIMES) == 14
assert GRID_TIMES[0] == time(9, 15) and GRID_TIMES[-1] == time(12, 30)

VENDOR_LAST = date.fromisoformat(CONFIG["era_boundaries"]["vendor_last"])
NATIVE_FROM = date.fromisoformat(CONFIG["era_boundaries"]["native_from"])
CAS_FROM = date.fromisoformat(CONFIG["era_boundaries"]["cas_from"])

FENCE_TRAIN = (date.fromisoformat(CONFIG["fences"]["train"][0]),
               date.fromisoformat(CONFIG["fences"]["train"][1]))
FENCE_HOLDOUT = (date.fromisoformat(CONFIG["fences"]["holdout"][0]),
                 date.fromisoformat(CONFIG["fences"]["holdout"][1]))
SEALED_START = date.fromisoformat(CONFIG["fences"]["sealed_start"])

HORIZONS = tuple(CONFIG["horizons"].keys())
HORIZON_LABELS = dict(CONFIG["horizons"])
HORIZON_TIMES = {k: (None if v == "close" else time.fromisoformat(v))
                 for k, v in CONFIG["horizons"].items()}

BIN_EDGES_PCT = list(CONFIG["return_bins_edges_pct"])

K_VALUES = tuple(CONFIG["k_values"])
DISTANCE = CONFIG["distance"]
REPRESENTATIONS = tuple(CONFIG["representations"])

MIN_BARS = CONFIG["eligibility"]["min_bars"]
MIN_MORNING_BARS = CONFIG["eligibility"]["min_morning_bars"]
FIRST_BAR_STANDARD = {k: time.fromisoformat(v)
                      for k, v in CONFIG["eligibility"]["first_bar_standard"].items()}

NULL_ITERS = CONFIG["nulls"]["iterations"]
NULL_SEED = CONFIG["nulls"]["seed"]

NW_LAG = CONFIG["stats"]["nw_lag"]
BOOT_BLOCKS = CONFIG["stats"]["bootstrap_blocks_days"]
BOOT_ITERS = CONFIG["stats"]["bootstrap_iterations"]
BOOT_SEED = CONFIG["stats"]["bootstrap_seed"]
QUANTILES = tuple(CONFIG["stats"]["quantiles"])

TOLERANCE_PCT = CONFIG["return_matching_tolerance_pct"]


def era_of(d: date) -> str:
    if d >= CAS_FROM:
        return "cas"
    if d > VENDOR_LAST:
        return "native"
    return "vendor"


def close_stamp_of(era: str) -> time:
    return time(15, 30) if era == "vendor" else time(15, 29)


def fence_of(d: date) -> str:
    if d >= SEALED_START:
        return "sealed"
    if d >= FENCE_HOLDOUT[0]:
        return "holdout"
    return "train"


class FenceError(RuntimeError):
    pass


def require_fence(d: date, fence: str) -> None:
    if fence == "sealed":
        raise FenceError(
            "SEALED is locked: no outcome-level read permitted before the "
            "methodology freeze (protocol §21). Structural eligibility "
            "inspection is the only permitted access.")
    if fence_of(d) != fence:
        raise FenceError(f"{d} belongs to fence {fence_of(d)}, not {fence}")
