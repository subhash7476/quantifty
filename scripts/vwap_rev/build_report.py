"""Substitute {{TABLE:name}} placeholders in the report template with tables built from results/*.csv.

Narrative lives in docs/reports/research/_report_template.md; every number in a table comes from a CSV that a
frozen-protocol script wrote. Reporting only; not part of the frozen hash set."""
from __future__ import annotations

import re

import pandas as pd

from scripts.vwap_rev import common as C
from scripts.vwap_rev.run_primary import RESULT_DIR

DOCS = C.REPO / "docs" / "reports" / "research"
TEMPLATE = DOCS / "_report_template.md"
REPORT = DOCS / "VWAP_EXTREME_REVERSION_RESEARCH_REPORT.md"
SIDE = {"up_disp_short": "up-disp -> short", "down_disp_long": "down-disp -> long", "pooled": "pooled"}


def md(df: pd.DataFrame, fmt: dict | None = None) -> str:
    fmt = fmt or {}
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in df.to_dict("records"):
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append("" if pd.isna(v) else fmt.get(c, "{:.2f}").format(v))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def cells(stage, tag="primary", excess=False) -> pd.DataFrame:
    return pd.read_csv(RESULT_DIR / f"{tag}_{stage}_{'excess_' if excess else ''}cells.csv")


def t_primary(stage: str) -> str:
    c = cells(stage)
    c = c[c.side != "pooled"].copy()
    c["side"] = c["side"].map(SIDE)
    c["95% CI (boot)"] = c.apply(lambda r: f"[{r.ci_lo:+.1f}, {r.ci_hi:+.1f}]", axis=1)
    c = c.rename(columns={"session_mean_bp": "session mean bp", "nw_t": "NW t", "p_one_nw": "p (1-sided NW)",
                          "p_holm_all10": "Holm-10 p", "mean_bp_event": "event mean bp",
                          "median_bp_event": "event median bp", "frac_pos": "frac R>0", "mde_bp_80": "MDE@80% bp",
                          "n_events": "events", "n_names": "names", "n_sessions": "sessions"})
    cols = ["side", "H", "events", "names", "sessions", "session mean bp", "95% CI (boot)", "NW t", "p (1-sided NW)",
            "Holm-10 p", "event mean bp", "event median bp", "frac R>0", "MDE@80% bp"]
    return md(c[cols], {"p (1-sided NW)": "{:.4f}", "Holm-10 p": "{:.4f}", "NW t": "{:.2f}", "frac R>0": "{:.3f}"})


def t_dist(stage: str) -> str:
    c = cells(stage)
    c = c[c.side != "pooled"].copy()
    c["side"] = c["side"].map(SIDE)
    cols = ["side", "H", "q01", "q05", "q10", "q25", "q50", "q75", "q90", "q95", "q99", "mean_bp_event", "sd_event",
            "skew", "kurt"]
    return md(c[cols].rename(columns={"mean_bp_event": "mean", "sd_event": "sd"}))


def t_exc(stage: str) -> str:
    c = cells(stage)
    c = c[c.side != "pooled"].copy()
    c["side"] = c["side"].map(SIDE)
    cols = ["side", "H", "mfe_mean", "mfe_median", "mae_mean", "mae_median", "frac_pos",
            "frac_toward_vwap_static", "dstat_mean_bp", "dstat_median_bp"]
    return md(c[cols].rename(columns={"frac_pos": "frac R>0", "frac_toward_vwap_static": "frac toward VWAP (static)",
                                      "dstat_mean_bp": "dist chg mean bp", "dstat_median_bp": "dist chg median bp"}),
              {"frac R>0": "{:.3f}", "frac toward VWAP (static)": "{:.3f}"})


def t_excess(stage: str) -> str:
    g = cells(stage)
    e = cells(stage, excess=True)
    g, e = g[g.side != "pooled"], e[e.side != "pooled"]
    m = g.merge(e, on=["side", "H"], suffixes=("_raw", "_ex"))
    m["side"] = m["side"].map(SIDE)
    out = m[["side", "H", "session_mean_bp_raw", "p_one_nw_raw", "session_mean_bp_ex", "nw_t_ex", "p_one_nw_ex",
             "mean_bp_event_ex", "median_bp_event_ex"]]
    out.columns = ["side", "H", "raw session mean", "raw p", "R_ex session mean", "R_ex NW t", "R_ex p",
                   "R_ex event mean", "R_ex event median"]
    return md(out, {"raw p": "{:.4f}", "R_ex p": "{:.4f}", "R_ex NW t": "{:.2f}"})


