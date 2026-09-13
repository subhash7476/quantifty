"""Structural certification checks for the NIFTY index-options EOD store — PTMS Family G.

Six gates, all structural. Nothing here computes a return, a signal, a
parameter or a statistic about outcomes: the checks are key integrity, null and
sign checks, ordering, grid spacing and class counts. That is what a substrate
contract is made of, and it is the level at which this surface can be certified
without spending research budget.

  G1  session coverage against the trading calendar
  G2  key uniqueness, nulls, OHLC ordering, per-session row sanity
  G3  expiry-regime structure (monthly -> weekly -> Tuesday) and nominal expiry
  G4  corporate-action requirement (index options: none applies)
  G5  tradeability semantics (a row is a quote, not a trade)
  G6  provenance and currency

Exit code is 1 if any HARD check fails; declared contract facts and documented
quarantines do not fail the run.

  python scripts/msrp/certify_index_options.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "market_data" / "options_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"

# Sessions the cash market traded but NSE published no F&O bhavcopy: Muhurat,
# special live sessions and Budget Saturdays. Absence is expected, not a hole.
EXPECTED_ABSENT = {
    "2016-10-30", "2019-10-27", "2020-02-01", "2020-11-14", "2023-11-12",
    "2024-01-20", "2024-03-02", "2024-05-18", "2025-02-01", "2026-02-01",
}
# trading_calendar carries this date; equity_bhavcopy has no rows for it either,
# so the calendar is wrong rather than this store.
CALENDAR_ARTIFACT = {"2016-04-19"}


def main() -> int:
    con = duckdb.connect(str(DB), read_only=True)
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    hard_fail = []

    rows, lo, hi, sessions = con.execute(
        "SELECT count(*), min(trade_date), max(trade_date), count(DISTINCT trade_date) "
        "FROM option_bhavcopy").fetchone()
    print(f"STORE  {rows:,} rows · {lo} -> {hi} · {sessions:,} sessions")
    print(f"       underlyings: {[r[0] for r in con.execute('SELECT DISTINCT symbol FROM option_bhavcopy').fetchall()]}")

    # --- G1 session coverage --------------------------------------------------
    cal = con.execute(
        "SELECT count(*) FROM eq.trading_calendar WHERE trade_date BETWEEN ? AND ?",
        [lo, hi]).fetchone()[0]
    absent = [str(r[0]) for r in con.execute(
        "SELECT trade_date FROM eq.trading_calendar WHERE trade_date BETWEEN ? AND ? "
        "AND trade_date NOT IN (SELECT DISTINCT trade_date FROM option_bhavcopy) "
        "ORDER BY 1", [lo, hi]).fetchall()]
    orphan = [str(r[0]) for r in con.execute(
        "SELECT DISTINCT trade_date FROM option_bhavcopy "
        "WHERE trade_date NOT IN (SELECT trade_date FROM eq.trading_calendar) ORDER BY 1").fetchall()]
    unexplained = [d for d in absent if d not in EXPECTED_ABSENT | CALENDAR_ARTIFACT]
    print(f"\nG1  coverage {sessions:,} of {cal:,} calendar sessions")
    print(f"    expected absences (no F&O published): {len([d for d in absent if d in EXPECTED_ABSENT])}")
    print(f"    calendar artifacts: {[d for d in absent if d in CALENDAR_ARTIFACT]}")
    print(f"    UNEXPLAINED absences: {unexplained or 'none'}")
    print(f"    dates absent from the calendar: {orphan or 'none'}")
    if orphan:
        hard_fail.append("G1: options dates with no calendar session")

    # --- G2 key integrity -----------------------------------------------------
    dupes = con.execute(
        "SELECT count(*) FROM (SELECT trade_date, symbol, expiry_dt, strike, option_type "
        "FROM option_bhavcopy GROUP BY ALL HAVING count(*) > 1)").fetchone()[0]
    nulls = con.execute(
        "SELECT sum(CASE WHEN expiry_dt IS NULL THEN 1 ELSE 0 END), "
        "       sum(CASE WHEN strike IS NULL THEN 1 ELSE 0 END), "
        "       sum(CASE WHEN close IS NULL THEN 1 ELSE 0 END), "
        "       sum(CASE WHEN settle IS NULL THEN 1 ELSE 0 END) FROM option_bhavcopy").fetchone()
    backwards = con.execute("SELECT count(*) FROM option_bhavcopy WHERE expiry_dt < trade_date").fetchone()[0]
    neg = con.execute("SELECT count(*) FROM option_bhavcopy WHERE strike <= 0 OR low < 0 OR settle < 0").fetchone()[0]
    ohlc = con.execute(
        "SELECT count(*) FROM option_bhavcopy WHERE contracts > 0 "
        "AND (high < low OR high < greatest(open, close) OR low > least(open, close))").fetchone()[0]
    thin = con.execute(
        "SELECT count(*) FROM (SELECT trade_date FROM option_bhavcopy GROUP BY 1 HAVING count(*) < 400)").fetchone()[0]
    print(f"\nG2  duplicate keys {dupes} · nulls {nulls} · expiry<trade {backwards} · "
          f"negative {neg} · OHLC violations among TRADED rows {ohlc} · thin sessions {thin}")
    for name, val in (("duplicate keys", dupes), ("nulls", sum(nulls)), ("expiry<trade", backwards),
                      ("negative values", neg), ("OHLC violations (traded)", ohlc)):
        if val:
            hard_fail.append(f"G2: {val} {name}")

    # --- G3 expiry regime -----------------------------------------------------
    print("\nG3  expiries per year by weekday")
    for y, d, n in con.execute(
            "SELECT year(expiry_dt), dayname(expiry_dt), count(DISTINCT expiry_dt) "
            "FROM option_bhavcopy GROUP BY 1,2 ORDER BY 1, 3 DESC").fetchall():
        print(f"      {y}  {d:<10} {n}")
    nominal = [str(r[0]) for r in con.execute(
        "SELECT DISTINCT expiry_dt FROM option_bhavcopy WHERE expiry_dt <= ? "
        "AND expiry_dt NOT IN (SELECT trade_date FROM eq.trading_calendar) ORDER BY 1", [hi]).fetchall()]
    orphan_exp = [str(r[0]) for r in con.execute(
        "SELECT expiry_dt FROM (SELECT DISTINCT expiry_dt FROM option_bhavcopy WHERE expiry_dt <= ? "
        "EXCEPT SELECT DISTINCT expiry_dt FROM option_bhavcopy WHERE trade_date = expiry_dt) "
        "ORDER BY 1", [hi]).fetchall()]
    print(f"    expiry_dt is NOMINAL — {len(nominal)} expiries fall on non-trading days: {nominal}")
    print(f"    expiries with no expiry-day row: {orphan_exp}")
    print("    modal strike gap by year:")
    for y, gap, n in con.execute(
            "WITH s AS (SELECT DISTINCT trade_date, expiry_dt, strike FROM option_bhavcopy), "
            "g AS (SELECT year(trade_date) y, strike - lag(strike) OVER "
            "      (PARTITION BY trade_date, expiry_dt ORDER BY strike) gap FROM s) "
            "SELECT y, gap, count(*) FROM g WHERE gap IS NOT NULL GROUP BY 1,2 "
            "QUALIFY row_number() OVER (PARTITION BY y ORDER BY count(*) DESC) = 1 ORDER BY y").fetchall():
        print(f"      {y}  {gap:g} points")

    # --- G4 corporate actions -------------------------------------------------
    print("\nG4  corporate actions: NONE APPLY. Strikes are absolute index points on a "
          "divisor-adjusted index;")
    print("    no bonus/split/face-value event re-prices a listed NIFTY contract and no "
          "adjustment factor exists.")
    print("    Index reconstitution changes the underlying's composition, not any contract's terms.")

    # --- G5 tradeability ------------------------------------------------------
    traded, untraded, oi_zero, untraded_priced, traded_oi_zero = con.execute(
        "SELECT sum(CASE WHEN contracts > 0 THEN 1 ELSE 0 END), "
        "       sum(CASE WHEN contracts = 0 THEN 1 ELSE 0 END), "
        "       sum(CASE WHEN open_int = 0 THEN 1 ELSE 0 END), "
        "       sum(CASE WHEN contracts = 0 AND close > 0 THEN 1 ELSE 0 END), "
        "       sum(CASE WHEN contracts > 0 AND open_int = 0 THEN 1 ELSE 0 END) "
        "FROM option_bhavcopy").fetchone()
    print(f"\nG5  traded rows (contracts > 0): {traded:,} ({100*traded/rows:.1f}%)")
    print(f"    untraded rows: {untraded:,} — of which {untraded_priced:,} carry close > 0")
    print(f"    open_int = 0: {oi_zero:,}, of which {traded_oi_zero:,} DID trade "
          f"(intraday open-and-close)")
    print("    RULE: `contracts > 0` is the tradeability predicate. `open_int > 0` is NOT — "
          "it discards real trades.")
    if untraded_priced != untraded:
        print(f"    note: {untraded - untraded_priced:,} untraded rows carry close = 0")

    # --- G6 provenance --------------------------------------------------------
    ing_lo, ing_hi = con.execute("SELECT min(ingested_at), max(ingested_at) FROM option_bhavcopy").fetchone()
    last_cal = con.execute("SELECT max(trade_date) FROM eq.trading_calendar").fetchone()[0]
    print(f"\nG6  ingest: scripts/msrp/ingest_option_bhavcopy.py (committed, idempotent, "
          f"insert-only per date)")
    print(f"    ingested_at {ing_lo} -> {ing_hi}")
    print(f"    store max {hi} vs calendar max {last_cal} — "
          f"{'CURRENT' if hi >= last_cal else f'STALE by {(last_cal - hi).days} days'}")
    con.close()

    print()
    if hard_fail:
        print("HARD FAILURES:", hard_fail)
        return 1
    print("No hard structural failure. Declared contract facts and documented quarantines stand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
