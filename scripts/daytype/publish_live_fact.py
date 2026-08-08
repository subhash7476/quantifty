"""DayType — live 13:00 regime-fact publisher (DAYTYPE_FACTS_ADOPTION_SPEC §2).

Produces *today's* 13pm regime fact from that session's Nifty + Bank-Nifty 1m
bars up to 13:00, and upserts it into the shared facts table with
produced_by=live@<commit>. Reuses the offline publisher's engine path — the
same DayTypeEngine and the same feature pipeline, so a live fact is byte-for-byte
comparable with an offline fact for the same session bars (spec §5).

Intraday VIX (DS2-3): the live fact carries the session's ~13:00 India VIX in the
distinct nullable `vix_at_checkpoint` column, read from the India VIX 1m series
exactly as NF/BN are (last 1m close at or before 13:00) — never from the EOD 1d
store, which does not exist intraday. The legacy `vix_close` column keeps its EOD
meaning and is NULL on live rows (its meaning never depends on `produced_by`).

Data source: the per-day 1m store for today if present; else the live buffer
(candles_today.duckdb). Requires >= MIN_BARS session bars up to 13:00, else it
reports "not ready" and writes nothing (a Stage-2 gate, not an error).

Also exposes `make_driver_hook()` — the per-session pre-signal seam (DS2-2) that
wires `publish_live` into the LoopDriver's tick so the fact is written before the
source's `on_bar` reads it.

Usage:
  python scripts/daytype/publish_live_fact.py
  python scripts/daytype/publish_live_fact.py --db /tmp/facts.duckdb
Output: upsert into data/features/day_type/day_type_facts.duckdb (override --db)
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.daytype.publish_facts import (  # noqa: E402
    CANDLE_DIR_1M, CHECKPOINT, MIN_BARS, TRAINED_ON,
    commit_ref, model_hash, regime_fact_version,
)

LIVE_BUFFER = ROOT / "data" / "live_buffer" / "candles_today.duckdb"

NF_SYMBOL = "NSE_INDEX|Nifty 50"
BN_SYMBOL = "NSE_INDEX|Nifty Bank"
VIX_SYMBOL = "NSE_INDEX|India VIX"


def _session_bars_from_df(df: pd.DataFrame, upto_min: int = 780) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    if "timestamp" not in df.columns:
        return None
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    hour_min = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    df = df[(hour_min >= 555) & (hour_min <= upto_min)].reset_index(drop=True)
    return df if len(df) >= MIN_BARS else None


def _today_bars(symbol: str, today: date) -> Optional[pd.DataFrame]:
    """Today's session bars: per-day store first, then the live buffer."""
    db_path = CANDLE_DIR_1M / f"{today.isoformat()}.duckdb"
    if db_path.exists():
        try:
            con = duckdb.connect(str(db_path), read_only=True)
            df = con.execute(
                "SELECT timestamp, open, high, low, close, volume FROM candles "
                "WHERE symbol = ? ORDER BY timestamp",
                [symbol],
            ).df()
            con.close()
            return _session_bars_from_df(df)
        except Exception:
            pass

    if LIVE_BUFFER.exists():
        try:
            con = duckdb.connect(str(LIVE_BUFFER), read_only=True)
            df = con.execute(
                "SELECT timestamp, open, high, low, close, volume FROM candles "
                "WHERE symbol = ? ORDER BY timestamp",
                [symbol],
            ).df()
            con.close()
            return _session_bars_from_df(df)
        except Exception:
            pass

    return None


def vix_at_checkpoint(today: date) -> Optional[float]:
    """Last India VIX 1m close at or before 13:00 (DS2-3).

    Read from the same live/per-day 1m source used for NF/BN — never the EOD
    1d store (which does not exist intraday). `_today_bars` filters to
    9:15..13:00 and requires >= MIN_BARS, so None means the VIX feed is
    missing/thin — the publisher then writes nothing and the source skips the
    session (F2 NULL-VIX skip, DS2-4).
    """
    df = _today_bars(VIX_SYMBOL, today)
    if df is None or df.empty:
        return None
    return float(df["close"].iloc[-1])


