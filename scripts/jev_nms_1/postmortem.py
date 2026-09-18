"""JEV-NMS-1 forensic post-mortem diagnostics — POST-MORTEM / NON-CONFIRMATORY.

Descriptive only. No Jev or network call, no refit, no selection, no new test
of any JEV-NMS-1 hypothesis. Inputs are the committed, hash-verified artifacts:
the cache (Jev responses), `development_step6.json` (stored fold pool
parameters), the frozen B3 pickles and D-fit constants, and the store files
(SHA-256-checked) for labels. The frozen B3 is only *applied*; the stored pool
parameters are only *re-applied*, so the recorded OOF dLL must be reproduced
exactly (an integrity check, not a new result).

Writes one new file, `postmortem_diagnostics.json` (create-only). No existing
artifact is modified.
"""
from __future__ import annotations

import os

if os.environ.get("OMP_NUM_THREADS") != "1":
    raise SystemExit("OMP_NUM_THREADS=1 must be set in the environment before launch (§14)")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from scipy.stats import rankdata, spearmanr  # noqa: E402

from scripts.jev_nms_1 import dev, dev_analysis as da  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
ARTIFACT_NAME = "postmortem_diagnostics.json"
DEV_SHA256 = "3fc16a452da9630dfeac95dd9616df21e56a32a5cd6b0963db01b17b3bdd669d"
CACHE_SHA256 = "fd27d793be510a1998d80b4d9a556e67fd0256d134a1e7d84cec3fd6f6a839c9"
L3_SHA256 = "cb67b5551371ce5d85c4085cff004c0a70b557d411654f309605f0a90fc72c35"
C = da.CLASSES


