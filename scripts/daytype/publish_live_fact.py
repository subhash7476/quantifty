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
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import duckdb

from scripts.daytype import vix_percentile
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.logging import setup_logger  # noqa: E402
from scripts.daytype.publish_facts import (  # noqa: E402
    CANDLE_DIR_1M, CHECKPOINT, MIN_BARS, TRAINED_ON,
    commit_ref, model_hash, regime_fact_version,
)

logger = setup_logger("publish_live_fact")

LIVE_BUFFER = ROOT / "data" / "live_buffer" / "candles_today.duckdb"

NF_SYMBOL = "NSE_INDEX|Nifty 50"
BN_SYMBOL = "NSE_INDEX|Nifty Bank"
VIX_SYMBOL = "NSE_INDEX|India VIX"

# The ingestor holds candles_today.duckdb in write bursts (cross-process DuckDB
# rule: one RW connection excludes every other opener, even read-only). Readers
# must ride out a burst, and a final failure must be LOUD — a bare except turns
# "we failed" into "the source doesn't have it", which is how the 2026-08-25
# 13:00 fact skipped ten straight publishes while every bar sat in the buffer.
# The original 2 s budget (8 x 0.25 s) was still shorter than the aggregator's
# write bursts over the multi-GB buffer, so 2026-09-01 skipped the 13:00 fact a
# second time (10/10 India VIX reads collided while NF/BN reads landed in free
# windows). Budget is now sized to ride out a full burst while staying inside
# the 1-minute bar cadence of the 13:00->13:10 retry window.
READ_RETRIES = 40
READ_RETRY_DELAY_S = 0.5


def _read_candles(path: Path, symbol: str,
                  retries: int = READ_RETRIES,
                  delay_s: float = READ_RETRY_DELAY_S) -> Optional[pd.DataFrame]:
    """Read one symbol's candles read-only, retrying the transient cross-process
    write-lock. Returns None only after the bound, logging the final error."""
    for attempt in range(retries):
        try:
            con = duckdb.connect(str(path), read_only=True)
            try:
                return con.execute(
                    "SELECT timestamp, open, high, low, close, volume FROM "
                    "candles WHERE symbol = ? ORDER BY timestamp", [symbol],
                ).df()
            finally:
                con.close()
        except Exception as exc:
            if attempt == retries - 1:
                logger.error("bar read from %s (%s) failed after %d attempts: %s",
                             path, symbol, retries, exc)
                return None
            time.sleep(delay_s)
    return None


SESSION_OPEN_MIN = 555                  # 09:15 IST, in minutes from midnight
CHECKPOINT_MIN = 780                    # 13:00 IST


