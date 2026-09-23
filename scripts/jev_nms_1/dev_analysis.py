"""JEV-NMS-1 development analysis (§14-§24), from the append-only cache only.

Frozen inputs, never re-estimated: §8 thresholds and §9 scales, B0/B1 tables
(`dfit_constants_step2.json`), B2 coefficients and B3 pickles selected and fit
on D-fit at step 2 (`b2_b3_step2.json`). No D-fit fit or hyperparameter
selection happens here (§26, §28 item 3). D-eval labels are computed by
APPLYING the frozen constants through the same `dfit` code path.

Rules applied (§14-§17, §24, A2, A3):
- Probabilities: every model's vector mapped by class name, clipped at 1e-4,
  renormalized, then scored (Q5); also applied to the pool's softmax output.
- Arg-max: first class in the frozen class order among exact maxima (A3-1).
- Pool (§16): logit_k = a ln p_B3,k + b ln p_J,k + c_k, sum c_k = 0; B3* has
  b = 0. Maximum likelihood.
- Cross-fitting: the 100 development sessions sorted by date into 5 contiguous
  blocks of 20; fit on 4 blocks, predict the held-out block. All development
  dLL is out of fold. Paired exclusion: an observation with an invalid Jev
  response is removed from both models and counted.
- dLL = session-weighted mean of session means of (l_B3* - l_B3+J), weight =
  valid observations per session.
- b-hat: B3+J fit once on every valid h15 observation (full permitted sample).
- §24 rule 4: OOF dLL <= 0 -> NULL. Rule 5: b-hat <= 0 -> NULL. Rule 6:
  n_req > 250 -> NULL.

Implementation choices not fixed by the protocol, pre-declared in this
docstring at the commit made before any development call:
- P1 optimizer: scipy.optimize.minimize(method="BFGS") with the analytic
  gradient of the MEAN negative log-likelihood, gtol 1e-9, start a=1, b=0,
  c=0; the negative log-likelihood is convex, so the optimum is unique. Parameters: (a, b, c1, c2, c3), c4 = -sum.
- P2 n_req (§23): smallest n with one-sided one-sample t-test power >= 0.80
  at alpha 0.05 (noncentral t; `scripts/rfa/power.py`, the repository's power
  convention), delta = 0.5 x OOF dLL, SD = sample SD (ddof 1) of the 100
  per-session OOF dLL means. Also reported: ddof 0 and the normal
  approximation. If the variants disagree on rule 6 or on N_P = max(120,
  n_req), the rule-6 outcome is flagged for an operator ruling.
- P3 secondary horizons: the 30 D2 sessions sorted by date into 5 contiguous
  blocks of 6 (primary reading); the alternative (D2 sessions keep their h15
  block) is also reported.
- P4 ECE: top-label confidence, 10 equal-width bins on [0, 1] (1.0 in the last
  bin), ECE = sum n_b/N |accuracy_b - confidence_b|.
- P5 coverage (§21): confidence = max clipped probability; at coverage c the
  cut is numpy.quantile(conf, 1 - c/100, method="linear") and conf >= cut is
  retained (ties at the cut are retained; the realized count is reported).
  AURC: observations sorted by descending confidence; risk(k) = mean loss of
  the first k, evaluated at the end of each exact-tie group (tie-order
  invariant); AURC = mean of risk(k), k = 1..N. The "descriptive test" of
  whether B3* loss is higher where J is least confident: Spearman correlation
  of J confidence with B3* log-loss, one-sided (alternative "less").
- P6 descriptive inference on development (the §19/§20 machinery is defined for
  P; development versions are descriptive, non-confirmatory):
  * moving-block bootstrap over the 100 date-ordered sessions, block 5,
    10,000 iterations, numpy default_rng(42): 20 block starts drawn uniformly
    from 0..95, statistic = weighted dLL, lower bound = 0.05 quantile (linear);
  * Newey-West t (Bartlett, lag 5) and AC1 on the unweighted per-session dLL
    series in date order;
  * conditional randomization: strata = slot x B3* top class x B3* max-prob
    tercile (cuts = numpy.quantile linear 1/3 and 2/3 of the OOF B3* max
    probability over the full permitted sample; tercile 0 if <= cut1, 1 if
    <= cut2, else 2); J vectors permuted within strata, fold pool parameters
    frozen, 1,000 iterations, default_rng(42); p = share of permuted dLL >=
    observed. Cuts are reported, NOT frozen (F2 is not set here);
  * N1: J vectors permuted across sessions independently within each slot,
    pool frozen, 1,000 iterations, default_rng(42);
  * N2: J shifted cyclically by 5k sessions in date order, k = 1..19, pool
    frozen; every shift is reported.
- P7 H-exposed (§18 "deterministic models on H-exposed", EXPOSED): B0-B3 only,
  every eligible H-exposed session x ten slots, features built by the §6 code.
"""
from __future__ import annotations

