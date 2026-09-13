"""Remove 1m bars stamped after the cash session closes.

Four sessions in Feb-Mar 2026 carry a tail of bars at 15:40-15:59 on top of a
complete 09:15-15:29 session - one row per symbol per minute, all with volume,
swelling toward 15:59. The same shape appeared in the 2026-03-03 orphan file,
which held 184 such rows stamped 2026-03-02, so this is one mechanism: the
ingestor flushing late aggregates after the close, sometimes into the next
day's file.

They are outside every cash window in core/market/session_schedule.py (pre-CAS
equities close 15:30; post-CAS the auction ends 15:35), so no equity 1m bar can
legitimately carry a later stamp. The harm is specific: any loader that takes
the last bar of the day as the close reads the 15:59 print instead of the 15:29
close - on 2026-03-04 that is 183 of ~206 symbols.

Muhurat and other special sessions are NOT pruned. They run entirely outside
the standard window (18:00-19:00, 13:45-14:44) and are real trading sessions;
a file whose bars are ALL out-of-window is a special session and is reported,
never touched. Only a file that holds a complete standard session AND a tail
beyond it is pruned.

Copy-first: each file is copied to data/_baselines/1m_pre_post_close_prune/
before the delete, and an existing baseline is never overwritten.

  python scripts/cas/prune_post_close_bars.py            # plan only
  python scripts/cas/prune_post_close_bars.py --apply
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.market.session_schedule import SEGMENTS, session_window  # noqa: E402
from scripts.cas.fo_1m_coverage import CANDLES_1M_DIR  # noqa: E402

BASELINE_DIR = ROOT / "data" / "_baselines" / "1m_pre_post_close_prune"


# The cash schedule bounds NSE cash equities and nothing else. Two other things
# legitimately sit outside it and must never be pruned:
#   - MCX_FO contracts (commodity futures open 09:00 and run to 23:55), and
#   - NSE_INDEX|Nifty 50's 15:30 bar on 2023-01-31, which is the vendor-era
#     end-labelled seam gate C1 exists to explain - deleting it would destroy
#     C1's own evidence.
# Restricting to NSE_EQ covers both without special-casing either.
EQUITY_PREFIX = "NSE_EQ|%"


def cash_close(on: date):
    """Latest minute any cash bar may be stamped: widest cash window, exclusive end."""
    ends = [session_window(seg, on)[1] for seg in SEGMENTS
            if seg.startswith("cash") and session_window(seg, on)]
    return max(ends)


def survey(sessions: list[date]):
    """[(date, in_window rows, late rows, late symbols, last late stamp)] for pruneable files."""
    out, specials = [], []
    for d in sessions:
        path = CANDLES_1M_DIR / f"{d}.duckdb"
        if not path.exists():
            continue
        cutoff = cash_close(d)
        con = duckdb.connect(str(path), read_only=True)
        try:
            keep, late, syms, last = con.execute(
                "SELECT count(*) FILTER (WHERE CAST(timestamp AS TIME) < ?), "
                "       count(*) FILTER (WHERE CAST(timestamp AS TIME) >= ?), "
                "       count(DISTINCT symbol) FILTER (WHERE CAST(timestamp AS TIME) >= ?), "
                "       max(CAST(timestamp AS TIME)) FILTER (WHERE CAST(timestamp AS TIME) >= ?) "
                "FROM candles WHERE symbol LIKE ?",
                [cutoff, cutoff, cutoff, cutoff, EQUITY_PREFIX]).fetchone()
        finally:
            con.close()
        if not late:
            continue
        if not keep:
            specials.append((d, late, str(last)))   # whole file outside the window
        else:
            out.append((d, keep, late, syms, str(last)))
    return out, specials


def _baseline(d: date) -> None:
    src = CANDLES_1M_DIR / f"{d}.duckdb"
    dst = BASELINE_DIR / f"{d}.duckdb"
    if dst.exists():
        return
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if dst.stat().st_size != src.stat().st_size:
        raise RuntimeError(f"baseline {dst} does not match {src}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="prune (baselines first)")
    parser.add_argument("--from", dest="from_date", default="2023-01-02")
    args = parser.parse_args()

    lo = date.fromisoformat(args.from_date)
    sessions = sorted(d for d in
                      (date.fromisoformat(p.stem) for p in CANDLES_1M_DIR.glob("*.duckdb"))
                      if d >= lo)
    prune, specials = survey(sessions)

    for d, late, last in specials:
        print(f"SPECIAL SESSION (not pruned) {d}: all {late} bars outside the standard "
              f"window, last {last}")
    print(f"{len(prune)} sessions carry post-close bars on top of a normal session")
    for d, keep, late, syms, last in prune:
        print(f"  {d}: {late} rows / {syms} symbols after {cash_close(d)}, last {last} "
              f"({keep:,} in-window rows kept)")
    if not args.apply or not prune:
        return 0

    total = 0
    for d, _keep, late, _syms, _last in prune:
        _baseline(d)
        cutoff = cash_close(d)
        con = duckdb.connect(str(CANDLES_1M_DIR / f"{d}.duckdb"))
        try:
            con.execute("DELETE FROM candles WHERE CAST(timestamp AS TIME) >= ? "
                        "AND symbol LIKE ?", [cutoff, EQUITY_PREFIX])
            gone = con.execute("SELECT count(*) FROM candles WHERE CAST(timestamp AS TIME) >= ? "
                               "AND symbol LIKE ?", [cutoff, EQUITY_PREFIX]).fetchone()[0]
        finally:
            con.close()
        if gone:
            raise RuntimeError(f"{d}: {gone} post-close rows survived the delete")
        total += late
    print(f"pruned {total} rows across {len(prune)} sessions")

    prune, _ = survey(sessions)
    print(f"after: {len(prune)} sessions still carrying post-close bars")
    return 1 if prune else 0


if __name__ == "__main__":
    raise SystemExit(main())
