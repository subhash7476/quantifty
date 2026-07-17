"""Build the Phase-2 reviewer's DEV-TRUNCATED store (freeze-ratification §5 step 4).

Produces a copy of the gate-(a/b/c) equity store containing ONLY dev-window data
(<= 2022-12-30), so the Phase-2 reviewer can *execute* the three re-derivation scripts
(phase1_prereg_analysis.py, phase1_ci_coverage.py, phase1_group_sequential.py) and
reproduce every dossier number, while the sealed held-out window (2023-01 -> 2026-06)
is PHYSICALLY ABSENT — the seal no longer rests on the reviewer's goodwill.

Seal policy
-----------
- equity_bhavcopy is the ONLY priced table; it is fenced to trade_date < 2023-01-01,
  so no sealed price or return exists and the equity_bhavcopy_adjusted VIEW yields
  nothing past 2022-12-30.
- Every other DATED table (trading_calendar, universe_membership, ingest_meta,
  universe_intervals, corporate_actions, ca_*, symbol_changes) is fenced to dev.
- adjustment_factors is kept FULL. This is the ONE irreducible exception: the
  backward-adjusted view multiplies each dev row by the cumulative product of factors
  with ex_date > trade_date (which includes post-2022 ex-dates), and those factors do
  NOT cancel across a rename boundary, so dev-window adjusted prices only reproduce
  byte-exactly with the full factor set. Its 382 post-2022 rows are bare multipliers
  (symbol/ex_date/factor/action_type/source) — no price, no return, no cash amount.

The ORIGINAL store is opened READ-ONLY and never modified.

Self-verifies: (1) sealed-absence on the copy + original intact; (2) byte-faithful
re-derivation by executing the two store-reading handoff scripts against the copy.

Usage:  python scripts/csmp/build_devtruncated_store.py
"""
import hashlib
import importlib.util
import io
import os
from contextlib import redirect_stdout
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
TGT = ROOT / "data" / "market_data" / "equity_bhavcopy_devtruncated.duckdb"
BOUND = "DATE '2023-01-01'"          # keep strictly-before; sealed window is 2023-01 -> 2026-06
CSMP = ROOT / "scripts" / "csmp"

FENCE = {
    "equity_bhavcopy":        f"WHERE trade_date < {BOUND}",
    "trading_calendar":       f"WHERE trade_date < {BOUND}",
    "universe_membership":    f"WHERE rebalance_date < {BOUND}",
    "ingest_meta":            f"WHERE trade_date < {BOUND}",
    "corporate_actions":      f"WHERE ex_date < {BOUND}",
    "ca_evidence_exceptions": f"WHERE ex_date < {BOUND}",
    "ca_parse_rejects":       f"WHERE ex_date < {BOUND}",
    "ca_scope_exclusions":    f"WHERE move_date < {BOUND}",
    "symbol_changes":         f"WHERE effective_dt < {BOUND}",
    # universe_intervals: special-cased (NULL sealed exit_dates)
    # kept FULL (irreducible / dateless reference):
    "adjustment_factors": "", "instrument_master": "", "symbol_isin": "",
    "universe_eligibility": "", "universe_probes": "",
}
CANON_PREREG = ["mean=0.0457", "CI[0.0091,0.0811]",
                "spread vs formation-complete=0.0624",
                "STOP-RULE (mean_IC>0.02 & CI_lo>0 & spread>0, stronger baseline): CONTINUE",
                "rule1=21", "rule2=1"]
CANON_COVERAGE = ["0.957", "0.049", "0.397", "0.809", "0.129"]  # post-F2 (§5.2 fwd()); pre-F2: 0.398 / 0.811


