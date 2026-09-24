"""PTMS Gann Stage-1 — P-2 external corporate-action enumeration (metadata only).

Enumerates the corporate actions of every NIFTY 100 point-in-time member entity over the
Stage-1 screen window from NSE's own CF-CA equities feed (the exchange record), and classifies
each by its PURPOSE text so the G-7 full-span exclusion rule can be applied at freeze.

Reads CA metadata and membership/entity mappings only. It reads no price, return or outcome.

Inputs (read-only):
  data/market_data/corporate_actions_raw/CF-CA-equities-*.csv   NSE CF-CA feed
  data/isd/n100_membership.duckdb:n100_membership                PIT membership intervals
  data/market_data/equity_bhavcopy.duckdb:symbol_entity_intervals time-aware symbol -> entity

Outputs:
  docs/reports/ptms/PTMS_GANN_P2_CA_EVENTS_<date>.csv   every classified event (one row per
                                                        entity, ex-date and class)
  docs/reports/ptms/PTMS_GANN_P2_CA_ENUMERATION_<date>.md  report with provenance hashes

Usage:
    python scripts/ptms/enumerate_nonratio_ca.py
"""

import csv
import glob
import hashlib
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
RAW_GLOB = str(ROOT / "data" / "market_data" / "corporate_actions_raw" / "CF-CA-equities-*.csv")
N100_DB = ROOT / "data" / "isd" / "n100_membership.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
OUT_DIR = ROOT / "docs" / "reports" / "ptms"
RUN_DATE = "2026-09-19"

WINDOW_START = date(2011, 3, 25)
WINDOW_END = date(2022, 12, 30)
# Equity series only. Debt series (e.g. IDFC tax-free bonds H1..HE) carry the issuer's symbol and
# would add spurious event dates (IDFC "Demerger" on its bond series 2015-09-29 vs EQ 2015-10-01).
EQUITY_SERIES = {"EQ", "BE", "BZ"}

# Ordered (class, pattern). A purpose may carry several classes ("AGM/Dividend/Special Dividend").
_IN_KIND = r"debenture|\bccds?\b|preference share"
CLASS_PATTERNS = [
    ("DEMERGER", r"de-?merger|spin[\s-]?off"),
    ("SCHEME", r"scheme of ar+angement|amalgamation"),
    ("IN_KIND", _IN_KIND),
    ("RIGHTS", r"\brights?\b"),
    ("SPECIAL_DIVIDEND", r"special|\bspl\b|one time"),
    ("BUYBACK", r"buy[\s-]?back"),
]
_RATIO = r"(bonus(?!\s*(debenture|preference))|split|splt|sub-division|consolidation)"

# Classes that are G-7 (non-ratio) events. R-13 named spin-offs, schemes, rights and special
# dividends; the operator ruled IN_KIND non-ratio and BUYBACK not non-ratio (2026-09-19,
# PTMS_GANN_OPERATOR_RULINGS_2026-09-19.md, P-2 addendum).
G7_CLASSES = {"DEMERGER", "SCHEME", "RIGHTS", "SPECIAL_DIVIDEND", "IN_KIND"}


def classify_purpose(purpose):
    p = purpose.lower()
    classes = {name for name, pat in CLASS_PATTERNS if re.search(pat, p)}
    if "IN_KIND" not in classes and re.search(_RATIO, p):
        classes.add("RATIO")
    return classes


def entity_at(intervals, symbol, day):
    for sym, valid_from, valid_to, entity in intervals:
        if sym == symbol and valid_from <= day <= valid_to:
            return entity
    return None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_inputs():
    con = duckdb.connect(str(N100_DB), read_only=True)
    membership = con.execute(
        "SELECT symbol, valid_from, COALESCE(valid_to, DATE '9999-12-31') FROM n100_membership "
        "WHERE valid_from <= ? AND COALESCE(valid_to, DATE '9999-12-31') >= ?",
        [WINDOW_END, WINDOW_START],
    ).fetchall()
    con.close()
    con = duckdb.connect(str(EQ_DB), read_only=True)
    intervals = con.execute("SELECT symbol, valid_from, valid_to, entity FROM symbol_entity_intervals").fetchall()
    con.close()
    return membership, intervals


def member_entities(membership, intervals):
    entities, member_spans, unmapped = set(), {}, []
    for symbol, valid_from, valid_to in membership:
        entity = entity_at(intervals, symbol, valid_from) or entity_at(intervals, symbol, min(valid_to, WINDOW_END))
        if entity is None:
            unmapped.append(symbol)
            continue
        entities.add(entity)
        member_spans.setdefault(entity, []).append((valid_from, valid_to))
    if unmapped:
        raise SystemExit(f"Unmapped membership symbols (fix symbol_entity_intervals first): {unmapped}")
    return entities, member_spans


def read_feed(entities, intervals):
    events, files, unparsed, non_equity = [], [], 0, 0
    for path in sorted(glob.glob(RAW_GLOB)):
        files.append((Path(path).name, _sha256(path)))
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    ex_date = datetime.strptime(row["EX-DATE"].strip(), "%d-%b-%Y").date()
                except ValueError:
                    unparsed += 1
                    continue
                if not WINDOW_START <= ex_date <= WINDOW_END:
                    continue
                entity = entity_at(intervals, row["SYMBOL"].strip(), ex_date)
                if entity in entities and row["SERIES"].strip() not in EQUITY_SERIES:
                    non_equity += 1
                elif entity in entities:
                    events.append((entity, row["SYMBOL"].strip(), ex_date, row["SERIES"].strip(),
                                   row["PURPOSE"].strip(), Path(path).name))
    return events, files, unparsed, non_equity


