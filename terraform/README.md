# Terraform — Slack Deploy Tool Infrastructure (AWS)

IaC for the AWS Lambda + Python implementation in
[`../lambda/`](../lambda/).

Owns infrastructure **and** packaging. Each `terraform apply` re-zips
`../lambda/src/` and re-deploys the function only if its hash changed.
Secret values are written directly into Secrets Manager via
`aws secretsmanager put-secret-value` and never pass through Terraform.

## What gets created

- IAM role for Lambda (basic execution + Secrets Manager read on the two named secrets)
- Two Secrets Manager entries — empty after apply, you populate them manually
- CloudWatch log group with 14-day retention
- Lambda function (Python 3.13, 10s timeout, 256 MB)
- Lambda Function URL (`AuthorizationType = NONE` — Slack signs the request)

## Prerequisites

```bash
brew install terraform     # >= 1.6
aws sts get-caller-identity --profile dangote-dev   # confirm auth
```

## First-time setup

```bash
cd devops/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars — set github_owner, github_repo at minimum

terraform init
terraform plan -out tfplan
terraform apply tfplan
```

State is **local** for this trial. Promote to a remote `s3` backend before
sharing the stack across machines.

## After apply — seed the secrets

`terraform output post_apply_secret_commands` prints the exact commands. In short:

```bash
GH_ID=$(terraform output -raw github_token_secret_id)
SL_ID=$(terraform output -raw slack_signing_secret_id)

aws secretsmanager put-secret-value --profile dangote-dev --region eu-west-1 \
  --secret-id "$GH_ID" --secret-string <YOUR_GITHUB_PAT>

aws secretsmanager put-secret-value --profile dangote-dev --region eu-west-1 \
  --secret-id "$SL_ID" --secret-string <YOUR_SLACK_SIGNING_SECRET>
```

Lambda fetches secrets on cold start and caches per warm container, so a
warm container will keep using the old value until it recycles. For
immediate pickup, force a redeploy:

```bash
aws lambda update-function-code --profile dangote-dev --region eu-west-1 \
  --function-name $(terraform output -raw function_name) \
  --zip-file fileb://build/lambda.zip
```

## Wire up Slack

```bash
terraform output function_url   # → paste into Slack slash command
```

## Updating Lambda code

Just edit files in `../lambda/src/` and re-run `terraform apply`. The
`archive_file` data source notices content changes and Terraform redeploys.

## Tear down

```bash
terraform destroy
```

`recovery_window_in_days = 0` on the secrets means names are reusable
immediately after destroy.

## Files

| File | Purpose |
|---|---|
| `main.tf` | Provider + Lambda + Function URL + Secrets Manager + IAM |
| `variables.tf` | Input variables — non-secret only |
| `outputs.tf` | Function URL, secret IDs, post-apply commands |
| `terraform.tfvars.example` | Template — copy to `terraform.tfvars` |
| `.gitignore` | Ignores state, tfvars, build/; commits `.terraform.lock.hcl` |
