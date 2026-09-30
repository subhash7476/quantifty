import dataclasses
import json

import pytest

from scripts.breakout_vol import common as C
from scripts.breakout_vol import freeze as F


def test_params_mirror_the_protocol_json_exactly():
    proto = json.loads(C.PROTOCOL_PATH.read_text())
    mine = {k: (list(v) if isinstance(v, tuple) else v) for k, v in dataclasses.asdict(C.P).items()}
    assert proto["params"] == mine
    assert {k: [a.isoformat(), b.isoformat()] for k, (a, b) in C.STAGES.items()} == proto["stages"]


def test_every_frozen_module_exists_and_is_hashed():
    h = F.current_hashes()
    for m in F.FROZEN_MODULES:
        assert f"scripts/breakout_vol/{m}" in h
    assert "protocol" in h and "protocol_md" in h and "core/execution/equity/delivery_fees.py" in h


def test_holdout_needs_val_cells_operator_authorisation_and_is_one_shot(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "HOLDOUT_MARKER", tmp_path / "read.json")
    monkeypatch.setattr(F, "HOLDOUT_AUTH", tmp_path / "auth.json")
    val = tmp_path / "cells_VAL.csv"
    with pytest.raises(RuntimeError, match="VAL cells"):
        F.holdout_guard(val)
    val.write_text("x")
    with pytest.raises(RuntimeError, match="authorisation"):
        F.holdout_guard(val)
    (tmp_path / "auth.json").write_text("{}")
    monkeypatch.setattr(C, "OUT_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="manifest_full"):
        F.holdout_guard(val)
    (tmp_path / "manifest_full.json").write_text("{}")
    F.holdout_guard(val)                                     # now allowed
    (tmp_path / "read.json").write_text("{}")
    with pytest.raises(RuntimeError, match="one-shot"):
        F.holdout_guard(val)


def test_assert_frozen_detects_a_changed_file(tmp_path, monkeypatch):
    rec = tmp_path / "freeze.json"
    monkeypatch.setattr(F, "FREEZE_PATH", rec)
    with pytest.raises(RuntimeError, match="not frozen"):
        F.assert_frozen()
    hashes = F.current_hashes()
    hashes["scripts/breakout_vol/engine.py"] = "0" * 64
    rec.write_text(json.dumps({"hashes": hashes}))
    with pytest.raises(RuntimeError, match="engine.py"):
        F.assert_frozen()