def t_costs(stage: str) -> str:
    c = pd.read_csv(RESULT_DIR / f"primary_{stage}_costs.csv")
    c = c[(c.side != "pooled") & (c.kappa_bp_side.isin([0.0, 2.75, 5.0]))]
    rows = []
    for (side, H), g in c.groupby(["side", "H"]):
        r = {"side": SIDE[side], "H": H, "gross session": g.gross_session_mean.iloc[0],
             "fees bp": g.fee_bp_mean.iloc[0]}
        for k in (0.0, 2.75, 5.0):
            x = g[g.kappa_bp_side == k].iloc[0]
            r[f"net session (k={k})"] = x.net_session_mean
            r[f"net EVENT (k={k})"] = x.net_event_mean
        rows.append(r)
    return md(pd.DataFrame(rows))


def t_comp() -> str:
    return md(pd.read_csv(RESULT_DIR / "stage_composition.csv"))


def t_quarterly() -> str:
    q = pd.read_csv(RESULT_DIR / "quarterly_excess.csv")
    q = q[q.H == 30].copy()
    rows = []
    for qt, g in q.groupby("quarter"):
        r = {"quarter": qt, "stage": g.stage.iloc[0]}
        for side, lab in (("down_disp_long", "down"), ("up_disp_short", "up")):
            x = g[g.side == side]
            if len(x):
                x = x.iloc[0]
                r[f"{lab} events"] = int(x.n_events)
                r[f"{lab} raw sess"] = x.raw_session_mean
                r[f"{lab} R_ex event"] = x.ex_event_mean
                r[f"{lab} R_ex sess"] = x.ex_session_mean
        rows.append(r)
    return md(pd.DataFrame(rows))


def t_weight() -> str:
    w = pd.read_csv(RESULT_DIR / "weighting_views.csv")
    w = w[w.H.isin([10, 30])].copy()
    w["side"] = w["side"].map(SIDE)
    cols = ["stage", "side", "H", "session_mean_raw", "event_mean_raw", "session_mean_raw_ex_singletons",
            "session_mean_excess", "session_mean_excess_ex_singletons", "singleton_session_share"]
    return md(w[cols].rename(columns={"session_mean_raw": "sess raw", "event_mean_raw": "event raw",
                                      "session_mean_raw_ex_singletons": "sess raw ex-singleton",
                                      "session_mean_excess": "sess R_ex",
                                      "session_mean_excess_ex_singletons": "sess R_ex ex-singleton",
                                      "singleton_session_share": "singleton share"}))


def t_sub(cut: str, stage: str = "HOLDOUT") -> str:
    s = pd.read_csv(RESULT_DIR / "subgroups_cells.csv")
    s = s[(s["cut"] == cut) & (s.stage == stage) & (s.H.isin([10, 30]))].copy()
    s["side"] = s["side"].map(SIDE)
    out = s[["level", "side", "H", "raw_n_events", "raw_n_sessions", "raw_session_mean", "raw_p_one",
             "ex_session_mean", "ex_p_one"]]
    out.columns = ["level", "side", "H", "events", "sessions", "raw sess mean", "raw p", "R_ex sess mean", "R_ex p"]
    return md(out, {"raw p": "{:.3f}", "R_ex p": "{:.3f}"})


def t_robust_labels() -> str:
    txt = (RESULT_DIR / "ROBUSTNESS.md").read_text(encoding="utf-8")
    m = re.search(r"(\| variant \|.*?)\n\n", txt, re.S)
    return m.group(1) if m else "(robustness summary missing)"


def build() -> None:
    txt = TEMPLATE.read_text(encoding="utf-8")

    def sub(m):
        name, *args = m.group(1).split(":")
        simple = {"comp": t_comp, "quarterly": t_quarterly, "weight": t_weight, "robust_labels": t_robust_labels}
        if name in simple:
            return simple[name]()
        fn = {"primary": t_primary, "dist": t_dist, "exc": t_exc, "excess": t_excess, "costs": t_costs,
              "sub": t_sub}[name]
        return fn(*args)

    out = re.sub(r"\{\{TABLE:([^}]+)\}\}", sub, txt)
    REPORT.write_text(out, encoding="utf-8")
    print("report written", len(out))


if __name__ == "__main__":
    build()
