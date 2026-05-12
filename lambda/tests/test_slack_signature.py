import hashlib
import hmac
import time

from slack_signature import is_valid

SECRET = "test-secret"


def _sign(secret: str, ts: int, body: str) -> str:
    base = f"v0:{ts}:{body}".encode("utf-8")
    return "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()


def test_valid_signature_passes():
    ts = int(time.time())
    body = "command=%2Fdeploy&text=staging"
    assert is_valid(SECRET, str(ts), _sign(SECRET, ts, body), body)


def test_wrong_signature_fails():
    ts = int(time.time())
    assert not is_valid(SECRET, str(ts), "v0=deadbeef", "x=1")


def test_stale_timestamp_fails():
    ts = int(time.time()) - 600
    body = "x=1"
    assert not is_valid(SECRET, str(ts), _sign(SECRET, ts, body), body)


def test_future_timestamp_fails():
    ts = int(time.time()) + 600
    body = "x=1"
    assert not is_valid(SECRET, str(ts), _sign(SECRET, ts, body), body)


def test_missing_secret_fails():
    ts = int(time.time())
    assert not is_valid("", str(ts), "v0=anything", "x=1")


def test_missing_headers_fail():
    assert not is_valid(SECRET, None, None, "x=1")


def test_wrong_prefix_fails():
    ts = int(time.time())
    body = "x=1"
    sig = _sign(SECRET, ts, body).replace("v0=", "v1=")
    assert not is_valid(SECRET, str(ts), sig, body)


def test_tampered_body_fails():
    ts = int(time.time())
    body = "command=%2Fdeploy&text=staging"
    sig = _sign(SECRET, ts, body)
    assert not is_valid(SECRET, str(ts), sig, "command=%2Fdeploy&text=production")


def test_non_numeric_timestamp_fails():
    body = "x=1"
    assert not is_valid(SECRET, "not-a-number", "v0=anything", body)
