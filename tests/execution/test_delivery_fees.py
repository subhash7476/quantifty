"""Gate (d) — NSE delivery-equity fee model (CSMP precondition).

Hand-computed expectations from the statutory schedules (see delivery_fees.py docstring):

  STT (delivery, BOTH legs):    0.1% — stable since 2004-10-01.
  NSE txn (of turnover):        0.00345% -> 0.00297% (2024-10-01, SEBI MII rationalization).
  SEBI turnover:                0.0001% (Rs 10/crore), both legs.
  Stamp duty (BUY only):        0.01% pre-2020 (Maharashtra-representative assumption)
                                 -> 0.003% post-2020-07-01 (uniform central regime).
  GST / service tax:            12.36% -> 14% (2015-06) -> 14.5% (2015-11) -> 15% (2016-06)
                                 -> 18% GST (2017-07). Base = brokerage + txn + SEBI ONLY.
  Brokerage:                    Rs 0 default (discount delivery).
  DP charge:                    Rs 13.5 flat + 18% GST, SELL only, per sell line (not ad-valorem).
"""

from datetime import date

import pytest

from core.execution.equity.delivery_fees import (
    delivery_equity_fees,
    exchange_txn_rate,
    gst_rate,
    stamp_duty_rate,
    stt_delivery_rate,
    SEBI_FEE_RATE,
)


class TestRateSchedules:
    def test_stt_delivery_stable_across_dev_window(self):
        assert stt_delivery_rate(date(2013, 6, 1)) == 0.001
        assert stt_delivery_rate(date(2025, 6, 1)) == 0.001

    def test_exchange_txn_pre_oct_2024(self):
        assert exchange_txn_rate(date(2024, 9, 30)) == 0.0000345

    def test_exchange_txn_post_oct_2024(self):
        assert exchange_txn_rate(date(2024, 10, 1)) == 0.0000297
        assert exchange_txn_rate(date(2025, 6, 1)) == 0.0000297

    def test_stamp_duty_pre_2020_assumption(self):
        assert stamp_duty_rate(date(2020, 6, 30)) == 0.0001

    def test_stamp_duty_post_2020_central_regime(self):
        assert stamp_duty_rate(date(2020, 7, 1)) == 0.00003
        assert stamp_duty_rate(date(2025, 6, 1)) == 0.00003

    def test_gst_service_tax_12_36_pre_2015(self):
        assert gst_rate(date(2013, 6, 1)) == 0.1236
        assert gst_rate(date(2015, 5, 31)) == 0.1236

    def test_gst_14_from_june_2015(self):
        assert gst_rate(date(2015, 6, 1)) == 0.14
        assert gst_rate(date(2015, 11, 14)) == 0.14

    def test_gst_14_5_from_nov_2015(self):
        assert gst_rate(date(2015, 11, 15)) == 0.145
        assert gst_rate(date(2016, 5, 31)) == 0.145

    def test_gst_15_from_june_2016(self):
        assert gst_rate(date(2016, 6, 1)) == 0.15
        assert gst_rate(date(2017, 6, 30)) == 0.15

    def test_gst_18_from_july_2017(self):
        assert gst_rate(date(2017, 7, 1)) == 0.18
        assert gst_rate(date(2025, 6, 1)) == 0.18

    def test_sebi_rate_constant(self):
        assert SEBI_FEE_RATE == 0.000001


