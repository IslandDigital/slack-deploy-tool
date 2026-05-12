variable "region" {
  type        = string
  description = "AWS region."
  default     = "eu-west-1"
}

variable "aws_profile" {
  type        = string
  description = "Local AWS CLI profile to authenticate with."
  default     = "dangote-dev"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for IAM resource names."
  default     = "slack-deploy"
}

variable "function_name" {
  type        = string
  description = "Lambda function name."
  default     = "slack-deploy"
}

variable "github_owner" {
  type        = string
  description = "GitHub org or user owning the target repo."
}

variable "github_repo" {
  type        = string
  description = "GitHub repository name (without owner)."
}

variable "github_workflow" {
  type        = string
  description = "Workflow filename to dispatch (e.g. deploy.yml)."
  default     = "deploy.yml"
}

variable "github_token" {
  type        = string
  description = "GitHub PAT with repo + workflow scopes. Set via TF_VAR_github_token; never commit."
  sensitive   = true
}

variable "slack_signing_secret" {
  type        = string
  description = "Slack app signing secret. Set via TF_VAR_slack_signing_secret; never commit."
  sensitive   = true
}

variable "slack_bot_token" {
  type        = string
  description = "Slack bot token (xoxb-...). Required for views.open. Set via TF_VAR_slack_bot_token."
  sensitive   = true
}
