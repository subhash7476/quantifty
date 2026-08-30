"""MRLC-test slippage repricer: re-price every trade at 0/5/10/20 bp per side.

Fills adjust: entry + slip, exits - slip (stop/target/timeout/close all receive
less). 1R recomputed from slippage-adjusted entry and stop. Fees recomputed on
adjusted values. Output: data/mrlc_test/slippage_summary.csv + console.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.equity.delivery_fees import delivery_equity_fees  # noqa: E402

OUT_DIR = ROOT / "data" / "mrlc_test"
NOTIONAL = 100_000.0
SLIPS = (0, 5, 10, 20)
THRESHOLDS = (10.0, 15.0)

SETS = [
    ("main_guard", OUT_DIR / "trades_2_0_guard.csv"),
    ("main_unguard", OUT_DIR / "trades_2_0.csv"),
    ("ext_guard", OUT_DIR / "trades_ext_2_0_guard.csv"),
    ("ext_unguard", OUT_DIR / "trades_ext_2_0.csv"),
    ("main_guard_1_5", OUT_DIR / "trades_1_5_guard.csv"),
    ("ext_guard_1_5", OUT_DIR / "trades_ext_1_5_guard.csv"),
]


def repricerow(t, s):
    entry_f = t["entry"] * (1 + s)
    stop_f = t["sl"] * (1 - s)
    one_r = entry_f - stop_f
    shares = NOTIONAL / entry_f
    fees = delivery_equity_fees(side="BUY", trade_value=entry_f * shares,
                                trade_date=pd.Timestamp(t["entry_date"]).date()).total
    if t["reason1"] == "TP1":
        tp_f = t["tp"] * (1 - s)
        exit2_f = t["exit2_price"] * (1 - s)
        fees += delivery_equity_fees(side="SELL", trade_value=tp_f * 0.5 * shares,
                                     trade_date=pd.Timestamp(t["exit1_date"]).date()).total
        fees += delivery_equity_fees(side="SELL", trade_value=exit2_f * 0.5 * shares,
                                     trade_date=pd.Timestamp(t["exit2_date"]).date()).total
        gross = 0.5 * shares * (tp_f - entry_f) + 0.5 * shares * (exit2_f - entry_f)
        r_gross = 0.5 * (tp_f - entry_f) / one_r + 0.5 * (exit2_f - entry_f) / one_r
    else:
        exit_f = t["exit1_price"] * (1 - s)
        fees += delivery_equity_fees(side="SELL", trade_value=exit_f * shares,
                                     trade_date=pd.Timestamp(t["exit1_date"]).date()).total
        gross = (exit_f - entry_f) * shares
        r_gross = (exit_f - entry_f) / one_r
    net = gross - fees
    r_net = net / (one_r * shares)
    return r_gross, r_net


def main():
    rows = []
    for tag, path in SETS:
        if not path.exists():
            print(f"  (missing {path.name})")
            continue
        df = pd.read_csv(path)
        for tf in df["tf"].unique():
            for t in THRESHOLDS:
                sub = df[(df["tf"] == tf) & (df["divergence_pct"] <= -t)]
                if len(sub) < 5:
                    continue
                for s in SLIPS:
                    res = sub.apply(lambda r: repricerow(r, s / 10000), axis=1)
                    rg = res.apply(lambda x: x[0])
                    rn = res.apply(lambda x: x[1])
                    rows.append(dict(tag=tag, tf=tf, threshold=t, slip_bp=s,
                                     n=len(sub), exp_net=rn.mean(),
                                     total_net=rn.sum(), exp_gross=rg.mean(),
                                     win_rate=(rn > 0).mean() * 100))
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "slippage_summary.csv", index=False)
    print("SLIPPAGE SUMMARY (net expectancy per trade)")
    print(out[(out["tag"] == "main_guard") & (out["threshold"] == 10.0)]
          .pivot(index="tf", columns="slip_bp", values="exp_net")
          .round(3).to_string())
    print(out[(out["tag"] == "main_guard") & (out["threshold"] == 15.0)]
          .pivot(index="tf", columns="slip_bp", values="exp_net")
          .round(3).to_string())
    print(out[(out["tag"] == "ext_guard") & (out["threshold"] == 15.0)]
          .pivot(index="tf", columns="slip_bp", values="exp_net")
          .round(3).to_string())
    print(f"summary -> {OUT_DIR / 'slippage_summary.csv'}")


if __name__ == "__main__":
    main()
