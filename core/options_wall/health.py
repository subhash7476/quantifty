"""Step-level health for the options-wall poller.

The poller runs six independent steps per cycle and swallows each one's
exceptions so a single failure cannot stop the others. This module decides
whether a swallowed exception is routine — a lock the next cycle clears — or a
defect that will never clear on its own, and tracks consecutive failures so
alerting is edge-triggered rather than fired every cycle.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[2]
WALL_HEARTBEAT_PATH = ROOT / "data" / "options" / "wall_poller_heartbeat.json"

TRANSIENT = "transient"
STRUCTURAL = "structural"

DEFAULT_ALERT_AT = 10
ALERT_AT = {"close_request": 1}

_LOCK_MARKER = "used by another process"


def classify(exc: BaseException) -> str:
    if isinstance(exc, duckdb.ConnectionException):
        return TRANSIENT
    if isinstance(exc, duckdb.IOException) and _LOCK_MARKER in str(exc):
        return TRANSIENT
    if isinstance(exc, requests.RequestException):
        return TRANSIENT
    return STRUCTURAL
