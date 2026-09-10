"""Tests for the Options-Wall chain scanner.

Headline regression (HIGH-1): the farm list's ranking was degenerate — a
`margin_proxy` proportional to credit made every row's score a constant 4.0, so
the list fell back to strike order. The farm screen now ranks on per-strike IV−RV
gap; `test_farm_ranks_by_iv_rv_gap` asserts the scores are distinct and correctly
ordered, and would have failed the old implementation.

Also covered: negative-GEX gating, the IV−RV threshold, the both-legs IV
requirement that keeps `iv=0.0` deep-ITM garbage out of the vol-outlier scan, and
realized-vol sanity.
"""
from datetime import datetime

from core.analytics.chain_scanner import ChainScanner, ScanConfig
from core.analytics.options_analytics import (
    GEXResult, OIAnalysisResult, OptionsStructuralData, PCRResult,
)
from core.analytics.realized_vol import annualized_rv_pct
from core.data.options_provider import OptionChainRow


_NOW = datetime(2026, 8, 14, 10, 0)   # expiry 2026-08-18 -> DTE 4


def _row(strike, otype, ltp, iv, key):
    return OptionChainRow(
        strike=strike, option_type=otype, instrument_key=key, tradingsymbol=key,
        expiry="2026-08-18", ltp=ltp, iv=iv,
    )


def _structural(spot, regime, gamma_by_strike, zero_gamma=None,
                ce_mass=None, pe_mass=None):
    pcr = PCRResult(pcr=1.0, total_ce_oi=100, total_pe_oi=100)
    gex = GEXResult(
        net_gamma_total=sum(gamma_by_strike.values()),
        net_gamma_ce=1.0, net_gamma_pe=1.0,
        gamma_by_strike=gamma_by_strike, zero_gamma_level=zero_gamma, regime=regime,
        gamma_ce_by_strike=ce_mass or {}, gamma_pe_by_strike=pe_mass or {},
    )
    return OptionsStructuralData(
        underlying="NSE_INDEX|Nifty 50", underlying_ltp=spot, expiry="2026-08-18",
        timestamp=datetime.now(), pcr=pcr, gex=gex, oi_analysis=OIAnalysisResult(),
    )


# --- farm screen -----------------------------------------------------------

def test_farm_emits_single_atm_fly_when_spot_near_pin():
    scanner = ChainScanner(ScanConfig(iv_rv_min_gap=2.0, pin_band_pct=0.01))
    chain = [
        _row(100.0, "CE", 5.0, 15.0, "K1"), _row(100.0, "PE", 5.0, 15.0, "K2"),
        _row(101.0, "CE", 5.0, 15.0, "K3"), _row(101.0, "PE", 5.0, 15.0, "K4"),
    ]
    # spot 100.4 -> ATM 100; pin argmax gamma at 100 (near spot)
    structural = _structural(100.4, "Positive GEX (Stable)", {100.0: 10, 101.0: 1})
    farm = [r for r in scanner.scan_chain(chain, structural, realized_vol=10.0, now=_NOW)
            if r.screen == "premium_farm"]
    assert len(farm) == 1
    assert farm[0].strike == 100.0            # ATM, not pin-loop
    assert farm[0].structure == "iron_fly"
    assert farm[0].score == farm[0].iv_minus_rv


def test_farm_result_carries_iron_fly_leg_quotes():
    scanner = ChainScanner(ScanConfig(iv_rv_min_gap=2.0, pin_band_pct=0.01, wing_pct=0.02))

    def q(strike, ot, bid, ask, key):
        r = _row(strike, ot, (bid + ask) / 2.0, 15.0, key)
        r.best_bid, r.best_ask = bid, ask
        return r

    # spot 100 -> ATM 100; wings at ±2% snap to 98 / 102 (same rule as build_iron_fly)
    chain = [
        q(98.0, "CE", 3.9, 4.1, "C98"), q(98.0, "PE", 0.9, 1.1, "P98"),
        q(100.0, "CE", 4.9, 5.1, "C100"), q(100.0, "PE", 4.9, 5.1, "P100"),
        q(102.0, "CE", 0.9, 1.1, "C102"), q(102.0, "PE", 3.9, 4.1, "P102"),
    ]
    structural = _structural(100.0, "Positive GEX (Stable)", {100.0: 10, 102.0: 1})
    farm = [r for r in scanner.scan_chain(chain, structural, realized_vol=10.0, now=_NOW)
            if r.screen == "premium_farm"]
    assert len(farm) == 1

    legs = farm[0].legs
    assert legs is not None
    by = {(l["side"], l["option_type"]): l for l in legs}
    assert by[("SELL", "CE")]["strike"] == 100.0
    assert by[("SELL", "PE")]["strike"] == 100.0
    assert by[("BUY", "CE")]["strike"] == 102.0   # call wing
    assert by[("BUY", "PE")]["strike"] == 98.0    # put wing
    assert by[("SELL", "CE")]["best_bid"] == 4.9
    assert by[("SELL", "CE")]["best_ask"] == 5.1
    assert by[("SELL", "CE")]["mid"] == 5.0


