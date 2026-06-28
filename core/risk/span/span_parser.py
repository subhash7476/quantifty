"""
SPAN Parser Registry (MM9.4-S2).

A registry of parse functions keyed by schema_version. Unknown versions raise
UnsupportedSpanSchema. The module-level parse_span_csv function provides a
convenience entry point that dispatches through the default registry.

The NSE SPAN CSV schema uses named constants (e.g. NSE_SCHEMA_V1) flagged
for implementation-time confirmation when the actual exchange file format is
inspected. The architecture supports future parser versions without changing
the SpanSnapshot DTO.
"""

from typing import Callable, Dict, List, Optional

from core.risk.span.span_snapshot import SpanSnapshot


class UnsupportedSpanSchema(ValueError):
    """Raised when a schema_version has no registered parser."""


class ParserRegistry:
    """Registry mapping schema_version strings to parse functions.

    Thread-safe by design (immutable after registration; registration
    happens at module load time / script startup, never during trading).
    """

    def __init__(self):
        self._parsers: Dict[str, Callable[[dict], SpanSnapshot]] = {}

    def register(self, schema_version: str,
                 parser_fn: Callable[[dict], SpanSnapshot]) -> None:
        self._parsers[schema_version] = parser_fn

    def parse(self, schema_version: str,
              raw_data: dict) -> SpanSnapshot:
        parser = self._parsers.get(schema_version)
        if parser is None:
            raise UnsupportedSpanSchema(
                f"No parser registered for schema version {schema_version!r}; "
                f"known versions: {list(self._parsers)}"
            )
        return parser(raw_data)

    def versions(self) -> List[str]:
        return list(self._parsers)


# Default global registry used by parse_span_csv().
_DEFAULT_REGISTRY = ParserRegistry()


def register_parser(schema_version: str,
                    parser_fn: Callable[[dict], SpanSnapshot]) -> None:
    """Register a parser in the default global registry (convenience)."""
    _DEFAULT_REGISTRY.register(schema_version, parser_fn)


def parse_span_csv(schema_version: str, raw_data: dict) -> SpanSnapshot:
    """Parse raw exchange data through the default registry.

    Args:
        schema_version: Version identifier (e.g. "v1").
        raw_data:       Dict extracted from the exchange CSV/metadata.

    Returns:
        A fully-populated SpanSnapshot.

    Raises:
        UnsupportedSpanSchema: If no parser is registered for version.
    """
    return _DEFAULT_REGISTRY.parse(schema_version, raw_data)
