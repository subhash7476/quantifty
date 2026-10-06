"""GEX-XS-5D precondition P1: point-in-time NSE board-meeting (results) calendar.

Fetches the NSE corporate board-meetings archive month by month (the API filters on the
meeting date), stores every raw response, parses rows with their known time (the later of
the filing timestamp and the dissemination time), and certifies the calendar against the
pre-registration's P1 checks (a)-(e). Reads calendar data and structural F&O name lists only:
no option prices, no equity prices, no outcomes.

Spec: docs/reports/GEX_XS_5D_PRE_REGISTRATION.md §7, §11.

Usage:
    python -m scripts.gex_xs_5d.ingest_board_meetings --end 2026-10-05            # fetch
    python -m scripts.gex_xs_5d.ingest_board_meetings --end 2026-10-05 --certify  # + report
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import date, datetime
from pathlib import Path

import duckdb
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "research" / "gex_xs_5d" / "board_meetings.duckdb"
FUTURES_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQUITY_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "GEX_XS_5D_BOARD_MEETINGS_CERT.md"
API = "https://www.nseindia.com/api/corporate-board-meetings"
PAGE = "https://www.nseindia.com/companies-listing/corporate-filings-board-meetings"
FIRST_MONTH = date(2016, 1, 1)
DATE_FMT = "%d-%b-%Y"
TS_FMT = "%d-%b-%Y %H:%M:%S"
RESULTS_RE = re.compile(r"result", re.IGNORECASE)
ISIN_PREFIX_LEN = 9          # issuer + security type, as CSMP's issuer linkage
PAUSE_S = 1.0

# P1 thresholds (pre-registration §11)
MIN_DISTINCT_RESULTS = 3
MIN_COVERAGE = 0.90
MIN_PRESENCE = 0.60
MIN_KNOWN_BEFORE = 0.99
MIN_MAPPED = 0.98
MAX_REVISION_SHARE = 0.02
RESCHEDULE_DAYS = 21         # descriptive only: close-dated meetings of one company


class FetchError(RuntimeError):
    pass


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _next_month(m: date) -> date:
    return date(m.year + (m.month == 12), m.month % 12 + 1, 1)


def _month_end(m: date) -> date:
    return date.fromordinal(_next_month(m).toordinal() - 1)


def months_to_fetch(first: date, end: date, cached: set, today: date) -> list[date]:
    """Months first..end's month; a cached month is skipped only if it has fully closed."""
    out, m = [], _month_start(first)
    while m <= _month_start(end):
        if m not in cached or _month_end(m) >= today:
            out.append(m)
        m = _next_month(m)
    return out


def _session():
    s = requests.Session()
    retry = Retry(total=4, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": PAGE,
    })
    s.get("https://www.nseindia.com", timeout=20)
    s.get(PAGE, timeout=20)
    return s


def fetch_month(session, month: date) -> list[dict]:
    params = {"index": "equities", "from_date": month.strftime("%d-%m-%Y"),
              "to_date": _month_end(month).strftime("%d-%m-%Y")}
    r = session.get(API, params=params, timeout=60)
    if r.status_code != 200:
        raise FetchError(f"{month:%Y-%m}: HTTP {r.status_code}")
    if "text/html" in r.headers.get("Content-Type", "") or r.content.lstrip().startswith(b"<"):
        raise FetchError(f"{month:%Y-%m}: HTML shell, not JSON")
    body = r.json()
    rows = body if isinstance(body, list) else body.get("data")
    if not isinstance(rows, list):
        raise FetchError(f"{month:%Y-%m}: unexpected payload shape {type(body).__name__}")
    return rows


def _ts(s):
    return datetime.strptime(s.strip(), TS_FMT) if s else None


def parse_row(raw: dict) -> dict:
    bm_ts, sys_ts = _ts(raw.get("bm_timestamp")), _ts(raw.get("sysTime"))
    known = max(t for t in (bm_ts, sys_ts) if t is not None)
    isin = (raw.get("sm_isin") or "").strip()
    purpose, desc = raw.get("bm_purpose") or "", raw.get("bm_desc") or ""
    orig, proposed = raw.get("oriiginalMeetingDate"), raw.get("proposedMeetingDate")
    return {
        "symbol": (raw.get("bm_symbol") or "").strip(),
        "isin": isin,
        "isin_prefix": isin[:ISIN_PREFIX_LEN] if isin.startswith("INE") else None,
        "bm_date": datetime.strptime(raw["bm_date"].strip(), DATE_FMT).date(),
        "purpose": purpose,
        "descr": desc,
        "bm_ts": bm_ts,
        "sys_ts": sys_ts,
        "known_ts": known,
        "orig_date": orig,
        "proposed_date": proposed,
        "has_revision": bool(orig or proposed),
        "is_results": bool(RESULTS_RE.search(purpose) or RESULTS_RE.search(desc)),
    }


