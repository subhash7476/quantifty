#!/usr/bin/env python3
"""C2 Phase 0.5 -- Turnover-Reduction Mini-Battery.

Runs 3 variants + reference on TRAIN (2011-2018), selects winner per S6,
confirms winner on HOLDOUT (2019-2022) per S7 G0.5.
"""

from __future__ import annotations

import datetime
import hashlib
import subprocess
import sys
import math
from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))
sys.path.insert(0, str(ROOT / "scripts" / "psb2"))

from scripts.psb2 import harness as H

STORE = str(ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb")
REPORT = ROOT / "docs" / "reports" / "C2_PHASE0_5_MINIBATTERY.md"

# Pinned split boundaries
TRAIN_HI = date(2018, 12, 31)
HOLDOUT_HI = date(2022, 12, 31)

# G0.5 thresholds (frozen S7)
POWER_HURDLE_G0 = 0.80
NET_SPREAD_FLOOR = 0.02  # 2%/yr
BONFERRONI_M = 3
ALPHA_G0 = 0.05


# -- Variant helpers -----------------------------------------------------

@dataclass
class VariantDef:
    vid: str
    cadence: str
    exit_band: float | None
    is_staggered: bool
    stag_tranches: int | None
    is_reference: bool = False


VARIANTS = [
    VariantDef("V1", "monthly", 0.40, False, None),
    VariantDef("V2", "fortnightly", 0.60, False, None),
    VariantDef("V3", "fortnightly", 0.40, True, 3),
    VariantDef("ref", "fortnightly", 0.40, False, None, is_reference=True),
]


def run_variant(
    panel: H.Panel,
    v: VariantDef,
    score_fn: Any,
    cutoff_hi: date,
):
    """Run a single variant on a panel fenced at cutoff_hi."""
    H.DEV_HI = cutoff_hi

    # Patch exit_band per variant
    orig_band = H.C2_EXIT_BAND
    if v.exit_band is not None:
        H.C2_EXIT_BAND = v.exit_band

    try:
        if v.vid == "V3":
            grid = H.fortnightly_grid(panel.cal)
            result = H.evaluate_candidate_psb2(
                panel, "C2", score_fn, STORE,
                fortnightly_grid_dates=grid,
                force_staggered=True,
                staggered_n_tranches=3,
            )
        elif v.cadence == "monthly":
            grid = H.monthly_grid(panel.cal)
            result = _run_variant_generic(panel, score_fn, grid, grid, 12, v, cutoff_hi)
        else:
            grid = H.fortnightly_grid(panel.cal)
            result = H.evaluate_candidate_psb2(
                panel, "C2", score_fn, STORE,
                fortnightly_grid_dates=grid,
            )
    finally:
        H.C2_EXIT_BAND = orig_band

    return result


def _run_variant_generic(panel, score_fn, grid, mg, ppy, v, cutoff_hi):
    """Generic evaluation loop for variants the CID-router doesn't handle."""
    dev_lo = date(2011, 1, 1)
    grid_next = {grid[i]: grid[i + 1] for i in range(len(grid) - 1)}
    formation_dates = [d for d in grid if dev_lo <= d <= cutoff_hi
                       and grid_next.get(d) is not None and grid_next[d] <= cutoff_hi]

    ic_list = []
    ic_imputed_list = []
    scored_by_date = []
    min_names_skipped = 0
    excl_counts = []
    fwd_missing_counts = []

    for t in formation_dates:
        tp = grid_next[t]
        if tp is None or tp > cutoff_hi:
            continue
        scores = score_fn(t)
        if not scores:
            min_names_skipped += 1
            continue
        members = H.members_at(panel, t)
        excl_counts.append(len(members) - len(scores))
        rows = []
        scores_list = []
        fwd_with_none = []
        for ent, score in scores.items():
            f = H._ret(panel, ent, t, tp)
            if f is not None:
                rows.append((ent, score, f))
                fwd_with_none.append(f)
            else:
                fwd_with_none.append(None)
        if len(rows) < H.MIN_NAMES:
            min_names_skipped += 1
            continue
        fwd_missing_counts.append(len(scores) - len(rows))
        date_ic_result = H.date_ic(
            np.array(list(scores.values())),
            np.array(fwd_with_none, dtype=object)
        )
        if date_ic_result[0] is not None:
            ic_list.append(date_ic_result[0])
            ic_imputed_list.append(date_ic_result[1])
        scored_by_date.append((t, rows))

    if len(ic_list) < 2:
        return H.CandidateResult(cid=v.vid, dates=formation_dates, n_dates=len(formation_dates))

    ic_arr = np.array(ic_list)
    mean_ic = float(np.mean(ic_arr))
    sd_ic = float(np.std(ic_arr, ddof=1)) if len(ic_arr) > 1 else 0.0
    _, _, t_stat, p_val = H._one_sided_t(ic_arr)
    ac1 = H._ac1(ic_arr)

    if v.is_staggered:
        
        topq_seq, base_seq = H._staggered_sequences(
            panel, scored_by_date, mg, H.monthly_grid(panel.cal),
            n_tranches=v.stag_tranches)
    else:
        topq_seq, _, base_seq = H._quintile_sequences_psb2(
            scored_by_date, banded=True, exit_band=v.exit_band)

    topq_net, topq_gross, _, topq_fees = H._simulate(topq_seq, ppy)
    base_net, base_gross, _, base_fees = H._simulate(base_seq, ppy)
    net_spread = topq_net - base_net
    gross_spread = topq_gross - base_gross
    fee_slip_drag_bp = (topq_gross - topq_net) * 10000.0

    turnovers = []
    for i in range(1, len(topq_seq)):
        prev_ents = {e for e, _ in topq_seq[i - 1][1]}
        curr_ents = {e for e, _ in topq_seq[i][1]}
        if len(curr_ents) > 0:
            churn = len(prev_ents ^ curr_ents) / (2.0 * len(curr_ents))
            turnovers.append(churn)
    turnover = float(np.mean(turnovers)) if turnovers else 0.0

    n_star = H.sealed_grid_count_psb2(STORE, v.cadence)
    power_d, power_half = H._power(mean_ic, sd_ic, n_star)

    ic_imputed_arr = np.array(ic_imputed_list) if ic_imputed_list else ic_arr
    mean_ic_imputed = float(np.mean(ic_imputed_arr))
    sign_flag = bool((mean_ic > 0) != (mean_ic_imputed > 0))
    n_half = len(ic_arr) // 2
    first_half_ic = float(np.mean(ic_arr[:n_half])) if n_half > 0 else mean_ic
    second_half_ic = float(np.mean(ic_arr[n_half:])) if len(ic_arr) > n_half else mean_ic

    return H.CandidateResult(
        cid=v.vid, dates=formation_dates, n_dates=len(formation_dates),
        ic=ic_arr, ic_imputed=ic_imputed_arr,
        mean_ic=mean_ic, sd_ic=sd_ic, tstat=t_stat, pvalue=p_val,
        ac1=ac1, nw_t=None,
        mean_ic_imputed=mean_ic_imputed, sign_flag=sign_flag,
        min_names_skipped=min_names_skipped,
        excl_counts=excl_counts, fwd_missing_counts=fwd_missing_counts,
        ca_excl_counts=[],
        net_spread=net_spread, gross_spread=gross_spread, q1_q5=0.0,
        fee_slip_drag_bp=fee_slip_drag_bp, turnover=turnover,
        fees_topq=topq_fees, fees_base=base_fees,
        first_half_ic=first_half_ic, second_half_ic=second_half_ic,
        n_star=n_star, power=power_d, power_half=power_half, power_nw=None,
    )


def build_scorer(panel):
    fg = H.fortnightly_grid(panel.cal)
    def fn(t):
        return H.score_c2_psb2(panel, t, fg=fg)
    return fn


def fence_check(panel, cutoff_hi, label):
    obs = panel.observed_max
    con = duckdb.connect(STORE, read_only=True)
    store_max = con.execute("SELECT MAX(trade_date) FROM equity_bhavcopy").fetchone()[0]
    con.close()
    print(f"  [{label}] Observed MAX: {obs}, cutoff: {cutoff_hi}, store MAX: {store_max}")
    assert obs <= cutoff_hi, f"FENCE FAIL [{label}]: {obs} > {cutoff_hi}"
    assert obs != store_max, f"FENCE FAIL [{label}]: observed ({obs}) == store MAX ({store_max})"
    return obs, store_max


def compute_digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    print("=" * 72)
    print("C2 Phase 0.5 -- Turnover-Reduction Mini-Battery")
    print("=" * 72)

    # -- Precondition: fidelity tests green ------------------------------
    print("\nFidelity precondition (score_c2_psb2 unchanged)...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "tests" / "psb2" / "test_fidelity.py"),
         "-q", "--tb=short"],
        capture_output=True, text=True, cwd=ROOT
    )
    fidelity_pass = result.returncode == 0
    print(f"  Fidelity tests: {'PASS' if fidelity_pass else 'FAIL'}")
    if not fidelity_pass:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(1)

    # -- PHASE A: TRAIN -------------------------------------------------
    print("\n" + "=" * 72)
    print("PHASE A: TRAIN (2011-01-01 -> 2018-12-31)")
    print("=" * 72)

    H.DEV_HI = TRAIN_HI
    H.C2_DEV_LO = date(2010, 1, 4)
    panel_train = H.load_panel(STORE, cutoff=TRAIN_HI)
    train_obs, _ = fence_check(panel_train, TRAIN_HI, "TRAIN")

    score_fn_train = build_scorer(panel_train)
    train_results = {}

    for v in VARIANTS:
        print(f"\n  Running {v.vid}...")
        if v.vid == "V3":
            # Patch for staggered with 3 tranches
            orig_c4 = H.C4_N_TRANCHES
            H.C4_N_TRANCHES = v.stag_tranches
        r = run_variant(panel_train, v, score_fn_train, TRAIN_HI)
        if v.vid == "V3":
            H.C4_N_TRANCHES = orig_c4
        train_results[v.vid] = r
        print(f"    n={r.n_dates}  IC={r.mean_ic:.6f}  SD={r.sd_ic:.6f}"
              f"  net={r.net_spread:.4%}  turn={r.turnover:.4f}"
              f"  power={r.power:.4f}")

    # S6 Selection: winner = highest TRAIN net spread among those with power >= 0.80
    eligible = [(v, train_results[v.vid])
                for v in VARIANTS if not v.is_reference]
    eligible_scored = [(v, r) for v, r in eligible
                       if r.n_dates >= 2 and r.power >= POWER_HURDLE_G0]

    if not eligible_scored:
        print("\n  NO WINNER: no variant clears TRAIN power >= 0.80")
        winner_v = None
        winner_r = None
    else:
        eligible_scored.sort(key=lambda x: x[1].net_spread, reverse=True)
        winner_v, winner_r = eligible_scored[0]
        print(f"\n  WINNER: {winner_v.vid}"
              f"  net={winner_r.net_spread:.4%}  power={winner_r.power:.4f}")

    # -- PHASE B: HOLDOUT -----------------------------------------------
    print("\n" + "=" * 72)
    print("PHASE B: HOLDOUT (2019-01-01 -> 2022-12-31)")
    print("=" * 72)

    H.DEV_HI = HOLDOUT_HI
    H.C2_DEV_LO = date(2010, 1, 4)
    panel_holdout = H.load_panel(STORE, cutoff=HOLDOUT_HI)
    hold_obs, _ = fence_check(panel_holdout, HOLDOUT_HI, "HOLDOUT")

    holdout_result = None
    g0_pass = False
    g0_detail = []

    if winner_v is not None:
        score_fn_hold = build_scorer(panel_holdout)
        print(f"\n  Running {winner_v.vid} on HOLDOUT...")
        if winner_v.vid == "V3":
            orig_c4 = H.C4_N_TRANCHES
            H.C4_N_TRANCHES = winner_v.stag_tranches
        holdout_result = run_variant(panel_holdout, winner_v, score_fn_hold, HOLDOUT_HI)
        if winner_v.vid == "V3":
            H.C4_N_TRANCHES = orig_c4

        r = holdout_result
        print(f"    n={r.n_dates}  IC={r.mean_ic:.6f}  SD={r.sd_ic:.6f}"
              f"  net={r.net_spread:.4%}  turn={r.turnover:.4f}"
              f"  power={r.power:.4f}")

        # G0.5 evaluation (S7)
        power_ok = r.power >= POWER_HURDLE_G0
        g0_detail.append(("Power (>= 0.80)", r.power, power_ok))

        spread_ok = r.net_spread >= NET_SPREAD_FLOOR
        g0_detail.append(("Net spread (>= 2.0%/yr)", r.net_spread, spread_ok))

        # Deflated p: use the one-sided p from the simple t-test
        raw_p = r.pvalue
        deflated_p = min(1.0, BONFERRONI_M * raw_p)
        p_ok = deflated_p < ALPHA_G0
        g0_detail.append((
            f"Deflated p (m={BONFERRONI_M}, < {ALPHA_G0})",
            f"{deflated_p:.6e} (raw p={raw_p:.6e})",
            p_ok
        ))

        ic_ok = r.mean_ic > 0
        g0_detail.append(("Mean IC (> 0)", r.mean_ic, ic_ok))

        g0_pass = all(item[2] for item in g0_detail)
        print(f"  G0.5: {'PASS' if g0_pass else 'FAIL'}")

    # -- Generate report ------------------------------------------------
    print("\n" + "=" * 72)
    print("Generating report")
    print("=" * 72)

    lines = []
    def emit(s=""):
        lines.append(s)

    emit("# C2 Phase 0.5 -- Turnover-Reduction Mini-Battery")
    emit()
    emit("## Fence Assertions")
    emit()
    emit("| Run | Observed MAX | Cutoff | Store MAX | Status |")
    emit("|---|---|---|---|---|")
    emit(f"| TRAIN | {train_obs} | {TRAIN_HI} | 2026-07-09 | "
         f"{'PASS' if train_obs != date(2026, 7, 9) else 'FAIL'} |")
    emit(f"| HOLDOUT | {hold_obs} | {HOLDOUT_HI} | 2026-07-09 | "
         f"{'PASS' if hold_obs != date(2026, 7, 9) else 'FAIL'} |")
    emit()

    emit("## Variant Slate (S4)")
    emit()
    emit("| ID | Cadence | Exit band | Hold | Mechanism |")
    emit("|---|---|---|---|---|")
    for v in VARIANTS:
        stag = f"staggered {v.stag_tranches}-period" if v.is_staggered else "single"
        note = "(reference, not counted)" if v.is_reference else ""
        emit(f"| {v.vid} | {v.cadence} | {v.exit_band or 'N/A'} | {stag} | {note} |")
    emit()

    emit("## Phase A: TRAIN Results (2011 -> 2018)")
    emit()
    emit("| ID | n | Mean IC | SD_IC | AC_1 | Net spread | Gross spread | "
         "Fee drag (bp) | Turnover | Power (n*) | Power >= 0.80? |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    for v in VARIANTS:
        r = train_results.get(v.vid)
        if r is None or r.n_dates < 2:
            emit(f"| {v.vid} | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |")
            continue
        power_ok = "YES" if r.power >= POWER_HURDLE_G0 else "no"
        emit(f"| {v.vid} | {r.n_dates} | {r.mean_ic:.6f} | {r.sd_ic:.6f} | "
             f"{r.ac1:.4f} | {r.net_spread:.4%} | {r.gross_spread:.4%} | "
             f"{r.fee_slip_drag_bp:.1f} | {r.turnover:.4f} | "
             f"{r.power:.4f} (n*={r.n_star}) | {power_ok} |")
    emit()

    emit("### Selection (S6)")
    emit()
    if eligible_scored:
        emit(f"**Winner: {winner_v.vid}** -- highest TRAIN net spread "
             f"({winner_r.net_spread:.4%}) among variants with TRAIN power "
             f"(P{winner_r.power:.4f}) >= 0.80.")
    else:
        emit("**No winner:** no variant cleared TRAIN power >= 0.80.")
        emit(f"\nCandidates with power >= 0.80:")
        for v, r in eligible:
            emit(f"- {v.vid}: net={r.net_spread:.4%}, power={r.power:.4f}")
    emit()

    emit("## Phase B: HOLDOUT Confirmation (2019 -> 2022)")
    emit()
    if holdout_result is not None:
        r = holdout_result
        emit(f"**Confirmed variant:** {winner_v.vid}")
        emit()
        emit("| Metric | Value |")
        emit("|---|---|")
        emit(f"| n (formations) | {r.n_dates} |")
        emit(f"| Mean IC | {r.mean_ic:.6f} |")
        emit(f"| SD_IC | {r.sd_ic:.6f} |")
        emit(f"| AC_1 | {r.ac1:.6f} |")
        emit(f"| Net spread (ann.) | {r.net_spread:.4%} |")
        emit(f"| Gross spread (ann.) | {r.gross_spread:.4%} |")
        emit(f"| Fee+slippage drag (bp/yr) | {r.fee_slip_drag_bp:.1f} |")
        emit(f"| Turnover | {r.turnover:.4f} |")
        emit(f"| Power (n*={r.n_star}) | {r.power:.4f} |")

        emit()
        emit("### Gate G0.5 (S7)")
        emit()
        emit("| Criterion | Threshold | Value | Verdict |")
        emit("|---|---|---|---|")
        for name, val, ok in g0_detail:
            vstr = f"{val:.4f}" if isinstance(val, float) else str(val)
            emit(f"| {name} | -- | {vstr} | {'**PASS**' if ok else 'FAIL'} |")
        emit()
        emit(f"**G0.5 overall: {'PASS' if g0_pass else 'FAIL'}**")
        if g0_pass:
            emit(f"\nThe winner **{winner_v.vid}** clears all thresholds. "
                 f"It earns the sealed read and proceeds to Phase 1 (C2-VAL) "
                 f"pre-registration.")
        else:
            emit(f"\nG0.5 FAIL. Terminal for this round -- no re-roll.")
    else:
        emit("No variant advanced to HOLDOUT confirmation.")
    emit()

    # Digest
    emit("---")
    content_lines = list(lines)
    report_content = "\n".join(content_lines)
    digest = compute_digest(report_content)
    emit(f"**SHA-256:** `{digest}`")
    emit(f"**Generated (outside seal):** "
         f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"  Report: {REPORT}")
    print(f"  Digest: {digest}")

    # -- Summary ---------------------------------------------------------
    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for v in VARIANTS:
        r = train_results.get(v.vid)
        if r and r.n_dates >= 2:
            print(f"  TRAIN {v.vid}: n={r.n_dates}  IC={r.mean_ic:.6f}  "
                  f"SD={r.sd_ic:.6f}  net={r.net_spread:.4%}  "
                  f"turn={r.turnover:.4f}  power={r.power:.4f}")
    if holdout_result:
        r = holdout_result
        print(f"  HOLDOUT {winner_v.vid}: n={r.n_dates}  IC={r.mean_ic:.6f}  "
              f"SD={r.sd_ic:.6f}  net={r.net_spread:.4%}  "
              f"turn={r.turnover:.4f}  power={r.power:.4f}")
        print(f"  G0.5: {'PASS' if g0_pass else 'FAIL'}")
    print("=" * 72)

    return 0 if (holdout_result is not None and g0_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
