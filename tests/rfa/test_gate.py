import pytest
from governance.rfa.declaration import Declaration
from scripts.rfa.gate import METHODOLOGY_VERSION, POWER_HURDLE, evaluate


def _decl(**overrides):
    base = dict(
        name="TESTC1",
        methodology_version=METHODOLOGY_VERSION,
        delta_lo=0.02, delta_hi=0.05,
        sd_lo=0.15, sd_hi=0.25,
        delta_provenance="literature",
        sd_provenance="first principles",
        prior_exposure="none",
        n_available=130,
        cadence="monthly",
        window="2012-2022",
        test_type="two_sided",
        metric="rank_ic",
    )
    base.update(overrides)
    return Declaration(**base)


def test_abandons_when_corner_cannot_clear_hurdle():
    v = evaluate(_decl(delta_lo=0.005, delta_hi=0.01, sd_lo=0.30, sd_hi=0.40, n_available=50))
    assert v.decision == "ABANDON"
    assert v.max_power < POWER_HURDLE


def test_proceeds_when_corner_clears_hurdle():
    v = evaluate(_decl(delta_hi=0.20, sd_lo=0.10, n_available=400))
    assert v.decision == "PROCEED"
    assert v.max_power >= POWER_HURDLE


def test_verdict_flips_with_inputs_only():
    weak = evaluate(_decl(delta_lo=0.005, delta_hi=0.01, sd_lo=0.30, sd_hi=0.40, n_available=50))
    strong = evaluate(_decl(delta_hi=0.20, sd_lo=0.10, n_available=400))
    assert {weak.decision, strong.decision} == {"ABANDON", "PROCEED"}


def test_evaluates_at_optimistic_corner():
    v = evaluate(_decl())
    assert v.corner_delta == 0.05
    assert v.corner_sd == 0.15


def test_methodology_mismatch_is_hard_failure():
    with pytest.raises(ValueError, match="methodology_version"):
        evaluate(_decl(methodology_version="0.0.1-ancient"))


def test_invalid_declaration_rejected_before_evaluation():
    with pytest.raises(ValueError, match="delta_provenance"):
        evaluate(_decl(delta_provenance=""))


def test_reports_required_formations_at_each_band_point():
    v = evaluate(_decl())
    assert v.n_required_corner < v.n_required_central < v.n_required_pessimistic
