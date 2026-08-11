"""
Split a large options chain CSV into per-date DuckDB files.

Streams the CSV line by line — only holds one date's rows in memory at a time.
No memory load of the full 1.8 GB file. Assumes the CSV is sorted by timestamp
(which your Dhan data is).

Each output file: options/{YYYY-MM-DD}.duckdb with table 'options'.

Usage:
    python split_options_csv.py dhan_historical.csv options/
"""

import csv
import sys
from pathlib import Path

import duckdb


def main():
    if len(sys.argv) < 3:
        print("Usage: python split_options_csv.py <csv_path> <output_dir>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Streaming {csv_path} ...")

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)

        current_date = None
        buffer = []

        def flush():
            nonlocal buffer, current_date
            if not buffer or current_date is None:
                return
            out_path = out_dir / f"{current_date}.duckdb"
            # Build DataFrame from buffer
            import pandas as pd
            df = pd.DataFrame(buffer)
            con = duckdb.connect(str(out_path))
            con.execute("DROP TABLE IF EXISTS options")
            con.execute("CREATE TABLE options AS SELECT * FROM df")
            con.close()
            print(f"  {current_date}: {len(buffer)} rows")
            buffer = []

        row_count = 0
        for row in reader:
            row_count += 1
            ts = row["timestamp"]
            # Extract date from ISO timestamp: "2025-01-01T03:45:00+00:00"
            date_str = ts[:10]  # "2025-01-01"

            if current_date is not None and date_str != current_date:
                flush()
                buffer = []

            current_date = date_str
            buffer.append(row)

            if row_count % 1_000_000 == 0:
                print(f"  ... {row_count:,} rows processed")

        # Flush final date
        flush()

    print(f"Done — {row_count:,} rows written to {out_dir}/")


if __name__ == "__main__":
    main()

