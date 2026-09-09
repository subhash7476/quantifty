"""A test run must never write into the operational log directory."""
import os
from pathlib import Path


def test_tests_do_not_log_into_the_repo_logs_dir():
    assert os.environ.get("NIFTY_LOG_DIR"), "conftest must redirect logs during tests"
    assert Path(os.environ["NIFTY_LOG_DIR"]).resolve() != (Path.cwd() / "logs").resolve()


def test_setup_logger_writes_under_the_override(tmp_path, monkeypatch):
    monkeypatch.setenv("NIFTY_LOG_DIR", str(tmp_path))
    from core.logging.logger import setup_logger
    logger = setup_logger("isolation_probe")
    logger.warning("probe")
    for handler in logger.handlers:
        handler.flush()
    assert (tmp_path / "isolation_probe.log").exists()
