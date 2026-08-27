from datetime import datetime

from core.database.ingestors.db_tick_aggregator import is_carry_forward

EQ = "NSE_EQ|INE002A01018"
IDX = "NSE_INDEX|Nifty 50"


def test_zero_volume_flat_bar_in_post_cas_auction_window_is_carry_forward():
    assert is_carry_forward(
        EQ, datetime(2026, 8, 24, 15, 20), 1304.1, 1304.1, 1304.1, 1304.1, 0
    )


def test_auction_print_is_not_carry_forward():
    assert not is_carry_forward(
        EQ, datetime(2026, 8, 24, 15, 29), 1309.8, 1309.8, 1309.8, 1309.8, 377584
    )


def test_continuous_bar_before_1515_is_not_carry_forward():
    assert not is_carry_forward(
        EQ, datetime(2026, 8, 24, 15, 14), 1305.0, 1305.1, 1302.9, 1304.1, 68944
    )


def test_pre_cas_zero_volume_bar_is_not_carry_forward():
    assert not is_carry_forward(
        EQ, datetime(2026, 7, 29, 15, 20), 1040.9, 1040.9, 1040.9, 1040.9, 0
    )


def test_index_bars_are_never_marked_because_index_volume_is_always_zero():
    # Nifty 50's real closing value on 2026-08-04 sits at 15:29 as a flat,
    # zero-volume bar. An unscoped predicate would destroy it.
    assert not is_carry_forward(
        IDX, datetime(2026, 8, 4, 15, 29), 24614.9, 24614.9, 24614.9, 24614.9, 0
    )
    assert not is_carry_forward(
        IDX, datetime(2026, 8, 4, 15, 20), 24463.45, 24463.45, 24463.45, 24463.45, 0
    )
