import math
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

from scripts.jev_nms_1.dfit import classify, laplace, q, slot_index, state_windows, window_stats  # noqa: E402


def test_slot_index_counts_minutes_from_the_open():
    assert slot_index("10:00") == 45 and slot_index("14:30") == 315


def test_forward_window_uses_bars_t_to_t_plus_h_minus_1_and_P_t_is_bar_t_minus_1():
    closes = [100.0 + i for i in range(345)]
    r, er, rv = state_windows(closes, "10:00", 5)["fwd"]
    assert r == math.log(closes[49] / closes[44])      # P(t+h)=C[t+h-1], P(t)=C[t-1]
    assert abs(er - 1.0) < 1e-12                          # monotone path
    rets = [math.log(closes[j] / closes[j - 1]) for j in range(45, 50)]
    assert rv == math.sqrt(sum(x * x for x in rets))


def test_trailing_window_is_bars_t_minus_h_to_t_minus_1():
    closes = [100.0 + i for i in range(345)]
    r, _, _ = state_windows(closes, "10:00", 30)["trail"]
    assert r == math.log(closes[44] / closes[14])


def test_er_is_zero_when_there_is_no_movement():
    assert window_stats([100.0] * 10, 1, 5) == (0.0, 0.0, 0.0)


def test_label_precedence_disorderly_first_then_trending():
    c = {"E_star": 0.5, "Z_star": 1.0, "V_star": 1.0}
    assert classify(0.01, 0.4, 2.0, 1.5, c) == "disorderly"
    assert classify(0.01, 0.6, 2.0, 1.5, c) == "trending_up"
    assert classify(-0.01, 0.6, -2.0, 0.1, c) == "trending_down"
    assert classify(0.01, 0.6, 0.5, 0.1, c) == "range_bound"
    assert classify(0.01, 0.5, 1.0, 0.1, c) == "trending_up"     # >= at thresholds


def test_quantile_is_numpy_linear():
    assert q([1, 2, 3, 4], 0.5) == 2.5 and q([0, 10], 0.7) == 7.0


def test_laplace_smoothing_plus_one():
    p = laplace({"trending_up": 2, "trending_down": 0, "range_bound": 0, "disorderly": 0})
    assert p["trending_up"] == 3 / 6 and p["disorderly"] == 1 / 6
