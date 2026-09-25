"""Phone approval of the daily Upstox token, for mornings away from the PC.

Lifecycle (only while the orchestrator waits on its token gate):
  1. a one-route listener on 127.0.0.1:<port>,
  2. an ngrok tunnel publishing it at the free static domain,
  3. a GET through the public URL proving the tunnel reaches the listener —
     only then the token request, since Upstox is not documented to retry a
     failed delivery and each request pings the phone,
  4. Upstox asks for approval in its app + WhatsApp; on Approve it POSTs the
     token to https://<domain>/upstox/notify/<secret>, which is validated,
     proven against the profile API, and saved to credentials.json.
stop() tears both down on every exit path. The token, the API secret and the
path secret are never logged or sent to Telegram.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Mapping, Optional

import requests

from core.auth.upstox_token_request import (TokenRejected, TokenRequestError,
                                            accept_notification, request_token)
from scripts.ops import pidfile

_logger = logging.getLogger("token_approval")

ROOT = Path(__file__).resolve().parents[2]
NGROK_PID = ROOT / "data" / "ops" / "ngrok.pid"
DEFAULT_PORT = 5055
MAX_BODY_BYTES = 8192
NOTIFY_PREFIX = "/upstox/notify/"

__all__ = ["PhoneApproval", "TokenRequestError"]


def _spawn_ngrok(argv):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=flags)


def _tunnel_check(url: str) -> bool:
    try:
        r = requests.get(url, headers={"ngrok-skip-browser-warning": "1"}, timeout=5)
    except requests.RequestException:
        return False
    return r.status_code == 200 and r.text == "ok"


def _kill(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


class PhoneApproval:
    def __init__(self, *, api_key: str, api_secret: str, domain: str, secret: str,
                 ngrok_path: str = "ngrok", port: int = DEFAULT_PORT,
                 pid_path: Path = NGROK_PID,
                 spawn: Callable = _spawn_ngrok, tunnel_check: Callable = _tunnel_check,
                 request: Callable = request_token, accept: Callable = accept_notification,
                 save: Optional[Callable] = None, notify: Callable = lambda text: None,
                 kill: Callable = _kill, lock_alive: Callable = pidfile.lock_alive,
                 check_timeout_s: float = 30.0):
        self._api_key, self._api_secret = api_key, api_secret
        self._domain, self._secret, self._ngrok = domain, secret, ngrok_path
        self._port, self._pid_path = port, Path(pid_path)
        self._spawn, self._check, self._request = spawn, tunnel_check, request
        self._accept, self._notify, self._kill = accept, notify, kill
        self._lock_alive, self._check_timeout_s = lock_alive, check_timeout_s
        if save is None:
            from core.auth.credentials import credentials
            save = credentials.save
        self._save = save
        self._server: Optional[ThreadingHTTPServer] = None
        self._proc = None
        self.bound_port: Optional[int] = None

    @classmethod
    def from_env(cls, env: Mapping[str, str], creds: Mapping, **kw) -> Optional["PhoneApproval"]:
        domain, secret = env.get("UPSTOX_NOTIFY_DOMAIN"), env.get("UPSTOX_NOTIFY_SECRET")
        api_key, api_secret = creds.get("api_key"), creds.get("api_secret")
        if not (domain and secret and api_key and api_secret):
            return None
        return cls(api_key=api_key, api_secret=api_secret, domain=domain, secret=secret,
                   ngrok_path=env.get("NGROK_PATH", "ngrok"), **kw)

    @property
    def _public_url(self) -> str:
        return f"https://{self._domain}{NOTIFY_PREFIX}{self._secret}"

    def start(self) -> bool:
        """Open the tunnel and send the approval request. False → use the browser."""
        try:
            self._serve()
            self._open_tunnel()
            if not self._wait_for_tunnel():
                return self._fail("tunnel check failed")
            self._request(self._api_key, self._api_secret)
        except TokenRequestError as exc:
            return self._fail(str(exc))
        except Exception as exc:  # noqa: BLE001 — any failure here falls back to the browser
            _logger.exception("phone approval setup failed")
            return self._fail(type(exc).__name__)
        self._notify(f"Approve the Upstox login request sent at "
                     f"{datetime.now():%H:%M} (Upstox app / WhatsApp). Valid until 03:30.")
        return True

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except Exception:  # noqa: BLE001 — terminate already issued
                pass
            pidfile.release_lock(self._pid_path, self._proc.pid)
            self._proc = None

    def _fail(self, reason: str) -> bool:
        _logger.warning("phone approval unavailable: %s", reason)
        self.stop()
        self._notify(f"Upstox phone approval unavailable ({reason}). "
                     f"Log in via the browser at the PC.")
        return False

    def _open_tunnel(self) -> None:
        stale = pidfile.read_pid(self._pid_path)
        if stale is not None and self._lock_alive(self._pid_path):
            _logger.info("terminating stale ngrok pid %s", stale)
            self._kill(stale)
        self._proc = self._spawn([self._ngrok, "http", "--url", f"https://{self._domain}",
                                  str(self.bound_port)])
        pidfile.write_pid(self._pid_path, self._proc.pid)

    def _wait_for_tunnel(self) -> bool:
        deadline = time.monotonic() + self._check_timeout_s
        while True:
            if self._check(self._public_url):
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(1.0, remaining))

    def _on_notification(self, payload) -> int:
        try:
            token = self._accept(payload, self._api_key)
        except TokenRejected as exc:
            _logger.warning("token notification rejected: %s", exc)
            return 400
        self._save({"access_token": token["access_token"], "user_id": token["user_id"]})
        _logger.info("Upstox token received via phone approval")
        self._notify("Upstox token received. Orchestrator continuing.")
        return 200

    def _serve(self) -> None:
        route, approval = NOTIFY_PREFIX + self._secret, self

        class Handler(BaseHTTPRequestHandler):
            def _reply(self, code: int, body: bytes = b"") -> None:
                self.send_response(code)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # tunnel self-check
                self._reply(200, b"ok") if self.path == route else self._reply(404)

            def do_POST(self):
                if self.path != route:
                    return self._reply(404)
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0 or length > MAX_BODY_BYTES:
                    return self._reply(413)
                try:
                    payload = json.loads(self.rfile.read(length))
                except ValueError:
                    return self._reply(400)
                self._reply(approval._on_notification(payload))

            def log_message(self, fmt, *args):  # default logs the path, which holds the secret
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", self._port), Handler)
        self.bound_port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
