"""
SignalSource conformance suite — the runnable Strategy Integration Contract
---------------------------------------------------------------------------
MM12.2 (docs/reports/MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §7.1–§7.2):
the offline certification harness an external `SignalSource` implementation
must pass before any PAPER run (the CONFORMANT gate of the promotion ladder,
§14.1). It turns the DRIVER_SPECIFICATION.md §5.4 invariants and the §6
replay-equivalence determinism requirement into checkable assertions instead
of prose (ADR-016; the "checked invariants, not just documented ones"
obligation from the MM11 review §2.2).

Two layers (architecture §7):
- Layer 1 (STATIC)     — checks on the class/instance/package, no bars run.
- Layer 2 (BEHAVIORAL) — checks that drive a fresh source through a recorded
                         bar corpus via a `factory` (a zero-arg callable
                         returning a NEW source per call, so no state leaks
                         between checks or between the replay-twice runs).

Pytest-importable by design: an external strategy repo certifies with a
single test calling `run_conformance(...)`, or per-check for granular
failures. Layer 3 (the runtime `GuardedSignalSource` boundary guard,
ADR-018/ADR-019) is a separate MM12.3 component — this module is offline
certification only and holds NO runtime behavior, NO strategy logic, and NO
alpha (ADR-002).

This module deliberately imports execution/broker types ONLY inside the
forbidden-handle check (they are the contraband being detected); the suite
itself never constructs or touches platform runtime state.
"""

import ast
import inspect
import math
import time
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from core.events import OHLCVBar, SignalEvent, SignalType
from core.runtime.signal_source import SignalSource

# The published contract version a certified strategy records
# (architecture §14.3 — additive-only evolution within a major version).
STRATEGY_CONTRACT_VERSION = "1.0"

# The sanctioned platform import surface for an external strategy package
# (ADR-016). Any other `core.*` import is a boundary violation.
SANCTIONED_IMPORT_PREFIXES = ("core.events", "core.runtime.signal_source")

# Instance attributes must not hold objects from these platform layers
# (DRIVER_SPECIFICATION §5.4: no ledger/broker/handler handle).
FORBIDDEN_HANDLE_MODULE_PREFIXES = ("core.execution", "core.brokers")

# Constructor parameters whose names betray a platform-handle injection point.
FORBIDDEN_CONSTRUCTOR_PARAMS = frozenset({
    "execution", "execution_handler", "handler", "ledger", "broker",
    "position_tracker", "order_tracker", "driver",
})

SourceFactory = Callable[[], SignalSource]


class ConformanceViolation(AssertionError):
    """A named contract violation. `check` identifies the failed invariant."""

    def __init__(self, check: str, detail: str):
        self.check = check
        self.detail = detail
        super().__init__(f"[{check}] {detail}")


# --------------------------------------------------------------------------- #
# Layer 1 — static conformance (§7.1)
# --------------------------------------------------------------------------- #

def check_is_signal_source(source: object) -> None:
    """The candidate must be a `SignalSource` (the strategy interface, ADR-016)."""
    if not isinstance(source, SignalSource):
        raise ConformanceViolation(
            "is_signal_source",
            f"{type(source).__name__} is not a core.runtime.signal_source.SignalSource")


def check_on_bar_not_coroutine(source: SignalSource) -> None:
    """The pull contract is synchronous (§5.2); an async on_bar can never be
    awaited by the single-threaded driver."""
    if inspect.iscoroutinefunction(type(source).on_bar):
        raise ConformanceViolation(
            "on_bar_not_coroutine",
            f"{type(source).__name__}.on_bar is a coroutine function; the "
            "driver's pull is synchronous (DRIVER_SPECIFICATION §5.2)")


def check_constructor_surface(source_cls: type) -> None:
    """No constructor parameter may be a platform-handle injection point
    (§5.4). Name-based detection — a heuristic, backed by the behavioral
    forbidden-handle check on the live instance."""
    params = inspect.signature(source_cls.__init__).parameters
    offending = sorted(FORBIDDEN_CONSTRUCTOR_PARAMS.intersection(params))
    if offending:
        raise ConformanceViolation(
            "constructor_surface",
            f"{source_cls.__name__}.__init__ accepts platform-handle "
            f"parameter(s) {offending} (DRIVER_SPECIFICATION §5.4)")


