"""Step-level health for the options-wall poller.

The poller runs six independent steps per cycle and swallows each one's
exceptions so a single failure cannot stop the others. This module decides
whether a swallowed exception is routine — a lock the next cycle clears — or a
defect that will never clear on its own, and tracks consecutive failures so
alerting is edge-triggered rather than fired every cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

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


@dataclass(frozen=True)
class Verdict:
    ok: bool
    kind: Optional[str]
    level: str
    alert: bool
    record: dict


class StepHealth:
    """Per-(underlying, step) failure state, edge-triggered alert decisions."""

    def __init__(self, alert_at: Optional[Dict[str, int]] = None):
        self._alert_at = dict(ALERT_AT if alert_at is None else alert_at)
        self._state: Dict[Tuple[str, str], dict] = {}

    def record(self, step: str, underlying: str,
               exc: Optional[BaseException] = None,
               now: Optional[datetime] = None) -> Verdict:
        key = (underlying, step)
        if exc is None:
            record = {"ok": True}
            self._state[key] = record
            return Verdict(True, None, "info", False, record)

        now = now or datetime.now()
        kind = classify(exc)
        prev = self._state.get(key)
        failing = prev is not None and not prev["ok"]
        consecutive = prev["consecutive"] + 1 if failing else 1
        since = prev["since"] if failing else now.isoformat(timespec="seconds")
        record = {
            "ok": False,
            "kind": kind,
            "error_type": type(exc).__name__,
            "error_msg": str(exc)[:200],
            "consecutive": consecutive,
            "since": since,
        }
        self._state[key] = record
        threshold = 1 if kind == STRUCTURAL else self._alert_at.get(step, DEFAULT_ALERT_AT)
        return Verdict(False, kind, "error" if kind == STRUCTURAL else "warning",
                       consecutive == threshold, record)

    def snapshot(self) -> Dict[str, Dict[str, dict]]:
        out: Dict[str, Dict[str, dict]] = {}
        for (underlying, step), record in self._state.items():
            out.setdefault(underlying, {})[step] = record
        return out

    def any_failing(self) -> bool:
        return any(not record["ok"] for record in self._state.values())
