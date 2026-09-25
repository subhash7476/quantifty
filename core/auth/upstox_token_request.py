"""Upstox Access Token Request flow — phone approval instead of a browser login.

request_token() asks Upstox to push an Approve/Reject prompt to the account
holder (Upstox app + WhatsApp). On approval Upstox POSTs the token to the
notifier webhook registered on the developer app; accept_notification()
validates that payload and proves the token works before anyone stores it.
Docs: https://upstox.com/developer/api-documentation/access-token-request
"""
from __future__ import annotations

from typing import Any, Callable, Dict

import requests

REQUEST_URL = "https://api.upstox.com/v3/login/auth/token/request/{client_id}"
PROFILE_URL = "https://api.upstox.com/v2/user/profile"
TIMEOUT_S = 20


class TokenRequestError(RuntimeError):
    """Upstox refused to open an approval request."""


class TokenRejected(ValueError):
    """A webhook payload that must not be stored as the access token."""


def request_token(api_key: str, api_secret: str,
                  post: Callable = requests.post) -> Dict[str, Any]:
    resp = post(REQUEST_URL.format(client_id=api_key),
                json={"client_secret": api_secret},
                headers={"accept": "application/json", "Content-Type": "application/json"},
                timeout=TIMEOUT_S)
    body = resp.json() if resp.status_code == 200 else {}
    if resp.status_code != 200 or body.get("status") != "success":
        raise TokenRequestError(f"token request refused: HTTP {resp.status_code}")
    return body.get("data", {})


def accept_notification(payload: Any, api_key: str,
                        get: Callable = requests.get) -> Dict[str, str]:
    if not isinstance(payload, dict):
        raise TokenRejected("payload is not an object")
    if payload.get("message_type") != "access_token":
        raise TokenRejected("unexpected message_type")
    if payload.get("client_id") != api_key:
        raise TokenRejected("client_id does not match this app")
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise TokenRejected("missing access_token")

    resp = get(PROFILE_URL, headers={"accept": "application/json",
                                     "Authorization": f"Bearer {token}"},
               timeout=TIMEOUT_S)
    if resp.status_code != 200:
        raise TokenRejected(f"profile check failed: HTTP {resp.status_code}")
    if resp.json().get("data", {}).get("user_id") != payload.get("user_id"):
        raise TokenRejected("user_id does not match the token's profile")
    return {"access_token": token, "user_id": payload["user_id"],
            "expires_at": payload.get("expires_at")}
