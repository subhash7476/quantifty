"""TS Basis Daily — options signal-strength analysis over the past month.

For every formation date in the last ~30 calendar days, loads the TS Basis
Daily signal book from carry_facts, ranks by z_carry_neut, and takes the
top-5 longs (Q5, highest z) and top-5 shorts (Q1, lowest z) — the same
top-5-per-side selection `ts_basis_daily_options.py` reports.

Each name is resolved to the tradeable option contract exactly as the
selection logic does (LONG -> CE, SHORT -> PE; nearest monthly expiry with
DTE >= min_dte; ATM strike snapped for liquidity), but priced as-of the
formation date (no lookahead).

Entry/exit prices come **directly from Upstox daily candles** — the standard
historical-candle endpoint for still-active contracts and the
expired-instruments endpoint for contracts that have since expired. Bhavcopy
settle is used ONLY to resolve the contract (strike/expiry), never to price.

Signal strength is measured three ways:
  1. Underlying direction hit — did the futures forward move the way the
     signal predicted (LONG -> up, SHORT -> down)?
  2. Option premium return — what you'd actually earn buying the CE/PE.
  3. z-rank monotonicity — does rank 1 beat rank 5?

Usage:
  python scripts/ts_basis_daily_options_signal_strength.py [--days 30]
"""
from __future__ import annotations

import statistics as st
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.auth.credentials import credentials  # noqa: E402

FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"
OPT_DB = ROOT / "data" / "market_data" / "stock_options_bhavcopy.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
INST_DB = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"
REPORT = ROOT / "docs" / "reports" / "TS_BASIS_DAILY_OPTIONS_SIGNAL_STRENGTH.md"

MIN_DTE = 7
MIN_OI = 100
HIST_URL = "https://api.upstox.com/v2/historical-candle/{key}/day/{to_date}/{from_date}"
EXPIRED_URL = ("https://api.upstox.com/v2/expired-instruments/historical-candle/"
               "{key}|{expiry_dmy}/day/{to_date}/{from_date}")

_token = credentials.get("access_token")
_headers = {"Authorization": f"Bearer {_token}", "Accept": "application/json"}
_candle_cache: dict[str, dict[str, list]] = {}


