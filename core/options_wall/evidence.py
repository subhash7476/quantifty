"""Options-Wall evidence analytics — read-only, over the pilot's own trail.

Answers the question Trade Intelligence would have been asked, but against the
richer evidence the wall already records: closed paper flies (`trades`) joined to
the market regime at entry (`session_regime`). Produces expectancy broken down by
exit reason, GEX regime at entry, and the IV−RV band the farm signal fired on —
the levers that would let the executor open (or skip) better trades over time.

No Trade Intelligence sink is wired in: its stock-cross-sectional schema (z-score,
quintile, sector) does not fit an options structure, and the wall store already
holds more relevant fields. This is the analytics layer over that store.
"""

from __future__ import annotations

import statistics
from typing import Callable, Dict, List, Optional

from core.options_wall import persistence as pers
from core.options_wall.engine import UNDERLYINGS


def _iv_band(x: Optional[float]) -> str:
    if x is None:
        return "unknown"
    if x < 0:
        return "IV<RV"
    if x < 2:
        return "0–2 pt"
    if x < 4:
        return "2–4 pt"
    return ">4 pt"


def _regime_bucket(regime: Optional[str]) -> str:
    r = regime or ""
    if "Positive" in r:
        return "Positive GEX"
    if "Negative" in r:
        return "Negative GEX"
    return "unknown"


def closed_trades_with_context(name: Optional[str] = None,
                               db_path=pers.WALL_RESULTS_DB) -> List[Dict]:
    """Closed paper flies enriched with the regime/IV−RV at entry.

    Each trade is joined to the most recent `session_regime` row at or before its
    entry timestamp for the same underlying. Read-only; returns [] on an empty or
    trades-less DB.
    """
    names = [name] if name else list(UNDERLYINGS)
    if not db_path.exists() or not pers._trades_table_exists(db_path):
        return []
    conn = pers._connect_ro(db_path)
    out: List[Dict] = []
    try:
        has_regime = conn.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='main' AND table_name='session_regime'").fetchone()[0]
        for nm in names:
            sym = UNDERLYINGS[nm]
            rows = conn.execute(
                "SELECT * FROM trades WHERE underlying=? AND exit_ts IS NOT NULL "
                "ORDER BY entry_ts", [sym]).fetchall()
            for r in rows:
                t = dict(zip(pers._TRADE_COLS, r))
                t["index"] = nm
                t["regime"] = t["iv_minus_rv"] = t["pin_conviction"] = None
                if has_regime and t["entry_ts"] is not None:
                    ctx = conn.execute(
                        "SELECT regime, atm_iv, realized_vol, pin_conviction "
                        "FROM session_regime WHERE underlying=? AND ts<=? "
                        "ORDER BY ts DESC LIMIT 1", [sym, t["entry_ts"]]).fetchone()
                    if ctx:
                        t["regime"] = ctx[0]
                        if ctx[1] is not None and ctx[2] is not None:
                            t["iv_minus_rv"] = ctx[1] - ctx[2]
                        t["pin_conviction"] = ctx[3]
                out.append(t)
    finally:
        conn.close()
    return out


def _agg(trades: List[Dict]) -> Dict:
    nets = [t["net_pnl"] for t in trades if t["net_pnl"] is not None]
    roms = [t["return_on_margin"] for t in trades if t["return_on_margin"] is not None]
    wins = sum(1 for x in nets if x > 0)
    return {
        "n": len(trades),
        "wins": wins,
        "win_rate": (wins / len(nets)) if nets else None,
        "total_net": sum(nets) if nets else 0.0,
        "avg_net": statistics.mean(nets) if nets else None,
        "avg_rom": statistics.mean(roms) if roms else None,
    }


def _group(trades: List[Dict], keyfn: Callable[[Dict], str]) -> Dict[str, Dict]:
    groups: Dict[str, List[Dict]] = {}
    for t in trades:
        groups.setdefault(keyfn(t), []).append(t)
    return {k: _agg(v) for k, v in sorted(groups.items(), key=lambda kv: str(kv[0]))}


def evidence_summary(name: Optional[str] = None,
                     db_path=pers.WALL_RESULTS_DB) -> Dict:
    """Overall expectancy + breakdowns by exit reason, entry regime, IV−RV band."""
    trades = closed_trades_with_context(name, db_path)
    return {
        "n_closed": len(trades),
        "overall": _agg(trades),
        "by_exit_reason": _group(trades, lambda t: t.get("exit_reason") or "unknown"),
        "by_regime": _group(trades, lambda t: _regime_bucket(t.get("regime"))),
        "by_iv_band": _group(trades, lambda t: _iv_band(t.get("iv_minus_rv"))),
    }
