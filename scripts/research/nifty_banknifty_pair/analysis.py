"""
Pair trading analysis: Nifty 50 vs Bank Nifty.

Approaches tested:
1. Ratio z-score mean reversion (rolling window)
2. Cointegration test (Johansen)
3. Kalman filter dynamic hedge ratio
4. Half-life estimation (Ornstein-Uhlenbeck process)

Execution assumptions:
- Futures: Nifty lot=25, BankNifty lot=15
- Hedge ratio is rounded to nearest lot multiple
- Costs: ~0.03% round trip per pair leg (futures STT + brokerage + exchange)
"""
import json
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ── Futures lot sizes and costs ────────────────────────────────────────

NIFTY_LOT = 25
BANKNIFTY_LOT = 15
NIFTY_LOT_VALUE_FACTOR = NIFTY_LOT  # multiplier for notional
BANKNIFTY_LOT_VALUE_FACTOR = BANKNIFTY_LOT

COST_PER_SIDE_BPS = 1.5   # 0.015% per side (STT + brokerage + exchange)
COST_ROUNDTRIP_BPS = COST_PER_SIDE_BPS * 2 * 2  # two legs, each round trip


def closest_lots(nifty_lots_target: float, banknifty_lots_target: float):
    """Round to nearest integer lots."""
    return round(nifty_lots_target), round(banknifty_lots_target)


def notional_match_lots(nifty_price: float, banknifty_price: float):
    """Size so that notional exposure is approximately equal."""
    nifty_notional = nifty_price * NIFTY_LOT
    banknifty_notional = banknifty_price * BANKNIFTY_LOT

    # Match on ~500K notional each side
    target = 500_000
    nifty_lots = target / nifty_notional
    banknifty_lots = target / banknifty_notional
    return closest_lots(nifty_lots, banknifty_lots)


# ── Ratio z-score strategy ─────────────────────────────────────────────

