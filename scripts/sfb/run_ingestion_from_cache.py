"""Ingest all cached F&O bhavcopy files into the futures store.

Processes cached focal_*.zip and foudiff_*.zip files from bhavcopy_raw/.
Skips dates already present in the store. Uses the existing ingest pipeline.
"""

import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "sfb"))

from ingest_futures_bhavcopy import *  # noqa: E402

RAW_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(DB_PATH))
con.execute(SCHEMA_SQL)

focal = sorted(RAW_DIR.glob("focal_*.zip"))
foudiff = sorted(RAW_DIR.glob("foudiff_*.zip"))
print(f"Cached focal (legacy): {len(focal)}")
print(f"Cached foudiff (UDiFF): {len(foudiff)}")

total = 0
present = 0

for f in focal + foudiff:
    ds = f.stem.split("_", 1)[1]
    d = date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))

    existing = con.execute(
        "SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date = ?", [d]
    ).fetchone()[0]
    if existing > 0:
        present += 1
        continue

    n, src = ingest_day(con, d)
    if n > 0:
        con.execute(
            "INSERT INTO ingest_meta VALUES (?, ?) "
            "ON CONFLICT (trade_date) DO UPDATE SET source = EXCLUDED.source",
            [d, src],
        )
        total += n
    elif n == -2:
        print(f"PARSE-FAIL {d}")
    elif n == -1:
        print(f"TRANSIENT {d}")

con.close()

print(f"\nInserted: {total:,} rows")
print(f"Skipped (already present): {present}")

con = duckdb.connect(str(DB_PATH))
r = con.execute(
    "SELECT COUNT(*), MIN(trade_date), MAX(trade_date) FROM futures_bhavcopy"
).fetchone()
n_und = con.execute(
    "SELECT COUNT(DISTINCT underlying) FROM futures_bhavcopy WHERE inst_type='FUTSTK'"
).fetchone()[0]
print(f"Store: {r[0]:,} rows, {r[1]} to {r[2]}, {n_und} FUTSTK underlyings")
con.close()
