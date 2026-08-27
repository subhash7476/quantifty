"""Gate (a)/(b) — NSE futures fee model schedule + arithmetic tests (A construct).

Hand-computed expectations from the statutory schedules (see
core/execution/futures/futures_fees.py docstring):

  STT (futures, SELL only):    0.01% (2008-10-01) -> 0.0125% (2019-10-01)
                               -> 0.02% (2024-10-01). Zero on buy.
  NSE F&O txn (both legs):     0.0021% -> 0.00173% (2024-10-01).
  SEBI turnover:               0.0001% (Rs 10/crore), both legs.
  Stamp duty (BUY only):       0.002% both eras (Maharashtra-representative
                               pre-2020 assumption; central 0.002% post).
  GST / service tax:           12.36% -> 14% (2015-06) -> 14.5% (2015-11)
                               -> 15% (2016-06) -> 18% GST (2017-07).
                               Base = brokerage + txn + SEBI ONLY.
  Brokerage:                   min(Rs 20, 0.03% of notional) per order.
"""

from datetime import date

import pytest

from core.execution.futures.futures_fees import (
    breakeven_round_trip_bps,
    brokerage_flat,
    exchange_txn_rate,
    futures_round_trip_fees,
    gst_rate,
    stamp_duty_rate,
    stt_futures_rate,
    SEBI_FEE_RATE,
)


class TestRateSchedules:
    def test_stt_pre_2019(self):
        assert stt_futures_rate(date(2013, 6, 1)) == 0.0001
        assert stt_futures_rate(date(2019, 9, 30)) == 0.0001

    def test_stt_2019_to_2024(self):
        assert stt_futures_rate(date(2019, 10, 1)) == 0.000125
        assert stt_futures_rate(date(2024, 9, 30)) == 0.000125

    def test_stt_post_oct_2024(self):
        assert stt_futures_rate(date(2024, 10, 1)) == 0.0002
        assert stt_futures_rate(date(2025, 6, 1)) == 0.0002

    def test_exchange_txn_pre_oct_2024(self):
        assert exchange_txn_rate(date(2024, 9, 30)) == 0.000021

    def test_exchange_txn_post_oct_2024(self):
        assert exchange_txn_rate(date(2024, 10, 1)) == 0.0000173
        assert exchange_txn_rate(date(2026, 1, 1)) == 0.0000173

    def test_stamp_duty_both_eras(self):
        assert stamp_duty_rate(date(2013, 6, 1)) == 0.00002
        assert stamp_duty_rate(date(2020, 6, 30)) == 0.00002
        assert stamp_duty_rate(date(2020, 7, 1)) == 0.00002
        assert stamp_duty_rate(date(2025, 6, 1)) == 0.00002

    def test_gst_schedule_mirrors_equity_models(self):
        assert gst_rate(date(2013, 6, 1)) == 0.1236
        assert gst_rate(date(2015, 6, 1)) == 0.14
        assert gst_rate(date(2015, 11, 15)) == 0.145
        assert gst_rate(date(2016, 6, 1)) == 0.15
        assert gst_rate(date(2017, 7, 1)) == 0.18

    def test_brokerage_floor_dominates_large_tickets(self):
        assert brokerage_flat(200_000_000) == 20.0
        assert brokerage_flat(70_000) == 20.0
        assert brokerage_flat(50_000) == pytest.approx(15.0)


class TestRoundTrip:
    def test_post_oct_2024_hand_computed(self):
        d = date(2025, 6, 2)
        v = 25_000_000.0
        f = futures_round_trip_fees(entry_value=v, exit_value=v,
                                    entry_date=d)
        assert f.brokerage == 40.0                      # 20 + 20
        assert f.stt == pytest.approx(5000.0)           # 0.02% sell leg
        assert f.exchange_txn == pytest.approx(2 * v * 0.0000173)
        assert f.sebi_fee == pytest.approx(2 * v * SEBI_FEE_RATE)
        assert f.stamp_duty == pytest.approx(500.0)     # 0.002% buy leg
        gst_base = f.brokerage + f.exchange_txn + f.sebi_fee
        assert f.gst == round(0.18 * gst_base, 6)
        bps = breakeven_round_trip_bps(price=25_000.0, quantity=1000,
                                       trade_date=d)
        assert abs(bps - 10_000.0 * f.total / v) < 1e-9

    def test_stt_stamp_outside_gst_base(self):
        d = date(2025, 6, 2)
        v = 25_000_000.0
        f = futures_round_trip_fees(entry_value=v, exit_value=v,
                                    entry_date=d)
        assert f.gst == round(0.18 * (f.brokerage + f.exchange_txn
                                      + f.sebi_fee), 6)

    def test_pre_2024_era_cheaper_stt(self):
        d = date(2023, 6, 2)
        v = 25_000_000.0
        f = futures_round_trip_fees(entry_value=v, exit_value=v,
                                    entry_date=d)
        assert f.stt == pytest.approx(3125.0)           # 0.0125% sell leg
        assert f.exchange_txn == pytest.approx(2 * v * 0.000021)

    def test_2013_era_service_tax(self):
        d = date(2013, 6, 2)
        v = 10_000_000.0
        f = futures_round_trip_fees(entry_value=v, exit_value=v,
                                    entry_date=d)
        assert f.stt == pytest.approx(1000.0)           # 0.01% sell leg
        assert f.gst == pytest.approx(0.1236 * (f.brokerage + f.exchange_txn
                                                + f.sebi_fee))
        assert f.stamp_duty == pytest.approx(200.0)

    def test_canonical_notional_cost_lane(self):
        # A construct lane check: 1-lot notional at canonical capital, post-2024
        bps = breakeven_round_trip_bps(price=25_000.0, quantity=8000,
                                       trade_date=date(2026, 8, 24))
        assert 1.5 < bps < 4.0
