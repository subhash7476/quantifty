"""G2 v2 — Sector classification for the F&O universe, three-tier approach.

Tier 1: NSE index constituent files (Nifty 500 + sectoral) — sourced, consistent
Tier 2: Entity inheritance via symbol_entity_intervals — time-aware
Tier 3: Minimal manual register for genuinely dead/delisted names

Single vocabulary: NSE's official 20-label macro-sector scheme.
Output carries valid_from/valid_to for time-aware join.

Usage:
    python scripts/g2_ingest_sector_classification.py
"""

import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FUTURES_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
OUTPUT_DIR = ROOT / "governance" / "carry"

# --- Tier 1: Download NSE index constituent files ---

NSE_INDEX_FILES = [
    "ind_nifty500list",
    "ind_niftymidcap150list",
    "ind_niftysmallcap250list",
    "ind_niftybanklist",
    "ind_niftyitlist",
    "ind_niftypharmalist",
    "ind_niftyfmcglist",
    "ind_niftyautolist",
    "ind_niftymetallist",
    "ind_niftymedialist",
    "ind_niftyrealtylist",
    "ind_niftyoilgaslist",
    "ind_niftyhealthcarelist",
    # "ind_niftyconsumerdgoodslist" 404s — the correct NSE name is consumerdurables. The old
    # name sat here behind a bare `except: pass`, so its absence was invisible and its names
    # fell through to the Tier 3 hand register instead of being sourced.
    "ind_niftyconsumerdurableslist",
    "ind_niftycommoditieslist",
    "ind_niftyinfralist",
    "ind_niftypsubanklist",
    # Widest NSE list (751 names). Listed first so narrower, more specific sectoral files
    # overwrite it on conflict.
    "ind_niftytotalmarket_list",
]


def download_nse_industry() -> tuple[dict, dict]:
    """Download NSE index constituent files.

    Returns ({symbol: industry}, {symbol: source_file}). Fails loudly: a non-200 raises, as
    does a transport error. A silently-skipped file demotes real names into the hand register,
    which is exactly how that register grew an error rate nobody could see.
    """
    result, evidence = {}, {}
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})
    for fname in NSE_INDEX_FILES:
        url = f"https://nsearchives.nseindia.com/content/indices/{fname}.csv"
        resp = sess.get(url, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"{fname}: HTTP {resp.status_code} — fix the name or remove it "
                               f"from NSE_INDEX_FILES; do not let it fail silently")
        n = 0
        for line in resp.text.strip().split("\n")[1:]:
            parts = line.split(",")
            if len(parts) >= 4:
                sym, ind = parts[2].strip(), parts[1].strip()
                if sym and ind:
                    result[sym] = ind
                    evidence[sym] = fname
                    n += 1
        print(f"  {fname}: {n} names")
    return result, evidence


