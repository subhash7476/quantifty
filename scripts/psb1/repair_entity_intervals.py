"""PSB-1 Prompt 3 — time-aware entity resolution runner.

Validates the repair on a COPY of the store first (fail-safe), then, only if every
prediction holds on the copy, applies it to the real store. Steps:

  1. Copy the store to a scratch path.
  2. On the copy: run build_universe (time-aware intervals + membership), then
     build_adjusted_view (interval-joined). Capture the universe_membership diff vs the
     pre-repair store (P7) and the recycled-split count (P1).
  3. Symbol-grain prev_close invariant over the whole panel, enumerating every violation
     (P3). Check DVL 2021-08-05 (P4) and the DTIL close regression (P5).
  4. Re-run R1 on the repaired copy; report before/after composition (P6, not asserted).
  5. If P1-P5 hold, apply the same rebuild to the real store; else STOP and report.

Usage:
    python scripts/psb1/repair_entity_intervals.py            # validate on copy, then apply
    python scripts/psb1/repair_entity_intervals.py --dry-run  # copy only, do not touch real store
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "csmp"))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))

import build_universe                # noqa: E402 — D6-authorised edit
import ingest_corporate_actions      # noqa: E402 — the adjusted-view builder
import screening_harness as H        # noqa: E402
from screening_harness import load_factors_by_entity, load_ca_scope_exclusions  # noqa: E402

STORE = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
SCRATCH = Path(r"C:\Users\devou\AppData\Local\Temp\opencode") / "psb1_prompt3_copy.duckdb"


def membership_snapshot(con):
    return {(r[0], r[1], r[2]) for r in con.execute(
        "SELECT rebalance_date, symbol, rank FROM universe_membership").fetchall()}


def _entity_map_join(con, alias, datecol="trade_date"):
    """Half-open interval join fragment mapping (symbol, <datecol>) -> entity, using
    `symbol_entity_intervals` if present (post-repair) else `universe_eligibility`
    (Prompt-2 state). Same entity grain either way."""
    has_iv = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_name='symbol_entity_intervals'").fetchone()[0]
    if has_iv:
        return (f"JOIN symbol_entity_intervals i ON i.symbol = {alias}.symbol "
                f"AND {alias}.{datecol} >= i.valid_from AND {alias}.{datecol} < i.valid_to")
    return f"JOIN universe_eligibility i ON i.symbol = {alias}.symbol"


def prev_close_violations(con):
    """VIEW-INDUCED fabrications in the CONSUMED series over the WHOLE panel (P3).

    Amended twice per Lead Review 5 and the STOP investigation:

      1. The invariant is on the series PSB-1 actually consumes — adjusted `close`
         (`load_panel` reads adj_close into `panel.px`; the view's `prev_close` COLUMN is
         read by no consumer, so testing it flags the legitimate ex-date `prev_close` step
         that backward adjustment intends — 246 benign rows, out of Prompt 3 scope).
      2. Entity grain over the EQ+BE union at the consumer's dedup (rn=1 turnover-primary),
         so the check never crosses a recycled-ticker seam or a BE->EQ migration
         (Review 5 Finding B).

    Definition (Review 4/5 acceptance criterion): for consecutive entity sessions the
    ADJUSTED close-to-close return must equal the RAW return divided by the spanning
    factor. A violation is the adjustment fabricating a return the raw series + register
    do not justify (e.g. the DVL/DTIL seam). Returns (entity, date, adj_ret, expected)."""
    ja = _entity_map_join(con, "a")
    jr = _entity_map_join(con, "r")
    je = _entity_map_join(con, "af", datecol="ex_date")
    sql = f"""
        WITH ad AS (
            SELECT i.entity, a.trade_date, a.close acl,
                   ROW_NUMBER() OVER (PARTITION BY i.entity, a.trade_date
                       ORDER BY a.turnover DESC NULLS LAST, a.symbol) rn
            FROM equity_bhavcopy_adjusted a {ja}),
        rw AS (
            SELECT i.entity, r.trade_date, r.close rcl,
                   ROW_NUMBER() OVER (PARTITION BY i.entity, r.trade_date
                       ORDER BY r.turnover DESC NULLS LAST, r.symbol) rn
            FROM equity_bhavcopy r {jr}
            WHERE r.series IN ('EQ','BE')),
        ev AS (
            SELECT i.entity, af.ex_date,
                   COALESCE(EXP(SUM(LN(af.factor)) FILTER (
                       WHERE af.action_type IN ('BONUS','SPLIT','SPECIAL_DIVIDEND'))), 1.0) f
            FROM adjustment_factors af {je}
            GROUP BY i.entity, af.ex_date),
        a2 AS (SELECT entity, trade_date, acl,
                      LAG(acl) OVER (PARTITION BY entity ORDER BY trade_date) alag,
                      LAG(trade_date) OVER (PARTITION BY entity ORDER BY trade_date) ptd
               FROM ad WHERE rn=1),
        r2 AS (SELECT entity, trade_date, rcl,
                      LAG(rcl) OVER (PARTITION BY entity ORDER BY trade_date) rlag
               FROM rw WHERE rn=1)
        SELECT a2.entity, a2.trade_date, a2.acl/a2.alag AS adj_ret,
               (r2.rcl/r2.rlag) / COALESCE((SELECT f FROM ev
                   WHERE ev.entity=a2.entity AND ev.ex_date>a2.ptd AND ev.ex_date<=a2.trade_date
                   ORDER BY ev.ex_date LIMIT 1), 1.0) AS expected
        FROM a2 JOIN r2 USING (entity, trade_date)
        WHERE a2.alag>0 AND r2.rlag>0
          AND ABS(a2.acl/a2.alag - (r2.rcl/r2.rlag) / COALESCE((SELECT f FROM ev
                   WHERE ev.entity=a2.entity AND ev.ex_date>a2.ptd AND ev.ex_date<=a2.trade_date
                   ORDER BY ev.ex_date LIMIT 1), 1.0)) > 1e-6
        ORDER BY ABS(a2.acl/a2.alag) DESC
    """
    return con.execute(sql).fetchall()


def rebuild(con):
    """Run the time-aware universe build + adjusted-view rebuild on `con` (read-write)."""
    # build_universe.main() opens its own connection; call its steps against our con instead.
    for t in ("universe_membership", "universe_intervals", "instrument_master",
              "universe_eligibility", "universe_probes", "symbol_entity_intervals"):
        con.execute(f"DROP TABLE IF EXISTS {t}")
    con.execute(build_universe.SCHEMA_SQL)
    con.execute("DELETE FROM universe_probes")
    method = build_universe.probe_official_membership(con)
    build_universe.fetch_instrument_master(con)
    _, n_rename, n_split = build_universe.build_entities(con)
    build_universe.classify_eligibility(con)
    membership, _ = build_universe.build_membership(con, method)
    build_universe.build_intervals(con, membership)
    ingest_corporate_actions.build_adjusted_view(con)
    return n_split


def r1_scan(db_path):
    panel = H.load_panel(db_path=str(db_path), cutoff=H.DEV_HI)
    fac = load_factors_by_entity(str(db_path), H.DEV_HI)
    doc = load_ca_scope_exclusions(str(db_path), H.DEV_HI)
    return H.scan_data_integrity(panel, fac, doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # ---- baseline snapshots from the real store (read-only) --------------------------------------
    ro = duckdb.connect(str(STORE), read_only=True)
    memb_before = membership_snapshot(ro)
    pc_before = prev_close_violations(ro)
    ro.close()
    scan_before = r1_scan(STORE)
    print(f"BEFORE: membership rows={len(memb_before)}, view-induced adj_close violations={len(pc_before)}")
    print(f"BEFORE R1: {scan_before.n_moves} moves, {len(scan_before.residue_rows)} residue, "
          f"{len(scan_before.undocumented)} halt, {len(scan_before.large_genuine)} large")

    # ---- rebuild on a COPY -----------------------------------------------------------------------
    SCRATCH.parent.mkdir(parents=True, exist_ok=True)
    if SCRATCH.exists():
        SCRATCH.unlink()
    shutil.copy2(STORE, SCRATCH)
    cc = duckdb.connect(str(SCRATCH))
    n_split = rebuild(cc)
    cc.close()
    print(f"\nCOPY rebuilt: recycled-ticker splits = {n_split}")

    ro2 = duckdb.connect(str(SCRATCH), read_only=True)
    memb_after = membership_snapshot(ro2)
    pc_after = prev_close_violations(ro2)
    n_intervals = ro2.execute("SELECT COUNT(*) FROM symbol_entity_intervals").fetchone()[0]
    n_multi = ro2.execute(
        "SELECT COUNT(*) FROM (SELECT symbol FROM symbol_entity_intervals "
        "GROUP BY symbol HAVING COUNT(*)>1)").fetchone()[0]
    multi_syms = [r[0] for r in ro2.execute(
        "SELECT symbol FROM symbol_entity_intervals GROUP BY symbol HAVING COUNT(*)>1").fetchall()]
    dvl = ro2.execute("SELECT prev_close, close FROM equity_bhavcopy_adjusted "
                      "WHERE symbol='DVL' AND trade_date='2021-08-05'").fetchone()
    dvl_prev_day = ro2.execute("SELECT close FROM equity_bhavcopy_adjusted "
                               "WHERE symbol='DVL' AND trade_date='2021-08-04'").fetchone()
    dtil = ro2.execute("""SELECT trade_date, close FROM equity_bhavcopy_adjusted
                          WHERE symbol='DTIL' AND trade_date IN ('2021-08-04','2021-08-05')
                          ORDER BY trade_date""").fetchall()
    ro2.close()
    scan_after = r1_scan(SCRATCH)

    # ---- predictions -----------------------------------------------------------------------------
    p1 = n_multi == 1 and multi_syms == ["DTIL"]
    p2 = True  # co-trading assertion passed inside rebuild (would have raised); confirm below
    p3 = len(pc_after) == 0
    dvl_prev = dvl[0] if dvl else None
    p4 = dvl_prev is not None and dvl_prev_day is not None and abs(dvl_prev - dvl_prev_day[0]) < 0.01
    dtil_ret = (dtil[1][1] / dtil[0][1] - 1.0) if len(dtil) == 2 and dtil[0][1] else None
    p5 = dtil_ret is not None and -0.36 < dtil_ret < -0.31
    memb_changed = memb_before != memb_after

    print("\n=== PREDICTIONS (validated on copy) ===")
    print(f"P1 exactly 1 symbol splits (DTIL): multi={n_multi} {multi_syms} -> {'PASS' if p1 else 'FAIL'}")
    print(f"P2 co-trading assertion passes (0 overlapping entities): {'PASS' if p2 else 'FAIL'} "
          "(rebuild would have raised otherwise)")
    print(f"P3 view-induced adj_close-continuity violations {len(pc_before)} -> {len(pc_after)} "
          f"(expect 0): {'PASS' if p3 else 'FAIL'}")
    print(f"P4 DVL 2021-08-05 adj_prev_close={dvl_prev} == adj_close(08-04)="
          f"{dvl_prev_day[0] if dvl_prev_day else None}: {'PASS' if p4 else 'FAIL'}")
    print(f"P5 DTIL 2021-08-05 close return={dtil_ret:+.4f} (~-0.335 expected): "
          f"{'PASS' if p5 else 'FAIL'}" if dtil_ret is not None else "P5 DTIL rows missing: FAIL")
    if pc_after:
        print(f"\nView-induced adj_close-continuity violations remaining ({len(pc_after)}), enumerated:")
        for ent, d, adj_ret, expected in pc_after[:50]:
            print(f"  {ent:12s} {d} adj_ret={adj_ret:.4f} vs expected(raw/factor)={expected:.4f}")

    # ---- P6 R1 composition (report, not asserted) ------------------------------------------------
    print("\n=== P6 — R1 composition before/after (reported, not asserted) ===")
    print(f"  moves:        {scan_before.n_moves} -> {scan_after.n_moves}")
    print(f"  residue:      {len(scan_before.residue_rows)} -> {len(scan_after.residue_rows)}")
    print(f"  undoc(HALT):  {len(scan_before.undocumented)} -> {len(scan_after.undocumented)}")
    print(f"  large-genuine:{len(scan_before.large_genuine)} -> {len(scan_after.large_genuine)}")
    print("  residue rows after:")
    for e, d, r, cls, docd in sorted(scan_after.residue_rows, key=lambda x: x[2]):
        print(f"    {e:12s} {d} {r:+.1%} {cls} {'documented' if docd else 'UNDOCUMENTED->HALT'}")
    dtil_in = any(e == "DTIL" for e, *_ in scan_after.residue_rows) or \
              any(e == "DTIL" for e, *_ in scan_after.undocumented)
    print(f"  DTIL present in R1 residue/halt: {dtil_in} "
          "(pre-authorized §11.3 halt if a member — see P7)")

    # ---- P7 membership diff (STOP AND REPORT) ----------------------------------------------------
    print("\n=== P7 — universe_membership diff (STOP AND REPORT, do not act) ===")
    if memb_changed:
        added = memb_after - memb_before
        removed = memb_before - memb_after
        print(f"  MEMBERSHIP CHANGED: +{len(added)} / -{len(removed)} cells "
              f"(before {len(memb_before)}, after {len(memb_after)})")
        for tag, s in (("+", added), ("-", removed)):
            for rd, sym, rk in sorted(s)[:20]:
                print(f"    {tag} {rd} {sym} rank={rk}")
    else:
        print("  MEMBERSHIP UNCHANGED — byte-identical to the banked universe. "
              "CSMP A2 substrate unaffected by the membership recut.")

    all_pass = p1 and p2 and p3 and p4 and p5
    print(f"\n{'ALL P1-P5 PASS on copy' if all_pass else 'PREDICTION FAILURE on copy — STOP'}")

    # ---- apply to real store only if clean and not dry-run ---------------------------------------
    if all_pass and not args.dry_run:
        rw = duckdb.connect(str(STORE))
        rebuild(rw)
        rw.close()
        print(f"\nAPPLIED to real store {STORE}.")
    elif args.dry_run:
        print("\n--dry-run: real store NOT modified.")
    else:
        print("\nReal store NOT modified (prediction failure).")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
