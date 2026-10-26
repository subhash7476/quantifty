"""M4a-CE freeze gate: protocol + every module on the computation path + the imported BKV-1/VWAP modules + the panel
snapshot hashes + the outcome-free diagnostics.

Outcome measurement (run_stage.py) refuses to run unless every hash still matches. The freeze itself refuses to be
written once any results directory exists. A defect is handled by an explicit, logged amend - never a silent edit.
There is no HOLDOUT guard because there is no HOLDOUT: the dev snapshot ends 2022-12-30.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys

from scripts.m4a_compress import common as C

FREEZE_PATH = C.RESEARCH_DOCS / "m4a_compress_FREEZE.json"
FROZEN_MODULES = ("common.py", "panel.py", "state.py", "cohorts.py", "outcome.py", "analyze.py", "classify.py",
                  "stats.py", "diagnostics.py", "freeze.py", "run_stage.py", "verify_independent.py")
EXTERNAL_MODULES = ("scripts/breakout_vol/common.py", "scripts/breakout_vol/engine.py", "scripts/breakout_vol/stats.py",
                    "scripts/breakout_vol/verify_independent.py", "scripts/vwap_rev/stats.py")
INPUT_DOCS = ("docs/reports/external/M4A_COMPRESSION_EXPANSION_DESIGN_INVENTORY.md",)
LF, CRLF = bytes([10]), bytes([13, 10])


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes().replace(CRLF, LF)).hexdigest()      # autocrlf-immune


def _raw_sha(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def current_hashes() -> dict:
    h = {"protocol": _sha(C.PROTOCOL_PATH), "protocol_md": _sha(C.RESEARCH_DOCS / "M4A_COMPRESSION_EXPANSION_PROTOCOL.md")}
    for m in FROZEN_MODULES:
        h[f"scripts/m4a_compress/{m}"] = _sha(C.REPO / "scripts" / "m4a_compress" / m)
    for m in EXTERNAL_MODULES + INPUT_DOCS:
        h[m] = _sha(C.REPO / m)
    for name in ("panel", "calendar", "membership"):
        h[f"snapshot_dev/{name}"] = _raw_sha(C.SNAPSHOT_DIR / f"{name}_dev.parquet")
    diag = C.OUT_DIR / "diagnostics_outcome_free.json"
    if diag.exists():
        h["diagnostics_outcome_free"] = _sha(diag)
    return h


def _git(*args) -> str:
    return subprocess.run(["git", "-C", str(C.REPO), *args], capture_output=True, text=True).stdout.strip()


def freeze(amend_reason: str | None = None) -> dict:
    proto = json.loads(C.PROTOCOL_PATH.read_text())
    if "DRAFT" in proto["version"]:
        raise SystemExit("protocol is not a final version")
    if (C.OUT_DIR / "results").exists() and not amend_reason:
        raise SystemExit("a results directory exists: the freeze must precede every outcome")
    if not (C.OUT_DIR / "diagnostics_outcome_free.json").exists():
        raise SystemExit("run the outcome-free diagnostics before the freeze")
    history = []
    if FREEZE_PATH.exists():
        if not amend_reason:
            raise SystemExit("already frozen; only an explicit logged amend rewrites a freeze")
        old = json.loads(FREEZE_PATH.read_text())
        history = old.get("history", []) + [
            {k: old[k] for k in ("version", "hashes", "git_head_at_freeze", "frozen_at")} | {"superseded_for": amend_reason}]
    rec = {"protocol_id": proto["protocol_id"], "version": proto["version"], "hashes": current_hashes(),
           "git_head_at_freeze": _git("rev-parse", "HEAD"), "git_dirty_paths_at_freeze": _git("status", "--porcelain").splitlines(),
           "frozen_at": dt.datetime.now().isoformat(timespec="seconds"),
           "outcomes_computed_before_freeze": (C.OUT_DIR / "results").exists(), "history": history}
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
    if now["snapshot_dev/panel"] != C.BKV_PANEL_SHA256:
        raise RuntimeError("panel snapshot is not the BKV-1 dev panel")
    return rec


if __name__ == "__main__":
    print(json.dumps(freeze(sys.argv[1] if len(sys.argv) > 1 else None), indent=2))
