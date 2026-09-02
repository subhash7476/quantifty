"""Wall metrics: HHI, pin candidates, gamma walls, sigma, hedge ladder, OI since open."""
from datetime import date, datetime

import pytest

from core.analytics import wall_metrics as wm
from core.data.options_provider import OptionChainRow


# ---------------------------------------------------------------------- HHI

def test_hhi_is_one_for_a_single_strike_and_low_when_even():
    assert wm.hhi({100.0: 5.0}) == pytest.approx(1.0)
    assert wm.hhi({100.0: 1.0, 101.0: 1.0, 102.0: 1.0, 103.0: 1.0}) == pytest.approx(0.25)


def test_hhi_uses_absolute_shares_and_handles_empty():
    assert wm.hhi({100.0: -3.0, 101.0: 1.0}) == pytest.approx(0.625)
    assert wm.hhi({}) is None
    assert wm.hhi({100.0: 0.0}) is None


def test_hhi_band_labels():
    assert wm.hhi_band(0.30) == "COMPRESSED"
    assert wm.hhi_band(0.15) == "BALANCED"
    assert wm.hhi_band(0.05) == "DISPERSED"
    assert wm.hhi_band(None) is None


# ------------------------------------------------------------ pin candidates

def test_pin_candidates_rank_by_combined_mass_and_report_lead():
    ce = {100.0: 6.0, 101.0: 2.0, 102.0: 1.0}
    pe = {100.0: 4.0, 101.0: 4.6, 102.0: 1.0}
    out = wm.pin_candidates(ce, pe)
    assert out["pin"] == 100.0            # 10.0
    assert out["runner_up"] == 101.0      # 6.6
    assert out["margin"] == pytest.approx(34.0)         # 100 − 66
    # conviction: lead of the top over the mean of the rest, scaled 0–100
    # rest scores (pct of pin): 66, 20 → mean 43 → 57
    assert out["conviction"] == pytest.approx(57.0)
    assert out["candidates"][0] == (100.0, 100.0)
    assert out["candidates"][1] == (101.0, pytest.approx(66.0))


def test_pin_conviction_labels():
    assert wm.conviction_band(75) == "LOCKED"
    assert wm.conviction_band(50) == "CONTESTED"
    assert wm.conviction_band(10) == "DRIFTING"


def test_pin_candidates_with_single_strike_is_locked():
    out = wm.pin_candidates({100.0: 3.0}, {})
    assert out["pin"] == 100.0 and out["runner_up"] is None
    assert out["conviction"] == 100.0 and out["margin"] == 100.0


def test_pin_candidates_empty():
    assert wm.pin_candidates({}, {})["pin"] is None


# --------------------------------------------------------------- gamma walls

def test_gamma_walls_are_side_argmax():
    ceiling, floor = wm.gamma_walls({100.0: 1.0, 102.0: 5.0}, {98.0: 7.0, 100.0: 2.0})
    assert ceiling == 102.0 and floor == 98.0
    assert wm.gamma_walls({}, {}) == (None, None)


# --------------------------------------------------------------------- sigma

def test_sigma_points_scales_atm_iv_by_root_time():
    # spot 25000, IV 12%, 4 sessions of 252 → 25000 * 0.12 * sqrt(4/252)
    assert wm.sigma_points(25000.0, 12.0, 4 / 252) == pytest.approx(25000 * 0.12 * (4 / 252) ** 0.5)
    assert wm.sigma_points(25000.0, None, 4 / 252) is None


def test_time_to_expiry_years_counts_remaining_session_fraction():
    # 2 full sessions ahead plus the rest of today's 6.25h session (half left at 12:22:30)
    now = datetime(2026, 9, 2, 12, 22, 30)   # Wednesday
    tte = wm.time_to_expiry_years("2026-09-04", now)
    assert tte == pytest.approx((2 + 0.5) / 252)
    # on expiry day after close: floor, never zero
    assert wm.time_to_expiry_years("2026-09-02", datetime(2026, 9, 2, 16, 0)) > 0


# -------------------------------------------------------------- hedge ladder

def test_hedge_ladder_long_gamma_dealers_sell_rallies():
    # signed gamma units are (gamma × OI × lot): dealer delta change per 1 pt = Σ g
    spot = 100.0
    ladder = wm.hedge_ladder({100.0: 10.0}, spot)
    by_move = {row["move_pct"]: row for row in ladder}
    assert set(by_move) == {-1.5, -1.0, -0.5, 0.5, 1.0, 1.5}
    # +1% → dealer delta +10*1 = +10 units → hedge = sell 10 units → −10 × spot / 1e7 Cr
    assert by_move[1.0]["flow_cr"] == pytest.approx(-10 * 1.0 * spot / 1e7)
    assert by_move[-1.0]["flow_cr"] == pytest.approx(+10 * 1.0 * spot / 1e7)
    assert by_move[1.0]["side"] == "SELL" and by_move[-1.0]["side"] == "BUY"


def test_hedge_ladder_empty():
    assert wm.hedge_ladder({}, 100.0) == []


# ------------------------------------------------------------ OI since open

def _row(strike, otype, oi, volume=0):
    return OptionChainRow(strike=strike, option_type=otype, instrument_key=f"{otype}{strike}",
                          tradingsymbol=f"{otype}{strike}", expiry="2026-09-08",
                          oi=oi, volume=volume)


def test_oi_since_open_splits_added_and_unwound_per_strike():
    chain = [_row(100.0, "CE", 1500, volume=300), _row(100.0, "PE", 800, volume=100),
             _row(101.0, "CE", 200)]
    baseline = {(100.0, "CE"): 1000, (100.0, "PE"): 1000, (101.0, "CE"): 200}
    out = wm.oi_since_open(chain, baseline)
    assert out["added"] == 500 and out["unwound"] == 200
    assert out["by_strike"][100.0] == {"ce": 500, "pe": -200}
    assert out["by_strike"][101.0] == {"ce": 0, "pe": 0}
    assert out["total_oi"] == 2500
    assert out["vol_oi"] == pytest.approx(400 / 2500)


def test_oi_since_open_without_baseline_returns_none():
    assert wm.oi_since_open([_row(100.0, "CE", 10)], {}) is None
