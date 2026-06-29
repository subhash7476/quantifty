"""
SPAN Parser Registry (MM9.5-S1).

A registry of parse functions keyed by schema_version. Unknown versions raise
UnsupportedSpanSchema. The module-level parse function dispatches through the
default registry.

Parser functions receive raw bytes (ADR-009). The registry key is the
<fileFormat> value verbatim (ADR-010).
"""

from typing import Callable, Dict, List

from core.risk.span.span_snapshot import SpanSnapshot, UnsupportedSpanSchema


class ParserRegistry:
    """Registry mapping schema_version strings to parse functions.

    Thread-safe by design (immutable after registration; registration
    happens at module load time / script startup, never during trading).
    """

    def __init__(self):
        self._parsers: Dict[str, Callable[[bytes], SpanSnapshot]] = {}

    def register(self, schema_version: str,
                 parser_fn: Callable[[bytes], SpanSnapshot]) -> None:
        self._parsers[schema_version] = parser_fn

    def parse(self, schema_version: str,
              raw: bytes) -> SpanSnapshot:
        parser = self._parsers.get(schema_version)
        if parser is None:
            raise UnsupportedSpanSchema(
                f"No parser registered for schema version {schema_version!r}; "
                f"known versions: {list(self._parsers)}"
            )
        return parser(raw)

    def versions(self) -> List[str]:
        return list(self._parsers)


# Default global registry used by parse_span_xml().
_DEFAULT_REGISTRY = ParserRegistry()


def register_parser(schema_version: str,
                    parser_fn: Callable[[bytes], SpanSnapshot]) -> None:
    """Register a parser in the default global registry (convenience)."""
    _DEFAULT_REGISTRY.register(schema_version, parser_fn)


def parse_span_xml(schema_version: str, raw: bytes) -> SpanSnapshot:
    """Parse raw exchange data through the default registry.

    Args:
        schema_version: Version identifier (e.g. "4.00").
        raw:            Raw bytes of the SPAN file.

    Returns:
        A fully-populated SpanSnapshot.

    Raises:
        UnsupportedSpanSchema: If no parser is registered for version.
    """
    return _DEFAULT_REGISTRY.parse(schema_version, raw)
