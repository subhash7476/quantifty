"""
Unit tests for core.runtime.config — DriverConfig + Mode.

Validates the configuration model in DRIVER_SPECIFICATION.md section 13:
- required mode/symbols, spec defaults for the optional fields;
- the mode-dependent telemetry_enabled default (True live / False replay) and
  explicit override;
- isolation-level validation (non-empty symbols, positive poll interval,
  None-or-positive max_bars, Mode type);
- immutability (frozen) and the is_live / is_replay helpers.
"""

import dataclasses

import pytest

from core.runtime.config import DriverConfig, Mode


# --------------------------------------------------------------------------- #
# Required fields + defaults
# --------------------------------------------------------------------------- #
def test_minimal_construction_applies_spec_defaults():
    cfg = DriverConfig(mode=Mode.LIVE, symbols=["NSE_INDEX|Nifty 50"])
    assert cfg.mode is Mode.LIVE
    assert cfg.symbols == ["NSE_INDEX|Nifty 50"]
    assert cfg.poll_interval_s == 0.5
    assert cfg.max_bars is None
    assert cfg.heartbeat_path == "logs/heartbeat.json"
    assert cfg.telemetry_host == "127.0.0.1"
    assert cfg.telemetry_port == 5560
    assert cfg.telemetry_node == "trade_loop"
    assert cfg.telemetry_interval_s == 5.0
    assert cfg.require_reconciliation_on_start is True


def test_overrides_are_respected():
    cfg = DriverConfig(
        mode=Mode.REPLAY,
        symbols=["A", "B"],
        poll_interval_s=1.0,
        max_bars=1000,
        heartbeat_path="logs/custom.json",
        telemetry_host="10.0.0.5",
        telemetry_port=6000,
        telemetry_node="replay_loop",
        telemetry_interval_s=2.5,
        require_reconciliation_on_start=False,
    )
    assert cfg.poll_interval_s == 1.0
    assert cfg.max_bars == 1000
    assert cfg.heartbeat_path == "logs/custom.json"
    assert cfg.telemetry_host == "10.0.0.5"
    assert cfg.telemetry_port == 6000
    assert cfg.telemetry_node == "replay_loop"
    assert cfg.telemetry_interval_s == 2.5
    assert cfg.require_reconciliation_on_start is False


# --------------------------------------------------------------------------- #
# Mode-dependent telemetry default + override
# --------------------------------------------------------------------------- #
def test_telemetry_enabled_defaults_true_in_live():
    cfg = DriverConfig(mode=Mode.LIVE, symbols=["A"])
    assert cfg.telemetry_enabled is True


def test_telemetry_enabled_defaults_false_in_replay():
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=["A"])
    assert cfg.telemetry_enabled is False


def test_telemetry_enabled_explicit_override_wins_in_live():
    cfg = DriverConfig(mode=Mode.LIVE, symbols=["A"], telemetry_enabled=False)
    assert cfg.telemetry_enabled is False


def test_telemetry_enabled_explicit_override_wins_in_replay():
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=["A"], telemetry_enabled=True)
    assert cfg.telemetry_enabled is True


# --------------------------------------------------------------------------- #
# Mode helpers
# --------------------------------------------------------------------------- #
def test_is_live_and_is_replay_helpers():
    live = DriverConfig(mode=Mode.LIVE, symbols=["A"])
    replay = DriverConfig(mode=Mode.REPLAY, symbols=["A"])
    assert live.is_live is True and live.is_replay is False
    assert replay.is_replay is True and replay.is_live is False


# --------------------------------------------------------------------------- #
# Validation (isolation-level only)
# --------------------------------------------------------------------------- #
def test_empty_symbols_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        DriverConfig(mode=Mode.LIVE, symbols=[])


def test_non_mode_value_rejected():
    with pytest.raises(TypeError, match="mode must be a Mode"):
        DriverConfig(mode="LIVE", symbols=["A"])  # type: ignore[arg-type]


def test_non_positive_poll_interval_rejected():
    with pytest.raises(ValueError, match="poll_interval_s"):
        DriverConfig(mode=Mode.LIVE, symbols=["A"], poll_interval_s=0.0)


def test_non_positive_max_bars_rejected():
    with pytest.raises(ValueError, match="max_bars"):
        DriverConfig(mode=Mode.REPLAY, symbols=["A"], max_bars=0)


def test_max_bars_none_is_allowed():
    cfg = DriverConfig(mode=Mode.LIVE, symbols=["A"], max_bars=None)
    assert cfg.max_bars is None


# --------------------------------------------------------------------------- #
# Immutability
# --------------------------------------------------------------------------- #
def test_config_is_frozen():
    cfg = DriverConfig(mode=Mode.LIVE, symbols=["A"])
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.poll_interval_s = 2.0  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Mode enum
# --------------------------------------------------------------------------- #
def test_mode_values():
    assert Mode.LIVE.value == "LIVE"
    assert Mode.REPLAY.value == "REPLAY"
    assert set(Mode) == {Mode.LIVE, Mode.REPLAY}
