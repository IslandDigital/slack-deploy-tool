"""List git tags from the target repo, filtered by app prefix, with TTL cache.

Tags follow `<app>@<env>@YYYY.MM.DD.N`, e.g. `filing-next@dev@2026.05.08.4`.
We list refs/tags via the GitHub API and filter client-side.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

CACHE_TTL_SECONDS = 60
MAX_TAGS_PER_APP = 25

_cache: dict[str, tuple[float, list[str]]] = {}


def list_tags_for_app(
    token: str,
    owner: str,
    repo: str,
    app: str,
    timeout_seconds: float = 5.0,
) -> list[str]:
    """Return up to MAX_TAGS_PER_APP recent tags matching `<app>@...`, newest first."""
    cache_key = f"{owner}/{repo}/{app}"
    now = time.time()
    cached = _cache.get(cache_key)
    if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]

    url = (
        f"https://api.github.com/repos/{owner}/{repo}/git/matching-refs/tags/"
        f"{urllib.parse.quote(app)}@"
    )
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
    tags = tags[:MAX_TAGS_PER_APP]

    _cache[cache_key] = (now, tags)
    return tags
