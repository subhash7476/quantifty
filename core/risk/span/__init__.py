"""
SPAN Parameter Infrastructure (MM9.5-S2)
========================================
Deterministic, immutable data foundation for SPAN margin computation.

Modules:
  span_snapshot   — Immutable DTOs (SpanSnapshot, SpanRiskArray, etc.)
  span_parser     — Parser registry keyed by schema_version
  span_repository — On-disk snapshot read path, checksum verification
  span_freshness  — Expected trading-date computation
  span_readiness  — Startup readiness evaluation (READY / REFUSE)
  span_pipeline   — Fetch-job pipeline primitives (download, promote, archive)
"""

from core.risk.span.span_snapshot import (
    SpanSnapshot,
    SpanRiskArray,
    UnsupportedSpanSchema,
    SpanFutureContract,
    SpanOptionSeries,
    SpanOptionContract,
)
from core.risk.span.span_parser import ParserRegistry, register_parser, parse_span_xml
from core.risk.span.span_repository import SpanRepository
from core.risk.span.span_freshness import expected_span_date
from core.risk.span.span_readiness import (
    SpanReadinessVerdict,
    evaluate,
    assess,
    build_span_readiness,
)
from core.risk.span.span_calculator import (
    SpanMarginCalculator,
    SpanMarginError,
    UnsupportedInstrument,
    MissingRiskArray,
    MissingRiskMetric,
    SPAN_METRIC_SCAN_RISK,
    SPAN_METRIC_SHORT_OPTION_MIN,
    SPAN_METRIC_PRICE_SCAN_RANGE,
    SPAN_METRIC_VOL_SCAN_RANGE,
    SPAN_METRIC_CVF,
    SPAN_METRIC_INTRA_SPREAD_CHARGE,
    SPAN_METRIC_RISK_FREE_RATE,
)
from core.risk.span.parser_v400 import parse_span_xml as _parse_v400

# Register the v4.00 parser in the default global registry (ADR-010).
register_parser("4.00", _parse_v400)

__all__ = [
    "SpanSnapshot",
    "SpanRiskArray",
    "UnsupportedSpanSchema",
    "SpanFutureContract",
    "SpanOptionSeries",
    "SpanOptionContract",
    "ParserRegistry",
    "parse_span_xml",
    "SpanRepository",
    "expected_span_date",
    "SpanReadinessVerdict",
    "evaluate",
    "assess",
    "build_span_readiness",
    "SpanMarginCalculator",
    "SpanMarginError",
    "UnsupportedInstrument",
    "MissingRiskArray",
    "MissingRiskMetric",
    "SPAN_METRIC_SCAN_RISK",
    "SPAN_METRIC_SHORT_OPTION_MIN",
    "SPAN_METRIC_PRICE_SCAN_RANGE",
    "SPAN_METRIC_VOL_SCAN_RANGE",
    "SPAN_METRIC_CVF",
    "SPAN_METRIC_INTRA_SPREAD_CHARGE",
    "SPAN_METRIC_RISK_FREE_RATE",
]
