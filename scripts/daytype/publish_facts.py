"""DayType — offline regime-fact publisher (DAYTYPE_FACTS_ADOPTION_SPEC §2/§4).

Batches a bar-corpus date range into per-session 13pm regime facts, written to
a DuckDB facts table keyed by session_date. Every row carries the provenance
triple (model_hash, regime_fact_version, trained_on) plus the producing mode and
commit ref, so a Stage-1 replay is reproducible from the recorded model + this
committed publisher.

Classification runs here (the publisher), never in a strategy's runtime
(Principle #2; spec §5). 13pm only (DT5) — AM checkpoints are ignored.

Usage:
  python scripts/daytype/publish_facts.py
  python scripts/daytype/publish_facts.py --start 2023-01-01 --end 2023-12-31
  python scripts/daytype/publish_facts.py --db /tmp/facts.duckdb
Output: data/features/day_type/day_type_facts.duckdb (override with --db)
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.state.daytype_engine import DayTypeEngine, CHECKPOINT_BARS, MIN_BARS_REQUIRED

CANDLE_DIR_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
CANDLE_DIR_1D = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
FACTS_DB = ROOT / "data" / "features" / "day_type" / "day_type_facts.duckdb"

NF_SYMBOL = "NSE_INDEX|Nifty 50"
BN_SYMBOL = "NSE_INDEX|Nifty Bank"
VIX_SYMBOL = "NSE_INDEX|India VIX"

CHECKPOINT = "13pm"
TARGET_BAR = CHECKPOINT_BARS[CHECKPOINT]          # 225 (bars 0..224 used by the model)
MIN_BARS = MIN_BARS_REQUIRED[CHECKPOINT]          # 100

# Standing model provenance (operator-directed 2026-08-07; spec §4 trained_on).
TRAINED_ON = r"D:\BOT\root vintage — NOT F:\nifty data"

# Model dir resolved by the engine's hard path (core/state -> models/daytype).
MODEL_DIR = ROOT / "models" / "daytype" / "logistic_13pm_prod"
MODEL_FILES = ("model.pkl", "scaler.pkl", "metadata.json")


def model_hash() -> str:
    """SHA-256 over the 13pm model's three files, in fixed order (DT4)."""
    h = hashlib.sha256()
    for name in MODEL_FILES:
        data = (MODEL_DIR / name).read_bytes()
        h.update(name.encode("utf-8"))
        h.update(data)
    return h.hexdigest()


def regime_fact_version() -> str:
    """Version string from the 13pm model metadata, prefixed dt- (DT4)."""
    import json
    meta = json.loads((MODEL_DIR / "metadata.json").read_text(encoding="utf-8"))
    return f"dt-{meta.get('version', 'unknown')}"


def commit_ref() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
        return out or "no-commit"
    except Exception:
        return "no-commit"


def _session_bars(d: date, symbol: str, upto_min: int = 780) -> Optional[pd.DataFrame]:
    """Load 1m bars for a session, filtered to 9:15..13:00 (555..780 min)."""
    db_path = CANDLE_DIR_1M / f"{d.isoformat()}.duckdb"
    if not db_path.exists():
        return None
    try:
        con = duckdb.connect(str(db_path), read_only=True)
        df = con.execute(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol = ? ORDER BY timestamp",
            [symbol],
        ).df()
        con.close()
    except Exception:
        return None
    if df.empty:
        return None
    hour_min = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    df = df[(hour_min >= 555) & (hour_min <= upto_min)].reset_index(drop=True)
    return df


def compute_13pm_state(d: date, nf: pd.DataFrame, bn: pd.DataFrame) -> Optional[dict]:
    """Feed NF/BN bars through the engine; return the 13pm DayTypeState dict."""
    eng = DayTypeEngine(lock_threshold=1.01)
    eng.reset(d)

    n = min(len(nf), len(bn), TARGET_BAR + 1)   # 226 bars through 13:00 inclusive
    if n < MIN_BARS:
        return None
    nf = nf.head(n).reset_index(drop=True)
    bn = bn.head(n).reset_index(drop=True)

    result = None
    for i in range(n):
        eng.on_bn_bar(bn.iloc[i].to_dict())
        st = eng.on_bar(nf.iloc[i].to_dict())
        if st is not None and st.checkpoint == CHECKPOINT:
            result = st
    return result.to_dict() if result is not None else None


