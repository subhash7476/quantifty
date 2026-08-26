"""ISD G7f — vendor CA-adjustment verification against the daily adjusted view.

The vendor series appears back-adjusted (probe: RELIANCE ≈216 on 2015-02-02).
If that adjustment basis is wrong or partial, corporate-action seams fabricate
overnight returns. Test: at every known ex-date (certified `corporate_actions`
table) the VENDOR overnight gap (open/prev_close - 1) must look like an ordinary
return. Any seam with |gap| > 20% fails outright (the PSB fabrication threshold);
the full non-CA overnight-gap distribution is published alongside for context.
"""
from __future__ import annotations

import duckdb

from scripts.isd import EQUITY_DB, VENDOR_DIR, connect_ro
from scripts.isd.read_1m import connect_ro as _ro

FABRICATION_BPS = 2000.0     # |gap| > 20% = fabricated seam (PSB threshold)


def _ca_ex_dates(isins: list) -> dict:
    """isin -> sorted list of (ex_date, purpose)."""
    con = connect_ro(EQUITY_DB)
    try:
        rows = con.execute("""
            select ca.symbol, ca.ex_date,
                   coalesce(ca.purpose_raw, 'unknown')
            from corporate_actions ca
        """).fetchall()
        sym_isin = dict(con.execute(
            "select symbol, isin from symbol_isin where isin is not null"
        ).fetchall())
    finally:
        con.close()
    out: dict = {}
    for symbol, ex_date, purpose in rows:
        isin = sym_isin.get(symbol)
        if not isin:
            continue
        out.setdefault(isin, []).append(
            (ex_date.date() if hasattr(ex_date, "date") else ex_date,
             purpose))
    for isin in out:
        out[isin].sort()
    return {i: v for i, v in out.items() if i in set(isins)}


def run(manifest_path=VENDOR_DIR / "manifest.jsonl", stride_days: int = 1) -> dict:
    """Audit CA seams in the staged vendor series.

    For each resolved ticker: overnight gaps are computed from vendor_1m; seams
    whose previous session is the trading day before an ex-date are compared
    against the fabrication bound.
    """
    import datetime as dt
    import json

    records = [json.loads(l) for l in open(manifest_path, encoding="utf-8")
               if l.strip()]
    resolved = [r for r in records if r["resolved"]]
    ca = _ca_ex_dates([r["isin"] for r in resolved])

    seams_checked = 0
    violations = []
    all_gaps = []
    for r in resolved:
        src = VENDOR_DIR / f"{r['ticker']}.duckdb"
        if not src.exists():
            continue
        ex_dates = {d for d, _p in ca.get(r["isin"], [])}
        con = connect_ro(src)
        try:
            gaps = con.execute("""
                with days as (
                    select distinct cast(ts as DATE) d from vendor_1m
                ),
                pairs as (
                    select d, lag(d) over (order by d) prev_d from days
                )
                select p.prev_d, p.d,
                       (o.open / c.close - 1.0) * 10000.0 as gap_bps,
                       p.d - p.prev_d
                from pairs p
                join (select cast(ts as DATE) d,
                             arg_min(open, ts) open from vendor_1m group by 1) o
                      on o.d = p.d
                join (select cast(ts as DATE) d,
                             arg_max("close", ts) "close"
                             from vendor_1m group by 1) c
                      on c.d = p.prev_d
                order by p.d
            """).fetchall()
        finally:
            con.close()
        for prev_d, d, gap_bps, cal_gap in gaps:
            all_gaps.append(abs(gap_bps))
            # a seam = first session AFTER a known ex-date (calendar gap small)
            gap_days = cal_gap.days if hasattr(cal_gap, "days") else cal_gap
            hit = any(0 < (d - ed).days <= max(gap_days, 4)
                      for ed in ex_dates)
            if not hit:
                continue
            seams_checked += 1
            if abs(gap_bps) > FABRICATION_BPS:
                violations.append({
                    "ticker": r["ticker"], "session": d.isoformat(),
                    "prev_session": prev_d.isoformat(),
                    "gap_bps": round(gap_bps, 1),
                })

    all_gaps.sort()
    return {
        "gate": "G7f",
        "tickers_audited": len(resolved),
        "entities_with_ca": len(ca),
        "seams_checked": seams_checked,
        "fabricated_seams": len(violations),
        "violations": violations[:50],
        "overnight_gap_abs_bps_p50": round(all_gaps[len(all_gaps)//2], 2)
        if all_gaps else None,
        "overnight_gap_abs_bps_p99": round(all_gaps[int(len(all_gaps)*0.99)], 2)
        if all_gaps else None,
        "pass": seams_checked > 0 and not violations,
    }
