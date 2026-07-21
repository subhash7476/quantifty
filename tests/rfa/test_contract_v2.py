"""Contract v2 tests -- Sharpe-band parameterisation for per_trade_pnl.

Loaded by `RFA_V2_REMEDIATION_PROMPT.md`. Reference values verified
independently against scipy 1.17.0 before this file was written:

    Sharpe |  c  |  n  |  Power   | n_req(0.80)
    -------|-----|-----|----------|------------
    0.577  | 52  | 380 | 0.4649   | -
    0.601  | 52  | 380 | 0.4907   | -
    1.000  | 52  | 380 | 0.8540   | 323
    1.442  | 52  | 380 | 0.9877   | 156 (this impl) / 157 (prompt) -- 1-unit n_req
                                    discrepancy, df-dependent; disclosed in
                                    RFA_V2_REMEDIATION_REPORT.md

Minimum annualized Sharpe for power 0.80 at n=380, one-sided, alpha=0.05: 0.9214.
"""
import math
import pytest

from governance.rfa.declaration import Declaration, validate
from scripts.rfa.gate import (
    METHODOLOGY_VERSION, POWER_HURDLE, evaluate,
)
from scripts.rfa.power import power_at


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rank_ic(**overrides):
    base = dict(
        name="TESTC",
        methodology_version=METHODOLOGY_VERSION,
        delta_lo=0.02, delta_hi=0.05,
        sd_lo=0.15, sd_hi=0.25,
        delta_provenance="Jegadeesh-Titman (1993).",
        sd_provenance="Breadth floor, N=200 names.",
        prior_exposure="none",
        n_available=130,
        cadence="monthly",
        window="2012-2022",
        test_type="two_sided",
        metric="rank_ic",
    )
    base.update(overrides)
    return Declaration(**base)


def _per_trade_pnl(**overrides):
    base = dict(
        name="TESTP",
        methodology_version=METHODOLOGY_VERSION,
        sharpe_lo=0.5, sharpe_hi=0.8,
        cadence_per_year=52,
        sharpe_provenance="Carr-Wu (2009) short-variance Sharpes 0.5-1.0.",
        prior_exposure="none",
        n_available=380,
        cadence="weekly",
        window="2019-2026",
        test_type="one_sided",
        metric="per_trade_pnl",
    )
    base.update(overrides)
    return Declaration(**base)


# ---------------------------------------------------------------------------
# Task 4 -- validate() branches on metric
# ---------------------------------------------------------------------------

def test_per_trade_pnl_requires_sharpe_band():
    """validate() raises when a per_trade_pnl declaration omits the Sharpe band."""
    with pytest.raises(ValueError, match="sharpe_lo"):
        validate(_per_trade_pnl(sharpe_lo=None, sharpe_hi=None))
    with pytest.raises(ValueError, match="sharpe_hi"):
        validate(_per_trade_pnl(sharpe_hi=None))
    with pytest.raises(ValueError, match="cadence_per_year"):
        validate(_per_trade_pnl(cadence_per_year=None))
    with pytest.raises(ValueError, match="sharpe_provenance"):
        validate(_per_trade_pnl(sharpe_provenance="   "))


def test_per_trade_pnl_rejects_delta_sd_bands():
    """validate() raises when both parameterisations are supplied -- the
    redundant degree of freedom is what the O1 defect exploited."""
    with pytest.raises(ValueError, match="coupled-band"):
        validate(_per_trade_pnl(
            delta_lo=0.002, delta_hi=0.005,
            sd_lo=0.025, sd_hi=0.060,
        ))


def test_rank_ic_rejects_sharpe_band():
    """Mirror case: rank_ic declares delta/sd; sharpe is derived. Supplying
    both re-introduces the same coupling for the metric where it does not
    structurally cancel."""
    with pytest.raises(ValueError, match="coupled-band"):
        validate(_rank_ic(sharpe_lo=0.5, sharpe_hi=1.0))


