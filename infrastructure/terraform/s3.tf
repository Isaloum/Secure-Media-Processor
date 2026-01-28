# ============================================================================
# S3 Buckets
# ============================================================================
# - Frontend bucket: Static website hosting for React app
# - Media bucket: User uploaded/processed files (encrypted)

# -----------------------------------------------------------------------------
# Frontend Bucket (Static Website)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "frontend" {
  bucket = "${local.name_prefix}-frontend-${random_id.suffix.hex}"

  tags = {
    Name = "${local.name_prefix}-frontend"
  }
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"  # SPA fallback
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  depends_on = [aws_s3_bucket_public_access_block.frontend]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
}

resource "aws_s3_bucket_cors_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    max_age_seconds = 3600
  }
}

# -----------------------------------------------------------------------------
# Media Storage Bucket (Private, Encrypted)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "media" {
  bucket = "${local.name_prefix}-media-${random_id.suffix.hex}"

  tags = {
    Name = "${local.name_prefix}-media"
  }
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id

  versioning_configuration {
    status = var.enable_s3_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = [
      "https://${var.domain_name}",
      "https://${var.app_subdomain}.${var.domain_name}",
      "http://localhost:3000"
    ]
    expose_headers  = ["ETag", "x-amz-meta-*"]
    max_age_seconds = 3600
  }
}

# Lifecycle rule to auto-delete temporary files after 7 days
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    id     = "cleanup-temp-files"
    status = "Enabled"

    filter {
      prefix = "temp/"
    }

    expiration {
      days = 7
    }
  }

  rule {
    id     = "cleanup-incomplete-uploads"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# -----------------------------------------------------------------------------
# Lambda Deployment Bucket
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "lambda_deployments" {
  bucket = "${local.name_prefix}-lambda-${random_id.suffix.hex}"

  tags = {
    Name = "${local.name_prefix}-lambda-deployments"
  }
}

resource "aws_s3_bucket_public_access_block" "lambda_deployments" {
  bucket = aws_s3_bucket.lambda_deployments.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "lambda_deployments" {
  bucket = aws_s3_bucket.lambda_deployments.id

  rule {
    id     = "cleanup-old-deployments"
    status = "Enabled"

    filter {
      prefix = ""
    }

    # Keep only last 30 days of deployments
    expiration {
      days = 30
    }
  }
}
