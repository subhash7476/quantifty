"""PSB-1 Prompt 3-B — prev_close series-crossing fix validation.

Rebuilds ONLY build_adjusted_view() (the prev_close expression) and verifies the five
Review-6 predictions on a COPY, then applies to the real store if clean.

Usage:
    python scripts/psb1/repair_prev_close.py            # validate on copy, then apply
    python scripts/psb1/repair_prev_close.py --dry-run   # copy only
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "csmp"))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))

import ingest_corporate_actions      # noqa: E402 — build_adjusted_view()
import screening_harness as H        # noqa: E402
from screening_harness import load_factors_by_entity, load_ca_scope_exclusions  # noqa: E402
from repair_entity_intervals import prev_close_violations, membership_snapshot  # noqa: E402

STORE = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
SCRATCH = Path(r"C:\Users\devou\AppData\Local\Temp\opencode") / "psb1_prompt3b_copy.duckdb"


def prev_close_col_violations(con):
    """VIEW-INDUCED violations in the prev_close COLUMN (Review 6): entity grain, EQ+BE union,
    adj_gap vs raw_gap where adj_gap = adj_prev_close(t)/adj_close(prev entity session)."""
    return con.execute("""
        WITH a AS (
            SELECT i.entity, ad.symbol, ad.series, ad.trade_date, ad.prev_close apc,
                   LAG(ad.close) OVER (PARTITION BY i.entity ORDER BY ad.trade_date, ad.symbol) alag
            FROM equity_bhavcopy_adjusted ad
            JOIN symbol_entity_intervals i ON i.symbol=ad.symbol
                 AND ad.trade_date>=i.valid_from AND ad.trade_date<i.valid_to),
        r AS (
            SELECT i.entity, rb.symbol, rb.series, rb.trade_date, rb.prev_close rpc,
                   LAG(rb.close) OVER (PARTITION BY i.entity ORDER BY rb.trade_date, rb.symbol) rlag
            FROM equity_bhavcopy rb
            JOIN symbol_entity_intervals i ON i.symbol=rb.symbol
                 AND rb.trade_date>=i.valid_from AND rb.trade_date<i.valid_to
            WHERE rb.series IN ('EQ','BE'))
        SELECT a.symbol, a.trade_date, a.apc/a.alag adj_gap, r.rpc/r.rlag raw_gap
        FROM a JOIN r USING (symbol, series, trade_date)
        WHERE a.alag>0 AND r.rlag>0 AND r.rpc>0
          AND ABS(a.apc/a.alag - r.rpc/r.rlag) > 1e-6
        ORDER BY ABS(a.apc/a.alag - r.rpc/r.rlag) DESC
    """).fetchall()


def r1_scan(db):
    panel = H.load_panel(db_path=str(db), cutoff=H.DEV_HI)
    return H.scan_data_integrity(panel, load_factors_by_entity(str(db), H.DEV_HI),
                                 load_ca_scope_exclusions(str(db), H.DEV_HI))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ro = duckdb.connect(str(STORE), read_only=True)
    col_before = prev_close_col_violations(ro)
    adjclose_before = prev_close_violations(ro)          # the consumed-series invariant
    rows_before = ro.execute("SELECT COUNT(*) FROM equity_bhavcopy_adjusted").fetchone()[0]
    memb_before = membership_snapshot(ro)
    vertoz_before = ro.execute("SELECT prev_close FROM equity_bhavcopy_adjusted "
                               "WHERE symbol='VERTOZ' AND trade_date='2025-07-14'").fetchone()
    ro.close()
    scan_before = r1_scan(STORE)
    print(f"BEFORE: prev_close-column violations={len(col_before)}, adj_close violations={len(adjclose_before)}, "
          f"rows={rows_before}, VERTOZ 07-14 prev_close={vertoz_before[0] if vertoz_before else None}")
    print(f"BEFORE R1: {scan_before.n_moves}/{len(scan_before.residue_rows)}/"
          f"{len(scan_before.undocumented)}/{len(scan_before.large_genuine)}")

    SCRATCH.parent.mkdir(parents=True, exist_ok=True)
    if SCRATCH.exists():
        SCRATCH.unlink()
    shutil.copy2(STORE, SCRATCH)
    cc = duckdb.connect(str(SCRATCH))
    ingest_corporate_actions.build_adjusted_view(cc)     # rebuild view ONLY
    cc.close()

    ro2 = duckdb.connect(str(SCRATCH), read_only=True)
    col_after = prev_close_col_violations(ro2)
    adjclose_after = prev_close_violations(ro2)
    rows_after = ro2.execute("SELECT COUNT(*) FROM equity_bhavcopy_adjusted").fetchone()[0]
    memb_after = membership_snapshot(ro2)
    vertoz_after = ro2.execute("SELECT prev_close FROM equity_bhavcopy_adjusted "
                               "WHERE symbol='VERTOZ' AND trade_date='2025-07-14'").fetchone()
    vertoz_bench = ro2.execute("SELECT close FROM equity_bhavcopy_adjusted "
                               "WHERE symbol='VERTOZ' AND trade_date='2025-07-11'").fetchone()
    ro2.close()
    scan_after = r1_scan(SCRATCH)

    p1 = len(col_after) == 0
    p2 = vertoz_after and vertoz_bench and abs(vertoz_after[0] - vertoz_bench[0]) < 0.01
    p3 = rows_after == rows_before == 7030920 and len(adjclose_after) == 0
    p4 = (scan_after.n_moves == scan_before.n_moves
          and len(scan_after.residue_rows) == len(scan_before.residue_rows)
          and len(scan_after.undocumented) == len(scan_before.undocumented)
          and len(scan_after.large_genuine) == len(scan_before.large_genuine))
    p5 = memb_after == memb_before

    print("\n=== PREDICTIONS (validated on copy) ===")
    print(f"P1 prev_close-column violations {len(col_before)} -> {len(col_after)} (expect 0): "
          f"{'PASS' if p1 else 'FAIL'}")
    print(f"P2 VERTOZ 2025-07-14 prev_close={vertoz_after[0] if vertoz_after else None} "
          f"(expect {vertoz_bench[0] if vertoz_bench else None} = adj_close 07-11): {'PASS' if p2 else 'FAIL'}")
    print(f"P3 rows {rows_before}->{rows_after} & adj_close violations {len(adjclose_before)}->"
          f"{len(adjclose_after)}: {'PASS' if p3 else 'FAIL'}")
    print(f"P4 R1 {scan_before.n_moves}/{len(scan_before.residue_rows)}/{len(scan_before.undocumented)}/"
          f"{len(scan_before.large_genuine)} -> {scan_after.n_moves}/{len(scan_after.residue_rows)}/"
          f"{len(scan_after.undocumented)}/{len(scan_after.large_genuine)}: {'PASS' if p4 else 'FAIL'}")
    print(f"P5 membership {len(memb_before)}->{len(memb_after)} identical: {'PASS' if p5 else 'FAIL'}")
    if col_after:
        print(f"\nprev_close-column violations remaining ({len(col_after)}), enumerated:")
        for s, d, ag, rg in col_after[:50]:
            print(f"  {s:12s} {d} adj_gap={ag:.4f} raw_gap={rg:.4f}")

    all_pass = p1 and p2 and p3 and p4 and p5
    print(f"\n{'ALL P1-P5 PASS on copy' if all_pass else 'PREDICTION FAILURE — STOP'}")

    if all_pass and not args.dry_run:
        rw = duckdb.connect(str(STORE))
        ingest_corporate_actions.build_adjusted_view(rw)
        rw.close()
        print(f"\nAPPLIED to real store {STORE}.")
    elif args.dry_run:
        print("\n--dry-run: real store NOT modified.")
    else:
        print("\nReal store NOT modified (prediction failure).")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