import os

if os.environ.get("OMP_NUM_THREADS") != "1":
    raise SystemExit("OMP_NUM_THREADS=1 must be set in the environment before launch (§14)")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import pickle  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from scipy.optimize import minimize  # noqa: E402
from scipy.stats import norm, spearmanr  # noqa: E402

from scripts.jev_nms_1 import dev  # noqa: E402
from scripts.jev_nms_1.dfit import classify, load_closes, state_windows  # noqa: E402
from scripts.jev_nms_1.eligibility import load_seal  # noqa: E402
from scripts.jev_nms_1.features import load_window_bars, raw_features, rounded, slot_index  # noqa: E402
from scripts.jev_nms_1.rulings import frozen_argmax, load_a3  # noqa: E402
from scripts.jev_nms_1.s0 import _append  # noqa: E402
from scripts.rfa.power import n_required  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
ARTIFACT_NAME = "development_step6.json"
CLASSES = ("trending_up", "trending_down", "range_bound", "disorderly")
SLOTS = ("10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30")
FIELDS = ("minutes_since_open", "gap_bp", "ret_open_bp", "ret_15_bp", "ret_30_bp",
          "rv_30_bp", "range_30_bp", "er_30", "twap_dist_bp")
CLIP, K, SEED = 1e-4, 5, 42
FROZEN = {
    "dfit_constants_step2.json": "656ed4ddf3ee19d264c2dc8183844f329881bf14ca2e77c7dfb87e6d8bafe88d",
    "b2_b3_step2.json": "23e32d105f9953e162d0588198829e02448213cc95145a35020aed571f504959",
}
PICKLES = {
    5: "1f0e9675725c30e4323d8bf9779c43a51fceb0c3d38eece7a079d852c694908e",
    15: "b50a42de6862fda0afabe6f83a5a436b4cfa4f5e2bdaaa14c9c91a1a40fccd46",
    30: "434ecbb0a670fb8f0f4d3b238de24c1862bb103272372ba0f395d1a39022a675",
}


# ---------- probabilities and scoring ----------

def clip(p: np.ndarray) -> np.ndarray:
    p = np.maximum(np.asarray(p, dtype=np.float64), CLIP)
    return p / p.sum(axis=-1, keepdims=True)


def vec(d: dict) -> list[float]:
    return [d[c] for c in CLASSES]


