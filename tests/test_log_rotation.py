"""A log file shared by several processes must not break rotation on Windows.

Several children (chain poller, wall poller, Flask) each open their own handler on
logs/options_provider.log. At 10 MB the stdlib handler tried to rename it on every
emit, Windows refused while the others held it open, and each refusal printed a
traceback, dropped the record, and shuffled the backups (2026-09-24, 14:58).
"""
import logging
import os
import sys

import pytest

from core.logging.logger import SafeRotatingFileHandler, setup_logger


def _record(msg):
    return logging.LogRecord("probe", logging.INFO, __file__, 1, msg, None, None)


def _handler(path, max_bytes=50):
    h = SafeRotatingFileHandler(str(path), maxBytes=max_bytes, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(message)s"))
    return h


def _seed_backups(path):
    for i in (1, 2, 3):
        (path.parent / f"{path.name}.{i}").write_text(f"backup {i}\n", encoding="utf-8")


def _backups(path):
    return {i: (path.parent / f"{path.name}.{i}").read_text(encoding="utf-8")
            for i in (1, 2, 3) if (path.parent / f"{path.name}.{i}").exists()}


def _refuse_live_rename(monkeypatch, path, calls):
    real = os.replace

    def fake(src, dst):
        calls.append(src)
        if os.path.abspath(src) == os.path.abspath(path):
            raise PermissionError(32, "The process cannot access the file", src)
        return real(src, dst)

    monkeypatch.setattr(os, "replace", fake)


def test_refused_rollover_keeps_record_backups_and_stays_quiet(tmp_path, monkeypatch, capsys):
    path = tmp_path / "shared.log"
    path.write_text("x" * 100 + "\n", encoding="utf-8")   # already over maxBytes
    _seed_backups(path)
    calls = []
    _refuse_live_rename(monkeypatch, path, calls)
    handler = _handler(path)

    for i in range(5):
        handler.emit(_record(f"line {i}"))
    handler.close()

    text = path.read_text(encoding="utf-8")
    assert all(f"line {i}" in text for i in range(5))                 # nothing dropped
    assert _backups(path) == {i: f"backup {i}\n" for i in (1, 2, 3)}  # backups untouched
    assert len(calls) == 1                                            # no retry per emit
    err = capsys.readouterr().err
    assert "Logging error" not in err
    assert err.count("rotation of") == 1                              # one warning


def test_rollover_is_retried_after_the_back_off(tmp_path, monkeypatch):
    path = tmp_path / "shared.log"
    path.write_text("x" * 100 + "\n", encoding="utf-8")
    calls = []
    _refuse_live_rename(monkeypatch, path, calls)
    clock = [1000.0]
    monkeypatch.setattr("core.logging.logger.time.monotonic", lambda: clock[0])
    handler = _handler(path)

    handler.emit(_record("a"))
    clock[0] += SafeRotatingFileHandler.RETRY_AFTER_S + 1
    handler.emit(_record("b"))
    handler.close()

    assert len(calls) == 2


def test_unshared_file_still_rotates_normally(tmp_path):
    path = tmp_path / "solo.log"
    path.write_text("x" * 100 + "\n", encoding="utf-8")
    _seed_backups(path)
    handler = _handler(path)

    handler.emit(_record("fresh"))
    handler.close()

    assert path.read_text(encoding="utf-8") == "fresh\n"
    assert _backups(path) == {1: "x" * 100 + "\n", 2: "backup 1\n", 3: "backup 2\n"}


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only sharing semantics")
def test_real_second_handle_on_windows(tmp_path, capsys):
    path = tmp_path / "held.log"
    path.write_text("x" * 100 + "\n", encoding="utf-8")
    _seed_backups(path)
    other_process = open(path, "a", encoding="utf-8")   # what a sibling child holds
    try:
        handler = _handler(path)
        handler.emit(_record("still written"))
        handler.close()
    finally:
        other_process.close()

    assert "still written" in path.read_text(encoding="utf-8")
    assert _backups(path) == {i: f"backup {i}\n" for i in (1, 2, 3)}
    assert "Logging error" not in capsys.readouterr().err


def test_setup_logger_uses_the_safe_handler(tmp_path, monkeypatch):
    monkeypatch.setenv("NIFTY_LOG_DIR", str(tmp_path))
    logger = setup_logger("rotation_probe", console=False)
    assert any(isinstance(h, SafeRotatingFileHandler) for h in logger.handlers)
