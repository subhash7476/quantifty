"""VWAP-XREV freeze gate. Outcome measurement refuses to run unless the protocol
file's sha256 matches the recorded freeze (written before any forward return exists)."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess

from scripts.vwap_rev import common as C

FREEZE_PATH = C.REPO / "docs" / "reports" / "research" / "vwap_extreme_reversion_FREEZE.json"


def protocol_sha() -> str:
    raw = C.PROTOCOL_PATH.read_bytes().replace(b"
", b"
")     # immune to autocrlf
    return hashlib.sha256(raw).hexdigest()


def freeze() -> dict:
    proto = json.loads(C.PROTOCOL_PATH.read_text())
    if "DRAFT" in proto["version"]:
        raise SystemExit("protocol is still DRAFT")
    if FREEZE_PATH.exists():
        raise SystemExit("already frozen; a freeze is never rewritten")
    head = subprocess.run(["git", "-C", str(C.REPO), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    rec = {"protocol_id": proto["protocol_id"], "version": proto["version"],
           "sha256": protocol_sha(), "git_head_at_freeze": head,
           "frozen_at": dt.datetime.now().isoformat(timespec="seconds"),
           "outcomes_computed_before_freeze": False}
    FREEZE_PATH.write_text(json.dumps(rec, indent=2))
    return rec


def assert_frozen() -> dict:
    if not FREEZE_PATH.exists():
        raise RuntimeError("protocol not frozen: outcome measurement is forbidden")
    rec = json.loads(FREEZE_PATH.read_text())
    if rec["sha256"] != protocol_sha():
        raise RuntimeError("protocol changed after freeze")
    return rec


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2))
