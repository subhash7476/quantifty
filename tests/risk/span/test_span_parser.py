"""Block H — Parser registry + UnsupportedSpanSchema (MM9.4-S2, MM9.5-S1)."""

from datetime import date

import pytest

import hashlib

from datetime import date

import pytest

from core.risk.span.span_parser import (
    ParserRegistry,
    register_parser,
    parse_span_xml,
)
from core.risk.span.span_snapshot import (
    SpanSnapshot,
    SpanRiskArray,
    UnsupportedSpanSchema,
)


def test_registry_starts_empty():
    reg = ParserRegistry()
    assert reg.versions() == []
    with pytest.raises(UnsupportedSpanSchema):
        reg.parse("9.99", b"some bytes")


def test_register_and_parse_v400():
    reg = ParserRegistry()

    def _v400_parser(raw: bytes) -> SpanSnapshot:
        return SpanSnapshot(
            snapshot_date=date(2026, 6, 28),
            schema_version="4.00",
            exchange="NSE",
            segment="FO",
            file_hash=hashlib.sha256(raw).hexdigest(),
            is_settlement=False,
            risk_arrays={},
            metadata={},
        )

    reg.register("4.00", _v400_parser)
    assert "4.00" in reg.versions()
    result = reg.parse("4.00", b"hello")
    assert isinstance(result, SpanSnapshot)
    assert result.schema_version == "4.00"
    assert result.file_hash == hashlib.sha256(b"hello").hexdigest()


def test_unknown_version_raises():
    reg = ParserRegistry()
    with pytest.raises(UnsupportedSpanSchema):
        reg.parse("9.99", b"ignored")


def test_parse_span_xml_module_function():
    """The module-level parse_span_xml dispatches through the global registry."""
    register_parser("4.00", lambda raw: SpanSnapshot(
        date(2026, 6, 28), "4.00", "NSE", "FO", hashlib.sha256(raw).hexdigest(), False, {}, {}))
    result = parse_span_xml("4.00", b"abc")
    assert result is not None
    assert result.schema_version == "4.00"


def test_register_parser_deprecated():
    """register_parser is the legacy module-level registration (or no-op)."""
    register_parser("4.00", lambda raw: None)


def test_multiple_versions_coexist():
    reg = ParserRegistry()
    reg.register("4.00", lambda raw: SpanSnapshot(date(2026, 6, 28), "4.00", "NSE", "FO", "", False, {}, {}))
    reg.register("4.01", lambda raw: SpanSnapshot(date(2026, 6, 28), "4.01", "NSE", "FO", "", False, {}, {}))
    assert set(reg.versions()) == {"4.00", "4.01"}
