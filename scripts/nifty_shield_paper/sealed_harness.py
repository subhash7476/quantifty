#!/usr/bin/env python
"""
Sealed NiftyShield Validation Harness
======================================
Self-contained script — reads 1m bars + options chain, runs DayType engine,
selects structures, simulates entry at 13:00 and exit management to 15:15.

Usage:
    # Single CSV (all dates in one file — loads into memory once)
    python run.py --bars-dir bars/ --options-file options/dhan_historical.csv --start 2025-01-01

    # Per-date files in a directory
    python run.py --bars-dir bars/ --options-dir options/ --start 2025-01-01 --end 2025-12-31

Expected directory layout (sealed folder root):
    run.py
    core/
      __init__.py
      state/
        __init__.py
        daytype_engine.py     # from F:\Nifty\core\state\
      analytics/
        __init__.py
        day_features.py        # from F:\Nifty\core\analytics\
        resampler.py           # from F:\Nifty\core\analytics\
    models/
      logistic_13pm_prod/
        model.pkl
        scaler.pkl
        metadata.json
    bars/
      {YYYY-MM-DD}.duckdb      # 1m Nifty + BankNifty OHLC
    options/
      *.csv                    # 1m Nifty options chain
    output/
      (generated)
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Optional

import duckdb
import numpy as np
import pandas as pd

# ── Path setup ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.state.daytype_engine import DayTypeEngine

# ── Constants ───────────────────────────────────────────────────────────────────

NF_SYMBOL  = "NSE_INDEX|Nifty 50"
BN_SYMBOL  = "NSE_INDEX|Nifty Bank"

ENTRY_HOUR, ENTRY_MINUTE = 13, 0         # 13:00 IST
EXIT_HOUR,  EXIT_MINUTE  = 15, 15        # 15:15 IST

# Structure selection (from nifty_shield_v1/config.py)
VIX_SKIP_ABOVE      = 20.0
VIX_REDUCE_ABOVE    = 16.0
IRON_FLY_VIX_ABOVE  = 14.0
DIRECTIONAL_WING_PTS = 150               # bull_put / bear_call wing distance
STRANGLE_OTM_PTS     = 50                # strangle OTM distance
WING_OFFSET_PTS      = 100               # iron fly wings

PROFIT_TARGET_PCT    = 0.50              # TP at 50% of credit received
STOP_LOSS_MULTIPLIER = 2.0               # SL at 2x credit received
LOT_SIZE             = 75                # Nifty contract

# Strike interval for Nifty index options
STRIKE_INTERVAL = 50

UTC_OFFSET = time(3, 45)   # 03:45 UTC = 09:15 IST (NSE open + 5:30 IST offset)
# The timestamp in options CSV is UTC+0. IST = UTC + 5:30.
# So 13:00 IST = 07:30 UTC, 15:15 IST = 09:45 UTC.
ENTRY_UTC = time(7, 30)
EXIT_UTC  = time(9, 45)


# ── Bar loading ─────────────────────────────────────────────────────────────────

def load_bars(session_date: date, bars_dir: Path) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Load 1m Nifty + BankNifty bars for a session date. Returns (nf_df, bn_df)."""
    db_path = bars_dir / f"{session_date.isoformat()}.duckdb"
    if not db_path.exists():
        return None, None

    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except Exception:
        return None, None

    nf = _load_symbol(con, NF_SYMBOL)
    bn = _load_symbol(con, BN_SYMBOL)
    con.close()

    if nf is None or nf.empty or bn is None or bn.empty:
        return None, None

    # Filter to session hours: 9:15 (555 min) to 15:30 (930 min)
    nf = _filter_session(nf)
    bn = _filter_session(bn)

    # Require at least 100 bars for 13:00 checkpoint
    if len(nf) < 100 or len(bn) < 100:
        return None, None

    return nf, bn


def _load_symbol(con: duckdb.DuckDBPyConnection, symbol: str) -> pd.DataFrame | None:
    try:
        df = con.execute(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol = ? ORDER BY timestamp",
            [symbol],
        ).df()
        if df.empty:
            return None
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception:
        return None


def _filter_session(df: pd.DataFrame) -> pd.DataFrame:
    hm = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    return df[(hm >= 555) & (hm <= 929)].reset_index(drop=True)


# ── Options chain ───────────────────────────────────────────────────────────────

_chain_cache: pd.DataFrame | None = None
_cache_source: str | None = None


def load_full_chain(path: str) -> pd.DataFrame:
    """Load a single master CSV into memory once. Caches globally."""
    global _chain_cache, _cache_source
    if _cache_source == path and _chain_cache is not None:
        return _chain_cache
    print(f"Loading options chain from {path} ...")
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    _chain_cache = df
    _cache_source = path
    return df


