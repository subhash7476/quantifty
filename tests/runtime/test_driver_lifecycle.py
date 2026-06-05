"""
Unit tests for LoopDriver Phase A — lifecycle state machine only.

Validates DRIVER_SPECIFICATION.md §3: the six runtime states, every legal
§3.2 transition, rejection of illegal transitions, and the strategy-agnostic
import invariant (ADR-002/006). No IO, no collaborators beyond DriverConfig.
"""

import ast
from pathlib import Path

import pytest

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import (
    InvalidStateTransition,
    LoopDriver,
    RuntimeState,
)


def _driver() -> LoopDriver:
    return LoopDriver(DriverConfig(mode=Mode.REPLAY, symbols=["NSE_INDEX|Nifty 50"]))


# --------------------------------------------------------------------------- #
# Construction
# --------------------------------------------------------------------------- #
def test_construct_starts_in_startup():
    assert _driver().state is RuntimeState.STARTUP


def test_config_is_retained():
    cfg = DriverConfig(mode=Mode.LIVE, symbols=["A"])
    assert LoopDriver(cfg).config is cfg


def test_runtime_state_has_exactly_six_members():
    assert {s.value for s in RuntimeState} == {
        "STARTUP", "RECOVERY", "RUNNING", "PAUSED", "STOPPING", "STOPPED",
    }
    assert len(RuntimeState) == 6  # kill-switch is NOT a state (§3.2)


# --------------------------------------------------------------------------- #
# Legal transitions (every §3.2 edge)
# --------------------------------------------------------------------------- #
def test_startup_to_running():
    d = _driver()
    d.start()
    assert d.state is RuntimeState.RUNNING


def test_startup_to_recovery_to_running():
    d = _driver()
    d.enter_recovery()
    assert d.state is RuntimeState.RECOVERY
    d.start()
    assert d.state is RuntimeState.RUNNING


def test_running_pause_resume():
    d = _driver()
    d.start()
    d.pause()
    assert d.state is RuntimeState.PAUSED
    d.resume()
    assert d.state is RuntimeState.RUNNING


def test_running_to_stopping_to_stopped():
    d = _driver()
    d.start()
    d.stop()
    assert d.state is RuntimeState.STOPPING
    d.finalize_stop()
    assert d.state is RuntimeState.STOPPED


def test_paused_to_stopping():
    d = _driver()
    d.start()
    d.pause()
    d.stop()
    assert d.state is RuntimeState.STOPPING


def test_abort_startup_from_startup():
    d = _driver()
    d.abort_startup()
    assert d.state is RuntimeState.STOPPED


def test_abort_startup_from_recovery():
    d = _driver()
    d.enter_recovery()
    d.abort_startup()
    assert d.state is RuntimeState.STOPPED


def test_all_six_states_reachable():
    seen = set()
    d = _driver()
    seen.add(d.state)              # STARTUP
    d.enter_recovery(); seen.add(d.state)   # RECOVERY
    d.start(); seen.add(d.state)            # RUNNING
    d.pause(); seen.add(d.state)            # PAUSED
    d.resume(); d.stop(); seen.add(d.state) # STOPPING
    d.finalize_stop(); seen.add(d.state)    # STOPPED
    assert seen == set(RuntimeState)


def test_paused_is_distinct_from_stopped():
    d = _driver()
    d.start()
    d.pause()
    assert d.state is RuntimeState.PAUSED
    assert d.state is not RuntimeState.STOPPED


# --------------------------------------------------------------------------- #
# Illegal transitions are rejected
# --------------------------------------------------------------------------- #
def test_pause_from_startup_rejected():
    with pytest.raises(InvalidStateTransition):
        _driver().pause()


def test_resume_from_running_rejected():
    d = _driver()
    d.start()
    with pytest.raises(InvalidStateTransition):
        d.resume()


def test_start_from_paused_rejected():
    d = _driver()
    d.start()
    d.pause()
    with pytest.raises(InvalidStateTransition):
        d.start()


def test_finalize_stop_from_running_rejected():
    d = _driver()
    d.start()
    with pytest.raises(InvalidStateTransition):
        d.finalize_stop()


def test_enter_recovery_from_running_rejected():
    d = _driver()
    d.start()
    with pytest.raises(InvalidStateTransition):
        d.enter_recovery()


def test_stop_from_startup_rejected():
    with pytest.raises(InvalidStateTransition):
        _driver().stop()


@pytest.mark.parametrize("verb", [
    "enter_recovery", "start", "pause", "resume", "stop",
    "abort_startup", "finalize_stop",
])
def test_stopped_is_terminal(verb):
    d = _driver()
    d.start()
    d.stop()
    d.finalize_stop()
    assert d.state is RuntimeState.STOPPED
    with pytest.raises(InvalidStateTransition):
        getattr(d, verb)()


def test_invalid_transition_carries_current_and_target():
    d = _driver()  # STARTUP
    with pytest.raises(InvalidStateTransition) as exc:
        d.pause()  # target PAUSED, illegal from STARTUP
    assert exc.value.current is RuntimeState.STARTUP
    assert exc.value.target is RuntimeState.PAUSED
    assert "STARTUP" in str(exc.value) and "PAUSED" in str(exc.value)


def test_failed_transition_does_not_change_state():
    d = _driver()
    with pytest.raises(InvalidStateTransition):
        d.resume()  # illegal from STARTUP
    assert d.state is RuntimeState.STARTUP  # unchanged


# --------------------------------------------------------------------------- #
# Strategy-agnostic invariant (ADR-002 / ADR-006)
# --------------------------------------------------------------------------- #
def test_driver_imports_no_strategy_code():
    forbidden_roots = {
        "strategies", "backtest", "runner", "ftmo",
        "models", "scanners", "research", "analytics", "state",
    }
    src_path = Path(__file__).resolve().parents[2] / "core" / "runtime" / "driver.py"
    tree = ast.parse(src_path.read_text(encoding="utf-8"))

    imported_roots: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
                if alias.name.startswith("core."):
                    imported_roots.add(alias.name.split(".")[1])
        elif isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            imported_roots.add(parts[0])
            if parts[0] == "core" and len(parts) > 1:
                imported_roots.add(parts[1])

    assert forbidden_roots.isdisjoint(imported_roots), (
        f"driver.py must not import strategy/alpha code; found: {sorted(imported_roots)}"
    )
