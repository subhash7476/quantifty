"""Score STOCK-STRADDLE-M10 cycles from the capture store, by the FROZEN pre-registration
(docs/reports/strategies/STOCK_STRADDLE_M10_PRE_REGISTRATION.md, SHA-256 03672fd0...).

One cycle = one monthly expiry E. From the entry (T-10) capture it applies section 3 eligibility
(U1-U5) and the section 4 ATM rule; from the exit (T-1) capture the section 6 fills, fees and
missing-quote fallback; then the section 7 equal-weight cycle mean and the section 8 void rule.
Per-name rows and the cycle row go to the cycles store; re-scoring a cycle replaces its rows.
`summary()` gives the section 1 test and the section 9 falsification state over counted cycles.

    python scripts/research/options_seller_edge/straddle_cycle_evaluate.py --expiry 2026-10-27
    python scripts/research/options_seller_edge/straddle_cycle_evaluate.py --summary
    python scripts/research/options_seller_edge/straddle_cycle_evaluate.py --dry --entry-only \
        --expiry 2026-10-27 --entry-date 2026-09-28 --capture-db <dryrun.duckdb>
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from datetime import date, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from core.execution.options.fees import option_order_fees  # noqa: E402  (read-only import)
from scripts.research.options_seller_edge.straddle_cycle_capture import (  # noqa: E402
    DEFAULT_DB, ENTRY_OFFSET, EXIT_OFFSET, FUTURES_DB, MIN_FUT_COVERAGE, sessions_before)

CYCLES_DB = ROOT / "data" / "research" / "straddle_m10" / "cycles.duckdb"
OPTIONS_BHAV_DB = ROOT / "data" / "market_data" / "stock_options_bhavcopy.duckdb"

PASS_ORDER = ("c-5", "c-2", "c-10", "c-20")    # sections 4 and 6
MAX_LATE_S = 60                                # section 4: a pass counts only if on time
ATM_BAND = 0.05                                # strictly within 5 %
DIVIDEND_LIMIT = 0.02                          # D5
EXIT_MARKUP = 1.10                             # D7 exit fallback
N_WINDOW, T_CRIT = 36, 1.690                   # section 1: t(0.95, 35)
F1_T, F2_CUM, FALSIFY_FROM = 2.33, -1.0, 6     # section 9

NAME_COLS = ("expiry", "role", "underlying", "lot_size", "status", "entry_pass", "strike",
             "ce_key", "pe_key", "fut_ltp", "ce_bid", "pe_bid", "ce_ask", "pe_ask",
             "ce_exit_src", "pe_exit_src", "fees", "gross", "net")
SCHEMA = """
create table if not exists cycle_names (
  expiry date, role varchar, underlying varchar, lot_size integer, status varchar,
  entry_pass varchar, strike double, ce_key varchar, pe_key varchar, fut_ltp double,
  ce_bid double, pe_bid double, ce_ask double, pe_ask double, ce_exit_src varchar,
  pe_exit_src varchar, fees double, gross double, net double);
create table if not exists cycles (
  expiry date, role varchar, entry_date date, exit_date date, scored_ts timestamp, void boolean,
  void_reason varchar, n_universe integer, n_eligible integer, cycle_gross double,
  cycle_net double, fallback_legs integer, ban_source varchar, ca_source varchar,
  excl_u2 integer, excl_u3 integer, excl_u4 integer, excl_u5 integer);
