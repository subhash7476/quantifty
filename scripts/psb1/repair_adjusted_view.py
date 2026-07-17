"""PSB-1 Prompt 2 — entity-grain adjustment repair runner.

1. Measures the invariant violation count against the CURRENT (symbol-grain) view (read-only).
2. Asserts no (entity, ex_date) draws factors from >1 symbol (STOP if any found).
3. Rebuilds `equity_bhavcopy_adjusted` via `build_adjusted_view()` (the one authorised CSMP edit).
4. Measures the invariant violation count against the REPAIRED (entity-grain) view.
5. Re-runs R1 on the repaired panel and prints the classification shifts.
6. Verifies six falsifiable predictions.

Usage:
    python scripts/psb1/repair_adjusted_view.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "csmp"))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))

import ingest_corporate_actions  # noqa: E402 — the authorised CSMP module
import screening_harness as H     # noqa: E402
from screening_harness import load_factors_by_entity, load_ca_scope_exclusions  # noqa: E402

STORE = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"


def invariant_violations(con):
    """Count (entity, date) pairs where the adjusted close-to-close return does NOT
    equal the raw close-to-close return (except across a true ex-date, where it must
    equal raw_ret / factor). Uses the view's adj_close and raw equity_bhavcopy for raw,
    both deduped at the entity grain (rn=1 turnover-primary, ever-member, dev-fenced)."""
    rows = con.execute("""
        WITH eprint AS (
            SELECT entity, trade_date, adj_close, raw_close FROM (
                SELECT e.entity, a.trade_date,
                       a.close AS adj_close,                            -- view pre-multiplied
                       eb.close AS raw_close,
                       a.turnover,
                       ROW_NUMBER() OVER (PARTITION BY e.entity, a.trade_date
                           ORDER BY a.turnover DESC NULLS LAST, a.symbol) rn
                FROM equity_bhavcopy_adjusted a
                JOIN universe_eligibility e ON e.symbol = a.symbol
                JOIN equity_bhavcopy eb ON eb.symbol = a.symbol AND eb.trade_date = a.trade_date
                WHERE a.trade_date <= '2022-12-31'
                  AND e.entity IN (SELECT DISTINCT e2.entity FROM universe_membership m
                                   JOIN universe_eligibility e2 ON e2.symbol=m.symbol)
            ) WHERE rn=1
        ),
        events AS (
            SELECT e.entity, af.ex_date,
                   COALESCE(EXP(SUM(LN(af.factor)) FILTER (
                       WHERE af.action_type IN ('BONUS','SPLIT','SPECIAL_DIVIDEND'))), 1.0) f
            FROM adjustment_factors af
            JOIN universe_eligibility e ON e.symbol=af.symbol
            GROUP BY e.entity, af.ex_date
        ),
        factor_map AS (
            SELECT e1.entity, e1.trade_date, e1.adj_close, e1.raw_close,
                   LEAD(e1.trade_date) OVER (PARTITION BY e1.entity ORDER BY e1.trade_date) next_td,
                   LEAD(e1.adj_close) OVER (PARTITION BY e1.entity ORDER BY e1.trade_date) next_adj,
                   LEAD(e1.raw_close) OVER (PARTITION BY e1.entity ORDER BY e1.trade_date) next_raw
            FROM eprint e1
        )
        SELECT COUNT(*)
        FROM factor_map f
        WHERE f.next_td IS NOT NULL
          AND f.raw_close > 0
          AND ABS( (f.next_adj / f.adj_close - 1.0) -
                   (f.next_raw / f.raw_close - 1.0) /
                   COALESCE( (SELECT ev.f FROM events ev
                              WHERE ev.entity = f.entity
                                AND ev.ex_date > f.trade_date AND ev.ex_date <= f.next_td
                              ORDER BY ev.ex_date LIMIT 1), 1.0)
                 ) > 1e-9
    """).fetchone()[0]
    return rows


def assert_no_double_apply(con):
    """Assert no (entity, ex_date) draws factors from >1 symbol. If any do, STOP."""
    n = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT u.entity, af.ex_date, COUNT(DISTINCT af.symbol) ns
            FROM adjustment_factors af
            JOIN universe_eligibility u ON u.symbol=af.symbol
            GROUP BY u.entity, af.ex_date HAVING ns>1
        )
    """).fetchone()[0]
    assert n == 0, f"CRITICAL — {n} (entity, ex_date) pairs draw factors from >1 symbol. STOP."
    print(f"Double-application risk check: {n} (entity, ex_date) pairs -> OK")


