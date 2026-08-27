"""A — Phase-1 F&O cost substrate measurements.

Measures, WITHOUT any construct signal or P&L (read boundary per
A_CONSTRUCT_DEFINITION.md):

  A. Slippage  — bar-open vs prior-bar-close drift on the index 1m store,
                 era-split (vendor 2012-01-02..2023-01-31 / native
                 2023-03-01..present): pooled distribution + entry-bar drift
                 (bar index 31 and 46 opens vs prior closes — the A entry
                 bars, bar-count semantics from the opening print).
  B. Basis     — near-month Nifty futures (FUTIDX bhavcopy, volume-dominance
                 roll calendar) vs official 1d cash close, 2016-02-11..:
                 level distribution + |daily change| distribution (sizes the
                 basis lane; pre-2016 spans carry the disclosed assumption).
  C. Roll calendar — volume-dominance roll dates for NIFTY futures (causal,
                 per build_continuous_futures._resolve_roll_dates, FUTIDX).
  D. Cadence   — per-year count of tradeable sessions (session-valid per the
                 construct rule: first bar stamped with the session date +
                 entry bar index 31 / 46 present).

Usage: python scripts/a_index_intraday/measure_cost_substrate.py
"""
from __future__ import annotations

import glob
import json
import os
import statistics
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CANDLE_DIR_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
CANDLE_DIR_1D = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
FUTURES_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
OUT_DIR = ROOT / "data" / "a_index_intraday"
REPORT = ROOT / "docs" / "reports" / "A_COST_SUBSTRATE_MEASUREMENTS.md"

NF = "NSE_INDEX|Nifty 50"
VENDOR_LAST = "2023-01-31"
ENTRY_BAR_CELL1 = 31   # bar index of the entry open (window = bars 0..30)
ENTRY_BAR_CELL2 = 46   # bar index of the entry open (window = bars 0..45)


