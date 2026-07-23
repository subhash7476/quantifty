"""Carry substrate certification runner.

Builds the basis panel, runs the four arms + PIT guard, and generates a
script-generated report with zero hand-edited numbers.

Usage:
    python scripts/signal_engine/carry/certify_substrate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))

import contract_arms as A          # noqa: E402
from disposition_register import build_register, disposition_for  # noqa: E402

FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "CARRY_SUBSTRATE_CERTIFICATION.md"


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def main():
    commit = _git_commit()
    con = duckdb.connect()
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute("SET threads=4")

    print("Building basis panel...")
    n_cells = A.build_basis_panel(con)

    # Substrate stats
    stats = con.execute("""
        SELECT
            COUNT(*) AS total_cells,
            COUNT(CASE WHEN spot_close IS NOT NULL THEN 1 END) AS joined_cells,
            COUNT(CASE WHEN entity IS NOT NULL THEN 1 END) AS entity_resolved,
            COUNT(DISTINCT underlying) AS n_underlyings,
            MIN(trade_date) AS min_date,
            MAX(trade_date) AS max_date,
            AVG(CASE WHEN annualized_basis IS NOT NULL THEN annualized_basis END) AS mean_ann_basis,
            MEDIAN(CASE WHEN annualized_basis IS NOT NULL THEN annualized_basis END) AS median_ann_basis
        FROM basis_panel
    """).fetchone()

    join_pct = (stats[2] / stats[0] * 100) if stats[0] > 0 else 0
    entity_pct = (stats[2] / stats[0] * 100) if stats[0] > 0 else 0

    print(f"  {stats[0]:,} basis cells, {stats[3]} underlyings, {stats[4]} -> {stats[5]}")
    print(f"  Spot join: {stats[1]:,}/{stats[0]:,} ({join_pct:.2f}%)")
    print(f"  Entity resolved: {stats[2]:,}/{stats[0]:,} ({entity_pct:.2f}%)")

    print("Running arms...")
    arm_a = A.arm_a(con)
    arm_b = A.arm_b(con)
    arm_c = A.arm_c(con)
    arm_d = A.arm_d(con)
    pit = A.pit_guard(con)
    reg = build_register()

    con.close()

    # ── Apply disposition register ──
    _, _, arm_c_excl, _ = reg

    # Arm A: disposition roll jumps using crisis periods
    arm_a_residue = []
    for row in arm_a.roll_jumps:
        u, d = row[1], row[2]  # roll date is the 3rd element
        reason = disposition_for(u, d)
        arm_a_residue.append((*row, reason))
    arm_a_undoc = [r for r in arm_a_residue if r[-1] is None]

    # Arm C split violations
    arm_c_split_residue = []
    for row in arm_c.split_violations:
        sym, ex = row[0], row[1]
        reason = arm_c_excl.get((sym, ex))
        arm_c_split_residue.append((*row, reason))
    arm_c_split_undoc = [r for r in arm_c_split_residue if r[-1] is None]

    # Arm C dividend residuals
    arm_c_div_residue = []
    for row in arm_c.dividend_residuals:
        sym, ex = row[0], row[1]
        reason = disposition_for(sym, ex)
        arm_c_div_residue.append((*row, reason))
    arm_c_div_undoc = [r for r in arm_c_div_residue if r[-1] is None]

    # Arm D: disposition each extreme cell individually
    arm_d_residue = []
    for row in arm_d.extreme_cells:
        u, d = row[0], row[1]
        reason = disposition_for(u, d)
        arm_d_residue.append((*row, reason))
    arm_d_undoc = [r for r in arm_d_residue if r[-1] is None]

    # ── Build report ──
    w = []
    W = w.append

    W("# Carry Substrate Certification Report\n")
    W(f"**Script-generated** — `scripts/signal_engine/carry/certify_substrate.py`. "
      f"Code commit `{commit}`.\n")
    W("Read-only over both stores. No signal, IC, or return computed. "
      "Certifies the futures + spot substrate can produce an honest basis.\n")
    W("**RULE 1 — RAW spot:** basis uses `equity_bhavcopy` (series='EQ'), NOT "
      "`equity_bhavcopy_adjusted`. The basis is a same-session ratio (F−S)/S; a back-adjusted "
      "spot leg is scaled by future CA factors the raw futures price does not carry, which "
      "fabricates a basis on every name with any later corporate action.\n")
    W(f"**RULE 2 — PIT F&O eligibility** from the feed itself: a name is F&O-listed on date d "
      f"IFF it has a FUTSTK record on d. `fo_eligible_intervals` is unusable (10-month "
      f"coverage only).\n")

    # ── Falsifiable predictions (stated BEFORE results) ──
    W("## Falsifiable predictions (stated before the run)\n")
    W("1. Cross-sectional `resid_carry` is near-symmetric around zero each day (the demean "
      "forces this); tails bounded by the Arm D cap. Systematic skew or one-sided fat tails "
      "on specific dates flags one-sided CA adjustment.")
    W("2. Basis does **not** jump discontinuously on futures **roll dates** (a jump ⇒ the "
      "roll leaked a price level).")
    W("3a. Basis does **not** jump on **ex-SPLIT / ex-BONUS** dates (the ratio cancels in "
      "(F−S)/S).")
    W("3b. On **ex-DIVIDEND** dates the basis **does** step up by ~D/(S·τ) — that is clean "
      "data, not a defect. The prediction is that the **residual** after removing that "
      "predicted step is within tolerance.\n")

    # ── Bounds ──
    W("## Pre-set bounds\n")
    W(f"| Bound | Value | Justification |")
    W(f"|---|---|---|")
    W(f"| Roll raw basis tolerance (Arm A) | ±{A.ROLL_RAW_TOL:.0%} raw ratio | Both contracts on "
      f"same underlying at roll; raw (F−S)/S should be continuous; annualized is misleading "
      f"because the two contracts have different DTE |")
    W(f"| CA raw basis tolerance (Arm C) | ±{A.CA_RAW_TOL:.0%} raw ratio | After subtracting "
      f"predicted raw change (D/S for dividends, 0 for splits); Indian SSF futures are efficient "
      f"and adjust by ~D on ex-date |")
    W(f"| Raw ratio bound (Arm D tier 1) | ±{A.RAW_RATIO_BOUND:.0%} | Beyond ±5% raw premium is "
      f"almost certainly a data defect or genuine crisis — dispositioned either way |")
    W(f"| Annualized bound (Arm D tier 2) | ±{A.BASIS_FABRICATION_BOUND:.0%} annualized, "
      f"DTE ≥ {A.MIN_DTE_FOR_ANNUALIZED_FLAG} | Catches persistent extreme carry that isn't a "
      f"near-expiry annualization artifact |\n")

    # ── Substrate summary ──
    W("## Substrate summary\n")
    W(f"| Quantity | Value |")
    W(f"|---|---|")
    W(f"| Basis cells | {stats[0]:,} |")
    W(f"| Underlyings | {stats[3]} |")
    W(f"| Date range | {stats[4]} → {stats[5]} |")
    W(f"| Spot join | {stats[1]:,} / {stats[0]:,} ({join_pct:.2f}%) |")
    W(f"| Entity resolved | {stats[2]:,} / {stats[0]:,} ({entity_pct:.2f}%) |")
    W(f"| Mean annualized basis | {stats[6]:.6f} |")
    W(f"| Median annualized basis | {stats[7]:.6f} |")
    W("")

    # ── Arm summary table ──
    all_ok = True
    W("## Certification summary\n")
    W("| Arm | Result | Detail |")
    W("|---|:--:|---|")

    a_ok = arm_a.gaps == 0 and arm_a.overlaps == 0 and len(arm_a_undoc) == 0
    W(f"| **Arm A** contract & roll | {'PASS' if a_ok else '**FLAG**'} | "
      f"gaps={arm_a.gaps}, overlaps={arm_a.overlaps}, roll jumps={len(arm_a.roll_jumps)} "
      f"({len(arm_a.roll_jumps) - len(arm_a_undoc)} dispositioned, **{len(arm_a_undoc)}** undocumented) |")
    if not a_ok:
        all_ok = False

    b_ok = len(arm_b.unresolved_symbols) == 0 and len(arm_b.multi_entity) == 0 and arm_b.spot_missing == 0
    W(f"| **Arm B** entity alignment | {'PASS' if b_ok else '**FLAG**'} | "
      f"unresolved={len(arm_b.unresolved_symbols)}, multi-entity={len(arm_b.multi_entity)}, "
      f"spot missing={arm_b.spot_missing:,} |")
    if not b_ok:
        all_ok = False

    c_split_ok = len(arm_c_split_undoc) == 0
    c_div_ok = len(arm_c_div_undoc) == 0
    c_ok = c_split_ok and c_div_ok
    W(f"| **Arm C** CA consistency | {'PASS' if c_ok else '**FLAG**'} | "
      f"split violations={len(arm_c.split_violations)} ({len(arm_c.split_violations) - len(arm_c_split_undoc)} "
      f"dispositioned, **{len(arm_c_split_undoc)}** undocumented), "
      f"dividend discontinuities={len(arm_c.dividend_residuals)} "
      f"({len(arm_c.dividend_residuals) - len(arm_c_div_undoc)} dispositioned, "
      f"**{len(arm_c_div_undoc)}** undocumented) |")
    if not c_ok:
        all_ok = False

    d_ok = len(arm_d_undoc) == 0
    W(f"| **Arm D** basis fabrication | {'PASS' if d_ok else '**FLAG**'} | "
      f"extreme={len(arm_d.extreme_cells)} ({len(arm_d.extreme_cells) - len(arm_d_undoc)} "
      f"dispositioned, **{len(arm_d_undoc)}** undocumented), stale={arm_d.stale_cells:,} |")
    if not d_ok:
        all_ok = False

    pit_ok = pit.non_pit_cells == 0
    W(f"| **PIT guard** F&O eligibility | {'PASS' if pit_ok else '**FAIL**'} | "
      f"{pit.total_cells:,} cells, {pit.non_pit_cells} non-PIT (structural by construction) |")
    if not pit_ok:
        all_ok = False
    W("")

    # ── Arm A detail ──
    W("## Arm A — Contract identity & roll integrity\n")
    W(f"- Gaps (name-dates in FUTSTK with no near-month selection): **{arm_a.gaps}**")
    W(f"- Overlaps (name-dates with >1 selected contract): **{arm_a.overlaps}**")
    W(f"- Roll discontinuities (raw basis jump > {A.ROLL_RAW_TOL:.0%} at roll): "
      f"**{len(arm_a.roll_jumps)}**\n")
    if arm_a.roll_jumps:
        W("| Underlying | Prev date | Roll date | Prev raw | New raw | Change | Disposition |")
        W("|---|---|---|---:|---:|---:|---|")
        for u, ptd, td, pb, nb, chg, reason in sorted(arm_a_residue, key=lambda x: (x[-1] is None, -x[5]))[:20]:
            tag = reason or "**HALT**"
            W(f"| {u} | {ptd} | {td} | {pb:.6f} | {nb:.6f} | {chg:.6f} | {tag} |")
        if len(arm_a.roll_jumps) > 20:
            W(f"\n*... {len(arm_a.roll_jumps) - 20} more*")
        W("")

    # ── Arm B detail ──
    W("## Arm B — Two-leg entity alignment\n")
    if arm_b.unresolved_symbols:
        W(f"**{len(arm_b.unresolved_symbols)} underlyings** not in `symbol_entity_intervals`:\n")
        for (sym,) in arm_b.unresolved_symbols:
            W(f"- {sym}")
        W("")
    else:
        W("All FUTSTK underlyings resolve to an entity. ")

    if arm_b.multi_entity:
        W(f"\n**{len(arm_b.multi_entity)} cells** with multiple entity assignments (co-trading):\n")
        for u, td, n in arm_b.multi_entity[:10]:
            W(f"- {u} on {td}: {n} entities")
    else:
        W("No co-trading entities. ")

    if arm_b.spot_missing > 0:
        W(f"\n\n**{arm_b.spot_missing:,} cells** with no EQ spot leg (futures trade_date "
          "with no matching equity EQ close). These are suppressed in basis computation.\n")
    else:
        W("All cells have an EQ spot leg.\n")

    # ── Arm C detail ──
    W("## Arm C — Corporate-action consistency\n")
    W("### Splits / bonuses (Prediction 3a)\n")
    W("The ratio *k* cancels in (F−S)/S: S→S/k and F→F/k, so the raw basis ratio is "
      "invariant. A jump > 3% in raw_basis_ratio at a split/bonus ex-date flags one-sided "
      f"adjustment.\n")
    if arm_c.split_violations:
        n_disp = len(arm_c.split_violations) - len(arm_c_split_undoc)
        W(f"**{len(arm_c.split_violations)} violations** "
          f"({n_disp} dispositioned, **{len(arm_c_split_undoc)}** undocumented"
          f"{' — HALT' if arm_c_split_undoc else ''}):\n")
        W("| Symbol | Ex-date | Prev raw | New raw | Change | Disposition |")
        W("|---|---|---:|---:|---:|---|")
        for sym, ex, pr, nr, chg, reason in sorted(arm_c_split_residue, key=lambda x: (x[-1] is None, -x[4])):
            tag = reason or "**HALT**"
            W(f"| {sym} | {ex} | {pr:.6f} | {nr:.6f} | {chg:.6f} | {tag} |")
        W("")
    else:
        W("**0 violations.** Basis is continuous across all split/bonus ex-dates.\n")

    W("### Dividends (Prediction 3b)\n")
    W("On ex-dividend dates, both legs adjust by ~D in the efficient Indian SSF market, "
      "so the raw basis is roughly continuous (same as splits). The test flags any raw "
      f"discontinuity > {A.CA_RAW_TOL:.0%} — a jump means one leg didn't adjust.\n")
    if arm_c.dividend_residuals:
        n_disp = len(arm_c.dividend_residuals) - len(arm_c_div_undoc)
        W(f"**{len(arm_c.dividend_residuals)} discontinuities** beyond tolerance "
          f"({n_disp} dispositioned, **{len(arm_c_div_undoc)}** undocumented"
          f"{' — HALT' if arm_c_div_undoc else ''}):\n")
        W("| Symbol | Ex-date | Div amt | Actual raw Δ | Disposition |")
        W("|---|---|---:|---:|---|")
        for sym, ex, damt, act, reason in sorted(arm_c_div_residue, key=lambda x: (x[-1] is None, -abs(x[3]))):
            tag = reason or "**HALT**"
            W(f"| {sym} | {ex} | {damt:.2f} | {act:.6f} | {tag} |")
        W("")
    else:
        W("**0 residuals** beyond tolerance. All dividend ex-dates show the predicted step.\n")

    W("### Dividend PIT-ness limitation\n")
    W(f"{arm_c.pit_limitation}\n")

    # ── Arm D detail ──
    W("## Arm D — Basis fabrication invariant\n")
    W(f"Two-tier: |raw ratio| > {A.RAW_RATIO_BOUND:.0%} OR (|annualized| > {A.BASIS_FABRICATION_BOUND:.0%} "
      f"AND DTE ≥ {A.MIN_DTE_FOR_ANNUALIZED_FLAG}). "
      f"Stale cells (NULL leg): **{arm_d.stale_cells:,}**.\n")
    if arm_d.extreme_cells:
        n_disp = len(arm_d.extreme_cells) - len(arm_d_undoc)
        W(f"**{len(arm_d.extreme_cells)} cells** flagged "
          f"({n_disp} dispositioned, **{len(arm_d_undoc)}** undocumented"
          f"{' — HALT' if arm_d_undoc else ''}).\n")
        W("| Underlying | Date | Ann. basis | Raw ratio | DTE | F close | S close | Disposition |")
        W("|---|---|---:|---:|---:|---:|---:|---|")
        for u, d, ab, rr, dte, fc, sc, reason in arm_d_residue[:30]:
            tag = reason or "**HALT**"
            W(f"| {u} | {d} | {ab:.4f} | {rr:.6f} | {dte} | {fc:.2f} | {sc:.2f} | {tag} |")
        if len(arm_d.extreme_cells) > 30:
            W(f"\n*... {len(arm_d.extreme_cells) - 30} more*")
        W("")
    else:
        W("**0 cells** flagged. All basis values within the bound.\n")

    # ── PIT guard detail ──
    W("## PIT universe guard\n")
    W(f"F&O eligibility is PIT by construction (RULE 2): every cell in the basis panel has a "
      f"FUTSTK record on its trade_date. **{pit.total_cells:,}** cells, "
      f"**{pit.non_pit_cells}** non-PIT.\n")

    # ── Prediction outcomes ──
    W("## Prediction outcomes\n")
    W("| # | Prediction | Result |")
    W("|---|---|:--:|")
    W(f"| 1 | Cross-sectional basis near-symmetric (mean ≈ median) | "
      f"{'PASS' if abs(stats[6] - stats[7]) < 0.05 else '**CHECK**'} "
      f"(mean={stats[6]:.4f}, median={stats[7]:.4f}) |")
    W(f"| 2 | No roll discontinuities | "
      f"{'PASS' if len(arm_a_undoc) == 0 else '**FLAG**'} "
      f"({len(arm_a.roll_jumps)} jumps, {len(arm_a_undoc)} undocumented) |")
    W(f"| 3a | Basis continuous at split/bonus dates | "
      f"{'PASS' if len(arm_c_split_undoc) == 0 else '**FLAG**'} "
      f"({len(arm_c.split_violations)} violations, {len(arm_c_split_undoc)} undocumented) |")
    W(f"| 3b | Dividend basis continuous | "
      f"{'PASS' if len(arm_c_div_undoc) == 0 else '**FLAG**'} "
      f"({len(arm_c.dividend_residuals)} discontinuities, {len(arm_c_div_undoc)} undocumented) |")
    W("")

    # ── Final status ──
    if all_ok:
        status = ("**SUBSTRATE CERTIFIED — the four-arm contract holds.** "
                  "The Carry TRAIN read (pre-reg §9 gate 2) is authorized.")
    else:
        status = ("**CERTIFICATION INCOMPLETE — flagged items above must be resolved "
                  "(disposition or repair) before the TRAIN read.**")
    W(f"\n{status}\n")

    report = "\n".join(w) + "\n"
    REPORT.write_text(report, encoding="utf-8")
    print(f"\nReport: {REPORT}")
    print(status)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
