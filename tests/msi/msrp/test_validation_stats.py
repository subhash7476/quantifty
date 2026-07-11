import numpy as np
import pytest

from core.msi.msrp.validation_stats import (
    roc_auc,
    moving_block_bootstrap_delta_auc_ci,
    canonical_json,
    format_6dp,
    sha256_hex,
)


def test_roc_auc_perfect_separation():
    assert roc_auc(np.array([0.1, 0.2, 0.8, 0.9]), np.array([0, 0, 1, 1])) == pytest.approx(1.0)


def test_roc_auc_inverted_is_zero():
    assert roc_auc(np.array([0.9, 0.8, 0.2, 0.1]), np.array([0, 0, 1, 1])) == pytest.approx(0.0)


def test_roc_auc_ties_average():
    assert roc_auc(np.array([0.5, 0.5, 0.5, 0.5]), np.array([0, 1, 0, 1])) == pytest.approx(0.5)


def test_roc_auc_single_class_is_nan():
    assert np.isnan(roc_auc(np.array([0.1, 0.2]), np.array([1, 1])))


def test_bootstrap_ci_is_deterministic_under_seed():
    rng = np.random.default_rng(0)
    n = 120
    cand = rng.normal(size=n)
    labels = (cand + rng.normal(size=n) > 0).astype(int)
    ref = rng.normal(size=n)
    ci_a = moving_block_bootstrap_delta_auc_ci(cand, ref, labels, 10, 500, seed=42)
    ci_b = moving_block_bootstrap_delta_auc_ci(cand, ref, labels, 10, 500, seed=42)
    assert ci_a == ci_b
    assert ci_a[0] <= ci_a[1]


def test_format_6dp_and_canonical_json():
    assert format_6dp(0.1234567) == 0.123457
    assert canonical_json({"b": format_6dp(1 / 3), "a": 2}) == '{"a": 2, "b": 0.333333}'


def test_sha256_hex_stable():
    assert sha256_hex("abc") == sha256_hex("abc")
    assert len(sha256_hex("abc")) == 64
