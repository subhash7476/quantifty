"""E008 window identity (AUDIT_2026-09-25 R3).

The 18 trips to 2026-09-25 span three exit/sizing regimes. The window restarts
at WINDOW_START on one frozen execution identity; a session counts only if its
recorder stamped that identity.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.nifty_shield_paper import identity  # noqa: E402


def test_execution_hash_ignores_line_endings(tmp_path):
    (tmp_path / "a.py").write_bytes(b"x = 1\r\ny = 2\r\n")
    crlf = identity.execution_hash(tmp_path, files=["a.py"])
    (tmp_path / "a.py").write_bytes(b"x = 1\ny = 2\n")
    assert identity.execution_hash(tmp_path, files=["a.py"]) == crlf


def test_execution_hash_moves_with_any_execution_file(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("y = 1\n", encoding="utf-8")
    before = identity.execution_hash(tmp_path, files=["a.py", "b.py"])
    (tmp_path / "b.py").write_text("y = 2\n", encoding="utf-8")
    assert identity.execution_hash(tmp_path, files=["a.py", "b.py"]) != before


def test_the_tree_matches_the_frozen_identity():
    """Fails when execution code changes without a re-freeze. A change means a
    new identity: re-pin FROZEN_EXECUTION_HASH and WINDOW_START together and
    ledger it — never re-pin just to make this pass."""
    assert identity.execution_hash(ROOT) == identity.FROZEN_EXECUTION_HASH


def test_window_counts_only_on_or_after_start_with_the_frozen_stamp(tmp_path, monkeypatch):
    import json
    from datetime import date
    from scripts.nifty_shield_paper.assemble_report import load_window_evidence
    monkeypatch.setattr(identity, "WINDOW_START", date(2026, 9, 28))
    for d, stamp in (("2026-09-25", identity.FROZEN_EXECUTION_HASH),
                     ("2026-09-28", "an-older-build"),
                     ("2026-09-29", identity.FROZEN_EXECUTION_HASH)):
        pkg = tmp_path / "sessions" / d
        pkg.mkdir(parents=True)
        (pkg / "session_summary.json").write_text(json.dumps({"replay_inputs": True}))
        (pkg / "telemetry.json").write_text(json.dumps({"clean": True}))
        (pkg / "meta.json").write_text(json.dumps({"execution_hash": stamp}))
    reasons = {d["session"]: d["exclusion_reasons"]
               for d in load_window_evidence(tmp_path)["session_details"]}
    assert "before-window-start" in reasons["2026-09-25"]
    assert "off-identity" in reasons["2026-09-28"]
    assert reasons["2026-09-29"] == ["no-closed-structure"]   # stamp accepted


def test_the_recorder_stamps_the_identity_it_started_with(tmp_path, monkeypatch):
    """The live checkout can change while a session runs; the stamp must be
    the code the process loaded, taken at start, not at finalize."""
    from scripts.nifty_shield_paper import recorder as rec_mod
    monkeypatch.setattr(rec_mod, "execution_hash", lambda root: "at-start")
    r = rec_mod.SessionRecorder(str(tmp_path / "pkg"))
    monkeypatch.setattr(rec_mod, "execution_hash", lambda root: "at-finalize")
    assert r._execution_hash == "at-start"
