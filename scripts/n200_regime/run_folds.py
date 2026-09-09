"""Expanding-window fold runner — fit, freeze, filter.

Design: `docs/superpowers/specs/2026-09-09-n200-regime-hmm-design.md` §6, §8, §9.

For each evaluation year T in 2017..2026:
  1. GK floor per entity, from that entity's non-zero GK in the fit window only
  2. features over each entity's full price history using that floor
  3. winsorization bounds and standardization moments, fitted on fit-window
     member rows only
  4. pooled panel HMM on fit-window sequences, canonically ordered, then frozen
  5. causal forward filter over each sequence, keeping only year-T rows

The barrier is the whole point: every quantity in steps 1, 3 and 4 comes from
data ending 31 December T-1. Lookahead through parameters leaves no trace in the
output, so it has to be prevented here.

Usage: python scripts/n200_regime/run_folds.py [--folds 2017 2018 ...]
Output: data/features/n200_regime/regime_panel.duckdb
        data/features/n200_regime/params/fold_{year}.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
import sys  # noqa: E402

sys.path.insert(0, str(ROOT))

from core.analytics.regime.features import (  # noqa: E402
    FEATURE_SETS, features_from_gk, fit_normalization, gk_floor_value,
)
from core.analytics.regime.panel_hmm import fit_panel, filter_sequence  # noqa: E402

PANEL = ROOT / "data" / "features" / "n200_regime" / "panel.duckdb"
OUT_DIR = ROOT / "data" / "features" / "n200_regime"


def variant_paths(variant: str) -> tuple[Path, Path]:
    """Variant B writes to its own paths so Variant A's artifacts are never
    overwritten and the two remain comparable (variant-B spec §3)."""
    suffix = "" if variant == "A" else f"_{variant.lower()}"
    return OUT_DIR / f"regime_panel{suffix}.duckdb", OUT_DIR / f"params{suffix}"

FOLD_YEARS = list(range(2017, 2027))
N_STATES = 3
SEED = 20260909
MIN_SEQ_SESSIONS = 60
MAX_ITER = 200
TOL = 1e-6


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def load_panel() -> pd.DataFrame:
    con = duckdb.connect(str(PANEL), read_only=True)
    df = con.execute("""
        SELECT entity, symbol, trade_date, close, gk, in_universe, seq_id
        FROM panel_base ORDER BY entity, trade_date
    """).df()
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def entity_floors(df: pd.DataFrame, fit_end: pd.Timestamp) -> tuple[dict, float]:
    """Per-entity GK floor from fit-window rows only, plus a pooled fallback.

    A name that enters the universe during the evaluation year has no fit-window
    history to floor against; it takes the pooled median of the per-entity
    floors rather than a floor derived from its own evaluation year.
    """
    fit = df[df["trade_date"] <= fit_end]
    floors = {e: gk_floor_value(g["gk"].to_numpy())
              for e, g in fit.groupby("entity", observed=True)}
    pooled = float(np.median([v for v in floors.values() if v > 0])) if floors else 1e-12
    return floors, pooled


def build_fold_features(df: pd.DataFrame, floors: dict,
                        pooled: float) -> pd.DataFrame:
    parts = []
    for entity, g in df.groupby("entity", observed=True):
        g = g.sort_values("trade_date")
        f = features_from_gk(g["gk"], g["close"], floors.get(entity, pooled))
        f.index = g.index
        parts.append(f)
    return pd.concat(parts).reindex(df.index)


def run_fold(df: pd.DataFrame, year: int,
              variant: str = "A") -> tuple[pd.DataFrame, dict]:
    feature_names = list(FEATURE_SETS[variant])
    fit_end = pd.Timestamp(year - 1, 12, 31)
    year_start, year_end = pd.Timestamp(year, 1, 1), pd.Timestamp(year, 12, 31)

    floors, pooled = entity_floors(df, fit_end)
    feats = build_fold_features(df, floors, pooled)

    usable = df["in_universe"] & feats[feature_names].notna().all(axis=1)
    long_enough = df.loc[usable, "seq_id"].value_counts()
    keep_seqs = set(long_enough[long_enough >= MIN_SEQ_SESSIONS].index)
    usable &= df["seq_id"].isin(keep_seqs)

    fit_mask = usable & (df["trade_date"] <= fit_end)
    if not fit_mask.any():
        raise RuntimeError(f"fold {year}: empty fit window")

    norm = fit_normalization(feats.loc[fit_mask, feature_names].to_numpy())

    fit_seqs = [norm.apply(g[feature_names].to_numpy())
                for _, g in feats.loc[fit_mask].groupby(
                    df.loc[fit_mask, "seq_id"], observed=True)]
    fit_seqs = [s for s in fit_seqs if len(s) >= 2]

    model = fit_panel(fit_seqs, N_STATES, seed=SEED, max_iter=MAX_ITER, tol=TOL)

    # Filter each sequence from its own start through the end of year T, then
    # keep only year-T rows. Running from the sequence start gives the filter
    # its run-up; it is causal, so no future row can reach a kept one.
    eval_mask = usable & (df["trade_date"] <= year_end)
    has_year = set(df.loc[usable & (df["trade_date"] >= year_start)
                          & (df["trade_date"] <= year_end), "seq_id"])
    rows = []
    for seq_id, idx in df.loc[eval_mask].groupby("seq_id", observed=True).groups.items():
        if seq_id not in has_year:
            continue
        sub = df.loc[idx].sort_values("trade_date")
        x = norm.apply(feats.loc[sub.index, feature_names].to_numpy())
        if len(x) < 2:
            continue
        probs, entropy, states = filter_sequence(model, x)
        in_year = (sub["trade_date"] >= year_start).to_numpy()
        out = pd.DataFrame({
            "entity": sub["entity"].to_numpy()[in_year],
            "symbol": sub["symbol"].to_numpy()[in_year],
            "trade_date": sub["trade_date"].to_numpy()[in_year],
            "p_s0": probs[in_year, 0], "p_s1": probs[in_year, 1],
            "p_s2": probs[in_year, 2],
            "state": states[in_year].astype(int),
            "entropy": entropy[in_year],
        })
        rows.append(out)

    panel = pd.concat(rows, ignore_index=True)
    panel["fold_year"] = year
    panel["model_hash"] = model.model_hash

    params = {
        **model.to_dict(),
        "fold_year": year,
        "variant": variant,
        "feature_names": feature_names,
        "normalization": norm.to_dict(),
        "gk_floor_pooled": pooled,
        "gk_floor_entities": len(floors),
        "trained_on": f"2010-01-04..{fit_end.date()} (member rows from 2012)",
        "n_fit_sequences": len(fit_seqs),
        "n_fit_observations": int(sum(len(s) for s in fit_seqs)),
        "n_filtered_rows": int(len(panel)),
        "seed": SEED, "max_iter": MAX_ITER, "tol": TOL,
        "git_commit": git_commit(),
        "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_hash": model.model_hash,
    }
    return panel, params


def main() -> int:
    ap = argparse.ArgumentParser(description="Run expanding-window regime folds")
    ap.add_argument("--folds", type=int, nargs="*", default=FOLD_YEARS)
    ap.add_argument("--variant", choices=sorted(FEATURE_SETS), default="A")
    args = ap.parse_args()

    out_db, param_dir = variant_paths(args.variant)
    param_dir.mkdir(parents=True, exist_ok=True)
    print(f"Variant {args.variant}: features "
          f"{', '.join(FEATURE_SETS[args.variant])}")
    print("Loading base panel...")
    df = load_panel()
    print(f"  {len(df):,} rows, {df['entity'].nunique()} entities")

    frames = []
    for year in args.folds:
        print(f"\n[fold {year}] fitting on data through {year - 1}-12-31 ...")
        panel, params = run_fold(df, year, args.variant)
        (param_dir / f"fold_{year}.json").write_text(
            json.dumps(params, indent=2), encoding="utf-8")
        frames.append(panel)
        A = np.asarray(params["A"])
        print(f"  iters {params['n_iter']:>3}  converged {params['converged']}  "
              f"loglik {params['loglik']:,.0f}")
        print(f"  fit {params['n_fit_observations']:,} obs / "
              f"{params['n_fit_sequences']} seqs  ->  "
              f"{params['n_filtered_rows']:,} filtered rows")
        print("  diag(A) " + "  ".join(f"{A[i, i]:.3f}" for i in range(N_STATES))
              + f"   state mix " + "  ".join(
                  f"{(panel['state'] == s).mean():.2f}" for s in range(N_STATES)))

    all_panel = pd.concat(frames, ignore_index=True)
    out_db.unlink(missing_ok=True)
    con = duckdb.connect(str(out_db))
    con.execute("CREATE TABLE regime_panel AS SELECT * FROM all_panel")
    con.execute("CREATE INDEX rp_ent ON regime_panel (entity, trade_date)")
    con.close()

    print(f"\n{len(all_panel):,} rows written to {out_db}")
    print(f"params -> {param_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
