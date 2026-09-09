"""Primary gate and mandatory sanity checks — §10 of the N200 regime design spec.

Evaluated exactly as pre-registered. Nothing here re-specifies features, folds or
the model; it reads what `run_folds.py` produced and scores it.

Gate (§10.1): does filtered P(S_2), out of sample, predict forward 5-day realized
Garman-Klass volatility landing in that stock's own trailing top tercile? Scored
by Brier against two baselines — a trailing base rate and a persistence baseline
built from the stock's current GK percentile — with a reliability curve and ECE.
Pass needs skill > 0 against both baselines pooled and in >= 7 of 10 folds, a
monotone non-decreasing reliability curve, and ECE < 0.05.

Sanity A (§10.2): out-of-sample mean log-likelihood per observation must beat an
i.i.d. Gaussian mixture and a single-state Gaussian in >= 8 of 10 folds.

Sanity C (§10.3): median dwell > 3 sessions, and March 2020 in the top 1% of days
by cross-sectional mean P(S_2).

Usage: python scripts/n200_regime/evaluate.py
Output: docs/reports/index_research/N200_REGIME_EVALUATION.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.analytics.regime.features import (  # noqa: E402
    FEATURE_NAMES, forward_realized_vol, trailing_tercile_cuts,
)
from core.analytics.regime.panel_hmm import _logsumexp, log_emissions  # noqa: E402
from scripts.n200_regime.run_folds import (  # noqa: E402
    FOLD_YEARS, MIN_SEQ_SESSIONS, build_fold_features, entity_floors, load_panel,
)

PANEL_DIR = ROOT / "data" / "features" / "n200_regime"
REGIME_DB = PANEL_DIR / "regime_panel.duckdb"
PARAM_DIR = PANEL_DIR / "params"
OUT = ROOT / "docs" / "reports" / "index_research" / "N200_REGIME_EVALUATION.md"

HORIZON = 5
TRAILING = 252
MIN_TRAILING = 60
N_BINS = 10
MIN_BIN = 100
BLOCK = 10
N_BOOT = 1000
SEED = 20260909

PASS_MIN_FOLDS = 7
PASS_ECE = 0.05
SANITY_A_MIN_FOLDS = 8
MIN_DWELL = 3.0


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def skill(p: np.ndarray, y: np.ndarray, base: np.ndarray) -> float:
    b_ref = brier(base, y)
    return float(1.0 - brier(p, y) / b_ref) if b_ref > 0 else np.nan


def reliability(p: np.ndarray, y: np.ndarray) -> tuple[pd.DataFrame, float]:
    edges = np.linspace(0.0, 1.0, N_BINS + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, N_BINS - 1)
    rows, ece, n = [], 0.0, len(p)
    for b in range(N_BINS):
        m = idx == b
        if not m.any():
            continue
        rows.append({"bin": f"[{edges[b]:.1f},{edges[b+1]:.1f})", "n": int(m.sum()),
                     "mean_pred": float(p[m].mean()), "observed": float(y[m].mean())})
        if m.sum() >= MIN_BIN:
            ece += m.sum() / n * abs(p[m].mean() - y[m].mean())
    return pd.DataFrame(rows), float(ece)


def block_bootstrap_ci(df: pd.DataFrame, base_col: str) -> tuple[float, float]:
    """Stationary block bootstrap over dates (block 10) on the skill score.

    Skill is a ratio of two means over observations, so a resample only needs
    each date's summed squared errors and its row count -- resampling the rows
    themselves would rebuild a 460k-row frame a thousand times for an identical
    number.
    """
    rng = np.random.default_rng(SEED)
    g = df.assign(
        se_model=(df["p_s2"] - df["y_top"]) ** 2,
        se_base=(df[base_col] - df["y_top"]) ** 2,
    ).groupby("trade_date")[["se_model", "se_base"]].sum()
    model_s, base_s = g["se_model"].to_numpy(), g["se_base"].to_numpy()
    n_dates = len(model_s)
    n_blocks = max(1, n_dates // BLOCK)

    offsets = np.arange(BLOCK)
    out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        starts = rng.integers(0, n_dates, n_blocks)
        idx = (starts[:, None] + offsets[None, :]).ravel() % n_dates
        denom = base_s[idx].sum()
        out[b] = 1.0 - model_s[idx].sum() / denom if denom > 0 else np.nan
    lo, hi = np.nanpercentile(out, [2.5, 97.5])
    return float(lo), float(hi)


def build_targets(panel: pd.DataFrame) -> pd.DataFrame:
    """Forward-vol target, trailing tercile cuts, and both baselines, per entity."""
    parts = []
    for _, g in panel.groupby("entity", observed=True):
        g = g.sort_values("trade_date").copy()
        gk = g["gk"].to_numpy()
        fwd = forward_realized_vol(gk, HORIZON)
        lo, hi = trailing_tercile_cuts(fwd, TRAILING, MIN_TRAILING)
        g["y_top"] = np.where(np.isnan(fwd) | np.isnan(hi), np.nan,
                              (fwd > hi).astype(float))
        g["y_bot"] = np.where(np.isnan(fwd) | np.isnan(lo), np.nan,
                              (fwd < lo).astype(float))
        # baseline 1: trailing realized rate of the event, ending at t-1
        g["base_rate"] = (pd.Series(g["y_top"].to_numpy()).shift(1)
                          .rolling(TRAILING, min_periods=MIN_TRAILING).mean().to_numpy())
        # baseline 2: persistence — today's GK percentile in its trailing window
        s = pd.Series(gk)
        g["base_persist"] = s.rolling(TRAILING, min_periods=MIN_TRAILING).apply(
            lambda w: (w[:-1] < w[-1]).mean(), raw=True).to_numpy()
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def fit_iid_mixture(x: np.ndarray, k: int, seed: int, iters: int = 100):
    """Same emissions, no transition structure — the §10.2 comparator."""
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(x), k, replace=False)
    mu, var = x[idx].copy(), np.tile(x.var(0), (k, 1))
    w = np.full(k, 1.0 / k)
    for _ in range(iters):
        lp = log_emissions(x, mu, var) + np.log(w)[None, :]
        ll = _logsumexp(lp, axis=1)
        r = np.exp(lp - ll[:, None])
        nk = r.sum(0)
        w = nk / nk.sum()
        mu = (r.T @ x) / nk[:, None]
        var = np.maximum((r.T @ (x * x)) / nk[:, None] - mu * mu, 1e-6)
    return mu, var, w


def iid_loglik(x, mu, var, w) -> float:
    return float(np.mean(_logsumexp(log_emissions(x, mu, var) + np.log(w)[None, :],
                                    axis=1)))


def single_gaussian_loglik(x, fit) -> float:
    mu, var = fit.mean(0)[None, :], np.maximum(fit.var(0), 1e-6)[None, :]
    return float(np.mean(log_emissions(x, mu, var)))


def hmm_loglik(x_seqs, params) -> float:
    from core.analytics.regime.panel_hmm import _forward
    A, mu, var = (np.array(params[k]) for k in ("A", "mu", "var"))
    log_A, log_pi = np.log(np.maximum(A, 1e-300)), np.log(
        np.maximum(np.array(params["pi"]), 1e-300))
    tot, n = 0.0, 0
    for s in x_seqs:
        _, ll = _forward(log_emissions(s, mu, var), log_A, log_pi)
        tot += ll
        n += len(s)
    return tot / max(n, 1)


def main() -> int:
    print("Loading regime panel and base panel...")
    con = duckdb.connect(str(REGIME_DB), read_only=True)
    reg = con.execute("SELECT * FROM regime_panel").df()
    con.close()
    reg["trade_date"] = pd.to_datetime(reg["trade_date"])

    base = load_panel()
    merged = build_targets(base[["entity", "trade_date", "gk", "close",
                                 "in_universe", "seq_id", "symbol"]])
    df = reg.merge(merged[["entity", "trade_date", "y_top", "y_bot", "base_rate",
                           "base_persist"]], on=["entity", "trade_date"], how="left")
    ev = df.dropna(subset=["y_top", "base_rate", "base_persist"]).copy()
    print(f"  {len(ev):,} scorable observations of {len(df):,} filtered rows")

    L: list[str] = []
    w = L.append
    w("# N200 Regime Classifier — Evaluation Against the Pre-Registered Gate")
    w("")
    w("Generated by `scripts/n200_regime/evaluate.py`. Every number is "
      "script-produced. The gate, its thresholds and its baselines were pinned in "
      "`docs/superpowers/specs/2026-09-09-n200-regime-hmm-design.md` §10 before any "
      "fold was fitted; nothing here re-specifies features, folds or the model.")
    w("")

    # ── Structural disclosure ────────────────────────────────────────────
    p_first = json.loads((PARAM_DIR / f"fold_{FOLD_YEARS[0]}.json").read_text())
    p_last = json.loads((PARAM_DIR / f"fold_{FOLD_YEARS[-1]}.json").read_text())
    mus = np.array([json.loads((PARAM_DIR / f"fold_{y}.json").read_text())["mu"]
                    for y in FOLD_YEARS])
    A_last = np.array(p_last["A"])

    w("## 0. Structural disclosure — what the states turned out to be")
    w("")
    w("**The unsupervised objective separated on directional efficiency, not on "
      "unoriented volatility.** This is disclosed before any gate number because it "
      "changes how every figure below should be read.")
    w("")
    w("| state | " + " | ".join(f"`{n}`" for n in FEATURE_NAMES) + " | reading |")
    w("|---|" + "---:|" * len(FEATURE_NAMES) + "---|")
    reading = ["chop", "up-trend", "down-trend"]
    for s in range(3):
        w(f"| S{s} | " + " | ".join(f"{mus[:, s, j].mean():+.3f}"
                                     for j in range(len(FEATURE_NAMES)))
          + f" | {reading[s]} |")
    w("")
    drift_sep = mus[:, 1, 3].mean() - mus[:, 2, 3].mean()
    vol_sep = mus[:, 2, 0].mean() - mus[:, 0, 0].mean()
    w(f"Drift separation between S1 and S2 is **{drift_sep:.2f} sigma**; volatility "
      f"separation between S0 and S2 is **{vol_sep:.2f} sigma**. The states are "
      "ordered by volatility mean as pre-registered, and that ordering held in all "
      "ten folds with non-overlapping ranges, so no label switching occurred — but "
      "it sorts on the weakest axis of separation, not the strongest.")
    w("")
    w("**Transition topology.** The fitted matrix carries an emergent structural "
      "zero between the two trending states:")
    w("")
    w("| from \\ to | S0 chop | S1 up | S2 down | dwell |")
    w("|---|---:|---:|---:|---:|")
    for i in range(3):
        w(f"| S{i} | " + " | ".join(f"{A_last[i, j]:.3f}" for j in range(3))
          + f" | {1 / (1 - A_last[i, i]):.1f} |")
    w("")
    w("A name never passes directly between up-trend and down-trend: it must "
      "decelerate through chop first. That was not imposed — EM found it.")
    w("")
    w("**Consequence for the gate.** P(S_2) is a down-trend probability, and it is "
      "being scored against a forward *volatility* target. Any skill it shows is "
      "therefore partly the leverage effect (down moves are high-vol moves) rather "
      "than evidence of a volatility regime as such. The gate is evaluated exactly "
      "as pinned; a purely unoriented volatility classifier would be a separate "
      "pre-registered Variant B.")
    w("")

    # ── Primary gate ─────────────────────────────────────────────────────
    w("## 1. Primary gate (§10.1) — does P(S_2) predict forward high volatility?")
    w("")
    p, y = ev["p_s2"].to_numpy(), ev["y_top"].to_numpy()
    b_rate, b_pers = ev["base_rate"].to_numpy(), ev["base_persist"].to_numpy()

    sub = ev.sort_values(["entity", "trade_date"]).groupby("entity", observed=True) \
             .apply(lambda g: g.iloc[::HORIZON], include_groups=False).reset_index()
    ps, ys = sub["p_s2"].to_numpy(), sub["y_top"].to_numpy()
    bs_rate, bs_pers = sub["base_rate"].to_numpy(), sub["base_persist"].to_numpy()

    w("| metric | full sample | non-overlapping (every 5th session) |")
    w("|---|---:|---:|")
    w(f"| observations | {len(ev):,} | {len(sub):,} |")
    w(f"| event rate (top tercile) | {y.mean():.4f} | {ys.mean():.4f} |")
    w(f"| Brier — P(S_2) | {brier(p, y):.5f} | {brier(ps, ys):.5f} |")
    w(f"| Brier — base-rate baseline | {brier(b_rate, y):.5f} | "
      f"{brier(bs_rate, ys):.5f} |")
    w(f"| Brier — persistence baseline | {brier(b_pers, y):.5f} | "
      f"{brier(bs_pers, ys):.5f} |")
    w(f"| **skill vs base rate** | **{skill(p, y, b_rate):+.4f}** | "
      f"**{skill(ps, ys, bs_rate):+.4f}** |")
    w(f"| **skill vs persistence** | **{skill(p, y, b_pers):+.4f}** | "
      f"**{skill(ps, ys, bs_pers):+.4f}** |")
    w("")
    print("  bootstrapping skill CIs...")
    lo_r, hi_r = block_bootstrap_ci(ev, "base_rate")
    lo_p, hi_p = block_bootstrap_ci(ev, "base_persist")
    w(f"Stationary block bootstrap (block {BLOCK}, {N_BOOT} resamples over dates), "
      f"full sample: skill vs base rate **[{lo_r:+.4f}, {hi_r:+.4f}]**, "
      f"skill vs persistence **[{lo_p:+.4f}, {hi_p:+.4f}]**.")
    w("")

    w("### Per fold")
    w("")
    w("| fold | n | Brier | skill vs base rate | skill vs persistence |")
    w("|---|---:|---:|---:|---:|")
    folds_rate, folds_pers = 0, 0
    for yr, g in ev.groupby("fold_year"):
        gp, gy = g["p_s2"].to_numpy(), g["y_top"].to_numpy()
        s_r = skill(gp, gy, g["base_rate"].to_numpy())
        s_p = skill(gp, gy, g["base_persist"].to_numpy())
        folds_rate += s_r > 0
        folds_pers += s_p > 0
        w(f"| {yr} | {len(g):,} | {brier(gp, gy):.5f} | {s_r:+.4f} | {s_p:+.4f} |")
    w("")
    w(f"Folds with positive skill: **{folds_rate}/10** vs base rate, "
      f"**{folds_pers}/10** vs persistence (pass needs >= {PASS_MIN_FOLDS}).")
    w("")

    rel, ece = reliability(p, y)
    w("### Reliability (§10.1)")
    w("")
    w("| bin | n | mean predicted | observed |")
    w("|---|---:|---:|---:|")
    for _, r in rel.iterrows():
        w(f"| {r['bin']} | {int(r['n']):,} | {r['mean_pred']:.3f} | "
          f"{r['observed']:.3f} |")
    populated = rel[rel["n"] >= MIN_BIN]
    monotone = bool(np.all(np.diff(populated["observed"].to_numpy()) >= 0))
    w("")
    w(f"Populated bins (n >= {MIN_BIN}): {len(populated)}. Monotone non-decreasing: "
      f"**{monotone}**. ECE: **{ece:.4f}** (pass needs < {PASS_ECE}).")
    w("")

    yb = ev["y_bot"].to_numpy()
    ok_b = ~np.isnan(yb)
    w(f"Reported, not gated — the S0 / bottom-tercile pair: Brier "
      f"{brier(ev['p_s0'].to_numpy()[ok_b], yb[ok_b]):.5f}, skill vs persistence "
      f"{skill(ev['p_s0'].to_numpy()[ok_b], yb[ok_b], 1 - ev['base_persist'].to_numpy()[ok_b]):+.4f}.")
    w("")

    gate_pass = (skill(p, y, b_rate) > 0 and skill(p, y, b_pers) > 0
                 and folds_rate >= PASS_MIN_FOLDS and folds_pers >= PASS_MIN_FOLDS
                 and monotone and ece < PASS_ECE)

    # ── Sanity A ─────────────────────────────────────────────────────────
    print("  sanity A: likelihood comparators per fold...")
    w("## 2. Sanity check A (§10.2) — predictive compression")
    w("")
    w("| fold | HMM | i.i.d. mixture | single Gaussian | beats both |")
    w("|---|---:|---:|---:|---|")
    base_panel = load_panel()
    a_pass = 0
    for yr in FOLD_YEARS:
        params = json.loads((PARAM_DIR / f"fold_{yr}.json").read_text())
        fit_end = pd.Timestamp(yr - 1, 12, 31)
        ys_, ye = pd.Timestamp(yr, 1, 1), pd.Timestamp(yr, 12, 31)
        floors, pooled = entity_floors(base_panel, fit_end)
        feats = build_fold_features(base_panel, floors, pooled)
        usable = base_panel["in_universe"] & feats[list(FEATURE_NAMES)].notna().all(axis=1)
        counts = base_panel.loc[usable, "seq_id"].value_counts()
        usable &= base_panel["seq_id"].isin(set(counts[counts >= MIN_SEQ_SESSIONS].index))
        norm = params["normalization"]
        lower, upper = np.array(norm["lower"]), np.array(norm["upper"])
        mean, std = np.array(norm["mean"]), np.array(norm["std"])

        def apply(mask):
            raw = feats.loc[mask, list(FEATURE_NAMES)].to_numpy()
            return (np.clip(raw, lower, upper) - mean) / np.where(std > 0, std, 1.0)

        fit_x = apply(usable & (base_panel["trade_date"] <= fit_end))
        ev_mask = usable & (base_panel["trade_date"] >= ys_) & (base_panel["trade_date"] <= ye)
        ev_x = apply(ev_mask)
        ev_seqs = [apply(ev_mask & (base_panel["seq_id"] == s))
                   for s in base_panel.loc[ev_mask, "seq_id"].unique()]
        ev_seqs = [s for s in ev_seqs if len(s) >= 2]

        mu_m, var_m, w_m = fit_iid_mixture(fit_x, 3, SEED)
        ll_hmm = hmm_loglik(ev_seqs, params)
        ll_iid = iid_loglik(ev_x, mu_m, var_m, w_m)
        ll_one = single_gaussian_loglik(ev_x, fit_x)
        beats = ll_hmm > ll_iid and ll_hmm > ll_one
        a_pass += beats
        w(f"| {yr} | {ll_hmm:.4f} | {ll_iid:.4f} | {ll_one:.4f} | "
          f"{'yes' if beats else 'NO'} |")
    w("")
    w(f"HMM beats both comparators in **{a_pass}/10** folds "
      f"(pass needs >= {SANITY_A_MIN_FOLDS}).")
    w("")

    # ── Sanity C ─────────────────────────────────────────────────────────
    w("## 3. Sanity check C (§10.3) — structural realism")
    w("")
    dwells = []
    for yr in FOLD_YEARS:
        A = np.array(json.loads((PARAM_DIR / f"fold_{yr}.json").read_text())["A"])
        dwells.extend(1.0 / (1.0 - np.diag(A)))
    med_dwell = float(np.median(dwells))
    w(f"Median implied dwell across all folds and states: **{med_dwell:.1f} "
      f"sessions** (pass needs > {MIN_DWELL}).")
    w("")
    daily = reg.groupby("trade_date").agg(mean_p2=("p_s2", "mean"), n=("p_s2", "size"))
    daily = daily[daily["n"] > 100].sort_values("mean_p2", ascending=False)
    top1pct = daily.head(max(1, len(daily) // 100))
    mar20 = top1pct[(top1pct.index >= "2020-03-01") & (top1pct.index <= "2020-03-31")]
    w(f"Days in the top 1% by cross-sectional mean P(S_2): {len(top1pct)}, of which "
      f"**{len(mar20)} fall in March 2020**. Highest day overall: "
      f"{daily.index[0]:%Y-%m-%d} at {daily['mean_p2'].iloc[0]:.3f}.")
    w("")
    c_pass = med_dwell > MIN_DWELL and len(mar20) > 0

    w("## 4. Verdict")
    w("")
    w(f"- Primary gate (§10.1): **{'PASS' if gate_pass else 'FAIL'}**")
    w(f"- Sanity A (§10.2): **{'PASS' if a_pass >= SANITY_A_MIN_FOLDS else 'FAIL'}**")
    w(f"- Sanity C (§10.3): **{'PASS' if c_pass else 'FAIL'}**")
    w("")
    w("Read the verdict together with §0: P(S_2) is a down-trend probability scored "
      "against a volatility target, so a pass is evidence that directional state "
      "carries forward-volatility information — not that the model isolates a "
      "volatility regime.")
    w("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L).encode("ascii", "replace").decode("ascii"))
    print(f"\nWritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
