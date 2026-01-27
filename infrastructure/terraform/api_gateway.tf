# ============================================================================
# API Gateway v2 (HTTP API)
# ============================================================================
# Using HTTP API (v2) instead of REST API for lower costs
# Free tier: 1M API calls/month for first 12 months

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"
  description   = "Secure Media Processor API"

  cors_configuration {
    allow_origins = [
      "https://${var.domain_name}",
      "https://${var.app_subdomain}.${var.domain_name}",
      "http://localhost:3000"
    ]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = [
      "Content-Type",
      "Authorization",
      "X-Amz-Date",
      "X-Api-Key",
      "X-Amz-Security-Token"
    ]
    expose_headers = ["*"]
    max_age        = 3600
  }

  tags = {
    Name = "${local.name_prefix}-api"
  }
}

# Lambda integration
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# Catch-all route (Lambda handles routing internally via FastAPI)
resource "aws_apigatewayv2_route" "catch_all" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId         = "$context.requestId"
      ip                = "$context.identity.sourceIp"
      requestTime       = "$context.requestTime"
      httpMethod        = "$context.httpMethod"
      routeKey          = "$context.routeKey"
      status            = "$context.status"
      protocol          = "$context.protocol"
      responseLength    = "$context.responseLength"
      integrationStatus = "$context.integrationStatus"
      errorMessage      = "$context.error.message"
    })
  }

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  tags = {
    Name = "${local.name_prefix}-api-stage"
  }
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.name_prefix}-api"
  retention_in_days = 7  # Minimize costs

  tags = {
    Name = "${local.name_prefix}-api-gateway-logs"
  }
}

# -----------------------------------------------------------------------------
# JWT Authorizer (Cognito)
# -----------------------------------------------------------------------------
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${local.name_prefix}-cognito-authorizer"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.web.id]
    issuer   = "https://${aws_cognito_user_pool.main.endpoint}"
  }
}

# Protected route example (can be added for specific endpoints)
# resource "aws_apigatewayv2_route" "protected" {
#   api_id             = aws_apigatewayv2_api.main.id
#   route_key          = "GET /api/protected"
#   target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
#   authorization_type = "JWT"
#   authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
# }
