#!/usr/bin/env python3
"""SE-1 counting pass — enumerate Nifty 50 / Nifty Next 50 constituent-change
events from the monthly MCWB archives, entity-resolve them, classify them, and
run the effective-breadth power arithmetic.

This is a counting exercise. It reads no price, return, OHLCV, futures, or
options data; it computes no return, abnormal or otherwise, and takes no
position on whether any effect exists. Its output feeds an RFA declaration for
SE-1 (or forces the dossier's ranking to be rewritten) — it is not itself an
RFA declaration.

Resolution limit (disclosed up front, from the prompt): MCWB is monthly.
Diffing consecutive months yields the event list and a month-resolution
effective window. It does NOT yield the announcement date — announcement-vs-
effective is the entire mechanism of SE-1. MCWB enumerates events; it never
timestamps them. Where an announcement date cannot be sourced it is recorded
as UNKNOWN, never imputed, never substituted with the effective date.

Usage:
    python scripts/se1/count_index_events.py

Outputs:
    data/se1/nifty50_change_events.json      — itemised event register (committed)
    data/se1/niftynext50_change_events.json  — same, for Nifty Next 50
    console summary + the clustering and power arithmetic the report needs
"""

import json
import sys
import zipfile
from calendar import monthrange
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

REF_DIR = ROOT / "data" / "reference"
MANIFEST_PATH = REF_DIR / "mcwb_manifest.json"
EQUITY_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
# Committed output (data/ and reference/ are gitignored; the register must be
# tracked). Same pattern as scripts/psb1/disposition_register.py.
OUT_DIR = ROOT / "scripts" / "se1" / "registers"

INDEXES = [
    ("nifty50", "nifty50_mcwb.csv", "Nifty 50"),
    ("niftynext50", "niftynext50_mcwb.csv", "Nifty Next 50"),
]

# NSE's own test/placeholder rows found inside the official MCWB archives
# (verified 2026-08-04 against the raw CSVs): DUMMYREL in mcwb_jul23,
# DUMMYTATAM in mcwb_oct25, DUMMYHDLVR in mcwb_dec25/mcwb_jan26. They are not
# securities; they fabricate spurious add/drop events. Excluded by name — this
# is source-pollution removal, not interpolation.
DUMMY_SYMBOLS = {"DUMMYREL", "DUMMYTATAM", "DUMMYHDLVR"}


def load_valid_months() -> list:
    """Chronological list of valid MCWB archive records (dicts)."""
    manifest = json.load(open(MANIFEST_PATH, encoding="utf-8"))
    valid = [r for r in manifest["records"] if r["status"] == "valid"]
    valid.sort(key=lambda r: r["month"])
    return valid


def month_symbols(rec, csv_name) -> set:
    """Parse the Security Symbol column of one MCWB CSV, excluding NSE's own
    test rows (DUMMY_SYMBOLS)."""
    with zipfile.ZipFile(REF_DIR / rec["filename"]) as zf:
        raw = zf.read(csv_name).decode("utf-8", errors="replace")
    syms = set()
    for line in raw.splitlines():
        if "Sr. No" in line:
            continue
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < 2 or not parts[0].strip().isdigit():
            continue
        s = parts[1].strip().upper()
        if s and s not in DUMMY_SYMBOLS:
            syms.add(s)
    return syms


def month_end(m: str) -> date:
    """The MCWB report is a month-end snapshot; resolve symbols at month-end."""
    y, mo = int(m[:4]), int(m[5:7])
    return date(y, mo, monthrange(y, mo)[1])


def build_resolver(con):
    """Return resolve(symbol, month_date) -> (entity, method).

    Primary: symbol_entity_intervals (entity in force at the month).
    Fallback: ISIN issuer prefix (INE first 9 chars).
    Final fallback: the raw symbol.
    """
    iv_map = defaultdict(list)
    for sym, vf, vt, ent in con.execute(
        "SELECT symbol, valid_from, valid_to, entity "
        "FROM symbol_entity_intervals"
    ).fetchall():
        iv_map[sym].append((vf, vt, ent))
    isin = dict(con.execute("SELECT symbol, isin FROM symbol_isin").fetchall())

    def resolve(sym, month_date):
        for vf, vt, ent in iv_map.get(sym, []):
            if vf <= month_date < vt:
                return ent, "interval"
        i = isin.get(sym)
        if i and i.startswith("INE"):
            return i[:9], "isin_issuer"
        return sym, "raw"

    return resolve


