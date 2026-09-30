"""VWAP-XREV freeze gate.

The freeze record hashes the protocol, every module on the primary computation path and the
membership file. Outcome measurement refuses to run unless every hash still matches, and the
HOLDOUT read is one-shot (marker file), the pattern used by the repo's run_sealed.py scripts.
A discovered defect is handled by an explicit, logged `amend`, never by a silent edit.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys

from scripts.vwap_rev import common as C

RESEARCH_DOCS = C.REPO / "docs" / "reports" / "research"
FREEZE_PATH = RESEARCH_DOCS / "vwap_extreme_reversion_FREEZE.json"
HOLDOUT_MARKER = RESEARCH_DOCS / "vwap_extreme_reversion_HOLDOUT_READ.json"
MEMBERSHIP_JSON = C.OUT_DIR / "fno_membership.json"

FROZEN_MODULES = ("engine.py", "analyze.py", "stats.py", "universe.py", "common.py",
                  "classify.py", "freeze.py", "run_primary.py", "run_classify.py")
LF, CRLF = bytes([10]), bytes([13, 10])


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes().replace(CRLF, LF)).hexdigest()    # autocrlf-immune


def protocol_sha() -> str:
    return _sha(C.PROTOCOL_PATH)


def current_hashes() -> dict:
    h = {"protocol": protocol_sha(), "membership_json": _sha(MEMBERSHIP_JSON)}
    for m in FROZEN_MODULES:
        h[f"scripts/vwap_rev/{m}"] = _sha(C.REPO / "scripts" / "vwap_rev" / m)
    return h


def _head() -> str:
    return subprocess.run(["git", "-C", str(C.REPO), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


def freeze(amend_reason: str | None = None) -> dict:
    proto = json.loads(C.PROTOCOL_PATH.read_text())
    if "DRAFT" in proto["version"] or "RC" in proto["version"]:
        raise SystemExit("protocol is not a final version")
    history = []
    if FREEZE_PATH.exists():
        if not amend_reason:
            raise SystemExit("already frozen; a freeze is only rewritten by an explicit logged amend")
        old = json.loads(FREEZE_PATH.read_text())
        history = old.get("history", []) + [
            {k: old[k] for k in ("version", "hashes", "git_head_at_freeze", "frozen_at")}
            | {"superseded_for": amend_reason}]
    rec = {"protocol_id": proto["protocol_id"], "version": proto["version"],
           "hashes": current_hashes(), "git_head_at_freeze": _head(),
           "frozen_at": dt.datetime.now().isoformat(timespec="seconds"),
           "outcomes_computed_before_freeze": False, "history": history}
    FREEZE_PATH.write_text(json.dumps(rec, indent=2))
    return rec


def assert_frozen() -> dict:
    if not FREEZE_PATH.exists():
        raise RuntimeError("protocol not frozen: outcome measurement is forbidden")
    rec = json.loads(FREEZE_PATH.read_text())
    now = current_hashes()
    bad = [k for k, v in rec["hashes"].items() if now.get(k) != v]
    if bad:
        raise RuntimeError(f"frozen files changed after freeze: {bad}")
    return rec


def holdout_guard(val_cells_csv) -> None:
    """HOLDOUT may be read only once, and only after VAL results exist."""
    if HOLDOUT_MARKER.exists():
        raise RuntimeError(f"HOLDOUT already read ({HOLDOUT_MARKER.name}); one-shot")
    if not val_cells_csv.exists():
        raise RuntimeError("VAL cells file missing: VAL must be read before HOLDOUT")


def mark_holdout_read(note: str) -> None:
    HOLDOUT_MARKER.write_text(json.dumps({
        "read_at": dt.datetime.now().isoformat(timespec="seconds"),
        "protocol_sha": json.loads(FREEZE_PATH.read_text())["hashes"]["protocol"],
        "note": note}, indent=2))


if __name__ == "__main__":
    reason = sys.argv[1] if len(sys.argv) > 1 else None
    print(json.dumps(freeze(reason), indent=2))
