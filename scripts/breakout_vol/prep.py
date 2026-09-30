"""BKV-1 panel snapshot (outcome-free, ingest-level).

Reads the certified equity store read-only ONCE and writes hashed parquet snapshots so the
research never depends on a live DuckDB file. The dev snapshot stops at DEV_CUTOFF: no HOLDOUT
price exists in it. A HOLDOUT snapshot is only built by `--holdout`, after the operator go-ahead.

Conventions inherited unchanged from the PSB/CSMP harness (scripts/psb1/screening_harness.py load_panel):
adjusted OHLCV from `equity_bhavcopy_adjusted`, entity by `universe_eligibility`, one listing per
(entity, date) chosen by the highest turnover (rn=1), calendar = trading_calendar with n_symbols >= 200.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys

import duckdb
import pandas as pd

from scripts.breakout_vol import common as C


def _sha(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(cutoff: dt.date, tag: str) -> dict:
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(C.EQUITY_DB), read_only=True)
    unfenced_max = con.execute("SELECT MAX(trade_date) FROM equity_bhavcopy").fetchone()[0]

    cal = con.execute("""
        SELECT c.trade_date, c.n_symbols,
               COALESCE(t.tot_turnover, 0) AS tot_turnover_eq
        FROM trading_calendar c
        LEFT JOIN (SELECT trade_date, SUM(turnover) tot_turnover FROM equity_bhavcopy
                   WHERE series = 'EQ' GROUP BY 1) t USING (trade_date)
        WHERE c.trade_date >= ? AND c.trade_date <= ?
        ORDER BY 1""", [C.PANEL_START, cutoff]).df()

    memb = con.execute("""
        SELECT um.rebalance_date, e.entity, um.symbol, um.rank
        FROM universe_membership um JOIN universe_eligibility e ON e.symbol = um.symbol
        WHERE um.rebalance_date <= ? ORDER BY um.rebalance_date, um.rank""", [cutoff]).df()

    panel = con.execute("""
        SELECT entity, trade_date, symbol, series, open, high, low, close, volume, turnover, n_listings
        FROM (
          SELECT e.entity, a.trade_date, a.symbol, a.series, a.open, a.high, a.low, a.close,
                 a.volume, a.turnover,
                 COUNT(*) OVER (PARTITION BY e.entity, a.trade_date) AS n_listings,
                 ROW_NUMBER() OVER (PARTITION BY e.entity, a.trade_date
                                    ORDER BY a.turnover DESC NULLS LAST, a.symbol) AS rn
          FROM equity_bhavcopy_adjusted a JOIN universe_eligibility e ON e.symbol = a.symbol
          WHERE a.trade_date >= ? AND a.trade_date <= ?
            AND e.entity IN (SELECT DISTINCT e2.entity FROM universe_membership m
                             JOIN universe_eligibility e2 ON e2.symbol = m.symbol
                             WHERE m.rebalance_date <= ?)
        ) WHERE rn = 1 ORDER BY entity, trade_date""", [C.PANEL_START, cutoff, cutoff]).df()
    raw_rows = con.execute("SELECT COUNT(*) FROM equity_bhavcopy WHERE trade_date <= ?", [cutoff]).fetchone()[0]
    con.close()

    assert panel["trade_date"].max() <= pd.Timestamp(cutoff), "FENCE LEAK"
    out = {}
    for name, df in (("calendar", cal), ("membership", memb), ("panel", panel)):
        p = C.OUT_DIR / f"{name}_{tag}.parquet"
        df.to_parquet(p, index=False)
        out[name] = {"path": str(p), "rows": int(len(df)), "sha256": _sha(p)}
    manifest = {"tag": tag, "cutoff": cutoff.isoformat(), "built_at": dt.datetime.now().isoformat(timespec="seconds"),
                "store_unfenced_max_date": str(unfenced_max), "fence_vacuous": bool(unfenced_max <= cutoff),
                "raw_equity_rows_le_cutoff": int(raw_rows), "panel_max_date": str(panel["trade_date"].max().date()),
                "duplicate_listings_dropped": int((panel["n_listings"] > 1).sum()),
                "files": out}
    (C.OUT_DIR / f"manifest_{tag}.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    if "--holdout" in sys.argv:
        m = build(C.STAGES["HOLDOUT"][1], "full")
    else:
        m = build(C.DEV_CUTOFF, "dev")
    print(json.dumps(m, indent=2))
