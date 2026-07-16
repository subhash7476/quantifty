"""Profile data generation."""
import sys, time
sys.path.insert(0, '.')
from pathlib import Path
import duckdb
import numpy as np
from datetime import date, timedelta
from scripts.psb2 import harness as H

ROOT = Path(__file__).resolve().parent.parent
N_CAL_DAYS = 3500
ENTITIES = [f"S{i:04d}" for i in range(1, 31)]

def bday_span(start, n):
    days = []
    d = start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days

t0 = time.time()
cal = bday_span(date(2010, 1, 4), N_CAL_DAYS)
print(f"Calendar: {len(cal)} days in {time.time()-t0:.1f}s")

t0 = time.time()
fg = H.fortnightly_grid(cal)
print(f"Fortnightly grid: {len(fg)} dates in {time.time()-t0:.1f}s")

# Build panel
out = Path("data/psb2_synthetic/profile.duckdb")
con = duckdb.connect(str(out))
con.execute("CREATE TABLE trading_calendar (trade_date DATE, n_symbols INTEGER)")
con.execute("CREATE TABLE universe_eligibility (symbol VARCHAR, entity VARCHAR)")
con.execute("CREATE TABLE universe_membership (rebalance_date DATE, symbol VARCHAR, rank INTEGER)")
con.execute("CREATE TABLE equity_bhavcopy_adjusted (symbol VARCHAR, trade_date DATE, close DOUBLE, open DOUBLE, deliv_pct DOUBLE, turnover DOUBLE)")

t0 = time.time()
con.executemany("INSERT INTO trading_calendar VALUES (?, 200)", [(d,) for d in cal])
con.executemany("INSERT INTO universe_eligibility VALUES (?, ?)", [(e, e) for e in ENTITIES])
con.executemany("INSERT INTO universe_membership VALUES (?, ?, ?)", [(date(2010, 1, 4), e, i+1) for i, e in enumerate(ENTITIES)])
print(f"Metadata inserts done in {time.time()-t0:.1f}s")

# Generate price data
t0 = time.time()
rng = np.random.default_rng(42)
price = np.ones((len(ENTITIES), len(cal))) * 100.0
for j in range(1, len(cal)):
    price[:, j] = price[:, j - 1] * (1 + rng.normal(0, 0.01, len(ENTITIES)))
print(f"Price generation done in {time.time()-t0:.1f}s")

# Generate delivery data
t0 = time.time()
deliv_base = {e: 0.40 for e in ENTITIES}
rows = []
for i, e in enumerate(ENTITIES):
    for j, d in enumerate(cal):
        dp = deliv_base[e] + rng.normal(0, 0.05)
        dp = max(0.05, min(0.95, dp))
        cv = float(round(float(price[i, j]), 2))
        rows.append((e, d, cv, cv, round(dp, 4), float(round(float(rng.uniform(1e6, 1e8)), 0))))
print(f"Row generation done in {time.time()-t0:.1f}s ({len(rows)} rows)")

t0 = time.time()
con.executemany("INSERT INTO equity_bhavcopy_adjusted VALUES (?,?,?,?,?,?)", rows)
con.close()
print(f"Bulk insert done in {time.time()-t0:.1f}s")

# Now load
t0 = time.time()
panel = H.load_panel(str(out), cutoff=H.DEV_HI)
print(f"Panel load done in {time.time()-t0:.1f}s: {len(panel.px)} px entries")
