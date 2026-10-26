import dataclasses
import json
import re

import pytest

from scripts.m4a_compress import common as C
from scripts.m4a_compress import freeze as F
from scripts.m4a_compress import run_stage as R


def test_params_and_stages_mirror_the_protocol_json_exactly():
    proto = json.loads(C.PROTOCOL_PATH.read_text())
    mine = {k: (list(v) if isinstance(v, tuple) else v) for k, v in dataclasses.asdict(C.P).items()}
    assert proto["params"] == mine
    assert {k: [a.isoformat(), b.isoformat()] for k, (a, b) in C.STAGES.items()} == proto["stages"]
    assert proto["primary_family"]["size"] == 4


def test_there_is_no_holdout_stage_and_the_dev_fence_is_2022_12_30():
    assert set(C.STAGES) == {"TRAIN", "VAL"}
    assert C.DEV_CUTOFF.isoformat() == "2022-12-30" and max(b for _, b in C.STAGES.values()) <= C.DEV_CUTOFF
    with pytest.raises(ValueError, match="no HOLDOUT"):
        R.execute("HOLDOUT")


def _imports(module: str) -> set:
    src = (C.REPO / "scripts" / "m4a_compress" / f"{module}.py").read_text()
    return set(re.findall(r"^\s*(?:from|import)\s+scripts\.m4a_compress(?:\s+import\s+([\w, ]+)|\.(\w+))", src, flags=re.M))


def test_only_the_stage_runner_imports_the_outcome_module():
    for m in ("state", "cohorts", "diagnostics", "panel", "analyze", "classify", "stats", "common"):
        src = (C.REPO / "scripts" / "m4a_compress" / f"{m}.py").read_text()
        assert not re.search(r"m4a_compress(\.| import .*\b)outcome\b", src), f"{m} must not import outcome"
    assert re.search(r"import outcome as O", (C.REPO / "scripts" / "m4a_compress" / "run_stage.py").read_text())


def test_every_frozen_module_exists_and_is_hashed():
    h = F.current_hashes()
    for m in F.FROZEN_MODULES:
        assert f"scripts/m4a_compress/{m}" in h
    for m in F.EXTERNAL_MODULES + F.INPUT_DOCS:
        assert m in h
    assert "protocol" in h and "protocol_md" in h and "snapshot_dev/panel" in h


def test_snapshot_is_the_bkv1_frozen_panel():
    assert F.current_hashes()["snapshot_dev/panel"] == C.BKV_PANEL_SHA256


def test_assert_frozen_detects_a_changed_file_and_a_missing_freeze(tmp_path, monkeypatch):
    rec = tmp_path / "freeze.json"
    monkeypatch.setattr(F, "FREEZE_PATH", rec)
    with pytest.raises(RuntimeError, match="not frozen"):
        F.assert_frozen()
    hashes = F.current_hashes()
    hashes["scripts/m4a_compress/outcome.py"] = "0" * 64
    rec.write_text(json.dumps({"hashes": hashes}))
    with pytest.raises(RuntimeError, match="outcome.py"):
        F.assert_frozen()


def test_freeze_is_refused_once_any_result_exists(tmp_path, monkeypatch):
    (tmp_path / "results").mkdir()
    (tmp_path / "diagnostics_outcome_free.json").write_text("{}")
    monkeypatch.setattr(C, "OUT_DIR", tmp_path)
    monkeypatch.setattr(F, "FREEZE_PATH", tmp_path / "freeze.json")
    with pytest.raises(SystemExit, match="precede every outcome"):
        F.freeze()
