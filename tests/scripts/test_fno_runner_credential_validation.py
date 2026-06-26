"""
MM8.3 — Startup credential validation tests.

Verifies that build_runner() refuses to start ExecutionMode.LIVE when Upstox
credentials are missing or expired, before any collaborator is constructed.

Gate order: source → broker → credential → universe.
PAPER mode skips the credential check entirely.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests" / "runtime"))

from _runner_harness import NoopSource, build, isolate_store, EQUITY
from _doubles import FakeMarketDataProvider, bar_series

import scripts.fno_runner as fno_runner
from core.clock import ReplayClock
from core.execution.handler import ExecutionMode

from datetime import datetime
import pytz

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


def _fake_broker():
    b = MagicMock()
    b.get_positions.return_value = []
    return b


def _patch_valid_creds(monkeypatch):
    mock = MagicMock()
    mock.has_upstox_token = True
    mock.is_token_expired = False
    monkeypatch.setattr(fno_runner, "_live_credentials", mock)


def _patch_missing_token(monkeypatch):
    mock = MagicMock()
    mock.has_upstox_token = False
    mock.is_token_expired = False
    monkeypatch.setattr(fno_runner, "_live_credentials", mock)


def _patch_expired_token(monkeypatch):
    mock = MagicMock()
    mock.has_upstox_token = True
    mock.is_token_expired = True
    monkeypatch.setattr(fno_runner, "_live_credentials", mock)


# --------------------------------------------------------------------------- #
# (1) LIVE + missing token → ValueError before construction
# --------------------------------------------------------------------------- #
def test_live_refuses_when_token_missing(tmp_path, monkeypatch):
    isolate_store(tmp_path, monkeypatch)
    _patch_missing_token(monkeypatch)
    provider = FakeMarketDataProvider({EQUITY: bar_series(EQUITY, 3)}, live=True)

    with pytest.raises(ValueError, match="(?i)token|credential"):
        fno_runner.build_runner(
            source=NoopSource(),
            symbols=[EQUITY],
            execution_mode=ExecutionMode.LIVE,
            broker=_fake_broker(),
            broker_positions=lambda: [],
            clock=ReplayClock(FIXED_DT),
            provider=provider,
            db_manager=tmp_path,
            metrics_path=str(tmp_path / "metrics.json"),
        )


# --------------------------------------------------------------------------- #
# (2) LIVE + expired token → ValueError before construction
# --------------------------------------------------------------------------- #
def test_live_refuses_when_token_expired(tmp_path, monkeypatch):
    isolate_store(tmp_path, monkeypatch)
    _patch_expired_token(monkeypatch)
    provider = FakeMarketDataProvider({EQUITY: bar_series(EQUITY, 3)}, live=True)

    with pytest.raises(ValueError, match="(?i)token|credential|expired"):
        fno_runner.build_runner(
            source=NoopSource(),
            symbols=[EQUITY],
            execution_mode=ExecutionMode.LIVE,
            broker=_fake_broker(),
            broker_positions=lambda: [],
            clock=ReplayClock(FIXED_DT),
            provider=provider,
            db_manager=tmp_path,
            metrics_path=str(tmp_path / "metrics.json"),
        )


# --------------------------------------------------------------------------- #
# (3) LIVE + valid token → no error
# --------------------------------------------------------------------------- #
def test_live_proceeds_with_valid_token(tmp_path, monkeypatch):
    isolate_store(tmp_path, monkeypatch)
    _patch_valid_creds(monkeypatch)
    provider = FakeMarketDataProvider({EQUITY: bar_series(EQUITY, 3)}, live=True)

    fno_runner.build_runner(
        source=NoopSource(),
        symbols=[EQUITY],
        execution_mode=ExecutionMode.LIVE,
        broker=_fake_broker(),
        broker_positions=lambda: [],
        clock=ReplayClock(FIXED_DT),
        provider=provider,
        db_manager=tmp_path,
        metrics_path=str(tmp_path / "metrics.json"),
    )


# --------------------------------------------------------------------------- #
# (4) PAPER mode → credential check is skipped entirely
# --------------------------------------------------------------------------- #
def test_paper_mode_skips_credential_check(tmp_path, monkeypatch):
    mock = MagicMock()
    mock.has_upstox_token = False  # would fail if checked
    mock.is_token_expired = True
    monkeypatch.setattr(fno_runner, "_live_credentials", mock)

    build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,),
          execution_mode=ExecutionMode.PAPER)