def get_date_chain(full_chain: pd.DataFrame | None, options_path: Path,
                   session_date: date) -> pd.DataFrame | None:
    """Return options chain rows for a single session date.
    If full_chain is provided (single CSV mode), filter from it.
    Otherwise search per-date files in options_path.
    """
    if full_chain is not None:
        mask = full_chain["timestamp"].dt.date == session_date
        df = full_chain[mask]
        return df if not df.empty else None

    # Per-date file mode — try DuckDB first, then CSV
    date_str = session_date.isoformat()
    db_path = options_path / f"{date_str}.duckdb"
    if db_path.exists():
        try:
            con = duckdb.connect(str(db_path), read_only=True)
            df = con.execute("SELECT * FROM options").df()
            con.close()
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        except Exception:
            pass

    for f in sorted(options_path.glob(f"*{date_str}*")):
        if f.suffix == ".csv":
            try:
                return pd.read_csv(f, parse_dates=["timestamp"])
            except Exception:
                return None
    return None


def get_atm_strike(chain: pd.DataFrame, entry_ts: pd.Timestamp) -> float:
    """Find the ATM strike at the entry timestamp (closest to spot)."""
    row = chain[(chain["timestamp"] == entry_ts) & (chain["strike_relative"] == "ATM")]
    if row.empty:
        # Fallback: use spot_price to find nearest strike in the chain
        spot = chain.loc[chain["timestamp"] == entry_ts, "spot_price"].iloc[0]
        strikes = chain.loc[chain["timestamp"] == entry_ts, "strike_price"].dropna().unique()
        return float(strikes[np.argmin(np.abs(strikes - spot))])
    return float(row["strike_price"].iloc[0])


def get_option_price(chain: pd.DataFrame, ts: pd.Timestamp,
                     option_type: str, strike: float) -> float | None:
    """Get the close price for a specific option at a timestamp."""
    match = chain[
        (chain["timestamp"] == ts)
        & (chain["option_type"] == option_type)
        & (chain["strike_price"] == strike)
        & (chain["expiry_code"] == 1)
    ]
    if match.empty:
        return None
    return float(match["close"].iloc[0])


def get_atm_iv(chain: pd.DataFrame, ts: pd.Timestamp) -> float | None:
    """Get ATM CE IV as VIX proxy."""
    match = chain[
        (chain["timestamp"] == ts)
        & (chain["strike_relative"] == "ATM")
        & (chain["option_type"] == "CE")
        & (chain["expiry_code"] == 1)
    ]
    if match.empty or pd.isna(match["iv"].iloc[0]):
        return None
    return float(match["iv"].iloc[0])


def resolve_strike(atm: float, offset_pts: int, chain: pd.DataFrame,
                   ts: pd.Timestamp) -> float | None:
    """Find the nearest strike to (atm + offset_pts * sign)."""
    target = round((atm + offset_pts) / STRIKE_INTERVAL) * STRIKE_INTERVAL
    available = chain.loc[
        (chain["timestamp"] == ts) & (chain["expiry_code"] == 1),
        "strike_price"
    ].dropna().unique()
    if len(available) == 0:
        return None
    return float(available[np.argmin(np.abs(available - target))])


# ── Structure selection ─────────────────────────────────────────────────────────

def select_structure(regime: str, vix: float) -> dict | None:
    """Map regime + VIX to structure definition. Returns None if VIX skip."""
    if vix > VIX_SKIP_ABOVE:
        return None

    if regime == "BullTrend":
        return {
            "name": "bull_put_spread",
            "legs": [
                {"type": "PE", "offset": 0, "side": "sell"},       # short ATM PE
                {"type": "PE", "offset": DIRECTIONAL_WING_PTS, "side": "buy"},  # long wing PE
            ],
        }
    elif regime == "BearTrend":
        return {
            "name": "bear_call_spread",
            "legs": [
                {"type": "CE", "offset": 0, "side": "sell"},       # short ATM CE
                {"type": "CE", "offset": DIRECTIONAL_WING_PTS, "side": "buy"},  # long wing CE
            ],
        }
    else:  # Choppy
        if vix > VIX_REDUCE_ABOVE:
            return {
                "name": "short_strangle",
                "legs": [
                    {"type": "CE", "offset": STRANGLE_OTM_PTS, "side": "sell"},
                    {"type": "PE", "offset": -STRANGLE_OTM_PTS, "side": "sell"},
                ],
            }
        elif vix > IRON_FLY_VIX_ABOVE:
            return {
                "name": "iron_fly",
                "legs": [
                    {"type": "CE", "offset": 0, "side": "sell"},               # short ATM CE
                    {"type": "PE", "offset": 0, "side": "sell"},               # short ATM PE
                    {"type": "CE", "offset": WING_OFFSET_PTS, "side": "buy"},  # long wing CE
                    {"type": "PE", "offset": -WING_OFFSET_PTS, "side": "buy"}, # long wing PE
                ],
            }
        else:
            return {
                "name": "short_straddle",
                "legs": [
                    {"type": "CE", "offset": 0, "side": "sell"},
                    {"type": "PE", "offset": 0, "side": "sell"},
                ],
            }


