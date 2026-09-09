"""Phase 1B TRAIN orchestrator — analogue engine, forecasts, controls, nulls.

Runs on TRAIN only (fence-guarded, refuses any other fence). Writes all
artefacts under data/analog_path/ and appends ledger rows. The SEALED
window is not touched: `load_eligible_dates("train")` + require_fence per
date make any SEALED access raise.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.analog_path import config
from scripts.analog_path.control import run_control
from scripts.analog_path.eligibility import load_eligible_dates
from scripts.analog_path.forecasts import (calibration, expanding_baseline,
                                           expanding_return_only, quality,
                                           return_controlled)
from scripts.analog_path.ledger import record
from scripts.analog_path.matcher import analogue_forecasts, match_day
from scripts.analog_path.nulls import (block_shift_null,
                                       empirical_p_two_sided,
                                       randomized_matching_null,
                                       sign_permutation_null)
from scripts.analog_path.states import build_matrices

OUT = Path(__file__).resolve().parents[2] / "data" / "analog_path"
REPS = {"A": "states_A", "B": "states_B", "C": "states_C"}


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    dates = load_eligible_dates("train")
    if len(dates) < 1500:
        raise RuntimeError(
            f"eligible TRAIN list has only {len(dates)} dates — the persisted "
            "eligible_days.csv appears stale or clobbered; rebuild with "
            "scripts.analog_path.eligibility.build_eligible_days()")
    for d in dates:
        config.require_fence(d, "train")
    M = build_matrices(dates)
    mat_dates = M["dates"]
    n = len(mat_dates)
    if n < 1500:
        raise RuntimeError(f"TRAIN matrix has only {n} sessions — eligibility "
                           "regression; refusing to run on a truncated sample")
    A, B, C = M["states_A"], M["states_B"], M["states_C"]
    R = M["r_1230"]
    O = M["outcomes"]
    X = M["excursions"]
    horizons = list(config.HORIZONS)
    print(f"TRAIN matrix: n={n} (skipped {len(M['skipped'])})")

    baseline_f = np.column_stack([expanding_baseline(O, h) for h in range(len(horizons))])
    retonly_f = np.column_stack([expanding_return_only(O, h, R) for h in range(len(horizons))])
    realized = O

    grid = {"quality": {}, "regression": {}, "similarity": {}, "records_summary": {}}
    record_rows = []

    for rep_name, mat_key in REPS.items():
        states = M[mat_key]
        for k in config.K_VALUES:
            cell = f"{rep_name}_K{k}"
            means = {h: np.full(n, np.nan) for h in horizons}
            medians = {h: np.full(n, np.nan) for h in horizons}
            sim = {"reference_percentile": np.full(n, np.nan),
                   "pool_rank_nearest": np.full(n, np.nan),
                   "nearest_dist": np.full(n, np.nan),
                   "kth_dist": np.full(n, np.nan),
                   "median_pool": np.full(n, np.nan)}
            rows = []
            n_pool_small = 0
            for i in range(n):
                md = match_day(states, i, k)
                if md is None:
                    n_pool_small += 1
                    continue
                sim["reference_percentile"][i] = md["reference_percentile"]
                sim["pool_rank_nearest"][i] = md["pool_rank_nearest"]
                sim["nearest_dist"][i] = md["nearest_dist"]
                sim["kth_dist"][i] = md["kth_dist"]
                sim["median_pool"][i] = md["median_pool_dist"]
                for hcol, h in enumerate(horizons):
                    fc = analogue_forecasts(O[:, hcol], md["analogue_idx"])
                    means[h][i] = fc["mean"]
                    medians[h][i] = fc["median"]
                rows.append({
                    "query_date": mat_dates[i].isoformat(),
                    "k": k,
                    "analogue_dates": [mat_dates[j].isoformat() for j in md["analogue_idx"]],
                    "distances": [float(dd) for dd in md["distances"]],
                    "reference_percentile": md["reference_percentile"],
                    "pool_rank_nearest": md["pool_rank_nearest"],
                })
            df = pd.DataFrame(rows)
            df.to_parquet(OUT / f"analogue_records_train_{rep_name}_K{k}.parquet")
            record_rows.append((cell, len(rows)))
            grid["similarity"][cell] = {
                "n_query": int(len(rows)),
                "n_pool_too_small": int(n_pool_small),
                "reference_percentile": _dist_summary(sim["reference_percentile"]),
                "pool_rank_nearest": _dist_summary(sim["pool_rank_nearest"]),
                "nearest_dist": _dist_summary(sim["nearest_dist"]),
                "kth_dist": _dist_summary(sim["kth_dist"]),
                "median_pool_dist": _dist_summary(sim["median_pool"]),
            }
            for hcol, h in enumerate(horizons):
                q_mean = quality(means[h], realized[:, hcol])
                q_median = quality(medians[h], realized[:, hcol])
                grid["quality"][f"{cell}/{h}"] = {
                    "mean_forecast": q_mean, "median_forecast": q_median,
                    "calibration_mean": calibration(means[h], realized[:, hcol]),
                }
                grid["regression"][f"{cell}/{h}"] = return_controlled(
                    realized[:, hcol], means[h], R)

    # baselines (single per horizon, walk-forward causal)
    grid["baselines"] = {}
    for hcol, h in enumerate(horizons):
        grid["baselines"][f"unconditional/{h}"] = quality(
            baseline_f[:, hcol], realized[:, hcol])
        grid["baselines"][f"return_only/{h}"] = quality(
            retonly_f[:, hcol], realized[:, hcol])

    # nulls: randomized matching per (K, horizon); observed per rep
    grid["nulls"] = {}
    null_corrs = {}
    for k in config.K_VALUES:
        for h in range(len(horizons)):
            key = f"K{k}/{horizons[h]}"
            null_corrs[key] = randomized_matching_null(O, h, k, realized[:, h])
    for rep_name in REPS:
        for k in config.K_VALUES:
            for h, hname in enumerate(horizons):
                f = grid["quality"][f"{rep_name}_K{k}/{hname}"]["mean_forecast"]["corr"]
                null = null_corrs[f"K{k}/{hname}"]
                null_sample = np.asarray(null["sample"])
                grid["nulls"][f"{rep_name}_K{k}/{hname}"] = {
                    "observed_corr": f,
                    "null": null,
                    "effect_size": (f - null["null_mean"]) / null["null_sd"]
                    if f is not None and null["null_sd"] > 0 else None,
                    "empirical_p_two_sided": empirical_p_two_sided(f, null_sample)
                    if f is not None and len(null_sample) > 0 else None,
                }

    # block-shift + sign-permutation nulls for the close horizon
    close = horizons.index("close")
    for rep_name in REPS:
        for k in config.K_VALUES:
            cell = f"{rep_name}_K{k}"
            f = np.full(n, np.nan)
            # recompute mean forecast for close horizon
            for i in range(n):
                md = match_day(M[REPS[rep_name]], i, k)
                if md is not None:
                    f[i] = analogue_forecasts(O[:, close], md["analogue_idx"])["mean"]
            grid["nulls"][f"{cell}/close/block_shift"] = {
                "stat": "corr", "observed": grid["quality"][f"{cell}/close"]["mean_forecast"]["corr"],
                "null": block_shift_null(realized[:, close], f, mat_dates),
            }
            grid["nulls"][f"{cell}/close/sign_perm_da"] = {
                "stat": "dir_acc",
                "observed": grid["quality"][f"{cell}/close"]["mean_forecast"]["dir_acc"],
                "null": sign_permutation_null(realized[:, close], f),
            }

    # same-return/different-path control
    control_out = run_control(C, R, O, mat_dates)
    grid["control"] = control_out

    # MFE/MAE diagnostics: analogue mean vs realized (close horizon), rep A K20
    diag = {}
    for rep_name in REPS:
        states = M[REPS[rep_name]]
        for k in config.K_VALUES:
            for exc, col in (("mfe", 0), ("mae", 1)):
                f = np.full(n, np.nan)
                for i in range(n):
                    md = match_day(states, i, k)
                    if md is not None:
                        f[i] = float(np.mean(X[md["analogue_idx"], col]))
                q = quality(f, X[:, col])
                diag[f"{rep_name}_K{k}/{exc}"] = {
                    "corr": q["corr"], "mae": q["mae"], "n": q["n"]}
    grid["excursion_diagnostics"] = diag

    with open(OUT / "phase1b_train_grid.json", "w") as fh:
        json.dump(grid, fh, indent=1, default=str)
    for cell, nrows in record_rows:
        record("phase1b_analogue_engine", fence="train", representation=cell.split("_")[0],
               distance="euclidean", k=int(cell.split("K")[1]), horizon="all",
               sample=f"TRAIN walk-forward, {nrows} query days",
               metric="analogue records + similarity",
               result={"n_query": nrows}, used_for_methodology_decision=False)
    return grid


def _dist_summary(x: np.ndarray) -> dict:
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)),
            "mean": float(np.mean(x)),
            "median": float(np.median(x)),
            "p10": float(np.quantile(x, 0.10)),
            "p90": float(np.quantile(x, 0.90)),
            "frac_gt_50pct": float(np.mean(x > 0.5)),
            "frac_gt_90pct": float(np.mean(x > 0.9))}


if __name__ == "__main__":
    g = run()
    print("\nPhase 1B TRAIN complete.")
    for cell, sim in g["similarity"].items():
        s = sim["reference_percentile"]
        print(f"  {cell}: ref-pct median={s['median']:.3f} "
              f"frac>50%={s['frac_gt_50pct']:.3f} frac>90%={s['frac_gt_90pct']:.3f}")
    print("\nclose-horizon quality (mean forecast):")
    for rep_name in ("A", "B", "C"):
        for k in config.K_VALUES:
            q = g["quality"][f"{rep_name}_K{k}/close"]["mean_forecast"]
            reg = g["regression"][f"{rep_name}_K{k}/close"]
            print(f"  {rep_name}_K{k}: corr={q['corr']:+.4f} dir={q['dir_acc']:.3f} "
                  f"b_analogue={reg['beta_analogue']:+.4f} t={reg['t_analogue']:+.2f} "
                  f"dR2={reg['delta_r2']:+.5f}")
    c = g["control"]
    print(f"\ncontrol: n_groups={c['n_groups']}")
    for h, v in c["horizons"].items():
        print(f"  {h}: mean_diff={v['mean_diff']:+.5f} nw_t={v['nw_t']:+.2f} "
              f"ci=[{v['ci95_lo']:+.5f}, {v['ci95_hi']:+.5f}]")