def pct_dist(a, labels=("p50", "p90", "p99", "max")):
    a = sorted(a)
    if not a:
        return {k: None for k in labels}
    return {
        "p50": a[len(a) // 2],
        "p90": a[int(len(a) * 0.90)],
        "p99": a[int(len(a) * 0.99)],
        "max": a[-1],
    }


def main() -> int:
    t0 = time.time()
    pooled = {"vendor": [], "native": []}
    entry31 = {"vendor": [], "native": []}
    entry46 = {"vendor": [], "native": []}
    cadence = {31: {}, 46: {}}
    valid_sessions = 0
    skipped_stamp = 0

    files = sorted(glob.glob(str(CANDLE_DIR_1M / "*.duckdb")))
    for i, f in enumerate(files):
        d = os.path.basename(f)[:10]
        era = "vendor" if d <= VENDOR_LAST else "native"
        con = duckdb.connect(f, read_only=True)
        try:
            rows = con.execute(
                "SELECT timestamp, open, close FROM candles "
                "WHERE symbol = ? ORDER BY timestamp", [NF]).fetchall()
        except Exception:
            rows = []
        con.close()
        if not rows:
            continue
        # session-validity rule: first bar stamped with the session date
        if rows[0][0].date().isoformat() != d:
            skipped_stamp += 1
            continue
        valid_sessions += 1
        opens = [float(r[1]) for r in rows]
        closes = [float(r[2]) for r in rows]
        for t in range(1, len(rows)):
            if closes[t - 1] > 0:
                pooled[era].append(abs(opens[t] - closes[t - 1]) / closes[t - 1])
        if len(rows) > ENTRY_BAR_CELL1 and closes[ENTRY_BAR_CELL1 - 1] > 0:
            entry31[era].append(abs(opens[ENTRY_BAR_CELL1]
                                    - closes[ENTRY_BAR_CELL1 - 1])
                                / closes[ENTRY_BAR_CELL1 - 1])
            cadence[31][d[:4]] = cadence[31].get(d[:4], 0) + 1
        if len(rows) > ENTRY_BAR_CELL2 and closes[ENTRY_BAR_CELL2 - 1] > 0:
            entry46[era].append(abs(opens[ENTRY_BAR_CELL2]
                                    - closes[ENTRY_BAR_CELL2 - 1])
                                / closes[ENTRY_BAR_CELL2 - 1])
            cadence[46][d[:4]] = cadence[46].get(d[:4], 0) + 1
        if (i + 1) % 600 == 0:
            print(f"  1m pass {i + 1}/{len(files)}")

    slip = {era: {"pooled_bp": pct_dist([x * 1e4 for x in pooled[era]]),
                  "entry31_bp": pct_dist([x * 1e4 for x in entry31[era]]),
                  "entry46_bp": pct_dist([x * 1e4 for x in entry46[era]])}
            for era in ("vendor", "native")}

    # ---- B/C. basis + roll calendar (FUTIDX NIFTY, 2016-02-11..) ------------
    con = duckdb.connect(str(FUTURES_DB), read_only=True)
    expiries = [r[0] for r in con.execute(
        "SELECT DISTINCT expiry_dt FROM futures_bhavcopy "
        "WHERE underlying = 'NIFTY' AND inst_type = 'FUTIDX' "
        "ORDER BY expiry_dt").fetchall()]
    roll_dates = []
    for k, near_exp in enumerate(expiries[:-1]):
        next_exp = expiries[k + 1]
        last_hold = near_exp - timedelta(days=1)
        r = con.execute(
            "WITH nv AS (SELECT trade_date, contracts c FROM futures_bhavcopy "
            "WHERE underlying='NIFTY' AND inst_type='FUTIDX' AND expiry_dt=? "
            "AND trade_date<=?), xv AS (SELECT trade_date, contracts c FROM "
            "futures_bhavcopy WHERE underlying='NIFTY' AND inst_type='FUTIDX' "
            "AND expiry_dt=?) SELECT nv.trade_date FROM nv JOIN xv ON "
            "xv.trade_date=nv.trade_date WHERE nv.c IS NOT NULL AND xv.c IS NOT "
            "NULL AND xv.c > nv.c ORDER BY nv.trade_date LIMIT 1",
            [near_exp, last_hold, next_exp]).fetchone()
        roll_dates.append((r[0] if r else last_hold, near_exp, next_exp))
    con.close()

    # in-effect contract per trade date: windows between roll dates
    def contract_for(d):
        for rd, near_exp, next_exp in roll_dates:
            if d <= rd:
                return near_exp
        return expiries[-1]

    cash = {}
    for f in sorted(glob.glob(str(CANDLE_DIR_1D / "*.duckdb"))):
        dd = os.path.basename(f)[:10]
        c = duckdb.connect(f, read_only=True)
        try:
            r = c.execute(
                "SELECT close FROM candles WHERE symbol=? AND timeframe='1d' "
                "ORDER BY timestamp DESC LIMIT 1", [NF]).fetchone()
        except Exception:
            r = None
        c.close()
        if r:
            cash[dd] = float(r[0])

    con = duckdb.connect(str(FUTURES_DB), read_only=True)
    fut = con.execute(
        "SELECT trade_date, expiry_dt, close FROM futures_bhavcopy "
        "WHERE underlying='NIFTY' AND inst_type='FUTIDX' AND close IS NOT NULL"
    ).fetchall()
    con.close()
    fut_by = {}
    for td, ex, cl in fut:
        fut_by.setdefault(td.isoformat(), {})[ex] = float(cl)

    basis_levels, basis_changes = [], []
    basis_dates = sorted(set(cash) & set(fut_by))
    prev_b, prev_ex = None, None
    n_basis = 0
    n_roll_days = 0
    for d in basis_dates:
        ex = contract_for(date.fromisoformat(d))
        fc = fut_by[d].get(ex)
        cc = cash.get(d)
        if not fc or not cc or cc <= 0:
            continue
        b = (fc - cc) / cc * 1e4
        basis_levels.append(b)
        # within-contract change only: a position never holds through a roll
        # (flat overnight, contract fixed at entry) — roll days are excluded
        # from the |Δ| distribution to avoid term-spread jump artifacts.
        if prev_b is not None and prev_ex == ex:
            basis_changes.append(abs(b - prev_b))
        elif prev_b is not None:
            n_roll_days += 1
        prev_b, prev_ex = b, ex
        n_basis += 1

    roll_by_year = {}
    for rd, near_exp, next_exp in roll_dates:
        roll_by_year[str(rd.year)] = roll_by_year.get(str(rd.year), 0) + 1

    # ---- report ----------------------------------------------------------------
    snap = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "valid_sessions": valid_sessions,
        "skipped_stamp_mismatch": skipped_stamp,
        "slippage_bp": slip,
        "basis_bp": {"n": n_basis, "n_roll_days_excluded": n_roll_days,
                     "level": pct_dist(basis_levels),
                     "abs_daily_change_within_contract":
                         pct_dist(basis_changes)},
        "roll_dates_total": len(roll_dates),
        "roll_dates_by_year": roll_by_year,
        "cadence_by_year": {"cell1_entry31": cadence[31],
                            "cell2_entry46": cadence[46]},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "cost_substrate_measurements.json").write_text(
        json.dumps(snap, indent=1), encoding="utf-8")

    def f(x):
        return f"{x:.2f}" if isinstance(x, float) else str(x)

    lines = [
        "# A — Phase-1 F&O Cost-Substrate Measurements",
        "",
        f"Generated: {snap['generated']} · runtime {time.time() - t0:.0f}s · "
        f"valid sessions {valid_sessions} · stamp-mismatch skipped "
        f"{skipped_stamp}",
        "",
        "**Read boundary:** raw bars + microstructure only; no construct "
        "signal, no P&L (per A_CONSTRUCT_DEFINITION.md).",
        "",
        "## A. Slippage (bar-open vs prior-bar-close drift, bp)",
        "",
        "| Era | Measure | p50 | p90 | p99 | max |",
        "|---|---|---:|---:|---:|---:|",
        f"| vendor | pooled all bars | {f(slip['vendor']['pooled_bp']['p50'])} | "
        f"{f(slip['vendor']['pooled_bp']['p90'])} | "
        f"{f(slip['vendor']['pooled_bp']['p99'])} | "
        f"{f(slip['vendor']['pooled_bp']['max'])} |",
        f"| vendor | entry bar 31 (cell 1) | {f(slip['vendor']['entry31_bp']['p50'])} | "
        f"{f(slip['vendor']['entry31_bp']['p90'])} | "
        f"{f(slip['vendor']['entry31_bp']['p99'])} | "
        f"{f(slip['vendor']['entry31_bp']['max'])} |",
        f"| vendor | entry bar 46 (cell 2) | {f(slip['vendor']['entry46_bp']['p50'])} | "
        f"{f(slip['vendor']['entry46_bp']['p90'])} | "
        f"{f(slip['vendor']['entry46_bp']['p99'])} | "
        f"{f(slip['vendor']['entry46_bp']['max'])} |",
        f"| native | pooled all bars | {f(slip['native']['pooled_bp']['p50'])} | "
        f"{f(slip['native']['pooled_bp']['p90'])} | "
        f"{f(slip['native']['pooled_bp']['p99'])} | "
        f"{f(slip['native']['pooled_bp']['max'])} |",
        f"| native | entry bar 31 (cell 1) | {f(slip['native']['entry31_bp']['p50'])} | "
        f"{f(slip['native']['entry31_bp']['p90'])} | "
        f"{f(slip['native']['entry31_bp']['p99'])} | "
        f"{f(slip['native']['entry31_bp']['max'])} |",
        f"| native | entry bar 46 (cell 2) | {f(slip['native']['entry46_bp']['p50'])} | "
        f"{f(slip['native']['entry46_bp']['p90'])} | "
        f"{f(slip['native']['entry46_bp']['p99'])} | "
        f"{f(slip['native']['entry46_bp']['max'])} |",
        "",
        "Entry slippage lane: p90 of the entry-bar drift per era per cell. "
        "Exit lane: the ISD convention — exit at the last bar close pays the "
        "same band.",
        "",
        "## B. Basis (near-month Nifty futures vs official cash, bp)",
        "",
        "| Statistic | Level (bp) | |Δ daily|, within-contract (bp) |",
        "|---|---:|---:|",
        f"| n | {n_basis} | {n_basis - n_roll_days} (roll days excluded: "
        f"{n_roll_days}) |",
        f"| p50 | {f(snap['basis_bp']['level']['p50'])} | "
        f"{f(snap['basis_bp']['abs_daily_change_within_contract']['p50'])} |",
        f"| p90 | {f(snap['basis_bp']['level']['p90'])} | "
        f"{f(snap['basis_bp']['abs_daily_change_within_contract']['p90'])} |",
        f"| p99 | {f(snap['basis_bp']['level']['p99'])} | "
        f"{f(snap['basis_bp']['abs_daily_change_within_contract']['p99'])} |",
        f"| max | {f(snap['basis_bp']['level']['max'])} | "
        f"{f(snap['basis_bp']['abs_daily_change_within_contract']['max'])} |",
        "",
        "**Basis treatment (D5 input) — mean vs dispersion.** The basis change "
        "over a hold splits into: (1) a MEAN component = the carry drift over "
        "the hold — for a ~5.7h hold at ~6% carry, ~0.4 bp/trade (direction-"
        "dependent; a long position loses the carry decay, a short gains it; "
        "for the alternating sign book it nearly nets out) — immaterial to the "
        "net-spread gate; (2) a DISPERSION component = basis noise over the "
        "hold. The measurable bound is the full-day within-contract |Δ| p90 "
        "of 19.2 bp; the intraday-hold value is unmeasurable pre-2023 (no "
        "futures 1m) and is expected to be smaller (the full-day measure "
        "includes overnight basis gaps an intraday hold avoids; futures and "
        "cash move together tick-by-tick intraday). The noise is INVISIBLE to "
        "a cash-series backtest, so it does not enter the net-spread gate as a "
        "cost — it enters the RFA as a Sharpe/power disclosure: the declared "
        "per-trade effect must be defended against a basis-noise floor of "
        "~19 bp/day (full-day bound). A cheap forward probe (live futures LTP "
        "vs cash index over actual hold windows, ~30 sessions) can measure the "
        "intraday value on the native era. Pre-2016 spans hold the 2016+ "
        "figures as the disclosed assumption.",
        "",
        "## C. Roll calendar (volume-dominance, NIFTY FUTIDX)",
        "",
        f"Total roll dates: {len(roll_dates)} ({min(str(r[0]) for r in roll_dates)} "
        f"-> {max(str(r[0]) for r in roll_dates)}); by year: "
        f"{', '.join(f'{k}:{v}' for k, v in sorted(roll_by_year.items()))}",
        "",
        "Roll executes at entry-time instrument selection (flat overnight — "
        "0 roll legs; the basis lane covers the discrepancy).",
        "",
        "## D. Cadence (tradeable sessions per year)",
        "",
        "| Year | cell 1 (entry bar 31) | cell 2 (entry bar 46) |",
        "|---|---:|---:|",
    ]
    for y in sorted(set(cadence[31]) | set(cadence[46])):
        lines.append(
            f"| {y} | {cadence[31].get(y, 0)} | {cadence[46].get(y, 0)} |")
    lines += [
        "",
        "Cadence per year = sessions passing the session-validity rule with "
        "the entry bar present. Trades/year for the RFA cadence figure: mean "
        f"of the cell-1 column across 2012-2026 "
        f"({sum(cadence[31].values()) / 15:.0f}/yr).",
        "",
        "Snapshot: `data/a_index_intraday/cost_substrate_measurements.json`",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"valid sessions {valid_sessions}, stamp-skip {skipped_stamp}")
    print("slippage entry31 vendor/native p90:",
          slip["vendor"]["entry31_bp"]["p90"], slip["native"]["entry31_bp"]["p90"])
    print("basis n", n_basis, "p90 level", snap["basis_bp"]["level"]["p90"],
          "p90 |d| within-contract",
          snap["basis_bp"]["abs_daily_change_within_contract"]["p90"])
    print("rolls", len(roll_dates), "->", REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
