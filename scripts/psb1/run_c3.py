"""PSB-1 Phase 2 C3 battery: script-generated report (delivery ratio z-score)."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))
sys.path.insert(0, str(ROOT / "scripts" / "csmp"))

import duckdb
from screening_harness import (
    load_panel, make_score_fn, evaluate_candidate,
    DEV_HI, C3_C4_DEV_LO,
    fence_check, load_factors_by_entity, load_ca_scope_exclusions, scan_data_integrity,
    reg_positions,
)

STORE = str(ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb")
REPORT = ROOT / "docs" / "reports" / "PSB1_C3_REPORT.md"

def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception:
        return "unknown"

def store_stamps():
    con = duckdb.connect(STORE, read_only=True)
    rows = con.execute("SELECT COUNT(*) FROM equity_bhavcopy_adjusted").fetchone()[0]
    fenced = con.execute("SELECT MAX(trade_date) FROM equity_bhavcopy_adjusted WHERE trade_date<=?", [DEV_HI]).fetchone()[0]
    unfenced = con.execute("SELECT MAX(trade_date) FROM equity_bhavcopy_adjusted").fetchone()[0]
    con.close()
    return rows, fenced, unfenced

def main():
    commit = git_commit()
    store_rows, fenced_max, unfenced_max = store_stamps()
    fence_check(STORE, DEV_HI)

    print("Building D5 register...")
    fbe = load_factors_by_entity(STORE, cutoff=DEV_HI)
    documented = load_ca_scope_exclusions(STORE, cutoff=DEV_HI)
    panel = load_panel(db_path=STORE, cutoff=DEV_HI)
    scan = scan_data_integrity(panel, fbe, documented)
    reg_pos = reg_positions(panel, scan.register)

    print("Loading panel for C3...")
    panel = load_panel(db_path=STORE, cutoff=DEV_HI)

    print("Making C3 score function...")
    fn = make_score_fn(panel, "C3", reg_pos=reg_pos)

    print("Evaluating C3 candidate...")
    result = evaluate_candidate(panel, "C3", fn, db_path=STORE, reg_pos=reg_pos)

    r = result
    nw_triggered = abs(r.ac1) > 0.10

    w = []
    W = w.append
    W("# PSB-1 Phase 2 C3 Battery Report — Delivery Ratio Z-Score")
    W("")
    W("**Script-generated** — `scripts/psb1/run_c3.py`. Deterministic run (§10).")
    W("")
    W("| Field | Value |")
    W("|---|---|")
    W(f"| Code commit | `{commit}` |")
    W(f"| Store row count | {store_rows:,} |")
    W(f"| Store fenced MAX(trade_date) | {fenced_max} |")
    W(f"| Store unfenced MAX | {unfenced_max} |")
    W(f"| Candidate | {r.cid} |")
    W(f"| Cadence | weekly |")
    W(f"| Dev window | {C3_C4_DEV_LO} to {DEV_HI} |")
    W(f"| N formation dates (n) | {r.n_dates} |")
    W("")
    W("## §6 Metrics")
    W("")
    W("| Metric | Value |")
    W("|---|---|")
    W(f"| Mean IC | {r.mean_ic:.6f} |")
    W(f"| SD IC | {r.sd_ic:.6f} |")
    W(f"| One-sided t | {r.tstat:.4f} |")
    W(f"| One-sided p | {r.pvalue:.6e} |")
    W(f"| AC₁ | {r.ac1:.6f} |")
    W(f"| NW t (|AC₁|>{0.10}) | {'N/A' if not nw_triggered else f'{r.nw_t:.4f}'} |")
    W(f"| Imputed mean IC (§4.2) | {r.mean_ic_imputed:.6f} |")
    W(f"| Sign flag | {r.sign_flag} |")
    W(f"| Min-names skipped | {r.min_names_skipped} |")
    W(f"| First-half mean IC | {r.first_half_ic:.6f} |")
    W(f"| Second-half mean IC | {r.second_half_ic:.6f} |")
    W("")
    W("## §4.1 Exclusion counts")
    W("")
    W("| Metric | Value |")
    W("|---|---|")
    excl_total = sum(r.excl_counts) if r.excl_counts else 0
    fwd_miss_total = sum(r.fwd_missing_counts) if r.fwd_missing_counts else 0
    ca_excl_total = sum(r.ca_excl_counts) if r.ca_excl_counts else 0
    W(f"| Formation-date exclusions (total) | {excl_total} |")
    W(f"| Forward-missing (total) | {fwd_miss_total} |")
    W(f"| CA-excluded forward (D5.8, total) | {ca_excl_total} |")
    W("")
    if r.excl_counts:
        W(f"Per-date excl: min={min(r.excl_counts)} max={max(r.excl_counts)}")
        W(f"Per-date fwd-missing: min={min(r.fwd_missing_counts)} max={max(r.fwd_missing_counts)}")
        W(f"Per-date ca-excl: min={min(r.ca_excl_counts)} max={max(r.ca_excl_counts)}")
        W("")
    W("## §6 Quintile spread")
    W("")
    W("| Metric | Value |")
    W("|---|---|")
    W(f"| Net top-quintile spread (upper-bound) | {r.net_spread:.6f} (ann. return, net of fees) |")
    W(f"| Gross spread (top - base) | {r.gross_spread:.6f} |")
    W(f"| Q1-Q5 spread | {r.q1_q5:.6f} |")
    W(f"| Fee+slippage drag | {r.fee_slip_drag_bp:.1f} bp/yr |")
    W(f"| One-way turnover | {r.turnover:.4f} |")
    W("")
    W("## §7 Power projection")
    W("")
    W("| Metric | Value |")
    W("|---|---|")
    W(f"| n* (sealed grid [2023-2026]) | {r.n_star} |")
    W(f"| Power at δ (observed mean IC) | {r.power:.4f} |")
    W(f"| Power at δ/2 | {r.power_half:.4f} |")
    W(f"| Power-NW at δ | {'N/A' if not nw_triggered else f'{r.power_nw:.4f}'} |")
    W("")
    W(f"## Formation dates ({r.n_dates})")
    W("")
    W(f"First: {r.dates[0]}, Last: {r.dates[-1]}")
    W("")
    W("## §10 Determinism compliance")
    W("")
    W("This report is 100% script-generated. No hand-edited numbers.")
    W("")

    report = "\n".join(w) + "\n"
    REPORT.write_text(report, encoding="utf-8")
    print(f"\nReport written: {REPORT}")
    print(f"C3 summary: n={r.n_dates}, mean IC={r.mean_ic:.6f}, t={r.tstat:.4f}, p={r.pvalue:.6e}")

if __name__ == "__main__":
    main()
