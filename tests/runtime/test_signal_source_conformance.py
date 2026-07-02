"""
MM12.2 — SignalSourceConformanceSuite proof tests (architecture §7.1–§7.2).

Exit criterion (MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md §15): the suite
runs against a deliberately-broken fixture source and FAILS on each violated
invariant, and runs against the trivial inert source and PASSES. Each broken
fixture below violates exactly one invariant so a failure names its check.
"""
from datetime import timedelta

import pytest

from core.events import SignalEvent, SignalType
from core.runtime.conformance import (
    STRATEGY_CONTRACT_VERSION,
    ConformanceViolation,
    check_constructor_surface,
    check_entry_risk_metadata,
    check_import_surface,
    check_is_signal_source,
    check_latency_budget,
    check_lifecycle,
    check_no_forbidden_handles,
    check_on_bar_not_coroutine,
    check_replay_equivalence,
    check_return_shape,
    check_timestamp_discipline,
    run_conformance,
)
from core.runtime.signal_source import SignalSource

from _doubles import bar_series

_SYM = "NSE_FO|53001"
_BARS = bar_series(_SYM, 4)


def _entry(bar, **metadata_overrides):
    metadata = {"sl_distance": 1.5, "risk_r": 500.0}
    metadata.update(metadata_overrides)
    return SignalEvent(strategy_id="fixture", symbol=bar.symbol,
                       timestamp=bar.timestamp, signal_type=SignalType.BUY,
                       confidence=1.0, metadata=metadata)


class _InertSource(SignalSource):
    """The trivial conformant source: never signals."""

    def on_bar(self, bar):
        return []


class _EmittingSource(SignalSource):
    """Conformant emitting source: contract-clean BUY on every second bar."""

    def __init__(self):
        self._count = 0

    def on_bar(self, bar):
        self._count += 1
        return [_entry(bar)] if self._count % 2 == 0 else []


# --------------------------------------------------------------------------- #
# Exit criterion, passing half: conformant sources clear the FULL suite.
# --------------------------------------------------------------------------- #
def test_inert_source_is_conformant():
    run_conformance(_InertSource, _BARS, latency_budget_s=1.0)


def test_emitting_source_is_conformant():
    run_conformance(_EmittingSource, _BARS)


def test_contract_version_published():
    assert STRATEGY_CONTRACT_VERSION == "1.0"


# --------------------------------------------------------------------------- #
# Layer 1 — each static invariant fails on its targeted broken fixture.
# --------------------------------------------------------------------------- #
def test_not_a_signal_source_fails():
    class _Impostor:  # duck-typed but not the ABC (ADR-016)
        def on_bar(self, bar):
            return []

    with pytest.raises(ConformanceViolation, match=r"\[is_signal_source\]"):
        check_is_signal_source(_Impostor())


def test_coroutine_on_bar_fails():
    class _AsyncSource(SignalSource):
        async def on_bar(self, bar):
            return []

    with pytest.raises(ConformanceViolation, match=r"\[on_bar_not_coroutine\]"):
        check_on_bar_not_coroutine(_AsyncSource())


def test_platform_handle_constructor_param_fails():
    class _HandleWanting(SignalSource):
        def __init__(self, execution_handler=None):
            self._h = execution_handler

        def on_bar(self, bar):
            return []

    with pytest.raises(ConformanceViolation, match=r"\[constructor_surface\]"):
        check_constructor_surface(_HandleWanting)


def test_held_execution_layer_object_fails():
    from core.execution.position_tracker import PositionTracker

    class _LedgerHolder(SignalSource):
        def __init__(self):
            self.tracker = PositionTracker()  # §5.4 contraband

        def on_bar(self, bar):
            return []

    with pytest.raises(ConformanceViolation, match=r"\[no_forbidden_handles\]"):
        check_no_forbidden_handles(_LedgerHolder())


def test_held_handle_inside_container_fails():
    from core.execution.position_tracker import PositionTracker

    class _BuriedHolder(SignalSource):
        def __init__(self):
            self.deps = {"ledger": PositionTracker()}

        def on_bar(self, bar):
            return []

    with pytest.raises(ConformanceViolation, match=r"\[no_forbidden_handles\]"):
        check_no_forbidden_handles(_BuriedHolder())


def test_import_surface_sanctioned_imports_pass(tmp_path):
    pkg = tmp_path / "strategy_pkg"
    pkg.mkdir()
    (pkg / "alpha.py").write_text(
        "from core.events import SignalEvent, SignalType\n"
        "from core.runtime.signal_source import SignalSource\n"
        "import math\n",
        encoding="utf-8")
    check_import_surface(pkg)


@pytest.mark.parametrize("stmt", [
    "from core.execution.handler import ExecutionHandler\n",
    "import core.brokers.paper_broker\n",
    "from core.runtime import driver\n",
    "from core import execution\n",
])
def test_import_surface_forbidden_imports_fail(tmp_path, stmt):
    pkg = tmp_path / "strategy_pkg"
    pkg.mkdir()
    (pkg / "alpha.py").write_text(stmt, encoding="utf-8")
    with pytest.raises(ConformanceViolation, match=r"\[import_surface\]"):
        check_import_surface(pkg)


