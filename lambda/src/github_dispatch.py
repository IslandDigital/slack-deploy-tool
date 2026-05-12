import json
import urllib.error
import urllib.request


def trigger_deployment(
    token: str,
    owner: str,
    repo: str,
    workflow: str,
    environment: str,
    ref: str = "main",
    timeout_seconds: float = 10.0,
) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches"
    payload = json.dumps({"ref": ref, "inputs": {"environment": environment}}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "slack-deploy-tool",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"GitHub dispatch returned {resp.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub dispatch failed ({exc.code}): {body}") from exc
