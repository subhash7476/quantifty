"""
Rigorous train/test validation for Nifty-BankNifty pair trading.

Tests:
1. Fixed parameter train/test — find best params on 2016-2019, test on 2020-2026
2. Walk-forward — re-optimize every 2 years
3. Regime analysis — how does the strategy perform in bull/bear/sideways?
4. Additional strategies — MA crossover, breakout from range
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import numpy as np
import pandas as pd
from scripts.research.nifty_banknifty_pair.data_loader import load_1d_data
from scripts.research.nifty_banknifty_pair.analysis import (
    compute_rolling_zscore,
    ratio_zscore_backtest,
    test_cointegration,
    COST_ROUNDTRIP_BPS,
)


def train_test_validation(df: pd.DataFrame) -> dict:
    """
    Train on 2016-2019, test on 2020-2026.
    Grid search on train, fix best params, apply to test.
    Also test flipped: train on 2020-2022, test on 2023-2026.
    """
    results = {}

    splits = [
        ("2016-2019 train --> 2020-2026 test", "2016-01-01", "2019-12-31", "2020-01-01", "2026-07-31"),
        ("2020-2022 train --> 2023-2026 test", "2020-01-01", "2022-12-31", "2023-01-01", "2026-07-31"),
    ]

    for label, train_start, train_end, test_start, test_end in splits:
        mask_train = (df.index.astype(str) >= train_start) & (df.index.astype(str) <= train_end)
        mask_test = (df.index.astype(str) >= test_start) & (df.index.astype(str) <= test_end)

        df_train = df[mask_train].copy()
        df_test = df[mask_test].copy()

        if len(df_train) < 252 or len(df_test) < 252:
            results[label] = {"error": "Insufficient data"}
            continue

        # Grid search on training
        best_params = None
        best_net = -float("inf")
        grid_results = []

        for entry_z in [1.0, 1.5, 2.0, 2.5, 3.0]:
            for exit_z in [0.0, 0.5, 1.0, 1.5]:
                for window in [10, 20, 40, 60, 120]:
                    r = ratio_zscore_backtest(
                        df_train, entry_z=entry_z, exit_z=exit_z, window=window,
                        cost_bps=COST_ROUNDTRIP_BPS, label=""
                    )
                    if "error" not in r:
                        grid_results.append({
                            "entry_z": entry_z, "exit_z": exit_z, "window": window,
                            "net_pnl_bps": r["net_pnl_bps"],
                            "n_trades": r["n_trades"],
                            "win_rate": r["win_rate"],
                            "annual_bps": r["annualized_net_bps"],
                        })
                        if r["net_pnl_bps"] > best_net:
                            best_net = r["net_pnl_bps"]
                            best_params = {"entry_z": entry_z, "exit_z": exit_z, "window": window}

        # Apply best params to test
        if best_params:
            test_result = ratio_zscore_backtest(
                df_test, entry_z=best_params["entry_z"], exit_z=best_params["exit_z"],
                window=best_params["window"], cost_bps=COST_ROUNDTRIP_BPS, label=""
            )
        else:
            test_result = {"error": "No valid params found"}

        # Top 5 parameter combos
        top5 = sorted(grid_results, key=lambda x: x["net_pnl_bps"], reverse=True)[:5]

        results[label] = {
            "train_n": len(df_train),
            "test_n": len(df_test),
            "best_params": best_params,
            "best_train_net_bps": best_net if best_params else None,
            "test_result": {
                "net_pnl_bps": test_result.get("net_pnl_bps"),
                "annualized_net_bps": test_result.get("annualized_net_bps"),
                "n_trades": test_result.get("n_trades"),
                "win_rate": test_result.get("win_rate"),
                "profit_factor": test_result.get("profit_factor"),
                "max_drawdown_bps": test_result.get("max_drawdown_bps"),
            } if "error" not in test_result else {"error": test_result.get("error")},
            "top5_train": top5,
        }

    return results


def walk_forward_analysis(df: pd.DataFrame) -> dict:
    """
    Walk-forward: 2-year training, 1-year test, advance by 1 year.
    """
    results = []
    df["year"] = pd.DatetimeIndex(df.index.astype(str)).year

    train_start = 2016
    while train_start + 2 <= 2025:
        train_years = range(train_start, train_start + 2)
        test_year = train_start + 2

        mask_train = df["year"].isin(train_years)
        mask_test = df["year"] == test_year

        df_train = df[mask_train].copy()
        df_test = df[mask_test].copy()

        if len(df_train) < 252 or len(df_test) < 30:
            train_start += 1
            continue

        # Grid search on training
        best_params = None
        best_net = -float("inf")
        for entry_z in [1.0, 1.5, 2.0, 2.5]:
            for exit_z in [0.0, 0.5, 1.0]:
                for window in [10, 20, 40, 60]:
                    r = ratio_zscore_backtest(
                        df_train, entry_z=entry_z, exit_z=exit_z, window=window,
                        cost_bps=COST_ROUNDTRIP_BPS, label=""
                    )
                    if "error" not in r and r["net_pnl_bps"] > best_net:
                        best_net = r["net_pnl_bps"]
                        best_params = {"entry_z": entry_z, "exit_z": exit_z, "window": window}

        if best_params:
            test_result = ratio_zscore_backtest(
                df_test, entry_z=best_params["entry_z"], exit_z=best_params["exit_z"],
                window=best_params["window"], cost_bps=COST_ROUNDTRIP_BPS, label=""
            )
        else:
            test_result = {"error": "No valid params"}

        results.append({
            "train_years": f"{train_start}-{train_start+1}",
            "test_year": test_year,
            "best_params": best_params,
            "test_net_bps": test_result.get("net_pnl_bps", 0) if "error" not in test_result else 0,
            "test_n_trades": test_result.get("n_trades", 0) if "error" not in test_result else 0,
            "test_win_rate": test_result.get("win_rate", 0) if "error" not in test_result else 0,
            "error": "error" in test_result,
        })

        train_start += 1

    if not results:
        return {"error": "No walk-forward windows possible"}

    valid = [r for r in results if not r["error"]]
    test_nets = [r["test_net_bps"] for r in valid]
    total_test_net = sum(test_nets)
    n_test_wins = sum(1 for n in test_nets if n > 0)

    return {
        "n_windows": len(valid),
        "n_windows_positive": n_test_wins,
        "n_windows_negative": len(valid) - n_test_wins,
        "total_test_net_bps": round(total_test_net, 1),
        "mean_test_net_bps": round(np.mean(test_nets), 1) if test_nets else 0,
        "median_test_net_bps": round(np.median(test_nets), 1) if test_nets else 0,
        "windows": results,
    }


def regime_analysis(df: pd.DataFrame) -> dict:
    """
    Analyze strategy performance in different market regimes.
    Regimes defined by Nifty 50 200-day MA trend.
    """
    df = df.copy()
    df["nifty_ma200"] = df["nifty_close"].rolling(window=200).mean()
    df["regime"] = "sideways"
    df.loc[df["nifty_close"] > df["nifty_ma200"] * 1.05, "regime"] = "bull"
    df.loc[df["nifty_close"] < df["nifty_ma200"] * 0.95, "regime"] = "bear"
    df = df.dropna(subset=["nifty_ma200"])

    # Test the baseline strategy in each regime
    regimes = {}
    for regime_name in ["bull", "bear", "sideways"]:
        sub = df[df["regime"] == regime_name].copy()
        if len(sub) < 60:
            regimes[regime_name] = {"error": "Insufficient data", "n_days": len(sub)}
            continue

        r = ratio_zscore_backtest(
            sub, entry_z=1.5, exit_z=0.0, window=20, cost_bps=COST_ROUNDTRIP_BPS, label=""
        )
        if "error" not in r:
            regimes[regime_name] = {
                "n_days": len(sub),
                "n_trades": r["n_trades"],
                "net_pnl_bps": r["net_pnl_bps"],
                "annualized_net_bps": r["annualized_net_bps"],
                "win_rate": r["win_rate"],
                "max_drawdown_bps": r["max_drawdown_bps"],
            }
        else:
            regimes[regime_name] = {"error": r["error"], "n_days": len(sub)}

    return regimes


def plot_regime_distribution(df):
    """No-op — matplotlib may not be available. Just return data."""
    pass


def main():
    print("=" * 70)
    print("RIGOROUS VALIDATION: Train/Test & Regime Analysis")
    print("=" * 70)

    print("\n[1/4] Loading data...")
    df = load_1d_data(start="2016-01-01")
    df["ratio"] = df["banknifty_close"] / df["nifty_close"]
    df = df.asfreq("D").dropna(subset=["ratio"])  # Ensure daily frequency
    print(f"  {len(df)} observations, {df.index[0]} to {df.index[-1]}")

    print("\n[2/4] Train/Test validation...")
    tt = train_test_validation(df)
    for label, result in tt.items():
        if "error" in result:
            print(f"  {label}: ERROR — {result['error']}")
        else:
            bp = result.get("best_params", {})
            tr = result.get("test_result", {})
            print(f"  {label}:")
            print(f"    Best params (train): entry_z={bp.get('entry_z')}, exit_z={bp.get('exit_z')}, window={bp.get('window')}")
            print(f"    Train net: {result.get('best_train_net_bps')} bps")
            if "error" in tr:
                print(f"    Test: ERROR — {tr['error']}")
            else:
                print(f"    Test net: {tr.get('net_pnl_bps')} bps ({tr.get('annualized_net_bps')} bps/yr)")
                print(f"    Test trades: {tr.get('n_trades')}, win rate: {tr.get('win_rate')}%, PF: {tr.get('profit_factor')}")
                print(f"    Test MaxDD: {tr.get('max_drawdown_bps')} bps")

    print("\n[3/4] Walk-forward analysis...")
    wf = walk_forward_analysis(df)
    if "error" not in wf:
        print(f"  Windows: {wf['n_windows']}")
        print(f"  Positive windows: {wf['n_windows_positive']} / {wf['n_windows']}")
        print(f"  Total test net: {wf['total_test_net_bps']} bps")
        print(f"  Mean test net: {wf['mean_test_net_bps']} bps")
        print(f"  Median test net: {wf['median_test_net_bps']} bps")
        for w in wf["windows"]:
            print(f"    {w['train_years']} --> {w['test_year']}: {w['test_net_bps']:.0f} bps ({w['test_n_trades']} trades, {w['test_win_rate']:.0f}% WR)")
    else:
        print(f"  ERROR: {wf['error']}")

    print("\n[4/4] Regime analysis...")
    ra = regime_analysis(df)
    for regime, stats in ra.items():
        if "error" in stats:
            print(f"  {regime}: ERROR ({stats['n_days']}d)")
        else:
            print(f"  {regime}: {stats['n_days']}d, net={stats['net_pnl_bps']} bps ({stats['annualized_net_bps']} bps/yr), WR={stats['win_rate']}%, DD={stats['max_drawdown_bps']} bps")

    # ── Save results ──────────────────────────────────────────────────
    output = {
        "train_test": tt,
        "walk_forward": wf,
        "regime": ra,
    }

    # Make JSON-safe
    def make_safe(obj):
        if isinstance(obj, dict):
            return {k: make_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_safe(v) for v in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        return obj

    output_path = Path("F:/Nifty/docs/reports/NIFTY_BANKNIFTY_PAIR_VALIDATION.json")
    output_path.write_text(json.dumps(make_safe(output), indent=2, default=str))
    print(f"\nResults saved to: {output_path}")

    # ── Final verdict ─────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL VERDICT")
    print("=" * 70)

    # Check if any test period is significantly profitable
    test_nets = []
    for label, result in tt.items():
        if "test_result" in result and "net_pnl_bps" in result["test_result"]:
            test_nets.append(result["test_result"]["net_pnl_bps"])

    if test_nets:
        all_positive = all(n > 0 for n in test_nets)
        print(f"All test periods positive: {all_positive}")
        print(f"Test net values: {test_nets}")

    if wf and "error" not in wf:
        pos_rate = wf["n_windows_positive"] / wf["n_windows"] if wf["n_windows"] > 0 else 0
        print(f"Walk-forward positive rate: {pos_rate:.0%} ({wf['n_windows_positive']}/{wf['n_windows']})")
        print(f"Walk-forward total test net: {wf['total_test_net_bps']} bps")

    # Regime check: does it work in all regimes?
    if ra:
        regimes_ok = [regime for regime, stats in ra.items() if "error" not in stats and stats.get("net_pnl_bps", 0) > 0]
        print(f"Profitable regimes: {regimes_ok} / {list(ra.keys())}")

    print("\nRECOMMENDATION:")
    if all_positive and pos_rate > 0.5:
        print("  POTENTIAL: Strategy shows out-of-sample robustness. Proceed to deeper analysis.")
    else:
        print("  NO OPPORTUNITY: Strategy fails out-of-sample validation.")
        print("  The Nifty-BankNifty spread does NOT mean-revert reliably enough for trading.")


if __name__ == "__main__":
    main()
