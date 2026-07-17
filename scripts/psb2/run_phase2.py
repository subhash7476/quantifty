"""PSB-2 Phase 2 — candidate runs on real dev data (Prompt 2).

Usage: python scripts/psb2/run_phase2.py C2
       python scripts/psb2/run_phase2.py C3
       python scripts/psb2/run_phase2.py C4

Run order: C2 -> C3 -> C4 (§11.3). One report per candidate, committed as produced.
§9 immutability attaches the moment C2's report exists.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import duckdb

from scripts.psb1.screening_harness import (
    load_panel,
    fence_check,
    monthly_grid,
    DEV_HI,
    SEALED_LO,
    SEALED_HI,
)
from scripts.psb2 import harness as H

STORE = str(ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb")


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def compute_hash(result: H.CandidateResult) -> str:
    payload = {
        "cid": result.cid,
        "n_dates": result.n_dates,
        "mean_ic": result.mean_ic,
        "sd_ic": result.sd_ic,
        "tstat": result.tstat,
        "pvalue": result.pvalue,
        "ac1": result.ac1,
        "net_spread": result.net_spread,
        "gross_spread": result.gross_spread,
        "turnover": result.turnover,
        "fee_slip_drag_bp": result.fee_slip_drag_bp,
        "n_star": result.n_star,
        "power": result.power,
        "mean_ic_imputed": result.mean_ic_imputed,
        "first_half_ic": result.first_half_ic,
        "second_half_ic": result.second_half_ic,
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def n_star_exact(db_path: str, cadence: str) -> tuple[int, list[date]]:
    """Compute n* exactly from trading_calendar over sealed window (§3, dates-only)."""
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute(
        "SELECT trade_date FROM trading_calendar WHERE n_symbols >= 200 "
        "AND trade_date >= ? AND trade_date <= ? ORDER BY trade_date",
        [SEALED_LO, SEALED_HI],
    ).fetchall()
    con.close()
    cal = [r[0] for r in rows]
    if cadence == "fortnightly":
        grid = H.fortnightly_grid(cal)
    elif cadence == "monthly":
        grid = monthly_grid(cal)
    else:
        raise ValueError(f"Unknown cadence: {cadence}")
    return len(grid), grid


def run_candidate(cid: str) -> H.CandidateResult:
    """Load real panel, build scorer, evaluate candidate."""

    # -- §2: fence verification against the store (not the loaded panel) --
    fenced_max, unfenced_max, store_rows = fence_check(STORE, DEV_HI)
    assert fenced_max is not None and unfenced_max is not None
    if fenced_max == unfenced_max:
        raise RuntimeError(
            f"FENCE IS DEAD: fenced MAX={fenced_max} == unfenced MAX={unfenced_max} "
            f"— the fence is not excluding anything"
        )

    # -- §2: compute n* exactly --
    if cid in ("C2", "C3"):
        cadence = "fortnightly"
    else:
        cadence = "monthly"
    n_star_count, n_star_grid = n_star_exact(STORE, cadence)
    n_star_fg = n_star_count if cadence == "fortnightly" else n_star_exact(STORE, "fortnightly")[0]
    n_star_mg = n_star_count if cadence == "monthly" else n_star_exact(STORE, "monthly")[0]

    # -- Load panel --
    panel = load_panel(db_path=STORE, cutoff=DEV_HI)

    # -- Build scorer closures --
    if cid in ("C2", "C3"):
        fg = H.fortnightly_grid(panel.cal)

        def c2_fn(t: date) -> dict[str, float]:
            return H.score_c2_psb2(panel, t, fg=fg)

    if cid == "C2":
        score_fn = c2_fn
    elif cid == "C3":

        def c3_fn(t: date) -> dict[str, float]:
            return H.score_c3_psb2(panel, t, H.score_c2_psb2(panel, t, fg=fg))

        score_fn = c3_fn
    elif cid == "C4":
        mg = monthly_grid(panel.cal)

        def c4_fn(t: date) -> dict[str, float]:
            g = mg.index(t) if t in mg else -1
            if g < 0:
                return {}
            return H.score_c4_psb2(panel, t, g, mg)

        score_fn = c4_fn
    else:
        raise ValueError(f"Unknown candidate: {cid}")

    # -- Evaluate --
    if cid == "C4":
        result = H.evaluate_candidate_psb2(panel, cid, score_fn, STORE, monthly_grid_dates=mg)
    else:
        result = H.evaluate_candidate_psb2(panel, cid, score_fn, STORE, fortnightly_grid_dates=fg)

    return result, panel, fenced_max, unfenced_max, store_rows, n_star_count, n_star_fg, n_star_mg


def generate_report(
    result: H.CandidateResult,
    commit: str,
    store_rows: int,
    fenced_max: date,
    unfenced_max: date,
    n_star: int,
    n_star_fg: int,
    n_star_mg: int,
) -> str:
    r = result
    cid = r.cid

    if cid in ("C2", "C3"):
        cadence = "fortnightly"
        ppy = 24
        dev_lo = H.C2_DEV_LO if cid == "C2" else H.C3_DEV_LO
        design_turnover = "~0.15"
        design_fee_drag = "~78 bp/yr"
    else:
        cadence = "monthly"
        ppy = 12
        dev_lo = H.C4_DEV_LO
        design_turnover = "~0.17"
        design_fee_drag = "~2.5 pp/yr"

    nw_triggered = r.ac1 > H.AC1_TRIGGER

    # §8 eligibility
    eligible_i = r.mean_ic > 0
    eligible_ii = r.net_spread > 0
    eligible_iii = r.power >= 0.80
    all_eligible = eligible_i and eligible_ii and eligible_iii

    excl_total = sum(r.excl_counts) if r.excl_counts else 0
    fwd_miss_total = sum(r.fwd_missing_counts) if r.fwd_missing_counts else 0

    digest = compute_hash(r)

    lines: list[str] = []
    A = lines.append

    A(f"# PSB-2 Phase 2 {cid} Battery Report")
    A("")
    commit_ref = f"`{commit}`" if commit and commit != "unknown" else commit
    A(f"**Script-generated** — `scripts/psb2/run_phase2.py`. Deterministic run (§10). Code commit {commit_ref}.")
    A("")
    A(f"| Field | Value |")
    A(f"|---|---|")
    A(f"| Code commit | {commit_ref} |")
    A(f"| Store row count | {store_rows:,} |")
    A(f"| Store fenced MAX(trade_date) | {fenced_max} |")
    A(f"| Store unfenced MAX | {unfenced_max} |")
    A(f"| Fence proven | {'YES — fenced != unfenced' if fenced_max != unfenced_max else 'DEAD'} |")
    A(f"| Candidate | {cid} |")
    A(f"| Cadence | {cadence} ({ppy} ppy) |")
    A(f"| Dev window | {dev_lo} to {DEV_HI} |")
    realized_n = len(r.ic) if r.ic is not None and hasattr(r.ic, '__len__') else 0
    A(f"| N formation dates (grid) | {r.n_dates} |")
    A(f"| Realized n (scored formations) | {realized_n} |")
    A("")

    # -- §6 Metrics --
    A("## §6 Metrics")
    A("")
    A(f"| Metric | Value |")
    A(f"|---|---|")
    A(f"| Mean IC | {r.mean_ic:.6f} |")
    A(f"| SD IC | {r.sd_ic:.6f} |")
    A(f"| One-sided t | {r.tstat:.4f} |")
    A(f"| One-sided p | {r.pvalue:.6e} |")
    A(f"| AC\u2081 | {r.ac1:.6f} |")
    nw_str = f"{r.nw_t:.4f}" if (nw_triggered and r.nw_t is not None) else "N/A"
    A(f"| NW t (AC\u2081 > {H.AC1_TRIGGER}) | {nw_str} |")
    A(f"| Imputed mean IC (§4.2) | {r.mean_ic_imputed:.6f} |")
    A(f"| Sign flag | {r.sign_flag} |")
    A(f"| Min-names skipped | {r.min_names_skipped} |")
    A(f"| First-half mean IC | {r.first_half_ic:.6f} |")
    A(f"| Second-half mean IC | {r.second_half_ic:.6f} |")
    A("")

    # -- §4.1 Exclusion counts --
    A("## §4.1 Exclusion counts")
    A("")
    A(f"| Metric | Value |")
    A(f"|---|---|")
    A(f"| Formation-date exclusions (total) | {excl_total} |")
    A(f"| Forward-missing (total) | {fwd_miss_total} |")
    A("")
    if r.excl_counts:
        A(f"Per-date excl: min={min(r.excl_counts)} max={max(r.excl_counts)}")
        A(f"Per-date fwd-missing: min={min(r.fwd_missing_counts)} max={max(r.fwd_missing_counts)}")
        A("")

    # -- Quintile spread --
    A("## §6 Quintile spread")
    A("")
    A(f"| Metric | Value |")
    A(f"|---|---|")
    A(f"| Net top-quintile spread | {r.net_spread:.6f} (ann. return, net of fees) |")
    A(f"| Gross spread (top - base) | {r.gross_spread:.6f} |")
    A(f"| Fee+slippage drag | {r.fee_slip_drag_bp:.1f} bp/yr |")
    A(f"| One-way turnover | {r.turnover:.4f} |")
    A("")
    A(f"Design estimate (rationale, not prediction): turnover {design_turnover}, fee drag {design_fee_drag}.")
    A(f"Observed turnover {r.turnover:.4f}; observed drag {r.fee_slip_drag_bp:.1f} bp/yr.")
    A("")

    # -- §7 Power projection --
    A("## §7 Power projection")
    A("")
    A(f"| Metric | Value |")
    A(f"|---|---|")
    A(f"| n* (sealed grid 2023-01-01 to 2026-06-30) | {n_star} |")
    A(f"| n* fortnightly / monthly | {n_star_fg} / {n_star_mg} |")
    A(f"| \u03b4 (observed mean IC) | {r.mean_ic:.6f} |")
    A(f"| SD_dev | {r.sd_ic:.6f} |")
    A(f"| Noncentrality (\u03b4\u221a n* / SD) | {(r.mean_ic * math.sqrt(n_star) / r.sd_ic) if r.sd_ic > 0 else 0:.4f} |")
    A(f"| Power at \u03b4 | {r.power:.4f} |")
    A(f"| Power at \u03b4/2 | {r.power_half:.4f} |")
    pnw_str = f"{r.power_nw:.4f}" if (nw_triggered and r.power_nw is not None) else "N/A"
    A(f"| Power-NW at \u03b4 | {pnw_str} |")
    A(f"| Power hurdle | \u2265 {H.POWER_HURDLE} |")
    A("")

    if nw_triggered:
        A(f"**AC\u2081 exposure (§7):** AC\u2081 = {r.ac1:.6f} > {H.AC1_TRIGGER}. Adjacent fortnightly formations overlap in "
          "their 252-day delivery baseline. The simple-t projection may be optimistic — "
          "a fortnightly candidate can clear the 0.80 hurdle on a projection its own "
          "reported AC\u2081 shows is optimistic. The gating power remains simple-t. "
          "The operator reads every power number with this exposure in view.")

    # -- §8 Eligibility --
    A("")
    A("## §8 Eligibility")
    A("")
    A(f"| Criterion | Threshold | Observed | Pass |")
    A(f"|---|---|---|---|")
    A(f"| (i) Mean IC > 0 | > 0 | {r.mean_ic:.6f} | {eligible_i} |")
    A(f"| (ii) Net spread > 0 | > 0 | {r.net_spread:.6f} | {eligible_ii} |")
    A(f"| (iii) Power \u2265 0.80 | \u2265 0.80 | {r.power:.4f} | {eligible_iii} |")
    A("")
    if all_eligible:
        A(f"**Eligible:** all three §8 criteria met. {cid} proceeds to §8 ranking in Prompt 3.")
    else:
        A(f"**Not eligible:** one or more §8 criteria not met. {cid} cannot be the winner.")
    A("")

    # -- Common sub-window note --
    if cid in ("C2", "C3"):
        A(f"**Robustness sub-window:** {H.COMMON_SUBWINDOW_LO} to {DEV_HI}. "
          f"For C2/C3 this is their entire declared window — the declared-window columns "
          f"above are also the common sub-window columns and are not duplicated.")
    else:
        A(f"**Robustness sub-window:** {H.COMMON_SUBWINDOW_LO} to {DEV_HI} "
          f"(28 monthly grid dates for C4). See Prompt 3 for the sub-window column.")

    # -- Formation dates --
    A("")
    A(f"## Formation dates ({r.n_dates})")
    A("")
    if r.dates:
        A(f"First: {r.dates[0]}, Last: {r.dates[-1]}")
    A("")

    # -- Determinism --
    A("## §10 Determinism compliance")
    A("")
    A(f"Digest (sha256 of core metrics): `{digest}`")
    A("")
    A("This report is 100% script-generated. No hand-edited numbers. "
      "Re-running the identical code against the identical dev-fenced store "
      "yields byte-identical output.")
    A("")

    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/psb2/run_phase2.py <CID>")
        print("  CID: C2 | C3 | C4")
        sys.exit(1)

    cid = sys.argv[1].upper()
    if cid not in ("C2", "C3", "C4"):
        print(f"Unknown candidate: {cid}. Must be C2, C3, or C4.")
        sys.exit(1)

    commit = git_commit()
    print(f"Phase 2: running {cid} on real dev data (commit {commit})")
    print(f"Store: {STORE}")
    print(f"Cutoff: {DEV_HI}")

    result, panel, fenced_max, unfenced_max, store_rows, n_star, n_star_fg, n_star_mg = run_candidate(cid)

    report_path = ROOT / "docs" / "reports" / f"PSB2_{cid}_REPORT.md"
    report = generate_report(
        result, commit, store_rows, fenced_max, unfenced_max,
        n_star, n_star_fg, n_star_mg,
    )
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport written: {report_path}")

    # Summary to stdout
    r = result
    n_scored = len(r.ic) if hasattr(r.ic, '__len__') and r.ic is not None else "N/A"
    print(f"\n{cid} summary:")
    print(f"  N grid dates: {r.n_dates}")
    print(f"  N scored (n): {n_scored}")
    print(f"  Mean IC: {r.mean_ic:.6f}")
    print(f"  SD IC: {r.sd_ic:.6f}")
    print(f"  t: {r.tstat:.4f}")
    print(f"  p: {r.pvalue:.6e}")
    print(f"  AC1: {r.ac1:.6f}")
    print(f"  Net spread: {r.net_spread:.6f}")
    print(f"  Gross spread: {r.gross_spread:.6f}")
    print(f"  Turnover: {r.turnover:.4f}")
    print(f"  Fee drag: {r.fee_slip_drag_bp:.1f} bp/yr")
    print(f"  n*: {n_star}")
    print(f"  Power: {r.power:.4f}")
    print(f"  Digest: {compute_hash(r)}")


if __name__ == "__main__":
    main()
