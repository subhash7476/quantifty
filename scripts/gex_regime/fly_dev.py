"""GEX fly Stage B — B1 development read, 2019-02-11 → 2022-12-30.

Spec: docs/superpowers/specs/2026-09-23-gex-fly-stage-b-design.md §7 B1.
Usage: python scripts/gex_regime/fly_dev.py
Reads no trade date >= 2023-01-01.
"""
from __future__ import annotations

import math
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.analytics.gex_history import MAX_DTE, MAX_FWD_DEV, parity_forward  # noqa: E402
from core.analytics.iron_fly import (  # noqa: E402
    MIN_SESSIONS_LEFT, SPREAD, conservative_mark, exit_reason, leg_costs,
    position_value, select_legs, trade_return, zone_thresholds,
)
from scripts.gex_regime.run_stage_a import (  # noqa: E402
    OPTIONS_DB, REPORT_DIR, WARMUP_DAYS, build_regimes, check_window, load_daily,
)

WINDOW_START, WINDOW_END = date(2019, 2, 11), date(2022, 12, 30)
N_START = date(2018, 1, 1)
LOT_TABLE = ((date(2021, 7, 29), 50), (date(1900, 1, 1), 75))  # by contract expiry
LOT_VALID_BEFORE = date(2024, 1, 1)
ALT_SPREADS = (0.01, 0.04)


def lot_for_expiry(expiry: date) -> int:
    if expiry >= LOT_VALID_BEFORE:
        raise ValueError(f"B1 lot table not verified for expiry {expiry}")
    for start, lot in LOT_TABLE:
        if expiry >= start:
            return lot


@dataclass(frozen=True)
class Market:
    sessions: list
    n: pd.Series
    zones: pd.DataFrame
    chains: dict
    book: dict
    spot: dict

    @classmethod
    def build(cls, sessions, n, zones, options: pd.DataFrame, spot: dict) -> "Market":
        chains = {t: g for t, g in options.groupby("trade_date")}
        book = {(r.trade_date, r.expiry_dt, r.strike, r.option_type): (r.close, r.settle, r.contracts)
                for r in options.itertuples(index=False)}
        return cls(list(sessions), n, zones, chains, book, spot)


@dataclass(frozen=True)
class Position:
    entry: date
    expiry: date
    legs: tuple
    lot: int
    credit: float
    risk: float
    v0: float
    v_prev: float
    prices: tuple
    entry_fees: float
    entry_prem: float


def sessions_left(t: date, expiry: date, sessions: list) -> int:
    n = sum(1 for s in sessions if t < s <= expiry)
    if expiry > sessions[-1]:
        n += len(pd.bdate_range(sessions[-1] + timedelta(days=1), expiry))
    return n


def _open(mkt: Market, t: date, structure: str, daily, spread_unit):
    chain = mkt.chains.get(t)
    if chain is None:
        return "no_chain"
    candidates = sorted(e for e in chain["expiry_dt"].unique()
                        if sessions_left(t, e, mkt.sessions) >= MIN_SESSIONS_LEFT)
    if not candidates:
        return "no_expiry"
    expiry = candidates[0]
    exp_chain = chain[chain["expiry_dt"] == expiry]
    t_years = (expiry - t).days / 365
    fwd = parity_forward(exp_chain, t_years)
    if fwd is None:
        return "no_forward"
    if abs(fwd / mkt.spot[t] - 1) > MAX_FWD_DEV:
        return "fwd_dev"
    sel = select_legs(exp_chain, fwd, t_years, structure)
    if isinstance(sel, str):
        return sel
    legs, width = sel
    rows = [mkt.book.get((t, expiry, leg.strike, leg.option_type)) for leg in legs]
    if any(r is None or r[2] <= 0 for r in rows):
        return "untraded_leg"
    prices = tuple(float(r[0]) for r in rows)
    v0 = position_value(legs, prices)
    credit, risk = -v0, width + v0
    if credit <= 0 or risk <= 0:
        return "bad_credit"
    lot = lot_for_expiry(expiry)
    fees, prem = leg_costs(legs, prices, t, lot, opening=True)
    daily[t] -= fees / risk
    spread_unit[t] += 0.5 * prem / risk
    return Position(t, expiry, legs, lot, credit, risk, v0, v0, prices, fees, prem)


