"""JEV-NMS-1 §28 step 2 (B2/B3) — §14 selection and fit on D-fit, per horizon.

Rulings applied (2026-09-18): B2 standardized once with the full-D-fit mean and
population SD (ddof=0; G-5, Q3); selection criterion = mean log-loss over ALL
out-of-fold observations (Q4) of probabilities clipped at >= 1e-4 and
renormalized (Q5); B2 C per horizon (A2-3); ties within 1e-12 -> first in
list/grid order.

Stage `equivalence` runs the full selection under each fold-allocation
convention for 442 sessions (Q2): A = np.array_split (first blocks larger),
B = last blocks larger, C = boundaries floor(i*n/5 + 1/2). Stage `fit` refuses
to run unless every convention selected the same hyperparameters, then refits
on all D-fit and persists the models. Both artifacts are create-only.
"""
from __future__ import annotations

import os

if os.environ.get("OMP_NUM_THREADS") != "1":
    raise SystemExit("OMP_NUM_THREADS=1 must be set in the environment before launch (§14)")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import itertools  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import pickle  # noqa: E402
import warnings  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import sklearn  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
CONFIG = REPO / "governance" / "jev_nms_1" / "config.json"
FEATURES_SHA256 = "29997617dba1888c4f66ff28da85e4ad42f3866b8b5bcd59d2b43e0404049eb3"
DFIT_SHA256 = "656ed4ddf3ee19d264c2dc8183844f329881bf14ca2e77c7dfb87e6d8bafe88d"
EQUIVALENCE_NAME = "fold_equivalence_step2.json"
FIT_NAME = "b2_b3_step2.json"
HORIZONS = (5, 15, 30)
CLASSES = ("trending_up", "trending_down", "range_bound", "disorderly")
FIELDS = ("minutes_since_open", "gap_bp", "ret_open_bp", "ret_15_bp", "ret_30_bp",
          "rv_30_bp", "range_30_bp", "er_30", "twap_dist_bp")
SLOTS = ("10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30")
CONVENTIONS = ("A", "B", "C")
K = 5


