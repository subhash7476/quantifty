"""
SignalSource — the strategy-agnostic signal seam
-------------------------------------------------
The single, abstract boundary through which *all* trading intent enters the
platform at runtime. The Deterministic Loop Driver (docs/DRIVER_SPECIFICATION.md
section 5) pulls signals from a SignalSource once per bar and routes them to the
ExecutionHandler. Strategies, a discretionary console, or a replay tool inject
intent by *implementing* this interface — never by calling the ExecutionHandler
directly (ADR-006: the LoopDriver is the sole runtime orchestrator).

Governing law:
- PLATFORM_CONSTITUTION Principle 3 (Deterministic Operation) and Principle 5
  (Platform/Strategy Separation).
- ADR-002 (Platform/Strategy Separation): the allowed dependency is
  Strategy -> Platform. This module is platform-owned; a concrete strategy
  depends on it, never the reverse. It therefore imports no strategy code.
- ADR-003 (Deterministic Processing): the contract is a synchronous *pull*
  (the driver asks the source on each bar, on the driver's thread, in a fixed
  order). A push model would destroy deterministic ordering and the
  single-thread guarantee, so it is intentionally absent from this interface.

This module contains NO concrete strategy, NO signal-generation, and NO alpha
logic. It defines only the contract.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from core.events import OHLCVBar, SignalEvent


class SignalSource(ABC):
    """
    Abstract source of trading signals consumed by the LoopDriver.

    Contract (DRIVER_SPECIFICATION.md section 5.2 — synchronous pull, never
    push):

        on_bar(bar) -> List[SignalEvent]
            Called once per bar, synchronously, on the driver thread. Returns
            zero or more SignalEvents to route, **in priority order** (the list
            order *is* the routing order; the driver does not re-rank). An empty
            list is the normal "do nothing this bar" case. The method MUST be
            side-effect-free with respect to platform state.

    The same interface serves every client shape without the driver ever
    branching on type (DRIVER_SPECIFICATION.md section 5.3):

      * Futures strategy   — returns directional BUY/SELL/EXIT signals.
      * Option strategy    — returns option signals (strike/expiry chosen inside
                             the source).
      * Discretionary      — backed by a thread-safe queue the human/UI writes
                             to; on_bar drains the queue synchronously so an
                             asynchronous actor fits the synchronous pull model
                             without breaking the single execution path.
      * Replay engine      — replays previously recorded SignalEvents keyed by
                             timestamp (reproduction, not backtesting — it
                             injects recorded signals, it does not generate
                             them).

    What an implementation MUST NOT do (DRIVER_SPECIFICATION.md section 5.4):
      * place orders directly (that would bypass ExecutionHandler.process_signal
        and violate ADR-006);
      * hold a handle to the ledger, broker, or trackers (violates ADR-001 /
        ADR-005);
      * call back into the driver during on_bar (no driver-thread reentrancy).

    Implementations obtain any inputs they need themselves; the driver injects
    only the bar (and an optional read-only context at on_start). The driver
    does not feed analytics into the source.
    """

    def on_start(self, context: Optional[Any] = None) -> None:
        """
        Optional lifecycle hook invoked once before the loop begins pulling
        bars. Use it for warmup or subscription setup.

        Args:
            context: An optional, read-only context object the driver may pass.
                It MUST NOT be (or expose) the ledger, broker, or
                ExecutionHandler — that would violate the section 5.4 boundary.
                The driver injects nothing into on_bar itself (section 5.2);
                this hook is the only place a source receives anything beyond
                the bar.

        The base implementation is a no-op; override only if the source needs
        startup work.
        """
        return None

    @abstractmethod
    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        """
        Produce the signals to route for this bar.

        Args:
            bar: The current OHLCVBar. The driver advances the Clock to
                bar.timestamp before this call and pairs each returned signal
                with current_price = bar.close when routing to
                ExecutionHandler.process_signal (DRIVER_SPECIFICATION.md
                sections 4 and 8).

        Returns:
            A list of SignalEvents in priority/routing order. Return an empty
            list to take no action this bar. Implementations must not mutate
            platform state here.
        """
        raise NotImplementedError

    def on_stop(self) -> None:
        """
        Optional lifecycle hook invoked once during shutdown (driver STOPPING,
        DRIVER_SPECIFICATION.md section 3). Use it to flush or close
        source-owned resources. The base implementation is a no-op.
        """
        return None
