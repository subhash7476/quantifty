"""
SPAN Readiness — Startup evaluation (MM9.4-S2).

Evaluates whether a SPAN snapshot is available and current for the expected
trading day. Returns READY or REFUSE (no WARN, no grace period).

Intended to be consumed by the LoopDriver startup gate (Phase F), mirroring
the instrument master readiness pattern from core/instruments/master_readiness.py.
"""

from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

from core.instruments.master_readiness import ReadinessState
from core.risk.span.span_freshness import expected_span_date
from core.risk.span.span_repository import SpanRepository


@dataclass(frozen=True)
class SpanReadinessVerdict:
    """Readiness verdict for the SPAN snapshot gate.

    Fields:
      state:          FRESH (ready to start) or BLOCK (refuse to start).
      snapshot_date:  The date of the loaded snapshot, if any.
      expected_date:  The date that was expected.
      reason:         Human-readable explanation.
    """
    state: ReadinessState
    snapshot_date: Optional[date]
    expected_date: date
    reason: str


def evaluate(
    snapshot_date: Optional[date],
    expected_date: date,
) -> SpanReadinessVerdict:
    """Pure evaluation: given a snapshot date and expected date, return a verdict.

    Args:
        snapshot_date: The date of the snapshot (None if absent).
        expected_date: The expected trading date.

    Returns:
        READY if the snapshot_date matches the expected_date.
        BLOCK if the snapshot is absent, corrupt, or stale.
    """
    if snapshot_date is None:
        return SpanReadinessVerdict(
            state=ReadinessState.BLOCK,
            snapshot_date=None,
            expected_date=expected_date,
            reason=f"SPAN snapshot absent for {expected_date}",
        )
    if snapshot_date < expected_date:
        return SpanReadinessVerdict(
            state=ReadinessState.BLOCK,
            snapshot_date=snapshot_date,
            expected_date=expected_date,
            reason=f"SPAN snapshot stale: found {snapshot_date}, expected {expected_date}",
        )
    # Future snapshots are also BLOCK (can't use tomorrow's parameters today)
    if snapshot_date > expected_date:
        return SpanReadinessVerdict(
            state=ReadinessState.BLOCK,
            snapshot_date=snapshot_date,
            expected_date=expected_date,
            reason=f"SPAN snapshot from future: found {snapshot_date}, expected {expected_date}",
        )
    return SpanReadinessVerdict(
        state=ReadinessState.FRESH,
        snapshot_date=snapshot_date,
        expected_date=expected_date,
        reason="READY",
    )


def assess(
    repository: SpanRepository,
    expected: date,
) -> SpanReadinessVerdict:
    """Load a snapshot from the repository and evaluate its freshness.

    Args:
        repository: A SpanRepository instance.
        expected:   The expected trading date.

    Returns:
        READY if the snapshot loads and its date matches expected.
        BLOCK if the snapshot is absent, fails to load, or is stale.
    """
    try:
        snapshot = repository.load(expected)
        return evaluate(snapshot.snapshot_date, expected)
    except FileNotFoundError:
        return SpanReadinessVerdict(
            state=ReadinessState.BLOCK,
            snapshot_date=None,
            expected_date=expected,
            reason=f"SPAN snapshot file not found for {expected}",
        )
    except (ValueError, Exception) as exc:
        return SpanReadinessVerdict(
            state=ReadinessState.BLOCK,
            snapshot_date=None,
            expected_date=expected,
            reason=f"SPAN snapshot corrupt: {exc}",
        )


def build_span_readiness(
    repository: SpanRepository,
) -> Callable[[], SpanReadinessVerdict]:
    """Build a zero-arg readiness checker for the startup gate.

    Args:
        repository: A SpanRepository instance.

    Returns:
        A callable that returns a SpanReadinessVerdict when invoked.
    """
    def _checker() -> SpanReadinessVerdict:
        expected = expected_span_date()
        return assess(repository, expected)
    return _checker