"""


# ---------------------------------------------------------------- capture store reads

def usable_passes(cap, role: str, expiry: date, trade_date: date) -> dict[str, str]:
    """label -> run_id for the passes of (role, expiry, trade_date) that started on time."""
    rows = cap.execute(
        "select pass_label, run_id, epoch(started_ts) - epoch(planned_ts) from capture_runs "
        "where role = ? and expiry = ? and trade_date = ? order by started_ts",
        [role, expiry, trade_date]).fetchall()
    return {lb: rid for lb, rid, late in rows if late <= MAX_LATE_S}


def _quotes(cap, run_id: str) -> pd.DataFrame:
    return cap.execute("select * from quotes where run_id = ?", [run_id]).df()


def pick_atm(q: pd.DataFrame) -> pd.DataFrame:
    """Section 4 on one pass: per name, the traded two-sided strike nearest the future LTP."""
    fut = q[q.instrument_type == "FUT"].set_index("underlying")
    fut = fut[(fut.status == "ok") & fut.ltp.notna()]
    vol = pd.to_numeric(q.volume, errors="coerce").fillna(0)
    o = q[q.instrument_type.isin(["CE", "PE"]) & q.best_bid.notna() & q.best_ask.notna() & (vol > 0)]
    ce = o[o.instrument_type == "CE"].set_index(["underlying", "strike"])
    pe = o[o.instrument_type == "PE"].set_index(["underlying", "strike"])
    pair = ce.join(pe, lsuffix="_ce", rsuffix="_pe", how="inner").reset_index()
    pair = pair[pair.underlying.isin(fut.index)]
    pair["fut_ltp"] = pair.underlying.map(fut.ltp)
    pair["dist"] = (pair.strike - pair.fut_ltp).abs()
    pair = pair.sort_values(["underlying", "dist", "strike"]).groupby("underlying").head(1)
    pair = pair[(pair.strike / pair.fut_ltp - 1).abs() < ATM_BAND]
    return pair.set_index("underlying")


def entry_selection(cap, role: str, expiry: date, entry_date: date):
    """(universe frame, chosen ATM per name, per-pass futures coverage) from the entry capture."""
    passes = usable_passes(cap, role, expiry, entry_date)
    quotes = {lb: _quotes(cap, rid) for lb, rid in passes.items()}
    uni = pd.concat([q[q.instrument_type == "FUT"][["underlying", "lot_size"]] for q in quotes.values()]
                    ).drop_duplicates("underlying") if quotes else pd.DataFrame(columns=["underlying", "lot_size"])
    coverage = {}
    for lb, q in quotes.items():
        f = q[q.instrument_type == "FUT"]
        coverage[lb] = (f.ltp.notna() & (f.status == "ok")).mean() if len(f) else 0.0
    chosen = {}
    for lb in PASS_ORDER:
        if lb not in quotes:
            continue
        atm = pick_atm(quotes[lb])
        for name, r in atm.iterrows():
            if name not in chosen:
                chosen[name] = dict(entry_pass=lb, strike=r.strike, ce_key=r.instrument_key_ce,
                                    pe_key=r.instrument_key_pe, fut_ltp=r.fut_ltp,
                                    ce_bid=r.best_bid_ce, pe_bid=r.best_bid_pe)
    return uni, pd.DataFrame.from_dict(chosen, orient="index"), coverage


def _artifact(cap, kind: str, expiry: date, entry_date: date):
    row = cap.execute(
        "select body from artifacts where kind = ? and expiry = ? and trade_date = ? and ok "
        "order by fetched_ts desc limit 1", [kind, expiry, entry_date]).fetchone()
    return None if row is None else bytes(row[0])


# ---------------------------------------------------------------- U3 / U4 / U5

def history_pass(futures_db: str, entry_date: date, prev_session: date) -> set[str]:
    """U3 through T-11: n20 >= 15, n60 >= 40, rv20 > 0 on front-future daily log returns
    (same contract, consecutive sessions, |ln r| >= 0.25 excluded), as build_stock_straddles."""
    con = duckdb.connect(futures_db, read_only=True)
    try:
        last = con.execute("select max(trade_date) from futures_bhavcopy where trade_date < ?",
                           [entry_date]).fetchone()[0]
        if last != prev_session:
            raise RuntimeError(f"futures_bhavcopy ends {last}; U3 needs T-11 = {prev_session}")
        df = con.execute("""
          with b as (select underlying, expiry_dt, trade_date, close from futures_bhavcopy
                     where inst_type = 'FUTSTK' and trade_date <= ?
                       and trade_date > ?::date - interval 200 day),
          d as (select trade_date, row_number() over (order by trade_date) di
                from (select distinct trade_date from futures_bhavcopy
                      where inst_type in ('FUTSTK','FUTIDX') and trade_date <= ?
                        and trade_date > ?::date - interval 200 day)),
          front as (select underlying, trade_date, min(expiry_dt) fe from b
                    where expiry_dt >= trade_date group by 1, 2),
          c as (select b.underlying, b.expiry_dt, b.trade_date, d.di, b.close,
                       lag(b.close) over w pc, lag(d.di) over w pdi
                from b join d using (trade_date) where b.close > 0
                window w as (partition by b.underlying, b.expiry_dt order by b.trade_date))
          select c.underlying, c.di,
                 case when pdi = di - 1 and abs(ln(close / pc)) < 0.25 then ln(close / pc) end r
          from c join front f on c.underlying = f.underlying and c.trade_date = f.trade_date
                             and c.expiry_dt = f.fe
        """, [prev_session] * 4).df()
    finally:
        con.close()
    last_di = df.di.max()
    ok = set()
    for name, g in df.sort_values("di").groupby("underlying"):
        if g.di.iloc[-1] != last_di:
            continue                    # no front-future row on T-11
        r20, r60 = g.r.iloc[-20:].dropna(), g.r.iloc[-60:].dropna()
        if len(r20) >= 15 and len(r60) >= 40 and r20.std() > 0:
            ok.add(name)
    return ok


def ban_set(body: bytes | None, entry_date: date):
    """U4 / D6: the ban file counts only if its header names the entry date."""
    if not body:
        return set(), "none (no ban file)"
    text = body.decode("utf-8-sig").strip().splitlines()
    m = re.search(r"Trade Date\s+(\d{2}-[A-Za-z]{3}-\d{4})", text[0]) if text else None
    if not m or datetime.strptime(m.group(1), "%d-%b-%Y").date() != entry_date:
        return set(), f"none (ban file header {text[0][:60] if text else ''!r} != entry date)"
    names = {ln.split(",", 1)[1].strip() for ln in text[1:] if "," in ln}
    return names, "captured fo_secban"


_AMOUNT = re.compile(r"R[se]\.?\s*(\d+(?:\.\d+)?)", re.I)
_SPLIT = re.compile(r"/|\band\b", re.I)
_NIL = re.compile(r"\bnil\b")


def purpose_components(purpose: str) -> tuple[bool, list]:
    """(has a price-adjusting action, dividend amounts per share) for one NSE PURPOSE string.

    NSE combines actions in one purpose ("Bonus 1:1/ Dividend- Rs 5 Per Share", "Annual General
    Meeting / Dividend - Re 0.60/- Per Share / Bonus 1 : 1"). "/-" is a rupee suffix, not a
    separator, and "(Purpose Revised)" is a note. A general-meeting component is neutral; a
    dividend component contributes its amount (0 for "NIL", None if unreadable); anything else
    adjusts price.
    """
    text = re.sub(r"\([^)]*\)", " ", purpose.replace("/-", " "))
    adjusting, amounts = False, []
    for part in (p.strip(" -") for p in _SPLIT.split(text)):
        low = part.lower()
        if not low or "general meeting" in low:
            continue
        if "dividend" in low:
            m = _AMOUNT.search(part)
            amounts.append(float(m.group(1)) if m else 0.0 if _NIL.search(low) else None)
        else:
            adjusting = True
    return adjusting, amounts


def ca_excluded(body: bytes | None, entry_date: date, exit_date: date, fut_ltp: dict) -> tuple:
    """U5 / D5: ex-date in (entry, exit] for any purpose but a dividend, or a dividend >= 2 % of
    the entry future LTP. A dividend whose amount cannot be read is excluded (conservative)."""
    if body is None:
        return set(), "none (no CA list)"
    out = set()
    for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig"))):
        sym = (row.get("SYMBOL") or "").strip()
        if sym not in fut_ltp:
            continue
        ex = datetime.strptime(row["EX-DATE"].strip(), "%d-%b-%Y").date()
        if not (entry_date < ex <= exit_date):
            continue
        adjusting, amounts = purpose_components(row.get("PURPOSE") or "")
        if adjusting or None in amounts or sum(amounts) >= DIVIDEND_LIMIT * fut_ltp[sym]:
            out.add(sym)
    return out, "captured ca_forward" if body else "captured ca_forward (none announced)"


# ---------------------------------------------------------------- exit fills

def exit_prices(cap, role: str, expiry: date, exit_date: date, keys: list[str],
                options_bhav_db: str):
    """key -> (ask, source). Section 6: first usable pass with an ask in PASS_ORDER, else
    1.10 x max(highest captured LTP that day, T-1 bhavcopy close / settle if untraded)."""
    passes = usable_passes(cap, role, expiry, exit_date)
    wanted, out = set(keys), {}
    for lb in PASS_ORDER:
        if lb not in passes:
            continue
        q = cap.execute("select instrument_key, best_ask from quotes where run_id = ? and "
                        "best_ask is not null", [passes[lb]]).fetchall()
        for k, ask in q:
            if k in wanted and k not in out:
                out[k] = (ask, lb)
    missing = [k for k in keys if k not in out]
    if missing:
        ltp = dict(cap.execute(
            "select q.instrument_key, max(q.ltp) from quotes q join capture_runs r using (run_id) "
            "where r.role = ? and r.expiry = ? and r.trade_date = ? group by 1",
            [role, expiry, exit_date]).fetchall())
        bhav = _bhav_marks(cap, missing, expiry, exit_date, options_bhav_db)
        for k in missing:
            ref = max(v for v in (ltp.get(k), bhav.get(k)) if v is not None) \
                if (ltp.get(k) is not None or bhav.get(k) is not None) else None
            if ref is None:
                raise RuntimeError(f"no exit ask, LTP or T-1 bhavcopy mark for {k} - "
                                   f"score after the {exit_date} bhavcopy is ingested")
            out[k] = (EXIT_MARKUP * ref, "fallback")
    return out


def _bhav_marks(cap, keys, expiry, exit_date, options_bhav_db):
    legs = cap.execute(
        "select distinct instrument_key, underlying, strike, instrument_type from quotes "
        f"where instrument_key in ({','.join('?' * len(keys))})", keys).fetchall()
    con = duckdb.connect(options_bhav_db, read_only=True)
    try:
        out = {}
        for k, u, strike, t in legs:
            r = con.execute(
                "select case when contracts > 0 then close else settle end from stock_options_bhavcopy "
                "where trade_date = ? and underlying = ? and expiry_dt = ? and strike = ? and option_type = ?",
                [exit_date, u, expiry, strike, t]).fetchone()
            if r and r[0]:
                out[k] = float(r[0])
        return out
    finally:
        con.close()


def name_fees(ce_bid, pe_bid, ce_ask, pe_ask, lot, entry_date, exit_date) -> float:
    """Section 6: four orders (2 SELL at entry, 2 BUY at exit), quantity = lot size, rupees."""
    return sum(option_order_fees(premium=p, quantity=lot, side=s, trade_date=d).total
               for p, s, d in ((ce_bid, "SELL", entry_date), (pe_bid, "SELL", entry_date),
                               (ce_ask, "BUY", exit_date), (pe_ask, "BUY", exit_date)))


# ---------------------------------------------------------------- one cycle

def score_cycle(expiry: date, *, capture_db=str(DEFAULT_DB), futures_db=str(FUTURES_DB),
                options_bhav_db=str(OPTIONS_BHAV_DB), dry=False, entry_date=None, exit_date=None,
                entry_only=False, ban_file=None, ca_file=None):
    entry_date = entry_date or sessions_before(expiry, ENTRY_OFFSET)
    exit_date = exit_date or sessions_before(expiry, EXIT_OFFSET)
    prefix = "dry-" if dry else ""
    cap = duckdb.connect(capture_db, read_only=True)
    try:
        uni, chosen, coverage = entry_selection(cap, prefix + "entry", expiry, entry_date)
        ban_body = Path(ban_file).read_bytes() if ban_file else _artifact(cap, "fo_secban", expiry, entry_date)
        ca_body = Path(ca_file).read_bytes() if ca_file else _artifact(cap, "ca_forward", expiry, entry_date)
        prev = sessions_before(entry_date, 1)
        hist = history_pass(futures_db, entry_date, prev)
        banned, ban_src = ban_set(ban_body, entry_date)
        fut = chosen.fut_ltp.to_dict() if len(chosen) else {}
        ca_out, ca_src = ca_excluded(ca_body, entry_date, exit_date, fut)

        rows, excl = [], {"U2": 0, "U3": 0, "U4": 0, "U5": 0}
        for u, lot in uni.itertuples(index=False):
            status = ("U2" if u not in chosen.index else "U3" if u not in hist
                      else "U4" if u in banned else "U5" if u in ca_out else "eligible")
            if status != "eligible":
                excl[status] += 1
            c = chosen.loc[u].to_dict() if u in chosen.index else {}
            rows.append(dict(expiry=expiry, role=prefix + "live", underlying=u, lot_size=int(lot),
                             status=status, **{k: c.get(k) for k in (
                                 "entry_pass", "strike", "ce_key", "pe_key", "fut_ltp",
                                 "ce_bid", "pe_bid")}))
        names = pd.DataFrame(rows, columns=[c for c in NAME_COLS if c not in (
            "ce_ask", "pe_ask", "ce_exit_src", "pe_exit_src", "fees", "gross", "net")])
        elig = names[names.status == "eligible"].copy()

        void_reason = None
        if not coverage or max(coverage.values()) < MIN_FUT_COVERAGE:
            void_reason = f"entry capture futures coverage {max(coverage.values(), default=0):.0%}"
        elif elig.empty:
            void_reason = "no eligible name"
        if entry_only or void_reason:
            return names, dict(void=void_reason is not None, void_reason=void_reason,
                               ban_source=ban_src, ca_source=ca_src, excl=excl, coverage=coverage)

        px = exit_prices(cap, prefix + "exit", expiry, exit_date,
                         list(elig.ce_key) + list(elig.pe_key), options_bhav_db)
    finally:
        cap.close()

    elig["ce_ask"], elig["ce_exit_src"] = zip(*elig.ce_key.map(px))
    elig["pe_ask"], elig["pe_exit_src"] = zip(*elig.pe_key.map(px))
    elig["fees"] = [name_fees(r.ce_bid, r.pe_bid, r.ce_ask, r.pe_ask, r.lot_size, entry_date, exit_date)
                    for r in elig.itertuples()]
    prem = elig.ce_bid + elig.pe_bid
    elig["gross"] = (prem - elig.ce_ask - elig.pe_ask) / prem
    elig["net"] = (prem - elig.ce_ask - elig.pe_ask - elig.fees / elig.lot_size) / prem
    names = pd.concat([names[names.status != "eligible"], elig], ignore_index=True)
    names = names.reindex(columns=list(NAME_COLS))
    fallback = int((elig.ce_exit_src == "fallback").sum() + (elig.pe_exit_src == "fallback").sum())
    return names, dict(void=False, void_reason=None, ban_source=ban_src, ca_source=ca_src,
                       excl=excl, coverage=coverage, entry_date=entry_date, exit_date=exit_date,
                       cycle_gross=float(elig.gross.mean()), cycle_net=float(elig.net.mean()),
                       fallback_legs=fallback)


def write_cycle(cycles_db: str, expiry: date, role: str, names: pd.DataFrame, info: dict,
                entry_date: date, exit_date: date):
    Path(cycles_db).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(cycles_db)
    try:
        con.execute(SCHEMA)
        con.execute("delete from cycle_names where expiry = ? and role = ?", [expiry, role])
        con.execute("delete from cycles where expiry = ? and role = ?", [expiry, role])
        frame = names.reindex(columns=list(NAME_COLS))  # noqa: F841 - read by DuckDB below
        con.execute(f"insert into cycle_names ({','.join(NAME_COLS)}) select * from frame")
        e = info["excl"]
        con.execute("insert into cycles values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [expiry, role, entry_date, exit_date, datetime.now(), info["void"],
                     info["void_reason"], len(names), int((names.status == "eligible").sum()),
                     info.get("cycle_gross"), info.get("cycle_net"), info.get("fallback_legs"),
                     info["ban_source"], info["ca_source"], e["U2"], e["U3"], e["U4"], e["U5"]])
    finally:
        con.close()


# ---------------------------------------------------------------- window test

def summary(nets: list[float]) -> dict:
    """Section 1 test and section 9 falsification over counted cycle net returns, in expiry order."""
    x = np.asarray(nets[:N_WINDOW], dtype=float)
    out = {"n": len(x)}
    falsified = None
    for k in range(FALSIFY_FROM, len(x) + 1):
        xs = x[:k]
        sd = xs.std(ddof=1)
        t_neg = -xs.mean() / sd * np.sqrt(k) if sd > 0 else 0.0
        if t_neg >= F1_T:
            falsified = f"F1 at cycle {k} (t for mean<0 = {t_neg:.2f})"
            break
        if xs.sum() <= F2_CUM:
            falsified = f"F2 at cycle {k} (cumulative {xs.sum():+.1%} of premium)"
            break
    out["falsified"] = falsified
    if len(x) >= 2:
        sd = x.std(ddof=1)
        out.update(mean=x.mean(), sd=sd, t=x.mean() / sd * np.sqrt(len(x)) if sd > 0 else np.nan,
                   sharpe_ann=x.mean() / sd * np.sqrt(12) if sd > 0 else np.nan,
                   skew=pd.Series(x).skew() if len(x) >= 3 else np.nan,
                   cvar10=np.sort(x)[:max(1, len(x) // 10)].mean(), worst3=list(np.sort(x)[:3]),
                   cumulative=x.sum())
    if falsified:
        out["verdict"] = "FALSIFIED"
    elif len(x) < N_WINDOW:
        out["verdict"] = f"IN PROGRESS ({len(x)}/{N_WINDOW} cycles)"
    else:
        out["verdict"] = "CONFIRMED" if out["t"] > T_CRIT else "NOT CONFIRMED"
    return out


def counted_nets(cycles_db: str, role: str = "live") -> list[float]:
    con = duckdb.connect(cycles_db, read_only=True)
    try:
        return [v for (v,) in con.execute(
            "select cycle_net from cycles where role = ? and not void order by expiry", [role]).fetchall()]
    finally:
        con.close()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--expiry")
    ap.add_argument("--capture-db", default=str(DEFAULT_DB))
    ap.add_argument("--cycles-db", default=str(CYCLES_DB))
    ap.add_argument("--futures", default=str(FUTURES_DB))
    ap.add_argument("--options-bhav", default=str(OPTIONS_BHAV_DB))
    ap.add_argument("--dry", action="store_true", help="score dry-entry/dry-exit captures")
    ap.add_argument("--entry-date")
    ap.add_argument("--exit-date")
    ap.add_argument("--entry-only", action="store_true", help="eligibility report; writes nothing")
    ap.add_argument("--ban-file", help="D6 fallback: NSE dated archive ban file for the entry date")
    ap.add_argument("--ca-file", help="D5 fallback: CA list fetched before the T-9 open")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args(argv)
    role = ("dry-" if a.dry else "") + "live"

    if a.summary:
        s = summary(counted_nets(a.cycles_db, role))
        for k, v in s.items():
            print(f"{k:12s} {v}")
        return 0
    if (a.entry_date or a.exit_date) and not a.dry:
        print("--entry-date/--exit-date are dry-only: live cycles use the calendar T-10/T-1")
        return 2
    expiry = date.fromisoformat(a.expiry)
    ed = date.fromisoformat(a.entry_date) if a.entry_date else None
    xd = date.fromisoformat(a.exit_date) if a.exit_date else None
    names, info = score_cycle(expiry, capture_db=a.capture_db, futures_db=a.futures,
                              options_bhav_db=a.options_bhav, dry=a.dry, entry_date=ed,
                              exit_date=xd, entry_only=a.entry_only, ban_file=a.ban_file,
                              ca_file=a.ca_file)
    cov = ", ".join(f"{k} {v:.0%}" for k, v in info["coverage"].items())
    print(f"{role} {expiry}: universe {len(names)}, eligible {(names.status == 'eligible').sum()}, "
          f"excluded {info['excl']}; entry futures coverage {cov}")
    print(f"  ban: {info['ban_source']}; CA: {info['ca_source']}")
    for st in ("U3", "U4", "U5"):
        hit = sorted(names[names.status == st].underlying)
        if hit:
            print(f"  {st}: {', '.join(hit)}")
    if info["void"]:
        print(f"  VOID: {info['void_reason']}")
    if a.entry_only or info["void"]:
        if info["void"] and not a.entry_only:
            write_cycle(a.cycles_db, expiry, role, names, info,
                        ed or sessions_before(expiry, ENTRY_OFFSET), xd or sessions_before(expiry, EXIT_OFFSET))
        return 0
    write_cycle(a.cycles_db, expiry, role, names, info, info["entry_date"], info["exit_date"])
    print(f"  cycle gross {info['cycle_gross']:+.2%}  net {info['cycle_net']:+.2%}  "
          f"fallback legs {info['fallback_legs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
