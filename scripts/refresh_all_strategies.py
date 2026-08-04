"""Refresh all strategy data — with checkpointing.

Only rebuilds data when source data has changed. Skips strategies
whose output DB is already current.

Usage: python scripts/refresh_all_strategies.py [--force] [--skip-{carry,ts-basis,daily}]
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
SIG_ENGINE = SCRIPTS / "signal_engine"

FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"

MONTHLY_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
WEEKLY_DB = ROOT / "data" / "signal_engine" / "carry" / "weekly_signals.duckdb"
CARRY_FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
TS_SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis" / "ts_signals.duckdb"
DAILY_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
DAILY_FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"


def _latest_source_date():
    con = duckdb.connect(str(FUT_DB), read_only=True)
    r = con.execute(
        "SELECT MAX(trade_date) FROM futures_bhavcopy WHERE inst_type='FUTSTK'"
    ).fetchone()[0]
    con.close()
    return r


def _max_formation(db_path):
    if not db_path.exists():
        return None
    try:
        con = duckdb.connect(str(db_path), read_only=True)
        r = con.execute("SELECT MAX(formation_date) FROM signals").fetchone()[0]
        con.close()
        return r
    except Exception:
        return None


def _needs_rebuild(db_path, label, monthly=False):
    src_max = _latest_source_date()
    if src_max is None:
        print(f"  [{label}] No source data — skipping")
        return False

    out_max = _max_formation(db_path)
    if out_max is None:
        print(f"  [{label}] No existing output — needs build")
        return True

    if isinstance(out_max, date) and isinstance(src_max, date):
        # For monthly formations: the last formation requires the NEXT month
        # to have at least one trading day. Allow up to 40 days of tolerance.
        tolerance = 40 if monthly else 0  # daily cadence: any new source date needs rebuild
        if out_max >= src_max:
            print(f"  [{label}] Up to date (output={out_max}, source={src_max})")
            return False
        if (src_max - out_max).days <= tolerance:
            print(f"  [{label}] Recent (gap={src_max - out_max}) — output={out_max}, source={src_max}")
            return False

    print(f"  [{label}] Stale — output={out_max}, source={src_max}")
    return True


def _run(script_path, args=None, label=""):
    print(f"  [{label}] Running {script_path.name}...")
    t0 = time.time()
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, cwd=str(ROOT))
    elapsed = time.time() - t0
    ok = result.returncode == 0
    status = "OK" if ok else f"FAILED (exit {result.returncode})"
    print(f"  [{label}] {status} ({elapsed:.0f}s)")
    return ok


def _publish_carry_facts():
    """Fast inline facts publish — no re-running build_carry or neutralize."""
    if not MONTHLY_DB.exists():
        print("  [carry-facts] Monthly signals DB not found")
        return False

    if CARRY_FACTS_DB.exists():
        CARRY_FACTS_DB.unlink()

    fc = duckdb.connect(str(CARRY_FACTS_DB))
    fc.execute("SET threads=4")
    fc.execute(f"ATTACH '{MONTHLY_DB}' AS sig (READ_ONLY)")

    fc.execute("""
        CREATE TABLE carry_facts (
            formation_date   DATE    NOT NULL,
            underlying       VARCHAR NOT NULL,
            sector           VARCHAR,
            z_carry          DOUBLE,
            z_carry_neut     DOUBLE,
            quintile         TINYINT,
            eligible         BOOLEAN NOT NULL,
            raw_z            DOUBLE,
            basis_reverting  BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (formation_date, underlying)
        )
    """)
    fc.execute("CREATE INDEX idx_facts_date ON carry_facts (formation_date)")

    fc.execute("""
        INSERT INTO carry_facts
            (formation_date, underlying, sector, z_carry, z_carry_neut,
             quintile, eligible)
        WITH raw AS (
            SELECT s.formation_date, s.underlying, s.sector,
                   s.z_carry, s.z_carry_neut, s.liquid
            FROM sig.signals s WHERE s.z_carry_neut IS NOT NULL
        ),
        ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY formation_date ORDER BY z_carry_neut) AS rn_asc,
                   ROW_NUMBER() OVER (PARTITION BY formation_date ORDER BY z_carry_neut DESC) AS rn_desc,
                   COUNT(*) FILTER (WHERE liquid) OVER (PARTITION BY formation_date) AS n_liq,
                   COUNT(*) OVER (PARTITION BY formation_date) AS n_total
            FROM raw
        )
        SELECT formation_date, underlying, sector, z_carry, z_carry_neut,
               CASE WHEN n_total < 5 OR n_liq < 5 THEN NULL
                    WHEN NOT liquid THEN 3
                    WHEN rn_asc <= GREATEST(1, CAST(ROUND(0.20 * n_liq) AS BIGINT)) THEN 1
                    WHEN rn_desc <= GREATEST(1, CAST(ROUND(0.20 * n_liq) AS BIGINT)) THEN 5
                    ELSE 3 END AS quintile,
               liquid AS eligible
        FROM ranked
    """)

    n = fc.execute("SELECT COUNT(*) FROM carry_facts").fetchone()[0]
    nf = fc.execute("SELECT COUNT(DISTINCT formation_date) FROM carry_facts").fetchone()[0]
    fc.close()
    print(f"  [carry-facts] Published {n:,} facts across {nf} formations")
    return True


def _publish_daily_facts():
    """Fast inline facts publish for ts_basis_daily."""
    if not DAILY_DB.exists():
        print("  [daily-facts] Daily signals DB not found")
        return False

    if DAILY_FACTS_DB.exists():
        DAILY_FACTS_DB.unlink()

    fc = duckdb.connect(str(DAILY_FACTS_DB))
    fc.execute("SET threads=4")
    fc.execute(f"ATTACH '{DAILY_DB}' AS sig (READ_ONLY)")

    fc.execute("""
        CREATE TABLE carry_facts (
            formation_date   DATE    NOT NULL,
            underlying       VARCHAR NOT NULL,
            z_carry_neut     DOUBLE,
            quintile         TINYINT,
            eligible         BOOLEAN NOT NULL,
            PRIMARY KEY (formation_date, underlying)
        )
    """)
    fc.execute("CREATE INDEX idx_facts_date ON carry_facts (formation_date)")

    fc.execute("""
        INSERT INTO carry_facts
        WITH raw AS (
            SELECT formation_date, underlying, z_ts, liquid
            FROM sig.signals WHERE z_ts IS NOT NULL
        ),
        ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY formation_date ORDER BY z_ts) AS rn_asc,
                   ROW_NUMBER() OVER (PARTITION BY formation_date ORDER BY z_ts DESC) AS rn_desc,
                   COUNT(*) FILTER (WHERE liquid) OVER (PARTITION BY formation_date) AS n_liq
            FROM raw
        )
        SELECT formation_date, underlying, z_ts,
               CASE WHEN NOT liquid THEN 3
                    WHEN n_liq < 5 THEN 3
                    WHEN rn_asc <= GREATEST(1, CAST(ROUND(0.20 * n_liq) AS BIGINT)) THEN 1
                    WHEN rn_desc <= GREATEST(1, CAST(ROUND(0.20 * n_liq) AS BIGINT)) THEN 5
                    ELSE 3 END AS quintile,
               liquid AS eligible
        FROM ranked
    """)

    n = fc.execute("SELECT COUNT(*) FROM carry_facts").fetchone()[0]
    nf = fc.execute("SELECT COUNT(DISTINCT formation_date) FROM carry_facts").fetchone()[0]
    fc.close()
    print(f"  [daily-facts] Published {n:,} facts across {nf} formations")
    return True


def main():
    force = "--force" in sys.argv
    skip_carry = "--skip-carry" in sys.argv
    skip_ts = "--skip-ts-basis" in sys.argv
    skip_daily = "--skip-daily" in sys.argv

    print(f"Refresh all strategies — {date.today().isoformat()}")
    print(f"Source: {FUT_DB}")
    src_max = _latest_source_date()
    print(f"Latest source data: {src_max}\n")

    all_ok = True

    # -- 1. Carry (monthly + weekly) -----------------------------------------
    if not skip_carry:
        print("-- Carry --")
        build = SIG_ENGINE / "carry" / "build_carry.py"
        neut = SIG_ENGINE / "carry" / "neutralize.py"
        carry_ran = False

        # Monthly
        if force or _needs_rebuild(MONTHLY_DB, "carry-monthly", monthly=True):
            if not _run(build, ["--incremental"], "carry-monthly"):
                all_ok = False
            else:
                carry_ran = True

        # Weekly
        if all_ok and (force or _needs_rebuild(WEEKLY_DB, "carry-weekly")):
            if not _run(build, ["--incremental", "--weekly"], "carry-weekly"):
                all_ok = False

        # Neutralize (monthly only) — only if monthly was rebuilt
        if all_ok and carry_ran:
            if MONTHLY_DB.exists():
                _run(neut, label="carry-neut")

        # Facts — always refresh after any change
        if all_ok:
            _publish_carry_facts()

    # ── 2. TS Basis (reads from weekly carry) ────────────────────────────
    if not skip_ts:
        print("\n-- TS Basis --")
        if force or _needs_rebuild(TS_SIG_DB, "ts-basis"):
            build = SIG_ENGINE / "ts_basis" / "build_ts_signals.py"
            if _run(build, ["--incremental"], "ts-basis"):
                pub = SIG_ENGINE / "ts_basis" / "publish_facts.py"
                _run(pub, label="ts-basis-facts")
            else:
                all_ok = False

    # ── 3. TS Basis Daily ────────────────────────────────────────────────
    if not skip_daily:
        print("\n-- TS Basis Daily --")
        if force or _needs_rebuild(DAILY_DB, "ts-basis-daily"):
            build = SIG_ENGINE / "ts_basis_daily" / "build_ts_basis_daily.py"
            if _run(build, ["--incremental"], "ts-basis-daily"):
                _publish_daily_facts()
                _run(SIG_ENGINE / "ts_basis_daily" / "apply_recovery_filter.py",
                     label="daily-recovery-filter")
            else:
                all_ok = False

    print(f"\n{'='*60}")
    print(f"  Refresh {'COMPLETE' if all_ok else 'COMPLETE WITH ERRORS'}")
    print(f"{'='*60}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