# --- Tier 3: Manual register for genuinely dead/delisted names ---
# Mapped into NSE's official 20-label taxonomy.
MANUAL_SECTORS = {
    # --- Genuinely dead / delisted ---
    "ABIRLANUVO": "Textiles",
    "ALBK": "Financial Services",
    "ANDHRABANK": "Financial Services",
    "BHARATFIN": "Financial Services",
    "CAIRN": "Oil Gas & Consumable Fuels",
    "CAPF": "Financial Services",
    "DALMIABHA": "Construction Materials",
    "DHFL": "Financial Services",
    "JETAIRWAYS": "Services",
    "MCLEODRUSS": "Textiles",
    "ORIENTBANK": "Financial Services",
    "RCOM": "Telecommunication",
    "RDEL": "Capital Goods",
    "RELCAPITAL": "Financial Services",
    "RELINFRA": "Power",
    "RNAVAL": "Services",
    "SINTEX": "Textiles",
    "SREINFRA": "Financial Services",
    "SYNDIBANK": "Financial Services",

    # --- Live names outside Nifty 500, mapped to NSE taxonomy ---
    "AMARAJABAT": "Automobile and Auto Components",
    "APLLTD": "Healthcare",
    "ARVIND": "Textiles",
    "CENTURYTEX": "Textiles",
    "DCBBANK": "Financial Services",
    "DELTACORP": "Consumer Durables",
    "DISHTV": "Media Entertainment & Publication",
    "EQUITAS": "Financial Services",
    "GNFC": "Chemicals",
    "GSFC": "Chemicals",
    "GSPL": "Oil Gas & Consumable Fuels",
    "GUJGASLTD": "Oil Gas & Consumable Fuels",
    "HCC": "Construction",
    "HDFC": "Financial Services",
    "HDIL": "Realty",
    "HEXAWARE": "Information Technology",
    "IBREALEST": "Realty",
    "ICIL": "Textiles",
    "IDFC": "Financial Services",
    "INFIBEAM": "Information Technology",
    "JISLJALEQS": "Chemicals",
    "JPASSOCIAT": "Construction",
    "JUSTDIAL": "Services",
    "KSCL": "Chemicals",
    "KTKBANK": "Financial Services",
    "METROPOLIS": "Healthcare",
    "MINDTREE": "Information Technology",
    "PCJEWELLER": "Consumer Durables",
    "PEL": "Financial Services",
    "PTC": "Services",
    "RAIN": "Chemicals",
    "RAYMOND": "Textiles",
    "REPCOHOME": "Financial Services",
    "SKSMICRO": "Financial Services",
    "SOUTHBANK": "Financial Services",
    "STAR": "Healthcare",
    "TATAMTRDVR": "Automobile and Auto Components",
    "TV18BRDCST": "Media Entertainment & Publication",
    "UJJIVAN": "Financial Services",
    "UNITECH": "Realty",
    "VGUARD": "Consumer Durables",
}


def get_entity_map_time_aware(con) -> dict:
    """Load time-aware entity intervals.
    Returns {symbol: [(valid_from, valid_to, entity)]} sorted by valid_from.
    """
    rows = con.execute("""
        SELECT symbol, valid_from, valid_to, entity
        FROM symbol_entity_intervals
        WHERE entity IS NOT NULL
        ORDER BY symbol, valid_from
    """).fetchall()
    result = defaultdict(list)
    for sym, vf, vt, ent in rows:
        result[sym].append((vf, vt, ent))
    return dict(result)


