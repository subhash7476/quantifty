"""nifty_shield_v1 — dumb 13:00 SignalSource (Stage-1 decomposition §3).

Driven on `NSE_INDEX|Nifty 50` 1m bars. At exactly the 13:00 checkpoint bar of a
session (a session with no 13:00 bar is skipped — a Stage-2 live-feed concern, not
a corpus one) it reads the session's published regime/VIX fact, selects
a structure, computes strikes arithmetically, and emits one `SignalEvent` per leg
sharing a deterministic `group_id` (D3). It emits NO EXIT signals, reads no
option marks, sizes nothing, and mutates no platform state (the `entered_today`
flag is source-internal shadow state, explicitly allowed).

Only `core.events` + `core.runtime.signal_source` are imported (ADR-016);
the regime fact is the model boundary (D2) — the DayType model never runs here.
"""
from __future__ import annotations

import uuid
from datetime import date, time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.events import OHLCVBar, SignalEvent, SignalType, TradeStructuralContext
from core.runtime.signal_source import SignalSource

from strategies.nifty_shield_v1 import structures
from strategies.nifty_shield_v1.config import STRATEGY_ID
from strategies.nifty_shield_v1.facts import RegimeFactsReader

_ENTRY_HOUR, _ENTRY_MINUTE = 13, 0
_GROUP_NS = uuid.NAMESPACE_URL


class NiftyShieldSignalSource(SignalSource):
    """Emits one structure's legs at the 13:00 bar of each flat session."""

    def __init__(self, config: Dict[str, Any]):
        self._cfg = dict(config)
        self._reader: Optional[RegimeFactsReader] = None
        self._session_date: Optional[date] = None
        self._entered_today = False

    def on_start(self, context: Optional[Any] = None) -> None:
        # DS2-1: store the reader, do NOT snapshot. Live, today's 13:00 fact
        # does not exist at session start (~09:15) — it is published intraday
        # (DS2-2) and queried lazily at the 13:00 bar. Offline the fact is
        # already present, so the per-session query is a provable no-op.
        self._reader = RegimeFactsReader(self._cfg["facts_db_path"])

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        bar_dt = bar.timestamp
        bar_date = bar_dt.date() if hasattr(bar_dt, "date") else None
        if bar_date is None:
            return []

        # Session rollover: reset the in-memory entered flag on a new session.
        if self._session_date != bar_date:
            self._session_date = bar_date
            self._entered_today = False

        # Only the 13:00 checkpoint bar of a session can trigger.
        if self._entered_today or bar_dt.time() < time(_ENTRY_HOUR, _ENTRY_MINUTE):
            return []
        if bar_dt.time() != time(_ENTRY_HOUR, _ENTRY_MINUTE):
            return []

        fact = self._reader.fact(bar_date)
        if fact is None:
            self._entered_today = True
            return []

        # DS2-3: gate on the intraday 13:00 VIX when the row carries it (live),
        # else the EOD vix_close (offline corpus — byte-identical fallback).
        vix = fact.get("vix_at_checkpoint") or fact.get("vix_close")
        if vix is not None and vix > float(self._cfg.get("vix_skip_above", 20.0)):
            self._entered_today = True
            return []

        self._entered_today = True
        return self._build_legs(bar, fact)

    # ------------------------------------------------------------------ #
    # Signal construction
    # ------------------------------------------------------------------ #
    def _build_legs(self, bar: OHLCVBar, fact: dict) -> List[SignalEvent]:
        regime = fact["regime"]
        conf = float(fact["regime_confidence"])
        vix = fact.get("vix_at_checkpoint") or fact.get("vix_close")
        structure = structures.select_structure(regime, vix, self._cfg)

        base_lots = int(self._cfg.get("max_lots", 2))
        regime_mult = float(self._cfg.get("regime_sizing", {}).get(regime, 0.5))
        vix_reduce = (
            vix is not None
            and vix > float(self._cfg.get("vix_reduce_above", 16.0))
            and structure not in ("short_strangle",)
        )

        sl_distance, risk_r = self._risk_declaration(structure, base_lots)
        group_id = str(uuid.uuid5(
            _GROUP_NS, f"{STRATEGY_ID}:{self._session_date}:{structure}"))

        context = TradeStructuralContext(
            regime_state=regime,
            regime_confidence=conf,
            session_type="PM",
            dispersion_value=0.0,
            dispersion_pct=0.0,
            volatility_value=vix or 0.0,
            volatility_pct=0.0,
            breadth_ratio=0.0,
            signal_rank=1,
            signal_percentile=conf,
            sl_distance=sl_distance,
            risk_r=risk_r,
        )

        legs = structures.compute_legs(structure, float(bar.close), self._cfg,
                                       self._session_date)
        signals = []
        for leg in legs:
            metadata = {
                "group_id": group_id,
                "structure": structure,
                "leg_role": leg["leg_role"],
                "strike": leg["strike"],
                "expiry": leg["expiry"],
                "option_type": leg["option_type"],
                "base_lots": base_lots,
                "regime_mult": regime_mult,
                "vix_reduce": vix_reduce,
                "sl_distance": sl_distance,
                "risk_r": risk_r,
                "exit": {
                    "tp_pct": float(self._cfg.get("profit_target_pct", 0.50)),
                    "sl_mult": float(self._cfg.get("stop_loss_multiplier", 2.0)),
                    "hard_exit": "15:15",
                    "max_portfolio_delta": float(
                        self._cfg.get("max_portfolio_delta", 500)),
                },
            }
            signals.append(SignalEvent(
                strategy_id=STRATEGY_ID,
                symbol=leg["symbol"],
                timestamp=bar.timestamp,
                signal_type=SignalType.SELL if leg["signal_type"] == "SELL"
                else SignalType.BUY,
                confidence=conf,
                metadata=metadata,
                context=context,
            ))
        return signals

    def _risk_declaration(self, structure: str, base_lots: int):
        """Structure-derived sl_distance (points) + risk_r (Rs at declared lots).

        Defined structures: wing width is the worst-case loss distance.
        Undefined (straddle/strangle): a stated stress distance (§7a view).
        """
        lot_size = int(self._cfg.get("lot_size", 75))
        defined = {
            "bull_put_spread": int(self._cfg.get("directional_wing_pts", 150)),
            "bear_call_spread": int(self._cfg.get("directional_wing_pts", 150)),
            "iron_fly": int(self._cfg.get("wing_offset_pts", 100)),
        }
        sl_distance = defined.get(structure, int(self._cfg.get("undefined_risk_stress_pts", 200)))
        risk_r = float(sl_distance * lot_size * base_lots)
        return float(sl_distance), risk_r