def build():
    if TGT.exists():
        os.remove(TGT)
    src = duckdb.connect(str(SRC), read_only=True)
    view_sql = src.execute("select sql from duckdb_views() "
                           "where view_name='equity_bhavcopy_adjusted'").fetchone()[0]
    base_tables = [r[0] for r in src.execute(
        "select table_name from information_schema.tables "
        "where table_type='BASE TABLE' order by table_name").fetchall()]
    src.close()

    con = duckdb.connect(str(TGT))
    con.execute(f"ATTACH '{SRC}' AS src (READ_ONLY)")
    for t in base_tables:
        if t == "universe_intervals":
            con.execute(f"""CREATE TABLE universe_intervals AS
                SELECT * REPLACE (
                  CASE WHEN exit_date >= {BOUND} THEN NULL ELSE exit_date END AS exit_date)
                FROM src.universe_intervals WHERE entry_date < {BOUND}""")
        else:
            con.execute(f"CREATE TABLE {t} AS SELECT * FROM src.{t} {FENCE.get(t, '')}")
    con.execute(view_sql)
    con.execute("DETACH src")
    con.execute("CHECKPOINT")
    con.close()


def load_module(name, path, dbval):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.DB = dbval
    return m


def verify():
    ok = True
    t = duckdb.connect(str(TGT), read_only=True)
    print("Seal — dated tables (all except adjustment_factors must be dev-only):")
    dated = {"equity_bhavcopy": "trade_date", "trading_calendar": "trade_date",
             "universe_membership": "rebalance_date", "ingest_meta": "trade_date",
             "universe_intervals": "entry_date", "corporate_actions": "ex_date",
             "ca_evidence_exceptions": "ex_date", "ca_parse_rejects": "ex_date",
             "ca_scope_exclusions": "move_date", "symbol_changes": "effective_dt"}
    for tbl, col in dated.items():
        sealed = t.execute(f"select count(*) from {tbl} where {col} >= {BOUND}").fetchone()[0]
        ok &= sealed == 0
        print(f"  {tbl:24} sealed={sealed}  max={t.execute(f'select max({col}) from {tbl}').fetchone()[0]}")
    ev = t.execute(f"select count(*) from equity_bhavcopy_adjusted where trade_date >= {BOUND}").fetchone()[0]
    af_seal = t.execute(f"select count(*) from adjustment_factors where ex_date >= {BOUND}").fetchone()[0]
    af_cols = [r[0] for r in t.execute("select column_name from information_schema.columns "
                                        "where table_name='adjustment_factors'").fetchall()]
    ok &= ev == 0
    ok &= not any(c.lower() in ('close', 'open', 'high', 'low', 'prev_close', 'turnover', 'volume')
                  for c in af_cols)
    print(f"  THE SEAL: adjusted-view sealed rows={ev}; adjustment_factors kept full "
          f"({af_seal} sealed multipliers, cols={af_cols})")
    t.close()

    orig = duckdb.connect(str(SRC), read_only=True)
    n_orig = orig.execute("select count(*) from equity_bhavcopy").fetchone()[0]
    orig.close()
    ok &= n_orig == 7_030_920
    print(f"Original store intact: equity_bhavcopy rows={n_orig:,} (expect 7,030,920)")

    print("Reproduction — executing handoff scripts against the truncated store:")
    p1 = load_module("p1", CSMP / "phase1_prereg_analysis.py", TGT)
    b = io.StringIO()
    with redirect_stdout(b):
        p1.main()
    o1 = b.getvalue()
    p2 = load_module("p2", CSMP / "phase1_ci_coverage.py", TGT)
    b = io.StringIO()
    with redirect_stdout(b):
        p2.run(p2.dev_ic_series())
    o2 = b.getvalue()
    for sub in CANON_PREREG:
        hit = sub in o1
        ok &= hit
        print(f"  [{'ok' if hit else 'MISS'}] prereg: {sub}")
    for sub in CANON_COVERAGE:
        hit = sub in o2
        ok &= hit
        print(f"  [{'ok' if hit else 'MISS'}] coverage: {sub}")
    return ok


def main():
    build()
    ok = verify()
    sha = hashlib.sha256(TGT.read_bytes()).hexdigest()
    print("\n--- MANIFEST ---")
    print(f"file   : {TGT}")
    print(f"size   : {os.path.getsize(TGT) / 1e6:.1f} MB")
    print(f"sha256 : {sha}")
    print(f"VERDICT: {'PASS — sealed-absent and byte-faithful' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
