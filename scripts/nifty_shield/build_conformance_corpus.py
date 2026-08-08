"""Build the committed nifty_shield_v1 conformance corpus fixtures.

Extracts Nifty 50 1m bars + the matching 13pm regime/VIX facts for a fixed set
of sessions from the local store and writes them to the strategy package's
committed corpus dir. Deterministic and re-runnable; the committed CSVs are the
named, recorded corpus the Stage-1 conformance suite drives.

Sessions chosen: 2023-01-02..01-06 + 2023-01-09 — covering Choppy (iron_fly),
BearTrend (bear_call_spread) and BullTrend (bull_put_spread), all with
VIX < vix_skip_above so entry fires. This is index 1m bars + facts, NOT an
option-mark backtest — the OSC index-options window is untouched.

Usage: python scripts/nifty_shield/build_conformance_corpus.py
Output:
  strategies/nifty_shield_v1/corpus/bars.csv
  strategies/nifty_shield_v1/corpus/facts.csv
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CANDLE_DIR_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
FACTS_DB = ROOT / "data" / "features" / "day_type" / "day_type_facts.duckdb"
OUT_DIR = ROOT / "strategies" / "nifty_shield_v1" / "corpus"

NF_SYMBOL = "NSE_INDEX|Nifty 50"

SESSIONS = [
    date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4),
    date(2023, 1, 5), date(2023, 1, 6), date(2023, 1, 9),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    bar_rows = []
    for d in SESSIONS:
        db_path = CANDLE_DIR_1M / f"{d.isoformat()}.duckdb"
        if not db_path.exists():
            print(f"MISSING 1m store: {db_path}")
            return 1
        con = duckdb.connect(str(db_path), read_only=True)
        rows = con.execute(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol = ? ORDER BY timestamp", [NF_SYMBOL]).fetchall()
        con.close()
        for r in rows:
            bar_rows.append((d.isoformat(), r[0], r[1], r[2], r[3], r[4], int(r[5] or 0)))
        print(f"  {d}: {len(rows)} bars")

    if not FACTS_DB.exists():
        print(f"MISSING facts DB: {FACTS_DB}")
        return 1
    con = duckdb.connect(str(FACTS_DB), read_only=True)
    fact_rows = con.execute(
        "SELECT session_date, checkpoint, regime, regime_confidence, vix_close, "
        "       regime_fact_version, model_hash, produced_by, trained_on "
        "FROM day_type_facts "
        "WHERE checkpoint = '13pm' AND session_date IN ("
        + ",".join(f"'{d.isoformat()}'" for d in SESSIONS) + ") "
        "ORDER BY session_date"
    ).fetchall()
    con.close()

    with open(OUT_DIR / "bars.csv", "w", encoding="utf-8") as f:
        f.write("session_date,timestamp,open,high,low,close,volume\n")
        for r in bar_rows:
            f.write(",".join(str(x) for x in r) + "\n")
    with open(OUT_DIR / "facts.csv", "w", encoding="utf-8") as f:
        f.write("session_date,checkpoint,regime,regime_confidence,vix_close,"
                "regime_fact_version,model_hash,produced_by,trained_on\n")
        for r in fact_rows:
            f.write(",".join(str(x) for x in r) + "\n")

    print(f"bars:   {len(bar_rows)} rows -> {OUT_DIR / 'bars.csv'}")
    print(f"facts:  {len(fact_rows)} rows -> {OUT_DIR / 'facts.csv'}")
    for r in fact_rows:
        print(f"  {r[0]} {r[2]} conf={r[3]} vix={r[4]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
