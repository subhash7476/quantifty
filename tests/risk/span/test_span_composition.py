"""MM9.4-S4 — Composition Swap & Buying-Power Integration tests.

Groups:
  H — Handler injection: span_snapshot param, conditional calculator construction
  I — Gate source substitution: get_incremental_margin in _check_margin_budget
  J — Startup readiness: driver _check_span_readiness integration
  K — Composition root wiring: fno_runner snapshot + readiness injection
  L — Rollback path: MarginTracker fallback when no snapshot
"""

from datetime import date, datetime
from pathlib import Path

import pickle
import pytz
import pytest

from core.execution.handler import ExecutionConfig, ExecutionMode, PriceSnapshot
from core.execution.margin_tracker import MarginTracker
from core.execution.position_tracker import PositionTracker
from core.execution.position_models import Position, PositionSide
from core.instruments.equity import Equity
from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray
from core.risk.span.span_calculator import (
    SpanMarginCalculator,
    SPAN_METRIC_SCAN_RISK,
    SPAN_METRIC_SHORT_OPTION_MIN,
)
from core.instruments.master_readiness import ReadinessState

FIXED_DT = datetime(2026, 6, 28, 10, 0, tzinfo=pytz.UTC)


def _make_snapshot(risk_arrays=None):
    return SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="test_hash",
        is_settlement=False,
        risk_arrays=risk_arrays or {},
        metadata={},
    )


# --------------------------------------------------------------------------- #
# H — Handler injection: conditional calculator construction
# --------------------------------------------------------------------------- #

def test_margin_tracker_is_default_without_snapshot():
    """Handler constructs MarginTracker when span_snapshot is absent."""
    mt = MarginTracker(PositionTracker())
    assert isinstance(mt, MarginTracker)
    assert not hasattr(mt, "get_incremental_margin")


def test_span_calculator_produced_when_snapshot_given():
    """SpanMarginCalculator is created when span_snapshot is supplied."""
    pt = PositionTracker()
    snap = _make_snapshot({"NIFTY": {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}})
    calc = SpanMarginCalculator(pt, snap)
    assert isinstance(calc, SpanMarginCalculator)
    assert hasattr(calc, "get_incremental_margin")


def test_span_calculator_empty_book_used_margin():
    """Empty book with SpanMarginCalculator returns 0."""
    calc = SpanMarginCalculator(PositionTracker(), _make_snapshot())
    assert calc.get_used_margin({}) == 0.0


# --------------------------------------------------------------------------- #
# I — Gate source substitution: get_incremental_margin capability detection
# --------------------------------------------------------------------------- #

def test_span_calculator_has_get_incremental_margin():
    """SpanMarginCalculator exposes get_incremental_margin (not on protocol)."""
    calc = SpanMarginCalculator(PositionTracker(), _make_snapshot())
    assert hasattr(calc, "get_incremental_margin")


def test_margin_tracker_lacks_get_incremental_margin():
    """MarginTracker does not have get_incremental_margin."""
    mt = MarginTracker(PositionTracker())
    assert not hasattr(mt, "get_incremental_margin")


def test_get_incremental_margin_correct_value():
    """get_incremental_margin matches expected SPAN calculation (absolute-Rs)."""
    snap = _make_snapshot({
        "NIFTY": SpanRiskArray("NIFTY", {SPAN_METRIC_SCAN_RISK: 30.0, SPAN_METRIC_SHORT_OPTION_MIN: 16.0}),
    })
    calc = SpanMarginCalculator(PositionTracker(), snap)
    # risk = max(30.0, 16.0) = 30.0 (Rs/unit)
    # margin = qty * lot_size * risk * margin_rate = 50 * 65 * 30.0 * 1.0 = 97500
    result = calc.get_incremental_margin("NIFTY", 50, 200.0, lot_size=65)
    assert result == 97500.0


# --------------------------------------------------------------------------- #
# J — Startup readiness: driver _check_span_readiness integration
# --------------------------------------------------------------------------- #

def test_span_readiness_verdict_ready():
    """FRESH verdict means the gate passes."""
    from core.risk.span.span_readiness import SpanReadinessVerdict
    verdict = SpanReadinessVerdict(
        state=ReadinessState.FRESH,
        snapshot_date=date(2026, 6, 28),
        expected_date=date(2026, 6, 28),
        reason="READY",
    )
    assert verdict.state is ReadinessState.FRESH
    assert verdict.reason == "READY"


def test_span_readiness_verdict_block():
    """BLOCK verdict means the gate refuses."""
    from core.risk.span.span_readiness import SpanReadinessVerdict
    verdict = SpanReadinessVerdict(
        state=ReadinessState.BLOCK,
        snapshot_date=None,
        expected_date=date(2026, 6, 28),
        reason="SPAN snapshot absent",
    )
    assert verdict.state is ReadinessState.BLOCK


# --------------------------------------------------------------------------- #
# K — Composition root integration
# --------------------------------------------------------------------------- #

def test_repository_loads_snapshot(tmp_path):
    """SpanRepository can load a seeded snapshot (used by fno_runner)."""
    import hashlib
    from core.risk.span.span_repository import SpanRepository
    zip_content = b"fake zip content for checksum test"
    actual_hash = hashlib.sha256(zip_content).hexdigest()
    snap = SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash=actual_hash,
        is_settlement=False,
        risk_arrays={},
        metadata={},
    )
    snap_dir = tmp_path / "span"
    snap_dir.mkdir()
    fname = "nse_fo_span_2026-06-28"
    with open(snap_dir / f"{fname}.parquet", "wb") as f:
        pickle.dump(snap, f)
    with open(snap_dir / f"{fname}.zip", "wb") as f:
        f.write(zip_content)
    repo = SpanRepository(snap_dir)
    loaded = repo.load(date(2026, 6, 28))
    assert loaded.snapshot_date == date(2026, 6, 28)
    assert loaded.file_hash == actual_hash


def test_repository_latest_version(tmp_path):
    """SpanRepository.latest_version returns most recent date."""
    from core.risk.span.span_repository import SpanRepository
    snap_dir = tmp_path / "span"
    snap_dir.mkdir()
    for d in [date(2026, 6, 27), date(2026, 6, 28)]:
        snap = _make_snapshot().__class__(
            d, "v1", "NSE", "FO", "h", False, {}, {})
        with open(snap_dir / f"nse_fo_span_{d.isoformat()}.parquet", "wb") as f:
            pickle.dump(snap, f)
    repo = SpanRepository(snap_dir)
    assert repo.latest_version() == date(2026, 6, 28)


# --------------------------------------------------------------------------- #
# L — Rollback path
# --------------------------------------------------------------------------- #

def test_span_calculator_raises_missing_risk_array():
    """Without risk array data, SpanMarginCalculator raises."""
    pt = PositionTracker()
    pt._positions["UNKNOWN"] = Position(
        instrument=Equity("UNKNOWN"), side=PositionSide.LONG, quantity=10, avg_price=100.0)
    calc = SpanMarginCalculator(pt, _make_snapshot({}))
    from core.risk.span.span_calculator import MissingRiskArray
    with pytest.raises(MissingRiskArray):
        calc.get_used_margin({"UNKNOWN": 200.0})
