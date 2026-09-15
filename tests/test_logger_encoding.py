"""Log lines with characters outside a narrow code page (cp1252) must not be dropped."""
import io
import logging

from core.logging.logger import SafeConsoleHandler, setup_logger


def _record(msg):
    return logging.LogRecord("probe", logging.INFO, __file__, 1, msg, None, None)


def test_console_handler_escapes_unencodable_chars_instead_of_dropping(capsys):
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    handler = SafeConsoleHandler(stream)

    handler.emit(_record("window 2026-09-04 → 2026-09-14"))

    stream.seek(0)
    assert stream.read() == "window 2026-09-04 \\u2192 2026-09-14\n"
    assert "Logging error" not in capsys.readouterr().err


def test_file_handler_writes_utf8_regardless_of_locale(tmp_path, monkeypatch):
    monkeypatch.setenv("NIFTY_LOG_DIR", str(tmp_path))
    logger = setup_logger("encoding_probe", console=False)

    logger.info("window 2026-09-04 → 2026-09-14")
    for handler in logger.handlers:
        handler.flush()

    assert "→" in (tmp_path / "encoding_probe.log").read_text(encoding="utf-8")
