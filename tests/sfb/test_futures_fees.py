"""Tests for core/execution/futures/futures_fees.py — era-accurate futures fee model.

Expected values are independently sourced from circulars, not read from the
module being tested.
  - STT: pre-2024-10-01 = 0.0125%, post-2024-10-01 = 0.02%.
         Source: Budget 2024 / Finance (No.2) Act 2024 (caclubindia, ICICI Direct).
  - Exchange txn: pre-2024-10-01 = 0.00210%, post-2024-10-01 = 0.00189%.
         Source: NSE circulars, SEBI MII rationalization.
  - SEBI fee: 0.0001% stable. Source: SEBI (Turnover Fees) Regulations.
  - Stamp duty: post-2020-07-01 = 0.002%, pre = 0.01% (Maharashtra rep).
  - GST: 18% from 2017-07-01. Source: GST Act.
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.futures import futures_fees as FF


# --- STT (from circulars, not from the module) ---
# Corrected: pre-hike = 0.0125%, post-2024-10-01 = 0.02%

def test_stt_sell_only_post_hike():
    f = FF.futures_fees(side="SELL", trade_value=100000, trade_date=date(2025, 1, 1))
    assert abs(f.stt - 20.0) < 0.01  # 0.02% of 1L = Rs 20
    f_buy = FF.futures_fees(side="BUY", trade_value=100000, trade_date=date(2025, 1, 1))
    assert f_buy.stt == 0.0


def test_stt_sell_only_pre_hike():
    f = FF.futures_fees(side="SELL", trade_value=100000, trade_date=date(2024, 9, 30))
    assert abs(f.stt - 12.5) < 0.01  # 0.0125% of 1L = Rs 12.5


def test_stt_pre_2008():
    f = FF.futures_fees(side="SELL", trade_value=100000, trade_date=date(2008, 5, 31))
    assert f.stt == 0.0


def test_stt_post_2008_pre_hike():
    f = FF.futures_fees(side="SELL", trade_value=100000, trade_date=date(2008, 6, 1))
    assert abs(f.stt - 12.5) < 0.01  # 0.0125%


def test_stt_2024_oct_boundary():
    f_pre = FF.futures_fees(side="SELL", trade_value=100000, trade_date=date(2024, 9, 30))
    f_post = FF.futures_fees(side="SELL", trade_value=100000, trade_date=date(2024, 10, 1))
    assert abs(f_pre.stt - 12.5) < 0.01
    assert abs(f_post.stt - 20.0) < 0.01


# --- Exchange transaction charge ---

def test_exchange_txn_pre_mii():
    f = FF.futures_fees(side="BUY", trade_value=100000, trade_date=date(2024, 9, 30))
    assert abs(f.exchange_txn - 2.10) < 0.01  # 0.00210%


def test_exchange_txn_post_mii():
    f = FF.futures_fees(side="BUY", trade_value=100000, trade_date=date(2024, 10, 1))
    assert abs(f.exchange_txn - 1.89) < 0.01  # 0.00189%


# --- SEBI fee ---

def test_sebi_fee():
    f = FF.futures_fees(side="BUY", trade_value=100000, trade_date=date(2025, 1, 1))
    assert abs(f.sebi_fee - 0.10) < 0.001  # 0.0001%


# --- Stamp duty ---

def test_stamp_duty_buy_only():
    f_buy = FF.futures_fees(side="BUY", trade_value=100000, trade_date=date(2025, 1, 1))
    assert abs(f_buy.stamp_duty - 2.0) < 0.01  # 0.002% of 1L
    f_sell = FF.futures_fees(side="SELL", trade_value=100000, trade_date=date(2025, 1, 1))
    assert f_sell.stamp_duty == 0.0


def test_stamp_duty_pre_2020():
    f = FF.futures_fees(side="BUY", trade_value=100000, trade_date=date(2020, 6, 30))
    assert abs(f.stamp_duty - 10.0) < 0.01  # 0.01% rep rate


def test_stamp_duty_post_2020():
    f = FF.futures_fees(side="BUY", trade_value=100000, trade_date=date(2020, 7, 1))
    assert abs(f.stamp_duty - 2.0) < 0.01  # 0.002%


# --- GST ---

def test_gst_18pct():
    assert abs(FF.gst_rate(date(2025, 1, 1)) - 0.18) < 0.001


# --- Validation ---

def test_invalid_side():
    try:
        FF.futures_fees(side="HOLD", trade_value=100000, trade_date=date(2025, 1, 1))
        assert False, "expected ValueError"
    except ValueError:
        pass


# --- Internal consistency ---

def test_total_components():
    f = FF.futures_fees(side="BUY", trade_value=100000, trade_date=date(2025, 1, 1),
                        brokerage=20.0)
    expected = f.brokerage + f.stt + f.exchange_txn + f.sebi_fee + f.stamp_duty + f.gst
    assert abs(f.total - expected) < 0.001


def test_brokerage_default():
    f = FF.futures_fees(side="BUY", trade_value=100000, trade_date=date(2025, 1, 1))
    assert f.brokerage == 20.0


def test_brokerage_override():
    f = FF.futures_fees(side="BUY", trade_value=100000, trade_date=date(2025, 1, 1),
                        brokerage=50.0)
    assert f.brokerage == 50.0