def losses(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(p[np.arange(len(y)), y])


def argmax_idx(p: np.ndarray) -> np.ndarray:
    return np.array([CLASSES.index(frozen_argmax(dict(zip(CLASSES, row)), list(CLASSES))) for row in p])


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


# ---------- pool (§16) ----------

def _unpack(theta: np.ndarray, with_j: bool) -> tuple[float, float, np.ndarray]:
    if with_j:
        a, b, c3 = theta[0], theta[1], theta[2:]
    else:
        a, b, c3 = theta[0], 0.0, theta[1:]
    return a, b, np.append(c3, -c3.sum())


def pool_proba(theta, lb3, lj, with_j: bool) -> np.ndarray:
    a, b, c = _unpack(np.asarray(theta, dtype=np.float64), with_j)
    return softmax(a * lb3 + b * lj + c)


def fit_pool(lb3: np.ndarray, lj: np.ndarray, y: np.ndarray, with_j: bool) -> dict:
    onehot = np.eye(4)[y]
    n = len(y)

    def f(theta):
        a, b, c = _unpack(theta, with_j)
        z = a * lb3 + b * lj + c
        zmax = z.max(axis=1, keepdims=True)
        lse = (zmax[:, 0] + np.log(np.exp(z - zmax).sum(axis=1)))
        nll = float((lse - z[np.arange(n), y]).sum())
        r = softmax(z) - onehot
        ga, gb = float((r * lb3).sum()), float((r * lj).sum())
        gc_full = r.sum(axis=0)
        gc = gc_full[:3] - gc_full[3]
        grad = np.concatenate([[ga, gb] if with_j else [ga], gc])
        return nll / n, grad / n

    x0 = np.array([1.0, 0.0, 0.0, 0.0, 0.0] if with_j else [1.0, 0.0, 0.0, 0.0])
    res = minimize(f, x0, jac=True, method="BFGS", options={"gtol": 1e-9, "maxiter": 10_000})
    a, b, c = _unpack(res.x, with_j)
    return {"theta": res.x.tolist(), "a": float(a), "b": float(b), "c": c.tolist(),
            "nll": float(res.fun) * n, "converged": bool(res.success), "message": str(res.message),
            "n_iter": int(res.nit), "grad_max_abs": float(np.max(np.abs(res.jac)))}


def blocks(sessions: list[str]) -> list[list[str]]:
    return [list(b) for b in np.array_split(np.array(sorted(sessions)), K)]


def crossfit(obs: dict, block_of: dict) -> dict:
    """OOF B3* and B3+J probabilities per observation; fold parameters kept."""
    lb3, lj, y, sess = obs["lb3"], obs["lj"], obs["y"], obs["session"]
    fold = np.array([block_of[s] for s in sess])
    p_star, p_pool = np.zeros_like(lb3), np.zeros_like(lb3)
    params = []
    for k in range(K):
        tr, te = fold != k, fold == k
        fs = fit_pool(lb3[tr], lj[tr], y[tr], False)
        fj = fit_pool(lb3[tr], lj[tr], y[tr], True)
        p_star[te] = clip(pool_proba(fs["theta"], lb3[te], lj[te], False))
        p_pool[te] = clip(pool_proba(fj["theta"], lb3[te], lj[te], True))
        params.append({"fold": k, "n_train": int(tr.sum()), "n_test": int(te.sum()),
                       "b3_star": fs, "b3_plus_j": fj})
    return {"p_star": p_star, "p_pool": p_pool, "fold": fold, "params": params}


def dll(obs_sess: np.ndarray, d: np.ndarray, order: list[str]) -> tuple[float, np.ndarray, np.ndarray]:
    means = np.array([d[obs_sess == s].mean() for s in order])
    w = np.array([(obs_sess == s).sum() for s in order], dtype=np.float64)
    return float((means * w).sum() / w.sum()), means, w


# ---------- data ----------

def _json(name: str, sha: str) -> dict:
    raw = (OUT / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise RuntimeError(f"{name} does not match its recorded SHA-256")
    return json.loads(raw.decode("utf-8"))


def load_models(fit: dict) -> dict:
    out = {}
    for h in (5, 15, 30):
        e = fit["b3"][str(h)]
        blob = (OUT / e["pickle"]).read_bytes()
        sha = hashlib.sha256(blob).hexdigest()
        if sha != e["pickle_sha256"] or sha != PICKLES[h]:
            raise RuntimeError(f"B3 h{h} pickle does not match its recorded SHA-256")
        out[h] = pickle.loads(blob)
    return out


def b2_proba(fit: dict, h: int, X: np.ndarray) -> np.ndarray:
    st = fit["standardization"]
    Xs = (X - np.array(st["mean"])) / np.array(st["sd_ddof0"])
    e = fit["b2"][str(h)]
    raw = softmax(Xs @ np.array(e["coef"]).T + np.array(e["intercept"]))
    return clip(raw[:, [e["classes"].index(c) for c in CLASSES]])


def b3_proba(models: dict, fit: dict, h: int, X: np.ndarray) -> np.ndarray:
    raw = models[h].predict_proba(X)
    cls = list(models[h].classes_)
    if cls != fit["b3"][str(h)]["classes"]:
        raise RuntimeError("B3 class list differs from the fit artifact")
    return clip(raw[:, [cls.index(c) for c in CLASSES]])


def labels_for(store: Path, recs: list[dict], consts: dict) -> dict:
    """(date|slot, h) -> (label, trailing label), frozen constants applied."""
    out = {}
    for rec in recs:
        closes = load_closes(store, rec["date"], rec["file_sha256"])
        for s in SLOTS:
            for h in (5, 15, 30):
                w = state_windows(closes, s, h)
                c, sf, stl = consts["thresholds"][str(h)], consts["scales_forward"][str(h)][s], \
                    consts["scales_trailing"][str(h)][s]
                r, er, rv = w["fwd"]
                tr, te, trv = w["trail"]
                out[(f"{rec['date']}|{s}", h)] = (classify(r, er, r / sf, rv / sf, c),
                                                   classify(tr, te, tr / stl, trv / stl, c))
    return out


def deterministic(keys, X, lab, h, consts, fit, models) -> dict:
    slot = [k[11:] for k in keys]
    p = {"B0": clip([vec(consts["B0"][str(h)][s]) for s in slot]),
         "B1": clip([vec(consts["B1"][str(h)][s][lab[(k, h)][1]]) for k, s in zip(keys, slot)]),
         "B2": b2_proba(fit, h, X), "B3": b3_proba(models, fit, h, X)}
    return p


# ---------- metrics ----------

def metrics(p: np.ndarray, y: np.ndarray) -> dict:
    n = len(y)
    pred = argmax_idx(p)
    onehot = np.eye(4)[y]
    conf = p.max(axis=1)
    correct = pred == y
    bins = np.minimum((conf * 10).astype(int), 9)
    rel = []
    ece = 0.0
    for b in range(10):
        m = bins == b
        if m.any():
            acc_b, conf_b = float(correct[m].mean()), float(conf[m].mean())
            ece += m.sum() / n * abs(acc_b - conf_b)
            rel.append({"bin": b, "n": int(m.sum()), "accuracy": acc_b, "confidence": conf_b})
    return {"n": n, "log_loss": float(losses(p, y).mean()),
            "brier": float(((p - onehot) ** 2).sum(axis=1).mean()),
            "accuracy": float(correct.mean()),
            "confusion": {CLASSES[t]: {CLASSES[q]: int(((y == t) & (pred == q)).sum()) for q in range(4)}
                          for t in range(4)},
            "ece": float(ece), "reliability": rel}


def aurc(conf: np.ndarray, loss: np.ndarray) -> float:
    order = np.argsort(-conf, kind="stable")
    c, l = conf[order], loss[order]
    cum = np.cumsum(l) / np.arange(1, len(l) + 1)
    risk = np.empty_like(cum)
    i = 0
    while i < len(c):
        j = i
        while j + 1 < len(c) and c[j + 1] == c[i]:
            j += 1
        risk[i:j + 1] = cum[j]
        i = j + 1
    return float(risk.mean())


def coverage(pj, pstar, y) -> dict:
    conf_j, conf_s = pj.max(axis=1), pstar.max(axis=1)
    lj, ls = losses(pj, y), losses(pstar, y)
    ej, es = (argmax_idx(pj) != y).astype(float), (argmax_idx(pstar) != y).astype(float)
    levels = []
    for c in (100, 80, 60, 40, 20):
        row = {"coverage_pct": c}
        for name, conf in (("by_J_confidence", conf_j), ("by_B3star_confidence", conf_s)):
            cut = float(np.quantile(conf, 1 - c / 100, method="linear"))
            keep = conf >= cut
            row[name] = {"cut": cut, "n": int(keep.sum()), "realized_pct": 100 * float(keep.mean()),
                         "J_log_loss": float(lj[keep].mean()), "J_accuracy": float(1 - ej[keep].mean()),
                         "B3star_log_loss": float(ls[keep].mean()),
                         "B3star_accuracy": float(1 - es[keep].mean())}
        levels.append(row)
    rho = spearmanr(conf_j, ls, alternative="less")
    return {"levels": levels,
            "aurc": {"J_0_1": aurc(conf_j, ej), "J_log_loss": aurc(conf_j, lj),
                     "B3star_0_1": aurc(conf_s, es), "B3star_log_loss": aurc(conf_s, ls)},
            "b3star_loss_vs_J_confidence_spearman": {"rho": float(rho.statistic),
                                                     "p_one_sided_less": float(rho.pvalue)}}


def newey_west_t(x: np.ndarray, lag: int) -> float:
    n, m = len(x), x.mean()
    e = x - m
    s = (e @ e) / n
    for L in range(1, lag + 1):
        s += 2 * (1 - L / (lag + 1)) * (e[L:] @ e[:-L]) / n
    return float(m / math.sqrt(s / n))


def ac1(x: np.ndarray) -> float:
    e = x - x.mean()
    return float((e[1:] @ e[:-1]) / (e @ e))


def bootstrap_lb(means: np.ndarray, w: np.ndarray) -> dict:
    rng = np.random.default_rng(SEED)
    n, b = len(means), 5
    starts = rng.integers(0, n - b + 1, size=(10_000, n // b))
    idx = (starts[:, :, None] + np.arange(b)).reshape(10_000, -1)
    stats = (means[idx] * w[idx]).sum(axis=1) / w[idx].sum(axis=1)
    return {"lower_bound_95_one_sided": float(np.quantile(stats, 0.05, method="linear")),
            "iterations": 10_000, "block": b}


def frozen_pool_dll(obs, cf, lj_perm) -> float:
    ls_ = losses(cf["p_star"], obs["y"])
    pp = np.zeros_like(obs["lb3"])
    for prm in cf["params"]:
        te = cf["fold"] == prm["fold"]
        pp[te] = clip(pool_proba(prm["b3_plus_j"]["theta"], obs["lb3"][te], lj_perm[te], True))
    d = ls_ - losses(pp, obs["y"])
    return dll(obs["session"], d, obs["order"])[0]


def nulls(obs, cf, observed: float) -> dict:
    lj = obs["lj"]
    n = len(lj)
    sess, slot = obs["session"], obs["slot"]
    conf_s = cf["p_star"].max(axis=1)
    cuts = np.quantile(conf_s, [1 / 3, 2 / 3], method="linear")
    terc = np.where(conf_s <= cuts[0], 0, np.where(conf_s <= cuts[1], 1, 2))
    top = argmax_idx(cf["p_star"])
    strata = {}
    for i in range(n):
        strata.setdefault((slot[i], int(top[i]), int(terc[i])), []).append(i)
    rng = np.random.default_rng(SEED)
    cr = []
    for _ in range(1000):
        perm = np.arange(n)
        for members in strata.values():
            m = np.array(members)
            perm[m] = m[rng.permutation(len(m))]
        cr.append(frozen_pool_dll(obs, cf, lj[perm]))
    cr = np.array(cr)
    rng = np.random.default_rng(SEED)
    n1 = []
    by_slot = {s: np.where(slot == s)[0] for s in SLOTS}
    for _ in range(1000):
        perm = np.arange(n)
        for idx in by_slot.values():
            perm[idx] = idx[rng.permutation(len(idx))]
        n1.append(frozen_pool_dll(obs, cf, lj[perm]))
    n1 = np.array(n1)
    order = obs["order"]
    pos = {s: i for i, s in enumerate(order)}
    lookup = {(s, sl): i for i, (s, sl) in enumerate(zip(sess, slot))}
    n2 = []
    for k in range(1, 20):
        perm = np.array([lookup.get((order[(pos[s] + 5 * k) % len(order)], sl), -1)
                         for s, sl in zip(sess, slot)])
        ok = perm >= 0
        lj2 = lj.copy()
        lj2[ok] = lj[perm[ok]]
        n2.append({"shift_sessions": 5 * k, "dll": frozen_pool_dll(obs, cf, lj2),
                   "unmatched_obs_kept_unshifted": int((~ok).sum())})
    return {
        "conditional_randomization": {"tercile_cuts_not_frozen": cuts.tolist(), "strata": len(strata),
                                      "iterations": 1000, "p": float((cr >= observed).mean()),
                                      "null_mean": float(cr.mean())},
        "N1_within_slot_session_permutation": {"iterations": 1000, "p": float((n1 >= observed).mean()),
                                               "null_mean": float(n1.mean())},
        "N2_block_shift": {"shifts": n2,
                           "share_ge_observed": float(np.mean([s["dll"] >= observed for s in n2]))},
    }


def n_req(delta_dll: float, means: np.ndarray, rule: dict) -> dict:
    if not delta_dll > 0:
        return {"computed": False, "reason": "OOF dLL <= 0 (rule 4); delta undefined"}
    delta = 0.5 * delta_dll
    out = {}
    for name, sd in (("t_ddof1", means.std(ddof=1)), ("t_ddof0", means.std(ddof=0))):
        out[name] = {"sd": float(sd), "n_req": n_required(delta, float(sd), rule["power"], False)}
    zsd = means.std(ddof=1)
    out["normal_ddof1"] = {"sd": float(zsd), "n_req": math.ceil(
        ((norm.ppf(1 - rule["alpha"]) + norm.ppf(rule["power"])) * zsd / delta) ** 2)}
    verdicts = {k: (v["n_req"] is None or v["n_req"] > rule["abandon_if_n_req_gt"],
                    None if v["n_req"] is None else max(rule["min"], v["n_req"])) for k, v in out.items()}
    return {"computed": True, "delta": delta, "variants": out,
            "rule6_null": verdicts["t_ddof1"][0], "n_p_if_established": verdicts["t_ddof1"][1],
            "variants_disagree": len(set(verdicts.values())) > 1}


# ---------- assembly ----------

def build(store: Path) -> dict:
    config, _ = load_seal()
    a3 = load_a3()
    consts = _json("dfit_constants_step2.json", FROZEN["dfit_constants_step2.json"])
    fit = _json("b2_b3_step2.json", FROZEN["b2_b3_step2.json"])
    models = load_models(fit)
    elig, draws, feats = (dev._artifact(n) for n in
                          ("eligibility_step1.json", "draws_step2.json", "features_step2.json"))
    # fidelity: frozen B2/B3 reproduce their recorded D-fit in-sample log-loss
    dkeys = [f"{r['date']}|{r['slot']}" for r in consts["states"]["15"]]
    Xd = np.array([[feats["states"][k][f] for f in FIELDS] for k in dkeys])
    for h in (5, 15, 30):
        yd = np.array([CLASSES.index(r["label"]) for r in consts["states"][str(h)]])
        for name, p in (("b2", b2_proba(fit, h, Xd)), ("b3", b3_proba(models, fit, h, Xd))):
            if abs(losses(p, yd).mean() - fit[name][str(h)]["d_fit_in_sample_log_loss"]) > 1e-12:
                raise RuntimeError(f"{name} h{h} does not reproduce its D-fit log-loss")

    planned = dev.planned_states(draws)
    cache = dev._cache()
    started = dev._started()
    recs = {}
    for (tpl, key), p in zip(planned, started["planned"]):
        r = cache[p["key"]]
        if r["stage"] != "development" or r["state"] != key or r["template"] != tpl or not r["authoritative"]:
            raise RuntimeError(f"cache record mismatch for {tpl} {key}")
        recs[(tpl, key)] = r

    d = draws["draws"]
    dev_sessions = d["d1_dev"]["output"]
    erecs = {r["date"]: r for r in elig["sessions"]["d_eval"]}
    lab = labels_for(store, [erecs[s] for s in sorted(dev_sessions)], consts)

    def horizon_obs(h: int, sessions: list[str]) -> dict:
        tpl = f"h{h}"
        keys = [f"{s}|{sl}" for s in sorted(sessions) for sl in SLOTS]
        X = np.array([[feats["states"][k][f] for f in FIELDS] for k in keys])
        y = np.array([CLASSES.index(lab[(k, h)][0]) for k in keys])
        det = deterministic(keys, X, lab, h, consts, fit, models)
        valid = np.array([recs[(tpl, k)]["validity"]["valid"] for k in keys])
        pj = np.full((len(keys), 4), np.nan)
        for i, k in enumerate(keys):
            if valid[i]:
                pj[i] = clip(vec(recs[(tpl, k)]["validity"]["probabilities"]))
        m = valid
        return {"keys": [k for k, v in zip(keys, m) if v], "excluded": [k for k, v in zip(keys, m) if not v],
                "y": y[m], "pj": pj[m], "det": {n: p[m] for n, p in det.items()},
                "lb3": np.log(det["B3"][m]), "lj": np.log(pj[m]),
                "session": np.array([k[:10] for k in keys])[m], "slot": np.array([k[11:] for k in keys])[m],
                "order": sorted(sessions), "all_y": y, "all_det": det}

    out = {"protocol_id": "JEV-NMS-1", "stage": "development",
           "seals": {"f1_a2": "load_seal() passed", "a3": "load_a3() passed",
                     "a3_l3_baseline": a3["l3_baseline"]["value"], "a3_l5_threshold": a3["l5_halt"]["threshold"]},
           "frozen_inputs": {**FROZEN, **{f"b3_h{h}_step2.pkl": v for h, v in PICKLES.items()}}}
    horizons = {}
    for h, sessions in ((15, dev_sessions), (5, d["d2_dev_secondary"]["output"]),
                        (30, d["d2_dev_secondary"]["output"])):
        obs = horizon_obs(h, sessions)
        bl = blocks(sessions)
        block_of = {s: i for i, b in enumerate(bl) for s in b}
        cf = crossfit(obs, block_of)
        ls_, lp = losses(cf["p_star"], obs["y"]), losses(cf["p_pool"], obs["y"])
        val, means, w = dll(obs["session"], ls_ - lp, obs["order"])
        full = fit_pool(obs["lb3"], obs["lj"], obs["y"], True)
        full_star = fit_pool(obs["lb3"], obs["lj"], obs["y"], False)
        models_p = {**obs["det"], "J": obs["pj"], "B3*": cf["p_star"], "B3+J": cf["p_pool"]}
        hz = {
            "sessions": len(sessions), "observations_scheduled": len(sessions) * 10,
            "valid_observations": len(obs["y"]), "paired_excluded": obs["excluded"],
            "blocks": bl, "oof_dll": val,
            "per_session": [{"session": s, "dll": float(m), "weight": int(wt)}
                            for s, m, wt in zip(obs["order"], means, w)],
            "fold_params": cf["params"], "full_sample_b3_plus_j": full, "full_sample_b3_star": full_star,
            "b_hat_full": full["b"],
            "per_slot_dll": {s: float((ls_ - lp)[obs["slot"] == s].mean()) for s in SLOTS},
            "metrics": {n: metrics(p, obs["y"]) for n, p in models_p.items()},
            "J_minus_deterministic_log_loss": {
                n: float((losses(obs["det"][n], obs["y"]) - losses(obs["pj"], obs["y"])).mean())
                for n in ("B0", "B1", "B2", "B3")},
            "label_base_rates": {CLASSES[k]: float((obs["y"] == k).mean()) for k in range(4)},
        }
        if h != 15:
            alt_of = {s: i for i, b in enumerate(blocks(dev_sessions)) for s in b}
            cfa = crossfit(obs, alt_of)
            hz["alt_blocks_from_h15"] = {"oof_dll": dll(obs["session"], losses(cfa["p_star"], obs["y"])
                                                        - losses(cfa["p_pool"], obs["y"]), obs["order"])[0],
                                         "fold_sizes": [int((cfa["fold"] == k).sum()) for k in range(K)]}
        else:
            hz["coverage"] = coverage(obs["pj"], cf["p_star"], obs["y"])
            hz["descriptive_inference"] = {"bootstrap": bootstrap_lb(means, w),
                                           "newey_west_t_lag5": newey_west_t(means, 5), "ac1": ac1(means),
                                           **nulls(obs, cf, val)}
            hz["n_req"] = n_req(val, means, config["n_p_rule"])
        horizons[str(h)] = hz
    out["horizons"] = horizons

    p15 = horizons["15"]
    rule4 = p15["oof_dll"] <= 0
    rule5 = p15["b_hat_full"] <= 0
    rule6 = p15["n_req"].get("rule6_null") if p15["n_req"]["computed"] else None
    out["gates"] = {"rule4_oof_dll_le_0": rule4, "rule5_b_hat_le_0": rule5, "rule6_n_req_gt_250": rule6,
                    "rule6_needs_ruling": bool(p15["n_req"].get("variants_disagree")),
                    "invalid_rate_dev": 1 - sum(h["valid_observations"] for h in horizons.values()) / 1600}
    out["result"] = ("NULL" if (rule4 or rule5 or rule6) else
                     "NEEDS_RULING" if out["gates"]["rule6_needs_ruling"] else
                     "DEVELOPMENT_GATES_PASSED_F2_NOT_SET")

    # §18 deterministic models on H-exposed (EXPOSED)
    hx = [r for r in elig["sessions"]["h_exposed"] if r["eligible"]]
    hlab = labels_for(store, hx, consts)
    hkeys, hX = [], []
    for r in hx:
        bars = load_window_bars(store, r["date"], r["file_sha256"])
        for s in SLOTS:
            t = slot_index(s)
            f = rounded(raw_features(bars[:t], t, r["prev_1529_close"]))
            hkeys.append(f"{r['date']}|{s}")
            hX.append([f[x] for x in FIELDS])
    hX = np.array(hX)
    out["h_exposed_EXPOSED"] = {"sessions": len(hx), "states": len(hkeys), "label": "EXPOSED / NON-CONFIRMATORY",
                                "horizons": {}}
    for h in (5, 15, 30):
        y = np.array([CLASSES.index(hlab[(k, h)][0]) for k in hkeys])
        det = deterministic(hkeys, hX, hlab, h, consts, fit, models)
        out["h_exposed_EXPOSED"]["horizons"][str(h)] = {n: {k: v for k, v in metrics(p, y).items()
                                                            if k in ("n", "log_loss", "brier", "accuracy", "ece")}
                                                        for n, p in det.items()}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, required=True)
    args = ap.parse_args()
    target = OUT / ARTIFACT_NAME
    if target.exists():
        raise SystemExit("development artifact exists; the analysis is never re-run")
    out = build(args.store)
    out["cache_sha256"] = hashlib.sha256((OUT / "cache.jsonl").read_bytes()).hexdigest()
    out["built_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(target, "x", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(out, indent=1, sort_keys=True))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    p = out["horizons"]["15"]
    _append(OUT / "ledger.jsonl", {"event": "development_completed", "artifact": ARTIFACT_NAME, "sha256": digest,
                                   "result": out["result"], "oof_dll_h15": p["oof_dll"],
                                   "b_hat": p["b_hat_full"], "gates": out["gates"], "at": out["built_at"]})
    print(json.dumps({"result": out["result"], "gates": out["gates"], "oof_dll_h15": p["oof_dll"],
                      "b_hat": p["b_hat_full"], "n_req": p["n_req"]}, indent=1))
    print(f"{target}  sha256={digest}")


if __name__ == "__main__":
    main()
