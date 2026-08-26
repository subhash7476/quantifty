"""ISD G7e — cross-validation: vendor staging vs native store on the overlap.

For every shared (symbol, session, minute) the vendor close is compared to the
native Upstox-sourced close. The two series sit on DIFFERENT CA-adjustment
bases (measured 2026-08-25: HDFCBANK vendor = 2.0000 × native across all bars —
a post-overlap bonus; SIEMENS 0.7618; ITC 0.8649 after the ITC-Hotels demerger).
A CONSTANT per-ticker ratio is a basis offset, not corruption: each bar is
compared on the ALIGNED basis (vendor close ÷ the per-ticker-day median ratio)
and the tolerance applies to the residual.

PASS bar (proposed in the plan, confirmed at review): >=99% of ALIGNED bars
within 0.05% relative AND median aligned |Δclose| = 0. Raw (unaligned) shares,
basis-offset tickers, and a per-ticker-day low-agreement census are published
regardless — the disagreement census localizes, never hides (plan §G7e).
"""
from __future__ import annotations

import statistics

from scripts.isd import NATIVE_1M_DIR, connect_ro
from scripts.isd.ingest_vendor_archive import MANIFEST_PATH

REL_TOL = 0.0005           # 0.05%
PASS_SHARE = 0.99
TICKER_AGREE_SHARE = 0.99  # census line: per-ticker-day aligned share floor


def _paths():
    from scripts.isd import VENDOR_DIR
    return VENDOR_DIR / "vendor_flat.duckdb"


def duckdb_connect(path):
    import duckdb
    return duckdb.connect(str(path))


def consolidate(manifest_path=MANIFEST_PATH) -> int:
    """Flatten per-symbol staging DBs into one keyed table for joins.

    DuckDB-native: each source is ATTACHed and copied with INSERT INTO SELECT,
    never streamed through Python (the ~97M-bar Python executemany loop took
    hours and never finished — measured 2026-08-25).
    """
    import json
    from scripts.isd import VENDOR_DIR
    flat_path = VENDOR_DIR / "vendor_flat.duckdb"
    records = [json.loads(l) for l in open(manifest_path, encoding="utf-8")
               if l.strip()]
    resolved = [(r["ticker"], r["isin"]) for r in records if r["resolved"]]
    for stale in (flat_path, flat_path.with_suffix(".duckdb.wal")):
        if stale.exists():
            stale.unlink()
    out = duckdb_connect(flat_path)
    try:
        out.execute(
            "create table vendor_closes (trade_date DATE, minute INTEGER, "
            "isin VARCHAR, ticker VARCHAR, close DOUBLE)")
        for ticker, isin in resolved:
            src = VENDOR_DIR / f"{ticker}.duckdb"
            if not src.exists():
                continue
            out.execute(f"attach '{src.as_posix()}' as v (read_only)")
            try:
                out.execute(f"""
                    insert into vendor_closes
                    select cast(ts as DATE),
                           extract(hour from ts)*60 + extract(minute from ts),
                           ?, ?, "close"
                    from v.vendor_1m
                """, [isin, ticker])
            finally:
                out.execute("detach v")
        n = out.execute("select count(*) from vendor_closes").fetchone()[0]
    finally:
        out.close()
    return n


def run(stride: int = 3) -> dict:
    """Compare every `stride`-th native session against the vendor flat table."""
    flat_path = _paths()
    sessions = sorted(p.stem for p in NATIVE_1M_DIR.glob("*.duckdb")
                      if p.stem >= "2023-01-02")[::stride]

    months: dict = {}
    n_cmp = n_within_raw = n_within_align = 0
    basis_offset: set = set()
    low_agreement: dict = {}
    diffs = []

    for session in sessions:
        native = connect_ro(NATIVE_1M_DIR / f"{session}.duckdb")
        try:
            native.execute("pragma disable_progress_bar")
            native.execute(f"attach '{flat_path.as_posix()}' as v "
                           "(read_only)")
            try:
                rows = native.execute(f"""
                    select v.ticker, v.minute, v.close, n.close
                    from v.vendor_closes v
                    join candles n
                      on n.symbol = 'NSE_EQ|' || v.isin
                     and hour(n.timestamp)*60 + minute(n.timestamp) = v.minute
                    where v.trade_date = DATE '{session}'
                      and cast(n.timestamp as DATE) = DATE '{session}'
                """).fetchall()
            finally:
                native.execute("detach v")
        finally:
            native.close()

        by_ticker: dict = {}
        for ticker, minute, vc, nc in rows:
            by_ticker.setdefault(ticker, []).append(
                (minute, float(vc), float(nc)))

        month = session[:7]
        for ticker, bars in by_ticker.items():
            ratios = [vc / nc for _m, vc, nc in bars if nc > 0]
            if not ratios:
                continue
            med = statistics.median(ratios)
            if abs(med - 1.0) > 1e-6:
                basis_offset.add(ticker)
            m = months.setdefault(month, {"n": 0, "within": 0})
            day_n = day_within = 0
            for _m, vc, nc in bars:
                n_cmp += 1
                rd_raw = abs(vc - nc) / nc if nc > 0 else 1.0
                n_within_raw += 1 if rd_raw <= REL_TOL else 0
                aligned = vc / med
                rd = abs(aligned - nc) / nc if nc > 0 else 1.0
                day_n += 1
                day_within += 1 if rd <= REL_TOL else 0
                n_within_align += 1 if rd <= REL_TOL else 0
                m["n"] += 1
                m["within"] += 1 if rd <= REL_TOL else 0
                diffs.append(abs(aligned - nc))
            if day_within / day_n < TICKER_AGREE_SHARE:
                low_agreement.setdefault(ticker, []).append(session)

    diffs.sort()
    median_abs = diffs[len(diffs) // 2] if diffs else None
    share_align = n_within_align / n_cmp if n_cmp else None
    share_raw = n_within_raw / n_cmp if n_cmp else None
    monthly = [{"month": k,
                "n": v["n"],
                "within_share": round(v["within"] / v["n"], 5)}
               for k, v in sorted(months.items()) if v["n"] > 0]
    return {
        "gate": "G7e",
        "native_sessions_compared": len(sessions),
        "compared_bars": n_cmp,
        "raw_share_within_005pct": round(share_raw, 6) if share_raw is not None
        else None,
        "aligned_share_within_005pct": (round(share_align, 6)
                                        if share_align is not None else None),
        "aligned_median_abs_diff_rs": median_abs,
        "basis_offset_tickers": sorted(basis_offset),
        "low_agreement_ticker_days": {k: v for k, v in sorted(
            low_agreement.items())},
        "monthly_census_aligned": monthly,
        "pass": share_align is not None and share_align >= PASS_SHARE
                and median_abs == 0,
    }
