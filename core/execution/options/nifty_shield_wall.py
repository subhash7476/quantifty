"""NiftyShield — observe-only read of the Options-Wall poller's regime.

The platform already computes an options-structural read (gamma regime, pin
strike, walls, ATM IV vs realized vol) on the same clock as NiftyShield's 13:00
entry, in `data/options/wall_scan_results.duckdb::session_regime`. The
2026-09-08 audit found the structure decision consulted none of it, and that on
the three sessions where both reads exist they disagreed on two.

**This module changes no behaviour.** It records what the poller was saying at
each entry so the two reads can be compared on paired observations later. Three
sessions of overlap is not evidence that either read is better, and wiring an
unvalidated second opinion into a live decision would be replacing one
unmeasured rule with another.

Contract (the cross-process read the audit asked for):

  - **Read-only, separate process, separate store.** The poller owns the file;
    this never writes to it and holds no connection between calls.
  - **Staleness bound.** A row older than `max_age_s` is returned marked stale
    rather than silently used. The poller's cadence is seconds; minutes-old
    rows describe a different market.
  - **Fail-open, because this is observation.** A missing file, a lock, or a
    query error yields a record carrying the reason, never an exception into
    the entry path — an entry must not be lost to a logging dependency. The
    moment any of this gates a decision, that inverts: a gate that cannot read
    its input must fail closed, as the broker-margin path already does.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import duckdb

DEFAULT_DB = Path("data/options/wall_scan_results.duckdb")
DEFAULT_MAX_AGE_S = 300.0

# Prerequisite: the two reads speak different vocabularies and no mapping
# existed. This is the correspondence used when comparing them — an
# interpretation, recorded so the comparison is reproducible, not a claim that
# the two taxonomies measure the same thing. Positive net gamma means dealers
# damp moves (a pinning tape); negative net gamma means they amplify them.
GEX_TO_DAYTYPE = {
    "Positive GEX (Stable)": "Choppy",
    "Negative GEX (Volatile)": "Trending",
    "Neutral GEX": "Choppy",
}


def _classify_agreement(gex_regime: Optional[str],
                        daytype_regime: Optional[str]) -> Optional[str]:
    """Do the options-derived and day-type reads point the same way?

    The day-type taxonomy separates direction (BullTrend / BearTrend) from its
    absence (Choppy); the GEX taxonomy separates damping from amplification and
    says nothing about direction. So the only comparison the two support is
    trending-vs-pinning, and that is all this reports.
    """
    if not gex_regime or not daytype_regime:
        return None
    mapped = GEX_TO_DAYTYPE.get(gex_regime)
    if mapped is None:
        return "unmapped"
    dt = "Trending" if daytype_regime in ("BullTrend", "BearTrend") else "Choppy"
    return "agree" if mapped == dt else "disagree"


def read_wall_regime(session_date: str, at: datetime,
                     underlying: str = "NSE_INDEX|Nifty 50",
                     db_path: Path = DEFAULT_DB,
                     max_age_s: float = DEFAULT_MAX_AGE_S) -> Dict[str, Any]:
    """The poller's row nearest `at`, with staleness and availability recorded.

    Always returns a dict. `available` False carries `reason`; `stale` True
    means a row was found but is older than the bound and must not be read as
    describing this moment.
    """
    out: Dict[str, Any] = {"available": False, "stale": None, "reason": None}
    path = Path(db_path)
    if not path.exists():
        out["reason"] = f"wall store not present at {path}"
        return out
    try:
        con = duckdb.connect(str(path), read_only=True)
        try:
            row = con.execute(
                "SELECT ts, regime, atm_iv, realized_vol, pin_strike, put_wall, "
                "call_wall, pin_conviction, net_gex_cr, sigma_pts "
                "FROM session_regime WHERE underlying = ? AND trade_date = ? "
                "ORDER BY abs(epoch(ts) - epoch(?::timestamp)) LIMIT 1",
                [underlying, session_date, at.replace(tzinfo=None)]).fetchone()
        finally:
            con.close()
    except duckdb.Error as exc:
        out["reason"] = f"wall store unreadable: {exc}"
        return out
    if row is None:
        out["reason"] = "no wall regime row for this session"
        return out

    ts = row[0]
    age = abs((at.replace(tzinfo=None) - ts).total_seconds())
    out.update({
        "available": True,
        "stale": age > max_age_s,
        "age_s": round(age, 1),
        "max_age_s": max_age_s,
        "ts": ts.isoformat(),
        "wall_regime": row[1],
        "atm_iv": row[2],
        "realized_vol": row[3],
        "iv_minus_rv": (None if row[2] is None or row[3] is None
                        else round(float(row[2]) - float(row[3]), 3)),
        "pin_strike": row[4],
        "put_wall": row[5],
        "call_wall": row[6],
        "pin_conviction": row[7],
        "net_gex_cr": row[8],
        "sigma_pts": row[9],
    })
    return out


def shadow_record(session_date: str, at: datetime, daytype_regime: str,
                  structure: str, short_strike: Optional[float],
                  **kwargs) -> Dict[str, Any]:
    """The full observe-only record journaled at each entry."""
    rec = read_wall_regime(session_date, at, **kwargs)
    rec["daytype_regime"] = daytype_regime
    rec["structure"] = structure
    rec["short_strike"] = short_strike
    rec["agreement"] = _classify_agreement(rec.get("wall_regime"), daytype_regime)
    pin = rec.get("pin_strike")
    rec["short_strike_minus_pin"] = (
        None if pin is None or short_strike is None
        else round(float(short_strike) - float(pin), 2))
    return rec
