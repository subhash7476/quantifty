import json
from datetime import date
from pathlib import Path

import numpy as np

from scripts.analog_path import config
from scripts.analog_path.data_layer import load_session
from scripts.analog_path.eligibility import build_eligible_days
from scripts.analog_path.stats import summary


def _valid_sessions(dates):
    out = []
    for d in dates:
        s = load_session(d)
        if s is not None and s.valid:
            out.append(s)
    return out


def test_reproducible_session_state():
    a = load_session(date(2024, 6, 3))
    b = load_session(date(2024, 6, 3))
    assert np.array_equal(a.grid_prices, b.grid_prices)
    assert np.array_equal(a.path_state, b.path_state)
    assert np.array_equal(a.interval_state, b.interval_state)
    assert a.outcomes == b.outcomes
    assert a.mfe == b.mfe and a.mae == b.mae


def test_reproducible_summary():
    sessions = _valid_sessions([date(2012, 6, 4), date(2012, 6, 5),
                                date(2012, 6, 6), date(2012, 6, 7),
                                date(2012, 6, 8), date(2012, 6, 11),
                                date(2012, 6, 12), date(2012, 6, 13)])
    assert len(sessions) >= 6
    x = np.asarray([s.open_to_1230 for s in sessions])
    a, b = summary(x), summary(x)
    assert a == b
    assert np.isfinite(a["ci95_lo"]) and np.isfinite(a["ci95_hi"])


def test_mini_eligibility_build_excludes_multiday_file(tmp_path, monkeypatch):
    import scripts.analog_path.eligibility as elig
    monkeypatch.setattr(elig, "DATA_DIR", tmp_path)
    monkeypatch.setattr(elig, "ELIGIBLE_PATH", tmp_path / "eligible_days.csv")
    monkeypatch.setattr(elig, "DEFECT_PATH", tmp_path / "defect_register.json")
    out = build_eligible_days(date(2026, 2, 20), date(2026, 2, 28))
    assert out["eligible"] >= 0
    reg = json.loads((tmp_path / "defect_register.json").read_text())
    defect_dates = {e["date"] for e in reg["sessions_with_defects"]}
    assert "2026-02-25" in defect_dates
    assert date(2026, 2, 25) not in load_eligible_dates_static(tmp_path)


def load_eligible_dates_static(tmp_path: Path):
    import csv
    out = []
    with open(tmp_path / "eligible_days.csv", newline="") as fh:
        for row in csv.DictReader(fh):
            out.append(date.fromisoformat(row["date"]))
    return out
