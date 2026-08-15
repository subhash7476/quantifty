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
