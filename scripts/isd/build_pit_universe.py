"""ISD G5 — PIT universe membership (operator decision Q3: PIT, never static).

Membership semantics per session:
  `intraday_present` — the symbol carried bars in that day's native 1m file
                       (the practical tradeable set).
  `fno_member`       — a FUTSTK contract on that underlying traded that day
                       (futures-bhavcopy presence = direct F&O eligibility).
  entity resolution  — certified `symbol_entity_intervals` (CSMP), so recycled
                       tickers never fuse identities.

Cross-store verification (two independent bhavcopy feeds): FUTSTK underlyings
(futures_bhavcopy) vs OPTSTK underlyings (stock_options_bhavcopy) per shared
session. Census published; PASS bar (proposed, confirm at review): >=99%
agreement of union sets, and every intraday-present symbol resolves to an entity.
"""
from __future__ import annotations

import datetime as dt
from bisect import bisect_right

import duckdb

from scripts.isd import EQUITY_DB, FUTURES_DB, ISD_DATA_DIR, connect_ro

OPTIONS_DB = ISD_DATA_DIR.parent / "market_data" / "stock_options_bhavcopy.duckdb"
OUT_DB = ISD_DATA_DIR / "pit_universe.duckdb"


def _fno_days() -> dict:
    """session iso -> set(FUTSTK underlyings)."""
    con = connect_ro(FUTURES_DB)
    try:
        rows = con.execute("""
            select trade_date, underlying from futures_bhavcopy
            where inst_type = 'FUTSTK' and trade_date >= '2023-01-02'
            group by 1, 2
        """).fetchall()
    finally:
        con.close()
    out: dict = {}
    for d, u in rows:
        out.setdefault(d.isoformat(), set()).add(u)
    return out


def _opt_days() -> dict:
    """session iso -> set(OPTSTK underlyings) — the independent second feed."""
    con = connect_ro(OPTIONS_DB)
    try:
        rows = con.execute("""
            select trade_date, underlying from stock_options_bhavcopy
            where option_type = 'CE' and trade_date >= '2023-01-02'
            group by 1, 2
        """).fetchall()
    finally:
        con.close()
    out: dict = {}
    for d, u in rows:
        out.setdefault(d.isoformat(), set()).add(u)
    return out


def _entity_index():
    """symbol -> (starts list, entities list) for [valid_from, valid_to) spans."""
    con = connect_ro(EQUITY_DB)
    try:
        rows = con.execute(
            "select symbol, valid_from, valid_to, entity "
            "from symbol_entity_intervals").fetchall()
    finally:
        con.close()
    by_sym: dict = {}
    for sym, vf, vt, ent in rows:
        by_sym.setdefault(sym, []).append((vf.date() if hasattr(vf, "date") else vf,
                                           vt.date() if hasattr(vt, "date") else vt,
                                           ent))
    idx = {}
    for sym, spans in by_sym.items():
        spans.sort()
        idx[sym] = ([s[0] for s in spans], spans)
    return idx


def _resolve(idx, symbol, session_iso) -> str | None:
    import datetime as dt
    if symbol not in idx:
        return None
    starts, spans = idx[symbol]
    d = dt.date.fromisoformat(session_iso)
    i = bisect_right(starts, d) - 1
    if i >= 0 and spans[i][0] <= d < spans[i][1]:
        return spans[i][2]
    return None


def _resolve_any(idx, candidates, session_iso) -> str | None:
    import datetime as dt
    d = dt.date.fromisoformat(session_iso)
    for sym in candidates:
        if sym not in idx:
            continue
        starts, spans = idx[sym]
        i = bisect_right(starts, d) - 1
        if i >= 0 and spans[i][0] <= d < spans[i][1]:
            return spans[i][2]
    return None


def _rename_edges() -> dict:
    """symbol_changes adjacency, both directions (old<->new), transitively
    closed so an ISIN resolves through every name it ever traded under."""
    con = connect_ro(EQUITY_DB)
    try:
        rows = con.execute(
            "select old_symbol, new_symbol from symbol_changes").fetchall()
    finally:
        con.close()
    adj: dict = {}
    for old, new in rows:
        adj.setdefault(old, set()).add(new)
        adj.setdefault(new, set()).add(old)
    return adj


