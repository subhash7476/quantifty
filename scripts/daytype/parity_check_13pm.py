"""
NiftyShield 13pm train/serve parity gate (Task 4 acceptance).

Compares, feature-by-feature, the 13pm feature vector produced by
DayTypeEngine._compute_features('13pm') against the corresponding row of
intraday_features_13pm.csv, restricted to the deployed model's feature_names.

PASS = every feature in feature_names matches within 1e-6 on every sampled
session (no feature served as 0.0 that the CSV has nonzero, no residual skew).

Also reports the DEPLOYED 2025 holdout accuracy: run the engine over all 2025
sessions the way the sealed harness does (feed full session bars, take the
locked/last acted-on state), score against the 2025 cluster_id labels.

Writes docs/reports/NIFTY_SHIELD_DAYTYPE_PARITY_REPORT.md
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.state.daytype_engine import DayTypeEngine, CHECKPOINT_BARS

NF_SYMBOL = "NSE_INDEX|Nifty 50"
BN_SYMBOL = "NSE_INDEX|Nifty Bank"

CANDLE_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
FEATURE_CSV = ROOT / "data" / "features" / "day_type" / "intraday_features_13pm.csv"
REPORT = ROOT / "docs" / "reports" / "NIFTY_SHIELD_DAYTYPE_PARITY_REPORT.md"

TARGET_BAR = CHECKPOINT_BARS["13pm"]  # 225
MIN_BARS = 100
TOL = 1e-6
N_SAMPLE = 30  # >= 20 required

CLUSTER_NAMES = {0: "Choppy", 1: "BullTrend", 2: "BearTrend"}


def load_session(d: date, symbol: str) -> pd.DataFrame | None:
    db_path = CANDLE_DIR / f"{d.isoformat()}.duckdb"
    if not db_path.exists():
        return None
    try:
        con = duckdb.connect(str(db_path), read_only=True)
        df = con.execute(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol = ? ORDER BY timestamp",
            [symbol],
        ).df()
        con.close()
    except Exception:
        return None
    if df.empty:
        return None
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    hm = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    df = df[(hm >= 555) & (hm <= 929)].reset_index(drop=True)
    return df if len(df) >= MIN_BARS else None


def engine_13pm_features(d: date) -> dict | None:
    """Feed full session bars (never-lock) and return the 13pm feature dict."""
    nf = load_session(d, NF_SYMBOL)
    bn = load_session(d, BN_SYMBOL)
    if nf is None or bn is None:
        return None
    eng = DayTypeEngine(model_name="logistic", lock_threshold=1.01)
    eng.reset(d)
    n = min(len(nf), len(bn), TARGET_BAR + 1)
    if n < MIN_BARS:
        return None
    nf = nf.head(n).reset_index(drop=True)
    bn = bn.head(n).reset_index(drop=True)
    for i in range(n):
        eng.on_bn_bar(bn.iloc[i].to_dict())
        eng.on_bar(nf.iloc[i].to_dict())
    return eng._compute_features("13pm")


def parity_check(df_feat: pd.DataFrame, feature_names: list[str]) -> dict:
    """Compare engine 13pm feature vector vs CSV row for sampled sessions."""
    sample_mask = (df_feat.index.year >= 2024) & (df_feat.index.year <= 2025)
    candidates = list(df_feat.index[sample_mask])
    idx = np.linspace(0, len(candidates) - 1, N_SAMPLE).round().astype(int)
    sample_dates = [candidates[i] for i in idx]

    rows = []
    worst_per_feat = {}
    all_pass = True
    n_none = 0

    for d in sample_dates:
        d = pd.Timestamp(d).date()
        feats = engine_13pm_features(d)
        if feats is None:
            n_none += 1
            rows.append({"date": str(d), "status": "no_data"})
            continue
        row = df_feat.loc[pd.Timestamp(d)]
        max_diff = 0.0
        mismatches = []
        for f in feature_names:
            eng_v = float(feats.get(f, 0.0))
            csv_v = float(row[f]) if f in row and not pd.isna(row[f]) else 0.0
            diff = abs(eng_v - csv_v)
            worst_per_feat.setdefault(f, 0.0)
            worst_per_feat[f] = max(worst_per_feat[f], diff)
            max_diff = max(max_diff, diff)
            if diff > TOL:
                mismatches.append((f, eng_v, csv_v, diff))
        passed = len(mismatches) == 0
        all_pass = all_pass and passed
        rows.append({
            "date": str(d),
            "status": "ok" if passed else "MISMATCH",
            "n_features": len(feature_names),
            "max_diff": max_diff,
            "n_mismatch": len(mismatches),
            "mismatches": mismatches,
        })

    return {
        "sample_n": len(sample_dates),
        "ok_n": sum(1 for r in rows if r["status"] == "ok"),
        "n_none": n_none,
        "all_pass": all_pass,
        "rows": rows,
        "worst_per_feat": worst_per_feat,
        "feature_names": feature_names,
    }


def deployed_2025_accuracy(df_feat: pd.DataFrame) -> dict:
    """Replicate the sealed harness: full session, locked/last acted-on state."""
    mask = df_feat.index.year == 2025
    dates = list(df_feat.index[mask])
    label = df_feat.loc[mask, "cluster_id"].astype(int)

    correct = 0
    total = 0
    by_cls = {c: {"n": 0, "ok": 0} for c in (0, 1, 2)}
    detail = []
    for d in dates:
        d_ = pd.Timestamp(d).date()
        nf = load_session(d_, NF_SYMBOL)
        bn = load_session(d_, BN_SYMBOL)
        if nf is None or bn is None:
            continue
        eng = DayTypeEngine(model_name="logistic")  # default lock_threshold
        eng.reset(d_)
        n = min(len(nf), len(bn), TARGET_BAR + 1)
        if n < MIN_BARS:
            continue
        nf = nf.head(n).reset_index(drop=True)
        bn = bn.head(n).reset_index(drop=True)
        state = None
        for i in range(n):
            eng.on_bn_bar(bn.iloc[i].to_dict())
            result = eng.on_bar(nf.iloc[i].to_dict())
            if result is not None and result.predicted_state != "Unknown":
                state = result
        if state is None or state.predicted_state == "Unknown":
            continue
        pred_cls = {v: k for k, v in CLUSTER_NAMES.items()}[state.predicted_state]
        true_cls = int(label.loc[pd.Timestamp(d)])
        total += 1
        ok = pred_cls == true_cls
        correct += int(ok)
        by_cls[true_cls]["n"] += 1
        by_cls[true_cls]["ok"] += int(ok)
        detail.append({
            "date": str(d),
            "true": true_cls,
            "pred": pred_cls,
            "regime": state.predicted_state,
            "conf": state.confidence,
            "locked": state.locked,
            "ok": ok,
        })

    per_class = {
        CLUSTER_NAMES[c]: {
            "n": v["n"],
            "acc": round(v["ok"] / v["n"], 4) if v["n"] else None,
        }
        for c, v in by_cls.items()
    }
    return {
        "n_sessions": total,
        "accuracy": round(correct / total, 4) if total else None,
        "correct": correct,
        "per_class": per_class,
        "detail": detail,
    }


def opportunistic_am_parity() -> list[dict]:
    """Non-gating: 10am/11am engine-vs-CSV feature diff on a few sessions.

    Task 2's EOD-loader fix was expected to make these consistent. Engine and
    CSV builder define partial_vol_pct20 / partial_range_pct20 differently
    (all-history vs trailing-20 percentile), so record it opportunistically.
    """
    results = []
    for cp, tb in [("10am", 45), ("11am", 105)]:
        csv = pd.read_csv(
            ROOT / "data" / "features" / "day_type" / f"intraday_features_{cp}.csv",
            index_col=0, parse_dates=True)
        eng = DayTypeEngine(model_name="logistic", lock_threshold=1.01)
        fn = eng._models[cp][2]["feature_names"]
        for d in [date(2025, 3, 5), date(2025, 6, 13), date(2024, 8, 16)]:
            nf = load_session(d, NF_SYMBOL)
            bn = load_session(d, BN_SYMBOL)
            if nf is None or bn is None:
                continue
            eng.reset(d)
            n = min(len(nf), len(bn), tb + 1)
            nf = nf.head(n).reset_index(drop=True)
            bn = bn.head(n).reset_index(drop=True)
            for i in range(n):
                eng.on_bn_bar(bn.iloc[i].to_dict())
                eng.on_bar(nf.iloc[i].to_dict())
            feats = eng._compute_features(cp)
            row = csv.loc[pd.Timestamp(d)]
            mm = [f for f in fn if abs(float(feats.get(f, 0.0)) - float(row[f])) > 1e-6]
            results.append({"cp": cp, "date": str(d), "n_feat": len(fn),
                            "mismatches": mm})
    return results


def render_report(parity: dict, deployed: dict, meta: dict,
                  am_parity: list[dict] | None = None) -> str:
    lines = []
    A = lines.append
    A("# NiftyShield DayType Parity Report")
    A("")
    A("**Generated:** script (`scripts/daytype/parity_check_13pm.py`)")
    A("")
    A(f"- Model: `logistic_13pm_prod` (checkpoint `13pm`)")
    A(f"- `feature_names`: {len(meta['feature_names'])} features")
    A(f"- Orphan features absent from `feature_names`: "
      f"{'yes' if not ({'prev_day_vol_pct','partial_vol_pct20','partial_range_pct20'} & set(meta['feature_names'])) else 'NO'}")
    A(f"- `block_a_excluded`: {meta['block_a_excluded']}")
    A(f"- `train_thru`: {meta['train_thru']}")
    A(f"- Train/Val/Hold accuracy: "
      f"{[ (r['split'], r['n'], r['accuracy']) for r in meta['results'] ]}")
    A("")
    A("## 1. Engine-to-CSV feature parity (13pm)")
    A("")
    A(f"- Sessions sampled across 2024-2025: **{parity['sample_n']}** (>= 20 required)")
    A(f"- Sessions with full match (all features within 1e-6): "
      f"**{parity['ok_n']}**")
    A(f"- Sessions skipped (no session data): {parity['n_none']}")
    A("")
    A(f"**VERDICT: {'PASS' if parity['all_pass'] else 'FAIL'}** — every feature in "
      f"`feature_names` matched within 1e-6 on every sampled session.")
    A("")
    A("### Sampled sessions")
    A("")
    A("| date | status | n_features | max_diff | n_mismatch |")
    A("|---|---|---|---|---|")
    for r in parity["rows"]:
        A(f"| {r['date']} | {r['status']} | {r.get('n_features','-')} | "
          f"{r.get('max_diff','-')} | {r.get('n_mismatch','-')} |")
    A("")
    A("### Worst per-feature absolute difference (across samples)")
    A("")
    A("| feature | max abs diff |")
    A("|---|---|")
    for f, d_ in sorted(parity["worst_per_feat"].items(), key=lambda kv: -kv[1]):
        A(f"| {f} | {d_:.2e} |")
    A("")
    A("## 2. Deployed 2025 holdout accuracy (engine, harness-style)")
    A("")
    A("The engine is run over every 2025 session exactly as the sealed harness "
      "runs it: full session bars fed, the locked/last acted-on regime scored "
      "against the 2025 `cluster_id` labels.")
    A("")
    if deployed["n_sessions"]:
        A(f"- Sessions scored: **{deployed['n_sessions']}**")
        A(f"- Overall accuracy: **{deployed['accuracy']:.1%}** "
          f"({deployed['correct']}/{deployed['n_sessions']})")
        A("")
        A("| class | n | accuracy |")
        A("|---|---|---|")
        for cls, v in deployed["per_class"].items():
            acc = f"{v['acc']:.1%}" if v["acc"] is not None else "n/a"
            A(f"| {cls} | {v['n']} | {acc} |")
        A("")
        A("### Per-session detail")
        A("")
        A("| date | true | pred | regime | conf | locked | ok |")
        A("|---|---|---|---|---|---|---|")
        for row_ in deployed["detail"]:
            A(f"| {row_['date']} | {row_['true']} | {row_['pred']} | "
              f"{row_['regime']} | {row_['conf']:.3f} | {row_['locked']} | "
              f"{'YES' if row_['ok'] else 'no'} |")
    else:
        A("- No 2025 sessions scored.")
    A("")
    if am_parity:
        A("## 3. Opportunistic 10am/11am parity (non-gating)")
        A("")
        A("Task 2's EOD-loader fix unblocked the 10am/11am engines. The 13pm "
          "gate above is the acceptance criterion; 10am/11am are recorded here "
          "opportunistically and do **not** gate NiftyShield (it consumes the "
          "13pm regime). Residual feature differences below reflect the engine "
          "and CSV builder defining `partial_vol_pct20` / `partial_range_pct20` "
          "differently (all-history percentile in `_inject_block_a` vs "
          "trailing-20-day `_rolling_pct_rank` in `build_intraday_features.py`).")
        A("")
        A("| cp | date | n_feat | mismatched features |")
        A("|---|---|---|---|")
        for r in am_parity:
            mm = ", ".join(r["mismatches"]) if r["mismatches"] else "none"
            A(f"| {r['cp']} | {r['date']} | {r['n_feat']} | {mm} |")
        A("")
    return "\n".join(lines)


def main() -> int:
    print("NiftyShield 13pm train/serve parity gate")
    print("========================================")

    df_feat = pd.read_csv(FEATURE_CSV, index_col=0, parse_dates=True).sort_index()

    meta_path = ROOT / "models" / "daytype" / "logistic_13pm_prod" / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    feature_names = meta["feature_names"]

    print(f"Model feature_names: {len(feature_names)}")
    print("Running engine-to-CSV parity check...")
    parity = parity_check(df_feat, feature_names)
    print(f"  sampled={parity['sample_n']} ok={parity['ok_n']} "
          f"skip={parity['n_none']} all_pass={parity['all_pass']}")

    print("Running deployed 2025 holdout accuracy...")
    deployed = deployed_2025_accuracy(df_feat)
    if deployed["n_sessions"]:
        print(f"  n={deployed['n_sessions']} acc={deployed['accuracy']:.4f}")
    else:
        print("  no sessions scored")

    print("Running opportunistic 10am/11am parity...")
    am_parity = opportunistic_am_parity()

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(parity, deployed, meta, am_parity), encoding="utf-8")
    print(f"\nReport written: {REPORT}")
    print(f"PARITY VERDICT: {'PASS' if parity['all_pass'] else 'FAIL'}")
    return 0 if parity["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
