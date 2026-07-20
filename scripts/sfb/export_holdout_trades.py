"""Export HOLDOUT trades from the F1 feasibility screen as CSV."""

import sys, csv
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "sfb"))

import f1_feasibility_screen as S

OUTPUT = ROOT / "data" / "f1_holdout_trades_2019_2022.csv"


def main():
    print("Loading panel...")
    panel = S.load_prices_and_ohlc(S.DB_PATH, cutoff=S.DEV_HI)
    universe = S.build_liquidity_universe(panel, cutoff=S.DEV_HI)
    print(f"  Formations with eligible names: {len(universe)}")

    holdout_fd = sorted([d for d in universe
                         if S.HOLDOUT_LO <= d <= S.HOLDOUT_HI
                         and len(universe[d]) >= S.MIN_NAMES])
    print(f"  HOLDOUT formations: {len(holdout_fd)}")

    if not holdout_fd:
        print("No HOLDOUT formations found.")
        return

    # Best bracket from the screen
    train_fd = sorted([d for d in universe if d <= S.TRAIN_HI
                       and len(universe[d]) >= S.MIN_NAMES])
    best_bracket = S.select_bracket(panel, universe, train_fd, 0.0010)

    cal = panel["cal"]
    cal_pos = panel["cal_pos"]
    px = panel["px"]

    rows = []

    for t in holdout_fd:
        scores = S.score_momentum_12_1(panel, t)
        picks = S.select_top_n(scores, universe.get(t, []))
        if len(picks) < S.MIN_NAMES:
            continue

        idx = cal_pos.get(t)
        next_fd = None
        for j in range(idx + 1, len(cal)):
            d2 = cal[j]
            if S._is_month_end(cal, j) and d2 <= S.HOLDOUT_HI:
                next_fd = d2
                break
        if next_fd is None or next_fd <= t:
            continue

        for ent in picks:
            p0 = px.get((ent, t))
            if not p0 or p0 <= 0:
                continue

            bars = []
            for j in range(idx + 1, len(cal)):
                d2 = cal[j]
                if d2 > next_fd:
                    break
                h = panel["hi"].get((ent, d2))
                lv = panel["lo"].get((ent, d2))
                bars.append((d2, h, lv))
            if not bars:
                continue

            atr = S._compute_atr(panel, ent, t)
            n_max, k_sl, k_tp = best_bracket
            exit_price, days_held = S._apply_bracket(p0, atr, n_max, k_sl, k_tp, bars)

            if exit_price == p0:
                p1 = px.get((ent, next_fd))
                if p1 and p1 > 0:
                    exit_price = p1
                    days_held = n_max

            if exit_price <= 0:
                continue

            gross_ret = exit_price / p0 - 1.0
            buy_cost = S.formation_cost(S.POSITION_NOTIONAL, t, "BUY", 0.0010)
            sell_cost = S.formation_cost(S.POSITION_NOTIONAL, next_fd, "SELL", 0.0010)
            roll_cost = S.ROLL_ROUND_TRIPS_PER_FORMATION * (
                S.formation_cost(S.POSITION_NOTIONAL, t, "SELL", 0.0010)
                + S.formation_cost(S.POSITION_NOTIONAL, t, "BUY", 0.0010))
            net_ret = gross_ret - buy_cost - sell_cost - roll_cost

            exit_reason = "bracket_sl" if exit_price < p0 * 0.99 else (
                          "bracket_tp" if exit_price > p0 * 1.01 else "period_end")

            rows.append({
                "formation_date": t,
                "next_formation": next_fd,
                "entity": ent,
                "entry_price": round(p0, 2),
                "exit_price": round(exit_price, 2),
                "gross_return_pct": round(gross_ret * 100, 2),
                "net_return_pct": round(net_ret * 100, 2),
                "days_held": days_held,
                "exit_reason": exit_reason,
                "atr": round(atr, 2) if atr else "",
                "k_sl": k_sl,
                "k_tp": k_tp,
                "n_max": n_max,
            })

    print(f"  Trade rows: {len(rows)}")

    fieldnames = [
        "formation_date", "next_formation", "entity", "entry_price",
        "exit_price", "gross_return_pct", "net_return_pct",
        "days_held", "exit_reason", "atr", "k_sl", "k_tp", "n_max",
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"  Written to {OUTPUT}")
    print(f"  Formations: {len(set(r['formation_date'] for r in rows))}")
    print(f"  Unique entities: {len(set(r['entity'] for r in rows))}")
    print(f"  Mean gross return: {sum(r['gross_return_pct'] for r in rows)/len(rows):.2f}%")


if __name__ == "__main__":
    main()
