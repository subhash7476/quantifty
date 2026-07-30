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

MAX_SPREAD_PCT = 0.05
STRIKE_BAND = 3
MIN_VOLUME_FALLBACK = 1

_EOD_ONLY = object()


def screen_candidate(bid, ask, oi, volume, min_oi, min_volume, max_spread_pct):
    if bid is None or ask is None or bid <= 0 or ask <= 0:
        return False, None, "no quote"
    mid = (bid + ask) / 2.0
    spread_pct = (ask - bid) / mid
    if oi is None or oi < min_oi:
        return False, spread_pct, f"OI {oi} < {min_oi}"
    if volume is None or volume < min_volume:
        return False, spread_pct, f"vol {volume} < {min_volume}"
    if spread_pct > max_spread_pct:
        return False, spread_pct, f"spread {spread_pct:.1%} > {max_spread_pct:.0%}"
    return True, spread_pct, None


def pick_screened_strike(candidates, forward, min_oi, min_volume, max_spread_pct):
    passing = []
    last_reason = None
    for c in candidates:
        ok, spread_pct, reason = screen_candidate(
            c.get("bid"), c.get("ask"), c.get("oi"), c.get("volume"),
            min_oi, min_volume, max_spread_pct)
        c["spread_pct"] = spread_pct
        if ok:
            passing.append(c)
        else:
            last_reason = reason
    if not passing:
        return None, last_reason or "no candidate passed"
    chosen = min(passing, key=lambda c: (abs(c["strike"] - forward), c["spread_pct"]))
    return chosen, None


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


def _band_candidates(o, ticker, opt_type, expiry, odate, forward):
    chain = o.execute(
        "SELECT strike, settle, open_int FROM stock_options_bhavcopy "
        "WHERE underlying=? AND expiry_dt=? AND option_type=? AND trade_date=? "
        "ORDER BY strike",
        [ticker, expiry, opt_type, odate],
    ).fetchall()
    if not chain:
        return []
    strikes = [r[0] for r in chain]
    nearest = min(range(len(strikes)), key=lambda i: abs(strikes[i] - forward))
    lo, hi = max(0, nearest - STRIKE_BAND), min(len(chain), nearest + STRIKE_BAND + 1)
    return chain[lo:hi]


def _base_row(ticker, direction, opt_type):
    return {
        "ticker": ticker, "direction": direction, "opt_type": opt_type,
        "expiry": None, "strike": None, "settle": None, "oi": None,
        "forward": None, "lot_size": None, "instrument_key": None,
        "tradingsymbol": None, "quote_date": None, "snapped": False,
        "nearest_strike": None, "premium_cost": None,
        "anchor_source": None, "screen": "skipped", "spread_pct": None,
        "live_oi": None, "live_volume": None, "best_bid": None, "best_ask": None,
        "screen_reason": None,
    }


def _resolve_instrument(inst, snap, ticker, opt_type, strike, expiry):
    name = inst.execute(
        "SELECT name FROM instruments WHERE snapshot_date=? "
        "AND instrument_type='EQ' AND tradingsymbol=? LIMIT 1",
        [snap, ticker],
    ).fetchone()
    if not name:
        return None, None, None
    r = inst.execute(
        "SELECT instrument_key, tradingsymbol, lot_size FROM instruments "
        "WHERE snapshot_date=? AND name=? AND instrument_type=? "
        "AND strike=? AND expiry=? LIMIT 1",
        [snap, name[0], opt_type, strike, expiry.isoformat()],
    ).fetchone()
    return (r[0], r[1], r[2]) if r else (None, None, None)


def _fill_eod(o, inst, snap, row, forward):
    expiry = row["expiry"]
    sel = select_option(o, row["ticker"], row["opt_type"], expiry, forward)
    if sel is None:
        return
    key, tsym, lot = _resolve_instrument(
        inst, snap, row["ticker"], row["opt_type"], sel["strike"], expiry)
    row.update({
        "strike": sel["strike"], "settle": sel["settle"], "oi": sel["oi"],
        "forward": sel["forward"], "quote_date": sel["quote_date"],
        "snapped": sel["snapped"], "nearest_strike": sel["nearest_strike"],
        "lot_size": lot, "instrument_key": key, "tradingsymbol": tsym,
        "premium_cost": (sel["settle"] * lot) if (lot and sel["settle"]) else None,
        "screen": "skipped",
    })
    if row["anchor_source"] is None:
        row["anchor_source"] = "synthetic" if forward is None else "eod_future"