_COLS = ["symbol", "isin", "isin_prefix", "bm_date", "purpose", "descr", "bm_ts", "sys_ts",
         "known_ts", "orig_date", "proposed_date", "has_revision", "is_results"]


def ensure_schema(con):
    con.execute("""CREATE TABLE IF NOT EXISTS raw_months (
        month DATE PRIMARY KEY, fetched_at TIMESTAMP, n_rows INTEGER, payload VARCHAR)""")
    con.execute("""CREATE TABLE IF NOT EXISTS board_meetings (
        month DATE, symbol VARCHAR, isin VARCHAR, isin_prefix VARCHAR, bm_date DATE,
        purpose VARCHAR, descr VARCHAR, bm_ts TIMESTAMP, sys_ts TIMESTAMP, known_ts TIMESTAMP,
        orig_date VARCHAR, proposed_date VARCHAR, has_revision BOOLEAN, is_results BOOLEAN)""")


def insert_parsed(con, month: date, parsed: list[dict]):
    con.execute("DELETE FROM board_meetings WHERE month = ?", [month])
    if parsed:
        con.executemany(
            f"INSERT INTO board_meetings VALUES (?, {', '.join('?' * len(_COLS))})",
            [[month] + [p[c] for c in _COLS] for p in parsed])


def store_month(con, month: date, rows: list[dict]):
    parsed = [parse_row(r) for r in rows]
    con.execute("DELETE FROM raw_months WHERE month = ?", [month])
    con.execute("INSERT INTO raw_months VALUES (?, ?, ?, ?)",
                [month, datetime.now(), len(rows), json.dumps(rows)])
    insert_parsed(con, month, parsed)


def ingest(end: date, db: Path = DB, today: date | None = None):
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    ensure_schema(con)
    cached = {r[0] for r in con.execute("SELECT month FROM raw_months").fetchall()}
    months = months_to_fetch(FIRST_MONTH, end, cached, today or date.today())
    print(f"{len(months)} month(s) to fetch ({len(cached)} cached)")
    session = _session()
    for i, m in enumerate(months):
        rows = fetch_month(session, m)
        store_month(con, m, rows)
        print(f"  {m:%Y-%m}: {len(rows):5d} rows")
        if i + 1 < len(months):
            time.sleep(PAUSE_S)
    con.close()


# ---------------------------------------------------------------- certification

def missing_months(con, first: date, end: date) -> list[date]:
    have = {r[0] for r in con.execute("SELECT month FROM raw_months WHERE n_rows > 0").fetchall()}
    out, m = [], _month_start(first)
    while m <= _month_start(end):
        if m not in have:
            out.append(m)
        m = _next_month(m)
    return out


def results_coverage(rows: list[dict], names: dict, year: int) -> dict:
    """names: symbol -> ISIN prefix (or None). Covered = >= 3 distinct results meeting dates."""
    by_prefix, by_symbol = {}, {}
    for r in rows:
        if not r["is_results"] or r["bm_date"].year != year:
            continue
        if r["isin_prefix"]:
            by_prefix.setdefault(r["isin_prefix"], set()).add(r["bm_date"])
        by_symbol.setdefault(r["symbol"], set()).add(r["bm_date"])
    covered = 0
    for sym, prefix in names.items():
        dates = by_prefix.get(prefix, set()) | by_symbol.get(sym, set())
        covered += len(dates) >= MIN_DISTINCT_RESULTS
    n = len(names)
    return {"n_names": n, "n_covered": covered, "share": covered / n if n else 0.0}


def known_before_meeting_share(rows: list[dict]) -> float:
    res = [r for r in rows if r["is_results"]]
    return sum(r["known_ts"].date() <= r["bm_date"] for r in res) / len(res) if res else 0.0


