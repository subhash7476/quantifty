"""BKV-1 report builder (presentation only; not frozen). Every table is rendered from the result CSV/JSON files."""
from __future__ import annotations

import json
import shutil

import numpy as np
import pandas as pd

from scripts.breakout_vol import common as C
from scripts.breakout_vol import stats as S

RES = C.OUT_DIR / "results"
DOCS = C.RESEARCH_DOCS
BUNDLE = DOCS / "breakout_volume"


def md(df: pd.DataFrame, fmt: dict | None = None) -> str:
    fmt = fmt or {}
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if not np.isfinite(v) else fmt.get(c, "{:.2f}").format(v))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def primary(stage: str) -> str:
    c = pd.read_csv(RES / f"cells_{stage}.csv")
    adj = S.holm({(r.N, r.H, r.side): r.d_p_one for r in c.itertuples()}) if stage == "VAL" else {}
    t = pd.DataFrame({"N": c.N, "H": c.H, "side": c.side, "pair dates": c.n_pair_dates, "n_B": c.n_B, "n_C": c.n_C,
                      "m_B (bp)": c.mean_B_coh, "m_C (bp)": c.mean_C_coh, "d̄ = B−C (bp)": c.d_mean, "NW SE": c.d_se,
                      "t": c.d_t, "p (1-sided)": c.d_p_one,
                      "Holm-8 p": [adj.get((r.N, r.H, r.side), np.nan) for r in c.itertuples()] if stage == "VAL" else np.nan,
                      "MDE80 (bp)": c.d_mde80, "95% block-boot CI": [f"[{a:.0f}, {b:.0f}]" for a, b in zip(c.d_ci_lo, c.d_ci_hi)]})
    return md(t, {"p (1-sided)": "{:.3f}", "Holm-8 p": "{:.3f}", "t": "{:.2f}", "NW SE": "{:.1f}", "MDE80 (bp)": "{:.0f}",
                  "m_B (bp)": "{:.1f}", "m_C (bp)": "{:.1f}", "d̄ = B−C (bp)": "{:.1f}"})


def secondary(stage: str) -> str:
    c = pd.read_csv(RES / f"cells_{stage}.csv")
    t = pd.DataFrame({"N": c.N, "H": c.H, "side": c.side,
                      "A cohort mean (t)": [f"{a:.1f} ({b:.2f})" for a, b in zip(c.mean_A_coh, c.t_A)],
                      "B cohort mean (t)": [f"{a:.1f} ({b:.2f})" for a, b in zip(c.mean_B_coh, c.t_B)],
                      "C cohort mean (t)": [f"{a:.1f} ({b:.2f})" for a, b in zip(c.mean_C_coh, c.t_C)],
                      "D control (t)": [f"{a:.1f} ({b:.2f})" for a, b in zip(c.mean_D_coh, c.t_D)],
                      "n_D": c.n_D,
                      "event-wtd B−C": c.d_mean_evtwt, "2-way-cluster b (t; p)": [f"{a:.1f} ({b:.2f}; {p:.3f})" for a, b, p in zip(c.evt_b, c.evt_t, c.evt_p_one)],
                      "permutation p": c.perm_p_one, "attrition-bound d̄ (p)": [f"{a:.1f} ({p:.3f})" for a, p in zip(c.bound_d_mean, c.bound_d_p_one)]})
    return md(t, {"event-wtd B−C": "{:.1f}", "permutation p": "{:.3f}"})


def funnel(stage: str) -> str:
    a = json.loads((RES / f"accounting_{stage}.json").read_text())
    rows = []
    for k, v in a.items():
        n, h, s = k.split("_")
        rows.append({"cell": k, "formed": v["formed"], "resolved in stage": v["resolved_in_stage"], "dropped": v["dropped"],
                     "window beyond stage": v["excluded_by_containment"], "no benchmark": v["excluded_no_benchmark"],
                     "terminal ⊂ resolved": v["terminal_within_resolved"],
                     "B / C / D resolved": f"{v['resolved_B']} / {v['resolved_C']} / {v['resolved_D']}",
                     "A = B + C": "✓" if v["A_equals_B_plus_C"] else "✗",
                     "identity: resolved + dropped + beyond + no-bench = formed": "✓" if v["resolved_in_stage"] + v["dropped"] + v["excluded_by_containment"] + v["excluded_no_benchmark"] == v["formed"] else "✗"})
    return md(pd.DataFrame(rows))