def test_per_trade_pnl_sharpe_band_range_checks():
    """Sanity-range checks on the Sharpe band."""
    with pytest.raises(ValueError, match="sharpe_lo"):
        validate(_per_trade_pnl(sharpe_lo=-0.1))            # must be > 0
    with pytest.raises(ValueError, match="sharpe_lo"):
        validate(_per_trade_pnl(sharpe_lo=0.9, sharpe_hi=0.5))  # lo > hi
    with pytest.raises(ValueError, match="cadence_per_year"):
        validate(_per_trade_pnl(cadence_per_year=0))         # must be >= 1


# ---------------------------------------------------------------------------
# Task 4 -- evaluate() for per_trade_pnl: regression + thin proceed
# ---------------------------------------------------------------------------

def test_o1_original_bands_now_abandon():
    """REGRESSION, LOAD-BEARING. The O1 declaration's own coherent reading
    (Sharpe ~0.59-0.60) must now reach ABANDON at n=380. Pins
    RFA_GATE_O1_REVIEW.md S1 finding. Independent verification:
        S=0.601, c=52, n=380 -> power = 0.4907.
    """
    decl = _per_trade_pnl(
        name="O1_REGRESSION",
        sharpe_lo=0.577, sharpe_hi=0.601,
        cadence_per_year=52,
        n_available=380,
        sharpe_provenance=(
            "The O1 declaration's own coherent endpoint Sharpes, recovered "
            "from delta/sd via weekly_mean = (S/sqrt(52)) * weekly_sd. "
            "RFA_GATE_O1_REVIEW.md S1 table."
        ),
    )
    v = evaluate(decl)
    assert v.decision == "ABANDON"
    assert v.max_power == pytest.approx(0.4907, abs=1e-3)
    assert v.corner_sharpe == pytest.approx(0.601)
    assert v.corner_delta is None
    assert v.corner_sd is None


def test_sharpe_1_0_is_thin_proceed():
    """Even at the most generous defensible reading (literature ceiling
    Sharpe 1.0), the gate returns a THIN PROCEED: n_required=323 against
    n_available=380, a 1.18x margin -- not the 2.4x reported under the
    crossed-corner defect."""
    decl = _per_trade_pnl(
        name="O1_CEILING",
        sharpe_lo=0.5, sharpe_hi=1.0,
        cadence_per_year=52,
        n_available=380,
        sharpe_provenance="Carr-Wu (2009) short-variance Sharpe ceiling.",
    )
    v = evaluate(decl)
    assert v.decision == "PROCEED"
    assert v.max_power == pytest.approx(0.8540, abs=1e-3)
    assert v.n_required_corner == 323
    assert v.corner_sharpe == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Task 4 -- cadence invariance
# ---------------------------------------------------------------------------

def test_power_is_cadence_invariant():
    """For fixed annualized Sharpe S and elapsed time T, power is invariant
    under cadence c. ncp = (S/sqrt(c)) * sqrt(c*T) = S*sqrt(T), so c cancels.
    Slight numerical variation comes from discrete n and df=n-1.

    This test pins the F1 closure's 'higher cadence -> more formations ->
    escapes the sample wall' claim as wrong: at fixed S and T, going from
    monthly to daily buys nothing.
    """
    S = 1.0
    T_years = 7.3077   # 380 weeks / 52

    powers = []
    for c in (252, 52, 12):
        n = int(c * T_years)
        per_formation = S / math.sqrt(c)
        powers.append(power_at(per_formation, 1.0, n, two_sided=False))

    lo, hi = min(powers), max(powers)
    # Tolerance: discrete-n effect can move power by ~0.01; anything larger
    # would indicate the cadence-cancellation math is wrong.
    assert hi - lo < 0.02, f"power varied {lo:.4f}..{hi:.4f} across cadences"


# ---------------------------------------------------------------------------
# Task 4 -- withdrawn declaration enforcement
# ---------------------------------------------------------------------------

def test_withdrawn_declaration_raises_on_version():
    """The O1 declaration file is preserved byte-for-byte (digest
    25d4a723...) but pins methodology_version='1.0.0'. Under contract v2
    the gate must hard-fail rather than silently re-run a withdrawn
    declaration."""
    from governance.rfa.declarations.o1_vrp import DECLARATION
    with pytest.raises(ValueError, match="methodology_version"):
        evaluate(DECLARATION)
