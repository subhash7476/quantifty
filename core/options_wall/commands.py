"""Options-Wall command queue — file-based close requests (Flask → poller).

Flask is a read-only reader of the results DB; the poller is its sole writer, so
a manual exit cannot be written by Flask directly. Instead Flask drops a tiny
JSON request file here and the poller (the only writer) picks it up next cycle,
closes the trade at current marks, and clears the file. File-based rather than a
shared command DB to sidestep the cross-process DuckDB append locks on this
platform (see repo pitfalls — wall-store append locks 3–8 s).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List

# Anchored to the repo root (not CWD) so Flask and the poller — which may run
# from different working directories — always agree on the queue location.
ROOT = Path(__file__).resolve().parents[2]
CLOSE_DIR = ROOT / "data" / "options" / "close_requests"


def request_close(trade_id: int, index: str, close_dir: Path = CLOSE_DIR) -> None:
    """Queue a manual close for one trade (atomic write via temp + os.replace)."""
    close_dir.mkdir(parents=True, exist_ok=True)
    payload = {"trade_id": int(trade_id), "index": index,
               "requested_at": time.time()}
    tmp = close_dir / f".{int(trade_id)}.tmp"
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(str(tmp), str(close_dir / f"{int(trade_id)}.json"))


def pending_closes(close_dir: Path = CLOSE_DIR) -> List[Dict]:
    """All queued close requests (best-effort; skips a file mid-write)."""
    if not close_dir.exists():
        return []
    out: List[Dict] = []
    for f in close_dir.glob("*.json"):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out


def clear_close(trade_id: int, close_dir: Path = CLOSE_DIR) -> None:
    """Remove a processed (or stale) close request."""
    try:
        (close_dir / f"{int(trade_id)}.json").unlink()
    except OSError:
        pass
