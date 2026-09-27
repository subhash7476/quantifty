"""Live quote capture for STOCK-STRADDLE-M10 (pre-registration section 5).

On the entry (T-10) and exit (T-1) session of each monthly stock-option expiry, snapshot
bid/ask for every F&O stock's same-expiry future and the option strikes around it, in
several passes before the derivatives close. On the entry session also archive the day's
F&O ban file and NSE's corporate-action list over the hold. Nothing is selected here: ATM
choice, eligibility and fills are applied afterwards by the pre-registered rules.

Scheduled daily ~15:15 via scripts/ops/run_if_session.py straddle_capture; it is a no-op
unless today is T-10 or T-1. Exit status is non-zero on a failed capture so the gate alerts.

    python scripts/research/options_seller_edge/straddle_cycle_capture.py            # scheduled
    python scripts/research/options_seller_edge/straddle_cycle_capture.py --dry-run --role entry \
        --expiry 2026-10-27 --immediate --db <scratch>/capture.duckdb
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from core.market.session_schedule import session_window  # noqa: E402
from core.market.trading_calendar import is_session  # noqa: E402

DEFAULT_DB = ROOT / "data" / "research" / "straddle_m10" / "capture.duckdb"
MASTER_DB = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"
BAN_URL = "https://nsearchives.nseindia.com/content/fo/fo_secban.csv"

INDEX_NAMES = frozenset({"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"})
MIN_MONTHLY_NAMES = 100      # a stock monthly expiry lists ~210 names; weeklies/odd dates list <20
ENTRY_OFFSET, EXIT_OFFSET = 10, 1
STRIKE_BAND = 0.10           # capture band; the pre-registered ATM rule uses 5% inside it
PASS_OFFSETS_MIN = (20, 10, 5, 2)   # minutes before the derivatives close; c-5 is primary
CHUNK = 450                  # Upstox market-quote accepts up to 500 keys per call
RETRIES = 3
MIN_FUT_COVERAGE = 0.90

QUOTE_COLS = ("run_id", "instrument_key", "underlying", "instrument_type", "strike", "expiry",
              "lot_size", "ltp", "best_bid", "best_ask", "volume", "oi", "feed_ts", "status")
SCHEMA = """
create table if not exists capture_runs (
  run_id varchar, role varchar, expiry date, trade_date date, pass_label varchar,
  planned_ts timestamp, started_ts timestamp, finished_ts timestamp, master_snapshot date,
  n_keys integer, n_quoted integer, n_api_fail integer, errors varchar);
create table if not exists quotes (
  run_id varchar, instrument_key varchar, underlying varchar, instrument_type varchar,
  strike double, expiry date, lot_size integer, ltp double, best_bid double, best_ask double,
  volume bigint, oi double, feed_ts varchar, status varchar);
create table if not exists artifacts (
  trade_date date, expiry date, kind varchar, fetched_ts timestamp, ok boolean,
  error varchar, body blob);
