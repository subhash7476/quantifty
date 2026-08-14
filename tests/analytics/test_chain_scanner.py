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


def _row(strike, otype, ltp, iv, key):
    return OptionChainRow(
        strike=strike, option_type=otype, instrument_key=key, tradingsymbol=key,
        expiry="2026-08-18", ltp=ltp, iv=iv,
    )


def _structural(spot, regime, gamma_by_strike, zero_gamma=None):
    pcr = PCRResult(pcr=1.0, total_ce_oi=100, total_pe_oi=100)
    gex = GEXResult(
        net_gamma_total=sum(gamma_by_strike.values()),
        net_gamma_ce=1.0, net_gamma_pe=1.0,
        gamma_by_strike=gamma_by_strike, zero_gamma_level=zero_gamma, regime=regime,
    )
    return OptionsStructuralData(
        underlying="NSE_INDEX|Nifty 50", underlying_ltp=spot, expiry="2026-08-18",
        timestamp=datetime.now(), pcr=pcr, gex=gex, oi_analysis=OIAnalysisResult(),
    )


# --- farm screen -----------------------------------------------------------

def test_farm_ranks_by_iv_rv_gap():
    scanner = ChainScanner(ScanConfig(iv_rv_min_gap=2.0, pin_band_pct=0.01))
    chain = [
        _row(99.5, "CE", 5.0, 20.0, "K1"), _row(99.5, "PE", 5.0, 20.0, "K2"),
        _row(100.0, "CE", 5.0, 15.0, "K3"), _row(100.0, "PE", 5.0, 15.0, "K4"),
        _row(100.5, "CE", 5.0, 18.0, "K5"), _row(100.5, "PE", 5.0, 18.0, "K6"),
    ]
    structural = _structural(100.0, "Positive GEX (Stable)",
                             {99.5: 5, 100.0: 10, 100.5: 3})
    results = scanner.scan_chain(chain, structural, realized_vol=10.0)
    farm = [r for r in results if r.screen == "premium_farm"]

    assert len(farm) == 3
    scores = [r.score for r in farm]
    assert len(set(scores)) == 3                     # discriminating, not a constant
    assert scores == sorted(scores, reverse=True)    # desc
    assert [r.strike for r in farm] == [99.5, 100.5, 100.0]  # gap 10, 8, 5


def test_farm_gated_off_in_negative_gex():
    scanner = ChainScanner()
    chain = [_row(100.0, "CE", 5.0, 20.0, "K1"), _row(100.0, "PE", 5.0, 20.0, "K2")]
    structural = _structural(100.0, "Negative GEX (Volatile)", {100.0: 10})
    results = scanner.scan_chain(chain, structural, realized_vol=10.0)
    assert all(r.screen != "premium_farm" for r in results)


def test_farm_requires_iv_rv_gap():
    scanner = ChainScanner(ScanConfig(iv_rv_min_gap=5.0, pin_band_pct=0.01))
    chain = [_row(100.0, "CE", 5.0, 12.0, "K1"), _row(100.0, "PE", 5.0, 12.0, "K2")]
    structural = _structural(100.0, "Positive GEX (Stable)", {100.0: 10})
    results = scanner.scan_chain(chain, structural, realized_vol=10.0)
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
