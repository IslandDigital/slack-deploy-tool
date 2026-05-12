output "function_url" {
  value       = aws_lambda_function_url.this.function_url
  description = "Paste this into the Slack slash command Request URL."
}

output "function_name" {
  value       = aws_lambda_function.this.function_name
  description = "Lambda function name (use with `aws lambda update-function-code`)."
}

output "github_token_secret_id" {
  value       = aws_secretsmanager_secret.github_token.name
  description = "Secrets Manager ID for the GitHub PAT."
}

output "slack_signing_secret_id" {
  value       = aws_secretsmanager_secret.slack_signing_secret.name
  description = "Secrets Manager ID for the Slack signing secret."
}

output "post_apply_secret_commands" {
  value = <<EOT
Run these once to seed the runtime secrets (Secrets Manager entries are empty after apply):

  aws secretsmanager put-secret-value --profile ${var.aws_profile} --region ${var.region} \
    --secret-id ${aws_secretsmanager_secret.github_token.name} \
    --secret-string <YOUR_GITHUB_PAT>

  aws secretsmanager put-secret-value --profile ${var.aws_profile} --region ${var.region} \
    --secret-id ${aws_secretsmanager_secret.slack_signing_secret.name} \
    --secret-string <YOUR_SLACK_SIGNING_SECRET>

Future rotations: re-run `put-secret-value` with the same secret IDs.
Lambda fetches at cold start and caches per warm container.
EOT

  description = "Manual post-apply step — Terraform creates the secret shells but never writes values."
}
