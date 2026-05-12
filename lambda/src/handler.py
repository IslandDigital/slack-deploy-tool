import base64
import os
import urllib.parse

from github_dispatch import trigger_deployment
from slack_signature import is_valid


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

    if not is_valid(os.environ["SLACK_SIGNING_SECRET"], timestamp, signature, body):
        return _resp(401)

    form = urllib.parse.parse_qs(body, keep_blank_values=True)
    text = (form.get("text", [""])[0] or "").strip().lower()
    user_name = form.get("user_name", [""])[0]

    if not text:
        return _resp(200, "Usage: /deploy staging | /deploy production")

    try:
        trigger_deployment(
            token=os.environ["GITHUB_TOKEN"],
            owner=os.environ["GITHUB_OWNER"],
            repo=os.environ["GITHUB_REPO"],
            workflow=os.environ["GITHUB_WORKFLOW"],
            environment=text,
        )
    except Exception as exc:
        print(f"deployment failed: {exc}")
        return _resp(200, f"Deployment failed: {exc}")

    return _resp(200, f"Deployment triggered for {text} by {user_name}")