def _fetch_candles(instrument_key: str, expiry: date, to_date: date,
                   from_date: date) -> dict[str, list]:
    """Daily candles keyed by date. Uses expired endpoint when contract expired."""
    if not _token:
        raise RuntimeError("No Upstox access token")
    cache_key = f"{instrument_key}@{expiry.isoformat()}"
    if cache_key in _candle_cache:
        return _candle_cache[cache_key]
    to_d, from_d = to_date.isoformat(), from_date.isoformat()
    url = HIST_URL.format(key=instrument_key, to_date=to_d, from_date=from_d)
    resp = requests.get(url, headers=_headers, timeout=15)
    if resp.status_code == 400:
        url = EXPIRED_URL.format(key=instrument_key,
                                 expiry_dmy=expiry.strftime("%d-%m-%Y"),
                                 to_date=to_d, from_date=from_d)
        resp = requests.get(url, headers=_headers, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Upstox {resp.status_code} for {instrument_key}: {resp.text[:200]}")
    data = resp.json().get("data", {}).get("candles", [])
    out: dict[str, list] = {}
    for c in data:
        if len(c) >= 5:
            out[c[0][:10]] = [float(c[1]), float(c[2]), float(c[3]), float(c[4])]
    _candle_cache[cache_key] = out
    time.sleep(0.05)
    return out


def _pick_expiry_asof(o, ticker: str, d: date, min_dte: int) -> date | None:
    rows = o.execute(
        "SELECT DISTINCT expiry_dt FROM stock_options_bhavcopy "
        "WHERE underlying=? AND expiry_dt >= ? ORDER BY expiry_dt",
        [ticker, d],
    ).fetchall()
    for (exp,) in rows:
        if (exp - d).days >= min_dte:
            return exp
    return rows[-1][0] if rows else None


def _forward_asof(f, ticker: str, expiry: date, d: date) -> float | None:
    row = f.execute(
        "SELECT close FROM futures_bhavcopy WHERE underlying=? AND expiry_dt=? "
        "AND inst_type='FUTSTK' AND trade_date=? ORDER BY trade_date DESC LIMIT 1",
        [ticker, expiry, d],
    ).fetchone()
    return row[0] if row else None


def _forward_later(f, ticker: str, expiry: date, d: date) -> float | None:
    row = f.execute(
        "SELECT close FROM futures_bhavcopy WHERE underlying=? AND expiry_dt=? "
        "AND inst_type='FUTSTK' AND trade_date=? ORDER BY trade_date DESC LIMIT 1",
        [ticker, expiry, d],
    ).fetchone()
    return row[0] if row else None


def _chain_asof(o, ticker: str, expiry: date, opt_type: str, d: date) -> list:
    return o.execute(
        "SELECT strike, settle, open_int FROM stock_options_bhavcopy "
        "WHERE underlying=? AND expiry_dt=? AND option_type=? AND trade_date=? "
        "ORDER BY strike",
        [ticker, expiry, opt_type, d],
    ).fetchall()


def _pick_strike(chain: list, forward: float) -> tuple | None:
    if not chain:
        return None
    nearest = min(chain, key=lambda r: abs(r[0] - forward))
    chosen = nearest
    if nearest[2] is None or nearest[2] < MIN_OI:
        liquid = [r for r in chain if r[2] is not None and r[2] >= MIN_OI]
        if liquid:
            chosen = min(liquid, key=lambda r: abs(r[0] - forward))
    return chosen


def _name_for(inst, ticker: str) -> str | None:
    row = inst.execute(
        "SELECT name FROM instruments WHERE instrument_type='EQ' AND tradingsymbol=? LIMIT 1",
        [ticker],
    ).fetchone()
    return row[0] if row else None


def _instrument_key(inst, name: str, opt_type: str, strike: float, expiry: date) -> str | None:
    row = inst.execute(
        "SELECT instrument_key FROM instruments WHERE name=? AND instrument_type=? "
        "AND strike=? AND expiry=? LIMIT 1",
        [name, opt_type, strike, expiry.isoformat()],
    ).fetchone()
    return row[0] if row else None


def _lot_size(inst, name: str, opt_type: str, strike: float, expiry: date) -> int | None:
    row = inst.execute(
        "SELECT lot_size FROM instruments WHERE name=? AND instrument_type=? "
        "AND strike=? AND expiry=? LIMIT 1",
        [name, opt_type, strike, expiry.isoformat()],
    ).fetchone()
    return row[0] if row else None


def _calendar(f):
    rows = f.execute("SELECT DISTINCT trade_date FROM futures_bhavcopy ORDER BY trade_date").fetchall()
    return [r[0] for r in rows]


def _next_td(cal: list, cal_set: set, d: date, n: int) -> date | None:
    if d in cal_set:
        j = cal.index(d) + n
    else:
        j = next((i for i, c in enumerate(cal) if c > d), None)
        if j is None:
            return None
        j += n
    return cal[j] if j < len(cal) else None


def _stats(vals):
    if not vals:
        return "—"
    return (f"{st.mean(vals):+.1f}%  (med {st.median(vals):+.1f}%, "
            f"hit {sum(1 for v in vals if v > 0)/len(vals):.0%})")


def main():
    days = 30
    for i, a in enumerate(sys.argv):
        if a == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])

    o = duckdb.connect(str(OPT_DB), read_only=True)
    f = duckdb.connect(str(FUT_DB), read_only=True)
    inst = duckdb.connect(str(INST_DB), read_only=True)
    cal = _calendar(f)
    cal_set = set(cal)
    today = cal[-1]
    lo = today - timedelta(days=days)

    fc = duckdb.connect(str(FACTS_DB), read_only=True)
    formations = [r[0] for r in fc.execute(
        "SELECT DISTINCT formation_date FROM carry_facts "
        "WHERE formation_date >= ? ORDER BY formation_date", [lo]).fetchall()]
    fc.close()

    resolved = []
    for D in formations:
        con = duckdb.connect(str(FACTS_DB), read_only=True)
        facts = con.execute(
            "SELECT underlying, quintile, z_carry_neut FROM carry_facts "
            "WHERE formation_date=? AND eligible", [D]).fetchall()
        con.close()
        longs = sorted([(u, z) for u, q, z in facts if q == 5], key=lambda r: -r[1])[:5]
        shorts = sorted([(u, z) for u, q, z in facts if q == 1], key=lambda r: r[1])[:5]
        picks = [("LONG", u, z) for u, z in longs] + [("SHORT", u, z) for u, z in shorts]

        for side, ticker, z in picks:
            opt_type = "CE" if side == "LONG" else "PE"
            expiry = _pick_expiry_asof(o, ticker, D, MIN_DTE)
            row = dict(formation=D.isoformat(), ticker=ticker, side=side, z=z, opt_type=opt_type,
                       expiry=expiry.isoformat() if expiry else None)
            if expiry is None:
                row["reason"] = "no_expiry"
                resolved.append(row)
                continue
            forward = _forward_asof(f, ticker, expiry, D)
            row["forward"] = forward
            chain = _chain_asof(o, ticker, expiry, opt_type, D)
            if not chain:
                row["reason"] = "no_chain"
                resolved.append(row)
                continue
            strike_row = _pick_strike(chain, forward)
            if strike_row is None:
                row["reason"] = "no_tradeable_strike"
                resolved.append(row)
                continue
            strike, settle, oi = strike_row
            row.update(strike=strike, settle=settle, oi=oi)
            name = _name_for(inst, ticker)
            if name is None:
                row["reason"] = "no_instrument"
                resolved.append(row)
                continue
            row["instrument_key"] = _instrument_key(inst, name, opt_type, strike, expiry)
            row["lot_size"] = _lot_size(inst, name, opt_type, strike, expiry)
            if row["instrument_key"]:
                _fetch_candles(row["instrument_key"], expiry, today, D - timedelta(days=5))
            resolved.append(row)

    results = []
    for r in resolved:
        if not r.get("instrument_key") or not r.get("strike") or r.get("reason"):
            results.append(r)
            continue
        D = date.fromisoformat(r["formation"])
        expiry = date.fromisoformat(r["expiry"])
        candles = _candle_cache.get(f"{r['instrument_key']}@{r['expiry']}", {})

        def close_on(d: date | None):
            if d is None:
                return None
            for cand in (d.isoformat(), (d - timedelta(days=1)).isoformat()):
                c = candles.get(cand)
                if c:
                    return c[3]
            return None

        def open_on(d: date | None):
            if d is None:
                return None
            c = candles.get(d.isoformat())
            return c[0] if c else None

        entry_next = _next_td(cal, cal_set, D, 1)
        r["entry_close"] = close_on(D)
        r["entry_open_next"] = open_on(entry_next)
        r["exit_close_1"] = close_on(_next_td(cal, cal_set, D, 1))
        r["exit_close_2"] = close_on(_next_td(cal, cal_set, D, 2))
        r["exit_close_5"] = close_on(_next_td(cal, cal_set, D, 5))
        fwd0 = _forward_asof(f, r["ticker"], expiry, D)
        r["fwd_1"] = _forward_later(f, r["ticker"], expiry, _next_td(cal, cal_set, D, 1))
        r["fwd_5"] = _forward_later(f, r["ticker"], expiry, _next_td(cal, cal_set, D, 5))
        r["fwd0"] = fwd0
        results.append(r)

    _emit_report(results, today, days)
    return 0


