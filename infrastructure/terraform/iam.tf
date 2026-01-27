# ============================================================================
# IAM Roles and Policies
# ============================================================================

# -----------------------------------------------------------------------------
# Lambda Execution Role
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-lambda-execution"
  }
}

# Basic Lambda execution (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# DynamoDB access policy
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${local.name_prefix}-lambda-dynamodb"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.users.arn,
          "${aws_dynamodb_table.users.arn}/index/*",
          aws_dynamodb_table.files.arn,
          "${aws_dynamodb_table.files.arn}/index/*",
          aws_dynamodb_table.licenses.arn,
          "${aws_dynamodb_table.licenses.arn}/index/*",
          aws_dynamodb_table.usage.arn,
          "${aws_dynamodb_table.usage.arn}/index/*"
        ]
      }
    ]
  })
}

# S3 access policy
resource "aws_iam_role_policy" "lambda_s3" {
  name = "${local.name_prefix}-lambda-s3"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetObjectTagging",
          "s3:PutObjectTagging"
        ]
        Resource = [
          aws_s3_bucket.media.arn,
          "${aws_s3_bucket.media.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.media.arn
        ]
      }
    ]
  })
}

# Cognito access policy
resource "aws_iam_role_policy" "lambda_cognito" {
  name = "${local.name_prefix}-lambda-cognito"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:AdminGetUser",
          "cognito-idp:AdminUpdateUserAttributes",
          "cognito-idp:ListUsers"
        ]
        Resource = [
          aws_cognito_user_pool.main.arn
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# API Gateway CloudWatch Role
# -----------------------------------------------------------------------------
resource "aws_iam_role" "api_gateway_cloudwatch" {
  name = "${local.name_prefix}-apigw-cloudwatch"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-apigw-cloudwatch"
  }
}

resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  role       = aws_iam_role.api_gateway_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}