def costs(stage: str) -> str:
    c = pd.read_csv(RES / f"costs_{stage}.csv")
    b = c[c.arm == "B"]
    piv = b.pivot_table(index=["N", "H", "side"], columns="kappa_bp", values="net_evt_bp").reset_index()
    piv.columns = ["N", "H", "side"] + [f"net @κ={k:g}" for k in sorted(b.kappa_bp.unique())]
    base = b[b.kappa_bp == 0][["N", "H", "side", "n", "gross_raw_evt_bp", "fee_bp", "breakeven_kappa_bp"]].reset_index(drop=True)
    t = base.merge(piv, on=["N", "H", "side"])
    t = t.rename(columns={"gross_raw_evt_bp": "gross raw B (bp)", "fee_bp": "statutory+DP RT (bp)", "breakeven_kappa_bp": "break-even κ (bp/side)"})
    return md(t, {c_: "{:.1f}" for c_ in t.columns if c_ not in ("N", "H", "side", "n")})


def variants() -> str:
    v = pd.read_csv(RES / "post_primary_variants.csv")
    rows = []
    for tag, g in v[v.stage == "VAL"].groupby("variant", sort=False):
        best = g.sort_values("d_p_one").iloc[0]
        rows.append({"variant": tag, "cells": len(g), "min one-sided p": best.d_p_one,
                     "cell of min p": f"N{int(best.N)} H{int(best.H)} {best.side}", "d̄ there (bp)": best.d_mean,
                     "# cells p<0.05 (unadjusted)": int((g.d_p_one < 0.05).sum()),
                     "# cells with d̄>0": int((g.d_mean > 0).sum())})
    return md(pd.DataFrame(rows), {"min one-sided p": "{:.3f}", "d̄ there (bp)": "{:.1f}"})


def variant_cells() -> str:
    v = pd.read_csv(RES / "post_primary_variants.csv")
    g = v[v.stage == "VAL"].pivot_table(index=["N", "H", "side"], columns="variant", values="d_mean", sort=False).round(1)
    return md(g.reset_index())


def terciles() -> str:
    t = pd.read_csv(RES / "post_primary_depth_terciles.csv")
    t = t[t.stage == "VAL"].drop(columns=["stage"])
    t["depth range (bp)"] = [f"{a:.0f}–{'∞' if not np.isfinite(b) else f'{b:.0f}'}" for a, b in zip(t.depth_lo_bp, t.depth_hi_bp)]
    t = t[["N", "H", "side", "tercile", "depth range (bp)", "share_B", "n_B", "n_C", "pair_dates", "d_mean", "d_t", "d_p_one"]]
    return md(t, {"share_B": "{:.2f}", "d_mean": "{:.1f}", "d_t": "{:.2f}", "d_p_one": "{:.3f}"})


def gap() -> str:
    g = pd.read_csv(RES / "post_primary_gap_decomposition.csv")
    g = g[(g.stage == "VAL") & g.quantity.isin(["sg", "rest5", "raw5", "rest20", "raw20"])]
    g["quantity"] = g.quantity.map({"sg": "overnight gap (t close → t+1 open)", "rest5": "post-open drift, H=5", "raw5": "total raw, H=5",
                                    "rest20": "post-open drift, H=20", "raw20": "total raw, H=20"})
    return md(g.drop(columns=["stage"]), {c_: "{:.1f}" for c_ in ("mean_B", "mean_C", "diff_B_minus_C")})


def by_year() -> str:
    y = pd.read_csv(RES / "post_primary_by_year.csv")
    y = y[(y.stage == "VAL") & (y.H == 5)].pivot_table(index=["N", "side"], columns="year", values="d_mean").round(0).reset_index()
    return md(y, {c_: "{:.0f}" for c_ in y.columns if c_ not in ("N", "side")})