def publish_live(db_path: Path, today: Optional[date] = None) -> dict:
    from core.state.daytype_engine import DayTypeEngine, CHECKPOINT_BARS

    from scripts.daytype.publish_facts import compute_13pm_state

    today = today or date.today()
    nf = _today_bars(NF_SYMBOL, today)
    bn = _today_bars(BN_SYMBOL, today)

    if nf is None or bn is None:
        return {"ready": False, "reason": "insufficient bars up to 13:00", "session": today}

    st = compute_13pm_state(today, nf, bn)
    if st is None or st.get("predicted_state") == "Unknown":
        return {"ready": False, "reason": "no 13pm checkpoint produced", "session": today}

    produced_by = f"live@{commit_ref()}"
    vix_cp = vix_at_checkpoint(today)
    if vix_cp is None:
        return {"ready": False, "reason": "no India VIX at 13:00 for session", "session": today}
    hash_val = model_hash()
    ver = regime_fact_version()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute("""
        CREATE TABLE IF NOT EXISTS day_type_facts (
            session_date        DATE    NOT NULL,
            checkpoint          VARCHAR NOT NULL,
            regime              VARCHAR NOT NULL,
            regime_confidence   DOUBLE  NOT NULL,
            vix_close           DOUBLE,
            vix_at_checkpoint   DOUBLE,
            regime_fact_version VARCHAR NOT NULL,
            model_hash          VARCHAR NOT NULL,
            produced_by         VARCHAR NOT NULL,
            trained_on          VARCHAR NOT NULL,
            PRIMARY KEY (session_date, checkpoint)
        )
    """)
    # Migration for stores created before DS2-3.
    con.execute(
        "ALTER TABLE day_type_facts ADD COLUMN IF NOT EXISTS vix_at_checkpoint DOUBLE"
    )
    con.execute(
        "INSERT OR REPLACE INTO day_type_facts "
        "(session_date, checkpoint, regime, regime_confidence, vix_close, "
        " vix_at_checkpoint, regime_fact_version, model_hash, produced_by, trained_on) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [today, CHECKPOINT, st["predicted_state"], float(st["confidence"]),
         None, vix_cp, ver, hash_val, produced_by, TRAINED_ON],
    )
    con.close()
    return {"ready": True, "session": today, "regime": st["predicted_state"],
            "confidence": st["confidence"], "vix_at_checkpoint": vix_cp,
            "produced_by": produced_by}


def make_driver_hook(db_path: Path, today: Optional[date] = None):
    """Return the per-session pre-signal publish hook for LoopDriver (DS2-2).

    The returned callable takes the checkpoint bar's timestamp and publishes
    that session's 13pm live fact (INSERT OR REPLACE — idempotent). The driver
    invokes it once per session at/after the 13:00 tick, before on_bar; a
    not-ready result means the source reads no fact and skips the session
    (DS2-4). `today` is injectable for deterministic tests; the hook's return
    value is the publish result dict so a wrapper can journal a skipped-entry
    line.
    """
    def hook(bar_timestamp: datetime) -> Optional[dict]:
        session = today or bar_timestamp.date()
        return publish_live(Path(db_path), today=session)
    return hook


def main() -> int:
    parser = argparse.ArgumentParser(description="DayType live 13:00 regime-fact publisher")
    parser.add_argument("--db", default=str(ROOT / "data" / "features" / "day_type" / "day_type_facts.duckdb"))
    parser.add_argument("--date", default=None, help="Session date override (YYYY-MM-DD), default today")
    args = parser.parse_args()

    today = date.fromisoformat(args.date) if args.date else date.today()
    result = publish_live(Path(args.db), today=today)

    if not result["ready"]:
        print(f"NOT READY: {result['session']} — {result['reason']}")
        return 2
    print(f"LIVE FACT {result['session']}: {result['regime']} "
          f"conf={result['confidence']:.3f} vix_at_checkpoint={result['vix_at_checkpoint']} "
          f"({result['produced_by']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
