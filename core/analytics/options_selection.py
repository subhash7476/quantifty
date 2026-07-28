"""Option contract selection for a directional signal book.

Maps a list of (ticker, direction) signals to tradeable single-stock option
contracts: LONG -> CE, SHORT -> PE.

Rules (shared by the CLI report and the Flask panel so the two cannot drift):
  Expiry — nearest monthly at least `min_dte` days out. Skips the about-to-expire
           contract so the option retains time value.
  Strike — ATM: nearest listed strike to the expiry forward (near-month future
           close). If that strike carries less than MIN_OI open interest it is an
           illiquid half-strike; snap to the nearest strike that has real OI.

Premium/OI here are bhavcopy EOD reference values, not live quotes.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
OPT_DB = ROOT / "data" / "market_data" / "stock_options_bhavcopy.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
INST_DB = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"

MIN_OI = 100
DEFAULT_MIN_DTE = 7


def pick_expiry(o, ticker: str, min_dte: int, today: date | None = None):
    today = today or date.today()
    rows = o.execute(
        "SELECT DISTINCT expiry_dt FROM stock_options_bhavcopy "
        "WHERE underlying=? AND expiry_dt >= ? ORDER BY expiry_dt",
        [ticker, today],
    ).fetchall()
    for (exp,) in rows:
        if (exp - today).days >= min_dte:
            return exp
    return rows[-1][0] if rows else None


def select_option(o, ticker: str, opt_type: str, expiry, forward: float | None):
    """ATM strike for one contract, with the liquidity snap. None if no chain."""
    odate = o.execute(
        "SELECT MAX(trade_date) FROM stock_options_bhavcopy "
        "WHERE underlying=? AND expiry_dt=? AND option_type=?",
        [ticker, expiry, opt_type],
    ).fetchone()[0]
    chain = o.execute(
        "SELECT strike, settle, open_int, contracts FROM stock_options_bhavcopy "
        "WHERE underlying=? AND expiry_dt=? AND option_type=? AND trade_date=? "
        "ORDER BY strike",
        [ticker, expiry, opt_type, odate],
    ).fetchall()
    if not chain:
        return None

    if forward is None:  # synthetic forward via put-call parity
        pcp = o.execute(
            "SELECT strike, MAX(CASE WHEN option_type='CE' THEN settle END) c, "
            "MAX(CASE WHEN option_type='PE' THEN settle END) p "
            "FROM stock_options_bhavcopy "
            "WHERE underlying=? AND expiry_dt=? AND trade_date=? GROUP BY strike "
            "HAVING c IS NOT NULL AND p IS NOT NULL",
            [ticker, expiry, odate],
        ).fetchall()
        if not pcp:
            return None
        b = min(pcp, key=lambda r: abs(r[1] - r[2]))
        forward = b[0] + b[1] - b[2]

    nearest = min(chain, key=lambda r: abs(r[0] - forward))
    chosen = nearest
    if nearest[2] < MIN_OI:
        liquid = [r for r in chain if r[2] >= MIN_OI]
        if liquid:
            chosen = min(liquid, key=lambda r: abs(r[0] - forward))

    strike, settle, oi, vol = chosen
    return {
        "quote_date": odate,
        "forward": forward,
        "strike": strike,
        "settle": settle,
        "oi": oi,
        "volume": vol,
        "snapped": chosen[0] != nearest[0],
        "nearest_strike": nearest[0],
    }


def select_book_options(book, min_dte: int = DEFAULT_MIN_DTE, today: date | None = None):
    """Resolve [(ticker, direction), ...] into option contracts.

    direction: "LONG" -> CE, "SHORT" -> PE.
    Returns a list of dicts; a name whose chain or instrument key cannot be
    resolved still yields a row (with nulls) so it stays visible rather than
    silently vanishing from the book.
    """
    o = duckdb.connect(str(OPT_DB), read_only=True)
    f = duckdb.connect(str(FUT_DB), read_only=True)
    inst = duckdb.connect(str(INST_DB), read_only=True)
    snap = inst.execute("SELECT MAX(snapshot_date) FROM instruments").fetchone()[0]

    out = []
    try:
        for ticker, direction in book:
            opt_type = "CE" if direction == "LONG" else "PE"
            row = {
                "ticker": ticker,
                "direction": direction,
                "opt_type": opt_type,
                "expiry": None, "strike": None, "settle": None, "oi": None,
                "forward": None, "lot_size": None, "instrument_key": None,
                "tradingsymbol": None, "quote_date": None, "snapped": False,
                "nearest_strike": None, "premium_cost": None,
            }
            expiry = pick_expiry(o, ticker, min_dte, today)
            if expiry is None:
                out.append(row)
                continue

            fwd = f.execute(
                "SELECT close FROM futures_bhavcopy WHERE underlying=? AND expiry_dt=? "
                "ORDER BY trade_date DESC LIMIT 1",
                [ticker, expiry],
            ).fetchone()
            sel = select_option(o, ticker, opt_type, expiry, fwd[0] if fwd else None)
            if sel is None:
                row["expiry"] = expiry
                out.append(row)
                continue

            name = inst.execute(
                "SELECT name FROM instruments WHERE snapshot_date=? "
                "AND instrument_type='EQ' AND tradingsymbol=? LIMIT 1",
                [snap, ticker],
            ).fetchone()
            key = lot = tsym = None
            if name:
                r = inst.execute(
                    "SELECT instrument_key, tradingsymbol, lot_size FROM instruments "
                    "WHERE snapshot_date=? AND name=? AND instrument_type=? "
                    "AND strike=? AND expiry=? LIMIT 1",
                    [snap, name[0], opt_type, sel["strike"], expiry.isoformat()],
                ).fetchone()
                if r:
                    key, tsym, lot = r[0], r[1], r[2]

            row.update({
                "expiry": expiry,
                "strike": sel["strike"],
                "settle": sel["settle"],
                "oi": sel["oi"],
                "forward": sel["forward"],
                "quote_date": sel["quote_date"],
                "snapped": sel["snapped"],
                "nearest_strike": sel["nearest_strike"],
                "lot_size": lot,
                "instrument_key": key,
                "tradingsymbol": tsym,
                "premium_cost": (sel["settle"] * lot) if (lot and sel["settle"]) else None,
            })
            out.append(row)
    finally:
        o.close(); f.close(); inst.close()
    return out
