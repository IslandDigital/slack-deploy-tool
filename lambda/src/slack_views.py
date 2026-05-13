"""Slack Block Kit modal definition + views.open API call.

App dropdown is static_select (not external) because Slack's view.state.values
isn't updated for external_select inside input blocks until the modal is
submitted — which breaks the version dropdown's ability to read the picked
app at block_suggestion time. Trade-off: all apps are shown regardless of env.
"""
import json
import urllib.error
import urllib.request

ENVIRONMENTS = ["dev", "test"]


def build_deploy_modal(apps: list[str], response_url: str = "") -> dict:
    env_options = [_opt(e) for e in ENVIRONMENTS]
    app_options = [_opt(a) for a in apps]

    return {
        "type": "modal",
        "callback_id": "deploy_submit",
        "private_metadata": json.dumps({"response_url": response_url}),
        "title": _txt("Deploy"),
        "submit": _txt("Deploy"),
        "close": _txt("Cancel"),
        "blocks": [
            {
                "type": "input",
                "block_id": "env_block",
                "label": _txt("Environment"),
                "element": {
                    "type": "static_select",
                    "action_id": "env_select",
                    "options": env_options,
                    "initial_option": env_options[0],
                },
            },
            {
                "type": "input",
                "block_id": "app_block",
                "label": _txt("App"),
                "element": {
                    "type": "static_select",
                    "action_id": "app_select",
                    "options": app_options,
                    "initial_option": app_options[0],
                },
            },
            {
                "type": "input",
                "block_id": "version_block",
                "label": _txt("Version"),
                "element": {
                    "type": "external_select",
                    "action_id": "version_select",
                    "placeholder": _txt("latest (HEAD) or pick a tag"),
                    "min_query_length": 0,
                },
            },
        ],
    }


def build_version_options(tags: list[str]) -> dict:
    options = [_opt("latest (HEAD)", "__head__")] + [_opt(t) for t in tags]
    return {"options": options[:100]}


def post_to_response_url(response_url: str, text: str, timeout_seconds: float = 3.0) -> None:
    """Post an in-channel message back via the slash command's response_url.

    response_url is valid for 30 minutes and allows up to 5 messages. No bot
    scopes required — Slack treats this as the slash command's own reply.
    """
    payload = json.dumps({"response_type": "in_channel", "text": text}).encode("utf-8")
    req = urllib.request.Request(
        response_url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "slack-deploy-tool",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        resp.read()


def open_modal(bot_token: str, trigger_id: str, view: dict, timeout_seconds: float = 3.0) -> None:
    payload = json.dumps({"trigger_id": trigger_id, "view": view}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/views.open",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "slack-deploy-tool",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError(f"views.open returned not-ok: {body}")


def _txt(s: str) -> dict:
    return {"type": "plain_text", "text": s}


def _opt(label: str, value: str | None = None) -> dict:
    return {"text": _txt(label), "value": value or label}
