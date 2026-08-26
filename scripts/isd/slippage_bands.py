"""ISD G6b — measured slippage bands from the native 1m store (measurement only).

Two families, pooled by per-session dollar-volume liquidity decile:
  drift   — (next_open - close) / close: the cost of acting on a signal computed
            at bar close but executable only at the next bar's open.
  range   — (high - low) / close: intra-minute excursion scale.
Percentiles p50/p90 published per decile. No viability verdicts here — Phase 0
consumes these numbers.
"""
from __future__ import annotations

import duckdb
import numpy as np

from scripts.isd.read_1m import connect_ro


def session_stats(path) -> dict:
    """Per-session decile aggregates via SQL; only aggregates cross the wire."""
    con = connect_ro(path)
    try:
        rows = con.execute("""
            with eq as (
                select symbol, timestamp, open, high, low, close, volume,
                       hour(timestamp)*60 + minute(timestamp) as m
                from candles where symbol like 'NSE_EQ%'
            ),
            seq as (
                select *,
                       lead(open) over (partition by symbol order by timestamp)
                           as next_open,
                       sum(close * volume) over (partition by symbol) as dvol,
                       count(*) over (partition by symbol) as n_bars
                from eq
            ),
            complete as (
                select *, ntile(10) over (order by dvol) as decile
                from seq where n_bars >= 360 and next_open is not null
                  and volume > 0 and close > 0
            )
            select
                decile,
                avg((next_open - close) / close) as drift_mean,
                quantile_cont((next_open - close) / close, 0.5) as drift_p50,
                quantile_cont((next_open - close) / close, 0.9) as drift_p90,
                quantile_cont((high - low) / close, 0.5) as range_p50,
                quantile_cont((high - low) / close, 0.9) as range_p90,
                count(*) as n_obs
            from complete
            group by decile order by decile
        """).fetchall()
    finally:
        con.close()
    return {"deciles": [
        {"decile": int(d), "drift_mean_bps": round(1e4 * dm, 2),
         "drift_p50_bps": round(1e4 * dp5, 2),
         "drift_p90_abs_bps": round(1e4 * abs(dp9), 2),
         "range_p50_bps": round(1e4 * rp5, 2),
         "range_p90_bps": round(1e4 * rp9, 2),
         "n_obs": int(n)}
        for d, dm, dp5, dp9, rp5, rp9, n in rows]}


def run(sessions: list, stride: int = 7) -> dict:
    """sessions: [(iso, path)]; every `stride`-th session is measured."""
    sampled = sessions[::stride]
    acc: dict = {}
    n_sessions = 0
    total_obs = 0
    for iso, path in sampled:
        try:
            st = session_stats(path)
        except RuntimeError:
            continue                      # ops contention — counted, not silent
        n_sessions += 1
        for row in st["deciles"]:
            a = acc.setdefault(row["decile"], {k: [] for k in
                                               ("drift_mean_bps",
                                                "drift_p50_bps",
                                                "drift_p90_abs_bps",
                                                "range_p50_bps",
                                                "range_p90_bps")})
            for k in a:
                a[k].append(row[k])
            total_obs += row["n_obs"]
    pooled = []
    for d in sorted(acc):
        pooled.append({"decile": d, **{
            k: round(float(np.mean(v)), 2) for k, v in acc[d].items()}},
        )
    return {
        "gate": "G6b",
        "sessions_sampled": len(sampled),
        "sessions_measured": n_sessions,
        "observations": total_obs,
        "pooled_by_decile": pooled,
        "pass": n_sessions > 0,
    }
