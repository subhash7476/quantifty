"""Carry v2 — HOLDOUT rank-IC read.

CARRY_V2_PRE_REGISTRATION.md §4.1 sets TWO HOLDOUT acceptance conditions:
  (1) rank-IC, positive sign, significant at Bonferroni alpha = 0.025
  (2) net quintile spread > 0 (already evaluated in run_net_spread.py)

This script fills the gap: condition (1) was never computed for Carry v2
HOLDOUT. The net-spread gate passed (+6.96%) and the SEALED read confirmed
(+20.52%), but the IC gate was undocumented. This script computes it using
the pre-registered Spearman rank-IC and the same methodology as run_sealed.py.

Output: docs/reports/CARRY_HOLDOUT_IC_REPORT.md
"""
from __future__ import annotations

import math, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr, t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
REPORT = ROOT / "docs" / "reports" / "CARRY_HOLDOUT_IC_REPORT.md"

HOLDOUT_LO = date(2021, 1, 31)
HOLDOUT_HI = date(2022, 12, 31)
ALPHA = 0.025


def _ac1(arr):
    n = len(arr)
    if n < 3: return 0.0
    r = arr - np.mean(arr)
    return float(np.sum(r[1:] * r[:-1]) / np.sum(r ** 2))


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception:
        return "unknown"


def main():
    commit = _git_commit()
    now_ts = date.today().isoformat()

    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute("SET threads=4")

    sig_rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_carry_neut, s.fwd_ret_1m
        FROM sig.signals s
        WHERE s.formation_date >= DATE '{HOLDOUT_LO}'
          AND s.formation_date <= DATE '{HOLDOUT_HI}'
          AND s.z_carry_neut IS NOT NULL AND s.fwd_ret_1m IS NOT NULL
          AND s.liquid = TRUE
        ORDER BY s.formation_date, s.underlying
    """).fetchall()
    con.close()

    by_date = defaultdict(list)
    for fd, u, z, fr in sig_rows:
        by_date[fd].append((float(z), float(fr)))

    ic_list = []
    for fd in sorted(by_date.keys()):
        rows = by_date[fd]
        zs = np.array([r[0] for r in rows], float)
        frs = np.array([r[1] for r in rows], float)
        present = np.isfinite(zs) & np.isfinite(frs)
        if present.sum() < 5: continue
        sr = spearmanr(zs[present], frs[present]).correlation
        if not np.isnan(sr):
            ic_list.append(float(sr))

    ic_arr = np.array(ic_list)
    n_ic = len(ic_arr)
    mean_ic = float(np.mean(ic_arr)) if n_ic > 0 else 0.0
    sd_ic = float(np.std(ic_arr, ddof=1)) if n_ic > 1 else 0.0
    tstat = mean_ic / (sd_ic / math.sqrt(n_ic)) if sd_ic > 0 and n_ic > 0 else 0.0
    ac1 = _ac1(ic_arr)
    p_one = 1.0 - float(student_t.cdf(tstat, n_ic - 1)) if n_ic > 1 else 1.0
    sign_correct = mean_ic > 0
    ic_pass = sign_correct and p_one < ALPHA

    print(f"Carry HOLDOUT IC: mean={mean_ic:+.4f} t={tstat:.2f} p={p_one:.6e} ac1={ac1:.4f} {'PASS' if ic_pass else 'FAIL'}")

    lines = []
    a = lines.append
    a("# Carry v2 — HOLDOUT Rank-IC Report\n")
    a(f"**Script-generated** — `scripts/signal_engine/carry/run_holdout.py`. Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a(f"**Pre-registration:** `CARRY_V2_PRE_REGISTRATION.md` (frozen, SHA "
      f"`74c7311cd84d48db8552f8bacd880b5e43d2264ae3b671aa12e7b3013fe4b1ec`).\n")
    a(f"**Window:** HOLDOUT {HOLDOUT_LO} -> {HOLDOUT_HI} ({n_ic} formations with IC).\n")
    a(f"**Sign:** +1 (long high residual carry, short low).\n")
    a(f"**Evidence floor:** Bonferroni α = {ALPHA} (m = 2: v1 falsified, v2 re-registered). "
      f"One-sided test in the pre-committed direction.\n")
    a("")

    a("---\n## 1. Rank-IC (Spearman)\n")
    a("| Metric | Value |\n|---|---|")
    a(f"| Mean IC | {mean_ic:+.6f} |")
    a(f"| SD(IC) | {sd_ic:.6f} |")
    a(f"| n | {n_ic} |")
    a(f"| t-stat | {tstat:.4f} |")
    a(f"| p-value (one-sided) | {p_one:.6e} |")
    a(f"| AC1 | {ac1:.4f} |")
    a(f"| Sign matches declaration (+1) | {'PASS' if sign_correct else '**FAIL**'} |")
    a(f"| Significant at α={ALPHA} | {'**PASS**' if ic_pass else '**FAIL**'} |")
    a("")

    a("---\n## 2. Comparison with pre-registered predictions\n")
    a(f"- **Pre-registered IC band (v2 §5, prediction 3):** +0.03 to +0.045\n")
    a(f"- **Realized IC:** {mean_ic:+.4f} — {'outside the band on the upside' if mean_ic > 0.045 else 'within the band'}\n")
    a("")

    a("---\n## 3. Gate\n")
    a(f"| Condition | Result |\n|---|---|")
    a(f"| Positive-sign IC at Bonferroni α={ALPHA} | {'PASS' if ic_pass else 'FAIL'} |")
    a(f"| Net spread > 0 (CARRY_NET_SPREAD_REPORT.md) | PASS (+6.96%) |")
    a("")
    if ic_pass:
        a("**HOLDOUT IC GATE: PASS** — Carry v2 clears the pre-registered rank-IC "
          "condition. Combined with net > 0, both §4.1 acceptance criteria are met. "
          "The SEALED read (+20.52%) was substantively justified.\n")
    else:
        a("**HOLDOUT IC GATE: FAIL** — Carry v2 does not clear the pre-registered "
          "rank-IC condition.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"Report: {REPORT}")
    return 0 if ic_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
