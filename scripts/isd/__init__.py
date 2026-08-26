"""ISD — Intraday-Stocks Discovery program (Phase 1 substrate certification).

Implements the APPROVED spec `docs/superpowers/specs/
2026-08-24-intraday-stocks-discovery-design.md` and its plan
`docs/superpowers/plans/2026-08-24-isd-phase-1-substrate-certification.md`.

Read-only over native market-data stores; derived artifacts land under
data/isd/ (gitignored) and the certification report under docs/reports/.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

NATIVE_1M_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
VENDOR_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m_vendor"
ISD_DATA_DIR = ROOT / "data" / "isd"
REPORT_DIR = ROOT / "docs" / "reports"

EQUITY_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
FUTURES_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
VENDOR_ZIP = Path.home() / "Downloads" / "archive.zip"

# Canonical paper capital (operator decision Q4, spec §10) — defined in the
# cost model so model and sizing basis ship together; re-exported here.
from core.execution.equity.intraday_fees import CANONICAL_CAPITAL  # noqa: E402,F401

# Regular session grid, minutes-of-day inclusive: 09:15 .. 15:29 (375 slots).
SESSION_FIRST_MIN = 9 * 60 + 15
SESSION_LAST_MIN = 15 * 60 + 29
SESSION_SLOTS = SESSION_LAST_MIN - SESSION_FIRST_MIN + 1

EQ_PREFIX = "NSE_EQ|"


def connect_ro(path, retries: int = 8, delay_s: float = 0.5):
    """Read-only DuckDB connect with bounded retry.

    Ops workers legitimately hold stores read-write in the evening (EOD chain);
    DuckDB's single-writer rule then blocks even readers. Retry transient
    sharing violations; surface the cause in the final raise so a persistently
    blocked run names it instead of crashing cryptically.
    """
    import time
    last = None
    for attempt in range(retries):
        try:
            import duckdb
            return duckdb.connect(str(path), read_only=True)
        except Exception as exc:
            last = exc
            msg = str(exc)
            transient = ("being used by another process" in msg
                         or "Conflicting lock" in msg
                         or "Cannot open file" in msg)
            if not transient or attempt == retries - 1:
                raise RuntimeError(
                    f"cannot open {path} read-only after {retries} attempts "
                    f"(ops worker holding the store?): {msg}") from exc
            time.sleep(delay_s)
    raise RuntimeError(f"unreachable: {last}")


def eq_sessions(start: str = "2023-01-02"):
    """(session_iso, path) for every native per-day file from `start` onward
    carrying NSE_EQ bars, sorted by session date.

    Pre-2023 files are index-only (measured); probing them wastes ~2700
    connections on a full-tree scan.
    """
    out = []
    for p in sorted(NATIVE_1M_DIR.glob("*.duckdb")):
        if p.stem < start:
            continue
        con = connect_ro(p)
        try:
            n_eq = con.execute(
                "select count(*) from candles where symbol like 'NSE_EQ%'"
            ).fetchone()[0]
        finally:
            con.close()
        if n_eq > 0:
            out.append((p.stem, p))
    return out
