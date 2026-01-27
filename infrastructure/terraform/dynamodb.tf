# ============================================================================
# DynamoDB Tables
# ============================================================================
# Using on-demand billing to stay within free tier and minimize costs
# Free tier: 25 GB storage, 25 WCU, 25 RCU

# Users table - stores user metadata and preferences
resource "aws_dynamodb_table" "users" {
  name         = "${local.name_prefix}-users"
  billing_mode = "PAY_PER_REQUEST"  # On-demand, no provisioned capacity
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  # GSI for email lookups
  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = false  # Disable to save costs
  }

  tags = {
    Name = "${local.name_prefix}-users"
  }
}

# Files table - tracks uploaded/processed files
resource "aws_dynamodb_table" "files" {
  name         = "${local.name_prefix}-files"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "file_id"
  range_key    = "user_id"

  attribute {
    name = "file_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  # GSI for user file listings
  global_secondary_index {
    name            = "user-files-index"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # TTL for auto-expiring temporary files
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "${local.name_prefix}-files"
  }
}

# Licenses table - tracks license keys and subscriptions
resource "aws_dynamodb_table" "licenses" {
  name         = "${local.name_prefix}-licenses"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "license_key"

  attribute {
    name = "license_key"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "gumroad_sale_id"
    type = "S"
  }

  # GSI for user license lookups
  global_secondary_index {
    name            = "user-licenses-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  # GSI for Gumroad sale ID lookups
  global_secondary_index {
    name            = "gumroad-sale-index"
    hash_key        = "gumroad_sale_id"
    projection_type = "ALL"
  }

  tags = {
    Name = "${local.name_prefix}-licenses"
  }
}

# Usage table - tracks API usage for rate limiting and analytics
resource "aws_dynamodb_table" "usage" {
  name         = "${local.name_prefix}-usage"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "period"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "period"
    type = "S"  # Format: YYYY-MM for monthly, YYYY-MM-DD for daily
  }

  # TTL for auto-cleanup of old usage records
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "${local.name_prefix}-usage"
  }
}
