import json
import time
from datetime import datetime

import pytest

from core.auth import credentials as cred_mod
from core.auth.credentials import CredentialManager


def _ts(s):
    return datetime.fromisoformat(s).timestamp()


@pytest.mark.parametrize("saved, now, expired", [
    ("2026-09-24 14:00", "2026-09-25 03:29", False),
    ("2026-09-24 14:00", "2026-09-25 03:30", True),   # 13.5 h old, dead at 03:30
    ("2026-09-24 14:00", "2026-09-25 09:10", True),   # the 22 h rule called this fresh
    ("2026-09-25 01:00", "2026-09-25 03:31", True),   # issued before 03:30 dies the same night
    ("2026-09-25 09:12", "2026-09-25 15:30", False),
])
def test_token_expires_at_next_0330(tmp_path, monkeypatch, saved, now, expired):
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"access_token": "t", "token_saved_at": _ts(saved)}))
    monkeypatch.setattr(cred_mod.time, "time", lambda: _ts(now))
    assert CredentialManager(str(path)).is_token_expired is expired


def test_save_rereads_file_so_a_stale_process_cannot_clobber_newer_keys(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"api_key": "k", "access_token": "old"}))
    stale = CredentialManager(str(path))          # e.g. Flask, loaded at startup
    fresh = CredentialManager(str(path))
    fresh.save({"access_token": "new"})           # webhook writes the new token
    stale.save({"redirect_uri": "r"})             # Flask later saves config
    on_disk = json.loads(path.read_text())
    assert on_disk["access_token"] == "new"
    assert on_disk["redirect_uri"] == "r" and on_disk["api_key"] == "k"


def test_long_lived_instance_sees_token_saved_by_another_process(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"access_token": "friday", "token_saved_at": time.time() - 4 * 86400}))
    flask = CredentialManager(str(path))          # started 09:10, before the token gate
    assert flask.needs_daily_refresh
    CredentialManager(str(path)).save({"access_token": "monday"})   # phone approval
    assert flask.get("access_token") == "monday"
    assert not flask.needs_daily_refresh


def test_instance_survives_file_disappearing(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"access_token": "t"}))
    mgr = CredentialManager(str(path))
    path.unlink()
    assert mgr.get("access_token") == "t"


def test_save_is_atomic_leaves_no_temp_file(tmp_path):
    path = tmp_path / "credentials.json"
    CredentialManager(str(path)).save({"access_token": "x"})
    assert [p.name for p in tmp_path.iterdir()] == ["credentials.json"]


def test_default_path_is_anchored_to_repo_root():
    assert cred_mod.DEFAULT_PATH.is_absolute()
    assert cred_mod.DEFAULT_PATH.parts[-2:] == ("config", "credentials.json")
