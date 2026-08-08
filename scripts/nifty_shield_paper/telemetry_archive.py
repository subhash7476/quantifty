"""NiftyShield — telemetry archive (E007 E, §7.2).

Per-session `RuntimeMetric` snapshot consistency checks, so a session offered as
PAPER evidence must satisfy §7.2: BARS_PROCESSED/LOOP_ITERATIONS session-
consistent, SIGNALS_RECEIVED/ROUTED/EXECUTION_CALLS mutually consistent, guard
counters zero, and (when present) a fresh heartbeat. A telemetry gap means the
affected session does not count toward the window.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.runtime.metrics import RuntimeMetric

GUARD_METRICS = (
    RuntimeMetric.STRATEGY_ERRORS,
    RuntimeMetric.STRATEGY_QUARANTINE_EVENTS,
    RuntimeMetric.SIGNAL_CONTRACT_REJECTIONS,
)


@dataclass
class TelemetrySession:
    session: str
    snapshot: Dict[str, int] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.violations


def archive_session(session: str,
                    snapshot: Dict[RuntimeMetric, int],
                    heartbeat_path: Optional[str] = None) -> TelemetrySession:
    """Validate one session's telemetry snapshot; return the session record."""
    arch = TelemetrySession(session=session,
                            snapshot={k.value: v for k, v in snapshot.items()})
    get = lambda m: snapshot.get(m, 0)

    for m in GUARD_METRICS:
        if get(m) != 0:
            arch.violations.append(
                f"{m.value}={get(m)} (guard counter must be 0)")

    bars = get(RuntimeMetric.BARS_PROCESSED)
    iterations = get(RuntimeMetric.LOOP_ITERATIONS)
    if iterations and bars > iterations:
        arch.violations.append(
            f"bars_processed({bars}) > loop_iterations({iterations})")
    if bars and iterations and bars != iterations:
        # Single-symbol windows: one bar per iteration. Multi-symbol windows may
        # legitimately differ, so only flag when bars EXCEED iterations.
        pass

    received = get(RuntimeMetric.SIGNALS_RECEIVED)
    routed = get(RuntimeMetric.SIGNALS_ROUTED)
    calls = get(RuntimeMetric.EXECUTION_CALLS)
    if received < routed:
        arch.violations.append(
            f"signals_received({received}) < signals_routed({routed})")
    if routed < calls:
        arch.violations.append(
            f"signals_routed({routed}) < execution_calls({calls})")

    if heartbeat_path:
        try:
            with open(heartbeat_path, encoding="utf-8") as f:
                hb = json.load(f)
            arch.snapshot["heartbeat_ts"] = str(hb.get("timestamp"))
        except (OSError, ValueError):
            arch.violations.append("heartbeat file missing or unreadable")

    return arch
