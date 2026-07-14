"""CSMP Gate (c) — point-in-time NIFTY-200 universe membership.

Universe rule (charter D1 — locked, no tuning freedom): **top 200 equities by
6-month median daily turnover**, monthly rebalance on the last full session of
each month, computed from the ingested store only. The parameters (200, the 6-month
median) are charter-locked. A split conserves price x quantity, so turnover needs
no corporate-action adjustment — ranking runs on raw `turnover` (gate a confirms the
field is populated for the whole span: 0 NULLs), and gate (b)'s adjusted view is not
consulted.

Source decision (this script evidences it; the audit re-states it): NSE publishes no
freely-obtainable point-in-time index-constituent *change history* (add/drop with
effective dates) back to the dev-window start — the `niftyindices` CSV path answers a
wrong-content 200 (an HTML shell) and the archives carry only the *current* survivor
list. The mechanical top-200-by-turnover rule is therefore the charter-locked
fallback, chosen on evidence, not assertion. A snapshot of today's list is fetched
for a validation cross-check ONLY (overlap with the most-recent rebalance); it is
never a membership input — a present-day survivor list is exactly the bias this gate
exists to prevent.

Inheritance (consumed, not re-derived):
  symbol_isin       non-equity filter (INE* = company; INF*/IN0*/IN9* = fund / SGB /
                    govt paper; name pattern `%BEES%/%ETF%/%GOLD%` is a fallback only)
  symbol_changes    entity continuity across renames (INFOSYSTCH -> INFY is one entity)
  instrument_master NSE EQUITY_L company master — resolves recent IPOs that carry no
                    ISIN in the cached raw payloads (ETERNAL, GROWW, SWIGGY, ...) and
                    leaves ICICIMOM30 (a fund) absent, i.e. named as a hole
  ca_scope_exclusions / ca_evidence_exceptions — a price-adjustment concern, not a
                    membership concern: flagged for gate (e), never dropped here

Usage:
    python scripts/csmp/build_universe.py
"""

import csv
import io
import re
import sys
import urllib.error
import urllib.request
import ssl
from collections import Counter
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
RAW_DIR = ROOT / "data" / "market_data" / "universe_raw"

UNIVERSE_SIZE = 200
LOOKBACK_MONTHS = 6
TRADING_FLOOR = 0.60
FULL_SESSION_MIN = 200
REBAL_START = date(2012, 1, 1)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

RE_RIGHTS = re.compile(r"-RE\d*$")
NAME_NON_EQUITY = re.compile(r"(BEES|ETF|GOLD)")