# --------------------------------------------------------------------------- #
# Layer 2 — each behavioral invariant fails on its targeted broken fixture.
# --------------------------------------------------------------------------- #
def test_on_stop_raise_fails_lifecycle():
    class _DirtyShutdown(SignalSource):
        def on_bar(self, bar):
            return []

        def on_stop(self):
            raise RuntimeError("flush failed")

    with pytest.raises(ConformanceViolation, match=r"\[lifecycle\]"):
        check_lifecycle(_DirtyShutdown, _BARS)


def test_zero_bar_intolerance_fails_lifecycle():
    class _NeedsBars(SignalSource):
        def on_bar(self, bar):
            return []

        def on_stop(self):
            raise RuntimeError("no bars ever arrived")  # e.g. asserts warm state

    with pytest.raises(ConformanceViolation, match=r"\[lifecycle\]"):
        check_lifecycle(_NeedsBars, [])


def test_none_return_fails_shape():
    class _ReturnsNone(SignalSource):
        def on_bar(self, bar):
            return None

    with pytest.raises(ConformanceViolation, match=r"\[return_shape\]"):
        check_return_shape(_ReturnsNone, _BARS)


def test_tuple_return_fails_shape():
    class _ReturnsTuple(SignalSource):
        def on_bar(self, bar):
            return ()

    with pytest.raises(ConformanceViolation, match=r"\[return_shape\]"):
        check_return_shape(_ReturnsTuple, _BARS)


def test_foreign_element_fails_shape():
    class _ReturnsStrings(SignalSource):
        def on_bar(self, bar):
            return ["BUY"]

    with pytest.raises(ConformanceViolation, match=r"\[return_shape\]"):
        check_return_shape(_ReturnsStrings, _BARS)


def test_non_bar_timestamp_fails_discipline():
    class _ClockDrifter(SignalSource):
        def on_bar(self, bar):
            drifted = bar.timestamp + timedelta(minutes=1)
            return [SignalEvent(strategy_id="fixture", symbol=bar.symbol,
                                timestamp=drifted, signal_type=SignalType.EXIT,
                                confidence=1.0)]

    with pytest.raises(ConformanceViolation, match=r"\[timestamp_discipline\]"):
        check_timestamp_discipline(_ClockDrifter, _BARS)


@pytest.mark.parametrize("metadata", [
    {},                                          # both mandatory keys missing
    {"sl_distance": 1.5},                        # risk_r missing
    {"sl_distance": 0.0, "risk_r": 500.0},       # non-positive
    {"sl_distance": "wide", "risk_r": 500.0},    # non-numeric
])
def test_bad_entry_risk_metadata_fails(metadata):
    class _BareEntry(SignalSource):
        def on_bar(self, bar):
            return [SignalEvent(strategy_id="fixture", symbol=bar.symbol,
                                timestamp=bar.timestamp,
                                signal_type=SignalType.BUY,
                                confidence=1.0, metadata=dict(metadata))]

    with pytest.raises(ConformanceViolation, match=r"\[entry_risk_metadata\]"):
        check_entry_risk_metadata(_BareEntry, _BARS)


def test_exit_signals_do_not_require_risk_metadata():
    class _BareExit(SignalSource):
        def on_bar(self, bar):
            return [SignalEvent(strategy_id="fixture", symbol=bar.symbol,
                                timestamp=bar.timestamp,
                                signal_type=SignalType.EXIT, confidence=1.0)]

    check_entry_risk_metadata(_BareExit, _BARS)


def test_cross_instance_state_leak_fails_replay_equivalence():
    class _Leaky(SignalSource):
        """State survives across instances (module/class-global): the second
        replay run continues the first run's counter, so identical inputs
        yield a different stream — exactly the §6 violation class."""
        _global_calls = 0

        def on_bar(self, bar):
            _Leaky._global_calls += 1
            return [_entry(bar)] if _Leaky._global_calls % 2 == 0 else []

    with pytest.raises(ConformanceViolation, match=r"\[replay_equivalence\]"):
        check_replay_equivalence(_Leaky, bar_series(_SYM, 3))


def test_slow_on_bar_fails_latency_budget():
    import time as _time

    class _Sluggish(SignalSource):
        def on_bar(self, bar):
            _time.sleep(0.02)
            return []

    with pytest.raises(ConformanceViolation, match=r"\[latency_budget\]"):
        check_latency_budget(_Sluggish, bar_series(_SYM, 2), budget_s=0.005)


# --------------------------------------------------------------------------- #
# run_conformance surfaces a broken invariant end-to-end (not only per-check).
# --------------------------------------------------------------------------- #
def test_run_conformance_surfaces_violation():
    class _ReturnsNone(SignalSource):
        def on_bar(self, bar):
            return None

    with pytest.raises(ConformanceViolation, match=r"\[return_shape\]"):
        run_conformance(_ReturnsNone, _BARS)


def test_run_conformance_with_package_scan(tmp_path):
    pkg = tmp_path / "strategy_pkg"
    pkg.mkdir()
    (pkg / "alpha.py").write_text(
        "from core.runtime.signal_source import SignalSource\n", encoding="utf-8")
    run_conformance(_InertSource, _BARS, package_root=pkg)
