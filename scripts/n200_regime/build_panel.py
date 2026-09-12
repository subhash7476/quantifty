"""Substrate -> base panel for the N200 regime classifier.

Design: `docs/superpowers/specs/2026-09-09-n200-regime-hmm-design.md` §4, §12.

Writes one row per (entity, session) for every name that is ever a universe
member, carrying CA-adjusted OHLC, the daily Garman-Klass variance, the
membership flag, and a sequence id.

**Why this stops at GK and does not write features.** The GK floor, the
winsorization bounds and the standardization moments are all fit-window
quantities (§5, §8), so they differ per fold. Computing features here would bake
one fold's normalization into the panel and quietly defeat the barrier. This
script produces what is fold-independent; `run_folds.py` adds the rest.

Non-member rows are kept because a name needs 252 sessions of trailing price
history before its first membership date to produce a feature at all — that
warmup is drawn from price history, which membership does not gate.

Usage: python scripts/n200_regime/build_panel.py
Output: data/features/n200_regime/panel.duckdb
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
OUT_DIR = ROOT / "data" / "features" / "n200_regime"
OUT = OUT_DIR / "panel.duckdb"
SCRATCH_DIR = ROOT / "data" / "scratch"

SERIES = ("EQ", "BE")
SEQUENCE_BREAK_DAYS = 10
LN2_TERM = 2.0 * 0.6931471805599453 - 1.0


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def build() -> int:
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.unlink(missing_ok=True)

    # In-memory root: the source attaches READ_ONLY, the output attaches
    # writable. The limit sits below the box's free RAM so DuckDB spills to
    # data/scratch instead of failing to allocate (see the preflight).
    con = duckdb.connect()
    con.execute("PRAGMA memory_limit='2GB'")
    con.execute("PRAGMA threads=2")
    con.execute(f"PRAGMA temp_directory='{SCRATCH_DIR.as_posix()}'")
    con.execute(f"ATTACH '{SRC.as_posix()}' AS src (READ_ONLY)")
    con.execute(f"ATTACH '{OUT.as_posix()}' AS out")

    print("[1] Resolving universe symbols and their membership windows...")
    con.execute("""
        CREATE TEMP TABLE member_windows AS
        WITH reb AS (
          SELECT DISTINCT rebalance_date FROM src.universe_membership),
        spans AS (
          SELECT rebalance_date,
                 lead(rebalance_date) OVER (ORDER BY rebalance_date) AS next_reb
          FROM reb)
        SELECT m.symbol, m.rebalance_date,
               COALESCE(s.next_reb, DATE '9999-12-31') AS next_reb
        FROM src.universe_membership m
        JOIN spans s USING (rebalance_date)
    """)

    # `equity_bhavcopy_adjusted` is a view doing entity-grain CA joins and is
    # recomputed per query, so it is read exactly once, restricted to symbols
    # that are ever members.
    print("[2] Materializing adjusted OHLC for universe symbols (single read)...")
    placeholders = ", ".join("?" for _ in SERIES)
    con.execute(f"""
        CREATE TEMP TABLE px AS
        SELECT trade_date, symbol, series, open, high, low, close
        FROM src.equity_bhavcopy_adjusted
        WHERE series IN ({placeholders})
          AND symbol IN (SELECT DISTINCT symbol FROM src.universe_membership)
    """, list(SERIES))
    n_px = con.execute("SELECT count(*) FROM px").fetchone()[0]
    print(f"    {n_px:,} rows")

    # A symbol can carry both EQ and BE on one date; keep EQ so a surveillance
    # move changes the row's series without duplicating the session.
    print("[3] Deduplicating series collisions and attaching entities...")
    con.execute("""
        CREATE TEMP TABLE px1 AS
        SELECT * FROM px
        QUALIFY row_number() OVER (
          PARTITION BY symbol, trade_date
          ORDER BY CASE WHEN series = 'EQ' THEN 0 ELSE 1 END) = 1
    """)
    con.execute("""
        CREATE TEMP TABLE px_ent AS
        SELECT p.*, COALESCE(e.entity, p.symbol) AS entity
        FROM px1 p
        LEFT JOIN src.symbol_entity_intervals e
          ON e.symbol = p.symbol
         AND p.trade_date >= e.valid_from
         AND p.trade_date <  e.valid_to   -- half-open [valid_from, valid_to): a closed
                                          -- comparison double-matches a recycled ticker's
                                          -- handoff date against both of its entities
    """)

    print("[4] Flagging membership and computing Garman-Klass...")
    con.execute(f"""
        CREATE TEMP TABLE flagged AS
        SELECT p.entity, p.symbol, p.trade_date, p.series,
               p.open, p.high, p.low, p.close,
               0.5 * pow(ln(p.high / p.low), 2)
                 - {LN2_TERM} * pow(ln(p.close / p.open), 2) AS gk,
               CASE WHEN EXISTS (
                 SELECT 1 FROM member_windows w
                 WHERE w.symbol = p.symbol
                   AND p.trade_date > w.rebalance_date
                   AND p.trade_date <= w.next_reb) THEN TRUE ELSE FALSE END
               AS in_universe
        FROM px_ent p
    """)

    # Gaps-and-islands over member rows only: a break in membership (a month
    # the name drops out) starts a new sequence, so no HMM run is propagated
    # across a hole in the panel.
    print("[5] Cutting membership sequences...")
    con.execute(f"""
        CREATE TABLE out.panel_base AS
        WITH mem AS (
          SELECT entity, trade_date,
                 CASE WHEN date_diff('day',
                        lag(trade_date) OVER (PARTITION BY entity
                          ORDER BY trade_date), trade_date)
                      > {SEQUENCE_BREAK_DAYS} THEN 1 ELSE 0 END AS brk
          FROM flagged WHERE in_universe),
        seqs AS (
          SELECT entity, trade_date,
                 entity || '#' || CAST(sum(brk) OVER (
                   PARTITION BY entity ORDER BY trade_date
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS VARCHAR)
                 AS seq_id
          FROM mem)
        SELECT f.entity, f.symbol, f.trade_date, f.series,
               f.open, f.high, f.low, f.close, f.gk, f.in_universe, s.seq_id
        FROM flagged f
        LEFT JOIN seqs s USING (entity, trade_date)
        ORDER BY f.entity, f.trade_date
    """)

    stats = con.execute("""
        SELECT count(*), count(DISTINCT entity), count(DISTINCT symbol),
               min(trade_date), max(trade_date),
               sum(CASE WHEN in_universe THEN 1 ELSE 0 END),
               count(DISTINCT seq_id),
               sum(CASE WHEN gk = 0 THEN 1 ELSE 0 END)
        FROM out.panel_base
    """).fetchone()
    rows, ents, syms, lo, hi, member_rows, seqs, zero_gk = stats

    con.execute("""
        CREATE TABLE out.build_meta (
          key VARCHAR PRIMARY KEY, value VARCHAR)
    """)
    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "source": str(SRC),
        "series": json.dumps(list(SERIES)),
        "sequence_break_days": str(SEQUENCE_BREAK_DAYS),
        "rows": str(rows), "entities": str(ents), "symbols": str(syms),
        "member_rows": str(member_rows), "sequences": str(seqs),
        "span": f"{lo} -> {hi}",
    }
    con.executemany("INSERT INTO out.build_meta VALUES (?, ?)", list(meta.items()))

    seq_len = con.execute("""
        SELECT count(*) FROM (
          SELECT seq_id, count(*) n FROM out.panel_base
          WHERE in_universe GROUP BY 1) WHERE n < 60
    """).fetchone()[0]

    con.close()

    print(f"\n    rows            {rows:,}")
    print(f"    entities        {ents:,} (from {syms:,} symbols)")
    print(f"    span            {lo} -> {hi}")
    print(f"    member rows     {member_rows:,}")
    print(f"    sequences       {seqs:,}  ({seq_len} shorter than 60 sessions)")
    print(f"    zero-GK rows    {zero_gk:,} ({zero_gk / rows:.2%})")
    print(f"\nWritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