def get_entity_industry(entity: str, tier1: dict, entity_to_symbols: dict):
    """Industry for an entity, via its sibling symbols in Tier 1.

    Returns (industry, sibling) so the inheritance can be evidenced, or (None, None).
    """
    for sibling in entity_to_symbols.get(entity, []):
        if sibling in tier1:
            return tier1[sibling], sibling
    return None, None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Get F&O universe
    con = duckdb.connect(str(FUTURES_DB), read_only=True)
    fo_names = {r[0] for r in con.execute(
        "SELECT DISTINCT underlying FROM futures_bhavcopy WHERE inst_type='FUTSTK'"
    ).fetchall()}
    print(f"F&O universe: {len(fo_names)} FUTSTK names")

    # Get cell counts per name
    cell_counts = {}
    for name in fo_names:
        cell_counts[name] = con.execute(
            "SELECT COUNT(*) FROM futures_bhavcopy WHERE underlying=? AND inst_type='FUTSTK'",
            [name]
        ).fetchone()[0]
    total_cells = sum(cell_counts.values())
    con.close()

    # Tier 1: NSE sourced industry
    print("\n=== Tier 1: Downloading NSE industry classification ===")
    tier1_raw, tier1_evidence = download_nse_industry()
    tier1 = {k: v for k, v in tier1_raw.items() if k in fo_names}
    print(f"  {len(tier1)}/{len(fo_names)} names sourced from NSE index files")

    remaining = fo_names - set(tier1.keys())
    print(f"  Remaining after Tier 1: {len(remaining)}")

    # Tier 2: Entity inheritance (time-aware)
    con = duckdb.connect(str(ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"), read_only=True)
    entity_map = get_entity_map_time_aware(con)

    # Build reverse map: entity → list of symbols
    entity_to_symbols = defaultdict(list)
    for sym, intervals in entity_map.items():
        for vf, vt, ent in intervals:
            if sym in fo_names:
                entity_to_symbols[ent].append(sym)
    con.close()

    # One entry per (symbol, entity interval), not one per symbol. A recycled ticker (DTIL)
    # is two different companies across its intervals, so a single blanket sector for all
    # time would attach the successor's industry to the predecessor's history.
    tier2 = {}
    tier2_intervals = defaultdict(list)
    for name in sorted(remaining):
        for vf, vt, entity in entity_map.get(name, []):
            if entity is None:
                continue
            industry, sibling = get_entity_industry(entity, tier1, entity_to_symbols)
            if industry:
                tier2_intervals[name].append((vf, vt, industry, f"inherit:{entity} via {sibling}"))
                tier2[name] = industry

    print(f"\n=== Tier 2: Entity inheritance (time-aware) ===")
    print(f"  {len(tier2)}/{len(remaining)} names inherited")

    remaining -= set(tier2.keys())
    print(f"  Remaining after Tier 2: {len(remaining)}")

    # Tier 3: Manual register
    tier3 = {k: v for k, v in MANUAL_SECTORS.items() if k in remaining}
    print(f"\n=== Tier 3: Manual register ===")
    print(f"  {len(tier3)}/{len(remaining)} names mapped manually")

    remaining -= set(tier3.keys())
    unclassified = sorted(remaining)
    print(f"  UNCLASSIFIED: {len(unclassified)}")

    # Combine all tiers
    all_sectors = {}
    all_sectors.update({k: (v, "1") for k, v in tier1.items()})
    all_sectors.update({k: (v, "2") for k, v in tier2.items()})
    all_sectors.update({k: (v, "3") for k, v in tier3.items()})
    for name in unclassified:
        all_sectors[name] = ("UNCLASSIFIED", "?")

    # Coverage report
    print()
    print("=" * 60)
    print("COVERAGE REPORT")
    print("=" * 60)
    print(f"{'Tier':20s} {'Names':>6s} {'Cells':>10s} {'% Cells':>8s}")
    print("-" * 46)
    for label, names in [
        ("Tier 1 (NSE sourced)", list(tier1.keys())),
        ("Tier 2 (entity inherit)", list(tier2.keys())),
        ("Tier 3 (manual dead)", list(tier3.keys())),
        ("UNCLASSIFIED", unclassified),
    ]:
        n_cells = sum(cell_counts[n] for n in names)
        pct = 100 * n_cells / total_cells if total_cells > 0 else 0
        print(f"{label:20s} {len(names):>6d} {n_cells:>10,d} {pct:>7.1f}%")
    print("-" * 46)
    print(f"{'TOTAL':20s} {len(fo_names):>6d} {total_cells:>10,d} {'100.0%':>8s}")

    covered_cells = total_cells - sum(cell_counts[n] for n in unclassified)
    if unclassified:
        print(f"\nUNCLASSIFIED cells: {total_cells - covered_cells:,} ({100*(total_cells-covered_cells)/total_cells:.1f}%)")
    else:
        print(f"\nStatus: ALL CLEAR — 100% coverage")

    # Write output with time-aware schema
    # Tier 1 and 3 are static by design — a current snapshot used as a non-PIT control
    # (OPEN-2(a), disclosed). Tier 2 carries the real entity intervals it was inherited over.
    out_path = OUTPUT_DIR / "sector_classification.csv"
    rows = 0
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "sector", "tier", "valid_from", "valid_to", "evidence"])
        for sym, (sec, tier_label) in sorted(all_sectors.items()):
            if tier_label == "2" and tier2_intervals.get(sym):
                for vf, vt, industry, ev in tier2_intervals[sym]:
                    w.writerow([sym, industry, "2", vf, vt, ev])
                    rows += 1
                continue
            evidence = {
                "1": tier1_evidence.get(sym, ""),
                "3": "manual-register",
            }.get(tier_label, "")
            w.writerow([sym, sec, tier_label, "2016-02-11", "9999-12-31", evidence])
            rows += 1
    print(f"\nWritten to {out_path} ({rows} rows, {len(all_sectors)} symbols)")

    # Print tier 1 labels for reference
    tier1_labels = sorted(set(tier1.values()))
    print(f"\nNSE taxonomy labels used ({len(tier1_labels)}):")
    for lbl in tier1_labels:
        n = sum(1 for v in tier1.values() if v == lbl)
        print(f"  {lbl}: {n} names")


if __name__ == "__main__":
    main()
