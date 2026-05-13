import base64
import json
import os
import urllib.parse

from app_catalog import APPS, list_apps
from github_dispatch import trigger_deployment
from github_tags import list_all_tags, tags_for_app_env
from slack_signature import is_valid
from slack_views import (
    build_deploy_modal,
    build_version_options,
    open_modal,
    post_to_response_url,
)


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

    if "payload" in form:
        return _route_interaction(json.loads(form["payload"][0]))

    return _handle_slash_command(form)


# -----------------------------------------------------------------------------
# Slash command — opens the deploy modal.
# -----------------------------------------------------------------------------
def _handle_slash_command(form: dict) -> dict:
    trigger_id = form.get("trigger_id", [""])[0]
    response_url = form.get("response_url", [""])[0]
    if not trigger_id:
        return _resp(200, "Slash command missing trigger_id.")

    try:
        open_modal(
            os.environ["SLACK_BOT_TOKEN"],
            trigger_id,
            build_deploy_modal(list_apps(), response_url=response_url),
        )
    except Exception as exc:
        print(f"views.open failed: {exc}")
        return _resp(200, f"Could not open deploy modal: {exc}")

    return _resp(200)


# -----------------------------------------------------------------------------
# Interactive payload router (view_submission, block_suggestion).
# -----------------------------------------------------------------------------
def _route_interaction(payload: dict) -> dict:
    kind = payload.get("type")
    if kind == "block_suggestion":
        return _handle_block_suggestion(payload)
    if kind == "view_submission":
        return _handle_view_submission(payload)
    return _resp(200)


# -----------------------------------------------------------------------------
# Block suggestion — only the version dropdown is external_select.
# Env and App are static_select (reliably committed to view.state.values).
# -----------------------------------------------------------------------------
def _handle_block_suggestion(payload: dict) -> dict:
    action_id = payload.get("action_id")
    if action_id != "version_select":
        return _json_resp(200, {"options": []})

    env = _selected_value(payload, "env_block", "env_select")
    app = _selected_value(payload, "app_block", "app_select")
    print(f"version_select: env={env!r} app={app!r}")

    if not app or not env:
        return _json_resp(200, build_version_options([]))

    try:
        all_tags = list_all_tags(
            token=os.environ["GITHUB_TOKEN"],
            owner=os.environ["GITHUB_OWNER"],
            repo=os.environ["GITHUB_REPO"],
        )
    except Exception as exc:
        print(f"all-tags fetch failed: {exc}")
        return _json_resp(200, build_version_options([]))

    filtered = tags_for_app_env(all_tags, app, env)
    print(f"version_select returning {len(filtered)} tags for {app}/{env}")
    return _json_resp(200, build_version_options(filtered))


def _selected_value(payload: dict, block_id: str, action_id: str) -> str | None:
    return (
        payload.get("view", {})
        .get("state", {})
        .get("values", {})
        .get(block_id, {})
        .get(action_id, {})
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
    user = payload.get("user", {})
    user_id = user.get("id", "")
    user_name = user.get("username", "?")
    response_url = _response_url_from_view(payload.get("view", {}))

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

    if response_url:
        version_label = "latest (HEAD)" if version == "__head__" else version
        announcement = (
            f"<@{user_id}> triggered deploy of `{app}` to `{environment}`"
            f" — version `{version_label}`"
        )
        try:
            post_to_response_url(response_url, announcement)
        except Exception as exc:
            # Non-fatal — the deploy already kicked off.
            print(f"channel announcement failed: {exc}")

    return _resp(200)


def _response_url_from_view(view: dict) -> str:
    raw = view.get("private_metadata") or ""
    if not raw:
        return ""
    try:
        return json.loads(raw).get("response_url", "")
    except json.JSONDecodeError:
        return ""


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
