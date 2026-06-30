"""MM10.1-S1 — Safety Hardening: SPAN-absent LIVE refusal."""

from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest

from core.execution.handler import ExecutionMode
from core.execution.margin_tracker import MarginTracker
from core.instruments.master_readiness import ReadinessState
from core.risk.span.span_readiness import SpanReadinessVerdict
from core.runtime.signal_source import SignalSource


@pytest.fixture
def mock_source():
    return Mock(spec=SignalSource)


@pytest.fixture
def mock_broker():
    b = MagicMock()
    b.__class__.__name__ = "MockBrokerAdapter"
    return b


@pytest.fixture
def mock_db():
    db = MagicMock()
    cm = MagicMock()
    db.trading_reader.return_value = cm
    return db


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def mock_clock():
    return MagicMock()


@pytest.fixture
def mock_journal():
    return MagicMock()


@patch("scripts.fno_runner.build_master_readiness")
@patch("scripts.fno_runner._live_credentials")
def test_live_fno_missing_snapshot_injects_block_checker(
    mock_creds, mock_bmr, mock_source, mock_broker, mock_db, mock_provider, mock_clock, mock_journal
):
    """LIVE F&O with absent snapshot injects an always-BLOCK checker."""
    mock_creds.configure_mock(has_upstox_token=True, is_token_expired=False)
    mock_bmr.return_value = Mock(return_value=Mock(state=ReadinessState.FRESH))

    with patch("scripts.fno_runner.SpanRepository.load") as mock_load:
        mock_load.side_effect = FileNotFoundError("No snapshot")
        from scripts.fno_runner import build_runner

        driver = build_runner(
            source=mock_source,
            symbols=["NSE_FO|NIFTY"],
            underlyings=["NIFTY"],
            execution_mode=ExecutionMode.LIVE,
            broker=mock_broker,
            broker_positions=lambda: [],
            db_manager=mock_db,
            provider=mock_provider,
            clock=mock_clock,
            journal=mock_journal,
        )

    assert driver._span_readiness is not None


@patch("scripts.fno_runner.build_master_readiness")
@patch("scripts.fno_runner._live_credentials")
def test_live_fno_block_checker_returns_block_verdict(
    mock_creds, mock_bmr, mock_source, mock_broker, mock_db, mock_provider, mock_clock, mock_journal
):
    """The injected block checker returns a BLOCK verdict with reason."""
    mock_creds.configure_mock(has_upstox_token=True, is_token_expired=False)
    mock_bmr.return_value = Mock(return_value=Mock(state=ReadinessState.FRESH))

    with patch("scripts.fno_runner.SpanRepository.load") as mock_load:
        mock_load.side_effect = FileNotFoundError("No snapshot")
        from scripts.fno_runner import build_runner

        driver = build_runner(
            source=mock_source,
            symbols=["NSE_FO|NIFTY"],
            underlyings=["NIFTY"],
            execution_mode=ExecutionMode.LIVE,
            broker=mock_broker,
            broker_positions=lambda: [],
            db_manager=mock_db,
            provider=mock_provider,
            clock=mock_clock,
            journal=mock_journal,
        )

    verdict = driver._span_readiness()
    assert verdict.state is ReadinessState.BLOCK
    assert "absent or corrupt" in verdict.reason


@patch("scripts.fno_runner.build_master_readiness")
@patch("scripts.fno_runner._live_credentials")
def test_live_fno_startup_gate_fires_and_aborts(
    mock_creds, mock_bmr, mock_source, mock_broker, mock_db, mock_provider, mock_clock, mock_journal
):
    """_check_span_readiness returns False and driver reaches STOPPED."""
    mock_creds.configure_mock(has_upstox_token=True, is_token_expired=False)
    mock_bmr.return_value = Mock(return_value=Mock(state=ReadinessState.FRESH))

    with patch("scripts.fno_runner.SpanRepository.load") as mock_load:
        mock_load.side_effect = ValueError("Corrupt data")
        from scripts.fno_runner import build_runner

        driver = build_runner(
            source=mock_source,
            symbols=["NSE_FO|NIFTY"],
            underlyings=["NIFTY"],
            execution_mode=ExecutionMode.LIVE,
            broker=mock_broker,
            broker_positions=lambda: [],
            db_manager=mock_db,
            provider=mock_provider,
            clock=mock_clock,
            journal=mock_journal,
        )

    result = driver._check_span_readiness()
    assert result is False
    from core.runtime.driver import RuntimeState
    assert driver.state is RuntimeState.STOPPED


@patch("scripts.fno_runner.build_master_readiness")
def test_paper_fno_missing_snapshot_proceeds(
    mock_bmr, mock_source, mock_db, mock_provider, mock_clock, mock_journal
):
    """PAPER F&O with absent snapshot proceeds with flat-rate MarginTracker."""
    mock_bmr.return_value = Mock(return_value=Mock(state=ReadinessState.FRESH))

    with patch("scripts.fno_runner.SpanRepository.load") as mock_load:
        mock_load.side_effect = FileNotFoundError("No snapshot")
        from scripts.fno_runner import build_runner

        driver = build_runner(
            source=mock_source,
            symbols=["NSE_FO|NIFTY"],
            underlyings=["NIFTY"],
            execution_mode=ExecutionMode.PAPER,
            db_manager=mock_db,
            provider=mock_provider,
            clock=mock_clock,
            journal=mock_journal,
        )

    assert driver._span_readiness is None
    assert isinstance(driver._execution.margin_tracker, MarginTracker)


@patch("scripts.fno_runner.build_master_readiness")
def test_equity_only_no_snapshot_no_effect(
    mock_bmr, mock_source, mock_db, mock_provider, mock_clock, mock_journal
):
    """Non-derivative symbols skip SPAN loading entirely — no exception."""
    mock_bmr.return_value = Mock(return_value=Mock(state=ReadinessState.FRESH))

    with patch("scripts.fno_runner.SpanRepository.load") as mock_load:
        mock_load.side_effect = FileNotFoundError("No snapshot")
        from scripts.fno_runner import build_runner

        driver = build_runner(
            source=mock_source,
            symbols=["RELIANCE"],
            execution_mode=ExecutionMode.PAPER,
            db_manager=mock_db,
            provider=mock_provider,
            clock=mock_clock,
            journal=mock_journal,
        )

    assert driver._span_readiness is None
