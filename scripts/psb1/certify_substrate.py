"""PSB-1 Substrate Certification Runner.

Tests every invariant accumulated across Prompts 2–4 against the REAL store
(read-only). Runs independently — no dependencies on any runner's state, no edits
to the store. The output is a script-generated certification report.

Invariants tested (ordered by discovery, roughly the prompt chain):
  I-1   adj_close continuity (adjusted return == raw return / spanning factor)
  I-2   prev_close column fabrications (adj_gap == raw_gap, entity grain)
  I-3   co-trading entities (0 entities with overlapping symbol spans)
  I-4   (entity, ex_date) double-apply (0 drawing factors from >1 symbol)
  I-5   first-session unadjusted ex-date prev_close (0 entities)
  I-6   universe_membership byte-identical to pre-Prompt-3 backup
  I-7   row count == 7,030,920
  I-8   gate-(b) §4 continuity (0 mismatches on CONTINUITY_SYMBOLS)
  I-9   symbol_entity_intervals (4,133 rows, exactly 1 DTIL split)
  I-10  DVL→DTIL re-key confirmed (DVL 0 factors, DTIL 1 factor, provenance)

Usage:
    python scripts/psb1/certify_substrate.py
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "csmp"))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))

from repair_entity_intervals import membership_snapshot  # noqa: E402
from repair_prev_close import prev_close_col_violations   # noqa: E402

STORE = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
BACKUP = Path(r"C:\Users\devou\AppData\Local\Temp\opencode\eqbhav_backup_5f05b0d.duckdb")
REPORT = ROOT / "docs" / "reports" / "PSB1_SUBSTRATE_CERTIFICATION.md"
DEV_HI = date(2022, 12, 31)


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=ROOT).decode().strip()
    except Exception:
        return "unknown"


# ────────────────────────────────────────────────────────────────────────────
#  I-1  adj_close continuity
# ────────────────────────────────────────────────────────────────────────────
def check_adj_close_continuity(con):
    """adjusted return == raw return / spanning factor, at consumer grain.
    From repair_adjusted_view.invariant_violations, Prompt 3."""
    # Precompute entity-level compounded factors per ex_date as a temp table (hybrid: the
    # Prompt-2 invariant does a per-row subquery, but we can materialise once).
    con.execute("""CREATE TEMP TABLE _cert_cum AS
        SELECT entity, ex_date,
               EXP(SUM(LN(price_factor)) OVER (PARTITION BY entity ORDER BY ex_date DESC
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)) cum_price
        FROM (SELECT i.entity, af.ex_date,
                     COALESCE(EXP(SUM(LN(af.factor)) FILTER (
                         WHERE af.action_type IN ('BONUS','SPLIT','SPECIAL_DIVIDEND'))),1.0) AS price_factor
              FROM adjustment_factors af
              JOIN symbol_entity_intervals i ON i.symbol=af.symbol
                   AND af.ex_date>=i.valid_from AND af.ex_date<i.valid_to
              GROUP BY i.entity, af.ex_date)""")
    violations = con.execute("""
        WITH ad AS (
            SELECT i.entity, a.trade_date, a.close acl,
                   ROW_NUMBER() OVER (PARTITION BY i.entity,a.trade_date
                       ORDER BY a.turnover DESC NULLS LAST, a.symbol) rn
            FROM equity_bhavcopy_adjusted a
            JOIN symbol_entity_intervals i ON i.symbol=a.symbol
                 AND a.trade_date>=i.valid_from AND a.trade_date<i.valid_to),
        rw AS (
            SELECT i.entity, r.trade_date, r.close rcl,
                   ROW_NUMBER() OVER (PARTITION BY i.entity,r.trade_date
                       ORDER BY r.turnover DESC NULLS LAST, r.symbol) rn
            FROM equity_bhavcopy r
            JOIN symbol_entity_intervals i ON i.symbol=r.symbol
                 AND r.trade_date>=i.valid_from AND r.trade_date<i.valid_to
            WHERE r.series IN ('EQ','BE')),
        a2 AS (SELECT entity,trade_date,acl,
                      LAG(acl) OVER (PARTITION BY entity ORDER BY trade_date) alag,
                      LAG(trade_date) OVER (PARTITION BY entity ORDER BY trade_date) ptd
               FROM ad WHERE rn=1),
        r2 AS (SELECT entity,trade_date,rcl,
                      LAG(rcl) OVER (PARTITION BY entity ORDER BY trade_date) rlag
               FROM rw WHERE rn=1),
        factor_at AS (
            SELECT a2.entity, a2.trade_date, a2.acl, a2.alag, r2.rcl, r2.rlag,
                   cc.cum_price AS cum_t,
                   -- cum on the previous session: find the smallest ex_date > a2.ptd
                   (SELECT cp.cum_price FROM _cert_cum cp WHERE cp.entity=a2.entity
                    AND cp.ex_date = (SELECT MIN(cp2.ex_date) FROM _cert_cum cp2
                        WHERE cp2.entity=a2.entity AND cp2.ex_date > a2.ptd)) AS cum_tp
            FROM a2 JOIN r2 ON a2.entity=r2.entity AND a2.trade_date=r2.trade_date
            JOIN _cert_cum cc ON cc.entity=a2.entity
                AND cc.ex_date = (SELECT MIN(cc2.ex_date) FROM _cert_cum cc2
                    WHERE cc2.entity=a2.entity AND cc2.ex_date > a2.trade_date)
            WHERE a2.alag>0 AND r2.rlag>0
        )
        SELECT entity, trade_date, acl/alag adj_ret, (rcl/rlag) * (cum_t/NULLIF(cum_tp,1)) expected
        FROM factor_at
        WHERE ABS(acl/alag - (rcl/rlag) * (cum_t/NULLIF(cum_tp,1))) > 1e-6
    """).fetchall()
    return len(violations), violations[:10]


# ────────────────────────────────────────────────────────────────────────────
#  I-2  prev_close column fabrications (via repair_prev_close import)
# ────────────────────────────────────────────────────────────────────────────
def check_prev_close_column(con):
    violations = prev_close_col_violations(con)
    return len(violations), violations[:10]


# ────────────────────────────────────────────────────────────────────────────
#  I-3  co-trading entities
# ────────────────────────────────────────────────────────────────────────────
def check_cotrading(con):
    """No entity may contain two symbols with overlapping trading spans within
    their interval. From repair_entity_intervals.build_entities assertion."""
    seg_rows = con.execute("""
        SELECT i.entity, i.symbol, MIN(e.trade_date) lo, MAX(e.trade_date) hi
        FROM symbol_entity_intervals i
        JOIN equity_bhavcopy e ON e.symbol=i.symbol AND e.series IN ('EQ','BE')
             AND e.trade_date>=i.valid_from AND e.trade_date<i.valid_to
        GROUP BY i.entity, i.symbol
    """).fetchall()
    per_ent = defaultdict(list)
    for ent, sym, lo, hi in seg_rows:
        per_ent[ent].append((sym, lo, hi))
    overlaps = []
    for ent, segs in per_ent.items():
        segs.sort(key=lambda x: x[1])
        for k in range(1, len(segs)):
            if segs[k][0] != segs[k - 1][0] and segs[k][1] <= segs[k - 1][2]:
                overlaps.append((ent, segs[k - 1][0], segs[k][0]))
    return len(overlaps), overlaps[:10]


# ────────────────────────────────────────────────────────────────────────────
#  I-4  (entity, ex_date) double-apply
# ────────────────────────────────────────────────────────────────────────────
def check_double_apply(con):
    dupe = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT i.entity, af.ex_date, COUNT(DISTINCT af.symbol) ns
            FROM adjustment_factors af
            JOIN symbol_entity_intervals i ON i.symbol=af.symbol
                 AND af.ex_date>=i.valid_from AND af.ex_date<i.valid_to
            GROUP BY i.entity, af.ex_date HAVING ns>1)
    """).fetchone()[0]
    return dupe


