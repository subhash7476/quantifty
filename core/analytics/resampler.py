import pandas as pd


def resample_ohlcv(df_1m: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """Resample 1m OHLCV to any target timeframe, preserving trading integrity.

    - Groups by session date first (no overnight bars)
    - Aggregation: open=first, high=max, low=min, close=last, volume=sum
    - Supported: 5m, 15m, 30m, 1h, 4h, 1d
    - Returns 1m data unchanged if target_tf == '1m'
    - Accepts timestamp as either a column or DatetimeIndex
    - Always returns timestamp as a column (not index)
    """
    if target_tf == "1m" or not target_tf:
        return df_1m

    df = df_1m.copy()

    ts_was_column = False
    if not isinstance(df.index, pd.DatetimeIndex):
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")
            ts_was_column = True
        else:
            raise ValueError("DataFrame must have a 'timestamp' column or a DatetimeIndex")

    tf_map = {
        "5m": "5min",
        "10m": "10min",
        "15m": "15min",
        "30m": "30min",
        "1h": "60min",
        "4h": "240min",
        "1d": "1D",
    }
    freq = tf_map.get(target_tf, target_tf)

    agg_dict = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    if "symbol" in df.columns:
        agg_dict["symbol"] = "first"

    def resample_session(group):
        resampled = group.resample(freq, closed="left", label="left", offset="15min").agg(agg_dict)
        return resampled.dropna(subset=["open"])

    df_resampled = df.groupby(df.index.date, group_keys=False).apply(resample_session)
    df_resampled = df_resampled.reset_index()
    if "index" in df_resampled.columns:
        df_resampled = df_resampled.rename(columns={"index": "timestamp"})
    if "timestamp" not in df_resampled.columns:
        first_col = df_resampled.columns[0]
        if pd.api.types.is_datetime64_any_dtype(df_resampled[first_col]):
            df_resampled = df_resampled.rename(columns={first_col: "timestamp"})

    return df_resampled.reset_index(drop=True)
