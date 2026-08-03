"""TS Basis Daily — equity signal-strength analysis over the past month.

Mirror of ts_basis_daily_options_signal_strength.py, but prices the signal on
the UNDERLYING EQUITY instead of option premiums.

For every formation date in the last ~30 calendar days, loads the TS Basis
Daily signal book from carry_facts, ranks by z_carry_neut, and takes the
top-5 longs (Q5, highest z) and top-5 shorts (Q1, lowest z) — the same
top-5-per-side selection `ts_basis_daily_options.py` reports.

Each name is resolved to its NSE_EQ equity instrument key and priced from
Upstox daily candles (no bhavcopy in the price path).

Signal strength is measured the same way as the options analysis:
  1. Equity forward return — what you'd earn holding the stock (long/short).
  2. Direction hit — did the equity move the way the z-score predicted
     (LONG -> up, SHORT -> down)?
  3. z-rank monotonicity — does rank 1 beat rank 5?

Usage:
  python scripts/ts_basis_daily_equity_signal_strength.py [--days 30]
"""
from __future__ import annotations

import statistics as st
import sys
import time
from datetime import date, timedelta
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import duckdb
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.auth.credentials import credentials  # noqa: E402

FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
INST_DB = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"
REPORT = ROOT / "docs" / "reports" / "TS_BASIS_DAILY_EQUITY_SIGNAL_STRENGTH.md"

HIST_URL = "https://api.upstox.com/v2/historical-candle/{key}/day/{to_date}/{from_date}"

_token = credentials.get("access_token")
_headers = {"Authorization": f"Bearer {_token}", "Accept": "application/json"}
_candle_cache: dict[str, dict[str, list]] = {}


def _fetch_candles(instrument_key: str, to_date: date, from_date: date) -> dict[str, list]:
    if not _token:
        raise RuntimeError("No Upstox access token")
    cache_key = instrument_key
    if cache_key in _candle_cache:
        return _candle_cache[cache_key]
    url = HIST_URL.format(key=instrument_key, to_date=to_date.isoformat(),
                          from_date=from_date.isoformat())
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


def _equity_key(inst, ticker: str) -> str | None:
    row = inst.execute(
        "SELECT instrument_key FROM instruments WHERE tradingsymbol=? "
        "AND instrument_type='EQ' ORDER BY snapshot_date DESC LIMIT 1",
        [ticker],
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
    return (f"{st.mean(vals):+.2f}%  (med {st.median(vals):+.2f}%, "
            f"hit {sum(1 for v in vals if v > 0)/len(vals):.0%})")


def main():
    days = 30
    for i, a in enumerate(sys.argv):
        if a == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])

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

    rows_out = []
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
            key = _equity_key(inst, ticker)
            row = dict(formation=D.isoformat(), ticker=ticker, side=side, z=z,
                       instrument_key=key)
            if key is None:
                row["reason"] = "no_instrument"
                rows_out.append(row)
                continue
            _fetch_candles(key, today, D - timedelta(days=5))
            rows_out.append(row)

    results = []
    for r in rows_out:
        if not r.get("instrument_key") or r.get("reason"):
            results.append(r)
            continue
        D = date.fromisoformat(r["formation"])
        candles = _candle_cache.get(r["instrument_key"], {})

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
        results.append(r)

    _emit_report(results, today, days)
    return 0


