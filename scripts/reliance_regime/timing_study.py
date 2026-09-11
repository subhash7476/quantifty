"""Study 1 — intraday entry/exit timing for the long-only sma_200 book.

Trade reconstruction (causal, close-to-close): the sma_200 signal is
computed at each daily close; a trade ENTERS at the close of the first day
the signal is on (entry day E) and EXITS at the close of the first day the
signal turns off (exit day X). The original research backtest is exactly
this book with entry=close_E / exit=close_X.

Timing variants replace the entry/exit price with executable intraday
alternatives measured from the vendor 1m store (window 2015-02-02 ->
2025-08-06; days outside it fall back to the daily store and are counted):

  entry: close_E (baseline) | open_E1 | twap30_E1 | vwap_E1
         | dip_E1 (limit at open_{E+1} - 0.5 x range_E, else close)
         | low_E1 (infeasible upper bound)
  exit:  close_X (baseline) | open_X1 (signal known at close_X, exit next open)

Fees: era-accurate delivery equity costs on every leg (₹1,00,000 notional).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from core.execution.equity.delivery_fees import delivery_equity_fees
from scripts.reliance_regime.data import build_panel
from scripts.reliance_regime.intraday import (VENDOR_FIRST, VENDOR_LAST,
                                              dip_fill, profile)
from scripts.reliance_regime.signals import sma_trend

OUT = Path(__file__).resolve().parents[2] / "data" / "reliance_regime"
NOTIONAL = 100_000.0


def _fees(side: str, d) -> float:
    return delivery_equity_fees(side=side, trade_value=NOTIONAL,
                                trade_date=d).total / NOTIONAL


def _trades(panel: pd.DataFrame) -> list[dict]:
    sig = sma_trend(panel, 200).fillna(0.0)
    trades = []
    in_pos = False
    entry = None
    for d in panel.index:
        on = bool(sig.loc[d] > 0.5)
        if on and not in_pos:
            entry = d
            in_pos = True
        elif not on and in_pos:
            trades.append({"entry": entry, "exit": d})
            in_pos = False
    if in_pos:
        trades.append({"entry": entry, "exit": panel.index[-1]})
    return trades


def run() -> dict:
    panel = build_panel()
    daily = panel.reset_index().set_index("date")
    trades = _trades(panel)
    # study window: entry day within the vendor 1m span
    study = [t for t in trades if VENDOR_FIRST <= t["entry"] <= VENDOR_LAST]

    result = {"n_trades_all": len(trades), "n_trades_study": len(study),
              "window": f"{VENDOR_FIRST} -> {VENDOR_LAST}",
              "variants": {}}

    def variant(name, entry_price_fn, exit_price_fn):
        rows = []
        fallback_entries = 0
        for t in study:
            e, x = t["entry"], t["exit"]
            de = daily.loc[e]
            dx = daily.loc[x]
            pe = entry_price_fn(e, x, de, dx)
            px = exit_price_fn(e, x, de, dx)
            if pe is None or px is None:
                continue
            pe_fb = pe if profile(e, de).sourced_from == "vendor_1m" else None
            hold_ret = float(px / pe - 1.0)
            fee = _fees("BUY", e) + _fees("SELL", x)
            rows.append({
                "entry": e, "exit": x,
                "hold_days": int((x - e).days),
                "gross": hold_ret, "net": hold_ret - fee,
                "entry_fallback": pe_fb is None,
            })
        df = pd.DataFrame(rows)
        if len(df) == 0:
            return {"n": 0}
        years = (df["exit"].max() - df["entry"].min()).days / 365.25
        gross = df["gross"].mean()
        net = df["net"].mean()
        return {
            "n": int(len(df)),
            "trades_per_year": len(df) / years,
            "mean_hold_days": float(df["hold_days"].mean()),
            "mean_gross_per_trade": float(gross),
            "mean_net_per_trade": float(net),
            "ann_net": float(net) * len(df) / years,
            "win_rate": float((df["net"] > 0).mean()),
            "n_entry_fallback": int(df["entry_fallback"].sum()),
            "years": float(years),
        }

    def ent_close(e, x, de, dx):
        return float(de["close"])

    def ent_open(e, x, de, dx):
        nxt = daily.index[daily.index.get_loc(e) + 1]
        p = profile(nxt, daily.loc[nxt])
        return p.open

    def ent_twap30(e, x, de, dx):
        nxt = daily.index[daily.index.get_loc(e) + 1]
        return profile(nxt, daily.loc[nxt]).twap30

    def ent_vwap(e, x, de, dx):
        nxt = daily.index[daily.index.get_loc(e) + 1]
        return profile(nxt, daily.loc[nxt]).vwap

    def ent_dip(e, x, de, dx):
        nxt = daily.index[daily.index.get_loc(e) + 1]
        dn = daily.loc[nxt]
        limit = float(dn["open"]) - 0.5 * (float(de["high"]) - float(de["low"]))
        return dip_fill(nxt, limit, dn)

    def ent_low(e, x, de, dx):
        nxt = daily.index[daily.index.get_loc(e) + 1]
        return profile(nxt, daily.loc[nxt]).low

    def ext_close(e, x, de, dx):
        return float(dx["close"])

    def ext_open(e, x, de, dx):
        nxt = daily.index[daily.index.get_loc(x) + 1]
        return profile(nxt, daily.loc[nxt]).open

    result["variants"]["close_E / close_X (baseline)"] = variant(
        "base", ent_close, ext_close)
    result["variants"]["open_E1 / close_X"] = variant("oe", ent_open, ext_close)
    result["variants"]["twap30_E1 / close_X"] = variant("tw", ent_twap30, ext_close)
    result["variants"]["vwap_E1 / close_X"] = variant("vw", ent_vwap, ext_close)
    result["variants"]["dip_E1 / close_X"] = variant("dip", ent_dip, ext_close)
    result["variants"]["low_E1 / close_X (infeasible bound)"] = variant(
        "low", ent_low, ext_close)
    result["variants"]["close_E / open_X1"] = variant("xo", ent_close, ext_open)
    result["variants"]["open_E1 / open_X1"] = variant("oo", ent_open, ext_open)

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "timing_study.json", "w") as fh:
        json.dump(result, fh, indent=1, default=str)
    return result


if __name__ == "__main__":
    r = run()
    print(f"trades: {r['n_trades_all']} all, {r['n_trades_study']} in vendor window")
    for name, v in r["variants"].items():
        if v["n"] == 0:
            print(f"  {name}: no trades")
            continue
        print(f"  {name:38s} n={v['n']:3d} hold={v['mean_hold_days']:5.1f}d "
              f"gross={v['mean_gross_per_trade']*100:+6.2f}% "
              f"net={v['mean_net_per_trade']*100:+6.2f}% "
              f"annNet={v['ann_net']*100:+6.2f}% wr={v['win_rate']:.2f} "
              f"fb={v['n_entry_fallback']}")