def reschedule_pairs(rows: list[dict]) -> dict:
    """Same company, distinct results meeting dates <= 21 days apart: how many, and how many
    had the later-dated meeting filed later (a reschedule appended as a new row)."""
    first_known = {}
    for r in rows:
        if r["is_results"]:
            k = (r["isin_prefix"] or r["symbol"], r["bm_date"])
            first_known[k] = min(first_known.get(k, r["known_ts"]), r["known_ts"])
    by_co = {}
    for (co, d), kt in first_known.items():
        by_co.setdefault(co, []).append((d, kt))
    pairs = later = 0
    for meetings in by_co.values():
        meetings.sort()
        for i, (d1, k1) in enumerate(meetings):
            for d2, k2 in meetings[i + 1:]:
                if (d2 - d1).days > RESCHEDULE_DAYS:
                    break
                pairs += 1
                later += k2 > k1
    return {"pairs": pairs, "later_filed": later}


def _rows(con, end: date) -> list[dict]:
    cur = con.execute(f"SELECT {', '.join(_COLS)} FROM board_meetings WHERE bm_date <= ?", [end])
    return [dict(zip(_COLS, r)) for r in cur.fetchall()]


def _futstk_names(end: date, futures_db: Path, equity_db: Path) -> tuple[dict, dict]:
    """Per year: FUTSTK names present on >= 60 % of that year's sessions; all names ever."""
    f = duckdb.connect(str(futures_db), read_only=True)
    per_year = f.execute("""
        WITH s AS (SELECT DISTINCT trade_date FROM futures_bhavcopy
                   WHERE inst_type = 'FUTSTK' AND trade_date BETWEEN '2016-01-01' AND ?),
             ny AS (SELECT year(trade_date) y, count(*) n FROM s GROUP BY 1),
             p AS (SELECT underlying, year(trade_date) y, count(DISTINCT trade_date) d
                   FROM futures_bhavcopy WHERE inst_type = 'FUTSTK'
                     AND trade_date BETWEEN '2016-01-01' AND ? GROUP BY 1, 2)
        SELECT p.y, p.underlying FROM p JOIN ny USING (y) WHERE p.d >= ? * ny.n""",
                         [end, end, MIN_PRESENCE]).fetchall()
    every = [r[0] for r in f.execute(
        "SELECT DISTINCT underlying FROM futures_bhavcopy WHERE inst_type = 'FUTSTK' "
        "AND trade_date BETWEEN '2016-01-01' AND ?", [end]).fetchall()]
    f.close()
    e = duckdb.connect(str(equity_db), read_only=True)
    prefix = {s: i[:ISIN_PREFIX_LEN] for s, i in e.execute(
        "SELECT symbol, isin FROM symbol_isin WHERE isin LIKE 'INE%'").fetchall()}
    e.close()
    years = {}
    for y, sym in per_year:
        years.setdefault(y, {})[sym] = prefix.get(sym)
    return years, {s: prefix.get(s) for s in every}


