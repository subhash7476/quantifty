"""M4a-CE report tables: every number in the characterization report's tables is script-generated from the result
files (nothing typed by hand). The report template holds prose and {{TABLE:name}} placeholders; this fills them.

    python -m scripts.m4a_compress.build_report
"""
from __future__ import annotations

import json
import math
import shutil

import numpy as np
import pandas as pd

from scripts.m4a_compress import classify as CL
from scripts.m4a_compress import common as C
from scripts.m4a_compress import stats as S

RES = C.OUT_DIR / "results"
DOCS = C.RESEARCH_DOCS
TEMPLATE = DOCS / "M4A_COMPRESSION_EXPANSION_CHARACTERIZATION_REPORT.template.md"
REPORT = DOCS / "M4A_COMPRESSION_EXPANSION_CHARACTERIZATION_REPORT.md"
BUNDLE = DOCS / "m4a_compress"


def fmt(x, nd=4):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    if isinstance(x, float):
        return f"{x:.{nd}f}" if abs(x) >= 1e-3 or x == 0 else f"{x:.2e}"
    return str(x)


def md(df: pd.DataFrame, cols: list, heads: list | None = None, nd=4) -> str:
    heads = heads or cols
    lines = ["| " + " | ".join(heads) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in df.itertuples(index=False):
        d = r._asdict()
        lines.append("| " + " | ".join(fmt(d[c], nd) for c in cols) + " |")
    return "\n".join(lines)


def cells(stage: str) -> pd.DataFrame:
    return pd.read_csv(RES / f"cells_{stage}.csv")


def primary(stage: str) -> pd.DataFrame:
    t = cells(stage)
    t = t[(t["variant"] == "D2") & (t["outcome"] == "E_range")].copy()
    adj = S.holm({(int(r.h), r.comparator): r.d_p_one for r in t.dropna(subset=["d_p_one"]).itertuples()})
    adjb = S.holm({(int(r.h), r.comparator): r.bound_d_p_one for r in t.itertuples() if np.isfinite(r.bound_d_p_one)})
    t["holm_p"] = [adj.get((int(r.h), r.comparator), np.nan) for r in t.itertuples()]
    t["holm_bound_p"] = [adjb.get((int(r.h), r.comparator), np.nan) for r in t.itertuples()]
    return t.sort_values(["comparator", "h"], ascending=[False, True])


def tab_primary(stage: str) -> str:
    t = primary(stage)
    return md(t, ["h", "comparator", "n_C", "n_X", "n_pair_dates", "n_dates_below_floor", "mean_C_coh", "mean_X_coh", "d_mean", "d_se",
                  "d_t", "d_p_one", "holm_p", "d_mde80", "bound_d_mean", "holm_bound_p"],
              ["h", "comparator", "n C events", "n X events", "pair dates", "dates < floor", "mean E (C)", "mean E (X)", "d-bar", "NW SE",
               "t", "p (1-sided)", "Holm p", "MDE80", "bound d-bar", "Holm bound p"])


def tab_counts(stage: str) -> str:
    t = primary(stage)
    return md(t, ["h", "comparator", "n_C", "dates_C", "n_X", "dates_X", "n_pair_dates", "n_dropped_C", "n_dropped_X", "n_value_missing"],
              ["h", "comparator", "C events", "C dates", "X events", "X dates", "pair dates", "dropped C", "dropped X", "value missing"])


def tab_reportonly(stage: str) -> str:
    t = primary(stage)
    return md(t, ["h", "comparator", "d_mean", "d_mean_evtwt", "d_ci_lo", "d_ci_hi", "evt_b", "evt_t", "evt_p_one", "perm_p_one"],
              ["h", "comparator", "d-bar", "event-wtd d", "boot CI lo", "boot CI hi", "cluster b", "cluster t", "cluster p", "perm p"])


def tab_levels(stage: str) -> str:
    lv = pd.read_csv(RES / f"levels_{stage}.csv")
    lv = lv[lv["variant"] == "D2"]
    return md(lv, ["h", "cohort", "n", "dates", "mean_evt", "median_evt", "mean_coh"],
              ["h", "cohort", "events", "dates", "mean E (events)", "median E", "mean E (date-cohort)"])


def tab_byyear(stage: str) -> str:
    by = pd.read_csv(RES / f"byyear_{stage}.csv")
    by["cell"] = "h" + by["h"].astype(str) + "_" + by["comparator"]
    piv = by.pivot_table(index="year", columns="cell", values="d_mean")
    cols = list(piv.columns)
    piv = piv.reset_index()
    piv["year"] = piv["year"].astype(str)
    return md(piv, ["year"] + cols, ["year"] + [c.replace("_", " ") for c in cols])


def tab_conc(stage: str) -> str:
    conc = json.loads((RES / f"concentration_{stage}.json").read_text())
    rows = [{"cell": k, **{kk: v for kk, v in c.items() if kk != "top_dates"}} for k, c in conc.items()]
    return md(pd.DataFrame(rows), ["cell", "n_dates", "d_mean", "d_median", "d_mean_ex_top_k", "share_of_sum_top_k", "share_pos_dates"],
              ["cell", "dates", "d-bar", "median d", "d-bar ex top-10", "share of sum in top-10", "share d>0"])


def tab_d1(stage: str) -> str:
    t = cells(stage)
    t = t[(t["variant"] == "D1") & (t["outcome"] == "E_range")]
    adj = S.holm({(int(r.h), r.comparator): r.d_p_one for r in t.dropna(subset=["d_p_one"]).itertuples()})
    t = t.assign(holm_p=[adj.get((int(r.h), r.comparator), np.nan) for r in t.itertuples()])
    return md(t, ["h", "comparator", "n_C", "n_X", "n_pair_dates", "mean_C_coh", "mean_X_coh", "d_mean", "d_t", "d_p_one", "holm_p", "d_mde80"],
              ["h", "comparator", "n C", "n X", "pair dates", "mean E (C)", "mean E (X)", "d-bar", "t", "p", "Holm p (info)", "MDE80"])


def tab_secondary(stage: str) -> str:
    t = cells(stage)
    t = t[(t["variant"] == "D2") & (t["outcome"] != "E_range")]
    return md(t, ["outcome", "h", "comparator", "n_pair_dates", "mean_C_coh", "mean_X_coh", "d_mean", "d_t", "d_p_one", "d_mde80"],
              ["outcome", "h", "comparator", "pair dates", "mean (C)", "mean (X)", "d-bar", "t", "p (unadj.)", "MDE80"])


def tab_signed(stage: str) -> str:
    s = pd.read_csv(RES / f"signed_{stage}.csv")
    s = s[s["variant"] == "D2"]
    return md(s, ["h", "cohort", "n", "mean_evt", "mean_coh", "frac_pos"], ["h", "cohort", "events", "mean signed move", "date-cohort mean", "share > 0"])


def tab_accounting(stage: str) -> str:
    a = json.loads((RES / f"accounting_{stage}.json").read_text())["D2"]
    rows = [{"block": k, **v} for k, v in a.items()]
    return md(pd.DataFrame(rows), ["block", "formed", "resolved", "dropped", "value_missing", "excluded_by_containment"],
              ["block", "formed", "resolved", "dropped", "value missing", "excluded by containment"])


def tab_verification() -> str:
    rows = []
    for st in ("TRAIN", "VAL"):
        v = json.loads((RES / f"verification_{st}.json").read_text())
        sql = v["vp1_sql"]
        for var in ("D2", "D1"):
            x = sql[var]
            rows.append({"stage": st, "check": f"VP1 SQL vs engine ({var})", "result": "PASS" if x["pass"] else "FAIL",
                         "detail": f"{x['ledger_rows']:,} ledger rows = {x['sql_rows']:,} SQL rows; {x['n_compared_values']:,} values; "
                                   f"max |pct| diff {x['pct_max_abs_diff']:.1e}; max |E| diff {x['E_max_abs_diff']:.1e}; flag mismatches {x['flag_mismatch']}"})
        r2 = v["vp2_raw"]
        rows.append({"stage": st, "check": "VP2 raw as-traded loops", "result": "PASS" if r2["pass"] else "FAIL",
                     "detail": f"{r2['verified']} verified of {r2['sampled']} sampled; skipped for a corporate action {r2['skipped_ca']}; "
                               f"max |E| diff {r2.get('E_max_abs_diff', float('nan')):.1e}"})
        r3 = v["vp3_stats"]
        rows.append({"stage": st, "check": "VP3 statistics (manual NW + statsmodels kernel)", "result": "PASS" if r3["pass"] else "FAIL",
                     "detail": "max abs diff " + ", ".join(f"{k} {x:.1e}" for k, x in r3["max_abs_diff"].items())})
        r4 = v["vp4_accounting"]
        rows.append({"stage": st, "check": "VP4 accounting / uniqueness / exclusivity", "result": "PASS" if r4["pass"] else "FAIL", "detail": "identities exact"})
        r5 = v["vp5_prices"]
        rows.append({"stage": st, "check": "VP5 price basis", "result": "PASS" if r5["pass"] else "FAIL",
                     "detail": f"adjusted = raw on CA-free names (max rel diff {r5['adj_vs_raw_max_rel_diff_no_CA_names']:.1e}); "
                               f"CA rebuild agreement {r5['ca_rows_reconstruction_agree']}/{r5['ca_rows_reconstructed']}"})
    return md(pd.DataFrame(rows), ["stage", "check", "result", "detail"])


def tab_classification() -> str:
    c = json.loads((RES / "classification.json").read_text())
    rows = [{"cell": k, "holm_p": v["holm_p"], "d_mean": v["d_mean"], "fragile": v["fragile"]} for k, v in c["val_info"].items()]
    return f"**Label:** {c['label']}\n\n" + md(pd.DataFrame(rows), ["cell", "d_mean", "holm_p", "fragile"], ["cell (h,comparator)", "d-bar", "Holm p", "attrition-fragile"])


TABLES = {
    "primary_VAL": lambda: tab_primary("VAL"), "primary_TRAIN": lambda: tab_primary("TRAIN"),
    "counts_VAL": lambda: tab_counts("VAL"), "counts_TRAIN": lambda: tab_counts("TRAIN"),
    "reportonly_VAL": lambda: tab_reportonly("VAL"), "reportonly_TRAIN": lambda: tab_reportonly("TRAIN"),
    "levels_VAL": lambda: tab_levels("VAL"), "levels_TRAIN": lambda: tab_levels("TRAIN"),
    "byyear_VAL": lambda: tab_byyear("VAL"), "byyear_TRAIN": lambda: tab_byyear("TRAIN"),
    "conc_VAL": lambda: tab_conc("VAL"), "conc_TRAIN": lambda: tab_conc("TRAIN"),
    "d1_VAL": lambda: tab_d1("VAL"), "d1_TRAIN": lambda: tab_d1("TRAIN"),
    "secondary_VAL": lambda: tab_secondary("VAL"), "secondary_TRAIN": lambda: tab_secondary("TRAIN"),
    "signed_VAL": lambda: tab_signed("VAL"), "signed_TRAIN": lambda: tab_signed("TRAIN"),
    "accounting_VAL": lambda: tab_accounting("VAL"), "accounting_TRAIN": lambda: tab_accounting("TRAIN"),
    "verification": tab_verification, "classification": tab_classification,
}


def build() -> str:
    text = TEMPLATE.read_text()
    for name, fn in TABLES.items():
        text = text.replace("{{TABLE:" + name + "}}", fn())
    left = [w for w in text.split() if w.startswith("{{TABLE:")]
    if left:
        raise SystemExit(f"unfilled placeholders: {left}")
    REPORT.write_text(text)
    BUNDLE.mkdir(exist_ok=True)
    for f in RES.glob("*"):
        if f.suffix in (".csv", ".json") or f.name.endswith(".csv.gz"):
            shutil.copy(f, BUNDLE / f.name)
    return text


if __name__ == "__main__":
    build()
    print(REPORT)
