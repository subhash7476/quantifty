"""PSB-1 / PSB-2 Prompt 1R4 8D — Register relisting factors.

Registers INDOSOLAR factor 100 @ 2022-06-28 and SPENTEX factor 100 @ 2024-01-12,
then rebuilds the adjusted view and re-runs the four-arm certification.

Copy-first pattern: validate on a scratch copy before applying to the real store.
NTL gets no factor (FV-only change, count unchanged).
"""

from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "csmp"))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))

import ingest_corporate_actions as ICA
import contract_arms as A
from screening_harness import load_factors_by_entity
from disposition_register import build_register

STORE = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
SCRATCH = ROOT / "data" / "market_data" / "eqbhav_repair_relisting.duckdb"
DEV_HI = date(2022, 12, 31)

# Factors to register (operator-confirmed, NSE/NCLT verified)
FACTORS = [
    # INDOSOLAR 1:100 entitlement for existing public holders; promoter base extinguished
    ("INDOSOLAR", date(2022, 6, 28), 100.0, "SPLIT", "nclt_order_2022_06_28_1to100"),
    # SPENTEX 1:100 ledger conversion (NSE/CML/72500); count: 519,748 shares
    ("SPENTEX", date(2024, 1, 12), 100.0, "SPLIT", "nse_cml_72500_2024_01_12_1to100"),
]


def _check_current_state(con) -> dict:
    """Capture current state for before/after comparison."""
    # Get current arm_b splices
    fbe = load_factors_by_entity(str(STORE), cutoff=date(9999, 12, 31))
    arm_b = A.arm_b(con)
    _, _, arm_b_excl = build_register(con)

    b_residue = []
    for ent, ps, s, td, ret, pc, c in arm_b.splices:
        reason = arm_b_excl.get((ent, td))
        b_residue.append((ent, td, ret, reason))

    return {
        "n_splices": len(arm_b.splices),
        "splices": b_residue,
        "n_halt_before": len([r for r in b_residue if r[3] is None]),
    }


def _predict_current_factors(con) -> list:
    """Check if factors already exist."""
    existing = {}
    for sym, ex, _, _, src in FACTORS:
        r = con.execute(
            "SELECT factor, source FROM adjustment_factors WHERE symbol=? AND ex_date=?",
            [sym, ex]).fetchone()
        existing[(sym, ex)] = r
    return existing


def main():
    import time
    t0 = time.time()

    # Read-only check of current state
    ro = duckdb.connect(str(STORE), read_only=True)
    state_before = _check_current_state(ro)
    existing_factors = _predict_current_factors(ro)
    ro.close()

    print(f"Current state: {state_before['n_splices']} splices, "
          f"{state_before['n_halt_before']} halt")

    for (sym, ex, _, _, src) in FACTORS:
        was = existing_factors.get((sym, ex))
        print(f"  {sym} @ {ex}: {'exists: factor=' + str(was[0]) if was else 'MISSING'}")

    # Press predictions
    predictions = [
        ("P1", "INDOSOLAR factor registered", not existing_factors.get(("INDOSOLAR", date(2022, 6, 28)))),
        ("P2", "SPENTEX factor registered", not existing_factors.get(("SPENTEX", date(2024, 1, 12)))),
        ("P3", "NTL has no factor (FV-only)", True),  # verified by not in FACTORS list
    ]
    for pid, desc, ok in predictions:
        print(f"  Prediction {pid}: {desc} — {'PASS' if ok else 'FAIL (unexpected)'}")

    if not all(p[2] for p in predictions):
        print("Predictions not met — stopping.")
        return 1

    # Copy store
    print(f"\nCopying store to scratch...")
    if SCRATCH.exists():
        SCRATCH.unlink()
    shutil.copy2(STORE, SCRATCH)

    # Apply on copy
    cc = duckdb.connect(str(SCRATCH))
    print(f"Registering {len(FACTORS)} factors...")
    for sym, ex, factor, atype, src in FACTORS:
        cc.execute(
            "INSERT OR REPLACE INTO adjustment_factors "
            "VALUES (?, ?, ?, ?, ?)",
            [sym, ex, factor, atype, src])
        print(f"  Registered {sym}: {factor}x {atype} @ {ex} ({src})")

    # Check for orphans
    try:
        ICA.assert_no_orphan_factors(cc)
        print("  No orphan factors: PASS")
    except AssertionError as e:
        print(f"  ORPHAN FACTORS: {e}")
        cc.close()
        SCRATCH.unlink(missing_ok=True)
        return 1

    # Rebuild adjusted view
    print("Rebuilding adjusted view...")
    ICA.build_adjusted_view(cc)
    print("  Adjusted view rebuilt")

    # Re-run arms (close cc first to avoid connection conflicts)
    cc.close()
    fbe = load_factors_by_entity(str(SCRATCH), cutoff=date(9999, 12, 31))
    cc = duckdb.connect(str(SCRATCH), read_only=True)
    arm_a = A.arm_a(cc, fbe)
    arm_b = A.arm_b(cc)
    arm_c = A.arm_c(cc, fbe)
    arm_d = A.arm_d(cc)

    arm_a_excl, arm_d_excl, arm_b_excl = build_register(cc)

    # Check predictions
    print("\n--- Predictions ---")
    # P4: INDOSOLAR boundary return (173.32 / (1.05 * 100)) = +65.1%
    # Need to find WAAREEINDO -> INDOSOLAR splice
    new_halt = []
    for ent, ps, s, td, ret, pc, c in arm_b.splices:
        reason = arm_b_excl.get((ent, td))
        if reason is None:
            new_halt.append((ent, td, ret))

    p4_ok = len(new_halt) == 0  # all 4 should be dispositioned
    p5_ok = len(arm_a.violations) == 0 or len([v for v in arm_a.violations
                                               if (v[0], v[2]) not in arm_a_excl]) == 0

    preds = [
        ("P4", "All splices dispositioned (0 halt)", p4_ok),
        ("P5", "Arm A clean (0 undocumented)", p5_ok),
        ("P6", "Arm C clean (0 violations)", len(arm_c.violations) == 0),
        ("P7", "Arm D clean (0 undocumented)",
         len([v for v in arm_d.violations if (v[0], v[1]) not in arm_d_excl]) == 0),
    ]
    all_pass = True
    for pid, desc, ok in preds:
        print(f"  {pid}: {desc} — {'PASS' if ok else 'FAIL'}")
        if not ok:
            all_pass = False

    if all_pass:
        print("\nALL PREDICTIONS PASS on scratch copy.")
        print(f"New halting splices: {len(new_halt)} (expect 0)")
        if new_halt:
            for ent, td, ret in new_halt:
                print(f"  {ent} @ {td}: {ret:+.1%}")

        # Apply to real store
        rw = duckdb.connect(str(STORE))
        for sym, ex, factor, atype, src in FACTORS:
            rw.execute("INSERT OR REPLACE INTO adjustment_factors "
                       "VALUES (?, ?, ?, ?, ?)", [sym, ex, factor, atype, src])
        ICA.build_adjusted_view(rw)
        rw.close()
        print("\nApplied to real store.")
    else:
        print("\nPREDICTIONS FAILED — not applying to real store.")
        print(f"Halting splices remain: {len(new_halt)}")

    cc.close()
    SCRATCH.unlink(missing_ok=True)
    print(f"Total: {time.time() - t0:.1f}s")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