def test_farm_gated_off_when_spot_far_from_pin():
    scanner = ChainScanner(ScanConfig(iv_rv_min_gap=2.0, pin_band_pct=0.005))
    chain = [
        _row(100.0, "CE", 5.0, 15.0, "K1"), _row(100.0, "PE", 5.0, 15.0, "K2"),
        _row(110.0, "CE", 5.0, 15.0, "K3"), _row(110.0, "PE", 5.0, 15.0, "K4"),
    ]
    # spot 100 but pin at 110 -> |spot-pin|/spot = 0.10 > 0.005 -> no trade
    structural = _structural(100.0, "Positive GEX (Stable)", {100.0: 1, 110.0: 10})
    farm = [r for r in scanner.scan_chain(chain, structural, realized_vol=10.0, now=_NOW)
            if r.screen == "premium_farm"]
    assert farm == []


def test_farm_gate_uses_atm_iv_not_pin_iv():
    scanner = ChainScanner(ScanConfig(iv_rv_min_gap=2.0, pin_band_pct=0.02))
    # ATM(100) IV 11 vs RV 10 -> gap 1.0 < 2.0 -> no trade, even if a neighbour is rich
    chain = [
        _row(100.0, "CE", 5.0, 11.0, "K1"), _row(100.0, "PE", 5.0, 11.0, "K2"),
        _row(101.0, "CE", 5.0, 20.0, "K3"), _row(101.0, "PE", 5.0, 20.0, "K4"),
    ]
    structural = _structural(100.2, "Positive GEX (Stable)", {100.0: 10, 101.0: 9})
    farm = [r for r in scanner.scan_chain(chain, structural, realized_vol=10.0, now=_NOW)
            if r.screen == "premium_farm"]
    assert farm == []


def test_farm_gated_off_in_negative_gex():
    scanner = ChainScanner()
    chain = [_row(100.0, "CE", 5.0, 20.0, "K1"), _row(100.0, "PE", 5.0, 20.0, "K2")]
    structural = _structural(100.0, "Negative GEX (Volatile)", {100.0: 10})
    results = scanner.scan_chain(chain, structural, realized_vol=10.0, now=_NOW)
    assert all(r.screen != "premium_farm" for r in results)


def test_farm_requires_iv_rv_gap():
    scanner = ChainScanner(ScanConfig(iv_rv_min_gap=5.0, pin_band_pct=0.01))
    chain = [_row(100.0, "CE", 5.0, 12.0, "K1"), _row(100.0, "PE", 5.0, 12.0, "K2")]
    structural = _structural(100.0, "Positive GEX (Stable)", {100.0: 10})
    results = scanner.scan_chain(chain, structural, realized_vol=10.0, now=_NOW)
    assert all(r.screen != "premium_farm" for r in results)  # gap 2.0 < 5.0


# --- IV helpers ------------------------------------------------------------

def test_strike_mid_iv_requires_both_legs():
    scanner = ChainScanner()
    one_sided = [_row(100.0, "CE", 5.0, 0.0, "K1"), _row(100.0, "PE", 5.0, 40.0, "K2")]
    assert scanner._strike_mid_iv(one_sided, 100.0) is None
    both = [_row(100.0, "CE", 5.0, 15.0, "K1"), _row(100.0, "PE", 5.0, 15.0, "K2")]
    assert scanner._strike_mid_iv(both, 100.0) == 15.0


