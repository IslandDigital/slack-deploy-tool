terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  backend "s3" {
    bucket       = "slack-deploy-terr-state"
    key          = "slack-deploy-tool/terraform.tfstate"
    region       = "eu-west-1"
    profile      = "dangote-dev"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile
}

# -----------------------------------------------------------------------------
# Lambda zip — packaged from ../lambda/src
# -----------------------------------------------------------------------------
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/src"
  output_path = "${path.module}/build/lambda.zip"
}

# -----------------------------------------------------------------------------
# Secrets Manager — empty shells; values seeded manually post-apply
# -----------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "github_token" {
  name                    = "${var.name_prefix}/github-token"
  description             = "GitHub PAT for workflow_dispatch (seeded out-of-band)"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret" "slack_signing_secret" {
  name                    = "${var.name_prefix}/slack-signing-secret"
  description             = "Slack signing secret for HMAC validation (seeded out-of-band)"
  recovery_window_in_days = 0
}

# -----------------------------------------------------------------------------
# IAM
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "secrets_read" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.github_token.arn,
      aws_secretsmanager_secret.slack_signing_secret.arn,
    ]
  }
}

resource "aws_iam_role_policy" "secrets_read" {
  name   = "${var.name_prefix}-secrets-read"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.secrets_read.json
}

# -----------------------------------------------------------------------------
# CloudWatch logs — explicit so retention is set on creation
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 14
}

# -----------------------------------------------------------------------------
# Lambda function + Function URL
# -----------------------------------------------------------------------------
resource "aws_lambda_function" "this" {
  function_name    = var.function_name
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.13"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 10
  memory_size      = 256

  environment {
    variables = {
      GITHUB_TOKEN_ARN         = aws_secretsmanager_secret.github_token.arn
      SLACK_SIGNING_SECRET_ARN = aws_secretsmanager_secret.slack_signing_secret.arn
      GITHUB_OWNER             = var.github_owner
      GITHUB_REPO              = var.github_repo
      GITHUB_WORKFLOW          = var.github_workflow
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs,
    aws_cloudwatch_log_group.lambda,
  ]
}

resource "aws_lambda_function_url" "this" {
  function_name      = aws_lambda_function.this.function_name
  authorization_type = "NONE"
}