# ────────────────────────────────────────────────────────────────────────────
#  I-5  first-session unadjusted prev_close
# ────────────────────────────────────────────────────────────────────────────
def check_first_session(con):
    """Entities whose FIRST in-panel session is itself an ex-date, with
    prev_close not properly adjusted. From Prompt 4 Task 5 (F-7)."""
    fs_ex = con.execute("""
        WITH fs AS (
            SELECT i.entity, MIN(a.trade_date) first_td
            FROM equity_bhavcopy_adjusted a
            JOIN symbol_entity_intervals i ON i.symbol=a.symbol
                 AND a.trade_date>=i.valid_from AND a.trade_date<i.valid_to
            GROUP BY i.entity),
        ev AS (
            SELECT i.entity, af.ex_date,
                   COALESCE(EXP(SUM(LN(af.factor)) FILTER (
                     WHERE af.action_type IN ('BONUS','SPLIT','SPECIAL_DIVIDEND'))),1.0) f
            FROM adjustment_factors af
            JOIN symbol_entity_intervals i ON i.symbol=af.symbol
                 AND af.ex_date>=i.valid_from AND af.ex_date<i.valid_to
            GROUP BY i.entity, af.ex_date)
        SELECT fs.entity, fs.first_td, ev.f
        FROM fs JOIN ev ON ev.entity=fs.entity AND ev.ex_date=fs.first_td
        WHERE ev.f <> 1.0
    """).fetchall()
    bad = []
    for entity, td, f in fs_ex:
        adj = con.execute("""
            SELECT a.close, a.prev_close FROM equity_bhavcopy_adjusted a
            JOIN symbol_entity_intervals i ON i.symbol=a.symbol
                 AND a.trade_date>=i.valid_from AND a.trade_date<i.valid_to
            WHERE i.entity=? AND a.trade_date=?
            ORDER BY a.turnover DESC NULLS LAST, a.symbol LIMIT 1""", [entity, td]).fetchone()
        raw = con.execute("""
            SELECT r.close, r.prev_close, r.symbol FROM equity_bhavcopy r
            JOIN symbol_entity_intervals i ON i.symbol=r.symbol
                 AND r.trade_date>=i.valid_from AND r.trade_date<i.valid_to
            WHERE i.entity=? AND r.trade_date=? AND r.series IN ('EQ','BE')
            ORDER BY r.turnover DESC NULLS LAST, r.symbol LIMIT 1""", [entity, td]).fetchone()
        if not adj or not raw or not raw[0] or raw[0] <= 0 or not raw[1]:
            continue
        cum_t = adj[0] / raw[0]
        expected = raw[1] * cum_t * f
        if expected and abs(adj[1] - expected) / expected > 1e-6:
            bad.append((raw[2], td, adj[1], expected))
    return len(bad), bad[:10]


