"""Per-file labelling + contiguity census over the 1m store — PTMS gate C1.

C1's third deliverable: the artifact that makes the vendor/native seam visible
for good. For every per-day file it records the observed first-bar stamp, the
labelling that stamp implies, and every minute of the session that is missing
or extra — so the era rule never has to be rediscovered from scratch, and a
hole cannot hide behind a file that merely exists.

Two things it deliberately does NOT do:

  - it does not guess. A first-bar stamp that is neither the session's open nor
    one minute after it is recorded as REFUSED, with the stamp, and counted as
    a defect (`core.market.bar_labeling`);
  - it does not assume 375 minutes. The expected minute set is built from
    `session_windows`, so a Muhurat hour and a split Saturday are measured
    against their own shape rather than failing a constant.

    python scripts/isd/census_1m_labeling.py                  # whole store
    python scripts/isd/census_1m_labeling.py --from 2023-01-02
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, time, timedelta, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.market.bar_labeling import (  # noqa: E402
    NATIVE, VENDOR, UnknownLabeling, labeling_of,
)
from core.market.session_schedule import CAS_EFFECTIVE, session_windows  # noqa: E402

CANDLES_1M_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
EQUITY_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
OUT_PATH = ROOT / "data" / "isd" / "c1_labeling_census.jsonl"

# cash_cat2 is the widest cash window in both eras: post-CAS it still runs to
# 15:30 while Category I continuous trading stops at 15:15, and the store keeps
# carry-forward bars across that gap.
SEGMENT = "cash_cat2"


def expected_stamps(on: date, labeling: str) -> set:
    """Every minute stamp the session should carry under `labeling`."""
    out = set()
    for start, end in session_windows(SEGMENT, on):
        cur = datetime.combine(on, start)
        stop = datetime.combine(on, end)
        if labeling == VENDOR:          # end-labelled: stamps run start+1 .. end
            cur += timedelta(minutes=1)
            stop += timedelta(minutes=1)
        while cur < stop:
            out.add(cur.time())
            cur += timedelta(minutes=1)
    return out


SYMBOL_FILTERS = {"all": "TRUE", "eq": "symbol LIKE 'NSE_EQ|%'",
                  "index": "symbol LIKE 'NSE_INDEX%'"}


def survey_file(path: Path, on: date, where: str = "TRUE") -> dict:
    con = duckdb.connect(str(path), read_only=True)
    try:
        stamps = [r[0] for r in con.execute(
            f"SELECT DISTINCT CAST(timestamp AS TIME) FROM candles WHERE {where} ORDER BY 1").fetchall()]
        rows, symbols = con.execute(f"SELECT count(*), count(DISTINCT symbol) FROM candles WHERE {where}").fetchone()
        # C3's assertion, not a count: is_synthetic means exactly "CAS auction
        # carry-forward" (core/database/ingestors/db_tick_aggregator.is_carry_forward),
        # which cannot be true of a pre-CAS bar or of one that carries volume.
        # A row marked otherwise is a flag that lies, and a construct filtering
        # on is_synthetic = FALSE silently drops it.
        bad_synthetic = con.execute(
            f"SELECT count(*) FROM candles WHERE {where} AND is_synthetic "
            f"AND (volume > 0 OR DATE '{on.isoformat()}' < DATE '{CAS_EFFECTIVE}' "
            f"     OR symbol NOT LIKE 'NSE_EQ|%')").fetchone()[0]
        misdated = con.execute(
            f"SELECT count(*) FROM candles WHERE {where} "
            f"AND CAST(timestamp AS DATE) <> DATE '{on.isoformat()}'").fetchone()[0]
        eq, idx = con.execute(
            "SELECT count(DISTINCT symbol) FILTER (WHERE symbol LIKE 'NSE_EQ|%'), "
            "       count(DISTINCT symbol) FILTER (WHERE symbol LIKE 'NSE_INDEX%') "
            f"FROM candles WHERE {where}").fetchone()
    finally:
        con.close()

    out = {"session": on.isoformat(), "rows": int(rows), "symbols": int(symbols),
           "eq_symbols": int(eq), "index_symbols": int(idx),
           "misdated": int(misdated), "synthetic_violations": int(bad_synthetic),
           "first": None, "last": None, "minutes": len(stamps)}
    if not stamps:
        return {**out, "class": "EMPTY"}
    out["first"], out["last"] = str(stamps[0]), str(stamps[-1])

    # A row stamped for another date is not a time-of-day question: its minute
    # can sit inside the window and still belong to a different session, so the
    # contiguity classes below would score the file clean. Checked first.
    if misdated:
        out["class"] = "MISDATED"
    try:
        labeling = labeling_of(stamps[0], on, SEGMENT)
    except UnknownLabeling as exc:
        return {**out, "class": "REFUSED", "labeling": None, "reason": str(exc)}

    want = expected_stamps(on, labeling)
    have = set(stamps)
    missing, extra = sorted(want - have), sorted(have - want)
    klass = "OK" if not missing and not extra else ("EXTRA" if extra else "GAP")
    if bad_synthetic:
        klass = "SYNTHETIC_LIES"
    if misdated:
        klass = "MISDATED"
    return {**out, "class": klass, "labeling": labeling,
            "expected_minutes": len(want),
            "missing": [str(m) for m in missing], "extra": [str(e) for e in extra]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="from_date", default="2012-01-01")
    parser.add_argument("--to", dest="to_date", default=None)
    parser.add_argument("--symbols", choices=sorted(SYMBOL_FILTERS), default="all",
                        help="census these symbols only (the 2023-01-31 seam is index-only)")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    lo = date.fromisoformat(args.from_date)
    hi = date.fromisoformat(args.to_date) if args.to_date else date(2100, 1, 1)

    con = duckdb.connect(str(EQUITY_DB), read_only=True)
    try:
        calendar = {r[0] for r in con.execute("SELECT trade_date FROM trading_calendar").fetchall()}
    finally:
        con.close()

    rows, classes, labelings = [], Counter(), Counter()
    for path in sorted(CANDLES_1M_DIR.glob("*.duckdb")):
        on = date.fromisoformat(path.stem)
        if not lo <= on <= hi:
            continue
        row = survey_file(path, on, SYMBOL_FILTERS[args.symbols])
        if on not in calendar:
            row["class"] = "NOT_A_SESSION"
        rows.append(row)
        classes[row["class"]] += 1
        labelings[row.get("labeling")] += 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

    print(f"{len(rows)} files {rows[0]['session']} -> {rows[-1]['session']} -> {args.out}")
    print("  labelling:", dict(labelings))
    print("  classes:  ", dict(classes))
    for row in rows:
        if row["class"] in ("GAP", "EXTRA", "REFUSED", "EMPTY", "NOT_A_SESSION", "MISDATED",
                             "SYNTHETIC_LIES"):
            detail = row.get("reason") or (
                f"{row['misdated']:,} rows stamped for another date" if row["class"] == "MISDATED"
                else f"{row['synthetic_violations']:,} rows marked synthetic that cannot be "
                     f"carry-forward" if row["class"] == "SYNTHETIC_LIES"
                else f"missing {row.get('missing')}" if row["class"] == "GAP"
                else f"extra {row.get('extra')}")
            print(f"  {row['class']:<13} {row['session']} {row['first']}-{row['last']} "
                  f"({row['minutes']} min): {detail}")
    defects = sum(classes[k] for k in ("REFUSED", "EMPTY", "NOT_A_SESSION", "MISDATED",
                                       "SYNTHETIC_LIES"))
    return 1 if defects else 0


if __name__ == "__main__":
    raise SystemExit(main())
