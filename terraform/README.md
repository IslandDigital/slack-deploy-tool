# Terraform — Slack Deploy Tool Infrastructure (AWS)

IaC for the AWS Lambda + Python implementation in
[`../lambda/`](../lambda/).

Owns infrastructure **and** packaging. Each `terraform apply` re-zips
`../lambda/src/` and re-deploys the function only if its hash changed.

Secrets (GitHub PAT, Slack signing secret) are passed as Lambda environment
variables. The values are sourced from sensitive Terraform variables backed by
`TF_VAR_*` shell env vars, so they never land in any file.

## What gets created

- IAM role for Lambda (basic execution / CloudWatch logs only)
- CloudWatch log group with 14-day retention
- Lambda function (Python 3.13, 10s timeout, 256 MB) with secrets in env
- REST API Gateway with `POST /deploy`, AWS_PROXY integration to the Lambda
- `aws_lambda_permission` letting API Gateway invoke

## Prerequisites

```bash
brew install terraform     # >= 1.10
aws sts get-caller-identity --profile dangote-dev   # confirm auth
```

## First-time setup

```bash
cd devops/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars — set github_owner, github_repo at minimum

# Provide the two secrets via env vars (silent prompt — keeps them out of history)
read -rs TF_VAR_github_token; export TF_VAR_github_token
read -rs TF_VAR_slack_signing_secret; export TF_VAR_slack_signing_secret

terraform init
terraform plan -out tfplan
terraform apply tfplan
```

State is in S3 (`s3://slack-deploy-terr-state/slack-deploy-tool/terraform.tfstate`),
encrypted, versioned, with native S3 locking (`use_lockfile = true`).

## After apply

```bash
terraform output slack_request_url
# → https://<api-id>.execute-api.eu-west-1.amazonaws.com/prod/deploy
# Paste into the Slack slash-command Request URL.
```

## Updating Lambda code

Edit `../lambda/src/`, re-export the two `TF_VAR_*` env vars, then
`terraform apply`. The `archive_file` data source notices content
changes and Terraform redeploys.

## Rotating secrets

```bash
read -rs TF_VAR_github_token; export TF_VAR_github_token
terraform apply
```

Lambda env vars update in-place; the next invocation sees the new value.

## Tear down

```bash
terraform destroy
```

## Files

| File | Purpose |
|---|---|
| `main.tf` | Provider + Lambda + API Gateway + IAM |
| `variables.tf` | Input variables — two are sensitive (`github_token`, `slack_signing_secret`) |
| `outputs.tf` | Slack request URL + function name |
| `terraform.tfvars.example` | Template — copy to `terraform.tfvars` (non-secret only) |
| `.gitignore` | Ignores state, tfvars, build/; commits `.terraform.lock.hcl` |

## Honest caveats

- Secret values live in Lambda's `environment.variables` block. Anyone with
  `lambda:GetFunctionConfiguration` on this function (in this account: anyone
  with admin) can read them. This is acceptable for a single-operator tool;
  for multi-team environments, prefer Secrets Manager.
- Secret values land in `terraform.tfstate` (in the S3 state bucket). Same
  blast radius as the IAM that already controls the bucket.
- Don't `print(os.environ)` or anything that dumps env vars in the Lambda
  code — it leaks secrets to CloudWatch.