def raw_diffs(months, symbol_sets):
    """Diffs between consecutive valid months. A missing month breaks the
    chain (the gap fabricates or hides events at both edges — never diff
    across it)."""
    diffs = []
    for m0, m1 in zip(months, months[1:]):
        s0, s1 = symbol_sets[m0["month"]], symbol_sets[m1["month"]]
        adds = s1 - s0
        drops = s0 - s1
        if adds or drops:
            diffs.append({
                "m0": m0["month"],
                "m1": m1["month"],
                "adds": sorted(adds),
                "drops": sorted(drops),
            })
    return diffs


def entity_resolve(diffs, symbol_sets, resolve):
    """Genuine adds/drops at entity grain, with the delta vs raw itemised.

    A raw add/drop is genuine iff its entity was not present in the index
    under ANY ticker in the neighbouring month (so a rename — same entity,
    new ticker — is not a genuine change)."""
    for d in diffs:
        m0 = month_end(d["m0"])
        m1 = month_end(d["m1"])
        ents0 = {resolve(s, m0)[0] for s in symbol_sets[d["m0"]]}
        ents1 = {resolve(s, m1)[0] for s in symbol_sets[d["m1"]]}
        genuine_adds = []
        for s in d["adds"]:
            ent, method = resolve(s, m1)
            if ent not in ents0:
                genuine_adds.append({"symbol": s, "entity": ent, "method": method})
        genuine_drops = []
        for s in d["drops"]:
            ent, method = resolve(s, m0)
            if ent not in ents1:
                genuine_drops.append({"symbol": s, "entity": ent, "method": method})
        d["genuine_adds"] = genuine_adds
        d["genuine_drops"] = genuine_drops
        d["n_raw"] = len(d["adds"]) + len(d["drops"])
        d["n_genuine"] = len(genuine_adds) + len(genuine_drops)
        d["n_artifact"] = d["n_raw"] - d["n_genuine"]
    return diffs


def classify(diffs):
    """scheduled = Nifty semi-annual review boundary; ad-hoc = everything else.

    Month resolution makes the exact review timing ambiguous (a review
    effective end-March surfaces in the March or the April snapshot depending
    on the archive's cut date), so the proxy is: a change first appearing in a
    March / April / September / October snapshot is scheduled; anything else is
    ad-hoc (M&A, suspension, fast-track demerger add). Disclosed, not precise.
    """
    for d in diffs:
        for e in d["genuine_adds"] + d["genuine_drops"]:
            e["m1"] = d["m1"]
            e["kind"] = "scheduled" if d["m1"][5:7] in ("03", "04", "09", "10") else "ad_hoc"
    return diffs


def flatten_events(diffs):
    out = []
    for d in diffs:
        for e in d["genuine_adds"]:
            out.append({
                "index": None,  # set by caller
                "effective_month": d["m1"],
                "direction": "add",
                "symbol": e["symbol"],
                "entity": e["entity"],
                "resolution": e["method"],
                "kind": e["kind"],
                "announcement_date": "UNKNOWN",
                "announcement_source": None,
            })
        for e in d["genuine_drops"]:
            out.append({
                "index": None,
                "effective_month": d["m1"],
                "direction": "drop",
                "symbol": e["symbol"],
                "entity": e["entity"],
                "resolution": e["method"],
                "kind": e["kind"],
                "announcement_date": "UNKNOWN",
                "announcement_source": None,
            })
    return out


def apply_announcements(events, supplemental: dict):
    """Apply externally-sourced announcement dates keyed by
    "index|effective_month|symbol|direction" -> [date, source].
    UNKNOWN stays UNKNOWN; effective dates are never substituted."""
    ann = supplemental.get("announcements", {})
    for e in events:
        key = "|".join((e["index"], e["effective_month"], e["symbol"], e["direction"]))
        if key in ann:
            d, src = ann[key]
            e["announcement_date"] = d
            e["announcement_source"] = src
    return events


