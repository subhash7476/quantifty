import pandas as pd

from core.analytics.day_features import drop_synthetic


def test_synthetic_bars_are_removed():
    df = pd.DataFrame({
        "close": [100.0, 101.0, 101.0],
        "is_synthetic": [False, False, True],
    })
    assert len(drop_synthetic(df)) == 2


def test_frames_without_the_column_pass_through_unchanged():
    df = pd.DataFrame({"close": [100.0, 101.0]})
    assert len(drop_synthetic(df)) == 2


def test_index_is_reset_so_positional_bar_slices_stay_valid():
    df = pd.DataFrame({
        "close": [100.0, 101.0, 102.0],
        "is_synthetic": [False, True, False],
    })
    result = drop_synthetic(df)
    assert list(result.index) == [0, 1]
