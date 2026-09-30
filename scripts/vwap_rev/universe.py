"""VWAP-XREV — PIT F&O universe, extended through the store's last session.

The certified ISD `pit_universe.duckdb` stops at 2026-08-24; the 1m store and the
futures bhavcopy run to 2026-09-29. Rather than mutate the certified artifact, the
ISD builder's own helpers (F&O presence from FUTSTK bhavcopy, ISIN->ticker rename
closure) are reused with paths redirected, membership is recomputed for every
session, and agreement with the certified table on the overlap is asserted.

fno_member(session, symbol) = a FUTSTK contract on that underlying traded that day
(direct F&O eligibility, point-in-time). No membership is projected backwards from
today's list.
"""
from __future__ import annotations

import datetime as dt
import json

import duckdb

from scripts.vwap_rev import common as C

UNIVERSE_JSON = C.OUT_DIR / "fno_membership.json"


def build_membership(present_by_session: dict[dt.date, list[str]]) -> dict[str, set]:
    """{session_iso: set(symbol keys that are F&O members that session)}."""
    import scripts.isd.build_pit_universe as bpu

    bpu.FUTURES_DB = C.FUTURES_DB
    bpu.EQUITY_DB = C.EQUITY_DB
    bpu.OPTIONS_DB = C.OPTIONS_DB
    fno = bpu._fno_days()
    isin_syms = bpu._isin_to_symbols()
    out: dict[str, set] = {}
    for d, keys in present_by_session.items():
        fset = fno.get(d.isoformat(), set())
        members = set()
        for key in keys:
            body = key.split("|", 1)[1]
            cands = isin_syms.get(body, {body})
            if any(c in fset for c in cands):
                members.add(key)
        out[d.isoformat()] = members
    return out


def agreement_with_certified(membership: dict[str, set]) -> dict:
    con = duckdb.connect(str(C.ISD_PIT_DB), read_only=True)
    try:
        rows = con.execute(
            "select session_date, isin, fno_member from pit_membership").fetchall()
    finally:
        con.close()
    cert: dict[str, set] = {}
    for d, key, fno in rows:
        if fno:
            cert.setdefault(d.isoformat(), set()).add(key)
    n_sess = n_diff = n_total = 0
    for s, mine in membership.items():
        if s not in cert:
            continue
        n_sess += 1
        both = mine | cert[s]
        n_total += len(both)
        n_diff += len(mine ^ cert[s])
    return {"sessions_compared": n_sess, "symbol_sessions_union": n_total,
            "symbol_sessions_differ": n_diff,
            "agreement": 1.0 - n_diff / n_total if n_total else None}


def save(membership: dict[str, set]) -> None:
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    UNIVERSE_JSON.write_text(json.dumps({k: sorted(v) for k, v in membership.items()}))


def load() -> dict[str, set]:
    return {k: set(v) for k, v in json.loads(UNIVERSE_JSON.read_text()).items()}
