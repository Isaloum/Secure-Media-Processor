# ============================================================================
# AWS Cognito User Pool
# ============================================================================
# Free tier: 50,000 monthly active users
# Provides: Sign up, sign in, password reset, email verification

resource "aws_cognito_user_pool" "main" {
  name = "${local.name_prefix}-users"

  # Username settings
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Password policy
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = false  # Keep it user-friendly
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration (use Cognito default - free)
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Schema attributes
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 5
      max_length = 254
    }
  }

  schema {
    name                     = "name"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 1
      max_length = 100
    }
  }

  # Custom attributes for license info
  schema {
    name                     = "license_tier"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 1
      max_length = 50
    }
  }

  # User verification
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Secure Media Processor - Verify your email"
    email_message        = "Your verification code is {####}"
  }

  # MFA (optional - disabled to keep it simple)
  mfa_configuration = "OFF"

  # Device tracking (disabled to reduce complexity)
  device_configuration {
    challenge_required_on_new_device      = false
    device_only_remembered_on_user_prompt = false
  }

  # Prevent user existence errors (security best practice)
  user_pool_add_ons {
    advanced_security_mode = "OFF"  # Keep costs at $0
  }

  tags = {
    Name = "${local.name_prefix}-user-pool"
  }
}

# User Pool Domain (for hosted UI)
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${local.name_prefix}-${random_id.suffix.hex}"
  user_pool_id = aws_cognito_user_pool.main.id
}

# App Client (for frontend)
resource "aws_cognito_user_pool_client" "web" {
  name         = "${local.name_prefix}-web-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # Token validity
  access_token_validity  = 1   # 1 hour
  id_token_validity      = 1   # 1 hour
  refresh_token_validity = 30  # 30 days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Auth flows
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]

  # OAuth settings
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  supported_identity_providers         = ["COGNITO"]

  # Callback URLs
  callback_urls = concat(
    var.cognito_callback_urls,
    [
      "https://${var.domain_name}/callback",
      "https://${var.app_subdomain}.${var.domain_name}/callback"
    ]
  )

  logout_urls = concat(
    var.cognito_logout_urls,
    [
      "https://${var.domain_name}",
      "https://${var.app_subdomain}.${var.domain_name}"
    ]
  )

  # Security settings
  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true

  # No client secret for SPA (public client)
  generate_secret = false

  # Read/write attributes
  read_attributes = [
    "email",
    "email_verified",
    "name",
    "custom:license_tier"
  ]

  write_attributes = [
    "email",
    "name",
    "custom:license_tier"
  ]
}

# App Client (for API/backend - with secret)
resource "aws_cognito_user_pool_client" "api" {
  name         = "${local.name_prefix}-api-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # Token validity
  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Auth flows for backend
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Generate secret for backend use
  generate_secret = true

  # Security
  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true
}

# Resource Server (for API scopes)
resource "aws_cognito_resource_server" "api" {
  identifier   = "https://${var.api_subdomain}.${var.domain_name}"
  name         = "${local.name_prefix}-api"
  user_pool_id = aws_cognito_user_pool.main.id

  scope {
    scope_name        = "read"
    scope_description = "Read access to API"
  }

  scope {
    scope_name        = "write"
    scope_description = "Write access to API"
  }

  scope {
    scope_name        = "admin"
    scope_description = "Admin access to API"
  }
}
