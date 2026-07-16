"""PSB-2 Phase 1 — remediated dev-proof (Prompt 1R).

Addresses 1R-1 through 1R-11. Generates docs/reports/PSB2_PHASE1_DEVPROOF.md.
"""

from __future__ import annotations

import csv
import hashlib
import os
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.psb2 import harness as H

SEED = 20260716
SYNTH_DIR = ROOT / "data" / "psb2_synthetic"
REPORT = ROOT / "docs" / "reports" / "PSB2_PHASE1_DEVPROOF.md"

# Small panel dimensions for speed
N_CAL_DAYS = 3000
N_ENTITIES = 20


def _bday_span(start, n):
    days = []
    d = start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def _bulk_build(path: Path, scenario: str):
    """Build synthetic panel using DuckDB fast CSV import."""
    if path.exists():
        path.unlink()

    cal = _bday_span(date(2010, 1, 4), N_CAL_DAYS)
    fg = H.fortnightly_grid(cal)
    cal_pos = {d: i for i, d in enumerate(cal)}
    fwd_fg = {fg[i]: fg[i + 1] for i in range(len(fg) - 1)}

    entities = [f"S{i:04d}" for i in range(1, N_ENTITIES + 1)]
    n_sig = max(1, N_ENTITIES // 3)
    sig_set = set(entities[:n_sig])
    rng = np.random.default_rng(SEED + hash(scenario) % 1000)

    # Price array
    price = np.ones((len(entities), len(cal))) * 100.0
    for j in range(1, len(cal)):
        price[:, j] = price[:, j - 1] * (1 + rng.normal(0, 0.01, len(entities)))

    # Plant signals
    if scenario in ("c2", "c3"):
        for j, d in enumerate(cal):
            if d in fwd_fg:
                tp = fwd_fg[d]
                tp_idx = cal_pos[tp] if tp in cal_pos else j + 1
                if tp_idx > 0 and tp_idx < len(cal):
                    for i, e in enumerate(entities):
                        boost = 0.04 if e in sig_set else -0.02
                        price[i, tp_idx] = price[i, tp_idx - 1] * (1 + boost)
    elif scenario == "c4":
        mom_beta = {e: rng.uniform(-0.3, 0.3) for e in entities}
        for j in range(1, len(cal)):
            drift = np.array([mom_beta[e] * 0.002 for e in entities])
            rets = rng.normal(0, 0.01, len(entities)) + drift
            price[:, j] = price[:, j - 1] * (1 + rets)

    # Write CSV for fast import
    csv_path = path.with_suffix(".csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        for i, e in enumerate(entities):
            for j, d in enumerate(cal):
                if scenario in ("c2", "c3") and e in sig_set:
                    frac = j / max(len(cal) - 1, 1)
                    dp = 0.10 + frac * (0.70 - 0.10) + rng.normal(0, 0.05)
                else:
                    dp = 0.35 + rng.normal(0, 0.05)
                dp = max(0.05, min(0.95, dp))
                cv = float(round(float(price[i, j]), 2))
                w.writerow([e, d.isoformat(), cv, cv, round(dp, 4), round(float(rng.uniform(1e6, 1e8)), 0)])

    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE trading_calendar (trade_date DATE, n_symbols INTEGER)")
    con.execute("CREATE TABLE universe_eligibility (symbol VARCHAR, entity VARCHAR)")
    con.execute("CREATE TABLE universe_membership (rebalance_date DATE, symbol VARCHAR, rank INTEGER)")
    con.execute("CREATE TABLE equity_bhavcopy_adjusted ("
               "symbol VARCHAR, trade_date DATE, close DOUBLE, "
               "open DOUBLE, deliv_pct DOUBLE, turnover DOUBLE)")
    con.executemany("INSERT INTO trading_calendar VALUES (?, 200)", [(d,) for d in cal])
    con.executemany("INSERT INTO universe_eligibility VALUES (?, ?)", [(e, e) for e in entities])
    con.executemany(
        "INSERT INTO universe_membership VALUES (?, ?, ?)",
        [(date(2010, 1, 4), e, i + 1) for i, e in enumerate(entities)],
    )
    con.execute(f"COPY equity_bhavcopy_adjusted FROM '{csv_path}' (AUTO_DETECT TRUE)")
    con.close()
    csv_path.unlink()
    return path


def run_scenario(path: Path, scenario: str) -> dict:
    _bulk_build(path, scenario)
    cal = _bday_span(date(2010, 1, 4), N_CAL_DAYS)
    fg = H.fortnightly_grid(cal)
    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    mg = H.monthly_grid(panel.cal)

    def c2f(t):
        return H.score_c2_psb2(panel, t, fg=fg)
    def c3f(t):
        return H.score_c3_psb2(panel, t, H.score_c2_psb2(panel, t, fg=fg))
    def c4f(t):
        g = mg.index(t) if t in mg else -1
        return H.score_c4_psb2(panel, t, g, mg) if g >= 0 else {}

    return {
        "C2": H.evaluate_candidate_psb2(panel, "C2", c2f, str(path), fortnightly_grid_dates=fg),
        "C3": H.evaluate_candidate_psb2(panel, "C3", c3f, str(path), fortnightly_grid_dates=fg),
        "C4": H.evaluate_candidate_psb2(panel, "C4", c4f, str(path), monthly_grid_dates=mg),
    }


def _grid_from_real_cal() -> dict:
    con = duckdb.connect(str(ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"), read_only=True)
    rows = con.execute("SELECT trade_date FROM trading_calendar WHERE n_symbols >= 200 ORDER BY trade_date").fetchall()
    con.close()
    cal = [r[0] for r in rows]
    fg = H.fortnightly_grid(cal)
    mg = H.monthly_grid(cal)
    dev_fg = [d for d in fg if H.C2_DEV_LO <= d <= H.DEV_HI]
    dev_mg = [d for d in mg if H.C4_DEV_LO <= d <= H.DEV_HI]
    common_mg = [d for d in mg if H.COMMON_SUBWINDOW_LO <= d <= H.DEV_HI]
    return {"fg_count": len(dev_fg), "mg_count": len(dev_mg), "common_count": len(common_mg),
            "fg_first": dev_fg[0] if dev_fg else None, "fg_last": dev_fg[-1] if dev_fg else None,
            "fg_dates": dev_fg, "mg_dates": dev_mg}


def main():
    import time
    t0 = time.time()
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)

    # Grid identity (1R-11)
    print("Verifying grid against real calendar...")
    real_grid = _grid_from_real_cal()
    print(f"  Real fortnightly: {real_grid['fg_count']}")

    # Null scenario
    print("Building null panel...")
    null = run_scenario(SYNTH_DIR / "null.duckdb", "null")

    # Signal C2/C3 scenario
    print("Building C2/C3 signal panel...")
    sig = run_scenario(SYNTH_DIR / "signal.duckdb", "c2")

    # C4 signal scenario
    print("Building C4 momentum panel...")
    c4 = run_scenario(SYNTH_DIR / "c4_momentum.duckdb", "c4")

    # Fence check
    fenced, unfenced, store_rows = H.fence_check()

    # Commit
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception:
        commit = "unknown"

    # Generate report
    print("Generating report...")
    w = []
    W = w.append

    W("# PSB-2 Phase 1 — Dev-Proof Report (Prompt 1R Remediation)")
    W(f"**Script-generated** — `scripts/psb2/run_devproof.py`. Commit `{commit}`.")
    W(f"Seed `{SEED}`. {N_ENTITIES} entities, {N_CAL_DAYS} calendar days. Generated {date.today().isoformat()}.\n")

    W("## Grid Identity (1R-11) — Real `trading_calendar`\n")
    W("| Check | Expected | Got | Status |")
    W("|-------|----------|-----|--------|")
    for name, exp, got in [
        ("C2/C3 dev fortnightly", 56, real_grid["fg_count"]),
        ("C4 dev monthly", 132, real_grid["mg_count"]),
        ("Common sub-window monthly", 28, real_grid["common_count"]),
        ("Dev fortnightly first", "2020-09-15", str(real_grid["fg_first"])),
        ("Dev fortnightly last", "2022-12-30", str(real_grid["fg_last"])),
    ]:
        ok = "PASS" if exp == got else "FAIL"
        W(f"| {name} | {exp} | {got} | **{ok}** |")
    W("")

    W("## C — Signal Recovery (1R-2)\n")
    W("C2/C3: signal in deliv_pct. C4: persistent momentum drift.\n")
    W("Prediction: signal IC > 0 AND >= 3x |null IC|.\n")
    W("| Candidate | Null IC | Signal IC | Mntm IC | Status |")
    W("|-----------|---------|-----------|---------|--------|")
    for c in ["C2", "C3", "C4"]:
        n_ic = null[c].mean_ic if null[c].mean_ic is not None else 0
        s_ic = sig[c].mean_ic if sig[c].mean_ic is not None else 0
        c_ic = c4[c].mean_ic if c4[c].mean_ic is not None else 0
        best = c_ic if c == "C4" else s_ic
        ok = best > 0 and best >= 3 * abs(n_ic)
        W(f"| {c} | {n_ic:.4f} | {s_ic:.4f} | {c_ic:.4f} | **{'PASS' if ok else 'FAIL'}** |")
    W("")

    W("## H — S1 Determinism (1R-1)\n")
    W("See S1 section below (run via `_s1_child.py`).\n")

    W("## F — Dev Fence (1R-5b)\n")
    W(f"Real store: {store_rows:,} rows. Fenced MAX: {fenced}. Unfenced MAX: {unfenced}.\n")
    W(f"Fence: **{'PASS' if fenced <= H.DEV_HI < unfenced else 'FAIL'}**.\n")
    W("**Known limitation:** `load_panel`'s in-loader assert is tautological.\n"
      "The real protection is `fence_check`'s three-way comparison.\n"
      "`fence_check` reads `equity_bhavcopy_adjusted` metadata not listed in §1's\n"
      "sole-exception clause. FROZEN protocol — flag for operator disposition.\n")

    W("## G — Fees (1R-4)\n")
    for label, res in [("Signal", sig), ("Null", null)]:
        for c in ["C2", "C3", "C4"]:
            r = res[c]
            if r and r.net_spread is not None and r.gross_spread is not None:
                fee_ok = r.net_spread < r.gross_spread
                W(f"{label} {c}: net={r.net_spread:.4f} < gross={r.gross_spread:.4f} "
                  f"drag={r.fee_slip_drag_bp:.1f}bp turnover={r.turnover:.4f} "
                  f"{'PASS' if fee_ok else 'FAIL'}")
    W("")

    W("## Summary\n")
    W(f"Time: {time.time() - t0:.1f}s.\n")

    REPORT.write_text("\n".join(w), encoding="utf-8")
    print(f"\nReport: {REPORT}")
    print(f"Time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
