"""CSMP Gate (b) — corporate-action ingestion from the NSE CF-CA feed.

NSE's CF-CA equities CSVs are the sole source for SPLIT and BONUS: they carry the
true ex-date and name both legs of a combined action in one PURPOSE string. The
BSE JSON cache supplies DIVIDEND only — it keys bonuses on the record date, which
is not the ex-date, and it mislabels bonus debentures as equity bonuses.

Face values are read from the face-value clause of the PURPOSE text, never by
scanning the whole string for integers. A record whose clause does not parse is
rejected into `ca_parse_rejects` with a reason and never guessed at.

Every factor is then screened against the market's own repricing at the ex-date;
factors that cannot be reconciled land in `ca_evidence_exceptions`. The exchange
document remains the authority for the event and its ratio — the price gap is a
screen for arithmetic error, not a source.

Usage:
    python scripts/csmp/ingest_corporate_actions.py
"""

import csv
import io
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
RAW_DIR = ROOT / "data" / "market_data" / "corporate_actions_raw"

SPECIAL_DIV_THRESHOLD = 0.20
EVIDENCE_TOLERANCE = 0.25
EVIDENCE_MAX_GAP_DAYS = 5

# Gold-ETF unit sub-divisions. The NSE equity CA feed carries no ETF records, so
# these come from the AMC notices. Each is corroborated against the ex-date gap;
# QGOLDHALF is 1:50, not the 1:100 every other gold ETF used.
ETF_SPLITS = [
    ("GOLDBEES", date(2019, 12, 19), 100, 1, "AMC notice; implied_close 0.00999"),
    ("AXISGOLD", date(2020, 7, 23), 100, 1, "AMC notice; implied_open 0.01000"),
    ("HDFCMFGETF", date(2021, 2, 17), 100, 1, "AMC notice; implied_close 0.00985"),
    ("GOLDSHARE", date(2021, 3, 25), 100, 1, "AMC notice; implied_close 0.01001"),
    ("BSLGOLDETF", date(2021, 11, 25), 100, 1, "AMC notice; implied_open 0.00997"),
    ("QGOLDHALF", date(2021, 12, 16), 50, 1, "AMC notice; 1:50 — implied_close 0.02024"),
    ("SETFGOLD", date(2022, 1, 6), 100, 1, "AMC notice; implied_close 0.00994"),
    ("LICMFGOLD", date(2026, 3, 6), 100, 1, "AMC notice; implied_close 0.00994"),
    ("IVZINGOLD", date(2026, 4, 30), 100, 1, "AMC notice; implied_close 0.01019"),
]

# Moves the audit flags as CA-shaped that gate (b) does not undertake to explain.
# Each is carried forward: gate (c)'s universe construction must honour them.
#
# The charter scopes gate (b) to "splits/bonuses (and rights, where material)".
# For the rows below the NSE CF-CA feed carries only AGM/dividend records — no
# split, no bonus, no special dividend — so no factor is derivable from the source
# this gate uses. Every one has the shape of a demerger, but that is a *suspicion*
# recorded as such: nothing in this repository corroborates it, and the resulting
# entities' relative values on the ex-date would be needed to derive a factor.
SCOPE_EXCLUSIONS = [
    ("SURANAT&P", date(2010, 8, 17), "out_of_scope_corporate_action"),
    ("TEXMACOLTD", date(2010, 11, 1), "out_of_scope_corporate_action"),
    ("WEIZMANIND", date(2010, 12, 8), "out_of_scope_corporate_action"),
    ("TRIVENI", date(2011, 5, 3), "out_of_scope_corporate_action"),
    ("ORIENTABRA", date(2011, 11, 11), "out_of_scope_corporate_action"),
    ("ORIENTPPR", date(2013, 3, 7), "out_of_scope_corporate_action"),
    ("FOURSOFT", date(2013, 10, 17), "out_of_scope_corporate_action"),
    ("SINTEX", date(2017, 5, 25), "out_of_scope_corporate_action"),
    ("DCM", date(2019, 5, 30), "out_of_scope_corporate_action"),
    ("QUESS", date(2025, 4, 15), "out_of_scope_corporate_action"),
    ("ABFRL", date(2025, 5, 22), "out_of_scope_corporate_action"),
    ("AHLEAST", date(2022, 10, 6), "disputed_ratio"),
    ("ICICIMOM30", date(2022, 8, 12), "unidentified_instrument"),
]

