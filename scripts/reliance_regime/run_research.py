"""RELIANCE regime research orchestrator.

Loads the aligned panel, builds the frozen signal slate, evaluates every
signal Long/Flat on three pre-specified panels (DEV 2010-2019, VAL
2020-2022, RECENT 2023+), and writes a JSON snapshot plus a markdown
report. Research only — no live/paper path, no position sizing beyond the
binary long/flat convention.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.reliance_regime.data import build_panel
from scripts.reliance_regime.evaluate import backtest, regime_buckets
from scripts.reliance_regime.signals import build_signals

OUT = Path(__file__).resolve().parents[2] / "data" / "reliance_regime"
PANELS = {"dev": "2010-01-01", "validation": "2020-01-01",
          "recent": "2023-01-01"}


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    panel = build_panel()
    sigs = build_signals(panel)
    result = {
        "instrument": "RELIANCE (NSE, delivery equity, CA-adjusted)",
        "span": f"{panel.index.min()} -> {panel.index.max()}",
        "n_rows": len(panel),
        "panels": {},
    }
    for name, start in PANELS.items():
        end = {"dev": "2019-12-31", "validation": "2022-12-31",
               "recent": "2099-12-31"}[name]
        mask = (panel.index >= pd.Timestamp(start).date()) & \
               (panel.index <= pd.Timestamp(end).date())
        p = panel[mask]
        result["panels"][name] = {
            "span": f"{p.index.min()} -> {p.index.max()}",
            "n_rows": int(len(p)),
            "signals": {},
        }
        for sname, sig in sigs.items():
            s = sig[mask]
            b = backtest(p, s)
            rb = regime_buckets(p, s)
            result["panels"][name]["signals"][sname] = {**b, "regime": rb}
    with open(OUT / "results.json", "w") as fh:
        json.dump(result, fh, indent=1, default=str)
    panel.to_parquet(OUT / "panel.parquet")
    sigs.to_parquet(OUT / "signals.parquet")
    return result


if __name__ == "__main__":
    run()
    print("written:", OUT)
