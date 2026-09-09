"""File-based close-request queue (Flask → poller)."""
from core.options_wall import commands


def test_request_pending_and_clear(tmp_path):
    d = tmp_path / "cr"
    commands.request_close(5, "NIFTY", close_dir=d)
    pend = commands.pending_closes(close_dir=d)
    assert len(pend) == 1
    assert pend[0]["trade_id"] == 5 and pend[0]["index"] == "NIFTY"
    commands.clear_close(5, close_dir=d)
    assert commands.pending_closes(close_dir=d) == []


def test_pending_on_missing_dir_is_empty(tmp_path):
    assert commands.pending_closes(close_dir=tmp_path / "nope") == []


def test_request_overwrites_same_trade(tmp_path):
    d = tmp_path / "cr"
    commands.request_close(7, "SENSEX", close_dir=d)
    commands.request_close(7, "SENSEX", close_dir=d)
    assert len(commands.pending_closes(close_dir=d)) == 1
