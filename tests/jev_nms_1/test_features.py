import math

import pytest

from scripts.jev_nms_1.features import FIELDS, fixed, raw_features, rounded, slot_index


def _bars(n=345):
    return [(100 + i * 0.1, 100 + i * 0.1 + 0.05, 100 + i * 0.1 - 0.05, 100 + i * 0.1 + 0.02)
            for i in range(n)]


def test_point_in_time_definitions():
    bars, t, cp = _bars(), slot_index("10:00"), 99.0
    f = raw_features(bars[:t], t, cp)
    close = [b[3] for b in bars]
    assert f["minutes_since_open"] == 45
    assert f["gap_bp"] == pytest.approx(math.log(bars[0][0] / cp) * 1e4)
    assert f["ret_open_bp"] == pytest.approx(math.log(close[44] / bars[0][0]) * 1e4)
    assert f["ret_15_bp"] == pytest.approx(math.log(close[44] / close[29]) * 1e4)
    assert f["ret_30_bp"] == pytest.approx(math.log(close[44] / close[14]) * 1e4)
    assert f["range_30_bp"] == pytest.approx(
        math.log(max(b[1] for b in bars[15:45]) / min(b[2] for b in bars[15:45])) * 1e4)
    assert f["twap_dist_bp"] == pytest.approx(math.log(close[44] / (sum(close[:45]) / 45)) * 1e4)


def test_er_30_uses_the_unrounded_f5():
    bars, t = _bars(), slot_index("11:00")
    f = raw_features(bars[:t], t, 99.0)
    rets = [math.log(bars[i][3] / bars[i - 1][3]) for i in range(t - 30, t)]
    assert f["er_30"] == abs(math.log(bars[t - 1][3] / bars[t - 31][3]) * 1e4) / (
        sum(abs(r) for r in rets) * 1e4)


def test_features_never_read_bar_t_or_later():
    bars, t = _bars(), slot_index("12:00")
    changed = bars[:t] + [(1.0, 1.0, 1.0, 1.0)] * (345 - t)
    assert raw_features(bars[:t], t, 99.0) == raw_features(changed[:t], t, 99.0)


def test_rounding_and_negative_zero():
    assert fixed(-0.04, 1) == 0.0 and str(fixed(-0.04, 1)) == "0.0"
    assert fixed(12.3456, 1) == 12.3 and fixed(0.12345, 3) == 0.123
    r = rounded({k: -0.0001 for k in FIELDS} | {"minutes_since_open": 45})
    assert r["gap_bp"] == 0.0 and r["minutes_since_open"] == 45