def _emit_report(results: list[dict], today: date, days: int):
    usable = [r for r in results if r.get("instrument_key")]
    no_key = [r for r in results if not r.get("instrument_key")]
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

    # long/short-adjusted: LONG return = +move, SHORT return = -move
    def adj_ret(g, entry_k, exit_k):
        out = []
        for r in g:
            if not (r.get(entry_k) and r.get(exit_k)):
                continue
            mv = r[exit_k] / r[entry_k] - 1.0
            out.append(mv if r["side"] == "LONG" else -mv)
        return out

    def hit(g, entry_k, exit_k):
        out = []
        for r in g:
            if not (r.get(entry_k) and r.get(exit_k)):
                continue
            mv = r[exit_k] / r[entry_k] - 1.0
            good = (mv > 0) if r["side"] == "LONG" else (mv < 0)
            out.append(good)
        return out

    all_g, long_g, short_g = grp(), grp("LONG"), grp("SHORT")

    lines = []
    lines.append(f"# TS Basis Daily — Equity Signal-Strength Analysis (past {days}d)")
    lines.append("")
    lines.append(f"*Generated {today.isoformat()} — underlying equity priced directly from Upstox "
                 "daily candles (NSE_EQ). Bhavcopy not used in the price path.*")
    lines.append("")
    lines.append(f"- Formations analysed: {len(set(r['formation'] for r in usable))}")
    lines.append(f"- Names resolved: {len(usable)}  (no instrument key: {len(no_key)}, "
                 f"no next-day exit yet: {len(no_exit)})")
    lines.append(f"- Evaluated (entry+exit present): {len(all_g)} "
                 f"= {len(long_g)} LONG / {len(short_g)} SHORT")
    lines.append("")
    lines.append("### Reading this table")
    lines.append("")
    lines.append("- **Equity return** is the raw spot move; long/short-adjusted is +move for LONG, "
                 "−move for SHORT (a positive adjusted return means the signal was right).")
    lines.append("- **Direction hit** is the fraction of names whose spot moved the predicted way "
                 "(LONG -> up, SHORT -> down).")
    lines.append("- z **rank 1** = strongest signal (highest z for LONG, most negative z for SHORT).")
    lines.append("")
    lines.append("## Equity returns (spot)")
    lines.append("")
    lines.append("| Cohort | Entry | H=1d | H=2d | H=5d |")
    lines.append("|---|---|---|---|---|")
    for label, g in [("All", all_g), ("LONG", long_g), ("SHORT", short_g)]:
        v1o = [100 * x for x in ret(g, "entry_open_next", "exit_close_1")]
        v2o = [100 * x for x in ret(g, "entry_open_next", "exit_close_2")]
        v5o = [100 * x for x in ret(g, "entry_open_next", "exit_close_5")]
        v1c = [100 * x for x in ret(g, "entry_close", "exit_close_1")]
        lines.append(f"| {label} | next-open | {_stats(v1o)} | {_stats(v2o)} | {_stats(v5o)} |")
        lines.append(f"| | formation-close | {_stats(v1c)} | — | — |")
    lines.append("")
    lines.append("## Long/short-adjusted returns (predicted-move sign)")
    lines.append("")
    lines.append("| Cohort | Entry | H=1d | H=2d | H=5d |")
    lines.append("|---|---|---|---|---|")
    for label, g in [("All", all_g), ("LONG", long_g), ("SHORT", short_g)]:
        v1o = [100 * x for x in adj_ret(g, "entry_open_next", "exit_close_1")]
        v2o = [100 * x for x in adj_ret(g, "entry_open_next", "exit_close_2")]
        v5o = [100 * x for x in adj_ret(g, "entry_open_next", "exit_close_5")]
        v1c = [100 * x for x in adj_ret(g, "entry_close", "exit_close_1")]
        lines.append(f"| {label} | next-open | {_stats(v1o)} | {_stats(v2o)} | {_stats(v5o)} |")
        lines.append(f"| | formation-close | {_stats(v1c)} | — | — |")
    lines.append("")
    lines.append("## Direction hit (predicted move)")
    lines.append("")
    lines.append("| Cohort | Hit H=1d | Hit H=2d | Hit H=5d |")
    lines.append("|---|---|---|---|")
    for label, g in [("All", all_g), ("LONG", long_g), ("SHORT", short_g)]:
        h1 = hit(g, "entry_open_next", "exit_close_1")
        h2 = hit(g, "entry_open_next", "exit_close_2")
        h5 = hit(g, "entry_open_next", "exit_close_5")
        s = lambda h: f"{sum(h)/len(h):.0%} ({len(h)})" if h else "—"
        lines.append(f"| {label} | {s(h1)} | {s(h2)} | {s(h5)} |")
    lines.append("")
    lines.append("## z-rank monotonicity (H=1d adjusted return, entry next-open)")
    lines.append("")
    lines.append("| Rank | LONG mean | LONG hit | SHORT mean | SHORT hit |")
    lines.append("|---|---|---|---|---|")
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
                mv = r["exit_close_1"] / r["entry_open_next"] - 1.0
                l_rank_ret[i].append(mv)
                l_rank_hit[i].append(mv > 0)
        for i, r in enumerate(shorts_f):
            if r.get("entry_open_next") and r.get("exit_close_1"):
                mv = r["exit_close_1"] / r["entry_open_next"] - 1.0
                s_rank_ret[i].append(-mv)
                s_rank_hit[i].append(mv < 0)
    for i in range(5):
        lr = l_rank_ret[i]; lh = l_rank_hit[i]
        sr = s_rank_ret[i]; sh = s_rank_hit[i]
        lr_s = f"{st.mean(lr)*100:+.2f}%" if lr else "—"
        lh_s = f"{sum(lh)/len(lh):.0%}" if lh else "—"
        sr_s = f"{st.mean(sr)*100:+.2f}%" if sr else "—"
        sh_s = f"{sum(sh)/len(sh):.0%}" if sh else "—"
        lines.append(f"| {i+1} | {lr_s} | {lh_s} | {sr_s} | {sh_s} |")
    lines.append("")
    lines.append("## Per-formation detail (H=1d, next-open entry)")
    lines.append("")
    lines.append("| Form | Ticker | Side | z | Entry(open) | Exit+1d | Spot mv 1d | Adj ret 1d |")
    lines.append("|---|---|---|---|---|---|---|---|")
    detail = sorted(all_g, key=lambda x: (x["formation"], x["side"], -x["z"]))
    for r in detail:
        entry, exit1 = r.get("entry_open_next"), r.get("exit_close_1")
        if entry and exit1:
            mv = exit1 / entry - 1.0
            adj = mv if r["side"] == "LONG" else -mv
            mv_s = f"{mv*100:+.2f}%"
            adj_s = f"{adj*100:+.2f}%"
        else:
            mv_s = adj_s = "—"
        lines.append(f"| {r['formation']} | {r['ticker']} | {r['side']} | {r['z']:.2f} | "
                     f"{entry or '—'} | {exit1 or '—'} | {mv_s} | {adj_s} |")
    lines.append("")
    text = "\n".join(lines)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nWrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
