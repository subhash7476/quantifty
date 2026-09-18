import pytest

from scripts.jev_nms_1.fence import Fence, FenceViolation
from scripts.jev_nms_1.l1 import planned_requests


def _fence(tmp_path):
    for d in ("2024-06-03", "2025-06-02", "2026-01-05"):
        (tmp_path / f"{d}.duckdb").write_bytes(b"")
    elig = {"sessions": {"d_fit": [{"date": "2024-06-03", "eligible": True},
                                   {"date": "2024-06-04", "eligible": False}],
                         "d_eval": [{"date": "2025-06-02", "eligible": True}],
                         "h_exposed": [{"date": "2026-01-05", "eligible": True}]}}
    return Fence(elig, tmp_path)


def test_fence_admits_only_eligible_states_of_the_active_set(tmp_path):
    f = _fence(tmp_path)
    f.check("S0", "2024-06-03|10:00")
    f.check("L2", "2025-06-02|10:00")
    f.check("development", "2025-06-02|10:00")
    for stage, key in [("S0", "2025-06-02|10:00"), ("development", "2024-06-03|10:00"),
                       ("L3", "2024-06-04|10:00"), ("L3", "2026-01-05|10:00"),
                       ("L2", "2026-09-21|10:00"), ("P", "2025-06-02|10:00"),
                       ("L3", "2027-01-04|10:00"), ("bogus", "2024-06-03|10:00")]:
        with pytest.raises(FenceViolation):
            f.check(stage, key)


def test_planned_requests_cover_every_preregistered_payload():
    slots = ["10:00"]
    draws = {"draws": {"d3_s0": {"states": ["a|10:00"] * 10},
                       "d4t_l2_timestamps": {"output": ["b|10:30"] * 90},
                       "d5_l3": {"output": ["c|11:00"] * 50},
                       "d1_dev": {"output": ["2025-01-02"] * 100},
                       "d2_dev_secondary": {"output": ["2025-01-02"] * 30}}}
    p = planned_requests(draws)
    assert sum(1 for s, _, _ in p if s == "S0") == 10
    assert sum(1 for s, _, _ in p if s == "L2") == 90
    assert sum(1 for s, _, _ in p if s == "L3") == 50
    assert sum(1 for s, t, _ in p if s == "development" and t == "h15") == 1000
    assert sum(1 for s, t, _ in p if s == "development" and t in ("h5", "h30")) == 600
    assert slots


def test_store_guard_refuses_an_eligible_in_set_date_whose_file_is_absent(tmp_path):
    (tmp_path / "2024-06-03.duckdb").write_bytes(b"")
    elig = {"sessions": {"d_fit": [{"date": "2024-06-03", "eligible": True},
                                   {"date": "2024-06-05", "eligible": True}],
                         "d_eval": [], "h_exposed": []}}
    f = Fence(elig, tmp_path)
    f.check("S0", "2024-06-03|10:00")
    with pytest.raises(FenceViolation, match="beyond the store"):
        f.check("S0", "2024-06-05|10:00")
