# Slack → GitHub Actions Deployment Tool (AWS Lambda + Python)

## Objective

A very small standalone internal tool that lets users trigger existing GitHub
Actions deployment pipelines directly from Slack.

The implementation is:

- AWS Lambda (Python 3.13)
- Terraform-provisioned, single root module
- Secrets in AWS Secrets Manager (Lambda reads at runtime via IAM role)
- Slack-signed requests (Lambda Function URL with `AuthorizationType = NONE`)
- Stdlib + boto3 only — no extra dependencies, no Lambda layer, no zip pipeline
- Compatible with existing GitHub Actions pipelines

This is intentionally a tiny operational footprint system.

---

## Architecture

```
Slack Slash Command
        ↓
Lambda Function URL  (auth_type = NONE — Slack signs the request)
        ↓
AWS Lambda (Python 3.13)
        ↓
GitHub workflow_dispatch API
        ↓
Existing GitHub Actions Deployment Pipeline
```

---

## Stack

| Purpose | Technology |
|---|---|
| Hosting | AWS Lambda |
| Runtime | Python 3.13 |
| HTTP entry | Lambda Function URL |
| Deployment engine | Existing GitHub Actions |
| Command interface | Slack Slash Commands |
| Secrets | AWS Secrets Manager |
| Provisioning | Terraform (`hashicorp/aws ~> 5.0`) |
| GitHub management | GitHub CLI (`gh`) |

---

## Required tooling

```bash
brew install awscli terraform gh
aws sts get-caller-identity --profile dangote-dev   # confirm AWS auth works
gh auth login                                       # for managing the GitHub PAT
```

Python 3.12+ is needed locally only for running `pytest` against the handler
code. The Lambda runtime is 3.13.

---

## Repository layout

```
devops/
├── slack-github-actions-deploy-tool-spec.md   # this file
├── lambda/
│   ├── src/
│   │   ├── handler.py             # Lambda entry point
│   │   ├── github_dispatch.py     # workflow_dispatch caller
│   │   └── slack_signature.py     # HMAC-SHA256 + 5-min replay window
│   ├── tests/
│   │   └── test_slack_signature.py
│   ├── pytest.ini
│   └── requirements-dev.txt
└── terraform/
    ├── main.tf                    # provider + Lambda + URL + Secrets Manager + IAM
    ├── variables.tf
    ├── outputs.tf
    ├── terraform.tfvars.example
    ├── README.md
    └── .gitignore
```

---

## GitHub requirements

The target workflow must support `workflow_dispatch`:

```yaml
name: Deploy
on:
  workflow_dispatch:
    inputs:
      environment:
        required: true
        default: staging
```

Create a Personal Access Token with `repo` and `workflow` scopes. Don't store
it anywhere on disk — you'll paste it directly into Secrets Manager below.

---

## Slack setup

1. Create an app at https://api.slack.com/apps
2. Add a slash command `/deploy`
3. Set Request URL to the Lambda Function URL output by Terraform
4. Save the Signing Secret (App Credentials → Signing Secret)

---

## Provisioning

```bash
cd devops/terraform
cp terraform.tfvars.example terraform.tfvars
# edit github_owner, github_repo

terraform init
terraform plan -out tfplan
terraform apply tfplan
```

Outputs include `function_url` (paste into Slack) and `post_apply_secret_commands`
with the exact `aws secretsmanager put-secret-value` invocations to seed the
two secrets.

Terraform never sees the secret values — they go directly from your shell into
Secrets Manager via the AWS CLI. Lambda's IAM role has `GetSecretValue` only on
those two specific ARNs.

---

## Local testing

```bash
cd devops/lambda
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

`tests/test_slack_signature.py` covers the HMAC validation: valid requests,
tampered bodies, stale timestamps, replay attempts, missing fields. The
deployment service and GitHub call are not tested in isolation — they're a
single `urllib` call with no logic worth mocking.

End-to-end testing requires a real Slack workspace and a real GitHub workflow
— do that against the deployed function, not locally.

---

## Updating Lambda code

Edit `lambda/src/`, then `terraform apply` — the `archive_file` data source
notices content changes and Terraform redeploys the function.

---

## Rotating secrets

```bash
aws secretsmanager put-secret-value --profile dangote-dev --region eu-west-1 \
  --secret-id slack-deploy/github-token --secret-string <NEW_PAT>
```

Warm Lambda containers cache the previous value until they recycle. To force
immediate pickup, redeploy the function (`terraform apply` after a no-op
change, or `aws lambda update-function-code`).

---

## Security posture

| Control | Where |
|---|---|
| Slack signature validation (HMAC-SHA256) | `slack_signature.py` |
| 5-minute replay-protection window | `slack_signature.py` (`MAX_SKEW_SECONDS`) |
| Constant-time signature compare | `hmac.compare_digest` |
| GitHub PAT scoping | `repo` + `workflow` only |
| Secret isolation | Secrets Manager, IAM scoped to two specific ARNs |
| Production deploy gating | Use GitHub Environment protection rules |
| Public Function URL exposure | Acceptable because every request must carry a valid Slack signature; unsigned requests get 401 |

---

## Design philosophy

This tool stays:

- small
- simple
- maintainable
- infrastructure-light

It is NOT a deployment platform. It is **a better button**.
