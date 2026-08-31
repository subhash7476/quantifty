"""MRLC-test forward paper scanner (daily cadence).

Nightly run AFTER the EOD bhavcopy ingest lands (ops EOD / download_all_data.py):

    python scripts/mrlc_test/scanner.py run            # detect + fill + track
    python scripts/mrlc_test/scanner.py status         # open trades + summary
    python scripts/mrlc_test/scanner.py run --as-of YYYY-MM-DD   # replay test

Logic reuses the backtest engine (run_symbol / _simulate) so the paper record is
byte-consistent with the validated backtest. Signals: stretch >=10% below the
prior-day 25-SMA + sweep (close below 10-session low on >=2x median volume) +
reclaim close within 3 bars + news guard (no >=8% crash in prior 3 sessions).
Entry = next session open. Exit = 50% at prior-day 25-SMA, 50% break-even then
2x ATR trail, 20-session time stop. Ledger: data/mrlc_test/paper/paper.duckdb.

NOTE: prices come from the CA-adjusted view (backward-adjusted). A corporate
action can revise past adjusted closes retroactively — disclosed approximation;
fills are real next-open prices.
"""
import sys
import argparse
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.equity.delivery_fees import delivery_equity_fees  # noqa: E402
from scripts.mrlc_test.engine import (  # noqa: E402
    run_symbol, _simulate, _crash_near, NEWS_WINDOW, RECLAIM_MAX_BARS,
    VOL_MULT, MIN_STRETCH, SMA_DAYS, SUPPORT_SESSIONS,
)

ADJ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
PAPER_DB = ROOT / "data" / "mrlc_test" / "paper" / "paper.duckdb"
TICKERS_CSV = ROOT / "data" / "mrlc_test" / "live_tickers.csv"
LOOKBACK_DAYS = 130          # ~85 sessions, enough for SMA25 + support + guards


# ---------------------------------------------------------------- mapping
def build_live_tickers(force=False):
    if TICKERS_CSV.exists() and not force:
        return pd.read_csv(TICKERS_CSV)["ticker"].tolist()
    uni = pd.read_csv(ROOT / "data" / "mrlc_test" / "universe.csv")["symbol"]
    isins = {s.split("|")[1] for s in uni}
    con = duckdb.connect(str(ADJ_DB), read_only=True)
    rows = con.execute("SELECT symbol, isin FROM symbol_isin").fetchall()
    rows += con.execute(
        "SELECT symbol, isin FROM instrument_master WHERE isin IS NOT NULL"
    ).fetchall()
    con.close()
    by_isin = {}
    for s, i in rows:
        by_isin.setdefault(i, s)
    tickers = sorted({by_isin[i] for i in isins if i in by_isin})
    pd.DataFrame({"ticker": tickers}).to_csv(TICKERS_CSV, index=False)
    print(f"live tickers: {len(tickers)} mapped (of {len(isins)} ISINs)")
    return tickers


# ---------------------------------------------------------------- ledger
def connect():
    PAPER_DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(PAPER_DB))
    con.execute("""CREATE TABLE IF NOT EXISTS signals (
        signal_id INTEGER PRIMARY KEY, symbol VARCHAR, signal_date DATE,
        stretch_pct DOUBLE, support DOUBLE, sweep_low DOUBLE, sl DOUBLE,
        tp DOUBLE, atr_sig DOUBLE, entry_date DATE, entry_price DOUBLE,
        status VARCHAR, note VARCHAR, created_at TIMESTAMP)""")
    con.execute("""CREATE TABLE IF NOT EXISTS trades (
        trade_id INTEGER PRIMARY KEY, signal_id INTEGER, symbol VARCHAR,
        signal_date DATE, entry_date DATE, entry_price DOUBLE, sl DOUBLE,
        tp DOUBLE, atr_sig DOUBLE,
        exit1_date DATE, exit1_price DOUBLE, reason1 VARCHAR,
        exit2_date DATE, exit2_price DOUBLE, reason2 VARCHAR,
        hold_sessions INTEGER, r_gross DOUBLE, r_net DOUBLE,
        fees_rs DOUBLE, status VARCHAR)""")
    con.execute("""CREATE TABLE IF NOT EXISTS run_log (
        run_date DATE, as_of DATE, scanned INTEGER, new_signals INTEGER,
        filled INTEGER, closed INTEGER, note VARCHAR)""")
    return con


