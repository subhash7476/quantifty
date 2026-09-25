import pytest

from core.auth import upstox_token_request as utr


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


def test_request_token_posts_secret_to_v3_endpoint():
    seen = {}

    def post(url, json, headers, timeout):
        seen.update(url=url, json=json)
        return Resp(200, {"status": "success",
                          "data": {"authorization_expiry": "1", "notifier_url": "u"}})

    out = utr.request_token("KEY", "SECRET", post=post)
    assert seen["url"] == "https://api.upstox.com/v3/login/auth/token/request/KEY"
    assert seen["json"] == {"client_secret": "SECRET"}
    assert out["authorization_expiry"] == "1"


def test_request_token_raises_on_error_without_echoing_secret():
    post = lambda url, json, headers, timeout: Resp(401, {"status": "error"})
    with pytest.raises(utr.TokenRequestError) as e:
        utr.request_token("KEY", "SECRET", post=post)
    assert "SECRET" not in str(e.value)


def _payload(**over):
    p = {"client_id": "KEY", "user_id": "AB1234", "access_token": "tok",
         "token_type": "Bearer", "expires_at": "1731448800000",
         "issued_at": "1731412800000", "message_type": "access_token"}
    p.update(over)
    return p


def _profile(user_id="AB1234", status=200):
    return lambda url, headers, timeout: Resp(status, {"status": "success",
                                                       "data": {"user_id": user_id}})


def test_accepts_verified_token():
    out = utr.accept_notification(_payload(), "KEY", get=_profile())
    assert out == {"access_token": "tok", "user_id": "AB1234",
                   "expires_at": "1731448800000"}


@pytest.mark.parametrize("payload, get, reason", [
    (_payload(message_type="other"), _profile(), "message_type"),
    (_payload(client_id="SOMEONE_ELSE"), _profile(), "client_id"),
    (_payload(access_token=""), _profile(), "access_token"),
    (_payload(), _profile(status=401), "profile"),
    (_payload(), _profile(user_id="ZZ9999"), "user_id"),
])
def test_rejects_unverifiable_notifications(payload, get, reason):
    with pytest.raises(utr.TokenRejected, match=reason):
        utr.accept_notification(payload, "KEY", get=get)


def test_rejects_non_dict_payload():
    with pytest.raises(utr.TokenRejected):
        utr.accept_notification(["x"], "KEY", get=_profile())
