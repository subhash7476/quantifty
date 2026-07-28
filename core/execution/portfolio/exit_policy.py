"""Exit policy protocol — separates exit decisions from the rebalancer.

The rebalancer owns entry and portfolio construction. This module
defines what happens AFTER a position is held: when to take profit,
when to stop out, when to let the signal decide.

A policy returns a decision. The rebalancer applies it. This keeps
the exit logic testable, swappable, and configurable without touching
signal or rebalancing code.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Protocol, Optional


class ExitDecision(Enum):
    HOLD = "hold"              # keep the position, no action
    EXIT_TAKE_PROFIT = "exit_take_profit"  # bank the gain
    EXIT_STOP = "exit_stop"    # cut the loss


@dataclass
class PositionState:
    """Snapshot of a held position at rebalance time."""
    underlying: str
    side: str                   # 'LONG' or 'SHORT'
    entry_date: date
    days_held: int
    cumulative_return: float    # since entry, signed for position direction
    current_z: float            # latest z_ts for this underlying
    current_cap: float          # Rs held in this position


class ExitPolicy(Protocol):
    """Protocol for exit decision engines.

    Called once per held position per rebalance. Returns an ExitDecision.
    The rebalancer applies CLOSE when EXIT_* is returned, HOLD otherwise.
    """

    def evaluate(self, pos: PositionState) -> ExitDecision:
        ...


@dataclass
class TakeProfitExitPolicy:
    """Exit when cumulative return exceeds a configurable threshold.

    Default: 0.5% — validated on TRAIN (+5.19pp) and HOLDOUT (+4.28pp).
    """
    threshold: float = 0.005  # 0.5% cumulative return

    def evaluate(self, pos: PositionState) -> ExitDecision:
        if pos.cumulative_return >= self.threshold:
            return ExitDecision.EXIT_TAKE_PROFIT
        return ExitDecision.HOLD


@dataclass
class CompositeExitPolicy:
    """Combine multiple exit rules. First non-HOLD decision wins."""
    policies: list

    def evaluate(self, pos: PositionState) -> ExitDecision:
        for p in self.policies:
            d = p.evaluate(pos)
            if d != ExitDecision.HOLD:
                return d
        return ExitDecision.HOLD
