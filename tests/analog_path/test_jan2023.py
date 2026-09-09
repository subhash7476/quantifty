from datetime import date, time

import numpy as np

from scripts.analog_path import config
from scripts.analog_path.data_layer import load_session, read_day


def _bar_close(d, stamp):
    for ts, o, h, lo, c, _s in read_day(d):
        if ts.time() == stamp:
            return c
    raise AssertionError(f"stamp {stamp} missing on {d}")


def test_transition_convention_vendor_before():
    s = load_session(date(2022, 12, 30))
    assert s.era == "vendor"
    assert s.bars[0][0].time() == time(9, 16)
    assert s.p_1230 == _bar_close(date(2022, 12, 30), time(12, 30))


def test_transition_convention_jan2023_start_labelled():
    # 2023-01-02..30 are physically start-labelled despite vendor provenance
    s = load_session(date(2023, 1, 2))
    assert s.era == "native"
    assert s.provenance_era == "vendor"
    assert s.bars[0][0].time() == time(9, 15)
    assert s.valid
    assert s.p_1230 == _bar_close(date(2023, 1, 2), time(12, 29))


def test_transition_convention_jan31_reverted_end_labelled():
    s = load_session(date(2023, 1, 31))
    assert s.era == "vendor"
    assert s.bars[0][0].time() == time(9, 16)
    assert s.p_1230 == _bar_close(date(2023, 1, 31), time(12, 30))


def test_transition_convention_native_from_march():
    s = load_session(date(2023, 3, 2))
    assert s.era == "native"
    assert s.provenance_era == "native"
    assert s.p_1230 == _bar_close(date(2023, 3, 2), time(12, 29))


def test_jan2023_sessions_are_eligible(tmp_path, monkeypatch):
    import csv
    import scripts.analog_path.eligibility as elig
    monkeypatch.setattr(elig, "DATA_DIR", tmp_path)
    monkeypatch.setattr(elig, "ELIGIBLE_PATH", tmp_path / "eligible_days.csv")
    monkeypatch.setattr(elig, "DEFECT_PATH", tmp_path / "defect_register.json")
    elig.build_eligible_days(date(2023, 1, 1), date(2023, 2, 2))
    eligible = []
    with open(tmp_path / "eligible_days.csv", newline="") as fh:
        for row in csv.DictReader(fh):
            d = date.fromisoformat(row["date"])
            if date(2023, 1, 1) <= d <= date(2023, 2, 2):
                eligible.append(d)
    assert date(2023, 1, 2) in eligible
    assert date(2023, 1, 30) in eligible
    assert date(2023, 1, 31) in eligible
    assert date(2023, 2, 1) not in eligible  # Feb 2023 hole (no file)


def test_labeling_rule_rejects_nonstandard_first_bars():
    assert config.labeling_of(time(9, 16)) == "vendor"
    assert config.labeling_of(time(9, 15)) == "native"
    assert config.labeling_of(time(9, 17)) is None
    assert config.labeling_of(time(11, 8)) is None
    s = load_session(date(2018, 7, 9))
    assert s is not None and not s.valid
    assert any("first_bar_stamp" in dd for dd in s.defects)
