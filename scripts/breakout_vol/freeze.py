"""BKV-1 freeze gate: protocol + every module on the computation path + the panel snapshot hashes.

Outcome measurement (run_stage.py) refuses to run unless every hash still matches. The HOLDOUT read is
one-shot (marker file), needs the VAL cells file, and needs an explicit operator authorisation record.
A defect is handled by an explicit, logged amend - never by a silent edit.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys

from scripts.breakout_vol import common as C

FREEZE_PATH = C.RESEARCH_DOCS / "breakout_volume_FREEZE.json"
HOLDOUT_MARKER = C.RESEARCH_DOCS / "breakout_volume_HOLDOUT_READ.json"
HOLDOUT_AUTH = C.RESEARCH_DOCS / "breakout_volume_HOLDOUT_AUTHORISATION.json"
FROZEN_MODULES = ("common.py", "prep.py", "engine.py", "stats.py", "analyze.py", "classify.py", "freeze.py",
                  "run_stage.py", "verify_independent.py")
EXTERNAL_MODULES = ("scripts/vwap_rev/stats.py", "core/execution/equity/delivery_fees.py")
LF, CRLF = bytes([10]), bytes([13, 10])


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes().replace(CRLF, LF)).hexdigest()      # autocrlf-immune


def current_hashes() -> dict:
    h = {"protocol": _sha(C.PROTOCOL_PATH),
         "protocol_md": _sha(C.RESEARCH_DOCS / "BREAKOUT_VOLUME_PROTOCOL.md")}
    for m in FROZEN_MODULES:
        h[f"scripts/breakout_vol/{m}"] = _sha(C.REPO / "scripts" / "breakout_vol" / m)
    for m in EXTERNAL_MODULES:
        h[m] = _sha(C.REPO / m)
    man = C.OUT_DIR / "manifest_dev.json"
    for name, meta in json.loads(man.read_text())["files"].items():
        h[f"snapshot_dev/{name}"] = meta["sha256"]
    return h


def _head() -> str:
    return subprocess.run(["git", "-C", str(C.REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def freeze(amend_reason: str | None = None) -> dict:
    proto = json.loads(C.PROTOCOL_PATH.read_text())
    if "DRAFT" in proto["version"]:
        raise SystemExit("protocol is not a final version")
    history = []
    if FREEZE_PATH.exists():
        if not amend_reason:
            raise SystemExit("already frozen; only an explicit logged amend rewrites a freeze")
        old = json.loads(FREEZE_PATH.read_text())
        history = old.get("history", []) + [
            {k: old[k] for k in ("version", "hashes", "git_head_at_freeze", "frozen_at")} | {"superseded_for": amend_reason}]
    rec = {"protocol_id": proto["protocol_id"], "version": proto["version"], "hashes": current_hashes(),
           "git_head_at_freeze": _head(), "frozen_at": dt.datetime.now().isoformat(timespec="seconds"),
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
    if HOLDOUT_MARKER.exists():
        raise RuntimeError(f"HOLDOUT already read ({HOLDOUT_MARKER.name}); one-shot")
    if not val_cells_csv.exists():
        raise RuntimeError("VAL cells file missing: VAL must be read before HOLDOUT")
    if not HOLDOUT_AUTH.exists():
        raise RuntimeError("no operator authorisation record: the HOLDOUT window is not spent without a go-ahead")
    if not (C.OUT_DIR / "manifest_full.json").exists():
        raise RuntimeError("manifest_full.json missing: build the full snapshot (prep --holdout) so the read is reconstructable")


def mark_holdout_read(note: str) -> None:
    man = json.loads((C.OUT_DIR / "manifest_full.json").read_text())
    HOLDOUT_MARKER.write_text(json.dumps({
        "read_at": dt.datetime.now().isoformat(timespec="seconds"),
        "protocol_sha": json.loads(FREEZE_PATH.read_text())["hashes"]["protocol"],
        "snapshot_full_files": {k: v["sha256"] for k, v in man["files"].items()},
        "snapshot_full_built_at": man["built_at"], "store_unfenced_max_date": man["store_unfenced_max_date"],
        "note": note}, indent=2))


if __name__ == "__main__":
    print(json.dumps(freeze(sys.argv[1] if len(sys.argv) > 1 else None), indent=2))
