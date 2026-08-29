import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.signal_engine.combination.composite_gate import Leg, evaluate  # noqa: E402

RNG = np.random.default_rng(42)


def _series(mean, sd, n=71, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(0.0, 1.0, n)
    x = (x - x.mean()) / x.std(ddof=1)
    return mean + sd * x


def test_rejects_composite_that_does_not_beat_its_best_leg():
    # This is the IVOL gate-4 shape: composite IR below the strong leg's IR.
    strong = _series(0.047, 0.077, seed=1)
    weak = _series(-0.050, 0.163, seed=2)
    composite = _series(0.070, 0.120, seed=3)   # IR 0.583 < strong's 0.610

    v = evaluate(composite, [Leg("CARRY", strong, +1), Leg("IVOL", weak, -1)], n_star=42)

    assert not v.passed
    assert v.stage == "LIFT"
    assert v.lift < 1.0
    assert v.best_leg == "CARRY"
    assert "dilution" in v.reason


def test_lift_is_checked_before_power_so_a_diluting_composite_cannot_pass_on_power():
    strong = _series(0.047, 0.077, seed=1)
    weak = _series(-0.050, 0.163, seed=2)
    composite = _series(0.070, 0.120, seed=3)

    v = evaluate(composite, [Leg("CARRY", strong, +1), Leg("IVOL", weak, -1)], n_star=42)

    assert v.power >= 0.80          # it WOULD have cleared the old 0.80-only gate
    assert not v.passed             # and the lift check stops it anyway
    assert v.stage == "LIFT"


def test_rejects_leg_whose_realized_sign_opposes_its_registration():
    # LAG: registered +1, realized negative.
    a = _series(0.040, 0.080, seed=4)
    lag = _series(-0.021, 0.136, seed=5)
    composite = _series(0.090, 0.090, seed=6)   # high IR so LIFT passes

    v = evaluate(composite, [Leg("CARRY", a, +1), Leg("LAG", lag, +1)], n_star=42)

    assert not v.passed
    assert v.stage == "SIGN"
    assert any("LAG" in f for f in v.sign_failures)


def test_rejects_leg_with_no_registered_sign():
    # SKEW registered two-sided: no direction pinned before the read.
    a = _series(0.040, 0.080, seed=4)
    skew = _series(-0.025, 0.117, seed=7)
    composite = _series(0.090, 0.090, seed=6)

    v = evaluate(composite, [Leg("CARRY", a, +1), Leg("SKEW", skew, 0)], n_star=42)

    assert not v.passed
    assert v.stage == "SIGN"
    assert v.sign_failures == ("SKEW: no registered sign",)


def test_rejects_when_power_below_hurdle_even_though_lift_and_signs_pass():
    a = _series(0.010, 0.150, seed=8)
    b = _series(0.008, 0.160, seed=9)
    composite = _series(0.014, 0.150, seed=10)  # lift > 1, but underpowered

    v = evaluate(composite, [Leg("A", a, +1), Leg("B", b, +1)], n_star=42)

    assert v.lift > 1.0
    assert not v.passed
    assert v.stage == "POWER"
    assert v.power < 0.80


def test_passes_when_lift_signs_and_power_all_clear():
    a = _series(0.040, 0.090, seed=11)
    b = _series(0.035, 0.100, seed=12)
    composite = _series(0.060, 0.090, seed=13)

    v = evaluate(composite, [Leg("A", a, +1), Leg("B", b, +1)], n_star=42)

    assert v.passed
    assert v.stage == "ALL"
    assert v.lift > 1.0
    assert v.power >= 0.80


def test_negative_registered_sign_leg_is_accepted_when_realized_sign_matches():
    a = _series(0.040, 0.090, seed=11)
    neg = _series(-0.035, 0.100, seed=12)
    composite = _series(0.060, 0.090, seed=13)

    v = evaluate(composite, [Leg("A", a, +1), Leg("NEG", neg, -1)], n_star=42)

    assert v.passed


def test_rejects_leg_whose_registered_sign_was_reversed_by_a_later_oos_read():
    # The IVOL case: negative as registered on TRAIN+HOLDOUT, so the plain sign
    # check passes -- but the SEALED read reversed it. The gate must not approve
    # a direction later data refuted.
    a = _series(0.040, 0.090, seed=11)
    ivol = _series(-0.042, 0.151, seed=14)
    composite = _series(0.075, 0.090, seed=15)

    clean = evaluate(composite, [Leg("A", a, +1), Leg("IVOL", ivol, -1)], n_star=42)
    assert clean.passed, "precondition: passes when the falsification is not declared"

    v = evaluate(composite,
                 [Leg("A", a, +1), Leg("IVOL", ivol, -1, sign_falsified=True)],
                 n_star=42)

    assert not v.passed
    assert v.stage == "SIGN"
    assert any("REVERSED" in f for f in v.sign_failures)


def test_raises_when_legs_are_not_on_a_common_intersection():
    a = _series(0.040, 0.090, n=71, seed=11)
    b = _series(0.035, 0.100, n=54, seed=12)
    composite = _series(0.060, 0.090, n=71, seed=13)

    with pytest.raises(ValueError, match="common intersection"):
        evaluate(composite, [Leg("A", a, +1), Leg("B", b, +1)], n_star=42)


def test_raises_on_single_leg():
    a = _series(0.040, 0.090, seed=11)
    with pytest.raises(ValueError, match="at least two legs"):
        evaluate(a, [Leg("A", a, +1)], n_star=42)