def _step(pos: Position, mkt: Market, t: date, i: int, gated: bool, daily, spread_unit, skips: Counter):
    prices = []
    for leg, prev in zip(pos.legs, pos.prices):
        r = mkt.book.get((t, pos.expiry, leg.strike, leg.option_type))
        if r is None:
            skips["carried_mark"] += 1
            prices.append(prev)
        else:
            prices.append(conservative_mark(r[0], r[1], r[2], leg.side))
    val = position_value(pos.legs, prices)
    daily[t] += (val - pos.v_prev) / pos.risk
    n, p50 = mkt.n.get(t, np.nan), mkt.zones["p50"].get(t, np.nan)
    regime_low = gated and not (np.isnan(n) or np.isnan(p50)) and n < p50
    last = i + 1 >= len(mkt.sessions)
    is_t1 = (not last) and mkt.sessions[i + 1] >= pos.expiry
    pnl = val - pos.v0
    reason = exit_reason(pnl, pos.credit, regime_low, is_t1) or ("window_end" if last else None)
    if reason is None:
        return replace(pos, v_prev=val, prices=tuple(prices)), None
    fees, prem = leg_costs(pos.legs, prices, t, pos.lot, opening=False)
    daily[t] -= fees / pos.risk
    spread_unit[t] += 0.5 * prem / pos.risk
    trade = {"entry": pos.entry, "exit": t, "expiry": pos.expiry, "reason": reason, "credit": pos.credit,
             "risk": pos.risk, "gross": pnl, "fees": pos.entry_fees + fees, "prem": pos.entry_prem + prem}
    return None, trade


def simulate(mkt: Market, structure: str, gated: bool):
    daily = pd.Series(0.0, index=mkt.sessions)
    spread_unit = pd.Series(0.0, index=mkt.sessions)
    trades, skips, pos = [], Counter(), None
    for i, t in enumerate(mkt.sessions):
        if pos is not None:
            pos, trade = _step(pos, mkt, t, i, gated, daily, spread_unit, skips)
            if trade is not None:
                trades.append(trade)
            continue
        if gated:
            n, p67 = mkt.n.get(t, np.nan), mkt.zones["p67"].get(t, np.nan)
            if np.isnan(n) or np.isnan(p67) or n < p67:
                continue
        opened = _open(mkt, t, structure, daily, spread_unit)
        if isinstance(opened, str):
            skips[opened] += 1
        else:
            pos = opened
    return daily, spread_unit, trades, skips


def metrics(daily: pd.Series, spread_unit: pd.Series, trades: list, spread: float) -> dict:
    d = daily - spread * spread_unit
    sd = d.std()
    cum = d.cumsum()
    out = {"sharpe": d.mean() / sd * math.sqrt(250) if sd > 0 else float("nan"),
           "mdd": float((cum - cum.cummax()).min()), "trades": len(trades)}
    if not trades:
        return out
    tr = pd.DataFrame(trades)
    r = pd.Series([trade_return(g, f, p, k, spread) for g, f, p, k in
                   zip(tr["gross"], tr["fees"], tr["prem"], tr["risk"])])
    a = ((tr["gross"] - tr["fees"]) / tr["risk"]).sum()
    b = (0.5 * tr["prem"] / tr["risk"]).sum()
    out.update({"hit": float((r > 0).mean()), "mean_r": float(r.mean()), "median_r": float(r.median()),
                "fee_drag": float((tr["fees"] / tr["risk"]).mean()),
                "spread_drag": float((0.5 * spread * tr["prem"] / tr["risk"]).mean()),
                "breakeven_spread": float(a / b) if b > 0 else float("nan"),
                "hold_sessions": float(np.mean([len(pd.bdate_range(x, y)) - 1
                                                 for x, y in zip(tr["entry"], tr["exit"])]))})
    return out


def load_fly_options(start: date, end: date) -> pd.DataFrame:
    con = duckdb.connect(str(OPTIONS_DB), read_only=True)
    df = con.execute(
        """SELECT trade_date, expiry_dt, strike, option_type, close, settle, contracts, open_int
           FROM option_bhavcopy
           WHERE symbol = 'NIFTY' AND trade_date BETWEEN ? AND ?
             AND expiry_dt > trade_date AND date_diff('day', trade_date, expiry_dt) <= ?""",
        [start, end, MAX_DTE]).df()
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df["expiry_dt"] = pd.to_datetime(df["expiry_dt"]).dt.date
    return df


def _fmt(x, spec):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else format(x, spec)


def _row(label, runs):
    m, lo, hi = runs
    return (f"| {label} | {_fmt(m['sharpe'], '+.2f')} | {m['trades']} | {_fmt(m.get('hit'), '.0%')} | "
            f"{_fmt(m.get('mean_r'), '+.4f')} | {_fmt(m['mdd'], '+.3f')} | {_fmt(m.get('fee_drag'), '.4f')} | "
            f"{_fmt(m.get('spread_drag'), '.4f')} | {_fmt(m.get('breakeven_spread'), '.1%')} | "
            f"{_fmt(lo['sharpe'], '+.2f')} | {_fmt(hi['sharpe'], '+.2f')} | {_fmt(m.get('hold_sessions'), '.1f')} |")


