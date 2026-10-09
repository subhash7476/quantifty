from datetime import date

from scripts import bootstrap


def test_window_seeds_from_scratch_when_store_is_empty(tmp_path):
    today = date(2026, 10, 9)
    assert bootstrap._window(tmp_path, 10, today) == (date(2026, 9, 29), date(2026, 10, 8))


def test_window_resumes_from_the_last_stored_session(tmp_path):
    (tmp_path / "2026-10-06.duckdb").touch()
    (tmp_path / "not-a-date.duckdb").touch()
    today = date(2026, 10, 9)
    assert bootstrap._window(tmp_path, 10, today) == (date(2026, 10, 6), date(2026, 10, 8))


def test_window_is_none_when_already_current(tmp_path):
    (tmp_path / "2026-10-09.duckdb").touch()
    assert bootstrap._window(tmp_path, 10, date(2026, 10, 9)) is None


def test_env_gets_fresh_secrets_and_trading_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap, "ENV_FILE", tmp_path / ".env")
    bootstrap._write_env()
    env = dict(line.split("=", 1) for line in (tmp_path / ".env").read_text().splitlines()
               if "=" in line and not line.startswith("#"))
    assert env["NIFTY_PROFILE"] == "trading"
    assert env["SECRET_KEY"] not in ("", "change-me")
    assert len(env["UPSTOX_NOTIFY_SECRET"]) >= 24
    assert env["UPSTOX_NOTIFY_DOMAIN"] == ""


def test_env_is_never_overwritten(tmp_path, monkeypatch):
    target = tmp_path / ".env"
    target.write_text("SECRET_KEY=mine\n")
    monkeypatch.setattr(bootstrap, "ENV_FILE", target)
    bootstrap._write_env()
    assert target.read_text() == "SECRET_KEY=mine\n"