# ────────────────────────────────────────────────────────────────────────────
#  I-6  universe_membership unchanged
# ────────────────────────────────────────────────────────────────────────────
def check_membership(con):
    if not BACKUP.exists():
        return -1, "BACKUP FILE NOT FOUND"
    bk = duckdb.connect(str(BACKUP), read_only=True)
    real = membership_snapshot(con)
    backup = membership_snapshot(bk)
    bk.close()
    identical = real == backup
    added = real - backup
    removed = backup - real
    return (0 if identical else len(added) + len(removed),
            f"real={len(real)} backup={len(backup)} +{len(added)} / -{len(removed)}")


# ────────────────────────────────────────────────────────────────────────────
#  I-7  row count
# ────────────────────────────────────────────────────────────────────────────
def check_row_count(con):
    rows = con.execute("SELECT COUNT(*) FROM equity_bhavcopy_adjusted").fetchone()[0]
    return rows, str(rows)


# ────────────────────────────────────────────────────────────────────────────
#  I-8  gate-(b) §4 continuity
# ────────────────────────────────────────────────────────────────────────────
def check_gate_b_continuity(con):
    CONT = ("RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","ITC","LT","AXISBANK",
            "KOTAKBANK","HINDUNILVR","BHARTIARTL","MARUTI","ASIANPAINT","WIPRO","ONGC",
            "NTPC","POWERGRID","TATAMOTORS","SUNPHARMA")
    df = con.execute(f"SELECT symbol,trade_date,close,prev_close FROM equity_bhavcopy_adjusted "
                     f"WHERE series='EQ' AND symbol IN {CONT} ORDER BY symbol,trade_date").df()
    ex = con.execute(f"SELECT DISTINCT symbol,ex_date FROM adjustment_factors "
                     f"WHERE symbol IN {CONT}").df()
    mismatch = 0
    for sym, g in df.groupby("symbol"):
        g = g.reset_index(drop=True)
        exd = set(ex[ex.symbol == sym].ex_date)
        for i, td in enumerate(g.trade_date):
            if td in exd and i > 0:
                b, a = g.close.iloc[i-1], g.prev_close.iloc[i]
                if b and a and b > 0 and abs(a-b)/b > 0.001:
                    mismatch += 1
    return mismatch, "20 mega-cap symbols"


# ────────────────────────────────────────────────────────────────────────────
#  I-9  symbol_entity_intervals
# ────────────────────────────────────────────────────────────────────────────
def check_intervals(con):
    rows = con.execute("SELECT COUNT(*) FROM symbol_entity_intervals").fetchone()[0]
    multi = con.execute(
        "SELECT symbol, COUNT(*) n FROM symbol_entity_intervals GROUP BY symbol "
        "HAVING n>1 ORDER BY n DESC").fetchall()
    return rows, multi


