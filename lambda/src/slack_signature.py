import hashlib
import hmac
import time

MAX_SKEW_SECONDS = 5 * 60


def is_valid(
    signing_secret: str,
    timestamp_header: str | None,
    signature_header: str | None,
    body: str,
) -> bool:
    if not signing_secret or not timestamp_header or not signature_header:
        return False
    if not signature_header.startswith("v0="):
        return False

    try:
        ts = int(timestamp_header)
    except ValueError:
        return False

    if abs(time.time() - ts) > MAX_SKEW_SECONDS:
        return False

    base = f"v0:{timestamp_header}:{body}".encode("utf-8")
    digest = hmac.new(signing_secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"

    return hmac.compare_digest(expected, signature_header)