# ── Session simulation ──────────────────────────────────────────────────────────

def get_timestamps_for_date(chain: pd.DataFrame, session_date: date) -> dict:
    """Build mapping of IST times to UTC timestamps present in the chain for a date."""
    df_date = chain[chain["timestamp"].dt.date == session_date]
    if df_date.empty:
        return {}

    ts_map = {}
    for _, row in df_date.iterrows():
        t = row["timestamp"]
        ist = t + pd.Timedelta(hours=5, minutes=30)
        ts_map[(ist.hour, ist.minute)] = t

    return ts_map


def simulate_session(session_date: date, engine: DayTypeEngine,
                     bars_dir: Path, options_path: Path,
                     full_chain: pd.DataFrame | None = None) -> dict | None:
    """Run one session: classify regime, select structure, simulate entry + exit."""
    # Load bars and run engine
    nf, bn = load_bars(session_date, bars_dir)
    if nf is None:
        return None

    engine.reset(session_date)
    bn_dicts = [row.to_dict() for _, row in bn.iterrows()]
    nf_dicts = [row.to_dict() for _, row in nf.iterrows()]

    state = None
    max_len = max(len(bn_dicts), len(nf_dicts))
    for i in range(max_len):
        if i < len(bn_dicts):
            engine.on_bn_bar(bn_dicts[i])
        if i < len(nf_dicts):
            result = engine.on_bar(nf_dicts[i])
            if result is not None and result.predicted_state != "Unknown":
                state = result

    if state is None or state.predicted_state == "Unknown":
        return {"date": str(session_date), "status": "skip", "reason": "no_regime"}

    # Load options chain
    chain = get_date_chain(full_chain, options_path, session_date)
    if chain is None:
        return {"date": str(session_date), "status": "skip", "reason": "no_options_data"}

    # Find 13:00 IST entry timestamp in chain
    entry_ist = (ENTRY_HOUR, ENTRY_MINUTE)
    ts_map = get_timestamps_for_date(chain, session_date)
    if entry_ist not in ts_map:
        return {"date": str(session_date), "status": "skip", "reason": "no_13:00_bar"}

    entry_ts = ts_map[entry_ist]

    # Find exit timestamps: 13:01 through 15:15
    exit_timestamps = []
    for h in range(ENTRY_HOUR, EXIT_HOUR + 1):
        start_m = ENTRY_MINUTE + 1 if h == ENTRY_HOUR else 0
        end_m = EXIT_MINUTE if h == EXIT_HOUR else 59
        for m in range(start_m, end_m + 1):
            if (h, m) in ts_map:
                exit_timestamps.append(ts_map[(h, m)])

    # ── ATM & VIX ───────────────────────────────────────────────────────────
    atm = get_atm_strike(chain, entry_ts)
    vix_proxy = get_atm_iv(chain, entry_ts)
    if vix_proxy is None:
        return {"date": str(session_date), "status": "skip", "reason": "no_iv"}

    vix_pct = vix_proxy  # IV is already in percentage units

    # ── Structure selection ─────────────────────────────────────────────────
    structure = select_structure(state.predicted_state, vix_pct)
    if structure is None:
        return {"date": str(session_date), "status": "skip",
                "reason": f"vix_skip ({vix_pct:.1f} > {VIX_SKIP_ABOVE})"}

    # ── Resolve leg strikes & entry prices ──────────────────────────────────
    legs = []
    total_credit = 0.0
    for leg_def in structure["legs"]:
        strike = atm if leg_def["offset"] == 0 else resolve_strike(
            atm, leg_def["offset"], chain, entry_ts
        )
        if strike is None:
            return {"date": str(session_date), "status": "skip",
                    "reason": f"no_strike for {leg_def}"}

        price = get_option_price(chain, entry_ts, leg_def["type"], strike)
        if price is None:
            return {"date": str(session_date), "status": "skip",
                    "reason": f"no_price for {leg_def['type']} {strike}"}

        multiplier = -1 if leg_def["side"] == "sell" else 1
        legs.append({
            "type": leg_def["type"],
            "strike": strike,
            "side": leg_def["side"],
            "entry_price": price,
        })
        total_credit += price * multiplier

    # Net credit received by the seller; positive = credit, negative = debit
    net_credit = -total_credit  # from seller's perspective

    if net_credit <= 0:
        return {"date": str(session_date), "status": "skip", "reason": "no_credit"}

    # ── Targets ─────────────────────────────────────────────────────────────
    tp_amount  = net_credit * PROFIT_TARGET_PCT   # group P&L target
    sl_amount  = net_credit * STOP_LOSS_MULTIPLIER  # group P&L stop

    # ── Exit simulation ─────────────────────────────────────────────────────
    exit_prices = {}
    exit_ts      = None
    exit_reason  = "time_exit"
    final_pnl    = 0.0

    for ts in exit_timestamps:
        group_pnl = 0.0
        current_prices = {}
        all_priced = True
        for leg in legs:
            px = get_option_price(chain, ts, leg["type"], leg["strike"])
            if px is None:
                all_priced = False
                break
            current_prices[leg["type"] + str(leg["strike"])] = px
            multiplier = 1 if leg["side"] == "sell" else -1
            group_pnl += (leg["entry_price"] - px) * multiplier

        if not all_priced:
            continue

        # TP: group P&L >= 50% of credit
        if group_pnl >= tp_amount:
            exit_prices = current_prices
            exit_ts = ts
            exit_reason = "profit_target"
            final_pnl = group_pnl
            break

        # SL: group P&L <= -2x credit
        if group_pnl <= -sl_amount:
            exit_prices = current_prices
            exit_ts = ts
            exit_reason = "stop_loss"
            final_pnl = group_pnl
            break

        # Keep track of last successfully priced bar for time exit fallback
        exit_prices = current_prices
        exit_ts = ts
        final_pnl = group_pnl

    if exit_ts is None:
        return {"date": str(session_date), "status": "skip",
                "reason": "no_exit_timestamps"}

    pnl_rs = final_pnl * LOT_SIZE

    return {
        "date": str(session_date),
        "status": "traded",
        "regime": state.predicted_state,
        "confidence": state.confidence,
        "vix": round(vix_pct, 2),
        "structure": structure["name"],
        "atm": atm,
        "net_credit": round(net_credit, 2),
        "entry_time": str(entry_ts),
        "exit_time": str(exit_ts),
        "exit_reason": exit_reason,
        "pnl_pts": round(final_pnl, 2),
        "pnl_rs": round(pnl_rs, 2),
        "legs": legs,
        "exit_prices": exit_prices,
    }


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NiftyShield sealed validation")
    parser.add_argument("--bars-dir", required=True, help="Path to 1m DuckDB bars")
    parser.add_argument("--options-file", default=None, help="Single options CSV (all dates). Overrides --options-dir.")
    parser.add_argument("--options-dir", default="options", help="Directory of per-date options CSVs (ignored if --options-file set)")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    bars_dir    = Path(args.bars_dir)
    options_path = Path(args.options_file) if args.options_file else Path(args.options_dir)
    output_dir  = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    full_chain = load_full_chain(args.options_file) if args.options_file else None

    # ── Date range ──────────────────────────────────────────────────────────
    bar_dates = sorted(
        date.fromisoformat(p.stem)
        for p in bars_dir.glob("*.duckdb")
    )
    start = date.fromisoformat(args.start) if args.start else bar_dates[0]
    end   = date.fromisoformat(args.end)   if args.end   else bar_dates[-1]
    dates = [d for d in bar_dates if start <= d <= end]
    print(f"Simulating {len(dates)} sessions: {dates[0]} → {dates[-1]}")

    # ── Init engine ─────────────────────────────────────────────────────────
    # The DayTypeEngine auto-resolves ROOT/MODEL_DIR/FEATURE_DIR relative to
    # its own file location inside the sealed folder. No monkey-patching needed.
    engine = DayTypeEngine(model_name="logistic", eod_feature_path=None)

    # ── Run sessions ────────────────────────────────────────────────────────
    trades = []
    skipped = {"no_regime": 0, "no_options_data": 0, "no_13:00_bar": 0,
               "no_iv": 0, "vix_skip": 0, "no_strike": 0, "no_price": 0,
               "no_credit": 0, "no_exit_timestamps": 0}

    for i, d in enumerate(dates):
        if i % 50 == 0:
            print(f"  {d} ({i}/{len(dates)})")

        result = simulate_session(d, engine, bars_dir, options_path, full_chain)
        if result is None:
            continue

        if result["status"] == "skip":
            reason = result.get("reason", "unknown")
            skipped[reason] = skipped.get(reason, 0) + 1
        else:
            trades.append(result)

    # ── Write trade list ────────────────────────────────────────────────────
    if trades:
        trade_rows = []
        for t in trades:
            legs_str = "; ".join(
                f"{l['side']} {l['type']} {l['strike']} @ {l['entry_price']}"
                for l in t["legs"]
            )
            trade_rows.append({
                "date": t["date"],
                "regime": t["regime"],
                "confidence": t["confidence"],
                "vix": t["vix"],
                "structure": t["structure"],
                "atm": t["atm"],
                "net_credit": t["net_credit"],
                "legs": legs_str,
                "entry_time": t["entry_time"],
                "exit_time": t["exit_time"],
                "exit_reason": t["exit_reason"],
                "pnl_pts": t["pnl_pts"],
                "pnl_rs": t["pnl_rs"],
            })

        df_trades = pd.DataFrame(trade_rows)
        trade_path = output_dir / "trade_list.csv"
        df_trades.to_csv(trade_path, index=False)
        print(f"\nTrade list: {trade_path} ({len(trades)} trades)")

        # ── Summary ────────────────────────────────────────────────────────
        pnl_series = df_trades["pnl_rs"]
        wins = (pnl_series > 0).sum()
        losses = (pnl_series <= 0).sum()

        # Sharpe (assuming zero risk-free rate)
        mean_pnl = pnl_series.mean()
        std_pnl  = pnl_series.std()
        sharpe = (mean_pnl / std_pnl * math.sqrt(252)) if std_pnl > 0 else 0

        # Max drawdown
        cumsum = pnl_series.cumsum()
        running_max = cumsum.cummax()
        drawdown = cumsum - running_max
        max_dd = float(drawdown.min())

        summary = {
            "total_trades": len(trades),
            "period": f"{dates[0]} → {dates[-1]}",
            "total_pnl_rs": round(float(pnl_series.sum()), 2),
            "mean_pnl_rs": round(float(mean_pnl), 2),
            "std_pnl_rs": round(float(std_pnl), 2),
            "sharpe": round(sharpe, 4),
            "max_drawdown_rs": round(max_dd, 2),
            "win_rate": round(wins / len(trades), 4) if trades else 0,
            "wins": int(wins),
            "losses": int(losses),
            "by_regime": {
                regime: {
                    "count": int((df_trades["regime"] == regime).sum()),
                    "total_pnl": round(float(df_trades.loc[df_trades["regime"] == regime, "pnl_rs"].sum()), 2),
                    "win_rate": round(float((df_trades.loc[df_trades["regime"] == regime, "pnl_rs"] > 0).mean()), 4),
                }
                for regime in sorted(df_trades["regime"].unique())
            },
            "by_structure": {
                structure: {
                    "count": int((df_trades["structure"] == structure).sum()),
                    "total_pnl": round(float(df_trades.loc[df_trades["structure"] == structure, "pnl_rs"].sum()), 2),
                    "win_rate": round(float((df_trades.loc[df_trades["structure"] == structure, "pnl_rs"] > 0).mean()), 4),
                }
                for structure in sorted(df_trades["structure"].unique())
            },
            "exit_reasons": {
                reason: int((df_trades["exit_reason"] == reason).sum())
                for reason in sorted(df_trades["exit_reason"].unique())
            },
            "skipped": skipped,
        }

        summary_path = output_dir / "summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Summary:     {summary_path}")

        # Print summary
        print(f"\n{'='*50}")
        print(f"Trades: {summary['total_trades']}  |  Win rate: {summary['win_rate']:.1%}")
        print(f"Total P&L: ₹{summary['total_pnl_rs']:,.0f}  |  Mean: ₹{summary['mean_pnl_rs']:,.0f}/trade")
        print(f"Sharpe: {summary['sharpe']:.2f}  |  Max DD: ₹{summary['max_drawdown_rs']:,.0f}")
        print(f"\nSkipped: {sum(skipped.values())} sessions")
        for reason, count in sorted(skipped.items()):
            if count > 0:
                print(f"  {reason}: {count}")
        print(f"{'='*50}")
    else:
        print("\nNo trades generated.")
        print(f"Skipped: {sum(skipped.values())} sessions")
        for reason, count in sorted(skipped.items()):
            if count > 0:
                print(f"  {reason}: {count}")


if __name__ == "__main__":
    main()