EXCLUSION_DETAIL = {
    "out_of_scope_corporate_action":
        "CA-shaped move with no split, bonus or special dividend in the NSE CF-CA "
        "feed. Charter scopes gate (b) to splits/bonuses/rights. Shape suggests a "
        "demerger — unverified; deriving a factor needs the resulting entities' "
        "relative values on the ex-date. Carried to gate (c).",
    "disputed_ratio":
        "NSE CF-CA publishes 'Bonus 1:2' (factor 0.666667); the market repriced by "
        "0.5016, i.e. a 1:1 bonus. Exchange text and market disagree. Needs "
        "adjudication against the company filing. Factor stored as published.",
    "unidentified_instrument":
        "No ISIN in any raw bhavcopy payload and no match to gate (a) H2's name "
        "pattern, so the non-equity exclusion cannot reach it. A -89.9% move on an "
        "ICICI momentum ETF. Needs an NSE instrument master, which gate (c) "
        "requires regardless.",
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ca_scope_exclusions (
    symbol     VARCHAR,
    move_date  DATE,
    reason     VARCHAR,
    detail     VARCHAR,
    carried_to VARCHAR
);
CREATE TABLE IF NOT EXISTS corporate_actions (
    symbol       VARCHAR,
    ex_date      DATE,
    action_type  VARCHAR,
    purpose_raw  VARCHAR,
    ratio_or_fv  VARCHAR,
    source       VARCHAR,
    scripcode    VARCHAR,
    raw_json     VARCHAR
);
CREATE TABLE IF NOT EXISTS adjustment_factors (
    symbol       VARCHAR,
    ex_date      DATE,
    factor       DOUBLE,
    action_type  VARCHAR,
    source       VARCHAR,
    PRIMARY KEY (symbol, ex_date, action_type)
);
CREATE TABLE IF NOT EXISTS ca_parse_rejects (
    symbol       VARCHAR,
    ex_date      DATE,
    action_type  VARCHAR,
    reason       VARCHAR,
    purpose_raw  VARCHAR,
    source       VARCHAR
);
CREATE TABLE IF NOT EXISTS ca_evidence_exceptions (
    symbol         VARCHAR,
    ex_date        DATE,
    legs           VARCHAR,
    stored_factor  DOUBLE,
    implied_open   DOUBLE,
    implied_close  DOUBLE,
    deviation      DOUBLE
);
"""

# The face-value clause begins at one of these words. Everything before it —
# dividend amounts, bonus ratios, meeting notices — is not a face value. A bare
# 'Spl' is not among them: in this feed it always abbreviates 'Special Dividend'
# ('Agm/Spl Div- Rs.5/-'), never a split, which is always written 'Fv Spl'.
SPLIT_KW = re.compile(
    r"(?i)(?:FACE\s+VALUE\s+SP|F\.?V\.?\s*SP)(?:LIT|LT|L)\b"
    r"|\bSPLIT\b|\bSPLT\b|SUB-?DIVISION|CONSOLIDATION")
# 'Rs.10/- To Re.1/-', 'Rs 10/- Per Share To Rs 2/- Per Share', 'Rs.5tors.2'
FV_RS = re.compile(
    r"(?i)\bR[se]\.?\s*(\d+(?:\.\d+)?)\s*(?:/-)?\s*"
    r"(?:per\s+share\s*)?(?:each\s*)?to\s*R[se]\.?\s*(\d+(?:\.\d+)?)")
# 'From 10/- To Face Value 2/-' — no currency prefix on either side
FV_FROM = re.compile(
    r"(?i)\bFROM\b\s*(?:R[se]\.?\s*)?(\d+(?:\.\d+)?)\s*(?:/-)?"
    r".{0,30}?\bTO\b\s*(?:FACE\s+VALUE\s*)?(?:R[se]\.?\s*)?(\d+(?:\.\d+)?)")

BONUS_KW = re.compile(r"(?i)\bBON(?:US)?\b")
BONUS_RATIO = re.compile(r"(?i)\bBON(?:US)?\b.{0,40}?(\d+)\s*:\s*(\d+)")
# Bonus debentures, DVR shares, NCRPS and preference shares do not dilute equity.
NON_EQUITY_BONUS = re.compile(
    r"(?i)\b(deb|debentures?|dvr|preference|ncrps|ncd|rps)\b|DEB\d")
# A capital reduction bundled with a consolidation has no single price factor.
CAP_REDUCTION = re.compile(r"(?i)CAPITAL\s+REDUCTION")


def parse_split_clause(purpose):
    """(old_fv, new_fv) from the face-value clause, or (None, reason)."""
    if CAP_REDUCTION.search(purpose):
        return None, "capital_reduction_ambiguous"
    kw = SPLIT_KW.search(purpose)
    if not kw:
        return None, "no_split_clause"
    clause = purpose[kw.start():]
    m = FV_RS.search(clause) or FV_FROM.search(clause)
    if not m:
        return None, "no_fv_pair_in_clause"
    old_fv, new_fv = float(m.group(1)), float(m.group(2))
    if old_fv <= 0 or new_fv <= 0:
        return None, "zero_face_value"
    if old_fv == new_fv:
        return None, "degenerate_equal_face_value"
    return (old_fv, new_fv), None


def parse_bonus_clause(purpose):
    """(new, held) from 'Bonus a:b', or (None, reason). (None, None) = no bonus."""
    if not BONUS_KW.search(purpose):
        return None, None
    if NON_EQUITY_BONUS.search(purpose):
        return None, "non_equity_bonus"
    m = BONUS_RATIO.search(purpose)
    if not m:
        return None, "no_bonus_ratio"
    new, held = int(m.group(1)), int(m.group(2))
    if new <= 0 or held <= 0:
        return None, "zero_bonus_ratio"
    return (new, held), None


def parse_nse_cf_ca():
    """Split and bonus legs from every CF-CA record. Both legs of a combined
    action come from the same PURPOSE string and share its ex-date."""
    events, factors, rejects = [], [], []
    for fp in sorted(RAW_DIR.glob("CF-CA-equities-*.csv")):
        source = f"NSE_CF-CA_{fp.name}"
        text = fp.read_bytes().decode("utf-8-sig")
        for row in csv.DictReader(io.StringIO(text)):
            purpose = (row.get("PURPOSE") or "").strip()
            symbol = (row.get("SYMBOL") or "").strip().upper()
            try:
                ex_date = datetime.strptime(
                    (row.get("EX-DATE") or "").strip(), "%d-%b-%Y").date()
            except ValueError:
                continue
            raw_json = json.dumps(row, default=str)[:4000]

            if SPLIT_KW.search(purpose) or CAP_REDUCTION.search(purpose):
                fv, reason = parse_split_clause(purpose)
                if fv:
                    old_fv, new_fv = fv
                    events.append({
                        "symbol": symbol, "ex_date": ex_date,
                        "action_type": "SPLIT", "purpose_raw": purpose,
                        "ratio_or_fv": f"{old_fv:g}/{new_fv:g}",
                        "source": source, "scripcode": "", "raw_json": raw_json,
                    })
                    factors.append({
                        "symbol": symbol, "ex_date": ex_date,
                        "factor": new_fv / old_fv,
                        "action_type": "SPLIT", "source": source,
                    })
                elif reason != "no_split_clause":
                    rejects.append({
                        "symbol": symbol, "ex_date": ex_date,
                        "action_type": "SPLIT", "reason": reason,
                        "purpose_raw": purpose, "source": source,
                    })

            bonus, reason = parse_bonus_clause(purpose)
            if bonus:
                new, held = bonus
                events.append({
                    "symbol": symbol, "ex_date": ex_date,
                    "action_type": "BONUS", "purpose_raw": purpose,
                    "ratio_or_fv": f"{new}:{held}",
                    "source": source, "scripcode": "", "raw_json": raw_json,
                })
                factors.append({
                    "symbol": symbol, "ex_date": ex_date,
                    "factor": held / (new + held),
                    "action_type": "BONUS", "source": source,
                })
            elif reason:
                rejects.append({
                    "symbol": symbol, "ex_date": ex_date,
                    "action_type": "BONUS", "reason": reason,
                    "purpose_raw": purpose, "source": source,
                })
    return events, factors, rejects


def build_rename_backmap(con):
    """new_symbol -> [(old_symbol, effective_dt)], from gate (a)'s symbol_changes."""
    back = {}
    for old, new, eff in con.execute(
            "SELECT old_symbol, new_symbol, effective_dt FROM symbol_changes "
            "WHERE effective_dt IS NOT NULL").fetchall():
        back.setdefault(new.upper(), []).append((old.upper(), eff))
    return back


def resolve_symbol_at_ex_date(con, symbol, ex_date, back, traded):
    """The CF-CA feed files every historical event under the symbol's *current*
    name: BAJAJCON carries BAJAJCORP's 2011 split. Walk the rename chain back to
    the name in force on the ex-date, and pick the first candidate that actually
    traded then."""
    chain, cur, seen = [symbol], symbol, {symbol}
    while True:
        candidates = [(old, eff) for old, eff in back.get(cur, []) if eff > ex_date]
        if not candidates:
            break
        old = min(candidates, key=lambda c: c[1])[0]
        if old in seen:
            break
        seen.add(old)
        chain.append(old)
        cur = old
    if len(chain) == 1:
        return symbol
    for candidate in reversed(chain):
        key = (candidate, ex_date)
        if key not in traded:
            traded[key] = con.execute(
                "SELECT 1 FROM equity_bhavcopy WHERE symbol = ? AND trade_date "
                "BETWEEN ? - INTERVAL 10 DAY AND ? + INTERVAL 10 DAY LIMIT 1",
                [candidate, ex_date, ex_date]).fetchone() is not None
        if traded[key]:
            return candidate
    return symbol


def _parse_bse_date(val):
    if val is None:
        return None
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except (ValueError, OverflowError):
            pass
    return None


def _to_str(*args):
    for v in args:
        if v is not None and v != "":
            return str(v)
    return ""


def parse_bse_dividends(scripcode, symbol, raw):
    """Dividends only. BSE bonus records are keyed on the record date and are
    superseded by the CF-CA feed."""
    if raw is None:
        return []
    rows = []
    for d in (raw.get("Table2") or []):
        dt = _parse_bse_date(d.get("Ex_date") or d.get("BCRD"))
        if dt is None:
            continue
        rows.append({
            "symbol": symbol, "ex_date": dt, "action_type": "DIVIDEND",
            "purpose_raw": _to_str(d.get("purpose") or d.get("purpose_name")),
            "ratio_or_fv": _to_str(d.get("Details") or d.get("Amount")),
            "source": f"BSE_{scripcode}", "scripcode": scripcode,
            "raw_json": json.dumps(d, default=str)[:4000],
        })
    seen = {(r["symbol"], r["ex_date"], r["purpose_raw"]) for r in rows}
    for d in (raw.get("Table") or []):
        dt = _parse_bse_date(d.get("BCRD_from") or d.get("BCRD_FROM")
                             or d.get("Ex_date"))
        if dt is None:
            continue
        purpose = _to_str(d.get("purpose_name") or d.get("purpose"))
        if (symbol, dt, purpose) in seen:
            continue
        rows.append({
            "symbol": symbol, "ex_date": dt, "action_type": "DIVIDEND",
            "purpose_raw": purpose, "ratio_or_fv": _to_str(d.get("Amount")),
            "source": f"BSE_{scripcode}", "scripcode": scripcode,
            "raw_json": json.dumps(d, default=str)[:4000],
        })
    return rows


def purge_and_rebuild(con):
    os.makedirs(RAW_DIR, exist_ok=True)
    con.execute(SCHEMA_SQL)
    con.execute("DELETE FROM corporate_actions")
    con.execute("DELETE FROM adjustment_factors")
    con.execute("DELETE FROM ca_parse_rejects")
    con.execute("DELETE FROM ca_evidence_exceptions")

    con.execute("DELETE FROM ca_scope_exclusions")
    df_excl = pd.DataFrame([
        {"symbol": s, "move_date": d, "reason": r,
         "detail": EXCLUSION_DETAIL[r], "carried_to": "gate_c"}
        for s, d, r in SCOPE_EXCLUSIONS])
    con.execute("INSERT INTO ca_scope_exclusions SELECT symbol, move_date, reason, "
                "detail, carried_to FROM df_excl")
    print(f"Scope exclusions       : {len(SCOPE_EXCLUSIONS)} moves carried to gate (c)")

    store_syms = {r[0] for r in con.execute(
        "SELECT DISTINCT symbol FROM equity_bhavcopy WHERE series='EQ'").fetchall()}

    div_events = []
    for p in sorted(RAW_DIR.glob("bse_ca_*.json")):
        code = p.stem.replace("bse_ca_", "")
        data = json.loads(p.read_bytes())
        if not any(isinstance(v, list) and v for v in data.values()):
            continue
        sym = None
        for tbl in ("Table1", "Table2", "Table"):
            entries = data.get(tbl, [])
            if entries:
                s = entries[0].get("short_name") or entries[0].get("scrip_id")
                if s:
                    sym = s.upper()
                    break
        if sym is None or sym not in store_syms:
            continue
        div_events.extend(parse_bse_dividends(code, sym, data))

    nse_events, nse_factors, rejects = parse_nse_cf_ca()

    back, traded, n_remapped = build_rename_backmap(con), {}, 0
    for record in nse_events + nse_factors:
        resolved = resolve_symbol_at_ex_date(
            con, record["symbol"], record["ex_date"], back, traded)
        if resolved != record["symbol"]:
            record["symbol"] = resolved
            n_remapped += 1
    print(f"Rename-remapped        : {n_remapped} records to the symbol in force "
          f"at their ex-date")

    df_ev = pd.DataFrame(div_events + nse_events).drop_duplicates(
        subset=["symbol", "ex_date", "action_type", "ratio_or_fv"])
    con.execute("INSERT INTO corporate_actions SELECT symbol, ex_date, "
                "action_type, purpose_raw, ratio_or_fv, source, scripcode, "
                "raw_json FROM df_ev")

    df_fac = pd.DataFrame(nse_factors).drop_duplicates(
        subset=["symbol", "ex_date", "action_type"])
    con.execute("INSERT INTO adjustment_factors SELECT symbol, ex_date, factor, "
                "action_type, source FROM df_fac")

    print(f"BSE dividend events    : {len(div_events):,}")
    print(f"NSE CF-CA events       : {len(nse_events):,}")
    print(f"NSE CF-CA factors      : {len(df_fac):,}")
    print(f"Parse rejects          : {len(rejects):,}")
    if rejects:
        df_rej = pd.DataFrame(rejects)
        con.execute("INSERT INTO ca_parse_rejects SELECT symbol, ex_date, "
                    "action_type, reason, purpose_raw, source FROM df_rej")
        for reason, n in df_rej.groupby("reason").size().items():
            print(f"    {reason:<32} {n}")
    return len(df_ev), len(df_fac), len(rejects)


def ingest_etf_splits(con):
    df_ev = pd.DataFrame([{
        "symbol": s, "ex_date": d, "action_type": "SPLIT",
        "purpose_raw": f"Gold ETF unit sub-division: FV {o} -> {n} ({note})",
        "ratio_or_fv": f"{o}/{n}",
        "source": f"ETF_AMC_notice_{d.isoformat()}_{s}",
        "scripcode": "", "raw_json": "{}",
    } for s, d, o, n, note in ETF_SPLITS])
    con.execute("INSERT INTO corporate_actions SELECT symbol, ex_date, "
                "action_type, purpose_raw, ratio_or_fv, source, scripcode, "
                "raw_json FROM df_ev")
    df_f = pd.DataFrame([{
        "symbol": s, "ex_date": d, "factor": n / o, "action_type": "SPLIT",
        "source": f"ETF_AMC_notice_{d.isoformat()}_{s}",
    } for s, d, o, n, _ in ETF_SPLITS])
    con.execute("INSERT OR REPLACE INTO adjustment_factors SELECT symbol, "
                "ex_date, factor, action_type, source FROM df_f")
    print(f"ETF split factors      : {len(ETF_SPLITS)}")
    return len(ETF_SPLITS)


def ingest_special_dividends(con):
    divs = con.execute("""
        SELECT symbol, ex_date, ratio_or_fv FROM corporate_actions
        WHERE action_type = 'DIVIDEND' AND ratio_or_fv NOT IN ('', '0')
    """).fetchall()
    n_unparseable = n_no_prior = n_below_threshold = n_exceeds_price = 0
    new_factors = []
    for sym, dt, amt_str in divs:
        try:
            amt = float(amt_str)
        except ValueError:
            n_unparseable += 1
            continue
        if amt <= 0:
            n_unparseable += 1
            continue
        prior = con.execute("""
            SELECT e.close FROM equity_bhavcopy e
            JOIN trading_calendar tc ON e.trade_date = tc.trade_date
                AND tc.n_symbols >= 200
            WHERE e.symbol = ? AND e.series = 'EQ' AND e.trade_date < ?
            ORDER BY e.trade_date DESC LIMIT 1
        """, [sym, dt]).fetchone()
        if not prior or not prior[0] or prior[0] <= 0:
            n_no_prior += 1
            continue
        prior_close = prior[0]
        if amt < SPECIAL_DIV_THRESHOLD * prior_close:
            n_below_threshold += 1
            continue
        if amt >= prior_close:
            n_exceeds_price += 1
            continue
        new_factors.append({
            "symbol": sym, "ex_date": dt,
            "factor": (prior_close - amt) / prior_close,
            "action_type": "SPECIAL_DIVIDEND",
            "source": f"bhavcopy_prior_close_{prior_close:.2f}_div_{amt:.2f}",
        })
    n_kept = 0
    if new_factors:
        df = pd.DataFrame(new_factors).drop_duplicates(
            subset=["symbol", "ex_date", "action_type"])
        con.execute("INSERT OR REPLACE INTO adjustment_factors SELECT symbol, "
                    "ex_date, factor, action_type, source FROM df")
        n_kept = len(df)
    print(f"Special dividends      : {n_kept} factors from {len(divs):,} rows")
    print(f"    amount unparseable   {n_unparseable:,}")
    print(f"    no prior close       {n_no_prior:,}")
    print(f"    below {SPECIAL_DIV_THRESHOLD:.0%} threshold  {n_below_threshold:,}")
    print(f"    amount >= price      {n_exceeds_price:,}")
    return n_kept


def build_adjusted_view(con):
    """Backward adjustment at the TIME-AWARE ENTITY grain.

    Prompt 2 (2026-07-13): entity-level cumulative factors fixed the rename discontinuity
    (59 entities) — a factor keyed to the post-rename symbol must reach the pre-rename prints
    of the *same entity*.

    Prompt 3 (2026-07-14): entity is resolved by `(symbol, trade_date)` through
    `symbol_entity_intervals` (half-open `[valid_from, valid_to)`, built by build_universe.py),
    not a time-agnostic symbol->entity map. This stops a *recycled* ticker (DTIL, relisted after
    its 2010 rename vacated the name) from being merged with the chain it left — which under
    Prompt 2 both applied one company's factor across another's history and fabricated a +50%
    `prev_close` gap via the same-date `LAG` reach-across. Intervals cover every
    `(symbol, trade_date)` in equity_bhavcopy exactly once, so the join neither drops nor
    duplicates a print.

    Ex-date consistency: `prev_close(t) = close(t-1)`, so `adj_prev_close(t)` must equal
    `adj_close(t-1)`. A `LAG` by `entity, series` retrieves the equal value at a genuine rename
    (no ex-date, cum unchanged); with time-aware entities it can no longer reach a co-trading
    different company's same-date row.
    """
    con.execute("""
CREATE OR REPLACE VIEW equity_bhavcopy_adjusted AS
WITH events AS (
    SELECT i.entity, af.ex_date,
           COALESCE(EXP(SUM(LN(af.factor)) FILTER (
               WHERE af.action_type IN ('BONUS','SPLIT','SPECIAL_DIVIDEND'))), 1.0)
               AS price_factor,
           COALESCE(EXP(SUM(LN(af.factor)) FILTER (
               WHERE af.action_type IN ('BONUS','SPLIT'))), 1.0) AS vol_factor
    FROM adjustment_factors af
    JOIN symbol_entity_intervals i ON i.symbol = af.symbol
         AND af.ex_date >= i.valid_from AND af.ex_date < i.valid_to
    GROUP BY i.entity, af.ex_date
),
cum AS (
    SELECT entity, ex_date,
           EXP(SUM(LN(price_factor)) OVER (
               PARTITION BY entity ORDER BY ex_date DESC
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)) AS cum_price,
           EXP(SUM(LN(vol_factor)) OVER (
               PARTITION BY entity ORDER BY ex_date DESC
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)) AS cum_vol
    FROM events
),
joined AS (
    SELECT e.trade_date, e.symbol, e.series, e.open, e.high, e.low, e.close,
           e.prev_close, e.volume, e.turnover, e.deliv_qty, e.deliv_pct,
           i.entity,
           COALESCE(c.cum_price, 1.0) AS cum_price,
           COALESCE(c.cum_vol, 1.0) AS cum_vol
    FROM equity_bhavcopy e
    JOIN symbol_entity_intervals i ON i.symbol = e.symbol
         AND e.trade_date >= i.valid_from AND e.trade_date < i.valid_to
    LEFT JOIN cum c ON c.entity = i.entity AND c.ex_date = (
        SELECT MIN(x.ex_date) FROM events x
        WHERE x.entity = i.entity AND x.ex_date > e.trade_date)
)
SELECT
    trade_date, symbol, series,
    open  * cum_price AS open,
    high  * cum_price AS high,
    low   * cum_price AS low,
    close * cum_price AS close,
    prev_close * COALESCE(
        LAG(cum_price) OVER (PARTITION BY entity, series ORDER BY trade_date, symbol),
        cum_price) AS prev_close,
    volume / NULLIF(cum_vol, 0) AS volume,
    turnover, deliv_qty, deliv_pct
FROM joined
""")


def record_evidence_exceptions(con):
    """Screen every ex-date's compounded factor against the market's own repricing.

    Prices come from the EQ+BE union: a symbol moved to BE trades every session, and
    an EQ-only lookup would compare prints years apart. The two prints must be
    adjacent sessions — a genuinely suspended symbol has no evidence, and comparing
    prints 85 days apart manufactures 'gaps' no circuit band permits.

    The adjustment lands at the open; the close is the official settlement price.
    A factor reconciles if either agrees within tolerance — demanding both fails on
    thin opens, demanding only the close fails on circuit-band days."""
    rows = con.execute(f"""
        WITH eqbe AS (
            SELECT trade_date, symbol, open, close,
                   ROW_NUMBER() OVER (PARTITION BY symbol, trade_date
                       ORDER BY CASE series WHEN 'EQ' THEN 0 ELSE 1 END) AS rn
            FROM equity_bhavcopy WHERE series IN ('EQ', 'BE')
        ),
        px AS (SELECT trade_date, symbol, open, close FROM eqbe WHERE rn = 1),
        events AS (
            SELECT symbol, ex_date, EXP(SUM(LN(factor))) AS f,
                   STRING_AGG(action_type || '=' || ROUND(factor, 6), ' * ') AS legs
            FROM adjustment_factors GROUP BY symbol, ex_date
        )
        SELECT v.symbol, v.ex_date, v.legs, v.f,
               o.open / p.close AS implied_open,
               o.close / p.close AS implied_close
        FROM events v
        LEFT JOIN LATERAL (
            SELECT trade_date, open, close FROM px
            WHERE px.symbol = v.symbol AND px.trade_date >= v.ex_date
            ORDER BY px.trade_date LIMIT 1) o ON TRUE
        LEFT JOIN LATERAL (
            SELECT trade_date, close FROM px
            WHERE px.symbol = v.symbol AND px.trade_date < v.ex_date
            ORDER BY px.trade_date DESC LIMIT 1) p ON TRUE
        WHERE o.open IS NOT NULL AND p.close > 0
          AND (o.trade_date - p.trade_date) <= {EVIDENCE_MAX_GAP_DAYS}
    """).fetchall()

    n_events = con.execute(
        "SELECT COUNT(DISTINCT (symbol, ex_date)) FROM adjustment_factors").fetchone()[0]
    exceptions = []
    for sym, ex, legs, f, imp_open, imp_close in rows:
        devs = [abs(f - i) / i for i in (imp_open, imp_close)
                if i is not None and i > 0]
        if not devs:
            continue
        if min(devs) > EVIDENCE_TOLERANCE:
            exceptions.append({
                "symbol": sym, "ex_date": ex, "legs": legs,
                "stored_factor": f, "implied_open": imp_open,
                "implied_close": imp_close, "deviation": min(devs),
            })
    if exceptions:
        df = pd.DataFrame(exceptions)
        con.execute("INSERT INTO ca_evidence_exceptions SELECT symbol, ex_date, "
                    "legs, stored_factor, implied_open, implied_close, "
                    "deviation FROM df")
    print(f"Evidence screen        : {len(rows):,} of {n_events:,} ex-dates have "
          f"adjacent-session evidence; {len(exceptions)} beyond "
          f"{EVIDENCE_TOLERANCE:.0%}")
    return len(rows), len(exceptions), n_events


def main():
    con = duckdb.connect(str(DB_PATH))
    n_events, n_factors, n_rejects = purge_and_rebuild(con)
    ingest_etf_splits(con)
    ingest_special_dividends(con)
    build_adjusted_view(con)
    n_tested, n_exceptions, n_ex_dates = record_evidence_exceptions(con)
    con.close()

    print()
    print("=" * 56)
    print("REBUILD SUMMARY")
    print("=" * 56)
    print(f"Events              : {n_events:,}")
    print(f"Factors             : {n_factors:,}")
    print(f"Parse rejects       : {n_rejects:,}")
    print(f"Ex-dates            : {n_ex_dates:,}")
    print(f"…with evidence      : {n_tested:,}")
    print(f"Evidence failures   : {n_exceptions:,}")


if __name__ == "__main__":
    main()
