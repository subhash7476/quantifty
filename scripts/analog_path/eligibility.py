"""Eligible-day build + integrity scan + defect register.

The eligible universe is rule-driven (config.eligibility + the frozen
session-validity checks in data_layer.load_session); nothing is hand-picked.
Outputs (persisted under data/analog_path/, git-ignored, reproducible):
  eligible_days.csv      — one row per eligible date, with fence + era
  defect_register.json   — append-only register of defect classes found
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from scripts.analog_path import config
from scripts.analog_path.data_layer import CANDLE_DIR_1M, load_session

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "analog_path"
ELIGIBLE_PATH = DATA_DIR / "eligible_days.csv"
DEFECT_PATH = DATA_DIR / "defect_register.json"


def _calendar_dates(lo: date, hi: date) -> list[date]:
    out = []
    d = lo
    while d <= hi:
        out.append(d)
        d += timedelta(days=1)
    return out


def build_eligible_days(start: date | None = None, end: date | None = None) -> dict:
    """Scan [start, end] (default full span 2012-01-01..today). Returns summary
    counts; persists eligible list + register for the scanned range."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    start = start or date(2012, 1, 1)
    end = end or date.today()
    dates = _calendar_dates(start, end)

    eligible: list[tuple[date, str, str]] = []
    defect_counter: Counter = Counter()
    missing_files: list[str] = []
    new_defects: list[dict] = []

    for d in dates:
        if not (CANDLE_DIR_1M / f"{d.isoformat()}.duckdb").exists():
            continue  # non-trading days and permanent holes: absence of a file is not a defect
        sess = load_session(d)
        if sess is None:
            missing_files.append(d.isoformat())
            continue
        if sess.valid:
            eligible.append((d, config.era_of(d), config.fence_of(d)))
        else:
            for code in sess.defects:
                defect_counter[code] += 1
            new_defects.append({"date": d.isoformat(), "defects": sess.defects})

    with open(ELIGIBLE_PATH, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "era", "fence"])
        for row in eligible:
            w.writerow(row)

    register = {
        "generated": date.today().isoformat(),
        "eligibility_rule": config.CONFIG["eligibility"],
        "eligible_count": len(eligible),
        "defect_class_counts": dict(defect_counter),
        "sessions_with_defects": new_defects,
    }
    with open(DEFECT_PATH, "w") as fh:
        json.dump(register, fh, indent=1)

    by_fence: Counter = Counter()
    by_era: Counter = Counter()
    for _, era, fence in eligible:
        by_fence[fence] += 1
        by_era[era] += 1
    return {"eligible": len(eligible), "by_fence": dict(by_fence),
            "by_era": dict(by_era), "defects": dict(defect_counter),
            "defect_sessions": len(new_defects), "missing_files": missing_files}


def load_eligible_dates(fence: str | None = None) -> list[date]:
    """Read the persisted eligible list, optionally fence-filtered."""
    if not ELIGIBLE_PATH.exists():
        raise FileNotFoundError(
            f"{ELIGIBLE_PATH} missing — run build_eligible_days() first")
    out = []
    with open(ELIGIBLE_PATH, newline="") as fh:
        for row in csv.DictReader(fh):
            d = date.fromisoformat(row["date"])
            if fence is None or row["fence"] == fence:
                out.append(d)
    return out
