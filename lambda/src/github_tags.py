"""Fetch + filter git tags from the target repo. One bulk fetch, all filtering client-side.

Tag convention: `<app>@<env>@YYYY.MM.DD.N`, e.g. `filing-next@dev@2026.05.08.4`.
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
    """Return up to MAX_TAGS_RETURNED tags matching `<app>@<env>@*`, newest-first."""
    prefix = f"{app}@{env}@"
    return [t for t in all_tags if t.startswith(prefix)][:MAX_TAGS_RETURNED]


def apps_with_tags_for_env(all_tags: list[str], env: str, candidate_apps: list[str]) -> list[str]:
    """Return apps from `candidate_apps` that have at least one tag for `env`."""
    return [a for a in candidate_apps if any(t.startswith(f"{a}@{env}@") for t in all_tags)]
