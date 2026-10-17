import pytest

from core.options_wall import paper_executor


@pytest.fixture(autouse=True)
def isolated_stop_file(tmp_path, monkeypatch):
    """Point the platform kill switch at tmp_path so the operator's live STOP never leaks in."""
    stop = tmp_path / "STOP"
    monkeypatch.setattr(paper_executor, "STOP_FILE", stop)
    return stop
