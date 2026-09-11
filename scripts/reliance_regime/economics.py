"""Study 2 — economic study of the long-only sma_200 book (full 2010-2026).

Cost ladder (per-leg cost in bps, applied to every entry and exit at
₹1,00,000 notional), yearly net-return table, participation, drawdown and
turnover profile. The 0 bp column is the gross ceiling; the era-accurate
delivery-fee column is reality; the ladder shows how much of the edge any
execution improvement could rescue.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.reliance_regime.data import build_panel
from scripts.reliance_regime.evaluate import backtest
from scripts.reliance_regime.signals import sma_trend
from scripts.reliance_regime.stats import block_bootstrap_ci

OUT = Path(__file__).resolve().parents[2] / "data" / "reliance_regime"
LADDER_BPS = [0, 2, 5, 10, 15, 20, 25]


def run() -> dict:
    panel = build_panel()
    sig = sma_trend(panel, 200).fillna(0.0)
    pos = sig.shift(1)
    ret = panel["ret"]
    valid = ret.notna() & pos.notna()
    pos, ret = pos[valid], ret[valid]
    strat_gross = pos * ret
    in_mkt = pos > 0.5
    buys = in_mkt.astype(int).diff().fillna(in_mkt.astype(int)).clip(lower=0)
    sells = (-in_mkt.astype(int).diff()).fillna(0.0).clip(lower=0)
    trades_per_day = (buys + sells)

    result = {"span": f"{panel.index.min()} -> {panel.index.max()}",
              "n_days": int(len(ret)),
              "in_market_fraction": float(in_mkt.mean()),
              "round_trips": int(trades_per_day.sum()),
              "trades_per_year": float(trades_per_day.sum() / len(ret) * 252),
              "cost_ladder": {}, "yearly": {}, "benchmarks": {}}

    gross_daily = strat_gross
    for bps in LADDER_BPS:
        cost = bps / 10000.0
        net = gross_daily - trades_per_day * cost
        ann = float(net.mean()) * 252
        vol = float(net.std()) * np.sqrt(252)
        eq = (1.0 + net).cumprod()
        dd = float((eq / eq.cummax() - 1.0).min())
        lo, hi = block_bootstrap_ci(net.values)
        result["cost_ladder"][f"{bps}bp"] = {
            "ann_net": ann, "sharpe_like": ann / vol if vol > 0 else None,
            "max_drawdown": dd, "ci95_lo": lo, "ci95_hi": hi,
        }

    years = pd.Series([d.year for d in ret.index], index=ret.index)
    for y, idx in years.groupby(years).groups.items():
        mask = years == y
        net = (strat_gross - trades_per_day * 0.00105)[mask]  # ~10.5bp/leg
        result["yearly"][str(y)] = {
            "n_days": int(mask.sum()),
            "in_market_fraction": float(in_mkt[mask].mean()),
            "gross_ann": float(strat_gross[mask].mean()) * 252,
            "net_ann_approx": float(net.mean()) * 252,
        }

    bh = backtest(panel, sig)
    result["benchmarks"] = {
        "always_long_gross_ann": float(ret.mean()) * 252,
        "sma200_net_ann": bh["ann_net_return"],
        "sma200_sharpe": bh["sharpe_like"],
        "sma200_maxdd": bh["max_drawdown"],
        "excess_vs_bh": bh["ann_net_return"] - float(ret.mean()) * 252,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "economics.json", "w") as fh:
        json.dump(result, fh, indent=1, default=str)
    return result


if __name__ == "__main__":
    r = run()
    print("cost ladder (per-leg):")
    for bps, v in r["cost_ladder"].items():
        print(f"  {bps:>4s}: ann={v['ann_net']*100:+7.2f}% sharpe={v['sharpe_like']:+.2f} "
              f"maxDD={v['max_drawdown']*100:+.1f}% ci=[{v['ci95_lo']*100:+.2f},{v['ci95_hi']*100:+.2f}]%")
    print("\nyearly (approx 10.5bp/leg net):")
    for y, v in r["yearly"].items():
        print(f"  {y}: inMkt={v['in_market_fraction']:.2f} gross={v['gross_ann']*100:+7.1f}% "
              f"net={v['net_ann_approx']*100:+7.1f}%")
    b = r["benchmarks"]
    print(f"\nbenchmarks: bh_gross={b['always_long_gross_ann']*100:+.2f}% "
          f"sma200_net={b['sma200_net_ann']*100:+.2f}% excess={b['excess_vs_bh']*100:+.2f}%")
