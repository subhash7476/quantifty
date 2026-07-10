"""CSMP — symbol -> ISIN map, from the raw bhavcopy payloads.

Gate (a)'s H2 recorded that ~200 ETF symbols carry `series = EQ` and must be kept
out of an equity universe. It identified them by the symbol-name pattern
`%BEES%`/`%ETF%`/`%GOLD%`. Names are not identifiers: that pattern misses
`KOTAKNIFTY`, `MON100`, `ICICI500`, `ICICIBANKN`, `MOLOWVOL` and 93 others, and it
matches on substrings that could belong to an operating company.

The bhavcopy itself carries the answer. NSE issues `INE*` ISINs to companies and
`INF*` ISINs to mutual-fund schemes, which is what an ETF is. This script unions
the ISIN column of every raw payload that has one — the 2,481 legacy `cm*bhav.csv`
files and the UDiFF `BhavCopy_NSE_CM_*.csv` — into `symbol_isin`, so gates (b) and
(c) can name a non-equity without pattern-matching a string.

Usage:
    python scripts/csmp/build_symbol_isin.py
"""

import csv
import io
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
RAW_DIR = ROOT / "data" / "market_data" / "bhavcopy_raw"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS symbol_isin (
    symbol   VARCHAR,
    isin     VARCHAR,
    source   VARCHAR,
    n_days   INTEGER,
    PRIMARY KEY (symbol)
);
"""


def _read_zip_csv(path):
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return None
        return zf.read(names[0]).decode("utf-8", "replace")


def collect_legacy():
    """`cm<DDMMMYYYY>bhav.csv` — SYMBOL, SERIES, ..., ISIN."""
    counts = defaultdict(Counter)
    for path in sorted(RAW_DIR.rglob("legacy_*.zip")):
        text = _read_zip_csv(path)
        if text is None:
            continue
        for row in csv.DictReader(io.StringIO(text)):
            symbol = (row.get("SYMBOL") or "").strip().upper()
            isin = (row.get("ISIN") or "").strip().upper()
            if symbol and isin:
                counts[symbol][isin] += 1
    return counts


def collect_udiff():
    """`BhavCopy_NSE_CM_*.csv` — TckrSymb, SctySrs, ISIN."""
    counts = defaultdict(Counter)
    for path in sorted(RAW_DIR.rglob("udiff_*.zip")):
        text = _read_zip_csv(path)
        if text is None:
            continue
        for row in csv.DictReader(io.StringIO(text)):
            if (row.get("SctySrs") or "").strip() not in ("EQ", "BE"):
                continue
            symbol = (row.get("TckrSymb") or "").strip().upper()
            isin = (row.get("ISIN") or "").strip().upper()
            if symbol and isin:
                counts[symbol][isin] += 1
    return counts


def main():
    legacy = collect_legacy()
    udiff = collect_udiff()
    print(f"legacy payloads : {len(legacy):,} symbols")
    print(f"udiff payloads  : {len(udiff):,} symbols")

    rows = []
    for symbol, counter in legacy.items():
        isin, n = counter.most_common(1)[0]
        rows.append({"symbol": symbol, "isin": isin,
                     "source": "legacy_bhavcopy", "n_days": n})
    seen = {r["symbol"] for r in rows}
    for symbol, counter in udiff.items():
        if symbol in seen:
            continue
        isin, n = counter.most_common(1)[0]
        rows.append({"symbol": symbol, "isin": isin,
                     "source": "udiff_bhavcopy", "n_days": n})

    con = duckdb.connect(str(DB_PATH))
    con.execute(SCHEMA_SQL)
    con.execute("DELETE FROM symbol_isin")
    df = pd.DataFrame(rows)
    con.execute("INSERT INTO symbol_isin SELECT symbol, isin, source, n_days FROM df")

    store = con.execute("SELECT COUNT(DISTINCT symbol) FROM equity_bhavcopy "
                        "WHERE series IN ('EQ','BE')").fetchone()[0]
    mapped = con.execute("""
        SELECT COUNT(DISTINCT e.symbol) FROM equity_bhavcopy e
        JOIN symbol_isin s ON s.symbol = e.symbol
        WHERE e.series IN ('EQ','BE')""").fetchone()[0]
    funds = con.execute("SELECT COUNT(*) FROM symbol_isin "
                        "WHERE isin LIKE 'INF%'").fetchone()[0]
    con.close()

    print(f"\nsymbol_isin rows : {len(rows):,}")
    print(f"store EQ+BE symbols mapped: {mapped:,} of {store:,} "
          f"({store - mapped:,} unmapped — listed outside both payload eras)")
    print(f"non-equity (INF* ISIN, mutual-fund schemes incl. ETFs): {funds:,}")


if __name__ == "__main__":
    main()
