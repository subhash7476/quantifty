import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402

from scripts.jev_nms_1.models import (  # noqa: E402
    CLASSES, clipped, fold_of_state, fold_sizes, mean_log_loss, select, standardize,
)


def test_fold_conventions_for_442_sessions():
    assert fold_sizes(442, "A") == [89, 89, 88, 88, 88]
    assert fold_sizes(442, "B") == [88, 88, 88, 89, 89]
    assert fold_sizes(442, "C") == [88, 89, 88, 89, 88]
    assert all(sum(fold_sizes(442, c)) == 442 for c in "ABC")


def test_folds_are_contiguous_session_blocks():
    dates = [f"2024-01-{d:02d}" for d in range(1, 11) for _ in range(3)]
    f = fold_of_state(dates, "A")
    assert list(f) == sorted(f) and len(set(zip(dates, f))) == 10


def test_probabilities_mapped_by_class_name_clipped_and_renormalized():
    classes = np.array(sorted(CLASSES))            # alphabetical, as sklearn stores them
    raw = np.array([[0.0, 0.5, 0.0, 0.5]])         # disorderly, range_bound, trending_down, trending_up
    p = clipped(raw, classes)
    assert np.isclose(p.sum(), 1.0)
    assert p[0, CLASSES.index("trending_up")] == p[0, CLASSES.index("range_bound")] == p.max()
    assert np.isclose(p[0, CLASSES.index("disorderly")], 1e-4 / (1.0 + 2e-4))


def test_pooled_log_loss_and_first_in_order_tie_break():
    p = np.full((2, 4), 0.25)
    assert np.isclose(mean_log_loss(p, np.array(["range_bound", "disorderly"])), np.log(4))
    assert select([0.5, 0.4 + 1e-13, 0.4, 0.6]) == 1


def test_population_sd():
    _, _, sd = standardize(np.array([[1.0], [3.0]]))
    assert sd[0] == 1.0
