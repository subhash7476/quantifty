from datetime import datetime

import duckdb

from scripts.isd.gate_contiguity import audit_session

SYM = "NSE_EQ|INE002A01018"


def test_audit_counts_synthetic_bars_separately(tmp_path):
    path = tmp_path / "2026-08-24.duckdb"
    con = duckdb.connect(str(path))
    con.execute(
        "CREATE TABLE candles (symbol VARCHAR, instrument_key VARCHAR, "
        "timeframe VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE, "
        "low DOUBLE, close DOUBLE, volume BIGINT, is_synthetic BOOLEAN)"
    )
    con.executemany(
        "INSERT INTO candles VALUES (?, '', '1m', ?, 1.0, 1.0, 1.0, 1.0, ?, ?)",
        [(SYM, datetime(2026, 8, 24, 15, 14), 100, False),
         (SYM, datetime(2026, 8, 24, 15, 20), 0, True),
         (SYM, datetime(2026, 8, 24, 15, 21), 0, True)],
    )
    con.close()

    result = audit_session(path, "2026-08-24")

    assert result["synthetic_bars"] == 2
    assert result["tradeable_slots"] == 1
