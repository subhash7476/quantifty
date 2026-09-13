"""Anchor x MCWB x PR reconciliation for Nifty 50 / Next 50 membership.

Triangulates three sources per semi-annual review (MAR: Feb->Apr snapshots,
effective window Feb-Apr; SEP: Aug->Oct snapshots, window Aug-Oct):
  1. ANCHOR: review-effective months from the PR corpus itself.
  2. MCWB: monthly member sets from data/reference/mcwb_*.zip (both legs).
  3. PR: include/exclude events from data/isd/n200_membership.duckdb.

Per (review, leg) each canonical symbol classifies as AGREE (both sources
move it the same way), PR-ONLY, or MCWB-ONLY. MCWB-ONLY rows are the
error-detector: missed PR, rename-mapping miss, or genuine NSE deviation.

Also runs anchor-conformance over the broad family (N200/50/Next50/100/
Full-Midcap): boundaries with effective months outside {2,3,4,8,9,10}
must be corporate-action-type; they are listed for review, not failed.

Read-only. Writes data/isd/mcwb_pr_reconciliation.csv + stdout summary.

Usage:
    python scripts/isd/reconcile_mcwb_pr.py
"""

import csv
import json
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "isd"))

from download_mcwb_archives import REF_DIR, MANIFEST_PATH, read_leg_members
from build_n200_membership import load_rename_dates, canonical_label

OUT_CSV = ROOT / "data" / "isd" / "mcwb_pr_reconciliation.csv"

LEGS = (("NIFTY 50", "n50"), ("NIFTY NEXT 50", "next50"))
FAMILY = ("NIFTY 200", "NIFTY 50", "NIFTY NEXT 50", "NIFTY 100",
          "NIFTY FULL MIDCAP 100")
ANCHOR_MONTHS = {2, 3, 4, 8, 9, 10}


def load_mcwb_sets():
    """{(year, month, leg): frozenset(canonical tickers)} for valid months."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    valid = {r["month"] for r in manifest["records"] if r["status"] == "valid"}
    rename_dates = load_rename_dates()
    canon = lambda s: canonical_label(s.strip(), rename_dates)
    sets = {}
    for m in sorted(valid):
        y, mo = int(m[:4]), int(m[5:7])
        path = REF_DIR / f"mcwb_{['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'][mo-1]}{y % 100:02d}.zip"
        members = read_leg_members(path)
        for _, leg in LEGS:
            sets[(y, mo, leg)] = frozenset(canon(t) for t in members[leg] if t)
    return sets


def load_pr_events():
    """{index_norm: [(effective_date, action, symbol, company)]}."""
    con = duckdb.connect(str(ROOT / "data" / "isd" / "n200_membership.duckdb"),
                         read_only=True)
    rows = con.execute(
        "select index_norm, effective_date, action, symbol, company "
        "from n200_events").fetchall()
    con.close()
    out = {}
    for idx, eff, act, sym, co in rows:
        out.setdefault(idx, []).append((eff, act, sym, co))
    return out


def main():
    mcwb = load_mcwb_sets()
    pr = load_pr_events()
    have = {(y, m) for (y, m, _l) in mcwb}

    reviews = []
    for y in range(2010, 2027):
        reviews.append((y, "MAR", (y, 2), (y, 4), date(y, 2, 1), date(y, 4, 30)))
        reviews.append((y, "SEP", (y, 8), (y, 10), date(y, 8, 1), date(y, 10, 31)))

    rename_dates = load_rename_dates()
    canon = lambda s: (canonical_label(s.strip(), rename_dates)
                       if s and s.strip() else None)

    def as_date(eff):
        return eff if hasattr(eff, "month") else date.fromisoformat(str(eff)[:10])

    PR_CORPUS_START = 2011  # n200_events PR coverage begins 2011; 2010 is MCWB-only

    rows = []
    print(f"{'review':>8} {'leg':>7} {'+mcwb':>6} {'-mcwb':>6} "
          f"{'PRin':>5} {'PRout':>6} {'AGREE':>6} {'PRONLY':>7} {'MCWBONLY':>9}  note")
    for y, tag, pre, post, w0, w1 in reviews:
        rev = f"{y}-{tag}"
        for idx, leg in LEGS:
            if pre not in have or post not in have:
                print(f"{rev:>8} {leg:>7} {'':>6} {'':>6} {'':>5} {'':>6} "
                      f"{'':>6} {'':>7} {'':>9}  SKIP pre/post MCWB missing")
                continue
            added = set(mcwb[(post[0], post[1], leg)]) - set(mcwb[(pre[0], pre[1], leg)])
            removed = set(mcwb[(pre[0], pre[1], leg)]) - set(mcwb[(post[0], post[1], leg)])
            pins, pouts = set(), set()
            for eff, act, sym, _co in pr.get(idx, []):
                if not (w0 <= as_date(eff) <= w1):
                    continue
                (pins if act == "include" else pouts).add(sym)
            pins = {canon(s) for s in pins} - {None}
            pouts = {canon(s) for s in pouts} - {None}
            pre_corpus = y < PR_CORPUS_START
            agree_in = added & pins
            agree_out = removed & pouts
            pr_only = (pins - added) | (pouts - removed)
            mcwb_only = (added - pins) | (removed - pouts)
            for s in sorted(agree_in):
                rows.append((rev, leg, s, "added", "include", "AGREE"))
            for s in sorted(agree_out):
                rows.append((rev, leg, s, "removed", "exclude", "AGREE"))
            for s in sorted(pr_only):
                side = "include" if s in pins else "exclude"
                mside = "added" if s in added else ("removed" if s in removed else "-")
                rows.append((rev, leg, s, mside, side, "PR-ONLY"))
            for s in sorted(mcwb_only):
                rows.append((rev, leg, s,
                             "added" if s in added else "removed", "-", "MCWB-ONLY"))
            note = ""
            if pre_corpus:
                note = "PRE-CORPUS (PR coverage starts 2011; MCWB moves are new evidence)"
            elif pr_only or mcwb_only:
                note = ("PR-ONLY: " + ",".join(sorted(pr_only)) if pr_only else "")
                note += (" | " if note and mcwb_only else "")
                note += ("MCWB-ONLY: " + ",".join(sorted(mcwb_only)) if mcwb_only else "")
            print(f"{rev:>8} {leg:>7} {len(added):>6} {len(removed):>6} "
                  f"{len(pins):>5} {len(pouts):>6} "
                  f"{len(agree_in | agree_out):>6} {len(pr_only):>7} "
                  f"{len(mcwb_only):>9}  {note}")

    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["review", "leg", "symbol", "mcwb", "pr", "class"])
        w.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {OUT_CSV}")

    print("\n== anchor-conformance: broad-family events outside Feb/Mar/Apr/Aug/Sep/Oct ==")
    off = []
    for idx in FAMILY:
        for eff, act, sym, co in pr.get(idx, []):
            m = eff.month if hasattr(eff, "month") else int(str(eff)[5:7])
            if m not in ANCHOR_MONTHS:
                off.append((str(eff)[:10], idx, act, sym, co))
    off.sort(key=lambda o: tuple("" if x is None else str(x) for x in o))
    print(f"{len(off)} off-cycle events")
    for o in off:
        print("  ", " | ".join("" if x is None else str(x) for x in o))


if __name__ == "__main__":
    main()
