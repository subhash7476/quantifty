"""Options-Wall paper executor — opens/marks/closes one ATM iron fly per index.

Reads a chain snapshot each cycle, runs the premium-farm screen, and manages at
most one open iron fly per underlying: open on a qualifying farm signal inside the
entry window; close on take-profit, stop-loss, a GEX regime flip to Negative, or the
time stop (session before expiry). P&L is computed directly (fly.py + fees.py); no
group/broker primitives are reused (spec 2026-08-14 pilot §12.4 deviation, by design).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Dict, Optional, Tuple

from core.analytics.chain_scanner import ChainScanner, ScanConfig
from core.options_wall import persistence as pers
from core.options_wall.fly import (FlyLeg, IronFly, build_iron_fly, exit_fees,
                                   mark_to_close, unrealized_pnl)


@dataclass
class PaperConfig:
    wing_pct: float = 0.015
    qty: int = 75
    tp_frac: float = 0.5
    sl_mult: float = 2.0
    entry_start: str = "09:30"
    entry_end: str = "15:00"
    squareoff: str = "15:15"
    min_dte: int = 1


def _hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def _mids(chain) -> Dict[Tuple[float, str], float]:
    out: Dict[Tuple[float, str], float] = {}
    for r in chain:
        bid = getattr(r, "best_bid", None)
        ask = getattr(r, "best_ask", None)
        if bid and ask and bid > 0 and ask > 0:
            mid = (bid + ask) / 2.0
        else:
            mid = r.ltp if r.ltp and r.ltp > 0 else None
        if mid is not None:
            out[(r.strike, r.option_type)] = mid
    return out


class PaperExecutor:
    def __init__(self, config: Optional[PaperConfig] = None,
                 scan_config: Optional[ScanConfig] = None,
                 db_path: Path = pers.WALL_RESULTS_DB):
        self.cfg = config or PaperConfig()
        self.scanner = ChainScanner(scan_config or ScanConfig(wing_pct=self.cfg.wing_pct))
        self.db_path = db_path

    def step(self, underlying, chain, structural, realized_vol, now: datetime) -> Optional[str]:
        mids = _mids(chain)
        open_rows = pers.open_trades(underlying, db_path=self.db_path)
        if open_rows:
            return self._manage(open_rows[0], structural, mids, now)

        if not (_hhmm(self.cfg.entry_start) <= now.time() <= _hhmm(self.cfg.entry_end)):
            return None
        dte = (date.fromisoformat(structural.expiry) - now.date()).days
        if dte < self.cfg.min_dte:
            return None

        farm = [r for r in self.scanner.scan_chain(chain, structural, realized_vol)
                if r.screen == "premium_farm"]
        if not farm:
            return None
        fly = build_iron_fly(chain, structural.underlying_ltp, self.cfg.wing_pct,
                             self.cfg.qty, now.date())
        if fly is None:
            return None
        pers.open_paper_trade(underlying, structural.expiry, fly, now, db_path=self.db_path)
        return "open"

    def _manage(self, row, structural, mids, now) -> Optional[str]:
        fly = self._rehydrate(row)
        reason = None
        if "Negative" in (structural.gex.regime or ""):
            reason = "regime_flip"
        else:
            pnl = unrealized_pnl(fly, mids)
            if pnl is not None and pnl >= self.cfg.tp_frac * row["net_credit"]:
                reason = "tp"
            elif pnl is not None and pnl <= -self.cfg.sl_mult * row["net_credit"]:
                reason = "sl"
        dte = (date.fromisoformat(row["expiry"]) - now.date()).days
        if reason is None and dte <= 1 and now.time() >= _hhmm(self.cfg.squareoff):
            reason = "time_stop"
        if reason is None:
            return None

        cost = mark_to_close(fly, mids)
        efees = exit_fees(fly, mids, now.date())
        if cost is None or efees is None:
            return None
        gross = row["net_credit"] - cost
        net = gross - row["entry_fees"] - efees
        pers.close_paper_trade(row["trade_id"], now, exit_mark=cost, exit_fees=efees,
                               gross_pnl=gross, net_pnl=net, exit_reason=reason,
                               db_path=self.db_path)
        return reason

    def _rehydrate(self, row) -> IronFly:
        legs = [
            FlyLeg("SELL", "CE", row["short_strike"], 0.0),
            FlyLeg("SELL", "PE", row["short_strike"], 0.0),
            FlyLeg("BUY", "CE", row["call_wing"], 0.0),
            FlyLeg("BUY", "PE", row["put_wing"], 0.0),
        ]
        return IronFly(short_strike=row["short_strike"], call_wing=row["call_wing"],
                       put_wing=row["put_wing"], legs=legs, net_credit_per_unit=0.0,
                       qty=row["qty"], net_credit=row["net_credit"],
                       entry_fees=row["entry_fees"], max_loss=row["max_loss"])