def verification() -> str:
    rows = []
    for st in ("TRAIN", "VAL"):
        d = json.loads((RES / f"verification_{st}.json").read_text())
        v1, v2, v3, v4, v5 = d["vp1_sql"], d["vp2_raw"], d["vp3_stats"], d["vp4_accounting"], d["vp5_volume"]
        rows += [
            {"stage": st, "check": "VP1 SQL vs engine (event-for-event)", "result": f"{v1['ledger_events']:,} vs {v1['sql_events']:,} events; only-in-one-side {v1['only_in_ledger']}+{v1['only_in_sql']}; arm mismatches {v1['arm_mismatch']}; status mismatches {v1['status_mismatch_H5']}+{v1['status_mismatch_H20']}; max abs Δf {max(v1['f_max_abs_diff_bp_H5'], v1['f_max_abs_diff_bp_H20']):.1e} bp; max abs ΔR_m {max(v1['Rm_max_abs_diff_H5'], v1['Rm_max_abs_diff_H20']):.1e}", "pass": v1["pass"]},
            {"stage": st, "check": "VP2 raw as-traded rebuild (sample)", "result": f"{v2['verified']} of {v2['sampled']} verified ({v2['skipped_ca']} skipped CA, {v2['skipped_multi_symbol']} multi-symbol); max rel ΔAV {v2['av_max_rel_diff']:.1e}; max abs ΔR5 {v2['R5_max_abs_diff']:.1e}; max abs ΔR20 {v2['R20_max_abs_diff']:.1e}; max abs Δmargin {v2['margin_max_abs_diff']:.1e}; {v2['level_differs_by_later_CA_events']} price levels differ (later CA) but ratios agree", "pass": v2["pass"]},
            {"stage": st, "check": "VP3 statistics (manual NW, statsmodels kernel, dict cohorts)", "result": "max abs Δ — d̄ {d_mean:.1e}, SE {d_se:.1e}, t {d_t:.1e}, p {d_p:.1e}, kernel SE {kernel_se:.1e}, cohort d {cohort_m:.1e}".format(**v3["max_abs_diff"]), "pass": v3["pass"]},
            {"stage": st, "check": "VP4 accounting identities", "result": f"duplicate keys {v4['duplicate_event_keys']}; identity {v4['identity_ok']}; A=B⊔C {v4['A_eq_B_plus_C']}; one R_m per date {v4['one_Rm_per_date']}", "pass": v4["pass"]},
            {"stage": st, "check": "VP5 volume (adjusted vs raw; CA rebuild; turnover flag)", "result": f"adjusted=raw on {v5['rows_checked']:,} CA-free-entity rows (max abs Δ {v5['adj_vs_raw_max_abs_diff_no_CA_names']:.0e}); CA rebuild {v5['ca_rows_reconstruction_agree']}/{v5['ca_rows_reconstructed']}; turnover-based flag agrees on {100 * v5['turnover_flag_agreement']:.1f}% of {v5['events']:,} breakouts", "pass": v5["pass"]},
            {"stage": st, "check": "VP6 fee arithmetic", "result": f"round trip {d['vp6_fee']['round_trip_bp']:.2f} bp by hand = library", "pass": d["vp6_fee"]["pass"]}]
    return md(pd.DataFrame(rows))


def bundle() -> None:
    BUNDLE.mkdir(parents=True, exist_ok=True)
    for f in ("cells_TRAIN.csv", "cells_VAL.csv", "cohort_TRAIN.csv", "cohort_VAL.csv", "costs_TRAIN.csv", "costs_VAL.csv",
              "accounting_TRAIN.json", "accounting_VAL.json", "verification_TRAIN.json", "verification_VAL.json",
              "vp2_raw_sample_TRAIN.csv", "vp2_raw_sample_VAL.csv", "classification.json", "worked_examples.md",
              "post_primary_variants.csv", "post_primary_gap_decomposition.csv", "post_primary_by_year.csv",
              "post_primary_depth_terciles.csv", "post_primary_meta.json", "events_TRAIN.csv.gz", "events_VAL.csv.gz",
              "bench_TRAIN.csv", "bench_VAL.csv", "run_TRAIN.json", "run_VAL.json"):
        shutil.copy(RES / f, BUNDLE / f)
    shutil.copy(C.OUT_DIR / "manifest_dev.json", BUNDLE / "manifest_dev.json")


def main() -> None:
    bundle()
    tpl = (DOCS / "BREAKOUT_VOLUME_RESEARCH_REPORT.template.md").read_text(encoding="utf-8")
    subs = {"PRIMARY_TRAIN": primary("TRAIN"), "PRIMARY_VAL": primary("VAL"), "SECONDARY_TRAIN": secondary("TRAIN"),
            "SECONDARY_VAL": secondary("VAL"), "FUNNEL_VAL": funnel("VAL"), "FUNNEL_TRAIN": funnel("TRAIN"),
            "COSTS_VAL": costs("VAL"), "COSTS_TRAIN": costs("TRAIN"), "VARIANTS": variants(), "VARIANT_CELLS": variant_cells(),
            "TERCILES": terciles(), "GAP": gap(), "BY_YEAR": by_year(), "VERIFICATION": verification(),
            "WORKED": (RES / "worked_examples.md").read_text(encoding="utf-8").split("\n", 2)[2],
            "CLASSIFICATION": json.dumps(json.loads((RES / "classification.json").read_text())["label"]),
            "CA_SHARE": f"{100 * json.loads((RES / 'post_primary_meta.json').read_text())['share_events_with_CA_in_span']:.1f}"}
    for k, v in subs.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    assert "{{" not in tpl, "unfilled placeholder"
    (DOCS / "BREAKOUT_VOLUME_RESEARCH_REPORT.md").write_text(tpl, encoding="utf-8")
    print("report written", len(tpl))


if __name__ == "__main__":
    main()
