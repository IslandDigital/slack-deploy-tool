"""Fetch + filter git tags from the target repo. One bulk fetch, all filtering client-side.

Two tag conventions coexist in IslandDigital/tax-web:
  3-segment (env-aware, newer):  `<app>@<env>@YYYY.MM.DD.N`  — filter by app + env
  2-segment (legacy):            `<app>@<version>`           — filter by app only
"""
import json
import time
import urllib.error
import urllib.request

CACHE_TTL_SECONDS = 60
MAX_TAGS_RETURNED = 25

_all_tags_cache: dict[str, tuple[float, list[str]]] = {}


def list_all_tags(
    token: str,
    owner: str,
    repo: str,
    timeout_seconds: float = 5.0,
) -> list[str]:
    """All tags in the repo (newest-first by sort), cached for CACHE_TTL_SECONDS."""
    cache_key = f"{owner}/{repo}"
    now = time.time()
    cached = _all_tags_cache.get(cache_key)
    if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]

    url = f"https://api.github.com/repos/{owner}/{repo}/git/matching-refs/tags/"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "slack-deploy-tool",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub tag list failed ({exc.code}): {body}") from exc

    tags = [ref["ref"].removeprefix("refs/tags/") for ref in data]
    tags.sort(reverse=True)
    _all_tags_cache[cache_key] = (now, tags)
    return tags


def tags_for_app_env(all_tags: list[str], app: str, env: str) -> list[str]:
    """Tags matching `<app>@<env>@*` (3-seg, env-aware) OR `<app>@*` (2-seg legacy).

    Newest-first, capped at MAX_TAGS_RETURNED.
    """
    matches: list[str] = []
    for tag in all_tags:
        parts = tag.split("@")
        if len(parts) >= 3 and parts[0] == app and parts[1] == env:
            matches.append(tag)
        elif len(parts) == 2 and parts[0] == app:
            matches.append(tag)
    return matches[:MAX_TAGS_RETURNED]


def apps_with_tags_for_env(all_tags: list[str], env: str, candidate_apps: list[str]) -> list[str]:
    """Apps with a 3-seg tag for this env. If no app has any 3-seg tag for this env
    (e.g. env-tagging hasn't started here yet), return every candidate so the user
    isn't blocked from picking any app."""
    any_env_specific = any(
        len(t.split("@")) >= 3 and t.split("@")[1] == env for t in all_tags
    )
    if not any_env_specific:
        return list(candidate_apps)
    return [
        app for app in candidate_apps
        if any(t.startswith(f"{app}@{env}@") for t in all_tags)
    ]