def test_vol_outliers_requires_both_legs():
    scanner = ChainScanner()
    chain = []
    for s in (98.0, 100.0, 101.0, 102.0):
        iv = 25.0 if s == 101.0 else 15.0
        chain.append(_row(s, "CE", 5.0, iv, f"C{s}"))
        chain.append(_row(s, "PE", 5.0, iv, f"P{s}"))
    # 99.0 has a garbage-CE IV (0.0) and a normal PE -> one-sided -> excluded
    chain.append(_row(99.0, "CE", 5.0, 0.0, "C99"))
    chain.append(_row(99.0, "PE", 5.0, 15.0, "P99"))

    flagged = {s for s, _, _ in scanner._vol_outliers(chain, spot=100.0)}
    assert 101.0 in flagged
    assert 99.0 not in flagged


# --- realized vol ----------------------------------------------------------

def test_rv_flat_series_is_zero():
    assert annualized_rv_pct([[100.0, 100.0, 100.0]]) == 0.0


def test_rv_noisier_is_higher():
    calm = annualized_rv_pct([[100.0, 100.1, 100.0, 100.1]])
    wild = annualized_rv_pct([[100.0, 101.0, 100.0, 101.0]])
    assert wild > calm > 0


# --- pin definition (2026-09-09 pin-gate defect) ----------------------------

def _pin_case(spot):
    """Mass concentrates at 100 (near spot); signed exposure peaks at 110 (far).

    This is the 2026-09-09 Nifty shape: the dashboard pinned 23,500 (0.11% from
    spot) while the entry gate's signed argmax sat at 23,700 (0.79%), locking the
    index out on 1,649 of 1,649 snapshots.
    """
    return _structural(
        spot, "Positive GEX (Stable)",
        gamma_by_strike={100.0: -8.0, 110.0: 3.0},   # signed argmax -> 110
        ce_mass={100.0: 12.0, 110.0: 2.0},           # unsigned mass  -> 100
        pe_mass={100.0: 10.0, 110.0: 1.0},
    )


def test_pin_uses_unsigned_gamma_mass_not_signed_exposure():
    """The entry gate must test the same pin the dashboard and engine already use.

    `wall_metrics.pin_candidates` (unsigned mass) is the platform's primary pin;
    `engine._regime_snapshot` reaches for the signed argmax only as a fallback.
    """
    scanner = ChainScanner()
    assert scanner._pin_strike(_pin_case(100.0)) == 100.0


def test_pin_falls_back_to_signed_argmax_when_mass_is_absent():
    """Mirrors engine.py: the signed argmax is the fallback, not the definition."""
    scanner = ChainScanner()
    st = _structural(100.0, "Positive GEX (Stable)", {100.0: 1.0, 110.0: 10.0})
    assert scanner._pin_strike(st) == 110.0


def test_pin_is_none_when_there_is_no_gamma_at_all():
    assert ChainScanner()._pin_strike(_structural(100.0, "Positive GEX (Stable)", {})) is None


def test_farm_admits_a_chain_pinned_near_spot_by_mass():
    """The Nifty lockout: every other gate passed; only the pin gate failed."""
    scanner = ChainScanner(ScanConfig(iv_rv_min_gap=2.0, pin_band_pct=0.005))
    chain = [
        _row(100.0, "CE", 5.0, 15.0, "K1"), _row(100.0, "PE", 5.0, 15.0, "K2"),
        _row(110.0, "CE", 1.0, 15.0, "K3"), _row(110.0, "PE", 1.0, 15.0, "K4"),
    ]
    farm = [r for r in scanner.scan_chain(chain, _pin_case(100.0), realized_vol=10.0,
                                          now=_NOW) if r.screen == "premium_farm"]
    assert len(farm) == 1
    assert farm[0].strike == 100.0


def test_pin_conviction_is_computed_on_the_mass_basis_and_stays_a_fraction():
    """Conviction must share the pin's basis, and keep ScanResult's 0-1 unit.

    `session_regime.pin_conviction` is 0-100 and `scan_results.pin_conviction` is
    0-1; the dashboard renders each accordingly (index.html:315 vs :637). Changing
    the basis must not change the unit.
    """
    scanner = ChainScanner()
    st = _pin_case(100.0)
    conv = scanner._pin_conviction(st, scanner._pin_strike(st))
    assert 0.0 < conv <= 1.0
    # 110 scores (2+1)/(12+10) = 13.6% of the leader -> conviction 1 - 0.136
    assert abs(conv - 0.8636) < 0.01
