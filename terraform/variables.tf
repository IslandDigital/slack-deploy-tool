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
  description = "Prefix for IAM and Secrets Manager resource names."
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