def _session_frame(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Session bars from 09:15 up to and including the first bar at/after 13:00.

    No coverage judgement here — the caller decides acceptance from the returned
    frame (its last bar's minute vs the checkpoint, and its length). This mirrors
    the DayTypeEngine, which fires 13pm on the first bar whose wall-clock time is
    >= 13:00, so a single dropped interior minute is harmless. When no bar reaches
    13:00 the full 09:15-onward frame is returned so the coverage note reports the
    true count and last minute.
    """
    if df is None or df.empty or "timestamp" not in df.columns:
        return None
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    minute = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    sess = df[minute >= SESSION_OPEN_MIN].sort_values("timestamp").reset_index(drop=True)
    if sess.empty:
        return sess
    sess_min = sess["timestamp"].dt.hour * 60 + sess["timestamp"].dt.minute
    reached = sess.index[sess_min >= CHECKPOINT_MIN]
    if len(reached):
        return sess.iloc[: reached[0] + 1].reset_index(drop=True)
    return sess


def _reaches_checkpoint(frame: Optional[pd.DataFrame]) -> bool:
    """True iff the frame's last bar is at/after 13:00 — the engine's wall-clock
    trigger condition. A frame that stops before 13:00 can never fire 13pm, which
    guards the ``13pm``-stamped-from-a-truncated-window fabrication."""
    if frame is None or frame.empty:
        return False
    last = frame["timestamp"].iloc[-1]
    return last.hour * 60 + last.minute >= CHECKPOINT_MIN


def _coverage(frame: Optional[pd.DataFrame]) -> str:
    if frame is None or frame.empty:
        return "0 bars"
    return f"{len(frame)} bars, last {frame['timestamp'].iloc[-1]:%H:%M}"


def _today_bars(symbol: str, today: date,
                diag: Optional[list] = None) -> tuple:
    """Today's session bars from the first source that reaches 13:00.

    Ordered ladder: per-day store, then the live buffer. Returns
    ``(frame, source_label)``.

    A source is accepted iff its session frame REACHES 13:00 (a bar at/after the
    checkpoint exists) AND holds >= MIN_BARS (100) bars -- the exact condition the
    DayTypeEngine needs to fire 13pm (wall-clock trigger, gap-tolerant). Interior
    gaps are tolerated: on 2026-09-03 the live buffer held 225 of 226 bars,
    missing only the interior minute 12:53, and the engine processes that fine.

    A source that does not reach 13:00 is REJECTED and the ladder continues (the
    2026-09-02 partial per-day store stopped at 09:57; the 2026-08-31 late start
    at 11:39 never held the morning). Not-ready names every source and its
    coverage in one line.
    """
    sources = (("per_day_store", CANDLE_DIR_1M / f"{today.isoformat()}.duckdb"),
               ("live_buffer", LIVE_BUFFER))
    for label, path in sources:
        if not path.exists():
            _note(diag, f"{label}: absent")
            continue
        df = _read_candles(path, symbol)
        if df is None:
            _note(diag, f"{label}: unreadable")
            continue
        frame = _session_frame(df)
        n = 0 if frame is None else len(frame)
        if _reaches_checkpoint(frame) and n >= MIN_BARS:
            _note(diag, f"{label}: {_coverage(frame)} -> used")
            return frame, label
        why = ("short of 13:00" if not _reaches_checkpoint(frame)
               else f"only {n} bars < {MIN_BARS}")
        _note(diag, f"{label}: {_coverage(frame)} -- {why}, rejected")
        logger.warning("%s: %s %s for %s (%s); trying next source",
                       symbol, label, why, today, _coverage(frame))
    return None, None


def _note(diag: Optional[list], line: str) -> None:
    if diag is not None and line not in diag:
        diag.append(line)


def vix_at_checkpoint(today: date) -> Optional[float]:
    """Last India VIX 1m close at or before 13:00 (DS2-3).

    Read from the same source ladder used for NF/BN -- never the EOD 1d store
    (which does not exist intraday). None means no source covers the session
    through 13:00; the publisher then writes nothing and the source skips the
    session (F2 NULL-VIX skip, DS2-4).
    """
    df, _ = _today_bars(VIX_SYMBOL, today)
    if df is None or df.empty:
        return None
    return float(df["close"].iloc[-1])


def publish_live(db_path: Path, today: Optional[date] = None) -> dict:
    from core.state.daytype_engine import DayTypeEngine, CHECKPOINT_BARS

    from scripts.daytype.publish_facts import compute_13pm_state

    today = today or date.today()
    diag: list = []
    nf, source = _today_bars(NF_SYMBOL, today, diag)
    bn, _ = _today_bars(BN_SYMBOL, today, diag)

    if nf is None or bn is None:
        # Name every source and its coverage: a skip must be diagnosable from
        # the one journal line, not reconstructed from three sessions of logs.
        return {"ready": False, "session": today,
                "reason": "no source covers 09:15..13:00 ["
                          + "; ".join(diag) + "]"}

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
    # Trailing VIX percentile: NiftyShield's structure gates key on where this
    # session's vol sits in its own recent distribution, not on an absolute
    # level (the absolute 14/16 gates stopped firing when India VIX compressed).
    con.execute(
        "ALTER TABLE day_type_facts ADD COLUMN IF NOT EXISTS vix_pctile DOUBLE"
    )
    vix_pct = vix_percentile.percentile(vix_cp, today)
    con.execute(
        "INSERT OR REPLACE INTO day_type_facts "
        "(session_date, checkpoint, regime, regime_confidence, vix_close, "
        " vix_at_checkpoint, vix_pctile, regime_fact_version, model_hash, "
        " produced_by, trained_on) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [today, CHECKPOINT, st["predicted_state"], float(st["confidence"]),
         None, vix_cp, vix_pct, ver, hash_val, produced_by, TRAINED_ON],
    )
    con.close()
    return {"ready": True, "session": today, "regime": st["predicted_state"],
            "confidence": st["confidence"], "vix_at_checkpoint": vix_cp,
            "vix_pctile": vix_pct,
            "produced_by": produced_by, "source": source}


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
