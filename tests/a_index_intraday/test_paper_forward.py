"""A — forward paper runner unit tests (frozen book logic).

Covers the pure decision/bookkeeping functions; the I/O seam (fills, TI,
ledger) is exercised by the runner's dry-run in integration, not here.
"""

from datetime import date

import pytest

from scripts.a_index_intraday.run_paper_forward import (
    CANONICAL, decide, leg_fee_rs, session_record,
)


class TestLegFees:
    def test_buy_leg_has_no_stt(self):
        f = leg_fee_rs("BUY", 20_000_000.0, date(2026, 8, 24))
        assert f > 0
        assert f < 6000.0

    def test_sell_leg_has_stt(self):
        b = leg_fee_rs("BUY", 20_000_000.0, date(2026, 8, 24))
        s = leg_fee_rs("SELL", 20_000_000.0, date(2026, 8, 24))
        assert s > b                       # STT 0.02% sell-side dominates

    def test_era_rates_change_fees(self):
        s24 = leg_fee_rs("SELL", 20_000_000.0, date(2026, 8, 24))   # 0.02%
        s18 = leg_fee_rs("SELL", 20_000_000.0, date(2018, 6, 1))    # 0.01%
        assert s18 < s24


class TestDecide:
    def test_positive_feature_buys(self):
        side, qty = decide(100.0, 101.0, 100.5)
        assert side == "BUY"
        assert qty == int(CANONICAL / 100.5)

    def test_negative_feature_sells(self):
        side, _ = decide(100.0, 99.0, 100.5)
        assert side == "SELL"

    def test_zero_feature_flat(self):
        side, qty = decide(100.0, 100.0, 100.5)
        assert side is None and qty == 0

    def test_bad_prices_flat(self):
        assert decide(0.0, 101.0, 100.5)[0] is None
        assert decide(100.0, 0.0, 100.5)[0] is None


class TestSessionRecord:
    def test_long_profit(self):
        r = session_record(date(2026, 8, 24), "BUY", 100.0, 101.0, 200_000,
                           100.0, 120.0)
        assert r["gross_bp"] == pytest.approx(100.0)     # +1% = 100 bp
        fee_bp = (100.0 + 120.0) / (200_000 * 100.0) * 1e4
        assert r["fee_bp"] == pytest.approx(fee_bp)
        assert r["net_bp"] == pytest.approx(100.0 - fee_bp)
        assert r["era"] == "cas"

    def test_short_loss(self):
        r = session_record(date(2026, 8, 24), "SELL", 100.0, 101.0, 200_000,
                           100.0, 120.0)
        assert r["gross_bp"] == pytest.approx(-100.0)

    def test_era_2018_vendor(self):
        r = session_record(date(2018, 6, 1), "BUY", 100.0, 101.0, 200_000,
                           100.0, 120.0)
        assert r["era"] == "vendor"
