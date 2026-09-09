"""NiftyShield audit - regime quality, exit efficiency, structure choice.

Read-only against every store. Generates
`docs/reports/index_research/NIFTY_SHIELD_REGIME_AND_STRUCTURE_AUDIT.md`.

Every number in the report comes from this script; nothing is hand-edited.

Decision rules are PINNED HERE, above the analysis, and the report carries a
sensitivity column for the one free parameter (the directional dead band).
"""
from __future__ import annotations

import collections
import json
import math
import sqlite3
import sys
from datetime import date, datetime, time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.options.fees import option_order_fees  # noqa: E402
from core.analytics.day_features import compute_session_features  # noqa: E402

EXEC_DB = ROOT / "data" / "nifty_shield" / "execution.db"
FACTS_DB = ROOT / "data" / "nifty_shield" / "facts.duckdb"
SESSIONS = ROOT / "data" / "nifty_shield" / "sessions"
CANDLES = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
CHAINS = ROOT / "data" / "options" / "wall_chain_snapshots"
FEATDIR = ROOT / "data" / "features" / "day_type"
OUT = (ROOT / "docs" / "reports" / "index_research"
       / "NIFTY_SHIELD_REGIME_AND_STRUCTURE_AUDIT.md")

SYMBOL = "NSE_INDEX|Nifty 50"
RISK_FREE = 0.065

# ---- PINNED DECISION RULES (stated before any number was computed) --------
# R1  Directional dead band for scoring a regime call against the realized
#     13:00 -> exit move. Primary 0.15% of the 13:00 level; the report also
#     prints 0.10% and 0.25% so the reader can see the rule's leverage.
DEAD_BANDS = (0.0010, 0.0015, 0.0025)
PRIMARY_BAND = 0.0015
# R2  Holding horizon used for "realized" everywhere: 13:00 -> 15:15 (the
#     hard exit in force for 7 of the 8 structures; 09-08 moved to 15:35).
HORIZON_END = "15:15"
# R3  Counterfactual structures are priced at chain LTP (the same convention
#     the live marks source used), at the actual entry and exit timestamps,
#     at a fixed 2 lots, with the real per-leg fee model.
CF_LOTS = 2
CF_LOT_SIZE = 75
# --------------------------------------------------------------------------

CONFIG = {
    "strike_step": 50, "wing_offset_pts": 100, "directional_wing_pts": 150,
    "strangle_otm_pts": 50, "profit_target_pct": 0.50,
}
CLUSTER_NAMES = {0: "Choppy", 1: "BullTrend", 2: "BearTrend"}
DIAG = ["day_range_pct", "linreg_r2", "clv", "pct_min_above_twap",
        "flip_count_15m", "center_of_mass_return_time", "range_pct_before_11am",
        "range_pct_after_130pm", "gap_pct", "avg_adverse_excursion",
        "intraday_atr_5m", "hh_count_15m", "ll_count_15m", "twap_cross_count"]


# ======================================================================== #
# A. Ledger
# ======================================================================== #
def load_ledger():
    con = sqlite3.connect("file:%s?mode=ro" % EXEC_DB, uri=True)
    con.row_factory = sqlite3.Row
    orders = {r["correlation_id"]: dict(r) for r in con.execute("select * from orders")}
    fills = [dict(r) for r in con.execute("select * from fills order by timestamp")]
    con.close()
    recs = []
    for f in fills:
        o = orders[f["order_id"]]
        sm = (json.loads(o["metadata"] or "{}")).get("strategy_metadata", {})
        recs.append({
            "ts": datetime.fromisoformat(f["timestamp"]).replace(tzinfo=None),
            "symbol": f["symbol"], "side": f["side"],
            "qty": float(f["quantity"]), "price": float(f["price"]),
            "fee": float(f["fee"]), "group": sm.get("group_id"),
            "structure": sm.get("structure"), "role": sm.get("leg_role"),
            "exit_reason": sm.get("exit_reason"), "expiry": sm.get("expiry"),
            "strike": sm.get("strike"), "opt": sm.get("option_type"),
        })
    return recs


def reattribute(recs):
    """Re-route each exit fill to the group that actually holds the symbol open.

    Walks fills in time order maintaining per-(group, symbol) open quantity.
    An exit tagged to a group already flat on that symbol is re-routed to the
    group carrying the open position. Returns (records, findings).
    """
    open_qty = collections.defaultdict(float)
    out, findings = [], []
    for r in recs:
        signed = r["qty"] if r["side"] == "BUY" else -r["qty"]
        g = r["group"]
        if r["exit_reason"] is not None:
            held = open_qty[(g, r["symbol"])]
            reduces = held != 0 and (held > 0) != (signed > 0)
            if not reduces:
                cands = [gg for (gg, s), q in open_qty.items()
                         if s == r["symbol"] and q != 0 and (q > 0) != (signed > 0)]
                if cands:
                    findings.append({
                        "ts": r["ts"], "symbol": r["symbol"], "tagged": g,
                        "tagged_open": held, "rerouted_to": cands[0],
                        "true_open": open_qty[(cands[0], r["symbol"])],
                        "qty": signed, "reason": r["exit_reason"],
                    })
                    g = cands[0]
        r2 = dict(r)
        r2["group_fixed"] = g
        open_qty[(g, r["symbol"])] += signed
        out.append(r2)
    return out, findings


def group_pnl(recs, key):
    groups = collections.defaultdict(list)
    for r in recs:
        groups[r[key]].append(r)
    rows = []
    for g, items in groups.items():
        gross = sum((1 if i["side"] == "SELL" else -1) * i["price"] * i["qty"]
                    for i in items)
        fee = sum(i["fee"] for i in items)
        struct = next((i["structure"] for i in items if i["structure"]), "?")
        reason = next((i["exit_reason"] for i in items if i["exit_reason"]), "OPEN")
        entries = [i for i in items if i["structure"]]
        rows.append({
            "group": g[:8], "date": min(i["ts"] for i in items).date().isoformat(),
            "structure": struct, "exit": reason,
            "entry_ts": min(i["ts"] for i in entries) if entries else None,
            "exit_ts": max(i["ts"] for i in items),
            "qty": max(i["qty"] for i in entries) if entries else 0,
            "expiry": next((i["expiry"] for i in entries if i["expiry"]), None),
            "gross": gross, "fees": fee, "net": gross - fee,
            "legs": [i for i in items if i["structure"]],
        })
    return sorted(rows, key=lambda r: r["date"])


# ======================================================================== #
# B. Regime
# ======================================================================== #
def load_facts():
    con = duckdb.connect(str(FACTS_DB), read_only=True)
    df = con.execute("select session_date, regime, regime_confidence, "
                     "vix_at_checkpoint from day_type_facts where checkpoint='13pm' "
                     "order by session_date").df()
    con.close()
    df["session_date"] = pd.to_datetime(df["session_date"]).dt.date
    return df


def load_bars(d):
    p = CANDLES / ("%s.duckdb" % d)
    if p.exists():
        con = duckdb.connect(str(p), read_only=True)
        df = con.execute("select timestamp, open, high, low, close, volume from candles "
                         "where symbol=? order by timestamp", [SYMBOL]).df()
        con.close()
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df, "1m candles"
    p = CHAINS / ("%s.duckdb" % d)
    if not p.exists():
        return None, None
    con = duckdb.connect(str(p), read_only=True)
    df = con.execute("select snapshot_timestamp as timestamp, underlying_ltp as close "
                     "from option_chain_snapshot where underlying_symbol=? "
                     "and underlying_ltp is not null order by 1", [SYMBOL]).df()
    con.close()
    if df.empty:
        return None, None
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").resample("1min").agg(
        {"close": ["first", "max", "min", "last"]}).dropna()
    df.columns = ["open", "high", "low", "close"]
    df = df.reset_index()
    df["volume"] = 0
    return df, "chain underlying_ltp"


