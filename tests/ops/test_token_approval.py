import json
import urllib.error
import urllib.request

import pytest

from core.auth.upstox_token_request import TokenRejected
from scripts.ops import token_approval as ta

SECRET = "s3cr3t-path"


class FakeProc:
    def __init__(self):
        self.pid, self.terminated = 4242, False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0


class Harness:
    def __init__(self, tmp_path, *, tunnel_ok=True, request_ok=True, accept=None):
        self.events, self.saved, self.msgs, self.killed = [], [], [], []
        self.proc = FakeProc()
        self.accept = accept or (lambda payload, api_key: {
            "access_token": payload["access_token"], "user_id": "AB1234",
            "expires_at": "1"})
        self.tunnel_ok, self.request_ok = tunnel_ok, request_ok
        self.approval = ta.PhoneApproval(
            api_key="KEY", api_secret="API_SECRET", domain="demo.ngrok-free.app",
            secret=SECRET, ngrok_path="ngrok", port=0,
            pid_path=tmp_path / "ngrok.pid",
            spawn=self._spawn, tunnel_check=self._check, request=self._request,
            accept=self._accept, save=self.saved.append, notify=self.msgs.append,
            kill=self.killed.append, lock_alive=lambda p: False,
            check_timeout_s=0.2)

    def _spawn(self, argv):
        self.events.append(("spawn", argv))
        return self.proc

    def _check(self, url):
        self.events.append(("check", url))
        return self.tunnel_ok

    def _request(self, key, secret):
        self.events.append(("request", key))
        if not self.request_ok:
            raise ta.TokenRequestError("token request refused: HTTP 401")
        return {"authorization_expiry": "1"}

    def _accept(self, payload, api_key):
        return self.accept(payload, api_key)

    def post(self, path, body):
        url = f"http://127.0.0.1:{self.approval.bound_port}{path}"
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code


@pytest.fixture
def h(tmp_path):
    harness = Harness(tmp_path)
    yield harness
    harness.approval.stop()


def test_start_brings_up_tunnel_and_checks_it_before_requesting(h):
    assert h.approval.start() is True
    kinds = [e[0] for e in h.events]
    assert kinds == ["spawn", "check", "request"]
    argv = h.events[0][1]
    assert argv[:2] == ["ngrok", "http"] and "https://demo.ngrok-free.app" in argv
    assert h.events[1][1] == f"https://demo.ngrok-free.app/upstox/notify/{SECRET}"
    assert len(h.msgs) == 1 and "Approve" in h.msgs[0]


def test_failed_tunnel_check_never_sends_request_and_cleans_up(tmp_path):
    h = Harness(tmp_path, tunnel_ok=False)
    assert h.approval.start() is False
    assert "request" not in [e[0] for e in h.events]
    assert h.proc.terminated
    assert not (tmp_path / "ngrok.pid").exists()
    assert "browser" in h.msgs[-1].lower()


def test_refused_request_cleans_up(tmp_path):
    h = Harness(tmp_path, request_ok=False)
    assert h.approval.start() is False
    assert h.proc.terminated


def test_valid_notification_is_saved(h):
    h.approval.start()
    status = h.post(f"/upstox/notify/{SECRET}", {"access_token": "TOKEN_VALUE"})
    assert status == 200
    assert h.saved == [{"access_token": "TOKEN_VALUE", "user_id": "AB1234"}]
    assert "received" in h.msgs[-1].lower()


def test_wrong_path_is_404_and_saves_nothing(h):
    h.approval.start()
    assert h.post("/upstox/notify/guess", {"access_token": "x"}) == 404
    assert h.saved == []


def test_rejected_notification_is_400_and_saves_nothing(tmp_path):
    def reject(payload, api_key):
        raise TokenRejected("client_id does not match this app")
    h = Harness(tmp_path, accept=reject)
    h.approval.start()
    try:
        assert h.post(f"/upstox/notify/{SECRET}", {"access_token": "x"}) == 400
        assert h.saved == []
    finally:
        h.approval.stop()


def test_stop_terminates_ngrok_releases_pidfile_and_is_idempotent(h, tmp_path):
    h.approval.start()
    assert (tmp_path / "ngrok.pid").exists()
    h.approval.stop()
    h.approval.stop()
    assert h.proc.terminated
    assert not (tmp_path / "ngrok.pid").exists()


def test_stale_ngrok_from_a_previous_run_is_killed_first(tmp_path):
    (tmp_path / "ngrok.pid").write_text("999")
    h = Harness(tmp_path)
    h.approval._lock_alive = lambda p: True
    h.approval.start()
    try:
        assert h.killed == [999]
    finally:
        h.approval.stop()


def test_messages_never_leak_token_or_secrets(h):
    h.approval.start()
    h.post(f"/upstox/notify/{SECRET}", {"access_token": "TOKEN_VALUE"})
    h.approval.stop()
    text = " ".join(h.msgs)
    for secret in ("TOKEN_VALUE", SECRET, "API_SECRET"):
        assert secret not in text


def test_from_env_is_disabled_without_domain_or_secret():
    assert ta.PhoneApproval.from_env({}, {"api_key": "k", "api_secret": "s"}) is None
    enabled = ta.PhoneApproval.from_env(
        {"UPSTOX_NOTIFY_DOMAIN": "d.ngrok-free.app", "UPSTOX_NOTIFY_SECRET": "x"},
        {"api_key": "k", "api_secret": "s"})
    assert enabled is not None
