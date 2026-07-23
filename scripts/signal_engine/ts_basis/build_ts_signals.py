"""TS Basis — signal construction (build_ts_signals.py).

Computes time-series basis z-scores per (formation_date, underlying):
  z_ts = (basis_now - trailing_mean) / trailing_std

Reads raw_ann_basis from the existing signals DB, computes trailing
z-scores per underlying, and writes to a new ts_signals.duckdb.

Bridge: TS_BASIS_PHASE0_PRE_REGISTRATION.md §3.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

SRC_SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
OUT_DB = ROOT / "data" / "signal_engine" / "ts_basis" / "ts_signals.duckdb"

Z_LOOKBACK = 504  # calendar days
Z_MIN_OBS = 12     # minimum prior formations
WINSORIZE_SD = 3.0


def main():
    OUT_DB.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute(f"ATTACH '{SRC_SIG_DB}' AS src (READ_ONLY)")
    con.execute("SET threads=4")

    print("Loading basis data...")
    rows = con.execute("""
        SELECT s.formation_date, s.underlying, s.raw_ann_basis, s.fwd_ret_1m, s.liquid
        FROM src.signals s
        WHERE s.raw_ann_basis IS NOT NULL AND s.liquid = TRUE
          AND s.fwd_ret_1m IS NOT NULL
        ORDER BY s.underlying, s.formation_date
    """).fetchall()

    name_history = defaultdict(list)
    for fdate, u, basis, fr, liq in rows:
        name_history[u].append((fdate, float(basis)))

    print(f"  {len(rows):,} rows across {len(name_history)} underlyings")

    # Compute z_ts
    signals = []
    for fdate, u, basis, fr, liq in rows:
        history = name_history[u]
        pos = next((i for i, (fd, _) in enumerate(history) if fd == fdate), None)
        if pos is None:
            continue

        prior = []
        for i2 in range(pos - 1, -1, -1):
            fd2, b2 = history[i2]
            if (fdate - fd2).days > Z_LOOKBACK:
                break
            prior.append(b2)

        if len(prior) < Z_MIN_OBS:
            continue

        mu = np.mean(prior)
        sd = np.std(prior, ddof=1)
        if sd < 1e-8:
            continue

        z_ts = (float(basis) - mu) / sd
        if np.isnan(z_ts):
            continue

        # Winsorize
        z_ts = float(np.clip(z_ts, -WINSORIZE_SD, WINSORIZE_SD))

        signals.append((str(fdate), u, float(basis), z_ts, float(fr), bool(liq)))

    con.close()

    print(f"  {len(signals):,} z-scored signals")

    if OUT_DB.exists():
        OUT_DB.unlink()

    out = duckdb.connect(str(OUT_DB))
    out.execute("""
        CREATE TABLE signals (
            formation_date DATE    NOT NULL,
            underlying     VARCHAR NOT NULL,
            raw_ann_basis  DOUBLE,
            z_ts           DOUBLE,
            fwd_ret_1m     DOUBLE,
            liquid         BOOLEAN,
            PRIMARY KEY (formation_date, underlying)
        )
    """)
    out.execute("CREATE INDEX idx_date ON signals (formation_date)")
    out.executemany(
        "INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?)",
        [(str(s[0]), s[1], s[2], s[3], s[4], s[5]) for s in signals],
    )
    total = out.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    n_form = out.execute("SELECT COUNT(DISTINCT formation_date) FROM signals").fetchone()[0]
    print(f"  Written {total:,} signals across {n_form} formations to {OUT_DB}")
    out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
