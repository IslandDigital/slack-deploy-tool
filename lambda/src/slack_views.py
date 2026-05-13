"""Slack Block Kit modal definition + views.open API call."""
import json
import urllib.error
import urllib.request

ENVIRONMENTS = ["dev", "test"]


def build_deploy_modal() -> dict:
    """Initial modal — env is static, app and version are external_select (cascading).

    App options are fetched once env is selected (filtered by env).
    Version options are fetched once both env and app are selected
    (filtered by `<app>@<env>@` prefix).
    """
    env_options = [_opt(e) for e in ENVIRONMENTS]

    return {
        "type": "modal",
        "callback_id": "deploy_submit",
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
                    "type": "external_select",
                    "action_id": "app_select",
                    "placeholder": _txt("pick an app"),
                    "min_query_length": 0,
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


def build_app_options(apps: list[str]) -> dict:
    """Block-suggestion response shape for app_select."""
    return {"options": [_opt(a) for a in apps][:100]}


def build_version_options(tags: list[str]) -> dict:
    """Block-suggestion response shape for version_select. Includes a HEAD sentinel."""
    options = [_opt("latest (HEAD)", "__head__")] + [_opt(t) for t in tags]
    return {"options": options[:100]}


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