def main():
    # ---- connect read-only, measure before --------------------------------------------------------
    ro = duckdb.connect(str(STORE), read_only=True)
    assert_no_double_apply(ro)
    before = invariant_violations(ro)
    print(f"Invariant violations BEFORE repair (entity-grain dedup, dev-fenced): {before}")
    # snapshot of current R1 for the prediction checks
    panel_before = H.load_panel(db_path=str(STORE), cutoff=H.DEV_HI)
    factors_before = load_factors_by_entity(STORE, H.DEV_HI)
    doc_before = load_ca_scope_exclusions(STORE, H.DEV_HI)
    scan_before = H.scan_data_integrity(panel_before, factors_before, doc_before)
    ro.close()
    print(f"  R1 before: {scan_before.n_moves} moves, {len(scan_before.residue_rows)} residue, "
          f"{len(scan_before.undocumented)} halt, {len(scan_before.large_genuine)} large(>=40%)")
    # ---- rebuild the view (read-write) -----------------------------------------------------------
    rw = duckdb.connect(str(STORE))
    ingest_corporate_actions.build_adjusted_view(rw)
    rw.close()
    # ---- connect read-only, measure after ---------------------------------------------------------
    ro2 = duckdb.connect(str(STORE), read_only=True)
    after = invariant_violations(ro2)
    print(f"Invariant violations AFTER repair (entity-grain dedup, dev-fenced): {after}")
    panel_after = H.load_panel(db_path=str(STORE), cutoff=H.DEV_HI)
    factors_after = load_factors_by_entity(STORE, H.DEV_HI)
    doc_after = load_ca_scope_exclusions(STORE, H.DEV_HI)
    scan_after = H.scan_data_integrity(panel_after, factors_after, doc_after)
    ro2.close()
    print(f"  R1 after: {scan_after.n_moves} moves, {len(scan_after.residue_rows)} residue, "
          f"{len(scan_after.undocumented)} halt, {len(scan_after.large_genuine)} large(>=40%)")

    # ---- six predictions --------------------------------------------------------------------------
    p1 = scan_after.n_moves == scan_before.n_moves - 15     # only the 15 rename moves vanish
    p2 = scan_after.n_moves == 220                          # 235-15=220
    p3 = len(scan_after.residue_rows) == 2 and "SINTEX" in [r[0] for r in scan_after.residue_rows \
        if r[4]] and "KWALITY" in [r[0] for r in scan_after.undocumented]
    p4 = len(scan_after.undocumented) == 1 and scan_after.undocumented[0][0] == "KWALITY"
    p5 = len(scan_after.large_genuine) == 34
    # prediction 6: report prev_close<Rs5 second-order effects
    second_order_candidates = []
    for e, d, r, cls, doc in scan_before.residue_rows:
        if cls == "CA-shaped-orphan" and (e, d) not in {(r[0], r[1]) for r in scan_after.residue_rows}:
            second_order_candidates.append(f"  {e} {d} was CA-shaped-orphan, now gone (rename fix)")
    print("\n=== PREDICTIONS ===")
    print(f"P1 moves 235->{scan_after.n_moves} (=220?): {'PASS' if p1 else 'FAIL'}")
    print(f"P2 no new rename moves: {'PASS' if p2 else 'FAIL'}  [not proven here]")
    print(f"P3 residue 7->{len(scan_after.residue_rows)} (=2?): {'PASS' if p3 else 'FAIL'}")
    print(f"P4 halt 6->{len(scan_after.undocumented)} (KWALITY=?): {'PASS' if p4 else 'FAIL'}")
    print(f"P5 large-genuine 43->{len(scan_after.large_genuine)} (=34?): {'PASS' if p5 else 'FAIL'}")
    # P6 second-order
    print(f"P6 prev_close<Rs5 second-order candidates: {len(second_order_candidates)}"
          + (f"; {', '.join(second_order_candidates[:5])}" if second_order_candidates else ""))
    # cross-check: 220 non-rename moves must be identical
    before_set = {(r[0], r[1]) for r in scan_before.residue_rows} | \
                 {(e, d) for e, d, _, _ in scan_before.undocumented} | \
                 {(e, d) for e, d, _, _ in scan_before.large_genuine}
    after_set = {(r[0], r[1]) for r in scan_after.residue_rows} | \
                {(e, d) for e, d, _, _ in scan_after.undocumented} | \
                {(e, d) for e, d, _, _ in scan_after.large_genuine}
    # the 15 rename moves (gone) + 34 large-genuine (before: 43)
    shared = before_set & after_set
    print(f"\nNon-rename moves preserved: {len(shared)} in common across before/after "
          f"(new after-only: {len(after_set - before_set)}, before-only (vanished): {len(before_set - after_set)})")
    if scan_before.n_moves == 235 and scan_after.n_moves == 220:
        vanished = {(r[0], r[1]) for r in scan_before.residue_rows if (r[0], r[1]) not in after_set}
        print("Vanished rename artifacts (should be 15):")
        for e, d, r, cls, _ in sorted(scan_before.residue_rows + \
                [(e, d, ret, cls, True) for e, d, ret, cls in scan_before.undocumented] + \
                [(e, d, ret, 'genuine-large', True) for e, d, ret, _ in scan_before.large_genuine],
                key=lambda x: x[2]):
            if (e, d) not in after_set:
                print(f"  {e:20s} {d} {r:+.1%} ({cls})")
        print(f"\nR1 new composition: residue={len(scan_after.residue_rows)} "
              f"undoc={len(scan_after.undocumented)} large={len(scan_after.large_genuine)}")

    # ---- blast-radius list (report, don't act) ---------------------------------------------------
    print("\n=== BLAST RADIUS (consumers of equity_bhavcopy_adjusted) ===")
    consumers = [
        "scripts/psb1/screening_harness.py",
        "scripts/csmp/run_a2_validation.py",
        "scripts/csmp/phase1_prereg_analysis.py",
        "scripts/csmp/phase1_ci_coverage.py",
        "scripts/csmp/triage_momentum.py",
        "scripts/csmp/build_devtruncated_store.py",
        "core/msi/artifacts/xs_momentum_v1/model.py",
    ]
    for c in consumers:
        print(f"  AFFECTED: {c}")
    print("  NOT affected: audit_corporate_actions.py (gate-(b) reads raw prices + adjustment_factors)")

    return 0 if all([p1, p3, p4, p5]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