def main() -> None:
    check_window(N_START, WINDOW_END)
    daily_px = load_daily(N_START - timedelta(days=WARMUP_DAYS), WINDOW_END)
    options = load_fly_options(N_START, WINDOW_END)
    spot = dict(zip(daily_px["date"], daily_px["close"]))
    regimes, _ = build_regimes(options, spot)
    all_sessions = [d for d in daily_px["date"] if N_START <= d <= WINDOW_END]
    n = regimes.set_index("date")["net_norm"].reindex(all_sessions)
    zones = zone_thresholds(n)
    window = [d for d in all_sessions if d >= WINDOW_START]
    mkt = Market.build(window, n, zones, options[options["trade_date"] >= WINDOW_START], spot)

    runs = {}
    for label, structure, gated in [("fly, N-gated (primary)", "fly", True), ("fly, ungated", "fly", False),
                                    ("condor, N-gated", "condor", True), ("straddle, N-gated", "straddle", True)]:
        daily, su, trades, skips = simulate(mkt, structure, gated)
        runs[label] = (daily, su, trades, skips,
                       tuple(metrics(daily, su, trades, s) for s in (SPREAD,) + ALT_SPREADS))

    gated, ungated = runs["fly, N-gated (primary)"][4][0], runs["fly, ungated"][4][0]
    stop1 = not gated["sharpe"] > 0
    stop2 = not gated["sharpe"] > ungated["sharpe"]
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()

    lines = [f"# GEX Fly Stage B — B1 development read ({WINDOW_START} → {WINDOW_END})", "",
             "Script-generated by `scripts/gex_regime/fly_dev.py` — do not hand-edit.",
             f"Spec: `docs/superpowers/specs/2026-09-23-gex-fly-stage-b-design.md` · code rev `{rev}`", "",
             "Unit: return on risk (net P&L per unit ÷ max loss per unit). Sharpe = daily mean/sd·√250 over all "
             f"{len(window)} window sessions (0 on flat days). Costs: era fees + spread (2 % primary).", "",
             "## Results", "",
             "| run | Sharpe @2 % | trades | hit | mean R | max DD | fee drag / trade | spread drag / trade | "
             "break-even spread | Sharpe @1 % | Sharpe @4 % | hold (sessions) |",
             "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|"]
    lines += [_row(label, r[4]) for label, r in runs.items()]
    lines += ["", "## Exits and skipped entries", "", "| run | exits by reason | skipped entries / carried marks |",
              "|---|---|---|"]
    for label, r in runs.items():
        exits = Counter(t["reason"] for t in r[2])
        lines.append(f"| {label} | {dict(sorted(exits.items()))} | {dict(sorted(r[3].items()))} |")
    lines += ["", "## Primary run by year (descriptive)", "", "| year | Sharpe @2 % | trades | mean R |",
              "|---|--:|--:|--:|"]
    daily, su, trades = runs["fly, N-gated (primary)"][:3]
    for y in sorted({d.year for d in window}):
        mask = [d.year == y for d in daily.index]
        yt = [t for t in trades if t["entry"].year == y]
        m = metrics(daily[mask], su[mask], yt, SPREAD)
        lines.append(f"| {y} | {_fmt(m['sharpe'], '+.2f')} | {m['trades']} | {_fmt(m.get('mean_r'), '+.4f')} |")
    verdict = "STOP — Stage B ends at B1" if (stop1 or stop2) else "CONTINUE to B2 (Sharpe band + RFA)"
    lines += ["", "## B1 stop rules (spec §7, pinned before this run)", "",
              f"1. gated fly net Sharpe ≤ 0: **{'fires' if stop1 else 'does not fire'}** "
              f"({_fmt(gated['sharpe'], '+.2f')})",
              f"2. gated fly Sharpe ≤ ungated fly Sharpe: **{'fires' if stop2 else 'does not fire'}** "
              f"({_fmt(gated['sharpe'], '+.2f')} vs {_fmt(ungated['sharpe'], '+.2f')})", "",
              f"**B1 verdict: {verdict}**", "",
              "Interpretation rule (spec §2): this is a statement about 2019-02 → 2022-12 history only — "
              "demonstrated / not demonstrated on this window, not a verdict on the construct in today's market.", ""]
    path = REPORT_DIR / "GEX_FLY_B1_DEV.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
