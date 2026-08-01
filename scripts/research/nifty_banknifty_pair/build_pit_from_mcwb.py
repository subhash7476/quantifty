"""
Build PIT Nifty 50 membership from NSE Monthly Constituent Weight Bulletins (MCWB).

Sources:
  data/reference/mcwb_*.zip — 125 monthly archives, each with nifty50_mcwb.csv
  data/reference/mcwb_manifest.json — metadata, SHA-256 verification

Output:
  data/reference/nifty50_pit_membership.json — PIT membership table
  data/reference/nifty50_pit_weights.json — monthly free-float weights
"""
import json
import csv
import zipfile
from pathlib import Path
from datetime import date
from collections import defaultdict


def parse_mcwb_archives():
    manifest_path = Path("data/reference/mcwb_manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    records = manifest["records"]
    valid_records = [r for r in records if r["status"] == "valid"]

    membership = {}   # month -> set of symbols
    weights = {}      # month -> {symbol -> weight_pct}

    missing_months = [r["month"] for r in records if r["status"] == "missing"]

    for rec in valid_records:
        month = rec["month"]
        zip_path = Path("data/reference") / rec["filename"]

        if not zip_path.exists():
            print(f"  WARNING: {rec['filename']} not found on disk")
            continue

        try:
            with zipfile.ZipFile(zip_path) as zf:
                with zf.open("nifty50_mcwb.csv") as f:
                    content = f.read().decode("utf-8")
        except Exception as e:
            print(f"  WARNING: Cannot read {rec['filename']}: {e}")
            continue

        # Parse CSV — skip header rows (first 2 lines are metadata)
        lines = content.split("\n")
        data_start = 0
        for i, line in enumerate(lines):
            if line.startswith("Sr. No"):
                data_start = i + 1
                break

        syms = set()
        sym_weights = {}
        try:
            reader = csv.reader(lines[data_start:])
            for row in reader:
                if len(row) < 7:
                    continue
                try:
                    sym = row[1].strip()
                    # Weight% is at index 6
                    weight_str = row[6].strip()
                    weight = float(weight_str)
                    syms.add(sym)
                    sym_weights[sym] = weight
                except (ValueError, IndexError):
                    # Skip rows with malformed data
                    continue
        except Exception as e:
            print(f"  WARNING parsing {rec['filename']}: {e}")
            continue

        if len(syms) >= 45:
            membership[month] = syms
            weights[month] = sym_weights
        else:
            print(f"  WARNING: {month} has only {len(syms)} constituents (expected ~50)")

    # Fill missing months with previous month's data
    sorted_months = sorted(membership.keys())
    for missing in sorted(missing_months):
        # Find most recent previous month
        prev = None
        for m in sorted_months:
            if m < missing:
                prev = m
        if prev:
            membership[missing] = membership[prev].copy()
            weights[missing] = {k: v for k, v in weights[prev].items()}
            print(f"  Filled missing {missing} from {prev}")

    return membership, weights, valid_records, missing_months


def main():
    print("Parsing NSE MCWB archives...")
    membership, weights, valid_records, missing_months = parse_mcwb_archives()

    n_records = len([r for r in valid_records if r["status"] == "valid"])
    print(f"\nParsed: {n_records} valid months, {len(missing_months)} missing")
    print(f"Coverage: {min(membership.keys())} to {max(membership.keys())}")
    print(f"Missing months: {missing_months}")

    # Check a few dates
    for month in sorted(membership.keys())[::24]:
        syms = membership[month]
        print(f"  {month}: {len(syms)} symbols")
        if month in weights:
            top3 = sorted(weights[month].items(), key=lambda x: -x[1])[:3]
            print(f"    Top weights: {[(s, f'{w:.1f}%') for s, w in top3]}")

    # Save
    out_dir = Path("data/reference")
    out_dir.mkdir(parents=True, exist_ok=True)

    membership_out = {k: sorted(list(v)) for k, v in membership.items()}
    with open(out_dir / "nifty50_pit_membership.json", "w") as f:
        json.dump(membership_out, f, indent=2)
    print(f"\nSaved membership: {out_dir / 'nifty50_pit_membership.json'}")

    with open(out_dir / "nifty50_pit_weights.json", "w") as f:
        json.dump(weights, f, indent=2)
    print(f"Saved weights: {out_dir / 'nifty50_pit_weights.json'}")

    # Summary stats
    n_months = len(membership)
    n_symbols_total = len(set().union(*membership.values()))
    avg_symbols = sum(len(v) for v in membership.values()) / n_months
    print(f"\nSummary: {n_months} months, {n_symbols_total} unique symbols, {avg_symbols:.1f} avg per month")


if __name__ == "__main__":
    main()
