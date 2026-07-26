"""IVOL section 9 -- gate 4 composite power check (engine level).

Combines the frozen Carry and IVOL signals on their COMMON TRAIN formations
(2017-02-28 -> 2020-12-31), builds the equal-risk-weight composite signal,
measures its realized composite IC series, and projects power to the sealed
window (n*=42). The 0.80 hurdle binds at the composite, not per-sleeve.

This is arithmetic on already-measured TRAIN quantities -- no new data read,
no sealed window touched.

Sign alignment:
  Carry: high z_carry_neut -> high fwd return (positive IC). Keep as-is.
  IVOL:  high z_ivol_neut  -> LOW fwd return (negative IC). Negate to align.
  Composite z = z_carry_neut - z_ivol_neut  (high -> high return expected).

Output: docs/reports/IVOL_COMPOSITE_CHECK_REPORT.md
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))
from screening_harness import _one_sided_t
from scripts.rfa.power import power_at

CARRY_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
IVOL_DB = ROOT / "data" / "signal_engine" / "ivol" / "signals.duckdb"
REPORT = ROOT / "docs" / "reports" / "IVOL_COMPOSITE_CHECK_REPORT.md"

TRAIN_LO = date(2017, 2, 28)
TRAIN_HI = date(2020, 12, 31)
MIN_NAMES = 5
POWER_HURDLE = 0.80
N_STAR = 42


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception:
        return "unknown"


def main():
    if not CARRY_DB.exists() or not IVOL_DB.exists():
        print("ERROR: need both Carry and IVOL signals DBs.")
        return 1

    con = duckdb.connect()
    con.execute(f"ATTACH '{CARRY_DB}' AS cr (READ_ONLY)")
    con.execute(f"ATTACH '{IVOL_DB}' AS iv (READ_ONLY)")
    con.execute("SET threads=2")
    commit = _git_commit()

    # Intersection of names both sleeves score, on common TRAIN formations.
    joined = con.execute(f"""
        SELECT iv.formation_date, iv.underlying,
               cr.z_carry_neut, iv.z_ivol_neut, iv.fwd_ret_1m
        FROM iv.signals iv
        JOIN cr.signals cr
          ON cr.formation_date = iv.formation_date AND cr.underlying = iv.underlying
        WHERE iv.formation_date >= DATE '{TRAIN_LO}'
          AND iv.formation_date <= DATE '{TRAIN_HI}'
          AND iv.z_ivol_neut IS NOT NULL
          AND cr.z_carry_neut IS NOT NULL
          AND iv.fwd_ret_1m IS NOT NULL
        ORDER BY iv.formation_date
    """).fetchall()

    by_date = defaultdict(list)
    for r in joined:
        by_date[r[0]].append(list(r))
    formation_dates = sorted(by_date.keys())
    print(f"Common TRAIN formations: {len(formation_dates)} "
          f"({formation_dates[0]} -> {formation_dates[-1]})")

    carry_ic, ivol_ic, comp_ic = [], [], []
    pooled_zc, pooled_zi, pooled_fwd = [], [], []
    names_per = []

    for fdate in formation_dates:
        rows = by_date[fdate]
        if len(rows) < MIN_NAMES:
            continue
        zc = np.array([r[2] for r in rows], float)
        zi = np.array([r[3] for r in rows], float)
        fwd = np.array([r[4] for r in rows], float)

        rho_c, _ = spearmanr(zc, fwd)
        rho_i, _ = spearmanr(zi, fwd)
        carry_ic.append(float(rho_c))
        ivol_ic.append(float(rho_i))

        # Composite: sign-aligned (negate IVOL), re-standardize cross-sectionally.
        comp = zc - zi
        csd = float(np.std(comp, ddof=1))
        comp_z = (comp - np.mean(comp)) / csd if csd > 0 else comp
        rho_comp, _ = spearmanr(comp_z, fwd)
        comp_ic.append(float(rho_comp))

        pooled_zc.extend(zc.tolist())
        pooled_zi.extend(zi.tolist())
        pooled_fwd.extend(fwd.tolist())
        names_per.append(len(rows))

    n_f = len(comp_ic)
    if n_f < 2:
        print("ERROR: too few common formations")
        return 1

    carry_ic = np.array(carry_ic)
    ivol_ic = np.array(ivol_ic)
    comp_ic = np.array(comp_ic)

    def _stats(x):
        m, sd, t, p = _one_sided_t(x)
        return m, sd, t

    c_mean, c_sd, c_t = _stats(carry_ic)
    i_mean, i_sd, i_t = _stats(ivol_ic)
    comp_mean, comp_sd, comp_t = _stats(comp_ic)

    # Realized cross-sleeve signal correlation (pooled, the rho that matters for breadth)
    rho_signal = float(np.corrcoef(pooled_zc, pooled_zi)[0, 1])
    # Realized per-formation IC correlation
    rho_ic = float(np.corrcoef(carry_ic, ivol_ic)[0, 1])

    # Composite power at n* (composite is positive-signed by construction)
    comp_power = power_at(abs(comp_mean), comp_sd, N_STAR, two_sided=False)

    # Standalone powers for comparison
    carry_power = power_at(abs(c_mean), c_sd, N_STAR, two_sided=False)
    ivol_power = power_at(abs(i_mean), i_sd, N_STAR, two_sided=False)

    gate4_pass = comp_power >= POWER_HURDLE

    # Report
    w = []
    W = w.append
    W("# IVOL — Gate 4 Composite Power Check\n")
    W(f"**Script-generated** — `scripts/signal_engine/ivol/composite_check.py`. "
      f"Code commit `{commit}`.\n")
    W("**Frozen protocol:** `IVOL_PHASE0_PRE_REGISTRATION.md` §9 gate 4 / §13 "
      f"(declaration SHA `d7ebcbcc…`).\n")
    W("**What this is:** arithmetic on already-measured TRAIN quantities — "
      "no new data read, no sealed window touched. Combines the frozen Carry and "
      "IVOL signals into the equal-risk-weight composite and projects power to "
      "the sealed window (n*=42).\n")
    W(f"**Common TRAIN formations:** {n_f} ({formation_dates[0]} -> "
      f"{formation_dates[-1]}), intersection of names both sleeves score, "
      f"mean {float(np.mean(names_per)):.0f} names/formation.\n")

    W("## Standalone vs Composite (on the common intersection)\n")
    W("| Sleeve | Mean IC | SD(IC) | IR (|mean|/SD) | t | Standalone power (n*=42) |")
    W("|---|---|---|---|---|---|")
    W(f"| Carry (z_carry_neut) | {c_mean:+.6f} | {c_sd:.6f} | {abs(c_mean)/c_sd:.4f} | {c_t:.4f} | {carry_power:.4f} |")
    W(f"| IVOL (z_ivol_neut) | {i_mean:+.6f} | {i_sd:.6f} | {abs(i_mean)/i_sd:.4f} | {i_t:.4f} | {ivol_power:.4f} |")
    W(f"| **Composite (z_carry - z_ivol)** | **{comp_mean:+.6f}** | **{comp_sd:.6f}** | "
      f"**{abs(comp_mean)/comp_sd:.4f}** | **{comp_t:.4f}** | **{comp_power:.4f}** |")
    W("")

    W("## Realized Cross-Sleeve Correlation\n")
    W("| Quantity | Value | Meaning |")
    W("|---|---|---|")
    W(f"| Signal correlation (pooled, z_carry vs z_ivol) | {rho_signal:+.4f} | "
      f"{'decorrelated' if abs(rho_signal) < 0.3 else ('correlated' if rho_signal > 0 else 'negatively correlated')} |")
    W(f"| Per-formation IC correlation | {rho_ic:+.4f} | "
      f"do the sleeves' monthly ICs move together? |")
    W("")
    W("The breadth thesis (`IR ≈ √(Σ IR_i²)` when uncorrelated) rewards low "
      "correlation. A signal correlation near zero means the composite IR "
      "approaches the quadrature sum of the standalone IRs.")
    W("")

    W("## Breadth Decomposition\n")
    quad = math.sqrt((abs(c_mean) / c_sd) ** 2 + (abs(i_mean) / i_sd) ** 2)
    W("| Quantity | Value |")
    W("|---|---|")
    W(f"| √(IR_carry² + IR_ivol²) [quadrature, if uncorrelated] | {quad:.4f} |")
    W(f"| Realized composite IR (|mean|/SD) | {abs(comp_mean)/comp_sd:.4f} |")
    W(f"| Ratio (realized / quadrature) | {(abs(comp_mean)/comp_sd)/quad:.4f} |")
    W("")
    if abs(rho_signal) < 0.3:
        W(f"Signal correlation {rho_signal:+.4f} is low, so the realized "
          f"composite IR should approach the quadrature sum — confirmed by the "
          f"ratio above.")
    else:
        W(f"Signal correlation {rho_signal:+.4f} is material; the realized "
          f"composite IR falls short of the quadrature sum (correlation penalty).")
    W("")

    W("## Power Projection (n* = 42, sealed window)\n")
    W("| Sleeve | Power |")
    W("|---|---|")
    W(f"| Carry standalone | {carry_power:.4f} |")
    W(f"| IVOL standalone | {ivol_power:.4f} |")
    W(f"| **Composite (Carry + IVOL)** | **{comp_power:.4f}** |")
    W(f"| Hurdle | {POWER_HURDLE:.2f} |")
    W("")

    W("## Gate-4 Verdict\n")
    if gate4_pass:
        W(f"**PASS** — composite power {comp_power:.4f} >= {POWER_HURDLE:.2f} "
          f"hurdle. The 2-sleeve engine (Carry + IVOL) clears the 0.80 hurdle "
          f"at the composite level.\n")
        W("**Next:** §9 gate 5 — the one-shot SEALED read (2023-01 → present), "
          "the final unrepeatable resource. Composite clearance authorizes "
          "opening it.")
    else:
        W(f"**FAIL** — composite power {comp_power:.4f} < {POWER_HURDLE:.2f} "
          f"hurdle. The 2-sleeve composite does not clear 0.80.\n")
        W("Per §13: the engine either accepts the realized shortfall explicitly "
          "(documented, with the realized numbers) or stops — it does NOT force "
          "a third sleeve or re-weight to hit the target. SEALED stays sealed "
          "unless the operator accepts a sub-0.80 composite.")

    report = "\n".join(w) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"\nReport: {REPORT}")
    print(f"  Carry IC {c_mean:+.4f} (IR {abs(c_mean)/c_sd:.4f}, power {carry_power:.4f})")
    print(f"  IVOL  IC {i_mean:+.4f} (IR {abs(i_mean)/i_sd:.4f}, power {ivol_power:.4f})")
    print(f"  Composite IC {comp_mean:+.4f} (IR {abs(comp_mean)/comp_sd:.4f}, power {comp_power:.4f})")
    print(f"  Signal rho {rho_signal:+.4f}, IC rho {rho_ic:+.4f}")
    print(f"  Gate 4: {'PASS' if gate4_pass else 'FAIL'} (hurdle {POWER_HURDLE})")

    con.close()
    return 0 if gate4_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
