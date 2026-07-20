import pytest
from scripts.rfa.power import power_at, n_required


def test_reproduces_documented_formation_requirement():
    n = n_required(delta=0.03, sd=0.2, target_power=0.80, two_sided=True)
    assert 340 <= n <= 360


def test_power_increases_with_n():
    lo = power_at(delta=0.03, sd=0.2, n=100, two_sided=True)
    hi = power_at(delta=0.03, sd=0.2, n=400, two_sided=True)
    assert hi > lo


def test_power_increases_with_delta_and_decreases_with_sd():
    base = power_at(delta=0.03, sd=0.2, n=200, two_sided=True)
    assert power_at(delta=0.06, sd=0.2, n=200, two_sided=True) > base
    assert power_at(delta=0.03, sd=0.4, n=200, two_sided=True) < base


def test_one_sided_needs_fewer_observations_than_two_sided():
    one = n_required(delta=0.03, sd=0.2, target_power=0.80, two_sided=False)
    two = n_required(delta=0.03, sd=0.2, target_power=0.80, two_sided=True)
    assert one < two


def test_degenerate_inputs_return_zero_power():
    assert power_at(delta=0.03, sd=0.0, n=200, two_sided=True) == 0.0
    assert power_at(delta=0.03, sd=0.2, n=1, two_sided=True) == 0.0


def test_n_required_returns_none_when_unreachable():
    assert n_required(delta=0.0, sd=0.2, target_power=0.80, two_sided=True) is None


def test_matches_psb1_bootstrap_reference():
    from scripts.psb1.screening_harness import _power
    ref, _ = _power(0.034892, 0.104033, 84)
    ours = power_at(delta=0.034892, sd=0.104033, n=84, two_sided=False)
    assert ours == pytest.approx(ref, abs=1e-9)