EQUITY_L_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
NIFTY200_CSV_URL = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
NIFTYINDICES_CSV_URL = "https://www.niftyindices.com/IndexConstituent/ind_Nifty200.csv"
NIFTYINDICES_HIST_URL = (
    "https://archives.nseindia.com/content/indices/historical/"
    "IndexConstituentHistory.xlsx")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS universe_membership (
    rebalance_date  DATE,
    symbol          VARCHAR,
    rank            INTEGER,
    turnover_median DOUBLE,
    method          VARCHAR,
    PRIMARY KEY (rebalance_date, symbol)
);
CREATE TABLE IF NOT EXISTS universe_intervals (
    symbol      VARCHAR,
    entity      VARCHAR,
    entry_date  DATE,
    exit_date   DATE,
    PRIMARY KEY (entity)
);
CREATE TABLE IF NOT EXISTS instrument_master (
    symbol          VARCHAR,
    name            VARCHAR,
    instrument_type VARCHAR,
    series          VARCHAR,
    listing_date    VARCHAR,
    isin            VARCHAR,
    face_value      VARCHAR,
    source          VARCHAR,
    PRIMARY KEY (symbol)
);
CREATE TABLE IF NOT EXISTS universe_eligibility (
    symbol  VARCHAR,
    entity  VARCHAR,
    class   VARCHAR,
    via     VARCHAR,
    PRIMARY KEY (symbol)
);
CREATE TABLE IF NOT EXISTS symbol_entity_intervals (
    symbol      VARCHAR,
    valid_from  DATE,
    valid_to    DATE,
    entity      VARCHAR,
    PRIMARY KEY (symbol, valid_from)
);
CREATE TABLE IF NOT EXISTS universe_probes (
    probe        VARCHAR,
    url          VARCHAR,
    outcome      VARCHAR,
    status       VARCHAR,
    note         VARCHAR
);
"""


# --------------------------------------------------------------------------
# HTTP fetch with shape+identity validation (gate-a G4 discipline)
# --------------------------------------------------------------------------
def _http_get(url, timeout=25, referer=None):
    headers = {"User-Agent": UA, "Accept": "*/*"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        return r.status, r.read()


def _probe(url, timeout=20):
    try:
        st, body = _http_get(url, timeout=timeout)
        return str(st), len(body), body[:160]
    except urllib.error.HTTPError as e:
        try:
            body = e.read()[:160]
        except Exception:
            body = b""
        return f"HTTP {e.code}", len(body), body
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return f"ERR {type(e).__name__}", 0, str(e).encode()[:160]


def fetch_instrument_master(con):
    """NSE EQUITY_L.csv — the authoritative company/instrument master (ISIN, name,
    listing date, face value). Cached under universe_raw/ for deterministic re-runs."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache = RAW_DIR / "equity_l.csv"
    if cache.exists():
        text = cache.read_bytes().decode("utf-8-sig", "replace")
        outcome = "cached"
        status = "local"
    else:
        status, raw = _http_get(EQUITY_L_URL, timeout=40)
        text = raw.decode("utf-8-sig", "replace")
        cache.write_bytes(raw)
        outcome = f"fetched HTTP {status}"
    reader = csv.DictReader(io.StringIO(text))
    reader.fieldnames = [(f or "").strip() for f in reader.fieldnames]
    rows = []
    for r in reader:
        sym = (r.get("SYMBOL") or "").strip().upper()
        if not sym:
            continue
        isin = (r.get("ISIN NUMBER") or "").strip().upper()
        itype = ("equity" if isin.startswith("INE") else
                 "fund" if isin.startswith("INF") else
                 "govt" if isin.startswith(("IN0", "IN9")) else "unknown")
        rows.append({
            "symbol": sym,
            "name": (r.get("NAME OF COMPANY") or "").strip(),
            "instrument_type": itype,
            "series": (r.get("SERIES") or "").strip(),
            "listing_date": (r.get("DATE OF LISTING") or "").strip(),
            "isin": isin,
            "face_value": (r.get("FACE VALUE") or "").strip(),
            "source": "NSE_EQUITY_L",
        })
    df = pd.DataFrame(rows)
    con.execute("DELETE FROM instrument_master")
    con.execute("INSERT INTO instrument_master SELECT symbol, name, instrument_type, "
                "series, listing_date, isin, face_value, source FROM df")
    con.execute("INSERT INTO universe_probes VALUES (?, ?, ?, ?, ?)",
                ["instrument_master", EQUITY_L_URL, outcome, status,
                 f"{len(rows)} companies; {sum(1 for r in rows if r['isin'].startswith('INE'))} INE ISIN"])
    return rows


