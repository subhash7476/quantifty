"""JEV-NMS-1 §6/§7 point-in-time features f1-f9 for one state.

Information set I_t: the session's bars stamped <= t-1 plus C_prev (the
previous session's 15:29 close from the step-1 artifact). Nothing else is read.
Values are natural-log returns in basis points. Order (operator ruling Q1,
2026-09-18): every feature is computed at full precision, dependent features
(er_30 from f5) are derived from the full-precision quantities, and only then
is each field rounded per §6 (bp 1 decimal, er_30 3 decimals, f1 integer,
negative zero written as 0).

`build` writes the create-only feature artifact for every eligible D-fit and
D-eval state; store files must match their step-1 SHA-256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import duckdb

FIELDS = ("minutes_since_open", "gap_bp", "ret_open_bp", "ret_15_bp", "ret_30_bp",
          "rv_30_bp", "range_30_bp", "er_30", "twap_dist_bp")
BP = 1e4


def fixed(x: float, places: int) -> float:
    v = float(format(x, f".{places}f"))
    return 0.0 if v == 0 else v


def is_tie(x: float, places: int) -> bool:
    """True if the exact binary value lies exactly halfway between two outputs."""
    scaled = Decimal(x).scaleb(places)
    return scaled - scaled.to_integral_value(rounding="ROUND_FLOOR") == Decimal("0.5")


def raw_features(bars: list[tuple], t: int, c_prev: float) -> dict:
    """bars: (open, high, low, close) for minutes 0 (= 09:15) .. t-1 at least; t = slot index."""
    close = [b[3] for b in bars]
    o = bars[0][0]
    p_t = close[t - 1]
    rets = [math.log(close[i] / close[i - 1]) for i in range(t - 30, t)]
    abs_sum = sum(abs(r) for r in rets)
    f5 = math.log(p_t / close[t - 31]) * BP
    return {
        "minutes_since_open": t,
        "gap_bp": math.log(o / c_prev) * BP,
        "ret_open_bp": math.log(p_t / o) * BP,
        "ret_15_bp": math.log(p_t / close[t - 16]) * BP,
        "ret_30_bp": f5,
        "rv_30_bp": math.sqrt(sum(r * r for r in rets)) * BP,
        "range_30_bp": math.log(max(b[1] for b in bars[t - 30:t]) /
                                min(b[2] for b in bars[t - 30:t])) * BP,
        "er_30": abs(f5) / (abs_sum * BP) if abs_sum != 0 else 0.0,
        "twap_dist_bp": math.log(p_t / (sum(close[:t]) / t)) * BP,
    }


def rounded(raw: dict) -> dict:
    out = {}
    for k in FIELDS:
        if k == "minutes_since_open":
            out[k] = int(raw[k])
        elif k == "er_30":
            out[k] = fixed(raw[k], 3)
        else:
            out[k] = fixed(raw[k], 1)
    return out


REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
ARTIFACT_NAME = "features_step2.json"
SLOTS = ("10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30")


def slot_index(slot: str) -> int:
    h, m = map(int, slot.split(":"))
    return (h - 9) * 60 + m - 15


def load_window_bars(store: Path, d: str, expected_sha: str) -> list[tuple]:
    """(open, high, low, close) of the 345 bars stamped 09:15..14:59, chronological."""
    path = store / f"{d}.duckdb"
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise RuntimeError(f"{path} changed since the step-1 eligibility artifact")
    con = duckdb.connect(str(path), read_only=True)
    try:
        bars = con.execute(
            "SELECT open, high, low, close FROM candles WHERE symbol = 'NSE_INDEX|Nifty 50' AND "
            "strftime(timestamp, '%H:%M') BETWEEN '09:15' AND '14:59' ORDER BY timestamp").fetchall()
    finally:
        con.close()
    if len(bars) != 345:
        raise RuntimeError(f"{d}: expected 345 window bars, got {len(bars)}")
    return bars


def build(store: Path, elig: dict) -> dict:
    states, ties = {}, []
    for name in ("d_fit", "d_eval"):
        for rec in elig["sessions"][name]:
            if not rec["eligible"]:
                continue
            bars = load_window_bars(store, rec["date"], rec["file_sha256"])
            for s in SLOTS:
                t = slot_index(s)
                raw = raw_features(bars[:t], t, rec["prev_1529_close"])  # I_t only
                ties += [(rec["date"], s, k) for k in FIELDS[1:]
                         if is_tie(raw[k], 3 if k == "er_30" else 1)]
                states[f"{rec['date']}|{s}"] = {"set": name, **rounded(raw)}
    if ties:
        raise RuntimeError(f"exact rounding ties need a ruling: {ties[:5]}")
    return states


def main() -> None:
    from scripts.jev_nms_1.draws import ELIGIBILITY_SHA256, load_eligibility
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, required=True)
    args = ap.parse_args()
    target = OUT / ARTIFACT_NAME
    if target.exists():
        raise SystemExit(f"{target} exists; never rebuilt")
    art = {"protocol_id": "JEV-NMS-1", "step": "section 28 step 2 - section 6 features",
           "eligibility_sha256": ELIGIBILITY_SHA256, "fields": list(FIELDS),
           "rounding": "full precision first; er_30 from unrounded f5 (ruling Q1); then fixed decimals",
           "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "states": build(args.store, load_eligibility())}
    with open(target, "x", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(art, indent=1, sort_keys=True))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with open(OUT / "ledger.jsonl", "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"event": "features_built", "at": art["built_at"],
                             "artifact": ARTIFACT_NAME, "sha256": digest}) + "\n")
    print(f"{len(art['states'])} states  {target}  sha256={digest}")


if __name__ == "__main__":
    main()