def classify_events(events, member_spans):
    rows = {}
    for entity, symbol, ex_date, series, purpose, source in events:
        for cls in classify_purpose(purpose):
            if cls == "RATIO":
                continue
            key = (entity, ex_date, cls)
            in_membership = any(f <= ex_date <= t for f, t in member_spans[entity])
            if key not in rows:
                rows[key] = [entity, symbol, ex_date.isoformat(), cls, series, purpose, source, in_membership,
                             cls in G7_CLASSES]
            elif purpose not in rows[key][5]:
                rows[key][5] += " || " + purpose
    return sorted(rows.values(), key=lambda r: (r[2], r[0], r[3]))


def write_outputs(rows, files, unparsed, non_equity, n_entities, n_events):
    csv_path = OUT_DIR / f"PTMS_GANN_P2_CA_EVENTS_{RUN_DATE}.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["entity", "symbol", "ex_date", "class", "series", "purpose", "source_file", "in_membership",
                    "g7_event"])
        w.writerows(rows)

    by_class = Counter(r[3] for r in rows)
    md = [
        f"# PTMS — Gann P-2 Corporate-Action Enumeration ({RUN_DATE})",
        "",
        "**Script-generated by `scripts/ptms/enumerate_nonratio_ca.py`. Do not hand-edit.**",
        "",
        "- **Source:** NSE CF-CA equities feed (the exchange's own corporate-action record), raw files below.",
        "- **Scope:** every NIFTY 100 point-in-time member entity (time-aware symbol → entity), ex-dates "
        f"{WINDOW_START} → {WINDOW_END}.",
        "- Metadata only: no price, return or outcome was read.",
        "",
        f"- Member entities: **{n_entities}**. Feed rows for member entities in the window: **{n_events}**.",
        f"- Feed rows with an unparseable EX-DATE (all files, skipped): **{unparsed}**.",
        f"- Member-entity rows on non-equity series (debt series, excluded): **{non_equity}**.",
        "",
        "## Classified events (ratio events and ordinary dividends excluded)",
        "",
        "| Class | Events | G-7 status |",
        "|---|--:|---|",
    ]
    for cls in ["DEMERGER", "SCHEME", "RIGHTS", "SPECIAL_DIVIDEND", "IN_KIND", "BUYBACK"]:
        status = "**G-7 event** (non-ratio)" if cls in G7_CLASSES else "Not a G-7 event (operator ruling 2026-09-19)"
        md.append(f"| {cls} | {by_class.get(cls, 0)} | {status} |")
    md += [
        "",
        "## Classification notes",
        "",
        "- Classification is by PURPOSE text only. **Special dividends are those the exchange labels "
        "special**; no size screen is applied, because a size screen needs prices, which P-2 excludes.",
        "- One feed row can carry two classes. \"Scheme of Arrangement – Bonus Debentures\" (NTPC 2015, "
        "BRITANNIA 2019/2021) is both SCHEME and IN_KIND. Its G-7 status therefore follows whichever "
        "class is non-ratio; both are (IN_KIND ruled non-ratio 2026-09-19).",
        "- `in_membership = no` rows are still in scope. G-7 excludes any observation whose dependency "
        "span contains the ex-date, and spans can reach back before a membership start.",
        "- Buybacks are listed for completeness but are **not** G-7 events (operator ruling 2026-09-19).",
        "- Single source, **accepted by the operator 2026-09-19**: the NSE feed is the exchange's own record. The BSE cache in the same "
        "directory is a shallow per-scrip summary (the latest few actions) and cannot cross-check "
        "2011–2022.",
    ]
    g7_dates = {(r[0], r[2]) for r in rows if r[8]}
    md += ["", f"**Distinct (entity, ex-date) G-7 events: {len(g7_dates)}** — the input to the G-7 exclusion.",
           "", "## Event list", "",
           "| Ex-date | Entity | Symbol | Class | G-7 | In membership | Purpose |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r[2]} | {r[0]} | {r[1]} | {r[3]} | {'yes' if r[8] else 'no'} | {'yes' if r[7] else 'no'} "
                  f"| {r[5].replace('|', '/')} |")
    md += ["", "## Provenance (SHA-256 of every raw file read)", "", "| File | SHA-256 |", "|---|---|"]
    md += [f"| {name} | `{digest}` |" for name, digest in files]
    md.append("")
    (OUT_DIR / f"PTMS_GANN_P2_CA_ENUMERATION_{RUN_DATE}.md").write_text("\n".join(md), encoding="utf-8")
    return csv_path, by_class


def main():
    membership, intervals = load_inputs()
    entities, member_spans = member_entities(membership, intervals)
    events, files, unparsed, non_equity = read_feed(entities, intervals)
    rows = classify_events(events, member_spans)
    csv_path, by_class = write_outputs(rows, files, unparsed, non_equity, len(entities), len(events))
    print(f"entities={len(entities)} feed_rows={len(events)} classified={len(rows)} {dict(by_class)} -> {csv_path}")


if __name__ == "__main__":
    sys.exit(main())
