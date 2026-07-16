"""Smoke test: grid counts, constants, basic import."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from datetime import date
import duckdb
from scripts.psb2.harness import (
    fortnightly_grid, monthly_grid, sealed_grid_count_psb2,
    C2_DEV_LO, C3_DEV_LO, C4_DEV_LO, DEV_HI,
)

con = duckdb.connect("data/market_data/equity_bhavcopy.duckdb", read_only=True)
cal = [r[0] for r in con.execute(
    "SELECT trade_date FROM trading_calendar WHERE n_symbols >= 200 ORDER BY trade_date"
).fetchall()]
con.close()

# Dev fortnightly
fg = [d for d in fortnightly_grid(cal) if C2_DEV_LO <= d <= DEV_HI]
print(f"C2/C3 dev fortnightly count: {len(fg)}")
print(f"  First: {fg[0]}, Last: {fg[-1]}")
mid = sum(1 for d in fg if d.day <= 15)
eom = len(fg) - mid
print(f"  Mid-month: {mid}, Month-end: {eom}")
assert len(fg) == 56, f"Expected 56, got {len(fg)}"
assert fg[0] == date(2020, 9, 15), f"First: {fg[0]}"
assert fg[-1] == date(2022, 12, 30), f"Last: {fg[-1]}"
assert mid == 28, f"Mid: {mid}"

# C4 dev monthly
mg = [d for d in monthly_grid(cal) if C4_DEV_LO <= d <= DEV_HI]
print(f"C4 dev monthly count: {len(mg)}")
assert len(mg) == 132, f"Expected 132, got {len(mg)}"

# Common sub-window
common = [d for d in monthly_grid(cal) if date(2020, 9, 4) <= d <= DEV_HI]
print(f"Common sub-window monthly: {len(common)}")
assert len(common) >= 28, f"Expected >=28, got {len(common)}"

# Sealed
n_fort = sealed_grid_count_psb2("data/market_data/equity_bhavcopy.duckdb", "fortnightly")
n_mon = sealed_grid_count_psb2("data/market_data/equity_bhavcopy.duckdb", "monthly")
print(f"Sealed fortnightly: {n_fort}, monthly: {n_mon}")
assert n_fort == 84, f"Fortnightly sealed: {n_fort}"
assert n_mon == 42, f"Monthly sealed: {n_mon}"

print("\nAll grid assertions PASS")
