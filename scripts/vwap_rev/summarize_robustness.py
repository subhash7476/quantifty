"""Render the robustness grid (post-primary, non-classifying) into results/ROBUSTNESS.md."""
from __future__ import annotations

import pandas as pd

from scripts.vwap_rev import classify as K
from scripts.vwap_rev.robustness import VARIANTS
from scripts.vwap_rev.run_primary import RESULT_DIR, cells_path

STAGES = ("TRAIN", "VAL", "HOLDOUT")


def cell(r) -> str:
    if pd.isna(r.session_mean_bp):
        return "n/a"
    return f"{r.session_mean_bp:+.1f} ({r.p_one_nw:.3f})"


def load(name: str, stage: str) -> pd.DataFrame:
    return pd.read_csv(cells_path("primary", stage) if name == "primary"
                       else RESULT_DIR / f"robust_{name}_{stage}_cells.csv")


def variant_table(name: str) -> str:
    tabs = {s: load(name, s) for s in STAGES}
    base = tabs["VAL"][tabs["VAL"].side != "pooled"]
    rows = []
    for r in base.itertuples():
        row = {"side": r.side, "H": r.H}
        for s in STAGES:
            t = tabs[s]
            m = t[(t.side == r.side) & (t.H == r.H)].iloc[0]
            row[s] = cell(m) + f" n={int(m.n_events)}"
        rows.append(row)
    df = pd.DataFrame(rows)
    lines = ["| side | H | TRAIN mean bp (p) | VAL mean bp (p) | HOLDOUT mean bp (p) |", "|---|---|---|---|---|"]
    for r in df.itertuples():
        lines.append(f"| {r.side} | {r.H} | {r.TRAIN} | {r.VAL} | {r.HOLDOUT} |")
    return "\n".join(lines)


def main() -> None:
    parts = ["# VWAP-XREV-1 — post-primary robustness grid (DISCLOSURE ONLY, NON-CLASSIFYING)\n",
             "Cell format: session-mean gross bp in the reversion direction (one-sided NW p), n events. "
             "`primary` is the frozen experiment. Nothing here can change the label or be promoted.\n",
             "## Label the FROZEN tree would give each variant (illustrative, not a classification)\n",
             "| variant | VAL-confirmed cells | HOLDOUT-confirmed (VAL-conditional Holm) | tree output (no delay-2 qualifier, no economics) |",
             "|---|---|---|---|"]
    for name in ["primary"] + [v for v in VARIANTS if v != "extra_h"]:
        try:
            val, hold = load(name, "VAL"), load(name, "HOLDOUT")
        except FileNotFoundError:
            continue
        v = K.val_confirmed(val)
        clean, _ = K.holdout_confirmed(v, hold, None)
        res = K.classify(val, hold, None, {})
        parts.append(f"| {name} | {', '.join(f'{s}/h{h}' for s, h in v) or 'none'} | "
                     f"{', '.join(f'{s}/h{h}' for s, h in clean) or 'none'} | {res['label']} |")
    for name in ["primary"] + list(VARIANTS):
        try:
            parts += [f"\n## {name}\n", variant_table(name) if name != "extra_h" else _extra()]
        except FileNotFoundError:
            parts += [f"\n## {name}\n", "(not run)"]
    (RESULT_DIR / "ROBUSTNESS.md").write_text("\n".join(parts), encoding="utf-8")
    print("ok")


def _extra() -> str:
    tabs = {s: load("extra_h", s) for s in STAGES}
    lines = ["| side | H | TRAIN | VAL | HOLDOUT |", "|---|---|---|---|---|"]
    for side in ("up_disp_short", "down_disp_long"):
        for H in (20, 45):
            cells = []
            for s in STAGES:
                t = tabs[s]
                m = t[(t.side == side) & (t.H == H)].iloc[0]
                cells.append(cell(m) + f" n={int(m.n_events)}")
            lines.append(f"| {side} | {H} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
