"""SE-3 post-review audit — B-2 / MEDIUM-1 reconciliation.

Answers the lead review's blocking question B-2: which end does Phase 2's
1,680th formation date sit on, versus Phase 1's certified 1,679?

READ-ONLY: recomputes the deterministic eligibility sets (Phase 1 waterfall
dates and Phase 2 IC dates) but writes NOTHING — no snapshot, no report, no
data/ file. This is a governance audit, not a re-run of the one-shot read and
not a re-read for tuning.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.se3 import certify_substrate as c
from scripts.se3 import run_confirmatory as r


def main():
    print("=== Phase 1 (certify_substrate.build_panel) ===")
    d = c.build_panel()
    all_dates = d["all_dates"]
    first_usable = d["first_usable"]
    print(f"total trading dates: {len(all_dates)}")
    print(f"first_usable (A10 RV warmup, all_dates[{c.RV_WINDOW - 1}]): {first_usable.date()}")
    # Phase 1 waterfall eligible set
    remaining = [x for x in all_dates if first_usable is None or x >= first_usable]
    cal_pos = {x: i for i, x in enumerate(all_dates)}
    remaining = [x for x in remaining if cal_pos[x] + 2 < len(all_dates)]
    rich_ok = set(d["names_per_day"][d["names_per_day"] >= c.MIN_NAMES].index)
    pair_ok = set(d["paired_per_day"][d["paired_per_day"] >= c.MIN_NAMES].index)
    remaining = [x for x in remaining if x in rich_ok]
    remaining = [x for x in remaining if x in pair_ok]
    print(f"Phase 1 waterfall eligible: {len(remaining)} dates")
    if remaining:
        print(f"  first: {remaining[0].date()}  last: {remaining[-1].date()}")

    print()
    print("=== Phase 2 (run_confirmatory merged_skip IC dates) ===")
    panel = d["panel"]
    from scripts.se3.certify_substrate import (
        _load_mcwb, _load_futures, _load_stock_options, _membership_for_date,
    )
    snapshots, _ = _load_mcwb()
    raw_fut = _load_futures(d["member_syms"])
    fut_stk = raw_fut[raw_fut["inst_type"] == "FUTSTK"]
    fut_stk_settle = fut_stk.set_index(["underlying", "expiry_dt", "trade_date"])["settle"]
    membership = {}
    fills = {}
    for td in all_dates:
        membership[td] = set(_membership_for_date(snapshots, td, fills).keys())
    fo_live = set(zip(fut_stk["underlying"], fut_stk["trade_date"]))
    member_pairs = set()
    for td, syms in membership.items():
        for s in syms:
            if (s, td) in fo_live:
                member_pairs.add((s, td))
    raw_stock = _load_stock_options(member_pairs, traded_only=True)
    traded = raw_stock

    returns = r.build_returns(panel, traded, fut_stk_settle)
    merged = panel.merge(returns, on=["trade_date", "underlying"], how="inner")
    merged = merged.sort_values(["underlying", "trade_date"]).reset_index(drop=True)
    merged["dh_skip"] = merged.groupby("underlying")["dh_return_scaled"].shift(-1)
    merged_skip = merged.dropna(subset=["dh_skip"]).copy()
    merged_skip["dh_return_scaled"] = merged_skip["dh_skip"]

    ic_per_day = merged_skip.dropna(subset=["richness"]).groupby("trade_date").size()
    ic_dates = sorted(ic_per_day[ic_per_day >= r.MIN_NAMES_IC].index)
    print(f"Phase 2 IC eligible: {len(ic_dates)} dates")
    if ic_dates:
        print(f"  first: {ic_dates[0].date()}  last: {ic_dates[-1].date()}")

    print()
    print("=== D1 (full pre-reg §5.1 cost stack, recomputed on frozen panel) ===")
    for bps in (0, 25, 50, 100):
        q = r._quintile_pnl(merged_skip, bps)
        if q is None:
            print(f"bps {bps}: no data")
            continue
        print(f"bps {bps:>3}: n_days={len(q)} gross_total={q['gross_pnl'].sum():.4f} "
              f"net_total={q['net_pnl'].sum():.4f} net_mean={q['net_pnl'].mean():.4f}")

    print()
    print("=== reconciliation ===")
    if remaining and ic_dates:
        print(f"Phase 1 first {remaining[0].date()} vs Phase 2 first {ic_dates[0].date()}")
        print(f"Phase 1 last  {remaining[-1].date()} vs Phase 2 last  {ic_dates[-1].date()}")
        early_diff = remaining[0] != ic_dates[0]
        late_diff = remaining[-1] != ic_dates[-1]
        if early_diff and not late_diff:
            print("Extra date is at the WARMUP end -> Phase 2 honours A10's >=18-obs floor,")
            print("admitting one earlier date than Phase 1's flat 20-day skip. Phase 2 is")
            print("correct; Phase 1's waterfall line is the wrong one.")
        elif late_diff and not early_diff:
            print("Extra date is at the TAIL end -> fence question, not a counting question.")
        elif early_diff and late_diff:
            print("Both ends differ.")
        else:
            print("First and last dates identical; count difference is interior.")


if __name__ == "__main__":
    main()