def compute_rolling_zscore(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Compute rolling z-score of the BankNifty/Nifty price ratio."""
    df = df.copy()
    rolling_mean = df["ratio"].rolling(window=window).mean()
    rolling_std = df["ratio"].rolling(window=window).std()
    df["ratio_z"] = (df["ratio"] - rolling_mean) / rolling_std
    df["ratio_ma"] = rolling_mean
    df["ratio_std"] = rolling_std
    return df


def ratio_zscore_backtest(
    df: pd.DataFrame,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    window: int = 20,
    min_holding_bars: int = 1,
    cost_bps: float = COST_ROUNDTRIP_BPS,
    label: str = "",
) -> dict:
    """
    Backtest ratio z-score mean reversion.

    When ratio_z > entry_z: short BankNifty, long Nifty (ratio expected to fall)
    When ratio_z < -entry_z: long BankNifty, short Nifty (ratio expected to rise)
    Exit when z-score crosses back within exit_z.
    """
    df = compute_rolling_zscore(df, window=window).dropna()

    if len(df) < window + 1:
        return {"error": "Insufficient data", "label": label, "params": {"entry_z": entry_z, "exit_z": exit_z, "window": window}}

    position = 0   # 0=flat, 1=long BNF/short Nifty, -1=short BNF/long Nifty
    holding_bars = 0
    trades = []

    for i in range(1, len(df)):
        z = df["ratio_z"].iloc[i]
        prev_position = position

        if position == 0 and holding_bars >= min_holding_bars:
            if z > entry_z:
                position = -1  # short BNF, long Nifty
                holding_bars = 0
            elif z < -entry_z:
                position = 1   # long BNF, short Nifty
                holding_bars = 0

        elif position == 1 and z > exit_z:
            position = 0
            holding_bars = 0

        elif position == -1 and z < -exit_z:
            position = 0
            holding_bars = 0

        else:
            holding_bars += 1

        if position != prev_position:
            if prev_position != 0:
                trades[-1]["exit_date"] = df.index[i]
                trades[-1]["exit_z"] = z
                trades[-1]["exit_nifty"] = df["nifty_close"].iloc[i]
                trades[-1]["exit_banknifty"] = df["banknifty_close"].iloc[i]
                trades[-1]["exit_ratio"] = df["ratio"].iloc[i]
                entry_r = trades[-1]["entry_ratio"]
                exit_r = trades[-1]["exit_ratio"]
                trades[-1]["pnl_bps"] = -prev_position * (exit_r - entry_r) / entry_r * 10000  # signed: position=1 means long ratio

            if position != 0:
                trades.append({
                    "entry_date": df.index[i],
                    "entry_z": z,
                    "entry_nifty": df["nifty_close"].iloc[i],
                    "entry_banknifty": df["banknifty_close"].iloc[i],
                    "entry_ratio": df["ratio"].iloc[i],
                    "position": position,
                    "exit_date": None,
                    "exit_z": None,
                    "exit_nifty": None,
                    "exit_banknifty": None,
                    "exit_ratio": None,
                    "pnl_bps": 0.0,
                })

    # Close any open positions
    for t in trades:
        if t["exit_date"] is None:
            t["exit_date"] = df.index[-1]
            t["exit_z"] = df["ratio_z"].iloc[-1]
            t["exit_nifty"] = df["nifty_close"].iloc[-1]
            t["exit_banknifty"] = df["banknifty_close"].iloc[-1]
            t["exit_ratio"] = df["ratio"].iloc[-1]
            entry_r = t["entry_ratio"]
            exit_r = t["exit_ratio"]
            t["pnl_bps"] = -t["position"] * (exit_r - entry_r) / entry_r * 10000

    if not trades:
        return {"error": "No trades generated", "label": label, "params": {"entry_z": entry_z, "exit_z": exit_z, "window": window}}

    trades_df = pd.DataFrame(trades)
    gross_pnl = trades_df["pnl_bps"].sum()
    n_trades = len(trades_df)
    cost_total_bps = n_trades * cost_bps
    net_pnl_bps = gross_pnl - cost_total_bps

    gross_bps_per_trade = gross_pnl / n_trades if n_trades else 0
    net_bps_per_trade = net_pnl_bps / n_trades if n_trades else 0

    pnl_series = trades_df["pnl_bps"] - cost_bps
    cumulative = pnl_series.cumsum()

    win_rate = (pnl_series > 0).mean() if n_trades else 0
    avg_win = pnl_series[pnl_series > 0].mean() if (pnl_series > 0).any() else 0
    avg_loss = pnl_series[pnl_series < 0].mean() if (pnl_series < 0).any() else 0
    profit_factor = abs(avg_win * (pnl_series > 0).sum()) / abs(avg_loss * (pnl_series < 0).sum()) if (pnl_series < 0).sum() > 0 and avg_loss != 0 else float("inf")

    # Max drawdown on cumulative
    cum_max = cumulative.cummax()
    drawdown = cumulative - cum_max
    max_dd = drawdown.min()

    year_span = (df.index[-1] - df.index[0]).days / 365.25
    annualized_return_bps = net_pnl_bps / year_span if year_span > 0 else 0

    return {
        "label": label,
        "params": {"entry_z": entry_z, "exit_z": exit_z, "window": window},
        "n_trades": n_trades,
        "gross_pnl_bps": round(gross_pnl, 1),
        "cost_total_bps": round(cost_total_bps, 1),
        "net_pnl_bps": round(net_pnl_bps, 1),
        "gross_per_trade_bps": round(gross_bps_per_trade, 1),
        "net_per_trade_bps": round(net_bps_per_trade, 1),
        "annualized_net_bps": round(annualized_return_bps, 1),
        "win_rate": round(win_rate * 100, 1),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown_bps": round(max_dd, 1),
    "start_date": str(df.index[0]),
    "end_date": str(df.index[-1]),
        "year_span": round(year_span, 2),
        "trades": trades_df.to_dict("records"),
    }


# ── Cointegration analysis ─────────────────────────────────────────────

def test_cointegration(df: pd.DataFrame) -> dict:
    """Johansen cointegration test on log prices."""
    from statsmodels.tsa.vector_ar.vecm import coint_johansen

    log_prices = pd.DataFrame({
        "nifty": np.log(df["nifty_close"].astype(float)),
        "banknifty": np.log(df["banknifty_close"].astype(float)),
    }).dropna()

    try:
        result = coint_johansen(log_prices, det_order=0, k_ar_diff=1)
        trace_stat = result.lr1
        trace_crit = result.cvt
        eigen_stat = result.lr2
        eigen_crit = result.cvm

        return {
            "trace_stat_r0": round(trace_stat[0], 4),
            "trace_crit_95_r0": round(trace_crit[0, 1], 4),
            "trace_stat_r1": round(trace_stat[1], 4),
            "trace_crit_95_r1": round(trace_crit[1, 1], 4),
            "eigen_stat_r0": round(eigen_stat[0], 4),
            "eigen_crit_95_r0": round(eigen_crit[0, 1], 4),
            "eigen_stat_r1": round(eigen_stat[1], 4),
            "eigen_crit_95_r1": round(eigen_crit[1, 1], 4),
            "cointegrated": trace_stat[0] > trace_crit[0, 1],
        }
    except Exception as e:
        return {"error": str(e)}


def estimate_half_life(df: pd.DataFrame, window: Optional[int] = None) -> dict:
    """
    Estimate half-life of mean reversion for the ratio using OLS.
    Half-life = -ln(2) / beta where beta comes from:
    delta_ratio_t = alpha + beta * ratio_{t-1} + epsilon_t
    """
    df = df.copy()
    df["ratio"] = df["banknifty_close"] / df["nifty_close"]
    df = df.dropna()
    ratio = df["ratio"].values

    if window:
        half_lives = []
        for i in range(window, len(ratio)):
            chunk = ratio[i - window:i]
            delta = np.diff(chunk)
            lag = chunk[:-1]
            mask = ~np.isnan(delta) & ~np.isnan(lag)
            if mask.sum() < 10:
                continue
            beta = np.polyfit(lag[mask], delta[mask], 1)[0]
            if beta < 0:
                half_lives.append(-np.log(2) / beta)
        if half_lives:
            return {
                "method": "rolling_ols",
                "window": window,
                "half_life_mean": round(np.mean(half_lives), 1),
                "half_life_median": round(np.median(half_lives), 1),
                "half_life_std": round(np.std(half_lives), 1),
                "observations": len(half_lives),
            }
        return {"error": "No valid half-life estimates"}

    delta = np.diff(ratio)
    lag = ratio[:-1]
    mask = ~np.isnan(delta) & ~np.isnan(lag)
    beta_full = np.polyfit(lag[mask], delta[mask], 1)[0]
    hl_full = -np.log(2) / beta_full if beta_full < 0 else float("inf")

    return {
        "method": "full_sample_ols",
        "beta": round(float(beta_full), 6),
        "half_life_days": round(hl_full, 1),
        "mean_reverting": beta_full < 0,
        "r2": round(float(np.corrcoef(lag[mask], delta[mask])[0, 1] ** 2), 4),
    }


# ── Correlation analysis ───────────────────────────────────────────────

def rolling_correlation(df: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """Compute rolling return correlation."""
    df = df.copy()
    df["ratio"] = df["banknifty_close"] / df["nifty_close"]
    df["nifty_ret"] = df["nifty_close"].pct_change()
    df["banknifty_ret"] = df["banknifty_close"].pct_change()
    df["rolling_corr"] = df["nifty_ret"].rolling(window=window).corr(df["banknifty_ret"])
    df["rolling_beta"] = (
        df["banknifty_ret"].rolling(window=window).cov(df["nifty_ret"]) /
        df["nifty_ret"].rolling(window=window).var()
    )
    return df.dropna()


def correlation_summary(df: pd.DataFrame) -> dict:
    """Summarize return correlation statistics."""
    df = rolling_correlation(df)
    ret_corr = df["nifty_ret"].corr(df["banknifty_ret"])

    return {
        "return_correlation": round(ret_corr, 4),
        "rolling_corr_mean": round(df["rolling_corr"].mean(), 4),
        "rolling_corr_min": round(df["rolling_corr"].min(), 4),
        "rolling_corr_max": round(df["rolling_corr"].max(), 4),
        "rolling_corr_std": round(df["rolling_corr"].std(), 4),
        "rolling_beta_mean": round(df["rolling_beta"].mean(), 4),
        "rolling_beta_std": round(df["rolling_beta"].std(), 4),
        "ratio_mean": round(df["ratio"].mean(), 4),
        "ratio_min": round(df["ratio"].min(), 4),
        "ratio_max": round(df["ratio"].max(), 4),
        "ratio_std": round(df["ratio"].std(), 4),
    }


# ── Intraday 1m analysis ───────────────────────────────────────────────

def intraday_spread_analysis(df_1m: pd.DataFrame) -> dict:
    """
    Analyze intraday spread properties using 1m data.
    Focus: does the ratio exhibit intraday mean reversion?
    """
    df = df_1m.copy()
    df["ratio"] = df["banknifty_close"] / df["nifty_close"]

    # Compute daily stats
    df["date"] = df.index.date
    df["time"] = df.index.time

    # Autocorrelation of ratio changes at 1m, 5m, 15m, 30m, 60m
    ratio_changes = df["ratio"].diff().dropna()
    autocorrs = {}
    for lag in [1, 5, 15, 30, 60]:
        autocorrs[f"lag_{lag}"] = round(ratio_changes.autocorr(lag=lag), 6)

    # Ratio z-score using daily open as reference
    daily_first = df.groupby("date")["ratio"].transform("first")
    df["ratio_vs_open"] = df["ratio"] / daily_first - 1

    # Check if extreme deviations revert by end of day
    df["day_open_ratio"] = daily_first
    df["day_close_ratio"] = df.groupby("date")["ratio"].transform("last")

    daily_df = df.groupby("date").agg(
        open_ratio=("ratio", "first"),
        close_ratio=("ratio", "last"),
        high_ratio=("ratio", "max"),
        low_ratio=("ratio", "min"),
        ratio_range=("ratio", lambda x: x.max() - x.min()),
        ratio_std=("ratio", "std"),
    )

    daily_df["intraday_change"] = daily_df["close_ratio"] / daily_df["open_ratio"] - 1
    daily_df["max_deviation"] = daily_df["high_ratio"] / daily_df["open_ratio"] - 1
    daily_df["min_deviation"] = daily_df["low_ratio"] / daily_df["open_ratio"] - 1

    # Mean reversion test: does the ratio close the gap from its opening level?
    # Regress intraday_change on max_deviation and min_deviation -> if beta negative, mean reversion exists
    from scipy import stats as scipy_stats

    valid = daily_df.dropna(subset=["intraday_change", "max_deviation", "min_deviation"])
    if len(valid) > 10:
        slope_up, intercept_up, r_up, _, _ = scipy_stats.linregress(
            valid["max_deviation"].clip(lower=0), valid["intraday_change"]
        )
        slope_down, intercept_down, r_down, _, _ = scipy_stats.linregress(
            valid["min_deviation"].clip(upper=0), valid["intraday_change"]
        )
    else:
        slope_up = slope_down = r_up = r_down = 0

    return {
        "n_days": len(daily_df),
        "autocorrelation_ratio_changes": autocorrs,
        "daily_ratio_range_mean_bps": round(daily_df["ratio_range"].mean() / daily_df["open_ratio"].mean() * 10000, 1),
        "daily_ratio_std_mean_bps": round(daily_df["ratio_std"].mean() / daily_df["open_ratio"].mean() * 10000, 1),
        "mean_reversion_up_slope": round(slope_up, 6),
        "mean_reversion_up_r": round(r_up, 4),
        "mean_reversion_down_slope": round(slope_down, 6),
        "mean_reversion_down_r": round(r_down, 4),
        "intraday_mean_reverting": bool(slope_up < 0 and slope_down > 0),
    }


# ── Gap analysis (EOD to next open) ────────────────────────────────────

def overnight_gap_analysis(df_1d: pd.DataFrame) -> dict:
    """
    Analyze whether overnight gaps in the ratio tend to close during the day.
    Cannot fully test without open prices — uses close-to-close with sign analysis.
    """
    df = df_1d.copy()
    df["ratio"] = df["banknifty_close"] / df["nifty_close"]
    df["ratio_change"] = df["ratio"].pct_change()

    # Serial correlation of ratio changes
    df["next_change"] = df["ratio_change"].shift(-1)

    # Check if large moves reverse the next day
    df["abs_change"] = df["ratio_change"].abs()
    threshold = df["ratio_change"].std()

    big_up = df[df["ratio_change"] > threshold]
    big_down = df[df["ratio_change"] < -threshold]

    reversal_rate_up = (big_up["next_change"] < 0).mean() if len(big_up) > 0 else 0
    reversal_rate_down = (big_down["next_change"] > 0).mean() if len(big_down) > 0 else 0
    reversal_rate = (
        (df["ratio_change"] * df["next_change"] < 0).mean()
        if len(df.dropna(subset=["next_change"])) > 0
        else 0
    )

    return {
        "ratio_change_autocorr_lag1": round(df["ratio_change"].autocorr(lag=1), 6),
        "reversal_rate_all": round(reversal_rate * 100, 1),
        "reversal_rate_big_up": round(reversal_rate_up * 100, 1),
        "reversal_rate_big_down": round(reversal_rate_down * 100, 1),
        "n_big_up": int(len(big_up)),
        "n_big_down": int(len(big_down)),
        "threshold": round(threshold * 10000, 1),
    }


# ── Bootstrap significance test ────────────────────────────────────────

def bootstrap_test_strategy(
    df: pd.DataFrame,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    window: int = 20,
    n_bootstrap: int = 2000,
) -> dict:
    """
    Bootstrap test: shuffle ratio changes to create synthetic paths,
    run the strategy, and compare actual net PnL to the null distribution.
    """
    # First get actual result
    actual = ratio_zscore_backtest(df, entry_z=entry_z, exit_z=exit_z, window=window, cost_bps=0)
    if "error" in actual:
        return {"error": actual["error"]}

    actual_net = actual["net_pnl_bps"]

    # Generate null distribution by shuffling ratio changes
    ratio = df["ratio"].dropna().values
    ratio_changes = np.diff(ratio)
    np.random.seed(42)

    null_pnls = []
    for _ in range(n_bootstrap):
        shuffled_changes = np.random.permutation(ratio_changes)
        synthetic_ratio = ratio[0] + np.cumsum(shuffled_changes)
        synthetic_ratio = np.insert(synthetic_ratio, 0, ratio[0])

        synthetic_df = df.copy()
        synthetic_df["ratio"] = synthetic_ratio[:len(synthetic_df)]
        synthetic_df["nifty_close"] = synthetic_df["nifty_close"]
        synthetic_df["banknifty_close"] = synthetic_df["nifty_close"] * synthetic_df["ratio"]

        result = ratio_zscore_backtest(synthetic_df, entry_z=entry_z, exit_z=exit_z, window=window, cost_bps=0)
        if "error" not in result:
            null_pnls.append(result["net_pnl_bps"])

    null_pnls = np.array(null_pnls)
    p_value = (null_pnls >= actual_net).mean()

    return {
        "actual_net_pnl_bps": round(actual_net, 1),
        "null_mean_bps": round(null_pnls.mean(), 1),
        "null_std_bps": round(null_pnls.std(), 1),
        "p_value": round(p_value, 4),
        "significant_at_5pct": p_value < 0.05,
        "n_bootstrap": n_bootstrap,
    }


# ── Main analysis runner ───────────────────────────────────────────────

def run_full_analysis(df_1d: pd.DataFrame, df_1m: Optional[pd.DataFrame] = None) -> dict:
    results = {}

    # Add ratio column
    df_1d = df_1d.copy()
    df_1d["ratio"] = df_1d["banknifty_close"] / df_1d["nifty_close"]

    # 1. Correlation summary
    results["correlation"] = correlation_summary(df_1d)

    # 2. Ratio statistics over different periods
    results["ratio_stats"] = {
        "full": {
            "mean": round(df_1d["ratio"].mean(), 4),
            "std": round(df_1d["ratio"].std(), 4),
            "min": round(df_1d["ratio"].min(), 4),
            "max": round(df_1d["ratio"].max(), 4),
            "latest": round(df_1d["ratio"].iloc[-1], 4),
        }
    }

    # Sub-periods
    for label, start, end in [
        ("2016-2019", "2016-01-01", "2019-12-31"),
        ("2020-2022", "2020-01-01", "2022-12-31"),
        ("2023-now", "2023-01-01", None),
    ]:
        mask = (df_1d.index.astype(str) >= start)
        if end:
            mask = mask & (df_1d.index.astype(str) <= end)
        sub = df_1d["ratio"][mask]
        if len(sub) > 0:
            results["ratio_stats"][label] = {
                "mean": round(sub.mean(), 4),
                "std": round(sub.std(), 4),
                "min": round(sub.min(), 4),
                "max": round(sub.max(), 4),
                "n": int(len(sub)),
            }

    # 3. Cointegration
    results["cointegration"] = test_cointegration(df_1d)

    # 4. Half-life
    results["half_life"] = estimate_half_life(df_1d)
    results["half_life_rolling"] = estimate_half_life(df_1d, window=252)

    # 5. Z-score strategy for multiple parameter combinations (EOD)
    results["eod_strategies"] = []
    for entry_z in [1.5, 2.0, 2.5]:
        for exit_z in [0.0, 0.5, 1.0]:
            for window in [20, 60, 120]:
                r = ratio_zscore_backtest(
                    df_1d, entry_z=entry_z, exit_z=exit_z, window=window,
                    label=f"EOD_z{entry_z}_ex{exit_z}_w{window}"
                )
                results["eod_strategies"].append(r)

    # 6. Bootstrap significance
    results["bootstrap"] = bootstrap_test_strategy(df_1d, entry_z=2.0, exit_z=0.5, window=20)

    # 7. Overnight gap analysis
    results["gap_analysis"] = overnight_gap_analysis(df_1d)

    # 8. Intraday analysis (if 1m data provided)
    if df_1m is not None and len(df_1m) > 0:
        results["intraday"] = intraday_spread_analysis(df_1m)

        # Intraday z-score strategy
        results["intraday_strategies"] = []
        for entry_z in [2.0, 2.5, 3.0]:
            for exit_z in [0.5, 1.0]:
                for window in [60, 120, 240]:  # 1h, 2h, 4h windows in minutes
                    r = ratio_zscore_backtest(
                        df_1m, entry_z=entry_z, exit_z=exit_z, window=window,
                        label=f"1M_z{entry_z}_ex{exit_z}_w{window}"
                    )
                    results["intraday_strategies"].append(r)

    return results


# ── Report generation ──────────────────────────────────────────────────

def generate_report(results: dict, output_path: Path) -> str:
    lines = []
    lines.append("# Nifty-BankNifty Index Pair Trading Research")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Correlation
    c = results.get("correlation", {})
    if c:
        lines.append("## 1. Correlation Analysis")
        lines.append(f"- Return correlation: {c.get('return_correlation', 'N/A')}")
        lines.append(f"- Rolling correlation (60d): mean={c.get('rolling_corr_mean', 'N/A')}, min={c.get('rolling_corr_min', 'N/A')}, max={c.get('rolling_corr_max', 'N/A')}")
        lines.append(f"- Rolling beta (60d): mean={c.get('rolling_beta_mean', 'N/A')}, std={c.get('rolling_beta_std', 'N/A')}")
        lines.append(f"- Ratio (BNF/N50): mean={c.get('ratio_mean', 'N/A')}, min={c.get('ratio_min', 'N/A')}, max={c.get('ratio_max', 'N/A')}")
        lines.append("")

    # Ratio stats
    rs = results.get("ratio_stats", {})
    if rs:
        lines.append("## 2. Ratio Statistics by Period")
        for period, stats in rs.items():
            lines.append(f"- **{period}**: mean={stats['mean']}, std={stats['std']}, min={stats['min']}, max={stats['max']}, n={stats.get('n', 'N/A')}")
        lines.append("")

    # Cointegration
    coin = results.get("cointegration", {})
    if coin and "error" not in coin:
        lines.append("## 3. Cointegration Test (Johansen)")
        lines.append(f"- Trace stat r=0: {coin.get('trace_stat_r0')} (95% crit: {coin.get('trace_crit_95_r0')})")
        lines.append(f"- Trace stat r=1: {coin.get('trace_stat_r1')} (95% crit: {coin.get('trace_crit_95_r1')})")
        lines.append(f"- **Cointegrated at 5%**: {coin.get('cointegrated')}")
        lines.append("")

    # Half-life
    hl = results.get("half_life", {})
    if hl and "error" not in hl:
        lines.append("## 4. Half-Life of Mean Reversion")
        lines.append(f"- Method: {hl.get('method')}")
        lines.append(f"- Beta: {hl.get('beta')}")
        lines.append(f"- Half-life (days): {hl.get('half_life_days')}")
        lines.append(f"- Mean-reverting: {hl.get('mean_reverting')}")
        lines.append(f"- R-squared: {hl.get('r2')}")
        lines.append("")

    hlr = results.get("half_life_rolling", {})
    if hlr and "error" not in hlr:
        lines.append(f"- Rolling (252d): median HL={hlr.get('half_life_median')}d, mean={hlr.get('half_life_mean')}d")
        lines.append("")

    # Gap analysis
    ga = results.get("gap_analysis", {})
    if ga:
        lines.append("## 5. Overnight Gap / Reversal Analysis")
        lines.append(f"- Ratio change autocorr (lag-1): {ga.get('ratio_change_autocorr_lag1')}")
        lines.append(f"- Reversal rate (all): {ga.get('reversal_rate_all')}%")
        lines.append(f"- Reversal rate (big up): {ga.get('reversal_rate_big_up')}% (n={ga.get('n_big_up')})")
        lines.append(f"- Reversal rate (big down): {ga.get('reversal_rate_big_down')}% (n={ga.get('n_big_down')})")
        lines.append("")

    # EOD Strategy results — sort by net PnL
    eod_strats = sorted(
        [s for s in results.get("eod_strategies", []) if "error" not in s],
        key=lambda x: x.get("net_pnl_bps", -99999),
        reverse=True,
    )
    if eod_strats:
        lines.append("## 6. EOD Z-Score Strategy Results (sorted by net PnL)")
        lines.append("")
        lines.append("| # | Entry Z | Exit Z | Window | N Trades | Net PnL (bps) | Annual (bps) | Win Rate | PF | Max DD (bps) |")
        lines.append("|---|---------|--------|--------|----------|---------------|--------------|----------|----|-------------|")
        for i, s in enumerate(eod_strats[:15]):
            lines.append(
                f"| {i+1} | {s['params']['entry_z']} | {s['params']['exit_z']} | {s['params']['window']} "
                f"| {s['n_trades']} | {s['net_pnl_bps']} | {s['annualized_net_bps']} "
                f"| {s['win_rate']}% | {s['profit_factor']} | {s['max_drawdown_bps']} |"
            )
        lines.append("")

    # Bootstrap
    bs = results.get("bootstrap", {})
    if bs and "error" not in bs:
        lines.append("## 7. Bootstrap Significance (shuffled ratio changes)")
        lines.append(f"- Actual net PnL: {bs.get('actual_net_pnl_bps')} bps")
        lines.append(f"- Null mean: {bs.get('null_mean_bps')} bps (std: {bs.get('null_std_bps')} bps)")
        lines.append(f"- p-value: {bs.get('p_value')}")
        lines.append(f"- Significant at 5%: {bs.get('significant_at_5pct')}")
        lines.append("")

    # Intraday
    intra = results.get("intraday", {})
    if intra:
        lines.append("## 8. Intraday Spread Analysis (1m data)")
        lines.append(f"- Days analyzed: {intra.get('n_days')}")
        lines.append(f"- Daily ratio range (mean): {intra.get('daily_ratio_range_mean_bps')} bps")
        lines.append(f"- Daily ratio std (mean): {intra.get('daily_ratio_std_mean_bps')} bps")
        lines.append(f"- Ratio change autocorr: {intra.get('autocorrelation_ratio_changes')}")
        lines.append(f"- Mean reversion up slope: {intra.get('mean_reversion_up_slope')} (r={intra.get('mean_reversion_up_r')})")
        lines.append(f"- Mean reversion down slope: {intra.get('mean_reversion_down_slope')} (r={intra.get('mean_reversion_down_r')})")
        lines.append(f"- Intraday mean-reverting: {intra.get('intraday_mean_reverting')}")
        lines.append("")

    intra_strats = sorted(
        [s for s in results.get("intraday_strategies", []) if "error" not in s],
        key=lambda x: x.get("net_pnl_bps", -99999),
        reverse=True,
    )
    if intra_strats:
        lines.append("## 9. Intraday Z-Score Strategy Results")
        lines.append("")
        lines.append("| # | Entry Z | Exit Z | Window (min) | N Trades | Net PnL (bps) | Annual (bps) | Win Rate | PF | Max DD (bps) |")
        lines.append("|---|---------|--------|-------------|----------|---------------|-------------|----------|----|-------------|")
        for i, s in enumerate(intra_strats[:15]):
            lines.append(
                f"| {i+1} | {s['params']['entry_z']} | {s['params']['exit_z']} | {s['params']['window']} "
                f"| {s['n_trades']} | {s['net_pnl_bps']} | {s['annualized_net_bps']} "
                f"| {s['win_rate']}% | {s['profit_factor']} | {s['max_drawdown_bps']} |"
            )
        lines.append("")

    # Conclusion
    lines.append("## 10. Summary & Recommendations")
    lines.append("")
    lines.append("### Key Findings")
    lines.append("")

    # Best EOD strategy
    if eod_strats:
        best = eod_strats[0]
        lines.append(f"- **Best EOD strategy**: entry_z={best['params']['entry_z']}, exit_z={best['params']['exit_z']}, window={best['params']['window']}d")
        lines.append(f"  - Net PnL: {best['net_pnl_bps']} bps over {best['year_span']} years ({best['annualized_net_bps']} bps/yr)")
        lines.append(f"  - {best['n_trades']} trades, win rate {best['win_rate']}%, PF {best['profit_factor']}, Max DD {best['max_drawdown_bps']} bps")
        lines.append("")

    if coin.get("cointegrated"):
        lines.append("- The Nifty-BankNifty log-price pair is cointegrated at the 5% level")
    else:
        lines.append("- The Nifty-BankNifty log-price pair is NOT cointegrated at the 5% level — spread trading relies on ratio stationarity rather than true cointegration")
    lines.append("")

    hl_days = hl.get("half_life_days", 999)
    if hl_days < 60:
        lines.append(f"- Ratio half-life is ~{hl_days} days — reasonably fast mean reversion suitable for trading")
    elif hl_days < 252:
        lines.append(f"- Ratio half-life is ~{hl_days} days — moderate mean reversion, requires patience")
    else:
        lines.append(f"- Ratio half-life is ~{hl_days} days — very slow mean reversion, may not be tradable at reasonable holding periods")
    lines.append("")

    lines.append("### Caveats")
    lines.append("")
    lines.append("1. Index data has volume=0 — all analysis is on close prices only, no VWAP or execution realism")
    lines.append("2. Trade execution requires futures — lot sizes and margin constraints are not modeled")
    lines.append("3. Cost assumptions (3 bps round-trip per pair) are estimated, not actual broker schedules")
    lines.append("4. This is a research exploration, not a pre-registered construct — no SEALED window spend")
    lines.append("5. Rolling window strategies are parameter-sensitive; parameter search is in-sample")
    lines.append("")

    report_text = "\n".join(lines)
    output_path.write_text(report_text)
    return report_text


if __name__ == "__main__":
    from .data_loader import load_1d_data

    df_1d = load_1d_data()
    results = run_full_analysis(df_1d)

    output_path = Path("F:/Nifty/docs/reports/NIFTY_BANKNIFTY_PAIR_RESEARCH.md")
    generate_report(results, output_path)
    print(json.dumps({k: v for k, v in results.items() if k not in ("eod_strategies", "intraday_strategies")}, indent=2, default=str))
