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

HORIZON (audit Finding A, resolved by disclosure): the regime label this reads is
a **full-session** (09:15-15:29) KMeans cluster, predicted at 13:00 from partial
features, and consumed over 13:00-15:15. It is a **directional prior**, not a
same-horizon forecast. What the evidence supports is a BullTrend-minus-BearTrend
forward-window separation of +0.255 pp (95% CI [+0.197, +0.312], n=1606 OOS
sessions). The trainer's 75-85% checkpoint accuracy is accuracy against the
full-session label and says nothing directly about the traded window, and
`regime_confidence` is confidence in the full-session class rather than a
probability about the afternoon. Do not derive a threshold or sizing rule as if
the label described 13:00-15:15.
See docs/reports/index_research/DAYTYPE_HORIZON_DISCLOSURE.md
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.events import OHLCVBar, SignalEvent, SignalType, TradeStructuralContext
from core.runtime.signal_source import SignalSource

from strategies.nifty_shield_v1 import structures
from strategies.nifty_shield_v1.config import STRATEGY_ID
from strategies.nifty_shield_v1.facts import RegimeFactsReader

_ENTRY_HOUR, _ENTRY_MINUTE = 13, 0
# Live fact-publication tolerance: the entry may fire on any bar from the 13:00
# checkpoint through 13:00 + this many minutes, so a publisher that needs a few
# minutes to compute the 13pm fact can still deliver it before the session is
# skipped. Offline, the fact is already present at 13:00, so this is a no-op.
_ENTRY_WINDOW_MINUTES = 10
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

    def _entry_window_end(self) -> time:
        """Last bar time (inclusive) on which an entry may fire."""
        window_minutes = int(self._cfg.get("entry_window_minutes", _ENTRY_WINDOW_MINUTES))
        return (datetime.combine(date.min, time(_ENTRY_HOUR, _ENTRY_MINUTE))
                + timedelta(minutes=window_minutes)).time()

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        bar_dt = bar.timestamp
        bar_date = bar_dt.date() if hasattr(bar_dt, "date") else None
        if bar_date is None:
            return []

        # Session rollover: reset the in-memory entered flag on a new session.
        if self._session_date != bar_date:
            self._session_date = bar_date
            self._entered_today = False

        # Only within the entry window (13:00 -> 13:00 + window) of a session can
        # a structure be emitted. Before the window: nothing. After it expires:
        # latch so the session is skipped (no fact ever arrived in time).
        if self._entered_today or bar_dt.time() < time(_ENTRY_HOUR, _ENTRY_MINUTE):
            return []
        if bar_dt.time() > self._entry_window_end():
            self._entered_today = True
            return []

        fact = self._reader.fact(bar_date)
        if fact is None:
            # Fact not published yet — keep waiting within the window (do NOT
            # latch): the reader re-queries the store on a miss, so a fact that
            # arrives a few bars later is seen on a subsequent bar.
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
        # Structure selection reads the trailing VIX PERCENTILE, not the level:
        # the absolute 14/16 gates never fired across the live window and made
        # iron_fly / short_strangle unreachable. A store predating the column
        # yields None, which select_structure resolves to the calmest branch.
        vix_pctile = fact.get("vix_pctile")
        structure = structures.select_structure(regime, vix_pctile, self._cfg)
        # Annualised decimal IV for the sigma scale the strikes are anchored to.
        iv = (float(vix) / 100.0) if vix else float(
            self._cfg.get("iv_default", 0.14))

        base_lots = int(self._cfg.get("max_lots", 2))
        regime_mult = float(self._cfg.get("regime_sizing", {}).get(regime, 0.5))
        vix_reduce = (
            vix_pctile is not None
            and float(vix_pctile) > float(
                self._cfg.get("vix_strangle_pctile", 59.0))
            and structure not in ("short_strangle",)
        )

        legs = structures.compute_legs(structure, float(bar.close), self._cfg,
                                       self._session_date, iv)
        sl_distance, risk_r = self._risk_declaration(structure, base_lots, legs)
        dte = max((date.fromisoformat(legs[0]["expiry"])
                   - self._session_date).days, 1)
        avail_decay = structures.available_decay_frac(dte, self._cfg)
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
                "offset_pts": leg["offset_pts"],
                "sigma_pts": leg["sigma_pts"],
                "dte": dte,
                # `spot` feeds the execution-boundary credit gate's reference
                # price. `iv` is India VIX and sizes the sigma strike offsets
                # ONLY — it is deliberately NOT a leg price input: the gate
                # prices each leg at that leg's own implied vol from the chain
                # snapshot, because one flat vol overstated a 6-DTE vertical by
                # ~30% (NIFTY_SHIELD_CREDIT_FLOOR_CALIBRATION_2026-09-09.md).
                "spot": float(bar.close),
                "iv": iv,
                "exit": {
                    # Take-profit is a fraction of the decay AVAILABLE to this
                    # structure over the hold, not of the credit -- see config.
                    "tp_decay_frac": float(
                        self._cfg.get("profit_target_decay_frac", 0.50)),
                    "available_decay_frac": avail_decay,
                    "sl_mult": float(self._cfg.get("stop_loss_multiplier", 2.0)),
                    "sl_frac": float(
                        self._cfg.get("stop_loss_max_loss_frac", 0.50)),
                    # Derived from config, not a literal: the exit manager
                    # reads `exit_time` and a hardcoded string here could
                    # advertise a flatten time the driver does not honour.
                    "hard_exit": "%02d:%02d" % (
                        int(self._cfg.get("exit_time", {}).get("hour", 15)),
                        int(self._cfg.get("exit_time", {}).get("minute", 35))),
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

    def _risk_declaration(self, structure: str, base_lots: int,
                          legs: List[Dict[str, Any]]):
        """Structure-derived sl_distance (points) + risk_r (Rs at declared lots).

        Defined structures: the wing width actually struck is the worst-case
        loss distance -- read off the computed legs, because that width is now
        sigma-anchored and differs session to session rather than being the
        fixed constant it used to be.
        Undefined (straddle/strangle): a stated stress distance (§7a view).
        """
        lot_size = int(self._cfg.get("lot_size", 75))
        if structure in ("bull_put_spread", "bear_call_spread", "iron_fly"):
            sl_distance = float(legs[0]["offset_pts"])
        else:
            sl_distance = float(
                self._cfg.get("undefined_risk_stress_pts", 200))
        risk_r = float(sl_distance * lot_size * base_lots)
        return float(sl_distance), risk_r
