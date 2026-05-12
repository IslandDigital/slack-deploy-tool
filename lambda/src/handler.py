import base64
import os
import urllib.parse

import boto3

from github_dispatch import trigger_deployment
from slack_signature import is_valid

_secrets_client = None
_cached_secrets: dict[str, str] = {}


def _get_secret(secret_id: str) -> str:
    if secret_id in _cached_secrets:
        return _cached_secrets[secret_id]
    global _secrets_client
    if _secrets_client is None:
        _secrets_client = boto3.client("secretsmanager")
    resp = _secrets_client.get_secret_value(SecretId=secret_id)
    value = resp["SecretString"]
    _cached_secrets[secret_id] = value
    return value


def _resp(status: int, body: str = "") -> dict:
    return {
        "statusCode": status,
        "body": body,
        "headers": {"Content-Type": "text/plain; charset=utf-8"},
    }


def lambda_handler(event: dict, context) -> dict:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    timestamp = headers.get("x-slack-request-timestamp")
    signature = headers.get("x-slack-signature")

    signing_secret = _get_secret(os.environ["SLACK_SIGNING_SECRET_ARN"])
    if not is_valid(signing_secret, timestamp, signature, body):
        return _resp(401)

    form = urllib.parse.parse_qs(body, keep_blank_values=True)
    text = (form.get("text", [""])[0] or "").strip().lower()
    user_name = form.get("user_name", [""])[0]

    if not text:
        return _resp(200, "Usage: /deploy staging | /deploy production")

    try:
        github_token = _get_secret(os.environ["GITHUB_TOKEN_ARN"])
        trigger_deployment(
            token=github_token,
            owner=os.environ["GITHUB_OWNER"],
            repo=os.environ["GITHUB_REPO"],
            workflow=os.environ["GITHUB_WORKFLOW"],
            environment=text,
        )
    except Exception as exc:
        print(f"deployment failed: {exc}")
        return _resp(200, f"Deployment failed: {exc}")

    return _resp(200, f"Deployment triggered for {text} by {user_name}")
