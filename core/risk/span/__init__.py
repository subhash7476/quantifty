"""
SPAN Parameter Infrastructure (MM9.4-S2)
========================================
Deterministic, immutable data foundation for SPAN margin computation.

Modules:
  span_snapshot   — Immutable DTOs (SpanSnapshot, SpanRiskArray)
  span_parser     — Parser registry keyed by schema_version
  span_repository — On-disk snapshot read path, checksum verification
  span_freshness  — Expected trading-date computation
  span_readiness  — Startup readiness evaluation (READY / REFUSE)
  span_pipeline   — Fetch-job pipeline primitives (download, promote, archive)
"""

from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray
from core.risk.span.span_parser import ParserRegistry, UnsupportedSpanSchema
from core.risk.span.span_repository import SpanRepository
from core.risk.span.span_freshness import expected_span_date
from core.risk.span.span_readiness import (
    SpanReadinessVerdict,
    evaluate,
    assess,
    build_span_readiness,
)

__all__ = [
    "SpanSnapshot",
    "SpanRiskArray",
    "ParserRegistry",
    "UnsupportedSpanSchema",
    "SpanRepository",
    "expected_span_date",
    "SpanReadinessVerdict",
    "evaluate",
    "assess",
    "build_span_readiness",
]
