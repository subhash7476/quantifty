"""Trade Intelligence — Historical Builder (M0).

Reconstructs every TS Basis Daily trade from TRAIN + HOLDOUT data.
One row per (underlying, entry_date, side). INSERT at entry with
immutable signal snapshot. UPDATE at exit with outcome.

Portfolio delta logic mirrors CarryRebalancerHook: top-5 per leg,
equal-weight, ADV-capped 10%, 0.25σ band suppression.

Usage:
  python scripts/signal_engine/ts_basis_daily/build_trade_intelligence.py
Output: data/signal_engine/trade_intelligence/trade_intelligence.duckdb
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
IDX_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
SECTOR_CSV = ROOT / "governance" / "carry" / "sector_classification.csv"
TI_DIR = ROOT / "data" / "signal_engine" / "trade_intelligence"
TI_DB = TI_DIR / "trade_intelligence.duckdb"

STRATEGY_NAME = "ts_basis_daily"
MAX_POSITIONS = 5
MAX_PER_SECTOR = 2  # sector diversification constraint
QUINTILE_FRAC = 0.20
ADV_CAP_FRAC = 0.10
BAND_SIGMA = 0.25

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _load_sectors():
    sectors = {}
    with open(SECTOR_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sectors[row["symbol"]] = row["sector"]
    return sectors


def _load_index_regime(dates_sorted):
    regime = {}
    for d in dates_sorted:
        f = IDX_DIR / f"{d}.duckdb"
        if not f.exists():
            continue
        try:
            c = duckdb.connect()
            c.execute(f"ATTACH '{f}' AS src (READ_ONLY)")
            row = c.execute(
                "SELECT close FROM src.candles WHERE symbol = 'NSE_INDEX|India VIX'"
            ).fetchone()
            vix = float(row[0]) if row else None
            row = c.execute(
                "SELECT close FROM src.candles WHERE symbol = 'NSE_INDEX|Nifty 50'"
            ).fetchone()
            nifty = float(row[0]) if row else None
            c.close()
            if vix is not None and nifty is not None:
                regime[d] = (vix, nifty)
        except Exception:
            continue
    return regime


def _nifty_20d_return(regime, all_dates):
    results = {}
    closes = {}
    for d in all_dates:
        r = regime.get(d)
        if r is not None:
            closes[d] = r[1]
    date_list = all_dates
    for d in date_list:
        nc = closes.get(d)
        if nc is None:
            results[d] = None
            continue
        idx = date_list.index(d)
        lo_idx = max(0, idx - 20)
        if lo_idx == idx:
            results[d] = None
            continue
        pc = closes.get(date_list[lo_idx])
        if pc and pc > 0:
            results[d] = (nc - pc) / pc
        else:
            results[d] = None
    return results


def _compute_target_book(facts_by_z, adva, sector_map=None, max_per_sector=None,
                         rank_by="z_ts"):
    n = len(facts_by_z)
    if n < 5:
        return {}, {}
    nq = min(MAX_POSITIONS, max(1, round(QUINTILE_FRAC * n)))

    def _key(r):
        z = float(r[1])
        if rank_by == "z_ts":
            return z
        rz = float(r[2]) if len(r) > 2 and r[2] is not None else z
        br = bool(r[3]) if len(r) > 3 and r[3] is not None else False
        if rank_by == "raw_z":
            return rz
        discount = 0.5 if br else 1.0
        return (1.0 if rz >= 0 else -1.0) * abs(rz) * discount

    sorted_facts = sorted(facts_by_z, key=_key)

    def _pick(rows, reverse=False):
        iterable = reversed(rows) if reverse else rows
        picked, sec_counts = [], {}
        for r in iterable:
            u = r[0]
            sec = sector_map.get(u, "UNKNOWN") if sector_map else "UNKNOWN"
            limit = max_per_sector if max_per_sector is not None else 999
            if sec_counts.get(sec, 0) >= limit:
                continue
            picked.append(u)
            sec_counts[sec] = sec_counts.get(sec, 0) + 1
            if len(picked) >= nq:
                break
        return picked

    long_names = _pick(sorted_facts, reverse=True)
    short_names = _pick(sorted_facts, reverse=False)

    longs = {}
    for u in long_names:
        max_val = adva.get(u, float('inf')) * ADV_CAP_FRAC
        cap = 1.0 / len(long_names) if long_names else 0
        longs[u] = min(cap, max_val if max_val > 0 else cap)
    shorts = {}
    for u in short_names:
        max_val = adva.get(u, float('inf')) * ADV_CAP_FRAC
        cap = 1.0 / len(short_names) if short_names else 0
        shorts[u] = min(cap, max_val if max_val > 0 else cap)
    # Normalize
    for side in [longs, shorts]:
        tot = sum(side.values())
        if tot > 0:
            for u in side:
                side[u] /= tot
    return longs, shorts


def _load_adva(con, fdate, underlyings):
    if not underlyings:
        return {}
    ul = ", ".join(f"'{u}'" for u in underlyings)
    rows = con.execute(f"""
        SELECT underlying, AVG(val_in_lakh) * 100000.0
        FROM (SELECT underlying, val_in_lakh,
              ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
              FROM fut.futures_bhavcopy WHERE trade_date <= DATE '{fdate}'
              AND trade_date > DATE '{fdate}' - INTERVAL '30 days'
              AND underlying IN ({ul}) AND inst_type = 'FUTSTK')
        WHERE rn <= 20 AND val_in_lakh IS NOT NULL
        GROUP BY underlying HAVING COUNT(*) >= 10
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def main():
    commit = _git_commit()
    TI_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old DB for clean build
    if TI_DB.exists():
        TI_DB.unlink()

    con = duckdb.connect(str(TI_DB))
    con.execute("""
        CREATE TABLE trades (
            trade_id           VARCHAR PRIMARY KEY,
            underlying         VARCHAR NOT NULL,
            side               VARCHAR NOT NULL,
            entry_date         DATE NOT NULL,
            strategy_name      VARCHAR NOT NULL,
            strategy_version   VARCHAR NOT NULL,
            z_ts               DOUBLE,
            raw_z              DOUBLE,
            quintile           TINYINT,
            rank_in_date       INTEGER,
            basis_reverting    BOOLEAN,
            sector             VARCHAR,
            vix_at_entry       DOUBLE,
            nifty_20d_at_entry DOUBLE,
            exit_date          DATE,
            days_held          INTEGER,
            exit_reason        VARCHAR,
            stock_return       DOUBLE,
            -- Option snapshot (M3 — NULL for historical trades)
            opt_type           VARCHAR,
            opt_strike         DOUBLE,
            opt_expiry         DATE,
            opt_dte            INTEGER,
            opt_premium        DOUBLE,
            opt_oi             BIGINT,
            opt_lot_size       INTEGER
        )
    """)
    con.execute("CREATE INDEX idx_trades_entry ON trades (entry_date)")
    con.execute("CREATE INDEX idx_trades_underlying ON trades (underlying)")
    con.execute("CREATE INDEX idx_trades_exit ON trades (exit_date)")
    con.execute("SET threads=4")

    # Attach source DBs
    con.execute(f"ATTACH '{FACTS_DB}' AS facts (READ_ONLY)")
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")

    # Load sectors
    sectors = _load_sectors()

    # Load all facts for TRAIN+HOLDOUT
    lo = WINDOWS["TRAIN"][0]
    hi = WINDOWS["HOLDOUT"][1]
    print(f"Loading facts {lo} -> {hi}...")
    fact_rows = con.execute(f"""
        SELECT formation_date, underlying, z_carry_neut, raw_z, quintile,
               eligible, basis_reverting
        FROM facts.carry_facts
        WHERE formation_date >= DATE '{lo}' AND formation_date <= DATE '{hi}'
          AND eligible = TRUE AND z_carry_neut IS NOT NULL
        ORDER BY formation_date, z_carry_neut
    """).fetchall()
    print(f"  {len(fact_rows):,} eligible facts")

    # Load forward returns
    print("Loading forward returns...")
    fwd_rows = con.execute(f"""
        SELECT formation_date, underlying, fwd_ret_1m
        FROM sig.signals
        WHERE formation_date >= DATE '{lo}' AND formation_date <= DATE '{hi}'
          AND fwd_ret_1m IS NOT NULL AND liquid = TRUE
    """).fetchall()
    fwd_map = {}
    for fd, u, fr in fwd_rows:
        fwd_map[(fd, u)] = float(fr)
    print(f"  {len(fwd_map):,} forward returns")

    # Load regime
    all_dates = sorted({r[0] for r in fact_rows})
    print(f"Loading regime for {len(all_dates)} dates...")
    regime = _load_index_regime(all_dates)
    nifty_20d = _nifty_20d_return(regime, all_dates)

    # Group facts by date
    by_date = defaultdict(list)
    for fd, u, z, rz, q, elig, br in fact_rows:
        by_date[fd].append((u, float(z), float(rz) if rz else float(z),
                            int(q), bool(br)))

    # Simulate portfolio
    formation_dates = sorted(by_date.keys())
    held_longs = {}
    held_shorts = {}
    trade_entries = {}   # {underlying: {side, entry_date, cum_ret, trade_id}}
    pending_inserts = []  # batch INSERT
    pending_updates = []  # batch UPDATE

    print(f"Simulating {len(formation_dates)} formation dates...")
    inserts, updates, closes, flips = 0, 0, 0, 0
    prev_fdate = None

    for i, fdate in enumerate(formation_dates):
        if i % 500 == 0:
            print(f"  ... {i}/{len(formation_dates)} ({fdate})")

        rows = by_date[fdate]
        ulist = list({r[0] for r in rows})
        adva = _load_adva(con, fdate, ulist)
        filt = [(u, z, rz, br) for u, z, rz, _, br in rows if u in adva]
        if len(filt) < 5:
            continue

        # Compute rank
        z_abs = [(u, abs(z), z, rz, q, br) for u, z, rz, q, br in rows if u in adva]
        z_abs.sort(key=lambda r: r[1], reverse=True)
        rank_map = {}
        for rank_idx, (u, az, z, rz, q, br) in enumerate(z_abs, 1):
            rank_map[u] = rank_idx

        # Compute forward returns for held positions (update cum_ret)
        if prev_fdate is not None:
            for u in list(trade_entries.keys()):
                daily = fwd_map.get((prev_fdate, u))
                if daily is not None and u in held_longs:
                    trade_entries[u]["cum_ret"] = (1 + trade_entries[u]["cum_ret"]) * (1 + daily) - 1
                elif daily is not None and u in held_shorts:
                    trade_entries[u]["cum_ret"] = (1 + trade_entries[u]["cum_ret"]) * (1 - daily) - 1

        # Compute target
        longs_t, shorts_t = _compute_target_book(filt, adva, sectors, MAX_PER_SECTOR)
        all_w = list(longs_t.values()) + list(shorts_t.values())
        sigma_w = float(np.std(all_w)) if len(all_w) > 1 else 0.0
        band = BAND_SIGMA * sigma_w

        # Apply band
        reb_l, reb_s = {}, {}
        for u, t in longs_t.items():
            c = held_longs.get(u, 0.0)
            reb_l[u] = t if abs(t - c) >= band or c == 0 else c
        for u, t in shorts_t.items():
            c = held_shorts.get(u, 0.0)
            reb_s[u] = t if abs(t - c) >= band or c == 0 else c

        # Detect exits (positions in held but not in reb)
        all_active = set(held_longs) | set(held_shorts)
        all_target = set(reb_l) | set(reb_s)

        for u in list(all_active):
            old_side = 'LONG' if u in held_longs else 'SHORT'
            new_side = 'LONG' if u in reb_l else ('SHORT' if u in reb_s else None)

            if new_side is None:
                # CLOSE — exited the book entirely
                entry = trade_entries.get(u)
                if entry:
                    days = (fdate - entry["entry_date"]).days
                    reason = 'EXIT_SIGNAL'  # dropped from quintile
                    pending_updates.append((
                        fdate, days, reason, entry["cum_ret"], entry["trade_id"]
                    ))
                    updates += 1
                    closes += 1
                    del trade_entries[u]
            elif new_side != old_side:
                # FLIP — CLOSE old side, OPEN new side
                entry = trade_entries.get(u)
                if entry:
                    days = (fdate - entry["entry_date"]).days
                    reason = 'EXIT_SIGNAL'
                    pending_updates.append((
                        fdate, days, reason, entry["cum_ret"], entry["trade_id"]
                    ))
                    updates += 1
                    flips += 1
                    del trade_entries[u]

                # OPEN new side
                rz_val = None
                z_val = None
                q_val = None
                br_val = None
                for _u, _z, _rz, _q, _br in rows:
                    if _u == u:
                        z_val = _z
                        rz_val = _rz
                        q_val = _q
                        br_val = _br
                        break
                if z_val is None:
                    continue

                trade_id = f"{u}_{fdate}_{new_side}"
                sec = sectors.get(u, "Unclassified")
                vix_val = regime.get(fdate, (None, None))[0]
                n20 = nifty_20d.get(fdate)
                rank_val = rank_map.get(u, 0)

                pending_inserts.append((
                    trade_id, u, new_side, fdate, STRATEGY_NAME, commit,
                    z_val, rz_val, q_val, rank_val, bool(br_val), sec,
                    vix_val, n20,
                ))
                inserts += 1

                entry = {"entry_date": fdate, "cum_ret": 0.0, "trade_id": trade_id}
                trade_entries[u] = entry
            # else: same side — hold, no trade event

        # Detect entries (in target but not held)
        for u in reb_l:
            if u not in held_longs and u not in trade_entries:
                rz_val = None; z_val = None; q_val = None; br_val = None
                for _u, _z, _rz, _q, _br in rows:
                    if _u == u:
                        z_val = _z; rz_val = _rz; q_val = _q; br_val = _br
                        break
                if z_val is None:
                    continue
                trade_id = f"{u}_{fdate}_LONG"
                sec = sectors.get(u, "Unclassified")
                vix_val = regime.get(fdate, (None, None))[0]
                n20 = nifty_20d.get(fdate)
                rank_val = rank_map.get(u, 0)
                pending_inserts.append((
                    trade_id, u, 'LONG', fdate, STRATEGY_NAME, commit,
                    z_val, rz_val, q_val, rank_val, bool(br_val), sec,
                    vix_val, n20,
                ))
                inserts += 1
                trade_entries[u] = {"entry_date": fdate, "cum_ret": 0.0, "trade_id": trade_id}

        for u in reb_s:
            if u not in held_shorts and u not in trade_entries:
                rz_val = None; z_val = None; q_val = None; br_val = None
                for _u, _z, _rz, _q, _br in rows:
                    if _u == u:
                        z_val = _z; rz_val = _rz; q_val = _q; br_val = _br
                        break
                if z_val is None:
                    continue
                trade_id = f"{u}_{fdate}_SHORT"
                sec = sectors.get(u, "Unclassified")
                vix_val = regime.get(fdate, (None, None))[0]
                n20 = nifty_20d.get(fdate)
                rank_val = rank_map.get(u, 0)
                pending_inserts.append((
                    trade_id, u, 'SHORT', fdate, STRATEGY_NAME, commit,
                    z_val, rz_val, q_val, rank_val, bool(br_val), sec,
                    vix_val, n20,
                ))
                inserts += 1
                trade_entries[u] = {"entry_date": fdate, "cum_ret": 0.0, "trade_id": trade_id}

        # Batch write every 250 formations
        if len(pending_inserts) > 5000:
            con.executemany(
                "INSERT INTO trades (trade_id, underlying, side, entry_date, "
                "strategy_name, strategy_version, z_ts, raw_z, quintile, "
                "rank_in_date, basis_reverting, sector, vix_at_entry, "
                "nifty_20d_at_entry) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                pending_inserts,
            )
            pending_inserts.clear()

        if len(pending_updates) > 5000:
            con.executemany(
                "UPDATE trades SET exit_date=?, days_held=?, exit_reason=?, "
                "stock_return=? WHERE trade_id=?",
                pending_updates,
            )
            pending_updates.clear()

        held_longs = reb_l
        held_shorts = reb_s
        prev_fdate = fdate

    # Flush remaining
    if pending_inserts:
        con.executemany(
            "INSERT INTO trades (trade_id, underlying, side, entry_date, "
            "strategy_name, strategy_version, z_ts, raw_z, quintile, "
            "rank_in_date, basis_reverting, sector, vix_at_entry, "
            "nifty_20d_at_entry) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            pending_inserts,
        )
    if pending_updates:
        con.executemany(
            "UPDATE trades SET exit_date=?, days_held=?, exit_reason=?, "
            "stock_return=? WHERE trade_id=?",
            pending_updates,
        )

    con.close()

    # ── Verification ────────────────────────────────────────────────
    vc = duckdb.connect(str(TI_DB), read_only=True)
    n_total = vc.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    n_closed = vc.execute(
        "SELECT COUNT(*) FROM trades WHERE exit_date IS NOT NULL"
    ).fetchone()[0]
    n_open = vc.execute(
        "SELECT COUNT(*) FROM trades WHERE exit_date IS NULL"
    ).fetchone()[0]
    ms = vc.execute("SELECT AVG(stock_return) FROM trades WHERE stock_return IS NOT NULL").fetchone()[0]
    wr = vc.execute(
        "SELECT AVG(CASE WHEN stock_return > 0 THEN 1 ELSE 0 END) FROM trades WHERE stock_return IS NOT NULL"
    ).fetchone()[0]
    vc.close()

    print(f"\n{'='*60}")
    print(f"  Trade Intelligence — M0 Build Complete")
    print(f"  Total trades:    {n_total:,}")
    print(f"  Closed:          {n_closed:,}")
    print(f"  Open (held at end): {n_open:,}")
    print(f"  Mean stock ret:  {ms*100:+.3f}%" if ms else "  Mean stock ret:  N/A")
    print(f"  Winner ratio:    {wr*100:.1f}%" if wr else "  Winner ratio:    N/A")
    print(f"  Inserts: {inserts:,} | Updates: {updates:,} | Closes: {closes:,} | Flips: {flips:,}")
    print(f"  DB: {TI_DB}")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
