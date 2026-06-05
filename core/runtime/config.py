"""
DriverConfig — runtime configuration for the Deterministic Loop Driver
----------------------------------------------------------------------
The single configuration object the LoopDriver reads (DRIVER_SPECIFICATION.md
section 13). It carries only the **infra** fields the old RunnerConfig had; the
strategy fields (strategy_ids / log_signals / disable_state_update) are
deliberately excluded (RUNNER_DEPENDENCY_ANALYSIS.md section 4, ADR-002).

This object holds *settings*, not collaborators. The driver consumes the
already-constructed ExecutionHandler / MarketDataProvider / Clock / SignalSource
by dependency injection; wiring those lives at the entry-script layer (scripts/),
not here. That keeps the driver testable with mocks and keeps secrets
(broker credentials, data paths) out of this object (SALVAGE_REPORT.md section 8).

Platform infrastructure only — no strategy, signal, or alpha logic
(PLATFORM_CONSTITUTION Principle 5).
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Mode(Enum):
    """
    Driver run mode. Gates clock semantics (DRIVER_SPECIFICATION.md section 6)
    and watchdog activation (section 9.5).

    LIVE   — wall-clock RealTimeClock; watchdog (staleness + heartbeat) active.
    REPLAY — data-driven ReplayClock; watchdog disabled (wall-clock staleness is
             meaningless against bar-time and would false-trip).
    """
    LIVE = "LIVE"
    REPLAY = "REPLAY"


@dataclass(frozen=True)
class DriverConfig:
    """
    Immutable runtime configuration for the LoopDriver (section 13).

    Required:
        mode: LIVE or REPLAY (gates clock + watchdog).
        symbols: instrument keys the provider tracks. Must be non-empty — the
            startup-validation gate refuses to run with no symbols (section 11.4).

    Optional (sensible defaults carried from the legacy runner where applicable):
        poll_interval_s: live no-bar polling cadence (section 7.3).
        max_bars: replay / safety guard; None = unbounded (live).
        heartbeat_path: watchdog beacon file (section 9.4).
        telemetry_enabled: whether the driver constructs a TelemetryPublisher
            (section 10). Defaults by mode when left as None — True for LIVE,
            False for REPLAY — and is resolved to a concrete bool at construction.
        telemetry_host / telemetry_port / telemetry_node: publisher endpoint and
            topic suffix; the port is the TelemetryBridge SUB endpoint (section 10.1).
        telemetry_interval_s: telemetry publish throttle (section 10.2); carried
            from the old loop (5.0s).
        require_reconciliation_on_start: startup-gate strictness (section 11.4).
            True by default; set False only as a deliberate operator override.

    The config validates only what it can know in isolation: a valid mode, a
    non-empty symbol list, a positive poll interval, and a None-or-positive
    max_bars. Everything else (broker reachability, data availability,
    reconciliation) is validated by the driver's startup gate, not here.
    """

    mode: Mode
    symbols: List[str]
    poll_interval_s: float = 0.5
    max_bars: Optional[int] = None
    heartbeat_path: str = "logs/heartbeat.json"
    telemetry_enabled: Optional[bool] = None
    telemetry_host: str = "127.0.0.1"
    telemetry_port: int = 5560
    telemetry_node: str = "trade_loop"
    telemetry_interval_s: float = 5.0
    require_reconciliation_on_start: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.mode, Mode):
            raise TypeError(
                f"mode must be a Mode (LIVE/REPLAY), got {type(self.mode).__name__}"
            )
        if not self.symbols:
            raise ValueError("symbols must be non-empty (startup gate, section 11.4)")
        if self.poll_interval_s <= 0:
            raise ValueError("poll_interval_s must be > 0")
        if self.max_bars is not None and self.max_bars <= 0:
            raise ValueError("max_bars must be None or a positive int")

        # Resolve the mode-dependent telemetry default to a concrete bool.
        # Frozen dataclass: assign via object.__setattr__.
        if self.telemetry_enabled is None:
            object.__setattr__(self, "telemetry_enabled", self.mode is Mode.LIVE)

    @property
    def is_live(self) -> bool:
        """True in LIVE mode. The watchdog runs only when this is True (section 9.5)."""
        return self.mode is Mode.LIVE

    @property
    def is_replay(self) -> bool:
        """True in REPLAY mode."""
        return self.mode is Mode.REPLAY
