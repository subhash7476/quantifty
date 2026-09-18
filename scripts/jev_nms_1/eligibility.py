"""JEV-NMS-1 §28 step 1 — mechanical eligibility construction.

Applies protocol §4 items 1-9 exactly as bound by Amendment 2 §A2-7 to every
calendar session of D-fit, D-eval and H-exposed (A2-2: nothing outside a
defined set is evaluated). No draws, no fitting, no Jev calls.

Item 5 "strictly monotonic" is chronological timestamp monotonicity
(operator ruling 2026-09-18): the session's timestamps, taken in ascending
time order, must strictly increase and contain each of the 345 window minutes
exactly once. Physical DuckDB row order is not part of eligibility and is
never read.

Where a frozen phrase admits more than one mechanical reading (item 6
"consistent OHLC", item 7 "run ... unchanged close"), every reading is
evaluated and the outcome is accepted only if all readings agree on every
session; any disagreement raises ContractStop and no artifact is written.

The artifact is append-only: it is created exclusively and never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import duckdb

from core.market.bar_labeling import NATIVE, UnknownLabeling, labeling_of
from core.market.nse_holidays import NSE_HOLIDAYS
from core.market.session_schedule import SPECIAL_SESSIONS
from core.market.trading_calendar import OutsideCoverage, is_session, previous_session

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "governance" / "jev_nms_1" / "config.json"
ADDENDUM = REPO / "governance" / "jev_nms_1" / "config_amendment_2.json"
# A2 freeze record (JEV_NMS_1_A2_FREEZE_RECORD.md).
EXPECTED_ADDENDUM_SHA256 = "b9640bf22d2f1d53ca913654863280fa54087db00c2cd26675c1343ca9395484"

SYMBOL = "NSE_INDEX|Nifty 50"
OPEN = time(9, 15)
LAST_WINDOW_BAR = time(14, 59)
PRE_CLOSE = time(15, 0)
PREV_CLOSE_BAR = time(15, 29)
WINDOW_MINUTES = 345
ARTIFACT_NAME = "eligibility_step1.json"


class ContractStop(RuntimeError):
    """A result needs a ruling rather than mechanical application."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_seal() -> tuple[dict, dict]:
    if sha256_file(ADDENDUM) != EXPECTED_ADDENDUM_SHA256:
        raise ContractStop("config_amendment_2.json does not match the A2 freeze record")
    addendum = json.loads(ADDENDUM.read_text(encoding="utf-8"))
    for key in ("f1_configuration", "protocol_document", "amendment_2"):
        ref = addendum[key]
        if sha256_file(REPO / ref["file"]) != ref["sha256"]:
            raise ContractStop(f"{ref['file']} does not match its A2 reference")
    return json.loads(CONFIG.read_text(encoding="utf-8")), addendum