def _build_contracts(o, f, inst, book, min_dte, today, market_data):
    snap = inst.execute("SELECT MAX(snapshot_date) FROM instruments").fetchone()[0]
    live = market_data is not _EOD_ONLY

    expiries = {t: pick_expiry(o, t, min_dte, today) for t, _ in book}
    live_fwds = {}
    if live:
        live_fwds = _resolve_live_forwards(inst, snap, book, expiries, market_data)

    # Pass A: per-name context + collect candidate option keys for one batch.
    ctx = []
    all_keys = []
    for ticker, direction in book:
        opt_type = "CE" if direction == "LONG" else "PE"
        expiry = expiries.get(ticker)
        row = _base_row(ticker, direction, opt_type)
        if expiry is None:
            ctx.append((row, None))
            continue
        row["expiry"] = expiry

        eod_fut = f.execute(
            "SELECT close FROM futures_bhavcopy WHERE underlying=? AND expiry_dt=? "
            "ORDER BY trade_date DESC LIMIT 1", [ticker, expiry]).fetchone()
        if ticker in live_fwds:
            forward, row["anchor_source"] = live_fwds[ticker], "live"
        elif eod_fut:
            forward, row["anchor_source"] = eod_fut[0], "eod_future"
        else:
            forward, row["anchor_source"] = None, "synthetic"

        if not live or forward is None:
            ctx.append((row, ("EOD", forward)))
            continue

        odate = o.execute(
            "SELECT MAX(trade_date) FROM stock_options_bhavcopy "
            "WHERE underlying=? AND expiry_dt=? AND option_type=?",
            [ticker, expiry, opt_type]).fetchone()[0]
        band = _band_candidates(o, ticker, opt_type, expiry, odate, forward)
        cands = []
        for strike, settle, _eod_oi in band:
            key, tsym, lot = _resolve_instrument(inst, snap, ticker, opt_type, strike, expiry)
            cands.append({"strike": strike, "settle": settle, "key": key,
                          "tsym": tsym, "lot": lot})
            if key:
                all_keys.append(key)
        ctx.append((row, ("LIVE", forward, expiry, odate, opt_type, cands)))

    quotes = {}
    if all_keys:
        quotes = market_data.fetch_quotes_batch(all_keys).get("quotes", {})

    # Pass B: resolve each name to a final row.
    out = []
    for row, c in ctx:
        if c is None:
            out.append(row); continue
        if c[0] == "EOD":
            _fill_eod(o, inst, snap, row, c[1])
            out.append(row); continue

        _, forward, expiry, odate, opt_type, cands = c
        for cand in cands:
            q = quotes.get(cand["key"]) or {}
            cand["bid"], cand["ask"] = q.get("best_bid"), q.get("best_ask")
            cand["oi"], cand["volume"] = q.get("oi"), q.get("volume")
        if not any(cand.get("key") and quotes.get(cand["key"]) for cand in cands):
            _fill_eod(o, inst, snap, row, forward)   # feed miss -> skip screen
            out.append(row); continue

        strikes = [cand["strike"] for cand in cands]
        nearest = min(strikes, key=lambda s: abs(s - forward))
        lot_lookup = {cand["strike"]: cand["lot"] for cand in cands}
        min_vol = lot_lookup.get(nearest) or MIN_VOLUME_FALLBACK
        chosen, reason = pick_screened_strike(
            cands, forward, MIN_OI, min_vol, MAX_SPREAD_PCT)
        row["forward"] = forward
        if chosen is None:
            row["screen"] = "no_tradeable_strike"
            row["screen_reason"] = reason
            out.append(row); continue

        lot = chosen["lot"]
        row.update({
            "strike": chosen["strike"], "settle": chosen["settle"],
            "oi": chosen["oi"], "quote_date": odate,
            "nearest_strike": nearest, "snapped": chosen["strike"] != nearest,
            "screen": "pass" if chosen["strike"] == nearest else "snapped",
            "spread_pct": chosen["spread_pct"], "live_oi": chosen["oi"],
            "live_volume": chosen["volume"], "best_bid": chosen["bid"],
            "best_ask": chosen["ask"], "lot_size": lot,
            "instrument_key": chosen["key"], "tradingsymbol": chosen["tsym"],
            "premium_cost": (chosen["settle"] * lot) if (lot and chosen["settle"]) else None,
        })
        out.append(row)
    return out


def select_book_options(book, min_dte: int = DEFAULT_MIN_DTE, today: date | None = None,
                        market_data=None):
    """Resolve [(ticker, direction), ...] into option contracts.

    direction: "LONG" -> CE, "SHORT" -> PE.
    Returns a list of dicts; a name whose chain or instrument key cannot be
    resolved still yields a row (with nulls) so it stays visible rather than
    silently vanishing from the book.
    """
    if market_data is None:
        from core.brokers.upstox_market_data import UpstoxMarketData
        market_data = UpstoxMarketData()
    o = duckdb.connect(str(OPT_DB), read_only=True)
    f = duckdb.connect(str(FUT_DB), read_only=True)
    inst = duckdb.connect(str(INST_DB), read_only=True)
    try:
        return _build_contracts(o, f, inst, book, min_dte, today, market_data)
    finally:
        o.close(); f.close(); inst.close()


def _future_key(inst, snap, ticker, expiry):
    name = inst.execute(
        "SELECT name FROM instruments WHERE snapshot_date=? "
        "AND instrument_type='EQ' AND tradingsymbol=? LIMIT 1",
        [snap, ticker],
    ).fetchone()
    if not name:
        return None
    row = inst.execute(
        "SELECT instrument_key FROM instruments WHERE snapshot_date=? AND name=? "
        "AND instrument_type='FUT' AND expiry=? AND instrument_key LIKE 'NSE_FO%' LIMIT 1",
        [snap, name[0], expiry.isoformat()],
    ).fetchone()
    return row[0] if row else None


def _resolve_live_forwards(inst, snap, book, expiries, market_data):
    key_by_ticker = {}
    for ticker, _ in book:
        expiry = expiries.get(ticker)
        if expiry is None:
            continue
        key = _future_key(inst, snap, ticker, expiry)
        if key:
            key_by_ticker[ticker] = key
    ltps = market_data.fetch_ltp_batch(list(key_by_ticker.values()))
    return {t: ltps[k] for t, k in key_by_ticker.items() if k in ltps}
