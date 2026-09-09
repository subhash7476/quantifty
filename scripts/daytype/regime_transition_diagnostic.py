"""Empirical transition matrix of the DayType labels — does a day-type persist?

Answers recommendation #6 of REGIME_DETECTION_SPEC_AUDIT_2026-09-09.md at
near-zero cost: a Markov-switching / transition-matrix layer over day-types is
only worth building if day-types actually persist from one session to the next.
This reads the labels already on disk and measures that directly.

**Predictions, pinned before the run (repo convention: falsifiable first):**

  KILL Layer 2      max diagonal excess (p_ii - pi_i) < +0.03 AND Cramer's V < 0.05
  MOTIVATE Layer 2  max diagonal excess > +0.10 on any state
  INCONCLUSIVE      anything between — reported as such, not resolved by narrative

**Scope of the answer.** The label at date t comes from a KMeans fit that saw the
whole 2012-2025 panel (audit Finding C). That contaminates the *label definition*,
not the *sequence order*, so the transition structure below is a valid property of
the realized label sequence. It is NOT a forward-usable estimate of P for a live
model, which never has the global fit.

**Pair rule.** Consecutive rows are not always consecutive sessions (the file has
gaps, the largest 32 calendar days). A pair is counted only when the two dates are
<= MAX_PAIR_GAP_DAYS apart, which keeps Fri->Mon and drops outages. The dropped
count is reported.

Usage: python scripts/daytype/regime_transition_diagnostic.py
Output: docs/reports/index_research/REGIME_TRANSITION_DIAGNOSTIC.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

ROOT = Path(__file__).resolve().parents[2]
LABELS = ROOT / "data" / "features" / "day_type" / "cluster_labels.csv"
OUT = ROOT / "docs" / "reports" / "index_research" / "REGIME_TRANSITION_DIAGNOSTIC.md"

# id -> name binding. The label file's own `cluster_label` column is entirely
# empty, so this mapping (train_daytype_classifier.py:99-103) is the only source
# of it — and per audit Finding B it is a hardcoded post-hoc assignment, not a
# reproducible property of the fit.
CLUSTER_NAMES = {0: "Choppy", 1: "BullTrend", 2: "BearTrend"}

MAX_PAIR_GAP_DAYS = 5
KILL_EXCESS, KILL_V = 0.03, 0.05
MOTIVATE_EXCESS = 0.10


def load_pairs() -> tuple[pd.DataFrame, int, int]:
    df = pd.read_csv(LABELS, parse_dates=["date"]).sort_values("date")
    df = df.dropna(subset=["cluster_id"])
    df["cluster_id"] = df["cluster_id"].astype(int)
    nxt = df.shift(-1)
    gap = (nxt["date"] - df["date"]).dt.days
    pairs = pd.DataFrame({
        "date": df["date"], "frm": df["cluster_id"],
        "to": nxt["cluster_id"], "gap": gap,
    }).dropna()
    pairs["to"] = pairs["to"].astype(int)
    kept = pairs[pairs["gap"] <= MAX_PAIR_GAP_DAYS].reset_index(drop=True)
    return kept, len(pairs), len(pairs) - len(kept)


def transition(pairs: pd.DataFrame, k: int = 3) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    counts = np.zeros((k, k), dtype=int)
    for f, t in zip(pairs["frm"], pairs["to"]):
        counts[f, t] += 1
    P = counts / counts.sum(axis=1, keepdims=True)
    marg = counts.sum(axis=0) / counts.sum()
    return counts, P, marg


def cramers_v(counts: np.ndarray) -> tuple[float, float, float, int]:
    chi2, p, dof, _ = chi2_contingency(counts)
    n = counts.sum()
    v = float(np.sqrt(chi2 / (n * (min(counts.shape) - 1))))
    return float(chi2), float(p), v, int(dof)


def fmt_matrix(counts: np.ndarray, P: np.ndarray, marg: np.ndarray) -> list[str]:
    k = len(marg)
    head = "| from \\ to | " + " | ".join(CLUSTER_NAMES[j] for j in range(k)) + " | row n |"
    sep = "|---|" + "---:|" * (k + 1)
    lines = [head, sep]
    for i in range(k):
        cells = " | ".join(f"**{P[i, j]:.3f}** ({counts[i, j]})" if i == j
                           else f"{P[i, j]:.3f} ({counts[i, j]})" for j in range(k))
        lines.append(f"| {CLUSTER_NAMES[i]} | {cells} | {counts[i].sum()} |")
    lines.append("| *marginal (independence row)* | "
                 + " | ".join(f"*{m:.3f}*" for m in marg) + " | |")
    return lines


def residual_block(counts: np.ndarray) -> list[str]:
    """Post-hoc: where does the dependence sit? Standardized Pearson residuals
    (observed - expected)/sqrt(expected), plus the diagonal's share of chi-square.
    This is NOT part of the pinned rule — it is read after the verdict, to say what
    kind of dependence the chi-square found."""
    _, _, _, expected = chi2_contingency(counts)
    resid = (counts - expected) / np.sqrt(expected)
    contrib = (counts - expected) ** 2 / expected
    diag_share = float(np.trace(contrib) / contrib.sum())
    k = counts.shape[0]
    lines = ["**Post-hoc — standardized residuals** (observed vs independence; "
             "positive = happens more often than chance):", "",
             "| from \\ to | " + " | ".join(CLUSTER_NAMES[j] for j in range(k)) + " |",
             "|---|" + "---:|" * k]
    for i in range(k):
        lines.append(f"| {CLUSTER_NAMES[i]} | "
                     + " | ".join(f"{resid[i, j]:+.2f}" for j in range(k)) + " |")
    lines += ["", f"Share of chi-square coming from the **diagonal** (persistence) cells: "
              f"**{diag_share:.1%}** — the rest is off-diagonal (rotation between states).", ""]
    return lines


def lag_k_pairs(df: pd.DataFrame, lag: int) -> pd.DataFrame:
    nxt = df.shift(-lag)
    gap = (nxt["date"] - df["date"]).dt.days
    out = pd.DataFrame({"date": df["date"], "frm": df["cluster_id"],
                        "to": nxt["cluster_id"], "gap": gap}).dropna()
    out["to"] = out["to"].astype(int)
    return out[out["gap"] <= MAX_PAIR_GAP_DAYS * lag].reset_index(drop=True)


def section(title: str, pairs: pd.DataFrame) -> tuple[list[str], float, float]:
    counts, P, marg = transition(pairs)
    chi2, p, v, dof = cramers_v(counts)
    excess = np.diag(P) - marg
    dur = 1.0 / (1.0 - np.diag(P))
    dur_ind = 1.0 / (1.0 - marg)

    lines = [f"### {title}", "",
             f"n pairs = {len(pairs)}, span {pairs['date'].min():%Y-%m-%d} to "
             f"{pairs['date'].max():%Y-%m-%d}", ""]
    lines += fmt_matrix(counts, P, marg)
    lines += ["", "| state | p_ii | marginal pi_i | **diagonal excess** | "
              "E[duration] = 1/(1-p_ii) | baseline 1/(1-pi_i) |", "|---|---:|---:|---:|---:|---:|"]
    for i in range(3):
        lines.append(f"| {CLUSTER_NAMES[i]} | {P[i, i]:.3f} | {marg[i]:.3f} | "
                     f"**{excess[i]:+.3f}** | {dur[i]:.2f} | {dur_ind[i]:.2f} |")
    lines += ["", f"chi-square = {chi2:.2f} (dof {dof}), p = {p:.3g}, "
              f"**Cramer's V = {v:.4f}**", ""]
    return lines, float(np.max(excess)), v


def main() -> int:
    pairs, total, dropped = load_pairs()
    lines = [
        "# DayType Regime — Empirical Transition Matrix Diagnostic", "",
        "Generated by `scripts/daytype/regime_transition_diagnostic.py`. "
        "Every number below is script-produced.", "",
        "**What this answers.** Recommendation #6 of "
        "`REGIME_DETECTION_SPEC_AUDIT_2026-09-09.md`: a Markov-switching layer over "
        "day-types is worth building only if day-types persist session to session. "
        "Thresholds were pinned in the script docstring before the run — "
        f"KILL if max diagonal excess < +{KILL_EXCESS:.2f} and Cramer's V < {KILL_V:.2f}; "
        f"MOTIVATE if max diagonal excess > +{MOTIVATE_EXCESS:.2f}; otherwise INCONCLUSIVE.", "",
        "**What it cannot answer.** The label at date *t* comes from a KMeans fit that "
        "saw the whole 2012-2025 panel (audit Finding C). That contaminates the label "
        "*definition*, not the sequence *order*, so what follows is a valid property of "
        "the realized label sequence — but it is not a forward-usable estimate of `P` for "
        "a live model, which never has the global fit. The id->name binding is "
        "`CLUSTER_NAMES` from `train_daytype_classifier.py:99`, a hardcoded post-hoc "
        "assignment (audit Finding B); the label file's own `cluster_label` column is empty.", "",
        f"**Pair rule.** {total} consecutive-row pairs; a pair counts only when the two "
        f"dates are <= {MAX_PAIR_GAP_DAYS} calendar days apart (keeps Fri->Mon, drops "
        f"outages). **{dropped} pair(s) dropped.**", "",
        "---", "", "## 1. Full sample", "",
    ]
    full_lines, max_excess, v_full = section("2012-2025", pairs)
    counts_full, _, _ = transition(pairs)
    lines += full_lines + residual_block(counts_full)

    df2 = pd.read_csv(LABELS, parse_dates=["date"]).sort_values("date").dropna(
        subset=["cluster_id"])
    df2["cluster_id"] = df2["cluster_id"].astype(int)
    p2 = lag_k_pairs(df2, 2)
    c2, P2, m2 = transition(p2)
    _, _, v2, _ = cramers_v(c2)
    lines += [f"**Lag-2 check** (t -> t+2, n = {len(p2)}): max diagonal excess "
              f"**{float(np.max(np.diag(P2) - m2)):+.3f}**, Cramer's V **{v2:.4f}**.", ""]

    lines += ["---", "", "## 2. Subperiod stability", "",
              "Not a second hypothesis — a stability check on `P`. A transition matrix "
              "that moves between halves is worse for a persistence model than a weak "
              "one that holds still.", ""]
    early = pairs[pairs["date"].dt.year <= 2018]
    late = pairs[pairs["date"].dt.year >= 2019]
    e_lines, e_excess, e_v = section("2012-2018", early)
    l_lines, l_excess, l_v = section("2019-2025", late)
    lines += e_lines + l_lines

    _, P_e, _ = transition(early)
    _, P_l, _ = transition(late)
    drift = float(np.max(np.abs(P_e - P_l)))
    lines += [f"Largest absolute change in any `P` entry between halves: **{drift:.3f}**", ""]

    if max_excess < KILL_EXCESS and v_full < KILL_V:
        verdict = ("**KILL** — day-types do not persist. Max diagonal excess "
                   f"{max_excess:+.3f} < +{KILL_EXCESS:.2f} and Cramer's V {v_full:.4f} "
                   f"< {KILL_V:.2f}. A transition matrix over these labels carries "
                   "essentially no information beyond the marginal frequencies, so the "
                   "spec's Layer-2 persistence machinery has nothing to model here.")
    elif max_excess > MOTIVATE_EXCESS:
        verdict = ("**MOTIVATE** — day-types persist materially. Max diagonal excess "
                   f"{max_excess:+.3f} > +{MOTIVATE_EXCESS:.2f}. A persistence layer has "
                   "real structure to capture; subperiod drift above decides whether `P` "
                   "is stable enough to estimate.")
    else:
        verdict = ("**INCONCLUSIVE** — max diagonal excess "
                   f"{max_excess:+.3f} and Cramer's V {v_full:.4f} fall between the pinned "
                   "thresholds. Reported as such; not resolved by narrative.")

    lines += ["---", "", "## 3. Verdict", "", verdict, ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