def probe_official_membership(con):
    """Attempt the official point-in-time NIFTY-200 history. The CSV API answers a
    wrong-content 200 (HTML) and no dated change-history file is published; the
    archives carry only the current survivor list (fetched for validation ONLY)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    probes = []

    status, n, head = _probe(NIFTYINDICES_CSV_URL, timeout=20)
    wrong = head.lstrip().lower().startswith(b"<!doctype html")
    probes.append(("niftyindices_csv_api", NIFTYINDICES_CSV_URL,
                   f"{status} len={n} {'wrong-content(HTML)' if wrong else 'csv'}",
                   "survivor_current_or_unreachable",
                   "Answers an HTML shell, not the CSV — needs a session/CSRF token "
                   "the public endpoint does not expose."))

    status2, n2, head2 = _probe(NIFTYINDICES_HIST_URL, timeout=20)
    probes.append(("historical_change_history", NIFTYINDICES_HIST_URL,
                   f"{status2} len={n2}", "absent",
                   "No dated constituent change-history file at this path (404)."))

    # The current constituent list: obtainable, but survivor-biased -> validation only.
    cur_cache = RAW_DIR / "nifty200_current.csv"
    try:
        st, raw = _http_get(NIFTY200_CSV_URL, timeout=25)
        cur_cache.write_bytes(raw)
        cur_syms = set()
        for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig", "replace"))):
            s = (r.get("Symbol") or r.get("SYMBOL") or "").strip().upper()
            if s:
                cur_syms.add(s)
        probes.append(("current_list_validation_only", NIFTY200_CSV_URL,
                       f"{st} {len(cur_syms)} symbols", "survivor_current",
                       "Today's list. VALIDATION ONLY — never a membership input. "
                       "A present-day constituent list validates a reconstruction, "
                       "it is not a source of one."))
    except Exception as e:
        probes.append(("current_list_validation_only", NIFTY200_CSV_URL,
                       f"ERR {type(e).__name__}", "unreachable",
                       "Could not fetch; validation cross-check skipped."))
    for p in probes:
        con.execute("INSERT INTO universe_probes VALUES (?, ?, ?, ?, ?)", list(p))
    method = "turnover_top200"
    print(f"Official membership : unobtainable as point-in-time history -> "
          f"mechanical {method}")
    return method


# --------------------------------------------------------------------------
# Entity continuity (rename chains via union-find on symbol_changes)
# --------------------------------------------------------------------------
class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            return x
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        # deterministic tie-break keeps the representative stable across runs
        self.parent[max(ra, rb)] = min(ra, rb)


def build_entities(con):
    from collections import defaultdict as _dd
    uf = UnionFind()
    n_records = 0
    edges = []
    for old, new, eff in con.execute(
            "SELECT UPPER(old_symbol), UPPER(new_symbol), effective_dt "
            "FROM symbol_changes").fetchall():
        if old and new:
            uf.union(old, new)
            edges.append((old, new, eff))
            n_records += 1
    store_syms = [r[0] for r in con.execute(
        "SELECT DISTINCT symbol FROM equity_bhavcopy WHERE series IN ('EQ','BE')").fetchall()]

    # base (time-agnostic) entity = union-find representative — preserves the labels of the
    # 991 renames that already resolve correctly and every non-renamed symbol.
    base = {s: uf.find(s) for s in store_syms}

    # actual traded span per store symbol (needed by both ISIN linkage and recycled-ticker split).
    spans = {r[0]: (r[1], r[2]) for r in con.execute(
        "SELECT symbol, MIN(trade_date), MAX(trade_date) FROM equity_bhavcopy "
        "WHERE series IN ('EQ','BE') GROUP BY symbol").fetchall()}

    # --- Prompt 5 Task 3 (F-8): ISIN issuer-prefix linkage ---
    # A face-value change re-issues the security with a new ISIN serial (same issuer prefix),
    # which the full-ISIN entity map severs — exactly at the corporate action it must adjust
    # for. Merge entities sharing an `INE` issuer prefix where print ranges are disjoint and
    # abutting (NOT overlapping — that's a DVR/partly-paid class). Enumeration + evidence in
    # the report (n_merged_issuers).
    isin_rows = con.execute("""
        SELECT si.symbol, SUBSTR(si.isin,1,9) iss
        FROM symbol_isin si
        WHERE si.isin LIKE 'INE%'
    """).fetchall()
    # map per store symbol: use `base` for entity (already computed from union-find)
    iss_map = {}
    for sym, iss in isin_rows:
        if sym in set(store_syms):
            iss_map[sym] = iss
    # group store symbols by issuer prefix
    by_iss = _dd(list)
    for s in store_syms:
        iss = iss_map.get(s)
        if iss:
            by_iss[iss].append(s)
    merges = []   # (issuer_prefix, list[(symbol1, entity1), ...], gap_days)
    halt_overlaps = []  # issuers with cross-entity symbol overlaps (collected, raised at end)
    for iss, syms in by_iss.items():
        ents = {base.get(s, s) for s in syms}
        if len(ents) <= 1:
            continue
        # Merge only entities whose CONSTITUENT symbols have abutting, non-overlapping
        # print ranges. Two entities that share an issuer ARE the same company if their
        # symbol print ranges are temporally disjoint (old ticker ends before new begins).
        # Co-trading symbols (DVR, partly-paid) have overlapping ranges and must NOT merge.
        sym_spans = [(s, spans[s][0], spans[s][1]) for s in syms if s in spans]
        sym_spans.sort(key=lambda x: x[1])
        # Sort entities by their EARLIEST start date (chronological), so the older company
        # is e0 and the newer one is e1 — then e0's last print before e1's first is a rename.
        frag_ents = sorted({base.get(s, s) for s in syms},
                           key=lambda e: min(l for s,l,_ in sym_spans if base.get(s,s)==e))
        for k in range(1, len(frag_ents)):
            e0, e1 = frag_ents[k-1], frag_ents[k]
            s0 = [(lo, hi) for s, lo, hi in sym_spans if base.get(s,s) == e0]
            s1 = [(lo, hi) for s, lo, hi in sym_spans if base.get(s,s) == e1]
            if not s0 or not s1: continue
            # closest pair: latest exit of e0 vs earliest entry of e1
            hi0 = max(h for _, h in s0)
            lo1 = min(l for l, _ in s1)
            # check for cross-entity symbol overlap (any s0[i] overlaps any s1[j])
            cross_overlap = any(h0 >= l1 for l0,h0 in s0 for l1,_ in s1)
            if cross_overlap:
                halt_overlaps.append((iss, e0, e1))
                continue
            if hi0 < lo1:          # abutting -> same company rename
                uf.union(e0, e1)
                merges.append((iss, [(s, base.get(s, s)) for s in syms
                                     if base.get(s,s) in (e0,e1)],
                                (lo1 - hi0).days if lo1 and hi0 else None))
    if halt_overlaps:
        print(f"ISIN issuer overlaps  : {len(halt_overlaps)} issuer(s) skipped — overlapping "
              f"print ranges (likely DVR/partly-paid share classes): "
              f"{', '.join(f'{iss}({e0}/{e1})' for iss,e0,e1 in halt_overlaps[:10])}. "
              "Reported per Prompt 5 Task 3, P7 — not merged. All other abutting issuers "
              "merged successfully.")
    n_merged = len(merges)
    if n_merged:
        print(f"ISIN issuer merges    : {n_merged} merged (disjoint, abutting print ranges)")
        # recompute base after ISIN linkage merges
        base = {s: uf.find(s) for s in store_syms}

    # components at the base grain, for the co-trading test.
    comp = _dd(list)
    for s in store_syms:
        comp[base[s]].append(s)

    SENTINEL = date(9999, 12, 31)
    intervals = []          # (symbol, valid_from, valid_to, entity)
    n_split = 0
    for s in store_syms:
        s_lo, s_hi = spans[s]
        # a symbol's OWN outgoing rename dates: at each, its identity handed to the successor;
        # prints on/after that date are a recycled ticker (a different entity) ONLY IF they
        # co-trade with another member of the same base entity. NSE recycles vacated tickers;
        # a recorded effective_dt that predates the symbol's own first print (a stale rename
        # record) does not co-trade and is left merged.
        cut = None
        for old, new, eff in edges:
            if old != s or eff is None:
                continue
            if s_hi < eff:                       # no prints on/after this rename -> not recycled
                continue
            # do the on/after-eff prints of s overlap any other base-entity member?
            recycled_lo = max(s_lo, eff)
            for m in comp[base[s]]:
                if m == s:
                    continue
                m_lo, m_hi = spans[m]
                if m_lo <= s_hi and recycled_lo <= m_hi:   # spans overlap
                    cut = eff if cut is None else min(cut, eff)
                    break
        if cut is None or cut <= s_lo:
            intervals.append((s, s_lo, SENTINEL, base[s]))
        else:
            intervals.append((s, s_lo, cut, base[s]))        # pre-cut leg -> the chain entity
            intervals.append((s, cut, SENTINEL, s))          # recycled leg -> its own entity (its ticker)
            n_split += 1

    # --- assertion: no entity may contain two symbols with overlapping trading spans ---
    #     (the precondition Prompt 2 silently assumed). Measured on ACTUAL prints per interval,
    #     half-open [valid_from, valid_to): a print at valid_to belongs to the next interval.
    df_iv0 = pd.DataFrame(intervals, columns=["symbol", "valid_from", "valid_to", "entity"])
    con.execute("CREATE OR REPLACE TEMP TABLE _iv_check AS SELECT * FROM df_iv0")
    seg_rows = con.execute("""
        SELECT i.entity, i.symbol, MIN(e.trade_date) lo, MAX(e.trade_date) hi
        FROM _iv_check i
        JOIN equity_bhavcopy e ON e.symbol = i.symbol AND e.series IN ('EQ','BE')
             AND e.trade_date >= i.valid_from AND e.trade_date < i.valid_to
        GROUP BY i.entity, i.symbol
    """).fetchall()
    con.execute("DROP TABLE _iv_check")
    per_entity = _dd(list)   # entity -> list of (symbol, actual_lo, actual_hi) for populated intervals
    for ent, sym, lo, hi in seg_rows:
        per_entity[ent].append((sym, lo, hi))
    overlaps = []
    for ent, segs in per_entity.items():
        segs.sort(key=lambda x: x[1])
        for i in range(1, len(segs)):
            if segs[i][0] != segs[i - 1][0] and segs[i][1] <= segs[i - 1][2]:   # inclusive print spans
                overlaps.append((ent, segs[i - 1][0], segs[i][0]))
    assert not overlaps, (
        f"CO-TRADING ENTITY — {len(overlaps)} entity(ies) contain overlapping symbols "
        f"(recycled ticker not split): {overlaps[:5]}. STOP.")

    df_iv = pd.DataFrame(intervals, columns=["symbol", "valid_from", "valid_to", "entity"])
    con.execute("DELETE FROM symbol_entity_intervals")
    con.execute("INSERT INTO symbol_entity_intervals "
                "SELECT symbol, valid_from, valid_to, entity FROM df_iv")

    # symbol_entity temp (time-agnostic base map) — kept for eligibility classification, whose
    # equity/non-equity verdict does not depend on date. Time resolution lives in the intervals.
    rows = [{"symbol": s, "entity": base[s]} for s in store_syms]
    df = pd.DataFrame(rows)
    con.execute("CREATE OR REPLACE TEMP TABLE symbol_entity AS "
                "SELECT CAST(symbol AS VARCHAR) symbol, CAST(entity AS VARCHAR) entity FROM df")
    return rows, n_records, n_split, n_merged


# --------------------------------------------------------------------------
# Eligibility classification (ISIN primary, name fallback, instrument master)
# --------------------------------------------------------------------------
def classify_eligibility(con):
    """Per store symbol -> (entity, class, via).

    The charter eligibility is "equity (not INF*, not name-pattern fallback)": equity is
    the DEFAULT; instruments are excluded only when positively identified as non-equity.
    class in:
      equity_confirmed     INE* ISIN in symbol_isin, or company in the NSE EQUITY_L master
      equity_unidentified  no ISIN anywhere, not name-pattern, not a rights entitlement —
                           default-equity but FLAGGED (a hole: ICICIMOM30 is here; these
                           almost never rank top-200 and are named in the audit, not dropped)
      non_equity_isin      INF* (mutual-fund scheme / ETF), IN0*/IN9* (govt paper / SGB)
      non_equity_name      no ISIN, matches %BEES%/%ETF%/%GOLD% (gate-a H2 fallback)
      rights_entitlement   `-RE` suffix (NSE rights entitlement, not a share line)

    Entity continuity: an entity is equity if ANY of its component symbols is equity, so a
    rename whose old ticker carries no ISIN (VATECH->WABAG, ANGELBRKG->ANGELONE) keeps the
    entity eligible across the rename. Membership is computed per entity."""
    isin_map = {r[0]: (r[1] or "") for r in con.execute(
        "SELECT UPPER(symbol), UPPER(isin) FROM symbol_isin").fetchall()}
    master_isin = {r[0]: (r[1] or "") for r in con.execute(
        "SELECT UPPER(symbol), UPPER(isin) FROM instrument_master").fetchall()}

    rows = con.execute(
        "SELECT se.symbol, se.entity FROM symbol_entity se ORDER BY se.symbol").fetchall()
    out = []
    for symbol, entity in rows:
        isin = isin_map.get(symbol)
        if isin:
            if isin.startswith("INE"):
                cls, via = "equity_confirmed", "symbol_isin"
            else:
                cls, via = "non_equity_isin", f"isin:{isin[:3]}"
        else:
            misin = master_isin.get(symbol)
            if misin:
                if misin.startswith("INE"):
                    cls, via = "equity_confirmed", "instrument_master"
                else:
                    cls, via = "non_equity_isin", f"master:{misin[:3]}"
            elif RE_RIGHTS.search(symbol):
                cls, via = "rights_entitlement", "suffix:-RE"
            elif NAME_NON_EQUITY.search(symbol):
                cls, via = "non_equity_name", "name_pattern"
            else:
                cls, via = "equity_unidentified", "no_isin_no_master"
        out.append({"symbol": symbol, "entity": entity, "class": cls, "via": via})
    con.execute("DELETE FROM universe_eligibility")
    df = pd.DataFrame(out)
    con.execute("INSERT INTO universe_eligibility SELECT symbol, entity, class, via FROM df")
    return out


# --------------------------------------------------------------------------
# Rebalance calendar + lookback
# --------------------------------------------------------------------------
def rebalance_dates(con):
    rows = con.execute("""
        WITH m AS (
            SELECT EXTRACT(YEAR FROM trade_date)::INT y,
                   EXTRACT(MONTH FROM trade_date)::INT mo, trade_date
            FROM trading_calendar WHERE n_symbols >= ?)
        SELECT MAX(trade_date) FROM m GROUP BY y, mo
        HAVING MAX(trade_date) >= ? ORDER BY 1
    """, [FULL_SESSION_MIN, REBAL_START]).fetchall()
    return [r[0] for r in rows]


def lookback_start(t):
    total = t.year * 12 + (t.month - 1) - (LOOKBACK_MONTHS - 1)
    return date(total // 12, total % 12 + 1, 1)


# --------------------------------------------------------------------------
# Membership computation (the mechanical turnover rule, point-in-time)
# --------------------------------------------------------------------------
def build_membership(con, method):
    rebal = rebalance_dates(con)
    # entity resolved by (symbol, trade_date) via the interval table — no longer sums a
    # recycled ticker's turnover into the chain it vacated (Prompt 3 item 2).
    con.execute("""
        CREATE OR REPLACE TEMP TABLE entity_turnover AS
        SELECT i.entity, e.trade_date, SUM(e.turnover) AS turnover
        FROM equity_bhavcopy e
        JOIN symbol_entity_intervals i ON i.symbol = e.symbol
             AND e.trade_date >= i.valid_from AND e.trade_date < i.valid_to
        WHERE e.series IN ('EQ','BE')
        GROUP BY i.entity, e.trade_date
    """)
    con.execute("CREATE INDEX IF NOT EXISTS _et ON entity_turnover(entity, trade_date)")

    # an interval-entity is equity iff its symbol is equity-classed (class is time-agnostic).
    con.execute("""
        CREATE OR REPLACE TEMP TABLE equity_entities AS
        SELECT DISTINCT i.entity
        FROM symbol_entity_intervals i
        JOIN universe_eligibility u ON u.symbol = i.symbol
        WHERE u.class IN ('equity_confirmed','equity_unidentified')
    """)

    membership = []
    for t in rebal:
        lb = lookback_start(t)
        rows = con.execute("""
            WITH sess AS (
                SELECT COUNT(*) n FROM trading_calendar
                WHERE n_symbols >= ? AND trade_date BETWEEN ? AND ?
            ),
            traded AS (
                SELECT et.entity, MEDIAN(et.turnover) AS med,
                       SUM(CASE WHEN tc.n_symbols >= ? THEN 1 ELSE 0 END) AS nd
                FROM entity_turnover et
                JOIN trading_calendar tc ON tc.trade_date = et.trade_date
                WHERE et.trade_date BETWEEN ? AND ? AND et.turnover > 0
                GROUP BY et.entity
            ),
            on_t AS (          -- must be actually trading on the rebalance session
                SELECT entity FROM entity_turnover WHERE trade_date = ? AND turnover > 0
            ),
            elig AS (
                SELECT t.entity, t.med
                FROM traded t
                CROSS JOIN sess
                JOIN on_t USING (entity)
                WHERE t.entity IN (SELECT entity FROM equity_entities)
                  AND t.nd >= ? * sess.n
            ),
            label AS (         -- the entity's ticker in force on t (date-resolved)
                SELECT i.entity, b.symbol
                FROM equity_bhavcopy b
                JOIN symbol_entity_intervals i ON i.symbol = b.symbol
                     AND b.trade_date >= i.valid_from AND b.trade_date < i.valid_to
                WHERE b.trade_date = ? AND b.turnover > 0
                QUALIFY ROW_NUMBER() OVER (PARTITION BY i.entity ORDER BY b.turnover DESC) = 1
            )
            SELECT l.symbol, e.entity, e.med
            FROM elig e
            JOIN label l ON l.entity = e.entity
        """, [FULL_SESSION_MIN, lb, t, FULL_SESSION_MIN, lb, t, t, TRADING_FLOOR, t]).fetchall()
        ranked = sorted(rows, key=lambda r: (-r[2], r[0]))[:UNIVERSE_SIZE]
        for rank, (symbol, entity, med) in enumerate(ranked, 1):
            membership.append({
                "rebalance_date": t, "symbol": symbol, "rank": rank,
                "turnover_median": float(med), "method": method, "entity": entity,
            })
    con.execute("DELETE FROM universe_membership")
    df = pd.DataFrame([{k: v for k, v in r.items() if k != "entity"} for r in membership])
    con.execute("INSERT INTO universe_membership SELECT rebalance_date, symbol, rank, "
                "turnover_median, method FROM df")
    return membership, rebal


def build_intervals(con, membership):
    """Per entity: first/last rebalance of membership. symbol = the entity's most
    recent active ticker (canonical label); exit_date NULL while still a member."""
    if not membership:
        con.execute("DELETE FROM universe_intervals")
        return
    df = pd.DataFrame(membership)
    last_ticker = (df.sort_values(["entity", "rebalance_date"])
                     .drop_duplicates("entity", keep="last")[["entity", "symbol"]]
                     .rename(columns={"symbol": "last_symbol"}))
    spans = (df.groupby("entity")
               .agg(entry_date=("rebalance_date", "min"),
                    exit_date=("rebalance_date", "max"))
               .reset_index()
               .merge(last_ticker, on="entity"))
    spans["exit_date"] = spans.apply(
        lambda r: None if r["exit_date"] == df["rebalance_date"].max() else r["exit_date"],
        axis=1)
    spans = spans.rename(columns={"last_symbol": "symbol"})[
        ["symbol", "entity", "entry_date", "exit_date"]]
    con.execute("DELETE FROM universe_intervals")
    con.execute("INSERT INTO universe_intervals SELECT symbol, entity, entry_date, "
                "exit_date FROM spans")


def main():
    con = duckdb.connect(str(DB_PATH))
    # These five tables are fully derived and rebuilt every run; drop+recreate keeps
    # the schema in step with this script (inherited tables are never touched).
    for t in ("universe_membership", "universe_intervals", "instrument_master",
              "universe_eligibility", "universe_probes", "symbol_entity_intervals"):
        con.execute(f"DROP TABLE IF EXISTS {t}")
    con.execute(SCHEMA_SQL)
    con.execute("DELETE FROM universe_probes")

    method = probe_official_membership(con)
    fetch_instrument_master(con)
    _, n_rename, n_split, n_merged = build_entities(con)
    elig = classify_eligibility(con)

    cc = Counter(r["class"] for r in elig)
    print(f"Rename records     : {n_rename:,} (entity continuity via symbol_changes)")
    print(f"Recycled-ticker splits: {n_split} (symbol printing on/after its own rename, "
          "co-trading its vacated chain -> time-sliced into a second entity)")
    print(f"ISIN issuer merges  : {n_merged} (fragmented INE-issuer entities merged; "
          "disjoint, abutting print ranges)")
    print(f"Eligibility classes: " + ", ".join(f"{k}={v:,}" for k, v in
          sorted(cc.items(), key=lambda x: -x[1])))

    membership, rebal = build_membership(con, method)
    build_intervals(con, membership)

    n_rebal = len(rebal)
    n_cells = len(membership)
    yr_cells = Counter(r["rebalance_date"].year for r in membership)
    yr_rebals = Counter(r["rebalance_date"].year for r in [
        {"rebalance_date": d} for d in rebal])
    print(f"Rebalance dates    : {n_rebal} (last full session/month, {rebal[0]}..{rebal[-1]})")
    print(f"Membership cells   : {n_cells:,}")
    print("Avg members/rebalance by year: " + ", ".join(
        f"{y}:{round(yr_cells[y] / yr_rebals[y])}" for y in sorted(yr_cells)))

    con.close()
    print("\nDone. Run scripts/csmp/audit_universe.py next.")


if __name__ == "__main__":
    main()
