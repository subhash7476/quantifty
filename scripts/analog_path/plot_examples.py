"""Visual inspection: query path vs top-5 analogues for stratified examples.

Example selection is by SIMILARITY STRATA ONLY (reference percentile:
low = high similarity, ~median = moderate, high = weak), never by outcome.
All plots use TRAIN data only.
"""
from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts.analog_path import config
from scripts.analog_path.data_layer import load_session, read_day
from scripts.analog_path.eligibility import load_eligible_dates

OUT = Path(__file__).resolve().parents[2] / "data" / "analog_path" / "plots"
GRID_TICKS = list(range(14))


def _normalize_afternoon(sess):
    bars = read_day(sess.date)
    p0 = sess.p_1230
    after = [b for b in bars if b[0].time() > time(12, 30)]
    out_t, out_v = [], []
    for b in after[::15]:
        out_t.append((b[0].hour - 12) * 60 + b[0].minute - 30)
        out_v.append(b[4] / p0 - 1.0)
    return np.asarray(out_t), np.asarray(out_v)


def plot_examples() -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    rec = pd.read_parquet(OUT.parent / "analogue_records_train_A_K5.parquet")
    rec = rec.sort_values("query_date").reset_index(drop=True)
    pct = rec["reference_percentile"].to_numpy()
    strata = {
        "high": int(np.argmin(pct)),
        "moderate": int(np.argmin(np.abs(pct - np.median(pct)))),
        "weak": int(np.argmax(pct)),
    }
    saved = []
    for name, i in strata.items():
        row = rec.iloc[i]
        qd = row["query_date"]
        qs = load_session(date.fromisoformat(qd))
        fig, ax = plt.subplots(figsize=(9, 6))
        x = np.arange(14)
        ax.plot(x, qs.path_state, "k-o", lw=2, ms=4, label=f"query {qd}")
        ax.axvline(13, color="gray", ls="--", lw=1)
        ax.text(13.05, ax.get_ylim()[0], "12:30", fontsize=8, color="gray")
        for ad in row["analogue_dates"][:5]:
            a = load_session(date.fromisoformat(ad))
            ax.plot(x, a.path_state, lw=1, alpha=0.75, label=f"{ad}")
            tx, ty = _normalize_afternoon(a)
            ax.plot(13 + tx / 15.0, ty, lw=0.8, alpha=0.35, color="tab:blue")
        ax.set_title(f"similarity stratum: {name} (ref pct {row['reference_percentile']:.3f})")
        ax.set_xlabel("grid stamp (0=09:15 ... 13=12:30; after 13: 15-min steps)")
        ax.set_ylabel("normalized return vs 09:15")
        ax.legend(fontsize=7, loc="best")
        fig.tight_layout()
        path = OUT / f"example_{name}_similarity_{qd}.png"
        fig.savefig(path, dpi=110)
        plt.close(fig)
        saved.append({"stratum": name, "query_date": qd,
                      "reference_percentile": float(row["reference_percentile"]),
                      "plot": path.name})
    with open(OUT / "examples.json", "w") as fh:
        json.dump(saved, fh, indent=1)
    return saved


if __name__ == "__main__":
    for s in plot_examples():
        print(s)
