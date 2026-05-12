import base64
import json
import os
import urllib.parse

from app_catalog import APPS, list_apps
from github_dispatch import trigger_deployment
from github_tags import list_tags_for_app
from slack_signature import is_valid
from slack_views import build_deploy_modal, build_version_options, open_modal


def _resp(status: int, body: str = "") -> dict:
    return {
        "statusCode": status,
        "body": body,
        "headers": {"Content-Type": "text/plain; charset=utf-8"},
    }


def _json_resp(status: int, payload: dict) -> dict:
    return {
        "statusCode": status,
        "body": json.dumps(payload),
        "headers": {"Content-Type": "application/json; charset=utf-8"},
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

    # Slack interactive payloads (view_submission, block_suggestion) arrive as
    # a single `payload` form field carrying JSON.
    if "payload" in form:
        return _route_interaction(json.loads(form["payload"][0]))

    return _handle_slash_command(form)


# -----------------------------------------------------------------------------
# Slash command — opens the deploy modal.
# -----------------------------------------------------------------------------
def _handle_slash_command(form: dict) -> dict:
    trigger_id = form.get("trigger_id", [""])[0]
    if not trigger_id:
        return _resp(200, "Slash command missing trigger_id.")

    view = build_deploy_modal(list_apps())
    try:
        open_modal(os.environ["SLACK_BOT_TOKEN"], trigger_id, view)
    except Exception as exc:
        print(f"views.open failed: {exc}")
        return _resp(200, f"Could not open deploy modal: {exc}")

    return _resp(200)


# -----------------------------------------------------------------------------
# Interactive payload router.
# -----------------------------------------------------------------------------
def _route_interaction(payload: dict) -> dict:
    kind = payload.get("type")
    if kind == "block_suggestion":
        return _handle_block_suggestion(payload)
    if kind == "view_submission":
        return _handle_view_submission(payload)
    return _resp(200)


# -----------------------------------------------------------------------------
# Block suggestion — populates the Version dropdown for the currently-selected App.
# -----------------------------------------------------------------------------
def _handle_block_suggestion(payload: dict) -> dict:
    if payload.get("action_id") != "version_select":
        return _json_resp(200, {"options": []})

    app = _selected_app(payload) or next(iter(APPS))
    try:
        tags = list_tags_for_app(
            token=os.environ["GITHUB_TOKEN"],
            owner=os.environ["GITHUB_OWNER"],
            repo=os.environ["GITHUB_REPO"],
            app=app,
        )
    except Exception as exc:
        print(f"tag list failed for {app}: {exc}")
        tags = []

    return _json_resp(200, build_version_options(tags))


def _selected_app(payload: dict) -> str | None:
    values = payload.get("view", {}).get("state", {}).get("values", {})
    return (
        values.get("app_block", {})
        .get("app_select", {})
        .get("selected_option", {})
        .get("value")
    )


# -----------------------------------------------------------------------------
# View submission — translate modal selections into deploy.yml inputs + dispatch.
# -----------------------------------------------------------------------------
def _handle_view_submission(payload: dict) -> dict:
    values = payload["view"]["state"]["values"]
    environment = values["env_block"]["env_select"]["selected_option"]["value"]
    app = values["app_block"]["app_select"]["selected_option"]["value"]
    version = values["version_block"]["version_select"]["selected_option"]["value"]
    user_name = payload.get("user", {}).get("username", "?")

    inputs = _build_workflow_inputs(environment=environment, app=app, version=version)

    try:
        trigger_deployment(
            token=os.environ["GITHUB_TOKEN"],
            owner=os.environ["GITHUB_OWNER"],
            repo=os.environ["GITHUB_REPO"],
            workflow=os.environ["GITHUB_WORKFLOW"],
            inputs=inputs,
        )
    except Exception as exc:
        print(f"deployment dispatch failed for {app}@{environment}: {exc}")
        return _json_resp(200, {
            "response_action": "errors",
            "errors": {"app_block": f"Dispatch failed: {exc}"[:255]},
        })

    print(f"deploy dispatched: app={app} env={environment} version={version} by={user_name}")
    # Empty 200 → Slack closes the modal.
    return _resp(200)


def _build_workflow_inputs(environment: str, app: str, version: str) -> dict:
    inputs: dict = {
        "environment": environment,
        "auto_detect": "false",
        "force_deploy": "false",
        "dry_run_tagging": "false",
        "sha": "" if version == "__head__" else version,
    }
    for known_app, flag_name in APPS.items():
        inputs[flag_name] = "true" if known_app == app else "false"
    return inputs