def _emit_report(results: list[dict], today: date, days: int):
    usable = [r for r in results if r.get("strike")]
    no_key = [r for r in results if r.get("strike") and not r.get("instrument_key")]
    no_exit = [r for r in usable if r.get("entry_open_next") is None]

    def grp(side=None):
        out = []
        for r in usable:
            if side and r["side"] != side:
                continue
            if r.get("entry_open_next") and r.get("exit_close_1"):
                out.append(r)
        return out

    def ret(g, entry_k, exit_k):
        return [r[exit_k] / r[entry_k] - 1.0 for r in g
                if r.get(entry_k) and r.get(exit_k)]

    def fwd_hit(g, key):
        vals = []
        for r in g:
            f0, fx = r.get("fwd0"), r.get(key)
            if not f0 or not fx:
                continue
            mv = fx / f0 - 1.0
            good = (mv > 0) if r["side"] == "LONG" else (mv < 0)
            vals.append(good)
        return vals

    all_g, long_g, short_g = grp(), grp("LONG"), grp("SHORT")

    lines = []
    lines.append(f"# TS Basis Daily — Options Signal-Strength Analysis (past {days}d)")
    lines.append("")
    lines.append(f"*Generated {today.isoformat()} — prices fetched directly from Upstox daily "
                 "candles (historical-candle for active contracts, expired-instruments for "
                 "expired). Bhavcopy used only for contract resolution, never pricing.*")
    lines.append("")
    lines.append(f"- Formations analysed: {len(set(r['formation'] for r in usable))}")
    lines.append(f"- Contracts resolved: {len(usable)}  (no instrument key: {len(no_key)}, "
                 f"no next-day exit yet: {len(no_exit)})")
    lines.append(f"- Evaluated (entry+exit present): {len(all_g)} "
                 f"= {len(long_g)} LONG / {len(short_g)} SHORT")
    lines.append("")
    lines.append("### Reading this table")
    lines.append("")
    lines.append("- **Option premium return** is what a trader actually earns buying the recommended "
                 "ATM CE/PE — it includes theta/gamma, so a *correct direction call* still loses if "
                 "the move is small or late.")
    lines.append("- **Underlying direction hit** isolates signal quality from option mechanics: did "
                 "the futures forward move the way the z-score predicted (LONG -> up, SHORT -> down)?")
    lines.append("- z **rank 1** = strongest signal (highest z for LONG, most negative z for SHORT).")
    lines.append("")
    lines.append("## Option premium returns")
    lines.append("")
    lines.append("| Cohort | Entry | H=1d | H=2d | H=5d |")
    lines.append("|---|---|---|---|---|")
    for label, g in [("All", all_g), ("LONG (CE)", long_g), ("SHORT (PE)", short_g)]:
        v1o = [100 * x for x in ret(g, "entry_open_next", "exit_close_1")]
        v2o = [100 * x for x in ret(g, "entry_open_next", "exit_close_2")]
        v5o = [100 * x for x in ret(g, "entry_open_next", "exit_close_5")]
        v1c = [100 * x for x in ret(g, "entry_close", "exit_close_1")]
        lines.append(f"| {label} | next-open | {_stats(v1o)} | {_stats(v2o)} | {_stats(v5o)} |")
        lines.append(f"| | formation-close | {_stats(v1c)} | — | — |")
    lines.append("")
    lines.append("## Underlying direction hit (futures forward, predicted move)")
    lines.append("")
    lines.append("| Cohort | Fwd hit H=1d | Fwd hit H=5d |")
    lines.append("|---|---|---|")
    for label, g in [("All", all_g), ("LONG (CE)", long_g), ("SHORT (PE)", short_g)]:
        h1 = fwd_hit(g, "fwd_1")
        h5 = fwd_hit(g, "fwd_5")
        s1 = f"{sum(h1)/len(h1):.0%}" if h1 else "—"
        s5 = f"{sum(h5)/len(h5):.0%}" if h5 else "—"
        lines.append(f"| {label} | {s1} ({len(h1)}) | {s5} ({len(h5)}) |")
    lines.append("")
    lines.append("## z-rank monotonicity (H=1d premium return, entry next-open)")
    lines.append("")
    lines.append("| Rank | LONG mean 1d | LONG hit 1d | SHORT mean 1d | SHORT hit 1d |")
    lines.append("|---|---|---|---|---|")
    # group by per-formation rank index (rank 0 = highest-z long / lowest-z short)
    by_form = {}
    for r in all_g:
        by_form.setdefault(r["formation"], []).append(r)
    l_rank_ret = {i: [] for i in range(5)}
    l_rank_hit = {i: [] for i in range(5)}
    s_rank_ret = {i: [] for i in range(5)}
    s_rank_hit = {i: [] for i in range(5)}
    for frm, rows in by_form.items():
        longs_f = sorted([r for r in rows if r["side"] == "LONG"], key=lambda r: -r["z"])
        shorts_f = sorted([r for r in rows if r["side"] == "SHORT"], key=lambda r: r["z"])
        for i, r in enumerate(longs_f):
            if r.get("entry_open_next") and r.get("exit_close_1"):
                ret1 = r["exit_close_1"] / r["entry_open_next"] - 1.0
                l_rank_ret[i].append(ret1)
                l_rank_hit[i].append(ret1 > 0)
        for i, r in enumerate(shorts_f):
            if r.get("entry_open_next") and r.get("exit_close_1"):
                ret1 = r["exit_close_1"] / r["entry_open_next"] - 1.0
                s_rank_ret[i].append(ret1)
                s_rank_hit[i].append(ret1 > 0)
    for i in range(5):
        lr = l_rank_ret[i]; lh = l_rank_hit[i]
        sr = s_rank_ret[i]; sh = s_rank_hit[i]
        lr_s = f"{st.mean(lr)*100:+.1f}%" if lr else "—"
        lh_s = f"{sum(lh)/len(lh):.0%}" if lh else "—"
        sr_s = f"{st.mean(sr)*100:+.1f}%" if sr else "—"
        sh_s = f"{sum(sh)/len(sh):.0%}" if sh else "—"
        lines.append(f"| {i+1} | {lr_s} | {lh_s} | {sr_s} | {sh_s} |")
    lines.append("")
    lines.append("## Per-formation detail (H=1d)")
    lines.append("")
    lines.append("| Form | Ticker | Side | z | Exp | Strike | Entry(open) | Exit+1d | Ret 1d | Fwd mv 1d |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    detail = sorted(all_g, key=lambda x: (x["formation"], x["side"], -x["z"]))
    for r in detail:
        entry, exit1 = r.get("entry_open_next"), r.get("exit_close_1")
        ret1 = f"{(exit1/entry-1)*100:+.1f}%" if (entry and exit1) else "—"
        f0, fx = r.get("fwd0"), r.get("fwd_1")
        fw = f"{(fx/f0-1)*100:+.1f}%" if (f0 and fx) else "—"
        lines.append(f"| {r['formation']} | {r['ticker']} | {r['side']} | {r['z']:.2f} | "
                     f"{r['expiry'][5:]} | {r['strike']:.0f} | "
                     f"{entry or '—'} | {exit1 or '—'} | {ret1} | {fw} |")
    lines.append("")
    text = "\n".join(lines)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nWrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