def sessions_between(lo: date, hi: date) -> list[date]:
    out, d = [], lo
    while d <= hi:
        if is_session(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def populations(config: dict, addendum: dict) -> dict[str, list[date]]:
    sets = config["sets"]
    f1 = date.fromisoformat(addendum["f1_date"])
    return {
        "d_fit": sessions_between(*(date.fromisoformat(x) for x in sets["d_fit"])),
        "d_eval": sessions_between(*(date.fromisoformat(x) for x in sets["d_eval"])),
        # H-exposed: 2026-01-01 -> the last session dated <= F1.
        "h_exposed": sessions_between(date.fromisoformat(sets["h_exposed"][0]), f1),
    }


def read_bars(path: Path) -> list[tuple]:
    """Nifty 50 bars in chronological order: (timestamp, open, high, low, close, is_synthetic)."""
    con = duckdb.connect(str(path), read_only=True)
    try:
        return con.execute(
            "SELECT timestamp, open, high, low, close, is_synthetic FROM candles "
            "WHERE symbol = ? ORDER BY timestamp", [SYMBOL]).fetchall()
    finally:
        con.close()


def _is_flat(bar) -> bool:
    return bar[1] == bar[2] == bar[3] == bar[4]


def longest_flat_run(bars: list[tuple], variant: str) -> tuple:
    """Longest run of O=H=L=C bars with an unchanged close, bars before 15:00, time order.

    identical_close: consecutive flat bars sharing one close.
    minute_adjacent: as identical_close, and each bar one minute after the last.
    vs_previous_bar: flat bars whose close equals the immediately preceding bar's close.
    """
    seq = sorted(b for b in bars if b[0].time() < PRE_CLOSE)
    best, start, length = (None, 0), None, 0
    for i, bar in enumerate(seq):
        prev = seq[i - 1] if i else None
        if variant == "vs_previous_bar":
            ok = _is_flat(bar) and prev is not None and bar[4] == prev[4]
            extends = ok and length > 0
        else:
            ok = _is_flat(bar)
            extends = ok and length > 0 and bar[4] == prev[4] and (
                variant == "identical_close" or bar[0] - prev[0] == timedelta(minutes=1))
        if extends:
            length += 1
        elif ok:
            start, length = bar[0], 1
        else:
            start, length = None, 0
        if length > best[1]:
            best = (start, length)
    return best


def _ohlc_consistent(bar, variant: str) -> bool:
    o, h, l, c = bar[1:5]
    if variant == "high_low_only":
        return h >= l
    return h >= max(o, c) and l <= min(o, c) and h >= l


def evaluate_session(d: date, store: Path, defects: set[date], freeze_run: int) -> dict:
    rec: dict = {"date": d.isoformat(), "weekday": d.strftime("%a"), "items": {}, "reasons": {}}
    items, reasons = rec["items"], rec["reasons"]
    path = store / f"{d.isoformat()}.duckdb"
    rec["file_present"] = path.exists()
    rec["file_sha256"] = sha256_file(path) if path.exists() else None

    weekday_ok = d.weekday() < 5 and d not in NSE_HOLIDAYS
    items["1"] = rec["file_present"] and weekday_ok
    if not items["1"]:
        reasons["1"] = ("file_absent" if not rec["file_present"] else
                        "weekend" if d.weekday() >= 5 else "nse_holiday")

    bars = read_bars(path) if path.exists() else None
    rec["n_nifty_bars"] = None if bars is None else len(bars)
    if bars:
        first = min(b[0] for b in bars)
        rec["first_stamp"] = first.isoformat()
        items["2"] = first.date() == d
        if not items["2"]:
            reasons["2"] = "first_bar_misdated"
        if first.time() != OPEN:
            items["3"], reasons["3"] = False, f"first_stamp_{first.time():%H:%M}"
        else:
            try:
                items["3"] = labeling_of(first.time(), d) == NATIVE
            except UnknownLabeling as exc:
                raise ContractStop(f"{d}: labeling_of rejected a 09:15 first bar: {exc}")
            if not items["3"]:
                reasons["3"] = "not_native"
        _window_items(rec, bars, d, freeze_run)
    else:
        rec["first_stamp"] = None
        why = "file_absent" if bars is None else "no_nifty_bars"
        for k in ("2", "3", "5", "6", "7"):
            items[k], reasons[k] = False, why
        rec["item7_longest_run"] = None

    items["4"] = d not in SPECIAL_SESSIONS
    if not items["4"]:
        reasons["4"] = "special_session"
    _item8(rec, d, store)
    items["9"] = d not in defects
    if not items["9"]:
        reasons["9"] = "defect_register"

    rec["eligible"] = all(items[k] for k in "123456789")
    rec["otherwise_eligible"] = all(items[k] for k in "12345689")
    return rec


def _window_items(rec: dict, bars: list[tuple], d: date, freeze_run: int) -> None:
    items, reasons = rec["items"], rec["reasons"]
    window = [b for b in bars if OPEN <= b[0].time() <= LAST_WINDOW_BAR]
    expected = {datetime.combine(d, OPEN) + timedelta(minutes=i) for i in range(WINDOW_MINUTES)}
    stamps = [b[0] for b in window]  # ascending chronological order
    strictly_increasing = all(a < b for a, b in zip(stamps, stamps[1:]))
    full = strictly_increasing and len(stamps) == WINDOW_MINUTES and set(stamps) == expected
    items["5"] = full
    if not full:
        missing = len(expected - set(stamps))
        reasons["5"] = f"window_bars={len(stamps)} missing_minutes={missing}"

    through = [b for b in bars if b[0].time() <= LAST_WINDOW_BAR]
    readings6 = {}
    for variant in ("high_low_only", "open_close_within_range"):
        readings6[variant] = all(
            _ohlc_consistent(b, variant) and min(b[1:5]) > 0 and b[5] is False for b in through)
    if len(set(readings6.values())) != 1:
        raise ContractStop(f"{d}: item 6 readings disagree {readings6}")
    items["6"] = readings6["open_close_within_range"]
    if not items["6"]:
        reasons["6"] = "ohlc_price_or_synthetic"

    runs = {v: longest_flat_run(bars, v)
            for v in ("identical_close", "minute_adjacent", "vs_previous_bar")}
    outcomes = {v: r[1] < freeze_run for v, r in runs.items()}
    if len(set(outcomes.values())) != 1:
        raise ContractStop(f"{d}: item 7 readings disagree {runs}")
    items["7"] = outcomes["identical_close"]
    start, length = runs["identical_close"]
    rec["item7_longest_run"] = {"start": start.isoformat() if start else None, "length": length}
    if not items["7"]:
        reasons["7"] = f"feed_freeze run_start={start:%H:%M} length={length}"


def _item8(rec: dict, d: date, store: Path) -> None:
    items, reasons = rec["items"], rec["reasons"]
    prev = previous_session(d)  # OutsideCoverage propagates: fatal (A2-7)
    rec["previous_session"] = prev.isoformat()
    ppath = store / f"{prev.isoformat()}.duckdb"
    rec["prev_file_sha256"] = sha256_file(ppath) if ppath.exists() else None
    rec["prev_1529_close"] = None
    if not ppath.exists():
        items["8"], reasons["8"] = False, "prev_file_absent"
        return
    pbars = read_bars(ppath)
    at = [b for b in pbars if b[0] == datetime.combine(prev, PREV_CLOSE_BAR)]
    if len(at) > 1:
        raise ContractStop(f"{d}: previous session {prev} has {len(at)} bars stamped 15:29")
    if not pbars:
        items["8"], reasons["8"] = False, "prev_no_nifty_bars"
    elif not at:
        items["8"], reasons["8"] = False, "prev_no_1529_bar"
    elif not at[0][4] > 0:
        items["8"], reasons["8"] = False, "prev_1529_close_le_0"
    else:
        items["8"] = True
        rec["prev_1529_close"] = at[0][4]


def summarize(records: dict[str, list[dict]]) -> dict:
    out = {}
    for name, recs in records.items():
        by_year: dict = {}
        for r in recs:
            y = by_year.setdefault(r["date"][:4], Counter())
            y["sessions"] += 1
            y["eligible"] += r["eligible"]
            y["otherwise_eligible"] += r["otherwise_eligible"]
        fails = Counter(k for r in recs for k, v in r["items"].items() if not v)
        out[name] = {
            "sessions": len(recs),
            "eligible": sum(r["eligible"] for r in recs),
            "otherwise_eligible": sum(r["otherwise_eligible"] for r in recs),
            "excluded": sum(not r["eligible"] for r in recs),
            "item7_alone_excluded": sum(r["otherwise_eligible"] and not r["eligible"] for r in recs),
            "failures_by_item": dict(sorted(fails.items())),
            "by_year": {y: dict(c) for y, c in sorted(by_year.items())},
        }
    return out


def build(store: Path) -> dict:
    config, addendum = load_seal()
    elig = config["eligibility"]
    defects = {date.fromisoformat(x) for x in elig["defect_register"]}
    records = {name: [evaluate_session(d, store, defects, elig["feed_freeze_run_bars"]) for d in ds]
               for name, ds in populations(config, addendum).items()}
    return {
        "protocol_id": "JEV-NMS-1",
        "step": "section 28 step 1 - eligibility construction",
        "seal": {"f1_configuration": addendum["f1_configuration"],
                 "protocol_document": addendum["protocol_document"],
                 "amendment_2": addendum["amendment_2"],
                 "config_amendment_2_sha256": EXPECTED_ADDENDUM_SHA256},
        "store": str(store),
        "symbol": SYMBOL,
        "summary": summarize(records),
        "sessions": records,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, required=True, help="1m store directory")
    ap.add_argument("--out", type=Path, default=REPO / "data" / "jev_market_state")
    ap.add_argument("--dry-run", action="store_true", help="evaluate and print; write nothing")
    args = ap.parse_args()
    try:
        artifact = build(args.store)
    except OutsideCoverage as exc:
        raise SystemExit(f"FATAL OutsideCoverage: {exc}")
    artifact["built_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(json.dumps(artifact["summary"], indent=1))
    if args.dry_run:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / ARTIFACT_NAME
    with open(target, "x", encoding="utf-8", newline="") as fh:  # append-only: never overwrite
        fh.write(json.dumps(artifact, indent=1, sort_keys=True))
    digest = sha256_file(target)
    with open(args.out / "ledger.jsonl", "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"event": "eligibility_constructed", "at": artifact["built_at"],
                             "artifact": ARTIFACT_NAME, "sha256": digest}) + "\n")
    print(f"{target}  sha256={digest}")


if __name__ == "__main__":
    main()
