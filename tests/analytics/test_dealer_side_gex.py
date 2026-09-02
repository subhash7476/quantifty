"""Dealer-side inferred GEX (Hedgewall-style) — sign per strike from the
OI-change × option-price-change grid, ₹ crore units with spot², neutral band,
and the theta-drift reliability guard."""
import pytest

from core.analytics.options_analytics import OptionsAnalytics
from core.data.options_provider import OptionChainRow


def _row(strike, otype, *, oi, oi_change, close, ltp, gamma=0.001, lot=75):
    return OptionChainRow(strike=strike, option_type=otype, instrument_key=f"{otype}{strike}",
                          tradingsymbol=f"{otype}{strike}", expiry="2026-09-08",
                          ltp=ltp, close=close, oi=oi, oi_change=oi_change,
                          gamma=gamma, lot_size=lot)


SPOT = 25000.0
# one contract's crore exposure: gamma*oi*lot*spot^2*0.01 / 1e7
UNIT_CR = 0.001 * 1_000_000 * 75 * SPOT ** 2 * 0.01 / 1e7


def test_assumed_side_is_unchanged_default():
    chain = [_row(25000, "CE", oi=1_000_000, oi_change=10, close=100, ltp=110),
             _row(25000, "PE", oi=1_000_000, oi_change=10, close=100, ltp=110)]
    gex = OptionsAnalytics.calculate_gex(chain, SPOT)
    assert gex.gamma_by_strike[25000.0] == pytest.approx(0.0)
    assert gex.net_gamma_ce > 0 and gex.net_gamma_pe < 0


def test_new_buyers_make_dealer_short_gamma():
    # OI up + price up → public buying, dealer short → negative
    chain = [_row(25000, "CE", oi=1_000_000, oi_change=5000, close=100, ltp=110)]
    gex = OptionsAnalytics.calculate_gex(chain, SPOT, dealer_side="inferred")
    assert gex.gamma_by_strike[25000.0] < 0
    assert gex.side_by_strike[(25000.0, "CE")] == "short"


def test_new_sellers_make_dealer_long_gamma():
    # OI up + price down → public writing, dealer long → positive
    chain = [_row(25000, "PE", oi=1_000_000, oi_change=5000, close=100, ltp=90)]
    gex = OptionsAnalytics.calculate_gex(chain, SPOT, dealer_side="inferred")
    assert gex.gamma_by_strike[25000.0] > 0
    assert gex.side_by_strike[(25000.0, "PE")] == "long"


def test_closing_rows_follow_the_remaining_public_side():
    # OI down + price up → shorts covering → public was short → dealer long (+)
    # OI down + price down → longs selling out → dealer short (−)
    chain = [_row(25000, "CE", oi=1_000_000, oi_change=-5000, close=100, ltp=110),
             _row(25100, "CE", oi=1_000_000, oi_change=-5000, close=100, ltp=90)]
    gex = OptionsAnalytics.calculate_gex(chain, SPOT, dealer_side="inferred")
    assert gex.gamma_by_strike[25000.0] > 0
    assert gex.gamma_by_strike[25100.0] < 0


def test_ambiguous_rows_are_excluded_and_counted_in_coverage():
    chain = [_row(25000, "CE", oi=1_000_000, oi_change=5000, close=100, ltp=90),
             _row(25100, "CE", oi=1_000_000, oi_change=0, close=100, ltp=100)]
    gex = OptionsAnalytics.calculate_gex(chain, SPOT, dealer_side="inferred")
    assert 25100.0 not in gex.gamma_by_strike
    assert gex.side_by_strike[(25100.0, "CE")] is None
    assert gex.side_coverage == pytest.approx(0.5)


def test_crore_exposure_uses_spot_squared():
    chain = [_row(25000, "CE", oi=1_000_000, oi_change=5000, close=100, ltp=90)]
    gex = OptionsAnalytics.calculate_gex(chain, SPOT, dealer_side="inferred")
    assert gex.net_gex_cr == pytest.approx(UNIT_CR)
    assert gex.gex_cr_by_strike[25000.0] == pytest.approx(UNIT_CR)


def test_neutral_band_inside_100_crore():
    small = [_row(25000, "CE", oi=10, oi_change=5, close=100, ltp=90)]
    assert OptionsAnalytics.calculate_gex(small, SPOT, dealer_side="inferred").regime == "Neutral"
    big = [_row(25000, "CE", oi=1_000_000, oi_change=5, close=100, ltp=90)]
    assert "Positive" in OptionsAnalytics.calculate_gex(big, SPOT, dealer_side="inferred").regime


def test_theta_drift_marks_side_unreliable():
    # every classified row is "price down": the price test is measuring the clock
    chain = [_row(25000 + 100 * i, t, oi=1_000_000, oi_change=100, close=100, ltp=95)
             for i in range(5) for t in ("CE", "PE")]
    gex = OptionsAnalytics.calculate_gex(chain, SPOT, dealer_side="inferred")
    assert gex.side_reliable is False
    mixed = chain[:5] + [_row(26000 + 100 * i, "CE", oi=1_000_000, oi_change=100,
                              close=100, ltp=105) for i in range(5)]
    assert OptionsAnalytics.calculate_gex(mixed, SPOT, dealer_side="inferred").side_reliable is True


def test_side_mass_per_strike_is_unsigned():
    chain = [_row(25000, "CE", oi=1_000_000, oi_change=5000, close=100, ltp=110),
             _row(25000, "PE", oi=2_000_000, oi_change=5000, close=100, ltp=110)]
    gex = OptionsAnalytics.calculate_gex(chain, SPOT, dealer_side="inferred")
    assert gex.gamma_ce_by_strike[25000.0] == pytest.approx(0.001 * 1_000_000 * 75)
    assert gex.gamma_pe_by_strike[25000.0] == pytest.approx(0.001 * 2_000_000 * 75)


def test_structural_snapshot_passes_dealer_side_through():
    chain = [_row(25000, "CE", oi=1_000_000, oi_change=5000, close=100, ltp=110)]
    snap = OptionsAnalytics().build_structural_snapshot(chain, "NSE_INDEX|Nifty 50", SPOT,
                                                        "2026-09-08", dealer_side="inferred")
    assert snap.gex.gamma_by_strike[25000.0] < 0