# ---------------------------------------------------------------- data
def load_recent(con, as_of):
    as_of = as_of or date.today()
    lo = (as_of - timedelta(days=LOOKBACK_DAYS)).isoformat()
    con.execute(f"ATTACH '{ADJ_DB.as_posix()}' AS adj (READ_ONLY)")
    con.execute("DROP TABLE IF EXISTS recent")
    con.execute(f"""CREATE TABLE recent AS
        SELECT trade_date, symbol, open, high, low, close, volume
        FROM adj.equity_bhavcopy_adjusted
        WHERE trade_date >= '{lo}' AND trade_date <= '{as_of.isoformat()}'""")
    con.execute("DETACH adj")


def bars_for(con, ticker):
    return con.execute(
        "SELECT trade_date AS ts, open, high, low, close, volume "
        "FROM recent WHERE symbol = ? ORDER BY trade_date", [ticker]).fetchdf()


# ---------------------------------------------------------------- detect
def detect_last_bar_signal(bars, daily):
    """Signal whose reclaim bar is the FINAL session (entry bar does not exist yet)."""
    if len(bars) < 30:
        return []
    close = bars["close"].to_numpy()
    low = bars["low"].to_numpy()
    volume = bars["volume"].to_numpy()
    n = len(bars)
    daily_close = daily["close"].to_numpy()
    ranks = pd.to_datetime(bars["ts"].dt.date).map(
        {d: r for r, d in enumerate(pd.to_datetime(daily["ts"].dt.date))}).to_numpy()
    daily_ret = np.full(len(daily_close), np.nan)
    daily_ret[1:] = np.diff(daily_close) / daily_close[:-1]
    j = n - 1
    rj = ranks[j]
    if rj is None or rj < max(SMA_DAYS, SUPPORT_SESSIONS):
        return []
    sma = float(daily_close[rj - SMA_DAYS:rj].mean())
    if np.isnan(sma):
        return []
    div = (close[j] - sma) / sma
    if div > -MIN_STRETCH or _crash_near(daily_ret, rj):
        return []
    sup = float(low[:j][ranks[:j] >= rj - SUPPORT_SESSIONS].min()) if (ranks[:j] >= rj - SUPPORT_SESSIONS).any() else None
    if sup is None:
        return []
    for k in range(1, RECLAIM_MAX_BARS + 1):
        i = j - k
        if i < 0:
            break
        ri = ranks[i]
        if ri is None:
            continue
        sup_i = float(low[:i][ranks[:i] >= ri - SUPPORT_SESSIONS].min()) if (ranks[:i] >= ri - SUPPORT_SESSIONS).any() else None
        if sup_i is None:
            continue
        med_i = pd.Series(volume[:i]).rolling(20, min_periods=20).median().iloc[-1]
        if np.isnan(med_i):
            continue
        if (close[i] < sup_i and low[i] < sup_i
                and volume[i] >= VOL_MULT * med_i and close[j] > sup_i):
            sweep_low = float(low[i:j + 1].min())
            atr = _atr14(bars).to_numpy()[j]
            if np.isnan(atr):
                return []
            return [dict(signal_date=pd.to_datetime(bars["ts"].iloc[j]).date(),
                         stretch_pct=div * 100, support=sup_i, sweep_low=sweep_low,
                         sl=sweep_low - 2.0 * atr, tp=sma, atr_sig=atr)]
    return []


