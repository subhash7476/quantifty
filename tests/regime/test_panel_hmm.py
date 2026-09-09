"""Panel HMM engine tests — §11 of the N200 regime design spec.

The two that carry the weight are `test_recovers_known_parameters` (if EM cannot
recover parameters it generated, nothing downstream means anything) and
`test_filtered_probability_ignores_future_bars` (the only test that actually
proves filtered-not-smoothed — a smoother fails it immediately).
"""
from __future__ import annotations

import numpy as np
import pytest

from core.analytics.regime.panel_hmm import (
    LOG_EMISSION_FLOOR, PanelHMM, canonical_order, filter_sequence, fit_panel,
    log_emissions, state_entropy,
)

K = 3
D = 2

TRUE_A = np.array([
    [0.90, 0.08, 0.02],
    [0.10, 0.80, 0.10],
    [0.05, 0.15, 0.80],
])
# state 0 quiet, state 1 intermediate, state 2 stress — feature 0 is the
# volatility proxy the canonical ordering sorts on
TRUE_MU = np.array([[-1.0, 0.5], [0.0, -0.5], [1.6, 0.2]])
TRUE_VAR = np.array([[0.25, 0.40], [0.25, 0.40], [0.36, 0.40]])


def generate_panel(n_seq: int, n_steps: int, seed: int = 0) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    seqs = []
    for _ in range(n_seq):
        s = rng.integers(0, K)
        rows = []
        for _ in range(n_steps):
            rows.append(rng.normal(TRUE_MU[s], np.sqrt(TRUE_VAR[s])))
            s = rng.choice(K, p=TRUE_A[s])
        seqs.append(np.asarray(rows))
    return seqs


@pytest.fixture(scope="module")
def fitted() -> PanelHMM:
    return fit_panel(generate_panel(40, 500), n_states=K, seed=7)


def test_recovers_known_parameters(fitted: PanelHMM):
    assert fitted.converged
    assert np.allclose(fitted.mu, TRUE_MU, atol=0.15)
    assert np.allclose(fitted.var, TRUE_VAR, atol=0.15)
    assert np.allclose(fitted.A, TRUE_A, atol=0.06)


def test_filtered_probability_ignores_future_bars(fitted: PanelHMM):
    x = generate_panel(1, 300, seed=99)[0]
    full, _, _ = filter_sequence(fitted, x)
    for t in (5, 50, 180, 299):
        truncated, _, _ = filter_sequence(fitted, x[: t + 1])
        assert np.array_equal(full[t], truncated[t]), (
            f"P(S_{t}) changed when future rows were removed — the filter is "
            "reading ahead"
        )


def test_fit_is_deterministic():
    seqs = generate_panel(12, 200, seed=3)
    a = fit_panel(seqs, n_states=K, seed=11)
    b = fit_panel(seqs, n_states=K, seed=11)
    assert np.array_equal(a.A, b.A)
    assert np.array_equal(a.mu, b.mu)
    assert np.array_equal(a.var, b.var)
    assert a.model_hash == b.model_hash


def test_canonical_ordering_sorts_states_by_volatility_mean(fitted: PanelHMM):
    assert list(fitted.mu[:, 0]) == sorted(fitted.mu[:, 0])


def test_canonical_ordering_is_invariant_to_label_permutation(fitted: PanelHMM):
    perm = [2, 0, 1]
    shuffled = PanelHMM(
        A=fitted.A[np.ix_(perm, perm)], pi=fitted.pi[perm], mu=fitted.mu[perm],
        var=fitted.var[perm], order_map=tuple(range(K)), n_iter=fitted.n_iter,
        loglik=fitted.loglik, converged=fitted.converged,
    )
    restored = canonical_order(shuffled)
    assert np.allclose(restored.A, fitted.A)
    assert np.allclose(restored.mu, fitted.mu)


def test_log_emissions_are_floored_for_extreme_outliers(fitted: PanelHMM):
    x = np.array([[1e6, -1e6]])
    le = log_emissions(x, fitted.mu, fitted.var)
    assert np.all(np.isfinite(le))
    assert np.all(le >= LOG_EMISSION_FLOOR)


def test_outlier_row_does_not_poison_the_posterior(fitted: PanelHMM):
    x = generate_panel(1, 60, seed=5)[0]
    x[30] = [1e6, -1e6]
    probs, entropy, states = filter_sequence(fitted, x)
    assert np.all(np.isfinite(probs))
    assert np.allclose(probs.sum(axis=1), 1.0)
    assert np.all(np.isfinite(entropy))
    assert states.shape == (len(x),)


def test_loglik_is_monotone_non_decreasing():
    model = fit_panel(generate_panel(8, 300, seed=17), n_states=K, seed=2,
                      track_history=True)
    hist = np.asarray(model.loglik_history)
    assert np.all(np.diff(hist) >= -1e-8), "EM decreased the likelihood"


def test_entropy_is_zero_at_certainty_and_one_at_uniform():
    assert state_entropy(np.array([[1.0, 0.0, 0.0]]))[0] == pytest.approx(0.0)
    assert state_entropy(np.full((1, 3), 1 / 3))[0] == pytest.approx(1.0)


def test_short_sequences_are_rejected_rather_than_silently_fitted():
    with pytest.raises(ValueError, match="at least"):
        fit_panel([np.zeros((1, D))], n_states=K, seed=0)
