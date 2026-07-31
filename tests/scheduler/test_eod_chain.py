from pathlib import Path

from core.scheduler.eod_chain import run_chain, run_step


def _script(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_run_step_succeeds_on_zero_exit(tmp_path):
    s = _script(tmp_path, "ok.py", "print('fine')\n")
    r = run_step("ok", s)
    assert r.ok is True
    assert "fine" in r.stdout


def test_run_step_fails_on_nonzero_exit_and_captures_stderr(tmp_path):
    s = _script(tmp_path, "bad.py", "import sys; print('BoomError', file=sys.stderr); sys.exit(1)\n")
    r = run_step("bad", s)
    assert r.ok is False
    assert "BoomError" in r.stderr_tail


def test_run_step_survives_non_ascii_output(tmp_path):
    # Windows default code page raises UnicodeDecodeError on these without utf-8.
    s = _script(tmp_path, "uni.py", "print('carry — basis → ₹100')\n")
    r = run_step("uni", s)
    assert r.ok is True


def test_run_chain_stops_at_first_failure(tmp_path):
    a = _script(tmp_path, "a.py", "print('a')\n")
    b = _script(tmp_path, "b.py", "import sys; sys.exit(2)\n")
    c = _script(tmp_path, "c.py", "raise AssertionError('must not run')\n")
    results = run_chain([("a", a), ("b", b), ("c", c)])
    assert [r.label for r in results] == ["a", "b"]
    assert results[-1].ok is False


def test_run_chain_runs_all_steps_when_all_pass(tmp_path):
    a = _script(tmp_path, "a.py", "print('a')\n")
    b = _script(tmp_path, "b.py", "print('b')\n")
    results = run_chain([("a", a), ("b", b)])
    assert all(r.ok for r in results)
    assert len(results) == 2
