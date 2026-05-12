output "slack_request_url" {
  value       = "${aws_api_gateway_stage.prod.invoke_url}/deploy"
  description = "Paste this into the Slack slash command Request URL."
}

output "function_name" {
  value       = aws_lambda_function.this.function_name
  description = "Lambda function name (use with `aws lambda update-function-code`)."
}