def vix_close(d: date) -> Optional[float]:
    db_path = CANDLE_DIR_1D / f"{d.isoformat()}.duckdb"
    if not db_path.exists():
        return None
    try:
        con = duckdb.connect(str(db_path), read_only=True)
        row = con.execute(
            "SELECT close FROM candles WHERE symbol = ? LIMIT 1", [VIX_SYMBOL]
        ).fetchone()
        con.close()
    except Exception:
        return None
    return float(row[0]) if row else None


def _existing_dates(db_path: Path) -> set:
    if not db_path.exists():
        return set()
    con = duckdb.connect(str(db_path), read_only=True)
    rows = con.execute(
        "SELECT session_date FROM day_type_facts WHERE checkpoint = ?", [CHECKPOINT]
    ).fetchall()
    con.close()
    return {r[0] for r in rows}


def _schema(con) -> None:
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
    # Migration for stores created before DS2-3: the offline publisher never
    # writes vix_at_checkpoint (EOD vix_close keeps its meaning, DS2-3); the
    # column exists so live rows can carry the intraday 13:00 India VIX.
    con.execute(
        "ALTER TABLE day_type_facts ADD COLUMN IF NOT EXISTS vix_at_checkpoint DOUBLE"
    )


def publish(start: date, end: date, db_path: Path, produced_by: str,
            dates_only: Optional[set] = None, progress_every: int = 100) -> dict:
    """Batch regime facts over the date range; returns summary counts."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    hash_val = model_hash()
    ver = regime_fact_version()
    existing = _existing_dates(db_path)

    rows: List[tuple] = []
    skipped_no_data = 0
    skipped_no_state = 0
    skipped_no_vix = 0

    days = sorted(
        d for d in (start + timedelta(n) for n in range((end - start).days + 1))
        if (CANDLE_DIR_1M / f"{d.isoformat()}.duckdb").exists()
    )
    for idx, d in enumerate(days):
        if dates_only is not None and d not in dates_only:
            continue
        if d in existing:
            continue

        nf = _session_bars(d, NF_SYMBOL)
        bn = _session_bars(d, BN_SYMBOL)
        if nf is None or bn is None or len(nf) < MIN_BARS or len(bn) < MIN_BARS:
            skipped_no_data += 1
            continue

        st = compute_13pm_state(d, nf, bn)
        if st is None or st.get("predicted_state") == "Unknown":
            skipped_no_state += 1
            continue

        vix = vix_close(d)
        if vix is None:
            skipped_no_vix += 1
            continue

        rows.append((
            d, CHECKPOINT, st["predicted_state"], float(st["confidence"]),
            vix, ver, hash_val, produced_by, TRAINED_ON,
        ))
        if progress_every and (len(rows) + skipped_no_data + skipped_no_state) % progress_every == 0:
            print(f"    ... {d} ({st['predicted_state']} conf={st['confidence']:.3f})")

    con = duckdb.connect(str(db_path))
    _schema(con)
    if rows:
        con.executemany(
            "INSERT OR REPLACE INTO day_type_facts "
            "(session_date, checkpoint, regime, regime_confidence, vix_close, "
            " regime_fact_version, model_hash, produced_by, trained_on) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    total = con.execute("SELECT COUNT(*) FROM day_type_facts").fetchone()[0]
    n_sess = con.execute(
        "SELECT COUNT(DISTINCT session_date) FROM day_type_facts WHERE checkpoint = ?",
        [CHECKPOINT],
    ).fetchone()[0]
    con.close()

    return {
        "new_rows": len(rows), "total_rows": total, "sessions": n_sess,
        "skipped_no_data": skipped_no_data, "skipped_no_state": skipped_no_state,
        "skipped_no_vix": skipped_no_vix, "model_hash": hash_val, "version": ver,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DayType offline regime-fact publisher")
    parser.add_argument("--start", default="2023-01-02", help="Start date (inclusive)")
    parser.add_argument("--end", default="2026-07-03", help="End date (inclusive)")
    parser.add_argument("--db", default=str(FACTS_DB), help="Output DuckDB path")
    parser.add_argument("--produced-by", default="offline", choices=["offline", "live"])
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    produced_by = f"{args.produced_by}@{commit_ref()}"

    print(f"DayType offline facts publisher")
    print(f"  Range:      {start} -> {end}")
    print(f"  Model:      {MODEL_DIR}")
    print(f"  model_hash: {model_hash()}")
    print(f"  version:    {regime_fact_version()}")
    print(f"  Output:     {args.db}")
    print(f"  produced_by: {produced_by}")

    summary = publish(start, end, Path(args.db), produced_by)
    print("\nDone:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