"""


def sessions_before(expiry: date, n: int, session_fn=is_session) -> date:
    """The n-th regular trading session strictly before `expiry`."""
    d, seen = expiry, 0
    while seen < n:
        d -= timedelta(days=1)
        if session_fn(d):
            seen += 1
    return d


def monthly_expiries(master: duckdb.DuckDBPyConnection, snap: date) -> list[date]:
    rows = master.execute(
        "select expiry, count(distinct name) from instruments where snapshot_date = ? "
        "and instrument_type = 'FUT' group by 1 order by 1", [str(snap)]).fetchall()
    return [date.fromisoformat(str(e)) for e, n in rows if n >= MIN_MONTHLY_NAMES]


def cycle_role(today: date, expiries: list[date], session_fn=is_session):
    """('entry'|'exit', expiry) when today is T-10 / T-1 of the next monthly expiry, else None."""
    upcoming = [e for e in expiries if e > today]
    if not upcoming:
        return None
    e = upcoming[0]
    if today == sessions_before(e, ENTRY_OFFSET, session_fn):
        return "entry", e
    if today == sessions_before(e, EXIT_OFFSET, session_fn):
        return "exit", e
    return None


def load_universe(master: duckdb.DuckDBPyConnection, snap: date, expiry: date):
    q = ("select instrument_key, name as underlying, instrument_type, strike, expiry, lot_size "
         "from instruments where snapshot_date = ? and expiry = ? and instrument_type in ({})")
    futs = master.execute(q.format("'FUT'"), [str(snap), str(expiry)]).df()
    opts = master.execute(q.format("'CE','PE'"), [str(snap), str(expiry)]).df()
    futs = futs[~futs.underlying.isin(INDEX_NAMES)].reset_index(drop=True)
    opts = opts[opts.underlying.isin(set(futs.underlying))].reset_index(drop=True)
    return futs, opts


def _px(v):
    return float(v) if v not in (None, 0, 0.0) else None


def quote_all(md, keys: list[str], sleep=time.sleep):
    """Quote `keys` in chunks. Returns (quotes, api_failed_keys, errors).

    A chunk that still errors after RETRIES is recorded as api_fail, never as an absent
    quote: an API failure must not read as "no market", which would make names ineligible.
    """
    quotes, failed, errors = {}, set(), []
    for i in range(0, len(keys), CHUNK):
        chunk = keys[i:i + CHUNK]
        for attempt in range(RETRIES):
            res = md.fetch_quotes_batch(chunk)
            if not res.get("error"):
                quotes.update(res.get("quotes") or {})
                break
            errors.append(f"chunk {i // CHUNK} attempt {attempt + 1}: {res['error']}")
            sleep(1.0 * (attempt + 1))
        else:
            failed.update(chunk)
        sleep(0.25)
    return quotes, failed, errors


def _rows(run_id, frame, quotes, failed):
    out = []
    for r in frame.itertuples(index=False):
        q = quotes.get(r.instrument_key)
        status = "api_fail" if r.instrument_key in failed else ("ok" if q else "missing")
        q = q or {}
        out.append((run_id, r.instrument_key, r.underlying, r.instrument_type,
                    None if pd.isna(r.strike) else float(r.strike), r.expiry, int(r.lot_size),
                    _px(q.get("ltp")), _px(q.get("best_bid")), _px(q.get("best_ask")),
                    q.get("volume"), q.get("oi"),
                    None if q.get("feed_ts") is None else str(q.get("feed_ts")), status))
    return out


def entry_keys_from_store(con, entry_role: str, expiry: date) -> list[str]:
    return [k for (k,) in con.execute(
        "select distinct q.instrument_key from quotes q join capture_runs r using (run_id) "
        "where r.role = ? and r.expiry = ? and q.instrument_type in ('CE','PE')",
        [entry_role, expiry]).fetchall()]


def run_pass(con, md, role, expiry, snap, futs, opts, label, planned_ts, sleep=time.sleep):
    """One snapshot: futures first, then the option set (band at entry, entry keys at exit)."""
    run_id, started = uuid.uuid4().hex[:12], datetime.now()
    fq, ffail, errors = quote_all(md, list(futs.instrument_key), sleep)
    held = (entry_keys_from_store(con, role.replace("exit", "entry"), expiry)
            if role.endswith("exit") else [])
    if held:
        sel = opts[opts.instrument_key.isin(held)]
    else:
        ltp = {r.underlying: _px(fq.get(r.instrument_key, {}).get("ltp"))
               for r in futs.itertuples(index=False)}
        ref = opts.underlying.map(ltp)
        sel = opts[ref.notna() & ((opts.strike / ref - 1).abs() <= STRIKE_BAND)]
    oq, ofail, oerr = quote_all(md, list(sel.instrument_key), sleep)
    rows = _rows(run_id, futs, fq, ffail) + _rows(run_id, sel, oq, ofail)
    errors += oerr
    frame = pd.DataFrame(rows, columns=QUOTE_COLS)  # noqa: F841 - read by DuckDB below
    con.execute(f"insert into quotes ({','.join(QUOTE_COLS)}) select * from frame")
    con.execute("insert into capture_runs values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [run_id, role, expiry, planned_ts.date(), label, planned_ts, started,
                 datetime.now(), snap, len(rows), sum(r[-1] == "ok" for r in rows),
                 len(ffail) + len(ofail), "; ".join(errors) or None])
    return run_id


def coverage(con, run_id) -> dict:
    """Names with a future quote, names whose 5%-band has a two-sided CE+PE pair, and why not."""
    c = con.execute("""
      with q as (select * from quotes where run_id = ?),
      f as (select underlying, ltp fut from q where instrument_type = 'FUT'),
      o as (select q.*, f.fut from q join f using (underlying)
            where q.instrument_type in ('CE','PE') and abs(q.strike / f.fut - 1) <= 0.05),
      pair as (select underlying, strike,
                 bool_and(best_bid is not null and best_ask is not null) two_sided,
                 bool_and(coalesce(volume, 0) > 0) traded, count(*) legs
               from o group by 1, 2 having count(*) = 2)
      select
        (select count(*) from q where instrument_type = 'FUT') n_names,
        (select count(*) from f where fut is not null) fut_quoted,
        (select count(distinct underlying) from pair where two_sided) names_two_sided,
        (select count(distinct underlying) from pair where two_sided and traded) names_tradable,
        (select count(*) from q where instrument_type <> 'FUT') opt_rows,
        (select avg((best_bid is not null and best_ask is not null)::int) from q
          where instrument_type <> 'FUT' and status = 'ok') opt_two_sided_share,
        (select count(*) from q where status = 'api_fail') api_fail,
        (select count(*) from q where status = 'missing') missing,
        (select count(*) from q where status = 'ok' and (best_bid is null) <> (best_ask is null)) one_sided
    """, [run_id]).fetchone()
    keys = ("names", "fut_quoted", "names_two_sided", "names_tradable", "opt_rows",
            "opt_two_sided_share", "api_fail", "missing", "one_sided")
    return dict(zip(keys, c))


def fetch_artifacts(con, today: date, expiry: date, exit_day: date, http_get=None, ca_fetch=None):
    """Archive the ban file and the forward corporate-action list, raw bytes, one row each."""
    import requests
    http_get = http_get or (lambda url: requests.get(
        url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20))
    if ca_fetch is None:
        from scripts.csmp.download_corporate_actions import fetch as ca_fetch
    jobs = {"fo_secban": lambda: _ok_body(http_get(BAN_URL)),
            "ca_forward": lambda: ca_fetch(today + timedelta(days=1), exit_day)}
    for kind, job in jobs.items():
        body, err = None, None
        try:
            body = job()
        except (Exception, SystemExit) as e:   # ca_fetch sys.exits on a bad NSE response
            err = f"{type(e).__name__}: {e}"
        con.execute("insert into artifacts values (?,?,?,?,?,?,?)",
                    [today, expiry, kind, datetime.now(), body is not None, err, body])


def _ok_body(resp) -> bytes:
    resp.raise_for_status()
    return resp.content


def pass_times(today: date, immediate: bool) -> list[tuple[str, datetime]]:
    close = datetime.combine(today, session_window("derivatives", today)[1])
    if immediate:
        now = datetime.now()
        return [(f"c-{m}", now) for m in PASS_OFFSETS_MIN]
    return [(f"c-{m}", close - timedelta(minutes=m)) for m in PASS_OFFSETS_MIN]


def _telegram(text: str) -> None:
    try:
        from dotenv import load_dotenv
        from core.scheduler.eod_telegram import send_sync
        load_dotenv(ROOT / ".env")
        send_sync(text)
    except Exception as e:  # a failed notification must not fail a completed capture
        print(f"telegram failed: {type(e).__name__}: {e}")


def main(argv=None, md=None, today=None, sleep=time.sleep, notify=_telegram, artifacts_kw=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--master", default=str(MASTER_DB))
    ap.add_argument("--credentials", help="credentials.json to read the token from")
    ap.add_argument("--role", choices=("auto", "entry", "exit"), default="auto")
    ap.add_argument("--expiry", help="YYYY-MM-DD; default: from the calendar")
    ap.add_argument("--dry-run", action="store_true", help="tag runs dry-*, no Telegram")
    ap.add_argument("--immediate", action="store_true", help="take every pass now")
    a = ap.parse_args(argv)
    today = today or date.today()

    if a.credentials:
        import core.auth.credentials as cred
        cred.credentials = cred.CredentialManager(a.credentials)
    master = duckdb.connect(a.master, read_only=True)
    snap = master.execute("select max(snapshot_date) from instruments where snapshot_date <= ?",
                          [str(today)]).fetchone()[0]
    snap = date.fromisoformat(str(snap))
    expiries = monthly_expiries(master, snap)

    if a.role == "auto":
        hit = cycle_role(today, expiries)
        if hit is None:
            print(f"{today}: not a T-{ENTRY_OFFSET} or T-{EXIT_OFFSET} session - nothing to capture")
            return 0
        role, expiry = hit
    else:
        role = a.role
        expiry = date.fromisoformat(a.expiry) if a.expiry else next(e for e in expiries if e > today)
    tag = f"dry-{role}" if a.dry_run else role
    close = datetime.combine(today, session_window("derivatives", today)[1])
    if not a.immediate and datetime.now() >= close:
        print(f"{tag} {today}: started after the derivatives close {close:%H:%M} - no live quotes")
        return 1
    futs, opts = load_universe(master, snap, expiry)
    master.close()
    print(f"{tag} {today} expiry {expiry} master {snap}: {len(futs)} stock futures, "
          f"{len(opts)} options listed")

    if md is None:
        from core.brokers.upstox_market_data import UpstoxMarketData
        md = UpstoxMarketData()
    Path(a.db).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(a.db)
    con.execute(SCHEMA)
    con.close()

    if role == "entry":
        con = duckdb.connect(a.db)
        fetch_artifacts(con, today, expiry, sessions_before(expiry, EXIT_OFFSET),
                        **(artifacts_kw or {}))
        for kind, ok, err in con.execute(
                "select kind, ok, error from artifacts where trade_date = ? and expiry = ? "
                "order by fetched_ts desc limit 2", [today, expiry]).fetchall():
            print(f"  artifact {kind}: {'ok' if ok else 'FAILED ' + str(err)}")
        con.close()

    results = []
    for label, planned in pass_times(today, a.immediate):
        wait = (planned - datetime.now()).total_seconds()
        if wait > 0:
            sleep(wait)
        con = duckdb.connect(a.db)
        run_id = run_pass(con, md, tag, expiry, snap, futs, opts, label, planned, sleep)
        cov = coverage(con, run_id)
        con.close()
        results.append((label, cov))
        share = cov["opt_two_sided_share"]
        print(f"  {label} {datetime.now():%H:%M:%S}: futures {cov['fut_quoted']}/{cov['names']}, "
              f"names two-sided in 5% band {cov['names_two_sided']} (traded {cov['names_tradable']}), "
              f"option rows {cov['opt_rows']} two-sided {0 if share is None else share:.1%}, "
              f"api_fail {cov['api_fail']} missing {cov['missing']} one-sided {cov['one_sided']}")

    bad = [lb for lb, c in results
           if c["api_fail"] or c["names"] == 0 or c["fut_quoted"] / c["names"] < MIN_FUT_COVERAGE]
    primary = dict(results).get("c-5")
    summary = (f"STRADDLE-M10 {tag} {today} (exp {expiry}): c-5 futures "
               f"{primary['fut_quoted']}/{primary['names']}, two-sided names "
               f"{primary['names_two_sided']}" + (f"; FAILED passes {bad}" if bad else ""))
    print(summary)
    if not a.dry_run:
        notify(summary)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
