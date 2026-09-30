"""Render the primary-result CSVs into one markdown file (reporting only; not frozen, non-classifying)."""
from __future__ import annotations

import json

import pandas as pd

from scripts.vwap_rev.run_primary import RESULT_DIR

STAGES = ("TRAIN", "VAL", "HOLDOUT")


def md(df: pd.DataFrame, floatfmt="{:.3f}") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join(floatfmt.format(v) if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(out)


def main() -> None:
    parts = ["# VWAP-XREV-1 — primary results (auto-generated from results/*.csv)\n"]
    for st in STAGES:
        c = pd.read_csv(RESULT_DIR / f"primary_{st}_cells.csv")
        c = c[c.side != "pooled"][["side", "H", "n_events", "n_names", "n_sessions", "session_mean_bp", "nw_t",
                                   "p_one_nw", "p_holm_all10", "ci_lo", "ci_hi", "mean_bp_event",
                                   "median_bp_event", "frac_pos", "mde_bp_80"]]
        parts += [f"\n## {st} — primary cells (gross bp, reversion direction)\n", md(c)]
        e = pd.read_csv(RESULT_DIR / f"primary_{st}_excess_cells.csv")
        e = e[e.side != "pooled"][["side", "H", "session_mean_bp", "nw_t", "p_one_nw", "mean_bp_event",
                                   "median_bp_event"]]
        parts += [f"\n### {st} — market-excess R_ex (same inference)\n", md(e)]
        n = pd.read_csv(RESULT_DIR / f"primary_{st}_costs.csv")
        n = n[(n.side != "pooled") & (n.kappa_bp_side.isin([0.0, 2.75, 5.0]))]
        n = n.pivot_table(index=["side", "H"], columns="kappa_bp_side", values="net_session_mean").reset_index()
        n.columns = ["side", "H"] + [f"net@k{c}" for c in n.columns[2:]]
        parts += [f"\n### {st} — net session-mean bp by slippage scenario (kappa bp/side; statutory fees ~4.5 bp RT)\n", md(n)]
    cl = json.loads((RESULT_DIR / "classification.json").read_text())
    parts += ["\n## Frozen classification\n", "```json", json.dumps(cl, indent=1), "```"]
    (RESULT_DIR / "PRIMARY_RESULTS.md").write_text("\n".join(parts))
    print("written", len(parts))


if __name__ == "__main__":
    main()
