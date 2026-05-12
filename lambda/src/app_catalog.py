"""Canonical app catalog and mapping to the deploy.yml workflow's boolean inputs.

Keeping this hardcoded (rather than parsing tax-web's deploy.yml at runtime) avoids
adding a YAML dependency and a GitHub round-trip on every modal open. When apps are
added to tax-web, append here and reapply — Terraform will redeploy the Lambda.
"""

# App name (as shown in modal + used as tag prefix) → deploy.yml boolean input.
APPS: dict[str, str] = {
    "calculator-next": "deploy_calculator",
    "filing-next": "deploy_filing",
    "home-page": "deploy_home_page",
    "invoicing-next": "deploy_invoicing",
    "api": "deploy_api",
}


def list_apps() -> list[str]:
    return list(APPS.keys())


def input_flag_for(app: str) -> str:
    return APPS[app]
