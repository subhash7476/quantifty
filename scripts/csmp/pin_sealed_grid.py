"""Pin the sealed rebalance-date grid — CALENDAR-ONLY (Prompt-9 Fix 4 / dossier §1.1).

Enumerates the 42 sealed-window formation dates (the last full session, n_symbols >= 200,
of each month from 2022-12 to 2026-05 inclusive) from `trading_calendar` ONLY — trade_date
and n_symbols, NO price table and NO returns. This is the non-price calendar-fact exception
§1.1 authorises; it reads no hypothesis-relevant sealed data.

Deterministic and generated (not hand-typed), so the §1.1 pin has a reproducible provenance.
The count is a VOID-check, never a tuning lever: if it is not 42 this FAILS LOUDLY.

Usage:
    python scripts/csmp/pin_sealed_grid.py
"""
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
SEALED_FIRST_MONTH = date(2022, 12, 1)   # 2022-12 formation -> 2023-01 forward (first OOS obs, §1.1/S5)
SEALED_LAST_MONTH = date(2026, 5, 31)    # 2026-05 formation -> 2026-06 forward (last in-window)
EXPECTED_COUNT = 42


def sealed_rebalance_dates():
    con = duckdb.connect(str(DB), read_only=True)
    grid = [r[0] for r in con.execute("""
      WITH m AS (SELECT trade_date, EXTRACT(YEAR FROM trade_date)::INT y,
                        EXTRACT(MONTH FROM trade_date)::INT mo
                 FROM trading_calendar WHERE n_symbols >= 200)
      SELECT MAX(trade_date) FROM m GROUP BY y, mo ORDER BY 1""").fetchall()]
    con.close()
    return [d for d in grid if SEALED_FIRST_MONTH <= d <= SEALED_LAST_MONTH]


def main():
    dates = sealed_rebalance_dates()
    n = len(dates)
    print(f"Sealed rebalance grid (calendar-only; trading_calendar.n_symbols>=200 month-ends, "
          f"{SEALED_FIRST_MONTH:%Y-%m} .. {SEALED_LAST_MONTH:%Y-%m}):")
    print(f"  count = {n}  |  first = {dates[0]}  |  last = {dates[-1]}")
    print("  " + ", ".join(str(d) for d in dates))
    assert n == EXPECTED_COUNT, (
        f"VOID: sealed formation count = {n}, expected {EXPECTED_COUNT}. This is a VOID-check, "
        "not a tuning lever — do NOT adjust anything to make it 42; report and stop.")
    print(f"OK: count == {EXPECTED_COUNT} (VOID-checked).")


if __name__ == "__main__":
    main()
