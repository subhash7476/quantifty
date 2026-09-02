"""_regime_snapshot must expose spot and the full gamma ladder for the dashboard."""
from datetime import datetime

from core.analytics.options_analytics import (
    GEXResult, OIAnalysisResult, OptionsStructuralData, PCRResult,
)
from core.data.options_provider import OptionChainRow
from core.options_wall.engine import _regime_snapshot


def _chain():
    rows = []
    for k in (99, 100, 101):
        rows.append(OptionChainRow(strike=float(k), option_type="CE",
                                   instrument_key=f"CE{k}", tradingsymbol=f"CE{k}",
                                   expiry="2026-08-18", ltp=1.0, iv=15.0, underlying_ltp=100.0))
    return rows


def _structural(spot=100.0):
    gex = GEXResult(net_gamma_total=10.0, net_gamma_ce=1.0, net_gamma_pe=1.0,
                    gamma_by_strike={100.0: 10.0, 101.0: 1.0}, zero_gamma_level=None,
                    regime="Positive GEX (Stable)")
    return OptionsStructuralData(
        underlying="NSE_INDEX|Nifty 50", underlying_ltp=spot, expiry="2026-08-18",
        timestamp=datetime.now(), pcr=PCRResult(pcr=1.0, total_ce_oi=1, total_pe_oi=1),
        gex=gex, oi_analysis=OIAnalysisResult())


def test_regime_snapshot_includes_spot_and_gamma_ladder():
    snap = _regime_snapshot(_structural(spot=100.0), _chain(), rv=9.0)
    assert snap["underlying_ltp"] == 100.0
    assert snap["gamma_by_strike"] == {100.0: 10.0, 101.0: 1.0}


def _chain_with_oi():
    rows = []
    for k in (99, 100, 101):
        for t in ("CE", "PE"):
            rows.append(OptionChainRow(strike=float(k), option_type=t,
                                       instrument_key=f"{t}{k}", tradingsymbol=f"{t}{k}",
                                       expiry="2026-09-08", ltp=1.0, iv=15.0, oi=1000,
                                       volume=100, underlying_ltp=100.0))
    return rows


def test_regime_snapshot_carries_wall_metrics():
    gex = GEXResult(net_gamma_total=10.0, net_gamma_ce=1.0, net_gamma_pe=1.0,
                    gamma_by_strike={100.0: 10.0, 101.0: 1.0}, zero_gamma_level=None,
                    regime="Positive GEX (Stable)", net_gex_cr=250.0,
                    gex_cr_by_strike={100.0: 230.0, 101.0: 20.0},
                    gamma_ce_by_strike={100.0: 6.0, 101.0: 1.0},
                    gamma_pe_by_strike={100.0: 4.0}, side_coverage=0.9, side_reliable=True)
    structural = OptionsStructuralData(
        underlying="NSE_INDEX|Nifty 50", underlying_ltp=100.0, expiry="2026-09-08",
        timestamp=datetime.now(), pcr=PCRResult(pcr=1.0, total_ce_oi=1, total_pe_oi=1),
        gex=gex, oi_analysis=OIAnalysisResult())
    baseline = {(100.0, "CE"): 900, (100.0, "PE"): 1100}
    snap = _regime_snapshot(structural, _chain_with_oi(), rv=9.0, oi_baseline=baseline,
                            now=datetime(2026, 9, 2, 12, 0))
    assert snap["net_gex_cr"] == 250.0
    assert snap["pin_strike"] == 100.0 and snap["runner_up"] == 101.0
    assert snap["gex_at_pin_cr"] == 230.0
    assert snap["gamma_ceiling"] == 100.0 and snap["gamma_floor"] == 100.0
    assert 0 < snap["hhi"] <= 1
    assert snap["sigma_pts"] > 0
    assert snap["side_coverage"] == 0.9 and snap["side_reliable"] is True
    assert {r["move_pct"] for r in snap["hedge_ladder"]} == {-1.5, -1.0, -0.5, 0.5, 1.0, 1.5}
    assert snap["oi_rotation"]["by_strike"][100.0] == {"ce": 100, "pe": -100}
