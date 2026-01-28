# ============================================================================
# Terraform Outputs
# ============================================================================
# These values are needed for frontend configuration and deployment

# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------
output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "lambda_function_url" {
  description = "Lambda Function URL (alternative to API Gateway)"
  value       = aws_lambda_function_url.api.function_url
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.main.id
}

# -----------------------------------------------------------------------------
# Cognito
# -----------------------------------------------------------------------------
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  description = "Cognito User Pool ARN"
  value       = aws_cognito_user_pool.main.arn
}

output "cognito_client_id" {
  description = "Cognito App Client ID (for frontend)"
  value       = aws_cognito_user_pool_client.web.id
}

output "cognito_domain" {
  description = "Cognito hosted UI domain"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "cognito_issuer" {
  description = "Cognito token issuer URL"
  value       = "https://${aws_cognito_user_pool.main.endpoint}"
}

# -----------------------------------------------------------------------------
# S3 Buckets
# -----------------------------------------------------------------------------
output "frontend_bucket_name" {
  description = "S3 bucket name for frontend hosting"
  value       = aws_s3_bucket.frontend.id
}

output "frontend_bucket_website_url" {
  description = "S3 static website URL"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "media_bucket_name" {
  description = "S3 bucket name for media storage"
  value       = aws_s3_bucket.media.id
}

output "lambda_deployment_bucket" {
  description = "S3 bucket for Lambda deployments"
  value       = aws_s3_bucket.lambda_deployments.id
}

# -----------------------------------------------------------------------------
# DynamoDB Tables
# -----------------------------------------------------------------------------
output "dynamodb_users_table" {
  description = "DynamoDB Users table name"
  value       = aws_dynamodb_table.users.name
}

output "dynamodb_files_table" {
  description = "DynamoDB Files table name"
  value       = aws_dynamodb_table.files.name
}

output "dynamodb_licenses_table" {
  description = "DynamoDB Licenses table name"
  value       = aws_dynamodb_table.licenses.name
}

output "dynamodb_usage_table" {
  description = "DynamoDB Usage table name"
  value       = aws_dynamodb_table.usage.name
}

# -----------------------------------------------------------------------------
# Lambda
# -----------------------------------------------------------------------------
output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.api.arn
}

output "lambda_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda_execution.arn
}

# -----------------------------------------------------------------------------
# Configuration for Frontend
# -----------------------------------------------------------------------------
output "frontend_config" {
  description = "Configuration values for frontend .env file"
  value = <<-EOT
    # Secure Media Processor Frontend Configuration
    # Copy these values to your frontend .env file

    REACT_APP_API_URL=${aws_apigatewayv2_api.main.api_endpoint}
    REACT_APP_COGNITO_USER_POOL_ID=${aws_cognito_user_pool.main.id}
    REACT_APP_COGNITO_CLIENT_ID=${aws_cognito_user_pool_client.web.id}
    REACT_APP_COGNITO_DOMAIN=${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com
    REACT_APP_AWS_REGION=${var.aws_region}
    REACT_APP_S3_MEDIA_BUCKET=${aws_s3_bucket.media.id}
  EOT
}

# -----------------------------------------------------------------------------
# Configuration for Backend/Lambda
# -----------------------------------------------------------------------------
output "backend_config" {
  description = "Configuration values for backend .env file"
  sensitive   = true
  value = <<-EOT
    # Secure Media Processor Backend Configuration

    ENVIRONMENT=${var.environment}
    AWS_REGION=${var.aws_region}
    DYNAMODB_USERS_TABLE=${aws_dynamodb_table.users.name}
    DYNAMODB_FILES_TABLE=${aws_dynamodb_table.files.name}
    DYNAMODB_LICENSES_TABLE=${aws_dynamodb_table.licenses.name}
    DYNAMODB_USAGE_TABLE=${aws_dynamodb_table.usage.name}
    S3_MEDIA_BUCKET=${aws_s3_bucket.media.id}
    COGNITO_USER_POOL_ID=${aws_cognito_user_pool.main.id}
    COGNITO_CLIENT_ID=${aws_cognito_user_pool_client.web.id}
  EOT
}

# -----------------------------------------------------------------------------
# Deployment Commands
# -----------------------------------------------------------------------------
output "deployment_commands" {
  description = "Useful deployment commands"
  value = <<-EOT
    # Deploy frontend to S3
    aws s3 sync ./frontend/build s3://${aws_s3_bucket.frontend.id} --delete

    # Update Lambda function code
    aws lambda update-function-code \
      --function-name ${aws_lambda_function.api.function_name} \
      --zip-file fileb://lambda.zip

    # View Lambda logs
    aws logs tail /aws/lambda/${aws_lambda_function.api.function_name} --follow
  EOT
}
