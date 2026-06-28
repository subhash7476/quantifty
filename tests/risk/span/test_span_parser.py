"""Block H — Parser registry + UnsupportedSpanSchema (MM9.4-S2)."""

from datetime import date

import pytest

from core.risk.span.span_parser import (
    ParserRegistry,
    UnsupportedSpanSchema,
    parse_span_csv,
    register_parser,
)
from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray


def test_registry_starts_empty():
    reg = ParserRegistry()
    assert reg.versions() == []
    with pytest.raises(UnsupportedSpanSchema):
        reg.parse("v99", {"key": "val"})


def test_register_and_parse_v1():
    reg = ParserRegistry()

    def _v1_parser(data: dict) -> SpanSnapshot:
        return SpanSnapshot(
            snapshot_date=date(2026, 6, 28),
            schema_version="v1",
            exchange="NSE",
            segment="FO",
            file_hash=data.get("file_hash", ""),
            risk_arrays={
                s["symbol"]: SpanRiskArray(s["symbol"], s["metrics"])
                for s in data.get("scrips", [])
            },
            metadata={},
        )

    reg.register("v1", _v1_parser)
    assert "v1" in reg.versions()
    result = reg.parse("v1", {"file_hash": "xyz", "scrips": [
        {"symbol": "NIFTY", "metrics": {"sr": 0.15}},
    ]})
    assert isinstance(result, SpanSnapshot)
    assert result.schema_version == "v1"
    assert result.file_hash == "xyz"
    assert "NIFTY" in result.risk_arrays


def test_unknown_version_raises():
    reg = ParserRegistry()
    with pytest.raises(UnsupportedSpanSchema):
        reg.parse("v999", {})


def test_parse_span_csv_module_function():
    """The module-level parse_span_csv dispatches through the global registry."""
    register_parser("v1", lambda d: SpanSnapshot(
        date(2026, 6, 28), "v1", "NSE", "FO", d.get("file_hash", ""), {}, {}))
    result = parse_span_csv("v1", {"file_hash": "abc"})
    assert result is not None
    assert result.schema_version == "v1"


def test_register_parser_deprecated():
    """register_parser is the legacy module-level registration (or no-op)."""
    # This should not raise
    register_parser("v1", lambda d: None)


def test_multiple_versions_coexist():
    reg = ParserRegistry()
    reg.register("v1", lambda d: SpanSnapshot(date(2026, 6, 28), "v1", "NSE", "FO", "", {}, {}))
    reg.register("v2", lambda d: SpanSnapshot(date(2026, 6, 28), "v2", "NSE", "FO", "", {}, {}))
    assert set(reg.versions()) == {"v1", "v2"}
