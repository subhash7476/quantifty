"""Options-Wall scan CLI — print the ranked farm list for Nifty + BankNifty.

Usage:
    python scripts/options_wall_scan.py [--indices NIFTY BANKNIFTY]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.options_wall.engine import scan_indices


def _fmt(r) -> str:
    credit = f"{r.credit:.1f}" if r.credit is not None else "-"
    gap = f"{r.iv_minus_rv:+.1f}" if r.iv_minus_rv is not None else "-"
    pin = f"{r.pin_conviction:.2f}" if r.pin_conviction is not None else "-"
    strike = f"{r.strike:.0f}" if r.strike is not None else "-"
    return (f"{r.screen:<12} {r.structure:<16} {r.option_type or '--':<4} "
            f"{strike:>8}  score={r.score:.2f}  credit={credit:>7}  "
            f"IV-RV={gap:>6}  pin={pin}  {r.reason}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Options-Wall scan")
    parser.add_argument("--indices", nargs="+", default=["NIFTY", "BANKNIFTY"])
    args = parser.parse_args()

    scanned = scan_indices(tuple(args.indices))
    for name, bundle in scanned.items():
        structural = bundle["structural"]
        rv = bundle["rv"]
        results = bundle["results"]
        print(f"\n=== {name} ===")
        if structural is None:
            print("  (no chain available)")
            continue
        print(f"  spot={structural.underlying_ltp:.1f}  expiry={structural.expiry}  "
              f"regime={structural.gex.regime}  RV={rv if rv is not None else '-'}")
        if not results:
            print("  (no farm-list rows for this cycle)")
            continue
        for r in results:
            print("  " + _fmt(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