def _atr14(bars):
    tr = pd.concat([
        bars["high"] - bars["low"],
        (bars["high"] - bars["close"].shift(1)).abs(),
        (bars["low"] - bars["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()


# ---------------------------------------------------------------- pipeline
def run_pipeline(as_of=None, verbose=True):
    as_of = as_of or date.today()
    con = connect()
    load_recent(con, as_of)
    tickers = build_live_tickers()
    existing = set()
    n_sig = con.execute("SELECT count(*) FROM signals").fetchone()[0]
    if n_sig:
        existing = {r[0] for r in con.execute(
            "SELECT symbol || '|' || signal_date FROM signals").fetchall()}
    n_tr = con.execute("SELECT count(*) FROM trades").fetchone()[0]
    if n_tr:
        existing |= {r[0] for r in con.execute(
            "SELECT symbol || '|' || signal_date FROM trades").fetchall()}
    new_signals = filled = closed = 0
    scanned = 0

    closed += _fill_and_track(con, tickers, verbose)

    for tk in tickers:
        bars = bars_for(con, tk)
        if len(bars) < 30:
            continue
        daily = bars.copy()
        scanned += 1
        if con.execute("SELECT count(*) FROM trades WHERE symbol = ? AND status = 'OPEN'",
                       [tk]).fetchone()[0] > 0:
            continue

        found = run_symbol(bars, daily, 2.0, tk, "1d_ext", news_guard=True)
        for tr in found:
            key = f"{tk}|{pd.Timestamp(tr['signal_date']).date()}"
            if key in existing:
                continue
            existing.add(key)
            if tr["reason1"] == "OPEN_END" or tr["reason2"] == "OPEN_END":
                status, note = "OPEN", "filled at next open"
                _save_trade(con, tk, tr, "OPEN")
            else:
                status, note = "CLOSED", "backfilled (already exited)"
                _save_trade(con, tk, tr, "CLOSED")
            new_signals += 1
            if verbose:
                print(f"  SIGNAL {tk} {tr['signal_date'].date()} div={tr['divergence_pct']:.1f}% "
                      f"-> {status}")

        last = detect_last_bar_signal(bars, daily)
        for sig in last:
            key = f"{tk}|{sig['signal_date']}"
            if key in existing:
                continue
            existing.add(key)
            sid = _insert_signal(con, tk, sig, "PENDING_ENTRY")
            new_signals += 1
            if verbose:
                print(f"  SIGNAL {tk} {sig['signal_date']} div={sig['stretch_pct']:.1f}% "
                      f"-> PENDING_ENTRY (enter at next open)")

    closed += _fill_and_track(con, tickers, verbose)
    con.execute("INSERT INTO run_log VALUES (?, ?, ?, ?, ?, ?, ?)",
                [date.today(), as_of, scanned, new_signals, 0, closed,
                 "run"])
    print(f"run @ {as_of}: scanned {scanned} tickers, {new_signals} new signals, "
          f"{closed} closed")
    con.close()


def _insert_signal(con, tk, sig, status):
    sid = con.execute("SELECT COALESCE(MAX(signal_id), 0) + 1 FROM signals").fetchone()[0]
    con.execute("INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [sid, tk, sig["signal_date"], sig["stretch_pct"], sig["support"],
                 sig["sweep_low"], sig["sl"], sig["tp"], sig["atr_sig"],
                 None, None, status, "", pd.Timestamp.now()])
    return sid


def _fill_and_track(con, tickers, verbose):
    """Fill PENDING_ENTRY signals whose entry session now exists; track open trades."""
    closed = 0
    pending = con.execute(
        "SELECT signal_id, symbol, signal_date FROM signals WHERE status = 'PENDING_ENTRY'"
    ).fetchall()
    for sid, tk, sig_date in pending:
        if con.execute(
            "SELECT count(*) FROM trades WHERE symbol = ? AND status = 'OPEN'",
            [tk]).fetchone()[0] > 0:
            con.execute("UPDATE signals SET status = 'SKIPPED_OVERLAP' "
                        "WHERE signal_id = ?", [sid])
            continue
        bars = bars_for(con, tk)
        daily = bars.copy()
        sig_date = pd.Timestamp(sig_date)
        dates = pd.to_datetime(bars["ts"].dt.date).tolist()
        if not any(d > sig_date for d in dates):
            continue
        nxt = min(d for d in dates if d > sig_date)
        idx = dates.index(nxt)
        row = con.execute("SELECT * FROM signals WHERE signal_id = ?", [sid]).fetchone()
        entry = float(bars["open"].iloc[idx])
        if entry <= 0:
            continue
        ranks = pd.Series(dates).map(
            {d: r for r, d in enumerate(pd.to_datetime(daily["ts"].dt.date))}).to_numpy()
        rank_to_date = {r: daily["ts"].iloc[r] for r in range(len(daily))}
        rec, _ = _simulate(bars, ranks, rank_to_date, daily, entry, row[6], row[7],
                           row[8], idx, tk, "1d_ext", row[3] / 100.0, 2.0,
                           row[5], row[4], daily["ts"].iloc[ranks[idx - 1]]
                           if idx - 1 >= 0 else daily["ts"].iloc[0])
        con.execute("UPDATE signals SET entry_date = ?, entry_price = ?, status = 'OPEN' "
                    "WHERE signal_id = ?", [daily["ts"].iloc[idx].date(), entry, sid])
        _save_trade(con, tk, rec, "OPEN")
        if verbose:
            print(f"  FILL {tk} entry {entry:.2f} on {daily['ts'].iloc[idx].date()}")

    open_rows = con.execute("SELECT trade_id, symbol FROM trades WHERE status = 'OPEN'").fetchall()
    for tid, tk in open_rows:
        bars = bars_for(con, tk)
        daily = bars.copy()
        row = con.execute(
            "SELECT signal_id, signal_date, entry_price, sl, tp, atr_sig, entry_date "
            "FROM trades WHERE trade_id = ?", [tid]).fetchone()
        dates = pd.to_datetime(daily["ts"].dt.date).tolist()
        try:
            idx = dates.index(pd.Timestamp(row[6]))
        except ValueError:
            continue
        ranks = pd.Series(dates).map(
            {d: r for r, d in enumerate(pd.to_datetime(daily["ts"].dt.date))}).to_numpy()
        rank_to_date = {r: daily["ts"].iloc[r] for r in range(len(daily))}
        rec, _ = _simulate(bars, ranks, rank_to_date, daily, row[2], row[3], row[4],
                           row[5], idx, tk, "1d_ext", 0.0, 2.0, 0.0, 0.0,
                           pd.Timestamp(row[1]))
        if rec["reason1"] != "OPEN_END" and rec["reason2"] != "OPEN_END":
            _save_trade(con, tk, rec, "CLOSED")
            closed += 1
            if verbose:
                print(f"  CLOSE {tk} entry {row[2]:.2f} -> {rec['reason1']}/{rec['reason2']} "
                      f"r_net {rec['r_net']:.2f}")
    return closed


def _save_trade(con, tk, rec, status):
    entry_d = pd.Timestamp(rec["entry_date"]).date() if rec["entry_date"] is not None else None
    sig_d = pd.Timestamp(rec["signal_date"]).date() if rec["signal_date"] is not None else None
    if status == "CLOSED":
        row = con.execute(
            "SELECT trade_id FROM trades WHERE symbol = ? AND signal_date = ? "
            "AND status = 'OPEN'",
            [tk, sig_d]).fetchone()
        if row:
            con.execute(
                "UPDATE trades SET exit1_date = ?, exit1_price = ?, reason1 = ?, "
                "exit2_date = ?, exit2_price = ?, reason2 = ?, hold_sessions = ?, "
                "r_gross = ?, r_net = ?, fees_rs = ?, status = 'CLOSED' "
                "WHERE trade_id = ?",
                [pd.Timestamp(rec["exit1_date"]).date() if rec["exit1_date"] is not None else None,
                 rec["exit1_price"], rec["reason1"],
                 pd.Timestamp(rec["exit2_date"]).date() if rec["exit2_date"] is not None else None,
                 rec["exit2_price"], rec["reason2"], rec["hold_sessions"],
                 rec["r_gross"], rec["r_net"], rec["fees_rs"], row[0]])
            return
    tid = con.execute("SELECT COALESCE(MAX(trade_id), 0) + 1 FROM trades").fetchone()[0]
    con.execute(
        "INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [tid, rec.get("signal_id", 0), tk, sig_d, entry_d,
         rec["entry"], rec["sl"], rec["tp"], rec["atr_sig"],
         pd.Timestamp(rec["exit1_date"]).date() if rec["exit1_date"] is not None else None,
         rec["exit1_price"], rec["reason1"],
         pd.Timestamp(rec["exit2_date"]).date() if rec["exit2_date"] is not None else None,
         rec["exit2_price"], rec["reason2"], rec["hold_sessions"],
         rec["r_gross"], rec["r_net"], rec["fees_rs"], status])


def status():
    con = connect()
    n_sig = con.execute("SELECT count(*) FROM signals").fetchone()[0]
    open_ = con.execute(
        "SELECT symbol, entry_date, entry_price, sl, tp "
        "FROM trades WHERE status = 'OPEN'").fetchall()
    print(f"signals: {n_sig}, open: {len(open_)}")
    for r in open_:
        print(f"  OPEN {r[0]} entry {r[1]} @ {r[2]:.2f} sl {r[3]:.2f} tp {r[4]:.2f}")
    hist = con.execute(
        "SELECT count(*), sum(r_net), avg(r_net) FROM trades WHERE status = 'CLOSED'"
    ).fetchone()
    print(f"closed: {hist[0]}, total net R {hist[1]:.2f}, avg {hist[2]:.2f}")
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "status"])
    ap.add_argument("--as-of")
    args = ap.parse_args()
    if args.cmd == "run":
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
        run_pipeline(as_of)
    else:
        status()