def cluster_stats(events):
    """n_nominal, n_clusters, ratio, per-cluster size distribution, span.

    n_clusters is computed two ways:
      - from sourced announcement dates (exact, but only where sourced);
      - structurally, as the number of distinct change-instances (effective
        months). Each scheduled review announces all its names on one date, so
        one review = one cluster; each ad-hoc change-instance is its own
        announcement. This is the operational count at month resolution when
        announcement dates are UNKNOWN.
    """
    ann = [e for e in events if e["announcement_date"] != "UNKNOWN"]
    n_nominal = len(events)
    clusters = defaultdict(list)
    for e in ann:
        clusters[e["announcement_date"]].append(e)
    struct_clusters = defaultdict(list)
    for e in events:
        struct_clusters[e["effective_month"]].append(e)
    cluster_sizes = sorted(len(v) for v in clusters.values())
    struct_sizes = sorted(len(v) for v in struct_clusters.values())
    stats = {
        "n_nominal": n_nominal,
        "n_clusters_sourced": len(clusters),
        "n_clusters_struct": len(struct_clusters),
        "ratio_sourced": round(n_nominal / len(clusters), 3) if clusters else None,
        "ratio_struct": round(n_nominal / len(struct_clusters), 3) if struct_clusters else None,
        "cluster_size_min": cluster_sizes[0] if cluster_sizes else None,
        "cluster_size_median": cluster_sizes[len(cluster_sizes) // 2] if cluster_sizes else None,
        "cluster_size_max": cluster_sizes[-1] if cluster_sizes else None,
        "struct_size_min": struct_sizes[0] if struct_sizes else None,
        "struct_size_median": struct_sizes[len(struct_sizes) // 2] if struct_sizes else None,
        "struct_size_max": struct_sizes[-1] if struct_sizes else None,
        "announcement_coverage": round(len(ann) / len(events), 4) if events else None,
        "announcement_dates": sorted(clusters),
    }
    return stats


def required_delta_over_sd(n, target_power=0.80, two_sided=True):
    """δ/sd required for two-sided power 0.80 at n formations, via the same
    machinery as scripts/rfa/power.py (noncentral t)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from scripts.rfa.power import power_at

    def f(delta_over_sd):
        return power_at(delta_over_sd, sd=1.0, n=n, two_sided=two_sided)

    lo, hi = 0.0, 5.0
    if f(hi) < target_power:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) >= target_power:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2, 4)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    months = load_valid_months()
    covered = f"{months[0]['month']} .. {months[-1]['month']}"
    missing = [m["month"] for m in json.load(open(MANIFEST_PATH, encoding="utf-8"))["records"]
               if m["status"] != "valid"]

    con = duckdb.connect(str(EQUITY_DB), read_only=True)
    resolve = build_resolver(con)

    supplemental = {}
    sup_path = OUT_DIR / "announcement_dates.json"
    if sup_path.exists():
        supplemental = json.load(open(sup_path, encoding="utf-8"))

    summary = {"covered_span": covered, "missing_months": missing}
    for index_key, csv_name, label in INDEXES:
        symbol_sets = {m["month"]: month_symbols(m, csv_name) for m in months}
        diffs = raw_diffs(months, symbol_sets)
        diffs = entity_resolve(diffs, symbol_sets, resolve)
        diffs = classify(diffs)
        events = flatten_events(diffs)
        for e in events:
            e["index"] = index_key
        events = apply_announcements(events, supplemental)

        stats = cluster_stats(events)
        n_nominal = stats["n_nominal"]
        n_clusters_sourced = stats["n_clusters_sourced"]
        n_clusters_struct = stats["n_clusters_struct"]
        required = {
            "n_nominal": required_delta_over_sd(n_nominal) if n_nominal else None,
            "n_clusters_sourced": (
                required_delta_over_sd(n_clusters_sourced) if n_clusters_sourced else None
            ),
            "n_clusters_struct": (
                required_delta_over_sd(n_clusters_struct) if n_clusters_struct else None
            ),
        }
        out = {
            "index": index_key,
            "label": label,
            "covered_span": covered,
            "missing_months": missing,
            "raw_diff_count": sum(d["n_raw"] for d in diffs),
            "artifact_count": sum(d["n_artifact"] for d in diffs),
            "genuine_event_count": n_nominal,
            "scheduled_count": sum(1 for e in events if e["kind"] == "scheduled"),
            "ad_hoc_count": sum(1 for e in events if e["kind"] == "ad_hoc"),
            "clusters": stats,
            "required_delta_over_sd": required,
            "events": events,
        }
        (OUT_DIR / f"{index_key}_change_events.json").write_text(
            json.dumps(out, indent=2), encoding="utf-8")

        print(f"===== {label} ({index_key}) =====")
        print(f"  covered: {covered}  missing: {missing}")
        print(f"  raw diffs: {out['raw_diff_count']}  artifacts (delta): {out['artifact_count']}  "
              f"genuine events: {n_nominal}  "
              f"(scheduled {out['scheduled_count']} / ad-hoc {out['ad_hoc_count']})")
        print(f"  n_nominal={n_nominal}  n_clusters_struct={n_clusters_struct}  "
              f"ratio_struct={stats['ratio_struct']}  "
              f"announcement_coverage={stats['announcement_coverage']}")
        print(f"  required delta/sd @0.80 (two-sided): "
              f"n_nominal={required['n_nominal']}  "
              f"n_clusters_struct={required['n_clusters_struct']}")

    con.close()
    print(f"\nregisters written to {OUT_DIR}")


if __name__ == "__main__":
    main()
