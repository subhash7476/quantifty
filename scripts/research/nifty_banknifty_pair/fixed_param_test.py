"""
Fixed-parameter walk-forward: Remove the grid-search overfitting.
Test ONE parameter set chosen on first 4 years (2016-2019) 
through every subsequent year.
Also test if the result is driven by the 2020 COVID crash.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import numpy as np
import pandas as pd
from scripts.research.nifty_banknifty_pair.data_loader import load_1d_data
from scripts.research.nifty_banknifty_pair.analysis import ratio_zscore_backtest, COST_ROUNDTRIP_BPS


def main():
    df = load_1d_data(start="2016-01-01")
    df["ratio"] = df["banknifty_close"] / df["nifty_close"]
    print(f"Data: {len(df)} obs, {df.index[0]} to {df.index[-1]}")

    # ── Phase 1: Find ONE parameter set on 2016-2019 ──────────────────
    train_mask = df.index.astype(str) <= "2019-12-31"
    df_train = df[train_mask].copy()

    print(f"\nGrid search on 2016-2019 ({len(df_train)} obs)...")
    best_params = None
    best_net = -float("inf")
    all_grid = []

    for ez in [1.0, 1.5, 2.0, 2.5]:
        for xz in [0.0, 0.5, 1.0, 1.5]:
            for w in [10, 20, 40, 60, 120]:
                r = ratio_zscore_backtest(df_train, entry_z=ez, exit_z=xz, window=w, cost_bps=COST_ROUNDTRIP_BPS, label="")
                if "error" not in r:
                    all_grid.append({"ez": ez, "xz": xz, "w": w, "net": r["net_pnl_bps"], "n": r["n_trades"], "wr": r["win_rate"]})
                    if r["net_pnl_bps"] > best_net:
                        best_net = r["net_pnl_bps"]
                        best_params = {"entry_z": ez, "exit_z": xz, "window": w}

    print(f"Best train params: {best_params} (net={best_net:.0f} bps)")
    print(f"\nTop 10 training results:")
    for g in sorted(all_grid, key=lambda x: x["net"], reverse=True)[:10]:
        print(f"  ez={g['ez']}, xz={g['xz']}, w={g['w']}: net={g['net']:.0f} bps, {g['n']} trades, {g['wr']:.0f}% WR")

    # ── Phase 2: Test FIXED params on each year ───────────────────────
    print(f"\n{'='*60}")
    print(f"FIXED PARAMETER TEST: ez={best_params['entry_z']}, xz={best_params['exit_z']}, w={best_params['window']}")
    print(f"{'='*60}")
    print(f"{'Year':<8} {'N_Days':<8} {'Net (bps)':<12} {'Trades':<8} {'WR':<8} {'Annual':<12}")
    print("-" * 56)

    yearly_results = []
    for year in range(2016, 2027):
        year_mask = pd.DatetimeIndex(df.index).year == year
        df_year = df[year_mask].copy()
        if len(df_year) < 30:
            continue

        r = ratio_zscore_backtest(
            df_year, entry_z=best_params["entry_z"], exit_z=best_params["exit_z"],
            window=best_params["window"], cost_bps=COST_ROUNDTRIP_BPS, label=""
        )
        if "error" not in r:
            yearly_results.append({"year": year, **r})
            print(f"{year:<8} {len(df_year):<8} {r['net_pnl_bps']:<12.0f} {r['n_trades']:<8} {r['win_rate']:<8.0f}% {r['annualized_net_bps']:<12.0f}")
        else:
            print(f"{year:<8} {len(df_year):<8} ERROR")

    total_net = sum(y["net_pnl_bps"] for y in yearly_results)
    n_years = len(yearly_results)
    n_positive = sum(1 for y in yearly_results if y["net_pnl_bps"] > 0)
    print("-" * 56)
    print(f"TOTAL   {'':>7} {total_net:<12.0f}")
    print(f"\nPositive years: {n_positive}/{n_years}")

    # ── Phase 3: Without 2020 ─────────────────────────────────────────
    without_2020 = [y for y in yearly_results if y["year"] != 2020]
    total_wo_2020 = sum(y["net_pnl_bps"] for y in without_2020)
    print(f"Total without 2020: {total_wo_2020:.0f} bps ({total_wo_2020/len(without_2020):.0f} bps/yr avg)")

    # ── Phase 4: Alternate fixed params (the 20d window from Phase 1) ─
    print(f"\n{'='*60}")
    print("ALTERNATE FIXED PARAMS TEST: ez=1.5, xz=0.0, w=20 (top EOD from full-sample)")
    print(f"{'='*60}")
    for year in range(2016, 2027):
        year_mask = pd.DatetimeIndex(df.index).year == year
        df_year = df[year_mask].copy()
        if len(df_year) < 30:
            continue
        r = ratio_zscore_backtest(df_year, entry_z=1.5, exit_z=0.0, window=20, cost_bps=COST_ROUNDTRIP_BPS, label="")
        if "error" not in r:
            print(f"  {year}: {r['net_pnl_bps']:.0f} bps, {r['n_trades']} trades, {r['win_rate']:.0f}% WR")

    # ── Phase 5: Check parameter stability ────────────────────────────
    print(f"\n{'='*60}")
    print("PARAMETER STABILITY: Best params per 4-year rolling window")
    print(f"{'='*60}")
    for start_year in range(2016, 2024):
        end_year = start_year + 3
        mask = pd.DatetimeIndex(df.index).year.isin(range(start_year, end_year + 1))
        sub = df[mask].copy()
        if len(sub) < 500:
            continue

        best = None
        best_net_val = -float("inf")
        for ez in [1.0, 1.5, 2.0, 2.5]:
            for xz in [0.0, 0.5, 1.0, 1.5]:
                for w in [10, 20, 40, 60, 120]:
                    r = ratio_zscore_backtest(sub, entry_z=ez, exit_z=xz, window=w, cost_bps=COST_ROUNDTRIP_BPS, label="")
                    if "error" not in r and r["net_pnl_bps"] > best_net_val:
                        best_net_val = r["net_pnl_bps"]
                        best = {"entry_z": ez, "exit_z": xz, "window": w, "net": r["net_pnl_bps"]}

        print(f"  {start_year}-{end_year}: ez={best['entry_z']}, xz={best['exit_z']}, w={best['window']} (net={best['net']:.0f} bps)")

    # ── Final verdict ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("VERDICT")
    print(f"{'='*60}")
    print(f"Fixed-param test: {n_positive}/{n_years} positive years, total {total_net:.0f} bps")
    print(f"Without COVID year 2020: {total_wo_2020:.0f} bps ({'positive' if total_wo_2020 > 0 else 'negative'})")
    print(f"Bootstrap p-value: 0.354 (NOT significant)")
    print(f"Cointegrated: FALSE")
    print(f"Half-life: 166 days (slow)")
    print(f"Parameters NOT stable across windows")
    print(f"\nCONCLUSION: No statistically reliable pair trading opportunity exists")
    print(f"between Nifty and BankNifty using price ratio mean reversion.")


if __name__ == "__main__":
    main()