# ────────────────────────────────────────────────────────────────────────────
#  I-10 DVL→DTIL re-key confirmed
# ────────────────────────────────────────────────────────────────────────────
def check_rekey(con):
    dvl = con.execute("SELECT COUNT(*) FROM adjustment_factors WHERE symbol='DVL'").fetchone()[0]
    dtil = con.execute("SELECT symbol,ex_date,factor,action_type,source FROM "
                       "adjustment_factors WHERE symbol='DTIL'").fetchall()
    return dvl == 0 and len(dtil) >= 1, f"DVL={dvl} DTIL={len(dtil)} {dtil[0][3] if dtil else 'NONE'}"


# ────────────────────────────────────────────────────────────────────────────
#  Main
# ────────────────────────────────────────────────────────────────────────────
def main():
    con = duckdb.connect(str(STORE), read_only=True)

    checks = [
        ("I-1  adj_close continuity (cons. grain)",         check_adj_close_continuity(con),  0),
        ("I-2  prev_close column fabrications",              check_prev_close_column(con),     0),
        ("I-3  co-trading entities (overlapping spans)",     check_cotrading(con),             0),
        ("I-4  (entity,ex_date) double-apply",               (check_double_apply(con), ""),   0),
        ("I-5  first-session unadj. ex-date prev_close",    check_first_session(con),         0),
        ("I-6  universe_membership unchanged",               check_membership(con),            0),
        ("I-7  row count == 7,030,920",                     check_row_count(con),     7030920),
        ("I-8  gate-(b) §4 continuity",                     check_gate_b_continuity(con),     0),
        ("I-9  symbol_entity_intervals (1 DTIL split)",     (None, check_intervals(con)),    None),
        ("I-10 DVL→DTIL re-key confirmed",                  (None, check_rekey(con)),        None),
    ]

    lines = []
    w = lines.append
    w("# PSB-1 Substrate Certification Report\n")
    w(f"**Script-generated** — `scripts/psb1/certify_substrate.py`. "
      f"Code commit `{_git_commit()}`. Real store, read-only.\n")
    w("Invariants accumulated across Prompts 2–4, tested independently on the "
      "post-Prompt-4 real store.\n")
    w("| # | Invariant | Result | Threshold | Evidence |")
    w("|---|---|:--:|---:|")
    all_pass = True
    for label, res, thresh in checks:
        val = res[0]
        extra = res[1]
        if label == "I-9  symbol_entity_intervals (1 DTIL split)":
            rows, multi = extra
            ok = rows == 4133 and len(multi) == 1 and multi[0][0] == "DTIL" and multi[0][1] == 2
            result = "PASS" if ok else "FAIL"
            evidence = f"{rows} rows, multi={len(multi)} ({', '.join(f'{s}x{n}' for s,n in multi)})"
            if not ok:
                all_pass = False
        elif label == "I-10 DVL→DTIL re-key confirmed":
            ok, ev = extra
            result = "PASS" if ok else "FAIL"
            evidence = ev
            if not ok:
                all_pass = False
        elif label == "I-6  universe_membership unchanged":
            ok = val == 0
            result = "PASS" if ok else "FAIL"
            evidence = str(extra)
            if not ok:
                all_pass = False
        else:
            ok = val == thresh
            result = "PASS" if ok else "FAIL"
            if val != thresh:
                all_pass = False
            if isinstance(extra, list):
                evidence = f"{val} violations" if val else "0"
            else:
                evidence = str(extra)
        w(f"| {label} | {result} | {thresh} | {evidence} |")

    w("")
    status = "**ALL INVARIANTS PASS — SUBSTRATE IS CERTIFIED.**" if all_pass \
             else "**CERTIFICATION FAILED — invariants above must be resolved.**"
    w(f"{status}\n")

    # detail sections for non-zero violations
    for label, res, _ in checks:
        val, extra = res
        if isinstance(val, int) and val != 0 and isinstance(extra, list) and extra:
            w(f"### Violations: {label}\n")
            for row in extra[:20]:
                w(f"- `{row}`")
            w("")

    report = "\n".join(lines) + "\n"
    REPORT.write_text(report, encoding="utf-8")
    con.close()

    print(f"Certification {'PASSED' if all_pass else 'FAILED'}: {REPORT}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