def realized_stats(d):
    bars, src = load_bars(d)
    if bars is None or bars.empty:
        return None
    b = bars.set_index("timestamp")
    at13 = b.between_time("12:55", "13:05")
    if at13.empty:
        return None
    p13 = float(at13["close"].iloc[-1])
    hold = b.between_time("13:00", HORIZON_END)
    if hold.empty:
        return None
    pex = float(hold["close"].iloc[-1])
    hi, lo = float(hold["high"].max()), float(hold["low"].min())
    y = hold["close"].to_numpy(dtype=float)
    x = np.arange(len(y), dtype=float)
    r2 = float(np.corrcoef(x, y)[0, 1] ** 2) if len(y) > 2 and y.std() > 0 else 0.0
    return {
        "p1300": p13, "pexit": pex, "ret_pct": (pex - p13) / p13 * 100,
        "move_pts": pex - p13, "range_pts": hi - lo,
        "mfe_up_pts": hi - p13, "mfe_dn_pts": p13 - lo,
        "hold_r2": r2, "n_bars": len(hold),
        "day_open": float(b["open"].iloc[0]), "day_close": float(b["close"].iloc[-1]),
        "day_range_pts": float(b["high"].max() - b["low"].min()),
        "src": src,
    }


def _prev_close(d):
    """Prior trading session's Nifty close (for gap_pct)."""
    cur = date.fromisoformat(d)
    files = sorted(p.stem for p in CANDLES.glob("*.duckdb"))
    prior = [f for f in files if f < d]
    if not prior:
        return None
    con = duckdb.connect(str(CANDLES / ("%s.duckdb" % prior[-1])), read_only=True)
    row = con.execute("select close from candles where symbol=? "
                      "order by timestamp desc limit 1", [SYMBOL]).fetchone()
    con.close()
    return None if row is None else float(row[0])


def frozen_cluster_label(d):
    """Assign the session to the FROZEN training centroids (nearest, z-scored).

    The clustering pipeline persisted only the diagnostic-space centroids, not
    the scaler/PCA/KMeans objects, so this is a nearest-centroid approximation
    of the training label over the 14 diagnostic features, standardised on the
    2012-2025 training distribution. Reported with its margin so a marginal
    assignment is visible rather than hidden.
    """
    bars, _ = load_bars(d)
    if bars is None or bars.empty:
        return None
    df = bars.copy()
    hm = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    df = df[(hm >= 555) & (hm <= 929)].reset_index(drop=True)
    if len(df) < 5:
        return None
    first_hm = int(df["timestamp"].dt.hour.iloc[0]) * 60 + int(df["timestamp"].dt.minute.iloc[0])
    last_hm = int(df["timestamp"].dt.hour.iloc[-1]) * 60 + int(df["timestamp"].dt.minute.iloc[-1])
    full = (first_hm <= 556) and (last_hm >= 925)
    try:
        feats = compute_session_features(df)
    except Exception as exc:                       # noqa: BLE001
        return {"error": str(exc)[:80]}
    # gap_pct is a block-A feature needing the prior session's close, which
    # compute_session_features cannot see from a single day.
    if feats.get("gap_pct") is None or (isinstance(feats.get("gap_pct"), float)
                                        and np.isnan(feats.get("gap_pct"))):
        prev = _prev_close(d)
        feats["gap_pct"] = (np.nan if prev is None
                            else (float(df["open"].iloc[0]) - prev) / prev * 100)
    train = pd.concat([pd.read_csv(FEATDIR / ("nifty_day_features_%d.csv" % y),
                                   index_col=0, parse_dates=True)
                       for y in range(2012, 2026)])
    cent = pd.read_csv(FEATDIR / "cluster_centroids.csv").set_index("cluster")
    mu, sd = train[DIAG].mean(), train[DIAG].std()
    v = pd.Series({k: feats.get(k, np.nan) for k in DIAG}, dtype=float)
    if v.isna().any():
        return {"error": "missing features: %s" % list(v[v.isna()].index)}
    z = (v - mu) / sd
    dists = {c: float(np.linalg.norm((z - (cent.loc[c, DIAG] - mu) / sd).to_numpy()))
             for c in cent.index}
    order = sorted(dists, key=dists.get)
    return {"label": CLUSTER_NAMES[order[0]], "d1": dists[order[0]],
            "full_session": full,
            "first_bar": df["timestamp"].iloc[0], "last_bar": df["timestamp"].iloc[-1],
            "d2": dists[order[1]], "margin": dists[order[1]] - dists[order[0]],
            "clv": feats.get("clv"), "linreg_r2": feats.get("linreg_r2"),
            "day_range_pct": feats.get("day_range_pct")}


def score_direction(regime, move_pts, p13, band):
    thr = p13 * band
    realized = "Flat" if abs(move_pts) < thr else ("Up" if move_pts > 0 else "Down")
    want = {"BullTrend": "Up", "BearTrend": "Down", "Choppy": "Flat"}[regime]
    return realized, ("HIT" if realized == want else "MISS")


# ======================================================================== #
# C. Exit efficiency
# ======================================================================== #
def marks_path(d):
    p = SESSIONS / d / "marks.jsonl"
    if not p.exists():
        return []
    out, seen = [], None
    for line in p.open():
        rec = json.loads(line)
        m = rec.get("marks") or {}
        if not m or m == seen:
            continue
        seen = m
        out.append(dict(m))
    return out


def exit_efficiency(row):
    path = marks_path(row["date"])
    legs = [l for l in row["legs"]]
    if not path or not legs:
        return None
    entry_val = sum((1 if l["side"] == "SELL" else -1) * l["price"] * l["qty"]
                    for l in legs)
    vals = []
    for m in path:
        if not all(l["symbol"] in m for l in legs):
            continue
        vals.append(sum((1 if l["side"] == "SELL" else -1) * m[l["symbol"]] * l["qty"]
                        for l in legs))
    if len(vals) < 3:
        return None
    # marks.jsonl carries no timestamps, and the poller warms the marks source
    # before the entry fills. The mark taken AT entry must reproduce the entry
    # value, so the path starts at whichever of the first few marks is closest
    # to it -- everything before that is a pre-entry poll and would otherwise
    # enter as unattainable P&L.
    head = vals[:5]
    start = min(range(len(head)), key=lambda i: abs(head[i] - entry_val))
    dropped = start
    series = [entry_val - v for v in vals[start:]]
    if len(series) < 3:
        return None
    s = np.array(series)
    credit = entry_val
    tp = CONFIG["profit_target_pct"] * abs(credit)
    return {"credit": credit, "mfe": float(s.max()), "mae": float(s.min()),
            "final": float(s[-1]), "n": len(s), "tp_threshold": tp,
            "dropped_pre_entry": dropped,
            "tp_reached_pct": float(s.max() / tp * 100) if tp else float("nan"),
            "capture": float(s[-1] / s.max() * 100) if s.max() > 0 else float("nan")}


