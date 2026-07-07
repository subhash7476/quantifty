"""Gate (b) — NSE index-options fee model (MSRP Phase 7 precondition).

Hand-computed expectations from the statutory schedules:
  STT (sell, of premium): 0.05% -> 0.0625% (2023-04-01) -> 0.1% (2024-10-01) -> 0.15% (2026-04-01)
  NSE txn (of premium):   0.0495% -> 0.03503% (2024-10-01, true-to-label)
  SEBI: 0.0001%; stamp (buy): 0.003%; GST: 18% on (brokerage + txn + SEBI); brokerage Rs 20/order.
"""

from datetime import date

import pytest

from core.execution.options.fees import (
    exchange_txn_rate,
    option_order_fees,
    stt_sell_rate,
)


class TestRateSchedules:
    def test_stt_pre_april_2023(self):
        assert stt_sell_rate(date(2023, 3, 31)) == 0.0005

    def test_stt_april_2023_era(self):
        assert stt_sell_rate(date(2023, 4, 1)) == 0.000625
        assert stt_sell_rate(date(2024, 9, 30)) == 0.000625

    def test_stt_october_2024_era(self):
        assert stt_sell_rate(date(2024, 10, 1)) == 0.001
        assert stt_sell_rate(date(2026, 3, 31)) == 0.001

    def test_stt_april_2026_era(self):
        assert stt_sell_rate(date(2026, 4, 1)) == 0.0015

    def test_exchange_txn_legacy(self):
        assert exchange_txn_rate(date(2024, 9, 30)) == 0.000495

    def test_exchange_txn_true_to_label(self):
        assert exchange_txn_rate(date(2024, 10, 1)) == 0.0003503


class TestOptionOrderFees:
    def test_sell_order_2025(self):
        # SELL 75 units @ premium 200 on 2025-06-02: turnover 15,000
        f = option_order_fees(
            premium=200.0, quantity=75, side="SELL", trade_date=date(2025, 6, 2)
        )
        assert f.brokerage == 20.0
        assert f.stt == pytest.approx(15.0)
        assert f.exchange_txn == pytest.approx(5.2545)
        assert f.sebi == pytest.approx(0.015)
        assert f.gst == pytest.approx(0.18 * (20.0 + 5.2545 + 0.015))
        assert f.stamp_duty == 0.0
        assert f.total == pytest.approx(20.0 + 15.0 + 5.2545 + 0.015 + 4.54851)

    def test_buy_order_2025(self):
        # BUY side: no STT, stamp duty 0.003% of premium turnover
        f = option_order_fees(
            premium=200.0, quantity=75, side="BUY", trade_date=date(2025, 6, 2)
        )
        assert f.stt == 0.0
        assert f.stamp_duty == pytest.approx(0.45)
        assert f.total == pytest.approx(20.0 + 5.2545 + 0.015 + 4.54851 + 0.45)

    def test_sell_order_2023_era_rates(self):
        # 2023 era: STT 0.0625%, txn 0.0495%
        f = option_order_fees(
            premium=100.0, quantity=50, side="SELL", trade_date=date(2023, 6, 1)
        )
        assert f.stt == pytest.approx(5000 * 0.000625)
        assert f.exchange_txn == pytest.approx(5000 * 0.000495)

    def test_round_trip_long_straddle_cost_positive(self):
        # 4 orders: buy CE, buy PE, sell CE, sell PE — total must exceed 4x brokerage
        legs = [
            option_order_fees(premium=150.0, quantity=75, side="BUY", trade_date=date(2025, 1, 6)),
            option_order_fees(premium=140.0, quantity=75, side="BUY", trade_date=date(2025, 1, 6)),
            option_order_fees(premium=120.0, quantity=75, side="SELL", trade_date=date(2025, 1, 6)),
            option_order_fees(premium=160.0, quantity=75, side="SELL", trade_date=date(2025, 1, 6)),
        ]
        assert sum(f.total for f in legs) > 80.0

    def test_invalid_side_raises(self):
        with pytest.raises(ValueError):
            option_order_fees(premium=100.0, quantity=75, side="HOLD", trade_date=date(2025, 1, 6))

    def test_zero_premium_only_fixed_costs(self):
        f = option_order_fees(premium=0.0, quantity=75, side="SELL", trade_date=date(2025, 1, 6))
        assert f.total == pytest.approx(20.0 + 0.18 * 20.0)
