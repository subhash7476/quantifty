import hashlib
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from scripts.jev_nms_1 import postmortem as pm  # noqa: E402

ART = pm.OUT / pm.ARTIFACT_NAME


def test_auc_rank_sum_matches_definition():
    score = np.array([0.1, 0.4, 0.35, 0.8, 0.4])
    pos = np.array([False, False, True, True, True])
    pairs = [(s1 > s0) + 0.5 * (s1 == s0) for s1 in score[pos] for s0 in score[~pos]]
    assert pm.auc(score, pos) == pytest.approx(np.mean(pairs))
    assert pm.auc(np.arange(4.0), np.array([False, False, True, True])) == 1.0


def test_postmortem_inputs_are_the_frozen_hashes():
    assert pm.DEV_SHA256 == hashlib.sha256((pm.OUT / "development_step6.json").read_bytes()).hexdigest()
    assert pm.CACHE_SHA256 == hashlib.sha256((pm.OUT / "cache.jsonl").read_bytes()).hexdigest()


@pytest.mark.skipif(not ART.exists(), reason="post-mortem artifact not built")
def test_stored_pool_parameters_reproduce_the_recorded_oof_dll_exactly():
    a = json.loads(ART.read_text(encoding="utf-8"))
    rep = a["integrity"]["stored_fold_params_reproduce_recorded_oof_dll"]
    assert all(v["exact"] for v in rep.values()) and set(rep) == {"5", "15", "30"}
    assert rep["15"]["recorded"] == pytest.approx(-0.0004990247434012935, abs=0)
    assert a["integrity"]["request_state_equals_sealed_features_mismatches"] == 0
    assert a["integrity"]["raw_probabilities_keyed_by_class_name_equal_parse"]
    assert a["label"] == "POST-MORTEM / NON-CONFIRMATORY"


@pytest.mark.skipif(not ART.exists(), reason="post-mortem artifact not built")
def test_postmortem_class_usage_is_consistent_with_recorded_confusion():
    a = json.loads(ART.read_text(encoding="utf-8"))
    dev = json.loads((pm.OUT / "development_step6.json").read_text(encoding="utf-8"))
    conf = dev["horizons"]["15"]["metrics"]["J"]["confusion"]
    share = a["horizons"]["15"]["class_usage"]["J"]["argmax_share"]
    for c in pm.C:
        assert share[c] == pytest.approx(sum(conf[t][c] for t in pm.C) / 1000)
