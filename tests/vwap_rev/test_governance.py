import dataclasses
import json

import numpy as np
import pytest

from scripts.vwap_rev import common as C
from scripts.vwap_rev import engine as E
from scripts.vwap_rev import freeze as F


def test_params_defaults_equal_protocol_json():
    mirror = json.loads(C.PROTOCOL_PATH.read_text())["params_mirror"]
    p = E.Params()
    for f in dataclasses.fields(E.Params):
        v = getattr(p, f.name)
        m = mirror[f.name]
        assert (list(v) if isinstance(v, tuple) else v) == m, f.name
    assert json.loads(C.PROTOCOL_PATH.read_text())["extreme_threshold"]["q_frozen"] == p.q


def test_prior_counts_finite_sigma_not_rows():
    st = E._State()
    st.hist["A"] = [(t, np.nan if t % 2 else 0.001, 0.02, 1e6) for t in range(20)]   # 10 finite
    sig, _, _ = E._prior(st, "A", 20, E.Params())
    assert np.isnan(sig)
    st.hist["A"] = [(t, 0.001, 0.02, 1e6) for t in range(20)]
    assert E._prior(st, "A", 20, E.Params())[0] == pytest.approx(0.001)


def _flat_session():
    n = C.N_SLOTS
    s = {k: np.full((1, n), 100.0, np.float32) for k in ("O", "H", "L", "C")}
    s["V"] = np.full((1, n), 500.0, np.float32)
    s["symbols"] = np.array(["NSE_EQ|X"])
    return s


def test_last_valid_exit_uses_earlier_close_and_strict_gives_nan():
    s = _flat_session()
    s["C"][0, 110] = 101.0
    for a in ("O", "H", "L", "C", "V"):
        s[a][0, 105:108] = np.nan            # bars 105..107 invalid; exit slot for H=10 is 110 (valid)
    for a in ("O", "H", "L", "C", "V"):
        s[a][0, 110] = np.nan                # now the exit slot itself is invalid
    s["C"][0, 109] = 100.5
    vw, ok = E.session_vwap(s, "typical")
    strict = E._outcomes(s, 0, 100, +1, vw, ok, E.Params())
    assert np.isnan(strict["R_h10"])
    lv = E._outcomes(s, 0, 100, +1, vw, ok, E.Params(exit_fill="last_valid"))
    assert lv["R_h10"] == pytest.approx(-(100.5 / 100.0 - 1) * 1e4)


def test_freeze_detects_any_hashed_file_change(tmp_path, monkeypatch):
    rec = {"hashes": F.current_hashes()}
    f = tmp_path / "freeze.json"
    f.write_text(json.dumps(rec))
    monkeypatch.setattr(F, "FREEZE_PATH", f)
    assert F.assert_frozen() is not None
    rec["hashes"]["scripts/vwap_rev/engine.py"] = "0" * 64
    f.write_text(json.dumps(rec))
    with pytest.raises(RuntimeError, match="changed after freeze"):
        F.assert_frozen()


def test_outcomes_refused_without_freeze(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "FREEZE_PATH", tmp_path / "missing.json")
    with pytest.raises(RuntimeError, match="not frozen"):
        E.run_sessions(E.Params(), sessions=[], membership={}, with_outcomes=True)


def test_holdout_guard_requires_val_and_is_one_shot(tmp_path, monkeypatch):
    marker = tmp_path / "marker.json"
    monkeypatch.setattr(F, "HOLDOUT_MARKER", marker)
    val = tmp_path / "val.csv"
    with pytest.raises(RuntimeError, match="VAL must be read"):
        F.holdout_guard(val)
    val.write_text("x")
    F.holdout_guard(val)                      # allowed
    marker.write_text("{}")
    with pytest.raises(RuntimeError, match="one-shot"):
        F.holdout_guard(val)
