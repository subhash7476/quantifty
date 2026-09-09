"""Trailing India VIX percentile, with an incremental local cache.

NiftyShield's structure-selection gates key on where today's India VIX sits in
its own recent distribution rather than on an absolute level, so the 13pm fact
publisher needs a trailing window at publish time. Scanning the 1d candle store
(one DuckDB file per session) costs minutes; doing that inside the intraday
publisher would block the driver hook.

So the series is cached in a single small store and topped up incrementally:
`refresh()` populates it from the 1d store and later runs append only the
sessions it does not already hold.

**`percentile()` never refreshes.** Reading a fact must not scan the candle
store or write to a shared file as a side effect: it would put minutes of file
IO inside the intraday driver hook, and it made a unit-test run mutate a
production data path. `refresh()` is an explicit maintenance step for the EOD
chain (`python -m scripts.daytype.vix_percentile`). A cache that is absent or
too short yields None, which the strategy treats as "gate unavailable" and
resolves to its calmest branch — the same graceful-absence contract
`vix_at_checkpoint` already uses.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DAILY_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
CACHE = ROOT / "data" / "nifty_shield" / "vix_history.duckdb"
VIX_SYMBOL = "NSE_INDEX|India VIX"


def _ensure_table(con) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS vix_history ("
                "session_date DATE PRIMARY KEY, vix_close DOUBLE NOT NULL)")


def refresh(upto: Optional[date] = None) -> int:
    """Top the cache up from the 1d store. Returns rows added."""
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(CACHE))
    try:
        _ensure_table(con)
        have = {r[0] for r in con.execute(
            "SELECT session_date FROM vix_history").fetchall()}
        added = 0
        for p in sorted(DAILY_DIR.glob("*.duckdb")):
            try:
                d = date.fromisoformat(p.stem)
            except ValueError:
                continue
            if d in have or (upto is not None and d > upto):
                continue
            try:
                src = duckdb.connect(str(p), read_only=True)
                row = src.execute("SELECT close FROM candles WHERE symbol = ? "
                                  "LIMIT 1", [VIX_SYMBOL]).fetchone()
                src.close()
            except duckdb.Error:
                continue
            if row is None or row[0] is None or float(row[0]) <= 0:
                continue
            con.execute("INSERT OR REPLACE INTO vix_history VALUES (?, ?)",
                        [d, float(row[0])])
            added += 1
        return added
    finally:
        con.close()


def percentile(vix_value: float, asof: date, lookback_sessions: int = 756,
               cache_path: Optional[Path] = None) -> Optional[float]:
    """Percentile of `vix_value` within the trailing window ending before `asof`.

    The window excludes `asof` itself, so the gate compares today's vol against
    history rather than against a window it is already part of. Returns None
    when fewer than a quarter of the requested sessions are available — a
    percentile off a short window is a number without a meaning, and the caller
    treats None as "gate unavailable" rather than substituting a default.
    """
    path = Path(cache_path) if cache_path is not None else CACHE
    if not path.exists():
        return None
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute(
            "SELECT vix_close FROM vix_history WHERE session_date < ? "
            "ORDER BY session_date DESC LIMIT ?",
            [asof, int(lookback_sessions)]).fetchall()
    finally:
        con.close()
    vals = [float(r[0]) for r in rows]
    if len(vals) < max(30, lookback_sessions // 4):
        return None
    below = sum(1 for v in vals if v < float(vix_value))
    return round(below / len(vals) * 100.0, 2)


def main() -> int:
    """Maintenance entry point: top the cache up. Run from the EOD chain."""
    added = refresh()
    print(f"vix_history cache: {added} session(s) added -> {CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
