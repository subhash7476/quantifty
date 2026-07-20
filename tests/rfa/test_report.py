from governance.rfa.declaration import Declaration
from scripts.rfa.gate import METHODOLOGY_VERSION, evaluate
from scripts.rfa.report import render


def _decl(**overrides):
    base = dict(
        name="TESTC1",
        methodology_version=METHODOLOGY_VERSION,
        delta_lo=0.02, delta_hi=0.05,
        sd_lo=0.15, sd_hi=0.25,
        delta_provenance="Momentum magnitudes from Jegadeesh & Titman (1993).",
        sd_provenance="Breadth-based dispersion floor, first principles.",
        prior_exposure="Operator has read PSB-1 and PSB-2 reports.",
        n_available=130,
        cadence="monthly",
        window="2012-2022",
        test_type="two_sided",
        metric="rank_ic",
    )
    base.update(overrides)
    return Declaration(**base)


def _render(**overrides):
    d = _decl(**overrides)
    return render(d, evaluate(d), "deadbeef" * 8)


def test_report_states_verdict_and_digest():
    out = _render(delta_lo=0.005, delta_hi=0.01, sd_lo=0.30, sd_hi=0.40, n_available=50)
    assert "ABANDON" in out
    assert "deadbeef" * 8 in out
    assert METHODOLOGY_VERSION in out


def test_proceed_is_qualified_as_not_provably_infeasible():
    out = _render(delta_hi=0.20, sd_lo=0.10, n_available=400)
    assert "PROCEED" in out
    assert "not provably infeasible" in out


def test_report_carries_scope_caveat_and_corner_rationale():
    out = _render().lower()
    assert "fees" in out and "maxdd" in out
    assert "intentionally unrealistic" in out


def test_report_reproduces_provenance_verbatim():
    d = _decl()
    out = render(d, evaluate(d), "0" * 64)
    assert d.delta_provenance in out
    assert d.sd_provenance in out
    assert d.prior_exposure in out
