"""TS Basis — HOLDOUT Read

Confirms the pre-registered hypothesis on the HOLDOUT window (2021-01 -> 2022-12),
the only clean out-of-sample window for TS Basis.

Pre-reg: TS_BASIS_PHASE0_PRE_REGISTRATION.md (frozen, SHA 07265b50...)
Protocol: §6 — HOLDOUT must show positive-sign IC significant at Bonferroni
  alpha=0.025 (m>=2) AND net > 0. If both fail, TS Basis is dead. If both pass,
  SEALED read authorized.

Output: docs/reports/TS_BASIS_HOLDOUT_REPORT.md
"""
from __future__ import annotations

import json, math, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.signal_engine.ts_basis.run_net_spread import _simulate

SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "TS_BASIS_HOLDOUT_REPORT.md"

HOLDOUT_LO = date(2021, 1, 1)
HOLDOUT_HI = date(2022, 12, 31)
ALPHA = 0.025  # Bonferroni, m>=2 (carry + ts_basis sign discovery on TRAIN)


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
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    # ── Full simulation ──
    sim = _simulate("HOLDOUT", HOLDOUT_LO, HOLDOUT_HI, con)
    con.close()

    # ── IC computation from simulation (already has raw net spreads but not ICs) ──
    # Rerun with IC collection
    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    sig_rows = con.execute(f"""
        SELECT formation_date, underlying, z_ts, fwd_ret_1m
        FROM sig.signals WHERE formation_date >= DATE '{HOLDOUT_LO}'
        AND formation_date <= DATE '{HOLDOUT_HI}'
        AND z_ts IS NOT NULL AND fwd_ret_1m IS NOT NULL AND liquid = TRUE
        ORDER BY formation_date, underlying
    """).fetchall()
    con.close()

    ic_list = []
    by_date = defaultdict(list)
    for fd, u, z, fr in sig_rows:
        by_date[fd].append((float(z), float(fr)))
    for fd in sorted(by_date.keys()):
        rows = by_date[fd]
        zs = np.array([r[0] for r in rows], float)
        frs = np.array([r[1] for r in rows], float)
        present = np.isfinite(zs) & np.isfinite(frs)
        if present.sum() < 5: continue
        sr = np.corrcoef(zs[present], frs[present])[0, 1]
        if not np.isnan(sr):
            ic_list.append(float(sr))

    ic_arr = np.array(ic_list)
    n_ic = len(ic_arr)
    mean_ic = float(np.mean(ic_arr)) if n_ic > 0 else 0.0
    sd_ic = float(np.std(ic_arr, ddof=1)) if n_ic > 1 else 0.0
    tstat = mean_ic / (sd_ic / math.sqrt(n_ic)) if sd_ic > 0 and n_ic > 0 else 0.0
    ac1 = _ac1(ic_arr)

    # One-sided p: P(T > tstat) under t-distribution with n-1 df
    from scipy.stats import t as student_t
    p_one = 1.0 - float(student_t.cdf(tstat, n_ic - 1)) if n_ic > 1 else 1.0

    sign_correct = mean_ic > 0
    ic_significant = sign_correct and p_one < ALPHA
    net_positive = sim.get("ann_net", 0) > 0 if isinstance(sim, dict) else False

    # ── Report ──
    lines = []
    a = lines.append
    a("# TS Basis — HOLDOUT Read Report\n")
    a(f"**Script-generated** — `scripts/signal_engine/ts_basis/run_holdout.py`. Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a(f"**Pre-registration:** `TS_BASIS_PHASE0_PRE_REGISTRATION.md` (frozen, SHA-256 "
      f"`07265b507179667588d06cb35c1e98c72bd065a3bbf95cf9a6c7d8b996a1ad84`).\n")
    a(f"**Window:** HOLDOUT {HOLDOUT_LO} -> {HOLDOUT_HI} ({n_ic} formations with IC, "
      f"{sim.get('return_periods', 0)} return periods).\n")
    a(f"**Sign:** +1 (long high z_ts, short low z_ts).\n")
    a(f"**Evidence floor:** Bonferroni α = {ALPHA} (m ≥ 2: cross-sectional carry + TS Basis "
      f"sign discovery on TRAIN). One-sided test in the pre-committed direction.\n")
    a("")

    a("---\n## 1. Rank-IC\n")
    a("| Metric | Value |")
    a("|---|---|")
    a(f"| Mean IC | {mean_ic:+.6f} |")
    a(f"| SD(IC) | {sd_ic:.6f} |")
    a(f"| n (formations) | {n_ic} |")
    a(f"| t-stat | {tstat:.4f} |")
    a(f"| p-value (one-sided) | {p_one:.6e} |")
    a(f"| AC1 | {ac1:.4f} |")
    a(f"| Sign matches declaration (+1) | {'PASS' if sign_correct else '**FAIL**'} |")
    a(f"| Significant at α={ALPHA} | {'**PASS**' if ic_significant else '**FAIL**'} |")
    a("")

    a("---\n## 2. Net-of-Fee Spread\n")
    if isinstance(sim, dict) and "error" not in sim:
        a("| Metric | Value |")
        a("|---|---|")
        a(f"| Gross annualized | {sim['ann_gross']*100:+.2f}% |")
        a(f"| Net annualized | {sim['ann_net']*100:+.2f}% |")
        a(f"| Fee drag | {sim['fee_drag_bp']:.0f} bp |")
        a(f"| Avg turnover | {sim['avg_turnover']:.3f} |")
        a(f"| Return periods | {sim['return_periods']} |")
        a(f"| Net > 0 | {'**PASS**' if net_positive else '**FAIL**'} |")
    else:
        a(f"Simulation error: {sim.get('error', 'unknown')}\n")
    a("")

    a("---\n## 3. Fee Component Breakdown\n")
    if isinstance(sim, dict) and "fee_breakdown" in sim:
        fb = sim["fee_breakdown"]
        total_fee = sum(fb.values())
        a("| Component | Total (Rs) | Share |")
        a("|---|---:|--:|")
        for comp in ["brokerage", "stt", "exchange_txn", "sebi_fee", "stamp_duty", "gst"]:
            val = fb.get(comp, 0.0)
            a(f"| {comp} | {val:,.0f} | {val/total_fee*100:.1f}% |")
        a(f"| **Total fees** | **{total_fee:,.0f}** | 100.0% |")
    a("")

    a("---\n## 4. HOLDOUT Gate (per pre-reg §6)\n")
    a(f"| Condition | Result | Detail |")
    a(f"|---|---|---|")
    a(f"| Positive-sign IC significant (α={ALPHA}, one-sided) | "
      f"{'PASS' if ic_significant else '**FAIL**'} | "
      f"IC={mean_ic:+.4f}, t={tstat:.2f}, p={p_one:.6e} |")
    a(f"| Net long/short spread > 0 | "
      f"{'PASS' if net_positive else '**FAIL**'} | "
      f"{sim.get('ann_net', 0)*100:+.2f}% annualized |")
    a("")

    gate_pass = ic_significant and net_positive
    if gate_pass:
        a("**HOLDOUT VERDICT: PASS** — TS Basis clears both pre-registered acceptance "
          "criteria on the only clean out-of-sample window. The signal survives "
          "multiplicity-adjusted significance (m≥2, α=0.025) and produces a positive "
          "net spread under futures fees.\n\n"
          "Proceed to SEALED read (2023-01-01 -> 2026-07-20) under "
          "`TS_BASIS_SEALED_READ_PROTOCOL.md`. The SEALED protocol must be frozen "
          "before the read.\n")
    else:
        a("**HOLDOUT VERDICT: FAIL** — TS Basis did not survive the holdout. "
          "The signal is dead; there is no v2 (sign committed and unflippable). "
          "An honest terminal result, reported as-is.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"Report: {REPORT}")
    print(f"HOLDOUT IC: {mean_ic:+.4f} t={tstat:.2f} p={p_one:.6e} {'PASS' if ic_significant else 'FAIL'}")
    print(f"HOLDOUT net: {sim.get('ann_net', 0)*100:+.2f}% {'PASS' if net_positive else 'FAIL'}")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
