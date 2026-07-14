"""PSB-1 Phase-1 synthetic dev-proof (Prompt 1 + remediation Prompt 1-A).

Builds synthetic panels in their OWN DuckDB files under data/psb1_synthetic/ (never the
real store), runs the harness end-to-end, and emits the script-generated report
docs/reports/PSB1_PHASE1_HARNESS_REPORT.md with falsifiable predictions P1-P7 + P4b and
an R1 data-integrity demonstration.

No candidate score is computed on real data. The only real-store touches are dates/counts
reads: the P7 fence-check and the real n* count (§1/§7 exception). Deterministic: seed
20260713 (protocol §10); S1 proves it across two interpreters with differing PYTHONHASHSEED.

Usage:
    python scripts/psb1/run_synthetic_devproof.py                 # full run + report
    python scripts/psb1/run_synthetic_devproof.py --canonical-out PATH   # S1 worker (internal)
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))

import screening_harness as H  # noqa: E402

SEED = 20260713
SYNTH_DIR = ROOT / "data" / "psb1_synthetic"
REPORT = ROOT / "docs" / "reports" / "PSB1_PHASE1_HARNESS_REPORT.md"
REAL_STORE = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"

N_NAMES = 210
N_WEEKS = 260
DAYS_PER_WEEK = 5
START = date(2018, 1, 1)


def _calendar():
    days = []
    d = START
    for _ in range(N_WEEKS * DAYS_PER_WEEK):
        days.append(d)
        d += timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
    return days


def build_panel(path, scenario, rng):
    """Synthetic panel. Weekly return R_{i,k} (one log-return/week on the grid day; other
    4 days flat). With 5 trading days/week t-5 == previous grid, so C1 s = -R_k and
    forward = R_{k+1}.
      'null'     : R iid.
      'reversal' : R AR(1) coef -c (c=0.05) -> C1 mean IC ~ 0.05; delistings among losers.
      'delivery' : forward = d*z(abnormal delivery) + noise -> C3 mean IC > 0.
    """
    days = _calendar()
    T = len(days)
    grid_pos = [(k + 1) * DAYS_PER_WEEK - 1 for k in range(N_WEEKS)]
    names = [f"S{i:04d}" for i in range(N_NAMES)]

    c = 0.05
    sigma = 0.03
    d_strength = 0.0024

    R = np.zeros((N_WEEKS, N_NAMES))
    R[0] = rng.normal(0, sigma, N_NAMES)
    base_deliv = rng.uniform(0.30, 0.60, N_NAMES)
    abn = rng.normal(0, 1.0, (N_WEEKS, N_NAMES))
    for k in range(1, N_WEEKS):
        eta = rng.normal(0, sigma * np.sqrt(1 - c * c), N_NAMES)
        if scenario == "reversal":
            R[k] = -c * R[k - 1] + eta
        elif scenario == "delivery":
            R[k] = d_strength * abn[k - 1] + rng.normal(0, sigma, N_NAMES)
        else:
            R[k] = rng.normal(0, sigma, N_NAMES)

    logret = np.zeros((T, N_NAMES))
    for k in range(N_WEEKS):
        logret[grid_pos[k]] = np.log1p(R[k])
    prices = 100.0 * np.exp(np.cumsum(logret, axis=0))

    deliv = np.zeros((T, N_NAMES))
    for k in range(N_WEEKS):
        lo = 0 if k == 0 else grid_pos[k - 1] + 1
        hi = grid_pos[k]
        wk_val = np.clip(base_deliv + 0.10 * abn[k] + rng.normal(0, 0.01, N_NAMES), 0.01, 0.99)
        for j in range(lo, hi + 1):
            deliv[j] = wk_val

    missing = np.zeros((T, N_NAMES), dtype=bool)
    if scenario == "reversal":
        for k in range(1, N_WEEKS - 1):
            losers = np.argsort(R[k])[:N_NAMES // 10]
            pick = losers[rng.random(len(losers)) < 0.5]
            missing[grid_pos[k + 1], pick] = True

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    sealed = []
    sd = date(2023, 1, 2)
    while sd <= date(2026, 6, 30):
        if sd.weekday() < 5:
            sealed.append(sd)
        sd += timedelta(days=1)
    cal_df = pd.DataFrame({"trade_date": days + sealed,
                           "n_symbols": [N_NAMES] * (len(days) + len(sealed))})
    elig_df = pd.DataFrame({"symbol": names, "entity": names})
    memb_df = pd.DataFrame({"rebalance_date": [START] * N_NAMES,
                            "symbol": names, "rank": list(range(1, N_NAMES + 1))})
    day_arr = np.array(days)
    keep = ~missing
    jj, ii = np.where(keep)
    px_df = pd.DataFrame({
        "trade_date": day_arr[jj],
        "symbol": np.array(names)[ii],
        "close": prices[jj, ii].astype(float),
        "open": [None] * len(jj),
        "deliv_pct": deliv[jj, ii].astype(float),
        "turnover": (1e6 + ii).astype(float),
    })
    con.register("cal_df", cal_df); con.execute(
        "CREATE TABLE trading_calendar AS SELECT trade_date::DATE trade_date, n_symbols FROM cal_df")
    con.register("elig_df", elig_df); con.execute(
        "CREATE TABLE universe_eligibility AS SELECT * FROM elig_df")
    con.register("memb_df", memb_df); con.execute(
        "CREATE TABLE universe_membership AS SELECT rebalance_date::DATE rebalance_date, symbol, rank FROM memb_df")
    con.register("px_df", px_df); con.execute(
        "CREATE TABLE equity_bhavcopy_adjusted AS "
        "SELECT trade_date::DATE trade_date, symbol, close, open, deliv_pct, turnover FROM px_df")
    con.close()
    return path


def _run_all(scenario_path):
    panel = H.load_panel(db_path=scenario_path, cutoff=H.DEV_HI)
    out = {}
    for cid in ("C1", "C2", "C3", "C4", "C5"):
        fn = H.make_score_fn(panel, cid)
        out[cid] = H.evaluate_candidate(panel, cid, fn, db_path=str(scenario_path))
    return out


def _r1_real():
    """Run the §11.3 R1 scan on the REAL dev-fenced adjusted panel (permitted: the scan is
    not a candidate score). Returns the CAScanResult — the operator artifact (Prompt 1-B)."""
    panel = H.load_panel(db_path=str(REAL_STORE), cutoff=H.DEV_HI)
    factors = H.load_factors_by_entity(REAL_STORE, H.DEV_HI)
    documented = H.load_ca_scope_exclusions(REAL_STORE, H.DEV_HI)
    return H.scan_data_integrity(panel, factors, documented)


def _predictions(res_null, res_rev, res_del, fenced, unfenced, rows):
    c1_rev, c1_null = res_rev["C1"], res_null["C1"]
    c3_del = res_del["C3"]
    checks = []
    p1 = 0.03 <= c1_rev.mean_ic <= 0.07
    checks.append(("P1 planted signal (C1 reversal)",
                   f"mean IC={c1_rev.mean_ic:.4f} (target ~0.05, tol +/-0.02)", p1))
    lo = c1_null.mean_ic - 1.96 * c1_null.sd_ic / np.sqrt(c1_null.n_dates)
    hi = c1_null.mean_ic + 1.96 * c1_null.sd_ic / np.sqrt(c1_null.n_dates)
    checks.append(("P2 null (C1 null scenario)",
                   f"mean IC={c1_null.mean_ic:.4f} 95%CI[{lo:.4f},{hi:.4f}] covers 0",
                   lo <= 0 <= hi))
    checks.append(("P3 sign wiring (C1>0 reversal; C3>0 delivery)",
                   f"C1={c1_rev.mean_ic:.4f}>0 ; C3={c3_del.mean_ic:.4f}>0",
                   c1_rev.mean_ic > 0 and c3_del.mean_ic > 0))
    checks.append(("P4 F2 delisting machinery (imputed < primary for C1)",
                   f"primary={c1_rev.mean_ic:.4f} imputed={c1_rev.mean_ic_imputed:.4f}",
                   c1_rev.mean_ic_imputed < c1_rev.mean_ic))
    p4b = c1_rev.sign_flag and not c1_null.sign_flag
    checks.append(("P4b §4.2 sign-flag fires on reversal C1, not on null C1",
                   f"reversal C1 flag={c1_rev.sign_flag} ; null C1 flag={c1_null.sign_flag}", p4b))
    p5 = (c1_rev.fees_topq > 0 and c1_rev.fees_base > 0
          and c1_rev.net_spread < c1_rev.gross_spread)
    checks.append(("P5 fees (both legs charged; net < gross)",
                   f"fees_topq={c1_rev.fees_topq:.1f} fees_base={c1_rev.fees_base:.1f} "
                   f"net={c1_rev.net_spread:.4f} < gross={c1_rev.gross_spread:.4f}", p5))
    checks.append(("P7 fence-check real store (fenced <= cutoff < unfenced)",
                   f"fenced={fenced} <= {H.DEV_HI} < unfenced={unfenced}; rows={rows:,}",
                   fenced <= H.DEV_HI < unfenced))
    return checks


def _git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=ROOT).decode().strip()
    except Exception:
        return "unknown"


def _cand_table(title, res):
    lines = [f"### {title}\n",
             "| Cand | n | skip | fwd_miss | ca_excl | mean IC | SD | t | p(1s) | AC1 | NW t | "
             "imputed IC | flag | net spread | gross spread | Q1-Q5 | turnover | n* | power | power(d/2) |",
             "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|--:|--:|--:|--:|--:|--:|--:|"]
    for cid in ("C1", "C2", "C3", "C4", "C5"):
        r = res[cid]
        nw = f"{r.nw_t:.2f}" if r.nw_t is not None else "-"
        pw_nw = f" (NW {r.power_nw:.2f})" if r.power_nw is not None else ""
        lines.append(
            f"| {cid} | {r.n_dates} | {r.min_names_skipped} | {sum(r.fwd_missing_counts)} | "
            f"{sum(r.ca_excl_counts)} | {r.mean_ic:.4f} | {r.sd_ic:.4f} | "
            f"{r.tstat:.2f} | {r.pvalue:.4f} | {r.ac1:.3f} | {nw} | {r.mean_ic_imputed:.4f} | "
            f"{'FLAG' if r.sign_flag else '-'} | {r.net_spread:.4f} | {r.gross_spread:.4f} | "
            f"{r.q1_q5:.4f} | {r.turnover:.3f} | {r.n_star} | {r.power:.3f}{pw_nw} | "
            f"{r.power_half:.3f} |")
    return "\n".join(lines) + "\n\n"


def _flag_lines(scenarios):
    out = []
    for label, res in scenarios:
        for cid in ("C1", "C2", "C3", "C4", "C5"):
            r = res[cid]
            if r.sign_flag:
                out.append(f"> **FLAG (§4.2 sign discrepancy) — {label}/{cid}:** primary mean IC "
                           f"{r.mean_ic:+.4f} vs imputed {r.mean_ic_imputed:+.4f} — sign differs; "
                           "surfaced to the operator, not dropped.")
    return ("\n".join(out) + "\n\n") if out else "_No §4.2 sign discrepancies in this run._\n\n"


def _r1_section(scan):
    """Render the R1 real dev-window classification (Prompt 1-B items 5/6 + D5)."""
    h = ["## R1 — §11.3 data-integrity classification (REAL dev window)\n"]
    h.append("Gate-(b)'s five-bucket classifier (`audit_corporate_actions.py:279-296`), "
             "reused via `classify_move`, run on the real dev-fenced adjusted panel exactly "
             "as `load_panel` builds it (rn=1 dedup, ever-member, ≤ 2022-12-31). The scan "
             "reads prices but computes **no candidate score** (Prompt 1-B).\n")
    h.append(f"Screened >|20%| moves: **{scan.n_moves}**. Bucket counts:\n")
    h.append("| Bucket | Count | Residue? |")
    h.append("|---|--:|:--:|")
    for b in ("CA-explained", "genuine", "magnitude-mismatch", "direction-mismatch",
              "CA-shaped-orphan"):
        h.append(f"| {b} | {scan.counts.get(b, 0)} | {'**yes**' if b in H.RESIDUE else 'no'} |")
    h.append("")
    n_doc = sum(1 for r in scan.residue_rows if r[4])
    h.append(f"**Residue: {len(scan.residue_rows)}** ({n_doc} documented in "
             f"`ca_scope_exclusions`, {len(scan.undocumented)} undocumented). The full "
             "residue register (documented + undocumented) is the **D5 missing-input set** "
             f"({len(scan.register)} rows); the §11.3 **HALT** set is the "
             f"{len(scan.undocumented)} undocumented rows only.\n")
    h.append("| Entity | Move date | Adjusted move | Class | Disposition |")
    h.append("|---|---|--:|---|---|")
    for e, d, r, cls, doc in sorted(scan.residue_rows, key=lambda x: x[2]):
        disp = "documented (still a missing input, D5.1)" if doc else "**UNDOCUMENTED — HALTs (§11.3)**"
        h.append(f"| {e} | {d} | {r:+.1%} | {cls} | {disp} |")
    h.append("")
    h.append("> **§11.3 status (Prompt 1-B item 6, reported not acted on):** a correct R1 "
             f"**HALTs** on the {len(scan.undocumented)} undocumented residue rows above. Their "
             "disposition is governed by operator decision **D5** (unadjusted CA = missing "
             "input); the register is threaded into scoring (D5.2-7) and exercised by "
             "`tests/psb1/test_scoring.py`.\n")
    if scan.large_genuine:
        h.append("**Honest disclosure (Prompt 1-B item 6) — large moves gate-(b) classifies "
                 "`genuine`, therefore NOT in the register and NOT excluded by D5:**\n")
        h.append("Gate-(b)'s CA-ratio test is strict (±`CA_RATIO_TOLERANCE`=0.02) and disabled "
                 "below Rs 5 (the tick-grid floor). Several very large negative adjusted moves "
                 "fall just outside the canonical-ratio band or have a backward-adjusted "
                 "`prev_close` < Rs 5, so gate-(b) classes them `genuine`. They remain in the "
                 "scored panel. This is gate-(b)'s pinned classification (§9); flagged for the "
                 "operator, **not** silently reclassified.\n")
        h.append("| Entity | Move date | Adjusted move | Surviving ratio |")
        h.append("|---|---|--:|--:|")
        for e, d, r, sv in sorted(scan.large_genuine, key=lambda x: x[2])[:20]:
            h.append(f"| {e} | {d} | {r:+.1%} | {sv:.4f} |")
        h.append("")
    return "\n".join(h) + "\n"


def _canonical(res_null, res_rev, res_del, checks, fenced, unfenced, rows,
               nstar_w, nstar_m, scan, commit):
    """The report MINUS the self-referential S1 determinism line (compared across processes)."""
    h = []
    h.append("# PSB-1 Phase 1 — Screening Harness Report (synthetic dev-proof + real R1)\n")
    h.append(f"**Script-generated** (protocol §10). Code commit at generation `{commit}` — "
             "when the report is committed together with the code this is the **parent** of "
             "the commit that adds this file (Lead Review D3); re-run post-commit to stamp the "
             f"exact commit. Seed `{SEED}` (§10).\n")
    h.append("Candidate scores are proved on **synthetic data only**. The real store is read "
             "only for: the P7 fence-check and real n* (dates/counts), and the R1 §11.3 scan "
             "(adjusted prices, **not** a candidate score — Prompt 1-B).\n")
    h.append(f"**Real-store stamp (D3/S3):** rows **{rows:,}**, unfenced "
             f"`MAX(trade_date)={unfenced}`, loader fenced observed max `{fenced}` "
             f"(≤ {H.DEV_HI}). 3.5y of sealed data is physically present and excluded.\n")
    h.append(f"**Real n\\* (R2, real `trading_calendar`, dates only):** weekly **{nstar_w}**, "
             f"monthly **{nstar_m}** in [2023-01-01, 2026-06-30]. (The per-candidate n\\* in "
             "the tables below is the *synthetic* calendar's count — a synthetic artifact.)\n")
    h.append(f"Synthetic panels: {N_NAMES} names x {N_WEEKS} weekly grids "
             f"({DAYS_PER_WEEK} trading days/week), scenarios null / reversal / delivery, "
             "each in its own DuckDB under `data/psb1_synthetic/` (gitignored).\n")

    h.append("## Falsifiable predictions\n")
    h.append("| Prediction | Evidence | Result |")
    h.append("|---|---|---|")
    for name, ev, ok in checks:
        h.append(f"| {name} | {ev} | {'PASS' if ok else 'FAIL'} |")
    h.append("")

    h.append(_r1_section(scan))

    h.append("## §4.2 sign-discrepancy flags (D2)\n")
    h.append(_flag_lines([("reversal", res_rev), ("delivery", res_del), ("null", res_null)]))

    h.append("## Harness output by scenario\n")
    h.append("Net spread is an **upper bound on realizable economics** (same-close "
             "formation, no execution lag — §6/F5). Three distinct counters (D5.8): `skip` "
             "= <5-scored-name dates (I2); `fwd_miss` = §4.2 missing-forward; `ca_excl` = D5 "
             "CA-register forward exclusions. All 0 on the synthetic panels (no CAs planted); "
             "the D5 register path is exercised in `tests/psb1/test_scoring.py`.\n")
    h.append(_cand_table("Scenario: reversal (C1/C4 signal + planted delistings)", res_rev))
    h.append(_cand_table("Scenario: delivery (C3 signal)", res_del))
    h.append(_cand_table("Scenario: null", res_null))
    return "\n".join(h)


def _compute():
    rng_null = np.random.default_rng(SEED)
    rng_rev = np.random.default_rng(SEED + 1)
    rng_del = np.random.default_rng(SEED + 2)
    p_null = build_panel(SYNTH_DIR / "null.duckdb", "null", rng_null)
    p_rev = build_panel(SYNTH_DIR / "reversal.duckdb", "reversal", rng_rev)
    p_del = build_panel(SYNTH_DIR / "delivery.duckdb", "delivery", rng_del)
    res_null, res_rev, res_del = _run_all(p_null), _run_all(p_rev), _run_all(p_del)
    fenced, unfenced, rows = H.fence_check(db_path=REAL_STORE, cutoff=H.DEV_HI)
    nstar_w = H.sealed_grid_count(str(REAL_STORE), "weekly")
    nstar_m = H.sealed_grid_count(str(REAL_STORE), "monthly")
    scan = _r1_real()
    checks = _predictions(res_null, res_rev, res_del, fenced, unfenced, rows)
    canonical = _canonical(res_null, res_rev, res_del, checks, fenced, unfenced, rows,
                           nstar_w, nstar_m, scan, _git_commit())
    return canonical, checks, scan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-out", default=None)
    args = ap.parse_args()

    SYNTH_DIR.mkdir(parents=True, exist_ok=True)

    if args.canonical_out:                                  # S1 worker: emit canonical bytes, exit
        canonical, _, _ = _compute()
        Path(args.canonical_out).write_text(canonical, encoding="utf-8")
        return 0

    # S1: two separate interpreters with differing PYTHONHASHSEED, whole-file byte compare
    tmp = Path(tempfile.mkdtemp(prefix="psb1_s1_"))
    outs = []
    for seed in ("0", "1"):
        out = tmp / f"canon_{seed}.md"
        env = dict(os.environ, PYTHONHASHSEED=seed)
        subprocess.run([sys.executable, str(Path(__file__)), "--canonical-out", str(out)],
                       check=True, env=env, cwd=str(ROOT))
        outs.append(out.read_bytes())
    s1_ok = outs[0] == outs[1]
    ha, hb = hashlib.sha256(outs[0]).hexdigest(), hashlib.sha256(outs[1]).hexdigest()

    canonical, checks, scan = _compute()
    s1_line = (f"| S1/P6 determinism (two interpreters, PYTHONHASHSEED 0 vs 1, whole-file "
               f"bytes) | sha256 seed0={ha[:16]} seed1={hb[:16]} | {'PASS' if s1_ok else 'FAIL'} |")
    # splice the S1 line into the predictions table (after the header separator row)
    lines = canonical.split("\n")
    idx = next(i for i, ln in enumerate(lines) if ln.startswith("|---|---|---|"))
    lines.insert(idx + 1, s1_line)
    report = "\n".join(lines)
    REPORT.write_text(report, encoding="utf-8")

    all_ok = all(ok for _, _, ok in checks) and s1_ok
    print(f"\n{'ALL PREDICTIONS PASS (P1-P7, P4b, S1)' if all_ok else 'FAILURE — see report'}"
          f"  ->  {REPORT}")
    print(f"S1 cross-process byte-identical: {s1_ok}")
    print(f"R1 real dev-window: {scan.n_moves} moves screened, "
          f"{len(scan.residue_rows)} residue ({len(scan.undocumented)} undocumented -> would HALT), "
          f"{len(scan.large_genuine)} large genuine (not in register)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
