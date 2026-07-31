"""Trading-day inference and the EOD retry decision.

No holiday list exists in this repo and `trading_calendar` is derived from the
downloads themselves, so trading-day status is inferred from whether any of the
four independent NSE feeds published data for today.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "market_data"

GRACE_HOUR = 21
MAX_ATTEMPTS = 8

FEED_STORES = {
    "equity": (DATA / "equity_bhavcopy.duckdb", "equity_bhavcopy"),
    "futures": (DATA / "futures_bhavcopy.duckdb", "futures_bhavcopy"),
    "stock_options": (DATA / "stock_options_bhavcopy.duckdb", "stock_options_bhavcopy"),
}
INDEX_1D_DIR = DATA / "nse" / "candles" / "1d"


@dataclass(frozen=True)
class Decision:
    action: str  # "chain" | "retry" | "holiday" | "exhausted"
    reason: str


def _max_trade_date(db_path: Path, table: str) -> date | None:
    if not db_path.exists():
        return None
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        names = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if table not in names:
            return None
        return con.execute(f"SELECT MAX(trade_date) FROM {table}").fetchone()[0]
    finally:
        con.close()


def _max_index_date() -> date | None:
    if not INDEX_1D_DIR.exists():
        return None
    stems = [f.stem for f in INDEX_1D_DIR.glob("*.duckdb")]
    return max((date.fromisoformat(s) for s in stems), default=None)


def probe_feeds() -> dict[str, date | None]:
    feeds = {name: _max_trade_date(path, table) for name, (path, table) in FEED_STORES.items()}
    feeds["index"] = _max_index_date()
    return feeds


def decide(feeds: dict[str, date | None], today: date, now: datetime, attempt: int) -> Decision:
    fresh = [name for name, d in feeds.items() if d == today]

    if feeds.get("futures") == today:
        return Decision("chain", f"futures published {today}")

    if attempt >= MAX_ATTEMPTS:
        return Decision("exhausted", f"no futures data after {attempt} attempts (fresh: {fresh or 'none'})")

    if fresh:
        return Decision("retry", f"trading day confirmed by {', '.join(sorted(fresh))}; futures not yet published")

    if now.hour >= GRACE_HOUR:
        return Decision("holiday", f"no feed published {today} by {now:%H:%M} — treating as non-trading day")

    return Decision("retry", f"no feed published {today} yet; before {GRACE_HOUR}:00 grace cutoff")
