"""Block G — SpanSnapshot / SpanRiskArray DTO immutability (MM9.4-S2)."""

from datetime import date, datetime

import pytz

from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray


def test_span_snapshot_is_frozen():
    snap = SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="abc123",
        risk_arrays={},
        metadata={},
    )
    try:
        snap.snapshot_date = date(2026, 6, 29)
        assert False, "SpanSnapshot must be frozen"
    except Exception:
        pass


def test_span_risk_array_is_frozen():
    ra = SpanRiskArray(symbol="NIFTY", risk_metrics={"scan_risk": 0.15})
    try:
        ra.symbol = "BANKNIFTY"
        assert False, "SpanRiskArray must be frozen"
    except Exception:
        pass


def test_span_snapshot_carries_required_fields():
    snap = SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="abc123",
        risk_arrays={"NIFTY": SpanRiskArray(symbol="NIFTY", risk_metrics={"sr": 0.15})},
        metadata={"downloaded_at": datetime(2026, 6, 28, 10, 0, tzinfo=pytz.UTC)},
    )
    assert snap.snapshot_date == date(2026, 6, 28)
    assert snap.schema_version == "v1"
    assert snap.exchange == "NSE"
    assert snap.segment == "FO"
    assert snap.file_hash == "abc123"
    assert "NIFTY" in snap.risk_arrays
    assert snap.risk_arrays["NIFTY"].symbol == "NIFTY"
    assert snap.metadata["downloaded_at"] is not None


def test_span_risk_array_holds_metrics():
    ra = SpanRiskArray(
        symbol="BANKNIFTY",
        risk_metrics={"scan_risk": 0.18, "extreme_loss": 0.05, "spread": 0.02},
    )
    assert ra.risk_metrics["scan_risk"] == 0.18
    assert ra.risk_metrics["extreme_loss"] == 0.05


def test_span_snapshot_empty_risk_arrays():
    snap = SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="abc123",
        risk_arrays={},
        metadata={},
    )
    assert snap.risk_arrays == {}


def test_span_snapshot_deterministic_repr():
    snap1 = SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="abc123",
        risk_arrays={"A": SpanRiskArray("A", {"x": 1.0})},
        metadata={"k": "v"},
    )
    snap2 = SpanSnapshot(
        snapshot_date=date(2026, 6, 28),
        schema_version="v1",
        exchange="NSE",
        segment="FO",
        file_hash="abc123",
        risk_arrays={"A": SpanRiskArray("A", {"x": 1.0})},
        metadata={"k": "v"},
    )
    assert snap1 == snap2
