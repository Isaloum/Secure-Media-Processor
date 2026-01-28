# ============================================================================
# Secure Media Processor - Main Terraform Configuration
# ============================================================================
#
# Budget-optimized serverless architecture (~$1-10/month)
# - AWS Lambda + API Gateway (free tier: 1M requests/month)
# - DynamoDB (free tier: 25GB storage)
# - S3 (static hosting + file storage)
# - Cognito (free tier: 50,000 MAU)
#
# Usage:
#   terraform init
#   terraform plan -var="domain_name=yourdomain.com"
#   terraform apply -var="domain_name=yourdomain.com"
# ============================================================================

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Uncomment to use S3 backend for state (recommended for production)
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "secure-media-processor/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Secondary provider for CloudFront (must be us-east-1)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = local.common_tags
  }
}

# Random suffix for globally unique names
resource "random_id" "suffix" {
  byte_length = 4
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# Data source for current region
data "aws_region" "current" {}