def _load(name: str, sha: str) -> dict:
    raw = (OUT / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise RuntimeError(f"{name} does not match its recorded SHA-256")
    return json.loads(raw.decode("utf-8"))


def dataset() -> tuple[list[str], np.ndarray, dict]:
    """D-fit states in (date, slot) order: dates, X (9 rounded features), y per horizon."""
    feats = _load("features_step2.json", FEATURES_SHA256)["states"]
    dfit = _load("dfit_constants_step2.json", DFIT_SHA256)
    rows = dfit["states"]["15"]
    keys = [f"{r['date']}|{r['slot']}" for r in rows]
    for h in HORIZONS:
        if [f"{r['date']}|{r['slot']}" for r in dfit["states"][str(h)]] != keys:
            raise RuntimeError("label rows are not aligned across horizons")
    if keys != sorted(keys, key=lambda k: (k[:10], SLOTS.index(k[11:]))):
        raise RuntimeError("D-fit states are not in (date, slot) order")
    X = np.array([[feats[k][f] for f in FIELDS] for k in keys], dtype=np.float64)
    y = {h: np.array([r["label"] for r in dfit["states"][str(h)]]) for h in HORIZONS}
    return [k[:10] for k in keys], X, y


def fold_sizes(n: int, convention: str) -> list[int]:
    base, extra = divmod(n, K)
    if convention == "A":
        return [base + (i < extra) for i in range(K)]
    if convention == "B":
        return [base + (i >= K - extra) for i in range(K)]
    bounds = [math.floor(i * n / K + 0.5) for i in range(K + 1)]
    return [bounds[i + 1] - bounds[i] for i in range(K)]


def fold_of_state(dates: list[str], convention: str) -> np.ndarray:
    sessions = sorted(set(dates))
    fold, i = {}, 0
    for f, size in enumerate(fold_sizes(len(sessions), convention)):
        for d in sessions[i:i + size]:
            fold[d] = f
        i += size
    return np.array([fold[d] for d in dates])


def clipped(proba: np.ndarray, classes: np.ndarray) -> np.ndarray:
    """Columns reordered by class NAME into CLASSES order; clip >= 1e-4; renormalize."""
    idx = [list(classes).index(c) for c in CLASSES]
    p = np.maximum(proba[:, idx], 1e-4)
    return p / p.sum(axis=1, keepdims=True)


def mean_log_loss(p: np.ndarray, y: np.ndarray) -> float:
    true = np.array([CLASSES.index(c) for c in y])
    return float(-np.mean(np.log(p[np.arange(len(y)), true])))


def standardize(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean, sd = X.mean(axis=0), X.std(axis=0, ddof=0)
    return (X - mean) / sd, mean, sd


def b2(cfg: dict, c: float) -> LogisticRegression:
    b = cfg["B2"]
    return LogisticRegression(C=c, solver=b["solver"], max_iter=b["max_iter"], tol=b["tol"])


def b3(cfg: dict, point: dict) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(**cfg["B3"]["fixed"], **point)


def b3_grid(cfg: dict) -> list[dict]:
    order, grid = cfg["B3"]["grid_order"], cfg["B3"]["grid"]
    return [dict(zip(order, vals)) for vals in itertools.product(*(grid[k] for k in order))]


def fit_logged(model, X, y, log: list, tag: str):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(X, y)
    log += [{"fit": tag, "category": w.category.__name__, "message": str(w.message)} for w in caught]
    return model


def oof_loss(make, X, y, folds, log, tag) -> float:
    p = np.zeros((len(y), len(CLASSES)))
    for f in range(K):
        tr, te = folds != f, folds == f
        m = fit_logged(make(), X[tr], y[tr], log, f"{tag} fold{f}")
        p[te] = clipped(m.predict_proba(X[te]), m.classes_)
    return mean_log_loss(p, y)


def select(losses: list[float]) -> int:
    best = min(losses)
    return next(i for i, v in enumerate(losses) if v - best <= 1e-12)


def run_convention(conv, cfg, dates, X, Xs, y, log) -> dict:
    folds = fold_of_state(dates, conv)
    grid, cs = b3_grid(cfg), cfg["B2"]["C_grid"]
    out = {"fold_sizes": fold_sizes(len(set(dates)), conv), "horizons": {}}
    for h in HORIZONS:
        l2 = [oof_loss(lambda c=c: b2(cfg, c), Xs, y[h], folds, log, f"{conv} h{h} B2 C={c}")
              for c in cs]
        l3 = [oof_loss(lambda g=g: b3(cfg, g), X, y[h], folds, log, f"{conv} h{h} B3 {i}")
              for i, g in enumerate(grid)]
        i2, i3 = select(l2), select(l3)
        out["horizons"][str(h)] = {
            "b2_oof_log_loss": dict(zip(map(str, cs), l2)), "b2_selected_C": cs[i2],
            "b3_oof_log_loss": l3, "b3_selected_index": i3, "b3_selected": grid[i3]}
        print(conv, h, "B2 C", cs[i2], "B3", i3, grid[i3], flush=True)
    return out


def equivalence() -> dict:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    dates, X, y = dataset()
    Xs, _, _ = standardize(X)
    log: list = []
    results = {c: run_convention(c, cfg, dates, X, Xs, y, log) for c in CONVENTIONS}
    decisions = {c: {h: (r["horizons"][h]["b2_selected_C"], r["horizons"][h]["b3_selected_index"])
                     for h in r["horizons"]} for c, r in results.items()}
    return {"conventions": results, "decisions": decisions,
            "all_equal": len({json.dumps(d, sort_keys=True) for d in decisions.values()}) == 1,
            "b3_grid": b3_grid(cfg), "warnings": log}


def fit() -> dict:
    eq = _load(EQUIVALENCE_NAME, _ledger_sha(EQUIVALENCE_NAME))
    if not eq["all_equal"]:
        raise SystemExit("fold conventions disagree; a Q2 ruling is required before fitting")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    dates, X, y = dataset()
    Xs, mean, sd = standardize(X)
    sel = eq["conventions"]["A"]["horizons"]
    log: list = []
    out = {"b2": {}, "b3": {}}
    for h in HORIZONS:
        s = sel[str(h)]
        m2 = fit_logged(b2(cfg, s["b2_selected_C"]), Xs, y[h], log, f"final h{h} B2")
        out["b2"][str(h)] = {"C": s["b2_selected_C"], "classes": list(m2.classes_),
                             "coef": m2.coef_.tolist(), "intercept": m2.intercept_.tolist(),
                             "n_iter": m2.n_iter_.tolist()}
        m3 = fit_logged(b3(cfg, s["b3_selected"]), X, y[h], log, f"final h{h} B3")
        again = b3(cfg, s["b3_selected"]).fit(X, y[h])
        if not np.array_equal(m3.predict_proba(X), again.predict_proba(X)):
            raise RuntimeError(f"B3 h{h} refit is not deterministic")
        blob = pickle.dumps(m3, protocol=5)
        path = OUT / f"b3_h{h}_step2.pkl"
        with open(path, "xb") as fh:
            fh.write(blob)
        out["b3"][str(h)] = {"params": s["b3_selected"], "grid_index": s["b3_selected_index"],
                             "classes": list(m3.classes_), "n_iter": m3.n_iter_,
                             "pickle": path.name, "pickle_sha256": hashlib.sha256(blob).hexdigest(),
                             "d_fit_in_sample_log_loss": mean_log_loss(
                                 clipped(m3.predict_proba(X), m3.classes_), y[h])}
        out["b2"][str(h)]["d_fit_in_sample_log_loss"] = mean_log_loss(
            clipped(m2.predict_proba(Xs), m2.classes_), y[h])
    out["standardization"] = {"fields": list(FIELDS), "mean": mean.tolist(), "sd_ddof0": sd.tolist()}
    out["selection_convention"] = "A (np.array_split); equivalent to B and C per fold_equivalence_step2.json"
    out["warnings"] = log
    return out


def _ledger_sha(name: str) -> str:
    for line in reversed((OUT / "ledger.jsonl").read_text(encoding="utf-8").splitlines()):
        rec = json.loads(line)
        if rec.get("artifact") == name:
            return rec["sha256"]
    raise RuntimeError(f"{name} has no ledger entry")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=("equivalence", "fit"))
    args = ap.parse_args()
    name = EQUIVALENCE_NAME if args.stage == "equivalence" else FIT_NAME
    target = OUT / name
    if target.exists():
        raise SystemExit(f"{target} exists; never refit")
    art = equivalence() if args.stage == "equivalence" else fit()
    art.update({"protocol_id": "JEV-NMS-1", "stage": args.stage,
                "features_sha256": FEATURES_SHA256, "dfit_constants_sha256": DFIT_SHA256,
                "sklearn": sklearn.__version__, "numpy": np.__version__,
                "omp_num_threads": os.environ["OMP_NUM_THREADS"],
                "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    with open(target, "x", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(art, indent=1, sort_keys=True))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with open(OUT / "ledger.jsonl", "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"event": f"b2_b3_{args.stage}", "at": art["built_at"],
                             "artifact": name, "sha256": digest,
                             "warnings": len(art["warnings"])}) + "\n")
        for w in art["warnings"]:  # §14: convergence/deprecation warnings go to the ledger
            fh.write(json.dumps({"event": "fit_warning", "artifact": name, **w}) + "\n")
    print(f"{target}  sha256={digest}")


if __name__ == "__main__":
    main()