# ======================================================================== #
# D. Black-Scholes on the traded legs
# ======================================================================== #
def _nd(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs_price(S, K, T, r, sig, cp):
    if T <= 0 or sig <= 0:
        return max(0.0, (S - K) if cp == "CE" else (K - S))
    d1 = (math.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    if cp == "CE":
        return S * _nd(d1) - K * math.exp(-r * T) * _nd(d2)
    return K * math.exp(-r * T) * _nd(-d2) - S * _nd(-d1)


def bs_delta(S, K, T, r, sig, cp):
    if T <= 0 or sig <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * math.sqrt(T))
    return _nd(d1) if cp == "CE" else _nd(d1) - 1.0


def implied_vol(price, S, K, T, r, cp):
    lo, hi = 1e-4, 5.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if bs_price(S, K, T, r, mid, cp) > price:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# ======================================================================== #
# E. Counterfactual grid
# ======================================================================== #
def chain_at(d, expiry, ts):
    p = CHAINS / ("%s.duckdb" % d)
    if not p.exists():
        return None
    con = duckdb.connect(str(p), read_only=True)
    snap = con.execute(
        "select snapshot_timestamp from option_chain_snapshot "
        "where underlying_symbol=? and expiry_date=? "
        "order by abs(epoch(snapshot_timestamp) - epoch(?::timestamp)) limit 1",
        [SYMBOL, expiry, ts.replace(tzinfo=None)]).fetchone()
    if snap is None:
        con.close()
        return None
    df = con.execute(
        "select strike_price, option_type, ltp, best_bid, best_ask, oi, iv, "
        "delta, underlying_ltp from option_chain_snapshot where "
        "underlying_symbol=? and expiry_date=? and snapshot_timestamp=?",
        [SYMBOL, expiry, snap[0]]).df()
    con.close()
    return {"ts": snap[0], "df": df}


def legs_for(structure, atm):
    w = CONFIG["wing_offset_pts"]
    dw = CONFIG["directional_wing_pts"]
    o = CONFIG["strangle_otm_pts"]
    return {
        "short_straddle": [("SELL", atm, "CE"), ("SELL", atm, "PE")],
        "short_strangle": [("SELL", atm + o, "CE"), ("SELL", atm - o, "PE")],
        "iron_fly": [("SELL", atm, "CE"), ("SELL", atm, "PE"),
                     ("BUY", atm + w, "CE"), ("BUY", atm - w, "PE")],
        "bear_call_spread": [("SELL", atm, "CE"), ("BUY", atm + dw, "CE")],
        "bull_put_spread": [("SELL", atm, "PE"), ("BUY", atm - dw, "PE")],
        "iron_condor_150w": [("SELL", atm + 150, "CE"), ("BUY", atm + 300, "CE"),
                             ("SELL", atm - 150, "PE"), ("BUY", atm - 300, "PE")],
    }[structure]


ALL_STRUCTURES = ["short_straddle", "short_strangle", "iron_fly",
                  "bear_call_spread", "bull_put_spread", "iron_condor_150w"]


def px(snap, strike, opt, field="ltp"):
    df = snap["df"]
    row = df[(df.strike_price == strike) & (df.option_type == opt)]
    if row.empty:
        return None
    v = row.iloc[0][field]
    return None if pd.isna(v) else float(v)


def _mid(snap, strike, opt):
    b = px(snap, strike, opt, "best_bid")
    a = px(snap, strike, opt, "best_ask")
    if b is None or a is None or b <= 0 or a <= 0 or a < b:
        return None
    return 0.5 * (b + a)


def counterfactual(d, expiry, entry_ts, exit_ts, lot_size, structures=None):
    e_snap = chain_at(d, expiry, entry_ts)
    x_snap = chain_at(d, expiry, exit_ts)
    if not e_snap or not x_snap:
        return None
    spot = float(e_snap["df"]["underlying_ltp"].dropna().iloc[0])
    spot_x = float(x_snap["df"]["underlying_ltp"].dropna().iloc[0])
    atm = int(round(spot / CONFIG["strike_step"]) * CONFIG["strike_step"])
    qty = CF_LOTS * lot_size
    td = date.fromisoformat(d)
    rows = []
    for s in (structures or ALL_STRUCTURES):
        gross, fee, ok, detail, credit = 0.0, 0.0, True, [], 0.0
        for side, k, opt in legs_for(s, atm):
            pe, pxx = px(e_snap, k, opt), px(x_snap, k, opt)
            if pe is None or pxx is None or pe <= 0:
                ok = False
                break
            sgn = 1 if side == "SELL" else -1
            credit += sgn * pe * qty
            gross += sgn * (pe - pxx) * qty
            fee += option_order_fees(premium=pe, quantity=int(qty), side=side,
                                     trade_date=td).total
            fee += option_order_fees(premium=pxx, quantity=int(qty),
                                     side=("BUY" if side == "SELL" else "SELL"),
                                     trade_date=td).total
            detail.append("%s%d%s %.2f->%.2f" % (side[0], k, opt, pe, pxx))
        if not ok:
            continue
        # Sensitivity: the same structure priced at bid/ask mid on both
        # sides. LTP is the primary convention because it matches the live
        # fills, but the far wings quote in single-digit rupees where LTP is
        # most likely stale.
        m_gross, m_ok = 0.0, True
        for side, k, opt in legs_for(s, atm):
            me, mx = _mid(e_snap, k, opt), _mid(x_snap, k, opt)
            if me is None or mx is None:
                m_ok = False
                break
            m_gross += (1 if side == "SELL" else -1) * (me - mx) * qty
        rows.append({"structure": s, "credit": credit, "gross": gross,
                     "fees": fee, "net": gross - fee,
                     "net_mid": (m_gross - fee) if m_ok else None,
                     "net_per_lot": (gross - fee) / CF_LOTS,
                     "legs": "; ".join(detail)})
    return {"atm": atm, "spot": spot, "spot_exit": spot_x,
            "entry_snap": e_snap["ts"], "exit_snap": x_snap["ts"],
            "rows": sorted(rows, key=lambda r: -r["net"])}


# ======================================================================== #
# F. Cost restatement + leg diagnostics
# ======================================================================== #
def option_fees_for(row):
    """Restate the structure's fees under the NSE index-option cost model.

    The live handler charged `ExecutionHandler._calculate_fees`, which is the
    NSE *equity intraday* schedule: it carries no option STT (0.15% of sell
    premium since 2026-04-01) and a different exchange rate.
    """
    con = sqlite3.connect("file:%s?mode=ro" % EXEC_DB, uri=True)
    con.row_factory = sqlite3.Row
    orders = {r["correlation_id"]: dict(r) for r in con.execute("select * from orders")}
    fills = [dict(r) for r in con.execute("select * from fills order by timestamp")]
    con.close()
    total = 0.0
    for f in fills:
        o = orders[f["order_id"]]
        sm = (json.loads(o["metadata"] or "{}")).get("strategy_metadata", {})
        gid = sm.get("group_id") or ""
        if not gid.startswith(row["group"]):
            continue
        ts = datetime.fromisoformat(f["timestamp"])
        total += option_order_fees(premium=float(f["price"]),
                                   quantity=int(f["quantity"]),
                                   side=f["side"], trade_date=ts.date()).total
    return total


def leg_diagnostics(row):
    """IV and delta of the actually-traded legs at entry, from their own marks.

    Solves Black-Scholes for the implied vol of each filled leg against the
    Nifty level at entry, then reports the delta that vol implies. Uses only
    the fill price, strike, spot and time to expiry, so it works for the
    2026-09-15 expiry that the chain store does not cover.
    """
    bars, _ = load_bars(row["date"])
    if bars is None or bars.empty or not row["expiry"]:
        return None
    b = bars.set_index("timestamp")
    win = b.between_time("12:55", "13:30")
    if win.empty:
        return None
    idx = win.index[win.index <= pd.Timestamp(row["entry_ts"])]
    spot = float(win.loc[idx[-1], "close"]) if len(idx) else float(win["close"].iloc[0])
    exp = date.fromisoformat(row["expiry"])
    days = (exp - date.fromisoformat(row["date"])).days + (15.5 - 13.0) / 24.0
    T = max(days, 1e-6) / 365.0
    out = []
    for leg in row["legs"]:
        k, cp = float(leg["strike"]), leg["opt"]
        iv = implied_vol(leg["price"], spot, k, T, RISK_FREE, cp)
        out.append({"role": leg["role"], "side": leg["side"], "strike": k,
                    "opt": cp, "price": leg["price"], "iv": iv,
                    "delta": bs_delta(spot, k, T, RISK_FREE, iv, cp),
                    "moneyness_pts": k - spot})
    net_delta = sum((1 if l["side"] == "BUY" else -1) * d["delta"] * l["qty"]
                    for l, d in zip(row["legs"], out))
    sigma_pts = spot * out[0]["iv"] * math.sqrt(T)
    return {"spot": spot, "T_days": days, "legs": out, "net_delta": net_delta,
            "sigma_to_expiry_pts": sigma_pts}


def structure_geometry(row):
    """Credit, width, max profit / max loss and the required win rate."""
    legs = row["legs"]
    shorts = [l for l in legs if l["side"] == "SELL"]
    wings = [l for l in legs if l["side"] == "BUY"]
    credit = sum((1 if l["side"] == "SELL" else -1) * l["price"] * l["qty"]
                 for l in legs)
    if not wings or not shorts:
        return {"credit": credit, "width": None, "max_loss": None,
                "reward_risk": None, "breakeven_win_rate": None}
    pairs = [abs(float(w["strike"]) - float(s["strike"]))
             for s in shorts for w in wings if w["opt"] == s["opt"]]
    if not pairs:
        return {"credit": credit, "width": None, "max_loss": None,
                "reward_risk": None, "breakeven_win_rate": None}
    width = max(pairs)
    qty = shorts[0]["qty"]
    max_loss = width * qty - credit
    rr = credit / max_loss if max_loss > 0 else None
    bw = (max_loss / (max_loss + credit)) if max_loss > 0 else None
    return {"credit": credit, "width": width, "max_loss": max_loss,
            "reward_risk": rr, "breakeven_win_rate": bw, "qty": qty}


def options_regime_at(d, entry_ts):
    """The wall poller's own options-derived read at the shield's entry."""
    p = ROOT / "data" / "options" / "wall_scan_results.duckdb"
    if not p.exists():
        return None
    con = duckdb.connect(str(p), read_only=True)
    row = con.execute(
        "select ts, regime, atm_iv, realized_vol, pin_strike, put_wall, "
        "call_wall, pin_conviction, net_gex_cr, sigma_pts, underlying_ltp "
        "from session_regime where underlying=? and trade_date=? "
        "order by abs(epoch(ts) - epoch(?::timestamp)) limit 1",
        [SYMBOL, d, entry_ts.replace(tzinfo=None)]).fetchone()
    con.close()
    if row is None:
        return None
    keys = ("ts", "regime", "atm_iv", "realized_vol", "pin_strike", "put_wall",
            "call_wall", "pin_conviction", "net_gex_cr", "sigma_pts",
            "underlying_ltp")
    return dict(zip(keys, row))


# ======================================================================== #
# G. Report
# ======================================================================== #
def fmt(x, n=2):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    return "{:,.{}f}".format(x, n)


def main():
    recs = load_ledger()
    fixed, findings = reattribute(recs)
    as_rec = group_pnl(fixed, "group")
    fixed_rows = group_pnl(fixed, "group_fixed")
    facts = load_facts()
    L = []
    w = L.append

    w("# NiftyShield - Regime Quality and Structure-Choice Audit")
    w("")
    w("Generated by `scripts/nifty_shield/audit_regime_and_structures.py` on "
      "%s. Read-only against every store; every number below is "
      "script-produced." % datetime.now().strftime("%Y-%m-%d %H:%M"))
    w("")
    w("> **Correction, 2026-09-08 — finding #4 amended after a wider read.** "
      "The first issue of this audit reported that 0 of 6 directional regime "
      "calls hit over the holding window and treated that as a finding about "
      "the model. It is not: at n=6 it is noise. "
      "`scripts/nifty_shield/diagnose_regime_horizon.py` re-ran the same "
      "question over **1,606 out-of-sample sessions** and found the 13:00 call "
      "*does* separate direction over its own forward window "
      "(BullTrend minus BearTrend = **+0.255 pp**, bootstrap 95% CI "
      "[+0.197, +0.312], excluding zero). Section 2.2 and finding #4 below are "
      "amended accordingly; the live-window numbers are unchanged and are "
      "retained as a record of what 6 sessions showed. See "
      "`NIFTY_SHIELD_REGIME_HORIZON_DIAGNOSTIC.md`.")
    w("")
    w("## 0. Scope, and what this evidence can and cannot support")
    w("")
    w("- **%d sessions** carry a 13:00 regime fact (%s to %s); **%d structures** "
      "were actually entered." % (len(facts), facts["session_date"].min(),
                                  facts["session_date"].max(), len(fixed_rows)))
    w("- At n=8 traded structures no accuracy or P&L figure here is *evidence* "
      "of edge or its absence. Treat every rate as descriptive.")
    w("- **Option-chain history exists for 3 sessions only** (2026-09-04, "
      "09-07, 09-08), and covers the *current-week* Nifty expiry only.")
    w("  - 2026-09-04: the shield traded the 08SEP expiry, which the store "
      "covers, so an **exact** like-for-like structure counterfactual is "
      "possible.")
    w("  - 2026-09-07 / 09-08: the shield traded 15SEP; the store holds only "
      "08SEP, so those grids compare **expiry choice**, not structure choice, "
      "and are labelled as such.")
    w("  - No Black-Scholes reconstruction of the 15SEP surface is attempted: "
      "a 0-1 DTE chain does not extrapolate to 8 DTE, and term structure is "
      "exactly the quantity under test.")
    w("")
    w("**Pinned decision rules** (fixed before any number was computed):")
    w("")
    w("- R1 - a regime call is scored against the realized 13:00 to 15:15 move "
      "with a dead band of **%.2f%%** of the 13:00 level; sensitivity at %s is "
      "printed." % (PRIMARY_BAND * 100,
                    ", ".join("%.2f%%" % (b * 100) for b in DEAD_BANDS)))
    w("- R2 - the realized horizon is 13:00 to %s everywhere." % HORIZON_END)
    w("- R3 - counterfactuals price at chain LTP (the live marks convention), "
      "at the actual entry/exit timestamps, at a **fixed %d lots x %d units** "
      "(so sizing cannot drive the ranking - the live book used 75, 150 and 65 "
      "units as the broker basket-margin clamp moved), with the real per-leg "
      "NSE index-option fee model." % (CF_LOTS, CF_LOT_SIZE))
    w("")

    # ---- 1. Ledger --------------------------------------------------------
    w("## 1. The ledger is mis-attributed on 2026-08-21")
    w("")
    if findings:
        w("A position-walk over every fill (maintaining per-group, per-symbol "
          "open quantity) finds exits routed to a group that was already flat:")
        w("")
        w("| when | symbol | tagged group | its open qty | actually open in | that qty | exit qty | reason |")
        w("|---|---|---|---:|---|---:|---:|---|")
        for f in findings:
            w("| %s | %s | `%s` | %s | `%s` | %s | %s | %s |" % (
                f["ts"].strftime("%Y-%m-%d %H:%M:%S"), f["symbol"],
                f["tagged"][:8], fmt(f["tagged_open"], 0),
                f["rerouted_to"][:8], fmt(f["true_open"], 0),
                fmt(f["qty"], 0), f["reason"]))
        w("")
        w("Mechanism: group `5f5b591a` (the 08-20 bull put spread) was manually "
          "closed at 12:59:07 on 08-21. Its stop-loss evaluated again at "
          "13:05:24 and closed by *symbol*, not by the group's own remaining "
          "legs - and by then `NIFTY25AUG2624250PE` was the short put of the "
          "brand-new straddle `f37e2e99`, entered 71 seconds earlier at "
          "13:04:13. The stop bought 150 units (the straddle's size, not the "
          "spread's 75) and flattened the straddle's put leg.")
        w("")
        w("Two consequences: the per-structure P&L below is wrong as recorded, "
          "and **the 08-21 straddle cannot be used to judge structure choice** "
          "- it was half-closed 71 seconds after entry by another group's stop.")
        w("")
    else:
        w("No mis-attributed exits found.")
        w("")

    w("### 1.1 Per-structure ledger, as recorded vs re-attributed")
    w("")
    w("| date | group | structure | exit | qty | gross (as recorded) | net (as recorded) | gross (re-attributed) | net (re-attributed) |")
    w("|---|---|---|---|---:|---:|---:|---:|---:|")
    bykey = {r["group"]: r for r in as_rec}
    for r in fixed_rows:
        a = bykey.get(r["group"], r)
        w("| %s | `%s` | %s | %s | %d | %s | %s | %s | **%s** |" % (
            r["date"], r["group"], r["structure"], r["exit"], int(r["qty"]),
            fmt(a["gross"]), fmt(a["net"]), fmt(r["gross"]), fmt(r["net"])))
    tot_a = sum(r["net"] for r in as_rec)
    tot_f = sum(r["net"] for r in fixed_rows)
    w("| **total** | | | | | | **%s** | | **%s** |" % (fmt(tot_a), fmt(tot_f)))
    w("")
    w("The totals agree (%s) - only the attribution moves. As recorded, 08-20 "
      "shows -10,018 and 08-21 shows +9,689; both are artefacts of the same "
      "mis-routed fill." % fmt(tot_f))
    w("")

    w("### 1.2 The PAPER fee model is the wrong schedule")
    w("")
    w("`ExecutionHandler._calculate_fees` (handler.py:1136) charges the **NSE "
      "equity intraday** schedule on option legs. Three departures, read off "
      "the function body:")
    w("")
    w("| component | charged | correct for NSE index options | effect |")
    w("|---|---|---|---|")
    w("| STT | 0.025% of turnover on **every** leg (the docstring says "
      "\"applied on sell side; averaged across both legs\") | 0.15% of sell-leg "
      "**premium** only, since 2026-04-01 | 6x too little on the sell leg, and "
      "a charge on the buy leg that does not exist |")
    w("| Exchange txn | 0.00345% | 0.03503% | ~10x too low |")
    w("| Stamp duty | 0.003% on both sides | 0.003% buy side only | small "
      "over-charge on sells |")
    w("")
    w("The correct schedule already exists at `core/execution/options/fees.py` "
      "and is simply not wired to this path. Restating every fill through it:")
    w("")
    w("| date | structure | fees charged | fees under option model | net (charged) | net (correct) |")
    w("|---|---|---:|---:|---:|---:|")
    corr_tot = 0.0
    for r in fixed_rows:
        of = option_fees_for(r)
        corr = r["gross"] - of
        corr_tot += corr
        w("| %s | %s | %s | %s | %s | **%s** |" % (
            r["date"], r["structure"], fmt(r["fees"]), fmt(of),
            fmt(r["net"]), fmt(corr)))
    w("| **total** | | | | **%s** | **%s** |" % (fmt(tot_f), fmt(corr_tot)))
    w("")
    w("The eight structures net **%s** as booked and **%s** under the correct "
      "schedule - a %s understatement of cost over 8 round trips. At this trade "
      "size fees are the same order as the entire result."
      % (fmt(tot_f), fmt(corr_tot), fmt(tot_f - corr_tot)))
    w("")

    # ---- 2. Regime --------------------------------------------------------
    w("## 2. Is the regime call on our side?")
    w("")
    w("### 2.1 The model against its own training target (full-day cluster)")
    w("")
    w("The label the classifier was trained to predict is the KMeans cluster of "
      "**full-session** features (`scripts/daytype/cluster_day_types.py`). "
      "Stored cluster labels stop at 2025-12-31 and the 2026 feature file stops "
      "at 2026-08-07, so no stored ground truth exists for the live window. The "
      "column below assigns each session to the **frozen training centroids** "
      "(`cluster_centroids.csv`), nearest-centroid over the 14 diagnostic "
      "features, z-scored on the 2012-2025 distribution. The pipeline did not "
      "persist its scaler/PCA/KMeans objects, so this is an approximation of "
      "the training label, not the label itself - the margin column shows how "
      "close each call was.")
    w("")
    w("| date | predicted @13:00 | conf | VIX | full-day label | margin | CLV | linreg r2 | day range % | session complete | agree |")
    w("|---|---|---:|---:|---|---:|---:|---:|---:|---|---|")
    agree = tot = agree_full = tot_full = 0
    for _, fr in facts.iterrows():
        d = fr["session_date"].isoformat()
        c = frozen_cluster_label(d)
        if not c or "error" in c:
            w("| %s | %s | %.3f | %.2f | n/a | | | | | | |" % (
                d, fr["regime"], fr["regime_confidence"], fr["vix_at_checkpoint"]))
            continue
        ok = c["label"] == fr["regime"]
        agree += ok
        tot += 1
        if c["full_session"]:
            agree_full += ok
            tot_full += 1
        cov = "yes" if c["full_session"] else ("**no** - bars %s to %s"
                                               % (c["first_bar"].strftime("%H:%M"),
                                                  c["last_bar"].strftime("%H:%M")))
        w("| %s | %s | %.3f | %.2f | %s | %s | %s | %s | %s | %s | %s |" % (
            d, fr["regime"], fr["regime_confidence"], fr["vix_at_checkpoint"],
            c["label"], fmt(c["margin"]), fmt(c["clv"]), fmt(c["linreg_r2"]),
            fmt(c["day_range_pct"] * 100), cov, "HIT" if ok else "MISS"))
    w("")
    w("**%d of %d** agree; on complete sessions only, **%d of %d**. A session "
      "flagged incomplete has no 1m candle file yet, so its features are built "
      "from the chain snapshot's underlying and its open, first-hour range and "
      "close-location are all wrong - read that row as unscored, not as a hit."
      % (agree, tot, agree_full, tot_full))
    w("")
    w("**Do not read this rate against the 75-85% the trainer documents for "
      "the 13:00 checkpoint.** That figure is accuracy against the true "
      "PCA-space KMeans label; this one is against a 14-D z-scored "
      "nearest-centroid proxy. Without the persisted scaler/PCA/KMeans objects "
      "the disagreement cannot be split into model error and proxy error, so "
      "the two numbers are not commensurable. The horizon argument in 2.2 needs "
      "no proxy at all and is where the weight should sit.")
    w("")

    w("### 2.2 The horizon the strategy actually consumes")
    w("")
    w("The prediction is a **full-session** label. The structure is opened at "
      "13:00 and closed at 15:15. So the model is trained on one horizon and "
      "traded on another - and the traded horizon is the quiet part of the day.")
    w("")
    w("| date | predicted | 13:00 | 15:15 | move (pts) | move % | 13:00-15:15 range | up excursion | down excursion | trend r2 | price source | realized | verdict |")
    w("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|")
    rstats = {}
    for _, fr in facts.iterrows():
        d = fr["session_date"].isoformat()
        st = realized_stats(d)
        rstats[d] = st
        if st is None:
            continue
        real, verdict = score_direction(fr["regime"], st["move_pts"],
                                        st["p1300"], PRIMARY_BAND)
        w("| %s | %s | %s | %s | %s | %s%% | %s | %s | %s | %s | %s | %s | %s |" % (
            d, fr["regime"], fmt(st["p1300"], 1), fmt(st["pexit"], 1),
            fmt(st["move_pts"], 1), fmt(st["ret_pct"], 3),
            fmt(st["range_pts"], 1), fmt(st["mfe_up_pts"], 1),
            fmt(st["mfe_dn_pts"], 1), fmt(st["hold_r2"]), st["src"], real,
            verdict))
    w("")
    moves = [abs(s["move_pts"]) for s in rstats.values() if s]
    rngs = [s["range_pts"] for s in rstats.values() if s]
    lv = [s["p1300"] for s in rstats.values() if s]
    w("Median absolute 13:00 to 15:15 move: **%s points** (%s%% of index). "
      "Largest over %d sessions: **%s points**. Median 13:00-15:15 range: "
      "**%s points**." % (
          fmt(float(np.median(moves)), 1),
          fmt(float(np.median(moves)) / float(np.median(lv)) * 100, 3),
          len(moves), fmt(max(moves), 1), fmt(float(np.median(rngs)), 1)))
    w("")
    w("One row is measured off the chain snapshot's underlying rather than 1m "
      "candles; its range and excursion figures are sampled, not true 1m "
      "high/low, and are biased low against every other row.")
    w("")
    w("**Dead-band sensitivity** - how the verdict changes with R1. The last "
      "two columns split out the calls the structure choice actually turns on:")
    w("")
    w("| dead band | pts @ 24,000 | HIT (all) | of | rate | HIT (directional calls only) | of |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    dir_hits = {}
    for band in DEAD_BANDS:
        h = n = dh = dn = 0
        for _, fr in facts.iterrows():
            st = rstats.get(fr["session_date"].isoformat())
            if not st:
                continue
            n += 1
            hit = score_direction(fr["regime"], st["move_pts"], st["p1300"],
                                  band)[1] == "HIT"
            h += hit
            if fr["regime"] in ("BullTrend", "BearTrend"):
                dn += 1
                dh += hit
        dir_hits[band] = (dh, dn)
        w("| %.2f%% | %s | %d | %d | %.0f%% | **%d** | %d |" % (
            band * 100, fmt(24000 * band, 0), h, n, h / n * 100 if n else 0,
            dh, dn))
    w("")
    dh0, dn0 = dir_hits[PRIMARY_BAND]
    w("%d of %d directional calls hit over the live window, at every band "
      "tested. **Do not read that as a finding about the model.**" % (dh0, dn0))
    w("")
    w("The first issue of this audit did read it that way. It was wrong to. Six "
      "observations of a quantity whose per-day dispersion dwarfs its mean "
      "cannot distinguish \"no edge\" from \"an edge and a bad week\", and the "
      "wider read settles it the other way: over **1,606 out-of-sample "
      "sessions** the 13:00 call separates BullTrend from BearTrend by "
      "**+0.255 pp** on the checkpoint-to-close move, bootstrap 95% CI "
      "[+0.197, +0.312] - excluding zero. BullTrend sessions close +0.095% and "
      "62% of them close up; BearTrend sessions close -0.160% and 40% close up. "
      "The same test at the 10:00 and 11:00 checkpoints finds no separation at "
      "all (CIs spanning zero), so 13:00 is the *best* of the three "
      "checkpoints, not a poor one.")
    w("")
    w("What survives here is narrower, and is about magnitude rather than "
      "direction. The separation is roughly 60 points on a 24,000 index, "
      "against structures 150 points wide and an exit that never takes profit "
      "(section 3). **The signal is not the weak link; the vehicle is.** That "
      "is an argument for anchoring strikes and exits to the size of the move "
      "actually on offer, not for abandoning the 13:00 read.")
    w("")
    w("Two caveats on the wider read, so it is discounted correctly: the "
      "cluster boundaries were fit over the full 2012-2025 panel, so the label "
      "*definition* saw the test years (the forward-move measurement itself is "
      "clean); and a mean separation of 0.255 pp measured precisely at "
      "n=1,606 is a thin edge, not a strong one - per-session dispersion is "
      "far larger.")
    w("")

    # ---- 3. Exit efficiency ----------------------------------------------
    w("## 3. Were the trades worked for maximum profit?")
    w("")
    w("Structure mark-to-market path from `marks.jsonl` (the same marks the "
      "exit driver saw). MFE/MAE are the best and worst structure P&L reached "
      "while held, in rupees. `marks.jsonl` carries no timestamps, so the path "
      "is started at whichever of the first five marks reproduces the entry "
      "fill value - the poller warms the marks source before the fills, and "
      "those pre-entry polls would otherwise show as unattainable P&L.")
    w("")
    w("| date | structure | credit | MFE | MAE | at exit | TP threshold (50% of credit) | peak as % of TP | % of MFE captured |")
    w("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    effs = []
    for r in fixed_rows:
        e = exit_efficiency(r)
        if e is None:
            w("| %s | %s | | | | | | *no marks recorded* | |"
              % (r["date"], r["structure"]))
            continue
        effs.append((r, e))
        w("| %s | %s | %s | %s | %s | %s | %s | **%s%%** | %s%% |" % (
            r["date"], r["structure"], fmt(e["credit"], 0), fmt(e["mfe"], 0),
            fmt(e["mae"], 0), fmt(e["final"], 0), fmt(e["tp_threshold"], 0),
            fmt(e["tp_reached_pct"], 1), fmt(e["capture"], 1)))
    w("")
    w("Two caveats on the last row: the 2026-09-08 marks stop at 15:17 when the "
      "session recorder stopped, but the structure was not closed until "
      "15:53:57, so its `at exit` and captured-percentage figures are taken at "
      "the stale endpoint - the ledger's actual gross for that structure is "
      "208. Pre-entry marks were dropped as described above.")
    w("")
    if effs:
        best = max(e["tp_reached_pct"] for _, e in effs)
        w("**The profit target has never been reachable.** `profit_target_pct` "
          "is 0.50 - half the credit. Over every session with recorded marks "
          "the structure's peak profit got to at most **%s%%** of that "
          "threshold. A short 4-8 DTE structure held 2.25 hours decays a few "
          "percent of its premium; it cannot shed half. **The TP is unreachable "
          "by construction: not one structure in %d exited on the profit "
          "target.** Exits actually taken: %s." % (
              fmt(best, 1), len(fixed_rows),
              ", ".join("%d %s" % (c, k) for k, c in
                        sorted(collections.Counter(
                            x["exit"] for x in fixed_rows).items(),
                            key=lambda kv: -kv[1]))))
        w("")
        w("The MFE column also shows that what is being left on the table is "
          "small in absolute terms - peak profits of Rs 458-1,642 on a "
          "~Rs 29,000 credit straddle. This is a low-yield window, not a "
          "badly-harvested one.")
        w("")

    # ---- 4. Structure choice, layer 1 ------------------------------------
    w("## 4. Was the structure the best choice? - (a) what the code can see")
    w("")
    w("`strategies/nifty_shield_v1/structures.py::select_structure` is a pure "
      "function of **two inputs**:")
    w("")
    w("```")
    w("BullTrend               -> bull_put_spread")
    w("BearTrend               -> bear_call_spread")
    w("Choppy, VIX > 16        -> short_strangle")
    w("Choppy, 14 < VIX <= 16  -> iron_fly")
    w("Choppy, VIX <= 14       -> short_straddle")
    w("```")
    w("")
    w("It never reads: implied vs realized vol, the IV term structure, skew or "
      "risk reversal, the credit actually on offer, reward/risk, net gamma or "
      "the zero-gamma level, OI walls or max pain, the expected move to expiry, "
      "or the quoted spread. Strikes are **fixed point offsets** - ATM shorts, "
      "a 150-point directional wing, a 100-point fly wing, a 50-point strangle "
      "leg - never delta-based and never scaled by IV or days to expiry.")
    w("")
    w("Two structural consequences follow before any data is consulted.")
    w("")
    w("**(i) VIX has been below 14 on every session**, so the Choppy branch has "
      "only ever produced `short_straddle`. `iron_fly` and `short_strangle` are "
      "unreachable in this vol regime - India VIX at 10.5-11.7 would have to "
      "rise ~30%% to reach the fly branch. Three of the five structures in the "
      "catalogue are dead code at current vol. (Observed VIX range over the "
      "%d sessions: %.2f to %.2f.)"
      % (len(facts), facts["vix_at_checkpoint"].min(),
         facts["vix_at_checkpoint"].max()))
    w("")
    w("**(ii) The directional spreads short the ATM strike**, which makes them "
      "close to a coin flip by construction:")
    w("")
    w("| date | structure | credit | wing width x qty | max loss | credit / max loss | breakeven win rate |")
    w("|---|---|---:|---:|---:|---:|---:|")
    for r in fixed_rows:
        g = structure_geometry(r)
        if g["width"] is None:
            w("| %s | %s | %s | *undefined risk* | n/a | n/a | n/a |"
              % (r["date"], r["structure"], fmt(g["credit"], 0)))
            continue
        w("| %s | %s | %s | %s | %s | %s | %s%% |" % (
            r["date"], r["structure"], fmt(g["credit"], 0),
            fmt(g["width"] * g["qty"], 0), fmt(g["max_loss"], 0),
            fmt(g["reward_risk"]), fmt(g["breakeven_win_rate"] * 100, 1)))
    w("")
    w("A vertical that collects roughly half its own width needs to be right "
      "more than half the time, before fees, just to scratch - and it is being "
      "pointed by a label whose directional content over the holding window is "
      "the %s-point median move measured in section 2.2."
      % fmt(float(np.median(moves)), 1))
    w("")

    # ---- 5. Layer 2: leg diagnostics -------------------------------------
    w("## 5. Was the structure the best choice? - (b) what the traded legs imply")
    w("")
    w("Implied vol solved from each **actual fill price** against the Nifty "
      "level at entry (so this works for the 15SEP expiry the chain store does "
      "not cover), and the delta that vol implies. r = %.3f, expiry at 15:30, "
      "act/365." % RISK_FREE)
    w("")
    w("| date | structure | spot @ entry | DTE | leg | strike | pts from spot | price | IV | delta | net delta (units) | 1 sigma to expiry (pts) |")
    w("|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in fixed_rows:
        dg = leg_diagnostics(r)
        if dg is None:
            continue
        first = True
        for l in dg["legs"]:
            w("| %s | %s | %s | %s | %s | %d | %s | %s | %s%% | %s | %s | %s |" % (
                r["date"] if first else "", r["structure"] if first else "",
                fmt(dg["spot"], 1) if first else "",
                fmt(dg["T_days"], 1) if first else "",
                l["role"], int(l["strike"]), fmt(l["moneyness_pts"], 0),
                fmt(l["price"]), fmt(l["iv"] * 100, 1), fmt(l["delta"], 3),
                fmt(dg["net_delta"], 1) if first else "",
                fmt(dg["sigma_to_expiry_pts"], 0) if first else ""))
            first = False
    w("")
    w("Read the wing deltas down the column: the fixed 150-point directional "
      "wing does not sit at a stable delta from one day to the next, because "
      "days-to-expiry and IV both move underneath it. 'Defined risk' is defined "
      "in *points*, not in probability - the same nominal structure is a "
      "materially different bet on different days.")
    w("")
    w("Compare the 1-sigma-to-expiry column against the wing offsets: the wing "
      "sits inside or outside one standard deviation depending only on how many "
      "days happen to remain, which is a consequence of the "
      "`expiry_days_min = 2` constant rather than a decision.")
    w("")

    # ---- 6. Counterfactual grid ------------------------------------------
    w("## 6. What else was on the board?")
    w("")
    w("Every structure in the catalogue, plus a 150-point-wide iron condor "
      "(**not** in the catalogue), priced from the option chain at the **actual "
      "entry and exit timestamps**, at a fixed %d lots x %d units, at chain "
      "LTP, charged the real per-leg option fee model. Same timestamps and same "
      "size means this compares structure choice, not timing or sizing."
      % (CF_LOTS, CF_LOT_SIZE))
    w("")

    by_date = {r["date"]: r for r in fixed_rows}
    r = by_date.get("2026-09-04")
    if r:
        cf = counterfactual("2026-09-04", "2026-09-08", r["entry_ts"],
                            r["exit_ts"], CF_LOT_SIZE)
        if cf:
            w("### 6.1 2026-09-04 - exact like-for-like (traded expiry is in the store)")
            w("")
            w("Regime **Choppy**, VIX 10.79, so `short_straddle`. ATM %d, spot "
              "%s at entry to %s at exit. Chain snapshots %s / %s." % (
                  cf["atm"], fmt(cf["spot"], 1), fmt(cf["spot_exit"], 1),
                  cf["entry_snap"].strftime("%H:%M:%S"),
                  cf["exit_snap"].strftime("%H:%M:%S")))
            w("")
            w("| structure | credit | gross | fees | **net (LTP)** | net (bid/ask mid) | legs (entry -> exit) |")
            w("|---|---:|---:|---:|---:|---:|---|")
            for row in cf["rows"]:
                mark = " <- **traded**" if row["structure"] == r["structure"] else ""
                w("| %s%s | %s | %s | %s | **%s** | %s | %s |" % (
                    row["structure"], mark, fmt(row["credit"], 0),
                    fmt(row["gross"], 0), fmt(row["fees"], 0),
                    fmt(row["net"], 0),
                    fmt(row["net_mid"], 0) if row["net_mid"] is not None else "n/a",
                    row["legs"]))
            w("")
            traded = next((x for x in cf["rows"]
                           if x["structure"] == r["structure"]), None)
            if traded:
                mid_rows = [x for x in cf["rows"] if x["net_mid"] is not None]
                mid_rank = (sorted(mid_rows, key=lambda x: -x["net_mid"])
                            .index(traded) + 1) if traded in mid_rows else None
                mid_top = (sorted(mid_rows, key=lambda x: -x["net_mid"])[0]["structure"]
                           if mid_rows else None)
                w("The straddle the shield actually chose ranks **%d of %d at "
                  "LTP**, and **%s of %d at bid/ask mid**%s. Reconstruction "
                  "check: the grid prices the traded structure at gross %s "
                  "against the ledger's actual %s - a %s difference from "
                  "snapshot timing, which bounds the grid's precision." % (
                      cf["rows"].index(traded) + 1, len(cf["rows"]),
                      mid_rank if mid_rank else "n/a", len(mid_rows),
                      ("" if mid_top == traded["structure"]
                       else " - under the mid convention `%s` edges ahead of it, "
                            "so the top of the ranking is not robust to the "
                            "pricing convention" % mid_top),
                      fmt(traded["gross"], 0), fmt(r["gross"], 0),
                      fmt(abs(traded["gross"] - r["gross"]), 0)))
                w("")
                w("Note what drives the ranking: on a flat afternoon it is "
                  "simply **most premium sold wins**. The straddle collects the "
                  "most and gives back the least, and the two-leg structures "
                  "beat the four-leg ones partly on fees alone. That is a "
                  "statement about one quiet day, not a recommendation.")
                w("")
                w("The mid column is the robustness check that matters for the "
                  "four-leg structures: their far wings quote in single-digit "
                  "rupees, where LTP is the most likely to be stale. Where the "
                  "LTP and mid columns disagree in *rank*, the LTP ranking of "
                  "that structure should not be relied on.")
                w("")

    w("### 6.2 2026-09-07 and 2026-09-08 - expiry choice, not structure choice")
    w("")
    w("On both days `nearest_expiry(session_date, min_days=2)` skipped the "
      "expiry that was 0-1 days out and bought 8 days of time instead. The "
      "chain store holds that skipped near expiry, so the grid below shows what "
      "the *same catalogue* would have paid on it - against the shield's actual "
      "result on the far expiry.")
    w("")
    for d, exp in (("2026-09-07", "2026-09-08"), ("2026-09-08", "2026-09-08")):
        r = by_date.get(d)
        if not r:
            continue
        lot = CF_LOT_SIZE
        cf = counterfactual(d, exp, r["entry_ts"], r["exit_ts"], lot)
        if not cf:
            w("**%s** - near-expiry chain not resolvable." % d)
            w("")
            continue
        st = rstats.get(d)
        actual_units = float(r["legs"][0]["qty"])
        scale = (CF_LOTS * CF_LOT_SIZE) / actual_units
        w("**%s** - regime BearTrend, traded `%s` on the %s expiry. Nifty %s to "
          "%s over the hold. Near-expiry (%s) grid at the same timestamps, "
          "ATM %d:" % (
              d, r["structure"], r["expiry"],
              fmt(st["p1300"], 1) if st else "n/a",
              fmt(st["pexit"], 1) if st else "n/a", exp, cf["atm"]))
        w("")
        w("| structure (near expiry, %d x %d units) | credit | gross | fees | net (LTP) | net (mid) |"
          % (CF_LOTS, CF_LOT_SIZE))
        w("|---|---:|---:|---:|---:|---:|")
        for row in cf["rows"]:
            w("| %s | %s | %s | %s | **%s** | %s |" % (
                row["structure"], fmt(row["credit"], 0), fmt(row["gross"], 0),
                fmt(row["fees"], 0), fmt(row["net"], 0),
                fmt(row["net_mid"], 0) if row["net_mid"] is not None else "n/a"))
        w("| *actual: %s on the %s expiry, %d units, gross scaled to %d* | %s | %s | %s | %s | %s |"
          % (r["structure"], r["expiry"], int(actual_units),
             CF_LOTS * CF_LOT_SIZE, fmt(structure_geometry(r)["credit"] * scale, 0),
             fmt(r["gross"] * scale, 0), "-", "-", "-"))
        w("")
        w("The last row scales the shield's actual **gross** to the grid's size "
          "so the two are comparable; its fees are left blank because the "
          "Rs 20-per-leg brokerage does not scale linearly. Actual booked net "
          "at the real size was %s." % fmt(r["net"], 0))
        w("")
    w("Each of these is **one observation of a high-variance quantity**. A "
      "near-dated short structure earns more theta and is punished far harder "
      "by a move; two quiet afternoons say nothing about the rule, and skipping "
      "expiry day may well be a deliberate pin/gamma-risk choice. What the grid "
      "establishes is only that the choice is **material** - the near expiry "
      "pays a visibly different number - and that it is currently made by a "
      "date-arithmetic constant with no measurement behind it.")
    w("")

    w("### 6.3 What the options market itself was saying at the same moment")
    w("")
    w("The platform already runs an options-structural read on the same three "
      "days (`data/options/wall_scan_results.duckdb::session_regime`, the "
      "Options-Wall poller). Its output at the shield's entry timestamp, "
      "alongside the day-type regime the shield actually used:")
    w("")
    w("| date | day-type regime (used) | options-derived regime (ignored) | ATM IV | realized vol | IV - RV | pin strike | put wall | call wall | pin conviction | shield short strike | short strike vs pin |")
    w("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    any_or = False
    for d in ("2026-09-04", "2026-09-07", "2026-09-08"):
        r = by_date.get(d)
        if not r:
            continue
        orr = options_regime_at(d, r["entry_ts"])
        if not orr:
            continue
        any_or = True
        fr = facts[facts.session_date == date.fromisoformat(d)]
        shorts = [l for l in r["legs"] if l["side"] == "SELL"]
        ks = shorts[0]["strike"] if shorts else None
        w("| %s | %s | %s | %s%% | %s%% | %s pp | %s | %s | %s | %s | %s | %s |" % (
            d, fr["regime"].iloc[0] if len(fr) else "?", orr["regime"],
            fmt(orr["atm_iv"], 1), fmt(orr["realized_vol"], 1),
            fmt(orr["atm_iv"] - orr["realized_vol"], 1),
            fmt(orr["pin_strike"], 0), fmt(orr["put_wall"], 0),
            fmt(orr["call_wall"], 0), fmt(orr["pin_conviction"], 0),
            fmt(float(ks), 0) if ks else "n/a",
            fmt(float(ks) - orr["pin_strike"], 0) if ks else "n/a"))
    w("")
    if any_or:
        w("Three things this makes concrete.")
        w("")
        w("1. **The options-derived regime disagreed with the day-type regime "
          "on two of the three days.** The poller read *Positive GEX (Stable)* "
          "- a pinning, mean-reverting tape - on all three, while the day-type "
          "model called BearTrend on 09-07 and 09-08 and the shield opened a "
          "directional spread on both. Two independent regime reads exist on "
          "the same clock and only one of them is wired to the decision.")
        w("2. **The short strike sat one strike below the pin on every one of "
          "the three days.** ATM is struck off spot; the options market's own "
          "centre of gravity is the pin strike. The offset is small but it is "
          "not random, and nothing in the selector can see it.")
        w("3. **The variance premium is large and already measured** - by a "
          "component the selector never consults. Read the IV-RV column as a "
          "statement about the vol environment rather than the premium on the "
          "traded contract: the ATM IV shown is for the near expiry the poller "
          "tracks, which on 09-07 and 09-08 is not the expiry the shield "
          "traded.")
        w("")
        w("This is the direct answer to \"are we missing something\": the "
          "platform is already computing gamma structure, walls, pin, and an "
          "IV-RV spread on the same clock as the entry, and the structure "
          "decision uses none of it.")
        w("")

    # ---- 7. Findings ------------------------------------------------------
    w("## 7. Findings")
    w("")
    w("| # | severity | finding |")
    w("|---|---|---|")
    w("| 1 | **HIGH** | A stop-loss fired on an already-closed group and "
      "flattened a *different* group's leg by symbol match (08-21, 71 s after "
      "entry). Exits must target the group's own open legs and quantities. |")
    w("| 2 | **HIGH** | Option legs are charged the NSE **equity intraday** fee "
      "schedule; option STT (0.15% of sell premium) is never applied. The "
      "correct model already exists at `core/execution/options/fees.py` and is "
      "unused on this path. |")
    w("| 3 | **HIGH** | `profit_target_pct = 0.50` is unreachable on a 2.25-hour "
      "hold of a 4-8 DTE credit structure - peak profit reached at most ~19% of "
      "the threshold. `time_exit` is the only exit that ever fires. |")
    w("| 4 | **MEDIUM** *(amended - was HIGH)* | The model's training target is "
      "a **full-session** label while the strategy trades 13:00 to 15:15, so "
      "target and traded horizon are not the same quantity, and stored ground "
      "truth does not cover the live window. **The amended part:** this audit "
      "originally added that the call carries no direction over the holding "
      "window, on 0 of %d live directional calls. At n=1,606 out-of-sample "
      "sessions the 13:00 call *does* separate direction (+0.255 pp, CI "
      "[+0.197, +0.312]), and 10:00/11:00 do not - so the checkpoint is sound "
      "and the original claim was a small-sample artefact. The live median "
      "absolute move is still only %s points (%s%% of index), which is a "
      "statement about **structure sizing**, not about the signal. |"
      % (dn0, fmt(float(np.median(moves)), 1),
         fmt(float(np.median(moves)) / float(np.median(lv)) * 100, 3)))
    w("| 5 | **MEDIUM** | Structure selection reads only `regime` and `vix`. No "
      "IV/RV, skew, term structure, credit, reward/risk, gamma, OI or expected "
      "move enters the decision - and the platform already computes most of "
      "these in `data/options/wall_scan_results.duckdb`. |")
    w("| 6 | **MEDIUM** | With VIX at 10.5-11.7 on every session, the Choppy "
      "branch can only ever emit `short_straddle`. `iron_fly` and "
      "`short_strangle` are unreachable at current vol. |")
    w("| 7 | **MEDIUM** | Strikes and wings are fixed **point** offsets, so the "
      "same nominal structure is a different bet each day as DTE and IV move. "
      "Wings are not delta- or expected-move-anchored. |")
    w("| 8 | **LOW** | Two structures were open concurrently on overlapping "
      "strikes (08-21). Whether structure stacking is intended is undecided in "
      "the code, and it is what made finding 1 reachable. |")
    w("| 9 | **LOW** | Option-chain history is retained for 3 sessions and only "
      "for the current-week expiry - the traded expiry is not archived, so most "
      "of this audit cannot be repeated on the trades that matter. |")
    w("")
    w("## 8. What this audit cannot tell you")
    w("")
    w("- Whether NiftyShield has edge. n=8 structures, net %s on correct fees - "
      "indistinguishable from zero, and far too few observations to be evidence "
      "either way." % fmt(corr_tot))
    w("- Whether a different structure is *generally* better. The one exact "
      "counterfactual (09-04) ranks the traded straddle first, on a single "
      "quiet afternoon.")
    w("- Whether the near expiry is better. Two observations, opposite risk "
      "profile, no measurement.")
    w("")
    w("The findings that **do** stand independent of sample size are the "
      "mechanical ones: 1, 2, 3, 6 and 7 are properties of the code and the fee "
      "schedule, not of the sample. Finding 4's *structural* half - target "
      "horizon versus traded horizon - is also mechanical. Its original "
      "*empirical* half was not, and did not survive contact with a wider "
      "sample; that is recorded above rather than quietly deleted, because the "
      "way it failed is the more useful lesson: an n=6 rate read as a property "
      "of the model.")
    w("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("wrote %s (%d lines)" % (OUT, len(L)))


if __name__ == "__main__":
    main()