class TestDeliveryEquityFees:
    # Helper: a Rs 1,00,000 turnover leg is easy to read off the rates.
    BUY = "BUY"
    SELL = "SELL"
    V = 100_000.0

    def test_full_buy_leg_2025(self):
        # BUY Rs 1,00,000 on 2025-06-02: txn 0.00297%, stamp 0.003%, STT 0.1%, GST 18%.
        f = delivery_equity_fees(
            side=self.BUY, trade_value=self.V, trade_date=date(2025, 6, 2)
        )
        assert f.brokerage == 0.0
        assert f.stt == pytest.approx(100.0)            # 100000 * 0.001
        assert f.exchange_txn == pytest.approx(2.97)     # 100000 * 0.0000297
        assert f.sebi_fee == pytest.approx(0.10)         # 100000 * 0.000001
        assert f.stamp_duty == pytest.approx(3.0)        # 100000 * 0.00003 (buy side)
        assert f.gst == pytest.approx(0.18 * (0.0 + 2.97 + 0.10))   # 0.5526
        assert f.dp_charge == 0.0                        # buy side: no DP
        assert f.total == pytest.approx(106.6226)

    def test_full_sell_leg_2025(self):
        # SELL Rs 1,00,000 on 2025-06-02: no stamp; DP flat + GST.
        f = delivery_equity_fees(
            side=self.SELL, trade_value=self.V, trade_date=date(2025, 6, 2)
        )
        assert f.brokerage == 0.0
        assert f.stt == pytest.approx(100.0)
        assert f.exchange_txn == pytest.approx(2.97)
        assert f.sebi_fee == pytest.approx(0.10)
        assert f.stamp_duty == 0.0                       # sell side: no stamp
        assert f.gst == pytest.approx(0.5526)
        assert f.dp_charge == pytest.approx(13.5 * 1.18)  # 15.93
        assert f.total == pytest.approx(119.5526)

    def test_stt_applies_to_both_legs(self):
        # Delivery STT is on BOTH legs (unlike intraday 0.025% sell-only).
        buy = delivery_equity_fees(side=self.BUY, trade_value=50_000.0, trade_date=date(2025, 1, 6))
        sell = delivery_equity_fees(side=self.SELL, trade_value=200_000.0, trade_date=date(2025, 1, 6))
        assert buy.stt == pytest.approx(50_000.0 * 0.001)    # 50.0
        assert sell.stt == pytest.approx(200_000.0 * 0.001)  # 200.0

    def test_stamp_duty_buy_only(self):
        buy = delivery_equity_fees(side=self.BUY, trade_value=self.V, trade_date=date(2025, 1, 6))
        sell = delivery_equity_fees(side=self.SELL, trade_value=self.V, trade_date=date(2025, 1, 6))
        assert buy.stamp_duty > 0.0
        assert sell.stamp_duty == 0.0

    def test_gst_base_excludes_stt_and_stamp(self):
        # Acceptance criterion 3: GST on (brokerage + exchange_txn + sebi) ONLY.
        f = delivery_equity_fees(
            side=self.SELL, trade_value=self.V, trade_date=date(2025, 1, 6)
        )
        assert f.gst == pytest.approx(0.18 * (f.brokerage + f.exchange_txn + f.sebi_fee))
        # If STT or stamp had been in the base, gst would be materially larger.
        wrong_base = 0.18 * (f.brokerage + f.exchange_txn + f.sebi_fee + f.stt + f.stamp_duty)
        assert f.gst < wrong_base
        assert f.gst == pytest.approx(0.5526)

    def test_dp_charge_is_flat_not_ad_valorem_and_sell_only(self):
        small = delivery_equity_fees(side=self.SELL, trade_value=50_000.0, trade_date=date(2025, 1, 6))
        large = delivery_equity_fees(side=self.SELL, trade_value=500_000.0, trade_date=date(2025, 1, 6))
        buy = delivery_equity_fees(side=self.BUY, trade_value=self.V, trade_date=date(2025, 1, 6))
        # Same flat charge regardless of turnover.
        assert small.dp_charge == pytest.approx(large.dp_charge)
        assert small.dp_charge == pytest.approx(13.5 * 1.18)
        # Buy leg never pays DP.
        assert buy.dp_charge == 0.0

    def test_components_sum_to_total(self):
        f = delivery_equity_fees(
            side=self.SELL, trade_value=self.V, trade_date=date(2025, 1, 6)
        )
        assert f.total == pytest.approx(
            f.brokerage + f.stt + f.exchange_txn + f.sebi_fee
            + f.stamp_duty + f.gst + f.dp_charge
        )

    def test_era_2013_service_tax_and_pre_2020_stamp(self):
        # 2013-06-01: STT 0.1%, txn 0.00345%, stamp 0.01% (assumption), GST 12.36%.
        f = delivery_equity_fees(
            side=self.BUY, trade_value=self.V, trade_date=date(2013, 6, 1)
        )
        assert f.stt == pytest.approx(100.0)
        assert f.exchange_txn == pytest.approx(3.45)     # 100000 * 0.0000345
        assert f.sebi_fee == pytest.approx(0.10)
        assert f.stamp_duty == pytest.approx(10.0)       # 100000 * 0.0001 (pre-2020 buy)
        assert f.gst == pytest.approx(0.1236 * (0.0 + 3.45 + 0.10))  # 0.43878

    def test_era_2016_krishi_kalyan_cess(self):
        # 2016-12-15 sits in the 15% era (Krishi Kalyan Cess, 2016-06-01 -> 2017-06-30).
        f = delivery_equity_fees(
            side=self.BUY, trade_value=self.V, trade_date=date(2016, 12, 15)
        )
        assert f.stamp_duty == pytest.approx(10.0)       # still pre-2020 regime
        assert f.gst == pytest.approx(0.15 * (0.0 + 3.45 + 0.10))

    def test_era_boundary_gst_july_2017(self):
        pre = delivery_equity_fees(
            side=self.BUY, trade_value=self.V, trade_date=date(2017, 6, 30)
        )
        post = delivery_equity_fees(
            side=self.BUY, trade_value=self.V, trade_date=date(2017, 7, 1)
        )
        assert pre.gst == pytest.approx(0.15 * (3.45 + 0.10))
        assert post.gst == pytest.approx(0.18 * (3.45 + 0.10))
        assert post.gst > pre.gst

    def test_era_boundary_stamp_july_2020(self):
        pre = delivery_equity_fees(
            side=self.BUY, trade_value=self.V, trade_date=date(2020, 6, 30)
        )
        post = delivery_equity_fees(
            side=self.BUY, trade_value=self.V, trade_date=date(2020, 7, 1)
        )
        assert pre.stamp_duty == pytest.approx(10.0)
        assert post.stamp_duty == pytest.approx(3.0)

    def test_era_boundary_exchange_txn_oct_2024(self):
        pre = delivery_equity_fees(
            side=self.BUY, trade_value=self.V, trade_date=date(2024, 9, 30)
        )
        post = delivery_equity_fees(
            side=self.BUY, trade_value=self.V, trade_date=date(2024, 10, 1)
        )
        assert pre.exchange_txn == pytest.approx(3.45)
        assert post.exchange_txn == pytest.approx(2.97)

    def test_round_trip_buy_plus_sell_positive(self):
        buy = delivery_equity_fees(side=self.BUY, trade_value=self.V, trade_date=date(2025, 1, 6))
        sell = delivery_equity_fees(side=self.SELL, trade_value=self.V, trade_date=date(2025, 2, 3))
        assert (buy.total + sell.total) > 200.0  # STT alone is Rs 200 (both legs)

    def test_deterministic_same_inputs_identical_output(self):
        a = delivery_equity_fees(side=self.SELL, trade_value=123_456.78, trade_date=date(2024, 11, 5))
        b = delivery_equity_fees(side=self.SELL, trade_value=123_456.78, trade_date=date(2024, 11, 5))
        assert a == b

    def test_nonzero_brokerage_parameter(self):
        f = delivery_equity_fees(
            side=self.BUY, trade_value=self.V, trade_date=date(2025, 1, 6), brokerage=20.0
        )
        assert f.brokerage == 20.0
        # GST base now includes brokerage.
        assert f.gst == pytest.approx(0.18 * (20.0 + 2.97 + 0.10))

    def test_invalid_side_raises(self):
        with pytest.raises(ValueError):
            delivery_equity_fees(side="HOLD", trade_value=self.V, trade_date=date(2025, 1, 6))

    def test_zero_trade_value_no_turnover_costs(self):
        # With brokerage default 0, a zero-value leg carries no ad-valorem cost.
        buy = delivery_equity_fees(side=self.BUY, trade_value=0.0, trade_date=date(2025, 1, 6))
        sell = delivery_equity_fees(side=self.SELL, trade_value=0.0, trade_date=date(2025, 1, 6))
        assert buy.total == 0.0
        # Sell still pays the flat DP (a real demat debit happens on a zero-value sale too).
        assert sell.dp_charge == pytest.approx(13.5 * 1.18)
        assert sell.total == pytest.approx(sell.dp_charge)