def _load(name: str, sha: str) -> bytes:
    raw = (OUT / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise RuntimeError(f"{name} does not match its recorded SHA-256")
    return raw


def auc(score: np.ndarray, positive: np.ndarray) -> float:
    """One-vs-rest ROC AUC by the rank-sum formula (ties get average ranks)."""
    r = rankdata(score)
    n1, n0 = positive.sum(), (~positive).sum()
    return float((r[positive].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def horizon_rows(h, sessions, recs, feats, lab, consts, fit, models):
    keys = [f"{s}|{sl}" for s in sorted(sessions) for sl in da.SLOTS]
    X = np.array([[feats["states"][k][f] for f in da.FIELDS] for k in keys])
    y = np.array([C.index(lab[(k, h)][0]) for k in keys])
    det = da.deterministic(keys, X, lab, h, consts, fit, models)
    raw = [recs[(f"h{h}", k)]["validity"]["probabilities"] for k in keys]
    pj_raw = np.array([da.vec(p) for p in raw])
    return keys, X, y, det, pj_raw


def oof_from_stored(h_art, keys, lb3, lj):
    """Re-apply the stored fold parameters (no fit) to get OOF B3* and B3+J."""
    fold = {s: i for i, b in enumerate(h_art["blocks"]) for s in b}
    f = np.array([fold[k[:10]] for k in keys])
    ps, pp = np.zeros_like(lb3), np.zeros_like(lb3)
    for prm in h_art["fold_params"]:
        m = f == prm["fold"]
        ps[m] = da.clip(da.pool_proba(prm["b3_star"]["theta"], lb3[m], lj[m], False))
        pp[m] = da.clip(da.pool_proba(prm["b3_plus_j"]["theta"], lb3[m], lj[m], True))
    return ps, pp


def information(pj, pb3, pstar, y, X) -> dict:
    out = {"per_class": {}}
    for k, c in enumerate(C):
        pos = y == k
        out["per_class"][c] = {
            "spearman_pJ_vs_pB3": float(spearmanr(pj[:, k], pb3[:, k]).statistic),
            "auc_J": auc(pj[:, k], pos), "auc_B3": auc(pb3[:, k], pos), "auc_B3star": auc(pstar[:, k], pos),
            "mean_pJ_when_true": float(pj[pos, k].mean()), "mean_pJ_when_false": float(pj[~pos, k].mean()),
            "mean_pB3_when_true": float(pb3[pos, k].mean()), "mean_pB3_when_false": float(pb3[~pos, k].mean())}
    top_j, top_b = da.argmax_idx(pj), da.argmax_idx(pb3)
    out["argmax_agreement_J_B3"] = float((top_j == top_b).mean())
    out["mean_abs_prob_diff_J_B3"] = float(np.abs(pj - pb3).sum(axis=1).mean() / 2)
    kl = (pj * (np.log(pj) - np.log(pb3))).sum(axis=1)
    out["mean_KL_J_to_B3_nats"] = float(kl.mean())
    # does Jev read its inputs? direction and turbulence (association sanity check)
    fi = {f: i for i, f in enumerate(da.FIELDS)}
    tilt = pj[:, 0] - pj[:, 1]
    out["input_response"] = {
        "spearman_pJup_minus_pJdown_vs_ret_15_bp": float(spearmanr(tilt, X[:, fi["ret_15_bp"]]).statistic),
        "spearman_pJup_minus_pJdown_vs_ret_30_bp": float(spearmanr(tilt, X[:, fi["ret_30_bp"]]).statistic),
        "spearman_pJdisorderly_vs_rv_30_bp": float(spearmanr(pj[:, 3], X[:, fi["rv_30_bp"]]).statistic),
        "spearman_pJ_trend_total_vs_er_30": float(spearmanr(pj[:, 0] + pj[:, 1], X[:, fi["er_30"]]).statistic),
        "spearman_pB3up_minus_pB3down_vs_ret_15_bp": float(spearmanr(pb3[:, 0] - pb3[:, 1],
                                                                      X[:, fi["ret_15_bp"]]).statistic),
        "spearman_realized_up_minus_down_vs_ret_15_bp": float(spearmanr(
            (y == 0).astype(float) - (y == 1).astype(float), X[:, fi["ret_15_bp"]]).statistic)}
    return out


def class_usage(models: dict, y: np.ndarray) -> dict:
    out = {"realized_base_rate": {c: float((y == k).mean()) for k, c in enumerate(C)}}
    for n, p in models.items():
        top = da.argmax_idx(p)
        out[n] = {"mean_probability": {c: float(p[:, k].mean()) for k, c in enumerate(C)},
                  "argmax_share": {c: float((top == k).mean()) for k, c in enumerate(C)},
                  "log_loss_by_true_class": {c: float(-np.log(p[y == k, k]).mean()) for k, c in enumerate(C)},
                  "recall_by_true_class": {c: float((top[y == k] == k).mean()) for k, c in enumerate(C)}}
    return out


def calibration(pj_raw, pj, y, pstar) -> dict:
    vals = np.round(pj_raw, 6)
    true_raw = pj_raw[np.arange(len(y)), y]
    lj = da.losses(pj, y)
    zero_true = true_raw == 0
    sums = pj_raw.sum(axis=1)
    conf = pj.max(axis=1)
    top = da.argmax_idx(pj)
    groups = {}
    for lo, hi in ((0, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 0.75), (0.75, 1.01)):
        m = (conf >= lo) & (conf < hi)
        if m.any():
            groups[f"[{lo:.2f},{hi:.2f})"] = {
                "n": int(m.sum()), "mean_conf": float(conf[m].mean()), "accuracy": float((top[m] == y[m]).mean()),
                "argmax_share": {c: float((top[m] == k).mean()) for k, c in enumerate(C)},
                "B3star_accuracy": float((da.argmax_idx(pstar[m]) == y[m]).mean())}
    # per-class calibration in the large: mean predicted vs realized frequency
    return {
        "distinct_probability_values": int(len(np.unique(vals))),
        "all_two_decimal": bool(np.allclose(vals * 100, np.round(vals * 100))),
        "raw_sum_min": float(sums.min()), "raw_sum_max": float(sums.max()),
        "share_sums_not_1": float((np.abs(sums - 1) > 1e-9).mean()),
        "raw_zero_probabilities": int((pj_raw == 0).sum()),
        "true_class_raw_zero_count": int(zero_true.sum()),
        "log_loss_total": float(lj.mean()),
        "log_loss_contribution_of_true_class_zero_obs": float(lj[zero_true].sum() / len(y)),
        "log_loss_excluding_true_class_zero_obs": float(lj[~zero_true].mean()) if (~zero_true).any() else None,
        "renormalization_effect_max_abs_log": float(np.abs(np.log(sums)).max()),
        "confidence_groups": groups,
        "spearman_conf_vs_correct": float(spearmanr(conf, (top == y).astype(float)).statistic),
    }


def l3_noise(store: Path, consts: dict, elig: dict) -> dict:
    l3 = json.loads(_load("l3_step5.json", L3_SHA256))
    recs = {r["state"]: {} for r in l3["records"]}
    for r in l3["records"]:
        recs[r["state"]][r["replicate"]] = da.clip(da.vec(r["validity"]["probabilities"]))
    sess = {r["date"]: r for n in ("d_fit", "d_eval") for r in elig["sessions"][n]}
    lab = da.labels_for(store, [sess[d] for d in sorted({s[:10] for s in recs})], consts)
    diffs, l0s = [], []
    for s, rep in recs.items():
        k = C.index(lab[(s, 15)][0])
        l0, l1 = -np.log(rep[0][k]), -np.log(rep[1][k])
        diffs.append(l1 - l0)
        l0s.append(l0)
    d = np.array(diffs)
    return {"states": len(d), "mean_abs_replicate_logloss_diff": float(np.abs(d).mean()),
            "max_abs_replicate_logloss_diff": float(np.abs(d).max()),
            "mean_replicate_logloss_diff": float(d.mean()),
            "rep0_mean_log_loss_on_l3_states": float(np.mean(l0s)),
            "sd_of_mean_diff_over_50": float(d.std(ddof=1) / np.sqrt(len(d)))}


def integrity(recs, feats, h_art_all, reproduced) -> dict:
    mism = 0
    for (tpl, key), r in recs.items():
        state = json.loads(r["request_bytes"])["state"]
        sealed = {k: v for k, v in feats["states"][key].items() if k != "set"}
        if {k: float(v) for k, v in state.items()} != {k: float(v) for k, v in sealed.items()}:
            mism += 1
    order_ok = all(json.loads(r["response_raw"])["answers"][r["question_id"]]["probabilities"]
                   == r["validity"]["probabilities"] for r in recs.values())
    return {"request_state_equals_sealed_features_mismatches": mism,
            "raw_probabilities_keyed_by_class_name_equal_parse": order_ok,
            "stored_fold_params_reproduce_recorded_oof_dll": reproduced,
            "fold_sizes_h15": [p["n_test"] for p in h_art_all["15"]["fold_params"]]}


def build(store: Path) -> dict:
    art = json.loads(_load("development_step6.json", DEV_SHA256))
    _load("cache.jsonl", CACHE_SHA256)
    consts = da._json("dfit_constants_step2.json", da.FROZEN["dfit_constants_step2.json"])
    fit = da._json("b2_b3_step2.json", da.FROZEN["b2_b3_step2.json"])
    models = da.load_models(fit)
    elig, draws, feats = (dev._artifact(n) for n in ("eligibility_step1.json", "draws_step2.json",
                                                      "features_step2.json"))
    cache = dev._cache()
    recs = {(r["template"], r["state"]): r for r in cache.values() if r["stage"] == "development"}
    d = draws["draws"]
    er = {r["date"]: r for r in elig["sessions"]["d_eval"]}
    lab = da.labels_for(store, [er[s] for s in sorted(d["d1_dev"]["output"])], consts)

    out = {"label": "POST-MORTEM / NON-CONFIRMATORY", "inputs": {
        "development_step6.json": DEV_SHA256, "cache.jsonl": CACHE_SHA256, "l3_step5.json": L3_SHA256,
        **da.FROZEN, **{f"b3_h{h}_step2.pkl": v for h, v in da.PICKLES.items()}}, "horizons": {}}
    reproduced = {}
    for h, sessions in ((15, d["d1_dev"]["output"]), (5, d["d2_dev_secondary"]["output"]),
                        (30, d["d2_dev_secondary"]["output"])):
        keys, X, y, det, pj_raw = horizon_rows(h, sessions, recs, feats, lab, consts, fit, models)
        pj = da.clip(pj_raw)
        ha = art["horizons"][str(h)]
        pstar, ppool = oof_from_stored(ha, keys, np.log(det["B3"]), np.log(pj))
        val = da.dll(np.array([k[:10] for k in keys]), da.losses(pstar, y) - da.losses(ppool, y),
                     sorted(sessions))[0]
        reproduced[str(h)] = {"recomputed": val, "recorded": ha["oof_dll"], "exact": val == ha["oof_dll"]}
        entry = {"n": len(y), "information": information(pj, det["B3"], pstar, y, X),
                 "class_usage": class_usage({**det, "J": pj, "B3*": pstar, "B3+J": ppool}, y),
                 "calibration_J": calibration(pj_raw, pj, y, pstar),
                 "pool": {"oof_fold_b": [p["b3_plus_j"]["b"] for p in ha["fold_params"]],
                          "full_b": ha["b_hat_full"], "full_a": ha["full_sample_b3_plus_j"]["a"],
                          "b3star_full_a": ha["full_sample_b3_star"]["a"],
                          "full_nll_improvement_from_J_nats_total": ha["full_sample_b3_star"]["nll"]
                          - ha["full_sample_b3_plus_j"]["nll"],
                          "full_nll_improvement_per_obs": (ha["full_sample_b3_star"]["nll"]
                                                           - ha["full_sample_b3_plus_j"]["nll"]) / len(y),
                          "sd_of_lnpJ_centered": float((np.log(pj) - np.log(pj).mean(axis=1, keepdims=True)).std()),
                          "sd_of_lnpB3_centered": float((np.log(det["B3"]) - np.log(det["B3"]).mean(
                              axis=1, keepdims=True)).std())}}
        out["horizons"][str(h)] = entry
    out["integrity"] = integrity(recs, feats, art["horizons"], reproduced)
    out["l3_noise"] = l3_noise(store, consts, elig)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, required=True)
    args = ap.parse_args()
    target = OUT / ARTIFACT_NAME
    if target.exists():
        raise SystemExit("post-mortem artifact exists")
    out = build(args.store)
    with open(target, "x", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(out, indent=1, sort_keys=True))
    print(hashlib.sha256(target.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
