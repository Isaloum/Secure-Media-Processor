# ============================================================================
# AWS Lambda Function
# ============================================================================
# Serverless API using Lambda + API Gateway
# Free tier: 1M requests/month, 400,000 GB-seconds compute

# Placeholder for Lambda deployment package
# This will be replaced by actual deployment from CI/CD
data "archive_file" "lambda_placeholder" {
  type        = "zip"
  output_path = "${path.module}/lambda_placeholder.zip"

  source {
    content  = <<-EOF
      def handler(event, context):
          return {
              'statusCode': 200,
              'headers': {
                  'Content-Type': 'application/json',
                  'Access-Control-Allow-Origin': '*'
              },
              'body': '{"message": "Secure Media Processor API - Deploy the actual code"}'
          }
    EOF
    filename = "handler.py"
  }
}

# Main API Lambda function
resource "aws_lambda_function" "api" {
  function_name = "${local.name_prefix}-api"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "main.handler"
  runtime       = "python3.11"

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      AWS_REGION_NAME      = var.aws_region
      DYNAMODB_USERS_TABLE = aws_dynamodb_table.users.name
      DYNAMODB_FILES_TABLE = aws_dynamodb_table.files.name
      DYNAMODB_LICENSES_TABLE = aws_dynamodb_table.licenses.name
      DYNAMODB_USAGE_TABLE = aws_dynamodb_table.usage.name
      S3_MEDIA_BUCKET      = aws_s3_bucket.media.id
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.main.id
      COGNITO_CLIENT_ID    = aws_cognito_user_pool_client.web.id
      CORS_ORIGINS         = "https://${var.domain_name},https://${var.app_subdomain}.${var.domain_name},http://localhost:3000"
    }
  }

  tags = {
    Name = "${local.name_prefix}-api"
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.lambda_dynamodb,
    aws_iam_role_policy.lambda_s3,
    aws_iam_role_policy.lambda_cognito
  ]
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_api" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 7  # Keep logs for 7 days to minimize costs

  tags = {
    Name = "${local.name_prefix}-api-logs"
  }
}

# -----------------------------------------------------------------------------
# Lambda Function URL (Alternative to API Gateway - simpler, free)
# -----------------------------------------------------------------------------
resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"  # Public access (auth handled in code)

  cors {
    allow_credentials = true
    allow_origins     = [
      "https://${var.domain_name}",
      "https://${var.app_subdomain}.${var.domain_name}",
      "http://localhost:3000"
    ]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers     = ["*"]
    expose_headers    = ["*"]
    max_age           = 3600
  }
}
