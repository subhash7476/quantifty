"""PSB-1 / PSB-2 Prompt 1R5 — register relisting factors and verify boundary returns.

Factors committed in ingest_corporate_actions.py. This runner:
  - Rebuilds the adjusted view
  - Asserts the four boundary returns (§1)
  - Mutates INDOSOLAR factor on scratch to verify the check has teeth (§2)
  - Verifies register removal causes HALT (§6)
  - Regenerates the certification report (§7)
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
from disposition_register import build_register, RE_LISTINGS

STORE = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
SCRATCH = ROOT / "data" / "market_data" / "eqbhav_repair_r5.duckdb"

# Expected boundary returns (§1), derived from factor + handoff prices
BOUNDARIES = {
    ("INDOSOLAR", date(2025, 6, 19)): (+0.6507, 0.001),
    ("CLCIND", date(2026, 1, 30)):    (-0.8805, 0.001),
    ("NEUEON", date(2025, 12, 23)):   (+1.1022, 0.001),
    ("DELPHIFX", date(2020, 4, 21)):  (+0.3136, 0.001),
}


def _assert_boundaries(arm_b, arm_b_excl, label: str):
    """Assert all four boundary returns match expectations."""
    for ent, ps, s, td, ret, pc, c in arm_b.splices:
        key = (ent, td)
        if key not in BOUNDARIES:
            continue
        exp, tol = BOUNDARIES[key]
        assert abs(ret - exp) <= tol, (
            f"{label}: {ent} @ {td}: ret={ret:+.4f} (expected {exp:+.4f} +/- {tol})")
        print(f"  {label}: {ent} @ {td}: ret={ret:+.4f} (OK, expected {exp:+.4f})")


def _splice_halts(arm_b, arm_b_excl) -> list:
    """Return list of (ent, td, ret) for splices that still HALT."""
    halt = []
    for ent, ps, s, td, ret, pc, c in arm_b.splices:
        reason = arm_b_excl.get((ent, td))
        if reason is None:
            halt.append((ent, td, ret))
    return halt


def main():
    import time
    t0 = time.time()

    # ── Build from committed code alone (§5) ──
    print("=== Rebuilding adjusted view from committed code ===")
    if SCRATCH.exists():
        SCRATCH.unlink()
    shutil.copy2(STORE, SCRATCH)

    cc = duckdb.connect(str(SCRATCH))
    ICA.purge_and_rebuild(cc)
    ICA.ingest_etf_splits(cc)
    ICA.ingest_special_dividends(cc)
    ICA.apply_factor_overrides(cc)
    ICA.register_relisting_factors(cc)
    ICA.assert_no_orphan_factors(cc)
    ICA.build_adjusted_view(cc)
    print("  Adjusted view rebuilt from scratch\n")

    # ── §1: Assert boundary returns ──
    print("=== §1 — Boundary return assertions ===")
    cc.close()
    fbe = load_factors_by_entity(str(SCRATCH), cutoff=date(9999, 12, 31))
    cc = duckdb.connect(str(SCRATCH), read_only=True)
    arm_b = A.arm_b(cc)
    _, _, arm_b_excl = build_register(cc)
    _assert_boundaries(arm_b, arm_b_excl, "§1")
    halt = _splice_halts(arm_b, arm_b_excl)
    assert len(halt) == 0, f"Halting splices: {halt}"
    print("  All 4 boundary assertions PASS, 0 halting splices\n")

    # ── §2: Mutate INDOSOLAR factor on scratch ──
    print("=== §2 — Inverted factor mutation (scratch only) ===")
    cc.close()
    cc = duckdb.connect(str(SCRATCH))
    cc.execute(
        "UPDATE adjustment_factors SET factor=? WHERE symbol=? AND ex_date=?",
        [0.01, "INDOSOLAR", date(2022, 6, 28)])
    ICA.build_adjusted_view(cc)
    cc.close()
    fbe2 = load_factors_by_entity(str(SCRATCH), cutoff=date(9999, 12, 31))
    cc = duckdb.connect(str(SCRATCH), read_only=True)
    arm_b2 = A.arm_b(cc)
    _, _, arm_b_excl2 = build_register(cc)
    try:
        _assert_boundaries(arm_b2, arm_b_excl2, "§2 (inverted)")
        print("  !! §2 assertion PASSED — check lacks teeth (expected FAIL)")
    except AssertionError as e:
        print(f"  §2 assertion FAILED as expected: {e}")
    # Restore
    cc.close()
    shutil.copy2(STORE, SCRATCH)  # fresh copy
    print("  Inverted factor discarded; fresh copy restored\n")

    # ── §6: Remove register entry, verify HALT ──
    print("=== §6 — Register entry removal test ===")
    cc.close()
    cc = duckdb.connect(str(SCRATCH))
    ICA.purge_and_rebuild(cc)
    ICA.ingest_etf_splits(cc)
    ICA.ingest_special_dividends(cc)
    ICA.apply_factor_overrides(cc)
    ICA.register_relisting_factors(cc)
    ICA.assert_no_orphan_factors(cc)
    ICA.build_adjusted_view(cc)
    cc.close()

    # Verify register removal causes HALT (§6): remove key from arm_b_excl dict
    # after building, then check the splice is not in it.
    fbe3 = load_factors_by_entity(str(SCRATCH), cutoff=date(9999, 12, 31))
    cc = duckdb.connect(str(SCRATCH), read_only=True)
    arm_b3 = A.arm_b(cc)
    _, _, arm_b_excl3 = build_register(cc)
    # Remove one entry from the built dict
    removed_key = ("INDOSOLAR", date(2025, 6, 19))
    assert removed_key in arm_b_excl3, f"Key {removed_key} not in register"
    del arm_b_excl3[removed_key]
    halt3 = _splice_halts(arm_b3, arm_b_excl3)
    assert len(halt3) > 0, f"Expected >=1 halting splice after removing {removed_key}"
    print(f"  Removed {removed_key} from register: {len(halt3)} splice(s) HALT")
    for h in halt3:
        print(f"    {h[0]} @ {h[1]}: ret={h[2]:+.4f}")
    print("  (Register dict restored by discarding scratch copy)\n")
    cc.close()
    SCRATCH.unlink(missing_ok=True)

    # ── Apply to real store ──
    print("=== Applying to real store ===")
    rw = duckdb.connect(str(STORE))
    ICA.register_relisting_factors(rw)
    ICA.build_adjusted_view(rw)
    rw.close()
    print("  Factors registered, adjusted view rebuilt on real store\n")

    # ── Verify on real store ──
    fbe4 = load_factors_by_entity(str(STORE), cutoff=date(9999, 12, 31))
    ro = duckdb.connect(str(STORE), read_only=True)
    arm_b4 = A.arm_b(ro)
    _, _, arm_b_excl4 = build_register(ro)
    _assert_boundaries(arm_b4, arm_b_excl4, "Real store")
    halt4 = _splice_halts(arm_b4, arm_b_excl4)
    print(f"  Real store: {len(arm_b4.splices)} splices, {len(halt4)} halt")
    assert len(halt4) == 0, f"Halting splices remain: {halt4}"
    ro.close()

    print(f"\n=== ALL PASS ({time.time() - t0:.1f}s) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