def check_no_forbidden_handles(source: SignalSource) -> None:
    """No instance attribute (shallow, plus one level into containers) may
    hold an object from the execution/broker layers or the LoopDriver (§5.4:
    a source can never route or read platform truth directly)."""
    from core.runtime.driver import LoopDriver

    def _offends(value: object) -> bool:
        if isinstance(value, LoopDriver):
            return True
        return type(value).__module__.startswith(FORBIDDEN_HANDLE_MODULE_PREFIXES)

    for name, value in vars(source).items():
        candidates = [value]
        if isinstance(value, dict):
            candidates.extend(value.values())
        elif isinstance(value, (list, tuple, set)):
            candidates.extend(value)
        for candidate in candidates:
            if _offends(candidate):
                raise ConformanceViolation(
                    "no_forbidden_handles",
                    f"attribute '{name}' holds {type(candidate).__name__} from "
                    f"'{type(candidate).__module__}' (DRIVER_SPECIFICATION §5.4)")


def check_import_surface(package_root: Path) -> None:
    """AST-scan every .py under the strategy package: any `core.*` import
    outside the sanctioned surface (ADR-016) is a violation. Relative imports
    (strategy-internal) are ignored. Static text scan — nothing is imported."""
    package_root = Path(package_root)
    for py_file in sorted(package_root.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            imported: List[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported = [f"{node.module}.{alias.name}" for alias in node.names]
            for full_name in imported:
                if not (full_name == "core" or full_name.startswith("core.")):
                    continue
                if not full_name.startswith(SANCTIONED_IMPORT_PREFIXES):
                    raise ConformanceViolation(
                        "import_surface",
                        f"{py_file.name}:{node.lineno} imports '{full_name}' — "
                        f"outside the sanctioned surface "
                        f"{list(SANCTIONED_IMPORT_PREFIXES)} (ADR-016)")


# --------------------------------------------------------------------------- #
# Layer 2 — behavioral conformance (§7.2)
# --------------------------------------------------------------------------- #

def _drive(source: SignalSource,
           bars: Sequence[OHLCVBar]) -> List[List[SignalEvent]]:
    """Run the driver's lifecycle shape (§5.2: on_start → on_bar per bar →
    on_stop) and collect each bar's returned value verbatim."""
    source.on_start()
    try:
        return [source.on_bar(bar) for bar in bars]
    finally:
        source.on_stop()


def check_lifecycle(factory: SourceFactory, bars: Sequence[OHLCVBar]) -> None:
    """The three lifecycle shapes a source must tolerate (architecture §2):
    construction-then-abandonment (refused startup — neither hook fires),
    on_start→on_stop with zero bars, and the full start→bars→stop run."""
    try:
        factory()  # abandoned startup: constructed, never started (§2 note 2)
    except Exception as exc:
        raise ConformanceViolation(
            "lifecycle", f"construction raised: {exc!r}") from exc
    for label, corpus in (("zero-bar start/stop", []), ("full run", list(bars))):
        source = factory()
        try:
            _drive(source, corpus)
        except Exception as exc:
            raise ConformanceViolation(
                "lifecycle", f"{label} raised: {exc!r}") from exc


def check_return_shape(factory: SourceFactory, bars: Sequence[OHLCVBar]) -> None:
    """Every on_bar returns a list of SignalEvent — never None, never another
    container, never foreign elements (§5.2 `List[SignalEvent]`)."""
    for bar, result in zip(bars, _drive(factory(), bars)):
        if not isinstance(result, list):
            raise ConformanceViolation(
                "return_shape",
                f"on_bar({bar.timestamp}) returned {type(result).__name__}, "
                "not a list")
        for item in result:
            if not isinstance(item, SignalEvent):
                raise ConformanceViolation(
                    "return_shape",
                    f"on_bar({bar.timestamp}) returned a "
                    f"{type(item).__name__} element, not a SignalEvent")


def check_timestamp_discipline(factory: SourceFactory,
                               bars: Sequence[OHLCVBar]) -> None:
    """Every emitted signal carries the triggering bar's timestamp — time
    comes from the bar, never wall-clock (architecture §4.1/§6; ADR-003)."""
    for bar, result in zip(bars, _drive(factory(), bars)):
        for signal in result:
            if signal.timestamp != bar.timestamp:
                raise ConformanceViolation(
                    "timestamp_discipline",
                    f"signal timestamp {signal.timestamp} != bar timestamp "
                    f"{bar.timestamp} (wall-clock leakage?)")


def check_entry_risk_metadata(factory: SourceFactory,
                              bars: Sequence[OHLCVBar]) -> None:
    """Every BUY/SELL carries numeric sl_distance > 0 and risk_r > 0
    (architecture §4.2 mandatory reserved keys; the guard drops violators at
    runtime, ADR-018 — certification catches them earlier)."""
    for bar, result in zip(bars, _drive(factory(), bars)):
        for signal in result:
            if signal.signal_type not in (SignalType.BUY, SignalType.SELL):
                continue
            for key in ("sl_distance", "risk_r"):
                value = signal.metadata.get(key)
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    numeric = None
                if numeric is None or numeric <= 0:
                    raise ConformanceViolation(
                        "entry_risk_metadata",
                        f"{signal.signal_type.value} {signal.symbol} @ "
                        f"{bar.timestamp}: metadata['{key}'] = {value!r} "
                        "(must be numeric and > 0)")


def check_replay_equivalence(factory: SourceFactory,
                             bars: Sequence[OHLCVBar]) -> None:
    """The core determinism assertion (architecture §6): two fresh instances
    over the identical corpus must emit identical signal streams. SignalEvent
    is a frozen dataclass, so == compares every field including metadata."""
    first = _drive(factory(), bars)
    second = _drive(factory(), bars)
    if first != second:
        for i, (a, b) in enumerate(zip(first, second)):
            if a != b:
                raise ConformanceViolation(
                    "replay_equivalence",
                    f"bar {i} diverged between two identical runs: "
                    f"{a!r} != {b!r} (nondeterministic source)")
        raise ConformanceViolation(
            "replay_equivalence", "signal streams diverged between runs")


def check_latency_budget(factory: SourceFactory, bars: Sequence[OHLCVBar],
                         budget_s: float) -> None:
    """p99 on_bar wall time within the declared budget (obligation S1). The
    only wall-clock use in this suite — measurement, never decision input."""
    source = factory()
    source.on_start()
    durations = []
    try:
        for bar in bars:
            t0 = time.perf_counter()
            source.on_bar(bar)
            durations.append(time.perf_counter() - t0)
    finally:
        source.on_stop()
    if not durations:
        return
    p99 = sorted(durations)[max(0, math.ceil(0.99 * len(durations)) - 1)]
    if p99 > budget_s:
        raise ConformanceViolation(
            "latency_budget",
            f"p99 on_bar time {p99:.4f}s exceeds budget {budget_s}s "
            "(obligation S1: the loop is single-threaded)")


# --------------------------------------------------------------------------- #
# The suite
# --------------------------------------------------------------------------- #

def run_conformance(factory: SourceFactory, bars: Sequence[OHLCVBar], *,
                    package_root: Optional[Path] = None,
                    latency_budget_s: Optional[float] = None) -> None:
    """
    Run the full Layer 1 + Layer 2 suite; raise ConformanceViolation on the
    first failed invariant, return None when the source is CONFORMANT.

    Args:
        factory: zero-arg callable returning a FRESH SignalSource per call.
        bars: the recorded bar corpus to certify against.
        package_root: optional strategy package directory for the
            import-surface scan (skipped when None — e.g. certifying a
            single in-memory class).
        latency_budget_s: optional S1 budget; skipped when None (wall-clock
            measurement is environment-sensitive, so it is opt-in).
    """
    sample = factory()
    check_is_signal_source(sample)
    check_on_bar_not_coroutine(sample)
    check_constructor_surface(type(sample))
    check_no_forbidden_handles(sample)
    if package_root is not None:
        check_import_surface(package_root)

    check_lifecycle(factory, bars)
    check_return_shape(factory, bars)
    check_timestamp_discipline(factory, bars)
    check_entry_risk_metadata(factory, bars)
    check_replay_equivalence(factory, bars)
    if latency_budget_s is not None:
        check_latency_budget(factory, bars, latency_budget_s)