def _isin_to_symbols() -> dict:
    """isin -> every NSE symbol ever carrying it: master ∪ legacy mapping,
    then transitively expanded through rename chains (MCDOWELL-N→UNITDSPR,
    IIFLWAM→360ONE) so era-renamed tickers resolve under their old names."""
    con = connect_ro(EQUITY_DB)
    try:
        rows = con.execute(
            "select symbol, isin from instrument_master where isin is not null "
            "union select symbol, isin from symbol_isin where isin is not null"
        ).fetchall()
    finally:
        con.close()
    base: dict = {}
    for s, i in rows:
        base.setdefault(i, set()).add(s)
    adj = _rename_edges()
    out: dict = {}
    for isin, seeds in base.items():
        seen = set(seeds)
        frontier = list(seeds)
        while frontier:
            cur = frontier.pop()
            for nxt in adj.get(cur, ()):  # transitive closure
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        out[isin] = seen
    return out


def build(present_by_session: dict) -> dict:
    """present_by_session: {session_iso: [(isin_key, isin_body), ...]} where
    isin_key is the native symbol (`NSE_EQ|INE…`) and isin_body the ISIN.

    Writes data/isd/pit_universe.duckdb; returns the gate result dict.
    """
    fno = _fno_days()
    opt = _opt_days()
    idx = _entity_index()
    isin_syms = _isin_to_symbols()

    shared = sorted(set(fno) & set(opt))
    union_n = diff_n = 0
    worst_days = []
    for s in shared:
        u = fno[s] | opt[s]
        d = fno[s] ^ opt[s]
        union_n += len(u)
        diff_n += len(d)
        if u and len(d) / len(u) > 0.05:
            worst_days.append({"session": s, "sym_diff": sorted(d)[:10]})
    agreement = (1.0 - diff_n / union_n) if union_n else None

    OUT_DB.parent.mkdir(parents=True, exist_ok=True)
    if OUT_DB.exists():
        OUT_DB.unlink()
    out = duckdb.connect(str(OUT_DB))
    try:
        out.execute(
            "create table pit_membership (session_date DATE, symbol VARCHAR, "
            "isin VARCHAR, entity VARCHAR, intraday_present BOOLEAN, "
            "fno_member BOOLEAN)")
        unresolved = set()
        n_rows = 0
        n_weekend_special_sessions = 0
        batch = []
        for session, pairs in sorted(present_by_session.items()):
            if dt.date.fromisoformat(session).weekday() >= 5:
                # weekend specials (e.g. Diwali Muhurat): non-standard
                # microstructure, not program scope; their odd prints
                # (debt-series ISINs) are excluded by rule, counted below.
                n_weekend_special_sessions += 1
                continue
            fset = fno.get(session, set())
            for isin_key, isin_body in pairs:
                candidates = sorted(isin_syms.get(isin_body,
                                                  {isin_body}))
                ent = _resolve_any(idx, candidates, session)
                if ent is None:
                    unresolved.add((session,
                                    f"{isin_key}({','.join(candidates)})"))
                batch.append([session,
                              ",".join(candidates), isin_key, ent, True,
                              any(c in fset for c in candidates)])
                n_rows += 1
                if len(batch) >= 50_000:
                    out.executemany(
                        "insert into pit_membership values (?, ?, ?, ?, ?, ?)",
                        batch)
                    batch.clear()
        if batch:
            out.executemany(
                "insert into pit_membership values (?, ?, ?, ?, ?, ?)", batch)
    finally:
        out.close()

    return {
        "gate": "G5",
        "membership_rows": n_rows,
        "sessions": len(present_by_session),
        "weekend_special_sessions_skipped": n_weekend_special_sessions,
        "cross_feed_sessions_compared": len(shared),
        "cross_feed_agreement": round(agreement, 6) if agreement is not None else None,
        "cross_feed_worst_days": worst_days[:10],
        "unresolved_symbols": sorted(f"{s}:{u}" for s, u in unresolved)[:50],
        "unresolved_count": len(unresolved),
        # PASS bar: two independent feeds agree on F&O membership, and every
        # intraday-present symbol resolves to an entity interval.
        "pass": (agreement is not None and agreement >= 0.99
                 and not unresolved),
    }