def certify(end: date, db: Path = DB, futures_db: Path = FUTURES_DB,
            equity_db: Path = EQUITY_DB) -> dict:
    con = duckdb.connect(str(db), read_only=True)
    rows = _rows(con, end)
    miss = missing_months(con, FIRST_MONTH, end)
    con.close()
    years, every = _futstk_names(end, futures_db, equity_db)
    res = [r for r in rows if r["is_results"]]
    prefixes = {r["isin_prefix"] for r in rows if r["isin_prefix"]}
    symbols = {r["symbol"] for r in rows}
    mapped = sum((p in prefixes) or (s in symbols) for s, p in every.items())
    per_year = []
    for y in sorted(years):
        cov = results_coverage(res, years[y], y)
        yr = [r for r in res if r["bm_date"].year == y]
        rev = sum(r["has_revision"] for r in yr)
        keys = [(r["isin_prefix"] or r["symbol"], r["bm_date"]) for r in yr]
        lead = sorted((r["bm_date"] - r["known_ts"].date()).days for r in yr)
        per_year.append({
            "year": y, "rows": sum(r["bm_date"].year == y for r in rows), "results_rows": len(yr),
            **cov, "b_pass": cov["share"] >= MIN_COVERAGE,
            "revision_share": rev / len(yr) if yr else 0.0,
            "dup_rows": len(keys) - len(set(keys)),
            "median_lead_days": lead[len(lead) // 2] if lead else None,
            **reschedule_pairs(yr),
        })
        per_year[-1]["e_pass"] = per_year[-1]["revision_share"] <= MAX_REVISION_SHARE
    out = {
        "end": end, "n_rows": len(rows), "n_results": len(res),
        "a_missing_months": miss, "a_pass": not miss,
        "c_known_before": known_before_meeting_share(rows),
        "d_mapped": mapped / len(every) if every else 0.0, "d_n_names": len(every),
        "per_year": per_year,
    }
    out["c_pass"] = out["c_known_before"] >= MIN_KNOWN_BEFORE
    out["d_pass"] = out["d_mapped"] >= MIN_MAPPED
    out["void_years"] = [p["year"] for p in per_year if not (p["b_pass"] and p["e_pass"])]
    out["certified"] = out["a_pass"] and out["c_pass"] and out["d_pass"]
    return out


def render(c: dict) -> str:
    ok = lambda b: "PASS" if b else "FAIL"
    lines = [
        "# GEX-XS-5D — P1 board-meeting calendar certification",
        "",
        "Script-generated by `scripts/gex_xs_5d/ingest_board_meetings.py --certify` — do not hand-edit.",
        f"Spec: `docs/reports/GEX_XS_5D_PRE_REGISTRATION.md` §7, §11 · end date {c['end']}",
        "",
        f"**P1 {'CERTIFIED' if c['certified'] else 'NOT CERTIFIED — freeze blocked'}**"
        f" · void years under (b)/(e): {c['void_years'] or 'none'}",
        "",
        f"- Rows: {c['n_rows']:,} (results rows {c['n_results']:,})",
        f"- (a) months with no rows, 2016-01 → {c['end']:%Y-%m}: "
        f"{[m.strftime('%Y-%m') for m in c['a_missing_months']] or 'none'} → **{ok(c['a_pass'])}**",
        f"- (c) results rows known on or before the meeting date: {c['c_known_before']:.4f}"
        f" (≥ {MIN_KNOWN_BEFORE}) → **{ok(c['c_pass'])}**",
        f"- (d) FUTSTK names (2016 → end) mapped by ISIN prefix or symbol: {c['d_mapped']:.4f}"
        f" of {c['d_n_names']} (≥ {MIN_MAPPED}) → **{ok(c['d_pass'])}**",
        "",
        "## Per year — (b) coverage and (e) revisions",
        "",
        f"(b): share of FUTSTK names present on ≥ {MIN_PRESENCE:.0%} of the year's sessions with "
        f"≥ {MIN_DISTINCT_RESULTS} distinct results meeting dates (≥ {MIN_COVERAGE:.0%}). "
        f"(e): share of results rows with a revision field (≤ {MAX_REVISION_SHARE:.0%}).",
        "",
        "| year | rows | results rows | names | covered | (b) share | (b) | (e) revision share | (e) | duplicate rows | median lead (days) | close-dated pairs | later-filed |",
        "|---|--:|--:|--:|--:|--:|---|--:|---|--:|--:|--:|--:|",
    ]
    for p in c["per_year"]:
        lines.append(
            f"| {p['year']} | {p['rows']:,} | {p['results_rows']:,} | {p['n_names']} | {p['n_covered']} | "
            f"{p['share']:.3f} | {ok(p['b_pass'])} | {p['revision_share']:.4f} | {ok(p['e_pass'])} | "
            f"{p['dup_rows']:,} | {p['median_lead_days']} | {p['pairs']} | {p['later_filed']} |")
    lines += [
        "",
        "Duplicate rows rise from 2023 (a structured row plus an XBRL intimation row per meeting); "
        "the exclusion rule needs only one row known by the formation close.",
        "",
        "**What (e) cannot see.** The revision fields are null on every row, so (e) passes "
        "vacuously: it cannot tell 'no reschedules' from 'reschedules overwrote the meeting date "
        "without a trace'. The last two columns are descriptive evidence on that question: "
        f"distinct results meeting dates of one company ≤ {RESCHEDULE_DAYS} days apart, and how "
        "many of those had the later-dated meeting filed later. Close-dated pairs exist every "
        "year, and in most the later date was filed later — a reschedule recorded as a new row, "
        "not an overwrite. That supports, but does not prove, an append-only archive.",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", required=True, help="YYYY-MM-DD: E_s, the last date to cover")
    ap.add_argument("--certify", action="store_true")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--db", type=Path, default=DB)
    ap.add_argument("--futures", type=Path, default=FUTURES_DB)
    ap.add_argument("--equity", type=Path, default=EQUITY_DB)
    a = ap.parse_args()
    end = date.fromisoformat(a.end)
    if not a.no_fetch:
        ingest(end, a.db)
    if a.certify:
        c = certify(end, a.db, a.futures, a.equity)
        REPORT.write_text(render(c), encoding="utf-8")
        print(f"P1 {'CERTIFIED' if c['certified'] else 'NOT CERTIFIED'} -> {REPORT}")


if __name__ == "__main__":
    main()
